---
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:93e6ce898b89eab3a964167b5276dfae5b1d4c4074222a5b1f4b078b140feb24
verdict: pass
blockers: 0
critical_findings: 0
requirements: 0/0
scenarios: 5/5
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:33b09bba1726f5013a68440f3981f5acc987d56fa42c1eb9460ad992e755bf6a
build_command: uv run ruff check src/ tests/ && uv run mypy src/ && git diff --check
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
---

# Verify Report — restart-proof posture fields on `sofer_auth_status` (issue #145)

Change `2026-09-11-fix-auth-status-posture` — PR #2, branch `fix/145-auth-status-posture`
(base `dev`, sibling #144 merged at `cf27584`), working-tree diff (**no commit** — verified:
`git log --oneline -1` = `cf27584`, `git status --porcelain` = 3 modified files + untracked
change root). Verification was **independent and adversarial**: direct code/diff inspection,
a standalone re-derivation probe written from the spec (not the change's tests), the spec
scenario tests, the #144 pins, and every project gate.

> NOTE: verification performed against the working-tree diff on branch
> `fix/145-auth-status-posture` (HEAD `cf27584`), no commit made. Parent lifecycle tasks
> 4.1–4.3 (commit split, PR #2, bounded review) remain open and are **parent-owned**, not
> implementation blockers. `openspec/config.yaml` declares `strict_tdd: false` — strict TDD
> evidence gates are not active; assertion quality was still audited (no tautologies, no
> ghost loops, all assertions bind real values).

## Structured status / actionContext findings

- Native status (authoritative openspec store): `state: ready` for verify; `applyState:
  all_done`; `taskProgress 38/38` implementation tasks complete, `unchecked: []`;
  `deferredParentActions 3/3` (4.1–4.3, parent-owned); `dependencies: sync/archive blocked
  until clean verify`; `nextRecommended: sdd-verify`. No `blockedReasons`.
- `actionContext`: `repo-local`, `allowedEditRoots [C:\Users\elaze\Desktop\sofer]` — all
  3 changed files live inside the root; no warnings. Verified: `git diff --name-only` =
  `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `tests/test_mcp_schema.py` (plus
  the untracked change root) — **nothing on the Scope Guards list**.

## Verdict per issue #145 acceptance criterion

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | 4 fields present in envelope AND documented in docstring | **PASS** | Envelope `src/sofer/mcp_server.py:1890-1893` carries `phrase_source`, `server_process_id`, `server_started_at`, `server_version` inserted after `"requires_approval_phrase"` (reads globals only, never `os.environ`). Tool docstring (D7) documents all 4 with types/domains, precedence, capture-once at `build_server`, never-re-derived, pid process-scoped, started_at restart-proof, version non-empty/never-raises, never-leak extension + APX-01 pointer. Module docstring bullet (D9) names the 4 fields as non-secret lifecycle metadata. Independent probe P1/P7 confirmed presence in envelope and `output_schema`. |
| 2 | "Values differ across two `build_server()` calls" → anchor on `server_started_at` (µs + monotonic bump), NOT pid | **PASS** | `_next_started_at()` (`:300-323`): `datetime.now(timezone.utc).isoformat(timespec="microseconds")` + 1 µs monotonic bump when `stamp <= _last_started_at` (Windows/CPython 3.10 clock granularity rationale in docstring). Independent probe P3: two back-to-back builds → `2026-09-11T17:18:31.104574+00:00 < 2026-09-11T17:18:31.143236+00:00` (strictly increasing). P4: pid identical across builds `== os.getpid()` (process-scoped, never asserted to differ — the mandated anti-pitfall direction). `test_server_started_at_differs_across_builds` + `test_server_process_id_is_host_pid` pin both behaviors. |
| 3 | Unit tests cover fields and `phrase_source` values (11 new + 3 schema) | **PASS** | `TestAuthStatusPosture` = 11 tests (fields/typing, version equality, scope containment, 5 precedence paths + invariant incl. module-default direct call, restart-proof started_at, process-scoped pid) + 3 additive schema/envelope extensions. Ran: 14 passed (11 + 3) — see tests below. |

## Spec scenario coverage (delta 10.8: 5 new + 1 canonical)

| Scenario | Spec `*Tests:*` | Result |
|---|---|---|
| Preflight without publish (canonical, kept verbatim) | `TestAuthStatusValidity::test_missing_token_ok_false`, `test_approval_not_configured_ok_false`, `TestEnvelope::test_auth_status_no_leak` | PASS (pins, unmodified) |
| Posture fields present in envelope and schema (incl. scope containment, `required` unchanged, no `enum`) | `test_posture_fields_present_and_typed`, `test_server_version_equals_get_version`, `test_posture_fields_confined_to_auth_status`, extended `test_output_schema_typed` | PASS — also independently re-derived (probe P7: 4 typed props only on `sofer_auth_status`, `required == ["ok","exit_code","output"]`, no `enum`, roster = 14) |
| `phrase_source` follows configuration precedence (5 paths + invariant) | `test_phrase_source_explicit/_env/_none/_blank_env_is_none/_blank_explicit_beats_env/_consistent_with_approval_configured` | PASS — probe P1/P2 re-derived explicit→env transition and module-default `"none"` |
| `server_started_at` restart-proof across builds | `test_server_started_at_differs_across_builds` | PASS — probe P3 strictly-increasing |
| `server_process_id` process-scoped | `test_server_process_id_is_host_pid` | PASS — probe P4 identical + `== os.getpid()` |
| No phrase material in posture fields | extended `test_auth_status_no_leak` | PASS — probe P6: `"phrase123"`/`"envphrase"` absent from posture + envelope; `phrase_source ∈ {"env","explicit","none"}` |

## Task completion

All **38 implementation-owned tasks** are `- [x]` in `tasks.md`; **zero unchecked
implementation markers** remain (`grep -c` = 38, the only `- [ ]` rows are the 3
parent-owned lifecycle rows 4.1/4.2/4.3, preserved byte-for-byte as deferred actions) —
**no archive blocker from task checklist**. Review Workload Forecast respected: single
PR #2, no chaining, `size:exception` not used; budget measured at **406 changed lines**
(374 insertions + 32 deletions over 3 files) — inside the ~380–430 forecast and under the
~450 ask-on-risk gate; no scope creep.

## Deviations (each validated independently)

1. **`global (...)` parenthesized syntax** (D5) — invalid Python; implemented as two
   single-line `global` statements (`:2860-2861`). Logic identical; `mypy` clean.
2. **D7 docstring compressed** — full-length posture paragraph pushed the pre-"When to use"
   fragment count past the ≤10 cap in `TestDescriptions::test_descriptions_concise_no_msp_untrusted`
   (an existing DX pin). Compressed to a dot-free-identifier 2-fragment paragraph preserving
   all required facts (types/domains, precedence, capture-once, restart-proof, process-scoped,
   never-leak, APX-01). Pin verified passing (`1 passed`); live docstring inspected — all 4
   fields documented.
3. **Pre-existing ruff format drift on README/README_ES.md** — full-tree
   `uv run ruff format --check` flags exactly those 2 files; both **byte-identical to HEAD**
   `cf27584` (`git show HEAD:* | ruff format --check` exits 1; `cmp` identical) and on the
   Scope Guards no-touch list — not introduced here, not touched. Scoped check on the 3
   changed files: **3 files already formatted**.
4. Anchor-line shifts (tasks.md line refs resolved against the live file for the class
   insertion point) — documented in apply-progress; verified by hunk positions.

## #144 pin integrity (anti-regression gate)

`git diff -U0` hunk inventory — **additive only**:
- `tests/test_mcp_server.py`: hunks at `+17` (import `re`), `+33` (import `get_version`),
  and `@@ -584,0 +587,206 @@` (new `TestAuthStatusPosture` class, inserted after
  `TestAuthStatusValidity` before the 7.3 banner). **No hunks** in `TestHintContentActionable`
  (`:260-402`, 10 pins), `TestNextHintContract._is_flat_hint_dict` (`:217`),
  `TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed` (`:1103`),
  `test_blank_phrase_treated_as_unconfigured` (`:1151`), `TestApprovalNotConfiguredMessage`
  (`:1187`, incl. `test_publish_refusal_hints_unchanged_exact_dict` `:1239` and
  `test_approval_phrase_facts_not_drifted_between_hints_and_message` `:1248`),
  `TestAuthStatusValidity` (`:467`), `TestToolRoster::test_exactly_fourteen_callables` (`:423`).
- `tests/test_mcp_schema.py`: 3 additive hunks (`+246` output_schema; `+355`, `+408`
  envelope) — the guidance membership block (`guidance_keys <= set(envelope["hints"])`,
  `:393-404`) untouched.
- `src/sofer/mcp_server.py`: hunks only at D1–D9 regions (`+49` D9, `+67`/`+87` D1,
  `+294` D2–D4, `+1804` D7, `+1890` D6, `+2603` D8, `+2827`/`+2850`/`+2862`/`+2865` D5).
  No hunk touches `_approval_phrase_guidance_hints`, the `_APPROVAL_PHRASE_*` fact constants
  (`:185-245`), `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`, `sofer_publish_confirm`, or the roster.
- Canonical APX-01 untouched: delta spec has **no `## ADDED`/`## REMOVED`** (grep exit 1);
  `git status --porcelain -- openspec/specs/` empty.
- Explicit run of the pin set: **22 passed** (TestHintContentActionable, TestNextHintContract,
  TestApprovalNotConfiguredMessage, TestAuthStatusValidity, TestToolRoster::test_exactly_fourteen_callables,
  both publish-ladder fail-closed tests, schema `test_auth_status_approval_not_configured`).

## No-leak / domain audit

- `_resolve_approval_phrase` (`:326-346`) performs the **single** env read via
  `_APPROVAL_PHRASE_ENV_VAR` (fact constant `:195`); the old inline literal is gone
  (`grep 'os.environ.get("SOFER'` → no match). Precedence explicit > env > none; blank/
  whitespace ⇒ `(None, "none")`; blank explicit never falls back to env.
- Envelope reads globals only — never `os.environ` (probe P2: env change invisible to an
  already-built server; visible only after rebuild).
- `approval_configured = _APPROVAL_PHRASE is not None` (`:1857`) untouched → invariant
  `phrase_source == "none"` ⟺ `approval_configured is False` holds (probe + 7 tests).
- `server_version == get_version()`, non-empty, never raises (probe P5, equality-only test).

## Test / validation commands (all run, literal results)

| Command | Result |
|---|---|
| `uv run pytest tests/test_mcp_server.py::TestAuthStatusPosture tests/test_mcp_schema.py::TestOutputSchema::test_output_schema_typed tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak tests/test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured -q` | **14 passed in 1.41s** |
| #144 pin set (22 node IDs) | **22 passed in 1.50s** |
| `uv run pytest tests/ -q` | **1489 passed, 6 skipped, 13 warnings in 55.10s** (+11 vs baseline 1478; 0 skipped delta; no test removed/relaxed) |
| `uv run ruff check src/ tests/` | All checks passed! |
| `uv run ruff format --check src/sofer/mcp_server.py tests/test_mcp_server.py tests/test_mcp_schema.py` | 3 files already formatted |
| `uv run ruff format --check` (full-tree) | 2 files would be reformatted (README/README_ES, pre-existing at HEAD — see deviations) |
| `uv run mypy src/` | Success: no issues found in 32 source files |
| `git diff --check` | clean |
| Independent probe `verify_145_probe.py` (re-derivation: 2× build_server, envelope+schema via fastmcp Client, no-leak, version, pid, roster) | **ALL INDEPENDENT PROBES PASSED** (P1–P7) |

## Assertion quality (audit, strict-TDD inactive)

New tests are substantive: regex-fullmatch on ISO µs stamps, equality chains against
`get_version()`, roster-wide schema scan, five real config paths + module-default direct
call for the invariant, two real back-to-back builds for strict monotonicity, serialized
envelope scans for phrase material. No tautological asserts, no ghost loops (loop bodies
iterate distinct real values: `("", "   ")` env variants, 6 config cases), no
type-only-only assertions, no smoke-only tests.

## Exact blockers

None. `blockers: 0`. Remaining open rows are parent-owned lifecycle actions (4.1 commit
split, 4.2 PR #2, 4.3 bounded review + human-authorized merge to `dev`) — not verification
blockers; archive/sync remain gated on this clean verify per the status engine.