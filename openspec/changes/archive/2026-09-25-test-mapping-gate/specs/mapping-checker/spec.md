# mapping-checker Specification

## Purpose

Defines the **checker** that enforces the `test-mapping-contract` domain and the explicit boundary
around what is *not* yet mapped. The checker is a committed script under `scripts/` that:

1. enumerates `openspec/specs/*/spec.md` and classifies each spec as **mapped** (carries a
   `## Test Mapping` section) or **unmapped**;
2. for each mapped spec, requires **every `#### Scenario:` heading to appear in exactly one data row**
   and forbids empty rows;
3. for each `test:` row, requires the referenced test **to exist and to be collected by pytest**;
4. cross-checks the **registry** of unmapped specs against the tree as a **bijection**.

The checker proves **existence and collection only** — it SHALL NOT execute the referenced tests, and
it SHALL NOT be read as proving that a test exercises its scenario. That honest limit is the whole
point of the change (D2/D7) and is restated by the `rule6-reword` domain.

## Requirements

### Requirement: Spec-tree enumeration and classification (MC-01)

The checker SHALL enumerate every `openspec/specs/*/spec.md` file (exactly one `spec.md` per
immediate child directory of `openspec/specs/`) and classify each spec as **mapped** when it contains a
`## Test Mapping` heading that introduces at least one data row, or **unmapped** otherwise. The
classification SHALL be derived from the tree at check time, never from a hand-maintained list. The
checker SHALL be deterministic and SHALL NOT require network access.

#### Scenario: Every spec is classified from the tree

- GIVEN the committed `openspec/specs/` tree
- WHEN the checker enumerates `openspec/specs/*/spec.md`
- THEN it SHALL classify each spec as mapped or unmapped by inspecting its own text
- AND it SHALL derive both sets from that enumeration, not from an embedded roster

#### Scenario: A spec with a heading but no data rows is unmapped

- GIVEN a spec whose `## Test Mapping` heading is followed by a header and separator but no data row
- WHEN the checker classifies it
- THEN it SHALL be classified as unmapped — the section introduces no mapping

### Requirement: Scenario↔row completeness for mapped specs (MC-02)

For each **mapped** spec, the checker SHALL require that **every `#### Scenario:` heading appears in
exactly one data row** of that spec's `## Test Mapping` table, matched by the row's `Scenario` cell
text. A scenario heading that appears in **no** data row SHALL fail; a scenario that appears in **two or
more** data rows SHALL fail; a data row whose `Scenario` cell names no existing `#### Scenario:` heading
SHALL fail. The check SHALL be per-spec, so a scenario heading from one spec SHALL NOT satisfy a row in
another.

#### Scenario: A scenario with no row fails

- GIVEN a mapped spec with a `#### Scenario: X` heading and no data row naming `X`
- WHEN the checker validates that spec
- THEN it SHALL fail and name the spec and the unmapped scenario `X`

#### Scenario: A scenario mapped twice fails

- GIVEN a mapped spec whose table contains two data rows naming the same `#### Scenario: X`
- WHEN the checker validates that spec
- THEN it SHALL fail — each scenario SHALL appear in exactly one row

#### Scenario: A row naming an unknown scenario fails

- GIVEN a mapped spec whose table contains a data row naming a scenario that is not a
  `#### Scenario:` heading in that spec
- WHEN the checker validates that spec
- THEN it SHALL fail — the row references a scenario that does not exist

#### Scenario: A fully one-to-one mapping passes

- GIVEN a mapped spec in which every `#### Scenario:` heading appears in exactly one row and every row
  names an existing heading
- WHEN the checker validates that spec
- THEN that spec's completeness check SHALL pass

### Requirement: `test:` targets exist and are collected by pytest (MC-03)

For each `test:` row, the checker SHALL require the referenced **file to exist** under the repository
root. For a path-only reference, the referenced file SHALL yield **at least one collected item**; for a
`path::name` reference, the node id SHALL be an **exact member** of the node ids pytest collects for
that file. Collection SHALL be obtained with pytest in **collect-only** mode over the referenced files —
the checker SHALL NEVER execute a test body, and SHALL run offline. A missing file, a file that
collects nothing, a node id that pytest does not collect, and a malformed reference (per
`test-mapping-contract` TMC-02) SHALL each fail with the offending spec, row, and reference named.

#### Scenario: A missing test file fails

- GIVEN a `test:` row referencing `tests/does_not_exist.py`
- WHEN the checker validates the reference
- THEN it SHALL fail and name the row and the missing path

#### Scenario: An uncollected node id fails

- GIVEN a `test:` row referencing `tests/test_ci_workflows.py::test_no_such_name`
- WHEN the checker collects `tests/test_ci_workflows.py` with pytest
- THEN the node id SHALL NOT be present in the collected set and the checker SHALL fail

#### Scenario: A path-only reference with zero collected items fails

- GIVEN a `test:` row referencing an existing test file that pytest collects no items from
- WHEN the checker collects that file
- THEN it SHALL fail — a path-only reference requires at least one collected item

#### Scenario: A collected node id passes

- GIVEN a `test:` row referencing
  `tests/test_ci_workflows.py::test_ci_lint_job_runs_the_ruff_format_gate`
- WHEN the checker collects that file with pytest
- THEN the node id SHALL be present in the collected set and the reference SHALL pass

#### Scenario: Collection never executes a test

- GIVEN any run of the checker
- WHEN it resolves `test:` references
- THEN it SHALL invoke pytest in collect-only mode only
- AND no test body SHALL execute as a side effect of the check

