# Apply Progress: fix/dataset-identity-context — Slice 1 / PR 1 (Phase 1 tasks 1.1-1.4)

**Change**: fix-dataset-identity-context
**Branch**: fix/116-dataset-identity-context
**Mode**: Standard (strict_tdd false)
**Date**: 2026-09-04
**Delivery**: auto-forecast / feature-branch-chain — PR 1 base = tracker `fix/116-dataset-identity-context`

## Work Units

| Unit | Tasks | Commit | Notes |
|------|-------|--------|-------|
| A | 1.1 | 51d2ddc feat(context): add execution_context identity contract | New module: DatasetIdentity (frozen, derived config_path, from_parts), validate_identity (INIT-05 matrix, first error "name must be non-empty"), resolve_dataset_root (3 modes per D5), report_identity, IdentityResolutionError (names `cwd=<dataset dir>`), `_USER_RE`; stdlib + `model._PLACEHOLDERS` only |
| B | 1.2, 1.4 | 720a992 feat(model): add discovery_root bound to from_toml | `from_toml(path, discovery_root=None)` → `config.reload(base_dir, stop_at=discovery_root)`; docstring notes TC-05 bound; TC-05 bound tests in test_model.py (pytree fixture) |
| C | 1.3 | 94a5dc9 test(context): unit matrix for identity validation and resolution | tests/test_execution_context.py: validate_identity / resolve_dataset_root / report_identity / DatasetIdentity unit matrix |
| D | 1.5 (Finding 1) | 10e7eb8 fix(model): only pass stop_at to config.reload when discovery_root is set | Conditional reload: `stop_at` keyword passed only when a bound is given; unbounded CLI path keeps byte-identical `reload(base_dir)` call shape |
| E | 1.6 (S2) | 429a061 test(context): cover mode (b) expanduser and root-equality cells | +2 mode (b) unit tests: `~` expanduser step, `cwd == root` accepted equality case |

## Completed Tasks

- [x] 1.1 Create `src/sofer/execution_context.py` — module docstring, `DatasetIdentity` frozen dataclass (config_path derived property, from_parts classmethod), `validate_identity` → list[str] (INIT-05 matrix, first message exactly "name must be non-empty"), `resolve_dataset_root` 3 modes (no-bound CLI / inline containment / fail-closed strict-descendant naming cwd), `report_identity`, `IdentityResolutionError`, `_USER_RE`; imports stdlib + `model._PLACEHOLDERS` only; no mcp_server imports (D5)
- [x] 1.2 `model.py:from_toml` gains `discovery_root: Path | None = None` → `config.reload(base_dir, stop_at=discovery_root)`; docstring notes the bound (TC-05)
- [x] 1.3 `tests/test_execution_context.py` unit matrix (28 tests) — validate_identity (valid→[]; None/""/"   " name+user; placeholders YOUR_USER/Your_User/your-username/YOUR_ORG; a/b, a\b; C:/evil via ntpath.splitdrive; ./..; a/../b; quotes; newline/tab/NUL/DEL; leading/trailing whitespace; user regex rejects user.name/user name, accepts user-org/user_org; name placeholder NOT banned); resolve_dataset_root (no-bound live; no-bound rejects cwd; strict-descendant inside; root==live fails closed; outside fails closed; message names `pass cwd="<dataset dir>"`; explicit-cwd relative/absolute contained; escape; traversal); report_identity/from_parts invariants (config_path == dataset_root/name.toml, absolute, frozen)
- [x] 1.4 `tests/test_model.py` TC-05 bound tests (3 tests, pytree + restore_tool_config) — at-or-below applies (250), above-root blocked (defaults, NOT 999), omitted bound stays unbounded (250 from above-root pyproject)
- [x] 1.5 Gate-review correction (Finding 1, CRITICAL): `from_toml` previously called `config.reload(base_dir, stop_at=discovery_root)` UNCONDITIONALLY — the TC-04 spy (`def counting_reload(start=None)`, tests/test_config.py:353) accepts no keywords, so the CLI path raised TypeError → exit 1 → `test_exactly_one_phase1_reload_per_invocation` failed. Fixed production-side: `if discovery_root is not None: config.reload(base_dir, stop_at=discovery_root) else: config.reload(base_dir)` — CLI call shape byte-identical to before, bound semantics preserved. No test_config.py churn.
- [x] 1.6 Gate-review suggestion S2: added mode (b) matrix cells — `expanduser` (`~`) step (monkeypatched USERPROFILE/HOME to tmp_path) and the accepted `cwd == root` equality case (contained by `is_relative_to`, contrast with mode (c) strict-descendant).

## Gate Review Corrections (2026-09-04)

**Finding 1 (CRITICAL — fixed, commit 10e7eb8)**: unconditional `stop_at` keyword broke the TC-04 reload spy. Root cause confirmed at tests/test_config.py:353 (`def counting_reload(start=None)`). Fixed with a production-side conditional in `from_toml`; verified the previously-failing test passes (`test_exactly_one_phase1_reload_per_invocation` → 1 passed).

**S2 (addressed, commit 429a061)**: +2 mode (b) unit tests — `~` expansion before absolutizing, and `cwd == root` accepted (containment, not strict-descendant).

**S3 (noted — deferred, no code change)**: `validate_identity` bans only leading/trailing whitespace per INIT-05 wording; interior-space names (`"my dataset"`) are currently accepted. Behavior kept contract-faithful in this slice; the CLI layer (Slice 3) may decide whether to tighten the validation contract. Recorded as a known decision, not a defect.

## Re-verified Gates (post-correction)

| Command | Result |
|---------|--------|
| uv run pytest tests/ -q (branch) | 1318 passed, 2 skipped, 0 failed |
| uv run pytest tests/ -q (dev baseline worktree) | 1269 passed, 2 skipped — delta exactly +49 new tests, 0 regressions |
| uv run pytest tests/test_execution_context.py tests/test_model.py -q | 89 passed |
| uv run pytest tests/test_config.py::TestTc04CliReloadHooks::test_exactly_one_phase1_reload_per_invocation -q | 1 passed |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| src/sofer/execution_context.py | Created | Identity contract module (262 LOC): DatasetIdentity, validate_identity, resolve_dataset_root, report_identity, IdentityResolutionError, _USER_RE, _CONTROL_CHARS_RE |
| src/sofer/model.py | Modified | `from_toml(cls, path, discovery_root=None)`; `config.reload(base_dir, stop_at=discovery_root)`; docstring notes TC-05 |
| tests/test_execution_context.py | Created | Unit matrix (197 LOC, 28 tests) |
| tests/test_model.py | Modified | +3 TC-05 bound tests (TestFromTomlDiscoveryRoot) |

## Verification (Slice 1 gate)

| Command | Result |
|---------|--------|
| uv run pytest tests/test_execution_context.py tests/test_model.py -q | 87 passed |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |

