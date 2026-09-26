```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4a01a3e883fa91bb2f7d11eda7239bd6d00b2d0fb2376378db10d97f7902a1b1
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 9/9
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:6e8173a9be3005870246d7123c9b4663fee2a02e3162cfbf5f511b854e6410e5
build_command: uv run ruff check src/ tests/ scripts/ && uv run ruff format --check src/ tests/ scripts/ && uv run mypy src/ scripts/
build_exit_code: 0
build_output_hash: sha256:04f8b4efce0225c2bf8604d53c37d00e1d6b12a2b81c9ccc6f3530791138570c
```

# Verify report — `2026-09-15-chore-ruff-single-authority` (GitHub issue #195)

**Status: PASS** — 0 blockers, 0 critical findings. Every gate was re-derived by this phase with its own
commands; no figure in this report is copied from `apply-progress.md`.

**Change**: `2026-09-15-chore-ruff-single-authority` · branch `chore/195-ruff-single-authority` (from
`dev@5a2ae38`) · store **hybrid** — this file plus the Engram record under topic key
`sdd/2026-09-15-chore-ruff-single-authority/verify-report`.
**Inputs read this phase**: `proposal.md`, `preproposal.md`, `explore.md`, `design.md`, `tasks.md`,
`apply-progress.md`, `sync-report.md`, both change-root deltas (`specs/ci/spec.md`,
`specs/process-boundary/spec.md`), the two canonical specs they land in, and the changed production files.
**Strict TDD**: not active (`strict_tdd: false`) — see § Task completion and TDD.
**Edit scope honoured**: this phase wrote only `verify-report.md` and persisted the Engram record.
`tasks.md` needed no edit (0 unchecked implementation rows — § Task completion). No canonical spec under
`openspec/specs/**` was touched. No commit, no push.

## 1. Evidence digest definitions (reproducible)

The envelope's three digests are defined so any reader can reproduce them:

| Envelope field | Definition (exact) | Value |
| --- | --- | --- |
| `evidence_revision` | `sha256` of the concatenation `git diff` (all tracked changes) followed by `sha256sum` of the two change-root delta spec files | `sha256:4a01a3e883fa91bb2f7d11eda7239bd6d00b2d0fb2376378db10d97f7902a1b1` |
| `test_output_hash` | `sha256` of the complete stdout+stderr of `uv run pytest tests/ -q` as run in this phase | `sha256:6e8173a9be3005870246d7123c9b4663fee2a02e3162cfbf5f511b854e6410e5` |
| `build_output_hash` | `sha256` of the complete stdout+stderr of the `build_command` chain below | `sha256:04f8b4efce0225c2bf8604d53c37d00e1d6b12a2b81c9ccc6f3530791138570c` |

`build_command` note: this repository has **no compile/build step** (pure Python, hatch-vcs version at build
time, nothing compiled in the repository tree). The enforced static-gate chain that CI runs
(`ci.yml:19,21`; `release.yml:29,32`) is reported in the `build_*` row instead, and it was run exactly as
written above: exit 0.

```console
$ uv run ruff check src/ tests/ scripts/ && uv run ruff format --check src/ tests/ scripts/ && uv run mypy src/ scripts/
All checks passed!
68 files already formatted
Success: no issues found in 33 source files
# exit=0
```

## 2. Structured status and actionContext findings

| Field | Value consumed | Finding |
| --- | --- | --- |
| `changeName` | `2026-09-15-chore-ruff-single-authority` | Matches the change root and every artifact. No finding. |
| `artifactStore` | `openspec` (native) / `hybrid` (session preflight) | The parent prompt states hybrid, so both backends were written: this file **and** the Engram record. No conflict — `openspec` is the native projection, `hybrid` adds the Engram mirror. |
| `planningHome.mode` | `repo-local` | Change root resolves inside the repository. No finding. |
| `actionContext.mode` | `repo-local` | **No `workspace-planning` gate applies.** No `allowedEditRoots` requirement was triggered. |
| `actionContext.workspaceRoot` | `C:\Users\elaze\Desktop\sofer` | The authoritative root. Every path read and the two paths written are inside it. |
| `actionContext.allowedEditRoots` | `["C:\Users\elaze\Desktop\sofer"]` | Satisfied: `verify-report.md` and the Engram record are the only writes. |
| `taskProgress` | `total: 45, completed: 45, pending: 0, allComplete: true` | **Re-derived and confirmed**: `grep -cE '^\s*- \[x\]' tasks.md` → 45; `grep -cE '^\s*- \[ \]' tasks.md` → 0. |
| `dependencies.verify` | `ready` | Verification was authorised. |
| `dependencies.archive` | `blocked` | Consistent with this phase: the verify report did not exist at launch, and the two canonical specs still do not carry the deltas. |
| `blockedReasons` | `[]` | Nothing was blocked. |
| Active attempt | ordinal 2, work unit *"ruff single authority: independent verification of apply evidence"*, `state: proceed`, `max_changed_lines: 400` | Matches this launch. No new acquire was made; the parent-held token was used. |

