```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:cf066e208fac4f81896881c23dd6789f679a5785f9649565f1ac2663cf706894
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 1/1
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:972b6d9f8396d9e1e64d003e367faccfb85bb67287fa9f1d019278f177839c31
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
```

# Verify report: chore-cov01-floors-status-quo

**Change** `2026-09-15-chore-cov01-floors-status-quo` (GitHub #215, option (b)) · branch
`chore/215-cov01-floors-status-quo` · store **hybrid** (report path
`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/verify-report.md`; Engram topic key
`sdd/2026-09-15-chore-cov01-floors-status-quo/verify-report`) · verified at branch `HEAD` = `ac8af03`
(one commit, two files).

## Status

**PASS.** 33/33 tasks complete, 1/1 requirement covered, 1/1 scenario covered, all three ban-pinning guards
green **unmodified**, full suite green with a re-derived tally, build command clean, diff scope exactly as
designed, zero prohibited paths, zero blockers, zero critical findings.

Every evidence item below was **re-run by this phase**; none is inherited from `apply-progress.md`. Where a
recorded number was re-derived, the re-derived value is reported.

- `evidence_revision` is the native runtime **candidate identity at verify launch**, read from
  `gentle-ai sdd-attempt status --cwd "C:\Users\elaze\Desktop\sofer" --change
  "2026-09-15-chore-cov01-floors-status-quo"` → `objective.initial_candidate_identity`
  (`sha256:cf066e20…`), identical to the acquire response's `begin_candidate_identity`. The bounded attempt
  was claimed first: `gentle-ai sdd-attempt acquire … --request-id verify-215-cov07-static-evidence-01
  --max-attempts 2 --max-changed-lines 400 --untracked-scope exclude
  --expected-untracked-inventory sha256:413d890f…` → `{"state": "proceed", "token":
  "sha256:a705527f…"}`.
- `test_output_hash` is the sha256 of the exact captured stdout+stderr bytes of the full-suite run
  (`1785 passed, 6 skipped, 1 warning in 58.20s`, 2472 bytes, exit 0).
- `build_output_hash` is the sha256 of the exact captured stdout+stderr bytes of the chained
  `config.yaml` `rules.verify.build_command` (`All checks passed!` · `Success: no issues found in 32 source
  files`, exit 0). It is byte-identical to the hash recorded for the same command in the archived
  `2026-09-15-chore-ruff-format-hook-scope` verify report (`beb5f2fb…`), i.e. the toolchain output is
  unchanged across the two changes.

## Spec coverage

Delta retrieved and counted from the artifact itself
(`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`, 117 lines):
`grep -c '^### Requirement:'` → **1**; `grep -c '^#### Scenario:'` → **1**; `grep -c '^| COV-'` → **1**;
`head -1` → `# Delta for coverage`; `grep -c '^## Requirements'` → **0** (`## ADDED Requirements` → 1, i.e. a
delta, not a full spec, matching the archived `process-boundary` precedent).
`requirements: 1/1`, `scenarios: 1/1`.

| Req | Scenario | Class | Verified evidence | Result |
| --- | -------- | ----- | ----------------- | ------ |
| COV-07 | S1 — No gate is armed for the three second-tier floors | Verify-phase **static evidence** (no executable test by design) | **E1** six-command absence inventory re-run (all six reproduced with expected output, below) · **E2** record present in both carriers + guard green unmodified · **E3** three guards green, `git diff --stat -- tests/` empty, full suite `1785 passed, 6 skipped` | COMPLETE |

**Why static evidence is the correct class and not a test gap.** The scenario's own `- AND` clause is
normative: *"this SHALL remain **verify-phase static evidence** recorded in the verify report: this
requirement adds no test"*, and the delta's `## Test Mapping` row states the same. The capability's own
precedent is COV-04, whose canonical row reads `| COV-04 | (Retired — no scenarios) | … kept as a retired
marker only; not enforced |` — a recorded-not-enforced requirement with no pytest assertion. This phase
therefore performed the inspection the scenario specifies (E1) and did **not** invent a test; inventing one
would contradict the requirement being verified.

### E1 — the absence inventory (re-run by this phase, verbatim output)

```text
$ git grep -nE "for f in |fail-under" -- scripts/check_core_coverage.sh
scripts/check_core_coverage.sh:4:# its own scoped invocation. --fail-under=100 is a fixed policy constant, never a
scripts/check_core_coverage.sh:8:for f in cli scanner prepare publish; do
scripts/check_core_coverage.sh:9:  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
[exit 0]
# roster is exactly cli scanner prepare publish; the only floor literal is 100

$ git grep -n -- "--fail-under=" -- scripts/ .github/workflows/
scripts/check_core_coverage.sh:4:# its own scoped invocation. --fail-under=100 is a fixed policy constant, never a
scripts/check_core_coverage.sh:9:  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
[exit 0]
# only 100 literals, only in the gate script — no --fail-under in either workflow

$ git grep -n -e "fail_under" -e "fail-under" -- .github/workflows/
[exit 1 — no matches]
# zero matches in ci.yml and release.yml

$ git grep -nE "profile\.py|mcp_registration\.py|verification\.py" -- scripts/ .github/workflows/
[exit 1 — no matches]
# the three floors appear in no gated invocation and no CI step

$ git grep -n -A3 "\[tool.coverage.report\]" -- pyproject.toml
pyproject.toml:100:[tool.coverage.report]
pyproject.toml-101-show_missing = true
pyproject.toml-102-fail_under = 90
pyproject.toml-103-
[exit 0]
# the only coverage threshold is the config-owned scalar TOTAL floor

$ git grep -n "check_core_coverage.sh" -- .github/workflows/
.github/workflows/ci.yml:81:      # Four scoped per-file invocations in scripts/check_core_coverage.sh:
.github/workflows/ci.yml:85:        run: bash scripts/check_core_coverage.sh
[exit 0]
# ci.yml only; release.yml's asymmetry belongs to issue #185 and is asserted nowhere here
```

Read directly (not inferred from grep): `scripts/check_core_coverage.sh` is 11 lines; the loop is
`for f in cli scanner prepare publish; do` with body
`uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m`. **The three COV-01 second-tier
modules are absent from the gated surface and no non-100 floor exists anywhere in the committed surfaces.**
This is exactly the conjunction COV-07-S1 asserts.

### E2 — the record is present in both carriers

```text
$ git grep -n "COV-07" -- openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md AGENTS.md
AGENTS.md:128:- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors
(`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay
verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md:31:### Requirement: Second-tier per-file floors are deliberately verify-phase-only (COV-07)
openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md:91:| COV-07 | No gate is armed for the three second-tier floors | Verify-phase **static evidence** — … this requirement adds no test |
(+ lines 16, 21, 98, 101, 106, 109 = the delta's blockquote / cross-reference prose)
[exit 0]
# requirement heading :31, exactly one mapping row :91, AGENTS.md bullet :128

$ uv run pytest tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate -q
1 passed in 0.03s
[exit 0]

$ git diff -U0 origin/dev -- AGENTS.md
@@ -127,0 +128 @@ Rules:
+- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors
(`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay
verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
$ git diff --numstat origin/dev -- AGENTS.md
1	0	AGENTS.md
[exit 0]
# exactly +1 / -0 — one added line, zero deletions (proposal SC4)
$ tail -1 AGENTS.md | wc -l
1
# the bullet is one physical line (design D6)
```

**Independently reproduced the guard's capture region** (not trusted from design § *Guard analysis*): applying
`re.search(r"### 14\..*?(?=\n### 15\.|\Z)", AGENTS.md, re.DOTALL)` to the working tree yields a capture
spanning lines 101→129; the new bullet (line 128) is inside it; all three presence assertions hold
(`cli.py`/`scanner.py`/`prepare.py`/`publish.py` present; `100.00%` present; `# pragma: no cover` present);
and the bullet introduces no `### 15.` heading (so it cannot truncate the capture) and contains no
`100.00%` / pragma token (so it cannot mask a future removal elsewhere in the rule).

**Independent byte-identity check of the two artifacts against the design fixture** (`uv run python`):

```text
design Artifact A fence lines: 117 | delta file lines: 117
IDENTICAL (exact, incl. trailing newline): False
IDENTICAL (modulo terminal newline):      True     # the fence closes with ``` on the next line
design Artifact B vs last line of AGENTS.md: IDENTICAL (exact): True
```

## Task completion status

`tasks.md` — scanned with the contract regex `^\s*- \[ \]`:

```text
checked markers   (^\s*- \[x\]): 33
unchecked markers (^\s*- \[ \]): 0
```

**Exact unchecked `- [ ]` implementation task lines: none remain.** No archive blocker on completeness.
Tasks 0–5 (anchor preflight, A1 delta, A2 bullet, A3 single atomic commit, Task 4.1–4.4 evidence collection,
Task 5 rollback/stop conditions) are `[x]`, and their load-bearing claims were re-earned here: Task 3 → E4d
(authoritative diff lives on the `origin/dev` merge base, see below); Task 4.1–4.4 → E1–E4 re-run above.

## Structured status and actionContext

Native `gentle-ai.sdd-status` v2 consumed before phase work (read-only; recomputed nowhere): `next: verify`,
`verify: ready`, `apply: all_done`, `archive: blocked`, `tasks: 33/33 complete`,
`artifacts.verifyReport: missing`.

- `actionContext.mode: repo-local` (not `workspace-planning`), `workspaceRoot` =
  `C:\Users\elaze\Desktop\sofer`, `allowedEditRoots` = `["C:\Users\elaze\Desktop\sofer"]` — no
  `allowedEditRoots` deficit exists.
- Implementation ownership is proven inside the authoritative root: the only tracked changes are
  `AGENTS.md` and `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`, both
  repo-relative inside `C:\Users\elaze\Desktop\sofer`; the only untracked tree is the change directory
  itself (its phase artifacts). `git status --porcelain` → `?? …/apply-progress.md`, `?? …/design.md`,
  `?? …/explore.md`, `?? …/proposal.md`, `?? …/tasks.md`.
- Active change selection is unambiguous; `tasks.md` exists and is non-empty, so the missing/empty-tasks
  block does not apply.
- This phase wrote exactly one file — `verify-report.md` under the change directory — and no product path.

## Test / validation commands (exact, with exit codes)

| # | Command | Exit | Observed output (key line) | Digest |
| --- | ------- | ---- | -------------------------- | ------ |
| 1 | `uv run pytest tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate -q` | 0 | `1 passed in 0.03s` | E2 |
| 2 | `uv run pytest tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100 tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90 -q` | 0 | `3 passed in 0.05s` | E3 |
| 3 | `uv run pytest tests/ -q` (`config.rules.verify.test_command`) | 0 | `1785 passed, 6 skipped, 1 warning in 58.20s` | sha256 `972b6d9f8396d9e1e64d003e367faccfb85bb67287fa9f1d019278f177839c31` |
| 4 | `uv run ruff check src/ tests/ && uv run mypy src/` (`config.rules.verify.build_command`) | 0 | `All checks passed!` · `Success: no issues found in 32 source files` | sha256 `beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7` |
| 5 | `git diff --stat -- tests/` (E3) | 0 | *(no output — empty)* | n/a |
| 6 | `git grep -n -- "--fail-under=" -- scripts/ .github/workflows/` (E1b) | 0 | only `100` literals, only in the gate script | n/a |
| 7 | `git grep -n -e "fail_under" -e "fail-under" -- .github/workflows/` (E1c) | 1 (no matches = **expected**) | *(empty)* | n/a |
| 8 | `git grep -nE "profile\.py\|mcp_registration\.py\|verification\.py" -- scripts/ .github/workflows/` (E1d) | 1 (no matches = **expected**) | *(empty)* | n/a |
| 9 | `git diff --name-only origin/dev -- src/ tests/ scripts/ .github/ pyproject.toml uv.lock` (E4b) | 0 | *(empty)* | n/a |
| 10 | `git diff --name-only origin/dev -- openspec/specs/` (E4c) | 0 | *(empty — canonical untouched, `sdd-sync` owns it)* | n/a |

**Tally re-derived, not inherited.** The measured tally is `1785 passed, 6 skipped, 1 warning`
(1791 collected), independently reproduced here and identical to the dev baseline recorded for #216. The
`1 warning` is the pre-existing `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` `runpy`
`RuntimeWarning`, unrelated to this change. Zero failures, zero new skips, zero tests added or moved (row 5
empty + E4b empty prove the count cannot have shifted). `tests/test_coverage_contract.py` keeps its
documented skip (COV-01-S3); the full-suite run is not a coverage measurement and needs no `.coverage`
file.

## Strict TDD compliance

**Not active.** `openspec/config.yaml` declares `strict_tdd: false` both top-level and under `testing:`; the
session preflight did not activate it; `apply-progress.md` records the standard mode. No `TDD Cycle Evidence`
table is required and its absence is **not** a finding.

The absence is also substantively correct rather than an exception: this change adds **zero executable
behaviour** (two Markdown documents), so there is no failing test to write first. This phase confirmed the
change's stated RED↔GREEN equivalent independently: the **RED-equivalent** E1 absence inventory is *false-able*
(the three module names or a non-100 floor appearing in a gated surface would fail it) and is here re-proven
true **after** the commit; the **GREEN-equivalent** E2 proves the record landed in both carriers and that the
pre-existing guard is green **unmodified**. No failing test was manufactured — that would have been theatre,
as `tasks.md` § *TDD posture* records.

## Assertion quality findings

**Not applicable — this change adds no test.** Audited the three pre-existing guards that COV-07-S1 relies on,
since they are named normatively in the requirement and in the delta's Test Mapping row:

- `test_coverage_job_gates_core_modules_at_100` — asserts the loop roster
  (`"for f in cli scanner prepare publish" in script`), the exact scoped invocation shape
  (`'--include="src/sofer/${f}.py" --fail-under=100 -m'`), the script's presence in `ci.yml`, and that no
  other `--fail-under` value appears. Positive behavioural assertions over real defect classes; not
  tautological, not a ghost loop, not type-only.
- `test_coverage_gate_is_config_driven_without_cli_floor` — asserts `--fail-under`, `fail_under` and
  `fail-under` are absent from the raw text of **both** workflows. This is the guard that makes E1c/E1d
  meaningful.
- `test_pyproject_declares_coverage_fail_under_90` — parses `pyproject.toml` and asserts the scalar TOTAL
  floor, anchoring E1e.

`git diff --name-only origin/dev -- tests/test_ci_workflows.py` → empty: all three are **unmodified**, as the
scenario requires ("SHALL stay green **unmodified**"). No tautologies, ghost loops, type-only assertions,
smoke-only tests, or implementation-detail assertions were introduced by this change (it introduces none at
all). No assertion-quality finding.

## Adjudicated nuance carried forward (D5 — ACCEPTED, not an open finding)

`design.md` D5 states that "the only threshold literals in the whole delta are `100` and `fail_under = 90`".
That **literal** claim is falsified by tokens that do appear in the committed delta, as this phase re-confirmed
by digit-scanning the artifact:

- delta `:39` — `≥90`, naming the **existing** executable contract test `tests/test_coverage_contract.py`;
- delta `:63` — bare `90`, naming the **config-owned TOTAL scalar** (`COV-02` / `ci` CI-01);
- delta `:42` — `100%`, naming **COV-06's mandate title**.

The **substantive** rule D5 exists to protect — *no coverage value is attached to any of the three second-tier
modules* — **holds**, and this phase proved it mechanically rather than by reading: only three lines in the
delta mention `profile.py` / `mcp_registration.py` / `verification.py` (delta `:33`, `:34`, `:76`), and after
stripping `COV-0N` identifiers and test-node ids from those lines, **zero** numeric tokens remain
(`digits-after-id-strip=[]` for all three). Every numeric token in the delta therefore refers to *another*
requirement's boundary, never to the floors.

**Status: adjudicated and closed.** The worker stopped and reported instead of editing the fixture in apply
(correct per `tasks.md` Task 5); the parent accepted the byte-exact delta, including the recorded size
reconciliation (~78 estimated → 117 rendered), on the grounds that the substantive rule holds. This is
recorded here as an **accepted deviation of design prose**, not as an open finding, and it moves nothing:
no requirement, scenario, task, verdict, or product artifact depends on D5's literal wording. Recommended
one-line correction at `sdd-sync`/archive time (change "the only threshold literals" to "the only threshold
literals *attached to the three floors*") — cosmetic, non-blocking.

## Review workload / PR boundary findings

- **Actual product diff** (authoritative base `origin/dev`, E4a):
  `AGENTS.md +1`, `…/specs/coverage/spec.md +117` → `2 files changed, 118 insertions(+)`, 0 deletions.
- **Forecast reconciliation** (`tasks.md` § *Review Workload Forecast*): forecast ≈79 product lines
  (≈78 delta + 1 `AGENTS.md`); actual 118. The +39 is markdown wrapping at the canonical file's ~90-column
  prose width — already disclosed in `design.md` § *Size reconciliation* and `apply-progress.md` §8, and
  independently confirmed here by the byte-identity check (the delta is the design's fixture verbatim, so no
  content was added). Against the **400-line canonical** threshold this is **29.5 %**; against the
  **1500-line session** budget, **7.9 %**. `400-line budget risk: Low` holds.
- **No chaining, no exception.** `Chained PRs recommended: No`, `Chain strategy: pending` (chaining was never
  selected, so no chain strategy can be violated), and **no `size:exception` was used or needed** — correctly
  not inferred. The returned boundary is exactly the forecast one: **one commit, two files** (`ac8af03`),
  matching `tasks.md`'s load-bearing split prohibition (the `AGENTS.md` pointer and the COV-07 requirement it
  points at must never land separately — they did not: E4d roster is exactly those two paths).
- **No scope creep.** E4b is empty for `src/ tests/ scripts/ .github/ pyproject.toml uv.lock`; E4c is empty
  for `openspec/specs/` (canonical promotion is `sdd-sync`'s job and was **not** performed here);
  `tasks.md`'s entire *Forbidden* list is respected, including `CONTRIBUTING.md`, `README.md`,
  `README_ES.md`, `.pre-commit-config.yaml`, and the deliberately-stale `## Purpose` enumeration.
- **Phase artifacts are not in `git diff`.** The five untracked files under the change directory
  (`explore.md`, `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, plus this report) are untracked
  by design and therefore invisible to `git diff origin/dev` — this is expected, not a gap in E4a's roster.
- **Task-to-diff proportionality:** each `[x]` implementation task maps to a visible artifact — Task 1/A1 →
  the 117-line delta; Task 2/A2 → the single `AGENTS.md` line; Tasks 3/4 → the commit and this evidence set.
  No task is claimed without a produced artifact.

## Findings

**None at CRITICAL or WARNING severity.** Two informational notes already dispositioned above: the D5
literal-wording deviation (**accepted/adjudicated**, no verdict impact) and the design-estimate → rendered-line
delta (≈79 → 118, **disclosed and reconciled**, no delivery decision changes).

**Independent spot-check of apply-progress fidelity.** Every E1–E4 block re-run by this phase reproduced
byte-for-byte what `apply-progress.md` §5 recorded — including the two zero-match `git grep` invocations
(exit 1) and the `1 0 AGENTS.md` numstat — with one immaterial difference: apply-progress pasted
`scripts/check_core_coverage.sh:8:for f in cli scanner prepare publish;` while the committed file (and this
phase's run) reads `…publish; do`. The recorded line is a transcript truncation of the same single logical
line, not a divergence; the roster is identical and E3's guard asserts the same substring. No action required.

## Exact blockers

**None.** 0 blockers, 0 critical findings. No unchecked implementation task remains. Archive readiness is
gated only on the remaining `sdd-sync` promotion of COV-07 into
`openspec/specs/coverage/spec.md` (insert the block between the `---` at `:281` and the `## Test Mapping`
heading at `:283` with its own trailing `---`; append the single Test Mapping row after the COV-06 TOTAL row
at `:324`; re-verify anchors first — this phase confirmed the canonical file contains **0** occurrences of
`COV-07` and that COV-04's "kept as a retired marker only; not enforced" row is the precedent for the
static-evidence mapping).

## Risks

1. **The recorded invariant is not airtight, and the delta says so.** A new gate script or workflow step
   carrying a floor other than 100 would turn **no** existing test red (E1b/E1c scope is the four-module
   script plus the two workflows' raw text). What makes such a move illegitimate is COV-07's own prose, not
   the ban — which is precisely the scoping caveat the requirement carries. Residual and accepted; the
   requirement is the record.
2. **Sync-time anchor drift.** The delta's sync mechanics depend on canonical line numbers (`:281`, `:283`,
   `:306`, `:307`, `:324`). They are stable today, but any other change landing on the `coverage` capability
   first shifts them; `sdd-sync` must re-verify text anchors, and the delta's content is anchor-independent.
3. **COV-07 is not yet in the canonical spec** (0 occurrences verified). Until `sdd-sync` promotes it, a
   repository reader without the change directory sees only the `AGENTS.md` pointer. Expected mid-flight;
   not a verify defect.
4. **Static-only enforcement means the record can silently rot.** COV-07-S1 is a manual inspection with no
   automated tripwire by design; if a future change arms one of the three floors, CI will not notice — the
   requirement states that such a change must amend COV-07, COV-06, COV-03 and both ban-pinning guards in
   the same change. Process compliance is the only enforcement, and that is the recorded decision (#215
   option (b)).

## Next recommended

`sdd-sync` — promote COV-07 into `openspec/specs/coverage/spec.md` exactly as `design.md` § *Insertion-point
mechanics* specifies (block between `:281` and `:283` carrying its own trailing `---`; single row appended
after `:324`; re-verify anchors; never re-emit the table header/delimiter), then archive.
