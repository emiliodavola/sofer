```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:a0c2393fa5cc55f3eae8061f9c8bbd80dac71f6b7c1793ee92cd2733522fd987
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 5/5
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:0ad7f531cc7f43d5f1aabc531850e853737146b1fc72010a7cd39e0beb5efb3d
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
```

# Verify report: chore-ruff-format-drift (issue #177)

**Change**: `2026-09-14-chore-ruff-format-drift` · **Branch**: `chore/177-ruff-format-drift` · **Store**: hybrid (this file + Engram `sdd/2026-09-14-chore-ruff-format-drift/verify-report`)
**Phase**: verify — behaviour-preservation evidence for the `process-boundary` delta **PB-10** (five scenarios).
**Attempt**: `sha256:70244b8184c2af8fa90bb179ef964a86d718be3fc909aa9b6001a28ecf5566a9` (state `proceed`, work unit `ruff-format-drift-behaviour-preservation`).
**Branch state at verify time**: `.git/HEAD` → `ref: refs/heads/chore/177-ruff-format-drift`; `git rev-parse HEAD` → `bdcff254c4f315362b6977be8de2d1c12257a7a4` (unchanged, zero commits ahead — nothing committed by apply or verify).

## Verdict

**PASS.** Every PB-10 scenario is evidenced by reproduced command output. The primary gate (4.1) is a byte-for-byte identical suite tally with zero failures, and the two static contract guards pass — which is what settles "formatting-only". No blockers; archive-ready subject to the ordinary PR/review step.

**Hash provenance:** the envelope's three hashes were each computed from a real command capture — `evidence_revision` from this change's `git diff` (the six modified test files), `test_output_hash` from the full stdout/stderr of `uv run pytest tests/ -q`, and `build_output_hash` from the combined stdout/stderr of `uv run ruff check src/ tests/` followed by `uv run mypy src/`.

## Reproduced gates (exact commands, output, exit codes)

### 4.1 Primary behaviour-preservation gate — `uv run pytest tests/ -q`

```text
$ uv run pytest tests/ -q
1766 passed, 6 skipped, 14 warnings in 54.69s
EXIT=0
```

Pre-change baseline (recorded by apply **before** the reformat, per design §6 ordering rule): `1766 passed, 6 skipped, 14 warnings in 54.13s`, EXIT=0. **Tally identical; 0 failures; 0 errors.** The ordering rule is satisfied by the evidence trail (baseline in `apply-progress.md` §1, which predates the reformat commit-less working-tree change), not by re-measurement.

Static contract guards, run directly (they assert on YAML/TOML **text**):

```text
$ uv run pytest tests/test_ci_workflows.py tests/test_coverage_contract.py -q
22 passed in 0.58s
EXIT=0
```

Independent mechanical check of "no logic, assertion, import, or test-behaviour edit" (HEAD blob vs working tree, all six files):

```text
$ uv run python - <<'EOF'   # ast.dump(ast.parse(HEAD)) == ast.dump(ast.parse(WORK))
tests/test_ci_workflows.py: AST_IDENTICAL=True   TOKEN_DIFFS=0
tests/test_coverage_contract.py: AST_IDENTICAL=True   TOKEN_DIFFS=0
tests/test_mcp_registration.py: AST_IDENTICAL=True   TOKEN_LEN_EQUAL=False
tests/test_profile.py: AST_IDENTICAL=True   TOKEN_DIFFS=0
tests/test_publish.py: AST_IDENTICAL=True   TOKEN_DIFFS=0
tests/test_splits.py: AST_IDENTICAL=True   TOKEN_DIFFS=0
ALL_AST_IDENTICAL: True
EXIT=0

$ uv run python - <<'EOF'   # token multiset diff, test_mcp_registration.py
only-in-HEAD: {'OP:(': 1, 'OP:)': 1}
only-in-WORK: {}
NAME/STRING/NUMBER/COMMENT identical: True
```

