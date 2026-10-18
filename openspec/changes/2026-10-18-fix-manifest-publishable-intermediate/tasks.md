# Tasks: fix-manifest-publishable-intermediate

**Change** `2026-10-18-fix-manifest-publishable-intermediate` (GitHub **#346**) ·
branch `fix/346-manifest-publishable-intermediate`, rebased onto `dev@e23a6e8` ·
store **hybrid**.

**One-line outcome:** every manifest entry says whether it belongs to the delivery
(`publishable`) or is a local-only layer (`intermediate`), the layers are probed
where the pipeline writes them, and the manifest's delivered set equals what the
copy path stages.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change's carrier is a
measured before/after rather than a red test file: the implementation was written
first, and the defect was then measured on the real artifact with a scratch probe
run against the pre-fix `sofer.manifest` and against the change. The pre-fix
measurement is in `../../archive/2026-10-18-fix-manifest-publishable-intermediate/archive-report.md`
(§2) and in `design.md` §1; the assertion that pins the fixed behaviour is
`tests/test_manifest.py::test_delivered_set_is_the_staged_set`, which compares the
manifest against the real `_copy_package` output on the same tree.

The first RED attempt was an `ImportError` for `ArtifactClass` at collection — real
but weak evidence, which is why the behavioural probe replaced it as the recorded
carrier. Deviations are listed in the archive report.

---

## Tasks

| # | Task | Spec | State |
| --- | --- | --- | --- |
| T1 | `ArtifactClass` enum carried by every entry, serialized, read with a backward-compatible default | S2, S3 | done |
| T2 | `publishable()` / `intermediate()` / `delivered()` selectors | S1, S4 | done |
| T3 | Layer probe at the artifact cache with the dataset-root fallback and a safe relative path | S1 | done |
| T4 | Tests: every entry classified, delivered == staged, cache probe, root fallback, legacy manifest | S1-S5 | done |
| T5 | PUB-12 clause (field + probe + delivered identity) in the delta and the canonical spec, plus the archive report | S1-S3 | done |
| T6 | Gates: `pytest`, `publish.py` at 100.00%, `ruff`, `mypy`, `pyright`, `scripts/check_test_mapping.py` | — | done |

**Status:** implementation complete on `fix/346-manifest-publishable-intermediate`,
rebased onto `dev@e23a6e8` (the merge of PR #351); the branch is not pushed and no
PR exists — push and PR creation are the maintainer's decision.

## Work units

1. `fix(manifest): classify every artifact publishable or intermediate (#346)` —
   T1, T2, T3, T4.
2. `docs(specs): declare the PUB-12 classification boundary (#346)` — T5.
3. `chore(odd): record the #346 work units and archive the change` — T5, T6.
