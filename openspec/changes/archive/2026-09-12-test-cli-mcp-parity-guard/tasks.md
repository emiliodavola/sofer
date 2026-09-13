# Tasks: test-cli-mcp-parity-guard

Test-only change closing the systemic root cause behind #152/#153/#154/#155:
a CLI↔MCP surface parity guard. Zero production changes.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~360 (1 new test file + 3 change docs) |
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
| 1 | Guard test + change docs | PR 1 | Single test-only PR on `dev`; no production files touched |

## Phase 1: Introspection helpers (TDD base)

- [x] 1.1 `_cli_surface()`: walk `_build_parser()`; per subcommand collect
      normalized flags (longest `--` option, `-`→`_`, `--help` filtered as
      argparse infrastructure) and positional dest names; flatten nested
      `mcp add`/`mcp remove`.
- [x] 1.2 `_tools_dict(tmp_path)`: `build_server(root=...)` + fastmcp
      `Client.list_tools()` (mirror `test_mcp_schema.py` boundary).

Evidence 1.1-1.2: `uv run pytest tests/test_parity.py -q` collects clean.

## Phase 2: Area declarations + assertions (the guard)

- [x] 2.1 `AreaParity` dataclass + 9 `AREAS` entries (validate, prepare,
      publish, codebook, profile, render, init, scan, auth_status) with
      `flag_map` (incl. renames `output→output_dir`, `no_checks→run_checks`,
      positional `csv→path`), `exempt_flags`/`exempt_params` (reason inlined),
      `known_gaps` = {#153 × 4: publish clean/clean_cache; #154 × 2: scan ext;
      #155 × 1: codebook_all max_sample}.
- [x] 2.2 Assertions A1-A6 per area (declared-exists; every CLI flag declared;
      every positional declared; mapped params exist in a tool; every MCP
      param mapped-or-exempt; known gaps still hold as negative asserts).
- [x] 2.3 Roster test: declared tools ⊆ 14-tool roster; the two by-design
      asymmetries (auth_status MCP-only, mcp CLI-only) stay documented.

Evidence 2.1-2.3: `uv run pytest tests/test_parity.py -q` → 11 passed.

## Phase 3: Mutation probe (detection evidence)

- [x] 3.1 Temporarily add `--noop` to the scan parser in `src/sofer/cli.py`;
      expect A2 failure `['noop']`; revert immediately (no production diff
      remains; `git status` shows only the new test + change docs).

Evidence 3.1: targeted run fails with `scan: CLI flags without MCP
mapping/exemption: ['noop']`; working tree clean of mutations.

## Phase 4: Full gates

- [x] 4.1 `uv run pytest tests/ -q` → 1506 passed, 6 skipped, 0 failed
      (1495 baseline + 11 new).
- [x] 4.2 `uv run ruff check src/ tests/` → clean.
- [x] 4.3 `uv run mypy src/` → clean.
- [x] 4.4 `git diff --check` → clean.