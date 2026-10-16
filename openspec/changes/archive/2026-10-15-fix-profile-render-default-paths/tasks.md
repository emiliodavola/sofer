# Tasks: fix-profile-render-default-paths

**Change** `2026-10-15-fix-profile-render-default-paths` (GitHub **#294**) · branch
`fix/294-profile-render-default-paths` from `dev@b7dea51` · store **hybrid**.

**One-line outcome:** both batch tools' `output_dir` descriptions name the path the pipeline really
writes — the configured cache root plus the configured sub-directory — and the override semantics, all
derived from `config` instead of typed as literals.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real red-then-green:

- **RED (measured):**
  `uv run pytest tests/test_mcp_schema.py -q -k BatchOutputDirDescription` → **2 failed, 22 deselected**,
  each failure printing the shipped text (`default: renders`) and the missing `cache/renders`.
- **GREEN (measured):** `uv run pytest tests/test_mcp_schema.py tests/test_mcp_server.py -q` →
  **280 passed, 3 skipped**.
- **REFACTOR:** none needed; the description composer is a single helper used by both tools, and the
  test's schema walk reuses the existing version-independent pattern.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: both batch tools' `output_dir` description names the resolved default and the `<output_dir>/<sub-directory>` override form | done | `2 failed, 22 deselected` |
| T2 | Derive the descriptions from `config`; fix the two docstring side-effect lines | done | `_batch_output_dir_description` + both `Field`s |
| T3 | README + README_ES MCP-table rows in the same commit (rule 13) | done | `README.md:641/:643`, `README_ES.md:679/:681` |
| T4 | MSP-R03 spec delta + canonical spec | done | `openspec/specs/mcp-server/spec.md` |
| T5 | Gates: focused tests, full suite, ruff/format/mypy/pyright, mapping checker | done | see `archive-report.md` |
| T6 | Archive the change in the branch and commit | done | see `archive-report.md` |
