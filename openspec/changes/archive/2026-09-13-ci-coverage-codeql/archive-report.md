# Archive Report — 2026-09-13-ci-coverage-codeql

**Change**: `ci-coverage-codeql` — CI coverage gate at 90% + CodeQL Advanced Setup scanning
**Issue**: GitHub **none** — CI-infra change, no issue tracked
**Date**: 2026-09-13
**Artifact store**: `openspec` (hybrid; engram shadow saved for this report — observation ID **1178**, topic `sdd/2026-09-13-ci-coverage-codeql/archive-report`)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and not yet opened as a PR** — see *Delivery*)
**Verify verdict**: **PASS** — full suite `1567 passed, 6 skipped` rc 0; new module `tests/test_ci_workflows.py` 16 passed; ruff + mypy clean; `git diff --check` clean; 17/17 scenarios resolved (15 pytest-assertable + 2 verify-phase static evidence); 0 blockers, 0 CRITICAL. The coverage gate at 90 (measured 88% today) is **red by design** — the user-chosen forcing function (proposal + apply addendum, 2026-09-13), not a failure; the exit-code contract is proven by probes (V1 rc 2, V1b `--fail-under=88` rc 0, V2 `--fail-under=100` rc 2)
**Branch**: `feat/ci-coverage-codeql` @ working-tree diff — ~528 changed lines; **0 SDD-phase commits** (parent owns commits — explicit "do not commit" constraint)
**Archived path**: `openspec/changes/archive/2026-09-13-ci-coverage-codeql/`

## Summary

Added sofer's first CI quality/security guarantees, with **zero `src/sofer/` changes** and no new dependencies:

1. **Coverage gate at 90%** — the floor lives in `pyproject.toml` `[tool.coverage.report] fail_under = 90`
   (config-owned; value lifted 85→90 by user directive 2026-09-13). No workflow carries a threshold
   literal or `--fail-under=N` flag (CI-01 — coverage.py enforces the config floor itself). A dedicated
   `coverage` job in both `ci.yml` (standalone) and `release.yml` (`needs: [lint, test]`; feeds
   `build`/`citation-check`/`release`) runs the complete suite under instrumentation
   (`uv run coverage run -m pytest`), reports `-m` (missing lines → job log), and uploads `htmlcov` as a
   self-hosted artifact. No Codecov, no XML, no badge (CI-02). A tag push below the floor produces no
   release — `coverage` is a direct `needs` of `build`/`citation-check`/`release` (CI-03, needs-DAG proof).
2. **CodeQL Advanced Setup** — versioned `.github/workflows/codeql.yml` (push + PR to `main`/`dev`,
   weekly `schedule` cron `"0 3 * * 1"`) with `.github/codeql/config.yml` (`paths-ignore` for non-code
   trees `docs/`, `.github/`, `openspec/`, `cache/`, `tmp/`; `src/sofer/` deliberately NOT listed).
   `permissions: security-events: write` enables SARIF upload to the Security tab (CI-04, CI-05).
3. **Config + docs truth** — `openspec/config.yaml` declares coverage available at **90**
   (`testing.coverage.available: true`, `command`, `rules.verify.coverage_threshold: 90`; CI-06 S1);
   CONTRIBUTING documents the floor and commands; README.md + README_ES.md carry a mirrored
   quality-gates/CI section (rule 13); PR template checklist gains a coverage item.

New `ci` spec domain (CI-01..CI-06, 17 scenarios) pins all contracts; the only new module is the
static-inspection suite `tests/test_ci_workflows.py` (16 tests = 15 scenario-mapped + 1 presence guard).

**No commits were made by any SDD phase** (executor contract: parent owns versioning). Delivery is
pending: commit → single PR into `dev` → review/merge by the parent.

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (`sync-report.md` status
`synced`, archived with this change). Archive reads a *completed* sync; it does not perform one. The
only archive-time canonical edit is the provenance suffix amend recorded below.