Full suite intentionally NOT run (later slices re-baseline; per-slice gate only).

## Deviations from Design

None — implementation matches design.md D1-D5, D8, TC-05 testing rows, and the Interfaces/Contracts section. Note: mode (b) of `resolve_dataset_root` raises `IdentityResolutionError` (not `PathOutsideRootError`) per D5 — it is unit-matrix-only (S7); the MCP str-branch keeps `_contained_path`.

## Issues Found

- LSP flags `tomli` import in model.py as unresolved — pre-existing conditional Python 3.10 fallback import, not introduced by this slice; mypy ignores it (`ignore_missing_imports`).
- `object.__setattr__` bypasses the frozen-dataclass `__setattr__` override — the frozen test uses `setattr()` instead (routes through the override and raises FrozenInstanceError).
- Gate review Finding 1 (CRITICAL, fixed in 10e7eb8): unconditional `stop_at` keyword in `from_toml` broke the TC-04 reload spy (tests/test_config.py:353 accepts no keywords) — see Gate Review Corrections section above.

## Remaining Tasks

Phase 2 (Slice 2 / PR 2): tasks 2.1-2.8 — MCP adapter rework, boundary/schema tests, sweep.

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain), PR 1 of 4
- Current work unit: Slice 1 — Phase 1 tasks 1.1-1.6 (incl. gate corrections)
- Boundary: tracker `fix/116-dataset-identity-context` → PR 1 (base = tracker); PR 2 bases on PR 1
- Estimated review budget impact: 5 commits, ~550 added lines (production 270 + tests 280) — within the slice budget; later slices carry the ~43-site sweep

## Status

6/6 tasks complete (Slice 1, incl. gate corrections). Ready for next slice (PR 2) — MCP adapter (tasks 2.1-2.8).
---

# Apply Progress: fix/dataset-identity-context — Slice 2 / PR 2 (Phase 2 tasks 2.1-2.8)

**Change**: fix-dataset-identity-context
**Branch**: fix/116-dataset-identity-context
**Mode**: Standard (strict_tdd false)
**Date**: 2026-09-04
**Delivery**: auto-forecast / feature-branch-chain — PR 2 base = PR 1 (branch head 5ba842c..429a061)

## Work Units

| Unit | Tasks | Commit | Notes |
|------|-------|--------|-------|
| A | 2.1, 2.2 | 5ba842c fix(mcp): enforce identity validation and fail-closed cwd in sofer_init | sofer_init reworked validate → resolve → write: `validate_identity(name, user)` FIRST → `_refusal(errors)` (CONFIG_ERROR, `next: {}`, config_errors — matches the 10.3 envelope rule); cwd=None → `resolve_dataset_root(None, live_cwd=Path.cwd().resolve(), server_root=_get_root())` strict-descendant, `IdentityResolutionError` → envelope refusal naming cwd (S8, `next: {}`), NO write; cwd=str keeps `_contained_path(cwd, root=_get_root(), must_exist=False)` → `PathOutsideRootError` propagates as ToolError (D5 — the two error contracts pinned by INIT-02); placeholder fallback deleted (`user_val = user.strip()` + `assert user is not None`); Field descriptions (L1662/L1668) and docstrings updated (no "YOUR_USER placeholder" / "falls back to the server root"); success envelopes (dry-run+move, dry-run-only, real) + `output_schema` carry absolute `config_path`/`dataset_root` via `report_identity` (PB-03 same change; `required` stays `["ok","exit_code","output"]`) |
| B | 2.3 | 30bf478 fix(mcp): bound config discovery via from_toml discovery_root | `_bound_discovery` definition (L457-471) + 4 call sites deleted; `discovery_root=_get_root()` added at the 4 `from_toml` sites (`_load_dataset` L520, `sofer_profile_all` L1245, `sofer_render_all` L1367, `sofer_auth_status` L1433) per MSP-R10 |
| C | 2.4 | 920c771 fix(mcp): anchor relative output overrides to config dir | 6 config-bearing sites `root=_get_root()` → `root=cfg._base_dir` (prepare/publish/publish_confirm/codebook_all/profile_all/render_all); 3 single-file sites → `root=data_path.parent` (codebook, profile) / `root=package_path.parent` (render); `_validate_output_targets(cfg, root=_get_root())` unchanged |
| D | 2.5, 2.6 (+ 2.7/2.8 test_mcp_server sweep) | c3b81bd test(mcp): identity envelope, schema projection, and boundary flips | schema test (2.5: `config_path`/`dataset_root` string props, NOT in `required`); envelope-identity assert on success (INIT-03); `test_default_user_placeholder` repurposed → `test_missing_user_refused_before_write` + new `test_placeholder_user_refused_before_write` (INIT-05: no user / YOUR_USER → refusal, NO TOML, NO raw/); 4 new unsafe-name refusals (`a/../b`, quotes, newline, control char); 4 traversal tests flipped ToolError → envelope refusal (validate-first bans separators/drives before containment); `test_cwd_none_back_compat` → `test_cwd_none_fails_closed`; `test_auto_cwd_outside_fallback` → `test_auto_cwd_outside_fails_closed`; L2422-2429/L2641-2646 KEEP ToolError (sweep adds user before the cwd branch — D5 reconciliation); new MSP-R10 anchoring test (`sofer_prepare` `output_dir="build"` → `<root>/proj/build`, NOT `<root>/build`); region A/B/C sweep adds `user="testuser"` + explicit `cwd` to every call; template asserts → `user="testuser"` (L2157/2170-2172/2300-2302). NOTE: 2.6 flips and 2.7/2.8 sweep are interleaved in the same test functions/hunks (e.g. `test_creates_toml_and_raw` carries both the INIT-03 assert and the user+cwd sweep; `test_cwd_outside_via_mcp_schema_rejected` mixes the sweep with the new MSP-R10 class) — committed together; a line-level split would distort the diff |
| E | 2.7/2.8 process portion (pulled from 4.2) | ed1649c test(mcp): sweep sofer_init call sites for user and explicit cwd | test_mcp_process.py 7 sites (L113/170/174/181/195/203/262): user+cwd added (TestNestedCwd keeps cwd=None + chdir — the strict-descendant auto path), TestRecoveryInit template flips `user="YOUR_USER"` → `user="testuser"`, greenfield gains explicit cwd. PULLED FORWARD from Slice 4 task 4.2: the production change (validate-first + fail-closed cwd) breaks these 7 call sites and this slice's full-suite gate requires all-green; the 4.1 parent-root fixture and 4.3 TestParentRootIdentity remain Slice 4 work (task 4.2 stays unchecked — Slice 4 verifies the sweep is in place and owns the remainder) |
| F | — (style) | 064239b style(test): collapse over-split sofer_init call lines | ruff format --check correction on test_mcp_server.py (3 collapse sites) after c3b81bd |

