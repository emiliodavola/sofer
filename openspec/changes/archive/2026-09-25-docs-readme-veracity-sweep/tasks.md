# Tasks: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~34 authored (README.md 18, README_ES.md 16); SDD artifacts excluded |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | READMEs agree with the shipped MCP surface, flags and examples | PR 1 | `uv run pytest tests/test_mcp_server.py tests/test_scanner.py -q -k "BuildClarityReadme or docs_show_diagram"` | N/A (docs) — full `uv run pytest tests/ -q` | revert `README.md`, `README_ES.md` |

## Phase 1: MCP surface (#183)

- [x] 1.1 README.md summary row: `11 tools, 3 resources` → `14 tools, 4 resources`.
- [x] 1.2 README.md MCP paragraph: resource list gains `sofer://status`; add the static-resource note.
- [x] 1.3 README_ES.md summary row + MCP paragraph mirrored.

## Phase 2: Flags table (#190)

- [x] 2.1 README.md `--force` row lists `init, prepare, publish, profile, render, scan`.
- [x] 2.2 README.md `--dry-run` row lists `init, publish, scan`.
- [x] 2.3 README.md `--output DIR` row lists `codebook, prepare, publish, profile, render`; description covers `codebook`.
- [x] 2.4 README_ES.md three rows mirrored.

## Phase 3: Placeholders (#180)

- [x] 3.1 README.md: `C:/Users/elaze/...` → `C:/Users/.../...`; `C:\Users\elaze\...` → `C:\Users\...\...`.
- [x] 3.2 README.md: `--user emiliodavola` → `--user <hf-user>`; `user="emiliodavola"` → `user="<hf-user>"`.
- [x] 3.3 README_ES.md mirrored.
- [x] 3.4 `git grep -i elaze -- README.md README_ES.md` returns nothing.

## Phase 4: Verification

- [x] 4.1 Focused README tests green.
- [x] 4.2 Full suite green; ruff/mypy/pyright clean; `check_test_mapping.py` OK.
- [x] 4.3 Independent read-only verification PASS.
- [x] 4.4 Record verify-phase evidence in `verify-report.md`.

## Phase 5: Archive

- [x] 5.1 Move the change folder to `openspec/changes/archive/2026-09-25-docs-readme-veracity-sweep/` (mechanical move, `diff -r` readback).
