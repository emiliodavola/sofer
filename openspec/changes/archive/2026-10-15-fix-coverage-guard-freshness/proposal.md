# Proposal — `2026-10-15-fix-coverage-guard-freshness`

> **Change** `2026-10-15-fix-coverage-guard-freshness` · issue **#305** · branch
> `fix/305-coverage-guard-freshness` from `dev@fad1b00` · store **hybrid**
> (`odd/tasks/coverage-guard-freshness.md` + this folder).
>
> **Status:** implementation complete; archived inside the delivering branch
> (AGENTS.md rule 15).

---

## 1. Intent

`tests/test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present`
asserts the three ≥90 floors and TOTAL from the repo-root `.coverage`. It cannot
distinguish a database it just produced from one left behind by an earlier run, so
any stale local `.coverage` makes the assertion evaluate **old numbers** and fail a
suite whose code is fine — with a message that names a floor module and reads
exactly like the policy regression the guard exists to catch.

Measured on the untouched tree in this session: `.coverage` dated 2026-10-09 11:21
against `src/sofer/verification.py` dated 2026-10-14 02:39, and

```text
$ uv run pytest tests/test_coverage_contract.py -q
E   AssertionError: src/sofer/verification.py measured 78.2% locally (< 90)
1 failed, 2 passed in 0.93s
```

The fix keeps the local regression pin and makes the guard assert only on a
database it can vouch for: one that exists, is not an in-flight `coverage run`
measurement, and is at least as new as every file it measured. Everything else
skips with a named reason.

## 2. Scope

### In scope

- A pure, module-level policy helper `_vouch_for_coverage_data(data_file,
  measured, env) -> str | None` in `tests/test_coverage_contract.py`.
- The guard test using it: the `skipif`-on-absence decorator is replaced by the
  helper's reason, and the loaded database is re-checked against its measured
  files.
- Six policy tests (missing file, in-flight run, stale database, vanished
  measured path, and the two vouched-for cases).
- The `coverage` spec: COV-01's optional-guard clause, one new scenario, one
  `## Test Mapping` row, and COV-07's rationale (b).

### Out of scope (non-goals)

- **No `src/sofer/` change.** The diff is test-only plus specs.
- **No gate is armed for the three floors** (COV-07): nothing is added to
  `scripts/check_core_coverage.sh`, either workflow, or `pyproject.toml`;
  COV-07's "No gate is armed" scenario stays true unmodified.
- **The issue's option 2 is not implemented** (see D1) and **option 3** (delete
  the assertion, move the floors to CI) is not either: option 3 would arm a gate
  and is a larger change; option 1 was chosen by the maintainer.
- No `src/sofer/` coverage work, no new dependency, no version bump.

## 3. Settled decisions

| # | Decision |
| --- | --- |
| D1 | Option 2 is rejected **as written**: `coverage run` erases its data file at start and flushes it at exit, so during the run — the only moment its marker exists — the file on disk belongs to a previous run. A guard that *required* the marker could only read stale data, or never assert at all. |
| D2 | Vouch conditions, in order: the file exists; no measurement in flight (`COVERAGE_RUN` unset); the database is not older than any file it measured (`db_mtime >= max(measured mtime)`, `>=` for filesystem timestamp granularity), and no measured path has vanished. |
| D3 | The policy is a pure helper with a documented contract, unit-testable without coverage data (`tmp_path` + `os.utime`). |
| D4 | The assertion stays; only the skip condition widens from "absent" to "absent or unvouched-for". No gate, workflow, script or config key changes. |
| D5 | The residual limitation is named, not hidden: a subset `coverage run` also leaves a fresh, complete-looking database, and coverage data records no provenance about which tests ran. Mitigated by the measured-files check, recorded in the module docstring. |

## 4. Affected specs

`coverage`: COV-01 (Modified — the optional guard's vouch condition), COV-07
(Modified — rationale (b)) and one new COV-01 scenario. `coverage` carries a
`## Test Mapping` table, so the new scenario is mapped to
`tests/test_coverage_contract.py::test_vouch_rejects_stale_database` rather than
left unmapped; the registry is untouched and `scripts/check_test_mapping.py`
reports `coverage: 18 scenario(s), mapped`.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | The freshness check could silence a genuine regression that happens to coexist with a stale database. | Low | The skip is named and the guard still asserts on a fresh database; CI's own gates (`coverage report -m` + the four 100% rows) are unaffected and remain the arbiter. |
| R2 | A subset `coverage run` still yields an assertable database (D5). | Low | Named in the module docstring; the measured-files check catches the common partial cases; closing it fully needs provenance coverage data does not record. |
| R3 | Mtime-based staleness is weaker than hashing on filesystems with coarse timestamps. | Low | `>=` comparison absorbs coarse granularity; a source edited in the same timestamp tick as the measurement is not detected, and the CI gates remain authoritative. |

## 6. Rollback

Revert-only, test-only: restoring the `skipif` decorator, the direct
`.coverage` read, the removed six tests and the four spec sections restores the
previous behaviour exactly. No state, no migration.

## 7. Success criteria

SC-1 A stale local `.coverage` makes the guard skip with a reason naming
     staleness instead of failing a clean suite.
SC-2 An in-flight measurement is never asserted on.
SC-3 A fresh, complete database still asserts the three floors and TOTAL (the
     local pin survives).
SC-4 A clean checkout still skips (COV-01-S3 unchanged).
SC-5 No gate is armed for the three floors (COV-07's scenario stays true).
SC-6 Full suite green; ruff/format/mypy/pyright and the mapping checker green.
