# Proposal — `2026-10-09-fix-dependabot-multi-home-pins`

> **Change** `2026-10-09-fix-dependabot-multi-home-pins` · issue **#275**
> (*ci(deps): the Dependabot minor/patch group carries the multi-home analyzer pins — every
> mypy/pyright bump is red by construction*) · branch `ci/275-dependabot-multi-home-pins` from
> `dev@b0b6012` · store **hybrid** (this file + Engram mirror).
>
> **Status:** proposal complete, implemented and verified in the same branch.

---

## 1. Intent

`.github/dependabot.yml` groups every minor/patch `uv` bump under `python-minor-and-patch` with
`patterns: ["*"]`. That group includes the two **exact analyzer pins** `mypy==2.3.1` and
`pyright==1.1.414`, whose versions are declared in **three text homes that must move together**:
the `[dependency-groups] dev` pin in `pyproject.toml`, and the version named in
`openspec/project.md` and `openspec/config.yaml` — forced to agree by
`tests/test_ci_workflows.py::test_openspec_context_declares_the_enforced_tool_versions`
(issue #258, spec CI-13/CI-14). Dependabot's `uv` ecosystem can move only `pyproject.toml` and
`uv.lock`, so **every mypy/pyright PR it opens fails a guard by construction**.

This is the same defect class the same file already solved for `ruff` — its rationale is written
in the policy comment there ("the `uv` ecosystem can move only the first, so every PR it would
open is red (#252)"). PR #255 (*ci: harden the Dependabot bump flow so bumps cannot break CI*)
stated the goal this change completes: *"configure Dependabot so the bumps it cannot complete
atomically are not attempted."* The analyzer pins escaped that hardening, and **PR #271 is the
measured instance**.

## 2. Scope

### In scope

- `mypy` and `pyright` added to `updates[uv].ignore` in `.github/dependabot.yml`, with the
  rationale bullet in the same file's policy comment.
- `CONTRIBUTING.md` *Dependency updates*: the intentional non-automated list goes from two bumps
  to three, with the analyzer pins' three text homes and the manual procedure.
- `AGENTS.md` rule 9: the analyzer pins named beside `ruff` and `fastmcp` majors.
- `openspec/specs/ci/spec.md`: CI-14 amended (one new bullet + one new scenario) and one new
  Test Mapping row.
- One new static guard, `test_dependabot_ignores_the_coordinated_analyzer_pins`.

### Out of scope (non-goals, strictly respected)

- **No version bump of any kind.** `pyproject.toml`, `uv.lock`, `openspec/project.md` and
  `openspec/config.yaml` are untouched. Unblocking PR #271 is a separate decision.
- **No weakening of the #258 drift guard.** The check that catches a human moving one home and not
  the others stays byte-identical; this change removes a bump the bot cannot complete, never the
  check that catches the drift.
- **No `src/` change**, no new requirement, no workflow change, no `release.yml` change.
- **No README change.** No README section documents the dependency-update policy, so AGENTS.md
  rule 13 has no counterpart to sync. Verified during implementation.
- No commit/push/PR from SDD phases; the parent owns delivery.

## 3. Settled decisions

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | **Blanket `ignore`, matching `ruff`.** Bare `- dependency-name: "mypy"` / `"pyright"` entries, no `update-types` narrowing. | The multi-home edit is the same work at every update type, and a bare entry keeps one discrimination rule for the file. **Accepted cost, stated plainly:** major analyzer bumps stop arriving as individual PRs. Rejected alternative: `update-types: ["minor", "patch"]` so majors keep arriving — it fixes the group poisoning but not the defect, and it creates a two-class policy (`ruff` blanket, analyzers narrowed) that the next maintainer has to re-derive. |
| **D2** | The `ruff` entry and the `fastmcp` majors entry are left untouched. | Both are correct as written; the new entries are additive. |
| **D3** | The new guard mirrors `test_dependabot_ignores_the_coordinated_ruff_pin` and hardcodes no version. | CI-08 S1/S3 discipline: guards derive versions from the declaration home and carry no literal of their own. |
| **D4** | The record lands as a **MODIFIED** CI-14 block in the delta, not a new requirement. | CI-14 is the requirement that owns the Dependabot update policy; a fourth ignored dependency class extends it. Precedent: CI-07 and MSP-R03 were amended the same way. |

## 4. Issue #275 acceptance mapping

| AC | Acceptance criterion | Satisfied by |
| --- | --- | --- |
| **AC1** | The `uv` update ignores `mypy` and `pyright` at every update type | `.github/dependabot.yml` `ignore` entries + guard `test_dependabot_ignores_the_coordinated_analyzer_pins` + CI-14 S4 scenario |
| **AC2** | The policy is documented where a maintainer will look for it | `CONTRIBUTING.md` *Dependency updates* third bullet; `AGENTS.md` rule 9; the `dependabot.yml` policy comment |
| **AC3** | The decision is recorded durably, not in prose alone | CI-14 amendment in `openspec/specs/ci/spec.md` + its Test Mapping row |
| **AC4** | The #258 drift protection is not weakened | `test_openspec_context_declares_the_enforced_tool_versions` and its helpers byte-identical (D2) |
| **AC5** | The three safe bumps sharing the group are no longer withheld by an unrelated analyzer | Follows from AC1: the next Dependabot run opens a group with no multi-home member. PR #271 itself is resolved separately (see §8) |

## 5. Affected areas

| Area | File | Change class |
| --- | --- | --- |
| Policy config | `.github/dependabot.yml` | additive (2 ignore entries + 1 comment bullet) |
| Guards | `tests/test_ci_workflows.py` | additive (1 guard, ~25 lines) |
| Spec | `openspec/specs/ci/spec.md` | modification (CI-14 bullet + scenario + Test Mapping row) |
| Docs | `CONTRIBUTING.md`, `AGENTS.md` | additive (1 bullet each, one count word) |
| SDD | `openspec/changes/2026-10-09-fix-dependabot-multi-home-pins/**` | new |

**Code + config + tests: ≈ 45 changed lines.** Well inside the review budget; single PR, no chaining.

## 6. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A future maintainer needs an analyzer major and no longer sees it as a PR | Low | Accepted by D1 and stated in three places (issue, `dependabot.yml` comment, `CONTRIBUTING.md`). The `CONTRIBUTING.md` bullet carries the manual procedure, so the signal loss is documented, not silent |
| R2 | The blanket ignore could suppress security-update PRs for these two packages | Low | Pre-existing property of the same mechanism already applied to `ruff`; not a new regression. Flagged in issue #275 for verification rather than asserted here |
| R3 | The guard could pass vacuously if the `ignore` list shape changed | Low | The guard asserts `ignore` is a list and asserts exactly one entry per package, mirroring the S1 guard's non-vacuous shape |

## 7. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | Guard `test_dependabot_ignores_the_coordinated_analyzer_pins` is red before the config edit and green after |
| SC-2 | `scripts/check_test_mapping.py` exits 0 with `ci: 51 scenario(s), mapped` (50 before, +1 new scenario, 0 unmapped) |
| SC-3 | Full suite green with no reduction in the collected/passed tally; `tests/test_ci_workflows.py` goes 51 → 52 |
| SC-4 | `ruff check`, `ruff format --check`, `mypy src/ scripts/`, `pyright` and the coverage gates unchanged and green |
| SC-5 | `test_openspec_context_declares_the_enforced_tool_versions` byte-identical (D2) |
| SC-6 | `pyproject.toml`, `uv.lock`, `openspec/project.md`, `openspec/config.yaml` and `src/` absent from the diff |

## 8. PR boundary and the wave-0 decision

**Boundary: one PR, no chaining.** The change is a single policy adoption whose record, guard and
docs are mutually dependent.

**PR #271 is NOT closed by this change.** It cannot be rebased in place —
`maintainerCanModify=false` on the Dependabot branch, measured during implementation — so the
options are (a) close it once this change merges and let the next weekly run open a clean group, or
(b) open a replacement branch off `dev` carrying only the three single-home bumps. That is the
maintainer's decision and is recorded as an open item in issue #275.

## 9. Non-goals (restated for the spec delta)

No version bump; no edit to `pyproject.toml`, `uv.lock`, `openspec/project.md`,
`openspec/config.yaml` or `src/`; no weakening or amendment of the #258 tool-version guard; no new
`ci` requirement; no workflow, `release.yml`, CI-matrix or coverage-floor change; no README change;
no change to the `ruff` or `fastmcp` ignore entries; no commit/push/PR from SDD phases.
