# Tasks: Fix staged-parquet staging lookup (remote-relative keys)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~480–620 (src ~90, tests ~380–500, docs/spec edits ~20) |
| 400-line budget risk | High (exceeds default 400; within project review budget of 2000) |
| Chained PRs recommended | No — single PR, 2 work-unit commits per design § Migration/Rollout |
| Suggested split | Single PR on `fix/staged-parquet-stem-collision` → `dev`; commit 1 then commit 2 |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: High
```

Rationale: exceeds 400-line default but stays well under the approved 2000-line review budget; commit 1 is independently revertable and behavior-preserving, so a single PR preserves rollback safety without chained-PR overhead.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Extract `parquet_remote_for()` + adopt all 7 sites + unit tests (behavior-preserving) | PR 1 (commit 1) | `uv run pytest tests/test_mirror.py -q` | N/A — pure refactor; full suite proves no behavior change | Revert commit 1 only; no consumer touched (`repo_compliance.py` untouched) |
| 2 | Lookup flip + origins + warning + scenario tests + fixture restage | PR 1 (commit 2) | `uv run pytest tests/test_repo_compliance.py tests/test_prepare.py tests/test_mirror.py -q` | `uv run pytest tests/test_parquet_conversion.py tests/test_publish.py -q` (staging handshake end-to-end) | Revert commit 2 restores old flat-lookup contract |

## Phase 1: Helper extraction + call-site adoption (commit 1)

- [x] 1.1 Add `parquet_remote_for(remote: str) -> str` to `src/sofer/_mirror.py` next to `planned_remotes()` per design D1: backslash→slash normalization, then `str(PurePosixPath(posix_remote).with_suffix(".parquet"))`; docstring states pure/idempotent/case-preserving contract.
- [x] 1.2 Adopt at `_mirror.py:82` (`planned_remotes`): replace inline expression with `parquet_remote_for(entry.remote)`.
- [x] 1.3 Adopt at `src/sofer/prepare.py`:364 (`_assert_cross_file_schema`), :576 (`_check_local_overwrite` — wrap as `output_dir / PurePosixPath(parquet_remote_for(entry.remote))`), :709 (staging step 5, on `original_remote`).
- [x] 1.4 Adopt at `src/sofer/publish.py`:233 (`_repo_diff_summary`) and :479 (`_copy_planned_files`).
- [x] 1.5 Add helper unit tests to `tests/test_mirror.py`: S6-unit (`data\a\train.csv` → `data/a/train.parquet`) and S7 idempotency (`parquet_remote_for(forward-slash)` unchanged, incl. backslash variants).
- [x] 1.6 Gate: `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`. Commit 1: `refactor(mirror): extract parquet_remote_for and adopt at all derivation sites`.

## Phase 2: Consumer flip — lookup, origins, warning (commit 2)

- [x] 2.1 In `src/sofer/repo_compliance.py` `_build_schema_report_impl` (~:459-471): delete `entry_stem`; init `_warned_missing: set[str] = set()` before the loop; eligible entries resolve `candidate = staging_dir / PurePosixPath(parquet_remote_for(entry.remote))` per design D3.
- [x] 2.2 Warn-once per design D3: on absence emit exactly one `print(f"  [!] Staged Parquet '{parquet_key}' not found ...")` naming the key; never raise; corrupt-present Parquet keeps silent CSV fallback (RC-R14 scope).
- [x] 2.3 Import `parquet_remote_for` from `._mirror`.
- [x] 2.4 Origin labels per design D4: Parquet path sets `origin_name = parquet_key`; CSV path replaces the three `local.name` uses (~:558, :561, :602) with `entry.remote`.
- [x] 2.5 **[Gate-review advisory 1]** Restage regression fixture `tests/test_repo_compliance.py:2007` (`test_parquet_and_csv_paths_both_key_by_remote`): move staged Parquet from `stage/x.parquet` to `stage/data/x.parquet` so it matches `remote="data/x.csv"` (:2016) and keeps exercising the Parquet branch after the fix.
  - Deviation note: RC-R05 origin relabeling broke ONE additional existing assertion beyond the design audit (`TestDuplicateRemoteWarning::test_duplicate_remote_warns_once_and_keeps_first` — the dup-COLUMN warning now also names the remote); filter tightened to `"Duplicate remote '...'"`. Intent preserved.

## Phase 3: Scenario tests (spec ↔ test map, all in commit 2)

- [x] 3.1 New class `TestStagedParquetRemoteRelativeLookup` in `tests/test_repo_compliance.py` covering: **S1** nested remote reads own Parquet (dtypes/nullability from Parquet schema); **S2** root+nested same-stem independence (no cross-contamination); **S4** missing Parquet → exactly one `[!]` via capsys + CSV fallback columns; **S5** present → no `[!]` (capsys silence); **S10** origins `survey.parquet` vs `data/survey.parquet`.
- [x] 3.2 New nested-remote parity test in `tests/test_prepare.py` (near :116 fixtures): **S3** run `prepare` on cfg with remote `data/PROV/train.csv`, then `build_schema_report_with_rows(cfg, staging_dir=output_dir)` matches Parquet dtypes + metadata row count.
- [x] 3.3 Backslash e2e half of **S6** in `tests/test_prepare.py`: TOML remote `data\a\train.csv` round-trips — writer and reader derive the same `/`-key, Parquet branch taken.
- [x] 3.4 Extend `TestColumnOriginAttribution` in `tests/test_repo_compliance.py`: **S8** multi-file origins ∈ remotes (not basenames); **S9** duplicate-name first-wins with remotes differing from basenames (extend existing :1842 test).

## Phase 4: Reconciliation, gates, follow-ups

- [x] 4.1 **[Gate-review advisory 2]** Update `proposal.md` success criterion "(6 call sites)" → 7 adoption sites (6 duplication sites + 1 flat lookup), citing design's inventory correction.
- [x] 4.2 **[Gate-review advisory 3]** Add note for archive phase: pin RC-R14 "eligible entry" definition (CSV remote, not `recursive`, not `upload_as_csv`) when syncing main specs.
- [x] 4.3 **[Gate-review advisory 4]** Record follow-up issue suggestion (do NOT implement): case-insensitive filesystems collide on case-only-differing remotes (`A.csv`/`a.csv` derive distinct keys, same path).
- [x] 4.4 Full gate both batches: `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/`. Commit 2: `fix(compliance): resolve staged parquets by remote-relative key with fallback warning`.

## Archive-phase notes (advisory 3)

When syncing the delta into `openspec/specs/repo-compliance/spec.md`, pin the
RC-R14 "eligible entry" definition verbatim so the warning contract stays
scoped: an entry is eligible for staged-Parquet reading (and thus for the
missing-Parquet `[!]` warning) iff it declares a CSV remote
(`remote.lower().endswith(".csv")`), is NOT `recursive=true`, is NOT
`upload_as_csv=true`, and has `include_in_schema` respected for schema
collection. Entries outside this set never warn and never consult
`staging_dir`.

## Follow-up suggestions (advisory 4 — do NOT implement here)

- **Case-insensitive filesystem collision**: remotes differing only by case
  (`A.csv` vs `a.csv`) derive distinct keys from `parquet_remote_for`
  (case-preserving) but resolve to the SAME file on case-insensitive
  filesystems — one staged Parquet would be read for both entries. The
  warn-once set also treats them as distinct. Suggested fix direction:
  detect case-insensitive collisions among eligible remotes at report time
  and emit a deterministic `[!]`. Track as a follow-up issue after #60 ships.

## Test Plan (spec coverage)

| Scenario | Requirement | Test location |
|---|---|---|
| S1 nested reads own Parquet | RC-R13 | 3.1 class |
| S2 same-stem independence | RC-R13 | 3.1 class |
| S3 prepare→report parity | RC-R13 | 3.2 |
| S4 missing warns once + falls back | RC-R14 | 3.1 class |
| S5 present silent | RC-R14 | 3.1 class |
| S6 backslash round-trip | RC-R15 | 1.5 (unit) + 3.3 (e2e) |
| S7 normalization idempotent | RC-R15 | 1.5 |
| S8 multi-file origins | RC-R05 | 3.4 |
| S9 dup name first-wins | RC-R05 | 3.4 (extends existing) |
| S10 nested Parquet origins | RC-R05 | 3.1 class |
