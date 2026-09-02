```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:7f7b0982de7d679de20371a8ec72bcb4b00d37d31535c2a75612530aa4963135
verdict: pass
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 26/26
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:1981c0a0b634a2103d1d00b89122b729c69c4d0d48996280c42111183ca52204
build_command: uv run ruff check src/ tests/ && uv run mypy src/ scripts/ && git diff --check dev...HEAD
build_exit_code: 0
build_output_hash: sha256:f60b2867b79b4087fa0b79626b505f5c54fa6cb39c43fb18fc81ea025d4be167
```

## Verification Report

**Change**: test-mcp-cli-regression-suite
**Version**: specs/process-boundary/spec.md (PB-01…PB-09, 26 scenarios)
**Mode**: Standard (`strict_tdd=false` per `openspec/config.yaml`)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 27 (Phases 1–5: 5+5+6+6+5; per `tasks.md` and `gentle-ai sdd-status` → 27/27) |
| Tasks complete | 27 |
| Tasks incomplete | 0 |

Note: the orchestrator brief cites "20 tasks"; the authoritative `tasks.md`/`sdd-status` report **27** tasks, all `[x]` — the change is fully complete either way.

### Build & Tests Execution

**Build (lint/types/whitespace)**: ✅ Passed
```text
$ uv run ruff check src/ tests/
All checks passed!
$ uv run mypy src/ scripts/
Success: no issues found in 30 source files
$ git diff --check dev...HEAD
(no output — clean)
exit codes: 0 / 0 / 0
```

**Tests**: ✅ 1270 passed / ❌ 0 failed / ⚠️ 2 skipped (pre-existing)
```text
$ uv run pytest tests/ -q
1270 passed, 2 skipped, 13 warnings in 25.80s
$ uv run pytest tests/ --collect-only -q
1272 tests collected in 1.08s
Skips (both pre-existing, environment-only, present on dev):
  tests/test_mcp_server.py:597  — symlink/junction creation requires elevated
                                  privileges on this win32 host
  tests/test_mcp_server.py:1121 — hatchling build backend is not installed in
                                  the dev environment (CI builds the wheel)
Focused (change modules):
  tests/test_mcp_process.py -q        → 11 passed
  tests/test_cli.py::TestSubprocessBoundary + tests/test_mcp_schema.py -q → 18 passed
```

**PB-06 credential-free run**: the full suite above ran with `HF_TOKEN`, `HF_HUB_TOKEN`, and `HUGGING_FACE_HUB_TOKEN` all **absent** from the environment (verified before the run). Result: 1270 passed, 2 skipped — zero credential-dependent skips or failures.

