# Sync report: chore-ruff-format-hook-scope

**Status:** `synced`
**Change** `2026-09-15-chore-ruff-format-hook-scope` (GitHub #216) · branch `chore/216-ruff-format-hook-scope`
· store **hybrid** (this file + Engram mirror under topic key
`sdd/2026-09-15-chore-ruff-format-hook-scope/sync-report`) · synced at working-tree HEAD with the
apply-phase product diff present (` M .pre-commit-config.yaml`, ` M tests/test_ci_workflows.py`).

## Scope

| Field | Value |
| --- | --- |
| Domain | `process-boundary` |
| Delta (source) | `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md` |
| Canonical (target) | `openspec/specs/process-boundary/spec.md` |
| Delta kinds present | `## ADDED Requirements` only — **no** `## MODIFIED`, **no** `## REMOVED`, **no** `## RENAMED` |
| Canonical files updated | exactly 1 (`openspec/specs/process-boundary/spec.md`) |
| Other canonical specs | untouched (`openspec/specs/ci/spec.md` and all others: **0** diff paths) |
| Archive move | **not** performed (sync does not archive) |
| Commit | **not** performed |

## Requirement changes

| Kind | Requirement | Notes |
| --- | --- | --- |
| ADDED | `Repository-declared ruff-format hook file scope (PB-14)` | Copied **verbatim** from the delta's `## ADDED Requirements`: heading, the `> Added by change ...` line, the three normative paragraphs, and both scenarios (2/2) with every GIVEN/WHEN/THEN/AND bullet |
| MODIFIED | *(none)* | — |
| REMOVED | *(none)* | — |
| RENAMED | *(none)* | RENAMED is unsupported by the native helper and is not present here |

Placement per `design.md` §5 (the exact sync step):

- (a) the PB-14 block was inserted **immediately after PB-13's final scenario line** (old line 376, new
  lines 377–424), blank-line separated — the canonical file's own convention; `grep -c '^---$'` on the
  pre-edit file was `0`, so no `---` was introduced between requirement blocks.
- (b) the `## Test Mapping` section was **created at the end of the file**: `---` separator + heading +
  the delta's three-sentence intro prose (including the PB-01..PB-13 backfill non-goal) + the exact two
  `| PB-14 | ... |` rows (new lines 425–438). The `---` before a `## Test Mapping` section matches the
  repository convention already used by `openspec/specs/ci/spec.md` and `openspec/specs/coverage/spec.md`.

**Deliberately not promoted** (delta-only context, per design §5 "Sync edits nothing else"): the delta's
`## ADDED Requirements`/header blockquote prose, its `## Cross-referenced and deliberately untouched`
section, and its Non-goals paragraph. No `## Purpose` or other canonical text was rewritten.

## Guardrail / approval findings

- **Destructive sync:** no. The delta is ADDED-only (`git diff --numstat` → `62 0`), so there is no
  REMOVED requirement and no large MODIFIED block; no explicit approval is required and none was assumed.
- **Active same-domain collisions:** none. Native status reports
  `relationships.sameDomainActiveChanges: []` and `collisions: []`, and the only non-archived change
  directory under `openspec/changes/` is this one. No archive/sync ordering decision is needed.
- **Legacy flat spec:** none — the change carries domain specs (`specs/process-boundary/spec.md`), not a
  flat `openspec/changes/{change}/spec.md`.
- **MODIFIED/REMOVED existence check:** not applicable (no MODIFIED/REMOVED requirements).
- **RENAMED:** not applicable (absent from the delta).
- **`rules.sync` in `openspec/config.yaml`:** not declared; `rules.archive` warns on destructive deltas
  (not triggered). Nothing extra to apply.

## Verification report gate

`verify-report.md` present and **PASS**: `verdict: pass`, `blockers: 0`, `critical_findings: 0`,
`requirements: 1/1`, `scenarios: 2/2`, full suite green (`1785 passed, 6 skipped`), build command exit 0.
No unresolved `FAIL`, `BLOCKED`, `CRITICAL`, or verification blocker. Sync proceeded on that basis.

Non-blocking residue carried forward (does **not** block sync or archive): the verify report's
WARNING-1 records one inaccurate pasted command line in `apply-progress.md` §3.3 (an `EXTENSIONS`
key-membership check recorded as `True`; the correct the-intent check is against
`set().union(*EXTENSIONS.values())`). The artifact is an apply-phase file, so this phase did not edit it;
the correction is a one-line fix for the apply/archive owner.

## Structured status and actionContext findings

Native `gentle-ai.sdd-status 2026-09-15-chore-ruff-format-hook-scope` re-run read-only at sync launch
(consumed, not recomputed): `next: archive`; `dependencies`: `proposal/specs/design/tasks/apply/verify:
all_done`, `archive: ready`; `tasks: 8/8` (`allComplete: true`); `artifacts.verifyReport: done`;
`blockedReasons: []`; `remediationState.required: false`.

