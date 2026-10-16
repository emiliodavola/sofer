# Tasks: feat-curation-rationale-key

**Change** `2026-10-16-feat-curation-rationale-key` (GitHub **#324**) · branch
`feat/324-curation-rationale-key` from `dev@5249be6` · store **hybrid**.

**Inputs read this phase, directly:** `odd/tasks/curation-rationale-key.md` (specification of record),
`proposal.md` and `design.md` of this change, and issue #324's option 1.

**One-line outcome:** a config can fill `### Curation Rationale` with inline text and needs no file.

---

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Branch off `dev@5249be6` | — | git | done | `feat/324-curation-rationale-key` |
| T2 | RED: 7 tests for the key, the precedence, the two whitespace edges and the TOML round trip | S1 S2 S3 | inline, test-first | done | `7 failed, 11 passed` on the missing field, before T3/T4 |
| T3 | `model.py`: the `curation_rationale` field + its `from_toml` read | S1 | inline | done | `TestCurationRationaleKey`, `TestCardSectionKeysFromToml` |
| T4 | `repo_compliance.py`: the three-arm chain; `_MORE_INFO` stays four sites | S1 S2 S7 | inline | done | `21 passed`; `test_the_sentinel_is_the_single_shared_constant` |
| T5 | `repo-compliance` §2.1.1 + §2.1.2, and the removal of the clause sentence that asserted the opposite | S6 S7 | inline | done | this change's `specs/repo-compliance/spec.md`; the canonical spec |
| T6 | Gates: full suite, collection delta, ruff/format/mypy/pyright, test-mapping checker | — | inline | done | see the archive report |
| T7 | Archive inside the delivery branch (rule 15) | — | inline | done | this folder |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | `2247 passed, 9 skipped` (86.44 s) |
| Collection delta vs `dev@5249be6` | 2249 → 2256 collected (**+7**, the 7 new tests) |
| ruff / format (`src/ tests/`) | `All checks passed!` / `75 files already formatted` |
| mypy (`src/ scripts/`) / pyright | 0 errors / 0 errors (1 pre-existing `tomli` warning) |
| Test-mapping contract | `OK` |
| rule-14 per-file 100.00% gates | **not run** — no edit to the four core modules, and no test here executes their lines |

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The new tests **did** observe RED (`7 failed` on an
`AttributeError`/`TypeError` for the missing field) before the production edits, which is the
red-green sequence the harness prefers. What did **not** hold is the artifact ordering: the feature
document was written after the first source edit, a deviation recorded as D6 in
`odd/tasks/curation-rationale-key.md` and in the archive report.
