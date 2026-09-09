# Tasks: fix-mcp-workflow-registry (#117)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 500–750 (workflow.py port ~550 + integration + tests) |
| 400-line budget risk | High — exceeds 400 |
| Chained PRs recommended | Yes (see units) |
| Suggested split | Unit 1 PR (workflow.py types + registry + spec sync) → Unit 2 PR (MCP/CLI integration + tests) |
| Decision needed | After design approval |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | `src/sofer/workflow.py` + registry data + base-spec sync (mcp-server MSP-R13, cli CLI-R10) + unit tests of registry integrity | PR 1 | core contract; no behavior change yet |
| 2 | mcp_server.py + cli.py integration, executable-client tests, envelope parity, prompts/instructions from registry | PR 2 | consumes Unit 1; full suite |

## Phase 1: Port the typed workflow layer (`workflow.py`)

- [ ] 1.1 Port `WorkflowCall`, `WorkflowTemplate`, `HumanGate`, `WorkflowMetadata`, `WorkflowResult` + freeze/thaw helpers from the preserved reference (`c4dab7f:src/sofer/workflow.py`) — verbatim where stable, adapted where the current envelope schema differs; add docstrings per AGENTS.md rule 2.
- [ ] 1.2 Decide/keep the four phases (bootstrap/build/publish/triage) mapped onto the canonical branches of #117; validate that phase names match existing usage (`_PHASED_INSTRUCTIONS`, envelopes).

## Phase 2: Build the registry

- [ ] 2.1 Define the registry: one entry per registered tool (`sofer_init`, `sofer_scan_dry_run`, `sofer_scan_apply`, `sofer_validate`, `sofer_prepare`, `sofer_codebook_all`, `sofer_profile_all`, `sofer_render_all`, `sofer_codebook`, `sofer_profile`, `sofer_render`, `sofer_publish`, `sofer_publish_confirm`, `sofer_auth_status`, plus read-only helpers) with phase/branch/requires/next/gate.
- [ ] 2.2 Red (unit): registry integrity tests — every registered tool has exactly one entry; every `next` names a tool that exists; every named argument is a known parameter; `<config_path>` only in config-bearing tools; `sofer_render` triage has no publish next; `sofer_render_all` next is `sofer_auth_status`; delivery ends in `human_gate` before `sofer_publish_confirm`.
- [ ] 2.3 Green: implement registry; add a helper `registry_next(tool, context)` binding templates to concrete requests (`<config_path>` → value or `input_required`).

## Phase 3: Integration with MCP server (`mcp_server.py`)

- [ ] 3.1 Red: `tools/list` test asserting descriptions carry the registry phase/branch/continuation for every tool (test against the running server, existing schema test file `tests/test_mcp_schema.py`).
- [ ] 3.2 Red: envelope tests per tool — `next` in every envelope is registry-derivable: for each accepted response, the `next` tool exists and arguments match; error envelopes carry `error_code` + `message` + executable `next` or `input_required`; missing-config, invalid-config, invalid-output, missing-identity each covered.
- [ ] 3.3 Red: **executable-client recovery test** — a registered FastMCP client follows a continuation chain: init → scan_dry_run → apply → validate in a temp root, and render_all → auth_status → publish(dry_run=true) → human_gate (client actually invokes the returned tool; signature bindings are not enough).
- [ ] 3.4 Green: integrate — replace per-tool hand-built `next_hint` blocks with registry-backed construction; wire `_PHASED_INSTRUCTIONS`, prompts, and tool descriptions to the registry; keep `error_code` envelope schema stable.
- [ ] 3.5 Ensure `sofer_publish_confirm` is only offered after the human gate; `sofer_render` triage next never config-bearing publish.

## Phase 4: CLI parity

- [ ] 4.1 Red: CLI test — machine-readable status line parses as JSON with stable keys and no Python `repr` literals (e.g. `{'ok':...}` absent).
- [ ] 4.2 Green: serialize CLI status via `WorkflowResult.to_dict()` (or a documented subset) where a machine-readable line exists; human prose unchanged.

## Phase 5: Spec sync, verification, archive

- [ ] 5.1 Sync MSP-R13 and CLI-R10 deltas into `openspec/specs/mcp-server/spec.md` and `openspec/specs/cli/spec.md`.
- [ ] 5.2 Full gates: `uv run pytest tests/ -q` (+new), `ruff check`, `ruff format --check`, `mypy src/`, `git diff --check`.
- [ ] 5.3 Archive: `archive-report.md`, move to `openspec/changes/archive/2026-09-09-fix-mcp-workflow-registry/`, commit `chore(sdd): archive fix-mcp-workflow-registry — sync MSP-R13/CLI-R10 to base`, then PR(s) → dev (follow the two-unit split; merge only with green CI and explicit user authorization).

## Out of scope reminders

- No changes to scan transactionality, containment, credentials, artifact manifest (#122), or `SOFER_TRACE.md`.