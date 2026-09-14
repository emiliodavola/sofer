# Delta for ci

> **Change:** `2026-09-14-chore-python-version-313` (GitHub #178) · branch
> `chore/178-python-version-313`. Artifact store **hybrid**: this file plus an Engram
> mirror under topic key `sdd/2026-09-14-chore-python-version-313/spec`.
>
> **This artifact supersedes the proposal's capability claim.** `proposal.md` §
> `## Capabilities` records "New Capabilities: None / Modified Capabilities: None … no
> delta file is created", and Decision Point 4 records "Does this change need a spec
> delta? **No**" together with an explicit minimal fallback: "a `ci` CI-06-adjacent
> MODIFIED clause recording that the dev pin mirrors the CI gate interpreter —
> explicitly NOT proposed here". The native SDD status provider (Gentle AI v2.9.0)
> reports `specs: blocked` for this change and keeps `apply` blocked until a `specs`
> artifact exists, so **the proposal's fallback is adopted here instead of its stated
> "no delta" position**. Everything else the proposal records stands unchanged: the
> scope is still `.python-version` (one line) + the `AGENTS.md` rule-12 note, no
> runtime/CLI/packaging behaviour changes, and no test is added. `tasks.md` is not
> modified by this phase.
>
> **Capability choice — `ci`, and no second capability.** The invariant is an
> agreement between the *local development interpreter selection* and the interpreter
> that runs the *gate-bearing CI jobs*: `ci` CI-02 already pins the coverage job to
> Python 3.13, `ci` CI-01 owns the config-declared TOTAL gate those jobs enforce, and
> `ci` CI-06 owns the "declared config and documentation truth that keeps the gate
> enforced and discoverable" — the same shape as the contributor note this change
> corrects. The alternative home, `coverage` COV-06, was considered and rejected **as
> a modification target**: COV-06's gate machinery, four-module 100.00% mandate,
> pragma ban and `scripts/check_core_coverage.sh` shape are all untouched, and no COV
> requirement text changes — the change only makes COV-06's *local* satisfiability
> possible. `coverage` is therefore cross-referenced, not modified.
>
> **Additive, not destructive.** `## ADDED Requirements` is used because **no existing
> `ci` requirement text changes**: CI-01..CI-06 each keep their canonical clauses and
> scenarios byte-for-byte, so archive-time replacement of a canonical requirement
> block would be a lossy no-op. CI-06's four asserted documentation surfaces
> (`openspec/config.yaml`, `CONTRIBUTING.md`, README/README_ES, PR template) are all
> untouched by this change, and its implementing tests
> (`test_ci_workflows.py::test_contributing_documents_coverage_floor`) stay green by
> construction — so the `AGENTS.md` contributor note is modelled as a **new**
> requirement (CI-07, the next free ID in this capability) rather than as an in-place
> rewrite of CI-06's surface list.
>
> **Rule-6 resolution — see the dedicated section before the Test Mapping.** No
> scenario in this delta is left unmapped, and no vacuous test is invented.
>
> Domain hygiene checks performed for this phase: `openspec/specs/ci/spec.md` exists
> and was read before writing (delta, not full spec); no other active change carries
> `specs/ci/` (checked across `openspec/changes/*/specs/**`; only this change
> contributes one); this change has no legacy flat `openspec/changes/<change>/spec.md`
> to reconcile.

## ADDED Requirements

### Requirement: Dev interpreter pin matches the gate interpreter (CI-07)

> Added by change `2026-09-14-chore-python-version-313` (GitHub #178).

The repository's local development interpreter pin — the single-version
`.python-version` file at the repository root, which uv resolves for every documented
`uv run …` invocation — SHALL name the same Python version the gate-bearing CI jobs
run on. `.python-version` SHALL contain exactly `3.13` and SHALL equal both gate pins
declared in `.github/workflows/ci.yml`: the `lint` job's `python-version` (which runs
`uv run mypy src/ scripts/`) and the `coverage` job's `python-version` (which runs the
complete-suite coverage gate plus the four COV-06 per-file scoped gates). The pin
SHALL be the single local source of the gate interpreter, so that a clean checkout
needs **no `--python` flag** to run the gates.

The pin SHALL make the documented, flag-free gate commands satisfiable on a clean
checkout. `uv run mypy src/` and `uv run mypy src/ scripts/` SHALL exit 0 with zero
errors — in particular zero `[no-redef]` errors at the five interpreter-selection
fallback sites (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`,
`model.py`). `uv run coverage run -m pytest` followed by
`bash scripts/check_core_coverage.sh` SHALL exit 0 with each of the four core rows
(`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) at 100.00% and an empty `Missing`
column, and the script SHALL be able to reach its last gate (a first-file failure
aborts it under `set -euo pipefail`, leaving the remaining gates unverified). The
`3.10` pin could satisfy neither gate, because `3.10` installs the conditional `tomli`
backport, which makes one arm of every fallback dead and therefore makes the
four-module 100.00% mandate unsatisfiable by construction rather than by test quality.

