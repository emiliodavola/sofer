# Feature: mcp-hermes-adapter — issue #272

**Branch:** `feat/272-mcp-hermes-adapter` from `dev@90ee69f`
**Issue:** `emiliodavola/sofer#272` — *feat(mcp): add a `hermes` adapter to `sofer mcp add` — hand
registration leaves the containment root at the host cwd*
**Delivery PR:** opened against `dev`
**SDD change:** `openspec/changes/2026-10-09-feat-mcp-hermes-adapter/` (archived inside the PR)

## Goal

`ADAPTERS` had four agents, so Hermes Agent had to be registered by hand — and a hand registration
that does not reproduce the contained `cwd` makes Hermes launch `sofer-mcp` with its own cwd as the
containment root, so every path-bearing tool is refused while the CLI never fails. Add the fifth
adapter, in the file Hermes actually reads, with the contained `cwd` and the env NAMES the other
agents forward.

## The contract, taken from the issue plus the Hermes documentation

1. `hermes` entry: `fmt="yaml"`, `key="mcp_servers"`, `user_parts=(".hermes","config.yaml")`,
   `user_env_dir="HERMES_HOME"`, `command` string, absolute `cwd` — the issue's own proposed row.
2. Env forwarding writes NAMES only, as `${KEY}` references — Hermes documents
   `${VAR}` / `${env:VAR}` in any server-entry string value, `env` included, resolved from the active
   profile's secret scope with the process environment as fallback.
3. The YAML edit must preserve unrelated keys and indentation rather than rewriting the document
   (Hermes ships `config.yaml` as a commented example).
4. Hermes reads one config; `--scope project` resolves to it and names the substitution on stderr.

## Decisions that were not in the issue (each one is recorded in `proposal.md` §3)

| # | Decision | Evidence |
| --- | --- | --- |
| D2 | File edit, `delegates=False` — no native path | Hermes' documented `hermes mcp add` surface is `[--url] [--command] [--auth] [--args]`: no `cwd`, no env. The issue's own reproduction had to run `hermes config set mcp_servers.sofer.cwd` afterwards, and the fidelity gate has no `cwd` dimension to catch a silent omission. |
| D3 | `env="refs_braced"` (`${KEY}`), names only | Hermes' MCP config reference: `${VAR}` / `${env:VAR}` resolve in server-entry string values, `env` included; "put the secret in `~/.hermes/.env`". Same encoding as Pi, same policy as codex. |
| D4 | Single-scope: project resolves to the user file + stderr note, no refusal and no `<cwd>/.hermes/config.yaml` | Hermes has no project-scope config file. A file Hermes never reads is the silent no-op #274 removed; a refusal would fail `--agent all --scope project` for every agent. Accept-and-name matches the accepted `--cwd` amendment. |
| D6 | `project_scope` as an explicit capability | The registry is the single source of capabilities; inferring it from `project_parts == user_parts` would make a coincidence load-bearing. |

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Change artifacts (proposal, design, deltas, tasks) + this document | done | `openspec/changes/2026-10-09-feat-mcp-hermes-adapter/` |
| T2/T3 | YAML write support: `_yaml.py`, `fmt="yaml"` in `_infer_fmt`, `read_config`, `atomic_write` | pending | |
| T4/T5 | `hermes` adapter: registry row, `project_scope`, `resolve_config_path`, `single_scope_note`, CLI help + note | pending | |
| T6 | `cli.py` 100.00% with no pragma (rule 14) | pending | |
| T7 | READMEs (rule 13) + CONTRIBUTING architecture note | pending | |
| T8 | Full gate set | pending | |
| T9/T10/T11 | Work-unit commits, archive in the PR, push + PR | pending | |

## Design notes

- `_yaml.py::splice_entry(text, key, name, doc)` is a pure function: `yaml.compose` gives the exact
  line span of the `key.name` node, so only that span is re-rendered and every other line is copied
  verbatim. Flow-style or absent `key` fall back to a bounded, documented re-render of that one block.
- `atomic_write(..., fmt="yaml")` re-reads the pre-write text (documented: the caller reaches it after
  the single `.bak` backup and nothing mutates the file in between) so the splice has a document to
  preserve; `path` absent renders a fresh document. JSON and TOML branches untouched.
- `resolve_config_path` reads `project_scope`: when it is `False`, project scope uses the user
  resolution (still ignoring `--user-config`, which remains a user-scope concept).
- `delegates=False` rides the existing `_delegates` gate, so `probe_native("hermes")` is `False` and
  both handlers go straight to the file edit with no new decline reason.

## Behavior change, declared and accepted

Hermes' `config.yaml` is Hermes' own file and its documented rule is `hermes config set <key>
<value>`. sofer writes it directly, as it does for the other four agents, because the native surface
cannot express `cwd` and `hermes config set` would need three or more unverifiable native calls. The
edit is surgical, so the "do not rewrite the document" half of Hermes' rule is honored; a future
native route is a follow-up, not a silent fallback.
