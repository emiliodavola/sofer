# Design: PKG-05 install contract (#259)

**Change**: `docs-pkg05-install-contract`

## Requirement shape

PKG-05 becomes a MODIFIED requirement: the normative sentence now names the four git-tag
commands (with a `<repo>` placeholder) and adds a negative clause forbidding the bare
`pip install sofer` / `uv tool install sofer`. The single scenario is renamed
"README documents the git-tag install paths" and gains the negative assertion. Provenance note
records the issue and the no-PyPI rationale.

## Test

`tests/test_packaging.py`:

- `_project_homepage()` parses `pyproject.toml` (tomllib/tomli) and returns `[project.urls]
  Homepage`, so the repository URL is derived, not hardcoded.
- `_documented_git_tag_commands()` builds the four commands from that URL and the documented
  `vX.Y.Z` tag placeholder.
- `test_readme_documents_the_git_tag_install_paths()` asserts each command appears in both
  `README.md` and `README_ES.md`, and that neither contains a bare `pip install sofer` or
  `uv tool install sofer`.

The `vX.Y.Z` placeholder is the documented tag placeholder (not a version literal), and the
URL is derived, matching the repo's literal-free guard discipline.

## Why no Test Mapping table

See `exploration.md`. `packaging` is a permanent declared backlog spec
(`openspec/test-mapping-registry.md`); authoring a table would de-register it and force a full
scenario audit, which surfaces the false PKG-03 S2 (`sofer-mcp --help` blocks). The mapping for
PKG-05 S1 is recorded in `verify-report.md`; de-registration is a registry-owner decision.

## Test strategy

| Case | Expected |
| --- | --- |
| Clean tree | both READMEs pass |
| A required command removed | FAILS (negative control) |
| A bare `pip install sofer` added | FAILS (negative control) |
| Repo URL derived from pyproject | no owner literal in the test |
