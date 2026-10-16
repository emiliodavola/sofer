# Design — `2026-10-16-fix-mcp-registration-timeouts`

> **Change** `2026-10-16-fix-mcp-registration-timeouts` (issues **#287**, **#296**) · branch
> `fix/287-296-mcp-registration-timeouts` from `dev@6786ba1` · store **hybrid**.

---

## 1. The defect, precisely

`build_entry()` produced exactly what the adapter's `env` capability described and nothing else:

```python
entry["command"] = ["sofer-mcp"] if spec["command"] == "array" else "sofer-mcp"
entry["cwd"] = cwd_str
if spec["env"] == "allow_list": ...
```

No key bounded how long the host waited. Two deadlines then failed against host defaults, and neither
failure names its cause: the host reports `Connection failed … timed out` (cold start) or
`MCP request timed out after 60000ms` (per-request). The second is the worse one — the server
completes the work and writes the artifacts, and only the envelope is lost, so a caller reasoning over
`ok` cannot tell a failure from an unheard success.

## 2. Host schemas — researched, not guessed

| Agent | per-request key | connect/startup key | unit | host default |
| --- | --- | --- | --- | --- |
| pi | `timeout` | — (background connect) | seconds | 60, reset by progress notifications |
| hermes | `timeout` | `connect_timeout` | seconds | 300 / 60 |
| codex | `tool_timeout_sec` | `startup_timeout_sec` | seconds | 60 / 10 |
| gemini | `timeout` | — (same key covers discovery) | **milliseconds** | 600 000 |
| opencode | `timeout`, nested `{startup,catalog,execution}` | same object | **milliseconds** | 30 000 / 30 000 / 12 h |

Sources: Pi `docs/mcp.md` ("`timeout`: per-request timeout in seconds (default 60). Progress
notifications reset it."); Hermes *MCP Config Reference* (`timeout` number, "Tool call timeout in
seconds (default: 300)", `connect_timeout`, "Initial connection timeout in seconds (default: 60)");
Codex *Configuration Reference* (`mcp_servers.<name>.tool_timeout_sec`, `startup_timeout_sec`);
gemini-cli `packages/core/src/tools/mcp-client.ts`
(`options.timeout ?? this.serverConfig.timeout ?? MCP_DEFAULT_TIMEOUT_MSEC`, `MCP_DEFAULT_TIMEOUT_MSEC
= 10 * 60 * 1000`); opencode "MCP servers" (v2 docs: "Timeouts are positive integer milliseconds …
`timeout`: per-server timeout overrides" with `{startup, catalog, execution}`) plus its
`config/mcp.ts` zod schema, which declares `timeout` for a local server as a positive integer.

**opencode is excluded (decision D5).** Those two sources disagree: the zod schema says integer, the
current docs say a nested object in milliseconds. Writing the wrong shape risks failing validation of
the whole `mcp` block — a far worse outcome than an unset timeout — and opencode's own defaults
(30 s startup, 12 h execution) are not the pair that breaks. Its adapter declares no key and the README
names the manual one.

## 3. The edits

### 3.1 `src/sofer/config.py` + its `[tool.sofer]` home

Three defaults, read at the call site (AGENTS.md rule 1):

| Key | Default | Use |
| --- | --- | --- |
| `mcp_request_timeout_seconds` | `900` | Per-request deadline. Covers #296's measured ~680 s `prepare` with margin. |
| `mcp_connect_timeout_seconds` | `120` | Connect/startup deadline. ~4× #287's measured 32 s cold start. |
| `mcp_progress_heartbeat_seconds` | `20` | How often a long tool re-announces progress (§3.4). Must stay well under the smallest host default (60 s). |

All three are validated as positive integers: a non-positive host deadline would make the registered
server unusable, which is the failure the keys exist to prevent.

### 3.2 `src/sofer/mcp_registration.py` — capabilities, not branches

`Adapter` gains four fields, documented in the TypedDict, and `TestSingleSourceRegistry` now asserts
their value domains:

```python
timeout_key: str | None            # per-request deadline key
connect_timeout_key: str | None    # cold-start / initial-connection key
timeout_unit: Literal["seconds", "milliseconds"]
native_timeout: bool               # can the native `mcp add` set them?
```

`native_timeout` is `False` for every current agent — neither `codex mcp add` nor `gemini mcp add`
takes a timeout flag — but it is declared rather than hardcoded for the same reason `native_env` is
declared `False` for every agent: the gate stays a table read, and a host that grows the flag is one
edit.

`build_entry(agent, cwd, env, timeouts=None)` writes `timeout_entry_keys(agent, timeouts)` after
`cwd`. `timeouts=None` writes nothing, which is what `--no-timeout` and the pre-change shape share.

`_entries_equal()` gains `_timeout_keys_equal()`, called from the two env-specific branches. Without
it, changing `--timeout` alone would compare as unchanged and the idempotency guard would refuse to
rewrite — leaving the host with the old deadline while reporting `OK  already registered`.

`native_delegation_decline_reasons()` gains a `timeouts` parameter and appends `"timeout"` in fixed
order after `"env forwarding"` and `"project scope"`. Delegating without being able to set the
timeouts would drop exactly the values the entry was written for.

`dropped_timeout_note(agent, timeouts)` returns the stderr line for a host whose entry accepts no key
(opencode), mirroring `dropped_env_keys()`'s informational contract.

### 3.3 `src/sofer/cli.py`

Three flags on `mcp add`, with `_positive_seconds()` as the argparse type so a non-positive value
exits 2 with a usage message instead of being written:

- `--timeout SECONDS` → `Timeouts.request_seconds`, default `config.MCP_REQUEST_TIMEOUT_SECONDS`.
- `--connect-timeout SECONDS` → `Timeouts.connect_seconds`, default `config.MCP_CONNECT_TIMEOUT_SECONDS`.
- `--no-timeout` → `timeouts = None`.

The CLI passes `timeouts` to `delegate_add()` and `native_delegation_decline_reasons()` as well as
`build_entry()`, so the gate and the entry cannot disagree.

### 3.4 `src/sofer/mcp_server.py` — a heartbeat, not a callback

The long tools are synchronous and their domain functions print progress to captured stdout
(`_capture_output()`). Threading a progress callback through `prepare`/`codebook`/`profile`/`render`/
`publish` would touch five modules for a signal the host only needs as a deadline reset.

Instead each long tool becomes `async def` with `ctx: Context | None = None` (fastmcp's
`find_kwarg_by_type` treats a union containing `Context` as injected, so existing direct calls that
omit it keep working), and the existing body — lock, capture, domain call — runs in a worker thread
via `asyncio.to_thread` while a heartbeat task re-reports progress:

```python
task = asyncio.create_task(asyncio.to_thread(body))
while not task.done():
    await ctx.report_progress(...)      # resets the host deadline
    await asyncio.sleep(config.MCP_PROGRESS_HEARTBEAT_SECONDS)
```

The `_EXEC_LOCK` stays a `threading.Lock`, acquired only inside the worker thread. Acquiring it on the
event loop while another coroutine holds it and awaits its own worker would block the loop forever —
the body-in-a-thread shape avoids that entirely.

`Context.report_progress` is a no-op when the client sent no progress token, so clients that do not ask
for progress are unaffected.

### 3.5 Tests

`tests/test_mcp_registration.py` gains `TestRegistrationTimeouts` (10 tests: per-host key names and
units, the no-timeout shape, opencode's silence, the changed-timeout rewrite, both idempotency paths,
the decline reason and its order, and the note). `tests/test_cli.py` gains
`TestMcpRegistrationTimeoutsCli` (11 tests: defaults written, flags overriding, `--no-timeout`, gemini
milliseconds, the rewrite + backup, the decline warning followed by the file edit, delegation restored
by `--no-timeout`, opencode's stderr note, dry-run writing nothing, four rejected values, and the help
text).

Eight existing tests changed expectation, each because the behaviour change is the change:

| Test | Why it changed |
| --- | --- |
| `TestSingleSourceRegistry::test_every_agent_name_has_a_complete_adapter` | The required adapter key set gains the four capabilities; the test now also asserts their domains. |
| `TestSingleSourceRegistry::test_all_expansion_and_choices_track_a_new_registry_entry` | The fake sentinel entry needs the four keys to be a complete adapter. |
| `TestPiAdapter::test_pi_registry_entry_is_complete` | Exact-dict assertion on the adapter. |
| `TestHermesAdapter::test_hermes_registry_entry_is_exact` | Exact-dict assertion on the adapter. |
| `TestPiCli::test_pi_add_project_writes_dot_pi_and_env` | The written entry now carries `timeout`. |
| `TestPiAdapter::test_pi_entry_shape_string_command_no_type_or_enabled` | Now also asserts the no-`Timeouts` shape writes no key. |
| `TestMerge::test_codex_normalize_string_vs_array` | Its fixture entry lacked the timeout keys, so the rewrite it observed was the timeout being added rather than the command-form normalization it is about; the fixture now carries them. |
| `TestMcpNativeDelegationFidelityCli::test_add_generic_failure_when_no_fidelity_reason` | With a timeout written, codex now declines with the `timeout` reason; the case passes `--no-timeout` to stay about the *generic* fallback message. |

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is nevertheless a real red-then-green for
the behaviour change, with the ordering stated plainly rather than dressed up: the production edits
for `config.py`, `ADAPTERS`, `build_entry` and the gate landed **before** the new test section was
written, so the new tests never observed RED themselves.

- **RED (measured):** `uv run pytest tests/test_mcp_registration.py tests/test_cli.py tests/test_config.py -q`
  against the modified tree with the eight existing tests untouched → `8 failed, 416 passed, 3 skipped`.
  Every failure was the new behaviour arriving (`'timeout_key'` missing from the adapter sets,
  `{'timeout': 900}` extra in the Pi entry, `cannot express timeout` where the generic message was
  expected). That is the RED signal for the change.
- **GREEN (measured):** the same files → `370 passed, 3 skipped`, and the focused selection
  `-k "Timeouts or timeout"` → `16 passed`.

The three config keys and the adapter capabilities were also exercised end to end through
`sofer mcp add` in a subprocess (`test_parser_rejects_a_non_positive_timeout`,
`test_add_help_documents_the_timeout_flags`, `test_pi_add_project_writes_dot_pi_and_env`), so the
public boundary is covered and not only the helpers.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | Writing keys into files outside the repository. | **Med** | Namespaced under the `sofer` server name only, so no other server changes; the preserve-others, `.bak`, atomic-write and dry-run contracts are re-asserted by existing tests plus two new ones; `--no-timeout` opts out. |
| R2 | A host rejects the entry because the key name or unit is wrong. | **Med** | Each key/unit is sourced in §2 and recorded in the adapter comment; opencode is excluded rather than guessed. |
| R3 | The heartbeat leaks into a host that did not ask for progress. | Low | `Context.report_progress` returns without sending when no progress token is present. |
| R4 | Writing a timeout by default ends codex/gemini native delegation. | **Med** | Accepted and made explicit: fixed by `--no-timeout`, which restores the pre-change entry shape and the delegation path, and asserted by a dedicated test. |
| R5 | `--timeout` changes look idempotent and never rewrite. | Low | `_timeout_keys_equal()` closes it; `test_changed_timeout_is_not_swallowed_by_the_idempotency_guard` and its CLI twin assert it. |

## 6. Rollback

Revert-only: restoring `build_entry`'s signature, the `ADAPTERS` entries, the gate, the three CLI
flags, the three config keys and the two test files restores the previous behaviour exactly. No state,
no migration. A config already carrying the timeout keys stays valid — they are additive keys the host
reads on its own.
