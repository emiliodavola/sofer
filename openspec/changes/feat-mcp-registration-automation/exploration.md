# Exploration: feat-mcp-registration-automation

> Change: `feat-mcp-registration-automation` — GitHub #77 — automate sofer MCP registration across AI agents (opencode, codex, gemini)
> Date: 2026-08-30 | Mode: hybrid (engram + openspec) | Review budget: 3000

## Problem Validation

**Problem is real and confirmed by code inspection.**

Registering `sofer-mcp` today requires hand-editing N client-specific config files with no validation. The server is client-agnostic (one stdio binary at `sofer.mcp_server:main` / console script `sofer-mcp`), but each agent reinvents the same registration differently. The README (AI and MCP server section) currently documents only a single Claude Code example (`claude mcp add sofer -- uv run sofer-mcp`) and leaves OpenCode / Codex / Gemini to manual JSON/TOML edits.

**Verified against codebase:**

- `src/sofer/mcp_server.py` — closed in #70, exposes 10 callables / 8 logical tools, 3 resources, 3 prompts over stdio via `fastmcp` (`[project.optional-dependencies] mcp = ["fastmcp>=3.4,<4"]`). Security model (path containment, fail-closed publish ladder, `_EXEC_LOCK`, `_contained_path`) is complete. No registration helpers exist in this file.
- `src/sofer/cli.py` — no `mcp` subcommand exists. Verified via `Select-String "mcp"` returning zero hits. CLI has 7 top-level subcommands (`validate`, `prepare`, `publish`, `codebook`, `profile`, `render`, `init`, `scan`) with `argparse` + `func` dispatch; `mcp` would be the 8th.
- `pyproject.toml` — `[project.scripts]` declares `sofer = sofer.cli:main` and `sofer-mcp = sofer.mcp_server:main`. The `sofer-mcp` binary is the only artifact a registration entry should point at (recommended `["uv","run","sofer-mcp"]` or `["sofer-mcp"]` depending on install).
- `openspec/specs/mcp-server/spec.md` (MSP-R01..R12) — distribution contract is fully spec'd and tests exist (`tests/test_mcp_server.py`, 1k+ suite). No registration spec exists yet; this change extends the `mcp-server` or `cli` domain.

**Client-specific gotchas verified from issue #77 (2026-08 shapes, must be re-verified before implement):**

| Agent | Config location(s) | Format | Key pitfalls |
|---|---|---|---|
| **OpenCode** | Project: `./opencode.json` / `.opencode/opencode.json`; User/global: OS-dependent (XDG / `~/.config/opencode/opencode.json`) | JSON `mcp: { sofer: { type:"local", command:[...], environment:{...} } }` | Merge at top-level `mcp` key; `type: local` required; `command` is array, not string |
| **Codex CLI** | `~/.codex/config.toml` (user-scoped; no documented project-scoped file in 2026-08) | TOML `[mcp_servers.sofer]` with `command`, `cwd`, `env_vars` | `command` is string or array depending on codex version; `env_vars` is allow-list, not `env`; secrets must be whitelisted, not inlined |
| **Gemini CLI** | User: `~/.config/gemini/settings.json` or `~/.muse/settings.json`; Project: `./.muse/settings.json` (exact name varies by Gemini version — verify with `gemini mcp list` output) | JSON `mcpServers: { sofer: { command, args?, cwd, env } }` | No underscores in server name (already `sofer` is safe); **no shell env inheritance** — `HF_TOKEN` and `SOFER_MCP_APPROVAL_PHRASE` MUST be in explicit `env` block; `cwd` is explicit string, not derived |

**Consequences if not solved:** duplicated manual work per agent, silent mis-registration (wrong `cwd` breaks server path-containment root, missing `env` breaks publish), docs-only help does not validate JSON/TOML, MCP spec's shared `mcp.json` is not read by these agents, standalone shell scripts lack idempotency/backup/rollback.

