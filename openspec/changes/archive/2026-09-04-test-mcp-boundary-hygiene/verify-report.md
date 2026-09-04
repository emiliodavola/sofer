```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:904c6abd3e0f4fa0c9c16e7c4b695edf5d9105aa87215d1454d69ebb76f700ed
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 9/9
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:0066e4a8f4e7da5cc3c8ea4b9f1e203b5945245bf73fe28176803dc13b414253
build_command: uv run mypy src/ scripts/
build_exit_code: 0
build_output_hash: sha256:94e0905153fa10da2ccd027bdbee83bd76edc8e5f1b196900a71cfab8c96c653
```

## Verification Report

**Change**: test-mcp-boundary-hygiene
**Version**: spec delta (process-boundary, MODIFIED PB-01 + PB-03)
**Mode**: Standard (strict_tdd: false) · Hybrid artifact store
**Branch**: fix/130-boundary-hygiene @ a5253ad (base e3fe857)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 15 |
| Tasks complete | 15 |
| Tasks incomplete | 0 |

(apply-progress prose count corrected to 15 in the post-archive audit pass; tasks.md has 15 checkboxes across Phases 1-4, all `[x]`. No unchecked task.)

### Build & Tests Execution
**Build (type-check)**: ✅ Passed
```text
uv run ruff check src/ tests/ scripts/  → All checks passed! (exit 0)
uv run ruff format --check src/ tests/  → 58 files already formatted (exit 0)
uv run mypy src/ scripts/               → Success: no issues found in 30 source files (exit 0)
git diff --check                        → clean (exit 0)
```

**Tests**: ✅ 1269 passed / ❌ 0 failed / ⚠️ 2 skipped
```text
uv run pytest tests/ -q
1269 passed, 2 skipped, 13 warnings in 36.43s
(exit 0; warnings are pre-existing DeprecationWarnings in tests/test_codebook.py, unrelated)
```

**Coverage**: ➖ Not available (no coverage gate configured; not required by this change)

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PB-01 | s1 tools/list + call via in-process client (14 callables, envelope) | `tests/test_mcp_schema.py > TestToolCount::test_fourteen_tools` + `TestHappyPath::test_offline_happy_path` (client-boundary) | ✅ COMPLIANT |
| PB-01 | s2 Seven publish/scan_apply conversions (L1064/1073/1179/1189/1222/2577/2591) | `TestPublishDryRun::test_publish_dry_run_default_no_network`, `::test_publish_hf_target_schema_rejected`, `TestPublishTargetLadder::test_garbage_target_dry_run_false_refused_no_api`, `::test_aws_target_dry_run_false_refused`, `::test_local_target_dry_run_false_copies_package`, `TestInitXlsxIntegration::test_xlsx_registered_validate_passes_and_idempotent` — all via `_call(server, ...)` → `Client(server)` | ✅ COMPLIANT |
| PB-01 | s3 Stdio transport with clean framing | `tests/test_mcp_server.py > TestStdioSmoke` (unchanged, stdio subprocess tests) | ✅ COMPLIANT |
| PB-01 | s4 No remaining direct-call proofs | `rg -n "sofer_publish(\|sofer_scan_apply(\|sofer_auth_status(" tests/` → 0 matches (exit 1); only string refs (`_call(server, "sofer_...")`) + source-inspection refs (`inspect.getsource(sofer_scan_apply)`, callables list L1915-1925) remain | ✅ COMPLIANT |
| PB-01 | s5 Invalid Literal target rejected before body (ToolError, not error_code; body never runs; L1210 not re-added) | `test_publish_hf_target_schema_rejected` / `test_garbage_target_dry_run_false_refused_no_api` / `test_aws_target_dry_run_false_refused` — all `pytest.raises(ToolError, match="Input should be 'local'")`; L1179 keeps `calls == []`; `test_garbage_target_dry_run_ok_no_network` deleted (absent from collect) | ✅ COMPLIANT |
| PB-01 | s6 Stream-restore conversion exercises the tool body (body raise, not target validation) | `TestStreamRestore::test_stdout_stderr_restored_after_raise` — `pytest.raises(ToolError, match="config not found")` around `_call(server, "sofer_publish", {"config": <missing.toml>})`; `sys.stdout is fake_out` / `sys.stderr is fake_err` asserts retained | ✅ COMPLIANT |
| PB-01 | s7 auth_status routes via boundary and exposes next | `tests/test_mcp_schema.py > TestEnvelope::test_auth_status_no_leak` — `_call(server, "sofer_auth_status", ...)`; env-hygiene asserts unchanged; ADDED `envelope["next"]["acknowledge_risk"] is True` and `envelope["next"]["approval_phrase"] == "<from human>"` | ✅ COMPLIANT |
| PB-03 | s1 publish_confirm replay reaches a DIFFERENT gate | `tests/test_mcp_process.py > TestRecoveryPublishConfirm::test_replay_acknowledge_risk_progresses_to_approval_gate` — first call refused at risk gate (`"acknowledge_risk=True" in output`), replay `{"acknowledge_risk": True}` (token present) refused at approval gate (`"approval phrase" in output.lower()`, risk msg absent) | ✅ COMPLIANT |
| PB-03 | s2 init refusal replay reaches different gate or ok:True | `TestRecoveryInit::test_replay_force_past_file_exists` (file-exists → `{"force": True}` → ok:True, template overwritten) + `::test_replay_corrected_name_past_name_empty` (name-empty → non-empty name → ok:True) | ✅ COMPLIANT |

