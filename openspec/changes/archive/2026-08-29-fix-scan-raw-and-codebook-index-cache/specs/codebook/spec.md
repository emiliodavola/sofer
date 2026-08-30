# Delta for codebook

## MODIFIED Requirements

### Requirement: Root Index (CB-R04)

When `--all-files` is used, the system MUST generate the root `codebook.md` at `write_root / "codebook.md"`: `cache/codebook.md` when `output_dir is None` (standalone `codebook --all-files`), `output_dir/codebook.md` when `output_dir` is set (prepare). The index SHALL contain a TOC with relative links under `codebooks/` prefix (matching uploader's HF staging), not `data/codebooks/`, colocated with per-file `codebooks/<rel-stem>.md`. System MUST NOT write `base_dir/codebook.md` in standalone mode.

(Previously: root codebook.md in TOML config directory (base_dir/codebook.md) regardless of write_root.)

#### Scenario: Standalone batch writes to cache

- GIVEN `dataset.toml` in `/proj/` with `raw/a.csv` and `raw/b.parquet`
- WHEN `sofer codebook --config dataset.toml --all-files` completes
- THEN `/proj/cache/codebook.md` SHALL exist, `/proj/cache/codebooks/a.md` and `b.md` SHALL exist
- AND `/proj/codebook.md` SHALL NOT exist, links SHALL be `codebooks/a.md` and `codebooks/b.md`

#### Scenario: Prepare mode writes to build

- GIVEN `generate_all` called with `output_dir=/proj/build`
- WHEN `--all-files` executes via prepare
- THEN `/proj/build/codebook.md` and `/proj/build/codebooks/*.md` SHALL exist

#### Scenario: Nested subdirectories preserved in links

- GIVEN `[[file]]` for `raw/Labels/etiquetas_a.csv`
- WHEN standalone batch generates index
- THEN link SHALL be `codebooks/Labels/etiquetas_a.md` (and file at `cache/codebooks/Labels/etiquetas_a.md`)

#### Scenario: Index links are relative paths

- GIVEN generated `cache/codebook.md`
- WHEN any codebook link is extracted
- THEN path SHALL be relative (e.g., `codebooks/DPTO.md`) and MUST NOT be absolute
