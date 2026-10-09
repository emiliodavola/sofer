# Delta for mcp-registration

> **Change** `2026-10-09-feat-mcp-user-config-flag` (issue **#274**) · branch
> `feat/274-mcp-user-config-flag` · store **hybrid**.
>
> **One modification, no new requirement.** MCP-REG-01 gains the user-scope resolution contract. The
> previous behaviour resolved under `Path.home()` alone, which follows `$HOME`, while agents such as
> opencode read their config from the system account home — so the entry could land in a file the agent
> never reads and sofer would report success.
>
> **Rule-6 resolution.** `mcp-registration` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the new scenario maps to `TestUserConfigResolution` in
> `tests/test_mcp_registration.py` without a Test Mapping row, and the registry is not edited.

## MODIFIED Requirements

### Requirement: MCP add idempotent and safe (MCP-REG-01)

> Added by change `sofer-mcp-agents` (archived 2026-08-30). Modified by
> `2026-10-09-fix-mcp-user-config-resolution` (issue #274) — the `--cwd` rule became existence instead
> of containment. Modified by `2026-10-09-feat-mcp-user-config-flag` (issue #274) — the user-scope
> config file resolves by explicit declaration first.

**Modification scope.** Exactly two spans move, and nothing else in the requirement does:

| Span | Operation |
| --- | --- |
| the requirement body | one paragraph appended: the three-step resolution, the blank-is-unset rule, the `--agent all` rejection, the mismatch warning, and project scope ignoring the flag |
| the requirement body | one amendment blockquote appended after that paragraph |
| the scenarios | one scenario appended: `User-scope config resolution` |

**Added clause (verbatim, as it reads in the canonical spec after this change):**

The user-scope config file SHALL resolve by explicit declaration first, then the adapter's environment
override, then the home directory: (1) `--user-config PATH` — returned as the stated **file** path, a
blank or whitespace-only value counting as unset; (2) the adapter's `user_env_dir` when that variable
is set to a non-empty value (Pi's `PI_CODING_AGENT_DIR`), whose directory replaces the home prefix and
whose file name is `user_parts[-1]`; (3) `Path.home()` joined with `user_parts` — the documented
default. `--user-config` SHALL be rejected when combined with `--agent all`, because each agent has its
own config file and one path is ambiguous for all of them. When `Path.home()` differs from the account
home (`pwd.getpwuid(os.getuid()).pw_dir` on POSIX), `add` and `remove` SHALL print a warning naming both
homes, so that a write into a file the agent never reads is never a silent success. Project scope SHALL
ignore `--user-config`: the declared file is a user-scope concept.

> Added by `2026-10-09-feat-mcp-user-config-flag` (issue #274). The previous behaviour resolved user
> scope under `Path.home()` alone, which follows `$HOME`; agents such as opencode resolve their config
> from the system account home and ignore both `$HOME` and `XDG_CONFIG_HOME`, so sofer could write the
> entry into a file the agent never reads **and report success**. Removing that silent no-op is the
> whole point of this clause.

**Added scenario (verbatim):**

#### Scenario: User-scope config resolution

- GIVEN a user-scope `add` or `remove`
- WHEN `--user-config PATH` is passed, or the adapter's env override is set, or neither is present
- THEN the config file SHALL be the first present of `--user-config PATH`, the adapter's `user_env_dir`
  file, and `Path.home()` joined with `user_parts` (a blank `--user-config` counts as unset, and project
  scope ignores it)
- AND `--user-config` combined with `--agent all` SHALL exit 1 without writing
- AND when the home and the account home differ, a warning naming both SHALL be printed to stderr

## Non-goals recorded by this change

No change to the server-root containment; no version bump; no new requirement; no Test Mapping row; no
registry edit; no commit/push/PR from SDD phases; no `# pragma: no cover`.
