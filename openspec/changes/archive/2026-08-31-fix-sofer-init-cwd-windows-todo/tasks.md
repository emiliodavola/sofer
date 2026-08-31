# Tasks: fix-sofer-init-cwd-windows-todo

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180–220 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (template + cwd + tests + docs) |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Windows-safe template + cwd containment + tests + docs | PR 1 → main | Sole unit; all slices fit <400 lines; tests/docs bundled |

## Phase 1: Foundation — Template

- [x] 1.1 Replace `_INIT_TEMPLATE` placeholders `TODO: raw/file.csv` → `raw/example.csv` in `src/sofer/cli.py:746-822` (remove `:`; keep `raw/example.csv` valid NTFS). *Maps to INIT-01 Win32 no-drive/colon-rejected + CLI-R07 Windows-safe placeholder/ntpath drive; files: `src/sofer/cli.py`; est: ~6 lines* — **blocks 2.x, 3.x**

## Phase 2: Core Implementation — MCP cwd Containment

- [x] 2.1 Add `cwd: Annotated[str|None, Field(...)]=None` to `sofer_init` signature in `src/sofer/mcp_server.py:1647-1665` and register schema in `_register_tools` (output_schema + Field description). *Maps to INIT-02 cwd schema + MSP-R03 sofer_init cwd schema; files: `src/sofer/mcp_server.py`; est: ~15 lines*
- [x] 2.2 Implement `effective_root` resolution (`None→_get_root()`, `str→_contained_path(cwd, root=_SERVER_ROOT.resolve(), must_exist=False)+is_relative_to` else `PathOutsideRootError`) and anchor `toml_path`/`raw_dir` under it (no `_SERVER_ROOT` mutation). *Maps to INIT-02 (None back-compat/contained/outside/traversal/no-mutation) + INIT-03 stale-root/idempotent/cleanup; files: `src/sofer/mcp_server.py`; est: ~40 lines; depends on 2.1*

## Phase 3: Testing — Windows, Containment, Stale-Root, XLSX

- [x] 3.1 Windows placeholder test: `ntpath.splitdrive("raw/example.csv")==("","raw/example.csv")` and `":" not in local`; parses TOML on win32. *Maps to INIT-01 Win32 no-drive/No TODO colon/Colon rejected + CLI-R07 ntpath drive; files: `tests/test_mcp_server.py`; est: ~20 lines; parallelizable after 1.1*
- [x] 3.2 cwd containment tests: inside `Desktop/test` ok, `C:/Windows` outside → `PathOutsideRootError`, traversal `../` → error, `_get_root()` unchanged after call. *Maps to INIT-02 all 5 scenarios; files: `tests/test_mcp_server.py`; est: ~40 lines; parallelizable after 2.2*
- [x] 3.3 Stale-root anchored test: `build_server(root=Desktop)` + `sofer_init(cwd="Desktop/test", name="test")` → `Desktop/test/test.toml`+`raw/` exist, `Desktop/test.toml` absent; idempotent re-run preserves `keep.csv`; parent `Desktop/raw` not created. *Maps to INIT-03 stale-root/idempotent/cleanup; files: `tests/test_mcp_server.py`; est: ~30 lines; parallelizable after 2.2*
- [x] 3.4 xlsx integration: create `DATA_GOT_ALL.xlsx`+`dataset.xlsx` loose in `effective_root`, `sofer_init(cwd=…)`→`sofer_scan_apply`→`cache/*.xlsx` exist + TOML `cache/*.xlsx`×2 + `sofer_validate` ok, rerun idempotent count 2. *Maps to INIT-04 xlsx registered/validate passes/scan idempotent + CLI-R07 scan xlsx; files: `tests/test_mcp_server.py`; est: ~35 lines; parallelizable after 2.2*
- [x] 3.5 Schema contract test: `tools/list` 14 tools, `sofer_init` has optional `cwd` `str`→`None`, `C:/Windows`→`PathOutsideRootError` via schema. *Maps to MSP-R03 schemas constrained/cwd schema; files: `tests/test_mcp_server.py`; est: ~15 lines; parallelizable after 2.1*

## Phase 4: Cleanup — CLI Literals & Docs

- [x] 4.1 Update `tests/test_cli.py` `_INIT_TEMPLATE` literal assertions `TODO: raw/file.csv`→`raw/example.csv`. *Maps to CLI-R07 Windows-safe placeholder; files: `tests/test_cli.py`; est: ~5 lines; parallelizable after 1.1*
- [x] 4.2 Sync `README.md` + `README_ES.md` Phase 0 wording to `raw/example.csv` example. *Maps to INIT-01/CLI-R07 docs; files: `README.md`, `README_ES.md`; est: ~10 lines; parallelizable after 1.1*

## Dependencies & Parallelization

- Order: 1.1 → 2.1 → 2.2 → 3.x → 4.x (4.x can start after 1.1, but full green needs 2.2).
- Parallelizable: 3.1, 3.2, 3.3, 3.4, 3.5 mutually; 4.1, 4.2 mutually.
- Blocker: 1.1 unblocks 3.1/4.1/4.2; 2.2 unblocks 3.2/3.3/3.4.

## Verification

- `uv run pytest tests/test_mcp_server.py tests/test_cli.py -q` (INIT-01..04, MSP-R03).
- `ntpath` Windows check green on Linux CI; manual `win32` mental model `splitdrive` empty.
- `sofer init` → `sofer scan` → `sofer validate` manual on `DATA_GOT_ALL.xlsx` fixture.
