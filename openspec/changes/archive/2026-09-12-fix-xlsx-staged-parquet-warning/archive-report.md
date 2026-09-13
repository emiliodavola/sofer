# Archive Report — 2026-09-12-fix-xlsx-staged-parquet-warning

**Change**: `fix-xlsx-staged-parquet-warning`
**Issue**: GitHub **#150** — `sofer_prepare` misleading `[!]` warning for multi-sheet XLSX when per-sheet staged Parquets exist under collapsed single-underscore names
**Date**: 2026-09-12
**Artifact store**: `openspec` (hybrid; engram shadow saved for this report — observation ID **1155**, topic `sdd/fix-xlsx-staged-parquet-warning/archive-report`)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and not yet opened as a PR** — see *Delivery*)
**Verify verdict**: **PASS** — `gentle-ai.verify-result/v1`, `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 3/3`, `scenarios: 13/13`, `test_exit_code: 0`, `build_exit_code: 0`
**Branch**: `fix/150-xlsx-staged-warning` @ `4a9e0d4` — working-tree diff (2 files, 248 insertions / 43 deletions, ~291 changed lines); no commits made by the SDD phases
**Archived path**: `openspec/changes/archive/2026-09-12-fix-xlsx-staged-parquet-warning/`

## Summary

Closes **#150**: `_build_schema_report_impl` searched only the spec-layout double-underscore glob
`stem__*.parquet` (plus the bare base `stem.parquet`), so multi-sheet XLSX entries whose per-sheet
Parquets were written by `prepare` under **collapsed single-underscore** names
(`normalize_parquet_remote` collapses `__+` → `_`) misfired the `[!] Staged Parquet '<base>.parquet'
not found … falling back to CSV inference.` warning — and silently degraded the schema to a
first-sheet-only re-read, dropping sheets ≥ 2 columns and per-sheet row counts from the schema report
and Dataset Card. The root cause is a **producer/consumer naming mismatch**, not a missing artifact.

Fix shape (design D1–D7, all as designed):
- One module-private `_staged_xlsx_sheet_parquets(staging_dir, parquet_key)` helper in
  `src/sofer/repo_compliance.py` used by **both** XLSX glob sites (AGENTS.md rule 4 — mirrors the
  established `_mirror.expanded_planned_remotes` / `prepare._check_local_overwrite` dual-layout
  precedent; primary `stem__*.parquet`, fallback `stem_*.parquet` excluding the bare base stem, `[]`
  on missing dir; no new imports).
- Two module-level template constants `_WARN_STAGED_PARQUET_MISSING` / `_WARN_STAGED_PARQUET_UNREADABLE`
  with the format-generic tail `falling back to original-file inference.` applied at all **four** print
  sites; `[!]` prefix, `Staged Parquet '{key}'` fragment, warn-once-by-key guards, and error
  classification preserved (grep `CSV inference` → zero hits).
- 4 new tests in `tests/test_repo_compliance.py` (`TestBuildSchemaReportXlsxStaged` + module-level
  `_stage_parquet` promotion + `_make_xlsx` helper); existing warn-path tests kept byte-identical.

Diff: **2 files, 248 insertions / 43 deletions** (~291 changed lines: `src/sofer/repo_compliance.py`
~+63/−43, `tests/test_repo_compliance.py` +185 fully additive). Out of scope respected: `_mirror.py`,
`prepare.py`, canonical specs, README/README_ES untouched.

**No commits were made by any SDD phase** (executor contract: parent versions). Delivery is pending:
commit → PR into `dev` → human approval/merge → manual issue close (dev does not auto-close).

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (`sync-report.md` status
`synced`, present in this archive). Archive reads a *completed* sync; it does not perform one.

