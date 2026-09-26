# Tasks — `2026-09-26-test-205-csv-tier-gaps`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~120–170 (tests + one comment + spec) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single PR |
| Chain strategy | n/a |

## Phase 1: Test fixes (RED first where applicable)

- [ ] 1.1 **F3** Add `test_declared_pipe_outside_sniff_set_wins` to
      `tests/test_converters.py::TestCsvDialectResolution` (`|` outside `config.SNIFF_DELIMITERS`,
      asserting `["col1", "col2", "col3"]`).
- [ ] 1.2 **F1** Rewrite `tests/test_parquet_conversion.py::TestDelimiterPlumbing::test_custom_delimiter_used_via_upload`
      to drive `_declared_cfg` and assert `num_columns == 2` / column names. First prove RED: run the
      same column-count assertion against the old programmatic config and record the one-column
      failure.
- [ ] 1.3 **F2** Add a JSONL-fallback test to `tests/test_converters.py` that forces
      `pyarrow.json.read_json` to raise and asserts the measured fallback behaviour (first-record
      schema; later-only key dropped; conversion still succeeds).
- [ ] 1.4 **F2** Correct the `from_pylist handles sparse keys (union)` comment in
      `src/sofer/_converters.py` to state the measured behaviour.
- [ ] 1.5 **F4** Replace `_PRECHANGE_UNDECLARED_SHA256` in `tests/test_parquet_conversion.py` with a
      reference digest derived at test time from the pre-change read shape.
- [ ] 1.6 **F5** Add a test pinning the programmatic-`DatasetConfig` boundary (value without
      `declared_meta_keys` does not override; sniff fallback collapses the `|` file to one column).

## Phase 2: Verification

- [ ] 2.1 Run `uv run pytest tests/ -q` green; re-derive the tally on the branch.
- [ ] 2.2 Run the four new/rewritten tests focused and record the RED/GREEN evidence for F1.
- [ ] 2.3 Run `uv run coverage run -m pytest` + `uv run coverage report -m`; confirm the four COV-06
      modules (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) stay at 100.00% with no pragma and
      TOTAL ≥ the config floor.
- [ ] 2.4 Run `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/ scripts/`,
      `uv run mypy src/ scripts/`, `uv run pyright`, and `uv run python scripts/check_test_mapping.py`.
- [ ] 2.5 Write `openspec/changes/2026-09-26-test-205-csv-tier-gaps/verify-report.md` with the actual
      command output.

## Phase 3: Archive

- [ ] 3.1 Append PC-U07 to `openspec/specs/parquet-conversion/spec.md` (the archive-time sync).
- [ ] 3.2 Move the change directory to `openspec/changes/archive/2026-09-26-test-205-csv-tier-gaps/`
      and write `archive-report.md`.
- [ ] 3.3 Re-run `uv run python scripts/check_test_mapping.py` after the archive (bijection must hold).
