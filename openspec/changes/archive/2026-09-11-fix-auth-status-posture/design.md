# Design: restart-proof posture fields on `sofer_auth_status` (issue #145)

Change `2026-09-11-fix-auth-status-posture` — **PR #2** of the auth_status split, stacked on
`dev` (sibling #144 hints/guidance MERGED via PR #158 / `cf27584`, untouched here). Scope:
**issue #145 ONLY** — add `phrase_source`, `server_process_id`, `server_started_at`,
`server_version` to the `sofer_auth_status` envelope + `output_schema` so a claimed restart
is verifiable. The phrase itself (or any derived value) NEVER appears in any posture field.

Reference combined planning at `C:\tmp\sofer-ref\combined\` was checked and is **not
accessible (ENOENT)**; all design decisions below are carried by and reused from
`proposal.md` (D3 phrase_source / D7 started_at semantics preserved), re-verified against
the actual code in this session.

---

## 1. Inputs reviewed (this phase)

| Input | Location | Verdict |
|---|---|---|
| Proposal (decisions source) | `openspec/changes/2026-09-11-fix-auth-status-posture/proposal.md` | All decisions reused, not re-derived |
| Spec delta (5 scenarios, MODIFIED 10.8 only) | `openspec/changes/2026-09-11-fix-auth-status-posture/specs/mcp-server/spec.md` | No ADDED/REMOVED sections; APX-01 untouched |
| Canonical spec | `openspec/specs/mcp-server/spec.md:420-432` (10.8) + `:434+` (APX-01) | Delta composes by diff at archive |
| Code — globals | `src/sofer/mcp_server.py:284-285` (`_SERVER_ROOT`, `_APPROVAL_PHRASE`) | Four posture globals are new; none exist |
| Code — phrase read | `src/sofer/mcp_server.py:2761-2767` (inline arg > `os.environ.get(...)` > blank→None) | Refactored into the pure helper; behavior preserved |
| Code — envelope | `src/sofer/mcp_server.py:1800-1813` | Additive fields only; all current asserts partial-key (verified: no `set(envelope)` / exact-key equality anywhere in `tests/test_mcp_*.py`) |
| Code — schema | `src/sofer/mcp_server.py:2507-2523` | 4 additive properties; `required` stays `["ok","exit_code","output"]`; no `enum` anywhere in file |
| Code — imports | `src/sofer/mcp_server.py:52-101` | `datetime`/`timezone` and `_version.get_version` are new imports |
| `_version.get_version()` | `src/sofer/_version.py` | lru_cached, never raises, non-empty; imports only `importlib.metadata` — no cycle |
| Tests | `tests/test_mcp_server.py`, `tests/test_mcp_schema.py` | Pins enumerated in §7 |

---

## 2. Design decisions (each with rationale)

### D1 — Imports

`mcp_server.py` imports section gains exactly two lines:

```python
from datetime import datetime, timedelta, timezone
from ._version import get_version
```

- `timedelta` is needed for the 1 µs monotonic bump (`datetime.fromisoformat(prev) + timedelta(microseconds=1)`).
- `_version` imports only `importlib.metadata` — no sofer package imports, no circular-import
  risk (verified in `_version.py`); `cli.py` already consumes `get_version()`.
- No new dependencies; no `pyproject.toml` change.

### D2 — Four never-`None` posture globals (+ monotonic state), exact names/types

Placed in the "Server state + execution lock" section next to `_SERVER_ROOT`/`_APPROVAL_PHRASE`
(`:284-285`), **after** the `_next_started_at` helper definition (order matters: the module
defaults call it at import time):

```python
_PhraseSource = Literal["env", "explicit", "none"]

# Posture state (issue #145): process-lifecycle metadata captured at build_server
# and reported by sofer_auth_status. Defaults are never None so a directly-called
# sofer_auth_status without build_server still returns a well-typed envelope.
_PHRASE_SOURCE: _PhraseSource = "none"
_SERVER_PROCESS_ID: int = os.getpid()
_SERVER_STARTED_AT: str = _next_started_at()
_SERVER_VERSION: str = get_version()
```

| Global | Type | Module default | Rationale |
|---|---|---|---|
| `_PHRASE_SOURCE` | `_PhraseSource` (alias of `Literal["env","explicit","none"]`) | `"none"` | The fail-closed default: no server built ⇒ no phrase ⇒ `"none"`. Preserves the invariant `"none"` ⟺ `approval_configured is False` even for a direct call |
| `_SERVER_PROCESS_ID` | `int` | `os.getpid()` | Non-`None` int default so the envelope is typed; **authoritative capture is in `build_server`** (the mandate's "no module import-time" decision — the module default is a free OS syscall that equals the build-captured value in the same process, so the distinction is semantic, not observable) |
| `_SERVER_STARTED_AT` | `str` | `_next_started_at()` | Needs a valid ISO µs string for typing; one `datetime.now(utc)` call at import (cheap, and the very first stamp in the process needs no bump) |
| `_SERVER_VERSION` | `str` | `get_version()` | **DÓNDE — import vs build_server: both.** The module default must be a real non-empty value (no `None`, no duplicated literal fallback — AGENTS.md rule 1/4), and `get_version()` is `lru_cache`d: the module default warms the cache, so `build_server`'s assignment is a cache hit with **zero marginal import-time cost** (one `importlib.metadata.version` read total, paid only when `mcp_server` is imported). The cons of build_server-only (default would need `None` or a hand-copied sentinel, breaking never-`None`/no-duplication) outweigh the ₵µs saved — rejected. Authoritative capture remains in `build_server` |

### D3 — `_next_started_at()` helper (single source for the format + monotonic bump)

Module state above the globals:

```python
_last_started_at: str | None = None
```

Helper (in the server-state section, before the posture globals):

```python
def _next_started_at() -> str:
    """ISO-8601 UTC microsecond timestamp, strictly increasing across calls.

    ``datetime.now(timezone.utc)`` can return the same value for back-to-back
    calls (Windows/CPython 3.10 clock granularity); ``server_started_at`` is the
    restart-proof signal, so a 1 microsecond monotonic bump is applied against
    the previous stamp when the wall clock did not advance. Fixed-width
    ``timespec="microseconds"`` plus the constant ``+00:00`` offset keep the
    lexicographic ordering valid.
    """
    global _last_started_at
    stamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    if _last_started_at is not None and stamp <= _last_started_at:
        stamp = (datetime.fromisoformat(_last_started_at) + timedelta(microseconds=1)).isoformat(
            timespec="microseconds"
        )
    _last_started_at = stamp
    return stamp
```

- **Format**: `YYYY-MM-DDTHH:MM:SS.ffffff+00:00` — `timespec="microseconds"` is **mandatory**
  (default `"auto"` drops the fraction on whole-µs stamps and emits 3 digits on multiples of
  1000, breaking both the µs requirement and the fixed-width lexicographic ordering).
  Constant `+00:00` offset ⇒ string comparison == chronological comparison.
- **Bump**: against the module `_last_started_at` (chosen over a build_server-local variable —
  the helper is then unit-testable in isolation and is the single source for the format used
  by both the module default and the build_server capture). Lexicographic `<=` compare, then
  re-serialize from parse+1µs with the same fixed-width format so ordering stays valid forever.
- **Decision from the mandate** ("variable module `_last_started_at` dentro de build_server o
  helper `_next_started_at()`"): **helper** — see rationale above.

### D4 — `_resolve_approval_phrase()` pure helper (single env read, mirrors the existing read)

```python
def _resolve_approval_phrase(explicit: str | None) -> tuple[str | None, _PhraseSource]:
    """Resolve the approval phrase exactly once, mirroring build_server's single read.

    Precedence: explicit argument > SOFER_MCP_APPROVAL_PHRASE > none. A blank or
    whitespace-only value (explicit or env) is treated as unconfigured and maps
    to ``(None, "none")``; a blank explicit argument SHALL NOT fall back to the
    environment. Performs exactly one environment read.

    Returns:
        ``(normalized_phrase, source)`` — the fail-closed phrase (None when
        unconfigured) and the configuration path that produced it.
    """
    if explicit is not None:
        if explicit.strip():
            return explicit, "explicit"
        return None, "none"
    env_value = os.environ.get(_APPROVAL_PHRASE_ENV_VAR)
    if env_value and env_value.strip():
        return env_value, "env"
    return None, "none"
```

| Configuration | `_APPROVAL_PHRASE` | `approval_configured` | `phrase_source` |
|---|---|---|---|
| `build_server(approval_phrase="x")` | `"x"` | `True` | `"explicit"` |
| no arg, `SOFER_MCP_APPROVAL_PHRASE="x"` | `"x"` | `True` | `"env"` |
| no arg, env absent | `None` | `False` | `"none"` |
| no arg, env `""` / `"   "` | `None` | `False` | `"none"` |
| `approval_phrase=""` while env set | `None` | `False` | `"none"` (no env fallback) |

- **Behavior-preserving refactor**: the old inline `approval_phrase if approval_phrase is not
  None else os.environ.get("SOFER_MCP_APPROVAL_PHRASE")` + blank→None is reproduced exactly
  (blank explicit never reaches the env — the arg branch wins and normalizes to `None`).
  Existing pins `test_blank_phrase_treated_as_unconfigured` (env `""`) and the
  `TestHintContentActionable` no-phrase paths stay green by construction.
- **Bonus within scope**: the helper uses the module constant `_APPROVAL_PHRASE_ENV_VAR`
  instead of the inline literal `"SOFER_MCP_APPROVAL_PHRASE"` that `build_server` currently
  hardcodes at `:2761` — single fact source (AGENTS.md rule 1/4); same string, no drift.
- **Read-once contract**: this is the ONLY env read for the phrase in the whole change; the
  envelope/tool never re-read `os.environ` (all envelope reads are globals — see D6).

### D5 — `build_server` capture (top of function, before `_FastMCP(...)`)

```python
global (
    _SERVER_ROOT,
    _APPROVAL_PHRASE,
    _PHRASE_SOURCE,
    _SERVER_PROCESS_ID,
    _SERVER_STARTED_AT,
    _SERVER_VERSION,
)
_SERVER_ROOT = Path(root).expanduser().resolve() if root is not None else Path.cwd().resolve()
_APPROVAL_PHRASE, _PHRASE_SOURCE = _resolve_approval_phrase(approval_phrase)
_SERVER_PROCESS_ID = os.getpid()
_SERVER_STARTED_AT = _next_started_at()
_SERVER_VERSION = get_version()
server = _FastMCP("sofer", instructions=_PHASED_INSTRUCTIONS)
```

- Capture order matters only for the started_at monotonic bump (each build takes the next
  stamp); all four are captured before registration so every tool call sees the built posture.
- The one-server-per-process warning block (`:2725-2736`) is extended to name the new globals
  (`_PHRASE_SOURCE`, `_SERVER_PROCESS_ID`, `_SERVER_STARTED_AT`, `_SERVER_VERSION`) — the
  last-built posture inherits for every tool call, same as root/phrase today.
- `build_server` docstring gains the posture-capture contract: phrase + source resolved once
  here; pid/started-at/version captured here; the running server never re-reads the
  environment; restart required for changes (ties into `_PHRASE_READ_ONCE_FACT` wording).
- **No new lock, no `_reload_tool_config` touch** — posture is process-lifecycle state,
  orthogonal to per-call `[tool.sofer]` reload.

### D6 — Envelope (`sofer_auth_status` return dict), additive only

Insert after `"requires_approval_phrase"` (reads globals only — **never `os.environ`**):

```python
"approval_configured": approval_configured,
"requires_approval_phrase": requires_approval_phrase,
"phrase_source": _PHRASE_SOURCE,
"server_process_id": _SERVER_PROCESS_ID,
"server_started_at": _SERVER_STARTED_AT,
"server_version": _SERVER_VERSION,
"next": _workflow_next("sofer_auth_status", config),
```

- `ok` / `exit_code` / `hints` / `next` / `config_errors` semantics untouched.
- Verified safe: no existing test asserts exact key-set equality on the envelope
  (grep for `set(envelope)` / `.keys() ==` / `== set(` across `tests/test_mcp_*.py` → no
  matches); all current auth_status asserts are partial-key.
- `approval_configured = _APPROVAL_PHRASE is not None` at `:1776` stays; coupled with D4's
  invariant, `phrase_source == "none"` ⟺ `approval_configured is False` always holds.

### D7 — Tool docstring (`sofer_auth_status`)

The "The envelope carries two approval-posture fields" paragraph is extended to document the
four posture fields with types/domains:

- `phrase_source` — `"env" | "explicit" | "none"`; precedence prose (explicit
  `approval_phrase` argument > `SOFER_MCP_APPROVAL_PHRASE` > none; blank → `"none"`, blank
  explicit never falls back to env); captured **exactly once at `build_server`** from the
  same read that resolves the phrase; never re-derived at tool-call time — env changes need a
  full restart.
- `server_process_id` — `os.getpid()` of the hosting process, captured at `build_server`;
  **process-scoped** (stable for the process life).
- `server_started_at` — ISO-8601 UTC microsecond timestamp captured at `build_server`;
  differs and strictly increases across builds — **the restart-proof signal**.
- `server_version` — package version from installed metadata (`_version.get_version()`),
  non-empty, never raises.
- Never-leak extension: "the phrase, any phrase-derived value, and the configured env value
  never appear in any posture field — `phrase_source` describes the configuration path only."
- APX-01 guidance pointer (variable NAME + read-once + launcher-env + restart facts) stays as-is.

### D8 — `output_schema` (additive, no `enum`, `required` untouched)

Insert after `"requires_approval_phrase"` in `_register_tools` (`:2511-2520`):

```python
"phrase_source": {
    "type": "string",
    "description": '"env" | "explicit" | "none" — the configuration path that produced '
    'approval_configured (explicit approval_phrase argument > SOFER_MCP_APPROVAL_PHRASE > '
    'none), captured once at build_server; never the phrase itself or any derived value.',
},
"server_process_id": {
    "type": "integer",
    "description": "os.getpid() of the hosting process at build_server — process-scoped, "
    "never a cross-restart signal.",
},
"server_started_at": {
    "type": "string",
    "description": "ISO-8601 UTC timestamp (microsecond precision) captured at "
    "build_server — differs and strictly increases across builds; the restart-proof signal.",
},
"server_version": {
    "type": "string",
    "description": "Package version from installed metadata (_version.get_version()), "
    "non-empty, never raises.",
},
```

- `required` stays `["ok", "exit_code", "output"]` — **unchanged** (schema pins in
  `test_output_schema_typed` / `test_sofer_init_identity_fields_in_schema` assert this exact
  list; additive properties are safe).
- **No `enum`** — no enum precedent anywhere in this file; the domain is asserted in tests and
  documented in the description (same pattern as the existing `token` string property).

### D9 — Module docstring security bullet

The final security bullet ("The token and approval phrase are never logged, returned, or
placed in docstrings or resources...") gains: the four posture fields are non-secret
process-lifecycle metadata; `phrase_source` reports the configuration path only; the phrase
or any derived value never appears in them.

---

## 3. Data flow

```
process start → build_server()
  ├─ _APPROVAL_PHRASE, _PHRASE_SOURCE = _resolve_approval_phrase(approval_phrase)   ← one env read
  ├─ _SERVER_PROCESS_ID = os.getpid()
  ├─ _SERVER_STARTED_AT = _next_started_at()                                         ← ISO µs + monotonic bump
  └─ _SERVER_VERSION = get_version()                                                 ← lru_cached metadata
        │
        ▼
sofer_auth_status(config)  → envelope += 4 globals (never os.environ)              → output_schema (4 additive props)
        │
        ▼
real restart (new process) → new build_server → new started_at (> prev), new pid, fresh version
```

The issue's criterion "**values differ across two `build_server()`**" is satisfied by
`server_started_at` (strictly increasing within one process thanks to the µs monotonic bump)
**plus** `phrase_source` (differs whenever the two builds' configs differ). `server_process_id`
is **process-scoped**: it equals `os.getpid()` and is identical across builds in one process —
documented as such everywhere (spec text, tool docstring, schema description, tests) and
**never asserted to differ across builds** (no drift promise, no subprocess spawning).

---

## 4. Files changed (exactly three, + this change root)

| File | Change |
|---|---|
| `src/sofer/mcp_server.py` | D1 imports; D2 globals + `_PhraseSource` + `_last_started_at`; D3 `_next_started_at`; D4 `_resolve_approval_phrase`; D5 `build_server` capture + warning/docstring; D6 envelope; D7 tool docstring; D8 output_schema; D9 module docstring |
| `tests/test_mcp_server.py` | New `TestAuthStatusPosture` class (~11 tests, §6) — additive |
| `tests/test_mcp_schema.py` | 3 additive extensions (§6) — existing asserts untouched, never relaxed |
| `openspec/changes/2026-09-11-fix-auth-status-posture/` (this change root) | `specs/mcp-server/spec.md` (already authored, spec phase), `design.md` (this phase) |

**Hard no-touch list**: `README.md`/`README_ES.md`, `pyproject.toml`, `workflow.py`,
`mcp_registration.py`, other tools' envelopes/schemas, canonical `openspec/specs/**` (merged
at archive), `TRACE.md`, `scratch/**`. Tool roster stays exactly 14 callables
(`TestToolRoster::test_exactly_fourteen_callables`).

---

## 5. Contracts & invariants (pinned by tests)

1. **`phrase_source` domain** — `∈ {"env", "explicit", "none"}`; typed `str`; no `enum` in schema.
2. **Invariant**: `phrase_source == "none"` ⟺ `approval_configured is False` — holds on all
   five configuration paths.
3. **Read-once**: `phrase_source` derived exactly once in `build_server` from the same read
   that resolves the phrase; `sofer_auth_status` reads globals only, never `os.environ`.
4. **Fail-closed**: blank/whitespace (explicit or env) ⇒ `(None, "none")`; blank explicit
   never falls back to env.
5. **Restart-proof**: within one process, `server_started_at` strictly increases across two
   `build_server()` calls (fixed-width ISO µs, `+00:00`, monotonic 1 µs bump).
6. **Process-scoped**: `server_process_id == os.getpid()`, identical across builds in one
   process — never asserted to differ.
7. **`server_version`**: equals `get_version()`, non-empty, never raises.
8. **NEVER-LEAK**: the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean
   probe, comparison result), and the configured env value never appear in any posture field
   or any rendering of the envelope.
9. **Additive schema**: `required` remains exactly `["ok", "exit_code", "output"]`; the 4
   properties are declared on `sofer_auth_status` only (scope containment).
10. **#144 pins intact**: `hints` guidance payload, flatness invariant, exact-dict refusal
    hints, `PUBLISH_APPROVAL_NOT_CONFIGURED` message, roster — byte-for-byte in the diff.

---

## 6. Test mapping (spec scenario → test → what it asserts)

### New class `TestAuthStatusPosture` in `tests/test_mcp_server.py` (~11 tests)

Reuses `_make_dataset` / `restore_tool_config` / `_call` / `mcp_payload`; every `none`/`blank`
case does `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)` so an ambient shell
variable cannot flake CI.

| Spec scenario (delta) | Test | Asserts |
|---|---|---|
| Posture fields present in envelope and schema | `test_posture_fields_present_and_typed` | Envelope carries `phrase_source` (str, ∈ domain), `server_process_id` (int), `server_started_at` (str, ISO-8601 UTC `+00:00` with 6-digit µs), `server_version` (str, non-empty) |
| Posture fields present in envelope and schema | `test_server_version_equals_get_version` | `envelope["server_version"] == ms._SERVER_VERSION == get_version()` — equality, never a literal |
| Posture fields present in envelope and schema (scope containment) | `test_posture_fields_confined_to_auth_status` | No other tool's envelope/output_schema gains any of the 4 keys (roster-wide scan) |
| phrase_source follows configuration precedence | `test_phrase_source_explicit` | `approval_phrase="x"` ⇒ `"explicit"`, `approval_configured:true` |
| phrase_source follows configuration precedence | `test_phrase_source_env` | no arg + env set ⇒ `"env"`, `approval_configured:true` |
| phrase_source follows configuration precedence | `test_phrase_source_none` | no arg + env delenv'd ⇒ `"none"`, `approval_configured:false` |
| phrase_source follows configuration precedence | `test_phrase_source_blank_env_is_none` | no arg + env `""`/whitespace ⇒ `"none"` (fail-closed) |
| phrase_source follows configuration precedence | `test_phrase_source_blank_explicit_beats_env` | `approval_phrase=""` while env set ⇒ `"none"` (no env fallback) |
| phrase_source follows configuration precedence (invariant) | `test_phrase_source_consistent_with_approval_configured` | `"none"` ⟺ `approval_configured is False` across all five paths (incl. direct call without `build_server` → module default `"none"`) |
| server_started_at is the restart-proof signal across server builds | `test_server_started_at_differs_across_builds` | Two back-to-back `build_server()`: second `server_started_at` differs AND is strictly greater (lexicographic); `phrase_source` reflects each build's own config path (build A: env/delenv; build B: explicit — or both same path, started_at still increases) |
| server_process_id is process-scoped | `test_server_process_id_is_host_pid` | `server_process_id == os.getpid()` in both envelopes, identical across the two builds — never asserted to differ |

### Additive schema extensions in `tests/test_mcp_schema.py` (3 touched, never relaxed)

| Test | Extension |
|---|---|
| `TestOutputSchema::test_output_schema_typed` | For `sofer_auth_status` only: the 4 properties are declared with correct types (`phrase_source`/`server_started_at`/`server_version` type `string`, `server_process_id` type `integer`); `required == ["ok","exit_code","output"]` assertion **unchanged** |
| `TestEnvelope::test_auth_status_no_leak` | Scan the serialized envelope **including the four posture fields** for phrase material (`"phrase123"` absent, no hash/probe key); `phrase_source ∈ {"env","explicit","none"}`; existing assertions untouched |
| `TestEnvelope::test_auth_status_approval_not_configured` | Additive assert `envelope["phrase_source"] == "none"` (the delenv'd no-phrase build must report `"none"`), keeping the invariant visible at the schema level; existing guidance assertions untouched |

Expected count: **1478 + 11 = 1489 passed / 6 skipped** at apply (re-verify against the
actual tail — session-supplied baseline; `config.yaml`/AGENTS.md quote stale numbers).

---

## 7. Anti-regression gate (#144 pins must stay byte-identical in the diff)

`git diff` must show **no hunks** in:

- `TestHintContentActionable` (8 tests, `tests/test_mcp_server.py:258-402`) — including
  `test_auth_status_unconfigured_guidance_has_no_phrase_material` and
  `test_auth_status_unconfigured_hints_are_flat_scalars` (flatness),
- flatness invariant `TestNextHintContract._is_flat_hint_dict` (`:215`),
- publish ladder `test_no_phrase_configured_refuses_fail_closed` (`:895`),
  `test_blank_phrase_treated_as_unconfigured` (`:943`),
  `TestApprovalNotConfiguredMessage` (`:1014-1050+`) — including
  `test_publish_refusal_hints_unchanged_exact_dict` (`hints == {"action": "configure_approval_phrase"}`)
  and `test_approval_phrase_facts_not_drifted_between_hints_and_message`,
- `TestAuthStatusValidity` (all pins partial-key — safe by construction; verified),
- `TestToolRoster::test_exactly_fourteen_callables`,
- canonical spec APX-01: delta has **no** `## ADDED`/`## REMOVED` section (grep gate); APX-01
  exists only in the canonical file during this phase; merge at archive = 10.8 replaced +
  everything else preserved.

Verification commands (apply phase):

```bash
uv run pytest tests/ -q                                   # expect 1489 passed / 6 skipped (tail literal)
uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q   # focused (pins + new)
uv run mypy src/                                          # CI gate; never commit --no-verify
ruff check . && ruff format . --check && git diff --check
git diff --name-only                                      # exactly the 3 source/test files + openspec change root
```

---

## 8. Delivery

- Branch `fix/145-auth-status-posture` (base `dev`, #144 already merged) — **PR #2 stacked**.
- PR via `.github/PULL_REQUEST_TEMPLATE.md` with REAL command output + SDD artifacts section
  (proposal/spec/design paths + §6 spec-scenario→test map).
- No tag, no release, no version bump (hatch-vcs derives from tags — untouched).
- Review budget: well under the 400-line threshold (bulk is additive test coverage; 3
  source/test files + this change root). `ask-on-risk`: any overrun pauses for a decision.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phrase leak via a posture field or docstring line | Low | Metadata-only fields; never-leak extended (contract 8); `test_auth_status_no_leak` scans the serialized envelope incl. the 4 fields |
| pid pitfall — asserting pid "differs across builds" (guaranteed failure: one process, one `os.getpid()`) | High if direction missed | Criterion anchored on `server_started_at` + `phrase_source`; pid asserted `== os.getpid()` and identical across builds (contract 6); no subprocess spawning |
| `phrase_source` fail-closed mislabel (blank env / blank explicit) | Med | D4 single capture point mirroring the existing read; blank always ⇒ `"none"`; invariant test pins `"none"` ⟺ `approval_configured is False` on all five paths |
| Clock granularity — identical `datetime.now()` for back-to-back builds (Windows/CPython 3.10) | Med | `timespec="microseconds"` fixed-width + 1 µs monotonic bump in `_next_started_at()`; lexicographic comparison stays valid (`+00:00`) |
| Breaking canonical APX-01 / #144 pins | Low | MODIFIED 10.8 only; §7 grep gate; pin hunks checked in the diff; `TestHintContentActionable` untouched |
| `server_version` import layering / cycle | Low | `_version` imports only `importlib.metadata` (verified); lru_cached; test pins equality, not a literal |
| Import-time cost of `_SERVER_VERSION`/`_SERVER_STARTED_AT` defaults | Low | One lru_cached metadata read + one `datetime.now()` per import, paid only when `mcp_server` is imported; build_server assignments are cache/state hits afterward (D2 rationale) |
| Ambient env flake in tests (a developer's shell has `SOFER_MCP_APPROVAL_PHRASE` set) | Med | Every `none`/`blank` case `delenv`s the var explicitly (`raising=False`); env case `setenv`s a fixed value |
| Baseline drift in the PR | Low | Re-verify the tail at apply; report actual numbers |

---

*Branch `fix/145-auth-status-posture`. Artifact store: openspec (this file). Reuses decisions
from `proposal.md` (capture-at-build_server, phrase_source precedence + invariant, µs +
monotonic bump, pid process-scoped, 4 additive schema fields, no enum, pins #144 intact).*