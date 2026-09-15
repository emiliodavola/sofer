# Archive Report — 2026-09-15-chore-cov01-floors-status-quo

**Change**: `2026-09-15-chore-cov01-floors-status-quo`
**Issue**: GitHub **#215** — *chore: record the three second-tier per-file coverage floors as deliberately verify-phase-only*, option (b). The archive does **not** close the issue: delivery (commit + PR) is parent-owned and still pending.
**Branch**: `chore/215-cov01-floors-status-quo` (from `dev`)
**Date**: authored 2026-09-15; **archived 2026-09-15**
**Artifact store**: **hybrid** — this file inside the archived change root, plus the Engram record under topic key `sdd/2026-09-15-chore-cov01-floors-status-quo/archive-report`, **observation id `1293`**
**Status**: **archived by the `sdd-archive` phase** — pass, no blockers
**Verify verdict**: **PASS** — `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 1/1`, `evidence_revision sha256:cf066e208fac4f81896881c23dd6789f679a5785f9649565f1ac2663cf706894`
**Archived path**: `openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/`

## Summary

The three COV-01 second-tier per-file coverage floors (`profile.py`, `mcp_registration.py`, `verification.py`) are recorded as **deliberately not CI-gated**: they stay verify-phase evidence only, and arming a gate for them is defined as a spec change. The change adds no executable behaviour — it lands one `AGENTS.md` rule-14 adjacent-policy bullet and a 117-line ADDED-only domain delta promoted to canonical `COV-07` by `sdd-sync`. Archive moved the change root to the dated archive folder without editing any product path or canonical spec.

## Archive preconditions (all satisfied — actual output)

| Gate | Command / source | Actual output |
| --- | --- | --- |
| Verify report resolves and passes | `verify-report.md` envelope at head | `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 1/1`; no unresolved `FAIL` / `BLOCKED` / `CRITICAL` |
| Native `gentle-ai.sdd-status` v2 (consumed read-only, not recomputed) | `gentle-ai sdd-status 2026-09-15-chore-cov01-floors-status-quo` at archive launch | `next: archive`; `apply: all_done`; `verify: all_done`; `archive: ready`; `tasks: 33/33 complete`; `nextRecommended: "archive"`; `blockedReasons: []`; `remediationState.required: false` |
| `actionContext` | native status JSON | `mode: repo-local` (not `workspace-planning`); `workspaceRoot: C:\Users\elaze\Desktop\sofer`; `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`; move target and report path resolve inside the root |
| File-backed sync completed | `sync-report.md` (status **SYNCED**) | 1 ADDED, 0 MODIFIED, 0 REMOVED, 0 RENAMED; canonical promotion already on disk |
| Canonical carries COV-07 | `grep -c "COV-07" openspec/specs/coverage/spec.md` | `2` — requirement heading at `:283` and `## Test Mapping` row at `:375` |
| Final Task Completion Gate (re-read immediately before the move) | `grep -c '^\s*- \[ \]' …/tasks.md` | `0` (exit 1 = no matches); `grep -c '^\s*- \[x\]'` → `33`; `tasks.md` sha256 `80fcf96c4a5d4d7afa6b3c16e0dcedee4aea71bceed9bc05f199754e8abbef31` |
| Legacy flat spec | inventory | none — the change carries `specs/coverage/spec.md`, not a flat `spec.md` |
| Archive-name collision | `ls -d openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo` | `No such file or directory` — no collision |
| Active-change collisions | `ls -1 openspec/changes/` (pre-move) | exactly `2026-09-15-chore-cov01-floors-status-quo` and `archive`; no other active change |
| `rules.archive` (`openspec/config.yaml`) | config read | "Warn before merging destructive deltas" — **not triggered** (ADDED-only) |
| Path-reference safety of the move | `grep -n "openspec/changes"` over canonical spec, `AGENTS.md`, delta | exit `1` (no matches) in all three — the move creates **no stale path reference** |

**No unchecked implementation task boxes remain.** The Final Task Completion Gate found zero `- [ ]` lines, so **no archive-time sync fallback was run, no mechanical checkbox repair was performed, and no stale-checkbox reconciliation was needed**. No archive-time sync fallback approval was required because `sdd-sync` had already completed successfully.

## Artifacts read

- `proposal.md` (49,415 B), `explore.md` (33,410 B), `design.md` (30,095 B), `tasks.md` (17,317 B)
- `specs/coverage/spec.md` (117 lines; `## ADDED Requirements` only, 1 requirement, 1 scenario, 1 Test Mapping row)
- `apply-progress.md` (13,412 B), `verify-report.md` (23,731 B), `sync-report.md` (16,786 B)
- `openspec/config.yaml` (`strict_tdd: false`, `rules.archive`)
- Canonical `openspec/specs/coverage/spec.md` (read-only confirmation of COV-07 + mapping row)
- `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/` — the #216 precedent for the archive folder name and report layout

