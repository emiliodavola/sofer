# Feature: parquet-dtype-control — issue #337

**Branch:** `fix/337-parquet-dtype-control` from `dev@ec511e7`
**Issue:** `emiliodavola/sofer#337` — *bug(convert): pyarrow inference still alters zero-padded code values, and no forced-string escape hatch exists*
**Delivery PR:** [#341](https://github.com/emiliodavola/sofer/pull/341) — `fix/337-parquet-dtype-control` → `dev`, assigned to `@emiliodavola`
**SDD change:** `openspec/changes/archive/2026-10-17-fix-parquet-dtype-control/` (archived inside the PR)
**Phase:** 2 of the v0.8.0 batch

## Goal

`prepare` converts CSV to Parquet with pyarrow's inference, so an official zero-padded statistical code
(`"001"`, `"02"`) is stored as `int64` and the delivered bytes are no longer the source values. The
conversion *detects* it and prints `[!] VALUE ALTERED`, and then ships the altered Parquet with exit 0
and a validation report reading `Errors: 0 / Warnings: 0`. `#12` agreed the contract (forced string
dtype or a warning, plus a `column_types` control) and was closed with that half undelivered; the
`parquet-conversion` spec of record never gained the requirement either.

The maintainer's framing: **do not change the data, only curate and document it.**

## Specs

S1 (#12, verbatim): "**Value parity**: the set of values per column (string-normalized) must be
identical after conversion. Any value pyarrow would alter (leading zeros, comma decimals, date/time
formats) is either preserved via forced string dtype or reported as a warning before upload."

S2 (#12, verbatim): "**Dtype control**: `ConvertOptions`/`column_types` support so code-like columns
can be forced to string; no silent inference."

S3 (#12, verbatim): "**Acceptance criteria**: No converted file changes row count, column names, or
values vs the source CSV." + "Tests cover leading-zero columns, comma decimals, quoted delimiters,
all-null columns."

S4 (#337, verbatim): the requirement "**do not change the data, only curate and document it.**"

S5 (#337 proposed fix 3, verbatim): "Promote `VALUE ALTERED` from a print to a quality check with a
severity, so `validate`/`prepare` can fail on it, and record it in the manifest/report."

S6 (#337 proposed fix 4, verbatim): "Keep `convert_to_parquet = false` as the per-file escape hatch and
document its precedence against the new dtype control."

## Measured baseline (2026-10-17, `dev@ec511e7`)

`tmp/verify-337/`: `raw/DPTO.csv` = `IDDPTO;NOMDPTO` / `001;Amazonas` / `02;Antioquia` / `5;Atlantico`,
run through `uv run sofer prepare tmp/verify-337/dpto.toml`:

```
[!] VALUE ALTERED: column 'IDDPTO' — e.g. '001' changed after type inference
Validation report: verify337 / Errors: 0 / Warnings: 0 / OK  All checks passed.
Result: 1 parquet(s) generated     exit 0
Parquet readback: schema=IDDPTO: int64, NOMDPTO: string   IDDPTO=[1, 2, 5]
```

## Tasks

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | RED: a leading-zero column survives conversion as `string` with its exact source values | S1, S3, S4 | **done** | RED against pre-fix `src/`: `assert DataType(int64) == DataType(string)` with `IDDPTO: [[1,2]]`. GREEN: `TestPrepareValueParity::test_zero_padded_codes_survive_prepare` |
| T2 | RED: `column_types` forces a named column to string; an unsupported type value is refused naming the accepted set | S2 | **done** | RED: `TypeError: FileEntry.__init__() got an unexpected keyword argument 'column_types'`. GREEN: `TestColumnTypeControl` (6) + `TestFileColumnTypes` (4) |
| T3 | RED: a residual alteration that no forced dtype covers fails `prepare` (non-zero, structured finding) instead of shipping | S5 | **done** | RED: `assert 0 == 1` on the exit code (the altered value shipped). GREEN: `test_residual_alteration_fails_prepare` (`rc == 1`, `VALUE PARITY FAILED`, `column_types = { V = "string" }`, no Parquet) + `test_residual_alteration_raises_instead_of_shipping` |
| T4 | RED: `validate` reports the alteration risk from the CSV alone, naming the file, column and the exact `column_types` line to add | S5 | **done** | RED: `assert False = any(<generator ...>)` (no warning). GREEN: `TestColumnValueParityWarning` (4) |
| T5 | RED: `convert_to_parquet = false` still wins over `column_types` (precedence, rule 6 "existing behaviour touched") | S6 | **done** | `test_convert_to_parquet_false_wins_over_column_types`: the CSV is staged unchanged and no Parquet is written |
| T6 | GREEN: `column_types` on `[[file]]` (inline table) threaded through `convert_file_to_parquet` into pyarrow's `ConvertOptions` | S2 | **done** | `_parse_column_types` (model), `column_type_datatype`, `_forced_column_types`; `convert_options` passed only when something is forced (PC-U01 call shape kept) |
| T7 | GREEN: leading-zero probe on the raw CSV before the inference read, forcing those columns to string by default | S1, S4 | **done** | `leading_zero_columns` bounded by `[tool.sofer] leading_zero_probe_rows` (default 1000); `TestLeadingZeroProbe` (7) covers detection, the non-code guard, empty cells and the row budget |
| T8 | GREEN: parity findings become structured, severity-carrying results recorded in the prepare report; residual alteration fails the run | S5 | **done** | `_check_conversion_parity` extends the pairs through an out-parameter (D6) and returns its printed warnings unchanged; `ValueAlterationError` is re-raised past the converter's broad `except` (D4). Deviation from the plan: the **manifest schema was left untouched** (D7) — the finding is recorded in the `prepare` report, which is what the MCP envelope returns as `output` |
| T9 | `parquet-conversion` spec: value-parity + dtype-control requirements and their scenarios | S1-S6 | **done** | `openspec/specs/parquet-conversion/spec.md`: §7.2 rewritten, §7.4 added, five scenarios; delta in `openspec/changes/2026-10-17-fix-parquet-dtype-control/specs/parquet-conversion/spec.md`; `scripts/check_test_mapping.py` → `OK: test-mapping contract holds` |
| T10 | README + README_ES (rule 7/13): `column_types`, the auto-protection rule, the precedence and the failure mode | S2, S6 | **done** | README/README_ES footnote ² mirrored (prose translated, TOML in English) + the `prepare` subcommand description (rule 7) |
| T11 | Gates: pytest, ruff, mypy, pyright, coverage (rule 14: `prepare.py` at 100.00%), commit slices, push, PR assigned to `@emiliodavola` | — | **done** | `uv run pytest tests/ -q` → **2426 passed, 9 skipped**; `coverage run -m pytest` → same, TOTAL **94%** (floor 90); rule-14 rows `cli.py` 744/100%, `scanner.py` 193/100%, `prepare.py` 342/100%, `publish.py` 352/100%; `ruff check` + `ruff format --check` clean; `mypy src/ scripts/` clean; `pyright` 0 errors (1 pre-existing `tomli` warning); `scripts/check_test_mapping.py` → `OK`. Three work-unit commits: `5ed5db8` (dtype control), `9a6d4b6` (fail-closed parity + validate prediction), the archive commit (docs, spec, change folder). **The first gate run found three defects** — two `[tool.sofer]` keys missing from `pyproject.toml`, a spy in `tests/test_parquet_conversion.py` that did not accept the new keyword, and `mypy` rejecting the reused `exc` binding — all fixed before the PR |

## Decisions

- **D1 — the dtype map lives on `[[file]]`, not `[meta]`.** A column belongs to a file; `[meta]` is the
  dataset-card namespace (`META_KEYS`) and putting a per-file dtype map there would need a file key
  inside a metadata table. Surface: `column_types = { IDDPTO = "string" }` as an inline table on the
  entry (the form the issue itself proposes).
- **D2 — the vocabulary is `"string"` only, refused otherwise.** The requirement is "force a code-like
  column to string"; anything richer is speculative config surface. An unknown value fails closed with
  the accepted set named, so the vocabulary can grow without a silent typo.
- **D3 — leading-zero columns are auto-forced, and that is a deliberate default change.** A code with a
  leading zero is not a number, the current delivery is wrong, and `#12`'s own contract allows
  preserving over warning. The probe is bounded by a `[tool.sofer]` row count (rule 1) and the decision
  is reported per file, so the operator sees it without reading the Parquet.
- **D4 — a residual alteration is fatal, not advisory.** After D3, anything still altered is an
  alteration the operator did not authorize; shipping it is exactly what S4 forbids. The message names
  the file, the column and the `column_types` line that fixes it.
- **D5 — `prepare` and `validate` report the same finding shape.** `validate` predicts it from the CSV
  (no Parquet yet), `prepare` confirms it from the converted table; one vocabulary, two producers.
- **D6 — no pandas.** Everything stays on the pyarrow + stdlib readers already in use (rule 9).

## Log

- **L1** (user, verbatim): "revisá los issues pendientes e armate un roadmap de implementación, no
  confies en lo que dicen, chequeá a partir de ellos y asegurate que digan lo correcto, sino modificalos

  necesito una rama por issue y luego un push y PR (asignado a mi) por implementación"
- **L2** (user, verbatim): "usá ODD obligatoriamente"
- **L3** — verification (2026-10-17): the defect reproduced end-to-end (Parquet `IDDPTO: int64` =
  `[1, 2, 5]`, exit 0, `Errors: 0 / Warnings: 0`). #12's quoted contract matches its body verbatim and
  #12 is CLOSED with the checklist unchecked, so the dtype half was never delivered. Two refinements
  applied to the issue text: the line range for the emission (`:400-405` detects and builds the message,
  `:406-407` prints, `:513` discards the returned warnings) and the grep scope (`src/`, not "the
  installed package"). Evidence appended to the issue body.
- **L4** — the value-parity design was validated against the real library before writing code:
  `001`/`02` infer as `int64` and come back as `['001','02']` when forced; `+5` infers as `double` and
  is the residual case the probe cannot protect (it is not zero-padded), which is what makes the
  fail-closed half testable with a real fixture rather than a synthetic one.
- **L5** — implementation complete: `column_types` on `[[file]]`, the bounded leading-zero probe, the
  forced `ConvertOptions`, the structured parity pairs with `ValueAlterationError` re-raised past the
  CSV fallback, the `prepare` failure block (exit 1) and the `validate` prediction. RED measured per
  half against the pre-fix source. Spec §7.2/§7.4 + five scenarios, README pair, `prepare` help text.
  Deviation recorded: the manifest schema was left untouched (D7).
- **L6** — first full gate run defeated three things the compiler of the change did not: the two new
  `[tool.sofer]` keys were absent from `pyproject.toml` (`test_repo_pyproject_declares_every_default_key`
  is total parity), `COLUMN_TYPES_SUPPORTED` had to mirror the default's type (`list`, not `tuple`) for
  `test_constants_equal_defaults_at_import`, and mypy rejects reusing an `except … as exc` binding later
  in the function. A fourth failure was a test that pins "prepare routes CSV conversion through
  `_converters`": its spy did not accept the new keyword, and keeping its assertion was the point.
  Lesson kept for the third phase: run the gate set *before* writing the delivery record, not after.
