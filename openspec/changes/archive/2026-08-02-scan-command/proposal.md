# Proposal: Scan Command

## Intent

Manually maintaining `[[file]]` entries is error-prone — users must list every file,
keep paths in sync, and remember to update on adds/removals. `data-uploader scan`
automates discovery, copies files to `data/`, and writes TOML, making the config
the single source of truth for all downstream commands (codebook, upload, validate).

## Scope

### In Scope
- New `scan` subcommand: recursive file discovery + TOML registration + copy-to-data
- Extensible format registry: `.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl` (v1)
- Idempotent TOML merge — no duplicate `[[file]]` entries on re-scan
- TOML write via `tomli_w`; preserve all non-`[[file]]` sections (`[dataset]`, `[meta]`, `[[check]]`, `[[quality]]`)
- `--dry-run` (report only) and `--force` (skip confirmation); copy-by-default
- Standard exclusion list: `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `build/`

### Out of Scope
- File format validation or content inspection (belongs to `validate`/`quality`)
- Converting discovered files (belongs to `parquet-conversion`)
- `--move` flag (deferred; copy-only for v1)
- Per-file custom remote path mapping
- `.gitignore`-aware scanning (deferred)

## Capabilities

### New Capabilities
- `scan`: Automated data-file discovery and TOML registration. Discovers supported
  formats, deduplicates against existing entries, copies to `data/` (preserving
  relative subdirectory structure), and writes updated TOML via `tomli_w`.

### Modified Capabilities
None. Existing commands consume TOML — scan produces it without changing their contracts.

## Approach

Three new components, following the existing architecture (one domain module per command):

1. **`_formats.py`** — `SUPPORTED_FORMATS: dict[str, str]` extension-to-label registry.
   Single source of truth; extensible by adding dict entries.
2. **`scanner.py`** — Four-phase orchestrator: `discover_files()` (recursive
   `pathlib.rglob` with exclusions), `merge_entries()` (resolve + deduplicate
   against existing `FileEntry` list by resolved path), `copy_files()` (`shutil.copy2`
   to `data/`, preserving subdirectory structure), `write_toml()` (serialise full
   config via `tomli_w.dumps()`).
3. **`cli.py`** — `scan` subparser wired via `set_defaults(func=_cmd_scan)`.
   CLI: `data-uploader scan [config.toml] [--dry-run] [--force] [--ext .ext]`.

TOML round-trip: `tomli.load()` → merge new `[[file]]` entries → `tomli_w.dumps()`.
Comment preservation is not guaranteed (`tomli_w` is write-only) — accepted tradeoff
per user decision.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/data_uploader/_formats.py` | New | Extension registry |
| `src/data_uploader/scanner.py` | New | Discovery, merge, copy, TOML write |
| `src/data_uploader/cli.py` | Modified | `scan` subparser + `_cmd_scan` |
| `src/data_uploader/__init__.py` | Modified | Docstring update |
| `pyproject.toml` | Modified | Add `tomli_w` dependency |
| `tests/test_scanner.py` | New | Scan logic tests |
| `tests/test_cli.py` | Modified | Subparser + flag tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TOML comment loss (tomli_w has no comment preservation) | Medium | Accepted — user chose tomli_w. Template comments survive as TOML string values. |
| Idempotency gaps — stale entries or missing files after manual changes | Medium | Resolve paths via base_dir for dedup; warn on missing registered files during scan. |
| Large trees slow scan (thousands of files) | Low | Hardcoded exclusion list; `rglob` is adequate for typical projects. |
| Cross-platform path separators | Low | Follow existing `PurePosixPath` pattern for TOML remote paths. |

## Rollback Plan

Revert commit. `scan` is purely additive — new modules + one new subparser. No existing
files lose functionality. If TOML was modified by scan, restore from git or backup.

## Dependencies

- `tomli_w` (new — lightweight, write-only TOML serialisation)
- `tomli` (already present for reading)

## Success Criteria

- [ ] `data-uploader scan dataset.toml` discovers all supported files and registers them
- [ ] Running scan twice produces identical TOML output (no duplicate entries)
- [ ] `data-uploader validate dataset.toml` passes on scan-produced config
- [ ] `--dry-run` reports planned changes without modifying disk or TOML
- [ ] Excluded directories (`.git/`, `.venv/`, etc.) never appear in scan results
- [ ] Copy preserves relative subdirectory structure inside `data/`; originals untouched
