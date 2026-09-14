# Apply Progress: fix-cli-codebook-config (issue #182)

**Change**: `2026-09-14-fix-cli-codebook-config` · **Issue**: #182 · **Branch**: `fix/182-cli-codebook-config`
**Store**: hybrid (this file + Engram topic key `sdd/2026-09-14-fix-cli-codebook-config/apply-progress`) ·
**Approach**: **Option B** as designed (unified reader via `_csv_reader.stream_csv`) · **Strict TDD**: off (`openspec/config.yaml`)
**Status**: all 19 apply checkboxes are `- [x]`; 0 remain unchecked. Verify gates are deferred to `verify`.

## Structured status consumed

`applyState: ready`, `artifactStore: openspec`, `actionContext.mode: repo-local`,
`allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`. Every target file is inside that root, so no
`blocked` condition applied. Runtime gate: `gentle-ai sdd-attempt acquire --token
sha256:3e7ae8680522b9e8031ff397f28d622a9a86a5708797b1d7ddbc2071e4a5884e` returned `state: proceed`
(the pre-existing active attempt for this work unit was continued, not replaced).

## Review workload

Forecast: `Decision needed before apply: No` · `Chained PRs recommended: No` · `400-line budget risk: Low`.
**Actual**: `222 insertions(+), 20 deletions(-)` across 3 files (242 changed lines) — inside the 400-line
canonical threshold, so single PR / no chain; no delivery decision was required or invented.

## Task-by-task

| Task | Status | Evidence |
|---|---|---|
| 1.1 baseline tally (pre-edit) | done | `1766 passed, 6 skipped, 1 warning in 57.20s` (exit 0) — re-derived, not trusted |
| 1.2 resolved `delimiter`/`encoding` at call time | done | `cli.py` diff: `delimiter = config.CSV_DELIMITER`, `encoding = config.CSV_ENCODING` beside `max_sample`; both passed as kwargs |
| 1.3 `except (ValueError, LookupError)` → `Error:` + rc 1 | done | try/except wraps `generate_codebook(...)`, reusing the `--all-files` sibling idiom; no `except Exception` |
| 1.4 docstring extended | done | docstring names `config.CSV_DELIMITER` / `config.CSV_ENCODING`, the reload ordering, MSP-R10 and the diagnostic contract |
| 2.1 `_read_csv` → `stream_csv` adapter | done | consumes `(header, row)`, first yield = headers, remaining rows transposed column-wise |
| 2.2 explicit `max_sample=None` | done | `grep -n "max_sample=None" src/sofer/codebook.py` → line 95 (the delegated call) |
| 2.3 `_read_file`/`_read_tsv` preserved; `import csv` dropped | done | `_read_file` unchanged with explicit params; `_read_tsv` still `delimiter="\t"`; `git diff -U0` hunk headers confined to imports + `_read_csv`/`_read_tsv`; ruff clean (unused import would fail) |
| 2.4 docstring names the delegated reader + fallback policy | done | docstring names `sofer._csv_reader.stream_csv` and `utf-8-sig` → `utf-8` (never `latin-1`/`cp1252`) |
| 3.1 `test_codebook_honors_tool_sofer_delimiter` | done | green via `run_cli`; asserts `| 1 | \`name\`` / `| 2 | \`age\`` (2 columns) |
| 3.2 `test_codebook_honors_tool_sofer_encoding` | done | green; `csv_encoding = "cp1252"` + byte `0xE1` (invalid UTF-8) succeeds |
| 3.3 `test_codebook_undecodable_file_is_diagnostic` | done | green; byte `0x81` undecodable in cp1252 **and** UTF-8 → `rc == 1`, stderr starts `Error: `, no `Traceback` |
| 3.4 `test_codebook_unknown_codec_is_diagnostic` | done | green; `csv_encoding = "not-a-codec"` → same three assertions (the `LookupError` arm) |
| 3.5 in-process carriers for both arms (**added during apply**) | done | 2 tests in `TestCodebookSingleFileDiagnosticArmsInProcess`; see "Deviations" |
| 4.1 full suite vs baseline | done | `1772 passed, 6 skipped, 1 warning in 55.62s` (exit 0) = baseline +6 tests, 0 failures |
| 4.2 focused run | done | `253 passed, 1 skipped, 1 warning in 21.41s` (exit 0) = 247 + 6 |
| 4.3 core-coverage mandate | done | `bash scripts/check_core_coverage.sh` exit 0; `cli.py 580 stmts, 0 miss, 166 branch, 0 BrPart, 100%`, **empty `Missing`** column |
| 4.4 static gates | done | `mypy` exit 0, `ruff check` exit 0, `ruff format --check` exit 0 |
| 4.5 mechanical scope check | done | 3 changed paths only; 0 forbidden hits (below) |
| 4.6 duplicated-reader grep | done | `codebook.py` contributes **zero** hits for `csv.reader` and zero for `ENCODING_FALLBACKS` (below) |

