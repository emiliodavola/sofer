# test-mapping-contract Specification

## Purpose

Defines the **machine-readable evidence contract** carried by every `## Test Mapping` table in
`openspec/specs/*/spec.md`: the evidence-prefix grammar (`test:` / `verify:`) that every data row's
Verification cell SHALL begin with, what makes a row **valid** or **empty**, and the exact set of specs
the contract reaches today. The contract stops the mapping from being free-form prose while
**preserving every existing evidence string verbatim** — a re-tag adds exactly one prefix, it never
re-authors the row.

This domain specifies **WHAT a compliant table looks like**. The enforcement mechanism — spec-tree
enumeration, scenario↔row bijection, pytest collection of `test:` targets, and the unmapped-spec
registry — is specified by the sibling `mapping-checker` domain. The domain is **scoped to the specs
that already carry a `## Test Mapping` section** (D3): on this branch those are exactly `ci`,
`coverage`, and `process-boundary`. A spec with no table is deliberately **out of the contract's direct
reach** and captured by the registry instead — this change does not sweep 659 scenarios (the #211
scope boundary).

## Requirements

### Requirement: Evidence-cell prefix contract (TMC-01)

Every **data row** of a `## Test Mapping` table SHALL begin its Verification cell with **exactly one**
machine-readable prefix — `test:` for a row routed to a repository test, or `verify:` for a row routed
to declared verify-phase evidence. The prefix SHALL be the first non-whitespace token of the cell,
SHALL be lowercase, and SHALL be immediately followed by its reference with no intervening separator
requirement beyond whitespace. A cell that begins with no recognised prefix, with both prefixes, with a
repeated prefix, or with a differently-cased token SHALL be **non-compliant**. The evidence text that
follows the prefix SHALL be preserved **verbatim** from the pre-change row; this contract SHALL be read
as a re-tag, never a re-authorship or a reclassification (D1).

#### Scenario: A `test:` cell is compliant and preserves its evidence string

- GIVEN a data row whose Verification cell reads `test:tests/test_ci_workflows.py — YAML inspection`
- WHEN the cell is inspected against the contract
- THEN it SHALL be compliant with prefix `test:`
- AND the reference `tests/test_ci_workflows.py — YAML inspection` SHALL be byte-identical to the
  pre-change cell with only the prefix added

#### Scenario: A `verify:` cell is compliant and preserves its evidence string

- GIVEN a data row whose Verification cell reads `verify:Verify-phase static evidence — needs-chain proof`
- WHEN the cell is inspected against the contract
- THEN it SHALL be compliant with prefix `verify:`
- AND the reference text SHALL be preserved verbatim from the pre-change row

#### Scenario: A cell without a prefix is non-compliant

- GIVEN a data row whose Verification cell reads `tests/test_ci_workflows.py — YAML inspection`
- WHEN the cell is inspected against the contract
- THEN it SHALL be non-compliant — no `test:` or `verify:` prefix is present

#### Scenario: A cell with two prefixes is non-compliant

- GIVEN a data row whose Verification cell reads `test: verify: tests/test_ci_workflows.py`
- WHEN the cell is inspected against the contract
- THEN it SHALL be non-compliant — exactly one prefix is required, not two

#### Scenario: A differently-cased token is non-compliant

- GIVEN a data row whose Verification cell reads `Test:tests/test_ci_workflows.py`
- WHEN the cell is inspected against the contract
- THEN it SHALL be non-compliant — the prefix grammar is lowercase-only

### Requirement: `test:` reference grammar (TMC-02)

A `test:` row SHALL name a **repository-relative** test path using POSIX `/` separators and no leading
`/`, **optionally** followed by exactly one `::` node selector naming a test function
(`test:<path>::<test_name>`). The reference SHALL be non-empty. An absolute path, a path containing a
Windows drive letter or backslash, an empty reference, and a reference containing more than one `::`
segment SHALL each be non-compliant. The `test:` prefix SHALL denote a repository test and SHALL NOT
denote a verify-phase artifact or a documentation reference.

#### Scenario: A path-only reference is well-formed

- GIVEN a `test:` row whose reference is `tests/test_ci_workflows.py`
- WHEN the reference grammar is applied
- THEN it SHALL be well-formed — a repository-relative path with no node selector

#### Scenario: A path-plus-node reference is well-formed

- GIVEN a `test:` row whose reference is
  `tests/test_ci_workflows.py::test_ci_lint_job_runs_the_ruff_format_gate`
- WHEN the reference grammar is applied
- THEN it SHALL be well-formed — one path and exactly one `::` node selector

#### Scenario: An absolute or Windows-style path is non-compliant

- GIVEN `test:` rows whose references are `/workspace/sofer/tests/test_cli.py` and
  `tests\\test_cli.py`
- WHEN the reference grammar is applied
- THEN each SHALL be non-compliant — the reference SHALL be repository-relative with POSIX separators

