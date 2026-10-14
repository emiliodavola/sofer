# Archive Report: One config per schema group

**Change**: `2026-10-13-fix-mixed-schema-configs`
**Archived to**: `openspec/changes/archive/2026-10-13-fix-mixed-schema-configs/`
**Branch**: `fix/292-mixed-schema-configs` (base `dev@4ca823e`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `repo-compliance` | Updated | RC-Universal-Card (§4.20) amended in place with the mixed-schema grouping clause and 2 scenarios; a new requirement **RC-R23 "Mixed-schema config grouping"** added with 6 scenarios. No Test Mapping row and no registry edit: `repo-compliance` is a permanent declared-backlog spec, and `scripts/check_test_mapping.py` exits 0 with `repo-compliance: 74 scenario(s), unmapped` (was 66; +8 new). |

The canonical `openspec/specs/repo-compliance/spec.md` was amended **in place**
from the delta. The previous card merged every remote into one `train` config
unconditionally; RC-R23 declares the grouping, the slug rule, the single-config
`default`, the per-group `dataset_info`, and the ungroupable guard — all of
which were previously enforced (or rather, not enforced) nowhere.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present (all tasks complete except T10, which the parent withheld)
- `specs/repo-compliance/spec.md` (delta) — present

## Source of Truth Updated

- `openspec/specs/repo-compliance/spec.md` — RC-Universal-Card §4.20 modified and
  RC-R23 added.
- `openspec/test-mapping-registry.md` — **untouched**; the registry bijection
  still holds (`check_test_mapping.py` exits 0).
- `README.md` / `README_ES.md` — **unchanged**: neither README documents the
  card's `configs`/`dataset_info` structure, so no documented section changed
  (AGENTS.md rule 13 does not trigger).

## SDD Cycle Complete

Implementation: complete (`src/sofer/repo_compliance.py`, `src/sofer/splits.py`,
`src/sofer/config.py`, `pyproject.toml` `[tool.sofer]`,
`tests/test_repo_compliance.py`, `tests/test_splits.py`, the canonical
`repo-compliance` spec).

Verification (all run on base `4ca823e`; the parent re-runs on the rebased state):

- `uv run pytest tests/ -q` → **2096 passed, 8 skipped** (the skips are
  environment-dependent: symlink/junction creation, `pwd` off POSIX, hatchling
  build backend)
- `uv run coverage run -m pytest` → 2095 passed, 9 skipped; `coverage report -m`
  → **TOTAL 94%**, `repo_compliance.py` 92%, `splits.py` 94%
- `uv run ruff check src/ tests/ scripts/` → All checks passed
- `uv run ruff format --check src/ tests/` → 75 files already formatted
- `uv run mypy src/ scripts/` → Success: no issues found in 37 source files
- `uv run pyright` → 0 errors, 1 warning (pre-existing `_toml.py` `tomli` source)
- `uv run python scripts/check_test_mapping.py` → OK: test-mapping contract holds

No `# pragma: no cover` added anywhere. `quality.py`, `publish.py` and
`prepare.py` are absent from the diff.

Delivery: **not committed by this worker** — the parent owns the commit, the
rebase onto the updated `dev` (now `71da0e7`) and the PR. The working tree is
left intact.

Unfinished tasks and unresolved findings:

- **Dry-run warning (corrected before delivery)** — the `config_names` keyword
  and the `card_config_group_warn_limit` default it alone read were removed by
  the parent: no production caller can supply the card's config names without
  parsing the built card, and an unused keyword is surface that does not earn
  its place. The warning now states both card shapes, which is true without the
  names; naming the groups from the built card is a named follow-up.
- **Global column dedup** — a later file whose columns all repeat an earlier
  file has no schema entries; grouping absorbs it into the sole signature group
  (correct for train/test) or gives it its own group when several signatures
  exist (loadable, not ideal). Recorded as R1 in `design.md`.
