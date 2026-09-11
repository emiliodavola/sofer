# Design: 2026-09-11-fix-auth-status-hints

**Change:** `2026-09-11-fix-auth-status-hints` · **Branch:** `fix/144-auth-status-hints` (base `dev`, PR-only)
**Inputs:** `proposal.md` (this folder), `specs/mcp-server/spec.md` (APX-01), `reference-144-145-planning.md`.
**Scope lock:** GitHub **ISSUE #144 ONLY** — PR #1 of 2 of the split auth-status diagnostics delivery. Posture fields (`phrase_source`, `server_process_id`, `server_started_at`, `server_version`) are **out of scope** and belong to the stacked change `2026-09-11-fix-auth-status-posture` (issue #145, branch `fix/145-auth-status-posture`).

---

## 1. Problem statement (verified by reading `dev` this session)

`sofer_auth_status` with `approval_configured:false` returns `hints = {"action": "configure_approval_phrase"}` — a dead end. The root cause is **process-start semantics**, not hint wording:

| Fact | Evidence (verified) |
|---|---|
| The phrase is read **exactly once**, at build time | `src/sofer/mcp_server.py:2606` `def build_server(...)`; `:2642` `os.environ.get("SOFER_MCP_APPROVAL_PHRASE")`; module global `_APPROVAL_PHRASE` (assigned only there, read at `:1150`, `:1665`) |
| Blank/whitespace phrase fails closed | `mcp_server.py:2644-2648` (`raw_phrase if raw_phrase and raw_phrase.strip() else None`) |
| The running server never re-reads the environment | no second `os.environ.get`/`getenv` of that key anywhere in `mcp_server.py` |
| A separately-launched shell does not reach the launcher env (Windows root cause) | consequence of the read-once site above; documented in `README.md:701-705` / `README_ES.md:736-740` |
| `mcp add --agent opencode` forwards **no** environment | `src/sofer/mcp_registration.py:158-159` returns `{type, command, cwd}` only; `:160-162` codex `env_vars` (NAMES); `:163-165` gemini `env` (NAME → `$NAME`); `:38` `_ENV_KEYS = ["HF_TOKEN", "SOFER_MCP_APPROVAL_PHRASE"]` |
| The refusal message already partially satisfies acceptance #2 | `mcp_server.py:1155` "`publish is disabled: ... (set SOFER_MCP_APPROVAL_PHRASE and restart) — ...`" — missing launcher-env semantics and per-agent setup; no test pins the wording |
| Hint content is untested | `tests/test_mcp_server.py:208-271` (`TestNextHintContract`) asserts only shape/flatness; `:320-443` (`TestAuthStatusValidity`) asserts only `ok`/`exit_code`; `tests/test_mcp_schema.py:272-350` (`TestEnvelope`) asserts pin keys only |

