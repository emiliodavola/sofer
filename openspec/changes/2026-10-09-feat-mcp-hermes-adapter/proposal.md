# Proposal — `2026-10-09-feat-mcp-hermes-adapter`

> **Change** `2026-10-09-feat-mcp-hermes-adapter` · issue **#272** · branch
> `feat/272-mcp-hermes-adapter` from `dev@90ee69f` · store **hybrid** (this file + Engram mirror).
>
> **Status:** proposal complete, implemented, verified and **archived inside this PR** (AGENTS.md
> rule 15).

---

## 1. Intent

`sofer mcp add --agent` supports `opencode`, `codex`, `gemini` and `pi`. Hermes Agent (Nous Research)
is not in `ADAPTERS`, so the server must be registered by hand — and a hand registration that does not
reproduce the contained `cwd` leaves the MCP refusing every dataset path:

```json
{"error": "Error calling tool 'sofer_codebook': data file resolves outside the server root:
 /workspace/test/dataset.xlsx"}
```

Every path-bearing tool is refused identically, while the CLI never fails. The fix is one adapter
entry: `hermes`, written into the file Hermes actually reads, with the contained `cwd` and the env
NAMES the other four already forward.

This is an integration gap, not a pipeline bug: with the right root every stage works.

## 2. Scope

### In scope

- A fifth `ADAPTERS` entry, `hermes`: `mcp_servers` under `~/.hermes/config.yaml` (or
  `$HERMES_HOME/config.yaml`), `command` as a string, absolute `cwd`, `env` as `${KEY}` references.
- **YAML support in the config I/O path**: `read_config`, `_infer_fmt` and `atomic_write` gain the
  `yaml` format, and a **surgical writer** preserves the rest of the document byte-for-byte.
- One adapter capability, `project_scope`, and the single-scope resolution it drives: Hermes reads one
  config, so `--scope project` resolves to that same file and the CLI names the substitution on
  stderr instead of refusing (or writing a file Hermes never reads).
- `openspec/specs/mcp-registration/spec.md` (MCP-REG-01) and `openspec/specs/cli/spec.md` (CLI-R09).
- Both READMEs (rule 13) and the `CONTRIBUTING.md` architecture note.

### Out of scope (non-goals)

- **The server-root containment** (`_contained_path`, `_get_root`, `PathOutsideRootError`,
  `build_server`) and every tool's path resolution — untouched. The missing `--root` /
  `SOFER_MCP_ROOT` lever is issue **#273**, already delivered by #279.
- **No native `hermes` delegation** — see D2. `delegate_add` / `delegate_remove` / `probe_native` are
  untouched.
- No new dependency (`pyyaml>=6.0` is already a runtime dependency, `pyproject.toml:29`), no version
  bump, no `uv.lock` change, no `openspec/project.md` or `openspec/config.yaml` change.
- No Test Mapping rows and no registry edit: `mcp-registration` and `cli` are permanent
  declared-backlog specs (`openspec/test-mapping-registry.md`).
- No change to how TOML or JSON configs are written — the documented "TOML edits may strip comments"
  behavior stands.

