# Delta for data-quality

> **Change** `2026-10-14-fix-bounded-quality-scan` (issue **#290**) · branch
> `fix/290-bounded-quality-scan` from `dev@4ca823e` · store **hybrid**.
>
> **One bounded-scan contract and three modifications.** The validator's per-row memory becomes
> independent of dataset size, and the full-scan decision stops being a side effect of severity: it
> becomes a config-owned tri-state that only the checks which genuinely need every row can trigger.
>
> **Rule-6 resolution.** `data-quality` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the scenarios below carry their evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit. A
> `verify:` class is used only where no repository test can prove the clause.

## MODIFIED Requirements

### 4.1 Duplicates — row-hash based, streaming

**Clause added:** The system MUST cap the number of distinct row hashes it tracks at
`quality_max_dup_tracking` (`[tool.sofer]`, default 1 000 000). Once the cap is reached, the system
MUST stop inserting new hashes and MUST NOT evict a tracked hash; a `duplicates` finding produced
under the cap SHALL be marked `partial` and SHALL name the cap in its message. Duplicate pairs among
already-tracked hashes MUST continue to be reported.

#### Scenario: Duplicate tracking cap is reached

- GIVEN a CSV whose distinct rows exceed `quality_max_dup_tracking`
- WHEN `QualityValidator.run()` completes
- THEN the hash table SHALL hold at most `quality_max_dup_tracking` entries
- AND a `duplicates` finding SHALL be marked `partial`
- AND its message SHALL name the cap

**Evidence:** `test: tests/test_quality.py::TestDuplicateTrackingCap::test_tracking_dict_never_exceeds_the_cap`, `test: tests/test_quality.py::TestDuplicateTrackingCap::test_cap_marks_partial_and_names_the_cap`, `test: tests/test_quality.py::TestDuplicateTrackingCap::test_cap_without_duplicates_reports_partial`

### 4.3 Empty columns — all values empty/NA/null across sample

**Clause changed:** The `empty_columns` bookkeeping SHALL be a per-column "seen non-empty" boolean
keyed `file::col`, not a distinct-value set. A column SHALL be reported empty when it was never seen
with a non-empty value. Memory for this accumulator SHALL be O(columns), independent of the row
count.

#### Scenario: Populated column bookkeeping is a boolean

- GIVEN a column with several distinct non-empty values
- WHEN `QualityValidator.run()` completes
- THEN the per-column state SHALL be a single `True` flag, not a set of values
- AND its size SHALL NOT grow with the number of distinct values

**Evidence:** `test: tests/test_quality.py::TestColNonemptyBoolean::test_seen_flag_is_a_bool_not_a_value_set`, `test: tests/test_quality.py::TestColNonemptyBoolean::test_memory_is_o_columns_not_o_rows`, `test: tests/test_quality.py::TestColNonemptyBoolean::test_empty_column_stays_false_and_is_reported`

### 5.3 QualityResult dataclass

**Clause added:** `QualityResult.partial` SHALL be `True` when the finding's evidence is not a
complete view: when the scan was sampled and the finding is a streaming `warn` finding; when the scan
was sampled under `quality_full_scan = "never"` and the finding is streaming; or when an accumulator
was capped (the duplicate-tracking cap). A fixed-size probe finding (`encoding_validation`) SHALL
NEVER be marked `partial` by sampling.

**Evidence:** `test: tests/test_quality.py::TestFullFileCoverage::test_warn_check_partial_when_max_sample_applied`, `test: tests/test_quality.py::TestFullScanPolicy::test_never_honours_max_sample_with_fail_check`, `test: tests/test_quality.py::TestFullScanPolicy::test_encoding_probe_finding_is_never_partial`

## ADDED Requirements

### 4.13 Explicit full-scan policy

`QualityValidator` SHALL decide whether to read every row from an explicit, config-owned policy
rather than from severity alone. The policy is tri-state (`quality_full_scan`, `[tool.sofer]`,
default `"auto"`; an optional per-dataset `[quality] full_scan` table value wins over it when set):

- `auto` — a full scan is forced only when an active `fail`-severity check is named in
  `quality_row_requiring_checks` (`[tool.sofer]`, default `["corrupt_records"]`); otherwise the
  `[quality] max_sample` applies.
- `always` — every eligible file is read in full.
- `never` — `[quality] max_sample` is honoured even with a `fail` check active.

A fixed-size probe such as `encoding_validation` (8 KB) MUST NOT force a full scan. The validator
SHALL remain single-pass; per-check multi-pass scanning is explicitly out of scope.

#### Scenario: Encoding probe does not force the full scan

- GIVEN `corrupt_records` at `warn`, `encoding_validation` at `fail`, and a corrupt row beyond `max_sample`
- WHEN `QualityValidator.run()` executes under the default `auto` policy
- THEN the corrupt row SHALL NOT be detected (the scan was sampled)

**Evidence:** `test: tests/test_quality.py::TestFullScanPolicy::test_encoding_probe_does_not_force_full_scan`, `test: tests/test_quality.py::TestFullScanPolicy::test_needs_full_scan_is_false_for_encoding_probe_only`

#### Scenario: Row-requiring fail check still scans every row

- GIVEN `corrupt_records` at `fail` and a corrupt row beyond `max_sample`
- WHEN `QualityValidator.run()` executes under the default `auto` policy
- THEN the corrupt row SHALL be detected

**Evidence:** `test: tests/test_quality.py::TestFullScanPolicy::test_row_requiring_fail_check_still_scans_full_file`, `test: tests/test_quality.py::TestFullScanPolicy::test_needs_full_scan_true_for_default_corrupt_records`

#### Scenario: never honours max_sample with a fail check attached

- GIVEN `quality_full_scan = "never"` with a `fail` row-requiring check and a small `max_sample`
- WHEN `QualityValidator.run()` executes
- THEN a corrupt row within the sample SHALL be reported and marked `partial`
- AND a corrupt row beyond the sample SHALL NOT be read

**Evidence:** `test: tests/test_quality.py::TestFullScanPolicy::test_never_honours_max_sample_with_fail_check`

#### Scenario: always scans the full file

- GIVEN `quality_full_scan = "always"` with a small `max_sample`
- WHEN `QualityValidator.run()` executes
- THEN a corrupt row beyond `max_sample` SHALL be detected
- AND the finding SHALL NOT be marked `partial`

**Evidence:** `test: tests/test_quality.py::TestFullScanPolicy::test_always_scans_everything`

#### Scenario: Per-dataset override wins over the tool default

- GIVEN `[quality] full_scan = "always"` and a tool-wide `quality_full_scan = "auto"`
- WHEN `QualityValidator.run()` executes
- THEN the dataset override SHALL decide the scan

**Evidence:** `test: tests/test_quality.py::TestFullScanPolicy::test_per_dataset_override_wins_over_tool_default`, `test: tests/test_quality.py::TestQualityFromToml::test_quality_policy_table_parsed`, `test: tests/test_quality.py::TestQualityFromToml::test_unknown_full_scan_mode_warns`

### 4.14 Bounded per-row accumulators

Every per-row accumulator SHALL have a bound independent of the dataset size. In particular the
duplicate finding list SHALL stop growing at `REPORT_MAX_ITEMS`, the empty-row list SHALL stop
growing at `REPORT_MAX_ITEMS`, and the corrupt-record list SHALL stop growing at
`REPORT_MAX_CORRUPT_RECORDS` — all at accumulation time, not report time. The `duplicates` hash
table SHALL be bounded by `quality_max_dup_tracking` and the `empty_columns` state by the column
count.

#### Scenario: Finding lists stop growing at their report limits

- GIVEN a stream with more duplicates, empty rows or corrupt records than the relevant report limit
- WHEN `QualityValidator.run()` completes
- THEN each finding list SHALL hold exactly its report limit
- AND two stream sizes SHALL produce identical accumulator sizes

**Evidence:** `test: tests/test_quality.py::TestAccumulatorCaps::test_duplicate_findings_capped_at_report_limit`, `test: tests/test_quality.py::TestAccumulatorCaps::test_empty_rows_capped_at_report_limit`, `test: tests/test_quality.py::TestAccumulatorCaps::test_corrupt_findings_capped_at_report_limit`, `test: tests/test_quality.py::TestAccumulatorCaps::test_accumulator_sizes_do_not_grow_with_dataset_size`

### 2.2 QualityConfig dataclass (modified)

**Clause added:** `QualityConfig` SHALL gain an optional `full_scan: str | None = None` field. When
set, it SHALL win over the tool-wide `config.QUALITY_FULL_SCAN`. `DatasetConfig.from_toml()` SHALL
read it (and an optional `max_sample`) from an optional `[quality]` policy table, warning and
ignoring an unknown mode.

**Evidence:** `test: tests/test_quality.py::TestQualityFromToml::test_quality_policy_table_parsed`, `test: tests/test_quality.py::TestQualityFromToml::test_unknown_full_scan_mode_warns`

## Config-surface removal recorded by this change

`quality_value_preview_len` (`[tool.sofer]`, issue #189) had exactly one reader — the distinct-value
set in `_col_nonempty` — and that set is replaced by a boolean here. The key SHALL be removed from
`_DEFAULTS`, from the module constants, from `pyproject.toml`, and from its test vehicles; a
`[tool.sofer]` value for it is ignored (unknown keys are not iterated by `_read_tool_section`). This
removal is a config-surface change and is declared in `design.md` §5.4 and in the archive report.

**Evidence:** `test: tests/test_config.py::TestQualityScanBoundsConfig::test_quality_value_preview_len_key_removed`, `test: tests/test_config.py::TestQualityScanBoundsConfig::test_toml_overrides_quality_bounds`, `test: tests/test_config.py::TestQualityScanBoundsConfig::test_rejects_unknown_full_scan_mode`, `test: tests/test_config.py::TestQualityScanBoundsConfig::test_rejects_non_positive_dup_cap`
