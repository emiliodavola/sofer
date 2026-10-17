# Proposal — `2026-10-17-fix-parquet-dtype-control`

> **Change** `2026-10-17-fix-parquet-dtype-control` · issue **#337** · branch
> `fix/337-parquet-dtype-control` from `dev@a7f631e` · store **hybrid**
> (this folder + Engram mirror).
>
> **Status:** implementation complete; archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

`sofer prepare` converts CSV to Parquet with pyarrow's inference, so an official
zero-padded statistical code (`"001"`, `"02"`) was stored as `int64` and the
textual form was lost. The conversion *detected* it, printed
`[!] VALUE ALTERED: column 'IDDPTO' — e.g. '001' changed after type inference`,
and then shipped the altered Parquet with exit 0 and a validation report reading
`Errors: 0 / Warnings: 0` — reproduced on a two-row fixture, Parquet readback
`IDDPTO: int64 = [1, 2, 5]`.

Issue #12 had already accepted the contract ("preserved via forced string dtype
or reported as a warning", plus `column_types` support) and was closed with that
half undelivered; `openspec/specs/parquet-conversion/spec.md` §7.2 documented the
gap as a limitation instead of a requirement.

The maintainer's framing: **do not change the data, only curate and document it.**

## 2. Scope

**In:** `column_types` on `[[file]]`; automatic protection of zero-padded code
columns; a structured, severity-carrying parity finding that fails `prepare`;
the same finding predicted by `validate` from the source alone; the spec, both
READMEs and the `prepare` help text.

**Out:** any dtype vocabulary beyond `"string"`; applying the control to
`.tsv`/`.xlsx`/`.jsonl` (their converters keep their current path — `.tsv` uses a
fixed tab delimiter and takes no `column_types`); changing the manifest schema;
guessing delimiter-agnostic numeric shapes.

## 3. Approach

1. `FileEntry.column_types` is parsed from an inline table on the entry, with a
   closed vocabulary (`config.COLUMN_TYPES_SUPPORTED = ("string",)`) enforced
   both at configuration validation and at the point of use.
2. `_converters.leading_zero_columns` probes at most
   `[tool.sofer] leading_zero_probe_rows` rows and returns the columns whose
   non-empty values are all digits with at least one leading zero; those columns
   are forced to `string` through `pyarrow.csv.ConvertOptions`, each decision
   printed. The operator's declaration wins over the probe.
3. The value check reports structured `(column, sample)` pairs through an
   out-parameter (so the caller acts without re-reading the CSV).
   `_convert_csv_to_parquet` raises `ValueAlterationError` when anything is left
   altered; the broad `except` that degrades read failures into the CSV fallback
   re-raises it, so a data-integrity failure is never hidden.
4. `prepare` collects those failures, prints each column with a sample and the
   exact `column_types` declaration that fixes it, delivers nothing for those
   files, and returns 1. `validate` reports the same finding as a warning from
   the source alone.

## 4. Affected specs

- `parquet-conversion` — §7.2 stops documenting the gap as unavoidable, a new
  §7.4 declares value parity and dtype control, and five scenarios are added.
  The spec has no `## Test Mapping` section and is recorded as a permanent
  declared backlog in `openspec/test-mapping-registry.md`, so no row is owed and
  the registry is not edited.

## 5. Delivery

One branch, one delivery PR against `dev`, assigned to `@emiliodavola` with
`Closes #337`, archived inside that PR. Work units: the config surface and the
converter protection; the fail-closed parity finding and the `validate`
prediction.
