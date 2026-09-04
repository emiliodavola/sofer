# Proposal: test-mcp-boundary-hygiene

## Intent

Closes #130: finish #119's residual PB-01 conversion list (9 direct registered-tool calls in `tests/test_mcp_server.py` → public `Client(server)` boundary via the shared `call_tool`/`_call` helper) and formalize PB-03's hint-VALUE replay framing after the Gap-2 audit proved `next` is not boundary-visible without a production schema change. Test-only; zero production changes.

## Scope

### In Scope
- Convert 7× `sofer_publish` (L291, L1064, L1073, L1179, L1189, L1210, L1222) + 2× `sofer_scan_apply` (L2577, L2591) in `tests/test_mcp_server.py`.
- 10th call `sofer_auth_status` (`tests/test_mcp_schema.py:251`) — recommended include (justified in Decision Points).
- L291 trigger fix (body-raising path); L1210 delete; drop now-unused `sofer_publish` import (ruff F401; `sofer_scan_apply` import stays for the source-inspection test).
- MODIFIED `process-boundary` spec delta (PB-01 conversion list + boundary-honest ToolError semantics; PB-03 hint-VALUE contract).

### Out of Scope
- Production `src/sofer/` changes (`next` added to `output_schema`s — proven required for boundary visibility; `sofer_auth_status`'s schema is the counter-example).
- Network publish; SOFER_TRACE.md (PB-08); other #115 items; archived 2026-09-02 delta (stays untouched).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `process-boundary`: PB-01 conversion list extended to `sofer_publish` + `sofer_scan_apply` (s2 gains boundary-honest ToolError semantics); PB-03 reworded to lead with the hint-VALUE contract and record the `next` re-audit conclusion.

## Approach

- Convert each site to `_call(server, "sofer_publish", {...}).data`; capture `server = build_server(...)` where currently discarded (L1062).
- L291: `target="hf"` is rejected at input validation (conversion would be vacuous — stream swap never exercised) — switch to a tool-body raising trigger: missing TOML → `MCPToolError` (deterministic; alternative: outside-root config → `PathOutsideRootError`); assert `pytest.raises(ToolError)`.
- L1073/L1179/L1189: drop envelope `error_code` assertions → `pytest.raises(ToolError)`; L1179 `calls == []` preserved (stronger: tool body never runs).
- Spec delta at `openspec/changes/test-mcp-boundary-hygiene/specs/process-boundary/spec.md` (`## MODIFIED Requirements` full blocks, unchanged scenarios preserved).

## Decision Points

| # | Decision | Recommendation | Tradeoff |
|---|----------|----------------|----------|
| 1 | L1210 delete vs fold into L1179 | **Delete** | Asserted behavior (garbage+dry_run → ok True) is direct-call-only, unreproducible at the boundary; coverage redundant (L1064 dry-run + L1179 garbage rejection). Folding duplicates L1179; `calls == []` value survives via L1179. |
| 2 | 10th call include vs strictly-9 | **Include** | Widens issue scope, but `sofer_auth_status` is the ONLY tool whose schema declares `next` → converted test becomes the sole boundary-level `next` assertion; trivial (precedent L317); no boundary-hiding direct call remains. |
| 3 | L291 body-raising trigger | **Missing TOML → MCPToolError** | Deterministic, no path setup; both options exercise `_capture_output`'s finally-restore equally. |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `tests/test_mcp_server.py` | Modified | 9 conversions, L1210 delete, import cleanup |
| `tests/test_mcp_schema.py` | Modified | L251 auth_status via boundary |
| `openspec/changes/…/specs/process-boundary/spec.md` | New | MODIFIED PB-01 + PB-03 |
| `tests/test_mcp_process.py` | Minimal | Optional docstring alignment (hint VALUES) |
| `tests/conftest.py`, `src/sofer/mcp_server.py` | None | Read-only reference |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| L291 vacuous conversion (schema rejection skips tool body) | Med | Body-raising trigger chosen in this proposal |
| `calls == []` semantics shift (in-schema rejection, not in-tool gate) | Med | Document reason in design; assertion is strictly stronger |
| Missed F401 (`sofer_publish` import) | Low | Same-commit removal; ruff gate |
| 10th-call scope rejection | Low | Justification above; deferral is defensible |

## Rollback Plan

Single test-only PR — revert the commit. Deleted L1210 test restorable from git history if needed. Spec delta supersedes PB-01/PB-03 only at its own archive; no production surface.

## Dependencies

None. Forecast ~85-145 changed lines (upper ~250 with #119's 1.25-1.7× miss factor); 400-line budget risk Low; single PR, no chaining.

## Success Criteria

- [ ] No direct registered-tool calls remain in `tests/test_mcp_server.py`; `test_auth_status_no_leak` routes via the boundary.
- [ ] `uv run pytest tests/ -q` passes (1270 baseline → net 1269 after L1210 delete, 2 skipped).
- [ ] `uv run ruff check src/ tests/`, `uv run mypy src/`, `git diff --check` pass.
- [ ] PB-01/PB-03 delta applied; invalid Literal inputs surface as ToolError, not envelope `error_code` branches.