**Fix = guidance, not runtime.** The phrase stays read-once; the change makes the recovery path explicit on the two surfaces that report the state, and pins that content with tests (acceptance #3).

---

## 2. Decisions

### D1 (mandate #2) — Hint key contract on `sofer_auth_status`

`hints` gains a flat, scalar, `approval_phrase_*`-namespaced guidance block **only in the unconfigured branch**:

| Key | Value | Origin / rationale |
|---|---|---|
| `action` | `"configure_approval_phrase"` | **unchanged, stable** — pinned by `tests/test_mcp_schema.py:348` |
| `approval_phrase_env_var` | `_APPROVAL_PHRASE_ENV_VAR` = `"SOFER_MCP_APPROVAL_PHRASE"` | NAME only, never a value |
| `approval_phrase_when` | `_PHRASE_READ_ONCE_FACT` | read-once-at-start (shared constant) |
| `approval_phrase_where` | `_PHRASE_LAUNCH_ENV_FACT` | launcher env; a separate shell does not reach it (Windows root cause) |
| `approval_phrase_restart` | `_PHRASE_RESTART_FACT` | prose restart requirement |
| `approval_phrase_restart_required` | `True` | machine-readable flat boolean (scalar ⇒ flatness-safe) |
| `approval_phrase_setup_opencode` | `_OPENCODE_SETUP` | opencode entry is `{type, command, cwd}` and forwards **no environment** — guidance points at the launcher env, never at env forwarding (`mcp_registration.py:158-159`) |
| `approval_phrase_setup_codex` | `_CODEX_SETUP` | codex writes an `env_vars` allow-list of **names** (values never on disk) (`:160-162`) |
| `approval_phrase_setup_gemini` | `_GEMINI_SETUP` | gemini writes an `env` mapping of NAME → `$NAME` refs (values never on disk) (`:163-165`) |
| `approval_phrase_verify` | `_PHRASE_VERIFY_FACT` | verification step: after the restart `sofer_auth_status` reports `approval_configured:true` |

Pre-existing keys (`token`, `acknowledge_confidential`, `acknowledge_risk`) are untouched. The configured branch keeps `hints["approval_phrase"] = "<from human>"` and gains **no** `approval_phrase_*` key.

**Why per-agent keys instead of one prose blob:** they are branchable by an agent (act on your own key), individually assertable in tests (spec scenario 3 is a per-agent contract), and collapse later without touching spec bullets. Rejected blob (see `proposal.md` Alternatives).

**Why flat scalars:** `tests/test_mcp_server.py:213` `_is_flat_hint_dict` rejects dict/list values — the same invariant the spec pins (`MSP-R13`).

**Namespace rule:** `approval_phrase_*` keeps `"approval_phrase" not in hints` true when unconfigured (exact-key dict membership, `tests/test_mcp_schema.py:349`) while preserving the bare key in the configured branch (`test_mcp_schema.py:327`, `test_auth_status_no_leak`).

Implementation shape (in `sofer_auth_status`, replacing `mcp_server.py:1672`):

```python
if approval_configured:
    next_hint["approval_phrase"] = "<from human>"
else:
    next_hint.update(_approval_phrase_guidance_hints())
```

`_approval_phrase_guidance_hints()` is a **pure function returning a fresh flat dict** (no shared mutable module state, no in-place global mutation) — it owns the whole unconfigured payload, including `action`, so the assertion at `test_mcp_schema.py:348` reads from one place.

### D2 (mandate #3) — `PUBLISH_APPROVAL_NOT_CONFIGURED` message

Replace the inline literal at `mcp_server.py:1155` with a composed module constant:

```python
_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE: str = (
    "publish is disabled: no approval phrase is configured on this server - "
    f"{_PHRASE_READ_ONCE_FACT} (build_server(approval_phrase=...) or {_APPROVAL_PHRASE_ENV_VAR}); "
    f"{_PHRASE_LAUNCH_ENV_FACT}; {_PHRASE_RESTART_FACT} - "
    "a human approval phrase is required for any Hugging Face publish"
)
```

- The `"publish is disabled"` prefix is **verbatim** (pinned by `tests/test_mcp_server.py:786`); ASCII `-` separators, no em-dash (proposal mandate), no phrase material.
- Each process-start fact appears **once** — no duplication, and no repetition of the per-agent setup (that rides in the preflight `hints`; the refusal keeps its minimal payload).
- `next_hint={"action": _APPROVAL_PHRASE_ACTION}` where `_APPROVAL_PHRASE_ACTION: str = "configure_approval_phrase"`, so the refusal `hints` stays **byte-for-byte** `{"action": "configure_approval_phrase"}` (pinned exact-dict at `tests/test_mcp_server.py:784`) while sharing one literal with the preflight.
- `_error_envelope` renders `message` into `output` (`mcp_server.py:753-790`), so the wording is user-visible exactly where `:786` asserts it. `error_code`, the `extra` payload, and the never-upload semantics (the gate precedes any upload) are unchanged.

**Why the refusal `hints` is deliberately asymmetric with the preflight `hints`:** `MSP-R13` keeps error envelopes minimal, and `:784` pins the exact dict. Same *semantics*, different *surface* — enforced structurally by D3's shared constants (spec scenario "Guidance message and hints share one fact source"), not by copying text.

### D3 (mandate #1) — One fact source (proposal `D4`)

Five module constants in `mcp_server.py`'s constants block (near `_ERROR_CODES` at `:143` and `_PHASED_INSTRUCTIONS` at `:154`), ASCII only, named per AGENTS.md §1 (fail-closed gate wording must never be user-tunable, so **no** `[tool.sofer]` key and no `pyproject.toml` entry):

```python
_APPROVAL_PHRASE_ENV_VAR: str = "SOFER_MCP_APPROVAL_PHRASE"   # NAME only - never a value
_APPROVAL_PHRASE_ACTION: str = "configure_approval_phrase"    # shared by both surfaces
_PHRASE_READ_ONCE_FACT: str = "... read once, when the MCP server process starts ..."
_PHRASE_LAUNCH_ENV_FACT: str = (
    f"{_APPROVAL_PHRASE_ENV_VAR} must be in the environment of the process that launches "
    "sofer-mcp - a variable set in a separate shell or terminal does not reach it"
)
_PHRASE_RESTART_FACT: str = (
    "a full restart of the agent/server host process is required for a new value to take effect"
)
```

Plus the registration-shape table the per-agent strings are composed from (verified against `mcp_registration.build_entry`), so the "keys we claim" set is data, not prose:

```python
_APPROVAL_PHRASE_AGENT_ENTRY_KEYS: dict[str, tuple[str, ...]] = {
    "opencode": ("type", "command", "cwd"),   # mcp_registration.py:158-159 - no env field
    "codex": ("env_vars",),                   # mcp_registration.py:160-162 - NAMES only
    "gemini": ("env",),                       # mcp_registration.py:163-165 - NAME -> $NAME
}
```

Composition rule: **every** process-start fact used by a hint value is the constant itself (no re-typing), and `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` embeds the same four constants. A drift-guard test (D5) asserts each fact constant is a substring of both its hint value and the message — the "same semantics on both surfaces" contract becomes mechanically checkable, not aspirational.

**Deliberate non-unification:** `mcp_registration._ENV_KEYS:38` keeps its own `"SOFER_MCP_APPROVAL_PHRASE"` literal. `mcp_server` sits behind the optional `mcp` extra (`fastmcp`); `mcp_registration` is CLI-side and must never import the server module (it would make the CLI depend on the extra). Adding the reverse import is also wrong (unnecessary coupling). The duplication is accepted and, optionally, guarded by a one-line drift assertion in the new tests (D5, T12).

### D4 (mandate #4) — Docstring / schema surface: what to touch

| Surface | Action | Rationale |
|---|---|---|
| `sofer_auth_status` docstring (`mcp_server.py:1609-1636`) | **Update.** Document the unconfigured guidance contract: read-once, launcher env, restart (`approval_phrase_restart_required: true`), per-agent keys, verify step, and the never-leak rule (NAME only, no config path). Keep the existing `When to use:` / `Requires:` / `Next:` lines and the ≤10-sentence pre-block shape. | The tool description **is** the docstring (`_workflow_description`, `mcp_server.py:~745`); `tests/test_mcp_schema.py:66-85` requires "When to use" present, and forbids `MSP-R` / `CF-` / `UNTRUSTED` tokens in any description (`tests/test_mcp_schema.py:66-103`, `TestDescriptions`) — the new text must respect both. |
| `build_server` docstring warning block (`:2606-2634`) | **Update (2 lines).** State the read-once/restart contract next to the existing "one-server-per-process" warning. | Makes the guidance's claim traceable to the code that implements it. |
| Module docstring security bullet (`:29-38`, fail-closed ladder) | **Update (1 sentence).** Extend the never-leak sentence: the configured phrase value never appears anywhere; the preflight guidance carries the variable NAME only. | `AGENTS.md §2` (module docstring) + spec NEVER-LEAK. |
| `sofer_auth_status` `output_schema` (`:2391-2403`) | **No change.** `hints` is already `{"type": "object"}`; **no envelope field is added**. Typed `properties` entries for posture fields are #145. | Changing it would be scope drift into #145 and a needless schema churn. |
| `_ERROR_ENVELOPE_SCHEMA_FIELDS` (`:135-140`) | **No change.** | No new envelope key. |
| `sofer_publish_confirm` `approval_phrase` param description (`:1063`) | **No change** (recommended). The refusal message carries the guidance; widening param descriptions is diff noise and `tests/test_mcp_schema.py:104-173` only requires a description to exist. | Minimal diff, single guidance home. |
| `_PHASED_INSTRUCTIONS` (`:157-171`) | **No change.** It already names the env var and the fail-closed rule. | Avoid churn in a pinned instruction string (`tests/test_mcp_schema.py:87-102`). |

### D5 (mandate #5) — Tests

**New tests (RED first, then GREEN), named exactly as the spec delta pins them:**

`tests/test_mcp_server.py::TestHintContentActionable` (place after `TestNextHintContract`, i.e. after `:271`):

| # | Test | Asserts |
|---|---|---|
| T1 | `test_auth_status_unconfigured_hint_is_actionable` | unconfigured ⇒ `action` stable, guidance names the var, read-once, launcher env, restart, verify step |
| T2 | `test_auth_status_unconfigured_hint_restart_required_is_true` | `hints["approval_phrase_restart_required"] is True` |
| T3 | `test_auth_status_unconfigured_hints_are_flat_scalars` | reuse `TestNextHintContract._is_flat_hint_dict` semantics on the enriched payload (no dict/list values) |
| T4 | `test_auth_status_configured_hints_have_no_guidance_keys` | configured branch: `hints["approval_phrase"] == "<from human>"`, **zero** `approval_phrase_*` keys |
| T5 | `test_auth_status_unconfigured_hint_uses_verified_registration_keys` | per-agent values contain the keys in `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` (`type`/`command`/`cwd`, `env_vars`, `env`) and opencode's value states **no** environment is forwarded |
| T6 | `test_auth_status_unconfigured_guidance_has_no_phrase_material` | server built with `approval_phrase="phrase123"`… (unconfigured guidance generated from a no-phrase server) — no phrase value, no bare `approval_phrase` key, no derived signal |
| T7 | `test_auth_status_unconfigured_guidance_names_no_config_path` | no hint value contains `opencode.json`, `config.toml`, `settings.json`, `.codex`, `.config` |

`tests/test_mcp_server.py::TestApprovalNotConfiguredMessage` (place next to `TestPublishAuthorizationLadder`, `:638`):

| # | Test | Asserts |
|---|---|---|
| T8 | `test_publish_approval_not_configured_message_process_start_semantics` | `error_code == PUBLISH_APPROVAL_NOT_CONFIGURED`, `upload_calls == []`, message names the var + read-once + launcher env + restart, `"publish is disabled"` prefix kept |
| T9 | `test_publish_refusal_hints_unchanged_exact_dict` | `hints == {"action": "configure_approval_phrase"}` (exact) |
| T10 | `test_approval_phrase_facts_not_drifted_between_hints_and_message` | each of the 4 fact constants is a substring of its hint value **and** of `ms._APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` |

**Additive extends (existing assertions untouched, nothing relaxed):**

| # | Test | Added assertions |
|---|---|---|
| T11 | `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured` (`:330-350`) | guidance keys present alongside the kept `action` and `"approval_phrase" not in hints` |
| T12 | `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` (`:305-328`) | serialize the whole envelope and the refusal message: the configured phrase value appears in neither; optional 1-line drift assert `_APPROVAL_PHRASE_ENV_VAR in mcp_registration._ENV_KEYS` |
| T13 | `tests/test_mcp_server.py::TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed` (`:750-786`) | **additive only**: message-names-var/read-once/launcher/restart asserts; existing `:784`/`:786` lines stay verbatim |

**Pins that must survive untouched (regression contract):**

- `tests/test_mcp_server.py:784` — refusal `hints` exact dict; `:786` — `"publish is disabled"` in `output`.
- `tests/test_mcp_server.py:208-271` — `TestNextHintContract` flatness + executable `next` (MSP-R13); `next` is **not** modified.
- `tests/test_mcp_schema.py:348-349` — `action` value + bare `approval_phrase` absent when unconfigured; `:327` — configured branch `approval_phrase == "<from human>"`; `:185` — `readOnlyHint: true` (guidance rides in `hints`; the tool stays side-effect-free).
- Tool roster stays 14 callables (`tests/test_mcp_server.py:256-276`, `TestToolRoster`); no new tool, no `[tool.sofer]` key, no `pyproject.toml` change.

**Test hygiene:** unconfigured cases always `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)` **before** `build_server` (the env is read at build time — setting it after the build proves nothing, which is precisely the bug), following the existing pattern at `test_mcp_server.py:428`, `:770-775`, `test_mcp_schema.py:328`; valid-config setup via `_make_dataset(tmp_path)` + `HF_TOKEN`. No network, no `mock` of `upload_folder` beyond the existing helper.

**Spec-delta pointer correction (housekeeping, in scope):** the APX-01 test pointer names `TestPublishApprovalLadder::test_no_phrase_configured_refuses_fail_closed`; the real class is `TestPublishAuthorizationLadder` (`tests/test_mcp_server.py:638`). Fix the pointer in `specs/mcp-server/spec.md` (descriptive text only, ADD-only requirement, delta not yet archived) so `AGENTS.md §6` holds literally.

### D6 (mandate #6) — Delivery

| Item | Decision |
|---|---|
| Branch / PR | `fix/144-auth-status-hints` (base `dev`), PR-only into `dev`; **PR #1 of 2**; sibling `fix/145-auth-status-posture` merges after (same file, ordering avoids conflict) |
| Files | `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `tests/test_mcp_schema.py` (+ this change's `openspec/changes/2026-09-11-fix-auth-status-hints/` artifacts) |
| Size estimate | production ≈ +65/−5; tests ≈ +150; total ≈ **215 changed lines < 400** ⇒ single PR, no chaining, no `size:exception` |
| Excluded | `README.md` / `README_ES.md` (MCP tool-level change; no CLI flag/config key/heading — `AGENTS.md §13` not triggered; README `:619-621`, `:678-681`, `:701-705` already state env shapes and restart semantics consistently with the new text), posture fields (#145), runtime re-read, `next` registry, publish ladder, `workflow.py`, `pyproject.toml` |
| Dependencies | none new; **no new imports** (`datetime` / `_version` are #145) |
| Gates | `uv run pytest tests/ -q` green before **and** after (re-measure the collector count at apply — proposal quotes 1468/6, `AGENTS.md §6` quotes 1149/2; record the real numbers in the PR template), `uv run mypy src/` clean, ruff via pre-commit (never `--no-verify`), PR template sections complete with actual command output + SDD artifacts section |

---

## 3. Data flow (after)

```
build_server(root, approval_phrase=...)            # single env read, process start
  └── _APPROVAL_PHRASE = phrase or env-or-None     # blank/whitespace -> None (fail-closed)

sofer_auth_status(config)
  ├── approval_configured = _APPROVAL_PHRASE is not None
  ├── hints: pre-existing keys (token/acknowledge_*) 
  │     └── if not approval_configured:  update(_approval_phrase_guidance_hints())
  │               _APPROVAL_PHRASE_ENV_VAR ─┐
  │               _PHRASE_READ_ONCE_FACT  ──┤→ approval_phrase_env_var / _when / _where /
  │               _PHRASE_LAUNCH_ENV_FACT ──┤  _restart / _restart_required / _verify /
  │               _PHRASE_RESTART_FACT    ──┘  _setup_{opencode,codex,gemini}
  └── next = registry sofer_publish call (MSP-R13, unchanged)

sofer_publish_confirm(...)  with no configured phrase
  └── _error_envelope("PUBLISH_APPROVAL_NOT_CONFIGURED",
                       _APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE,   # same 4 constants
                       next_hint={"action": _APPROVAL_PHRASE_ACTION})   # exact-dict pin
```

Both surfaces render the same four facts from the same constants; only the *carrier* differs (flat preflight `hints` vs. refusal `message`/`output`).

---

## 4. Spec coverage matrix (APX-01)

| Scenario | Tests |
|---|---|
| Unconfigured approval hint is actionable | T1, T2, T3, T4, T11 |
| Publish refusal message carries the same process-start semantics | T8, T9, T13 |
| Guidance message and hints share one fact source | T10, T5 |
| Guidance leaks no phrase material and invents no config path | T6, T7, T12 |

---

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Phrase material leaks through guidance/message | Only the NAME constant is interpolated; never-leak docstring bullet extended; T6/T12 scan the serialized payload and message for the configured value |
| Guidance claims env forwarding opencode does not do | Per-agent claim keys come from `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` verified at `mcp_registration.py:158-165`; T5 asserts the keys *and* the "no environment forwarded" statement |
| Restart semantics stated weakly ("re-call the tool") | `_PHRASE_RESTART_FACT` + `approval_phrase_restart_required: True`; `_PHRASE_LAUNCH_ENV_FACT` states a separate shell does not reach the server; T1/T2/T8 assert the wording |
| Broken pin / flatness invariant | `publish_confirm` `hints` untouched (T9 keeps `:784`); values are scalars (T3); `approval_phrase_*` prefix preserves `:349`; extends are additive only (T11–T13) |
| Scope drift into #145 | No envelope field, no `output_schema` entry, no `datetime`/`_version` import, no posture symbol in code or docstrings; apply-phase review greps for the four posture names |
| Flaky tests from an ambient shell variable | Always `monkeypatch.delenv(...)` before `build_server` in unconfigured cases |
| Docstring breaks description contract | New docstring text avoids `MSP-R`/`CF-`/`UNTRUSTED`, keeps `When to use:`, keeps the pre-block short (`tests/test_mcp_schema.py:66-103`) |

---

## 6. Apply plan (TDD)

1. **RED** — add T1–T13; run the two files; T1–T12 fail (missing keys / old message), T13's existing assertions still pass.
2. **GREEN** — add the D3 constants + `_approval_phrase_guidance_hints()`, swap `sofer_auth_status:1672` and the `:1155` literal; tests pass.
3. **TRIANGULATE** — configured branch (T4), flatness (T3), no-leak (T6/T12), drift guard (T10) on both surfaces.
4. **REFACTOR** — docstrings (D4), module never-leak bullet, spec pointer fix; no behaviour change.
5. **VERIFY** — full `uv run pytest tests/ -q`, `uv run mypy src/`, ruff via pre-commit; PR template with real output; confirm 14 callables and that no posture symbol exists in the diff.

---

## 7. Deferred to #145 (explicitly not designed here)

`phrase_source` (explicit > env > none), `server_process_id`, `server_started_at` (restart-proof), `server_version`, the auth_status `output_schema` additions, and the ALTERED 10.8 spec rows. APX-01 is posture-free so the two deltas compose cleanly at archive.