- The status injected into this phase's preflight was **stale** — it was computed before
  `verify-report.md` existed (`artifacts.verifyReport: missing`, `verify: ready`, `sync: blocked`,
  `nextRecommended: sdd-verify`). The read-only re-run resolved it to the authoritative current state
  above, which is consistent with the parent prompt (`verify all_done`, `archive ready`) and with the
  parent's explicit authorization to re-run the read-only status. No blocker survived: the only recorded
  dependency was "sync only after verification is clean", and verification is now clean.
- `actionContext.mode: repo-local`, `workspaceRoot` = `C:\Users\elaze\Desktop\sofer`,
  `allowedEditRoots` = `["C:\Users\elaze\Desktop\sofer"]`. Not `workspace-planning`, so no
  `allowedEditRoots` deficit exists. Both files this phase touched (`openspec/specs/process-boundary/spec.md`,
  `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/sync-report.md`) resolve inside that root, so
  the canonical-path guard is satisfied.
- `artifactStore: openspec` in the native status, `hybrid` in the session preflight: the filesystem sync
  ran, and the Engram mirror was saved (see *Artifacts*). Not the non-authoritative
  `resolve-via-engram` carve-out (an `openspec/` home exists), so the status was treated as authoritative.

## Validation checks performed (exact commands and observed results)

| # | Check | Command | Observed |
| --- | --- | --- | --- |
| S1 | Append-only, canonical | `git diff --stat -- openspec/specs/process-boundary/spec.md` | `1 file changed, 62 insertions(+)` — insertions only |
| S2 | Zero removed lines | `git diff --numstat -- openspec/specs/process-boundary/spec.md` | `62	0	openspec/specs/process-boundary/spec.md` → added 62, **removed 0** |
| S3 | Zero `-` content lines | `git diff -- openspec/specs/process-boundary/spec.md \| grep -c '^-[^-]'` | `0` |
| S4 | PB-01..PB-13 byte-for-byte | `head -n 376 openspec/specs/process-boundary/spec.md \| diff - /tmp/pb-before.md` (pre-edit copy) | identical, empty diff, exit 0 |
| S5 | Exactly one PB-14 heading | `grep -c '^### Requirement:.*(PB-14)'` | `1` |
| S6 | Exactly one Test Mapping heading | `grep -c '^## Test Mapping'` | `1` |
| S7 | Total requirement headings | `grep -c '^### Requirement:'` | `14` (13 pre-existing + PB-14) |
| S8 | PB-01..PB-13 headings still present | `grep -cE '^### Requirement:.*\(PB-(0[1-9]\|1[0-3])\)'` | `13` |
| S9 | Both PB-14 scenarios present | `sed -n '378,424p' … \| grep -c '^#### Scenario:'` | `2` |
| S10 | PB-14 block byte-identical to the delta | `diff <(sed -n '378,424p' canonical) <(sed -n '34,80p' delta)` | identical |
| S11 | Test Mapping byte-identical to the delta | `diff <(sed -n '428,438p' canonical) <(sed -n '84,94p' delta)` | identical |
| S12 | No other canonical spec / forbidden path touched | `git status --porcelain` | only ` M .pre-commit-config.yaml`, ` M tests/test_ci_workflows.py`, ` M openspec/specs/process-boundary/spec.md`, `?? openspec/changes/2026-09-15-chore-ruff-format-hook-scope/` — 0 paths under any other `openspec/specs/**` |

Suite/build commands were **not** re-run: this phase edits Markdown only (a canonical spec and the sync
report); it compiles no code and changes no test, so re-running `uv run pytest tests/ -q` would only
re-earn the verify report's already-green evidence. `AGENTS.md` rule 6 applies to spec scenarios against
tests, which this change already satisfies 1:1 (PB-14 S1 → `tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown`;
PB-14 S2 → verify-phase runtime evidence, as PB-14 itself mandates).

## Risks

1. **None blocking.** The sync is additive and byte-verified; the canonical spec gains PB-14 and the
   `## Test Mapping` section and loses nothing.
2. **Preflight staleness (resolved, worth noting for the harness).** The injected status marked `sync`
   blocked and `nextRecommended: sdd-verify` because it predated the verify report. The read-only re-run
   corrected it; the parent's instruction to re-run was load-bearing, not cosmetic.
3. **WARNING-1 residue** (see *Verification report gate*): the inaccurate R2 evidence line is still in
   `apply-progress.md` §3.3 and, if quoted forward into the archive report unchanged, would read as
   reproducible evidence. One-line correction needed by the apply/archive owner.
4. **Declaration-vs-behaviour gap** (accepted in the verify report, unchanged): the guard proves the
   declared `types_or`; a future pre-commit release could alter the override semantic while the guard
   stays green. Now stated normatively in canonical PB-14, so the canonical spec carries the caveat.
5. **Not committed.** The canonical edit and this report sit uncommitted in the working tree; a
   commit/push remains a human-controlled action outside this phase.

## Next recommended

`sdd-archive` — sync is complete and clean; PB-14 + `## Test Mapping` are in the canonical
`openspec/specs/process-boundary/spec.md`, `tasks.md` is 8/8 with zero unchecked tasks, verify is PASS
with 0 blockers, and no same-domain collision exists. Archive must move the change folder to
`openspec/changes/archive/YYYY-MM-DD-2026-09-15-chore-ruff-format-hook-scope` (the `sync-report.md`
travels with the change).
