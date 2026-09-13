# Apply Progress: Document the Windows approval-phrase path (PowerShell + cmd)

**Change**: `2026-09-11-fix-docs-approval-phrase-windows` (Fixes GitHub #151)
**Branch**: `docs/fix-151-approval-phrase-windows` (base `dev` — `git merge-base --is-ancestor dev HEAD` OK)
**Mode**: standard (NOT strict TDD — `openspec/config.yaml` sets `strict_tdd: false`; docs-only, spec delta none per `specs/no-delta.md`)
**Runtime token**: `sha256:5ad6768b79703daec174ab18dc70259d8e308ebaac8394a298039c994edaf4af` (work-unit `fix-151-approval-windows`)
**Status**: all 29 implementation-owned tasks complete; Phase 5/6 parent-owned tasks deferred.

## Structured status consumed

- Native engine reported `applyState: blocked` with `blockedReasons: ["domain specs are missing or partial."]`.
- Resolved as **stale/non-applicable for this change**: the spec artifact exists as `openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/specs/no-delta.md` (docs-only change, no capability delta by design — proposal *Capabilities / Spec delta*, design D8/§1). Required apply inputs (`proposal.md`, `specs/no-delta.md`, `design.md`, `tasks.md`) are all present and readable. The parent explicitly authorized apply for this change; no dependency/`actionContext` warning blocked the work.
- `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`; every write stayed inside that root.

## Completed tasks (all implementation-owned rows, 29/29)

Phase 0 preflight 0.1–0.7 · Phase 1 EN 1.1–1.5 · Phase 2 ES 2.1–2.4 · Phase 3 acceptance 3.1–3.6 · Phase 4 suite/tooling/gate 4.1–4.7.

## Files changed

| File | Change | Lines |
|---|---|---|
| `README.md` | Pure insertion between the per-agent env paragraph (L685) and the existing `**Windows:**` sentence (now L710): PowerShell fence + cmd/`setx` note + session/launcher/restart prose + Verify pointer | +23, −0 |
| `README_ES.md` | Same insertion between L720 and the `**Windows:**` sentence (now L745): ES prose mirror, fence byte-identical | +23, −0 |
| `openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/apply-progress.md` | This artifact | new |
| `openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/tasks.md` | Implementation-owned checkboxes marked `- [x]` | checkbox only |

`git diff --stat -- README.md README_ES.md` → `2 files changed, 46 insertions(+)`, **0 deletions**.
Total changed lines 46 + this artifact ≈ 11-12% of the 400-line review budget → single PR, no chain strategy.

## Evidence (exact commands + output)

### Phase 0 — preflight / baselines

```text
$ git rev-parse --abbrev-ref HEAD
docs/fix-151-approval-phrase-windows
$ git merge-base --is-ancestor dev HEAD   → exit 0 (dev is ancestor)

0.2 hard-zero baseline (all four empty — exit 1 each):
  grep -n "RNGCryptoServiceProvider" README.md README_ES.md   → (no output)
  grep -n "ToHexString"              README.md README_ES.md   → (no output)
  grep -n "weaker posture"           README.md                → (no output)
  grep -n "postura más débil"        README_ES.md             → (no output)

0.3 structural baseline:
  grep -c '^```' README.md README_ES.md  → README.md:38  README_ES.md:38
  grep -c '^#'   README.md README_ES.md  → 84 / 84
  grep -c '^## ' README.md README_ES.md  → 17 / 17
  grep -c '^### ' README.md README_ES.md → 17 / 17

0.4 #148 anti-regression baseline:
  EN ack=1  EN once=1  EN launcher=1  EN approval_configured=1
  ES ack=1  ES once=1  ES launcher=1  ES approval_configured=1

0.5 test baseline:
  $ uv run pytest tests/ -q
  1468 passed, 6 skipped, 13 warnings in 36.85s

0.6 read-only ground truth confirmed (no edits):
  src/sofer/mcp_server.py:217        _APPROVAL_PHRASE: str | None = None   (module level)
  src/sofer/mcp_server.py:1155       refusal hint "…set SOFER_MCP_APPROVAL_PHRASE and restart"
  src/sofer/mcp_server.py:1663       approval_configured = _APPROVAL_PHRASE is not None
  src/sofer/mcp_server.py:2640-2648  single read site in build_server (blank → None)
  openspec/specs/mcp-server/spec.md:137  fail-closed ladder / PUBLISH_APPROVAL_NOT_CONFIGURED
  openspec/specs/mcp-server/spec.md:390  published error-code enum
  openspec/specs/mcp-server/spec.md:424  sofer_auth_status / approval_configured
  openspec/specs/mcp-registration/spec.md:19  env NAMES only, never secret values

0.7 anchors unique before edit:
  grep -c -F 'environment or an explicit `environment` literal (plaintext on disk).' README.md        → 1  (L685)
  grep -c -F 'lanzador o un literal `environment` explícito (texto plano en disco).' README_ES.md     → 1  (L720)
```

### Phase 1/2 — insertion + structure

```text
$ grep -c '^```' README.md README_ES.md          → 40 / 40   (38 + 2 = one new fence pair each)
$ grep -c '^## ' README.md README_ES.md          → 17 / 17   (unchanged)
$ grep -c '^### ' README.md README_ES.md         → 17 / 17   (unchanged)
$ diff <(sed -n '689,696p' README.md) <(sed -n '724,731p' README_ES.md)
→ FENCES IDENTICAL (byte-for-byte, EN↔ES)
```

New fence body (byte-verbatim, unwrapped per design C5):

```powershell
# Portable on Windows PowerShell 5.1 (the default) and PowerShell 7+:
# the legacy RNG constructor is deprecated, and the static .NET 5+ hex
# helpers do not exist on 5.1, so use the instance API below.
$bytes = New-Object byte[] 16
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$env:SOFER_MCP_APPROVAL_PHRASE = -join ($bytes | ForEach-Object { $_.ToString("x2") })
```

- W1–W7 all present; N1–N7 all absent.
- No `sofer-mcp` launch line inside the fence (D3).
- No literal `RNGCryptoServiceProvider` / `ToHexString` (D5): comments describe "the legacy RNG constructor" / "the static .NET 5+ hex helpers".
- Diagnostics pointer present with the `**Verify**` (EN) / `**Verificación**` (ES) label; it does not restate the error-code disambiguation.
- ES fence is byte-identical to EN; only surrounding prose is translated; all technical tokens stay English.

### Phase 3 — acceptance

```text
3.1 hard-zero after edit (all four empty, matching 0.2):
  grep -n "RNGCryptoServiceProvider" README.md README_ES.md   → (no output, exit 1)
  grep -n "ToHexString"              README.md README_ES.md   → (no output, exit 1)
  grep -n "weaker posture"           README.md                → (no output, exit 1)
  grep -n "postura más débil"        README_ES.md             → (no output, exit 1)
  extra N2/N5/N6 probe: grep -n "without restart|reloads|python -c \"import secrets|HKLM" README.md README_ES.md → (no output, exit 1)

3.2 presence (≥1 hit in BOTH files):
  README.md:695 / README_ES.md:730   [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  README.md:702,703,705,707 (4)      `setx` …      README_ES.md:737,738,742 (3)
  README.md:696 / README_ES.md:731   $env:SOFER_MCP_APPROVAL_PHRASE = -join (…)
  README.md:674 / README_ES.md:709   export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"   (existing, unchanged)
  README.md:708,714 / README_ES.md:743,749   approval_configured
  grep -n "RandomNumberGenerator.*Create().GetBytes" README.md README_ES.md → 695 / 730

3.3 anti-regression — design §7.3 EXACT anchors, all still exactly 1:
  EN ack=1  EN once=1  EN launcher=1  EN 'sofer_auth_status(config).*approval_configured'=1
  ES ack=1  ES once=1  ES launcher=1  ES 'sofer_auth_status(config).*approval_configured'=1

3.4 scope guard:
  $ git status --short
   M README.md
   M README_ES.md
  ?? openspec/changes/2026-09-11-fix-docs-approval-phrase-windows/
  Zero changes under src/, tests/, docs/, openspec/specs/, TRACE.md, scratch/, .gitignore, pyproject.toml, openspec/config.yaml.
  $ ls docs/cli-vs-mcp.md
  ls: cannot access 'docs/cli-vs-mcp.md': No such file or directory   (docs/ contains only configuration.md — NOT created)

3.5 pure addition:
  $ git diff --stat -- README.md README_ES.md
   README.md    | 23 +++++++++++++++++++++++
   README_ES.md | 23 +++++++++++++++++++++++
   2 files changed, 46 insertions(+)
  $ git diff -- README.md README_ES.md | grep '^-'
  --- a/README.md
  --- a/README_ES.md
  (only the two diff headers — ZERO deleted lines)

3.6 whitespace:
  $ git diff --check     → (no output) exit 0
```

### Phase 4 — suite, tooling, §7.5 execution gate

```text
4.1 $ uv run pytest tests/ -q
    1468 passed, 6 skipped, 13 warnings in 37.19s      (numerically identical to 0.5; no test file edited)

4.2 $ uv run ruff check src/ tests/
    All checks passed!                                  exit 0

4.3 $ uv run mypy src/
    Success: no issues found in 32 source files         exit 0

4.4 §7.5 gate — Windows PowerShell 5.1 (REQUIRED):
    $ powershell.exe -NoProfile -Command '$PSVersionTable.PSVersion.ToString(); $bytes = New-Object byte[] 16; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString("x2") })'
    5.1.26100.9444
    cc1309def8924e7bba9a7cbfee22c433
    exit=0   → PASS (version line + 32-char lowercase hex)

4.5 §7.5 gate — PowerShell 7+:
    $ pwsh -NoProfile -Command '$PSVersionTable.PSVersion.ToString(); $bytes = New-Object byte[] 16; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString("x2") })'
    7.6.6
    b478186b29f646f8491d69e208332fc5
    exit=0   → PASS (version line + 32-char lowercase hex)

4.6 shape equivalence (C3/W1): generated value = 32 characters, lowercase hex ([0-9a-f]), 16 bytes × 2
    hex digits — exactly the `openssl rand -hex 16` example's shape. No invented length/algorithm.
    Only the length/shape is recorded; the generated secrets are not persisted or committed.

4.7 gate consolidation: 5.1 = PASS, pwsh 7+ = PASS. §7.5 is satisfied; PR is not blocked by this gate.
```

## Deviations from design

1. **Line-count arithmetic in design §6.1/§6.2 and §8 is off by 3 per file.** The design states
   "New lines: 20 (2 intro + 1 blank + 8 fence + 1 blank + 8 prose)", but the §6.1/§6.2 block it
   specifies contains **10** prose lines after the fence, and the blank separator before the existing
   `**Windows:**` sentence is an added line. Actual result: **+23 / +23, 0 deletions** (46 total),
   not +20/+20 (40). The inserted text is byte-verbatim the design block — the diff was not
   re-wrapped or trimmed to hit the estimate (budget is not code-golf; `work-unit-commits` skill).
   46 lines is still ≈12% of the 400-line budget → no delivery-strategy question.
2. **`grep -c '^#'` rises by +3 per file (84 → 87).** The three mandated PowerShell comment lines
   begin with `#`. This counter includes code-fence comment lines, so the design's §7.3
   "`grep -c '^#'` unchanged" guard and task 1.5 literally conflict with the mandated
   (D5/W7, task 1.4) comment lines. The guard's **intent** holds: no new heading exists —
   `^## ` = 17/17 and `^### ` = 17/17 are unchanged, EN↔ES are equal, and no TOC/anchor changed.
   `grep -c '^# '` likewise rises 49 → 52 (+3) for the same three comment lines, EN=ES.
3. **Bare `grep -c 'approval_configured'` is 2 in each file (was 1).** The new mandated
   `sofer_auth_status` → `approval_configured` pointer (W6/D6, §7.2 presence requirement)
   necessarily adds one occurrence. The design's §7.3 *exact* anchor form
   (`sofer_auth_status(config).*approval_configured`) is still exactly **1** in both files, so the
   #148 Verify paragraph is byte-identical and singular. The tasks.md 0.4 counter is over-broad
   relative to design §7.3; the design-accurate check passes.
4. **Two new prose lines are 82 columns (EN/ES), one char over the ≤80 guidance.**
   `` `$env:` (PowerShell) and `set` (cmd) affect only the current session — a process `` and
   `Confirm with \`sofer_auth_status\` → \`approval_configured\` (see **Verify** below).`
   Both are the design's §6.1 byte-verbatim text, and the **pre-existing** #148 prose in the same
   region already reaches 82 columns (EN) / 81 (ES), so they match their neighbours. Not re-wrapped,
   to preserve the mandated byte-verbatim block.

No other deviation. No #148 baseline sentence was modified; the `**Windows:**` and `**Verify:**`
paragraphs are untouched.

## Remaining tasks

All implementation-owned rows are complete. The 5 remaining unchecked rows are **parent-owned**
lifecycle actions (preserved byte-for-byte, deferred):

```text
- [ ] 5.1 Stage `README.md` + `README_ES.md` **together in a single commit** … <!-- sdd-owner: parent -->
- [ ] 5.2 Push the dedicated branch and open the PR into `dev` with `gh pr create --base dev` … <!-- sdd-owner: parent -->
- [ ] 5.3 Confirm the PR diff region-by-region … <!-- sdd-owner: parent -->
- [ ] 6.1 Run the bounded post-apply review over the PR diff … <!-- sdd-owner: parent -->
- [ ] 6.2 Confirm the lifecycle gate … <!-- sdd-owner: parent -->
```

`sdd-apply` MUST NOT start review/refutation/correction/validation actors, create receipts, or
validate delivery gates → this phase returns `next_recommended: parent-lifecycle`.

## Workload / PR boundary

Single PR, one commit, both READMEs together (AGENTS.md §13 / design C2). 46 added lines, 0 deleted.
No chaining required; no `size:exception` requested or implied. Delivery decision stays with the
parent at the gate.

## TDD evidence

Strict TDD is **not active** (`openspec/config.yaml: strict_tdd: false`; `rules.apply.tdd: false`).
This change is docs-only with an explicit no-delta spec (`specs/no-delta.md`), so no RED/GREEN cycle
applies. The executable proof that the documented behavior is real is the existing suite passing
**unchanged** (`tests/test_mcp_server.py` fail-closed refusal,
`tests/test_mcp_process.py::TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch`
env-restart semantics) → 1468 passed / 6 skipped, identical to baseline.

| Task | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| (docs-only, no-delta) | n/a — no behavior change; hard-zero greps and the 5.1/pwsh execution gate are the change's own acceptance proof | acceptance greps + suite green | EN/ES parity + both PowerShell runtimes | none needed |
