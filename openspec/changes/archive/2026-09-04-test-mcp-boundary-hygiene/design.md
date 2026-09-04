# Design: test-mcp-boundary-hygiene

## Technical Approach

Test-only change closing #130: convert the 9 remaining direct registered-tool calls in `tests/test_mcp_server.py` plus the 10th (`sofer_auth_status` at `tests/test_mcp_schema.py:251`) to the public `fastmcp.Client(server)` boundary via the shared `call_tool` (conftest.py:140) and module-local `_call` helpers (PB-01, spec delta s2). Invalid Literal inputs surface as `ToolError` at the boundary through in-schema rejection — never as envelope `error_code` branches. L291's stream-restore test switches to a body-raising trigger so `_capture_output`'s `finally` restore is genuinely exercised (spec delta s6). L1210 is deleted (spec delta s5 AND clause). Zero production changes; `next` boundary visibility is asserted only where the schema declares it (`sofer_auth_status`, spec delta s7).

## Conversion mechanics — per-site table

All conversions follow the established #119 pattern (`pytest.raises(ToolError, match=...)` precedent at L1845-1878; body-raise precedent at L2635-2640).

| Site | Test | Call shape after conversion | Assertion delta |
|---|---|---|---|
| L291 | `TestStreamRestore.test_stdout_stderr_restored_after_raise` | `server = build_server(root=tmp_path)`; `pytest.raises(ToolError, match="config not found")` around `_call(server, "sofer_publish", {"config": str(tmp_path / "missing.toml")})` | `envelope["ok"] is False` → `pytest.raises(ToolError)`; stream-restore asserts (`sys.stdout is fake_out`) unchanged and now meaningful (body ran); `_make_dataset` dropped (missing.toml must not exist); `# type: ignore[arg-type]` gone |
| L1062/64 | `TestPublishDryRun.test_publish_dry_run_default_no_network` | capture `server = build_server(root=tmp_path)` (was discarded); `envelope = _call(server, "sofer_publish", {"config": str(tmp_path / "dataset.toml")}).data` | none — ok/dry_run/output unchanged |
| L1073 | `TestPublishDryRun.test_publish_hf_without_confirm_raises` | `pytest.raises(ToolError, match="Input should be 'local'")` around `_call(server, "sofer_publish", {"config": ..., "target": "hf", "dry_run": False})` | `error_code == "TARGET_INVALID"` dropped (branch unreachable at boundary); name now accurate |
| L1179 | `TestPublishTargetLadder.test_garbage_target_dry_run_false_refused_no_api` | same shape, `"target": "garbage"` | `error_code` dropped; `calls == []` + `_api` monkeypatch + HF_TOKEN setenv kept (D4/D5) |
| L1189 | `TestPublishTargetLadder.test_aws_target_dry_run_false_refused` | same shape, `"target": "aws"` | `error_code` dropped; setup kept (D5) |
| L1210 | `TestPublishTargetLadder.test_garbage_target_dry_run_ok_no_network` | **DELETED** (D3) | — |
| L1222 | `TestPublishTargetLadder.test_local_target_dry_run_false_copies_package` | `_call(server, "sofer_publish", {"config": str(...), "target": "local", "dry_run": False, "output_dir": str(deliver)}).data` | none — ok/exit_code/deliver assertions unchanged |
| L2577 | `test_xlsx_registered_validate_passes_and_idempotent` (1st scan) | `scan_env = _call(server, "sofer_scan_apply", {"config": str(child / "test.toml")}).data` (server already captured L2570) | none |
| L2591 | same test (idempotent rerun) | `scan2 = _call(server, "sofer_scan_apply", {"config": str(child / "test.toml"), "force": True}).data` | none |
| schema:251 | `TestEnvelope.test_auth_status_no_leak` | `server = build_server(root=tmp_path, approval_phrase="phrase123")` (capture); `envelope = _call(server, "sofer_auth_status", {"config": str(tmp_path / "dataset.toml")}).data` | env-hygiene asserts unchanged; ADD `assert envelope["next"]["acknowledge_risk"] is True` and `assert envelope["next"]["approval_phrase"] == "<from human>"` (deterministic given token present / confidential False / approval phrase set — mcp_server.py:1450-1457) |

