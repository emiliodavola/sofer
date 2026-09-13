# Proposal: Document Windows approval-phrase generation (PowerShell + cmd)

**Issue**: GitHub #151 (OPEN) — docs-only
**Date**: 2026-09-11
**Status**: proposed
**Change type**: docs-only (`README.md`, `README_ES.md`) — no code, no behavior, no spec delta required

## Intent

README "Hardening for sensitive hosts" shows only a Linux/bash way to create
the approval phrase (`export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"`).
Windows users have no documented way to generate or set it: no `openssl`, no
`export`. Without a documented generation path, Windows hosts silently ship
with no phrase and `sofer_publish_confirm` refuses every publish with
`PUBLISH_APPROVAL_NOT_CONFIGURED` — a setup trap for exactly the sensitive-host
workflow the section exists to protect.

The fix is additive documentation only: give Windows a way to (1) generate a
random hex phrase with the .NET crypto RNG, (2) persist/set it via cmd
(`setx`), and (3) understand the Windows env semantics — `$env:`/`set` affect
only the current shell, the value must reach the environment that **launches**
the MCP server (launcher env or `setx` followed by a full host restart), and a
running server never re-reads env vars. The fix complements the fail-closed
rewrite already merged in #148 (PR #156, `ab2a68f`) — it must **not** duplicate
or regress that wording.

## Sources

- **Issue #151** (per the mandate): README lacks a Windows path to generate/set
  the approval phrase; requested: PowerShell snippet using .NET crypto RNG, a
  `setx` cmd note, an explanation of `$env:`/`set` vs launcher-environment
  semantics and host restart, and a link to `sofer_auth_status` diagnostics;
  `README_ES.md` must mirror in the same commit.