**Verdict: GO — problem is validated, scope is bounded, and a CLI subcommand eliminates the duplication.**

---

## Current State

### How the system works today (relevant to this topic)

- **Server:** `sofer.mcp_server.build_server(root, approval_phrase)` captures a containment root and optional approval phrase, registers 10 tools / 3 resources / 3 prompts on a `FastMCP("sofer")`. `main()` builds with `root=cwd` and `SOFER_MCP_APPROVAL_PHRASE` from env, then `server.run("stdio")`. No registration logic lives here.
- **CLI dispatch:** `src/sofer/cli.py` does config bootstrap (`config.reload(None)`), `_build_parser()` with 8 subparsers, then `args.func(args)`. Each handler (`_cmd_validate`, `_cmd_prepare`, etc.) has a module-level docstring describing orchestration. Tests in `tests/test_cli.py` assert parser shapes and that `upload` is rejected.
- **Tool config:** `src/sofer/config.py` provides `[tool.sofer]` defaults (output_dir=`cache`, raw_dir=`raw`, etc.) via `reload(start, stop_at)` with bounded discovery (`stop_at` used by MCP server to avoid above-root pyproject). No registration defaults exist yet.
- **Docs:** `README.md` AI and MCP server section covers `pip install 'sofer[mcp]'`, `sofer-mcp` launch, Claude Code example, security model, and `SOFER_MCP_APPROVAL_PHRASE`. `README_ES.md` must stay in sync per AGENTS.md rule 13. No per-agent registration docs for OpenCode/Codex/Gemini exist.
- **Tests / CI:** `uv run pytest tests/ -q` (1029+ tests), `ruff` + `mypy` on commit, tag-driven release via `.github/workflows/release.yml`. No existing tests cover config-file editing.
- **Client configs in this repo:** No `opencode.json`, no `.codex/config.toml`, no Gemini settings file checked in — registration must create or merge them on the user's machine, not in the repo.

### Related specs

- `openspec/specs/mcp-server/spec.md` — MSP-R01..R12 (transport, roster, safety, publish gate, resources, prompts, offline testability, packaging/docs)
- `openspec/specs/cli/spec.md` — CLI-R01..R04 (top-level commands, help text accuracy)
- `openspec/specs/tool-config/spec.md` — TC-01..TC-06 (discovery, precedence, reload)

---

## Affected Areas

- `src/sofer/cli.py` — **primary**: add `mcp` subparser with `add`/`remove` (and optionally `status`/`list`) subcommands, handler functions `_cmd_mcp_add`, `_cmd_mcp_remove`, argparse wiring, help text, idempotent merge logic or delegation to `mcp_registration` domain module. Effort driver: arg parsing, `--agent <agent|all>` enum, `--scope user|project`, `--cwd`, `--dry-run`, `--force`.
- `src/sofer/mcp_registration.py` — **new domain module** (one module per concern, AGENTS.md rule 10): per-agent adapters (OpenCode / Codex / Gemini), config location resolution, format-specific read/write (JSON vs TOML), backup before edit, merge preserving existing config, `cwd` containment validation, unreadable-file fail-cleanly, native-command delegation (`codex mcp add`, `gemini mcp add` when available) with fallback to direct file edit. Extract if CLI would otherwise bloat.
- `src/sofer/config.py` / `pyproject.toml [tool.sofer]` — **possible**: no hardcoded agent names, paths, or command arrays; defaults belong in `[tool.sofer]` if they need to be configurable (e.g., default `command` for `sofer-mcp`, default `cwd` policy). Follow AGENTS.md rule 1 and rule 3.
- `pyproject.toml [project.optional-dependencies]` / `[dependency-groups]` — **evaluate**: TOML editing needs `tomli-w` (already a dependency for `write_toml`) — reuse it; JSON needs stdlib `json`. No new heavy dependency unless TOML round-trip preservation requires `tomlkit` — prefer `tomli` + `tomli-w` (already in deps) and accept comment loss with warning.
- `README.md` + `README_ES.md` — **required in same commit**: document `sofer mcp add --agent all` / `sofer mcp remove`, per-agent behavior, backup location, idempotency, `cwd` semantics. AGENTS.md rule 7 + rule 13.
- `openspec/specs/mcp-server/spec.md` or new `openspec/specs/mcp-registration/spec.md` — delta spec for registration contract (idempotency, backup, preserve, cwd containment, env forwarding, fail-cleanly).
- `openspec/specs/cli/spec.md` — update if `mcp` becomes a top-level subcommand (CLI-R03 pattern).
- `tests/test_cli.py` + new `tests/test_mcp_registration.py` — parser tests, merge-idempotent tests, backup tests, unreadable-file tests, per-agent fixture tests (temp JSON/TOML files), delegation preference tests. Spec scenarios → tests (AGENTS.md rule 6).
- `src/sofer/mcp_server.py` — **read-only** for exploration: registration must point at `sofer-mcp` correctly (absolute `cwd` for containment) but the server itself needs no change. Verify `build_server(root)` semantics so registration's `cwd` choice is correct.

