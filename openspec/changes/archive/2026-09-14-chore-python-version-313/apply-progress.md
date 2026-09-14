# Apply progress: chore-python-version-313 (issue #178)

**Branch**: `chore/178-python-version-313` (`.git/HEAD` → `ref: refs/heads/chore/178-python-version-313`)
**Store**: OpenSpec (file) + Engram mirror under topic key `sdd/2026-09-14-chore-python-version-313/apply-progress`
**Scope executed**: the parent's **narrowed objective** — the two edits plus the **static** gates
(V1, V2, V3, V6, V7, V8). V4 and V5 are **deferred to the verify phase** (see §5).
**Delivery**: single PR against `dev`; no chaining, no `size:exception`. Nothing committed, pushed or
opened as a PR; `--no-verify` was never used.

---

## 1. Completed tasks and persisted checkbox updates

Every row below is marked `- [x]` in
`openspec/changes/2026-09-14-chore-python-version-313/tasks.md` (re-read after editing, see §7).

| Task | Status | Evidence |
| --- | --- | --- |
| 1.1 Baseline confirmation (branch, pin, stale note) | **done → `- [x]`** | §2 Phase-1 evidence |
| 1.2 Working tree clean before editing | **done → `- [x]`** | §2 Phase-1 evidence (only the untracked SDD change dir, explained) |
| 2.1 `.python-version` set to exactly `3.13` | **done → `- [x]`** | §3 (V1a) |
| 2.2 Pin equals both CI gate pins | **done → `- [x]`** | §3 (V1) |
| 3.1 `AGENTS.md:90` bullet corrected in place (five modules, real fallback form, 3.13 rationale, escape hatch, "do not add mypy to the version matrix" kept) | **done → `- [x]`** | §3 (V7) |
| 3.2 Surrounding rule-12 bullets byte-for-byte preserved | **done → `- [x]`** | §3 (V7c/V7d — exactly one hunk, `@@ -90 +90 @@`) |
| 4.1 `CONTRIBUTING.md` no-edit decision recorded | **done → `- [x]`** | §3 (4.1 — empty diff) |
| 4.2 CI-06 S2 pinned strings hold by construction | **done → `- [x]`** | §3 (4.2 — string counts) |
| 5.1 **V1** pin is the gate interpreter | **done → `- [x]`** | §3 |
| 5.2 **V2** `uv run mypy src/` green | **done → `- [x]`** | §3 |
| 5.3 **V3** `uv run mypy src/ scripts/` green | **done → `- [x]`** | §3 |
| 5.4 **V4** COV-06 gate script | **NOT RUN → stays `- [ ]`** | Deferred to verify by the parent's narrowed objective (§5) |
| 5.5 **V5** full suite + packaging-test verdict | **NOT RUN → stays `- [ ]`** | Deferred to verify by the parent's narrowed objective (§5) |
| 5.6 **V6** mechanical scope check | **done → `- [x]`** | §3 |
| 5.7 **V7** AGENTS.md note accuracy | **done → `- [x]`** | §3 |
| 5.8 **V8** `tests/test_ci_workflows.py` green | **done → `- [x]`** | §3 |
| 6.1 / 6.2 / 6.3 OpenSpec lifecycle + bounded review | **NOT STARTED → stays `- [ ]` (parent-owned)** | §6 |

## 2. Files changed (pre-edit baseline evidence)

```text
$ cat .git/HEAD
ref: refs/heads/chore/178-python-version-313

$ git rev-parse --abbrev-ref HEAD
chore/178-python-version-313

$ cat -A .python-version          # pre-edit
3.10$

$ awk 'NR==90' AGENTS.md          # pre-edit (stale note)
- The workflow's lint job intentionally runs mypy only under Python 3.13, mirroring CI. Do not add mypy to the version matrix: under 3.10 the `import tomli as tomllib` fallback triggers `no-redef` errors (known latent issue in `model.py`, `config.py`, `cli.py`).

$ awk 'NR==89 || NR==91 {printf "%d: %.40s\n", NR, $0}' AGENTS.md   # surrounding bullets, pre-edit
89: - **Never move or delete a pushed tag** unless th
91: - Branch flow: all work lands on `dev` first; `m

