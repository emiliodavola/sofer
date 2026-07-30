# Exploration: Data Quality Checks for data-uploader

## Current State

The data-uploader already has a validation pipeline in `checks.py` that runs **before** any upload:

- `DatasetValidator` checks file existence, minimum file count, total size threshold, and CSV column presence
- Uses a `ValidationReport` model with two severity levels: `errors` (blocks upload) and `warnings` (advisory)
- The TOML config uses a catch-all `[[check]]` section that mixes threshold config (`min_files`, `min_total_size_mb`) with column expectations (`columns` + `expected`)
- Schema profiling already exists in `repo_compliance.py` (column type inference, missing% per column, unique counts) — but it's **only used** for the Dataset Card generation, never for validation
- No duplicate detection, null profiling, format consistency checks, or encoding validation exists

### Existing building blocks

| Component | Location | Relevant to quality? |
|-----------|----------|---------------------|
| `DatasetConfig` (dataclass) | `model.py` | Yes — needs extension for quality config |
| `ValidationReport` | `checks.py` | Yes — report model with errors/warnings |
| `DatasetValidator` | `checks.py` | Yes — framework exists, needs new checks |
| `ColumnSchema` (dataclass) | `repo_compliance.py` | Yes — schema already has dtype, nullability, missing% |
| `build_schema_report` | `repo_compliance.py` | Yes — CSV sampling + type inference exists |
| `infer_column_type` | `codebook.py` | Yes — can be reused for format validation |
| CLI `validate` command | `cli.py` | Yes — entry point for quality checks |
| CLI `upload` command | `cli.py` | Yes — blocks on validation failure |

## Affected Areas

- `src/data_uploader/model.py` — Add `QualityConfig` dataclass and `[[quality]]` TOML section
- `src/data_uploader/checks.py` — Extend `DatasetValidator` with quality checks (or new `QualityValidator`)
- `src/data_uploader/repo_compliance.py` — (minor) expose `_read_csv_sample` for reuse
- `src/data_uploader/cli.py` — Wire quality checks into `validate` and `upload` commands
- `tests/test_checks.py` — Add tests for all quality checks
- `pyproject.toml` — Possibly add optional quality dependencies? (see analysis below)
- `openspec/specs/data-quality/spec.md` — New spec domain for data quality

## Approaches

### 1. Extend existing `DatasetValidator` in `checks.py`

Add new `_check_*` methods to the existing `DatasetValidator` class. The `[[check]]` TOML section gets optional quality sub-keys (e.g., `detect_duplicates = true`, `max_null_pct = 5.0`).

- **Pros**: Minimal new code. Reuses `ValidationReport`, `csv.reader` loop infrastructure. Follows existing pattern exactly.
- **Cons**: The `[[check]]` section is already overloaded (thresholds + column checks). Adding quality config there makes it harder to read. `DatasetValidator` currently reads all files once per check — quality checks need streaming access to avoid O(n^2) reopenings.
- **Effort**: Low (if we keep it simple)

### 2. New `quality.py` module with `QualityValidator` class

Separate module for data quality checks. Uses a dedicated `[[quality]]` TOML section. Inherits the `ValidationReport` model for consistency but has its own run loop.

```toml
[[quality]]
check = "duplicates"
severity = "warn"

[[quality]]
check = "null_threshold"
columns = ["age", "income"]
max_null_pct = 10.0
severity = "fail"

[[quality]]
check = "value_range"
columns = ["age"]
min = 0
max = 120
severity = "fail"
```

- **Pros**: Clean separation of concerns. Quality config is self-documenting. The `[[check]]` section stays focused on structural validation (files, sizes, column presence). Easier to test independently.
- **Cons**: More files. Slight duplication of the sampling/reading infrastructure unless we extract a shared CSV reader utility.
- **Effort**: Medium

### 3. Hybrid: Extract shared CSV reader, extend both

Refactor CSV reading into a shared utility (`_csv_reader.py` or within `checks.py`). Add quality checks as a separate pass (not interleaved with structural checks). The quality pass emits to the same `ValidationReport` but is configured via `[[quality]]`.

