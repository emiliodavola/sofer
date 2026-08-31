# Tasks: feat-mcp-auto-install

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~95–110 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (no split) |
| Delivery strategy | single-pr (auto-forecast single PR) |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Promotion + guard + READMEs + tests + lock (all 6 spec-mandated items) | PR 1 → main | Single PR, ~100 lines, autonomous scope, rollback = revert pyproject/guard/READMEs + `uv lock` |

## Phase 1: Packaging foundation

- [x] 1.1 Edit `pyproject.toml` — add `fastmcp>=3.4,<4` to `[project].dependencies`; keep `[project.optional-dependencies].mcp` identical pin as alias; verify `[dependency-groups].dev` pin identical (3 places)
- [x] 1.2 Regenerate `uv.lock` via `uv lock` — verify `sofer` entry lists `fastmcp` under `dependencies` not `optional-dependencies` (MSP-R02 uv.lock scenario)

## Phase 2: Core — degraded guard

- [x] 2.1 Update `src/sofer/mcp_server.py:55-59` guard `ImportError` message to mention both `pip` and `uv tool` with PEP 508 `sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z` (never `git+...[mcp]`); keep `raise ... from _exc` and `pragma: no cover` (MSP-R02 guard scenario) — depends on 1.1

## Phase 3: Documentation (parallelizable after Phase 1)

- [x] 3.1 Edit `README.md` — fix Install: canonical `pip install "sofer @ git+...@vX.Y.Z"` + `uv tool install "sofer @ git+..." --force` + alias note `sofer[mcp] @ ...`; add `uvx --from git+... --with "sofer[mcp]" sofer-mcp --help`; flip AI/MCP intro to included-by-default alias; remove every `git+...[mcp]` (MSP-R12 scenarios)
- [x] 3.2 Edit `README_ES.md` same commit — mirror `README.md` headings/order/code blocks per AGENTS.md §13 (Spanish prose, English commands identical); same fixes as 3.1 — parallel with 3.1, depends on 1.1

## Phase 4: Tests

- [x] 4.1 Update `tests/test_mcp_server.py` — invert `TestImportWithoutExtra`/guard tests to assert `import fastmcp` succeeds on lean install and `Requires-Dist` unconditional; add/keep `sys.modules` monkeypatch guard test asserting message contains `pip`, `uv tool`, `sofer[mcp] @ git+https://` and NOT `git+...[mcp]` — depends on 2.1
- [x] 4.2 Add/keep wheel METADATA checks in `tests/test_mcp_server.py` (`TestWheelPackaging`): `Requires-Dist: fastmcp>=3.4,<4` without `extra == 'mcp'` and `Provides-Extra: mcp` alias — depends on 1.1

## Phase 5: Verification

- [x] 5.1 Run `uv lock && uv run ruff check --fix && ruff format && mypy src/ && pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` — green
- [x] 5.2 Smoke `python -c "import fastmcp; import sofer.mcp_server"`; `uv tool install "sofer @ git+...@vX.Y.Z" --force` → `sofer-mcp --help` ok; alias `sofer[mcp] @` also ok (manual)
- [x] 5.3 `uv build` → inspect `METADATA`/`entry_points.txt` for unconditional `fastmcp` and both `sofer`+`sofer-mcp` (PKG-03/06)

Parallelizable: 3.1∥3.2 after Phase 1; 4.1∥4.2 after Phase 2; Phase 5 after all. Dependencies: `1.1→1.2→2.1→4.x→5.x` and `1.1→3.x→5.x`.

Estimates: pyproject +1, uv.lock ~30, mcp_server ~4, README ~27, README_ES ~27, tests ~10 → **~100 lines** (well under 400/2000).
