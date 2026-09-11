# Tasks: Document the Windows approval-phrase path (PowerShell + cmd)

**Change**: `2026-09-11-fix-docs-approval-phrase-windows` (Fixes GitHub #151)
**Spec delta**: none (`specs/no-delta.md`) — docs-only, no code, no config, no new test, no spec file.
**Design source of truth**: `design.md` §3 D1–D8 (decisions), §4.1–4.2 (W1–W7 / N1–N7 wording contract), §4.3–4.4 (structure + language split), §6.1/§6.2 (exact insert blocks + anchors), §6.3 (parity), §7.1–7.5 (acceptance greps + mandatory execution gate), §8 (file map).
**This file operationalizes that design; it does not re-invent the wording.**

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~40 (design §8: +20 `README.md`, +20 `README_ES.md`, 0 deletions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (`docs/fix-151-approval-phrase-windows` → `dev`), one commit containing both READMEs |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

Single PR confirmed: ~40 lines is ~10% of the 400-line review budget (design C7/§8), so `ask-on-risk` raises no delivery question and no `size:exception` is requested or implied. Chain strategy stays `pending` because chaining is not required. Zero deletions is part of the acceptance contract (§7.3).

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | EN block + ES mirror + acceptance evidence + execution gate (Phases 1–4) | PR 1 | One commit, two files; all verification inside this unit |
| 2 | Commit + PR + bounded review/lifecycle gate (Phases 5–6) | PR 1 | Parent-owned delivery and gate |

---

## Scope guards (apply to every task; no checkbox implies permission)

**Only these two files may change:** `README.md`, `README_ES.md` (+ this change's own SDD artifacts under `openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/`).

**Explicitly forbidden for this change:**
- `TRACE.md`, `SOFER_TRACE.md`, `docs/**` (in particular `docs/cli-vs-mcp.md` — design §5/proposal verify it does **not** exist; do **not** create it), `CONTRIBUTING.md`, `scratch/**`, `.gitignore`
- `src/**`, `tests/**`, `openspec/specs/**`, `openspec/config.yaml`, `pyproject.toml` — read-only (design C1, `no-delta.md` §4)
- Any new env var name, flag, path, error code, constant, generation path, or new test (design D8, N5)
- New headings, TOC edits, tables, images, reflowing neighbouring paragraphs, or renaming the two hardening headings (design C9, §4.3)
- Any edit to a merged #148 baseline sentence (fail-closed preamble, read-once paragraph, per-agent env paragraph, `**Windows:**` sentence, `**Verify:**` paragraph) — design C4
- Claims from design §4.2 N1–N7; wording that pre-empts open issues #144/#145
- Committing to `main` or `dev` directly; merging without a PR; any tag or release step

## Phase 0 — Preflight: branch, baseline evidence, read-only confirmation

- [x] 0.1 Confirm the dedicated branch is checked out and based on `dev`: `git rev-parse --abbrev-ref HEAD` must print `docs/fix-151-approval-phrase-windows`; `git merge-base --is-ancestor dev HEAD` must succeed. If the branch is missing, create it from `dev` (`git switch dev && git pull && git switch -c docs/fix-151-approval-phrase-windows`). Never commit to `main`/`dev`. <!-- sdd-owner: implementation -->
- [x] 0.2 Record the pre-change hard-zero baseline (design §7.1) — all four must print **nothing** today: `grep -n "RNGCryptoServiceProvider" README.md README_ES.md`; `grep -n "ToHexString" README.md README_ES.md`; `grep -n "weaker posture" README.md`; `grep -n "postura más débil" README_ES.md`. Capture the literal (empty) output as the comparison target for task 3.1. <!-- sdd-owner: implementation -->
- [x] 0.3 Record the pre-change structural counters (comparison targets for tasks 1.5, 2.4, 3.5): `grep -c '^```' README.md README_ES.md` (fence count per file, expect N and N) and `grep -c '^#' README.md README_ES.md` plus `grep -c '^## ' README.md README_ES.md` and `grep -c '^### ' README.md README_ES.md` (per-level heading counts must be equal across files and must not change). <!-- sdd-owner: implementation -->
- [x] 0.4 Record the pre-change #148 anti-regression counts (design §7.3, comparison target for task 3.3): `grep -c "Do not rely on the two \`acknowledge_\*\` flags alone" README.md`; `grep -c "once at process start" README.md`; `grep -c "the variable must be in the launcher's environment" README.md`; `grep -c "approval_configured" README.md`; and the ES equivalents `grep -c "No confíes solo en los dos flags \`acknowledge_\*\`" README_ES.md`; `grep -c "una sola vez al iniciar el proceso" README_ES.md`; `grep -c "la variable debe estar en el entorno del lanzador" README_ES.md`; `grep -c "approval_configured" README_ES.md`. Each #148 anchor must count exactly `1` (single occurrence) before the edit. <!-- sdd-owner: implementation -->
- [x] 0.5 Record the pre-change test baseline: `uv run pytest tests/ -q` and capture the literal tail (expected **1468 passed / 6 skipped**). This is the comparison target for task 4.1 and must stay numerically identical. <!-- sdd-owner: implementation -->
- [x] 0.6 Confirm read-only ground truth before writing anything (no edits): `src/sofer/mcp_server.py` (`:217`, `:1154-1155`, `:1660-1663`, `:2640-2648`), `openspec/specs/mcp-server/spec.md` (`:137`, `:390`, `:424`), `openspec/specs/mcp-registration/spec.md:19`. Every W-claim in design §4.1 must trace here (design §5) — no new repo fact may be invented. <!-- sdd-owner: implementation -->
- [x] 0.7 Confirm both insertion anchors are unique **before** editing (design §6.1/§6.2 require exactly one occurrence): `grep -c -F 'environment or an explicit `environment` literal (plaintext on disk).' README.md` must print `1` (file line 685) and `grep -c -F 'lanzador o un literal `environment` explícito (texto plano en disco).' README_ES.md` must print `1` (file line 720). A count other than 1 means the anchor is ambiguous — stop and re-derive placement from design D1 instead of guessing. <!-- sdd-owner: implementation -->

## Phase 1 — `README.md`: insertion into `### Hardening for sensitive hosts`

- [x] 1.1 Apply the §6.1 edit recipe: replace the anchor span `literal (plaintext on disk).\n\n**Windows:**` (README.md L685→L687) with `literal (plaintext on disk).\n\n` + the design §6.1 block + `\n\n**Windows:**`. The block is exactly +20 lines (2 intro + 1 blank + 8 fence + 1 blank + 8 prose), adds one `` ```powershell `` fence, and is a **pure insertion** — zero deletions. Do not modify the read-once paragraph, the per-agent env paragraph, the `**Windows:**` sentence, or the `**Verify:**` paragraph (design C4). <!-- sdd-owner: implementation -->
- [x] 1.2 Verify every mandatory claim from design §4.1 is present in the new EN text — W1 (32-hex phrase without `openssl`, same shape as `openssl rand -hex 16`), W2 (`$env:`/`set` are session-scoped), W3 (value must be in the environment that launches the MCP server, or `setx` + full host restart), W4 (`setx` facts incl. `HKCU\Environment`, newly created processes only, unencrypted, 1024-char cap), W5 (running server never re-reads), W6 (`sofer_auth_status` → `approval_configured` pointer), W7 (portable 5.1 + 7+). Add no claim beyond them. <!-- sdd-owner: implementation -->
- [x] 1.3 Verify zero forbidden claims from design §4.2 are introduced: no "reloads/picks up without restart" (N1), no "`setx` affects the current shell" (N2), no literal `RNGCryptoServiceProvider`/`ToHexString` (N3), no weak/optional phrasing or duplication of a #148 sentence (N4), no third generation path such as `python -c "secrets…"` (N5), no `HKLM`/other-user/registry-internals claims (N6), no behavior claim beyond the already-normative ones (N7). <!-- sdd-owner: implementation -->
- [x] 1.4 Verify the fence contract (design C5, D2, D5, §4.3): the `` ```powershell `` fence body is byte-verbatim as specified — the three comment lines (described as "the legacy RNG constructor" / "the static .NET 5+ hex helpers", **never** the literal deprecated names), `$bytes = New-Object byte[] 16`, `[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)`, `$env:SOFER_MCP_APPROVAL_PHRASE = -join ($bytes | ForEach-Object { $_.ToString("x2") })` — copied unwrapped onto single lines, not re-wrapped to ≤80 columns. The fence carries **no** `sofer-mcp` launch line (design D3). <!-- sdd-owner: implementation -->
- [x] 1.5 Structural self-check on `README.md`: prose wraps at ≤80 columns matching neighbours; blank-line separation preserved; exactly one new fence pair added (`grep -c '^```' README.md` == task 0.3 baseline + 2); heading counts unchanged (`grep -c '^#'`, `grep -c '^## '`, `grep -c '^### '` all equal to the task 0.3 baseline); no new heading, table, image, or TOC entry. <!-- sdd-owner: implementation -->

## Phase 2 — `README_ES.md`: mirror in the same commit

- [x] 2.1 Apply the §6.2 edit recipe in the **same working session** (never a later commit — AGENTS.md §13, design C2): replace the anchor span `texto plano en disco).\n\n**Windows:**` (README_ES.md L720→L722) with `texto plano en disco).\n\n` + the design §6.2 block + `\n\n**Windows:**`, exactly +20 lines and a pure insertion. Heading `### Endurecimiento para hosts sensibles` stays unchanged. <!-- sdd-owner: implementation -->
- [x] 2.2 Enforce the design §4.4 language split: the entire PowerShell fence (code comment lines included) is **byte-identical** to the EN fence; technical tokens stay English (`SOFER_MCP_APPROVAL_PHRASE`, `setx`, `$env:`, `set`, `openssl`, `RandomNumberGenerator`, `.NET`, `HKCU\Environment`, `sofer_auth_status`, `approval_configured`, `<value>`, `MCP`); only surrounding prose is translated. The diagnostics pointer uses the label `**Verificación**` and must not restate the Spanish Verify paragraph. <!-- sdd-owner: implementation -->
- [x] 2.3 Verify the ES block mirrors W1–W7 claim-for-claim and introduces none of N1–N7; in particular W4 keeps all four Microsoft-documented `setx` facts (user environment, newly created processes only, current shell untouched/unencrypted, 1024-char cap) and W5 keeps "un servidor en ejecución nunca vuelve a leer el entorno". <!-- sdd-owner: implementation -->
- [x] 2.4 Structural + parity self-check (design §6.3): `README_ES.md` prose ≤80 columns, one new fence pair (`grep -c '^```'` == task 0.3 baseline + 2); EN↔ES heading count per level equal and unchanged; the modified regions are the same region in both files (hardening section only); no heading text changed → no anchor churn. <!-- sdd-owner: implementation -->

## Phase 3 — Acceptance verification (design §7.1–§7.3): greps, scope, pure-addition

- [x] 3.1 Hard-zero greps (each must print **nothing**, matching the task 0.2 baseline): `grep -n "RNGCryptoServiceProvider" README.md README_ES.md`; `grep -n "ToHexString" README.md README_ES.md`; `grep -n "weaker posture" README.md`; `grep -n "postura más débil" README_ES.md`. A non-empty result is a defect in the fence comment or the prose — fix the wording, never the grep. <!-- sdd-owner: implementation -->
- [x] 3.2 Presence greps, each ≥1 hit in **both** files (design §7.2): `grep -n "RandomNumberGenerator" README.md README_ES.md`; `grep -n "setx" README.md README_ES.md`; `grep -n '\$env:SOFER_MCP_APPROVAL_PHRASE' README.md README_ES.md`; `grep -n "openssl rand -hex 16" README.md README_ES.md` (existing, unchanged); `grep -n "approval_configured" README.md README_ES.md`; `grep -n "RandomNumberGenerator.*Create().GetBytes" README.md README_ES.md` (exact portable form). Capture the output verbatim for the PR body. <!-- sdd-owner: implementation -->
- [x] 3.3 Anti-regression single-occurrence greps (design §7.3): rerun the task 0.4 command set; every #148 anchor must still count exactly `1` in its file — proving the baseline sentences are byte-identical and singular (not duplicated by the new block). <!-- sdd-owner: implementation -->
- [x] 3.4 Scope guard: `git status --short` lists exactly `README.md`, `README_ES.md`, plus the untracked change directory `openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/`. Zero changes under `src/`, `tests/`, `docs/`, `openspec/specs/`, `TRACE.md`, `scratch/`, `.gitignore`, `pyproject.toml`, `openspec/config.yaml`. Explicitly confirm `docs/cli-vs-mcp.md` was **not** created. <!-- sdd-owner: implementation -->
- [x] 3.5 Pure-addition guard + diff audit (design §7.3, §8): `git diff -- README.md README_ES.md | grep '^-'` returns only the two `---` diff headers (i.e. **zero deleted lines**); `git diff --stat -- README.md README_ES.md` shows exactly 2 files with ≈ +20/+20 and 0 deletions; total changed lines ≈40, well under the 400-line budget. Anything else in the diff is a scope violation — stop and revert it. <!-- sdd-owner: implementation -->
- [x] 3.6 Whitespace: `git diff --check` clean (design §7.3). <!-- sdd-owner: implementation -->

## Phase 4 — Suite, tooling, and the mandatory PowerShell execution gate (§7.4–§7.5)

- [x] 4.1 Suite unchanged: `uv run pytest tests/ -q` is green and numerically identical to the task 0.5 baseline (**1468 passed / 6 skipped**). The read-only executable proof is `tests/test_mcp_server.py` (fail-closed refusal) and `tests/test_mcp_process.py::TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch` (env-restart semantics at `:620-621`) — they must pass **unmodified**; no test file may be edited to accommodate wording (design C8). <!-- sdd-owner: implementation -->
- [x] 4.2 Tooling no-op: `uv run ruff check src/ tests/` clean. Because this change is docs-only, a non-clean result means something outside the two READMEs was touched — investigate instead of "fixing" it (design §7.4). <!-- sdd-owner: implementation -->
- [x] 4.3 Type-check no-op: `uv run mypy src/` clean (same reasoning as task 4.2). <!-- sdd-owner: implementation -->
- [x] 4.4 **§7.5 gate — Windows PowerShell 5.1 (required).** Run the design §3 D4 command verbatim on a Windows host: `powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion.ToString(); $bytes = New-Object byte[] 16; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString('x2') })"`. Record the **exact command and its exact output** in the verify report and the PR body: it must print a `5.1.<build>` line followed by a **32-character lowercase hex** string. Do not persist, reuse, or commit the printed phrase. <!-- sdd-owner: implementation -->
- [x] 4.5 **§7.5 gate — PowerShell 7+ (`pwsh`).** Run the same form via `pwsh -NoProfile -Command "…"` and record the exact command + output; when present it must print `7.<minor>.<build>` plus a 32-char lowercase hex string. If `pwsh` is **absent** on the host (or the invocation fails with command-not-found), record the literal error/absence output verbatim, report it explicitly as **best-effort / not executed**, and note it in the PR body — do not fabricate or skip silently; do not soften or simulate the result. <!-- sdd-owner: implementation -->
- [x] 4.6 Shape equivalence check (design C3, W1): confirm the 5.1-generated value matches the existing `openssl rand -hex 16` example's shape exactly — 16 bytes → 32 lowercase hex characters, no invented length or algorithm. Record only the length/shape observation (e.g. a character count), never the secret value itself. <!-- sdd-owner: implementation -->
- [x] 4.7 Gate consolidation: the PR must not be opened unless task 4.4 printed the 5.1 version line **and** a 32-char hex value (design §7.5, "PR-blocking by design"); record the combined gate outcome (5.1 pass/fail, pwsh pass/absent) as the literal §7.5 evidence block carried into the PR's verification section. <!-- sdd-owner: implementation -->

## Phase 5 — Delivery: one commit, PR only

- [ ] 5.1 Stage `README.md` + `README_ES.md` **together in a single commit** (AGENTS.md §13, design C2); commit message names GitHub issue #151 and the docs-only scope. Pre-commit ruff + mypy run automatically — do not use `--no-verify`. Verify afterwards that exactly one commit exists on the branch beyond `dev` and that it contains both files (`git show --stat HEAD`). <!-- sdd-owner: parent -->
- [ ] 5.2 Push the dedicated branch and open the PR into `dev` with `gh pr create --base dev` (never `main`/`dev` directly; no tag, no release). Fill every section of `.github/PULL_REQUEST_TEMPLATE.md` (AGENTS.md §11) with **actual command output** from Phases 3–4 — hard-zero greps, presence greps, single-occurrence greps, `git status --short`, `git diff --stat`, pytest tail, ruff/mypy, `git diff --check`, and the verbatim §7.5 execution-gate output (task 4.7) — plus the mandatory *SDD artifacts* section listing `proposal.md`, `specs/no-delta.md`, `design.md`, `tasks.md`. <!-- sdd-owner: parent -->
- [ ] 5.3 Confirm the PR diff region-by-region: both READMEs changed in the same hardening region, EN block and ES block mirrored, fence byte-identical EN↔ES; no `src/`/`tests/`/`docs/`/`openspec/specs/`/`TRACE.md`/scope-guard file present. Do not merge without human approval at the delivery gate. <!-- sdd-owner: parent -->

## Phase 6 — Bounded review and lifecycle gate (parent-owned)

- [ ] 6.1 Run the bounded post-apply review over the PR diff using design §4.1/§4.2 as the checklist: every W1–W7 claim present in both languages, zero N1–N7 claims, fence byte-identical and portable-form-correct, ES mirror complete and same-commit, zero deletions, no change to any #148 baseline sentence. <!-- sdd-owner: parent -->
- [ ] 6.2 Confirm the lifecycle gate: human approval of the PR before merge, `dev`-only target, no tag/release step, and the §7.5 gate evidence recorded in the PR (proposal *Delivery*, design §9). <!-- sdd-owner: parent -->

---

## Advisories

1. **Do not create `docs/cli-vs-mcp.md`.** The proposal's earlier sibling (#148) verified it does not exist and forbade creating it; the out-of-scope list is explicit. A later phase must not "restore" it.
2. **The fence comment is the hard-zero risk.** Writing "why not `RNGCryptoServiceProvider`" or "why not `ToHexString`" would fail task 3.1 by construction — describe the APIs ("legacy RNG constructor", "static .NET 5+ hex helpers") instead (design D5).
3. **Pointer, not restatement.** The diagnostics sentence must point at the existing `**Verify:**` / `**Verificación:**` paragraph; restating `PUBLISH_APPROVAL_NOT_CONFIGURED` vs `PUBLISH_APPROVAL_REQUIRED` would duplicate logic (AGENTS.md §4, design D6) and break the single-occurrence greps.
4. **Prose wraps, code does not.** Only re-wrap prose; keep every fence line verbatim on one line even where it exceeds 80 columns (design C5).