## Completed Tasks

- [x] 2.1 Rework `sofer_init` validate → resolve → write: `validate_identity` → `_refusal(CONFIG_ERROR)`; cwd=None strict-descendant via `resolve_dataset_root` → envelope refusal naming cwd (`next: {}` per S8); str-cwd keeps `_contained_path` → `PathOutsideRootError`; placeholder fallback L1727 deleted; Field descriptions/docstrings updated (L1662/1668/1674/1687)
- [x] 2.2 PB-03 same change: `config_path`/`dataset_root` (absolute strings via `report_identity`) in the 3 success envelopes (L1795/1809/1828) AND `output_schema` (2 string props, `required` unchanged); refusals carry none
- [x] 2.3 `_bound_discovery` def + 4 call sites deleted; `discovery_root=_get_root()` at the 4 `from_toml` sites (L520/1245/1367/1433) per MSP-R10
- [x] 2.4 Re-anchored relative outputs: 6 config-bearing sites `root=cfg._base_dir` (L775/851/1006/1114/1265/1387); 3 single-file sites `root=data_path.parent`/`root=package_path.parent` (L1070/1177/1319); `_validate_output_targets(cfg, root=_get_root())` unchanged
- [x] 2.5 test_mcp_schema.py: `sofer_init` output_schema declares `config_path`/`dataset_root` string props, NOT in `required` (MSP-R03, PB-03)
- [x] 2.6 Boundary tests: envelope-identity assert (INIT-03); missing-user + placeholder-user refusals (INIT-05, no TOML/raw); 4 unsafe-name refusals (`a/../b`, quotes, newline, control char); 4 traversal flips ToolError → envelope; `test_cwd_none_back_compat` → `test_cwd_none_fails_closed`; `test_auto_cwd_outside_fallback` → `test_auto_cwd_outside_fails_closed`; L2422-2429/L2641-2646 keep ToolError; new MSP-R10 anchoring test (`proj/build`, not `root/build`)
- [x] 2.7 Sweep region A (L2154-2263) + B (L2265-2410): `user="testuser"` + explicit `cwd` on every call; template asserts → `user="testuser"` (L2157/2170-2172/2300-2302)
- [x] 2.8 Sweep region C (L2410-2646): user+cwd added (L2576 already correct — untouched); containment expectations kept

## Work Unit Evidence

| Work unit | Focused test command and exact result | Runtime harness command/scenario and exact result | Rollback boundary |
|-----------|----------------------------------------|---------------------------------------------------|-------------------|
| A (2.1+2.2) | `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` → 158 passed, 2 skipped (final, after D/E landed) | In-process `build_server` + `Client(server)` smoke: success envelope carries absolute config_path/dataset_root; missing user / cwd=None / `../evil` → ok:False refusals, no write | Revert commits 5ba842c..064239b — restores old back-compat init, envelope/schema, flips |
| B (2.3) | same focused suite (B alone is behavior-neutral; no test churn) | N/A — pure adapter edit; MSP-R10 bound proven by existing TC-05 tests + new anchoring test | Revert 30bf478 — restores `_bound_discovery` |
| C (2.4) | same focused suite | New `TestOutputAnchoringMspR10::test_relative_output_dir_anchors_to_config_dir` → package lands under `<root>/proj/build` | Revert 920c771 — anchors back to server root |
| D (2.5+2.6) | `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` → 158 passed, 2 skipped | Schema projection verified empirically: FastMCP drops undeclared envelope keys; flips assert via `config_errors` text | Revert c3b81bd — tests flip back |
| E (process sweep) | full suite → 1325 passed, 2 skipped | Real-process stdio suite (test_mcp_process.py) green — same spawn fixture | Revert ed1649c — call sites back to old args |

## Verification (Slice 2 gate)

| Command | Result |
|---------|--------|
| uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q | 158 passed, 2 skipped |
| uv run pytest tests/ -q (FULL suite) | 1325 passed, 2 skipped — 1318 baseline + 7 new tests (placeholder-user refusal, 4 unsafe-name, MSP-R10 anchoring, schema identity), flips replace in place, no net deletion |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |
| git status | only SOFER_TRACE.md (untracked, untouched — PB-08) + openspec artifacts (untracked per convention); working tree clean |

## Deviations from Design

1. **Unit D/E merged for test_mcp_server.py**: the 2.6 flips and the 2.7/2.8 sweep are interleaved in the same test functions and hunks (e.g. `test_creates_toml_and_raw` = INIT-03 envelope assert + user+cwd sweep; `test_cwd_outside_via_mcp_schema_rejected` = sweep + adjacent new MSP-R10 class). A line-level split would produce distorted, un-reviewable hunks; committed as one unit (c3b81bd). The process sweep is its own unit (ed1649c).
2. **test_mcp_process.py sweep pulled forward from Slice 4 (task 4.2)**: the production change (validate-first user requirement + fail-closed cwd) breaks the 7 in-process/stdio call sites at L113/170/174/181/195/203/262, and this slice's gate requires the FULL suite green. The 4.2 sweep portion is done; the `mcp_stdio_parent_root` fixture (4.1) and `TestParentRootIdentity` (4.3) remain Slice 4. Task 4.2 stays unchecked in tasks.md — Slice 4 confirms the sweep and owns the remaining parent-root identity work.
3. Intermediate commits (A/B/C) leave the focused suite red until D/E land — inherent to the coupling (the flips are the direct test consequences of A and cannot pass before A); the final slice state is fully green.
4. `user_val = user.strip()` is guarded by `assert user is not None` (mypy narrowing) instead of a bare call — validation guarantees non-None; the assert documents the invariant.

## Issues Found

- **FastMCP in-process projection drops undeclared envelope keys** (verified empirically): sofer_init refusal envelopes surface only `ok`/`exit_code`/`output`/`config_errors`; `error_code`/`message`/`next` are NOT client-visible (schema does not declare them). The 2.6 flip tests therefore assert the refusal via `config_errors` message text ("single path component", "user must be non-empty", "cwd") — consistent with the existing suite (no test asserts `error_code`; test_mcp_process.py header documents the projection contract). The INTERNAL envelope still carries `error_code: CONFIG_ERROR` + `next: {}` per 10.3.
- Refusal envelopes project `config_path`/`dataset_root` as `None` (schema-declared fields absent from the internal dict) — "refusals carry none" satisfied; tests assert absence-of-write rather than key absence.
- LSP flags `tomli` import + `_SERVER_ROOT` global redefinition as pre-existing (unchanged from Slice 1; project mypy config ignores both).
- `_bound_discovery` removal is a pure retirement: `from_toml(discovery_root=...)` now binds discovery per-call at all 4 MCP sites (MSP-R10); the TC-05 model tests cover the bound semantics.

