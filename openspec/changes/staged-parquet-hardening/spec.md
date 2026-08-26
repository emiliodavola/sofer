# Delta for repo-compliance

> Change: `staged-parquet-hardening` (GitHub #63, #64). Closes two residuals from
> #60. Continues RC-R01–RC-R15 numbering with two additive requirements:
> RC-R16 (case-fold collision refusal) and RC-R17 (unreadable staged-Parquet
> warning).

## ADDED Requirements

### Requirement: Case-fold collision on staged-Parquet remotes is refused (RC-R16)

For entries that declare a `.csv` remote case-insensitively and are NOT
`recursive` (the scan covers all physically-staged `.csv` remotes — including
`upload_as_csv` and `include_in_schema=false`, which `prepare` still stages via
`copy_to_mirror`), if two entries' `entry.remote` values differ verbatim but
normalize to the same staged-Parquet key, the system MUST reject the config
with a deterministic hard error naming BOTH colliding remotes, during
`validate()` and before any staging write. Case-preserving `parquet_remote_for`
keys remain unchanged. This is distinct from RC-R11: verbatim-identical remotes
produce RC-R11's non-aborting `[!]` warning; case-differing-but-colliding
remotes produce RC-R16's hard error. Equivalence is the derived key
`parquet_remote_for(entry.remote).lower()` (which also catches backslash-vs-slash
normalized collisions) — and uses `str.lower()`, NOT `casefold()`: no additional
Unicode normalization (e.g. `"ß"` vs `"ss"` are NOT equal).

#### Scenario: Case-differing remotes are rejected naming both

- GIVEN two entries with remotes `Data/Prov/Train.CSV` and `data/prov/train.csv`
- WHEN `validate()` runs
- THEN a single hard error naming BOTH remotes SHALL be emitted
- AND the command SHALL exit 1 before any staging write

#### Scenario: Exact-duplicate remotes still warn, not error

- GIVEN two entries with the identical verbatim remote `data/train.csv`
- WHEN the pipeline runs
- THEN RC-R11's `[!]` warning SHALL fire (non-aborting)
- AND NO case-fold collision error SHALL be raised

#### Scenario: Lower-case equivalence only, no Unicode normalization

- GIVEN remotes `straße.csv` and `strasse.csv`
- WHEN validation runs
- THEN no collision error SHALL be raised (lower() treats them distinct)

#### Scenario: Ineligible entries are unaffected

- GIVEN entries that are `recursive` or non-`.csv` remotes
- WHEN validation runs
- THEN no RC-R16 error SHALL be raised for those entries
- AND entries with `include_in_schema=false` or `upload_as_csv=true` but a
  `.csv` remote SHALL still be scanned, because `prepare` stages them
  physically (section 7 `copy_to_mirror` does not skip them) and a
  case-differing pair would still collide on disk

#### Scenario: Error precedes any staging write

- GIVEN a config with case-differing remotes
- WHEN `prepare` executes
- THEN validation SHALL fail (exit 1) BEFORE the staging directory is written

### Requirement: Unreadable staged Parquet warns deterministically and falls back (RC-R17)

When a staged Parquet EXISTS for an eligible entry but cannot be read, the
system MUST emit exactly one `[!]` warning naming the parquet key AND the
failure class — one of `corrupt/parse`, `io/permission`, or `other` — then fall
back to CSV inference without raising. The warning fires warn-once per key per
run, in declaration order. This is mutually exclusive with RC-R14 (absent): a
single entry triggers at most one of the two.

#### Scenario: Corrupt parquet warns with class and falls back

- GIVEN an eligible entry whose staged Parquet exists but fails to parse
- WHEN the schema report is built
- THEN one `[!]` warning SHALL name the key and `corrupt/parse`
- AND columns SHALL come from CSV fallback (no raise)

#### Scenario: IO/permission failure warns with class

- GIVEN a staged Parquet that exists but raises an IO/permission error on read
- WHEN the schema report is built
- THEN one `[!]` warning SHALL name the key and `io/permission`
- AND the CSV fallback SHALL proceed

#### Scenario: Other exception warns with generic class

- GIVEN a staged Parquet whose read raises an exception outside corrupt/parse
  or io/permission
- WHEN the schema report is built
- THEN one `[!]` warning SHALL name the key and `other`

#### Scenario: Absent parquet stays RC-R14 (no double warning)

- GIVEN an eligible entry whose staged Parquet is ABSENT
- WHEN the schema report is built
- THEN only RC-R14's missing-parquet `[!]` SHALL fire
- AND no unreadable warning SHALL be emitted

#### Scenario: Warn-once per key

- GIVEN two entries sharing one corrupt staged-Parquet key
- WHEN the schema report is built
- THEN exactly one `[!]` unreadable warning SHALL be emitted

#### Scenario: Readable parquet stays silent

- GIVEN every eligible entry's staged Parquet reads successfully
- WHEN the schema report is built
- THEN no unreadable warning SHALL be emitted
