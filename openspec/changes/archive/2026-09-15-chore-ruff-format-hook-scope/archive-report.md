# Archive Report — 2026-09-15-chore-ruff-format-hook-scope

**Change**: `2026-09-15-chore-ruff-format-hook-scope`
**Issue**: GitHub **#216** — *chore: the `ruff-format` pre-commit hook rewrites `README.md` and
`README_ES.md` (its `types_or` includes `markdown`)* — the issue this change was opened for and the one it
closes. The archive does **not** close it: delivery (commit + PR) is parent-owned and still pending, so #216
remains open until the delivery PR lands.
**Branch**: `chore/216-ruff-format-hook-scope` (from `dev`) — working tree, **no commits**
**Date**: authored 2026-09-15; **archived 2026-09-15**
**Artifact store**: **hybrid** — this file inside the archived change root, plus the Engram record under
topic key `sdd/2026-09-15-chore-ruff-format-hook-scope/archive-report`
**Status**: **archived by the `sdd-archive` phase** — pass, no blockers
**Verify verdict**: **PASS** — `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`,
`scenarios: 2/2`, `evidence_revision sha256:6203b4f2dd9f268292070d014c285c62ebfdffa95759bf3a18007974591a0e52`
**Archived path**: `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/`

## Summary

The `ruff-format` pre-commit hook was rewriting `README.md` / `README_ES.md`, because `ruff-pre-commit`
widened its cached manifest's `types_or` to include `markdown` between 0.15.21 and 0.16.6 while
`.pre-commit-config.yaml` declared no `types_or` of its own — so the upstream default *was* the repository's
scope (`2 files reformatted, 9 files left unchanged`, measured in #195). The fix declares the scope
repo-side (`types_or: [python, pyi, jupyter]`), records why on the edited entry, and pins it with one static
guard test that reads `.pre-commit-config.yaml` and asserts the defect class directly.

## Archive preconditions (all satisfied)

| Gate | Result |
| --- | --- |
| Native `gentle-ai.sdd-status` v2 (consumed read-only, not recomputed) | `next: archive`; `apply/verify: all_done`; `archive: ready`; `tasks 8/8` (`allComplete: true`); `artifacts.verifyReport: done`; `blockedReasons: []`; `remediationState.required: false` |
| Verify report resolves and passes | `verdict: pass`, 0 blockers, 0 critical, no unresolved `FAIL` / `BLOCKED` / `CRITICAL` |
| File-backed sync completed | `sync-report.md` status `synced`; canonical `openspec/specs/process-boundary/spec.md` carries PB-14 (line 378) and `## Test Mapping` (line 428), 14 requirement headings, `+62/0` |
| Final Task Completion Gate (re-read immediately before the move) | `grep -c '^\s*- \[ \]' tasks.md` → **0**; `grep -c '^\s*- \[x\]'` → **8**; `tasks.md` sha256 `e44a9708721c6dc67fd368299f5b97934c27ec1c47bdd83d41a51047a583a176` |
| Legacy flat spec | none — the change carries `specs/process-boundary/spec.md`, not a flat `spec.md` |
| Archive-name collision | none — `archive/2026-09-15-chore-ruff-format-hook-scope/` did not exist |
| `actionContext` | `mode: repo-local`, `workspaceRoot: C:\Users\elaze\Desktop\sofer`, `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`; not `workspace-planning`; every path written resolves inside the root |
| `rules.archive` (`openspec/config.yaml`) | "Warn before merging destructive deltas" — **not triggered** (ADDED-only) |

**No unchecked implementation task boxes remain.** The Final Task Completion Gate found zero `- [ ]` lines,
so no archive-time sync fallback was attempted, no mechanical checkbox repair was performed, and no
stale-checkbox reconciliation was needed. No archive-time sync fallback approval was required because
`sdd-sync` had already run successfully.

## Artifacts read

- `proposal.md` (44,797 B), `preproposal.md` (4,365 B), `explore.md` (29,259 B), `research.md` (2,414 B)
- `design.md` (16,740 B) — §1 PB-14 wording, §2 Test Mapping decision (T1), §3 guard test, §4 YAML edit,
  §5 delta + sync step, §6 verify plan V1–V10
- `specs/process-boundary/spec.md` (118 lines; `## ADDED Requirements` only)
- `tasks.md` (8/8), `apply-progress.md` (§3.3 R2/V6), `verify-report.md`, `sync-report.md`
- `openspec/config.yaml` (`strict_tdd: false`, `rules.archive`)
- Canonical `openspec/specs/process-boundary/spec.md` (read-only confirmation of PB-14 + `## Test Mapping`)

## Domains synced

Exactly one domain: **`process-boundary`** → `openspec/specs/process-boundary/spec.md`, performed by
`sdd-sync` (not by this phase). This phase edited **no** canonical spec and no product file — the only file
it wrote is this report.

| Kind | Requirement names |
| --- | --- |
| ADDED | `Repository-declared ruff-format hook file scope (PB-14)` |
| MODIFIED | *(none)* |
| REMOVED | *(none)* |
| RENAMED | *(none)* |

**Non-destructive.** ADDED-only delta (`+62 / -0` on the canonical file), zero removed content lines, so no
destructive-merge approval was required or assumed; PB-01..PB-13 are byte-for-byte intact (verified by
`sdd-sync` check S4). The `## Test Mapping` section was created at the end of the canonical file with two
`| PB-14 | ... |` rows, matching the convention already used by `openspec/specs/ci/spec.md` and
`openspec/specs/coverage/spec.md`.

## Active same-domain change warnings

**None.** Native status reports `relationships.sameDomainActiveChanges: []` and `collisions: []`; after the
move, `openspec/changes/` contains only `archive/`. No sync/archive ordering decision was needed.

## Recorded deviation and corrected evidence

1. **Design deviation (recorded, API does not exist).** `design.md` §6 V6 prescribes
   `identify.tags_from_filename`. The installed `identify` 2.6.19 exposes no such name (its `__init__.py`
   measures 0 bytes; pre-commit imports the submodules directly, so hook filtering still works correctly) —
   `hasattr(identify, "tags_from_filename")` → `False`, confirmed independently by both `sdd-apply` and
   `sdd-verify`. R2's *intent* was therefore discharged against the real API:
   `identify.extensions.EXTENSIONS` is a dict keyed by extension name → identify type-tag set, and each
   declared tag is a real identify tag via the union of values, not the dict keys.
   `sdd-verify` independently re-earned `all(t in set().union(*EXTENSIONS.values()) for t in
   ('python','pyi','jupyter'))` → `True` (`'py' → {'python','text'}`, `'pyi' → {'pyi','text'}`,
   `'ipynb' → {'jupyter','json','text'}`). The declared list is not silently inert, and no requirement,
   scenario, task, or product artifact depends on the nonexistent helper.
2. **Corrected R2 evidence line in `apply-progress.md` §3.3.** `sdd-verify` WARNING-1 flagged an inaccurate
   pasted line (an `EXTENSIONS` **key**-membership check recorded as `True`; the correct check is against
   `set().union(*EXTENSIONS.values())`). That line has since been **corrected in place**: §3.3 now records
   `ALL = set().union(*EXTENSIONS.values()); all(t in ALL for t in ('python','pyi','jupyter'))` → `True`
   against the dict's value union, with the submodule/`__init__.py` explanation. This archive report carries
   the corrected form; the inaccurate key-membership expression is not propagated here.

## Archive move

```text
openspec/changes/2026-09-15-chore-ruff-format-hook-scope/
  -> openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/
```

The change folder was **untracked** (verified with `git ls-files --error-unmatch` before the move), so a
plain `mv` was used; no `git mv` was applicable. The archive folder name equals the change name, which
already embeds its date — matching the existing `archive/2026-09-15-chore-ruff-single-authority/`
precedent. No archived change was deleted or modified.

Post-move listing of
`openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/`:

```text
apply-progress.md     design.md      explore.md    preproposal.md   proposal.md
research.md           specs/         sync-report.md  tasks.md       verify-report.md
specs/process-boundary/spec.md
```

All nine expected phase artifacts plus the domain delta and this report are present.

## Review workload / delivery boundary

Product-surface diff is `2 files changed, 34 insertions(+), 5 deletions(-)` = **39 changed product lines**
(`.pre-commit-config.yaml` `+6`, `tests/test_ci_workflows.py` `+33/-5`), inside the `~71` (60–80) forecast
and two orders of magnitude inside the 400-line canonical and 1500-line session budgets. No chaining was
selected (`Chain strategy: pending`), so the single-PR boundary holds, and **no `size:exception` was used,
needed, or inferred**. Prohibited-path scan: `pyproject.toml`, `.github/workflows/**`, `src/sofer/**`,
`README.md`, `README_ES.md`, `uv.lock` → 0 matches.

**Not delivered.** Nothing was committed, pushed, or opened as a PR by this phase (and none was by any prior
phase). Delivery is parent-owned and still pending.

## Structured status and `actionContext` findings

Native `gentle-ai.sdd-status 2026-09-15-chore-ruff-format-hook-scope` re-run read-only at archive launch
(consumed, not recomputed): `next: archive`, `archive: ready`, `tasks: 8/8 complete`,
`blockedReasons: []`, `remediationState.required: false`. This matches the parent prompt's state. The
preflights seen by earlier phases were stale (`verify`/`sync` readiness predated the verify report); both
were corrected by read-only re-runs, and the archive phase consumed a status that was already current.

- `actionContext.mode: repo-local` — not `workspace-planning`, so no `allowedEditRoots` deficit exists.
- The move target `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/` and the report path
  resolve inside `C:\Users\elaze\Desktop\sofer`, inside the single allowed edit root.
- The native status reports `artifactStore: openspec` while the session preflight says `hybrid`: the
  filesystem move ran (openspec half) and the Engram record was saved (hybrid half). The
  `resolve-via-engram` carve-out does not apply — an `openspec/` home exists.

## Risks

1. **Declaration-vs-behaviour gap (accepted, unchanged).** The guard proves the *declaration*; the R1
   `--files README.md` runtime run (`(no files to check)Skipped`) plus the empty
   `git diff --stat -- README.md README_ES.md` prove the *behaviour*. A future pre-commit release could
   change the override semantic while the guard stays green. Now stated normatively in canonical PB-14, so
   the caveat survives into the canonical spec.
2. **`pyi` / `jupyter` are declared but inert today** (no `.pyi` / `.ipynb` in the tree). Confirmed benign:
   both are valid identify tags, so the declaration is honest, and the 68-file hook scope equals the tracked
   Python set.
3. **Not committed.** The product diff, the canonical `openspec/specs/process-boundary/spec.md` edit, and the
   whole archived change tree remain uncommitted; they must ride into the delivery commit, otherwise the
   canonical promotion and this audit trail would be lost on a hard reset.
4. **Issue closure.** #216 is still open by design; the archive does not close it. The delivery PR must
   close it.

## Next recommended

**Delivery (parent-owned): commit + PR.** Commit the two product files
(`.pre-commit-config.yaml`, `tests/test_ci_workflows.py`), the canonical
`openspec/specs/process-boundary/spec.md` promotion, and the archived change tree, then open the single PR on
`chore/216-ruff-format-hook-scope` closing #216. No further SDD phase is required.
