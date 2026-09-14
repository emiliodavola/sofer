# Apply progress: chore-ruff-format-drift (issue #177)

**Phase**: apply — **static proofs only**. `verify` owns behaviour-preservation evidence.
**Branch**: `chore/177-ruff-format-drift` · **Store**: hybrid (this file + Engram mirror
`sdd/2026-09-14-chore-ruff-format-drift/apply-progress`) · **Strict TDD**: off (`openspec/config.yaml`) —
no behaviour to unit-test, so no RED→GREEN→TRIANGULATE→REFACTOR cycle applies.
**Attempt**: token `sha256:feb2147b8103877f04022b35bedaba5b434750029b4fb4c0c2961adcc6957c0b`
(state `proceed`, work unit `ruff-format-drift-six-test-files`, max changed lines 1200).

## Task status against `tasks.md`

| Task | Status | Evidence anchor |
| --- | --- | --- |
| 1.1 branch identity + clean tree | done | §1 |
| 1.2 pre-change baseline tally | done | §1 |
| 2.1 reformat the six files via `uv run ruff format` | done | §2 |
| 2.2 diff is formatting-only and in scope | done | §3.3 |
| 2.3 contract guards' asserted content unchanged | done | §3.5 |
| 3.1 V1 `format --check` exit 0 | done | §3.1 |
| 3.2 V1b `format --diff` empty | done | §3.1 |
| 3.3 V2 `ruff check` clean | done | §3.2 |
| 3.4 S4 no CI gate armed | done | §3.4 |
| 4.1 V3 post-change suite tally | deferred to `verify` | §4 |
| 4.2 V4 `mypy src/` | deferred to `verify` | §4 |
| 4.3 V5 `check_core_coverage.sh` | deferred to `verify` | §4 |
| 4.4 V6b `git diff --check` | deferred to `verify` | §4 |
| 5.1 / 5.2 delivery + OpenSpec lifecycle | parent-owned, untracked | tasks.md |

## 1. Baseline — captured BEFORE any formatting (design §6 ordering rule)

`.git/HEAD` → `ref: refs/heads/chore/177-ruff-format-drift`; `git branch --show-current` →
`chore/177-ruff-format-drift`; `git rev-parse HEAD` → `bdcff254c4f315362b6977be8de2d1c12257a7a4`.
`git status --porcelain` before the reformat:

```text
?? openspec/changes/2026-09-14-chore-ruff-format-drift/
```

**Pre-change baseline tally (verbatim, captured before the reformat):**

```text
$ uv run pytest tests/ -q
1766 passed, 6 skipped, 14 warnings in 54.13s
EXIT=0
```

Pre-change red gate (verbatim):

```text
$ uv run ruff format --check src/ tests/
6 files would be reformatted, 61 files already formatted
EXIT=1
```

## 2. The reformat — exactly six files, produced by the environment's ruff

Producer identity (design D1): `uv run ruff --version` → **`ruff 0.16.0`** — the same binary
PB-10's gate command invokes. The pre-commit `ruff-format` hook (pinned `v0.16.7`) was **not** used,
no editor format-on-save was used, and no hand edit was made.

```text
$ uv run ruff format tests/test_ci_workflows.py tests/test_coverage_contract.py tests/test_mcp_registration.py tests/test_profile.py tests/test_publish.py tests/test_splits.py
6 files reformatted
EXIT=0
```

## 3. Static proofs (real output, real exit codes)

### 3.1 V1 / V1b — formatter gate

```text
$ uv run ruff format --check src/ tests/
67 files already formatted
EXIT=0

$ uv run ruff format --diff src/ tests/
67 files already formatted
EXIT=0        # no diff emitted → nothing left to reformat
```

### 3.2 V2 — lint unchanged

```text
$ uv run ruff check src/ tests/
All checks passed!
EXIT=0
```

### 3.3 Diff scope (S2)

```text
$ git diff --stat
 tests/test_ci_workflows.py      | 27 ++++++++++++---------------
 tests/test_coverage_contract.py |  4 +---
 tests/test_mcp_registration.py  | 24 ++++++------------------
 tests/test_profile.py           |  8 ++------
 tests/test_publish.py           |  3 +--
 tests/test_splits.py            |  4 +---
 6 files changed, 23 insertions(+), 47 deletions(-)

$ git diff --numstat
12	15	tests/test_ci_workflows.py
1	3	tests/test_coverage_contract.py
6	18	tests/test_mcp_registration.py
2	6	tests/test_profile.py
1	2	tests/test_publish.py
1	3	tests/test_splits.py

$ git diff -- .github/ src/ pyproject.toml uv.lock .pre-commit-config.yaml README.md README_ES.md CONTRIBUTING.md openspec/
(empty)
```

Zero paths under `src/sofer/`, `.github/`, `pyproject.toml`, `.pre-commit-config.yaml`, `uv.lock`.
`git status --porcelain` after the reformat: the six ` M` test files plus the untracked change directory.

### 3.4 S4 — no CI gate armed, and none touched

```text
$ grep -rn "format --check" .github/workflows/    → no matches (grep exit 1)
$ grep -rn "ruff format"    .github/workflows/    → no matches (grep exit 1)
```

