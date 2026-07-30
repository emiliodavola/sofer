# Proposal: HF Dataset Compliance (P0)

## Intent

The `data-uploader` CLI uploads raw files to Hugging Face Hub but produces repos that don't follow official HF dataset standards — no Dataset Card, no LICENSE, no schema declaration. This makes repos invisible to the Dataset Viewer, breaks `datasets.load_dataset()`, and undermines the Leek group data-sharing principles the tool claims to follow.

## Scope

### In Scope (P0 — this change)
- Extend TOML `[meta]` section with Dataset Card + Leek-aligned fields
- Generate HF-standard Dataset Card (`README.md` with YAML frontmatter)
- Generate `LICENSE` file from declared SPDX identifier
- Document schema (columns, types, units, descriptions, missing-value coding) in the Dataset Card
- Refactor upload pipeline: new internal `repo_compliance.py` module, `upload` orchestrates

### Out of Scope (deferred)
- Parquet conversion (P1)
- Split detection / `[[split]]` TOML section (P1)
- Data quality checks (P2)
- `load_dataset()` automated verification (P2)

## Capabilities

### New Capabilities
- `repo-compliance`: Dataset Card generation, LICENSE creation, schema documentation — called by upload before pushing files

### Modified Capabilities
- None (first SDD change; no existing specs to modify)

## Approach

1. Extend `DatasetConfig.dataclass` in `model.py` with new `[meta]` fields (language, pretty_name, task_categories, size_categories, citation, source_organization, collection_method)
2. Create `src/data_uploader/repo_compliance.py` with three pure functions:
   - `build_dataset_card(cfg, schema) -> str` — generates `README.md` with YAML frontmatter + Leek-aligned body
   - `build_license_file(license_id) -> str` — returns well-known license text or descriptive fallback for unknown identifiers
   - `build_schema_report(cfg) -> list[ColumnSchema]` — reads CSV headers/sample to infer types
3. Refactor `uploader.upload()` to call `repo_compliance` before `huggingface-cli` push
4. Dataset Card body follows Leek guide sections: raw data provenance, tidy data description, codebook reference, processing recipe

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/data_uploader/model.py` | Modified | New `[meta]` fields on `DatasetConfig` |
| `src/data_uploader/repo_compliance.py` | New | Dataset Card, LICENSE, schema generation |
| `src/data_uploader/uploader.py` | Modified | Orchestrates compliance before upload |
| `src/data_uploader/cli.py` | None | No CLI changes this slice |
| `tests/` | Modified | New test file `test_repo_compliance.py` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| YAML frontmatter parsing mismatches | Low | Generate via `PyYAML yaml.safe_dump()` — write structured dict, not string templates |
| License text copyright (reproducing SPDX texts) | Low | Embed OSI-approved short templates; fail-safe by linking to `choosealicense.com` |
| Non-SPDX license crash | Medium | Non-SPDX values produce a descriptive LICENSE file ("This dataset is shared under the following terms: ...") instead of raising `ValueError`; upload continues normally |
| Breaking existing upload workflows | Low | Backward-compatible TOML (new fields optional, default to sensible values) |

## Rollback Plan

- Revert `uploader.py` — compliance is orchestrated, not inlined; reverting restores old behavior
- Old TOML files remain valid (all new fields optional)
- Repos uploaded without compliance are unchanged; user re-runs `upload` to regenerate artifacts

## Dependencies

- `PyYAML` (replaces `tomli-w` in `pyproject.toml`) for YAML frontmatter generation
- No net-new runtime dependencies for P0

## Success Criteria

- [ ] `data-uploader upload <config.toml>` generates a HF repo with `README.md` (valid YAML frontmatter) + `LICENSE`
- [ ] Dataset Card renders correctly on HF Hub Dataset Viewer
- [ ] `from datasets import load_dataset; load_dataset("user/repo")` works without custom code
- [ ] All existing 54 unit tests pass unchanged
- [ ] New fields are optional — all existing TOML configs remain valid
