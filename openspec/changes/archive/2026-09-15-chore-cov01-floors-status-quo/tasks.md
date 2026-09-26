# Tasks: chore-cov01-floors-status-quo

**Change**: `2026-09-15-chore-cov01-floors-status-quo` · **Issue**: #215 · **Branch**:
`chore/215-cov01-floors-status-quo` · **Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram
mirrors it at `sdd/2026-09-15-chore-cov01-floors-status-quo/tasks` (type `decision`)
**Phase**: tasks · **Source of truth**: `design.md` (Artifact A = the delta verbatim; Artifact B = the
`AGENTS.md` bullet verbatim; § *Insertion-point mechanics*, § *Guard analysis*, § *Verification and evidence
plan* E1–E4, § *Rollback*); `proposal.md` for the decisions record
**Inputs read this phase**: `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/design.md` (full) ·
`proposal.md` (full) · `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md`
(delta-format precedent) · `openspec/specs/coverage/spec.md:270-330` · `AGENTS.md:101-128` ·
`tests/test_coverage_contract.py:1-45` · `openspec/config.yaml` · `CONTRIBUTING.md:85-89` (conventional commits)
**Product size**: ≈79 changed lines (≈78 delta + 1 `AGENTS.md` line) · **0** lines in `src/`, `tests/`,
`scripts/`, `.github/workflows/`, `pyproject.toml`, `uv.lock`

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ≈79 product lines (≈78 delta + 1 `AGENTS.md`); ≈80–110 with the usual drift |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR — A1 + A2 in **one** commit, A3 = that commit + E1–E4 evidence |
| Delivery strategy | auto-chain (session preference) — no chain trigger fires; the change ships as a single PR |
| Chain strategy | pending (chaining is not selected; never used) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**Budget reconciliation.** 79 product lines against the 400-line canonical threshold and the 1500-line session
review budget: 19× and 5 % of budget respectively. Even if the reviewer counts this cycle's phase artifacts
(`explore.md`, `proposal.md`, `design.md`, this `tasks.md`, plus the verify report — ≈200–400 lines of prose),
the total stays far inside 1500 and **no delivery decision changes**: no chaining, no `ask-on-risk`, no
`size:exception`. The design's recorded size reconciliation (proposal ≈47 → rendered ≈78) is markdown
wrapping at the canonical file's ~90-column prose width, not added content.

**Split prohibition (load-bearing).** A1 and A2 must never land in separate commits or separate PRs: the
`AGENTS.md` bullet is a pointer to COV-07 and is meaningless — and would be a dangling reference — without the
requirement it points at. Rollback is atomic for the same reason (design § *Rollback*).

---

## TDD posture — stated honestly (no RED/GREEN theatre)

`openspec/config.yaml` sets `strict_tdd: false`, and this change adds **no executable behaviour**: it edits two
Markdown documents and no test is added, modified, or deleted (proposal non-goal 2; design § *Guard analysis*).
There is therefore **no failing test to write first**. The RED↔GREEN pair is replaced by two verifiable records,
in this order:

1. **RED-equivalent — E1 static-absence inventory** (task 4.1): the three floors appear in no gated invocation
   and every `--fail-under` literal stays `100`. This is **already true before the change**; it is re-proven
   *after* the change because COV-07's single scenario asserts exactly that inventory, and evidence taken only
   before the edit would prove nothing about the committed state.
2. **GREEN-equivalent — E2 record presence** (task 4.2): the COV-07 requirement + its one mapping row exist in
   the delta, the `AGENTS.md` bullet names the three modules and the pointer, and
   `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` is green **unmodified**.

The ordering is deliberately inverted relative to classic TDD (`E1` re-run after the edit, `E2` proving the
record landed). Nothing in this change is pytest-assertable except the pre-existing guards, which must stay
green by remaining byte-identical — so no test-red state is manufactured. Recording this inversion is the
honest form; a fabricated failing-test step would be theatre.

---

## Task 0 — Preflight: re-verify every anchor before editing

