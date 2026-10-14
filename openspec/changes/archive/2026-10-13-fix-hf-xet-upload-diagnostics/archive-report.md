# Archive Report: Name the HF upload failure, retry once, report the empty repository

**Change**: `2026-10-13-fix-hf-xet-upload-diagnostics`
**Archived to**: `openspec/changes/archive/2026-10-13-fix-hf-xet-upload-diagnostics/`
**Branch**: `fix/289-hf-xet-upload-diagnostics` (base `dev@4ca823e`)

> `origin/dev` advanced to `71da0e7` (#297, #293) while this change was implemented.
> Every tally below was measured on base **`4ca823e`**; the parent rebases the branch
> onto the new `dev` and re-runs the whole gate battery on the rebased state. All git
> mutations (stage/commit/PR) are owned by the parent; this worktree carries the change
> uncommitted, so this report names no commit identity.

## Specs Synced

| Domain | Action | Details |
| --- | --- | --- |
| `publish` | Updated | PUB-01 "hf target uploads via upload_folder" amended: 1 clause added (named upload failure, config-owned backend probe, bounded retry, no fallback, created-but-empty report), 1 amendment note recording why no `--no-xet` flag / in-process fallback exists, and 3 scenarios added (`Upload failure names the cause and the backend`, `Upload retried once`, `Created-but-empty repository reported`). No Test Mapping row and no registry edit: `publish` is a permanent declared-backlog spec. |

The canonical `openspec/specs/publish/spec.md` was amended **in place** from the delta's
`## MODIFIED Requirements` block; the delta describes the two spans that moved (the
requirement body and the scenario list) rather than re-copying the whole requirement.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present; T1–T7 and T9 complete, T8 (commits) handed to the parent, which owns all git mutations
- `specs/publish/spec.md` (delta) — present
- `archive-report.md` — this file

The change produced no `explore.md`, `apply-progress.md`, `verify-report.md` or
`sync-report.md` siblings; the five files above are the complete set.

## Source of Truth Updated

- `openspec/specs/publish/spec.md` — PUB-01 is canonical with its new clause, note and
  three scenarios.
- `openspec/test-mapping-registry.md` — **untouched**; the registry bijection still holds
  (`scripts/check_test_mapping.py` exits 0).
- `README.md` + `README_ES.md` — matching `### Troubleshooting HF uploads` /
  `### Solución de problemas de subida a HF` sections and ToC entries (rule 13).
- `src/sofer/config.py` + `pyproject.toml [tool.sofer]` — the four defaults
  (`hf_upload_retry_count`, `hf_backend_disable_env`, `hf_backend_prefix_env`,
  `hf_upload_error_max_chars`) are declared together, so the `_DEFAULTS ↔ pyproject.toml`
  parity guards (`tests/test_config.py`) pass.

## SDD Cycle Complete

**Implementation**: complete — `src/sofer/publish.py`, `src/sofer/config.py`,
`pyproject.toml`, `tests/test_publish.py`, both READMEs, canonical `publish` spec.

**Verification** (all measured on base `4ca823e`):

| Gate | Observed |
| --- | --- |
| `uv run pytest tests/ -q` | `2100 passed, 9 skipped` |
| RED (pre-change, new selection) | `10 failed, 1 passed` — the named-cause and retry cases |
| `uv run coverage run -m pytest` + `uv run coverage report -m` | TOTAL **94%** (gate ≥ 90) |
| `bash scripts/check_core_coverage.sh` | exit 0 — `cli`/`scanner`/`prepare`/`publish` each **100%** |
| `uv run ruff check src/ tests/ scripts/` | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | `75 files already formatted` |
| `uv run mypy src/ scripts/` | `Success: no issues found in 37 source files` |
| `uv run pyright` | `0 errors, 1 warning` (pre-existing `_toml.py` tomli) |
| `uv run python scripts/check_test_mapping.py` | `OK: test-mapping contract holds` |

`publish.py` — an AGENTS.md rule-14 module — stayed at **100.00%** line and branch
coverage (`351 stmts / 0 missed`, `150 branch / 0 partial`) with no `# pragma: no cover`
anywhere; both new failure branches are executed by `TestHfUploadDiagnostics` and
`TestPublishEmptyRepositoryReport`. The four new config defaults are read at the call site
(no literal in `publish.py`), and the red-first tests proved non-vacuous by the measured
RED above.

**Delivery**: the change is complete in the working tree; stage/commit/push/PR are the
parent's responsibility, and the final commit body must carry `Closes #289`. The parent
rebases onto `origin/dev@71da0e7` and re-runs the full gate battery before delivery.

**Unfinished tasks and unresolved findings**: none from this change. The systematic xet
failure (0/9) is mitigated by the named cause and the documented `HF_HUB_DISABLE_XET=1`
re-run, not fixed in-process — a supported per-call backend selector remains a follow-up
only if `huggingface_hub` adds one (decision D1).
