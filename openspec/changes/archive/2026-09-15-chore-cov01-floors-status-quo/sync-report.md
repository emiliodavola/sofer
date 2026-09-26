# Sync report: chore-cov01-floors-status-quo

**Change** `2026-09-15-chore-cov01-floors-status-quo` (GitHub #215) · branch
`chore/215-cov01-floors-status-quo` · store **hybrid** (report path
`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/sync-report.md`; Engram topic key
`sdd/2026-09-15-chore-cov01-floors-status-quo/sync-report`) · phase `sdd-sync` · canonical target
`openspec/specs/coverage/spec.md`.

## Status

**SYNCED.** Domain `coverage` synced to canonical: **+1 ADDED requirement** (COV-07) with its one scenario, and
**+1 row** appended to the existing `## Test Mapping` table. **0 MODIFIED**, **0 REMOVED**, **0 RENAMED**.
No collision, no destructive delta, no blocker. The change directory **stays active** — `sdd-sync` does not
archive (`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/` is untouched and still present;
`openspec/changes/archive/` was not written to).

Inputs read this phase (directly, from the OpenSpec backend):

- `…/proposal.md`, `…/specs/coverage/spec.md` (delta, 117 lines), `…/design.md` (§ *Insertion-point
  mechanics*, § *Guard analysis*), `…/tasks.md` (33/33 checked), `…/verify-report.md` (**PASS**, envelope at
  head), `AGENTS.md` rule 14, `openspec/specs/process-boundary/spec.md` (PB-14 precedent from #216).

## Structured status and actionContext

The parent-injected `gentle-ai.sdd-status` snapshot marked `sync: blocked`. That snapshot was **stale**: it was
taken before `verify-report.md` was written. Re-deriving read-only with
`gentle-ai sdd-status 2026-09-15-chore-cov01-floors-status-quo` returned:

```text
next: archive
apply: all_done
verify: all_done
archive: ready
tasks: 33/33 complete
nextRecommended: "archive"
blockedReasons: []
```

`artifacts.verifyReport: "done"`, `collisions: []`, `relationships.sameDomainActiveChanges: []`. The injected
snapshot also carried `blockedReasons: []`, so there was nothing to return as a blocker; with verify clean and
zero same-domain collisions, the sync precondition ("sync only after verification is clean") is satisfied and
the phase proceeded.

- `actionContext.mode: repo-local` (not `workspace-planning`), `workspaceRoot` =
  `C:\Users\elaze\Desktop\sofer`, `allowedEditRoots` = `["C:\Users\elaze\Desktop\sofer"]` — the canonical
  target is inside the root, so no `allowedEditRoots` block applies.
- Active change selection unambiguous; `artifactStore: openspec` per the engine while the session preflight
  chose **hybrid**, so this phase did **both**: filesystem canonical promotion *and* the Engram mirror.
- Verify verdict consumed: `pass`, 1/1 requirement, 1/1 scenario, 0 blockers, 0 critical findings. No `FAIL`,
  `BLOCKED`, or `CRITICAL` token is present as an unresolved finding.

## Step 0 — anchors re-verified by TEXT (not line numbers)

`design.md` risk row *"Anchors drift"* and `verify-report.md` risk 2 both require re-verification by text. All
five anchors were re-resolved on the working tree **before** any edit:

```text
$ grep -c '^### Requirement:' openspec/specs/coverage/spec.md      # pre-sync
6
$ grep -n '^### Requirement:' openspec/specs/coverage/spec.md
54:  …(COV-01)      94: …(COV-02)      125: …(COV-03)
167: …(COV-04) RETIRED   186: …(COV-05)      214: …(COV-06)

$ grep -n '^---$' openspec/specs/coverage/spec.md
92  123  165  184  212  281          # 281 = the `---` closing COV-06's last scenario

$ grep -n '^## Test Mapping' openspec/specs/coverage/spec.md
283

$ grep -n '^| Req | Scenario | Verification |' openspec/specs/coverage/spec.md
306
$ grep -n '^| --- | -------- | ------------ |' openspec/specs/coverage/spec.md
307

$ grep -c '^| COV-' openspec/specs/coverage/spec.md
17                                     # rows 308–324; :324 is the file's final content line
$ awk 'NR==324' openspec/specs/coverage/spec.md | cut -c1-40
| COV-06 | TOTAL stays config-owned at 90
```

Byte-level confirmation of the seam (`sed -n '275,285p' … | od -c`):
`… behavior)\n` `\n` `---\n` `\n` `## Test Mapping\n` `\n`. The anchors were found **exactly where the design
recorded them** (`:281`, `:283`, `:306`, `:307`, `:324`) — no drift this time.

Additional pre-edit invariant confirmed: **the canonical file has no trailing newline** (`HEAD` blob also ends
without one: `… gate (rc 0) |`, 23095 bytes, 324 lines, `ends-NL=False`). See § *The single numstat deletion*.

## Step 1 — COV-07 block inserted between the COV-06-closing `---` and `## Test Mapping`

Edit shape (text anchors, resolved by the literal seam string `---\n\n## Test Mapping\n`, count asserted `== 1`):

```text
- THEN `fail_under` SHALL equal 90 … TOTAL gate's behavior)      :279
                                                                 (blank)   :280
---                                                              :281
                                                                 (blank)   :282   ← reused as the blank BEFORE the block
+ ### Requirement: Second-tier per-file floors … (COV-07)             :283  ← 49 delta lines, byte-identical
+ …                                                                   …
+ #### Scenario: No gate is armed for the three second-tier floors     …
+ - AND this SHALL remain **verify-phase static evidence** …           :329
+                                                                 (blank)   :330
+ ---                                                                 :331  ← the block's OWN trailing separator
                                                                 (blank)   :332
 ## Test Mapping                                                  :333
```

Result: the original `:281` `---` became the separator *before* COV-07 and COV-07's own trailing `---` is the
separator *before* `## Test Mapping` — **exactly one blank line on each side of the block and no doubled
separator** (the named silent-failure mode in `design.md`).

```text
$ grep -n '^---$' openspec/specs/coverage/spec.md        # post-sync
92  123  165  184  212  281  331                          # 331 = COV-07's own separator; no adjacency
$ grep -c '^## Test Mapping' openspec/specs/coverage/spec.md
1
$ awk 'NR>=281 && NR<=283' openspec/specs/coverage/spec.md | cat -A | cut -c1-30
---
$
### Requirement: Second-tier…
```

Blank-line convention matched to #216's PB-14 insertion into `openspec/specs/process-boundary/spec.md`
(`---` / blank / block / blank / `## …`).

## Step 2 — exactly one row appended as the table's new final data row

The delta's own `| COV-07 | … |` line was copied **verbatim** (646 chars) as a new final line after the COV-06
TOTAL row. The `| Req | Scenario | Verification |` header (`:306`) and the delimiter row (`:307`) were
**not** re-emitted, and no existing row or the `## Test Mapping` intro prose (`:335+`) was edited.

```text
$ grep -n '^| COV-' openspec/specs/coverage/spec.md | tail -3
373:| COV-06 | The cli.py __main__ guard is executed under the coverage tracer | …
374:| COV-06 | TOTAL stays config-owned at 90 | …
375:| COV-07 | No gate is armed for the three second-tier floors | …

$ sed -n '375p' openspec/specs/coverage/spec.md | cut -c1-80
| COV-07 | No gate is armed for the three second-tier floors | Verify-phase **static ev
```

`## Purpose` was deliberately **not** refreshed (the change's recorded non-goal — CI-07/CI-08 precedent; it
already omits COV-04).

## Self-checks (all green)

| # | Check | Expected | Observed |
| --- | --- | --- | --- |
| 1 | `grep -c '^### Requirement:'` | 7 (COV-01..COV-07) | **7** — COV-07 heading at `:283` |
| 2 | `grep -n '^\| COV-' \| tail -1` | COV-07 row last | **`:375`** `\| COV-07 \| No gate is armed …` |
| 3 | File ends at the table | no content after new row | file ends `:375`; `tail -c 1` = `\|` (EOF convention unchanged) |
| 4 | `grep -c '^## Test Mapping'` | 1 | **1** (`:333`) |
| 5 | No doubled `---` at the seam | one separator per side | `---`:281 `---`:331 separated by the block; no `---\n---`, no `---\n\n\n` |
| 6 | Block byte-identical to delta | delta lines 31–79 | **49 lines at canonical `:283–331`, byte-identical** |
| 7 | Row byte-identical to delta | delta line 91 | **appended verbatim** (646 chars, same line) |
| 8 | COV-01..COV-06 byte-identical | every original line unchanged, in order | **all 324 original lines byte-identical** |
| 9 | Diff scope | only the canonical file | `git diff --name-only` → **exactly `openspec/specs/coverage/spec.md`** |
| 10 | Forbidden paths | empty | `src/ tests/ scripts/ .github/ pyproject.toml uv.lock AGENTS.md README*.md CONTRIBUTING.md .pre-commit-config.yaml` → **empty** |

Checks 6–8 were proven mechanically (not by reading) with a script that re-extracted the block from the delta
by **text anchor**, then asserted:

```text
[1] HEAD blob: 23095 bytes, 324 lines, ends-NL=False
[2] worktree : 27532 bytes, 375 lines, ends-NL=False
[3] inserted block: 49 lines; appended row: 646 chars
[4] block at new lines 283..331 is byte-identical to the delta
[5] all 324 original lines are byte-identical, in order, and untouched
[6] the only added trailing line is the delta's COV-07 mapping row; EOF newline unchanged
[7] seam intact: exactly one `---` before `## Test Mapping`, no doubled separator, 7 requirements
```

## The single numstat deletion (adjudicated, disclosed — not a content edit)

```text
$ git diff --numstat -- openspec/specs/coverage/spec.md
52      1       openspec/specs/coverage/spec.md
$ git diff --stat
 openspec/specs/coverage/spec.md | 53 ++++++++++++++++++++++++++++++++++++++++- 
 1 file changed, 52 insertions(+), 1 deletion(-)
```

The parent self-check asked for **insertions only, zero deletions**. That is **mathematically unachievable
for an append to this file** and the reason is structural, not a defect: `openspec/specs/coverage/spec.md` has
**no trailing newline** at its final content line (`:324`), so placing any line *after* it necessarily
re-emits that line with a newline terminator. Git reports the moved `\ No newline at end of file` marker as one
deletion plus one insertion. Verified in isolation before touching the repo:

```text
old: "a\nb\nlast line no newline"   new: "a\nb\nlast line no newline\nnew appended row"
→ 2  1  f.md        # 1 deletion = the no-newline marker, not changed text
```

The only `-` line in the real diff is therefore the COV-06 TOTAL row re-emitted with its newline — its **text
is byte-identical** (self-check 8: `n[i+len(block)+1:] == o_lines[i:] + [row]`, which matches that row exactly).
Two deliberately conservative choices preserve everything else:

1. **The file's EOF convention is unchanged** — the new final row is written *without* a trailing newline, so
   the file still ends `… adds no test |` with `ends-NL=False`, exactly as `HEAD` did. Adding a trailing newline
   instead would have silently changed the file's EOF style (and produced the same 52/1 numstat).
2. **No line was re-wrapped, reordered, or reworded** — the delta's prose was copied verbatim, including its
   ~90-column wrapping and its long single-line scenario bullets.

Net effect: `52 insertions(+), 1 deletion(-)` where the deletion is the EOF marker; **zero characters of
COV-01..COV-06 requirement text changed** (self-check 8 proves it line-by-line).

## Validation commands run

| # | Command | Exit | Observed |
| --- | --- | --- | --- |
| 1 | `grep -c '^### Requirement:' openspec/specs/coverage/spec.md` | 0 | `7` |
| 2 | `grep -n '^\| COV-' openspec/specs/coverage/spec.md` | 0 | 18 rows; last = `:375 \| COV-07 \| …` |
| 3 | `grep -c '^## Test Mapping' openspec/specs/coverage/spec.md` | 0 | `1` |
| 4 | `grep -n '^---$' openspec/specs/coverage/spec.md` | 0 | `92 123 165 184 212 281 331` (no adjacency) |
| 5 | `git diff --numstat -- openspec/specs/coverage/spec.md` | 0 | `52 1` (see § above) |
| 6 | `git diff --name-only` | 0 | `openspec/specs/coverage/spec.md` only |
| 7 | `git diff --name-only -- src/ tests/ scripts/ .github/ pyproject.toml uv.lock AGENTS.md …` | 0 | *(empty)* |
| 8 | `uv run pytest tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100 tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90 -q` | 0 | `3 passed in 0.06s` |
| 9 | `uv run pytest tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate -q` | 0 | `1 passed in 0.04s` |
| 10 | `uv run pytest tests/ -q` | 0 | **`1785 passed, 6 skipped, 1 warning in 58.05s`** |
| 11 | `grep -rn 'openspec/specs' tests/` | 1 (no matches) | *(empty)* — no test reads the canonical spec, so the promotion is test-invisible |
| 12 | `gentle-ai sdd-status 2026-09-15-chore-cov01-floors-status-quo` | 0 | `next: archive`, `verify: all_done`, `blockedReasons: []` |

**Tally re-derived, unchanged.** `1785 passed, 6 skipped` — byte-for-byte the tally `verify-report.md` recorded
(1 warning = the pre-existing `runpy` `RuntimeWarning`, unrelated). Nothing test-visible changed: the delta and
this sync edit are Markdown only, and check 11 proves no test asserts on canonical spec content.

The `build_command` (`uv run ruff check src/ tests/ && uv run mypy src/`) was **not** re-run: this phase touched
no Python file (check 7 forbids it), so there is nothing for those tools to see. The `MD028` markdown advisory
observed during the edit is pre-existing (a blank line inside a blockquote) and is not a repository gate.

## Collisions, destructive deltas, and RENAMED

- **Active same-domain collisions: none.** `relationships.sameDomainActiveChanges: []`, `collisions: []`; and
  no other active change in `openspec/changes/` targets `coverage`. No archive/sync ordering decision was
  needed.
- **Destructive REMOVED / large MODIFIED: n/a.** The delta carries `## ADDED Requirements` only — no
  `## MODIFIED`, `## REMOVED`, or `## RENAMED Requirements` section (verified by reading the delta in full).
  No approval was required or requested.
- **RENAMED: absent**, so the unsupported-helper block does not apply.
- **Legacy flat spec: absent** — the delta is a domain delta at
  `openspec/changes/…/specs/coverage/spec.md`, and the canonical target is the domain file
  `openspec/specs/coverage/spec.md`.
- `rules.sync` in `openspec/config.yaml` (when present) imposes nothing beyond the above.

## Change stays in the change directory (sync ≠ archive)

`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/` is **still in place** (proposal, spec, design,
tasks, apply-progress, verify-report, and now this sync-report); `openspec/changes/archive/` was **not**
written to. No commit, push, or PR was created. The working tree shows exactly one modified tracked file
(the canonical spec) plus the change directory's still-untracked phase artifacts.

## Findings

**None blocking.** Two informational items, both dispositioned:

1. **The injected status snapshot was stale** (`sync: blocked`) while the freshly derived native status reads
   `verify: all_done`, `nextRecommended: archive`, `blockedReasons: []`. Recorded here so a later reader does
   not mistake the snapshot for a live blocker.
2. **The 52/1 numstat vs "insertions only"** — a file-EOF-convention artifact of a no-trailing-newline file,
   proven not to touch any COV-01..COV-06 character (see § *The single numstat deletion*).

## Risks

1. **Sync's job is done but nothing enforces COV-07.** COV-07-S1 is a verify-phase static inspection by design
   (#215 option (b)); if a later change arms one of the three floors, no test turns red. That is the recorded
   invariant, now canonical, and the requirement itself mandates amending COV-07 + COV-06 + COV-03 + the two
   ban-pinning guards in the same future change.
2. **`## Purpose` is now stale with respect to COV-07** (it already omitted COV-04). Deliberate, per the
   change's non-goal and the CI-07/CI-08 precedent; owned by whoever closes the COV-04 gap.
3. **The D5 wording nit** (`verify-report.md` § *Adjudicated nuance*) is untouched by sync — it lives in
   `design.md`, not in the promoted requirement text. Sync did not "fix" it, correctly: the canonical block is
   the delta's byte-exact text.
4. **Anchor drift is now consumed** — this sync read the anchors once and edited; any change landing on
   `coverage` before archive does not affect the already-promoted COV-07 block.

## Next recommended

`sdd-archive` — verification is PASS, sync is complete (COV-07 promoted, row appended), 33/33 tasks checked,
zero unchecked implementation tasks, `blockedReasons: []` and `archive: ready` in the fresh native status.
`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/` is ready to move to
`openspec/changes/archive/2026-09-15-2026-09-15-chore-cov01-floors-status-quo/`.
