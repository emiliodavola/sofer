# Design: feat-profile-render-all-files

## Technical Approach

Replicate `codebook.generate_all:387-565` for `profile`/`render` as `generate_all_profiles`/`generate_all_renders`. Opt-in `--all-files` iterates `[[file]]` via `DatasetConfig.from_toml`; single-file gains `FileExistsError` guard gated by `--force`. Config adds `profile_dir="profiles"`/`render_dir="renders"` via `_DEFAULTS`+`PROFILE_DIR`/`RENDER_DIR` with `reload` rebinding. CLI/MCP mirror the contract; collisions are fail-loud (write non-colliding first, then `ValueError`).

## Architecture Decisions

### Decision: Batch algorithm

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Copy `generate_all` verbatim per domain | Duplicates logic, max fidelity | **Chosen** |
| Shared `_batch_helpers` abstraction | DRY, premature coupling | Rejected |
| Stem-only `a.metadata.yaml` | Loses `Labels/a.csv` distinction | Rejected |

Verbatim `base_dir`/`data_dir`/`rel_stem`+`PurePath.suffixes` prevents `a/b.csv` vs `c/b.csv` silent collision.

### Decision: Output layout

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Flat `profiles/`/`renders/` under `write_root` | Scannable, aligns with `cache/codebooks/` | **Chosen** |
| `docs/profiles/` default | Mixes artifact with publishable docs | Rejected — via `profile_dir` override |
| Per-dataset `<output>/<stem>/` | Deep, breaks flat convention | Rejected |

`docs/profiles` is a one-line TOML edit, no code fork.

### Decision: Force guard

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `exists()→FileExistsError("use --force to overwrite <path>")` | Fail-loud, hint aids migration | **Chosen** |
| Silent overwrite | Keeps bug | Rejected |
| Prompt `[y/N]` | Breaks CI/MCP | Rejected |

Breaking for 0.x, hint documents migration.

### Decision: MCP containment

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Extend `_validate_output_targets` with `profile_dir`/`render_dir` | Covers `../../evil` | **Chosen** |
| Contain only explicit `--output` | Leaves config escape | Rejected |

## Data Flow

```
Single: CLI --output/--force → profile()/render() → exists()?→ FileExistsError else write_text
Batch:  TOML → DatasetConfig.from_toml → validate + [[file]] check
        → base_dir, data_dir=base_dir/OUTPUT_DIR → entries (skip dir/missing/unsupported)
        → rel_stem = relative_to(data_dir) else relative_to(base_dir)
        → out=(write_root/profile_dir / rel_stem).with_suffix(suffixes→.metadata.yaml)
        → map output→[sources] → write non-colliding → ValueError naming colliding
Option B: relative --output anchors to base_dir; writes to <output>/profiles|/renders, never cache/
MCP: _contained_path(output) + _validate_output_targets + _reload_tool_config + _bound_discovery
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/config.py` | Modify | Add `profile_dir`/`render_dir` to `_DEFAULTS`, `PROFILE_DIR`/`RENDER_DIR`, `reload` |
| `src/sofer/profile.py` | Modify | `generate_all_profiles(cfg, output_dir?)` + `force` guard in `profile()` |
| `src/sofer/render.py` | Modify | `generate_all_renders(cfg, output_dir?)` + `force` guard in `render()` |
| `src/sofer/cli.py` | Modify | `--all-files`/`--force`/`--config` on `profile`/`render`; `_cmd_*` batch branches |
| `src/sofer/mcp_server.py` | Modify | Extend `sofer_profile`/`sofer_render`; extend `_validate_output_targets`, `_reload_tool_config` |
| `pyproject.toml` | Modify | Document `[tool.sofer] profile_dir`/`render_dir` |
| `tests/test_profile.py` | Modify | Batch, collision, Option B, config override, guard, `[[file]]` fail |
| `tests/test_render.py` | Modify | Mirror profile for `renders/` |
| `tests/test_cli.py` | Modify | Parser flags, dispatch, help accuracy |
| `tests/test_mcp_server.py` | Modify | Containment + batch parity |
| `tests/test_config.py` | Modify | Defaults/override/reload |

## Interfaces / Contracts

```python
def generate_all_profiles(cfg: DatasetConfig, output_dir: str | Path | None = None) -> list[str]: ...
def profile(dataset_path: Path, output_dir: Path | None = None, *, force: bool = False) -> int: ...
def generate_all_renders(cfg: DatasetConfig, output_dir: str | Path | None = None) -> list[str]: ...
def render(package_path: Path, output_dir: Path | None = None, *, force: bool = False) -> int: ...
# config
PROFILE_DIR: str  # "profiles"
RENDER_DIR: str   # "renders"
# mcp
def sofer_profile(dataset: str, output: str | None = None, *, all_files: bool = False, force: bool = False, config: str | None = None) -> dict[str, Any]: ...
def sofer_render(package: str, output: str | None = None, *, all_files: bool = False, force: bool = False, config: str | None = None) -> dict[str, Any]: ...
```

Paths: `<write_root>/<profile_dir>/<rel_stem>.metadata.yaml`, `<write_root>/<render_dir>/<rel_stem>.README.md` via `PurePath.suffixes` (last suffix→target). Errors: no `[[file]]`→non-zero mentioning `[[file]]`; collision→`ValueError` after partial write; single-file exists without `--force`→`FileExistsError("use --force to overwrite <dest>")`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit profile batch | N-files, nested `rel_stem`, collision+ValueError, Option B abs/rel, `cache/` untouched, `[[file]]` fail | `test_profile.py` temp TOML |
| Unit render batch | Same for `renders/*.README.md`; missing `metadata.yaml` skip | `test_render.py` |
| Force guard | `exists()`→`FileExistsError`+hint; `--force` overwrites | Both domain files |
| Config | Defaults `profiles`/`renders`, `docs/*` override, no hardcodes, `reload` | `test_config.py` |
| CLI | Flags `--all-files`/`--force`/`--config`/`--output`, TOML contract, help | `test_cli.py` |
| MCP | Containment `../../evil`, batch success+collision, bounded anchoring | `test_mcp_server.py` |

## Migration / Rollout

No data migration. Batch opt-in. Breaking: single-file without `--force` now errors — document in 0.x notes with `use --force` hint. Callers add `--force` to restore overwrite. Single PR, no flag.

## Open Questions

- [ ] None blocking. Deferred: per-dataset `[meta] profile_dir` override.