## Verbatim tallies

| Run | Command | Result | Exit |
|---|---|---|---|
| baseline, pre-edit | `uv run pytest tests/ -q` | `1766 passed, 6 skipped, 1 warning in 57.20s` | 0 |
| baseline, focused | `uv run pytest tests/test_cli.py tests/test_codebook.py -q` | `247 passed, 1 skipped, 1 warning in 20.09s` | 0 |
| post-change, full (final) | `uv run pytest tests/ -q` | `1772 passed, 6 skipped, 1 warning in 55.62s` | 0 |
| post-change, full under coverage | `uv run coverage run -m pytest -q` | `1771 passed, 7 skipped, 1 warning in 68.81s` | 0 |
| post-change, focused | `uv run pytest tests/test_cli.py tests/test_codebook.py -q` | `253 passed, 1 skipped, 1 warning in 21.41s` | 0 |
| new tests only | `uv run pytest tests/test_cli.py -q -k TestCodebookToolConfigParity` | `4 passed, 166 deselected in 2.68s` | 0 |
| new carriers only | `uv run pytest tests/test_cli.py -q -k TestCodebookSingleFileDiagnosticArmsInProcess` | `2 passed, 170 deselected in 0.49s` | 0 |

Delta = +6 collected / +6 passed in the plain run (4 CB-R11 boundary tests + 2 in-process carriers), 0 failures.
The 7th skip in the coverage row is `tests/test_coverage_contract.py`, whose `skipif` is evaluated at collection
time against a local `.coverage` DB that was deleted before that run (its documented "clean checkout → skip" path).

### Test discrimination (anti-regression)

With only the two source files stashed (`git stash push -- src/sofer/cli.py src/sofer/codebook.py`), the four
boundary tests fail (`4 failed, 166 deselected`), then the stash was popped and all four pass again. The tests
genuinely discriminate the fix rather than merely executing it.

## Coverage evidence (`bash scripts/check_core_coverage.sh`)

```
src\sofer\cli.py     580      0    166      0   100%          <- empty Missing column
src\sofer\scanner.py 159      0     76      0   100%
src\sofer\prepare.py 432      0    226      0   100%
src\sofer\publish.py 326      0    138      0   100%
CORE_COV_EXIT=0
```

`uv run coverage report -m` TOTAL row: `6006 stmts, 370 miss, 2324 branch, 167 BrPart, 93%` (config floor 90).

## Scope check

```
$ git diff --stat
 src/sofer/cli.py      |  39 +++++++++++--
 src/sofer/codebook.py |  45 +++++++++-----
 tests/test_cli.py     | 158 ++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 222 insertions(+), 20 deletions(-)

$ git status --porcelain
 M src/sofer/cli.py
 M src/sofer/codebook.py
 M tests/test_cli.py
?? openspec/changes/2026-09-14-fix-cli-codebook-config/

$ git diff --name-only | grep -E "_converters\.py|prepare\.py|mcp_server\.py|test_mcp_server\.py"
(no output)   -> 0 hits: zero #181 paths, zero MCP paths
```

