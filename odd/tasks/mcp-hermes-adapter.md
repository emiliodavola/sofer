# Feature: mcp-hermes-adapter — issue #272

**Branch:** `feat/272-mcp-hermes-adapter` from `dev@90ee69f`
**Issue:** `emiliodavola/sofer#272` — *feat(mcp): add a `hermes` adapter to `sofer mcp add` — hand
registration leaves the containment root at the host cwd*
**Delivery PR:** `emiliodavola/sofer#286` — `feat/272-mcp-hermes-adapter` → `dev`
**SDD change:** `openspec/changes/archive/2026-10-09-feat-mcp-hermes-adapter/` (archived inside the PR)

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
| D4 | Single-scope: project resolves to the user file + stderr note, no refusal and no `<cwd>/.hermes/config.yaml` | Hermes has no project-scope config file. A file Hermes never reads is the silent no-op #274 removed; a refusal would fail `--agent all --scope project` for every agent. Accept-and-name matches the accepted `--cwd` amendment. Confirmed with the maintainer after an explained trade-off. |
| D6 | `project_scope` as an explicit capability | The registry is the single source of capabilities; inferring it from `project_parts == user_parts` would make a coincidence load-bearing. |

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Change artifacts (proposal, design, deltas, tasks) + this document | done | `621ed37` |
| T2/T3 | YAML write support: `_yaml.py`, `fmt="yaml"` in `_infer_fmt`, `read_config`, `atomic_write` | done | RED `6 failed, 125 passed, 2 skipped, 1 error` → GREEN `153 passed, 2 skipped`; `c23a169` |
| T4/T5 | `hermes` adapter: registry row, `project_scope`, `resolve_config_path`, `single_scope_note`, CLI help + note, READMEs, CONTRIBUTING | done | RED `28 failed, 316 passed, 3 skipped` → GREEN `344 passed, 3 skipped`; `9f0b559` |
| T6 | `cli.py` 100.00% with no pragma (rule 14) | done | `cli 637 0 194 0 100%`; `check_core_coverage.sh` exit 0 |
| T7 | READMEs (rule 13) + CONTRIBUTING architecture note | done | 36 headings in the same order, technical content identical, anchors resolve |
| T8 | Line-ending defect found by the independent verifier | done | RED `3 failed` → GREEN `175 passed, 2 skipped`; `efb439b`; finding closed on re-verification |
| T9 | Canonical spec sync (MCP-REG-01/02, CLI-R09) | done | `0999eee` |
| T10 | Full gate set | done | `2088 passed, 8 skipped`; TOTAL 94%; four rule-14 rows 100%; ruff/mypy/pyright clean; `check_test_mapping.py` exit 0 |
| T11 | Archive the change inside the PR (rule 15) | done | `openspec/changes/archive/2026-10-09-feat-mcp-hermes-adapter/` + `archive-report.md` |
| T12 | Push + PR against `dev` | done | PR #286; checks run by CI |

## Design notes

- `_yaml.py::splice_entry(text, key, name, doc)` is a pure function: `yaml.compose` gives the exact
  line span of the `key.name` node (descending to the true content end rather than the token-level
  `end_mark`, which points at the *next* key), so only that span is re-rendered and every other line is
  copied verbatim. Flow-style or non-mapping `key` blocks fall back to a bounded, documented re-render
  of that one block.
- Line endings are preserved on both sides of the file boundary: `atomic_write`'s YAML branch reads
  the pre-write text and writes the tmp file with `newline=""`, and the spliced block is rendered with
  the document's own ending. `path` absent renders a fresh document. JSON and TOML branches untouched.
- `resolve_config_path` reads `project_scope`: when it is `False`, project scope uses the user
  resolution (still ignoring `--user-config`, which remains a user-scope concept).
- `delegates=False` rides the existing `_delegates` gate, so `probe_native("hermes")` is `False` and
  both handlers go straight to the file edit with no new decline reason.
- Every `--agent all` test sandboxes `HERMES_HOME` (or `Path.home`) into `tmp_path`, because hermes'
  project scope resolves to the user file — a test that wrote the real `~/.hermes/config.yaml` would be
  a defect.

## Behavior change, declared and accepted

Hermes' `config.yaml` is Hermes' own file and its documented rule is `hermes config set <key>
<value>`. sofer writes it directly, as it does for the other four agents, because the native surface
cannot express `cwd` and `hermes config set` would need three or more unverifiable native calls. The
edit is surgical, so the "do not rewrite the document" half of Hermes' rule is honored; a future
native route is a follow-up, not a silent fallback.