### Requirement: `verify:` references and empty rows (MC-04)

For each `verify:` row, the checker SHALL require a **non-empty artifact reference**. The checker SHALL
NOT attempt to resolve, execute, or verify a `verify:` reference beyond its non-emptiness — `verify:` is
the declared escape hatch, and the gate's obligation is to force it to be declared, not to pretend it is
proof. The checker SHALL additionally reject any **empty row** in a mapped table (per
`test-mapping-contract` TMC-04).

#### Scenario: An empty verify reference fails

- GIVEN a mapped spec with a `verify:` row whose reference is empty
- WHEN the checker validates that row
- THEN it SHALL fail — a `verify:` reference SHALL be non-empty

#### Scenario: An empty row fails

- GIVEN a mapped spec whose table contains an all-blank `| | | |` line
- WHEN the checker validates that spec
- THEN it SHALL fail — empty rows are not permitted in a compliant table

#### Scenario: A non-empty verify reference passes without being resolved

- GIVEN a mapped spec with a `verify:` row carrying a non-empty artifact reference
- WHEN the checker validates that row
- THEN it SHALL pass
- AND the checker SHALL NOT execute or resolve the referenced evidence

### Requirement: Registry bijection for unmapped specs (MC-05)

The checker SHALL read the committed registry (`openspec/test-mapping-registry.md`) and enforce a
**bijection** with the tree: every **unmapped** spec SHALL be listed exactly once with a **non-empty
reason**, and every **mapped** spec SHALL NOT be listed. Equivalently, `mapped ∪ registered` SHALL equal
the full spec set and `mapped ∩ registered` SHALL be empty. An unregistered unmapped spec and a stale
entry for a spec that now carries a table SHALL each fail, so a new spec cannot silently fall outside
the gate and a mapped spec cannot linger in the backlog. The registry SHALL carry each entry's measured
spec identity; scenario counts SHALL be **re-derived at check time**, never stored, so the registry
cannot decay into the stale-literal class #214 files.

#### Scenario: An unregistered unmapped spec fails

- GIVEN a spec without a `## Test Mapping` section that is absent from the registry
- WHEN the checker cross-checks the registry against the tree
- THEN it SHALL fail and name the unregistered spec

#### Scenario: A stale registered entry for a mapped spec fails

- GIVEN a spec that carries a `## Test Mapping` section and is nevertheless listed in the registry
- WHEN the checker cross-checks the registry against the tree
- THEN it SHALL fail and name the stale entry

#### Scenario: A registry entry with an empty reason fails

- GIVEN a registry entry whose reason cell is empty
- WHEN the checker parses the registry
- THEN it SHALL fail — every unmapped spec SHALL carry a non-empty reason

#### Scenario: The bijection holds on the change branch

- GIVEN the registry and `openspec/specs/*/spec.md` on this branch
- WHEN the checker cross-checks them
- THEN `mapped ∪ registered` SHALL equal the full spec set, the two sets SHALL be disjoint
- AND the registered set SHALL be exactly the 17 unmapped specs measured on this branch: `cli`,
  `codebook`, `data-quality`, `mcp-registration`, `mcp-server`, `metadata`, `packaging`,
  `parquet-conversion`, `pii-detection`, `prepare`, `profile`, `publish`, `render`, `repo-compliance`,
  `scan`, `semantic-type-inference`, `tool-config`

### Requirement: Checker exit contract and reported evidence (MC-06)

The checker SHALL exit **0** when every mapped spec is compliant and the registry bijection holds, and
**non-zero** when any check fails. On failure it SHALL report each offender on stdout/stderr with
enough context to act — the spec path, the row or scenario, and the reason — and it SHALL report the
full set of failures rather than aborting at the first one, so one run surfaces every problem. The
checker SHALL be deterministic across runs and SHALL NOT modify any repository file.

#### Scenario: A clean tree exits 0

- GIVEN the committed tree with every mapped spec compliant and the registry bijection holding
- WHEN the checker runs
- THEN it SHALL exit 0 with no failure report

#### Scenario: A violation exits non-zero and names the offender

- GIVEN a tree with at least one contract violation
- WHEN the checker runs
- THEN it SHALL exit non-zero
- AND the output SHALL identify the offending spec and the reason

#### Scenario: All failures are reported in one run

- GIVEN a tree with two independent violations
- WHEN the checker runs
- THEN both SHALL appear in the output of the same run

### Requirement: Gate integration — one step in the existing lint job (MC-07)

The checker SHALL be armed as **one step in the existing `lint` job** of
`.github/workflows/ci.yml` — no new job and no new matrix axis (D5). The step SHALL invoke the checker
directly and its **exit code SHALL gate the job**: a non-zero checker exit SHALL fail the `lint` job,
and a clean run SHALL contribute no new CI cost beyond the step itself. The checker SHALL be
runnable on a clean checkout with no network and no test execution.

#### Scenario: The lint job runs the checker

- GIVEN `.github/workflows/ci.yml`
- WHEN the `lint` job steps are inspected
- THEN exactly one step SHALL invoke the test-mapping checker
- AND no new job or matrix axis SHALL have been added for it

#### Scenario: A checker violation fails the lint job

- GIVEN the `lint` job with the checker step present
- WHEN the checker exits non-zero on a violating tree
- THEN the `lint` job SHALL fail

#### Scenario: The checker is green on a clean checkout

- GIVEN a clean checkout of the change branch
- WHEN the checker step runs
- THEN it SHALL exit 0 within the existing `lint` job (verify-phase runtime evidence)