## Architecture Decisions

### D1 — Convert via the shared boundary helper, not a new wrapper
**Choice**: `_call` → `call_tool` → in-process `Client(server)`.
**Alternatives considered**: per-module duplicate client code; keep direct import-and-call.
**Rationale**: the wrapper exists precisely to enforce PB-01; duplicating it would violate AGENTS.md rule 4 (no duplicated logic). `conftest.call_tool` + `mcp_payload` is the single home of the client/unwrap logic (PB-09); all three test modules already carry the module-local `_call` alias.

### D2 — L291 trigger: missing TOML → MCPToolError, not outside-root config
**Choice**: `{"config": str(tmp_path / "missing.toml")}`.
**Alternatives considered**: outside-root absolute path → `PathOutsideRootError` (needs a path outside root; win32/CI path semantics add noise).
**Rationale**: proposal DP3 — deterministic, zero path setup. Verified: `_contained_path` raises `MCPToolError("config not found: …")` when `must_exist=True` (mcp_server.py:337-338), and `sofer_publish` does NOT catch `MCPToolError` from `_load_dataset` (unlike `sofer_validate`, which converts it to a refusal envelope — mcp_server.py:705-708 vs 839-842), so the exception propagates out of the body through `_capture_output`'s `finally` and FastMCP surfaces it as `ToolError`. Boundary surfacing of body-raised `MCPToolError` subclasses is precedented (test_mcp_server.py:2635-2640, `match="outside the server root"`).

### D3 — L1210: delete, do not fold
**Choice**: delete the whole test.
**Alternatives considered**: fold the `calls == []` dry-run aspect into L1179.
**Rationale**: proposal DP1. The asserted behavior (`target="garbage", dry_run=True` → `ok:True`) is direct-call-only — the in-tool gate is `if not dry_run and target != "local"` (mcp_server.py:843), so the schema rejects `garbage` at the boundary BEFORE the body regardless of `dry_run`. Folding duplicates L1179; the `calls == []` value survives via L1179 (now strictly stronger, D4). Spec delta s5 AND clause pins the deletion; test count 1270 → 1269.

