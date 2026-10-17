# Delta for parquet-conversion

> **Change** `2026-10-17-fix-parquet-dtype-control` (issue **#337**) · branch
> `fix/337-parquet-dtype-control` from `dev@a7f631e` · store **hybrid**.
>
> **One modification + one new requirement.** §7.2 stops presenting the loss as
> an accepted limitation; a new §7.4 declares value parity, the declared dtype
> control and the automatic code protection, and five scenarios are added.
>
> **Rule-6 resolution.** `parquet-conversion` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md:34`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### 7.2 Known type-conversion gaps — Modified 2026-10-17, fix-parquet-dtype-control

The `pyarrow` inference table and the comma/mixed-type/long-field bullets are
unchanged. A fourth bullet names the zero-padded case and points at §7.4; the
gap is no longer presented as something an operator must simply accept.

## ADDED Requirements

### 7.4 Value parity and dtype control — Added 2026-10-17, fix-parquet-dtype-control

A converted file SHALL NOT change any value relative to its source.

- **Declared dtype control.** A `[[file]]` entry MAY declare
  `column_types = { COLUMN = "string" }`, forcing named columns past inference.
  `"string"` is the only type expressible today; any other value SHALL be refused
  naming the accepted set, both at configuration validation and at the point of
  use.
- **Automatic code protection.** Before the conversion read the converter SHALL
  probe at most `[tool.sofer] leading_zero_probe_rows` rows and force every column
  whose non-empty values are all digits with at least one leading zero to
  `string`, printing each decision.
- **Fail closed on anything left.** When the value check still finds a value the
  table does not carry, the conversion SHALL fail: `prepare` SHALL name each
  column with a sample and the exact `column_types` declaration that fixes it,
  deliver nothing for that file, and exit non-zero. It SHALL NOT be degraded into
  the CSV fallback of §1.1.
- **`validate` predicts it.** `sofer validate` SHALL report the same finding from
  the source alone as a warning naming the file and column, and SHALL NOT report
  a column already covered by a declaration.

#### Scenario: Zero-padded codes survive the conversion

- GIVEN a CSV whose `IDDPTO` column holds `001` and `02`, and no `column_types` declaration
- WHEN the file is converted
- THEN the Parquet column SHALL be `string`
- AND its values SHALL be `001` and `02`
- AND the automatic decision SHALL be printed for that column

#### Scenario: A declared column type forces the dtype

- GIVEN a `[[file]]` entry with `column_types = { V = "string" }`
- WHEN the file is converted
- THEN the `V` column SHALL be `string` carrying its source values
- AND the conversion SHALL NOT fail

#### Scenario: An uncovered alteration fails prepare

- GIVEN a CSV whose `V` column holds `+5`, with no declaration covering it
- WHEN `sofer prepare` runs
- THEN it SHALL report the column with a sample value and the `column_types` declaration that fixes it
- AND no Parquet SHALL be delivered for that file
- AND the exit code SHALL be non-zero

#### Scenario: An unsupported declared type is refused

- GIVEN `column_types = { ID = "int64" }`
- WHEN the configuration is validated, or the conversion is attempted
- THEN the refusal SHALL name the accepted set (`'string'`)
- AND no converted artifact SHALL be produced for that entry

#### Scenario: validate reports the code column before prepare

- GIVEN a CSV whose `IDDPTO` column holds `001`, and no `column_types` declaration
- WHEN `sofer validate` runs
- THEN it SHALL warn naming the file, the column and the declaration that makes it explicit
- AND the warning SHALL NOT be an error, because the conversion protects the column
