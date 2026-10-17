# Archive report — `2026-10-17-fix-parquet-dtype-control`

> **Change** `2026-10-17-fix-parquet-dtype-control` (issue **#337**) · branch
> `fix/337-parquet-dtype-control` from `dev@a7f631e` · store **hybrid**.
> **Archived inside its own delivery PR** (AGENTS.md rule 15): the same PR that
> merges the code moves this folder from `openspec/changes/` to
> `openspec/changes/archive/`, so the change and its record travel together.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Zero-padded column survives the conversion | done | RED: `assert DataType(int64) == DataType(string)`, `IDDPTO: [[1,2]]`. GREEN: `TestPrepareValueParity::test_zero_padded_codes_survive_prepare` |
| T2 | `column_types` forces the dtype; an unknown type is refused naming the set | done | RED: `TypeError: FileEntry.__init__() got an unexpected keyword argument 'column_types'`. GREEN: `TestColumnTypeControl` (6) + `TestFileColumnTypes` (4) |
| T3 | A residual alteration fails `prepare` instead of shipping | done | RED: `assert 0 == 1` on the exit code. GREEN: `test_residual_alteration_fails_prepare`, `test_residual_alteration_raises_instead_of_shipping` |
| T4 | `validate` predicts the finding from the source alone | done | RED: `assert False = any(<generator ...>)`. GREEN: `TestColumnValueParityWarning` (4) |
| T5 | `convert_to_parquet = false` still wins (precedence) | done | `test_convert_to_parquet_false_wins_over_column_types` |
| T6 | `ConvertOptions` threading | done | `convert_options` passed only when something is forced (PC-U01 call shape kept) |
| T7 | Bounded leading-zero probe | done | `TestLeadingZeroProbe` (7): detection, non-code guard, empty cells, row budget |
| T8 | Structured parity finding + fatal residue | done | `_check_conversion_parity` out-parameter (D6), `ValueAlterationError` re-raised past the CSV fallback (D4) |
| T9 | Spec + delta | done | `openspec/specs/parquet-conversion/spec.md` §7.2 rewritten, §7.4 added, five scenarios |
| T10 | README pair + `prepare` help text | done | README/README_ES footnote ², `cli.py` subcommand description |
| T11 | Full gate set, commits, push, PR | done — PR [#341](https://github.com/emiliodavola/sofer/pull/341) | see §2 of this report |

## 2. Verification, verbatim

```
$ uv run pytest tests/ -q
2426 passed, 9 skipped, 6 warnings in 89.90s

$ uv run coverage run -m pytest -q   &&   uv run coverage report -m | tail -1
TOTAL                             7543    387   2840    176    94%      # floor 90

$ uv run coverage report --include="src/sofer/cli.py" --fail-under=100 -m      -> 100%
$ uv run coverage report --include="src/sofer/scanner.py" --fail-under=100 -m  -> 100%
$ uv run coverage report --include="src/sofer/prepare.py" --fail-under=100 -m  -> 100%
$ uv run coverage report --include="src/sofer/publish.py" --fail-under=100 -m  -> 100%

$ uv run ruff check src/ tests/ scripts/        -> All checks passed!
$ uv run ruff format --check src/ tests/        -> 79 files already formatted
$ uv run mypy src/ scripts/                     -> Success: no issues found in 40 source files
$ uv run pyright                                -> 0 errors, 1 warning (pre-existing tomli module-source)
$ uv run python scripts/check_test_mapping.py   -> OK: test-mapping contract holds
```

RED was observed before each GREEN, against the pre-fix source (`git stash` of
`_converters.py`, `model.py`, `config.py`, `prepare.py`, `checks.py`); the verbatim
failures are in `tasks.md` and in the delivery PR body.

Measured library behaviour the design rests on (`tmp/verify-337/probe.py`):

```
inferred   : CODE: int64          PLUS: double
forced CODE: string ['001', '02']
residual   : PLUS [5.0, 6.0]      # "+5" is not zero-padded -> the fail-closed case
```

## 3. Specs of record

- `openspec/specs/parquet-conversion/spec.md` — §7.2 modified (the loss is no
  longer an accepted limitation), §7.4 added, five scenarios. The spec has no
  `## Test Mapping` section and is recorded as a permanent declared backlog
  (`openspec/test-mapping-registry.md:34`), so no row is owed and the registry was
  not edited.

## 4. Deferred, and why

- **`.tsv` has no dtype control.** Its converter uses a fixed tab delimiter and
  takes no `column_types`, so a code column in a TSV is still inferred. Extending
  the control there is a separate change to a converter this issue did not name.
- **The manifest schema is untouched** (D7). The finding is recorded in the
  `prepare` report, which is what the MCP envelope returns as `output`; adding a
  field to `PackageManifest` is a `prepare`/`manifest` schema change with its own
  spec delta and is not needed to record the posture.
- **The probe heuristic is first-N-rows.** A code column whose leading zero only
  appears past `leading_zero_probe_rows` is not auto-protected; the value check
  still catches it, so the outcome is a refusal naming the fix, never a silent
  alteration.

## 5. Behaviour change for existing users

A dataset with a zero-padded code column now delivers that column as `string`
instead of `int64` — the source form is the only correct delivery — and a value
the conversion would still change now fails `prepare` with a non-zero exit
instead of shipping. Both belong in the release notes for the next tag (rule 12),
and consumers that summed such a column must adapt.
