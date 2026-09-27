# Tasks: Align the fastmcp cap to `>=4,<5` (#257)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~30 authored (4 docs/specs + ~35 guard lines) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command |
|------|------|-----------|----------------------|
| 1 | Every fastmcp declaration home agrees on `>=4,<5` | PR 1 | `uv run pytest tests/test_packaging.py tests/test_mcp_server.py -q -k "fastmcp or wheel"` |

## Phase 1: Specs

- [x] 1.1 `packaging/spec.md` PKG-06 cap + provenance note.
- [x] 1.2 `mcp-server/spec.md` MSP-R02 cap + provenance note.
- [x] 1.3 `mcp-server/spec.md` MSP-R12 cap + provenance note.

## Phase 2: Prose homes

- [x] 2.1 `CONTRIBUTING.md` dependency-updates fastmcp cap → `<5`.
- [x] 2.2 `.github/dependabot.yml` fastmcp comment → `<5`.

## Phase 3: Guard

- [x] 3.1 `tests/test_packaging.py` cap-consistency guard (derived from `pyproject.toml`).

## Phase 4: Verify

- [x] 4.1 Focused guard + mcp wheel test.
- [x] 4.2 Full suite green; ruff/mypy/pyright clean.
- [x] 4.3 `scripts/check_test_mapping.py` exit 0.
- [x] 4.4 Independent read-only verification.
- [x] 4.5 Record evidence in `verify-report.md`.

## Phase 5: Archive

- [x] 5.1 Compose the canonical specs and move the change folder to `openspec/changes/archive/2026-09-26-docs-fastmcp-cap-drift/`.
