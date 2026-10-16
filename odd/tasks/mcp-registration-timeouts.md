# Feature: mcp-registration-timeouts — issues #287 + #296

**Branch:** `fix/287-296-mcp-registration-timeouts` from `dev@6786ba1`. **Issues:** `emiliodavola/sofer#287`, `emiliodavola/sofer#296`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-fix-mcp-registration-timeouts/`
(archived inside this PR, AGENTS.md rule 15). **Milestone:** v0.6.0 — agent surface & card completeness.
**Risk:** medium — the entry written into every user's agent config gains keys. Additive and
documented (the Task Size rule excludes an added optional field from high risk), but the write path
reaches files outside the repository, so the idempotency and preserve-others contracts are re-asserted.

## Goal

`sofer mcp add --agent <agent>` writes `command`, `cwd` and (where the agent supports it) `env`, and
nothing that bounds how long the host waits. Two distinct deadlines then fail against hosts' defaults
and both surface as `Connection failed` / `request timed out` — indistinguishable from a broken
registration:

- **cold start** (#287): `sofer-mcp` imports pandas, pyarrow, datasets and fastmcp before it can answer
  `initialize`; measured 16–32 s on a first launch after an install or upgrade, against hosts' default
  connect/startup deadlines.
- **per-request deadline** (#296): `sofer_prepare` ran ~680 s on a 3.2 GB / 66.2 M-row corpus and
  `sofer_codebook_all` ~100 s, against a documented 60 s host default. The server finishes the work and
  writes its artifacts; the **envelope is discarded**, so the caller cannot distinguish "failed" from
  "succeeded but unheard" and loses `next`, `error_code` and the diagnostics.

Both close with the same three-part shape: write the per-host timeout key into the entry, say what the
host must accommodate, and emit progress notifications so a long tool survives a deadline it cannot
raise.

## Host schemas (researched, not guessed)

| Agent | per-request key | connect/startup key | unit | defaults in the host |
| --- | --- | --- | --- | --- |
| pi | `timeout` | — (background connect) | seconds | 60 (progress notifications reset it) |
| hermes | `timeout` | `connect_timeout` | seconds | 300 / 60 |
| codex | `tool_timeout_sec` | `startup_timeout_sec` | seconds | 60 / 10 |
| gemini | `timeout` | — (same key covers discovery) | **milliseconds** | 600 000 |
| opencode | `timeout` (nested `{startup, catalog, execution}`) | same object | **milliseconds** | 30 000 / 30 000 / 12 h |

Sources: Pi `docs/mcp.md`; Hermes "MCP Config Reference"; Codex Configuration Reference and
`codex-rs/core/src/config/types.rs`; gemini-cli `packages/core/src/tools/mcp-client.ts`
(`MCP_DEFAULT_TIMEOUT_MSEC`); opencode "MCP servers" (v2 docs) plus its `config/mcp.ts` zod schema.

**opencode is excluded (decision D5).** Its published schema drifted between releases: the zod
`ConfigMCP.Local` declares `timeout` as a positive integer while the current docs declare a nested
object in milliseconds. Writing the wrong shape risks failing validation of the whole `mcp` block, and
opencode's own defaults (12 h execution) are not the ones that break. The adapter declares no timeout
keys and the README names the manual key with its reason.

## Specs

S1 (issue #287 §"Proposed solution" 2, verbatim): "**Optionally write it:** for hosts whose entry schema
accepts a connect timeout, let the adapter emit it (`--connect-timeout` flag, or a documented default for
`sofer-mcp` entries). This is per-agent by nature — a `native_connect_timeout` capability in `ADAPTERS`
next to `native_env`/`native_scope` would keep the registry the single source of truth."

S2 (issue #296 §"Proposed solution" 1, verbatim): "**Write the timeout into the registration entry**
where the host supports it (Pi's `mcp.json` accepts a per-server `timeout`; other hosts have
equivalents), or document the exact key per agent next to the existing per-agent `env` facts."

S3 (issue #287 §"Proposed solution" 1, verbatim): "**Document the cold start** in the agent-setup
section: a first launch can take tens of seconds (measured 16–32s here) while the heavy imports warm
up; if the host reports a connect timeout, raise its per-server connect timeout rather than assuming the
registration failed."

S4 (issue #296 §"Proposed solution" 2, verbatim): "**Document the expectation** in the tool
descriptions: which `sofer_*` calls are expected to run for minutes on a large dataset (`prepare`,
`codebook_all`, `profile_all`, `render_all`, `publish_confirm`) and that the host timeout must
accommodate them."

S5 (issue #296 §"Proposed solution" 3, verbatim): "**Emit progress notifications**, which reset the host
deadline per the Pi docs, so a long tool survives the default instead of requiring configuration. This
also helps on hosts whose timeout is not user-configurable."

S6 (issue #287 §"Proposed solution" 3, verbatim): "**Optional diagnostic aid:** `sofer doctor`/`sofer mcp
doctor` that measures the cold start and prints the value the host should be configured with."

S7 (derived from S1+S2): the timeout keys SHALL NOT break the written contracts — re-running the same
command SHALL stay byte-identical (no write, no `.bak`), the entry SHALL stay namespaced under the
`sofer` server name so no other server in the file is touched, and `--dry-run` SHALL still write nothing.

S8 (derived from S1): when the native `mcp add` cannot express the timeout the file edit writes, the
delegation gate SHALL decline with a named reason instead of delegating and losing the values.

## Decisions not in the issues

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The timeout values are `[tool.sofer]` defaults (`mcp_request_timeout_seconds` = 900, `mcp_connect_timeout_seconds` = 120) read through `config.py`, never literals. | AGENTS.md rule 1. 900 s covers #296's measured 680 s `prepare` with margin while staying under every host's own ceiling; 120 s is ~4× the measured 32 s cold start. |
| D2 | `--timeout` / `--connect-timeout` override per invocation; `--no-timeout` omits both keys. | S1 asks for a flag. `--no-timeout` restores the pre-change entry shape exactly, which is also what keeps native delegation reachable (D4) — without it, writing a timeout by default would silently end codex/gemini delegation. |
| D3 | gemini's single `timeout` key receives `max(request, connect)` in milliseconds. | gemini's `timeout` bounds tool discovery **and** tool calls (`discoverTools(..., timeout: serverConfig.timeout ?? MCP_DEFAULT_TIMEOUT_MSEC)`), so one value must serve both; the smaller would kill a long call, the larger only delays a hung connect. |
| D4 | A new `native_timeout` capability in `ADAPTERS` (`False` for codex and gemini) makes the delegation gate decline with reason `timeout`. | S1's own words ("a `native_connect_timeout` capability in `ADAPTERS`") and the existing `native_env`/`native_scope` pattern. `codex mcp add` and `gemini mcp add` accept no timeout flag, so delegating would drop the values. |
| D5 | opencode declares no timeout keys; the README names the manual key and the reason. | See "Host schemas" above: the shape is unstable across releases and its own defaults are not the failing ones. |
| D6 | Progress notifications are emitted by a **heartbeat** around the existing synchronous body, not by threading a callback through every domain function. | S5 needs the deadline reset, not a percentage. The body already prints to captured stdout; a heartbeat task (`asyncio.to_thread` + periodic `ctx.report_progress`) needs no change to `prepare`/`codebook`/`profile`/`render`/`publish` and keeps the single-writer `_EXEC_LOCK` in a worker thread, where holding it cannot block the event loop. |
| D7 | `sofer mcp doctor` measures the real cold start with one `initialize` round trip in a `sofer-mcp` subprocess, then prints the per-agent key and the measured-derived value. | S6. Import timing would measure the wrong thing (the host's deadline covers connect **and** handshake); the subprocess is the actual launch. |

## Non-goals

- Making `sofer-mcp` start faster (lazy imports). Named in #287 as the real root fix and out of scope.
- Returning written artifact paths in a dropped-response-surviving form (issue #296 §4, "the manifest
  already helps"). The envelope is the contract this change repairs.
- Writing timeouts into a shared, non-namespaced host block (opencode's `mcp.timeout` defaults), which
  would change other servers' behaviour.

## Tasks

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Feature doc + branch off `dev` | — | parent | pending | |
| T2 | RED: entry-shape, `--no-timeout`, idempotency and delegation-gate tests | S1 S2 S7 S8 | parent | pending | |
| T3 | `config.py` + `pyproject.toml`: the two new `[tool.sofer]` defaults, both homes (parity guard) | D1 | parent | pending | |
| T4 | `ADAPTERS`: `timeout_key`, `connect_timeout_key`, `timeout_unit`, `native_timeout` for all five agents | S1 D4 D5 | parent | pending | |
| T5 | `build_entry` writes the keys; `_entries_equal` compares them so a changed `--timeout` rewrites | S1 S2 S7 | parent | pending | |
| T6 | `native_delegation_decline_reasons` gains the `timeout` reason | S8 D4 | parent | pending | |
| T7 | CLI: `--timeout`, `--connect-timeout`, `--no-timeout` + help text | S1 D2 | parent | pending | |
| T8 | `mcp-registration` spec delta (the requirement + scenarios) | S1 S2 S7 S8 | parent | pending | |
| T9 | RED+GREEN: heartbeat progress notifications on the long tools | S5 D6 | parent | pending | |
| T10 | `sofer mcp doctor` subcommand + its tests | S6 D7 | parent | pending | |
| T11 | Tool descriptions name the long calls and the deadline; `mcp-server` spec delta | S4 | parent | pending | |
| T12 | README + README_ES: cold start, per-agent timeout table, long-tool expectation | S3 S4 | parent | pending | |
| T13 | Gates: full suite, per-file coverage on `cli.py`, ruff/format/mypy/pyright, test-mapping checker | — | parent | pending | |
| T14 | Work-unit commits on the branch (no push, no PR) | — | parent | pending | |

## Log

L1 (user request, verbatim): "revisá los issues pendientes, chequeá que sea correcto lo que reportan y
armá un roadmap de implementación"

L2 (user request, verbatim): "dale persistilo y convertilo en un milestone en github

arrancá la implementación, llevala hasta el final para cada issue pero no hagas push y PR, eso lo
hacemos mañana"

L3 (maintainer decisions): D1 #291 → add the `[meta]` keys. D2 #296 → timeout, docs and progress
notifications in one change (no separate 1b). D3 #288 → `warn`. D4 #306 → 5 M rows locally plus the
recipe for the large run.
