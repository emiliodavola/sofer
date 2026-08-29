# Design: fix-quality-encoding-xlsx

## Technical Approach

Suffix allowlist gates all P0 checks to CSV/TSV. `TEXT_SUFFIXES` + `is_text_eligible()` in `_formats.py`; `run()` filters before probe/`stream_csv`, helpers add defensive early-returns. `ran_checks` only records eligible files — binary-only datasets yield empty results and `publish` is not blocked. No new `[tool.sofer]` key, dependency, or CLI change. Implements proposal Approach 1 and delta spec scope + gated dispatch + UTF-8-only.

## Architecture Decisions

### Decision: Registry — where TEXT_SUFFIXES lives

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `_formats.py`: `TEXT_SUFFIXES + is_text_eligible()` | One module per concern; `SUPPORTED_FORMATS` already here; trivial import | **Chosen** |
| `quality.py` inline `{\".csv\",\".tsv\"}` | Smallest diff | Rejected — duplicates format knowledge (AGENTS.md §10, §4) |
| `config.py` `[tool.sofer]` key | User-configurable | Rejected — invariant, not preference |

**Rationale**: Single source of truth; no hardcoded literals in function bodies.

### Decision: Guard placement

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `run()` loop: `if not is_text_eligible(resolved): continue` after `exists`/`is_dir` | Single filter before I/O; accumulators stay clean | **Chosen (primary)** |
| Only inside helpers | `run()` still dispatches binary files; wasted work | Rejected alone |
| Both: `run()` filter + helper early-return | Direct calls safe; `ran_checks` cannot be polluted | **Chosen (defense in depth)** |

**Rationale**: Primary gate prevents I/O on binaries; helper guards cover direct-call spec scenario and protect `ran_checks`.

### Decision: No new `[tool.sofer]` key

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `quality_eligible_suffixes` in `_DEFAULTS` | Future `.psv` flexibility | Rejected — YAGNI; correctness bug, not preference |
| `TEXT_SUFFIXES` frozenset in code | Invariant (`xlsx is not CSV`); `prepare.py` uses same pattern | **Chosen** |

**Rationale**: Zero README/pyproject churn; future formats extend the frozenset.

### Decision: Why not magic-byte / NUL sniffing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Suffix `path.suffix.lower()` | O(1), deterministic, no I/O; handles `.parquet`/`.jsonl` | **Chosen** |
| Magic-byte (`PK\x03\x04`, `\x00`) | Handles mislabeled ext but heuristic; 8 KB UTF-8 collision; double-read | Rejected for P0 |
| Combined | Strongest but over-engineered | Deferred — mislabeled `.csv` with ZIP bytes **should** fail |

## Data Flow

```
DatasetConfig.files ──→ QualityValidator.run()
                             │ resolve → exists/is_dir? ─no→ skip
                             │ is_text_eligible? ─no→ skip (no I/O, no ran_checks)
                             │ yes
                             ├─→ _check_encoding_validation (8 KB probe, utf-8-sig→utf-8)
                             └─→ _process_file → stream_csv → _distribute_row → accumulators
                                          └─ ValueError → mislabeled .csv safety net
                             │
                             ▼
                post-scan checks (corrupt_records, cross_file_types…)
                             │ (accumulators contain only eligible files)
                             ▼
                ValidationReport {quality_results, ran_checks} → print_summary / publish gate
```

`Path.suffix.lower()` handles `.XLSX→.xlsx`, `README→""`, `.csv.gz→.gz` (skip).

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_formats.py` | Modify | Add `TEXT_SUFFIXES: frozenset[str]` + `is_text_eligible(Path)->bool`; update module docstring |
| `src/sofer/quality.py` | Modify | Import guard; filter `run()` loop; early-return in `_check_encoding_validation`/`_process_file`; fix `ran_checks`; update docstrings |
| `src/sofer/_csv_reader.py` | Referenced | No change; `ENCODING_FALLBACKS=["utf-8-sig","utf-8"]`; `ValueError` stays as safety net |
| `src/sofer/prepare.py` | Referenced | Gating pattern source; no change |
| `src/sofer/config.py` | Referenced | No new key (deliberate) |
| `tests/test_quality.py` | Modify | Binary skip, TSV eligible, case-insensitive, no-extension, ran_checks cases |
| `openspec/specs/data-quality/spec.md` | Delta exists | No design-phase change |

No duplication: `TEXT_SUFFIXES` distinct from `SUPPORTED_FORMATS`. CLI/README: none; docstring updates required.

## Interfaces / Contracts

```python
# src/sofer/_formats.py
from pathlib import Path
TEXT_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv"})
def is_text_eligible(path: Path) -> bool: ...  # path.suffix.lower() in TEXT_SUFFIXES

# src/sofer/quality.py guard contract
# run():  if not is_text_eligible(resolved): continue  # after exists/is_dir
# helpers: if not is_text_eligible(resolved): return  # no result, no ran_checks
```

`QUALITY_CHECK_NAMES` unchanged; skipped files affect neither `passed` nor `failed`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `is_text_eligible` | `a.XLSX`/`README`/`a.csv.gz` → false; `a.csv`/`a.tsv` → true |
| Unit | Helper guards | Direct call with `.xlsx`/`.parquet` → no result, no `ran_checks` |
| Unit | Binary skipped | `run()` with `.xlsx`/`.parquet`/`.jsonl` → `[]` results, `{}` ran_checks |
| Unit | TSV eligible | `.tsv` short row → `corrupt_records: fail` |
| Unit | Binary-only no cross-file | Two identical `.xlsx` → no duplicates/cross_file_types |
| Unit | `run()` filters before accumulators | `a.csv+b.xlsx+c.tsv` → only `a/c` reach probe/stream |
| Unit | UTF-8-only | `latin-1` `José` → fail; UTF-8 → pass |
| Unit | Mislabeled `.csv` | `.csv` with `PK` bytes → `ValueError` → fail |
| Unit | `ran_checks` | Binary-only → empty; mixed → only `data.csv` |
| Regression | Existing P0 | Re-run `TestCheck*` on `.csv` unchanged |

Reuse `_make_csv`/`_make_csv_cfg`/`_run_quality`; binary fixtures via `write_bytes(b"PK\x03\x04...")`.

## Migration / Rollout

No migration. Revert single commit to restore prior behavior. No flag — correctness gate. Binary-only now `0 failed` (publish unblocked).

## Open Questions

- [ ] None blocking. `.csv.gz` → `.gz` skip is correct for P0; future `Path.suffixes` if compressed CSV needed.
