# Delta for Codebook

## MODIFIED Requirements

### Requirement: Batch Generation (CB-R03)

When `--all-files` is specified, the system MUST generate one codebook for
every `[[file]]` entry in the TOML config that points to a supported-format
file. Directories and unsupported formats MUST be skipped with a warning.
Each codebook MUST be written to `data/codebooks/<rel-stem>.md`, where
`<rel-stem>` is the file's path relative to the `data/` directory with the
extension replaced by `.md` (e.g. `data/DPTO.csv` → `data/codebooks/DPTO.md`;
`data/Labels/etiquetas_a.csv` → `data/codebooks/Labels/etiquetas_a.md`). No
format suffix SHALL be appended. When two or more files resolve to the same
codebook path, the system MUST print an error naming each source file, MUST
exit 1, and MUST NOT write a codebook for any colliding file.
(Previously: every codebook was written alongside its data file as a shared
`codebook.md`, with `codebook_<fmt>.md` suffixes on same-directory collision —
making the per-file layout physically impossible.)

#### Scenario: Batch from TOML config

- GIVEN `dataset.toml` with `[[file]]` entries for `data/a.csv`,
  `data/b.parquet`, and `data/c.docx`
- WHEN `sofer codebook --config dataset.toml --all-files` is called
- THEN `data/codebooks/a.md` SHALL be generated for `a.csv`
- AND `data/codebooks/b.md` SHALL be generated for `b.parquet`
- AND `c.docx` SHALL be skipped with a warning

#### Scenario: Directory entry skipped

- GIVEN a `[[file]]` entry pointing to a directory
- WHEN `--all-files` executes
- THEN a warning SHALL be emitted
- AND no codebook SHALL be generated for that entry

#### Scenario: Nested file keeps its relative path

- GIVEN a `[[file]]` entry for `data/Labels/etiquetas_a.csv`
- WHEN `--all-files` executes
- THEN `data/codebooks/Labels/etiquetas_a.md` SHALL be generated

#### Scenario: Same-stem collision errors

- GIVEN `data/PROV.csv` and `data/PROV.parquet` in the same folder (both map to `data/codebooks/PROV.md`)
- WHEN `--all-files` executes
- THEN an error SHALL be printed naming both `PROV.csv` and `PROV.parquet`
- AND exit code SHALL be 1
- AND no codebook SHALL be written for either file

---

### Requirement: Root Index (CB-R04)

When `--all-files` is used, the system MUST generate a root `codebook.md` in
the TOML config's directory containing a table of contents with relative links
to each generated codebook and a dataset summary. The links SHALL point to the
per-file codebook paths under `data/codebooks/`.
(Previously: links pointed at per-directory `codebook.md` / `codebook_<fmt>.md`
files.)

#### Scenario: Root index after batch generation

- GIVEN `dataset.toml` in `/proj/` with files in `data/a.csv` and
  `data/b.parquet`
- WHEN `sofer codebook --config dataset.toml --all-files` completes
- THEN `/proj/codebook.md` SHALL exist
- AND SHALL contain links to `data/codebooks/a.md` and `data/codebooks/b.md`

## REMOVED Requirements

### Requirement: Output Collision (CB-R05)

(Reason: per-file output under `data/codebooks/` gives every file its own path,
making format-suffix naming (`codebook_<fmt>.md`) obsolete. Same-stem
collisions are now handled as errors under CB-R03.)
(Migration: consumers relying on `codebook_<fmt>.md` names must switch to
`data/codebooks/<rel-stem>.md`. Test `test_output_collision_uses_suffixes` is
replaced by the same-stem-collision error scenario under CB-R03.)
