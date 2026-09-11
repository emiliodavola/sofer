# Apply Progress — restart-proof posture fields on `sofer_auth_status` (issue #145)

Change `2026-09-11-fix-auth-status-posture` — PR #2 of the auth_status split, branch
`fix/145-auth-status-posture` (base `dev`; sibling #144 merged at `cf27584`, untouched).
Scope: **issue #145 ONLY** — add `phrase_source`, `server_process_id`, `server_started_at`,
`server_version` to the `sofer_auth_status` envelope + `output_schema`. Additive; the phrase
(and any derived value) NEVER appears in any posture field.

Inputs consumed: `proposal.md`, `specs/mcp-server/spec.md` (delta — `## ADDED`/`## REMOVED`
empty), `design.md` (D1–D9, contracts 1–10, §6 test map, §7 anti-regression gate),
`openspec/config.yaml` (`strict_tdd: false`, `test_command: uv run pytest tests/ -q`).
No previous `apply-progress` existed — this file is created fresh.

## Completed tasks and matching persisted checkbox updates

All 38 implementation-owned tasks are marked `- [x]` in `openspec/changes/2026-09-11-fix-auth-status-posture/tasks.md`
(`grep -c` = 38; `grep "\- \[ \]"` shows only the 3 parent-owned rows `4.1`/`4.2`/`4.3`, preserved
byte-for-byte as deferred lifecycle actions).

- **0.1–0.4** (baseline): `git rev-parse --abbrev-ref HEAD` → `fix/145-auth-status-posture`;
  `git log --oneline -3` → `cf27584 Merge pull request #158 from emiliodavola/fix/144-auth-status-hints`
  (then `358417f`, `e9163e1`); `git merge-base --is-ancestor cf27584 HEAD` → exit 0 (base confirmed).
  Pre-change baseline: `uv run pytest tests/ -q` → **1478 passed, 6 skipped, 13 warnings**.
  Pre-change gates: `ruff check src/ tests/` clean; `ruff format --check` clean at the time;
  `mypy src/` → "Success: no issues found in 32 source files"; `git diff --check` clean.
  Read-only anchor pass confirmed the envelope return, phrase read, `output_schema`, lifecycle
  globals, and imports line ranges, and re-grepped `set(envelope)` / `.keys() ==` / `== set(` in
  `tests/test_mcp_*.py` — only tool-name sets (`test_mcp_schema.py:65`, `:221`) and the subset
  check `guidance_keys <= set(envelope["hints"])` (`:377`); **no exact-key-set assertion on any
  envelope**.
- **1.1** (D1 imports): `from datetime import datetime, timedelta, timezone` + `from ._version import get_version`
  added; `_version.py` imports only `importlib.metadata` (no cycle); no `pyproject.toml` change.
- **1.2** (D3): `_last_started_at: str | None = None` + `_next_started_at()` — ISO-8601 UTC
  `timespec="microseconds"`, 1 µs monotonic bump when `stamp <= _last_started_at`, docstring
  documents the fixed-width/`+00:00` lexicographic==chronological rationale and the
  Windows/CPython 3.10 clock-granularity reason.
- **1.3** (D4): `_PhraseSource = Literal["env", "explicit", "none"]` +
  `_resolve_approval_phrase(explicit)` — one env read via `_APPROVAL_PHRASE_ENV_VAR`,
  precedence explicit > env > none, blank/whitespace ⇒ `(None, "none")`, blank explicit never
  falls back to env; docstring documents precedence + fail-closed + read-once contract.
- **1.4** (D2): four never-`None` posture globals after 1.2/1.3 (`_PHRASE_SOURCE: _PhraseSource = "none"`,
  `_SERVER_PROCESS_ID: int = os.getpid()`, `_SERVER_STARTED_AT: str = _next_started_at()`,
  `_SERVER_VERSION: str = get_version()`) with the posture-state comment.
- **1.5** (D5 `build_server`): `global` extended (two lines: root/phrase/source/pid + started/version);
  inline phrase read replaced by `_APPROVAL_PHRASE, _PHRASE_SOURCE = _resolve_approval_phrase(approval_phrase)`;
  `_SERVER_PROCESS_ID = os.getpid()`, `_SERVER_STARTED_AT = _next_started_at()`,
  `_SERVER_VERSION = get_version()` captured before `_FastMCP(...)`/`_register_tools`; the
  one-server-per-process `.. warning::` names all six globals + capture-once/restart contract;
  docstring's `approval_phrase:` arg notes "resolved exactly once here". No new lock, no
  `_reload_tool_config` touch. Blank-env path is byte-equivalent (proved by 1.12 smoke with
  unchanged counts).
- **1.6** (D6 envelope): 4 additive fields inserted after `"requires_approval_phrase"`, reading
  globals only; `approval_configured = _APPROVAL_PHRASE is not None` untouched (`"none"` ⟺ `False`).
- **1.7** (D7 docstring): posture paragraph documents fields/types/domains, precedence prose,
  capture-once + never-re-derived, pid process-scoped, started_at restart-proof,
  version non-empty/never-raises, never-leak extension, APX-01 pointer. Reflowed to a
  **2-sentence dot-free-identifier** version so `TestDescriptions::test_descriptions_concise_no_msp_untrusted`
  (≤10 fragments before "When to use") stays green with the pre-existing 10-fragment ceiling.
- **1.8** (D8 `output_schema`): 4 additive properties after `"requires_approval_phrase"`
  (`phrase_source`/`server_started_at`/`server_version` `string`, `server_process_id` `integer`),
  domain prose, `required` untouched, no `enum`, only `sofer_auth_status`.
- **1.9** (D9 module docstring): final security bullet names the 4 posture fields as non-secret
  process-lifecycle metadata; `phrase_source` describes the configuration path only.
- **1.10** #144 non-regression gate: `git diff -U0 -- src/sofer/mcp_server.py` hunks ONLY at
  D1–D9 regions: `@@ -49`, `-62`, `-81`, `-287` (D1–D9 globals/imports), `-1737` (D7),
  `-1808` (D6), `-2517` (D8), `-2726/-2745/-2756/-2758` (D5). No hunk touches
  `_approval_phrase_guidance_hints`, the `_APPROVAL_PHRASE_*` fact constants (`:185-245`),
  `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`, `sofer_publish_confirm` (`:1255-1273`), or the roster.
- **1.11** anti-ADDED-spec gate: `grep -n "^## ADDED\|^## REMOVED"` on the delta spec → empty
  (exit 1); `git status --porcelain -- openspec/specs/` → empty (canonical APX-01 untouched).
- **1.12** focused pre-test smoke: `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q`
  → **213 passed, 3 skipped** (unchanged pre-change counts → D4 refactor behavior-preserving).

## Phase 2 — tests

- **2.1** `TestAuthStatusPosture` inserted between `TestAuthStatusValidity` (ends ~`test_approval_not_configured_ok_false`)
  and the `# 7.3` banner (before `TestNoSilentDefault`); module imports extended
  (`import re`, `from datetime import datetime, timedelta, timezone`,
  `from sofer._version import get_version`); zero edits to existing test bodies.
- **2.2** `test_posture_fields_present_and_typed` — `approval_phrase="phrase123"`; envelope carries
  `phrase_source=="explicit"`, int `server_process_id`, ISO-8601 UTC `+00:00` µs `server_started_at`
  (regex `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00`), non-empty str `server_version`.
- **2.3** `test_server_version_equals_get_version` — `envelope["server_version"] == ms._SERVER_VERSION == get_version()`
  (equality only, no literal).
- **2.4** `test_posture_fields_confined_to_auth_status` — roster-wide scan of all 14 tools'
  `outputSchema.properties`: only `sofer_auth_status` gains the 4 keys; roster = 14 callables.
- **2.5–2.9** `phrase_source` precedence: explicit ⇒ `"explicit"`; env ⇒ `"env"`; none (env deleted)
  ⇒ `"none"`; blank/whitespace env ⇒ `"none"` (fail-closed); blank explicit while env set ⇒ `"none"`
  (no env fallback). `delenv("SOFER_MCP_APPROVAL_PHRASE")` in every none/blank case.
- **2.10** `test_phrase_source_consistent_with_approval_configured` — invariant
  `phrase_source == "none"` ⟺ `approval_configured is False` across explicit/env/none/blank-env/
  blank-explicit + a **direct `ms.sofer_auth_status(...)` call with no `build_server`**
  (module default `"none"`; globals reset: `_APPROVAL_PHRASE=None`, `_PHRASE_SOURCE="none"`,
  `_SERVER_ROOT=tmp_path`).
- **2.11** `test_server_started_at_differs_across_builds` — first envelope captured BEFORE second
  `build_server()`; second stamp differs AND is strictly greater (lexicographic, µs + monotonic
  bump); each build's `phrase_source` reflects its own config path ("none" then "explicit");
  **no pid-drift assertion**.
- **2.12** `test_server_process_id_is_host_pid` — `server_process_id == os.getpid()` in both
  envelopes and identical across builds; explicit comment: pid is process-scoped and MUST NOT be
  asserted to differ.
- **2.13** `test_mcp_schema.py::TestOutputSchema::test_output_schema_typed` extended additively:
  for `sofer_auth_status` only, the 4 properties declared with correct types (`string`/`integer`),
  no `enum`, and `required == ["ok", "exit_code", "output"]` (the pre-existing init `required`
  assertion untouched).
- **2.14** `test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` extended additively:
  `phrase_source ∈ {"env","explicit","none"}`; serialized envelope (posture fields included)
  carries no `"phrase123"`, no hash/length/probe key; existing assertions untouched.
- **2.15** `test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured` extended
  additively: `envelope["phrase_source"] == "none"`; all guidance assertions (incl. `:371-379`)
  untouched, never relaxed.
- **2.16** focused run: `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` →
  **224 passed, 3 skipped** (213 + 11 new; every pre-existing pin unmodified).

## Phase 3 — verification evidence (command output)

- **3.1** `uv run pytest tests/ -q` → **`1489 passed, 6 skipped, 13 warnings in 57.09s`**
  (delta vs baseline +11 passed, 0 skipped; no test removed, relaxed, or skipped).
  `uv run pytest tests/test_mcp_server.py::TestAuthStatusPosture -q` → **11 passed in 1.12s**.
- **3.2** `uv run ruff check src/ tests/` → **All checks passed!**
  `uv run ruff format --check` → 74 files already formatted; **`README.md` and `README_ES.md`
  reported as "would be reformatted" — pre-existing drift, byte-identical to HEAD (verified:
  `git show HEAD:README.md | ruff format --check` exit 1, `cmp` identical), and both are on the
  Scope Guards no-touch list, so NOT touched. Scoped format check on the 3 changed files:
  **3 files already formatted**. `uv run mypy src/` → **Success: no issues found in 32 source
  files**. `git diff --check` → clean.
- **3.3** `git diff --check` clean; `git status --porcelain` → exactly
  `M src/sofer/mcp_server.py`, `M tests/test_mcp_server.py`, `M tests/test_mcp_schema.py`,
  `?? openspec/changes/2026-09-11-fix-auth-status-posture/` — nothing on the Scope Guards list.
- **3.4** scenario→test map (all 6 delta scenarios covered by passing tests, AGENTS.md §6):
  | Delta scenario | Tests |
  |---|---|
  | 10.8 base + preflight without publish | `TestAuthStatusValidity::test_missing_token_ok_false`, `test_approval_not_configured_ok_false`, `TestEnvelope::test_auth_status_no_leak` (pins, unmodified) |
  | Posture fields present in envelope and schema | `test_posture_fields_present_and_typed`, `test_server_version_equals_get_version`, `test_posture_fields_confined_to_auth_status`, extended `test_output_schema_typed` |
  | phrase_source precedence | `test_phrase_source_explicit` / `_env` / `_none` / `_blank_env_is_none` / `_blank_explicit_beats_env` / `_consistent_with_approval_configured` |
  | restart-proof started_at | `test_server_started_at_differs_across_builds` |
  | process-scoped pid | `test_server_process_id_is_host_pid` |
  | No phrase material in posture fields | extended `test_auth_status_no_leak` |
- **3.5** #144 pin re-verification on the final diff: `git diff -U0 -- tests/test_mcp_server.py`
  hunks = imports (`+17`, `+33`) + `@@ -584,0 +587,206 @@` (new class AFTER `TestAuthStatusValidity`,
  before the `7.3` banner) — no hunks in `TestHintContentActionable` (`258-402`),
  `TestNextHintContract._is_flat_hint_dict` (`215`), `test_no_phrase_configured_refuses_fail_closed`
  (`895`), `test_blank_phrase_treated_as_unconfigured` (`943`), `TestApprovalNotConfiguredMessage`
  (`979-1055`, incl. `:1031` and `:1040`), `TestAuthStatusValidity` (`465`), or
  `TestToolRoster::test_exactly_fourteen_callables` (`421`). `git diff -U0 -- tests/test_mcp_schema.py`
  hunks only at `246` (`TestOutputSchema`) and `355`/`408` (`TestEnvelope`) — additive only.
  Canonical APX-01 untouched (delta has no `## ADDED`/`## REMOVED`).
- **3.6** budget: `git diff --stat` → `3 files changed, 374 insertions(+), 32 deletions(-)`
  = **406 changed code lines** — within the ~380–430 forecast, under the ~450 ask-on-risk gate;
  no scope creep (single concern, 3 code files).

## Deviations from design

1. **`global (...)` is invalid Python syntax** — the design's D5 snippet used a parenthesized
   multi-name `global` statement, which does not parse. Implemented as two single-line
   `global _SERVER_ROOT, _APPROVAL_PHRASE, _PHRASE_SOURCE, _SERVER_PROCESS_ID` +
   `global _SERVER_STARTED_AT, _SERVER_VERSION` (E501 noqa'd in this file). Logic identical.
2. **D7 docstring length vs the ≤10-sentence DX guard** — the design's full-length posture
   paragraph pushed `sofer_auth_status`'s pre-"When to use" fragment count to 15 (> 10 allowed by
   `TestDescriptions::test_descriptions_concise_no_msp_untrusted`, an existing pin). Compressed to
   a 2-fragment dot-free-identifier paragraph (merged the two hinted/unconfigured sentences) that
   preserves all documented facts (types/domains, precedence, capture-once, restart-proof,
   process-scoped, never-leak + APX-01 pointer). Envelope/schema/source behavior unchanged.
3. **`ruff format --check` full-tree drift** — flags `README.md`/`README_ES.md` as needing
   reformatting. Pre-existing (byte-identical to HEAD at `cf27584`; exit 1 on HEAD content too) and
   out of scope (Scope Guards no-touch). All changed files pass the formatter.
4. Test placement used the class-insertion point from the design (after `TestAuthStatusValidity`,
   before the `7.3` banner); actual anchor lines shifted (+62 source lines from D1–D4 insertions),
   so the tasks.md line references were resolved against the live file.

## Remaining implementation tasks

None — all 38 implementation-owned tasks are checked `- [x]` in the persisted tasks artifact.

## Workload / PR boundary

Single PR #2 (`fix/145-auth-status-posture` → `dev`), per the Review Workload Forecast
(Decision needed before apply: No; Chained PRs recommended: No; 400-line budget risk: Low).
`git diff --stat` = 406 changed lines (additive; ~120 source + ~238 server tests + ~30 schema
tests + change-root artifacts in `openspec/changes/...`, review-light).

## Structured status consumed

`applyState: ready` (authoritative openspec store); `dependencies: apply ready, verify/sync/archive
blocked until this phase returns`; `actionContext: repo-local`, allowedEditRoots
`["C:\\Users\\elaze\\Desktop\\sofer"]` — all edits within root; no warnings. Delivery strategy
`ask-on-risk`: budget stayed under ~450, so the default single-pr path holds with no pause.
Always ask before any commit/push (not performed; `git status` left working-tree dirty for the
parent's commit phase).

## Notes for verify / parent

- Verification commands to reproduce: `uv run pytest tests/ -q` (1489 passed, 6 skipped),
  `uv run ruff check src/ tests/`, `uv run mypy src/`, `git diff --check`, scoped
  `uv run ruff format --check src/sofer/mcp_server.py tests/test_mcp_server.py tests/test_mcp_schema.py`.
- Parent lifecycle (4.1–4.3) remains: split commits, open PR #2 against `dev`, bounded review then
  human-authorized merge. No tag, no release, no version bump.