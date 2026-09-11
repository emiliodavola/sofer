# Tasks: restart-proof posture fields on `sofer_auth_status` (issue #145)

Change `2026-09-11-fix-auth-status-posture` — **PR #2** of the auth_status split, branch
`fix/145-auth-status-posture` (base `dev`, sibling #144 merged at `cf27584`, untouched here).
Scope: **issue #145 ONLY** — add `phrase_source`, `server_process_id`, `server_started_at`,
`server_version` to the `sofer_auth_status` envelope + `output_schema`.

Inputs: `proposal.md`, `specs/mcp-server/spec.md` (MODIFIED 10.8 only, 6 scenarios),
`design.md` (D1–D9, contracts 1–10, §6 test map, §7 anti-regression gate).
`openspec/config.yaml`: `strict_tdd: false`, `test_command: uv run pytest tests/ -q`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380–430 code lines (`src/sofer/mcp_server.py` ~120 + `tests/test_mcp_server.py` ~235 + `tests/test_mcp_schema.py` ~28; + ~600 lines of OpenSpec planning artifacts in the change root, review-light) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR (#2 `fix/145-auth-status-posture` → `dev`) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not applicable — no chaining; single pre-approved PR #2) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

Budget note: the diff is additive, single-concern, 3 code files, no multi-area or generated-code
change; the bulk is additive test coverage (high signal, low cognitive load). Ask-on-risk guard:
if the actual `git diff --stat` exceeds ~450 changed code lines, or any task forces a
non-additive edit outside the 3 files, PAUSE for a delivery decision.

## Scope Guards (hard no-touch, enforced in phase 3)

`TRACE.md`, `scratch/**`, `.gitignore`, `README.md`/`README_ES.md`, `pyproject.toml`,
`src/sofer/workflow.py` (MSP-R13 `next` registry), `mcp_registration.py`, canonical
`openspec/specs/**` (merged at archive), #144 hints/guidance payload and
`_APPROVAL_PHRASE_*` fact constants, `sofer_publish_confirm` gate order, other tools'
envelopes/schemas, tool roster (14 callables), new deps/flags/config keys, any phrase value or
phrase-derived signal in the envelope. No tag, no release, no version bump. Never commit to
`main`/`dev`.

---

## Phase 0 — Baseline evidence (read-only, before any edit)

- [x] Confirm branch and base: `git rev-parse --abbrev-ref HEAD` = `fix/145-auth-status-posture`; `git log --oneline -3` shows `dev`-based head with #144 (`cf27584`) reachable (`git merge-base --is-ancestor cf27584 HEAD`); record the output verbatim. <!-- sdd-owner: implementation -->
- [x] Re-measure the pre-change baseline and record the literal tail: `uv run pytest tests/ -q` (expect ≈ `1478 passed, 6 skipped`; `openspec/config.yaml` + AGENTS.md §6 quote stale counts — compare like-for-like). <!-- sdd-owner: implementation -->
- [x] Re-measure the pre-change quality gates clean: `uv run ruff check src/ tests/`, `uv run ruff format --check`, `uv run mypy src/`, `git diff --check`; record output. <!-- sdd-owner: implementation -->
- [x] Confirm the edit anchors and the exact-key-set safety (read-only): envelope return `src/sofer/mcp_server.py:1800-1813`, phrase read `:2756-2767`, `output_schema` `:2507-2523`, lifecycle globals `:284-285`, imports `:52-101`; grep `set(envelope)`, `.keys() ==`, `== set(` in `tests/test_mcp_*.py` — this phase's read-only pass found ONLY tool-name sets (`tests/test_mcp_schema.py:65`, `:221`) and a subset check (`:377` `guidance_keys <= set(envelope["hints"])`), i.e. **no exact-key-set assertion on any envelope**; re-run in this task and record. <!-- sdd-owner: implementation -->

## Phase 1 — Implementation: `src/sofer/mcp_server.py` (additive, D1–D9)

- [x] Imports (D1): add `from datetime import datetime, timedelta, timezone` and `from ._version import get_version` in the `:52-101` block; no dependency, no `pyproject.toml` change; confirm `_version.py` imports only `importlib.metadata` (no cycle). <!-- sdd-owner: implementation -->
- [x] Add `_last_started_at: str | None = None` and the `_next_started_at() -> str` helper (D3) in the server-state section **before** the posture globals: ISO-8601 UTC `timespec="microseconds"`, 1 µs monotonic bump when `stamp <= _last_started_at`, `global _last_started_at`; docstring states the format rationale (fixed width + constant `+00:00` keeps lexicographic == chronological) and the Windows/CPython 3.10 clock-granularity reason. <!-- sdd-owner: implementation -->
- [x] Add `_PhraseSource = Literal["env", "explicit", "none"]` and the pure helper `_resolve_approval_phrase(explicit: str | None) -> tuple[str | None, _PhraseSource]` (D4): exactly one env read via `_APPROVAL_PHRASE_ENV_VAR` (not the inline literal), precedence explicit > env > none, blank/whitespace ⇒ `(None, "none")`, blank explicit never falls back to env; docstring documents precedence, fail-closed behavior, and the read-once contract. <!-- sdd-owner: implementation -->
- [x] Add the four never-`None` posture globals (D2) next to `_SERVER_ROOT`/`_APPROVAL_PHRASE` (`:284-285`) **after** 1.2/1.3 so the module defaults are callable at import: `_PHRASE_SOURCE: _PhraseSource = "none"`, `_SERVER_PROCESS_ID: int = os.getpid()`, `_SERVER_STARTED_AT: str = _next_started_at()`, `_SERVER_VERSION: str = get_version()`, with the posture-state comment. <!-- sdd-owner: implementation -->
- [x] `build_server` (D5, `:2722-2767`): extend the `global` statement with the 4 new names; replace the inline phrase read with `_APPROVAL_PHRASE, _PHRASE_SOURCE = _resolve_approval_phrase(approval_phrase)`; capture `_SERVER_PROCESS_ID = os.getpid()`, `_SERVER_STARTED_AT = _next_started_at()`, `_SERVER_VERSION = get_version()` **before** `_FastMCP(...)`/`_register_tools`; extend the one-server-per-process warning block (`:2725-2736`) to name the 4 globals; extend the docstring with the posture-capture + read-once/restart contract. No new lock, no `_reload_tool_config` touch. Behavior of the existing blank-env path must be byte-equivalent. <!-- sdd-owner: implementation -->
- [x] Envelope (D6, `:1800-1813`): insert the 4 additive fields after `"requires_approval_phrase"`, reading the globals only — **never `os.environ`**; `ok`/`exit_code`/`hints`/`next`/`config_errors` semantics untouched; `approval_configured = _APPROVAL_PHRASE is not None` at `:1776` unchanged (keeps the `"none"` ⟺ `False` invariant). <!-- sdd-owner: implementation -->
- [x] Tool docstring (D7, `sofer_auth_status` at `:1716`): document the 4 fields with types/domains, the `phrase_source` precedence prose, capture-once-at-`build_server` + never-re-derived contract, `server_process_id` process-scoped, `server_started_at` as the restart-proof signal, `server_version` non-empty/never raises, the never-leak extension, and the APX-01 guidance pointer (unchanged). <!-- sdd-owner: implementation -->
- [x] `output_schema` (D8, `:2507-2523`): add the 4 additive properties after `"requires_approval_phrase"` with the domain prose (`phrase_source`/`server_started_at`/`server_version` `"string"`, `server_process_id` `"integer"`); `required` stays exactly `["ok", "exit_code", "output"]`; **no `enum`**; no other tool's schema touched. <!-- sdd-owner: implementation -->
- [x] Module docstring security bullet (D9, `:24-49`): extend the never-leak/fail-closed list to name the 4 posture fields as non-secret process-lifecycle metadata whose `phrase_source` describes the configuration path only. <!-- sdd-owner: implementation -->
- [x] **#144 non-regression gate (byte-intact pins)**: `git diff -U0 -- src/sofer/mcp_server.py` shows hunks ONLY in the D1–D9 regions; no hunk touches `_approval_phrase_guidance_hints`, the `_APPROVAL_PHRASE_*` fact constants (`:185-245`), `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`, `sofer_publish_confirm` (`:1255-1273`), or the roster. <!-- sdd-owner: implementation -->
- [x] **Anti-ADDED-spec gate**: `grep -n "^## ADDED\|^## REMOVED" openspec/changes/2026-09-11-fix-auth-status-posture/specs/mcp-server/spec.md` returns empty, and the delta contains no APX-01 requirement body (APX-01 exists only in canonical `openspec/specs/mcp-server/spec.md:434+`, untouched — verify `git status`/`git diff` shows no canonical spec edit). <!-- sdd-owner: implementation -->
- [x] Focused pre-test smoke: `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` is green with the unchanged pre-change counts (proves D4's refactor is behavior-preserving before new tests land). <!-- sdd-owner: implementation -->

## Phase 2 — Tests

Reuses `_make_dataset` / `restore_tool_config` / `_call` / `mcp_payload`. Every `none`/`blank`
case MUST `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)` so an ambient shell
variable cannot flake CI; env cases `setenv` a fixed value.

- [x] Create `TestAuthStatusPosture` in `tests/test_mcp_server.py` (after `TestAuthStatusValidity` area, before `TestNoSilentDefault` at `:590`) with the module-level test imports needed (`os`, `from sofer._version import get_version`, `import sofer.mcp_server as ms`) and no edits to existing test bodies. <!-- sdd-owner: implementation -->
- [x] `test_posture_fields_present_and_typed` — `approval_phrase="phrase123"`; envelope carries `phrase_source` (str ∈ domain), `server_process_id` (int), `server_started_at` (str matching ISO-8601 UTC `+00:00` with 6-digit µs), `server_version` (non-empty str). <!-- sdd-owner: implementation -->
- [x] `test_server_version_equals_get_version` — asserts `envelope["server_version"] == ms._SERVER_VERSION == get_version()` (equality, never a literal). <!-- sdd-owner: implementation -->
- [x] `test_posture_fields_confined_to_auth_status` — roster-wide scan: no other tool's envelope or `output_schema.properties` gains any of the 4 keys; roster stays 14 callables. <!-- sdd-owner: implementation -->
- [x] `test_phrase_source_explicit` — `approval_phrase="x"` ⇒ `"explicit"`, `approval_configured is True`. <!-- sdd-owner: implementation -->
- [x] `test_phrase_source_env` — no arg + `SOFER_MCP_APPROVAL_PHRASE="x"` ⇒ `"env"`, `approval_configured is True`. <!-- sdd-owner: implementation -->
- [x] `test_phrase_source_none` — no arg + `delenv` ⇒ `"none"`, `approval_configured is False`. <!-- sdd-owner: implementation -->
- [x] `test_phrase_source_blank_env_is_none` — no arg + env `""` and whitespace-only ⇒ `"none"` (fail-closed). <!-- sdd-owner: implementation -->
- [x] `test_phrase_source_blank_explicit_beats_env` — `approval_phrase=""` while env set ⇒ `"none"` (no env fallback), `approval_configured is False`. <!-- sdd-owner: implementation -->
- [x] `test_phrase_source_consistent_with_approval_configured` — invariant `phrase_source == "none"` ⟺ `approval_configured is False` across all five configuration paths, including a direct call with no `build_server` (module default `"none"`). <!-- sdd-owner: implementation -->
- [x] `test_server_started_at_differs_across_builds` — two back-to-back `build_server()` calls: second `server_started_at` differs AND is strictly greater (lexicographic compare); `phrase_source` reflects each build's own config path (µs + monotonic bump; never asserts pid drift). <!-- sdd-owner: implementation -->
- [x] `test_server_process_id_is_host_pid` — `server_process_id == os.getpid()` in both envelopes and identical across the two builds; explicit comment that pid is process-scoped and MUST NOT be asserted to differ. <!-- sdd-owner: implementation -->
- [x] Extend `tests/test_mcp_schema.py::TestOutputSchema::test_output_schema_typed` (`:233`) additively: for `sofer_auth_status` only, the 4 properties are declared with the correct types; the `required == ["ok","exit_code","output"]` assertion stays exactly as-is. <!-- sdd-owner: implementation -->
- [x] Extend `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` (`:307`) additively: scan the serialized envelope including the 4 posture fields for phrase material (`"phrase123"` absent, no hash/length/probe key), assert `phrase_source ∈ {"env","explicit","none"}`; existing assertions untouched. <!-- sdd-owner: implementation -->
- [x] Extend `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured` (`:343`) additively: assert `envelope["phrase_source"] == "none"`; existing guidance assertions (incl. `:371-379`) untouched, never relaxed. <!-- sdd-owner: implementation -->
- [x] Focused run green: `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` — new tests pass and every pre-existing pin in both files is unmodified; record the tail. <!-- sdd-owner: implementation -->

## Phase 3 — Verification evidence

- [x] Full suite: `uv run pytest tests/ -q` — record the literal tail and the delta vs. task 0.2 (expect ≈ `1489 passed, 6 skipped`); no test removed, relaxed, or skipped. <!-- sdd-owner: implementation -->
- [x] Quality gates: `uv run ruff check src/ tests/`, `uv run ruff format --check`, `uv run mypy src/` — all clean (AGENTS.md §5); never commit with `--no-verify`. <!-- sdd-owner: implementation -->
- [x] Diff hygiene: `git diff --check` clean; `git diff --name-only` shows exactly `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `tests/test_mcp_schema.py` + the `openspec/changes/2026-09-11-fix-auth-status-posture/**` change root — nothing on the Scope Guards list. <!-- sdd-owner: implementation -->
- [x] Spec-scenario → test map (AGENTS.md §6): each of the 6 delta scenarios (10.8 base + posture present/schema, precedence, restart-proof, process-scoped, no-phrase-material) has at least one named passing test from the spec's `*Tests:*` rows; record the map table as PR evidence. <!-- sdd-owner: implementation -->
- [x] #144 pin re-verification on the final diff: `git diff` contains no hunks in `TestHintContentActionable` (`tests/test_mcp_server.py:258-402`), `TestNextHintContract._is_flat_hint_dict` (`:215`), `test_no_phrase_configured_refuses_fail_closed` (`:895`), `test_blank_phrase_treated_as_unconfigured` (`:943`), `TestApprovalNotConfiguredMessage` (`:979-1055`, incl. `test_publish_refusal_hints_unchanged_exact_dict` `:1031` and `test_approval_phrase_facts_not_drifted_between_hints_and_message` `:1040`), `TestAuthStatusValidity` (`:465`), `TestToolRoster::test_exactly_fourteen_callables` (`:421`); canonical APX-01 untouched (delta has no `## ADDED`/`## REMOVED`). <!-- sdd-owner: implementation -->
- [x] Budget check: `git diff --stat` total changed code lines within the forecast (~380–430); if over ~450 or scope creep appeared, STOP and surface the delivery decision instead of committing. <!-- sdd-owner: implementation -->

## Phase 4 — Parent lifecycle (commit + PR #2)

- [ ] 4.1 Parent: split the work into reviewable commits on `fix/145-auth-status-posture` (e.g. `feat(mcp): capture posture state in build_server` → `feat(mcp): expose posture fields on sofer_auth_status` → `test(mcp): cover auth status posture fields`) keeping tests with code; pre-commit ruff+mypy must pass; no commit to `main`/`dev`. <!-- sdd-owner: parent -->
- [ ] 4.2 Parent: open PR #2 (`fix/145-auth-status-posture` → `dev`) using `.github/PULL_REQUEST_TEMPLATE.md` with REAL verification output (full pytest tail, ruff, mypy, `git diff --check`), the SDD artifacts section (proposal/spec/design/tasks paths + the 3.4 scenario→test map), and this change's Review Workload Forecast; explicit note: no tag, no release, no version bump. <!-- sdd-owner: parent -->
- [ ] 4.3 Parent: start or reuse the bounded review for the PR diff and only then hand the merge decision to the human (`gh pr merge` is human-authorized); confirm the merge target is `dev`. <!-- sdd-owner: parent -->

---

## Dependency Order

0.1 → 0.2/0.3/0.4 → 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6/1.7/1.8/1.9 (independent, same file) →
1.10/1.11 → 1.12 → 2.1 → 2.2…2.12 (independent) → 2.13…2.15 → 2.16 → 3.1…3.6 → 4.1 → 4.2 → 4.3.

## Rollback Boundaries

- Phase 1 only: `git checkout -- src/sofer/mcp_server.py` restores D4's behavior-preserving
  refactor with zero test impact (all new fields additive).
- Phase 2 only: revert `tests/test_mcp_server.py` / `tests/test_mcp_schema.py`; source posture
  fields remain harmless and uncovered.
- Whole change: branch is isolated from `dev`; aborting = close PR #2, no tag/release/version
  state to unwind (hatch-vcs derives from tags).
