# Archive Report: The batch tools name the path the pipeline really writes

**Change**: `2026-10-15-fix-profile-render-default-paths`
**Archived to**: `openspec/changes/archive/2026-10-15-fix-profile-render-default-paths/`
**Branch**: `fix/294-profile-render-default-paths` (base `dev@b7dea51`)
**Issue**: `emiliodavola/sofer#294`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-server` | Updated | MSP-R03's parameter clause now requires the batch `output_dir` descriptions to name the resolved default path — the artifact-cache write root (`config.OUTPUT_DIR`) joined with the configured sub-directory (`config.PROFILE_DIR` / `config.RENDER_DIR`) — and to state that an override replaces that write root, so artifacts land in `<output_dir>/<sub-directory>`; the bare directory name SHALL NOT be presented as the whole default. One scenario is added ("batch output_dir descriptions name the resolved default"). No requirement added or removed. |

The canonical `openspec/specs/mcp-server/spec.md` was amended in place from the delta's `## MODIFIED
Requirements` block. `mcp-server` is a permanent declared-backlog spec, so no `## Test Mapping` row is
added: `scripts/check_test_mapping.py` exits 0 and reports `mcp-server: 128 scenario(s), unmapped` (was
127), and the registry is untouched.

## Archive Contents

- `proposal.md` — present (intent, scope, D1–D6, 3 risks, rollback, SC-1..SC-5)
- `design.md` — present (the defect with the code lines that contradict the text, the measured
  RED/GREEN, the edit table, the three rejected alternatives)
- `tasks.md` — present, T1–T6 complete
- `specs/mcp-server/spec.md` (delta) — present

## Source of Truth Updated

- `openspec/specs/mcp-server/spec.md` — MSP-R03 as amended.
- `src/sofer/mcp_server.py` — `_batch_output_dir_description(kind, configured_dir)`, used by both batch
  tools' `output_dir` `Field`s; both docstrings' side-effect lines now name the configured key and the
  artifact-cache write root instead of a bare path.
- `tests/test_mcp_schema.py` — `_schema_description` walk + `TestBatchOutputDirDescription` (parametrized
  over the two tools).
- `README.md` / `README_ES.md` — MCP-table rows `4b` / `5b` now say `cache/profiles/` and
  `cache/renders/`, matching the CLI sections that already did; both files changed in the same commit
  (rule 13), with paths kept in English in both.
- `odd/tasks/profile-render-default-paths.md` — the ODD record.

## Verification

| Gate | Command | Result |
|------|---------|--------|
| Focused selection | `uv run pytest tests/test_mcp_schema.py -q -k BatchOutputDirDescription` | **2 failed, 22 deselected** (RED) → packed into the GREEN run below |
| MCP modules | `uv run pytest tests/test_mcp_schema.py tests/test_mcp_server.py -q` | **280 passed, 3 skipped** |
| Full suite | `uv run pytest tests/ -q` | **2152 passed, 9 skipped, 6 warnings** in 105.28s |
| Lint | `uv run ruff check src/ tests/ scripts/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 75 files already formatted |
| Types | `uv run mypy src/ scripts/` | Success: no issues found in 37 source files |
| Types (2nd) | `uv run pyright` | 0 errors, 1 warning (pre-existing `tomli` stub warning in `_toml.py:27`) |
| Spec↔test mapping | `uv run python scripts/check_test_mapping.py` | OK — `mcp-server: 126 scenario(s), unmapped` (was 125) |

The numbers above were measured on this change's content. An earlier run read `2154 passed` and 128
scenarios because the branch was momentarily cut from the `#295` branch and carried its two new tests;
`#295` has since merged (`#309`), and the re-measurement on this change's own bytes reads
`2152 passed, 9 skipped` with `mcp-server: 126 scenario(s)`. Test-count delta from the diff: one
parametrized guard covering two tools (two cases).

## Notes for the reviewer

1. **The issue's first suggestion was not followed literally.** It proposed writing `cache/profiles` into
   the description; the text is instead **derived** from `config.OUTPUT_DIR` + the configured
   sub-directory, because a literal path is the same drift mechanism that produced the issue
   (AGENTS.md rule 1 applied to a documentation string).
2. **Item 2 of the issue was decided, not dropped**: `cache/` stays the default home, and the decision
   with its rationale is recorded in `proposal.md` D4 — moving it is a contract change across `config`,
   `manifest.py`'s managed-directory list, `clean_cache` and the publish path, while the documented
   `--output DIR` route already covers "keep them where I can read them" (`--output` moves the whole
   write root and leaves `cache/` untouched).
3. **Item 3 of the issue is out of scope**, so `#294` is only partially delivered: the PR's closing
   reference is the maintainer's choice (`Closes` would close an issue with item 3 still true;
   `Refs` plus a follow-up issue is the alternative). Flagged at PR time, not silently closed.
4. **Residual**: the README's path mentions are literals and could drift again; the code surface that
   agents actually read is derived and guarded.
