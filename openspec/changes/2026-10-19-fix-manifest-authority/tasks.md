# Tasks — `2026-10-19-fix-manifest-authority` (issue #349)

> Planning record. The working plan with spec ids, routes, risks and the Log lives in
> `odd/tasks/manifest-authority.md`; this file mirrors the state of each task so the
> archive report can be read without the ODD doc.

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | `write_manifest()` in `manifest.py`; `prepare` writes through it; RED carrier: the durable file follows `codebook_all` | done | commit `d05acd4`; `test_codebook_all_refreshes_the_durable_manifest`; `pytest tests/test_manifest.py` 15 passed |
| T2 | `refresh_manifest()` called at the end of `codebook_all` / `profile_all` / `render_all` | done | commit `d05acd4`; `test_profile_and_render_all_refresh_the_durable_manifest`, `test_a_cache_mode_phase_never_invents_a_package_record` |
| T3 | `publish` reads `from_dir`, recomputes only when no record exists, and refuses a stale record before the network | done | `3ed11cf`; `TestDurableManifest` (6 tests) in `tests/test_publish.py` |
| T4 | Tests: per-phase invariant, legacy tree, stale blocks, stale warns, both path roots, nothing-declared | done | `3ed11cf`; `tests/test_manifest.py` 17 passed; `tests/test_publish.py` 134 passed |
| T5 | PUB-12 reconciliation + PRP-11 refresh clause, in the delta and the canonical specs | done | `specs/publish/spec.md`, `specs/prepare/spec.md`, `openspec/specs/publish/spec.md`, `openspec/specs/prepare/spec.md`; `check_test_mapping.py` OK |
| T6 | Recovery text and CLI help name the real recovery; `README.md` + `README_ES.md` | done | the docs commit on this branch |
| T7 | Gates: full suite under coverage, the four 100.00% core modules, ruff, mypy, pyright, `check_test_mapping.py`, differential check against `47bf12c` | done | the archive report in `openspec/changes/archive/2026-10-19-fix-manifest-authority/` carries the verbatim evidence |

## Deviations

- The writer delegation for T3 was refused by the harness three times
  (`Writer session Git authority changed before admission`), after clean Git state was
  verified (single worktree, expected HEAD, no locks). T3 was implemented inline by the
  parent instead; the fallback is recorded here rather than retried.
- T4's publish-side tests were written before the implementation in `publish.py`
  (RED observed: five real assertion failures, including the ghost-entry discriminator),
  so test-first holds for that unit.