## Remaining Tasks

Phase 2 (Slice 2) complete. Phase 3 (Slice 3 / PR 3): tasks 3.1-3.5 — CLI `--user` required + rejections + anchors + README pair + CLI tests. Phase 4 (Slice 4 / PR 4): tasks 4.1-4.3 — conftest parent-root fixture + process sweep (partially pre-done in ed1649c) + TestParentRootIdentity. Phase 5: per-slice gates.

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain), PR 2 of 4
- Current work unit: Slice 2 — Phase 2 tasks 2.1-2.8 (+ process sweep pulled forward)
- Boundary: PR 1 (5ba842c..429a061) → PR 2 (5ba842c..064239b) — 6 commits: 3 production (A/B/C) + 2 test (D/E) + 1 style
- Estimated review budget impact: 6 commits, ~480 changed lines (production ~90, tests ~390)

## Status

8/8 tasks complete (Slice 2). Ready for next slice (PR 3) — CLI + docs (tasks 3.1-3.5). Full suite re-baselined at 1325 passed, 2 skipped.
---

# Apply Progress: fix/dataset-identity-context — Slice 3 / PR 3 (Phase 3 tasks 3.1-3.5)

**Change**: fix-dataset-identity-context
**Branch**: fix/116-dataset-identity-context
**Mode**: Standard (strict_tdd false)
**Date**: 2026-09-04
**Delivery**: auto-forecast / feature-branch-chain — PR 3 base = PR 2 (branch head 064239b..baf6eff)

## Work Units

| Unit | Tasks | Commit | Notes |
|------|-------|--------|-------|
| A | 3.1, 3.2 | a9e21cd fix(cli): require --user and reject unsafe identity in init | `_cmd_init` validate FIRST via `validate_identity` → each error to stderr, exit 1, no TOML/raw (CLI-R07 pre-write); `dataset_root = resolve_dataset_root(None, live_cwd=Path.cwd().resolve())` (mode a, no bound); `output = dataset_root / f"{name}.toml"`; `raw_dir_path = dataset_root / config.RAW_DIR`; `user_val = args.user`; absolute `OK  Created {output}` at all 5 write sites (non-move + 4 move branches); exists-guard kept (validate → resolve → exists-guard → scaffold → write per D7); move-existing candidate collection + `base_dir` re-anchored to `dataset_root` (identical value, one resolved root). argparse `--user` → `required=True` (exit 2 naming `--user`, no write) + help text per CLI-R07; top-level description example updated to `sofer init my-dataset --user myuser` (rule 7 help accuracy). Handler-level `validate_identity` kept as defense-in-depth for direct `_cmd_init(Namespace(...))` calls. |
| B | 3.3 | 4f4bd4c fix(cli): anchor single-file output overrides to input parent | Relative `--output` now anchors to the input's parent (MSP-R10 parity with the MCP side): `_cmd_codebook` → `Path(args.csv).parent`; `_cmd_profile` → `Path(args.dataset).parent`; `_cmd_render` → package dir-or-file (`pkg if pkg.is_dir() else pkg.parent`). Absolute `--output` unchanged. Batch tools already `cfg._base_dir`-anchored — untouched. |
| C | 3.4 | 37bff75 test(cli): init identity, required --user, and absolute print | Flip L117 `test_init_content_is_valid_toml` → `user="alice"`, `repo_id == "alice/test-ds"`; L187 `test_init_default_user_placeholder` repurposed → `test_init_missing_user_rejected_handler` (rc 1, no TOML/raw, stderr names user) + `test_init_missing_user_rejected_subprocess` (rc 2, stderr names `--user`, no TOML); TestParser.test_init_command gains `--user alice` + sibling `test_init_requires_user` (SystemExit 2 naming `--user`); `user="alice"` added to every `_cmd_init` call in TestInitCommand/TestInitTemplateCommands/TestInitRawFolder; external call sites fixed: test_config.py:530 + test_scanner.py:925 gain `user="testuser"` (stale YOUR_USER patch-replace removed — template now embeds a validated repo_id); NEW `test_init_prints_absolute_config_path` (run_cli rc 0, stdout contains `str(tmp_path.resolve() / "myds.toml")` — CLI-R07 canonical absolute print); NEW rc-1 subprocess rejections: placeholder `--user YOUR_USER` (stderr names placeholder, no TOML/raw) + unsafe `a/../b` (stderr names component, no file). |
| D | 3.5 | baf6eff docs: document required --user and identity validation in init | README.md L318 (`init <name>`) + L348 (`--user USER`) and README_ES.md L330 + L360 updated SAME commit (rule 13): `--user` required, missing → exit 2, placeholder/unsafe → exit 1 pre-write, absolute `config_path` print. Technical tokens stay English in both; prose translated in README_ES. |

## Completed Tasks

- [x] 3.1 `_cmd_init` (cli.py): validate first via `validate_identity` → errors to stderr + exit 1 (no write); `dataset_root = resolve_dataset_root(None, live_cwd=Path.cwd().resolve())` (mode a, no bound); `output = dataset_root / f"{name}.toml"`; `raw_dir_path = dataset_root / config.RAW_DIR`; `user_val = args.user`; absolute `OK  Created {output}` (L841-858 + 4 move-existing branches use the same resolved paths); exists-guard behavior kept (refuse overwrite)
- [x] 3.2 argparse `--user` → `required=True` (exit 2 naming `--user`, no write) + help text updated per CLI-R07; handler-level `validate_identity` kept as defense-in-depth (covers direct `_cmd_init(Namespace(...))` calls)
- [x] 3.3 CLI single-file `--output` anchors: `_cmd_codebook` → `Path(args.csv).parent`; `_cmd_profile` → `Path(args.dataset).parent`; `_cmd_render` → package dir-or-file (`pkg if pkg.is_dir() else pkg.parent`); batch tools already `cfg._base_dir`-anchored — no change
- [x] 3.4 `tests/test_cli.py`: L117 flip (`user="alice"`, `repo_id == "alice/test-ds"`); L187 repurposed → missing-`--user` rejection (handler rc 1 + subprocess rc 2, no TOML); TestParser.test_init_command + `--user alice` + sibling SystemExit(2)-naming-`--user` test; `--user` added to all TestInitCommand calls (plus TestInitTemplateCommands/TestInitRawFolder + test_config.py:530 + test_scanner.py:925); NEW print test (rc 0, absolute `config_path` in stdout); NEW rc-1 rejection tests (placeholder `YOUR_USER`, unsafe `a/../b`)
- [x] 3.5 README.md + README_ES.md same commit (rules 7/13): `init <name>` row + `--user` row → required, pre-write rejection of placeholder/unsafe identity, absolute `config_path` print; technical text stays English in both files

## Work Unit Evidence

