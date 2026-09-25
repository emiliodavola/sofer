# Tasks: 2026-09-25-chore-single-source-agent-registry

## Phase 1 — Single-source registry (`mcp_registration.py`)

- [x] 1.1 Extend `Adapter` TypedDict: `user_parts`, `project_parts`, `command`,
      `adds_type_local`, `env`, `delegates` (keep `fmt`, use `key`).
- [x] 1.2 Fill `ADAPTERS` for opencode/codex/gemini; add `AGENT_NAMES = tuple(ADAPTERS)`.
- [x] 1.3 Add `_adapter(agent)` centralising the unknown-agent `ValueError`.
- [x] 1.4 `resolve_config_path` joins registry path parts (no per-agent branches).
- [x] 1.5 `build_entry` composes command/type/env from the registry.
- [x] 1.6 `_normalize_codex_command` → `_normalize_command`; generic `_entries_equal`.
- [x] 1.7 Generic `merge` / `remove_entry` keyed by `ADAPTERS[agent]["key"]`.
- [x] 1.8 Gate `probe_native` / `delegate_add` / `delegate_remove` on `delegates`;
      `dropped_env_keys` on `env == "none"`.
- [x] 1.9 Remove the dead `cmd_variants`; declare the single native `add` shape.

## Phase 2 — CLI derives from the registry (`cli.py`)

- [x] 2.1 Import the `mcp_registration` module; drop the unused `_AgentName`/`_Scope` aliases.
- [x] 2.2 Both `--agent` `choices` become `[*mcp_registration.AGENT_NAMES, "all"]`.
- [x] 2.3 Both `all` expansions become `list(mcp_registration.AGENT_NAMES)`.
- [x] 2.4 Read `fmt` from the registry; update `_cmd_mcp_add` docstring step 1.

## Phase 3 — Tests

- [x] 3.1 Rename the `_normalize_command` test.
- [x] 3.2 `TestSingleSourceRegistry`: registry↔`AGENT_NAMES`, adapter completeness,
      per-agent path resolution.
- [x] 3.3 CLI `choices` equal `[*AGENT_NAMES, "all"]` for `add` and `remove`.
- [x] 3.4 Sentinel registry entry flows into choices and `--agent all`.

## Phase 4 — Verification

- [x] 4.1 `uv run pytest tests/ -q` green.
- [x] 4.2 `ruff check` + `ruff format --check` clean.
- [x] 4.3 `mypy src/ scripts/` and `pyright` clean.
- [x] 4.4 `scripts/check_test_mapping.py` passes; `scripts/check_core_coverage.sh` 100%.
- [x] 4.5 `coverage report -m`: `mcp_registration.py` ≥90, TOTAL ≥90.
