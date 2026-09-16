# Exploration — `2026-09-15-chore-type-gate-policy`

> **Change** `2026-09-15-chore-type-gate-policy` · issue **#201** (*policy: decide whether
> `tests/` joins the mypy gate, and whether pyright is a gate at all*) · branch
> `chore/201-type-gate-policy` · baseline `dev@8184ffb` · store **hybrid** (this file +
> Engram mirror under topic key `sdd/2026-09-15-chore-type-gate-policy/explore`).
>
> **Phase:** explore (read-only mapping). No proposal, design, spec delta, or code is written
> here. Every `[tool.*]`, workflow, hook, spec and source line below was read in this branch;
> every *measurement* is the parent's shell-run evidence and is cited as verified, not re-run.
>
> **Decisions are closed (user-confirmed).** Q1 → **(a)** `tests/` stays **excluded** from the
> mypy gate, and the decision is recorded durably. Q2 → **(c)** pyright is **adopted as a real
> gate** (not advisory). This exploration maps **HOW**, plus the concrete choices the proposal
> must still make. It does not re-open either decision.

---

## 1. Scope

In scope (mapping only):

1. Durable homes for the two decisions, with the in-repo precedent for each candidate home and
   what each choice costs/breaks.
2. The exact pyright configuration that makes the gate **green on `src/` today**, per diagnostic,
   including which diagnostics are real defects worth fixing in code.
3. Decide-scope choices the proposal/design must settle: gate path scope, `typeCheckingMode`,
   warning severity, pinning/invocation, guard tests.
4. Non-goals, open measurements, and the review-workload forecast.

Out of scope (recorded in §8): flipping mypy to `strict = true`; gating `tests/`; touching the CI
test matrix or `release.yml`; any coverage-floor, pragma, or test-count change; dependencies
beyond what the gate itself needs.

---

## 2. Verified facts, mapped to `file:line`

### 2.1 The mypy gate as committed

| Fact | Location (verified) |
| --- | --- |
| `python_version = "3.10"`, `strict = false`, `check_untyped_defs = true`, `ignore_missing_imports = true`, `warn_unused_ignores = true`, `exclude = ["tests/", ".venv/"]` | `pyproject.toml:77-83` |
| CI lint job: `uv sync`, `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/ scripts/` on Python 3.13 | `.github/workflows/ci.yml:6-23` (`mypy` step at `:21`) |
| Local pre-commit hook: `uv run mypy src/ scripts/`, `pass_filenames: false` | `.pre-commit-config.yaml:19-25` |
| Documented command list includes `uv run mypy src/` | `CONTRIBUTING.md:28` |
| **DRIFT**: "We use **mypy** in strict mode. Run `mypy src/`…" while `strict = false` | `CONTRIBUTING.md:79-81` |
| PR template carries `uv run mypy src/` in the Verification block (`:23`) and the Checklist (`:45`) | `.github/PULL_REQUEST_TEMPLATE.md:20-48` |
| `type_checker.command = "uv run mypy src/"` and `pre_commit` roster | `openspec/config.yaml` (`testing.quality`, `testing.pre_commit`) — **gitignored SDD-local state** (`.gitignore:56-57`), still asserted by CI-06 S1 |
| Interpreter pin is exactly `3.13` | `.python-version:1` (CI-07 pins `ci.yml` lint + coverage jobs to the same value) |

### 2.2 The pyright surface as committed

| Fact | Evidence |
| --- | --- |
| **No** `pyrightconfig.json` anywhere (repo, home, parents) | parent shell sweep — verified |
| **No** `[tool.pyright]` in `pyproject.toml` | `pyproject.toml` read end-to-end — verified |
| **No** pyright entry in `.pre-commit-config.yaml` | file read end-to-end — verified |
| **No** pyright step in any workflow | `.github/workflows/ci.yml` read; parent swept the workflow dir — verified |
| pyright exists **only** as a global npm install (`/c/Users/elaze/AppData/Roaming/npm/pyright`, reported 1.39.9); `uv run pyright` fails (not a Python dep) | parent shell — verified |
| No `ruff.toml` at the repo root (config is `[tool.ruff]` in `pyproject.toml`) | `find` returned nothing; `pyproject.toml:59-76` |

### 2.3 Measured pyright baselines (parent-run, configs deleted, tree clean afterwards)

Taken with an explicit `{"typeCheckingMode": …}` config at the **repo root**:

| Scope | basic | standard | strict | no-config default |
| --- | --- | --- | --- | --- |
| `src/` (32 files) | **10 errors / 0 warnings** | 11 errors / 0 warnings | 578 errors / 0 warnings | 18 errors / **1088 warnings** |
| `tests/` (35 files) | 119 errors | 119 errors | — | 147 errors / 13423 warnings |

The 10 `basic` errors on `src/`, each verified by the parent (all ten are reproduced in §4 with
their resolution).

`uv.lock` is committed and carries the dev-group pins (`uv.lock:1144` mypy, `:2033` ruff,
`:2093-2120` the dev-group closure) — a pyright dev pin regenerates this region.

### 2.4 The `ci` spec's shape, and where a new requirement would sit

- Requirements run **CI-01 … CI-08**, the last starting at `openspec/specs/ci/spec.md:285`.
  **Next free ID: CI-09.**
- `## Test Mapping` lives at `openspec/specs/ci/spec.md:380` and ends at the CI-08 row (`:393`).
  Row format: `| Req | Scenario | Verification |`; two verification dialects are already in use —
  `` `tests/test_ci_workflows.py` — <helper/detail> `` and
  `Verify-phase runtime evidence — <command> exit codes (CI-01 gate-exit-code precedent)`.