## 3. Settled decisions

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | `hermes` is one `ADAPTERS` entry: `fmt="yaml"`, `key="mcp_servers"`, `user_parts=(".hermes","config.yaml")`, `user_env_dir="HERMES_HOME"`, `command="string"`, `not adds_type_local`, `delegates=False`, `env="refs_braced"`, `project_scope=False`. | Issue #272's proposed table, mapped onto the existing single-source registry (#235/#142). `HERMES_HOME` names the Hermes **home directory** and Hermes' own `config.yaml` lives at its root, which is exactly the existing `user_env_dir` mechanism (`user_parts[-1]` is the file name) — no new mechanism is invented for it. |
| **D2** | The write path is a **file edit**, not native delegation: `delegates=False`. | Measured, not assumed. Hermes' documented `hermes mcp add <name>` surface is `[--url URL] [--command CMD] [--auth oauth\|header] [--args ...]` — no `cwd`, no env; the issue's own reproduction had to run `hermes config set mcp_servers.sofer.cwd /workspace/test` afterwards. A native path that silently omits `cwd` reproduces the exact defect this change removes, and the fidelity gate (`native_env`/`native_scope`) has no `cwd` dimension to catch it. The `hermes config set` route was also rejected: it needs three or more native calls that cannot be exercised by any test here, it writes every `UPPER_SNAKE` name to `~/.hermes/.env` rather than `config.yaml`, and it re-fights the env-NAMES-only contract. |
| **D3** | `env="refs_braced"`: `env: {HF_TOKEN: "${HF_TOKEN}", …}`, names only. | Hermes documents that string values anywhere in a server entry — `env` included — may reference environment variables as `${VAR}` or `${env:VAR}`, resolved from the active profile's secret scope with the process environment as fallback, so the **name** is persisted and the value never is. This is the same policy as codex's `env_vars` allow-list and the same encoding as Pi (`${KEY}`), so no new `env` mode is added. |
| **D4** | Hermes is **single-scope**: `--scope project` resolves to the same config `--scope user` resolves to, and `add`/`remove` print one stderr note naming the substitution. No refusal, no skip rule, no `<cwd>/.hermes/config.yaml`. | Hermes reads exactly one config (`~/.hermes/config.yaml`, or `$HERMES_HOME/config.yaml`; `hermes project` is a named multi-folder workspace, not a config file). Writing `<cwd>/.hermes/config.yaml` would be the silent no-op #274 exists to remove; refusing would make `--agent all --scope project` fail for every agent and add friction for no safety. Accept-and-name is the rule the same repo already chose for `--cwd` (accepted with a stderr warning naming the resolved path and the roots it is outside of). |
| **D5** | The YAML writer **splices only the `sofer` entry**; unrelated keys, comments and formatting outside it stay byte-identical. | #272's own write-path clause: "a file edit must preserve unrelated keys/indentation rather than rewriting the document". A `safe_load` + `safe_dump` round trip would delete every comment in a file Hermes ships as a commented example. TOML's documented comment-stripping behavior is unchanged. |
| **D6** | `project_scope` is a new capability field, not an inference from `project_parts`. | The registry is the single source of capabilities, and "this agent has no distinct project file" is a capability. Inferring it from `project_parts == user_parts` would make an unrelated coincidence load-bearing. |
| **D7** | `--user-config` keeps its user-scope-only rule for Hermes: `--scope project` ignores it even though it resolves to the user file. | The flag states a **user**-scope file; project scope ignoring it is the existing declared rule, and `--agent hermes --scope project --user-config X` must not silently acquire a meaning the spec forbids. |

## 4. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | The new tests are red before the change and green after (observed per work unit, recorded in `tasks.md`) |
| SC-2 | `cli.py` stays at **100.00%** (rule 14) with no `# pragma: no cover`, and `scripts/check_core_coverage.sh` exits 0 |
| SC-3 | `--agent all` writes **five** configs, the fifth being `~/.hermes/config.yaml` with `mcp_servers.sofer` |
| SC-4 | A Hermes edit leaves every other byte of a commented `config.yaml` intact, and an unchanged entry writes nothing and creates no `.bak` |
| SC-5 | The full gate set is green: pytest, `ruff check`, `ruff format --check`, mypy, pyright, coverage, `check_test_mapping.py` |
| SC-6 | Both READMEs carry the same sections and the same technical content (rule 13) |

## 5. Affected specs

| Spec | Requirement | Action |
| --- | --- | --- |
| `mcp-registration` | MCP-REG-01 (MCP add idempotent and safe) | Modified — hermes agent row, YAML write clause, single-scope clause, new scenarios |
| `cli` | CLI-R09 (mcp add/remove help) | Modified — agent enumeration, env-forwarding sentence, YAML preservation and single-scope sentences, scenarios |
