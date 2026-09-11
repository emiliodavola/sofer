```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:0c754720485abc1478d8920c36513c85387fce707d72f50c0c2d6d8360abc7ac
# sha256 of `git diff` (README.md + README_ES.md) — verified against the working
# tree on branch docs/fix-readme-fail-closed-publish; the same blobs shipped in
# commit 1ad9837 (README.md e7cfba34, README_ES.md c9fbb51c), so the verdict
# carries over unchanged to the delivered PR (#156).
artifact_blobs:
  README.md: e7cfba3468b6b1dd6f9a40156b9f0e1c6b71e192
  README_ES.md: c9fbb51c5e6ff587369428e3e3fe1798fb9565c4
verdict: pass
blockers: 0
critical_findings: 0
requirements: 0/0           # no-delta change: no requirement delta introduced
scenarios: 0/0              # no-delta change: no new scenario introduced
warnings: 0
acceptance_criteria: 8/8    # issue #148 criteria (proposal *Success Criteria*)
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_result: 1468 passed, 6 skipped, 13 warnings
build_command: uv run ruff check src/ tests/ && uv run mypy src/ && git diff --check
build_exit_code: 0
```

## Verification Report

**Change**: `2026-09-11-fix-docs-fail-closed-publish` (fixes GitHub #148)
**Version**: N/A — docs-only, no spec delta (`specs/no-delta.md`)
**Branch**: `docs/fix-readme-fail-closed-publish` (working tree, **no commit yet**)
**Mode**: Standard (`openspec/config.yaml` → `strict_tdd: false`) — Strict TDD inactive; prose-only diff, no RED/GREEN cycle exists. The existing fail-closed tests are the executable proof of the documented behavior and were verified **unmodified**.

### Status / actionContext consumed

| Field | Value | Verdict |
|---|---|---|
| `artifactStore` | `openspec` (repo-local) | matches `planningHome` |
| `actionContext.mode` | `repo-local` | OK — no `workspace-planning` gate applies |
| `allowedEditRoots` | `[C:\Users\elaze\Desktop\sofer]` | every modified file is inside the root; only `README.md` / `README_ES.md` were touched |
| `blockedReasons` | `["domain specs are missing or partial."]` | **FALSE POSITIVE — see below** |
| `applyState` | `blocked` | same false positive (spec-delta heuristic) |

**Stale-engine reconciliation (blocker for archive, not for this pass).** The engine derives
`artifacts.specs: missing` from the absence of a `## ADDED`/`## MODIFIED` delta file. This change
*ships no delta by design*: `specs/no-delta.md` §3 records the approved "No delta" verdict, and
`design.md` D6 states the requirement because MSP-R05 (`openspec/specs/mcp-server/spec.md:137`),
10.3 (`:390`), 10.8 (`:424`) and MCP-REG-01 (`mcp-registration/spec.md:19`) already mandate the
behavior the README now describes. All three apply inputs (tasks, design, spec verdict) exist.
The engine's `applyState: blocked` / `sync` / `archive` states must be reconciled before archive
(the archive step must not fail on "missing specs" for a no-delta change).

### Completeness — task checkboxes

| Metric | Value |
|---|---|
| Tasks total rows | 30 (28 implementation-owned + 2 parent-owned) |
| Implementation rows checked | 25 / 28 |
| Parent rows | 2 / 2 unchecked (deferred, `sdd-owner: parent`) |
| `tasks.md` `[x]` count | 25 |
| `tasks.md` `[ ]` count | 5 (3 implementation + 2 parent) |

**Exact unchecked implementation task lines (CRITICAL archive blockers — delivery phase, explicitly withheld by the parent so verify consumes the working-tree diff):**

```text
- [ ] 4.1 Stage and commit `README.md` + `README_ES.md` **together in the same commit** (AGENTS.md §13, design C2) with a message naming issue #148 and the docs-only scope. Pre-commit ruff + mypy run automatically — do not use `--no-verify`. <!-- sdd-owner: implementation -->
- [ ] 4.2 Push the dedicated branch and open a PR into `dev` (never `main`/`dev` directly). Fill every section of `.github/PULL_REQUEST_TEMPLATE.md` with **actual command output** from Phase 3 (hard-zero greps, presence greps, `git status --short`, pytest tail, ruff/mypy, `git diff --check`) and list this change's SDD artifact paths in the mandatory *SDD artifacts* section (AGENTS.md §11). <!-- sdd-owner: implementation -->
- [ ] 4.3 Confirm the PR diff shows matching changes in both READMEs region-by-region, and that no `src/`/`tests/`/`docs/`/`TRACE.md`/scope-guard file appears in it. Do not merge without human approval at the delivery gate. <!-- sdd-owner: implementation -->
```

Deferred parent rows (recorded, not this phase's work):

```text
- [ ] 5.1 Run the bounded post-apply review over the PR diff, using design §4.1/§4.2 (W/N tables) as the review checklist: every W-claim present in both languages, zero N-claims, no invented token, ES mirror complete and same-commit. <!-- sdd-owner: parent -->
- [ ] 5.2 Confirm the lifecycle gate: human approval of the PR before merge, `dev`-only target, and no release/tag step for this docs-only change (proposal *Delivery*, design §9). <!-- sdd-owner: parent -->
```

**Archive readiness: BLOCKED.** The content verification below passes cleanly, but archive must
wait for 4.1–4.3 (commit + PR) and the two parent lifecycle rows. These are **not** "stale
checkboxes": they are genuinely not done, and 4.1 additionally materializes the design C2
"both READMEs in the same commit" invariant, which is currently **unprovable** (see criterion 5).

### Requirements / scenarios checked

**No-delta change — nothing to map.** Per `specs/no-delta.md`, no requirement or scenario is added,
modified, or removed, so the spec compliance matrix is intentionally empty. What *was* verified is
the **normative standard the README must now match** (design C3 — no claim beyond existing normative text):

| Normative source | Line | What it mandates | README must state it | Result |
|---|---|---|---|---|
| `openspec/specs/mcp-server/spec.md` MSP-R05 | :137 | phrase mandatory; empty/whitespace normalized to unconfigured; refusal `PUBLISH_APPROVAL_NOT_CONFIGURED`; upload never reached; acknowledgment booleans never sufficient | W1, W2, W3 | ✅ matched |
| `openspec/specs/mcp-server/spec.md` 10.3 | :390 | `PUBLISH_APPROVAL_NOT_CONFIGURED` and `PUBLISH_APPROVAL_REQUIRED` are first-class envelope codes | W2, W9 | ✅ matched |
| `openspec/specs/mcp-server/spec.md` 10.8 | :424 | `requires_approval_phrase` always `true`; `approval_configured` = non-blank phrase; blank ⇒ unconfigured | W8 | ✅ matched |
| `openspec/specs/mcp-registration/spec.md` MCP-REG-01 | :19 | gemini `env` / codex `env_vars` persist env **NAMES only**, secrets never written to disk | W6 (names-only half) | ✅ matched |

**Scenarios NOT applicable (recorded, per `specs/no-delta.md` §3):** every MSP-R05 / 10.3 / 10.8 /
MCP-REG-01 scenario is already covered by the existing suite and is untouched by this change. No
new scenario is claimed; no spec file was written (`openspec/specs/**` unchanged, verified below).

### Acceptance greps re-run independently (design §7)

**Hard-zero (§7.1) — must print nothing:**

```text
$ grep -n "weaker posture\|when configured\|acknowledgment booleans" README.md
(no output, exit 1)                                  # baseline was README.md:646,672,673
$ grep -n "configurada — una frase\|postura más débil\|booleanos de reconocimiento" README_ES.md
(no output, exit 1)                                  # baseline was README_ES.md:681,708,709
$ grep -ni "weaker\|when configured\|only the two\|solo los dos\|cuando está configurada\|postura más débil" README.md README_ES.md
(no output, exit 1)                                  # widened, independent re-check
```

6 → 0 against the task 0.2 baseline, confirmed by an independent widened pattern. ✅

**Presence (§7.2) — each ≥ 1 hit in each file:**

```text
$ grep -c "PUBLISH_APPROVAL_NOT_CONFIGURED" README.md README_ES.md
README.md:3        README_ES.md:3
$ grep -n "approval_configured" README.md README_ES.md
README.md:691      README_ES.md:726
$ grep -n "SOFER_MCP_APPROVAL_PHRASE" README.md README_ES.md
README.md:320,619,674,679        README_ES.md:332,652,709,714
$ grep -n "once at process start" README.md
README.md:678
$ grep -n "una sola vez al iniciar el proceso" README_ES.md
README_ES.md:713
```

**Anti-regression N3 (§7.3) — no CLI over-claim:**

```text
$ sed -n '663,700p' README.md | grep -n "sofer publish"        # (no output, exit 1)
$ sed -n '698,735p' README_ES.md | grep -n "sofer publish"     # (no output, exit 1)
```

Every `SOFER_MCP_APPROVAL_PHRASE` hit is outside the `sofer publish` examples.
Section attribution of each hit (EN): `:320` = `## Command reference` → the `mcp add` row
(accurate: `mcp add` *does* forward env names — not a publish-gate claim); `:619,674,679` =
`## AI and MCP server`. Lines `:170` (typical-workflow `sofer_auth_status` preflight) and `:320`
are pre-existing and make no optionality claim. **No occurrence inside `## Command reference`'s
`sofer publish` examples.** ✅

**Mirror guard / heading parity (§13):**

```text
$ for l in 1 2 3 4:  h1 EN=49 ES=49 | h2 EN=17 ES=17 | h3 EN=17 ES=17 | h4 EN=0 ES=0
$ grep -c '^#' README.md README_ES.md    -> 84 / 84
$ git diff -U0 | grep -E "^[+-]#"        -> (empty: no heading line added/removed/renamed)
```

Heading counts equal per level, order preserved (`### Security model` → `### Hardening for
sensitive hosts` ↔ `### Modelo de seguridad` → `### Endurecimiento para hosts sensibles`), no
heading text changed ⇒ no anchor churn. The one new intra-page link in each file resolves:

```text
README.md:585     ### Register sofer-mcp with AI agents (opencode, codex, gemini)
README_ES.md:618  ### Registrar sofer-mcp con agentes de IA (opencode, codex, gemini)
link targets:     (#register-sofer-mcp-with-ai-agents-opencode-codex-gemini)
                  (#registrar-sofer-mcp-con-agentes-de-ia-opencode-codex-gemini)
```

### Claim → evidence traceability (W1–W10, re-verified from source, not from the report)

| # | Claim in the new README text | Independent source evidence | Verdict |
|---|---|---|---|
| W1 | Phrase is mandatory for every HF publish via `sofer_publish_confirm`; the two `acknowledge_*` flags are never sufficient | `src/sofer/mcp_server.py:1063` (`"ALWAYS required for publish"`), `:1148` (`if _APPROVAL_PHRASE is None:`), `:1152-1154` (`"the acknowledgment booleans are ADDITIONAL gates, never sufficient on their own"`), `:167`; spec MSP-R05 `:137` | ✅ verified |
| W2 | No phrase ⇒ refusal `PUBLISH_APPROVAL_NOT_CONFIGURED`, upload disabled entirely | `mcp_server.py:1148-1158` (`_error_envelope("PUBLISH_APPROVAL_NOT_CONFIGURED", …)` before any upload); spec `:137`, `:390`; test `test_no_phrase_configured_refuses_fail_closed` asserts `upload_calls == []` | ✅ verified |
| W3 | Empty / whitespace-only counts as unconfigured | `mcp_server.py:2648` `_APPROVAL_PHRASE = raw_phrase if raw_phrase and raw_phrase.strip() else None`; spec `:424` ("empty or whitespace-only … MUST be treated as unconfigured") | ✅ verified |
| W4 | Comes from `build_server(root, approval_phrase=...)` or `SOFER_MCP_APPROVAL_PHRASE` | `mcp_server.py:2637-2642` (`approval_phrase if … else os.environ.get("SOFER_MCP_APPROVAL_PHRASE")`) | ✅ verified |
| W5 | Read once at process start, immutable for that process; restart the launching host after a change | `mcp_server.py:217` module-level `_APPROVAL_PHRASE` (single project-wide env read site is `:2642`, only reachable from `build_server`); error message `:1155` "set `SOFER_MCP_APPROVAL_PHRASE` and restart"; `design.md` D4 | ✅ verified |
| W6 | codex `env_vars` / gemini `env` persist env **names only**; opencode receives no env from `sofer mcp add`; opencode literal form is plaintext on disk | `mcp_registration.py:140-144` docstring ("opencode: no env forwarding (returns minimal entry)"); `:158-161` opencode returns `{"type":"local","command":["sofer-mcp"],"cwd":…}` with **no** env; `:442` `_ENV_KEYS = ["HF_TOKEN","SOFER_MCP_APPROVAL_PHRASE"]`; spec MCP-REG-01 `:19`; **`environment` key verified against the upstream opencode config schema** (`https://opencode.ai/config.json`: MCP `local` entry → `"environment": {object of string}` — "Environment variables to set when running the MCP server"), opencode 1.18.30 installed locally | ✅ verified (one token from upstream schema — see SUGGESTION 2) |
| W7 | Windows: the variable must be in the **launcher's** environment and the host fully restarted | Same evidence as W5 (env is read at process start from the launcher's environment); `design.md` D4 | ✅ verified |
| W8 | Verify with `sofer_auth_status(config)` → `approval_configured`; `requires_approval_phrase` always `true` | `mcp_server.py:1662` `approval_configured = _APPROVAL_PHRASE is not None`; `:1663` `requires_approval_phrase = True`; `:1691-1692` both in the envelope; spec 10.8 `:424` | ✅ verified |
| W9 | `PUBLISH_APPROVAL_NOT_CONFIGURED` = no phrase on the server; `PUBLISH_APPROVAL_REQUIRED` = phrase missing/mismatched in the call | `mcp_server.py:1148` vs `:1166` (`if approval_phrase is None or not hmac.compare_digest(...)`) — two distinct branches/verdicts; spec 10.3 `:390` | ✅ verified |
| W10 | `openssl rand -hex 16` example and the `export … ; sofer-mcp` fence retained | `git diff` shows the fence as unchanged context (`README.md:674-676`, `README_ES.md:709-711`) | ✅ verified |

**N-claims (forbidden) — all re-checked, none present:**

```text
N1 "weaker posture / trusted single-user stdio"      -> hard-zero greps empty (both files)          ✅ absent
N2 "when configured / optional phrase"               -> hard-zero greps empty; Security-model bullet rewritten ✅ absent
N3 "the CLI (sofer publish) needs a phrase"          -> zero "sofer publish" in the changed regions; new text says
                                                        sofer_publish_confirm only                  ✅ absent
N4 "the secret value is stored on disk by mcp add"   -> text says names-only and flags the opencode literal as
                                                        plaintext on disk (the opposite claim)      ✅ absent
N5 #144/#145/#151 pre-emption / envelope diagnostics -> region scan for #144|#145|#151|diagnostic|envelope: empty ✅ absent
N6 per-host restart recipe                           -> generic "fully restart the agent host" only ✅ absent
N7 hardcoded phrase length / algorithm / rotation    -> none; only the pre-existing openssl rand -hex 16 (W10)   ✅ absent
```

### Diff audit — docs-only (C1, §7.3, §7.9)

```text
$ git branch --show-current
docs/fix-readme-fail-closed-publish
$ git status --short
 M README.md
 M README_ES.md
?? openspec/changes/2026-09-11-fix-docs-fail-closed-publish/   (this change's own SDD artifacts — expected)
$ git diff --stat
 README.md    | 34 ++++++++++++++++++++++++++++------
 README_ES.md | 36 ++++++++++++++++++++++++++++--------
 2 files changed, 56 insertions(+), 14 deletions(-)
$ git diff --check
(clean, exit 0)
```

Hunks (`git diff -U0`): 3 in `README.md` (security-model clause + hardening body) and 3 in
`README_ES.md` (same two regions, ES) — **exactly the four regions of `design.md` §8**. Zero files
under `src/`, `tests/`, `docs/`, `openspec/specs/`, `TRACE.md`, `scratch/`, `.gitignore`; no test
file modified (`git status --short tests/ src/` → empty). **56+14 = 70 changed lines = 17.5 % of
the 400-line review budget.**

### Build & tests — actual output (re-run by verify)

```text
$ uv run pytest tests/ -q
1468 passed, 6 skipped, 13 warnings in 51.98s                       (exit 0)
$ uv run pytest tests/test_mcp_server.py -q -k "fail_closed or approval or auth_status"
4 passed, 183 deselected in 1.30s                                   (exit 0)
$ uv run pytest "tests/test_mcp_server.py::TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed" \
                "tests/test_mcp_process.py::TestDeliveryHandoff::test_handoff_pipeline_reaches_upload_branch" -q
2 passed in 1.33s                                                   (exit 0)
$ uv run ruff check src/ tests/
All checks passed!                                                  (exit 0)
$ uv run mypy src/
Success: no issues found in 32 source files                         (exit 0)
$ git diff --check
clean                                                               (exit 0)
```

The suite count **matches the apply claim exactly** (1468 passed / 6 skipped) and the 70-line diff
is prose-only. `ruff`/`mypy` are genuine no-ops as required by design §7.4 (docs-only change).

**Fail-closed pins — present, unmodified, green (C8, D6):**

| Pin | Location | Verified |
|---|---|---|
| `test_no_phrase_configured_refuses_fail_closed` | `tests/test_mcp_server.py:750` (docstring `:753-758`, asserts `:783`ff: `PUBLISH_APPROVAL_NOT_CONFIGURED`, `exit_code == 1`, `upload_calls == []`) | ✅ exists, file unmodified, 1 passed |
| `test_handoff_pipeline_reaches_upload_branch` | `tests/test_mcp_process.py:559` (fail-closed approval-gate comment/assert `:620-621`) | ✅ exists, file unmodified, 1 passed |

These two tests are the **executable proof the corrected prose is true**: a server with no phrase
refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reaches the upload, while a
correctly-phrased call on a configured server succeeds. No test was edited to accommodate wording.

### Strict TDD compliance

**Inactive — not applicable.** `openspec/config.yaml:13` → `strict_tdd: false` (also repeated at
`:16`). `apply-progress.md` declares "Strict TDD: inactive … prose-only change, no RED/GREEN
cycle", which is consistent with the artifact store's configuration. Consequently:

- No `TDD Cycle Evidence` table is required or expected.
- No assertion-quality audit applies (no test file was created or modified — confirmed by
  `git status --short tests/` → empty).
- The behavioral truth of the documentation rests on the two pre-existing pins above, which were
  re-run unmodified by this pass.

### Review workload / PR boundary

| Field | Forecast (`tasks.md`) | Actual | Verdict |
|---|---|---|---|
| Estimated changed lines | ~70 | 70 (56 insertions + 14 deletions) | ✅ on estimate |
| 400-line budget risk | Low | 17.5 % of budget | ✅ |
| Chained PRs recommended | No | single branch `docs/fix-readme-fail-closed-publish` → `dev` | ✅ |
| `size:exception` | not requested / not needed | none recorded, none needed | ✅ correctly absent |
| Chain strategy | `pending` (chaining not required) | n/a — single slice | ✅ consistent |
| Scope creep beyond assigned tasks | — | none: only the 4 forecast regions changed | ✅ |

The PR/work boundary matches the forecast: a single docs-only slice, well inside budget, no
chaining, no exception.

### Acceptance criteria — issue #148 (proposal *Success Criteria*)

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | README describes fail-closed posture: phrase **mandatory**, unconfigured server refuses with `PUBLISH_APPROVAL_NOT_CONFIGURED` | ✅ **PASS** | `README.md:666-673` (+ `:648-651` security-model bullet always-in-force); W1/W2 evidence above; hard-zero + presence greps |
| 2 | Read once at process start, requires host restart to change; verify via `sofer_auth_status` → `approval_configured` (+ `requires_approval_phrase` always true) | ✅ **PASS** | `README.md:678-688` and `:690-695`; `mcp_server.py:217,2637-2648,1662-1663`; `spec.md:424` |
| 3 | Per-agent configuration (codex `env_vars`, gemini `env`, opencode launcher env / `environment` literal + plaintext caveat) and Windows launcher-env + full-restart note | ✅ **PASS** | `README.md:680-689`; `mcp_registration.py:140-161,442`; `spec.md (mcp-registration):19`; opencode `environment` key verified against the upstream schema |
| 4 | **No** surviving text implying the booleans suffice or the phrase is optional (`"when configured"` removed) | ✅ **PASS** | Hard-zero greps empty (narrow + widened) in both files; 6 → 0 vs baseline; both defective regions rewritten |
| 5 | `README_ES.md` mirrors both edits **in the same commit**, prose ES / tokens EN, heading parity + order preserved | ⚠️ **PASS (content) / UNPROVABLE (same-commit)** | Mirror is complete and region-identical; tokens stay English; parity 17/17 `###`, 84/84 `#`, no heading change. The **same-commit** half cannot be proven yet — there is no commit (blocked by task 4.1). Content is ready; the invariant materializes only when 4.1 lands |
| 6 | Zero changes to `src/`, `tests/`, `docs/`, `TRACE.md`, `openspec/specs/` | ✅ **PASS** | `git status --short` → only `README.md`, `README_ES.md`, plus the change's own untracked SDD dir |
| 7 | `uv run pytest tests/ -q` passes unchanged; `mypy` unaffected; `git diff --check` clean | ✅ **PASS** | 1468 passed / 6 skipped (re-run, matches baseline); mypy 32 files clean; ruff clean; `git diff --check` clean |
| 8 | No leftover `"weaker posture"` / `"postura más débil"` in either README | ✅ **PASS** | Hard-zero greps empty; widened pattern also empty |

**8 / 8 acceptance criteria pass** (criterion 5's delivery half is the pending 4.1 task, not a
content failure).

### Documented deviations — independently re-measured

| # | Deviation (apply-progress) | Independent measurement | Verdict |
|---|---|---|---|
| 1 | Two >80-column lines, both unbreakable inline Markdown links | Measured **every added line** (`git diff -U0` → new line numbers → character length): `README.md` added=28 over80=1 → **L682 = 95 chars**; `README_ES.md` added=28 over80=1 → **L717 = 108 chars**. Both are the mandated intra-page links. Every other added line is ≤ 80 **characters**. | ✅ Claim is accurate and complete. Note: a naive byte-length check (awk/POSIX) flags `README.md:691` (82 bytes) and 2 ES lines — these are 80/`≤80` **characters** and their excess is only multi-byte `→`/`—`, i.e. not real violations. |
| 2 | Line numbers shifted (+2/+17) after the edits | Confirmed: the added-line ranges are `README.md` 643-651 and 663-698; `README_ES.md` 677-686 and 698-733. Heading order/pairing preserved. | ✅ |
| 3 | ES re-wrap around the security-model clause (content unchanged) | Confirmed in the diff: only the clause sentence changed; the `HF_TOKEN` → … token-resolution chain remains byte-identical context. | ✅ |
| 4 | No new env var / flag / error code / heading / TOC edit / test | Confirmed: `git diff -U0 \| grep -E "^[+-]#"` empty (no heading lines); no new tokens beyond W-table tokens; `tests/` untouched. | ✅ |

### Issues

**CRITICAL**: none in the verified content.

**CRITICAL (archive blockers, process — 3):** unchecked implementation tasks `4.1`, `4.2`, `4.3`
(exact lines reproduced above). They are the delivery phase (commit both READMEs together, push +
PR into `dev`, confirm the PR diff), withheld by explicit parent instruction for this pass. Until
they land, `design.md` C2 / AGENTS.md §13 "same commit" is **unprovable**, and `nextRecommended`
must not be `sdd-archive`.

**WARNING**: none.

**SUGGESTION** (non-blocking):

1. **Reconcile the stale-engine spec heuristic before archive.** The engine's
   `blockedReasons: ["domain specs are missing or partial."]` / `applyState: blocked` is a
   false positive for a `no-delta` change. The archive step should be told the
   `specs/no-delta.md` verdict so it doesn't treat `artifacts.specs: missing` as a blocker. If the
   engine cannot express "no delta", record the exemption in the archive note.
2. **Traceability of the `environment` token (W6).** `design.md` §5 traces W6 only to
   `mcp-registration/spec.md:19` + `README.md:619-621`, but the opencode `environment` key is not
   in this repo — it comes from the upstream opencode config schema (`mcp.<name>.environment` for
   `type: "local"`). I verified it against `https://opencode.ai/config.json` (opencode 1.18.30).
   The README text is accurate; consider citing the upstream schema in the design's traceability
   block so a future reviewer can re-verify without network archaeology.
3. **Column-count convention for future acceptance greps.** The `≤ 80 columns` rule is checked in
   *characters* here while POSIX tooling measures *bytes*; the two disagree on lines containing
   `→`/`—`. AGENTS.md-style self-checks should state the unit explicitly to avoid a false FAIL in
   a future run.

### Verdict

**PASS (content) — archive BLOCKED.** All 8 issue-#148 acceptance criteria pass on the working
tree; the hard-zero greps are empty (6 → 0) and independently re-confirmed with a widened pattern;
every new claim traces to `src/sofer/mcp_server.py`, the live specs, or (for the single upstream
token) the opencode config schema — no over-claim, and **zero** N1–N7 forbidden claims; the diff is
docs-only (2 files, 70 lines, 17.5 % of budget, exactly the 4 forecast regions); the ES mirror is
complete with English technical tokens and preserved heading parity; `1468 passed / 6 skipped`,
`ruff`, `mypy`, and `git diff --check` are all green with the two fail-closed pins unmodified and
green. Strict TDD is inactive by configuration (`strict_tdd: false`) and no test file changed.
Archive is blocked solely by the three unchecked delivery tasks (4.1–4.3) plus the two parent
lifecycle rows — the "same commit" invariant (criterion 5) cannot be proven until 4.1 lands, and
the engine's `missing specs` blocker must be reconciled first.