Design-time line numbers are snapshots, not identifiers (design § *Open items handed forward* item 2).

- [x] Confirm the working tree is on branch `chore/215-cov01-floors-status-quo` and that
      `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/` contains exactly
      `explore.md`, `proposal.md`, `design.md`, and this `tasks.md` — plus, after task 1, `specs/coverage/spec.md`. <!-- sdd-owner: implementation -->
- [x] Re-verify the canonical coverage anchors in `openspec/specs/coverage/spec.md` before any other phase edits
      them: the `---` closing COV-06 at `:281`, the `## Test Mapping` heading at `:283`, the table header at
      `:306`, the delimiter row at `:307`, and the COV-06 TOTAL row at `:324` as the file's final content line.
      Record any drift in the apply report; the anchor-referenced *content* (design Artifact A) is
      drift-independent — only the sync phase's insertion offsets change. <!-- sdd-owner: implementation -->
- [x] Re-verify the `AGENTS.md` insertion anchor: rule 14 is the file's **last** rule (no `### 15.` heading
      exists) and the last bullet closes at `AGENTS.md:127` with the line `  floor.` <!-- sdd-owner: implementation -->

---

## Task 1 (Work unit A1) — Write the delta spec (new file)

- [x] Create the directory `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/` and the
      file `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`. <!-- sdd-owner: implementation -->
- [x] Populate it with design Artifact A **byte-for-byte**, copied from the fenced block in `design.md` §
      *Artifact A — the delta, verbatim*, at column 0 (the outer fence is not part of the content). Concretely,
      the file must contain, in this order: the `# Delta for coverage` H1; the change/issue/branch/store
      blockquote; the capability-justification, additivity, and first-of-its-kind sync-mechanics paragraphs;
      `## ADDED Requirements`; the single `### Requirement: Second-tier per-file floors are deliberately
      verify-phase-only (COV-07)` block (four prose paragraphs) with its one `#### Scenario: No gate is armed
      for the three second-tier floors`; the block's own trailing `---`; `## Test Mapping` with its three prose
      lines and exactly one row; `## Cross-referenced and deliberately untouched`; and the one-paragraph
      non-goals record. <!-- sdd-owner: implementation -->
- [x] Self-check the delta against proposal success criteria 1 and 2: exactly **one** new requirement (COV-07),
      exactly **one** scenario, exactly **one** Test Mapping row; the requirement carries the posture, the three
      in-repo rationale reasons, the **scoped** boundary with the "SHALL NOT be read as a fence around the whole
      repository" caveat, the arming path (its own SDD change amending this requirement + COV-06 + COV-03 + the
      two ban-pinning guards), and the no-number/no-drift clause. <!-- sdd-owner: implementation -->
- [x] Confirm the delta's only threshold literals are `100` and `fail_under = 90`, both quoted from other
      requirements as the definition of the boundary — **no coverage figure for the three floors** (proposal
      success criterion 2; design decision D5). Confirm the phrase "is impossible to arm" appears nowhere
      (proposal risk R2). <!-- sdd-owner: implementation -->
- [x] Confirm the delta is **not** a full spec: it opens with `# Delta for coverage`, uses
      `## ADDED Requirements` (not `## Requirements`), and re-states no COV-01..COV-06 clause — matching the
      archived precedent at
      `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md`. <!-- sdd-owner: implementation -->
- [x] Confirm **no** per-requirement `> Added by change …` provenance line sits above COV-07 (design decision
      D8 — COV-01..COV-06 carry none; provenance lives in the delta header blockquote). <!-- sdd-owner: implementation -->

---

## Task 2 (Work unit A2) — Append exactly one bullet to `AGENTS.md` rule 14

- [x] Append design Artifact B **byte-for-byte** as a **new final bullet** of rule 14's list, immediately after
      `AGENTS.md:127` (the line `  floor.`), inside the file's last rule. The bullet is
      `- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).`
      — **one logical bullet on one physical line** (design decision D6; the wrapped 4-line variant is
      rejected because proposal success criterion 4 asserts one added line literally). <!-- sdd-owner: implementation -->
