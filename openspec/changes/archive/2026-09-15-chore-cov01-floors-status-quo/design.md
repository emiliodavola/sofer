# Design: chore-cov01-floors-status-quo

**Change**: `2026-09-15-chore-cov01-floors-status-quo` · **Issue**: #215 · **Branch**:
`chore/215-cov01-floors-status-quo` · **Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram
mirrors it at `sdd/2026-09-15-chore-cov01-floors-status-quo/design` (type `architecture`)
**Phase**: design (wording fixture) · **Source of truth**: `proposal.md` in this change root — every product
decision below is the proposal's, restated as byte-exact text, not re-opened
**Inputs read this phase**: `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/proposal.md` (full) ·
`openspec/specs/coverage/spec.md` (full, with grep-derived line anchors) · `AGENTS.md:94-128` ·
`tests/test_ci_workflows.py:232-345` · `tests/test_coverage_contract.py:1-45` ·
`openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md` (delta shape
precedent) · `scripts/check_core_coverage.sh` · `.github/workflows/ci.yml` · `.github/workflows/release.yml` ·
`pyproject.toml:94-103` · `.pre-commit-config.yaml`
**Product size**: delta ≈78 lines + `AGENTS.md` **1** added line · **0** lines in `src/`, `tests/`,
`scripts/`, `.github/workflows/`, `pyproject.toml` — **single PR**, `auto-chain` needs no pause

> **Size reconciliation (recorded, not hidden).** The proposal estimated ≈47 changed lines; the byte-exact
> fixture below renders to ≈78 delta lines + 1 `AGENTS.md` line. The overage is markdown wrapping at the
> file's ~90-column prose width (COV-06's own body is 30 lines for fewer clauses) plus the
> first-of-its-kind sync-mechanics note. Content is exactly the proposal's; nothing was added to the
> deliverable. Against the 1500-line review budget this is immaterial and **no delivery decision changes**
> — no chaining, no `ask-on-risk`, no `size:exception`.

---

## Decision summary (design-level only; D1–D2 are the proposal's confirmed user decisions)

| ID | Decision | Origin | Consequence for the fixture |
| --- | --- | --- | --- |
| **D1** | Option (b) for #215: keep the status quo, record it as deliberate. No gate, no test, no workflow, no number | proposal (user-confirmed) | The whole artifact is a record; the scenario's only evidence class is verify-phase static |
| **D2** | Durable home = new additive **COV-07** + exactly **one** added `AGENTS.md` bullet near rule 14; rule 14's text is not reworded | proposal (user-confirmed) | Two artifacts, one commit; § *Insertion-point mechanics* and § *Guard analysis* fix the mechanics |
| **D3** | Exactly **one** scenario, and it is an **absence inventory**, not a restatement of COV-06-S1 | proposal *Carrier 1b* | Scenario body asserts roster + literal + threshold absence, plus the three modules' absence from every gated surface |
| **D4** | The "ban is scoped, not airtight" nuance is **one clause in canonical text**; the phrase "is impossible to arm" appears nowhere | proposal §8 Q3 → clause 3 | Requirement paragraph 2 carries the caveat explicitly |
| **D5** | **COV-07's requirement body states no coverage value for the three floors.** It names the modules and defers the value to COV-01 ("the value COV-01 declares") | **design-level refinement** — resolves a conflict inside the proposal: *Carrier 1* clause 1 renders the floors as "`profile.py` ≥90, …" while clause 5 forbids restating a coverage value and success criterion 2 says COV-07 "contains no coverage figure" | Clause 5 wins: the fixture omits `≥90`. The only threshold literals in the whole delta are `100` and `fail_under = 90`, both quoted from **other** requirements (COV-06-S1's boundary, COV-02/CI-01's scalar) as the definition of the boundary — never as a claim about the three floors |
| **D6** | The `AGENTS.md` bullet is **one logical bullet on one physical line** | **design-level refinement** of proposal success criterion 4 ("exactly one added line … zero deleted lines") | `git diff -U0 -- AGENTS.md` = 1 added line, 0 deletions, exactly as SC4 asserts. Precedented in-file: `AGENTS.md:68`, `:70`, `:79`, `:84`, `:89` are 150–400-char single-line bullets. **Rejected variant**: 2-space-wrapped continuation (4 added lines) — it matches rule 14's local wrapping but weakens SC4's literal diff assertion for a cosmetic gain; semantics and the guard are identical either way |
| **D7** | The delta's `## Test Mapping` carries only the row + a sync instruction, not a copy of the section's prose | design (mechanics) | Sync must append a row to an **existing** table (first of its kind) without rewriting the canonical prose at `spec.md:285-304` |
| **D8** | No per-requirement `> Added by change …` provenance line above COV-07 | design (local style) | COV-01..COV-06 carry none; PB-14's line is `process-boundary`'s local convention, not this capability's. Provenance lives in the delta header blockquote |

