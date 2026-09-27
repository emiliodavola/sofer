# Exploration: PKG-05 install contract (#259)

**Change**: `docs-pkg05-install-contract`
**Issue**: GitHub #259 — PKG-05 install-doc requirement is unsatisfiable under the no-PyPI policy, and the README install paths are untested.
**Mode**: SDD (a normative requirement is amended).

## Problem

`openspec/specs/packaging/spec.md` (PKG-05) required:

> The README SHALL document `pip install sofer` and `uv tool install sofer` as install paths.

But the project publishes no PyPI package (AGENTS.md rule 12: "There is no PyPI publishing";
`gh api repos/emiliodavola/sofer/releases/latest` shows a GitHub Release only). The README
documents git-tag installs instead:

```
uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force
pip install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
uvx --from git+https://github.com/emiliodavola/sofer.git@vX.Y.Z --with "sofer[mcp]" sofer-mcp --help
```

Satisfying PKG-05 as written would require documenting a PyPI install that does not exist.
It was also untested: `tests/test_packaging.py` claims PKG-01..PKG-05, but no test asserted the
README install commands (the only `pip install` assertion, `tests/test_mcp_server.py:148`,
checks the degraded-extra message).

## Decision: amend PKG-05, add a test, do NOT author a Test Mapping table

The issue asks to "map the scenario to that test per AGENTS.md rule 6". The mapping contract
offers exactly two states per spec: it either carries a `## Test Mapping` table listing **every**
scenario, or it is recorded in `openspec/test-mapping-registry.md` as a permanent declared
backlog (registry decision, issue #234: "No sweep will author a `## Test Mapping` table for
them"). `packaging` is in that backlog, alongside `mcp-server`, `cli`, etc.

Authoring a table for `packaging` would:
- de-register it (the checker enforces the bijection), and
- force every other packaging scenario to be audited in the same change.

That audit surfaces a **pre-existing false scenario**, out of #259's scope: PKG-03 S2 requires
`sofer-mcp --help` to exit 0, but `sofer_mcp.main()` ignores argv and runs a stdio server
(`src/sofer/mcp_server.py:3456-3472`), so `sofer-mcp --help` blocks (`timeout 8 …; echo $?` →
`124`). Mapping it to `verify:` would be a dishonest escape-hatch row for a scenario that does
not hold; fixing it is a separate requirement change.

Decision: keep `packaging` in the declared backlog (the registry owner's explicit policy), amend
PKG-05, add the README test, and record the scenario→test mapping in this change's
`verify-report.md`. De-registering `packaging` and fixing PKG-03 S2 is a registry-owner decision,
surfaced to the maintainer in the PR.

## Scope boundary

- In: PKG-05 requirement (canonical + delta), the README install test in `tests/test_packaging.py`.
- Out: the README files themselves (already correct), the registry policy, PKG-03 S2, and the
  fastmcp cap drift (#257).
