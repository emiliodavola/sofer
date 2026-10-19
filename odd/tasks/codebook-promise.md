# Feature: codebook-promise — issue #354

**Branch:** `fix/354-codebook-promise` from `dev@150ead1`
**Issue:** `emiliodavola/sofer#354` — *bug(publish): the promised-codebooks rule cannot fire — `codebooks_required` reaches neither the writer that records the promise nor the reader that enforces it*
**Delivery:** single PR, assigned to `emiliodavola`; commit, push and PR were explicitly requested by the maintainer
**Test runner:** `uv run pytest tests/ -q`
**Decision:** the promise is derived from the package tree (`codebook.md` present ⇔ codebooks were promised); the `codebooks_required` parameter is deleted from every home
**Risk:** item 3 — `publish`, `build_package_manifest`, `write_manifest` and `refresh_manifest` are importable API and the removal of a keyword parameter is a contract change

## Specs

S1 — #354 `## Expected behaviour`, chosen branch (verbatim): "**The promise is recorded.** `prepare --all-files` and `codebook_all` write (and refresh) the record with the promise, so an absent `codebooks/` entry is recorded `MISSING` and the block that already exists fires with its recovery. This is the smallest change that makes PUB-12's sentence true, and it lets the now-unused `publish` parameter be deleted — one home for the promise, less surface rather than more."

S2 — #354 `## Acceptance criteria` (verbatim): "promised + absent → the record reads `missing`, and `publish` refuses with a recovery naming the chain that supplies the pages;"

S3 — #354 `## Acceptance criteria` (verbatim): "not promised + absent → `optional`, and no warning (PUB-08 preserved);"

S4 — #354 `## Acceptance criteria` (verbatim): "after the fix, the flag has exactly one home, and the dead parameter is gone from the other;"

S5 — #354 `## Acceptance criteria` (verbatim): "both directions are pinned by tests, and any new line lives in a module under its existing coverage mandate (`publish.py`, `prepare.py` and `cli.py` are at 100.00%; `# pragma: no cover` is forbidden there)."

S6 — derived from S1 (the break the issue does not name): the promise SHALL survive every later-phase refresh, so `profile_all` and `render_all` SHALL NOT downgrade a promised-and-absent codebook set back to `optional`.

S7 — derived from S1 (empty tree): a `codebooks/` directory that exists but holds no page SHALL NOT be a silent absence — it is `missing` when promised and `optional` when not.

S8 — maintainer instruction (verbatim): "usando el nivel de ODD necesario implementalo, creá una rama aparte para versionar, luego push y PR asignado a mi"

## Tasks

| # | Task | Spec | Status | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Feature doc, branch `fix/354-codebook-promise`, Engram mirror | S8 | done | this file; `odd/codebook-promise/tasks` |
| T2 | RED first: rewrite the promise test as tree-derived, add sticky-refresh, empty-dir and confirm-refusal cases | S2, S3, S6, S7 | done | 4 failures observed before the implementation (3 in `tests/test_manifest.py`, 1 in `tests/test_publish.py::TestDurableManifest`) |
| T3 | `manifest.py`: derive the promise from `codebook.md`, treat an empty `codebooks/` as an absence, delete the parameter from `build_package_manifest`, `write_manifest`, `refresh_manifest` | S1, S4, S6, S7 | done | `git diff src/sofer/manifest.py` |
| T4 | `publish.py`: delete the parameter from `publish` and `_delivery_divergence` and the two call sites | S1, S4 | done | `rg codebooks_required src/ tests/ scripts/` → no match |
| T5 | PUB-12 delta + canonical spec + docstrings name the tree-derived promise | S1, S2, S3 | done | `openspec/specs/publish/spec.md` (PUB-12 + 3 scenarios), `openspec/changes/2026-10-19-fix-codebook-promise/`, both READMEs |
| T6 | Gates: full suite under coverage, the four 100.00% modules, ruff, mypy, pyright, `check_test_mapping.py`, differential check against `dev@150ead1` | S5 | done | 2513 passed / 9 skipped; four gated modules 100.00%, TOTAL 94% (gate 90); ruff clean; mypy clean; pyright 0 errors; test-mapping OK; differential identical; see L5 |
| T7 | Independent verifier over the diff, then the native review assessment | — | done | verifier: PASS WITH ADVISORIES, no code blocker (L7); native review on `dev..HEAD` after the record commit: approved and acknowledged, findings non-blocking |
| T8 | Archive the SDD change inside this branch, push, PR assigned to `emiliodavola` | S8 | done | `openspec/changes/archive/2026-10-19-fix-codebook-promise/` (L8); PR #355 |

