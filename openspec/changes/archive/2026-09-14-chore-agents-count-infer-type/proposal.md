# Proposal: chore-agents-count-infer-type

## Intent
Close issue #162 twice over: `AGENTS.md` rule 6 anchors its "never reduce coverage" floor to a test
count that no longer matches reality (unverifiable by reading it), and `tests/test_codebook.py`
calls the private deprecated alias `_infer_type`, so every suite run emits 14
`DeprecationWarning`s. Documentation plus test hygiene; one private symbol.

## Verified state
- Branch verified by reading `.git/HEAD`: `ref: refs/heads/chore/162-agents-count-infer-type` (off `dev`).
- `AGENTS.md:44`: `1149 tests currently pass (1151 collected, 2 skipped) — never reduce coverage.`
- Real suite (parent-measured on this branch): **1766 passed, 6 skipped, 1772 collected**; alias message 10× (14 warnings).
- `_infer_type` defined at `src/sofer/codebook.py:60-71` — `stacklevel=2`, delegates to `infer_column_type`.
- Callers: `tests/test_codebook.py` only — import L11, calls L28/31/34/38/41/46/49/52/53, parity test L73.

## Decision point — the alias
Repo-wide search for `_infer_type` returns only the definition and `tests/test_codebook.py`; every
other hit is historical prose under `openspec/changes/archive/**`. Nothing in docs, READMEs, the
MCP tool surface, `__init__.py` or any other test references it; canonical
`openspec/specs/repo-compliance/spec.md:1494` only records a past rename, it does not require the
alias to exist. Floors: COV-01 = `profile.py`/`mcp_registration.py`/`verification.py`; COV-06 =
`cli.py`/`scanner.py`/`prepare.py`/`publish.py` (`scripts/check_core_coverage.sh`). **`codebook.py`
has no per-file floor**, so deletion cannot drop one.
- **(A) Keep + pin** with a `pytest.warns(DeprecationWarning)` test — migration window for external
  importers, and keeps a symbol nothing in-repo uses.
- **(B) Delete (recommended)** — private, deprecated, uncalled in-repo, no floor depends on it;
  removes the warning surface at its source instead of pinning it. Cost: a private-name breaking
  change for hypothetical out-of-repo importers.
Recommendation **B**, fallback A if reviewers want the window. Either way the acceptance criterion
is identical: a normal suite run emits **zero** `DeprecationWarning`s.

## Scope
1. `AGENTS.md` rule 6 — replace the decaying literal with the source of truth (the command) plus the
   observed tally. The defect is the anchorage, not the number: any hardcoded count re-stales.
2. `tests/test_codebook.py` — `TestInferType` asserts the *same inputs → same expected outputs* via
   `infer_column_type`; import and alias call sites removed.
3. `src/sofer/codebook.py` — delete `_infer_type` (B).
4. `test_returns_same_as_private` (L64-73) exists **only** to pin the alias: replaced by the same four
   `(values, expected)` cases asserted directly against `infer_column_type` (strictly stronger,
   public API); under A it becomes the `pytest.warns` test. No case is dropped either way.

## Non-goals
- Other stale numbers: `openspec/project.md` (#184), `CONTRIBUTING.md` ruff ref (#187), README
  counts/flags (#183, #190). `openspec/config.yaml` is stale too but **gitignored** — unfixable by a PR.
- No other test file, no other source module; no change to `README.md`, `README_ES.md`,
  `pyproject.toml`, `.github/**`, or `openspec/specs/**`.
- No assertion dropped, weakened, skipped or reformatted away.
- Untouched: `openspec/changes/2026-09-14-chore-python-version-313/`, `openspec/changes/archive/**`.
- No commit, push or PR — the parent owns delivery.

## Affected areas
| Area | Impact |
| --- | --- |
| `AGENTS.md` | rule 6: count + phrasing |
| `tests/test_codebook.py` | import + 10 call sites + parity test |
| `src/sofer/codebook.py` | −12 lines (B) |
| specs | none — no capability delta |

## Risks / rollback
| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Private-name removal breaks an out-of-repo importer | Low | PR/release note; A is the fallback |
| TOTAL drops below the config-owned 90 | Very low | only fully covered lines move; verify re-runs `coverage report -m` |
| An assertion is softened during migration | Low | verify diffs the assertion table vs pre-change |

Rollback: revert the three-file diff; no data, no migrations, no feature flag.

## Verification
- `uv run pytest tests/ -q` → 1766 passed / 6 skipped, **zero** `DeprecationWarning` lines (grep the
  warnings summary, or `-W error::DeprecationWarning` on the migrated module).
- `uv run pytest tests/test_codebook.py -q` → green, same behaviour still asserted.
- `uv run mypy src/` clean (32 files); `uv run ruff check src/ tests/` → `All checks passed!`;
  `uv run ruff format --check src/ tests/` clean.
- `bash scripts/check_core_coverage.sh` exit 0; `uv run coverage report -m` TOTAL ≥ 90.
- `AGENTS.md` rule 6 matches the numbers the run actually observed.