$ git status --short              # pre-edit
?? openspec/changes/2026-09-14-chore-python-version-313/
```

Task 1.2 note: the pre-edit `git status --short` was **not literally empty** — it carried exactly one
untracked entry, this change's own SDD artifact directory (`proposal.md`, `tasks.md`, `specs/ci/spec.md`,
`design.md`). No tracked file was modified before the edits, so the post-edit `git diff --stat` (V6)
isolates the change's two files exactly. The red baseline commands (`uv run mypy src/`,
`coverage run -m pytest`) were deliberately **not** re-run, per task 1.1.

**Files changed by this attempt (exactly two, both tracked):**

| File | Change |
| --- | --- |
| `.python-version` | `3.10` → `3.13` (1 line) |
| `AGENTS.md` | rule-12 latent-issue bullet at line 90 rewritten in place (1 line replaced) |

SDD artifacts written this attempt (untracked, not review load):
`openspec/changes/2026-09-14-chore-python-version-313/apply-progress.md` (+ the `- [x]` updates in
`tasks.md`).

## 3. Static gate evidence (V1, V2, V3, V6, V7, V8) — verbatim, with exit codes

### V1 — the pin is the gate interpreter

```text
=== V1a .python-version ===
3.13$
=== V1b ci.yml:15 and :61 ===
15:           python-version: "3.13"
61:           python-version: "3.13"
```

`cat -A` proves the file is a single line `3.13` with a terminating newline — no trailing blank line, no
comment, no other content. `.python-version` = `3.13` ≡ lint-job pin `"3.13"` ≡ coverage-job pin `"3.13"`.
`git diff -- .github/` is empty, so the CI pins were read, not changed.

### V2 — `uv run mypy src/` (flag-free)

```text
$ uv run mypy src/
Using CPython 3.13.12
Creating virtual environment at: .venv
Installed 96 packages in 1.53s
Success: no issues found in 32 source files
EXIT_CODE=0
```

Exit code **0**, zero errors. The five `[no-redef]` errors the `3.10` baseline produced
(`src/sofer/cli.py:440`, `config.py:153`, `mcp_registration.py:130`, `mcp_server.py:689`, `model.py:399`)
are **gone** — mypy now checks against an interpreter where the `except ImportError:` arm is the live one
and `tomli` is not installed.

### V3 — `uv run mypy src/ scripts/` (the exact pre-commit hook `entry:`)

```text
$ uv run mypy src/ scripts/
Success: no issues found in 33 source files
EXIT_CODE=0
```

Exit code **0** — the hook entry at `.pre-commit-config.yaml:11-16` that failed on every commit under the
`3.10` pin now passes. The hook was **not** modified, and `--no-verify` was not used at any point.

### V6 — mechanical scope check

```text
$ git diff --stat
 .python-version | 2 +-
 AGENTS.md       | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)

$ git diff -- src/ pyproject.toml .github/ README.md README_ES.md CONTRIBUTING.md openspec/specs
(empty output)

$ grep -n "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py
NO_PRAGMA_IN_CORE_MODULES

$ git diff -- '*.py' | grep -n "pragma"
NO_PRAGMA_IN_PY_DIFF

$ git diff --name-only -- tests/
(empty output)

$ grep -n "fail_under" pyproject.toml
98:fail_under = 90

$ grep -n "python_version\|requires-python" pyproject.toml
6:requires-python = ">=3.10"
27:    "tomli>=2.0; python_version < '3.11'",
74:python_version = "3.10"
```

Interpretation, point by point:

- `git diff --stat` shows **exactly two** modified files — the two intended ones.
- The scope diff for `src/`, `pyproject.toml`, `.github/`, `README.md`, `README_ES.md`, `CONTRIBUTING.md`
  and `openspec/specs` is **empty**.
- The four core modules carry **no** pragma token; the diff introduces **no** pragma into any `.py` file.
  A blunt `git diff | grep "pragma: no cover"` does match one line — **the AGENTS.md prose added by this
  change**, which *names* the pragma as forbidden by rule 14. It is documentation text, not a code
  directive, and the pragma contract scans only `src/sofer/{cli,scanner,prepare,publish}.py`
  (`tests/test_coverage_contract.py::test_core_modules_contain_no_pragma_tokens`), so this is not a
  violation. Recorded explicitly so the reviewer does not have to re-derive it.
- `fail_under = 90` (pyproject.toml:98) is intact and `pyproject.toml` has zero diff lines;
  `requires-python = ">=3.10"` (:6) and `[tool.mypy] python_version = "3.10"` (:74) are unchanged.
- No test file was touched, so no test count moved and no drifted test file (issue #177) was reformatted.
- No `ruff format --check` gate was added, and no stale test count (issues #162/#184) was "fixed here".

### 4.1 / 4.2 — `CONTRIBUTING.md` no-edit decision

```text
$ git diff -- CONTRIBUTING.md
(empty output)