| Work unit | Focused test command and exact result | Runtime harness command/scenario and exact result | Rollback boundary |
|-----------|----------------------------------------|---------------------------------------------------|-------------------|
| A (3.1+3.2) | `uv run pytest tests/test_cli.py -q` → 87 passed (final, after C landed) | `run_cli(["init","myds2"], cwd=tmp_path)` → rc 2, stderr names `--user`, no TOML; `run_cli(["init","myds","--user","alice"], cwd=tmp_path)` → rc 0, stdout contains absolute config_path | Revert a9e21cd — restores `--user` default + relative print + no validation |
| B (3.3) | same focused suite (B alone is behavior-neutral for existing tests — all single-file `--output` call sites use absolute paths) | Anchoring proven by code inspection + full suite; no existing test exercised relative single-file `--output` against cwd | Revert 4f4bd4c — relative `--output` resolves against cwd again |
| C (3.4) | `uv run pytest tests/test_cli.py tests/test_config.py tests/test_scanner.py -q` → 217 passed | Subprocess boundary: rc 2 (missing --user) / rc 1 (placeholder, unsafe name) / rc 0 + absolute print, all via real `python -m sofer.cli` (PB-02) | Revert 37bff75 — tests flip back to placeholder-default expectations |
| D (3.5) | N/A — docs-only | README mirror check: init/--user rows present in BOTH README.md and README_ES.md | Revert baf6eff — rows back to "default: YOUR_USER placeholder" |

## Verification (Slice 3 gate)

| Command | Result |
|---------|--------|
| uv run pytest tests/test_cli.py -q | 87 passed |
| uv run pytest tests/ -q (FULL suite) | 1330 passed, 2 skipped — 1325 baseline + 6 new tests − 1 removed (test_init_default_user_placeholder) = net +5; re-baselined |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |
| git status | SOFER_TRACE.md untracked and UNMODIFIED (PB-08: never staged, never touched; mtime 2026-08-31 17:40, predates session; length 17210) + openspec artifacts untracked per convention; README.md + README_ES.md both updated (rule 13) |

## Deviations from Design

1. **Intermediate commits leave the focused suite red until C lands** — inherent coupling (the 3.4 flips are the direct test consequences of 3.1/3.2 and cannot pass before them), identical to Slice 2 deviation #3. The final slice state is fully green; the commit order follows the orchestrator's explicit unit plan (A production → B production → C tests → D docs).
2. **test_config.py:530 and test_scanner.py:925 also needed `user=`** — the design's flip list named only test_cli.py, but `_cmd_init` is called from two sibling modules; both assert rc 0, so they required the sweep edit. test_scanner.py's stale `YOUR_USER/my-ds` patch-replace was removed (the template now embeds a validated `testuser/my-ds` repo_id; the replace had become a no-op).
3. **`--user` added beyond TestInitCommand** — TestInitTemplateCommands and TestInitRawFolder also call `_cmd_init(Namespace(...))` without user; all 18 in-file call sites got `user=` (task 3.4 wording said "all TestInitCommand calls" but the requirement applies to every direct handler call).
4. **Move-existing candidate collection re-anchored to `dataset_root`** — `Path.cwd().iterdir()` / `base_dir = Path.cwd().resolve()` → `dataset_root.iterdir()` / `base_dir = dataset_root`. Identical values (mode (a) returns the resolved live cwd); keeps the whole handler on one resolved root (design D7's "same resolved paths").
5. **Top-level parser description example updated** — `sofer init my-dataset` → `sofer init my-dataset --user myuser` (AGENTS.md rule 7 help-text accuracy; the old example would now exit 2). Not in the design's explicit list but required for truthful help text.

## Issues Found

- Ruff E501 surfaced when `user="alice"` pushed `_cmd_init` call lines past 100 chars — wrapped in the existing two-line style (then ruff format normalized indentation to 12-space continuation). No test-semantic changes from the wraps.
- LSP `tomli` import warnings in cli.py/test files remain pre-existing (conditional Python 3.10 fallback, documented Slices 1-2; mypy config ignores).
- `validate_identity`'s S3 note (interior-space names accepted) is unchanged at the CLI layer: `--user "my user"` → rejected by `^[\w\-]+$` regex; `name "my dataset"` is still accepted (contract-faithful per INIT-05 wording — recorded in Slice 1 as a known decision, not a defect).

## Remaining Tasks

Phase 3 (Slice 3) complete. Phase 4 (Slice 4 / PR 4): tasks 4.1-4.3 — conftest parent-root fixture (`mcp_stdio_parent_root`, PB-09 second fixture) + TestParentRootIdentity real-process class (PB-04); task 4.2 process sweep is partially pre-done in ed1649c (Slice 2). Phase 5: per-slice gates (5.1 done for slices 1-3; 5.2 done for slice 3).

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain), PR 3 of 4
- Current work unit: Slice 3 — Phase 3 tasks 3.1-3.5
- Boundary: PR 2 (064239b) → PR 3 (a9e21cd..baf6eff) — 4 commits: 2 production (A/B) + 1 test (C) + 1 docs (D); ~150 changed lines
- Estimated review budget impact: ~150 changed lines (production ~75, tests ~70, docs 4)

## Status

5/5 tasks complete (Slice 3). Ready for next slice (PR 4) — real-process stdio parent-root identity (tasks 4.1-4.3). Full suite re-baselined at 1330 passed, 2 skipped.
---

# Apply Progress: fix/dataset-identity-context — Slice 4 / PR 4 (Phase 4 tasks 4.1-4.3 + gate-review follow-up) — FINAL slice

**Change**: fix-dataset-identity-context
**Branch**: fix/116-dataset-identity-context
**Mode**: Standard (strict_tdd false)
**Date**: 2026-09-04
**Delivery**: auto-forecast / feature-branch-chain — PR 4 base = PR 3 (branch head baf6eff..62da878)

## Work Units