---

## Artifact A — the delta, verbatim

Target path: `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` (**new file**).
The apply phase copies this block byte-for-byte (outside the fence, at column 0).

```markdown
# Delta for coverage

> **Change** `2026-09-15-chore-cov01-floors-status-quo` (issue #215) · branch
> `chore/215-cov01-floors-status-quo` · store **hybrid** (Engram mirror topic key
> `sdd/2026-09-15-chore-cov01-floors-status-quo/spec`).
>
> **Capability `coverage`, justified.** The recorded invariant is the enforcement posture of the three
> COV-01 floors, and this capability already owns that object: COV-01 declares the floors, COV-03/COV-06
> own the gate machinery, and COV-04 already demonstrates the recorded-not-enforced shape in this same
> file. The alternative home, `ci` CI-01, was considered and rejected: CI-01 owns the config-declared
> TOTAL floor and this change arms no CI step, so a `ci` requirement about un-gated per-file floors would
> be misfiled. `ci` is cross-referenced only, never modified.
>
> **Additive, not destructive.** COV-01..COV-06 keep their clauses, scenarios and earned verify evidence
> byte-for-byte, so archive-time replacement of a canonical block would be a lossy no-op; the clause
> enters as **new** requirement **COV-07** — the next free ID in this capability, whose canonical file
> ends at COV-06.
>
> **Sync mechanics (first of their kind in this repository).** This is the first requirement whose Test
> Mapping row is **appended to an existing table** rather than creating the section. Sync therefore
> (a) inserts the COV-07 block — requirement, scenario, and its own trailing `---` separator — between the
> `---` that closes COV-06 (`openspec/specs/coverage/spec.md:281`) and the `## Test Mapping` heading
> (`:283`), so no doubled separator is produced, and (b) appends the single row at the **end of the
> existing table**, immediately after the COV-06 TOTAL row (`:324`, the file's last content line). Sync
> edits nothing else: the `## Test Mapping` intro prose and every existing row stay byte-identical, and
> the `## Purpose` enumeration is deliberately left stale (the CI-07/CI-08 precedent — it already omits
> COV-04).

## ADDED Requirements

### Requirement: Second-tier per-file floors are deliberately verify-phase-only (COV-07)

The three COV-01 floors — `src/sofer/profile.py`, `src/sofer/mcp_registration.py`,
and `src/sofer/verification.py` — SHALL remain **verify-phase-evidenced only**: no
CI step, workflow, committed gate script, or `pyproject.toml` key SHALL enforce
them, and this requirement arms none. The posture is deliberate, not an oversight,
for three in-repo reasons: (a) coverage.py cannot express a per-file floor in
config — `[tool.coverage.report] fail_under` is a single scalar owned by the TOTAL
gate (CI-01 / COV-02); (b) the only executable in-repo ≥90 check,
`tests/test_coverage_contract.py`, skips when no local `.coverage` data file is
present, which is exactly the state the CI coverage job collects in, and COV-01-S3
declares that skip intended; and (c) the CLI-core 100% mandate (COV-06) already
consumes the repository's per-file gate machinery, and its S1 floor-literal ban is
the boundary this repository chose.

The enforcement boundary SHALL be that COV-06-S1 ban, scoped to the surfaces it
actually covers: `scripts/check_core_coverage.sh`, whose module roster is exactly
`cli scanner prepare publish`, and the raw text of `.github/workflows/ci.yml` and
`.github/workflows/release.yml`, pinned by
`tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and
`::test_coverage_gate_is_config_driven_without_cli_floor`. That boundary SHALL NOT
be read as a fence around the whole repository: a new gate script or workflow step
carrying a floor other than 100 would turn no existing test red, so what makes such
a move illegitimate is this requirement, not the ban alone.

Arming any gate for the three floors — a non-100 scoped invocation, a new gate
script, a per-file config key, or a workflow step — SHALL be its own SDD change,
and that change SHALL amend this requirement together with COV-06 and COV-03 and
the two ban-pinning guards named above, in the same change. This requirement SHALL
NOT restate, lower, raise, re-measure, or promise a coverage value, and SHALL NOT
be read as authorizing any of those floors to drift below the value COV-01
declares: the floors' values and their verify-phase evidence class stay exactly as
COV-01 declares them, and the TOTAL gate stays config-owned at 90 (COV-02 / `ci`
CI-01).

This requirement is additive: COV-01..COV-06 SHALL keep their clauses, scenarios,
and earned verify evidence unchanged, and this requirement SHALL NOT be read as
substituting for COV-01 (the floors still bind as declared) nor as weakening
COV-06, which owns the four-module mandate.

#### Scenario: No gate is armed for the three second-tier floors

- GIVEN the enforcement surfaces as committed by this change — `scripts/check_core_coverage.sh`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `pyproject.toml`'s `[tool.coverage.report]`
- WHEN they are inspected at verify time
- THEN the gate script's module roster SHALL still be exactly the four CLI-core modules, no `--fail-under` value other than 100 SHALL appear in the script or in either workflow (the COV-06-S1 boundary), and the only coverage threshold in `pyproject.toml` SHALL still be the scalar TOTAL `fail_under = 90` (CI-01 / COV-02)
- AND `profile.py`, `mcp_registration.py`, and `verification.py` SHALL appear in no gated invocation and no CI step SHALL enforce a per-file floor for any of them — they stay COV-01 verify-phase evidence
- AND this SHALL remain **verify-phase static evidence** recorded in the verify report: this requirement adds no test, and the two ban-pinning guards SHALL stay green **unmodified** — they keep the existing surfaces closed and do not make the ban airtight (the scoping paragraph above is the record)

---

## Test Mapping

Sync appends the single row below to the **end of the existing table** in
`openspec/specs/coverage/spec.md`, immediately after the COV-06 TOTAL row. The
section's existing intro prose and every existing row are untouched by this
change; this row is a verify-phase **static-evidence** row by construction,
because this change adds no test.

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| COV-07 | No gate is armed for the three second-tier floors | Verify-phase **static evidence** — read of `scripts/check_core_coverage.sh` (roster = the four CLI-core modules; every `--fail-under` literal is 100), `.github/workflows/ci.yml` and `.github/workflows/release.yml` (no `--fail-under`/`fail-under`/`fail_under`), and `pyproject.toml`'s `[tool.coverage.report]` (scalar `fail_under = 90` only), pasted into the verify report; the two guards `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and `::test_coverage_gate_is_config_driven_without_cli_floor` stay green **unmodified** — this requirement adds no test |

---

## Cross-referenced and deliberately untouched

- `coverage` COV-01..COV-06 — no clause, scenario, floor value, evidence class, or requirement ID is
  edited, renumbered, retired, or re-scoped by this delta. COV-07 is additive: it does not substitute for
  COV-01 and does not weaken COV-06.
- `coverage` COV-02 / `ci` CI-01 — the config-owned TOTAL gate stays exactly where it is
  (`[tool.coverage.report]` `fail_under = 90`, next to `show_missing = true`). COV-07 declares no
  threshold and adds no config key.
- `coverage` COV-06-S1 — the non-100 `--fail-under` ban over `scripts/check_core_coverage.sh` and the raw
  text of both workflows is the boundary this requirement records, scoping caveat included. Neither the
  ban nor the two guards pinning it is edited here.
- `process-boundary` PB-05 — the complete-suite invariant every coverage figure is taken over. The COV-07
  scenario reads committed surfaces only and runs no measurement.
- Issue **#185** — owns the release/CI asymmetry (`release.yml`'s coverage job runs the TOTAL report step
  and no core gate script). COV-07 asserts nothing about it and closes nothing.