| Field | Value |
|---|---|
| Domains synced | **`repo-compliance`** (1 of 1) |
| ADDED requirements | **`Staged per-sheet Parquet lookup accepts collapsed single-underscore names (RC-R22)`** — inserted after RC-R21, immediately before `## 5. Backward compatibility`; all 5 scenarios + provenance `> Added by change … (closes #150).` |
| MODIFIED requirements | **RC-Universal § 4.19** (`Schema report via staged Parquet for all convertible formats`) — dual-layout origin wording, first-sheet-only fallback for genuinely-missing multi-sheet Parquets documented as explicitly UNCHANGED, `(Previously, by fix-xlsx-staged-parquet-warning: …)` history note; 6 scenarios untouched. **RC-R14 § 4.15** (`Missing staged Parquet warns deterministically, then falls back to CSV`) — prose tail corrected `"CSV inference path"` → `"source-file fallback path"` with format-generic re-read wording; 2 scenarios untouched |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical file | `openspec/specs/repo-compliance/spec.md` (**modified in the worktree** — +121/−5 net per sync report; `git diff` shows exactly 3 hunks: § 4.15, § 4.19, RC-R22) |
| Insertion point | `### Requirement: Staged per-sheet Parquet lookup accepts collapsed single-underscore names (RC-R22)` at canonical **line 1300** (re-verified at archive), immediately after RC-R21 |
| Counts (canonical, re-verified at archive) | RC-R22 heading occurrences **exactly 1**; format reconciliations documented in sync-report (heading normalization to `### Requirement: <Title> (RC-R22)` convention, canonical `### 4.19 …` / `### 4.15 …` heading forms) |
| Archive-time sync fallback | **NOT executed and not needed** — `sync-report.md` status `synced` exists and the parent prompt mandated recording (not re-applying) the sync |
| Destructive merge | **Not applicable** — ADD 1, MODIFIED 2 (prose-only), REMOVED 0; `openspec/config.yaml` `rules.archive` ("Warn before merging destructive deltas.") **honored** — nothing destructive was merged, no approval was required or given |

**Precedent / where the sync record lives.** Unlike the `2026-09-09`/`2026-09-11` changes (which used
`sync-note.md`), this change recorded sync in a **`sync-report.md`** inside the change root
(`openspec/changes/fix-xlsx-staged-parquet-warning/sync-report.md`, schema `gentle-ai.sync-result/v1`),
which is archived with the change. Its content (delta names, canonical file, validation commands,
formatting reconciliations, collision scan) is folded into this report as recorded above.

**Active same-domain collisions: none.** Sync report scan (`grep '^### '` + `git diff`):
active changes `2026-09-12-fix-residual-parity` (codebook/mcp-server), `2026-09-12-fix-scan-parity-mcp`
(mcp-server), and `2026-09-12-test-cli-mcp-parity-guard` (no domain specs) do **not** touch
`openspec/specs/repo-compliance/spec.md`; native status `collisions: []`, `sameDomainActiveChanges: []`.

## Verification Evidence

| Gate | Result |
|---|---|
| Verify verdict | `pass` — `blockers: 0`, `critical_findings: 0`, `requirements: 3/3`, `scenarios: 13/13` (machine-readable envelope at the head of `verify-report.md`) |
| RC-R22 scenario → test coverage | **5/5** (AGENTS.md rule 6): S1→`test_multi_sheet_collapsed_staged_parquets_stay_silent`, S2→`test_multi_sheet_spec_layout_double_underscore_stays_silent`, S3→`test_single_sheet_staged_parquet_stays_silent`, S4→existing `test_missing_parquet_warns_once_and_falls_back_to_csv` + `test_missing_parquet_warns_once_per_unique_key` (unmodified), S5→`test_multi_sheet_missing_staged_parquet_still_warns_once` — all non-vacuous (RED pre-fix documented for S1/S5; regression-guard for S2/S3/S4) |
| Pytest (full) | `PYTHONIOENCODING=utf-8 uv run pytest tests/ -q` → **1528 passed, 6 skipped**, 13 warnings, exit 0 — baseline 1524/6 + exactly the 4 new tests (additive only, no new dependencies) |
| Pytest (focused) | `tests/test_repo_compliance.py -q` → **185 passed**; `-k TestBuildSchemaReportXlsxStaged` → **4 passed, 181 deselected** |
| Lint / type / whitespace | `uv run ruff check src/ tests/` → "All checks passed!" · `uv run ruff format --check src/ tests/` → "65 files already formatted" · `uv run mypy src/` → "Success: no issues found in 32 source files" · `git diff --check` → clean |
| Scope / AGENTS.md checks | rule 4 (no duplicated logic — single shared helper at both glob sites), rule 1 (only new literals are the two warning constants), rule 6 (every RC-R22 scenario → a test), rule 3 (config read, no hardcoded defaults), no `CSV inference` tail in src/tests; `_mirror.py`/`prepare.py`/README untouched |
| Strict TDD | Inactive by configuration (`strict_tdd: false` in `config.yaml`); RED-first documented where practical (2.3/2.6 were RED pre-fix); assertion-quality audit performed — no tautologies/ghost loops/type-only asserts |
| File hashes (post-apply) | `repo_compliance.py` `a4882f99…c939`; `test_repo_compliance.py` `02dadf5d…a51b` (match apply-progress and verify) |

