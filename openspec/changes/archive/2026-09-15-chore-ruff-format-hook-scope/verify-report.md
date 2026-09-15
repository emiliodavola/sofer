```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:6203b4f2dd9f268292070d014c285c62ebfdffa95759bf3a18007974591a0e52
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 2/2
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:a80f31426d116de48940265d36b026e9e5b4a97e60f06743fa685d5c0c7a8d43
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
```

# Verify report: chore-ruff-format-hook-scope

**Change** `2026-09-15-chore-ruff-format-hook-scope` (GitHub #216) · branch `chore/216-ruff-format-hook-scope`
· store **openspec** (report path `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/verify-report.md`;
Engram mirror `sdd/2026-09-15-chore-ruff-format-hook-scope/verify-report`) · verified at commit-on-branch
`HEAD` with a two-file working-tree diff.

## Status

**PASS.** 8/8 tasks complete, 1/1 requirement covered, 2/2 scenarios covered, focused guard test green
(RED independently reproduced against the pre-change config), full suite green, build command clean,
review workload and PR boundary inside budget, zero prohibited paths.

- `evidence_revision` is the native runtime **candidate identity at verify launch**, read from
  `gentle-ai sdd-attempt status --cwd "C:\Users\elaze\Desktop\sofer" --change
  "2026-09-15-chore-ruff-format-hook-scope"` → `objective.initial_candidate_identity`
  (`sha256:6203b4f2...`). The bounded attempt was claimed first: `gentle-ai sdd-attempt acquire` →
  `{"state": "proceed", "token": "sha256:4346a54426e1fcd36c4290a9f89bff39cffa16c9b77277431061cfff8165f001"}`
  (`--untracked-scope=exclude`, inventory `sha256:9d55929c...`).
- `test_output_hash` is the sha256 of the exact captured stdout+stderr bytes of the full-suite run
  (`1785 passed, 6 skipped, 1 warning in 59.10s`); `build_output_hash` is the sha256 of the exact
  captured stdout+stderr bytes of the chained build command.

## Spec coverage

Delta: `specs/process-boundary/spec.md` — counted from the retrieved artifact
(`grep -c '^### Requirement:'` → 1; `grep -c '^#### Scenario:'` → 2). `requirements: 1/1`,
`scenarios: 2/2`.

| Req | Scenario | Class | Verified evidence | Result |
| --- | -------- | ----- | ----------------- | ------ |
| PB-14 | S1 — The hook declares its own scope and excludes Markdown | Green test, 1:1 | `uv run pytest tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown -q` → `1 passed in 0.04s`, exit 0; RED reproduced against the pre-change config (below) | COMPLETE |
| PB-14 | S2 — The hook no longer receives Markdown and leaves the READMEs untouched | Verify-phase runtime evidence | `uv run pre-commit run ruff-format --files README.md` → `ruff format...(no files to check)Skipped`, exit 0; `uv run pre-commit run ruff-format --all-files --verbose` → `Passed` + `68 files left unchanged`, exit 0, **0** `.md` paths in the verbose file list, **0** `files were modified by this hook`; `git diff --stat -- README.md README_ES.md` → empty, exit 0 | COMPLETE |

**RED half of S1, independently re-earned without editing the repository.** The spec requires red-then-green
recorded in the verify report; the no-edit constraint of this phase forbids re-adding the pre-change YAML, so
the guard's assertion sequence was replayed against the pre-change config read straight out of git
(`git show HEAD:.pre-commit-config.yaml`) with the module's `_load_yaml`/`_RUFF_PRE_COMMIT_REPO` selection
logic:

```text
RED REPRODUCED against HEAD config -> AssertionError: the ruff-format hook entry must declare `types_or`: its scope is a repository declaration, not the upstream manifest default (PB-14)
```

This is the same assertion text and the same failing condition pasted in `apply-progress.md` (V1, `1 failed`,
`tests\test_ci_workflows.py:511`). Green half re-run by this phase: `1 passed`.

**S2 discrimination respected (the #195 trap).** The hook entry is the fixing command
`ruff format --force-exclude`, which exits 0 after rewriting. The evidence above is therefore the hook's
**file-list output** (`(no files to check)Skipped`; `68 files left unchanged`, zero `.md`), not the exit
code alone. `README.md` / `README_ES.md` are tracked, so the empty `git diff --stat` is sound; no untracked
probe was used. `68 files left unchanged` equals `git ls-files '*.py' '*.pyi' '*.ipynb' | wc -l` → `68`,
matching AC2's expected scope.

**Cross-references intact.** `git diff --name-only | grep -E '^openspec/specs/' | wc -l` → `0`: the canonical
`openspec/specs/process-boundary/spec.md` is untouched (delta promotes at `sdd-sync`). V10 gates:
`git grep -n "format --check" -- .github/workflows/` → 0 matches (exit 1);
`git grep -n "pre-commit" -- .github/` → 0 matches (exit 1) — PB-10's no-gate scenario keeps passing and
#194 retains gate ownership.

## Task completion status

`tasks.md` — `8` checked, `0` unchecked. Scan for unchecked implementation markers:

```text
grep -c '^[[:space:]]*- \[ \]' openspec/changes/2026-09-15-chore-ruff-format-hook-scope/tasks.md
0
```

**Exact unchecked `- [ ]` implementation task lines: none remain.** No archive blocker on completeness.
All six Phase 3 (`3.1`–`3.6`) evidence tasks are `[x]`, and their evidence was re-earned or re-checked by
this phase (3.1/3.2 re-run above; 3.4 re-run as the build command; 3.5/3.6 re-run as V9/V10; 3.3 re-checked
under *Findings*).

## Structured status and actionContext

Native `gentle-ai.sdd-status` v2 (read-only, consumed before phase work; recomputed nowhere):
`next: verify`, `verify: ready`, `apply: all_done`, `archive: blocked`, `tasks: 8/8 complete`,
`artifacts.verifyReport: missing`.

- `actionContext.mode: repo-local`, `workspaceRoot` = `C:\Users\elaze\Desktop\sofer`,
  `allowedEditRoots` = `["C:\Users\elaze\Desktop\sofer"]`. Not `workspace-planning`, so no
  `allowedEditRoots` deficit exists.
- Implementation ownership is proven inside the authoritative root: the only modified tracked paths are
  `.pre-commit-config.yaml` and `tests/test_ci_workflows.py`, both repo-relative inside
  `C:\Users\elaze\Desktop\sofer`; the only untracked tree is the change directory itself.
  `git status --porcelain` → ` M .pre-commit-config.yaml`, ` M tests/test_ci_workflows.py`,
  `?? openspec/changes/2026-09-15-chore-ruff-format-hook-scope/`.
- `tasks.md` exists and is non-empty (the only active change directory under `openspec/changes/`), so the
  missing/empty-tasks block does not apply. Active change selection is unambiguous.
- This phase wrote exactly one file — `verify-report.md` under the change directory — and no product path.

## Test / validation commands (exact, with exit codes)

| # | Command | Exit | Observed output (key line) | Digest |
| --- | ------- | ---- | -------------------------- | ------ |
| 1 | `uv run pytest tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown -q` | 0 | `1 passed in 0.04s` | sha256 `a23e4e23ff133452cbbea2116bde11299e8cd6492bc70e3d90b69afbfa735e28` |
| 2 | `uv run pytest tests/ -q` | 0 | `1785 passed, 6 skipped, 1 warning in 59.10s` | sha256 `a80f31426d116de48940265d36b026e9e5b4a97e60f06743fa685d5c0c7a8d43` |
| 3 | `uv run ruff check src/ tests/ && uv run mypy src/` (config `rules.verify.build_command`) | 0 | `All checks passed!` · `Success: no issues found in 32 source files` | sha256 `beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7` |
| 4 | `uv run ruff check src/ tests/ scripts/ && uv run mypy src/ scripts/` (the repository-enforced wider form, V8) | 0 | `All checks passed!` · `Success: no issues found in 33 source files` | sha256 `22de7d9d10fd8609003c89764dd19678cb6c6142acf612f7965ab9973ba0e85d` |
| 5 | `uv run pre-commit run ruff-format --files README.md` (AC1 / R1) | 0 | `ruff format...(no files to check)Skipped` | sha256 `f5bc8e2ef494e6cb4c728db1beaa84a9c0526d7f9d704cd0ee009bcb035d03d9` |
| 6 | `uv run pre-commit run ruff-format --all-files --verbose` (AC2 / R4) | 0 | `Passed` · `68 files left unchanged` · 0 `.md` paths · 0 `files were modified` | sha256 `60129ccf988d10ac026f166e875cb8e830539b48cbc20bf4e34e437c4f0dd05f` |
| 7 | `git diff --stat -- README.md README_ES.md` (V5) | 0 | *(no output — empty)* | n/a |

Full-suite count matches the branch's re-derived tally expectation of `1785 passed, 6 skipped`
(`1791 collected` = `1786` passed/skipped + the `+1` guard test over the `1790` baseline recorded in
`apply-progress.md`). The single `1 warning` is the pre-existing
`tests/test_cli.py::test_cli_main_guard_executed_via_runpy` `runpy` `RuntimeWarning`, unrelated to this
change and present before it. Zero failures, zero new skips. The `uv run ruff check src/ tests/` build form
was used for the envelope because it is the literal `rules.verify.build_command` in `openspec/config.yaml`;
variant 4 is reported for completeness and is also clean.

## Strict TDD compliance

**Not active** — `openspec/config.yaml` declares `strict_tdd: false` (both top-level and under `testing:`),
the preflight did not activate it, and `apply-progress.md` declares `Mode: standard (strict_tdd: false)`.
No `TDD Cycle Evidence` table is therefore required, and its absence is **not** a finding. The phase
nonetheless re-earned the change's RED→GREEN carrier independently (see *Spec coverage*): the guard is red
against `HEAD:.pre-commit-config.yaml` and green in the worktree, matching the V1/V2 records in
`apply-progress.md`.

## Assertion quality findings

Not a strict-TDD change, but the new test's four assertions were audited anyway:

- `assert len(hooks) == 1` — positive behavioural assertion on a real defect class (a duplicated/renamed
  hook entry).
- `assert types_or is not None` — the declaration contract; this is the assertion that produces the
  reproduced RED.
- `assert isinstance(types_or, list)` — hardening that keeps the next assertion non-vacuous: against a
  scalar `types_or: markdown`, `"markdown" not in types_or` would be a substring test and would
  false-green.
- `assert "markdown" not in types_or` — the defect class, asserted directly.

No tautologies, no ghost loops, no type-only-only assertions, no smoke-only tests, no
implementation-detail CSS/DOM assertions. Assertions carry failure messages; the selection logic reuses the
module's existing `_load_yaml` / `_RUFF_PRE_COMMIT_REPO` with no new import, helper, module, or dependency
(AGENTS.md rule 4). Deliberate non-assertion of the declared list is spec-mandated ("no other tag SHALL be
asserted"), not a gap: the guard asserts the defect class rather than mirroring `[python, pyi, jupyter]`,
so a legitimate future widening stays green.

## Review workload / PR boundary findings

- Product-surface diff: `.pre-commit-config.yaml` `+6`, `tests/test_ci_workflows.py` `+33/-5` →
  `2 files changed, 34 insertions(+), 5 deletions(-)` = **39 changed product lines** against the `~71`
  (60–80) forecast in `tasks.md`. Inside the forecast band, and two orders of magnitude inside the
  **400-line canonical** and **1500-line session** budgets. The `Review Workload Forecast` row
  `Chained PRs recommended: No` and `400-line budget risk: Low` hold.
- **No chaining was selected** (`Chain strategy: pending` in `tasks.md`; the session preflight left it
  deferred until chaining is selected), so the single-PR boundary is the correct one and this phase
  verified exactly that scope. **No `size:exception` was used or needed**, and none was inferred.
- **No scope creep.** V9 re-run: `git diff --name-only` contains exactly the two product files;
  prohibited-path scan `grep -E "^(pyproject\.toml|\.github/workflows/|src/sofer/|README\.md|README_ES\.md|uv\.lock)"`
  → **0 matches**. `openspec/specs/**` → 0 paths. `README.md` / `README_ES.md` byte-identical (empty
  `git diff --stat`, AGENTS.md rule 13 preserved). The six `tasks.md` non-goals are all respected.
- Task-to-diff proportionality: every `[x]` implementation task maps to a visible diff hunk (1.1 → guard
  test + docstring `four`→`five`; 2.1 → comment + `types_or`). No task is claimed without a produced
  artifact.

## Findings

**WARNING-1 (evidence fidelity, not a change defect) — one recorded verbatim R2 line is not literally
reproducible.** `apply-progress.md` §3.3 records the discharge of R2 as:
`all(t in ALL for t in ('python','pyi','jupyter'))` → `True` against `identify.extensions.EXTENSIONS`.
Re-run in this venv (identify **2.6.19**, `importlib.metadata.version("identify")`), `EXTENSIONS` is a
**dict keyed by extension name without dots** (`['adoc', 'ai', 'aj', 'asciidoc', 'apinotes', 'asar', 'asm', 'astro']`, `len == 335`), so
`'python' in EXTENSIONS` is a **key** test and the recorded expression actually evaluates to **False**:

```text
EXTENSIONS keys sample: ['adoc', 'ai', 'aj', 'asciidoc', 'apinotes', 'asar', 'asm', 'astro']
tag-membership correct check: True
key-membership (as recorded): False
```

The **intent of R2 is nevertheless satisfied and independently re-verified by this phase**: each declared
tag is a real identify type tag via the value union —
`all(t in set().union(*EXTENSIONS.values()) for t in ('python','pyi','jupyter'))` → `True`
(`'py' → {'python','text'}`, `'pyi' → {'pyi','text'}`, `'ipynb' → {'jupyter','json','text'}`). The declared
list is therefore not silently inert: the fix is real, the guard is green, and R1/AC1/AC2 were re-earned
directly. Classified WARNING because it is an inaccuracy in a *phase artifact's* pasted evidence line, not
in any shipped product path; the recommendation is a one-line correction of the recorded command at
`sdd-sync`/archive time. It does not block verify and it does not move the verdict.

**RECORDED DEVIATION (design, not a finding against the change) — V6's API does not exist.** `design.md`
§6 V6 prescribes
`uv run python -c "import identify as i; print([t in i.tags_from_filename(f) for t, f in ...])"`. The
installed `identify` 2.6.19 has **no** `tags_from_filename` (its `__init__.py` measures 0 bytes; the module
exposes `EXTENSIONS`, `EXTENSIONS_NEED_BINARY_CHECK`, `NAMES`), confirmed by this phase:
`hasattr(identify, "tags_from_filename")` → `False`. The recorded resolution — discharging R2's *intent*
against `identify.extensions.EXTENSIONS` instead of the nonexistent helper — is correct and was the right
call; the only residue is WARNING-1 above. No requirement, scenario, task, or product artifact is affected,
and PB-14 was amended at design time to state R2 as verify-phase runtime evidence rather than a pytest
assertion, so nothing in the shipped surface depends on that API.

## Exact blockers

**None.** 0 blockers, 0 critical findings.

## Risks

1. **Declaration-vs-behaviour gap (accepted, unchanged by this phase).** The guard proves the *declaration*;
   R1's `--files README.md` runtime run proves the *behaviour*. Both were re-earned green in this phase, but
   a future pre-commit release could change the override semantic while the guard stays green. This is
   already stated normatively in PB-14 and in the proposal's risk table; no mitigation is added here.
2. **`pyi` / `jupyter` are declared but inert today** (no `.pyi` / `.ipynb` in the tree). Confirmed benign:
   both are valid identify tags, so the declaration is honest rather than noisy, and the 68-file scope equals
   the tracked Python set.
3. **WARNING-1 residue.** If the inaccurate R2 line is promoted unchanged into a canonical artifact or the
   archive report, it will be re-read as reproducible evidence later. One-line correction is sufficient.
4. **Canonical spec promotion is still pending** — `openspec/specs/process-boundary/spec.md` does not yet
   contain PB-14 or the `## Test Mapping` section; `sdd-sync` owns that append. Verifying here does not
   perform it.

## Next recommended

`sdd-sync` — promote PB-14 after PB-13's final scenario and append the `## Test Mapping` section to
`openspec/specs/process-boundary/spec.md` exactly as `design.md` §5 specifies, then archive.
