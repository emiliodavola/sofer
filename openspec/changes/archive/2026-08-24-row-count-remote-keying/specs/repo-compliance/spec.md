# Delta for repo-compliance

> Change: `row-count-remote-keying`. Lifts limitation D7 of
> `openspec/changes/archive/2026-08-17-publish-readme-bugs/design.md`.

## ADDED Requirements

### Requirement: Duplicate declared remote emits a warning (RC-R11)

Exact row counts are keyed by verbatim `entry.remote`; two `[[file]]` entries
declaring the same `remote` would overwrite one another's count. When the
dataset TOML declares two or more files with the same `remote` value, the
system MUST emit a `[!]` warning naming the duplicated remote before reporting
proceeds. The build MUST still complete deterministically (first-declared
entry wins for any shared key); this warning guards the keying invariant, it
MUST NOT abort the run.

#### Scenario: Hand-edited TOML with duplicate remotes warns

- GIVEN a hand-edited TOML declaring two `[[file]]` entries whose `remote`
  values are identical
- WHEN schema report and Dataset Card generation run
- THEN exactly one `[!]` warning naming that duplicated remote SHALL be emitted
- AND the build SHALL complete without raising an exception

#### Scenario: Distinct remotes stay silent

- GIVEN a TOML where every `[[file]]` entry has a unique `remote`
- WHEN the pipeline runs
- THEN no duplicate-remote warning SHALL be emitted

### Requirement: Non-schema files use the configured row-count fallback (RC-R12)

Entries that cannot yield exact counts cheaply — recursive directory trees,
remotes that do not end in `.csv` (including declared native `.parquet`),
and entries with `include_in_schema = false` — MUST NOT contribute per-file
exact row counts. When NO configured file yields an exact count, the card's
train split `num_examples` SHALL fall back to
`CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)` (read from tool config at call
time, never hardcoded). This preserves the D7 fallback policy documented in
`2026-08-17-publish-readme-bugs/design.md`.

#### Scenario: Recursive-only dataset uses fallback

- GIVEN a DatasetConfig whose only entries are recursive directories
- WHEN the card frontmatter is generated
- THEN `num_examples` SHALL equal
      `CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)`

#### Scenario: Excluded-from-schema files contribute no exact counts

- GIVEN every `[[file]]` entry has `include_in_schema = false`
- WHEN the card frontmatter is generated
- THEN `num_examples` SHALL equal the fallback product above

## MODIFIED Requirements

### Requirement: Real num_examples in YAML splits (RC-R07)

> Added by change `publish-readme-bugs` (archived 2026-08-24). Modified by
> change `row-count-remote-keying`.

Exact per-file row counts SHALL be stored in a dict keyed by the entry's
**verbatim remote path** (`entry.remote`, POSIX-style, matching how
`planned_remotes` and `configs.data_files` render remotes). Because remotes
are unique per dataset, keys are unique by construction. BOTH producer paths
key identically by remote: the Parquet path stores `pf.metadata.num_rows`;
the CSV path stores the counted data row total. Keys MUST NOT be derived from
basenames or local filenames, which collide across subdirectories. The sole
production consumer sums VALUES only; `ColumnSchema.origin` remains
basename-based display provenance and is never joined against these keys.
The card's single train split's `num_examples` SHALL equal the SUM of the
stored values — EXACT, never capped by any sample size.

(Previously: keys were mixed origin basenames — Parquet remote stems vs CSV
local filenames — so same-basename files collided and the second write
silently overwrote the first, undercounting `num_examples`.)

#### Scenario: num_examples equals actual rows

- GIVEN a 5-row dataset whose columns hold 13 distinct values in total
- WHEN the card's YAML frontmatter is generated
- THEN `dataset_info.splits[0].num_examples` SHALL be 5

#### Scenario: Multi-file splits sum per-file row counts

- GIVEN two files with 30 and 40 rows respectively feeding one train split
- WHEN splits are computed
- THEN the single train split's `num_examples` SHALL equal the sum of per-file
  row counts (30+40=70)

#### Scenario: Same-stem subdirectory remotes keep distinct counts

- GIVEN two CSV entries with remotes `a/data.csv` (30 rows) and `b/data.csv`
  (40 rows), whose basenames are identical
- WHEN row counts are collected
- THEN the row-count dict SHALL contain two DISTINCT keys, `a/data.csv` → 30
      and `b/data.csv` → 40
- AND the train split's `num_examples` SHALL be 70 (no silent overwrite)

#### Scenario: Parquet and CSV paths both key by remote

- GIVEN one CSV entry converted to Parquet (staging provided) and one
  `upload_as_csv` entry, with distinct remotes
- WHEN row counts are collected
- THEN both the Parquet-path count and the CSV-path count SHALL be keyed by
      their respective `entry.remote` values

#### Scenario: Single-remote behavior unchanged

- GIVEN a DatasetConfig with one CSV file entry and a 5-row file
- WHEN the card is generated
- THEN the row-count dict SHALL contain exactly `{<entry.remote>: 5}`
- AND `num_examples` SHALL be 5
