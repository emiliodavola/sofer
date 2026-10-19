# Tasks — `2026-10-19-fix-codebook-promise` (issue #354)

> Planning record. The working plan with spec ids, routes, risks and the Log lives in
> `odd/tasks/codebook-promise.md`; this file mirrors the state of each task so the
> archive report can be read without the ODD doc.

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Feature doc, branch `fix/354-codebook-promise`, Engram mirror | done | `odd/tasks/codebook-promise.md`; topic `odd/codebook-promise/tasks` |
| T2 | RED first: tree-derived promise, empty-dir absence, sticky refresh, confirm refusal | done | four assertion failures observed before the implementation |
| T3 | `manifest.py` derives the promise from `codebook.md`; empty `codebooks/` is an absence; parameter deleted from the three signatures | done | the fix commit; `pytest tests/test_manifest.py tests/test_publish.py` |
| T4 | `publish.py`: parameter deleted from `publish` and `_delivery_divergence`, both call sites updated | done | the fix commit |
| T5 | PUB-12 delta and canonical spec; README/README_ES note the tree-derived rule | done | `specs/publish/spec.md`, `openspec/specs/publish/spec.md`, both READMEs |
| T6 | Gates: full suite under coverage, four 100.00% modules, ruff, mypy, pyright, test-mapping checker, differential check | done | `archive-report.md` §2 |
| T7 | Independent verifier over the diff, then the native review assessment | in progress | `archive-report.md` §3 |
| T8 | Archive inside the branch; push; PR assigned to `emiliodavola` | pending | |