- [x] Verify the bullet contains no `### 15.` heading, no `100.00%` string, and no `# pragma: no cover` token,
      so it cannot mask a future removal anywhere in rule 14's captured region (design § *Guard analysis*). <!-- sdd-owner: implementation -->
- [x] Verify **nothing else** in `AGENTS.md` changed: zero deleted lines, zero reordered lines, rule 14's
      existing sentences byte-identical, no `### 15.` inserted, no reflow of the file's trailing blank line. <!-- sdd-owner: implementation -->

---

## Task 3 (Work unit A3, part 1) — Land A1 + A2 in ONE atomic commit

- [x] Run `uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest tests/ -q` and record the tally
      re-derived on this branch (the proposal's `1766 passed, 6 skipped` is context only, never a promise —
      AGENTS.md rule 6). Pre-commit hooks run automatically per AGENTS.md rule 5; do not pass `--no-verify`. <!-- sdd-owner: implementation -->
- [x] Stage exactly two files — `AGENTS.md` and
      `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` — and create **one**
      conventional-commit commit named like
      `docs(coverage): record the three second-tier floors as deliberately verify-phase-only (COV-07) (#215)`
      (`CONTRIBUTING.md:85-89`; branch intent `chore/215-…`). A1 and A2 must be in the same commit. <!-- sdd-owner: implementation -->
- [x] Confirm the commit touched no path outside those two: `git diff --name-only HEAD~1..HEAD`. <!-- sdd-owner: implementation -->

---

## Task 4 (Work unit A3, part 2) — Collect E1–E4 evidence

Commands and expected outcomes are design § *Verification and evidence plan*. Paste **actual output**, never a
restatement (AGENTS.md rule 11).

### 4.1 — E1: the static-absence inventory (RED-equivalent, re-proven after the edit)

- [x] Record `git grep -nE "for f in |fail-under" -- scripts/check_core_coverage.sh` — expected roster
      `for f in cli scanner prepare publish` plus one `--fail-under=100` line. <!-- sdd-owner: implementation -->
- [x] Record `git grep -n -- "--fail-under=" -- scripts/ .github/workflows/` — expected: only `100` literals. <!-- sdd-owner: implementation -->
- [x] Record `git grep -n -e "fail_under" -e "fail-under" -- .github/workflows/` — expected: **zero** matches. <!-- sdd-owner: implementation -->
- [x] Record `git grep -nE "profile\.py|mcp_registration\.py|verification\.py" -- scripts/ .github/workflows/` —
      expected: **zero** matches (the three floors appear in no gated invocation and no CI step). <!-- sdd-owner: implementation -->
- [x] Record `git grep -n -A3 "\[tool.coverage.report\]" -- pyproject.toml` — expected: `show_missing = true`
      and the scalar `fail_under = 90`, nothing else. <!-- sdd-owner: implementation -->
