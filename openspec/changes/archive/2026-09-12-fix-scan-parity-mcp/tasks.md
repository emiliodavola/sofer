# Tasks: fix-scan-parity-mcp

Closes #152 + #154: scan parity CLI↔MCP (Phase-1 move opt-in + extensions
filter). Flipped from the parity guard's `known_gaps`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~330 (mcp_server + tests + guard + spec delta) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main (not needed) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Implementation + tests + guard flip + spec delta | PR 1 | Single scan-parity PR on `dev` |

## Phase 1: Tests (RED)

- [x] 1.1 `tests/test_mcp_server.py`: `_scanned_dataset` fixture helper
      (post-scan layout: registered file already in `cache/`, so the only loose
      file is the one under test).
- [x] 1.2 `TestScanMoveLoosePhase` (5): move to raw + cache copy + TOML
      register; default opt-in leaves files loose; collision aborts atomically;
      dry-run previews without mutation; dry-run hints move_loose.
- [x] 1.3 `TestScanExtensionsFilter` (4): apply filter; dry-run filter;
      invalid suffix refused; extensions filter both phases with move.

Evidence 1.1-1.3: RED — 8 failed (schema rejection `unexpected_keyword_argument`),
1 passed (default opt-in guard).

## Phase 2: Implementation (GREEN)

- [x] 2.1 `mcp_server.py`: import `check_raw_collisions` + `SUPPORTED_FORMATS`.
- [x] 2.2 `_normalize_scan_extensions` helper (validate/normalize, ValueError).
- [x] 2.3 `sofer_scan_dry_run(config, extensions=None, move_loose=False)`:
      Phase-1 preview + collision refusal + `move_loose=True` hint when loose
      files exist without it.
- [x] 2.4 `sofer_scan_apply(config, force=False, extensions=None, move_loose=False)`:
      Phase-1 MOVE (atomic collision abort), `moved` in successful envelope,
      print move lines (parity with sofer_init).
- [x] 2.5 Register `moved: {"type": "integer"}` in `sofer_scan_apply`'s
      `output_schema` (fastmcp filters envelope fields against it).

Evidence 2.1-2.5: `uv run pytest tests/test_mcp_server.py -k "MoveLoose or
ExtensionsFilter"` → 9 passed.

## Phase 3: Parity guard flip (RED→GREEN, by design)

- [x] 3.1 `tests/test_parity.py` scan area: `ext` → `flag_map`
      (`ext → extensions`), `known_gaps` entries removed, `move_loose` added
      as documented MCP-only exemption (#152).

Evidence 3.1: `uv run pytest tests/test_parity.py tests/test_mcp_server.py -q`
→ 231 passed, 3 skipped (guard GREEN after the flip).

## Phase 4: Spec delta + verify + gates

- [x] 4.1 Spec delta `specs/mcp-server/spec.md`: MODIFIED MSP-R06 + NEW
      MSP-R14 (extensions) + NEW MSP-R15 (Phase-1 move opt-in) with scenarios.
- [x] 4.2 Full suite + ruff + ruff format + mypy + `git diff --check`.
- [x] 4.3 Verify report + archive on merge.