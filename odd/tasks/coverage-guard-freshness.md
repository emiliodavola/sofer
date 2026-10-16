# Feature: coverage-guard-freshness — issue #305

**Branch:** `fix/305-coverage-guard-freshness` from `dev@01a141c1`-era `dev` (`fad1b00`).
**Issue:** `emiliodavola/sofer#305`. **Delivery PR:** (pending — user decision) → `dev`.
**SDD change:** `openspec/changes/2026-10-15-fix-coverage-guard-freshness/` (archived inside this
branch, AGENTS.md rule 15). **Risk:** low — test-only, no `src/` change, no gate added or removed.

## Goal

`tests/test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present`
reads `<repo>/.coverage` and asserts the three ≥90 floors plus TOTAL from it. It cannot tell a
database it just produced from one left behind by an earlier run, so a stale or partial local
`.coverage` makes it evaluate **old numbers** and fail a suite whose code is fine — with a message
that names a floor module and reads exactly like the policy regression the guard exists to catch.

Measured in this session on the untouched tree:

```text
$ ls -la --time-style=long-iso .coverage src/sofer/verification.py
2026-10-09 11:21 .coverage
2026-10-14 02:39 src/sofer/verification.py

$ uv run pytest tests/test_coverage_contract.py -q
E   AssertionError: src/sofer/verification.py measured 78.2% locally (< 90)
1 failed, 2 passed in 0.93s
```

**One-line outcome:** the guard asserts only on a database it can vouch for — one that exists, is not
an in-flight `coverage run` measurement, and is newer than every file it measured — and skips with a
named reason otherwise, while the local regression pin survives for fresh data.

## Specs

S1 (user, verbatim): "3. opcion 1"

S2 (issue #305 §Proposed solution item 1, verbatim): "**Compare the data file's mtime (or a hash of
the measured files) against the current sources, and skip when the database predates them.**"

S3 (issue #305 §Problem, verbatim): "The guard cannot tell a database it just produced from one left
behind by an earlier run, so any stale or partial `.coverage` in the working tree makes the assertion
evaluate **old numbers** and fail a suite whose code is fine."

S4 (issue #305 §Evidence, verbatim):

```text
$ uv run pytest tests/ -q
FAILED tests/test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present
1 failed, 2135 passed, 8 skipped
```

S5 (user, verbatim): "1. D1: explicamelo en facil / 2. D2: data fields por tabla / 3. opcion 1 / 4.
arrancá"

S6 (`openspec/specs/coverage/spec.md` COV-07, verbatim): "Arming any gate for the three floors — a
non-100 scoped invocation, a new gate script, a per-file config key, or a workflow step — SHALL be its
own SDD change"

S7 (`openspec/specs/coverage/spec.md` COV-01, verbatim): "The change MAY additionally guard the floors
with a skip-if-absent `tests/test_coverage_contract.py` regression guard that asserts the three rows
and TOTAL from a local `.coverage` data file when one is present, and SHALL skip on a clean checkout"

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The issue's **option 2 is rejected as written**: requiring an environment marker the coverage job sets cannot work. `coverage run` erases its data file at start and flushes it at process exit, so during the run — the only moment the marker exists — the file on disk is a previous run's or empty; a guard that required the marker would read stale data or never assert at all. | `coverage/cmdline.py`: `COVERAGE_RUN=true` is set at line 1034 immediately before the run, and `Coverage.start()` erases the data file; the guard test executes inside that same process. Recorded so the rejected option is not revisited. |
| D2 | "Can I vouch for this database?" has three conditions, checked in order: the file exists; the measurement is not in flight (`COVERAGE_RUN` unset); and the database is **not older than any file it measured** (`db_mtime >= max(measured_mtime)`, `>=` for filesystem timestamp granularity). A measured path that no longer exists is not vouched for. | S2's first half (mtime comparison, chosen over hashing: a hash of the measured sources cannot be stored by `coverage run` without a new gate surface, and mtime answers the same question). |
| D3 | The policy lives in a **pure, module-level helper** (`_vouch_for_coverage_data`) that takes the path, the measured list and the environment, and returns the skip reason or `None`. | So the policy is unit-testable with `tmp_path` + `os.utime` and no coverage data, and the assertions stay where the pin lives (AGENTS.md rule 2: documented contract). |
| D4 | The **assertion stays**. This change does not move the floors anywhere, arms no gate and touches no workflow, script or `pyproject.toml` key; it only widens the guard's existing skip condition from "absent" to "absent or unvouched-for". | S6 + COV-07: arming a gate for the three floors would be a different, larger change. S7's MAY-clause is preserved verbatim, only its precondition ("when one is present") becomes "when one is present and vouched for". |
| D5 | A residual limitation is **named, not hidden**: a `coverage run` over a *subset* of the suite also produces a fresh, complete-looking database, and the guard will assert on it. | Coverage data records no provenance about which tests ran. Mitigated — not closed — by requiring the database to have measured every `src/sofer/*.py` file (the existing "partial database" skip already covers missing files); the residual is recorded in the module docstring. |

## Tasks

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | RED: unit tests for `_vouch_for_coverage_data` — missing file, in-flight measurement, stale database, database measuring a file that no longer exists, fresh database vouched for | S2 D2 D3 | inline | pending | — |
| T2 | Implement the helper and wire it into the guard (replacing the `skipif` decorator with the helper's reason) | S2 S3 D2 D3 D4 | inline | pending | — |
| T3 | Keep the regressions green: fresh database still asserts the three floors + TOTAL; clean checkout still skips | S7 D4 | inline | pending | — |
| T4 | `coverage` spec delta (COV-01 clause + new scenario + Test Mapping row; COV-07 clause (b) note) and canonical spec amendment | S6 S7 | inline | pending | — |
| T5 | Live demonstration on the real artifact: a database whose mtime predates its sources makes the guard skip (reason named) instead of failing | S3 S4 S5 | inline | pending | — |
| T6 | Gates: full suite, ruff/format/mypy/pyright, `check_test_mapping.py`, archive, commit | — | inline | pending | — |

## Log

L1 (2026-10-15, user, verbatim): "revisá los issues tipo bug y armate un roadmap para implementar los
cambios, el issue #304 analizalo bien, puede haber columnas con nombres repetidos a lo largo de las
diferentes tablas y eso no es un problema, en todo caso tendria que haber un esquema de como se
relacionan"

L2 (2026-10-15, this session): reproduced the false positive live — the tree carries a `.coverage` from
2026-10-09 while `src/sofer/verification.py` is from 2026-10-14, and the guard fails with
`src/sofer/verification.py measured 78.2% locally (< 90)`. Also established that the issue's option 2 is
a trap (D1).

L3 (2026-10-15, user, verbatim): "1. D1: explicamelo en facil / 2. D2: data fields por tabla / 3. opcion
1 / 4. arrancá" — option 1 (freshness) chosen; this change implements it.
