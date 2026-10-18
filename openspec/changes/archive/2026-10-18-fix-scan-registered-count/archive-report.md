# Archive report — `2026-10-18-fix-scan-registered-count`

> **Change** `2026-10-18-fix-scan-registered-count` (issue **#345**) · branch
> `fix/345-scan-registered-count` from `dev@c68e090` · store **hybrid**.
> **Archived inside its own delivery branch** (AGENTS.md rule 15): the branch that
> carries the code also carries this folder's move into `openspec/changes/archive/`,
> so the change and its record travel together. The branch is not pushed and no PR
> exists yet — push and PR creation are the maintainer's decision.

---

## 1. What shipped

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | `scanner.merge_entries_counted` returns `(toml, added)`; `merge_entries` is a thin wrapper | done | `src/sofer/scanner.py`; `TestMergeEntries` 19 passed (12 pre-existing + 2 new + 5 counted-arc tests) |
| T2 | Both MCP scan tools report the merge's count; `registered` schema descriptions state the semantics | done | `src/sofer/mcp_server.py` (`_REGISTERED_FIELD_DESCRIPTION`, two `output_schema` blocks); `TestScanRegisteredCount` 3 passed |
| T3 | CLI reports the merge's count in `Registered N` and in the dry-run preview | done | `src/sofer/cli.py:645-650`; `TestScanCountWithInitPlaceholders` 2 passed |
| T4 | Tests: MCP apply + dry-run on a fresh `sofer_init` tree, idempotent re-scan, CLI lines, scanner unit tests | done | 7 new tests; see §2 RED/GREEN |
| T5 | `scan` and `mcp-server` spec clauses + this archive report | done | `openspec/specs/scan/spec.md` SCN-04, `openspec/specs/mcp-server/spec.md` MSP-R15, and this folder's two deltas |
| T6 | Full gate set | done | see §2 |

**Commits**

| Commit | Subject |
| --- | --- |
| `b6f2d56` | `fix(scan): count registered entries from the merge, not the pre-strip baseline (#345)` |
| `0decb63` | `docs(specs): declare the #345 registered-count contract (SCN-04, MSP-R15)` |
| this commit | `chore(odd): record the #345 work units and archive the change inside the branch` |

## 2. Verification, verbatim

**RED, observed before the fix was written** (pre-fix `src/`, new tests in place):

```
$ uv run pytest tests/test_scanner.py -k counted_merge -q
E   ImportError: cannot import name 'merge_entries_counted' from 'sofer.scanner'
    (…\src\sofer\scanner.py)
1 error in 0.46s

$ uv run pytest tests/test_mcp_server.py -k TestScanRegisteredCount -q
>       assert first["registered"] == 5, first
E       assert 3 == 5
3 failed, 306 deselected in 1.99s

$ uv run pytest tests/test_cli.py -k TestScanCountWithInitPlaceholders -q
>       assert "DRY RUN  Would register 3 new [[file]] entry(s)." in out
E       AssertionError: … 'DRY RUN  Would register 1 new [[file]] entry(s).\n'
2 failed, 243 deselected in 2.38s
```

The MCP and CLI numbers are the reported defect exactly: `N - 2`, where 2 is the
number of `raw/example*` placeholders `sofer_init` writes.

**GREEN and the gate battery** (after the fix, on this branch):

```
$ uv run pytest <the 7 tests of this change> -q
7 passed in 1.15s

$ uv run pytest tests/ -q
2483 passed, 9 skipped, 6 warnings in 114.44s (0:01:54)      # baseline dev@c68e090: 2476 passed, 9 skipped

$ uv run coverage run -m pytest            -> exit 0
$ uv run coverage report --include="src/sofer/scanner.py" --fail-under=100 -m
src\sofer\scanner.py     196      0     88      0   100%
$ uv run coverage report --include="src/sofer/cli.py" --fail-under=100 -m
src\sofer\cli.py     741      0    226      0   100%
$ uv run coverage report -m | tail -1
TOTAL                             7657    391   2888    175    94%      # config floor 90

$ uv run ruff check src/ tests/ scripts/        -> All checks passed!
$ uv run ruff format --check src/ tests/        -> 79 files already formatted
$ uv run --python 3.13 mypy src/ scripts/       -> Success: no issues found in 40 source files
$ uv run pyright                                -> 0 errors, 1 warning
                                                    (pre-existing: src/sofer/_toml.py:27 tomli module source)
$ uv run python scripts/check_test_mapping.py   -> OK: test-mapping contract holds
```

The `+7` over baseline is exactly this change's new tests; no pre-existing test
changed state. The differential check for the touched shared code is the suite
itself: `merge_entries` keeps its dict-only contract and its callers and tests are
unmodified, while `merge_entries_counted` adds the count the same merge computed.

## 3. Deviations, recorded honestly

1. **One test was rewritten after its first RED.** The initial CLI dry-run test
   asserted a registration preview after loose candidates, which is unreachable by
   design: `scan --dry-run` returns right after the MOVE preview when loose files
   exist (`cli.py:572-579`), so Phase 2 — and its `Would register N` line — only
   runs with sources already under `raw/`. The test now stages the files under
   `raw/` and RED was re-observed on that path (`Would register 1` for 3 files).
2. **The gate battery was not delegated.** Two `gentle-ai-worker` launches were
   refused with `Writer session Git authority changed before admission` (the
   session started on `main`; this work is on a branch). The native `Agent`
   fallback is not available in this environment, so the battery ran inline and is
   reported above. Reported as unavailable, not retried further.
3. **No README change.** `README.md` and `README_ES.md` do not state the
   registration count, so rules 7 and 13 owe no edit here.
