# Exploration: fastmcp cap drift (#257)

**Change**: `docs-fastmcp-cap-drift`
**Issue**: GitHub #257 — specs/CONTRIBUTING/dependabot still require `fastmcp <4` while code/lock/tests are on `>=4,<5`.
**Mode**: SDD (normative SHALL requirements are amended).

## Shipped truth (verified)

| Home | Value |
| --- | --- |
| `pyproject.toml:22,45,57` | `fastmcp>=4,<5` (dependency, `mcp` extra alias, dev group) |
| `uv.lock:3357-3374` | `fastmcp>=4,<5`, resolved `fastmcp 4.0.5` |
| `tests/test_mcp_server.py:2834` | asserts `Requires-Dist: fastmcp<5,>=4` |
| `src/sofer/mcp_server.py` | fastmcp 4 API adaptation (PR #253) |

## Stale declaration homes (verified)

| Home | Stale text |
| --- | --- |
| `openspec/specs/packaging/spec.md:132-145` | PKG-06 requires `fastmcp>=3.4,<4` in the requirement, the scenario, and the alias scenario |
| `openspec/specs/mcp-server/spec.md:31-67` | MSP-R02 requires `fastmcp>=3.4,<4` in the requirement, the alias, and the wheel scenario |
| `openspec/specs/mcp-server/spec.md:471-487` | MSP-R12 requires `fastmcp>=3.4,<4` in the requirement and two scenarios |
| `CONTRIBUTING.md:118-120` | "the declared `<4` cap is a real boundary" |
| `.github/dependabot.yml:18-20` | "rewrites the declared `<4` cap itself (#253)" |

Both specs are in the permanent unmapped `## Test Mapping` backlog
(`openspec/test-mapping-registry.md:30,33`), so no guard covered them and the drift was
invisible to the suite.

## Decision: SDD

The affected text is normative RFC-2119 (`SHALL declare fastmcp>=3.4,<4`), not descriptive
prose. Amending a requirement is an SDD change with MODIFIED-requirement deltas, as the issue
states. No scenario list changes: the cap literal is the only edit.

## Guard decision

The issue asks to "consider adding a static guard ... that asserts a single fastmcp cap
across pyproject.toml and the specs". A guard is cheap and closes the drift class, so it is
in scope: a supporting guard in `tests/test_packaging.py` derives the cap from
`pyproject.toml` and asserts every prose home (the two specs, CONTRIBUTING, dependabot) names
it and that the retired `fastmcp>=3.4,<4` literal is gone.
