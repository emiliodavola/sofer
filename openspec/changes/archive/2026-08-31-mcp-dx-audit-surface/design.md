# Design: mcp-dx-audit-surface — MCP DX Audit — Secure core, agent-hostile surface

## Technical Approach

Surface-only refactor of `src/sofer/mcp_server.py`. No logic change to safety core: `_contained_path` 254-322, publish ladder 852-894 (`target→acknowledge_risk→acknowledge_confidential→approval_phrase` via `hmac.compare_digest`, quality before token), token ladder 573-595 (`HF_TOKEN→HF_HUB_TOKEN→HUGGING_FACE_HUB_TOKEN→get_token()`+`.env`). All 11→14 tools adopt FastMCP 3.4.7 idiom: `Annotated[T, Field(description=...)]`, `Literal["local"/"hf"]` enum, `annotations`, `output_schema`. Domain modules untouched. Implements proposal P1-P4 and spec delta 10.3-10.12.

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|----------|--------|----------|--------|
| Surface boundary | A surface-only vs B touch domain/safety | B risks containment/ladder regression | **A** — freeze 254-595, edit only signatures/descriptions/annotations/schema/instructions |
| Schema pattern | A `Annotated+Field`+`Literal` vs B manual json_schema | B drifts from FastMCP/Pydantic | **A** — `inspect.signature(FastMCP.tool)` confirms support |
| Profile/render poly | A split `sofer_profile`+`sofer_profile_all` vs B `mode` enum | B keeps branching + `all_files+config` overload; A mirrors `codebook/_all` precedent | **A — split**; remove `all_files`, batch via `*_all(config)` |
| Output rename | A clean break `output→output_file/dir` vs B description-only | B leaves dual-typed schema | **A — clean break** pre-1.0 (0.x per AGENTS.md §12); CHANGELOG only, no shim |
| Error contract | A `error_code+next` envelope primary + `sofer_auth_status` secondary vs B `sofer_auth_status` alone | B leaves `ok:false` vs `McpError` duality | **A — enriched first, auth_status second**; P2 envelope, P3 tool |
| `no_checks` | `run_checks:bool=true` normalization | `no_checks` is double-negation | **Normalize** in P4 |
| Branching | Single `feat/mcp-dx-audit-surface` vs chained PRs | Budget 5000, est ~500 | **Single branch**; chain if slice >400 lines or total >5000 |

Rejected: `sofer_build` atom — deferred to `feat/mcp-build-clarity`. Chain via `instructions`+`Requires`/`Next` first, measure, then decide.

## Data Flow

```
Agent──initialize→ build_server(root,approval_phrase) → FastMCP(instructions=phased diagram)
  ├─tools/list → 14 tools × {description(Requires/Next), inputSchema(enum+Field), annotations, outputSchema}
  ├─tools/call → _tool_execution lock → _contained_path/_load_dataset → domain fn → {ok,exit_code,output,error_code?,next?,config_errors}
  └─sofer_auth_status → _get_hf_token() probe (no network) + confidential + _APPROVAL_PHRASE → {token, next}
```

Phased diagram in `instructions` (no `prompts/list` needed):

