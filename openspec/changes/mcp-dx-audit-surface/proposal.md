# Proposal: mcp-dx-audit-surface — MCP DX Audit — Secure core, agent-hostile surface

## Intent

`tools/list` alone must teach the canonical chain. Today agents skip `scan`, miss `codebook/profile/render`, brute-force 4 publish gates.

**Bootstrap Phase 0 — conditional canonical (owner 2026-08-31):** `init→scan` REQUIRED for greenfield (no `.toml`/empty `[[file]]`). Build `validate→prepare→codebook_all→profile→render→publish(dry_run)→STOP→publish_confirm` assumes `[[file]]`. Deprecated `"Not part of canonical"` at `mcp_server.py:1283,1347,1430` MUST be fixed.

**Safety core — surface-only, non-negotiable:** 4-gate ladder (`target=="hf"`→`acknowledge_risk`→`acknowledge_confidential`→`approval_phrase` via `hmac.compare_digest`, quality before token), containment `CF-1/CF-2`, token ladder `HF_TOKEN`→`get_token()`+`.env`. Never weaken/log.

## Scope

### In Scope
- Schema: `Annotated[Field(description)]` all ~28 params; `target`→`Literal` enum; `annotations`; `output_schema` typed envelope
- Error contract (explore §4.1): `error_code`+`next` envelope primary, `sofer_auth_status` convenience second `{token:present|missing, confidential, requires_approval_phrase, next}`
- Chain affordance: `instructions` phased Bootstrap→Build→Publish + per-tool `Requires`/`Next`; 11× `UNTRUSTED` → single `instructions`
- Naming clean break pre-1.0: `output`→`output_file`/`output_dir`; `sofer_profile_all`/`sofer_render_all` split (mirrors `codebook`); `no_checks`→`run_checks`; remove `all_files`; rewrite descriptions
- Bootstrap fix + `README.md`/`README_ES.md` sync

### Out of Scope
- `sofer_build` → `feat/mcp-build-clarity` (deferred)
- Safety/transport/network/timeout changes
- Deprecated aliases shim (clean break; re-add only if consumers surface)

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `mcp-server`: schema/annotations/envelope/enum/affordance/output file-dir/split/run_checks/auth_status/Bootstrap/outputSchema

## Approach

Phased `work-unit-commits`, `auto-forecast`, budget 5000 (est. ~500).

- **P1 No-break (S):** descriptions, annotations, enum, Requires/Next+diagram, UNTRUSTED move
- **P2 Envelope (M):** `error_code`+`next`; wrap `PublishRefusedError`/`PathOutsideRootError` (transport only throws)
- **P3 Pre-flight+rename (S/M):** `sofer_auth_status`; `output_file`/`output_dir`
- **P4 Split (M):** `sofer_profile_all`/`sofer_render_all`, `run_checks`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modified | 11 `@mcp.tool` + `build_server()` + `sofer_auth_status` |
| `openspec/specs/mcp-server/spec.md` | Modified | error_code/enum/annotations/output/split/diagram/schema |
| `README.md`+`README_ES.md` | Modified | Phased diagram |
| `tests/test_mcp_schema.py` | New | Asserts descriptions/annotations/enum/schema; `SOFER_VERBOSE` stderr note |
| `pyproject.toml` | Unchanged | `fastmcp>=3.4,<4` present |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Ladder/containment regression | Low | Isolate diff `mcp_server.py:254-595`; logic unchanged |
| `output_*` break | Low | Pre-1.0 minor + CHANGELOG |
| Drift vs `feat/mcp-build-clarity` | Low | Delta only `mcp-server` |

## Rollback Plan

Revert branch before merge. No DB. Safety unchanged.

## Dependencies

- `fastmcp 3.4`, `Field`, `Literal`/`Annotated`
- `explore.md` + Engram 791 + #111 (17/17 verified)
- `feat/mcp-build-clarity` independent

## Success Criteria

- [ ] Every param has `description`; `target` enum; `annotations` correct; `outputSchema` typed
- [ ] Expected failures → `{ok:false,error_code,next}` not throw
- [ ] Chain from `tools/list` alone: diagram + `Requires`/`Next`
- [ ] `sofer_auth_status` present `readOnlyHint:true`, no token leak
- [ ] Bootstrap Phase 0 updated; `sofer_build` not introduced
- [ ] Happy path `validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status→publish_confirm` succeeds

---
*Branch: single `feat/mcp-dx-audit-surface` (500<5000). Chain only if P4 exceeds. `sdd-apply` creates PR(s) without authorize/merge; close #111 after verify. Hybrid: file + Engram `sdd/mcp-dx-audit-surface/proposal`.*
