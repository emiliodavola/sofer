# Design: chore-python-version-313 (issue #178)

**Status**: complete
**Change**: `2026-09-14-chore-python-version-313`
**Branch**: `chore/178-python-version-313` (`.git/HEAD` reads `ref: refs/heads/chore/178-python-version-313`)
**Phase**: design — after proposal + `ci` spec delta (CI-07). Strict-TDD off (`strict_tdd: false`); there is no test to write (see §8).
**Store**: hybrid — this file plus an Engram mirror under `sdd/2026-09-14-chore-python-version-313/design`.

Read for this design: `proposal.md` (Approach, Decision Points, Verification Approach V1–V8, Risks,
Rollback), `specs/ci/spec.md` (CI-07, five scenarios), `tasks.md`, `AGENTS.md` rules 12/14,
`pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
`.pre-commit-config.yaml`, `scripts/check_core_coverage.sh`, and one archived design for house shape.

---

## 1. What this design decides

**Almost nothing — and saying so is the design.** This change has no architectural surface: it moves
one line of developer-environment configuration and corrects one documentation note. The approach,
the decision points, the rollback and the evidence set were all settled in the proposal and are not
re-opened here. What a reviewer needs from this artifact is the part a proposal does not carry: the
**precise relationship between the three interpreter intercepts**, the **mechanism argument** for why
the pin rather than the code is the fix, the **alternatives and their dispositions**, the **blast
radius**, and the **honest boundary of what is proven versus inferred**.

Everything below is a record. There is exactly one thing the design affirms positively as an
architectural statement: **no new module, no interface change, no data-flow change, no dependency
change, and no workflow change are required to satisfy CI-07** (§6, §7).

## 2. D1 — The three interpreter intercepts, stated precisely

Reviewers conflate these three settings; they are independent and each is left untouched except the
first.

| # | Intercept | Site | Current value | What it selects | This change |
| --- | --- | --- | --- | --- | --- |
| I1 | `.python-version` | repo root (1 line) | `3.10` → **`3.13`** | The interpreter a **developer's tools run under** — uv resolves it for every documented `uv run …` | **Only edit.** Set to `3.13` |
| I2 | `[tool.mypy] python_version` | `pyproject.toml:74` | `"3.10"` | The **minimum language / typing level the code is checked against**; tracks `requires-python`, not the dev interpreter | **Unchanged, deliberately** |
| I3 | `[project] requires-python` | `pyproject.toml:6` | `">=3.10"` | The **user-facing install contract** (declares support; drives the `tomli` marker at `:27` and the 3.10–3.14 classifier list) | **Unchanged, deliberately** |

`[tool.ruff] target-version = "py310"` (`pyproject.toml:58`) is a fourth member of I2's class — a
*minimum target*, not an interpreter selection — and it also stays unchanged; it is named here only so
the "which settings are interpreter-selecting?" question has one complete answer.

**The independence evidence, and why it forbids touching I2.** The measured green 3.13 run
(`mypy src/` → `Success: no issues found in 32 source files`, exit 0) was obtained with **I2 unchanged
at `"3.10"`**. That is direct evidence that I1 and I2 are independent: changing which interpreter
*executes* mypy does not require changing which language level mypy *checks against*. It is therefore
also the reason I2 must not be touched by this change — the green result was not produced by editing
I2, so editing I2 would be an unmeasured change riding along on a measured one (proposal R4; CI-07's
"zero `pyproject.toml` paths" clause).

The coherent reading of the change in one sentence: **I1 moves to where the gates run, I2 stays where
the support contract is, I3 stays where the users are.**

## 3. D2 — Why the mechanism is the pin and not the code

The defect is not the pin's *value* in isolation and not the fallbacks' *quality*; it is the
interaction of the pin with a five-fold duplication.

The repo contains five structurally identical interpreter-selection fallbacks (re-verified read-only
this phase):

| # | Site | Code |
| --- | --- | --- |
| 1 | `src/sofer/cli.py:438-440` | `try: import tomli as _tomli` / `except ImportError:` / `import tomllib as _tomli` |
| 2 | `src/sofer/config.py:151-153` | same pair (`except ImportError:  # Python ≥ 3.11`) |
| 3 | `src/sofer/mcp_registration.py:128-130` | same pair |
| 4 | `src/sofer/mcp_server.py:687-689` | same pair (`# Python >= 3.11`) |
| 5 | `src/sofer/model.py:397-399` | same pair (`# Python ≥ 3.11`) |

