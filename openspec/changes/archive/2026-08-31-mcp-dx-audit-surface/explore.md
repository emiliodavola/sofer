# Exploration: mcp-dx-audit-surface — MCP DX Audit (11 tools, 10 cross-cutting fixes)

> **Change:** `mcp-dx-audit-surface` · **Issue:** #111 · **Date:** 2026-08-31
> **Auditor stance:** Independent verification of every claim in #111 against live `tools/list` + source reads. The issue is UNTRUSTED input — each finding was re-checked file:line before accepting.

---

## 1. Current State

### 1.1 Surface as an agent sees it (verified live 2026-08-31)

| Layer | Count | Source | What the agent gets |
|-------|-------|--------|---------------------|
| Tools | 11 callables | `mcp_server.py:637-1546` via `FastMCP.tool` | `sofer_validate`, `sofer_prepare`, `sofer_publish`, `sofer_publish_confirm`, `sofer_codebook`, `sofer_codebook_all`, `sofer_profile`, `sofer_render`, `sofer_scan_dry_run`, `sofer_scan_apply`, `sofer_init` |
| Resources | 0 live, 3 templates | `mcp_server.py:1636-1652` (`sofer://dataset/{config_path*}`, `sofer://codebook/{data_file*}`, `sofer://metadata/{data_file*}`) | `resources/list` empty; `resources/templates/list` returns 3 |
| Prompts | 3 | `mcp_server.py:1660-1752` | `prepare_dataset`, `assess_dataset`, `finalize_and_publish` — each carries the canonical chain with copy-paste examples |

**Live `tools/list` introspection** (`server._list_tools()` on FastMCP 3.4.7, `C:\Users\elaze\AppData\Local\Temp\check_mcp5.py`):

- **Every tool** `parameters.properties[*]` is `{"type":"string"}` or `{"type":"boolean"}` with **no `description` key** — confirmed for all ~28 params.
- **Every tool** `annotations` is `None` (no `readOnlyHint`/`destructiveHint`/`openWorldHint`).
- **Every tool** `output_schema` is `{"additionalProperties": true, "type":"object"}` — generic, no typed envelope.
- `sofer_publish.target` and `sofer_publish_confirm.target` are `{"type":"string"}` — no `enum`.
- Server `instructions` (`build_server` at `mcp_server.py:1796-1811`) already contains a one-liner canonical chain + publish gate + UNTRUSTED note, but not the phased Bootstrap→Build→Publish diagram.

### 1.2 Safety core (why the B grade, not F)

- **Containment CF-1/CF-2**: `_contained_path` (`mcp_server.py:254-322`) + `_get_root()` anchors every path arg, resource URI, `output`, and `[[file]] local/remote` (`_validate_file_entries`, `_validate_output_targets`). Verified correct — including Windows drive-letter rejection on POSIX (`_is_absolute_or_drive`).
- **Publish ladder**: `sofer_publish_confirm` 4-gate fail-closed (`mcp_server.py:852-894`): `target=="hf"` → `acknowledge_risk` → `acknowledge_confidential` if `confidential` → `approval_phrase` via `hmac.compare_digest`. Quality gate before token check (`mcp_server.py:859-871`).
- **Token ladder**: `_get_hf_token()` (`mcp_server.py:573-595`) `HF_TOKEN → HF_HUB_TOKEN → HUGGING_FACE_HUB_TOKEN → get_token()` + `.env` + `HF_HUB_DISABLE_IMPLICIT_TOKEN` guard. Never logged.
- **Single-writer**: `_EXEC_LOCK` + `_capture_output` (`mcp_server.py:162-209`) serializes all tool bodies.

None of the 10 proposed fixes need to touch this core. The task is surface-only.

### 1.3 Chain placement (the F that drives everything)

