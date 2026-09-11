# Proposal: restart-proof posture fields on `sofer_auth_status` (issue #145)

## Intent

Issue **#145 (enhancement, OPEN)**: during repeated "configure again / probá de nuevo" rounds the user could not tell whether the MCP server had actually been restarted — `approval_configured` is a binary flag with no provenance, and a stale process is indistinguishable from a freshly restarted one. Root cause (as stated in the issue): `sofer_auth_status` returns only `approval_configured: bool`; there is no server-side evidence of process identity or start time, so re-testing after a claimed restart is unverifiable.

This change adds **restart-proof posture fields** to the `sofer_auth_status` envelope (NEVER the phrase itself or any value derived from it):

- `phrase_source` — `"env" | "explicit" | "none"`, the configuration path that produced `_APPROVAL_PHRASE`;
- `server_process_id` — current pid (`os.getpid()`) of the hosting process;
- `server_started_at` — ISO-8601 UTC timestamp captured at `build_server` time;
- `server_version` — package version from installed metadata (`_version.get_version()`).

After a real restart `server_started_at`/`server_process_id` change — observable, verifiable proof for both the agent and the human. This is **PR #2** of the auth_status split; sibling **#144 (hints/guidance) is MERGED** (PR #158, `cf27584`) and is **untouched** by this change.

## Sources

### Issue
- GitHub #145 (enhancement, open) — restart-proof posture fields on the `sofer_auth_status` envelope.
- Acceptance criteria (verbatim intent): fields present in the envelope and documented in its docstring; values differ across two `build_server()` calls (different process identity); unit tests cover the fields and `phrase_source` values. Files: `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`.

