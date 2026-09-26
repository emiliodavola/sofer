# Delta for parquet-conversion

> Change `2026-09-26-test-205-csv-tier-gaps` (issue #205). Canonical target:
> `openspec/specs/parquet-conversion/spec.md` §13. The behaviour requirement **PC-U01** is
> **unchanged**; this delta adds the **evidence** duty for the declared-dialect tier as **PC-U07**.
> The parent change `2026-09-14-fix-prepare-csv-config-tier` (#181) added PC-U01's declared-wins
> behaviour but left four test-quality gaps; this delta closes them.

## ADDED Requirements

### Requirement: Discriminating, version-stable evidence for the declared-dialect tier (PC-U07)

The test suite for PC-U01's declared-dialect tier SHALL carry **evidence that can fail**. The
integration test for the declared-wins path SHALL drive the dataset-TOML seam
(`DatasetConfig.from_toml`, which alone populates `declared_meta_keys`) and SHALL assert the produced
Parquet's **true column count/names**, not the mere presence of a `.parquet` file — a mis-detected
delimiter collapses the header into one column and would satisfy an existence-only assertion. At
least one declared-wins case SHALL use a delimiter **outside** `config.SNIFF_DELIMITERS`
(`[";", ",", "\t"]`), so honouring the declaration is the only way to pass.

The JSONL fallback path of `_convert_jsonl_to_parquet` SHALL be exercised by a test that forces the
fast path to fail and asserts the fallback's **measured** behaviour; the code comment SHALL describe
that behaviour, not a hoped-for one.

The undeclared byte-identity evidence SHALL derive its reference **at test time** from the
pre-change read shape; it SHALL NOT depend on a frozen digest of pyarrow-version-dependent output
bytes. The byte-identity claim (the undeclared path adds no `read_options`) SHALL remain asserted.

The boundary around a programmatically constructed `DatasetConfig` SHALL be **explicit**: a dialect
value supplied without the `declared_meta_keys` presence signal SHALL take the sniff fallback, the
decision SHALL be recorded under the change's design (ADR), and the behaviour SHALL be pinned by a
test. Redesigning the presence signal is out of scope unless the boundary is first re-decided.

#### Scenario: The declared-wins integration test fails against a mis-split

- GIVEN the CSV dialect plumbing test
- WHEN the dataset declares `csv_delimiter = "|"` through the TOML seam and the file is `|`-separated
- THEN the staged Parquet SHALL hold the file's true column count and column names
- AND a one-column mis-split SHALL fail the assertion (the test's discriminating power is the column
  count, not the presence of `data.parquet`)

#### Scenario: A declared-wins case cannot pass by sniff coincidence

- GIVEN a declared-wins unit test over a delimiter **outside** `config.SNIFF_DELIMITERS` (e.g. `|`)
- WHEN the conversion runs with the declaration present
- THEN it SHALL produce the file's true columns
- AND without the declaration the same input would collapse to one column, so the test cannot pass by
  coincidence

#### Scenario: The JSONL fallback is exercised and its real behaviour asserted

- GIVEN a JSONL file whose later record carries a key absent from its first record, and a forced
  failure of `pyarrow.json.read_json`
- WHEN `_convert_jsonl_to_parquet` runs the fallback
- THEN it SHALL still write a Parquet file via `json` + `pa.Table.from_pylist`
- AND the test SHALL assert the measured schema-from-first-record behaviour (a later-only key is
  dropped; the parity check is advisory) and the code comment SHALL match it

#### Scenario: The undeclared byte-identity evidence is derived at test time

- GIVEN the undeclared-dialect byte-identity test
- WHEN it establishes its reference output
- THEN the reference digest SHALL be computed from the recreated pre-change read shape with the
  installed pyarrow, not from a frozen literal
- AND the emitted Parquet bytes SHALL equal that reference

#### Scenario: The programmatic-config boundary is decided and pinned

- GIVEN a programmatic `DatasetConfig(csv_delimiter="|")` with an empty `declared_meta_keys`
- WHEN the conversion runs
- THEN it SHALL take the sniff fallback (the declaration is not observed without the presence signal)
- AND the decision SHALL be recorded in the change design and pinned by a test

## Evidence (AGENTS.md rule 6)

`parquet-conversion` carries no `## Test Mapping` section (it is a registered spec in
`openspec/test-mapping-registry.md`), so this delta records its scenario→test evidence here and in
the change's verify report.

| Scenario | Test |
|----------|------|
| Declared-wins integration fails against a mis-split | `tests/test_parquet_conversion.py::TestDelimiterPlumbing::test_custom_delimiter_used_via_upload` (rewritten through the declared-TOML seam; RED/GREEN recorded) |
| Declared-wins case cannot pass by sniff coincidence | `tests/test_converters.py::TestCsvDialectResolution::test_declared_pipe_outside_sniff_set_wins` |
| JSONL fallback exercised and real behaviour asserted | `tests/test_converters.py` (new fallback test) |
| Byte-identity evidence derived at test time | `tests/test_parquet_conversion.py::TestUndeclaredDialectByteIdentical::test_undeclared_dialect_matches_prechange_bytes` (rewritten) |
| Programmatic-config boundary decided and pinned | `tests/test_converters.py::TestCsvDialectResolution` (new boundary test) |
