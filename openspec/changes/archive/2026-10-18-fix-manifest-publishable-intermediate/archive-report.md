# Archive report — `2026-10-18-fix-manifest-publishable-intermediate`

> **Change** `2026-10-18-fix-manifest-publishable-intermediate` (issue **#346**) ·
> branch `fix/346-manifest-publishable-intermediate`, rebased onto `dev@e23a6e8`
> (the merge of PR #351) · store **hybrid**.
> **Archived inside its own delivery branch** (AGENTS.md rule 15). Push and merge
> are the maintainer's decision.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | `ArtifactClass` on every entry, serialized, defaulted on read | done | `test_every_entry_carries_an_explicit_classification`, `test_manifest_without_classification_reads_as_publishable` |
| T2 | `publishable()` / `intermediate()` / `delivered()` | done | `test_delivered_set_is_the_staged_set` |
| T3 | Layer probe at the artifact cache with the dataset-root fallback | done | `test_layer_probe_reads_the_artifact_cache`, `test_layer_probe_still_reads_the_dataset_root`, `test_layer_outside_the_root_is_reported_without_raising` |
| T4 | Tests | done | `tests/test_manifest.py` 14 passed |
| T5 | PUB-12 clause + scenarios + PRP-11 drift + this report | done | `openspec/specs/publish/spec.md`, `openspec/specs/prepare/spec.md`, this folder's delta |
| T6 | Gate set | done | see §2 |
| T7 | A recursive tree is a directory entry, never a delivered file | done | `test_recursive_tree_is_a_directory_entry_never_a_delivered_file` (found by the verifier, see §3) |

**Commits**

| Commit | Subject |
| --- | --- |
| `b8c5e9d` | `fix(manifest): classify every artifact publishable or intermediate (#346)` |
| `c87a43c` | `docs(specs): declare the PUB-12 classification boundary (#346)` |
| `5c3925e` | `chore(odd): record the #346 work units and archive the change inside the branch` |
| `7bde2b9` | `test(manifest): pin the out-of-root layer probe fallback (#346)` |
| `e565331` | `fix(manifest): a recursive tree is a directory entry, never a delivered file (#346)` |
| `bc67a3c` | `docs(specs): scope the delivered set to file entries and fix the prepare drift (#346)` |
| this commit | `chore(odd): record the independent verification round and the re-taken evidence` |

## 2. Verification, verbatim

**Before/after on the real artifact**, scratch probe against the pre-fix
`sofer.manifest` and against this change (prepared tree plus `cache/profiles` and
`cache/renders` as `profile_all`/`render_all` write them):

```
--- before ---------------------------------------------------------------
declared artifacts:      7
classification present:  False
profile  entry:           path='profiles/' status=optional      <- files were in cache/
render   entry:           path='renders/' status=optional
staged by _copy_package: 4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
publishable():           absent -- a reader must know which types are local-only

--- after ----------------------------------------------------------------
declared artifacts:      7
classification present:  True
profile  entry:           path='cache/profiles/data.metadata.yaml' status=staged
render   entry:           path='cache/renders/data.README.md' status=staged
staged by _copy_package: 4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
publishable():           5
delivered():             4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
delivered == staged:     True
```

The 5-vs-4 line is why `delivered()` exists: `publishable()` alone counts an absent
optional `codebook.md` as part of the delivery, the same overstatement #346 reports,
one artifact smaller.

**The recursive-tree case** (the verifier's counterexample, re-measured after the
fix in `e565331`):

```
--- before the fix -------------------------------------------------------
entry: path='assets' status=staged class=publishable
entry: path='empty'  status=staged class=publishable
delivered(): ['LICENSE', 'README.md', 'assets', 'empty']
staged files: ['LICENSE', 'README.md', 'assets/a.txt', 'assets/nested/b.txt']

--- after the fix --------------------------------------------------------
entry: path='assets/' status=staged class=publishable
entry: path='empty/'  status=staged class=publishable
delivered(): ['LICENSE', 'README.md']
staged files: ['LICENSE', 'README.md', 'assets/a.txt', 'assets/nested/b.txt']
```

**Gates, on the rebased base** (`dev@e23a6e8`, with #345 and #348 merged):

```
$ uv run pytest tests/test_manifest.py -q
14 passed in 1.14s

$ uv run pytest tests/ -q
2495 passed, 9 skipped, 6 warnings in 97.85s (0:01:37)
# baseline dev@c68e090: 2476 passed, 9 skipped; +7 from #345, +5 from #348, +7 from this change

$ uv run coverage run -m pytest            -> exit 0
$ uv run pytest tests/test_coverage_contract.py -q                 -> 9 passed
$ uv run coverage report --include="src/sofer/publish.py"  --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report --include="src/sofer/scanner.py"  --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report --include="src/sofer/cli.py"      --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report --include="src/sofer/prepare.py"  --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report -m | tail -1
TOTAL                             7686    392   2888    175    94%      # config floor 90

$ uv run ruff check src/ tests/ scripts/        -> All checks passed!
$ uv run ruff format --check src/ tests/        -> 79 files already formatted
$ uv run --python 3.13 mypy src/ scripts/       -> Success: no issues found in 40 source files
$ uv run pyright                                -> 0 errors, 1 warning
                                                    (pre-existing: src/sofer/_toml.py:27 tomli module source)
$ uv run python scripts/check_test_mapping.py   -> OK: test-mapping contract holds
```

## 3. Independent verification round

The `assess` entry point was unavailable (`package-local-binary-missing`, and it
reported `changedPaths: 0`, so it said nothing about the candidate), so an
independent `gentle-ai-verify` ran against five explicit claims. Its verdict:

| Claim | Verdict |
| --- | --- |
| 1 backward compat + byte-stable roundtrip | PASS (caveat: a legacy `profile`/`render` entry defaults to `publishable`) |
| 2 `delivered()` == the staged set | **FAIL** — true only for non-recursive fixtures |
| 3 no consumer breaks | PASS in code; **doc drift** in `openspec/specs/prepare/spec.md` (PRP-11) |
| 4 probe cannot crash `prepare` | PASS; `except ValueError` **uncovered in the commit**; symlink/unreadable behaviour unverified |
| 5 blocking rule untouched | PASS |

What the FAIL was: the manifest records ONE entry per recursive remote, so
`delivered()` listed `assets` and an empty `empty` while the copy path staged
`assets/a.txt` and `assets/nested/b.txt`. The empty tree reported an artifact that
stages zero files — the exact overstatement #346 exists to remove, reintroduced by
the new derived set. I had generalized the identity from a non-recursive fixture.

What changed because of it: `e565331` (directory entries carry a trailing slash,
`ManifestEntry.is_directory`, `delivered()` excludes them, one test with a populated
tree and an empty tree) and `bc67a3c` (the claim narrowed to "publishable AND staged
AND a file path" in the canonical spec, the delta and the design; PRP-11 updated
with `classification` and the directory-path convention). The legacy-default caveat
from claim 1 is now stated in PUB-12 as well.

The verifier also flagged a process blocker worth keeping: it observed
`tests/test_manifest.py` change **during** its run, because I was editing the tree
while it was reading it. Verification must target a frozen commit — which is what
the follow-up run does.

## 4. Deviations, recorded honestly

1. **Test-first did not hold for the initial unit.** The implementation came before
   the tests. The first RED (`ImportError: cannot import name 'ArtifactClass'` at
   collection) was too weak to be the carrier, so the recorded evidence is the
   measured before/after probe in §2.
2. **The probe caught a defect before shipping.** The first version made
   `publishable()` the delivery set, which over-declared like #346
   (`publishable 5` against `staged 4`).
3. **The bug is not fully absent from the manifest's history:** `publish.py` needed
   no change (`required_missing()` is its only manifest reader, and intermediate
   entries are never `missing`), but the *manifest reader* PUB-12 describes is still
   unimplemented — that is #349, deliberately out of scope.
4. **The branch was rebased and the evidence re-taken** on `e23a6e8`; the earlier
   base (`d07557e`) lacked #348 and was not used as evidence.
5. **One commit attempt was aborted by a hook/stash conflict** (the `ruff-format`
   hook rewrote a line also inside pre-commit's stash); recovery was to stage the
   formatted version, never `--no-verify`.
6. **I invalidated the local coverage base and mis-read the result.** A
   `coverage run --branch -m pytest tests/test_manifest.py` (subset) overwrote
   `.coverage`, and `tests/test_coverage_contract.py` then failed a clean suite with
   `profile.py measured 52.7%`. `.coverage` is gitignored, so nothing reached the
   repo; repaired by re-running the full suite under coverage. Subset measurements in
   this repo must use `coverage run --data-file=<scratch>`.
7. **The claim was over-general when first written** (see §3): corrected in code,
   spec, delta and design after the verifier falsified it.
