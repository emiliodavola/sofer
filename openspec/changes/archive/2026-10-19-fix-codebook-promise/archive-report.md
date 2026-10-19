# Archive report — `2026-10-19-fix-codebook-promise`

> **Change** `2026-10-19-fix-codebook-promise` · issue **#354** · branch
> `fix/354-codebook-promise` from `dev@150ead1` · store **hybrid** (this folder,
> the ODD doc `odd/tasks/codebook-promise.md` and its Engram mirror).
> **Archived inside its own delivery branch** (AGENTS.md rule 15). Push and the pull
> request were explicitly requested by the maintainer.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Feature doc, branch `fix/354-codebook-promise`, Engram mirror | done | `odd/tasks/codebook-promise.md`; topic `odd/codebook-promise/tasks` |
| T2 | RED first: tree-derived promise, empty-dir absence, sticky refresh, confirm refusal | done | four assertion failures observed before the implementation (3 in `tests/test_manifest.py`, 1 in `tests/test_publish.py::TestDurableManifest`) |
| T3 | `manifest.py` derives the promise from `codebook.md`; an empty `codebooks/` is an absence; the parameter is deleted from `build_package_manifest`, `write_manifest`, `refresh_manifest` | done | `7279485`; `tests/test_manifest.py` |
| T4 | `publish.py`: the parameter is deleted from `publish` and `_delivery_divergence`, both call sites updated | done | `7279485`; `rg codebooks_required src/ tests/ scripts/` → no match |
| T5 | PUB-12 delta and canonical spec; the tree-derived rule in `README.md` / `README_ES.md` | done | `0575a0e`; `openspec/specs/publish/spec.md` (PUB-12 + 3 scenarios) |
| T6 | Gates: full suite under coverage, the four 100.00% modules, ruff, mypy, pyright, `check_test_mapping.py`, differential check | done | §2 below |
| T7 | Independent verifier over the diff, then the native review assessment and its acknowledgement | done | §3 below; verifier PASS WITH ADVISORIES |
| T8 | Archive inside the branch; push; PR assigned to `emiliodavola` | done | this file; the archive commit |

**The change in one line:** the promise "this package carries codebooks" stopped
being a parameter nobody passed and became a fact of the package tree — an index
with no pages is `missing` and `publish` refuses with the chain that supplies them;
no index is `optional` and nothing is said.

## 2. Verification, verbatim

All commands run from the repository root on the frozen tree.

```
$ uv run pytest tests/ -q
2513 passed, 9 skipped
# base dev@150ead1: 2509 passed, 9 skipped  ->  +4 in tests/test_manifest.py
# and tests/test_publish.py, then +3 verifier-derived regression tests in
# tests/test_codebook_promise.py, written after the verifier ran.

$ uv run coverage run -m pytest tests/ -q ; uv run coverage report -m | tail -1
TOTAL                                                           94%   # floor 90

$ for f in cli scanner prepare publish; do
    uv run coverage report --include="src/sofer/$f.py" --fail-under=100 -m >/dev/null
    echo "$f exit=$?"; done
cli exit=0        scanner exit=0        prepare exit=0        publish exit=0
# each of the four modules measured 100.00%; manifest.py 99% (line 351,
# pre-existing at the base and outside this change's surface).

$ uv run ruff check src/ tests/ scripts/
All checks passed!
$ uv run ruff format --check src/ tests/
# all files already formatted

$ uv run mypy src/ scripts/
Success: no issues found
$ uv run pyright
0 errors  # 1 pre-existing tomli warning
$ uv run python scripts/check_test_mapping.py
OK: test-mapping contract holds             # exit 0; publish stays a declared-backlog spec
```

**Differential check** against a `dev@150ead1` worktree created outside the
repository, for the commands that share the code this change touches:

```
IDENTICAL  prepare            (manifest.json byte-identical after dropping the `source` path)
IDENTICAL  prepare --all-files
IDENTICAL  prepare + codebook_all
```

The only other difference was the imported module path, which proves the two runs
used different trees. The intended delta — promised and empty becomes `missing`
instead of `optional` — is pinned by the RED/GREEN tests, not by this comparison,
because the fixtures that reach it do not exist on the base.

## 3. Decisions and honest notes

**Why the tree and not the record.** `codebook.generate_all` always writes the root
`codebook.md` (`codebook.py:792`) but creates `codebooks/` only when it writes a page.
The pair therefore encodes both facts at once: index present + no pages = promised and
produced nothing; index absent = never promised. A sticky boolean in `manifest.json`
was rejected because #349's divergence rule compares the record against a recount of
the *same tree* — a field only the record knows would make the two sides structurally
unable to agree (design D1).