`git diff --stat src/sofer/_csv_reader.py` is empty (byte-identical). `codebook.py`'s `generate` /
`generate_all` signatures and the `cfg.csv_delimiter`/`cfg.csv_encoding` dataset tier are untouched
(`git diff` contains no line mentioning either definition).

## Reader unification (task 4.6)

```
$ grep -rn "csv\.reader\|ENCODING_FALLBACKS" src/sofer/ --include="*.py"
src/sofer/checks.py:175:                    reader = csv.reader(fh, delimiter=self.cfg.csv_delimiter)
src/sofer/quality.py:27:from ._csv_reader import ENCODING_FALLBACKS, stream_csv
src/sofer/quality.py:552:        for enc in ENCODING_FALLBACKS:
src/sofer/repo_compliance.py:295:            reader = csv.reader(fh, delimiter=delimiter)
src/sofer/_csv_reader.py:27:ENCODING_FALLBACKS = ["utf-8-sig", "utf-8"]
src/sofer/_csv_reader.py:96:    for enc in ENCODING_FALLBACKS:
src/sofer/_csv_reader.py:110:        reader = csv.reader(fh, delimiter=delimiter)
```

`src/sofer/codebook.py` contributes **zero** hits for `csv.reader` and **zero** for the fallback list — the
codebook CSV path no longer owns a second reader; it delegates to `_csv_reader.stream_csv`. The remaining hits are
pre-existing and outside this change's allowed edit set: `checks.py`/`repo_compliance.py` are unrelated readers
(#181's territory and other capabilities) and `quality.py` intentionally probes through the shared
`ENCODING_FALLBACKS` constant, which `_csv_reader.py` still owns.

**What changed for `--all-files` and why that is acceptable.** `generate_all`'s dataset-`[meta]` tier is
untouched, and it still passes explicit `delimiter`/`encoding` into `_read_file` → `_read_csv`, so every
dataset-level resolution keeps working. The CSV arm now additionally walks the shared reader's documented
fallback policy (configured encoding first, then `utf-8-sig` → `utf-8`) and raises `ValueError` where a bare
`open()` previously raised `UnicodeDecodeError`; `generate_all`'s per-file `except Exception` warning path catches
both identically, and the explicit `max_sample=None` guarantees the reader never applies
`codebook_max_sample` on top of `generate`'s own `_build_markdown(max_sample)` cap (no double sampling). Its
`--all-files` tests (`test_codebook_all_files_max_sample_parity`, `test_codebook_warning_strict_cp1252`,
`TestCodebookAllFilesErrors`) are green in the full-suite runs above.

## Deviations from design / tasks

1. **Two in-process coverage carriers were added (task 3.5) beyond D5's four boundary tests.** D5 asserted the
   `run_cli` boundary tests would make `cli.py`'s new arms execute under the 100.00% per-file mandate; that is
   factually inverted. `uv run coverage run -m pytest` instruments only the test process — subprocess execution is
   not recorded, and CI sets no `COVERAGE_PROCESS_START` — so the four boundary tests alone leave `cli.py` at
   **5%** and the gate measured `src\sofer\cli.py 580 3 166 0 99%` with `Missing 264-266` (the exception body).
   The fix follows the repo's established carrier pattern (`TestCodebookAllFilesErrors` covers the `--all-files`
   arm in-process) and is explicitly permitted by the spec delta's Test Mapping: "an in-process `_cmd_codebook`
   call MAY be added but MUST NOT replace the boundary test". Both carriers raise the real exceptions from the
   real reader (no mock); only the resolved config constants are monkeypatched. `# pragma: no cover` stays
   forbidden and unused. Result: `cli.py` back to 100.00% with an empty `Missing` column.
