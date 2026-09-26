# Verify Report: 2026-09-25-fix-mcp-native-delegation

## Scope

Verify the unified native-delegation fidelity gate for #167 (env) and #232
(scope) on branch `fix/167-232-native-mcp-delegation` (base `dev@8d2f5eb`).

## Commands and observed results

| Gate | Command | Result |
|------|---------|--------|
| Area tests | `uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q` | **278 passed** |
| Full suite under coverage | `uv run coverage run -m pytest tests/ -q` | **1888 passed, 2 skipped** |
| Lint | `uv run ruff check src/ tests/ scripts/` | **clean** |
| Format | `uv run ruff format --check src/ tests/ scripts/` | **72 files already formatted** |
| Types (mypy) | `uv run mypy src/ scripts/` | **No issues found** |
| Types (pyright) | `uv run pyright` | **0 errors** (1 pre-existing `tomli` warning) |
| Mapping gate | `uv run python scripts/check_test_mapping.py` | **OK: test-mapping contract holds** |
| Core 100% gates | `bash scripts/check_core_coverage.sh` | **cli/scanner/prepare/publish ×100%** |
| Floor (COV-01) | `coverage report --include=src/sofer/mcp_registration.py --fail-under=90 -m` | **100%** |
| TOTAL | `uv run coverage report -m` | **93%** (≥90) |

## Scenario → test map (informational; not a `## Test Mapping` heading)

| Scenario (MCP-REG-04) | Test |
|-----------------------|------|
| Env NAMES make the native path decline | `tests/test_mcp_registration.py::TestDelegation::test_present_delegates_declines_env`; `TestNativeDelegationFidelity::test_delegate_add_declines_unfaithful_without_spawn`; `tests/test_cli.py::TestMcpNativeDelegationFidelityCli::test_add_declines_env_warns_and_file_edits` |
| Scope is forwarded when the native CLI supports it | `TestNativeDelegationFidelity::test_delegate_add_forwards_scope_to_gemini`; `test_delegate_remove_scope_gate`; `tests/test_cli.py::TestMcpNativeDelegationFidelityCli::test_add_passes_requested_scope_to_native` |
| Project scope makes the native path decline for a scope-less CLI | `TestNativeDelegationFidelity::test_delegate_add_codex_user_is_scope_less`; `test_delegate_add_declines_unfaithful_without_spawn`; `tests/test_cli.py::TestMcpNativeDelegationFidelityCli::test_add_declines_project_scope_for_codex`; `test_remove_declines_project_scope_for_codex` |
| Fidelity decline falls back and keeps the exit code | `tests/test_cli.py::TestMcpNativeDelegationFidelityCli::test_add_declines_env_warns_and_file_edits`; `test_remove_declines_project_scope_for_codex`; `tests/test_mcp_registration.py::TestDelegation::test_fail_fallback` |
| Faithful cases still delegate | `TestDelegation::test_present_delegates`; `TestNativeDelegationFidelity::test_delegate_add_forwards_scope_to_gemini`; `test_delegate_add_codex_user_is_scope_less` |
| CLI-R09: help documents native delegation fidelity | `tests/test_cli.py::TestMcpCliHelp::test_mcp_help_native_delegation_fidelity` |

## Independent verification

A read-only `general` subagent reviewed the uncommitted diff against `dev` and
was asked to falsify 8 claims. **All 8 PASS; nothing falsified.** It confirmed:
one registry-driven gate (no second copy in `cli.py`), env-present declines
without spawning for codex and gemini, gemini `--scope` argv assertions, codex
project-scope decline, warning semantics (reason labels only, no values, exit 0),
opencode/pi file-edit only, docs/specs consistency, and no out-of-scope change.
It re-ran the area tests (278 passed) and `ruff check` (clean).

Residual notes (not defects):
- The gemini `--scope` / codex no-scope premise is externally sourced
  (context7: Gemini CLI docs, Codex `mcp_cmd.rs`); in-repo tests pin the argv
  sofer *sends*, not the third-party CLI's handling.
- README wording was clarified after the review (`env` applies to both
  delegating agents; project-scope decline is codex-specific).

## Verdict

PASS. All acceptance criteria of #167 and #232 are met with real evidence:
- #167 — native delegation declines when env NAMES must be forwarded; the file
  edit persists NAMES only; no value is ever handed to a native env flag.
- #232 — gemini receives `--scope`; codex declines on `--scope project`, so a
  project request never ends in a user-only native write; a warning names the
  reason and the file edit runs.