**Non-goals recorded by this delta:** no gate is armed for the three floors (no non-100 scoped invocation,
no new script, no config key, no workflow step); no `src/sofer/**`, `tests/**`, `scripts/**`,
`.github/workflows/**`, `pyproject.toml`, or `uv.lock` line; no change to `tests/test_coverage_contract.py`
or its skip semantics; no new coverage figure, re-measurement, or margin promise; no rewording of
`AGENTS.md` rule 14 (the pointer is a separate additive bullet in this change); no edit of the
`## Purpose` enumeration (left stale deliberately, CI-07/CI-08 precedent); no `CONTRIBUTING.md` update; no
canonical `openspec/specs/**` edit before `sdd-sync`; no commit, push, or PR.
```

**Style check against the neighbors** (`openspec/specs/coverage/spec.md`): COV-07 uses the file's heading
shape (`### Requirement: <title> (COV-0N)`, then `#### Scenario: <title>`, then `- GIVEN` / `- WHEN` /
`- THEN` / `- AND` bullets), its SHALL-per-clause prose register, and its cross-requirement citation style
(bare `COV-0N-Sx`, `CI-01`, `PB-05`). Paragraph 2 deliberately echoes COV-04's "recorded, not enforced"
posture and COV-06-S1's exact phrasing ("no `--fail-under` value other than 100 SHALL appear in the
workflow or script", `spec.md:246-250`) so the boundary is recognizably the same one. The scenario's `- AND
… verify-phase static evidence` closing bullet mirrors the `- AND` evidence-class bullets other coverage
scenarios use for non-pytest evidence.

---

## Artifact B — the `AGENTS.md` bullet, verbatim

Append as a **new final bullet of rule 14's list**, immediately after `AGENTS.md:127` (the line
`  floor.`, which closes the bullet starting at `:125`), inside the file's last rule (no `### 15.` exists).
**One physical line; nothing else in `AGENTS.md` changes.**

