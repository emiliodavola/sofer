# Delta for repo-compliance

## ADDED Requirements

### Requirement: Codebook Upload Orchestration (RC-C01)

The `upload()` orchestration SHALL upload the generated codebook artifacts to
the Hugging Face repository after the data files. The root index `codebook.md`
in the config directory SHALL be uploaded as `codebook.md`. Every per-file
codebook under `data/codebooks/` SHALL be uploaded mirroring its relative path
under a `codebooks/` prefix (e.g. `data/codebooks/DPTO.md` →
`codebooks/DPTO.md`; `data/codebooks/Labels/etiquetas_a.md` →
`codebooks/Labels/etiquetas_a.md`). A missing root index or missing
`data/codebooks/` directory SHALL be skipped without failing the upload.
(Previously: only the single file declared in `cfg.codebook` was uploaded, to
`codebook/{name}` — that behavior is superseded.)

#### Scenario: Upload codebooks after data files

- GIVEN generated `codebook.md` and `data/codebooks/DPTO.md` on disk
- WHEN `upload()` executes
- THEN the data files SHALL be uploaded before any codebook
- AND the root index SHALL be uploaded to `codebook.md`
- AND the per-file codebook SHALL be uploaded to `codebooks/DPTO.md`
- AND `upload()` SHALL return 0

#### Scenario: No codebooks generated

- GIVEN no `codebook.md` and no `data/codebooks/` directory on disk
- WHEN `upload()` executes
- THEN no codebook upload SHALL be attempted
- AND the data files SHALL still be uploaded
- AND `upload()` SHALL return 0

#### Scenario: Declared single codebook is superseded

- GIVEN `cfg.codebook = "codebook.md"` in the TOML
- WHEN `upload()` executes with generated codebooks present
- THEN the generated root index and per-file codebooks SHALL be uploaded per
  the RC-C01 convention
- AND the legacy `codebook/{name}` single-file upload SHALL NOT occur
