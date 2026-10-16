# Proposal — `2026-10-16-fix-mcp-registration-timeouts`

> **Change** `2026-10-16-fix-mcp-registration-timeouts` · issues **#287** + **#296** · branch
> `fix/287-296-mcp-registration-timeouts` from `dev@6786ba1` · store **hybrid** (this file + the
> Engram mirror).
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

`sofer mcp add --agent <agent>` writes `command`, `cwd` and (where the agent supports it) `env`, and
nothing that bounds **how long the host waits**. Two independent deadlines then fail against hosts'
defaults, and both surface the same way — indistinguishable from a broken registration:

1. **Cold start (#287).** `sofer-mcp` imports pandas, pyarrow, datasets and fastmcp before it can
   answer `initialize`. Measured 16–32 s on the first launch after an install or upgrade (empty
   bytecode cache, cold page cache), against hosts' default connect/startup deadlines. The host
   reports `Connection failed … timed out`, and raising its per-server timeout fixes it — which is
   the only way a user can tell the difference.
2. **Per-request deadline (#296).** `sofer_prepare` ran ~680 s on a 3.2 GB / 66.2 M-row corpus and
   `sofer_codebook_all` ~100 s, against a documented 60 s host default. The server does **not** stop:
   it finishes, writes its artifacts, and the response is discarded. The caller loses `next`,
   `error_code` and the diagnostics, and cannot distinguish "failed" from "succeeded but unheard".

The fix has three parts, and all three are needed:

- **Write the deadline.** The entry carries the host's per-request and connect/startup keys, with the
  key name and unit declared per agent in `ADAPTERS` — the same single-source rule as env forwarding.
- **Say what the host must accommodate.** The agent-setup section documents the cold start and names
  the calls expected to run for minutes.
- **Reset the deadline instead of only raising it.** Long tools emit progress notifications, so a
  tool survives a default the user cannot raise.

## 2. Scope

### In scope

- `src/sofer/mcp_registration.py`: `Timeouts`, `timeout_entry_keys()`, the four new `ADAPTERS`
  capabilities, `build_entry()` writing the keys, `_entries_equal()` comparing them,
  `dropped_timeout_note()`, and the `timeout` decline reason in `native_delegation_decline_reasons()`.
- `src/sofer/cli.py`: `--timeout` / `--connect-timeout` / `--no-timeout` on `mcp add`, the
  `_positive_seconds()` argparse type, and the wiring of both the delegation gate and the note.
- `src/sofer/config.py`, `pyproject.toml`: `mcp_request_timeout_seconds`,
  `mcp_connect_timeout_seconds`, `mcp_progress_heartbeat_seconds` in both homes (parity guard).
- `src/sofer/mcp_server.py`: a progress heartbeat around the long tools' bodies, plus `Runs for
  minutes:` lines in the tool descriptions.
- `openspec/specs/mcp-registration/spec.md`: the new requirement and its scenarios.
- `README.md`, `README_ES.md`: the cold start, the per-agent timeout table and the long-call
  expectation.

### Out of scope

- **Making `sofer-mcp` start faster** (lazy imports). Named in #287 as the real root fix; a larger
  change, and it does not help anyone on an older version.
- **Returning written artifact paths in a form that survives a dropped response** (#296 §4). The
  envelope is the contract this change repairs; the manifest already helps.
- **Writing a timeout for opencode.** Its published schema drifted between releases (see
  `design.md` §2). The README names the manual key.

## 3. Approach

Per-agent capabilities, not per-agent branches. `ADAPTERS` already answers "what can this host
express?" for env and scope; the timeouts join it as `timeout_key`, `connect_timeout_key`,
`timeout_unit` and `native_timeout`. Every consumer — `build_entry`, the idempotency comparison, the
delegation gate, the CLI note — reads those fields and has no host-specific branch of its own.

The values are `[tool.sofer]` defaults read at the call site (AGENTS.md rule 1), overridable per
invocation, and omittable with `--no-timeout`. That last flag is not decoration: with a timeout
written by default, the native codex/gemini delegation gate declines (neither `codex mcp add` nor
`gemini mcp add` takes a timeout flag), so `--no-timeout` is what keeps delegation reachable.

## 4. Success criteria

- SC-1: `sofer mcp add --agent <pi|hermes|codex|gemini>` writes the host's timeout keys with the
  right names and unit; opencode's entry is unchanged and its reason reaches stderr.
- SC-2: re-running with the same values writes nothing and creates no `.bak`; changing `--timeout`
  rewrites and backs up.
- SC-3: with a timeout requested, codex/gemini delegation declines with the `timeout` reason and the
  file edit runs; with `--no-timeout`, delegation proceeds exactly as before.
- SC-4: a long tool re-announces progress while it runs, so a client that requested a progress token
  keeps its request alive.
- SC-5: the agent-setup docs name the cold start, the per-agent key and the long calls.
- SC-6: the full gate set is green, with `cli.py` still at 100.00% line coverage.
