# Proposal: Fix README fail-closed publish documentation

**Issue**: GitHub #148 (OPEN)
**Date**: 2026-09-11
**Status**: proposed
**Change type**: docs-only (`README.md`, `README_ES.md`) — no code, no behavior, no spec delta required

## Intent

The README tells users (and agents) that the HF publish approval phrase is optional, while the running MCP server is **fail-closed**: with no phrase configured, `sofer_publish_confirm` refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reaches the upload. Documentation contradicts the security model and actively misleads readers — `TRACE.md` records an agent flow that kept retrying publish without a configured phrase precisely because the docs implied the two acknowledgment booleans were sufficient.

The fix is a docs correction, not a behavior change: make the user-facing README describe the posture the code already enforces and the spec already asserts.

## Sources

- Issue #148, verbatim: README "Hardening for sensitive hosts" claims *"only the two acknowledgment booleans gate the HF publish"*; code is fail-closed.
- `openspec/specs/mcp-server/spec.md:137` (MSP-R05, added by `sofer-mcp-server`) — already normative: *"When the server has NO phrase configured — including an empty or whitespace-only value, which SHALL be normalized to unconfigured — `sofer_publish_confirm` SHALL refuse with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reach the upload; **the acknowledgment booleans alone are never sufficient**."*
- `openspec/specs/mcp-server/spec.md:424` (10.8) — `sofer_auth_status` returns `approval_configured` and `requires_approval_phrase` (**always `true`**), no network, no value leak. This is the documented verification path.
- `openspec/specs/mcp-registration/spec.md:19` — codex `env_vars` / gemini `env` persist env **names only** (allow-list), secret values never written to disk. Ground truth for the per-agent guidance.

### Verified current state (no re-investigation needed)

| Artifact | Location | Content | Verdict |
|---|---|---|---|
| `README.md` | L672-673 | "When no phrase is configured, only the two acknowledgment booleans gate the HF publish — a weaker posture suited to trusted single-user stdio setups." | **Contradicts code** — the primary defect |
| `README.md` | L643-647 (`### Security model` → "Fail-closed publish authorization" bullet) | "…and — **when configured** — an approval phrase compared with `hmac.compare_digest`" | **Implies the phrase is optional** — adjacent instance of the same defect |
| `README_ES.md` | L708-709 | "Cuando no hay frase configurada, solo los dos booleanos de reconocimiento protegen la publicación en HF — una postura más débil…" | Spanish mirror of the primary defect |
| `README_ES.md` | ~L681-682 (`### Modelo de seguridad`) | "…y — cuando está configurada — una frase de aprobación…" | Spanish mirror of the adjacent defect |
| `src/sofer/mcp_server.py` | L1148-1155 | `if _APPROVAL_PHRASE is None:` → error envelope `PUBLISH_APPROVAL_NOT_CONFIGURED`, `next_hint={"action": "configure_approval_phrase"}`, message "…a human approval phrase is required for any Hugging Face publish" | Correct — fail-closed |
| `src/sofer/mcp_server.py` | L2623-2630 (`build_server` docstring) | phrase "REQUIRED for any HF publish (fail-closed) … the acknowledgment booleans alone are never sufficient" | Correct |
| `src/sofer/mcp_server.py` | L1060-1065 (`sofer_publish_confirm` param) | "ALWAYS required for publish — the server refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED`…" | Correct |
| `tests/test_mcp_server.py` L758, `tests/test_mcp_process.py` L621 | — | Existing tests already pin fail-closed ("the acknowledgment booleans are no longer sufficient alone") | Correct — no new test needed for a docs change |
| `docs/cli-vs-mcp.md` L99-100, L177-181 | — | Already states the fail-closed posture and "read **once** at process start" | **Already accurate — do not touch** |
| `TRACE.md` L145-181 | — | Already documents fail-closed reality and the `approval_configured` preflight | **Already accurate — do not touch** |

Only the two READMEs are wrong. Everything else in the repo already agrees with the code.

## Scope

### In Scope

- Rewrite the `README.md` `### Hardening for sensitive hosts` section (L661-673) so it describes the fail-closed reality:
  - the approval phrase is **mandatory for any HF publish** — without it `sofer_publish_confirm` returns `PUBLISH_APPROVAL_NOT_CONFIGURED` and the upload is disabled entirely;
  - the phrase is read **once at process start** (`build_server(root, approval_phrase=...)` or `SOFER_MCP_APPROVAL_PHRASE`) and is immutable for the life of that process — a long-running agent host must be restarted after the value changes;
  - how to supply it per agent, delegating to the existing MCP registration guidance rather than inventing a new table: codex `env_vars` allow-list, gemini `env` with `$KEY` references, opencode via the launcher environment or an explicit `environment` literal — with the plaintext caveat for the literal form (values written to disk; env names alone are persisted by the native `mcp add` paths);
  - **Windows note**: the variable must be present in the *launcher's* environment (the process that starts `sofer-mcp`), not merely in the shell you typed in, and the host must be fully restarted for the change to take effect;
  - **verification**: call `sofer_auth_status(config)` and read `approval_configured` (`requires_approval_phrase` is always `true`); distinguish `PUBLISH_APPROVAL_NOT_CONFIGURED` (no phrase on the server) from `PUBLISH_APPROVAL_REQUIRED` (missing/mismatched phrase in the call).
