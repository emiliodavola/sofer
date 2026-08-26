# Design: Fix staged-parquet staging lookup (remote-relative keys)

## Technical Approach

Both handshake ends derive their key from one shared helper, `_mirror.parquet_remote_for(remote)`. The write side (prepare → `copy_to_mirror`) is already compliant; the consumer lookup in `_build_schema_report_impl` flips from flat `{stem}.parquet` to `staging_dir / PurePosixPath(parquet_remote_for(entry.remote))`. Origin labels become remote-relative POSIX paths, and a deterministic `[!]` warning fires when an expected staged Parquet is absent. Answers RC-R13/R14/R15 and the RC-R05 modification.

**Inventory correction**: the proposal lists 6 call sites, but the duplicated expression appears in **7** places — `prepare.py:364` (`_assert_cross_file_schema`) was missed by explore.md's inventory. All 7 are adopted here to satisfy the single-definition success criterion.

## Architecture Decisions

### D1: Helper signature & location

```python
# src/sofer/_mirror.py — public name in private module, next to planned_remotes()
def parquet_remote_for(remote: str) -> str:
    """Return the staged-Parquet remote key for *remote* ..."""
    posix_remote = remote.replace("\\", "/")          # RC-R15 normalization
    return str(PurePosixPath(posix_remote).with_suffix(".parquet"))
```

| Option | Tradeoff | Decision |
|---|---|---|
| Helper in `_mirror.py`, public name | Module already owns remote vocabulary (`planned_remotes`, `copy_to_mirror`) | ✅ Chosen |
| Helper in `config.py`/new module | Remote-path logic scattered; new module for one function | ❌ |
| Accept `Path \| str` | Remotes are always `str` (`model.py:367`); union invites misuse | ❌ — `str` only |

