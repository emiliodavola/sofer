# Design: feat-mcp-registration-automation

## Technical Approach

Hybrid delegation-first with file-edit fallback. New `src/sofer/mcp_registration.py` owns per-agent adapters (path resolution, JSON/TOML I/O, merge, backup, atomic write, delegation probe); `src/sofer/cli.py` owns only `mcp add/remove` parsers and thin `_cmd_mcp_add/_remove` handlers that loop agents and aggregate exit codes. Satisfies MCP-REG-01/02 + CLI-R09: idempotent merge, preserve keys, `.bak` backup, absolute contained `cwd`, atomic `tmp+os.replace`, unreadable→exit 1, per-client env, prefer native else file-merge.

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|----------|--------|----------|--------|
| Delegation | A file-edit only / B hybrid native+fallback | A simpler; B future-proofs format drift via agent validation | **B hybrid** — `shutil.which`+timeout probe for `codex`/`gemini`; OpenCode always file-edit |
| TOML I/O | `tomli-w` vs `tomlkit` | `tomlkit` keeps comments but adds dep | **tomli/tomli-w** (already deps); accept comment loss, warn in docs |
| Backup | single `.bak` vs timestamped | chain avoids clobber but unbounded | **single `.bak` overwrite** per spec; document clobber |
| Adapter shape | class/agent vs functions+registry | classes heavier | **functions + `ADAPTERS` dict** (`TypedDict` with resolve/read/merge/write/delegate) aligns flat-module pattern |
| Cwd containment | `resolve()`+`is_relative_to` | strict prevents mis-anchored server | **absolute resolve, validate `is_relative_to(user_home)` or `is_relative_to(project_root)`**; fail with path |
| Defaults | hardcode `sofer-mcp` vs `[tool.sofer]` knob | knob violates YAGNI for v1 | **no new knob** — fixed `sofer-mcp` from `[project.scripts]` |

## Data Flow

```
sofer mcp add --agent all [--scope user|project] [--cwd PATH] [--dry-run]
  → _build_parser(): mcp → add/remove (choices opencode|codex|gemini|all)
  → _cmd_mcp_add: expand "all" → for each agent:
      1. resolve_config_path(agent,scope) → Path
      2. probe_native(agent) → bool (which + --help, 3s timeout)
      3. if native: delegate_add() → ok? done else fallthrough
      4. file-edit: read_config() ─unreadable→ exit1 no backup/write
                 build_entry(cwd_resolved, env) → dict
                 merge(existing, desired) → (new_doc, changed)
                   - normalize Codex command string/array before diff
                   - preserve other servers; if !changed → no write
                 dry-run? → report only
                 backup() → <path>.bak (copy2)
                 atomic_write() → tmp in same dir + os.replace
      → aggregate → exit 0 iff all ok else 1
```

`remove` mirrors without `cwd`: native remove first, else load→delete `sofer` key idempotently→backup+atomic only if present.

Error handling: unreadable/malformed JSON/TOML → `print` to stderr, `return 1`, no `.bak`, no write. `cwd` resolved absolute via `Path(...).resolve()`; `is_relative_to` fails → exit 1. Windows `Path.home()` handles `~` and drive mismatch (`C:` vs `D:` → False). TOML comment loss noted in README.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/mcp_registration.py` | Create | Adapters: resolve/read/entry/merge/backup/atomic/probe/delegate; `json`, `tomli`/`tomli-w` |
| `src/sofer/cli.py` | Modify | `mcp` + `add`/`remove`; `--agent`/`--scope`/`--cwd`/`--dry-run`; handlers + docstrings |
| `src/sofer/config.py` | No change | No new defaults for v1 (deferred) |
| `tests/test_mcp_registration.py` | Create | Idempotency, backup, preserve, unreadable, atomic, containment, normalize, env |
| `tests/test_cli.py` | Modify | Parser/help tests for `mcp`; mock delegation |
| `README.md` + `README_ES.md` | Modify | Document `add/remove --agent all`, per-agent paths, `.bak`, idempotency, cwd, env |

## Interfaces / Contracts

```python
AgentName = Literal["opencode","codex","gemini"]
Scope = Literal["user","project"]

def resolve_config_path(agent: AgentName, scope: Scope, cwd: Path|None=None) -> Path: ...
def read_config(path: Path) -> tuple[dict, str]: ...  # ("json"|"toml"), raises on unreadable
def build_entry(agent: AgentName, cwd: Path, env: dict[str,str]) -> dict: ...
def merge(agent: AgentName, existing: dict, desired: dict) -> tuple[dict,bool]: ...
def backup(path: Path) -> Path|None: ...
def atomic_write(path: Path, doc: dict, fmt: str) -> None: ...  # tmp+os.replace
def probe_native(agent: AgentName, timeout: float=3.0) -> bool: ...
def delegate_add(agent: AgentName, cwd: Path, env_keys: list[str]) -> bool: ...
def delegate_remove(agent: AgentName) -> bool: ...
def _cmd_mcp_add(args: Namespace) -> int: ...
def _cmd_mcp_remove(args: Namespace) -> int: ...
# entries: opencode mcp.sofer, codex mcp_servers.sofer, gemini mcpServers.sofer
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit registration | idempotent no-write, backup, preserve, unreadable→exit1, atomic, cwd contained, Codex normalize, Gemini env | `tmp_path` JSON/TOML; byte-identical re-run; mock `Path.home` |
| Unit CLI | `sofer --help` has `mcp`; `mcp --help` has `add`/`remove`; `add --help` has `--agent/--scope/--cwd/--dry-run` | `_build_parser().parse_args` + `capsys` |
| Unit delegation | present→delegate, absent→file-edit, fail→fallback, timeout→fallback, opencode never delegates | mock `shutil.which` + `subprocess.run` |
| Integration | `add --agent all` creates 3; `remove` deletes; `--dry-run` no mutation; `--cwd` absolute; `--scope` routing | isolated `HOME` via `monkeypatch` + `tmp_path` |
| Containment | cwd outside root refused; relative resolved | unit with `resolve_config_path` |

## Migration / Rollout

No migration. Additive, no data mutated. Rollback: restore `.bak` or `sofer mcp remove --agent all`; revert commit. Note TOML reformat and Gemini plaintext `env` in release notes.

## Open Questions

- [ ] Verify native names `codex mcp add` / `gemini mcp add` via `--help` before spec freeze
- [ ] Gemini `settings.json` path: `~/.muse/settings.json` vs `~/.config/gemini/settings.json` — probe order
- [ ] Backup clobber policy: single `.bak` ok vs timestamped chain for follow-up