No `.github/` path appears in the diff, so enforcement remains the local pre-commit `ruff-format`
hook on staged files; recurrence stays owned by issue **#194**.

### 3.5 Formatting-only proof — asserted content unchanged

`git diff tests/test_ci_workflows.py tests/test_coverage_contract.py` shows **only** line reflow and
blank-line insertion: every asserted literal (`ci.yml` / `release.yml` / `codeql.yml` set,
`fail_under = 90` regex, `--fail-under` / `bash scripts/check_core_coverage.sh` strings, the
`### 14\.` rule regex, the exempted `uv run coverage report -m` step string) is byte-identical.
No quoted YAML/TOML literal moved.

Mechanical confirmation across **all six** files, HEAD blob vs working tree, with the verifier that
cannot be fooled by layout:

- **AST identity** — `ast.dump(ast.parse(HEAD))` == `ast.dump(ast.parse(WORK))` for every file:
  `ALL_AST_IDENTICAL: True` (exit 0).
- **Significant-token identity** (NAME / OP / STRING / NUMBER / COMMENT / f-string parts) — the only
  difference in the whole diff is ruff deleting one redundant parenthesis pair around a
  single-line `assert` in `tests/test_mcp_registration.py` (`assert (\n … is False\n)` →
  `assert … is False`). `NON_EQUAL_BLOCKS_TOTAL: 2` (the two `OP` tokens). **No NAME, STRING, NUMBER
  or COMMENT token changed** — hence no logic, assertion, import, string or comment edit.

## 4. Deferred to `verify` (deliberately not run in this attempt)

Per the parent's static-only scope and design §6's apply/verify split, these behaviour-preservation
gates are **not** claimed here and were **not** executed: `uv run mypy src/` (4.2),
`bash scripts/check_core_coverage.sh` (4.3), the post-change `uv run pytest tests/ -q` tally
comparison against §1's baseline (4.1), and `git diff --check` (4.4). Tasks 4.1–4.4 remain
unchecked in `tasks.md` for the `verify` phase to discharge.

## 5. Deviations from design

None. Design D1 (producer = `uv run ruff`, ambient 0.16.0) and D2 (formatting-only) hold as written.
The single parenthesis-pair removal noted in §3.5 is standard ruff normalization, AST-neutral, and
is recorded rather than treated as a deviation.

### Pre-existing diagnostics observed and deliberately NOT fixed

The editor's LSP pass flagged three type diagnostics inside `tests/test_mcp_registration.py`
(`__getitem__` on `object` at the `data["mcp"]["sofer"]["cwd"]` assertion, and `str` → `AgentName`
at two `resolve_config_path(agent, "project", proj)` calls). Each flagged line is **byte-identical at
HEAD** and **outside every hunk of the reformat diff** (`git diff -U0 … | grep -c` → 0), so they
pre-date this change and are unrelated to it. They are left untouched on purpose: PB-10 covers a
formatting-only edit, the change's non-goals forbid any logic/assertion/import edit, and the project
type gate is `uv run mypy src/` (src only). Fixing them here would add out-of-scope lines to a
whitespace-only diff and break the "exactly six files, formatting only" contract.

## 6. Workload / PR boundary

Single work unit, single PR against `dev` — no chaining, no `size:exception`. 23 insertions /
47 deletions across six test files (~35 modified lines, 70 line-level changes), well under the
400-line review budget; the forecast's `400-line budget risk: Low` / `Decision needed before apply: No`
/ `Chained PRs recommended: No` guard lines are unaffected. Rollback: one `git revert`; nothing
committed, pushed, or published by this phase.

## 7. Status consumed / produced

Consumed: `gentle-ai.sdd-status` v2 — `applyState: ready`, `actionContext.mode: repo-local`,
`workspaceRoot` and `allowedEditRoots` = `C:\Users\elaze\Desktop\sofer`, `artifactStore: openspec`.
All edits stayed inside the single allowed edit root; no `actionContext` warnings encountered.
Runtime attempt: `sdd-attempt acquire` → `{"state": "proceed"}` on the existing token
`sha256:feb2147b…` (continued, not re-created).

## 8. Remaining unchecked implementation tasks

```text
- [ ] 4.1 **V3** `uv run pytest tests/ -q` after the reformat → counts **identical** to the tally recorded in 1.2 with **0 failures**; `tests/test_ci_workflows.py` and `tests/test_coverage_contract.py` pass with their asserted strings unchanged (PB-10 S3). These two guards assert on YAML/TOML **text**, which is why this evidence — not the diff — is what settles "formatting-only".
- [ ] 4.2 **V4** `uv run mypy src/` → clean (32 source files), exit 0 with no flags.
- [ ] 4.3 **V5** `bash scripts/check_core_coverage.sh` → exit 0 with all four scoped rows (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) at **100.00%** and an empty `Missing` column (PB-10 S5, `coverage` COV-06). This is the leg that shows covered lines moved together with their branch data; nothing is weakened or re-declared.
- [ ] 4.4 **V6b** `git diff --check` → clean (no whitespace errors left in the reformatted files).
```

Phase 5 (5.1, 5.2) carries `<!-- sdd-owner: parent -->` markers and is deliberately untouched.
