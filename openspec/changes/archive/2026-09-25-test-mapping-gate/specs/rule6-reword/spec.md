# rule6-reword Specification

## Purpose

Defines the **rewrite of rule 6** — the repository's central traceability invariant — in its two
normative homes, `AGENTS.md` (rule 6, currently `AGENTS.md:42`) and `openspec/config.yaml`
(`rules.specs`), so both state **exactly what the mechanism enforces** instead of an absolute the
repository does not honor. The rewrite SHALL declare the honest limit (the gate proves a `test:`
reference exists and is collected, **not** that a test exercises its scenario), the `test:`/`verify:`
contract and the `verify:` escape hatch, and the registry scope for specs without a table. As part of
the same edit it SHALL absorb **#214**: the stale hardcoded pass/collected/skipped tally in rule 6 SHALL
be **deleted, not updated**, leaving the reproducing command as the only anchor (PB-11).

## Requirements

### Requirement: Honest limit declared (R6-01)

Rule 6 SHALL state that the traceability gate verifies a `test:` reference **exists and is collected by
pytest**, and SHALL state explicitly that this is an **existence/collection** check that does **not**
prove the referenced test exercises the scenario. It SHALL NOT claim that "every scenario has a
corresponding test" as an absolute enforced fact, because the mechanism does not verify exercise. The
`verify:` route SHALL be named as the declared escape hatch rather than as proof.

#### Scenario: Rule 6 states the existence/collection limit

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL state that a `test:` reference is verified to exist and to be collected by pytest
- AND it SHALL state that this is not proof that the test exercises the scenario

#### Scenario: Rule 6 no longer asserts an unenforced absolute

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL NOT present "every scenario has a corresponding test" as a fact the gate enforces
  without qualification

### Requirement: `test:`/`verify:` contract and escape hatch declared (R6-02)

Rule 6 SHALL name the two evidence prefixes — `test:` and `verify:` — and SHALL state that every data
row of a `## Test Mapping` table begins its Verification cell with exactly one of them. It SHALL define
`test:` as routing to a repository test and `verify:` as routing to declared, non-machine-verified
verify-phase evidence, so a reader understands that `verify:` declares an evidence class and does not
assert proof. The rule SHALL point to the `test-mapping-contract` capability as the contract of record.

#### Scenario: Rule 6 names both prefixes and their meaning

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL name `test:` and `verify:`
- AND it SHALL state that `verify:` is declared evidence that the gate does not machine-verify

#### Scenario: A data row without a prefix is described as non-compliant

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL state that a Test Mapping row SHALL begin with exactly one prefix

### Requirement: Registry scope declared (R6-03)

Rule 6 SHALL state that specs which carry **no** `## Test Mapping` section are recorded in the
**registry** (`openspec/test-mapping-registry.md`) and are **outside the gate** until they adopt one,
and that the checker enforces the registry↔tree bijection so no spec can silently fall outside the
gate. The rule SHALL remain truthful about the coverage limit this implies: the 17 currently-unmapped
specs are a **declared backlog**, not mapped work.

#### Scenario: Rule 6 points to the registry and states the boundary

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL name the registry as the home of the specs without a table
- AND it SHALL state that those specs are outside the gate until they adopt a table

### Requirement: AGENTS.md and config.yaml agree (R6-04)

`AGENTS.md` rule 6 and `openspec/config.yaml`'s `rules.specs` entry SHALL state the **same contract**
after the change: the prefixes, the existence/collection limit, the `verify:` escape hatch, and the
registry boundary. Neither home SHALL contradict the other, and a static guard test SHALL assert that
the two texts agree on the contract terms so a future edit to one cannot silently diverge from the
other (#211 acceptance criterion: "`AGENTS.md` rule 6 and `openspec/config.yaml` rules agree").

#### Scenario: Both normative homes state the same contract

- GIVEN `AGENTS.md` rule 6 and `openspec/config.yaml`'s `rules.specs` entry after the change
- WHEN `tests/` inspects both texts
- THEN each SHALL name `test:` and `verify:`, the existence/collection limit, and the registry
- AND a guard test SHALL fail if the two texts disagree on those contract terms

#### Scenario: A diverging edit to one home is caught

- GIVEN the guard test that pins rule 6 and `rules.specs` to the contract terms
- WHEN one home is edited to drop a contract term while the other is unchanged
- THEN the guard test SHALL fail

### Requirement: Stale tally deleted, not updated — #214 absorbed (R6-05)

Rule 6's hardcoded pass/skipped/collected tally SHALL be **removed**, and SHALL NOT be replaced by an
updated figure. The reproducing command (`uv run pytest tests/ -q`) SHALL remain as the sole anchor of
the "never reduce coverage" floor, so the rule carries a command that re-derives the tally instead of a
hand-maintained literal that goes stale. This SHALL satisfy BP-11 scenario 1 ("the anchor carries its
own command") by the **absence** of any recorded figure, and SHALL close #214's primary acceptance
criterion without a re-derivation step.

#### Scenario: The stale triple is gone

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN the pre-change literal `1766 passed, 6 skipped (1772 collected)` SHALL be absent
- AND no replacement pass/skipped/collected triple SHALL have been written

#### Scenario: The reproducing command is retained

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL still name `uv run pytest tests/ -q` as the command that reports the tally
- AND no hardcoded tally SHALL remain without that reproducing command beside it

### Requirement: config.yaml context tally is not a stale literal (R6-06)

`openspec/config.yaml`'s `context` line SHALL NOT continue to present a stale hardcoded test tally
(`1029 tests (2 skipped, 1031 collected, 334 spec scenarios)`) as truth. Because `config.yaml` is
edited in this change anyway, the stale figure SHALL be **removed** and the line SHALL defer to the
reproducing command already declared under `testing` (`test_command: "uv run pytest tests/ -q"`)
instead of carrying a number no run re-derives — the same delete-not-update rule as R6-05.

#### Scenario: The config context carries no stale count

- GIVEN `openspec/config.yaml` after the change
- WHEN the `context` line and the `testing` block are inspected
- THEN no stale `tests` / `collected` / `skipped` / `scenarios` count SHALL remain in `context`
- AND the reproducing command declared under `testing` SHALL remain present

### Requirement: project.md stale tallies stay owned by #184 (R6-07)

The stale tallies in `openspec/project.md` (`:40`, `:81`, `:87`) SHALL be **cross-referenced** to issue
**#184**, which owns that file, and SHALL NOT be silently rewritten by this change (D8). This
requirement records the boundary rather than expanding the change into an unrelated documentation
sweep.

#### Scenario: project.md tallies are cross-referenced, not edited

- GIVEN this change's diff and `openspec/project.md`
- WHEN the diff is inspected
- THEN `openspec/project.md` SHALL NOT appear in the diff
- AND the change's documentation SHALL name #184 as the owner of those tallies
