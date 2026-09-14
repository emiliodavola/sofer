# Proposal: chore-python-version-313

**Issue:** #178 (`dev-env: .python-version 3.10 makes local mypy and the COV-06 coverage gate unsatisfiable (CI runs 3.13)`)
**Branch:** `chore/178-python-version-313` (verified via `.git/HEAD` → `ref: refs/heads/chore/178-python-version-313`, cut from `dev`)
**Artifact mode:** hybrid (OpenSpec + Engram) — this file is the OpenSpec artifact; an Engram observation mirrors it under `sdd/2026-09-14-chore-python-version-313/proposal`.
**Follow-up (out of scope here):** issue #192 owns the structural fix (make `tomli` unconditional; collapse the five duplicated fallbacks into one helper).

## Intent

Closes #178: the tracked dev-environment pin `.python-version` says `3.10`, while every gate-bearing CI job runs on `3.13`. At any single interpreter exactly one arm of the five `try: import tomli as _tomli / except ImportError: import tomllib as _tomli` fallbacks is dead, and which arm is dead is decided by the pin — not by the code. At `3.10` the `tomli` backport *is* installed (pyproject.toml:27 declares `tomli>=2.0; python_version < '3.11'`), so `src/sofer/cli.py:439-440` can never execute; that makes `--fail-under=100` for `cli.py` **unsatisfiable in the developer environment by construction**, and it makes `uv run mypy src/` fail with five `[no-redef]` errors. At `3.13` the backport is absent, the `except` arm executes, and both gates are green.

The operational cost is not cosmetic: the local `pre-commit` mypy hook (`.pre-commit-config.yaml:11-16`, `entry: uv run mypy src/ scripts/`) fails on **every commit**, and the repository's own documented gate commands (`uv run mypy src/`, `uv run coverage run -m pytest` + `bash scripts/check_core_coverage.sh`) cannot be satisfied on a clean checkout — pushing contributors toward `--no-verify`, which AGENTS.md rule 5 forbids. CI does not catch this because `.github/workflows/ci.yml` pins the `lint` job (`:15`) and the `coverage` job (`:61`) to `python-version: "3.13"` via `astral-sh/setup-uv` (which sets `UV_PYTHON`), while the `3.10` matrix leg (`:28`, `:36`) runs only `uv run pytest -v` and `uv run sofer --help` — never the mypy or coverage gates.

**Confirmed product decision (not re-opened):** the maintainer chose to bump `.python-version` to `3.13` and to treat the deeper structural defect as the separate follow-up change #192. The maintainer explicitly confirmed that this does **not** reduce user-facing Python support: `requires-python = ">=3.10"` (pyproject.toml:6) is untouched and the CI test matrix keeps exercising `3.10`–`3.14` (`.github/workflows/ci.yml:28`).

The distinction that makes this coherent and must survive review: `.python-version` selects **the interpreter a developer runs the tools with**; `[tool.mypy] python_version = "3.10"` selects **the minimum language/typing level the code is checked against** (it tracks `requires-python`, not the dev interpreter). The measured green-3.13 result was obtained with `python_version = "3.10"` **unchanged**, which is direct evidence that the two settings are independent.

## Current State (verified on this branch)

`.git/HEAD` on this branch reads `ref: refs/heads/chore/178-python-version-313`; `.python-version` contains exactly `3.10`. Every row below was read from the working tree on this branch; the measured command evidence is the parent's reproduction on `dev@2f57f8e` and is reused verbatim per the handoff (not re-measured here).