- [x] Record `git grep -n "check_core_coverage.sh" -- .github/workflows/` — expected: `ci.yml` only
      (`release.yml` stays asymmetric; that asymmetry belongs to issue #185 and is asserted nowhere here). <!-- sdd-owner: implementation -->

### 4.2 — E2: the record is present in both carriers (GREEN-equivalent)

- [x] Record `git grep -n "COV-07" -- openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md AGENTS.md`
      — expected: the delta's requirement heading plus its one mapping row, and the `AGENTS.md` bullet. <!-- sdd-owner: implementation -->
- [x] Run `uv run pytest tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate -q` and record the
      result — expected green, with the guard file **unmodified** (it was green before the bullet too; the bullet
      is additive and the guard's three assertions are presence-based). <!-- sdd-owner: implementation -->

### 4.3 — E3: the guards stay green unmodified, and no test moved

- [x] Run and record
      `uv run pytest tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100 tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90 -q`
      — expected: all green, all unmodified. <!-- sdd-owner: implementation -->
- [x] Record `git diff --stat -- tests/` — expected: **empty**. <!-- sdd-owner: implementation -->
- [x] Record `uv run pytest tests/ -q` on this branch and report the measured tally. The run is **not** a
      coverage measurement and needs no `.coverage` file; `tests/test_coverage_contract.py` keeps its documented
      skip (COV-01-S3). <!-- sdd-owner: implementation -->

### 4.4 — E4: diff scope (the "no code change" acceptance criterion)

- [x] Record `git diff --stat origin/dev` — expected roster: `AGENTS.md`, the change's delta, and the change's
      phase artifacts — nothing else. <!-- sdd-owner: implementation -->
- [x] Record `git diff --name-only origin/dev -- src/ tests/ scripts/ .github/ pyproject.toml uv.lock` —
      expected: **empty**. <!-- sdd-owner: implementation -->
- [x] Record `git diff -U0 -- AGENTS.md` — expected exactly **+1 / −0** (proposal success criterion 4). <!-- sdd-owner: implementation -->
- [x] Confirm `openspec/specs/coverage/spec.md` is absent from the diff — the canonical capability file is
      touched **only** by `sdd-sync` (design § *Insertion-point mechanics* Step 3). <!-- sdd-owner: implementation -->

---

## Task 5 — Rollback readiness and stop conditions

- [x] Record the revert handle in the apply report: **one commit, two files, one command** — `git revert <sha>`
      (or `git reset` before any push) deletes the delta and removes the `AGENTS.md` bullet. Because the
      canonical `openspec/specs/coverage/spec.md` is untouched until sync, a pre-sync revert restores every
      canonical spec byte-for-byte. <!-- sdd-owner: implementation -->
- [x] Stop-and-report conditions (do **not** self-authorize any of these): an anchor is missing or drifted such
      that the delta cannot be placed without rewording canonical prose; any E1 command returns a non-100
      `--fail-under` literal or a match for the three floor modules; any E3 guard is red; or the diff reaches any
      path in the forbidden list below. Each of these is a design-doc escalation, never a fix made in apply. <!-- sdd-owner: implementation -->

---

## Forbidden (zero-path guard for the whole apply phase)

Absent from the diff by construction (proposal success criterion 5; E4 asserts it mechanically):
`src/sofer/**` · `tests/**` · `scripts/**` · `.github/workflows/**` · `pyproject.toml` · `uv.lock` ·
`CONTRIBUTING.md` · `README.md` · `README_ES.md` · `.pre-commit-config.yaml` · `openspec/specs/**`
(sync-phase only) · the `## Purpose` enumeration in the canonical coverage spec (left stale deliberately —
COV-04 precedent). No gate is armed for the three floors, no coverage figure is measured or promised, no
`--fail-under=90` anywhere, no test is added or edited, and the `AGENTS.md` bullet is a pointer, **not** a second
mandate over the three modules.

---

## Recorded handoff to verify

1. E1–E4 above are **apply-owned evidence collection**; the verify phase re-runs them and pastes the outputs into
   the verify report as COV-07's static evidence (design success criterion 9). No new test is invented for it.
2. Issue #215's full acceptance-criteria list is still unread (no `gh` in this runtime); the proposal's AC1–AC3
   transcription is what this task set traces. Extend the traceability table before verify if the issue carries
   more.
3. `sdd-sync` owns the canonical edit: insert the COV-07 block between the `---` closing COV-06 (`:281`) and the
   `## Test Mapping` heading (`:283`), carrying its own trailing `---`, then append the single row after the
   COV-06 TOTAL row (`:324`). Re-verify the anchors first; never re-emit the table header or delimiter row.

---

- [x] Final self-check before returning: the delta exists at the exact path, the `AGENTS.md` diff is +1/−0, one
      commit carried both, E1–E4 outputs are recorded verbatim, and no forbidden path appears in
      `git diff --name-only origin/dev`. <!-- sdd-owner: implementation -->