| Field | Value |
|---|---|
| Domains synced | **`ci`** (1 of 1) — **new domain** (no `openspec/specs/ci/` existed canonical); full copy, not a deltas merge |
| ADDED requirements | **CI-01 Coverage gate in config** (3 scenarios) · **CI-02 Self-hosted coverage evidence** (3) · **CI-03 Release gated on the coverage job** (2) · **CI-04 CodeQL scan cadence and SARIF upload** (3) · **CI-05 CodeQL Advanced Setup config with paths-ignore** (2) · **CI-06 Declared coverage config and documentation truth** (4) — 6 requirements, 17 scenarios total |
| MODIFIED requirements | **none** |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical file | `openspec/specs/ci/spec.md` (**created** at sync, 239 lines; `git diff` vs change-local spec = exactly the provenance blockquote, 2 lines) |
| Change-local source | `openspec/changes/2026-09-13-ci-coverage-codeql/specs/ci/spec.md` (237 lines, archived here) |
| Provenance note | `> Introduced by change \`2026-09-13-ci-coverage-codeql\` (2026-09-13).` under `## Purpose` (canonical line 14), matching the repo's blockquote convention |
| Archive-time sync fallback | **NOT executed and not needed** — `sync-report.md` status `synced` is present; the parent's final-state facts confirm G.3 satisfied |
| Destructive merge | **Not applicable** — ADD 6 / MODIFIED 0 / REMOVED 0; `openspec/config.yaml` `rules.archive` ("Warn before merging destructive deltas.") **honored** — nothing destructive was merged, no approval was required or given |
| Same-domain collisions | **none** — archive scan (`grep -rln 'specs/ci' openspec/changes/*/specs/`) finds no other active change touching the `ci` domain; native status `collisions: []` / `sameDomainActiveChanges: []` |

### Provenance suffix amend (archive-time, parent-instructed)

The repo convention marks archived changes with an `(archived YYYY-MM-DD)` suffix (e.g.
`> Added by change \`installable-cli-pypi\` (archived 2026-08-26).` in `openspec/specs/cli/spec.md`).
Per the parent instruction ("add the provenance suffix if the repo convention marks archived changes"),
the canonical `ci` provenance line was amended at archive:

```diff
- > Introduced by change `2026-09-13-ci-coverage-codeql` (2026-09-13).
+ > Introduced by change `2026-09-13-ci-coverage-codeql` (archived 2026-09-13).
```

Single-line provenance amend only — no requirement text, scenario, or heading touched. Archive date
(2026-09-13) matches the provenance date, so no date correction was needed.

## Verification Evidence

