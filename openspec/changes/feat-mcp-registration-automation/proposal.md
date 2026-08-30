# Proposal: feat-mcp-registration-automation

## Intent

Eliminate hand-editing N configs to register `sofer-mcp` (#77). One stdio binary must be registered in three different formats (OpenCode JSON `mcp`, Codex TOML `[mcp_servers]`, Gemini JSON `mcpServers`) with gotchas (`env_vars` vs `env`, no env inheritance). Provide `sofer mcp add --agent all` that is idempotent and validated.

## Scope

### In Scope
- `sofer mcp add/remove --agent <opencode|codex|gemini|all> [--scope user|project] [--cwd PATH] [--dry-run]`
- Adapters for OpenCode/Codex/Gemini: path resolution, JSON/TOML I/O, preserve-merge, cwd containment, backup, fail-cleanly
- Hybrid: native `codex/gemini mcp add` first, else direct merge; OpenCode always file-edit
- Env forwarding (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`), atomic write, help + README/ES, tests

### Out of Scope
- Claude/Cursor/Copilot adapters (later), shared `mcp.json`, standalone script, docs-only
- Transport or publish changes

## Capabilities

### New Capabilities
- `mcp-registration`: idempotent merge, preserve existing, backup, cwd anchoring, per-client env, fail-cleanly, hybrid delegation

### Modified Capabilities
- `cli`: add `mcp` top-level subcommand (`add`/`remove`)

## Approach

Hybrid delegation-first with file-edit fallback. New `src/sofer/mcp_registration.py` + thin `cli.py` handlers. Per adapter: `resolve_config_path` → `read_config` (unreadable→exit 1) → `build_entry` → `merge` (normalize `command` string/array, no write if equal) → `backup` → atomic `temp+os.replace`. Resolve `--cwd` absolute via `Path.resolve()`+`is_relative_to`; probe native via `which`+timeout; delegate if ok else file-edit. Entries: OpenCode `type:local+command[]`, Codex `command+cwd+env_vars`, Gemini `command+cwd+env`. Reuse `tomli`/`tomli-w`+`json`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py` | Modified | `mcp` subparser + handlers |
| `src/sofer/mcp_registration.py` | New | Adapters, merge, backup, delegation |
| `openspec/specs/mcp-registration/spec.md` | New | Registration contract |
| `openspec/specs/cli/spec.md` | Modified | CLI-R for `mcp` |
| `README.md` + `README_ES.md` | Modified | Document `add/remove` |
| `tests/test_mcp_registration.py` | New | Merge/backup/unreadable/delegation |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TOML comment loss | High | Warn; `tomlkit` only if needed |
| Gemini path/key drift | Med | Probe both; re-verify before spec |
| Codex `command` shape | Med | Normalize on read/write/diff |
| Gemini env non-inheritance | High | Always emit explicit `env` |
| Native probe hang | Low | Timeout + `--no-native` fallback |

## Rollback Plan

Restore `<path>.bak` or `sofer mcp remove --agent all`. Native path delegates remove or direct delete. Revert single commit; no server state.

## Dependencies

- `src/sofer/mcp_server.py` (#70), `pyproject.toml` `sofer-mcp`; specs `mcp-server`/`cli`
- Re-verify 2026-08 shapes and native names before spec

## Success Criteria

- [ ] `add --agent all` registers 3 agents; `remove` deletes idempotently
- [ ] Preserve other keys; equal re-run does no write
- [ ] Backup before edit; `--dry-run` no mutation
- [ ] `cwd` absolute+contained; unreadable→exit 1
- [ ] Env per client; native first for Codex/Gemini
- [ ] Help + README/ES updated; `pytest` green