#### Scenario: An empty or multi-selector reference is non-compliant

- GIVEN `test:` rows whose references are the empty string and
  `tests/test_cli.py::test_a::test_b`
- WHEN the reference grammar is applied
- THEN each SHALL be non-compliant — the reference SHALL be non-empty and carry at most one `::`

### Requirement: `verify:` reference grammar (TMC-03)

A `verify:` row SHALL carry a **non-empty artifact reference** naming the verify-phase evidence class
that evidences the scenario — for example the gate command whose exit code is pasted into the verify
report, the static inspection performed, or the report section that records it. The `verify:` prefix
SHALL declare the escape hatch **honestly**: it is deliberately **not machine-verified** by the checker,
and neither this contract nor the gate SHALL be read as asserting that a `verify:` row *proves* its
scenario (D2). An empty or whitespace-only reference SHALL be non-compliant.

#### Scenario: A non-empty verify reference is compliant

- GIVEN a `verify:` row whose reference is
  `Verify-phase runtime evidence — bash scripts/check_core_coverage.sh exit code`
- WHEN the reference is inspected
- THEN it SHALL be compliant — the artifact reference is non-empty and names an evidence class

#### Scenario: An empty verify reference is non-compliant and is not treated as proof

- GIVEN a `verify:` row whose reference is empty or whitespace-only
- WHEN the reference is inspected
- THEN it SHALL be non-compliant
- AND the checker SHALL NOT report that row as satisfied evidence — `verify:` declares an evidence
  class, it does not prove the scenario

### Requirement: Table structure — data rows and empty rows (TMC-04)

A `## Test Mapping` table SHALL consist of a **header row** declaring exactly the three columns `Req`,
`Scenario`, and `Verification`; a Markdown **separator row**; and zero or more **data rows**. A data
row is a table line whose three cells each carry non-empty content. An **empty row** — a table line
whose cells are all whitespace-only, or whose `Req`/`Scenario`/`Verification` content is absent — SHALL
NOT appear in a compliant table. The header row and the separator row SHALL NOT be treated as data rows
by the contract or by the checker. The column order SHALL be fixed at `Req`, `Scenario`, `Verification`.

#### Scenario: Header and separator are not data rows

- GIVEN a `## Test Mapping` table beginning with `| Req | Scenario | Verification |` and its separator
- WHEN the table is parsed
- THEN the header and separator SHALL be recognised as structural, not as data rows
- AND the first row validated against TMC-01 SHALL be the first row after the separator

#### Scenario: An all-blank line is an empty row

- GIVEN a table containing the line `| | | |` between two data rows
- WHEN the table is parsed
- THEN that line SHALL be classified as an empty row and the table SHALL be non-compliant

#### Scenario: A row missing the Verification cell is non-compliant

- GIVEN a table line whose Verification cell carries no content
- WHEN the table is parsed
- THEN it SHALL be non-compliant — a data row SHALL carry content in all three columns

### Requirement: Contract scope — the three table-bearing specs (TMC-05)

The contract SHALL reach **exactly** the specs that carry a `## Test Mapping` section. On this branch
those three specs SHALL be `ci` (`openspec/specs/ci/spec.md`), `coverage`
(`openspec/specs/coverage/spec.md`), and `process-boundary`
(`openspec/specs/process-boundary/spec.md`), and **every data row in each** SHALL be compliant with
TMC-01..TMC-04. A spec that does not carry a `## Test Mapping` section SHALL be **out of the contract's
direct reach** and SHALL be captured by the `mapping-checker` registry instead; the contract SHALL NOT
be read as requiring such a spec to author a table, and SHALL NOT be read as backfilling a test id for
any scenario (the no-sweep boundary, #211 scope note). The scope set SHALL be derived from the tree, not
from a hand-maintained list, so a spec that gains or loses the section moves in or out of scope without
any edit to this contract.

#### Scenario: The three table-bearing specs are in scope

- GIVEN `openspec/specs/*/spec.md` on this branch
- WHEN the specs carrying a `## Test Mapping` section are enumerated
- THEN the set SHALL be exactly `ci`, `coverage`, and `process-boundary`
- AND every data row in those three tables SHALL be compliant with TMC-01..TMC-04

#### Scenario: A spec without a table is out of direct reach and registry-covered

- GIVEN a spec such as `openspec/specs/cli/spec.md` that carries no `## Test Mapping` section
- WHEN the contract's direct reach is determined
- THEN the spec SHALL be out of direct reach — no row SHALL be required of it
- AND it SHALL be captured by the `mapping-checker` registry, which is the enforcement surface for the
  uncovered set

#### Scenario: Scope is tree-derived, not hand-listed

- GIVEN a hypothetical spec that gains a `## Test Mapping` section, and another that loses one
- WHEN the contract's scope is determined
- THEN the gaining spec SHALL enter scope and the losing spec SHALL leave it, with no edit to this
  contract's text — the scope set is derived from the tree