---

## Approaches

### 1. File-edit only — pure Python merge (no delegation)

Implement `sofer mcp add --agent <opencode|codex|gemini|all> [--scope user|project] [--cwd PATH] [--dry-run] [--force]` that directly reads, merges, backs up, and writes each agent's config file (JSON for OpenCode/Gemini, TOML for Codex). `remove` deletes the `sofer` entry idempotently. No subprocess delegation.

- Pros: single code path; deterministic; easy to test with temp files; no dependency on whether `codex`/`gemini` binaries are installed; works offline; full control over backup/rollback.
- Cons: must handle every format quirk internally (TOML comment loss if using `tomli-w`, Codex `command` string-vs-array ambiguity, Gemini `mcpServers` vs `mcp_servers` key casing across versions); divergence risk if an agent changes its format — our parser must track it; no benefit from native validation the agent's own `mcp add` might provide.
- Effort: Medium (per-agent adapters + atomic write + backup + tests)
- Fits requirements: merge idempotent ✓, preserve existing ✓, cwd containment ✓, backup ✓, fail cleanly ✓, env forwarding ✓ — but violates "prefer native registration commands when available".

### 2. Hybrid: prefer native `mcp add`/`remove`, fallback to direct file edit (RECOMMENDED)

`sofer mcp add` first probes for native registration binaries (`codex mcp add`, `gemini mcp add` — verify exact subcommand names per agent, 2026-08 shapes may have shifted), and if found + executable, delegates (`subprocess.run` with timeout, capture output, fail cleanly on non-zero). If not found or delegation fails, falls back to Approach 1's direct file edit. OpenCode has no native `mcp add` in 2026-08 — always file-edit. `remove` mirrors the same priority. Backup before any file edit; native path needs no backup (agent owns its config). Add `--no-native` / `--direct` flag to force file-edit for debugging.

- Pros: satisfies the explicit requirement "prefer native registration commands when available else direct file edit"; leverages agent-side validation; future-proofs against format drift (native path stays correct even if file shape changes); still works when binaries absent; minimal new dependencies.
- Cons: subprocess delegation adds failure modes (binary missing, version skew, interactive prompts, shell quoting on Windows); need to detect and parse native command availability without false positives; tests must mock subprocess and cover both branches; Windows `~/.codex/config.toml` path expansion differs from Unix (use `Path.home()` + `os.path.expanduser`).
- Effort: Medium-High (adapters + delegation layer + dual-path tests)
- Fits requirements: all six requirements satisfied; aligns with issue's "Where an agent ships a native registration command, prefer delegating to it; fall back to direct config editing otherwise."

### 3. Docs-only + `--print-config` (no file writes)

