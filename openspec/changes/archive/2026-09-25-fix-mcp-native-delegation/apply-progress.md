# Apply Progress: 2026-09-25-fix-mcp-native-delegation

## Status

Complete. Unified native-delegation fidelity gate implemented in
`mcp_registration.py`, surfaced in `cli.py`, tested, documented, and synced.

## What changed

### `src/sofer/mcp_registration.py`

- `Adapter` gains `native_env: bool` and `native_scope: bool`; all four entries
  declare them (opencode `F/F`, codex `F/F`, gemini `F/T`, pi `F/F`).
- New `native_delegation_decline_reasons(agent, env_keys, scope) -> list[str]`:
  the single fidelity predicate. `["env forwarding"]` when env NAMES must be
  forwarded but the native CLI cannot; `["project scope"]` when project scope is
  requested and the native CLI has no scope selector.
- `delegate_add(agent, cwd, env_keys, scope="user")` gates on the predicate
  (returns `False` without spawning), and forwards `--scope <scope>` when
  `native_scope`.
- `delegate_remove(agent, scope="user")` gates with `env_keys=[]` and forwards
  `--scope` when `native_scope`.
- Module/TypedDict/function docstrings document the criterion.

### `src/sofer/cli.py`

- `_scope` is computed once and passed to both delegates.
- A fidelity decline prints
  `  !  <agent> native mcp add/remove cannot express <reason(s)>; falling back to file edit`
  on stderr (reason labels only, never values); a raise or non-zero exit keeps
  the generic `native … failed, falling back to file edit` message.
- `mcp add`/`mcp remove` help/description strings document the fidelity gate.

### Docs / specs

- `README.md`, `README_ES.md`: delegation bullet rewritten for the gate.
- New change folder with `proposal.md`, `explore.md`, `design.md`, `tasks.md`,
  and deltas `specs/mcp-registration/spec.md`, `specs/cli/spec.md`.
- Canonical `openspec/specs/mcp-registration/spec.md` (MCP-REG-01/02 qualified,
  MCP-REG-04 added) and `openspec/specs/cli/spec.md` (CLI-R09 extended) synced.

## Notes / decisions

- `native_env=False` for every current agent because codex/gemini native env
  flags (`--env`/`-e`) take literal `KEY=VALUE` values, which would persist a
  secret (CF-3 violation). The field is per-agent so a future native CLI that
  forwards NAME refs is a one-line registry change.
- The CLI re-calls the same pure predicate only to choose warning text; the
  delegate remains the authority. In real usage the two cannot diverge (a
  non-empty reason set makes the delegate decline before spawning; a raise or
  non-zero exit implies no reason).

## Out of scope (unchanged)

#204, #205, #234; the native `--command`/`--cwd` argv shape; the gemini user
path `~/.config/gemini/settings.json` (vs Gemini's documented `~/.gemini/`).
