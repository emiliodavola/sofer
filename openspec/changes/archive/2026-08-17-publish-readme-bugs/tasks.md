# Tasks: publish-readme-bugs

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~260–330 (incl. tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (`fix/publish-readme-bugs` → `dev`), 4 work-unit commits |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

Single PR confirmed: estimate is under the 400-line threshold; no size exception needed.

## Phase 1 — WU1 / Fix 4: config + shared unique helper (foundation)

- [x] 1.1 RED: add failing tests — sentinel columns excluded from `unique` (CB-R07, PRF-02, RC-R10); footnote uses configured sample size (monkeypatched `[tool.sofer] schema_sample_size`)
- [x] 1.2 GREEN: add `count_unique_non_missing(values: Iterable[str]) -> int` to `src/sofer/_sentinels.py` (filters ""/sentinels, `len(set(...))`)
- [x] 1.3 GREEN: add `schema_sample_size: 10_000` to `_DEFAULTS` in `src/sofer/config.py`; export `SCHEMA_SAMPLE_SIZE`
- [x] 1.4 GREEN: replace inline unique logic in `repo_compliance.py` (~:500 parquet, ~:563 CSV), `codebook.py` (~:291), `profile.py` (~:213) with the helper
- [x] 1.5 GREEN: delete `_SCHEMA_SAMPLE_SIZE` (`repo_compliance.py:35`) → import from config; generate f-string footnote from value (~:861)
- [x] 1.6 GREEN: `cli.py:606` `--max-sample` default → `CODEBOOK_MAX_SAMPLE` (CB-R08)
- [x] 1.7 Document `schema_sample_size` (commented example) under `[tool.sofer]` in `pyproject.toml`
- [x] 1.8 Run `uv run pytest tests/test_codebook.py tests/test_profile*.py tests/test_repo_compliance.py -q` → green

## Phase 2 — WU2 / Fix 2: column origin + num_examples

- [x] 2.1 RED: failing tests in `tests/test_repo_compliance.py` — `ColumnSchema.origin` populated on parquet (`origin_name`) and CSV (`local.name`) paths; Data Fields renders `File` column without `::` prefix (RC-R05/R06); num_examples = exact rows (Parquet `pf.metadata.num_rows`, CSV `len(rows)`); multi-file train split sums counts (RC-R07: 30+40=70); fallback `CARD_FALLBACK_ROWS_PER_FILE × files` (D7)
- [x] 2.2 GREEN: add `origin: str = ""` to `ColumnSchema` (`repo_compliance.py`); populate in both sampling paths
- [x] 2.3 GREEN: add `build_schema_report_with_rows(...) -> tuple[list[ColumnSchema], dict[str, int]]` delegating to same body (D1); `build_schema_report` stays byte-compatible
- [x] 2.4 GREEN: `prepare.py:724` switches to `build_schema_report_with_rows`; pass `row_counts` into `build_dataset_card(..., row_counts=...)`
- [x] 2.5 GREEN: card emits single train split with `num_examples = sum(row_counts.values())`; footnote uses `SCHEMA_SAMPLE_SIZE`
- [x] 2.6 Verify backward compat: existing callers of `build_schema_report` untouched; suite green

## Phase 3 — WU3 / Fix 3: delivered paths in Data Structure

- [x] 3.1 RED: failing RC-R08 tests in `tests/test_repo_compliance.py` — converted CSV shows `.parquet` remote; CSV listed only when `keep_csv=True`; `upload_as_csv` → declared csv; recursive tree paths
- [x] 3.2 GREEN: `build_dataset_card` gains `keep_csv: bool = False` kwarg; render Data Structure from `_mirror.planned_remotes(cfg, keep_csv)` (D3); drop `e.local` usage
- [x] 3.3 Remove dead `"::"` skip guards (`build_dataset_card`:719, :855); update stale `filename::` docstring in `build_schema_report` (~:414-417)
- [x] 3.4 Verify no import cycle (`_mirror` imports `.model` only); suite green

## Phase 4 — WU4 / Fix 1: publish auto-prepare + PUB-08

- [x] 4.1 RED: pin mtimes via `os.utime` in setup (source newer than parquet = stale); new `test_autoprepare_generates_codebooks` fails first; REVERSE `test_publish.py:695` (fresh bare-prepare build → assert PUB-08 warning text + rc==0 + nothing staged); add PUB-08 negative test (complete build → capsys asserts NO warning, rc==0)
- [x] 4.2 GREEN: `publish.py:598` auto-prepare call → `prepare(cfg, source, force=True, all_files=True)`
- [x] 4.3 GREEN: PUB-08 warning printed before hf staging when `_collect_codebook_remotes(source)` empty; delivery proceeds
- [x] 4.4 Confirm `test_codebooks_staged_in_staging:677` (explicit `--all-files` happy path) still passes

## Phase 5 — Verification & delivery

- [x] 5.1 `uv run pytest tests/ -q` → 688+ pass, none removed
- [x] 5.2 `uv run ruff check . && uv run ruff format --check . && uv run mypy src/` clean
- [x] 5.3 Update README if CLI defaults surfaced there; fill `.github/PULL_REQUEST_TEMPLATE.md` with real command output
- [x] 5.4 Branch `fix/publish-readme-bugs` off `dev`; one commit per work unit (WU1→WU4); single PR to `dev`