### D4 — `calls == []` semantics: in-schema rejection, not in-tool gate
**Choice**: keep the assertion at L1179; its meaning is now "the tool body provably never runs" — `publish._api` is untouched by construction, not by gate ordering.
**Alternatives considered**: drop the assertion (trivially true once the body can't run).
**Rationale**: strictly stronger guarantee (spec delta s5). The assertion doubles as a regression net: if FastMCP's validation ever loosens (e.g. `target` becomes plain `str`), the body would run, the in-tool gate would refuse with a non-raising envelope, and `pytest.raises(ToolError)` would fail loudly.

### D5 — Keep existing setup (fixtures, `_api` monkeypatches, setenvs) at converted sites
**Choice**: minimal diff; do not strip `_make_dataset`/`_prepare_package`/HF_TOKEN setenv from L1179/L1189.
**Alternatives considered**: trim dead setup from refusal tests.
**Rationale**: smallest review surface; if the schema-validation boundary ever regresses, the retained setup keeps the site a REAL offline refusal test rather than a vacuous one. Only L291 drops `_make_dataset` (its missing-file premise requires the TOML absent).

### D6 — Include the 10th call (`sofer_auth_status`)
**Choice**: convert `test_auth_status_no_leak`.
**Alternatives considered**: defer it (issue scope stated 9).
**Rationale**: proposal DP2. `sofer_auth_status` is the ONLY tool whose `output_schema` declares `next` (mcp_server.py:2117-2131 vs all other schemas) — the converted test becomes the sole boundary-level `next` assertion (spec delta s7). Trivial conversion (precedent `test_offline_happy_path` L317). No boundary-hiding direct call remains.

### D7 — Import cleanup: design CORRECTION to the proposal
**Choice**: `tests/test_mcp_server.py` import block unchanged — `sofer_publish` does NOT become F401.
**Evidence**: `test_every_tool_acquires_execution_lock` (L1907-1926) uses `sofer_publish` in a source-inspection `callables` list (L1913); `test_scan_apply_never_prompts_and_chains_scanner` (L1078-1088) keeps `sofer_scan_apply`. The proposal's "drop unused import" risk is a false alarm.
**In `tests/test_mcp_schema.py`**: the `sofer_auth_status` import (L18) DOES become F401 — L251 is the only use of the imported function (L187 is tools-dict schema inspection via `_list_tools`). Change to `from sofer.mcp_server import build_server`.

### D8 — PB-03 framing: no behavioral change, one comment-level alignment
**Choice**: `tests/test_mcp_process.py` recovery tests (TestRecoveryPublishConfirm L121-156, TestRecoveryInit L159-206) already implement the hint-VALUE contract exactly (refusal reason in boundary-visible `output` + deterministic hint VALUES replayed → asserted to reach a DIFFERENT gate or `ok:True`). Edit only the module docstring L6: "executing the documented ``next`` hints" → "executing the documented hint VALUES", so spec wording == test wording.
**Alternatives considered**: leave the docstring as-is.
**Rationale**: spec delta PB-03 leads with the hint-VALUE contract; aligning the docstring keeps the spec/test wording identical at zero behavioral risk. No code change.

## Data Flow

    test ── _call(server, name, args) ──► conftest.call_tool
       └► asyncio.run(Client(server).call_tool(name, args))
              ├─ input validation (Literal) rejects ──► ToolError raised (body never runs)
              └─ body runs under _tool_execution() + _capture_output()
                     ├─ MCPToolError propagates (finally restores streams) ──► ToolError at boundary (L291 trigger)
                     └─ envelope dict ──► mcp_payload unwrap ──► .data (plain dict asserts)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `tests/test_mcp_server.py` | Modify | 8 boundary conversions (L291/1064/1073/1179/1189/1222/2577/2591), delete L1210 test, new L291 docstring; imports unchanged (D7) |
| `tests/test_mcp_schema.py` | Modify | L243-256 conversion + `next` asserts; import L18 trims `sofer_auth_status` (D7) |
| `tests/test_mcp_process.py` | Modify (docstring only) | module docstring L6 wording (D8) |
| `openspec/changes/test-mcp-boundary-hygiene/design.md` | Create | this document |

## Interfaces / Contracts

No new interfaces. Boundary contract relied upon (pinned by #119 and this delta): FastMCP projects tool results through each tool's declared `output_schema`; invalid Literal inputs raise `ToolError` at input validation before the body runs; `MCPToolError` raised in a body surfaces as `ToolError` at the client. `sofer_auth_status`'s schema is the only one declaring `next`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Boundary | Literal rejection → ToolError (s5) | converted L1073/L1179/L1189 (`match="Input should be 'local'"`) |
| Boundary | body-raise stream restore (s6) | rewritten L291 (`match="config not found"`) |
| Boundary | `next` visibility (s7) | `test_auth_status_no_leak` extended with `next` asserts |
| Boundary | valid publish/scan envelopes | converted L1064/L1222/L2577/L2591, assertions unchanged |
| Unit | none new | no production change |

Counts: baseline 1270 passed + 2 skipped → **1269 passed + 2 skipped** (L1210 deletion).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary is introduced or modified (existing stdio tests are untouched).

## Migration / Rollout

No migration required. Rollback: single test-only commit — revert it; deleted L1210 test restorable from git history (proposal rollback plan).

## Verification Plan

1. `uv run pytest tests/ -q` → 1269 passed, 2 skipped.
2. `uv run ruff check src/ tests/` → clean (no F401; pre-commit ruff gate).
3. `uv run ruff format --check src/ tests/` → clean (apply `ruff format` to touched files if flagged).
4. `uv run mypy src/` → clean (no src changes; tests excluded by mypy config).
5. `git diff --check` → clean.
Expected changed lines: ~130-180 (additions + deletions) — 400-line budget risk **Low**; single PR, no chaining.

## Open Questions

None.