# Proposal: static `sofer://status` resource so `resources/list` is never empty (issue #146)

## Intent

Issue **#146 (enhancement, OPEN)**: during MCP surface debugging an agent called `list_mcp_resources(server="sofer")` and got an **empty resource list** — "no diagnostic surface on the server". Root cause (stated in the issue, TRACE attempt 2.5): all three registered resources are URI **templates** (`sofer://dataset/{config_path*}`, `sofer://codebook/{data_file*}`, `sofer://metadata/{data_file*}`, registered via `server.resource(...)` in `_register_resources`). FastMCP lists templates under `resources/templates/list`, **not** `resources/list` — so any client asking for concrete resources sees an empty list by design.

This change registers **one static resource `sofer://status`** (no path variables) returning a JSON posture object — `approval_configured`, `phrase_source`, `root`, `version`, `started_at`, `tool_count` — reusing the #145 posture globals verbatim (same data as the `sofer_auth_status` envelope diagnostics, zero tools required to read it). `resources/list` becomes non-empty and agents get a zero-tool, read-only, secret-free view of server state.

## Sources

### Issue
- GitHub #146 (enhancement, open) — verbatim acceptance criteria: **AC1** `resources/list` returns the static resource; **AC2** content fields are correct and reflect build-time state; **AC3** unit tests cover registration and content. Files: `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`.