- Correct the adjacent `README.md` `### Security model` → "Fail-closed publish authorization" bullet: drop "when configured" and state that the phrase gate is always in force.
- Mirror **both** edits in `README_ES.md` in the **same commit** (AGENTS.md §13): translated prose only; commands, env var names, flags, error codes, and CLI output stay English.
- Replace the misleading sentence outright — the acceptance criterion is that **no leftover text implies the acknowledgment booleans are sufficient on their own** (nor that the phrase is optional).

### Out of Scope

- **Any code or behavior change.** The server is already correct and the spec already asserts it; this change modifies documentation only.
- **Open parallel issues #144 / #145 / #151** (approval-posture area — diagnostics, `approval_configured` envelope reporting, related hardening). Explicitly not folded in; no speculative wording that pre-empts their outcomes.
- **Spec delta.** See below — none is required.
- `TRACE.md`, `docs/cli-vs-mcp.md`, `CONTRIBUTING.md`, `README` sections outside the hardening/security-model area (MCP registration, tools table, workflow diagram are already consistent).
- Commit, PR, chaining, and release decisions — deferred to the human (see *Delivery* below).

## Capabilities / Spec delta

### New Capabilities
- None.

### Modified Capabilities
- **None — no spec delta is required.** `openspec/specs/mcp-server/spec.md` (MSP-R05 L137, 10.8 L424) already mandates fail-closed refusal with `PUBLISH_APPROVAL_NOT_CONFIGURED` and already states that the acknowledgment booleans alone are never sufficient. The failing artifact is the README; the spec is the *source of truth the README must match*. Editing the spec here would either restate existing normative text or encode documentation wording as a requirement, both of which add ceremony without changing behavior.

  If the spec phase disagrees, the only defensible minimal delta would be a docs-consistency requirement (user-facing documentation SHALL describe the fail-closed posture). Recommend **against** it: it is not executable, and this repo's specs are behavior contracts.

  **Skip the spec phase unless the parent explicitly overrides this.**

## Approach

Single docs slice, two files, one commit (per §13).

1. **`README.md` — hardening section rewrite.** Keep the `### Hardening for sensitive hosts` heading unchanged to preserve the existing anchor and the ES mirror's heading parity. Keep the `openssl rand -hex 16` example (`export SOFER_MCP_APPROVAL_PHRASE=…`), then add the corrected mandatory phrasing, the read-once/restart semantics, the per-agent pointer with the plaintext caveat, the Windows launcher note, and the `sofer_auth_status` verification step. Fold in only facts already in the spec/code/docstrings — no invented env names, paths, or flags (AGENTS.md §1: values come from code/spec, not from prose invention).
2. **`README.md` — Security model bullet fix.** "…and — when configured — an approval phrase compared with `hmac.compare_digest`" → state that the phrase gate is always enforced and that an unconfigured phrase refuses the call with `PUBLISH_APPROVAL_NOT_CONFIGURED`.
3. **`README_ES.md` — mirror both edits** in the same commit, neutral Spanish prose, technical tokens (env var names, error codes, flags, `sofer_auth_status`, `approval_configured`, `hmac.compare_digest`) left in English. Heading text stays `### Endurecimiento para hosts sensibles`.
4. **Self-check before handing to verify**: grep both files for `weaker posture` / `postura más débil`, `when configured` / `cuando está configurada`, and "acknowledgment booleans" / "booleanos de reconocimiento" — zero matches may remain that imply the booleans suffice. Also confirm heading parity and section order between the two files (§13).

