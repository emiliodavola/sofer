# Verify Report: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

**Change**: `docs-readme-veracity-sweep`
**Branch**: `docs/readme-veracity-sweep`
**Work-unit commit**: `710a3e5`
**Mode**: ODD (documentation-only; no runtime boundary)

## Scope Verified

| Issue | Acceptance criterion | Result |
|-------|----------------------|--------|
| #183 | Both READMEs state 14 tools / 4 resources / 3 prompts | PASS |
| #183 | Resource list includes `sofer://status`; fields match `_resource_status` | PASS |
| #183 | README.md and README_ES.md stay mirrored; no test token removed | PASS |
| #190 | `--force`, `--dry-run`, `--output` rows list every accepting subcommand | PASS |
| #180 | `git grep -i elaze -- README.md README_ES.md` returns nothing | PASS |
| #180 | `user="emiliodavola"` no longer in a published README example | PASS |
| #180 | Examples use generic placeholders consistent with the file precedent | PASS |
| — | `openspec/changes/archive/**` and source byte-unchanged | PASS |

## Runtime Evidence

| Command | Exit | Observed |
|---------|------|----------|
| `uv run pytest tests/test_mcp_server.py tests/test_scanner.py -q -k "BuildClarityReadme or docs_show_diagram"` | 0 | `3 passed, 343 deselected in 5.16s` |
| `uv run pytest tests/ -q` | 0 | `1849 passed, 2 skipped, 1 warning in 297.66s (0:04:57)` |
| `uv run ruff check src/ tests/ scripts/` | 0 | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | 0 | `70 files already formatted` |
| `uv run mypy src/ scripts/` | 0 | `Success: no issues found in 35 source files` |
| `uv run pyright` | 0 | `0 errors, 1 warning, 0 informations` |
| `uv run python scripts/check_test_mapping.py` | 0 | `OK: test-mapping contract holds` |

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` could not be resolved from
source) is pre-existing on `dev`; the source tree is identical to `dev`.

## Static Evidence

- `src/sofer/mcp_server.py` has 14 `server.tool(` and 4 `server.resource(` registrations;
  the runtime `build_server()` reports `tools: 14`, `resources: 1 ['sofer://status']`,
  `resource_templates: 3`, `prompts: 3`.
- CLI re-derivation from the argparse builder confirms the documented flag sets exactly.
- `git grep -i elaze -- README.md README_ES.md` → empty; `git grep 'user="emiliodavola"'
  -- README.md README_ES.md` → empty; all remaining `emiliodavola` are project URLs.
- `git show --stat 710a3e5` touches only `README.md` and `README_ES.md`.

## Independent Verification

A separate read-only sub-agent (`general`) re-derived every claim from the tree and returned
`OVERALL: PASS`. It confirmed the source AND runtime MCP counts, re-derived the argparse
flag sets, confirmed the placeholder greps are empty, ran the focused tests (`3 passed`), and
confirmed the commit scope. Non-blocking caveats it raised: the README abbreviates the
template URI variable names (`{config}` vs the actual `{config_path*}`) — a pre-existing
simplification, count unaffected; and `-o` is a `codebook`-only short alias.

## Limitations

- No spec-governed behavior changes, so there is no scenario-mapped guard for the README
  surfaces; evidence is static inspection, the existing suite, and the focused README tests.
- The optional `tests/test_docs_placeholders.py` guard from #180 was not added (conditional
  in the issue; out of the maintainer's decided file scope).

## Result

All acceptance criteria verified; full suite and gates green. Ready for archive.