2. **The adapter discards a partial pass when `stream_csv` restarts on a fallback encoding.** The reader re-yields
   its header when it retries with the next encoding; the adapter resets the partial columns then, so rows are
   never duplicated. This is exercised by the undecodable-input tests (cp1252 fails mid-file → `utf-8-sig` and
   `utf-8` restarts), so the branch is genuinely covered rather than defensive dead code.
3. **The four boundary tests pass `env={"PYTHONIOENCODING": "utf-8"}`.** The child's console encoding here is
   cp1252, while `run_cli` decodes strictly as UTF-8; the reader's diagnostic carries an em dash, so pinning the
   child to UTF-8 keeps the assertion platform-independent. The cp1252 console path keeps its own dedicated tests
   in `TestConsoleEncodingGuard`.
4. **No `StopIteration` guard in the rewritten `_read_csv`.** The empty-file placeholder contract is preserved
   through `stream_csv`'s documented `([], None)` header yield (a truly empty file still returns `([], [], None)`
   and renders "no data rows"), which `test_generate_empty_csv_returns_placeholder` pins. Keeping the old
   `except StopIteration` would have been unreachable code.

## Environment note (not a regression)

A single intermediate `uv run pytest tests/ -q` observed `1 failed, 1769 passed, 6 skipped`:
`test_three_floor_modules_and_total_meet_90_when_data_file_present` read the repo-local **stale** `.coverage` DB
(git-ignored, `.gitignore:60`) and counted the newly added source lines as missing → TOTAL 89.8%. That is an
artifact of measuring old execution data against new source, not a product defect. After the mandated fresh
`uv run coverage run -m pytest`, the contract test passes (`3 passed`) and the plain full-suite tally is clean at
`1772 passed, 6 skipped`. CI is unaffected: on a clean checkout the DB is absent and that test skips.

## Remaining tasks

None. `openspec/changes/2026-09-14-fix-cli-codebook-config/tasks.md` has **0** `- [ ]` lines and **19** `- [x]`
lines; every `sdd-owner: implementation` marker is terminal and well-formed, and the parent-owned rows plus the
non-checkbox §Verify Gates / §Parent-Owned Lifecycle sections were left as non-checkbox text.

## Verify gates

Deferred to the **verify** phase by design (they must not gate `apply`): the CB-R11 five-scenario review against
the spec delta, the `latin-1`-rejection precedent (`tests/test_quality.py:750-757`) re-run, the full-suite
re-run under `openspec/config.yaml`'s `verify.test_command`, the `cli.py` 100.00% confirmation on the verify
branch, and rollback feasibility. Rollback remains a single revert: 3 files, no migration, no persisted artifact,
no config/pyproject/workflow surface.

## Pre-existing findings carried into `risks` (all mechanically disproven as introduced here)

- `src/sofer/cli.py:465` — `import tomli as _tomli` unresolved in the local static analyzer (`tomli` is not
  installed; the `tomllib` arm is live). Present at HEAD line 438; `git diff` mentions tomli 0 times. AGENTS.md
  rule 12 documents this as a known latent condition of this environment.
- `src/sofer/cli.py:1046` — `shutil.move(str(src), str(dest))` "call without try/except": HEAD line 1019, inside
  `_cmd_init`'s `--move` flow, shifted only by the `_cmd_codebook` insertion. My diff hunks are confined to
  lines 181-266. Byte-identity proof: `git show HEAD:src/sofer/cli.py | sed -n '985,1040p'` and
  `sed -n '1012,1067p' src/sofer/cli.py` both hash to
  `sha256 52d226b11ba6bf5f9e3b3a3086be386b8acea2b0518934896e39cd6097cf831f` (identical `diff` output), and the
  flagged line executes in tests (`cli.py` at 100.00%, 0 missing).
- `src/sofer/codebook.py:247,252` — `_read_jsonl`'s bare `open` / `json.loads` advisories: untouched function
  (starts at line 238), shifted by the insertion above it.
- `tests/test_cli.py:16` (`from conftest import run_cli`, the repo-wide pytest convention) and the `tomli`
  fallbacks in `tests/test_cli.py`: pre-existing, unmodified lines.
