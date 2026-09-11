# Spec Analysis — No Spec Delta Required

**Change**: `2026-09-11-fix-docs-fail-closed-publish` (Fixes GitHub #148)
**Date**: 2026-09-11
**Verdict**: **No delta.** This change corrects a documentation drift; the behavior it must describe is
already normative and executable-tested. No `## ADDED` / `## MODIFIED` / `## REMOVED` requirement is
introduced, and nothing in this file implies a code, configuration, or test change.

---

## 1. Defect confirmed (documentation only)

| Artifact | Location | Text | Status |
|---|---|---|---|
| `README.md` | L643-647 (`### Security model` → "Fail-closed publish authorization") | "…and — **when configured** — an approval phrase compared with `hmac.compare_digest`" | Contradicts the spec — implies the phrase is optional |
| `README.md` | L670-671 (`### Hardening for sensitive hosts`) | "When no phrase is configured, only the two acknowledgment booleans gate the HF publish — a weaker posture…" | Contradicts the spec — primary defect |
| `README_ES.md` | L681-682 | "…y — cuando está configurada — una frase de aprobación…" | Spanish mirror of the adjacent defect |
| `README_ES.md` | L708-710 | "Cuando no hay frase configurada, solo los dos booleanos de reconocimiento…" | Spanish mirror of the primary defect |

---

## 2. Existing normative coverage (claims verified line by line)

The proposal's central claim — *no spec delta is required because the spec already mandates the
fail-closed refusal* — is **confirmed**. Each proposition the README must state is already normative:

| Proposition the README must state | Canonical location | Existing normative text (verbatim excerpt) | Verdict |
|---|---|---|---|
| No phrase configured ⇒ publish is refused | `openspec/specs/mcp-server/spec.md:131` (MSP-R05) — body at `:137` | "When the server has NO phrase configured — including an empty or whitespace-only value, which SHALL be normalized to unconfigured — `sofer_publish_confirm` SHALL refuse with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reach the upload; **the acknowledgment booleans alone are never sufficient**." | Already covered |
| The phrase is mandatory for every publish (not optional) | `openspec/specs/mcp-server/spec.md:137` | "SHALL require a host-configured `approval_phrase` (from `build_server(root, approval_phrase)` or the `SOFER_MCP_APPROVAL_PHRASE` environment variable) and SHALL refuse on absent or mismatched phrase, compared with a constant-time comparison (`hmac.compare_digest`)." | Already covered |
| `PUBLISH_APPROVAL_NOT_CONFIGURED` is a first-class refusal code | `openspec/specs/mcp-server/spec.md:386`, body at `:390` | "`error_code` MUST be `…|PUBLISH_APPROVAL_REQUIRED|PUBLISH_APPROVAL_NOT_CONFIGURED|TARGET_INVALID`" | Already covered |
| The verification path is `sofer_auth_status()` + `approval_configured` | `openspec/specs/mcp-server/spec.md:420`, body at `:424` | "`requires_approval_phrase` is always `true` (a phrase is always required for publish); `approval_configured` reflects whether the server has a non-blank phrase set. An empty or whitespace-only phrase MUST be treated as unconfigured (`approval_configured:false`)." | Already covered |
| Per-agent env handling persists env **names**, never secret values | `openspec/specs/mcp-registration/spec.md:19` | "Both Gemini `env` and Codex `env_vars` persist env NAMES only … secret values (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) are never written to disk." | Already covered |

The behavior is additionally pinned executable-side (`tests/test_mcp_server.py:757-758`, `:783`,
`:795-820`; `tests/test_mcp_process.py:621`). Those tests pass **unchanged** — they are the proof that
the corrected prose matches reality, not a gap to fill.

---

## 3. Why no delta is warranted

1. **No behavioral proposition is missing.** Every statement the corrected README will make is a
   restatement of MSP-R05 (`:137`), 10.3 (`:390`), 10.8 (`:424`), or MCP-REG-01 (`:19`). A delta here
   would duplicate existing normative text, which AGENTS.md §4 forbids.
2. **The only candidate delta is documentation wording, not behavior.** A requirement of the form
   "the README SHALL describe the fail-closed publish posture" is not a behavior contract. Per
   `openspec/config.yaml` `rules.specs` and AGENTS.md §6, every scenario MUST have a corresponding
   test, so such a delta would oblige a README-grep test and expand a prose-only change into
   `tests/` — a scope the approved proposal explicitly excludes.
3. **No canonical docs spec exists for this area to modify.** `openspec/specs/` has README-touching
   requirements only where behavior is already nailed down by prose-generation or install paths
   (`packaging/spec.md:116` PKG-05; `tool-config/spec.md:172` TC-09). Neither covers publish-approval
   documentation, and pretending to modify one would be a fabricated delta.
4. **AGENTS.md §13 (README/README_ES sync) is a process rule, not a spec requirement.** It governs
   *when* both files are edited (same commit), not *what* the system does; encoding it as a scenario
   would encode repository workflow as system behavior.

---

## 4. Boundary this artifact enforces

- The change modifies **`README.md` and `README_ES.md` only**.
- `openspec/specs/**` is read-only for this change (no canonical merge at archive time).
- `src/**` and `tests/**` are read-only for this change.
- The corrected wording MUST NOT assert anything beyond §2; no claim about the CLI needing a phrase
  (`docs/cli-vs-mcp.md` states the CLI never needs it), and no pre-emption of open issues #144/#145/#151.

---

## 5. Residual risk (recorded, deliberately out of scope)

The drift went undetected because no requirement pins README conformance for the publish-approval
posture, and the existing README-grep test class (`tests/test_mcp_server.py`, `TestBuildClarityReadme`)
covers the tool chain and arguments but not this surface. Preventing recurrence would require a
**separate** change introducing a docs-conformance requirement plus its grep test. That is recorded
here as a follow-up candidate and is intentionally **not** created by this change.
