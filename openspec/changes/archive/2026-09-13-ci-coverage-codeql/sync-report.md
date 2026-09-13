# Sync Report — CI coverage gate and CodeQL scanning (2026-09-13-ci-coverage-codeql)

**Status: SYNCED** (canonical spec promotion; change stays active — archive is a separate phase).

## 1. What was synced

| Item | Value |
| --- | --- |
| Change | `2026-09-13-ci-coverage-codeql` (branch `feat/ci-coverage-codeql`) |
| Artifact store | openspec (native status `artifactStore: openspec`; `openspec/config.yaml` header notes hybrid openspec+engram — sync report persisted to both) |
| Delta kind | **New-domain spec** (no `openspec/specs/ci/` existed canonical) — full copy, not a deltas merge |
| Domain(s) synced | `ci` |
| Canonical file(s) updated | `openspec/specs/ci/spec.md` (created, 239 lines) |
| Change-local source | `openspec/changes/2026-09-13-ci-coverage-codeql/specs/ci/spec.md` (237 lines) |
| Provenance note added | `> Introduced by change \`2026-09-13-ci-coverage-codeql\` (2026-09-13).` under `## Purpose`, matching the repo's blockquote convention (`packaging`/`mcp-server` use `> Added by change ...`; the change is not archived yet, so no `(archived …)` suffix) |

Canonical content is the change-local spec **verbatim** (Purpose + Requirements CI-01..CI-06 + 17 scenarios + the Test Mapping table included per the spec agent's sizing decision), plus the single provenance line. Only diff vs the change-local spec: the provenance blockquote (2 lines). Line endings normalized to LF per `.gitattributes` (`* text=auto eol=lf`), matching all existing `openspec/specs/*/spec.md`.

## 2. Requirements and scenarios

- CI-01 Coverage gate in config — 3 scenarios
- CI-02 Self-hosted coverage evidence — 3 scenarios
- CI-03 Release gated on the coverage job — 2 scenarios
- CI-04 CodeQL scan cadence and SARIF upload — 3 scenarios
- CI-05 CodeQL Advanced Setup config with paths-ignore — 2 scenarios
- CI-06 Declared coverage config and documentation truth — 4 scenarios

17 scenarios total; Test Mapping table lists all 17 (15 pytest-assertable via `tests/test_ci_workflows.py`, 2 verify-phase static evidence: CI-03 S2 needs-chain proof, CI-06 S3 README/README_ES mirror).

## 3. Guards and checks

- Verify report read: **PASS** for implementation; 17/17 scenarios resolved; no unresolved FAIL/BLOCKED/CRITICAL. The "ARCHIVE NOT READY" verdict is parent-owned commit markers (G.1–G.3) plus the expected 90-floor red gate — the red gate may not block verify per the report's own verdict. **G.3 is precisely this sync's deliverable.**
- No `## RENAMED Requirements` in the delta (new domain; nothing to rename).
- Legacy flat spec check: none — change ships `specs/ci/spec.md` (domain dir present). `openspec/specs/ci/` did not exist before this sync.
- Same-domain collisions: **none**. Active changes and their domains: `2026-09-12-fix-mcp-opencode-env` → cli, mcp-registration; `2026-09-12-fix-residual-parity` → codebook, mcp-server; `2026-09-12-fix-scan-parity-mcp` → mcp-server; `2026-09-13-ci-coverage-codeql` → ci; `2026-09-13-fix-prompt-intro-repr` → mcp-server; `2026-09-13-test-mcp-injection-semantics` → mcp-server. Only this change touches `ci`.
- Destructive sync: none (ADDED-only new domain; no REMOVED, no large MODIFIED blocks; no approval needed).
- `rules.sync` in `openspec/config.yaml`: not present (config defines proposal/specs/design/tasks/apply/verify/archive only) — no additional sync rules to apply.
- Validation performed: structural check — 1 spec heading, 6 `### Requirement:` blocks (CI-01..CI-06), 17 `#### Scenario:` blocks, 1 `## Test Mapping` table with 17 data rows; `git diff` vs change-local source = exactly the provenance note; line-ending check = LF. Markdown lint hook: clean.
- Ordering requirement: not applicable (new domain, canonical file created fresh, no conflict with another change).

## 4. Status engine / actionContext findings

- Native status: `artifactStore: openspec`, `isNonAuthoritative: false`, `actionContext.mode: repo-local`, `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` — `openspec/specs/ci/` is inside workspace/allowed roots. `nextRecommended` reported "Change selection is ambiguous" for the *parent* orchestrator; this executor was given an explicit, unambiguous change (`2026-09-13-ci-coverage-codeql`) and proceeded.
- `apply` was marked blocked at parent status resolution (attributed to the parent's selection ambiguity, not to an artifact failure in this change); verify-report is present and PASS, which is the sync phase's input requirement. No sync-phase blocker found.

## 5. Not done here (deliberately)

- Change folder NOT moved to archive (archive is a separate `sdd-archive` phase — verify report marks archive not ready pending parent commits G.1–G.3 and work-unit commits).
- No commit made (`git status` shows the new `openspec/specs/ci/` as untracked/`??` alongside the change dir).
- No implementation files modified.

## 6. Next recommended

- **`sdd-archive`** for this change once the parent completes: work-unit commits (L29, A.4, B.3, D.5, C.6, V.6), G.1 review, and G.2 delivery gate — the canonical spec promotion (G.3) is now satisfied by this sync. Pre-archive re-verify should confirm the canonical `ci` spec is committed.
- Coverage-raising follow-up change (88% → 90% floor) is a separate future change, not this one's scope.

## 7. Risks

| Item | Severity | Note |
| --- | --- | --- |
| Parent status "blocked / ambiguous selection" vs explicit change input | Low | Executor followed the explicit tasking; sync proceeded on the verify-report PASS |
| Uncommitted work units (branch `feat/ci-coverage-codeql` trees untracked) | High (for archive, not sync) | Parent-owned; this sync does not commit |
| Red coverage gate at 90 (88% today) | Expected by design | Follow-up change owns raising coverage |
| `openspec/config.yaml` is gitignored → CI-06 S1 test skips in CI | Low | Pre-existing, accepted at verify; skip-if-absent guard |