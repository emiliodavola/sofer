# Proposal: feat/mcp-init-tool — Expose `sofer init` as MCP tool `sofer_init`

## Intent

`mcp_server.py` expone 10 callables/8 tools pero omite `init`; `cli.py::_cmd_init` es el único bootstrap. Agentes MCP no pueden crear TOML + `raw/` sin salir del canal. Agregar `sofer_init` con paridad CLI para habilitar bootstrap puro vía MCP.

## Scope

### In Scope
- `sofer_init` en `mcp_server.py::_register_tools` (→ 11/9 tools)
- Args `name: str` requerido (+ `move_existing`, `dry_run`, `force` bool False)
- CF-2: `name→Path` bajo `_get_root()` via `_contained_path`; `_validate_output_targets` para `output`
- Reuso `_INIT_TEMPLATE` y `check_flatten_collisions` (candidates + `raw/` existente)
- `_tool_execution` + `_capture_output`, envelope `{ok, exit_code, output, config_errors}`, docstring UNTRUSTED
- Tests `tests/test_mcp_server.py` + tabla `README.md`/`README_ES.md`

### Out of Scope
- HTTP/streamable, nuevos resources/prompts, cambios ladder `publish_confirm`, editar `cli.py`/`scanner.py`

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `mcp-server`: MSP-R03 roster 10/8 → 11/9 + escenarios `sofer_init`

## Approach

Thin adapter espejo de `sofer_scan_*`: `_tool_execution` + `_capture_output`; resolver `name→Path` vía `_contained_path` bajo `_get_root()`; `_reload_tool_config` + `_bound_discovery`; reusar `_INIT_TEMPLATE` y flujo `_cmd_init` sin `input()` (candidates depth-1 + `check_flatten_collisions` → exit 1); `dry_run` sin mkdir/move; `_validate_output_targets` pre-write.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modified | `sofer_init` + `_register_tools` |
| `src/sofer/cli.py` | Referenced | `_INIT_TEMPLATE` reusado |
| `src/sofer/scanner.py` | Referenced | `check_flatten_collisions` |
| `openspec/specs/mcp-server/spec.md` | Modified | Roster + escenarios |
| `tests/test_mcp_server.py` | Modified | 4 escenarios: TOML ok, dry_run, colisión, traversal |
| `README.md` + `README_ES.md` | Modified | Tabla tools |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Traversal `name` (`../`, abs, symlink) | Med | `_contained_path` + `is_relative_to` |
| Stem collision `raw/` | Med | `check_flatten_collisions` → exit 1 |
| `config.reload` leak | Low | Per-call `_reload_tool_config` bajo `_EXEC_LOCK` |
| dry_run muta | Low | Guard: no mkdir/move si `dry_run` |

## Rollback Plan

Revert commit: borrar `sofer_init` y registro. Sin migración; TOML/`raw/` quedan válidos.

## Dependencies

- `fastmcp>=3.4,<4`, `DatasetConfig`, `sofer.config`; sin `HF_TOKEN`/red

## Success Criteria

- [ ] `tools/list` incluye `sofer_init` con `name` req + 3 bools
- [ ] CF-2 traversal rechazado (`PathOutsideRootError`/`ok:False`)
- [ ] Reusa `_INIT_TEMPLATE` y `check_flatten_collisions`
- [ ] `dry_run` sin side-effects; `move_existing` preserva árbol
- [ ] Tests MCP verdes: TOML válido, dry_run, colisión, traversal
- [ ] `ruff` + `mypy` + `pytest -q` verdes; READMEs listan `sofer_init`
