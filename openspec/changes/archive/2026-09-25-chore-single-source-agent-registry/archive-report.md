# Archive Report: 2026-09-25-chore-single-source-agent-registry

## What was archived

`openspec/changes/archive/2026-09-25-chore-single-source-agent-registry/` with
`explore.md`, `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`,
`verify-report.md`, `sync-report.md`, `archive-report.md`.

## Spec synchronization

**No spec deltas.** This is a pure internal refactor: entry shapes, config paths,
idempotency, delegation and env handling are unchanged, and no requirement or scenario
is added, modified, or removed.

`mcp-registration` and `cli` remain registered in `openspec/test-mapping-registry.md`
as unmapped (no `## Test Mapping` table), so the registry↔tree bijection is unchanged
and `scripts/check_test_mapping.py` still reports:

```
OK: test-mapping contract holds
```

## Follow-ups (not this change)

- **#142** (`pi`): one new `ADAPTERS` entry; `cli.py` needs no edit.
- **`src/sofer/mcp_server.py:218-236`** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` — an
  adjacent duplicate roster for approval-phrase hints, out of #235's file scope.
