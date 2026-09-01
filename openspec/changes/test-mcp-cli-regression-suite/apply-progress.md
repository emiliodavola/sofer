# Apply Progress: Registered MCP and CLI process-boundary regression suite

## Status

Phase 1 (PR 1) complete — tasks 1.1–1.5 done. Phase 2 (PR 2) complete —
tasks 2.1–2.5 done. Phase 3 (PR 3) complete — tasks 3.1–3.6 done. Standard
mode (`strict_tdd=false` per `openspec/config.yaml`); Work Unit Evidence
recorded below.

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

### Phase 3 (PR 3)

- [x] 3.1 Create `tests/fixtures/mcp-config-states/{empty,malformed}.toml`, out of `mcp-happy-path/` (PB-04).
- [x] 3.2 Stdio framing: `initialize → tools/list (14) → tools/call`; clean JSON-RPC, no stray stdout (PB-01).
- [x] 3.3 Nested CWD: `build_server(parent)` + `chdir(nested)`; init lands under nested — assert paths (PB-04).
- [x] 3.4 Recovery: publish_confirm refusal → replay `next` → past risk gate (PB-03).
- [x] 3.5 Recovery: init refusals (file-exists/name-empty) → replay → intended branch (PB-03).
- [x] 3.6 Gate: focused `test_mcp_process.py`, then full suite + ruff + mypy + `git diff --check` (PB-07); win32 skips reuse `_make_link` (D6).

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | PR 2: `uv run pytest tests/test_mcp_server.py -q` → **137 passed, 2 skipped**; `uv run pytest tests/test_mcp_schema.py -q` → **15 passed**. PR 3: `uv run pytest tests/test_mcp_process.py -q` → **5 passed** (stdio framing, nested CWD, publish risk replay, init force replay, init name replay) |
| Runtime harness command/scenario and exact result | PR 2: in-process `Client(server)` boundary — `sofer_publish_confirm` no-ack refusal → envelope `{ok:False, exit_code:1, acknowledge_risk:False}` with refusal message in `output`; `target="local"` → schema `literal_error` ToolError "Input should be 'hf'" (TARGET_INVALID envelope branch is unreachable through the boundary); `sofer_init` dotdot/C:/evil → ToolError "outside the server root"; `sofer_validate` missing config → `ok:False` + `config_errors` (throwaway probe in temp dir, not committed). PR 3: real stdio subprocess (`mcp_stdio_server.spawn()` → `stdio_client` → `ClientSession`) — `initialize` ok, `tools/list` = 14, `sofer_validate(config="dataset.toml")` payload `json.loads` clean envelope `{ok:True, exit_code:0, config_errors:[]}`; nested-CWD `sofer_init` with cwd unset auto-detects live CWD → TOML + `raw/` land under the nested dir, not the parent root; publish_confirm replay (`acknowledge_risk=True`, token stripped) fails at the token gate ("HF_TOKEN" message, no "acknowledge_risk=True"); init replay `{"force": True}` after file-exists refusal and corrected-name replay after name-empty refusal both reach `ok:True` |
| Rollback boundary | PR 2: revert commits `354b9e9` + `cdc95f3` (or `git revert` them). PR 3: revert commits `f5ef349` + `8d0c4f8` + `3237aee` (or `git revert` them): delete the two fixture files and `tests/test_mcp_process.py` plus the chore commit — zero production surface (`src/sofer/` untouched, verified by `git diff --stat` showing only `tests/` + `openspec/`) |

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `tests/test_mcp_server.py` | Modified | (PR 2) Converted 22 `sofer_publish_confirm`, 25 `sofer_init`, 1 `sofer_validate` direct calls to `_call(server, ...)` + `mcp_payload` unwrap; refusal assertions moved to boundary-visible fields; dropped `PathOutsideRootError` import |
| `tests/test_mcp_schema.py` | Modified | (PR 2) Added module-local `_call` (delegates unwrap to conftest `mcp_payload`); converted `test_refusal_envelope`, `test_publish_risk_envelope`, `test_offline_happy_path` through `Client(server)`; dropped unused `sofer_publish` import |
| `tests/test_mcp_process.py` | Created | (PR 3) Process-boundary module: `TestStdioFraming` (real stdio transport via shared `mcp_stdio_server` fixture — first real consumer, PB-09), `TestNestedCwd` (PB-04), `TestRecoveryPublishConfirm` + `TestRecoveryInit` (PB-03 replay of documented hints); module-local thin `_call`/`_run`/`_strip_hf_token` adapters delegating unwrap to conftest `mcp_payload` |
| `tests/fixtures/mcp-config-states/empty.toml` | Created | (PR 3) Valid TOML with no `[[file]]` entries (PB-04 empty-config fixture), kept out of `mcp-happy-path/` |
| `tests/fixtures/mcp-config-states/malformed.toml` | Created | (PR 3) Unparseable TOML (unclosed table header) for the PB-04 malformed-config scenario |
| `openspec/changes/test-mcp-cli-regression-suite/tasks.md` | Modified | (PR 2 + PR 3) Marked 2.1–2.5 and 3.1–3.6 `[x]`; added forecast note (PR 2 actual 436 lines vs ~250–350 forecast) |
| `openspec/changes/test-mcp-cli-regression-suite/design.md` | Modified | (PR 3) Corrected D3 premise + Open Questions + Data Flow recovery line: refusal envelopes DIFFER at the client boundary (`output_schema` drops `error_code`/`message`/`next`; non-`hf` targets surface as schema `ToolError`); recovery replay keys off boundary-visible refusal message + documented hint VALUES |
| `openspec/changes/test-mcp-cli-regression-suite/apply-progress.md` | Modified | (PR 2 + PR 3) Merged Phase 2 and Phase 3 progress into this artifact (cumulative with Phase 1) |

