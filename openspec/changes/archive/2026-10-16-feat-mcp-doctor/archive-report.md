# Archive report — `2026-10-16-feat-mcp-doctor`

> **Change** `2026-10-16-feat-mcp-doctor` · issue **#322** · branch `feat/322-mcp-doctor` from
> `dev@24520b6` · milestone **v0.7.0 — follow-up defects from the v0.6.0 batch**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

`sofer mcp doctor` measures the **real** launch of `sofer-mcp` — spawn it, time the stdio `initialize`
round trip — and prints that measurement beside the per-agent entry key and the value `sofer mcp add`
would write there. It is the diagnostic half of #287 that PR #311 deliberately left out (its archive
report §5).

| Requirement | Where |
| --- | --- |
| CLI-R09 extended — `doctor` joins the `mcp` children | `openspec/specs/cli/spec.md` |
| CLI-R15 added — the measured cold start and the deadline to configure (8 scenarios, inline `test:` evidence) | `openspec/specs/cli/spec.md` |
| MCP-REG-05 extended — the written value is checkable against this machine | `openspec/specs/mcp-registration/spec.md` |
| Entry-point resolution, the measurement, the rows, the report | `src/sofer/mcp_doctor.py` (new, 487 lines) |
| The `doctor` subparser, its help, `_cmd_mcp_doctor` | `src/sofer/cli.py` |
| 35 tests | `tests/test_mcp_doctor.py` (new, 373 lines) |
| The subcommand row and its two flags, in both READMEs | `README.md`, `README_ES.md` |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T11). No `pending` row remains.

## 3. Measured evidence

| Gate | Command | Result |
| --- | --- | --- |
| Failing-on-RED | `uv run pytest tests/test_mcp_doctor.py -q` against the `NotImplementedError` skeleton | **35 failed** — a per-behaviour failure, not a collection `ImportError` |
| Focused GREEN | same command after the module and the subparser | **35 passed** |
| Full suite | `uv run coverage run -m pytest tests/ -q` | **2282 passed, 9 skipped** (105.08 s) |
| Suite delta | 2247 passed before this change (measured on `dev@24520b6` for #324) | **+35**, exactly the 35 new tests; collection 2256 → 2291 |
| `cli.py` 100.00% (rule 14) | `bash scripts/check_core_coverage.sh` | **675 stmts / 204 branch / 0 missed / 100%** |
| `scanner.py` / `prepare.py` / `publish.py` (rule 14) | same script | **100%** each |
| TOTAL floor | `uv run coverage report -m` | **94%** (≥ 90, spec `ci` CI-01) |
| Lint / format | `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/` | `All checks passed!` / 77 files already formatted |
| Types | `uv run --python 3.13 mypy src/ scripts/`, `uv run pyright` | 0 errors / 0 errors (1 pre-existing `tomli` warning in `_toml.py`) |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK` |
| The command itself | `uv run sofer mcp doctor` | **1806 ms** measured, exit 0, all five agent rows correct — see §5.1 |
| Delivery | `git show --stat c683d29` | 15 files changed, **+1644 / −6**, all four pre-commit hooks `Passed`; pushed, `origin/feat/322-mcp-doctor` verified equal to local |
| Pull request | — | **#332**, open against `dev`, label `type:feature`, assigned to `emiliodavola` |

The suite delta is arithmetic, not reconciliation: 2247 + 35 = 2282 passed, and 2256 + 35 = 2291
collected.

## 4. Decision recorded

**D1 — the exit code stays 0 when the measurement exceeds the budget; only an unmeasurable launch
exits 1.** The repository's own contract for this class of message: `dropped_timeout_note` and the
OpenCode env-drop warning are informational and never change the exit code (MCP-REG-03, MCP-REG-05). A
slow machine is not a broken registration, and an exit code that said otherwise would recreate the very
confusion the issue exists to remove.

D2–D6 (the module split, the round trip, no `--root`, CLI-R10 JSON, the no-`--agent` default) are
recorded in `design.md` §4.

## 5. Deviations and findings, stated

1. **The row model was wrong in the first draft.** It assumed one timeout key per agent. The adapter
   table says codex and hermes write two, gemini's single key is in **milliseconds**, and pi's single
   key receives the *request* value. The model became `connect_timeout_key or timeout_key` carrying the
   adapter's own unit, and every row is now compared against `timeout_entry_keys`. A wrong premise of
   mine, recorded rather than folded silently into the tests (`design.md` §3.2).
2. **D4 was rewritten to match the code, not the reverse.** As first written it said the doctor resolves
   the root and passes `--root` to the child. The implementation deliberately does neither: it inherits
   the environment and the process cwd, so the child applies MSP-R01 itself and the doctor cannot alter
   the launch it is measuring. The plan was corrected; the code was not bent to the plan.
3. **Running the command found something the tests could not.** The em dashes in the new human output
   render as `�` in a cp1252 console. Verified **not** to be a new defect: `cli.py` and `prepare.py`
   already emit non-ASCII glyphs, the pre-existing OpenCode note (`mcp_registration.py:1085`) uses a
   literal em dash, and CLI-R11 requires visible substitution rather than a crash — which is what
   happened (exit 0, the rest of the output intact). Left unchanged and recorded.
4. **Two lint/type defects of mine, fixed before the gates ran clean.** `int(round(...))` (RUF046) and
   an `Any` return in `_stderr_tail` where mypy could not hold the attribute narrowing.
5. **The 16–32 s figure was removed from both READMEs; it stands everywhere else.** The maintainer's
   instruction was to stop measuring it and to drop it from the README if it was not doing work — and it
   was not: what a user needs is the *reason* a connect deadline is written (a first launch after an
   install or upgrade is slower than a warm one, and a connect timeout reads exactly like a broken
   registration), while the numbers are a measurement of one environment stated as a general fact. This
   change also ships `sofer mcp doctor`, which prints ~1.8 s on this machine: a README asserting 16–32 s
   beside a command printing 1800 ms makes the user trust neither. Both READMEs now carry the reason, a
   pointer at the command, and the statement that the written value comes from `[tool.sofer]` rather
   than from a number frozen in a document.

   The figure is **still asserted** in `pyproject.toml:238`, `src/sofer/config.py:150`,
   `src/sofer/mcp_registration.py:288` and `openspec/specs/mcp-registration/spec.md:395` — the last of
   which is the contract of record. Those are reported rather than changed: the spec asserts a
   measurement as fact, and rewriting a contract clause is a scope this instruction did not cover. See
   §6.

## 6. Follow-ups this change creates

- **Four sites still assert the 16–32 s figure** (`pyproject.toml:238`, `src/sofer/config.py:150`,
  `src/sofer/mcp_registration.py:288`, `openspec/specs/mcp-registration/spec.md:395`). Three are
  comments justifying the default's magnitude; the fourth is the contract of record and states the
  figure as the reason the clause exists. Deciding between removing the number everywhere, restating it
  as the environment it was measured in, or measuring it properly is open — the maintainer's
  instruction covered the README only. Until then the doctor and the spec can disagree in front of a
  user, which is the one thing this change was supposed to end.
- **#320's opencode work should consume this command's output.** The doctor already names the missing
  key per agent; whatever shape is chosen for opencode must arrive here as another adapter capability,
  not as a second hand-written table.
- **The measurement is single-sample.** A future change may want to repeat it (median of N) so a
  machine near the budget does not flip on noise. Not needed while the verdict is informational.
