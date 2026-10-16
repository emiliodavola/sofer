# Proposal — `2026-10-16-fix-codex-home-resolution`

> **Change** `2026-10-16-fix-codex-home-resolution` · issue **#325** · branch
> `fix/325-codex-home-and-321-delegation` (from `fix/316-321-bug-chore-followups`) · store **hybrid**.
>
> **Status:** implementation complete; archived inside the delivering PR (AGENTS.md rule 15).

## 1. Intent

`sofer mcp add --agent codex` could write into a file codex never reads.

## 2. The defect, measured

`src/sofer/mcp_registration.py:127` documents, in the `native_scope` field of the adapter contract, that
codex's native commands "always act on the global `$CODEX_HOME` config". The adapter declares
`user_env_dir: None` (`:219`) with `user_parts: (".codex", "config.toml")` (`:204`), so
`resolve_config_path` never consults the variable:

```text
$ CODEX_HOME=/tmp/other-codex uv run python -c "
import os; os.environ['CODEX_HOME'] = '/tmp/other-codex'
from sofer.mcp_registration import resolve_config_path
print(resolve_config_path('codex', 'user'))
"
C:\Users\elaze\.codex\config.toml
```

The command exits 0 and the registration is invisible to codex: the class of defect #274 exists to
remove, for the one host #274 did not cover.

## 3. Scope

- `ADAPTERS["codex"]`: `user_env_dir = "CODEX_HOME"`. `user_parts` is unchanged (design D1).
- Both READMEs' per-agent table names the override, as they already do for Pi and Hermes.
- Three tests: the override wins, the no-variable default survives, project scope ignores the override.

## 4. Why this carries no spec delta

The spec already requires the resolution order — `--user-config PATH`, then the adapter's `user_env_dir`
file, then `Path.home()` joined with `user_parts` (`openspec/specs/mcp-registration/spec.md:69-73`) — and
its per-agent table names only the file name (`:16`). The defect is that codex's adapter *data* contradicted
the contract its own field documents, which is an adapter-data fix rather than a rule change. Nine archived
changes carry no `specs/` delta, so this is an established shape.

## 5. Non-goals

- **#321's option 1** — the next commit on this branch, and it *does* carry a delta: it reverses an
  MCP-REG-05 clause.
- **Project-scope resolution for codex**, unchanged: `cwd/.codex/config.toml`.
- **Re-deriving codex's own behaviour.** Whether codex honours `$CODEX_HOME` is not verified from codex's
  sources here; the repository asserts it at `:127`, and this change makes sofer agree with its own
  documented belief. If that assertion is wrong, this change is a no-op and the assertion is the bug.