- **Append convention (precedent, verbatim from the archived CI-08 delta):** a new requirement
  block is inserted **between the `---` that closes the previous requirement and the
  `## Test Mapping` heading**, carrying its own trailing `---` so no doubled separator appears; the
  Test Mapping rows are **appended at the end of the existing table**; the `## Purpose` enumeration
  (`ci/spec.md:3-11`, still listing only CI-01..CI-06) is **deliberately left stale** (CI-07 and
  CI-08 both did this).
- Canonical requirements are **replaced at archive, not edited** by the change: the archived deltas
  (`2026-09-15-chore-ruff-single-authority/specs/ci/spec.md`,
  `2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`) both open with
  "**Additive, not destructive**" and add the next free ID.
- `process-boundary` runs **PB-01 … PB-14** (next free **PB-15**) and *does* now have a
  `## Test Mapping` table (`openspec/specs/process-boundary/spec.md:428`, rows only for PB-14 —
  PB-01..PB-13 explicitly not backfilled). PB-07 (*Quality gates*, `:200`) already carries an
  incidental clause: *"New test helpers SHALL be type-annotated even though mypy excludes
  `tests/`."*

### 2.5 Precedent for "record a status-quo decision durably"

`openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` (issue
#215) is the closest analogue to Q1: a **posture decision with no code change**, recorded as a
new additive requirement (COV-07), scenario mapped to **verify-phase static evidence**, with an
explicit "Non-goals recorded by this delta" and "Cross-referenced and deliberately untouched"
section. It also records the *scoping caveat* honestly (the existing guard is not airtight).

### 2.6 Precedent for single-authority tool pinning (issue #195 → CI-08, merged)

- `[tool.ruff] required-version = "==0.16.7"` as the **enforcing** declaration
  (`pyproject.toml:66`), the exact dev pin `ruff==0.16.7` (`pyproject.toml:44`), and the
  `ruff-pre-commit` `rev: v0.16.7` (`.pre-commit-config.yaml:2`).
- Three static guards in `tests/test_ci_workflows.py`
  (`test_ruff_pin_hook_rev_and_required_version_agree`,
  `test_workflows_do_not_declare_a_ruff_version`,
  `test_contributing_names_the_declared_ruff_version`), each **deriving** `X.Y.Z` from the dev pin
  via `_declared_ruff_version()` and holding no version literal.
- Plus a fourth scenario mapped to verify-phase **runtime** evidence (a mismatch probe must fail
  loudly).

---

## 3. The two decisions: home comparison and recommendation

### 3.1 Candidate homes, with cost/breakage

| Home | What it would carry | Cost / what it breaks |
| --- | --- | --- |
| **`ci` spec — new requirement CI-09** (`openspec/specs/ci/spec.md:285` insertion point, rows appended at `:393`) | Both decisions: (i) `tests/` stays out of the mypy **and** pyright gates, with rationale; (ii) pyright is a real gate: config home, mode, scope, warning posture, CI step, pin, guards | Cost: one new requirement block + its delta file + N Test Mapping rows; **breaks nothing** — CI-01..CI-08 stay byte-identical (additive convention). This is the capability that already owns gate config/declaration truth (CI-01 flags-in-config ban, CI-06 documentation truth, CI-07 declaration equality, CI-08 pin authority) and the one that indexes `tests/test_ci_workflows.py` in its Test Mapping. |
| **`ci` — two requirements (CI-09 tests/-exclusion posture, **CI-10** pyright gate) | Same content, split | Cost: two archive insertions, two `---` blocks, a second delta section; benefit: each decision independently assertable/replaceable. Slightly more inventory for an issue that is one policy question with two halves. |
| **`process-boundary` PB-15** | The local-invocation half (pre-commit hook roster) — PB-14 precedent for "repository-declared hook scope" | Cost: `ci` still needs the CI-step half, so this **splits one gate across two capabilities** (two deltas, two guard groups, cross-references both ways). Use only if the design decides the pre-commit hook is the load-bearing surface. |
| **PB-07 modification** (existing clause already mentions "mypy excludes `tests/`") | Q1's posture | Cost: **destructive edit** of an existing requirement; the repo's convention is the "Modified by …"/"(Previously: …)" marker (PB-09 precedent) and additive recording. Higher review cost than CI-09 for less clarity. |
| **`CONTRIBUTING.md` §Type checking** (`:79-81`) | Human-facing statement of both decisions + the drift fix | Not durable on its own: a spec requirement is needed for the *contract*; CONTRIBUTING is the **documentation surface** CI-06-style tests can assert. Must land in the same change (AGENTS rule 7/13 spirit). |
| **`AGENTS.md` rules 5 and 12** | rule 5 (pre-commit roster), rule 12 (latent-issue note names the five tomli sites) | rule 5 already says "`ruff` … and `mypy` run on every commit" — a pyright hook would make that sentence **factually stale**, so it must be edited if a hook is added; rule 12 is already CI-07-asserted text and must not be weakened (only cross-referenced). Cost: small, but rule-12 text is spec-asserted, so any edit is a contract edit. |
| **`pyproject.toml` comments** (`[tool.mypy]` / new `[tool.pyright]` block) | Inline rationale next to the declarations | Zero archive cost and visible at the point of truth — but **not enforceable** and not a decision record in SDD terms. The `ruff` comment at `pyproject.toml:63-66` is the precedent for *how* to write it. Use as a supplement, never as the home. |
| **`README.md` / `README_ES.md` §"Quality gates and security scanning"** (`README.md:753-768`) | User-facing gate roster (today: coverage + CodeQL only; mypy is **absent**) | AGENTS rule 13 forces the same edit in `README_ES.md` (`:794` area). Not a decision record. Note: adding pyright here without adding mypy would be odd — see §7 open question. |
| **`.github/PULL_REQUEST_TEMPLATE.md`** | Checklist item + verification block | CI-06 S4 precedent (the coverage-gate item). Small, and it is the surface contributors actually read. |
| **`openspec/project.md`** (`:14`, `:16-17`, `:70`, `:82-83`) | The stack/commands truth table | **Stale throughout** (says mypy 2.3.0, ruff 0.16.0, coverage "not installed", 1342 tests, 29 test files). Editing it here would half-refresh a file owned elsewhere; flag, do not absorb. |
| **`openspec/config.yaml`** (gitignored SDD-local) | `testing.quality.type_checker.command`, `testing.pre_commit` | CI-06 S1 asserts two coverage keys only, and the test **skips** when the file is absent (gitignored). Adding a pyright key is optional and cannot be a gate; if touched, it is local state, not a contract. |

### 3.2 Recommendation

1. **Contract home: `ci`, as one new additive requirement `CI-09` ("Type-gate posture: `tests/`
   excluded from mypy, pyright adopted as a real gate") with both decisions as separately-scenario'd
   clause groups.** Rationale: `ci` owns gate config/declaration truth, already has the Test
   Mapping table that indexes the guard file, and the additive-next-free-ID convention is the
   repo's established archive mechanics. Keep `PB-07` and `PB-14` **cross-referenced, not edited**.
   If the design prefers strict one-decision-one-requirement, split into CI-09 + CI-10 with the
   same clauses and rows — that is the only structural difference.
2. **Documentation surfaces in the same change: `CONTRIBUTING.md` §Type checking (both decisions,
   and the `strict = false` drift fixed), `AGENTS.md` rule 5 (only if a pre-commit hook lands) and
   a cross-reference from rule 12's latent-issue note, `README.md` + `README_ES.md` gate section,
   PR-template checklist item.** These are what CI-06-style text guards can assert.
3. **Inline rationale comments in `pyproject.toml`** next to `[tool.mypy]` (why `tests/` stays out)
   and in the new `[tool.pyright]` block (why this mode/scope), in the style of
   `pyproject.toml:63-66`.
4. **Do not touch** `openspec/project.md`, `openspec/config.yaml`, or the `## Purpose` enumerations
   (CI-07/CI-08 precedent for the latter).

---

## 4. The 10 `basic` errors and their canonical minimal resolution

Legend for the last column: **R14** = a module in AGENTS rule 14's 100.00%-coverage mandate
(`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) where `# pragma: no cover` is forbidden and
every line must execute in tests.

| # | Diagnostic | Location (verified) | Real defect? | Canonical minimal resolution | Files touched | R14 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reportArgumentType` — `list[_CellGetValue]` vs `list[object]` invariance | `_converters.py:620` `raw_rows.append(vals)`; `raw_rows: list[list[object]]` at `:611`; `vals = list(row)` at `:614` | **No** — purely a typing gap. Values are openpyxl cell scalars; storing them as `object` is what the code already means. mypy misses it only because it does not model openpyxl (untyped under `ignore_missing_imports`), while pyright resolves openpyxl's real types. | **Fix in code, 1 line:** annotate the binding — `vals: list[object] = list(row) if row is not None else []` (`:614`). No behaviour change, no new executable line, coverage-neutral. Preferred over an ignore (also strictly better typing). | `_converters.py` | No |
| 2-6 | `reportMissingImports` "tomli" ×5 | `cli.py:465`, `config.py:151`, `mcp_registration.py:128`, `mcp_server.py:687`, `model.py:411` | **No** — the py<3.11 marker-only runtime dep (`pyproject.toml:27`, `tomli>=2.0; python_version < '3.11'`), absent on the 3.13 gate interpreter **by design** (AGENTS rule 12 / CI-07). | **Preferred (DRY, zero `src/` edits):** `[tool.pyright] stubPath = …` + one committed stub package for `tomli` (`<name>-stubs/__init__.pyi`, PEP 561 layout — exact accepted layout is an open measurement, §7-O2). **Fallback:** 5 per-line `# pyright: ignore[reportMissingImports]` comments (comment-only; does not affect coverage; **not** a coverage pragma, so rule 14 is untouched). | `pyproject.toml` + 1 new stub file **or** the 5 modules (incl. **R14 `cli.py`**) | cli.py **yes** |
| — | **REJECTED**: add `tomli` to the `dev` group | would install it on 3.13 | — | On 3.13 the `try:` arm (`cli.py:465`) would then **succeed**, the `except ImportError:` arm at `cli.py:466-467` would never execute, `import tomllib as _tomli` (`:467`) becomes a missed line, and the **`cli.py` COV-06 row can no longer reach 100.00%** → the CI coverage job fails. This is the rule-12 failure mode in reverse. **Do not add tomli to dev deps.** | — | — |
| 7 | `reportAttributeAccessIssue` — `TextIO.reconfigure` | `prepare.py:445` (`sys.stdout.reconfigure(encoding="utf-8")`, guarded by `sys.platform == "win32" and hasattr(sys.stdout, "reconfigure")` at `:444`) | **No** — typeshed places `reconfigure` on `TextIOWrapper`, not `TextIO`; the runtime guard is deliberate duck typing. | Per-line `# pyright: ignore[reportAttributeAccessIssue]` (comment-only, zero behaviour change) **or** `cast("io.TextIOWrapper", sys.stdout).reconfigure(...)`. | `prepare.py` | **Yes** |
| 8 | same | `publish.py:686` (guard at `:685`) | same as #7 | same as #7 | `publish.py` | **Yes** |
| — | **REJECTED for #7/#8**: narrow with `isinstance(stream, io.TextIOWrapper)` (the house pattern at `cli.py:1609-1611`, which is exactly why `cli.py`'s `reconfigure` call is **not** in the error list) | — | — | The two win32 tests inject a **duck-typed** `_FakeStdout` and assert `fake.reconfigured is True` (`tests/test_prepare.py:1626-1657`, `tests/test_publish.py:2018-2052`). Narrowing the guard would fail both tests **and** leave `:445` / `:686` unexecuted — a rule-14 violation by construction. Any code-level narrowing therefore also edits two test files; that is a larger, riskier change than the ignore/cast. | — | — |
| 9 | `reportPrivateImportUsage` | `publish.py:70` `from huggingface_hub.utils import RepositoryNotFoundError` (used at `:238`) | **Arguably yes** — importing a *public* error class through a private/re-export namespace. Runtime works today, but the import path is not part of huggingface_hub's declared public surface. | **Prefer the code fix:** import from the public module (`from huggingface_hub.errors import RepositoryNotFoundError`), **verifying in apply** that the declared floor `huggingface-hub>=0.26.0` exposes it there. Fallback: per-line ignore. | `publish.py` | **Yes** |
| 10 | `reportMissingImports` "datasets" | `verification.py:66` (optional-dependency guard, `try: import datasets / except ImportError:` → skipped report) | **No** — `datasets` is deliberately **not** a dependency (`pyproject.toml:28-36`) and must stay optional; mypy covers this via `ignore_missing_imports = true`. | Per-line `# pyright: ignore[reportMissingImports]` (1 line). **Do not** add `datasets` as a dev dep (heavy; violates "no new dependency beyond the gate"). A stub in `stubPath` is possible but must model `load_dataset`, `DatasetDict.keys()`, `__getitem__`, `len` — more drift surface for one call site. | `verification.py` | No |

**Net code deltas for a green `src/` gate:** 1 annotation (`_converters.py`), 1 import path
(`publish.py`), 2 ignores-or-casts (`prepare.py`, `publish.py`), 1 ignore (`verification.py`),
and 5 tomli resolutions via either one stub file + config or 5 comments. All are type-only or
comment-only; **none changes runtime behaviour**, so the test suite and coverage rows are
unaffected in the recommended shape.

---

## 5. Decide-scope: mode, warnings, path scope

### 5.1 `typeCheckingMode`

| Mode | `src/` errors today | Read |
| --- | --- | --- |
| `basic` | 10 | Smallest gate; enables the error-severity core (missing imports, argument/attribute/assignment types). |
| `standard` | **11** | **Recommended.** The strongest mode reachable inside this change's budget; closest analogue to a real second opinion beside `mypy strict = false, check_untyped_defs = true`. Enables `reportRedeclaration`, incompatible overrides, `reportConstantRedefinition`, etc. — the rules that catch *future* regressions, which is the point of adopting a gate. |
| `strict` | 578 | Out of scope: a type-cleanup campaign, not a policy change. Explicitly a non-goal (§8). |

**Cost of `standard` over `basic`: exactly one error.** The parent measured the 10 `basic` errors
individually; the **11th (`standard`-only) error is not enumerated** — that is **open measurement
O1** (§7). It must be identified and resolved before the mode can be committed, and the design must
check the candidates that plausibly fire on this tree: `reportRedeclaration` on the five
`import tomli as _tomli` / `import tomllib as _tomli` double-import sites (which would be **5**
errors, not 1 — so probably *not* this one), `reportIncompatibleVariableOverride`,
`reportPrivateUsage`, `reportConstantRedefinition`, `reportUnsupportedDunderAll`. If O1 turns out
to be systemic rather than a single local fix, fall back to `basic` and record the mode choice as a
decision with its rationale (rather than silently weakening it later).

### 5.2 Warning severity — the issue's explicit requirement

- pyright's CLI **exits non-zero only on errors**; `--warnings` promotes warnings into the failure
  condition.
- Measured today: with an explicit `typeCheckingMode` config at the repo root, `src/` reports
  **0 warnings** in all three modes; the **no-config-default** run reported **18 errors / 1088
  warnings**. That no-config row is the one shape that would make `--warnings` expensive, and its
  rule composition was **not enumerated** — **open measurement O2** (§7). It must be reproduced
  under the committed config, because the committed config is what the gate runs.
- **Recommendation (explicit decision to be written into CI-09):** warnings SHALL NOT fail the
  gate — the gate's exit contract is **errors only** (pyright's default semantics), and any rule
  the design wants to bind SHALL be declared at `error` severity in `[tool.pyright]`, never left at
  warning severity and hoped for. Record the measured `"N errors, M warnings"` summary line as
  verify-phase runtime evidence, so a future warning-count jump is visible in the report even
  though it does not fail the build. This answers "warning severity must be explicitly decided"
  without adopting an undefined failure mode.

### 5.3 Gate path scope — `src/` only vs `src/ scripts/`

- The **mypy** anchor is asymmetric by design: `CONTRIBUTING.md:28` and most historical evidence
  use `uv run mypy src/`, while the **enforced** invocations are `uv run mypy src/ scripts/`
  (`.github/workflows/ci.yml:21`, `.pre-commit-config.yaml:22`, and CI-07 S2 names exactly that as
  "the exact entry of the local pre-commit mypy hook").
- `scripts/` contains **exactly one** file: `scripts/update_citation.py` (stdlib-only, ~200 lines,
  `from __future__ import annotations`, no third-party imports). **Its pyright result is an open
  measurement (O3)** — it cannot be measured in this phase.
- **Recommendation:** default to **`src/ scripts/`** to mirror the *enforced* mypy scope (one
  scope for "what type-checks in this repo", which is also what CI-07 asserts), **conditional on
  O3**: if `scripts/update_citation.py` reports errors beyond a trivial local fix, fall back to
  `src/` and record the narrowing as a decision with its rationale (the alternative — leaving
  `scripts/` unchecked while mypy checks it — should be named, not implied).
- **How scope is declared matters for drift.** Two viable shapes:
  - **(A) config-driven:** `[tool.pyright] include = ["src", "scripts"]`,
    `exclude = ["tests", ".venv", …]`, and the gate runs **bare** `uv run pyright`. One
    declaration, guard-able as a unit, and the `tests` exclusion is enforceable exactly once.
  - **(B) invocation-driven:** `uv run pyright src/ scripts/` in `ci.yml` + the hook, mirroring
    mypy's shape — but scope is then declared in **two** files that can silently drift, and
    command-line file specs bypass `include`/`exclude` (so the `tests` guarantee rests on the
    invocation text instead of the config).
  - **Recommendation: (A)**, with a guard asserting the config keys. (B) is acceptable if the
    design prefers literal symmetry with mypy; if (B) is chosen, the `tests` guard must assert the
    invocation text *and* keep an `exclude` key as belt-and-braces.

---

## 6. Pinning and invocation (CI + local)

### 6.1 Distribution choice

| Option | Shape | Cost / risk |
| --- | --- | --- |
| **PyPI `pyright` wrapper as a `[dependency-groups] dev` pin** (`pyright==X.Y.Z`) | The version reaches CI through `uv.lock` — the same path ruff takes (`uv.lock:2033`, CI-08 S2's "no version literal in a workflow") | **Recommended.** Matches #195's single-authority discipline and the existing dev-group roster (`pyproject.toml:38-47`). **Requires Node at runtime** — GitHub's ubuntu-latest runners ship Node, and Node is present on this Windows box (the global npm pyright proves it). The wrapper's own optional Node extra (if offered by the pinned version) can remove the system-Node assumption — **verify in design, O4**. |
| npm / `npx pyright@X.Y.Z` in the workflow | No `uv.lock`/dev-group change | **Not recommended**: the version literal lands **inside a workflow**, which is precisely the shape CI-08 S2 bans for ruff; it also splits the pin away from the dev group and adds a second package manager to CI. |
| `basedpyright` (PyPI-native fork, no Node) | No Node dependency | **Not "pyright"** — a different analyzer with a different rule catalogue and different baselines; adopting it would invalidate the measured 10/11/578 counts and would not be what Q2 asked for. Only if the design concludes Node is unacceptable. |

### 6.2 Version-pinning discipline, mapped to #195's precedent

- **Single authority + exact pin:** `pyright==X.Y.Z` in `[dependency-groups] dev`, guarded by a
  test that derives `X.Y.Z` from the pin (reusing the shape of `_declared_ruff_version()` and
  `_EXACT_PIN_RE` in `tests/test_ci_workflows.py`) and asserts it equals the `uv.lock` resolution
  entry; **no workflow SHALL declare a pyright version literal** (CI-08 S2 analogue).
- **The ruff-analogue "enforcing declaration" does not exist for pyright**: ruff has
  `required-version` (config load fails on a mismatched binary); pyright has **no equivalent config
  key** (open measurement O5 — confirm against the pinned version's config schema; do not assume).
  Therefore the *enforcement* half must be verify-phase runtime evidence instead: `uv run pyright
  --version` must equal the dev pin.
- **`uv.lock` regeneration is required** when the dev group changes — CI-08 already states the
  obligation for a pin move ("confined to the … package block and the dev specifier"), and PKG-06
  states the same regeneration class. Cost: a diff in the dev-group closure region
  (`uv.lock:2093-2120`) plus the wrapper's transitive packages.
- **Baseline identity caveat:** the 10/11 counts are the parent's measurement with the *locally
  installed* npm pyright (reported 1.39.9). Analyzer versions change their diagnostics, so the
  design must **re-measure the baselines with the pinned distribution/version** before committing
  the mode and the resolution table (O6). If the counts differ from those in §2.3, the §4 table is
  the thing to re-derive, not to assume.

### 6.3 Config home (single authority)

- **`[tool.pyright]` in `pyproject.toml`,** placed immediately after `[tool.mypy]`
  (`pyproject.toml:77-83`), so both type-checker declarations live in one file.
- **A guard SHALL assert there is no `pyrightconfig.json`** (repo root, and by extension anywhere
  in the tree): pyright silently prefers `pyrightconfig.json` over `[tool.pyright]`, so a stray
  file would quietly re-create the drift class #195/CI-08 closed. This is the pyright analogue of
  "single authoritative version".
- Config keys the gate needs, at minimum: `typeCheckingMode`, `include`, `exclude` (must contain
  `tests`), `pythonVersion` (decide: mirror `[tool.mypy] python_version = "3.10"` — the *minimum*
  language level, per CI-07's clause — or pin to the gate interpreter `3.13`; **O7**), and
  `stubPath` if the tomli stub route is chosen; `reportMissingImports` **SHALL NOT** be globally
  disabled.

### 6.4 Invocation surface

| Surface | Recommendation | Cost / breakage |
| --- | --- | --- |
| **CI lint job** (`.github/workflows/ci.yml:6-23`, after the mypy step at `:21`) | **Mandatory** — one step, e.g. `uv run pyright` (shape A) or `uv run pyright src/ scripts/` (shape B), under the existing Python 3.13 pin (CI-07 invariant preserved: `.python-version` = lint-job pin = coverage-job pin = `3.13`). | +1 step (~4 lines); no other workflow changes. |
| **Local pre-commit hook** (`.pre-commit-config.yaml:19-25`) | **Recommended, as a second `repo: local` hook entry** with `pass_filenames: false`, mirroring the mypy entry's shape — this is what makes "gate" true locally. Cost: every commit pays pyright startup, **and a contributor without Node gets a hard commit failure** (the wrapper needs Node). If the design judges that unacceptable, record the CI-only posture explicitly and note it diverges from the mypy precedent + from `AGENTS.md` rule 5's sentence. | +6-10 lines; rule 5 wording must be updated either way the choice lands. |
| **Local manual command** (`CONTRIBUTING.md:24-30` Development commands) | Mandatory documentation; the CI-08 S3 precedent ("CONTRIBUTING names the declared version") shows documentation is a guarded surface. | +1-2 lines. |

---

## 7. Test-guard plan

### 7.1 Inventory of the existing guard module (`tests/test_ci_workflows.py`, 23 tests)

Helpers available for reuse: `_read_text`, `_load_toml`, `_load_yaml`, `_as_list`, `_workflow`,
`_triggers`, `_workflow_names`, `_coverage_jobs`, `_find_step`, `_openspec_config`,
`_declared_ruff_version`, `_DEV_ENTRY_RE`, `_EXACT_PIN_RE`, `_RUFF_PRE_COMMIT_REPO`,
`_REPO_ROOT`, `_WORKFLOW_DIR`.

| Test | What it asserts |
| --- | --- |
| `test_ci_workflow_files_present` | `ci.yml`, `release.yml`, `codeql.yml` exist before any parse (fails loudly, not vacuously) |
| `test_pyproject_declares_coverage_fail_under_90` | CI-01 S1: `[tool.coverage.report] fail_under == 90` |
| `test_coverage_job_gates_core_modules_at_100` | COV-06: gate script roster `cli scanner prepare publish`, `--include=…--fail-under=100 -m`, referenced from `ci.yml`; no non-100 floor literal, no `fail_under` key in script/workflows |
| `test_agents_md_declares_core_100_mandate` | COV-06: AGENTS rule 14 names the four modules, "100.00%", and the pragma ban |
| `test_coverage_gate_is_config_driven_without_cli_floor` | CI-01 S2 (TOTAL only): no floor literal/flag in either workflow; the report step is the flag-free `uv run coverage report -m` |
| `test_coverage_report_honors_show_missing` | CI-01 S3: `show_missing is True` + report step present |
| `test_coverage_jobs_generate_and_upload_htmlcov` | CI-02 S1: 2 coverage jobs; `coverage html` + `upload-artifact@v7` named `coverage-html`, path `htmlcov` |
| `test_coverage_report_step_lists_missing_lines` | CI-02 S2 |
| `test_no_xml_codecov_or_badge_references_in_workflows` | CI-02 S3 |
| `test_release_is_gated_on_the_coverage_job` | CI-03 S1: `needs` graph (`coverage`, `build`, `citation-check`, `release`) |
| `test_codeql_has_push_pr_and_weekly_triggers` | CI-04 S1 |
| `test_codeql_pull_request_targets_dev` | CI-04 S2 |
| `test_codeql_security_write_permission_and_python` | CI-04 S3: permissions map + `init@v4 languages: python` + `analyze@v4` |
| `test_codeql_init_references_config_file` | CI-05 S1: `config-file: ./.github/codeql/config.yml` |
| `test_codeql_private_window_publishes_sarif_artifact_without_upload` | Private-window guard: `upload: never` + SARIF artifact |
| `test_codeql_paths_ignore_covers_non_code_trees` | CI-05 S2: `docs/`, `.github/`, `openspec/` present; `src/sofer/` absent |
| `test_openspec_config_declares_coverage_available_at_90` | CI-06 S1 (skips when the gitignored file is absent) |
| `test_contributing_documents_coverage_floor` | CI-06 S2: "90%", both coverage commands, "no drop in coverage" gone |
| `test_pr_template_has_coverage_checklist_item` | CI-06 S4: "Coverage gate met" + "README_ES.md updated" in the Checklist |
| `test_ruff_pin_hook_rev_and_required_version_agree` | **CI-08 S1** — the pin-authority pattern to imitate |
| `test_workflows_do_not_declare_a_ruff_version` | **CI-08 S2** — "version reaches CI through `uv.lock`, never a workflow" |
| `test_contributing_names_the_declared_ruff_version` | CI-08 S3 — derives the version, holds no literal |
| `test_ruff_format_hook_excludes_markdown` | PB-14 S1: exactly one `ruff-format` entry, list-valued `types_or`, no `markdown` |

Runtime gate exit-code evidence is **not** asserted here (CI-01 S2 and CI-08 S4 record it in the
verify report) — that is the dialect a pyright gate must follow.

### 7.2 New guards this change implies

| Guard (proposed name) | Asserts | Notes |
| --- | --- | --- |
| `test_pyright_config_declares_the_decided_posture` | `[tool.pyright]` exists in `pyproject.toml`; `typeCheckingMode` equals the decided value; `include` covers the decided scope; **`exclude` contains `tests`**; `reportMissingImports` is **not** globally disabled (`not in ("none", False)`) | Asserts the **decision class**, not a mirror of the whole config, so adding a rule key later stays green (PB-14 S1's "assert the defect class" principle). |
| `test_pyright_has_exactly_one_config_home` | No `pyrightconfig.json` in the repo (root or any subdirectory) | Guards the single-authority property (§6.3); this is the pyright analogue of CI-08 S1's three-declaration equality. |
| `test_ci_lint_job_runs_the_pyright_gate` | `ci.yml` `lint` job has a step whose `run` equals the decided invocation; and **no workflow contains a pyright version specifier** (mirror of CI-08 S2) | Reuses `_find_step` / `_workflow`. |
| `test_mypy_and_pyright_exclude_tests` (Q1's record) | `[tool.mypy] exclude` contains `tests/`; **every** mypy invocation in `ci.yml` and `.pre-commit-config.yaml` names `src`/`scripts` and never `tests`; the pyright config keeps `tests` out too; `CONTRIBUTING.md` documents the posture | This is the testable core of decision (a) — "`tests/` is out of **both** gates" becomes a red-then-green guard rather than prose. |
| `test_pyright_dev_pin_is_exact_and_matches_the_lock` | Exactly one `pyright==X.Y.Z` in `[dependency-groups] dev` (reuse `_DEV_ENTRY_RE` / `_EXACT_PIN_RE`), and the same version appears in `uv.lock`'s resolved entry | Derived, never a literal (CI-08 S1/S3 rule). |
| `test_contributing_documents_the_pyright_gate` | CONTRIBUTING §Type checking names the pyright invocation (and, if the drift fix lands, states the real mypy posture) | Keep the assertion **presence-shaped**; asserting the *absence* of the substring "strict mode" is brittle — if the design wants the drift locked, assert the true posture positively (e.g. `strict = false` named or the pyright/mypy commands both present). |
| (text guard, CI-06 S4 shape) | PR template Checklist carries the pyright item | If a checklist item is added. |
| (verify-phase static evidence rows) | `README.md` / `README_ES.md` gate section mirror | Not pytest-assertable (CI-06 S3 precedent). |

### 7.3 Verify-phase (runtime) evidence the design must plan for

1. `uv run pyright` (or the decided invocation) → **exit 0**, with the pasted summary
   (`N errors, 0 warnings`).
2. `uv run pyright --version` → equals the dev-pin `X.Y.Z` (the enforcement that pyright itself
   lacks, §6.2).
3. **Red-first proof that the gate is real** (CI-08 S4 mismatch-probe precedent): inject a
   deliberate type error in a scratch file **inside the gate's scope**, show the gate exits
   **non-zero** with that error reported, remove it, show exit 0. Without this, "adopted as a real
   gate" is an unproven claim.
4. Confirm the gate does **not** analyze `tests/`: run the gate and show `tests/` files absent from
   the output (or that a deliberately broken `tests/` file does not fail it).
5. `uv run pytest tests/ -q` unchanged green; `bash scripts/check_core_coverage.sh` four 100.00%
   rows unchanged; `uv run mypy src/ scripts/` exit 0.

---

## 8. Non-goals (respect strictly)

- **No coverage change of any kind:** no floor movement, no `# pragma: no cover` (forbidden in the
  four rule-14 modules), no test-count weakening, no `scripts/check_core_coverage.sh` or
  `fail_under` edit. In particular, no resolution may add `tomli` to the dev environment (§4).
- **No mypy `strict = true` flip.** `strict = false` stays; the CONTRIBUTING drift is a
  **documentation** fix in this change, not a config tightening.
- **No pyright gate over `tests/`** (decision (a)); `tests/` stays out of both gates.
- **No CI test-matrix change and no `release.yml` change.** The coverage job, the 3.10–3.14 ×
  ubuntu/windows matrix, and the release `needs` chain stay byte-identical.
- **No dependency beyond the gate itself:** the pyright pin (and its transitive Node shim) is the
  only addition; no `datasets`, no `tomli`, no new test-only packages.
- **No `pyrightconfig.json`** (single config home), and no version literal in any workflow.
- **Do not edit** `ci` CI-01..CI-08, `PB-07`, `PB-14`, or the canonical `openspec/specs/**` before
  `sdd-sync`; do not refresh the stale `## Purpose` enumerations; do not absorb the other
  documentation drifts (§9) — they have owners.
- No commit, push, or PR from the SDD phases themselves.

---

## 9. Open questions and measurements owed

| ID | Question / measurement | Owner |
| --- | --- | --- |
| **O1** | Identify and resolve the single `standard`-mode-only 11th error on `src/` (candidate rule codes listed in §5.1). Does it need a code fix, an ignore, or does it push the choice back to `basic`? | design/apply |
| **O2** | Reproduce the four measured runs **under the committed `[tool.pyright]` config** and enumerate: (a) the rule codes behind the no-config 18 errors / 1088 warnings; (b) the warning count under the chosen mode. The "warnings do not fail the gate" clause needs this to be a decision, not an assumption. | design |
| **O3** | `scripts/update_citation.py` diagnostic count under the chosen mode (decides `src/ scripts/` vs `src/`, §5.3). | design/apply |
| **O4** | Does the pinned PyPI `pyright` version offer a Node-provisioning extra (removing the system-Node assumption), and can `uv lock` express it? | design |
| **O5** | Confirm pyright has **no** `required-version` analogue in the pinned version's config schema; if one exists, the pin-enforcement design changes (§6.2). | design |
| **O6** | Re-measure the §2.3 baselines with the **pinned** distribution/version — do the 10 / 11 / 578 counts hold? (The parent's numbers come from the local npm install.) | design |
| **O7** | `[tool.pyright] pythonVersion`: mirror `[tool.mypy] python_version = "3.10"` (the minimum, per CI-07's clause that it "declares the minimum language/typing level") or pin to the gate interpreter `3.13`? The choice changes which diagnostics fire (e.g. `tomllib` availability). | design |
| **O8** | Pre-commit hook or CI-only (§6.4)? Interacts with `AGENTS.md` rule 5's sentence and with the Node-on-contributor-machines risk. | design |
| **O9** | Does the README gate section gain **both** mypy and pyright, or pyright only? Today the README never mentions mypy (verified) — adding pyright alone would be asymmetric. | proposal/design |
| **O10** | One requirement (CI-09 with two clause groups) or two (CI-09 + CI-10)? Both are precedent-consistent; archive cost differs (§3.1). | proposal |
| **O11** | Exact `stubPath` layout pyright accepts for the `tomli` stub (`typings/tomli-stubs/__init__.pyi` PEP 561 shape vs a bare `.pyi`), and whether the stub route or 6 per-line ignores is preferred. | design/apply |
| **O12** | Should the `tests/`-exclusion decision also be referenced from PB-07 (which already implies it) without editing PB-07's clauses? | design |

### 9.1 Drift findings recorded (not absorbed)

1. **`CONTRIBUTING.md:81` claims mypy strict mode** while `pyproject.toml:79` sets
   `strict = false`. The two are contradictory; the issue's own scope makes the documentation side
   of this drift in scope here.
2. **`CONTRIBUTING.md:75` points at "`ruff.toml` at the repo root"** — no such file exists
   (`[tool.ruff]` lives in `pyproject.toml`). Already owned elsewhere (issue **#187** per the
   archived CI-08 delta); recorded, not absorbed.
3. **`openspec/project.md` is stale** (`:14` mypy 2.3.0, `:82` ruff 0.16.0, `:86` "Coverage
   tooling: not installed", `:45` "1342 passed", `:39` "29 test files"). Not this change's job.
4. **`README.md`/`README_ES.md` gate section omits mypy entirely** (`README.md:753-768` covers
   coverage + CodeQL only) — relevant to O9.
5. **`openspec/config.yaml` `type_checker.command` is `uv run mypy src/`** while the enforced
   invocation is `src/ scripts/`, and it would silently omit pyright; it is gitignored local SDD
   state (CI-06 S1 skips when absent), so it cannot carry the contract.

---

## 10. Workload forecast (1500-line review budget)

| File | Change | Est. lines |
| --- | --- | --- |
| `pyproject.toml` | `[tool.pyright]` block + rationale comment; `pyright==X.Y.Z` in the dev group | +14 / −0 |
| `uv.lock` | dev-group closure + the wrapper's transitive entries | +40 … +120 (mechanical) |
| `.github/workflows/ci.yml` | one pyright step in the `lint` job | +4 … +6 |
| `.pre-commit-config.yaml` | second `repo: local` hook entry (if O8 = yes) | +6 … +10 |
| `src/sofer/_converters.py` | `vals: list[object]` annotation | 1 |
| `src/sofer/publish.py` | public import path; 1 reconfigure ignore-or-cast | 2 |
| `src/sofer/prepare.py` | 1 reconfigure ignore-or-cast | 1 |
| `src/sofer/verification.py` | 1 optional-dep ignore | 1 |
| `src/sofer/{cli,config,mcp_registration,mcp_server,model}.py` | 0 (stub route) or 5 tomli ignores | 0 … 5 |
| `typings/tomli-stubs/__init__.pyi` (if stub route) | new file | +10 … +20 |
| `tests/test_ci_workflows.py` | 5-6 new guards + small helpers | +100 … +180 |
| `CONTRIBUTING.md` | Type checking section rewritten; drift fixed; commands | +6 … +10 / −2 |
| `AGENTS.md` | rule 5 wording (and/or a rule-12 cross-reference) | +2 … +6 |
| `README.md` + `README_ES.md` | gate-section bullet(s), mirrored | +4 … +8 |
| `.github/PULL_REQUEST_TEMPLATE.md` | checklist item (+ verification line) | +2 … +3 |
| SDD artifacts (this file, proposal, design, tasks, spec delta, verify report) | — | +250 … +400 (not source) |

**Code + config + tests: ≈ 180–330 changed lines** (≈ 220–450 including `uv.lock`). Against the
1500-line budget that is **~15–30 % of budget** — comfortably a **single PR**; no chaining, no
`size:exception`, no `ask-on-risk` delivery pause expected. The dominant review-load risks are
(a) `uv.lock`'s mechanical diff and (b) the guard-test block — both bounded. If O1 (the 11th
`standard` error) or O11 (stub layout) turns out to require a redesign, the forecast moves by
tens of lines, not hundreds.

---

## 11. Summary of recommendations

1. **Q1 record:** new **additive** `ci` requirement with a scenario asserting `tests/` is out of
   the mypy **and** pyright gates (`[tool.mypy] exclude`, invocation texts, `[tool.pyright]
   exclude`), plus the `CONTRIBUTING.md` §Type checking rewrite that also fixes the
   `strict = false` drift; cross-reference `PB-07` instead of editing it.
2. **Q2 record:** the same requirement (or CI-09 + CI-10) declares pyright a **real gate**:
   `[tool.pyright]` in `pyproject.toml` within `include`/`exclude`, `typeCheckingMode = standard`
   (fall back to `basic` if O1 says so), **warnings do not fail the gate** with the summary line
   recorded as evidence, an exact `pyright==X.Y.Z` dev pin + `uv.lock` refresh, one CI lint-job
   step, no version literal in any workflow, no `pyrightconfig.json`, and a red-first
   runtime proof.
3. **Ten diagnostics:** two real code improvements (`_converters.py:614` annotation,
   `publish.py:70` public import path), two comments-or-casts on the runtime-guarded
   `reconfigure` calls, one optional-dep ignore, five tomli resolutions via a single stub (or five
   ignores) — and **never** a `tomli` dev dependency.
4. **Guards:** 5–6 new static tests in `tests/test_ci_workflows.py`, all deriving versions from the
   dev pin; the runtime proofs (green run, version equality, red-first failure, `tests/` untouched)
   belong in the verify report.
