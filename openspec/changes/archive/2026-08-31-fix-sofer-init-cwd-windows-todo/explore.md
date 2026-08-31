# Exploration: fix-sofer-init-cwd-windows-todo

**Change**: `fix-sofer-init-cwd-windows-todo` (issue #113)
**Date**: 2026-08-31
**Mode**: hybrid (Engram + openspec)
**Investigator**: sdd-explore (auto)

## Executive Summary

`sofer_init` via MCP scaffolds in the **parent** directory on Windows and emits `TODO:`-prefixed placeholder `[[file]]` paths that contain a colon — illegal on NTFS. The parent-directory bug is a **server-root/CWD desynchronization**: `mcp_server.sofer_init` anchors on `_get_root()` (frozen at `build_server()` time, default `Path.cwd().resolve()`) while the CLI `_cmd_init` anchors on live `Path.cwd()`. If the MCP process was started in `Desktop/` and the user then creates `Desktop/test/` and calls `sofer_init(name="test")` without restarting the server, `root` stays `Desktop` and `test.toml`+`raw/` land one level too high. The colon bug is a **template literal** (`_INIT_TEMPLATE` in `src/sofer/cli.py:774,778`) that fails Windows filename rules and `sofer_validate`'s existence check. `*.xlsx` non-discovery is a secondary symptom: `scan_apply` was never reached (or was run against the wrong root) and, even when run, `SUPPORTED_FORMATS` does include `.xlsx` — the issue is that the scan phase was skipped/mis-anchored. Fix requires (a) per-call CWD/root re-resolution or `cwd` argument on `sofer_init`, (b) Windows-safe placeholders, (c) ensuring `sofer_init -> sofer_scan_apply` chain discovers `.xlsx` and is idempotent, plus an integration test on `windows-latest`.

## Current State

### How `sofer init` works today

**CLI** (`src/sofer/cli.py:825-952`, `_cmd_init`):

- `output = Path(f"{args.name}.toml")` — relative to **live** `Path.cwd()` (line 841).
- `raw_dir_path = Path.cwd() / RAW_DIR` (847) — always live CWD.
- Writes `_INIT_TEMPLATE.format(name, user)` (852), scaffolds `raw/` with `mkdir -p`, then optionally `check_flatten_collisions` + `shutil.move` for `--move-existing`.
- Template lives at `src/sofer/cli.py:746-822` (`_INIT_TEMPLATE`). Placeholder files:
  ```toml
  [[file]]
  local = "TODO: raw/file.csv"
  [[file]]
  local = "TODO: raw/directory/"
  ```
  plus meta `source = "TODO: organisation name"` (758,774,778) — all contain colon+space.

**MCP** (`src/sofer/mcp_server.py:1647-1802`, `sofer_init`):

- Captures `root = _get_root()` (1686) which returns `_SERVER_ROOT` (set once in `build_server`, `src/sofer/mcp_server.py:2328`) or falls back to `Path.cwd().resolve()` only when no server was built (unit-test path).
- `build_server(root=None)` at `src/sofer/mcp_server.py:2298,2328` defaults to `Path.cwd().resolve()` **at process start**. One-server-per-process; `main()` (2351) calls `build_server()` with no args, so root == cwd at `sofer-mcp` launch.
- Resolves `toml_path = _contained_path(f"{name}.toml", root=root, ...)` (1687) — relative join against `root`, then `candidate.resolve()` + `is_relative_to(root.resolve())` containment.
- `raw_dir = root / RAW_DIR` (1694), `base_dir = root.resolve()` (1695). Every write (`Path(toml_path).write_text(...)`, `raw_dir.mkdir(...)`, `move_to_raw`) is anchored on `root`, not live `Path.cwd()`.
- `mcp_registration.py:build_entry` (line ~95-110) builds the agent config entry with `"cwd": str(cwd.resolve())` and agents launch `sofer-mcp` with that `cwd`. If the entry's `cwd` is stale (e.g., `Desktop` instead of `Desktop/test`), the server's root is permanently stale until restart.

**Config & scanner**:

- `src/sofer/config.py:32-36` — `RAW_DIR="raw"`, `OUTPUT_DIR="cache"`. Reload with bounded `stop_at=_get_root()` (mcp_server.py:454-471). Scanner `discover_files` (scanner.py:133-161) walks `root.rglob("*")`, prunes `EXCLUSIONS`, keeps `SUPPORTED_FORMATS` keys — which **does** include `.xlsx` (src/sofer/_formats.py:18-24). `merge_entries` (194-199) strips `TODO:` entries so placeholders never register. `_cmd_scan` phases 1/2 (cli.py:369-554) move loose files to `raw/` then copy `raw/`->`cache/` flattened.

**Validation**:

- `src/sofer/model.py:547-551` — `DatasetConfig.validate()` resolves each `FileEntry` relative to `cfg._base_dir` (TOML dir) and errors `Local path not found` if missing. `checks.py:121-126` mirrors this. So a placeholder `TODO: raw/file.csv` always fails validation unless edited/removed or stripped by `scan`/`merge_entries`.

### Reproduced evidence for issue #113

- With `CWD=C:\Users\elaze\Desktop\test`, CLI would write `C:\Users\elaze\Desktop\test\test.toml` + `C:\Users\elaze\Desktop\test\raw\`.
- With `root=C:\Users\elaze\Desktop` (parent), MCP `sofer_init(name="test")` yields `_contained_path("test.toml", root=Desktop)` -> `Desktop/test.toml` (parent) and `raw_dir=Desktop/raw`. This matches the report exactly.
- Generated TOML contained `local = "TODO: raw/file.csv"` — `ntpath.splitdrive("TODO: raw/file.csv")` on Windows returns `('TODO:', ' raw/file.csv')`; `_contained_path` and `FileEntry.resolve` treat this as drive-prefixed or as a filename literally containing `:`, which is illegal for `Win32` creation and resolves under `Path.resolve()` to `C:\Users\elaze\Desktop\TODO: raw\...` (NTFS forbids `:` except as drive separator). `sofer_validate` then reports `Missing: C:\Users\elaze\Desktop\TODO: raw\file.csv`.
- `DATA_GOT_ALL.xlsx` (~93KB) and `dataset.xlsx` (~167KB) in `test/` were never registered — because `sofer_scan_apply` was either never invoked (user expected `sofer_init` to auto-scan) or was invoked with `config="test.toml"` resolving against the wrong `root` (parent), so `discover_files(base_dir=Desktop)` did not see `Desktop/test/*.xlsx` as inside `base_dir` correctly, or discovered but filtered by wrong `exclude_dirs` anchoring.
- `repo_id = "emiliodavola/test"` correctly set — `user_val` logic (mcp_server.py:1696) and `_INIT_TEMPLATE` (759) are sound.

## Affected Areas

- `src/sofer/mcp_server.py:190-198` — `_get_root()` and `_SERVER_ROOT` lifecycle (root freeze point).
- `src/sofer/mcp_server.py:2298-2332` — `build_server(root, approval_phrase)` — default `Path.cwd().resolve()`, global mutable state, one-server-per-process warning.
- `src/sofer/mcp_server.py:1647-1802` — `sofer_init` — entire MCP init path; especially 1686-1695 (`root`, `toml_path`, `raw_dir`, `base_dir`), 1722-1796 (branching for `move_existing`/`dry_run`).
- `src/sofer/cli.py:746-822` — `_INIT_TEMPLATE` — placeholder literals with `TODO:` prefix (lines 774, 778, also 765-769).
- `src/sofer/cli.py:825-952` — `_cmd_init` — CLI mirror for parity checks; uses live `Path.cwd()` intentionally (correct for CLI, diverges from MCP).
- `src/sofer/scanner.py:194-199` — `merge_entries` TODO-stripping guard; `src/sofer/scanner.py:133-161` discovery including `.xlsx`.
- `src/sofer/_formats.py:18-24` — `SUPPORTED_FORMATS` — confirms `.xlsx` supported; no code change needed here but scan anchoring does.
- `src/sofer/model.py:322-378,515-567` — `DatasetConfig.from_toml` + `validate` — local path resolution against `_base_dir`, drives the `Local path not found` error.
- `src/sofer/config.py:100-127,196-251` — config discovery `reload(start, stop_at=_get_root())` — bounded walk, relevant to root drift.
- `src/sofer/mcp_registration.py:53-90,95-110,200-260` — `resolve_config_path`, `build_entry`, `validate_cwd` — determines what `cwd` is written to agent config and thus what the MCP server's `root` becomes at next launch.
- `tests/test_mcp_server.py` — `TestInit*` suites (`TestInitCreatesTomlAndRaw`, `TestInitDryRun`, `TestInitCollision`, `TestInitTraversal`, `TestInitIdempotencyForce`, `TestInitTreePreserve`) — currently pass on Linux but don't cover Windows `:` behavior or stale-root scenario.
- `tests/test_cli.py`, `tests/test_scanner.py` — init/scan coverage; need Windows fixture.
- `openspec/specs/mcp-server/spec.md` — INIT-01 and MSP-R03/R06 — will need delta for any new `cwd` param or behavioral guarantee.
- `README.md` / `README_ES.md` + `docs/` — workflow docs `sofer init -> sofer scan` conditional `Phase 0 REQUIRED when no TOML / empty [[file]]` (fix checklist f).

## Root Cause Hypotheses

### (a) Parent-directory scaffolding

**H1 — Stale server root (most likely, P0):**

`_SERVER_ROOT` is set once at `build_server()` (process start) to `Path.cwd().resolve()` at that moment. MCP clients (opencode) spawn `sofer-mcp` with `cwd` from the agent config entry (`opencode.json` `mcp.sofer.cwd`). If the user created `Desktop/test/` **after** the agent/MCP server started (server root = `Desktop`), or if the agent config's `cwd` was `Desktop` because it was registered before `test/` existed, the server's root never automatically follows the user's new CWD. `sofer_init(name="test")` then resolves `test.toml` under `Desktop` not `Desktop/test`. CLI `_cmd_init` does not have this bug because it reads live `Path.cwd()` per invocation.

Evidence: `mcp_server.py:185-197,2328`; `mcp_registration.py:build_entry` writes cwd once; `main()` has no per-call re-anchor. The issue's `CWD=C:\Users\elaze\Desktop\test` vs `Desktop/test.toml` parent mismatch is the exact signature of H1.

**H2 — `Path.resolve()` symlink / `..` handling on Windows (less likely):**

`_contained_path` does `candidate = root / candidate; resolved = candidate.resolve()` and `raw_dir.resolve().is_relative_to(base_dir)`. On Windows, `Path.resolve()` follows junctions/symlinks and may normalize `C:\Users\elaze\Desktop\test\..` differently; if the MCP client passes `name` with path separators or `root` contains a trailing `..`, resolution could escape. Tests `test_traversal_*` already gate `../` and `C:/`, but a config where `root` itself is a symlink to `Desktop` could canonicalize to a different drive letter casing. This would be secondary to H1, not the primary parent-offset.

**H3 — Missing per-call `cwd` capture / `projectPath` from MCP client not propagated (design gap):**

FastMCP stdio server inherits `os.getcwd()` from the spawner, but the MCP spec also carries `clientInfo` / `roots` / `workspace` hints that sofer never reads. If the editor moves its workspace to `test/` without restarting the MCP server, there is no channel to update `_SERVER_ROOT`. Without a per-call `cwd` parameter or `roots` subscription, the server cannot self-correct. This is the architectural root of H1.

**Disambiguation plan**: Log `_get_root()` vs `Path.cwd().resolve()` at `sofer_init` entry; add a test that starts `build_server(root=tmpA)`, then changes `os.chdir(tmpA/sub)` and calls `sofer_init(name="sub")` — it will write to `tmpA/sub.toml`? Actually with current code it writes to `tmpA/sub.toml`? Wait `f"{name}.toml"` with `name=sub` under `root=tmpA` -> `tmpA/sub.toml`, not `tmpA/sub/sub.toml`. That's the bug. A failing test with `root=Desktop` and `chdir=Desktop/test` calling `sofer_init(name="test")` and asserting `Desktop/test/test.toml` exists will reproduce H1.

### (b) `TODO:` colon illegal on Windows

**H1 — Hardcoded placeholder with colon+space (confirmed, P0):**

`_INIT_TEMPLATE` at `cli.py:774` `local = "TODO: raw/file.csv"` and `778` `local = "TODO: raw/directory/"` emit a colon. On Windows NTFS, `:` is reserved (drive separator, stream separator), and `Path("TODO: raw/file.csv").resolve()` on `win32` yields a drive-like interpretation (`ntpath.splitdrive` -> `TODO:` drive). Even on POSIX, the placeholder is a nonexistent path that `validate` must report. The scanner's `merge_entries` already strips `TODO:` entries, but `validate` runs before scan and therefore fails `Local path not found`. The fix is to replace placeholders with Windows-safe values (e.g., `raw/example.csv` or `raw/REPLACE_ME.csv`) or remove the placeholder `[[file]]` blocks entirely and document that `sofer_init` + `sofer_scan_apply` populates them.

Evidence: `cli.py:746-822`; Windows path rules (PowerShell `Join-Path` guidance, `ntpath.isabs` handling in `mcp_server.py:257-279` shows awareness of drive prefixes); issue report colon -> `C:\...\TODO: raw\...`.

**H2 — `scanner.merge_entries` stripping too late (secondary):**

Stripping happens only inside `scan` (scanner.py:197). `sofer_init` itself does not strip, so a user running `sofer_validate` immediately after `sofer_init` (before `scan`) sees the placeholder error. This is intentional for the "edit the file" workflow, but the placeholder must still be a valid (though nonexistent) path so `validate` error message is `Missing: <resolved>/raw/file.csv` without colon confusion, and CI on Windows must not hit `OSError` on `Path.write_text` dealing with colon in TOML value (not a filesystem write, but `Path("TODO: raw/file.csv")` as a TOML *value* is not a file creation — it only becomes a path when `FileEntry.resolve` is called).

**H3 — Encoding/escaping of TOML placeholder not needed beyond colon removal:**

No TOML escaping issue; `tomli` handles quoted strings. The problem is purely the *content* of the string, not its serialization.

## Approaches

### Approach 1 — Minimal patch: Windows-safe template + stale-root guard + `sofer_scan_apply` auto-invoke hint (Low-Medium effort)

**What**: (a) Replace `TODO: raw/file.csv` -> `raw/example.csv` and `TODO: raw/directory/` -> `raw/example_dir/` (or comment them out with `# [[file]]` example) in `_INIT_TEMPLATE` (cli.py:746-822) and ensure `mcp_server.sofer_init` reuses the updated template. (b) In `mcp_server.sofer_init`, before resolving `toml_path`, detect stale root: if `Path.cwd().resolve() != _get_root().resolve()` and `Path.cwd().resolve().is_relative_to(_get_root().resolve())`, either warn in `output` or optionally re-anchor to `Path.cwd()` when the cwd is a child of root (covers `Desktop/test` inside `Desktop`). Alternatively, add optional `cwd: str | None` param to `sofer_init` that, when provided, is validated via `_contained_path(..., must_exist=False)` under current root and becomes the effective root/base for this call (back-compat: `None` = current behavior). (c) Ensure `move_existing` scans `root` (not `Path.cwd()`) and that `SUPPORTED_FORMATS` discovery for `*.xlsx` is exercised; document `sofer_init -> sofer_scan_apply` explicitly and make `sofer_init` optionally chain `scan_apply` when `move_existing=True` or via new `auto_scan: bool=False` flag. (d) Add Windows `:` regression test (`test_init_windows_placeholder_valid_path`) and a stale-root test.

- Pros: Smallest blast radius; fixes both symptoms without changing server lifecycle; backward compatible (`cwd=None`); template fix is trivial; leverages existing `check_flatten_collisions`/`move_to_raw`.
- Cons: Stale-root heuristic is fragile (what if user truly wants parent?); `cwd` param adds API surface; does not fix the underlying one-server-per-process staleness for other tools (`sofer_scan_apply` still anchored on stale root unless also patched).
- Effort: Low (template) + Medium (root heuristic + tests) ~ 1-2 PRs within 400-line budget.

### Approach 2 — Correct anchoring: per-call CWD re-resolution + `cwd` override on every dataset tool (Medium effort, architecturally correct)

**What**: Change `mcp_server._get_root()` semantics to return live `Path.cwd().resolve()` when the MCP client's `roots` or `cwd` header indicates a workspace move, or add explicit `cwd: Path | None` param to `sofer_init`, `sofer_scan_*`, `sofer_validate`, etc., validated with `_contained_path(..., must_exist=False)` and used as effective `root`/`base_dir` for that call instead of the frozen `_SERVER_ROOT`. For `sofer_init`, default `cwd` to `Path.cwd().resolve()` (live) rather than `_get_root()` when `sofer_init` is called without explicit `cwd` — this restores CLI parity (`Path.cwd()` vs `_get_root()`). Keep `_SERVER_ROOT` only as a containment *outer bound* (`stop_at` for config discovery, and to reject `cwd` that escapes it), not as the write anchor.

- Pros: Fixes parent-dir bug at the root cause (anchoring); restores parity between CLI and MCP; makes `sofer_init` work in newly created subdirectories without restarting the server; Windows-safe template is still needed but decoupled.
- Cons: Larger change (touch `sofer_init` + `sofer_scan_*` + possibly `_load_dataset`); requires spec delta (INIT-01 + MSP-R03 schema change); needs careful containment review — `cwd` must be `is_relative_to(_SERVER_ROOT)` else `PathOutsideRootError`.
- Effort: Medium. Fits one PR (~250 lines) if limited to `sofer_init` + `sofer_scan_*`; full-suite `cwd` on all tools is High.

### Approach 3 — Server lifecycle fix: restart/watch + deprecate placeholder `[[file]]` blocks (Medium-High effort, most robust)

**What**: (a) Fix template to emit **no** placeholder `[[file]]` blocks — instead emit commented examples (`# [[file]]` / `# local = "raw/your_file.csv"`), so `validate` does not fail on fresh init and `scan` populates real entries. (b) Make `build_server` subscribe to MCP `roots/list_changed` or poll `Path.cwd()` per call, updating `_SERVER_ROOT` when the workspace root moves (or document that users must run `sofer mcp add --cwd <new>` and restart). (c) Add Windows integration test matrix (`windows-latest`) exercising `sofer_init` + real `.xlsx` files in `test/` and asserting `test/test.toml`, `test/raw/`, `test/cache/` layout.

- Pros: Eliminates the placeholder error entirely (no `Local path not found` after init); handles workspace moves generically; Windows CI catches regressions permanently.
- Cons: Commented TOML sections are less discoverable for new users (they must uncomment vs edit); `roots` subscription requires FastMCP API not yet used (research needed); lifecycle change touches `build_server` global state and `_EXEC_LOCK` interactions.
- Effort: Medium-High. Spec + code + CI workflow change (~300-400 lines, may need chained PRs).

## Recommendation

**Recommended: Approach 1 (minimal) immediately, then Approach 2 incrementally.**

- Ship Approach 1 as the fix for issue #113: Windows-safe template + `sofer_init(cwd?)` optional param with containment, plus `sofer_scan_apply` anchoring fix and `windows-latest` smoke test. This closes the P0 within review budget and is safely cherry-pickable.
- Follow up with Approach 2's per-call CWD re-resolution as a fast-follow: make `sofer_init` default to live `Path.cwd()` when `_SERVER_ROOT` is stale, and add the same `cwd` param to `sofer_scan_*`. This is the correct architectural repair without overhauling the server lifecycle.
- Approach 3's commented-template variant is worth discussing in proposal/spec: if the team prefers "init should not fail validate", commented examples are cleaner than `raw/example.csv` placeholders that still fail `validate`. Decide in `sdd-propose`.

## Risks

- **Stale root re-anchoring can widen containment if done naively** — any `cwd` override MUST be `is_relative_to(_SERVER_ROOT.resolve())` and `_contained_path`-validated; otherwise `cwd=C:/Windows` could let `sofer_init` write outside the intended workspace. Mitigation: treat `_SERVER_ROOT` as outer bound, `cwd` as inner anchor, reject with `PathOutsideRootError` when outside.
- **Template change breaks tests that assert exact `_INIT_TEMPLATE` string** — `tests/test_mcp_server.py::TestInitCreatesTomlAndRaw` compares `Path.read_text() == _INIT_TEMPLATE.format(...)`. Changing the template literals will green those tests (they compare against the same constant) but any hard-coded `TODO: raw/file.csv` assertion in tests must be updated.
- **Scan discovery of `.xlsx` may be masked by `EXCLUSIONS` or `raw/` vs `cache/` confusion** — `discover_files` prunes `.git`, `__pycache__`, etc., but not `.xlsx`. The real failure was scan never ran or ran against wrong `base_dir`. Ensure integration test creates `DATA_GOT_ALL.xlsx` and `dataset.xlsx` in `raw/` or loose in `test/` and asserts `discovered >=2`, `registered >=2`, and `local = "cache/DATA_GOT_ALL.xlsx"` etc.
- **Windows colon regression may reappear via other placeholders** — `meta` fields `description = "TODO: short description"` etc. are TOML *values*, not paths, so colons there are safe. Only `[[file]] local` needs Windows-safe paths. Audit all `TODO:` strings before closing.
- **Review budget (3000 lines allocated, 400-line PR guard active)** — Approaches 1 and 2 together may approach 300 lines; keep PRs sliced (PR1: template + `cwd` param + unit tests; PR2: scan anchoring + Windows CI).
- **One-server-per-process invariant** — Changing `_SERVER_ROOT` per call mutates global state under `_EXEC_LOCK`; concurrent calls could see different roots. The lock serializes this, but document that `cwd` override is per-call effective root, not a mutation of `_SERVER_ROOT`.

## Ready for Proposal

**Yes** — sufficient evidence to draft `proposal.md` for `fix-sofer-init-cwd-windows-todo`.

**What the orchestrator should tell the user / next phase inputs**:

- Scope: `src/sofer/mcp_server.py` (`sofer_init` + `_get_root`/`build_server`), `src/sofer/cli.py` (`_INIT_TEMPLATE`), `src/sofer/scanner.py` (no change, but verify), `tests/test_mcp_server.py` + new `tests/test_init_windows.py` or `tests/test_mcp_server.py::TestInitWindows*`, `.github/workflows/` (add `windows-latest` job), `README.md`/`README_ES.md` Phase 0 workflow docs.
- Proposal MUST choose between commented `[[file]]` examples vs `raw/example.csv` Windows-safe placeholders; MUST decide `cwd` param shape (`str | None`, `must_exist=False`, contained).
- Spec deltas: `mcp-server` INIT-01 (placeholder path MUST be Windows-safe, no `:`), plus optional `cwd` param scenario; `tool-config` if `cwd` outer-bound rule changes.
- Design MUST include sequence diagram `client cwd -> sofer_init(cwd?) -> _get_root vs Path.cwd() -> _contained_path -> write` and decision matrix Approaches 1 vs 2.
- Tasks MUST forecast 400-line budget: Decision needed before apply: No (single slice fits if limited to template + `cwd` + tests), Chained PRs recommended: No for Approach 1 alone, Yes if Approach 2 bundled.

## Key Files and Line References

| File | Lines | Why |
|------|-------|-----|
| `src/sofer/mcp_server.py:185-198` | `_SERVER_ROOT`, `_get_root` | Root freeze point — parent-dir RCA |
| `src/sofer/mcp_server.py:2298-2332` | `build_server` | Defaults to `Path.cwd().resolve()` at start |
| `src/sofer/mcp_server.py:1647-1802` | `sofer_init` | Full MCP init flow, writes under `root` |
| `src/sofer/cli.py:746-822` | `_INIT_TEMPLATE` | Placeholder literals with `TODO:` (774,778) |
| `src/sofer/cli.py:825-952` | `_cmd_init` | CLI uses live `Path.cwd()` (parity reference) |
| `src/sofer/scanner.py:133-161,194-199` | `discover_files`, `merge_entries` | `.xlsx` support + `TODO:` strip |
| `src/sofer/_formats.py:18-24` | `SUPPORTED_FORMATS` | Confirms `.xlsx` included |
| `src/sofer/model.py:547-551` | `validate` | `Local path not found` origin |
| `src/sofer/config.py:100-127,196-251` | `reload`, `_discover` | Bounded discovery with `stop_at=_get_root()` |
| `src/sofer/mcp_registration.py:53-110` | `resolve_config_path`, `build_entry` | Sets `cwd` in agent config -> server root |
| `tests/test_mcp_server.py:TestInit*` | multiple | Existing init tests, need Windows extension |

## Blast Radius

- **Direct**: `sofer_init` consumers (MCP clients), `sofer_scan_apply` after init, `sofer_validate` immediately post-init (currently fails on placeholder, will change behavior).
- **Indirect**: All MCP tools that use `_get_root()` as anchor (`sofer_validate`, `sofer_prepare`, etc.) if root re-anchoring approach is taken — but limiting `cwd` param to `sofer_init` keeps blast small.
- **CI**: Adding `windows-latest` matrix will increase CI minutes; template change may require regenerating fixtures `tests/fixtures/mcp-happy-path/`.

## Delivery Forecast (auto)

- Estimated changed lines: 120-280 (template 4 lines + `sofer_init` 30-60 + tests 80-120 + workflow 20).
- 400-line budget risk: **Low** for Approach 1 alone; **Medium** if bundling Approach 2 full `cwd` on all tools.
- Chained PRs: Not required for Approach 1; recommend slice if adding Windows CI matrix.

---
*Generated by `sdd-explore` for `fix-sofer-init-cwd-windows-todo`. Saved to Engram topic `sdd/fix-sofer-init-cwd-windows-todo/explore` and `openspec/changes/fix-sofer-init-cwd-windows-todo/explore.md` per hybrid artifact_store. Review budget 3000 lines; delivery strategy auto-forecast.*
