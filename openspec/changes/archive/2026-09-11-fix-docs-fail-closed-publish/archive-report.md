# Archive Report — fix-docs-fail-closed-publish

**Change**: `2026-09-11-fix-docs-fail-closed-publish`
**Issue**: GitHub #148 — PR #156 (`docs(readme): document mandatory fail-closed approval phrase (closes #148)`), **OPEN**, base `dev`
**Date**: 2026-09-11
**Artifact store**: openspec (repo-local; no Engram observation IDs for this change — the openspec store is authoritative)
**Status**: **archived** (archive mechanics complete; delivery not yet merged — see *Delivery*)
**Verify verdict**: PASS — `gentle-ai.verify-result/v1`, `verdict: pass`, `blockers: 0`, `critical_findings: 0`; issue #148 acceptance criteria **8/8**
**Branch**: `docs/fix-readme-fail-closed-publish` (base `dev`) @ `884c044`
**Archived path**: `openspec/changes/archive/2026-09-11-fix-docs-fail-closed-publish/`

## Summary

Docs-only correction of a security-model drift: `README.md` / `README_ES.md` described the HF publish approval phrase as optional ("when configured", "only the two acknowledgment booleans gate the HF publish — a weaker posture…") while `sofer_publish_confirm` is **fail-closed** — with no phrase configured it refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reaches the upload. Four regions were rewritten (EN + ES security-model bullet, EN + ES hardening body) to match the already-normative behavior: phrase mandatory, read once at process start, per-agent supply guidance, Windows launcher-env note, and `sofer_auth_status` → `approval_configured` verification. Diff: **2 files, 56 insertions, 14 deletions (70 changed lines, ≈18 % of the 400-line review budget)**; zero changes under `src/`, `tests/`, `docs/`, `TRACE.md`, `scratch/`, `.gitignore`, `openspec/specs/`.

Delivered on a dedicated branch as three commits (`1ad9837` README/ES + change artifacts, `400d5a5` tasks 4.x/5.1 + verdict normalization, `884c044` verify-report envelope alignment). **No commits were made to `main` or `dev`.** PR #156 is open against `dev`, unmerged — archive records this as the final state and makes **no merge claim**.

## Spec Sync

**None — no delta authored** (see `specs/no-delta.md` §2/§3/§6).

| Field | Value |
|---|---|
| Domains synced | **none** — `openspec/changes/…/specs/` contains `no-delta.md` only; no `<domain>/spec.md` delta exists |
| ADDED requirements | none |
| MODIFIED requirements | none |
| REMOVED requirements | none |
| RENAMED requirements | none |
| Canonical writes | **none** — `openspec/specs/**` untouched (`git status --porcelain openspec/specs/` → empty, re-confirmed at archive time) |
| Destructive merge | not applicable — no `REMOVED`, no large `MODIFIED`; no approval was required or given |
| Active same-domain changes | **none** — `ls openspec/changes/` → this change + `archive/` only (no collision warning to raise) |

The behavior the README must now describe was already normative before this change; the archive re-verified the four verbatim anchors remain in place, so there is nothing to promote (1 match each):

| Canonical anchor | Location | Verified text |
|---|---|---|
| MSP-R05 fail-closed ladder | `openspec/specs/mcp-server/spec.md:137` | `…SHALL refuse with \`PUBLISH_APPROVAL_NOT_CONFIGURED\` and never reach the upload; the acknowledgment booleans alone are never sufficient.` |
| Envelope error codes | `openspec/specs/mcp-server/spec.md:390` | `…PUBLISH_APPROVAL_NOT_CONFIGURED\|TARGET_INVALID…` |
| `sofer_auth_status` contract | `openspec/specs/mcp-server/spec.md:424` | `` `requires_approval_phrase` is always `true` `` |
| Per-agent env persistence | `openspec/specs/mcp-registration/spec.md:19` | `secret values (\`HF_TOKEN\`, \`SOFER_MCP_APPROVAL_PHRASE\`) are never written to disk.` |

`sdd-sync` re-verified this independently (not carried over from the proposal) — zero domain deltas, zero `## ADDED|MODIFIED|REMOVED|RENAMED` sections, canonical already normative, no collision, no destructive delta. **No `sync-report.md` was written, deliberately**: this repository records spec-sync outcomes in the `## Spec Sync` section of `archive-report.md` and no `sync-report.md` exists anywhere under `openspec/`; creating one would invent a convention. Archive-time sync fallback was therefore **not executed and not needed** — there was no delta to merge.

