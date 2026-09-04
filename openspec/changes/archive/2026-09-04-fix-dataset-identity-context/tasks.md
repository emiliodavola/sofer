# Tasks: fix-dataset-identity-context

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500-650 |
| 400-line budget risk | High |
| 800-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | auto-chain (auto-forecast) |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High
800-line budget risk: Medium

### Suggested Work Units (feature-branch-chain: PR #1 base = tracker `fix/116-dataset-identity-context`; each child bases on the previous PR branch; only the tracker merges to dev)

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | execution_context + model.from_toml + unit tests | PR 1 (base=tracker) | `uv run pytest tests/test_execution_context.py tests/test_model.py -q` | N/A — pure unit matrix; mypy + ruff gate | Revert PR 1 — unused module + optional param; zero behavior change |
| 2 | MCP adapter + boundary/schema tests + sweep | PR 2 (base=PR 1) | `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` | In-process `build_server` + `Client(server)` | Revert PR 2 — old back-compat init + envelope/schema; tests flip back |
| 3 | CLI `--user` required + rejections + anchors + README pair + CLI tests | PR 3 (base=PR 2) | `uv run pytest tests/test_cli.py -q` | `run_cli` subprocess (cp1252 env) | Revert PR 3 — argparse default + relative print; no MCP impact |
| 4 | conftest parent-root fixture + process sweep + TestParentRootIdentity | PR 4 (base=PR 3) | `uv run pytest tests/test_mcp_process.py -q` | Real `sofer-mcp` stdio spawn (one/module) | Revert PR 4 — fixture + process tests; production untouched |

## Phase 1: Foundation — execution_context + model (Slice 1)

- [x] 1.1 Create `src/sofer/execution_context.py`: module docstring; `DatasetIdentity` (frozen, `config_path` derived property, `from_parts`); `validate_identity`; `resolve_dataset_root` (3 modes per D5); `report_identity`; `IdentityResolutionError` (message names `cwd=<dataset dir>`); `_USER_RE`; stdlib + `model._PLACEHOLDERS` imports only
- [x] 1.2 `model.py:from_toml` gains `discovery_root: Path | None = None` → `config.reload(base_dir, stop_at=discovery_root)` (L378); docstring notes the bound (TC-05)
- [x] 1.3 Create `tests/test_execution_context.py` matrix: validate_identity (valid→`[]`; None/""/" "/placeholder/`a/b`/`a\b`/`C:/evil`/`.`/`..`/quotes/newline/control/whitespace/user-regex per INIT-05); resolve_dataset_root (no-bound, strict-descendant, root==live, outside, explicit-cwd contained/escape — mode (b) unit-only per S7); report_identity/from_parts invariants
- [x] 1.4 `tests/test_model.py` TC-05 bound tests (conftest `pytree`): pyproject above + inside `discovery_root` → only at-or-below applies; omitted bound stays unbounded
- [x] 1.5 Gate-review correction (Finding 1): `from_toml` passes `stop_at` to `config.reload` ONLY when `discovery_root` is set — the unbounded CLI path keeps the byte-identical `reload(base_dir)` call shape (TC-04 spy accepts no keywords); full suite re-verified green (1318 passed, 2 skipped on branch vs 1269 dev baseline, delta = 49 new tests, 0 regressions)
- [x] 1.6 Gate-review suggestion S2: mode (b) matrix cells added — `expanduser` (`~`) step and `cwd == root` accepted equality case

## Phase 2: MCP adapter (Slice 2)

