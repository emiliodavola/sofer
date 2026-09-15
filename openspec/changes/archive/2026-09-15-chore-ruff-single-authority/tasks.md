# Tasks: chore-ruff-single-authority

**Change** `2026-09-15-chore-ruff-single-authority` (GitHub #195) · branch
`chore/195-ruff-single-authority` · store **hybrid** — this file plus the Engram mirror under topic
key `sdd/2026-09-15-chore-ruff-single-authority/tasks`.
**Inputs read this phase**: `design.md` (733 lines), `proposal.md`, `preproposal.md`,
`specs/ci/spec.md`, `specs/process-boundary/spec.md`, plus `tests/test_ci_workflows.py`,
`pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `CONTRIBUTING.md`, `openspec/specs/ci/spec.md`,
`openspec/config.yaml`, `.python-version`.

**One-line outcome**: one ruff version (`0.16.7`) declared in three places that a static guard forces
equal, enforced at config load by `[tool.ruff] required-version`, PB-10's now-false deferral sentence
replaced, and **no CI format gate armed**.

## Phase routing and sequencing rules

| Rule | Value |
| --- | --- |
| `strict_tdd` | `false` (`openspec/config.yaml:12`), but the three CI-08 scenarios land as **new tests**, so the sequence is still RED → GREEN → TRIANGULATE; REFACTOR has no production code to restructure (task 1.5 states why) |
| Hard ordering 1 | §3.6's **RED probe precedes any declaration edit** — task 1.3 must run before task 2.1 |
| Hard ordering 2 | The **`uv.lock` refresh precedes the runtime probes** — tasks 2.5–2.7 must run before 4.1–4.6, because the S4/AC3 probes must judge **0.16.7 in the venv** |
| Hard ordering 3 | **Sync lands both deltas in one operation** (task 6.1): PB-10 forward-references `ci` CI-08, so a reader between two writes would see a dangling reference |
| No CI gate | PB-10 keeps enforcement on the local `ruff-format` hook and assigns recurrence to #194; this change arms no `format --check` step and adds no workflow file (tasks 4.7, 7.8) |
| Rules 7 / 13 | **This change touches neither `README.md` nor `README_ES.md`.** It adds no subcommand, no flag, and no CLI help text, so rule 7's help/README update and rule 13's mirroring do not apply (asserted in task 7.8) |
| Other binding conventions | Rule 1 (no hardcoded values — task 2.2 records why the `required-version` literal is a build/toolchain declaration), rule 4 (no duplicated logic — task 1.1 reuses the module's helpers, adds no new file), rule 6 (every spec scenario maps to a test — tasks 1.4, 5.7), rule 14 (coverage mandates — task 7.5) |

## Corrections carried into apply (gatekeeper findings and measured state — inputs, not opinions)

1. **Append point.** The design says the three guards are "appended at `:421`". Measured: `tests/test_ci_workflows.py` is **426 lines** and line 421 is the *start* of the existing
   `def test_pr_template_has_coverage_checklist_item`; the file's last line (426) is
   `assert "README_ES.md updated" in checklist`. The guards are appended at the **end of the file**,
   after the last existing test — task 1.1 says so explicitly.
2. **Docstring arithmetic is verified and closes — do not "fix" it.** Measured on the pre-apply tree:
   the canonical `ci` Test Mapping table (`openspec/specs/ci/spec.md:285`) holds **22** data rows,
   **15** of which name `tests/test_ci_workflows.py`; the module holds **19** `def test_` functions,
   of which 15 map to `ci` and **4** do not (2 `coverage` COV-06, 1 CodeQL private-window, 1 supporting
   guard `test_ci_workflow_files_present`). Post-apply: 15 + 3 = **18** `ci`-mapped, plus the same 4
   non-`ci` = **22** = `grep -c "^def test_"` (19 + 3). The verify phase **re-derives** these figures
   (task 7.6) instead of copying them.
3. **`uv.lock` confinement is an unverified probe.** No flag is asserted: task 2.5 runs the probe and
   pastes the diff with explicit accept/reject rules.
4. **`v0.16.7` tag existence is an unverified probe.** The pre-commit cache's newest ruff clone pins
   `ruff==0.16.6`, so the tag has never resolved on this machine. Materialising the hook environment is
   both the AC3 evidence and the tag-existence probe (tasks 4.3–4.4); failure is escalated (task 4.8).
5. **Mutation-revert safety (deviation from design §3.6's shorthand, recorded).** §3.6 says each
   mutation is reverted with `git checkout --` on that one file. That is safe **only** for
   `.pre-commit-config.yaml`, whose baseline diff is zero. For `pyproject.toml` and `CONTRIBUTING.md`
   it would delete **this change's own edits** along with the mutation. Tasks 3.2 and 5.3 therefore
   restore by re-editing the declared value and prove byte-identity with a diff hash captured before
   the probe.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | **≈184 (≈170–195)**: `pyproject.toml` 4–5 · `uv.lock` ≈40 (36–46, *unverified* until task 2.5) · `tests/test_ci_workflows.py` ≈78 (65–85: helper + constants ≈22, three tests ≈45, module docstring ≈11) · `CONTRIBUTING.md:77` 2 · `.pre-commit-config.yaml` 0 · functional subtotal **≈124 (110–140)** · spec-delta content in the change root (`ci` CI-08 + 4 Test Mapping rows ≈50, of which ≈6 lines change in apply; `process-boundary` PB-10 ≈10) **≈60**. SDD artifacts under the change root (`proposal.md` / `spec.md` / `design.md` / this file / apply-progress / verify-report, ≈700 lines of prose) are **not review load** — this repository's own precedent (`openspec/changes/archive/2026-09-14-chore-ruff-format-drift/tasks.md:23`) |
| 400-line budget risk | **Low** |
| Chained PRs recommended | **No** |
| Suggested split | **Single PR** against `dev` (~184 lines). Fallback only if the parent counts SDD artifacts as load (then ≈880 raw lines): PR 1 functional core — `pyproject.toml` + `uv.lock` + the three guard tests + `CONTRIBUTING.md` (≈124 lines, where AC1/AC2/AC5 are verifiable in isolation) → PR 2 the two spec deltas → PR 3 the phase artifacts. **The guard tests are never split from the CI-08 scenario rows they satisfy** (AGENTS.md rule 6) |
| Delivery strategy | **auto-chain** (risk is Low, so no chain is selected) |
| Chain strategy | **pending** (chaining deferred until selected; not needed — ≈184 lines against a 400-line budget, so `ask-on-risk` should not fire) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**Budget-reading note (recorded, not re-opened).** The session preflight block states a 1500-line
review budget while this change's parent ruling is **400 with SDD artifacts excluded**. The estimate
passes under **both** readings (≈184 estimated, ≈880 only if ≈700 lines of prospective SDD prose are
counted as review load), so the forecast is Low under either and no decision gate is requested.

### Suggested Work Units

| Unit | Goal | Boundaries (start → finish · verify · rollback) |
| --- | --- | --- |
| 1 | Guard tests, RED first (tasks 1.1–1.5) | start: clean tree · finish: 3 new failing tests · verify: RED output naming the exact-pin assertion · rollback: revert `tests/test_ci_workflows.py` |
| 2 | Declarations + lock (tasks 2.1–2.8) | start: pin is `ruff>=0.9.0` · finish: `ruff 0.16.7` in the venv, confined lock diff · verify: `uv run ruff --version`, `uv lock --check` exit 0, diff hunks all name `ruff` · rollback: revert `pyproject.toml` **and** `uv.lock` together, never one alone |
| 3 | Guard teeth — mutation probes (tasks 3.1–3.3, 5.3) | start: guards green · finish: each leg observed RED and restored byte-identically · verify: per-leg RED output + `git status --porcelain` free of residue · rollback: none needed; residue is a failure |
| 4 | Runtime evidence (tasks 4.1–4.8) | start: 0.16.7 in the venv · finish: AC3 parity verdicts + S4 legs A/B + no-CI-gate greps · verify: pasted outputs with exit codes · rollback: no source change; the hook is removable with `pre-commit uninstall` |
| 5 | Docs + SDD text (tasks 5.1–5.7) | start: line 77 unchanged · finish: one token added, docstring reconciled, delta wording fixed · verify: `--word-diff` shows one line/one token, 22 guard tests passed · rollback: revert `CONTRIBUTING.md`, the docstring hunk, the `ci` delta |
| 6 | Sync + final gates (tasks 6.1–6.4, 7.1–7.10) | start: both deltas written, neither landed · finish: canonical specs carry both, all gates green · verify: the 18/22/26 row arithmetic and the full command block · rollback: whole-change `git revert` |

---

## Phase 0 — Baseline and scope anchor

- [x] 0.1 Confirm the branch is `chore/195-ruff-single-authority` (not `dev`) and that
  `git status --porcelain` shows only this change's SDD artifacts, so the later scope proofs are
  unambiguous. Do **not** commit, push, tag or open a PR at any point in this phase set.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the branch line plus the verbatim `git status --porcelain` output.

- [x] 0.2 Record the **pre-change** `uv run pytest tests/ -q` tally verbatim (collected / passed /
  skipped). Re-derive it — never copy `AGENTS.md` rule 6's figure (rule 6's tally literal is another
  owner's). This must happen before task 1.1: a tally taken later cannot support "baseline + 3".
  <!-- sdd-owner: implementation -->
  - **Evidence:** the actual tail line with collected/passed/skipped counts.

- [x] 0.3 Record the pre-change structural figures the module docstring will have to reconcile:
  `grep -c "^def test_" tests/test_ci_workflows.py` → **19**;
  `grep "^| CI-0" openspec/specs/ci/spec.md | wc -l` → **22**;
  `grep "^| CI-0" openspec/specs/ci/spec.md | grep -c "test_ci_workflows.py"` → **15**;
  `git diff --numstat uv.lock` → empty (the lock is clean, which is the confinement probe's baseline).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the four command outputs.

- [x] 0.4 Record the append anchor as measured: `grep -n "^def test_pr_template_has_coverage_checklist_item"
  tests/test_ci_workflows.py` → **421**, and the file's last line is **426**
  (`assert "README_ES.md updated" in checklist`). The three guards therefore go **after line 426**,
  i.e. at the end of the file — never at `:421`, which is the *start* of an existing test.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both greps' output, recorded before any edit.

## Phase 1 — RED: the three guards, appended at the end of the file

- [x] 1.1 Append the guard block to the **end of `tests/test_ci_workflows.py`** (after line 426, after
  `test_pr_template_has_coverage_checklist_item`): one module-level extraction helper
  `_declared_ruff_version()`, the constants `_RUFF_PRE_COMMIT_REPO =
  "https://github.com/astral-sh/ruff-pre-commit"`, `_DEV_ENTRY_RE`, `_EXACT_PIN_RE` (placed with the
  other module constants and helpers), and exactly the three tests
  `test_ruff_pin_hook_rev_and_required_version_agree`,
  `test_workflows_do_not_declare_a_ruff_version`,
  `test_contributing_names_the_declared_ruff_version`. Reuse the existing `_read_text`, `_load_toml`,
  `_load_yaml`, `_workflow_names` and `_WORKFLOW_DIR` (rule 4: no duplicated logic, no new file); the
  module already imports `re` (`:20`), so no new import is needed. The helper must parse a PEP 508
  **name** (so a future `ruff-lsp>=0.1` entry is excluded rather than tripping "exactly one pin") and
  must assert the specifier is an exact `==X.Y.Z` (that assertion is what makes the guard fail on
  today's floor). **No test may carry a version literal** — every value is extracted from the dev pin.
  The `required-version` assertion reads `[tool.ruff]["required-version"]`; the hook assertion compares
  the `astral-sh/ruff-pre-commit` entry's `rev` to `"v" + version`; the workflow guard asserts the
  extracted literal is absent from every workflow **and** that no ruff version-specifier syntax exists
  there, with a non-empty workflow-list assertion so it cannot pass vacuously; the CONTRIBUTING guard
  is boundary-aware (`(?<![\d.])…(?![\d.])`) so `0.16.7` inside `0.16.70` does not satisfy it.
  Docstrings on the helper and each test state which CI-08 scenario they assert.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the appended block's text plus `git diff --numstat tests/test_ci_workflows.py`.

- [x] 1.2 Run the `python-code-style` trio on the single touched Python file:
  `uv run ruff format tests/test_ci_workflows.py`, then
  `uv run ruff check --fix tests/test_ci_workflows.py`, then `uv run ruff check tests/test_ci_workflows.py`
  → clean. Note in the progress record that that skill's "drop a root `ruff.toml`" step does **not**
  apply here: this repository keeps ruff config in `pyproject.toml:56-69`, a deliberate divergence
  (recorded in `explore.md`). One fix pass per warning, then surface — do not enter a third cycle.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the three commands' output and exit codes.

- [x] 1.3 **RED, before any declaration edit**: `uv run pytest tests/test_ci_workflows.py -q` with the
  three tests present and `pyproject.toml:47` still `ruff>=0.9.0` → the failures must come from the
  exactness assertion in `_declared_ruff_version()` (the drift-explaining message), not from a missing
  file or a KeyError. Record the failing test names and the assertion messages verbatim.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the pytest output showing the new tests failing on the exact-pin assertion.

- [x] 1.4 Confirm the three test names are byte-identical to the names the `ci` delta's CI-08 scenarios
  and its four Test Mapping rows use, and record the three names verbatim for the verify phase
  (AGENTS.md rule 6: one test per scenario, no vacuous fourth test).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the three `def test_` lines plus the matching scenario lines from
    `specs/ci/spec.md`.

- [x] 1.5 Record explicitly that **REFACTOR does not apply**: this change adds no production code, the
  only structural concern (shared extraction versus duplication) is settled by construction in task 1.1
  (rule 4), and the touched module's own docstrings are reconciled in task 5.4 rather than by a refactor
  pass. If a genuine duplication is discovered while writing 1.1, extract it inside this task instead of
  opening a new one.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the one-line statement in the apply progress, plus any extraction actually performed.

## Phase 2 — GREEN: declarations, lock refresh, hook verification

- [x] 2.1 Replace the dev-group pin: `pyproject.toml:47` `"ruff>=0.9.0"` → `"ruff==0.16.7"`. Exact
  specifier, no floor — the floor is what let `uv lock` resolve `0.16.0` in the first place.
  <!-- sdd-owner: implementation -->
  - **Evidence:** `grep -n '"ruff==' pyproject.toml` → the single line at 47, and
    `grep -c "ruff>=" pyproject.toml` → 0.

- [x] 2.2 Insert the enforcing declaration in `[tool.ruff]` **after `line-length = 100`
  (`pyproject.toml:58`)** and **before the `extend-exclude` comment block (`:59`)**: the three-line
  explanatory comment plus `required-version = "==0.16.7"`. The comment must state that the single
  authoritative version equals the dev-group pin and the `ruff-pre-commit` rev, that the three
  declarations are forced to agree by CI-08's guards, and that a drifting binary fails at config load —
  and it must **not** repeat the version, so each declaration site holds exactly one occurrence.
  Record, for rule 1, why this literal is not a "hardcoded value" defect: it is a build/toolchain
  declaration of the same class as `.python-version` and `[tool.mypy] python_version`
  (`pyproject.toml:74`); `[tool.sofer]` config holds runtime defaults consumed by `src/sofer/config.py`,
  and **no `src/sofer/` code path reads a ruff version** — `grep -rn "ruff" src/` returns only
  `src/sofer/mcp_server.py:1` (`# ruff: noqa: E501`, a directive).
  <!-- sdd-owner: implementation -->
  - **Evidence:** `grep -n "required-version" pyproject.toml` → the new line,
    `grep -c "0.16.7" pyproject.toml` → **2** (pin + required-version), the `grep -rn "ruff" src/`
    output, and the recorded rule-1 rationale.

- [x] 2.3 Re-run `uv run pytest tests/test_ci_workflows.py -q` and record the intermediate state
  honestly: tests 1 and 2 are **green**, test 3 is **still RED** because `CONTRIBUTING.md:77` has not
  been edited yet — that edit is task 5.1 by design ordering. Record the exact pass/fail split; do not
  claim three greens here.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the pytest summary line naming which of the three tests still fails.

- [x] 2.4 Verify `.pre-commit-config.yaml` needs **no edit**: `grep -n
  "astral-sh/ruff-pre-commit" .pre-commit-config.yaml` → the entry at `:2-3` with `rev: v0.16.7`, and
  `git diff --stat .pre-commit-config.yaml` → empty. "Unchanged" is an **asserted property**, not an
  assumption: the guard fails if the rev moves alone. **If the rev is not `v0.16.7`**: stop, re-read
  line 3, capture `git log -1 --format=%H%n%s -- .pre-commit-config.yaml`, and escalate to the parent —
  the authoritative version is a ratified decision (D1 = `0.16.7`), so a moved rev must be re-ratified,
  never silently adopted; do not edit the rev unilaterally and do not let the guard's rev assertion
  "fix" the disagreement.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the grep output, the empty diffstat, or the escalation note with the commit
    identity if the rev moved.

- [x] 2.5 **`uv.lock` confinement probe — no flag is asserted.** Run, in order, and record raw output:
  `git status --porcelain uv.lock` → empty; `uv lock --help | grep -n "upgrade-package\|check\|locked"`
  (discover which flags this uv actually supports); then `uv lock`; then `git diff --numstat uv.lock`
  and `git diff uv.lock`. **Accept** only: lines inside the `ruff` package block (`uv.lock:2032-2037`
  and its wheel list — pre-change `version = "0.16.0"` at `:2034`, the `sdist` line at `:2036`, the 17
  wheel entries), and the single dev-specifier line `uv.lock:2120`
  (`{ name = "ruff", specifier = ">=0.9.0" }` → `"==0.16.7"`, the only line of the `sofer` metadata
  block that may change). **Reject and surface — never absorb**: any other `[[package]]` touched, any
  package added or removed, the lock header (`uv.lock:1-11`), whitespace/ordering churn, or any
  non-ruff `requires-dev`/`requires-dist` change. On rejection: `git checkout -- uv.lock`, record the
  observed churn verbatim, then retry with `uv lock --upgrade-package ruff` (**flag NOT verified this
  phase** — record whether this uv accepts it) and re-inspect. If the churn persists, or if the machine
  is offline so `uv lock` cannot run, report AC5 as **blocked** and escalate: hand-editing `uv.lock`,
  staging a partial hunk, or absorbing the churn are **forbidden** workarounds.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the discovered flag list, `git diff --numstat uv.lock`, the full `git diff uv.lock`
    with every hunk attributed to a `ruff` line, and an explicit accept-or-escalate verdict.

- [x] 2.6 Consistency check: run the flag task 2.5 discovered — `uv lock --check` (or `uv lock --locked`
  if `--check` is unsupported) → **exit 0**. Record the actual flag used, because which one exists is
  unverified.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the command line, its output and its exit code.

- [x] 2.7 `uv sync`, then `uv run ruff --version` → **`ruff 0.16.7`**. This is the precondition for tasks
  4.1–4.6 (the S4 and AC3 probes must judge the declared value, not the ambient 0.16.0).
  <!-- sdd-owner: implementation -->
  - **Evidence:** both commands' output.

- [x] 2.8 Record the lock-refresh verdict in one place for the verify report: the accepted hunks by line
  range, the reject-rule outcome, and the AC5 ownership correction — the obligation's home is **`ci`
  CI-08** (task 5.5), with `packaging` PKG-06's regeneration clause cited as the **same class** of rule
  scoped to its own `fastmcp` declaration, **not** as this one's owner. The proposal's AC5 row citing
  PKG-06 as owner is superseded by this correction.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the recorded verdict plus the superseded-citation note.

## Phase 3 — TRIANGULATE: the guard's teeth (mutation probes)

Each leg: mutate one declaration, observe the specific guard going RED, restore, prove restoration.
A leftover mutation is a **verification failure**, not a footnote.

- [x] 3.1 Mutation leg 1 — the hook rev: set `.pre-commit-config.yaml:3` to `rev: v0.16.6`; run
  `uv run pytest tests/test_ci_workflows.py -q` → test 1 fails on the **rev** assertion (record the
  message); restore with `git checkout -- .pre-commit-config.yaml` (safe: the file's baseline diff is
  zero) and prove `git diff --stat .pre-commit-config.yaml` is empty again.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the RED message naming the rev assertion, plus the empty diffstat after restore.

- [x] 3.2 Mutation leg 2 — `required-version`: capture the pre-probe fingerprint
  `git diff pyproject.toml | sha256sum`, then set `required-version = "==0.16.6"`; run
  `uv run pytest tests/test_ci_workflows.py -q` → test 1 fails on the **required-version** assertion
  (record the message). Restore by **re-editing back to `"==0.16.7"`** — `git checkout -- pyproject.toml`
  is **forbidden** here because it would delete this change's own pin and `required-version` edits
  (correction 5) — then re-run the fingerprint and require it to **match byte-for-byte**, and re-run
  `uv run pytest tests/test_ci_workflows.py -q` to confirm the leg is green again.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the RED message, the two matching `sha256sum` values, and the green re-run.

- [x] 3.3 No-residue assertion: `git status --porcelain` → only the intended change paths
  (`pyproject.toml`, `uv.lock`, `tests/test_ci_workflows.py`) plus this change's SDD artifacts —
  `CONTRIBUTING.md` is expected to be untouched at this point. Record the output verbatim.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the verbatim `git status --porcelain` output. (The third mutation leg runs at task 5.3,
    immediately after the documentation edit exists.)

## Phase 4 — Runtime evidence (AC3 parity, `required-version`, no-CI-gate)

- [x] 4.1 CI-08 S4 **leg A** — the declared value passes: `uv run ruff check src/ tests/ scripts/` → exit
  **0**; `uv run ruff format --check src/ tests/ scripts/` → exit **0** with
  `68 files already formatted`. Record both outputs and exit codes (the enforced command scope from
  `ci.yml:19`, not the narrower documented one — #212 stays untouched).
  <!-- sdd-owner: implementation -->
  - **Evidence:** both commands' output and exit codes.

- [x] 4.2 CI-08 S4 **leg B** — a mismatch probe: create a config file **outside the repository** (e.g.
  `%TEMP%\ruff-probe\ruff.toml` on Windows, `$TMPDIR` elsewhere) holding only
  `required-version = "==99.0.0"`, then run
  `uv run ruff check --config <probe> src/ tests/ scripts/` and
  `uv run ruff format --check --config <probe> src/ tests/ scripts/` → **both non-zero**, each message
  naming the required **and** the running version. Record the actual exit codes — do **not** assert `2`,
  and do not accept a TOML/parse error as the failure (that would prove nothing). If `--config` rejects
  an out-of-tree path, fall back to a temp directory holding a `pyproject.toml` with
  `[tool.ruff] required-version` and record the substitution. The tracked `pyproject.toml` is never
  edited by this probe.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both probe commands' full output, exit codes, and the version pair each message names.

- [x] 4.3 AC3 parity (D3) — pre-state `git status --porcelain`; then `pre-commit install` and
  `ls .git/hooks/pre-commit`. Write the parity probe file **once** at the repo root, untracked and
  deliberately misformatted but **valid** Python (e.g. `def probe( x,y ):` with `return    x+y` on the
  next line) — it is the immutable content both surfaces judge. **Surface A first**:
  `uv run ruff format --check _ruff_parity_probe.py` → exit **1**, `1 file would be reformatted`.
  **Then surface B**: `pre-commit run ruff-format --files _ruff_parity_probe.py` → exit **1**,
  `1 file would be reformatted` (the hook rewrites the file, which is why A must precede B). Same
  verdict on the same bytes is AC3's evidence.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both commands' output and exit codes, the `ls .git/hooks/pre-commit` line, and the
    statement that A ran before B.

- [x] 4.4 Prove the hook's bundled binary — and probe the tag at the same time:
  `grep -n "ruff==" ~/.cache/pre-commit/*/pyproject.toml` (`$HOME/.cache/pre-commit` under Git Bash on
  Windows) → at least one clone pinning **`ruff==0.16.7`**. A **new** clone appearing is itself evidence
  that the upstream `v0.16.7` tag resolved (the newest cached clone previously pinned `0.16.6`) —
  record whether a new directory appeared.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the grep output with the cache path, plus the new-clone observation.

- [x] 4.5 Whole-tree leg: `pre-commit run ruff-format --all-files` → no reformat reported. **If any
  tracked file changes**, 0.16.7 differs from 0.16.0 on this tree for that path: stop the probe,
  `git checkout --` the affected paths, and surface the finding as a scope change — never absorb it
  (the four rule-14 modules would be at risk).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the command's output plus either "no tracked file changed" or the surfaced finding.

- [x] 4.6 Cleanup: `rm _ruff_parity_probe.py`, then `git status --porcelain` → identical to the pre-state
  of task 4.3 (no tracked change, no probe residue). Record that the hook itself **stays installed**
  (that is the intended contributor state) and that its rollback is `pre-commit uninstall`.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the two `git status --porcelain` outputs (before/after) and the rollback note.

- [x] 4.7 No-CI-gate static evidence (PB-10's live clause, CI-08's inverse assertion):
  `grep -rn "format" .github/workflows/` → **0 matches**;
  `grep -rn "format --check" .github/workflows/` → **0 matches**; and `git diff --name-only` contains
  **no** `.github/workflows/` path. This change arms no step, adds no workflow file.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both greps' output (0 matches) and the absence of any workflow path in the diff.

- [x] 4.8 Escalation rule, stated so it cannot be worked around: if the `v0.16.7` tag cannot be fetched
  (task 4.4 finds no 0.16.7 clone) or the hook cannot materialise, **AC3 is blocked**: record the failure
  verbatim and escalate to the parent. Substituting `language: system`, switching the rev to a cached
  version, or claiming AC3 from surface A alone are all forbidden.
  <!-- sdd-owner: implementation -->
  - **Evidence:** either the successful materialisation evidence or the explicit blocked-and-escalated
    record.

## Phase 5 — Documentation, module docstring, and the change-root spec text

- [x] 5.1 Edit `CONTRIBUTING.md:77` — **first sentence only**:
  `This project uses **ruff** for linting and formatting.` →
  `This project uses **ruff** 0.16.7 for linting and formatting.` The two remaining sentences stay
  **byte-identical** (the nonexistent `ruff.toml` path is #187's defect; the narrower documented
  commands at `:22-31` are #212's). Constraints: the edit lands inside `### Code style` (`:75`) and
  before `### Type checking` (`:79`) — never in the Development-commands block — and **re-read line 77
  immediately before applying**, because #187 may have land-changed that same line; if it did, re-anchor
  the edit to the current text rather than applying a stale hunk.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the new line 77 verbatim, plus the re-read output that proves the anchor was current.

- [x] 5.2 Boundary proof for 5.1: `git diff --word-diff CONTRIBUTING.md` → **exactly one changed line**
  and **exactly one inserted token** (`0.16.7`) plus its space; the sentence naming `ruff.toml` must not
  appear anywhere in the diff. Also `git diff --numstat CONTRIBUTING.md` → `1  1`.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the `--word-diff` output and the numstat line.

- [x] 5.3 Mutation leg 3 — the documentation half: capture
  `git diff CONTRIBUTING.md | sha256sum`, remove the version from the Code style sentence, run
  `uv run pytest tests/test_ci_workflows.py -q` → `test_contributing_names_the_declared_ruff_version`
  fails (record the message); restore by **re-editing** (never `git checkout -- CONTRIBUTING.md`, which
  would delete this change's own edit — correction 5), then require the fingerprint to match and the
  three guards to be green again.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the RED message, the two matching `sha256sum` values, and the green re-run.

- [x] 5.4 Reconcile the module docstring of `tests/test_ci_workflows.py` (`:1-11`) — four edits in the
  same docstring: (a) the enumeration becomes **`CI-01..CI-08`** (fixing the pre-existing CI-07 omission,
  because a CI-08 mention beside a missing CI-07 would be manifestly wrong); (b) the row figure becomes
  **18**, phrased as "`ci` Test Mapping rows whose verification names a test in this module" — which is
  what the number actually counts, and which is true of the **canonical + delta union** a reader sees
  after sync; (c) one added clause names the **four** remaining tests (the two `coverage` COV-06 guards,
  the CodeQL private-window guard, and `test_ci_workflow_files_present`) so `18 + 4 = 22` matches the
  module's test-function count and the next reader re-derives no mismatch; (d) the runtime-evidence
  sentence gains **CI-08 S4** alongside CI-01 S2. Do not paste figures from the design — use the values
  re-derived in task 7.6, and introduce no version literal anywhere in the module.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the docstring diff plus `grep -c "^def test_"` and the two row greps from task 7.6
    shown beside the quoted docstring figures.

- [x] 5.5 Apply the two-part wording fix in `openspec/changes/…/specs/ci/spec.md` (design §1.5),
  and nothing else in the delta: (1) in the CI-08 body, replace
  `A change that moves the pin SHALL refresh \`uv.lock\` in the same change; \`packaging\` PKG-06 owns that rule and this requirement SHALL NOT re-declare it.`
  with the ratified replacement stating that the refresh is confined to the ruff package block and the
  dev specifier, that PKG-06 states the same class for its own `fastmcp` declaration and **SHALL NOT** be
  read as owning this one, and that the obligation is therefore stated in CI-08; (2) in the delta's
  *Cross-referenced and deliberately untouched* table, replace the PKG-06 row's reason with the ratified
  text naming CI-08 as the owner and PKG-06 as the same class. Record the before/after text of both
  spots, and note that **no** fifth scenario is added (task 5.6 keeps the row set at four).
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff` of the delta file with exactly those two hunks.

- [x] 5.6 Confirm the `process-boundary` delta is **unchanged** this phase (ratified as written): record
  that `specs/process-boundary/spec.md` received no edit, that its PB-10 block replaces exactly one
  sentence and inserts the `(Previously: …)` note while the five scenarios stay byte-identical, and that
  the `(Previously: …)` line is the **only** version-literal occurrence anywhere — exempt by the
  canonical-spec convention (`openspec/specs/process-boundary/spec.md:12,63,95,115,232` carry the same
  shape). The normative-literal invariant is therefore **1 → 0**, checked in task 7.9.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the empty diff for that file plus the enumerated exemption.

- [x] 5.7 Local green check: `uv run pytest tests/test_ci_workflows.py -q` → **22 passed** (19
  pre-existing + 3 guards), zero failures, and **no new skip** introduced (the module's only
  `pytest.skip` remains `_openspec_config`'s). Record the summary line.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the 22-passed summary line and the unchanged skip count.

## Phase 6 — Sync: land both deltas in one operation

Owning phase: `sdd-sync`. Do **not** run this before Phase 5's text is final.

These four obligations carry `sdd-owner: parent`, not `implementation`: `sdd-sync` is
orchestrator-invoked and is never an automatic native-status dispatch, and its own contract requires a
clean `verify-report.md` before canonical specs are published. Tagging them `implementation` made the
native engine count them as apply work, which blocked `verify` on `allComplete` while `sdd-sync`
refused to run without a verify report — a circular dependency. The heading, the ownership tags and the
prose form below now agree.

**They are therefore documented obligations, not checkboxes — this section is deliberately NOT part of
the implementation task list.** The implementation list is complete when Phase 5 ends, which is exactly
what the native `allComplete` gate for `verify` measures; `sdd-sync` still publishes canonical specs
only after a clean `verify-report.md`. Nothing below is lost in the conversion: every command, every
expected value and every `**Evidence:**` line is preserved verbatim as prose. The repository's own
precedent agrees — neither archived change that carried a spec delta enumerates a canonical-landing
task at all (`openspec/changes/archive/2026-09-14-fix-prepare-csv-config-tier/tasks.md` and
`openspec/changes/archive/2026-09-14-fix-cli-codebook-config/tasks.md`: zero `canonical`/`sync`
matches), because canonical landing happens inside the `sdd-sync` phase, after `verify`, outside the
task list.

- **6.1** Land **both** deltas in a **single sync operation**: append the four CI-08 Test Mapping rows to
  the canonical `openspec/specs/ci/spec.md` `## Test Mapping` table (after the CI-07 rows) **and** apply
  the `process-boundary` MODIFIED PB-10 block to `openspec/specs/process-boundary/spec.md` — one
  sentence replaced plus the `(Previously: …)` note, five scenarios byte-identical. Never one without the
  other: PB-10 forward-references `ci` CI-08, so a reader between two writes would see a requirement
  pointing at nothing. Use the change-root delta files as the source of truth; do not re-author text.
  <!-- sdd-owner: parent -->
  - **Evidence:** the two canonical files' diffs, produced by one sync run.

- **6.2** Post-sync reference invariant: `grep -c "CI-08" openspec/specs/ci/spec.md` → non-zero (the
  requirement plus its four rows); `grep -c "CI-08" openspec/specs/process-boundary/spec.md` → non-zero
  (PB-10's single-authority sentence names it). Whenever PB-10's restatement is present, `CI-08` must
  exist.
  <!-- sdd-owner: parent -->
  - **Evidence:** both grep counts.

- **6.3** Post-sync table arithmetic: `grep "^| CI-0" openspec/specs/ci/spec.md | wc -l` → **26**
  (22 + 4); `grep "^| CI-0" openspec/specs/ci/spec.md | grep -c "test_ci_workflows.py"` → **18**. Diff
  the canonical PB-10 block against the delta's `## MODIFIED` block → identical apart from the delta's
  framing header.
  <!-- sdd-owner: parent -->
  - **Evidence:** the two counts and the block diff.

- **6.4** Canonical-scope guard: `git diff --name-only` shows only those two canonical spec paths among
  `openspec/specs/**` — and record that `ci/spec.md`'s `## Purpose` paragraph (`:5-11`) deliberately
  stays unchanged even though its `CI-01..CI-06` enumeration is stale for CI-07 and now CI-08: that
  staleness is pre-existing, the CI-07 precedent left Purpose alone, and fixing it would edit canonical
  prose for another requirement's defect. Mention it in the PR body so a reviewer does not read it as an
  oversight.
  <!-- sdd-owner: parent -->
  - **Evidence:** `git diff --name-only` plus the recorded Purpose decision.

## Phase 7 — Final gates (inputs for the verify report)

- [x] 7.1 `uv run pytest tests/ -q` → the task 0.2 baseline **+3 passed, 0 failed, and an unchanged
  skipped count**. Paste the post-change summary beside the baseline; re-derive, never copy a figure from
  `AGENTS.md`.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both summary lines side by side.

- [x] 7.2 `uv run ruff check src/ tests/ scripts/` → clean, exit 0 (the enforced scope, `ci.yml:19`).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the command output and exit code.

- [x] 7.3 `uv run ruff format --check src/ tests/ scripts/` → exit 0, `68 files already formatted` — the
  D1 measurement re-confirmed on the pinned binary.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the command output and exit code.

- [x] 7.4 `uv run mypy src/ scripts/` → clean, exit 0 (the enforced scope, `ci.yml:21` /
  `.pre-commit-config.yaml:13`). `.python-version` is `3.13`, so no `--python` flag is needed
  (AGENTS.md rule 12). Do not widen to AC4's narrower documented wording — that drift is #212.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the command output and exit code.

- [x] 7.5 Full coverage gate (rule 14): `uv run coverage run -m pytest`, then
  `bash scripts/check_core_coverage.sh` → exit 0 with all four scoped rows (`cli.py`, `scanner.py`,
  `prepare.py`, `publish.py`) at **100.00%** and an empty `Missing` column; the TOTAL floor stays the
  config-owned `fail_under = 90` (`ci` CI-01), unweakened and not re-declared. If the interpreter is
  older than 3.13, pass `--python 3.13` explicitly (AGENTS.md rule 12).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the four 100.00% rows plus the script's exit code.

- [x] 7.6 Re-derive the docstring figures (never copy): `grep -c "^def test_" tests/test_ci_workflows.py`
  → **22**; `grep "^| CI-0" openspec/specs/ci/spec.md openspec/changes/2026-09-15-chore-ruff-single-authority/specs/ci/spec.md
  | grep -c "test_ci_workflows.py"` → **18** (the union is deliberately used, because the `18` figure is
  true of canonical + delta in both the pre- and post-sync states). If either differs, fix the **figure**,
  never the evidence.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both counts shown next to the docstring's quoted figures.

- [x] 7.7 Scope proof: `git diff --name-only` (tracked changes) → exactly `pyproject.toml`, `uv.lock`,
  `CONTRIBUTING.md`, `tests/test_ci_workflows.py`, plus, after sync, `openspec/specs/ci/spec.md` and
  `openspec/specs/process-boundary/spec.md`; **zero** `src/sofer/**`, zero `.github/workflows/**`, zero
  `README*` paths, zero `.pre-commit-config.yaml`. `git status --porcelain` shows only those paths plus
  this change's SDD artifacts — no mutation residue, no `_ruff_parity_probe.py`, no tracked probe file.
  <!-- sdd-owner: implementation -->
  - **Evidence:** both command outputs verbatim.

- [x] 7.8 Rules 7 and 13 statement, with commands rather than an assertion of intent:
  `git diff --name-only | grep -c "README"` → **0**;
  `git diff --name-only -- src/sofer/ | wc -l` → **0** (no CLI module changed, so no `help=` /
  `description=` string and no `_cmd_*` handler moved); `git diff -U0 -- src/sofer/cli.py` → empty. Since
  no CLI surface, subcommand or flag changes, no `README.md` / `README_ES.md` update and no mirroring is
  due. Record the statement explicitly so the verify phase does not flag a missing doc update; the only
  documented claim that changes is the `CONTRIBUTING.md:77` sentence (task 5.1).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the three command outputs (zero counts, empty diff) plus the recorded statement.

- [x] 7.9 Assemble the verify-report inputs, each as real pasted output rather than prose: the task 1.3
  RED-before-edit output; the three mutation legs (3.1, 3.2, 5.3) with their restore proofs; the task 2.5
  lock diff plus the task 2.6 `uv lock --check` exit code; task 4.1/4.2 (S4 legs A and B, with the
  mismatch message naming both versions); task 4.3/4.4 (AC3 verdicts plus the hook's `ruff==0.16.7`
  cache line); task 4.5/4.7 (whole-tree leg and the zero-match workflow greps); the PB-10 normative-literal
  check — extract the delta's PB-10 block up to the `(Previously:` line into a temp file and require
  `grep -cE "0\.16\.[0-9]"` → **0** — and the AC5 ownership correction from task 2.8.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the assembled block in the apply progress, one section per item, each with a command.

- [x] 7.10 Record the verify-phase scoping rules so verify cannot manufacture false failures:
  PB-10's *"Exactly the six test files changed"* and *"Formatting-only"* scenarios describe the historical
  #177 edit and **SHALL NOT** be measured against this diff (this change touches `pyproject.toml`,
  `uv.lock`, `CONTRIBUTING.md`, `tests/test_ci_workflows.py` and two spec files); the version-literal
  invariant is **normative clauses 1 → 0** with the `(Previously: …)` note exempt, so `grep "0.16"` over a
  whole spec file is not a check; canonical specs are `sdd-sync`'s write, never verify's.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the recorded three-rule note referenced by the verify report.

---

## Parent-owned steps (not tasks — no checkboxes, no delivery gates generated here)

- **Delivery**: one PR against `dev` carrying the work-unit commits (unit 1 → unit 6 above), per the
  branch flow in `AGENTS.md` rule 12. The forecast is Low risk against the 400-line budget, so no chain
  is selected, `ask-on-risk` is not exercised and **no `size:exception` is requested**. If the diff ever
  exceeds the budget or leaves the intended paths, stop and ask rather than chain.
- **Bounded review** using `.github/PULL_REQUEST_TEMPLATE.md` (every section filled with real output,
  including the named pre-existing `ci` `## Purpose` staleness from task 6.4), then archive.
- **Rollback**: one commit — `git revert`. Nothing is published, no tag moves, no migration exists, and
  no release action is taken. The only non-git artefact is the untracked, per-clone
  `.git/hooks/pre-commit` written by task 4.3, removable with `pre-commit uninstall`.

## Out of scope (explicit non-goals — do not do these in this change)

No CI format gate: PB-10 keeps enforcement on the local `ruff-format` hook and **#194** owns both the
gate decision and the un-staged-file gap (tasks 4.7, 7.8 assert zero `format --check` invocations under
`.github/workflows/**` before and after). No **#187** work (the nonexistent `ruff.toml` reference in
`CONTRIBUTING.md:77`'s second sentence stays byte-identical). No **#212** work (the narrower documented
commands at `CONTRIBUTING.md:22-31` are not edited; task 4.1 runs the enforced commands instead). No
**#184 / #187 / #214** version prose (`openspec/project.md:82`, `AGENTS.md`, and the gitignored
`openspec/config.yaml:7` stay untouched — including under #210's decision that the config file becomes
committed). No `src/sofer/**` edit at all. No edit to canonical specs during apply (task 6.1 is sync's
write) and no edit to `openspec/changes/archive/**` (history is a record, not state). No new pytest file,
no lockfile-parsing test, no hook-activation test, no test asserting the guards carry no literal, and no
fourth guard test (design §3.5). No extra CI-08 scenario for the lock duty (design §1.5). No tag
movement, no release, no publish, no `size:exception`, and no commit or PR from this phase.

**Closing note:** the forecast is **Low risk, ~184 changed lines** (functional ≈124 plus spec-delta
≈60), so this is a **single PR** and **no delivery gate is expected**. `Chained PRs recommended: No`,
`Decision needed before apply: No`, `Chain strategy: pending` (chaining deferred until selected — not
needed here). The guard tests stay in the same PR as the CI-08 scenario rows they satisfy; if a future
budget ruling counts SDD artifacts as review load, the first chained slice is the functional core
(`pyproject.toml` + `uv.lock` + the three guard tests + `CONTRIBUTING.md`).
