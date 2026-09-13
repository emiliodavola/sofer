# Proposal: fix-scan-parity-mcp

## Intent

Close open issues #152 (MCP `sofer_scan_apply` skips the CLI's Phase-1
move-to-`raw/`) and #154 (CLI `--ext` filter not exposed on the MCP scan
tools). Both are CLI↔MCP parity gaps of the scan surface, declared as
`known_gaps` in the parity guard (`tests/test_parity.py`, PR #163): this
change flips them to `flag_map` (extensions) / a documented MCP-only exemption
(`move_loose`) as its RED→GREEN step, and updates the encoded spec (MSP-R06
codified the cache-only scan chain).

## Scope

### In Scope
- `sofer_scan_dry_run` and `sofer_scan_apply` gain `extensions: list[str] | None`
  (validated/normalized against `SUPPORTED_FORMATS`, accepts `"csv"`/`.csv`)
  and `move_loose: bool = False` (Phase-1 move of loose files outside
  `raw/`/`cache/`/`EXCLUSIONS` into `raw/` preserving the relative tree,
  collision-abort before any move, dry-run preview, never silent).
- `sofer_scan_apply` envelope gains `moved: int` (declared in `output_schema`);
  dry-run reports `move_loose=True` hint when loose files exist without it.
- Parity guard: `ext` moved `exempt_flags/known_gaps` → `flag_map`
  (`ext → extensions`); `move_loose` added as documented MCP-only exemption.
- Spec delta: MODIFIED MSP-R06 + NEW MSP-R14 (extensions) + NEW MSP-R15
  (Phase-1 move opt-in) in `specs/mcp-server/spec.md`; scenarios per requirement.
- Tests: 9 new (loose→raw move, opt-in default guard, collision abort
  atomically, dry-run preview no-mutation, move_loose hint, extensions filter
  apply+dry-run, invalid extension refused, filters both phases).

### Out of Scope
- CLI changes (`cli.py` untouched — the CLI already implements Phase 1 + `--ext`).
- The pre-cache legacy layout (`local = "data.csv"` direct): Phase-1 move does
  not distinguish registered state from physical location (CLI parity); a
  registered-but-loose file is moved like any loose file. Documented behavior.
- `sofer_init` (`move_existing` stays the init opt-in; unchanged).

## Capabilities

### New Capabilities
- `mcp-server`: `extensions` on both scan tools; `move_loose` opt-in Phase-1
  move on both scan tools; `moved` count on `sofer_scan_apply`.

### Modified Capabilities
- `mcp-server` MSP-R06: the scan chain is no longer cache-only — with
  `move_loose=True` it chains
  `discover_files(exclude raw/) → check_raw_collisions → move_to_raw →
  discover_files → check_flatten_collisions → merge_entries → copy_files →
  write_toml`.

## Approach

- Reuse only shared scanner primitives (`discover_files`, `check_raw_collisions`,
  `move_to_raw`, `copy_files`, `merge_entries`, `write_toml`) — zero duplicated
  orchestration; `check_raw_collisions` was the only missing import.
- `_normalize_scan_extensions` validates against `SUPPORTED_FORMATS` (leading
  dot, lowercase) and raises `ValueError` → refusal envelope.
- `move_loose` is an explicit opt-in (`False` default): the explicit call IS the
  confirmation (MCP non-interactivity, MSP-R06), never a silent move; collisions
  abort with `registered: 0` before any move.
- TDD: 9 behavior tests written first (RED — schema rejection), implementation
  (GREEN), parity guard flip last (RED→GREEN by design).

## Decision Points

| # | Decision | Recommendation | Tradeoff |
|---|----------|----------------|----------|
| 1 | `move_loose` default | **False** (opt-in) | Current behavior untouched; the issue's "never a silent move" contract; hints steer agents |
| 2 | `extensions` format | **Accept `"csv"` and `.csv`** | `discover_files` already normalizes; `SUPPORTED_FORMATS` keys (.dot) are the validation set |
| 3 | Legacy registered-loose files | **Do not special-case** | CLI parity (move is physical); the legacy layout is a test fixture, not a recent real flow; out of scope |
| 4 | `moved` in envelope | **Yes, declared in output_schema** | fastmcp filters envelope fields against `output_schema`; undeclared keys silently drop |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modified | scan tools + helper + import + output_schema |
| `tests/test_mcp_server.py` | Modified | 9 new tests + `_scanned_dataset` fixture helper |
| `tests/test_parity.py` | Modified | scan area: flips #154 gap, adds #152 exemption |
| `openspec/changes/…/specs/mcp-server/spec.md` | New | MODIFIED MSP-R06 + NEW MSP-R14/15 |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Registered-loose legacy files relocated by move | Low (fixture-only layout) | CLI-parity behavior, documented in spec |
| fastmcp output_schema filtering surprises | Med | `moved` declared in schema; covered by tests |
| Guard RED→GREEN ordering confusion | Low | `known_gaps` negative asserts fail loudly at the flip |