Semantics: input is the **verbatim** `entry.remote` (case preserved — gating via `.lower()` stays at each site, matching today's behavior); `\` → `/` first so `PurePosixPath` sees real separators (fixes the writer/reader divergence for TOML backslash remotes); idempotent because `replace` is idempotent and re-normalizing a normalized remote is a no-op. Does NOT lowercase or strip suffixes beyond `.with_suffix`.

### D2: Call-site adoption (behavior identical except RC-R15 backslash cases)

| Site | Current | New |
|---|---|---|
| `_mirror.py:82` (`planned_remotes`) | inline expression | `planned.append(parquet_remote_for(entry.remote))` |
| `prepare.py:364` (`_assert_cross_file_schema`) | inline expression | `parquet_remote = parquet_remote_for(entry.remote)` |
| `prepare.py:576` (`_check_local_overwrite`) | `output_dir / PurePosixPath(...).with_suffix(".parquet")` | `output_dir / PurePosixPath(parquet_remote_for(entry.remote))` |
| `prepare.py:709` (staging step 5) | inline expression on `original_remote` | `parquet_remote_for(original_remote)` |
| `publish.py:233` (`_repo_diff_summary`) | inline expression | `parquet_remote_for(entry.remote)` |
| `publish.py:479` (`_copy_planned_files`) | inline expression | `parquet_remote_for(entry.remote)` |
| `repo_compliance.py:459-471` (lookup) | flat `{stem}.parquet` | see D3 |

`WindowsPath / PurePosixPath` joins all parts (already proven at `prepare.py:576`, `publish.py:475`), so no `joinpath(*parts)` gymnastics needed.

### D3: Lookup rewrite + warn-once

In `_build_schema_report_impl`, replace `entry_stem` usage (:459 deleted):

```python
_warned_missing: set[str] = set()   # init before loop — warn once per unique key
...
if staging_dir is not None and not entry.upload_as_csv:
    parquet_key = parquet_remote_for(entry.remote)
    candidate = staging_dir / PurePosixPath(parquet_key)
    if candidate.exists():
        use_parquet, parquet_path, origin_name = True, candidate, parquet_key
    elif parquet_key not in _warned_missing:
        _warned_missing.add(parquet_key)
        print(f"  [!] Staged Parquet '{parquet_key}' not found in staging "
              f"directory; falling back to CSV inference.")
```

Warn point: existence-check failure only. A **present-but-corrupt** Parquet still falls back silently (unchanged; RC-R14 scopes the warning to absence). Determinism: declaration-order iteration + per-run set ⇒ same input → exactly one message per key, never raises — same convention as `_warn_duplicate_remotes` (#59). CSV fallback (delimiter/encoding from `cfg`) untouched.

### D4: Origin label plumbing

Produced only inside `_build_schema_report_impl`: Parquet path sets `origin_name = parquet_key`; CSV path replaces the three `local.name` uses (:558, :561, :602) with `entry.remote` (RC-R05 MODIFIED). Consumers (card Data Fields column, duplicate-column warnings) render whatever string arrives — no code change. **Test audit result**: every existing fixture uses root remotes where basename == remote (`test_repo_compliance.py:1816`, `:1833`, `:1860` all still hold), so no existing assertion breaks; the new stdout warning breaks no existing test (none assert silence on those paths). Tasks phase must re-verify with `uv run pytest tests/ -q`.

## Data Flow

```
TOML remote ──► parquet_remote_for() ──► prepare.copy_to_mirror  (writer: data/PROV/train.parquet)
                    │                                        │
                    └─► repo_compliance lookup ──► staging_dir / PurePosixPath(key) ──► exists?
                                                │                  │ no (+[!] once)
                                                ▼                  ▼
                                        Parquet branch      CSV fallback (origin=entry.remote)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | Modify | Add `parquet_remote_for()`; adopt at :82 |
| `src/sofer/repo_compliance.py` | Modify | Lookup rewrite (D3), origin labels (D4), import helper |
| `src/sofer/prepare.py` | Modify | Adopt helper at :364, :576, :709 |
| `src/sofer/publish.py` | Modify | Adopt helper at :233, :479 |
| `tests/test_mirror.py` | Modify | Helper unit tests |
| `tests/test_repo_compliance.py` | Modify | Scenarios S1-S2, S4-S5, S8-S10 classes |
| `tests/test_prepare.py` | Modify | Scenarios S3, S6 (nested-remote scaffolding at :116-117) |

## Interfaces / Contracts

`_mirror.parquet_remote_for(remote: str) -> str` — pure, total (never raises on valid str), idempotent, case-preserving, backslash-normalizing. Single source of the remote→parquet-key derivation for writers and readers.

## Testing Strategy

| Spec scenario | Test | Placement |
|---|---|---|
| S1 nested remote reads own Parquet | stage parquet at `staging/data/PROV/train.parquet`; assert dtype/nullable from Parquet schema | `test_repo_compliance.py::TestStagedParquetRemoteRelativeLookup` (new) |
| S2 same-stem root+nested independence | both staged, different schemas; assert each entry's columns/dtypes come from its own file | same class |
| S3 prepare→report parity | run `prepare` on nested-remote cfg (`data/PROV/train.csv`); `build_schema_report_with_rows(cfg, staging_dir=output_dir)` matches Parquet dtypes + metadata rows | `test_prepare.py` (new, near :116 fixtures) |
| S4 missing warns once + falls back | empty staging dir; capsys: exactly one `[!]` naming `train.parquet` key; CSV columns returned | S1 class |
| S5 present stays silent | all staged; capsys: no `[!]` | S1 class |
| S6 backslash round-trip | remote `data\a\train.csv` through `parquet_remote_for` on both sides → same `/`-key; Parquet branch taken | unit half in `test_mirror.py`, e2e half in `test_prepare.py` |
| S7 normalization idempotent | `parquet_remote_for("a/b.csv") == parquet_remote_for(parquet_remote_for("a/b.csv"))` and `"\\"` variants | `test_mirror.py` |
| S8 multi-file origins | two CSVs, distinct remotes; every ColumnSchema.origin ∈ {remote₁, remote₂} | extend `TestColumnOriginAttribution` |
| S9 dup name keeps first origin | exists (:1842) — extend assertion to remotes differing from basenames | same class |
| S10 nested Parquet origins distinguish | remotes `survey.csv` / `data/survey.csv` → origins `survey.parquet` / `data/survey.parquet` | S1 class |

Plus: full suite green + `uv run mypy src/` clean under 3.13 (`from __future__ import annotations` already present in all touched modules; helper needs no TYPE_CHECKING imports).

## Migration / Rollout

No migration (staging dirs ephemeral; `output_dir` user-regenerated). Single PR on `fix/staged-parquet-stem-collision` → `dev`, two work-unit commits:

1. `refactor(mirror): extract parquet_remote_for and adopt at all derivation sites` — pure refactor + helper unit tests (S6-unit, S7). Independently revertable; suite green.
2. `fix(compliance): resolve staged parquets by remote-relative key with fallback warning` — lookup flip, origins, warning, scenario tests S1-S6-e2e, S8-S10. Delta spec ships in this change (verify depends on it).

Rollback boundary: revert commit 2 restores old contract (old flat-lookup spec semantics); commit 1 is behavior-preserving.

## Open Questions

None blocking. One deliberate non-goal recorded: corrupt-Parquet read failures stay silent-fallback (out of RC-R14 scope).