Add `sofer mcp print --agent <agent>` that prints the verified JSON/TOML snippet to stdout (and optionally `--check` that validates an existing config file without editing). No backups, no writes. User copy-pastes.

- Pros: zero risk of clobbering; trivial to implement; no backup/TOML round-trip concerns; review budget near zero.
- Cons: does not solve the stated problem (user still edits N files by hand); no idempotency, no automation; contradicts the `sofer mcp add/remove` contract in the issue; would be marked NO-GO against the requirements.
- Effort: Low
- Fits requirements: fails "merge idempotent, preserve, backup, cwd containment, fail cleanly on unreadable" for writes — only useful as a complementary `--dry-run`/`--print` helper, not as the primary approach.

---

## Recommendation

**Approach 2 — Hybrid delegation-first with file-edit fallback — is the recommended path.**

Why:
- It is the only approach that satisfies every line of the issue's Requirements section, especially the "prefer native registration commands when available else direct file edit" clause.
- It keeps the deterministic file-edit path (Approach 1) as the reliable core, so the feature works even when native CLIs are absent or broken — no hard dependency on external binaries.
- It minimizes format-drift risk: if Codex or Gemini changes its TOML/JSON shape, the native delegation branch remains correct without a sofer release.
- It naturally provides `sofer mcp add --agent all` (loop over adapters, collect per-agent ok/fail, exit non-zero if any fail) and `sofer mcp remove --agent <agent|all>` with the same semantics.
- It maps cleanly to the existing architecture: new domain module `src/sofer/mcp_registration.py` (one module per concern), thin handlers in `cli.py`, shared helpers for backup (`<path>.bak.<timestamp>` or `.bak`), atomic write (write to temp + `os.replace`), cwd containment (`Path.resolve().is_relative_to(root)` pattern already proven in `mcp_server._contained_path`), and JSON/TOML helpers reusing `tomli`/`tomli-w`.

Suggested CLI shape (to be pinned in spec):

```
sofer mcp add    --agent <opencode|codex|gemini|all> [--scope user|project] [--cwd PATH] [--dry-run] [--force] [--no-native]
sofer mcp remove --agent <opencode|codex|gemini|all> [--scope user|project] [--dry-run]
sofer mcp status --agent <opencode|codex|gemini|all> [--scope user|project]   # optional, reports registered / missing / drift
```

Adapter contract (internal):

- `resolve_config_path(agent, scope) -> Path` — knows per-agent locations (user vs project scoped) with `Path.home()` and `Path.cwd()` anchoring; project scope defaults to `cwd` for opencode/gemini, user scope for codex.
- `read_config(path) -> dict/toml` — fail cleanly on unreadable (exit 1, message, no backup, no write).
- `build_entry(agent, cwd, env) -> dict` — verified 2026-08 shapes: OpenCode `{type:"local", command:["uv","run","sofer-mcp"]}`, Codex `{command:"sofer-mcp", cwd, env_vars:["HF_TOKEN","SOFER_MCP_APPROVAL_PHRASE"]}`, Gemini `{command:"sofer-mcp", cwd, env:{HF_TOKEN:"...", SOFER_MCP_APPROVAL_PHRASE:"..."}}` (explicit env, no inheritance). Include `cwd` always (absolute, resolved, contained).
- `merge(entry, existing) -> new_content` — idempotent: if entry already equals existing, no write; preserve all other keys.
- `backup(path)` — copy to `<path>.bak` or `<path>.bak.<iso>` before first edit; document location.

---

## Risks

