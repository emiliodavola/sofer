# Tasks: test-mcp-boundary-hygiene

Test-only change closing #130: 9+1 direct registered-tool calls → `Client(server)` boundary via `_call`; L291 body-raising trigger fix; L1210 deletion; PB-03 docstring alignment. Zero production changes.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~130-180 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main (not needed) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All conversions + trigger fix + 10th call + docstring + gates | PR 1 | Single test-only PR on `dev`; tests included |

## Phase 1: Conversions batch A (valid envelopes)

- [x] 1.1 L1064 `test_publish_dry_run_default_no_network` (`tests/test_mcp_server.py`): capture `server = build_server(root=tmp_path)`; `envelope = _call(server, "sofer_publish", {"config": str(tmp_path / "dataset.toml")}).data`; asserts unchanged.
- [x] 1.2 L1222 `test_local_target_dry_run_false_copies_package`: `_call(server, "sofer_publish", {"config": ..., "target": "local", "dry_run": False, "output_dir": str(deliver)}).data`; asserts unchanged.
- [x] 1.3 L2577+L2591 `test_xlsx_registered_validate_passes_and_idempotent`: both `sofer_scan_apply` calls → `_call(server, ..., {"config": str(child / "test.toml")[, "force": True]}).data`; asserts unchanged.

Evidence 1.1-1.3: targeted pytest on each converted test passes.

## Phase 2: Conversions batch B + trigger fix

- [x] 2.1 L1073 `test_publish_hf_without_confirm_raises` (renamed `test_publish_hf_target_schema_rejected`): `pytest.raises(ToolError, match="Input should be 'local'")` around `_call(server, "sofer_publish", {..., "target": "hf", "dry_run": False})`; drop `error_code` assert; rename test.
- [x] 2.2 L1179 `test_garbage_target_dry_run_false_refused_no_api`: same shape, `"target": "garbage"`; drop `error_code`; KEEP `calls == []` + `_api` monkeypatch + HF_TOKEN setenv (D4/D5).
- [x] 2.3 L1189 `test_aws_target_dry_run_false_refused`: same shape, `"target": "aws"`; drop `error_code`; keep setup (D5).
- [x] 2.4 L291 `test_stdout_stderr_restored_after_raise`: `server = build_server(root=tmp_path)`; `pytest.raises(ToolError, match="config not found")` around `_call(server, "sofer_publish", {"config": str(tmp_path / "missing.toml")})`; drop `_make_dataset` + `# type: ignore[arg-type]`; stream-restore asserts unchanged; update docstring.
- [x] 2.5 L1210: DELETE `test_garbage_target_dry_run_ok_no_network` (D3; spec s5 AND clause — do NOT re-add).

Evidence 2.1-2.5: targeted pytest passes; L291 finally-restore genuinely exercised; count 1270 → 1269.

## Phase 3: 10th call + import trim + docstring alignment

- [x] 3.1 `tests/test_mcp_schema.py` L251 `test_auth_status_no_leak`: capture `server = build_server(root=tmp_path, approval_phrase="phrase123")`; `envelope = _call(server, "sofer_auth_status", {"config": str(tmp_path / "dataset.toml")}).data`; env-hygiene asserts unchanged; ADD `next` asserts (`acknowledge_risk is True`, `approval_phrase == "<from human>"`).
- [x] 3.2 `tests/test_mcp_schema.py` L18 import: `sofer_auth_status` now F401 (L251 sole use) → `from sofer.mcp_server import build_server`; L187 tools-dict inspection unaffected. Evidence: `uv run ruff check tests/test_mcp_schema.py` clean.
- [x] 3.3 `tests/test_mcp_process.py` module docstring L6: "``next`` hints" → "hint VALUES" (D8; no code change).

Evidence 3.1/3.3: targeted pytest passes; docstring diff only.

## Phase 4: Final gates

- [x] 4.1 Full suite: `uv run pytest tests/ -q` → 1269 passed, 2 skipped.
- [x] 4.2 Quality gates: `uv run ruff check src/ tests/` + `uv run ruff format --check src/ tests/` (format touched files if flagged) + `uv run mypy src/` + `git diff --check` all clean.
- [x] 4.3 Boundary proofs: grep `tests/` — zero direct calls of imported registered tools; zero envelope `error_code` branches for invalid Literal inputs (PB-01 "No remaining direct-call proofs").
- [x] 4.4 Commit: single test-only conventional commit on the feature branch; `git diff --stat` shows only `tests/` + `openspec/changes/` (no `src/`); pre-commit hooks pass.