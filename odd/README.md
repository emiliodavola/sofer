# odd/ — harness task tracking

This directory is **task tracking for the development harness**, not project source. It holds one
file per substantial feature under `odd/tasks/`, recording the task list, the decisions taken before
implementation, and the evidence that closed each task — the durable counterpart to the session's
visible todo list.

Boundaries:

- **Not part of the shipped package.** Nothing under `odd/` is imported, packaged or executed by
  `sofer`. The module inventory of `AGENTS.md` rule 10 is `ls src/sofer/`, and this directory sits
  outside it.
- **Not a substitute for the SDD record.** The durable contract lives in `openspec/` — the specs
  under `openspec/specs/`, and the change folder under `openspec/changes/`. These files are the
  working plan that produced it, kept because the reasoning behind a change is worth more than the
  change.
- **Not a gate.** No test, guard or CI job reads this directory.

A feature file is written before the first source edit and updated as tasks close; each closed task
records its commit identity as evidence.
