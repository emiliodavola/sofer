# Tasks: feat-mcp-hermes-adapter

**Change** `2026-10-09-feat-mcp-hermes-adapter` (GitHub **#272**) · branch
`feat/272-mcp-hermes-adapter` from `dev@90ee69f` · store **hybrid** — this file plus the Engram
mirror.

**Inputs read this phase, directly:** `proposal.md` and `design.md` of this change.

**One-line outcome:** `sofer mcp add --agent hermes` writes the contained `sofer` entry into the
`config.yaml` Hermes actually reads, splicing it in so the rest of the document survives byte-for-byte,
and names the single-scope substitution instead of refusing it.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`; the change adds a capability, and the carriers are
real red-then-green runs, per work unit, with the counts recorded below. No REFACTOR target beyond the
documented splice cases and the line-ending fix the independent verifier forced.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Proposal, design, spec deltas, tasks and the ODD feature document | done | this folder + `odd/tasks/mcp-hermes-adapter.md`; commit `621ed37` |
| T2 | RED: the YAML write contract (`tests/test_yaml_edit.py`, the `_infer_fmt` / `read_config` / `atomic_write` cases) | done | `uv run pytest tests/test_yaml_edit.py tests/test_mcp_registration.py -q --continue-on-collection-errors` → `6 failed, 125 passed, 2 skipped, 1 error` (the error is the missing `_yaml` module at collection) |
| T3 | GREEN: `src/sofer/_yaml.py` + the `yaml` branches of `_infer_fmt`, `read_config`, `atomic_write` | done | same files → `153 passed, 2 skipped`; commit `c23a169` |
| T4 | RED: the adapter contract (`TestHermesAdapter`: registry row, `AGENT_NAMES`, `HERMES_HOME`, entry shape, single scope, native refusal, `--agent all` = five, help text) | done | `uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q` → `28 failed, 316 passed, 3 skipped` |
| T5 | GREEN: the `hermes` row, `project_scope`, `resolve_config_path`, `single_scope_note`, the CLI help and the note printing | done | same files → `344 passed, 3 skipped`; commit `9f0b559` |
| T6 | Rule-14 gate: `cli.py` at 100.00%, no pragma | done | `coverage report --include=src/sofer/cli.py --fail-under=100 -m` → `cli 637 0 194 0 100%`; `scripts/check_core_coverage.sh` exit 0; pragma count 0 |
| T7 | `README.md` + `README_ES.md` (rule 13) and the `CONTRIBUTING.md` architecture note | done | 36 `##`/`###` headings in the same order in both READMEs with identical technical content; both renamed anchors resolve; commit `9f0b559` |
| T8 | Full gate set (pytest, ruff + format, mypy, pyright, coverage, `check_test_mapping.py`) | done | `2088 passed, 8 skipped`; ruff check/format clean; mypy 37 files clean; pyright 0 errors; TOTAL 94%; the four rule-14 rows at 100%; `check_test_mapping.py` exit 0 |
| T9 | One work-unit commit per unit, branch first, Conventional Commit messages | done | `621ed37`, `c23a169`, `9f0b559`, `efb439b`, `0999eee`, plus this archive commit |
| T10 | Fix the line-ending defect the independent verifier falsified, with tests | done | RED `3 failed, 172 passed, 2 skipped` → GREEN `175 passed, 2 skipped`; commit `efb439b`; verifier re-ran the probes and closed the finding |
| T11 | Archive the change **inside this PR** (rule 15) with a report true of the artifact | done | this folder under `openspec/changes/archive/` + `archive-report.md` |
| T12 | Push the branch and open the PR against `dev` | pending | closed by the follow-up record commit inside the same PR — the PR cannot be cited before the commit that archives the change exists |

---

## Constraints honoured

- No hardcoded values (rule 1): every new name is a module constant or an adapter field
  (`_SINGLE_SCOPE_NOTE`, `_YAML_INDENT`, `_YAML_WIDTH`, `project_scope`); the two new literals
  (`"yaml"`, `project_scope`) join the existing single-source registry.
- Docstrings mandatory (rule 2): `_yaml.py` has a module docstring and a docstring on every public
  function; the modified functions document their new branch and the pre-write contract.
- Config is read, not bypassed (rule 3): the YAML branch consumes the same merged document the JSON
  and TOML branches consume; the adapter table stays the only source of agent facts.
- No duplicated logic (rule 4): the splice is one pure function used by `add` and `remove`; the
  `${KEY}` form reuses the existing `refs_braced` mode instead of adding a fourth env mode.
- Tests match specs (rule 6): no Test Mapping row (declared-backlog specs) and no registry edit.
- CLI help text accuracy (rule 7): the enumeration, the env sentence and the new format/scope
  sentences changed in the same commit as the behavior.
- README / README_ES sync (rule 13): both files changed in one commit, technical content in English.
- CLI-core coverage (rule 14): the new `cli.py` lines are exercised in both handlers; no pragma.
- Archive placement (rule 15): the change is archived inside this PR.
