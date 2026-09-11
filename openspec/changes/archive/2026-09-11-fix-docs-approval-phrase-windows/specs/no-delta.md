# Spec Analysis — No Spec Delta Required

**Change**: `2026-09-11-fix-docs-approval-phrase-windows` (Fixes GitHub #151)
**Date**: 2026-09-11
**Verdict**: **No delta.** This change adds an OS-level operator recipe (how to generate and
persist the approval phrase on Windows) to `README.md` and `README_ES.md`. Every behavior
proposition the new prose restates or depends on is already normative and executable-tested.
No `## ADDED` / `## MODIFIED` / `## REMOVED` requirement is introduced, and nothing in this
file implies a code, configuration, or test change.

---

## 1. Documentation gap confirmed (prose only, absence-type defect)

The issue is not a false README claim but a **missing** claim: the hardening section offers only
a bash generation path, so Windows hosts have no documented way to produce or persist the
phrase and silently ship refusing every publish via `sofer_publish_confirm` →
`PUBLISH_APPROVAL_NOT_CONFIGURED`.

| Artifact | Location | Text | Status |
|---|---|---|---|
| `README.md` | L664 (`### Hardening for sensitive hosts`), L673-676 | bash fence `export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"` | **Only generation path — the gap** |
| `README.md` | L687-689 | `**Windows:**` launcher-environment + full-restart sentence | Correct baseline from #148 (PR #156, `ab2a68f`) — keep verbatim |
| `README.md` | L691-695 | `**Verify:**` → `sofer_auth_status(config)` → `approval_configured` | Correct — reference, don't restate |
| `README_ES.md` | L699, L708-711 | Spanish mirror of the bash fence | Same gap |
| `README_ES.md` | L722-724, L726-730 | Spanish mirror of the Windows + Verify paragraphs | Correct baseline — keep verbatim |

The fix is additive prose: a PowerShell generation snippet (portable .NET crypto RNG, valid on
Windows PowerShell 5.1 and PowerShell 7+), a `setx` cmd note with its persistence caveats, and
container prose on `$env:`/`set` session scope vs. the launcher environment. No behavior changes.

---

## 2. Existing normative coverage (claims verified line by line)

The proposal's central claim — *no spec delta is required because the spec already mandates every
behavior the new prose states* — is **confirmed**. Each proposition is already normative:

| Proposition the new Windows prose states or depends on | Canonical location | Existing normative text (verbatim excerpt) | Verdict |
|---|---|---|---|
| The approval phrase is mandatory; absent phrase ⇒ publish refused with `PUBLISH_APPROVAL_NOT_CONFIGURED`; empty/whitespace-only counts as unconfigured; the acknowledgment booleans alone are never sufficient | `openspec/specs/mcp-server/spec.md:131` (MSP-R05 heading), body at `:137` | "…SHALL require a host-configured `approval_phrase` (from `build_server(root, approval_phrase)` or the `SOFER_MCP_APPROVAL_PHRASE` environment variable) and SHALL refuse on absent or mismatched phrase… When the server has NO phrase configured — including an empty or whitespace-only value, which SHALL be normalized to unconfigured — `sofer_publish_confirm` SHALL refuse with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reach the upload; the acknowledgment booleans alone are never sufficient." | Already covered |
| `PUBLISH_APPROVAL_NOT_CONFIGURED` is a first-class refusal code | `openspec/specs/mcp-server/spec.md:386` (10.3 heading), body at `:390` | "`error_code` MUST be `CONFIG_ERROR\|VALIDATION_FAILED\|QUALITY_GATE_FAILED\|PUBLISH_RISK_NOT_ACKD\|PUBLISH_CONFIDENTIAL_NOT_ACKD\|PUBLISH_APPROVAL_REQUIRED\|PUBLISH_APPROVAL_NOT_CONFIGURED\|TARGET_INVALID`" | Already covered |
| The verification path is `sofer_auth_status()` + `approval_configured`; phrase always required | `openspec/specs/mcp-server/spec.md:420` (10.8 heading), body at `:424` | "…`approval_configured:bool, requires_approval_phrase:bool`… `requires_approval_phrase` is always `true` (a phrase is always required for publish); `approval_configured` reflects whether the server has a non-blank phrase set. An empty or whitespace-only phrase MUST be treated as unconfigured." | Already covered |
| Per-agent env persistence stores env **names**, never secret values | `openspec/specs/mcp-registration/spec.md:9` (MCP-REG-01 heading), body at `:19` | "Both Gemini `env` and Codex `env_vars` persist env NAMES only (an allow-list of keys present in the environment); secret values (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) are never written to disk." | Already covered (scenarios at `:65-67`) |

The behavior is additionally pinned executable-side (`tests/test_mcp_server.py:757-758, 783,
795-820`; `tests/test_mcp_process.py:621` — fail-closed refusal and restart semantics). Those
tests pass **unchanged** and are the proof that the new prose describes real behavior.

### 2a. The Windows generation path is NOT spec-covered — and should not be

No requirement in `openspec/specs/` pins the README's hardening/approval-setup prose. The only
README-content requirements in the MCP area are `mcp-server/spec.md:346-382` (MSP-R12): they pin
the **Install + AI/MCP** sections (PEP 508 URLs, `uv tool`/`uvx --with`, "included by default")
and the §13 EN↔ES mirror rule — not the hardening section, not `SOFER_MCP_APPROVAL_PHRASE`
setup, and not any `setx`/PowerShell operator recipe. Grep across `openspec/specs/` for
`Hardening|setx|PowerShell|openssl` returns **zero** hits; the only `SOFER_MCP_APPROVAL_PHRASE`
hits are behavior contracts (`mcp-server/spec.md:137`, `mcp-registration/spec.md:19/65/67`).
The README Windows generation path is deployment documentation, not system behavior.

---

## 3. Why no delta is warranted

1. **No behavioral proposition is missing.** Every statement the new Windows prose makes is a
   restatement of MSP-R05 (`:137`), 10.3 (`:390`), 10.8 (`:424`), or MCP-REG-01 (`:19`), or is an
   OS-level operator recipe (PowerShell/cmd/env semantics, per Microsoft documentation) that no
   spec can or should pin as system behavior. A delta here would duplicate existing normative
   text (AGENTS.md §4) or fabricate a contract out of operator guidance.
2. **The only candidate delta is a docs-conformance requirement, which this repo would force
   through a test.** Per `openspec/config.yaml` `rules.specs` and AGENTS.md §6, every scenario
   MUST have a corresponding test. A requirement of the form "the README SHALL document the
   Windows generation path" would oblige a README-grep scenario. The pattern provably exists
   repo-wide — `tool-config/spec.md:172` (TC-09) with `tests/test_config.py:589-594`
   (`test_bootstrap_limitation_documented` greps `docs/configuration.md`), `packaging/spec.md:118`
   (PKG-05), and `tests/test_mcp_server.py:3656` (`TestBuildClarityReadme`, a README-grep class) —
   which is exactly why such a delta was **rejected**: it would expand a prose-only docs change
   into `tests/`, a scope the approved proposal explicitly excludes (see *Follow-up candidate*).
3. **No canonical docs spec exists for this area to modify.** `openspec/specs/` has README-touching
   requirements only where behavior is already nailed down by prose-generation or install paths
   (PKG-05, TC-09, MSP-R12). None covers publish-approval documentation; pretending to modify one
   would be a fabricated delta (same finding as the merged #148 `no-delta.md` §3).
4. **AGENTS.md §13 (README/README_ES sync) is a process rule, not a spec requirement.** It governs
   *when* both files are edited (same commit), not *what* the system does; encoding it as a
   scenario would encode repository workflow as system behavior (MSP-R12's §13 scenario at `:378`
   already pins the mirror rule for the Install/AI-MCP sections; the new prose inherits it).

---

## 4. Boundary this artifact enforces

- The change modifies **`README.md` and `README_ES.md` only** (one additive block per file).
- `openspec/specs/**` is read-only for this change (no canonical merge at archive time).
- `src/**` and `tests/**` are read-only for this change; no RED/GREEN cycle — the change is prose,
  and the existing suite (`tests/test_mcp_server.py`, `tests/test_mcp_process.py`) is expected to
  pass **unchanged** as executable proof that documented behavior is real.
- The additions MUST NOT restate #148 baseline sentences (fail-closed wording, read-once
  sentence, `**Windows:**` launcher sentence, `**Verify:**` paragraph) — pointer/reference only
  (AGENTS.md §4), and MUST NOT pre-empt open issues #144/#145.

---

## 5. Residual risk (recorded, deliberately out of scope)

Two recurrence-prevention candidates, intentionally **not** created by this change:

1. **"Read once at process start / restart required" is code-pinned, not spec-pinned.** The single
   env read (`src/sofer/mcp_server.py:2640-2648` → module-level `_APPROVAL_PHRASE`) and the
   refusal-message restart hint (`:1154-1155`) are the ground truth the new Windows prose relies
   on, but no requirement states the read-once contract. This is the **same finding** as the merged
   #148 (`no-delta.md` §5). A future change could make it explicit in `mcp-server/spec.md`.
2. **No requirement pins README conformance for the approval-setup prose.** The docs-conformance
   delta ("README SHALL document the Windows generation path") is feasible — the grep-test pattern
   exists (TC-09/PKG-05/`TestBuildClarityReadme`) — but it would expand this docs-only change into
   `tests/`; recorded here as a follow-up candidate, deliberately **not** created (identical
   disposition to #148's `no-delta.md` §5).

---

## 6. Engine reconciliation — no-delta blocking false positive (spec phase)

**Status**: no delta authored; `openspec/specs/**` untouched for this change.

The native status engine reports `blockedReasons: ["specs/ has files but no non-empty
<domain>/spec.md"]` / `artifacts.specs: "missing"` whenever a change's `specs/` directory is
non-empty without a `<domain>/spec.md`. This is the **known false positive** for a deliberately
no-delta change — the engine does not recognize a no-delta verdict artifact; the maintainer
adjudicates (§2/§3 and this file are the reconciliation record).

Engine-facing facts, verified this phase:

| Check | Evidence | Result |
|---|---|---|
| No `<domain>/spec.md` authored | this directory contains only `no-delta.md` | ✅ deliberate |
| No delta sections authored | no `## ADDED/MODIFIED/REMOVED/RENAMED` content anywhere in this file | ✅ deliberate |
| Canonical already normative | verbatim anchors, 1 match each: `mcp-server/spec.md:137` (`the acknowledgment booleans alone are never sufficient`), `:390` (`PUBLISH_APPROVAL_NOT_CONFIGURED\|TARGET_INVALID`), `:424` (`requires_approval_phrase` is always `true`); `mcp-registration/spec.md:19` (`SOFER_MCP_APPROVAL_PHRASE`) are never written to disk`) | ✅ §2 stands |
| `openspec/specs/**` untouched | no canonical writes performed or planned this phase | ✅ |

**Sync/archive expectation** (recorded here for the later phases, mirroring #148 precedent):
the sync phase must verify a no-op (zero domain deltas, `openspec/specs/**` clean) and must **not**
write a `sync-report.md` — this repository records spec-sync outcomes in the `## Spec Sync` section
of `archive-report.md` (25 archived changes do so; no `sync-report.md` exists anywhere under
`openspec/`). The archive phase must therefore record `## Spec Sync → None — no delta was authored
for this change` (precedent: `openspec/changes/archive/2026-09-09-fix-mcp-hf-token-fallback/
archive-report.md`). The engine's blocked-state is **not** an archive blocker.

---

## 7. Sync outcome — verified no-op (`sdd-sync`, 2026-09-11)

**Status**: verified no-op (no delta to merge) · **Canonical writes**: none · **`openspec/specs/**`** unchanged.

> Section-number note: the mandated heading text is preserved verbatim; the number is **7** (not 6) because §6 above already holds the spec-phase engine reconciliation for this change. The merged #148 sibling has no such section, so its sync outcome landed at §6.

Re-verified independently by the sync phase — evidence gathered in this pass, not carried over from the proposal or from §6:

| Check | Evidence (this pass) | Result |
|---|---|---|
| Zero domain deltas | `find openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/specs -mindepth 1 -maxdepth 1` → `…/specs/no-delta.md` | ✅ no `<domain>/spec.md` delta exists |
| No delta sections in the change | `grep -rn '^## \(ADDED\|MODIFIED\|REMOVED\|RENAMED\)' …/specs/` → exit 1; same grep over the whole change root → exit 1 | ✅ zero matches |
| No `RENAMED` delta (unsupported by the native helper) | same grep | ✅ zero matches — no unsupported sync path involved |
| Canonical already normative | verbatim anchors, 1 match each: `openspec/specs/mcp-server/spec.md:137` (`the acknowledgment booleans alone are never sufficient`), `:390` (`PUBLISH_APPROVAL_NOT_CONFIGURED\|TARGET_INVALID`), `:424` (`` `requires_approval_phrase` is always `true` ``); `openspec/specs/mcp-registration/spec.md:19` (``SOFER_MCP_APPROVAL_PHRASE`) are never written to disk``) | ✅ §2 stands |
| `openspec/specs/**` untouched | `git status --porcelain openspec/specs/` → empty (exit 0) | ✅ no canonical file modified |
| Active same-domain collisions | `ls openspec/changes/` → `2026-09-11-fix-docs-approval-phrase-windows` + `archive` only | ✅ none — no collision warning to raise |
| Destructive delta needing approval | no `REMOVED` requirement, no large `MODIFIED` block — no delta at all | ✅ not applicable; no approval required or given |
| Legacy flat spec | `specs/` contains `no-delta.md` only | ✅ not applicable |

Supporting check: `grep -rn 'Hardening\|setx\|PowerShell\|openssl' openspec/specs/` → zero hits (exit 1), re-confirming §2a — the new Windows generation recipe is deployment documentation that no canonical spec covers, and none should be fabricated for it. `openspec/config.yaml` defines **no `rules.sync` key** (only `proposal`/`specs`/`design`/`tasks`/`apply`/`verify`/`archive`), so no sync-phase rule constrains this outcome.

**No `sync-report.md` was written, deliberately.** This repository records spec-sync outcomes in the `## Spec Sync` section of `archive-report.md` (25 archived changes do so; 8 use `## Spec Sync Summary`), and **no `sync-report.md` exists anywhere under `openspec/`** (verified this pass: `find openspec -name sync-report.md` → 0) — creating one would invent a convention. The archive phase must therefore record `## Spec Sync → None — no delta was authored for this change` (precedent: `openspec/changes/archive/2026-09-11-fix-docs-fail-closed-publish/archive-report.md:18-20`; `…/2026-09-09-fix-mcp-hf-token-fallback/archive-report.md:17-19`), citing §2/§3 and this section.

**Structured status / `actionContext` findings** (consumed as authoritative, `isNonAuthoritative: false`): `artifactStore: openspec` (repo-local) ✅; `actionContext.mode: repo-local` ✅ — the `workspace-planning` gate does not apply; `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]` ✅ — the only file this phase writes is inside the root; `nextRecommended: sdd-verify` (superseded by this pass); `taskProgress: 29/29 complete`, **0 unchecked implementation rows** ✅; `blockedReasons: ["domain specs are missing or partial."]` with `sync: blocked` / `applyState: blocked` → **FALSE POSITIVE** for a deliberately no-delta change (identical disposition to §6 and to merged #148). Sync is therefore **not-applicable / verified no-op**, not blocked.

**Next phase**: `sdd-archive`, once the five parent-owned lifecycle rows (5.1–5.3 commit + PR + region confirmation; 6.1–6.2 bounded review + human delivery gate) land — the engine's spec heuristic does not block archive and needs no reconciliation beyond §6 and this section.