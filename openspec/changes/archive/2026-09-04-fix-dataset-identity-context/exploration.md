# Exploration: fix-dataset-identity-context (issue #116)

**Change**: `fix-dataset-identity-context` — make CLI and MCP dataset identity explicit and bounded.
**Issue**: GitHub #116 (labels: bug, status:approved) — first implementation slice of tracker #115.
**Date**: 2026-09-04 · **Artifact store**: hybrid (OpenSpec + Engram) · **Mode**: research only, no source edits.
**Baseline**: `dev` @ e3b9bfb (post PR #132). Suite: 1270 passed / 2 skipped (`uv run pytest tests/ -q`). `SOFER_TRACE.md` untouched (untracked; read-only reference, not source of truth).

## What / Why / Where

**What**: Read-only analysis of how CLI and MCP currently resolve dataset identity (name/user → `<name>.toml` location, dataset root, tool-config discovery anchor, output anchors), the root cause of the parent-root/child-cwd init bug, the exact adapter divergence points, gaps vs the issue's acceptance criteria, and a recommendation for `execution_context.py`.
**Why**: issue #116 needs one small, testable contract for identifying a dataset before any build/publish work — a lower-capability implementation agent must not have to reverse-engineer five interacting mechanisms.
**Where**: `src/sofer/cli.py`, `src/sofer/mcp_server.py`, `src/sofer/model.py`, `src/sofer/config.py`, `src/sofer/prepare.py`, `src/sofer/profile.py`, `src/sofer/render.py`, `src/sofer/codebook.py`; tests `test_cli.py`, `test_mcp_server.py`, `test_mcp_process.py`, `conftest.py`; specs `mcp-server` (INIT-01..04, MSP-R03/R10), `cli` (CLI-R07/R08), `tool-config` (TC-01/02/05/07), `process-boundary` (PB-04/09).

## Current-state map — CLI vs MCP identity resolution

### CLI init (`src/sofer/cli.py` `_cmd_init`, L825-952)

| Concern | Where | Behavior today |
|---|---|---|
| Write target | `cli.py:841` | `output = Path(f"{args.name}.toml")` — **cwd-relative, no containment, no validation** |
| Exists guard | `cli.py:842-844` | refuses overwrite, exit 1 |
| raw/ anchor | `cli.py:846-847` | `Path.cwd() / config.RAW_DIR` (bootstrap key, cwd walk-up per TC-07) |
| user default | `cli.py:851` | `getattr(args, "user", None) or "YOUR_USER"` — **placeholder enters generated TOML** |
| template | `cli.py:852` | `_INIT_TEMPLATE.format(name=args.name, user=user_val)` — raw interpolation, no escaping (`_INIT_TEMPLATE` at `cli.py:746-822`, `repo_id = "{user}/{name}"` L759) |
| write/print | `cli.py:857-858` | writes UTF-8; prints relative `Created {output}` — **no canonical absolute path** |
| parser | `cli.py:1300-1309` | positional `name` (no validation), `--user` default `None` → placeholder |
| bootstrap reload | `cli.py:1489` | `config.reload(None)` (cwd anchor) before parser build |

No name/user validation anywhere before the write; the only guard is file existence.

### MCP init (`src/sofer/mcp_server.py` `sofer_init`, L1647-1833)

| Concern | Where | Behavior today |
|---|---|---|
| signature | `mcp_server.py:1647-1671` | `name` required; `user: str\|None=None`; `cwd: str\|None=None` |
| name empty | `mcp_server.py:1690-1699` | envelope refusal `CONFIG_ERROR` — the only name validation |
| cwd=None | `mcp_server.py:1700-1712` | **Approach 2** (commit 82abfbc, ad-hoc post-archive): `live = Path.cwd().resolve()`; if `live.is_relative_to(root_resolved)` → `effective_root = live`; else → `effective_root = _get_root()`; bare `except Exception` → `_get_root()`. **Both else-branches silently select the server root** |
| cwd=str | `mcp_server.py:1713-1717` | `_contained_path(cwd, root=_SERVER_ROOT\|cwd, must_exist=False)` → `PathOutsideRootError` on escape |
| toml target | `mcp_server.py:1718-1724` | `_contained_path(f"{name}.toml", root=effective_root, extensions=(".toml",), must_exist=False)` — **catches `../`, absolute, drive escapes in name, but NOT nested-relative separators** (`name="a/../b"` passes) |
| raw/ anchor | `mcp_server.py:1725` | `effective_root / sofer_config.RAW_DIR` (bounded by `_reload_tool_config`? no — RAW_DIR read at call time; `_tool_execution` L200-213 serializes) |
| user default | `mcp_server.py:1727` | `user.strip() if user and user.strip() else "YOUR_USER"` — **placeholder enters generated TOML** |
| write | `mcp_server.py:1815-1818` (also dry-run branches L1788-1790, L1802-1804) | `raw_dir.mkdir` + `write_text(_INIT_TEMPLATE.format(name, user))` |
| success envelope | `mcp_server.py:1828-1833` | only `ok/exit_code/output/config_errors` — **NO `config_path` / `dataset_root` fields** |
| output_schema | `mcp_server.py:2090-2108` | same 4 fields — **boundary drops any new fields unless schema updated** |
| server root | `mcp_server.py:185` `_SERVER_ROOT`; `190-197` `_get_root()`; `2329-2372` `build_server(root=None)` → `Path.cwd().resolve()`; `2375-2383` `main()` → `build_server()` (root = **process cwd**) | containment root is a process global captured at build |
| containment gate | `mcp_server.py:282-339` `_contained_path` | expanduser → absolute-ize against root → resolve → `is_relative_to(root.resolve())` → ext allow-list → existence |

### Config loading (`src/sofer/model.py` `DatasetConfig.from_toml`, L322-509)

- `from_toml(cls, path)` — **no `discovery_root` parameter** (`model.py:322-323`). `base_dir = path.parent` (L370); **unbounded** `config.reload(base_dir)` (L378); `_base_dir` stored (L508).
- MCP compensates post-hoc: `_bound_discovery(base)` (`mcp_server.py:457-471`) re-runs `config.reload(base, stop_at=_get_root())` when `SOURCE_PATH` escaped the root — **the hack this change replaces with `from_toml(path, discovery_root=server_root)`**.
- `validate()` (`model.py:515-567`): placeholder check `repo_user.lower() in _PLACEHOLDERS` (L529-537, set at L33-35: `your_user`, `your_org`, ... — `YOUR_USER` matches via lowercasing), `repo_id` regex `^[\w\-]+/[\w\-]+$` (L540). **These run post-write only** (on the generated TOML), never pre-write.

### Tool config discovery (`src/sofer/config.py`)

- `_find_project_root(start, stop_at)` (L100-127) — walk-up, `stop_at` bounds above root; `_discover(start, stop_at)` (L196-230) — dataset-dir → cwd → `_DEFAULTS` (TC-02); `reload(start, stop_at)` (L233-258) rebinds constants under `_LOCK`.
- `_DEFAULTS` (L28-89): `output_dir="cache"` (L32), `raw_dir="raw"` (L33), `default_config_name="dataset.toml"` (L34), `profile_dir="profiles"`/`render_dir="renders"` (L35-36).
- MCP bounded reload helper: `_reload_tool_config(start)` (`mcp_server.py:445-454`) — `reload(start, stop_at=_get_root())`.

### Output resolution — the divergence

| Tool family | CLI anchor | MCP anchor |
|---|---|---|
| prepare | `resolve_output_dir(cfg, args.output)` → `cfg._base_dir / name` (`prepare.py:550-570`) ✓ config-dir | `_contained_path(output_dir, root=_get_root())` (`mcp_server.py:775-779`) → **server-root** ✗ |
| publish / confirm | `resolve_output_dir` (publish.py:620/667) ✓ | `_contained_path(..., root=_get_root())` (mcp_server.py:851-858, 1006-1014) ✗ |
| codebook_all / profile_all / render_all (batch) | raw `args.output` → domain anchors to `cfg._base_dir` (`profile.py:231-240`, `render.py:200-209`, `codebook.py:529`) ✓ | `_contained_path(..., root=_get_root())` (mcp_server.py:1114-1121, 1265-1272, 1387-1394) ✗ |
| profile / render / codebook (single-file) | `Path(args.output)` passed raw → **cwd-relative** when written (`profile.py:186`, `render.py:157`, `codebook.py:431`); default anchors to input's parent ✓/✗ | `_contained_path(output_file/output_dir, root=_get_root())` (mcp_server.py:1070-1071, 1177-1182, 1319-1324) ✗ |

**Net**: `output_dir="build"` with config at `<root>/test/test.toml` → CLI batch: `<root>/test/build`; MCP: `<root>/build`. Acceptance criterion: **both anchor relative overrides to `config_path.parent`**.

### Default-name guessing

- MCP: none — every tool requires explicit `config` (MSP-R10, `mcp_server.py:686-693` etc.). Canonical chain returns `config_path` from init.
- CLI: argparse defaults `default=config.DEFAULT_CONFIG_NAME` (`cli.py:1159, 1217, 1271, 1365`) + `_cmd_scan` resolves `Path(args.config)` (`cli.py:397`), `_cmd_profile`/`_cmd_render` `toml_arg` resolution (`cli.py:256-263, 325-332`).

## Root-cause analysis — parent-root/child-cwd bug

Ground truth: server root `C:\Users\elaze\Desktop`, intended dataset `C:\Users\elaze\Desktop\test`, `sofer_init(name="test", user="emiliodavola")` (cwd omitted) wrote `C:\Users\elaze\Desktop\test.toml`. `SOFER_TRACE.md` corroborates: first attempt created the TOML at the parent and the maintainer manually moved it to `test/test.toml`, after which the canonical chain used `config="test/test.toml"`.

Mechanism (`mcp_server.py:1700-1712`):
1. The host launched `sofer-mcp` with the **process cwd = the parent root** (`Desktop`); `main()` → `build_server()` → `_SERVER_ROOT = Path.cwd().resolve()` = `Desktop` (`mcp_server.py:2359`).
2. `cwd=None` → `live = Path.cwd().resolve()` = `Desktop`; `live.is_relative_to(Desktop)` → **True** (`is_relative_to` includes equality).
3. `effective_root = live` = `Desktop` → `_contained_path("test.toml", root=Desktop)` → `Desktop/test.toml`.
4. The intended child (`Desktop/test`) is **never consulted** — the auto-detect has no signal for it; `cwd` was omitted so the caller's intent was lost.

Two sub-branches silently select the parent root, both violating "never silently selects the parent root": (a) `live == root` (L1707-1708), (b) `live` outside root → `_get_root()` (L1709-1710). Historical drift: archived `fix-sofer-init-cwd-windows-todo` pinned `cwd=None → _get_root()` (INIT-02, "back-compat"); the ad-hoc Approach-2 commit `82abfbc` changed code+tests but **never updated the live `mcp-server` spec** — INIT-02's "cwd None back-compat" scenario (root stays `Desktop` when live CWD is `Desktop/test`) now contradicts the code (which would pick `Desktop/test`). Issue #116 supersedes both with fail-closed semantics.

## Divergence points (exact)

1. **cwd=None resolution**: MCP auto-detects (parent-root risk); CLI has no cwd concept (always cwd-anchored by process). Criterion: MCP uses live CWD only when *strictly inside* root, else input-required.
2. **Name/user validation**: CLI validates nothing; MCP validates only `name.strip()`. Neither rejects separators/quotes/newlines/control chars/drive paths pre-write; both emit `YOUR_USER`.
3. **Placeholder policy**: both adapters generate `YOUR_USER/…` TOML (`cli.py:851`, `mcp_server.py:1727`); rejection happens post-write in `validate()` (`model.py:529-537`) — issue demands pre-write rejection.
4. **Identity reporting**: CLI prints relative filename; MCP envelope/schema omit `config_path`/`dataset_root` entirely.
5. **Config-discovery bound**: `from_toml` unbounded + `_bound_discovery` post-hoc re-bind in MCP vs plain `reload` in CLI.
6. **Relative output override anchor**: MCP → server root (`_contained_path`); CLI batch → `cfg._base_dir`; CLI single-file → process cwd. Criterion: `config_path.parent` in both.

## Gaps vs issue acceptance criteria

| Criterion | Status | Gap |
|---|---|---|
| name/user mandatory, non-empty, safe single components; rejected before any write; no `YOUR_USER`/quote/newline/separator/drive/control char in TOML | ❌ | No validation in CLI; MCP name-empty only; `YOUR_USER` emitted by both; `name="a/../b"` passes MCP `_contained_path`; CLI `name` unguarded entirely |
| init creates `<dataset_root>/<name>.toml`, reports canonical absolute `config_path` + `dataset_root` | ❌ | Envelope/schema lack the fields (mcp_server.py:1828-1833, 2098-2108); CLI prints relative path only |
| Omitted MCP cwd: live CWD only when inside root; else fail closed, actionable, never parent root | ❌ | Both parent-root branches (L1707-1710) silently select root; `except Exception` (L1711) also falls back |
| Every subsequent config-bearing call uses returned `config_path`; no default-name guessing in canonical workflow | ⚠️ | MCP already explicit (MSP-R10); CLI still guesses `default_config_name` — canonical workflow is MCP; prompts/docs (L2242-2313) already carry config-path placeholders |
| `DatasetConfig.from_toml(path, discovery_root=server_root)` bounds MCP discovery; CLI compatible without bound | ❌ | Param missing; `_bound_discovery` is the workaround |
| Relative output overrides anchor to `config_path.parent` in both adapters | ❌ | MCP server-root; CLI single-file cwd-relative; CLI batch already `cfg._base_dir` ✓ |

## Existing tests that must change (and boundary patterns)

- `tests/test_cli.py:91-187` `TestInitCommand` — direct `cli._cmd_init(Namespace(...))`; **L117 and L187 assert `YOUR_USER` is generated** → flip to pre-write rejection (or require `--user`).
- `tests/test_mcp_server.py:2396-2409` `test_cwd_none_back_compat` — asserts cwd=None → server root (parent) even though live CWD would be the child → **must become fail-closed** (or child-anchored).
- `tests/test_mcp_server.py:2502-2549` `TestInitAutoCwd` — `test_auto_cwd_inside_root` (L2505, strict-descendant case) survives; `test_auto_cwd_outside_fallback` (L2521-2534, silent parent fallback) **must become fail-closed**; `test_explicit_cwd_still_overrides_auto` (L2536) survives.
- `tests/test_mcp_server.py:2248-2263` — name `../evil`/`/abs/evil`/`C:/evil` already rejected via `_contained_path` ✓ (keep); add `a/../b`, quotes/newline/control-char name/user cases.
- Boundary patterns (from archived `test-mcp-boundary-hygiene`, PR #132): registered tools via `Client(server)` + shared `call_tool`/`_call` (`conftest.py:140-168`, `mcp_payload` L97-137); stdio via module-scoped `McpStdioServer` fixture (`conftest.py:217-240`, cwd = server root = dataset dir — **no parent/child layout exists yet**); CLI via `run_cli` subprocess (`conftest.py:171-214`). PB-01 (`process-boundary/spec.md:9-56`) forbids boundary-hiding direct calls; PB-04 nested-output scenario (L124-128) currently proven only via `monkeypatch.chdir` + `build_server` (`test_mcp_process.py:98-118`) — **insufficient per the ground truth**: the fix's tests MUST launch the real MCP process with parent server root + intended child cwd over stdio.
- Envelope projection: `sofer_init` output_schema (`mcp_server.py:2098-2108`) drops undeclared keys at the boundary → `config_path`/`dataset_root` MUST be added to the schema or they are invisible to clients (same mechanism documented in PB-03).

## Approaches

1. **New shared module `src/sofer/execution_context.py` (recommended)** — single home for identity: `validate_identity(name, user) -> list[str]` (safe single components + placeholder ban), `resolve_dataset_root(cwd, live_cwd, server_root) -> Path | IdentityError` (strict-descendant fail-closed policy), `identity_for(root, name, user) -> DatasetIdentity` (dataclass with absolute `dataset_root`/`config_path`). Both adapters delegate; `from_toml` gains `discovery_root: Path | None = None`; MCP `sofer_init` envelope/schema gain `config_path`+`dataset_root`; MCP output overrides re-anchor to `config_path.parent`; CLI single-file `--output` anchors to the input's parent.
   - Pros: one testable contract (AGENTS.md rule 4); small diffs in `cli.py`/`mcp_server.py`; `_bound_discovery` removable; pure functions easy to unit-test.
   - Cons: new module + wider test churn (~150-250 test lines); strict-descendant edge: server root == dataset root deployments fail closed on cwd=None (caller passes `cwd=root` explicitly — document).
   - Effort: Medium.
2. **Fix in-place per adapter** — duplicate validation + fail-closed branches in `_cmd_init` and `sofer_init`.
   - Pros: no new module; smallest immediate diff.
   - Cons: duplicated logic (AGENTS.md rule 4); identity contract drifts again; harder for a lower-capability agent to test.
   - Effort: Low-Medium.
3. **Validate in `model.py` only** — extend `DatasetConfig` with pre-write validation; leave path/cwd resolution as-is.
   - Pros: touches the config model only.
   - Cons: misses the cwd/root half of the contract (the actual bug); adapter divergence persists.
   - Effort: Low (incomplete).

## Recommendation

**Approach 1** — create `src/sofer/execution_context.py` with:

- `DatasetIdentity` dataclass: `name`, `user`, `dataset_root: Path` (absolute, resolved), `config_path: Path` (`dataset_root / f"{name}.toml"`).
- `validate_identity(name, user) -> list[str]` — both mandatory non-empty; single component (no `/`, `\`, no `ntpath.splitdrive` drive/UNC, no `..`/`.` components, no quotes, no newlines/control chars, no leading/trailing whitespace); `user` must match `^[\w\-]+$` and must not be a placeholder (`YOUR_USER`, plus reuse `model._PLACEHOLDERS` normalized); rejects BEFORE any write (issue criterion 1).
- `resolve_dataset_root(cwd, *, live_cwd: Path, server_root: Path) -> Path` — `cwd` given → contained under `server_root` (reuse `_contained_path`-equivalent, must not exist required); `cwd` None → `live_cwd` only when `live_cwd != server_root.resolve() and live_cwd.is_relative_to(server_root.resolve())` (strict descendant); otherwise raise `IdentityResolutionError` with an actionable message naming the required `cwd` argument (issue criterion 3). CLI passes no server bound (dataset_root = resolved process cwd; still strict-descendant-free — CLI identity is explicit by construction).
- `report_identity(identity) -> dict` — canonical absolute `config_path`/`dataset_root` strings for the MCP envelope (issue criterion 2).
- Adapter deltas: `_cmd_init` (validate → resolve → write → print absolute config_path); `sofer_init` (validate → resolve with server_root → write → envelope + schema with `config_path`/`dataset_root`); `model.from_toml(path, discovery_root=None)` passes `stop_at=discovery_root` into `config.reload` (issue criterion 5, retire `_bound_discovery`); MCP config-bearing tools resolve relative `output_dir` overrides against the contained `config_path.parent` and single-file tools against the input's parent (issue criterion 6).
- Spec deltas (proposal phase): MODIFIED INIT-02 (fail-closed cwd=None + strict-descendant), MODIFIED INIT-03 (identity reporting fields), ADDED identity-validation requirement (replaces the YOUR_USER back-compat tests), MODIFIED MSP-R10 (from_toml discovery_root), MODIFIED TC-05 note, new process-boundary scenario (real-process parent/child stdio launch per ground truth, PB-09-compliant second module-scoped fixture).

**Test-plan direction**: new stdio test spawning `sofer-mcp` with cwd = parent root and an existing child dataset dir, asserting (a) cwd omitted → input-required refusal and no parent TOML, (b) `cwd=child` → `child/test.toml` + `raw/` + envelope `config_path`/`dataset_root`; CLI parity via `run_cli` subprocess (PB-02); identity matrix unit tests on `validate_identity`/`resolve_dataset_root`; update the four stale tests listed above; add `config_path`/`dataset_root` to the `sofer_init` output_schema assertions in `test_mcp_schema.py`.

**Review-budget forecast**: production ~120-200 lines (new module + adapter edits); tests ~150-250. Single PR likely within the 400-line budget; tasks phase should re-verify. **Decision needed before apply: Yes** (strict-descendant edge for root==dataset-root deployments; whether CLI keeps `--user` optional-but-rejected or required).

## Risks

1. **Strict-descendant edge**: a host that configures the server root to BE the dataset directory (root == live CWD) would now fail closed on cwd=None — behavior change beyond the issue's reproduction; document `cwd=root` as the explicit fix. Decide explicitly in the proposal.
2. **Boundary schema projection**: `config_path`/`dataset_root` silently dropped unless added to `sofer_init`'s `output_schema` (same mechanism as PB-03) — must land in the same change or clients never see them.
3. **Spec drift already present**: live `mcp-server` INIT-02 ("cwd None back-compat") contradicts the Approach-2 code — the delta must supersede it cleanly or archive-time merge will conflict.
4. **Stale tests asserting placeholder generation** (`test_cli.py:117/187`) and parent-root fallback (`test_mcp_server.py:2399-2409, 2521-2534`) will fail after the fix — they are intentional removals, not regressions; verify-report must treat them as expected.
5. **Real-process test cost**: PB-09 lean-spawn bound requires a second module-scoped stdio fixture (parent/child layout); keep one spawn per module.
6. **CLI `default_config_name` guessing** remains for non-canonical CLI use (TC-07 bootstrap); criterion only bans guessing in the *canonical workflow* — keep CLI behavior, don't over-remove.
7. `SOFER_TRACE.md` must stay untracked/untouched (PB-08).

## Ready for proposal

Yes. Orchestrator should tell the user: single-PR change; new `execution_context.py` shared identity module; fail-closed cwd semantics replace both silent parent-root branches; init envelope/schema gains `config_path`/`dataset_root`; `from_toml(discovery_root=...)` retires `_bound_discovery`; relative output overrides anchor to `config_path.parent` in both adapters; 4 existing tests flip (2 placeholder-generation, 2 parent-fallback) and a real-process stdio test with parent-root/child-cwd layout is mandatory per the ground truth; strict-descendant edge (root == dataset dir) needs an explicit decision.