# odd/ — durable task records for ODD work

This directory holds optional durable task records for **Organic Driven Development (ODD)**, the
workflow defined in `AGENTS.md` → Workflow. Nothing here is project source: it is working context,
not product, and nothing under `odd/` is imported, packaged or executed by `sofer`.

## ODD in one paragraph

ODD is the workflow for new work: **authorize** (analysis and review stay read-only unless
implementation is requested), **explore proportionately** (verify against the code and docs before
writing), **implement** the smallest coherent change, and **verify** with the applicable gates,
reporting actual results and any unavailable checks. Small changes go directly; the issue and PR are
the default record for scope, decisions, verification and delivery.

## When a task file is justified

Create a file under `odd/tasks/` only when essential decisions, dependencies or unfinished work
cannot live in the issue/PR and would otherwise be lost when resuming across sessions or handing work
over. State that continuity need before creating the file. Do not duplicate issue/PR content by
routine, and do not treat a task file as a required dossier for every change.

The existing files are historical delivery records: keep the decisions, task lists and commit
evidence they carry, and do not rewrite them. A closed task records its commit identity as evidence.

## Boundaries

- **Not part of the shipped package.** Nothing here participates in the `sofer` runtime. The module
  inventory is whatever `ls src/sofer/` reports (AGENTS.md rule 10), and this directory sits outside
  it.
- **Not a gate.** No test, guard or CI job reads this directory.
- **OpenSpec is the record of existing contracts, not an ODD requirement.** The specs under
  `openspec/specs/`, their `## Test Mapping` tables, `openspec/test-mapping-registry.md`, the
  archived changes and `scripts/check_test_mapping.py` remain in force. When an authorized change
  alters an existing contract, update that contract in place. New ODD work does not need a proposal,
  design, change folder or archive report, and does not need a parallel ODD and SDD dossier.
