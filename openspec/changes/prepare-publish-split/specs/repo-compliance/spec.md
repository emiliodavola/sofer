# Delta for repo-compliance

## ADDED Requirements

### Requirement: RC-R04 — Recursive entries stage correctly

Staging SHALL handle `recursive = true` entries without crashing. A
`recursive` entry pointing to a directory SHALL have its tree staged under the
entry's remote prefix by copying each file individually (or via
`shutil.copytree`); the directory itself SHALL NEVER be passed to
`shutil.copy2`. Passing a directory to `shutil.copy2` raises `PermissionError`
on Windows and `IsADirectoryError` on POSIX — this MUST NOT occur. Empty
directories SHALL stage zero files without error.

#### Scenario: Recursive directory stages its files

- GIVEN a `[[file]]` entry with `recursive = true` pointing to a directory containing `train.csv` and `test.csv`
- WHEN the staging step runs
- THEN both files SHALL be staged under the entry's remote prefix
- AND no exception SHALL be raised

#### Scenario: Nested subdirectories preserved

- GIVEN a recursive directory containing `Labels/etiquetas_a.csv`
- WHEN the staging step runs
- THEN `Labels/etiquetas_a.csv` SHALL be staged under the remote prefix

#### Scenario: Empty recursive directory is a no-op

- GIVEN a `recursive` entry pointing to an empty directory
- WHEN the staging step runs
- THEN zero files SHALL be staged
- AND no exception SHALL be raised

## REMOVED Requirements

### Requirement: Upload orchestration via uploader.upload() (§ 4.1)

(Reason: `uploader.py` is deleted and `upload()` is split into `prepare` (local
generation) and `publish` (delivery). The conversion → compliance → staging
sequence now belongs to `prepare`; the repo diff, overwrite protection, batch
`upload_folder` push, and post-upload report belong to `publish`. Scenario
preconditions in § 3.3.6 that reference `upload(cfg)` now refer to `prepare`
producing the staging directory.)
(Migration: PRP-02, PRP-03 (generation order); PUB-01 (batch upload), PUB-04
(dry-run diff).)

### Requirement: Codebook Batch Staging (RC-C01) (§ 4.2)

(Reason: staging codebooks into the package is now part of `prepare
--all-files`; delivery of the staged codebooks is covered by `publish`'s batch
upload.)
(Migration: PRP-04 (staging), PUB-01 (upload).)

### Requirement: Overwrite Protection Bypass for Auto-Generated Files (RC-C02) (§ 4.3)

(Reason: overwrite semantics are owned by the new commands' `--force` flags:
`prepare --force` for local regeneration, `publish --force` for remote files,
with auto-generated files (README.md, LICENSE, codebook.md, codebooks/**) still
bypassing protection on publish.)
(Migration: PRP-07 (prepare force), PUB-05 (publish force + auto-generated
bypass).)
