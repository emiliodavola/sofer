# Design: fix-sofer-init-cwd-windows-todo

## Technical Approach

Fix two coupled bugs with a minimal, contained change (Approach 1): replace the `TODO:`-prefixed placeholder in `_INIT_TEMPLATE` (`src/sofer/cli.py:746-822`) with a Windows-safe `raw/example.csv`, and add an optional `cwd` parameter to `sofer_init` that resolves to a per-call `effective_root` contained under `_SERVER_ROOT`. Scanner discovery and `merge_entries` TODO-stripping remain unchanged beyond confirming `.xlsx` is in `SUPPORTED_FORMATS` and anchoring the `scan` chain under the same `effective_root`. No global mutation, no new tool, no `SUPPORTED_FORMATS` change. Follow-up file issue for Approach 2 (default live `Path.cwd()` + `cwd` on scan).

## Architecture Decisions

| Decision | Option | Tradeoff | Verdict |
|---|---|---|---|
| Template placeholder | Keep `TODO: raw/file.csv` | Illegal on NTFS (`:` reserved), `ntpath.splitdrive` -> `('TODO:', ...)`, `FileEntry.validate` fails, violates INIT-01 | Reject |
|  | Comment out `[[file]]` (`# [[file]]`) | No failing placeholder but hides feature, requires doc change, merge_entries strip unused | Reserve for later |
|  | **`raw/example.csv`** (chosen) | Valid NTFS, `ntpath.splitdrive` -> `('', 'raw/example.csv')`, preserves Phase 0 flow (validate fails until scan/edit), minimal diff, tests green | **Chosen** |
| `cwd` shape | No `cwd` (status quo) | Parent-dir bug persists when `build_server(root=Desktop)` and client CWD is `Desktop/test` | Reject |
|  | Default live `Path.cwd()` | Fixes root cause but changes back-compat, larger blast, touches all tools | Defer to follow-up (Approach 2) |
|  | **`cwd: str \| None = None` optional** (chosen) | `None` -> `_get_root()` (back-compat), `str` -> per-call `effective_root` via `_contained_path(must_exist=False)` + `is_relative_to(_SERVER_ROOT.resolve())`. No global mutation, contained, explicit | **Chosen** |
| Containment gate | Lexical string check | Misses `..`, drive `C:`, UNC, symlinks | Reject |
|  | **`_contained_path` + `is_relative_to`** (chosen) | Resolves, collapses `..`, handles drive mismatch, reused by all tools, raises `PathOutsideRootError` | **Chosen** |
| Scanner TODO handling | Keep `TODO:` and filter later | Retains NTFS bug | Reject |
|  | **Strip `TODO:` in `merge_entries`** (existing) | Already handles `raw/example.csv` naturally, no template TODO to strip, idempotent | **Keep** |

## Data Flow

```
Client CWD (Desktop/test)
      │
      ▼
sofer_init(name, cwd?) ──► effective_root resolution
      │                         │
      │  cwd is None ──────────► _get_root()  (frozen _SERVER_ROOT or Path.cwd().resolve())
      │  cwd is str ───────────► _contained_path(cwd, root=_SERVER_ROOT, must_exist=False)
      │                         │  → resolve → is_relative_to(_SERVER_ROOT.resolve())
      │                         │  → fail: PathOutsideRootError (no write)
      │                         └─► effective_root (per-call local, never mutates _SERVER_ROOT)
      │
      ▼
_contained_path(f"{name}.toml", root=effective_root, must_exist=False)
      │  → candidate.resolve() is_relative_to(effective_root.resolve())
      ▼
effective_root / RAW_DIR  ──► raw_dir.mkdir(parents=True, exist_ok=True)
effective_root / f"{name}.toml" ──► write _INIT_TEMPLATE.format(name,user)
      │  (under _EXEC_LOCK + _capture_output)
      ▼
Next: sofer_scan_apply(config="effective_root/test.toml")
      │  discover_files(base_dir=effective_root, exclude=EXCLUSIONS|{OUTPUT_DIR})
      │  → SUPPORTED_FORMATS includes .xlsx → DATA_GOT_ALL.xlsx, dataset.xlsx found
      │  check_flatten_collisions → merge_entries (strips any residual TODO:) → copy_files(flatten_first_level) → write_toml
      ▼
sofer_validate → cfg.validate() + _validate_file_entries (contained) → ok:true
```

