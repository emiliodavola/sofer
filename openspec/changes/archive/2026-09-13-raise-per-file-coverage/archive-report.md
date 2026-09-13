# Archive Report — 2026-09-13-raise-per-file-coverage

**Change**: `2026-09-13-raise-per-file-coverage` — Raise per-file coverage to ≥90% (CLI-core 100% mandate: `cli.py`/`scanner.py`/`prepare.py`/`publish.py` at 100.00% with zero pragmas + three ≥90 floors for `profile.py`/`mcp_registration.py`/`verification.py`)
**Issue**: GitHub **none** — coverage-policy/test change, no issue tracked
**Date**: 2026-09-13
**Artifact store**: `openspec` (repo `openspec/config.yaml` header notes hybrid openspec+engram; archive ran file-backed per the openspec rules, and this report is also shadowed to Engram — observation ID **1187**, topic `sdd/2026-09-13-raise-per-file-coverage/archive-report`, per the newest archived-report precedent)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and not yet opened as a PR** — see *Delivery*)
**Verify verdict**: **PASS** — 16/16 scenarios resolved (15 top-level + 1 nested COV-06 guard-execution scenario); full suite `1745 passed, 6 skipped` rc 0 under both `uv run pytest tests/ -q` and the coverage-instrumented run; four core rows **100.00** (zero missed, zero pragma tokens), three floor rows **96 / 99 / 100** (≥90), **TOTAL 93%** (≥90) rc 0; `scripts/check_core_coverage.sh` rc 0 (four scoped 100 gates); ruff + mypy + `git diff --check` clean; 0 blockers, 0 CRITICAL
**Branch**: `test/raise-coverage-90` @ working-tree diff — **2770 insertions / 8 deletions, ZERO `src/sofer/` paths** (Resolution A); **0 SDD-phase commits** (parent owns commits — explicit "do not commit" constraint)
**Archived path**: `openspec/changes/archive/2026-09-13-raise-per-file-coverage/`

## Summary

Paid the forcing-function debt armed by PR #172 (change `2026-09-13-ci-coverage-codeql`, `fail_under = 90` in `pyproject.toml`): the coverage gate on `dev` measured 88% and this change raises it to green with a **stricter, re-scoped contract** — strictly test-only, zero `src/sofer/` edits:

1. **CLI-core 100% mandate (COV-06)** — `src/sofer/cli.py`, `scanner.py`, `prepare.py`, `publish.py` each measure **100.00% line coverage** with **zero `# pragma: no cover`** tokens anywhere in the four files (`branch = true`, complete suite). Enforcement is per-file scoped gates inside one committed script, `scripts/check_core_coverage.sh` (`coverage report --include=src/sofer/<file>.py --fail-under=100 -m` ×4), referenced by a single `ci.yml` coverage-job step — additive, and **never** a mutation of the config-owned TOTAL gate (CI-01). AGENTS.md rule 14 makes the mandate binding repo policy.
2. **Three per-file ≥90 floors (COV-01, re-scoped)** — `profile.py` **96%**, `mcp_registration.py` **99%**, `verification.py` **100%** on the regenerated baseline; each row individually binding, verified on the CI-interpreter-shape measurement with recorded margin (+6/+9/+10 pp) plus an optional skip-if-absent contract guard.
3. **Green TOTAL gate (COV-02)** — **TOTAL 93%** ≥ 90, `uv run coverage report -m` rc 0; `fail_under = 90` untouched and still config-owned (`test_pyproject_declares_coverage_fail_under_90` green; `pyproject.toml` absent from the diff).
4. **Zero `src/sofer/` paths (COV-03, Resolution A, parent-authorized 2026-09-13)** — the dead `cli.py` `__main__` guard (1574-1575) is **KEPT** and becomes a covered line via an in-process `runpy.run_module("sofer.cli", run_name="__main__")` test (`test_cli_main_guard_executed_via_runpy`, asserts `SystemExit.code == 0`) — real execution under the coverage tracer, no pragma, no src edit; `python -m sofer.cli` keeps working (PB-02 subprocess boundary in `tests/conftest.py::run_cli` stays intact).
5. **COV-04 (cheapest-wins adjacent set) retired** — the core-100 overshoot lands TOTAL 93% ≥ 90 with margin; no adjacent fills, no scope creep.
6. **Amended `coverage` spec domain** (COV-01..COV-06, 16 scenarios, canonical-first) cross-referencing `ci` CI-01 and `process-boundary` PB-05; CI-01 S2 test narrowed (TOTAL-gate-only flag ban) and the `ci` canonical spec gained the documented one-line COV-06 carve-out clause (line 30).

