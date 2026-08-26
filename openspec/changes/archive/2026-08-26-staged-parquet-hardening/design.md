# Design: Harden the staged-Parquet handshake

## Technical Approach

Two isolated, additive defenses. **RC-R16** (#63): a new
`_validate_case_fold_collisions(cfg)` helper in `_mirror.py` is called from
`DatasetConfig.validate()` (model.py), so case-differing remotes refuse the config
before any staging (exit 1 via the existing `_load_and_validate` path). **RC-R17**
(#64): `_read_parquet_sample` re-raises on read failure; its single call site in
`_build_schema_report_impl` classifies the exception, emits one warn-once `[!]`,
then falls back to CSV. `parquet_remote_for` and all on-disk layout stay unchanged.

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Helper name/location/signature | `_validate_case_fold_collisions(cfg: DatasetConfig) -> list[str]` in `_mirror.py` beside `_validate_remote_paths` | Renaming the dead `_validate_remote_paths` would churn `test_splits.py` (its only consumer) for no benefit; the two are distinct concerns. `_mirror` is the module's stated home for remote-path validation. No runtime cycle (`_mirror` imports model only under TYPE_CHECKING). |
| D2 | Scan eligibility | `.csv` (case-insensitive) AND not `recursive`; `include_in_schema` and `upload_as_csv` are NOT gates | `prepare.py` conversion loop (667–675) does not gate on `include_in_schema`, and section 7 (768–775) stages non-converted files (`upload_as_csv`, `.parquet`) via `copy_to_mirror` — so include_in_schema=false AND upload_as_csv `.csv` remotes are physically staged and can collide. Binding decisions override spec S4's `include_in_schema=false` and `upload_as_csv` bullets. `.parquet` remotes excluded per spec S4 (pre-existing gap; follow-up). |
| D3 | Equivalence function | `str.lower()` on the derived parquet key: `parquet_remote_for(entry.remote).lower()` | Spec S3 requires `straße`≠`ss` (no error), but Python `casefold()` folds ß→ss (verified) making them equal → S3 would fail. `lower()` satisfies S3, is ASCII-identical to casefold (the entire practical space), and matches the repo's `.lower()` gating idiom. Keying on the DERIVED parquet key (not the raw remote) also catches backslash-vs-slash pairs (`data\a\c.csv` vs `data/a/c.csv`) that normalize to the same physical key via RC-R15 — strictly more faithful to the physical collision. |
| D4 | RC-R16↔RC-R11 boundary | Skip verbatim-equal: error only when `seen[key] != remote` (first-wins `seen: dict[str,str]`) | Exact dups keep RC-R11's non-aborting `[!]`; case-fold collisions refuse. No double-report; declaration-ordered, deterministic. |
| D5 | Error mechanism | Append message to `validate()`'s `list[str]`; CLI prints `✗` and returns 1 | Matches every existing validate() error and the `_load_and_validate` exit-1 path (cli.py 66–71), before `resolve_output_dir`/`run_prepare` ⇒ before staging (S5). |
| D6 | RC-R17 mechanism | `_read_parquet_sample` re-raises (drop `except: return None`); call site catches | Single call site (488); re-raise is minimal, proposal-mandated, and the return type simplifies to non-Optional. |
| D7 | Failure classification | `_classify_parquet_read_failure(exc)`: `pa.ArrowInvalid`→`corrupt/parse`; `OSError`→`io/permission`; else `other` | Verified: garbage/empty/truncated→ArrowInvalid; `ArrowIOError`⊂`OSError`; a directory path raises `PermissionError`. Requires adding `import pyarrow as pa` (repo_compliance currently imports only `pq`). |
| D8 | Message/vocabulary | Inline f-strings (repo convention); failure tokens returned by classifier (single source) and interpolated | Matches RC-R14/`_warn_duplicate_remotes`; the classifier is the single source of the closed vocabulary → no duplication. |

## Data Flow

```
DatasetConfig.validate() ── errors.extend(_validate_case_fold_collisions(self))
   → collision? → CLI prints ✗ → return 1 (no staging)          [RC-R16]
build_schema_report ── _build_schema_report_impl
   candidate.exists()? ── no ──▶ RC-R14 [!] (absent)            [mutually exclusive]
                        └─ yes ── _read_parquet_sample
                              ── raise ──▶ classify → [!] key+class → CSV fallback [RC-R17]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | Modify | Add `_validate_case_fold_collisions(cfg)`; `_validate_remote_paths` untouched. |
| `src/sofer/model.py` | Modify | Import helper; `validate()` extends with its result after the file-entry checks (~line 505). |
| `src/sofer/repo_compliance.py` | Modify | Add `import pyarrow as pa`; `_read_parquet_sample` re-raises + new docstring; add `_classify_parquet_read_failure`; `_warned_unreadable` + try/except + `[!]` at 486–491. |
| `tests/test_mirror.py` | Modify | Unit tests for `_validate_case_fold_collisions` (S1–S4). |
| `tests/test_model.py` | Modify | `validate()`-level collision tests (S1–S4, incl. include_in_schema=false). |
| `tests/test_cli.py` | Modify | S5: `_cmd_prepare` returns 1, output dir absent. |
| `tests/test_repo_compliance.py` | Modify | S6–S11 + `_classify_parquet_read_failure` units. |

## Interfaces / Contracts

```python
# _mirror.py
def _validate_case_fold_collisions(cfg: DatasetConfig) -> list[str]:
    # key = parquet_remote_for(entry.remote).lower(); skip recursive / non-.csv (upload_as_csv & include_in_schema NOT gates per D2)
    # seen: dict[str, str]; if seen[key] != remote: append error naming (first, current)

# repo_compliance.py
def _classify_parquet_read_failure(exc: Exception) -> str:  # "corrupt/parse" | "io/permission" | "other"
# _read_parquet_sample(...) -> tuple[list[str], list[list[str]], pq.ParquetFile]  # RAISES on failure
```

RC-R16 error (in `validate()` list): `"Case-fold collision: remotes '{first}' and '{second}' differ only by case and would map to the same staged Parquet file; rename one of them."`
RC-R17 warning (printed): `"  [!] Staged Parquet '{parquet_key}' exists but could not be read ({failure_class}); falling back to CSV inference."`

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (`test_mirror.py`) | RC-R16 S1–S4 | Direct helper: message names both remotes; `[]` for exact-dup / ß / recursive / non-.csv; error for an include_in_schema=false pair and for an upload_as_csv `.csv` pair (D2) |
| Integration (`test_model.py`) | RC-R16 via `validate()` | Constructed `DatasetConfig` with real local files; `validate()` contains the collision message |
| CLI (`test_cli.py`) | RC-R16 S5 | `_cmd_prepare` → rc 1; staging dir not created |
| Integration (`test_repo_compliance.py`) | RC-R17 S6–S11 | Corrupt bytes→`corrupt/parse`; directory path→`io/permission`; monkeypatch `RuntimeError`→`other`; absent→RC-R14 only; two entries one key→1 warning; readable→silent |
| Unit (`test_repo_compliance.py`) | `_classify_parquet_read_failure` | ArrowInvalid/PermissionError/ArrowIOError/RuntimeError → correct classes |

## Migration / Rollout

No migration required; additive and isolated. Rollback: revert each commit
independently — no schema or on-disk change.

## Open Questions

None blocking. Archive-time spec notes: (a) S4 lists `include_in_schema=false` as
ineligible — superseded by the binding decision (scanned); (b) "Equivalence is
`str.casefold()` only" contradicts S3 — resolved as `str.lower()`.
