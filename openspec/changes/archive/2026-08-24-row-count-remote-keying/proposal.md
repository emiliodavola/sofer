# Proposal: Key exact row counts by remote path (row-count-remote-keying)

## Intent

Fix GitHub #57: `_build_schema_report_with_rows()` (`src/sofer/repo_compliance.py`) keys exact row counts by origin basename. Two declared files sharing a stem (`data/a/data.csv` + `data/b/data.csv`) collide on one dict key; the second write silently overwrites the first and `num_examples` in the Dataset Card frontmatter is wrong (30+40 → 40). This lifts limitation D7 of `2026-08-17-publish-readme-bugs/design.md`.

## Scope

### In Scope
- Re-key row counts by verbatim `entry.remote` at both producer sites (`repo_compliance.py:453` parquet, `:514` CSV). Unique per dataset by construction; also fixes today's mixed local-stem/remote-stem keying.
- Keep `ColumnSchema.origin` basename-based — display-only; no code joins it against keys.
- Update docstrings of `_build_schema_report_impl`, `build_schema_report_with_rows`, `build_dataset_card`.
- Warn when hand-edited TOML declares duplicate remotes (guards the new keying invariant; scanner dedups but doesn't validate).
- Tests: update 4 exact-dict assertions; add same-stem regression fixture (`a/data.csv` + `b/data.csv` → distinct keys, `num_examples == N+M`).
- Delta spec for `repo-compliance` § 4.8 (RC-R07): keying semantics basename → remote path.

### Out of Scope
- **Staged-parquet flat-by-remote-stem lookup bug** (`repo_compliance.py:435`; subdirectory remotes miss staging, same-stem remotes share a candidate path) — explicitly a separate follow-up issue; must not ride along.
- Exact counts for non-schema files (recursive trees, non-CSV remotes, `include_in_schema=false`): keep D7 fallback (`CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)`) — counting them costs full-file I/O or directory walks. Decision documented here.
- Partial-counts silent undercount for mixed schema/non-schema datasets — behavior unchanged, noted in design.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `repo-compliance`: RC-R07 — exact row counts keyed by remote path instead of origin basename; duplicate-remote warning requirement added.

## Approach

Exploration Approach A (recommended): two-line producer change to `row_counts[entry.remote] = ...`. The sole production consumer sums values only (`build_dataset_card`, ~line 793); zero consumers read keys. Alternatives rejected: tuple keys `(local, remote)` (no consumer needs provenance in keys — `ColumnSchema.origin` already carries display provenance) and structured records return type (consumer rewrite, overkill).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/repo_compliance.py` | Modified | Producer keying (:453, :514), duplicate-remote warning, docstrings |
| `src/sofer/prepare.py` | Verified | Values-only consumer; no code change |
| `tests/test_repo_compliance.py` | Modified | 4 assertions + 1 regression fixture |
| `openspec/specs/repo-compliance/spec.md` | Modified | RC-R07 delta |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dict-key semantics change of public-ish API | Low | Single consumer is values-only; tests updated in same commit |
| Duplicate remotes still overwrite | Low | New warning on duplicate remote |
| Staged-parquet bug confuses verification if left unfixed | Medium | Tracked as explicit follow-up issue |

## Rollback Plan

Single PR on `fix/row-count-remote-keying`; revert restores basename keying and prior assertions. No data migration, config, or persisted-state impact.

## Line Forecast

~120–160 changed lines total (≈20 src incl. warning, ≈60–90 tests, spec delta). Well under the 2000-line review budget → single PR, no chaining needed.

## Dependencies

- None external.

## Success Criteria

- [ ] Same-stem remotes produce distinct row-count keys; `num_examples == N+M`
- [ ] All existing tests pass (422 baseline) with updated assertions
- [ ] Duplicate declared remote emits a warning
- [ ] RC-R07 delta spec written; staged-parquet bug filed as separate issue
