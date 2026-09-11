# Proposal: 2026-09-11-fix-auth-status-diagnostics

## Intent

One change, **two issues, one tool** (`sofer_auth_status` in `mcp_server.py`), delivered on a single branch:

- **#144 (bug)** — the `approval_configured:false` hint dead-ends. Today the only hint is `{"action": "configure_approval_phrase"}` with no actionable path: the phrase is read **once** at `build_server` from env/arg and the running server never re-reads env; on Windows a separately-launched shell does not reach the launcher's environment; and `sofer mcp add --agent opencode` forwards no env by default. Wanted: the `hints` payload (and the `PUBLISH_APPROVAL_NOT_CONFIGURED` message) must explain process-start semantics, per-agent setup (opencode launcher env / `environment` object), the restart requirement, and how to verify — plus unit tests covering that content.
- **#145 (enhancement)** — add restart-proof posture fields to the `sofer_auth_status` envelope (NEVER the phrase itself or any value derived from it): `phrase_source` (`"env"|"explicit"|"none"`), `server_process_id` (pid), `server_started_at` (ISO UTC timestamp captured at `build_server`), `server_version` (from `_version.get_version()`). Values must differ across two `build_server()` calls. Documented in the tool docstring; unit tests for the fields and for `phrase_source` values.

## Sources

### Issues
- GitHub #144 (bug, open) — auth_status hint dead-end / no actionable path; no covering tests for hint/message content.
- GitHub #145 (enhancement, open) — restart-proof posture fields on the auth_status envelope.

