# Delta for repo-compliance

> **Change** `2026-10-16-feat-curation-rationale-key` (issue **#324**) · branch
> `feat/324-curation-rationale-key` from `dev@5249be6` · store **hybrid**.
>
> **One modified clause.** `### Curation Rationale` gains a free-text `[meta]` key in front of its
> existing file path. The placeholder rule and the five #291 keys are unchanged.
>
> **Rule-6 resolution.** `repo-compliance` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the scenarios below carry their evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit.

## MODIFIED Requirements

### Requirement: Card sections with a dedicated key (issue #291, amended by #324)

`repository`, `direct_use`, `out_of_scope_use`, `bias_risks_limitations` and `contact` SHALL each fill
the card section they name, and SHALL fall back to that section's placeholder when empty or
whitespace-only — a value that is only whitespace is not content. `repository` SHALL fall back to
`source` before the placeholder, because `source` is conventionally the organisation and is the best
available value for a repo link. Curation Rationale is the one section whose fill paths are governed by
the clause below instead, because it had a file path and now also has a key.

`### Curation Rationale` SHALL be filled by `[meta] curation_rationale` when that key holds
non-whitespace content, otherwise by the resolved content of the file `[meta] study_design` points at,
otherwise by that section's placeholder. The key SHALL win over the file, so declaring both is
unambiguous. When `curation_rationale` is absent the branch taken SHALL be the pre-#324 one unchanged:
a whitespace-only `study_design` file keeps the outcome it had — an empty section, not the placeholder
— because the caller decided there was a file. The `"[More Information Needed]"` sentinel SHALL come
from one module constant, so the sentinel the card emits and the value the tests assert cannot drift.

#### Scenario: A declared key fills the section with no file — issue #324

- GIVEN a config declaring `[meta] curation_rationale` and no `study_design`
- WHEN `build_dataset_card()` runs
- THEN the section body SHALL carry the declared text
- AND it SHALL NOT carry `[More Information Needed]`

**Evidence:** `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_the_key_fills_the_section_without_a_file`, `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_an_undeclared_study_design_with_a_key_is_enough`

#### Scenario: The key wins over the file — issue #324 §"Proposed solution" 1

- GIVEN a config declaring both `curation_rationale` and `study_design`, with a resolved file content
- WHEN the card is generated
- THEN the section SHALL carry the key's text
- AND the file's content SHALL NOT appear in that section

**Evidence:** `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_the_key_wins_over_the_study_design_file`

#### Scenario: A whitespace-only key is not content — issue #324 §"Proposed solution" 1

- GIVEN a whitespace-only `curation_rationale` and a resolved file content
- WHEN the card is generated
- THEN the section SHALL carry the file's content
- AND with no file resolved it SHALL carry the placeholder

**Evidence:** `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_a_whitespace_only_key_falls_back_to_the_file`, `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_a_whitespace_only_key_alone_keeps_the_sentinel`

#### Scenario: The pre-#324 file path is unchanged — issue #291 preserved

- GIVEN a config declaring `study_design` and no `curation_rationale`
- WHEN the card is generated with the resolved file content
- THEN the section SHALL carry that content exactly as it did before this change
- AND with neither source declared it SHALL carry the placeholder

**Evidence:** `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_declaring_study_design_alone_is_unchanged`, `test: tests/test_repo_compliance.py::TestCurationRationaleKey::test_neither_source_keeps_the_sentinel`, `test: tests/test_repo_compliance.py::TestStudyDesign`

#### Scenario: The key is read from the TOML — issue #324 §"Proposed solution" 1

- GIVEN a dataset TOML declaring `curation_rationale` under `[meta]`, as a multi-line string
- WHEN `DatasetConfig.from_toml()` parses it
- THEN the field SHALL carry the declared value
- AND an absent key SHALL default to empty

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeysFromToml::test_meta_keys_are_parsed`, `test: tests/test_repo_compliance.py::TestCardSectionKeysFromToml::test_absent_meta_keys_default_to_empty`

#### Scenario: One sentinel constant at four sites — issue #324 §"Proposed solution" 1

- GIVEN `build_dataset_card()`'s body
- WHEN it is inspected
- THEN it SHALL contain no inline `"[More Information Needed]"` literal
- AND it SHALL reference `_MORE_INFO` exactly four times, as it did before this change

**Evidence:** `test: tests/test_repo_compliance.py::TestCardSectionKeys::test_the_sentinel_is_the_single_shared_constant`
