# Tasks: Fix README fail-closed publish documentation

**Change**: `2026-09-11-fix-docs-fail-closed-publish` (Fixes GitHub #148)
**Spec delta**: none (`specs/no-delta.md`) — docs-only, no code, no config, no new test.
**Design source of truth**: `design.md` §6 (edit spec), §7 (acceptance), §4.1–4.2 (W1–W10 / N1–N7 wording contract), §8 (file map).
**This file operationalizes that design; it does not re-invent the wording.**

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~70 (design §8: ~13→~30 + ±4 per file × 2 files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (`docs/fix-readme-fail-closed-publish` → `dev`), one commit containing both READMEs |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

Single PR confirmed: ~70 lines is ~18% of the 400-line budget, so `ask-on-risk` raises no delivery question and no size exception is requested. Chain strategy stays `pending` because chaining is not required.

---

## Scope guards (apply to every task; no checkbox implies permission)

**Only these two files may change:** `README.md`, `README_ES.md`.

**Explicitly forbidden for this change:**
- `TRACE.md`, `docs/**` (incl. the design's §5 note that `docs/cli-vs-mcp.md` does not exist — do **not** create it), `CONTRIBUTING.md`, `scratch/**`, `.gitignore`
- `src/**`, `tests/**`, `openspec/specs/**`, `openspec/config.yaml`, `pyproject.toml` — read-only (`no-delta.md` §4, design C1)
- Any new env var name, flag, path, error code, or **new test** (design C6, D6)
- New headings, TOC edits, reflowing neighbouring paragraphs, or renaming the two section headings (design C5, D7)
- Committing to `main` or `dev` directly; merging without a PR
- Claims from `design.md` §4.2 N1–N7, and any wording that pre-empts issues #144/#145/#151

## Phase 0 — Preflight: branch, baseline, read-only confirmation

- [x] 0.1 Create a dedicated branch off `dev` (`git switch dev && git pull && git switch -c docs/fix-readme-fail-closed-publish`); never commit to `main`/`dev`. <!-- sdd-owner: implementation -->
- [x] 0.2 Record the pre-change baseline evidence: run the two hard-zero greps of design §7.1 — `grep -n "weaker posture\|when configured\|acknowledgment booleans" README.md` and `grep -n "configurada — una frase\|postura más débil\|booleanos de reconocimiento" README_ES.md` — and confirm exactly **6** matches (`README.md:646,672,673`; `README_ES.md:681,708,709`). <!-- sdd-owner: implementation -->
- [x] 0.3 Record the pre-change test baseline: `uv run pytest tests/ -q` and capture the literal tail (expected 1468 passed / 6 skipped). This number is the comparison target for task 3.6. <!-- sdd-owner: implementation -->
- [x] 0.4 Confirm read-only ground truth before writing (no edits): `src/sofer/mcp_server.py` (`:217`, `:1063`, `:1148-1155`, `:1166`, `:1627-1670`, `:2637-2648`), `openspec/specs/mcp-server/spec.md` (`:137`, `:390`, `:424`), `openspec/specs/mcp-registration/spec.md:19`, and the existing registration bullets `README.md:585-621` / `README_ES.md:618-652`. Every W-claim must come from here. <!-- sdd-owner: implementation -->

## Phase 1 — `README.md`: primary + adjacent region edits

- [x] 1.1 Edit the body of `### Hardening for sensitive hosts` (`README.md:662` heading; body `L663-673`): delete the conditional framing (`L664-665` "Hosts handling sensitive data SHOULD configure…") and the defect sentence pair (`L672-673` "When no phrase is configured, only the two acknowledgment booleans gate the HF publish — a weaker posture suited to trusted single-user stdio setups."), replacing them with design §6.1's block. Preserve the heading verbatim and keep the existing `export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"` / `sofer-mcp` Bash fence (W10, C5). <!-- sdd-owner: implementation -->
- [x] 1.2 Verify the replacement body carries every mandatory claim W1, W2, W3, W5, W6, W7, W8, W9 (and W4 at `L663-673` scope) from design §4.1, and that the delete-side abandons N1 and N2 phrasing in full. Do not add any N3–N7 claim. <!-- sdd-owner: implementation -->
- [x] 1.3 Confirm the negative referent naming from design D2 is applied: the text says the two `acknowledge_*` flags (not "acknowledgment booleans"), so the §7.1 EN grep stays hard-zero without human judgement. `acknowledge_risk` / `acknowledge_confidential` literal forms remain where they already exist. <!-- sdd-owner: implementation -->
- [x] 1.4 Confirm the intra-page link added in the hardening section targets the existing heading `### Register sofer-mcp with AI agents (opencode, codex, gemini)` (`README.md:585`) using the `#register-sofer-mcp-with-ai-agents-opencode-codex-gemini` slug; no new heading is created by the link. <!-- sdd-owner: implementation -->
- [x] 1.5 Apply the adjacent fix in `### Security model` (`README.md:632`) — the "Fail-closed publish authorization" bullet: replace the clause at `L646` `and — when configured — an approval phrase compared with \`hmac.compare_digest\`` with design §6.2's always-in-force wording, including the `PUBLISH_APPROVAL_NOT_CONFIGURED` refusal and the disabled-publish statement. Leave the rest of the bullet (the `HF_TOKEN` → `HF_TOKEN_PATH` resolution chain) byte-identical (D5, D7). <!-- sdd-owner: implementation -->
- [x] 1.6 Structural self-check on `README.md`: body wraps at ≤ 80 columns matching neighbours; blank-line separation and list indentation preserved; exactly one Bash fence in the region (no new fences, tables, or images); heading count and order unchanged (`grep -c '^### ' README.md` still `17`). <!-- sdd-owner: implementation -->

## Phase 2 — `README_ES.md` mirror (same commit as Phase 1)

- [x] 2.1 Mirror task 1.1 into the body of `### Endurecimiento para hosts sensibles` (`README_ES.md:697` heading; body `L699-710`): sentence-by-sentence per design §6.3, neutral Spanish prose. Heading text stays `### Endurecimiento para hosts sensibles`; the `openssl rand -hex 16` fence is retained. <!-- sdd-owner: implementation -->
- [x] 2.2 Mirror task 1.5 into `### Modelo de seguridad` (`README_ES.md:665`): replace `L680-681`'s `y — cuando está configurada — una frase de aprobación comparada con \`hmac.compare_digest\`` with design §6.3's wording (`… y siempre requiere una frase de aprobación del servidor … PUBLISH_APPROVAL_NOT_CONFIGURED …` — always the exact code `PUBLISH_APPROVAL_NOT_CONFIGURED`), re-wrapping the paragraph to the surrounding width while keeping the token-resolution chain untouched. <!-- sdd-owner: implementation -->
- [x] 2.3 Enforce the language split of design §4.4: all technical tokens stay English in the ES file (`SOFER_MCP_APPROVAL_PHRASE`, `HF_TOKEN`, `env_vars`, `env`, `environment`, `build_server(root, approval_phrase=...)`, `sofer_publish_confirm`, `sofer_auth_status(config)`, `approval_configured`, `requires_approval_phrase`, `acknowledge_*`, `PUBLISH_APPROVAL_NOT_CONFIGURED`, `PUBLISH_APPROVAL_REQUIRED`, `hmac.compare_digest`, `sofer-mcp`, `sofer mcp add`, code fences); only surrounding prose is translated. <!-- sdd-owner: implementation -->
- [x] 2.4 Confirm the ES intra-page link targets `### Registrar sofer-mcp con agentes de IA (opencode, codex, gemini)` (`README_ES.md:618`) with slug `#registrar-sofer-mcp-con-agentes-de-ia-opencode-codex-gemini`, and that the pre-existing Configuration-section sentence ("Los documentos técnicos de referencia … están en inglés.") is untouched. <!-- sdd-owner: implementation -->
- [x] 2.5 Structural self-check on `README_ES.md`: ≤ 80-column wrap, preserved blank lines/indentation, single Bash fence retained, `grep -c '^### ' README_ES.md` still `17`, and the two changed regions are the same two regions as in `README.md` (§13, design §6.4). <!-- sdd-owner: implementation -->
- [x] 2.6 Verify EN↔ES heading and section parity (AGENTS.md §13): same count per heading level and same order; the pair `### Security model → ### Hardening for sensitive hosts` (EN `L632`→`L662`) mirrors `### Modelo de seguridad → ### Endurecimiento para hosts sensibles` (ES `L665`→`L697`); no heading text changed → no anchor churn. <!-- sdd-owner: implementation -->

## Phase 3 — Acceptance verification (design §7)

- [x] 3.1 Hard-zero greps (must print **nothing**): `grep -n "weaker posture\|when configured\|acknowledgment booleans" README.md`; `grep -n "configurada — una frase\|postura más débil\|booleanos de reconocimiento" README_ES.md`. Must go 6 → 0 against the task 0.2 baseline. <!-- sdd-owner: implementation -->
- [x] 3.2 Respect the ES soft-wrap caveat (design §7.1): do **not** widen the ES pattern to `cuando está` — that form occurs benignly at `README_ES.md:332, 363, 400` and would produce false failures. The line-local pattern `configurada — una frase` is the accepted one. <!-- sdd-owner: implementation -->
- [x] 3.3 Positive-presence greps, each ≥1 hit in **both** files: `grep -c "PUBLISH_APPROVAL_NOT_CONFIGURED" README.md README_ES.md`; `grep -n "approval_configured" README.md README_ES.md`; `grep -n "SOFER_MCP_APPROVAL_PHRASE" README.md README_ES.md`; plus `grep -n "once at process start" README.md` and `grep -n "una sola vez al iniciar el proceso" README_ES.md`. <!-- sdd-owner: implementation -->
- [x] 3.4 Anti-regression check N3 (no CLI over-claim): every `SOFER_MCP_APPROVAL_PHRASE` occurrence in `README.md` / `README_ES.md` sits inside the `## AI and MCP server` block — never inside `## Command reference` or the `sofer publish` examples. Pre-existing hits at `README.md:320, 619` (ES `:332, 652`) plus the retained fence hit at `README.md:668` (ES `:704`) are expected. <!-- sdd-owner: implementation -->
- [x] 3.5 Scope guard C1: `git status --short` lists exactly `README.md` and `README_ES.md` (plus the untracked change directory if the SDD files are new). Zero changes under `src/`, `tests/`, `docs/`, `TRACE.md`, `scratch/`, `.gitignore`, `openspec/specs/`. <!-- sdd-owner: implementation -->
- [x] 3.6 Suite unchanged: `uv run pytest tests/ -q` → green and numerically equal to the task 0.3 baseline (1468 passed / 6 skipped expected). The fail-closed pins `tests/test_mcp_server.py::test_no_phrase_configured_refuses_fail_closed` (assert at `:783`, docstring at `:757-758`) and `tests/test_mcp_process.py::TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch` (approval-gate comment/assert at `:620-621`) must pass **unmodified** — they are the executable proof the corrected prose is true. No test file may be edited to accommodate wording (C8, D6). <!-- sdd-owner: implementation -->
- [x] 3.7 Tooling no-op: `uv run ruff check src/ tests/` and `uv run mypy src/` both clean. Because the change is docs-only, a non-clean result means something outside the two READMEs was touched — investigate instead of "fixing" it (design §7.4). <!-- sdd-owner: implementation -->
- [x] 3.8 Whitespace: `git diff --check` clean. <!-- sdd-owner: implementation -->
- [x] 3.9 Diff audit against design §8: `git diff --stat` shows 2 files; the four expected regions (`README.md` hardening body + security-model clause; `README_ES.md` hardening body + security-model clause) and only those; total changed lines ≈ 70, well under the 400-line budget. Anything else in the diff is a scope violation. <!-- sdd-owner: implementation -->

## Phase 4 — Delivery (one commit, both files, PR only)

- [x] 4.1 Stage and commit `README.md` + `README_ES.md` **together in the same commit** (AGENTS.md §13, design C2) with a message naming issue #148 and the docs-only scope. Pre-commit ruff + mypy run automatically — do not use `--no-verify`. <!-- sdd-owner: implementation --> (commit `1ad9837` on `docs/fix-readme-fail-closed-publish`)
- [x] 4.2 Push the dedicated branch and open a PR into `dev` (never `main`/`dev` directly). Fill every section of `.github/PULL_REQUEST_TEMPLATE.md` with **actual command output** from Phase 3 (hard-zero greps, presence greps, `git status --short`, pytest tail, ruff/mypy, `git diff --check`) and list this change's SDD artifact paths in the mandatory *SDD artifacts* section (AGENTS.md §11). <!-- sdd-owner: implementation --> (PR #156)
- [x] 4.3 Confirm the PR diff shows matching changes in both READMEs region-by-region, and that no `src/`/`tests/`/`docs/`/`TRACE.md`/scope-guard file appears in it. Do not merge without human approval at the delivery gate. <!-- sdd-owner: implementation --> (PR #156 files: README.md, README_ES.md, change artifacts only)

## Phase 5 — Bounded review and lifecycle gates (parent-owned)

- [x] 5.1 Run the bounded post-apply review over the PR diff, using design §4.1/§4.2 (W/N tables) as the review checklist: every W-claim present in both languages, zero N-claims, no invented token, ES mirror complete and same-commit. <!-- sdd-owner: parent --> (verify-report 8/8; W1-W10 traced, N1-N7 absent)
- [ ] 5.2 Confirm the lifecycle gate: human approval of the PR before merge, `dev`-only target, and no release/tag step for this docs-only change (proposal *Delivery*, design §9). <!-- sdd-owner: parent --> (awaiting human approval of PR #156)

---

## Advisories

1. **Do not create `docs/cli-vs-mcp.md`.** The proposal cites it as already accurate, but design §5 verified it does not exist (the live claim rests on `mcp_server.py`, `cli.py`, and `openspec/specs/mcp-server/spec.md`). A later phase must not "restore" it.
2. **Grep strings are the acceptance contract, so naming matters.** If the corrected text reintroduces the literal bigram "acknowledgment booleans" even in negation, task 3.1 degrades to human judgement. Use the `acknowledge_*` referent (design D2).
3. **Size trimming rule:** if the hardening section must shrink, the binding claims are {W1, W2, W5, W7, W8}; drop prose, never a claim (design §10).
4. **Baseline staleness:** `openspec/config.yaml` still records a 1029-test count; the operative baseline is the task 0.3 measurement, which is expected to match the session-supplied 1468 passed / 6 skipped. Compare like-for-like and report the actual numbers in the PR.
5. **Docs-conformance test is a separate follow-up**, recorded in `no-delta.md` §5 — do not add one here.