**No commits were made by any SDD phase** (executor contract: parent owns versioning). Delivery is pending: work-unit commits → single PR into `dev` → parent review/merge.

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (`sync-report.md` status `synced`, archived with this change). Archive reads a *completed* sync; it does not perform one, and no archive-time sync fallback was needed (parent final-state facts confirm the canonical spec is synced). The only archive-time canonical edit is the provenance suffix amend recorded below.

| Field | Value |
|---|---|
| Domains synced | **`coverage`** (1 of 1) — **new domain** (`openspec/specs/coverage/` did not exist canonical); full copy of the change-local spec, not a deltas merge |
| ADDED requirements | **COV-01** Per-file coverage floor for the three second-tier modules (3 scenarios) · **COV-02** TOTAL ≥90 with the CI-01 config-owned gate green (3) · **COV-03** Bounded diff — zero `src/sofer/` paths, no pragmas in the core modules (3) · **COV-04** Cheapest-wins adjacent set — **RETIRED** in this change (0 scenarios; marker row kept in the Test Mapping) · **COV-05** Behavior-asserting tests only (2) · **COV-06** CLI-core 100% mandate with scoped gates (4 top-level + 1 nested guard-execution scenario = 5) — 6 requirements, **16 scenarios** total (15 top-level + 1 nested); Test Mapping lists 17 rows incl. the retired COV-04 marker |
| MODIFIED requirements | **none** |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical file | `openspec/specs/coverage/spec.md` (**created** at sync, 325 lines; canonical content = change-local spec verbatim + provenance blockquote, `diff` = `50a51`) |
| Change-local source | `openspec/changes/2026-09-13-raise-per-file-coverage/specs/coverage/spec.md` (323 lines, archived here) |
| Provenance note | `> Introduced by change \`2026-09-13-raise-per-file-coverage\` (2026-09-13).` (canonical line 51, closing `## Purpose`), matching the repo's blockquote convention (`openspec/specs/ci/spec.md:14`) |
| Archive-time sync fallback | **NOT executed and not needed** — `sync-report.md` status `synced` is present; the parent's final-state facts confirm the canonical `coverage` spec is synced |
| Destructive merge | **Not applicable** — ADD 6 / MODIFIED 0 / REMOVED 0; `openspec/config.yaml` `rules.archive` ("Warn before merging destructive deltas.") **honored** — nothing destructive was merged, no approval was required or given |
| Same-domain collisions | **none** — native status `relationships.sameDomainActiveChanges: []` / `collisions: []`; archive scan finds the only active (non-archive) change dir is this one, and its own artifacts are the only files mentioning `specs/coverage` |

### Provenance suffix amend (archive-time, parent-instructed)

