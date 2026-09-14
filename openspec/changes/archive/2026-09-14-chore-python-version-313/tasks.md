# Tasks: chore-python-version-313

Closes #178 (`dev-env: .python-version 3.10 makes local mypy and the COV-06 coverage
gate unsatisfiable (CI runs 3.13)`) on branch `chore/178-python-version-313`
(`.git/HEAD` reads `ref: refs/heads/chore/178-python-version-313`), cut from `dev`.
Artifact store: **hybrid** — this file plus an Engram observation mirrored under
topic key `sdd/2026-09-14-chore-python-version-313/tasks`. The change is a
one-line dev-env pin plus a documentation-note correction: `.python-version`
`3.10` → `3.13` (which removes the `tomli` backport from the development
environment, so the `except ImportError` arm of all five `_tomli` fallbacks
executes) and an in-place correction of the latent-issue bullet at
`AGENTS.md:90` (three modules → five; wrong quoted import form → the real
`import tomli as _tomli` / `import tomllib as _tomli`; the 3.13 rationale; the
`--python 3.13` escape hatch). **Phase routing already decided by the parent and
recorded here, not re-opened: no spec delta** — no requirement in
`openspec/specs/` governs `.python-version` or the AGENTS.md note, no capability
changes, so `sdd-spec` is deliberately skipped and `coverage` COV-01/COV-02/COV-06
plus `ci` CI-01/CI-06 are cross-referenced and explicitly left untouched — **and
no design phase**, because the approach, decision points, rollback and
verification approach are already resolved in the proposal; a `design.md` would
be pure ceremony. Precedent for skipping both: the archived change
`openspec/changes/archive/2026-09-12-test-cli-mcp-parity-guard/` contains only
`proposal.md`, `tasks.md`, `verify-report.md`, `archive-report.md` — no `specs/`,
no `design.md` (verified by listing the directory). Next phase after tasks is
`apply` as a **single work unit**, then `verify`.

**Citation check on the parent's "one factual correction" (measured, refuted).**
The parent flagged the proposal's `AGENTS.md:90` citation as stale. Direct
measurement on this branch refutes that: `### 12. Release process` is at
`AGENTS.md:77`, the latent-issue bullet is at **`AGENTS.md:90`**, and
`### 13. README / README_ES sync` is at `:93` (rule 12 spans `:77`–`:92`). The
proposal's line number is accurate; the real line is 90, and it is cited as 90
from here on. The three substantive corrections to the note's *content* (module
list short by two, wrong quoted fallback form, missing rationale/escape hatch)
stand and are in scope. Also verified read-only: the same stale three-module note
exists at `openspec/changes/archive/2026-08-26-installable-cli-pypi/design.md:243`
and stays there — archived, frozen historical record.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~3–12 executable (−/+) — `.python-version` exactly 1 line (`3.10` → `3.13`, no other content in the file) and `AGENTS.md` rule 12's bullet ~2–10 lines (five modules named, real fallback form, 3.13 rationale, `--python 3.13` escape hatch, "do not add mypy to the version matrix" kept). `proposal.md`/`tasks.md` are SDD artifacts, not review load; no production code, no test line changes |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR against `dev` (one file edit of one line + one docs note) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not needed — single PR; chaining deferred until selected. The forecast is ~3–12 lines against a 400-line budget, so `ask-on-risk` should not fire) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

### Suggested Work Units

| Unit | Goal | Likely PR | Boundaries (start → finish · verify · rollback) |
| ------ | ------ | ----------- | ------------------------------------------------ |
| 1 | Pin edit: `.python-version` `3.10` → `3.13` (1 line) | PR 1 | 1.1 → 1.2 · `read .python-version` = `3.13` and `git diff --stat` shows 1 changed line in that file only · `git checkout -- .python-version` restores `3.10` exactly |
| 2 | Docs note: correct the `AGENTS.md:90` rule-12 bullet in place (five modules, real fallback form, 3.13 rationale, escape hatch; surrounding bullets byte-for-byte) | PR 1 | 2.1 → 2.2 · `git diff -U0 AGENTS.md` touches only line 90 (or the contiguous bullet block ending before the "Branch flow" bullet) and no other section moved · `git checkout -- AGENTS.md` restores the note text exactly |
| 3 | `CONTRIBUTING.md` no-edit decision recorded and verified (stays audit-able rather than an omission) | PR 1 | 3.1 → 3.2 · `git diff -- CONTRIBUTING.md` empty and the CI-06 S2 pinned strings still present verbatim · nothing to roll back (zero diff) |
| 4 | Evidence gates V1–V8 recorded with actual command output | PR 1 | 4.1 → 4.8 · all eight evidence rows pass or are escalated (V5 has an explicit escalation path) · revert units 1+2; V6 catches any over-reach mechanically |
| 5 | OpenSpec lifecycle: verify-report, bounded review of the two-file diff, PR against `dev`, archive | PR 1 | 5.1 → 5.3 (parent-owned) · verify-report carries real output; archive merge lands on `dev` · docs-only revert; the production diff is 1 pin line + 1 note |