Because I3's marker installs `tomli` only when `python_version < '3.11'`, **exactly one arm of every
fallback is dead per interpreter** — and *which* arm is dead is decided by I1, not by the code:

- **At the `3.10` pin**: `tomli` *is* installed → the `try` arm succeeds → the `except` arm never
  executes. In `cli.py` that makes `src/sofer/cli.py:439-440` unreachable from any test, so the
  `coverage` COV-06 gate for `cli.py` (`--fail-under=100`) is **unsatisfiable by construction, not by
  test-quality shortfall**. Two consequences follow, and both are worse than a red gate:
  1. `mypy` reports five `[no-redef]` errors at the second import of the same name
     (`cli.py:440`, `config.py:153`, `mcp_registration.py:130`, `mcp_server.py:689`, `model.py:399`) —
     so the local pre-commit hook (`.pre-commit-config.yaml:11-16`, `entry: uv run mypy src/ scripts/`)
     fails on **every** commit, pushing contributors toward `--no-verify`, which AGENTS.md rule 5 forbids.
  2. `scripts/check_core_coverage.sh` runs under `set -euo pipefail`, so the `cli.py` failure aborts the
     script before `scanner.py` / `prepare.py` / `publish.py` — **three of the four COV-06 gates are left
     unverified**, not merely red.
- **At `3.13`**: the backport is absent, the `except` arm executes, both gates are green.

