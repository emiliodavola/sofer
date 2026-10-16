# Feature: approval-phrase-agent-coverage — issue #295

**Branch:** `fix/295-approval-phrase-agent-coverage` from `dev@b7dea51`. **Issue:** `emiliodavola/sofer#295`
**Delivery PR:** (pending — user decision) → `dev`. **SDD change:**
`openspec/changes/2026-10-15-fix-approval-phrase-agent-coverage/` (archived inside this branch, rule 15).
**Risk:** low in code, real in contract — it adds two keys to the `sofer_auth_status` unconfigured
`hints` payload (`approval_phrase_setup_pi`, `approval_phrase_setup_hermes`) and deletes a dead table.

## Goal

`sofer_auth_status` on an unconfigured server reports the approval-phrase recovery path as flat
`approval_phrase_*` hints. The per-agent setup facts cover **3 of the 5** registered agents
(`opencode`, `codex`, `gemini`): `pi` and `hermes` are missing exactly where the fact matters most —
they are the two agents whose registration persists `env: {NAME: "${NAME}"}`, the braced form a user
cannot infer. The table that is supposed to keep them in sync
(`_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`) has **no production reader**: its only consumer is the test that
should have caught this, so the guard validates the incomplete copy against itself.

## Specs

S1 (user, verbatim): "armá un roadmap de los issue type:chore"

S2 (user, verbatim): "sincronizá `dev`, podá ramas locales y comenzá la implementación de ambos issues"

S3 (issue #295 §Proposed solution, verbatim): "1. **Derive the guidance from `ADAPTERS`** (or add a
drift guard) rather than a second hand-kept table, so adding an agent cannot leave the guidance behind.
2. Add `pi` and `hermes` entries stating: the registration writes `env: {NAME: "${NAME}"}`, Pi/Hermes
expand it from their own launch environment, so the variable must be set in the terminal or process
that launches the host — and the value is never written to disk."

S4 (issue #295 §Evidence, verbatim): "`sofer_auth_status` on an unconfigured server, invoked from a
**Pi** session, returns: … There is no `approval_phrase_setup_pi` and no `approval_phrase_setup_hermes`.
The refusal message's own guidance is therefore incomplete for the host actually in use."

S5 (`openspec/specs/mcp-server/spec.md` APX-01, verbatim): "per-agent setup guidance whose named keys
MUST be the shapes `mcp_registration.py` actually writes: `sofer mcp add --agent opencode` writes only
the `mcp.sofer` entry keys `type`, `command`, `cwd` and forwards **NO** environment … `codex` persists
an `env_vars` allow-list of environment-variable NAMES, and `gemini` persists an `env` mapping of NAME
→ `$NAME` references; secret VALUES are never written to disk"

S6 (this triage, measured): `grep -rn "_APPROVAL_PHRASE_AGENT_ENTRY_KEYS" src/ tests/` returns the
definition (`mcp_server.py:237`) and **no production reader** — only
`tests/test_mcp_server.py:370-375`, which iterates that same dict. The real payload is three
hard-coded constants (`mcp_server.py:242-255`) inlined at `mcp_server.py:984-986`.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The issue's stated **mechanism** is wrong and its **symptom** is right: the guidance is not "composed from a hand-maintained dict" — that dict is dead. The real drift is three hard-coded per-agent constants plus two hand-kept key sets in tests. | S6. Recorded because the fix targets the constants and the key sets, not the dead dict alone. |
| D2 | Derive each fact from `mcp_registration.ADAPTERS[agent]["env"]` — the capability enum `none` / `allow_list` / `refs` / `refs_braced` that `build_entry` itself branches on. One capability→prose table replaces N per-agent constants, and `pi`/`hermes` collapsing into the same `refs_braced` template is exactly the point. | S3 item 1; `mcp_registration.py:469-474` branches on the same enum, so prose and registration cannot disagree. |
| D3 | **Delete** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` and the three per-agent constants. Net deletion: one dead table plus three strings replaced by one capability table and one function. | The over-engineering test: the fix removes a parallel representation of the registration shape instead of adding a second guard around it. |
| D4 | The payload change is **additive** (two new `approval_phrase_setup_*` keys); no existing key, value, prefix or flatness invariant changes, and the refusal message stays minimal (MSP-R13). | S4/S5; consumers reading `approval_phrase_setup_<their-agent>` keep working, and the exact-set test becomes derived instead of literal. |
| D5 | Issue item 3 ("emit only the asking agent's fact") is **deferred** to its own change. | It needs a host-identity mechanism that does not exist (`user_env_dir` names a config directory, not a reliable host marker) and it would break every consumer that reads its own agent's key. Not this chore's scope, and it is a payload-contract change, not a doc/coverage fix. |
| D6 | The guard is the **existing sentinel pattern**, extended: patch `ADAPTERS` + `AGENT_NAMES` with a sentinel agent and assert the hints carry its fact; plus a coverage assertion that the capability table covers every capability in `ADAPTERS`; plus deriving the two test key sets from `AGENT_NAMES`. | `tests/test_mcp_registration.py::TestSingleSourceRegistry` already patches the registry; reusing it adds no new machinery, and deriving the key sets removes the second hand-kept copy. |
| D7 | Read the registry at **call time** inside the hint builder, never at import. | `tests/test_mcp_server.py` monkeypatches the registry, and the repo's convention is a dynamic `config` read at call time; an import-time constant would make the sentinel guard untestable. |

## Tasks

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | RED: the guidance covers **every** registered agent, the fact text names the field `build_entry` really writes (and the braced vs bare form), the capability table covers every capability, and a sentinel agent flows into the hints | S3 S4 S5 D2 D6 | inline | pending | — |
| T2 | Derive the facts from `ADAPTERS[agent]["env"]`; delete the dead table and the three constants; add `pi`/`hermes` keys | S3 D2 D3 D4 D7 | inline | pending | — |
| T3 | Derive the two test key sets (`_GUIDANCE_KEYS`, `test_mcp_schema.py` guidance set) from `registration.AGENT_NAMES` | S5 D6 | inline | pending | — |
| T4 | APX-01 spec delta: per-agent guidance covers every registered agent and is derived from the registry capability | S5 | inline | pending | — |
| T5 | Gates: focused tests, full suite, ruff/format/mypy/pyright, mapping checker | — | inline | pending | — |
| T6 | Archive the change in the branch, commit, and report the PR decision | — | inline | pending | — |

## Log

L1 (2026-10-16, user, verbatim): "armá un roadmap de los issue type:chore"

L2 (2026-10-16, this session, read-only triage): the label has only two open issues (#294, #295), both
`docs(mcp)`, sharing one root class — an agent-facing fact hand-maintained in parallel to the source
that owns it, with a guard that validates the copy against itself. Findings: the #295 dict has no
production reader; `ADAPTERS[agent]["env"]` is the real single source; the sentinel guard pattern
already exists; #294's stale text is only two param descriptions plus two README rows (the CLI sections
already say `cache/profiles`).

L3 (2026-10-16, user, verbatim): "sincronizá `dev`, podá ramas locales y comenzá la implementación de
ambos issues" — implementation authorised for #295 and #294. `dev` fast-forwarded to `origin/dev`
(`b7dea51`) and 7 merged local branches pruned before the first edit.
