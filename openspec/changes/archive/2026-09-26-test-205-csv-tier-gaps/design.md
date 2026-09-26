# Design — `2026-09-26-test-205-csv-tier-gaps`

## Technical Approach

Change only test evidence, plus one comment. The conversion logic in `src/sofer/_converters.py` is
**not** modified beyond the inaccurate JSONL comment (F2). Each finding gets the smallest test edit
that makes it able to fail; F5 is recorded as an accepted boundary (ADR-4) and pinned by a test.

## Architecture Decisions

### ADR-1 — F1 asserts through the declared-TOML seam and checks the column count

**Choice:** rewrite `TestDelimiterPlumbing::test_custom_delimiter_used_via_upload` to build the
config with the module's `_declared_cfg` helper (which writes a dataset TOML with `[meta]
csv_delimiter = "|"` and loads it via `DatasetConfig.from_toml`), run `publish`, then read the staged
Parquet and assert `num_columns == 2` and `column_names == ["col1", "col2"]`.
**Alternatives:** keep the programmatic config and add `declared_meta_keys` by hand (works, but
bypasses the XML/TOML seam the real users hit); assert the Parquet schema instead of the file's
existence (same idea, less explicit).
**Rationale:** `declared_meta_keys` is only populated by `from_toml` (model.py:541), so the TOML seam
is the production path. A mis-detected delimiter collapses the header into one column, so the column
count is precisely the discriminator the old assertion missed.

### ADR-2 — F2 forces the fallback and asserts its real behaviour

**Choice:** a test that monkeypatches `pyarrow.json.read_json` to raise, converts a small JSONL whose
second record carries a key absent from the first, and asserts the fallback produced a Parquet whose
schema comes from the **first** record (the later-only key is dropped) and that the parity warning is
advisory (conversion still succeeds).
**Alternatives:** (a) fix `from_pylist` to union keys — rejected: product change, out of #205 scope;
(b) only narrow the comment — rejected: the issue prefers a real assertion, and the path is
untested (`_converters.py` fallback body).
**Rationale:** the fallback is reachable only when the fast path raises, which a deterministic test
can force. Asserting the measured pyarrow 25.0.0 behaviour is honest; the comment is corrected to
match.

### ADR-3 — F3 adds a dedicated `|` declared-wins case

**Choice:** add `test_declared_pipe_outside_sniff_set_wins` to
`tests/test_converters.py::TestCsvDialectResolution`. `|` ∉ `config.SNIFF_DELIMITERS`, so without the
declaration the reader would collapse three columns into one.
**Alternatives:** parametrise the existing `;`/`,` cases over `[";", ",", "|"]` — accepted in spirit;
a dedicated case is chosen to keep the existing assertions and names stable while adding the one
discriminating input.
**Rationale:** a `;`/`,` file is sniffed to the same delimiter, so those tests cannot distinguish
"declared wins" from "sniff happened to agree". `|` can.

### ADR-4 — F5: the programmatic-`DatasetConfig` boundary is ACCEPTED

**Choice:** keep the presence signal as the contract of record. A programmatic
`DatasetConfig(csv_delimiter="|")` with an empty `declared_meta_keys` **does not** override; it takes
the sniff fallback. Pin this with a test that asserts the collapsed (one-column) result, and document
the decision here.
**Alternatives:** (a) make the value sufficient regardless of provenance — rejected: it would reverse
the merged #181 design D1 and reintroduce the "declared `;` vs declared nothing" ambiguity that
`declared_meta_keys` exists to remove; (b) drop the presence signal — rejected: same reason, plus 244
`DatasetConfig(...)` call sites depend on the defaults.
**Rationale:** nothing in `src/sofer/` constructs a `DatasetConfig` programmatically with a dialect,
so the boundary is reachable only by library consumers, who can set `declared_meta_keys` themselves.
The `model.py` `declared_meta_keys` docstring already states it; the test makes it enforceable.

### ADR-5 — F4 derives the reference digest at test time

**Choice:** recreate the pre-change read shape inside the test — sniff the delimiter with
`_sniff_csv_delimiter(csv, config.CSV_ENCODING)`, `pyarrow.csv.read_csv` with **no** `read_options`,
and write through the same `_write_parquet_table` — then compare the two Parquet files byte-for-byte.
**Alternatives:** (a) keep the literal and pin pyarrow — rejected: a version pin is heavier and the
literal is exactly the brittle artifact; (b) assert only semantic equality — weaker than the
byte-identity claim PC-U01 makes.
**Rationale:** both digests are produced with the installed pyarrow at test time, so a permitted
upgrade moves both sides together and cannot break the assertion for the wrong reason. The claim
"the undeclared path adds no `read_options`" is still exercised.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `tests/test_converters.py` | Modify | F3: add the `\|` declared-wins case; F2: add the JSONL-fallback test. |
| `tests/test_parquet_conversion.py` | Modify | F1: rewrite the plumbing test through the declared-TOML seam; F4: remove the frozen digest and derive a reference at test time; F5: pin the programmatic boundary. |
| `src/sofer/_converters.py` | Modify (comment only) | F2: correct the `from_pylist` "union" comment to the measured behaviour. |
| `openspec/specs/parquet-conversion/spec.md` | Modify | Add PC-U07 (test-evidence contract for the declared-dialect tier). |
| `openspec/changes/2026-09-26-test-205-csv-tier-gaps/**` | Create | This change's SDD artifacts. |

## Interfaces / Contracts

No public interface changes. The test-only contract added by PC-U07:

```text
The declared-dialect tier's evidence SHALL be discriminating (fails against a mis-split),
SHALL include a delimiter outside config.SNIFF_DELIMITERS, SHALL exercise the JSONL fallback,
SHALL re-derive byte-identity at test time, and SHALL pin the programmatic-config boundary.
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Declared-wins over an out-of-sniff delimiter; programmatic-boundary fallback | `tests/test_converters.py::TestCsvDialectResolution` and the pinned boundary test |
| Unit | JSONL fallback real behaviour | `tests/test_converters.py` with `pyarrow.json.read_json` monkeypatched to raise |
| Integration | `publish` plumbing through the declared-TOML seam | `tests/test_parquet_conversion.py::TestDelimiterPlumbing` |
| Regression | Undeclared byte-identity | `tests/test_parquet_conversion.py::TestUndeclaredDialectByteIdentical`, reference derived at test time |
| Gate | Suite/lint/types/checker | `uv run pytest tests/ -q`, ruff, mypy, pyright, `scripts/check_test_mapping.py` |

## Threat Matrix

No new process-integration, network, or file-system boundary is introduced: this change adds tests
and a comment. The only subprocess used in the change's evidence is the pre-existing pytest run. N/A.

## Migration / Rollout

No migration and no feature flag. The tests land with the corrected comment, so the branch is green
from the first commit.

## Open Questions

None. F1–F4 are test-only; F5 is decided (accepted) and pinned.
