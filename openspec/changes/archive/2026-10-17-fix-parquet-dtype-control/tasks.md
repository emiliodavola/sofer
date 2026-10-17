# Tasks: fix-parquet-dtype-control

**Change** `2026-10-17-fix-parquet-dtype-control` (GitHub **#337**) · branch
`fix/337-parquet-dtype-control` from `dev@a7f631e` · store **hybrid**.

**One-line outcome:** `column_types` forces named columns past pyarrow's
inference, zero-padded code columns are protected automatically, and any value
the conversion would still change fails `prepare` (exit 1) instead of shipping —
with `validate` reporting the same finding before the conversion runs.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a measured
red-then-green per half, against the pre-fix source (`git stash` of
`_converters.py`, `model.py`, `config.py`, `prepare.py`, `checks.py`):

```
$ uv run pytest "tests/test_prepare.py::TestPrepareValueParity" -q
E  assert DataType(int64) == DataType(string)
E     where DataType(int64) = pyarrow.Field<IDDPTO: int64>.type
E  assert 0 == 1                      # the altered value shipped with exit 0
E  TypeError: FileEntry.__init__() got an unexpected keyword argument 'column_types'
4 failed, 1 passed

$ uv run pytest "tests/test_checks.py::TestColumnValueParityWarning" -q
E  assert False = any(<generator ...>)   # no warning named the column
2 failed, 2 passed

$ uv run pytest tests/test_converters.py -q
E  ImportError: cannot import name 'leading_zero_columns'
```

GREEN with the change in place: the same selections pass.

---

## Tasks

| # | Task | Spec | State |
| --- | --- | --- | --- |
| T1 | `[[file]] column_types`: parse, vocabulary in `config`, validation naming the accepted set | S2 | done |
| T2 | `leading_zero_columns` probe, bounded by `[tool.sofer] leading_zero_probe_rows` | S1, S4 | done |
| T3 | Thread the forced types into `pyarrow.csv.ConvertOptions`, printed per decision | S1, S2 | done |
| T4 | Structured parity pairs + `ValueAlterationError`, re-raised past the CSV fallback | S1, S5 | done |
| T5 | `prepare` reports and fails (exit 1) without delivering the file | S5 | done |
| T6 | `validate` predicts the finding as a warning, skipping declared columns | S5 | done |
| T7 | Spec, README pair, `prepare` help text | S1-S6 | done |
| T8 | Full gate set: pytest, ruff, mypy, pyright, coverage with the rule-14 rows | — | done |
| T9 | Commit slices, push, PR against `dev` assigned to `@emiliodavola` | — | done |

## Work units

1. `feat(prepare): a declared column type keeps zero-padded codes intact (#337)`
   — T1, T2, T3, T7.
2. `fix(prepare): an unauthorized value alteration fails the run (#337)`
   — T4, T5, T6.