**Action-context guard result**: implementation ownership and every changed path are provably inside the
authoritative workspace, in `repo-local` mode. No scope gate fired.

## 3. Re-derived gate table (own commands, own outputs)

| # | Gate | Exact command | Result | Exit | Verdict |
| --- | --- | --- | --- | --- | --- |
| G1 | Full suite | `uv run pytest tests/ -q` | `1784 passed, 6 skipped, 1 warning in 58.14s` | 0 | PASS |
| G2 | Guard module | `uv run pytest tests/test_ci_workflows.py -q` | `22 passed in 0.12s` | 0 | PASS |
| G3 | Lint (enforced scope) | `uv run ruff check src/ tests/ scripts/` | `All checks passed!` | 0 | PASS |
| G4 | Format check (enforced scope) | `uv run ruff format --check src/ tests/ scripts/` | `68 files already formatted` | 0 | PASS |
| G5 | Types (enforced scope) | `uv run mypy src/ scripts/` | `Success: no issues found in 33 source files` | 0 | PASS |
| G6 | Types (AC4 literal wording) | `uv run mypy src/` | `Success: no issues found in 32 source files` | 0 | PASS |
| G7 | Pinned binary in the venv | `uv run ruff --version` | `ruff 0.16.7` | 0 | PASS |
| G8 | Lock consistency | `uv lock --check` | `Resolved 106 packages in 1ms` | 0 | PASS |
| G9 | Coverage (rule 14) | `uv run coverage run -m pytest` then `bash scripts/check_core_coverage.sh` | `1784 passed, 6 skipped`; four scoped rows at `100%`, empty `Missing`; script exit 0 | 0 | PASS |
| G10 | CI-08 S4 leg A (declared value) | `uv run ruff check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/ scripts/` | both clean | 0 / 0 | PASS |
| G11 | CI-08 S4 leg B (mismatch probe) | `uv run ruff check --config <out-of-tree probe> src/ tests/ scripts/` and the same with `--config` on `ruff format --check` | both `ruff failed … Required version \`==99.0.0\` does not match the running version \`0.16.7\`` | 2 / 2 | PASS |
| G12 | No CI format gate | `grep -rn 'format --check' .github/workflows/` and `grep -rn 'format' .github/workflows/` | 0 matches, both | 1 (no match) | PASS |
| G13 | Diff scope | `git diff --name-only` | exactly `CONTRIBUTING.md`, `pyproject.toml`, `tests/test_ci_workflows.py`, `uv.lock` | 0 | PASS |

**G9 raw rows** (`bash scripts/check_core_coverage.sh`, exit 0):

```text
Name               Stmts   Miss Branch BrPart  Cover   Missing
src\sofer\cli.py     580      0    166      0   100%
Name                   Stmts   Miss Branch BrPart  Cover   Missing
src\sofer\scanner.py     159      0     76      0   100%
Name                   Stmts   Miss Branch BrPart  Cover   Missing
src\sofer\prepare.py     325      0    180      0   100%
Name                   Stmts   Miss Branch BrPart  Cover   Missing
src\sofer\publish.py     326      0    138      0   100%
```

All four rule-14 rows are at **100%** with an empty `Missing` column, and the TOTAL floor remains the
config-owned `fail_under = 90` (`ci` CI-01) — unweakened, not re-declared.

