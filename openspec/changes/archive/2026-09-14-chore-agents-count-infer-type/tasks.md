# Tasks: chore-agents-count-infer-type

Closes #162 on branch `chore/162-agents-count-infer-type` (`.git/HEAD` → `ref: refs/heads/chore/162-agents-count-infer-type`, cut from `dev`). Store: **hybrid** — this file plus the Engram mirror `sdd/2026-09-14-chore-agents-count-infer-type/tasks`. Inputs already written and not re-litigated here: spec delta `specs/process-boundary/spec.md` (ADDED **PB-11** verifiable test-count anchor, ADDED **PB-12** zero deprecation warnings, with its `## Test Mapping` and binding `## Non-goals`) and `design.md` (§D1 verbatim rule-6 wording, §D2 five migration steps + nine call sites + the 13-case equivalence baseline, §D3 alias deletion with option A as fallback, §D4 numbering, §D6 commands). Strict TDD off (`openspec/config.yaml` `strict_tdd: false`): a behaviour-preserving migration has no RED state, so the sequence is **migrate → measure parity → measure gates**. Three files, ~30 changed lines, single PR — every task below traces to the design; no alternative shape is authorised.

**Merge-ordering constraint (design §D4 — recorded as context, deliberately NOT an apply task):** this delta uses PB-11/PB-12 because **PB-10 belongs to the sibling `2026-09-14-chore-ruff-format-drift` (PR #196) and is not yet on `dev`**. **PR #196 must merge before this change's PR**, and archive inserts PB-11/PB-12 after PB-10. If that order is not honoured the breakage is a cosmetic gap PB-09 → PB-11 — requirement IDs are labels, so the gap **must not be "fixed" by renumbering a merged requirement**; report it instead.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~30 (−/+) — `AGENTS.md` rule 6 line 44 ~−1/+2; `tests/test_codebook.py` ~−15/+14 (import −1, banner, class rename + docstring, nine call sites, parity test replaced by 4 asserted cases); `src/sofer/codebook.py` −12 (alias deletion only). `proposal.md` / `design.md` / the spec delta / `tasks.md` are SDD artifacts, not review load |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR against `dev` (three-file diff: one docs line, one test module, one −12-line deletion) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not needed — single PR; chaining deferred until selected. ~30 lines against a 400-line budget, so `ask-on-risk` does not fire) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

### Suggested Work Units

| Unit | Goal | Likely PR | Boundaries (start → finish · verify · rollback) |
| ------ | ------ | ----------- | ------------------------------------------------ |
| 1 | All of it: rule-6 anchor, `tests/test_codebook.py` migration, `src/sofer/codebook.py` alias deletion, evidence run | PR 1 | 1.1 → 4.5 · post-migration case list equals the §D2 13-case baseline, suite green with zero `DeprecationWarning` lines, `check_core_coverage.sh` exit 0, no assertion dropped/weakened/skipped · single-commit `git revert` of the three-file diff (no data, migration, flag, config or CI change; the suite is green in both states) |

Out-of-scope boundaries for unit 1: no file other than `AGENTS.md`, `tests/test_codebook.py`, `src/sofer/codebook.py` (third = alias deletion only). Any diff line elsewhere is a scope violation (delta non-goals / proposal §Non-goals) and is rejected at apply/verify — see task 4.5's mechanical check.

## Phase 1: `AGENTS.md` rule 6 — anchor the floor to its command (design §D1)

- [x] 1.1 Run `uv run pytest tests/ -q` on this branch and record the actual passed/skipped/collected triple verbatim (proposal measured 1766 passed / 6 skipped / 1772 collected; **measure, do not trust** — the pre-change rule-6 figure 1149/1151/2 is the stale value being removed). Populates `<P>/<S>/<C>` in 1.2. <!-- sdd-owner: implementation -->
  - **Evidence:** the suite tail line with collected/passed/skipped counts recorded verbatim.
- [x] 1.2 Replace `AGENTS.md:44` verbatim with the §D1 wording — lead sentence keeps the floor, names the reproducing command `uv run pytest tests/ -q`, labels any figure an observation of *this branch* and instructs re-derivation, then `Observed on this branch: <P> passed, <S> skipped (<C> collected).` with the counts from 1.1. `<P>/<S>/<C>` are measurements, not choices: no wording is invented. Touch no other line of rule 6 and no other rule. <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff -U0 -- AGENTS.md` shows exactly one replaced line, the post-change text names the command, and the 1149/1151/2 triple is absent.

## Phase 2: `tests/test_codebook.py` — migrate to the live public API (design §D2)

- [x] 2.1 Delete the `_infer_type,` import (L11) — the import block is alphabetical, nothing reorders — and retitle banner L23 `── _infer_type ──` → `── infer_column_type ──`. <!-- sdd-owner: implementation -->
  - **Evidence:** diff shows the single import line removed and the banner retitled; `infer_column_type` import kept.
- [x] 2.2 Rename `TestInferType` (L25-53) → `TestInferColumnTypeSamples` with docstring `"""Sample-value cases for the public infer_column_type (issue #162 migration)."""` — a class named after a deleted private alias would be a lie. <!-- sdd-owner: implementation -->
  - **Evidence:** renamed class + docstring in the diff; no `TestInferType` remains.
- [x] 2.3 Repoint all **nine** call sites (L28/31/34/38/41/46/49/52/53) to `infer_column_type`, keeping every input and every expected output byte-identical per the §D2 baseline (`["1","2","3","4"]`, `["1,5","2,0","3,7"]`, `["red","blue","green","red"]`, `["1","2","three","4"]`, `["","NA","MISSING"]`, `["10","","20","NA","30"]`, `["NA","NA",""]`, `["42"]`, `["hello"]` → numeric / numeric / categorical-text / `"mixed" in` / categorical-text / `"mixed" in` / categorical-text / numeric / categorical-text). <!-- sdd-owner: implementation -->
  - **Evidence:** exactly nine call sites repointed; each expected output unchanged (grep count + diff inspection).
- [x] 2.4 Refresh the `TestInferColumnType` docstring (L57, current text names the deleted symbol) → `"""Public infer_column_type — API surface and representative expected outputs."""`. <!-- sdd-owner: implementation -->
  - **Evidence:** docstring in the diff; zero references to the alias in the file.
- [x] 2.5 Delete `test_returns_same_as_private` (L64-73) and add `test_representative_cases_expected_outputs` asserting the **same four** `(values, expected)` cases against the live API — `["1","2","3"]`→numeric, `["red","blue"]`→categorical/text, `["1","two","3"]`→`"mixed (mostly numeric)"`, `["NA","","MISSING"]`→categorical/text — one assertion each (4). The 4 discarded `== _infer_type(values)` assertions were exact duplicates of the 4 kept `== expected` assertions over identical inputs, so no distinct assertion is lost; state this explicitly rather than gloss it. <!-- sdd-owner: implementation -->
  - **Evidence:** post-migration case list equals the §D2 13-case baseline case-for-case (9 sample + 4 parity); no case added, none dropped, none relaxed, skipped, parametrised away or reformatted away.

## Phase 3: `src/sofer/codebook.py` — delete the private deprecated alias (design §D3, option B)

- [x] 3.1 Delete `_infer_type` (`src/sofer/codebook.py:60-71`, −12 lines) as a pure deletion: nothing outside that block changes, no line nearby is reformatted, and no other symbol is touched. Safe by evidence — the only in-repo caller was the test migrated in phase 2, the canonical `openspec/specs/repo-compliance/spec.md:1494` only records a past rename, and `codebook.py` backs no per-file floor (COV-01 = `profile.py`/`mcp_registration.py`/`verification.py`; COV-06 = `cli.py`/`scanner.py`/`prepare.py`/`publish.py`). If a reviewer demands the compatibility window at PR time, option (A) is the documented fallback — then 2.5's replacement becomes a `pytest.warns(DeprecationWarning)` test and the acceptance criterion (zero warnings) is unchanged. <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff --stat src/sofer/codebook.py` shows deletions only (−12, 0 additions); repo-wide `_infer_type` search finds zero hits outside `openspec/changes/archive/**`.

## Phase 4: Evidence run (design §D6; acceptance evidence is command output, never placeholders)

- [x] 4.1 Re-run `uv run pytest tests/ -q`: suite green with the parity changes, and the warnings summary contains **zero** `DeprecationWarning` lines from `sofer.codebook` (PB-12 scenario 1). Confirm the tally equals the figure pasted into `AGENTS.md` rule 6 by 1.2; if it differs, amend 1.2 to the observed value rather than reporting a mismatch. <!-- sdd-owner: implementation -->
  - **Evidence:** actual tally line + the grep/absence result for `DeprecationWarning` in the warnings summary.
- [x] 4.2 Run `uv run pytest tests/test_codebook.py -q` (PB-12 scenario 2) and the same file under `-W error::DeprecationWarning` — green both ways, proving the migrated module needs no warning filter. <!-- sdd-owner: implementation -->
  - **Evidence:** both command outputs verbatim, including the per-test case list still asserting the baseline expectations.
- [x] 4.3 `uv run mypy src/` clean · `uv run ruff check src/ tests/` (`All checks passed!`) · `uv run ruff format --check src/ tests/` clean. mypy runs under Python 3.13 as in CI; do not add mypy to the version matrix (AGENTS rule 12). <!-- sdd-owner: implementation -->
  - **Evidence:** the three command outputs verbatim.
- [x] 4.4 `bash scripts/check_core_coverage.sh` exit 0 with `cli.py` / `scanner.py` / `prepare.py` / `publish.py` each at 100% (four rows, empty `Missing`), then `uv run coverage report -m` TOTAL at or above the config-owned `fail_under = 90` (`pyproject.toml:98`). The alias deletion removes fully-covered lines from an unfloored module, so no scoped gate can drop. <!-- sdd-owner: implementation -->
  - **Evidence:** the four scoped rows + the TOTAL row and the script's exit code.
- [x] 4.5 Mechanical scope + residual-reference check: `git diff --stat` lists exactly `AGENTS.md`, `tests/test_codebook.py`, `src/sofer/codebook.py` (plus this change's SDD artifacts); `git diff` is empty for `README.md`/`README_ES.md`, `pyproject.toml`, `.github/**`, `openspec/specs/**`, `proposal.md`, `design.md`, the spec delta, `openspec/changes/2026-09-14-chore-python-version-313/` and `openspec/changes/archive/**`; and the repo-wide `_infer_type` search over `src/`, `tests/`, `AGENTS.md` and the READMEs returns zero matches outside `openspec/changes/archive/**` historical prose (PB-12 scenario 3). <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff --stat`, the empty `git diff` for the listed paths, and the search result.

## Verification gates (verify phase — not apply tasks)

Owner: **verify**. These are the PB-11/PB-12 acceptance facts per the delta's `## Test Mapping`; they are recorded in `verify-report.md`, not closed here: PB-11 scenario 1 (post-change rule-6 text inspected and a fresh `uv run pytest tests/ -q` rerun whose tally is reproduced) · PB-11 scenario 2 (`git diff AGENTS.md` shows the 1149/1151/2 triple removed) · PB-12 scenario 1 (suite warnings summary has 0 `DeprecationWarning` lines, cross-checked with `-W error::DeprecationWarning`) · PB-12 scenario 2 (**pytest-asserted**: the 13-case behavioural-parity diff against the pre-change tree — the only strong row) · PB-12 scenario 3 (repo-wide alias scan). Verify also confirms no assertion was weakened and that the three-file boundary held.

## Lifecycle (parent-owned — not apply tasks)

Owner: **parent**. Commit the three-file diff on `chore/162-agents-count-infer-type` with hooks enabled (never `--no-verify`), quoting the design's verbatim compatibility note ("Removes the private, deprecated alias `sofer.codebook._infer_type`… No public API changes.") in the PR description and release notes; enforce the §D4 merge order — **PR #196 (PB-10) merges first**; archive PB-11/PB-12 after PB-10 without renumbering anything, reporting a PB-09 → PB-11 gap rather than "fixing" it; run the post-apply bounded review; no commit/push/PR is an apply task and no tag or release is cut.

## Out of scope (binding — no work in this change)

No fix for other stale documentation: `openspec/project.md` (#184), the `ruff.toml` reference in `CONTRIBUTING.md` (#187), the README counts/flags table (#183, #190). `openspec/config.yaml` carries a stale count too but is gitignored — local-only state, unfixable by a PR. No `filterwarnings` policy change in `pyproject.toml` (design §D5: a suite-wide pytest policy change with unrelated third-party warnings is not this chore). No test asserting `AGENTS.md`'s count against a computed count — the design rejected it as a fourth file outside scope and recorded it as an explicit follow-up (precedent `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate`). Do not touch any file other than the three named: not `proposal.md`, `design.md`, the spec delta, the canonical specs, the still-active `openspec/changes/2026-09-14-chore-python-version-313/`, or `openspec/changes/archive/**`. No commit, push or PR. No assertion dropped, weakened, skipped or renamed away.

**Closing note:** `apply` is a **single work unit** over three files and **no delivery gate is expected** — ~30 changed lines against the 400-line budget, so `ask-on-risk` is not exercised, no chaining is needed and `size:exception` is not requested. If the diff ever grows past the budget, stop and ask rather than chain.