The repo convention marks archived changes with an `(archived YYYY-MM-DD)` suffix (e.g. `2026-09-13-ci-coverage-codeql`'s `> Introduced by change \`2026-09-13-ci-coverage-codeql\` (archived 2026-09-13).`). Per the parent instruction, the canonical `coverage` provenance line was amended at archive:

```diff
- > Introduced by change `2026-09-13-raise-per-file-coverage` (2026-09-13).
+ > Introduced by change `2026-09-13-raise-per-file-coverage` (archived 2026-09-13).
```

Single-line provenance amend only — no requirement text, scenario, heading, or Test Mapping row touched. Archive date (2026-09-13) matches the provenance date, so no date correction was needed.

## Verification Evidence

| Gate | Result |
|---|---|
| Verify verdict | **PASS** — 0 blockers, 0 CRITICAL; 16/16 scenarios resolved (15 top-level + 1 nested), every scenario mapped to a green test or recorded verify-phase evidence (AGENTS.md rule 6; the 3 §14 parent gates are lifecycle markers, not implementations) |
| Pytest (full) | `uv run pytest tests/ -q` → **1745 passed, 6 skipped**, 14 warnings in 45.01s · coverage-instrumented `uv run coverage run -m pytest tests/ -q` → **1745 passed, 6 skipped**, 14 warnings in 60.49s (suite grows 1567 → 1745, +178; skips unchanged) |
| Coverage rows (COV-01/02/06) | `uv run coverage report -m` rc **0**: `cli.py 564/0 – 100%` · `scanner.py 159/0 – 100%` · `prepare.py 432/0 – 100%` · `publish.py 326/0 – 100%` (four core **100.00**, zero missed) · `mcp_registration.py 235/1 – 99%` · `profile.py 253/8 – 96%` · `verification.py 60/0 – 100%` (floors **≥90**; margins +6/+9/+10) · **TOTAL 5995 stmts / 365 missed / 2318 arcs / 166 missed — 93%** |
| COV-06 gate script | `bash scripts/check_core_coverage.sh` rc **0** — four scoped rows each `100%` (cli 564/0, scanner 159/0, prepare 432/0, publish 326/0); the rows the CI coverage job will reproduce |
| Negative TOTAL probe | `uv run coverage report --fail-under=95` → rc **2** (gate enforced — TOTAL 93 < 95); verify-only probe, never a workflow value |
| Quality gates | `uv run ruff check src/ tests/ scripts/` → "All checks passed!" (rc 0) · `uv run mypy src/ scripts/` → "Success: no issues found in 33 source files" (rc 0) · `git diff --check` → rc 0 (clean; benign CRLF-normalization warnings only) |
| Static contracts | `grep -rn "pragma: no cover"` over the four core modules → zero tokens (rc 1) · `grep -n "fail_under\|--fail-under\|fail-under"` in ci.yml + release.yml → zero hits (floors live only in `scripts/check_core_coverage.sh`) · `uv run pytest tests/test_cli.py::test_cli_main_guard_executed_via_runpy -q` → 1 passed · `uv run pytest tests/test_coverage_contract.py -q` (with `.coverage` removed) → `2 passed, 1 skipped` (floor guard skips on clean checkout) |
| CI-01 S2 narrowing | `test_coverage_gate_is_config_driven_without_cli_floor` re-scoped to the TOTAL gate only, with an added pinned assertion that the TOTAL report step stays the flag-free `uv run coverage report -m`; `test_coverage_job_gates_core_modules_at_100` + `test_agents_md_declares_core_100_mandate` green |
| Scope / conventions (COV-03) | `git diff origin/dev --stat` = **11 files changed, 2770 insertions(+), 8 deletions(-), ZERO `src/sofer/` paths** (Resolution A); no new dependencies; no `pytest-cov`/XML/Codecov; AGENTS.md rule 14 present; README/README_ES untouched (rule 13); `release.yml` deliberately NOT mirrored (bounded machinery) |
| Strict TDD | Inactive by configuration (`strict_tdd: false` in `openspec/config.yaml`); apply-progress records the TDD Cycle Evidence section correctly marked "Not applicable"; standard rule-6 verification performed |
| Assertion quality (COV-05) | Sampled new tests assert real observable outcomes (rc, capsys text, written artifacts, exceptions, `SystemExit.code == 0`); zero measured-percentage assertions in the test diff (the single `.coverage` read is the sanctioned skip-if-absent floor guard) |

Recorded non-critical residuals (verify-side reconciliations, within floors with margin): `mcp_registration.py` 99% (1 missed statement = provably-dead post-loop `return False`), `profile.py` 96% (8 provably-defensive/dead lines — gaps-empty, `out_path is None` guards, `base_rel` fallback), `verification.py` 100% (overshoots its floor). These are documented in apply-progress units B–H and are not archive blockers.

## Delivery

| Field | Value |
|---|---|
| Branch | `test/raise-coverage-90` @ working-tree diff; **0 SDD-phase commits** (`git status`: 12 tracked modifications + untracked `openspec/specs/coverage/`, `scripts/check_core_coverage.sh`, `tests/test_coverage_contract.py`, `openspec/changes/…`; nothing staged) |
| PR | **NOT yet opened** — parent-owned: work-unit commits → single PR against `dev` via `.github/PULL_REQUEST_TEMPLATE.md` (real verification output from the verify report; coverage rows, gate rows, suite count, ruff/mypy), assignee emiliodavola |
| Ask-on-risk gate | Measured `git diff origin/dev --stat` = **2770 changed lines**, crossing the 1500 threshold. The apply-progress records a **user-authorized provisional single-PR size exception (≤ ~3000 changed lines)**; 2770 < 3000, so the measured size sits within the recorded exception. Chain strategy was **never selected and is not invented** here; the final chain-vs-exception confirmation stays at the parent-owned delivery gate. The exception is recorded (not invented): user decision, not a silent adoption |
| Merge target | `dev` only (AGENTS.md rule 12); `main` receives changes only via release-time merges from `dev` |
| Issue close | **none** — no GitHub issue tracked for this change |
| Release / tag | **none** — no version bump (hatch-vcs derives version from tags); no tag pushed |
| Review workload | **2770 insertions / 8 deletions** across 11 files: `tests/test_cli.py` +739, `tests/test_prepare.py` +631, `tests/test_publish.py` +404, `tests/test_profile.py` +294, `tests/test_mcp_registration.py` +280, `tests/test_scanner.py` +222, `tests/test_splits.py` +96, `tests/test_ci_workflows.py` +72, AGENTS.md +28, ci.yml +7, `openspec/specs/ci/spec.md` +5 — within the recorded single-PR exception |
| Rollback | Revert the touched `tests/` + `tests/test_coverage_contract.py` + `scripts/check_core_coverage.sh` + ci.yml step + AGENTS.md rule 14 + the `ci` carve-out clause — one commit restores prior state; the `__main__` guard is KEPT (nothing to restore); TOTAL drops back below 90 as expected (the gate was deliberately armed as a forcing function) |

## Task Completion Gate (re-read immediately before the archive report write and the move)

Persisted tasks artifact re-read at `openspec/changes/2026-09-13-raise-per-file-coverage/tasks.md` **before** the report write and the folder move: **78/78 implementation task boxes are `[x]`** (`grep -c` = 78; units A–V all green per apply-progress + verify-report §1).

The **3 remaining unchecked `- [ ]` markers** are parent-owned lifecycle gates (`<!-- sdd-owner: parent -->`) — **none is an incomplete implementation task**. Exact lines (tasks.md §14):

```text
159: - [ ] Ask-on-risk gate: when the measured `git diff origin/dev --stat` crosses 1500 changed lines, PAUSE and request the user decision — chain vs size-exception; never invent a chain strategy or an exception. Record the decision in the verify report. <!-- sdd-owner: parent -->
160: - [ ] Post-apply bounded review of the full PR diff (review lens): assertion quality per COV-05, no pragma relapse, **zero `src/sofer/` paths** (Resolution A), gate-shape correctness, floor margins recorded. <!-- sdd-owner: parent -->
161: - [ ] Delivery: open the single PR against `dev` from `test/raise-coverage-90`, assign emiliodavola, fill the PR template (.github/PULL_REQUEST_TEMPLATE.md) with the real verification output from V — coverage rows, gate rows, suite count, ruff/mypy. <!-- sdd-owner: parent -->
```

**Reconciliation proof** (apply-progress.md + verify-report.md + parent final-state facts):

- **L159 (ask-on-risk)** — resolved/recorded, not incomplete: measured 2770 changed lines crossed 1500; verify-report §2 + apply-progress record the **user-authorized provisional single-PR size exception (≤ ~3000)**; 2770 is inside it. The residual is the parent's final delivery confirmation (chain vs exception), which remains open.
- **L160 (post-apply review)** — the verify-side audit covered assertion quality (COV-05), pragma absence, zero-src evidence, gate-shape correctness, floor margins; the parent's bounded review of the full PR diff remains a parent action.
- **L161 (delivery)** — no commits were made (parent hard constraint "Do NOT commit"); commit + single PR vs `dev` from `test/raise-coverage-90` (assignee emiliodavola, template from verify output) is parent-owned.

**Mechanical checkbox repair: NOT performed.** The parent did not instruct a stale-checkbox reconciliation, and flipping these boxes would misrepresent state — the tree is genuinely uncommitted (`git ls-files` on the change dir = 0 tracked files) and the boxes truthfully reflect pending parent action. The archive proceeds because **no `- [ ]` implementation task box remains**; the unchecked markers are audit state, not incomplete work, and the parent's final-state facts explicitly tasked this archive under the do-not-commit constraint.

## Structured Status & actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` | archive ran file-backed per the openspec rules; canonical merge was already performed by the sync phase; report also shadowed to Engram (`sdd/2026-09-13-raise-per-file-coverage/archive-report`, observation **1187**) since the repo config declares hybrid and the newest archived-report precedent does the same |
| `planningHome` | repo-local `openspec/` | change root existed; all required artifacts read from disk before the move (proposal, specs/coverage/spec.md, design, tasks, apply-progress, verify-report, sync-report, config.yaml) |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies; `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` contains every path written this pass (archive report, move target, canonical provenance edit) |
| `dependencies.sync` / `dependencies.archive` | `sync: blocked` / `archive: blocked` in the native JSON (pipeline order — sync waits on clean verify, archive waits on sync) | resolved from artifacts + parent final-state facts: verify PASS (16/16), `sync-report.md` status `synced`, canonical `openspec/specs/coverage/spec.md` present with the provenance note; archive readiness confirmed directly — no archive-time sync fallback needed |
| `taskProgress` | 78 total / 78 complete / 0 remaining / `unchecked: []` (implementation); `deferredParentActions` 3 remaining | actual persisted artifact confirms: 78/78 implementation `[x]`; 3 unchecked = parent-owned lifecycle gates (see Task Completion Gate) |
| `relationships.sameDomainActiveChanges` / `collisions` | `[]` / `[]` | archive's own scan found no other active change touching the `coverage` domain (the only active change dir is this one) |
| `rules.archive` | *"Warn before merging destructive deltas."* | honored — no destructive delta (ADD 6, MODIFIED 0, REMOVED 0); the sole canonical edit is the parent-instructed provenance suffix line |

## Archive Mechanics

- **`git mv` not applicable**: the whole change root is untracked (`git ls-files openspec/changes/2026-09-13-raise-per-file-coverage/` → **0 tracked files**; `git status` reports `?? openspec/changes/2026-09-13-raise-per-file-coverage/`). Move performed as a **plain filesystem rename** into `openspec/changes/archive/` — identical audit-trail outcome, since the parent's upcoming commit will add these files at their final archived path.
- Files archived (**8**, moved): `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `sync-report.md`, `specs/coverage/spec.md` + `archive-report.md` (additive, written into the change root **before** the move per the openspec-mode contract, then moved with the tree; repo convention per the `2026-09-13-ci-coverage-codeql` precedent).
- The vacated `openspec/changes/2026-09-13-raise-per-file-coverage/` tree was removed (empty).
- Audit trail intact: active artifacts were **moved, never deleted or modified**. The only content edit of the pass is the documented canonical `coverage` provenance suffix amend (`(2026-09-13)` → `(archived 2026-09-13)`, parent-instructed). Nothing under `src/`, `tests/`, `scripts/`, AGENTS.md, workflows, or any sibling active change dir was touched.
- **No commit made, nothing staged** (`git diff --cached` empty) — the parent versions the move and this report.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** revert the 12 touched implementation files (`tests/` ×10, AGENTS.md, ci.yml), delete `scripts/check_core_coverage.sh` + `tests/test_coverage_contract.py`, revert the `ci` canonical carve-out clause, and remove the canonical `openspec/specs/coverage/spec.md` domain file — one commit restores prior state; the `__main__` guard stays (Resolution A, nothing to restore); TOTAL drops back below 90 as the deliberately-armed forcing function expects.
- **Rollback of the archive move:** move the folder back to `openspec/changes/2026-09-13-raise-per-file-coverage/` and drop `archive-report.md` — lossless (originals unmodified, untracked, no history invalidated).
- **Next steps (parent-owned, remaining):** commit the work units in the recorded order on `test/raise-coverage-90`; open the **single PR against `dev`** (assignee emiliodavola, template filled with the real verification output from the verify report: coverage rows, gate rows, suite count, ruff/mypy); final chain-vs-exception confirmation (measured 2770 lines inside the recorded ≤ ~3000 single-PR exception); post-merge bounded review. Watch the **CI-arbiter result** (ubuntu / Python 3.13) — the four 100.00 rows are binary gates with no margin by design; floors carry margin (+6/+9/+10 over 90) and TOTAL carries +3.
- **Recorded follow-ups (out of scope, not created here):** none blocking — the prior change's pending-sync note for archived delta specs does not affect the `coverage` domain (written canonical-first); the `ci` canonical carve-out clause already landed (line 30).