### Verified current state (post-#144+#145 merged `d73c59a` — re-verified in this session, not taken on trust)
| Area | Location | Verified |
|------|----------|----------|
| `_register_resources` | `src/sofer/mcp_server.py:2697-2713` | Registers exactly 3 **templates** via `server.resource("sofer://dataset/{config_path*}")(_resource_dataset)` etc. (`:2711-2713`). Docstring documents the rest-pattern `{name*}` rationale. **No static resource exists; `resources/list` is empty by design.** |
| Resource handlers | `_resource_dataset` `:2647`, `_resource_codebook` `:~2664`, `_resource_metadata` `:~2682` | Uniform shape: `_contained_path(...)` + `_check_resource_size(...)` + read, wrapped in `_tool_execution()`/`_capture_output()` (they call domain code that prints). All return `str` (text content). |
| Containment + size guard | `_contained_path`/`_check_resource_size` (`:2632`), `sofer_config.AGENT_RESOURCE_MAX_BYTES` (default 50 MB) | Path-state machinery; applies to path-bearing resources only. A static no-path resource has nothing to contain or size-check. |
| Server-state globals (from **#145, merged**) | `mcp_server.py:290-291` (`_SERVER_ROOT`, `_APPROVAL_PHRASE`), `:349-352` (`_PHRASE_SOURCE`, `_SERVER_PROCESS_ID`, `_SERVER_STARTED_AT`, `_SERVER_VERSION`), `_next_started_at` `:303-323` | All four posture globals + phrase source exist and are set **once at `build_server`** (`:2862-2869`). Reused, NOT re-authored. |
| `sofer_auth_status` envelope | `mcp_server.py:1782`; `approval_configured = _APPROVAL_PHRASE is not None` `:1857`; posture fields `:1888-1894` | The exact field sources the status resource mirrors: `_APPROVAL_PHRASE is not None`, `_PHRASE_SOURCE`, `_SERVER_STARTED_AT`, `_SERVER_VERSION`. Never-leak contract documented in docstring + module security bullet (`:24-52`). |
| Tool roster | `_register_tools` `:2282`, 14 × `server.tool(` (`:2284-2583`) | 14 callables. Single source of truth for the count: `workflow.WORKFLOW_METADATA` (`src/sofer/workflow.py:300-394`, 14 keys — MSP-R13: every tool has exactly one registry entry). `TestToolRoster::test_exactly_fourteen_callables` (`tests/test_mcp_server.py:423`) must stay green **unmodified**. |
| `build_server` | `mcp_server.py:2823-2878` | Sets root + phrase + posture globals, then `_register_tools`/`_register_resources`/`_register_prompts` (`:2874-2877`). One-server-per-process warning block `:2826-2841`. |
| FastMCP version | `pyproject.toml:22` `"fastmcp>=3.4,<4"` | v3 semantics relied on: a URI with **no path parameters** registers a **static resource** (appears in `resources/list`); `{param*}` registers a **template** (`resources/templates/list`). This is exactly the reported behavior in the issue. |
| Resources tests | `tests/test_mcp_server.py:1483-1643` `TestResources` | 7 tests: raw TOML, codebook on demand, metadata present/missing, containment refused, extension allow-list, size guard, absolute-POSIX template regression. All via in-memory `Client(server)` + `client.read_resource(...)`. `_make_dataset`/`_run` helpers exist. **No `list_resources` test exists today.** |
| Canonical spec — Resources | `openspec/specs/mcp-server/spec.md` requirement **MSP-R07** ("Resources", Added by `sofer-mcp-server`, archived 2026-08-28) | The ONLY resources requirement. Declares the 3 templates, pure-read semantics, containment + per-resource extension allow-lists, size guard, `file://` boundary. **No mention of a static resource or `resources/list` non-emptiness.** The #146 delta is a MODIFIED on this requirement. |
| Baseline | parent-supplied (TRACE) | `uv run pytest tests/ -q` ≈ **1489 passed / 6 skipped** pre-change (re-verify at apply; AGENTS.md §6/config.yaml quote stale counts — report the literal tail in the PR). |

## Scope

### In Scope (issue #146 ONLY — the static status resource)
- `src/sofer/mcp_server.py`:
  - new handler `_resource_status() -> dict[str, Any]` (next to the other resource handlers) returning the six fields — `approval_configured: bool`, `phrase_source: "env"|"explicit"|"none"`, `root: str`, `version: str`, `started_at: str`, `tool_count: int`;
  - registration `server.resource("sofer://status")(_resource_status)` inside `_register_resources` (after the 3 templates) + docstring update (3 templates **+ 1 static** resource);
  - a short resource `description` (fastmcp v3 supports `server.resource(uri, description=...)`): "Server posture snapshot — non-secret process-lifecycle metadata…" (no PII note needed: MSP-R09's PII note applies to sample-content resources; status carries no sample data);
- `tests/test_mcp_server.py`: new `TestStatusResource` class (registration + content + phrase paths + no-leak + consistency with `sofer_auth_status`); roster/other pins untouched.
- Spec delta (spec phase): **MODIFIED** canonical requirement **MSP-R07** (see Spec Delta Statement) — prose + 2 new scenario rows, composed with the canonical file's untouched #144/#145 content (APX-01, 10.8).

### Out of Scope (hard guards)
- **Touching the 3 existing templates or their handlers** — `sofer://dataset|codebook|metadata` unchanged, containment/size-guard machinery untouched.
- `sofer_auth_status` envelope, its `output_schema`, `hints`/`next`, the publish ladder, `sofer_publish_confirm` — all unchanged (issue names status as a *parallel* zero-tool surface, "same data as the envelope diagnostics"; no envelope edit).
- `src/sofer/workflow.py` (MSP-R13 registry), the tool roster (stays exactly 14 — `test_exactly_fourteen_callables` unmodified), prompts, `pyproject.toml` (fastmcp already a dependency), new dependencies.
- Any **additional** status fields beyond the six the issue names (e.g. `server_process_id`, `tool` names, network flag) — issue scope is exactly `approval_configured, phrase_source, root, version, started_at, tool_count`; scope containment is itself an acceptance-relevant property (no roster/envelope growth).
- README.md / README_ES.md (no CLI flag, no README heading, no `[tool.sofer]` key — the resource is server-internal; §13 sync does not trigger), `openspec/specs/**` canonical file (delta lives in this change root and merges at archive), `TRACE.md`, `scratch/**`.
- No tag, no release, no version bump (hatch-vcs derives from tags — untouched).

## Approach

1. **`_resource_status` handler** (new, next to `_resource_dataset` at `~2647`, before `_register_resources`):
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
   Field-by-field source (all build-time / process-lifecycle):
   | Field | Source | Rationale |
   |---|---|---|
   | `approval_configured` | `_APPROVAL_PHRASE is not None` (`:1857` identity) | Byte-identical semantics to `sofer_auth_status` — the envelope and the resource cannot drift. Invariant: `phrase_source == "none"` ⟺ `approval_configured is False` (10.8). |
   | `phrase_source` | `_PHRASE_SOURCE` (`:349`) | The enum value only — the configuration path, never the phrase or any derived value. Read-once contract inherited automatically (global captured at `build_server`). |
   | `root` | `str(_get_root())` (`:317-321`) | Resolved absolute containment root — the same root every path-bearing tool/resource anchors on; `_get_root()` keeps the fallback-to-cwd uniform with the rest of the module. **Decision: expose the full path** (see Risks R2 + Question round Q1). |
   | `version` | `_SERVER_VERSION` (`:352`, = `_version.get_version()`) | Package version from installed metadata; non-empty, never raises. Named `version` per issue #146 (auth_status's longer name is `server_version`; the issue's field list wins for AC2). |
   | `started_at` | `_SERVER_STARTED_AT` (`:351`) | ISO-8601 UTC microsecond stamp captured at `build_server` — the restart-proof signal; equal by construction to auth_status's `server_started_at`. Named `started_at` per the issue. |
   | `tool_count` | `len(workflow.WORKFLOW_METADATA)` | **Single source of truth** (MSP-R13: every registered tool has exactly one registry entry; registry == roster, 14 keys today). NOT a hardcoded `14` — AGENTS.md rules 1/4: no magic number, no duplicated roster. Adding a tool later auto-bumps the count with zero edits here. |
2. **Registration** — in `_register_resources` after `:2713`:
   ```python
   # Static (no path variables) so fastmcp lists it under resources/list —
   # the three templates above live under resources/templates/list and the
   # issue's empty-list surprise (sofer://status fixes it) is exactly that gap.
   server.resource(
       "sofer://status",
       description=(
           "Server posture snapshot — approval_configured, phrase_source, root, "
           "version, started_at, tool_count. Non-secret process-lifecycle "
           "metadata only; no secrets, no side effects, no network."
       ),
   )(_resource_status)
   ```
   Update `_register_resources` docstring ("3 resource templates" → "3 resource templates + 1 static resource"). No `_tool_execution()`/`_capture_output()` wrapper: the handler only reads immutable-at-runtime globals — nothing prints, no domain code, no config mutation, so the stdout swap and the config-state lock are deliberately omitted (a requested read stays trivially safe). No `_contained_path`/`_check_resource_size`: there is no path argument and no file read — the MSP-R07 containment/size clauses govern path-bearing artifacts and are NOT extended to this resource (spec delta must say so, to avoid scope creep).
3. **No secrets by construction + guard test**: the payload emits only a bool, an enum, two strings from `_SERVER_*` globals, the containment root, and an int. The phrase/env value cannot appear unless the *root path itself* contains it (out of the resource's control; see R2). A test scans the serialized payload for phrase material anyway (mirrors `test_auth_status_no_leak`).
4. **Tests** — new `TestStatusResource` class in `tests/test_mcp_server.py` (reusing `_make_dataset`, `_run`, in-memory `Client`):
   - `test_status_resource_listed` — `client.list_resources()` SHALL include `sofer://status` (AC1: `resources/list` non-empty);
   - `test_status_resource_content_explicit` — `build_server(root, approval_phrase="phrase123")` → read `sofer://status`, assert all six fields: `approval_configured is True`, `phrase_source == "explicit"`, `root == str(root.resolve())`, `version == get_version()` (equality, not a literal), `started_at` parses as ISO-8601 µs and equals the build's `_SERVER_STARTED_AT`, `tool_count == len(workflow.WORKFLOW_METADATA)` (equality, not `14`);
   - `test_status_resource_unconfigured_invariant` — no phrase, env absent (always `delenv` so an ambient shell var can't flake CI): `approval_configured is False`, `phrase_source == "none"`; blank/whitespace env row: still `"none"` (invariant `"none"` ⟺ `False`);
   - `test_status_resource_no_phrase_leak` — phrase `"phrase123"` + env set → serialized payload free of `"phrase123"`, `phrase_source ∈ {"env","explicit","none"}`;
   - `test_status_resource_consistent_with_auth_status` — same build: resource `approval_configured`/`phrase_source` equal the `sofer_auth_status` envelope's, `started_at` == `server_started_at`, `version` == `server_version` (one fact source, two surfaces).
   - fastmcp accessor note (RED-phase pin): handlers returning `dict` produce JSON contents — the client exposes them as `.json` (JSONResourceContents) vs the existing tests' `.text`; the exact accessor is pinned by the first RED test (see Risks R5).
5. **No changes** to `build_server`, posture globals, envelope, roster, workflow, pyproject, READMEs.

## Alternatives

| Alternative | Rejected because |
|-------------|------------------|
| Register `sofer://status` as a **template** (`sofer://status/{scope*}`) | A template still lists under `resources/templates/list` — it does NOT fix the empty `resources/list` the issue reports. The whole point is a **static** resource. |
| Add the posture data to an existing resource (e.g. a synthetic `sofer://metadata/status`) | Misuses the artifact model (metadata is per-dataset `metadata.yaml` content), fights the extension allow-list and containment wiring, and conflates sample-content resources with server state. |
| Add a 15th tool `sofer_server_status` | Breaks the 14-callable roster invariant (`test_exactly_fourteen_callables`), contradicts the issue's "zero-tool read", and splits preflight onto a second tool surface. |
| Extend `sofer_auth_status` (envelope-only diagnostics) and skip the resource | Issue is explicit: the empty `resources/list` *is* the bug — a client that only lists resources still sees nothing; the envelope requires a tool call with a valid `config` argument, the resource requires none. |
| Harden/sanitize `root` (basename, redact user dir, `str(root)` with `$HOME` elision) | The root already appears verbatim in `sofer_init`'s `output_schema`/envelope (`config_path`, `dataset_root` — INIT-03, absolute strings), inside resource URIs (`sofer://dataset//abs/path/...`), and in path errors; a second, abbreviated representation of the same fact would be inconsistent and would break clients that match URIs against the root. Redaction targets secrets; the root is the containment boundary, not a secret (see R2). |
| `tool_count` as a hardcoded `14` or a module constant | Duplicates the roster (AGENTS.md rule 4) and silently drifts if a tool is added/removed; `len(workflow.WORKFLOW_METADATA)` is the existing single source of truth (MSP-R13). |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **R1 — phrase leak** — any status field carrying the phrase or a phrase-derived value (10.8/APX-01 NEVER-LEAK) | Low | Payload emits only bool + enum + `_SERVER_*` strings + root + int; `phrase_source` describes the configuration path only; guard test scans the serialized payload for phrase/env material and pins `phrase_source ∈ {"env","explicit","none"}`; invariant test pins `"none"` ⟺ `approval_configured is False`. |
| **R2 — `root` exposure** — the full resolved root reveals filesystem/home layout on the agent's machine | Med | Decision: expose full path (see Alternatives). The root is already exposed verbatim by INIT-03's absolute `config_path`/`dataset_root` in `sofer_init`, by resource URI paths, and by error messages — redaction would be the leak-inconsistent outlier. Residual disclosure is to the same process-context agent that already has filesystem access; universe of alternatives (basename, `$HOME` elision) documented and rejected. Noted in the resource description that `root` is the containment boundary. |
| **R3 — drift vs `sofer_auth_status`** — envelope and resource disagree on posture | Low | Both read the same globals through the same expressions (`_APPROVAL_PHRASE is not None`, `_PHRASE_SOURCE`, `_SERVER_STARTED_AT`, `_SERVER_VERSION`); dedicated consistency test asserts cross-surface equality in one build. |
| **R4 — `resources/list` still empty** (fastmcp v3 lists static resources under `resources/list`, templates under `resources/templates/list`) | Low | Primary acceptance test IS the `list_resources()` round-trip (`test_status_resource_listed`); `sofer://status` carries no path params so it registers as static by design; the `sofer://` scheme is already proven by the 3 templates. |
| **R5 — fastmcp v3 static-resource semantics** — no-arg handler / dict→JSON content / accessor mismatch (`.json` vs existing `.text`) | Med | In-process `Client` round-trips in RED phase pin the exact registration + content accessor before any domain code; fallback if v3.4+ rejects a no-arg handler with a dict return (unlikely — static resources are documented v3 API): return a JSON `str` and assert `.text` — registration stays static either way; the template-ification trap (adding a path param) is explicitly avoided. |
| **R6 — breaking existing pins** — roster, resource tests, #144/#145 spec content | Low | Touches neither tools nor templates: `test_exactly_fourteen_callables`, all 7 `TestResources` tests, hints/roster/schema pins stay green **unmodified**; spec delta is MODIFIED MSP-R07 only — canonical APX-01 and 10.8 are NOT re-added/touched (compose-by-diff at archive; spec-phase self-check greps the delta for `ADDED`/APX-01 absence). |
| **R7 — stale baseline claim** in the PR | Low | Baseline ≈ 1489 passed / 6 skipped parent-supplied; re-verified at apply and the literal tail reported (config.yaml/AGENTS.md counts are stale). |

## Success Criteria

Mapped to issue #146's three acceptance criteria.

**AC1 — `resources/list` returns the static resource:**
- [ ] New `TestStatusResource::test_status_resource_listed` asserts `client.list_resources()` includes `sofer://status` (non-empty list) — the exact reported failure mode is covered by a test.
- [ ] `sofer://status` is registered via `server.resource("sofer://status", ...)` with **no path variables** (registering a template would not satisfy this AC).

**AC2 — Content fields are correct and reflect build-time state:**
- [ ] `approval_configured` == `_APPROVAL_PHRASE is not None` (identical semantics to the envelope); `phrase_source` ∈ {"env","explicit","none"} with invariant `"none"` ⟺ `approval_configured is False` (explicit, env, none, blank-env paths tested).
- [ ] `root` == `str(_get_root())` (resolved absolute, containment-consistent); `version` == `_version.get_version()` non-empty; `started_at` == the build's `_SERVER_STARTED_AT` (ISO-8601 UTC µs, restart-proof signal); `tool_count` == `len(workflow.WORKFLOW_METADATA)` == 14 today — all asserted by equality against the source of truth, never by hardcoded literals.
- [ ] Consistency: `test_status_resource_consistent_with_auth_status` asserts resource ↔ envelope equality for the shared posture fields.

**AC3 — Unit tests cover registration and content:**
- [ ] `TestStatusResource` (~5 named tests): listed; title/content; unconfigured invariant; no-leak; envelope consistency. Files `src/sofer/mcp_server.py` + `tests/test_mcp_server.py` only.
- [ ] Every added spec scenario row has a matching test (AGENTS.md §6); existing `TestResources`/roster/hints pins stay green **unmodified**.

**Delivery-wide:**
- [ ] Full `uv run pytest tests/ -q` green: baseline (~1489 passed / 6 skipped) + new status tests, literal tail recorded; `uv run mypy src/`, ruff check + format clean; `git diff --check` clean.
- [ ] PR (`fix/146-status-resource` → `dev`) uses `.github/PULL_REQUEST_TEMPLATE.md` with REAL verification output and the SDD artifacts section (spec-scenario→test map). No tag/release/version bump.

## Spec Delta Statement

**CONFIRMED: REAL delta — MODIFIED `openspec/specs/mcp-server/spec.md` requirement `Resources (MSP-R07)` (canonical, Added by `sofer-mcp-server`, archived 2026-08-28). The canonical file must stay composed with the already-present `Auth status preflight read-only (10.8)` and `Approval-phrase configuration diagnostics (APX-01)` from the MERGED #144/#145 — the delta MUST NOT re-add or clobber them.**

Delta file to author in the spec phase: `openspec/changes/2026-09-11-fix-status-resource/specs/mcp-server/spec.md`, containing **only** the `## MODIFIED Requirements` section — NO `ADDED`, NO `REMOVED` sections:

- **Requirement body (additive edit to MSP-R07, keeping the original `> Added by change sofer-mcp-server (archived 2026-08-28).` attribution and appending `Modified by \`2026-09-11-fix-status-resource\`.` )**:
  - a sentence: the server SHALL additionally expose a **static** resource `sofer://status` (no path variables; registered so it appears under `resources/list`, NOT `resources/templates/list`) returning a JSON posture object with exactly six fields — `approval_configured: bool`, `phrase_source: "env"|"explicit"|"none"`, `root: str` (the resolved containment root), `version: str` (installed package version), `started_at: str` (ISO-8601 UTC µs captured at `build_server`), `tool_count: int` (size of the workflow registry, MSP-R13);
  - the never-leak sentence extended: the resource carries process-lifecycle metadata only — the phrase, any phrase-derived value, and the configured env value MUST NEVER appear in the payload; `phrase_source` describes the configuration path only; invariant `"none"` ⟺ `approval_configured:false`;
  - an explicit boundary sentence: the containment/size-guard/extension clauses of MSP-R07 govern path-bearing resources and SHALL NOT be extended to the static `sofer://status` (no path argument, no file read);
  - a `(Previously: ...)` historical note (the server exposed only the three URI templates; `resources/list` was empty by design).
- **Scenario rows (existing 3 KEPT unchanged + 2 new GWT)**:
  1. `Static status resource listed` — GIVEN a running server / WHEN `resources/list` is requested / THEN it SHALL include `sofer://status` (non-empty) AND the three dataset/codebook/metadata templates SHALL remain under `resources/templates/list`.
  2. `Status posture content` — GIVEN `build_server(root=..., approval_phrase="phrase123")` / WHEN `sofer://status` is read / THEN the payload SHALL carry the six fields with build-time values (`phrase_source="explicit"`, `approval_configured:true`, `root` equal to the resolved build root, `version` equal to `_version.get_version()`, `started_at` ISO-8601 UTC µs, `tool_count` equal to the registry count), SHALL contain no phrase material, and SHALL hold `"none"` ⟺ `approval_configured:false` across the unconfigured paths.
- **Composition note (critical):** canonical `spec.md` ALREADY contains 10.8 (posture, from #145) and APX-01 (hints, from #144). The delta MUST NOT re-add either; at archive, merge = MSP-R07 amended + everything else preserved. A spec-phase self-check greps the delta for an `ADDED` section (must be absent).

## Dependencies

- **Merged #144 + #145** (`d73c59a` on `dev`): the posture globals `_PHRASE_SOURCE`, `_SERVER_PROCESS_ID`, `_SERVER_STARTED_AT`, `_SERVER_VERSION`, `_next_started_at` (`mcp_server.py:303-323`, `:349-352`), the phrase resolution contract, canonical 10.8 + APX-01 in `spec.md`. This change only **reads** those globals — zero new state, zero new imports.
- `workflow.WORKFLOW_METADATA` (`src/sofer/workflow.py:300-394`) — existing registry, single source of truth for `tool_count`; `workflow` is already imported (`mcp_server.py:86`).
- Test fixtures: `_make_dataset`, `_run`, in-memory `Client(server)` pattern from `TestResources` (`tests/test_mcp_server.py:1487+`); `monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE")` for the none/blank rows (ambient-shell flake guard).
- No new dependencies (`fastmcp>=3.4,<4` already declared); no pyproject change.

## Delivery

- Branch `fix/146-status-resource` (already created, base `dev`; parent-verified). PR lands on `dev` only — commits target this branch; never commit directly to `main`; no tag, no release, no version bump (hatch-vcs derives from tags — untouched).
- Review budget: well under the 400-line threshold (2 source/test files, additive tests, 1 small delta file) — no `size:exception`, no chaining. Delivery strategy `ask-on-risk`: any size overrun or scope creep pauses for a decision.
- Baseline: `uv run pytest tests/ -q` ≈ 1489 passed / 6 skipped (re-verify at apply; report the literal tail and the delta vs. pre-change). Pre-commit runs ruff + mypy; push `uv run mypy src/` clean; never `git commit --no-verify`.
- PR: `.github/PULL_REQUEST_TEMPLATE.md` filled with ACTUAL command output and the SDD artifacts section. GitHub self-approve is impossible for the owner's own PR — human authorizes merge after review.

## Proposal Question Round

Auto execution mode — these assumptions are baked into this proposal and need explicit user sign-off (or correction) before the spec phase:

1. **`root` exposes the FULL resolved path** (via `_get_root()`). I chose full exposure because the root already appears verbatim in `sofer_init`'s absolute `config_path`/`dataset_root` (INIT-03), in resource URIs, and in path errors — redacting it on the status surface would be the inconsistent outlier. If you prefer a sanitized form (basename, `$HOME` elision), that changes the field's contract, the spec row, and the content test — flag it, otherwise full path ships.
2. **`tool_count` is derived from `len(workflow.WORKFLOW_METADATA)`** (14 today, auto-syncs if the roster changes), not a hardcoded constant — respects AGENTS.md rules 1/4. If you'd rather pin a literal `14` (matching `test_exactly_fourteen_callables`'s style), note it.
3. **Field names follow the issue verbatim** (`version`, `started_at`, `root` — not `server_version`/`server_started_at`), and the payload is exactly the six named fields — `server_process_id` deliberately NOT included (issue scope; the pid is process-scoped and adds nothing to a zero-tool read).
4. **The status handler is NOT wrapped in `_tool_execution()`/`_capture_output()`** — pure global reads, nothing prints, no domain code; wrapping would swap stdout pointlessly. If you want uniform wrapping for consistency, say so.
5. **Spec delta = MODIFIED MSP-R07 only** (2 new scenarios), composed with the already-canonical 10.8/APX-01; no README/ES change; baseline ≈ 1489/6 re-verified at apply.

---
*Branch: `fix/146-status-resource` (base `dev`, PR-only; no tag/release). Change persists to `openspec/changes/2026-09-11-fix-status-resource/` per artifact-store contract.*