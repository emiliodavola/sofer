# Design: 2026-09-25-fix-mcp-native-delegation

## Context

`mcp_registration.py` owns per-agent behavior through the single-source
`ADAPTERS` registry (#235, merged #241). `cli._cmd_mcp_add` /
`_cmd_mcp_remove` probe the native CLI (`probe_native`) and, on success, call
`delegate_add` / `delegate_remove`; a truthy result short-circuits the
file-edit path, a falsy result falls back to it.

Today `delegate_add(agent, cwd, env_keys)` documents `env_keys` as *"unused for
native path but kept for signature parity"* and `delegate_remove(agent)` takes
no scope. The native argv is scope-less and env-less, so a delegated
registration silently differs from the file edit (#167) and silently ignores
`--scope` (#232).

Native CLI capabilities were verified externally (context7, Codex
`cli/src/mcp_cmd.rs`, Gemini CLI `docs/tools/mcp-server.md`):

- `gemini mcp add [options] <name> <commandOrUrl>` supports `-s/--scope user|project`
  (default **project**) and `-e KEY=value`; `gemini mcp remove` honours the
  scope flag.
- `codex mcp add [OPTIONS] <name> (--url | -- <COMMAND>...)` supports
  `--env KEY=VALUE`; neither `codex mcp add` nor `codex mcp remove` has a scope
  selector — both act on the global `$CODEX_HOME/config.toml`.

Both native env flags take literal `KEY=VALUE` pairs. sofer's env contract is
the opposite: it persists env **NAMES** only and never secret values (CF-3).
Passing `--env HF_TOKEN=<value>` would persist the secret; passing
`--env HF_TOKEN=$HF_TOKEN` would persist a literal string that Codex does not
interpolate (Codex has no `$` expansion; Gemini's expansion semantics at
add-time are not guaranteed). Neither is faithful, so env forwarding is not
delegable.

## Decisions

### D1 — The fidelity gate is one pure predicate over registry data

Add `native_delegation_decline_reasons(agent, env_keys, scope) -> list[str]`. It
returns the reasons (empty list = native may proceed), reading only
`ADAPTERS`:

```python
spec = ADAPTERS.get(agent)
native_env = spec["native_env"] if spec is not None else False
native_scope = spec["native_scope"] if spec is not None else False
reasons: list[str] = []
if env_keys and not native_env:
    reasons.append("env forwarding")
if scope == "project" and not native_scope:
    reasons.append("project scope")
return reasons
```

`delegate_add` and `delegate_remove` both gate on it, and `cli.py` calls it only
to choose the warning text. This is the single decision point #167 and #232
share — no second patch, no divergent policy.

### D2 — Registry gains exactly two capability fields

`Adapter` gains `native_env: bool` and `native_scope: bool`; every entry
declares both so the "every adapter is complete" invariant stays an exact
`set(spec) == required` rather than a per-agent special case.

```python
"opencode": {..., "native_env": False, "native_scope": False}
"codex":    {..., "native_env": False, "native_scope": False}
"gemini":   {..., "native_env": False, "native_scope": True}
"pi":       {..., "native_env": False, "native_scope": False}
```

`native_env=False` is the *correct* value for codex/gemini today (value
semantics); the field exists so a future agent whose native CLI forwards NAME
refs is a one-line change.

### D3 — `delegate_add` / `delegate_remove` grow a `scope` parameter

```python
def delegate_add(agent, cwd, env_keys, scope="user") -> bool
def delegate_remove(agent, scope="user") -> bool
```

`scope` defaults to `"user"` (the CLI default), so direct callers keep working.
When `native_scope` is true the argv forwards `--scope <scope>`; when false no
scope flag is emitted. Both functions return `False` (immediately, without
spawning) when `native_delegation_decline_reasons` is non-empty.

Argv shape (options before the positional name, matching the documented
`gemini mcp add [options] <name>` form):

```text
<exe> mcp add [--scope <scope>] sofer --command sofer-mcp --cwd <cwd>
<exe> mcp remove [--scope <scope>] sofer
```

The pre-existing `--command`/`--cwd` shape is deliberately NOT changed here
(out of scope; separate concern).

### D4 — CLI warns only on a fidelity decline, not on an operational failure

`_cmd_mcp_add` / `_cmd_mcp_remove` keep calling the delegate and keep the
existing generic *"native … failed, falling back to file edit"* message for a
raise or a non-zero native exit. They add a distinct informational warning,
naming the reason(s), only when the delegate returned `False` without raising
and the gate has reasons:

```text
  !  codex native mcp add cannot express env forwarding, project scope; falling back to file edit
```

NAMES only (`env forwarding`, `project scope`) — the warning never carries a
value. Exit code is unchanged: the fallback file edit still honours env NAMES
and the requested scope, so the command succeeds.

Why keep calling the delegate when it will decline? It preserves the existing
call/test contract (the delegate is the authority) and the CLI's reason
computation stays purely cosmetic. A mocked `delegate_add` returning `True`
still short-circuits, exactly as before.

### D5 — No change to `probe_native` or `_delegates`

The probe answers "is the native CLI available", not "is delegation faithful".
The gate belongs to the delegate, so `probe_native` is untouched and opencode/pi
remain file-edit only via `delegates=False`.

## Contract / invariants

- Every adapter has exactly eleven keys, including `native_env` and
  `native_scope`.
- `native_delegation_decline_reasons(a, env, scope)` is `[]` iff delegation is
  faithful: `not env` or `native_env`, AND (`scope != "project"` or
  `native_scope`).
- `delegate_add` returns `False` without spawning when there is any decline
  reason; `delegate_remove` likewise (env is irrelevant to remove, so callers
  pass `[]`).
- `--scope project` never results in a user-only write: it is either forwarded
  (gemini) or declined to file edit (codex).
- Secret values are never passed to a native `--env`/`-e` argument.
- opencode/pi remain file-edit only; faithful codex/gemini cases still delegate.

## Test strategy

- `TestNativeDelegationFidelity` (unit): capability fields present; predicate
  truth table for codex/gemini/opencode/pi over env × scope; `delegate_add`
  argv contains `--scope user|project` for gemini and no env flag; codex
  declines on project scope; both decline when env is non-empty; `delegate_remove`
  forwards scope for gemini and declines project for codex.
- `tests/test_cli.py` (CLI): decline warning appears on stderr (env and scope,
  names only) and the file-edit fallback runs; gemini scope forwarding reaches
  the mocked native call; `cli.py` stays at 100% by exercising every new branch.
- Update existing pins: `test_present_delegates` (env now declines) and any
  assertion of the old env-dropping call.

## Consequences

- `sofer mcp add/remove --agent codex|gemini` is now *correct by construction*
  rather than accidentally correct only when the native CLI happens to be
  absent.
- In practice codex/gemini delegation is used only for an env-less user-scope
  add (and gemini remove with a forwarded scope); every other case uses the
  file edit. That is the intended trade: correctness over delegating.
- A new agent stays a single `ADAPTERS` entry plus its two native-capability
  bits.
