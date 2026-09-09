# Publish Specification

## Purpose

Delivery of a prepared dataset package to a target. `publish` pushes the
prepared package to the Hugging Face Hub via a single `upload_folder` call
(`--target hf`, default) or writes it to a local directory (`--target local`).
It auto-prepares when artifacts are stale or missing, and can dry-run, force,
verify, and keep CSVs.

## Requirements

### Requirement: hf target uploads via upload_folder (PUB-01) — Universal (Modified 2026-08-29, fix-multisheet-parquet-publish)

`publish --target hf` SHALL ensure the repository exists, run the quality gate, and push via single `upload_folder`. The system MUST derive remotes via `expanded_planned_remotes` when staging is resolvable else `planned_remotes`. `_repo_diff_summary`, `_copy_package`, `_check_overwrite_protection`, `_print_split_mapping_validation`/`detect_splits`, and dry-run MUST share the expanded set. `keep_csv` SHALL remain CSV-only.

(Previously: only `_copy_package` globbed; diff/protection/splits hid sheets behind single `stem.parquet`.)

#### Scenario: Diff universal remotes
- GIVEN `DATA/GOT Ano.csv`, `Data/B.tsv`
- WHEN diff runs
- THEN reports `data/got_ano.parquet`, `data/b.parquet`

#### Scenario: Copy stages parquets
- GIVEN `report__ventas.parquet` staged
- WHEN copy stages
- THEN includes it; expanded==staged

#### Scenario: keep_csv CSV-only
- GIVEN `a.csv->parquet`, `b.xlsx->b__s1.parquet`, `--keep-csv`
- WHEN staging
- THEN `a.csv` added; `b.xlsx` not

#### Scenario: Full hf publish
- GIVEN prepared output valid
- WHEN `publish dataset.toml` runs
- THEN repo ensured, diff, upload_folder once, split report, exit 0

#### Scenario: Quality gate blocks
- GIVEN quality fail
- WHEN publish runs
- THEN report, no upload, exit 1

#### Scenario: upload failure
- GIVEN upload_folder raises
- WHEN publish runs
- THEN error, exit 1

#### Scenario: Missing files
- GIVEN absent file
- WHEN staging
- THEN NOT FOUND, not included

#### Scenario: Multi-sheet diff and per-sheet protection
- GIVEN `report.xlsx` 2 sheets, Hub has `report__ventas.parquet`
- WHEN diff/protection
- THEN diff lists 2; only `ventas` protected w/o --force

#### Scenario: Split counts expanded
- GIVEN `report.xlsx` 2 sheets
- WHEN detect_splits
- THEN count 2

---

### Requirement: local target writes a complete package (PUB-02) — Universal (Modified 2026-08-29)

`publish --target local` SHALL delegate remote planning to `_mirror.planned_remotes` with normalization and `convert_to_parquet` handling, writing the complete package (normalized parquets, `README.md`, `LICENSE`, codebooks) to `--output` with no network calls. No duplication of gate logic.

(Previously: local path used same duplicated gate.)

#### Scenario: Local output uses normalized universal remotes
- GIVEN `remote="DATA GÖT Año.XLSX"` multi-sheet with `--target local --output ./out/`
- WHEN command executes
- THEN `./out/report__ventas.parquet` (normalized) SHALL exist and no network request SHALL be made

#### Scenario: Package written to --output (legacy preserved)

- GIVEN a prepared package and `sofer publish dataset.toml --target local --output ./out/`
- WHEN the command executes
- THEN `./out/` SHALL contain the parquet tree, README.md, LICENSE, and codebooks
- AND no network request SHALL be made

#### Scenario: Local target runs offline

- GIVEN no network connectivity
- WHEN `publish --target local` executes
- THEN the command SHALL complete successfully

### Requirement: Publish delegation invariant (PUB-09) — Modified 2026-08-29, fix-multisheet-parquet-publish

`expanded_planned_remotes`, diff, and copy MUST share ONE eligibility: `{.csv,.tsv,.xlsx,.jsonl}`+`convert!=false`+NOT `recursive` → normalized `parquet_remote_for` (xlsx→`__` set) else passthrough. Collisions MUST error identically. Diff vs staged divergence SHALL be a bug. `planned_remotes` is logical; expanded is ground truth.

(Previously: invariant only for `planned_remotes`; expansion diverged.)

#### Scenario: Diff and copy agree
- GIVEN mixed csv/tsv/xlsx/jsonl/parquet
- WHEN diff and copy compute
- THEN sets identical