| Fact | Site (file:line) | Verified state |
| --- | --- | --- |
| Dev interpreter pin | `.python-version` | `3.10` (single line) |
| Minimum supported Python (untouched by this change) | `pyproject.toml:6` | `requires-python = ">=3.10"` |
| Backport marker that decides which fallback arm is dead | `pyproject.toml:27` | `tomli>=2.0; python_version < '3.11'` |
| Static-check target (tracks `requires-python`, NOT the dev pin) | `pyproject.toml` `[tool.mypy]` | `python_version = "3.10"`, `strict = false`, `ignore_missing_imports = true` |
| Fallback site 1 | `src/sofer/cli.py:438-440` | `try: import tomli as _tomli` / `except ImportError:` / `import tomllib as _tomli` |
| Fallback site 2 | `src/sofer/config.py:151-153` | same pair (`except ImportError:  # Python ≥ 3.11`) |
| Fallback site 3 | `src/sofer/mcp_registration.py:128-130` | same pair |
| Fallback site 4 | `src/sofer/mcp_server.py:687-689` | same pair (`# Python >= 3.11`) |
| Fallback site 5 | `src/sofer/model.py:397-399` | same pair (`# Python ≥ 3.11`) |
| Latent-issue note (three modules named, not five) | `AGENTS.md:90` | `under 3.10 the \`import tomli as tomllib\` fallback triggers \`no-redef\` errors (known latent issue in \`model.py\`, \`config.py\`, \`cli.py\`)` — module list is short by two and the quoted import form is wrong (the code is `import tomli as _tomli` / `import tomllib as _tomli`, never `import tomli as tomllib`) |
| CI lint job interpreter | `.github/workflows/ci.yml:15` | `python-version: "3.13"` |
| CI test matrix (support floor, must stay) | `.github/workflows/ci.yml:28`, `:36` | `["3.10", "3.11", "3.12", "3.13", "3.14"]` → `${{ matrix.python-version }}`; runs only `uv run pytest -v` + `uv run sofer --help` |
| CI coverage job interpreter | `.github/workflows/ci.yml:61` | `python-version: "3.13"` |
| COV-06 gate script (no `--python` flag; follows the pin) | `scripts/check_core_coverage.sh:7-8` | `for f in cli scanner prepare publish; do` → `uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m` |
| Local pre-commit mypy hook (fails on every commit at 3.10) | `.pre-commit-config.yaml:11-16` | `entry: uv run mypy src/ scripts/`, `language: system`, `pass_filenames: false` |
| Pragma escape hatch is unavailable | `AGENTS.md` rule 14 | `# pragma: no cover` is FORBIDDEN in the four core modules — so the coverage failure is not fixable by pragma |
| No test pins the pin or rule 12 | `tests/test_ci_workflows.py:233-244` | the only test reading `AGENTS.md` extracts rule 14 by the regex `### 14.<anything>` up to a following `### 15.` or end-of-file (`re.DOTALL`); no test reads `.python-version`, and no test asserts rule 12's text |
| CONTRIBUTING.md commands are pin-agnostic | `CONTRIBUTING.md` → Development setup / Development commands | documents `uv sync`, `uv run pytest`, `uv run mypy src/`, `uv run ruff check src/ tests/`, `uv run coverage run -m pytest`, `uv run coverage report -m` — every invocation resolves the interpreter through uv/`.python-version`, so none of the text becomes wrong |
| CONTRIBUTING.md is pinned by a test (constrains any edit) | `tests/test_ci_workflows.py::test_contributing_documents_coverage_floor` (CI-06 S2) | asserts `"90%"`, `"uv run coverage run -m pytest"`, `"uv run coverage report -m"` present and `"no drop in coverage"` absent |

### Measured evidence (baseline `.python-version` = `3.10`, reproduced on `dev@2f57f8e`; reused, not re-measured)

- `uv run mypy src/` → **FAILS**, 5 errors: `[no-redef]` at `src/sofer/cli.py:440`, `src/sofer/config.py:153`, `src/sofer/mcp_registration.py:130`, `src/sofer/mcp_server.py:689`, `src/sofer/model.py:399` (`Found 5 errors in 5 files (checked 32 source files)`, exit 1).
- `uv run coverage run -m pytest` then `bash scripts/check_core_coverage.sh` → **FAILS**: `src\sofer\cli.py 574 2 166 0 99%  439-440`, `Coverage failure: total of 99 is less than fail-under=100`, exit 2. The `scanner.py` / `prepare.py` / `publish.py` gates never run because `set -euo pipefail` aborts the script at the first failure — so the 3.10 baseline leaves **three of the four COV-06 gates unverified**, not just red.
- `uv run pytest tests/ -q` → 1766 passed, 6 skipped (tests are unaffected by the pin; the suite is the baseline to protect).

