# Exploration: test-mcp-boundary-hygiene (issue #130)

Post-merge follow-up to test-mcp-cli-regression-suite (PR #123, issue #119, archived 2026-09-02).
Closes the two residual acceptance-criteria gaps from #119. Test-only — zero production changes.

## Current State

- HEAD `e3fe857` (dev; PR #131 merged). Full suite baseline: **1270 passed, 2 skipped** (verified by running `uv run pytest tests/ -q`).
- `tests/test_mcp_server.py` still has 9 direct registered-tool calls (7× `sofer_publish` at L291, L1064, L1073, L1179, L1189, L1210, L1222; 2× `sofer_scan_apply` at L2577, L2591). Everything else routes through `_call` → conftest `call_tool` → in-process `Client(server)`.
- Live spec `openspec/specs/process-boundary/spec.md` and the archived 2026-09-02 delta are **byte-identical** (SHA256 `F166D7DD17F9DE29C5841ABD62BD75A4E8A338BB114FE9D276CBDDD10165340F`, both).
- FastMCP projects tool results through each tool's declared `output_schema` (`_register_tools`, mcp_server.py:1836-2131): undeclared keys (`error_code`/`message`/`next`) are dropped at the client boundary; invalid Literal inputs (e.g. `sofer_publish target != "local"`) raise ToolError at input validation, before the tool body runs. Precedent: `pytest.raises(ToolError, match="Input should be 'hf'")` at test_mcp_server.py:1845-1878 (converted in #119).

## Affected Areas

- `tests/test_mcp_server.py` — 9 direct calls to convert; `sofer_publish` import becomes unused (ruff F401); `sofer_scan_apply` import stays (source-inspection test L1078).
- `tests/test_mcp_schema.py` — **10th direct call discovered** (L251 `sofer_auth_status(...)`), outside the issue's stated 9; boundary precedent at L317.
- `tests/test_mcp_process.py` — recovery tests already use the hint-VALUE framing; no changes expected (optional docstring alignment).
- `openspec/specs/process-boundary/spec.md` — PB-01 + PB-03 amended via a MODIFIED delta.
- `tests/conftest.py`, `src/sofer/mcp_server.py` — read-only reference; no changes.

## Gap 1 — per-site conversion notes

| Site | Test | Through `call_tool(server, "sofer_publish", ...)` | Assertion delta |
|------|------|---------------------------------------------------|-----------------|
| L291 | TestStreamRestore.test_stdout_stderr_restored_after_raise | target="hf" rejected at INPUT validation → tool body never runs → stream swap never exercised (**vacuous trap**) | Must switch trigger to a tool-body raising path (outside-root config → PathOutsideRootError, or missing TOML → MCPToolError "not found") so `_capture_output` finally-restore is genuinely exercised; `envelope["ok"] is False` → `pytest.raises(ToolError)` |
| L1064 | test_publish_dry_run_default_no_network | clean (defaults valid; ok/dry_run/output in schema) | none |
| L1073 | test_publish_hf_without_confirm_raises | target="hf" → ToolError | error_code TARGET_INVALID assertion dropped (branch unreachable at boundary); name becomes accurate |
| L1179 | test_garbage_target_dry_run_false_refused_no_api | target="garbage" → ToolError | `calls == []` preserved (stronger: tool body never runs); error_code dropped |
| L1189 | test_aws_target_dry_run_false_refused | target="aws" → ToolError | error_code dropped |
| L1210 | test_garbage_target_dry_run_ok_no_network | target="garbage" → ToolError regardless of dry_run; asserted ok True is **direct-call-only** (gate is `not dry_run and target != "local"`) | **Cannot convert**; coverage redundant (L1064 dry-run + L1179 garbage-rejection) → delete or fold into L1179 (proposal decision) |
| L1222 | test_local_target_dry_run_false_copies_package | clean (target="local", output_dir under root) | none |
| L2577/L2591 | test_xlsx_registered_validate_passes_and_idempotent | clean via `_call(server, "sofer_scan_apply", {"config": ..., "force": ...})` (server built at L2570) | none |

**10th call (scope decision)**: `test_auth_status_no_leak` (test_mcp_schema.py:251) calls `sofer_auth_status` directly. Trivially convertible (precedent L317); `sofer_auth_status` is the only tool whose output_schema declares `next` (L2127) — the converted test becomes the sole boundary-level assertion of the `next` field. Recommend including it; explicitly deferring is also defensible.

## Gap 2 — verdict: `next` cannot be surfaced without a production change

- Mechanism: every gated tool's `output_schema` is an explicit fixed property list (`_register_tools`); none list `error_code`/`message`/`next`. FastMCP drops undeclared keys at the client boundary.
- Counter-example: `sofer_auth_status` RETURNS `next` (mcp_server.py:1466) AND its schema declares it (L2127) → `next` IS client-visible there. Proving the only reason `next` is dropped elsewhere is the schema projection.
- Surfacing `next` for publish_confirm/init/publish/scan_apply = adding it to `_register_tools` schemas = production change = out of scope ("none needed — test-only").
- **Verdict: formalize the hint-VALUE substitution in the spec as the deliberate contract.** The live PB-03 already carries the apply-time parenthetical; promote it from parenthetical to the leading contract and record the re-audit conclusion. The tests (TestRecoveryPublishConfirm / TestRecoveryInit) already implement this framing exactly.

## Spec amendment (exact wording proposed)

**PB-01 (MODIFIED)** — extend the conversion list: "Direct-call tests for `sofer_publish_confirm`, `sofer_init`, `sofer_validate`, `sofer_publish`, and `sofer_scan_apply` in `tests/test_mcp_server.py`, plus `test_offline_happy_path` in `tests/test_mcp_schema.py`, SHALL be routed through `Client(server)` via the shared `call_tool`/`_call` helper." Scenario s2 WHEN extends to all five tools; THEN gains boundary-honest semantics: "invalid Literal inputs (e.g. non-`local` targets for `sofer_publish`) SHALL surface as ToolError at the client boundary, not as envelope `error_code` branches". s4 unchanged.

**PB-03 (MODIFIED)** — requirement paragraph leads with the deliberate contract: "Recovery tests SHALL execute the hint VALUES that the production gates pin for each refusal as a second call (deterministic, documented in `src/sofer/mcp_server.py`: publish_confirm risk gate → `{"acknowledge_risk": True}`, init file-exists → `{"force": True}`, init name-empty → a non-empty name). `next` itself is NOT client-visible for these tools because the declared `output_schema`s project envelopes and do not list `next`; surfacing it would require a production schema change, outside this suite's scope — so the hint-VALUE substitution IS the deliberate recovery contract. Tests SHALL assert the replayed call reaches the intended branch — not merely that the hint is present." Scenarios already align with the tests; optionally align "documented hint arguments" → "documented hint VALUES".

## Consistency / archive pattern

Confirmed via `2026-08-31-mcp-dx-audit-surface`: the archived delta is the original change's delta (`# Delta for mcp-server`, ADDED requirements); the live `mcp-server` spec (545 lines) carries the merged result with provenance annotations; archive commits perform the live-spec sync (`a754404`, `62ebf22`). The new change's delta lives at `openspec/changes/test-mcp-boundary-hygiene/specs/process-boundary/spec.md` (`## MODIFIED Requirements` full blocks); at its own archive it supersedes PB-01/PB-03 in the live spec; the 2026-09-02 archived delta stays untouched.

## Approaches

1. **Single PR, convert all 9 (delete L1210)** — recommended. Clean, one review unit, well under budget.
   - Pros: closes the gap fully; smallest review surface; L1210 is redundant coverage.
   - Cons: one test's direct-call-only behavior (garbage+dry_run → ok True) is intentionally lost (its `calls == []` value survives via L1179).
   - Effort: Low.
2. **Convert 9 + include the 10th (`sofer_auth_status`)** — slightly larger but more consistent.
   - Pros: no known boundary-hiding direct call remains; converts the only `next`-bearing tool (boundary-level `next` assertion).
   - Cons: exceeds the issue's stated 9; needs user sign-off on scope.
   - Effort: Low.
3. **Convert only, keep L1210 as a direct-call test** — rejected: violates PB-01 s4 ("no registered tool SHALL be imported and called directly to prove boundary behavior").
   - Effort: n/a.

## Recommendation

Option 1 (single PR, all 9, delete/fold L1210), with a proposal-time decision on the 10th `sofer_auth_status` call (recommend include — Option 2). Gap 2 is spec-formalization only; no production change.

## Risks

- L291 vacuous-conversion trap (input-schema rejection skips the tool body → streams never exercised) — must pick a body-raising trigger.
- L1210 direct-call-only behavior unreproducible at the boundary — deletion decision required.
- `calls == []` semantics shift at L1179/1210 (guard moves from in-tool gate to in-schema rejection — stronger, document the reason).
- Unused `sofer_publish` import → ruff F401 if missed.
- 10th call scope question.
- Engram #918 spec artifact is stale vs the filesystem (apply-time PB-03 correction) — later phases read the FS spec.

## Ready for Proposal

Yes. Single-PR, test-only; ~85-145 changed lines (upper ~250 with the 1.25-1.7× forecast-miss factor from #119's PR 2) — 400-line budget risk **Low**; no chaining.