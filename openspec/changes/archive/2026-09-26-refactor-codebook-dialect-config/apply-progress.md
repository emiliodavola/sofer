# Apply Progress: codebook dialect defaults moved out of the signatures (GitHub #260)

**Change**: `2026-09-26-refactor-codebook-dialect-config`
**Mode**: Standard (Strict TDD disabled per `openspec/config.yaml`)

## Completed Tasks

- [x] 1.1 `_read_csv` dialect required keyword-only
- [x] 1.2 `_read_tsv` encoding required keyword-only
- [x] 1.3 `_read_file` dialect required keyword-only
- [x] 1.4 `generate` dialect required keyword-only
- [x] 1.5 `profile.py` non-streamed calls pass `config.CSV_*`
- [x] 1.6 `cli.py` docstring/comment truth
- [x] 2.1 Every `tests/test_codebook.py` reader/`generate` call passes the dialect
- [x] 2.2 `TestDialectParametersAreRequired` added
- [x] 2.3 `tests/test_config.py` call passes configured dialect
- [x] 3.1 `codebook` delta written (CB-R11/CB-R12 MODIFIED + fail-closed scenario)
- [x] 3.2 Canonical `codebook` spec composed
- [x] 4.1–4.5 Gates green (see verify-report.md)
- [x] 4.6 Verify evidence recorded
- [x] 5.1 Change folder archived

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `src/sofer/codebook.py` | Modified | `_read_csv`/`_read_tsv`/`_read_file`/`generate` lose the literal `";"`/`"utf-8-sig"` defaults; dialect is required keyword-only |
| `src/sofer/profile.py` | Modified | Two non-streamed `_read_file` calls pass `config.CSV_DELIMITER`/`config.CSV_ENCODING` |
| `src/sofer/cli.py` | Modified | Docstring/comment reflect the required-argument contract |
| `tests/test_codebook.py` | Modified | Explicit dialect at every call; new required-argument/`inspect` guards |
| `tests/test_config.py` | Modified | `generate_codebook` call passes the configured dialect |
| `openspec/specs/codebook/spec.md` | Modified | CB-R11/CB-R12 amended via `sdd-archive-compose` |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_codebook.py tests/test_config.py tests/test_profile.py -q` — 218 passed |
| Runtime harness command/scenario and result | `uv run pytest tests/ -q` — 2000 passed, 1 skipped; `bash scripts/check_core_coverage.sh` — exit 0, four 100.00% rows |
| Rollback boundary | revert `codebook.py`, `profile.py`, `cli.py`, both test files, canonical `codebook` spec |

## Deviations from Design

None — implementation matches design.

## Issues Found

- The local, gitignored `.coverage` file is a stale mid-run artifact: the plain
  suite read it before it was regenerated and `profile.py` measured 83.6%. A
  fresh `uv run coverage run -m pytest` measures `profile.py` at 96% and the
  contract test passes. Not a code regression; CI re-measures from scratch.

## Remaining Tasks

None.

## Status

All tasks complete. Ready for archive.
