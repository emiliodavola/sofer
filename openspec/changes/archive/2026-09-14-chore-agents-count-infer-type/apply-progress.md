# Apply Progress: chore-agents-count-infer-type (issue #162)

**Status**: implementation complete — **Ready for verify** · **Branch**: `chore/162-agents-count-infer-type`
**Store**: hybrid (this file + Engram `sdd/2026-09-14-chore-agents-count-infer-type/apply-progress`)
**Strict TDD**: off (`openspec/config.yaml` `strict_tdd: false`) — a behaviour-preserving migration has no RED state; sequence was migrate → measure parity → measure gates.

## Structured status consumed

`applyState: ready` · `actionContext.mode: repo-local` · `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]` · `blockedReasons: []`.
Review Workload Gate: `Decision needed before apply: No` · `Chained PRs recommended: No` · `400-line budget risk: Low` · `Chain strategy: pending` → no delivery decision required; proceeded single-PR. No `actionContext` warning fired; every edited path is inside the allowed root.

## Workload / PR boundary

Single work unit, single PR against `dev`. Measured diff: **3 files, 22 insertions / 40 deletions = 62 changed lines** vs the 400-line budget (Low risk confirmed). No chaining, no `size:exception`, no `ask-on-risk` trigger. Rollback = revert the three-file diff (no data, migration, flag, config or CI change).

## Task completion (persisted checkboxes)

All **13/13** implementation-owned tasks marked `- [x]` in `tasks.md`; zero parent-owned markers exist; **`- [ ]` count re-read after the flip = 0**.

| Task | Status | Key evidence |
| --- | --- | --- |
| 1.1 baseline measurement | ✅ [x] | pre-edit `uv run pytest tests/ -q` → `1766 passed, 6 skipped, 14 warnings in 53.54s`, exit 0 |
| 1.2 `AGENTS.md` rule 6 §D1 wording | ✅ [x] | `@@ -44 +44,2 @@` single replaced line; `grep 1149\|1151` → exit 1 (absent) |
| 2.1 import L11 + banner L23 | ✅ [x] | `-1` import line; banner `── infer_column_type ──` |
| 2.2 class rename + docstring | ✅ [x] | `TestInferColumnTypeSamples` L25; no `TestInferType` remains |
| 2.3 nine call sites repointed | ✅ [x] | 9 sites in the sample class, 4 in the parity test = 13; inputs/outputs byte-identical |
| 2.4 `TestInferColumnType` docstring L57 | ✅ [x] | refreshed; `grep -c _infer_type tests/test_codebook.py` → 0 |
| 2.5 parity test replaced | ✅ [x] | `test_representative_cases_expected_outputs` (4 asserted cases) |
| 3.1 delete `_infer_type` | ✅ [x] | `git diff --numstat` → `0 15` (deletions only) |
| 4.1 full suite + zero warnings | ✅ [x] | `1766 passed, 6 skipped, 1 warning`; `grep -c DeprecationWarning` → 0 |
| 4.2 module green both ways | ✅ [x] | `82 passed` exit 0; `-W error::DeprecationWarning` → `82 passed` exit 0 |
| 4.3 mypy / ruff check / format | ✅ [x] | mypy `Success: no issues found in 32 source files`; ruff check `All checks passed!` (see deviation 2) |
| 4.4 coverage gates | ✅ [x] | `check_core_coverage.sh` exit 0 (4×100%, empty Missing); TOTAL 93% ≥ 90 |
| 4.5 mechanical scope check | ✅ [x] | `git diff --stat` = exactly the 3 files; 10 forbidden paths empty; alias scan 0 matches |

## Files changed

| File | Change |
| --- | --- |
| `AGENTS.md` | rule 6 line 44 replaced with the §D1 wording (+2/−1) |
| `tests/test_codebook.py` | import −1, banner, class rename + docstrings, 9 call sites, parity test replaced (+20/−24) |
| `src/sofer/codebook.py` | `_infer_type` deleted, pure deletion (+0/−15) |

Plus this change's artifacts: `tasks.md` (checkboxes) and this file. No other tracked file is touched.

## Evidence (real command output)