- **Canonical Build** (`README.md:484-487` + `mcp_server.py:1663-1687`): `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → STOP → publish_confirm`. Requires `[[file]]` from `scan`.
- **Bootstrap Phase 0** (owner decision 2026-08-31, #111 §2): `init → scan` is **conditional canonical** (greenfield only). Prior phrasing `"Not part of canonical"` in `mcp_server.py:1283,1347` is deprecated — must be updated.
- **Where chain lives today**: exclusively in `prompts/get` (`prepare_dataset` carries ordered steps + args + STOP). `tools/list` has no `Requires`/`Next`/`See also`. An agent bootstrapping from `tools/list` alone (default for opencode/codex/claude-code) cannot learn the order.

---

## 2. Claim Validation — confirm / refute each issue §5-§7 finding with file:line

| #111 Claim | Verdict | Evidence |
|------------|---------|----------|
| **Zero param descriptions (~28 bare `str`/`bool`)** | **CONFIRMED** | `mcp_server.py:637` `def sofer_validate(config: str)` — no `Annotated`/`Field`. Live `server._list_tools()` shows `{"type":"string"}` alone for every param. |
| **`target` free string not `enum`** | **CONFIRMED** | `mcp_server.py:736` `target: str = "local"`; `mcp_server.py:804` `target: str = "hf"`. CLI `cli.py:1062` correctly uses `choices=["hf","local"]` — MCP diverged. |
| **`no_checks` double negation** | **CONFIRMED** | `mcp_server.py:683` `no_checks: bool` + `cli.py:117` `run_checks=not no_checks`. Agent must invert. |
| **`all_files` boolean overload (single vs batch)** | **CONFIRMED** | `mcp_server.py:1026` `sofer_profile(dataset: str, ..., all_files: bool, config: Optional[str])`; `mcp_server.py:1150` `sofer_render` same. |
| **`dataset`/`package`/`config`/`path`/`name` polymorphic + shadow `config`** | **CONFIRMED — CRITICAL** | `sofer_validate(config)` vs `sofer_codebook(path)` vs `sofer_profile(dataset, config?)` vs `sofer_render(package, config?)` vs `sofer_init(name)` — 5 synonyms for "what to act on", all `str`. `sofer_profile` also has shadow `config: Optional[str]` that competes with `dataset`. |
| **`output` dual-typed file vs dir** | **CONFIRMED** | `sofer_codebook(path, output)` → file at `mcp_server.py:953-954`; `sofer_codebook_all(config, output)` → dir at `mcp_server.py:993-996`; same name, different semantics. |
| **Wall-of-text descriptions leaking `MSP-R03`/`CF-2`/`PRF-06`** | **CONFIRMED** | `sofer_validate` description ~280 words including `(MSP-R03, MSP-R09, MSP-R04)`; `sofer_prepare` similar. Buries `When to use` at line 10+. |
| **`UNTRUSTED` disclaimer repeated 11× (wastes ~440 tokens)** | **CONFIRMED** | `_UNTRUSTED_NOTE` (`mcp_server.py:103-106`) appended to every tool docstring via literal footer (`mcp_server.py:653-654, 702-703, ...`). Server `instructions` (`mcp_server.py:1809`) also carries it — duplication, not single-source. |
| **No `annotations` (`readOnlyHint` etc.)** | **CONFIRMED** | `server._list_tools()` shows `annotations: None` for all 11. No `mcp.tool(annotations={})` anywhere. |
| **No `outputSchema` — generic `{additionalProperties: true}`** | **CONFIRMED** | All 11 show `output_schema: {"additionalProperties": true, "type":"object"}`. No per-tool `output_schema=` passed to `server.tool()`. |
| **Error duality `ok:false` vs `McpError` throw** | **CONFIRMED** | `mcp_server.py:680` `return {"ok": ok, ...}` vs `mcp_server.py:768-776, 853-894` `raise PublishRefusedError`. Spec `openspec/specs/mcp-server/spec.md §MSP-R04` only documents envelope, not throw. |
| **`dry_run` incoherence (`True` on `publish`, `False` on `init`, separate tool for `scan`)** | **CONFIRMED** | `sofer_publish(dry_run=True)` vs `sofer_init(dry_run=False)` vs `sofer_scan_dry_run` as separate tool. `annotations.readOnlyHint` absent so agent can't distinguish. |
| **Chain lives in prompts, not tools** | **CONFIRMED** | `prompts/get("prepare_dataset")` returns 7-step chain with copy-paste; `tools/list` for `sofer_prepare` has no `next`/`requires`. |
| **`resources/list` empty, `resources/templates/list` has 3** | **CONFIRMED** | `mcp_server.py:1636` registers templates (`sofer://dataset/{config_path*}` etc.); no `resources/list` handlers. An agent checking only `resources/list` concludes "no resources". |
| **Bootstrap `"Not part of canonical"` phrasing outdated** | **CONFIRMED — owner decision** | `mcp_server.py:1283` + `mcp_server.py:1347` say `"Not part of canonical chain"` — contradicts owner decision that Bootstrap is Phase 0 canonical (conditional). Must be updated. |
| **`feat/mcp-build-clarity` `sofer_build` atom exists** | **CONFIRMED** | `openspec/changes/feat-mcp-build-clarity/proposal.md` + `design.md` — evaluated and **chose B (prompts/docs only), deferred `sofer_build`**. Not merged. |
| **`sofer_prepare` looks like full build but excludes `profile`/`render`** | **CONFIRMED** | `README.md:481` explicitly `"sofer_prepare alone does NOT produce profiles/renders"`; tool description says `"Prepare Parquet package"` without clarifying what it does NOT produce. |

**Overall verdict on audit accuracy:** 17/17 claims confirmed against live introspection + source. No refutations. The audit is a reliable spec — implementer can trust it, with the independent improvements below.

---

## 3. Findings by Dimension

### Safety — PASS (no surface fix may weaken it)

- Containment, publish ladder, token handling are A-grade. Any proposal that re-encodes `target` as `enum`, adds `error_code`, or introduces `sofer_auth_status` must preserve fail-closed semantics and never log token/phrase values.
- Risk: describing the ladder as `enum` + `Field(description="... acknowledge_risk ...")` is safe; describing it as pre-flight `next` hints is safe; describing it as `outputSchema` with `skipped_protected` (already present) is safe.

### Schema — FAIL

- Zero `Field(description=…)`, free-string `target`, boolean overload, dual-typed `output`. MCP spec 2025-06-18 expects `inputSchema` descriptions as the primary agent affordance; without them `tools/list` is unusable for validation.

### Error Contract — FAIL

- Dual shapes force `try/except` + `if not result.ok` in agent loop. `config_errors` is correctly surfaced per MSP-R04, but expected failures (`target!="hf"` with `dry_run=False`, missing acknowledge) throw `McpError(isError:true)` while `validate` failures return envelope. No `error_code` enum.

### Chain Affordance — FAIL

- Correct order is not machine-readable from `tools/list`. Server `instructions` has a one-liner but not the phased Bootstrap→Build→Publish diagram with conditional Phase 0. Per-tool `Requires:`/`Next:` absent.

### Naming — C

- `sofer_*` prefix correct (no doubling). Identity params (`config`/`path`/`dataset`/`package`/`name`) and `output` dual-typing are the debt. `all_files` naming is honest about what it does but hides that it's a mode switch.

### Docs — C

- Prompts are the only well-documented entry point (with examples). Tools bury usage behind 250-400 word walls. `UNTRUSTED` disclaimer repeats 11×.

---

## 4. Alternative Approaches Considered (with tradeoffs)

### 4.1 Error contract: `sofer_auth_status` tool vs richer error `next` hints

| Approach | What it is | Pros | Cons | Complexity | Recommendation |
|----------|------------|------|------|------------|----------------|
| **A — New `sofer_auth_status` read-only tool** (#111 fix #9) | `sofer_auth_status(config) → {token:"present|missing", token_source, confidential, requires_ack_confidential, requires_approval_phrase, next}` | Pre-flight without triggering a publish; answers "can I publish?" in one call | +1 tool (12 total), adds surface; agent could also learn via validate + error envelope | S | **Include, but non-blocking** — useful for `confidential` + approval-phrase checks that aren't visible until `validate` is called |
| **B — Richer `next` in error envelope only** | On `publish_confirm` refusal, return `{"ok":false, "error_code":"PUBLISH_RISK_NOT_ACKD", "message":"...", "next":{"acknowledge_risk":true}, "hint":"retry with acknowledge_risk=True"}` | No new tool; agent learns via trial exactly once per gate | Still costs 1 failing call per gate to learn | S | **Do regardless** — every refusal must carry machine-readable `error_code` + `next` |
| **C — Both** | B always; A as convenience | Best DX: proactive check + reactive guidance | Slightly more code | S | **RECOMMENDED**: implement B as the contract; add A as convenience after B |

**Why this is better than #111's A-only:** Issue proposes A as the sole pre-flight. Independent finding: B (structured refusal) is the actual contract fix; A is optimization. Agent that never calls `auth_status` should still succeed via `next` hints. Gate count matters: 4 gates × 1 turn each = 4 wasted turns with prose errors, 0 with `next`.

### 4.2 `profile`/`render` polymorphism: split `*_all` tools vs `mode` enum vs unified `config`-only

| Approach | Shape | Pros | Cons | Recommendation |
|----------|-------|------|------|----------------|
| **Split** `sofer_profile` + `sofer_profile_all` (and `render` pair) | Batch tools take `config: str` (TOML), single tools take `dataset: str`/`package: str` | Explicit, no overload, mirrors `codebook`/`codebook_all` which already split | 13 tools total (more surface), `sofer_profile` would need a deprecation story | Good |
| **`mode: Literal["single","all"]` on one tool** (#111 fix #10 alt) | One tool, `mode` selects whether `target_path` means file or TOML | Keeps tool count at 11, matches CLI `--all-files` flag | Still polymorphic `target_path` type depends on `mode` — agent must branch | OK but not better than split |
| **Unified `config`-only for batch, positional `dataset`/`package` for single (current) + deprecated alias** | Keep current split but fix naming: batch path is `config`, single is `dataset`/`package` with clear `Field(description)` | Smallest diff, fixes docs not arity | Doesn't remove `config` shadow — agent still sees optional override | Weak |
| **RECOMMENDED: Split + `mode` via `Annotated`** | New `sofer_profile_all(config)` and `sofer_render_all(config)` for batch; keep `sofer_profile(dataset)` / `sofer_render(package)` single-only; deprecate old `all_files`+`config` overload with one-release shim | Cleanest: `codebook` precedent, no polymorphic param, agent can't pass TOML as file by mistake; schema validates | Two new tools, one deprecation cycle | **Accept** — aligns with existing `codebook` split precedent |

**Why this improves on #111 fix #3:** Issue proposes either split or `mode` as alternatives. Independent finding: split is strictly better because `codebook` already split and agents already handle that pattern; `mode` keeps the polymorphism that is the root problem. The "deprecated `config` override" shim should be a single release, not permanent.

### 4.3 Build atom `sofer_build` vs prompt-only vs instructions-only

| Approach | Pros | Cons | Already decided? |
|----------|------|------|-------------------|
| **`sofer_build` atom** (`validate→prepare→codebook_all→profile_all→render_all` in one call) | One turn vs five; reduces missed-step rate | Hides per-step outputs; partial-failure envelope (`steps:{...}`) is complex; duplicates 4 domains' `force`/containment/containment-error handling; +150 LOC + tests; deferred per `feat/mcp-build-clarity` design | Deferred |
| **Prompt-only** (`prepare_dataset` carries chain) | Zero new surface | Agent that only calls `tools/list` never sees it | Current — proven insufficient |
| **Instructions + per-tool Requires/Next** (#111 fix #7) | Visible from `tools/list` + `initialize` without extra tool | Requires editing 11 descriptions + server `instructions` | **RECOMMENDED as Phase 1** |
| **Hybrid (instructions + atom later)** | Best long-term | Adds atom without measuring whether instructions fix the problem | Defer measurement |

**Independent recommendation:** Ship instructions + `Requires`/`Next` first, measure agent dry-run miss rate on a fixture, only then decide `sofer_build`. Do not bundle `sofer_build` with the schema/affordance fixes — it is a separate concern already tracked in `feat/mcp-build-clarity`.

### 4.4 `output` disambiguation vs keeping generic `output`

| Approach | Pros | Cons |
|----------|------|------|
| Rename to `output_file` vs `output_dir` (#111 fix #8) | Typed, agent can't confuse | Breaking; needs alias shim |
| Keep `output` but clarify per tool via `description` only | No break | Still dual-typed in schema |

**Recommendation:** Rename to `output_file` (where tool writes a file) vs `output_dir` (where tool writes a dir), keep `output` as deprecated alias one release. This matches MCP best practice: distinct params for distinct artifact kinds. Effort M — worth it.

### 4.5 Schema annotations via `Annotated` vs manual `json_schema` dict

- **Use `Annotated[str, Field(description=…)]` exclusively.** FastMCP 3.4.7 derives `inputSchema` from Python type hints via Pydantic introspection (verified: `parameters` dict is built from function signature). Manual `json_schema_extra` is only for non-Pydantic metadata (e.g., `Requires`/`Next` adjacency).
- **For `target` enum:** `Annotated[Literal["local"], Field(description=…)]` and `Annotated[Literal["hf"], Field(...)]` — produces `{"enum":["local"]}` in `inputSchema` without extra error code.
- **`outputSchema`:** pass `output_schema={...}` to `server.tool()` (FastMCP 3.4.7 supports `output_schema` param per `inspect.signature(FastMCP.tool)`). Define typed envelope `{ok: bool, exit_code: int, output: str, error_code?: str, next?: object, ...}` per tool.

### 4.6 Deprecated aliases: one-release shim vs clean break

- Project is pre-1.0 (`hatch-vcs` version, `README` `vX.Y.Z`), so minor bumps may carry breaking changes per `AGENTS.md §12`. No evidence of wide external MCP consumers yet.
- **Independent judgment:** Clean break with `minor` bump + CHANGELOG migration note is acceptable and avoids `Field(deprecated=True)` shim complexity. If external consumers surface, reintroduce aliases. Prefer clean break over the 1-release deprecation tax unless product signals otherwise.

### 4.7 Token leakage dimension (missing from #111)

- Verified: token never in description, resource, or `output` capture. `approval_phrase` only compared via `hmac.compare_digest`, never logged. No fix needed — note as PASS in spec delta.

### 4.8 Missing audit dimensions — observability & testing

| Dimension | Gap | Proposal |
|-----------|-----|----------|
| **Observability** | No structured log per tool call (only captured stdout). Debugging agent chains requires parsing `output` prose | Add `SOFER_VERBOSE=1` structured log `{tool, duration_ms, ok, error_code}` to stderr (never stdout — preserves JSON-RPC framing) |
| **MCP fixture testing** | No `tests/test_mcp_schema.py` asserting `description`, `annotations`, `enum`, `outputSchema` | Add fixture test that introspects `server._list_tools()` + asserts every param has `description`, correct `annotations`, `target` enum, typed `outputSchema` |
| **Timeout** | FastMCP `timeout` not set — long `prepare` blocks. CLI has no timeout either | Not blocking; note for follow-up |
| **Resource discovery** | `resources/list` empty confuses agents | Either register a static `resources/list` handler or document in server `instructions` that resources are addressable only via `resources/templates/list` |

---

## 5. Affected Areas

- `src/sofer/mcp_server.py` — all 11 `@mcp.tool` definitions (add `Annotated`/`Field`, `annotations`, `output_schema`, `Requires`/`Next` in description, `target` enum, `output_file`/`output_dir` rename, de-polymorphize `profile`/`render`, move UNTRUSTED to server `instructions`, add `sofer_auth_status`), `build_server()` instructions (phased diagram + UNTRUSTED single-source), `_register_resources` (optional `resources/list` affordance).
- `openspec/specs/mcp-server/spec.md` — error_code table, annotation contracts, `target` enum, `output` → `output_file`/`output_dir`, `profile`/`render` split, auth_status, phased Bootstrap→Build→Publish diagram, `outputSchema` per tool.
- `README.md` + `README_ES.md` — phased diagram mirroring server instructions (already has canonical Build chain at `README.md:484-487`; needs Bootstrap Phase 0 update).
- `pyproject.toml` — no change required (already `fastmcp>=3.4,<4` in dependencies per `feat/mcp-auto-install`).
- `openspec/changes/feat-mcp-build-clarity/` — remains separate; this change does not add `sofer_build`.

---

## 6. Approaches

### 6.1 Approach A — Surface-only DX audit fixes (no new orchestration) — RECOMMENDED

Fix schema, annotations, descriptions, error contract, chain affordance, and naming without adding `sofer_build`. This is #111's Phases 1-3 plus independent improvements (clean break, split over mode, `next` hints as primary contract).

- Pros: Minimal risk — safety core untouched; all fixes are additive or strictly tightening (enum, annotations, descriptions); verifiable via `tools/list` JSON alone; no new coordination complexity.
- Cons: Build still costs 5 calls (vs 1 with atom) — acceptable until measurement.
- Effort: Medium (1 file + spec delta + READMEs; ~2-3d with tests).

### 6.2 Approach B — A + `sofer_build` atom in same change

Bundle the atom with the DX fixes.

- Pros: One-shot delivery.
- Cons: Mixes concerns (surface audit vs orchestration), already deferred by `feat/mcp-build-clarity` for good reasons; partial-failure envelope multiplies review burden; risks 5000-line phased plan collapsing into one PR.
- Effort: High.
- Verdict: **Rejected** — violates `work-unit-commits` guard and pre-decided `feat/mcp-build-clarity` deferral. Measure after A.

---

## 7. Recommendation

**Adopt #111's audit as the implementation spec with the following amendments:**

1. **Phasing:** Keep #111's 4 phases but merge Phases 1+2 into a single "no-break surface" slice (descriptions + annotations + `target` enum + Requires/Next + UNTRUSTED move). This is the highest-ROI cut and should land first.
2. **Error contract:** Make `error_code` + `next` on every refusal the primary fix (M); add `sofer_auth_status` only after (S) — not as substitute.
3. **Polymorphism:** Prefer split `sofer_profile`/`sofer_profile_all` + `sofer_render`/`sofer_render_all` over `mode` — precedent of `codebook`/`codebook_all` is the strongest argument.
4. **`output` rename:** `output_file` vs `output_dir` with clean break (pre-1.0) — skip 1-release alias unless consumers exist.
5. **`sofer_build`:** Do not include — leave to `feat/mcp-build-clarity`, gated on post-fix agent dry-run metrics.
6. **Bootstrap phrasing:** Update `mcp_server.py:1283,1347,1430` plus server `instructions` to reflect Phase 0 conditional canonical (owner decision).
7. **Add missing test dimension:** `tests/test_mcp_schema.py` (schema assertions) + `SOFER_VERBOSE` observability note.

**Why not rubber-stamp:** The 10 fixes are individually correct, but the plan's ordering (auth_status before error envelope) and deprecation-heavy alias strategy add complexity that pre-1.0 status makes unnecessary. The independent evaluation tightens the contract by making refusal `next` hints primary and trimming the alias tax.

---

## 8. Risks

- **Safety reflexivity:** Any edit to `mcp_server.py` header/filters risks touching containment or publish ladder — mitigate by reviewing `mcp_server.py:254-595` diff in isolation and keeping `_contained_path` + `_get_hf_token` + `_APPROVAL_PHRASE` logic unchanged.
- **Breaking `output` rename:** Agents pinned to `output` param will fail validation — clean break is pre-1.0 acceptable but must be in CHANGELOG with search-replace migration (`output` → `output_file`/`output_dir`).
- **Spec drift:** `openspec/specs/mcp-server/spec.md` must stay in lockstep — the `sofer_build` capability (`mcp-build-orchestration`) must not be conflated with this change's `mcp-server` deltas.
- **Review budget:** Estimated diff ~400-600 lines across `mcp_server.py` + spec + READMEs — within one PR, but the `profile`/`render` split may push toward `chained PRs recommended: Yes` with slice boundary at Phase 3.
- **Under-indexed dimension:** Without `outputSchema` the envelope remains untyped for code-gen models — prioritize typed `output_schema` per tool alongside `Field(description)`.

---

## 9. Ready for Proposal

**Yes.**

Orchestrator should launch `sdd-propose` for `mcp-dx-audit-surface` with:

```yaml
change_name: mcp-dx-audit-surface
scope: mcp-server (spec delta) + mcp_server.py surface + README phasing
intents:
  - Make the 11-tool surface learnable from tools/list alone (no prompts/list, no README needed)
  - Tighten schema (descriptions, enum, annotations, outputSchema) and error contract (single envelope + error_code + next)
  - Fix naming debt (output file/dir, profile/render de-polymorphize, all_files/no_checks normalization)
```

Proposal must carry the amended phasing (merged S slice first) and explicitly defer `sofer_build`.

---

## 10. Evidence Index

| Claim | Source |
|-------|--------|
| 11 tools schema with zero descriptions / no annotations / generic output_schema | `server._list_tools()` live introspection (FastMCP 3.4.7) — `C:\Users\elaze\AppData\Local\Temp\check_mcp5.py` output |
| Canonical Build chain | `README.md:484-487`, `mcp_server.py:1796-1801` instructions + `mcp_server.py:1663` `prepare_dataset` prompt |
| Bootstrap Phase 0 conditional | Owner decision in #111 §2 + `mcp_server.py:1283,1347,1430` outdated phrasing |
| Containment / publish ladder / token chain verified | `mcp_server.py:254-322` `_contained_path`, `mcp_server.py:852-894` ladder, `mcp_server.py:573-595` `_get_hf_token` |
| `feat/mcp-build-clarity` deferred `sofer_build` | `openspec/changes/feat-mcp-build-clarity/design.md` decision B |
| CLI `choices` for `target` vs MCP free string | `cli.py:1062` `choices=["hf","local"]` vs `mcp_server.py:736` `target: str` |
| FastMCP tool decorator supports `annotations` + `output_schema` | `inspect.signature(FastMCP.tool)` — `annotations: ToolAnnotations | dict`, `output_schema: dict | None` |

