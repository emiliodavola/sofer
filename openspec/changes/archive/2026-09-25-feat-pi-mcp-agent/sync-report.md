# Sync Report: 2026-09-25-feat-pi-mcp-agent

## Spec synchronization

Two capability specs were synced from this change's deltas:

### `mcp-registration`

- **MCP-REG-01 (MODIFIED)** — supported agent set is
  `<opencode|codex|gemini|pi|all>`; Pi entry table row; Pi `${KEY}` env rule;
  Pi user/project path rule; "Add all" now expects 4 configs; added scenarios
  `Add Pi user`, `Add Pi project`, `Pi entry shape`, `Pi env braced references
  only`.
- **MCP-REG-02 (MODIFIED)** — `remove` accepts `pi`; "Remove all" expects 4
  configs; added scenario `Remove Pi preserves others`.
- **MCP-REG-03 (MODIFIED)** — `--agent all` expands to four agents; Pi added to
  the non-warning forwarding set; the "fires once" and "no warning" scenarios
  updated.

### `cli`

- **CLI-R09 (MODIFIED)** — `--agent` surface includes `pi`; the env-forwarding
  help sentence names codex/gemini/pi.

The canonical files were edited directly to match the delta requirement bodies
(the requirement bodies under
`openspec/changes/2026-09-25-feat-pi-mcp-agent/specs/` are byte-identical to the
canonical sections, as verified by an independent `diff`).

## Test-mapping contract

`mcp-registration` and `cli` remain **unmapped** (no `## Test Mapping` table), so
this change adds no mapped rows and the registry↔tree bijection is unchanged:

```
$ uv run python scripts/check_test_mapping.py
INFO: mcp-registration: 26 scenario(s), unmapped
INFO: cli: 48 scenario(s), unmapped
...
OK: test-mapping contract holds
```

An informational scenario→test map is recorded in the change's
`verify-report.md` (not a `## Test Mapping` heading, so the gate is unaffected).
