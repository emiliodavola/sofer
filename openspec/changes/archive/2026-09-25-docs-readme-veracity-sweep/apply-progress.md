# Apply Progress: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

**Change**: `docs-readme-veracity-sweep`
**Mode**: ODD work-unit commit (Strict TDD disabled per `openspec/config.yaml`; SDD subagent delegation was blocked by the runtime preflight gate, so the orchestrator applied and verified directly)

## Completed Tasks

- [x] 1.1–1.3 MCP surface: 14 tools / 4 resources / 3 prompts + `sofer://status` in both READMEs
- [x] 2.1–2.4 Flags table: `--force`, `--dry-run`, `--output DIR` rows completed in both READMEs
- [x] 3.1–3.4 Placeholders: `elaze` and `emiliodavola` example literals genericised in both READMEs
- [x] 4.1–4.4 Focused tests, full suite, gates, independent verification, verify-report
- [x] 5.1 Archive the change folder

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `README.md` | Modified | Summary row + MCP paragraph + status note; 3 flag rows; placeholder examples |
| `README_ES.md` | Modified | Mirrored edits (AGENTS.md rule 13) |
| `openspec/changes/archive/2026-09-25-docs-readme-veracity-sweep/` | New | This change's artifacts (explore/proposal/design/tasks/apply-progress/verify-report/archive-report) |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Work-unit commit | `710a3e5` — `docs(readme): correct MCP surface counts, flag table, and placeholders (#183, #190, #180)` (README.md +31/−? and README_ES.md, 2 files, +34/−24) |
| Focused test command and result | `uv run pytest tests/test_mcp_server.py tests/test_scanner.py -q -k "BuildClarityReadme or docs_show_diagram"` — `3 passed, 343 deselected` |
| Runtime harness command/scenario and result | N/A — documentation-only; no runtime boundary. Full `uv run pytest tests/ -q` — `1849 passed, 2 skipped, 1 warning in 297.66s` |
| Lint/type/contract gates | `ruff check src/ tests/ scripts/` — All checks passed; `ruff format --check src/ tests/` — 70 files already formatted; `mypy src/ scripts/` — no issues in 35 files; `pyright` — 0 errors, 1 pre-existing `_toml.py` warning; `scripts/check_test_mapping.py` — OK |
| Rollback boundary | `git revert 710a3e5` (or restore both READMEs from `60cb540`); no source/spec/workflow dependency |

## Deviations from Design

One same-class extra beyond #180's enumerated table: the CLI greenfield example
`sofer init test --user emiliodavola` (README.md:149 / README_ES.md:157) was also
genericised to `--user <hf-user>`, because the issue names the personal handle
(`emiliodavola`) as part of the defect and the line is a copy-pasteable example. The MCP
`user="emiliodavola"` literal (README.md:163 / README_ES.md:171) was genericised per the
issue's acceptance criterion.

## Issues Found

None.

## Remaining Tasks

None.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: README veracity triple
- Boundary: `README.md` + `README_ES.md` (+ archived change artifacts)
- Estimated review budget impact: ~34 authored lines (Low)

## Status

17/17 tasks complete. Ready for archive.
