# Tasks: fix-scan-registered-count

**Change** `2026-10-18-fix-scan-registered-count` (GitHub **#345**) · branch
`fix/345-scan-registered-count` from `dev@c68e090` · store **hybrid**.

**One-line outcome:** `registered` (both MCP scan tools) and `Registered N new
[[file]] entry(s).` (CLI) report the number of entries the merge actually
appended, so a greenfield scan of N files says N and an idempotent re-scan says 0.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real
red-then-green for each surface:

- **RED (MCP):** with the pre-fix `src/` restored, a fresh `sofer_init` tree plus
  N loose CSV files reports `registered: N - 2`; the new tests fail on
  `assert 3 == 5` (two init placeholders) for both `sofer_scan_dry_run` and
  `sofer_scan_apply`.
- **RED (CLI):** an init-style TOML (`raw/example.csv`, `raw/example/`) plus N
  loose files prints `Registered 0 new [[file]] entry(s).` today.
- **GREEN:** the same selections pass with the change in place, and the
  idempotent re-scan reports `0` without a code path special-casing it.

```
$ uv run pytest tests/ -q
2483 passed, 9 skipped, 6 warnings in 114.44s        # baseline on dev@c68e090: 2476 passed, 9 skipped
```

The measured RED output and the full gate transcript are recorded verbatim in the
change's `archive-report.md`.

**Status:** implementation complete on `fix/345-scan-registered-count`; the branch
is not pushed and no PR exists — push and PR creation are the maintainer's
decision.

---

## Tasks

| # | Task | Spec | State |
| --- | --- | --- | --- |
| T1 | `scanner.merge_entries_counted` returns `(toml, added)`; `merge_entries` is a thin wrapper over it | S2 | done |
| T2 | `sofer_scan_dry_run` and `sofer_scan_apply` report the counted value; `registered` schema descriptions state the semantics | S1, S3 | done |
| T3 | `cli._cmd_scan` reports the counted value in `Registered N` and in the dry-run preview | S5 | done |
| T4 | Tests: MCP apply + dry-run on a fresh `sofer_init` tree, idempotent re-scan, CLI line, scanner unit test | S1, S4 | done |
| T5 | `scan` and `mcp-server` spec deltas; archive report | S1-S3 | done |
| T6 | Full gate set: `pytest`, `ruff check`, `ruff format --check`, `mypy`, `pyright`, `scanner.py` + `cli.py` at 100.00%, `scripts/check_test_mapping.py` | — | done |

## Work units

1. `fix(scan): count registered entries from the merge, not the pre-strip baseline (#345)`
   — T1, T2, T3, T5 (spec clauses for the rule).
2. `test(scan): pin the registered count on a fresh init tree (#345)` — T4.
3. `chore(odd): record the #345 task rows and the archive report` — T5, T6.
