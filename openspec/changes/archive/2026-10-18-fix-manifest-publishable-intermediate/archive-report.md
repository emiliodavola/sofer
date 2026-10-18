# Archive report — `2026-10-18-fix-manifest-publishable-intermediate`

> **Change** `2026-10-18-fix-manifest-publishable-intermediate` (issue **#346**) ·
> branch `fix/346-manifest-publishable-intermediate`, rebased onto `dev@e23a6e8`
> (the merge of PR #351) · store **hybrid**.
> **Archived inside its own delivery branch** (AGENTS.md rule 15). The branch is
> not pushed and no PR exists yet — push and PR creation are the maintainer's
> decision.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | `ArtifactClass` on every entry, serialized, defaulted on read | done | `src/sofer/manifest.py`; `test_every_entry_carries_an_explicit_classification`, `test_manifest_without_classification_reads_as_publishable` |
| T2 | `publishable()` / `intermediate()` / `delivered()` | done | `test_delivered_set_is_the_staged_set` |
| T3 | Layer probe at the artifact cache with the dataset-root fallback | done | `test_layer_probe_reads_the_artifact_cache`, `test_layer_probe_still_reads_the_dataset_root` |
| T4 | 5 new tests | done | `tests/test_manifest.py` 12 passed |
| T5 | PUB-12 clause + three scenarios + this report | done | `openspec/specs/publish/spec.md`; this folder's delta |
| T6 | Gate set | done | see §2 |

**Commits**

| Commit | Subject |
| --- | --- |
| `b8c5e9d` | `fix(manifest): classify every artifact publishable or intermediate (#346)` |
| `c87a43c` | `docs(specs): declare the PUB-12 classification boundary (#346)` |
| this commit | `chore(odd): record the #346 work units and archive the change` |

## 2. Verification, verbatim

**Before/after on the real artifact**, via a scratch probe (`.tmp-wu3/probe.py`,
deleted after use) run against the pre-fix `sofer.manifest` and against this
change, on a prepared tree plus `cache/profiles` and `cache/renders` as
`profile_all`/`render_all` write them:

```
--- A. pre-fix -----------------------------------------------------------
declared artifacts:      7
classification present:  False
profile  entry:           path='profiles/' status=optional      <- files were in cache/
render   entry:           path='renders/' status=optional
staged by _copy_package: 4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
publishable():           absent -- a reader must know which types are local-only

--- B. this change -------------------------------------------------------
declared artifacts:      7
classification present:  True
profile  entry:           path='cache/profiles/data.metadata.yaml' status=staged
render   entry:           path='cache/renders/data.README.md' status=staged
staged by _copy_package: 4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
publishable():           5
delivered():             4 -> ['LICENSE', 'README.md', 'codebooks/data.md', 'data.parquet']
delivered == staged:     True
```

The 5-vs-4 line is the whole point of the `delivered()` selector: `publishable()`
alone counts an absent optional `codebook.md` as part of the delivery, which is the
same overstatement #346 reports, one artifact smaller.

**Gates, on the rebased base** (`dev@e23a6e8`, i.e. with #345 and #348 merged):

```
$ uv run pytest tests/test_manifest.py -q
12 passed in 3.32s

$ uv run pytest tests/ -q
2493 passed, 9 skipped, 6 warnings in 134.11s (0:02:14)
# baseline dev@c68e090: 2476 passed, 9 skipped; +7 from #345, +5 from #348, +5 from this change

$ uv run coverage run -m pytest            -> exit 0
$ uv run coverage report --include="src/sofer/publish.py"  --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report --include="src/sofer/scanner.py"  --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report --include="src/sofer/cli.py"      --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report --include="src/sofer/prepare.py"  --fail-under=100 -m -> exit 0, 100%
$ uv run coverage report -m | tail -1
TOTAL                             7682    394   2888    176    94%      # config floor 90

$ uv run ruff check src/ tests/ scripts/        -> All checks passed!
$ uv run ruff format --check src/ tests/        -> 79 files already formatted
$ uv run --python 3.13 mypy src/ scripts/       -> Success: no issues found in 40 source files
$ uv run pyright                                -> 0 errors, 1 warning
                                                    (pre-existing: src/sofer/_toml.py:27 tomli module source)
$ uv run python scripts/check_test_mapping.py   -> OK: test-mapping contract holds
```

## 3. Deviations, recorded honestly

1. **Test-first did not hold for this unit.** The implementation was written before
   the tests. The first RED attempt was an `ImportError: cannot import name
   'ArtifactClass'` at collection — a real failure but weak evidence — so the
   recorded carrier is the measured before/after probe in §2, not a RED test file.
   `publish.py`, the module the issue names, needed no change: `required_missing()`
   is its only manifest reader and intermediate entries are never `missing`.
2. **The probe caught a defect in this change before it shipped.** The first version
   made `publishable()` the delivery set, which over-declared exactly like #346
   (`publishable 5` against `staged 4`) because an absent optional `codebook.md` is
   publishable in principle. `delivered()` — publishable ∧ staged — was added, and
   the test asserts it against the real copy-path output.
3. **The branch was rebased and the evidence re-taken.** `git rebase origin/dev`
   replayed `b8c5e9d` onto `e23a6e8` after PR #351 merged; the manifest tests and
   the whole battery above were run there. The earlier base (`d07557e`) lacked #348
   and was not used as evidence.
4. **The first commit attempt was aborted by a hook/stash conflict.** The
   `ruff-format` hook rewrote a line that was also inside pre-commit's stash of
   unstaged changes, so pre-commit rolled the fixes back and no commit was created.
   Recovery was to stage the formatted worktree version so index and worktree agree,
   then commit — never `--no-verify`.
5. **No README change.** The READMEs do not document `manifest.json`'s field list, so
   rules 7 and 13 owe no edit here. (The manifest is documented by the PUB-12 spec,
   amended above.)