### Verified current state (re-verified above, not taken on trust)
| Area | Location | Verified |
|------|----------|----------|
| `sofer_auth_status` tool | `src/sofer/mcp_server.py:1609-1701` | Envelope: `ok, exit_code, output, token, confidential, requires_ack_confidential, approval_configured, requires_approval_phrase, next, hints, config_errors`. **No posture fields.** Hint logic L1674-1681: `approval_configured` → `{"approval_phrase": "<from human>"}` else `{"action": "configure_approval_phrase"}` (dead-end). |
| `sofer_auth_status` output_schema | `mcp_server.py:2391-2408` | Typed schema; `next`/`hints` arrive via `_ERROR_ENVELOPE_SCHEMA_FIELDS` splat (L135-141: `error_code, message, next, hints`). The 4 new posture fields MUST be added to this `properties` dict too. |
| `_APPROVAL_PHRASE` read-once | `mcp_server.py:2634-2648` (`build_server`) | `approval_phrase` arg > `os.environ["SOFER_MCP_APPROVAL_PHRASE"]`; blank/whitespace → `None` (fail-closed). Never re-read afterwards. `phrase_source` mapping must mirror this exact precedence. **No `server_started_at` captured today.** |
| `PUBLISH_APPROVAL_NOT_CONFIGURED` | `mcp_server.py:1146-1156` | Message **already** contains "set SOFER_MCP_APPROVAL_PHRASE and restart" — the #144 message ask is *partially* met; gap = per-agent actionable guidance + tests asserting the wording. |
| Version helper | `src/sofer/_version.py` `get_version()` | `importlib.metadata.version("sofer")`, fallback `0.0.0.dev0`, never raises. **Not yet imported** by `mcp_server.py` (verified import block L51-100). `datetime`/`timezone` also not yet imported — new imports required. |
| Spec 10.8 | `openspec/specs/mcp-server/spec.md:420` `### Requirement: Auth status preflight read-only (10.8)` | One scenario ("Preflight without publish"). **ALTERED by this change → REAL spec delta** (fields + scenario rows), matching tests (AGENTS.md §6). |
| Test baseline (correction to #144's "no covering tests") | `tests/test_mcp_server.py`, `tests/test_mcp_schema.py` | Behavioral coverage **exists** for the envelope shape/`ok` semantics: `test_mcp_server.py:241-250` (`next` present), `:321-436` (ok/exit_code/token/`approval_configured`/`requires_approval_phrase`, e.g. `test_approval_not_configured_ok_false` L421); `test_mcp_schema.py:185` (readOnlyHint), `:305` (no leak), `:330`/`:348` (asserts `hints["action"] == "configure_approval_phrase"`); `PUBLISH_APPROVAL_NOT_CONFIGURED` error_code+hints asserted at `test_mcp_server.py:783-784, 820`. What is **not** covered: the message body wording, per-agent guidance content (new), and the new posture fields. |

## Scope

### In Scope
- `sofer_auth_status` envelope + output_schema: add `phrase_source`, `server_process_id`, `server_started_at`, `server_version` (non-secret metadata only).
- `hints` payload when `approval_configured:false`: replace the dead-end `action` with actionable per-agent guidance — process-start semantics, opencode launcher env / `environment` object keys (verified against `mcp_registration.py` at design time), restart requirement, how to verify.
- `PUBLISH_APPROVAL_NOT_CONFIGURED` message: consistent per-agent process-start wording (keep the existing "set … and restart" core, extend to per-agent setup).
- Tool docstring (`sofer_auth_status`) + `build_server` docstring: document posture fields and restart semantics.
- Spec delta: update 10.8 requirement text + extend/add GWT scenario rows.
- Tests: new posture-field + `phrase_source` + hint-guidance + message-wording tests; keep existing envelope tests green.

### Out of Scope
- Changing phrase mechanics — the phrase stays read-once at build; restart is the documented contract (that is the root cause #144 surfaces, not a bug to "fix" by runtime re-read).
- Any phrase value, hash, checksum, or derived signal in the envelope (never — security posture, see Risks).
- Other tools' envelopes, transport/network changes, `<` approvals ladder changes.
- New CLI flags or config keys.
- README.md / README_ES.md: expected **unchanged** (tool-docstring-level change, not user-facing CLI help); if design touches README content, sync both in the same commit (AGENTS.md §13).

## Approach

1. **Posture fields** (in `sofer_auth_status` and its output_schema):
   - `phrase_source`: mirror `build_server` L2634-2648 precedence — `"explicit"` when `approval_phrase` arg was passed non-blank; `"env"` when arg was None and env var non-blank; `"none"` otherwise (incl. blank/whitespace env — consistent with `approval_configured:false`, fail-closed). Needs `phrase_source` recorded on the global at build time alongside `_APPROVAL_PHRASE` (single capture point, never recomputed from runtime env).
   - `server_process_id`: `os.getpid()` captured at `build_server`.
   - `server_started_at`: `datetime.now(timezone.utc).isoformat()` captured at `build_server` (µs resolution → differs across two builds).
   - `server_version`: `_version.get_version()` (add import; never raises).
   - Never include the phrase; tests assert absence + `type`/`value` of each field.
2. **Hints guidance (#144)** — when `approval_configured:false`, `hints` carries structured actionable guidance: `action: "configure_approval_phrase"` kept as the stable action key PLUS guidance keys explaining process-start semantics ("phrase is read once when the MCP server process starts; set `SOFER_MCP_APPROVAL_PHRASE` in the environment of the process that launches `sofer-mcp`, then full restart required") and per-agent setup verified against `mcp_registration.py` (e.g. opencode: launcher env / `environment` object — exact key names verified at design time, per the 2026-09-09 registration change's shapes) + how to verify (`sofer_auth_status` → `approval_configured:true`).
3. **Message (#144)** — `PUBLISH_APPROVAL_NOT_CONFIGURED` wording extended consistently; tests assert the wording.
4. **Docstring** — document the 4 fields, semantics, never-leak note, and restart contract.
5. **Spec delta** — update 10.8 envelope contract (add the 4 fields + never-leak extension), extend the existing "Preflight without publish" scenario and add GWT rows; matching tests per AGENTS.md §6.
6. **Tests** — extend `tests/test_mcp_server.py` (posture fields, phrase_source env/explicit/none via monkeypatch + explicit arg, started_at differs across two `build_server()` calls, version == `get_version()`, hints guidance content, message wording) and `tests/test_mcp_schema.py` (output_schema gains the 4 fields; no-leak test extended to cover the new fields).

## Alternatives

| Alternative | Rejected because |
|-------------|------------------|
| Re-read `SOFER_MCP_APPROVAL_PHRASE` from env on every `sofer_auth_status` call | Breaks the fail-closed server-level invariant and the read-once contract; runtime half-refresh would make `approval_configured` inconsistent with what `sofer_publish_confirm` actually enforces. #144's fix is *process-start semantics*, not runtime refresh. |
| Include a phrase probe (e.g. "is the phrase the literal 'x'?") or any phrase-derived value | Any derived signal is a guessing oracle → rejected on security posture (never leak, never weaken the gate). |
| Add a dedicated `sofer_setup_approval` tool / instruction step | Scope creep for two issues; guidance in `hints` + message + docstring is sufficient and keeps the envelope read-only (10.8 stays `readOnlyHint:true`). |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Phrase leak (field, docstring, tests printing it) | Low | Posture fields carry metadata only; no phrase or derived value; extend `test_auth_status_no_leak` (test_mcp_schema.py:305) to assert the 4 new fields carry no phrase material; keep secrets out of test fixtures. |
| `phrase_source` wrong per env value (blank env vs absent vs explicit) | Med | Single capture point in `build_server` next to `_APPROVAL_PHRASE`; mapping mirrors L2634-2648 exactly (`explicit` > `env` > `none`; blank/whitespace → `none`); dedicated tests for env-set / env-blank / env-absent / explicit-arg / whitespace-only. |
| opencode hint inaccurate (launcher env vs `environment` object vs what `sofer mcp add` forwards) | Med | Design-time re-verification against `mcp_registration.py` (2026-09-09 registration shapes: `env_vars` vs `env` no-inheritance gotchas); hint names exact keys only after verification; if shape is client-version-dependent, phrase guidance generically + point to `sofer mcp add --agent opencode` env forwarding. |
| Windows restart semantics misstated | Med | Hint states the phrase is read once at server start and must be set in the *launcher's* environment, then full restart; never "export in a terminal then re-call" (a separately-launched shell does not reach the server process). |
| Existing envelope/schema tests break on added fields | Low | Current asserts are partial-key (`ok`/`exit_code`/`token`/`approval_configured`/`requires_approval_phrase`/`hints["action"]`) — additive fields are safe; only exact-dict schema asserts need review (verify output_schema tests around test_mcp_schema.py:321 before finalizing). |
| Spec over-promises pid "differs across two build_server() calls" | Med | Same OS process shares `os.getpid()` — the differ-across-builds guarantee is carried by `server_started_at` (µs) and `phrase_source`; spec/test wording: pid equals the pid of the process hosting the server; historical builds in separate processes differ. |

## Success Criteria

Mapped to **both** issues' acceptance criteria.

**#144 (bug — hint dead-end, actionable path):**
- [ ] `sofer_auth_status` with `approval_configured:false` returns a `hints` payload that explains process-start semantics (phrase read once at server start; set `SOFER_MCP_APPROVAL_PHRASE` in the launching process; restart required) + per-agent setup (opencode launcher env / `environment` object with design-verified key names) + how to verify (`approval_configured:true` after restart) — no dead-end action-only hint.
- [ ] `PUBLISH_APPROVAL_NOT_CONFIGURED` message covers the same process-start semantics consistently.
- [ ] Unit tests cover the hint payload content and the message wording (currently missing).

**#145 (enhancement — restart-proof posture):**
- [ ] Envelope (and output_schema) exposes `phrase_source`, `server_process_id`, `server_started_at`, `server_version`.
- [ ] `phrase_source` ∈ `{"env","explicit","none"}` and maps correctly per configuration path (explicit arg > env > none; blank/whitespace → `none`).
- [ ] `server_started_at` (ISO UTC, captured at `build_server`) differs across two `build_server()` calls; `phrase_source` reflects each call's path; `server_process_id` equals the hosting process pid.
- [ ] `server_version == _version.get_version()` (non-empty, never raises).
- [ ] The phrase (or any value derived from it) never appears in the envelope — no-leak test extended to the new fields.
- [ ] Tool docstring documents the 4 fields + restart semantics.
- [ ] Spec 10.8 updated (fields + scenarios) with matching tests (AGENTS.md §6).

**Delivery-wide:**
- [ ] Full `uv run pytest tests/ -q` green before/after (baseline re-verified at apply; user-reported 1468 collected / 6 skipped at 2026-09-11 — AGENTS.md §6 quotes 1149/2, re-verify); `uv run mypy src/` clean; PR uses `.github/PULL_REQUEST_TEMPLATE.md` with real verification output and SDD artifacts section.

## Spec Delta Statement

**CONFIRMED: REAL delta, not no-delta.** `openspec/specs/mcp-server/spec.md` 10.8 (L420, "Auth status preflight read-only", added by archived `mcp-dx-audit-surface`) MUST be modified:

- Requirement text: extend the envelope contract with `phrase_source` (`"env"|"explicit"|"none"`, explicit > env > none, blank/whitespace → `"none"`), `server_process_id`, `server_started_at` (ISO UTC captured at `build_server`), `server_version`; add the never-leak extension (no phrase or phrase-derived value); document restart semantics (phrase read once at server start).
- Scenario rows: extend the existing "Preflight without publish" scenario and add GWT rows:
  1. Posture fields present and restart-proof (values differ across two `build_server()` calls — `started_at`/`phrase_source` within one process; pid process-scoped).
  2. `phrase_source` per configuration path (explicit arg / env set / env blank-whitespace / env absent).
  3. No phrase or derived value in envelope.
- Matching tests for every added/changed row (AGENTS.md §6: every spec scenario has a corresponding test). Delta lands at `openspec/changes/2026-09-11-fix-auth-status-diagnostics/specs/mcp-server/spec.md` during the spec phase and is merged into the live spec.

## Dependencies

- `src/sofer/mcp_server.py` (tool + `build_server` + message), `src/sofer/_version.py` `get_version()` (new import), `src/sofer/mcp_registration.py` per-agent env shapes (opencode hint accuracy — re-verify 2026-09-09 shapes before spec), `openspec/specs/mcp-server/spec.md` 10.8.
- Test fixtures: `_make_dataset`, `restore_tool_config`, `_call` (tests/conftest.py + test modules).
- No new dependencies; `datetime`/`timezone` and `_version` import additions only.

## Delivery Note

- Branch `fix/144-145-auth-status-diagnostics` (already created, base `dev`). **PR-only**: commits land on this branch, merged via PR into `dev`; never commit directly to `main`/`dev`; no tag, no release, no version bump (hatch-vcs derives version from tags — untouched).
- GitHub self-approve is impossible for the owner's own PR — user authorizes merge via `gh pr merge` after review.
- Baseline: full `uv run pytest tests/ -q` green; user-reported 1468/6 (re-verify at apply). Pre-commit runs ruff + mypy; push `uv run mypy src/` clean.
- Success criteria above are the PR's acceptance checklist; PR template every section filled with actual command output; SDD artifacts section mandatory.

## Assumptions Requiring Review (proposal question round)

Auto execution mode — these assumptions are baked into the proposal above and need explicit user sign-off (or correction) before the spec phase:

1. **No README/ES change** — this is a tool-docstring + envelope change, not a user-facing CLI/README heading change (to date `sofer_auth_status` is not documented in README). If the repo convention is that envelope contract changes always touch README, say so and I'll add both files in one commit.
2. **Hint key shape for opencode** — proposal keeps `action: "configure_approval_phrase"` as a stable key and adds guidance keys whose exact per-agent names are verified against `mcp_registration.py` at design time; not invented in the proposal.
3. **`server_process_id` semantics** — within one OS process two `build_server()` calls share the pid; the "differ across builds" acceptance is carried by `server_started_at` (µs) and `phrase_source`. Cross-process builds differ in pid. If you want a stronger per-build identity (e.g. a build counter), that changes #145's field contract — flag it.
4. **No new config key or CLI flag** for the phrase — the read-once contract + restart guidance is the fix; no runtime re-read.

---
*Branch: `fix/144-145-auth-status-diagnostics` (single PR → `dev`). Change persists to `openspec/changes/2026-09-11-fix-auth-status-diagnostics/` per artifact-store contract.*