**Compliance summary**: 9/9 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| L291 body-raise trigger genuinely exercises `_capture_output` finally-restore | ✅ Implemented | `sofer_publish` (mcp_server.py L839-840) calls `_load_dataset` with NO try/except (unlike `sofer_validate` L703-708); `_contained_path` L337-338 raises `MCPToolError("config not found: …")` with `must_exist=True`; exception propagates through `_capture_output`'s finally (L228-234) → FastMCP `ToolError` at client. Verified in source. |
| L1210 deletion sound | ✅ Implemented | `sofer_publish` in-tool `TARGET_INVALID` gate (L843-849) is `if not dry_run and target != "local"` — direct-call-only; `target: Literal["local"]` (L803-808) rejects `garbage` in-schema before the body regardless of `dry_run`. Deleted test absent from collect. Replacement = in-schema ToolError tests (s5). |
| 10th call (`sofer_auth_status`) preserves env-hygiene + next | ✅ Implemented | `sofer_auth_status` (L1414-1468) is the ONLY tool whose `output_schema` declares `next` (L2127; all other 14 output_schema blocks lack it). Deterministic `next_hint` (L1450-1457): token present + non-confidential + approval set → `{"approval_phrase": "<from human>", "acknowledge_risk": True}` — matches the added asserts exactly. |
| PB-03 hint-VALUE contract == test behavior (no drift) | ✅ Implemented | Gate order in `sofer_publish_confirm` verified: target (L925) → quality (L933) → token (L949) → risk (L959, msg "requires acknowledge_risk=True") → confidential (L973) → approval (L987, msg "approval phrase required"). Replay with token present passes risk, refused at approval — exactly the spec's "NEXT check after the risk gate". Test docstrings quote the gate ordering. |
| Zero production drift | ✅ Implemented | `git diff e3fe857...HEAD -- src/` empty; working tree clean vs HEAD except untracked SOFER_TRACE.md (not staged). |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 shared `_call` → `call_tool` → `Client(server)` | ✅ Yes | all 10 conversions use the module-local `_call` delegating to conftest `call_tool`/`mcp_payload` |
| D2 L291 trigger = missing TOML → MCPToolError | ✅ Yes | `match="config not found"`; `_make_dataset` dropped; `# type: ignore[arg-type]` gone |
| D3 L1210 delete, do not fold | ✅ Yes | test gone; count 1270 → 1269 confirmed |
| D4 `calls == []` = in-schema rejection proof | ✅ Yes | kept at L1179 with `_api` monkeypatch + HF_TOKEN |
| D5 keep existing setup at converted sites | ✅ Yes | minimal diff; only L291 drops `_make_dataset` (required by missing-file premise) |
| D6 include 10th call (`sofer_auth_status`) | ✅ Yes | converted + `next` asserts |
| D7 import trim only in test_mcp_schema.py | ✅ Yes | `from sofer.mcp_server import build_server` (F401 fixed); test_mcp_server.py imports kept (source-inspection uses) |
| D8 PB-03 docstring alignment only | ✅ Yes | test_mcp_process.py L6: "``next`` hints" → "hint VALUES" |
| Deviation 1 (apply): `object()` → `io.StringIO()` fakes at L291 | ✅ Accepted | documented in apply-progress; required because FastMCP logs the body error to stderr post-raise (stdlib lastResort handler) — bare `object()` would crash the write and mask `match="config not found"`. Identity asserts unchanged. |

### Issues Found
**CRITICAL**: None
**WARNING**: None
**SUGGESTION**:
1. apply-progress.md task count corrected to 15 to match tasks.md's 15 checkboxes (Phases 1-4, all `[x]`). Resolved in the post-archive audit pass.
2. `SOFER_TRACE.md` is untracked in the working tree. It is intentionally not staged (apply-progress 4.4), but consider adding it to `.gitignore` or deleting before PR.

### Verdict
PASS — all 9 spec scenarios (7 PB-01 + 2 PB-03) covered by passing boundary tests; zero production changes; all gates green (1269 passed, 2 skipped; ruff/mypy/git-diff-check clean); L291 body-raise trigger and L1210 deletion verified sound against source.