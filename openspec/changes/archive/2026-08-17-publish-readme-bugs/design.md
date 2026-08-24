# Design: publish-readme-bugs

## Technical Approach

Four surgical fixes on the branch `fix/publish-readme-bugs`, ordered WU1→WU4 so the
shared helper (WU1) lands before its consumers. Estimated diff: ~260–330 lines
including tests → **single PR, four commits** (one per work unit). Under the 400-line
chained-PR threshold; proposal already recommended single PR.

## Architecture Decisions

| # | Decision | Options | Choice & Rationale |
|---|----------|---------|--------------------|
| D1 | `num_examples` flow | (a) change `build_schema_report` return type; (b) attach counts to `ColumnSchema`; (c) thin wrapper `build_schema_report_with_rows() -> tuple[list[ColumnSchema], dict[str, int]]` delegating to the same body | **(c)**. (a) breaks 30 callers; (b) duplicates a file-level fact onto every column. Wrapper keeps `build_schema_report` byte-compatible (returns `[0]`); only `prepare.py:724` switches to the full variant. Row counts collected in the same single pass: Parquet via `pf.metadata.num_rows` (exact, free — handle already returned by `_read_parquet_sample`), CSV via `len(rows)` (`_read_csv_sample` already reads the whole file). Dict keyed by origin filename; card sums values. |
| D2 | Shared unique helper | (a) duplicate filter in 4 sites; (b) helper in `_sentinels.py` | **(b)**. All four buggy sites already import `MISSING_VALUE_SENTINELS` from there; module is dependency-free. Signature: `count_unique_non_missing(values: Iterable[str]) -> int` — filters empty/sentinel values, returns `len(set(...))`. Replaces `repo_compliance.py:500,563`, `codebook.py:291`, `profile.py:213`. AGENTS rule 4. |
| D3 | Delivered-path reuse | (a) reimplement mapping; (b) `repo_compliance` imports `_mirror.planned_remotes` | **(b)**. Verified no cycle: `_mirror` imports only `.model` (TYPE_CHECKING); `model` imports neither. `planned_remotes(cfg, keep_csv)` already encodes conversion/`upload_as_csv`/`recursive`/`keep_csv` semantics (RC-R08). Drop `e.local` entirely. |
| D4 | File column vs grouped sections | grouped sections per file; flat table + `File` column | Flat + File column — spec RC-R06 decision. Dedup guarantees ≤1 row per name, so the table stays truthful; avoids restructuring YAML/markdown consumers. Names rendered WITHOUT any `::` prefix; the `"::" in s.name` skip guards (`build_dataset_card:719,855`) become dead code once origin is structural — remove them. **When removing those guards, also update `build_schema_report`'s docstring (~`repo_compliance.py:414-417`)**, which still documents the `filename::` disambiguation behavior that no longer exists. |
| D5 | `ColumnSchema.origin` | `str \| None = None`; `str = ""` | `origin: str = ""` — spec said `None` but every render site then needs None-checks; `""` renders as `-`. Safe: all constructors use kwargs (verified). Populated from existing `origin_name` (parquet path, `repo_compliance.py:443-450`) / `local.name` (CSV path, `:533`). |
| D6 | Auto-prepare semantics | force-regenerate codebooks always; `all_files=True` only when prepare actually runs | **all_files=True on the auto-prepare call** (`publish.py:598`). Key finding: `_needs_prepare` (`publish.py:391-423`) keys on parquet mtimes only — it does NOT know about codebooks. So after an explicit bare `prepare`, the build is fresh, auto-prepare skips, and no codebooks exist. That residual gap is covered by PUB-08: warn before hf delivery when `_collect_codebook_remotes(source)` is empty, then deliver (exit 0). |
| D7 | Fallback & keying policy for row counts | (a) skip files without schema coverage; (b) fall back to estimate; (c) rekey counts by full path | **(b) with basename keying kept (MVP).** Row counts are collected only for files that go through `build_schema_report`'s sampling paths. Datasets containing non-schema files — recursive directory trees, `upload_as_csv` entries, files excluded by `include_in_schema` — contribute NO row counts. When no counts exist at all (or as documented fallback), `num_examples` falls back to `CARD_FALLBACK_ROWS_PER_FILE × file count`. Counts dict stays keyed by origin **basename**; same-name collisions across directories overwrite each other's count. Documented as a known MVP limitation, not fixed here. |

### Fix 1 exact behavior matrix (test_publish.py:695 reversal)

| Scenario | Behavior | Test |
|----------|----------|------|
| Stale/missing build → `publish` | auto-prepare runs with `all_files=True` → codebooks staged | NEW: `test_autoprepare_generates_codebooks` |
| Fresh bare-`prepare` build → `publish` | no regen; nothing staged; **PUB-08 warning printed**; exit 0 | REVERSE `test_no_codebooks_means_nothing_codebook_staged`: same setup, assert warning text + rc==0 + nothing staged |
| Explicit `prepare --all-files` → `publish` | unchanged happy path | `test_codebooks_staged_in_staging:677` survives |

