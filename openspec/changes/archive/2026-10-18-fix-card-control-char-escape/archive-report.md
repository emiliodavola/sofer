# Archive report — `2026-10-18-fix-card-control-char-escape`

> **Change** `2026-10-18-fix-card-control-char-escape` (issue **#348**) · branch
> `fix/348-card-control-char-escape`, rebased onto `dev@d07557e` (the merge of
> PR #350) · store **hybrid**.
> **Archived inside its own delivery branch** (AGENTS.md rule 15): the branch that
> carries the code also carries this folder's move into `openspec/changes/archive/`.
> The branch is not pushed and no PR exists yet — push and PR creation are the
> maintainer's decision.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | `_md_visible` + `_md_cell` in `repo_compliance.py` | done | `src/sofer/repo_compliance.py`; `TestCardDataCellsArePrintable` 5 passed |
| T2 | Both Data Fields branches render through one shared row builder, data-derived cells escaped | done | `_data_fields_row`; the duplicated per-branch f-string is gone; the pre-existing `TestDataFieldsFileColumn` still passes |
| T3 | Tests: no raw control byte, a pipe cannot split the row, a backtick keeps the value, ordinary values unchanged | done | 5 new tests; see §2 RED/GREEN |
| T4 | RC-R21 clause + RC-R21.10/.11 in the canonical spec, the delta and this report | done | `openspec/specs/repo-compliance/spec.md`; this folder's `specs/repo-compliance/spec.md` |
| T5 | Full gate set | done | see §2 |

**Commits**

| Commit | Subject |
| --- | --- |
| `d69aa86` | `fix(card): escape data-derived cells so the card stays text (#348)` |
| `bc2dead` | `docs(specs): declare the printable-cell contract (RC-R21, #348)` |
| this commit | `chore(odd): record the #348 work units and archive the change inside the branch` |

## 2. Verification, verbatim

**RED, observed before the fix was written** (pre-fix `src/`, new tests in place):

```
$ uv run pytest tests/test_repo_compliance.py -k TestCardDataCellsArePrintable -q
E       AssertionError: assert '`a\\|b`' in '---\ndataset_info:\n ... '
E       AssertionError: assert '``a`b``' in '---\ndataset_info:\n ... '
4 failed, 1 passed, 234 deselected in 1.22s
```

**End-to-end differential, same corpus, on the real artifact** — a one-row CSV
whose only value is a NUL byte, rendered through `sofer init` → `scan` → `prepare`:

| code | card bytes | NUL bytes in the card | Example cell |
| --- | --- | --- | --- |
| previous (`dev`) | 1725 | 1 | *(no escape)* |
| this change | 1728 | 0 | `\x00` |

```
$ (measured with `tr -cd '\000' < build/README.md | wc -c`, after the first
   attempt used `grep $'\x00'`, which bash expands to an empty pattern and which
   therefore counted every line instead of the NUL byte — corrected here)
```

The Parquet keeps the value, as #348 requires: the same corpus still holds 53 NUL
bytes in `build/cpv2022.parquet`. The defect was in the document generator, never
in the data.

**GREEN and the gate battery, on the rebased base** (`dev@d07557e`, i.e. with
#345 already merged):

```
$ uv run pytest <both changes' tests> -q
24 passed in 2.16s

$ uv run pytest tests/ -q
2488 passed, 9 skipped, 6 warnings in 98.52s (0:01:38)
# baseline dev@c68e090: 2476 passed, 9 skipped; +7 from #345, +5 from this change

$ uv run coverage run -m pytest            -> exit 0
$ uv run coverage report --include="src/sofer/scanner.py" --fail-under=100 -m  -> 100%
$ uv run coverage report --include="src/sofer/cli.py" --fail-under=100 -m      -> 100%
$ uv run coverage report -m | tail -1
TOTAL                             7666    391   2888    175    94%      # config floor 90

$ uv run ruff check src/ tests/ scripts/        -> All checks passed!
$ uv run ruff format --check src/ tests/        -> 79 files already formatted
$ uv run --python 3.13 mypy src/ scripts/       -> Success: no issues found in 40 source files
$ uv run pyright                                -> 0 errors, 1 warning
                                                    (pre-existing: src/sofer/_toml.py:27 tomli module source)
$ uv run python scripts/check_test_mapping.py   -> OK: test-mapping contract holds
```

## 3. Deviations, recorded honestly

1. **One regression caught mid-change.** The first version fenced the `File` cell
   with backticks, where the card has always printed the origin bare. The
   pre-existing `TestDataFieldsFileColumn::test_card_renders_file_column` failed on
   `assert '| \`v\` | numeric | survey.parquet | No |' in result`. The File cell now
   uses `_md_visible` (escaped, unfenced) and only the name and Example cells use
   `_md_cell`. This is exactly the "existing behaviour that shares the code you
   changed" case, and the test is the proof it was caught rather than shipped.
2. **An invalid verification of my own was corrected.** The first end-to-end NUL
   check used `grep $'\x00'`, which bash expands to an empty pattern; it reported
   "98 NULs / binary" for a file with zero NUL bytes. Every NUL figure above comes
   from `tr -cd '\000' | wc -c`.
3. **The branch needed a rebase, and the evidence was re-taken after it.** The
   first full-suite run (2481 passed) happened before PR #350 merged, i.e. against
   a tree without #345. The authoritative numbers in §2 were measured on
   `dev@d07557e`.
4. **No README change.** The READMEs do not document the card's table cells, so
   rules 7 and 13 owe no edit here.
