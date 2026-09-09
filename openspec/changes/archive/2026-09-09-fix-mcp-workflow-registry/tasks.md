# Tasks: fix-mcp-workflow-registry (#117)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 500–750 total (PR 1: ~720; PR 2: pending) |
| 400-line budget risk | High — exceeds 400 |
| Chained PRs recommended | Yes (see units) |
| Suggested split | Unit 1 PR (workflow.py + registry + spec sync) → Unit 2 PR (MCP/CLI integration + tests) |
| Decision needed | Approved 2026-09-09 (user) |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | `src/sofer/workflow.py` + registry + spec sync + integrity tests | PR 1 | ✅ DONE — 12 tests, suite 1452 passed |
| 2 | mcp_server.py + cli.py integration, executable-client tests, envelope parity, prompts/instructions from registry | PR 2 | pending |

## Phase 1: Port the typed workflow layer (`workflow.py`) — DONE

- [x] 1.1 Ported `WorkflowCall`, `WorkflowTemplate`, `HumanGate`, `WorkflowMetadata`, `WorkflowResult` + freeze/thaw helpers + `success_result`/`failure_result` from the preserved reference (`c4dab7f:src/sofer/workflow.py`, 551 lines, shipped verbatim — docstrings already complete).
- [x] 1.2 Four phases (bootstrap/build/publish/triage) map onto #117 branches; `WORKFLOW_BRANCHES` covers greenfield/existing_config/triage/delivery exactly as specified.

## Phase 2: Build the registry — DONE (PR 1 scope: registry + integrity tests)

- [x] 2.1 Registry `WORKFLOW_METADATA` (14 entries, 1:1 with the current registered `sofer_*` tools) with phase/branch/requires/next/gate — ported from reference; `sofer_render_all → sofer_auth_status`, `sofer_publish → HumanGate("STOP human approval")`, triage tools have no config-bearing next.
- [x] 2.2 Integrity tests (tests/test_workflow.py, 12): exact roster match, one entry per canonical tool, every branch tool registered, every template continuation names a registered tool with arguments, greenfield chain, render_all→auth_status, typed human gate before publish_confirm, triage never advertises publish, `select_workflow_branch` facts, template binding degrading to `input_required` on missing config, envelopes are stable JSON.
- [x] 2.3 `_template_to_call` binds `<config_path>` to concrete requests (None → None = input-required degrade). Public executable-client tests belong to PR 2.

## Phase 3: Integration with MCP server (`mcp_server.py`) — PR 2 (pending)

- [ ] 3.1 Red: `tools/list` metadata from registry (tests/test_mcp_schema.py).
- [ ] 3.2 Red: per-tool envelope `next` registry-derivable; error envelopes structured (error_code/message/next or input_required) for missing-config, invalid-config, invalid-output, missing-identity.
- [ ] 3.3 Red: executable-client recovery test — registered FastMCP client follows init→scan_dry_run→apply→validate and render_all→auth_status→publish(dry_run)→human_gate chains by invoking returned tools.
- [ ] 3.4 Green: replace per-tool `next_hint` blocks with registry-backed construction; wire prompts/instructions/tool descriptions to the registry.
- [ ] 3.5 publish_confirm only after gate; render triage never config-bearing publish.

## Phase 4: CLI parity — PR 2 (pending)

- [ ] 4.1 Red: machine-readable status parses as JSON, no `repr` literals.
- [ ] 4.2 Green: serialize via `WorkflowResult.to_dict()` where a machine-readable line exists.

## Phase 5: Spec sync, verification, archive

- [x] 5.1 MSP-R13 + CLI-R10 synced into base specs (done in PR 1).
- [x] 5.2 Gates for PR 1: full suite **1452 passed / 6 skipped**, ruff check clean, ruff format clean, mypy clean (`Success: no issues found in 31 source files`), `git diff --check` clean.
- [x] 5.3 Archive for PR 1 done here; PR 2 will re-open/re-archive with the integration evidence.

## Out of scope reminders

- No changes to scan transactionality, containment, credentials, artifact manifest (#122), or `SOFER_TRACE.md`.