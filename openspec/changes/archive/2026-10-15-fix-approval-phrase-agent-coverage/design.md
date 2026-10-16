# Design — `2026-10-15-fix-approval-phrase-agent-coverage`

> **Change** `2026-10-15-fix-approval-phrase-agent-coverage` (issue **#295**) · branch
> `fix/295-approval-phrase-agent-coverage` from `dev@b7dea51` · store **hybrid**.

---

## 1. The defect, precisely

`_approval_phrase_guidance_hints()` returns the flat `hints` payload `sofer_auth_status` reports when
no approval phrase is configured (APX-01). Its per-agent block was three literal keys:

```python
"approval_phrase_setup_opencode": _OPENCODE_SETUP_FACT,
"approval_phrase_setup_codex": _CODEX_SETUP_FACT,
"approval_phrase_setup_gemini": _GEMINI_SETUP_FACT,
```

`mcp_registration.ADAPTERS` has five agents. `pi` and `hermes` were never added, and both use the
`refs_braced` capability — the `${NAME}` form Pi expands from its own launch environment, which is
exactly the fact a Pi user cannot infer and the one the reporting session needed.

Two hand-kept copies made the gap invisible:

1. `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` — a dict of the three agents' entry keys with **no production
   reader**; its only consumer was
   `tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_hint_uses_verified_registration_keys`,
   which iterated it. The guard therefore validated the guidance against the incomplete copy of the
   truth it was supposed to police.
2. Literal key sets in two test files (`_GUIDANCE_KEYS`, and the `guidance_keys` set in
   `tests/test_mcp_schema.py`) that also listed the same three agents.

This is the "broken in production, green in tests" shape: the corpus was taught to agree with the
defect.

## 2. Measured evidence

```text
$ grep -rn "_APPROVAL_PHRASE_AGENT_ENTRY_KEYS" src/ tests/ scripts/
src/sofer/mcp_server.py:237: _APPROVAL_PHRASE_AGENT_ENTRY_KEYS: dict[str, tuple[str, ...]] = {
tests/test_mcp_server.py:370:        for agent, keys in ms._APPROVAL_PHRASE_AGENT_ENTRY_KEYS.items():
```

RED, after the guard was rewritten to derive from the registry:

```
$ uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q -k "HintContentActionable or approval"
5 failed, 13 passed
E  Extra items in the left set: 'approval_phrase_setup_pi', 'approval_phrase_setup_hermes'
```

GREEN: `18 passed`.

## 3. The edits

### 3.1 `src/sofer/mcp_server.py`

| Site | Change |
| --- | --- |
| imports | `from . import mcp_registration as registration` (the registry is the single source; `mcp_registration` imports only stdlib + `._toml`/`._yaml`, so there is no cycle). |
| `_ENV_CAPABILITY_FACTS` (new) | `capability -> (reference form the registration persists, prose template)`. The form is interpolated as `{form}` because the braced form contains literal braces `str.format` would otherwise read as a field. |
| `_approval_phrase_setup_fact(agent)` (new) | One capability lookup, one `.format`. |
| `_approval_phrase_setup_facts()` (new) | `{agent: fact}` for `registration.AGENT_NAMES`, read at **call** time so a patched registry is honoured. |
| deleted | `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`, `_OPENCODE_SETUP_FACT`, `_CODEX_SETUP_FACT`, `_GEMINI_SETUP_FACT`. |
| `_approval_phrase_guidance_hints()` | The setup block is unpacked from `_approval_phrase_setup_facts()`; the process-start facts, the `action` key, the flatness invariant and the key order (setup block before `approval_phrase_verify`) are unchanged. |

### 3.2 tests

- `tests/test_mcp_server.py`: `_GUIDANCE_KEYS` derives the `approval_phrase_setup_*` members from
  `registration.AGENT_NAMES` (the exact-set pin survives, now registry-driven); the per-agent guard
  iterates the registry and cross-checks each fact against the real `build_entry` output (field name
  and reference form, with the `none` capability asserting that no environment is forwarded); two new
  tests cover the capability table and a sentinel agent patched into `ADAPTERS` + `AGENT_NAMES`.
- `tests/test_mcp_schema.py`: the payload-shape set derives from `mcp_registration.AGENT_NAMES`.

### 3.3 `openspec/specs/mcp-server/spec.md` (APX-01)

The per-agent clause now requires coverage of **every** agent in the registry and derivation from its
`env` capability (naming the field and the reference form actually written), and two scenarios are
added. No requirement added or removed; the flatness, namespacing, NEVER-LEAK and refusal-message
clauses are untouched.

## 4. Rejected alternative

Keeping the three constants and adding two more. It fixes today's symptom while leaving both hand-kept
copies in place, so the next agent added to `ADAPTERS` drifts exactly the same way — the defect is the
parallel representation, not the missing strings.

## 5. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real red-then-green (§2), including
one self-inflicted regression the tests caught (`KeyError: 'NAME'`, §3.1).

## 6. Risks

See `proposal.md` §5. The one worth a reviewer's attention: the payload gains two keys, which is
additive and pinned by a registry-derived exact-set assertion.

## 7. Rollback

Revert-only (§6 of the proposal).

## 8. Success criteria

SC-1..SC-5 of `proposal.md` §7.
