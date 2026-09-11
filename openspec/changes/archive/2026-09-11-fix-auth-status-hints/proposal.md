# Proposal: 2026-09-11-fix-auth-status-hints

**Change:** `2026-09-11-fix-auth-status-hints` · **Branch:** `fix/144-auth-status-hints` (base `dev`, PR-only)
**Scope: GitHub ISSUE #144 ONLY** — PR #1 of 2 in the split auth-status diagnostics delivery. The sibling change (`2026-09-11-fix-auth-status-diagnostics` posture fields, issue #145) is **explicitly NOT here**; it lands later on `fix/145-auth-status-posture`, stacked after this PR.

## Intent

**Issue #144 (bug, open): `sofer_auth_status` hint dead-ends when the approval phrase is not configured.** With `approval_configured:false` the only hint today is `{"action": "configure_approval_phrase"}` — a dead end with no actionable path. The root cause is process-start semantics, not hint wording: the phrase is read **exactly once** at `build_server` (`src/sofer/mcp_server.py:2638-2652`) and the running server never re-reads the environment; on Windows a separately-launched shell does not reach the launcher's environment; and `sofer mcp add --agent opencode` (`mcp_registration.py:158-159`) forwards **no environment** at all. Telling a user "configure the approval phrase" without saying *where the variable must live, that a restart is mandatory, and how per-agent registration actually forwards env* leaves them stuck.

The issue's acceptance criteria (this change's success contract):

1. With `approval_configured:false`, `hints` includes an **actionable per-agent setup message** (config path + restart requirement), not only `{"action": "configure_approval_phrase"}`.
2. The `PUBLISH_APPROVAL_NOT_CONFIGURED` message mentions the restart requirement (the current message already partially does — "set SOFER_MCP_APPROVAL_PHRASE and restart" at `mcp_server.py:1155`; we extend it and credit that).
3. Unit tests cover the hint/message **content** (no covering tests for hint/message wording exist today — only envelope-shape assertions).

The fix is guidance, **not runtime re-read**: the phrase stays read-once at build; restart is the documented contract. This change keeps the envelope shape stable, keeps `publish_confirm`'s `hints` byte-for-byte `{"action": "configure_approval_phrase"}`, and adds no new field to the envelope — the actionable content rides in the flat preflight `hints` object and the refusal message, exactly where MSP-R13 already routes it.

## Sources

### Issue
- **GitHub #144** (bug, open) — `sofer_auth_status` hint dead-end / no actionable path; no covering tests for hint/message content. (Scope limit: posture-field enhancement #145 is excluded from this change by split-delivery decision.)

