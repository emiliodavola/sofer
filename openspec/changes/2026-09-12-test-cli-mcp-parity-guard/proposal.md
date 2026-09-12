# Proposal: test-cli-mcp-parity-guard

## Intent

Close the systemic root cause behind open issues #152 (scan move-to-raw
missing in MCP), #153 (publish cleanup not exposed), #154 (scan `--ext` not
exposed), #155 (batch `max_sample` missing): **nothing compared the CLI flag
surface against the MCP tool parameter surface**, so CLI flags routinely
landed without an MCP counterpart and vice versa. Test-only; zero production
changes. The guard is the regression net that makes the whole issue class
caught, and its `known_gaps` mechanism makes the fixing changes' RED→GREEN
self-enforcing.

## Scope

### In Scope
- New `tests/test_parity.py`: introspects `cli._build_parser()` (flags +
  positionals per subcommand, nested `mcp add/remove` flattened) and the MCP
  tool schemas via `build_server(root=...)` + fastmcp `Client.list_tools()`
  (same boundary technique as `test_mcp_schema.py`).
- Per-area `AreaParity` declarations for all 9 CLI command areas that have an
  MCP counterpart (validate, prepare, publish, codebook, profile, render,
  init, scan) plus the MCP-only `sofer_auth_status`; deliberate asymmetries
  are documented inline with reasons (actor-driven gates, batch `*_all`
  redesign, CLI-only registration).
- `known_gaps` entries referencing #153/#154/#155 asserting the param is
  **absent** today; the fixing change flips each into `flag_map` (RED) then
  implements (GREEN). Moving a gap without fixing it fails the suite.
- Mutation-probe evidence: the guard detects an undeclared CLI flag (verified
  with a temporary `--noop` on scan, reverted after the run).

### Out of Scope
- Behavioral parity (e.g. scan Phase-1 move-to-raw semantics of #152, publish
  gating, dry-run defaults) — surface-encoded by design; covered by behavior
  tests in their own fixing changes.
- Any `src/sofer/` change; spec deltas; README; `mcp add/remove` itself
  (documented as deliberately CLI-only).

## Capabilities

### New Capabilities
None (test infrastructure only).

### Modified Capabilities
None.

## Approach

- Introspection helpers: `_cli_surface()` walks `_build_parser()` subparsers
  (argparse private API, `--help` filtered as infrastructure; alias
  collapsed to the longest `--` option); `_tools_dict(tmp_path)` mirrors
  `test_mcp_schema._tools_dict` (fastmcp `Client` over `build_server`).
- `AreaParity` dataclass: `cli_command`, `mcp_tools`, `flag_map` (incl.
  deliberate renames `output→output_dir`, `no_checks→run_checks`, positional
  `csv→path`), `exempt_flags`/`exempt_params` (reason inlined),
  `known_gaps` (`(param, tool) → issue ref`).
- Six assertions per area (A1 declared-exists, A2 every CLI flag declared,
  A3 every positional declared, A4 mapped params exist in a tool, A5 every
  MCP param mapped-or-exempt, A6 known gaps still hold).
- `PARITY` coverage union equals the full 14-tool roster; `sofer_auth_status`
  and `mcp` remain the two documented by-design asymmetries.

## Decision Points

| # | Decision | Recommendation | Tradeoff |
|---|----------|----------------|----------|
| 1 | `--help` in surface? | **Exclude** (argparse auto-add) | Including forces an exemption on every area with no value |
| 2 | Alias collapse (e.g. `--clean-cache`/`--all`) | **Longest `--` option wins** | `clean_cache` is the canonical dest; short alias ignored |
| 3 | `known_gaps` as negative asserts vs plain comment | **Negative asserts that fail on fix** | Fixing a gap without re-declaring breaks CI — the RED step is explicit |
| 4 | Behavior vs surface for #152 | **Out of scope (surface guard)** | Phase-1 move has no flag; belongs to the fixing change's behavior tests |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `tests/test_parity.py` | New | The parity guard (~340 lines incl. declarations) |
| `src/sofer/*` | None | Read-only reference |
| `openspec/specs/*` | None | No delta (test-only) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Guard becomes brittle on fastmcp introspection changes | Low | Same `Client(server)` boundary as existing schema tests; failures are informative |
| Declaration table drifts from intent | Med | Exemption reasons reference specs/issues; `--fix-me` free — the guard forces the decision at merge time |
| New legitimate asymmetries blocked | Low | Adding an exemption with a documented reason is the intended workflow |