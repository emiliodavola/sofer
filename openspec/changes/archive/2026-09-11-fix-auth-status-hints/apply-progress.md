# Apply Progress: 2026-09-11-fix-auth-status-hints

**Status:** success — implementation + tests complete, all gates green.
**Change:** `2026-09-11-fix-auth-status-hints` · **Branch:** `fix/144-auth-status-hints` (base `dev` verified: `git merge-base --is-ancestor dev HEAD` OK).
**Scope:** GitHub ISSUE #144 ONLY. Posture fields (`phrase_source`, `server_process_id`, `server_started_at`, `server_version` — #145) absent (grep gate clean).
**Mode:** standard (strict TDD off per tasks.md: `strict_tdd=false`; the delivery contract orders implementation before tests — recorded deviation from design §6 RED-first ordering; tests still ran immediately after GREEN and everything passed).

## Phase 0 — Baseline evidence (recorded before any edit)

- Branch: `fix/144-auth-status-hints`; `dev` is an ancestor (base OK); HEAD `7d5cc31` (merge PR #157).
- Baseline suite: **1468 passed, 6 skipped** (`uv run pytest tests/ -q`, 60.48s). No `SOFER_MCP_APPROVAL_PHRASE` in the shell env (unconfigured tests are env-clean).
- Baseline gates: `uv run ruff check src/ tests/` "All checks passed!", `uv run ruff format --check` "64 files already formatted", `uv run mypy src/` "Success: no issues found in 32 source files".
- Anchors confirmed pre-edit: refusal literal at `mcp_server.py:1155` (inside `PUBLISH_APPROVAL_NOT_CONFIGURED` branch); `sofer_auth_status` `sofer_auth_status` def at `:1609`; unconfigured branch `next_hint["action"] = "configure_approval_phrase"` at `:1672`; `build_server` env read `os.environ.get("SOFER_MCP_APPROVAL_PHRASE")` at `:2642`; module docstring never-leak sentence at `:47-48`. Tests: `TestNextHintContract` L208 (flatness helper L213), `TestToolRoster` L258, `TestPublishAuthorizationLadder` L638, `test_no_phrase_configured_refuses_fail_closed` L750 (exact-dict hint L784, `"publish is disabled"` L786); `test_mcp_schema.py` `test_auth_status_no_leak` L305 (L327), `test_auth_status_approval_not_configured` L330 (L348/L349). All confirmed at the documented locations.
- Anti-posture at baseline: `grep -nE "phrase_source|server_process_id|server_started_at|server_version" src/sofer/mcp_server.py` → zero matches.

## Phase 1 — Implementation (7/7 tasks done)

- Added the D3 fact-constant block between `_PHASED_INSTRUCTIONS` and the `_APPROVAL_PHRASE` global: `_APPROVAL_PHRASE_ENV_VAR`, `_APPROVAL_PHRASE_ACTION`, `_PHRASE_READ_ONCE_FACT`, `_PHRASE_LAUNCH_ENV_FACT`, `_PHRASE_RESTART_FACT`, `_PHRASE_VERIFY_FACT`, `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` (opencode `(type, command, cwd)` / codex `(env_vars,)` / gemini `(env,)` — verified against `mcp_registration.build_entry` :158-165), `_OPENCODE_SETUP_FACT` / `_CODEX_SETUP_FACT` / `_GEMINI_SETUP_FACT`. ASCII only, `-` separators, no `[tool.sofer]` key, no pyproject.toml change.
- Added composed `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`: verbatim `"publish is disabled:"` prefix; `_PHRASE_READ_ONCE_FACT` + `_APPROVAL_PHRASE_ENV_VAR` + `_PHRASE_LAUNCH_ENV_FACT` + `_PHRASE_RESTART_FACT` each exactly once; closes with "a human approval phrase is required for any Hugging Face publish".
- Added module-level pure helper `_approval_phrase_guidance_hints() -> dict[str, Any]` (placed after `_workflow_description`): fresh flat dict each call with `action` + 9 `approval_phrase_*` scalar keys; docstring documents flatness + NAME-only contract.
- Swapped the unconfigured branch in `sofer_auth_status` to `next_hint.update(_approval_phrase_guidance_hints())`; configured branch `next_hint["approval_phrase"] = "<from human>"` untouched; configured branch gains no `approval_phrase_*` key.
- Refusal at (formerly :1155): `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` + `next_hint={"action": _APPROVAL_PHRASE_ACTION}` — runtime `hints` stays byte-for-byte `{"action": "configure_approval_phrase"}` (pin green). `error_code`, `extra`, `config_errors`, never-upload semantics unchanged.
- Docstrings: `sofer_auth_status` — documented unconfigured guidance contract + never-leak rule (kept `When to use:`/`Requires:`/`Next:`, ≤10-sentence pre-block — `test_descriptions_concise_no_msp_untrusted` green, no `MSP-R`/`CF-`/`UNTRUSTED` tokens added); `build_server` warning block — 3 lines on read-once/restart; module docstring — never-leak extended with the NAME-only clause.
- Anti-posture grep INSIDE the diff: zero matches; `git diff src/sofer/mcp_server.py` has no new import (no `datetime`, no `_version`).

## Phase 2 — Tests (8/8 tasks done; all new tests + extends green)

- New class `TestHintContentActionable` (after `TestNextHintContract`; 7 tests: actionable, restart_required is True, flat scalars (reuses `_is_flat_hint_dict` semantics + fresh-dict check), configured-no-guidance, verified registration keys via real `mcp_registration.build_entry`, no phrase material incl. sha256 derived-signal check + exact key-set guard, no config-path names).
- New class `TestApprovalNotConfiguredMessage` (next to `TestPublishAuthorizationLadder`; 3 tests: message process-start semantics + `upload_calls == []`, refusal hints exact dict, 4-fact drift guard between hints and message).
- Additive extends: `test_mcp_schema.py::test_auth_status_approval_not_configured` (kept `:348`/`:349` verbatim; added guidance-keys ⊆ check + env_var value + `restart_required is True` + scalar flatness); `test_auth_status_no_leak` (kept `:327` verbatim; added: serialized refusal message + guidance free of `"phrase123"`, 1-line drift assert `ms._APPROVAL_PHRASE_ENV_VAR in mcp_registration._ENV_KEYS` with rationale comment). Also added `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE")` before `build_server` in the unconfigured schema test (additive, hygiene rule).
- Additive extends `test_mcp_server.py::test_no_phrase_configured_refuses_fail_closed`: message-names-var/read-once/launcher-env/restart asserts appended AFTER the existing block; the exact-dict `:784` and `:786` lines remain byte-for-byte untouched (verified in diff as context lines).
- Pins intact (read-only verification pass): `_is_flat_hint_dict` def, exact-dict `hints` assert, `"publish is disabled"` assert, schema `:327/:348/:349` — all appear in the diff as unchanged context lines; only additions follow them.
- Spec-delta housekeeping done: `TestPublishApprovalLadder` → `TestPublishAuthorizationLadder` in `openspec/changes/.../specs/mcp-server/spec.md` (1 occurrence).
- Focused run: `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` → **213 passed, 3 skipped** (10 new tests collected).

## Phase 3 — Evidence & verification gates (5/5 done)

- Full suite: **1478 passed, 6 skipped** (baseline 1468 + 10 new tests, 54.13s). `TestToolRoster` (14 callables) green; `TestDescriptions` verbosity gate green.
- `uv run ruff check src/ tests/` → "All checks passed!"; `uv run ruff format --check src/ tests/` → clean after `ruff format` applied to the 3 edited files (3 files reformatted, then re-check clean); `uv run mypy src/` → Success (32 files).
- `git diff --check` → clean.
- AGENTS.md §6 mapping (APX-01 scenarios): (1) actionable → `TestHintContentActionable` T1-T4 + extended `test_auth_status_approval_not_configured`; (2) publish refusal → `TestApprovalNotConfiguredMessage` T8/T9 + extended `test_no_phrase_configured_refuses_fail_closed`; (3) one fact source → T10 + T5; (4) no leak/no config path → T6/T7 + extended `test_auth_status_no_leak`.
- Anti-posture over final diff: `git diff | grep -nE "phrase_source|server_process_id|server_started_at|server_version"` → zero matches. Working tree contains ONLY: `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `tests/test_mcp_schema.py` (tracked, modified) + the pre-existing untracked openspec change dirs (parent-provided). No README/README_ES, no pyproject.toml, no workflow.py, no scratch, no .gitignore, no TRACE.md.

## Files changed

| File | Nature |
|---|---|
| `src/sofer/mcp_server.py` | D3 constants block + composed message + `_approval_phrase_guidance_hints()` + branch swap + refusal swap + 3 docstring updates |
| `tests/test_mcp_server.py` | 2 new classes (10 tests) + additive extends + 2 imports (`hashlib`, `mcp_registration`) |
| `tests/test_mcp_schema.py` | additive extends ×2 + imports (`mcp_registration`, `mcp_server as ms`) + env-clean `delenv` |
| `openspec/changes/2026-09-11-fix-auth-status-hints/specs/mcp-server/spec.md` | 1-line pointer fix (`TestPublishAuthorizationLadder`) |
| `openspec/changes/2026-09-11-fix-auth-status-hints/tasks.md` | 24 implementation-owned checkboxes `- [x]`; 3 parent-owned rows untouched |
| `openspec/changes/2026-09-11-fix-auth-status-hints/apply-progress.md` | this file |

## Deviations from design

1. **Ordering** — design §6 says RED-first; tasks.md explicitly orders implementation (phase 1) before tests (phase 2) with `strict_tdd=false`. Followed tasks.md. No RED failure evidence to report (tests were added after implementation; all passed on first run of the two files).
2. **Size** — forecast ~215 (200-240) lines; actual diff **390 insertions / 8 deletions** (398 raw ±). Under the 400-line budget, so the single-PR decision stands, but the overage vs. forecast is real (verbosity of mandated comment blocks, docstrings, and the 10 spec-required tests). `Decision needed before apply: No` / `Chained PRs recommended: No` were followed; delivery is parent-owned.
3. **`envelope["message"]` assertion** — the T13 extends assert on `f"{envelope['message']}{envelope['output']}"` (message + output) instead of `message` alone, because the fastmcp client boundary historically drops some envelope fields; output is the reliable carrier (`:786` already proves it).
4. **Verify fact in drift test** — `_PHRASE_VERIFY_FACT` rides only in the hints surface (message intentionally has exactly 4 facts), so T10's drift map covers exactly the 4 message facts; the verify-step assertion lives in T1.

## Structured status consumed

Native SDD status JSON (parent-resolved, `artifactStore: openspec`, `applyState: blocked` due to ambiguous-change listing) was superseded by the parent prompt, which explicitly selected change `2026-09-11-fix-auth-status-hints` and supplied the runtime attempt token + base branch; task artifacts confirmed present on disk. `actionContext.mode: repo-local`, `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` — all edits inside. No `workspace-planning` warnings.

## Remaining tasks (parent-owned, unchecked)

```text
- [ ] Commit the work in reviewable work units ... <!-- sdd-owner: parent -->
- [ ] Create PR #1 into `dev` ... <!-- sdd-owner: parent -->
- [ ] Post-apply bounded review ... <!-- sdd-owner: parent -->
```

## Workload / PR boundary

Single PR (`fix/144-auth-status-hints` → `dev`), PR #1 of 2, under the 400-line budget at 390 insertions. Sibling `fix/145-auth-status-posture` (issue #145) stays out of this diff. No commits made (per executor contract; parent owns commits).