**Tally delta, re-derived against the pre-change tree** (`git show HEAD:tests/test_ci_workflows.py`)
rather than against `apply-progress.md`: the pre-change module held **19** `def test_` functions; the working
tree holds **22**. The suite delta is therefore exactly **+3** — matching the three CI-08 guards — with the
skip count unchanged at 6 and 0 failures. The pre-change baseline figure `1781 passed / 6 skipped` is
`apply-progress.md`'s measurement (it cannot be re-measured without reverting the change); the **+3
arithmetic is confirmed** and no figure here was copied.

## 4. Requirement coverage

Counts are taken from the retrieved delta specs — the authoritative artifacts for this change.

| Requirement | Source | Declared | Verdict |
| --- | --- | --- | --- |
| `ci` **CI-08** — Single authoritative ruff version (`## ADDED`) | `specs/ci/spec.md` | 1 requirement, **4** scenarios | SATISFIED |
| `process-boundary` **PB-10** — Formatter integrity on a clean checkout (`## MODIFIED`) | `specs/process-boundary/spec.md` | 1 requirement, **5** restated scenarios | SATISFIED |

Totals: **requirements 2/2**, **scenarios 9/9**.

### Scenario ledger (what "complete" means per row)

| Scenario | Evidence class | Independently re-derived evidence |
| --- | --- | --- |
| CI-08 S1 — Dev pin, required-version, and hook rev agree | pytest | `test_ruff_pin_hook_rev_and_required_version_agree` passes; mutation legs 1 & 2 make it RED |
| CI-08 S2 — No workflow declares a ruff version | pytest | `test_workflows_do_not_declare_a_ruff_version` passes; non-vacuity guard (`assert names`) present; 3 workflow files scanned |
| CI-08 S3 — CONTRIBUTING names the declared version | pytest | `test_contributing_names_the_declared_ruff_version` passes; mutation leg 3 makes it RED |
| CI-08 S4 — `required-version` rejects a mismatched binary | verify-phase runtime evidence (by explicit spec design) | G10 exit 0/0 and G11 exit 2/2, each message naming required `==99.0.0` and running `0.16.7` |
| PB-10 (modified clause) — single declared authority, referenced to CI-08 | static + test | The restated sentence is present; the three declarations are equal at `0.16.7`; CI-08's guards enforce it |
| PB-10's 5 restated scenarios | byte-identity (this change's only obligation toward them) | Scenario region byte-identical to canonical, `sha256 f455cfd8ccf03247da1929fa0bfc24b6dd14b59ef8ce0e8918934cacf887aade` on both sides; `5` scenarios each side |

**Explicit disclosure on the denominator.** The `9` above is the number of scenarios *declared in the two
retrieved delta specs* (CI-08's 4 + PB-10's 5). PB-10's five scenarios are history — they record the #177
formatting edit and, per the change's own scoping rule, are **not** measured against this diff. This change's
obligation toward them is byte-identity, which this phase proved by hash. Counting them as "complete" means
*"this change satisfied the obligation it holds toward them"*, not *"their assertions were re-executed"*.
Nothing here is inflated to that effect.

### PB-10 delta re-read (own extraction, own diff)

`diff -u` of the canonical PB-10 block against the delta's `## MODIFIED` block yields **exactly one hunk**:
the second body paragraph. Lines 1–5 (heading, `:254` framing blockquote, paragraph 1) are byte-identical;
the five scenarios (`:260-293`) are byte-identical by hash; the "no new CI step" clause and the
#194-ownership clause are unchanged inside the rewritten paragraph; the `(Previously: …)` note is appended.

```console
$ diff -u <canonical PB-10 block> <delta ## MODIFIED block>
@@ -4,7 +4,9 @@
 [para 1 unchanged]
-The requirement SHALL be satisfiable with no new CI step: … The ruff version pin mismatch (pre-commit
-`v0.16.7` versus the environment's `0.16.0`) SHALL stay unaddressed here and SHALL be owned by issue #195. …
+The requirement SHALL be satisfiable with no new CI step: … The ruff version SHALL have a single declared
+authority — the environment's dev dependency pin, `[tool.ruff] required-version`, and the pre-commit `rev`
+SHALL name the same version, asserted statically by the guard required by `ci` CI-08. Alignment SHALL remain
+a declaration-and-local-hook matter: it SHALL arm no CI step, and issue #194 SHALL retain ownership of the
+un-staged-file gap. …
+
+(Previously: the paragraph deferred the pin mismatch — `v0.16.7` hook versus `0.16.0` environment — to
+issue #195; change `2026-09-15-chore-ruff-single-authority` owns it, and no version literal remains in this
+spec.)

$ diff <scenario regions>          → empty
$ sha256sum <both scenario regions> → f455cfd8ccf03247da1929fa0bfc24b6dd14b59ef8ce0e8918934cacf887aade (×2)
```