## Structured status and `actionContext` findings

Native `gentle-ai.sdd-status` v2 was consumed read-only before phase work and was **current** (`archive: ready`, `blockedReasons: []`), matching the parent prompt. The stale-snapshot problem recorded by `sdd-sync` did not recur here.

- `actionContext.mode: repo-local`, `workspaceRoot: C:\Users\elaze\Desktop\sofer`, `allowedEditRoots` = the single workspace root — no `allowedEditRoots` deficit, no `workspace-planning` archive restriction.
- The move target `openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/` and this report resolve inside the authoritative root.
- The native status reports `artifactStore: openspec` while the session preflight says **hybrid**: both halves ran — the filesystem move + this file (openspec half) and the Engram record (hybrid half). The `resolve-via-engram` carve-out does not apply because an `openspec/` planning home exists.
- **Post-move informational note (not a blocker):** re-running `gentle-ai sdd-status 2026-09-15-chore-cov01-floors-status-quo` after the move reports `next: sdd-new`, `apply/verify/archive: blocked`, `tasks: 0/0`, blocked reason `Active OpenSpec change not found`. This is the expected **terminal** state of a successfully archived change — the artifact root now lives under `archive/`, which the status engine does not scan as an active change. The authoritative archive-readiness snapshot is the pre-move one above.

## Domains synced

Exactly one domain: **`coverage`** → `openspec/specs/coverage/spec.md`, performed by `sdd-sync` (**not** by this phase). This phase edited **no** canonical spec and no product file — the only file it wrote is this report.

| Kind | Requirement names |
| --- | --- |
| ADDED | `Second-tier per-file floors are deliberately verify-phase-only (COV-07)` — with scenario `No gate is armed for the three second-tier floors` |
| MODIFIED | *(none)* |
| REMOVED | *(none)* |
| RENAMED | *(none)* |

**Non-destructive.** The delta carries `## ADDED Requirements` only. Canonical diff is `52 insertions(+), 1 deletion(-)` where the single deletion is the file's no-trailing-newline EOF marker (adjudicated and disclosed by `sdd-sync`); zero characters of COV-01..COV-06 requirement text changed. No destructive-merge approval was required or assumed.

## Active same-domain change warnings

**None.** `relationships.sameDomainActiveChanges: []` and `collisions: []` in native status; and after the move `ls -1 openspec/changes/` returns **`archive` only**, so no active change remains that could touch the `coverage` capability. No sync/archive ordering decision was needed.

## Archive move

```text
BEFORE: openspec/changes/2026-09-15-chore-cov01-floors-status-quo/
AFTER:  openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/
```

