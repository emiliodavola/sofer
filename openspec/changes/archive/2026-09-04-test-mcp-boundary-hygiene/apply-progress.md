# Apply Progress — test-mcp-boundary-hygiene

Change: `test-mcp-boundary-hygiene` (closes #130)
Branch: `fix/130-boundary-hygiene` (feature branch for PR; no push)
Mode: Standard (strict_tdd: false) · Hybrid artifact store (OpenSpec + Engram)
Date: 2026-09-04

## Status

All 15 tasks complete (Phases 1-4). Full gate green: **1269 passed, 2 skipped** (1271 collected) — exactly the design's predicted count after the L1210 deletion (baseline 1270 → 1269). Zero production changes (`src/` untouched).

## Phase 1: Conversions batch A (valid envelopes) — DONE

| Task | Site | Evidence |
|------|------|----------|
| 1.1 | `test_publish_dry_run_default_no_network` (L1064) | captured `server = build_server(root=tmp_path)`; `_call(server, "sofer_publish", {"config": ...}).data`; asserts unchanged |
| 1.2 | `test_local_target_dry_run_false_copies_package` (L1222) | `_call(server, "sofer_publish", {"config": ..., "target": "local", "dry_run": False, "output_dir": str(deliver)}).data`; asserts unchanged |
| 1.3 | `test_xlsx_registered_validate_passes_and_idempotent` (L2577+L2591) | both `sofer_scan_apply` calls → `_call(server, ..., {"config": ..., ["force": True]}).data`; asserts unchanged |

Focused run (Phase 1): `uv run pytest tests/test_mcp_server.py -q -k "test_publish_dry_run_default_no_network or test_local_target_dry_run_false_copies_package or test_xlsx_registered_validate_passes_and_idempotent"` → **3 passed, 136 deselected**.

> Note: test 1.2 required capturing `server = build_server(root=tmp_path)` — the original discarded it, and a module-level pytest fixture named `server` (test_mcp_server.py L147) would otherwise shadow the reference. Per PB-09 each test builds its own server.

## Phase 2: Conversions batch B + trigger fix — DONE

| Task | Site | Evidence |
|------|------|----------|
| 2.1 | `test_publish_hf_without_confirm_raises` (L1073) → **renamed** `test_publish_hf_target_schema_rejected` | `pytest.raises(ToolError, match="Input should be 'local'")` around `_call(..., {"target": "hf", "dry_run": False})`; `error_code` assert dropped |
| 2.2 | `test_garbage_target_dry_run_false_refused_no_api` (L1179) | same shape, `"target": "garbage"`; `calls == []` + `_api` monkeypatch + HF_TOKEN setenv KEPT (D4/D5) |
| 2.3 | `test_aws_target_dry_run_false_refused` (L1189) | same shape, `"target": "aws"`; `error_code` dropped; setup kept (D5) |
| 2.4 | `test_stdout_stderr_restored_after_raise` (L291) | `server = build_server(root=tmp_path)`; `pytest.raises(ToolError, match="config not found")` around `_call(server, "sofer_publish", {"config": str(tmp_path / "missing.toml")})`; `_make_dataset` dropped; `# type: ignore[arg-type]` gone; new docstring; stream-restore asserts unchanged |
| 2.5 | `test_garbage_target_dry_run_ok_no_network` (L1210) | **DELETED** (D3; spec s5 AND clause — not re-added) |

Focused run (Phase 2): `uv run pytest tests/test_mcp_server.py -q -k "test_publish_hf_target_schema_rejected or test_garbage_target_dry_run_false_refused_no_api or test_aws_target_dry_run_false_refused or test_stdout_stderr_restored_after_raise"` → **4 passed, 134 deselected**.

### D2 STRICT verification (L291 body-raise trigger)

Verified against `src/sofer/mcp_server.py` source before writing the conversion:

1. `_contained_path` (L282) has `must_exist: bool = True` default (L288) and raises `MCPToolError(f"{what} not found: {resolved}")` at L337-338.
2. `_load_dataset` (L488) calls `_contained_path(config_path, root=_get_root(), what="config", extensions=_CONFIG_EXTENSIONS)` (L516-518) — `must_exist` defaults True, so a missing TOML raises `MCPToolError("config not found: ...")`.
3. `sofer_publish`'s body (L839-872) calls `_load_dataset(config)` with **no try/except** — unlike `sofer_validate` (L705-708 catches `MCPToolError` → refusal envelope). The exception therefore propagates through `_capture_output`'s `finally` (L228-234 restores `sys.stdout`/`sys.stderr` to the captured originals) and out of the body.
4. Empirical: unpatched boundary call → `ToolError("Error calling tool 'sofer_publish': config not found: <path>")` — message contains `config not found` ✓.
5. `target: Annotated[Literal["local"], ...]` (L803-808) → non-`local` targets rejected in-schema before the body; the in-tool `TARGET_INVALID` gate (L843-849) is unreachable at the boundary regardless of `dry_run`, confirming D3 (L1210's asserted `garbage`+`dry_run` → `ok:True` is direct-call-only) and D4 (`calls == []` now proves the body never runs).

**Design fallback NOT needed** — the missing-TOML → `MCPToolError` trigger surfaces through the client as designed.

## Phase 3: 10th call + import trim + docstring alignment — DONE

| Task | Evidence |
|------|----------|
| 3.1 `test_auth_status_no_leak` (test_mcp_schema.py L251) | `server = build_server(root=tmp_path, approval_phrase="phrase123")`; `envelope = _call(server, "sofer_auth_status", {"config": ...}).data`; env-hygiene asserts unchanged; ADD `assert envelope["next"]["acknowledge_risk"] is True` and `assert envelope["next"]["approval_phrase"] == "<from human>"` |
| 3.2 import trim (test_mcp_schema.py L18) | `from sofer.mcp_server import build_server, sofer_auth_status` → `from sofer.mcp_server import build_server` (F401); L187 tools-dict inspection unaffected |
| 3.3 docstring (test_mcp_process.py L6) | "``next`` hints" → "hint VALUES" (D8) |

`next` shape verified against mcp_server.py L1450-1457: token present + confidential False + approval phrase set → `{"approval_phrase": "<from human>", "acknowledge_risk": True}` — deterministic, matches the design's asserts.

Focused: `uv run pytest tests/test_mcp_schema.py -q -k "test_auth_status_no_leak"` → **1 passed, 14 deselected**. `uv run ruff check tests/test_mcp_schema.py tests/test_mcp_server.py tests/test_mcp_process.py` → **All checks passed!**

## Phase 4: Final gates — DONE

| Gate | Result |
|------|--------|
| 4.1 Full suite | `uv run pytest tests/ -q` → **1269 passed, 2 skipped** (1271 collected; matches design count) |
| 4.2 Quality gates | ruff check clean · ruff format --check clean (58 files already formatted) · mypy clean (30 source files) · `git diff --check` clean |
| 4.3 Boundary proofs | `rg -n "sofer_publish\(|sofer_scan_apply\(|sofer_auth_status\(" tests/` → **0 matches** (exit 1); zero envelope `error_code` branches for invalid Literal inputs |
| 4.4 Commit | single test-only conventional commit on `fix/130-boundary-hygiene`; diff shows only `tests/` + `openspec/changes/` (no `src/`); SOFER_TRACE.md untracked, NOT staged |

## Work Unit Evidence

| Evidence | Required value |
|----------|----------------|
| Focused test command and exact result | Phase 1: 3 passed; Phase 2: 4 passed; Phase 3: 1 passed — all with `-k` selectors on `tests/test_mcp_server.py` / `tests/test_mcp_schema.py`; ruff check clean on all three touched test files |
| Runtime harness command/scenario and exact result | Full suite `uv run pytest tests/ -q` → 1269 passed, 2 skipped; boundary round-trips exercised via in-process `Client(server)` (conftest `call_tool`) for all 10 converted sites; L291 body-raise genuinely exercised `_capture_output`'s finally-restore (verified empirically: unpatched boundary call surfaces `ToolError("... config not found: ...")`) |
| Rollback boundary | Single test-only commit — revert it. Deleted L1210 test restorable from git history; `src/sofer/` untouched so no production surface. Files reverted without removing unrelated work: `tests/test_mcp_server.py`, `tests/test_mcp_schema.py`, `tests/test_mcp_process.py` |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_mcp_server.py` | Modified | 8 boundary conversions (L291/1064/1073/1179/1189/1222/2577/2591); L1210 test deleted; `test_publish_hf_without_confirm_raises` renamed `test_publish_hf_target_schema_rejected`; L291 rewritten with body-raise trigger + docstring; `import io` added; import block otherwise unchanged (D7) |
| `tests/test_mcp_schema.py` | Modified | L251 conversion + `next` asserts; import L18 trimmed to `from sofer.mcp_server import build_server` (D7) |
| `tests/test_mcp_process.py` | Modified | module docstring L6 wording only (D8) |
| `openspec/changes/test-mcp-boundary-hygiene/tasks.md` | Modified | tasks 1.1-4.4 marked `[x]` |
| `openspec/changes/test-mcp-boundary-hygiene/apply-progress.md` | Created | this document |

`git diff --stat`: 3 files, 69 insertions(+), 57 deletions(-) = 126 changed lines — within the Low budget forecast (~130-180).

## Deviations from Design

1. **L291 stream fakes: `object()` → `io.StringIO()`** (design table said "stream-restore asserts (`sys.stdout is fake_out`) unchanged"). The design's assumption that bare `object()` fakes survive a body-raise boundary call is wrong: after the tool body raises `MCPToolError`, FastMCP's server logs the error via `logger.exception("Error calling tool ...")` (fastmcp/server/server.py L1343); with no logging handlers configured, the stdlib `lastResort` handler writes to `sys.stderr` dynamically, crashing on a plain `object()` fake (`'object' object has no attribute 'write'`) and REPLACING the real error message — `match="config not found"` could never pass. Fix: file-like fakes (`io.StringIO()`, requires `import io` in the test module). The identity asserts `sys.stdout is fake_out` / `sys.stderr is fake_err` are unchanged and still prove `_capture_output`'s restore. The docstring documents the reason.
2. **None otherwise** — all 10 conversions, the L1210 deletion, the rename, the import trim (D7), and the docstring alignment (D8) match the design exactly.

## Issues Found

- None unresolved. The `object()`-fake issue above was found and fixed during apply (deviation 1).

## Remaining Tasks

- None — all tasks complete. Ready for `sdd-verify`.