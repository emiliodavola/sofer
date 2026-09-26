# Delta for process-boundary

> Change `2026-09-26-chore-234-verify-escape-hatch` (issue #234). Canonical target:
> `openspec/specs/process-boundary/spec.md`. Adds requirement **PB-15** and its Test Mapping rows.
> This domain already owns the AGENTS.md rule 6 anchor (PB-11), so the escape-hatch honesty duty
> lands beside it, not in a new capability.

## ADDED Requirements

### Requirement: Declared, non-verifiable `verify:` escape hatch with an owner and a review trigger (PB-15)

`AGENTS.md` rule 6 SHALL state plainly that a `verify:` row is a **declared, non-verifiable** escape
hatch: it names an evidence class, it does **not** prove its scenario, and no mechanism re-checks it.
Rule 6 SHALL name the escape hatch's **owner** (the repository maintainer) and its **review trigger**
(any change to a `verify:` row or to a spec's evidence class, and each release review). The
`openspec/config.yaml` `rules.specs` bullet SHALL state the same, so the two normative homes agree.
The checker `scripts/check_test_mapping.py` SHALL state the same policy in its module docstring and
SHALL report, on every run, the number of `verify:` rows it accepted as declared evidence, labelled
non-verifiable and naming the owner and review trigger. The checker SHALL NOT resolve, execute, or
otherwise verify a `verify:` reference (that would be the rejected option (a) of issue #234). The
unmapped specs in `openspec/test-mapping-registry.md` SHALL be recorded as a **permanent declared
backlog** — not pending work — with the same owner and review trigger. The checker's scenario grammar
`SCENARIO_RE` SHALL be documented as matching exactly the four-hash `#### Scenario:` level and SHALL be
pinned by tests.

#### Scenario: Rule 6 and the config state the escape hatch is non-verifiable with owner and trigger
- GIVEN `AGENTS.md` rule 6 and `openspec/config.yaml` `rules.specs` after the change
- WHEN the two normative homes are inspected
- THEN each SHALL state that a `verify:` row is declared and non-verifiable (not proof)
- AND each SHALL name the owner (the repository maintainer) and the review trigger

#### Scenario: The checker reports accepted verify rows as declared, non-verifiable evidence
- GIVEN a mapped spec carrying at least one `verify:` row
- WHEN the checker runs
- THEN its output SHALL report the number of accepted `verify:` rows as declared evidence
- AND the report SHALL label them non-verifiable and name the owner and the review trigger
- AND the checker SHALL NOT resolve or execute any `verify:` reference

#### Scenario: The registry records the permanent declared-backlog decision
- GIVEN `openspec/test-mapping-registry.md` after the change
- WHEN it is inspected for the policy on the unmapped specs
- THEN it SHALL state that they are a permanent declared backlog, not pending work
- AND it SHALL name the owner and the review trigger

#### Scenario: SCENARIO_RE matches exactly the four-hash level
- GIVEN a spec whose only scenario headings are `### Scenario:` or `##### Scenario:`
- WHEN the checker enumerates scenarios
- THEN those headings SHALL NOT be enumerated (a row naming them fails as a non-existent scenario)
- AND an indented `#### Scenario:` heading SHALL be enumerated

## Evidence (AGENTS.md rule 6)

PB-15's scenarios are added to the canonical `process-boundary` `## Test Mapping` table at archive
time, one row each, so the bijection holds:

| Scenario | Verification |
|----------|--------------|
| Rule 6 and the config state the escape hatch is non-verifiable with owner and trigger | `test:tests/test_ci_workflows.py::test_verify_escape_hatch_has_owner_and_review_trigger` |
| The checker reports accepted verify rows as declared, non-verifiable evidence | `test:tests/test_test_mapping_checker.py::test_verify_rows_reported_as_declared_escape_hatch` |
| The registry records the permanent declared-backlog decision | `test:tests/test_ci_workflows.py::test_verify_escape_hatch_has_owner_and_review_trigger` |
| SCENARIO_RE matches exactly the four-hash level | `test:tests/test_test_mapping_checker.py::test_scenario_regex_matches_only_four_hash_headings` |