- **Method: plain `mv`** (not `git mv`, not committed). The folder is *mixed*: one **tracked** file (the delta `specs/coverage/spec.md`, committed by `ac8af03`) plus seven **untracked** phase artifacts. `git ls-files openspec/changes/2026-09-15-chore-cov01-floors-status-quo/` before the move returned exactly `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`, so a plain move was the correct tool and nothing was staged.
- **Folder name equals the change name**, which already embeds its date (`2026-09-15-chore-cov01-floors-status-quo`) — matching the `archive/2026-09-15-chore-ruff-format-hook-scope/` (#216) and `archive/2026-09-15-chore-ruff-single-authority/` precedents. **No double date prefix.** `sync-report.md`'s closing line suggested `2026-09-15-2026-09-15-chore-cov01-floors-status-quo/`; that is a **superseded** suggestion and was **not** followed, per the parent prompt and the #216 precedent.
- No archived change was deleted or modified; the whole move is one directory rename.
- Post-move `git status --porcelain`:

```text
 D openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md
 M openspec/specs/coverage/spec.md
?? openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/
```

The ` D` is the tracked delta leaving its old path and the `??` is the arrived archive tree — git reports the pair as a rename once staged; nothing is committed by this phase.

## Final inventory of the archived folder

Every file under `openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/`, one line each (8 phase artifacts + 1 domain delta + this report = 9 files):

| # | File | Bytes | Note |
| --- | --- | --- | --- |
| 1 | `explore.md` | 33,410 | phase artifact |
| 2 | `proposal.md` | 49,415 | phase artifact |
| 3 | `design.md` | 30,095 | phase artifact |
| 4 | `tasks.md` | 17,317 | 33/33 checked, sha256 `80fcf96c…` (unchanged by the move) |
| 5 | `apply-progress.md` | 13,412 | phase artifact |
| 6 | `verify-report.md` | 23,731 | PASS envelope |
| 7 | `sync-report.md` | 16,786 | SYNCED |
| 8 | `specs/coverage/spec.md` | 8,722 | the **tracked** domain delta (sha256 `230ca13b782b0f4db17eeadad7b148b7a665794c6f4e4af47ed5fdde2264a30c`), moved with the folder |
| 9 | `archive-report.md` | *(this file)* | written into the archived folder after the move |

## Canonical spec is untouched by the move

```text
sha256 (pre-move)  : 6886789569719dbbe1d5ef2a1cc5e70fc245b7d1d06402840671c13fea439a6c  openspec/specs/coverage/spec.md
sha256 (post-move) : 6886789569719dbbe1d5ef2a1cc5e70fc245b7d1d06402840671c13fea439a6c  openspec/specs/coverage/spec.md
grep -c "COV-07" (post-move): 2   # heading :283 + mapping row :375
git diff --stat -- openspec/specs/coverage/spec.md: 1 file changed, 52 insertions(+), 1 deletion(-)   # the sdd-sync edit, byte-identical hash
```

The archive move touched no canonical byte: the pre-move and post-move hashes are identical, and the only canonical diff in the tree is `sdd-sync`'s already-recorded COV-07 promotion (COV-01..COV-06 byte-for-byte intact). The archive phase performed **no** canonical write.

## Commit plan (parent-owned)

Nothing was committed; the move is unstaged. The **single follow-up commit** the parent must land contains:

1. the **archive move** — the rename of `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/` → `openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/` (tracked path `…/specs/coverage/spec.md` moves accordingly; git detects the rename on `git add -A`);
2. the **canonical promotion** — `openspec/specs/coverage/spec.md` (`52 insertions(+), 1 deletion(-)`), already on disk from `sdd-sync`;
3. the **untracked phase artifacts** — `explore.md`, `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `sync-report.md`, and `archive-report.md`, all now under the archive path.

The apply commit **`ac8af03`** already carried `AGENTS.md` (`+1`) and the delta at its **old** path (`+117`) — those two product files are **not** part of this follow-up commit; the follow-up supplies only the move, the canonical promotion, and the phase artifacts. The pointer (`AGENTS.md` rule 14) and the requirement it points at (`COV-07`) therefore remain together in history, and the canonical promotion must not be separated from the archive move.

## Engram traceability

- Topic key: `sdd/2026-09-15-chore-cov01-floors-status-quo/archive-report`
- Observation id: **`1293`**, type `archive`, project `sofer`, scope `project`, `capture_prompt: false`
- Recorded upstream this run: `sdd/2026-09-15-chore-cov01-floors-status-quo/verify-report` and `…/sync-report` (written by their owning phases).
- The Engram body is this report verbatim minus this one-line self-reference, which can only be added after the save returns the id. This file is the canonical record; the topic key is the stable cross-reference if the id ever changes on upsert.

## Risks

1. **Not committed.** The archive move, the canonical `openspec/specs/coverage/spec.md` promotion, and the whole archived change tree are uncommitted working-tree state; a hard reset would lose the canonical promotion and the audit trail. The follow-up commit above is mandatory.
2. **The recorded invariant is not airtight, and the requirement says so.** COV-07-S1 is a verify-phase static inspection by design (#215 option (b)): if a later change arms one of the three floors, **no test turns red**. The requirement itself mandates amending COV-07 + COV-06 + COV-03 + both ban-pinning guards in the same future change. Process compliance is the only enforcement.
3. **`## Purpose` in the canonical `coverage` spec is stale with respect to COV-07** (it already omitted COV-04). Deliberate non-goal of this change, matching the CI-07/CI-08 precedent.
4. **The D5 literal-wording nit remains uncorrected.** `design.md` D5 says "the only threshold literals in the whole delta are `100` and `fail_under = 90`"; that literal claim is falsified by `≥90` / bare `90` / `100%` tokens naming *other* requirements' boundaries. The substantive rule holds (no coverage value attached to the three floors) and `verify-report.md` adjudicated it as an accepted prose deviation with an optional cosmetic fix. Sync correctly did **not** edit the canonical block for it; if the parent wants the one-line wording correction, it is a separate, non-blocking edit to `design.md` — this archive report leaves it as recorded.
5. **Issue #215 stays open.** Delivery (commit + PR) is parent-owned; the archive does not close it.

## Next recommended

**Delivery (parent-owned): commit + PR.** Land the single follow-up commit described above (archive move + canonical promotion + the eight phase artifacts) on `chore/215-cov01-floors-status-quo`, then open the PR closing #215. No further SDD phase is required. This `hybrid` archive is complete: filesystem move done, canonical already promoted, Engram record saved as observation `1293`.