- **Pros**: Best of both worlds. Shared reader prevents O(n^2) file reopening. Clean config separation. Structural checks and quality checks can run independently (structural first, then quality).
- **Effort**: Medium

## Recommendation

**Approach 3 (Hybrid)** with these specifics:

### Configuration: New `[[quality]]` TOML section

Create a `QualityCheck` dataclass in `model.py`:

```python
@dataclass
class QualityCheck:
    check: str                        # check type identifier
    severity: str = "warn"            # "warn" or "fail"
    columns: list[str] | None = None  # scoped columns (None = all)
    max_null_pct: float | None = None
    min: float | int | None = None    # for value_range
    max: float | int | None = None
    min_unique: int | None = None     # for uniqueness checks
```

The existing `[[check]]` TOML section stays as-is for structural checks. Quality checks go in `[[quality]]`.

### Architecture: New `quality.py` module

```
src/data_uploader/
├── checks.py          # structural checks (file existence, size, columns)
├── quality.py         # NEW — data quality checks (duplicates, nulls, formats, ranges, etc.)
├── _csv_reader.py     # NEW — shared streaming CSV reader utility
├── model.py           # extend: QualityCheck, QualityConfig dataclass
├── cli.py             # wire: run quality checks after structural checks
```

The `quality.py` module owns:

| Check | Implementation | Severity model | Large-file safe? |
|-------|---------------|----------------|------------------|
| **duplicates** | Compare line count vs unique-line count (set-based). For row-level, track hash of each row. | warn (configurable) | ✅ Streaming — one line at a time |
| **empty_rows** | Detect rows where all fields are empty/NA/null sentinel. | warn (configurable) | ✅ Streaming |
| **empty_columns** | Detect columns where all values are empty/NA/null across sample or full scan. | warn (configurable) | ⚠️ Full scan needed for accuracy, but still streaming |
| **null_profiling** | Per-column null% with configurable threshold. Reuse `infer_column_type` logic. | configurable per-column | ✅ Streaming — just counters |
| **format_consistency** | Detect mixed types within a column (numeric+text in same column). Reuse `infer_column_type` numeric ratio logic. | warn (configurable) | ✅ Streaming |
| **corrupt_records** | Detect inconsistent row lengths, CSV parsing errors (exception-based). | fail (hard) | ✅ Streaming — first-pass |
| **value_range** | Configurable min/max per column. | configurable per-column | ✅ Streaming — track min/max |
| **cross_file_types** | Same column name in multiple CSVs → compatible dtypes? | warn | Requires all files sampled |
| **encoding_validation** | Detect non-UTF-8 files before CSV parsing. | fail (hard) | ✅ One read pass |
| **outlier_detection** | IQR-based outlier flagging in numeric columns. | warn (configurable) | ⚠️ Needs stddev pass + second pass for IQR (or use streaming percentile approximation) |

### Threshold model

| Severity | Behavior | TOML default |
|----------|----------|--------------|
| `"fail"` | Blocks upload. Exits with code 1. Orange ✗ in report. | Default for: corrupt_records, encoding_validation |
| `"warn"` | Reported but does NOT block upload. Yellow ⚠ in report. | Default for: duplicates, empty_rows, format_consistency, outliers |

The user can override severity per-check in TOML: `severity = "fail"` on any check.

### Dependencies: stdlib only

| Check | Dependencies | Rationale |
|-------|-------------|-----------|
| duplicates | `csv`, `hashlib` (optional for row hashing) | Set-based dedup, no pandas needed |
| empty_rows | `csv` | Row iteration, simple |
| null_profiling | `csv` | Counter per column |
| format_consistency | `csv` | Reuse `infer_column_type` from `codebook.py` |
| corrupt_records | `csv` | Catch `csv.Error`, count `len(row)` |
| value_range | `csv` | Simple min/max tracking |
| encoding_validation | `codecs` (stdlib) | `codecs.lookup()` or try/except on open |
| cross_file_types | `csv` | File-by-file comparison of inferred types |
| outlier_detection | `csv`, `statistics` (stdlib ≥ 3.10) | `statistics.median` for IQR — requires a two-pass approach or streaming percentile. For v1, skip or keep as P1. |

