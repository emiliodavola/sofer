# Apply progress: chore-ruff-format-hook-scope

**Change** `2026-09-15-chore-ruff-format-hook-scope` (GitHub #216) · branch `chore/216-ruff-format-hook-scope` · store **hybrid** (this file + Engram mirror under topic key `sdd/2026-09-15-chore-ruff-format-hook-scope/apply-progress`).

**Mode:** standard (`strict_tdd: false` in `openspec/config.yaml`), RED→GREEN order preserved per `tasks.md`. Native status consumed before implementation: `gentle-ai sdd-status 2026-09-15-chore-ruff-format-hook-scope` → schema `gentle-ai.sdd-status@2`, `next: apply`, `apply: ready`, artifacts done, tasks 0/8.

## Completed implementation tasks (checkboxes flipped in `tasks.md`)

- [x] **1.1 (RED)** — `test_ruff_format_hook_excludes_markdown` appended after `test_contributing_names_the_declared_ruff_version` in `tests/test_ci_workflows.py` (verbatim design §3 body; reuses `_load_yaml` + `_RUFF_PRE_COMMIT_REPO`; no new imports/helpers/dependencies) + module docstring `four`→`five` with the PB-14 hook-scope guard added to the enumeration.
- [x] **2.1 (GREEN)** — 5-line rationale comment + `types_or: [python, pyi, jupyter]` inserted immediately under `- id: ruff-format` in `.pre-commit-config.yaml` (design §4 indentation: 6 spaces for `- id:`, 8 for comment/key). Nothing else in the file changed.
- **Delta:** confirmed already-written and final by the spec phase — `specs/process-boundary/spec.md` under the change dir (PB-14 + 2 scenarios + `## Test Mapping` + backfill named non-goal). Not edited by apply; `sdd-sync` promotes it.

## Files changed (product surface)

| File | Change |
| ---- | ------ |
| `.pre-commit-config.yaml` | +6 lines (comment + `types_or`) |
| `tests/test_ci_workflows.py` | +33/−5 (guard test + docstring count/enumeration) |

Final `git diff --stat`: `.pre-commit-config.yaml | 6 ++++++`, `tests/test_ci_workflows.py | 33 +++++++++++++++++++++++-----`, `2 files changed, 34 insertions(+), 5 deletions(-)`. (Delta + phase artifacts are untracked under `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/` and are not counted as product size.)

## Test evidence (verbatim)

**RED — V1 (before the YAML edit):** `uv run pytest tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown -q`

```
F                                                                        [100%]
================================== FAILURES ===================================
___________________ test_ruff_format_hook_excludes_markdown ___________________
    ...
    types_or = hooks[0].get("types_or")
>   assert types_or is not None, (
        "the ruff-format hook entry must declare `types_or`: its scope is a repository "
        "declaration, not the upstream manifest default (PB-14)"
    )
E   AssertionError: the ruff-format hook entry must declare `types_or`: its scope is a repository declaration, not the upstream manifest default (PB-14)
E   assert None is not None
tests\test_ci_workflows.py:511: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown - ...
1 failed in 0.18s
```

**GREEN — V2 (after the YAML edit):** same command →

```
.                                                                        [100%]
1 passed in 0.04s
```

**V7 (full suite):** `uv run pytest tests/ -q` →

```
1785 passed, 6 skipped, 1 warning in 60.66s (0:01:00)
```

Collected = 1791; HEAD baseline was 1790 (verified: `git show HEAD:tests/test_ci_workflows.py` = 22 `def test_` vs 23 in the worktree; no other test file modified). The `1 warning` is the pre-existing `runpy` warning from `test_cli_main_guard_executed_via_runpy`. 0 failures, 0 new skips.

**Lint:** `uv run ruff check tests/test_ci_workflows.py` → `All checks passed!` (exit 0).

## Deviations from design

None in substance. Process notes only:

- The RED step and the GREEN step were executed by two separate delegated writers (the `sdd-apply` phase agent timed out three times in this environment before the split); each run stayed inside its allowed edit surface and the TDD order was preserved by the parent (RED evidenced before the YAML edit).
- The GREEN writer's first two YAML write attempts over-indented the file (a harness output-prefix artifact in its `cat -A` inspection); both were corrected and the final `git diff` shows exactly the 6 intended added lines with no reindentation (parent-verified).

## Phase 3 verify commands (3.1–3.6) — executed by the parent before `sdd-verify`

All six `- [x]` in `tasks.md`. Evidence (verbatim, parent-run):

- **3.1 AC1 / V3** — `uv run pre-commit run ruff-format --files README.md` → `ruff format...(no files to check)Skipped`, exit 0. The config-level `types_or` **replaces** the manifest's (README.md is not a hook input).
- **3.2 AC2 / V4+V5** — `uv run pre-commit run ruff-format --all-files` → `ruff format...Passed`, exit 0 (no `files were modified by this hook`); immediately after, `git diff --stat -- README.md README_ES.md` → empty, exit 0.
- **3.3 R2 / V6** — **design deviation (recorded):** the design V6 command used `identify.tags_from_filename`, which does not exist in identify 2.6.19 (and this venv's `identify/__init__.py` is an empty file; pre-commit imports the submodules directly, so hooks still filter correctly). The intent — each declared tag resolves as a real identify type tag — was discharged against the real API `identify.extensions.EXTENSIONS` (dict keyed by **extension** → tag set): `ALL = set().union(*EXTENSIONS.values()); all(t in ALL for t in ('python','pyi','jupyter'))` → `True`, and `{'py': ['python','text'], 'pyi': ['pyi','text'], 'ipynb': ['json','jupyter','text']}`, exit 0. (sdd-verify independently re-earned this with the same union-of-values check, `True`.)
- **3.4 V8** — `uv run ruff check src/ tests/ scripts/` → `All checks passed!`; `uv run mypy src/ scripts/` → `Success: no issues found in 33 source files`; both exit 0.
- **3.5 V9** — `git diff --stat` → exactly `.pre-commit-config.yaml | 6 ++++++` and `tests/test_ci_workflows.py | 33 +++...` (2 files, 34 insertions, 5 deletions) + untracked `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/`; prohibited-path grep (`pyproject.toml|.github/|src/sofer/|README.md|README_ES.md|uv.lock`) → zero matches.
- **3.6 V10** — `git grep -n "format --check" -- .github/workflows/` → zero matches (exit 1); `git grep -n "pre-commit" -- .github/` → zero matches (exit 1). No gate armed; PB-10 scenario intact; #194 retains ownership.

## Remaining tasks

None — 8/8 `- [x]` in `tasks.md`.

## Workload / PR boundary

~39 changed product lines (34 insertions + 5 deletions) vs the ~71 estimate (60–80) — well inside the 400-line canonical threshold and the 1500-line session review budget. Single PR, one commit, no chaining. Delivery (commit/PR), review, and sync/archive are parent-owned.

## Status

Implementation complete: 8/8 tasks `- [x]` in `tasks.md`. `next_recommended: sdd-verify`.