**Normative version-literal invariant re-derived**: `awk … | grep -cE '0\.16\.[0-9]'` over the delta's
PB-10 normative block (header → `(Previously:`) → **0**; over the canonical PB-10 normative paragraph →
**1** (pre-sync). The invariant is **1 → 0**, discharged by `sdd-sync`. The `(Previously: …)` note carries
literals and is the **established canonical convention**, not a violation — the same shape already exists at
`openspec/specs/process-boundary/spec.md:12,63,95,115,232`. Per the change's own scoping rule, a bare
`grep "0.16"` over a whole spec file is not a check.

## 5. Acceptance criteria (issue #195, verbatim from the proposal's traceability table)

| AC | Verbatim criterion | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | "One ruff version is declared authoritative and named in `CONTRIBUTING.md` (which today does not mention a version at all)." | **SATISFIED** | `pyproject.toml:47` `"ruff==0.16.7"` (exact, `grep -c 'ruff>=' pyproject.toml` → 0); `pyproject.toml:62` `required-version = "==0.16.7"`; `.pre-commit-config.yaml:3` `rev: v0.16.7`; `CONTRIBUTING.md:77` `This project uses **ruff** 0.16.7 for linting and formatting.`; guards S1 + S3 green |
| 2 | "`.pre-commit-config.yaml`'s `rev` and `pyproject.toml`'s dev dependency agree on that version." | **SATISFIED** | `v0.16.7` vs `==0.16.7` → both `0.16.7`; `test_ruff_pin_hook_rev_and_required_version_agree` green; mutation leg 1 (rev → `v0.16.6`) turns it RED. `.pre-commit-config.yaml` genuinely needs no edit: `git diff --numstat .pre-commit-config.yaml` is empty |
| 3 | "`uv run ruff format --check src/ tests/` and the `ruff-format` hook produce the same verdict on the same file." | **SATISFIED ON SUBSTANCE — not exit-code parity** | See § 7. Both surfaces judged the same bytes unformatted; the hook rewrote them to byte-exactly the output surface A predicted; the hook's **own bundled binary** in check mode returned exit 1 with an identical message |
| 4 | "`uv run pytest tests/ -q` stays green; `ruff check` and `mypy src/` stay clean." | **SATISFIED** | G1 `1784 passed, 6 skipped … exit 0`; G3 `All checks passed!`; G6 `Success: no issues found in 32 source files` (and the enforced-scope G5 over `src/ scripts/`). Baselines preserved, nothing reduced, skip count unchanged |
| 5 | "If the pin moves, `uv.lock` is refreshed in the same change." | **SATISFIED** | See § 8 — confined to the ruff package block plus the single dev specifier; `uv lock --check` exit 0 |

## 6. Guard teeth (independent mutation probes)

