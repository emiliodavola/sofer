# Sync report: chore-type-gate-policy

**Change** `2026-09-15-chore-type-gate-policy` (GitHub **#201**) · branch `chore/201-type-gate-policy` ·
store **hybrid** — this file plus the Engram mirror under topic key
`sdd/2026-09-15-chore-type-gate-policy/sync-report` · phase **sdd-sync**.

## Status

**SYNCED.** The verified delta
`openspec/changes/2026-09-15-chore-type-gate-policy/specs/ci/spec.md` is promoted into the single canonical
target `openspec/specs/ci/spec.md`:

- the **CI-09** requirement (2 clause groups + 5 scenarios) inserted between CI-08's closing `---` and
  `## Test Mapping`, carrying its own trailing `---`;
- the 5 **CI-09 Test Mapping rows** appended after the CI-08 `required-version rejects a mismatched binary`
  row (the table's last content row) — the header and delimiter rows are **not** re-emitted;
- the **CI-07** amendment: Occurrence 1's clause (with the COR-7 join resolved), the backticked
  `(Previously: …)` marker, the `> Modified by …` blockquote line, and Occurrence 2's bullet.

**The change stays in `openspec/changes/2026-09-15-chore-type-gate-policy/` — sync does NOT archive, does not
move the directory, does not commit.** `git status --porcelain` still shows the change directory (and
`typings/`) untracked; no file outside `openspec/specs/ci/spec.md` was written by this phase.

Closing evidence: guard **G7** — red by design through apply and verify — is now **green**
(`uv run pytest tests/test_ci_workflows.py -q` → `30 passed in 0.24s`), and the full suite is
`1792 passed, 6 skipped, 1 warning in 61.04s` (zero failures).

## Inputs read and gate checks

| Input | Reading | Gate |
| --- | --- | --- |
| `proposal.md` | present, non-empty | pass |
| `specs/ci/spec.md` (delta) | 301 lines; `## ADDED`, `## Test Mapping`, `## MODIFIED Requirements` | pass |
| `design.md` §6 + amendments §COR-5 / §COR-7 | read in full; both binding | pass |
| `tasks.md` | `grep -c "^\s*- \[x\]"` → 50, `grep -c "^\s*- \[ \]"` → 0 | pass (50/50) |
| `verify-report.md` | `verdict: pass_with_warnings`, `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 5/5` | pass (clearly passing; no `FAIL`/`BLOCKED`/`CRITICAL`) |
| Legacy flat `openspec/changes/<change>/spec.md` | absent — domain spec `specs/ci/spec.md` is present | pass |
| `openspec/config.yaml` | present; no `rules.sync` block declared, so no extra sync rule applies | pass (informational) |
| Delta `## RENAMED Requirements` | absent | pass (nothing to block on) |
| Destructive spans | CI-09 is purely additive; the only removals are CI-07's two stale clauses (2 deleted lines). Explicit parent authorization recorded (DC-11/COR-4, design §6.6) | pass (approval recorded) |
| Same-domain active collisions | native `relationships.sameDomainActiveChanges` = `[]`; no other non-archived change carries `specs/ci/`; archive order not required | pass |

## Structured status and actionContext findings

**The status block injected into this phase was stale, and the discrepancy is recorded rather than
assumed.** The injected snapshot (`schemaVersion: 1`) reported `artifacts.verifyReport: "missing"`,
`dependencies.sync: "blocked"` and `nextRecommended: "sdd-verify"`; that snapshot was computed **before**
verify ran. The live re-derivation (`gentle-ai sdd-status --cwd .`, `schemaVersion: 2`) reports:

```text
next: archive
- apply: blocked
- verify: all_done
- archive: ready
- tasks: 50/50 complete
blockedReasons: [ "native SDD runtime execution is blocked(maintainer_decision) … this work unit's attempt
                  or changed-line budget needs a maintainer decision …" ]
```

- `artifacts.verifyReport: "done"`, `dependencies.verify: "all_done"` — the sync precondition the injected
  snapshot doubted ("sync delta specs into `openspec/specs` only after verification is clean") **is met**;
  the verify verdict is a clean `pass_with_warnings` with zero blockers.
- `actionContext.mode: "repo-local"`, `workspaceRoot = C:\Users\elaze\Desktop\sofer`,
  `allowedEditRoots = ["C:\Users\elaze\Desktop\sofer"]` — the canonical target is inside the authoritative
  root, so no `workspace-planning` / edit-root stop applies.
- The **single** live `blockedReason` concerns the `apply` **work-unit attempt / changed-line budget**
  (`maintainer_decision`) — a delivery-side accounting gate, **not** a sync blocker, and it does not change
  the substance or the write set of this phase. It is surfaced for the parent because it is the same
  accounting the verify report's **W5** delivery-budget finding names; both remain parent-owned.
- `artifactStore: openspec` (routing key for the file-backed path) while the session preflight declares
  **hybrid**, so this phase performed the filesystem sync **and** saves this report to Engram.

## Anchors re-verified BY TEXT before editing (recorded output)

All anchors were located by content, never by remembered line numbers; each probe below returned exactly
`1` occurrence, so every anchor was unambiguous **before** the write.

```text
$ grep -c '^### Requirement:' openspec/specs/ci/spec.md                     → 8
$ grep -c '^#### Scenario:'  openspec/specs/ci/spec.md                     → 26
$ grep -c '^| CI-09 |'       openspec/specs/ci/spec.md                     → 0
$ grep -c '"3\.10"'          openspec/specs/ci/spec.md                     → 2   (lines 223, 275)
$ grep -n 'python_version'   openspec/specs/ci/spec.md                     → 223, 274

# anchor uniqueness, one probe per planned edit (all 1 = unique)
$ A) '> Added by change `2026-09-14-chore-python-version-313` …'            → 1
$ B) '`[tool.mypy] python_version` SHALL remain `"3.10"` (it declares the minimum language/typing level,
      tied to `requires-python`, not the developer interpreter), the CI test matrix SHALL keep'          → 1
$ C) 'and the diff SHALL contain zero `pyproject.toml` paths and zero `.github/workflows/` paths.'        → 1
$ D) '- THEN `requires-python` SHALL still be `>=3.10` and `[tool.mypy] python_version`\n
      SHALL still be `"3.10"`'                                                                            → 1
$ E) '---\n\n## Test Mapping'                                                       → 1
$ F) 'mismatched binary | Verify-phase runtime evidence'                            → 1
```

Structural anchors confirmed by text (design §6.5 / §6.6 / OBS-5):

- CI-08's block ends with its `required-version rejects a mismatched binary` scenario, then the closing
  `---`, then `## Test Mapping` — the CI-09 block is inserted **between** that `---` and the heading
  (pre-write lines 362/364; post-write `### Requirement: … (CI-09)` starts at line 374).
- `## Test Mapping`'s last content row is the CI-08 `required-version rejects a mismatched binary` row
  (pre-write line 400 = EOF, file terminated by a newline) — the five CI-09 rows are appended there
  (post-write lines 526–530), with the header row and `| --- | -------- | ------------ |` delimiter row
  left untouched.
- CI-07's blockquote is one `> Added by …` line (pre-write line 217); its two `python_version` occurrences
  are the third paragraph (line 223) and the first THEN bullet of the `User-facing support is unchanged`
  scenario (lines 274–275).
- Repository conventions confirmed in place elsewhere and reused: `> Modified by …` stacked under
  `> Added by …` (`openspec/specs/repo-compliance/spec.md:681-682`, and CI-08's own blockquote), and the
  `(Previously: …)` marker (`openspec/specs/cli/spec.md:209`, `parquet-conversion/spec.md:529`,
  `tool-config/spec.md:324`). The retired value in the marker is written **backticked** per COR-5.

## Edit 1 — CI-09 (purely additive)

**Mechanics.** The 114-line CI-09 block (delta lines 43–156: requirement heading, `> Added by …` note, clause
groups Q1/Q2/S, the five scenarios, and the block's own trailing `---`) and the 5 Test Mapping rows
(delta lines 169–173) were spliced **byte-for-byte from the delta** by span index, with these assertions
evaluated before the write: exactly one `### Requirement:` line, exactly five `#### Scenario:` lines, the
block's last line is `---`, and every row starts with `| CI-09 |` and ends with `|`. No table header or
delimiter row was re-emitted; no existing row was rewritten.

**Before (canonical, around the insertion point):**

```text
    - AND this evidence is **verify-phase runtime evidence** — the commands above, pasted with
      their exit codes into the verify report (CI-01 gate-exit-code precedent)

---

## Test Mapping
```

**After (canonical, lines 368–379 / 522–530):**

```text
      their exit codes into the verify report (CI-01 gate-exit-code precedent)
      (line 371 blank)
---                                                                    (line 372: CI-08 closer, unchanged)
      (line 373 blank)
### Requirement: Type-gate posture — `tests/` excluded from both type gates and pyright adopted as a real gate (CI-09)
                                                                       (line 374)
> Added by change `2026-09-15-chore-type-gate-policy` (GitHub #201). …
…
  recorded as verify-phase runtime evidence (CI-01 gate-exit-code precedent)
      (blank)
---                                                                    (the block's OWN trailing `---`)
      (blank)
## Test Mapping
…
| CI-08 | required-version rejects a mismatched binary | Verify-phase runtime evidence — … |   (line 525)
| CI-09 | `tests/` stays out of both type gates | … |                                          (line 526)
| CI-09 | `[tool.pyright]` declares the decided posture and the gate runs | … |
| CI-09 | Exactly one pyright config home exists | … |
| CI-09 | The pin is exact, reaches CI through the lock, and matches the running binary | … |
| CI-09 | Adopting the gate leaves every existing gate declaration intact | … |                   (line 530)
```

**W2 reconciliation carried into the canonical text (as the delta already had it — no rewrite here).** The
promoted CI-09 clause group Q2 now reads: *"The **four** `tomli` fallback sites that still select the parser
behind `try:` / `except ImportError:` (`cli.py`, `config.py`, `mcp_registration.py`, `model.py`) SHALL be
resolved by the committed stub under `stubPath`; `mcp_server.py`'s fallback is version-gated
(`sys.version_info >= (3, 11)`), so a static checker prunes its `tomli` arm and it needs no stub."* The stale
"five fallback sites" wording the verify report flagged in W2 is therefore **not** promoted.

## Edit 2 — CI-07 amendment (the authorized exception, four spans only)

**Span 1 — `> Modified by …` blockquote line appended to CI-07's existing `> Added by …` (COR-4/DC-11).**

```text
before:
> Added by change `2026-09-14-chore-python-version-313` (GitHub #178). … gate exit codes.

after:
> Added by change `2026-09-14-chore-python-version-313` (GitHub #178). … gate exit codes.
>
> Modified by `2026-09-15-chore-type-gate-policy` (GitHub #201) — the `[tool.mypy] python_version` declaration
> moved to `"3.11"` by maintainer decision; the `.python-version` pin, its equality with both gate-job pins, and
> every other clause are unchanged.
```

**Span 2 — Occurrence 1, the clause inside CI-07's third paragraph, with the COR-7 join resolved.**
The stale span `` `[tool.mypy] python_version` SHALL remain `"3.10"` (it declares the minimum language/typing
level, tied to `requires-python`, not the developer interpreter), `` is replaced **in place** by the delta's
frozen sentence; the continuation then opens a **new sentence** ("The CI test matrix SHALL keep exercising
…"), so the broken `same change., the CI test matrix` join is **never shipped** (§COR-7). Every other byte of
the paragraph — the opening "`.python-version` selects the interpreter …", the `requires-python` clause, the
test-matrix/floor/diff-scope continuation — is copied verbatim.

```text
before (line 223, excerpt):
… SHALL remain `>=3.10`, `[tool.mypy] python_version` SHALL remain `"3.10"` (it declares the minimum
language/typing level, tied to `requires-python`, not the developer interpreter), the CI test matrix SHALL keep
exercising `3.10`–`3.14`, …

after (line 227, excerpt):
… SHALL remain `>=3.10`, `[tool.mypy] python_version` SHALL be `"3.11"` — the language level mypy analyses
against, declared independently of both `requires-python` (`>=3.10`, the support floor) and `.python-version`
(`3.13`, the gate interpreter). At `3.11` the `import tomllib as _tomli` arm of the interpreter-selection
fallbacks is a resolvable stdlib module for mypy, while the marker-only `tomli` arm is covered by the global
`ignore_missing_imports = true`. It SHALL NOT be read as a support declaration: `requires-python` SHALL remain
`>=3.10`. A change that moves this value SHALL amend this clause in the same change. The CI test matrix SHALL
keep exercising `3.10`–`3.14`, the TOTAL coverage floor SHALL remain the config-owned `fail_under = 90`
(CI-01), and the diff SHALL contain zero `pyproject.toml` paths and zero `.github/workflows/` paths.
```

*Wrapping note (transparency, not a content change):* the canonical paragraph is a single unwrapped line, so
the frozen sentence is inserted as one line inside it; the delta wraps the same words over six lines. The
**words are byte-identical**; only soft line breaks differ, and a mid-paragraph hard wrap would have split one
canonical paragraph into seven lines. The `(Previously: …)` marker and the `> Modified by …` blockquote keep
the delta's own line breaks exactly.

**Span 3 — Occurrence 1b, the `(Previously: …)` marker paragraph, appended immediately after the third
paragraph (COR-5: the retired value is BACKTICKED, never a double-quoted literal).**

```text
(Previously: this clause required `[tool.mypy] python_version` to remain `3.10` and described it as the
minimum language level tied to `requires-python`; the maintainer declared `"3.11"` as the analysis level and
change `2026-09-15-chore-type-gate-policy` (GitHub #201) amends the clause to match the committed
configuration.)
```

**Span 4 — Occurrence 2, the first THEN bullet of the `User-facing support is unchanged` scenario.**

```text
before:                                                      after:
- THEN `requires-python` SHALL still be `>=3.10` and          - THEN `requires-python` SHALL still be `>=3.10` and
  `[tool.mypy] python_version`                                 `[tool.mypy] python_version`
  SHALL still be `"3.10"`                                       SHALL be `"3.11"` — the declared analysis level, amended by change
                                                                `2026-09-15-chore-type-gate-policy` (GitHub #201) to match the committed configuration
```

**Deliberately untouched inside CI-07 (verified byte-level):** the `.python-version` = `3.13` clause and its
equality with both gate-job pins (`\`.python-version\` SHALL contain exactly \`3.13\`` still present); the
"flag-free mypy gates are green on the pinned interpreter" paragraph; the COV-06-script paragraph; the
AGENTS-rule-12 latent-issue paragraph; the four other scenario bullets; and CI-07's Test Mapping row (no new
CI-07 row was added — the existing `User-facing support is unchanged | Verify-phase static evidence …` row is
re-satisfied).

**Everything else in the canonical capability is byte-identical:** CI-01…CI-06, CI-08 (clauses, scenarios and
rows), the `## Purpose` enumeration (still listing CI-01…CI-06 only — the CI-07/CI-08 precedent), the
`## Test Mapping` intro prose and all 26 pre-existing rows. Because the delta is a pure append plus exactly
the four CI-07 spans, no `ADDED`/`MODIFIED`/`REMOVED` requirement in the delta failed to match its canonical
counterpart, and no canonical requirement was deleted.

## Self-checks (actual output)

```text
$ wc -l openspec/specs/ci/spec.md                        → 530   (was 400; +130 content lines = 120 CI-09 + 10 CI-07)
$ grep -c '^### Requirement:' openspec/specs/ci/spec.md → 9     (was 8; the +1 is CI-09)
$ grep -c '^#### Scenario:'  openspec/specs/ci/spec.md → 31     (was 26; the +5 are CI-09's scenarios)
$ grep -c '^| CI-09 |'       openspec/specs/ci/spec.md → 5
$ grep -c '"3\.10"'          openspec/specs/ci/spec.md → 0     (REQUIRED: 0 — the retired double-quoted literal is gone)
$ grep -c '3\.10'            openspec/specs/ci/spec.md → 8     (all BACKTICKED prose: marker, `.python-version`
                                                               rationale, `requires-python` floor, test matrix — expected)
$ grep -n 'python_version'   openspec/specs/ci/spec.md → 219 (blockquote), 227 (clause, now `"3.11"`),
                                                         229 (marker), 283 (scenario bullet)
$ grep -n 'CI-09'            openspec/specs/ci/spec.md → 374 (requirement), 526–530 (the five rows)

# diff scope (this phase wrote exactly one file)
$ git diff --name-only -- openspec/                → openspec/specs/ci/spec.md
$ git diff --stat -- openspec/specs/               → openspec/specs/ci/spec.md | 134 +++…-  (132 insertions, 2 deletions)
$ git status --porcelain | grep '^??'              → openspec/changes/2026-09-15-chore-type-gate-policy/ , typings/
$ git diff --name-only        → the 17 apply-touched paths + openspec/specs/ci/spec.md
                                 (identical set to the pre-sync listing; the ONLY newly changed path is the canonical spec)

# byte-identity of the promoted blocks
CI-09 block byte-identity (canonical == delta): True
  sha256 canonical block: 0606ae987d3b96e21cc4aa9f17eff631a14d80c318ceeb039a3339de19fe7fd5
  sha256 delta     block: 0606ae987d3b96e21cc4aa9f17eff631a14d80c318ceeb039a3339de19fe7fd5
CI-09 rows  byte-identity (canonical endswith delta rows): True
  rows sha256: 606d8dad76b60e39d07290ecaadd668458dc7cd47a333ac6293f0ffbee5824e3

# CI-07 span checks inside the canonical CI-07 block
CI-07 block: "3.11" count = 4 | "3.10" count = 0 | backticked `3.10` = 8
CI-07 block still names 3.13: True | `.python-version` SHALL contain exactly `3.13` intact: True
COR-7 join ok ('in the same change. The CI test matrix SHALL keep exercising'): True
no broken join ('same change.,'): True
```

Canonical insertion structure (programmatic, `split("\n")`):

```text
371 ''        372 '---' (CI-08 closer)        373 ''
374 '### Requirement: Type-gate posture — `tests/` excluded from both type gates and pyright adopted as a real gate (CI-09)'
…
525 '| CI-08 | required-version rejects a mismatched binary | … |'
526–530 the five '| CI-09 |' rows (EOF)
```

## G7 before / after — the closing evidence verify deferred

| State | Command | Output |
| --- | --- | --- |
| **Before sync** (canonical CI-07 read `"3.10"`; recorded in `verify-report.md`) | `uv run pytest tests/test_ci_workflows.py -q` | `1 failed, 29 passed in 0.39s` (exit 1) — `AssertionError: CI-07 must name the declared [tool.mypy] python_version (3.11): the committed configuration and the canonical clause cannot diverge (issue #201)` at `tests/test_ci_workflows.py:780` |
| **Before sync**, full suite (`rules.verify.test_command`) | `uv run pytest tests/ -q` | `1 failed, 1791 passed, 6 skipped, 1 warning in 59.39s` (exit 1) — the single failure was G7 |
| **After sync** — module | `uv run pytest tests/test_ci_workflows.py -q` | **`30 passed in 0.24s`** (exit 0) |
| **After sync** — G7 targeted | `uv run pytest tests/test_ci_workflows.py -q -k test_ci07_names_the_declared_mypy_language_level` | **`1 passed, 29 deselected in 0.04s`** |
| **After sync** — full suite | `uv run pytest tests/ -q` | **`1792 passed, 6 skipped, 1 warning in 61.04s`** (exit 0) |

The module tally moved `29 passed + 1 failed` → `30 passed` with no `--deselect`, no mark and no test
weakened: G7 flipped because the canonical clause now names the value `pyproject.toml` declares
(`python_version = "3.11"`), which is exactly the divergence class the guard exists to catch. `1791 passed`
before (with one failure) → `1792 passed` after is the same 1798 collected tests, all green. The
`1 warning` is the pre-existing `runpy` `RuntimeWarning` in `tests/test_cli.py` (unchanged by this change).

**No other test was touched by this phase:** `git diff --name-only` shows no `tests/` path changed by sync
(`tests/test_ci_workflows.py` was already modified by apply, not by this phase), and the canonical spec is not
imported by any test.

## Remaining risks / parent-owned items

1. **W1 / W3 (blueprint divergence, missing SC-4c probe)** — still open from verify: the shipped `src/`
   resolutions at `_converters.py` / `mcp_server.py` do not match design §5.2's frozen form, and task 3.9's
   sensitivity probe has no pasted evidence. **Not a sync blocker** (both gates are green: `uv run mypy src/
   scripts/` exit 0, `uv run pyright` exit 0), but the archive phase's "design coherence" check will see it;
   the verify report recommends a `COR-8`-style adjudication in `apply-progress.md` §4 or an amendment to
   design §5.2. This phase deliberately did **not** author that entry (it owns the canonical spec only).
2. **W5 (delivery budget)** — the delivered diff exceeds the 400-line canonical threshold and the 1500-line
   session budget once `uv.lock` is counted; no `ask-on-risk` pause and no `size:exception` were recorded. The
   live status's `blockedReasons` entry (apply attempt / changed-line budget, `maintainer_decision`) points at
   the same accounting. Parent-owned, pre-PR decision — this phase records it and does not decide it.
3. **W4 / I1 / I2 / I3** — evidence-fidelity and informational notes from verify; unchanged by sync.
4. **R12 (CI-07's diff-scope clause)** — recorded, not silently reinterpreted: the clause's bytes stay
   identical and the delta's `## Cross-referenced and deliberately untouched` scope note (which this sync did
   **not** promote into the canonical file, since it is delta framing) carries the reading.

## Next recommended

`sdd-archive` — verify is clean (`pass_with_warnings`, 0 blockers), the canonical spec is synced, tasks are
50/50, and G7 is green. Archive is expected to remain gated only on the parent-side items above (W1/W3
adjudication recommended, W5 delivery decision) and on the live status's `maintainer_decision` blocked reason
for the `apply` attempt/line budget. This phase did **not** archive, move, commit or push anything.