```
Phase 0 Bootstrap [conditional: REQUIRED if greenfield — no TOML / empty [[file]]]
  init → scan ──→ Phase 1 Build: validate → prepare → codebook_all → profile_all → render_all
                    ──→ Phase 2 Publish: publish(dry_run) → STOP → publish_confirm (4-gate)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modify | Tool sigs `Annotated+Field`, `Literal` target, `output_file`/`output_dir`, `run_checks`, `annotations`+`output_schema`; add `sofer_auth_status`+`sofer_profile_all`/`sofer_render_all`; phased `instructions`; 11× `UNTRUSTED`→single `instructions`; fix `1283,1347,1430` Bootstrap wording |
| `README.md`+`README_ES.md` | Modify | Sync phased diagram same commit |
| `tests/test_mcp_schema.py` | Create | Offline asserts: descriptions, enum, no `all_files`/`no_checks`/`output`, annotations, output_schema, single `UNTRUSTED` |
| `tests/fixtures/mcp-happy-path/` | Create | Minimal TOML+CSV for offline chain |
| `CHANGELOG.md` | Modify | Breaking `output_*`/`run_checks`/`*_all` note |

## Interfaces / Contracts

**tools/list delta 11→14:** `sofer_validate`, `sofer_prepare`, `sofer_publish(local)`, `sofer_publish_confirm(hf)`, `sofer_codebook`, `sofer_codebook_all`, `sofer_profile`, `sofer_profile_all`, `sofer_render`, `sofer_render_all`, `sofer_scan_dry_run`, `sofer_scan_apply`, `sofer_init`, `sofer_auth_status`. Every param `Annotated[T, Field(description)]` non-empty; `target` `Literal`→`enum`; `output`→`output_file` (codebook single) / `output_dir` (dirs); no `all_files`/`no_checks`.

**Error envelope** (expected failures → envelope, not throw; only containment/transport throws `PathOutsideRootError`/`PublishRefusedError`):

```python
{"ok": True, "exit_code": 0, "output": str, ...}
{"ok": False, "exit_code": 1, "error_code": E, "message": str, "next": {}, "config_errors": []}
```

| `error_code` | `next` |
|--------------|--------|
| `CONFIG_ERROR` | fix config path |
| `VALIDATION_FAILED` | `sofer_validate` |
| `QUALITY_GATE_FAILED` | fix quality |
| `PUBLISH_RISK_NOT_ACKD` | `{acknowledge_risk:true}` |
| `PUBLISH_CONFIDENTIAL_NOT_ACKD` | `{acknowledge_confidential:true}` |
| `PUBLISH_APPROVAL_REQUIRED` | `{approval_phrase:"<from human>"}` |
| `PATH_OUTSIDE_ROOT` | throw |
| `TARGET_INVALID` | `{target:"local"\|"hf"}` |

```python
# FastMCP 3.4.7 pattern (non-obvious: annotations/output_schema are @tool kwargs, not docstring)
server.tool(sofer_validate, annotations={"readOnlyHint": True}, output_schema={"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]})
# param: Annotated[str, Field(description="TOML path under server root")]
# target: Annotated[Literal["local"], Field(description="...")]  # → enum
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Schema: 14 tools, descriptions, enum, no legacy params, annotations, output_schema, single `UNTRUSTED`, Bootstrap wording | `build_server()._list_tools()` offline in `tests/test_mcp_schema.py` |
| Unit | Envelope: `ok:false+error_code+next` vs throw boundary | Direct calls: bad config, `acknowledge_risk=false`, outside-root |
| Integration | Happy path `validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status` with `publish._api` mocked | `tests/fixtures/mcp-happy-path/`; assert `ok:true`, `dry_run:true` |
| Regression | No safety regression, existing tests green | `uv run pytest tests/ -q && uv run mypy src/` |

## Migration / Rollout

Phased `work-unit-commits`, `auto-forecast`, est. ~500 lines <5000 — single `feat/mcp-dx-audit-surface`:

- **P1 No-break (S)** — descriptions, annotations, `Literal` enum, `Requires`/`Next`+diagram, `UNTRUSTED` move.
- **P2 Envelope (M)** — wrap refusals → `error_code+next`; containment still throws.
- **P3 Preflight+rename (S/M)** — `sofer_auth_status` (`readOnlyHint:true`, no token leak) + `output_file`/`output_dir` clean break.
- **P4 Split (M)** — `sofer_profile_all`/`sofer_render_all`, `no_checks`→`run_checks`, remove `all_files`.

No flags/DB. Rollback = revert branch. If diff exceeds 400-line review slice, split chained PRs: P1+P2→PR#1, P3→PR#2, P4→PR#3.

## Open Questions

- [ ] Confirm `output_file` (single file) vs `output_dir` (dir) naming over uniform `output` — leaning file/dir per proposal.
- [ ] `sofer_auth_status` must read `_APPROVAL_PHRASE` at call time (yes).