**Coverage**: ➖ Not available (no coverage gate configured; not part of the spec).

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PB-01 | tools/list and call via in-process client | `tests/test_mcp_server.py > TestToolRoster::test_exactly_fourteen_callables` (14 callables via `Client(server)`), `::test_validate_round_trip` (documented envelope shape) | ✅ COMPLIANT |
| PB-01 | publish/init/validate through the client | Converted calls: `tests/test_mcp_server.py` `TestNetworkOffline`, `TestPublishAuthorizationLadder` (publish_confirm/init/validate via `_call(server, …)`); `tests/test_mcp_schema.py` `TestEnvelope::test_refusal_envelope`, `::test_publish_risk_envelope` | ✅ COMPLIANT |
| PB-01 | Stdio transport with clean framing | `tests/test_mcp_process.py > TestStdioFraming::test_initialize_list_call_clean_jsonrpc` (real `stdio_client`; `initialize → tools/list (14) → tools/call`; payload `json.loads` clean envelope) | ✅ COMPLIANT |
| PB-01 | No new direct-call proofs | Diff inspection: zero `+` lines call any registered tool directly (grep `^\+.*sofer_(publish|init|validate|…)\(` → none); only pre-existing `sofer_publish` ×7 + `sofer_scan_apply` ×2 direct calls remain, unchanged from `dev` and outside the spec's named conversion list | ✅ COMPLIANT |
| PB-02 | Help via subprocess | `tests/test_cli.py > TestSubprocessBoundary::test_help_exits_zero_and_lists_every_subcommand` (rc 0, all 9 subcommands in stdout) | ✅ COMPLIANT |
| PB-02 | cp1252 help on the ubuntu matrix | `tests/test_cli.py > TestSubprocessBoundary::test_help_strict_cp1252` (`PYTHONIOENCODING=cp1252`, `encoding="cp1252"`, `errors="strict"`, rc 0, **re-encodes stdout as cp1252** proving zero non-cp1252 glyphs — not a decode-only test) | ✅ COMPLIANT |
| PB-02 | Dispatch exit codes | `tests/test_cli.py > TestSubprocessBoundary::test_unknown_command_exits_2` (rc 2 + "invalid choice" in stderr) | ✅ COMPLIANT |
| PB-03 | publish_confirm replay | `tests/test_mcp_process.py > TestRecoveryPublishConfirm::test_replay_acknowledge_risk_progresses_to_approval_gate` — first call refused at risk gate (`acknowledge_risk=False`, message names hint); replayed with `acknowledge_risk=True`, token retained → refused at the **approval gate** (the literal next check after risk, message switches) — proves the replayed call progressed, not merely that the hint exists | ✅ COMPLIANT |
| PB-03 | init refusal replay | `tests/test_mcp_process.py > TestRecoveryInit::test_replay_force_past_file_exists` (file-exists → `force=True` → `ok:True`, template overwritten); `::test_replay_corrected_name_past_name_empty` (name-empty → corrected name → `ok:True`) | ✅ COMPLIANT |
| PB-04 | Empty config | `tests/test_mcp_process.py > TestConfigStates::test_empty_config_documented_result` (real `mcp-config-states/empty.toml`; `ok:False` + `config_errors` "No [[file]] entries") | ✅ COMPLIANT |
| PB-04 | Existing config | `::test_existing_config_validates_without_registration` (real `mcp-happy-path/` TOML; `ok:True`, no scan) | ✅ COMPLIANT |
| PB-04 | Greenfield bootstrap | `::test_greenfield_bootstrap_init_scan_apply_validate` (init → scan_apply → validate via client; `copied:1`, `cache/data.csv` on disk) | ✅ COMPLIANT |
| PB-04 | Triage | `::test_triage_scan_dry_run_preview_read_only` (dry-run lists candidates, `discovered:2`/`registered:1`, no `cache/` dir, TOML byte-identical) | ✅ COMPLIANT |
| PB-04 | Nested output CWD | `tests/test_mcp_process.py > TestNestedCwd::test_init_writes_under_nested_cwd` (`build_server(parent)` + `chdir(nested)`; asserts TOML+`raw/` land under **nested**, absent from parent) | ✅ COMPLIANT |
| PB-04 | Malformed config | `::test_malformed_config_refuses_with_config_errors` (real `mcp-config-states/malformed.toml`; `ok:False` + `config_errors` "Failed to read TOML") | ✅ COMPLIANT |
| PB-04 | Delivery handoff | `tests/test_mcp_process.py > TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch` (validate→prepare→codebook_all→profile_all→render_all→publish dry_run→publish_confirm; `publish._api` mocked; `upload_folder` spy proves upload branch) | ✅ COMPLIANT |
| PB-05 | CI runs the complete suite | `.github/workflows/ci.yml` test job: `uv run pytest -v` (full suite, unchanged invocation) + comment-only annotation | ✅ COMPLIANT |
| PB-05 | No focused-only gate | CI `uv run pytest -v` and dev `uv run pytest tests/ -q` both cover the complete suite (1272 collected) | ✅ COMPLIANT |
| PB-06 | Offline happy path | `tests/test_mcp_schema.py > TestHappyPath::test_offline_happy_path` (via `Client(server)`, `publish._api` monkeypatched) + `TestDeliveryHandoff` (mocked `_api`, no network) | ✅ COMPLIANT |
| PB-06 | No credentials required | Full suite run with HF_TOKEN/HF_HUB_TOKEN/HUGGING_FACE_HUB_TOKEN unset → 1270 passed, 2 skipped, no credential-dependent skips | ✅ COMPLIANT |
| PB-07 | Full suite passes | `uv run pytest tests/ -q` → 1270 passed, 2 skipped (1269 baseline + 3 = 1272 collected; count not regressed) | ✅ COMPLIANT |
| PB-07 | Lint, types, whitespace | ruff ✅, mypy src/ scripts/ ✅, `git diff --check` ✅ (all exit 0) | ✅ COMPLIANT |
| PB-08 | Untracked trace file untouched | `git status --short` → `?? SOFER_TRACE.md` (untracked, unstaged, unmodified); absent from `git diff dev...HEAD --name-only` | ✅ COMPLIANT |
| PB-09 | One server per test | Every new test calls `build_server(...)` per test (per-process `_SERVER_ROOT`/`_APPROVAL_PHRASE` globals); `server` fixture is function-scoped | ✅ COMPLIANT |
| PB-09 | Shared conftest helpers | `mcp_payload` (conftest) consumed by test_mcp_server (via delegating `_unwrap`), test_mcp_schema, test_mcp_process; `run_cli` consumed by test_cli; `mcp_stdio_server` consumed by test_mcp_process; no re-implementation anywhere | ✅ COMPLIANT |
| PB-09 | Lean process spawns | Module-scoped `mcp_stdio_server` fixture — one spawn config per module; `TestStdioFraming` is the sole stdio consumer of the new module | ✅ COMPLIANT |