- [x] 2.1 Rework `sofer_init` (mcp_server.py:1647-1833) validate→resolve→write: `validate_identity` → `_refusal(CONFIG_ERROR)`; cwd=None strict-descendant → envelope refusal naming cwd (`next: {}` per S8); str-cwd keeps `_contained_path` → `PathOutsideRootError`; delete placeholder fallback L1727; update Field descriptions/docstrings L1662/1668/1674/1687
- [x] 2.2 PB-03 same change: `config_path`/`dataset_root` (absolute strings) in 3 success envelopes (L1795/1809/1828) AND `output_schema` (L2098-2108, 2 string props, `required` unchanged); refusals carry none
- [x] 2.3 Delete `_bound_discovery` (def L457-471 + call sites L524/1252/1367-region/1440); add `discovery_root=_get_root()` at 4 `from_toml` sites (L520/1245/1367/1433) per MSP-R10
- [x] 2.4 Re-anchor relative outputs: 6 config-bearing `root=cfg._base_dir` (L775/851/1006/1114/1265/1387); 3 single-file `root=input.parent` (L1070/1177/1319)
- [x] 2.5 `tests/test_mcp_schema.py`: `sofer_init` output_schema declares `config_path`/`dataset_root` string props, not in `required` (MSP-R03, PB-03)
- [x] 2.6 Boundary tests: envelope-identity assert (INIT-03); repurpose L2199-2204 → placeholder refusal, no TOML/raw (INIT-05); new unsafe-name refusals `a/../b`/quotes/newline/control; flip L2245-2263 traversal ToolError→envelope; flip L2399-2409 + L2521-2534 → fail-closed; L2422-2429/L2641-2646 keep ToolError; new MSP-R10 anchoring test (`proj/build`, not root/build)
- [x] 2.7 Sweep region A (L2154-2263) + B (L2265-2410): add `"user": "testuser"` + explicit `cwd` to every `sofer_init` call; template asserts → `user="testuser"` (L2157/2170-2172/2300-2302)
- [x] 2.8 Sweep region C (L2410-2646): add user+cwd (skip L2576 — already correct); keep containment expectations

## Phase 3: CLI + docs (Slice 3)

- [x] 3.1 `_cmd_init` (cli.py:851): validate first (exit 1, one line per error); `dataset_root = resolve_dataset_root(None, live_cwd=Path.cwd().resolve())`; `output`/`raw_dir_path` derived from it; `user_val = args.user`; absolute `OK  Created {output}` (L841-858 + 4 move branches)
- [x] 3.2 argparse `--user required=True` + help text (L1301-1309) → exit 2 naming `--user`, no write (CLI-R07)
- [x] 3.3 CLI single-file `--output` anchors: `_cmd_codebook` L219, `_cmd_profile` L292, `_cmd_render` L361 (input's parent); batch already `cfg._base_dir`-anchored
- [x] 3.4 `tests/test_cli.py`: flip L117 (user="alice", repo `alice/test-ds`); repurpose L187 → rejection tests (handler rc 1 + subprocess rc 2, no TOML); parser L22-27 gains `--user alice` + required-flag sibling test; add `--user` to TestInitCommand calls; new print test (rc 0, absolute `config_path` in stdout); new rc-1 tests (placeholder/unsafe)
- [x] 3.5 README.md + README_ES.md same commit (rules 7/13): `init <name>` row (L318/330) + `--user` row (L348/360) → required, pre-write rejection, absolute config_path print; technical text stays English

## Phase 4: Real-process stdio (Slice 4)

- [x] 4.1 `tests/conftest.py`: second module-scoped `mcp_stdio_parent_root` (PB-09): `tmp_path_factory.mktemp` + `(parent / "child").mkdir()` → `McpStdioServer(cwd=parent)`; one spawn per module
- [x] 4.2 `tests/test_mcp_process.py` sweep: user+cwd at L113 (TestNestedCwd), L162-206 (TestRecoveryInit template → `user="testuser"`), L262 (greenfield)
- [x] 4.3 New `TestParentRootIdentity` (PB-04): (a) cwd omitted → refusal naming cwd, no parent `test.toml`/`raw/`; (b) `cwd="child"` → `child/test.toml` + `child/raw/` exist, parent absent, envelope absolute identity

## Phase 5: Verification (per-slice gate)

- [x] 5.1 Each slice: `uv run pytest tests/ -q` (re-baselined count), `uv run mypy src/`, `uv run ruff check src/ tests/` + `ruff format --check`, `git diff --check`
- [x] 5.2 Slice 3: no `SOFER_TRACE.md` touch (PB-08); README/README_ES both updated (rule 13)

Scenario map: INIT-02 (7), INIT-03 (4), INIT-05 (5), MSP-R03 (4), MSP-R10 (5 — delimiter/encoding + no-default-config-name verified by existing tests, no code change), CLI-R07 (11 existing + 4 new), TC-05 (2), PB-04 (5 existing re-verified + 2 new), PB-09 (2 existing + second-fixture rule). Threat matrix: all N/A — no RED tests.