### Verified current state (re-verified this session, not taken on trust)
| Area | Location | Verified |
|------|----------|----------|
| `sofer_auth_status` tool | `src/sofer/mcp_server.py:1609-1701` | Envelope `{ok, exit_code, output, token, confidential, requires_ack_confidential, approval_configured, requires_approval_phrase, next, hints, config_errors}`. Hint logic L1667-1675: configured → `{"approval_phrase": "<from human>"}`, else → `{"action": "configure_approval_phrase"}` — the dead-end. No guidance keys of any kind today. |
| Phrase read-once | `src/sofer/mcp_server.py:2638-2652` (`build_server`) | `approval_phrase` arg > `os.environ["SOFER_MCP_APPROVAL_PHRASE"]`; blank/whitespace → `None` (fail-closed); **never re-read** afterwards. The running server cannot observe a new env var — hence restart semantics. |
| `PUBLISH_APPROVAL_NOT_CONFIGURED` refusal | `src/sofer/mcp_server.py:1153-1157` | `_error_envelope("PUBLISH_APPROVAL_NOT_CONFIGURED", "publish is disabled: no approval phrase is configured on this server (set SOFER_MCP_APPROVAL_PHRASE and restart) — a human approval phrase is required for any Hugging Face publish", next_hint={"action": "configure_approval_phrase"})`. **Partial credit for acceptance #2**: it already names the variable and says "restart". Gap: launcher-environment semantics (a separate shell ≠ launcher env) and per-agent setup; no tests pin the wording. |
| `_error_envelope` | `src/sofer/mcp_server.py:753-761` | `message` is rendered into the envelope's human-readable `output` field (asserted as `envelope["output"]` at `tests/test_mcp_server.py:786`). |
| Registration shapes (opencode hint accuracy) | `src/sofer/mcp_registration.py:158-165` (`build_entry`) | opencode → `{type:"local", command:["sofer-mcp"], cwd}` — **no env field**, nothing forwarded (L158-159). codex → `{command, cwd, env_vars}` — allow-list of env **NAMES** only (L160-162). gemini → `{command, cwd, env: {"KEY": "$KEY"}}` — NAME→`$NAME` refs, values never on disk (L163-165). `_ENV_KEYS = ["HF_TOKEN", "SOFER_MCP_APPROVAL_PHRASE"]` (L38). Module docstring L16-18: "secret values are never written to disk". |
| Exact-dict hints invariant on publish surface | `tests/test_mcp_server.py:783-784` | `assert envelope["hints"] == {"action": "configure_approval_phrase"}` — **must survive untouched**; guidance goes in `message`/`output` there (D4), never in `publish_confirm`'s `hints`. `:786` `assert "publish is disabled" in envelope["output"]` — the composed message must keep this prefix. |
| Flat-hints invariant | `tests/test_mcp_server.py:212-271` (`TestNextHintContract`) | `_is_flat_hint_dict` (L216-219): every `hints` value must be a scalar (`not isinstance(v, (dict,list))`). **No nested dicts, ever** — the new guidance must be flat scalar keys (booleans are scalars and allowed). Success-preflight asserts are partial-key (`hints["acknowledge_risk"] is True`, L256) — no exact-dict assert on the unconfigured auth_status `hints`. |
| Schema/no-leak pins | `tests/test_mcp_schema.py:~305` (`test_auth_status_no_leak`), `~330-348` (`test_auth_status_approval_not_configured`) | No-leak: `"phrase123"`/`"secret123"` absent from the serialized envelope. Unconfigured: `hints["action"] == "configure_approval_phrase"` **and** `"approval_phrase" not in envelope["hints"]` — guidance keys must be `approval_phrase_*`-prefixed (exact-key dict membership, so the bare `approval_phrase` key from the configured branch stays absent). `~182-185` (`test_auth_status_readonly`): `readOnlyHint:true` — the guidance lives in `hints`, keeping the tool read-only. |
| Baseline coverage (correction to the issue's "no covering tests") | `tests/test_mcp_server.py:241-436` | Envelope shape/`ok` semantics ARE covered (`next` present, `ok`, `exit_code`, `token`, `approval_configured`, `requires_approval_phrase`, `test_approval_not_configured_ok_false`). Not covered: hint **content**, per-agent guidance, message wording, flatness of the new payload — that is this change's test gap. |

## Scope

### In Scope
- `src/sofer/mcp_server.py` (the only production module):
  - Shared **fact constants** (`_APPROVAL_PHRASE_ENV_VAR`, `_PHRASE_READ_ONCE_FACT`, `_PHRASE_LAUNCH_ENV_FACT`, `_PHRASE_RESTART_FACT`) and the composed message constant `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`, so the hint payload and the refusal message carry **structurally identical semantics** from the same source (no drift).
  - `sofer_auth_status` unconfigured branch: flat, scalar, `approval_phrase_*`-prefixed guidance keys (incl. per-agent `setup_opencode/codex/gemini` naming **only** the keys `mcp_registration.py` actually writes, a machine-readable restart boolean, and the verification step) — composed from the same fact constants; `action: "configure_approval_phrase"` kept as the stable machine-readable key.
  - `sofer_publish_confirm` refusal: replace the inline literal (`mcp_server.py:1155`) with the composed message constant; keep `"publish is disabled:"` prefix and `next_hint={"action": "configure_approval_phrase"}`; `hints` of the refusal unchanged (exact-dict test survives).
  - Docstrings: `sofer_auth_status` (guidance contract + never-leak note) and `build_server` (read-once/restart contract) — **no** posture fields documented (those belong to #145).
  - Module docstring security bullet: extend the never-leak list to the new guidance text (variable **NAME** only, never value).
- `tests/test_mcp_server.py`: new tests for hint content, per-agent verified-keys, message wording, flatness (strengthened), and a fact-constant drift guard; extend `test_no_phrase_configured_refuses_fail_closed` **additively** (existing asserts untouched).
- `tests/test_mcp_schema.py`: extend `test_auth_status_approval_not_configured` **additively** (keep `action` + `"approval_phrase" not in hints`; add guidance-key asserts); extend `test_auth_status_no_leak` to scan the guidance payload for phrase material.
- Spec delta: **ADDED requirement only** — "Approval-phrase configuration diagnostics (APX-01)" with its three scenarios, authored during the spec phase at `openspec/changes/2026-09-11-fix-auth-status-hints/specs/mcp-server/spec.md`; no modification of requirement 10.8 in this change.

### Out of Scope
- **Posture fields for #145** (`phrase_source`, `server_process_id`, `server_started_at`, `server_version`) — envelope fields, `output_schema` additions, `phrase_source` precedence extraction, and the 10.8 spec rows all belong to the stacked `fix/145-auth-status-posture` change. Do not implement, name in docstrings, or test them here.
- Runtime re-read of `SOFER_MCP_APPROVAL_PHRASE` — the read-once contract is the documented root cause, not a bug to "fix"; the change makes restart semantics explicit.
- Any phrase value, hash, checksum, or derived signal anywhere in the envelope, `hints`, message, or docstrings (never-leak; only the variable NAME may appear).
- Guidance naming an on-disk agent config file/dir (`opencode.json`, `config.toml`, `settings.json`, `.codex/`, `.config/`) as the place to put the phrase — the registration tooling writes the `mcp.sofer` entry, not a phrase file.
- `sofer_publish_confirm`'s `hints` dict, the `next` registry continuation (MSP-R13), the 4-gate publish ladder, other tools' envelopes, tool roster (stays 14), transport.
- `workflow.py`, CLI flags, config keys, `pyproject.toml`.
- `README.md` / `README_ES.md` — unchanged (MCP tool-level change, no CLI/README heading; AGENTS.md §13 not triggered).

## Approach

1. **One source of truth for the process-start facts** (`D4`, reused from the combined design). Four module constants, ASCII only (`-`, not em-dash), named per AGENTS.md §1 (fail-closed gate wording must never be user-tunable):
   - `_APPROVAL_PHRASE_ENV_VAR = "SOFER_MCP_APPROVAL_PHRASE"` — variable **name only**, never a value.
   - `_PHRASE_READ_ONCE_FACT` — "the approval phrase is read once, when the MCP server process starts".
   - `_PHRASE_LAUNCH_ENV_FACT` — the var must be in the environment of the process that **launches** `sofer-mcp`; a variable set in a separate shell/terminal does not reach it (this is the Windows root cause).
   - `_PHRASE_RESTART_FACT` — a full restart of the agent/server process is required for a change to take effect.
   - Composed: `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` starting with the preserved `"publish is disabled:"` prefix.

2. **Actionable `hints` when `approval_configured:false`** (`D1`, reused; flat scalars — `TestNextHintContract` forbids nested dicts). Kept keys: the existing `token`/`acknowledge_confidential`/`acknowledge_risk` entries. New keys:

   | Key | Value | Origin |
   |-----|-------|--------|
   | `action` | `"configure_approval_phrase"` (unchanged, stable) | invariant, `test_mcp_schema.py:348` |
   | `approval_phrase_env_var` | `"SOFER_MCP_APPROVAL_PHRASE"` | NAME only, never value |
   | `approval_phrase_when` | `_PHRASE_READ_ONCE_FACT` | shared constant |
   | `approval_phrase_where` | `_PHRASE_LAUNCH_ENV_FACT` | shared constant (Windows root cause) |
   | `approval_phrase_restart` | `_PHRASE_RESTART_FACT` | shared constant |
   | `approval_phrase_restart_required` | `True` (flat boolean — machine-readable restart signal, scalar per flatness invariant) | mandate |
   | `approval_phrase_setup_opencode` | "`sofer mcp add --agent opencode` writes only the `mcp.sofer` entry `{type, command, cwd}` and forwards **no environment** — set `SOFER_MCP_APPROVAL_PHRASE` in the launcher's environment" | verified `mcp_registration.py:158-159` |
   | `approval_phrase_setup_codex` | "codex persists an `env_vars` allow-list of env-variable NAMES (values never written to disk) — export the var before launching codex" | verified `mcp_registration.py:160-162` |
   | `approval_phrase_setup_gemini` | "gemini persists an `env` mapping NAME → `$NAME` references (values never written to disk) — export the var before launching gemini" | verified `mcp_registration.py:163-165` |
   | `approval_phrase_verify` | "after the restart, `sofer_auth_status` reports `approval_configured:true`" | verification step |

   Per-agent guidance names **only** keys `mcp_registration.py` writes (`type`, `command`, `cwd`, `env_vars`, `env`); no config file/dir names; no env-forwarding claim for opencode; no phrase material. Guidance appears **only** in the unconfigured branch — the configured branch stays `{"approval_phrase": "<from human>"}` plus the existing keys.

3. **Message wording (`#144` acceptance #2)** — `PUBLISH_APPROVAL_NOT_CONFIGURED` uses `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` verbatim (replacing the inline literal); keeps the `"publish is disabled:"` prefix (test `test_mcp_server.py:786`), `error_code`, `next_hint`, and the "upload never reached" semantics (MSP-R05). The message is the hint facts composed as one sentence — no drift possible (a drift-guard test asserts each fact constant is a substring of both the hint values and the message). Credit: the current message already said "set … and restart"; this formalizes it into the shared-fact contract plus launcher-environment semantics.

4. **Docstrings** — `sofer_auth_status`: guidance contract (read-once, launching-process env, restart, per-agent keys, verify step) + never-leak note. `build_server`: read-once/restart contract in the existing warning block. **No posture fields documented** (deferred to #145).

5. **Spec delta** — this change modifies **no** requirement; it **adds** APX-01 "Approval-phrase configuration diagnostics" with three scenarios (see Spec Delta Statement). The 10.8 envelope rows stay for #145.

6. **Tests** — new `TestAuthStatusUnconfiguredGuidance`-style coverage in `tests/test_mcp_server.py` (hint content: each fact key present with expected text; flatness re-checked for the new payload; per-agent keys ⊆ verified set and no config-file/dir names anywhere in `hints`; `approval_phrase_restart_required is True`; message wording: var name + read-once + launcher env + restart; drift guard between message and hints; upload never reached; refusal `hints == {"action": "configure_approval_phrase"}` unchanged) + additive extends in `tests/test_mcp_schema.py` (guidance keys present, `action` kept, bare `approval_phrase` key absent; no phrase material in the serialized guidance). Every spec scenario maps to a test (AGENTS.md §6).

## Alternatives

| Alternative | Rejected because |
|-------------|------------------|
| Re-read `SOFER_MCP_APPROVAL_PHRASE` from env on every `sofer_auth_status` call (make the hint magically resolve) | Breaks the fail-closed server-level invariant and the read-once contract; a runtime half-refresh would make `approval_configured` inconsistent with what `sofer_publish_confirm` actually enforces. The bug **is** process-start semantics; the fix documents and operationalizes them. |
| One verbose `approval_phrase_guidance` prose blob key instead of per-agent keys | Not branchable per agent and not per-agent testable; "verified registration keys" must be a per-agent assertion. Per-agent keys let an agent act on its own key without prose parsing (combined design's open question #1 — collapse is possible later without touching spec bullets). |
| Put guidance in `sofer_publish_confirm`'s `hints` too (symmetric payload) | Violates MSP-R13's minimal continuation and breaks the exact-dict assert `test_mcp_server.py:783-784`; the refusal's guidance belongs in `message`/`output` (D4), which is already where the human reads it. |
| Add a dedicated `sofer_setup_approval` tool or a `[tool.sofer]` config key | Scope creep; new tool breaks the 14-callable roster invariant; a user-tunable refusal/guidance config is a lever for weakening a fail-closed gate (AGENTS.md §1 precedent). |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Phrase leak via hint/message text (value, derived signal) | Low | Guidance and message carry the variable NAME only, composed from constants; docstring never-leak note extended; `test_auth_status_no_leak` extended to scan the serialized guidance payload and message for the configured phrase value. |
| opencode hint inaccurate (claims env forwarding the registration does not do) | Med | Hint text pinned to `mcp_registration.py:158-159`: opencode entry is `{type, command, cwd}` only and forwards **no environment** — the hint says set the var in the *launcher's* environment, never that registration forwards it; surface re-verified at design time. |
| Windows restart semantics misstated (suggesting "export in a new terminal then re-call") | Med | `_PHRASE_LAUNCH_ENV_FACT` states the var must be in the environment of the process that launches `sofer-mcp` and that a separate shell does not reach it; `approval_phrase_restart_required: true` is the machine-readable signal; tests assert the wording. |
| Exact-dict asserts / flatness invariant broken | Low | `publish_confirm`'s `hints` is deliberately untouched (`test_mcp_server.py:783-784` preserved); new guidance keys are flat scalars (boolean allowed by `_is_flat_hint_dict`); `approval_phrase_*` prefix keeps `"approval_phrase" not in envelope["hints"]` true (exact-key membership); no old assertion is relaxed — only additive new asserts. |
| Scope drift into #145 (posture fields) during apply | Med | This proposal is the #144 contract: envelope fields, `output_schema`, `phrase_source` and all 10.8 rows are named OUT; the spec delta is ADD-only (APX-01); apply-phase review gate checks no posture symbol appears. |

## Success Criteria

Mapped to the issue's **three acceptance criteria**:

**#144-1 — actionable hint when `approval_configured:false`:**
- [ ] `sofer_auth_status` returns a `hints` payload where `action` stays `"configure_approval_phrase"` **and** the payload additionally carries an actionable per-agent setup message: the variable NAME (`approval_phrase_env_var`), read-once-at-start semantics, launcher-environment requirement, restart requirement (prose `approval_phrase_restart` + machine-readable `approval_phrase_restart_required: true`), per-agent `setup_{opencode,codex,gemini}` keys naming only keys `mcp_registration.py` writes, and the verification step (`approval_configured:true` after restart). No dead-end action-only hint.
- [ ] The payload stays **flat** (scalar values only, `TestNextHintContract`), and no phrase value / config-file path appears in it.

**#144-2 — PUBLISH_APPROVAL_NOT_CONFIGURED mentions restart (credited, extended):**
- [ ] The refusal message (rendered into `envelope["output"]`) keeps `"publish is disabled:"` and now states, from the same fact constants as the hint: the variable NAME, read-once-at-start, launcher-environment, restart requirement. `error_code`, `next_hint`, and the never-upload semantics unchanged; `hints` of the refusal stays exactly `{"action": "configure_approval_phrase"}`.

**#144-3 — unit tests cover the hint/message content (today missing):**
- [ ] New tests assert the hint payload content (each guidance key present and matching the fact constants), the per-agent verified-keys contract (keys ⊆ `{type,command,cwd,env_vars,env}`, no config file/dir names), the message wording, `approval_phrase_restart_required is True`, the drift guard (facts shared between hints and message), and flatness of the enriched payload.
- [ ] Existing envelope/schema tests stay green **unchanged** (`test_mcp_server.py:783-786`, `TestNextHintContract`, `test_mcp_schema.py` no-leak/action/readOnly pins — extended additively, never relaxed).

**Delivery-wide:**
- [ ] Full `uv run pytest tests/ -q` green before and after (baseline re-verified at apply; user-reported 1468 collected / 6 skipped at 2026-09-11 — AGENTS.md §6 quotes 1149/2, re-verify; new tests are additive) and `uv run mypy src/` clean; PR uses `.github/PULL_REQUEST_TEMPLATE.md` with real command output and the SDD artifacts section.

## Spec Delta Statement

**REAL delta, ADD-only, requirement-level.** `openspec/specs/mcp-server/spec.md` gains one requirement in this change — nothing existing is modified:

- **ADDED — `### Requirement: Approval-phrase configuration diagnostics (APX-01)`**, carrying the three scenarios from the combined design's delta (authored at `openspec/changes/2026-09-11-fix-auth-status-hints/specs/mcp-server/spec.md` during the spec phase, merged into the live spec at archive):
  1. **Unconfigured approval hint is actionable** — `hints["action"]` stays `"configure_approval_phrase"`, and the flat payload additionally carries guidance naming `SOFER_MCP_APPROVAL_PHRASE`, the read-once-at-start semantics, the launching-process environment requirement with a mandatory restart, per-agent setup, and the verification step; no phrase value or phrase-derived value, no config file/dir path as the phrase location.
  2. **Publish refusal message carries the same process-start semantics** — `error_code = PUBLISH_APPROVAL_NOT_CONFIGURED`, upload never reached, message names the variable, read-once, launching-process env, restart.
  3. **Per-agent guidance uses only verified registration keys** — every per-agent key named is one `mcp_registration.py` writes (`type`, `command`, `cwd`, `env_vars`, `env`); no config file/dir path named as the phrase location.

- **The 10.8 envelope rows (posture fields, explicit>env>none precedence, restart-proof `started_at`, never-leak extension on the four fields) are DEFERRED TO #145** — the sibling change `2026-09-11-fix-auth-status-diagnostics` owns the MODIFIED-10.8 delta; this change must not touch them. (APX-01's prose is deliberately posture-free, so the two deltas compose cleanly at archive: #145's 10.8 never-leak bullet references APX-01's guidance; #144's APX-01 references no posture field.)
- Matching tests for every APX-01 row (AGENTS.md §6: every spec scenario has a corresponding test) — named in the Testing section approach above.

## Dependencies

- **Production:** `src/sofer/mcp_server.py` only (constants, hint branch, message, docstrings). `src/sofer/mcp_registration.py` is a **read-only reference** for the per-agent key names (already verified at `mcp_registration.py:158-165`).
- **Default constants vs config:** new text lives in named module constants, never in `pyproject.toml` / `[tool.sofer]` — same precedent as `_UNTRUSTED_NOTE` / `_PHASED_INSTRUCTIONS` (fail-closed gate wording must not be user-tunable). No new dependency; no new import needed for #144 (no `datetime`/`_version` — those are #145).
- **Tests:** shared fixtures (`_make_dataset`, `restore_tool_config`, `_call`, `_tools_dict`) already in `tests/conftest.py`; `monkeypatch.setenv`/`delenv` for `SOFER_MCP_APPROVAL_PHRASE` isolation (always `delenv` for absent/blank cases so an ambient shell variable cannot flake CI).
- **Stacked sibling:** `fix/145-auth-status-posture` (issue #145) is delivered **after** this PR. No functional dependency; it touches the same file, so PR ordering (this PR merges first) avoids conflict and lets #145's 10.8 never-leak bullet reference the already-merged APX-01.

## Delivery Note

- Branch `fix/144-auth-status-hints` (already created, base `dev`). **PR-only**: commits land on this branch, merged via PR into `dev`; never commit directly to `main`/`dev`; no tag, no release, no version bump (hatch-vcs derives version from tags — untouched). This is PR #1 of 2; the posture change (#145) is a separate stacked PR on `fix/145-auth-status-posture`.
- GitHub self-approve is impossible for the owner's own PR — user authorizes merge via `gh pr merge` after review.
- Baseline: full `uv run pytest tests/ -q` green before and after; user-reported 1468 collected / 6 skipped at 2026-09-11 (re-verify at apply; AGENTS.md §6 quotes an older 1149/2). The change is **new tests + two additive test edits only**; no existing assertion is relaxed.
- Pre-commit runs ruff + mypy automatically (no `--no-verify`); `uv run mypy src/` clean before push. Review budget: 2 test files + 1 production file, well under the 400-line threshold.
- Success criteria above are the PR's acceptance checklist; PR template sections filled with actual command output; SDD artifacts section mandatory.

## Proposal question round — assumptions requiring review

Auto mode — these assumptions are baked in above and need explicit sign-off (or correction) before the spec phase:

1. **Machine-readable restart signal** — I add one flat boolean key `approval_phrase_restart_required: true` alongside the prose `approval_phrase_restart` fact (both flat scalars; the flatness invariant admits booleans). If you prefer the restart signal to be prose-only (drop the boolean), or want the boolean to **replace** the prose key, say so — it changes the hint key contract the spec delta pins.
2. **Hint verbosity** — the unconfigured `hints` object grows to ~10 flat keys (per-agent setup as three keys). Alternative: one `approval_phrase_setup` blob. The combined design's open question favours per-agent keys for branchability/testability; the spec bullets survive a later collapse either way.
3. **opencode phrasing** — the hint says `sofer mcp add --agent opencode` forwards **no environment** and points the user at the launcher's environment (verified against `mcp_registration.py:158-159`). It does **not** claim any `environment` object exists in the written entry — correct per current code; flag if a newer opencode shape is expected.
4. **No README/ES change** — MCP tool-level fix (tool description is the docstring contract), no CLI flag/config key/README heading changes; AGENTS.md §13 not triggered. If the repo convention requires README touch for envelope behavior changes, say so and I'll add both files in one commit.
5. **Message prefix kept** — the composed message retains the leading `"publish is disabled:"` string verbatim to keep `test_mcp_server.py:786` and user-facing continuity; the rest is rewritten from the fact constants.

---
*Branch: `fix/144-auth-status-hints` (PR #1 → `dev`). Issue #144 ONLY; posture fields (#145) deferred to the stacked `fix/145-auth-status-posture` change. Change artifacts persist to `openspec/changes/2026-09-11-fix-auth-status-hints/` per the artifact-store contract.*