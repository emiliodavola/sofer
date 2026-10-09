# Tasks: fix-dependabot-multi-home-pins

**Change** `2026-10-09-fix-dependabot-multi-home-pins` (GitHub **#275**) · branch
`ci/275-dependabot-multi-home-pins` from `dev@b0b6012` · store **hybrid** — this file plus the Engram
mirror under topic key `sdd/2026-10-09-fix-dependabot-multi-home-pins/tasks`.

**Inputs read this phase, directly:** `design.md` (this change) and `proposal.md` (this change).
No other document is consulted.

**One-line outcome:** the `uv` Dependabot update ignores `mypy` and `pyright` at every update type,
so no PR the bot opens can be red by construction; the record lives in CI-14, the guard in
`tests/test_ci_workflows.py`, and the manual procedure in `CONTRIBUTING.md`.

---

## TDD posture — stated honestly: the carrier is the guard plus the mapping gate

`openspec/config.yaml` sets `strict_tdd: false`, and this change declares a policy rather than
production behaviour: there is no runtime behaviour to drive red-first. A manufactured "failing test
of behaviour that does not exist" would be theatre.

The honest red-then-green carrier is the **new guard** and the **Test Mapping gate**, both of which
fail for exactly the reasons this change exists, before any config or spec row is written:

- **RED (measured):** the guard fails with `AssertionError: expected exactly one 'mypy' ignore
  entry, found []` at `tests/test_ci_workflows.py:1318`; the mapping gate fails with
  `FAIL: ci: scenario has no mapping row: 'uv updates ignore the coordinated analyzer pins'`.
- **GREEN (measured):** the guard passes; the mapping gate exits 0 with
  `INFO: ci: 51 scenario(s), mapped`; the focused guard file goes 51 → 52 passed.

**REFACTOR has no target** — the change adds a declaration and its assertion, with no existing code
to restructure.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Write the new guard `test_dependabot_ignores_the_coordinated_analyzer_pins` and the CI-14 S4 scenario, **without** the config entries or the mapping row | done | RED: guard `found []` at `tests/test_ci_workflows.py:1318`; mapping gate `1 violation(s) found` |
| T2 | Add `mypy` and `pyright` to `updates[uv].ignore` (bare entries, D1) | done | GREEN: guard `1 passed` |
| T3 | Extend the `.github/dependabot.yml` bump-policy comment with the analyzer bullet | done | diff |
| T4 | Add the CI-14 Test Mapping row | done | GREEN: `check_test_mapping.py` exit 0, `ci: 51 scenario(s), mapped` |
| T5 | `CONTRIBUTING.md` *Dependency updates*: two → three intentional non-automated bumps | done | diff |
| T6 | `AGENTS.md` rule 9: name the analyzer pins beside `ruff` and `fastmcp` | done | diff |
| T7 | Verify no README section documents the dependency-update policy (rule 13) | done | no README section covers it; no README edit |
| T8 | Full gates: pytest, ruff check + format, mypy, pyright, coverage, `check_test_mapping.py` | done | verify report |
| T9 | Work-unit commit(s) on the feature branch | done | `git log` |
| T10 | Cadence `weekly` → `monthly` for both ecosystems, dropping `day` (maintainer-requested, not #275) | done | `git diff`; every existing Dependabot guard still green |

---

## Constraints honoured

- **The cadence is not guarded and not spec'd (D5).** No test asserts `interval`; the rationale is
  in the `dependabot.yml` policy comment. The `weekly` occurrences in `openspec/specs/ci/spec.md`
  (CI-04) are CodeQL's cron, not Dependabot's, so the delta carries no cadence clause.
- **No version bump:** `pyproject.toml`, `uv.lock`, `openspec/project.md` and
  `openspec/config.yaml` are absent from the diff (SC-6).
- **The #258 guard is byte-identical** (D2): `test_openspec_context_declares_the_enforced_tool_versions`
  and its helpers were not edited.
- **No `# pragma: no cover`** added anywhere; no `src/` change; no new `ci` requirement.
- **The `ruff` and `fastmcp` ignore entries are untouched** (D2).

---

## Open item carried to the maintainer

**PR #271** is not resolved by this change and cannot be rebased in place
(`maintainerCanModify=false`, measured). Once this change merges, the choice is (a) close #271 and
let the next weekly run open a clean group, or (b) open a replacement branch off `dev` carrying only
the three single-home bumps (`fastmcp`, `python-dotenv`, `coverage`). Decision recorded in issue
#275.
