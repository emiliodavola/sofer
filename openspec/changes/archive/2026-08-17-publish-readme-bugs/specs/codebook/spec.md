# Delta for codebook — sentinel-free unique counts and config-driven max-sample

> Note: the base spec (`openspec/specs/codebook/spec.md`) has no named requirement
> covering the unique-value statistic or the `--max-sample` flag, so both are
> recorded as ADDED requirements (repo convention for this capability).

## ADDED Requirements

### Requirement: Unique counts exclude missing sentinels (CB-R07)

For every format, the per-column `unique` statistic SHALL count DISTINCT
NON-MISSING values only. Missing-value sentinels ("", "NA", "NULL", "N/A", and
null/None) MUST NOT be counted as distinct values. This aligns `codebook.py`
with its own missing-percentage computation (which already filters sentinels)
and with the documented behavior of the Dataset Card's schema report.

(Previously: `n_unique = len(set(col_values))` counted sentinels as values,
so a column of ["A", "", "NA"] reported unique=3 while missing% excluded them —
inconsistent within the same output table.)

#### Scenario: Sentinels not counted as values

- GIVEN a column whose values are ["A", "", "NA", "B", "NULL"]
- WHEN the codebook is generated
- THEN unique SHALL be 2
- AND missing percentage SHALL reflect the 3 missing rows

#### Scenario: Column without sentinels unchanged

- GIVEN a column whose values are all non-missing
- WHEN the codebook is generated
- THEN unique SHALL equal the count of distinct values, as today

---

### Requirement: --max-sample default from config (CB-R08)

The `codebook` command's `--max-sample` default SHALL come from the
`CODEBOOK_MAX_SAMPLE` constant loaded from `[tool.sofer] codebook_max_sample`
(default `100_000`) via `config.py`. The CLI parser MUST NOT embed a numeric
literal default; the argparse help text SHALL state the configured value.

(Previously: `cli.py` hardcoded `default=100_000`, bypassing the user's TOML
config — AGENTS rule 1.)

#### Scenario: TOML override respected by CLI default

- GIVEN `[tool.sofer] codebook_max_sample = 50000`
- WHEN `sofer codebook data.csv` runs without `--max-sample`
- THEN sampling SHALL cap at 50000 rows

#### Scenario: Explicit flag still wins

- GIVEN any configured value
- WHEN `sofer codebook data.csv --max-sample 1000` runs
- THEN sampling SHALL cap at 1000 rows