$ for s in "90%" "uv run coverage run -m pytest" "uv run coverage report -m"; do grep -c -F "$s" CONTRIBUTING.md; done
90% -> 3
uv run coverage run -m pytest -> 1
uv run coverage report -m -> 1
no drop in coverage (must be 0) -> 0
```

Zero diff lines; the CI-06 S2 pinned strings are present verbatim and the forbidden
`"no drop in coverage"` phrase is absent — so
`tests/test_ci_workflows.py::test_contributing_documents_coverage_floor` is green **by construction**
(and is included in the V8 run below).

### V7 — the corrected `AGENTS.md:90` bullet

Verbatim, post-edit:

> - The workflow's lint job intentionally runs mypy only under Python 3.13, mirroring CI. Do not add mypy to the version matrix: a `3.10` development environment installs the conditional `tomli` backport (`pyproject.toml:27`), which makes the `import tomli as _tomli` arm of the five `try:` / `except ImportError:` fallbacks live and the `import tomllib as _tomli` arm dead, so the second import of the same name triggers `no-redef` errors (known latent issue in `cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`) — and it leaves the COV-06 per-file gates unsatisfiable by construction, because the dead arm cannot be executed by any test while `# pragma: no cover` is forbidden in those modules (rule 14). The dev-environment pin (`.python-version`) is therefore `3.13`; a contributor whose interpreter is older must pass `--python 3.13` explicitly for those two gates (`uv run --python 3.13 mypy src/ scripts/`, `uv run --python 3.13 coverage run -m pytest`).

Required-element marking (machine-checked against the line, `grep -c -F`):

| # | Required element | Checked string | Hits |
| --- | --- | --- | --- |
| 1 | all five modules named | `` `cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py` `` (contiguous run) | **1** |
| 2 | real fallback form quoted | `` `import tomli as _tomli` `` / `` `import tomllib as _tomli` `` | **1 / 1** |
| 3 | 3.13 rationale (3.10 dev env installs `tomli`) | `pyproject.toml:27` and `unsatisfiable by construction` | **1 / 1** |
| 4 | `--python 3.13` escape hatch | `--python 3.13` | **1** |
| 5 | kept instruction | `Do not add mypy to the version matrix` | **1** |

Placement and blast radius (V7c/V7d):

```text
$ awk 'NR==77 || NR==78 || NR==91 || NR==93 {printf "%d: %.60s\n", NR, $0}' AGENTS.md
77: ### 12. Release process
78: Releases are **tag-driven and automated** by `.github/workflows/rel
91: - Branch flow: all work lands on `dev` first; `main` receives ch
93: ### 13. README / README_ES sync

$ git diff -U0 -- AGENTS.md | grep -c "^@@"
1
$ git diff --numstat -- AGENTS.md
1	1	AGENTS.md
```

The note stayed **in place**: exactly one hunk, `@@ -90 +90 @@`; rule 12's header/prose, the versioning
bullet, the "Never move or delete a pushed tag" bullet and the "Branch flow" bullet are byte-for-byte
unchanged (1 insertion / 1 deletion in the whole file).

### V8 — docs/workflow static contracts

```text
$ uv run pytest tests/test_ci_workflows.py -q
...................                                                      [100%]
19 passed in 0.16s
EXIT_CODE=0
```

Exit code **0**, 19 passed — including `test_agents_md_declares_core_100_mandate` (rule-14 regex, whose
extraction window starts at `### 14.` and therefore sits below the edited rule-12 bullet) and
`test_contributing_documents_coverage_floor` (untouched file).

## 4. TDD evidence

**Strict TDD is not active** (`openspec/config.yaml` → `strict_tdd: false`), and this change deliberately
adds or adjusts **no test**: the pin's effect on `mypy`/coverage is not pytest-assertable, so V1–V8 are
command evidence (proposal Decision Point 1 / `ci` CI-07 "Rule-6 resolution"). No RED → GREEN →
TRIANGULATE → REFACTOR cycle applies, no test was invented, and no static drift guard was added.

| TDD phase | Evidence |
| --- | --- |
| RED | Not applicable — no test is written or adjusted (Decision Point 1) |
| GREEN | Not applicable as a test step; the equivalent proof is the command evidence V1/V2/V3/V6/V7/V8 in §3 |
| TRIANGULATE | Not applicable |
| REFACTOR | Not applicable |

