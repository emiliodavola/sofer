# Proposal: fix-scan-raw-and-codebook-index-cache

## Intent

Fix `raw/ -> cache/ -> build/` contract:

- **Bug 1 — scan:** creates `raw/` but not MOVE of `.csv/.tsv/.xlsx/.jsonl/.parquet` with subfolder tree. Correct is MOVE preserving `relative_to(base_dir)` into `raw/`.
- **Bug 2 — codebook:** `generate_all` writes `cache/codebooks/*` but index to `base_dir/codebook.md`. Must be `cache/codebook.md` (`codebook.py:441`).

User clarifies: MOVE, not copy.

## Scope

### In Scope
- scan MOVE: loose files → `raw/<relative>`, tree preserved, `mkdir -p`, collision check before any move.
- scan flags: `--dry-run` preview, `--force` skip prompt, else `[y/N]` abort with no partial moves.
- codebook: `root_path = write_root / "codebook.md"` when `output_dir is None`.
- specs/CLI/docs + tests.

### Out of Scope
- New formats, delimiter/encoding, `prepare`/`publish`.
- Removing `init --move-existing`.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `scan`: MOVE-to-raw preserving tree (SCN-07).
- `codebook`: index to `cache/codebook.md` (CB-R04).

## Approach

**Bug 1 — MOVE-preserving-tree** (reject 1A scaffold-only, 1B flatten mangling `a/b/x.csv`):
Discover files not under `raw/`/`cache/`/`EXCLUSIONS`; map `dest = raw_dir / rel`; check collisions vs existing `raw/` before `shutil.move`; then normal `raw/ -> cache/` copy/merge.

**Bug 2 — 2A one-liner** (`base_dir` → `write_root`). Reject 2B dual-write (contradicts spec).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py:_cmd_scan` | Modified | MOVE phase |
| `src/sofer/scanner.py` | Modified | tree MOVE helper |
| `src/sofer/codebook.py:441` | Modified | index to `write_root` |
| `openspec/specs/scan/spec.md` | Modified | SCN-07 |
| `openspec/specs/codebook/spec.md` | Modified | CB-R04 |
| `tests/test_codebook.py:556,573,591,679,772,806` | Modified | `cache/codebook.md` |
| `tests/test_scanner.py`, `tests/test_cli.py` | Modified | raw MOVE |
| `README*.md`, `docs/configuration.md` | Modified | docs |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 6 codebook tests encode bug | High | Fix in same commit |
| Scan tests assume copy-only | High | Update fixtures |
| Raw overwrite | Med | Pre-check; need `--force` |
| Users rely on `./codebook.md` | Med | Release note |
| `cache/` not gitignored | Low | Add to `.gitignore` |

## Rollback Plan

Revert `codebook.py:441` + tests; remove MOVE phase (moved files stay). Single commit.

## Dependencies

None (`shutil.move`, `config.RAW_DIR/OUTPUT_DIR`).

## Success Criteria

- [ ] loose `a.csv`+`sub/b.xlsx` → `raw/a.csv`+`raw/sub/b.xlsx`, originals gone, `cache/` copies exist.
- [ ] `--dry-run` prints `-> raw/...`, no FS/TOML change.
- [ ] collision `raw/a.csv` exists → fail before move, names both.
- [ ] `codebook --all-files` → `cache/codebook.md` + `cache/codebooks/*`, no root.
- [ ] `uv run pytest tests/ -q` + `ruff`/`mypy` green.
