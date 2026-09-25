# Proposal: 2026-09-25-fix-mcp-native-delegation

**Change:** `2026-09-25-fix-mcp-native-delegation` · **Issues:** #167, #232 `type:bug`
· **Branch:** `fix/167-232-native-mcp-delegation` (base `dev@8d2f5eb`, PR-only)

## Intent

Both issues attack the same native delegation path (`mcp_registration.delegate_add`
/ `delegate_remove`, invoked from `cli._cmd_mcp_add` / `_cmd_mcp_remove`) with the
same symptom: when the native `codex`/`gemini` CLI is on `PATH`, `sofer mcp
add/remove` silently produces a registration that differs from the file-edit
fallback.

- **#167** — `delegate_add` accepts `env_keys` but never forwards it, so a
  delegated `codex`/`gemini` registration ends up without `HF_TOKEN` /
  `SOFER_MCP_APPROVAL_PHRASE`, while the file-edit path persists those env
  NAMES (`env_vars` allow-list / `env` `$KEY` refs). Same command, different
  resulting config depending on whether delegation succeeds.
- **#232** — `delegate_add` / `delegate_remove` accept no `scope`, so a
  delegated `--scope project` silently targets the agent's default (user)
  config and never the project config.

Fixing each in isolation (an `--env` patch here, a `--scope` patch there) would
leave two divergent decision points for one question: *can the native CLI
faithfully reproduce what the file edit would write?* This change answers that
question once, in the single-source `ADAPTERS` registry, and applies it to both
`add` and `remove`.

## Scope

### In Scope

- `src/sofer/mcp_registration.py`: add native-delegation capability fields to
  the single-source `Adapter` registry (`native_env`, `native_scope`); add a
  pure predicate `native_delegation_decline_reasons(agent, env_keys, scope)`
  that is the ONE place the fidelity gate lives; grow `delegate_add(agent, cwd,
  env_keys, scope)` and `delegate_remove(agent, scope)` to consult it, to
  forward `--scope` where the agent CLI supports it, and to decline (return
  `False`) otherwise.
- `src/sofer/cli.py`: pass `scope` through; when native delegation is declined
  for a fidelity reason, print an informational stderr warning naming the agent
  and the reason(s) (`env forwarding`, `project scope` — NAMES only, never
  values) before falling back to file edit; update the `mcp` help/description
  strings.
- `tests/test_mcp_registration.py`, `tests/test_cli.py`: registry capability
  invariant, decline/forward tests (mock subprocess, assert args), CLI warning
  and fallback tests; update the two existing pins that asserted the old
  env-dropping delegated call.
- Docs: `README.md` + `README_ES.md` delegation/env parity note.
- Specs: `mcp-registration` (MCP-REG-01, MCP-REG-02, new MCP-REG-04) and `cli`
  (CLI-R09) deltas.

### Out of Scope

- **#204, #205, #234** — untouched.
- The native command *shape* (`--command`/`--cwd` argv, the gemini user path
  `~/.config/gemini/settings.json` vs Gemini's documented `~/.gemini/settings.json`)
  — pre-existing, separate concerns.
- Actually persisting env VALUES natively — forbidden: the never-persist-secret-
  values invariant (CF-3) outranks "use the native CLI".

### New Capabilities

None — no new capability domain. `mcp-registration` gains one requirement
(MCP-REG-04).

### Modified Capabilities

- `mcp-registration` (MCP-REG-01, MCP-REG-02): the "prefer native" clause is
  qualified by the fidelity gate; new MCP-REG-04 states the gate.
- `cli` (CLI-R09): the `mcp add` help contract additionally documents that
  native delegation is used only when it can faithfully forward env and scope,
  and that a warning is emitted when it cannot.

## Approach

The unified criterion: **delegate to the native CLI only when it can express the
same entry the file edit would; otherwise decline and edit the file.**

Researched native capabilities (context7):

| Agent | native `mcp add` scope | native `mcp add` env | native `mcp remove` scope |
|-------|------------------------|----------------------|---------------------------|
| gemini | `-s/--scope user\|project` (default project) | `-e KEY=value` (literal value persisted) | honours `--scope` |
| codex  | none (always global `$CODEX_HOME/config.toml`) | `--env KEY=VALUE` (literal value persisted) | none (always global) |
| opencode / pi | no native CLI | no native CLI | no native CLI |

Consequences encoded in the registry:

- `native_env=False` for every agent: neither native CLI can forward an env
  NAME without persisting a literal value, so a non-empty `env_keys` makes the
  native path unfaithful → decline, file edit (which persists NAMES only).
- `native_scope=True` only for gemini: `--scope` is forwarded there; for codex a
  `--scope project` request makes the native path unfaithful → decline, file
  edit.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_registration.py` | Modified | Two adapter capability fields + fidelity predicate; delegates consult it and forward `--scope` |
| `src/sofer/cli.py` | Modified | Passes scope; decline warning; help/description strings |
| `README.md`, `README_ES.md` | Modified | Delegation/env parity note |
| `openspec/specs/mcp-registration/spec.md` | Modified | MCP-REG-01/02 qualified; MCP-REG-04 added |
| `openspec/specs/cli/spec.md` | Modified | CLI-R09 help contract |
| `tests/test_mcp_registration.py`, `tests/test_cli.py` | Modified | Capability/decline/forward/warning coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Native delegation silently keeps diverging for a capability nobody modeled | Low | The gate is one predicate driven by registry data; a new agent declares its native capabilities in one entry |
| Regression: a working delegated path stops delegating | Med | Intended for the unfaithful cases; the faithful cases (empty env + supported scope) still delegate and are pinned by tests |
| A future agent's `--env` really does support name refs | Low | `native_env` is a per-agent flag; flipping it is a one-line registry change with a test |
| Secret values leak through a native `--env KEY=value` | Low | `native_env=False` forces env-present calls onto the file-edit path (NAMES only) |
| `cli.py` 100% per-file coverage gate (rule 14) regresses | Med | New warning/forward/decline branches each get a test; coverage measured in verify |

## Rollback Plan

Revert the change. No data or migration is involved. Reverting restores the
previous (unfaithful) delegation; already-written configs are untouched, and
re-running `sofer mcp add/remove` on the previous revision reconciles them.
Existing opencode/pi registrations and all file-edit paths are unaffected either
way.

## Dependencies

- Requires the single-source registry from #235 (merged #241, `ADAPTERS` /
  `AGENT_NAMES`). No new third-party dependency.

## Success Criteria

- [ ] `delegate_add` with a non-empty `env_keys` returns `False` (declines) for
  codex/gemini; the resulting `sofer` entry persists the same env NAMES as the
  file-edit path, never values.
- [ ] `delegate_add`/`delegate_remove` forward `--scope <scope>` to gemini;
  codex declines when `--scope project` is requested, so `--scope project` never
  ends in a user-only write.
- [ ] The CLI prints an informational stderr warning (agent + reason, no
  secrets) when delegation is declined for env/scope, then falls back to file
  edit; exit code unchanged.
- [ ] opencode/pi still file-edit only; the faithful codex/gemini cases still
  delegate.
- [ ] README + README_ES + CLI help updated; specs synced; tests + ruff + mypy +
  pyright + coverage gates green.
