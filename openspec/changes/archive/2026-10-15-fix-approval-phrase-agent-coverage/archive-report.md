# Archive Report: The approval-phrase guidance covers every registered agent, derived from the registry

**Change**: `2026-10-15-fix-approval-phrase-agent-coverage`
**Archived to**: `openspec/changes/archive/2026-10-15-fix-approval-phrase-agent-coverage/`
**Branch**: `fix/295-approval-phrase-agent-coverage` (base `dev@b7dea51`)
**Issue**: `emiliodavola/sofer#295`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-server` | Updated | APX-01's per-agent guidance clause is rewritten: the guidance SHALL cover **every** member of `mcp_registration.AGENT_NAMES` and SHALL be derived from that registry's own `env` capability (`none` / `allow_list` / `refs` / `refs_braced`), naming the field and reference form the entry actually carries. Two scenarios are added ("Per-agent guidance covers every registered agent", "A registration capability without a fact fails the guard"). No requirement added or removed; the `action` key, the process-start facts, the restart boolean, the flatness and namespacing invariants, the NEVER-LEAK rules and the shared fact source with the refusal message are untouched. |

The canonical `openspec/specs/mcp-server/spec.md` was amended in place from the delta's `## MODIFIED
Requirements` block. `mcp-server` is a permanent declared-backlog spec, so no `## Test Mapping` table
row is added: `scripts/check_test_mapping.py` exits 0 and reports `mcp-server: 127 scenario(s),
unmapped` (was 125), and `openspec/test-mapping-registry.md` is untouched.

## Archive Contents

- `proposal.md` — present (intent, scope, D1–D7, 3 risks, rollback, SC-1..SC-5)
- `design.md` — present (the defect with both hand-kept copies, the measured RED/GREEN, the edit table,
  § 4 the rejected alternative, the `KeyError: 'NAME'` self-reflection)
- `tasks.md` — present, T1–T6 complete
- `specs/mcp-server/spec.md` (delta) — present

## Source of Truth Updated

- `openspec/specs/mcp-server/spec.md` — APX-01 as amended.
- `src/sofer/mcp_server.py` — `_ENV_CAPABILITY_FACTS` (capability → reference form + template),
  `_approval_phrase_setup_fact(agent)`, `_approval_phrase_setup_facts()`; the deduped payload in
  `_approval_phrase_guidance_hints()`; **deleted** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`,
  `_OPENCODE_SETUP_FACT`, `_CODEX_SETUP_FACT`, `_GEMINI_SETUP_FACT`; new
  `from . import mcp_registration as registration`.
- `tests/test_mcp_server.py` — registry-derived `_GUIDANCE_KEYS`; the per-agent guard cross-checks each
  fact against the real `build_entry` output; two new tests (capability coverage, sentinel agent).
- `tests/test_mcp_schema.py` — the payload-shape set derives from `mcp_registration.AGENT_NAMES`.
- `odd/tasks/approval-phrase-agent-coverage.md` — the ODD record.
- **No README / README_ES change**: they list the MCP tool surface, not the guidance keys (nothing
  documented changes).

## Verification

| Gate | Command | Result |
|------|---------|--------|
| Focused selection | `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q -k "HintContentActionable or approval"` | **18 passed** |
| RED (before the implementation) | same selection | **5 failed, 13 passed** — `Extra items in the left set: 'approval_phrase_setup_pi', 'approval_phrase_setup_hermes'` |
| Full suite | `uv run pytest tests/ -q` | **2152 passed, 9 skipped, 6 warnings** in 72.76s |
| Lint | `uv run ruff check src/ tests/ scripts/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 75 files already formatted |
| Types | `uv run mypy src/ scripts/` | Success: no issues found in 37 source files |
| Types (2nd) | `uv run pyright` | 0 errors, 1 warning (pre-existing `tomli` stub warning in `_toml.py:27`) |
| Spec↔test mapping | `uv run python scripts/check_test_mapping.py` | OK — `mcp-server: 127 scenario(s), unmapped` (was 125) |

Test-count delta from the diff: two new tests in `tests/test_mcp_server.py` (capability coverage, sentinel
agent) plus one rewritten in place; `tests/test_mcp_schema.py` changed an assertion set, no new test.

## Notes for the reviewer

1. **The issue's mechanism was wrong, its symptom was right.** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` had
   no production reader — its only consumer was the test that should have caught the gap, iterating the
   same incomplete list. The real payload was three hand-written constants. The fix removes both
   parallel copies (the dead table and the constants) rather than adding two strings.
2. **Net deletion in production**: one dead dict plus three constants replaced by one capability table
   and two small functions; the payload grew by exactly the two missing agents.
3. **Payload change is additive** and the exact-set pin in tests is now registry-derived, so a future
   agent flows in without editing a literal.
4. **Deferred, explicitly**: issue item 3 ("emit only the asking agent's fact"). It needs a host-identity
   mechanism that does not exist and would break consumers reading their own agent's key — its own
   change, and a payload-contract one.
5. **Coverage note**: `mcp_server.py` measured 91% locally before this change; the new functions are
   exercised by the tests above, so the TOTAL gate keeps its margin.
