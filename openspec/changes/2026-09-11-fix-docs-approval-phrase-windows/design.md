# Design: Document the Windows approval-phrase path (PowerShell + cmd)

**Change**: `2026-09-11-fix-docs-approval-phrase-windows` (Fixes GitHub #151)
**Date**: 2026-09-11
**Status**: designed
**Change type**: docs-only — `README.md` + `README_ES.md`, one commit
**Spec delta**: none (see `specs/no-delta.md`; this design introduces no behavior)

---

## 1. Design summary

Strictly additive documentation. The hardening section shows only a bash
generation path, so Windows hosts have no documented way to produce or persist
the approval phrase. This change inserts one contiguous Windows block into
`### Hardening for sensitive hosts` (README.md L664-695) and its exact Spanish
mirror into `### Endurecimiento para hosts sensibles` (README_ES.md L699-730):
a **PowerShell generation snippet** (portable .NET crypto RNG, valid on Windows
PowerShell 5.1 = the default `powershell.exe` and PowerShell 7+), a **cmd/`setx`
note** with Microsoft-documented persistence caveats, and **container prose** on
Windows env semantics (`$env:`/`set` session scope vs. the launcher environment,
full host restart, running server never re-reads env vars) plus a pointer to the
existing Verify paragraph. No #148 baseline sentence is touched.

The engineering content of the design:

1. **Placement decision** (§3 D1) — where the block goes so it cannot read as a
   duplication or regression of the merged #148 fail-closed prose.
2. **Snippet contract** (§3 D2/D3/D5) — the exact three-line portable form, why
   the deprecated/static alternatives fail on 5.1, and how the fence comment
   explains the choice **without reintroducing the literal deprecated token**
   (hard-zero grep constraint).
3. **Wording contract** (§4) — the exact claims the new text MUST and MUST NOT
   make, each traced (§5).
4. **Mechanical acceptance** (§7) — hard-zero and presence greps for EN and ES,
   verbatim-anchor single-occurrence greps that prove the #148 sentences are
   byte-identical and singular, and the verify-phase PowerShell execution matrix
   (the snippet could not be executed in this design session — no execution tool
   in the session toolset; see §3 D4).

## 2. Design constraints and invariants

| # | Invariant | Source |
|---|---|---|
| C1 | Only `README.md` and `README_ES.md` change. Nothing under `src/`, `tests/`, `docs/`, `openspec/specs/`, `TRACE.md`, `SOFER_TRACE.md`, `.gitignore`. | `specs/no-delta.md` §4; proposal *Out of Scope* |
| C2 | Both files are edited in the **same commit**; heading count/order stay mirrored; prose is translated, technical tokens stay English. | AGENTS.md §13 |
| C3 | No countable constant is invented beyond the replica of the existing example: 16 bytes → 32 hex chars, matching `openssl rand -hex 16` exactly. | AGENTS.md §1; proposal *Approach* |
| C4 | The `### Hardening for sensitive hosts` / `### Endurecimiento para hosts sensibles` headings and the merged #148 baseline sentences in that section stay **byte-identical and singular**: fail-closed preamble, read-once paragraph, per-agent env paragraph, `**Windows:**` launcher sentence, `**Verify:**` paragraph. | `specs/no-delta.md` §4; mandate (forbidden: duplication/regression of #148 prose) |
| C5 | Code fence lines are copied **verbatim, unwrapped** even where a line exceeds the ≤80-column prose rule (prose wraps; code does not). | #148 design §4.3 (precedent) |
| C6 | Only Microsoft-documented `setx` facts are stated: writes `HKCU\Environment`; visible to **newly created** processes only; does not affect the current shell; stored unencrypted; 1024-character cap. | Mandate item 4 |
| C7 | The diff stays minimal and well inside the 400-line review budget; delivery is the dedicated branch `docs/fix-151-approval-phrase-windows` (base `dev`), merged only via PR; no tag, no release. | Session preflight (`ask-on-risk`); proposal *Delivery* |
| C8 | No new test. The existing publish-gate suite must pass **unchanged**: `uv run pytest tests/ -q` → **1468 passed / 6 skipped** (the mandate's baseline; unchanged by a docs-only diff). | Mandate item 6; `specs/no-delta.md` §2 |
| C9 | No new headings → no TOC edits → no anchor churn. The new text's pointer labels (`**Verify:**` / `**Verificación:**`) are inline bold labels in the same section — no anchors, no link targets. | #148 design D7 |

## 3. Decisions (with rationale)

### D1 — Placement: contiguous block immediately BEFORE the existing `**Windows:**` sentence

**Decision.** Insert the new Windows block after the per-agent env paragraph
(README.md L685, `…literal (plaintext on disk).`) and before the existing
`**Windows:**` sentence (L687). Same position for ES (after L720, before L722).
The block stays inside the same contiguous region (between the read-once/per-agent
paragraph and the `**Windows:**` sentence), so "the region stays contiguous" holds.

**Rationale.** The proposal's approach listed two candidate slots and deferred the
choice ("exact placement decided at design time"), with question-round assumption 4
leaning "immediately after the bash fence". Inserting after the bash fence would put
the block **directly adjacent to the read-once paragraph** ("It is read once at
process start … fully restart the agent host"), producing three adjacent restart/
immutability statements (new block → read-once paragraph → `**Windows:**` sentence)
and reading as an echo of #148 instead of a complement. Inserting between the
per-agent paragraph and the `**Windows:**` sentence gives the cleanest flow:

1. fail-closed preamble + bash fence (POSIX generate/launch),
2. read-once immutability + per-agent env guidance (generic rules),
3. **new Windows block** (generation, session-scope, `setx`, restart causality,
   verify pointer),
4. existing `**Windows:**` launcher sentence (verbatim — the natural conclusion:
   "and it must be in the environment that launches the server"),
5. existing Verify paragraph (the pointer's landing spot).

The `**Windows:**` sentence and the Verify paragraph stay untouched either way
(C4); this placement minimizes perceived duplication of #148 prose — the mandate's
top forbidden item — while keeping the new block a single contiguous insertion.

### D2 — Snippet: the portable instance form, exactly three code lines

**Decision.** The PowerShell fence is the mandate's REQUIRED portable form, verbatim:

```powershell
# Portable on Windows PowerShell 5.1 (the default) and PowerShell 7+:
# the legacy RNG constructor is deprecated, and the static .NET 5+ hex
# helpers do not exist on 5.1, so use the instance API below.
$bytes = New-Object byte[] 16
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$env:SOFER_MCP_APPROVAL_PHRASE = -join ($bytes | ForEach-Object { $_.ToString("x2") })
```

- `New-Object byte[] 16` + the instance `GetBytes(byte[])` are .NET Framework 2.0-era
  base-class APIs → present on **both** Windows PowerShell 5.1 (.NET Framework) and
  PowerShell 7+ (.NET). `RandomNumberGenerator.Create()` returns the OS-strong RNG
  on both runtimes.
- Rejected alternatives (all break 5.1 or are deprecated): `RNGCryptoServiceProvider`
  (obsolete, SYSLIB0023, on .NET 6+ → PowerShell 7); static
  `RandomNumberGenerator::GetBytes(int)` (needs .NET Core 3.0+ → absent on .NET
  Framework); `[System.Convert]::ToHexString` (needs .NET 5+ → absent on .NET
  Framework). Documented-availability matrix in §3 D4.
- Output shape: 16 bytes → `ToString("x2")` per byte → 32 lowercase hex chars,
  exactly reproducing the `openssl rand -hex 16` example's shape (C3). No
  `sofer-mcp` launch line is added to the fence (D3).

### D3 — No `sofer-mcp` line inside the PowerShell fence

**Decision.** The fence is generation + session-set only (the three mandated
lines). The bash fence beside it ends with `sofer-mcp`; the Windows fence does not.

**Rationale.** The existing #148 `**Windows:**` sentence states the variable must
be in the **launcher's** environment "not merely in the shell you typed in". A
`sofer-mcp` line inside the fence would imply launching the server from your
interactive shell is the recipe — a reading that collides with that sentence. The
new container prose (and the adjacent `**Windows:**` sentence) already covers
where the value must live; the fence only needs to be able to produce and set it.

### D4 — Snippet validation: not executable in this design session; portability justified from documented APIs; execution moved to a mandatory verify-phase gate

**Decision.** This design session's toolset exposes **no execution tool** (read /
grep / write / edit / memory tools only), so `powershell.exe` / `pwsh` were **not
invoked here**. Per the mandate ("otherwise state it was not executable here and
justify portability from documented API availability"), portability rests on the
following documented .NET API availability:

| API used | Documented availability | Verdict |
|---|---|---|
| `[System.Security.Cryptography.RandomNumberGenerator]::Create()` (static factory) | .NET Framework 1.1+, .NET Standard/Core, .NET 5+ | WinPS 5.1 ✓, PS 7 ✓ |
| `.GetBytes(byte[])` (instance method on the base class) | .NET Framework 2.0+, all later | WinPS 5.1 ✓, PS 7 ✓ |
| `New-Object byte[] 16` (byte-array literal) | Built-in PowerShell syntax, both runtimes | WinPS 5.1 ✓, PS 7 ✓ |
| `$_.ToString("x2")` + `-join` (hex formatting) | Built-in, both runtimes | WinPS 5.1 ✓, PS 7 ✓ |
| `RNGCryptoServiceProvider` (rejected) | Obsolete since .NET 6 (SYSLIB0023) → PowerShell 7 warns; discouraged everywhere | ✗ |
| static `RandomNumberGenerator::GetBytes(int)` (rejected) | .NET Core 3.0+ / .NET 5+ only; **absent on .NET Framework** | ✗ on 5.1 |
| `[System.Convert]::ToHexString` (rejected) | .NET 5+ only; **absent on .NET Framework** | ✗ on 5.1 |

**Verify-phase gate (mandatory before the PR lands)** — run on a Windows machine
with both runtimes and record command + output in the verify report:

```text
powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion.ToString(); $bytes = New-Object byte[] 16; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString('x2') })"
pwsh -NoProfile -Command     "$PSVersionTable.PSVersion.ToString(); $bytes = New-Object byte[] 16; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString('x2') })"
```

Expected: a line `5.1.<build>` then a 32-char lowercase hex string (single quotes
inside the `-Command` string avoid quoting issues); and `7.<minor>.<build>` with the
same 32-hex shape. Both must pass before the PR is opened.

### D5 — Fence comment explains the API choice WITHOUT the forbidden literal tokens

**Decision.** The fence comment describes "the legacy RNG constructor" and "the
static .NET 5+ hex helpers" instead of writing `RNGCryptoServiceProvider` /
`ToHexString` literally.

**Rationale.** The proposal's machinery self-check requires a **hard-zero** grep for
`RNGCryptoServiceProvider` in both files (and this design extends the hard-zero set
to `ToHexString`). A comment saying "why not `RNGCryptoServiceProvider`" would fail
that grep by construction. The descriptive phrasing keeps the explanation while
making acceptance machine-decidable. The three code lines remain byte-identical to
the mandate's required form (D2).

### D6 — Verify pointer, not restatement

**Decision.** The block ends with `Confirm with sofer_auth_status →
approval_configured (see **Verify** below).` — it does not restate the Verify
paragraph's error-code disambiguation.

**Rationale.** Mandate wording-contract item 5 requires the
`sofer_auth_status` → `approval_configured` verification path to appear in the new
container (also a presence-grep token); AGENTS.md §4 forbids duplicating the
disambiguation that the immediately-following **Verify:** paragraph already
carries. Pointer + token, no restatement.

### D7 — `setx` facts: exactly the four Microsoft-documented claims

**Decision.** The cmd note states: `setx SOFER_MCP_APPROVAL_PHRASE <value>` writes
to the user environment (`HKCU\Environment`); visible to **newly created**
processes only; does **not** change the current shell; stored **unencrypted**;
truncates values longer than **1024 characters**; and therefore still requires a
full host restart (a running server never re-reads env vars). No fifth claim, no
registry-path elaboration beyond `HKCU\Environment`, no claims about other users'
profiles or system-wide scope.

**Rationale.** C6. The four facts are the mandate's item-4 list, asserted as
Microsoft-documented. The truncation fact is phrased with the documented
"1024 characters" figure (the design's only new number, from Microsoft docs, not
invented — C3 applies to repo behavior, this is operator documentation).

### D8 — No spec delta, no test, single-commit delivery

**Decision.** No requirement file is added or modified (`specs/no-delta.md` §2-§4);
no test is added or changed; `README.md` + `README_ES.md` land in **one commit** on
the dedicated branch, merged only via PR (C7, C8).

**Rationale.** Already settled in the proposal and no-delta: every proposition the
new prose states restates MSP-R05 (`mcp-server/spec.md:137`), 10.3 (`:390`), 10.8
(`:424`), or MCP-REG-01 (`mcp-registration/spec.md:19`), or is OS-level operator
guidance (PowerShell/cmd/env semantics) that no spec pins as system behavior. A
docs-conformance requirement would force a README-grep test under
`openspec/config.yaml rules.specs` — out of scope (recorded as follow-up candidate).

## 4. Wording contract

### 4.1 Claims the new text MUST make (EN; ES mirrors each)

| # | Claim | Traced to |
|---|---|---|
| W1 | Windows can generate the phrase **without `openssl`**, using the .NET crypto RNG, producing the same 32-hex-char shape as `openssl rand -hex 16`. | OS tool availability; C3; existing example at README.md:674 |
| W2 | On Windows, `$env:` (PowerShell) and `set` (cmd) affect **only the current session**; a process inherits the value only when launched from that session. | Windows process env model (Microsoft docs) |
| W3 | The value must be in the environment that **launches** the MCP server, or be persisted via `setx` **and** followed by a full host restart. | `mcp_server.py:2637-2648` (read at build); `#148` `**Windows:**` sentence (L687-689, unchanged) |
| W4 | `setx` facts: `HKCU\Environment`, newly created processes only, current shell untouched, stored unencrypted, 1024-char cap. | Mandate item 4; C6 |
| W5 | A **running server never re-reads** env vars — restart is the only way to apply a change. | `mcp_server.py:217,2637-2648` (`_APPROVAL_PHRASE` module-level, read once) |
| W6 | Verify with `sofer_auth_status` → `approval_configured` (pointer to the existing **Verify:** paragraph, not a restatement). | `mcp_server.py:1627-1670`; `spec.md:424`; D6 |
| W7 | The PowerShell snippet is portable across Windows PowerShell 5.1 and PowerShell 7+ (stated by the fence comment). | §3 D2/D4 matrix |

### 4.2 Claims the new text MUST NOT make

| # | Forbidden claim | Why |
|---|---|---|
| N1 | That a running server **reloads** env vars, "picks up" the change, or that `$env:`/`setx` take effect without a restart. | Directly contradicted by W5 (the single-read site, `mcp_server.py:2640-2648`); the primary support-loop risk. |
| N2 | That `setx` affects the **current** shell or shows the value in the current session. | C6 (Microsoft docs: current shell untouched). |
| N3 | The literal tokens `RNGCryptoServiceProvider` / `ToHexString` anywhere in either README. | Proposal hard-zero grep + D5; the deprecated class must not be re-offered as a recipe. |
| N4 | Re-introduction of weak/optional phrasing ("weaker posture", "postura más débil", "optional phrase") or any duplication of a #148 baseline sentence (fail-closed preamble, read-once paragraph, per-agent paragraph, `**Windows:**` sentence, Verify paragraph). | Mandate forbidden list; C4; hard-zero greps §7.1. |
| N5 | A third generation path not requested by the issue (e.g. `python -c "secrets…"`). | Proposal *Alternatives* — rejected/deferred. |
| N6 | Claims about other users' environments, system-wide (`HKLM`) scope, or Cyrillic/registry internals beyond `HKCU\Environment`. | C6 — only documented facts. |
| N7 | Any behavior claim beyond the section's already-normative statements (MSP-R05, 10.3, 10.8, MCP-REG-01). | `specs/no-delta.md` §2. |

### 4.3 Structural constraints

- Region boundaries: body of `### Hardening for sensitive hosts` (README.md
  L664-695) / `### Endurecimiento para hosts sensibles` (README_ES.md L699-730)
  only; the insertion is a **pure addition** between the per-agent paragraph and
  the `**Windows:**` sentence in both files.
- Prose wraps at ≤ 80 columns; code fence lines are verbatim and do not wrap (C5).
- The new fence language token is `` ```powershell `` (new to both files — the
  files currently use only `bash` / `python` / `toml` / `yaml` fences; GitHub-flavored
  Markdown renders it in both).
- No new headings, tables, images, or TOC edits (C9).

### 4.4 Language split (AGENTS.md §13)

| Stays English in both files | Translated in `README_ES.md` |
|---|---|
| `SOFER_MCP_APPROVAL_PHRASE`, `setx`, `$env:`, `set`, `openssl`, `RandomNumberGenerator`, `.NET`, `HKCU\Environment`, `sofer_auth_status`, `approval_configured`, `sofer-mcp`, `MCP`, `<value>`, the whole PowerShell fence (code + comment lines, byte-identical) | All surrounding prose: "session", "launcher/entorno que lanza", "full host restart", "unencrypted/sin cifrar", "newly created/recién creados", the "**Verificación**" pointer label |

## 5. Claim → source traceability (no new facts)

```
W1,W7 → §3 D2/D4 documented .NET API matrix (external, Microsoft docs), C3
W2    → Windows process-environment model (Microsoft docs): set / $env: mutate
        the current process; children inherit at launch
W3,W5 → src/sofer/mcp_server.py:217,2637-2648  module-level _APPROVAL_PHRASE,
        read once at build_server; refusal hint ":set SOFER_MCP_APPROVAL_PHRASE
        and restart" (mcp_server.py:1154-1155)
W4    → C6 / mandate item 4 (Microsoft setx documentation)
W6    → src/sofer/mcp_server.py:1627-1670 sofer_auth_status:
        approval_configured, requires_approval_phrase=True
        → openspec/specs/mcp-server/spec.md:424   (already normative)
C4    → #148 baseline sentences stay byte-identical (this design edits around,
        never inside them)
N3    → proposal success criteria (hard-zero grep) + D5
No new repo facts. Everything the block states restates either existing README/
code/spec content or Microsoft-documented OS behavior — nothing invented (C3, N7).
```

## 6. Edit specification

### 6.1 `README.md` — one pure insertion (verified offsets: L664-695 region)

**Anchor** (must occur exactly once — apply phase runs `grep -c` to confirm):

```text
environment or an explicit `environment` literal (plaintext on disk).

**Windows:** the variable must be in the launcher's environment
```

**Edit recipe** — replace the anchor span `literal (plaintext on disk).\n\n**Windows:**`
with `literal (plaintext on disk).\n\n` + the block below + `\n\n**Windows:**`. The
read-once paragraph, per-agent paragraph, `**Windows:**` sentence, and Verify
paragraph are untouched (C4); the diff inside the section is additions only.

```markdown
On Windows, generate the same 32-hex-char phrase without `openssl`, using the
.NET crypto RNG, and set it for the current session only:

```powershell
# Portable on Windows PowerShell 5.1 (the default) and PowerShell 7+:
# the legacy RNG constructor is deprecated, and the static .NET 5+ hex
# helpers do not exist on 5.1, so use the instance API below.
$bytes = New-Object byte[] 16
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$env:SOFER_MCP_APPROVAL_PHRASE = -join ($bytes | ForEach-Object { $_.ToString("x2") })
```

`$env:` (PowerShell) and `set` (cmd) affect only the current session — a process
inherits the value only when it is launched from that session. For the agent
host to see it, the value must be in the environment that launches the MCP
server, or be persisted with `setx` and followed by a full host restart:
`setx SOFER_MCP_APPROVAL_PHRASE <value>` writes to the user environment
(`HKCU\Environment`) for **newly created** processes only — it does not change
the current shell, the value is stored unencrypted, and `setx` truncates
values longer than 1024 characters. A server that is already running never
re-reads the environment, so after `setx` you must fully restart the host.
Confirm with `sofer_auth_status` → `approval_configured` (see **Verify** below).
```

New lines: 20 (2 intro + 1 blank + 8 fence + 1 blank + 8 prose). W1-W7 all
present; N1-N7 all absent (checked mechanically in §7).

### 6.2 `README_ES.md` — the mirror, same commit (AGENTS.md §13)

**Anchor** (must occur exactly once):

```text
lanzador o un literal `environment` explícito (texto plano en disco).

**Windows:** la variable debe estar en el entorno del lanzador
```

**Edit recipe** — same shape: replace `texto plano en disco).\n\n**Windows:**`
with `texto plano en disco).\n\n` + the block below + `\n\n**Windows:**`.

```markdown
En Windows, genera la misma frase de 32 caracteres hexadecimales sin `openssl`,
usando el RNG criptográfico de .NET, y defínela solo para la sesión actual:

```powershell
# Portable on Windows PowerShell 5.1 (the default) and PowerShell 7+:
# the legacy RNG constructor is deprecated, and the static .NET 5+ hex
# helpers do not exist on 5.1, so use the instance API below.
$bytes = New-Object byte[] 16
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$env:SOFER_MCP_APPROVAL_PHRASE = -join ($bytes | ForEach-Object { $_.ToString("x2") })
```

`$env:` (PowerShell) y `set` (cmd) afectan solo a la sesión actual — un proceso
hereda el valor únicamente si se lanza desde esa sesión. Para que el host lo
vea, el valor debe estar en el entorno que lanza el servidor MCP, o persistido
con `setx` y seguido de un reinicio completo del host:
`setx SOFER_MCP_APPROVAL_PHRASE <value>` escribe en el entorno de usuario
(`HKCU\Environment`) solo para los procesos **recién creados** — no cambia el
shell actual, almacena el valor sin cifrar y trunca los valores de más de
1024 caracteres. Un servidor que ya está en ejecución nunca vuelve a leer el
entorno, así que tras `setx` debes reiniciar por completo el host. Confírmalo
con `sofer_auth_status` → `approval_configured` (ver **Verificación** abajo).
```

The PowerShell fence is **byte-identical** EN↔ES (code stays English in both,
§13-§4.4); only the surrounding prose is translated. New lines: 20.

### 6.3 Heading/parity check (structural, no edits)

```
README.md      L664 ### Hardening for sensitive hosts        (bash fence L673-676, **Windows:** L687-689, **Verify:** L691-695)
README_ES.md   L699 ### Endurecimiento para hosts sensibles  (bash fence L708-711, **Windows:** L722-724, **Verificación:** L726-730)
```

Pre-edit: `grep -c '^## '` and `grep -c '^### '` are equal across files; post-edit
they must remain equal and UNCHANGED (no new headings, C9). Both files gain exactly
one `` ```powershell `` fence (open+close), so `grep -c '^```'` rises by exactly 2
in each file.

## 7. Verification strategy (no new tests)

The executable proof of the *documented* behavior is the existing suite passing
**unchanged** (C8); the executable proof of the *documentation* is the grep set
below plus the snippet-execution gate (§3 D4). Both belong in the verify report.

### 7.1 Hard-zero greps (the acceptance criterion — each must print **nothing**)

```bash
grep -n "RNGCryptoServiceProvider" README.md README_ES.md
grep -n "ToHexString"              README.md README_ES.md
grep -n "weaker posture"           README.md
grep -n "postura más débil"        README_ES.md
```

Baseline: all four already return nothing today (the proposal verified
`RNGCryptoServiceProvider` absent; the design adds `ToHexString` to the same set —
the comment must therefore keep describing "legacy RNG constructor"/".NET 5+ hex
helpers", never the literal names — D5).

### 7.2 Presence greps (each must return ≥ 1 hit in **both** files)

```bash
grep -n "RandomNumberGenerator"        README.md README_ES.md   # new fence
grep -n "setx"                         README.md README_ES.md   # new cmd note
grep -n '\$env:SOFER_MCP_APPROVAL_PHRASE' README.md README_ES.md # new fence
grep -n "openssl rand -hex 16"         README.md README_ES.md   # existing — unchanged
grep -n "approval_configured"          README.md README_ES.md   # existing Verify + new pointer
grep -n "RandomNumberGenerator.*Create().GetBytes" README.md README_ES.md  # exact portable form
```

### 7.3 Anti-regression greps (#148 sentences byte-identical and singular)

Each of the following EN anchors must appear **exactly once** in `README.md` (and
the ES equivalents once in `README_ES.md`) — the count must be 1 both before and
after the edit:

```bash
grep -c "Do not rely on the two .acknowledge_\*. flags alone" README.md
grep -c "It is read .\*once at process start.\*"              README.md
grep -c "the variable must be in the launcher's environment"  README.md
grep -c "sofer_auth_status(config). . approval_configured"    README.md
grep -c "No confíes solo en los dos flags .acknowledge_\*."   README_ES.md
grep -c "Se lee .\*una sola vez al iniciar el proceso.\*"     README_ES.md
grep -c "la variable debe estar en el entorno del lanzador"   README_ES.md
grep -c "sofer_auth_status(config). . approval_configured"    README_ES.md
```

Plus scope/mirror/whitespace guards:

```bash
git status --short                                  # exactly README.md, README_ES.md
git diff -- README.md README_ES.md | grep '^-'      # ZERO deleted lines (pure addition)
grep -c '^#' README.md README_ES.md                 # per-level counts equal, unchanged
grep -c '^```' README.md README_ES.md               # rises by exactly 2 in each file
git diff --check                                    # clean
```

### 7.4 Suite and tooling (must be unchanged)

```bash
uv run pytest tests/ -q     # 1468 passed / 6 skipped — unchanged baseline (C8)
uv run ruff check src/ tests/
uv run mypy src/
```

`tests/test_mcp_server.py:751-820` (fail-closed refusal) and
`tests/test_mcp_process.py:621` (env-restart semantics) are the RED/GREEN-equivalent
executable proof that the new prose describes real behavior; they are read-only
evidence and must not be edited for wording.

### 7.5 Snippet execution gate (mandatory, Windows host with both runtimes)

Run §3 D4's two commands (powershell.exe 5.1 and pwsh 7+); each must print the
`$PSVersionTable` line and a 32-char lowercase hex string. Record command + output
in the verify report. **The PR must not be opened until both runtimes pass.**

## 8. File change map

| File | Region | Change | Lines (est.) |
|---|---|---|---|
| `README.md` | Insertion inside `### Hardening for sensitive hosts`, between per-agent paragraph (L685) and `**Windows:**` (L687) | PowerShell fence + cmd/`setx` note + session/launcher/restart prose + verify pointer | +20 |
| `README_ES.md` | Insertion inside `### Endurecimiento para hosts sensibles`, between L720 and L722 | ES mirror, fence byte-identical | +20 |

Estimated diff: ~40 added lines across 2 files, **zero deletions** — ~10% of the
400-line review budget, so no chain strategy is required. Unchanged by design:
`src/**`, `tests/**`, `docs/**`, `openspec/specs/**`, `TRACE.md`, `SOFER_TRACE.md`,
`.gitignore`, and every #148 sentence.

## 9. Delivery and rollout

- **Branch:** `docs/fix-151-approval-phrase-windows` (already exists, cut from
  `dev`). Merged **only via PR** — never on `dev`/`main` directly, no tag, no
  release (branch-flow rule; releases are tag-driven and irrelevant to docs).
- **Commits:** exactly one commit containing **both** files (C2/§13 — ES mirror in
  the same commit).
- **PR:** `.github/PULL_REQUEST_TEMPLATE.md` with every section filled, actual
  command output in Verification (grep outputs + snippet-execution output if a
  Windows host was available; otherwise the §7.5 gate result), and the SDD
  artifacts section pointing at this change's `proposal.md`, `specs/no-delta.md`,
  `design.md`.
- **Rollout:** none needed — documentation-only, no runtime surface.
- **Rollback:** `git revert` of the single docs commit. No spec/behavior rollback
  exists or is needed.
- **Archive note:** sync phase must verify a no-op (`openspec/specs/**` clean) and
  **not** write a `sync-report.md`; record `## Spec Sync → None — no delta was
  authored for this change` in the archive report (precedent:
  `2026-09-09-fix-mcp-hf-token-fallback/archive-report.md`; see `no-delta.md` §6).

## 10. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| PowerShell snippet breaks on Windows PowerShell 5.1 (default) despite the portable form | Med | §3 D2/D4 documented-availability matrix; **mandatory** §7.5 execution gate on BOTH runtimes before the PR; fence comment states the portability contract |
| README prose overstates `setx` (current shell, security, scope) | Med | C6 + N2/N6 — exactly the four Microsoft-documented claims, verified by the §7.2 `setx` presence grep being the *only* new `setx` occurrences |
| New block reads as duplication of #148 (restart/launcher themes appear 3×) | Med | D1 placement minimizes adjacency; W3/W5 phrased setx-causal, never verbatim; §7.3 single-occurrence greps prove byte-identity, "+0 deletions" diff proves addition-only |
| Fence comment reintroduces `RNGCryptoServiceProvider`/`ToHexString` literals | Low | D5 — descriptive wording; §7.1 hard-zero greps are line-local and catch it |
| ES mirror drifts or lands later | Med | Same commit (C2); §6.2 exact anchors; fence byte-identical EN↔ES; §7.3 mirror guards |
| Wording pre-empts open #144/#145 (approval-posture area) | Low | N7 — no claim beyond current code/spec; additive only |
| A reviewer treats the docs diff as trivially safe and skips the §7.5 gate | Med | Gate is PR-blocking by design (§7.5), recorded in the PR description |

## 11. Out of scope (guardrails)

- Any code, behavior, config, test, or spec change (C1, D8).
- Every merged #148 baseline sentence in the hardening section — read-only (C4).
- `docs/**`, `CONTRIBUTING.md`, `README` sections outside the hardening region,
  TOC, `TRACE.md`, `SOFER_TRACE.md`, `.gitignore` — untouched.
- Issues #144/#145 (approval diagnostics / posture) — no speculative wording.
- The `python -c "secrets…"` fallback generation path (rejected/deferred, N5).
- A docs-conformance requirement + its grep test — recorded follow-up candidate
  (`specs/no-delta.md` §5), deliberately not created.

## 12. Traceability to proposal success criteria

| Proposal criterion | Where handled here |
|---|---|
| AC1 — PowerShell generation path via portable `.NET` crypto RNG (no deprecated/7+-only forms) + `setx SOFER_MCP_APPROVAL_PHRASE <value>` cmd note with persistence caveats | D2/D7, W1/W4/W7, §6.1, §7.2 |
| AC2 — session-scope vs launcher env + `setx` + full restart + "running server never re-reads" + pointer (not restatement) to `sofer_auth_status` → `approval_configured` | W2/W3/W5/W6, D3/D6, §6.1 |
| AC3 — `README_ES.md` mirrors all additions in the same commit, prose Spanish, tokens English, parity preserved | C2, §4.4, §6.2/§6.3, §7.3 |
| No change to any #148 baseline sentence; zero weak/optional phrasing re-introduced | C4, N4, §7.1 (hard-zero) + §7.3 (single-occurrence) |
| Zero changes outside both READMEs (+ SDD artifacts) | C1, §8, §7.3 (`git status --short`) |
| Suite passes unchanged; `git diff --check` clean | C8, §7.4 |
| Positive greps pass in both files; `RNGCryptoServiceProvider` absent | §7.1/§7.2 |