## Verification Evidence

| Gate | Result |
|------|--------|
| Verify verdict | `pass` — `blockers: 0`, `critical_findings: 0` (machine-readable envelope at the head of `verify-report.md`) |
| Acceptance criteria (#148) | **8 / 8 PASS** (criterion 5's "same commit" half is now satisfied by `1ad9837`) |
| Pytest | `uv run pytest tests/ -q` → **1468 passed, 6 skipped**, 13 warnings (exit 0) — numerically equal to the task 0.3 baseline |
| Fail-closed pins | `TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed` + `TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch` → 2 passed, **unmodified** (the executable proof the corrected prose is true) |
| Lint / type | `uv run ruff check src/ tests/` → All checks passed! · `uv run mypy src/` → Success: no issues found in 32 source files |
| Whitespace | `git diff --check` → clean |
| Hard-zero greps | 6 → 0 vs baseline for `weaker posture\|when configured\|acknowledgment booleans` (EN) and `configurada — una frase\|postura más débil\|booleanos de reconocimiento` (ES); empty also under a widened independent pattern |
| Claim traceability | W1–W10 all verified against `src/sofer/mcp_server.py`, `mcp_registration.py`, the live specs (and, for the single opencode `environment` token, the upstream opencode config schema); **N1–N7 all absent** |
| Mirror guard (AGENTS.md §13) | EN↔ES heading parity preserved: 17 `###` / 84 `#` lines each, same order, no heading line added/removed/renamed |
| Strict TDD | inactive by configuration (`openspec/config.yaml` → `strict_tdd: false`); prose-only change, no RED/GREEN cycle exists, no test file created or modified |

## Delivery

| Field | Value |
|---|---|
| Branch | `docs/fix-readme-fail-closed-publish` (base `dev`) — never `main`/`dev` directly |
| Commits | `1ad9837` → `400d5a5` → `884c044` (head) |
| PR | **#156 — OPEN, unmerged**, base `dev`, `mergeable: MERGEABLE` — human approval pending |
| Merge target | `dev` only; `main` receives changes solely via release-time merges from `dev` |
| Release / tag step | **none** for this change (docs-only, no runtime surface) |
| Review workload | 70 changed lines = 17.5 % of the 400-line budget → single PR, no chaining, no `size:exception` |

**Task 5.2 (`sdd-owner: parent`) remains open by design.** It is the human lifecycle gate — approval of PR #156 before merge. It is a parent-owned lifecycle row, **not** an implementation task, and its completion is outside the archive's authority; the archive records the correct final state rather than asserting a merge that did not happen. Consequently `verify evidence_revision` carries over unchanged to PR #156 (the verified working-tree blobs are the blobs shipped in `1ad9837`: `README.md` `e7cfba34`, `README_ES.md` `c9fbb51c`).

## Task Completion Gate

Re-read the persisted tasks artifact immediately before the archive move:

- **`- [ ]` implementation task markers remaining: ZERO.** All 28 implementation-owned rows (Phases 0–4) are `[x]`.
- The single `- [ ]` in `tasks.md` is line 88, parent-owned — reproduced verbatim:

```text
- [ ] 5.2 Confirm the lifecycle gate: human approval of the PR before merge, `dev`-only target, and no release/tag step for this docs-only change (proposal *Delivery*, design §9). <!-- sdd-owner: parent --> (awaiting human approval of PR #156)
```

- **No stale-checkbox reconciliation was performed and none was needed.** The three delivery rows that `verify-report.md` reported as unchecked blockers (`4.1`, `4.2`, `4.3`) were closed by their owner in commit `400d5a5` with the required evidence appended (commit `1ad9837`, PR #156, PR file list) — i.e. genuinely completed, not mechanically repaired at archive time. Archive made **zero** edits to `tasks.md`.
- Final `tasks.md` count: 29 `[x]` / 1 `[ ]` (parent lifecycle row) of 30.

## Deviations and Adjudications

1. **Engine no-delta false positive (adjudicated, non-blocking).** The native status reports `artifacts.specs: "missing"`, `blockedReasons: ["domain specs are missing or partial."]`, and `applyState: blocked`. This is the **documented false positive** of the spec-delta heuristic for a deliberately no-delta change, recorded in three independent places: `specs/no-delta.md` §3 (approved "No delta" verdict) and §6 (engine reconciliation), `apply-progress.md` (discrepancy section), and `verify-report.md` (stale-engine reconciliation, with `applyState: blocked` explicitly named). All three genuinely required apply inputs (tasks, design, spec verdict) exist; the maintainer adjudicated archive to proceed, and the parent prompt carried that adjudication. **This is not a CRITICAL verification issue and does not block archive.**
2. **`spawn`-style malformed task ownership markers (engine parse artifact, non-blocking).** The engine flags five `tasks.md` rows as `Malformed task ownership marker`. Cause: evidence annotations were appended **after** the `<!-- sdd-owner: … -->` comment (e.g. `… <!-- sdd-owner: implementation --> (commit \`1ad9837\` …)`). The markers are present and correct; only the trailing parenthetical defeats the parser. The task-completion gate was therefore applied by reading the artifact directly (checkbox state + ownership marker), which shows zero unchecked implementation rows. Not repaired at archive time — editing the tasks artifact to satisfy a parser is out of archive scope and would destroy commit-anchored evidence.
3. **Two >80-column lines (accepted, re-measured).** One per README, both unbreakable inline Markdown links: `README.md:682` = 95 chars, `README_ES.md:717` = 108 chars. Measured in **characters**, not bytes. Alternatives (reference-style link, shortened text, split link) were rejected as further deviations from the design's mandated link text. Pre-existing precedent: 107 EN / 134 ES lines were already > 80 before this change.
4. **Line-number shifts (+2/+17) and one ES re-wrap.** The design/tasks line references describe the pre-edit tree; heading parity and order are preserved, and the ES `### Modelo de seguridad` paragraph was re-wrapped with the token-resolution chain byte-identical.
5. **No partial-archive exception was invoked.** Proposal ✅, design ✅, tasks ✅, apply-progress ✅, verify-report ✅ — all required artifacts are present and complete, so no intentional partial-archive approval was needed. No destructive canonical merge occurred, so no destructive-merge approval was needed either.

## Status and actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` (repo-local) | matches `planningHome`; archive ran file-backed per the openspec rules |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies |
| `allowedEditRoots` | `[C:\Users\elaze\Desktop\sofer]` | archive target `openspec/changes/archive/…` and the report are **inside** the root — no out-of-root write |
| `nextRecommended` | `fix-task-ownership-marker` (engine) | superseded by maintainer adjudication; see *Deviations* 1–2 — no archive-time repair performed |
| `dependencies` | `apply/verify/sync/archive` = `blocked`/`ready`/`blocked`/`blocked` | same no-delta false positive + the parent-owned 5.2 row; verify itself is `ready` with verdict `pass` |
| `collisions` / `sameDomainActiveChanges` | empty | no same-domain collision warning to raise |
| `rules.archive` (`openspec/config.yaml`) | `Warn before merging destructive deltas.` | honored — no destructive delta existed |
| Engram observation IDs | n/a — `openspec` store | no `sdd/{change}/archive-report` memory write is required in this mode; none performed or claimed |

## Archive Mechanics

- Move: `git mv openspec/changes/2026-09-11-fix-docs-fail-closed-publish openspec/changes/archive/2026-09-11-fix-docs-fail-closed-publish` — 5 pure renames + `specs/no-delta.md` as a rename-with-modification (`RM`), i.e. **full history preserved** and the uncommitted §6 sync-outcome edit carried over as-is.
- Files archived: `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `specs/no-delta.md`.
- `archive-report.md` is additive and lives inside the archived change; `openspec/changes/` now contains only `archive/`.
- Audit trail intact: active artifacts were moved, never deleted or rewritten. Nothing under `openspec/specs/`, `TRACE.md`, `scratch/`, `.gitignore`, `src/`, `tests/`, `README.md`, or `README_ES.md` was touched by this phase.
- **No commit was made** — the parent versions the move and this report.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** `git revert 1ad9837` restores both READMEs. No spec or code changed, so nothing else rolls back; the archived change folder stays as the audit trail.
- **Rollback of the archive move:** `git mv` the folder back to `openspec/changes/` (history-safe) and drop this report — the move is a pure rename, so reversal is lossless.
- **Next steps:** parent commits the archive move + this report on `docs/fix-readme-fail-closed-publish`, pushes, and PR #156 is reviewed and merged into `dev` by a human (task 5.2). No tag, no release step.
- **Recorded follow-up (out of scope, not created here):** a docs-conformance requirement + README-grep test would prevent recurrence of this drift class (`specs/no-delta.md` §5). Issues #144 / #145 / #151 were deliberately not pre-empted.
