# Design: Scan Command

## Technical Approach

Three additive components following the existing one-module-per-command pattern: a format registry (`_formats.py`), a scan orchestrator (`scanner.py`), and CLI wiring in `cli.py`. The scan command discovers data files recursively, deduplicates against existing `[[file]]` entries by resolved destination path, copies to `data/`, and writes the full TOML via `tomli_w.dumps()` — preserving all non-`[[file]]` sections by operating on the raw `tomli.load()` dict rather than reconstructing from `DatasetConfig`.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| TOML preservation strategy | (A) Reconstruct from `DatasetConfig`, (B) Load raw dict → modify `[[file]]` → dump | **B** | Only B preserves all unknown keys and `[[check]]`/`[[quality]]` arrays that `DatasetConfig` doesn't model as raw TOML. Comment loss is accepted (proposal §Approach). |
| Dedup key | (A) Source file path, (B) Destination `data/` path (resolved), (C) `remote` string | **B** | Matches spec SCN-02: existing entry `local = "data/survey.csv"` resolves to `/abs/data/survey.csv`; discovered `raw/survey.csv` → computes dest `data/survey.csv` → same resolved path → skipped. |
| Discovery API | (A) Generator (`yield`), (B) Return `list[Path]`, (C) Class with callbacks | **B** | Simplest contract; `rglob` already eager. List enables dry-run reporting without re-scanning. Sorted for idempotency (SCN-05). |
| Exclusion method | (A) `.gitignore` patterns, (B) Hardcoded set in walk filter | **B** | Proposal excludes `.gitignore`-aware scanning from v1 scope. |
| Error boundary | (A) Scanner catches and logs, (B) Scanner raises, CLI catches | **B** | Follows existing pattern: domain modules raise, `_cmd_*` handlers catch and return exit codes (see `_cmd_init`, `_cmd_validate`). |

## Data Flow

```
user: sofer scan [config.toml] [--dry-run] [--force] [--ext .ext]
  │
  ▼
_cmd_scan(args)
  │  1. Load raw TOML dict via tomli.load(config_path)
  │  2. Determine base_dir = config_path.parent, data_dir = base_dir / "data"
  │  3. discover_files(base_dir, extensions, EXCLUSIONS) → list[Path]
  │  4. merge_entries(discovered, raw_toml, base_dir, data_dir)
  │     ── mutates raw_toml["file"] in-place
  │  5. copy_files(discovered, base_dir, data_dir, dry_run, force)
  │     ── raises FileExistsError if dest collision without --force
  │  6. write_toml(raw_toml, config_path)  [skipped if dry_run]
  │  7. Print summary → return 0
```

## Module Contracts

### `_formats.py`

```python
SUPPORTED_FORMATS: dict[str, str]  # extension → human label
# Keys: ".csv", ".tsv", ".parquet", ".xlsx", ".jsonl"
```

No functions. Extending means adding one dict entry. Consumers import `.keys()` for filtering.

### `scanner.py`

```python
EXCLUSIONS: frozenset[str]  # {".git", "__pycache__", ".venv", "node_modules", "dist", "build"}

def discover_files(
    root: Path,
    extensions: Iterable[str] | None = None,
) -> list[Path]:
    """Recursive walk. Skips dirs in EXCLUSIONS. Filters by suffix.
    Returns sorted absolute Paths."""

def merge_entries(
    discovered: list[Path],
    raw_toml: dict[str, Any],
    base_dir: Path,
    data_dir: Path,
) -> dict[str, Any]:
    """Appends new `[[file]]` entries to raw_toml['file'].
    Dedup: resolve dest path `data_dir / discovered_file.relative_to(base_dir)`;
    skip if any existing entry's `FileEntry.local.resolve(base_dir)` matches.
    New entries: `local = "data/<relative>"`, `remote = PurePosixPath(relative)`.
    Returns mutated raw_toml."""

def copy_files(
    discovered: list[Path],
    base_dir: Path,
    data_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> list[tuple[Path, Path]]:
    """shutil.copy2 to data_dir, preserving relative subdirs.
    Lazily creates parent dirs. dry_run reports without copying.
    Raises FileExistsError on dest collision unless force=True."""

def write_toml(raw_toml: dict[str, Any], config_path: Path) -> None:
    """tomli_w.dumps() → overwrite config_path."""
```

### `cli.py` additions

```python
def _cmd_scan(args: argparse.Namespace) -> int:
    """Orchestrate the full scan pipeline. Catch all exceptions, print to stderr, return 1."""
```

Subparser: `scan` with positional `[config]` (nargs="?", default="dataset.toml"), flags `--dry-run`, `--force`, `--ext` (choices from `SUPPORTED_FORMATS.keys()`).

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_formats.py` | Create | `SUPPORTED_FORMATS` dict |
| `src/sofer/scanner.py` | Create | `discover_files`, `merge_entries`, `copy_files`, `write_toml` |
| `src/sofer/cli.py` | Modify | New `scan` subparser + `_cmd_scan` handler + imports |
| `src/sofer/__init__.py` | Modify | Add `scan` to docstring usage block |
| `pyproject.toml` | Modify | Add `tomli_w` to `dependencies` |
| `tests/test_scanner.py` | Create | Unit + integration tests |
| `tests/test_cli.py` | Modify | `scan` subparser parsing tests |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — `_formats` | Dict shape, all values are strings | Single assertion test |
| Unit — `discover_files` | Filter by extension, prune excluded dirs, `--ext` override, empty results | `tmp_path` fixture tree + exact list assertion |
| Unit — `merge_entries` | Dedup by resolved path, section preservation, new entry shape (`local`/`remote`) | Build raw TOML dicts, call merge, assert `tomli_w.dumps()` output |
| Unit — `copy_files` | Subdir creation, dry-run no-op, FileExistsError without `--force` | `tmp_path` source tree; assert dest exists, source untouched |
| Integration | Full `_cmd_scan` pipeline — verify output TOML parses via `DatasetConfig.from_toml()` and `cfg.validate()` passes | `tmp_path` with real file tree + TOML fixture |
| CLI | Subparser wiring: `scan dataset.toml`, `--dry-run`, `--force`, `--ext .csv`, default config | Follow `test_cli.py::TestParser` pattern |

## Open Questions

- [ ] Should `_cmd_scan` handle missing config by offering to run `_cmd_init`? Spec SCN-06 says error + exit 1 — conservative, but a UX improvement for later.
