# Feature: mcp-doctor — issue #322

- **Issue:** [#322](https://github.com/emiliodavola/sofer/issues/322) — `feat(cli): add sofer mcp doctor - measure the cold start and print the per-agent timeout value`
- **Branch:** `feat/322-mcp-doctor` from `dev@24520b6` (after #331 merged) · **Change:** `openspec/changes/archive/2026-10-16-feat-mcp-doctor/`
- **Spec of record:** `openspec/specs/cli/spec.md` (CLI-R02, CLI-R09, CLI-R10) and `openspec/specs/mcp-registration/spec.md` (MCP-REG-05). This file is the working plan behind them.

## Goal

PR #311 writes each host's connect/startup deadline into the registration entry, from a value chosen
against a *measurement* (16–32 s) rather than a measurement of **this** machine. On a slower host, a cold
container, or after a dependency lands in the import path, the written value can be too small and the
failure is indistinguishable from a broken registration — the exact symptom #287 exists to remove. #322
files the diagnostic PR #311 deliberately left out (its archive report §5).

Deliverable: `sofer mcp doctor [--agent <agent>] [--json]` — spawn the real `sofer-mcp`, time the stdio
`initialize` round trip, and print the measurement beside the per-agent key and the value `sofer mcp
add` would write.

## Specs

S1 (issue #322 §"Proposed solution" 1, verbatim): "`sofer mcp doctor [--agent <agent>] [--json]`, measuring the real launch: spawn `sofer-mcp` and time the `initialize` round trip over stdio (import timing measures the wrong thing — the host's deadline covers connect **and** handshake). Then print the measured milliseconds alongside the per-agent key and the value `sofer mcp add` would write, so the user can compare and, if the measurement exceeds it, raise `--timeout` / `--connect-timeout`."

S2 (issue #322 §"Proposed solution", constraints, verbatim): "a new subcommand is CLI surface: `argparse` help text, README + README_ES, and `cli.py` is one of the four modules under the rule-14 100.00% line-coverage mandate".

S3 (issue #322 §"Proposed solution", constraints, verbatim): "`--root` / `SOFER_MCP_ROOT` must be honoured in the spawned child, and the containment contract (`MSP-R01`) applies to anything the command resolves".

S4 (issue #322 §"Proposed solution", constraints, verbatim): "if `sofer-mcp` is not on `PATH` (an uninstalled checkout), fall back to the module entry point or fail with a message naming both".

S5 (issue #322 §"Problem", verbatim): "On a slower host, a cold container, or after a dependency lands in the import path, the written default can be too small and the failure looks exactly like a broken registration again."

S6 (`openspec/specs/cli/spec.md` CLI-R10, verbatim): "CLI status output that is machine-readable SHALL be stable JSON, not a Python dictionary `repr`."

S7 (`openspec/specs/cli/spec.md` CLI-R09, verbatim): "`sofer` MUST expose `mcp` with `add`/`remove`."

S8 (`openspec/specs/mcp-registration/spec.md` MCP-REG-05, verbatim): "An agent whose entry schema accepts no timeout key SHALL keep an entry without one, and `add` SHALL name that on stderr rather than reporting a clean success".

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The exit code is **0 even when the measurement exceeds the budget**. Only an unspawnable entry point exits 1. | The repository's own contract for this class of message: `mcp_registration.dropped_timeout_note` and the opencode env-drop warning are "informational only — it never changes the exit code" (MCP-REG-03, MCP-REG-05). A slow machine is not a broken registration, and an exit code that says so re-creates the confusion S5 names. |
| D2 | The measurement lives in a new module, `src/sofer/mcp_doctor.py`; `cli.py` only parses, calls and prints. | AGENTS.md rule 10 (one module per concern): the concern is a launch measurement, not registration (`mcp_registration.py`) nor dispatch (`cli.py`). It also keeps rule 14's 100.00% `cli.py` gate reachable without real subprocesses in every branch: the spawn is an injected callable. |
| D3 | Measure the `initialize` **round trip**, never import time. | S1 says so and gives the reason: the host's deadline covers connect **and** handshake. |
| D4 | `doctor` gains **no `--root` flag**, and it does not resolve or forward a root either: it inherits the environment and the process cwd, so the child applies MSP-R01 itself. | S1 fixes the flag surface as `[--agent] [--json]`; S3 requires the child to honour the root, not that `doctor` add a flag. Inheriting is **stronger** than forwarding: the doctor cannot alter the launch it is measuring, and the documented precedence is not re-derived or duplicated from `mcp_server._resolve_root`. Recorded as a correction — see L11. |
| D5 | `--json` emits the CLI-R10 stable-key object (`ok`, `exit_code`, plus the doctor's own keys), never a `repr`. | S6. The doctor's own keys are added to that object, not substituted for it. |
| D6 | With no `--agent`, the report covers every registered agent; with `--agent`, only that one. | S1's signature makes `--agent` optional, and S1's "the per-agent key and the value `sofer mcp add` would write" is a per-agent fact — a single number is only meaningful beside the key that receives it. opencode's row is the note from MCP-REG-05 (S8), not a fabricated value. |

## Tasks

| ID | Task | Spec | Route | State |
| --- | --- | --- | --- | --- |
| T1 | Branch off `dev@24520b6` | — | git | done |
| T2 | Feature doc + change folder (this file) — before the first source edit | — | inline | done |
| T3 | Probe the real stdio handshake empirically (framing + a real baseline number) | S1 | inline | done |
| T4 | RED: `tests/test_mcp_doctor.py` (35 tests, transport injected + one real spawn) | S1 S2 S3 S4 S6 | inline, test-first | done |
| T5 | `src/sofer/mcp_doctor.py` | S1 S3 S4 S6 | inline | done |
| T6 | `cli.py`: the `doctor` parser, its help, and `_cmd_mcp_doctor` | S2 S7 | inline | done |
| T7 | Specs: `cli` (CLI-R09 extended + CLI-R15 added) and `mcp-registration` (MCP-REG-05 diagnostic) | S1–S8 | inline | done |
| T8 | README + README_ES: the subcommand row and its flags (rules 7, 13) | S2 | inline | done |
| T9 | Gates: full suite, `cli.py` at 100.00% (rule 14), ruff/format/mypy/pyright, test-mapping | — | inline | done |
| T10 | Archive inside the delivery branch (rule 15); ROADMAP Batch B row | — | inline | done |

## Log

L1 (user, verbatim): "de que autorice el PR seguimos con #322"

L2 (user, verbatim, the original authorization for this batch): "1. Arrancá con #324\n2. arreglalo antes de comenzar si corresponde"

L3 (user, verbatim, the PR authorization): "hacé el PR"

L4 (evidence, recon): #322's premise holds — no `doctor` subcommand exists (`mcp_sub` has `add` and `remove` only), no measurement code exists anywhere, and the timeout values come from `config.MCP_CONNECT_TIMEOUT_SECONDS` (120) / `MCP_REQUEST_TIMEOUT_SECONDS` (900) via `[tool.sofer]`.

L5 (evidence, obligations): `cli`, `mcp-registration` and `mcp-server` are permanent declared-backlog specs (`openspec/test-mapping-registry.md`), so this change adds no `## Test Mapping` table and no registry edit; only `ci`, `coverage` and `process-boundary` are mapped.

L6 (user, verbatim): "autoricé el PR, ahora rebasá y luego continuá con el issue #324"

L7 (evidence, that instruction's outcome): #324 was already **MERGED and CLOSED** by then, so the only actionable part was the sync — the branch rebased (fast-forward, no history rewrite) and local `dev` fast-forwarded from `5249be6` to `24520b6`. #324 has no remaining work. The two parked #322 files were then unparked after the user selected "Seguí con #322" in the follow-up question, and this branch was created for real (the first draft of this file claimed a branch that did not exist yet — the claim is now true and the ordering is recorded in L9).

L8 (evidence, RED→GREEN): against a skeleton carrying the full public surface with `NotImplementedError` bodies, `uv run pytest tests/test_mcp_doctor.py -q` → **35 failed** — a per-behaviour failure, not a collection `ImportError`. After the module and the subparser landed: **35 passed**.

L9 (correction): the first draft of the tests assumed one timeout key per agent. The adapter table says otherwise — codex (`tool_timeout_sec` + `startup_timeout_sec`) and hermes (`timeout` + `connect_timeout`) write two, gemini's single `timeout` is in **milliseconds**, and pi's single `timeout` receives the *request* value. The row model became `connect_timeout_key or timeout_key` carrying the adapter's own unit, and every row is now compared against `timeout_entry_keys` rather than re-derived. A wrong premise of mine, recorded instead of folded silently into the tests.

L10 (evidence, lint and types): `ruff check src/ tests/ scripts/` → `All checks passed!`; `ruff format --check src/ tests/` → 77 files already formatted; `mypy src/ scripts/` → no issues in 39 source files; `pyright` → 0 errors. Two findings fixed on the way: `int(round(...))` (RUF046) and an `Any` return in `_stderr_tail` where mypy could not keep the attribute narrowing.

L11 (deviation, recorded): D4 as first written said the doctor resolves the root and passes `--root` to the child. The implementation deliberately does **neither** — it inherits the environment and the process cwd, so the child applies MSP-R01 itself and the doctor cannot alter the launch it is measuring. D4 was rewritten to match the code rather than the code bent to match the plan.

L12 (decision): this change does **not** touch the 16–32 s cold-start figure the specs and README record, even though it measured 1.7–1.9 s here (two runs, warm page cache). Two runs on one machine cannot falsify a figure that may have been taken cold or on slower hardware; revising a stated measurement needs its own measurement. Parked as its own item, and named in `design.md` §6 so the omission is deliberate and visible.

L13 (evidence, full gate set): `uv run coverage run -m pytest tests/ -q` → **2282 passed, 9 skipped** (105.08 s) — `+35` over the 2247 that `dev@24520b6` measured before this change, which is exactly the 35 new tests. `scripts/check_core_coverage.sh` → `cli.py` 675 stmts / 204 branch / **0 missed / 100%**, and scanner / prepare / publish at 100% each. `coverage report -m` → TOTAL **94%** (floor 90). `scripts/check_test_mapping.py` → `OK`. And the command itself, run by hand: **1806 ms**, exit 0, all five agent rows correct (opencode's note, `startup_timeout_sec = 120 seconds`, `timeout = 900000 milliseconds` for gemini, `timeout = 900 seconds` for pi, `connect_timeout = 120 seconds` for hermes).
