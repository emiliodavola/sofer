# Apply Progress: Registered MCP and CLI process-boundary regression suite

## Status

Phase 1 (PR 1) complete — tasks 1.1–1.5 done. Phase 2 (PR 2) complete —
tasks 2.1–2.5 done. Phase 3 (PR 3) complete — tasks 3.1–3.6 done. Phase 4
(PR 4) complete — tasks 4.1–4.6 done. Phase 5 (PR 5) complete — tasks
5.1–5.5 done. Standard mode (`strict_tdd=false` per
`openspec/config.yaml`); Work Unit Evidence recorded below. All 27/27 tasks
of the change are complete.

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

### Phase 4 (PR 4)

- [x] 4.1 Empty config: validate via client → documented empty-config result (PB-04).
- [x] 4.2 Existing config: happy-path TOML validates without re-registration (PB-04).
- [x] 4.3 Greenfield + triage: init → scan_apply → validate passes; scan_dry_run lists, copies nothing, TOML unchanged (PB-04).
- [x] 4.4 Malformed: validate via client → refusal with `config_errors` (PB-04).
- [x] 4.5 Handoff: validate→prepare→codebook→profile→render→publish(dry)→publish_confirm; `_api` mocked + `HF_TOKEN`; reaches upload (PB-04/06).
- [x] 4.6 Gate: suite passes without `HF_TOKEN` (PB-06); full gates (PB-07/08).

### Phase 5 (PR 5)

