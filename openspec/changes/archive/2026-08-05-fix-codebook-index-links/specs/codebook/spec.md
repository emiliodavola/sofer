# Delta for Codebook

## MODIFIED Requirements

### Requirement: Root Index (CB-R04)

When `--all-files` is used, the system MUST generate a root `codebook.md` in
the TOML config's directory containing a table of contents with relative links
to each generated codebook and a dataset summary. The links SHALL point to the
per-file codebook paths under the `codebooks/` prefix (matching the uploader's
HF repository staging layout), not under `data/codebooks/`.

(Previously: links pointed to `data/codebooks/` — produced 404 on Hugging Face
Hub because the uploader stages codebooks under `codebooks/`.)

#### Scenario: Root index after batch generation

- GIVEN `dataset.toml` in `/proj/` with files in `data/a.csv` and
  `data/b.parquet`
- WHEN `sofer codebook --config dataset.toml --all-files` completes
- THEN `/proj/codebook.md` SHALL exist
- AND SHALL contain links to `codebooks/a.md` and `codebooks/b.md`

#### Scenario: Nested subdirectories preserved in links

- GIVEN a `[[file]]` entry for `data/Labels/etiquetas_a.csv`
- WHEN `--all-files` generates the root index
- THEN the link SHALL point to `codebooks/Labels/etiquetas_a.md`

#### Scenario: Index links are relative paths

- GIVEN generated root index `codebook.md`
- WHEN any codebook link is extracted from the index
- THEN the path SHALL be a relative path (e.g., `codebooks/DPTO.md`)
- AND MUST NOT be an absolute path
