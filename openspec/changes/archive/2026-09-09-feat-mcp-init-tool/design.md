# Design: feat/mcp-init-tool — Expose `sofer init` as MCP tool `sofer_init`

## Technical Approach

Thin adapter in `src/sofer/mcp_server.py` mirroring `sofer_scan_*`: `sofer_init` runs under `_tool_execution` + `_capture_output`, resolves `name→Path` via `_contained_path` under `_get_root()`, reuses `cli._INIT_TEMPLATE` and `scanner.check_flatten_collisions`, honours `dry_run`/`force`/`move_existing` without `input()`. Register as 11th callable in `_register_tools` (10/8 → 11/9). Envelope `{ok, exit_code, output, config_errors}`; containment violations → `PathOutsideRootError`.

Refs: `specs/mcp-server/spec.md` INIT-01 + MSP-R03.

## Architecture Decisions

### Decision: Template reuse

| Option | Tradeoff | Decision |
|---|---|---|
| Duplicate string in `mcp_server.py` | Drifts from CLI | Rejected |
| Import `_INIT_TEMPLATE` from `cli` | Single source, byte-identical TOML | **Chosen** |

**Rationale**: CLI already shares `config`/`scanner`; import guarantees parity.

### Decision: Containment for `name`

| Option | Tradeoff | Decision |
|---|---|---|
| Regex allow-list | Rejects legit dots, needs sync | Rejected |
| `Path(name).resolve()` vs cwd | Mutable, breaks CF-2 | Rejected |
| `_contained_path(f"{name}.toml", root=_get_root(), extensions=(".toml",), must_exist=False)` | Reuses CF-2 (`expanduser→root→resolve→is_relative_to`), covers `../`, abs, drive/UNC, symlink | **Chosen** |

**Rationale**: Empty `name` → `".toml"` → `{ok:false, config_errors}`. `_validate_output_targets` still checked for `raw/` containment.

### Decision: Collision detection

| Option | Tradeoff | Decision |
|---|---|---|
| Custom stem set | Diverges, false positives | Rejected |
| `check_flatten_collisions(candidates+existing_raw, base_dir)` | Exact CLI gate (`_cmd_init:886`), `ValueError→ok:false`, atomic | **Chosen** |

**Rationale**: `candidates` = depth-1 `SUPPORTED_FORMATS` excl. output name; `existing` = `raw/**` with `SUPPORTED_FORMATS`. Ensures `a.csv` vs `raw/a.csv` agreement.

### Decision: `dry_run`/`force`/`move_existing` without prompts

| Option | Tradeoff | Decision |
|---|---|---|
| Port `isatty`/`input()` | Blocks stdio, violates MSP-R06 | Rejected |
| `dry_run` skips TOML write | Breaks spec preview | Rejected |
| `dry_run`: no `mkdir`/`move_to_raw`, TOML written + preview `a.csv -> raw/a.csv`; `move_existing=false` scaffolds `raw/`; `force` gates only TOML overwrite | Spec-compliant | **Chosen** |

**Rationale**: MSP-R06: call is confirmation. `force` kept for schema parity. Guard precedes every mutation.

### Decision: Registration + error mapping

| Option | Tradeoff | Decision |
|---|---|---|
| New `mcp_init.py` | Splits pipeline entry | Rejected |
| Top-level `sofer_init` + `server.tool()` in `_register_tools` | One-file change, consistent with 10 existing | **Chosen** |

**Rationale**: Update module docstring/roster `10→11`. `force=false` + existing TOML → `{ok:false, exit_code:1}`; `force=true` overwrites. Hard errors → `PathOutsideRootError` → `ToolError`.

## Data Flow

```
sofer_init(name, move_existing?, dry_run?, force?)
  → _tool_execution + _capture_output
  → empty name? → ok:false
  → _get_root() → _contained_path(f"{name}.toml") [CF-2]
  → exists + force gate
  → if move_existing:
      candidates=depth-1 SUPPORTED_FORMATS, existing=raw/** 
      check_flatten_collisions(candidates+existing) → ok:false on ValueError
      dry_run? plan : move_to_raw()
  → raw_dir.mkdir unless dry_run → write _INIT_TEMPLATE.format(name)
  → {ok, exit_code, output, config_errors} / raise
```

No `config.reload` pre-write (no `DatasetConfig` yet).

## File Changes

| File | Action | Description |
|---|---|---|
| `src/sofer/mcp_server.py` | Modify | Add `sofer_init`; import `_INIT_TEMPLATE`, `move_to_raw`, `SUPPORTED_FORMATS`; update docstring + `_register_tools` |
| `src/sofer/cli.py` | Referenced | `_INIT_TEMPLATE` reuse |
| `src/sofer/scanner.py` | Referenced | `check_flatten_collisions`/`move_to_raw` reuse |
| `tests/test_mcp_server.py` | Modify | Roster 10→11, 4 scenarios (TOML+raw, dry_run, collision, traversal) |
| `README.md`+`README_ES.md` | Modify | MCP table 10→11 |

## Interfaces / Contracts

```python
def sofer_init(name: str, move_existing: bool=False, dry_run: bool=False, force: bool=False) -> dict[str, Any]:
    """Create <name>.toml from _INIT_TEMPLATE and scaffold raw/. Side effects: writes TOML + mkdir raw/ (unless dry_run); with move_existing moves depth-1 SUPPORTED_FORMATS into raw/ (no flatten). Network: none. UNTRUSTED note."""
```

Schema: `name` required string; booleans default `false`. Success `ok:true, exit_code:0`, TOML==`_INIT_TEMPLATE.format(name)` and `raw/` exists. Fail `ok:false, exit_code:1` for idempotency/collision/empty; containment → `raise PathOutsideRootError`.

```python
if not name.strip(): return {"ok":False,"exit_code":1,"output":"","config_errors":["name must be non-empty"]}
toml_path=_contained_path(f"{name}.toml", root=_get_root(), what="name", extensions=_CONFIG_EXTENSIONS, must_exist=False)
raw_dir=_get_root()/sofer_config.RAW_DIR
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Containment `../`, `/abs`, `C:/evil`, empty | `sofer_init` with `build_server(root=tmp)` → `PathOutsideRootError`/`ok:false`, no escape |
| Unit | TOML+raw creation, `DatasetConfig.from_toml` parses, `force` idempotency | `tmp_path` isolated |
| Unit | `dry_run` no mutation | Seed `a.csv`, assert no `raw/`, `output` has `a.csv -> raw/a.csv` |
| Unit | Collision `a.csv`+`raw/a.csv` | `ok:false`, no move |
| Unit | `move_existing` tree preserve | `raw/a.csv` exists |
| Integration | Roster 11, `name` required | `Client.list_tools()` |
| Integration | Stdio clean framing | Spawn `sofer-mcp` |

Checks: `uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest tests/ -q`.

## Migration / Rollout

No migration. Revert removes `sofer_init`+registration; TOML/`raw/` remain. Branch `feat/mcp-init-tool` → PR to `dev` (#102). READMEs synced same commit.

## Open Questions

- [ ] `move_existing` depth stays depth-1 (CLI parity) — no `recursive` flag now.
- [ ] `force` gates only TOML overwrite, not collision (always fatal).
- [ ] `raw_dir` override via `[tool.sofer] raw_dir` deferred — `root/RAW_DIR` default suffices.
