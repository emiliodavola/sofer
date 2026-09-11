---
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:befb36e8735d2a957ef295a27e18e1a8e2a4faa40dfc6c3f154153fc14bdfdac
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 4/4
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:c9d78c563566b7530a90ac91332fe4c8b774d7fcb232c8a199aa5dfe746a3158
build_command: uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && git diff --check
build_exit_code: 0
build_output_hash: sha256:4348845146ec373cf5c30eca900aceb4a81fe1b51ffdf8f1b4416dc140e4d402
---

# Verify Report: 2026-09-11-fix-auth-status-hints

**Change:** `2026-09-11-fix-auth-status-hints` · **Branch:** `fix/144-auth-status-hints` (base `dev`, HEAD `7d5cc31`) · **Issue:** GitHub #144 ONLY
**Verified revision:** working tree, uncommitted — `sha256:befb36e8…` of `git diff` over the 3 changed files (`src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `tests/test_mcp_schema.py`; 390 insertions / 8 deletions; test files 100 % additive — 263 added, 0 deleted).
**Verifier posture:** independent, adversarial; no executor test was trusted as-is. All claims were re-derived from source, re-executed, and stress-tested with mutation runs.

> NOTE — The change is **PASS for issue #144** (hint/message contract + tests). It is **NOT archive-ready**: the 3 remaining unchecked rows in `tasks.md` are parent-owned delivery steps (`<!-- sdd-owner: parent -->`: commit, PR #1, post-apply bounded review). No unchecked *implementation* task remains. Archive also depends on the parent's commit/PR step and on the user-owned merge authorization.

## 1. Verdict per acceptance criterion (issue #144)

| # | Acceptance criterion (issue #144) | Verdict | Independent evidence |
|---|---|---|---|
| 1 | With `approval_configured:false`, `hints` carries actionable per-agent guidance (setup + restart requirement), not only `{"action":"configure_approval_phrase"}`; keys `approval_phrase_*` and `approval_phrase_restart_required` present in the `auth_status` envelope | **PASS** | Independent probe through the real in-memory `Client` boundary (not via the change's tests): on-wire `hints` = `action` + 9 `approval_phrase_*` keys (`env_var`, `when`, `where`, `restart`, `restart_required`, `setup_opencode`, `setup_codex`, `setup_gemini`, `verify`); `approval_phrase_restart_required is True`; `approval_phrase_env_var == "SOFER_MCP_APPROVAL_PHRASE"`; every value a flat scalar; bare `approval_phrase` key absent when unconfigured. Source of truth: `_approval_phrase_guidance_hints()` (`mcp_server.py:821-853`), merged at the unconfigured branch (`mcp_server.py:1783-1790`). |
| 2 | `PUBLISH_APPROVAL_NOT_CONFIGURED` message mentions restart **and** launcher-env | **PASS** | `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` (`mcp_server.py:238-247`) starts verbatim with `"publish is disabled:"` and interpolates `_PHRASE_READ_ONCE_FACT` + `_APPROVAL_PHRASE_ENV_VAR` + `_PHRASE_LAUNCH_ENV_FACT` ("must be in the environment of the process that launches sofer-mcp - a value set in a separate shell or terminal does not reach the server") + `_PHRASE_RESTART_FACT` ("a full restart of the agent/server host process is required"). `_error_envelope` renders `message` into `output` (`mcp_server.py:891`), so the wording is user-visible. Independent helper probe: `hints == {"action": "configure_approval_phrase"}` exact, `output == message`, prefix kept. |
| 3 | Unit tests cover hint/message content (10 new) | **PASS** | `--collect-only -k "TestHintContentActionable or TestApprovalNotConfiguredMessage"` → **exactly 10** tests (7 + 3), matching design D5's T1–T10 names one-for-one. Non-vacuity proven by mutation (see §5). |

## 2. Spec coverage (APX-01 — 4/4 scenarios)

| Scenario | Status | Tests (re-run green) |
|---|---|---|
| Unconfigured approval hint is actionable | **PASS** | `TestHintContentActionable::{test_auth_status_unconfigured_hint_is_actionable, …_restart_required_is_true, …_hints_are_flat_scalars, …_configured_hints_have_no_guidance_keys}` + extended `test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured` |
| Publish refusal message carries the same process-start semantics | **PASS** | `TestApprovalNotConfiguredMessage::{test_publish_approval_not_configured_message_process_start_semantics, test_publish_refusal_hints_unchanged_exact_dict}` + extended `TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed` |
| Guidance message and hints share one fact source | **PASS** | `test_approval_phrase_facts_not_drifted_between_hints_and_message` + `test_auth_status_unconfigured_hint_uses_verified_registration_keys` |
| Guidance leaks no phrase material and invents no config path | **PASS** | `test_auth_status_unconfigured_guidance_has_no_phrase_material` + `…_names_no_config_path` + extended `test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` |

No spec row is left without a test (AGENTS.md §6). Requirement count: 1 ADDED (APX-01), 0 MODIFIED, 0 REMOVED → 1/1.

## 3. Task completion status

`openspec/changes/2026-09-11-fix-auth-status-hints/tasks.md`: **24 `- [x]` implementation rows; 3 `- [ ]` rows remain — all explicitly parent-owned** (deferred parent actions, not implementation tasks):

```text
- [ ] Commit the work in reviewable work units (e.g., Phase 1 implementation unit, Phase 2 test unit) on `fix/144-auth-status-hints`; pre-commit hooks run ruff + mypy automatically; never `--no-verify`; never push to `main`/`dev` directly, no tag, no release, no version bump. <!-- sdd-owner: parent -->
- [ ] Create PR #1 into `dev` using `.github/PULL_REQUEST_TEMPLATE.md` with every section filled: `Closes #144` (issue linked), scope note "issue #144 only — posture fields (#145) land in the stacked PR from `fix/145-auth-status-posture`", Verification with REAL command output (pytest totals, ruff, mypy), Files-changed table, and the SDD artifacts section listing this change's proposal/spec/design/tasks. <!-- sdd-owner: parent -->
- [ ] Post-apply bounded review (parent-owned lifecycle gate): re-read `specs/mcp-server/spec.md` APX-01 against the applied diff — every MUST/SHALL row honored, pins (`test_mcp_server.py:213/783-784/786`, `test_mcp_schema.py:327/348/349`) untouched, anti-posture grep clean, no scope drift beyond issue #144; then hand the merge authorization to the user (`gh pr merge` — a GitHub owner cannot self-approve). <!-- sdd-owner: parent -->
```

No unchecked implementation task exists, so the CRITICAL completeness rule is not triggered. Archive remains blocked on the parent-owned commit + PR + bounded-review rows.

## 4. Structured status and actionContext findings

- Parent prompt supplied an explicit change selection (`2026-09-11-fix-auth-status-hints`) superseding the ambiguous native listing in the injected status JSON (`nextRecommended: "Change selection is ambiguous: …"`). Artifact store is `openspec`; the change root exists and all required artifacts are present on disk (`tasks.md`, `apply-progress.md`, `specs/mcp-server/spec.md`, `design.md`, `proposal.md`).
- `actionContext.mode: repo-local`, `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` — every changed file is inside the allowed root. No `workspace-planning` mode, no missing `allowedEditRoots`.
- `git status --porcelain` shows exactly the 3 expected modified files plus the two untracked `openspec/changes/2026-09-11-fix-auth-status-*` planning dirs. No README/README_ES, no `pyproject.toml`, no `workflow.py`, no scratch, no `.gitignore`, no TRACE.md (AGENTS.md §13 not triggered — no user-facing CLI/flag/heading change).
- Implementation ownership proven: all edits are inside the authoritative workspace; no cross-worktree or out-of-root mutation.

## 5. Commands run (exact)

```text
uv run pytest tests/ -q                                   → exit 0; 1478 passed, 6 skipped, 13 warnings in 53.04s
                                                            stdout sha256:c9d78c563566b7530a90ac91332fe4c8b774d7fcb232c8a199aa5dfe746a3158
uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q
                                                          → exit 0; 213 passed, 3 skipped in 18.55s (baseline focused, incl. all pins)
uv run pytest tests/test_mcp_server.py -q -k TestToolRoster → exit 0; 3 passed (roster still 14 callables)
uv run pytest tests/test_mcp_server.py -q --collect-only -k "TestHintContentActionable or TestApprovalNotConfiguredMessage"
                                                          → 10/197 collected (exactly the 10 new tests)
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/ && git diff --check
                                                          → exit 0; "All checks passed!" / "64 files already formatted" /
                                                            "Success: no issues found in 32 source files" / silent
                                                            stdout sha256:4348845146ec373cf5c30eca900aceb4a81fe1b51ffdf8f1b4416dc140e4d402
git diff | sha256sum                                      → befb36e8735d2a957ef295a27e18e1a8e2a4faa40dfc6c3f154153fc14bdfdac
git diff --stat                                           → 3 files changed, 390 insertions(+), 8 deletions(-)
```

Reported totals (`1478 passed / 6 skipped`) reconcile exactly with apply-progress's baseline claim: 1468 (Phase 0) + 10 new tests. `AGENTS.md §6`'s stale "1149 tests" quote and the proposal's "1468/6" forecast were both re-measured rather than trusted.

### Adversarial mutation runs (non-vacuity proof, executed outside the repo)

Two throwaway pytest plugins were injected via `PYTHONPATH` from `C:/tmp` (no repo file was created, modified, or left behind):

1. **Revert to pre-#144 behaviour** (`_approval_phrase_guidance_hints` → `{"action": …}` and the message → the old literal): `tests/test_mcp_server.py tests/test_mcp_schema.py` went **8 failed, 205 passed, 3 skipped** — every new/extended test fired. The new tests detect the exact regression they were written to prevent.
2. **Fact drift** (`_PHRASE_RESTART_FACT` mutated after import, leaving the message stale): **4 failed, 209 passed, 3 skipped** (`…facts_not_drifted_between_hints_and_message` failed with `assert 'no restart is needed, just re-call the tool' in 'publish is disabled: …'`). The drift guard is real, not decorative.

### Independent read-once probe (not a test)

Through the real in-memory `Client` boundary: built a server with `SOFER_MCP_APPROVAL_PHRASE` absent, **then** exported the variable and called `sofer_auth_status` → `_APPROVAL_PHRASE` stayed `None` before and after, `approval_configured` stayed `false`. This independently corroborates the guidance's central user-facing claim (read-once at process start ⇒ a full restart is required; setting the variable later cannot help) and confirms `grep` found exactly **one** env-read site for the variable (`mcp_server.py:2761`, inside `build_server`).

## 6. Claim-to-code independence check (per-agent guidance)

Every per-agent claim was re-derived from `src/sofer/mcp_registration.py` and reproduced by calling the real `build_entry`:

| Agent | Claimed keys (`_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`) | Real `build_entry` output | Verdict |
|---|---|---|---|
| opencode | `("type", "command", "cwd")` | `{'type': 'local', 'command': ['sofer-mcp'], 'cwd': <abs>}` — no env field | **accurate**; guidance states "no environment is forwarded" and points at the launching terminal |
| codex | `("env_vars",)` | `{'command', 'cwd', 'env_vars': ['HF_TOKEN', 'SOFER_MCP_APPROVAL_PHRASE']}` — NAMES only | **accurate**; no secret value on disk |
| gemini | `("env",)` | `{'command', 'cwd', 'env': {'HF_TOKEN': '$HF_TOKEN', 'SOFER_MCP_APPROVAL_PHRASE': '$SOFER_MCP_APPROVAL_PHRASE'}}` — NAME → `$NAME` | **accurate**; no secret value on disk |

`mcp_registration.py:158-165` matches the claims byte-for-byte (`:158-159` opencode minimal entry, `:160-162` codex `env_vars`, `:163-165` gemini `env`). The guidance names no on-disk config file or directory (independent scan for `opencode.json`, `config.toml`, `settings.json`, `.codex`, `.config` → zero hits) and leaks no phrase value, no SHA-256 of it, and no bare `approval_phrase` key.

## 7. Anti-posture gate (issue #145 isolation)

| Gate | Command | Result |
|---|---|---|
| Posture symbols absent from the whole diff | `git diff \| grep -nE "phrase_source\|server_process_id\|server_started_at\|server_version"` | **0 matches** (exit 1) |
| Posture symbols absent from the source file | `grep -nE "…" src/sofer/mcp_server.py` | **0 matches** |
| No new imports (no `datetime`/`_version`) | `git diff src/sofer/mcp_server.py \| grep -E '^\+\s*(import \|from [A-Za-z_])'` | **0 matches**; the sorted import-name list is identical between `HEAD` and the working tree (only line numbers shift) |
| No envelope/schema drift into #145 | `output_schema` and `_ERROR_ENVELOPE_SCHEMA_FIELDS` untouched in the diff | **clean** |
| ASCII-only production text | `git diff src/sofer/mcp_server.py \| grep -nP '^\+.*[^\x00-\x7F]'` | **0 matches** (the replaced em-dash literal is gone) |
| Whitespace | `git diff --check` | clean |

## 8. Pins (must survive untouched)

| Pin (documented in tasks/design) | Working-tree line | Status |
|---|---|---|
| `_is_flat_hint_dict` definition | `tests/test_mcp_server.py:215` | unchanged (was `:213` before the additive block; **test files have 0 deletions**, so every pre-existing line is byte-identical) |
| Refusal exact-dict `hints` in `test_no_phrase_configured_refuses_fail_closed` | `tests/test_mcp_server.py:929` | unchanged; the new asserts were appended **after** `:930` |
| `"publish is disabled" in envelope["output"]` | `tests/test_mcp_server.py:930` | unchanged |
| New additive twin of the exact-dict pin | `tests/test_mcp_server.py:1038` | new test `test_publish_refusal_hints_unchanged_exact_dict` — green |
| Configured branch `approval_phrase == "<from human>"` | `tests/test_mcp_schema.py:329` (was `:327`) | unchanged |
| Unconfigured `action` pin + bare-key-absent pin | `tests/test_mcp_schema.py:362-363` (was `:348-349`) | unchanged |
| `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", …)` inside `test_auth_status_no_leak` | `tests/test_mcp_schema.py:341` | unchanged (context line) |
| Tool roster = 14 callables | `TestToolRoster` | 3 passed |
| Spec-delta pointer fix `TestPublishApprovalLadder → TestPublishAuthorizationLadder` | `specs/mcp-server/spec.md:61` | done (1 occurrence, correct name) |

**Line-number drift note:** the accept-prompt quoted the schema pins as `:361/362`; in the actual working tree they are `:362-363`, shifted by the +11 additive lines that precede them plus the +2 import lines at the top of the file. Content is byte-identical — the prompt's numbers were off by one, the pins are not.

## 9. Strict TDD compliance

`openspec/config.yaml` sets `strict_tdd: false` (also `testing.strict_tdd: false`, `apply.tdd: false`), and `tasks.md` states `strict_tdd: false` with implementation ordered before tests. **Strict TDD is therefore NOT active** and no `TDD Cycle Evidence` table is required; its absence is not a finding.

Assertion-quality audit performed anyway (advisory, since the gate is inactive):

- No tautologies that matter: T1/T2/T8/T13 do compare against module constants (`hints[k] == ms._PHRASE_*` is tautological in isolation), but each is paired with a literal-content assert (`"read exactly once"`, `"process starts"`, `"separate shell or terminal"`, `"full restart"`, `"approval_configured:true"`) that pins actual wording. Mutation #2 proves the pairing works.
- No ghost loops: the `for agent, keys in …` loop in `test_auth_status_unconfigured_hint_uses_verified_registration_keys` iterates a 3-entry non-empty table and asserts presence in the **real** `build_entry` output — it can fail.
- No type-only assertions alone; no CSS/implementation-detail assertions; no smoke-only tests. The one shape-only test (`…hints_are_flat_scalars`) is legitimately shape-focused and is complemented by content tests.
- The extended exact-key-set assert (`set(hints) == _GUIDANCE_KEYS | {"action", "acknowledge_risk"}`) is a strong guard: it fails on both missing and extra (phrase-probe) keys.
- Minor: `test_publish_refusal_hints_unchanged_exact_dict` duplicates the `:929` pin — deliberate, and mutation #1 shows it correctly stays green when the guidance is removed (it pins the asymmetry the spec requires).

## 10. Review workload / PR boundary

| Field | Forecast (tasks.md) | Actual | Verdict |
|---|---|---|---|
| Changed lines | ~215 (range 200–240) | **390 insertions / 8 deletions** (398 raw) | **Deviation disclosed and harmless.** Still under the 400-line canonical review budget, so the `Chained PRs recommended: No` / single-PR decision stands; `size:exception` was neither used nor needed. The overage is ~1.8× the forecast — flagged as a **WARNING** for forecast accuracy only. |
| Files | 3 code/test files | 3 (`mcp_server.py` +135, `test_mcp_schema.py` +31, `test_mcp_server.py` +232) | matches |
| Chain strategy | `pending` → single PR | no chain used, no slice mixing | matches |
| Scope creep | none | no #145 symbol, no README, no config/pyproject change | **none** |

PR boundary matches design D6: PR #1 of 2, slice = issue #144 only; the sibling `fix/145-auth-status-posture` work is entirely absent from this diff.

## 11. Findings

**Blockers (0)** — none.

**Critical (0)** — none.

**Warnings (2, non-blocking)**

1. **Size forecast accuracy** — actual 390 inserted lines vs the ~215 (200–240) forecast. Honest disclosure in `apply-progress.md` mitigates; the change stays inside the 400-line budget. Future forecasts for this style of change should budget for mandated docstrings/comments and 10 spec-pinned tests.
2. **Duplicated env-var literal across modules** — `mcp_server._APPROVAL_PHRASE_ENV_VAR` and `mcp_registration._ENV_KEYS[1]` both spell `"SOFER_MCP_APPROVAL_PHRASE"` (AGENTS.md §4 "no duplicated logic"). Design D3 documents the reason (the CLI-side module must never import the optional-`mcp`-extra server module, and the reverse import would be needless coupling) and the new test `test_auth_status_no_leak` adds a one-line drift assert (`ms._APPROVAL_PHRASE_ENV_VAR in mcp_registration._ENV_KEYS`). Accepted-by-design; noted so it is not re-litigated at review.

**Informational (2)**

1. `_APPROVAL_PHRASE_ENV_VAR` appears twice inside the refusal message (once standalone in the `(build_server(approval_phrase=...) or VAR)` clause, once inside `_PHRASE_LAUNCH_ENV_FACT`). The spec pins each *fact constant* exactly once, which holds; the NAME repetition is intentional in design D2's template.
2. `_PHRASE_VERIFY_FACT` deliberately rides only in the `hints` surface (the message carries the 4 process-start facts) — documented as deviation 4 in `apply-progress.md` and consistent with spec scenario 3, which enumerates the 4 facts.

**Deviations from design (all disclosed in apply-progress, all acceptable)**

1. Ordering: implementation before tests (design §6 said RED-first), per `tasks.md` + `strict_tdd: false`. Non-vacuity re-proved by mutation (§5), which is stronger evidence than a claimed RED run.
2. T13 asserts on `message + output` rather than `message` alone (fastmcp boundary drops some success-envelope fields). Independently confirmed: on an `auth_status` **success** envelope `message`/`error_code` are `None`, while `_error_envelope` sets `output = message` on refusals — the chosen carrier is the reliable one.
3. Spec-delta pointer fix lives in the untracked change folder, so it is not part of the 3-file `git diff` hash; verified directly at `specs/mcp-server/spec.md:61`.

## 12. Exact blockers

None. The change passes verification for issue #144. Archive is **not** declared ready by this report: the parent-owned rows (commit → PR #1 → post-apply bounded review) and the user-owned merge authorization remain outstanding, and the executor is not authorized to perform them.
