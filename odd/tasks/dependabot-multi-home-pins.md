# Feature: dependabot-multi-home-pins — issue #275

**Branch:** `ci/275-dependabot-multi-home-pins` from `dev@b0b6012`
**Issue:** `emiliodavola/sofer#275` — closed as COMPLETED
**Evidence PR:** #271 — the red bot PR that motivated the change; closed by the maintainer
**Delivery PR:** `emiliodavola/sofer#276` — merged as `b05d977`
**SDD change:** `openspec/changes/archive/2026-10-09-fix-dependabot-multi-home-pins/` (archived)

## Goal

A Dependabot bump PR is either green or is not opened at all. The guarantee held for `ruff` and
`fastmcp` majors (CI-14 S1/S2) and failed for `mypy`/`pyright`, whose exact versions are declared in
three text homes the `uv` ecosystem cannot move together: the `[dependency-groups] dev` pin,
`openspec/project.md`, and `openspec/config.yaml`.

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: guard fails against the current `dependabot.yml`; mapping gate fails on the new CI-14 scenario | done | guard: `AssertionError: expected exactly one 'mypy' ignore entry, found []` at `tests/test_ci_workflows.py:1318`; mapping: `FAIL: ci: scenario has no mapping row: 'uv updates ignore the coordinated analyzer pins'` (1 violation) |
| T2 | GREEN: `mypy`/`pyright` in `updates[uv].ignore` + policy comment | done | guard `1 passed`; commit `1c4589c` |
| T3 | `CONTRIBUTING.md`: two → three intentional non-automated bumps | done | commit `1c4589c` |
| T4 | `AGENTS.md` rule 9: analyzer pins named beside `ruff`/`fastmcp` | done | commit `1c4589c` |
| T5 | CI-14 bullet + scenario + Test Mapping row | done | `check_test_mapping.py` exit 0, `ci: 51 scenario(s), mapped`; commit `1c4589c` |
| T6 | Full gates green | done | pytest 1998 passed / 6 skipped; ruff clean; mypy 36 files; pyright 0 errors; coverage TOTAL 94% with the four rule-14 files at 100% |
| T7 | Work-unit commits on the feature branch | done | `1c4589c`, `3f10c54`, `9596da7` |
| T8 | Push + PR against `dev`, assigned to `emiliodavola` | done | PR #276 — 14/14 checks SUCCESS, `MERGEABLE` / `CLEAN` |
| T9 | Cadence `weekly` → `monthly` for both ecosystems, dropping `day` | done | commit `9596da7`; parsed schedules `[('uv', {'interval': 'monthly'}), ('github-actions', {'interval': 'monthly'})]` |
| T10 | Archive the SDD change and close out this record | done | moved to `openspec/changes/archive/2026-10-09-fix-dependabot-multi-home-pins/` with its `archive-report.md`; `openspec/changes/` now holds only `archive/` |

## Decisions taken before implementation

- **D1 — blanket ignore, matching `ruff`.** Bare `dependency-name` entries with no `update-types`
  narrowing. Accepted cost, stated plainly: major analyzer bumps stop arriving as individual PRs.
  Rejected alternative: `update-types: [minor, patch]` — it fixes the group poisoning but not the
  defect, and creates a two-class policy (`ruff` blanket, analyzers narrowed) the next maintainer
  has to re-derive.
- **D2 — the #258 drift guard is not touched.** It removes a bump the bot cannot complete, never the
  check that catches a human moving one home and not the others. Verified byte-identical.
- **D3 — no version bumps in this change.** `pyproject.toml`, `uv.lock`, `openspec/project.md` and
  `openspec/config.yaml` are untouched.
- **D4 — the cadence is documented, not guarded and not spec'd.** Every existing guard in this area
  encodes a *constraint*; cadence is a *preference*, and gating it would make a scheduling choice
  unchangeable without editing a test. The rationale lives in the `dependabot.yml` policy comment.

## Out of scope

- Unblocking #271 (wave 0): `maintainerCanModify=false` on the Dependabot branch, so it cannot be
  rebased in place. Resolved by the maintainer — see the wave-0 section below.
- Any `src/` change. This is config, policy docs, one spec delta, and one guard.

## Gates

`uv run pytest tests/ -q` · `uv run ruff check src/ tests/ scripts/` · `uv run ruff format --check src/ tests/`
· `uv run mypy src/ scripts/` · `uv run pyright` · `uv run coverage run -m pytest` + `coverage report`
· `uv run python scripts/check_test_mapping.py`

Base-vs-branch tally, measured back to back in the same environment: base `b0b6012` 1997 passed /
6 skipped → branch 1998 / 6. Delta exactly +1 test, the new guard.

## Wave 0 (#271) — closed by the maintainer

#271 was **closed** by the maintainer rather than rebased, because `maintainerCanModify=false` on
the Dependabot branch made a rebase impossible — so option **(b)** was taken, not (c).

Consequence, recorded: the three single-home bumps it carried (`fastmcp` 4.0.8→4.0.10,
`python-dotenv` 1.2.3→1.2.4, `coverage` 7.16.1→7.16.2) waited for the next scheduled run — which the
cadence change in this same change made **monthly**. They did not have to wait that long: the next
Dependabot run after the merge opened a fresh group (#277), which carried `fastmcp`, `python-dotenv`,
`datasets` and `coverage` and merged as `86398ab`.