## Deviations from Design

- **Refusal assertions moved off `error_code`/`next`** (PR 2): the declared
  `output_schema` for `sofer_publish_confirm`/`sofer_validate`/`sofer_init`
  does NOT expose `error_code`, `message`, or `next` — FastMCP projects the
  tool envelope through the schema, dropping those fields at the client
  boundary. Converted tests therefore assert boundary-visible signals:
  `ok`/`exit_code`, tool-specific flags (`acknowledge_risk`,
  `confidential`), and the human-readable refusal message in `output`
  (e.g. `"acknowledge_risk=True"`, `"HF_TOKEN"`, `"approval phrase"`).
  This matches PB-01's "same envelope shape as the documented public
  contract" — the schema IS the documented contract.
- **`target`-refusal tests pin schema rejection instead of TARGET_INVALID**
  (PR 2): `test_confirm_refuses_local_target`/`test_confirm_refuses_unknown_target`
  now assert `ToolError` (`literal_error`, "Input should be 'hf'") because
  the `Literal["hf"]` input schema rejects non-hf targets before the tool
  body runs; the `TARGET_INVALID` envelope branch is unreachable through
  `Client(server)`. This is a stronger boundary proof, not a coverage loss.
- **`sofer_scan_apply` direct calls retained** (PR 2): in
  `test_xlsx_registered_validate_passes_and_idempotent` (2 calls): PB-01
  enumerates only `sofer_publish_confirm`/`sofer_init`/`sofer_validate` for
  conversion; scan_apply was out of this PR's scope (the boundary grep in
  2.5 covers exactly the three named tools).
- **`test_auth_status_no_leak` stays direct** (PR 2): `sofer_auth_status` is not
  in the PB-01 conversion list; only `test_offline_happy_path` was routed
  through the client per task 2.4.
- **Renamed 3 tests** (PR 2) whose names said "direct": `test_direct_call_creates_toml`
  → `test_client_call_creates_toml`, `test_user_sets_repo_id_direct` →
  `test_user_sets_repo_id_client`, `test_traversal_direct_raises` →
  `test_traversal_client_raises` (no direct calls remain, so the old names
  would mislead).
- **design.md D3 premise corrected** (PR 3, artifact hygiene from the PR 2
  gate review): D3 originally claimed "Envelopes identical post-unwrap" —
  inaccurate. Refusal envelopes differ at the client boundary (`error_code`/
  `next` dropped by `output_schema`; `target` refusals surface as schema
  `ToolError`). design.md D3, the Open Questions section, and the Data Flow
  recovery line now state the accurate boundary behavior; PB-03 replay keys
  off the boundary-visible refusal message plus the documented `next` hint
  VALUES (risk → `{"acknowledge_risk": True}`, confidential →
  `{"acknowledge_confidential": True}`, approval → `{"approval_phrase": ...}`,
  init file-exists → `{"force": True}`, init name-empty → `{}`).
- **Forecast miss noted** (PR 3, artifact hygiene): PR 2 landed at 436 changed
  lines (260 insertions + 168 deletions) vs the ~250–350 forecast; the
  planning trail (tasks.md Review Workload Forecast) now carries a one-line
  note so future slices plan against reality.
- **D6 not exercised in PR 3**: no test in this slice creates links, so the
  `_make_link` skip-without-privileges pattern was not needed; it remains in
  `tests/test_mcp_server.py` for any later slice that needs it.
- **PR 3 uses conftest's `_write_minimal_dataset`** for the publish recovery
  fixture instead of a third `_make_dataset` copy (AGENTS.md rule 4 — no
  duplicated logic; the helper already lived in conftest and now has a second
  consumer).

## Issues Found

- None blocking. Boundary discovery resolved in PR 3: `error_code`/`message`/
  `next` are not client-visible for publish/init/validate, so the
  recovery-replay tests assert on the boundary-visible refusal message and the
  documented hint VALUES (see D3 correction above) — spec PB-03 remains
  satisfiable without a spec amendment.
- Pre-existing note (from PR 1): `tests/test_mcp_server.py::_make_dataset`
  and conftest's `_write_minimal_dataset` remain near-duplicates;
  refactoring is deferred out of scope (flagged in tasks).

## Remaining Tasks (later PRs in the chain)

- [ ] 4.1–4.6 Phase 4 (PR 4): config states + handoff
- [ ] 5.1–5.5 Phase 5 (PR 5): test_cli subprocess + CI

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain on `test/mcp-cli-regression-suite`)
- Current work unit: PR 3 — `mcp-config-states/` fixtures + stdio/CWD/recovery
- Boundary: PR 2 (direct-call → `Client(server)` conversions) → this PR adds
  the process-boundary module (`tests/test_mcp_process.py`, 5 tests) plus the
  Phase 4 config-state fixtures and the D3/forecast artifact corrections;
  planning trail ships with the code (repo `chore(sdd):` convention)
- Estimated review budget impact: 225 insertions + 4 deletions (229 changed
  lines) across two new fixture files, `tests/test_mcp_process.py`, and the
  three openspec artifacts — comfortably under the 400-line guard

## Status

13/16 tasks complete (Phases 1–3). Ready for review of PR 3; next batch = PR 4 (Phase 4).