**Compliance summary**: 26/26 scenarios compliant (runtime-executed for all behavioral scenarios; static diff/CI evidence for PB-01-s4, PB-05, PB-08).

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| PB-01 | ✅ Implemented | 22 publish_confirm + 25 init + 1 validate direct calls converted to `_call(server, …)`; `test_offline_happy_path` via `Client(server)`; roster/schema/round-trip through client; no new direct-call proofs added |
| PB-02 | ✅ Implemented | `TestSubprocessBoundary` (3 tests) via shared `run_cli`; `[sys.executable, "-m", "sofer.cli", …]`; strict cp1252 with re-encode assertion |
| PB-03 | ✅ Implemented | Recovery replay executes documented `next` hints (`acknowledge_risk`, `force`, corrected name) and asserts branch progression (different gate or `ok:True`) |
| PB-04 | ✅ Implemented | All 7 config-state scenarios via real fixture TOMLs (`mcp-config-states/`, `mcp-happy-path/`) and filesystem-path assertions |
| PB-05 | ✅ Implemented | CI keeps `uv run pytest -v` as complete gate; comment-only annotation |
| PB-06 | ✅ Implemented | `publish._api` monkeypatched everywhere; suite green with all HF tokens absent |
| PB-07 | ✅ Implemented | All four gates green; new helpers fully type-annotated (`mcp_payload`, `run_cli`, `McpStdioServer`) |
| PB-08 | ✅ Implemented | Trace file untracked/unstaged/absent from diff throughout |
| PB-09 | ✅ Implemented | Single home for `mcp_payload`/`run_cli`/`mcp_stdio_server`; one server per test; module-scoped spawn; `asyncio.run`, no pytest-asyncio, no new deps |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 Layout (new `test_mcp_process.py`; helpers in conftest) | ✅ Yes | Exactly as designed |
| D2 Root-unwrap (`mcp_payload` in conftest; `_unwrap` delegates) | ✅ Yes | `test_mcp_server._unwrap` is now a one-line delegation |
| D3 Conversions through `Client(server)` | ✅ Yes | With the documented boundary correction: refusal envelopes differ at the client boundary (`output_schema` drops `error_code`/`message`/`next`; non-`hf` targets surface as schema `ToolError`) — design.md D3/Open Questions updated to match reality; replay keys off boundary-visible message + documented hint values |
| D4 CLI subprocess (cp1252 cross-platform) | ✅ Yes | `PYTHONIOENCODING=cp1252` + strict decode + re-encode; no Windows CI job |
| D5 Isolation (one server per test; module-scoped stdio; `asyncio.run`) | ✅ Yes | No pytest-asyncio added |
| D6 win32 safety (`_make_link` skip pattern) | ✅ Yes (not exercised) | No link-creating test in the change; pattern retained in test_mcp_server.py for future slices |
| D7 CI comment-only annotation | ✅ Yes | `git diff` confirms comment-only; YAML still parses |

### Issues Found

**CRITICAL**: None

**WARNING**:
1. Orchestrator brief cites "20 tasks"; authoritative `tasks.md` + `gentle-ai sdd-status` report **27 tasks** (5+5+6+6+5), all complete. Metadata discrepancy only — no impact on the change's completeness (27/27).
2. Pre-existing near-duplicate fixtures `tests/test_mcp_server.py::_make_dataset` vs `conftest._write_minimal_dataset` remain (already flagged in apply-progress; deferred out of scope — violates AGENTS.md rule 4 but predates this change).

**SUGGESTION**:
1. Pre-existing direct calls of `sofer_publish` (7 sites) and `sofer_scan_apply` (2 sites) in `tests/test_mcp_server.py` remain as the only registered-tool direct calls — outside PB-01's named conversion list, but a future boundary-hygiene pass (with a spec amendment) could route them through `Client(server)` too.
2. Consider adding `SOFER_TRACE.md` to `.gitignore` so PB-08's untracked invariant holds mechanically rather than by discipline.

### Verdict

**PASS** — all 27/27 tasks complete; 26/26 spec scenarios covered by passing tests or verified static/CI evidence; all gates green (1270 passed/2 pre-existing skips, ruff, mypy, `git diff --check`); suite deterministic and credential-free; zero production drift (`src/sofer/` untouched); `SOFER_TRACE.md` untracked and absent from the diff.