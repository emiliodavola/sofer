# Proposal: Make PKG-05 the real git-tag install contract (#259)

## Intent

PKG-05 required the README to document `pip install sofer` / `uv tool install sofer`, but sofer
publishes no PyPI package (AGENTS.md rule 12). The requirement was unsatisfiable as written, and
the README's actual git-tag install paths had no test. This change amends PKG-05 to the real
install contract and adds a test that parses both READMEs and asserts the documented commands.

## Scope

### In Scope

- `openspec/specs/packaging/spec.md`: PKG-05 MODIFIED to the git-tag install contract; scenario
  renamed to "README documents the git-tag install paths".
- `tests/test_packaging.py`: `test_readme_documents_the_git_tag_install_paths`, deriving the repo
  URL from `[project.urls] Homepage` and asserting the four commands in `README.md` and
  `README_ES.md`, and that no bare `pip install sofer` / `uv tool install sofer` remains.

### Out of Scope

- The README files — already correct.
- Authoring a `## Test Mapping` table for `packaging` — that is a registry-owner policy decision
  (the spec is a permanent declared backlog), and it would force auditing PKG-03 S2, which is
  currently false (`sofer-mcp --help` blocks; see `exploration.md`). Recorded, not changed.
- A PyPI publication (#254-family follow-up).
- The fastmcp cap drift (#257) and the SDD-context reconciliation (#258).

## Capabilities

### Modified Capabilities

- `packaging`: PKG-05 install documentation.

No scenario is added; the one PKG-05 scenario is renamed and its assertion changed.

## Approach

1. Rewrite PKG-05 in the canonical spec and the delta to describe the git-tag commands and to
   forbid the bare PyPI commands.
2. Add the README test, deriving the repository URL from `pyproject.toml` rather than hardcoding
   the owner, so a repository move needs no test edit.
3. Verify with the focused test, negative controls, the full suite, the gates, and the checker.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/packaging/spec.md` | Modified | PKG-05 requirement + scenario |
| `tests/test_packaging.py` | Modified | README git-tag install test + module docstring |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| The test hardcodes the repo owner | Low | The URL is derived from `[project.urls] Homepage` |
| The test passes vacuously if a README loses its install block | Low | Negative controls: removing a command or adding bare `pip install sofer` fails |
| Leaving `packaging` unmapped is read as ignoring the issue's rule-6 mapping ask | Medium | The rationale (registry policy + false PKG-03 S2) is stated in `exploration.md`, `verify-report.md`, and the PR body |

## Rollback Plan

Revert the two-file diff + archived change folder. No source, dependency, README, workflow, or
release state is touched.

## Dependencies

None.

## Success Criteria

- [ ] PKG-05 describes the git-tag install contract and forbids the bare PyPI commands.
- [ ] The README test parses both READMEs and fails on drift.
- [ ] Full suite green; ruff/mypy/pyright clean; checker exit 0.
