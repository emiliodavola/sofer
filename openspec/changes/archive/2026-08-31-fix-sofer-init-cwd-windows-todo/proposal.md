# Proposal: fix-sofer-init-cwd-windows-todo

## Intent

Fix MCP `sofer_init` writing to parent dir and `TODO:` placeholders with `:` illegal on NTFS (#113). From `C:\...\test`, `sofer_init("test")` must write `test/test.toml` + `test/raw/` with valid TOML and discover `.xlsx`.

## Scope

### In Scope
- Windows-safe `_INIT_TEMPLATE` (`cli.py:746-822`) — no `:` in `[[file]]`.
- `sofer_init(cwd?: str | None)` per-call root, contained under `_SERVER_ROOT`, no global mutation.
- Tests (Windows + stale-root) + README sync.

### Out of Scope
- `cwd` on `sofer_scan_*` (follow-up).
- Removing `[[file]]` blocks entirely.
- `SUPPORTED_FORMATS` change.
- `windows-latest` matrix if deferred — `ntpath` test suffices.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `mcp-server` (INIT-01, MSP-R03): Windows-safe placeholder; `sofer_init` adds optional `cwd` with containment.
- `cli` (CLI-R07): template uses Windows-safe examples.

## Approach

**Template: `raw/example.csv` over commented `[[file]]`.** Valid NTFS, preserves Phase 0 flow (`validate` fails until `scan`/edit), minimal diff, tests green. Commented variant hides feature — reserve.

**`cwd` shape:** `sofer_init(..., cwd: str | None = None)`. `None`→`_get_root()` (back-compat). `str`→`_contained_path(cwd, root=_SERVER_ROOT, must_exist=False)` rejected if not `is_relative_to(_SERVER_ROOT)`. Per-call `effective_root`, never mutates `_SERVER_ROOT`.

|  | Approach 1 — Ship now | Approach 2 — Follow-up |
|---|---|---|
| Fix | Safe template + optional `cwd` | Default live `Path.cwd()` + `cwd` on scan |
| Pros | Small blast, back-compat, <400 lines | Root-cause fix |
| Cons | Needs explicit `cwd` when stale | Larger, scan delta |
| Effort | ~120-200 lines, 1 PR | ~80-120 lines |

Ship Approach 1; file issue for Approach 2.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py:746-822` | Modified | `TODO:` → `raw/example.csv` |
| `src/sofer/mcp_server.py:1647-1802` | Modified | `sofer_init` `cwd` + containment |
| `src/sofer/mcp_server.py:190-2332` | Modified | Docs: no mutation |
| `tests/test_mcp_server.py` | Modified | Windows + stale-root |
| `.github/workflows/*` | Modified | `windows-latest` or ntpath |
| `README.md`, `README_ES.md` | Modified | Phase 0 wording |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `cwd` containment widen | Low | `is_relative_to(_SERVER_ROOT)` + `_contained_path` |
| `TODO:` assertions break | Med | Update literals only |
| `.xlsx` not found | Low | Test with `DATA_GOT_ALL.xlsx` + `dataset.xlsx` |
| Global mutation | Low | Per-call local |

## Rollback Plan

Revert commit; `cwd` is additive. Re-cut TOML with `sofer init --force` if needed.

## Dependencies

- `SUPPORTED_FORMATS` includes `.xlsx`.
- `config.reload(stop_at=_get_root())` outer bound unchanged.

## Success Criteria

- [ ] In `C:\...\test`, `sofer_init("test")` creates `test/test.toml` + `test/raw/` (not parent).
- [ ] No `TODO:`; `local` is `raw/example.csv` (no `:`).
- [ ] `sofer_validate` passes after `sofer_scan_apply`; `.xlsx` → `cache/*.xlsx`.
- [ ] `sofer_init(cwd="C:/Windows")` → `PathOutsideRootError`.
- [ ] Single PR <400 lines; Windows test green.
