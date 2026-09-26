# Sync Report: 2026-09-25-chore-single-source-agent-registry

## Delta specs

None. This change contains no `specs/` directory: it is a pure refactor of
`src/sofer/mcp_registration.py`, `src/sofer/cli.py` and
`tests/test_mcp_registration.py` with no requirement or scenario change.

## Canonical specs touched

None.

## Test-mapping contract

`mcp-registration` and `cli` were, and remain, registered as unmapped in
`openspec/test-mapping-registry.md`. The `mapped ∪ registered == specs` bijection is
unchanged; `uv run python scripts/check_test_mapping.py` → `OK: test-mapping contract
holds`.
