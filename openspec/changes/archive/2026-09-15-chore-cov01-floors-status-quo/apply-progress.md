# Apply Progress — 2026-09-15-chore-cov01-floors-status-quo

Change: `2026-09-15-chore-cov01-floors-status-quo` (issue #215, option (b))
Branch: `chore/215-cov01-floors-status-quo` (from dev@319bb7e)
Applier: `gentle-ai-worker` (scoped surfaces), parent adjudication
Date: 2026-09-15

## 1. Work executed (tasks.md Tasks 0-2)

| Task | Result | Evidence |
|------|--------|----------|
| Task 0 — anchor re-verification | done | `grep -n "^### 1[0-9]\." AGENTS.md` → only 63,72,78,94,101 (no `### 15.`; rule 14 is last); `wc -l AGENTS.md` → 127 pre-edit |
| Task 1 (A1) — delta spec created | done | `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` (117 lines) — `diff -u <(sed -n '47,163p' design.md) <delta>` → empty (byte-identical to Artifact A) |
| Task 2 (A2) — AGENTS.md bullet | done | `diff -u <(sed -n '184p' design.md) <(tail -1 AGENTS.md)` → empty (byte-identical to Artifact B); `git diff --numstat -- AGENTS.md` → `1 0 AGENTS.md` |
| Task 3 (commit) | done | `ac8af03` — `docs(coverage): record the three second-tier floors as deliberately verify-phase-only (COV-07) (#215)` — exactly 2 files, 118 insertions(+) |

## 2. TDD honesty record

No executable behaviour was added (two Markdown documents only; `openspec/config.yaml:13 strict_tdd: false`).
Per tasks.md 4.2, the RED↔GREEN equivalent is:
- **E1 (static-absence inventory)**: true BEFORE the change, must be re-proven AFTER (verify phase owns it).
- **E2 (record presence)**: the COV-07 text + AGENTS.md bullet must be present after (proven below).
No failing test was manufactured — a manufactured red test would be theatre (tasks.md Task 5 stop-condition discipline).

## 3. Evidence (applied)

### 3.1 Structure self-check (delta)

```text
$ grep -n "^# \|^## \|^### Requirement:\|^#### Scenario:" <delta>
1:# Delta for coverage
29:## ADDED Requirements
31:### Requirement: Second-tier per-file floors are deliberately verify-phase-only (COV-07)
71:#### Scenario: No gate is armed for the three second-tier floors
81:## Test Mapping
95:## Cross-referenced and deliberately untouched
```

Counts: requirements=1, scenarios=1, Test Mapping `| COV-` rows=1. `^## Requirements` absent (delta format, matches the #216 archived precedent).

### 3.2 Forbidden-phrasing + D5 substantive rule

```text
$ grep -n -i "impossible to arm" <delta>            # ABSENT (proposal R2 held)
$ grep -n "Added by change" <delta>                 # ABSENT (design D8 held)
$ grep -nE "profile\.py|mcp_registration\.py|verification\.py" <delta> | grep "[0-9]"
# → only delta lines 33-34 and 76 match the module names, and NONE of those lines carries a digit
```

**Adjudicated nuance (worker stop-and-report, parent decision):** design D5's *literal* claim ("the only threshold literals in the whole delta are `100` and `fail_under = 90`") is falsified by tokens that DO appear: `≥90` (delta line 39 — names the existing executable contract test), bare `90` (line 63 — the config-owned TOTAL scalar, COV-02/CI-01), `100%` (line 42 — COV-06's mandate title). **Decision: accept the delta as-is.** The *substantive* D5 rule — no coverage value attached to any of the three second-tier modules — HOLDS (proven above), and every numeric token refers to another requirement's boundary, never to the floors. The delta is the design's own byte-exact Artifact A; the worker correctly refused to edit it (tasks.md Task 5: stop-and-report, never fix-in-apply).

### 3.3 AGENTS.md bullet

```text
$ tail -1 AGENTS.md
- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
```

One physical line (`wc -l` = 1); contains no `### 15.`, no `100.00%`, no pragma token. Rule 14's mandate text byte-identical (`git diff --numstat` → `1 0`). The bullet falls inside `test_agents_md_declares_core_100_mandate`'s capture region (rule 14 is the file's last rule) — safe because all three guard assertions are presence-based.

### 3.4 Guard suite (unmodified)

```text
$ uv run pytest tests/test_ci_workflows.py -q
....................... [100%]
23 passed in 0.15s
```

Includes `test_coverage_job_gates_core_modules_at_100`, `test_coverage_gate_is_config_driven_without_cli_floor`, `test_agents_md_declares_core_100_mandate` (confirmed collected). `git status` → no `tests/` change.

### 3.5 Full suite + build sanity (parent, post-apply)

```text
$ uv run pytest tests/ -q
1785 passed, 6 skipped, 1 warning in 59.95s   # identical to dev@319bb7e baseline

$ uv run ruff check src/ tests/
All checks passed!
$ uv run ruff format --check src/ tests/
67 files already formatted
$ uv run mypy src/
Success: no issues found in 32 source files
```

### 3.6 Scope proof

```text
$ git status --porcelain
 M AGENTS.md
?? openspec/changes/2026-09-15-chore-cov01-floors-status-quo/
$ git diff --name-only
AGENTS.md
```

No `src/`, `tests/`, `scripts/`, `.github/`, `pyproject.toml`, `uv.lock`, `openspec/specs/**` touched. Nothing staged.

## 4. Task 3.1 combined command (verbatim)

```text
$ uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest tests/ -q
All checks passed!
Success: no issues found in 32 source files
1785 passed, 6 skipped, 1 warning in 57.79s
# (tally re-derived on this branch; pre-commit hooks ran without --no-verify: ruff/ruff format/mypy all "no files to check" Skipped — markdown-only diff)
```

Commit roster (Task 3.3, verbatim):

```text
$ git diff --name-only HEAD~1..HEAD
AGENTS.md
openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md
```

## 5. Task 4 — E1–E4 evidence (verbatim, post-commit)

### 5.1 E1 — static-absence inventory (RED-equivalent, re-proven after the edit)

```text
$ git grep -nE "for f in |fail-under" -- scripts/check_core_coverage.sh
scripts/check_core_coverage.sh:4:# its own scoped invocation. --fail-under=100 is a fixed policy constant, never a
scripts/check_core_coverage.sh:8:for f in cli scanner prepare publish;
do
scripts/check_core_coverage.sh:9:  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
# ✓ roster exactly `cli scanner prepare publish`; only --fail-under=100

$ git grep -n -- "--fail-under=" -- scripts/ .github/workflows/
scripts/check_core_coverage.sh:4:# its own scoped invocation. --fail-under=100 is a fixed policy constant, never a
scripts/check_core_coverage.sh:9:  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
# ✓ only `100` literals, in the gate script only

$ git grep -n -e "fail_under" -e "fail-under" -- .github/workflows/
# (no matches, exit 1)
# ✓ zero matches in both workflows

$ git grep -nE "profile\.py|mcp_registration\.py|verification\.py" -- scripts/ .github/workflows/
# (no matches, exit 1)
# ✓ the three floors appear in no gated invocation and no CI step

$ git grep -n -A3 "\[tool.coverage.report\]" -- pyproject.toml
pyproject.toml:100:[tool.coverage.report]
pyproject.toml-101-show_missing = true
pyproject.toml-102-fail_under = 90
pyproject.toml-103-
# ✓ scalar fail_under = 90 only, nothing else

$ git grep -n "check_core_coverage.sh" -- .github/workflows/
.github/workflows/ci.yml:81:      # Four scoped per-file invocations in scripts/check_core_coverage.sh:
.github/workflows/ci.yml:85:        run: bash scripts/check_core_coverage.sh
# ✓ ci.yml only; release.yml asymmetry belongs to #185 and is asserted nowhere here
```

### 5.2 E2 — the record is present in both carriers (GREEN-equivalent)

```text
$ git grep -n "COV-07" -- openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md AGENTS.md
AGENTS.md:128:- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
openspec/changes/.../specs/coverage/spec.md:16:> enters as **new** requirement **COV-07** — the next free ID in this capability, whose canonical file
openspec/changes/.../specs/coverage/spec.md:21:> (a) inserts the COV-07 block — requirement, scenario, and its own trailing `---` separator — between the
openspec/changes/.../specs/coverage/spec.md:31:### Requirement: Second-tier per-file floors are deliberately verify-phase-only (COV-07)
openspec/changes/.../specs/coverage/spec.md:91:| COV-07 | No gate is armed for the three second-tier floors | Verify-phase **static evidence** — ... this requirement adds no test |
openspec/changes/.../specs/coverage/spec.md:98:  edited, renumbered, retired, or re-scoped by this delta. COV-07 is additive: ...
openspec/changes/.../specs/coverage/spec.md:101:  (`[tool.coverage.report]` `fail_under = 90`, next to `show_missing = true`). COV-07 declares no
openspec/changes/.../specs/coverage/spec.md:106:- `process-boundary` PB-05 — ... The COV-07
openspec/changes/.../specs/coverage/spec.md:109:  and no core gate script). COV-07 asserts nothing about it and closes nothing.
# ✓ requirement heading (:31) + exactly one mapping row (:91) + AGENTS.md bullet (:128)

$ uv run pytest tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate -q
.                                                                        [100%]
1 passed in 0.04s
# ✓ green, guard file unmodified
```

### 5.3 E3 — guards stay green unmodified, no test moved

```text
$ uv run pytest tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100 tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90 -q
...                                                                      [100%]
3 passed in 0.06s
# ✓ all green, all unmodified

$ git diff --stat -- tests/
# (empty)
# ✓ no test moved

$ uv run pytest tests/ -q
1785 passed, 6 skipped, 1 warning in 57.79s
# ✓ measured on this branch (Task 3.1 run); tests/test_coverage_contract.py keeps its documented skip (COV-01-S3)
```

### 5.4 E4 — diff scope (the "no code change" acceptance criterion)

```text
$ git diff --stat origin/dev
 AGENTS.md                                          |   1 +
 .../specs/coverage/spec.md                         | 117 +++++++++++++++++++++
 2 files changed, 118 insertions(+)
# ✓ expected roster: AGENTS.md + the change's delta; phase artifacts are untracked (not in git diff) — nothing else tracked

$ git diff --name-only origin/dev -- src/ tests/ scripts/ .github/ pyproject.toml uv.lock
# (empty)
# ✓ forbidden-path list clean

$ git diff -U0 origin/dev -- AGENTS.md
diff --git a/AGENTS.md b/AGENTS.md
index efdf2dd..3c23f73 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -127,0 +128 @@ Rules:
+- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
$ git diff --numstat origin/dev -- AGENTS.md
1	0	AGENTS.md
# ✓ exactly +1/−0 (proposal success criterion 4)

$ git diff --name-only origin/dev -- openspec/specs/
# (empty)
# ✓ canonical capability file untouched — sdd-sync owns it
```

## 6. Task 5 — Rollback handle and stop conditions

- **Revert handle:** ONE commit, two files, one command — `git revert ac8af03` (or `git reset --hard f9ac51b`-era state via `git reset` before any push) deletes the delta and removes the `AGENTS.md` bullet. Because the canonical `openspec/specs/coverage/spec.md` is untouched until sync, a pre-sync revert restores every canonical spec byte-for-byte.
- **Stop-and-report conditions honored:** no anchor was missing or drifted (all re-verified in Task 0); no E1 command returned a non-100 `--fail-under` literal or a match for the three floor modules; no E3 guard is red; no forbidden path appears in the diff. The one deviation found (D5 literal-claim nuance) was STOP-AND-REPORT by the worker and adjudicated in §3.2 — never self-fixed in apply.

## 7. Final self-check (tasks.md last item)

- [x] delta exists at the exact path `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`
- [x] `AGENTS.md` diff is +1/−0 (E4.3)
- [x] one commit (`ac8af03`) carried both (roster above)
- [x] E1–E4 outputs recorded verbatim (§5)
- [x] no forbidden path in `git diff --name-only origin/dev` (E4.1/E4.2)

## 8. Carry-forward to verify

- E1 static-absence inventory must be RE-RUN after (design E1, six `git grep` commands with expected outputs — tasks.md Task 4.1).
- D5 nuance above must appear in the verify report as adjudicated (not as an open finding).
- Sync constraint: COV-07 block goes between canonical `:281` and `:283` (own trailing `---`), Test Mapping row appended after `:324`; re-verify anchors (drift risk Low).
- Size: 118 product lines (117 delta + 1 AGENTS.md) — the design's ≈78 estimate was markdown wrapping; still ~5% of the 1500-line budget, no chaining.

## 9. Engram

#1290 (apply-progress, saved pre-commit; commit `ac8af03` + E1–E4 + rollback handle appended after).
