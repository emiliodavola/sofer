# Feature: parquet-dtype-control — issue #337

**Branch:** `fix/337-parquet-dtype-control` from `dev@ec511e7`
**Issue:** `emiliodavola/sofer#337` — *bug(convert): pyarrow inference still alters zero-padded code values, and no forced-string escape hatch exists*
**Delivery PR:** pending — assigned to `@emiliodavola`
**SDD change:** `openspec/changes/2026-10-17-fix-parquet-dtype-control/`
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
| T1 | RED: a leading-zero column survives conversion as `string` with its exact source values | S1, S3, S4 | pending | — |
| T2 | RED: `column_types` forces a named column to string; an unsupported type value is refused naming the accepted set | S2 | pending | — |
| T3 | RED: a residual alteration that no forced dtype covers fails `prepare` (non-zero, structured finding) instead of shipping | S5 | pending | — |
| T4 | RED: `validate` reports the alteration risk from the CSV alone, naming the file, column and the exact `column_types` line to add | S5 | pending | — |
| T5 | RED: `convert_to_parquet = false` still wins over `column_types` (precedence, rule 6 "existing behaviour touched") | S6 | pending | — |
| T6 | GREEN: `column_types` on `[[file]]` (inline table) threaded through `convert_file_to_parquet` into pyarrow's `ConvertOptions` | S2 | pending | — |
| T7 | GREEN: leading-zero probe on the raw CSV before the inference read, forcing those columns to string by default | S1, S4 | pending | — |
| T8 | GREEN: parity findings become structured, severity-carrying results recorded in the prepare report and the manifest; residual alteration fails the run | S5 | pending | — |
| T9 | `parquet-conversion` spec: value-parity + dtype-control requirements and their scenarios; numbered `S#`/`T#` mapping | S1-S6 | pending | — |
| T10 | README + README_ES (rule 7/13): `column_types`, the auto-protection rule, the precedence and the failure mode | S2, S6 | pending | — |
| T11 | Gates: pytest, ruff, mypy, pyright, coverage (rule 14: `prepare.py` at 100.00%), commit slices, push, PR assigned to `@emiliodavola` | — | pending | — |

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
