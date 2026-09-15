# Sync Report — 2026-09-15-chore-ruff-single-authority

**Status: `synced`** — both deltas landed in **one** operation. Nothing was left half-written.

- Change: `2026-09-15-chore-ruff-single-authority` (GitHub #195) · branch `chore/195-ruff-single-authority` · HEAD `5a2ae38`
- Store: **hybrid** — this file **and** the Engram record under topic key `sdd/2026-09-15-chore-ruff-single-authority/sync`
- Domains synced: `process-boundary` (MODIFIED **PB-10**) and `ci` (ADDED **CI-08**)
- Sync gate: clean `verify-report.md` present — `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 9/9`, `evidence_revision sha256:4a01a3e8…`
- This run **overwrites** the earlier `status: blocked` report (that launch had no verify artifact; the blocker is cleared)

## What changed, in one table

| Canonical file | Edit | Hunk | Lines |
| --- | --- | --- | --- |
| `openspec/specs/process-boundary/spec.md` | PB-10 body paragraph 2 rewritten + `(Previously: …)` note appended | `@@ -258 +258,3 @@` | 1 deleted / 3 added |
| `openspec/specs/ci/spec.md` | CI-08 requirement block inserted before `## Test Mapping` | `@@ -284,0 +285,79 @@` | 79 added |
| `openspec/specs/ci/spec.md` | 4 CI-08 Test Mapping rows appended after the CI-07 rows | `@@ -317,0 +397,4 @@` | 4 added |

New file digests: `process-boundary/spec.md` `sha256 44ea078a5ac5c44a382376bbd5b60585f0ebf5c2052927459ea23ec9ea845607`;
`ci/spec.md` `sha256 f1183295bda316848f90763e11f7b21c73eea1fba745139ae3be86472c58d93a`.

Source of truth: the change-root deltas. **No text was re-authored** — the CI-08 requirement block and the four rows were spliced byte-for-byte from `specs/ci/spec.md`, and PB-10's paragraph + note from `specs/process-boundary/spec.md`.

## 1. `openspec/specs/process-boundary/spec.md` — PB-10 MODIFIED

```console
$ git diff -U0 -- openspec/specs/process-boundary/spec.md
@@ -258 +258,3 @@ The repository's Python sources and tests SHALL satisfy the project formatter: `
-The requirement SHALL be satisfiable with no new CI step: … The ruff version pin mismatch (pre-commit `v0.16.7` versus the environment's `0.16.0`) SHALL stay unaddressed here and SHALL be owned by issue #195. Evidence for this requirement is command output, and the sibling gates SHALL remain green and unweakened (PB-05, PB-07, `ci` CI-01, `coverage` COV-06).
+The requirement SHALL be satisfiable with no new CI step: … The ruff version SHALL have a single declared authority — the environment's dev dependency pin, `[tool.ruff] required-version`, and the pre-commit `rev` SHALL name the same version, asserted statically by the guard required by `ci` CI-08. Alignment SHALL remain a declaration-and-local-hook matter: it SHALL arm no CI step, and issue #194 SHALL retain ownership of the un-staged-file gap. Evidence for this requirement is command output, and the sibling gates SHALL remain green and unweakened (PB-05, PB-07, `ci` CI-01, `coverage` COV-06).
+
+(Previously: the paragraph deferred the pin mismatch — `v0.16.7` hook versus `0.16.0` environment — to issue #195; change `2026-09-15-chore-ruff-single-authority` owns it, and no version literal remains in this spec.)
```

Exactly one hunk, exactly one body sentence replaced, plus the `(Previously: …)` note — the established canonical convention (`process-boundary/spec.md:12,63,95,115,232`), not a version-literal violation.

### Everything else in PB-10 preserved

| Surface | Check | Result |
| --- | --- | --- |
| `:254` framing blockquote | text present verbatim | **preserved** |
| "no new CI step" clause | present in the rewritten paragraph | **preserved** |
| #194 ownership (both clauses) | `issue #194 owns both the decision to arm such a gate` + `#194 SHALL retain ownership of the un-staged-file gap` | **preserved** |
| "Evidence for this requirement is command output …" tail | present verbatim | **preserved** |
| Zero-`format --check` scenario | `#### Scenario: No CI gate was armed, and recurrence stays owned by #194` → `THEN zero matches SHALL exist in both states` | **preserved** |

### PB-10's five scenarios are byte-identical — proven, not asserted

```console
$ python: canonical scenario region == delta scenario region   → True
$ sha256 canonical scenarios: 0735123bd1b16448318ffcc5bbc45a68049ad681e727b6b943ac96454b3b1ad7
$ sha256 delta     scenarios: 0735123bd1b16448318ffcc5bbc45a68049ad681e727b6b943ac96454b3b1ad7
$ scenario count canonical: 5      $ scenario count delta: 5
```

Region boundaries: from `#### Scenario: Clean-checkout format check exits 0` to the next `### Requirement` (canonical) / to `---` before `## Scope boundaries` (delta) — both regions end on the same trailing blank line, so the comparison is hash-exact over equal extents.

### The whole MODIFIED block matches the delta

```console
$ diff <canonical PB-10 block> <delta ## MODIFIED block>   → empty
$ python: canonical PB-10 block == delta ## MODIFIED block (minus the delta's framing header) → True
```

So the canonical block now **is** the delta block; the only difference between the two files is the delta's `## MODIFIED Requirements` framing header and its surrounding delta-only prose.

## 2. `openspec/specs/ci/spec.md` — CI-08 ADDED + 4 Test Mapping rows

```console
$ git diff -U0 -- openspec/specs/ci/spec.md | grep '^@@'
@@ -284,0 +285,79 @@ The pin SHALL make the documented, flag-free gate commands satisfiable on a clea
@@ -317,0 +397,4 @@ evidence recorded in the verify report.
$ git diff --numstat -- openspec/specs/ci/spec.md
83  0  openspec/specs/ci/spec.md        # 79-line CI-08 block + 1 blank + 4 rows
```

- The CI-08 requirement body and its four scenarios are **byte-identical to the delta** (`canonical CI-08 block == delta CI-08 block` → `True`), inserted after CI-07's terminating `---` and before the next `---` / `## Test Mapping`.
- The four rows are the delta's rows verbatim and are appended **after the CI-07 rows**, in the existing 3-column format; the two verify-phase rows follow the convention already in use at the former `:313-314`:

```text
| CI-08 | Dev pin, required-version, and hook rev agree | `tests/test_ci_workflows.py` — `test_ruff_pin_hook_rev_and_required_version_agree`: tomllib + YAML declaration equality, with `X.Y.Z` extracted from the dev pin |
| CI-08 | No workflow declares a ruff version | `tests/test_ci_workflows.py` — `test_workflows_do_not_declare_a_ruff_version`: YAML/full-text scan of `.github/workflows/*.yml` |
| CI-08 | CONTRIBUTING names the declared version | `tests/test_ci_workflows.py` — `test_contributing_names_the_declared_ruff_version`: text inspection of `CONTRIBUTING.md` |
| CI-08 | required-version rejects a mismatched binary | Verify-phase runtime evidence — `uv run ruff check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/ scripts/` exit codes under a mismatched `required-version` probe and under the declared value (CI-01 gate-exit-code precedent) |
```

- Guard: **zero deleted lines** in `ci/spec.md` — the change is purely additive, so no other requirement or scenario was disturbed.

### `## Purpose` deliberately untouched

```console
$ python: Purpose paragraph (## Purpose → ## Requirements) byte-identical to HEAD → True
$ sha256 HEAD: 803a63559a0bcbf86182e6517171a597b4ee0ad863639e7a9fffa63fca2cb3af
$ sha256 work: 803a63559a0bcbf86182e6517171a597b4ee0ad863639e7a9fffa63fca2cb3af
```

Its `CI-01..CI-06` enumeration stays stale for CI-07 and now CI-08 by design (CI-07 precedent left Purpose alone). **This must be named in the PR body** so a reviewer does not read it as an oversight.

## 3. Obligations 6.2–6.4 — real commands, real output

### 6.2 — post-sync reference invariant

```console
$ grep -c "CI-08" openspec/specs/ci/spec.md
6            # 1 heading + 1 body sentence ("stated here, in CI-08") + 4 rows
$ grep -c "CI-08" openspec/specs/process-boundary/spec.md
1            # PB-10's single-authority sentence
```

Both non-zero. The forward reference now resolves: wherever PB-10's restatement appears, `CI-08` **exists** in `ci/spec.md`.

### 6.3 — table arithmetic, pre-sync vs post-sync

| Measurement (`grep`) | Pre-sync | Post-sync | Delta |
| --- | --- | --- | --- |
| `grep "^\| CI-0" openspec/specs/ci/spec.md \| wc -l` | **22** | **26** | **+4** |
| `grep "^\| CI-0" openspec/specs/ci/spec.md \| grep -c "test_ci_workflows.py"` | **15** | **18** | **+3** |

```console
$ # pre-sync (measured before the write, in this run)
CI-0 rows: 22
test_ci_workflows.py rows: 15
$ # post-sync
rows: 26
module rows: 18
$ # PB-10 block identity
canonical PB-10 block == delta ## MODIFIED block (minus framing header): True
```

The +4 / +3 delta is **measured on both sides of the write**, not asserted. The 18 module-named rows are 15 canonical + 3 new CI-08 pytest rows; the fourth CI-08 row is verify-phase runtime evidence, which is why it is not counted among the module-named rows.

### 6.4 — canonical-scope guard

```console
$ git diff --name-only
CONTRIBUTING.md
openspec/specs/ci/spec.md
openspec/specs/process-boundary/spec.md
pyproject.toml
tests/test_ci_workflows.py
uv.lock

$ git status --porcelain
 M CONTRIBUTING.md
 M openspec/specs/ci/spec.md
 M openspec/specs/process-boundary/spec.md
 M pyproject.toml
 M tests/test_ci_workflows.py
 M uv.lock
?? openspec/changes/2026-09-15-chore-ruff-single-authority/
```

Apply's four verified paths are intact and unmodified by this phase, and the **only** two `openspec/specs/**` paths added are the two intended canonical specs. Zero `.github/workflows/**`, zero `src/sofer/**`, zero `README*`, zero `.pre-commit-config.yaml`.

### Post-sync sanity (spec-only change, no regression)

```console
$ git diff --check            → (clean)
$ uv run pytest tests/test_ci_workflows.py -q
22 passed in 0.12s
$ git diff --stat -- openspec/specs/
 openspec/specs/ci/spec.md               | 83 +++++++++++++++++++++++++++++++++
 openspec/specs/process-boundary/spec.md |  4 +-
 2 files changed, 86 insertions(+), 1 deletion(-)
```

## 4. Structured status and `actionContext` findings

| Field | Consumed value | Finding |
| --- | --- | --- |
| `changeName` | `2026-09-15-chore-ruff-single-authority` | Matches the change root and every artifact. No finding. |
| `artifactStore` | `openspec` (native) / `hybrid` (session preflight) | Both backends written: this file **and** the Engram record. No conflict. |
| `actionContext.mode` | `repo-local` | No `workspace-planning` gate fires; no `allowedEditRoots` requirement triggered. |
| `actionContext.workspaceRoot` | `C:\Users\elaze\Desktop\sofer` | Authoritative root; every path read and every path written is inside it. |
| `actionContext.allowedEditRoots` | `["C:\Users\elaze\Desktop\sofer"]` | Satisfied — only the two canonical specs and this report were written. |
| `dependencies.verify` | `ready` (this launch's status) | The clean verify report is the gate that opened this phase. |
| `dependencies.sync` (injected block) | `blocked` (stale projection) | Superseded by this run: a validated pass verify report (`evidence_revision sha256:4a01a3e8…`) now exists and the sync gate is open. Measured post-sync: `CI-08` non-zero in both files, 26 rows / 18 module rows. |
| `nextRecommended` (injected block) | `sdd-verify` (stale projection) | Superseded: verify is complete and this sync landed. Next is `sdd-archive`. |
| `collisions` | `[]` | Re-confirmed — `openspec/changes/` holds only this change plus `archive/`; no other active change touches `ci` or `process-boundary`. |
| `blockedReasons` | `[]` | Nothing blocked. |

**Non-authoritative carve-out**: not triggered — `nextRecommended` was never `resolve-via-engram`, and the store is file-backed (`openspec`), so the deltas were read from and written to the filesystem.

**Destructive-sync guard**: no `## REMOVED Requirements`, no `## RENAMED Requirements`, no large MODIFIED block (one sentence + one note), no legacy flat `spec.md`, no same-domain active collision → **no explicit approval was required**, and none was assumed.

## 5. Explicitly NOT synced, and why

| Target | Not synced | Why |
| --- | --- | --- |
| `tasks.md` | Nothing ticked | Phase 6 is prose by design (`<!-- sdd-owner: parent -->`, no checkboxes) so the native `allComplete` gate for `verify` can complete. Editing it would have changed a file the verify report is bound to. **`tasks.md` is untouched.** |
| `ci/spec.md` `## Purpose` (`:5-11`) | Left stale | Deliberate — pre-existing omission (CI-07 precedent), recorded as a PR-body note. Its hash is byte-identical to `HEAD`. |
| `pyproject.toml`, `uv.lock`, `CONTRIBUTING.md`, `tests/**`, `.github/**` | Untouched | Apply's verified, uncommitted state — the verify report's `evidence_revision` is bound to it. Re-editing would invalidate that binding. |
| Change-root delta files | Untouched (read-only source of truth) | They are the authoritative delta text; the canonical specs received it verbatim. |
| Archive | Not performed | `sdd-sync` publishes canonical specs and keeps the change active; the dated move is `sdd-archive`'s job. |
| Commits / pushes | None | Out of scope for this phase. |

No file outside the two canonical specs and this report was written. No child subagent was launched.

## 6. Next step

`sdd-archive` — verify is clean, sync has landed, and 45/45 implementation tasks are complete with zero unchecked rows. Expected archive precondition state: `CI-08` present in both canonical specs, 26 `ci` Test Mapping rows of which 18 name `tests/test_ci_workflows.py`, and PB-10's modified clause quoted above at `process-boundary/spec.md:258-260`.

## Key Learnings

1. Splicing delta blocks by exact line range instead of retyping them guarantees byte-identical canonical text and removes whitespace risk from wrapped prose.
2. A sync that must combine a forward reference and its target should splice both deltas in a single write so no intermediate state contains a dangling reference.
3. Diff-alignment ambiguity around repeated separator lines can visibly render an insertion in a different position than the constructed output, so the written bytes must be re-measured, not read off the diff.
4. Proving byte-identity of a preserved block is cheaper and stronger as a hash comparison over equal-extent regions than as a line-by-line diff.
5. The pre-sync and post-sync counts must both be measured in the same run, because only the pair proves the arithmetic delta rather than asserting it.