`statistics` module is stdlib in Python 3.10+. No new runtime dependencies are needed.

**If numpy were available**, outlier detection and value range checks would be simpler and faster. But it's not a dep, and adding it just for this is not justified. We can add optional numpy support later via `[quality.extra]` extras.

### Integration with existing pipeline

```
config.validate()          ← model.py: validate TOML structure
       ↓
DatasetValidator.run_all() ← checks.py: structural checks (files, sizes, columns)
       ↓
QualityValidator.run()     ← quality.py: data quality checks (NEW)
       ↓
(if passed) upload()       ← uploader.py: generate compliance + upload
```

**Design decision**: Quality checks run AFTER structural checks. Rationale: no point profiling nulls in a file that doesn't exist or has wrong columns. But quality checks run BEFORE schema report (which is inside `upload()`), so the user gets quality feedback without triggering a full upload attempt.

**Output format**: The existing `ValidationReport` model is reused for quality checks. A new `print_quality_report()` method or section is appended to the output. Optionally, a `--json` flag for machine-readable output.

### Comparison with industry standards

| Standard | What it says | How this maps |
|----------|-------------|---------------|
| **Great Expectations** | Expectation suites (column_map, column_pair, table-level). Data Assistant auto-profiles. | We don't need the framework — just the *concept* of configurable expectations. Our `[[quality]]` section IS an expectation suite in TOML form. |
| **ISO 8000** | Syntactic (format, encoding), semantic (accuracy, consistency), pragmatic (timeliness). | Our P0 covers syntactic + basic semantic. Full semantic (cross-dataset accuracy) is out of scope for a single-dataset uploader. |
| **DAMA DMBOK** | Six dimensions: completeness, uniqueness, timeliness, validity, accuracy, consistency. | Completeness → null_profiling, empty_rows. Uniqueness → duplicates. Consistency → format_consistency, cross_file_types. Validity → value_range. |
| **HF Ecosystem** | Dataset Viewer: basic stats only. Dataset Card: manual limitations section. No quality library. | We provide what HF doesn't: automated, configurable quality guarantees before data reaches the hub. |
| **Pandas profiling / ydata-profiling** | Rich HTML report with correlations, quantile stats. | Too heavy (pandas dep). Our approach is lighter but gives less visual richness. Acceptable for a CLI tool. |

### Risks

1. **Large file performance** — Some checks (outliers, empty_columns for full scan) may be O(n) but still slow on multi-GB CSVs. Mitigation: default sampling (first 100K rows, configurable via `max_sample`). For full-scan checks (duplicates, corrupt_records), streaming is naturally O(n) but memory-efficient.

2. **False positives in format consistency** — A column that is "mostly numeric" but has a few text codes like "NA" or "MISSING" could trigger false format warnings. Mitigation: ignore known missing-value sentinels before type inference, configurable via `ignore_values` in config.

3. **TOML config gets verbose** — Per-column thresholds for 200-column datasets could make the config file unwieldy. Mitigation: support a `default_severity` at the top of `[[quality]]` and only override per-column when needed.

4. **No numpy for IQR** — Streaming percentile (P25/P75) for outlier detection without numpy requires either storing all values (memory risk) or using a streaming algorithm (T-Digest, P² algorithm). Mitigation: keep outliers as P1, or implement P² algorithm (~50 lines of stdlib math).

## Ready for Proposal

Yes. The exploration phase has answered all 6 questions from the deliverable. The hybrid approach (new `quality.py` + shared CSV reader + `[[quality]]` TOML section + stdlib-only deps) is well-defined and maps cleanly onto existing code patterns without introducing debt.

The orchestrator should tell the user:
- **No new heavy dependencies** — everything uses stdlib (csv, statistics, codecs)
- **Quality checks are opt-in** via `[[quality]]` TOML sections, with sensible defaults
- **Existing `validate` and `upload` commands** will automatically include quality checks
- **Warn vs fail per check** is configurable in the TOML
- **Large files are handled** via streaming + configurable sampling