No before/after behavior diff exists, so there is no RED/GREEN test cycle: the change is prose. The executable proof that the *documented* behavior is real is the existing test suite (`tests/test_mcp_server.py`, `tests/test_mcp_process.py`), which is expected to pass **unchanged**.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `README.md` | Modified | `### Hardening for sensitive hosts` (L661-673) rewritten; `### Security model` fail-closed bullet (L643-647) corrected; `### Hardening for sensitive hosts` heading preserved |
| `README_ES.md` | Modified | Same two edits mirrored in the same commit (AGENTS.md §13); heading `### Endurecimiento para hosts sensibles` preserved |
| `openspec/specs/mcp-server/spec.md` | Unchanged | Already normative for fail-closed publish (MSP-R05, 10.8) |
| `openspec/specs/mcp-registration/spec.md` | Unchanged | Source of the per-agent env behavior being referenced |
| `src/sofer/**` | Unchanged | Code is already correct; read-only reference |
| `tests/**` | Unchanged | Existing tests already pin fail-closed (`test_mcp_server.py:758`, `test_mcp_process.py:621`) |
| `docs/cli-vs-mcp.md`, `TRACE.md` | Unchanged | Already accurate |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `README_ES.md` drifts or lands in a later commit | Med | Same commit (§13, mandated); equal heading count/order check as a step in the plan; §13 is also a PR-template checklist item |
| Over-claiming in the rewrite (e.g. stating the phrase lives only in env, or that the CLI needs it) | Med | Every claim traced to `mcp_server.py:1060-1065/1148-1155/2623-2630`, `spec.md:137/424`, `spec.md (mcp-registration):19`; `docs/cli-vs-mcp.md` already states CLI never needs it — do not contradict it |
| Per-agent guidance drifts from the `mcp add` reality (opencode receives no env) | Med | Keep the hardening section short and defer detail to the existing MCP-registration bullets (L601-621) rather than duplicating them (AGENTS.md §4 — no duplicated logic) |
| Windows "restart the host" guidance is misread as "restart the shell" | Low | Explicit wording: the variable must be in the **launcher's** environment and the host fully restarted |
| Docs change collides with or pre-empts #144/#145/#151 | Low | Strictly no new claims beyond current code/spec; those issues' scope untouched and not referenced as pending work |
| Reviewing a "small" docs change under-cecks the mirrored file | Low | Diff must show matching changes in both READMEs; reviewers can compare section-by-section |

## Rollback Plan

`git revert` the single docs commit (or restore both files from the previous revision). Docs-only, no migration, no state, no compatibility surface. The spec and code are untouched, so no spec or behavior rollback exists or is needed.

## Dependencies

- None. No new dependencies, no tooling, no config changes.
- Read-only references: `src/sofer/mcp_server.py`, `openspec/specs/mcp-server/spec.md`, `openspec/specs/mcp-registration/spec.md`, `docs/cli-vs-mcp.md`.

## Success Criteria

- [ ] `README.md` describes the fail-closed posture: the phrase is **mandatory** for any HF publish; an unconfigured server refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED`.
- [ ] `README.md` states the phrase is read once at process start and requires a host restart to change, and shows how to verify via `sofer_auth_status` → `approval_configured` (+ `requires_approval_phrase` always true).
- [ ] `README.md` documents per-agent configuration (codex `env_vars`, gemini `env`, opencode launcher env / `environment` literal with plaintext caveat) and the Windows launcher-environment + full-restart note.
- [ ] `README.md` contains **no** surviving text implying the acknowledgment booleans are sufficient on their own, or that the phrase is optional ("when configured" removed).
- [ ] `README_ES.md` mirrors both edits in the **same commit**, with prose in Spanish and technical tokens in English; heading parity and section order preserved.
- [ ] Zero changes to `src/`, `tests/`, `docs/`, `TRACE.md`, or `openspec/specs/`.
- [ ] `uv run pytest tests/ -q` passes unchanged; `uv run mypy src/` unaffected; `git diff --check` clean.
- [ ] No leftover occurrences of "weaker posture" / "postura más débil" in either README.

## Delivery

Pre-flight human gate: **no commit, branch, PR, or release is proposed by this artifact.** Delivery shape (single PR vs. chained vs. exception) is the human's decision at the delivery gate; this change is small (two docs files, roughly one section each) and well inside the 400-changed-line review budget, so no chain strategy is required or suggested.

## Proposal question round

Assumptions needing user review before spec/design/apply (question round offered; the user may answer, correct, or request a second round):

1. **Always-on phrasing.** Should the hardening section read as "the phrase is mandatory and publish is *disabled* without it" (current code, current spec), or should it hedge with "unless the host explicitly runs a trusted single-user stdio setup"? The second reading is the posture the old sentence implied — if any such supported mode exists outside the code path we read, the docs must say so; if not, the doc states the hard refusal. **Assumption taken: no such mode exists; the refusal is unconditional.**
2. **Windows restart scope.** Is "the variable must be in the launcher's environment and the host must be fully restarted" precise enough for the support/agent workflows seen in `TRACE.md`, or is a concrete restart sequence (per host: codex / gemini / opencode) expected in the README? **Assumption taken: short launcher-environment wording plus a restart requirement, no per-host restart recipes.**
3. **Open `mcp add` vs. manual env.** Should the hardening section point at `sofer mcp add` (which persists env *names* for codex/gemini and nothing for opencode) as the recommended setup path, or stay manual (`export` + launcher config)? **Assumption taken: recommend `mcp add` for codex/gemini and describe the opencode literal form with its plaintext caveat.**
4. **Section placement/size.** Is expanding `### Hardening for sensitive hosts` to roughly 15-25 lines acceptable in the README, or should the depth live in `docs/` with a one-paragraph summary plus link? **Assumption taken: keep it in the README, bounded, and defer detail to the existing MCP-registration bullets.**
5. **Scope boundary on the adjacent bullet.** Fixing the `### Security model` "when configured" wording is a second, in-adjacent-location edit not named in the issue. Include it (recommended — same defect, same acceptance criterion) or leave it to a follow-up? **Assumption taken: include it.**