Sequencing note: `_EXEC_LOCK` serializes the entire body (fastmcp threadpool), `config.reload(stop_at=_get_root())` outer bound unchanged; scanner `discover_files` anchoring is `base_dir = toml_path.parent.resolve()` self-anchored II per `_scan_prologue`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/cli.py:746-822` | Modify | `_INIT_TEMPLATE`: `local = "TODO: raw/file.csv"` → `local = "raw/example.csv"`; `local = "TODO: raw/directory/"` → valid or removed; audit meta `TODO:` values (not paths). No hardcoded defaults beyond template. |
| `src/sofer/mcp_server.py:1647-1802` | Modify | `sofer_init` signature add `cwd: Annotated[str\|None, Field(description="...Must stay under server root...")] = None`; compute `effective_root` (None→_get_root(), str→_contained_path check), use for `toml_path`, `raw_dir`, `base_dir`; update docstring side-effects; no mutation of `_SERVER_ROOT`. |
| `src/sofer/mcp_server.py:190-2332` | Modify | Docs: note per-call local, add `_INIT_TEMPLATE` Windows note. Registration in `_register_tools` gains `cwd` in schema + `output_schema`. |
| `src/sofer/scanner.py:194-199` | Verify | `merge_entries` TODO strip already handles transition; ensure `.xlsx` discovered (no code change). |
| `src/sofer/_formats.py:18-24` | Verify | `SUPPORTED_FORMATS` already includes `.xlsx` (no change). |
| `tests/test_mcp_server.py` | Modify | Add Windows placeholder (ntpath), cwd containment (inside/outside/traversal/no-mutation), stale-root (build_server parent, cwd child/test), xlsx integration (DATA_GOT_ALL.xlsx + dataset.xlsx) + validate pass; update literals. |
| `tests/test_cli.py` | Modify | Update `_INIT_TEMPLATE` literal assertions to `raw/example.csv`. |
| `.github/workflows/*` | Defer | `windows-latest` matrix deferred — ntpath unit test suffices per proposal; file follow-up issue. |
| `README.md`, `README_ES.md` | Modify | Sync Phase 0 wording: template example `raw/example.csv`. |

## Interfaces / Contracts

```python
# mcp_server.py — modified signature only new param
def sofer_init(
    name: Annotated[str, Field(description="Dataset name used for <name>.toml")],
    move_existing: Annotated[bool, Field(description="When true, move depth-1 supported files into raw/")] = False,
    dry_run: Annotated[bool, Field(description="When true, preview without writing")] = False,
    force: Annotated[bool, Field(description="Overwrite existing <name>.toml when true.")] = False,
    user: Annotated[str | None, Field(description="Hugging Face username for repo_id")] = None,
    cwd: Annotated[str | None, Field(description="Working directory for init; must stay under server root. When None, uses server root (back-compat).")] = None,
) -> dict[str, Any]: ...

# effective_root resolution (non-obvious pattern — per-call local)
effective_root: Path
if cwd is None:
    effective_root = _get_root()
else:
    # contained under outer bound, may not exist yet, never mutates _SERVER_ROOT
    effective_root = _contained_path(cwd, root=_SERVER_ROOT.resolve(), what="cwd", must_exist=False)
    # _contained_path already enforces is_relative_to(_SERVER_ROOT.resolve()) else PathOutsideRootError
# then:
toml_path = _contained_path(f"{name}.toml", root=effective_root, what="name", extensions=_CONFIG_EXTENSIONS, must_exist=False)
raw_dir = effective_root / sofer_config.RAW_DIR

# cli.py template diff
# before: local = "TODO: raw/file.csv"
# after:  local = "raw/example.csv"   # ntpath.splitdrive("raw/example.csv") == ("", "raw/example.csv")
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Windows placeholder | `ntpath.splitdrive("raw/example.csv") == ("","raw/example.csv")`; `":" not in local`; TOML parses on win32 |
| Unit | cwd containment | `cwd=None` back-compat; `cwd="Desktop/test"` inside → ok; `cwd="C:/Windows"` outside → `PathOutsideRootError`; traversal `../` → error; `_get_root()` unchanged after call |
| Unit | Stale-root | `build_server(root=parent)` + `sofer_init(cwd="parent/child/test", name="test")` → `parent/child/test/test.toml` + `raw/` exist, `parent/test.toml` absent |
| Integration | xlsx discovery | Create `DATA_GOT_ALL.xlsx` + `dataset.xlsx` loose in `effective_root`, `sofer_init(cwd=...)` then `sofer_scan_apply` → `cache/*.xlsx` exist, TOML `local="cache/*.xlsx"` count 2, `sofer_validate` ok:true, rerun idempotent |
| Integration | Scan anchoring | `discover_files` excludes `cache/`+`EXCLUSIONS`, `merge_entries` strips TODO, `check_flatten_collisions` atomic |
| Windows | Path validation | `ntpath` drive checks, `is_relative_to` case-insensitive, `_is_absolute_or_drive` rejects `C:`/`UNC` |

## Migration / Rollout

No migration required. `cwd` is additive and defaults to `None` (back-compat). Existing `test.toml` with `TODO:` placeholders can be fixed by `sofer_scan_apply` (strips) or regenerated via `sofer init --force`. Single PR <400 lines; no feature flag. Chained PR not needed. Defer `windows-latest` CI to follow-up issue if ntpath coverage accepted.

## Open Questions

- [ ] Confirm `windows-latest` matrix deferred — ntpath test sufficient for this PR or required now?
- [ ] Should `cwd` validation create the directory when `must_exist=False` and `raw/` mkdir follows — or require explicit existence?
```
