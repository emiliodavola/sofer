# Delta for process-boundary

## MODIFIED Requirements

### Requirement: Registered MCP tools via public boundary (PB-01)

The suite SHALL exercise registered MCP tools through `fastmcp.Client(server)` (in-process) or the real stdio transport, and SHALL NOT rely on imported tool functions alone. Direct-call tests for `sofer_publish_confirm`, `sofer_init`, `sofer_validate`, `sofer_publish`, and `sofer_scan_apply` in `tests/test_mcp_server.py` — plus `test_offline_happy_path` and `test_auth_status_no_leak` in `tests/test_mcp_schema.py` — SHALL be routed through `Client(server)` via the shared `call_tool`/`_call` helper. The suite SHALL verify `tools/list`, JSON-Schema generation, envelopes, and a `tools/call` round-trip. Invalid Literal inputs (e.g. non-`local` `sofer_publish` targets) SHALL surface as `ToolError` at the client boundary through in-schema rejection, NOT as envelope `error_code` branches. New tests SHALL NOT add boundary-hiding direct calls for registered tools.
(Previously: conversion list named only `sofer_publish_confirm`/`sofer_init`/`sofer_validate`; invalid inputs were asserted via envelope `error_code` branches.)

#### Scenario: tools/list and call via in-process client

- GIVEN `build_server()` and an in-process `Client(server)`
- WHEN `tools/list` and one `tools/call` execute
- THEN 14 callables SHALL be listed and the call SHALL return the documented envelope

#### Scenario: Seven publish/scan_apply conversions through the client

- GIVEN the seven conversion sites in `tests/test_mcp_server.py` (`test_publish_dry_run_default_no_network`, `test_publish_hf_target_schema_rejected`, `test_garbage_target_dry_run_false_refused_no_api`, `test_aws_target_dry_run_false_refused`, `test_local_target_dry_run_false_copies_package`, and `test_xlsx_registered_validate_passes_and_idempotent` covering the two `sofer_scan_apply` sites)
- WHEN each runs via `_call(server, "sofer_publish"|"sofer_scan_apply", {...})` through `Client(server)`
- THEN valid-input conversions (dry-run plan `test_publish_dry_run_default_no_network`, local copy `test_local_target_dry_run_false_copies_package`, scan registration `test_xlsx_registered_validate_passes_and_idempotent`) SHALL return the documented envelope shape

#### Scenario: Stdio transport with clean framing

- GIVEN the server spawned as a subprocess
- WHEN `initialize → tools/list → tools/call` run
- THEN every response SHALL be valid JSON-RPC with no stray stdout bytes

#### Scenario: No remaining direct-call proofs

- GIVEN the converted test suite
- WHEN direct-call sites are enumerated across `tests/test_mcp_server.py` and `tests/test_mcp_schema.py`
- THEN zero registered tool SHALL be imported and called directly — every registered-tool call SHALL go through `Client(server)` or stdio

#### Scenario: Invalid Literal target rejected before the tool body

- GIVEN `sofer_publish` called via `Client(server)` with `target` outside the `"local"` Literal (`"hf"`, `"garbage"`, `"aws"`)
- WHEN the call executes
- THEN the request SHALL be rejected in-schema at input validation and SHALL surface as `ToolError` at the boundary — not an envelope `error_code` branch — and the tool body SHALL NOT run (`test_garbage_target_dry_run_false_refused_no_api`'s `calls == []` is preserved; the guard moved from the in-tool TARGET_INVALID gate to in-schema rejection)
- AND the deleted `test_garbage_target_dry_run_ok_no_network` direct-call-only test (`garbage` + `dry_run` → `ok:True`) SHALL NOT be re-added — its boundary-visible replacement is this in-schema rejection, which holds regardless of `dry_run`

#### Scenario: Stream-restore conversion exercises the tool body

- GIVEN `TestStreamRestore.test_stdout_stderr_restored_after_raise` routed through `Client(server)`
- WHEN `sofer_publish` raises INSIDE the tool body (missing TOML → `MCPToolError`), not via `target="hf"` which input validation rejects before the body
- THEN `pytest.raises(ToolError)` SHALL pass AND stdout/stderr SHALL be restored, exercising `_capture_output`'s stream swap

#### Scenario: auth_status routes via the boundary and exposes next

- GIVEN `test_auth_status_no_leak` (`tests/test_mcp_schema.py`) converted to `Client(server)`
- WHEN `sofer_auth_status` runs via the boundary
- THEN the call SHALL return the documented envelope INCLUDING `next` — the only tool whose `output_schema` declares it — making this the sole boundary-level `next` assertion

### Requirement: Recovery replay executes returned calls (PB-03)

Recovery tests SHALL key off the deterministic hint VALUES that the production gates pin for each refusal, plus the boundary-visible `output` message, and SHALL execute the hinted arguments as a second call. `next` itself is NOT client-visible for `sofer_publish_confirm`/`sofer_init` because the declared `output_schema`s project envelopes and do not list `next` (re-audited: `sofer_auth_status` is the only tool whose schema declares `next`, proving the projection is the cause); surfacing `next` would require a production schema change, outside this suite's scope — the hint-VALUE substitution IS the deliberate recovery contract. Replayed calls SHALL be asserted to reach a DIFFERENT gate than the refusal, or `ok:True` — not merely that the hint is present.
(Previously: framed as "executes the documented hint arguments" with the boundary projection as a parenthetical correction.)

#### Scenario: publish_confirm replay

- GIVEN `sofer_publish_confirm` refused at the risk gate (`ok:False`; the boundary-visible `output` message states `acknowledge_risk=True` is required)
- WHEN the documented hint VALUE `{"acknowledge_risk": True}` is replayed as a second call with the token still present
- THEN the call SHALL be refused at the approval gate — the NEXT check after the risk gate — proving the risk gate accepted the acknowledgment

#### Scenario: init refusal replay

- GIVEN `sofer_init` returning a boundary-visible refusal (`config_errors`/`output` state the required correction: file-exists → replay `{"force": True}`; name-empty → replay a non-empty name)
- WHEN the documented hint VALUES are replayed
- THEN the intended branch SHALL be reached (a different gate or `ok:True`)