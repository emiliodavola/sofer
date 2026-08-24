# Design: Data Quality Checks

## Technical Approach

Add a `data-quality` capability that inspects CSV **content** after structural validation passes and before upload. A new `QualityValidator` in `quality.py` runs 9 P0 streaming checks via a shared `_csv_reader.py` generator, produces a `ValidationReport`, and integrates into both `validate` and `upload` CLI commands. Configurable via an optional `[[quality]]` TOML section; sensible built-in defaults mean checks run even without configuration.

## Architecture Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Module split | (a) Single `quality.py`, (b) `quality.py` + `_csv_reader.py` | **b** | `_csv_reader.py` is a utility reused by both quality checks and future consumers; separation keeps quality.py focused on check logic |
| Streaming reader shape | (a) Return all rows, (b) Generator yielding `(header, row)` | **b** | Generator never loads full dataset; stops at `max_sample`. First yield has `row=None` so callers always get header before data |
| Encoding fallback | (a) Try utf-8-sig, then utf-8, then latin-1, then cp1252, (b) utf-8-sig → utf-8 → ValueError | **a** | Latin-1 and Windows-1252 are the most common non-UTF-8 encodings in real-world CSV data. Python's utf-8 decoder is NOT lenient enough to cover them — it rejects bytes 0x80–0x9F (common in Windows-1252) and many multi-byte sequences. The 4-step chain (utf-8-sig → utf-8 → latin-1 → cp1252) avoids false positives while still catching truly binary files. Plain utf-8 is kept for consistency even though it shares the same decoder as utf-8-sig |
| Severity model | (a) 3 tiers (error/warn/info), (b) 2 tiers (fail/warn) | **b** | Maps directly to `ValidationReport.errors` / `warnings`. `fail` → `errors.append()`, `warn` → `warnings.append()` |
| Built-in defaults | (a) No [[quality]] → skip all, (b) No [[quality]] → run all P0 with defaults | **b** | Proposal spec: quality is always on. Users must explicitly opt out. `value_range` is the only check skipped without config (needs min/max) |
| Format consistency reuse | (a) Write new type inference, (b) Reuse `codebook.infer_column_type` | **b** | Avoids duplication; `infer_column_type` is already stdlib-only and tested |
| Cross-file types | (a) Single-pass merge, (b) Collect per-file types, compare after scan | **b** | Post-scan comparison is simple and cheap (schema is tiny vs data volume) |
| Duplicate detection | (a) Bloom filter, (b) Set of row hashes | **b** | Set-of-hashes works for P0 volumes (100K sample, typical CSVs < 1M rows). Bloom filter is a P1 optimisation for multi-GB files |
| Value range tracking | (a) Store all values, (b) Streaming min/max only | **b** | Only need min/max — no sorting, no storage of all values. O(1) memory per tracked column |
| Single-pass interleaving | (a) Each check opens files independently, (b) `QualityValidator` opens each file once via `stream_csv`, distributes rows to all active check accumulators | **b** | Eliminates 9× read amplification (each P0 check reading every file independently). One pass populates all per-file accumulators; cross-file checks finalize after all files are scanned |

## Data Flow

```
config.validate() ──→ structural checks ──→ QualityValidator.run() ──→ upload()
                         (checks.py)       (quality.py)                (unchanged)
                                              │
                           stream_csv() per file (single pass;
                             distributed to all active checks)
                                        │
                          ┌───────────────┼───────────────────┐
                     encoding_val   P0 checks (7)        cross_file_types
                     (pre-scan,     (interleaved          (post-scan)
                      same fallback  single-pass)
                      chain as
                      stream_csv)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_csv_reader.py` | Create | Generator `stream_csv()`: yields `(header, row)`, encoding fallback utf-8-sig→utf-8→latin-1→cp1252, `max_sample` cap, empty-file handling |
| `src/sofer/quality.py` | Create | `QualityValidator` class with 9 `_check_*()` methods, `run()` → `ValidationReport` |
| `src/sofer/model.py` | Modify | Add `QualityCheck`, `QualityConfig`, `QualityResult` dataclasses; `from_toml()` parses `[[quality]]` |
| `src/sofer/checks.py` | Modify | Add `ValidationReport.quality_results: list[QualityResult]`. `print_summary()` iterates `quality_results` in a dedicated `─── Quality checks ───` section (only when non-empty) |
| `src/sofer/cli.py` | Modify | `_cmd_validate` and `_cmd_upload` call `QualityValidator(cfg).run()`, assign `report.quality_results` from returned report |
| `tests/test_quality.py` | Create | Unit tests for every P0 check, following `test_checks.py` patterns |

## Interfaces / Contracts

```python
# model.py additions
@dataclass
class QualityCheck:
    check: str                                       # P0 check identifier
    severity: str = "warn"                           # "warn" | "fail"
    columns: list[str] | None = None                 # None = all columns
    max_null_pct: float | None = None                # for null_profiling
    min: float | None = None                         # for value_range
    max: float | None = None                         # for value_range
    min_unique: int | None = None                    # for duplicates
    ignore_values: list[str] | None = None            # for format_consistency

@dataclass
class QualityConfig:
    checks: list[QualityCheck] = field(default_factory=list)  # user overrides only; QualityValidator merges with built-in defaults
    default_severity: str = "warn"
    max_sample: int = 100_000

@dataclass
class QualityResult:
    check: str                                 # check identifier
    severity: str                              # "warn" | "fail"
    message: str                               # human-readable description

# quality.py
class QualityValidator:
    def __init__(self, cfg: DatasetConfig) -> None: ...
    def run(self) -> ValidationReport: ...

# _csv_reader.py
def stream_csv(
    path: Path, delimiter: str = ";",
    encoding: str = "utf-8-sig", max_sample: int = 100_000,
) -> Generator[tuple[list[str], list[str] | None], None, None]:
    """Yields (header, row). First yield has row=None (header only)."""
```

## Integration

```
cfg = DatasetConfig.from_toml(args.config)        # unchanged
config_errors = cfg.validate()                     # unchanged
if config_errors: return 1                         # unchanged

validator = DatasetValidator(cfg)
report = validator.run_all()                       # structural checks (unchanged)

quality = QualityValidator(cfg)                    # NEW
quality_report = quality.run()                     # NEW — returns ValidationReport
report.quality_results = quality_report.quality_results  # NEW — QualityResult list, not flat merge

report.print_summary()
return 0 if report.passed else 1                   # unchanged
```

Quality results are stored separately from structural errors/warnings via the
`QualityResult` dataclass. `print_summary()` iterates `quality_results` in a
dedicated section. This keeps findings separable — structural and quality
results are never interleaved.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|---------|
| Unit | `stream_csv` normal, encoding fallback, sample cap | `tmp_path` + `_make_csv` helper, following `test_checks.py` |
| Unit | Each `_check_*` with known-good / known-bad CSVs | One test per scenario from the spec (pass/fail per check) |
| Unit | `QualityConfig.from_toml` parsing | Full `[[quality]]` section, empty, unknown check names |
| Unit | `ValidationReport.print_summary` quality section | Capture stdout with `capsys` |
| Integration | `_cmd_validate` + `_cmd_upload` with quality merge | Full CLI invocation via `CliRunner` or `tmp_path` config |

## Migration / Rollout

No migration required. Quality is entirely additive — existing TOML configs without `[[quality]]` get built-in defaults automatically. All existing tests pass unchanged.

## Open Questions

None. All design decisions are resolved by the spec.
