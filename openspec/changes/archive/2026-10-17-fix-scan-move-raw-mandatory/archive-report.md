# Archive report — `2026-10-17-fix-scan-move-raw-mandatory`

> **Change** `2026-10-17-fix-scan-move-raw-mandatory` (issue **#339**) · branch
> `fix/339-scan-move-raw-mandatory` from `dev@ec511e7` · store **hybrid**.
> **Archived inside its own delivery PR** (AGENTS.md rule 15): the same PR that
> merges the code moves this folder from `openspec/changes/` to
> `openspec/changes/archive/`, so the change and its record travel together.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Phase 1 unconditional in `sofer_scan_apply` / `sofer_scan_dry_run`; `move_loose` removed | done | `grep -rn move_loose src/` → 0 hits; `TestScanMoveToRawPhase` 7 passed |
| T2 | Registration keyed by the owning root (`scanner.registration_path`) | done | `TestRegistrationPath` 4 passed; `merge_entries`, `copy_files`, `check_flatten_collisions` share it |
| T3 | `validate`/`prepare` refuse a `cache/`-only registration with no `raw/` source | done | `TestCacheOnlyRegistrationGate` 4 passed |
| T4 | Both scan adapters report those entries without rewriting the TOML | done | `TestStaleCacheRegistrations` 6 passed; `test_scan_reports_stale_cache_registration` in `tests/test_scanner.py` and `tests/test_mcp_server.py` |
| T5 | Mandate stated in the tool descriptions, CLI help and `_PHASED_INSTRUCTIONS` | done | tool descriptions, `cli.py` help, `mcp_server.py:195` |
| T6 | `scan` spec amended + delta recorded | done | `openspec/specs/scan/spec.md` SCN-01/SCN-02/SCN-07 + 4 scenarios; this folder's `specs/scan/spec.md` |
| T7 | Full gate set | done | see §2 |
| T8 | Commits, push, PR assigned to `@emiliodavola` | done in the delivery PR that carries this archive | PR body names the archive path (rule 11) |

## 2. Verification, verbatim

```
$ uv run pytest tests/ -q
2399 passed, 9 skipped, 6 warnings in 89.46s        # baseline on dev@ec511e7: 2380 passed, 9 skipped

$ uv run coverage run -m pytest   &&   uv run coverage report -m | tail -1
TOTAL                             7427    384   2786    173    94%      # floor 90

$ uv run coverage report --include="src/sofer/cli.py" --fail-under=100 -m     -> 100%
$ uv run coverage report --include="src/sofer/scanner.py" --fail-under=100 -m -> 100%

$ uv run ruff check src/ tests/ scripts/        -> All checks passed!
$ uv run ruff format --check src/ tests/        -> 79 files already formatted
$ uv run mypy src/ scripts/                     -> Success: no issues found in 40 source files
$ uv run pyright                                -> 0 errors, 1 warning (pre-existing tomli module-source)
$ uv run python scripts/check_test_mapping.py   -> OK: test-mapping contract holds
```

RED was observed before each GREEN, against the pre-fix source (`git stash` of
`scanner.py`, `cli.py`, `mcp_server.py`):

```
$ uv run pytest "tests/test_mcp_server.py::TestScanMoveToRawPhase" -q
E  assert 0 == 1 where 0 = envelope.get('moved')
E  assert 'raw/loose.csv' in 'Phase 1 - 1 loose file(s) outside raw//cache/ would be moved into raw/
   on apply with move_loose=True. ...'

$ uv run pytest tests/test_scanner.py -q
E  ImportError: cannot import name 'registration_path' from 'sofer.scanner'
E  assert report.passed is False        # the gate produced no error before it existed
```

## 3. Specs of record

- `openspec/specs/scan/spec.md` — SCN-01, SCN-02 and SCN-07 modified in place; four
  scenarios added. `scan` is a permanent declared-backlog spec
  (`openspec/test-mapping-registry.md:41`), so no `## Test Mapping` row is owed and
  the registry was not edited.

## 4. Deferred, and why

- **A repair command for configs a pre-fix scan doubled** (D5): the fix stops creating
  the duplicates and reports them, but rewriting a generated config is its own change
  with its own risk.
- **`check_flatten_collisions` is unreachable inside the scan flow** now that the move
  is unconditional: two distinct sources cannot share a key once every file lives under
  `raw/`. The guard stays for mixed-root callers, its unit test was rewritten to that
  input, and the reachable collision is the `raw/` one Phase 1 aborts on. Removing it
  would be a spec change (SCN-06 names it), so it was kept.

## 5. Behaviour change for existing users

A config whose `[[file]]` entries point into `cache/` with no `raw/` source now fails
`validate` (exit 1) until it is re-scanned. That is the requested fail-closed
behaviour, the message names the repair, and it belongs in the release notes for the
next tag (rule 12).