- `README.md:664` — `### Hardening for sensitive hosts` (baseline = merged #148).
- `README.md:673-676` — the **only** generation snippet today: a bash fence
  (`export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"`). No Windows path.
- `README.md:687-689` — existing `**Windows:**` launcher-environment + full-restart
  sentence (from #148). **Correct and mandatory — do not regress.**
- `README.md:691-695` — existing `**Verify:**` paragraph (`sofer_auth_status(config)`
  → `approval_configured`; `PUBLISH_APPROVAL_NOT_CONFIGURED` vs
  `PUBLISH_APPROVAL_REQUIRED`). The Windows snippet container must **refer** to it,
  not restate it.
- `README_ES.md:699` — `### Endurecimiento para hosts sensibles`; fence at
  `:708-711` (bash only); Windows sentence `:722-724`; Verificación `:726-730`.
  Same gap as EN.
- `src/sofer/mcp_server.py:2640-2648` — the **single** env read site: `build_server`
  reads `SOFER_MCP_APPROVAL_PHRASE` at build time into the module-level
  `_APPROVAL_PHRASE` (blank/whitespace normalized to unconfigured). Ground truth
  for "read once at process start; restart to change" (also echoed in the refusal
  message at `:1155`: "…set `SOFER_MCP_APPROVAL_PHRASE` and restart").
- `src/sofer/mcp_server.py:1154-1155`, `:2626-2630` — fail-closed refusal and
  `build_server` docstring ("REQUIRED … when unset the publish is DISABLED").
- `src/sofer/mcp_server.py:1660-1663` — `sofer_auth_status`: `approval_configured =
  _APPROVAL_PHRASE is not None`; `requires_approval_phrase = True`. The verified
  diagnostics the issue wants linked.
- Windows env model (external, Microsoft-documented): `set` (cmd) and `$env:` /
  `$env:NAME = value` (PowerShell) mutate **only the current process** (inherited
  by children); `setx NAME value` persists to the user environment
  (`HKCU\Environment`) and is visible only to **newly created** processes; it does
  **not** affect the current shell; values are stored unencrypted; `setx` truncates
  values longer than 1024 characters. `[System.Convert]::ToHexString` requires
  .NET 5+ (PowerShell 7+); the static `RandomNumberGenerator::GetBytes(int)` form
  requires .NET Core 3.0+ — **both fail on Windows PowerShell 5.1** (the default
  `powershell.exe`), where you must use the instance API
  `[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)`
  with a pre-allocated byte array; `RNGCryptoServiceProvider` (the issue's literal
  suggestion) is deprecated in .NET 6+ (SYSLIB0023).

### Verified current state (re-investigation completed 2026-09-11)

| Artifact | Location | Content | Verdict |
|---|---|---|---|
| `README.md` | L664, L666-695 | `### Hardening for sensitive hosts` — fail-closed, read-once, per-agent env persistence, Windows launcher sentence, Verify paragraph | Correct baseline from #148 — keep verbatim |
| `README.md` | L673-676 | bash fence `export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"` | **Only generation path — the gap** |
| `README.md` | L687-689 | Windows launcher-environment sentence | Correct — complement, don't regress |
| `README_ES.md` | L699, L708-711, L722-724 | Mirror of the above | Same gap |
| `src/sofer/mcp_server.py` | L2640-2648 | single env read into `_APPROVAL_PHRASE` at build time | Read-once semantics — code-pinned |
| `src/sofer/mcp_server.py` | L1154-1155, L1660-1663, L2626-2630 | refusal + auth_status fields + docstring | Correct — read-only reference |
| `docs/cli-vs-mcp.md` | — | **does not exist** (verified by sibling #148 design §5) | Do **not** create it |
| `openspec/specs/mcp-server/spec.md` | L137, L390, L424 | fail-closed ladder, `PUBLISH_APPROVAL_NOT_CONFIGURED` enum, `sofer_auth_status` fields | Already normative — see Spec delta |
| `openspec/specs/mcp-registration/spec.md` | L19 | env **names** only persisted; secret values never written to disk | Relevant context for the `setx` note (OS-level persistence, distinct from sofer's own config writes) |

## Scope

### In Scope

- `README.md` — inside `### Hardening for sensitive hosts` only:
  - **PowerShell generation snippet** (Windows): `.NET crypto RNG` producing the
    same 32-hex-char shape as the existing `openssl rand -hex 16` example, using
    the **portable** instance API (`RandomNumberGenerator::Create().GetBytes(...)`),
    not the deprecated `RNGCryptoServiceProvider` and not the PowerShell-7-only
    static `GetBytes(int)` form — a documented deviation from the issue's literal
    snippet (see *Alternatives*).
  - **cmd note**: `setx SOFER_MCP_APPROVAL_PHRASE <value>` — persists the value for
    **new** processes; does not affect the current shell; stored unencrypted;
    full host restart still required (aligns with the existing `**Windows:**`
    sentence).
  - **Container prose** stating the Windows semantics: `$env:` (PowerShell) and
    `set` (cmd) affect only the current shell/session; the value must be in the
    environment that **launches** the MCP server (launcher env, or `setx` followed
    by a full host restart); a running server never re-reads env vars.
  - A pointer to the existing `**Verify:**` paragraph (`sofer_auth_status` →
    `approval_configured`), per the issue's "link to `sofer_auth_status`
    diagnostics" acceptance item — pointer, not restatement (AGENTS.md §4).
- `README_ES.md` — mirror the same additions in the **same commit** (AGENTS.md
  §13): translated prose only; `SOFER_MCP_APPROVAL_PHRASE`, `setx`, `$env:`,
  `set`, `RandomNumberGenerator`, `sofer_auth_status`, `approval_configured`,
  code fences stay English. Heading `### Endurecimiento para hosts sensibles`
  unchanged.

### Out of Scope

- **Any code, behavior, config, or test change.** The server is correct; this is
  prose only.
- **Any change to the #148 baseline text** in the hardening section (fail-closed
  phrasing, read-once sentence, per-agent env paragraph, Windows launcher
  sentence, Verify paragraph) — the additions slot in around it.
- **Spec delta** — see below; none is required.
- **Open issues #144 / #145** (approval-posture area) — not folded in; no wording
  that pre-empts their outcomes.
- New README sections or files (`docs/…`), `CHANGELOG`-style updates,
  `SOFER_TRACE.md`/`TRACE.md` (neither exists at the repo root), CI, release
  artifacts. `docs/cli-vs-mcp.md` must **not** be created (sibling #148 verified
  it does not exist and forbade creating it).
- Commit, PR, and merge decisions — deferred to the delivery gate (see
  *Delivery*).

## Capabilities / Spec delta

### New Capabilities

- None.

### Modified Capabilities

- **None — no spec delta is required.** Every behavior proposition the new
  Windows text either restates or depends on is already normative:
  - phrase mandatory + fail-closed refusal — `openspec/specs/mcp-server/spec.md:137` (MSP-R05);
  - `PUBLISH_APPROVAL_NOT_CONFIGURED` as a first-class error code — `spec.md:390` (10.3);
  - `sofer_auth_status` / `approval_configured` / `requires_approval_phrase` — `spec.md:424` (10.8);
  - per-agent env names-only persistence — `openspec/specs/mcp-registration/spec.md:19`.
  The new content is an **OS-level operator recipe** (how to generate/persist a
  secret on Windows) — not a system-behavior contract.

  Two honest caveats:
  1. The "read once at process start / restart required" prop is **code-pinned
     (`mcp_server.py:2640-2648` module-level `_APPROVAL_PHRASE`), not
     spec-pinned** — same finding as the merged #148 (`no-delta.md` §5). Making it
     explicit in the spec is a deliberate follow-up candidate, **not** created here.
  2. A docs-conformance delta ("README SHALL document the Windows generation
     path") is *feasible* in this repo — precedent `tool-config/spec.md:172`
     (TC-09) and `packaging/spec.md:118` (PKG-05) spec README content with grep
     tests (`tests/test_config.py:589-594`, `tests/test_mcp_server.py:3656`
     `TestBuildClarityReadme`). But `openspec/config.yaml` `rules.specs` pairs
     every scenario with a test, so such a delta would force a README-grep test
     and expand this docs-only change into `tests/` — rejected for scope, recorded
     as a recurrence-prevention candidate.

  **Skip the spec phase unless the parent explicitly overrides this.**

## Approach

Strictly additive, two files, one commit (per §13). Do not touch any #148 line.

1. **`README.md` — insert the Windows generation block** between the bash fence
   (`:676` end) and the read-once paragraph (`:678`), or immediately after the
   read-once/per-agent paragraph and before the existing `**Windows:**` sentence
   (`:687`) — exact placement decided at design time; the region stays contiguous
   and the `**Windows:**` sentence stays verbatim.
   - PowerShell fence (portable across Windows PowerShell 5.1 and PowerShell 7+):
     allocate `New-Object byte[] 16`, fill via
     `[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)`,
     join `$bytes | ForEach-Object { $_.ToString('x2') }` → 32-hex phrase;
     `$env:SOFER_MCP_APPROVAL_PHRASE = $phrase` sets it **for this session only** —
     the fence prose must say so explicitly.
   - cmd note: `setx SOFER_MCP_APPROVAL_PHRASE <value>` + the caveats (new
     processes only; current shell unaffected; stored unencrypted; full host
     restart still required).
   - Container prose: `$env:`/`set` scope vs launcher environment; the value must
     be in the environment that launches the MCP server; a running server never
     re-reads env vars; pointer to the existing **Verify:** paragraph
     (`sofer_auth_status` → `approval_configured`).
   - A short comment line inside the PowerShell fence noting the portable RNG API
     (why not `RNGCryptoServiceProvider`, why not `ToHexString`).
2. **`README_ES.md` — mirror in the same commit**: neutral Spanish prose, all
   technical tokens English, heading unchanged, section order/parity preserved
   (§13 + sibling precedent).
3. **Self-check before verify**: positive greps in **both** files —
   `RandomNumberGenerator`, `setx`, `$env:SOFER_MCP_APPROVAL_PHRASE`,
   `openssl rand -hex 16` (unchanged), `approval_configured`; parity greps
   (heading + section order EN↔ES); zero-tolerance: no re-introduced "weak
   posture"/"optional phrase" phrasing, no duplicated #148 sentences, no literal
   `RNGCryptoServiceProvider`.

No RED/GREEN cycle: the change is prose. Executable proof that the documented
behavior is real is the existing suite (`tests/test_mcp_server.py`,
`tests/test_mcp_process.py`), expected to pass **unchanged**.

## Alternatives

| Alternative | Verdict |
|---|---|
| Issue's literal snippet (`RNGCryptoServiceProvider`, static `::GetBytes()` form) | **Rejected.** `RNGCryptoServiceProvider` is deprecated (.NET 6+, SYSLIB0023); the static `RandomNumberGenerator::GetBytes(int)` needs .NET Core 3.0+ → fails on Windows PowerShell 5.1 (the default `powershell.exe`). |
| `[System.Convert]::ToHexString(...)` | **Rejected.** .NET 5+/PowerShell 7+ only → same 5.1 break. |
| `python -c "import secrets; print(secrets.token_hex(16))"` fallback (works wherever sofer runs; cmd-capturable) | **Possible but deferred.** Consistent with sofer being a Python tool, but adds a third path the issue didn't ask for and widens the diff; recommend leaving out unless the user wants it. Flagged in the question round. |
| New standalone `Windows:` subsection / new `docs/` file | **Rejected.** Hardening section is already Windows-aware (launcher sentence); additive inline keeps the minimal diff, matches the `### Windows notes` precedent (README.md:134), and preserves §13 parity. |
| Spec delta (docs-conformance requirement) | **Rejected** — see *Capabilities / Spec delta*. |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `README.md` | Modified | Windows generation block (PowerShell fence + cmd/setx note + scope/restart prose + diagnostics pointer) inserted inside `### Hardening for sensitive hosts` (L664-695); everything else untouched |
| `README_ES.md` | Modified | Same block mirrored in the same commit; heading `### Endurecimiento para hosts sensibles` (L699) preserved |
| `src/sofer/**`, `tests/**`, `openspec/specs/**` | Unchanged | Read-only references / untouched |
| `docs/`, `TRACE.md`, `SOFER_TRACE.md` | Unchanged | Out of scope; `docs/cli-vs-mcp.md` deliberately **not** created |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| PowerShell snippet breaks on Windows PowerShell 5.1 (`powershell.exe`), the default | Med | Use the portable instance API `Create().GetBytes($bytes)` with a pre-allocated array; design phase must validate the fence against both `$PSVersionTable` 5.1 and pwsh 7 before apply; comment in the fence explains the choice; **no** `ToHexString`, **no** static `GetBytes(int)`, **no** `RNGCryptoServiceProvider` |
| `setx` semantics over- or under-stated (current shell unaffected; new processes only; unencrypted; 1024-char cap) | Med | Keep only Microsoft-documented claims; explicit sentence that `setx` does not affect the current shell and that an already-running host still needs a full restart |
| Users expect `$env:`/`set` to persist and "it didn't work" support loops | Med | Container prose states session-scope explicitly and ties to the existing launcher-environment sentence — the value must be in the env that launches the MCP server |
| Regressing or duplicating the merged #148 baseline (fail-closed, read-once, launcher sentence, Verify) | Low | Strictly additive edits; diff review; zero-tolerance greps for re-introduced "weak posture / optional phrase" wording |
| `README_ES.md` drifts or lands in a later commit | Med | Same commit (§13); heading + section-order parity check as a step; §13 is a PR-template item |
| Snippet invents new values (length/algorithm) diverging from the existing example | Low | 16 bytes → 32 hex chars, matching `openssl rand -hex 16` exactly; no hardcoded new constants beyond the example (AGENTS.md §1) |
| Collision with open #144/#145 (approval-posture area) | Low | No new claims beyond current code/spec; additive only, no pre-emption |

## Rollback Plan

`git revert` the single docs commit (or restore both READMEs from the previous
revision). Docs-only, no migration, no state, no compatibility surface; the
spec/code are untouched, so no spec or behavior rollback exists or is needed.

## Dependencies

- None. No new dependencies, tooling, or config changes.
- Read-only references: `src/sofer/mcp_server.py:1154-1155, 1660-1663, 2640-2648`,
  `openspec/specs/mcp-server/spec.md:137/390/424`,
  `openspec/specs/mcp-registration/spec.md:19`; Windows env model per Microsoft
  documentation (not a repo dependency).

## Success Criteria

Mapped to the issue's three acceptance criteria (AC1-AC3):

- [ ] **AC1** — `README.md` hardness section shows a **PowerShell generation path**
  (Windows): a code fence producing a 32-hex-char phrase via the .NET crypto RNG
  using the portable `RandomNumberGenerator::Create()` instance API (no
  `RNGCryptoServiceProvider`, no PowerShell-7-only forms), **plus** a cmd note
  `setx SOFER_MCP_APPROVAL_PHRASE <value>` with its persistence caveats.
- [ ] **AC2** — the snippet container text explains the Windows process semantics:
  `$env:`/`set` affect only the current shell; the value must be in the
  environment that **launches** the MCP server (launcher env, or `setx` followed
  by a full host restart); a running server never re-reads env vars; and a
  pointer (not restatement) to `sofer_auth_status` → `approval_configured`
  diagnostics.
- [ ] **AC3** — `README_ES.md` mirrors all additions in the **same commit**, prose
  in Spanish, technical tokens English, heading and section-order parity
  preserved.
- [ ] No change to any #148 baseline sentence in the hardening section; zero
  re-introduced "weak posture / optional phrase" implications in either file.
- [ ] Zero changes outside `README.md` + `README_ES.md` (+ this change's SDD
  artifacts).
- [ ] `uv run pytest tests/ -q` passes unchanged; `uv run mypy src/` unaffected;
  `git diff --check` clean.
- [ ] Positive-presence greps pass in **both** files: `RandomNumberGenerator`,
  `setx`, `$env:`, `SOFER_MCP_APPROVAL_PHRASE`; negative grep passes:
  `RNGCryptoServiceProvider` (both files), "weaker posture"/"postura más débil".

## Delivery

Dedicated branch **`docs/fix-151-approval-phrase-windows`** (already created,
base `dev`), PR-only — never on `main`/`dev` directly, no tag, no release
(branch-flow rule: all work lands on `dev` first; releases are tag-driven via
`release.yml` and are irrelevant to a docs change). Size: two additive blocks in
two files, well under the 400-changed-line review budget → **single PR, no chain
strategy**; the final merge decision stays at the delivery gate (ask-on-risk
domain; no risk trigger expected for an additive prose change). Run
`gh pr create` with the `.github/PULL_REQUEST_TEMPLATE.md` filled in (mandatory
SDD-artifacts section).

## Proposal question round

Assumptions needing user review before spec/design (the user may answer,
correct, or request a second round):

1. **PowerShell floor.** Should the Windows path target **both** Windows
   PowerShell 5.1 (`powershell.exe`, the default) and PowerShell 7+, or 7+ only?
   **Assumption taken: both** — the portable `Create().GetBytes($bytes)` snippet;
   this deviates from the issue's literal static `::GetBytes()` form, which breaks
   on 5.1. Correct framing welcome: some projects drop 5.1 deliberately.
2. **`setx` plaintext caveat.** OK to state explicitly that `setx` persists the
   phrase **unencrypted** in the user environment (`HKCU\Environment`), mirroring
   the existing plaintext caveat for opencode's `environment` literal?
   **Assumption taken: yes — factual, keeps hardening honest.**
3. **Python fallback.** Add a `python -c "import secrets; …"` one-liner as an
   additional generation path (sofer is a Python tool, so it always exists where
   sofer runs), or keep strictly PowerShell + cmd per the issue?
   **Assumption taken: PowerShell + cmd only** (minimal, exactly what the issue
   asked); the Python one-liner is a rejected alternative unless you want it.
4. **Placement.** Insert the Windows block between the bash fence and the
   read-once paragraph (contiguous region), or after the `**Windows:**` launcher
   sentence? **Assumption taken: contiguous, immediately after the bash fence**;
   the existing `**Windows:**` sentence stays untouched.
5. **Diagnostics pointer.** The issue asks to link `sofer_auth_status`
   diagnostics — pointer to the existing **Verify:** paragraph or restate the
   full path in the Windows container? **Assumption taken: pointer only**
   (AGENTS.md §4 — no duplicated logic).