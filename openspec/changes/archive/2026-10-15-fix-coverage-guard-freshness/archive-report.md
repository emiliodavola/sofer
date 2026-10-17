# Archive Report: The coverage-contract guard asserts only on data it can vouch for

**Change**: `2026-10-15-fix-coverage-guard-freshness`
**Archived to**: `openspec/changes/archive/2026-10-15-fix-coverage-guard-freshness/`
**Branch**: `fix/305-coverage-guard-freshness` (base `dev@fad1b00`)
**Issue**: `emiliodavola/sofer#305`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `coverage` | Updated | COV-01's optional-guard clause now reads "when one is present **and the guard can vouch for it**" and lists the three skip conditions (clean checkout, measurement in flight via `COVERAGE_RUN`, database older than any file it measured, with `>=` for timestamp granularity) plus the naming requirement. One scenario is added: "Contract guard skips an unvouchable database — issue #305". COV-07's rationale item (b) accounts for the second skip and its heading records the modification. No requirement added or removed; **no gate is armed**. |

The canonical `openspec/specs/coverage/spec.md` was amended in place from the delta's
`## MODIFIED Requirements` block. `coverage` carries its own `## Test Mapping` table, so the new
scenario is mapped rather than left unmapped:
`test:tests/test_coverage_contract.py::test_vouch_rejects_stale_database`. `scripts/check_test_mapping.py`
exits 0 and reports `coverage: 18 scenario(s), mapped` (was 17); `openspec/test-mapping-registry.md` is
untouched.

## Archive Contents

- `proposal.md` — present (intent, scope, D1–D5, the rejected option 2 as written, 3 risks, rollback,
  SC-1..SC-6)
- `design.md` — present (the defect precisely, the measured before/after, the edit table, § 4 the
  rejected alternative in detail, TDD posture, risks)
- `tasks.md` — present, T1–T6 complete; T7 (push/PR) is parent-owned and pending
- `specs/coverage/spec.md` (delta) — present

No `explore.md`, `apply-progress.md`, `verify-report.md` or `sync-report.md` siblings were produced;
the four files above are the complete set.

## Source of Truth Updated

- `openspec/specs/coverage/spec.md` — COV-01 and COV-07 as amended.
- `tests/test_coverage_contract.py` — `_vouch_for_coverage_data` (the pure policy), `_pinned_file` and
  six policy tests; the guard test drops its `skipif`-on-absence decorator, calls the helper before
  loading (existence, in-flight) and again with the loaded `measured` list (freshness), and keeps its
  assertions verbatim. Module docstring states the policy and the residual limitation.
- `odd/tasks/coverage-guard-freshness.md` — the ODD record (specs quoted verbatim, D1–D5, tasks, log).
- **No `src/sofer/` change**, no gate script, workflow, `pyproject.toml` key or README change (rules 7
  and 13 do not trigger: no CLI surface, option, config key or documented behaviour changed).

## Verification

| Gate | Command | Result |
|------|---------|--------|
| Full suite | `uv run pytest tests/ -q` | **2141 passed, 9 skipped** in 70.12s |
| Focused module | `uv run pytest tests/test_coverage_contract.py -q` | **8 passed, 1 skipped** (the skip is the guard declining a stale database) |
| RED (before the helper existed) | `uv run pytest tests/test_coverage_contract.py -q` | **7 failed, 2 passed** (`NameError: name '_vouch_for_coverage_data' is not defined`) |
| Lint | `uv run ruff check src/ tests/ scripts/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 75 files already formatted |
| Types | `uv run mypy src/ scripts/` | Success |
| Types (2nd) | `uv run pyright` | 0 errors |
| Spec↔test mapping | `uv run python scripts/check_test_mapping.py` | OK — `coverage: 18 scenario(s), mapped` |
| Live stale-database skip | mtime pinned into the past, then restored | `SKIPPED [1] ...: stale coverage database: it is older than a file it measured (_converters.py) — run `uv run coverage run -m pytest` for current numbers` |
| Floors + TOTAL via the guard, **fresh** database | `uv run pytest tests/test_coverage_contract.py -q` | **9 passed, no skip** — the guard asserted the three ≥90 floors and TOTAL on the database that run had just produced, so the local regression pin survives (SC-3) |
| Coverage TOTAL | `uv run coverage run -m pytest` + `uv run coverage report -m` | TOTAL **94%** (floor 90, CI-01); `verification.py` and `scanner.py` **100%**, `repo_compliance.py` 92%, `splits.py` 94% |

## Notes for the reviewer

1. **The assertion is unchanged.** This change removes no pin: it only widens the guard's skip
   condition from "the file is absent" to "the file is absent or cannot be attributed to this tree".
   `scripts/check_core_coverage.sh`, both workflows and `pyproject.toml` are untouched, so COV-07's
   "No gate is armed for the three second-tier floors" scenario and the two ban-pinning guards in
   `tests/test_ci_workflows.py` stay green **unmodified**.
2. **The issue's option 2 is documented as rejected** (proposal D1, design § 4) rather than silently
   skipped: `coverage run` erases its data file at start and flushes it at exit while setting
   `COVERAGE_RUN` for the very process the guard runs in, so requiring that marker could only read a
   previous run's data — or never assert at all. The marker is used inverted, as a skip reason.
3. **Residual limitation, named**: a `coverage run` over a *subset* of the suite also leaves a fresh,
   complete-looking database and the guard will assert on it. Coverage data records no provenance about
   which tests ran; the measured-files check catches the common partial cases. Recorded in the test
   module's docstring and as R2 in `proposal.md` § 5.
4. **Relationship to #304**: the sibling change's archive report records this same false positive as
   the reason its suite had to be run after `rm -f .coverage`. After this change that workaround is no
   longer needed — the guard declines the stale database and names why.
