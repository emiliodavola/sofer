# Delta for process-boundary

**Capability choice (justified):** `process-boundary` only. PB-07 owns the "these commands SHALL
pass" family, and PB-10 (ruff-format-drift, branch `chore/177-ruff-format-drift`, not merged here)
is its formatter-integrity sibling; a suite-level zero-`DeprecationWarning` property and a
count-truth anchor are that same family. `coverage` owns *measured percentages and gate exit codes*,
not prose literals. `codebook` owes no REMOVED delta — no requirement in `openspec/specs/codebook/`
mandates `_infer_type` (only `repo-compliance/spec.md:1494` records its past rename). ONE capability,
because both properties are suite/gate hygiene facts of one boundary. Numbering: PB-10 is reserved by
the unmerged ruff-format-drift change (`.git/COMMIT_EDITMSG`: "sync PB-10 and archive the
ruff-format-drift change"); its text is absent on this branch and is neither written nor modified.

ADDED, not MODIFIED: PB-07's existing text still holds verbatim, so no lossy archive-time
replacement is needed.

## ADDED Requirements

### Requirement: Verifiable test-count anchor (PB-11)

AGENTS.md rule 6 SHALL anchor its "never reduce coverage" floor to the SOURCE of the tally — the
command that reports it — and SHALL NOT present a bare hardcoded pass/collected/skipped literal as
the floor's only support. Any recorded figure SHALL match the tally that command reports on the
change's branch.

#### Scenario: Anchor carries its own command

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL name the count command (`uv run pytest tests/ -q`)
- AND any recorded pass/collected/skipped figure SHALL match that command's actual tally

#### Scenario: The stale literal is gone

- GIVEN `AGENTS.md:44` pre-change (`1149 tests currently pass (1151 collected, 2 skipped)`)
- WHEN post-change rule 6 is inspected
- THEN the 1149/1151/2 triple SHALL be absent
- AND no hardcoded tally SHALL remain without the reproducing command beside it

### Requirement: Zero deprecation warnings from the migrated codebook surface (PB-12)

A normal suite run SHALL emit zero `DeprecationWarning`s from the codebook type-inference surface:
`_infer_type` in `src/sofer/codebook.py` SHALL be deleted (option B — the only in-repo caller
migrates to the live public API), and no module, test or doc outside `openspec/changes/archive/**`
SHALL reference it. The migration SHALL NOT drop, weaken, skip or reword away a behavioural
assertion: `tests/test_codebook.py` SHALL assert the SAME `(values, expected)` cases against
`infer_column_type`, and `test_returns_same_as_private` — whose only subject was the alias — SHALL be
replaced by those same cases asserted against the live API.

#### Scenario: Suite run is deprecation-free

- GIVEN the change applied on `chore/162-agents-count-infer-type`
- WHEN `uv run pytest tests/ -q` runs
- THEN it SHALL be green
- AND the warnings summary SHALL contain zero `DeprecationWarning` lines from `sofer.codebook`

#### Scenario: Behavioural parity preserved on the live API

- GIVEN `tests/test_codebook.py` post-migration
- WHEN `uv run pytest tests/test_codebook.py -q` runs
- THEN every pre-change `(values, expected)` case SHALL still assert the same expected output, now
  against `infer_column_type`, with no case deleted, relaxed or parametrised away

#### Scenario: No residual alias reference

- GIVEN the post-change tree
- WHEN `_infer_type` is searched over `src/`, `tests/`, `AGENTS.md` and the READMEs
- THEN zero matches SHALL be found outside `openspec/changes/archive/**` historical prose

## Non-goals (binding)

- No fix for other stale numbers: `openspec/project.md` (#184), the `ruff.toml` reference in
  `CONTRIBUTING.md` (#187), README counts/flags (#183, #190). `openspec/config.yaml` is stale too but
  gitignored — local-only, unfixable by a PR.
- No change outside `AGENTS.md`, `tests/test_codebook.py`, `src/sofer/codebook.py` (third: alias
  deletion only). No `pyproject.toml` `filterwarnings` addition — out of scope.
- No behavioural assertion weakened, skipped, renamed away or removed.
- Untouched: `tasks.md`, `proposal.md`, `openspec/specs/**`,
  `openspec/changes/2026-09-14-chore-python-version-313/`, `openspec/changes/archive/**`.
- No commit, push or PR — the parent owns delivery.

## Test Mapping

process-boundary carries no Test Mapping section; this delta adds one for PB-11/PB-12 only (`ci`,
`coverage` precedent: "a green test **or** verify-phase static/runtime evidence"). Strength column
is honest: only the behavioural-parity row is a pytest assertion; the others are command/scan facts
of the same class as the COV-01/COV-02 rows.

| Req | Scenario | Verification | Strength |
| --- | --- | --- | --- |
| PB-11 | Anchor carries its own command | Verify-phase static evidence: post-change `AGENTS.md` rule 6 text inspected, plus a rerun of `uv run pytest tests/ -q` whose tally is reproduced in the verify report | Weaker — prose/command fact; a static guard would need a 4th file (precedent `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate`), outside this proposal's scope |
| PB-11 | The stale literal is gone | Verify-phase static evidence: `git diff AGENTS.md` shows the 1149/1151/2 triple removed and rule 6 naming the command | Weaker — same class |
| PB-12 | Suite run is deprecation-free | Runtime command evidence: `uv run pytest tests/ -q` warnings summary contains 0 `DeprecationWarning`, cross-checked with `-W error::DeprecationWarning` on `tests/test_codebook.py`; output reproduced in the verify report | Medium — runtime fact, not pytest-asserted: no `filterwarnings` config exists and adding one is out of scope |
| PB-12 | Behavioural parity preserved on the live API | **pytest-asserted**: the migrated `tests/test_codebook.py` cases themselves (`uv run pytest tests/test_codebook.py -q` green); verify diffs the case list and expected outputs against the pre-change tree | Strong |
| PB-12 | No residual alias reference | Verify-phase static evidence: repo-wide search for `_infer_type` returns zero hits outside `openspec/changes/archive/**`; the `src/sofer/codebook.py` diff is the deletion only | Medium — static scan recorded in verify |
