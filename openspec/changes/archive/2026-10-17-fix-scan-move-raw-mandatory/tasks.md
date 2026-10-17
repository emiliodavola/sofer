# Tasks: fix-scan-move-raw-mandatory

**Change** `2026-10-17-fix-scan-move-raw-mandatory` (GitHub **#339**) · branch
`fix/339-scan-move-raw-mandatory` from `dev@ec511e7` · store **hybrid**.

**One-line outcome:** both MCP scan tools run the Phase-1 move into `raw/`
unconditionally with no opt-in flag, every discovered file is keyed relative to
the root that owns it, and a `cache/`-only registration with no `raw/` source is
refused by `validate`/`prepare` and reported by both scan adapters.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real
red-then-green for each half:

- **RED (measured, move + key rule):** with the pre-fix `src/` restored
  (`git stash` of `scanner.py`, `cli.py`, `mcp_server.py`):
  `pytest "tests/test_mcp_server.py::TestScanMoveToRawPhase"` →
  `assert 0 == 1 where 0 = envelope.get('moved')`, the nested file absent from
  `raw/`, and the dry run advertising `move_loose`; `pytest tests/test_scanner.py`
  → `ImportError: cannot import name 'registration_path' from 'sofer.scanner'`.
- **GREEN:** the same selections pass with the change in place.
- **RED (measured, gate + report):** the gate tests were written against the
  pre-gate validator and fail with `assert report.passed is False` (no error is
  produced); the adapter tests fail on `"no raw/ source" not in output`.

---

## Tasks

| # | Task | Spec | State |
| --- | --- | --- | --- |
| T1 | Make Phase 1 unconditional in `sofer_scan_apply` and `sofer_scan_dry_run`; remove `move_loose`; keep the collision abort, the dry-run preview and the `force`/`extensions` surface | S1, S2, S5 | done |
| T2 | Key registration by the owning root: `scanner.registration_path` shared by `check_flatten_collisions`, `merge_entries`, `copy_files` | S3 | done |
| T3 | Refuse a `cache/`-only registration with a missing `raw/` source in `DatasetValidator`, naming the repair | S4 | done |
| T4 | Report those entries from both scan adapters, bounded by `report_max_items`, without rewriting the TOML | S3 | done |
| T5 | State the mandate in the tool descriptions, the CLI help and `_PHASED_INSTRUCTIONS` | S6 | done |
| T6 | Amend `openspec/specs/scan/spec.md` (SCN-01, SCN-02, SCN-07 + 3 scenarios) and both READMEs | S1-S6 | done |
| T7 | Full gate set: `pytest`, `ruff check`, `ruff format --check`, `mypy`, `pyright`, coverage with the rule-14 rows for `cli.py` and `scanner.py` at 100.00% | — | done |
| T8 | Commit slices, push, PR against `dev` assigned to `@emiliodavola` with `Closes #339` | — | pending |

## Work units

1. `fix(scan): moving sources into raw/ is mandatory in both scan tools (#339)`
   — T1, T2, T5, T6.
2. `fix(scan): refuse a cache-only registration with no raw/ source (#339)`
   — T3, T4, T6 (spec clause for S4).