### Measured evidence (isolated `3.13` environment, `UV_PROJECT_ENVIRONMENT=/tmp/sofer313 uv run --python 3.13`, repository untouched)

- `mypy src/` → `Success: no issues found in 32 source files` (exit 0) — with `[tool.mypy] python_version = "3.10"` unchanged.
- `coverage run -m pytest` + `bash scripts/check_core_coverage.sh` → all four modules at `100%` with an empty `Missing` column, exit 0.
- **Honest caveat, carried forward unresolved:** that isolated environment reported `1 failed, 1765 passed, 6 skipped`, the failure being `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version`. The cause was **not pinned**. The most plausible explanation is stale build/editable-install metadata rather than the interpreter: `src/sofer/_version.py` resolves the version solely from `importlib.metadata.version("sofer")`, the isolated environment reported project version `0.3.12.dev57+g059ffc637`, `g059ffc637` is **not an ancestor of HEAD**, and zero git tags are reachable from `dev`. The `3.13` leg of CI is green today. **This change MUST re-run the full local suite after the bump and record the actual result rather than assume it** (see Success Criteria and R2).

### Packaging evidence (reused from the handoff; establishes the change is dev-env-only)

`.python-version` **is** shipped inside the sdist but **not** in the wheel; the built wheel declares `Requires-Python: >=3.10` and `Requires-Dist: tomli>=2.0; python_version < '3.11'`, and the installed 32-module package contains **zero** references to the pin. A clean `3.10.20` environment installed the built wheel and ran `sofer --version` / `--help` successfully with `tomli==2.4.1` resolved automatically by the marker. This is the direct evidence that bumping the pin cannot alter what users install or which interpreters the package supports.

### Why CI does not already catch this

`.github/workflows/ci.yml` pins the lint job (`:15`) and the coverage job (`:61`) to `3.13` via `astral-sh/setup-uv`, which sets `UV_PYTHON`; the `3.10` matrix leg (`:28`, `:36`) runs only `uv run pytest -v` and `uv run sofer --help`. The mypy error and the COV-06 failure are therefore invisible in CI and appear only on a developer machine following `.python-version`.

## Scope

### In Scope

