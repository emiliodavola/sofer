# Proposal: publish-readme-bugs — four user-reported publish/card bugs

## Intent

After publishing a real census dataset, users found the delivered package incomplete and its README misleading: no codebooks ship with `publish`, "Data Fields" mixes columns across files without attribution (and reports absurd `num_examples`), "Data Structure" leaks the publisher's local disk paths into a public artifact, and a hardcoded 10,000 sample size diverges from the codebook while `unique` counts missing sentinels as values.

## Scope

### In Scope
- **Bug 1**: publish auto-prepare passes `all_files=True`; explicit warning when the build dir lacks codebooks; reverse pinned test `test_publish.py:695`.
- **Bug 2**: add `origin: str | None` to `ColumnSchema`; per-file attribution in the card's Data Fields table; `num_examples` = real row counts per split (`pf.metadata.num_rows` / counted CSV rows), replacing `sum(unique)`.
- **Bug 3**: Data Structure renders only repo-relative DELIVERED paths via `planned_remotes` reuse (rule 4); honors conversion/`upload_as_csv`/`recursive`/`keep_csv`; drop `e.local`.
- **Bug 4**: new `[tool.sofer] schema_sample_size` (default `10_000`) → `config.py`; footnote generated from config; unique = `len(set(non_missing))` in `repo_compliance.py:500/:563`, `codebook.py:291`, `profile.py:213`.
- **Extra finding**: `cli.py:606` hardcoded `--max-sample 100_000` default → use `CODEBOOK_MAX_SAMPLE`.

### Out of Scope
- Row-group-0 head-of-file sampling bias: documented as footnote caveat only.
- Threading an opt-out flag for auto-prepare codebook generation.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `repo-compliance`: §§3.1–3.3 — origin attribution, delivered-path Structure section, configured sample size, sentinel-free unique counts, real `num_examples`.
- `publish`: PUB-03 — auto-prepare produces codebooks (complete package).
- `codebook`: unique counts exclude sentinels; `--max-sample` default from config.
- `profile`: unique counts exclude sentinels.

## Approach

Bugs 2+4 both touch `build_schema_report`/`build_dataset_card` — implement together to avoid double test churn. Bugs 1 and 3 are independent. Bug 3 imports/reuses `_mirror.planned_remotes` rather than copying it. All defaults flow through `[tool.sofer]` + `config.py` (rule 1).

## Affected Areas

| Area | Impact |
|------|--------|
| `src/sofer/publish.py` | Modified — auto-prepare `all_files=True`, codebook warning |
| `src/sofer/repo_compliance.py` | Modified — ColumnSchema.origin, card rendering, num_examples, sample config |
| `src/sofer/_mirror.py` | Consumed (no logic duplication) |
| `src/sofer/config.py`, `pyproject.toml` | Modified — `schema_sample_size` key |
| `src/sofer/codebook.py`, `profile.py` | Modified — unique sentinel fix |
| `src/sofer/cli.py` | Modified — `--max-sample` default from config |
| `tests/` | Reverse `test_publish.py:695`; update `test_repo_compliance.py:1733/:1748`; new tests for attribution, paths, sample size, unique |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Bug 2 changes YAML `dataset_info.splits.num_examples` semantics | Med | Delta spec + updated/new tests; consumers of the key reviewed |
| Bug 1 reverses a pinned test; slower auto-prepare | Low-Med | Explicit test reversal in review; codebooks capped by CODEBOOK_MAX_SAMPLE |
| Unique-count semantic change alters existing outputs | Low | Docstring already promised exclusion — fix aligns code to contract |

## Rollback Plan

Single branch on `fix/publish-readme-bugs`; each bug is an independent work unit — revert commits per bug. No data migration or persisted-format breakage beyond the YAML value correction (regenerating the card restores prior shape minus bugs).

## Dependencies

None new.

## Success Criteria

- [ ] Bare `sofer publish cfg.toml` delivers Parquet + README + LICENSE + codebooks
- [ ] Data Fields attributes every column to its source file; no silent drops
- [ ] `num_examples` equals actual row count per split
- [ ] Data Structure shows only delivered repo-relative paths
- [ ] Sample size configurable via `[tool.sofer]`; README/codebook consistent
- [ ] `unique` excludes sentinels in all 4 sites; `cli.py:606` reads config
- [ ] `uv run pytest tests/ -q`, `ruff check`, `mypy src/` all pass

## Delivery

Estimated ~350–450 lines incl. tests → single PR is viable, but Bugs 2+4 vs 1+3 split cleanly. Recommendation: single PR ordered Bug 4 → 2 → 3 → 1 (shared functions first), keeping each bug a separate commit for revertability.
