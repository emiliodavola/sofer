# Design — `2026-10-17-fix-parquet-dtype-control`

> **Change** `2026-10-17-fix-parquet-dtype-control` (issue **#337**) · branch
> `fix/337-parquet-dtype-control` from `dev@a7f631e` · store **hybrid**.

---

## 1. The defect, precisely

`_convert_csv_to_parquet` read the CSV with `pc.read_csv(local, **dialect)`,
compared the inferred table against the source strings
(`_check_conversion_parity`), printed `[!] VALUE ALTERED …` per column, and
returned the table anyway:

```python
        parity_ok, _ = _check_conversion_parity(local, delimiter, table, encoding)
        if not parity_ok:
            return None
        return _write_parquet_table(table, staging_dir, local.stem)
```

Only the *hard* checks (row count, column count, column names) could fail. The
soft value check built `warnings`, printed them, and its result was discarded by
the caller (`parity_ok, _ =`) — so nothing downstream could see it, nothing
reached the report or the manifest, and the process exited 0.

## 2. Why the value check could not simply become fatal

Failing on the bare `warnings` list would fail every dataset that already ships
today, because the alteration it detects is real but *fixable*: the column can be
forced to `string`. The fix therefore has to produce the protection first, and
only fail on what the protection cannot reach. Hence the three-part design:
declared dtype → automatic protection for the pattern the issue names → fail
closed on the residue.

## 3. The forced-dtype path

`pc.ConvertOptions(column_types={...})` is the pyarrow API for "do not infer this
column". Measured on the fixture:

| source | inferred | forced to string |
| --- | --- | --- |
| `001`, `02` | `int64` → `[1, 2]` | `string` → `['001', '02']` |
| `+5`, `+6` | `double` → `[5.0, 6.0]` | `string` → `['+5', '+6']` |

`+5` is the residual case: it is not zero-padded, so the probe leaves it alone
and the value check still finds `+5 ≠ 5.0` — which is exactly what `prepare` now
reports and refuses.

`convert_options` is passed **only when something is forced**, so a dataset that
needs no dtype control keeps the pre-change read shape asserted by PC-U01.

## 4. The probe

`leading_zero_columns` reads at most `leading_zero_probe_rows` rows and returns a
column when every non-empty probed value is all digits *and* at least one carries
a leading zero (`^0\d+$`). The second condition is what keeps free text with an
incidental `007 …` token out of the forced set; the row budget is what keeps the
detection from reading a multi-GB corpus twice.

## 5. Decisions

- **D1 — the dtype map lives on `[[file]]`.** A column belongs to a file; `[meta]`
  is the dataset-card namespace. Surface: `column_types = { ID = "string" }` as an
  inline table (the form the issue proposes).
- **D2 — the vocabulary is `"string"` only, refused otherwise.** Enforced twice:
  `_validate_config_types` (stable diagnostic naming the accepted set) and
  `column_type_datatype` at the point of use. A value that reaches the converter
  without validation does not raise: the conversion fails closed, prints the
  accepted set, and the original CSV is staged unchanged.
- **D3 — leading-zero columns are auto-protected, and that is a deliberate default
  change.** A code with a leading zero is not a number, `#12`'s contract allows
  preserving over warning, and the probe is bounded by a `[tool.sofer]` row count
  (rule 1). Each decision is printed so the operator sees it.
- **D4 — a residual alteration is fatal, not advisory.** After D3, anything still
  altered is an alteration the operator did not authorize. `ValueAlterationError`
  is re-raised through the converter's broad `except`, so it can never be degraded
  into the §1.1 CSV fallback, which is reserved for genuine read failures.
- **D5 — `validate` predicts, `prepare` confirms.** One vocabulary, two producers:
  the same probe drives the warning (`validate`) and the protection (`prepare`).
- **D6 — the parity pairs travel through an out-parameter.** `_check_conversion_parity`
  keeps its `(ok, warnings)` contract (six call sites and their assertions are
  untouched) and extends an optional list with `(column, sample)` pairs, so the
  converter acts on the finding without a second Python read of the CSV. An
  out-parameter is the deliberate trade-off: a frozen result object would have
  been tidier and would have broken every existing unpacking for no behavioural
  gain.
- **D7 — the manifest schema is untouched.** The finding is recorded in the
  `prepare` report, which is what the MCP envelope returns as `output`. Adding a
  field to `PackageManifest` would be a `prepare`/`manifest` schema change with
  its own spec delta; it is not needed to satisfy "record it in the
  manifest/report".

## 6. Residual risks

- The default change is visible: a dataset with a zero-padded column now delivers
  that column as `string` instead of `int64`. That is the requested behaviour and
  it belongs in the release notes; consumers that summed the column must adapt.
- `.tsv` keeps its pre-change path (fixed tab delimiter, no dtype control). A
  zero-padded TSV column is still inferred. Out of scope here, recorded as such.
- The probe is a heuristic on the first `leading_zero_probe_rows` rows: a code
  column whose leading zero only appears later is not auto-protected. The value
  check still catches it, so the outcome is a refusal naming the fix, never a
  silent alteration.
