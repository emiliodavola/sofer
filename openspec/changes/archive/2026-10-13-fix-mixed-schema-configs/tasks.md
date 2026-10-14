# Tasks: fix-mixed-schema-configs

**Change** `2026-10-13-fix-mixed-schema-configs` (GitHub **#292**) · branch
`fix/292-mixed-schema-configs` from `dev@4ca823e` · store **hybrid**.

**One-line outcome:** `build_dataset_card` emits one `configs` entry (with its
own `dataset_info`) per column-signature group, never a merged config; every
`config_name` is a validated slug; a multi-group card carries no `default`; an
ungroupable corpus emits neither block.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real
red-then-green:

- **RED (measured):**
  `pytest tests/test_repo_compliance.py::TestMixedSchemaConfigs "tests/test_splits.py::TestValidateSplitMapping::test_group_aware_warning_names_configs"`
  → **6 failed, 1 passed**; the reproduction observed one merged `configs`
  entry, the ungroupable test observed the merged block, and
  `validate_split_mapping` rejected `config_names` (`TypeError`).
- **GREEN (measured):** the mixed class plus the full `TestValidateSplitMapping`
  contract → **17 passed**. Full suite on base `4ca823e`: **2096 passed, 8
  skipped** (the skips are environment-dependent: symlink/junction creation,
  `pwd` off POSIX, hatchling build backend; an earlier run of the same tree
  reported 2095/9). The parent re-runs on the rebased state.

**REFACTOR:** the config plan, group naming and `dataset_info` builder are
single shared helpers; no further refactor target.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: mixed corpus → one config per signature, matching `dataset_info`; single-signature → one config; slug never `pretty_name`; multi-group card has no `default` | done | `6 failed, 1 passed` (focused run) |
| T2 | RED: ungroupable corpus emits neither `configs` nor `dataset_info`; the dry-run warning no longer claims one merged split | done | the same RED run (`KeyError`/`AssertionError` + `TypeError`) |
| T3 | Grouping implementation over `schema` + `row_counts`, with origin aliases for the CSV-fallback path | done | `group_remotes_by_schema`, `schema_config_plan` |
| T4 | `config_name` slug + identifier validation | done | `_slugify_config_name`, `_config_name_for_group`, `_name_groups` |
| T5 | D4 applied to `default` | done | single-group `default: True`; multi-group absent |
| T6 | Dry-run warning becomes true and actionable for both card shapes | done | `validate_split_mapping(remotes)` states both outcomes + 1 test; the `config_names` draft was removed by the parent before delivery |
| T7 | `repo-compliance` spec delta (RC-Universal-Card + RC-R23) | done | canonical spec updated; `check_test_mapping.py` exit 0 |
| T8 | README / README_ES | done (n/a) | the card's `configs` block is not documented in either README; no documented section changed |
| T9 | Gates: full suite, coverage ≥ 90, ruff/format/mypy/pyright, `check_test_mapping.py` | done | see the archive report |
| T10 | Commit + push + PR | **withheld by the parent** — the parent rebases onto the new `dev`, commits and opens the PR | this branch's working tree only |

---

## Constraints honoured

- **No `# pragma: no cover` anywhere.**
- **`quality.py` and `publish.py` untouched** — frozen for this batch.
- **`prepare.py` untouched** — no rule-14 coverage obligation arises.
- Five new defaults live in `config._DEFAULTS` **and** `pyproject.toml`
  `[tool.sofer]` (the parity guard requires both).