#### Scenario: Collision error
- GIVEN `data/report.xlsx` vs `DATA/REPORT.XLSX`
- WHEN dry-run validates
- THEN error both, no upload

### Requirement: Expanded planned remotes via mirror scan (PUB-10) — Added 2026-08-29, fix-multisheet-parquet-publish

The system MUST provide `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `_mirror.py`. It SHALL reuse `sanitize_sheet_name`/`normalize_parquet_remote` and SHALL NOT open workbooks. For convertible `.xlsx` (not recursive, `convert_to_parquet` true): if `staging_dir` exists it MUST glob `<dir>/<stem>__*.parquet`; on match it SHALL emit them else single `<stem>.parquet`. If absent it SHALL fallback to `planned_remotes`. Others equal `planned_remotes`. `keep_csv` SHALL remain CSV-only.

#### Scenario: Multi-sheet expands
- GIVEN `report.xlsx` staged as `report__ventas.parquet`, `report__costos.parquet`
- WHEN helper runs
- THEN both `__` remotes present, not `report.parquet`

#### Scenario: Single-sheet stays single
- GIVEN `single.xlsx` staged as `single.parquet`
- WHEN helper runs
- THEN exactly `single.parquet`

#### Scenario: Fallback and invariants
- GIVEN `staging_dir=None`, `recursive=true`
- WHEN helper runs
- THEN `planned_remotes` placeholder; recursive unchanged; no openpyxl

---

### Requirement: Auto-prepare when artifacts are stale or missing (PUB-03)

`publish` SHALL run `prepare` automatically before delivering when the output
directory has no Parquet files, or when the TOML's modification time OR any
declared source file's modification time (for ALL supported formats — CSV,
TSV, Parquet, Excel, JSONL) is newer than the newest Parquet file. The TOML and
source files SHALL be the source of truth; Parquet existence is the fallback
check.

Auto-prepare SHALL run with the all-files behavior ENABLED (equivalent to
`prepare --all-files`): the prepared package SHALL include per-file codebooks
(`codebooks/**/*.md`) and the root `codebook.md` index, so that a bare
`sofer publish dataset.toml` delivers a complete package — data + README +
LICENSE + codebooks.

(Previously: auto-prepare ran plain `prepare(cfg, source, force=True)` with
all-files disabled, so published packages never contained codebooks and nothing
warned about it.)

#### Scenario: Parquet missing triggers prepare

- GIVEN a config whose output directory contains no `.parquet` files
- WHEN `publish` executes
- THEN `prepare` SHALL run first
- AND the freshly prepared package SHALL be delivered

#### Scenario: TOML newer than parquet triggers prepare

- GIVEN `dataset.toml` modified after the last Parquet write
- WHEN `publish` executes
- THEN `prepare` SHALL run first

#### Scenario: Source file newer than parquet triggers prepare

- GIVEN a declared source CSV (or any supported format) modified after the
  last Parquet write, even when the TOML is unchanged
- WHEN `publish` executes
- THEN `prepare` SHALL run first

#### Scenario: Up-to-date package skips prepare

- GIVEN Parquet files exist AND the TOML and all source files are older than them
- WHEN `publish` executes
- THEN no `prepare` SHALL run
- AND the existing package SHALL be delivered

#### Scenario: Auto-prepare generates codebooks

- GIVEN a stale build directory (sources newer than Parquet)
- WHEN `publish` executes and auto-prepare runs
- THEN the delivered package SHALL include `codebooks/**/*.md` and root `codebook.md`
- AND the pinned test asserting "bare prepare stages no codebooks" SHALL be reversed

---

### Requirement: --dry-run shows the diff without publishing (PUB-04)

`--dry-run` SHALL print the repo diff summary and split report without pushing
any files and without mutating the output directory.

#### Scenario: Dry-run does not upload

- GIVEN a valid config and `sofer publish dataset.toml --dry-run`
- WHEN the command executes
- THEN the diff summary SHALL be printed
- AND no `upload_folder` call SHALL be made
- AND the exit code SHALL be 0

---

### Requirement: --force bypasses overwrite protection (PUB-05)

Auto-generated files — `README.md`, `LICENSE`, `codebook.md`, and
`codebooks/**/*.md` — SHALL always overwrite remote files without prompting,
even without `--force`. For all other remote files, overwrite protection SHALL
apply unless `--force` is given.

Remote inspection SHALL be fail-closed: `_inspect_repo` SHALL return an empty
list ONLY when the repository does not exist (`RepositoryNotFoundError`); ANY
other inspection failure (network, authentication, rate limit) SHALL raise and
abort the publish with exit code 1 BEFORE any staging or upload — inspection
failure is NEVER treated as an empty repo, so overwrite protection always
sees the true remote state. `_ensure_repo` SHALL likewise raise (not print and
continue) when `create_repo` fails for a reason other than "already exists".
A post-upload inspection failure SHALL NOT fail an already-successful upload:
it prints a warning and skips the split report only.

#### Scenario: Auto-generated files always overwrite

- GIVEN `README.md` and `LICENSE` already exist on the Hub
- AND no `--force`
- WHEN `publish` executes
- THEN both SHALL be uploaded unconditionally
- AND no prompt SHALL block them

#### Scenario: Protected file needs --force

- GIVEN a data file already exists on the Hub and no `--force`
- WHEN `publish` executes
- THEN overwrite protection SHALL refuse the file
- AND with `--force` the file SHALL be overwritten

#### Scenario: Repo-not-found reads as empty

- GIVEN `list_repo_files` raises `RepositoryNotFoundError`
- WHEN `_inspect_repo` executes
- THEN it SHALL return `[]` (empty repo) and publish SHALL proceed normally

#### Scenario: Inspection failure fails closed

- GIVEN `list_repo_files` raises any other error (e.g. network failure)
- WHEN `publish` executes against hf
- THEN the publish SHALL abort with exit code 1 BEFORE any upload
- AND `upload_folder` SHALL NOT be called
- AND the error SHALL be surfaced (never a silent empty list)

#### Scenario: create_repo failure fails closed

- GIVEN `create_repo` fails for a reason other than "already exists"
- WHEN `_ensure_repo` executes
- THEN the failure SHALL raise (publish aborts, exit code 1)

---

### Requirement: --keep-csv uploads CSVs alongside parquet (PUB-07)

For the `hf` target, `--keep-csv` SHALL include each converted entry's original
CSV in the upload at its original remote path, alongside the Parquet. For the
`local` target, `--keep-csv` SHALL have no effect.

#### Scenario: CSV kept alongside parquet on hf

- GIVEN `sofer publish dataset.toml --keep-csv`
- WHEN the hf upload completes
- THEN `data/PROV/train.csv` SHALL be uploaded alongside `data/PROV/train.parquet`

#### Scenario: --keep-csv ignored for local target

- GIVEN `sofer publish dataset.toml --target local --keep-csv`
- WHEN the command executes
- THEN the local package SHALL contain only the default artifacts

---

### Requirement: Codebook-absence warning before delivery (PUB-08)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

When delivering to the `hf` target, if the build directory contains NO codebooks
(neither `codebook.md` nor `codebooks/**/*.md`) at delivery time, `publish`
SHALL print a warning advising how to generate them. The warning MUST NOT block
delivery — the upload SHALL proceed for all other files.

(Previously: absence was silent — the repo diff simply omitted the codebook
entries.)

#### Scenario: Build without codebooks warns but delivers

- GIVEN an up-to-date build directory containing no codebook files
- WHEN `publish` executes against hf
- THEN a codebook-missing warning SHALL be printed before upload
- AND the remaining package SHALL still be delivered (exit 0)

#### Scenario: Complete package does not warn

- GIVEN a build directory that includes codebooks
- WHEN `publish` executes
- THEN no codebook-missing warning SHALL be printed

---

### Requirement: Build cleanup on successful publish (PUB-11)

`sofer publish --clean` (default off) MUST delete the resolved build directory only after a successful `hf` upload where `fail == 0`. The system MUST NOT delete on `--dry-run`, quality-gate block, or upload failure. For `--target local` the system MUST NOT delete unless `--clean` is explicitly given; then it MUST delete the `--output` destination, not the source build. The build path MUST be resolved via `resolve_output_dir(cfg, --output)` so `--output` overrides are honored. `--clean` alone MUST be build-only; deletion of `cache/` (`config.OUTPUT_DIR` anchored to `cfg._base_dir`, shared tool-wide) MUST require opt-in `--clean-cache` (or `--clean --all`), warning that siblings share it.

#### Scenario: Successful hf publish with --clean deletes build

- GIVEN `build/` exists and `publish --target hf --clean` succeeds with `fail == 0`
- WHEN upload completes
- THEN `build/` (resolved via `resolve_output_dir`) SHALL be removed

#### Scenario: --clean --clean-cache deletes build and cache

- GIVEN `build/` and `cache/` exist and `publish --target hf --clean --clean-cache` succeeds
- WHEN upload completes
- THEN both `build/` and `cache/` SHALL be removed

#### Scenario: Dry-run with --clean does not delete

- GIVEN `publish --dry-run --clean` invoked
- WHEN diff/split report prints
- THEN neither `build/` nor `cache/` SHALL be removed

#### Scenario: Quality-gate block does not delete

- GIVEN quality gate fails and `--clean` was given
- WHEN `publish` exits 1 without upload
- THEN neither `build/` nor `cache/` SHALL be removed

#### Scenario: Upload failure does not delete

- GIVEN `upload_folder` raises and `--clean` was given
- WHEN `publish` exits 1
- THEN neither `build/` nor `cache/` SHALL be removed

#### Scenario: Local target without explicit --clean does not delete

- GIVEN `publish --target local --output ./out` without `--clean`
- WHEN command completes with exit 0
- THEN neither `./out/` nor `build/`/`cache/` SHALL be removed

#### Scenario: Local target with explicit --clean deletes destination

- GIVEN `publish --target local --output ./out --clean` succeeds
- WHEN command completes
- THEN `./out/` SHALL be removed and source `build/` SHALL remain

#### Scenario: Custom --output build cleanup anchored correctly

- GIVEN `publish --target hf --output ./staging --clean` succeeds
- WHEN upload completes
- THEN `./staging/` SHALL be removed and `cfg._base_dir / "cache"` SHALL remain unless `--clean-cache` given


### Requirement: Package artifact manifest with explicit publishable/intermediate boundary (PUB-12)

The publish flow SHALL operate on one machine-readable package manifest listing every artifact of the selected build profile — `source` (the real config path), `artifact_type`, `path`, and `status` — with artifacts classified as **publishable** (parquet incl. multi-sheet expansion, csv when keep_csv, README, LICENSE, codebook.md, codebooks/**) or **intermediate** (profiles, renders, per-sheet intermediates, schema/card inputs). `prepare` writes the manifest into the output dir; publish dry-run and confirm SHALL read the SAME manifest to plan and to enforce contents (no divergence).

Missing **required** artifacts SHALL block confirm with a stable `error_code` and a concrete recovery (re-run prepare); optional artifacts absent SHALL be marked `optional` and SHALL NOT emit the "missing artifact" warning (no silent omission, no false warning). Staleness SHALL key on the real config path (custom TOML names and multi-sheet Excel outputs included). Local delivery SHALL honor `force`. Remote inspection failures SHALL fail closed (unchanged PUB-05).

(Previously: the package boundary was implicit — plan_remote_files derived the dry-run set and codebook_remotes were collected from the output dir, with a warning when codebooks were absent that could be a false positive for optional artifacts.)

#### Scenario: Manifest lists exact publishable set for single-sheet source

- GIVEN a single-CSV dataset and a fresh prepare
- THEN `output_dir/manifest.json` SHALL list each parquet, README.md, LICENSE, and codebook.md as `staged`
- AND profiles/renders present in the tree SHALL be `intermediate` (never publishable)

#### Scenario: Multi-sheet Excel expansion is manifest-correct

- GIVEN an XLSX source converted to `stem__sheet.parquet` sheets
- THEN every sheet parquet SHALL appear in the manifest with its per-sheet path

#### Scenario: Missing required artifact blocks confirm with recovery

- GIVEN a manifest missing a required codebook that the profile promises
- WHEN confirm runs
- THEN it SHALL fail with a stable `error_code` and a `recovery` naming re-run prepare

#### Scenario: Optional absent artifact does not warn

- GIVEN a profile whose renders are optional and absent
- WHEN dry-run/confirm run
- THEN no "missing" warning SHALL be emitted for the optional artifact and its manifest entry SHALL read `optional`

#### Scenario: Dry-run and confirm share one manifest

- GIVEN a prepared package
- WHEN dry-run plans and confirm uploads
- THEN both SHALL consume the same `manifest.json` entries (structure, not re-derived sets)

#### Scenario: Custom config TOML name invalidates the package

- GIVEN a dataset configured via `custom-name.toml`
- WHEN the TOML is modified after the newest parquet
- THEN the package SHALL be treated as stale

#### Scenario: Local delivery overwrite protection honors force

- GIVEN a local target with an existing conflicting file
- WHEN `force=false`
- THEN the delivery SHALL refuse to overwrite
- AND with `force=true` it SHALL overwrite
