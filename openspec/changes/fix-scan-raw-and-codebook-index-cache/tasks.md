# Tasks: fix-scan-raw-and-codebook-index-cache

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 260–340 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (both fixes + tests + docs atomically) |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Scan MOVE + codebook `cache/codebook.md` + tests + docs/.gitignore | PR 1 → `dev` | Single PR; 1-line codebook fix ships with 6 test updates; scan MOVE is core |

## Phase 1: Foundation

- [x] 1.1 Add `check_raw_collisions(candidates, raw_dir, base_dir)` to `src/sofer/scanner.py` — `dest=raw_dir/rel` (`rel=src.relative_to(base_dir)`), raise `ValueError` naming both (#87)
- [x] 1.2 Add `move_to_raw(candidates, base_dir, raw_dir, *, dry_run=False)` to `src/sofer/scanner.py` — `mkdir(parents)`, `shutil.move`, no flatten (#87)
- [x] 1.3 Update `src/sofer/scanner.py` docstring: `raw/->cache/->build/`, MOVE-then-copy (#87)
- [x] 1.4 Fix `src/sofer/codebook.py:441` — `root_path=write_root/"codebook.md"` when `output_dir is None` (#88)

## Phase 2: Core — CLI MOVE-then-Copy

- [x] 2.1 Rewrite `_cmd_scan` in `src/sofer/cli.py` — P1 discover `EXCLUSIONS|{RAW_DIR,OUTPUT_DIR}` (5 exts), `raw_dir.mkdir` skip dry-run, `check_raw_collisions` atomic exit 1, `[y/N]`/`--force`/`--dry-run` gate, `move_to_raw`; P2 `check_flatten→merge→copy(raw→cache flatten)→write` (#87)
- [x] 2.2 Update `scan` parser help in `src/sofer/cli.py` — `mkdir -p raw/`, MOVE `relative_to`, `--dry-run` prints `-> raw/<rel>` (#87)

## Phase 3: Tests

- [x] 3.1 Update `tests/test_codebook.py` 6 asserts to `cache/codebook.md` (`:556,:573,:591,:679,:772,:806`), assert no `base_dir/codebook.md` (#88, CB-R04)
- [x] 3.2 Update `tests/test_scanner.py` — add `TestCheckRawCollisions`/`TestMoveToRaw` (tree, source gone, dry-run, EXCLUSIONS, `f.txt`), adapt MOVE semantics, idempotency (#87, SCN-07)
- [x] 3.3 Update `tests/test_cli.py` — e2e `a.csv`+`sub/b.xlsx` MOVE, dry-run no FS/TOML, collision fail, `N` abort, 5-exts vs `f.txt` (#87)

## Phase 4: Docs & Housekeeping

- [x] 4.1 Ensure `.gitignore` has `cache/` (#87, #88)
- [x] 4.2 Update `README.md`, `README_ES.md`, `docs/configuration.md` diagram `raw/DPTO.csv->cache/DPTO.csv` (#87)
- [x] 4.3 Verify `uv run pytest tests/ -q` + `ruff` + `mypy` green; manual scan/codebook flows (#87, #88)

## Dependencies & Order

1.4 before/parallel 1.1; 2.1 after 1.1–1.2; 3.1 after 1.4; 3.2–3.3 after 2.1; 4.x last.

## Estimates

P1 ~1.5h | P2 ~2h | P3 ~2h | P4 ~0.5h | Total ~6h

## Risks

- 6 codebook tests encode bug — ship fix+tests atomically.
- P1 must prune `.venv/.git/RAW_DIR/OUTPUT_DIR`; `f.txt` never moved.
- Collision check before first move; `N`/dry-run leaves TOML untouched.
