# Sync report: 2026-09-25-csv-dialect-override

**Change:** `2026-09-25-csv-dialect-override` (GitHub #204)

## Canonical specs synced

| Capability | Delta | Canonical requirement added |
| --- | --- | --- |
| `codebook` | `specs/codebook/spec.md` | **CB-R12** — Explicit CSV dialect override wins over config |
| `profile` | `specs/profile/spec.md` | **PRF-07** — Explicit CSV dialect override for profile |
| `cli` | `specs/cli/spec.md` | **CLI-R12** — Optional explicit CSV dialect flags |
| `mcp-server` | `specs/mcp-server/spec.md` | **MSP-R18** — Optional explicit CSV dialect parameters |

All four are **ADDED** requirements; no existing requirement was rewritten
(the override is additive above the existing config tiers, per the issue's
spec-impact note). The canonical text matches each delta one-for-one, including
the MSP-R18 "successful envelope" clarification applied during verification.

## Gate

```
uv run python scripts/check_test_mapping.py
=> OK: test-mapping contract holds
```

`cli`, `codebook`, `profile`, and `mcp-server` are declared backlog in
`openspec/test-mapping-registry.md` (no `## Test Mapping` table). The registry
and the spec set remain a bijection — no entry was added or removed, and scenario
counts are re-derived by the checker.
