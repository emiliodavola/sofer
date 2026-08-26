# Delta for repo-compliance

> Change: `staged-parquet-stem-collision` (GitHub #60). Fixes the consumer half
> of the staging handshake: the flat `{stem}.parquet` lookup becomes a
> remote-relative POSIX key. New requirements continue the existing scheme from
> RC-R12 (RC-R13..R15). One existing requirement (RC-R05) is modified.

## ADDED Requirements

### Requirement: Staged-Parquet resolution keys by remote-relative POSIX path (RC-R13)

When `staging_dir` is provided and an entry is eligible for Parquet reading,
`build_schema_report()` MUST resolve the candidate as `staging_dir` joined with
ALL components of the remote-derived key `parquet_remote_for(entry.remote)` —
the entry's remote with its suffix replaced by `.parquet`, POSIX-normalized.
The lookup MUST NOT use a bare filename stem. The SAME derivation MUST back
every producer and consumer of staged-Parquet paths (writer and reader share
one definition), so their keys are identical by construction.

(Previously: § 3.3.3 step 2a mandated `staging_dir / <stem>.parquet`, which
silently missed nested remotes' Parquets and cross-contaminated same-stem
entries; § 3.3.6's `"a.parquet::value"` prefix example is likewise superseded
by RC-R05's origin format below.)

#### Scenario: Nested remote reads its own Parquet

- GIVEN a CSV entry with remote `data/PROV/train.csv`
- AND a staged Parquet at `staging_dir/data/PROV/train.parquet`
- WHEN `build_schema_report(cfg, staging_dir=...)` runs
- THEN the Parquet branch SHALL be taken (dtypes and nullability from the
      Parquet schema)
- AND row counts SHALL come from Parquet metadata, not slow CSV counting

#### Scenario: Same-stem root and nested entries resolve independently

- GIVEN remotes `survey.csv` and `data/survey.csv`, each with its own staged
  Parquet containing different schemas
- WHEN the schema report is built
- THEN each entry SHALL resolve to its OWN parquet
- AND no column SHALL report the other file's dtype, nullability, or rows

#### Scenario: prepare → schema-report parity for nested remotes

- GIVEN a config with remote `data/PROV/train.csv` processed end-to-end by
  `prepare`
- WHEN the schema report is built with `staging_dir = output_dir`
- THEN column dtypes SHALL match the converted Parquet
- AND the reported row count SHALL equal the Parquet metadata row count

### Requirement: Missing staged Parquet warns deterministically, then falls back to CSV (RC-R14)

If the expected staged Parquet does not exist for an eligible entry, the
system MUST emit exactly one `[!]` warning naming the expected remote-relative
`.parquet` key, then fall back to the CSV inference path. The fallback MUST
NOT raise. Following the RC-R11 convention, the warning MUST be deterministic
(same input → same single message) and MUST NOT abort the run.

#### Scenario: Missing parquet warns once and falls back

- GIVEN an eligible CSV entry whose expected staged Parquet is absent from
  `staging_dir`
- WHEN the schema report is built
- THEN exactly one `[!]` warning naming the expected `.parquet` key SHALL be
      emitted
- AND the entry's columns SHALL come from the CSV fallback path

#### Scenario: Present parquet stays silent

- GIVEN every eligible entry's staged Parquet exists at its remote-relative
  key
- WHEN the schema report is built
- THEN no missing-parquet warning SHALL be emitted

### Requirement: Backslash normalization on both handshake sides (RC-R15)

Remotes containing `\` MUST be normalized to `/` identically when WRITING
staged Parquets and when RESOLVING them, so a TOML remote like
`data\a\train.csv` yields the same key on producer and consumer. Normalization
SHALL be idempotent: normalizing an already-normalized remote returns it
unchanged.

#### Scenario: Backslash remote round-trips

- GIVEN a TOML remote declared with backslash separators
- WHEN `prepare` stages the Parquet and the schema report resolves it
- THEN both sides SHALL derive the same forward-slash key
- AND the schema SHALL be read from the Parquet branch

#### Scenario: Normalization is idempotent

- GIVEN an already-forward-slash remote
- WHEN normalization is applied again
- THEN the value SHALL be unchanged

## MODIFIED Requirements

### Requirement: Column origin attribution (RC-R05)

> Added by change `publish-readme-bugs` (archived 2026-08-24). Modified by
> change `staged-parquet-stem-collision`.

`ColumnSchema` SHALL keep its optional `origin: str = ""` field, now holding
the source file's **remote-relative POSIX path**: on the Parquet path, the
remote-derived `.parquet` key (e.g. `"data/survey.parquet"`); on the CSV
path, `entry.remote`. `build_schema_report()` SHALL populate `origin` for
every collected column, on both paths. Duplicate-name resolution remains
first-occurrence-wins: a column name appearing in several files SHALL yield
ONE entry attributed to its first source file via `origin`, and the duplicate
warnings of § 3.3.7 remain unchanged. This also supersedes RC-R07's clause
calling origin "basename-based": origin is display provenance only and is
never joined against row-count keys.

(Previously: `origin` held the source file's basename — `"survey.csv"` /
`"survey.parquet"` — which is ambiguous for same-stem files under different
remotes.)

#### Scenario: Multi-file dataset exposes origin

- GIVEN a DatasetConfig with two CSV files, each contributing columns
- WHEN `build_schema_report()` runs
- THEN every returned ColumnSchema SHALL carry `origin` set to its source
      file's remote-relative path

#### Scenario: Duplicate name keeps first occurrence with its origin

- GIVEN two files that both contain a column "value"
- WHEN `build_schema_report()` runs
- THEN exactly one "value" entry SHALL be returned
- AND its `origin` SHALL be the first-declared file that provided the column

#### Scenario: Nested Parquet origins distinguish same-stem files

- GIVEN remotes `survey.csv` and `data/survey.csv`, both read from Parquet
- WHEN origins are assigned
- THEN they SHALL be `survey.parquet` and `data/survey.parquet` respectively
