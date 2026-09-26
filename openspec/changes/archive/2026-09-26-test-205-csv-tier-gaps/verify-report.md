# Verify Report — `2026-09-26-test-205-csv-tier-gaps`

> Phase: apply + verification. Branch `test/205-csv-tier-test-gaps`, base `dev@90de0f7`. No commit,
> push, or PR was made during verification. All commands run with the repo's `uv` environment.

## 1. What changed

| File | Action | Description |
| --- | --- | --- |
| `tests/test_parquet_conversion.py` | Modified | F1: plumbing test through the declared-TOML seam asserting the true column count; F4: frozen digest replaced by a reference derived at test time |
| `tests/test_converters.py` | Modified | F2: JSONL-fallback test (forced fast-path failure); F3: `\|` declared-wins case outside `SNIFF_DELIMITERS`; F5: programmatic-boundary pin |
| `src/sofer/_converters.py` | Modified (comment only) | F2: corrected the `from_pylist` "union" comment to the measured behaviour |

No conversion behaviour changed; `_converters.py`'s only edit is a comment.

## 2. F1 — RED before GREEN (the discriminator the old test missed)

The old test used a **programmatic** `DatasetConfig(csv_delimiter="|")` with empty
`declared_meta_keys` and asserted only file presence. Probe on the branch:

```text
$ uv run python - <<'PY' (probe)
declared_meta_keys(old): frozenset()
OLD num_columns: 1 names: ['col1|col2']
declared_meta_keys(new): frozenset({'csv_delimiter'})
  [!] data.csv: declared csv_delimiter '|' differs from sniffed ';' — using declared '|'
NEW num_columns: 2 names: ['col1', 'col2']
```

The old programmatic config produces a **one-column** mis-split, so the rewritten assertion
(`num_columns == 2`) is RED against it and GREEN through the declared-TOML seam. The old
existence-only assertions were satisfied by that mis-split — confirming the vacuous pass reported in
issue #205.

## 3. Focused tests (new/rewritten)

```text
$ uv run pytest tests/test_parquet_conversion.py tests/test_converters.py -q
83 passed

$ uv run pytest \
    tests/test_parquet_conversion.py::TestDelimiterPlumbing::test_custom_delimiter_used_via_upload \
    tests/test_parquet_conversion.py::TestUndeclaredDialectByteIdentical::test_undeclared_dialect_matches_prechange_bytes \
    tests/test_converters.py::TestCsvDialectResolution::test_declared_pipe_outside_sniff_set_wins \
    tests/test_converters.py::TestCsvDialectResolution::test_programmatic_value_without_presence_signal_falls_back_to_sniff \
    tests/test_converters.py::TestJsonlFallback::test_from_pylist_fallback_uses_first_record_schema -v
5 passed
```

## 4. Full suite (tally re-derived on this branch, never quoted)

```text
$ uv run coverage run -m pytest tests/ -q
1917 passed, 1 skipped, 1 warning in 402.86s (0:06:42)
```

The single warning is the pre-existing `runpy` `RuntimeWarning` from
`tests/test_cli.py::test_cli_main_guard_executed_via_runpy`; it is not a `DeprecationWarning` from
`sofer.codebook` (PB-12).

## 5. Coverage gates

```text
$ bash scripts/check_core_coverage.sh
src/sofer/cli.py      600  0  176  0  100%
src/sofer/scanner.py  159  0   76  0  100%
src/sofer/prepare.py  325  0  180  0  100%
src/sofer/publish.py  326  0  138  0  100%
CORE_EXIT=0

$ uv run coverage report -m | tail -1
TOTAL  5968  325  2282  154  94%
```

The four COV-06 modules stay at 100.00% with no `# pragma: no cover`; TOTAL (94%) is above the
config-owned `fail_under = 90`.

## 6. Lint / format / types / gate

```text
$ uv run ruff check src/ tests/ scripts/          -> All checks passed!
$ uv run ruff format --check src/ tests/ scripts/ -> 72 files already formatted
$ uv run mypy src/ scripts/                       -> mypy: No issues found
$ uv run pyright                                  -> 0 errors, 1 warning, 0 informations
$ uv run python scripts/check_test_mapping.py     -> OK: test-mapping contract holds (exit 0)
```

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` could not be resolved from source) is
pre-existing and outside this diff; pyright's exit contract is errors-only and it exits 0. The
test-mapping checker exits 0 with the registry bijection intact (`parquet-conversion` remains a
registered unmapped spec; the canonical spec gains PC-U07 at archive time).

## 7. Diff scope

```text
$ git diff --stat
src/sofer/_converters.py         |  5 ++-
tests/test_converters.py         | 69 ++++++++++++++++++++++++++++++++++++++++
tests/test_parquet_conversion.py | 58 ++++++++++++++++++++++++--------------
3 files changed, 107 insertions(+), 25 deletions(-)
```

Zero `pyproject.toml`, `README*`, `.github/workflows/`, or `src/sofer/` behaviour paths; the only
`src/` path is the comment correction. No coverage floor, gate, or dataset config changed.
