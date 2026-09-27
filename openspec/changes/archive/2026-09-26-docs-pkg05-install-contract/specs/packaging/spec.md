# Delta for packaging

> **Change** `docs-pkg05-install-contract` (issue #259) · branch `docs/259-pkg05-install-contract`.
>
> PKG-05 required the README to document `pip install sofer` and
> `uv tool install sofer`, but the project publishes no PyPI package
> (AGENTS.md rule 12). The requirement was unsatisfiable as written and the
> README's actual git-tag install paths were untested. This delta amends PKG-05
> to the real install contract.

## MODIFIED Requirements

### Requirement: Install documentation (PKG-05)

> Modified by `docs-pkg05-install-contract` (issue #259, 2026-09-26) — there is
> no PyPI project (AGENTS.md rule 12), so the documented paths are the git-tag
> install commands, not a bare `pip install sofer` / `uv tool install sofer`.

The README SHALL document the git-tag install commands, since no PyPI project is
published: `uv tool install "sofer @ git+<repo>@vX.Y.Z" --force`,
`pip install "sofer @ git+<repo>@vX.Y.Z"`,
`pip install "sofer[mcp] @ git+<repo>@vX.Y.Z"`, and
`uvx --from git+<repo>@vX.Y.Z --with "sofer[mcp]" sofer-mcp --help`. The README
SHALL NOT document a bare `pip install sofer` or `uv tool install sofer`.

#### Scenario: README documents the git-tag install paths

- GIVEN the README (`README.md` and `README_ES.md`)
- WHEN its install section is inspected
- THEN `uv tool install "sofer @ git+..."`, `pip install "sofer @ git+..."`, the `sofer[mcp]` alias, and the `uvx` command SHALL be documented
- AND a bare `pip install sofer` / `uv tool install sofer` SHALL NOT be documented