**The pragma is not an exit.** AGENTS.md rule 14 forbids `# pragma: no cover` in the four core modules
with no exception clause. So the dead-arm problem cannot be silenced; it must be made *executable* or
the mandate must change. **Recorded consequence: the `3.10` pin and the COV-06 mandate are mutually
exclusive as currently written.** One of the two has to give, and the maintainer's confirmed decision
is that the dev-environment pin gives (the mandate and the pin↔fallback coupling are addressed by the
structural follow-up, #192).

## 4. D3 — Alternatives considered and rejected

| # | Alternative | Why it was rejected | Disposition |
| --- | --- | --- | --- |
| A | **Structural fix**: make `tomli` unconditional and collapse the five fallbacks into one helper | A multi-module refactor that changes a **runtime dependency** (unconditional backport, or dropping the marker) and rewires five call sites' import path — it deserves its own proposal, its own spec delta and its own review, not a rider on a one-line dev-env pin | **Tracked as issue #192.** It is also where recurrence prevention lives, since it removes the coupling instead of freezing it |
| B | **Drop Python 3.10**: `requires-python = ">=3.11"` + stdlib `tomllib` (fallbacks collapse for free) | A **user-facing breaking change** while 3.10 still has upstream security support. It also violates the confirmed scope refusal to reduce support, and would force a `packaging`/`ci` matrix change | Rejected. `requires-python` stays `>=3.10`; the 3.10–3.14 matrix untouched (CI-07 "User-facing support is unchanged") |
| C | **Keep the `3.10` pin, document the workaround**: leave everything, tell contributors to run the two gates as `uv run --python 3.13 mypy src/` | The **default commands and the pre-commit hook would stay red**. The hook entry is `uv run mypy src/ scripts/` with `pass_filenames: false` and no `--python` flag; making it flag-driven means editing the hook, i.e. a scope increase for a worse state (a repository whose documented gates require an unwritten flag) | Rejected as the mechanism. The `--python 3.13` escape hatch survives **only as documentation for a contributor on an older interpreter** (AGENTS.md rule-12 note, CI-07 scenario 4 / V7) — never as the way the repo's own gates are run |
| D | **Static drift guard test**: assert `.python-version` equals the CI lint/coverage `python-version`, and/or that the rule-12 note carries its five elements | **Vacuous as proof**: it cannot show the gates are green, which is the entire point of the invariant. It also lands in `tests/test_ci_workflows.py`, whose self-declared contract maps pytest functions 1:1 to spec scenarios, so admitting it would require a further spec artifact — **scope creep into the `ci` domain for a one-line pin** | Rejected (proposal Decision Point 1). **Accepted cost, stated plainly:** a future local revert of `.python-version` to `3.10` goes uncaught by pytest. CI's `3.13`-pinned `lint`/`coverage` jobs remain the authoritative gates, and #192 removes the failure mode itself |

Note how the CI-07 delta and this table interlock: CI-07 exists (the `specs` phase adopted the
proposal's own stated fallback because the native provider keeps `apply` blocked without it), but
**the existence of CI-07 does not resurrect alternative D** — the delta resolves rule 6 to
verify-phase evidence, explicitly *not* to a new test. The design confirms that reading is correct and
that nothing in CI-07 requires a test to be invented.

## 5. D4 — Blast radius, and the honest boundary of the CI argument

**Blast radius — three files, one of them this artifact.** The production diff is `.python-version`
(1 line) plus the `AGENTS.md:90` rule-12 bullet (~2–10 lines). Nothing else in the repository changes
meaning:

| Surface | Effect of the pin change |
| --- | --- |
| Users installing the wheel | **None.** `.python-version` is shipped in the sdist but **not** in the wheel; the wheel declares `Requires-Python: >=3.10` and `Requires-Dist: tomli>=2.0; python_version < '3.11'`, and the installed 32-module package contains zero references to the pin. A clean `3.10.20` install of the built wheel runs `sofer --version` / `--help` successfully with `tomli` resolved by the marker |
| `requires-python`, classifiers, the matrix | **None.** I3 and the 3.10–3.14 matrix are untouched |
| `[tool.mypy] python_version`, ruff `target-version` | **None** (§2) |
| `src/sofer/**` | **Zero paths.** All five fallbacks stay byte-identical |
| `pyproject.toml`, coverage config | **Zero diff lines.** `fail_under = 90` intact |
| `CONTRIBUTING.md` | **Zero diff lines** — every documented command is `uv run …` and pin-agnostic, so no command string becomes wrong; the file's coverage wording is pinned by CI-06 S2 and stays green by construction |
| `.pre-commit-config.yaml` | **Untouched.** The mypy hook starts passing because I1 changed, not because the hook changed |
| `scripts/check_core_coverage.sh` | **Untouched.** It has no `--python` flag by design and follows the pin — which is exactly why the pin had to move |
| `.github/workflows/**` | **Untouched** (below) |

**CI non-regression argument.** No workflow file is edited, and the pin cannot leak into the jobs:

1. Each gate-bearing job declares its own interpreter through `astral-sh/setup-uv`'s `python-version`
   input — `ci.yml:15` (lint) and `ci.yml:61` (coverage), plus `release.yml:23/:63/:103` — which
   selects the job interpreter and exports `UV_PYTHON` to the job's steps.
2. The test matrix (`ci.yml:28/:36`) sets the same input per leg (`3.10`–`3.14`); matrix legs run only
   `uv run pytest -v` and `uv run sofer --help`, which are pin-agnostic anyway.
3. `AGENTS.md` rule 12 already records that the workflow runs mypy **only** under 3.13, mirroring CI —
   the same statement from the repo's own side.
4. **Empirical support:** the `lint` and `coverage` jobs are green *today* on a tree whose
   `.python-version` says `3.10`. If the job input did not win over the repo pin, mypy would be
   failing in CI for the same five `[no-redef]` errors it fails with locally — it is not.

**What is *not* proven, stated honestly.** The precedence in (1) is **inferred**, not reproduced:
a local `uv python find` probe did not honour `UV_PYTHON`, so the CI-side precedence was not
reproducible on a developer machine in this phase (it was not re-run here). The inference rests on
(4) — a green lint job under a 3.10 pin can only mean the job's own selection wins. **The confirming
experiment is the PR's own CI run:** if the pin did collapse the jobs, the `lint` job's
`uv run mypy src/ scripts/` step and the coverage job's `check_core_coverage.sh` step would fail on
this PR. That is a free, mandatory observation at verify time, and it is the reason no workflow change
is needed to "protect" the jobs.

## 6. Files, interfaces, data flow — all unchanged

| Question | Answer |
| --- | --- |
| New modules? | **No.** Zero `src/sofer/` paths |
| Interface / contract changes? | **No.** No CLI flag, no function signature, no MCP surface, no config schema |
| Data-flow changes? | **No.** The five fallbacks keep their exact resolution order; only *which arm is live* changes, and that is decided by the interpreter, not by the code |
| Dependency changes? | **No.** `tomli>=2.0; python_version < '3.11'` stays; under 3.13 uv simply does not install it for the dev environment, which is the mechanism (§3) |
| Workflow / CI changes? | **No.** See §5 |
| Migration, on-disk artifacts, published surface? | **No.** No migration, nothing published, no network, no destructive operation |
| Est. production delta | `.python-version` 1 line; `AGENTS.md` ~2–10 lines. Well under the 400-line budget → single PR, no chaining, no `size:exception` |

## 7. Consistency with the `ci` spec delta (CI-07)

The delta adds **CI-07** (`## ADDED Requirements`) and modifies nothing canonical — CI-01..CI-06 keep
their clauses byte-for-byte, and the `coverage` requirements are cross-referenced, not modified. This
design is consistent with that and adds no requirement of its own. Mapping, so the reviewer can check
the delta is fully covered by design + evidence:

| CI-07 scenario | Design anchor | Evidence |
| --- | --- | --- |
| Dev pin equals both gate-job pins | §2 (I1), §5 (1) | V1 |
| Flag-free mypy gates are green on the pinned interpreter | §2 (independence evidence), §3 | V2, V3 |
| The COV-06 gate script runs all four scoped gates to completion on the pin | §3 (`set -euo pipefail` abort) | V4 |
| The latent-issue note states the rationale and the escape hatch | §4 (alternative C's disposition) | V7 |
| User-facing support is unchanged | §2 (I2/I3 stay), §5 (blast radius) | V6 |

The delta's "no test invented, mapped to verify-phase evidence" resolution is confirmed as correct in
§4 (alternative D) and §8.

## 8. Verification approach and the apply/verify split

Verification is **command evidence**, not pytest assertions — consistent with the repo's own precedent
(`ci` CI-01's config-driven scenario is partly mapped to a local gate-run exit code; the `coverage` Test
Mapping records that measured percentages are not pytest-assertable and that the COV-06 rows are
enforced by per-file gate exit codes). The evidence set is the proposal's V1–V8 verbatim; the parent
split it across the two remaining phases as follows, and this design adopts that split:

| Row | Evidence | Phase |
| --- | --- | --- |
| V1 | `.python-version` reads exactly `3.13` and equals `ci.yml:15` / `:61` | **apply** |
| V2 | `uv run mypy src/` → exit 0, zero errors (the five `[no-redef]` errors gone) | **apply** |
| V3 | `uv run mypy src/ scripts/` (the exact pre-commit hook `entry:`) → exit 0 | **apply** |
| V4 | `uv run coverage run -m pytest` + `bash scripts/check_core_coverage.sh` → exit 0, four 100.00% rows, empty `Missing`, all four gates reached | **verify** |
| V5 | `uv run pytest tests/ -q` full suite executed, result recorded verbatim, with an explicit verdict on `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` | **verify** |
| V6 | `git diff --stat` shows exactly the two files; `git diff -- src/ pyproject.toml .github/ README.md README_ES.md CONTRIBUTING.md` empty; `fail_under = 90` intact; no pragma introduced | **apply** |
| V7 | `AGENTS.md` rule 12 names five modules, the real `_tomli` fallback form, the 3.13 rationale, the kept "do not add mypy to the version matrix", and the `--python 3.13` escape hatch | **apply** |
| V8 | `uv run pytest tests/test_ci_workflows.py -q` green (rule-14 regex and CI-06 S2 unaffected) | **apply** |

**Why the split is coherent:** apply is where the two edits land and where the *cheap, deterministic*
gates can be proven in the same sitting as the edit (V1, V2, V3, V6, V7, V8). V4 and V5 are the
expensive pair — a coverage-instrumented full-suite run plus a second full-suite run — and V5 carries
the one genuinely open finding of this change, so both belong to verify, where a failing or unresolved
result has a place to be recorded and escalated rather than absorbed.

**V5 is a real obligation, not a formality.** The isolated 3.13 measurement reported
`1 failed, 1765 passed, 6 skipped`, the failure being
`tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version`, cause unpinned. The
leading hypothesis (stale build/editable-install metadata — `_version.py` resolves the version solely
from `importlib.metadata.version("sofer")`; the isolated environment reported `0.3.12.dev57+g059ffc637`,
which is not an ancestor of HEAD, and zero git tags are reachable from `dev`; CI's 3.13 leg is green) is
**to be confirmed by the run, not assumed**. Disposition, restated as a design constraint: if it
reproduces after a clean `uv sync`/rebuild, it is escalated as its own finding — it is **never**
absorbed into this change, and the test is **never** weakened, skipped or xfailed to make the tally
look clean.

## 9. Rollback

Single-commit revert. The production diff is one line in `.python-version` plus the rule-12 note; the
revert restores `3.10` and the prior note text exactly. Nothing destructive, publishing, networked or
user-facing is touched, so a revert cannot affect an installed distribution, CLI behaviour, or the
support declaration — the wheel/sdist contract (`Requires-Python: >=3.10`,
`tomli>=2.0; python_version < '3.11'`) is untouched in both directions. A reverted tree returns to the
red local gates, which is issue #178 re-opened, not a new defect. Per-work-unit rollbacks are the
`git checkout -- <file>` restores already listed in `tasks.md`.

## 10. Open questions

**None blocking.** The four proposal assumptions (Q1 pin + documentation as the first slice with
recurrence prevention deferred to #192; Q2 no CONTRIBUTING.md edit; Q3 an uncaught local revert
accepted with CI as the authoritative gate; Q4 escalate rather than absorb the `test_packaging.py`
observation) are all consistent with §3–§5 and §8 and are adopted here unchanged. **What the design
does not decide** (and must not be read as implicitly approving): no `[tool.mypy] python_version` or
ruff `target-version` change, no `requires-python` change, no workflow change, no `src/sofer/` change,
no pragma, no new test, no spec-delta beyond the already-written CI-07, no relocation of the rule-12
note, and no reformat of the drifted test files (#177) or stale-count fixes (#162/#184).

---

## Output contract

- **status**: complete
- **executive_summary**: The change has no architectural surface — one dev-environment pin line
  (`.python-version` `3.10` → `3.13`) plus a correction to the AGENTS.md rule-12 note — so this design's
  value is in what it records rather than decides. It fixes the three-intercept relationship
  (`.python-version` selects the developer's tool interpreter; `[tool.mypy] python_version = "3.10"`
  and `requires-python = ">=3.10"` are minimum-level and support declarations that stay put — the
  measured green 3.13 run was obtained with `python_version` unchanged, which is the evidence the two
  are independent and the reason it must not be touched); the mechanism argument (five identical
  `tomli`/`tomllib` fallbacks make exactly one arm dead per interpreter, so at the `3.10` pin
  `cli.py:439-440` is unreachable and COV-06's `--fail-under=100` is unsatisfiable by construction —
  with `# pragma: no cover` forbidden by AGENTS.md rule 14, so the pin and the COV-06 mandate are
  mutually exclusive as written and one must give); the four rejected alternatives with dispositions
  (structural fix → issue #192; drop 3.10 → user-facing breaking change; keep 3.10 + document the
  `--python 3.13` workaround → leaves the defaults and the hook red; static drift guard → vacuous as
  proof and `ci`-domain scope creep); the blast radius with the CI non-regression argument (no workflow
  edit; per-job `setup-uv` interpreter selection wins over the repo pin, inferred from today's green
  lint job under a 3.10 pin, with the PR's CI run as the confirming experiment — `uv python find` did
  not honour `UV_PYTHON` locally, so precedence is not locally reproduced); and the verification split
  (apply proves V1/V2/V3/V6/V7/V8; verify owns V4 and V5, with V5 obliged to report the unexplained
  `tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version` observation rather
  than absorb or weaken it). Consistent with the CI-07 delta; no new module, interface, data flow,
  dependency or workflow change.
- **artifacts**:
  - `openspec/changes/2026-09-14-chore-python-version-313/design.md` (this file)
  - Engram: topic key `sdd/2026-09-14-chore-python-version-313/design`, type `architecture`
- **next_recommended**: `apply` — CI-07's spec delta and this design are now both present, so the
  parent's expectation that `apply` unblocks should hold; apply is a single work unit (pin line + rule-12
  note) and proves V1/V2/V3/V6/V7/V8, then `verify` owns V4 and V5.
- **risks**: R1 gate claim asserted but not reproduced (mitigation: V2–V4 mandatory with real output);
  R2 the `test_packaging.py` observation (mitigation: V5 explicit disposition — escalate, never absorb);
  R3 hidden test/doc pins the pin or rule 12 (verified absent; V8 re-proves); R4 scope creep
  (mechanical V6 diff check; `[tool.mypy] python_version` deliberately kept); R5 misread as reducing
  user-facing support (packaging evidence + untouched `requires-python`/matrix); R6 rule-14 regex
  perturbed by a rule-12 edit (low; V8); R7 the dev interpreter requirement rises to 3.13 without a
  CONTRIBUTING.md line (accepted; `uv sync` follows the pin, escape hatch documented in rule 12).
- **skill_resolution**: none — no executor/phase skill path was injected for this design phase, and no
  SDD-design skill exists in the available-skills list; the phase was completed from the injected SDD
  design contract directly (degraded fallback not required for a read-and-write design artifact).

## Key Learnings

- **Some design artifacts are records, not decisions.** When a change's decision points are already
  resolved, the honest artifact says "no architectural surface" and spends its length on the relationship
  between settings, the *why-not-the-other-mechanism* argument, the rejected alternatives and the
  blast radius — the four things a proposal does not carry and a reviewer cannot reconstruct.
- **Three settings that look like one.** `.python-version` (which interpreter runs the tools),
  `[tool.mypy] python_version` (which language level is checked against), `requires-python` (what users
  may install) are independent; the proof is that the green 3.13 measurement came from moving only the
  first. The same class also contains ruff's `target-version`.
- **A dead code arm can make a quality gate unreachable, not merely red.** The five duplicated
  `tomli`/`tomllib` fallbacks mean one arm is dead per interpreter, so a *dev-environment pin* decides
  whether a 100% coverage mandate is satisfiable. A pin and a coverage mandate can be mutually
  exclusive, which reframes "fix the environment" as a legitimate architectural finding.
- **`set -euo pipefail` turns one red gate into three unverified ones.** The `cli.py` failure aborts
  `check_core_coverage.sh` before the other three modules, so the true 3.10 baseline state was "one gate
  red, three never measured" — worth recording as such rather than as "four red gates".
- **Inference must be labelled as inference.** The CI-side precedence of `UV_PYTHON` over
  `.python-version` is supported by a green lint job under a 3.10 pin but was not reproducible locally,
  so the design states the inference, its support, and the confirming experiment (the PR's own CI run)
  instead of claiming a proof.