So the only token-level delta in the whole six-file diff is one redundant parenthesis pair removed by ruff around a single-line `assert` — AST-neutral, **no string literal touched** (hence the two guards' asserted YAML/TOML strings are provably byte-identical, not merely still-passing).

### 4.2 Type gate — `uv run mypy src/`

```text
$ uv run mypy src/
Success: no issues found in 32 source files
EXIT=0
```

32 source files, no flags — matches the expected shape exactly.

### 4.3 Coverage gate — `bash scripts/check_core_coverage.sh`

```text
$ uv run coverage run -m pytest -q
1766 passed, 6 skipped, 14 warnings in 65.05s (0:01:05)
COV_RUN_EXIT=0

$ bash scripts/check_core_coverage.sh
src\sofer\cli.py     574   0  166  0  100%   (Missing empty)
src\sofer\scanner.py 159   0   76  0  100%   (Missing empty)
src\sofer\prepare.py 432   0  226  0  100%   (Missing empty)
src\sofer\publish.py 326   0  138  0  100%   (Missing empty)
EXIT=0
```

All four scoped rows at **100%**, `Missing` column empty, script exit 0. Covered lines moved together with their branch data (branch counts non-zero and 0 partial on every row). `uv run coverage report -m` (flag-free, config-owned TOTAL floor) → `TOTAL … 93%`, `EXIT=0` — above the untouched `[tool.coverage.report] fail_under = 90` (`pyproject.toml:98`, `ci` CI-01).

### 4.4 Diff hygiene — `git diff --check` and diff scope

```text
$ git diff --check
(empty)
EXIT=0

$ git diff --stat
 tests/test_ci_workflows.py      | 27 ++++++++++++---------------
 tests/test_coverage_contract.py |  4 +---
 tests/test_mcp_registration.py  | 24 ++++++------------------
 tests/test_profile.py           |  8 ++------
 tests/test_publish.py           |  3 +--
 tests/test_splits.py            |  4 +---
 6 files changed, 23 insertions(+), 47 deletions(-)
EXIT=0

$ git diff --numstat
12  15  tests/test_ci_workflows.py
1    3  tests/test_coverage_contract.py
6   18  tests/test_mcp_registration.py
2    6  tests/test_profile.py
1    2  tests/test_publish.py
1    3  tests/test_splits.py
EXIT=0
```

Diff is limited to exactly the six named test files — zero `src/sofer/`, zero `.github/workflows/`, zero `pyproject.toml` / `.pre-commit-config.yaml` / `uv.lock` paths (prohibited-path check: `git diff --name-only | wc -l` → 6).

### Supporting static gates (PB-10 S1/S4 — re-run here, not taken from apply)

```text
$ uv run ruff format --check src/ tests/   → 67 files already formatted   EXIT=0
$ uv run ruff format --diff  src/ tests/   → 67 files already formatted (no diff emitted)   EXIT=0
$ uv run ruff check src/ tests/            → All checks passed!   EXIT=0
$ uv run ruff --version                    → ruff 0.16.0   EXIT=0
$ grep -rn "format --check" .github/workflows/   → no matches   EXIT=1
$ grep -rn "ruff format"    .github/workflows/   → no matches   EXIT=1
$ git diff -- .github/workflows/ | wc -l   → 0
$ ls .github/workflows/                    → ci.yml  codeql.yml  release.yml
$ ls openspec/changes/2026-09-14-chore-python-version-313/ porcelain → 0 (untouched)
```

## PB-10 scenario coverage

| Scenario | Evidencing command(s) | Result |
| --- | --- | --- |
| **S1** Clean-checkout format check exits 0 | `uv run ruff format --check src/ tests/` (exit 0, 67 already formatted) **and** `uv run ruff format --diff src/ tests/` (no diff emitted, exit 0) | ✅ PASS |
| **S2** Exactly the six test files changed | `git diff --stat` / `git diff --numstat` / `git diff --name-only` (6 paths, 23/47 lines; 0 `src/`, `.github/`, `pyproject.toml` paths) | ✅ PASS |
| **S3** Formatting-only — behaviour and asserted content preserved | `uv run pytest tests/ -q` (1766/6, EXIT=0, identical to pre-change baseline, 0 failures) + focused `test_ci_workflows.py test_coverage_contract.py` (22 passed) + AST/token identity across all six files | ✅ PASS (strongest gate) |
| **S4** No CI gate armed; recurrence owned by #194 | greps over `.github/workflows/**` = 0 matches in the post-state; `git diff -- .github/workflows/` empty ⇒ identical pre-state; enforcement remains the local `ruff-format` hook (`.pre-commit-config.yaml:7`) | ✅ PASS — **weakest evidence, see below** |
| **S5** Sibling gates stay green and unmoved | `ruff check` (all passed) · `mypy src/` (32 files clean) · `git diff --check` clean · `coverage run -m pytest` + `bash scripts/check_core_coverage.sh` (four rows 100%, empty `Missing`, exit 0) · flag-free `coverage report -m` 93% ≥ config `fail_under = 90` | ✅ PASS |

**Honest weakness flags (no gate softened).**

- **S4 is the weakest leg.** Its evidence is a *negative* static match: two zero-match greps plus an empty `.github/workflows/` diff. A zero-match grep is weaker than an exit-code gate — it would also pass if the pattern or path were wrong. Mitigations applied here: the workflow directory is confirmed to exist and contain three files (`ci.yml`, `codeql.yml`, `release.yml`), the pattern `ruff format` is the broad form, and pre-state equality is proven by the empty workflow diff rather than asserted. This is the best available evidence for "no gate was armed" short of CI history.
- **"Clean checkout" wording (S1) is satisfied as *working-tree* evidence, not a committed-checkout run.** HEAD is still `bdcff254…` with the reformat uncommitted (`git rev-parse HEAD` unchanged; `git status --porcelain` shows the six ` M` test files). The formatter gate ran on the working tree that the parent will commit; if the committed blob ever diverges from this working tree, S1 must be re-run at that revision. Flagged, not a failure.
- **S3 relies on a baseline captured, not re-capturable now.** The baseline `1766 passed, 6 skipped` can no longer be produced from this tree (the reformat already happened), so this verify pass *consumes* apply's ordering-disciplined baseline. It is cross-checked by two independent discriminators that do not depend on the baseline at all: the flag-free TOTAL coverage floor (93% ≥ 90) and AST/token identity, both of which would fail on a behaviour-changing edit.
- **PB-10's no-new-test contract and AGENTS.md rule 6.** PB-10's evidence is command-based by design, and the repo resolves this class the same way it already does: the `coverage` spec records measured percentages and the four 100.00% rows as verify-phase command evidence, explicitly not pytest-assertable, and `ci` CI-01's config-driven scenario plus the immediately preceding change's CI-07 delta (`2026-09-14-chore-python-version-313`) were mapped identically. Treated as satisfied by precedent; the accepted cost (no drift guard, a future reformat-shaped drift again escapes pytest) is stated here and owned by #194, never claimed closed by PB-10.

## Task completion

`tasks.md` scan for `^\s*- \[ \]` (unchecked implementation tasks): **0 matches** (`GREP_EXIT=1`); `^\s*- \[x\]` count: **9**. No unchecked implementation task lines remain, therefore no completeness blocker and no stale-checkbox reconciliation is needed. `tasks.md`, `proposal.md`, `design.md` and the spec delta were **not** modified by this phase — only `verify-report.md` was written. The apply-phase deferrals (4.1–4.4) are discharged above.

## Structured status / actionContext findings

- `apply: all_done`, `verify: ready`, `actionContext.mode: repo-local`, `workspaceRoot` = `allowedEditRoots` = `C:\Users\elaze\Desktop\sofer` — single allowed edit root, no `actionContext` warnings; every read and the one write stayed inside it.
- `artifactStore: openspec` matches the `nextRecommended: verify` path, so the non-authoritative store carve-out does not apply.
- No blocker conditions present: active change unambiguous; tasks artifact present and non-empty; implementation ownership provable inside the authoritative workspace (`git status --porcelain` = exactly the six expected test files plus this change's untracked SDD directory).
- `remediationState.required: false`, `blockedReasons: []`.

## Strict TDD compliance

**Not active — verified, not assumed.** `openspec/config.yaml` sets `strict_tdd: false` (and `testing.strict_tdd: false`); `tasks.md` states "`strict_tdd: false` … no RED → GREEN → TRIANGULATE → REFACTOR sequence applies"; `apply-progress.md` records the same. There is no behaviour to unit-test, so no `TDD Cycle Evidence` table is required and no CRITICAL TDD finding applies. Assertion-quality audit is likewise **N/A**: this change adds and modifies zero assertions (AST identity proves it), so there is no new test content to audit for tautologies, ghost loops, type-only or smoke-only assertions.

## Review workload / PR boundary findings

| Check | Finding |
| --- | --- |
| Forecast honoured | `tasks.md` forecast: single PR, no chaining, `400-line budget risk: Low` → confirmed. Diff is 6 test files, **23 insertions / 47 deletions** (~70 line-level changes), well under the 400-line canonical threshold. |
| Chained PRs | Not recommended and not used — one slice, no partial-PR boundary to validate. |
| `size:exception` | **Not used** and not requested — correctly, given the size. |
| Chain strategy | Unchanged/pending in `tasks.md`; correctly not exercised (single PR, `ask-on-risk` never had to fire). |
| Scope creep | **None found.** Only the six forecast files changed; zero `src/sofer/**`, `.github/**`, `pyproject.toml`, `.pre-commit-config.yaml`, `uv.lock`, `README*`, `CONTRIBUTING.md`, `openspec/specs/**`, `openspec/config.yaml`, or `openspec/changes/2026-09-14-chore-python-version-313/**`. |

## Accepted, owned limitations (not regressions, not fixed here)

1. **The drift class stays open.** No `ruff format --check` step exists in any workflow (0 matches), so an un-staged file can drift again — issue **#194** owns the decision to arm the gate and the resulting exposure. PB-10 deliberately does not claim to close it.
2. **Ruff pin mismatch remains.** `.pre-commit-config.yaml` pins `ruff-pre-commit` `v0.16.7`; ambient `uv run ruff` is `0.16.0` (the binary that produced this reformat and that PB-10's gate invokes). Issue **#195** owns alignment. Out of scope for a whitespace-only commit.
3. **Three pre-existing type diagnostics in `tests/test_mcp_registration.py`** (`__getitem__` on `object`; `str` → `AgentName` at two `resolve_config_path` sites) are **not** regressions and were **not** fixed. The token-identity check above independently confirms no NAME/STRING/OP content changed outside one parenthesis pair, so those lines are untouched; PB-10's non-goals forbid logic edits, and the project type gate is `uv run mypy src/` (source only), which is clean.

## Blockers

**None.** All five PB-10 scenarios pass; every gate exited 0 with the expected output; no unchecked implementation tasks remain. Rollback remains one `git revert`; nothing was committed, pushed, or published by this phase, and no `--no-verify`, tag movement, or artifact outside `verify-report.md` was touched.