| Unit | Tasks | Commit | Notes |
|------|-------|--------|-------|
| A | 4.1, 4.3 | d6f5ee4 test(process): add parent-root stdio fixture and fail-closed identity test | conftest gains the second module-scoped stdio fixture `mcp_stdio_parent_root` (PB-09: `tmp_path_factory.mktemp("mcp-stdio-parent")` + `(parent / "child").mkdir()` → `McpStdioServer(cwd=parent)`; reuses the existing dataclass, no new class; one spawn per module). New `TestParentRootIdentity` (PB-04 ground truth) launches the REAL `sofer-mcp` process via that fixture (server root = parent, live CWD = parent) and runs BOTH scenarios over ONE stdio session (one spawn per module, PB-09 lean-spawn bound): (a) `sofer_init(name="test", user="testuser")` cwd omitted → `ok:False` refusal whose `config_errors` name `cwd` (the `IdentityResolutionError` strict-descendant message), NO `parent/test.toml`, NO `parent/raw/` — THE #116 reproduction fail-closed; (b) `sofer_init(name="test", user="testuser", cwd="child")` → `child/test.toml` + `child/raw/` exist, `parent/test.toml` ABSENT, envelope reports absolute `config_path`/`dataset_root` (INIT-03, PB-03 — both output_schema-declared so they survive the stdio projection) |
| B | follow-up (Slice 3 WARNING) | 62da878 test(cli): cover single-file output anchoring to input parent | `TestSubprocessBoundary::test_codebook_relative_output_anchors_to_input_parent`: `run_cli(["codebook", "data/sample.csv", "-o", "out.md"], cwd=tmp_path)` with the input in `data/` and the subprocess cwd at the parent — asserts rc 0, `tmp_path/data/out.md` EXISTS (anchored to the INPUT's parent, D9/MSP-R10 parity) and `tmp_path/out.md` does NOT (never cwd). Tiny inline CSV (`col;val\n1;2\n`), no fixture file needed |
| C | 4.2 remainder | — (NO commit — nothing remained) | Verified `ed1649c` covered ALL of the 4.2 sweep: TestRecoveryInit L162-206 already carries user+cwd and its template expectations already flipped `user="YOUR_USER"` → `user="testuser"` (L183/L209); greenfield L262 has user+cwd; the only cwd-less call site is TestNestedCwd L113 — INTENTIONAL (it is the spec's "cwd omitted with live CWD strictly inside root" strict-descendant auto-detect scenario; adding cwd would destroy the test's purpose). Same for test_mcp_server.py L2702/L2720 (TestInitAutoCwd, in-process auto-detect/fail-closed). No changes were required — Unit C commit skipped per plan |

## Completed Tasks

- [x] 4.1 `tests/conftest.py`: second module-scoped fixture `mcp_stdio_parent_root` (PB-09): `tmp_path_factory.mktemp("mcp-stdio-parent")` + `(parent / "child").mkdir()` → `McpStdioServer(cwd=parent)`; reuses the existing dataclass (no new class); one spawn per module; module docstring updated to name the sibling fixture
- [x] 4.2 `tests/test_mcp_process.py` sweep — VERIFIED COMPLETE (ed1649c, Slice 2): TestRecoveryInit template expectations flipped to `user="testuser"` (L183/L209); all call sites carry user+cwd except TestNestedCwd L113 which INTENTIONALLY keeps cwd omitted (the strict-descendant auto-detect scenario); greenfield L262 has user+cwd. Nothing remained to fix
- [x] 4.3 New `TestParentRootIdentity` (PB-04 ground truth) via the real stdio process: (a) cwd omitted → input-required refusal naming `cwd`, NO parent `test.toml`/`raw/`; (b) `cwd="child"` → `child/test.toml` + `child/raw/` exist, `parent/test.toml` absent, envelope absolute `config_path`/`dataset_root`. Both scenarios in ONE stdio session (one spawn per module)
- [x] Phase 5 gate-review follow-up: new CLI boundary test `test_codebook_relative_output_anchors_to_input_parent` (single-file `--output` anchors to the input's parent, never cwd — D9/MSP-R10 parity, Slice 3 WARNING)
- [x] 5.1 Per-slice verification — complete for all 4 slices (this slice's gates below)
- [x] 5.2 SOFER_TRACE.md untouched (PB-08: mtime 2026-08-31 17:40, length 17210 — verified this slice); README/README_ES both updated in Slice 3 (rule 13)

## Work Unit Evidence

| Work unit | Focused test command and exact result | Runtime harness command/scenario and exact result | Rollback boundary |
|-----------|----------------------------------------|---------------------------------------------------|-------------------|
| A (4.1+4.3) | `uv run pytest tests/test_mcp_process.py tests/test_cli.py -q` → 100 passed | REAL `sofer-mcp` stdio spawn (fixture `mcp_stdio_parent_root`, one subprocess): cwd omitted at parent root → refusal naming cwd, no parent writes; then `cwd="child"` in the same session → child/test.toml + child/raw/, absolute config_path/dataset_root in envelope — the #116 reproduction, proven over the real process boundary | Revert d6f5ee4 — fixture + TestParentRootIdentity removed; production untouched |
| B (follow-up) | same focused suite (100 passed) | `run_cli(["codebook","data/sample.csv","-o","out.md"], cwd=tmp_path)` subprocess → rc 0, `data/out.md` exists, `<cwd>/out.md` absent | Revert 62da878 — test removed; production untouched |
| C (4.2 verify) | `uv run pytest tests/ -q` → 1332 passed, 2 skipped (sweep sites all green) | N/A — verification-only unit; no code changed (ed1649c already swept) | N/A — no diff produced |

## Verification (Slice 4 gate)

| Command | Result |
|---------|--------|
| uv run pytest tests/test_mcp_process.py tests/test_cli.py -q | 100 passed |
| uv run pytest "tests/test_mcp_process.py::TestParentRootIdentity" "tests/test_cli.py::TestSubprocessBoundary::test_codebook_relative_output_anchors_to_input_parent" -v | 2 passed (the two new tests) |
| uv run pytest tests/ -q (FULL suite) | 1332 passed, 2 skipped — 1330 baseline + 2 new tests; re-baselined |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |
| git status | SOFER_TRACE.md untracked, mtime 2026-08-31 17:40, length 17210 — UNTOUCHED (PB-08); openspec artifacts untracked per convention |

## Deviations from Design

1. **TestParentRootIdentity runs BOTH scenarios in one stdio session (one spawn per module)**: the design/tasks describe (a) and (b) as separate sub-cases, but PB-09's lean-spawn bound ("keeping one spawn per module per fixture") plus the repo's own `McpStdioServer` docstring ("bounding subprocess wall-clock to one spawn per module") make a single session the strictest reading — the fixture is module-scoped, one subprocess serves both sequential calls, and the live CWD is the parent root for both (the ground-truth setup for each). Failure isolation is preserved by distinct assert messages naming the failing scenario.
2. **Task 4.2 wording "user+cwd at L113 (TestNestedCwd)" not applied literally**: L113 keeps `cwd=None` + `monkeypatch.chdir` because the test IS the spec's "cwd omitted with live CWD strictly inside root" scenario (strict-descendant auto-detect); adding explicit cwd would remove the only coverage of that scenario. This matches design D11's sweep intent and Slice 2's recorded decision (ed1649c note). No other 4.2 remainder existed.
3. **Unit C produced no commit**: the plan said "only if changes remain" — verification showed none remained.

## Issues Found

- LSP flags `content[0].text` (mcp content-union narrowing) and the implicit `from conftest import` in the new test code — IDENTICAL pre-existing patterns in TestStdioFraming L90/L164 and every sibling module; mypy excludes tests, the suite passes. No action.
- The refusal envelope over stdio carries `ok`/`exit_code`/`output`/`config_errors` only (error_code/message/next dropped by output_schema projection) — the new test asserts the refusal via `config_errors` text naming `cwd`, consistent with the documented boundary contract in the module header.

## Remaining Tasks

None — all phases complete. Change ready for sdd-verify (full-suite re-baseline 1332 passed, 2 skipped across all 4 slices).

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain), PR 4 of 4 (FINAL)
- Current work unit: Slice 4 — Phase 4 tasks 4.1-4.3 + gate-review follow-up (Unit C skipped: no 4.2 remainder)
- Boundary: PR 3 (baf6eff) → PR 4 (d6f5ee4..62da878) — 2 commits, ~110 changed lines (all tests; production untouched across the whole slice)
- Estimated review budget impact: 2 commits, ~110 changed lines (fixture 28 + process test 60 + CLI test 15 + conftest docstring)

## Status

3/3 tasks complete (Slice 4) + Phase 5 gates 5.1/5.2 complete for all 4 slices. **All phases complete — change ready for sdd-verify.** Full suite re-baselined at 1332 passed, 2 skipped.

---

# Post-audit blockers (5) — applied 2026-09-04 (post-verify, pre-merge)

**Context**: An independent audit of the verified + archived change found 5 real defects. Fixed on `fix/116-dataset-identity-context` BEFORE merge. Strict TDD disabled (Standard mode). All gates re-run after the fixes.

## Work Units

| Unit | Blocker | Commit | Notes |
|------|---------|--------|-------|
| 1 | B1 — user regex accepts trailing `\n`; CLI/MCP divergence | 615decc fix(context): reject control characters in user identity | `_USER_RE` `^[\w\-]+$` → `^[\w\-]+\Z` (end-of-string anchor — Python `$` matches before a trailing `\n`); `validate_identity` adds a control-char check for `user` mirroring `name` (rejects `\n`/`\t`/NUL/DEL before the regex step); +4 unit matrix cells (alice\n/alice\t/alice\x00/alice\x7f) and +1 MCP boundary refusal test (newline user → ok:False, no TOML, no raw/) |
| 2 | B2 — `sofer_init` uses stale global `sofer_config.RAW_DIR` | ba59a57 fix(mcp): reload tool config per init root for raw dir | `_reload_tool_config(effective_root)` runs right after `effective_root` resolution and BEFORE `raw_dir = effective_root / sofer_config.RAW_DIR` (mcp_server L1706); defaults unchanged when no pyproject; +1 test (pyproject `raw_dir="sources"` under root A → `A/sources/` not `A/raw/`; second init in root B without pyproject → `B/raw/`, no cross-call leakage) |
| 3 | B3 — MCP render output anchor diverges from CLI for package directories | 7bbd065 fix(mcp): anchor render output inside package directories | MCP `_contained_path` anchor `root=package_path.parent` → `root=package_path if package_path.is_dir() else package_path.parent` (single expression, CLI `_cmd_render` parity); +2 tests (dir package → `<dir>/out/README.md` not `<parent>/out/`; file package → parent anchor unchanged) |
| 4 | B4 — `dry_run` WRITES the TOML (contradicts spec + tool docs) | 9418621 fix(mcp): dry-run init performs no filesystem writes | Both dry-run branches no longer call `write_text`; print `DRY RUN  Would create <name>.toml` + `DRY RUN  Would scaffold <raw_dir>` and return the same ok:True envelope with `report_identity` (computed path, no write). `move_existing` dry-run keeps its move-preview lines and never creates `raw/`. Field description + Args docstring updated to "without writing any files". TEST FLIP: `test_dry_run_no_mutation` L2253-2254 `is_file()` → `not .exists()`; +1 new test `test_dry_run_plain_no_toml` (plain dry-run no writes, identity still reported) |
| 5 | B5a/B5c — quick start missing `--user`; `user` schema optional | 3f4f9ef fix(docs): required --user in quick start and required user schema | B5a: `sofer init my-dataset` → `sofer init my-dataset --user myuser` in README.md L62 AND README_ES.md L64 (same commit, rule 13; technical text English in both). B5c: `user: Annotated[str \| None, Field(...)] = None` → `user: Annotated[str, Field(description=...)]` (required, moved before the defaulted params; `assert user is not None` removed); +1 schema test (`user` in `required`, type string, not nullable); TEST FLIP: `test_missing_user_refused_before_write` — absent user now rejected in-schema (`ToolError`), no TOML/raw |

## Blocker 5b (tool documentation audit) — verified, NO change needed

The audit asked to verify all 14 tool names appear in the MCP section of README.md/README_ES.md (prose ~L510-514 and quick-reference table ~L539-551). Verified programmatically against the server's 14 registered callables (`test_mcp_schema.py::TestToolCount::test_fourteen_tools` roster): **all 14 names appear in BOTH files in BOTH the prose list and the table** (the combined `sofer_scan_dry_run / sofer_scan_apply` row counts as both). No missing/misnamed tool found; no doc edit required.

## Blocker 4 spec alignment — verified, NO live-spec change needed

The audit's conditional ("update the live spec IF INIT-01/INIT-02 or the tool description contract says dry_run writes the TOML") was checked: openspec/specs/mcp-server/spec.md INIT-01 (Windows-safe placeholder), INIT-02 (cwd containment), and INIT-03 (anchored writes + identity reporting) do NOT state that dry_run writes the TOML; the tool docstring already said "unless dry_run" and the Field description said "without writing raw/ or moving files". The implementation + tests now match the existing no-mutation intent; the Field/Args wording was tightened to "without writing any files" to remove the ambiguity. The CLI spec (CLI-R07) `--dry-run previews no mutation` is CLI-side and out of scope (MCP-only blocker). No spec.md edit was required or made.

## Verification (post-fix gates)

| Command | Result |
|---------|--------|
| uv run pytest tests/ -q (FULL suite) | 1342 passed, 2 skipped, 0 failed — 1332 baseline + 10 new tests (5 B1 + 1 B2 + 2 B3 + 1 B4 + 1 B5c), 2 flips replaced in place; re-baselined |
| uv run pytest tests/test_execution_context.py tests/test_mcp_server.py tests/test_mcp_schema.py -q | 214 passed, 2 skipped |
| uv run pytest tests/test_mcp_process.py -q | 12 passed |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |
| git status | SOFER_TRACE.md untracked, mtime 2026-08-31 17:40, length 17210 — UNTOUCHED (PB-08); openspec artifacts untracked per convention |

## Files Changed (post-audit)

| File | Action | What Was Done |
|------|--------|---------------|
| src/sofer/execution_context.py | Modified | `_USER_RE` `\Z` anchor; user control-char check in `validate_identity` (B1) |
| src/sofer/mcp_server.py | Modified | `_reload_tool_config(effective_root)` in sofer_init (B2); render output anchor dir-vs-file (B3); dry-run branches no-write + preview lines + Field/Args wording (B4); `user` required non-nullable + `assert` removed (B5c) |
| tests/test_execution_context.py | Modified | +4 user control-char matrix cells (B1) |
| tests/test_mcp_server.py | Modified | +1 newline-user boundary refusal (B1); +1 raw-dir reload test (B2); +2 render anchoring tests (B3); flip `test_dry_run_no_mutation` + `test_dry_run_plain_no_toml` (B4); flip `test_missing_user_refused_before_write` → ToolError (B5c) |
| tests/test_mcp_schema.py | Modified | +1 `test_sofer_init_user_required` (B5c) |
| README.md / README_ES.md | Modified | quick start `--user myuser` in both (B5a, rule 13) |

## Deviations / Notes

1. **B5c forced a parameter reorder**: a required `user` after defaulted params is illegal Python, so `user` moved to directly after `name`. All call sites pass keyword args — no caller impact; schema `required` is now `["name", "user"]`.
2. **B5c changed the missing-user boundary contract**: absent `user` is now rejected by FastMCP input validation (`ToolError`) instead of reaching the tool for an envelope refusal. `user=""` / `"   "` still reach the tool and refuse via envelope (validate_identity). The INIT-05 scenario "missing or blank identity refused before write" holds at the schema boundary for absent values and at the envelope for blank values.
3. **B4 test flip is a deliberate contract correction**: the old assertion `assert (tmp_path / "my-ds.toml").is_file()` codified the bug; it now asserts the TOML is NOT written.
4. Commit 5 (3f4f9ef) additionally carries a 1-line ruff-format collapse of a B3 test signature (discovered by the final `ruff format --check` gate; folded into the local unpushed branch, no semantic change).

## Status

5/5 blockers fixed and verified. Ready for sdd-verify (full-suite re-baseline 1342 passed, 2 skipped).

---

# Pre-merge alignment (2026-09-04) — final apply batch before merge

**Context**: Re-verification (1342 passed / 2 skipped) and security/resilience audits found NO CRITICAL issues. Two should-fix resilience WARNINGs were closed in this batch: (1) CLI `--dry-run` wrote files while MCP `sofer_init(dry_run=True)` writes nothing — adapter semantics for the same flag contradicted each other; (2) the synced live specs + archive were uncommitted, so HEAD's committed specs contradicted shipped code (old `user: str | None = None` + `YOUR_USER` placeholder). Strict TDD disabled (Standard mode). Committed locally as two work units; no push, no PR.

## Work Unit 1 — CLI `--dry-run` no-mutation parity (resilience WARNING #2)

| Commit | Scope |
|--------|-------|
| `a1cb36f fix(cli): honor --dry-run as no-mutation in init` | `src/sofer/cli.py`, `tests/test_cli.py`, `openspec/specs/cli/spec.md` |

- `_cmd_init` plain-init branch (no `--move-existing`): `--dry-run` previously ALWAYS wrote `raw/` + the TOML (`dry_run` was never consulted). Now previews `DRY RUN  Would create <name>.toml` + `DRY RUN  Would scaffold <raw_dir>` and exits 0 with ZERO writes.
- `--move-existing --dry-run` branch: previously printed move previews but STILL wrote the TOML. Now preview-only (no TOML, no `raw/`, no moves) — aligned with MCP `sofer_init` (mcp_server.py:1776-1804).
- `init --dry-run` argparse help + `init` description updated: "performs no writes in either branch (no <name>.toml, no raw/, no moves)".
- CLI-R07 spec body now documents `--dry-run` as no-mutation for BOTH branches; new scenario "Dry-run plain init no mutation"; existing "Dry-run preview" scenario extended to assert no TOML.
- Tests: `TestSubprocessBoundary::test_init_dry_run_no_mutation` (new, subprocess, rc 0 + preview text + no TOML + no raw/); `TestInitRawFolder::test_init_plain_dry_run_no_mutation` (new, in-process); `test_move_existing_dry_run_no_mutation` FLIPPED — `assert (tmp_path/"my-ds.toml").exists()` → `assert not ...` (the old assertion codified the bug; deliberate contract correction, same intent as the B4 MCP flip).

## Work Unit 2 — commit synced specs + archive (resilience WARNING #3)

| Commit | Scope |
|--------|-------|
| `docs(sdd): commit synced specs, archive, and post-audit re-verification` | `openspec/` (project.md, specs/{mcp-server,process-boundary,tool-config}/spec.md — cli/spec.md already in unit 1 — and `changes/archive/2026-09-04-fix-dataset-identity-context/`) |

- `openspec/project.md` count drift fixed: 3× "1332 passed, 2 skipped" → **1342 passed, 2 skipped** (structure tree, Testing section, footer). Test-file count re-verified at 29 — wording already accurate.
- Archive folder verified complete: proposal, design, tasks, `specs/{cli,mcp-server,process-boundary,tool-config}/spec.md`, apply-progress, verify-report, exploration, archive-report — all present; verify-report includes the post-audit re-verification section (B1-B5 conformance + gates + +10 count reconciliation + SUGGESTIONs).
- **INIT-05 prose regex aligned** (verify SUGGESTION 1: "align the spec regex literal with `\Z` at the next spec edit for exactness"): prose `^[\w\-]+$` → `^[\w\-]+\Z` in the requirement body (with an inline note explaining `\Z` is the exact no-trailing-newline anchor, strict superset of the old `$`-form) and in the "Non-conforming user rejected" scenario (now also cites `alice\n`). Implementation (`execution_context._USER_RE = re.compile(r"^[\w\-]+\Z")`) and prose now match exactly — chose the `\Z` option over keeping `$`, per the verify SUGGESTION.
- Committed with `git add openspec/` ONLY — SOFER_TRACE.md never staged (PB-08).

## Gates (post-alignment, ACTUAL output)

| Command | Result |
|---------|--------|
| uv run pytest tests/ -q (FULL suite) | **1344 passed, 2 skipped, 0 failed** — 1342 baseline + 2 new CLI dry-run tests; re-baselined |
| uv run pytest tests/test_cli.py -q | 90 passed |
| uv run mypy src/ | Success: no issues found in 30 source files |
| uv run ruff check src/ tests/ | All checks passed |
| uv run ruff format --check src/ tests/ | 60 files already formatted |
| git diff --check | clean |
| git status | SOFER_TRACE.md untracked (`??`) and UNMODIFIED — never staged (PB-08); openspec/ committed; no unintended files |

## Status

2/2 pre-merge alignment work units complete. Branch `fix/116-dataset-identity-context` is **merge-ready** (subject to orchestrator/PR review): full suite 1344 passed / 2 skipped, all gates green, resilience WARNINGs #2 and #3 closed, SOFER_TRACE.md untouched.
