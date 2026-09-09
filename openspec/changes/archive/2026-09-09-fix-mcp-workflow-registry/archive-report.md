# Archive Report — fix-mcp-workflow-registry (PR 1)

**Archived**: 2026-09-09
**Issue**: GitHub #117 (child of epic #115)
**Branch**: `fix/117-executable-workflow`
**Scope of this archive**: PR 1 only (workflow.py + registry + spec sync).

## Summary

Ported the canonical workflow contract into the codebase as the single
authoritative registry (#117). `src/sofer/workflow.py` ships the typed
envelope layer (`WorkflowCall`, `WorkflowTemplate`, `HumanGate`,
`WorkflowMetadata`, `WorkflowResult`), the four canonical branches
(greenfield / existing_config / triage / delivery), the 14-entry
`WORKFLOW_METADATA` registry (1:1 with the registered `sofer_*` tools), and
`success_result` / `failure_result` factories. Integration with the MCP
server and CLI (envelopes, tools/list, prompts, executable-client tests,
CLI-R10 JSON) is PR 2.

## Provenance

`workflow.py` is ported from the preserved reference work
(`c4dab7f:src/sofer/workflow.py`, 551 lines, frozen as evidence for #115
slice 1, shipped verbatim with complete docstrings). The change
`fix-mcp-end-to-end-reliability` is NOT being revived — only the leaf
workflow module is integrated, per AGENTS.md rule 4 (no duplicated logic).
The reference registry's branch chains match #117's acceptance criteria
exactly (verified by the integrity tests before integration).

## Spec Sync

- **`openspec/specs/mcp-server/spec.md` — ADDED `MSP-R13`** (Authoritative
  workflow registry with executable continuations) with 8 scenarios.
- **`openspec/specs/cli/spec.md` — ADDED `CLI-R10`** (Machine-readable
  status as stable JSON) with 2 scenarios — foundation for PR 2's CLI
  parity work.

## Verification Evidence

- New `tests/test_workflow.py` (12 tests): roster matches the canonical
  tools; one entry per tool; branch tools all registered; every template
  continuation names a registered tool with arguments; greenfield chain
  init→scan_dry_run→scan_apply→validate; existing-config chain routes
  render_all→auth_status; delivery ends in typed `HumanGate` before
  `sofer_publish_confirm`; triage (codebook/profile/render) never
  advertises config-bearing publish; `select_workflow_branch` facts;
  template binding degrades to input-required when config is missing;
  success/failure envelopes are stable JSON (CLI-R10 foundation).
- Full suite: **1452 passed, 6 skipped** (was 1440 before PR 1) on
  `fix/117-executable-workflow`.
- `ruff check` clean; `ruff format --check` clean; `mypy src/` clean
  (`31 source files`); `git diff --check` clean.

## Archive Mechanics

- Change directory moved: `openspec/changes/fix-mcp-workflow-registry/` →
  `openspec/changes/archive/2026-09-09-fix-mcp-workflow-registry/`.
- PR 2 (MCP/CLI integration) will extend this archive record with the
  integration evidence before #117 is closed.

## PR 2 — Integration (2026-09-09, same archive record)

Extends this archive: the MCP server and CLI contract now consume the
registry (MSP-R13).

### What landed (src/sofer/mcp_server.py)

- `_workflow_next` / `_workflow_doc_line` / `_workflow_description` helpers;
  `_error_envelope` gains `next_call` (executable registry continuation) with
  legacy `next_hint` mapped to a new flat `hints` field; `_refusal` gains
  `tool_name`/`config_path` and builds a truthful retry (`WorkflowCall` with
  `{"config": path}`, or `input_required=("config",)` when no path).
- Every success envelope now carries `next` from the registry: validate →
  prepare → codebook_all → profile_all → render_all → auth_status →
  publish (dry_run) → typed `human_gate`; greenfield init → scan_dry_run →
  scan_apply → validate. `sofer_init` success carries `next` after
  `report_identity`.
- `sofer_auth_status`: `next` is the executable `sofer_publish` call;
  preflight hints live in `hints`.
- `_register_tools` appends `Workflow: phase=…, branch=…, next=…` to every
  tool's description (tools/list metadata from the registry).
- Missing-config / invalid-config refusals recover with a retry of the SAME
  tool (never a fabricated credential); publish_confirm risk refusal carries
  `input_required=("acknowledge_risk",)`.
- `workflow.bind_continuation` (workflow.py): binds `<config_path>` templates
  to a request, degrading to `input_required=("config",)` when absent.

### Tests

- `tests/test_mcp_server.py` — new `TestWorkflowRegistryConformance` (7):
  tools/list descriptions carry Workflow metadata; validate success next is
  executable (sofer_prepare); render_all next is sofer_auth_status;
  missing-config recovery is structured; publish dry_run ends in a typed
  human gate; **greenfield chain executed via a registered FastMCP client**
  (init → scan_dry_run → scan_apply → validate following the returned
  continuations); refusal recovery is a truthful retry of the same tool.
- Updated flat-`next` contract tests to the executable `next` + `hints`
  split (tests/test_mcp_server.py, tests/test_mcp_schema.py).
- `tests/test_workflow.py` — bind_continuation degradation tests.

### Verification

- Full suite: **1461 passed, 6 skipped** (was 1452 after PR 1).
- `ruff check` clean; `ruff format --check` clean; `mypy src/` clean
  (31 source files); `git diff --check` clean.
