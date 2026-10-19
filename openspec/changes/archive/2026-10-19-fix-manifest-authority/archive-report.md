# Archive report — `2026-10-19-fix-manifest-authority`

> **Change** `2026-10-19-fix-manifest-authority` · issue **#349** · branch
> `fix/349-manifest-authority` from `dev@47bf12c` · store **hybrid** (this folder,
> the ODD doc `odd/tasks/manifest-authority.md` and its Engram mirror).
> **Archived inside its own delivery branch** (AGENTS.md rule 15). Push and the pull
> request are the maintainer's decision.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | `write_manifest()` — one writer; `prepare` creates the durable record through it | done | `d05acd4`; `test_codebook_all_refreshes_the_durable_manifest` |
| T2 | `refresh_manifest()` at the end of `codebook_all`, `profile_all`, `render_all`; refreshes only a directory that already owns a manifest | done | `d05acd4`; `test_profile_and_render_all_refresh_the_durable_manifest`, `test_a_cache_mode_phase_never_invents_a_package_record` |
| T3 | `publish` reads `from_dir`; recomputes only for a tree with no durable record; refuses a stale record before the network and before staging | done | `3ed11cf`; `TestDurableManifest` (6 cases) |
| T4 | Tests for every new line and branch, RED first | done | `3ed11cf`; `tests/test_manifest.py` 17 passed, `tests/test_publish.py` 134 passed |
| T5 | PUB-12 reconciliation and the PRP-11 creator/refresher clause, in the delta and both canonical specs | done | this folder's `specs/`; `check_test_mapping.py` exit 0 |
| T6 | `publish` CLI description + `README.md` + `README_ES.md` | done | `57dd0a7` |
| T7 | Gates and the differential check against the base commit | done | §2 below |
| T8 | The independent verification's findings, fixed rather than documented away: an unreadable record is refused with `UNREADABLE_MANIFEST` instead of crashing, and the rule became a path-set comparison instead of an mtime proxy, which deleted the `stat` scan | done | the follow-up commits on this branch |
| T9 | The **second** verification round: its finding that a promised recursive tree the delivery no longer holds went undetected (the upload succeeded without it), closed by comparing the presence of every publishable entry, files and trees alike, and pinned by a test; plus the `UNREADABLE_MANIFEST` clause and the `keep_csv` limit reaching the canonical spec, the delta, the design, the CLI help and both READMEs | done | the follow-up commits on this branch |

**The change in one line:** the manifest on disk stopped being a prepare-time
snapshot nobody read, and became the object `publish` plans and enforces with —
kept current by every phase that adds a package artifact, and refused when something
outran it.

## 2. Verification, verbatim

All commands run from the repository root on the frozen tree.

```
$ uv run coverage run -m pytest tests/ -q
2506 passed, 9 skipped, 6 warnings in 136.24s (0:02:16)
# base dev@47bf12c: 2495 passed, 9 skipped  ->  +11: 8 in tests/test_publish.py,
# 3 in tests/test_manifest.py

$ for f in cli scanner prepare publish; do
    uv run coverage report --include="src/sofer/$f.py" --fail-under=100 -m >/dev/null; echo "$f exit=$?"; done
cli exit=0        # 741 stmts, 100%
scanner exit=0    # 196 stmts, 100%
prepare exit=0    # 342 stmts, 100%
publish exit=0    # 413 stmts, 100%

$ uv run coverage report -m | tail -1
TOTAL                             7740    387   2908    176    94%   # floor 90

$ uv run python scripts/check_test_mapping.py
INFO: publish: 66 scenario(s), unmapped     # was 60
INFO: prepare: 46 scenario(s), unmapped     # was 45
OK: test-mapping contract holds             # exit 0

$ uv run ruff check src/ tests/ scripts/
All checks passed!
$ uv run ruff format --check src/ tests/
79 files already formatted
```

**Differential check** against the base commit, for every command that shares the
code this change touches, **re-run after the rule changed**: Both sides ran in the **same** fixture directory, wiped
and recreated between the two passes, so the absolute paths inside the output are
identical by construction and a diff can only come from behaviour:

```
=== exit codes (rc side command) ===        # base 47bf12c  |  this change
0 base prepare_dataset.toml                 0 new prepare_dataset.toml
0 base codebook_--all-files_--config_dataset.toml   0 new ...
0 base profile_dataset.toml_--all-files     0 new profile_dataset.toml_--all-files
0 base render_dataset.toml_--all-files      0 new render_dataset.toml_--all-files
0 base publish_dataset.toml_--dry-run       0 new publish_dataset.toml_--dry-run
0 base publish_dataset.toml_--target_local_--output_._out   0 new ...

=== stdout/stderr diffs, base (47bf12c) vs new ===
IDENTICAL  codebook_--all-files_--config_dataset.toml.out
IDENTICAL  prepare_dataset.toml.out
IDENTICAL  profile_dataset.toml_--all-files.out
IDENTICAL  publish_dataset.toml_--dry-run.out
IDENTICAL  publish_dataset.toml_--target_local_--output_._out.out
IDENTICAL  render_dataset.toml_--all-files.out
```

No difference nobody asked for. The intended differences are behavioural and are
pinned by tests, not by this comparison: the file on disk changes after each phase,
and a stale record refuses.

## 3. Decisions and honest notes

**The branch decision.** Read as *the same derivation*, PUB-12 was satisfiable —
`publish` recomputes deterministically, so two runs agree. Read as *the same
artifact*, it was never satisfied, and the artifact is what a human or an agent
opens. The maintainer chose **B** (verbatim: "opcion B"). **A** (read the file, fail
closed on staleness alone) blocks the canonical chain by construction, because
`prepare` runs before `codebook_all`, so it is B plus a guaranteed failure mode;
**C** (declare the file a checkpoint) is the smallest diff but leaves the auditable
document unable to answer the only question a reader brings to it.