Four probes were run. Each mutated exactly one declaration, observed the specific RED, was restored **by
re-editing** (never `git checkout --` on a file carrying this change's real edit), and proved byte-identical
by `sha256` of the whole file. The original floor defect was reconstructed too, which is the guard's real
teeth.

| Probe | Mutation | Observed RED | Restore proof |
| --- | --- | --- | --- |
| P1 — RED reconstruction (the historical defect) | `pyproject.toml:47` `"ruff==0.16.7"` → `"ruff>=0.9.0"` | `3 failed, 19 passed in 0.29s` — all three guards fail through the shared helper's exactness assertion at `tests/test_ci_workflows.py:114` | `pyproject.toml` `sha256 9b349ac8db3c58c0132dfdcf33cc2969fb81f6a892f619f82e53838100cbfd31` before = after; `uv.lock` untouched (`0f5bb813cec8…` before = after); module back to `22 passed` |
| P2 — hook rev | `.pre-commit-config.yaml:3` `rev: v0.16.6` | `FAILED … test_ruff_pin_hook_rev_and_required_version_agree`, `At index 0 diff: 'v0.16.6' != 'v0.16.7'` | `sha256 340e1723a77c…` before = after; module back to `22 passed` |
| P3 — `required-version` | `pyproject.toml:62` `"==0.16.6"` | `FAILED … test_ruff_pin_hook_rev_and_required_version_agree`, `+ ==0.16.6` vs `==0.16.7` | `sha256 9b349ac8…` before = after; module back to `22 passed` |
| P4 — documentation half | `CONTRIBUTING.md:77` version token removed | `FAILED … test_contributing_names_the_declared_ruff_version` | `sha256 2bf3ea3065e0…` before = after; module back to `22 passed` |

**Every leg has teeth.** No residue: after all four probes `git status --porcelain` shows exactly the four
intended tracked paths plus the untracked change root, and `git diff --numstat` is unchanged at
`1/1, 5/1, 75/5, 22/22`.

**P1 is the strongest single finding of this phase**: it independently reproduces the apply phase's RED
claim (`3 failed, 19 passed`) and proves the three guards fail on the *actual historical defect* — a floor
specifier, not merely a version mismatch. It also confirms the pre-change module size (19 tests) against the
real file, since the probe was run with `uv`'s re-lock bypassed (`.venv/Scripts/python.exe -m pytest`) so the
mutation could not write to `uv.lock`.

## 7. AC3 adjudication — what is and is not demonstrated

The probe file was written once (`def probe( x,y ):` / `    return    x+y`, `sha256 13e1a389…`) and judged by
both surfaces.

**Demonstrated.**

1. **Surface A** — `uv run ruff format --check <probe>`: exit **1**, `1 file would be reformatted`, with the
   predicted output shown, and the probe's bytes unchanged by the check.
2. **Surface B** — `uv run pre-commit run ruff-format --files <probe>`: `ruff format ... Passed`, exit **0**,
   and the file **rewritten** to `def probe(x, y):` / `    return x + y` — byte-for-byte the output surface A
   predicted (`sha256 09f1e098…` after B).
3. **The hook's own bundled binary, check mode** — `~/.cache/pre-commit/repon1p3j7_t/py_env-python3/Scripts/ruff.exe`
   (`ruff 0.16.7`) `format --check <probe>`: exit **1**, the identical message and the identical predicted
   output as surface A.

So on the same bytes, the two independently installed ruff 0.16.7 binaries agree on the verdict (*this file
is unformatted*) and on the exact target bytes, and they return the identical exit code when invoked in the
same mode.

**Not demonstrated.**

1. **Wrapper-level exit-code equality.** `pre-commit run ruff-format` returned 0 where
   `ruff format --check` returned 1. This is mechanical, and both causes were measured independently in this
   phase:
   - the hook's entry is a **fixing** command — `.pre-commit-hooks.yaml` (cached rev `v0.16.7`, read
     read-only) declares `entry: ruff format --force-exclude`; only `--check` returns non-zero after a
     reformat;
   - pre-commit detects "files were modified by this hook" through `git diff`, which cannot see an
     **untracked** file.
2. **Wrapper behaviour on a *tracked* misformatted file** was not exercised: no tracked file in this tree is
   misformatted, and producing one would mean editing a production file, which this phase may not do. That
   case is therefore **unverified**.

**Plain verdict.** AC3 is satisfied **on substance**: the two surfaces judge the same file identically and
produce the same bytes. It is **not** claimed as exit-code parity, and the wrapper's exit code on an
untracked probe is a documented, measured property of the fix-mode entry plus pre-commit's `git diff`
detection — not a disagreement between the two ruff installations.

