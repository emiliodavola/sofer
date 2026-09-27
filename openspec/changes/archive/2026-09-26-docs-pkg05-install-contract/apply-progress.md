# Apply Progress: PKG-05 install contract (#259)

**Change**: `docs-pkg05-install-contract`
**Mode**: SDD (MODIFIED requirement; no new scenario)

## Completed Tasks

- [x] 1.1–1.2 PKG-05 amended in the canonical spec and the delta.
- [x] 2.1–2.3 README git-tag install test + helpers + module docstring.
- [x] 3.1–3.5 Verification + independent verification; scenario mapping recorded.
- [x] 4.1 Archive.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `openspec/specs/packaging/spec.md` | Modified | PKG-05 → git-tag install contract; scenario renamed; provenance note |
| `tests/test_packaging.py` | Modified | `test_readme_documents_the_git_tag_install_paths` + `_project_homepage`/`_documented_git_tag_commands`/`_RETIRED_INSTALL_RE`; docstring |
| `openspec/changes/archive/2026-09-26-docs-pkg05-install-contract/` | New | This change's artifacts |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_packaging.py -q -k readme` — `1 passed`; module `8 passed` |
| Runtime harness command/scenario and result | N/A — documentation/spec + static README parse. Full `uv run pytest tests/ -q` — `1989 passed, 1 skipped` |
| Negative controls | removing a required command from either README fails; adding bare `pip install sofer` / `pip install 'sofer'` / `uv tool install sofer` fails; tree restored byte-for-byte |
| Lint/format gates | `ruff check src/ tests/ scripts/` passed; `ruff format --check src/ tests/` 73 files formatted |
| Test-mapping checker | `OK: test-mapping contract holds` (`packaging` stays a registered backlog spec) |
| Rollback boundary | Revert the two-file diff + change folder; no source/dependency/README/workflow/release change |

## Deviations from Design

The negative check was hardened from an exact substring test to `_RETIRED_INSTALL_RE` after
independent verification, so quoted / `pip3` / `python -m pip` bare forms are also flagged.
The decision **not** to author a `## Test Mapping` table for `packaging` is documented in
`exploration.md`: the registry declares it a permanent backlog, and a full audit surfaces the
false PKG-03 S2 (`sofer-mcp --help` blocks), which is out of this change's scope.

## Remaining Tasks

None.
