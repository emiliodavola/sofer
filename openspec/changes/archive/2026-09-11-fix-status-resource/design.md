# Design: static `sofer://status` resource so `resources/list` is never empty (issue #146)

Change `2026-09-11-fix-status-resource` — **issue #146 ONLY**, branch `fix/146-status-resource`
(base `dev`, PR-only). Root cause: all three registered resources are URI **templates**
(`sofer://dataset/{config_path*}`, `sofer://codebook/{data_file*}`, `sofer://metadata/{data_file*}` in
`_register_resources`), which FastMCP lists under `resources/templates/list` — so `resources/list`
was empty by design (`d73c59a` post-#144+#145 state, re-verified this phase). This design registers
ONE static resource `sofer://status` (no path variables) returning a JSON posture object reusing the
#145 posture globals verbatim; `resources/list` becomes non-empty, zero tools required to read it.

Decisions carried from `proposal.md` (Q-round answers: full `root` path, `tool_count` from the
workflow registry, field names per the issue, no `_tool_execution()` wrapper, MODIFIED MSP-R07 only).
The proposal's open fastmcp-semantics question (R5) is **resolved here with installed-source
evidence** (D6).

---

## 1. Inputs reviewed (this phase)

| Input | Location | Verdict |
|---|---|---|
| Proposal (decisions source) | `openspec/changes/2026-09-11-fix-status-resource/proposal.md` | All decisions reused, not re-derived; R5 downgraded from open risk to pinned fact (D6) |
| Spec delta (choreographed test names) | `openspec/changes/2026-09-11-fix-status-resource/specs/mcp-server/spec.md` | MODIFIED MSP-R07 only; no ADDED/REMOVED; 5 choreographed `TestStatusResource` names + 2 GWT scenarios |
| Canonical spec | `openspec/specs/mcp-server/spec.md` REQ MSP-R07 | Delta composes by diff at archive; 10.8/APX-01 (from merged #145/#144) must NOT be re-added |
| Code — registration | `src/sofer/mcp_server.py:2697-2713` | `_register_resources` registers exactly 3 templates; no static resource exists |
| Code — handlers | `_resource_dataset` `:2647`, `_resource_codebook`, `_resource_metadata` | All return `str`, wrapped in `_tool_execution()`/`_capture_output()`; status handler will NOT follow this shape (D4) |
| Code — posture globals (from #145) | `mcp_server.py:290-291`, `:349-352`, `_next_started_at` `:303-323` | `_APPROVAL_PHRASE`, `_PHRASE_SOURCE`, `_SERVER_STARTED_AT`, `_SERVER_VERSION` exist, set once at `build_server`; reused verbatim |
| Code — envelope | `sofer_auth_status` `:1782`, `approval_configured = _APPROVAL_PHRASE is not None` `:1857`, posture fields `:1888-1894` | The exact identity/expressions the resource mirrors (one fact source, two surfaces) |
| Code — `build_server` | `:2823-2878` | Sets globals once; `_register_resources(server)` at `:2876`; one-server-per-process warning |
| fastmcp v3 (installed source) | `site-packages` via uv cache `fastmcp/server/server.py`, `resources/base.py`, `resources/function_resource.py`, `client/mixins/resources.py` | s. §2 D2/D6 — static-vs-template rule, dict→JSON-content auto-serialization, client accessors all pinned from installed code |
| `workflow.WORKFLOW_METADATA` | `src/sofer/workflow.py:300-394` | Exactly **14 keys** (`sofer_init`…`sofer_publish_confirm`) — matches the 14-callable roster; `tool_count` = `len(registry)` |
| Imports | `mcp_server.py:67-87` | `Any` (`:69`), `Path` (`:68`), `workflow` (`:86`) already imported — zero new imports |
| Tests | `tests/test_mcp_server.py:1483-1643` (TestResources), `:423` (roster 14) | Reuses `_make_dataset`/`_run`/in-memory `Client`; all existing pins stay unmodified |

---

## 2. Design decisions (each with rationale)

### D1 — Handler: `_resource_status() -> dict[str, Any]`, placed next to the other resource handlers

New function immediately before `_register_resources` (after `_resource_metadata`, `~:2695`):

```python
def _resource_status() -> dict[str, Any]:
    """Static posture snapshot for agents (issue #146) — non-secret
    process-lifecycle metadata; no path variables, no file reads.

    Mirrors the sofer_auth_status envelope diagnostics: approval_configured
    reflects whether the server has a non-blank approval phrase set;
    phrase_source is the configuration path that produced it ("env" |
    "explicit" | "none"); root is the resolved containment root; version and
    started_at are the #145 build-time posture globals; tool_count is the
    size of the workflow registry (MSP-R13). No secrets: the phrase, any
    phrase-derived value, and the configured env value never appear. Side
    effects: none. Network usage: none.
    """
    return {
        "approval_configured": _APPROVAL_PHRASE is not None,
        "phrase_source": _PHRASE_SOURCE,
        "root": str(_get_root()),
        "version": _SERVER_VERSION,
        "started_at": _SERVER_STARTED_AT,
        "tool_count": len(workflow.WORKFLOW_METADATA),
    }
```

- **Return type `dict[str, Any]` (not `str`, not `bytes`)** — pinned from the installed fastmcp
  source (`fastmcp/resources/base.py:194-197`, `ResourceResult._normalize_contents`): a dict (or
  list/int/float/bool/None) is auto-serialized to
  `ResourceContent(json.dumps(contents), mime_type="application/json")` → a `TextResourceContents`
  whose `.text` holds the JSON string with mime `application/json`. So the handler stays a plain
  dict, and the client accessor is **`.text`** — identical to the existing `TestResources` round-trips
  (`contents[0].text`); **no `.json` accessor, no manual `json.dumps` in the handler** (fastmcp owns
  serialization; `json.loads(contents[0].text)` in tests round-trips it).
- `Any` is already imported (`mcp_server.py:69`) and used across the module — the annotation adds
  zero imports (D5).
- Byte-identical posture semantics with the envelope: `_APPROVAL_PHRASE is not None` is the exact
  `sofer_auth_status` identity (`:1857`) — the two surfaces cannot drift (R3).

### D2 — Registration: static (no path variables) + a short `description`, after the 3 templates

In `_register_resources`, after `:2713`:

```python
    # Static (no path variables) so fastmcp lists it under resources/list —
    # the three templates above live under resources/templates/list; the
    # issue's empty-list surprise is exactly that gap.
    server.resource(
        "sofer://status",
        description=(
            "Server posture snapshot — approval_configured, phrase_source, root, "
            "version, started_at, tool_count. Non-secret process-lifecycle "
            "metadata only; no secrets, no side effects, no network."
        ),
    )(_resource_status)
```

- **Static-not-template pin** (installed source, `fastmcp/server/resource.py` / `function_resource.py:290-300`):
  fastmcp classifies by `has_uri_params = "{" in uri and "}" in uri` OR `has_func_params`.
  `"sofer://status"` has no `{}` and the handler takes no parameters ⇒ **static `Resource`** ⇒ listed
  by `server.list_resources()` (`fastmcp/server/server.py:785`) under `resources/list`, NOT by
  `list_resource_templates()` (`resources/templates/list`, `server.py:935-960`). Template-ification
  traps to avoid: adding a path param OR an injected `Context` parameter would demote it to a
  template and silently fail AC1.
- `description=` is a first-class keyword on `server.resource(uri, *, name, description, mime_type, …)`
  (`server.py:1862-1876`) — no `ResourceContent`/`ResourceResult` construction needed anywhere.
- Docstring of `_register_resources` updated: "Register the 3 resource templates" → "Register the 3
  resource templates + 1 static resource", keeping the existing `{name*}` rest-pattern rationale text.

### D3 — The payload is exactly the six issue-named fields, from the #145 globals verbatim

| Field | Source expression | Rationale |
|---|---|---|
| `approval_configured: bool` | `_APPROVAL_PHRASE is not None` | Identical semantics to `sofer_auth_status` (`:1857`); `phrase_source == "none"` ⟺ `approval_configured is False` invariant |
| `phrase_source: "env"\|"explicit"\|"none"` | `_PHRASE_SOURCE` | The configuration path only — never the phrase or any derived value; read-once contract inherited (global captured at `build_server`) |
| `root: str` | `str(_get_root())` | Resolved absolute containment root — the same root every path-bearing tool/resource anchors on (INIT-03-consistent); `_get_root()` keeps the fallback-to-cwd uniform with the rest of the module |
| `version: str` | `_SERVER_VERSION` (= `get_version()`) | Installed package version, non-empty, `lru_cache`d, never raises; issue's field name `version` wins over the envelope's `server_version` |
| `started_at: str` | `_SERVER_STARTED_AT` | ISO-8601 UTC µs stamp captured at `build_server` (`_next_started_at()`, monotonic bump); equal by construction to the envelope's `server_started_at` |
| `tool_count: int` | `len(workflow.WORKFLOW_METADATA)` | **Verified == 14** (workflow.py:300-394: `sofer_init` … `sofer_publish_confirm`) matching the 14-callable roster; derived, never a hardcoded literal (AGENTS.md rules 1/4) — a future roster change auto-bumps with zero edits here |

- `server_process_id` and anything else are deliberately NOT included (issue scope: exactly six fields).
- Never-leak by construction: the payload emits only a bool, an enum string, two `_SERVER_*` strings,
  the root path, and an int — the phrase/env value cannot appear unless the *root path itself*
  carries it (out of the resource's control; residual risk documented in §9 R2). The guard test still
  scans the serialized payload (mirrors `test_auth_status_unconfigured_guidance_has_no_phrase_material`).

### D4 — Zero side effects: no `_tool_execution()`/`_capture_output()`, no `_contained_path`/`_check_resource_size`

- The handler reads only immutable-at-runtime process globals and `len()` of an immutable
  `MappingProxyType` — nothing prints, no domain code, no config mutation ⇒ the stdout swap
  (`_capture_output`) and the config-state lock (`_tool_execution`) are deliberately **omitted**
  (proposal Q4 accepted).
- No `_contained_path`/`_check_resource_size`: there is no path argument and no file read; the
  MSP-R07 containment/size-guard/extension-allow-list clauses govern **path-bearing** resources and
  are explicitly NOT extended to this static resource (spec delta boundary sentence). No network.

### D5 — Zero new imports, zero new state, zero config changes

- `Any` (`:69`), `Path` (`:68`), `workflow` (`:86`), `_get_root` and the `_SERVER_*` globals all exist.
- No new module-level globals, no new defaults in `config.py`, no `pyproject.toml` change
  (`fastmcp>=3.4,<4` already declared), no new dependencies.
- `build_server` untouched: the handler simply reads what `build_server` already captures.

### D6 — Client-side round-trip contract (pinned from installed fastmcp, resolves proposal R5)

| Client call | Returns | Accessor used by tests |
|---|---|---|
| `await client.list_resources()` | `list[mcp.types.Resource]` (paginated, auto) | `r.uri` (== `"sofer://status"`), `r.description` |
| `await client.list_resource_templates()` | `list[mcp.types.ResourceTemplate]` | `t.uriTemplate` (the 3 templates remain listed here; status absent) |
| `await client.read_resource("sofer://status")` | `ReadResourceResult` | `contents[0].text` → `json.loads(...)` (dict auto-serialized, mime `application/json`) |

R5's fallback ("return a JSON `str` if v3 rejects a no-arg dict handler") is **not needed**: the
installed source proves no-arg static handlers and dict→JSON auto-serialization are first-class v3
behavior; the design keeps the dict return and pins the round-trip in the first RED test.

---

## 3. Data flow

```
build_server(root, approval_phrase)            # mcp_server.py:2823
  ├─ _SERVER_ROOT / _APPROVAL_PHRASE / _PHRASE_SOURCE / _SERVER_STARTED_AT / _SERVER_VERSION
  │    captured exactly once (posture globals, #145)          ── immutable-at-runtime
  └─ _register_resources(server)  (+1 static sofer://status, no path vars)
        │
        ▼  resources/list  →  client.list_resources()  →  uri == "sofer://status"   (AC1)
        ▼
_ resource_status() → dict[str, Any]   (no _tool_execution/_capture_output/_contained_path)
        │
        ▼  fastmcp ResourceResult._normalize_contents (base.py:194-197)
        │      dict → ResourceContent(json.dumps(...), mime_type="application/json")
        ▼
client.read_resource("sofer://status") → contents[0].text (JSON) → json.loads(payload)   (AC2)

Parallel surface: sofer_auth_status envelope reads the SAME globals/identity (:1782/:1857/:1888-1894)
                 → cross-surface consistency asserted by test (one fact source, two surfaces)

resources/templates/list  →  client.list_resource_templates()  →  the 3 templates, unchanged
```

---

## 4. Files changed

| File | Change | Scope guard |
|---|---|---|
| `src/sofer/mcp_server.py` | `_resource_status()` (D1) + registration in `_register_resources` (D2) + docstring line | No edits to the 3 templates/handlers, envelope, roster, prompts, `build_server`, imports, globals |
| `tests/test_mcp_server.py` | New `TestStatusResource` class (§6) | `TestResources` (7), `TestToolRoster::test_exactly_fourteen_callables`, all #144/#145 pins unmodified |
| `openspec/changes/2026-09-11-fix-status-resource/**` | This design + spec delta (spec phase) | Canonical `openspec/specs/mcp-server/spec.md` NOT edited this phase; merge at archive |

No README/README_ES (no CLI flag, no `[tool.sofer]` key — §13 not triggered), no tag/release/version
bump (hatch-vcs derives from tags), no `TRACE.md`/`scratch/**`.

---

## 5. Contracts & invariants (pinned by tests)

1. `resources/list` is **non-empty** and includes exactly one static resource `sofer://status`
   (AC1; the reported failure mode).
2. `sofer://status` has **no path variables** — absent from `resources/templates/list`; the 3
   templates remain under `resources/templates/list`.
3. Payload is **exactly** the six fields; `phrase_source ∈ {"env","explicit","none"}`; invariant
   `phrase_source == "none"` ⟺ `approval_configured is False` across explicit/env/none/blank rows.
4. `root` == the resolved build root; `version` == `get_version()` (non-empty, never raises);
   `started_at` == the build's `_SERVER_STARTED_AT` (ISO-8601 UTC µs, `+00:00`, fixed width);
   `tool_count` == `len(workflow.WORKFLOW_METADATA)` == 14 today — all asserted **by equality against
   the source of truth, never by hardcoded literals**.
5. Never-leak: the phrase, any phrase-derived value (hash included), and the configured env value
   never appear in the serialized payload; no phrase-probe keys beyond `phrase_source`.
6. Consistency: resource payload ≡ `sofer_auth_status` envelope for the shared posture fields in one
   build (one fact source, two surfaces).
7. Zero side effects: reading status changes no state, writes nothing, touches no network.
8. Roster stays exactly 14 (`test_exactly_fourteen_callables` unmodified) — status is a resource,
   not a 15th tool; containment/size-guard clauses NOT extended to the static resource.

---

## 6. Test mapping (spec scenario → test → what it asserts)

New class `TestStatusResource` in `tests/test_mcp_server.py` (reusing `_make_dataset`, `_run`,
in-memory `Client(server)`); env kept hermetic with `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE",
raising=False)` (ambient-shell flake guard, mirroring the #145 fixtures).

| §Spec scenario | Test (choreographed name) | Asserts |
|---|---|---|
| Static status resource listed | `test_status_resource_listed` | `client.list_resources()` non-empty; `"sofer://status"` ∈ URIs; 3 templates still ∈ `client.list_resource_templates()` `uriTemplate`s |
| Static status resource listed (static clause) | `test_status_resource_static_not_template` *(1 additional beyond the 5 choreographed — "~6 per spec")* | `"sofer://status"` ∉ `uriTemplate`s; URI contains no `{`/`}` — behavioral proof of static registration |
| Static status resource listed (content) | `test_status_resource_content_explicit` | `build_server(root=tmp_path, approval_phrase="phrase123")`; `json.loads(contents[0].text)`; field set == the 6; `approval_configured is True`, `phrase_source == "explicit"`, `root == str(tmp_path.resolve())`, `version == get_version()`, `started_at` matches `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00` and equals `ms._SERVER_STARTED_AT`, `tool_count == len(workflow.WORKFLOW_METADATA)` |
| Status posture consistent across surfaces | `test_status_resource_consistent_with_auth_status` | One build (+`HF_TOKEN` env, `_make_dataset`): resource `approval_configured`/`phrase_source` == envelope's; `started_at` == `server_started_at`; `version` == `server_version` |
| Status posture … free of secret material | `test_status_resource_no_phrase_leak` | Phrase `"phrase123"` (explicit + env rows): not in `str(payload)`; `sha256(b"phrase123").hexdigest()` not in serialized; exact 6-key set (no phrase-probe keys); `phrase_source ∈ {"env","explicit","none"}` |
| Status posture … unconfigured paths | `test_status_resource_unconfigured_invariant` | env absent → `"none"`/False; blank & whitespace env (`""`, `"  "`) → `"none"`/False; blank explicit beats env; non-blank env → `"env"`/True — invariant `"none"` ⟺ False on every row |

Sequence note: write the RED round-trips first (D6 accessor pin), then the handler; per AGENTS.md §6
every spec scenario row has a matching test; existing pins stay green unmodified (anti-regression gate).

---

## 7. Anti-regression gate (#144/#145 pins must stay byte-identical in the diff)

- `TestToolRoster::test_exactly_fourteen_callables` unmodified; roster tool set unchanged.
- All 7 `TestResources` tests (containment/extension/size-guard/absolute-POSIX-template) unmodified
  — the static resource adds no path handling to share.
- `sofer_auth_status` envelope, `output_schema`, hints/APX-01 pins, `test_mcp_schema.py` untouched.
- Spec delta: `grep -n "^## ADDED\|^## REMOVED" specs/mcp-server/spec.md` empty; canonical
  `openspec/specs/mcp-server/spec.md` has no edit in this phase (merge at archive keeps APX-01/10.8).
- `git diff --name-only` limited to the 2 source/test files + the change root.

---

## 8. Delivery

- Branch `fix/146-status-resource` → PR to `dev`; `.github/PULL_REQUEST_TEMPLATE.md` with ACTUAL
  verification output + SDD artifacts (spec-scenario→test map); human authorizes merge (owner cannot
  self-approve). No tag, no release, no version bump.
- Baseline re-verified at apply: full `uv run pytest tests/ -q` ≈ **1489 passed / 6 skipped +
  the new status tests**, literal tail reported (AGENTS.md §6 / config.yaml counts are stale);
  `uv run mypy src/` clean; ruff check + format clean; `git diff --check` clean; never
  `git commit --no-verify`.
- Review budget: 2 source/test files + small delta — far under the 400-line threshold; no
  `size:exception`, no chaining; `ask-on-risk` pauses if scope/size overruns.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| R1 — phrase leak (10.8/APX-01 NEVER-LEAK) | Low | Payload emits only bool + enum + `_SERVER_*` strings + root + int; `phrase_source` never carries material; guard test scans serialized payload incl. sha256 probe |
| R2 — `root` full-path exposure | Med | Accepted decision (proposal Q1): the root already appears verbatim in INIT-03 `config_path`/`dataset_root`, resource URIs, and path errors; redaction would be the inconsistent outlier; disclosure is to the same process-context agent with filesystem access |
| R3 — drift vs `sofer_auth_status` | Low | Same globals through the same expressions; dedicated cross-surface consistency test |
| R4 — `resources/list` still empty | Low | Primary acceptance test IS the `list_resources()` round-trip; static classification pinned from installed source (no `{}` in URI, no-arg handler) |
| R5 — fastmcp v3 static/JSON semantics | **Resolved** | Installed-source evidence: no-arg + no-`{}` ⇒ static ⇒ `resources/list`; dict ⇒ `json.dumps` text contents with `.text` accessor; client accessors (`uri`, `uriTemplate`, `contents[0].text`) pinned — RED round-trips first |
| R6 — breaking existing pins | Low | Touches neither tools nor templates; roster/resource/hints/schema tests unmodified; MODIFIED MSP-R07 only, 10.8/APX-01 compose at archive |
| R7 — stale baseline claim | Low | 1489/6 re-verified at apply; literal tail reported in PR |

---

## Key Learnings

- fastmcp v3 static-vs-template classification is URI/arity-driven (`{` in URI OR function params ⇒
  template); a no-arg handler on a `{}`-free URI is a static `Resource` under `resources/list`.
- A dict return is auto-serialized by `ResourceResult._normalize_contents` to JSON **text** contents
  (mime `application/json`) — the client `.text` accessor matches the existing template tests; no
  `.json` accessor or manual serialization needed.
- `_resource_status` is the deliberate outlier among handlers: pure global reads need no
  `_tool_execution()`/`_capture_output()` wrapper, and MSP-R07's containment/size clauses apply to
  path-bearing artifacts only — the spec delta must state that boundary explicitly.
- `tool_count` verified: `workflow.WORKFLOW_METADATA` has exactly 14 keys == the 14-callable roster
  — deriving from the registry (not a literal) keeps AGENTS.md rules 1/4 and auto-syncs on roster
  changes.
- The three templates stay under `resources/templates/list`; the fix for the issue is a **static**
  resource, so the round-trip test must assert on `list_resources()` AND `list_resource_templates()`
  to prove the classification, not just URI presence.