## Log

L1 — maintainer request (verbatim, 2026-10-19): "usando el nivel de ODD necesario implementalo, creá una rama aparte para versionar, luego push y PR asignado a mi"

L2 — roadmap decision (2026-10-19): the single home of the promise is the package tree. `generate_all` always writes the root `codebook.md` (`codebook.py:792`) but only creates `codebooks/` when a page is written, so `codebook.md` present + `codebooks/` absent is exactly "promised and empty". The alternative — a sticky boolean in `manifest.json` — adds a field the #349 divergence recount cannot recompute, so it would need a second source for the same fact.

L3 — inventory (2026-10-19): the issue names three breaks; verification found a fourth (the canonical chain's `profile_all`/`render_all` refresh would downgrade the promise back to `optional` even if a caller had passed the flag) and a fifth hole (an existing but empty `codebooks/` emitted no entry at all). Both are covered by S6/S7.

L4 — implementation (2026-10-19): `build_package_manifest` derives `promised` from `(output_dir / "codebook.md").is_file()` and collects pages before deciding, so an empty directory is an absence; the parameter is gone from all five signatures and all call sites. `publish` still enforces `required_missing()` over the durable record — the block did not need to move, only the record needed to be able to carry `missing`.

L5 — gates (2026-10-19): `uv run pytest tests/ -q` → 2513 passed, 9 skipped; `coverage report` → `cli.py`, `scanner.py`, `prepare.py`, `publish.py` 100.00% each under the scoped `--fail-under=100` gate, module report 94% TOTAL (gate `fail_under = 90`), `manifest.py` 99% (line 351, pre-existing); `ruff check` + `format --check` clean; `mypy src/ scripts/` clean; `pyright` 0 errors (1 pre-existing `tomli` warning); `check_test_mapping.py` → contract holds, publish remains a declared-backlog spec. Differential against a `dev@150ead1` worktree (outside the repo, three cases: `prepare`, `prepare --all-files`, `prepare` + `codebook_all`): manifests byte-identical after dropping the `source` path; only the imported module path differed, which proves the two runs used different trees. The intended delta (promised-and-empty → `missing`) is pinned by the RED/GREEN tests, not by the differential.

L6 — Risk: item 3, because the deleted keyword parameters are importable API and the codebook rule is a delivery gate.

L7 — independent verifier (2026-10-19): PASS WITH ADVISORIES, no code blocker; S1–S7 reproduced independently (28 probe assertions plus a real-path `prepare --all-files` probe), S8 blocked at the time because nothing was committed yet. The verifier's three non-duplicative probes landed as `tests/test_codebook_promise.py`: the real writer state, the absence of the keyword in every signature, and the no-path-divergence claim. Two record corrections were applied: the premature T8 "done" and this Log's earlier 98% figure, which was a six-file scoped report, not the TOTAL.

L8 — close (2026-10-19): native review approved and its authority acknowledged; the change dir moved to `openspec/changes/archive/2026-10-19-fix-codebook-promise/` inside this branch with `archive-report.md` (gates, differential, decisions, advisories), and the branch pushed as PR #355 against `dev`, assigned to `emiliodavola`. Final gate run: 2514 passed / 8 skipped (an earlier run reported 2513 / 9 — same 2522 collected, one host-capability skip flipped). The archive report's advisories are follow-ups, not debt on this candidate: the hardcoded index filename, the declared migration for old `optional` records, the sticky-refresh test not calling the phase functions end-to-end, and the pre-existing `prepare` silent success for an unreadable source that `publish` then refuses.
