# Tasks: fix-approval-phrase-agent-coverage

**Change** `2026-10-15-fix-approval-phrase-agent-coverage` (GitHub **#295**) · branch
`fix/295-approval-phrase-agent-coverage` from `dev@b7dea51` · store **hybrid**.

**One-line outcome:** the unconfigured-approval guidance carries one setup fact per **registered**
agent, derived from the registration capability `build_entry` itself branches on, and the two
hand-kept copies that let `pi`/`hermes` fall behind are gone.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real red-then-green:

- **RED (measured):**
  `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q -k "HintContentActionable or approval"`
  → **5 failed, 13 passed**. `Extra items in the left set: 'approval_phrase_setup_pi',
  'approval_phrase_setup_hermes'` on the derived guidance set; `AttributeError` on
  `_ENV_CAPABILITY_FACTS`; the sentinel agent produced no key; and the exact-set pin failed because
  the guidance genuinely lacked two agents.
- **GREEN (measured):** the same selection → **18 passed**.
- **REFACTOR:** the first GREEN attempt raised `KeyError: 'NAME'` — a template containing the literal
  `${NAME}` fed to `str.format` reads the braces as a field. The capability table now carries the
  reference form as a separate field interpolated as `{form}`, and the single-lookup comprehension
  became `_approval_phrase_setup_fact(agent)` (one capability lookup per agent).

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: guidance covers every registered agent; each fact names the field and form `build_entry` writes; the capability table covers every capability; a sentinel agent flows in | done | `5 failed, 13 passed` |
| T2 | Derive the facts from `ADAPTERS[agent]["env"]`; delete the dead table and the three constants; add the two missing agents | done | `18 passed` |
| T3 | Derive `_GUIDANCE_KEYS` (test_mcp_server) and the guidance set (test_mcp_schema) from `registration.AGENT_NAMES` | done | same GREEN run |
| T4 | APX-01 spec delta + canonical `mcp-server` spec | done | `openspec/specs/mcp-server/spec.md` |
| T5 | Gates: focused tests, full suite, ruff/format/mypy/pyright, mapping checker | done | see `archive-report.md` |
| T6 | Archive the change in the branch and commit | done | see `archive-report.md` |
