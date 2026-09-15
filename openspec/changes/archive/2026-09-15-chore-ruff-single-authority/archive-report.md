# Archive Report — 2026-09-15-chore-ruff-single-authority

**Change**: `2026-09-15-chore-ruff-single-authority`
**Issue**: GitHub **#195** — *chore: two authoritative ruff versions in play (pre-commit v0.16.7 vs ambient
0.16.0)* — the issue this change was opened for and the one it closes. Measured this phase via
`gh issue view 195`: still `state: OPEN`, because **nothing was committed** and the closing PR has not been
opened. The archive does not close it; the delivery PR does.
**Date**: authored 2026-09-15; **archived 2026-09-15**
**Artifact store**: **hybrid** — this file inside the change root, plus the Engram record under topic key
`sdd/2026-09-15-chore-ruff-single-authority/archive`
**Status**: **archived by the `sdd-archive` phase** (native status consumed: `archive: ready`,
`verify: all_done`, `tasks 45/45 complete`, `blockedReasons: []` for the archive phase)
**Verify verdict**: **PASS** — `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`,
`scenarios: 9/9`, `evidence_revision sha256:4a01a3e8…`. Natively validated this phase (§ *Verify gate*)
**Branch**: `chore/195-ruff-single-authority` (from `dev@5a2ae38`) — working tree, **no commits**
**Archived path**: `openspec/changes/archive/2026-09-15-chore-ruff-single-authority/`

## Summary

Closes #195: two tools formatted and linted this repository while disagreeing about which ruff they were —
`.pre-commit-config.yaml:3` pinned `ruff-pre-commit` `rev: v0.16.7`, while the dev group floated
`ruff>=0.9.0` and `uv.lock` resolved `0.16.0`. The hook is a *different implementation* of the formatter
than the binary the gate invokes, and nothing made the disagreement visible. `process-boundary` PB-10
explicitly deferred the mismatch to issue #195; this change owns it.

What shipped, in one table:

| Surface | Final state | Measured this phase |
| --- | --- | --- |
| `pyproject.toml:47` dev pin | `"ruff==0.16.7"` (exact, no floor) | `grep -n '"ruff==' pyproject.toml` → `47:    "ruff==0.16.7",` |
| `pyproject.toml:62` `[tool.ruff]` | `required-version = "==0.16.7"` — a drifting binary now fails at config load | `grep -n "required-version" pyproject.toml` → `62:required-version = "==0.16.7"` |
| `.pre-commit-config.yaml:3` | **unchanged** (`rev: v0.16.7` was already the D1 authority) | `sed -n '1,5p'` → `rev: v0.16.7`; `git diff --numstat .pre-commit-config.yaml` → **empty** |
| `tests/test_ci_workflows.py` | three static guards + one extraction helper, appended after line 426; **no version literal in the module** | `grep -c "0\.16" tests/test_ci_workflows.py` → **0**; guards at `:463`, `:475`, `:488` |
| `CONTRIBUTING.md:77` | `This project uses **ruff** 0.16.7 for linting and formatting.` (version only added; the `ruff.toml` clause is #187's defect and is byte-identical) | `sed -n '77p'` → the sentence above |
| `uv.lock` | refreshed by the same change; confined to the `ruff` package block + the single dev-specifier line | `git diff --numstat uv.lock` → `22 22`; `uv lock --check` → exit **0** |
| `openspec/specs/ci/spec.md` | **CI-08** added + 4 Test Mapping rows | § *Spec sync* |
| `openspec/specs/process-boundary/spec.md` | **PB-10** modified — one sentence replaced + `(Previously: …)` note | § *Spec sync* |

No CI format gate was armed: `grep -rn "format" .github/workflows/` → **0 matches**, and no workflow path
appears in the diff. PB-10 keeps enforcement on the local hook and #194 keeps the un-staged-file gap.

## Tracked diff at archive time — six paths

Measured this phase with `git diff --numstat` (the archive sees a tree that `verify-report.md` did not:
`sdd-sync` landed both deltas *after* verification, adding two canonical spec paths to the four the verify
report recorded).

| Path | Added | Deleted | Notes |
| --- | --- | --- | --- |
| `CONTRIBUTING.md` | 1 | 1 | one token added to line 77 |
| `openspec/specs/ci/spec.md` | 83 | 0 | CI-08 block (79) + 1 blank + 4 Test Mapping rows — purely additive |
| `openspec/specs/process-boundary/spec.md` | 3 | 1 | PB-10 paragraph 2 rewritten + `(Previously: …)` note |
| `pyproject.toml` | 5 | 1 | pin line, `required-version`, the explanatory comment |
| `tests/test_ci_workflows.py` | 75 | 5 | helper + constants + three guards + module docstring reconciliation |
| `uv.lock` | 22 | 22 | `ruff` 0.16.0 → 0.16.7 block + dev specifier |
| **Total** | **189** | **30** | **219 changed lines across 6 tracked paths** |

Pre-sync, the tracked diff was **132** (103 added / 29 deleted) over four paths — the figure attempt 1 of the
runtime ledger recorded. The 87-line movement is entirely the two canonical spec files.

Scope proof, measured this phase: `git diff --name-only -- src/sofer/ | wc -l` → **0**;
`git diff --name-only | grep -c README` → **0**; `git diff --name-only | grep -c .github/workflows` → **0**;
`openspec/specs/**` paths → exactly the two intended specs. **No rule-14 module was touched.**

## Spec sync

Domains synced: **`ci`** and **`process-boundary`** — both landed in **one** `sdd-sync` operation
(`sync-report.md`, status `synced`), gated on the clean verify report.

| Operation | Requirement | Result |
| --- | --- | --- |
| `## ADDED` | `ci` **CI-08 — Single authoritative ruff version** | Inserted before `## Test Mapping`; 4 scenarios; 4 Test Mapping rows appended after the CI-07 rows |
| `## MODIFIED` | `process-boundary` **PB-10 — Formatter integrity on a clean checkout** | One body sentence replaced; `(Previously: …)` note appended; five scenarios byte-identical |
| `## REMOVED` | — | **None.** No requirement was deleted or renamed |

**Post-sync canonical measurements** (final-state facts, re-checked independently by the orchestrator and
re-measured by this phase):

| Measurement | Pre-sync | Post-sync | Measured this phase |
| --- | --- | --- | --- |
| `grep "^\| CI-0" openspec/specs/ci/spec.md \| wc -l` | 22 | **26** | **26** ✓ |
| … of which naming `tests/test_ci_workflows.py` | 15 | **18** | **18** ✓ |
| `grep -c "CI-08" openspec/specs/ci/spec.md` | 0 | **6** (1 heading + 1 body sentence + 4 rows) | **6** ✓ |
| `grep -c "CI-08" openspec/specs/process-boundary/spec.md` | 0 | **1** (PB-10's restatement) | **1** ✓ |

PB-10's five scenarios are byte-identical to the delta's, proven by hash over equal-extent regions:
`sha256 0735123bd1b16448318ffcc5bbc45a68049ad681e727b6b943ac96454b3b1ad7` on both sides — re-measured this
phase on the canonical and delta regions (identical after trailing-whitespace normalisation), matching the
sync phase's figure.

**Destructive merge guard**: `openspec/config.yaml` `rules.archive` says *"Warn before merging destructive
deltas."* Nothing here was destructive — one sentence replaced in PB-10, all of CI-08 additive (83 added /
**0 deleted** in the canonical `ci` file), no `REMOVED`, no `RENAMED`, no partial MODIFIED block, no scenario
dropped. **No destructive-sync approval was required and none was assumed.**

**Same-domain active-change warning**: none. `openspec/changes/` holds only this change plus `archive/`; no
other active change touches `ci` or `process-boundary`.

**Legacy flat `spec.md`**: absent (`ls …/spec.md` → ENOENT). The change carries `specs/ci/spec.md` and
`specs/process-boundary/spec.md` — the canonical delta layout.

## Acceptance criteria — issue #195

Verbatim criteria from the proposal's traceability table; verdicts as adjudicated by the verify phase, with
the two non-parity items recorded exactly as they stand.

| AC | Verdict | Basis |
| --- | --- | --- |
| 1 — one authoritative version, named in `CONTRIBUTING.md` | **SATISFIED** | Three declarations at `0.16.7`; `required-version` enforcing; `CONTRIBUTING.md:77` names it; guard tests S1 + S3 green |
| 2 — hook `rev` and dev dependency agree | **SATISFIED** | `v0.16.7` vs `==0.16.7`; guard green; mutation leg 1 (rev → `v0.16.6`) turns it RED; `.pre-commit-config.yaml` genuinely needs no edit |
| 3 — `ruff format --check` and the `ruff-format` hook agree on the same file | **SATISFIED ON SUBSTANCE — explicitly NOT claimed as exit-code parity** | Both surfaces judged the same bytes unformatted; the hook rewrote them to byte-exactly the bytes surface A predicted; the hook's **own bundled binary** (`ruff 0.16.7`) in check mode returned exit **1** with the identical message. `pre-commit run ruff-format` itself exited **0** because the hook entry is a *fixing* command (`entry: ruff format --force-exclude`) and pre-commit detects modification through `git diff`, which is blind to an untracked file |
| 4 — suite green, `ruff check` and `mypy src/` clean | **SATISFIED** | `1784 passed, 6 skipped` (module `19 → 22` test functions = the three guards, skip count unchanged); enforced-scope lint and mypy clean |
| 5 — `uv.lock` refreshed in the same change | **SATISFIED — refresh accepted** | `22/22` confined to the `[[package]] name = "ruff"` block plus the single dev-specifier line; `uv lock --check` exit **0** (re-measured this phase) |

AC5 ownership note: the obligation is homed in `ci` **CI-08**, whose body states the refresh must be
confined to the ruff block and the dev specifier, and that `packaging` PKG-06 "SHALL NOT be read as owning
this one". The proposal's earlier AC5 row naming PKG-06 as owner is superseded, as `apply-progress.md` §2.8
records.

## Verify gate — natively validated, re-run in this phase

```console
$ gentle-ai sdd-verify-validate --input openspec/changes/2026-09-15-chore-ruff-single-authority/verify-report.md --requirements 2 --scenarios 9
{
  "valid": true,
  "verdict": "pass",
  "evidence_revision": "sha256:4a01a3e883fa91bb2f7d11eda7239bd6d00b2d0fb2376378db10d97f7902a1b1"
}
```

Independent of that envelope, the report itself carries `blockers: 0` and `critical_findings: 0`, and the
ledger's attempt 1 (apply) is `outcome: passed`. No `FAIL`, `BLOCKED` or `CRITICAL` marker exists anywhere
in `verify-report.md` — the only occurrences of those words are inside the sentence declaring their absence
and inside the negative-space lists (`§ Unverified / not demonstrated`, `§ Blockers`), which is a statement
of scope, not an unresolved finding.

## Gates re-measured in this archive phase

Read-only, non-mutating commands; no tracked file was touched by any of them.

| Check | Command | Result |
| --- | --- | --- |
| Verify envelope valid | `gentle-ai sdd-verify-validate …` | `valid: true, verdict: pass` |
| Guard module green | `.venv/Scripts/python.exe -m pytest tests/test_ci_workflows.py -q` | `22 passed in 0.12s` (run through the venv interpreter to avoid uv's default re-lock touching `uv.lock`) |
| Lock consistent | `uv lock --check` | `Resolved 106 packages in 1ms`, exit **0** |
| Canonical row arithmetic | `grep "^\| CI-0" openspec/specs/ci/spec.md \| wc -l` / `… \| grep -c test_ci_workflows.py` | **26** / **18** |
| Forward reference resolves | `grep -c "CI-08"` on both canonical specs | **6** / **1** |
| Scenario byte-identity | `awk` region extraction + `sha256sum` | both `0735123bd1b16448318ffcc5bbc45a68049ad681e727b6b943ac96454b3b1ad7` |
| Module holds no version literal | `grep -c "0\.16" tests/test_ci_workflows.py` | **0** |
| Diff scope | `git diff --name-only` | the six tracked paths, nothing else |

## Task completion gate

Re-read immediately before the report write and the move:

```console
$ grep -cE '^\s*- \[x\]' openspec/changes/2026-09-15-chore-ruff-single-authority/tasks.md
45
$ grep -nE '^\s*- \[ \]' openspec/changes/2026-09-15-chore-ruff-single-authority/tasks.md
(no output — exit 1, zero matches)
```

**45 checked / 0 unchecked — this is the correct final state and no repair was performed.** No
stale-checkbox reconciliation was needed, so none was undertaken. Phase 6 of `tasks.md` is **prose, not
checkboxes**, deliberately: those four obligations are `<!-- sdd-owner: parent -->` and belong to
`sdd-sync`, which discharged them (see `sync-report.md`). Tagging them as implementation checkboxes created
a circular dependency (apply could not complete while sync refused to run without a verify report).
**Do not re-introduce checkboxes into Phase 6.**

## Structured status and `actionContext` findings

| Field | Value consumed | Finding |
| --- | --- | --- |
| `changeName` | `2026-09-15-chore-ruff-single-authority` | Matches the change root and every artifact. No finding. |
| `artifactStore` | `openspec` native / `hybrid` session preflight | Both backends written: this file + the Engram record. No conflict. |
| `planningHome.mode` | `repo-local` | Change root resolves inside the repository. No finding. |
| `actionContext.mode` | `repo-local` | **No `workspace-planning` gate applies**; no `allowedEditRoots` requirement was triggered. |
| `actionContext.workspaceRoot` | `C:\Users\elaze\Desktop\sofer` | Authoritative root. The move source, the move target and this report are all inside it. |
| `actionContext.allowedEditRoots` | `[C:\Users\elaze\Desktop\sofer]` | Satisfied — only the change-directory move and this report were written. |
| `dependencies.archive` | `ready` | Authorised this phase. |
| `dependencies.verify` | `all_done` | The clean verify report is the gate that opened the archive. |
| `taskProgress` | `total: 45, completed: 45, pending: 0, allComplete: true` | Re-derived above, not trusted. |
| `relationships.sameDomainActiveChanges` | `[]` | Re-confirmed: no other active change touches `ci` or `process-boundary`. |
| `blockedReasons` | non-empty, `maintainer_decision` on the runtime attempt | **Does not gate archive.** The `archive` phase instruction is `State: ready`; the blocker is the attempt-ledger accounting item R0 below, which is an orchestration concern, not an archive-readiness concern. Named here so it is not read as cleared by archiving. |
| `nextRecommended` | `archive` | Executed by this phase. |

## Open items — carried forward, not failures of this change

**R0 — the runtime attempt ledger is over budget and awaits a maintainer decision.**
Re-measured this phase with `gentle-ai sdd-attempt status`:

```text
changed_lines: 132      # attempt 1 (apply)
changed_lines: 4186     # attempt 2 (verify)
cumulative_changed_lines: 4186
lifetime_changed_lines: 4318
decision_required: true
next_action: "reset"
max_changed_lines: 400  (explicit)
```

The verify attempt was settled with `--untracked-scope select`, which charged all ten change-root SDD
artifacts (**4186** lines) against a **400**-line objective, where the tracked diff is **132**. The
verification verdict is **unaffected** — the over-budget state is accounting, not evidence. `reset` is
maintainer-only and remains pending. This archive deliberately does **not** run `reset`, `rescope` or any
attempt mutation.

**R1 — a pre-existing defect found by this change's apply phase and confirmed by verify — now GitHub #216.**
The `ruff-format` pre-commit hook declares `types_or: [python, pyi, jupyter, markdown]`, so it rewrites
`README.md` and `README_ES.md`. It was reverted and deliberately **not** absorbed; it belongs to **#216 —
"chore: the ruff-format pre-commit hook rewrites README.md and README_ES.md (its types_or includes
markdown)"**, created 2026-09-15 alongside this launch. It is version-independent (0.16.0 and 0.16.7 agree)
and outside the enforced `src/ tests/ scripts/` scope. **Both READMEs are clean in this diff** — measured
this phase: `git diff --name-only | grep -c README` → 0.

**`ci/spec.md` `## Purpose` (`:5-11`) still enumerates `CI-01..CI-06`.**
Stale for CI-07 and now for CI-08, and left untouched on the CI-07 precedent — fixing it would edit
canonical prose for another requirement's defect. The sync phase proved it byte-identical to `HEAD`
(`sha256 803a63559a0bcbf86182e6517171a597b4ee0ad863639e7a9fffa63fca2cb3af`). **This must be named in the PR
body so a reviewer does not read it as an oversight.**

**AC3 is met on substance, not on exit-code parity.**
`ruff format --check` on the untracked probe exited **1**; the same file through `pre-commit run ruff-format`
was rewritten to exactly the predicted bytes but exited **0**, because the hook's entry is a fixing command
and pre-commit's modification detection is `git diff`-based (blind to an untracked file). Exact parity was
obtained from the hook's own bundled binary (`ruff 0.16.7`, check mode → exit **1**, identical message).
Recorded as **met-on-substance, explicitly not as "parity proven"**. Also unverified: wrapper behaviour on a
*tracked* misformatted file (producing one would require editing a production file, outside the phase's edit
authority).

**AC5 (`uv.lock`) — refresh accepted.** `22/22` confined to the `[[package]] name = "ruff"` block
(`version` 0.16.0 → 0.16.7, the `sdist` line, 17 wheel entries) plus the single dev-specifier line in the
`sofer` metadata block: `{ name = "ruff", specifier = ">=0.9.0" }` → `"==0.16.7"`. Lock header untouched, no
package added or removed, no whitespace churn. `uv lock --check` exit **0**.

**Rule 6 finding, carried from verify.** CI-08 S1/S2/S3 map 1:1 to the three guards; **CI-08 S4 has no
pytest test** — it maps to verify-phase runtime evidence, as the delta's fourth Test Mapping row declares,
following the repo's CI-01 S2 / CI-07 precedent and rule 9. Reported as a finding, not scored as a gap.

## Deviations recorded

1. **`uv.lock` was already refreshed before apply's explicit probe** — `uv run` re-locks by default when
   declarations change, so the probe's step-0 assertion (`git status --porcelain uv.lock` → empty) was
   already false. No `--upgrade-package` fallback was needed; the confinement was re-derived independently
   and confirmed by `uv lock --check`. Not a defect.
2. **REFACTOR does not apply** — no production code was added; the only structural concern (shared
   extraction vs duplication) is satisfied by construction: one helper, three guards, existing
   `_read_text` / `_load_toml` / `_load_yaml` / `_workflow_names` reused, no new file, no new import.
3. **Mutation-revert safety** — the three mutation probes were restored by **re-editing** the declared value
   and proving whole-file `sha256` identity, never by `git checkout --`, which would have deleted this
   change's own uncommitted edits. Consistent with `tasks.md` correction 5.
4. **Phase 6 is prose** — see the task completion gate above.
5. **Proposal-time unverified items are retired**: the upstream `v0.16.7` tag **does** resolve (a new
   pre-commit clone appeared at `~/.cache/pre-commit/repon1p3j7_t/`, pinning `ruff==0.16.7`; the previously
   newest clone pinned `0.16.6`), so the hook materialises and no workaround (`language: system`, rev
   downgrade, claiming AC3 from surface A alone) was used. `required-version` was confirmed on 0.16.7
   specifically. The `uv.lock` delta shape was measured, not reasoned.

## Nothing was committed

**No commit, no push, no tag, no PR, no release, no `size:exception`, no `reset`.** Every tracked change is
still an uncommitted working-tree modification on `chore/195-ruff-single-authority`:

```console
$ git status --porcelain
 M CONTRIBUTING.md
 M openspec/specs/ci/spec.md
 M openspec/specs/process-boundary/spec.md
 M pyproject.toml
 M tests/test_ci_workflows.py
 M uv.lock
?? openspec/changes/archive/2026-09-15-chore-ruff-single-authority/
```

The archive phase's only writes are the move of the change directory and this report. Rollback of the whole
change remains a single `git revert` once committed; the only non-git artefact is the untracked, per-clone
`.git/hooks/pre-commit` written by AC3's evidence path, removable with `pre-commit uninstall`.

## Files

Archived: `proposal.md`, `preproposal.md`, `explore.md`, `design.md`, `tasks.md`, `apply-progress.md`,
`verify-report.md`, `sync-report.md`, `specs/ci/spec.md`, `specs/process-boundary/spec.md`,
`archive-report.md`.

Engram record: topic key `sdd/2026-09-15-chore-ruff-single-authority/archive`.

**Not present, and never was:** a flat legacy `openspec/changes/{change}/spec.md`.

## Key Learnings

1. `sdd-sync` landing canonical deltas after verification means the archive always sees more tracked paths than the verify report recorded.
2. An over-budget runtime attempt ledger records accounting, not evidence, so a passing verification verdict stays valid while `reset` waits on a maintainer.
3. Because an active change directory is untracked, moving it under `changes/archive/` leaves the whole destination untracked in `git status`, so the move must be confirmed by listing the new path.
4. Re-measuring the canonical row arithmetic and the preserved-scenario hash in the archive phase is cheap and independently confirms the sync phase's claims.
5. Running the guard suite through the venv interpreter instead of `uv run` avoids the default re-lock silently rewriting `uv.lock` during archive verification.
