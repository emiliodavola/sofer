# Delta for repo-compliance

> **Change** `2026-10-16-feat-card-section-keys` (issue **#291**) · branch
> `feat/291-card-section-keys` from `dev@6786ba1` · store **hybrid**.
>
> **One added clause.** Five card sections gain a `[meta]` key, so a fully-filled config stops shipping
> a placeholder card. The placeholder rule itself is unchanged.
>
> **Rule-6 resolution.** `repo-compliance` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the scenarios below carry their evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit.

## ADDED Requirements

### RC-Universal-Card — "Card sections with a dedicated key (issue #291)"

`repository`, `direct_use`, `out_of_scope_use`, `bias_risks_limitations` and `contact` SHALL each fill
the card section they name, and SHALL fall back to that section's placeholder when empty or
whitespace-only — a value that is only whitespace is not content. `repository` SHALL fall back to
`source` before the placeholder, because `source` is conventionally the organisation and is the best
available value for a repo link. `### Curation Rationale` SHALL continue to be filled by
`[meta] study_design`, whose content the caller resolves; it has no free-text key of its own. The
`"[More Information Needed]"` sentinel SHALL come from one module constant, so the sentinel the card
emits and the value the tests assert cannot drift.

#### Scenario: A fully-filled config emits no sentinel — issue #291

- GIVEN a DatasetConfig with every ROTW field set — description, license, source, tags, language,
  collection_method, citation, and the five new keys — plus a `study_design` file
- WHEN `build_dataset_card()` runs
- THEN the card SHALL contain no `[More Information Needed]` and no `[Not specified]`
- AND each new key's value SHALL appear in its own section

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_a_fully_filled_config_emits_no_sentinel`, `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_each_key_fills_its_own_section`

#### Scenario: An unset key keeps the placeholder — issue #291

- GIVEN a config with none of the five keys set
- WHEN the card is generated
- THEN the four `[More Information Needed]` sections SHALL still carry that placeholder
- AND a whitespace-only value SHALL behave exactly like an unset one

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_unset_keys_keep_their_sentinel`, `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_whitespace_only_values_keep_their_sentinel`

#### Scenario: The repository falls back to the source — issue #291 §"Proposed solution" 3

- GIVEN a config with `source` set and no `repository`
- WHEN the card is generated
- THEN `- **Repository:**` SHALL carry the source value
- AND a declared `repository` SHALL take precedence over it

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_repository_falls_back_to_the_source`, `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_a_declared_repository_beats_the_source`

#### Scenario: Curation Rationale is filled by study_design, and only by it — issue #291

- GIVEN a config with the five new keys set and no `study_design`
- WHEN the card is generated
- THEN exactly one `[More Information Needed]` SHALL remain, in `### Curation Rationale`

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_curation_rationale_needs_study_design`

#### Scenario: The keys are read from the TOML — issue #291

- GIVEN a dataset TOML declaring the five keys under `[meta]`, one of them a multi-line string
- WHEN `DatasetConfig.from_toml()` parses it
- THEN each field SHALL carry the declared value
- AND an absent key SHALL default to empty

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeysFromToml::test_meta_keys_are_parsed`, `test: tests/test_repo_compliance.py::TestCardSectionKeysFromToml::test_absent_meta_keys_default_to_empty`

#### Scenario: One sentinel constant, not four literals — issue #291

- GIVEN `build_dataset_card()`'s body
- WHEN it is inspected
- THEN it SHALL contain no inline `"[More Information Needed]"` literal
- AND it SHALL reference `_MORE_INFO` once per sentinel site

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_the_sentinel_is_the_single_shared_constant`
