# Tasks: feat-mcp-hermes-adapter

**Change** `2026-10-09-feat-mcp-hermes-adapter` (GitHub **#272**) · branch
`feat/272-mcp-hermes-adapter` from `dev@90ee69f` · store **hybrid** — this file plus the Engram
mirror.

**Inputs read this phase, directly:** `proposal.md` and `design.md` of this change.

**One-line outcome:** `sofer mcp add --agent hermes` writes the contained `sofer` entry into the
`config.yaml` Hermes actually reads, splicing it in so the rest of the document survives, and names
the single-scope substitution instead of refusing it.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`; the change adds a capability, and the carriers are
real red-then-green runs: the new tests fail before their implementation and pass after, per work
unit, with the counts recorded below. No REFACTOR target beyond the documented splice cases.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Proposal, design, spec deltas, tasks and the ODD feature document | done | this folder + `odd/tasks/mcp-hermes-adapter.md` |
| T2 | RED: the YAML write contract (`tests/test_yaml_edit.py`, the `_infer_fmt` / `read_config` / `atomic_write` cases) | pending | |
| T3 | GREEN: `src/sofer/_yaml.py` + the `yaml` branches of `_infer_fmt`, `read_config`, `atomic_write` | pending | |
| T4 | RED: the adapter contract (`TestHermesAdapter`: registry row, `AGENT_NAMES`, `HERMES_HOME`, entry shape, single scope, native refusal, `--agent all` = five, help text) | pending | |
| T5 | GREEN: the `hermes` row, `project_scope`, `resolve_config_path`, `single_scope_note`, the CLI help and the note printing | pending | |
| T6 | Rule-14 gate: `cli.py` at 100.00%, no pragma | pending | |
| T7 | `README.md` + `README_ES.md` (rule 13) and the `CONTRIBUTING.md` architecture note | pending | |
| T8 | Full gate set (pytest, ruff + format, mypy, pyright, coverage, `check_test_mapping.py`) | pending | |
| T9 | One work-unit commit per unit, branch first, Conventional Commit messages | pending | |
| T10 | Archive the change **inside this PR** (rule 15) with a report true of the artifact | pending | |
| T11 | Push and PR against `dev` | pending | |

---

## Constraints honoured

- No hardcoded values (rule 1): every new name is a module constant or an adapter field; the two new
  literals (`"yaml"`, `project_scope`) join the existing single-source registry.
- Docstrings mandatory (rule 2): `_yaml.py` gets a module docstring and every public function one;
  the modified functions document their new branch and the pre-write contract.
- Config is read, not bypassed (rule 3): the YAML branch consumes the same merged document the JSON
  and TOML branches consume; no second source of truth for the entry.
- No duplicated logic (rule 4): the splice is one pure function used by `add` and `remove`; the
  `${KEY}` form reuses the existing `refs_braced` mode instead of adding a fourth env mode.
- Tests match specs (rule 6): no Test Mapping row (declared-backlog specs) and no registry edit.
- CLI help text accuracy (rule 7): the enumeration, the env sentence and the new format/scope
  sentences change in the same commit as the behavior.
- README / README_ES sync (rule 13): both files change in one commit, technical content in English.
- CLI-core coverage (rule 14): the new `cli.py` lines are exercised in both handlers; no pragma.
- Archive placement (rule 15): the change is archived inside this PR.
