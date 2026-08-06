# Delta for repo-compliance

## ADDED Requirements

### Requirement: RC-R02 — Duplicate column summary threshold

`build_schema_report()` SHALL emit warnings for duplicate column names across files. A new `schema_dup_threshold` config key (default `3`) in `[tool.sofer]` SHALL govern the output format:

- When duplicate count ≤ `schema_dup_threshold`: individual `[!]` warnings per duplicate.
- When duplicate count > `schema_dup_threshold`: a single `[i]` summary with the top 5 most-duplicated columns, a contextual message, and a tip referencing `include_in_schema` as an opt-out.

#### Scenario: Default threshold — 1 duplicate (below limit)
- GIVEN `schema_dup_threshold = 3` and 1 duplicate column detected
- WHEN `build_schema_report()` emits duplicate warnings
- THEN a single `[!]` warning SHALL be printed

#### Scenario: Default threshold — 3 duplicates (at limit)
- GIVEN `schema_dup_threshold = 3` and 3 duplicate columns detected
- WHEN `build_schema_report()` emits duplicate warnings
- THEN 3 individual `[!]` warnings SHALL be printed

#### Scenario: Default threshold — 4 duplicates (above limit)
- GIVEN `schema_dup_threshold = 3` and 4 duplicate columns detected
- WHEN `build_schema_report()` emits duplicate warnings
- THEN a single `[i]` summary SHALL be printed with top 5 columns, a contextual message, and a tip referencing `include_in_schema`

#### Scenario: Custom threshold — 8 duplicates (below limit)
- GIVEN `schema_dup_threshold = 10` and 8 duplicate columns detected
- THEN 8 individual `[!]` warnings SHALL be printed

#### Scenario: Custom threshold — 11 duplicates (above limit)
- GIVEN `schema_dup_threshold = 10` and 11 duplicate columns detected
- THEN a single `[i]` summary SHALL be printed

#### Scenario: No duplicates
- GIVEN no duplicate column names across files
- WHEN `build_schema_report()` completes
- THEN no duplicate-related warnings SHALL be emitted

### Requirement: RC-R03 — Per-file schema inclusion

Each `[[file]]` entry SHALL support an optional `include_in_schema` boolean, defaulting to `true`. When `false`, `build_schema_report()` SHALL skip that file — its columns SHALL NOT appear in the Dataset Card's Codebook table. The file SHALL still be uploaded and listed in `configs`/`data_files`.

When all configured files have `include_in_schema = false`, `build_schema_report()` SHALL emit a warning and return an empty list.

#### Scenario: File excluded from schema
- GIVEN a `[[file]]` entry with `include_in_schema = false`
- WHEN `build_schema_report()` processes the file list
- THEN the file's columns SHALL NOT appear in the returned ColumnSchema list
- AND the file SHALL still be uploaded

#### Scenario: Field absent — default behavior preserved
- GIVEN a `[[file]]` entry without an `include_in_schema` field
- WHEN `build_schema_report()` processes the file list
- THEN the file SHALL contribute columns normally (default `true`)

#### Scenario: All files excluded from schema
- GIVEN all `[[file]]` entries have `include_in_schema = false`
- WHEN `build_schema_report()` processes the file list
- THEN a warning "All files excluded from schema" SHALL be emitted
- AND an empty list SHALL be returned

#### Scenario: Mixed inclusion — only true files contribute
- GIVEN some files with `include_in_schema = true` and some with `false`
- WHEN `build_schema_report()` processes the file list
- THEN only files with `include_in_schema = true` SHALL contribute columns
