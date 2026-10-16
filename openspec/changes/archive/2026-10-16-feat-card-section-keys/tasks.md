# Tasks: feat-card-section-keys

**Change** `2026-10-16-feat-card-section-keys` (GitHub **#291**) · branch
`feat/291-card-section-keys` from `dev@6786ba1` · store **hybrid**.

**Inputs read this phase, directly:** `odd/tasks/card-section-keys.md` (specification of record),
`design.md` and `proposal.md` of this change, and the maintainer's decision D1 (add the `[meta]` keys
rather than omit the sections).

**One-line outcome:** a config with every ROTW field filled produces a card with no
`[More Information Needed]` and no `[Not specified]`.

---

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Branch off `dev`; feature doc | — | done | `feat/291-card-section-keys`; `odd/tasks/card-section-keys.md` |
| T2 | `model.py`: five `[meta]` fields + `from_toml` reads | S1 | done | `TestCardSectionKeysFromToml` (2 tests) |
| T3 | `repo_compliance.py`: one `_MORE_INFO` constant; the seven sites read their key with a `.strip()` fallback | S1 S7 | done | `TestCardSectionKeys` (8 tests) |
| T4 | `repository` falls back to `source`, declared value wins | S3 | done | `test_repository_falls_back_to_the_source`, `test_a_declared_repository_beats_the_source` |
| T5 | `repo-compliance` spec delta + canonical §2.1.1/§2.1.2 | S1 S3 | done | `specs/repo-compliance/spec.md` of this change; `openspec/specs/repo-compliance/spec.md` |
| T6 | Gates: full suite, per-file 100.00% on the four core modules, ruff/format/mypy/pyright, test-mapping checker | — | done | see the close-out |
| T7 | Work-unit commits on the branch (no push, no PR) | — | done | see the archive report |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | see the archive report |
| `cli.py` / `scanner.py` / `prepare.py` / `publish.py` 100.00% (rule 14) | 100% each |
| TOTAL floor | ≥ 90% |
| ruff / format / mypy / pyright | clean |
| Test-mapping contract | `OK` |
| README / README_ES | unchanged on purpose: the README enumerates only three `[meta]` keys, so the full key list lives in the spec and rule 13 is not triggered |

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests. The
measured sequence, including the three fixture corrections and the reason no existing test changed, is
recorded in `design.md` §3.3 and §4.
