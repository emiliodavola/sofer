# Tasks: feat/mcp-init-tool — Expose `sofer init` as MCP tool `sofer_init`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 220-280 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (feat/mcp-init-tool → dev) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | sofer_init + registration + tests + docs | PR 1 → dev | Single PR; `_contained_path` + `_INIT_TEMPLATE` + `check_flatten_collisions`; `pytest -q` green |

## Phase 1: Core Implementation

- [x] 1.1 Add imports in `src/sofer/mcp_server.py` — `from .cli import _INIT_TEMPLATE`, `from .scanner import move_to_raw`, `SUPPORTED_FORMATS`, `sofer_config.RAW_DIR` — no new module
- [x] 1.2 Implement `sofer_init(name: str, move_existing: bool=False, dry_run: bool=False, force: bool=False) -> dict` in `src/sofer/mcp_server.py` under `_tool_execution` + `_capture_output` — empty `name.strip()` → `{ok:False,config_errors}`, `_contained_path(f"{name}.toml", root=_get_root(), extensions=(".toml",))`, exists+`force` gate, `check_flatten_collisions(candidates+existing, base_dir)` on `ValueError` → `{ok:False,exit_code:1}`, `dry_run` skips `mkdir`/`move_to_raw` but writes TOML + preview `a.csv -> raw/a.csv`, `raw_dir.mkdir(exist_ok=True)` otherwise, `Path(toml_path).write_text(_INIT_TEMPLATE.format(name=name))`, `move_to_raw(candidates, base_dir, raw_dir)` when `move_existing`
- [x] 1.3 Update module docstring in `src/sofer/mcp_server.py` — `10 callables (8 logical)` → `11 callables (9 logical)` and pipeline comment

## Phase 2: Wiring

- [x] 2.1 Register `sofer_init` in `_register_tools(server: _FastMCP)` in `src/sofer/mcp_server.py` as 11th `server.tool(sofer_init)` — update function docstring `10→11` roster
- [x] 2.2 Map errors to envelope — `PathOutsideRootError` via `_contained_path` propagates as `ToolError`, idempotency/collision/empty return `{ok:False,exit_code:1}` with captured `output`/`config_errors`

## Phase 3: Testing

- [x] 3.1 Update `tests/test_mcp_server.py` roster — `TestToolRoster::test_exactly_ten_callables` → `test_exactly_eleven_callables` asserts 11 callables and `sofer_init` schema (`name` required string, 3 bools default false) via `Client.list_tools()`
- [x] 3.2 Add scenario tests (INIT-01) in `tests/test_mcp_server.py` using `build_server(root=tmp_path)` — Creates TOML+raw (assert `tmp/my-ds.toml == _INIT_TEMPLATE.format(name="my-ds")` + `raw/` exists + `DatasetConfig.from_toml` parses `cfg.name=="my-ds"`), dry_run no mutation (seed `a.csv`, assert no `raw/` and `output` contains `a.csv -> raw/a.csv`), collision `a.csv`+`raw/a.csv` → `{ok:False}` no move, traversal `../evil`/`/abs`/`C:/evil` → `PathOutsideRootError`/`ok:False` no escape
- [x] 3.3 Add idempotency/force/tree tests in `tests/test_mcp_server.py` — `force=false` does not overwrite existing TOML, `force=true` overwrites and `{ok:True}`, `move_existing` preserves `relative_to(root)` tree (`a/b/x.csv` → `raw/a/b/x.csv` via `move_to_raw`)

## Phase 4: Docs & Verification

- [x] 4.1 Update `README.md` — MCP table: `10 tool callables` → `11`, add row `sofer_init | name!, move_existing?, dry_run?, force? | toml+raw/preview | none`, sync counter in "AI and MCP server" section
- [x] 4.2 Update `README_ES.md` — same MCP table row + counter sync as `README.md` (content stays English for commands/filenames)
- [x] 4.3 Verify `uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest tests/ -q` green and stdio handshake `sofer-mcp` clean framing — no cross-call `config` residue
