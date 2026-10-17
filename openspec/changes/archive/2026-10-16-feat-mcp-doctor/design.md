# Design — `2026-10-16-feat-mcp-doctor`

> **Change** `2026-10-16-feat-mcp-doctor` (issue **#322**) · branch `feat/322-mcp-doctor` from
> `dev@24520b6` · store **hybrid**.

---

## 1. The defect, precisely

`sofer mcp add` writes a connect deadline from `[tool.sofer] mcp_connect_timeout_seconds` (default
120 s). That default was chosen against a *quoted* measurement — the 16–32 s the `mcp-registration` spec
and the README record — not against a measurement of the machine that carries the entry. Two failure
shapes follow:

- a host slower than the one the figure came from, where the entry's value is still too small; and
- a host where a dependency lands in the import path and the cold start moves after the value was
  written.

Both surface to the user as a host connect timeout, which is indistinguishable from a broken
registration. Nothing in the CLI could measure the real launch, so the only available value was the
configuration default — a value, not a measurement.

## 2. Why a new module rather than more of `cli.py` or `mcp_registration.py`

AGENTS.md rule 10 is one module per concern. The concern here is a *launch measurement*: it is not
registration (it writes nothing), and it is not CLI dispatch. A separate module also makes the transport
injectable, which is what keeps rule 14's 100.00% `cli.py` mandate reachable: every handler branch is
covered without a real subprocess per branch, while one deliberate test still spawns the real server.

The module imports no MCP SDK. Without the optional `mcp` extra the child cannot start — and *that is a
result*, not an error condition: a doctor that refused to load without the dependency it diagnoses would
be useless in exactly the case that matters. The extra is required by the child, never by this module.

## 3. The measurement

### 3.1 Framing and the deadline

Before writing any code, the real handshake was probed (`tmp/probe_initialize.py`, a throwaway script
under a gitignored directory): write one JSON-RPC `initialize` request as a single line, read one line
back. The server answers with a valid `result` and no `Content-Length` headers. That settled the
transport without a guess, and produced a baseline: **1874 ms and 1718 ms** on this machine, twice.

A `threading.Timer` kills the child at the deadline. That makes the blocked `readline()` return empty,
so the deadline becomes a *reported failure* rather than a hang — and it is portable, unlike a
`select`-based read, which the Windows matrix would defeat.

The child is killed in a `finally` for every path, and its stderr is quoted (bounded) when it fails to
answer: "the server could not start, and here is why" is the single most useful thing this command can
say.

### 3.2 The row model — a wrong premise, corrected

The first draft of the tests assumed one timeout key per agent. The adapter table says otherwise:

| Agent | request key | connect key | unit | what `mcp add` writes |
| --- | --- | --- | --- | --- |
| opencode | — | — | — | `{}` (MCP-REG-05 note) |
| codex | `tool_timeout_sec` | `startup_timeout_sec` | seconds | 900 / 120 |
| gemini | `timeout` | — | **milliseconds** | 900000 |
| pi | `timeout` | — | seconds | 900 |
| hermes | `timeout` | `connect_timeout` | seconds | 900 / 120 |

So the cold-start key is `connect_timeout_key or timeout_key`, the row must carry the adapter's own
unit, and pi's and gemini's single key receives the *request* value — which is what that key covers,
since neither declares a separate connect deadline. A row that reported "one key, one value in seconds"
would have been wrong for three of the five agents. The correction is recorded here rather than folded
silently into the tests, and the model is now pinned by
`test_the_row_value_matches_what_mcp_add_would_write`, which compares every row against
`timeout_entry_keys` rather than re-deriving it.

## 4. Decisions

| # | Decision | Rationale |
| --- | --- | --- |
| D1 | Exceeding the budget keeps exit code 0; only an unmeasurable launch exits 1. | The repository's own contract for this class of message: `dropped_timeout_note` and the OpenCode env-drop warning are informational and never change the exit code (MCP-REG-03, MCP-REG-05). A slow machine is not a broken registration; an exit code that said so would recreate the confusion the issue exists to remove. |
| D2 | The measurement lives in `src/sofer/mcp_doctor.py`. | §2. |
| D3 | Measure the `initialize` round trip, never import time. | The host deadline covers connect *and* handshake (issue #322 §"Proposed solution" 1). |
| D4 | `doctor` gains no `--root` flag; it inherits the environment and the process cwd, so the child resolves its own root exactly as a host launch would. | The issue fixes the surface as `[--agent] [--json]` and requires the *child* to honour the root. Inheriting is stronger than forwarding: the doctor cannot alter the launch it is measuring, and MSP-R01 stays the child's contract, un-duplicated. |
| D5 | `--json` emits the CLI-R10 stable-key object. | CLI-R10 requires machine-readable status to be stable JSON carrying `ok` / `exit_code` / `message`, never a `repr`. The doctor's own keys are added to it, not substituted for it. |
| D6 | No `--agent` means every registered agent; `--agent <name>` restricts it. | The issue makes `--agent` optional, and "the per-agent key and the value `sofer mcp add` would write" is a per-agent fact — a single number is only meaningful beside the key that receives it. |

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | The measurement's own wall clock is noisy, so a machine near the budget flips verdicts. | Low | The verdict is informational (D1), and the number printed is the measurement, not a pass/fail. |
| R2 | A future server rejects the client's `protocolVersion`. | Low | The server negotiates; a refusal arrives as a non-`result` answer and is reported with the child's stderr, not swallowed. |
| R3 | The real-spawn test is slow or flaky in CI. | Low | One spawn, ~2 s measured, well inside the harness budget; the transport is injected everywhere else. |
| R4 | The module grows an accidental MCP SDK import and breaks `sofer mcp doctor` without the extra. | Medium | §2 names the constraint; the module's import list is stdlib plus two package modules. |
| R5 | The report's rows drift from what registration writes. | Low | Values come from `timeout_entry_keys` only, and a test compares every row against it. |

## 6. Deliberately out of scope: the 16–32 s figure

The issue's premise is the cold start, and the specs quote 16–32 s as the measured figure. This change
measured **1.7–1.9 s** on its own machine, twice. That is recorded in `odd/tasks/mcp-doctor.md` as a
finding and **not** used to edit the figure: two runs on one machine with a warm page cache cannot
falsify a figure that may have been taken cold, on slower hardware, or before a dependency left the
import path. Revising a measurement that a spec states as fact needs its own measurement — cold cache,
and ideally a second machine — which is a separate change. Changing the sentence from a value this
change did not reproduce would be exactly the defect class rule 15 is written about.

## 7. Rollback

Revert-only: delete the module and the test file, drop the subparser and the handler, and the CLI returns
to its previous surface. No state, no migration, no config rewrite — the command never wrote a file.
