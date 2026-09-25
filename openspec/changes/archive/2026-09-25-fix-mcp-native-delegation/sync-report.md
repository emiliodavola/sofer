# Sync Report: 2026-09-25-fix-mcp-native-delegation

## Spec synchronization

Two capability specs were synced from this change's deltas:

### `mcp-registration`

- **MCP-REG-01 (MODIFIED)** — the "prefer native registration else file merge"
  clause is qualified: delegate only when the native CLI can faithfully forward
  the same env NAMES and scope as the file edit, else file merge (see
  MCP-REG-04). The `Native delegation` scenario now states the "no env NAMES,
  expressible scope" precondition.
- **MCP-REG-02 (MODIFIED)** — `remove` delegates only when it can faithfully
  express the requested scope, else file edit (see MCP-REG-04).
- **MCP-REG-04 (ADDED)** — Native delegation fidelity: the single
  registry-driven predicate; env-decline, scope-forward (gemini), scope-decline
  (codex), warning + fallback, and faithful-cases-still-delegate scenarios.

### `cli`

- **CLI-R09 (MODIFIED)** — the help contract additionally documents native
  delegation fidelity (used only when it can forward the same env NAMES and
  scope; otherwise the config file is edited with a warning on stderr), with a
  matching scenario.

The canonical files were edited directly to match the delta requirement bodies.

## Test-mapping contract

`mcp-registration` and `cli` remain **unmapped** (no `## Test Mapping` table), so
this change adds no mapped rows and the registry↔tree bijection is unchanged:

```
$ uv run python scripts/check_test_mapping.py
INFO: mcp-registration: 31 scenario(s), unmapped
INFO: cli: 49 scenario(s), unmapped
...
OK: test-mapping contract holds
```

An informational scenario→test map is recorded in the change's
`verify-report.md` (not a `## Test Mapping` heading, so the gate is unaffected).
