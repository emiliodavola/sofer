# Delta for mcp-server

> **Change** `2026-10-16-feat-agent-metadata-flow` (issue **#288**) · branch
> `feat/288-agent-metadata-flow` from `dev@6786ba1` · store **hybrid**.
>
> **One added requirement.** The metadata step joins the advertised chain, and the pipeline warns while
> `[meta]` still carries template placeholders.
>
> **Rule-6 resolution.** `mcp-server` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the scenarios below carry their evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit.

## ADDED Requirements

### Requirement: The metadata step is in the agent-facing surface (MSP-META-01)

The canonical chain the server advertises SHALL name the metadata step — filling `[meta]`
`description`, `license`, `source` and `tags` — between bootstrap and Phase 1, because an MCP consumer
has no source of truth other than the descriptions and envelopes it receives, and a required step that
is absent from them cannot be inferred (issue #288).

`sofer_validate`'s description SHALL require `[meta] description/license/source/tags filled (no
placeholders)` and `sofer_prepare`'s SHALL require that validation passed with no placeholder warning;
the workflow registry SHALL carry the same requirement for `sofer_validate`. `sofer_init`'s
continuation SHALL name filling `[meta]` before registering files.

`sofer_validate` — and the pre-prepare run, which shares the validator — SHALL emit one **warning** per
`[meta]` scalar field (`description`, `license`, `source`) that is empty or begins with one of the
`meta_placeholder_prefixes` values (`[tool.sofer]`, case-insensitive), plus one warning for placeholder
`tags`. The force SHALL be a warning and SHALL NOT change the exit code or `ValidationReport.passed`: a
failure would break every existing config that still carries a placeholder, which is a contract change
rather than a fix (maintainer decision D3).

#### Scenario: The metadata step is in the chain the agent reads — issue #288

- GIVEN the server is built
- WHEN its instructions and `tools/list` descriptions are read
- THEN the instructions SHALL name the metadata step before Phase 1
- AND `sofer_validate`'s description SHALL require `[meta] description/license/source/tags filled (no placeholders)`
- AND `sofer_init`'s continuation SHALL name filling `[meta]`

**Evidence:** `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_server_instructions_name_the_metadata_step`, `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_validate_requires_filled_meta`, `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_init_next_points_at_the_metadata_step`, `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_the_workflow_registry_carries_the_requirement`

#### Scenario: A placeholder warns without failing the run — issue #288

- GIVEN a dataset TOML whose `[meta]` values are the `sofer init` template's placeholders
- WHEN `sofer_validate` runs (or the pre-prepare validation does)
- THEN the report SHALL carry one warning per offending field, naming it
- AND `ValidationReport.passed` SHALL remain `True` and the exit code SHALL be unchanged

**Evidence:** `test: tests/test_checks.py::TestMetaPlaceholderGate::test_each_placeholder_field_warns`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_the_warning_reaches_the_report_and_keeps_passed_true`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_the_warning_is_visible_in_the_printed_summary`

#### Scenario: Only a prefix marks a placeholder — issue #288

- GIVEN a value that contains a prefix but does not start with one, and one that does
- WHEN the gate runs
- THEN only the value beginning with a prefix SHALL be reported
- AND the match SHALL be case-insensitive
- AND an empty `tags` list SHALL NOT warn, because there is no value to replace

**Evidence:** `test: tests/test_checks.py::TestMetaPlaceholderGate::test_a_real_value_merely_containing_a_prefix_is_fine`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_the_match_is_case_insensitive`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_an_empty_value_warns_for_the_three_scalars`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_an_example_prefixed_source_is_flagged`

#### Scenario: The prefixes are configuration — issue #288

- GIVEN `[tool.sofer] meta_placeholder_prefixes` is changed
- WHEN the gate runs
- THEN it SHALL use the configured values, not a literal

**Evidence:** `test: tests/test_checks.py::TestMetaPlaceholderGate::test_prefixes_are_config_owned`
