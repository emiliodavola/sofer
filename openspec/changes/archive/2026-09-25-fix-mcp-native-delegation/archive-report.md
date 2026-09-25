# Archive Report: 2026-09-25-fix-mcp-native-delegation

## What was archived

`openspec/changes/archive/2026-09-25-fix-mcp-native-delegation/` with
`explore.md`, `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`,
`verify-report.md`, `sync-report.md`, `archive-report.md`, and
`specs/mcp-registration/spec.md` + `specs/cli/spec.md` (the deltas retained for
provenance).

## Change summary

Issues #167 and #232 were two symptoms of one defect on the native MCP
delegation path: `delegate_add`/`delegate_remove` silently produced a
registration that differed from the file-edit fallback — dropping env NAMES
(#167) and ignoring `--scope` (#232). The fix introduces one fidelity criterion,
gated by the single-source `ADAPTERS` registry:

- `Adapter` gains `native_env` and `native_scope`.
- `native_delegation_decline_reasons(agent, env_keys, scope)` is the single
  predicate consumed by both delegates.
- Native delegation forwards `--scope` where the agent CLI supports it
  (gemini); it declines (returns `False` without spawning) when env NAMES must
  be forwarded and cannot be represented faithfully, or when `--scope project`
  is requested from a scope-less CLI (codex).
- The CLI warns on stderr naming the reason (`env forwarding`, `project
  scope`; NAMES only) and falls back to file edit; exit code unchanged.
- opencode/pi remain file-edit only; faithful codex/gemini cases still delegate.

## Spec synchronization

- `mcp-registration`: MCP-REG-01/02 MODIFIED (fidelity-qualified "prefer
  native"); MCP-REG-04 ADDED (native delegation fidelity).
- `cli`: CLI-R09 MODIFIED (help documents the fidelity gate).
- Canonical specs edited to match the deltas. `mcp-registration` and `cli` stay
  unmapped, so `scripts/check_test_mapping.py` still reports `OK: test-mapping
  contract holds`.

## Verification

Area tests 279 passed; full suite under coverage 1888 passed / 2 skipped; ruff
check + format clean; mypy clean; pyright 0 errors (1 pre-existing warning);
test-mapping OK; core 100% gates green; `cli.py` 100%, `mcp_registration.py`
100%, TOTAL 93%. Independent read-only `general` subagent: **all 8 claims PASS,
nothing falsified**; its README-wording note was fixed before archiving.

## Follow-ups (not this change)

- **Gemini user config location** — sofer's file-edit user path
  `~/.config/gemini/settings.json` differs from Gemini CLI's documented
  `~/.gemini/settings.json`; a pre-existing path concern (adjacent to
  #204/#205), not touched here.
- **Native argv shape** — `--command sofer-mcp --cwd <cwd>` is preserved; a
  separate review could align it with each CLI's documented `-- <command>`
  form. Not part of #167/#232.
