# Apply Progress — 2026-09-11-fix-docs-fail-closed-publish

**Change**: `2026-09-11-fix-docs-fail-closed-publish` (fixes GitHub #148)
**Phase**: apply (implementation)
**Status**: partial — Phases 0–3 complete and verified; Phase 4 (commit/push/PR) withheld by explicit parent instruction; Phase 5 parent-owned
**Strict TDD**: inactive (`openspec/config.yaml` `strict_tdd: false`) — prose-only change, no RED/GREEN cycle; the existing fail-closed tests are the executable proof and ran unmodified.

## Status consumed (and discrepancy recorded)

- Consumed the parent-supplied native status (schema `gentle-ai.sdd-status@2`, `artifactStore: openspec`, `planningHome.mode: repo-local`, `changeRoot: openspec/changes/2026-09-11-fix-docs-fail-closed-publish`).
- `actionContext`: `mode: repo-local`, `workspaceRoot: C:\Users\elaze\Desktop\sofer`, `allowedEditRoots: [C:\Users\elaze\Desktop\sofer]`, `warnings: []` — no unsafe edit roots; every write stayed under the repo root, and only `README.md` / `README_ES.md` were modified.
- **Discrepancy (recorded, not silently ignored).** A full-engine serialization also surfaced `applyState: "blocked"` with `blockedReasons: ["domain specs are missing or partial."]` and `artifacts.specs: "missing"`. That signal is a false positive of the spec-delta heuristic: this change deliberately carries **no requirement delta** — `openspec/changes/2026-09-11-fix-docs-fail-closed-publish/specs/no-delta.md` (§3) records the approved verdict "No delta", and `proposal.md` / `design.md` D6 both state no spec delta is required because MSP-R05 (`openspec/specs/mcp-server/spec.md:137`), 10.3 (`:390`), 10.8 (`:424`) and MCP-REG-01 (`mcp-registration/spec.md:19`) already mandate the behavior the README must describe. All three required apply inputs (tasks, design, spec-verdict) are present, and the parent prompt supplied a reduced authoritative status without `applyState` plus a resolved delivery path. Implementation therefore proceeded; the stale-engine signal is logged here as a risk for verify.
- Review Workload Gate: `Decision needed before apply: No`, `Chained PRs recommended: No`, `Chain strategy: pending`, `400-line budget risk: Low` → single PR, no chain, no `size:exception` needed.

## Completed tasks (25 of 28 implementation rows; checkboxes updated in `tasks.md`)

- **Phase 0 (4/4)**: `0.1` branch `docs/fix-readme-fail-closed-publish` (base `dev`, 0 commits ahead at start, no work on `main`/`dev`); `0.2` baseline hard-zero greps = exactly **6** matches (`README.md:646,672,673`; `README_ES.md:681,708,709`); `0.3` baseline suite `1468 passed, 6 skipped` (54.64s); `0.4` read-only ground truth confirmed in `src/sofer/mcp_server.py` (`:217`, `:1063`, `:1148-1155`, `:1166`, `:1627-1670`, `:2637-2648`), `openspec/specs/mcp-server/spec.md` (`:137`, `:390`, `:424`), `openspec/specs/mcp-registration/spec.md:19`, and the registration bullets `README.md:585-621` / `README_ES.md:618-652`.
- **Phase 1 (6/6)**: `1.1` hardening body rewritten per design §6.1; `1.2` W1–W10 all present, N1/N2 phrasing deleted in full; `1.3` referent is the two `acknowledge_*` flags (no "acknowledgment booleans" bigram); `1.4` link targets the existing `#register-sofer-mcp-with-ai-agents-opencode-codex-gemini` heading, no new heading; `1.5` `### Security model` bullet now always-in-force incl. `PUBLISH_APPROVAL_NOT_CONFIGURED`; `1.6` structural self-check (see deviations).
- **Phase 2 (6/6)**: `2.1` ES hardening body mirrored per design §6.3; `2.2` ES `### Modelo de seguridad` clause mirrored (exact code `PUBLISH_APPROVAL_NOT_CONFIGURED`, token chain untouched); `2.3` language split enforced (technical tokens stay English in ES); `2.4` ES link targets `#registrar-sofer-mcp-con-agentes-de-ia-opencode-codex-gemini`; `2.5` ES structural self-check; `2.6` EN↔ES heading parity preserved (17 `###` each, 84 `#`-lines each, same order).
- **Phase 3 (9/9)**: all acceptance checks green (evidence below).

## Files changed

| File | Region | Change |
|---|---|---|
| `README.md` | `### Hardening for sensitive hosts` body (heading `:664`, body `:666-695`) | defect sentence pair + "SHOULD for sensitive hosts" framing replaced with the W1–W10 block; `openssl rand -hex 16` fence retained |
| `README.md` | `### Security model` bullet (`:648-651`) | `and — when configured — an approval phrase…` → always-in-force + `PUBLISH_APPROVAL_NOT_CONFIGURED` + publish disabled |
| `README_ES.md` | `### Endurecimiento para hosts sensibles` body (heading `:699`, body `:701-730`) | ES mirror of the above |
| `README_ES.md` | `### Modelo de seguridad` bullet (`:680-683`) | ES mirror of the security-model clause; token-resolution chain untouched |
| `openspec/changes/2026-09-11-fix-docs-fail-closed-publish/tasks.md` | checkboxes | 25 implementation rows `- [ ]` → `- [x]`; parent rows untouched |
| `openspec/changes/2026-09-11-fix-docs-fail-closed-publish/apply-progress.md` | new | this file |

Tracked diff: **2 files, 56 insertions, 14 deletions (70 changed lines)** — `git diff --stat`; ≈18 % of the 400-line budget.

## Verification evidence (Phase 3)

```
3.1 hard-zero EN  grep -n "weaker posture\|when configured\|acknowledgment booleans" README.md      → (no output, exit 1)
3.1 hard-zero ES  grep -n "configurada — una frase\|postura más débil\|booleanos de reconocimiento" README_ES.md → (no output, exit 1)
    → 6 → 0 versus the task 0.2 baseline
3.3 presence      PUBLISH_APPROVAL_NOT_CONFIGURED: README.md=3, README_ES.md=3
                  approval_configured: README.md:691, README_ES.md:726
                  SOFER_MCP_APPROVAL_PHRASE: README.md:320,619,674,679; README_ES.md:332,652,709,714
                  "once at process start": README.md:678 ; "una sola vez al iniciar el proceso": README_ES.md:713
3.2 ES caveat     "cuando está" still only at README_ES.md:332,363,400 (benign) — pattern not widened
3.4 N3 guard      no "sofer publish" occurrence inside the two changed regions (new text says sofer_publish_confirm only)
3.5 scope guard   git status --short → " M README.md", " M README_ES.md", "?? openspec/changes/2026-09-11-fix-docs-fail-closed-publish/"
3.6 suite         uv run pytest tests/ -q → 1468 passed, 6 skipped, 13 warnings in 54.28s (baseline 1468/6 unchanged)
                  pins unmodified: TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed
                  + TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch → 2 passed
3.7 tooling       uv run ruff check src/ tests/ → "All checks passed!"
                  uv run mypy src/ → "Success: no issues found in 32 source files"
3.8 whitespace    git diff --check → clean (exit 0)
3.9 diff audit    git diff -U0 hunks: 3 in README.md (646, 664, 672), 3 in README_ES.md (680, 699, 708) — exactly the four intended regions, nothing else
```

## Deviations from design

1. **Two lines exceed the 80-column rule — both are unbreakable inline Markdown links** (design §6.1/§6.3 themselves render the link on one line): `README.md:682` = 95 chars (`[Register sofer-mcp with AI agents](#register-sofer-mcp-with-ai-agents-opencode-codex-gemini)):`) and `README_ES.md:717` = 108 chars (ES equivalent). Every other line in both changed regions is ≤ 80 chars (measured in characters, not bytes). Alternatives (reference-style link, shortened link text, splitting the link text across lines) were rejected: they either deviate further from the design's mandated link text or introduce a Markdown construct the README does not use. Pre-existing precedent: `README.md` had 107 lines > 80 and `README_ES.md` 134 before this change.
2. **Line numbers shifted** (+2/+17) in both files after the edits; the design/tasks line references describe the pre-edit tree. Parity and order are preserved: EN `### Security model` `:632` → `### Hardening for sensitive hosts` `:664`; ES `### Modelo de seguridad` `:665` → `### Endurecimiento para hosts sensibles` `:699` (both offsets +2).
3. **ES re-wrap:** task 2.2 targeted `L680-681`; the ES adjacent clause now spans `:680-683` because the replacement sentence is longer than the deleted fragment. The preceding line `:680` (`para las configuraciones marcadas como [meta] confidential`) was re-wrapped over `:680-682` to keep the paragraph inside the width — content unchanged, token-resolution chain from `:684` onward byte-identical.
4. No other deviation: no new env var/flag/error code, no new heading, no TOC edit, no new test, no claim from N3–N7.

## Remaining tasks (exact unchecked lines)

```text
- [ ] 4.1 Stage and commit `README.md` + `README_ES.md` **together in the same commit** (AGENTS.md §13, design C2) with a message naming issue #148 and the docs-only scope. Pre-commit ruff + mypy run automatically — do not use `--no-verify`. <!-- sdd-owner: implementation -->
- [ ] 4.2 Push the dedicated branch and open a PR into `dev` (never `main`/`dev` directly). Fill every section of `.github/PULL_REQUEST_TEMPLATE.md` with **actual command output** from Phase 3 (hard-zero greps, presence greps, `git status --short`, pytest tail, ruff/mypy, `git diff --check`) and list this change's SDD artifact paths in the mandatory *SDD artifacts* section (AGENTS.md §11). <!-- sdd-owner: implementation -->
- [ ] 4.3 Confirm the PR diff shows matching changes in both READMEs region-by-region, and that no `src/`/`tests/`/`docs/`/`TRACE.md`/scope-guard file appears in it. Do not merge without human approval at the delivery gate. <!-- sdd-owner: implementation -->
```

Phase 4 was explicitly withheld by the parent prompt ("No commits, no push, no branch changes — the parent versions at the end"), so 4.1–4.3 stay unchecked and are handed to the parent. `sdd-apply` does not commit, push, or open PRs on its own authority.

Deferred parent lifecycle rows (untouched, byte-identical):

```text
- [ ] 5.1 Run the bounded post-apply review over the PR diff, using design §4.1/§4.2 (W/N tables) as the review checklist: every W-claim present in both languages, zero N-claims, no invented token, ES mirror complete and same-commit. <!-- sdd-owner: parent -->
- [ ] 5.2 Confirm the lifecycle gate: human approval of the PR before merge, `dev`-only target, and no release/tag step for this docs-only change (proposal *Delivery*, design §9). <!-- sdd-owner: parent -->
```

## Workload / PR boundary

Single PR, `docs/fix-readme-fail-closed-publish` → `dev`, one commit containing both READMEs (same-commit EN/ES mirror, AGENTS.md §13). 70 changed lines vs the 400-line budget → no chaining, no `size:exception`.

## Risks handed to verify / parent

1. The stale-engine `applyState: blocked` ("domain specs are missing or partial") must be reconciled with `specs/no-delta.md` so the change is not treated as spec-blocked at verify/archive.
2. The two >80-char link lines (deviation 1) are the only structural self-check caveat.
3. Phase 4 artifacts (commit message, PR body, PR diff confirmation) do not exist yet by design of the parent hand-off; verify must consume the *staged diff*, not a commit.
