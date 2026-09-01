# Apply Progress: Registered MCP and CLI process-boundary regression suite

## Status

Phase 1 (PR 1) complete — tasks 1.1–1.5 done. Phase 2 (PR 2) complete —
tasks 2.1–2.5 done. Standard mode (`strict_tdd=false` per
`openspec/config.yaml`); Work Unit Evidence recorded below.

## Completed Tasks

### Phase 1 (PR 1)

- [x] 1.1 Add `mcp_payload(result)` Root-unwrap to `tests/conftest.py` (ported from `_unwrap`), typed (PB-09/07).
- [x] 1.2 Add `run_cli(argv, *, cwd, env=None, encoding="utf-8")` — spawns `[sys.executable, "-m", "sofer.cli", ...]` (PB-02).
- [x] 1.3 Add module-scoped `mcp_stdio_server`: one `main()` stdio spawn per module (PB-09).
- [x] 1.4 `test_mcp_server._unwrap` delegates to `mcp_payload` (D2).
- [x] 1.5 Gate: full pytest, ruff, mypy, `git diff --check`; `SOFER_TRACE.md` untouched (PB-07/08).

### Phase 2 (PR 2)

- [x] 2.1 Convert ~22 `sofer_publish_confirm` direct calls in `tests/test_mcp_server.py` to `_call(server, ...)` + unwrap (PB-01).
- [x] 2.2 Convert ~16 `sofer_init` direct calls to `_call(server, ...)` (PB-01).
- [x] 2.3 Convert remaining direct `sofer_validate` calls; drop unused imports (PB-01).
- [x] 2.4 `test_mcp_schema.py`: convert direct validate/publish_confirm calls; route `test_offline_happy_path` via `Client(server)`, keep `_api` mock + `HF_TOKEN` (PB-01/06).
- [x] 2.5 Gate: no new boundary-hiding direct calls (PB-01); count not regressed (PB-07).

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `uv run pytest tests/test_mcp_server.py -q` → **137 passed, 2 skipped**; `uv run pytest tests/test_mcp_schema.py -q` → **15 passed** (both after conversion) |
| Runtime harness command/scenario and exact result | In-process `Client(server)` boundary: `sofer_publish_confirm` no-ack refusal → envelope `{ok:False, exit_code:1, acknowledge_risk:False}` with refusal message in `output`; `target="local"` → schema `literal_error` ToolError "Input should be 'hf'" (TARGET_INVALID envelope branch is unreachable through the boundary); `sofer_init` dotdot/C:/evil → ToolError "outside the server root"; `sofer_validate` missing config → `ok:False` + `config_errors` (throwaway probe in temp dir, not committed) |
| Rollback boundary | Revert commits `354b9e9` + `cdc95f3` (or `git revert` them): delete the two test diffs — zero production surface (`src/sofer/` untouched, verified by `git diff --stat` showing only `tests/`) |

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `tests/test_mcp_server.py` | Modified | Converted 22 `sofer_publish_confirm`, 25 `sofer_init`, 1 `sofer_validate` direct calls to `_call(server, ...)` + `mcp_payload` unwrap; refusal assertions moved to boundary-visible fields; dropped `PathOutsideRootError` import |
| `tests/test_mcp_schema.py` | Modified | Added module-local `_call` (delegates unwrap to conftest `mcp_payload`); converted `test_refusal_envelope`, `test_publish_risk_envelope`, `test_offline_happy_path` through `Client(server)`; dropped unused `sofer_publish` import |
| `openspec/changes/test-mcp-cli-regression-suite/tasks.md` | Modified | Marked 2.1–2.5 `[x]` |
| `openspec/changes/test-mcp-cli-regression-suite/apply-progress.md` | Modified | Merged Phase 2 progress into this artifact (cumulative with Phase 1) |

## Deviations from Design

- **Refusal assertions moved off `error_code`/`next`**: the declared
  `output_schema` for `sofer_publish_confirm`/`sofer_validate`/`sofer_init`
  does NOT expose `error_code`, `message`, or `next` — FastMCP projects the
  tool envelope through the schema, dropping those fields at the client
  boundary. Converted tests therefore assert boundary-visible signals:
  `ok`/`exit_code`, tool-specific flags (`acknowledge_risk`,
  `confidential`), and the human-readable refusal message in `output`
  (e.g. `"acknowledge_risk=True"`, `"HF_TOKEN"`, `"approval phrase"`).
  This matches PB-01's "same envelope shape as the documented public
  contract" — the schema IS the documented contract.
- **`target`-refusal tests pin schema rejection instead of TARGET_INVALID**:
  `test_confirm_refuses_local_target`/`test_confirm_refuses_unknown_target`
  now assert `ToolError` (`literal_error`, "Input should be 'hf'") because
  the `Literal["hf"]` input schema rejects non-hf targets before the tool
  body runs; the `TARGET_INVALID` envelope branch is unreachable through
  `Client(server)`. This is a stronger boundary proof, not a coverage loss.
- **`sofer_scan_apply` direct calls retained** in
  `test_xlsx_registered_validate_passes_and_idempotent` (2 calls): PB-01
  enumerates only `sofer_publish_confirm`/`sofer_init`/`sofer_validate` for
  conversion; scan_apply was out of this PR's scope (the boundary grep in
  2.5 covers exactly the three named tools).
- **`test_auth_status_no_leak` stays direct**: `sofer_auth_status` is not
  in the PB-01 conversion list; only `test_offline_happy_path` was routed
  through the client per task 2.4.
- **Renamed 3 tests** whose names said "direct": `test_direct_call_creates_toml`
  → `test_client_call_creates_toml`, `test_user_sets_repo_id_direct` →
  `test_user_sets_repo_id_client`, `test_traversal_direct_raises` →
  `test_traversal_client_raises` (no direct calls remain, so the old names
  would mislead).

## Issues Found

- None blocking. Boundary discovery worth noting for later PRs:
  `error_code`/`message`/`next` are not part of the client-visible envelope
  for publish/init/validate — the machine-readable `next` hint is only
  visible on direct calls. PR 3's recovery-replay tests (PB-03) will need
  to assert on the boundary-visible refusal message rather than `next`.
- Pre-existing note (from PR 1): `tests/test_mcp_server.py::_make_dataset`
  and conftest's `_write_minimal_dataset` remain near-duplicates;
  refactoring is deferred out of scope (flagged in tasks).

## Remaining Tasks (later PRs in the chain)

- [ ] 3.1–3.6 Phase 3 (PR 3): `mcp-config-states/` + stdio/CWD/recovery
- [ ] 4.1–4.6 Phase 4 (PR 4): config states + handoff
- [ ] 5.1–5.5 Phase 5 (PR 5): test_cli subprocess + CI

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain on `test/mcp-cli-regression-suite`)
- Current work unit: PR 2 — direct-call → `Client(server)` conversions
- Boundary: PR 1 (conftest fixtures + `_unwrap` delegation) → this PR routes
  the three registered tools through the public boundary; planning trail
  ships with the code (repo `chore(sdd):` convention)
- Estimated review budget impact: 260 insertions + 168 deletions (428
  changed lines) across two test files — above the 400-line guard, but the
  slice is the explicitly assigned PR 2 work unit of the feature-branch
  chain; the bulk is mechanical conversion + ruff-format multi-line wrapping

## Status

10/16 tasks complete (Phases 1–2). Ready for review of PR 2; next batch = PR 3 (Phase 3).