**Tag materialisation (the proposal's unverified #1) is retired.** A new pre-commit clone appeared at
`~/.cache/pre-commit/repon1p3j7_t/` (created `Sep 15 10:11`, this change's session) pinning
`ruff==0.16.7`; the newest clone before it (Sep 4) pinned `0.16.6`. So the upstream `v0.16.7` tag **resolves**
and the hook materialises. No workaround (`language: system`, rev downgrade, claiming AC3 from surface A
alone) was used anywhere.

## 8. AC5 adjudication — `uv.lock` confinement (own re-derivation, own verdict)

```console
$ git diff --numstat uv.lock
22	22	uv.lock
$ git diff -U3 uv.lock | grep -n '^@@'
5:@@ -2031,27 +2031,27 @@ wheels = [
54:@@ -2117,7 +2117,7 @@ dev = [
$ diff <(git show HEAD:uv.lock | grep -c '^\[\[package\]\]') <(grep -c '^\[\[package\]\]' uv.lock)
(identical — no package added or removed)
```

Hunk 1 covers the `[[package]] name = "ruff"` block only: `version` `0.16.0`→`0.16.7`, the `sdist` line, and
the 17 wheel entries (`34` wheel diff lines = 17 old + 17 new). Hunk 2 is the single dev-specifier line
inside the `[[package]] name = "sofer"` metadata block:

```console
-    { name = "ruff", specifier = ">=0.9.0" },
+    { name = "ruff", specifier = "==0.16.7" },
```

The lock header is untouched. There is no whitespace or ordering churn, no other `[[package]]` touched, and
no non-ruff `requires-dev` / `requires-dist` change. `uv lock --check` exits **0**.

**Verdict: ACCEPT — confined.** The apply phase's reported `22 added / 22 deleted` is confirmed by this
phase's own measurement.

**AC5 ownership.** The obligation is homed in `ci` CI-08, whose body now states the refresh must be
"confined to the ruff package block and the dev specifier" and that `packaging` PKG-06 "SHALL NOT be read as
owning this one". The delta text is consistent with the ratified correction; the proposal's earlier AC5 row
naming PKG-06 as owner is superseded, as `apply-progress.md` §2.8 records. Noted, not a finding.

## 9. Deviations adjudicated

### D-1 — `uv.lock` was already refreshed before apply's explicit probe

`uv run` re-locks by default when declarations change, so the task's step-0 assertion (`git status
--porcelain uv.lock` → empty) was already false when the explicit probe ran, and no `--upgrade-package`
fallback was needed. **Effect on any claim in this report: none.** This phase re-derived the confinement
independently from the current diff, and `uv lock --check` confirms the lock is current and consistent with
the declarations. Not a defect.

### D-2 — Phase 6 (canonical landing) is not executed

The four Phase 6 items are `sdd-sync`'s write, gated on a clean verify report. They are **not checkboxes**
in the current `tasks.md` — the section is prose with `<!-- sdd-owner: parent -->` tags, which is why the
native engine reports 45/45. Measured state: the canonical `ci` file still holds 22 Test Mapping rows with 15
naming `tests/test_ci_workflows.py`, canonical `process-boundary` still carries the deferral sentence, and
`git status --porcelain -- openspec/specs/` is empty. This is **expected**, not a missing acceptance
criterion: no AC of issue #195 is about canonical landing, and the deltas deliberately remain in the change
root until sync. Canonical specs were not edited by this phase.

### D-3 — R1: the `ruff-format` hook rewrites `README.md` and `README_ES.md` (pre-existing)

Confirmed from this side and **not absorbed**:

```console
$ git diff --name-only | grep -c 'README'        # 0
$ git diff --stat -- README.md README_ES.md      # (empty)
```

Both files are unchanged in this change's diff, and the revert left them clean. The mechanism was
re-verified read-only from the cached hook manifest (`rev v0.16.7`), which declares
`entry: ruff format --force-exclude` and `types_or: [python, pyi, jupyter, markdown]` — Markdown is in the
hook's file set, and the rev predates this change. This is a real, **pre-existing, version-independent**
defect (both 0.16.0 and 0.16.7 agree), outside the enforced `src/ tests/ scripts/` scope, and it is not this
change's to fix. It is carried forward as a separate finding in the risks; it does **not** gate sync.

### D-4 — REFACTOR does not apply

No production code was added; the only structural concern (single shared extraction vs duplication) is
satisfied by construction — one helper, three guards, existing `_read_text` / `_load_toml` / `_load_yaml` /
`_workflow_names` reused, no new file, no new import (`re` was already imported). Consistent with
`apply-progress.md` §1.5.

## 10. Rule 6 (scenario ↔ test) findings

- CI-08 S1, S2, S3 map **1:1** to three tests whose names are byte-identical in the delta's scenario `WHEN`
  clauses and its Test Mapping rows:
  - `tests/test_ci_workflows.py:463 test_ruff_pin_hook_rev_and_required_version_agree`
  - `tests/test_ci_workflows.py:475 test_workflows_do_not_declare_a_ruff_version`
  - `tests/test_ci_workflows.py:488 test_contributing_names_the_declared_ruff_version`
- **CI-08 S4 has no pytest test.** It maps to verify-phase runtime evidence, exactly as the delta's fourth
  Test Mapping row declares, following this repository's own precedent (`ci` CI-01 S2's gate-exit-code row,
  CI-07's three runtime rows, `coverage` COV-01/COV-02) and AGENTS.md rule 9 (the suite spawns no second
  binary). The evidence was produced by this phase (G10/G11): probe exit **2** on both subcommands naming
  both versions, declared value exit **0** on both. **Reported as a finding, not scored as a gap** — the
  mapping is explicit, precedented and satisfied, but a literal reading of AGENTS.md rule 6 ("every SDD spec
  scenario must have a corresponding test") does not cover it.
- PB-10 adds no scenario, so its evidence classes are unchanged, and no PB-10 scenario is re-mapped by this
  change. Per the change's scoping rule 1, its "exactly the six test files" and "formatting-only" scenarios
  are historical records of the #177 edit and were **not** measured against this diff.
- **No scenario is left unmapped and no vacuous fourth test exists** — the module holds exactly the three new
  guards.
- **Module docstring arithmetic re-derived and it closes**: `grep -c '^def test_'` → **22**;
  `grep '^| CI-0'` over canonical + delta `ci` specs, filtered to rows naming `test_ci_workflows.py` →
  **18** (15 canonical + 3 delta). The four remaining tests are exactly the two `coverage` COV-06 guards
  (`test_coverage_job_gates_core_modules_at_100`, `test_agents_md_declares_core_100_mandate` — both named in
  `openspec/specs/coverage/spec.md:320,322`), the CodeQL private-window guard, and
  `test_ci_workflow_files_present`. **18 + 4 = 22 closes** against the real file and the real table.

## 11. Task completion

**No unchecked implementation task remains.**

```console
$ grep -cE '^\s*- \[x\]' openspec/changes/2026-09-15-chore-ruff-single-authority/tasks.md
45
$ grep -nE '^\s*- \[ \]' openspec/changes/2026-09-15-chore-ruff-single-authority/tasks.md
(no output — zero matches)
```

Exact unchecked `- [ ]` implementation task lines: **none**. Phase 6 (canonical landing) is not an
implementation checkbox; it is prose in the tasks artifact, tagged `sdd-owner: parent`, executed by
`sdd-sync` after this report. `tasks.md` was therefore **not edited** by this phase — no checkbox or
reconciliation was needed. Archive is blocked only on the pending sync, which is the expected ordering.

## 12. Strict TDD compliance

`strict_tdd` is **false** for this repository (`openspec/config.yaml:12`; corroborated by the parent's
launch context), so no `TDD Cycle Evidence` table is required in `apply-progress.md` and no RED/GREEN
ceremony is scored. This phase did not require it and did not treat its absence as a defect.

Independently, the test-before-declaration ordering the plan chose was **reproduced by this phase**: probe
P1 restores the pre-change declaration (`"ruff>=0.9.0"`) and shows all three guards failing
(`3 failed, 19 passed`), which is the observed-RED-before-GREEN property the plan claimed. REFACTOR has no
subject (no production code).

## 13. Assertion quality (new/changed tests)

The three added guards and the extraction helper were audited for the failure modes this phase checks for.

| Check | Finding |
| --- | --- |
| Tautology | None. Each guard compares a value **extracted from a different file** (`pyproject.toml` dev pin) against `[tool.ruff] required-version` and the `ruff-pre-commit` `rev`; equality can fail (P1–P4 prove it). |
| Ghost loop / vacuous pass | None. `test_workflows_do_not_declare_a_ruff_version` asserts the workflow list is non-empty before scanning, so an empty glob cannot pass it vacuously. |
| Type-only assertions | None. |
| Smoke-only | None. The guards assert concrete equality on parsed declarations, not mere importability. |
| Implementation-detail CSS assertions | Not applicable (no UI). |
| Hardcoded expected values | None. `grep -c '0\.16' tests/test_ci_workflows.py` → 0 version literals in the module; every value is derived. |
| Boundary correctness | `_DEV_ENTRY_RE` matches a PEP 508 **name** first, so `ruff-lsp>=0.1` is excluded rather than tripping the "exactly one pin" assertion; the CONTRIBUTING matcher is boundary-aware (`(?<![\d.])…(?![\d.])`), so `0.16.7` inside `0.16.70` does not satisfy it. |
| Helpers documented | `_declared_ruff_version()` carries a numpydoc docstring with a `Returns` section; each test's docstring names the CI-08 scenario it asserts. |

## 14. Review workload / PR boundary

| Item | Value |
| --- | --- |
| `tasks.md` forecast | ≈184 changed lines (functional ≈124 + spec-delta ≈60); `400-line budget risk: Low`; `Chained PRs recommended: No`; `Chain strategy: pending`; single PR; no `size:exception` |
| **Measured tracked diff** | **132 changed lines = 103 added / 29 deleted** — `CONTRIBUTING.md` 1/1, `pyproject.toml` 5/1, `tests/test_ci_workflows.py` 75/5, `uv.lock` 22/22 |
| Budget used | **33 %** of the canonical 400-line budget; **9 %** of the session's 1500-line budget |
| Chain strategy | **Not exercised and not needed.** No chained PRs were recommended, and the measured diff confirms the Low-risk forecast, so `ask-on-risk` correctly did not fire and no `size:exception` was requested or inferred |
| Work boundary returned | A **single** working-tree change on `chore/195-ruff-single-authority` — exactly the four production paths plus this change's SDD artifacts. No commits, no pushes |
| Scope creep | **None.** `git diff --name-only` is exactly the four expected paths. Zero `src/sofer/**`, zero `.github/workflows/**`, zero `README*`, zero `.pre-commit-config.yaml`, zero `openspec/specs/**` |

The forecast's fallback split (functional core → spec deltas → phase artifacts) was never needed; the guard
tests remain in the same slice as the CI-08 scenario rows they satisfy (AGENTS.md rule 6).

**Rules 7 / 13 with commands, not intent**: `git diff --name-only | grep -c 'README'` → 0;
`git diff --name-only -- src/sofer/ | wc -l` → 0. No CLI surface, subcommand or flag changed, so no
`help=` / `description=` string moved and no `README.md` / `README_ES.md` mirroring is due. The only
documented claim that changed is the `CONTRIBUTING.md:77` sentence.

## 15. Unverified / not demonstrated (explicit list)

1. **Wrapper-level exit-code parity for AC3** — `pre-commit run ruff-format` exit 0 vs
   `ruff format --check` exit 1 on an untracked probe (mechanism measured and explained in § 7).
2. **`pre-commit run ruff-format` on a *tracked* misformatted file** — not exercised; producing one would
   require editing a production file, which is outside this phase's edit authority.
3. **The pre-change suite tally `1781 passed / 6 skipped`** — `apply-progress.md`'s measurement; it cannot be
   re-measured without reverting the change. The **+3** delta was re-derived from the real pre-change module
   (`19` → `22` test functions) and every other baseline figure was re-derived from `git show HEAD:`.
4. **Post-sync canonical invariants** (`CI-08` present in both canonical specs; 26 `ci` rows of which 18 name
   the module) — `sdd-sync`'s write, deliberately not executed here. Measured pre-sync: 0 / 0 mentions,
   22 rows / 15 module-named rows. Expected, per § 9 D-2.
5. **R1's contributor-visible consequence** (a README edit plus an installed hook gets the READMEs rewritten)
   — characterised from the hook manifest and both binaries' verdicts, but not reproduced end-to-end here,
   because reproducing it would rewrite the READMEs.

## 16. Blockers

**None.** `blockers: 0`, `critical_findings: 0`. No finding requires remediation before `sdd-sync`.

## Key Learnings

1. Mutating a declaration and re-editing it back while proving whole-file `sha256` identity is a safe way to test guard teeth on a tree that carries uncommitted edits.
2. Running the suite through `.venv/Scripts/python.exe -m pytest` instead of `uv run pytest` prevents uv's default re-lock from writing to `uv.lock` during a declaration mutation probe.
3. The `ruff-format` pre-commit hook declares `types_or` including `markdown`, so it rewrites Markdown code blocks — pre-existing and version-independent for this repository.
4. A pre-commit hook whose entry is a fixing command exits 0 after rewriting a file, so exit-code parity with `ruff format --check` can only be shown through the hook's own bundled binary in check mode.
5. Redacting a version literal from a guard test by extracting it from a config declaration keeps one authoritative source and prevents the test from going stale on a bump.
