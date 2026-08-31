# Proposal: feat-mcp-auto-install

## Intent

`sofer-mcp` ships broken-by-default: `fastmcp` optional (`pyproject.toml:36-37`), so `uv tool install git+...@vX.Y.Z` → 22 pkgs, no fastmcp → crash. Make `sofer-mcp --help` succeed out-of-the-box (reporter: "instale automáticamente"); fix PEP 508 `git+...[mcp]` docs.

## Scope

### In Scope
- Promote `fastmcp>=3.4,<4` to `dependencies`; keep `mcp` alias one minor.
- Update `mcp_server.py:55-57` guard: pip + `uv tool` + `sofer[mcp] @ git+...` (keep degraded guard).
- Fix `README.md`/`README_ES.md` Install + AI/MCP: correct `name[extra] @ URL`, add `uv tool` + `uvx --with`; flip intro to included-by-default.
- Regenerate `uv.lock`; update `mcp-server` MSP-R02/R12.

### Out of Scope
- Two-wheel split; wrapper auto-install; vendoring; CI workflow.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `mcp-server`: MSP-R02 (lean → included-by-default) + MSP-R12 (optional → required + alias).

## Approach

Promotion + alias (§A): move pin to `dependencies`, keep alias in 3 places (identical pin, `uv lock` enforces). Keep 3-line guard for partial wheels. Docs: collapsed Install — canonical `sofer @ git+...` + alias note; both READMEs same commit (§13).

Rejected: docs-only, wrapper (MSP-R01), two wheels (~10 MB vs pyarrow), vendoring.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | fastmcp to deps; keep alias |
| `uv.lock` | Modified | regenerated |
| `mcp_server.py:55-57` | Modified | guard wording |
| `README.md` + `README_ES.md` | Modified | Install + AI/MCP fix |
| `mcp-server/spec.md` | Modified | MSP-R02/R12 |
| `tests/test_mcp_server.py` | Modified | import/wheel asserts |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Lean +10 MB | High | marginal vs pyarrow; release note |
| Pin drift | Medium | identical pin; `uv lock` |
| Stale guard | High | PEP 508 pip+uv |
| `uv tool upgrade` gap | Medium | doc re-install |
| README_ES lag | Medium | same-commit |

## Rollback Plan

Revert: move fastmcp to `optional-dependencies`, restore guard/docs/specs, `uv lock`. Alias kept → no break. Tag version via `hatch-vcs` unaffected.

## Dependencies

- Issue #100; `pyproject.toml`/`uv.lock`; `mcp-server` MSP-R02/R12.

## Success Criteria

- [ ] `uv tool install "sofer @ git+..." --force` installs fastmcp; `sofer-mcp --help` ok
- [ ] `pip install "sofer[mcp] @ git+..."` alias + `sofer @` both work
- [ ] Guard mentions pip + uv + `sofer[mcp] @ git+...`
- [ ] `README.md` shows PEP 508 `sofer @`/`sofer[mcp] @` + `uv tool` + `uvx --with`
- [ ] `README_ES.md` mirrors `README.md` same commit (§13)
- [ ] Broken `git+...[mcp]` (444) replaced + uv counterpart
- [ ] `pyproject.toml` fastmcp in `dependencies` + alias kept
- [ ] `uv.lock` regenerated (unconditional)
- [ ] `uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` green
- [ ] `mcp-server/spec.md` MSP-R02/R12 updated
