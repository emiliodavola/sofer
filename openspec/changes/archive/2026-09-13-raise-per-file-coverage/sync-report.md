# Sync Report — Raise per-file coverage to ≥90% (CLI-core 100% mandate)

**Status: SYNCED** (canonical spec promotion; change stays active — archive is a separate phase).

## 1. What was synced

| Item | Value |
| --- | --- |
| Change | `2026-09-13-raise-per-file-coverage` (branch `test/raise-coverage-90`, base `dev`) |
| Artifact store | openspec (native status `artifactStore: openspec`; `openspec/config.yaml` header notes hybrid openspec+engram — sync report persisted to both) |
| Delta kind | **New-domain spec** (no `openspec/specs/coverage/` existed canonical) — full copy, not a deltas merge |
| Domain(s) synced | `coverage` |
| Canonical file(s) updated | `openspec/specs/coverage/spec.md` (created, 325 lines) |
| Change-local source | `openspec/changes/2026-09-13-raise-per-file-coverage/specs/coverage/spec.md` (323 lines) |
| Provenance note added | `> Introduced by change \`2026-09-13-raise-per-file-coverage\` (2026-09-13).` closing the `## Purpose` section (after the amendment blockquotes, immediately before `## Requirements`), matching the repo's blockquote convention (`openspec/specs/ci/spec.md:14` uses the identical `> Introduced by change ...` shape; `packaging`/`mcp-server` use `> Added by change ...`). The change is not archived yet, so no `(archived …)` suffix |

Canonical content is the change-local spec **verbatim** (Purpose + Requirements COV-01..COV-06 + 16 scenarios + the Test Mapping table), plus the single provenance line. Only diff vs the change-local spec: the provenance blockquote (1 added line, `diff` = `50a51`). Line endings normalized to LF per `.gitattributes` (`* text=auto eol=lf`), no BOM, matching all existing `openspec/specs/*/spec.md`.

## 2. Requirements and scenarios

- COV-01 Per-file coverage floor for the three second-tier modules (`profile.py`/`mcp_registration.py`/`verification.py` ≥90) — 3 scenarios
- COV-02 TOTAL ≥90 with the CI-01 config-owned gate green — 3 scenarios
- COV-03 Bounded diff — zero `src/sofer/` paths, no pragmas in the core modules — 3 scenarios
- COV-04 Cheapest-wins adjacent set — **RETIRED** in this change — 0 scenarios (marker row kept)
- COV-05 Behavior-asserting tests only — 2 scenarios
- COV-06 CLI-core 100% mandate with scoped gates — 4 top-level + 1 nested guard-execution scenario = 5 scenarios

**16 scenarios total** (15 top-level + 1 nested `#### Scenario:` under COV-06, matching the verify report count); the `## Test Mapping` table lists 17 rows (the retired COV-04 marker row is included). Every scenario maps to a green test or recorded verify-phase evidence (AGENTS.md rule 6; verify report: PASS, 16/16 resolved).

## 3. Guards and checks

- Verify report read: **PASS** (implementation verification clean) — all 16 scenarios mapped to evidence; no unresolved FAIL/BLOCKED/CRITICAL; `sync: blocked` at resolution was the pipeline order (waits on clean verify — now available).
- No `## RENAMED Requirements` in the spec (new domain, full spec — nothing to rename; delta-marker scan for ADDED/MODIFIED/REMOVED/RENAMED clean).
- Legacy flat spec check: none — change ships `specs/coverage/spec.md` (domain dir present). `openspec/specs/coverage/` did not exist before this sync.
- Same-domain collisions: **none** — native status `relationships.sameDomainActiveChanges: []` and `collisions: []`; the only active (non-archive) change directory is this change.
- Destructive sync: none (new-domain ADDED-only full copy; no REMOVED, no large MODIFIED blocks; no approval needed).
- `rules.sync` in `openspec/config.yaml`: not present (config defines proposal/specs/design/tasks/apply/verify/archive only) — no additional sync rules to apply.
- Validation performed: structural check — 1 top-level heading, 6 `### Requirement:` blocks (COV-01..COV-06), 16 `#### Scenario:` blocks (15 top-level + 1 nested), 1 `## Test Mapping` table with 17 data rows; `git diff` vs change-local source = exactly the provenance note; line-ending check = LF (0 CRLF lines, no BOM); repo markdown hook clean (`✓ Markdown clean`). A markdownlint MD028 advisory (two adjacent blockquotes: the amendments history and the provenance note) is informational only — the repo hook tolerates it and the `ci`-style single-blockquote convention is preserved.
- Ordering requirement: not applicable (new domain, canonical file created fresh, no conflict with another active change).

## 4. Status engine / actionContext findings

- Native status: `artifactStore: openspec`, `isNonAuthoritative: false`, `actionContext.mode: repo-local`, `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]`, `warnings: []` — `openspec/specs/coverage/` is inside workspace/allowed roots. No stop condition fired.
- `dependencies.sync: blocked` reported at parent resolution predates the verify report; the verify report is now present and clean PASS — the sync phase's input requirement is satisfied, and the parent explicitly tasked this sync. `nextRecommended: sdd-verify` at resolution was resolved before verify completed; post-verify the next real phase is `sdd-archive` (see §6).
- Deferred parent actions (3, all parent-owned, none an implementation task): ask-on-risk gate (measured 2770 changed lines vs `origin/dev`, within the recorded user-authorized provisional single-PR size exception ≤ ~3000), post-apply bounded review, and delivery (PR vs `dev` from `test/raise-coverage-90`, assignee emiliodavola). These do not block sync.

## 5. Not done here (deliberately)

- Change folder NOT moved to archive (archive is a separate `sdd-archive` phase — pending sync completion + the parent-owned delivery gates).
- No commit made (`git status` shows the new `openspec/specs/coverage/` and the change dir as uncommitted alongside the implementation trees).
- No implementation files modified — this change's diff carries **zero `src/sofer/` paths** (COV-03) and this sync touched only `openspec/specs/coverage/spec.md` + this report.

## 6. Next recommended

- **`sdd-archive`** for this change once the parent completes the three deferred actions: the ask-on-risk decision record (already captured in verify-report: 2770 lines within the user-authorized provisional exception — chain strategy never selected, not invented here), the post-apply bounded review of the full PR diff, and delivery (work-unit commits + single PR vs `dev` from `test/raise-coverage-90`, PR template filled with the real verification output from the verify report). The canonical spec promotion is now satisfied by this sync. Pre-archive re-verify should confirm the canonical `coverage` spec is committed.

## 7. Risks

| Item | Severity | Note |
| --- | --- | --- |
| CI-arbiter measurement pending (ubuntu / Python 3.13) | Medium (for delivery, not sync) | Four COV-06 100.00 rows are binary gates with no margin; floors carry margin (+6/+9/+10 over 90, TOTAL +3). Archive readiness unaffected; CI result lives at the parent delivery gate |
| Uncommitted work units (branch `test/raise-coverage-90` trees untracked) | High (for archive, not sync) | Parent-owned; this sync does not commit |
| MD028 markdownlint advisory (adjacent blockquotes in Purpose) | Low | Informational; repo markdown hook passes clean; consistent with the amendments + provenance layout |
| Non-critical floor residuals (`mcp_registration.py` 99%, `profile.py` 96%) | Low | Documented verify-side reconciliations (provably-dead/defensive lines), within floor with margin |