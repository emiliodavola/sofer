# Archive Report: One schema entry per origin so same-schema tables share a config

**Change**: `2026-10-15-fix-schema-relation-map`
**Archived to**: `openspec/changes/archive/2026-10-15-fix-schema-relation-map/`
**Branch**: `fix/304-schema-relation-map` (base `dev@fad1b00`)
**Issue**: `emiliodavola/sofer#304`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `repo-compliance` | Updated | RC-R05 rewritten: one entry per `(origin, name)`, the first-occurrence-wins clause replaced, and its "Duplicate name keeps first occurrence with its origin" scenario replaced by "Duplicate name yields one entry per origin". § 3.3.6's already-superseded `"a.parquet::value"` prefix block re-stated in the `origin` format (two entries). RC-R06's collapse rationale rewritten (one row per schema entry; per-origin `<details>` blocks) plus a new scenario for a repeated name. RC-R21 gains the per-origin display clause and RC-R21.09. RC-R23 gains the **Remote classes (D1)** clause, the resolved-origin **Grouping (D2)** clause, the `features` name-dedup sentence, and four scenarios (same-schema pair shares one config; unknown never invents a group; unknown joins the sole group; declared non-schema keeps its own config). No requirement added or removed. |

The canonical `openspec/specs/repo-compliance/spec.md` was amended in place from the delta's
`## MODIFIED Requirements` block, matching #292's precedent for this capability. `repo-compliance`
remains a permanent declared-backlog spec: `scripts/check_test_mapping.py` exits 0 and reports
`repo-compliance: 80 scenario(s), unmapped` (was 71 before this change), no `## Test Mapping` table is
added, and `openspec/test-mapping-registry.md` is untouched.

## Archive Contents

- `proposal.md` — present (intent, scope, D1–D6, affected specs, 5 risks, rollback, SC-1..SC-7)
- `design.md` — present (the defect precisely, the measured before/after evidence, the per-site edit
  table, the TDD posture)
- `tasks.md` — present, T1–T9 complete; T10 (push/PR) is parent-owned and pending
- `specs/repo-compliance/spec.md` (delta) — present

No `explore.md`, `apply-progress.md`, `verify-report.md` or `sync-report.md` siblings were produced;
the four files above are the complete set. Verification evidence is in `tasks.md` and below.

## Source of Truth Updated

- `openspec/specs/repo-compliance/spec.md` — the five modified sections are canonical.
- `openspec/test-mapping-registry.md` — **untouched**; the checker still exits 0.
- `src/sofer/repo_compliance.py` — one `ColumnSchema` entry per `(origin, name)`;
  `_is_convertible_entry`, `_is_schema_eligible`, `_note_column_origin` and
  `_schema_eligible_remotes` added; `group_remotes_by_schema(schema_eligible=...)` classifies a
  schema-less remote before grouping it; `_features_for_group(..., aliases)` resolves the group's
  origins through the same map grouping and row counts use and lists each distinct name once;
  the Data Quality Notes empty-column list is deduped; the duplicate warning text now says
  `each file keeps its own schema entries.`
- `tests/test_repo_compliance.py` — new `TestSchemaRelationMap` (8 tests) plus 5 assertions that
  pinned the old global dedup, updated in the same commit.
- `odd/tasks/schema-relation-map.md` — the ODD record (specs quoted verbatim, D1–D6, tasks, log).
- **No README / README_ES / docs change**: no CLI surface, option, config key or documented command
  behaviour changed. Verified: neither README mentions the schema dedup, `configs` grouping or the
  Data Fields collapse rule (AGENTS.md rules 7 and 13 do not trigger).

## Verification

| Gate | Command | Result |
|------|---------|--------|
| Full suite | `uv run pytest tests/ -q` | **2144 passed, 9 skipped** in 84.12s |
| Focused module | `uv run pytest tests/test_repo_compliance.py -q` | **206 passed** |
| Lint | `uv run ruff check src/ tests/ scripts/` | All checks passed |
| Format | `uv run ruff format --check src/ tests/` | 74 files already formatted |
| Types | `uv run mypy src/ scripts/` | Success |
| Types (2nd) | `uv run pyright` | 0 errors |
| Spec↔test mapping | `uv run python scripts/check_test_mapping.py` | OK — `repo-compliance: 80 scenario(s), unmapped` |
| Coverage TOTAL | `uv run coverage run -m pytest` + `uv run coverage report -m` | TOTAL **94%** (floor 90, CI-01); `repo_compliance.py` **92%**, `prepare.py` **100.00%**, `publish.py` **100.00%** |
| Second-tier floors (COV-01) | same report | `profile.py` 96%, `mcp_registration.py` 99%, `verification.py` 100% |
| CLI-core 100% gates (COV-06) | `bash scripts/check_core_coverage.sh` | `cli.py` / `scanner.py` / `prepare.py` / `publish.py` all **100.00%** |
| Local coverage pin, fresh data | `uv run pytest tests/test_coverage_contract.py -q` | **3 passed** |
| RED (before any source edit) | `uv run pytest tests/test_repo_compliance.py -q -k "TestSchemaRelationMap or duplicate_name"` | **7 failed, 3 passed, 196 deselected** |

The first full-suite run was executed after `rm -f .coverage`: the working tree carried a local
coverage database from 2026-10-09, which makes `tests/test_coverage_contract.py` assert stale
percentages and fail for an unrelated reason. That false positive is issue **#305**, untouched by this
branch and fixed in its own change (`fix/305-coverage-guard-freshness`). The coverage rows above were
measured afterwards on a database this branch produced, which is why the local pin passes there.

## Notes for the reviewer

1. **Two deliberate behaviour changes**, both in `proposal.md` § 5 and pinned by tests: the Data
   Fields section now renders one row per schema entry (R1), and a schema-eligible remote that could
   not be read makes a multi-signature corpus ungroupable instead of inventing a config group (R3).
2. **#292's recorded R1 is closed** by this change: the limitation named in
   `openspec/changes/archive/2026-10-13-fix-mixed-schema-configs/design.md` § 4 R1 ("a later file
   whose columns all repeat an earlier file has no schema entries") no longer holds. The issue's own
   proposal item 1 is implemented; item 2 is implemented with the three-class refinement (D1) that
   keeps `include_in_schema = false` files and recursive trees in their own configs, as RC-R03 and
   RC-R12 require.
3. **Two claims in issue #304's report are corrected here**: the schema report is consumed only by
   `repo_compliance` and `prepare` (`codebook.py` streams its own readers and `quality.py` never sees
   it), and the fix did not need the `build_schema_report` return-shape change the issue assumed
   (D3 — with per-origin entries the flat list *is* the per-origin map).
4. **#303 becomes cheap after this change**: `schema_config_plan` is the single plan, so a card
   builder that returns it can name the emitted config groups in the dry-run warning without parsing
   the card.
