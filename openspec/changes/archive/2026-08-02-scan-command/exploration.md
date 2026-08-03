# Exploration: scan-command

## Current State

The `data-uploader` CLI (`cli.py`) uses argparse subparsers with a `func` dispatch pattern. Four commands exist today: `init`, `validate`, `upload`, `codebook`. Datasets are registered in TOML via `[[file]]` entries, each with a `local` path (relative to the TOML's directory, resolved via `_base_dir`) and a `remote` path for the HF repo. There is no automated discovery — users manually list files.

### Key architecture pieces

| Component | File | Relevant to scan? |
|-----------|------|-------------------|
| CLI subparser registration | `cli.py:_build_parser()` | Yes — scan needs a new subparser + `_cmd_scan` |
| `func` dispatch pattern | `cli.py:main()` → `args.func(args)` | Yes — exact same pattern |
| `DatasetConfig.from_toml()` | `model.py:203-369` | Yes — scan must read existing TOML |
| `DatasetConfig` dataclass | `model.py:113-369` | Yes — `files: list[FileEntry]` is the target |
| `FileEntry` dataclass | `model.py:17-39` | Yes — `local`, `remote` paths; `resolve()` |
| TOML serialization | **Nonexistent** | Critical gap — no `to_toml()` or TOML writer |
| `_cmd_init` template | `cli.py:87-158` | Reference — manual TOML string generation |
| CSV/Parquet handling | `uploader.py` | No — scan doesn't convert, it discovers |
| Codebook generation | `codebook.py` | No — but future: codebook could consume scan output |
| `_sentinels.py` | Shared sentinel values | No |
| `checks.py` | `DatasetValidator` | No — but validate must work post-scan |

### File extension handling today

There is NO centralized format/extension registry. Extensions are handled ad-hoc:
- `uploader.py:848`: checks `remote_lower.endswith(".csv")` or `.parquet`
- `codebook.py`: assumes CSV via `csv.reader`
- No module knows about `.xlsx` at all

## Affected Areas

- `src/data_uploader/cli.py` — New subparser for `scan`, new `_cmd_scan` function, new `_SCAN_DESCRIPTION` help text
- `src/data_uploader/model.py` — Optional: `write_toml()` class method, `DatasetConfig.to_toml()`, or a new `_formats.py` for the extension registry
- `src/data_uploader/scanner.py` — **NEW MODULE**: scan logic, file walking, TOML merging
- `src/data_uploader/__init__.py` — Minor: update docstring to mention `scan`
- `tests/test_cli.py` — Parser tests for new subparser + `--flags`
- `tests/test_scanner.py` — **NEW**: scan logic tests (file discovery, TOML merge, move)
- `pyproject.toml` — Optional: `openpyxl` dependency if `.xlsx` support is in scope for the initial delivery
- `openspec/specs/scan/` — **NEW SPEC DOMAIN**: requirements for the scan command

## Approaches

### 1. New `scanner.py` module + `_formats.py` registry

Create two new modules:
- `_formats.py`: A constant `SUPPORTED_FORMATS: dict[str, str]` mapping extension → label (e.g., `{".csv": "CSV", ".parquet": "Parquet", ".xlsx": "Excel"}`). This is the single source of truth for what `scan` discovers.
- `scanner.py`: Contains `scan_project()`, `merge_files()`, `move_files()`, and `write_toml()` (or a dedicated `_toml_writer.py`).

CLI wires `_cmd_scan` → `scanner.scan_project(config_path, move=False, dry_run=False)`.

- **Pros**: Clean separation of concerns. The format registry is reusable by future commands. Easy to extend — just add to the dict. Scan logic is testable independently of CLI.
- **Cons**: Two new files. TOML writing is a new capability that needs design (preserve comments? preserve structure?).
- **Effort**: Medium

### 2. Inline scan in `cli.py` + format list in `model.py`

Add scan logic directly in `_cmd_scan()`, and put the format list as a constant in `model.py` or `__init__.py`.

- **Pros**: Fewer files. Simpler for a small feature.
- **Cons**: CLI module gets bloated. Scan logic untestable without CLI harness. Violates the existing pattern where all four commands delegate to domain modules (`validate`→`checks.py`, `upload`→`uploader.py`, `codebook`→`codebook.py`).
- **Effort**: Low (but technical debt)

### 3. Extend `DatasetConfig` with scan + write methods

Add `DatasetConfig.scan_directory()` and `DatasetConfig.to_toml()` as methods on the existing dataclass. The CLI just calls them.

- **Pros**: Keeps model + behavior together. Feels "OO".
- **Cons**: `DatasetConfig` is currently a pure data class (plus `from_toml` and `validate`). Adding filesystem-scanning and TOML-writing responsibilities violates single-responsibility. The dataclass would grow to ~600+ lines.
- **Effort**: Low-Medium

## Recommendation

**Approach 1** — new `scanner.py` module + `_formats.py` registry. This follows the existing architectural pattern where each command domain has its own module (`checks.py`, `codebook.py`, `uploader.py`, `quality.py`). The `_formats.py` module mirrors `_sentinels.py` and `_csv_reader.py` — small, focused, shared utility modules.

### Detailed design sketch

```
src/data_uploader/
├── _formats.py          ← NEW — SUPPORTED_FORMATS dict
├── scanner.py           ← NEW — scan_project(), merge_entries(), reorganize_files()
├── model.py             ← MODIFIED — (only if to_toml() lives here; see open question)
├── cli.py               ← MODIFIED — new subparser + _cmd_scan
└── __init__.py          ← MODIFIED — docstring update
```

**`_formats.py`**:
```python
SUPPORTED_FORMATS: dict[str, str] = {
    ".csv": "CSV",
    ".parquet": "Parquet",
    ".xlsx": "Excel",
}
```

**`scanner.py`** responsibilities:
1. `discover_files(root: Path, formats: dict[str, str]) -> list[Path]` — recursive walk, skip `.git/`, `__pycache__/`, skip files already inside `data/`
2. `build_entries(discovered: list[Path], existing: list[FileEntry], base_dir: Path) -> list[FileEntry]` — generate `FileEntry` objects, deduplicate against existing entries, assign `remote` paths
3. `reorganize_files(entries: list[FileEntry], data_dir: Path, dry_run: bool) -> list[tuple[Path, Path]]` — move files from original location to `data/<relative-path>`, return (old_path, new_path) mapping
4. `generate_toml(cfg: DatasetConfig, entries: list[FileEntry]) -> str` — serialize config to TOML string, preserving `[dataset]` and `[meta]` sections, regenerating `[[file]]` sections

**CLI interface**:
```
data-uploader scan [config.toml] [--move] [--dry-run] [--force]
```
- `config`: Path to TOML config file (creates if doesn't exist)
- `--move`: Actually move files to `data/` (default: only register)
- `--dry-run`: Show what would happen, don't write/move anything
- `--force`: Skip confirmation prompts
- `--ext`: Additional extensions to scan (e.g., `--ext .jsonl --ext .tsv`)

### Deduplication strategy

Compare `FileEntry.resolve(base_dir)` resolved paths. If a discovered file's absolute path matches an existing entry's resolved path, skip it. This handles both:
- Files already registered (no duplicate `[[file]]` blocks)
- Files already in `data/` that were previously moved

### TOML writing strategy

Since the project has no TOML writer, and `tomli` is read-only, the options are:
1. **`tomlkit`** (read-write TOML, preserves comments): Adds a dependency but is the cleanest approach
2. **Manual string generation** (like `_cmd_init` template): No new dependency but brittle — comments and custom sections are lost
3. **`tomli-w`** (write-only TOML): Lightweight, no comment preservation

**Recommendation**: `tomlkit` — it preserves comments and user formatting, which is critical when modifying an existing TOML that the user has customized. However, this is a new dependency decision that needs user sign-off.

## Risks

1. **TOML comment/structure loss** — If writing TOML without `tomlkit`, user's comments and custom sections are destroyed. This is a catastrophic UX failure for a tool whose config is the source of truth. **Severity: HIGH**.

2. **File move safety** — Moving user files is destructive. A bug could scatter data files. Must have `--dry-run` and confirmation prompts. The `--move` flag should default to `False` for safety. **Severity: HIGH**.

3. **xlsx dependency** — Adding `.xlsx` support requires `openpyxl` as a dependency. This has cascading effects: CI, pre-commit, potential binary wheels on different platforms. If xlsx is deferred to a follow-up, the architecture must make it trivial to add later. **Severity: MEDIUM**.

4. **Large project trees** — Scanning a project with thousands of files (especially in `node_modules/`, `.venv/`, etc.) could be slow. Must skip well-known exclusion directories. **Severity: LOW** (mitigated by `.gitignore`-aware walking or explicit exclusions).

5. **Cross-platform path behavior** — Path handling on Windows (`\ ` vs `/`) combined with TOML root needing `/` for remote paths. The existing code already uses `PurePosixPath` for remote paths — scan must do the same. **Severity: LOW** (existing patterns handle this).

6. **Config with no `_base_dir`** — `DatasetConfig._base_dir` defaults to `Path()`, which resolves to CWD. If scan is called without a config path, or on a config that was loaded without a proper base_dir, path resolution could be wrong. **Severity: MEDIUM**.

7. **Idempotency gaps** — If a user moves a file manually after `scan`, then runs `scan` again, the tool should detect the file is missing from its registered location and warn (not silently create a duplicate). **Severity: MEDIUM**.

## Edge Cases to Handle

| Case | Behavior |
|------|----------|
| No TOML config exists | Create new TOML from template (reuse `init` pattern but with discovered files) |
| TOML exists with custom `[meta]` | Preserve all non-file sections unchanged |
| TOML has `recursive=true` directory entries | Skip files already covered by directory entries; warn if conflicts |
| File with same name in different dirs | OK — different `local` paths → distinct `FileEntry` |
| Files inside `data/` already | Skip (already organized) |
| Files in `.git/`, `__pycache__/`, `.venv/` | Always excluded from scan |
| Hidden files (dot-prefixed) | Excluded by default (`.gitignore`-aware) |
| Empty files (0 bytes) | Include them — `validate` will catch issues later |
| Windows path separators in TOML | Always normalize to `/` in TOML output |
| `scan` run from subdirectory | Resolve relative to config's `_base_dir`, not CWD |
| Already-registered file was deleted | Warn during scan, mark or remove from TOML |

## Open Questions (for proposal phase resolution)

1. **TOMl writing approach**: `tomlkit` (dep, preserves comments) vs `tomli-w` (lightweight, loses comments) vs manual string generation (brittle). This is the single biggest architectural decision.

2. **xlsx scope**: Include in initial delivery or defer? Including it means adding `openpyxl` as a dependency.

3. **Default exclusion list**: Should scan respect `.gitignore`? Use a hardcoded exclusion list? Both? Standard exclusions: `.git`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `dist`, `build`, `.eggs`.

4. **`--move` default**: Should it default to `False` (safe) or `True` (the stated goal is reorganization)? Recommendation: `False` for safety.

5. **Remote path auto-generation**: Currently `remote` is free-form. After `scan`, should `remote` be auto-generated as the filename (flat) or the relative path (preserves structure)? E.g., `data/otra-carpeta/file3.csv` → `remote = "otra-carpeta/file3.csv"` or `remote = "file3.csv"`?

6. **Interaction with `init` command**: Should `scan` on a new project also run `init`-like template generation? Or should the user run `init` first, then `scan`?

7. **What happens to existing `[[file]]` entries that point to files NOT discovered by scan?** Keep them (user-added)? Remove them (stale)? Warn about them?

## Ready for Proposal

**Yes.** The architecture fit is clean — this is a new command that follows the same pattern as all existing commands (domain module + CLI subparser + func dispatch). The main decisions that need user input during proposal are:

1. TOML writing library choice (`tomlkit` vs alternatives)
2. Whether xlsx is in scope for v1
3. The default for `--move` flag behavior
4. Remote path auto-generation strategy

The orchestrator should present these as focused questions in the proposal phase, not as an overwhelming menu.