| Gate | Result |
|---|---|
| Verify verdict | **PASS** — 0 blockers, 0 CRITICAL; 17/17 scenarios resolved (15 pytest-assertable → `tests/test_ci_workflows.py`; 2 static evidence per the PB-05/MSP-R12 precedent: CI-03 S2 needs-DAG proof, CI-06 S3 README/README_ES mirror diff) |
| Pytest (full) | `uv run pytest tests/ -q` → **1567 passed, 6 skipped**, 13 warnings, exit 0 (baseline 1551 + this module's 16; suite never regresses) |
| Pytest (module) | `uv run pytest tests/test_ci_workflows.py -q` → **16 passed** (test #13 RUNS — `openspec/config.yaml` present locally; skips with a documented guard when absent) |
| Lint / type / whitespace | `uv run ruff check src/ tests/ scripts/` → "All checks passed!" · `uv run mypy src/ scripts/` → "Success: no issues found in 33 source files" · `git diff --check` → clean |
| Coverage gate probes | V1 `uv run coverage report -m` (config `fail_under = 90`, no flag) → **rc 2** (TOTAL 88% < 90, red by design, missing lines listed) · V1b `--fail-under=88` → rc 0 · V2 `--fail-under=100` → rc 2. Same `.coverage` dataset proves the config-driven exit-code contract end-to-end; probes are verify-phase evidence only, never a workflow value |
| CI-01 anti-pattern guard | Raw-text scan of ci.yml + release.yml: **zero** hits for `fail_under` / `--fail-under` / `fail-under`; floor value exists only at `pyproject.toml:98` |
| Scope / conventions | Zero `src/sofer/` changes; no new dependencies (coverage.py + pyyaml already present; no pytest-cov); PB-05 (`uv run pytest -v` CI gate) untouched; README/README_ES mirrored in one working change (rule 13); no badge added |
| Strict TDD | Inactive by configuration (`strict_tdd: false` in `openspec/config.yaml`); C-phase suite authored GREEN-last by construction (asserts A+B+D+E content) |

## Delivery

| Field | Value |
|---|---|
| Branch | `feat/ci-coverage-codeql` @ working-tree diff; **0 SDD-phase commits** (`git status`: 10 tracked modifications + untracked `.github/codeql/`, `codeql.yml`, `tests/test_ci_workflows.py`, `openspec/changes/…`, `openspec/specs/ci/`; nothing staged) |
| PR | **NOT yet opened** — parent-owned: commit → single PR into `dev` via `.github/PULL_REQUEST_TEMPLATE.md` (coverage-gate checklist item now included) with real gate output and the SDD artifacts section |
| Merge target | `dev` only (AGENTS.md rule 12); `main` receives changes only via release-time merges from `dev` |
| Issue close | **none** — no GitHub issue tracked for this infra change |
| Release / tag | **none** — no version bump (hatch-vcs derives version from tags); a tag push below 90% would be blocked by the new release `coverage` gate by design |
| Review workload | **~528 changed lines** (tracked +122/−6 = 128 + new `codeql.yml` 37 + `codeql/config.yml` 13 + `test_ci_workflows.py` 350 ≈ 528) — the 400-line monitor FIRED at apply → ask-on-risk → **explicit user authorization of `size:exception` up to 1500 lines, single PR** (proposal + apply-progress amendment, 2026-09-13); the ~528-line diff is inside the authorized budget. `size:exception` explicitly recorded; no re-chaining required |
| Rollback | Remove `fail_under = 90` from pyproject + delete both `coverage` jobs + delete `codeql.yml`/`.github/codeql/` + revert doc/template/config edits — one commit restores prior state; no production code, no dataset behavior touched |

## Task Completion Gate (re-read immediately before the archive report write and the move)

Persisted tasks artifact re-read at `openspec/changes/2026-09-13-ci-coverage-codeql/tasks.md` **before**
the report write and the folder move: **22/22 implementation task boxes are `[x]`** (baseline + A.1–A.3,
B.1–B.2, D.1–D.4, E.1–E.2, C.1–C.5, V.1–V.5; all gates green per apply-progress + verify-report §1).

The **9 remaining unchecked `- [ ]` markers** are commit/ownership/parent-gate markers — **none is an
incomplete implementation task**. Exact lines (tasks.md):

```text
L29  - [ ] Working tree is on `feat/ci-coverage-codeql`; the SDD artifacts (proposal, spec, design) are committed; tree is otherwise clean.
L39  - [ ] A.4 — Verify and commit A as one work unit …
L47  - [ ] B.3 — Verify both files parse … commit B as one work unit.
L57  - [ ] D.5 — Verify D … commit D as one work unit.
L73  - [ ] C.6 — Commit C as one work unit.
L82  - [ ] V.6 — Write … verify-report.md … commit the SDD artifacts (tasks.md, verify-report.md) …
L86  - [ ] G.1 — Bounded post-apply review …          <!-- sdd-owner: parent -->
L87  - [ ] G.2 — Lifecycle gate (delivery) …          <!-- sdd-owner: parent -->
L88  - [ ] G.3 — Lifecycle gate (spec promotion) …    <!-- sdd-owner: parent -->
```

**Reconciliation proof** (apply-progress.md + verify-report.md + parent final-state facts):

- **A.4 / B.3 / D.5 / C.6** — the verify halves are proven done: apply-progress records "verify done;
  commit deferred to parent" per row; verify-report §1 gates G1–G5 all rc 0. The only remaining action
  in each row is **the commit**, which the parent owns ("Do NOT commit; the parent owns commits").
- **V.6** — `verify-report.md` exists (written at apply; rewritten authoritative by the verify phase,
  2026-09-13); its commit is parent-deferred.
- **L29** — all SDD artifacts exist (proposal/spec/design/tasks/apply-progress/verify-report/
  sync-report archived here); the commit of that tree is parent-owned.
- **G.1 / G.2 / G.3** — parent-owned lifecycle gates. **G.3 resolved**: `sync-report.md` status
  `synced` and the canonical `openspec/specs/ci/spec.md` exist (parent final-state fact: "Canonical spec
  already synced … G.3 satisfied"). **G.2 resolved**: delivery decided by the user's explicit
  `size:exception` up to 1500 lines, single PR (V.5 monitor FIRED → ask-on-risk → explicit authorization;
  apply-progress addendum). **G.1 resolved**: bounded review measured by the parent (~528 lines, inside
  the authorized budget).

**Mechanical checkbox repair: NOT performed.** The parent did not instruct a stale-checkbox
reconciliation, and flipping these boxes would misrepresent state — the tree is genuinely uncommitted
(`git ls-files` on the change dir = 0 tracked files) and the boxes truthfully reflect the pending
parent commits. The archive proceeds because no `- [ ]` **implementation** task box remains; the
unchecked markers are audit state, not incomplete work, and the parent final-state facts explicitly
tasked this archive under the do-not-commit constraint.

## Structured Status & actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` (hybrid) | archive ran file-backed per the openspec rules; canonical merge was already performed by the sync phase; archive report also shadowed to Engram (`sdd/2026-09-13-ci-coverage-codeql/archive-report`, observation **1178**) since hybrid mode and memory tools are available |
| `planningHome` | repo-local `openspec/` | change root existed; all required artifacts read from disk before the move |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies; `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` contains every path written this pass (archive report, move target, canonical provenance edit) |
| Change selection | ambiguous in the injected status JSON (`nextRecommended`/`blockedReasons`: "Change selection is ambiguous: …" listing this change among 7 candidates; `changeName: null`, `dependencies.archive: blocked`) | **superseded by the parent prompt**, which explicitly selected `2026-09-13-ci-coverage-codeql` (matching branch `feat/ci-coverage-codeql` and the change-boundary spec `specs/ci/spec.md`). Sibling `2026-09-12-*` / `2026-09-13-*` active dirs were **not** touched |
| `taskProgress` | 0/0 surfaced (selection unresolved) | actual persisted artifact: 22/22 implementation `[x]`; 9 unchecked = commit/ownership/parent-gate markers (see Task Completion Gate) |
| `dependencies.archive` | `blocked` in the JSON (selection) | resolved by the parent's explicit pin; verify PASS with 0 blockers, sync-report `synced`, no same-domain collisions — archive readiness confirmed directly from artifacts |
| `sameDomainActiveChanges` / `collisions` | not surfaced / empty | archive's own scan found no other active change touching `ci` (sync-report + `grep -rln 'specs/ci'`) |
| `rules.archive` | *"Warn before merging destructive deltas."* | honored — no destructive delta (ADD 6, MODIFIED 0, REMOVED 0); the sole canonical edit is the parent-instructed provenance suffix line |

## Archive Mechanics

- **`git mv` not applicable**: the whole change root is untracked (`git ls-files openspec/changes/2026-09-13-ci-coverage-codeql/` → **0 tracked files**; `git status` reports `?? openspec/changes/2026-09-13-ci-coverage-codeql/`). Move performed as a **plain filesystem rename** into `openspec/changes/archive/` — identical audit-trail outcome, since the parent's upcoming commit will add these files at their final archived path.
- Files archived (**8**, moved): `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `sync-report.md`, `specs/ci/spec.md` + `archive-report.md` (additive, written into the change root **before** the move per the openspec-mode contract, then moved with the tree; repo convention per `2026-09-11`/`2026-09-12` precedents).
- The vacated `openspec/changes/2026-09-13-ci-coverage-codeql/` tree was removed (empty).
- Audit trail intact: active artifacts were **moved, never deleted or modified**. The only content edit of the pass is the documented canonical `ci` provenance suffix amend (`(2026-09-13)` → `(archived 2026-09-13)`, parent-instructed). Nothing under `src/`, `tests/`, README files, workflows, or the sibling active change dirs was touched.
- **No commit made, nothing staged** (`git diff --cached` empty) — the parent versions the move and this report.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** revert `pyproject.toml` (`fail_under = 90`), both workflow `coverage`
  jobs, delete `codeql.yml` + `.github/codeql/` + `tests/test_ci_workflows.py`, revert CONTRIBUTING /
  README / README_ES / PR template, and remove the canonical `openspec/specs/ci/spec.md` domain file —
  one commit restores prior state; no production code or dataset behavior involved.
- **Rollback of the archive move:** move the folder back to `openspec/changes/2026-09-13-ci-coverage-codeql/`
  and drop `archive-report.md` — lossless (originals unmodified, untracked, no history invalidated).
- **Next steps (parent-owned, remaining):** commit the 10 modified implementation files + the 3 new
  files + `openspec/specs/ci/spec.md` + the archived change dir on `feat/ci-coverage-codeql`; open the
  single PR into `dev` (template sections filled with real gate output; coverage-gate checklist item
  already present); post-merge bounded review; optionally delete the `.pi-lens.json` guard file
  (untracked apply-phase incident artifact). No tag, no release.
- **Recorded follow-ups (out of scope, not created here):** a coverage-raising change to turn the red
  gate green — per-file gaps `cli.py` 84%, `profile.py` 80%, `mcp_registration.py` 80%, `publish.py`
  87% against the 90% total floor; the floor itself may only be relaxed via a spec change to CI-01.