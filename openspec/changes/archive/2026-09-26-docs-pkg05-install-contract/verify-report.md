# Verify Report: PKG-05 install contract (#259)

**Change**: `docs-pkg05-install-contract`
**Mode**: SDD
**Branch**: `docs/259-pkg05-install-contract` (base `dev` @ `5f6c2de`)

## Verification evidence

| Check | Command | Result |
| --- | --- | --- |
| Focused test | `uv run pytest tests/test_packaging.py -q -k readme` | `1 passed` |
| Packaging module | `uv run pytest tests/test_packaging.py -q` | `8 passed` |
| Full suite | `uv run pytest tests/ -q` | `1989 passed, 1 skipped` |
| Lint | `uv run ruff check src/ tests/ scripts/` | passed |
| Format | `uv run ruff format --check src/ tests/` | 73 files already formatted |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK: test-mapping contract holds` |

## Scenario → evidence mapping (PKG-05)

| Scenario | Evidence |
| --- | --- |
| README documents the git-tag install paths | `test:tests/test_packaging.py::test_readme_documents_the_git_tag_install_paths` (parses `README.md` and `README_ES.md`; derives the repo URL from `[project.urls] Homepage`) |

`packaging` remains in `openspec/test-mapping-registry.md` as a permanent declared backlog, so
no `## Test Mapping` table is authored (see `exploration.md` for the rationale and the PKG-03 S2
finding). This table records the mapping without changing the registry policy.

## Negative controls

The test fails when a required command is removed from either README, and when a bare
`pip install sofer` / `pip install 'sofer'` / `uv tool install sofer` is added. The regex
excludes the legitimate `sofer @ git+...` and `sofer[mcp] @ ...` forms. All probes restored the
tree byte-for-byte.

## Independent verification (subagent)

A read-only adversarial subagent verified the change. **Verdict: PASS** on all eight items
(no-PyPI premise, PKG-05 canonical, delta↔canonical equality, test quality, test effectiveness,
registry policy, the PKG-03 S2 claim, and scope discipline).

### Findings and resolution

- **verify-report.md missing** (referenced by the proposal/design) — created here. Fixed.
- **Literal substring negative check** — hardened to `_RETIRED_INSTALL_RE`, which flags quoted,
  `pip3`, and `python -m pip` bare forms while excluding the two git-tag forms. Fixed.
- **Whole-README scan vs the scenario's "install section"** — behaviourally stricter (a superset
  of the install section); kept intentionally.

### Pre-existing issue surfaced (out of scope, reported to the maintainer)

PKG-03 S2 ("Both CLIs run") requires `sofer-mcp --help` to exit 0, but
`src/sofer/mcp_server.py::main` ignores argv and runs a stdio server, so
`timeout 8 uv run sofer-mcp --help </dev/null` exits `124` (blocked), while `sofer --help`
exits `0`. This is why `packaging` was **not** given a Test Mapping table in this change: mapping
a false scenario would be a dishonest escape-hatch row. Fixing PKG-03 S2 is a separate change.

Unresolved findings in this change: none.
