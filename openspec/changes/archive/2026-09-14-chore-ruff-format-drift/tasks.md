# Tasks: chore-ruff-format-drift

Closes #177 — `uv run ruff format --check src/ tests/` is red on six test files nobody touched
(`6 files would be reformatted, 61 files already formatted`, exit 1), so a contributor following
CONTRIBUTING.md gets a failure unrelated to their change. Fix: format **exactly** those six files
with the environment's ruff via `uv run`, zero logic change. Branch `chore/177-ruff-format-drift`
(`.git/HEAD` reads `ref: refs/heads/chore/177-ruff-format-drift`); cut from `dev`, zero commits ahead.
Store: **hybrid** — this file + Engram mirror under topic key `sdd/2026-09-14-chore-ruff-format-drift/tasks`.

**Phase routing already decided by the parent — recorded, not re-opened.** A spec delta **exists**
(this change's `specs/process-boundary/spec.md`, **PB-10**, five scenarios) and `design.md` exists.
`apply` produces the reformat and proves the **static** properties (D1 producer rule, `format --check`
/ `ruff check` / diff scope); `verify` owns the **behaviour-preservation** evidence (D2's three-legged
proof). `strict_tdd: false` (`openspec/config.yaml`) and there is no behaviour to unit-test, so no
RED → GREEN → TRIANGULATE → REFACTOR sequence applies: the evidence gates below are the verification.
Reused context: ambient ruff **0.16.0**; `.pre-commit-config.yaml:3` pins `ruff-pre-commit` **v0.16.7`;
grep for `format` over `.github/workflows/**` = **0 matches** (no CI gate armed).

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~41 executable (−/+) — six test files only (`test_ci_workflows.py`, `test_coverage_contract.py`, `test_mcp_registration.py`, `test_profile.py`, `test_publish.py`, `test_splits.py`); 82 `--diff` lines. Zero `src/sofer/**`, zero `.github/workflows/**`, zero `pyproject.toml` / `.pre-commit-config.yaml` / `uv.lock`. `proposal.md` / `spec.md` / `design.md` / this file are SDD artifacts, not review load |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR against `dev` (~41 lines, one commit) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not needed — single PR; chaining deferred until selected. ~41 lines against a 400-line budget, so `ask-on-risk` should not fire) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

### Suggested Work Units

| Unit | Goal | Likely PR | Boundaries (start → finish · verify · rollback) |
| ------ | ------ | ----------- | ------------------------------------------------ |
| 1 | Baseline **before any formatting**: branch + clean tree + pre-change `pytest` tally recorded verbatim | PR 1 | 1.1 → 1.2 · tally line recorded with 0 failures · no change to revert |
| 2 | `uv run ruff format` over the six named files — the only production diff | PR 1 | 2.1 → 2.3 · `format --check src/ tests/` exit 0, 0 to reformat; `git diff --stat` = exactly six files · `git checkout -- tests/` restores the pre-change bytes exactly |
| 3 | Static proofs (apply): `--check` exit 0, `--diff` empty, `ruff check` clean, no CI gate armed | PR 1 | 3.1 → 3.4 · all four green · revert with unit 2 |
| 4 | Behaviour-preservation evidence (verify): identical suite tally, `mypy` clean, COV-06 100%×4 | PR 1 | 4.1 → 4.4 · tally identical to 1.2 with 0 failures; four 100.00% rows · revert with unit 2 |
| 5 | Delivery + OpenSpec lifecycle: single PR against `dev`, bounded review, archive | PR 1 | 5.1 → 5.2 (parent-owned) · PR carries real command output; no chaining, no `size:exception` · one-commit `git revert` |

## Phase 1: Baseline (hard ordering — before any formatting)

- [x] 1.1 Confirm branch identity and a clean tree: `.git/HEAD` reads `ref: refs/heads/chore/177-ruff-format-drift` (do **not** work on `dev` — proposal's "commit lands on `dev`" risk) and `git status --short` is empty apart from this change's SDD artifacts, so the post-format `git diff --stat` isolates exactly six files. <!-- sdd-owner: implementation -->
  - **Evidence:** the `.git/HEAD` line and the `git status --short` output.
- [x] 1.2 Capture the **pre-change** `uv run pytest tests/ -q` tally and record it verbatim (measure, do not trust — `AGENTS.md` rule 6's `1149` is stale per #162; the prior change recorded `1766 passed, 6 skipped`). This MUST happen before task 2.1: a tally taken after the reformat makes PB-10 S3's "identical tally" claim unfalsifiable (design §6 ordering rule). <!-- sdd-owner: implementation -->
  - **Evidence:** the actual tail line with collected/passed/skipped counts.

## Phase 2: The reformat (six files, exactly)

- [x] 2.1 Run `uv run ruff format tests/test_ci_workflows.py tests/test_coverage_contract.py tests/test_mcp_registration.py tests/test_profile.py tests/test_publish.py tests/test_splits.py` — no directory argument, no other path. The producer MUST be the environment's ruff via `uv run` (design D1: same binary PB-10's gate invokes, so S1 passes by construction) — **never** the pre-commit `ruff-format` hook (0.16.7), an editor, or a hand edit. <!-- sdd-owner: implementation -->
  - **Evidence:** the command's own output (`N files reformatted`), plus the recorded producer identity (uv-run ambient ruff `0.16.0`) and an explicit statement that the hook was not used.
- [x] 2.2 Verify the diff is formatting-only and in scope: `git diff --stat` shows **exactly** those six files and zero paths under `src/sofer/`, `.github/`, `pyproject.toml`, `.pre-commit-config.yaml` or `uv.lock`; `git diff --numstat` totals ~41 changed lines. Any other path is a scope violation (proposal R4) — stop and revert, do not absorb. <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff --stat` and `git diff --numstat` output; the prohibited-path list asserted as 0.
- [x] 2.3 Spot-check that asserted string content in the two static contract guards is unchanged: `git diff tests/test_ci_workflows.py tests/test_coverage_contract.py` contains no change to any quoted YAML/TOML string literal (the formatter rewrites whitespace and token layout, never string contents — design §3). A content change is a bug to report, never to keep. <!-- sdd-owner: implementation -->
  - **Evidence:** the two guards' diff hunks, with only whitespace/reflow lines and no string-literal lines.

## Phase 3: Static proofs (apply-phase evidence)

- [x] 3.1 **V1** `uv run ruff format --check src/ tests/` → exit **0**, reporting **zero** files to reformat (PB-10 S1). <!-- sdd-owner: implementation -->
  - **Evidence:** the actual command output and exit code.
- [x] 3.2 **V1b** `uv run ruff format --diff src/ tests/` → emits no diff, so nothing is left to reformat (PB-10 S1). <!-- sdd-owner: implementation -->
  - **Evidence:** empty diff output.
- [x] 3.3 **V2** `uv run ruff check src/ tests/` → still `All checks passed!` (PB-10 S5) — no lint change was introduced alongside the format. <!-- sdd-owner: implementation -->
  - **Evidence:** the actual command output and exit code.
- [x] 3.4 **S4** Confirm no CI gate was armed: grep `format --check` (and `format`) over `.github/workflows/**` → **0 matches**, and no workflow path appears in `git diff --stat`. Enforcement stays the local pre-commit `ruff-format` hook on staged files; recurrence is owned by #194, not by this change (PB-10 S4). <!-- sdd-owner: implementation -->
  - **Evidence:** the grep result (0 matches) and the absence of `.github/` in the diff.

## Verification gates (verify phase — not apply tasks)

Owning phase: **verify** — these four behaviour-preservation gates must not be represented as unchecked apply tasks, because doing so deadlocked the flow (`apply` never counted as complete and `verify` stayed blocked).

- 4.1 **V3** `uv run pytest tests/ -q` after the reformat → counts **identical** to the tally recorded in 1.2 with **0 failures**; `tests/test_ci_workflows.py` and `tests/test_coverage_contract.py` pass with their asserted strings unchanged (PB-10 S3). These two guards assert on YAML/TOML **text**, which is why this evidence — not the diff — is what settles "formatting-only". <!-- sdd-owner: implementation -->
  - **Evidence:** the post-change tally line beside the 1.2 baseline, plus both guards' pass status.
- 4.2 **V4** `uv run mypy src/` → clean (32 source files), exit 0 with no flags. <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output and exit code.
- 4.3 **V5** `bash scripts/check_core_coverage.sh` → exit 0 with all four scoped rows (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) at **100.00%** and an empty `Missing` column (PB-10 S5, `coverage` COV-06). This is the leg that shows covered lines moved together with their branch data; nothing is weakened or re-declared. <!-- sdd-owner: implementation -->
  - **Evidence:** the four `coverage report --include=… --fail-under=100 -m` rows plus the script's exit code.
- 4.4 **V6b** `git diff --check` → clean (no whitespace errors left in the reformatted files). <!-- sdd-owner: implementation -->
  - **Evidence:** empty `git diff --check` output.

## Lifecycle (parent-owned — not apply tasks)

Owning phase: **parent session** (delivery + OpenSpec lifecycle, not `apply`) — these two steps must not be represented as unchecked apply tasks, because doing so deadlocked the flow (`apply` never counted as complete and `verify` stayed blocked).

- 5.1 Deliver as a **single work unit, single PR against `dev`** — no chaining, no `size:exception`, no tag movement (design §5). <!-- sdd-owner: parent -->
- 5.2 Populate the verify report with the unit 3–4 command output (not placeholders), run the bounded review of the six-file diff, then archive. Rollback = one-commit `git revert`; the tree returns to the red gate, which re-opens #177 rather than creating a new defect. <!-- sdd-owner: parent -->

## Out of scope (explicit non-goals — do not do these in this change)

No `ruff format --check` step in any workflow: issue **#194** owns that decision, and **PB-10 does not
close the drift class** — the drift can return on files nobody stages. No ruff version-pin alignment
(hook `v0.16.7` vs ambient `0.16.0`): issue **#195** owns it. No formatting change outside the six named
files; no logic, assertion, import or test-behaviour change — a reformat that changes behaviour is a bug
to report, never to absorb. No fix for stale counts in `AGENTS.md` rule 6 (#162), `openspec/project.md`
(#184) or the `ruff.toml` reference in `CONTRIBUTING.md` (#187). Do not touch `README.md` /
`README_ES.md`, `CONTRIBUTING.md`, `openspec/specs/**`, `openspec/config.yaml`,
`openspec/changes/archive/**`, or the still-active `openspec/changes/2026-09-14-chore-python-version-313/`.
Do not modify `proposal.md`, `design.md` or the spec delta (PB-10). Do not commit, push or open a PR.

**Closing note:** `apply` is a **single work unit** (one command over six files, ~41 changed lines) and
**no delivery gate is expected** — the forecast is Low risk against the 400-line budget, so `ask-on-risk`
is not exercised, no chaining is needed and `size:exception` is not requested. If the diff ever grows
past the budget or leaves the six files, stop and ask rather than chain.
