# Tasks: fix-card-config-group-warning

**Change** `2026-10-16-fix-card-config-group-warning` (GitHub **#303**) · branch
`fix/303-card-config-group-warning` from `dev@6786ba1` · store **hybrid**.

**Inputs read this phase, directly:** `odd/tasks/card-config-group-warning.md` (specification of
record), `design.md` and `proposal.md` of this change, and
`openspec/changes/archive/2026-10-13-fix-mixed-schema-configs/design.md` §3.3 + R2 — the decision that
removed the draft surface this change restores, now with a production caller.

**One-line outcome:** the dry-run default-load warning names the configs the card emitted, so the
`load_dataset(repo, name=...)` instruction is actionable without opening the frontmatter.

---

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Branch off `dev`; feature doc | — | done | `fix/303-card-config-group-warning`; `odd/tasks/card-config-group-warning.md` |
| T2 | `config.py` + `pyproject.toml`: `card_config_group_warn_limit`, validated positive | S4 | done | `tests/test_config.py` parity guard green |
| T3 | `repo_compliance.card_config_names()` — read the emitted names back from the card | S4 | done | `TestCardConfigNames` (10 tests) |
| T4 | `validate_split_mapping(remotes, config_names, warn_limit)` + `_config_name_hint()` | S4 | done | `TestConfigNameHintInWarning` (7 tests) |
| T5 | `publish._print_split_mapping_validation()` + both call sites | S4 | done | `TestSplitMappingValidationNamesConfigsNext` (2 tests) |
| T6 | `repo-compliance` spec delta + canonical S4 clause | S4 | done | `specs/repo-compliance/spec.md` of this change; `openspec/specs/repo-compliance/spec.md` |
| T7 | Gates: full suite, `publish.py` per-file 100.00%, ruff/format/mypy/pyright, test-mapping checker | — | done | see the close-out |
| T8 | Work-unit commits on the branch (no push, no PR) | — | done | see the archive report |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | 2185 passed, 9 skipped |
| `publish.py` 100.00% (rule 14) | 100% |
| `cli.py` / `scanner.py` / `prepare.py` | 100% each |
| TOTAL floor | 94% |
| ruff / format / mypy / pyright | clean |
| Test-mapping contract | `OK` |

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests, so
the new tests did not themselves observe RED. What was actually observed is recorded in full in
`design.md` §4: the `57 failed` RED of an implementation pass that dropped two body lines of
`validate_split_mapping`, the three findings in the first run of the new tests, and the
`480 passed` GREEN.
