# Design: Key exact row counts by remote path (row-count-remote-keying)

## Technical Approach

Producer-side re-keying inside `_build_schema_report_impl` (`src/sofer/repo_compliance.py`):
both row-count writes switch to verbatim `entry.remote`; a new duplicate-remote
warning guards the resulting keying invariant; fallback behavior (RC-R12) is
already spec-conformant and gets documentation-only changes. Sole consumer
(`build_dataset_card`, repo_compliance.py:793) sums values only — verified zero
key-reading consumers (`prepare.py:714` passes the dict straight through).

## Architecture Decisions

| # | Decision | Options | Tradeoff | Chosen |
|---|----------|---------|----------|--------|
| D1 | Row-count key = verbatim `entry.remote` | (a) verbatim remote · (b) lowercased/normalized remote | (a) matches `planned_remotes` / `configs.data_files` rendering exactly (RC-R07 wording "verbatim"); (b) silently rewrites user TOML strings | **(a)** |
| D2 | `ColumnSchema.origin` stays basename-based | (a) untouched · (b) switch to remote | (a) human-readable "File" column preserved; no code joins origin against keys (verified) · (b) breaks display + `_dup_map` messages for no functional gain | **(a)** |
| D3 | Return type of `build_schema_report_with_rows` stays `tuple[list[ColumnSchema], dict[str, int]]` | (a) keep dict, re-document contract · (b) structured records | (a) minimal diff, consumer untouched · (b) consumer rewrite for provenance nobody reads | **(a)** |
| D4 | First-declared entry wins on duplicate remote | (a) plain assignment (last wins) · (b) `setdefault` guard (first wins) | Spec RC-R11 mandates first-declared-wins and matches the existing first-occurrence-wins convention for duplicate columns | **(b)** — both producer sites use `row_counts.setdefault(entry.remote, ...)` |
| D5 | Duplicate detection lives at top of `_build_schema_report_impl` as helper `_warn_duplicate_remotes(cfg)` | (a) impl pre-pass · (b) wrapper-only | Both public wrappers route through the impl; card generation always follows report building (`prepare.py:714`) | **(a)** |

## Data Flow

    cfg.files ──► _warn_duplicate_remotes (new, [!] print, declaration order)
        │
        ▼
    _build_schema_report_impl
        ├─ staged parquet :453  row_counts.setdefault(entry.remote, pf.metadata.num_rows)
        ├─ CSV path      :514  row_counts.setdefault(entry.remote, len(rows))
        └─ ColumnSchema.origin unchanged (local.name / "<stem>.parquet")
        │
        ▼
    build_dataset_card :792-793   num_examples = sum(row_counts.values())
                                  or CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)

Keying detail: the loop's `remote = entry.remote.lower()` (line 417) is used
ONLY for the `.endswith(".csv")` gate — keys use verbatim `entry.remote`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/repo_compliance.py` | Modify | Re-key producers (:453, :514); add `_warn_duplicate_remotes` (~10 lines); update docstrings of `_build_schema_report_impl`, `build_schema_report_with_rows`, `build_dataset_card`; comment on partial-counts undercount (:792) |
| `tests/test_repo_compliance.py` | Modify | Update exact-dict assertions; add same-stem regression, dual-path keying, duplicate-warning, silence, and fallback tests (~80 lines) |
| `openspec/specs/repo-compliance/spec.md` | Modify (archive step) | RC-R07 delta lands at archive time; no code-side spec edit in this PR beyond the change folder |

No changes: `prepare.py`, `model.py`, `config.py` (all knobs already read at
call time via `config.X`).

## Interfaces / Contracts

```python
def _warn_duplicate_remotes(cfg: DatasetConfig) -> None:
    """Emit one [!] warning per remote declared by 2+ [[file]] entries.

    Deterministic: iterates cfg.files in declaration order; warnings are
    emitted in first-declaration order of each duplicated remote. Never raises.
    """
```

Contract change (docstring-level): `row_counts` maps **verbatim remote path**
(`entry.remote`) → EXACT row count; remotes are unique per well-formed dataset;
duplicate declarations keep the FIRST entry's count and emit `[!]`. Keys are
POSIX-style, identical to how `configs.data_files` renders them.

Warning message shape (matches existing style, e.g. line 571):

```
  [!] Duplicate remote 'a/data.csv' declared by multiple [[file]] entries;
      keeping the first entry's row count.
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit — RC-R07 | Same-stem distinct keys | New fixture: `tmp_path/a/data.csv` (30 rows) + `tmp_path/b/data.csv` (40 rows), remotes `a/data.csv` / `b/data.csv` → assert `row_counts == {"a/data.csv": 30, "b/data.csv": 40}` and `num_examples == 70` |
| Unit — RC-R07 | Parquet+CSV both key by remote | Staged parquet entry + `upload_as_csv` entry → both counts keyed by their remotes |
| Unit — RC-R07 | Existing assertions | :1944 `{"d.csv": 5}`, :1964 `{"a.csv": …}`, :2020 `{"w.csv": 3}` stay valid (remote == filename there); :1985 changes `{"p.parquet": 5}` → `{"p.csv": 5}` (remote-keyed). Add clarifying comments that keys are remotes |
| Unit — RC-R11 | Duplicate warns once | Two entries, same remote → capsys asserts exactly one `[!]` naming the remote; build completes; first count kept |
| Unit — RC-R11 | Silence | All-unique remotes → no duplicate warning in output |
| Unit — RC-R12 | Recursive-only fallback | Recursive-only `cfg.files`, schema passed manually, `row_counts=None` → `num_examples == CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)` |
| Unit — RC-R12 | Excluded files fallback | All `include_in_schema=false`, `row_counts={}` → fallback product |

Run `uv run pytest tests/ -q` after each batch (422-test baseline).

## Migration / Rollout

None. Single PR on `fix/row-count-remote-keying`; revert restores prior keying
and assertions. The staged-parquet flat-stem lookup bug (:435) is explicitly
out of scope — separate follow-up issue so verification confusion is tracked.

Known residual (documented, not fixed): mixed schema/non-schema datasets sum
partial counts silently (undercount) when *some* files yield counts — RC-R12
fallback applies only when NO file yields one.

## Open Questions

- None blocking. Case-sensitivity note: duplicate detection compares verbatim
  remotes (consistent with D1 keying); `A/Data.csv` vs `a/data.csv` are distinct
  keys by design.
