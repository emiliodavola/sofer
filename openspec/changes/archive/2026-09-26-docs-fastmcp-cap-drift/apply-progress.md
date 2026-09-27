# Apply Progress: Align the fastmcp cap to `>=4,<5` (#257)

**Change**: `docs-fastmcp-cap-drift`
**Mode**: SDD (MODIFIED requirements; no new scenario)

## Completed Tasks

- [x] 1.1–1.3 Canonical specs amended (PKG-06, MSP-R02, MSP-R12) with provenance notes.
- [x] 2.1–2.2 CONTRIBUTING + dependabot cap prose aligned.
- [x] 3.1 Supporting guard in `tests/test_packaging.py`.
- [x] 4.1–4.5 Verification + independent verification.
- [x] 5.1 Archive.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `openspec/specs/packaging/spec.md` | Modified | PKG-06 cap `>=3.4,<4` → `>=4,<5` + provenance |
| `openspec/specs/mcp-server/spec.md` | Modified | MSP-R02 + MSP-R12 cap → `>=4,<5` + provenance |
| `CONTRIBUTING.md` | Modified | fastmcp cap prose `<4` → `<5` |
| `.github/dependabot.yml` | Modified | fastmcp cap comment `<4` → `<5` |
| `tests/test_packaging.py` | Modified | Cap-consistency guard derived from `pyproject.toml` |
| `openspec/changes/archive/2026-09-26-docs-fastmcp-cap-drift/` | New | This change's artifacts |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_packaging.py -q -k fastmcp_cap` — `1 passed` |
| Runtime harness command/scenario and result | `uv run pytest tests/test_mcp_server.py -q -k wheel_declares_script_and_extra` — skipped locally (hatchling absent; CI builds the wheel). Full `uv run pytest tests/ -q` — `1989 passed, 1 skipped` |
| Negative controls | packaging-spec cap reverted to `>=3.4,<4` → fails; CONTRIBUTING `<5`→`<6` → fails; a contradictory `fastmcp>=3,<4` added to a spec → fails; all restored byte-for-byte |
| Lint/format gates | `ruff check src/ tests/ scripts/` passed; `ruff format --check src/ tests/` 73 files formatted |
| Test-mapping checker | `OK: test-mapping contract holds` (both specs remain in the registered backlog) |
| Rollback boundary | Revert the five-file diff + change folder; no dependency/code/workflow/release state touched |

## Deviations from Design

The guard was hardened after independent verification's MINOR findings: it now also asserts a
**positive** upper-bound match in the two prose homes (catches CONTRIBUTING/dependabot drifting
to a different `<N`) and rejects a **contradictory** fastmcp cap in either spec.

## Remaining Tasks

None.