**Deviations, recorded rather than smoothed over:**

1. **The writer delegation was refused by the harness** three times
   (`Writer session Git authority changed before admission`), repeated after
   verifying clean Git state (single worktree, expected HEAD, no index or hook
   locks) and after changing the task label to force a fresh writer session. T3 was
   implemented inline by the parent. A refused delegation is reported, never retried
   into ceremony.
2. **Test-first held for T3 and not for T1.** Six `TestDurableManifest` cases were
   written before the `publish` implementation and observed RED as real assertion
   failures; the strongest is a ghost required entry that exists only in the durable
   document, which a recount cannot see. T1's carrier RED was the invariant
   `from_dir(out) == build_package_manifest(cfg, out)` failing on the
   `codebook_page` entry that stayed `optional` while the pages were on disk — not
   an `ImportError`, but not written before the helper either.
3. **One existing test needed a fixture adjustment.** `TestAutoPrepare::
   test_up_to_date_skips_prepare` moves `data.parquet` to a future mtime to prove
   the auto-prepare signal, which is now *also* a genuinely stale record; the
   record's mtime moves with the artifact, so the fixture keeps describing the
   up-to-date package it was written about while still testing that signal.
4. **A test-authoring defect of mine**, caught by the first GREEN attempt: the entry
   helper's fifth positional parameter is `status`, and one case passed
   `"intermediate"` there, so the manifest failed to decode before any assertion
   ran. Fixed by naming the parameter.
5. **The differential harness lied twice before it told the truth.** The first pass
   ran each side in its own directory, so five commands "DIFFERED" only by the side's
   absolute path, and `codebook dataset.toml --all-files` exited 1 on *both* sides
   because the batch form needs `--config` — so that row proved nothing. Both were
   fixed before any result was quoted. My first fix attempted `sed` path
   normalization; it did not substitute on file input in this environment, so the
   approach was abandoned in favour of removing the path difference at the source.
6. **"Stable `error_code`" was not adopted.** S7 inherited the phrase from the
   issue, but `sofer_publish_confirm` returns `ok`, `exit_code` and `output` only
   (`mcp_server.py:1860-1868`) — exactly as the pre-existing required-missing block
   always has. The implementation and both spec texts say **marker**:
   `STALE_MANIFEST`, printed in the block and carried to an agent inside the
   envelope's `output`.

**The rule changed after the verification passed, and that is why this record keeps the
rejected version.** The verifier falsified the mtime proxy's false-refusal surface over
every *in-repo* writer and found none; the full suite then found the case that enumeration
cannot see — an in-place edit of a file the record already declares
(`test_root_index_uploaded_as_codebook_md` rewrites `codebook.md` to prove the package's
own file ships). The record and the tree declared exactly the same paths, so nothing had
diverged, yet the proxy refused the delivery and its printed recovery would have
regenerated that file and destroyed the edit. The rule is now a path-set comparison
(design D3b): the record must declare, path for path, the deliverable set a recount
produces, naming `undeclared` and `withdrawn`. `intermediate` entries are never compared.
The change deleted `_newest_declared_artifact` and its whole `stat` scan, so the verifier's
second finding is structurally impossible rather than patched, and two existing fixtures
moved to the supported flow (a hand-added codebook page now needs the chain re-run — which
is exactly what the printed recovery says).

**A false claim in this record, caught by the second verification round.** The `da39960`
commit message and the ODD doc said PUB-12 had gained the `UNREADABLE_MANIFEST` clause; it
had not — the block lived only in `publish.py`, its tests and the ODD entry. The follow-up
commit adds the clause, its scenario and the matching clause in the archived delta, D3b,
the CLI help and both READMEs. The same round found a real hole with behaviour behind it: a
record still promising a recursive tree the delivery no longer holds was not detected, and
the verifier showed the upload succeeding without the tree. `_delivery_divergence` now
compares the *presence* of every publishable entry, trees included, and the case is pinned
by a test. One under-declaration the rule cannot enforce is now stated instead of implied:
a `keep_csv` upload adds the original CSVs from the configuration, so the record never
declared them and the comparison must not refuse on that account.

**Found while verifying #349, recorded as out of scope (separate issues):**

- **The `! MISSING` rows of the dry-run plan are unreachable.** `publish.py:446-459`
  nests them under `if modified:`; the dry-run path is the only one that passes a
  manifest and it passes `existing_files=[]` (`publish.py:867-876`), so `modified` is
  always empty, while the confirm path passes no manifest at all
  (`publish.py:975-983`). The plan the human approves therefore never discloses the
  required-missing artifacts, and its only "evidence" is a unit test that injects
  existing files.
- **`codebooks_required` is dead in production.** `publish.py:768` defaults it to
  `False` and no caller passes `True`, so a missing `codebook_page` can never block.
- **PUB-12's own `error_code` clause is pre-existing drift** (note 6 above): the
  publish envelope has never carried that field.

## 4. Commits

| Commit | Subject |
| --- | --- |
| `d05acd4` | `fix(manifest): refresh the durable manifest at every phase that adds package artifacts (#349)` |
| `3ed11cf` | `fix(publish): plan and enforce against the durable manifest (#349)` |
| `57dd0a7` | `docs: declare the durable manifest as the object of record (#349)` |
| this commit | `chore(odd): archive the change inside its delivery branch (#349)` |
