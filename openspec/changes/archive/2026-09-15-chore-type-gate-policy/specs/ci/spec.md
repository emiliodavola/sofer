# Delta for ci

> **Change** `2026-09-15-chore-type-gate-policy` (GitHub #201) · branch
> `chore/201-type-gate-policy` · store **hybrid** (this file + Engram mirror under topic key
> `sdd/2026-09-15-chore-type-gate-policy/spec`).
>
> **Additive for CI-09, plus one authorized modification for CI-07.** CI-01..CI-06 and CI-08 keep their
> clauses, scenarios and Test Mapping rows byte-for-byte; the contract enters as **new** requirement **CI-09**,
> the next free ID in this capability, with **five** scenarios and **five** appended Test Mapping rows. CI-07
> receives **one** clause amendment (+ its own restatement in one scenario bullet) — the authorized exception
> of §6.6/DC-11, driven by the maintainer's decision that `[tool.mypy] python_version = "3.11"` stays.
>
> **Capability `ci`, justified.** `ci` owns gate config/declaration truth (CI-01 flags-in-config, CI-06
> documentation truth, CI-07 declaration equality, CI-08 pin authority) and is the capability whose Test
> Mapping indexes `tests/test_ci_workflows.py` — the file the six guards land in. The alternative home
> `process-boundary` PB-15 was rejected: this change arms a CI step, so a requirement about the gate's
> declaration belongs with the gate (EX §3.1).
>
> **One requirement, two clause groups.** Q1 (`tests/` excluded from both gates) and Q2 (pyright is a real
> gate) are two halves of one policy question; they are separately **scenario'd** rather than split into
> CI-09 + CI-10, which halves the archive-insert cost (P §4 D9, O10 closed).
>
> **Rule-6 resolution.** S1–S4 map to static guards G1/G3/G4/G5 in `tests/test_ci_workflows.py`; S5's
> declarations-invariance half maps to guard G6 and its mypy-exit-zero half maps to **verify-phase runtime
> evidence** (CI-01/CI-08 precedent — a pytest cannot spawn the gate without adding a dependency class
> AGENTS rule 9 keeps out).
>
> **One CI step is armed, deliberately.** Unlike CI-08 (which asserted the *inverse*), CI-09 declares the
> `lint`-job step that runs the pyright gate, and G3 keeps that step and the ban on workflow version
> literals in one guard.
>
> **Domain hygiene (checked at design time).** `openspec/specs/ci/spec.md` ends at CI-08; no other
> non-archived change carries `specs/ci/`; this change has no legacy flat `openspec/changes/<change>/spec.md`.
> The canonical file is **not** edited before `sdd-sync`.
>
> **Cross-references, not edits.** `process-boundary` PB-07 ("New test helpers SHALL be type-annotated even
> though mypy excludes `tests/`") is cited by S1 and left byte-identical; PB-14 (hook scope) and CI-08 (pin
> authority) are cited, never modified; and CI-07's `.python-version` pin and every clause other than the
> `python_version` declaration are cited and untouched **except** the single amendment frozen below.

## ADDED Requirements

### Requirement: Type-gate posture — `tests/` excluded from both type gates and pyright adopted as a real gate (CI-09)

> Added by change `2026-09-15-chore-type-gate-policy` (GitHub #201). Scenarios 1–4 are asserted
> by static guard tests in `tests/test_ci_workflows.py`; scenario 5's mypy-exit-zero half is
> verify-phase runtime evidence — the framing this capability's Test Mapping already uses for gate
> exit codes.

**Clause group Q1 — the `tests/` exclusion (the durable record of decision (a)).**

The repository SHALL keep `tests/` out of **every** enforced type gate. `[tool.mypy] exclude` SHALL contain
`tests/`; every mypy invocation in `.github/workflows/ci.yml` and `.pre-commit-config.yaml` SHALL name
`src`/`scripts` and SHALL NOT name `tests`; and `[tool.pyright] exclude` SHALL contain `tests`, so the
exclusion is declared once in configuration and the pyright gate SHALL be invoked **bare** (no path
arguments) for that declaration to be the single authority. The posture SHALL be documented in
`CONTRIBUTING.md`'s type-checking section, and this requirement SHALL NOT be read as relaxing
`process-boundary` PB-07: new test helpers SHALL still be type-annotated by convention even though neither
gate analyses them.

**Clause group Q2 — the pyright gate (the durable record of decision (c)).**

pyright SHALL be a **real** gate, not an advisory analyzer. `pyproject.toml` SHALL declare exactly one
`[tool.pyright]` table — the single configuration authority; no `pyrightconfig.json` SHALL exist anywhere in
the tree, because pyright silently prefers it over the table. That table SHALL declare
`typeCheckingMode = "standard"`, `include` covering `src` and `scripts` (the enforced mypy scope),
`exclude` containing `tests`, `pythonVersion` equal to the gate interpreter that `.python-version` pins,
`stubPath` naming the committed `tomli` stub directory, and SHALL NOT globally disable
`reportMissingImports`. One step in the `lint` job of `.github/workflows/ci.yml` SHALL run the gate, and one
local pre-commit hook SHALL run it locally, mirroring the `mypy` hook's shape (`pass_filenames: false`).

pyright SHALL be pinned by an exact `pyright==X.Y.Z` entry in `[dependency-groups] dev`, and the version
SHALL reach CI through `uv.lock`: **no file under `.github/workflows/` SHALL declare a pyright version
literal**. pyright has no `required-version` analogue, so the enforcement SHALL be a runtime equality proof
— `uv run pyright --version` SHALL equal the dev pin — recorded as verify-phase evidence.

The gate's exit contract SHALL be **errors only**: no invocation SHALL pass `--warnings`, and any rule the
repository wants to bind SHALL be declared at `error` severity in `[tool.pyright]` rather than left at
warning severity and hoped for. The measured `"N errors, M warnings"` summary SHALL be recorded as
verify-phase evidence so a warning-count jump is visible without failing the build.

The four `tomli` fallback sites that still select the parser behind `try:` / `except ImportError:`
(`cli.py`, `config.py`, `mcp_registration.py`, `model.py`) SHALL be resolved by the committed stub under
`stubPath`; `mcp_server.py`'s fallback is version-gated (`sys.version_info >= (3, 11)`), so a static checker
prunes its `tomli` arm and it needs no stub. `tomli` SHALL NOT be added to any dependency group, which would
make the fallback arm dead on the pinned interpreter and break the `cli.py` COV-06 row (AGENTS.md rule 12). The gate SHALL be invoked as `uv run pyright`, so
third-party imports resolve against the project environment.

**Clause group S — no weakening.** Adopting the new posture SHALL NOT weaken what already holds: under the
committed `[tool.mypy] strict = true`, `uv run mypy src/ scripts/` SHALL exit 0; the `[tool.coverage.report]`
TOTAL floor, the four COV-06 per-file gates, the CI test matrix and the `release.yml` `needs` graph SHALL be
unchanged; and no resolution of a type diagnostic SHALL add a `# pragma: no cover` anywhere.

#### Scenario: `tests/` stays out of both type gates

- GIVEN `pyproject.toml`'s `[tool.mypy]` and `[tool.pyright]` blocks, every mypy invocation in
  `.github/workflows/ci.yml` and `.pre-commit-config.yaml`, and `CONTRIBUTING.md`'s type-checking section
- WHEN `tests/test_ci_workflows.py::test_mypy_and_pyright_exclude_tests` inspects them
- THEN `[tool.mypy] exclude` SHALL contain `tests/` and `[tool.pyright] exclude` SHALL contain `tests`
- AND every mypy invocation SHALL name `src`/`scripts` and SHALL NOT name `tests`
- AND the type-checking section SHALL name both gate commands and state that `tests/` is excluded from
  both gates, so Q1's answer is documented where a contributor reads it
- AND the PR template's Checklist SHALL carry the pyright item (the CI-06 S4 shape), and
  `process-boundary` PB-07 SHALL be cross-referenced, not edited — its "test helpers are still
  annotated by convention" clause stays in force

#### Scenario: `[tool.pyright]` declares the decided posture and the gate runs

- GIVEN `pyproject.toml`, `.github/workflows/ci.yml`, and `.pre-commit-config.yaml`
- WHEN `tests/test_ci_workflows.py::test_pyright_config_declares_the_decided_posture` and
  `::test_ci_lint_job_runs_the_pyright_gate` inspect them
- THEN `[tool.pyright]` SHALL declare `typeCheckingMode = "standard"`, an `include` covering both
  `src` and `scripts`, an `exclude` containing `tests`, a `pythonVersion` equal to the value
  `.python-version` pins, and a `stubPath` naming the committed `tomli` stub directory
- AND `reportMissingImports` SHALL NOT be globally disabled
- AND the `lint` job SHALL contain exactly the bare gate invocation `uv run pyright`, and no file
  under `.github/workflows/` SHALL declare a pyright version literal
- AND the committed invocation SHALL exit 0 on the committed tree, with the measured
  `"N errors, 0 warnings"` summary recorded as verify-phase runtime evidence

#### Scenario: Exactly one pyright config home exists

- GIVEN the repository tree, excluding the virtual environment and other machine-local directories
- WHEN `tests/test_ci_workflows.py::test_pyright_has_exactly_one_config_home` searches it
- THEN zero `pyrightconfig.json` files SHALL exist, so `[tool.pyright]` stays the single
  configuration authority — the analogue of CI-08's single-declaration rule, which a stray JSON
  file would silently defeat because pyright prefers it over the table

#### Scenario: The pin is exact, reaches CI through the lock, and matches the running binary

- GIVEN `pyproject.toml`'s `[dependency-groups] dev` list and `uv.lock`
- WHEN `tests/test_ci_workflows.py::test_analyzer_dev_pins_are_exact_and_match_the_lock` derives
  `X.Y.Z` from the dev pin and compares the lock's resolved entry against it, and when
  `uv run pyright --version` runs
- THEN exactly one pyright dev entry SHALL exist and its specifier SHALL be the exact
  `==X.Y.Z`, so a `>=` floor SHALL fail the guard
- AND `uv.lock`'s resolved pyright package SHALL carry that same version
- AND the guard SHALL hold no version literal of its own, so a bump edits declarations only
- AND `uv run pyright --version` SHALL equal that version — the enforcement pyright itself lacks
  (it has no `required-version` analogue) — recorded as verify-phase runtime evidence

#### Scenario: Adopting the gate leaves every existing gate declaration intact

- GIVEN `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  `.pre-commit-config.yaml`, and `pyproject.toml`
- WHEN `tests/test_ci_workflows.py::test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`
  inspects them, and when `uv run mypy src/ scripts/` runs under the committed `strict = true`
- THEN the mypy invocations SHALL still be exactly `uv run mypy src/ scripts/` on both surfaces
  (the `lint` job step and the local `mypy` hook entry)
- AND no workflow SHALL declare a coverage floor literal or a `--fail-under` flag in its raw text,
  and exactly one `ruff-format` hook entry SHALL remain (PB-14)
- AND `uv run mypy src/ scripts/` SHALL exit 0 with zero errors, and the CI test matrix,
  `release.yml`'s `needs` graph, the TOTAL floor and the four COV-06 rows SHALL be unchanged —
  recorded as verify-phase runtime evidence (CI-01 gate-exit-code precedent)

---

## Test Mapping

The five rows below follow this file's canonical `## Test Mapping` format and are appended to that table at
`sdd-sync` — at the **end** of the existing table, immediately after the CI-08 `required-version rejects a
mismatched binary` row, which is the table's last content row today. The section's existing intro prose and
every existing row stay byte-identical; the two verify-phase row conventions already in use
("Verify-phase static evidence — `<command>`" and "Verify-phase runtime evidence — `<command>`") are reused
verbatim.

| Req | Scenario | Verification |
| --- | --- | --- |
| CI-09 | `tests/` stays out of both type gates | `tests/test_ci_workflows.py` — `test_mypy_and_pyright_exclude_tests`: tomllib parse of both type-checker blocks + text inspection of every mypy invocation and of `CONTRIBUTING.md`'s type-checking section and the PR template |
| CI-09 | `[tool.pyright]` declares the decided posture and the gate runs | `tests/test_ci_workflows.py` — `test_pyright_config_declares_the_decided_posture` and `test_ci_lint_job_runs_the_pyright_gate`: tomllib + YAML inspection; local gate run `uv run pyright` exit code with the measured summary line (verify-phase runtime evidence) |
| CI-09 | Exactly one pyright config home exists | `tests/test_ci_workflows.py` — `test_pyright_has_exactly_one_config_home`: tree walk for `pyrightconfig.json` |
| CI-09 | The pin is exact, reaches CI through the lock, and matches the running binary | `tests/test_ci_workflows.py` — `test_analyzer_dev_pins_are_exact_and_match_the_lock`: dev-pin derivation + `uv.lock` resolution equality; `uv run pyright --version` equality (verify-phase runtime evidence) |
| CI-09 | Adopting the gate leaves every existing gate declaration intact | `tests/test_ci_workflows.py` — `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`: YAML/tomllib inspection; `uv run mypy src/ scripts/` exit code (CI-01 gate-exit-code precedent) |

---

## MODIFIED Requirements

### Requirement: Dev interpreter pin matches the gate interpreter (CI-07)

> Added by change `2026-09-14-chore-python-version-313` (GitHub #178). Every scenario below is evidenced by
> verify-phase static or runtime gate evidence rather than by a pytest assertion — the framing this
> capability's own Test Mapping already uses for gate exit codes.
>
> Modified by `2026-09-15-chore-type-gate-policy` (GitHub #201) — the `[tool.mypy] python_version` declaration
> moved to `"3.11"` by maintainer decision; the `.python-version` pin, its equality with both gate-job pins, and
> every other clause are unchanged.

**Modification scope (DC-11 / COR-4 — the single authorized exception to this change's CI-01..CI-08
non-goal).** Exactly four spans of CI-07 move, and nothing else in that requirement does:

| Span | Operation |
| --- | --- |
| the `[tool.mypy] python_version` clause inside the requirement's third paragraph | replaced in place |
| the first THEN bullet of the `User-facing support is unchanged` scenario | replaced |
| a `(Previously: …)` marker paragraph | appended immediately after the third paragraph |
| the `> Modified by …` blockquote line | appended to the existing `> Added by …` blockquote line |

The reason is recorded, not implicit: the canonical clause required the retired value while the committed
`pyproject.toml` declares `"3.11"` (maintainer decision, BL §8.5 #1), so leaving it would ship a requirement
that is false on the tree — the documented-contract-is-false failure mode this change exists to remove. Guard
`G7` (`test_ci07_names_the_declared_mypy_language_level`) enforces the agreement from here on: it derives the
value from `[tool.mypy] python_version` and asserts CI-07 names it, so config and canonical clause cannot
diverge silently again.

**Occurrence 1 — the `python_version` clause inside CI-07's third paragraph.** The paragraph begins "This
requirement SHALL NOT change user-facing Python support:". The frozen sentence below replaces exactly the
stale clause — the one requiring `[tool.mypy] python_version` to remain at the retired `3.10` value and
describing it as the minimum language/typing level tied to `requires-python` — at that same position; every
other byte of the paragraph (including the bytes before the clause and the bytes after it, up to and
including the closing clause about zero `pyproject.toml` / zero `.github/workflows/` diff paths) is copied
verbatim:

```text
`[tool.mypy] python_version` SHALL be `"3.11"` — the language level mypy analyses against, declared
independently of both `requires-python` (`>=3.10`, the support floor) and `.python-version` (`3.13`, the gate
interpreter). At `3.11` the `import tomllib as _tomli` arm of the interpreter-selection fallbacks is
a resolvable stdlib module for mypy, while the marker-only `tomli` arm is covered by the global
`ignore_missing_imports = true`. It SHALL NOT be read as a support declaration: `requires-python` SHALL remain
`>=3.10`. A change that moves this value SHALL amend this clause in the same change.
```

**Occurrence 1b — the appended `(Previously: …)` marker.** Inserted as a new paragraph immediately after
CI-07's third paragraph, using the repository's marker convention (`openspec/specs/cli/spec.md:209`,
`parquet-conversion/spec.md:529`, `tool-config/spec.md:324`). The retired value is written as inline code, the
way this repository's other `(Previously: …)` markers write retired values, so the file-wide absence check on
the retired double-quoted value stays exact (COR-5):

```text
(Previously: this clause required `[tool.mypy] python_version` to remain `3.10` and described it as the
minimum language level tied to `requires-python`; the maintainer declared `"3.11"` as the analysis level and
change `2026-09-15-chore-type-gate-policy` (GitHub #201) amends the clause to match the committed
configuration.)
```

**Occurrence 2 — the same clause restated in CI-07's `User-facing support is unchanged` scenario.** That
scenario's first THEN bullet repeats the clause, so amending only the paragraph would leave CI-07
self-contradictory. The bullet is replaced as a whole (in the canonical file it is wrapped over two lines):

```text
- THEN `requires-python` SHALL still be `>=3.10` and `[tool.mypy] python_version`
  SHALL be `"3.11"` — the declared analysis level, amended by change
  `2026-09-15-chore-type-gate-policy` (GitHub #201) to match the committed configuration
```

**Deliberately untouched inside CI-07 (byte-identical; `G7` reads none of them):** the `.python-version` =
`3.13` clause and its equality with both gate-job pins; the "flag-free mypy gates are green on the pinned
interpreter" paragraph (including its `[no-redef]` requirements); the COV-06-script paragraph; the AGENTS
rule 12 latent-issue paragraph; the four other scenario bullets (dev pin = both job pins; flag-free mypy
gates; COV-06 script; latent-issue note); and the fifth scenario's remaining bullets (`requires-python`,
matrix, floor, diff scope).

**Evidence class unchanged.** CI-07's Test Mapping row (`| CI-07 | User-facing support is unchanged |
Verify-phase static evidence — diff and config inspection … |`) stays byte-identical and is **re-satisfied**
by a static read of the committed config against the amended clause. No new CI-07 row is added.

---

## Cross-referenced and deliberately untouched

- `ci` CI-01 — the config-owned TOTAL floor stays exactly where it is (`[tool.coverage.report]`
  `fail_under = 90`, next to `show_missing = true`). CI-09 declares no threshold, adds no config key and arms
  no coverage invocation.
- `ci` CI-02, CI-03 — the artifact/log evidence contract and the release `needs` graph are unchanged; CI-09
  asserts the `needs` graph is untouched (S5) and edits neither workflow's coverage job.
- `ci` CI-04, CI-05 — CodeQL cadence and config: untouched; CI-09 adds no CodeQL surface.
- `ci` CI-06 — the documentation-truth requirement is untouched; CI-09's own S1 adds a **new** assertion about
  `CONTRIBUTING.md`'s type-checking section and the PR template, which is a CI-09 clause, not a change to
  CI-06's four asserted surfaces.
- `ci` CI-08 — single authoritative ruff version: cited as the pin-authority precedent (the single-config-
  home rule of CI-09 S3 and the no-workflow-literal rule mirror it). Its clauses, scenarios, rows and its
  trio guard stay byte-identical.
- `ci` `## Purpose` — left stale deliberately (it enumerates CI-01..CI-06 only). Adding CI-07 and CI-08 left
  it unchanged; this change does the same.
- `ci` CI-07's "zero `pyproject.toml` paths / zero `.github/workflows/` paths" clause — **not amended** by this
  change. It was written and verified as the evidence for the change that moved `.python-version` to `3.13`
  (where nothing else moved), and it is not read here as a standing ban on ever touching `pyproject.toml` or
  `.github/workflows/` — CI-09 itself requires a `ci.yml` lint step and a `[tool.pyright]` block. The clause's
  bytes stay identical; this reading is recorded so the tension is visible rather than latent.
- `process-boundary` PB-07 — "new test helpers SHALL be type-annotated even though mypy excludes `tests/`".
  Cross-referenced by CI-09 S1 and explicitly **not** relaxed: neither gate analyses `tests/`, and the
  annotation-by-convention rule stays in force. No byte of PB-07 changes.
- `process-boundary` PB-14 — hook scope/ownership. CI-09 adds a `pyright` hook entry locally and, unlike
  CI-08, arms one CI `lint` step; PB-14's hook-ownership clauses are cited, never modified.
- `packaging` PKG-06 — the `uv.lock` regeneration class, scoped to its own declaration. CI-09's pin/lock
  equality obligation is stated here (S4) and does not edit PKG-06.
- Issues **#187** (`CONTRIBUTING.md` names a nonexistent `ruff.toml`), **#212** (documented commands narrower
  than CI), **#194** (no `format --check` CI gate), **#215** (un-gated per-file floors) — each keeps its own
  owner. CI-09 touches `CONTRIBUTING.md`'s type-checking section and one command-list line only; the
  `ruff.toml` sentence and the `mypy src/` path text stay for their owners.
- `openspec/project.md` and `openspec/config.yaml` — untouched; no requirement here needs either.

**Non-goals recorded by this delta:** no `tests/` in either type gate; no coverage change of any kind (no
floor movement, no `# pragma: no cover` anywhere, no `scripts/check_core_coverage.sh` or `fail_under` edit);
no dependency added beyond the analyzer dev pins already declared (no `tomli`, no `basedpyright`, no analyzer
substitution) and no `python_version` / `ignore_missing_imports` change; no mypy `strict` reversion or
further tightening; no `pyright strict` campaign; no `pyrightconfig.json`; no version literal in any
workflow; no CI test-matrix or `release.yml` change; no edit to CI-01..CI-06, CI-08, PB-07, PB-14, the
`## Purpose` enumeration, `openspec/project.md` or `openspec/config.yaml` — and to CI-07 only the four spans
frozen above, nothing else in that requirement; no absorption of #187, #212, #194, #215 or the CI-07
diff-scope reading; no canonical `openspec/specs/**` edit before `sdd-sync`; no commit, push or PR.