```markdown
- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
```

Properties (all deliberate, tested in § *Guard analysis*):

- **Additive only** — zero deletions, zero reordering; rule 14's existing sentences are byte-identical
  before and after (proposal SC4).
- **No second mandate** — the leading clause marks it an adjacent-policy pointer, and it names the three
  modules without asserting a mandate over them; rule 14 continues to cover exactly the four core modules.
- **It carries the payload** — the three module names, the word "not CI-gated", and the COV-07 pointer, so
  an agent that never opens `openspec/specs/` still cannot infer that a gate exists (proposal Q1).
- **One physical line** — satisfies SC4's `git diff -U0` assertion literally; see D6 for the rejected
  wrapped variant and the in-file single-line precedent.

---

## Insertion-point mechanics (anchors the sync phase will use)

All anchors were read from the working tree at design time via `grep` (file:line, authoritative). Sync must
**re-verify them before editing** — the numbers shift if any other change lands on the capability first.

### Step 1 — insert the COV-07 block into `openspec/specs/coverage/spec.md`

Current shape of the seam (grep-confirmed):

```text
:275  #### Scenario: TOTAL stays config-owned at 90
:276  (blank)
:277  - GIVEN pyproject.toml parsed with tomllib
:278  - WHEN the [tool.coverage.report] table is inspected …
:279  - THEN fail_under SHALL equal 90 … (COV-06's last scenario body)
:280  (blank)
:281  ---
:282  (blank)
:283  ## Test Mapping
```

**Insertion rule**: paste the Artifact A block from `### Requirement: Second-tier per-file floors …`
through its trailing `---` **between `:281` and `:283`** — i.e. after the `---` that closes COV-06 and
before the `## Test Mapping` heading — preserving exactly one blank line on each side of the inserted block.
COV-06's own `:281` `---` becomes the separator *before* COV-07; COV-07's trailing `---` is the separator
*before* `## Test Mapping`. This is why the block must carry its own trailing separator: inserting it
*before* `:281` instead would leave two adjacent `---` lines.