## Delivery

| Field | Value |
|---|---|
| Branch | `fix/150-xlsx-staged-warning` @ `4a9e0d4` — working-tree diff; **0 SDD-phase commits** (`git status`: 3 tracked modifications + untracked archive dir, nothing staged) |
| PR | **NOT yet opened** — parent-owned (row 4.4 remaining parent action): commit → PR into `dev` via `.github/PULL_REQUEST_TEMPLATE.md` with `Closes #150`, real gate output, and the SDD artifacts section |
| Merge target | `dev` only (AGENTS.md rule 12); `main` receives changes only via release-time merges from `dev` |
| Issue close | **manual after merge** by the parent — dev does not auto-close #150 |
| Release / tag | **none** — no version bump (hatch-vcs derives version from tags) |
| Review workload | **~291 changed lines** (248+/43−) — inside the 400-line canonical budget; **single PR**, no chaining, no `size:exception` (parent measured; budget risk Low) |
| Rollback | single-commit revert of `repo_compliance.py` + `test_repo_compliance.py` + delete of the change-local spec delta; no data/config/on-disk artifact touched |

## Task Completion Gate (re-read immediately before the archive move)

Persisted tasks artifact re-read at `openspec/changes/fix-xlsx-staged-parquet-warning/tasks.md` **before**
the move; after reconciliation (below) it holds **zero `- [ ]` markers** — 17/17 implementation rows
(`[x]`, Phases 1–3, with evidence lines) **+ 4/4 parent-owned rows** (Phase 4, `[x]`).

### Stale-checkbox reconciliation (exceptional, parent-instructed — recorded per contract)

- **Instruction**: parent FINAL-STATE HANDOFF declared, "The 4 parent rows of tasks.md (4.1-4.4) are
  considered complete at close by this parent handoff (spec delta verified, verify written, canonical
  synced, bounded review measured + archive now executing)" and the job's final-state facts require
  "tasks 17/17 + 4 parent rows all complete now at close" — an explicit instruction to treat the four
  unchecked rows as complete at archive time.
- **Proof** (apply-progress + verify-report + sync-report + parent measurement): 4.1 spec delta present
  and complete (verify-report: RC-R22 5 scenarios + §4.19 dual-layout + RC-R14 tail all in the
  change-local spec; heading inventory re-checked at archive); 4.2 verify doc populated — per repo
  convention the file is `verify-report.md` (the tasks.md "verify.md" wording is a generic reference,
  per verify-report); 4.3 canonical sync complete (`sync-report.md` status `synced`; RC-R22 at canonical
  :1300 re-verified at archive); 4.4 bounded review measured by the parent (~291 changed lines, inside
  the 400-line budget, single PR) with archive now executing.
- **Lines changed in `tasks.md`** (flip `- [ ]` → `- [x]`, lines 130–133 of the pre-move file):
  - `4.1 …` — `[x]` (row text otherwise byte-identical)
  - `4.2 Populate openspec/changes/fix-xlsx-staged-parquet-warning/verify.md …` — `[x]` **and**
    filename corrected `verify.md` → `verify-report.md` to match the repo's actual artifact name
    (the file exists in this archive; the old wording referenced a file that never existed)
  - `4.3 …` — `[x]` (row text otherwise byte-identical)
  - `4.4 …` — `[x]` (row text otherwise byte-identical)
- No other edit was made to `tasks.md`; all 17 implementation rows were already `[x]` with evidence and
  were untouched.

