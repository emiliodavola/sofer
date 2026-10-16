# Tasks: feat-agent-metadata-flow

**Change** `2026-10-16-feat-agent-metadata-flow` (GitHub **#288**) · branch
`feat/288-agent-metadata-flow` from `dev@6786ba1` · store **hybrid**.

**Inputs read this phase, directly:** `odd/tasks/agent-metadata-flow.md` (specification of record),
`design.md` and `proposal.md` of this change, and the maintainer's decision D3 (warn, not fail).

**One-line outcome:** the metadata step is in the chain the agent reads, and `sofer_validate` warns
while `[meta]` still carries template placeholders — without ever failing the run.

---

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Branch off `dev`; feature doc | — | done | `feat/288-agent-metadata-flow` |
| T2 | `config.py` + `pyproject.toml`: `meta_placeholder_prefixes`, validated | D2 | done | `TestMetaPlaceholderGate::test_prefixes_are_config_owned`; parity guard green |
| T3 | `checks.py`: `meta_placeholder_warnings()` + `_looks_like_placeholder()` | S2 S3 | done | `TestMetaPlaceholderGate` (9 tests) |
| T4 | Wire it into `DatasetValidator.run_all()`, covering CLI validate, the MCP tool and the pre-prepare run with one call site | S2 | done | `test_the_warning_reaches_the_report_and_keeps_passed_true`, `test_the_warning_is_visible_in_the_printed_summary` |
| T5 | `_PHASED_INSTRUCTIONS`: the metadata step, before Phase 1; `Requires:` on validate/prepare/init | S1 | done | `TestMetadataStepInTheAdvertisedChain` (6 tests) |
| T6 | `workflow.py`: the registry requirement for `sofer_validate` | S1 | done | `test_the_workflow_registry_carries_the_requirement` |
| T7 | README + README_ES: who fills `[meta]` (rule 13) | S1 | done | both files |
| T8 | `mcp-server` spec delta + canonical MSP-META-01 | S1 S2 S3 | done | `specs/mcp-server/spec.md` of this change; `openspec/specs/mcp-server/spec.md` |
| T9 | Gates: full suite, per-file 100.00% on the four core modules, ruff/format/mypy/pyright, test-mapping checker | — | done | see the close-out |
| T10 | Work-unit commits on the branch (no push, no PR) | — | done | see the archive report |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | 2170 passed, 9 skipped |
| `cli.py` / `scanner.py` / `prepare.py` / `publish.py` 100.00% (rule 14) | 100% each |
| TOTAL floor | 94% |
| ruff / format / mypy / pyright | clean |
| Test-mapping contract | `OK` |

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests. The
measured sequence — `140 passed` before, `5 failed` on the first run of the new tests with all five being
my own wrong premises, one ordering defect in the change found by the surface test, then `2170 passed` —
is recorded in full in `design.md` §5.