**Forbidden**: placing COV-07 after the `## Test Mapping` heading (a requirement stranded below the index
breaks the file's section order); dropping COV-07's trailing `---`; touching `:1-280`; touching the
`## Purpose` paragraph (`:5-29`, deliberately left stale — it already omits COV-04).

### Step 2 — append the row to the existing table

Table geometry: header at `:306`, delimiter row at `:307`, 17 data rows `:308-324`, and `:324` (the COV-06
TOTAL row) is the **final content line of the file**.

**Insertion rule**: append the single row from Artifact A's `## Test Mapping` as a new line immediately
after the current `:324`. The `| Req | Scenario | Verification |` header and the
`| --- | -------- | ------------ |` delimiter row are **not** re-emitted; the canonical `## Test Mapping`
intro prose (`:285-304`) and rows `:308-324` are **not** edited.

### Step 3 — nothing else

`AGENTS.md` gains its one bullet in the same commit (apply phase), not at sync. Sync edits no other file,
and `sdd-sync` is the only phase allowed to touch `openspec/specs/**`.

---

## Guard analysis — why the added bullet cannot break an existing test

Read directly from `tests/test_ci_workflows.py:266-277`:

```python
def test_agents_md_declares_core_100_mandate() -> None:
    rule14 = re.search(r"### 14\..*?(?=\n### 15\.|\Z)", _read_text("AGENTS.md"), re.DOTALL)
    assert rule14 is not None, "AGENTS.md rule 14 not found"
    text = rule14.group(0)
    for module in ("cli.py", "scanner.py", "prepare.py", "publish.py"):
        assert module in text
    assert "100.00%" in text
    assert re.search(r"#\s*pragma:\s*no\s*cover", text, re.IGNORECASE) is not None
```

| Question | Finding |
| --- | --- |
| Does the bullet land inside the regex-captured region? | **Yes** — rule 14 is the file's last rule (no `### 15.`), so `\Z` terminates the capture after the new bullet. This is the proposal's recorded, pre-verified fact. |
| Can added text break it? | **No** — all three assertions are *presence* assertions over the captured text (`cli.py`/`scanner.py`/`prepare.py`/`publish.py`; `100.00%`; the pragma token). Addition can only add matches, never remove them. The bullet contains none of `### 15.` and does not delete any rule-14 sentence (D2 / D6). |
| Does the bullet risk a *false* pass? | No — it introduces no `100.00%` string, no pragma token, and no `### 15.` heading, so it cannot mask a future removal elsewhere in the rule. |
| Does any other test read `AGENTS.md` or the coverage spec? | **No** — `grep AGENTS\.md tests/` reaches only `:269` (plus docstrings); zero matches for `COV-0\d` / `specs/coverage` under `tests/`. Adding a delta file under `openspec/changes/` is likewise unobserved: the only `openspec/` reads are `openspec/config.yaml` (gitignored, skip-guarded) and a `paths-ignore` membership check. |
| Do the two ban guards need to change? | **No** — they read `scripts/check_core_coverage.sh`, `ci.yml`, `release.yml`. None is edited by this change, and the new delta file is not read by any test. `test_coverage_job_gates_core_modules_at_100` stays green **unmodified** (roster + `--fail-under=100` untouched); `test_coverage_gate_is_config_driven_without_cli_floor` stays green **unmodified** (`fail-under`/`fail_under` absent from both workflows, verified: zero matches). |

**Conclusion**: **no test change is required or permitted** (proposal non-goal 2). If this analysis is ever
falsified at verify time, the correct response is to shorten the bullet — never to edit a guard.

---

## File-change plan (apply phase)

| # | Path | Action | Lines | Notes |
| --- | --- | --- | --- | --- |
| **A1** | `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` | **create** (new dir `specs/coverage/`) | ≈78 | Artifact A, byte-for-byte |
| **A2** | `AGENTS.md` | **edit** — append 1 bullet after line 127 | +1 / −0 | Artifact B, byte-for-byte; rule 14 body untouched |
| *(sync)* | `openspec/specs/coverage/spec.md` | insert block between `:281` and `:283`; append row after `:324` | +≈40 | **`sdd-sync` only** — not the apply phase |

**One commit for A1+A2** (one reviewable work unit): the pointer is meaningless without the requirement it
points at, so they must never land in separate commits (proposal § *Delivery*). Order inside the work unit:
A1 first, A2 second.

Zero paths in: `src/sofer/**`, `tests/**`, `scripts/**`, `.github/workflows/**`, `pyproject.toml`,
`uv.lock`, `CONTRIBUTING.md`, `README*.md`, `.pre-commit-config.yaml`.

---

## Verification and evidence plan

Nothing here is a new test: every item is a read-only inspection pasted into the verify report, exactly the
class COV-01's floors and COV-04's retirement already use.

### E1 — COV-07's scenario: the absence inventory (the load-bearing evidence)

```bash
# a) the gate script's roster and its only floor literal
git grep -nE "for f in |fail-under" -- scripts/check_core_coverage.sh

# b) every --fail-under literal in the gate script and both workflows is 100
git grep -n -- "--fail-under=" -- scripts/ .github/workflows/

# c) no config-key or dash spelling of the total floor in either workflow
git grep -n -e "fail_under" -e "fail-under" -- .github/workflows/     # expect: zero matches

# d) the three floor modules appear in NO gated invocation and no CI step
git grep -nE "profile\.py|mcp_registration\.py|verification\.py" -- scripts/ .github/workflows/   # expect: zero matches

# e) the only coverage threshold in pyproject.toml is the scalar TOTAL floor
git grep -n -A3 "\[tool.coverage.report\]" -- pyproject.toml

# f) the gate script is referenced by the ci.yml coverage job (and, per #185, not by release.yml)
git grep -n "check_core_coverage.sh" -- .github/workflows/
```

Expected: (a) `for f in cli scanner prepare publish` + one `--fail-under=100` line; (b) only `:100`
literals; (c) zero matches; (d) zero matches; (e) `show_missing = true` + `fail_under = 90` and nothing
else; (f) `ci.yml` only. Command names, not pasted output, are fixed here — the verify phase pastes the
actual output (AGENTS.md rule 11).

### E2 — the record is present in both carriers

```bash
git grep -n "COV-07" -- openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md AGENTS.md
uv run pytest tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate -q
```

Expected: the delta's requirement heading + its one mapping row; the `AGENTS.md` bullet naming
`profile.py`/`mcp_registration.py`/`verification.py` and COV-07; the guard green (green **before** the
bullet too — the bullet is additive).

### E3 — the guards stay green unmodified, and no test moved

```bash
uv run pytest tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100 \
             tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor \
             tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90 -q
git diff --stat -- tests/          # expect: empty
uv run pytest tests/ -q            # tally re-derived, unchanged (no test added, none newly skipped)
```

The full-suite run is **not** a coverage measurement and needs no `.coverage` file; the contract test keeps
its documented skip. The tally is re-derived on this branch and reported as measured — the proposal's
`1766 passed, 6 skipped` is context only, never restated as a promise (AGENTS.md rule 6).

### E4 — diff scope (the "no code change" acceptance criterion)

```bash
git diff --stat origin/dev
git diff --name-only origin/dev -- src/ tests/ scripts/ .github/ pyproject.toml uv.lock   # expect: empty
git diff -U0 -- AGENTS.md                                                                  # expect: +1 / -0
```

Expected `--stat` roster: `AGENTS.md`, the change's delta, and the change's phase artifacts — nothing else.

### Non-verification (out of scope by construction)

No gate is run for the three floors (none exists — that is the recorded fact); no coverage figure is
measured, promised, or compared; no CI run is required beyond the PR's normal gates.

---

## Rollback

**One commit, two files, one command.** `git revert <commit>` (or `git reset` before the push) deletes the
delta file and removes the `AGENTS.md` bullet. Because the canonical `openspec/specs/coverage/spec.md` is
not edited until `sdd-sync`, a pre-sync revert restores **every canonical spec byte-for-byte** — the
strongest reversibility available, and the concrete advantage the proposal recorded for the
new-requirement-over-amendment choice.

- A1+A2 landing in one commit makes the revert atomic: no state exists where the `AGENTS.md` bullet points
  at a COV-07 that no longer exists, or vice versa.
- No runtime behaviour, no test, no workflow, no gate script, no `pyproject.toml` key, no dependency, no
  lockfile, no published artefact, no version move — so nothing else can be left half-reverted.
- Post-revert state: "three floors declared, nothing enforcing them, nothing saying so", issue #215 still
  open, and this change's explore/proposal/design records still valid.
- The `sdd-sync` step is separable and reversible in the same way: reverting the sync commit removes COV-07
  and the row from the canonical file, touching nothing else in it.

---

## Risks (narrowed from the proposal; only design-phase deltas listed)

| Risk | Severity | Why it survives into implementation | Handling |
| --- | --- | --- | --- |
| **D5's omission of `≥90` is read as an oversight** rather than as clause 5's requirement | Medium | A reviewer skimming clause 1's intent sees a missing floor value | D5 and the requirement's own sentence ("SHALL NOT restate … a coverage value") state it; verify evidence for SC2 is the check that the only threshold literals in the delta are `100` and `fail_under = 90` |
| **The delta's ≈78 lines exceed the proposal's ≈47 estimate** and are mistaken for scope creep | Low–Medium | The estimate is in the proposal's changed-lines table | Size reconciliation block above; content is byte-equal to the proposal's carrier lists, and the 1500-line budget is untouched |
| **A wrapped `AGENTS.md` bullet is expected** (rule 14's local style) and D6's single line surprises review | Low | Rule 14's own bullets wrap at ~88 columns | D6 records the rejected variant, its cost (4 added lines vs SC4's literal "one added line"), and the in-file single-line precedent at `:68/:70/:79/:84/:89`; the guard is indifferent either way |
| **Sync inserts before the `---` instead of after it**, yielding doubled separators | Low but silent | The two anchors are one line apart | The mechanics section states the rule twice (insert *after* `:281`, *before* `:283`, block carries its own trailing `---`) and names the failure mode explicitly |
| **Sync re-emits the table header/delimiter** while appending the row | Low | Copying the delta's `## Test Mapping` fence wholesale is tempting | Step 2 says explicitly: append one line after `:324`; the header, delimiter, intro prose, and rows `:308-324` are not edited |
| **Anchors drift** because another change touches the capability before sync | Low | Line numbers are not stable identifiers | The mechanics section requires re-verification at sync time and gives the surrounding text of each anchor, not only the numbers |
| **Someone "improves" the ban while here** (e.g. fencing new scripts) | Low | The scoping caveat makes the gap visible and tempting | Out-of-scope rows in the proposal and in the delta's non-goals; E4's zero-path diff assertion catches it mechanically |

Proposal risks R1–R9 remain as written; the fixture above implements their stated mitigations (clause 3 for
R2, clause 5 for R3, the adjacent-pointer framing for R4, the guard analysis for R5, the two-step sync
mechanics for R6, E4 for the scope-creep rows).

---

## Open items handed forward

1. **Issue #215's full AC list** is still unread (no `gh` in this runtime); the proposal's parent-relayed
   AC1–AC3 transcription is what apply/verify trace. Extend the traceability table before verify if the
   issue carries more.
2. **Delta/sync line numbers are design-time snapshots.** `sdd-sync` re-verifies `:281`, `:283`, `:306`,
   `:307`, `:324` before editing; the design's content is anchor-independent.
3. **The `## Purpose` enumeration stays stale** (COV-04 already omitted, COV-07 will be too) — deliberate,
   the CI-07/CI-08 precedent; owned by whoever fixes the COV-04 gap, not by this change.
4. **No task file exists yet.** `tasks.md` is the next phase's artifact; derive it from the file-change plan
   (A1 → A2 → one commit → verify evidence E1–E4), not from this design's section order.