## Data Flow (Fix 2)

```
cfg.files ──► build_schema_report_with_rows(cfg, ..., staging_dir)
                 │  per entry: origin_name tracked (existing code)
                 ├─► list[ColumnSchema]        (+ origin="")
                 └─► dict[origin, rows]        (pf.metadata.num_rows | len(rows))
                        │
prepare.py ─────────────┴──► build_dataset_card(cfg, schema, row_counts=...)
                                ├─ Data Fields: +File column (s.origin)
                                ├─ single train split:
                                │    num_examples = sum(row_counts.values())
                                │    (exact per-file row counts summed —
                                │     NOT capped by sample size;
                                │     fallback: CARD_FALLBACK_ROWS_PER_FILE × files, D7)
                                └─ footnote: f"...{SCHEMA_SAMPLE_SIZE:,}-row sample..."
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_sentinels.py` | Modify | Add `count_unique_non_missing()` (D2) |
| `src/sofer/config.py` | Modify | `schema_sample_size: 10_000` in `_DEFAULTS`; export `SCHEMA_SAMPLE_SIZE` |
| `src/sofer/repo_compliance.py` | Modify | Delete `_SCHEMA_SAMPLE_SIZE` (:35) → config import; unique fix ×2; `origin` field + population; wrapper D1; File column; `num_examples`; delivered-path rendering via `planned_remotes` (D3, `keep_csv: bool = False` kwarg on `build_dataset_card`); f-string footnote (:861) |
| `src/sofer/codebook.py` | Modify | Use shared helper (:291) |
| `src/sofer/profile.py` | Modify | Use shared helper (:213) |
| `src/sofer/cli.py` | Modify | `--max-sample` default → `CODEBOOK_MAX_SAMPLE` (:606) |
| `src/sofer/publish.py` | Modify | `prepare(cfg, source, force=True, all_files=True)` (:598); PUB-08 warning before hf staging |
| `src/sofer/prepare.py` | Modify | Call `build_schema_report_with_rows`; pass `row_counts` to card |
| `pyproject.toml` | Modify | Document `schema_sample_size` under `[tool.sofer]` (commented example) |
| `tests/test_publish.py` | Modify | Reverse :695; add auto-prepare-codebooks test |
| `tests/test_repo_compliance.py` | Modify | Footnote literals (:1746,:1752) → configured value; new: origin/File column, num_examples, delivered paths, sentinel-free uniques |
| `tests/test_codebook.py`, `tests/test_profile*.py` | Modify | Sentinel-exclusion scenarios (CB-R07, PRF-02) |

## Interfaces / Contracts

```python
def count_unique_non_missing(values: Iterable[str]) -> int: ...
def build_schema_report_with_rows(
    cfg: DatasetConfig, csv_delimiter: str | None = None,
    csv_encoding: str | None = None, staging_dir: Path | None = None,
) -> tuple[list[ColumnSchema], dict[str, int]]: ...
@dataclass
class ColumnSchema:
    ...  # existing fields
    origin: str = ""   # source filename as sampled ("x.parquet" or "x.csv")
def build_dataset_card(cfg, schema, ..., row_counts: dict[str, int] | None = None,
                       keep_csv: bool = False) -> str: ...
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | helper, origin, footnote, num_examples, paths, warning | tmp_path fixtures; sentinel columns assert `unique` excludes sentinels; custom `schema_sample_size` via monkeypatched config |
| Integration | prepare+publish flow | Existing mocked-HF harness (`_mock_hf_api`, `_fixed_staging`) |
| Regression | full suite | `uv run pytest tests/ -q` — 422 passing, none removed |

**Mtime pinning (mandatory).** The reversed test (`tests/test_publish.py:695`)
and every mtime-sensitive test MUST pin file mtimes explicitly in setup with
`os.utime`: source files older than parquet for fresh-build paths, newer for
stale-build paths. This removes filesystem-timestamp-granularity flakiness
(same-second writes would make `_needs_prepare` nondeterministic).

**PUB-08 negative-scenario mapping.** Alongside the reversed warning test, add
a negative case: complete build (codebooks present) → `publish hf` → NO warning
printed. Assert via capsys that stderr/stdout does NOT contain the PUB-08
warning text, and rc==0 with codebooks staged.

## Migration / Rollout

No migration. Card YAML `dataset_info.splits[0].num_examples` changes value semantics
(sum-of-uniques → row count); HF accepts both. `keep_csv` defaults `False` in the card —
a user publishing with `--keep-csv` gets a card listing only parquet remotes unless
re-prepared; documented as accepted limitation.

## Open Questions

- [ ] None blocking. (Out of scope, documented: row-group-0 sampling bias.)