### Verified current state (post-#144, re-verified in this session — not taken on trust)
| Area | Location | Verified |
|------|----------|----------|
| `sofer_auth_status` tool | `src/sofer/mcp_server.py:1716`; envelope return `:1800-1813`; `approval_configured = _APPROVAL_PHRASE is not None` `:1776` | Envelope: `ok, exit_code, output, token, confidential, requires_ack_confidential, approval_configured, requires_approval_phrase, next, hints, config_errors`. **No posture fields.** `hints`/`next` already carry the #144 APX-01 payload (`_approval_phrase_guidance_hints()` merged at `:1786`). |
| `sofer_auth_status` output_schema | `mcp_server.py:2507-2523` (properties `:2511-2520`, `required` `:2523`) | Typed properties; `hints`/`next` splatted via `_ERROR_ENVELOPE_SCHEMA_FIELDS` (`:132-141`). The 4 new posture fields MUST be added here too (additive, not in `required`, no `enum` — file precedent). |
| `build_server` | `mcp_server.py:2756`; one-server-per-process warning `:2725-2736`; inline env read `:2761-2767` | `approval_phrase` arg > `os.environ["SOFER_MCP_APPROVAL_PHRASE"]`; blank/whitespace → `None` (fail-closed). **No `server_started_at`/pid captured today.** `phrase_source` MUST mirror this single read. |
| #144 module constants | `mcp_server.py:185-204` (`_APPROVAL_PHRASE_ENV_VAR`, `_APPROVAL_PHRASE_ACTION`, `_PHRASE_READ_ONCE_FACT`, `_PHRASE_LAUNCH_ENV_FACT`, `_PHRASE_RESTART_FACT`, `_PHRASE_VERIFY_FACT`); `:210-222` (`_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`); `:225-245` (setup facts + `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`) | Present and canonical — reused, NOT re-authored. |
| Process-lifecycle globals | `mcp_server.py:284-285` (`_SERVER_ROOT`, `_APPROVAL_PHRASE`) | No `_PHRASE_SOURCE`/`_SERVER_*` globals exist yet — all four posture globals are new. |
| Imports | `mcp_server.py:52-101` | `os` present (`:58`), `Literal` present (`:64`). **`datetime`/`timezone` NOT imported**; `_version.get_version` **NOT imported** — both are new imports. `get_version()` is `lru_cache`d and never raises (`src/sofer/_version.py`, fallback `0.0.0.dev0`); it is the same helper `cli.py` uses (package-internal, no circular-import risk — `_version` imports only `importlib.metadata`). |
| Canonical spec 10.8 | `openspec/specs/mcp-server/spec.md:420-432` | Requirement text + 1 scenario ("Preflight without publish"). Envelope declared WITHOUT posture fields. **ALTERED by this change → REAL spec delta (MODIFIED 10.8).** |
| Canonical spec APX-01 | `openspec/specs/mcp-server/spec.md:434+` | Already canonical, "Added by change `2026-09-11-fix-auth-status-hints` (archived 2026-09-11)". The #145 delta MUST compose with it without re-adding or breaking it. |
| Tests (post-#144) | `tests/test_mcp_server.py` | `TestHintContentActionable` `:258` (8 tests, `:298-402`); `TestAuthStatusValidity` `:465` (incl. `test_approval_not_configured_ok_false` `:566`); publish-ladder posture pins: `test_no_phrase_configured_refuses_fail_closed` `:895`, `test_blank_phrase_treated_as_unconfigured` `:943`, `test_publish_approval_not_configured_message_process_start_semantics` `:1014`, `test_publish_refusal_hints_unchanged_exact_dict` `:1031`, `test_approval_phrase_facts_not_drifted_between_hints_and_message` `:1040`; flatness invariant `TestNextHintContract._is_flat_hint_dict` `:215`; helpers `_call` `:84`, `_server_factory` `:153`. |
| Tests (schema) | `tests/test_mcp_schema.py:325-363+` | `test_auth_status_no_leak` and `test_auth_status_approval_not_configured` already extended by #144 (guidance keys, exact-key membership `"approval_phrase" not in hints`, no-phrase-material). These MUST stay green — the #145 delta is additive on top. |
| Baseline | session-supplied | `uv run pytest tests/ -q` ≈ **1478 passed / 6 skipped** post-#144 (re-verify at apply; `openspec/config.yaml` and AGENTS.md §6 quote stale counts — compare like-for-like, report actual numbers in the PR). |

## Scope

### In Scope (issue #145 ONLY — posture fields)
- `sofer_auth_status` envelope + `output_schema`: add `phrase_source`, `server_process_id`, `server_started_at`, `server_version` (non-secret metadata only).
- A `phrase_source` capture in `build_server` that **mirrors the existing single phrase read** (arg > env > none; blank/whitespace → `"none"`; blank explicit NEVER falls back to env).
- `server_started_at` captured at the top of `build_server`; `server_process_id` via `os.getpid()`; `server_version` via `_version.get_version()` (new import).
- Tool docstring (`sofer_auth_status`) + `build_server` docstring + module docstring security bullet: document the 4 posture fields, their types/domains, the read-once contract, and the never-leak extension.
- Spec delta: **MODIFIED** canonical requirement `10.8` (envelope contract + new GWT scenario rows), composed with the already-canonical **APX-01**.
- Tests: new `TestAuthStatusPosture` class + additive extensions to `tests/test_mcp_schema.py` (schema declares the 4 fields; `required` unchanged; no-leak extended). No test is relaxed.

### Out of Scope (hard guards)
- **#144 content**: `hints` guidance payload, `_approval_phrase_guidance_hints`, the `PUBLISH_APPROVAL_NOT_CONFIGURED` message, `_APPROVAL_PHRASE_*` fact constants — all **unchanged** (already canonical).
- `src/sofer/workflow.py` (MSP-R13 `next` registry), `sofer_publish_confirm` gate order, `hints` on any other tool, other tools' envelopes/schemas.
- New MCP tools/resources/prompts (roster must stay at exactly 14 callables — `TestToolRoster::test_exactly_fourteen_callables`), new CLI flags, config keys, or dependencies.
- Any phrase value, hash, checksum, or derived signal in the envelope (never — security posture, see Risks).
- `README.md` / `README_ES.md`, `pyproject.toml`, canonical `openspec/specs/**` (delta lives in this change root and merges at archive), `TRACE.md`, `scratch/**`.
- Runtime re-derivation of `phrase_source` from the environment (read-once contract) and any `enum` on `phrase_source`.
- No tag, no release, no version bump (hatch-vcs derives from tags — untouched).

## Approach

1. **Imports** (`mcp_server.py:52-101`): add `from datetime import datetime, timedelta, timezone` and `from ._version import get_version`. No new dependencies.
2. **Process-lifecycle globals** (next to `_SERVER_ROOT`/`_APPROVAL_PHRASE` at `:284-285`), with valid never-`None` module defaults so a directly-called `sofer_auth_status` without `build_server` still returns a well-typed envelope:
   - `_PHRASE_SOURCE: Literal["env", "explicit", "none"] = "none"` (alias `_PhraseSource`),
   - `_SERVER_PROCESS_ID: int = os.getpid()`,
   - `_SERVER_STARTED_AT: str = _next_started_at()`,
   - `_SERVER_VERSION: str = get_version()`.
3. **`phrase_source` derivation** (design D3, reused from the reference): one pure helper `_resolve_approval_phrase(explicit: str | None) -> tuple[str | None, _PhraseSource]` that performs **exactly one env read** and returns the normalized phrase + its source, replacing the inline read at `build_server:2761-2767`. Precedence:
   | Configuration | `_APPROVAL_PHRASE` | `approval_configured` | `phrase_source` |
   |---|---|---|---|
   | `build_server(approval_phrase="x")` | `"x"` | `True` | `"explicit"` |
   | no arg, `SOFER_MCP_APPROVAL_PHRASE="x"` | `"x"` | `True` | `"env"` |
   | no arg, env absent | `None` | `False` | `"none"` |
   | no arg, env `""` / `"   "` | `None` | `False` | `"none"` |
   | `approval_phrase=""` while env set | `None` | `False` | `"none"` (no env fallback) |
   Invariant pinned by tests: **`phrase_source == "none"` ⟺ `approval_configured is False`**.
4. **`server_started_at` capture** (design D7): `_next_started_at()` returns `datetime.now(timezone.utc).isoformat(timespec="microseconds")` with a **monotonic 1 µs bump** against the previous stamp — Windows/CPython 3.10 clock granularity can return identical `datetime.now()` values for two back-to-back builds, and this is the ONE signal the restart-proof scenario relies on. `timespec="microseconds"` is mandatory (default `"auto"` drops the fraction on whole-µs stamps and emits 3 digits on multiples of 1000, breaking both the µs requirement and the lexicographic ordering).
5. **`build_server`** (`:2756`): capture all four values at the TOP, before `_FastMCP(...)`/`_register_tools`:
   `_APPROVAL_PHRASE, _PHRASE_SOURCE = _resolve_approval_phrase(approval_phrase); _SERVER_PROCESS_ID = os.getpid(); _SERVER_STARTED_AT = _next_started_at(); _SERVER_VERSION = get_version()`. Extend the one-server-per-process warning block (`:2725-2736`) to name the new globals; docstring gains the posture-capture + read-once/restart contract. No new lock; nothing touches `_reload_tool_config` (posture is process-lifecycle state, orthogonal to per-call `[tool.sofer]` reload).
6. **`sofer_auth_status`** (`:1716`): add the 4 envelope fields (reads globals only, never `os.environ` — read-once contract); `hints`/`next`/`ok` semantics untouched. Tool docstring documents the fields with types/domains, the precedence prose, the read-once/restart contract, the never-leak extension, and the APX-01 guidance pointer.
7. **`output_schema["properties"]`** (`:2511-2520`): add 4 additive properties after `requires_approval_phrase`: `phrase_source` (`{"type": "string", "description": domain prose}`), `server_process_id` (`{"type": "integer"}`), `server_started_at` (`{"type": "string"}`), `server_version` (`{"type": "string"}`). `required` stays `["ok", "exit_code", "output"]`; **no `enum`** (no enum precedent in this file; domain asserted in tests + documented in the description).
8. **Module docstring security bullet** (`:24-49`): extend the fail-closed/never-leak list to name the four posture fields (non-secret metadata; `phrase_source` reports the configuration path only).
9. **Spec delta** (spec phase): MODIFIED 10.8 only (see Spec Delta Statement).
10. **Tests**: `TestAuthStatusPosture` in `tests/test_mcp_server.py` (~11 named tests, reusing `_make_dataset`/`restore_tool_config`/`_call`/`mcp_payload`); additive schema extensions in `tests/test_mcp_schema.py` (3 touched tests, all extended never relaxed). Full matrix in the Testing Strategy section of the spec/design; proposal-level list in Success Criteria.

## Alternatives

| Alternative | Rejected because |
|-------------|------------------|
| Re-derive `phrase_source` from `os.environ` at tool-call time | Violates the read-once contract and would misreport posture after an env change — exactly the unverifiability #145 exists to remove; a running server never re-reads the environment. |
| Include a phrase probe or any phrase-derived value (hash, length, boolean comparison) as "proof" of configuration | Any derived signal is a guessing oracle that weakens the fail-closed gate — rejected on security posture (never leak, never weaken). |
| Per-build counter (`build #N`) instead of `server_started_at` | A counter is process-scoped and resets on restart — it carries NO cross-restart signal; `server_started_at` is both the signal and genuinely informative (when this server process was constructed). |
| Add a separate `sofer_server_info` tool for posture | Scope creep; breaks the 14-callable roster invariant and splits preflight onto two surfaces for zero contract gain. |
| Compute `server_process_id` as a per-build unique id (e.g. a counter or uuid) | pid is the honest, well-understood OS identity; a synthetic id adds machinery and still cannot distinguish restarts (ids reset per process). pid is documented as process-scoped (see Risks — pid pitfall). |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Phrase leak** — any posture field or docstring line carrying the phrase or a phrase-derived value | Low | Posture fields carry metadata only; the never-leak clause in canonical 10.8/APX-01 is extended in the delta to name the four fields; `test_auth_status_no_leak` extended to assert the serialized envelope contains no phrase material and `phrase_source ∈ {"env","explicit","none"}`. |
| **pid pitfall** — asserting pid "differs across two `build_server()` calls" (guaranteed-failing test: one OS process shares `os.getpid()`) | High if direction is missed | The restart-proof guarantee is carried by `server_started_at` (µs + monotonic bump ⇒ strictly increasing across builds in one process) and `phrase_source` (differs whenever the builds' configs differ). pid is documented as **process-scoped** in the field description, tool docstring, spec text, and tests (`server_process_id == os.getpid()`, never "differs across builds"). Cross-process builds (real restarts) differ in pid as a matter of OS behavior — documented, not asserted (no subprocess spawning for a diagnostic field). |
| **`phrase_source` fail-closed** — blank env / whitespace-only / blank explicit mislabeled as configured | Med | Single capture point in `build_server` next to `_APPROVAL_PHRASE`; mapping mirrors the existing read exactly; blank always ⇒ `"none"` and `approval_configured:false`; invariant test pins `"none"` ⟺ `approval_configured is False` across all five paths. |
| **Clock granularity** — `datetime.now()` identical for two back-to-back builds (Windows/CPython 3.10) | Med | Fixed-width `timespec="microseconds"` + 1 µs monotonic bump in `_next_started_at()`; lexicographic comparison stays valid (`+00:00` constant offset). |
| **Breaking canonical APX-01** — the #145 delta re-adding or clobbering the already-merged #144 requirement | Low | Spec delta is **MODIFIED 10.8 only** (wholesale new requirement body for 10.8); APX-01 is NOT re-added, NOT touched; compose-by-diff at archive; a spec-phase review greps the delta for `ADDED`/APX-01 absence. |
| **Breaking existing pins** — the #144 hints/message/roster invariants | Low | This change touches neither `hints` nor `sofer_publish_confirm`: `TestHintContentActionable`, flatness invariant, exact-dict `hints == {"action": "configure_approval_phrase"}` (`test_publish_refusal_hints_unchanged_exact_dict`), and the 14-tool roster all stay green **unmodified**. All current auth_status asserts are partial-key — additive fields are safe; schema `required` unchanged. |
| **`server_version` import layering** — `_version` in the server module creating a cycle or breaking the CLI-only convention | Low | `_version.py` imports only `importlib.metadata` (no sofer imports) — no cycle; `cli.py` already consumes `get_version()`; the server gains the same read-only lru_cached call. `server_version` equals `get_version()` non-empty, never raises (test pins the equality, not a literal). |
| **Baseline drift** — quoting a stale test count in the PR | Low | Session-supplied baseline ≈ 1478/6 post-#144; re-verified at apply (task 0.2 equivalent) and the literal tail reported in the PR. |

## Success Criteria

Mapped to issue #145's three acceptance criteria.

**AC1 — Fields present in the envelope and documented in its docstring:**
- [ ] `sofer_auth_status` envelope exposes `phrase_source`, `server_process_id`, `server_started_at`, `server_version`.
- [ ] The 4 fields are declared in `sofer_auth_status`'s `output_schema.properties`; `required` remains `["ok", "exit_code", "output"]`; no `enum`.
- [ ] Tool docstring documents the 4 fields (types/domains), the `phrase_source` precedence, the read-once/restart contract, and the never-leak extension.

**AC2 — Values differ across two `build_server()` calls (different process identity):**
- [ ] `server_started_at` differs AND strictly increases across two `build_server()` calls in one process (µs + monotonic bump); `phrase_source` reflects each build's configuration path.
- [ ] `server_process_id` equals `os.getpid()` in both envelopes — documented process-scoped (never asserted to differ across builds).
- [ ] `server_version == _version.get_version()`, non-empty, never raises.
- [ ] The phrase (or any derived value) never appears anywhere in the envelope — `test_auth_status_no_leak` extended to cover the 4 fields.

**AC3 — Unit tests cover the fields and `phrase_source` values:**
- [ ] `TestAuthStatusPosture` (~11 tests) covers: fields present + typed; `server_version` equals `get_version()`; `started_at` differs/increases across builds; pid is host pid; `phrase_source` explicit / env / none / blank-env-is-none / blank-explicit-beats-env; invariant `"none"` ⟺ `approval_configured is False`; schema declares the fields with `required` unchanged; no-leak extended; scope containment (no other tool gains the 4 fields).
- [ ] Every added spec scenario row has a matching test (AGENTS.md §6); existing auth_status/hints/roster pins stay green **unmodified**.

**Delivery-wide:**
- [ ] Full `uv run pytest tests/ -q` green: baseline (~1478 passed / 6 skipped) + new posture tests, literal tail recorded; `uv run mypy src/`, ruff check + format clean; `git diff --check` clean.
- [ ] PR #2 (`fix/145-auth-status-posture` → `dev`) uses `.github/PULL_REQUEST_TEMPLATE.md` with REAL verification output and the SDD artifacts section (spec-scenario→test map). No tag/release/version bump.

## Spec Delta Statement

**CONFIRMED: REAL delta — MODIFIED `openspec/specs/mcp-server/spec.md` requirement `Auth status preflight read-only (10.8)` (L420-432), AND the canonical file must stay composed with the already-present `Approval-phrase configuration diagnostics (APX-01)` (L434+, from the MERGED #144).**

Delta file to author in the spec phase: `openspec/changes/2026-09-11-fix-auth-status-posture/specs/mcp-server/spec.md`, containing **only** the `## MODIFIED Requirements` section — NO `ADDED`, NO `REMOVED` sections:

- **Requirement body (wholesale replacement of 10.8's text, keeping the original `> Added by change mcp-dx-audit-surface (archived 2026-08-31).` attribution)**:
  - envelope contract grows `phrase_source:"env"|"explicit"|"none"`, `server_process_id:int`, `server_started_at:str`, `server_version:str`;
  - the 4 posture fields with their semantics: `phrase_source` mirrors the single phrase read (explicit > env > none; blank/whitespace → `"none"`; blank explicit never falls back to env); `server_process_id` = `os.getpid()` captured at `build_server`; `server_started_at` = ISO-8601 UTC µs captured at `build_server`, MUST differ across two `build_server()` calls; `server_version` = `_version.get_version()`, non-empty, never raises;
  - read-once contract: `phrase_source` derived once at `build_server` from the same read that resolves the phrase; never re-read at tool-call time; env changes require a restart;
  - NEVER-LEAK extension: the phrase, any phrase-derived value, and the configured env value MUST NEVER appear in any of the four fields or any rendering of the envelope; `phrase_source` describes the configuration path only;
  - a `(Previously: ...)` historical paragraph (the envelope carried no posture metadata; the never-leak clause covered only token/phrase values) — repo convention for MODIFIED requirements.
- **Scenario rows (existing + new GWT)**:
  1. `Preflight without publish` — KEPT unchanged (canonical scenario).
  2. `Posture fields present in envelope and schema` — fields carry `phrase_source` (`"explicit"` for `approval_phrase="phrase123"`), int pid, ISO-8601 UTC `started_at`, `server_version`; schema declares them.
  3. `Posture is restart-proof across server builds` — two `build_server()` calls: `server_started_at` SHALL differ (the restart-proof signal); `server_process_id` SHALL equal the hosting pid in both (process-scoped); `phrase_source` SHALL reflect each build.
  4. `phrase_source follows configuration precedence` — the five-path table ⇒ `explicit`/`env`/`none`/`none`/`none`; blank explicit never falls back.
  5. `No phrase material in the posture fields` — serialized envelope free of `"phrase123"`; the 4 fields carry no derived value.
- **Composition note (critical):** the canonical `spec.md` ALREADY contains APX-01 from #144. The delta for this change MUST NOT re-ADD APX-01 or any #144 content; at archive, merge = 10.8 replaced + everything else (APX-01 included) preserved. A spec-phase self-check greps the delta for an `ADDED` section (must be absent) and for APX-01 (contents must exist only in the canonical file).

## Dependencies

- **Merged #144** (PR #158, `cf27584`): module constants `mcp_server.py:185-245`, `_approval_phrase_guidance_hints` helper (`:824-870`), `TestHintContentActionable` (`tests/test_mcp_server.py:258`), canonical APX-01 (`openspec/specs/mcp-server/spec.md:434+`). The #145 delta composes ON TOP of these; the phrase resolution to mirror lives at `build_server:2761-2767`.
- `src/sofer/_version.py::get_version` (new import; lru_cached, never raises).
- Test fixtures: `_make_dataset`, `restore_tool_config`, `_call` (`tests/conftest.py` + `tests/test_mcp_server.py:84`), `monkeypatch.setenv`/`delenv` for `SOFER_MCP_APPROVAL_PHRASE` (always `delenv` for `none`/`blank` cases so an ambient shell variable cannot flake CI).
- No new dependencies; `datetime`/`timezone` and `_version` import additions only.

## Delivery

- Branch `fix/145-auth-status-posture` (already created, base `dev`; parent-verified). **PR #2 "stacked"** — lands on `dev` AFTER the merged PR #1 (#144); commits target this branch only; never commit directly to `main`/`dev`; no tag, no release, no version bump (hatch-vcs derives version from tags — untouched).
- Review budget: estimated delta well under the 400-line threshold (2 source/test files + 1 delta file; bulk is additive test coverage; no multi-area diff) — no `size:exception` requested, no chaining needed. Delivery strategy `ask-on-risk`: any size overrun or scope creep pauses for a decision.
- Baseline: `uv run pytest tests/ -q` ≈ 1478 passed / 6 skipped (re-verify at apply; report the literal tail and the delta vs. the pre-change measurement). Pre-commit runs ruff + mypy; push `uv run mypy src/` clean; never `git commit --no-verify`.
- PR: `.github/PULL_REQUEST_TEMPLATE.md` filled with ACTUAL command output and the SDD artifacts section (proposal/spec/design/tasks paths + spec-scenario→test map). GitHub self-approve is impossible for the owner's own PR — human authorizes `gh pr merge` after review.

## Proposal Question Round

Auto execution mode — these assumptions are baked into this proposal and need explicit user sign-off (or correction) before the spec phase:

1. **`phrase_source` for a blank explicit argument.** The design note says "'explicit' si el arg es no-None (aunque blank)" — taken strictly, `build_server(approval_phrase="")` with env set would report `"explicit"`. I chose the **reference-D3 semantics**: blank/whitespace explicit ⇒ `"none"` (fail-closed, no env fallback), because the design note also states the invariant **`"none"` ⟺ `approval_configured is False`**, which the strict reading would break (`approval_configured:false` + `phrase_source:"explicit"` would misreport posture — the exact problem #145 fixes). The reference spec scenario pins this row as `"none"`. If you intended explicit-provided-even-blank to win, that changes the invariant, the spec scenario, and `test_phrase_source_consistent_with_approval_configured` — flag it.
2. **`server_started_at` carries the "differs across builds" acceptance, not pid.** `os.getpid()` is constant within one test/process; the monotonic-µs-stamped `server_started_at` is the restart-proof signal (per the pitfall note). A stronger per-build identity (e.g. a build counter) would change #145's field contract — not included.
3. **No README/ES change** — `sofer_auth_status` is an MCP tool description, not CLI help or a README heading; no CLI flag, config key, or `[tool.sofer]` default changes. `AGENTS.md §13` sync does not trigger.
4. **Spec delta is MODIFIED 10.8 only.** It reuses the reference's authored 10.8 delta text but DROPS the reference's ADDED APX-01 section (now canonical from the merged #144) — composition is at archive, and the delta must not duplicate it.
5. **Baseline number**: session-supplied ≈ 1478 passed / 6 skipped post-#144; re-verified at apply and reported from actual output (canonical `config.yaml`/AGENTS.md counts are stale).

---
*Branch: `fix/145-auth-status-posture` (PR #2, stacked on `dev`). Change persists to `openspec/changes/2026-09-11-fix-auth-status-posture/` per artifact-store contract.*