**Enforcement did not move.** `publish` already blocks on
`manifest.required_missing()` over the durable record. The change only makes the
record capable of carrying a `missing` codebook entry, then deletes the dead
parameter. The block, its recovery text and the dry-run/local warning behavior are
untouched (D4).

**Two breaks the issue does not name, both fixed rather than documented away:**

1. **The refresh downgrade.** `profile_all` and `render_all` run after `codebook_all`
   on the canonical chain and refresh the record. A parameter-based promise would
   have been downgraded back to `optional` by them even if a caller had passed the
   flag. Because the promise is recomputed from the tree on every build, no refresh
   can downgrade it and no call site needs to know it exists (S6, D3).
2. **The empty directory.** The previous probe was
   `if codebooks_dir.is_dir(): for page in rglob("*.md")`. A directory that exists
   with zero pages entered the branch, iterated nothing, and emitted no entry at
   all — neither `missing` nor `optional`, so no reader could see it. The probe now
   collects the pages first and treats "no pages" as the absence it is (S7, D2).

**Migration is the documented behavior.** A record written before this change says
`optional`, and `publish` reads the record as-is (PUB-12), so it does not block until
the build chain refreshes it. That is consistent with every other record-derived rule
from #349 and is stated in the spec delta instead of being special-cased in the reader
(D5).

**Test-first held for the four carrier cases.** They were written before the
implementation and observed RED as real assertion failures — not import errors. The
verifier's three non-duplicative probes landed afterwards as
`tests/test_codebook_promise.py`: the real `prepare --all-files` writer state, the
absence of the keyword in every signature, and the claim that an old `optional`
record is not a path divergence.

**Deviations and honest notes:**

1. **Delivery heuristic exceeded by documentation, not by behavior.** The coverage
   unit is 220 added lines (code + tests) in commit `7279485`; the rest of the diff is
   the spec delta, the ODD doc and this record. One coherent rule with its tests and
   docs stays one PR — no size-only split (ODD delivery heuristic, advisory).
2. **Native review was requested on the committed range** (`dev..HEAD`, committed
   only) with the risk, readability and reliability lenses, and its consent envelope
   was granted by the maintainer. Outcome: **approved**. Its findings were all
   non-blocking, and none is restated here as a defect because none named a required
   behavior change.
3. **Review advisories recorded, deliberately not fixed on this candidate:**

   - `R1-hardcoded-index-filename` — the literal `codebook.md` in
     `src/sofer/manifest.py:302-310` is the contract `codebook.generate_all` publishes,
     but it is a literal rather than a named constant; extracting one is a small
     follow-up with its own review.
   - `R1-old-records-still-ship-silently` — pre-fix records say `optional`, so an old
     tree keeps shipping without the pages until the chain refreshes it (D5). This is
     the declared migration, not an oversight; changing it would need a second source
     for the same fact.
   - `R2-1` — `test_the_promise_survives_the_later_phase_refreshes` asserts the
     derivation directly and does not invoke `profile_all`/`render_all`; the verifier
     probed those paths independently. Strengthening it into an end-to-end test is a
     test-only follow-up.
   - `R2-2` — `tasks.md` cited an archive report the branch did not yet carry; closed
     by this commit.
   - `R2-3` — the same hardcoded index name observation from the readability lens.
   - `R2-4`, `R2-5` — test docstring/style notes, no behavior.
   - `R3-001` — `prepare --all-files` exits 0 when a source is unreadable, leaving an
     index with no pages; `publish` then refuses and the printed recovery reproduces
     the state. The refusal is the requested #354 behavior; the silent success of the
     phase is a pre-existing `prepare` question, out of this change's scope.
   - `R3-002`, `R3-003` — non-blocking robustness observations; neither named a
     behavior change and neither reproduced as a defect, so neither is restated here.

**Found while implementing, recorded as out of scope (separate work):**

- The `! MISSING` rows of the dry-run plan remain unreachable (first recorded in the
  #349 archive report). This change blocks through `required_missing()`, not through
  the plan rows, so the human-visible plan still does not disclose the block.
- `manifest.py` line 351 remains the module's only uncovered line, pre-existing at the
  base.

## 4. Commits

| Commit | Subject |
| --- | --- |
| `7279485` | `fix(manifest): derive the codebook promise from the package tree (#354)` |
| `0575a0e` | `docs(specs): PUB-12 states the tree-derived codebook promise (#354)` |
| this commit | `chore(odd): archive the change inside its delivery branch (#354)` |
