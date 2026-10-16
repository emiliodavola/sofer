# Delta for repo-compliance

> **Change** `2026-10-16-fix-card-config-group-warning` (issue **#303**) · branch
> `fix/303-card-config-group-warning` from `dev@6786ba1` · store **hybrid**.
>
> **One modified clause.** The default-load warning names the config names the card actually emitted,
> instead of leaving `name='<config>'` for the reader to resolve by opening the frontmatter.
>
> **Rule-6 resolution.** `repo-compliance` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the scenarios below carry their evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit.

## MODIFIED Requirements

### RC-Universal-Card — "Actionable warning (S4)"

**Clause changed.** `validate_split_mapping(remotes, config_names=None, warn_limit=None)` SHALL warn,
for a multi-file corpus with no split keywords, that the card groups those files by column schema —
every file into one `train` split for a single-config card, and one table at a time for a multi-config
card. The clause SHALL NOT claim a single merged split in general, because the card no longer emits
one.

When `config_names` is supplied, the warning SHALL name those configs (`name='<first>'`,
`name='<second>'`, …) instead of emitting the unresolvable placeholder `name='<config>'`: the names are
computed inside `build_dataset_card`, which returns only the card text, so a caller that prints the
warning has no other way to name them, and an MCP caller receives the warning in the tool result
without the card at all. The named list SHALL be capped at `card_config_group_warn_limit`
(`[tool.sofer]`, default 5) with an `... and N more` suffix, so a corpus with many column-signature
groups still gets a readable instruction. `config_names=None` or `[]` SHALL keep the placeholder form,
which is the only case a caller cannot name them.

`repo_compliance.card_config_names(build_dir)` SHALL return the `configs[].config_name` values read
back from the built card's YAML frontmatter — the names that shipped, never a second derivation that
could disagree with the artifact — and SHALL return `[]` for a card that is absent, unreadable,
unfenced, malformed, has no `configs` block, or does not name every entry with a non-empty string.

#### Scenario: The dry-run warning names the emitted configs — issue #303

- GIVEN a built package whose card emitted two configs, `persona` and `hogar`
- WHEN `sofer publish --dry-run` prints the split-mapping validation for a multi-file corpus with no
  split keywords
- THEN the default-load warning SHALL name `name='persona'` and `name='hogar'`
- AND it SHALL NOT print `name='<config>'`

**Evidence:** `test: tests/test_repo_compliance.py::TestCardConfigNames::test_reads_the_names_a_real_card_emitted`, `test: tests/test_splits.py::TestConfigNameHintInWarning::test_names_the_configs_when_supplied`, `test: tests/test_publish.py::TestSplitMappingValidationNamesConfigsNext::test_print_mapping_validation_passes_the_names_through`

#### Scenario: No built card keeps the placeholder form

- GIVEN no `README.md` in the package directory (or a card with no `configs` block)
- WHEN the split-mapping validation runs
- THEN the warning SHALL state both card shapes and keep `name='<config>'`
- AND `card_config_names` SHALL return an empty list

**Evidence:** `test: tests/test_splits.py::TestConfigNameHintInWarning::test_falls_back_to_the_placeholder_without_names`, `test: tests/test_splits.py::TestConfigNameHintInWarning::test_empty_name_list_is_the_placeholder_form`, `test: tests/test_publish.py::TestSplitMappingValidationNamesConfigsNext::test_print_mapping_validation_without_names_keeps_the_placeholder`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_missing_card_returns_empty`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_valid_frontmatter_without_configs_returns_empty`

#### Scenario: A long config list is elided at the configured cap

- GIVEN a card that emitted more configs than `card_config_group_warn_limit`
- WHEN the warning is printed
- THEN it SHALL list exactly the first `card_config_group_warn_limit` names
- AND it SHALL end the list with `... and N more`, where N counts the elided names

**Evidence:** `test: tests/test_splits.py::TestConfigNameHintInWarning::test_elides_past_the_configured_limit`, `test: tests/test_splits.py::TestConfigNameHintInWarning::test_default_limit_is_read_from_config`, `test: tests/test_splits.py::TestConfigNameHintInWarning::test_no_ellipsis_when_every_name_fits`

#### Scenario: A card that cannot name its configs yields no names, never a guess

- GIVEN a `README.md` that is unfenced, malformed, not a mapping, has a non-list `configs`, or whose
  entries lack a non-empty string `config_name`
- WHEN `card_config_names` reads it
- THEN it SHALL return an empty list

**Evidence:** `test: tests/test_repo_compliance.py::TestCardConfigNames::test_unfenced_card_returns_empty`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_prose_before_the_fence_returns_empty`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_malformed_yaml_returns_empty`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_non_mapping_frontmatter_returns_empty`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_entry_without_a_string_config_name_returns_empty`, `test: tests/test_repo_compliance.py::TestCardConfigNames::test_configs_that_is_not_a_list_returns_empty`

#### Scenario: A single-config card names its one config

- GIVEN a corpus whose files share one column signature
- WHEN `card_config_names` reads the built card
- THEN it SHALL return exactly that one config's name

**Evidence:** `test: tests/test_repo_compliance.py::TestCardConfigNames::test_single_config_card_names_its_one_config`
