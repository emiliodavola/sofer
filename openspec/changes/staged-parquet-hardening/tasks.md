# Tasks: Harden the staged-Parquet handshake

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 300–380 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR to dev, 2 internal commits |
| Delivery strategy | exception-ok (single PR, 2000-line budget) |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | RC-R16 collision refusal (commit 1) | PR 1 | `uv run pytest tests/test_mirror.py tests/test_model.py tests/test_cli.py -q` | `uv run sofer prepare <colliding.toml>` exits 1, no output dir | Revert commit 1 |
| 2 | RC-R17 unreadable-parquet warning (commit 2) | PR 1 | `uv run pytest tests/test_repo_compliance.py -q` | Corrupt staged `.parquet`; re-prepare → one `[!]`, CSV fallback | Revert commit 2 |

## Phase 1: RC-R16 — Case-fold collision refusal (commit 1)

- [x] 1.1 RED (tests/test_mirror.py, new `TestValidateCaseFoldCollisions`): S1 error names both remotes; S2 exact dup → `[]`; S3 `straße`/`strasse` → `[]`; S4 recursive/non-.csv → `[]`, include_in_schema=false & upload_as_csv `.csv` pair → error
- [x] 1.2 GREEN (src/sofer/_mirror.py): add `_validate_case_fold_collisions(cfg) -> list[str]` after `parquet_remote_for` (line 72); eligible = `.csv` case-insens. AND not recursive (upload_as_csv/include_in_schema NOT gates — D2); key `parquet_remote_for(entry.remote).lower()` (D3); `seen: dict[str,str]`, error iff `seen[key] != remote` (D4); msg per design line 62
- [x] 1.3 RED (tests/test_model.py, `TestValidate` line 219): S1–S4 via `validate()` — collision message present; exact-dup/ß clean
- [x] 1.4 GREEN (src/sofer/model.py): import helper (safe — `_mirror` imports model only under TYPE_CHECKING); `validate()` `errors.extend(...)` after line 505, before `return errors` (517)
- [x] 1.5 RED (tests/test_cli.py, `TestLoadAndValidate` line 164): S5 — colliding TOML → `_cmd_prepare` rc 1 (cli.py 118), output dir never created
- [x] 1.6 Gate: `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`
- [x] 1.7 Commit 1: `fix(mirror): refuse case-fold collisions on staged-parquet remotes (RC-R16)` — _mirror.py, model.py, + 3 test files (1ff981c)

## Phase 2: RC-R17 — Unreadable staged-Parquet warning (commit 2)

- [x] 2.1 RED (tests/test_repo_compliance.py, import block 11–22 + new `TestClassifyParquetReadFailure`): ArrowInvalid→`corrupt/parse`; PermissionError/ArrowIOError→`io/permission`; RuntimeError→`other`
- [x] 2.2 GREEN (src/sofer/repo_compliance.py): add `import pyarrow as pa` (line 15); add `_classify_parquet_read_failure(exc) -> str` near `_read_parquet_sample` (line 346)
- [x] 2.3 GREEN: `_read_parquet_sample` (346–380) re-raises (drop `except: return None`); return type non-Optional; docstring documents raise contract
- [x] 2.4 RED (`TestBuildSchemaReportParquetFallback` line 658): S6 corrupt bytes→`corrupt/parse`; S7 directory path→`io/permission`; S8 monkeypatched RuntimeError→`other`; S9 absent→RC-R14 only; S10 2 entries/1 key→1 warning; S11 readable→silent
- [x] 2.5 GREEN: call site 485–491 — add `_warned_unreadable: set[str]` (near `_warned_missing`, line 447); try/except around `_read_parquet_sample`; warn-once `[!]` naming key+class (design line 63); `use_parquet = False`
- [x] 2.6 Gate: `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`
- [x] 2.7 Commit 2: `fix(repo-compliance): warn once and fall back when staged parquet unreadable (RC-R17)` — repo_compliance.py, test_repo_compliance.py (7816b2b)

## Phase 3: Documentation & handoff

- [x] 3.1 No README/CLI-help updates (no new flags); no hardcoded values introduced (RC-R16/R17 messages are inline f-strings per design D8, matching `_warn_duplicate_remotes`/RC-R14)
- [x] 3.2 Full suite green (795 passed); branch pushed; PR #65 to dev opened, template filled