`.python-version` selects the interpreter a developer's tools run under; it SHALL NOT
be read as a support declaration. This requirement SHALL NOT change user-facing Python
support: `pyproject.toml` `[project] requires-python` SHALL remain `>=3.10`,
`[tool.mypy] python_version` SHALL remain `"3.10"` (it declares the minimum
language/typing level, tied to `requires-python`, not the developer interpreter), the
CI test matrix SHALL keep exercising `3.10`–`3.14`, the TOTAL coverage floor SHALL
remain the config-owned `fail_under = 90` (`ci` CI-01), and the change's diff SHALL
contain zero `pyproject.toml` paths and zero `.github/workflows/` paths.

`AGENTS.md` rule 12's latent-issue note SHALL be accurate and SHALL record the
consequence for a contributor on an older interpreter. It SHALL name all five fallback
modules (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`),
SHALL quote the real fallback form (`import tomli as _tomli` / `import tomllib as
_tomli`), SHALL record that the pin is `3.13` because a `3.10` development environment
installs the `tomli` backport and thereby makes the local `mypy` and COV-06 gates
unsatisfiable by construction, SHALL keep the existing "do not add mypy to the version
matrix" instruction, and SHALL state that a contributor on an older interpreter must
pass `--python 3.13` explicitly for those two gates. The note SHALL stay where it is
(relocating it is out of scope) and SHALL NOT weaken any other rule-12 bullet.

#### Scenario: Dev pin equals both gate-job pins

- GIVEN `.python-version` at the repository root and `.github/workflows/ci.yml`
- WHEN the pin is read and compared against the `python-version` declared for the
  `lint` job and for the `coverage` job
- THEN `.python-version` SHALL contain exactly `3.13` and no other content
- AND it SHALL equal both job pins, so the local gate interpreter and the CI gate
  interpreter are the same value

#### Scenario: Flag-free mypy gates are green on the pinned interpreter

- GIVEN a clean checkout whose only interpreter selection is `.python-version` (no
  `--python` flag on any command)
- WHEN `uv run mypy src/` and `uv run mypy src/ scripts/` run — the latter being the
  exact entry of the local pre-commit mypy hook
- THEN each SHALL exit 0 with zero errors
- AND in particular no `[no-redef]` error SHALL be reported at any of the five
  interpreter-selection fallback sites, which the `3.10` pin produced

#### Scenario: The COV-06 gate script runs all four scoped gates to completion on the pin

- GIVEN a clean checkout whose only interpreter selection is `.python-version`
- WHEN `uv run coverage run -m pytest` runs and is followed by
  `bash scripts/check_core_coverage.sh`
- THEN the script SHALL exit 0
- AND each of the four core rows SHALL be 100.00% with an empty `Missing` column
- AND the script SHALL NOT abort before its last gate has run, so all four scoped
  gates are verified in the same pass (the pin that made the first row fail left the
  remaining three unverified)

#### Scenario: The latent-issue note states the rationale and the escape hatch

- GIVEN `AGENTS.md` rule 12's latent-issue note
- WHEN the note is read
- THEN it SHALL name all five fallback modules and quote the real fallback form
  (`import tomli as _tomli` / `import tomllib as _tomli`)
- AND it SHALL record that the pin is `3.13` because a `3.10` development environment
  installs the `tomli` backport and makes the local `mypy` and COV-06 gates
  unsatisfiable by construction
- AND it SHALL keep the "do not add mypy to the version matrix" instruction
- AND it SHALL state that a contributor on an older interpreter must pass
  `--python 3.13` explicitly for those two gates

#### Scenario: User-facing support is unchanged

- GIVEN `pyproject.toml`, `.github/workflows/ci.yml`, and this change's diff
- WHEN the support declarations, the coverage floor, and the diff are inspected
- THEN `requires-python` SHALL still be `>=3.10` and `[tool.mypy] python_version`
  SHALL still be `"3.10"`
- AND the CI test matrix SHALL still exercise `3.10`, `3.11`, `3.12`, `3.13`, and
  `3.14`
- AND the TOTAL coverage floor SHALL still be the config-owned `fail_under = 90`
  (`ci` CI-01), with no threshold added or re-declared
- AND the diff SHALL contain zero `pyproject.toml` paths and zero
  `.github/workflows/` paths

---

## Rule-6 resolution: mapped to verify-phase evidence, with no test invented

`openspec/config.yaml` (`rules.specs`) and AGENTS.md rule 6 require every spec scenario
to have a corresponding test. This change deliberately adds no test (proposal Decision
Point 1 / tasks "Deliberate decisions"), so the mapping is stated here explicitly and
each of the five scenarios above is mapped to concrete, already-planned evidence — no
scenario was written that cannot be evidenced at all.

1. **The precedent is the repo's own.** Both this capability's canonical spec and the
   `coverage` canonical spec already resolve rule 6 as "a green test **or** to
   verify-phase static/runtime evidence". `ci` CI-01's "Gate is config-driven" scenario
   is mapped partly to "local gate run — `uv run coverage report -m` exit code
   (verify-phase runtime evidence)", and `ci` CI-03's release scenario is mapped wholly
   to "Verify-phase static evidence". The `coverage` Test Mapping records that "actual
   measured percentages are NOT pytest-assertable" and that the COV-06 100.00% rows are
   "enforced by the per-file gate invocations' exit codes in CI — runtime gate
   evidence, same precedent". Gate exit codes and measured rows therefore already live
   in this repo's evidence category, not in pytest.
2. **Scenarios 1–3 are command-evidence shaped.** "The pin equals the gate pins",
   "`mypy src/` exits 0", and "all four COV-06 rows are at 100.00% with an empty
   `Missing` column" are facts about *executed gates*. A pytest assertion cannot
   produce them without spawning `mypy`/`coverage` from the suite — i.e. building a
   second gate inside the test suite, which is neither the intent nor in scope.
3. **Scenarios 4–5 are statically assertable, and are nevertheless mapped to static
   verify-phase evidence by decision, not by omission.** A drift guard (a text
   inspection in `tests/test_ci_workflows.py` asserting `.python-version` equals the
   lint/coverage pins, and that the rule-12 note carries its five required elements)
   would be admissible under that module's declared 1:1 pytest-function↔spec-scenario
   contract now that CI-07 exists. It was considered and rejected in the proposal
   (Decision Point 1): it cannot prove the invariant's point (that the gates are
   green), and recurrence prevention is owned by issue **#192**, which removes the
   interpreter↔fallback coupling instead of freezing it in a test. **Accepted cost,
   stated plainly:** a future local revert of `.python-version` to `3.10` would go
   uncaught by pytest; CI's `3.13`-pinned `lint` and `coverage` jobs remain the
   authoritative gates.
4. **Nothing existing is disturbed.** CI-06's four scenarios keep their implementing
   tests unchanged: `CONTRIBUTING.md` is untouched, and the rule-12 note edit sits
   outside the rule-14 regex extracted by
   `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate`. That
   regression check is part of the change's evidence set (V8), not a new CI-07 test.

---

## Cross-referenced and deliberately untouched

| Canonical text | Treatment | Why |
| --- | --- | --- |
| `ci` CI-01 (config-owned `fail_under = 90`; flag ban) | Not modified | `pyproject.toml` has zero diff lines; the TOTAL gate and its flag ban are unchanged |
| `ci` CI-02 (coverage job on Python 3.13) | Not modified | The job pins are the reference the dev pin now mirrors; not one workflow line changes |
| `ci` CI-06 (documentation truth, four asserted surfaces) | Not modified | All four surfaces (`openspec/config.yaml`, `CONTRIBUTING.md`, README/README_ES, PR template) are untouched; the corrected `AGENTS.md` contributor note is a new requirement (CI-07), not a change to CI-06's asserted surface list |
| `coverage` COV-01 / COV-02 (floors, CI interpreter as arbiter) | Not modified | The change makes the local reproduction of these floors possible; it moves no floor and no measurement |
| `coverage` COV-06 (four-module 100.00% mandate, scoped gates, pragma ban) | Not modified | The gate script, the mandate, and the pragma ban are untouched; COV-06's local satisfiability is the *effect* of CI-07, not a change to it |

---

<!-- Informational only: maps each scenario to its evidence (AGENTS.md rule 6 /
openspec/config.yaml — every spec scenario MUST have a corresponding test or, per this
repo's ci/coverage Test Mapping precedent, verify-phase static/runtime evidence).
Not part of the archived requirement blocks. -->

| Req | Scenario | Evidence | Kind |
| --- | -------- | -------- | ---- |
| CI-07 | Dev pin equals both gate-job pins | V1 — read `.python-version` against `ci.yml` lint/coverage `python-version` values | Verify-phase static evidence (proposal V1) |
| CI-07 | Flag-free mypy gates are green on the pinned interpreter | V2 — `uv run mypy src/` exit 0 with zero `[no-redef]`; V3 — `uv run mypy src/ scripts/` exit 0 | Verify-phase runtime evidence — gate exit codes (CI-01-S2 precedent) |
| CI-07 | The COV-06 gate script runs all four scoped gates to completion on the pin | V4 — `uv run coverage run -m pytest` then `bash scripts/check_core_coverage.sh`: exit 0, four 100.00% rows, empty `Missing`, every gate reached | Verify-phase runtime evidence — gate exit codes (COV-06 precedent) |
| CI-07 | The latent-issue note states the rationale and the escape hatch | V7 — read `AGENTS.md` rule 12 and mark each of the five required elements present | Verify-phase static evidence (rule-6 resolution point 3) |
| CI-07 | User-facing support is unchanged | V6 — `git diff --stat` / `git diff` show zero `pyproject.toml` and zero `.github/workflows/` paths, `fail_under = 90` intact, no pragma introduced; `requires-python`, `[tool.mypy] python_version`, and the 3.10–3.14 matrix read unchanged | Verify-phase static evidence |

Suite-protection evidence that is **not** a CI-07 scenario (it guards behaviour this
requirement must not disturb): V5 — full suite executed after the bump with the
`tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version`
observation explicitly reported (pass → closed as environment artifact; fail →
escalated, never absorbed); V8 —
`uv run pytest tests/test_ci_workflows.py -q` green, proving CI-06's static contracts
survive the rule-12 edit and the pin change.