- **TOML round-trip fidelity:** `tomli-w` does not preserve comments or formatting in `~/.codex/config.toml`. An edit will reformat the file and strip comments. Mitigation: warn in docs; consider `tomlkit` if comment preservation is required (adds dependency — evaluate trade-off).
- **Gemini config location drift:** `settings.json` path and key name (`mcpServers` vs `mcp_servers` vs `mcp`) have changed across Gemini CLI versions. Mitigation: verify against installed `gemini --help` / `gemini mcp --help` at spec time; probe both locations; include version check in `status`.
- **Codex `command` shape ambiguity:** Codex docs show both `command = "sofer-mcp"` (string) and `command = ["sofer-mcp"]` (array) across versions. Mitigation: accept both on read, normalize to array on write, idempotency comparison normalizes before diff.
- **Gemini env non-inheritance:** Forgetting explicit `env` forwarding silently breaks HF publish. Mitigation: always emit `env` with `HF_TOKEN` and `SOFER_MCP_APPROVAL_PHRASE` placeholders or current shell values; document that secrets are stored in plaintext in the config file (same as Codex `env_vars` allow-list semantics).
- **CWD containment:** Registration `cwd` must be absolute and inside the user's intended root; a relative or outside-root `cwd` would misconfigure the server's path containment. Mitigation: resolve `cwd` via `Path.resolve()`, validate `is_relative_to(home)` or `is_relative_to(project_root)` depending on scope, fail with clear message.
- **Native command availability detection:** `codex mcp add` / `gemini mcp add` may not exist on all installations; probing via `shutil.which` + `--help` can hang or prompt. Mitigation: use timeout, never prompt, fall back silently; add `--no-native` escape hatch.
- **Windows paths:** `~/.codex/config.toml` on Windows is `%USERPROFILE%\.codex\config.toml`; `Path.home()` handles it but tests must cover `ntpath` behavior (already proven in `mcp_server._remote_is_unsafe`).
- **Backup clobbering:** Repeated `add` should not create unbounded `.bak` files. Mitigation: single `.bak` + `.bak.<timestamp>` only when existing `.bak` differs, or keep one backup and document.
- **Review budget:** 3000-line budget is ample; expected delta is ~400-600 lines (adapters + CLI + tests + docs) — well under budget. Still forecast and slice if design grows.
- **Scope creep:** Future agents (Claude Code, Cursor, VS Code Copilot) are out of scope for v1 — keep initial scope to OpenCode/Codex/Gemini as the issue suggests, and design adapters as extensible.

---

## Ready for Proposal

**Yes — GO.**

The exploration is complete and the change is ready for `sdd-propose` to draft the proposal. Required inputs for the next phase:

- **Change name:** `feat-mcp-registration-automation`
- **Artifact store:** hybrid (this file + engram `sdd/feat-mcp-registration-automation/explore`)
- **Scope (in):** `sofer mcp add/remove` with `--agent <agent|all>`, per-agent adapters for OpenCode/Codex/Gemini, idempotent merge preserving existing config, cwd containment, backup before edit, fail cleanly on unreadable, native-command delegation when available with file-edit fallback, env forwarding per client rules, help text + README/ES updates, spec delta, tests.
- **Scope (out):** Claude Code / Cursor / VS Code Copilot adapters (future), shared `mcp.json` client config, standalone shell script, MCP server transport changes, publish logic changes.
- **Key validation before spec:** re-verify 2026-08 config shapes (`opencode.json` `mcp` block, `~/.codex/config.toml` `[mcp_servers.sofer]`, Gemini `settings.json` `mcpServers`) against current agent binaries; confirm `codex mcp add` and `gemini mcp add` subcommand names and flags.

## References

- Issue: https://github.com/emiliodavola/sofer/issues/77
- Server: `src/sofer/mcp_server.py` (build_server, _contained_path, HAMC approval phrase)
- CLI: `src/sofer/cli.py` (_build_parser, _cmd_* handlers, no mcp subcommand today)
- Scripts: `pyproject.toml [project.scripts]` sofer-mcp
- Docs: `README.md` AI and MCP server section (install, launch, security model)
- Spec: `openspec/specs/mcp-server/spec.md` MSP-R01..R12
- Config: `src/sofer/config.py` ([tool.sofer] discovery, reload, stop_at containment)
