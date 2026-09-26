# Archive Report: 2026-09-25-feat-pi-mcp-agent

## What was archived

`openspec/changes/archive/2026-09-25-feat-pi-mcp-agent/` with `explore.md`,
`proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`,
`sync-report.md`, `archive-report.md`, and `specs/mcp-registration/spec.md` +
`specs/cli/spec.md` (the deltas retained for provenance).

## Change summary

Issue #142: added `pi` (`pi-mcp-adapter`) as the fourth MCP agent on the
single-source `ADAPTERS` registry (#235/#241). Pi is one registry entry plus two
new capability values: `user_env_dir` (`PI_CODING_AGENT_DIR` overrides the
user-scope directory) and `env="refs_braced"` (Pi interpolates only `${KEY}`).
`--agent all` now expands to four agents. Pi is file-edit only, persists env
NAMES only, and writes Pi-owned files (`$PI_CODING_AGENT_DIR/mcp.json` /
`~/.pi/agent/mcp.json` / `./.pi/mcp.json`) — which at user scope also shadows a
malformed lower-precedence shared `~/.config/mcp/mcp.json` entry.

## Spec synchronization

- `mcp-registration`: MCP-REG-01/02/03 MODIFIED (four agents, Pi entry/env/
  scopes, `all` → four).
- `cli`: CLI-R09 MODIFIED (`--agent` includes pi; forwarding sentence includes
  pi).
- Canonical specs synced; requirement bodies byte-identical to the deltas
  (independently diffed). `mcp-registration` and `cli` stay unmapped, so
  `scripts/check_test_mapping.py` still reports `OK: test-mapping contract
  holds`.

## Verification

Full suite 1875 passed / 2 skipped; focused MCP area 265 passed; ruff, mypy,
pyright, test-mapping and core-coverage gates green; `mcp_registration.py` 100%
and `cli.py` 100% (TOTAL 93%). Independent read-only `general` subagent:
**PASS, all 11 claims verified, none falsified.** One test gap it found (Pi not
asserted in the no-warning test) was fixed before archiving.

## Follow-ups (not this change)

- **`src/sofer/mcp_server.py`** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` — the
  approval-phrase setup-hint roster still lists only opencode/codex/gemini; a
  separate concern (same boundary #235 drew).
- **Pi optional fields** (`directTools`, `lifecycle`, `toolPrefix`) — left
  minimal on purpose; a follow-up could expose them.
- **Pre-existing:** `mcp remove --scope project` anchors on `Path.cwd()` because
  `remove` has no `--cwd`; applies to every agent, unchanged by #142.
