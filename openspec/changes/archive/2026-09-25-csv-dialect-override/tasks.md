# Tasks: 2026-09-25-csv-dialect-override

## Phase 1 — Domain (`profile.py`)

- [x] 1.1 `profile(...)` gains optional keyword `delimiter: str | None = None`,
      `encoding: str | None = None`; explicit → `config.CSV_*` for streamed
      formats (`.tsv` keeps `\t`); records used values in `FileMetadata`.
- [x] 1.2 `_read_dataset_for_profile(path, suffix, delimiter=None, encoding=None)`
      applies the same resolution and returns the used dialect.
- [x] 1.3 `generate_all_profiles(cfg, output_dir=None, delimiter=None, encoding=None)`
      threads the pair into `_read_dataset_for_profile`.
- [x] 1.4 Docstrings state the precedence and the `.tsv` carve-out.

## Phase 2 — CLI (`cli.py`)

- [x] 2.1 `--delimiter` / `--encoding` (default `None`) added to the `codebook`
      and `profile` subparsers via the shared `_add_dialect_args` helper.
- [x] 2.2 `_cmd_codebook`: single-file explicit → `config.CSV_*`; `--all-files`
      explicit → `generate_all` (None → `cfg.csv_*`).
- [x] 2.3 `_cmd_profile`: single-file explicit → `run_profile`; `--all-files`
      explicit → `generate_all_profiles`.
- [x] 2.4 `_echo_explicit_dialect(args)` prints the supplied override(s) to stderr.
- [x] 2.5 `codebook` / `profile` help and description strings updated.

## Phase 3 — MCP (`mcp_server.py`)

- [x] 3.1 `sofer_codebook`: optional `delimiter` / `encoding`; explicit →
      post-reload `sofer_config.CSV_*`; `dialect` envelope.
- [x] 3.2 `sofer_codebook_all`: same; explicit → `cfg.csv_*` via `generate_all`.
- [x] 3.3 `sofer_profile`: same → `run_profile`.
- [x] 3.4 `sofer_profile_all`: same → `generate_all_profiles`.
- [x] 3.5 Parameter descriptions state the fallback; `dialect` declared in the
      four tools' `output_schema` (otherwise FastMCP drops it).

## Phase 4 — Tests

- [x] 4.1 `tests/test_cli.py::TestExplicitCsvDialectOverride` (10 tests).
- [x] 4.2 `tests/test_mcp_server.py::TestExplicitCsvDialectOverrideMcp` (6 tests).
- [x] 4.3 `tests/test_mcp_schema.py::TestExplicitDialectParams` (3 tests).
- [x] 4.4 `tests/test_profile.py::TestProfileExplicitDialectPrf07` (5 tests).
- [x] 4.5 `tests/test_parity.py` flag_map registers the two new CLI flags.

## Phase 5 — Docs

- [x] 5.1 `README.md`: flags, precedence, `.tsv` carve-out, MCP params + `dialect`.
- [x] 5.2 `README_ES.md`: mirrored.

## Phase 6 — Specs

- [x] 6.1 Delta `specs/codebook/spec.md`: ADDED CB-R12.
- [x] 6.2 Delta `specs/profile/spec.md`: ADDED PRF-07.
- [x] 6.3 Delta `specs/cli/spec.md`: ADDED CLI-R12.
- [x] 6.4 Delta `specs/mcp-server/spec.md`: ADDED MSP-R18.
- [x] 6.5 Synced all four canonical specs with the deltas.

## Phase 7 — Verification

- [x] 7.1 Focused area: `uv run pytest tests/test_cli.py tests/test_mcp_server.py
      tests/test_mcp_schema.py tests/test_profile.py tests/test_codebook.py -q` —
      608 passed, 0 failed, 1 skipped.
- [x] 7.2 `uv run coverage run -m pytest tests/ -q` — 1913 passed, 2 skipped.
- [x] 7.3 `ruff check`/`format` clean; `mypy src/ scripts/` no issues; `pyright`
      0 errors (1 pre-existing `tomli` warning).
- [x] 7.4 `scripts/check_test_mapping.py` — OK; core coverage 4×100%; floors
      profile 96% / mcp_registration 100% / verification 100%; TOTAL 93%.
- [x] 7.5 Independent read-only verification by a `general` subagent — 12/12
      claims PASS, 0 falsified; two wording/naming nits fixed (MSP-R18 "successful
      envelope"; test renames).

## Phase 8 — Archive + PR

- [x] 8.1 `apply-progress.md`, `verify-report.md`, `sync-report.md`,
      `archive-report.md` written; change moved under `openspec/changes/archive/`.
- [ ] 8.2 Commit, push, open the PR against `dev` (assigned `emiliodavola`, body
      per `.github/PULL_REQUEST_TEMPLATE.md`, `Refs #204`).