**1.1 — pre-edit baseline**
```
1766 passed, 6 skipped, 14 warnings in 53.54s        # exit 0
```
The `14 warnings` were the 14 `_infer_type` `DeprecationWarning`s (proposal's starting defect).

**1.2 — `git diff -U0 -- AGENTS.md`**
```
@@ -44 +44,2 @@
-- 1149 tests currently pass (1151 collected, 2 skipped) — never reduce coverage.
+- Never reduce coverage. The authoritative tally is what `uv run pytest tests/ -q` reports on your branch —
+  re-derive it, never trust a figure here. Observed on this branch: 1766 passed, 6 skipped (1772 collected).
```
`grep -n "1149\|1151" AGENTS.md` → no match (exit 1). Wording is §D1 verbatim with measured `<P>/<S>/<C>`.

**3.1 — deletion shape**
```
 src/sofer/codebook.py | 15 ---------------
 1 file changed, 15 deletions(-)
numstat: 0	15
```
Before the edit, `grep -n -B2 -A14 "def _infer_type"` showed the block at **60–72** (13 source lines) with two blank separator lines; `git diff -U0` confirms deletions only, 0 additions.

**4.1 — post-change full suite**
```
1766 passed, 6 skipped, 1 warning in 54.42s           # exit 0
grep -c "DeprecationWarning"  →  0
```
The single remaining warning is pre-existing and unrelated: `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` → `RuntimeWarning: 'sofer.cli' found in sys.modules … (runpy)`.
Tally cross-check: `uv run pytest tests/ --collect-only -q` → `1772 tests collected` → 1766 + 6 = 1772 ✅ equals the figure pasted into rule 6. PB-11 scenario 1 satisfied; the 1149/1151/2 triple is gone.

**4.2 — migrated module**
```
uv run pytest tests/test_codebook.py -q                              → 82 passed in 1.04s   (exit 0)
uv run pytest tests/test_codebook.py -q -W error::DeprecationWarning → 82 passed in 1.02s   (exit 0)
```
Verbose case list (both runs, under `-W error::DeprecationWarning`):
`test_numeric`, `test_numeric_with_decimals`, `test_categorical`, `test_mixed_mostly_numeric`, `test_empty_values`, `test_mixed_with_missing`, `test_all_missing`, `test_single_value`, `test_public_api_exists`, `test_representative_cases_expected_outputs` — all PASSED.

**4.3 — quality gates**
```
uv run mypy src/                                        → Success: no issues found in 32 source files (exit 0)
uv run ruff check src/ tests/                           → All checks passed! (exit 0)
uv run ruff format --check src/sofer/codebook.py tests/test_codebook.py → 2 files already formatted (exit 0)
```
mypy ran under the repo's pinned 3.13 (`.python-version` → `3.13`); no version-matrix change (AGENTS rule 12).

**4.4 — coverage gates**
```
bash scripts/check_core_coverage.sh → exit 0
  src\sofer\cli.py      574  0  166  0  100%   (Missing: empty)
  src\sofer\scanner.py  159  0   76  0  100%   (Missing: empty)
  src\sofer\prepare.py  432  0  226  0  100%   (Missing: empty)
  src\sofer\publish.py  326  0  138  0  100%   (Missing: empty)
uv run coverage report -m → exit 0
  src\sofer\codebook.py  366  42  160  13  89%   (no per-file floor — COV-01 / COV-06 do not cover it)
  TOTAL                 6002 365 2322 166  93%   (≥ config-owned fail_under = 90)
```
The deletion removed fully-covered lines from an unfloored module, so no scoped gate could drop.

**4.5 — mechanical scope + residual references**
```
git diff --stat → AGENTS.md | src/sofer/codebook.py | tests/test_codebook.py   (only these)
EMPTY git diff for: README.md, README_ES.md, pyproject.toml, .github, openspec/specs,
  proposal.md, design.md, specs/, openspec/changes/2026-09-14-chore-python-version-313, openspec/changes/archive
grep -rn "_infer_type" src/ tests/ AGENTS.md README.md README_ES.md → 0 matches (exit 1)
```

## Behavioural parity (PB-12 scenario 2 vs the §D2 13-case baseline)

| # | values | expected | pre-change | post-change |
| --- | --- | --- | --- | --- |
| 1 | `["1","2","3","4"]` | `numeric` | ✅ | ✅ |
| 2 | `["1,5","2,0","3,7"]` | `numeric` | ✅ | ✅ |
| 3 | `["red","blue","green","red"]` | `categorical/text` | ✅ | ✅ |
| 4 | `["1","2","three","4"]` | `"mixed" in` | ✅ | ✅ |
| 5 | `["","NA","MISSING"]` | `categorical/text` | ✅ | ✅ |
| 6 | `["10","","20","NA","30"]` | `"mixed" in` | ✅ | ✅ |
| 7 | `["NA","NA",""]` | `categorical/text` | ✅ | ✅ |
| 8 | `["42"]` | `numeric` | ✅ | ✅ |
| 9 | `["hello"]` | `categorical/text` | ✅ | ✅ |
| 10 | `["1","2","3"]` | `numeric` | ✅ | ✅ |
| 11 | `["red","blue"]` | `categorical/text` | ✅ | ✅ |
| 12 | `["1","two","3"]` | `mixed (mostly numeric)` | ✅ | ✅ |
| 13 | `["NA","","MISSING"]` | `categorical/text` | ✅ | ✅ |

**13 cases / 13 primary assertions — none added, none dropped, none relaxed, skipped, parametrised away or reformatted away.**
Assertion count moved 17 → 13. The 4 removed statements were `infer_column_type(values) == _infer_type(values)` in `test_returns_same_as_private`; they were **exact duplicates** of the 4 kept `== expected` assertions over identical inputs (the alias merely delegates to the public function), so **no distinct assertion was lost**. Stated explicitly per task 2.5.

## Deviations from design

1. **`codebook.py` deletion measured −15, design/tasks cited −12.** The function spans source lines 60–72 (13 lines: def + 4-line docstring + `import warnings` + blank + 5-line `warnings.warn` + return); removing the block plus its now-redundant blank separator pair yields `-15 / +0`. The **shape** is exactly the authorised one ("pure deletion, nothing outside that block changes, 0 additions") — only the counting estimate was off by the docstring's blank line and the blank pair. No line nearby was reformatted.
2. **`uv run ruff format --check src/ tests/` is not clean repo-wide (exit 1).** Six pre-existing unformatted files: `tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`, `tests/test_mcp_registration.py`, `tests/test_profile.py`, `tests/test_publish.py`, `tests/test_splits.py`. This is the drift owned by the **unmerged sibling `2026-09-14-chore-ruff-format-drift` (PR #196)**, which design §D4 mandates must merge first. It is **not caused by this change**: the diff is exactly the three in-scope files, none of them in that list, and the two files this change edits pass `ruff format --check` standalone (exit 0). Fixing the six would break the binding three-file scope, so it is disclosed, not silently repaired.
3. **Targeted build-artifact hygiene (no tracked change).** After the edit, `grep -rn _infer_type` matched four **stale gitignored `.pyc` caches** (`src/sofer/__pycache__/codebook.cpython-310.pyc`, `…-311.pyc`, `tests/__pycache__/test_codebook.cpython-310-pytest-9.1.1.pyc`, `…-311…pyc`). PB-12 scenario 3 requires zero matches outside `openspec/changes/archive/**`, so those four derived artifacts were removed. They are untracked, auto-regenerated, and cannot affect the diff — re-running the migrated module regenerates an alias-free cache (`grep -rn _infer_type tests/__pycache__/` → exit 1). This is not a source edit and does not widen scope.

No other deviation: §D1 wording verbatim, §D2 migration verbatim, the rule-6 figure re-derived from the post-change run.

## pi-lens automated-check disposition (14 reported lines)

All 14 lines are **pre-existing and byte-identical to HEAD**; proof by comparison at the measured offsets:

- `tests/test_codebook.py` L299/300/301/319/403/404/877/878/879/1133 == HEAD L303/304/305/323/407/408/881/882/883/1137 (net offset −4) — `ws.append(...)` / `ws.title` where `ws = wb.active` is `Worksheet | None` in the openpyxl stubs.
- `src/sofer/codebook.py` L75/230/235 == HEAD L90/245/250 (offset −15) — `with open(...)` in `_read_csv` / `_read_jsonl` and `json.loads(stripped)`.

Disposition: **left unchanged, on purpose.** The binding scope in `tasks.md` non-goals ("no file other than the three named; third = alias deletion only"; "no line nearby is reformatted") and the parent's instruction to use the design verbatim forbid touching them; fixing them would add unrelated churn to a 62-line review and expand the diff beyond the declared three files. Substance also holds: the `codebook.py` reads are error-guarded by their callers (`generate_all` wraps `_read_file` in `try/except Exception` → warn-and-continue), and `tests/` is outside the repo's type gate (`uv run mypy src/`, AGENTS rules 5/12), which passes clean.

## Remaining tasks

**None.** `grep -c "^- \[ \] " tasks.md` → 0.

Parent-owned lifecycle actions (explicitly **not** apply tasks, untouched by this phase): commit the three-file diff with hooks enabled (never `--no-verify`); quote the design's verbatim compatibility note in the PR description and release notes; enforce the §D4 merge order (**PR #196 first**); archive PB-11/PB-12 after PB-10 without renumbering, reporting a PB-09 → PB-11 gap rather than "fixing" it; run the post-apply bounded review. No tag or release is cut.

## Risks

1. **PR #196 merge order** — if the sibling merges after this change, the archive shows a cosmetic PB-09 → PB-11 gap. Report it; never renumber a merged requirement.
2. **Option B private-name removal** — an out-of-repo importer of `sofer.codebook._infer_type` would break. Mitigated by the recorded compatibility note; option (A) (`pytest.warns` window) stays the documented fallback in design §D3.
3. **Repo-wide `ruff format --check` stays red until #196 merges** — pre-existing, unrelated, and out of the three-file scope.

## next_recommended

`parent-lifecycle` → verify (PB-11 2 scenarios + PB-12 3 scenarios per the delta's `## Test Mapping`).