Tests run this attempt (evidence, not the deferred expensive gates):
`uv run mypy src/` (exit 0), `uv run mypy src/ scripts/` (exit 0),
`uv run pytest tests/test_ci_workflows.py -q` (exit 0, 19 passed).

## 5. Deferred gates — V4 and V5 (explicitly out of scope this attempt)

The parent's narrowed objective for this attempt is **static gates only**. Both slow gates are therefore
**not run here** and remain unchecked in `tasks.md`:

- **V4** (task 5.4) — `uv run coverage run -m pytest` + `bash scripts/check_core_coverage.sh`
  (the four COV-06 100.00% rows). **Deferred to verify by the parent's narrowed objective.**
- **V5** (task 5.5) — `uv run pytest tests/ -q` (full suite tally + the explicit
  `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` verdict).
  **Deferred to verify by the parent's narrowed objective.**

Neither command was executed in this attempt; no result is claimed for either, and no green is reported
for them. The verify phase owns both and re-runs them. Rationale for the split (design §8): apply proves
the cheap deterministic gates in the same sitting as the edit; V4/V5 are the expensive pair and V5 carries
the change's one genuinely open finding, so they belong where a failing or unresolved result has a place
to be recorded and escalated.

## 6. Remaining tasks — exact unchecked lines

Implementation-owned rows still open (both deferred to verify by the parent's narrowed objective, §5):

```text
- [ ] 5.4 **V4** Run `uv run coverage run -m pytest`, then `bash scripts/check_core_coverage.sh`, and record the four scoped rows verbatim: `cli.py`, `scanner.py`, `prepare.py`, `publish.py` each `100%` with an empty `Missing` column, exit 0, and `cli.py:439-440` no longer reported missing. Note that on the 3.10 baseline `set -euo pipefail` aborted at `cli.py`, leaving three of the four COV-06 gates unverified — this run must show all four executing. <!-- sdd-owner: implementation -->
- [ ] 5.5 **V5** Run `uv run pytest tests/ -q` with the full suite actually executed and record the tally verbatim. Explicitly report `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version`, which failed in the isolated 3.13 experiment for an unpinned reason. Working hypothesis to **confirm by the run, not assume**: stale build/editable-install metadata — `src/sofer/_version.py` resolves the version solely from `importlib.metadata.version("sofer")`, the isolated env reported `0.3.12.dev57+g059ffc637`, `g059ffc637` is not an ancestor of HEAD, and zero git tags are reachable from `dev`; CI's 3.13 leg is green. Disposition: if it reproduces, clean the build/venv metadata (fresh `uv sync`, rebuild) and re-run; if it still fails, **escalate it as its own finding/issue — never absorb it into this change and never weaken, skip or xfail the test**. <!-- sdd-owner: implementation -->
```

**Parent-owned rows remain unchecked and untouched** (Phase 6, `<!-- sdd-owner: parent -->`): 6.1
(`verify-report.md`), 6.2 (bounded review + archive) and 6.3 (cross-reference confirmation at archive
time). This attempt created or approved no receipt, started no bounded-review/refutation/correction actor,
and validated no delivery gate — `sdd-apply` returns `parent-lifecycle`.

## 7. Post-edit reconciliation of the persisted tasks artifact

Re-read after the checkbox update (`grep -n "^- \[" tasks.md`):

- `- [x]` **1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 5.3, 5.6, 5.7, 5.8** — 14 implementation rows,
  each backed by the evidence in §3.
- `- [ ]` **5.4, 5.5** — implementation-owned, deliberately deferred (§5); no checkpoint was claimed for
  work not performed.
- `- [ ]` **6.1, 6.2, 6.3** — parent-owned (`<!-- sdd-owner: parent -->`), preserved byte-for-byte, listed
  as deferred lifecycle actions.

All 19 rows were pre-existing; no malformed or duplicate `sdd-owner` marker was found, and no parent-owned
row was modified.

## 8. Deviations from design, with justification

| # | Deviation | Justification / impact |
| --- | --- | --- |
| D1 | **Environment handling** for the `.venv` rebuild. The design and the parent's note assumed the first `uv run` would rebuild `.venv` as CPython 3.13. It did not: uv failed with `error: failed to remove directory \`\\?\C:\Users\elaze\Desktop\sofer\.venv\Scripts\`: Acceso denegado. (os error 5)` (exit 2), because VS Code's own extension servers hold `.venv\Scripts\{python.exe,ruff.exe}` open (PIDs at the time: black-formatter LSP 17612, isort LSP 11924, `ruff.exe server` 9696). Force-killing them was **ineffective** — VS Code respawned them within 3 s (new PIDs 10796 / 28804) and the lock re-formed. Resolution: `.venv` was renamed to `.venv_310_orphan` (a gitignored path — `.gitignore:14` matches `.venv_*/`), after which uv materialised a fresh CPython 3.13.12 `.venv` at the default path and installed 96 packages in 1.53 s; the stale environment was then removed once VS Code's servers had re-spawned against the new 3.13 `.venv`. | **No task, spec, scope or acceptance criterion changed**, and `.python-version` — the change's own artifact — is unaffected. The end state is exactly the one `ci` CI-07 describes: the default-path `.venv` is now CPython 3.13, so all documented flag-free `uv run …` commands resolve to the gate interpreter. The affected directories are gitignored build artifacts, so `git diff`/`git status` (used for V6) stay clean of them. Recorded here rather than silently. |
| D2 | None else. No deviation from the design's scope, files, or evidence set. | — |

Explicitly **not** done, per the forbidden list and the out-of-scope boundaries: no edit to
`pyproject.toml` (`requires-python`, the `tomli` marker, `[tool.mypy] python_version`, `fail_under`),
`src/sofer/**`, `.github/**`, `CONTRIBUTING.md`, `README*.md`, `openspec/config.yaml`,
`openspec/specs/**`, `openspec/changes/archive/**`, `scripts/check_core_coverage.sh` or
`.pre-commit-config.yaml`; no commit, push, PR, or tag; and `--no-verify` was never used.

## 9. Workload / PR boundary

| Field | Value |
| --- | --- |
| Changed tracked files | **2** (`.python-version`, `AGENTS.md`) |
| Changed executable lines | **2** (1 insertion + 1 deletion each; `git diff --stat` = `2 files changed, 2 insertions(+), 2 deletions(-)`) |
| 400-line budget risk | **Low** — ~2 lines against a 400-line budget |
| Delivery strategy | `auto-chain` selected in preflight, but **not exercised**: the forecast (3–12 lines) is far under budget, so no work-unit split is needed |
| PR boundary | **Single PR against `dev`**; no chained/stacked PR, no `size:exception` |
| Commit policy | Nothing committed — the user must ask explicitly before any commit |

## 10. Structured status consumed

Native SDD status (deterministic, consumed before editing):

- `changeName`: `2026-09-14-chore-python-version-313`; `artifactStore`: `openspec`
- `applyState`: **ready**; `dependencies.apply`: ready; `taskProgress`: 19 total / 0 completed at entry
- `actionContext.mode`: `repo-local`; `workspaceRoot` = `allowedEditRoots[0]` =
  `C:\Users\elaze\Desktop\sofer` — every file touched is inside the authoritative workspace, so no
  edit-root stop applied
- `actionContext` **warnings: none**
- `remediationState.required`: `false`
- Attempt continuity: `gentle-ai sdd-attempt acquire` was re-invoked with the already-active token
  `sha256:01b87e61889b00124afd71fbb7fe1f696fefca0295cc5ddb3460484ce1b7c1ab`
  (objective generation 2, work unit `apply-178-pin-313-static-gates`) and returned
  `{"state":"proceed"}` — the exact attempt was continued rather than a new one opened.
- Status produced after this attempt: `verify` remains **blocked** in the native engine because
  `taskProgress` is not complete (5.4/5.5 pending by the parent's narrowed objective, 6.1–6.3
  parent-owned). That is the expected handoff state, not a defect of this attempt.

## 11. Risks carried forward to verify

- **V4/V5 unproven here** (by design): the COV-06 four-row gate and the full-suite tally — including the
  open `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` question (R2) —
  rest entirely on the verify phase. No green is claimed for them.
- **Local `.venv` rebuild depended on an environment intervention** (deviation D1). If VS Code is open
  while verify re-runs the expensive gates, the same lock can reappear; the venv is now 3.13, so a
  re-lock would block only environment mutation, not the gate commands themselves.
- The change's own protection against a future local revert of `.python-version` to `3.10` is CI plus
  documentation only — accepted deliberately in the proposal (Decision Point 1 / Q3); recurrence
  prevention is owned by issue **#192**.