Out of scope boundaries to respect during units 1–4: do NOT touch
`pyproject.toml` (`requires-python = ">=3.10"` at `:6`, the `tomli` marker at
`:27`, `[tool.mypy] python_version = "3.10"` at `:74`, `line-length = 100` at
`:58`, `fail_under = 90` at `:98`), `src/sofer/**` (zero paths — the structural
fix is #192), `.github/workflows/**`, `scripts/check_core_coverage.sh`,
`.pre-commit-config.yaml`, `README.md` / `README_ES.md`,
`openspec/config.yaml` (gitignored local state), `openspec/specs/**`, and
`openspec/changes/archive/**` (including
`archive/2026-08-26-installable-cli-pypi/design.md:243`, which carries the same
stale three-module note and is a frozen record). Any diff line outside
`.python-version` + `AGENTS.md` is a scope violation (proposal R4) and is
rejected at apply/verify per the mechanical check in task 4.6.

## Deliberate decisions carried forward (from the proposal, not re-litigated)

- **No new or adjusted test, and no vacuous test invented** (proposal Decision
  Point 1). The pin's effect on `mypy`/coverage is not pytest-assertable: at gate
  time "the pin is `3.13`", "`mypy src/` exits 0" and "`cli.py` is at 100.00%"
  are **command-evidence** facts, matching the `coverage` spec precedent that
  measured percentages and gate exit codes are verify-phase runtime evidence,
  never test assertions. A static drift guard (`assert .python-version ==`
  the CI lint/coverage pin) was considered and **rejected**: it cannot prove the
  gates are green (vacuous as proof) and would break
  `tests/test_ci_workflows.py`'s self-declared 1:1 spec-scenario contract unless
  this change also created a `ci` spec delta — scope creep into the `ci` domain
  for a one-line pin. **Tradeoff accepted explicitly:** a future revert of
  `.python-version` to `3.10` would go uncaught by pytest; CI's lint/coverage
  jobs are pinned to `3.13` and remain the authoritative gates, and recurrence
  prevention is owned by issue #192 (the structural fix), not by this chore.
- **Consequence for sequencing:** `strict_tdd: false` (`openspec/config.yaml`)
  and there is no test to write, so no RED → GREEN → TRIANGULATE → REFACTOR
  sequence applies to this change. The evidence gate phase (V1–V8) is the
  verification, replacing a test phase.
- **No spec delta / no design phase** (phase routing above, with precedent).
- **`CONTRIBUTING.md` gets no edit** (proposal Decision Point 2): every
  documented command is `uv run …` and pin-agnostic, and
  `tests/test_ci_workflows.py::test_contributing_documents_coverage_floor`
  (`:415`) pins the strings `"90%"`, `"uv run coverage run -m pytest"`,
  `"uv run coverage report -m"` and the absence of `"no drop in coverage"`.
  Task unit 3 makes this decision mechanically auditable rather than an
  omission. The contributor-facing `--python 3.13` guidance lands in the
  AGENTS.md rule-12 note (unit 2).

## Phase 1: Baseline confirmation (read-only, no red-state re-measurement)

- [x] 1.1 Confirm branch identity and pre-change file state: `.git/HEAD` reads `ref: refs/heads/chore/178-python-version-313`; `.python-version` contains exactly `3.10`; `AGENTS.md:90` still carries the stale note. Do **not** re-run the red baseline commands — the proposal's `dev@2f57f8e` mypy/COV-06 measurements are reused verbatim per the handoff. <!-- sdd-owner: implementation -->
  - **Evidence:** recorded `.git/HEAD` line, `.python-version` content, and the pre-edit `AGENTS.md:90` text.
- [x] 1.2 Confirm the working tree is clean before editing (`git status --short` empty) so that the post-edit `git diff --stat` in task 4.6 isolates this change's two files exactly. <!-- sdd-owner: implementation -->
  - **Evidence:** `git status --short` output (empty, or pre-existing artifacts named and explained).

## Phase 2: The pin edit (`.python-version`)

- [x] 2.1 Set `.python-version` to `3.13` — one line, exactly `3.13`, no trailing blank line, no comment, no other content. This is the only behavioral edit of the change; it is what lets the `except ImportError` arm of the five `_tomli` fallbacks (`src/sofer/cli.py:438-440`, `config.py:151-153`, `mcp_registration.py:128-130`, `mcp_server.py:687-689`, `model.py:397-399`) execute in the development environment. Do NOT touch `requires-python` (`pyproject.toml:6`, stays `>=3.10`) or `[tool.mypy] python_version` (`pyproject.toml:74`, stays `"3.10"` — it tracks the minimum language level, and the measured green 3.13 result was obtained with it unchanged). <!-- sdd-owner: implementation -->
  - **Evidence:** `read .python-version` returns exactly `3.13`; `git diff -- .python-version` shows one removed `3.10` line and one added `3.13` line.
- [x] 2.2 Confirm the pin equals the CI gate interpreter: the value is identical to `.github/workflows/ci.yml:15` (lint job) and `:61` (coverage job) `python-version: "3.13"` — read those lines, change nothing there. <!-- sdd-owner: implementation -->
  - **Evidence:** the three values recorded side by side (`3.13` / `"3.13"` / `"3.13"`); `.github/` has zero diff lines.

## Phase 3: Correct the `AGENTS.md` rule-12 note in place (`AGENTS.md:90`)

- [x] 3.1 Rewrite the latent-issue bullet at `AGENTS.md:90` so it is accurate, in four ways, keeping the existing "do not add mypy to the version matrix" instruction intact (that instruction is still correct and is not weakened): (a) name **all five** modules — `cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py` (the current text names three: `model.py`, `config.py`, `cli.py`); (b) quote the **real** fallback form `import tomli as _tomli` / `import tomllib as _tomli` (the current text says `import tomli as tomllib`, which appears nowhere in `src/sofer/`); (c) record that the pin is `3.13` because a `3.10` development environment installs the `tomli` backport (declared at `pyproject.toml:27`), which makes the local `mypy` and COV-06 gates unsatisfiable by construction; (d) state the `--python 3.13` escape hatch — a contributor on an older interpreter must pass `--python 3.13` explicitly for those two gates. Keep the note **in place** at `AGENTS.md:90`; do not relocate it into rule 5 (pre-commit) or rule 14 (coverage) — docs-structure change is out of scope. <!-- sdd-owner: implementation -->
  - **Evidence:** the new bullet text, and a check that it names five modules, the real `_tomli` fallback form, the 3.13 rationale and the `--python 3.13` escape hatch (this is evidence row V7).
- [x] 3.2 Preserve the surrounding rule-12 bullets **byte-for-byte** unless a line must change to stay truthful: the versioning bullet, the "Never move or delete a pushed tag" bullet, and the "Branch flow" bullet stay as-is; rule 12's header and prose (`AGENTS.md:77`–`:79`) and `### 13.` (`:93`) stay untouched. Verify with `git diff -U0 -- AGENTS.md` that only the latent-issue bullet's line range changed (no whitespace/reflow churn elsewhere). <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff -U0 -- AGENTS.md` shows the change confined to the rule-12 bullet region with no other hunk.

## Phase 4: `CONTRIBUTING.md` — explicit no-edit unit (decision made auditable)

- [x] 4.1 Record and verify the **no edit** decision (proposal Decision Point 2): every command in `CONTRIBUTING.md` (`uv sync`, `uv run pytest`, `uv run mypy src/` at `:28`, `uv run ruff check src/ tests/` at `:29`, `uv run coverage run -m pytest` at `:30`, `uv run coverage report -m` at `:31`) resolves the interpreter through uv/`.python-version`, so no command string becomes wrong under the new pin. The only change is that the commands now work, which is the intent. <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff -- CONTRIBUTING.md` is empty (zero lines).
- [x] 4.2 Confirm the CI-06 S2 pins still hold **by construction** because the file was untouched: the strings `"90%"`, `"uv run coverage run -m pytest"`, `"uv run coverage report -m"` are present and `"no drop in coverage"` is absent, i.e. `tests/test_ci_workflows.py::test_contributing_documents_coverage_floor` (`:415`) is not disturbed. Do not add a "dev environment is 3.13" line here — that guidance belongs in the AGENTS.md rule-12 note (task 3.1). <!-- sdd-owner: implementation -->
  - **Evidence:** the four string checks recorded; empty `git diff -- CONTRIBUTING.md`.

## Phase 5: Evidence gates V1–V8 (acceptance evidence, command output not placeholders)

> Verification for this change is **command evidence**, not pytest assertions
> (Deliberate decisions section). Each task below carries its evidence row
> verbatim from the proposal. Prohibited: reporting green without running the
> command (proposal R1).

| # | Evidence step | Command | Pass condition |
| --- | --- | --- | --- |
| V1 | The pin is the gate interpreter | read `.python-version` | `3.13` (exactly), and identical to the value `ci.yml:15` / `:61` pin |
| V2 | Local mypy gate green, no flags | `uv run mypy src/` | exit 0, 0 errors (the 5 `[no-redef]` errors at `cli.py:440`, `config.py:153`, `mcp_registration.py:130`, `mcp_server.py:689`, `model.py:399` gone) |
| V3 | Pre-commit hook surface green | `uv run mypy src/ scripts/` | exit 0 (this is the exact `entry:` of the local hook at `.pre-commit-config.yaml:11-16` that was failing every commit) |
| V4 | COV-06 gates green, no flags | `uv run coverage run -m pytest` then `bash scripts/check_core_coverage.sh` | exit 0; `cli.py` / `scanner.py` / `prepare.py` / `publish.py` each `100%` with an empty `Missing` column (in particular `cli.py:439-440` no longer listed as missing) |
| V5 | Full suite green after the bump | `uv run pytest tests/ -q` | full suite actually executed; result recorded verbatim. The `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` observation from the isolated 3.13 run MUST be explicitly reported — either it passes on the bumped pin (observation closed as environment artifact) or it fails and is escalated as its own finding (R2) rather than silently accepted |
| V6 | Nothing weakened | config + diff inspection | `pyproject.toml` absent from the diff (so `fail_under = 90`, `show_missing`, `python_version = "3.10"` all unchanged); no test count changed; no `# pragma: no cover` introduced; zero `src/sofer/` paths; zero `.github/workflows/` paths; `CONTRIBUTING.md` untouched |
| V7 | AGENTS.md note accuracy | read `AGENTS.md` rule 12 | the note names all five modules, quotes the real fallback form, records the 3.13 rationale, and states the `--python 3.13` escape hatch for older interpreters |
| V8 | Docs/agent-instruction tests still green | `uv run pytest tests/test_ci_workflows.py -q` | green — in particular `test_agents_md_declares_core_100_mandate` (`:233`, rule-14 regex, unaffected by a rule-12 edit) and `test_contributing_documents_coverage_floor` (`:415`, unaffected because CONTRIBUTING.md is untouched) |

- [x] 5.1 **V1** Read `.python-version` and record that it is exactly `3.13` and identical to the `ci.yml:15` / `:61` pin value. <!-- sdd-owner: implementation -->
  - **Evidence:** the file content plus the two `ci.yml` values quoted side by side.
- [x] 5.2 **V2** Run `uv run mypy src/` and record the output verbatim: exit 0, zero errors — specifically the absence of the five `[no-redef]` errors at `src/sofer/cli.py:440`, `config.py:153`, `mcp_registration.py:130`, `mcp_server.py:689`, `model.py:399` that the 3.10 baseline produced. <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output (e.g. `Success: no issues found in 32 source files`) and exit code.
- [x] 5.3 **V3** Run `uv run mypy src/ scripts/` — the exact `.pre-commit-config.yaml` `entry:` that failed on every commit — and record exit 0. Confirm the working commit happens with hooks enabled (never `--no-verify`, AGENTS.md rule 5). <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output and exit code.
- [ ] 5.4 **V4** Run `uv run coverage run -m pytest`, then `bash scripts/check_core_coverage.sh`, and record the four scoped rows verbatim: `cli.py`, `scanner.py`, `prepare.py`, `publish.py` each `100%` with an empty `Missing` column, exit 0, and `cli.py:439-440` no longer reported missing. Note that on the 3.10 baseline `set -euo pipefail` aborted at `cli.py`, leaving three of the four COV-06 gates unverified — this run must show all four executing. <!-- sdd-owner: implementation -->
  - **Evidence:** the four `coverage report --include=… --fail-under=100 -m` rows plus the script's exit code (0).
- [ ] 5.5 **V5** Run `uv run pytest tests/ -q` with the full suite actually executed and record the tally verbatim. Explicitly report `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version`, which failed in the isolated 3.13 experiment for an unpinned reason. Working hypothesis to **confirm by the run, not assume**: stale build/editable-install metadata — `src/sofer/_version.py` resolves the version solely from `importlib.metadata.version("sofer")`, the isolated env reported `0.3.12.dev57+g059ffc637`, `g059ffc637` is not an ancestor of HEAD, and zero git tags are reachable from `dev`; CI's 3.13 leg is green. Disposition: if it reproduces, clean the build/venv metadata (fresh `uv sync`, rebuild) and re-run; if it still fails, **escalate it as its own finding/issue — never absorb it into this change and never weaken, skip or xfail the test**. <!-- sdd-owner: implementation -->
  - **Evidence:** the actual `uv run pytest tests/ -q` tally line (baseline to protect: `1766 passed, 6 skipped`) plus an explicit pass/fail/escalated statement for that single test.
- [x] 5.6 **V6** Mechanical scope check, recorded as raw output: `git diff --stat` shows exactly two modified files (`.python-version`, `AGENTS.md`) plus this change's SDD artifacts; `git diff -- src/ pyproject.toml .github/ README.md README_ES.md CONTRIBUTING.md openspec/specs` is **empty**; grep confirms no `# pragma: no cover` was introduced anywhere and `fail_under = 90` is intact at `pyproject.toml:98`; no stale test count in `AGENTS.md` rule 6 (issue #162) or `openspec/project.md` (issue #184) was "fixed" here; no test file was reformatted (issue #177) and no `ruff format --check` CI gate was added. <!-- sdd-owner: implementation -->
  - **Evidence:** the `git diff --stat` and `git diff` outputs, the pragma grep result, and the `fail_under` line.
- [x] 5.7 **V7** Read `AGENTS.md` rule 12 (`:77`–`:92`) and confirm the corrected note at `:90`: names all five modules (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`), quotes the real fallback form (`import tomli as _tomli` / `import tomllib as _tomli`), records the 3.13-because-3.10-installs-`tomli` rationale, keeps "do not add mypy to the version matrix", and states the `--python 3.13` escape hatch for the two gates on an older interpreter. <!-- sdd-owner: implementation -->
  - **Evidence:** the corrected bullet quoted in full, with each of the five required elements marked present.
- [x] 5.8 **V8** Run `uv run pytest tests/test_ci_workflows.py -q` and record it green, proving neither the rule-12 edit nor the pin disturbs the COV-06/CI static contracts — in particular `test_agents_md_declares_core_100_mandate` (`:233`, extracts rule 14 via `### 14.` up to `### 15.`/EOF, so a rule-12 edit above it is outside the regex) and `test_contributing_documents_coverage_floor` (`:415`). <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output and exit code.

## Phase 6: OpenSpec lifecycle + bounded review (parent-owned, after implementation)

- [ ] 6.1 Populate `openspec/changes/2026-09-14-chore-python-version-313/verify-report.md` with the V1–V8 results using actual command output (not placeholders), including the V5 disposition for `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` — passed (observation closed as environment artifact) or escalated as its own finding. <!-- sdd-owner: parent -->
- [ ] 6.2 Post-apply bounded review of the PR diff (1 pin line + the rule-12 note bullet), confirm the no-spec-delta and no-design-phase routing still holds for archive, then archive the change. Rollback = single-commit revert: the production diff is one line in `.python-version` plus one documentation bullet, so the revert restores `3.10` and the note text exactly; nothing destructive, publishing, networked, or user-facing is touched, and the wheel/sdist contract (`Requires-Python: >=3.10`, `tomli>=2.0; python_version < '3.11'`) is untouched in both directions. <!-- sdd-owner: parent -->
- [ ] 6.3 Confirm the cross-references were honored at archive time: `coverage` COV-01/COV-02/COV-06 and `ci` CI-01/CI-06 were left untouched (no delta file, no canonical spec edit), issue #178 is closed by the PR, and the structural follow-up remains open under issue #192. <!-- sdd-owner: parent -->

## Follow-ups (out of scope, tracked — no work in this change)

- **#192** — structural fix: make `tomli` unconditional and collapse the five
  duplicated `_tomli` fallbacks into one shared helper; this is what removes the
  pin↔gate coupling instead of freezing it (and is where recurrence prevention
  lives, per the no-test decision).
- **#177** — six drifted test files need reformatting; no `ruff format --check`
  CI gate is added here.
- **#162** / **#184** — stale test counts in `AGENTS.md` rule 6 and
  `openspec/project.md`.
- `openspec/changes/archive/2026-08-26-installable-cli-pypi/design.md:243` —
  carries the same stale three-module note; archived historical record, not
  edited (verified read-only).

**Closing note:** `apply` is a **single work unit** (two files: one pin line +
one documentation bullet) and **no delivery gate is expected** — the forecast is
~3–12 changed lines against the 400-line budget, so `ask-on-risk` is not
exercised, no chaining is needed, and `size:exception` is not requested. If the
diff ever grows past the budget, stop and ask rather than chain.
