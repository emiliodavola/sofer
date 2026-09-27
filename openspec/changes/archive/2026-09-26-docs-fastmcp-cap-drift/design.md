# Design: fastmcp cap drift (#257)

**Change**: `docs-fastmcp-cap-drift`

## Delta shape

`## MODIFIED Requirements` carrying the **complete** requirement blocks for PKG-06, MSP-R02,
and MSP-R12 as they must read after the change. Scenarios are reproduced unchanged; only the
`fastmcp>=3.4,<4` literal becomes `fastmcp>=4,<5` (and the alias `["fastmcp>=4,<5"]`). The
state is composed into the canonical specs during archive.

## Requirement provenance

Each amended requirement gains a `Modified by docs-fastmcp-cap-drift (issue #257, 2026-09-26)`
note next to the existing `Added by` / `Modified by feat-mcp-auto-install` notes, so the
history of the cap is readable without a git blame.

## Guard

`tests/test_packaging.py::test_fastmcp_cap_is_single_across_declaration_homes`:

1. derive the cap from `pyproject.toml` with `fastmcp(?P<cap>>=[^"'\s]+)` → `>=4,<5`; assert
   exactly one distinct cap across the dependency, the `mcp` extra, and the dev group;
2. assert `openspec/specs/packaging/spec.md` and `openspec/specs/mcp-server/spec.md` name
   `fastmcp>=4,<5`;
3. assert the retired `fastmcp>=3.4,<4` literal is absent from both specs, `CONTRIBUTING.md`,
   and `.github/dependabot.yml`, and that the two prose homes no longer say `` `<4` ``.

The guard holds no version literal of its own (the cap is derived), matching CI-08/CI-13.

## Why the specs stay unmapped

Both `packaging` and `mcp-server` are in the permanent declared backlog
(`openspec/test-mapping-registry.md`), and this change neither adds nor removes a scenario.
The guard is a supporting guard, not a new scenario, so the registry bijection is unchanged.

## Test strategy

| Guard | Positive | Negative control |
| --- | --- | --- |
| cap consistency | 1 cap, named everywhere | restore `fastmcp>=3.4,<4` in packaging spec → fails |
| pyproject cap | derived `>=4,<5` | widen to `>=4,<6` in one home → fails (2 caps) |