## Structured Status & actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` (hybrid) | archive ran file-backed per the openspec rules; canonical merge had already been performed by the sync phase; archive report also shadowed to Engram (`sdd/fix-xlsx-staged-parquet-warning/archive-report`) since hybrid mode and memory tools are available |
| `planningHome` | repo-local `openspec/` | change root existed; all required artifacts read from disk before the move |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies; `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` contains every path written (archive target + report inside the root) |
| Change selection | ambiguous in the injected status JSON (`nextRecommended: "Change selection is ambiguous: …"` listing this change among three `2026-09-12-*` siblings; `blockedReasons` identical) | **superseded by the parent prompt**, which explicitly selected `fix-xlsx-staged-parquet-warning` (matching branch `fix/150-xlsx-staged-warning` and the archive edit surfaces). The non-authoritative-store carve-out applies to the sibling `2026-09-12-*` dirs, which remain active and were **not** touched by this archive |
| `taskProgress` | 0/0 surfaced (selection unresolved) | actual persisted artifact: 21/21 task rows `[x]` after reconciliation — Final Task Completion Gate passes with zero unchecked markers |
| `dependencies.archive` | `blocked` in the JSON (selection) | resolved by the parent's explicit pin; verify PASS with 0 blockers and sync complete — archive readiness confirmed directly from artifacts |
| `sameDomainActiveChanges` / `collisions` | not surfaced / empty | archive's own scan (sync-report + re-checks) found no other active change touching `repo-compliance` |
| `rules.archive` | *"Warn before merging destructive deltas."* | honored — no destructive delta (ADD 1, MODIFIED prose-only 2, REMOVED 0) |

## Archive Mechanics

- **`git mv` not applicable**: the whole change root was untracked (`git ls-files` → 0 tracked files;
  `git status` reported `?? openspec/changes/fix-xlsx-staged-parquet-warning/`). Move performed as a
  **plain filesystem rename** into `openspec/changes/archive/` — identical audit-trail outcome, since
  the parent's upcoming commit will add these files at their final archived path.
- Files archived (**8**, moved; **1** written): `proposal.md`, `exploration.md`, `design.md`,
  `tasks.md`, `apply-progress.md`, `verify-report.md`, `sync-report.md`,
  `specs/repo-compliance/spec.md` (moved) + `archive-report.md` (additive, written at the archived path
  after the move — repo convention per `2026-09-11-*` precedents).
- The vacated `openspec/changes/fix-xlsx-staged-parquet-warning/` tree was removed (empty).
- Audit trail intact: active artifacts were **moved, never deleted or modified** (the sole content edit
  of the pass is the documented tasks.md 4.x checkbox reconciliation above). Nothing under
  `openspec/specs/` (already synced), `src/`, `tests/`, README files, or the sibling `2026-09-12-*`
  active change dirs was touched.
- **No commit made, nothing staged** (`git diff --cached` empty) — the parent versions the move and
  this report. Worktree change set after the move is the same 3 tracked modifications
  (`openspec/specs/repo-compliance/spec.md`, `src/sofer/repo_compliance.py`,
  `tests/test_repo_compliance.py`) plus the untracked archive dir.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** `git checkout -- src/sofer/repo_compliance.py
  tests/test_repo_compliance.py` (or `git revert` once committed); the canonical RC-R22 block + §4.19 /
  RC-R14 amendments would then need manual removal from `openspec/specs/repo-compliance/spec.md`
  (RC-R22 block + provenance, canonical ~:1300 onward, ending before `## 5. Backward compatibility`).
- **Rollback of the archive move:** move the folder back to
  `openspec/changes/fix-xlsx-staged-parquet-warning/` and drop `archive-report.md` — lossless: originals
  unmodified (except the documented tasks.md checkbox reconciliation) and untracked, so no history is
  invalidated.
- **Next steps (parent-owned, remaining):** commit the 2 code/test files **+ `openspec/specs/repo-compliance/spec.md`**
  + the archived change dir on `fix/150-xlsx-staged-warning`, open the single PR into `dev` with the
  template's sections filled with real gate output, run the post-merge bounded review, then **manually
  close issue #150** after merge (dev does not auto-close). No tag, no release.
- **Recorded follow-ups (out of scope, not created here):** (a) unify
  `_mirror.expanded_planned_remotes` / `prepare._check_local_overwrite` onto the new
  `_staged_xlsx_sheet_parquets` in a later change (identical logic, already test-covered); (b) optional
  modernization of RC-R14 eligibility prose ("CSV remote") superseded by RC-Universal §4.19 — left
  untouched to keep this delta minimal.