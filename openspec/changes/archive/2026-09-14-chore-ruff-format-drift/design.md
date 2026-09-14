# Design: chore-ruff-format-drift (issue #177)

**Status**: complete
**Change**: `2026-09-14-chore-ruff-format-drift` · **Branch**: `chore/177-ruff-format-drift` — `.git/HEAD` reads `ref: refs/heads/chore/177-ruff-format-drift` (verified this phase; discharges the proposal's stale "HEAD on `dev`" row, which the spec delta also records and `proposal.md` deliberately is not edited for)
**Phase**: design — after proposal + `process-boundary` delta (PB-10, five scenarios). Strict-TDD off: there is no test to write (PB-10's rule-6 resolution).
**Store**: hybrid — this file plus an Engram mirror under `sdd/2026-09-14-chore-ruff-format-drift/design`.

Read: `proposal.md`, `specs/process-boundary/spec.md` (PB-10), `.pre-commit-config.yaml`, `pyproject.toml` (`[tool.ruff]`, `[dependency-groups] dev`), `.github/workflows/ci.yml`, `scripts/check_core_coverage.sh`, and the immediately preceding `2026-09-14-chore-python-version-313/design.md` for house shape.

---

## 1. What this design decides

**Almost nothing — and saying so is the design.** No architectural surface: no module, interface, data-flow, dependency or workflow change (§5). The approach and evidence set were settled in the proposal and are not re-opened. What a reviewer cannot reconstruct from the proposal is *which binary* is allowed to produce the reformat, *why the change is provably formatting-only*, the rejected alternatives with dispositions, the blast radius, and the ordering rule that makes the behaviour claim falsifiable. That is all this file carries.

## 2. D1 — The reformat is produced by `uv run ruff format`, and by nothing else

The environment's ruff is **0.16.0**; `.pre-commit-config.yaml` pins `ruff-pre-commit` at **`rev: v0.16.7`**; `pyproject.toml`'s dev group only floor-bounds it (`ruff>=0.9.0`, `pyproject.toml:47`).

| Producer | Verdict |
| --- | --- |
| `uv run ruff format <six files>` | **Adopted.** It is the *same binary* PB-10's gate command invokes, so `uv run ruff format --check src/ tests/` passes **by construction**, not by luck |
| The pre-commit `ruff-format` hook (0.16.7) | **Rejected.** A different formatter version may leave the gate red after the work is done — a real possibility here, since the hook's output was never measured against 0.16.0 |
| An editor / hand edit | **Rejected** for the same reason: unverifiable formatter identity |

Consequence recorded, not fixed: the **two-version inconsistency** (hook `v0.16.7` vs ambient `0.16.0`) is filed as **issue #195** and is out of scope. Aligning the pins is a dependency change that must not ride along in a whitespace-only commit (§3B).

## 3. D2 — Why the change is formatting-only, and how that is proven mechanically

**The argument.** `ruff format` rewrites whitespace and token layout; it never rewrites string contents. That matters because two of the six files are **static contract guards that assert on YAML/TOML text** — `tests/test_ci_workflows.py` and `tests/test_coverage_contract.py` — where a content rewrite would silently falsify an assertion.

**The proof (three legs, all command output):**

1. `uv run pytest tests/ -q` → tally **identical** to the baseline recorded before the reformat, **0 failures**, both contract guards green (PB-10 S3, re-using PB-05's gate).
2. `uv run ruff check src/ tests/` → still `All checks passed!` (PB-10 S5, V2).
3. COV-06 still **100% for all four modules** — `bash scripts/check_core_coverage.sh` exit 0, four rows at 100.00%, empty `Missing`. This is the leg that shows the *covered lines moved together with their branch data*: a reflow that shifted an executable line without its branch would show up here.

## 4. D3 — Alternatives considered and rejected

| # | Alternative | Why rejected | Disposition |
| --- | --- | --- | --- |
| A | **Arm `ruff format --check` in `ci.yml` now** | A policy change: a new workflow step, a new `ci` spec scenario, and a workflow-shape test. PB-10 deliberately adds no CI step, so a `ci` clause naming one would be false | **Filed as #194.** It also owns recurrence: PB-10 does not claim to close the defect class |
| B | **Align the ruff version pins first** | A dependency change (`uv.lock`, hook rev) riding on a whitespace-only commit — unreviewable as one unit and untestable by the six-file diff | **Filed as #195** |
| C | **Rely on the pre-commit hook alone** | A contributor who does not install hooks is not gated at all; and the hook runs on **staged** files only — which is precisely why this drift survived on six files nobody edits | Rejected. Enforcement stays the hook (PB-10 S4), with the gap owned by #194 |

## 5. Blast radius, and rollback

| Surface | Effect |
| --- | --- |
| `tests/{test_ci_workflows,test_coverage_contract,test_mcp_registration,test_profile,test_publish,test_splits}.py` | Reformatted — six files, ~41 changed lines (82 `--diff` lines) |
| `src/sofer/**` | **Zero paths.** No interface, data flow, dependency, workflow or config change |
| `openspec/changes/2026-09-14-chore-ruff-format-drift/**` | This design + mirror. `proposal.md` and the spec delta untouched |

Well under the 400-line budget → single PR, no chaining, no `size:exception`. **Rollback**: one commit, one `git revert`; nothing published, no data, no migration, no tag movement. A reverted tree returns to the red gate — issue #177 re-opened, not a new defect.

## 6. Verification approach and the apply/verify split

| Phase | Owns | Rows |
| --- | --- | --- |
| **apply** | Produces the reformat; proves the *static* properties | `format --check` exit 0 with 0 to reformat + empty `format --diff`; `ruff check` clean; `git diff --stat` = exactly six files, zero `src/sofer/` / `.github/workflows/` / `pyproject.toml` paths; zero `format --check` matches under `.github/workflows/` |
| **verify** | Owns *behaviour-preservation* evidence | Full suite with the baseline tally recorded **before** the reformat; `uv run mypy src/` clean (32 files); `bash scripts/check_core_coverage.sh` exit 0, four 100.00% rows |

**One ordering rule, stated because it is what makes the claim falsifiable: the baseline `pytest` tally MUST be captured *before* `ruff format` runs.** A tally taken afterwards proves nothing — there would be no pre-state to compare against, and "identical tally" would degrade into an unfalsifiable assertion. PB-10 S3 is written as "the tally recorded immediately before the reformat" for exactly this reason.

## 7. Consistency with the PB-10 delta, and the boundary of what is claimed

PB-10 is **additive** (PB-01..PB-09 byte-identical), hosted in `process-boundary` because PB-07 already owns "quality gates" as a category; the alternative home `ci` CI-06 was rejected in the delta because it owns workflow/documentation truth and this change adds no workflow step. This design adds no requirement of its own and satisfies each scenario by the anchors in §2–§6: S1 ← §2 + §6 (apply), S2 ← §5 + §6 (apply), S3 ← §3 + §6 ordering rule (verify), S4 ← §4C + §6 (apply), S5 ← §3.3 + §6 (verify).

**Open questions: none blocking.** Assumptions adopted unchanged: ship six-file hygiene without arming a gate; leave the pin mismatch as a follow-up. **What the design does not decide** (and must not be read as approving): no CI step (#194), no pin change (#195), no formatting outside the six files, no fix for #162/#184/#187, no new test, no `src/sofer/**` edit, no commit/push/PR/tag.

---

## Output contract

- **status**: complete
- **executive_summary**: The change has no architectural surface — a mechanical reformat of six test files, ~41 changed lines — so this design's value is in recording the few decisions that matter. It fixes the *producer* of the reformat: `uv run ruff format`, the same binary PB-10's gate invokes (ambient 0.16.0), with the pre-commit hook (0.16.7) and any editor or hand edit rejected because a different formatter version could leave the gate red after the work was done — the underlying two-version inconsistency filed as #195, out of scope. It states the formatting-only argument (the formatter rewrites whitespace and token layout, never string contents, which matters because two of the six files are static contract guards asserting on YAML/TOML text) and its three-legged mechanical proof: identical `pytest` tally with 0 failures and both guards green, `ruff check` still clean, and COV-06 still 100% on all four modules — the leg showing covered lines moved together with their branch data. Three rejected alternatives carry dispositions: arm `format --check` in CI (#194, a policy change PB-10 deliberately does not make), align the ruff pins (#195, a dependency change that must not ride on a whitespace commit), rely on the hook alone (an un-hooked contributor is not gated, and the hook sees staged files only — exactly why the drift survived). Blast radius is six test files with zero `src/sofer/**` paths and no interface, data-flow, dependency or workflow change; rollback is one `git revert`. The apply/verify split is adopted as given — apply proves the static properties, verify owns behaviour preservation — with one ordering rule emphasized: the baseline suite tally must be captured **before** the reformat, or "identical tally" becomes unfalsifiable.
- **artifacts**:
  - `openspec/changes/2026-09-14-chore-ruff-format-drift/design.md` (this file)
  - Engram: topic key `sdd/2026-09-14-chore-ruff-format-drift/design`, type `architecture`
- **next_recommended**: `tasks` — PB-10's five scenarios, the apply/verify split, and the baseline-before-format ordering rule are now all pinned, so `tasks` can enumerate work units against them.
- **risks**: R1 the "passes by construction" claim is only true if the reformat is actually produced by `uv run ruff format` (mitigation: D1 is a hard constraint in tasks, and apply's `format --diff` emptiness is the check); R2 the two contract guards could in principle be perturbed (mitigation: formatter does not rewrite string contents; verify's S3 run exercises both); R3 the baseline tally is captured too late (mitigation: ordering rule stated in §6 and carried into tasks); R4 scope creep into #194/#195 (mitigation: `git diff --stat` = exactly six files, zero workflow/`pyproject.toml` paths); R5 the drift returns on unstaged files — **accepted and named**, owned by #194, never claimed as closed by PB-10.
- **skill_resolution**: none — no executor/phase skill path was injected for this design phase and no SDD-design skill exists in the available-skills list; the phase was completed from the injected SDD design contract directly (a read-and-write artifact, so no degraded fallback was required).

## Key Learnings

- **A formatter version is a correctness input, not an implementation detail.** With the gate binary (0.16.0) and the hook binary (0.16.7) unpinned against each other, "I ran the formatter" does not imply "the gate is green". Naming the exact producer converts a hope into a construction.
- **A whitespace-only change still needs a falsifiable behaviour claim.** The proof is not "the tests pass" but "the tally equals a tally taken *before*" — hence the ordering rule. Capture order is part of the evidence design.
- **Two of six files were static contract guards.** That is what makes "formatting-only" non-obvious here and why the formatter's string-content guarantee had to be stated rather than assumed.
- **Refusing to arm the gate is a decision that must be written down.** PB-10 deliberately leaves the defect class open; #194 owns it. An artifact that stayed silent on this would read as if the drift could not return.
