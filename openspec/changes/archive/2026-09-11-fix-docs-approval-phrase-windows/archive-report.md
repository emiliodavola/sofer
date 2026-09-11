# Archive Report — fix-docs-approval-phrase-windows

**Change**: `2026-09-11-fix-docs-approval-phrase-windows`
**Issue**: GitHub #151 — PR #157 (`docs(readme): document Windows approval-phrase generation (closes #151)`), **OPEN**, base `dev`
**Date**: 2026-09-11
**Artifact store**: openspec (repo-local; no Engram observation IDs for this change — the openspec store is authoritative)
**Status**: **archived** (archive mechanics complete; delivery not yet merged — see *Delivery*)
**Verify verdict**: PASS — `gentle-ai.verify-result/v1`, `verdict: pass`, `blockers: 0`, `critical_findings: 0`; issue #151 acceptance criteria **3/3**
**Branch**: `docs/fix-151-approval-phrase-windows` (base `dev`) @ `b5805f5`
**Archived path**: `openspec/changes/archive/2026-09-11-fix-docs-approval-phrase-windows/`

## Summary

Docs-only **additive** correction of a documentation gap: the hardening section documented only the
bash generation path (`export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"`), so Windows hosts
had no documented way to produce or persist the phrase — while `sofer_publish_confirm` is fail-closed
and refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED` when no phrase is configured.

One contiguous insertion per README adds: a `powershell` fence generating the phrase via the .NET
crypto RNG instance API (portable across Windows PowerShell 5.1 and PowerShell 7+), a cmd/`setx` note
with its four Microsoft-documented persistence caveats (`HKCU\Environment`, newly-created processes
only, current shell untouched/unencrypted, 1024-character cap), container prose on `$env:`/`set`
session scope vs. the launcher environment and the full-host-restart requirement, and a
`sofer_auth_status` → `approval_configured` pointer. The pre-existing #148 baseline sentences
(fail-closed wording, read-once sentence, `**Windows:**` launcher sentence, `**Verify:**` paragraph)
are untouched. Diff: **2 files, 46 insertions, 0 deletions (46 changed lines, 11.5 % of the 400-line
review budget)**; zero changes under `src/`, `tests/`, `docs/`, `openspec/specs/`, `TRACE.md`,
`scratch/`, `.gitignore`.

Delivered on a dedicated branch as a single commit (`b5805f5`: both READMEs + the six SDD artifacts).
**No commits were made to `main` or `dev`.** PR #157 is open against `dev`, unmerged — archive records
this as the final state and makes **no merge claim**.

> **Final-state supersession.** `verify-report.md` was produced while the tree was still uncommitted
> and therefore recorded criterion 3's same-commit half as *UNPROVABLE* and the commit as absent. The
> parent's final-state handoff outranks that intermediate snapshot: commit `b5805f5` now exists and
> contains **both** READMEs, so the AGENTS.md §13 / design C2 same-commit invariant is **provable**.
> This archive re-verified the final state directly (`git show --stat HEAD`, `git status --short` →
> empty, `git merge-base --is-ancestor dev HEAD` → exit 0) rather than carrying the stale note over.

## Spec Sync

**None — no delta authored** (see `specs/no-delta.md` §2/§3/§7).

| Field | Value |
|---|---|
| Domains synced | **none** — `openspec/changes/…/specs/` contains `no-delta.md` only; no `<domain>/spec.md` delta exists |
| ADDED requirements | none |
| MODIFIED requirements | none |
| REMOVED requirements | none |
| RENAMED requirements | none |
| Canonical writes | **none** — `openspec/specs/**` untouched (`git status --porcelain openspec/specs/` → empty, re-confirmed at archive time) |
| Destructive merge | not applicable — no `REMOVED`, no large `MODIFIED`; no approval was required or given |
| Active same-domain changes | **none** — `ls openspec/changes/` → `archive/` only (no collision warning to raise) |

`git grep -n '^## \(ADDED\|MODIFIED\|REMOVED\|RENAMED\)'` over the whole change root → **exit 1** (zero
matches), and the `specs/` directory holds no `<domain>/spec.md`. The behavior the new prose describes
was already normative before this change; the archive re-verified the four verbatim anchors remain in
place at their cited lines, so there is nothing to promote:

| Canonical anchor | Location | Verified at archive time |
|---|---|---|
| MSP-R05 fail-closed ladder | `openspec/specs/mcp-server/spec.md:137` | `…SHALL refuse with \`PUBLISH_APPROVAL_NOT_CONFIGURED\` and never reach the upload; the acknowledgment booleans alone are never sufficient.` — **present, 1×** at :137 |
| Envelope error codes | `openspec/specs/mcp-server/spec.md:390` | `…PUBLISH_APPROVAL_NOT_CONFIGURED\|TARGET_INVALID…` — **present** at :390 (a looser single-token alternation also matches the MSP-R05 body at :137, which carries both tokens — expected, not a drift) |
| `sofer_auth_status` contract | `openspec/specs/mcp-server/spec.md:424` | `` `requires_approval_phrase` is always `true` `` — **present, 1×** at :424 |
| Per-agent env persistence | `openspec/specs/mcp-registration/spec.md:19` | `secret values (\`HF_TOKEN\`, \`SOFER_MCP_APPROVAL_PHRASE\`) are never written to disk.` — **present** at :19 (the same phrase also occurs in the MCP-REG-01 preamble at :5 — expected) |

Supporting check: `grep -rn 'Hardening\|setx\|PowerShell\|openssl' openspec/specs/` → **exit 1** (zero
hits), re-confirming `no-delta.md` §2a — the Windows generation recipe is deployment documentation
that no canonical spec covers, and none should be fabricated for it.

`openspec/config.yaml` defines **no `rules.sync` key** (only `proposal`/`specs`/`design`/`tasks`/
`apply`/`verify`/`archive`), so no sync-phase rule constrains this outcome.

**No `sync-report.md` was written, deliberately.** This repository records spec-sync outcomes in the
`## Spec Sync` section of `archive-report.md` (25 archived changes do so; 8 use `## Spec Sync
Summary`), and **no `sync-report.md` exists anywhere under `openspec/`** (re-verified this pass:
`find openspec -name sync-report.md` → 0) — creating one would invent a convention. Archive-time sync
fallback was therefore **not executed and not needed**: there was no delta to merge, and the sync
phase had already recorded its verified no-op at `specs/no-delta.md` §7.

## Verification Evidence

| Gate | Result |
|------|--------|
| Verify verdict | `pass` — `blockers: 0`, `critical_findings: 0` (machine-readable envelope at the head of `verify-report.md`; `requirements: 0/0`, `scenarios: 0/0` by design) |
| Acceptance criteria (#151) | **3 / 3 PASS** — criterion 3's same-commit half now provable via `b5805f5` (both READMEs in one commit, verified `git show --stat HEAD` → `README.md 23 +` / `README_ES.md 23 +`) |
| Pytest | `uv run pytest tests/ -q` → **1468 passed, 6 skipped**, 13 warnings (exit 0) — numerically equal to the task 0.5 baseline, so the docs-only diff changed no behavior |
| Fail-closed pins | `tests/test_mcp_server.py` (fail-closed refusal ladder) + `tests/test_mcp_process.py::TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch` → passed **unmodified** (the executable proof the documented behavior is real) |
| Lint / type / whitespace | `uv run ruff check src/ tests/` → All checks passed! · `uv run mypy src/` → Success: no issues found in 32 source files · `git diff --check` → clean |
| Hard-zero greps | `RNGCryptoServiceProvider`, `ToHexString`, `weaker posture`, `postura más débil` → **empty (exit 1)** in both files |
| Presence greps | `RandomNumberGenerator` (695 / 730), `setx` (4 / 3), `$env:SOFER_MCP_APPROVAL_PHRASE` (696 / 731), `approval_configured` (708,714 / 743,749), exact portable form `RandomNumberGenerator.*Create().GetBytes` (695 / 730) |
| Anti-regression (#148) | EN/ES `acknowledge_*`-alone, "once at process start" / "una sola vez al iniciar el proceso", launcher-environment sentence, and the exact anchor `sofer_auth_status(config).*approval_configured` → **exactly 1 each**; zero deletions in the diff |
| EN↔ES fence byte-identity | `sed -n '690,697p' README.md` and `sed -n '725,732p' README_ES.md` → sha256 `6ce78f8cca4f978d9981d3af0caadadb24481007a5699898c11fcf76280a8959` **both** (re-measured at archive time) |
| Claim traceability (W1–W7 / N1–N7) | W1–W7 all verified against `src/sofer/mcp_server.py:217,1155,1663,2640-2648`, the live specs, and Microsoft `setx` documentation; **N1–N7 all absent** |
| Mirror guard (AGENTS.md §13) | Heading parity preserved: `^## ` = 17 / 17, `^### ` = 17 / 17, equal EN↔ES, no heading added/removed/renamed |
| **§7.5 PowerShell execution gate** | **PASS on both runtimes, executed (not merely documented):** Windows PowerShell **5.1.26100.9444** → `e1e6f94839ef89064189e433d5abce7c` (len 32, `^[0-9a-f]{32}$`); pwsh **7.6.6** → `2d385835232ddc9e965c281517f17ec2` (len 32, `^[0-9a-f]{32}$`). Apply phase had run the same gate green with two other throwaway samples (`cc1309de…` / `b478186b…`). Samples are ephemeral: `HKCU\Environment` contains no `SOFER_MCP_APPROVAL_PHRASE` value and the shell does not set it |
| Strict TDD | inactive by configuration (`openspec/config.yaml` → `strict_tdd: false`); prose-only change, no RED/GREEN cycle exists, no test file created or modified |

## Delivery

| Field | Value |
|---|---|
| Branch | `docs/fix-151-approval-phrase-windows` (base `dev`) — never `main`/`dev` directly |
| Commits | **`b5805f5`** (single commit beyond `dev`; `git rev-list --count dev..HEAD` → `1`) |
| Commit contents | 8 files, 1794 insertions, 0 deletions — `README.md` (+23), `README_ES.md` (+23), and the six SDD artifacts (`proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `specs/no-delta.md`) |
| PR | **#157 — OPEN, unmerged**, base `dev`, `mergeable: MERGEABLE`, `headRefOid: b5805f5` — human approval pending |
| Merge target | `dev` only; `main` receives changes solely via release-time merges from `dev` |
| Release / tag step | **none** for this change (docs-only, no runtime surface) |
| Review workload | 46 changed lines = 11.5 % of the 400-line budget → single PR, no chaining, no `size:exception` |

**Tasks 5.1–5.3 and 6.1–6.2 (`sdd-owner: parent`) remain open in the persisted artifact** — the parent
lifecycle rows (commit ✔ → PR ✔ → region-by-region confirmation → bounded review → human gate). They
are **not** implementation tasks and their completion is outside the archive's authority; the archive
records the correct final state rather than asserting a merge that did not happen. Consequently the
verified working-tree blobs are the blobs shipped in `b5805f5` (`README.md` blob `001355f9`,
`README_ES.md` blob `4860202d`; working tree `git status --short` → empty).

## Task Completion Gate

Re-read the persisted tasks artifact immediately before the archive move (now at
`openspec/changes/archive/2026-09-11-fix-docs-approval-phrase-windows/tasks.md`):

- **`- [ ]` implementation task markers remaining: ZERO.** All 29 implementation-owned rows
  (Phases 0–4) are `[x]`.
- The **5** remaining `- [ ]` rows are **all parent-owned** (`<!-- sdd-owner: parent -->`), reproduced
  verbatim:

```text
- [ ] 5.1 Stage `README.md` + `README_ES.md` **together in a single commit** (AGENTS.md §13, design C2); commit message names GitHub issue #151 and the docs-only scope. Pre-commit ruff + mypy run automatically — do not use `--no-verify`. Verify afterwards that exactly one commit exists on the branch beyond `dev` and that it contains both files (`git show --stat HEAD`). <!-- sdd-owner: parent -->
- [ ] 5.2 Push the dedicated branch and open the PR into `dev` with `gh pr create --base dev` (never `main`/`dev` directly; no tag, no release). Fill every section of `.github/PULL_REQUEST_TEMPLATE.md` (AGENTS.md §11) with **actual command output** from Phases 3–4 — hard-zero greps, presence greps, single-occurrence greps, `git status --short`, `git diff --stat`, pytest tail, ruff/mypy, `git diff --check`, and the verbatim §7.5 execution-gate output (task 4.7) — plus the mandatory *SDD artifacts* section listing `proposal.md`, `specs/no-delta.md`, `design.md`, `tasks.md`. <!-- sdd-owner: parent -->
- [ ] 5.3 Confirm the PR diff region-by-region: both READMEs changed in the same hardening region, EN block and ES block mirrored, fence byte-identical EN↔ES; no `src/`/`tests/`/`docs/`/`openspec/specs/`/`TRACE.md`/scope-guard file present. Do not merge without human approval at the delivery gate. <!-- sdd-owner: parent -->
- [ ] 6.1 Run the bounded post-apply review over the PR diff using design §4.1/§4.2 as the checklist: every W1–W7 claim present in both languages, zero N1–N7 claims, fence byte-identical and portable-form-correct, ES mirror complete and same-commit, zero deletions, no change to any #148 baseline sentence. <!-- sdd-owner: parent -->
- [ ] 6.2 Confirm the lifecycle gate: human approval of the PR before merge, `dev`-only target, no tag/release step, and the §7.5 gate evidence recorded in the PR (proposal *Delivery*, design §9). <!-- sdd-owner: parent -->
```

- **No stale-checkbox reconciliation was performed and none was needed.** Rows 5.1 and 5.2 are marked
  parent-owned and their objective conditions are observable in the final state (commit `b5805f5` with
  both READMEs; PR #157 open against `dev`), but the parent prompt did **not** instruct archive-time
  checkbox repair and rows 5.3/6.1/6.2 are genuinely still pending human action — so mechanically
  flipping any box would have misrecorded state. Archive made **zero** edits to `tasks.md`.
- Final `tasks.md` count: 29 `[x]` / 5 `[ ]` (all parent-owned lifecycle rows) of 34.

## Deviations and Adjudications

1. **Design line arithmetic is off by 3 per file (forecast +20/+20 → actual +23/+23).** The design's
   byte-verbatim §6.1/§6.2 block contains **10** prose lines, not the "8 prose" its estimate states, and
   the trailing separator blank becomes an added line: 2 intro + 1 blank + 8 fence + 1 blank + 10 prose
   + 1 trailing blank = **23**. `git diff --numstat` confirms `23 0` per file (46 total, not 40). The
   inserted text is byte-verbatim the design block — **not** trimmed to hit the estimate. 11.5 % of the
   400-line budget → no delivery-strategy question arose.
2. **`grep -c '^#'` rises +3 per file (84 → 87).** The three mandated PowerShell comment lines begin
   with `#`, so the counter includes code-fence comments; design §7.3's "unchanged" guard literally
   conflicts with the mandated (D5/W7) comment lines. The guard's **intent** holds: `^## ` = 17/17,
   `^### ` = 17/17, EN↔ES equal, no TOC/anchor churn. `grep -c '^# '` likewise rises 49 → 52 (+3),
   EN = ES.
3. **Bare `grep -c 'approval_configured'` is 2 per file (was 1).** The mandated W6/D6
   `sofer_auth_status` → `approval_configured` pointer necessarily adds one occurrence
   (`README.md:708,714`; `README_ES.md:743,749`). The design's §7.3 *exact* anchor
   (`sofer_auth_status(config).*approval_configured`) is still **exactly 1** in both files, so the #148
   Verify paragraph remains singular and byte-identical. The over-broad counter lives in `tasks.md` 0.4;
   the design-accurate check passes.
4. **Sync outcome recorded at `specs/no-delta.md` §7, not §6.** `no-delta.md` already carried a
   change-specific §6 (spec-phase engine reconciliation) that the merged #148 sibling lacked, so the
   sync outcome landed one section later. The mandated heading **text** is preserved verbatim; only the
   section ordinal differs. This is why the archive cites §2/§3/**§7**.
5. **Engine no-delta false positive (adjudicated, non-blocking).** The native status reports
   `artifacts.specs: "missing"`, `blockedReasons: ["domain specs are missing or partial."]`,
   `applyState: blocked`, and `sync`/`archive: blocked`. This is the **documented false positive** of the
   spec-delta heuristic for a deliberately no-delta change, recorded independently in four places:
   `specs/no-delta.md` §3 (approved "No delta" verdict), §6 (spec-phase reconciliation) and §7
   (sync-phase reconciliation); `apply-progress.md` (discrepancy section); and `verify-report.md`
   (stale-engine reconciliation, with `applyState: blocked` explicitly named). All required inputs
   (proposal, spec verdict, design, tasks, apply-progress, verify-report) exist and were read directly.
   The maintainer adjudicated archive to proceed, and the sibling `#148` change was archived identically.
   **This is not a CRITICAL verification issue and does not block archive.**
6. **Two added prose lines are 82 columns (one over the ≤80 guidance).** Confirmed: `README.md` has 2
   (`$env:` line + `Confirm with …` line); `README_ES.md` has 1 (its Spanish counterpart is shorter).
   The pre-existing #148 prose in the same region already reaches 82 (EN) / 81 (ES) columns, so the new
   lines match their neighbours; nothing was re-wrapped, preserving the byte-verbatim block.
7. **Fence offsets one line later than the evidence record states.** `apply-progress.md` cites the fence
   at `README.md:689-696`; the actual span is `690-697` (`README_ES.md:725-732`). The byte-identity claim
   reproduces at the corrected offsets (sha256 `6ce78f8c…` both languages) — a harmless evidence-record
   offset, already flagged by verify as non-blocking.
8. **No partial-archive exception was invoked.** Proposal ✅, design ✅, tasks ✅, apply-progress ✅,
   verify-report ✅, spec verdict ✅ — all required artifacts are present and complete, so no intentional
   partial-archive approval was needed. No destructive canonical merge occurred, so no destructive-merge
   approval was needed either.

## Status and actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` (repo-local) | matches `planningHome`; archive ran file-backed per the openspec rules |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies |
| `allowedEditRoots` | `[C:\Users\elaze\Desktop\sofer]` | archive target `openspec/changes/archive/…` and the report are **inside** the root — no out-of-root write |
| `nextRecommended` | `sdd-verify` (engine) | superseded by the completed verify (`verdict: pass`); archive proceeded under maintainer adjudication |
| `isNonAuthoritative` | `false` | structured status consumed as authoritative; the sole `blockedReasons` entry is the adjudicated no-delta false positive (see *Deviations* 5) |
| `taskProgress` | `29/29` complete, `unchecked: []` | **zero unchecked implementation rows** |
| `deferredParentActions` | `0/5` complete, 5 remaining | exactly the five `sdd-owner: parent` lifecycle rows — reported separately from implementation work, and not an archive blocker by construction |
| `dependencies` | `apply`/`verify`/`sync`/`archive` = `blocked`/`ready`/`blocked`/`blocked` | the no-delta false positive plus the parent-owned rows; verify itself is `ready` with verdict `pass` |
| `collisions` / `sameDomainActiveChanges` | empty | no same-domain collision warning to raise |
| `rules.archive` (`openspec/config.yaml`) | `Warn before merging destructive deltas.` | honored — no destructive delta existed |
| Engram observation IDs | n/a — `openspec` store | no `sdd/{change}/archive-report` memory write is required in this mode; none performed or claimed |

## Archive Mechanics

- Move: `git mv openspec/changes/2026-09-11-fix-docs-approval-phrase-windows
  openspec/changes/archive/2026-09-11-fix-docs-approval-phrase-windows` — **6 pure renames**
  (`R`, 100 % similarity: `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`,
  `verify-report.md`, `specs/no-delta.md`), i.e. **full history preserved** and no worktree edit.
- Files archived: `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`,
  `specs/no-delta.md`.
- `archive-report.md` is additive and lives inside the archived change; `openspec/changes/` now
  contains only `archive/`.
- Audit trail intact: active artifacts were moved, never deleted or rewritten. Nothing under
  `openspec/specs/`, `TRACE.md`, `scratch/`, `.gitignore`, `src/`, `tests/`, `README.md`, or
  `README_ES.md` was touched by this phase — the only pending worktree changes after the move are the
  six renames plus this new untracked report.
- **No commit was made** — the parent versions the move and this report.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** `git revert b5805f5` restores both READMEs. No spec or code
  changed, so nothing else rolls back; the archived change folder stays as the audit trail.
- **Rollback of the archive move:** `git mv` the folder back to `openspec/changes/` (history-safe) and
  drop this report — the move is a pure rename, so reversal is lossless.
- **Next steps:** the parent commits the archive move + this report on
  `docs/fix-151-approval-phrase-windows` (same PR branch, **no merge to `dev`/`main`** by this phase),
  pushes, and PR #157 is reviewed and merged into `dev` by a human (rows 5.3/6.1/6.2). No tag, no
  release step.
- **Recorded follow-ups (out of scope, not created here):** (a) make the "read once at process start /
  restart required" contract explicit in `mcp-server/spec.md` (code-pinned at
  `src/sofer/mcp_server.py:217,2640-2648`, not spec-pinned); (b) a docs-conformance requirement +
  README-grep test for the approval-setup prose — feasible via the existing TC-09 / PKG-05 /
  `TestBuildClarityReadme` pattern, but deliberately not created because it would expand a docs-only
  change into `tests/` (`specs/no-delta.md` §5). Issues #144 / #145 / #151 were deliberately not
  pre-empted.