1. **`.python-version` → `3.13`** (the single behavioral edit of this change; one line). This is what makes the documented `mypy src/` and `scripts/check_core_coverage.sh` gates satisfiable on a clean checkout with no flags, because it removes the `tomli` backport from the development environment and thereby lets the `except ImportError` arm of all five fallbacks execute.
2. **`AGENTS.md` rule 12 latent-issue note (`AGENTS.md:90`)** — corrected in place, in three ways:
   - module list: `model.py`, `config.py`, `cli.py` → the real five (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`);
   - quoted fallback form: `import tomli as tomllib` → the actual `import tomli as _tomli` / `import tomllib as _tomli`;
   - rationale for the new pin: the pin is `3.13` because a `3.10` development environment installs `tomli`, which makes the local `mypy` and COV-06 gates unsatisfiable by construction; a contributor on an older interpreter must pass `--python 3.13` explicitly for those two gates.
   The corrected note keeps the existing "do not add mypy to the version matrix" instruction (that instruction is still correct and is not weakened).
3. **`CONTRIBUTING.md` — decision recorded: no edit is required.** Every command the file documents (`uv sync`, `uv run pytest`, `uv run mypy src/`, `uv run ruff check src/ tests/`, `uv run coverage run -m pytest`, `uv run coverage report -m`) resolves the interpreter through uv and `.python-version`; the pin change does not alter a single command string. The only thing that changes is that the commands now *work*, which is the intent. `tests/test_ci_workflows.py::test_contributing_documents_coverage_floor` (CI-06 S2) pins the strings `"90%"`, `"uv run coverage run -m pytest"`, `"uv run coverage report -m"` and the absence of `"no drop in coverage"`; leaving the file untouched keeps that scenario green by construction. The "pass `--python 3.13` explicitly on an older interpreter" guidance lands in the AGENTS.md rule-12 note (in scope item 2), not in CONTRIBUTING.md.
4. **Tests — honesty statement: no new or adjusted test is required, and none will be invented.** The handoff is explicit that a unit test cannot assert the interpreter pin's effect on `mypy`/coverage, and that is correct: at gate time, "the pin is `3.13`" and "`mypy src/` exits 0" and "`cli.py` is at 100.00%" are **command-evidence** facts (the `coverage` spec COV-01/COV-02/COV-06 row precedent already records percentages and gate exit codes as verify-phase runtime evidence, never pytest assertions). Verification for this change is therefore an evidence step, not a test:
   - `uv run mypy src/` (exit 0) — and, because the pre-commit hook runs the wider surface, `uv run mypy src/ scripts/`;
   - `uv run coverage run -m pytest` then `bash scripts/check_core_coverage.sh` (exit 0, four `100%` rows, empty `Missing`);
   - `uv run pytest tests/ -q` (full suite executed; result recorded — including the `tests/test_packaging.py` observation above).
   See Decision Point 1 for the one non-vacuous static guard that was considered and why it is nevertheless excluded.

### Out of Scope

- **No change to `requires-python`** — `>=3.10` stays (pyproject.toml:6). User-facing Python support is unchanged.
- **No change to `[tool.mypy] python_version`** — it stays `"3.10"` because it declares the minimum language/typing level tied to `requires-python`, not the developer interpreter. The measured green 3.13 result was obtained with it unchanged.
- **Nothing under `.github/workflows/`** — no `ci.yml`, `release.yml`, or `codeql.yml` edit; the matrix keeps testing `3.10`–`3.14`.
- **Nothing under `src/sofer/`** — zero paths. The structural fix (make `tomli` unconditional; collapse the five duplicated fallbacks into one shared helper) is issue **#192** as its own change. `# pragma: no cover` remains forbidden by AGENTS.md rule 14 and is not a fix.
- **No reformat** of the six drifted test files (issue **#177**), and **no new `ruff format --check` CI gate** (separate undecided policy question).
- **No fix** to the stale test counts in `AGENTS.md` rule 6 (issue **#162**) or `openspec/project.md` (issue **#184**).
- **No change to `openspec/config.yaml`** — it is gitignored (`.gitignore` → SDD generated artifacts), so it is local-only state that cannot be fixed by a PR.
- **No change to `README.md` / `README_ES.md`** — no user-facing contract changes (AGENTS.md rule 13 not triggered).
- No spec delta and no capability change, and no relocation/restructuring of the AGENTS.md note (e.g. moving it into rule 5 or rule 14) — that is a docs-structure question owned by the follow-up work, not by this confined chore.

## Capabilities

### New Capabilities

None. This change alters no runtime, CLI, packaging, or distribution behavior — it changes which interpreter a developer's tools run under and corrects a documentation note.

### Modified Capabilities

None. No requirement in `openspec/specs/` text is changed, and no delta file is created. The specs this change **cross-references and deliberately leaves untouched** are:
- `coverage` **COV-06** (the four core modules' 100.00% mandate and the `scripts/check_core_coverage.sh` gates) — this change *restores* the local satisfiability of COV-06 without touching the gate machinery, the floor, or the pragma ban.
- `coverage` **COV-01 / COV-02** and `ci` **CI-01** (the config-owned TOTAL floor of 90, `pyproject.toml` untouched) — unchanged by construction; `pyproject.toml` has zero diff lines.
- `ci` **CI-06** (documentation/gate discoverability) — only AGENTS.md rule 12, a contributor-facing note, is corrected; CI-06's asserted surfaces (`CONTRIBUTING.md` coverage wording, `openspec/config.yaml`, PR template) are untouched.

No spec delta also means no new spec scenario, hence no rule-6 test obligation (AGENTS.md rule 6) — consistent with the "no invented test" decision above.

## Approach

1. **The edit (apply phase).** Set `.python-version` to `3.13` (one line, no other content). Then correct the AGENTS.md rule-12 note as described in In Scope item 2, keeping the note in place and preserving the surrounding release-procedure bullets byte-for-byte.
2. **Do not touch `pyproject.toml`, `src/sofer/`, `.github/workflows/`, `CONTRIBUTING.md`, `README*.md`, `openspec/config.yaml`.** Any diff line outside `.python-version` + `AGENTS.md` is a scope violation and is rejected at apply/verify. Enforce mechanically: `git diff --stat` must show exactly two files, and `git diff -- src/ pyproject.toml .github/ README.md README_ES.md CONTRIBUTING.md` must be empty.
3. **Verification (see the dedicated section).** Re-run the four gate commands on the new pin and record actual output — including the full-suite result, which is where the unresolved `tests/test_packaging.py` observation is either confirmed gone or escalated.
4. **Delivery.** Forecast ≈ 3–12 changed lines (1 in `.python-version`, ~2–10 in one `AGENTS.md` bullet) plus this proposal. That is far under the 400-line review budget, so **no delivery gate is expected to trigger**: single PR against `dev`, no chaining, no `size:exception`. The strategy is `ask-on-risk`; it is only exercised if the diff actually grows past the budget (it must not).

## Verification Approach

Verification for this change is **command evidence**, recorded in the apply/verify reports, not pytest assertions (see In Scope item 4 and Decision Point 1).

| # | Evidence step | Command | Pass condition |
| --- | --- | --- | --- |
| V1 | The pin is the gate interpreter | read `.python-version` | `3.13` (exactly), and identical to the value `ci.yml:15` / `:61` pin |
| V2 | Local mypy gate green, no flags | `uv run mypy src/` | exit 0, 0 errors (the 5 `[no-redef]` errors at `cli.py:440`, `config.py:153`, `mcp_registration.py:130`, `mcp_server.py:689`, `model.py:399` gone) |
| V3 | Pre-commit hook surface green | `uv run mypy src/ scripts/` | exit 0 (this is the exact `entry:` of the local hook that was failing every commit) |
| V4 | COV-06 gates green, no flags | `uv run coverage run -m pytest` then `bash scripts/check_core_coverage.sh` | exit 0; `cli.py` / `scanner.py` / `prepare.py` / `publish.py` each `100%` with an empty `Missing` column (in particular `cli.py:439-440` no longer listed as missing) |
| V5 | Full suite green after the bump | `uv run pytest tests/ -q` | full suite actually executed; result recorded verbatim. The `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` observation from the isolated 3.13 run MUST be explicitly reported — either it passes on the bumped pin (observation closed as environment artifact) or it fails and is escalated as its own finding (R2) rather than silently accepted |
| V6 | Nothing weakened | config + diff inspection | `pyproject.toml` absent from the diff (so `fail_under = 90`, `show_missing`, `python_version = "3.10"` all unchanged); no test count changed; no `# pragma: no cover` introduced; zero `src/sofer/` paths; zero `.github/workflows/` paths; `CONTRIBUTING.md` untouched |
| V7 | AGENTS.md note accuracy | read `AGENTS.md` rule 12 | the note names all five modules, quotes the real fallback form, records the 3.13 rationale, and states the `--python 3.13` escape hatch for older interpreters |
| V8 | Docs/agent-instruction tests still green | `uv run pytest tests/test_ci_workflows.py -q` | green — in particular `test_agents_md_declares_core_100_mandate` (rule-14 regex, unaffected by a rule-12 edit) and `test_contributing_documents_coverage_floor` (unaffected because CONTRIBUTING.md is untouched) |

## Decision Points

| # | Decision | Recommendation | Tradeoff |
| --- | --- | --- | --- |
| 1 | Is any test required for the pin? | **No test is added, and no test is adjusted.** The pin's effect on `mypy`/coverage is not pytest-assertable; verification is V1–V5 command evidence, matching the `coverage` spec's own precedent that measured percentages and gate exit codes are verify-phase runtime evidence, never test assertions. A static drift guard (`assert .python-version == ci.yml lint/coverage python-version`) was considered and **rejected**: it cannot prove the gates are green (vacuous as proof), and placing it in `tests/test_ci_workflows.py` would break that module's self-declared "every pytest function maps 1:1 to a spec scenario" contract unless this change also created a `ci` spec delta — which would be scope creep into the `ci` domain for a one-line dev-env pin. Recurrence prevention is instead owned by #192 (the structural fix), where the failure mode disappears rather than being pinned. | Choosing "no test" means a future revert of `.python-version` to `3.10` would go uncaught by pytest — accepted deliberately, because CI's lint/coverage jobs are pinned to `3.13` and remain the authoritative gates, and because the structural fix (#192) removes the coupling entirely rather than freezing it in a test |
| 2 | `CONTRIBUTING.md`: edit or not? | **No edit.** No documented command changes meaning under the new pin (all are `uv run …`), and the file's coverage wording is pinned by CI-06 S2. The contributor-facing "use `--python 3.13` explicitly for these two gates on an older interpreter" guidance goes into the AGENTS.md rule-12 note, which is the file that already carries the latent-issue explanation. | A contributor reading only CONTRIBUTING.md (never AGENTS.md) learns the pin indirectly via `uv sync`. Accepted: CONTRIBUTING.md is the *setup* path and `uv sync` follows `.python-version` automatically, so the correct behavior is what they get by default — no note is needed to make the documented commands work |
| 3 | Where the pin rationale lives | **In `AGENTS.md` rule 12, in place** — corrected, not relocated, and not duplicated. The note stays in the release/repo-flow rule area the handoff named. | Rule 12 is titled "Release process", so a dev-env note there is slightly off-topic; relocating it to rule 5 (pre-commit) or rule 14 (coverage) was rejected as out of the confirmed "exactly this" scope and as a docs-structure change that belongs to follow-up work |
| 4 | Does this change need a spec delta? | **No.** No requirement in `openspec/specs/` governs `.python-version` or AGENTS.md rule 12, and no capability or behavior changes. The affected specs (`coverage` COV-01/02/06, `ci` CI-01/CI-06) are cross-referenced and explicitly left untouched. | If the spec phase or openspec tooling turns out to require a delta for every change, the minimal fallback is a `ci` CI-06-adjacent MODIFIED clause recording that the dev pin mirrors the CI gate interpreter — explicitly NOT proposed here, because it would grow the change's surface beyond its confirmed scope and the gate-vs-pin coupling is what #192 removes |

## Affected Areas

| Area | Impact | Description |
| --- | --- | --- |
| `.python-version` | Modified (1 line) | `3.10` → `3.13`; the only behavioral edit. Makes the `except ImportError` arm of all five `_tomli` fallbacks executable in the development environment, which is what turns `mypy src/` and the COV-06 gate green |
| `AGENTS.md` (rule 12 note, line 90) | Modified (~2–10 lines) | Module list corrected from three to five; fallback form corrected to `import tomli as _tomli` / `import tomllib as _tomli`; new rationale (pin is 3.13 because a 3.10 dev env installs `tomli` and makes the local mypy + COV-06 gates unsatisfiable); contributor escape hatch (`--python 3.13` for those two gates on an older interpreter) |
| `openspec/changes/2026-09-14-chore-python-version-313/proposal.md` | New (this phase) | The proposal artifact |
| `openspec/changes/archive/2026-08-26-installable-cli-pypi/design.md:243` | Reference only (read-only) | Historical record carrying the same stale three-module note; archived, so NOT edited |
| `CONTRIBUTING.md` | **None (decision recorded)** | All documented commands are `uv run …` and unchanged; the CI-06 S2 test's pinned strings are preserved by not touching the file |
| `pyproject.toml` | **None** | `requires-python = ">=3.10"` (:6), the `tomli` marker (:27), and `[tool.mypy] python_version = "3.10"` all stay. `fail_under = 90` stays. Zero diff lines |
| `.github/workflows/**` | **None** | lint/coverage jobs stay on `3.13`; the test matrix keeps `3.10`–`3.14` |
| `src/sofer/**` | **None (zero paths)** | Five duplicated `_tomli` fallbacks remain exactly as-is; the structural fix is #192 |
| `scripts/check_core_coverage.sh` | **None** | Untouched; it has no `--python` flag by design and follows the pin |
| `.pre-commit-config.yaml` | **None** | Untouched; the mypy hook starts passing because the pin changed, not because the hook changed |
| `README.md`, `README_ES.md`, `tests/**`, `openspec/config.yaml` | **None** | Rule 13 not triggered; no test added or adjusted (Decision Point 1); `openspec/config.yaml` is gitignored local state |

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| R1 — The gate claim is asserted but not reproduced after the bump | Low | V2–V4 are mandatory and must be recorded with actual output. The 3.13 measurement already exists on an isolated environment with the same `[tool.mypy]` settings; the change reproduces it under the real pin. Prohibited: reporting green without running the commands |
| R2 — `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` fails locally under 3.13 (it failed in the isolated run; cause unpinned) | Medium | V5 mandates a full-suite run and explicit reporting. Working hypothesis (to be confirmed by the run, not assumed): stale build/editable-install metadata — `_version.py` reads `importlib.metadata.version("sofer")` only, the isolated env reported `0.3.12.dev57+g059ffc637`, `g059ffc637` is not an ancestor of HEAD, and zero tags are reachable from `dev`; the CI 3.13 leg is green. **Disposition:** if it reproduces, clean the build/venv metadata (fresh `uv sync`, rebuild wheel) and re-run; if it still fails it is escalated as its own issue/finding and NOT silently absorbed into this change, and NOT "fixed" by weakening the test |
| R3 — A hidden test or doc pins `.python-version`, rule 12, or the three-module list | Low (verified) | Only `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` reads `AGENTS.md`, and it extracts rule 14 only (rule 12 edit is above it and outside the regex); no test reads `.python-version`; no test asserts `requires-python`. V8 re-runs the docs/workflow test module to prove it |
| R4 — Scope creep: someone "while here" bumps `[tool.mypy] python_version`, touches `src/sofer/`, or reformats the drifted test files | Medium | Hard Out list + mechanical scope check in V6 (`git diff --stat` exactly two files; `src/sofer/`, `pyproject.toml`, `.github/`, `README*`, `CONTRIBUTING.md` diffs empty). `[tool.mypy] python_version = "3.10"` is deliberately kept — the measured green result depends on nothing there changing |
| R5 — The change is misread as reducing user-facing Python support | Medium | The packaging evidence is stated up front (sdist-only file, `Requires-Python: >=3.10`, `tomli` marker resolves on a clean 3.10.20 install) and `requires-python` + the CI `3.10`–`3.14` matrix are explicit In-Scope-preserved items. The Intent states the confirmed maintainer decision verbatim |
| R6 — The AGENTS.md rule-12 edit accidentally perturbs rule 14 (tested by COV-06) | Low | The edit is confined to the rule-12 bullet list at line 90; the rule-14 extraction (`### 14.` up to a following `### 15.` or end-of-file) is unaffected (rule 14 is the final section). V8 proves it |
| R7 — The `.python-version` change raises the *developer* interpreter requirement to 3.13 without a contributor note | Low–Medium | Accepted and documented: `uv` provisions/downloads 3.13 for `uv sync` by default, and the AGENTS.md rule-12 note records the `--python 3.13` escape hatch for the two gates on an older interpreter. The contributor setup command itself is unchanged, so CONTRIBUTING.md stays accurate without an edit (Decision Point 2) |

## Rollback Plan

Revert the commit. The production diff is one line in `.python-version` (plus the documentation note), so the revert restores the 3.10 dev environment and the AGENTS.md note text exactly. No destructive, publishing, network, or data surface is touched; there is no migration, no dependency change, and no artifact is published. Because the change is dev-env + docs only, a revert cannot affect any installed distribution, any CLI behavior, or any user-facing support declaration — the wheel/sdist contract (`Requires-Python: >=3.10`, `tomli>=2.0; python_version < '3.11'`) is untouched in both directions. A reverted tree simply returns to the two-and-a-half red local gates, which is issue #178 re-opened, not a new defect.

## Dependencies

None. No new dependency, no version bump, no workflow change, and no ordering constraint against other changes. The only relationship is by content: issue **#192** is the named follow-up that removes the underlying coupling (five duplicated `tomli` fallbacks + conditional backport) that the pin now merely avoids, and issue **#178** is closed by this change. Forecast ≈ 3–12 changed lines across 2 files (`.python-version`, `AGENTS.md`) plus this proposal artifact — far under the 400-line review budget; single PR against `dev`, no chaining, no exception.

## Success Criteria

- [ ] `.python-version` contains `3.13` and nothing else changed in that file (V1).
- [ ] On a clean checkout with `.python-version` = `3.13`, the **documented, flag-free** commands are green: `uv run mypy src/` exits 0 with zero errors (V2), and `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` exits 0 with `cli.py`, `scanner.py`, `prepare.py`, `publish.py` each at `100%` and an empty `Missing` column — `cli.py:439-440` no longer reported missing (V4).
- [ ] `uv run mypy src/ scripts/` (the exact pre-commit hook entry that was failing on every commit) exits 0 (V3).
- [ ] `uv run pytest tests/ -q` is green **with the full suite actually executed and the result recorded verbatim**, including an explicit statement about `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` (passes → observation closed as environment artifact; fails → escalated, not absorbed) (V5).
- [ ] `AGENTS.md` rule 12's latent-issue note is accurate: it names all five modules (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`), quotes the real fallback form (`import tomli as _tomli` / `import tomllib as _tomli`), records that the pin is `3.13` because a `3.10` development environment installs `tomli` and makes the local mypy and COV-06 gates unsatisfiable, keeps "do not add mypy to the version matrix", and states that a contributor on an older interpreter must pass `--python 3.13` explicitly for those two gates (V7).
- [ ] Nothing is weakened: no test count reduced, no coverage floor changed (`fail_under = 90` intact), no `# pragma: no cover` introduced, `pyproject.toml` absent from the diff, zero `src/sofer/` paths, zero `.github/workflows/` paths, `README*.md` untouched (V6).
- [ ] `CONTRIBUTING.md` decision recorded as **no edit** with rationale, and `tests/test_ci_workflows.py::test_contributing_documents_coverage_floor` stays green by construction (V8).
- [ ] `tests/test_ci_workflows.py` fully green, proving neither the AGENTS.md rule-12 edit nor the pin disturbs the COV-06/CI static contracts (V8).
- [ ] No spec delta created and no capability modified; the affected specs (`coverage` COV-01/02/06, `ci` CI-01/CI-06) are untouched by construction (Decision Point 4).
- [ ] Closes #178; the deeper structural defect remains open under #192.

## Proposal question round

**The confirmed product decision is not re-opened here** and the handoff explicitly forbids interviewing the user, so no question is asked about the bump itself. The following are the genuinely open product/PRD-level questions, recorded as **assumptions for parent/owner review** before the spec/apply phases. Each is answerable with "assumption holds" or a correction.

1. **Q1 — Is "pin + documentation" the intended first slice, with recurrence prevention deferred to #192?** Assumption: **yes.** This change deliberately adds no test and no spec delta (Decision Points 1 and 4); the coupling that caused the defect is removed by #192 rather than frozen by a static drift guard. If the maintainer instead wants the dev-env↔CI-gate agreement pinned now, the cost is a `ci`-domain spec scenario plus a test in `tests/test_ci_workflows.py` — a real scope increase, so it is not assumed.
2. **Q2 — Does the pin change the *contributor* onboarding requirement in a way that must be visible in CONTRIBUTING.md?** Assumption: **no.** `uv sync` follows `.python-version` and uv provisions 3.13 by default; the contributor-facing guidance for older interpreters lives in the AGENTS.md rule-12 note. If the maintainer wants a contributor-visible line ("this repo's dev environment is 3.13") in CONTRIBUTING.md, that is a one-line addition that must preserve the CI-06 S2 pinned strings.
3. **Q3 — Is it acceptable that the only local protection against a silent revert to 3.10 is CI (whose lint/coverage jobs are pinned to 3.13) plus documentation?** Assumption: **yes, accepted explicitly**, because a pytest assertion on the pin cannot prove the gates are green and would not be a gate in its own right (R4/Decision Point 1). If the maintainer considers an uncaught local revert a real risk, the remedy belongs to #192's structural fix, not to this chore.
4. **Q4 — The unresolved `tests/test_packaging.py` failure under an isolated 3.13 environment:** assumption is that it is an environment/metadata artifact (`_version.py` reads installed metadata only; the reported `g059ffc637` is not an ancestor of HEAD; zero tags reachable from `dev`; CI's 3.13 leg is green). If V5 shows it reproducing on the bumped pin after a clean `uv sync` and wheel rebuild, it is escalated as a separate finding rather than absorbed — confirm that disposition is preferred over expanding this change to chase it.

