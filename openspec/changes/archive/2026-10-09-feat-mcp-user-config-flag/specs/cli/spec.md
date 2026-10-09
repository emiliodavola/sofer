# Delta for cli

> **Change** `2026-10-09-feat-mcp-user-config-flag` (issue **#274**) · branch
> `feat/274-mcp-user-config-flag` · store **hybrid**.
>
> **One modification, no new requirement.** CLI-R09 gains `--user-config` for both `mcp add` and
> `mcp remove`, and states the `--agent all` rejection.
>
> **Rule-6 resolution.** `cli` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the new expectations map to the tests in
> `tests/test_mcp_registration.py` and `tests/test_cli.py` without a Test Mapping row, and the registry
> is not edited.

## MODIFIED Requirements

### Requirement: mcp add/remove help (CLI-R09)

> Added by change `sofer-mcp-agents` (archived 2026-08-30). Modified by
> `2026-10-09-feat-mcp-user-config-flag` (issue #274) — both subcommands accept `--user-config`.

**Modification scope.** Exactly three spans move, and nothing else in the requirement does:

| Span | Operation |
| --- | --- |
| the flag enumeration sentence | `[--user-config PATH]` inserted after `[--cwd PATH]` in the `add` list (and the flag is accepted by `remove` too) |
| the requirement body | one paragraph appended stating the flag's meaning and the `--agent all` rejection |
| the `add help` scenario | `--user-config` added to the list of flags that SHALL be listed |

**Added text (verbatim, as it reads in the canonical spec after this change):**

`add` and `remove` MUST also accept `--user-config PATH`: the explicit user-scope config **file**,
which wins over the adapter's env override and the home default, and which MUST be rejected with
`--agent all` because one path cannot name four different agent config files.

**Modified scenario line (verbatim):**

- THEN `--agent`, `--scope`, `--cwd`, `--user-config`, `--dry-run` SHALL be listed

## Non-goals recorded by this change

No new requirement; no Test Mapping row; no registry edit; no change to any other CLI surface; no
change to `--cwd`'s rule (that was slice 1, `2026-10-09-fix-mcp-user-config-resolution`).