- [x] 5.1 Add `TestSubprocessBoundary` to `tests/test_cli.py`: `--help` subprocess → rc 0, lists all subcommands (PB-02).
- [x] 5.2 cp1252: `PYTHONIOENCODING=cp1252` + `errors="strict"` → rc 0, strict-decodable; no non-cp1252 glyphs; win32-only skips (PB-02).
- [x] 5.3 Dispatch: unknown command subprocess → argparse rc 2 (PB-02).
- [x] 5.4 `ci.yml`: comment-only annotation on `uv run pytest -v` as complete gate (PB-05, D7).
- [x] 5.5 Final gate: full pytest (count stable) + ruff + mypy + `git diff --check`; `SOFER_TRACE.md` untracked/unstaged (PB-07/08); one spawn per module (PB-09).

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | PR 2: `uv run pytest tests/test_mcp_server.py -q` → **137 passed, 2 skipped**; `uv run pytest tests/test_mcp_schema.py -q` → **15 passed**. PR 3: `uv run pytest tests/test_mcp_process.py -q` → **5 passed** (stdio framing, nested CWD, publish risk replay, init force replay, init name replay). PR 4: `uv run pytest tests/test_mcp_process.py -q` → **11 passed** (5 Phase 3 + 6 Phase 4: empty config, existing config, greenfield bootstrap, triage preview, malformed config, delivery handoff). PR 5: `uv run pytest tests/test_cli.py::TestSubprocessBoundary -v` → **3 passed** (help lists every subcommand, cp1252 strict help, unknown command rc 2); full `uv run pytest tests/test_cli.py -q` → **82 passed** |
| Runtime harness command/scenario and exact result | PR 2: in-process `Client(server)` boundary — `sofer_publish_confirm` no-ack refusal → envelope `{ok:False, exit_code:1, acknowledge_risk:False}` with refusal message in `output`; `target="local"` → schema `literal_error` ToolError "Input should be 'hf'" (TARGET_INVALID envelope branch is unreachable through the boundary); `sofer_init` dotdot/C:/evil → ToolError "outside the server root"; `sofer_validate` missing config → `ok:False` + `config_errors` (throwaway probe in temp dir, not committed). PR 3: real stdio subprocess (`mcp_stdio_server.spawn()` → `stdio_client` → `ClientSession`) — `initialize` ok, `tools/list` = 14, `sofer_validate(config="dataset.toml")` payload `json.loads` clean envelope `{ok:True, exit_code:0, config_errors:[]}`; nested-CWD `sofer_init` with cwd unset auto-detects live CWD → TOML + `raw/` land under the nested dir, not the parent root; publish_confirm replay (`acknowledge_risk=True`, token present, approval_phrase server) fails at the APPROVAL gate ("approval phrase" message, no "acknowledge_risk=True") — the literal next check after risk — proving the risk gate accepted the acknowledgment; init replay `{"force": True}` after file-exists refusal and corrected-name replay after name-empty refusal both reach `ok:True`. PR 4: `sofer_validate` on `mcp-config-states/empty.toml` → `{ok:False, exit_code:1, output:"No [[file]] entries found in configuration.", config_errors:["No [[file]] entries found in configuration."]}`; happy-path TOML → `{ok:True, exit_code:0, config_errors:[]}` without any scan; greenfield `sofer_init(name="green-ds", user="myuser")` → `ok:True`, then `sofer_scan_apply` (`copied:1`, `cache/data.csv` written) → `sofer_validate` `ok:True`; `sofer_scan_dry_run` on `_write_minimal_dataset` + `new.csv` → `{ok:True, discovered:2, registered:1}`, output lists `-> cache/new.csv`, no `cache/` dir, TOML byte-identical; malformed TOML → `{ok:False, exit_code:1, config_errors:["Failed to read TOML: ..."]}`; handoff chain validate→prepare→codebook_all→profile_all→render_all→`publish(dry_run=True)` (`{ok:True, dry_run:True}`) → `publish_confirm(acknowledge_risk=True)` with mocked `_api` + `HF_TOKEN` → `{ok:True, acknowledge_risk:True}` and the `upload_folder` spy recorded ≥1 call (upload branch reached, offline). PR 5: real CLI subprocess (`run_cli` → `[sys.executable, "-m", "sofer.cli", ...]`) — `--help` → rc 0, stdout lists all 9 subcommands (init, scan, validate, prepare, publish, codebook, profile, render, mcp); `PYTHONIOENCODING=cp1252` + `encoding="cp1252", errors="strict"` → rc 0, stdout strict-decodable and fully cp1252-encodable (no non-cp1252 glyphs — verified by live probe BEFORE writing the test, per task 5.2); unknown command → rc 2 with "invalid choice" on stderr (argparse dispatch) |
| Rollback boundary | PR 2: revert commits `354b9e9` + `cdc95f3` (or `git revert` them). PR 3: revert commits `f5ef349` + `8d0c4f8` + `3237aee` + `6baa813` (or `git revert` them). PR 4: revert commits `3d85368` + `5e70b84` + the Phase 4 chore commit (or `git revert` them) — zero production surface (`src/sofer/` untouched, verified by `git diff --stat` showing only `tests/` + `openspec/`). PR 5: revert the Phase 5 commits (test_cli + ci.yml + chore) — zero production surface (`src/sofer/` untouched across ALL phases, verified by `git diff --stat dev...HEAD`) |

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `tests/test_mcp_server.py` | Modified | (PR 2) Converted 22 `sofer_publish_confirm`, 25 `sofer_init`, 1 `sofer_validate` direct calls to `_call(server, ...)` + `mcp_payload` unwrap; refusal assertions moved to boundary-visible fields; dropped `PathOutsideRootError` import |
| `tests/test_mcp_schema.py` | Modified | (PR 2) Added module-local `_call` (delegates unwrap to conftest `mcp_payload`); converted `test_refusal_envelope`, `test_publish_risk_envelope`, `test_offline_happy_path` through `Client(server)`; dropped unused `sofer_publish` import |
| `tests/test_mcp_process.py` | Created | (PR 3) Process-boundary module: `TestStdioFraming` (real stdio transport via shared `mcp_stdio_server` fixture — first real consumer, PB-09), `TestNestedCwd` (PB-04), `TestRecoveryPublishConfirm` + `TestRecoveryInit` (PB-03 replay of documented hints); module-local thin `_call`/`_run` adapters delegating unwrap to conftest `mcp_payload`; post-review `6baa813` strengthened `TestRecoveryPublishConfirm` to stop the replay at the approval gate and dropped the then-unused `_strip_hf_token` |
| `tests/fixtures/mcp-config-states/empty.toml` | Created | (PR 3) Valid TOML with no `[[file]]` entries (PB-04 empty-config fixture), kept out of `mcp-happy-path/` |
| `tests/fixtures/mcp-config-states/malformed.toml` | Created | (PR 3) Unparseable TOML (unclosed table header) for the PB-04 malformed-config scenario |
| `openspec/changes/test-mcp-cli-regression-suite/tasks.md` | Modified | (PR 2 + PR 3 + PR 4 + PR 5) Marked 2.1–2.5, 3.1–3.6, 4.1–4.6, and 5.1–5.5 `[x]`; added forecast note (PR 2 actual 436 lines vs ~250–350 forecast) |
| `openspec/changes/test-mcp-cli-regression-suite/design.md` | Modified | (PR 3) Corrected D3 premise + Open Questions + Data Flow recovery line: refusal envelopes DIFFER at the client boundary (`output_schema` drops `error_code`/`message`/`next`; non-`hf` targets surface as schema `ToolError`); recovery replay keys off boundary-visible refusal message + documented hint VALUES |
| `openspec/changes/test-mcp-cli-regression-suite/apply-progress.md` | Modified | (PR 2 + PR 3 + PR 4) Merged Phase 2, Phase 3, and Phase 4 progress into this artifact (cumulative with Phase 1) |
| `tests/test_mcp_process.py` | Modified | (PR 4) Added `TestConfigStates` (empty config 4.1, existing config 4.2, greenfield bootstrap 4.3, triage preview 4.3, malformed config 4.4 — all through `Client(server)`, real fixture TOMLs from `mcp-config-states/` + `mcp-happy-path/`) and `TestDeliveryHandoff` (4.5: validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→publish_confirm with `publish._api` monkeypatched, `HF_TOKEN` set, `upload_folder` spy proving the upload branch); module docstring extended to Phase 4 |
| `tests/test_cli.py` | Modified | (PR 5) Added `TestSubprocessBoundary` (PB-02): `--help` subprocess exits 0 and lists ALL 9 subcommands (5.1); `PYTHONIOENCODING=cp1252` + `encoding="cp1252"` (strict via `run_cli`) → rc 0, stdout re-encodable as cp1252 proving no non-cp1252 glyphs (5.2); unknown command → rc 2 with "invalid choice" in stderr (5.3). Reuses conftest `run_cli` (PB-09 — second real consumer after PR 1's harness probe); module docstring + import updated |
| `.github/workflows/ci.yml` | Modified | (PR 5) Comment-only annotation above the `Run tests` step: `uv run pytest -v` IS the deliberate complete-suite gate (PB-05/D7); no focused-only command may replace it. Verified comment-only via `git diff`; YAML still parses |
| `openspec/changes/test-mcp-cli-regression-suite/tasks.md` | Modified | (PR 5) Marked 5.1–5.5 `[x]` — ALL 27 tasks of the change now complete |
| `openspec/changes/test-mcp-cli-regression-suite/apply-progress.md` | Modified | (PR 5) Merged Phase 5 progress into this artifact (cumulative with Phases 1–4) |

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
- **Gate-review WARNING fixed post-review (`6baa813`)**: the original PR 3
  `TestRecoveryPublishConfirm` replay stripped the token, so the replayed call
  was stopped at the TOKEN gate — which production pins BEFORE the risk gate
  (`mcp_server.py:948`, "Token after quality gate, before acknowledgments").
  That proved a different gate only by ordering, never that
  `acknowledge_risk=True` was accepted. Strengthened: the server now carries
  `approval_phrase="s3cret"` and the token stays present, so the replayed call
  is refused at the APPROVAL gate — the literal next check AFTER the risk gate
  (`mcp_server.py:987`) — with the refusal message switching from the risk
  message to "approval phrase required". Deterministic and offline (no
  network, no real credentials; approval gate is a `build_server` param).
- **PR 3 uses conftest's `_write_minimal_dataset`** for the publish recovery
  fixture instead of a third `_make_dataset` copy (AGENTS.md rule 4 — no
  duplicated logic; the helper already lived in conftest and now has a second
  consumer).
- **PR 4 triage test reuses `_write_minimal_dataset` + `new.csv`** instead of
  re-implementing a scan fixture: `discovered:2` (registered `data.csv` +
  new `new.csv`) and `registered:1` mirror the existing
  `test_scan_dry_run_counts_and_writes_nothing` shape exactly, keeping the
  dry-run assertion meaningful (something IS registered, so "copies nothing /
  TOML unchanged" is provable against a non-trivial delta).
- **PR 4 greenfield asserts `copied` instead of `registered`**: after
  `sofer_init`, the TOML carries the template's two placeholder `[[file]]`
  entries, and `scanner.merge_entries` strips them while adding the discovered
  file — so `registered = len(merged) - before = 1 - 2 = -1`. The meaningful
  signal is `copied == 1` (the actual copy count) plus the on-disk
  `cache/data.csv` and the passing `sofer_validate`.
- **PR 4 greenfield passes `user="myuser"` to `sofer_init`**: the template's
  `YOUR_USER` placeholder trips `DatasetConfig.validate()` ("repo_id contains
  placeholder 'your_user'"), so a bare init→scan→validate chain would refuse
  at validate; passing a real user keeps the bootstrap chain green (same
  reason `test_e2e_init_move_scan_flattened` patches the placeholder TOML
  inline).
- **D6 not exercised in PR 5** (win32 skip): `TestSubprocessBoundary` is pure
  subprocess output — no links, junctions, or privilege-dependent operations —
  so the `_make_link` skip-without-privileges pattern was not needed, exactly
  as the task brief predicted. The cp1252 test is cross-platform by design
  (`PYTHONIOENCODING` + strict decode, D4), so it runs on the ubuntu CI
  matrix without any win32 branch.
- **PR 5 verified the live probe BEFORE writing the test** (task 5.2
  mandate): `sofer --help` under `PYTHONIOENCODING=cp1252` with
  `encoding="cp1252", errors="strict"` exits 0, strict-decodes, and
  re-encodes as cp1252 — the current help text contains NO non-cp1252 glyphs,
  so no test weakening was needed (no finding to report). The test's explicit
  `stdout.encode("cp1252")` re-encode assertion pins that contract so a future
  help-text glyph (em dash, arrow, check mark) fails loudly.
- **PR 5 asserts "invalid choice" in stderr** for the unknown-command test:
  argparse error messages are not localized, so the deterministic English
  `argument command: invalid choice: ...` line is stable across the CI
  matrix; the primary assertion remains `returncode == 2` (PB-02).

## Issues Found

- None blocking. Boundary discovery resolved in PR 3: `error_code`/`message`/
  `next` are not client-visible for publish/init/validate, so the
  recovery-replay tests assert on the boundary-visible refusal message and the
  documented hint VALUES (see D3 correction above) — spec PB-03 remains
  satisfiable without a spec amendment.
- PR 4 (documented deviation, non-blocking): `registered` is negative (-1)
  when scanning a freshly-`sofer_init`ed TOML because `merge_entries` strips
  the template placeholder entries before counting — the greenfield test
  asserts `copied` instead (see Deviations above).
- Pre-existing note (from PR 1): `tests/test_mcp_server.py::_make_dataset`
  and conftest's `_write_minimal_dataset` remain near-duplicates;
  refactoring is deferred out of scope (flagged in tasks).
- PR 5 (no findings): the cp1252 live probe confirmed the help text is fully
  cp1252-encodable, so no non-cp1252 glyph issue exists to report; full-suite
  count landed exactly at the forecast (1269 baseline + 3 = 1272 collected;
  1270 passed + 2 skipped).

## Remaining Tasks (later PRs in the chain)

None — ALL 27 tasks (Phases 1–5, PRs 1–5) are complete. The change is ready
for sdd-verify.

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain on `test/mcp-cli-regression-suite`)
- Current work unit: PR 5 — CLI subprocess boundary + CI annotation (final slice)
- Boundary: PR 4 (config states + delivery handoff) → this PR adds
  `TestSubprocessBoundary` to `tests/test_cli.py` (3 tests, PB-02) and the
  comment-only complete-gate annotation in `.github/workflows/ci.yml`
  (PB-05/D7); planning trail ships with the code (repo `chore(sdd):`
  convention)
- Estimated review budget impact: ~80 insertions across `tests/test_cli.py`
  (3 tests + class + import) + 6 comment lines in `ci.yml` + ~60 in the two
  openspec artifacts — well under the 400-line guard

## 4R Hardening (post-verify corrective pass)

Post-verify hardening driven by the pre-PR 4R review findings (R1/R2/R3/R4);
the change had already passed sdd-verify (PASS, 26/26 scenarios). Three
surgical fixes — tests-only (zero production surface in `src/sofer/`), no
behavior or assertion changes — re-verified with the full gate suite (count
stable). Commits `c5125f2`, `1da70aa`, `2679158`.

### Fix 1 — HF_TOKEN env hygiene (R1/R3/R4)

- **Before**: `tests/test_mcp_schema.py::test_publish_risk_envelope` set
  `os.environ["HF_TOKEN"] = "hf_test_token"` then `del os.environ["HF_TOKEN"]`
  — leak-on-failure (a failing assert skips the `del`) and a key-deletion
  side effect on the real environment.
- **After**: `monkeypatch.setenv("HF_TOKEN", "hf_test_token")` (fixture arg,
  matching every sibling test) — no leak, no `del`, no key side effect; the
  in-function `import os` was dropped. Test behavior identical.
- Commit: `c5125f2` (`test(mcp): fix HF_TOKEN env hygiene in risk envelope test`).

### Fix 2 — consolidate the triplicated `_call` helper (R2: PB-09 + AGENTS.md rule 4 + PB-07)

- **Before**: three ~12-line `_call(server, name, args)` wrappers
  (`test_mcp_server.py` pre-existing; `test_mcp_schema.py` new and UNTYPED
  with `# type: ignore[no-untyped-def]`; `test_mcp_process.py` new, typed)
  each re-implemented `Client(server)` context → `call_tool(name, args)` →
  unwrap via `mcp_payload`.
- **After**: ONE fully-typed
  `call_tool(server: Any, name: str, arguments: dict[str, Any] | None = None) -> Any`
  in `tests/conftest.py` (next to `mcp_payload`, delegating unwrap to it);
  the three module `_call`s are thin fully-typed aliases
  (`return call_tool(server, name, args)`) so ~38 call sites needed no edits.
  `test_mcp_server._unwrap` unchanged (already delegates to `mcp_payload`).
  Dropped the now-unused `fastmcp.Client` / `mcp_payload` imports.
- Commit: `1da70aa` (`test(mcp): consolidate call_tool helper in conftest`).

### Fix 3 — timeouts at subprocess/stdio boundaries (R4: CI deadlock protection)

- **Before**: `run_cli` (`subprocess.run`) had no timeout; `TestStdioFraming`
  created `ClientSession(read, write)` with no read timeout — a hung server or
  CLI would stall CI indefinitely.
- **After**: `run_cli(..., timeout: float | None = 30.0)` passed to
  `subprocess.run(..., timeout=timeout)` — NO try/except, so `TimeoutExpired`
  fails the test loudly (the desired behavior); existing call sites keep the
  30s default. `ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30))`
  — kwarg verified against installed mcp 1.29.1 (`ClientSession.__init__`
  signature checked before writing; `read_timeout_seconds` is a documented
  `timedelta | None` param).
- Commit: `2679158` (`test(mcp): add timeouts to subprocess and stdio boundaries`).

### Verification (final committed state)

| Gate | Result |
|---|---|
| Focused `pytest tests/test_mcp_server.py tests/test_mcp_schema.py tests/test_mcp_process.py tests/test_cli.py -q` | **245 passed, 2 skipped** |
| Full `pytest tests/ -q` | **1270 passed, 2 skipped** (1272 collected — count stable, no tests added/removed) |
| `ruff check src/ tests/` | **All checks passed** |
| `mypy src/ scripts/` | **Success: no issues found in 30 source files** |
| `git diff --check` | exit 0 |
| `SOFER_TRACE.md` | still untracked (`??`), never staged |
| Grep on the diff | no `os.environ["HF_TOKEN"]` set/`del` (remaining matches are deletions only); no `# type: ignore[no-untyped-def]` in the new helpers |

### Work Unit Evidence (4R hardening)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py tests/test_mcp_process.py tests/test_cli.py -q` → **245 passed, 2 skipped** |
| Runtime harness command/scenario and exact result | Full suite `uv run pytest tests/ -q` → **1270 passed, 2 skipped**: every client-boundary call (in-memory `Client(server)` and real stdio `ClientSession` with 30s read timeout) still unwraps through the shared `call_tool`/`mcp_payload`; the risk-envelope refusal still surfaces `acknowledge_risk: False` + `"acknowledge_risk=True"` in `output` with `HF_TOKEN` set via monkeypatch |
| Rollback boundary | Revert commits `c5125f2`, `1da70aa`, `2679158` (or `git revert`) — zero production surface (`src/sofer/` untouched; `git diff --stat` shows only `tests/` + this artifact) |

## Verifier response

External verifier blocked the PR chain (issue #119) with 4 blockers + 3 risks,
all diagnosed and addressed surgically in this pass:

- **Blocker 1 — spec PB-03 boundary reality**: amended PB-03 to
  boundary-observable framing — recovery tests execute the documented `next`
  hint VALUES (deterministic, pinned by the production gates) because `next`
  itself is not client-visible (`output_schema` projects envelopes), and
  assert the replayed call reaches the intended branch (Fix D). The tests
  already implemented exactly this framing; the spec now matches.
- **Blocker 2 — ruff format gate**: `uv run ruff format src/ tests/`
  reformatted the 3 files ruff flagged (`tests/conftest.py`,
  `tests/test_mcp_process.py`, `tests/test_mcp_server.py` — single-line
  `_call`/`call_tool` aliases); formatting only, no behavior change (Fix A).
- **Blocker 3 — evidence count + verify report**: task count corrected to
  27/27 (tasks.md has 27 tasks, all `[x]`) and `verify-report.md` committed
  with the batch so the evidence ships with the change (Fixes E/G).
- **Blocker 4 — CI on every branch**: `ci.yml` gained a `push` trigger on
  `branches: ['**']` — the `pull_request` `branches:` filter applies to the
  PR BASE, so chained slice branches never got CI; design.md D7 updated to
  match (Fix F).
- **Risk 2 — env hygiene**: `test_auth_status_no_leak` converted from raw
  `os.environ` set/`del` to the `monkeypatch` fixture (`setenv` +
  `delenv(..., raising=False)`); the in-function `import os` dropped (Fix B).
- **Risk 3 — upload args**: `test_handoff_pipeline_reaches_upload_branch`
  strengthened from the bare `assert upload_calls` to an exact-count +
  repo_id + staging-contract assertion (Fix C).
- **Risk 1 (4R)** — already resolved by the earlier hardening pass (R2 `_call`
  consolidation, R4 timeouts); re-verified in this batch.

## Status

27/27 tasks complete (Phases 1–5, PRs 1–5). Full suite **1270 passed,
2 skipped** (1269 baseline + 3), ruff/mypy/`git diff --check` all clean,
`SOFER_TRACE.md` untouched. Ready for sdd-verify of the whole change.
Post-verify: 4R hardening pass complete (commits `c5125f2`, `1da70aa`,
`2679158`) — full suite still **1270 passed, 2 skipped**, all gates green,
zero production surface.
Verifier response: all 4 blockers + 3 risks addressed (commits `12ef381`,
`484e63d`, `209f9a3`, `c04a99f`, `3cf6075`, `ddb4dc9`, plus this chore
commit) — full suite **1270 passed, 2 skipped**, `ruff format --check`
clean, zero production surface.