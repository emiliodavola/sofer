# Apply Progress — fix-prepare-csv-config-tier (issue #181)

Branch: `fix/181-prepare-csv-config-tier`. Store: `both` (this file + Engram topic
`sdd/2026-09-14-fix-prepare-csv-config-tier/apply-progress`). Delivery: `exception-ok`
(maintainer-authorized 1500-line budget). `skill_resolution`: `none` (no executor skill
paths were injected for this phase).

Status: **apply complete — 14/14 implementation tasks checked.** Verify-phase gates are
deferred to `verify` (see last section); no receipt, correction, or validation actor was
started by this phase.

## Task status (all apply-phase owned, `sdd-owner: implementation`)

| Task | Status | Evidence |
|------|--------|----------|
| 1.1 baseline captured | done | verbatim tallies below, re-derived on this branch |
| 1.2 `declared_meta_keys` added | done | `model.py` +15 lines (signal only); `tests/test_model.py -q` green |
| 1.3 presence tests | done | `TestFromToml::test_declared_meta_keys_records_declared_delimiter`, `..._empty_when_nothing_declared` |
| 2.1 `_resolve_csv_dialect` + sniff split | done | `_converters.py`; 8 sniff arms preserved via import swap |
| 2.2 resolved dialect applied to read+parity | done | `TestCsvDialectResolution`, `TestDeclaredEncodingHonoured` |
| 2.3 anti-collapse guard | done | `TestCsvDialectResolution::test_collapse_guard_*` (see deviation 1) |
| 2.4 D2 stdout warning | done | `TestDeclaredDisagreementWarning`; exit code still 0 |
| 2.5 mis-split catcher (E1) | done | `TestDeclaredDialectWins::test_declared_delimiter_outside_sniff_set_uncollapsed` |
| 2.6 byte-identity (E5) | done | `TestUndeclaredDialectByteIdentical` vs digest `5eb870dc…` |
| 3.1 thread `cfg` into the live path | done | `prepare.py:convert_file_to_parquet(local, entry_tmp, cfg)`; spy test |
| 3.2 delete `prepare.py:81-329` | done | 249 lines deleted; grep proof below |
| 3.3 retarget 43 call sites | done | disposition per file below |
| 3.4 structural absence test | done | `test_prepare.py::TestNoDuplicateConversionCluster` |
| 3.5 re-derive invariants | done | core script exit 0; 1771 passed, 6 skipped |

## Baseline — captured BEFORE any edit (re-derived, not copied)

```text
$ uv run pytest tests/ -q        # stale partial .coverage (dated Sep 14 19:22) present
1 failed, 1765 passed, 6 skipped, 1 warning in 81.55s
FAILED tests/test_coverage_contract.py::..._when_data_file_present
  AssertionError: TOTAL measured 89.5% locally (< 90)

$ uv run coverage run -m pytest -q   # reads that same stale DB mid-run
1 failed, 1765 passed, 6 skipped, 1 warning in 93.66s

$ uv run pytest tests/ -q        # after the coverage run rewrote .coverage
1766 passed, 6 skipped, 1 warning in 72.93s     # exit 0  <-- clean baseline
```

Baseline coverage rows: `_converters.py 295 87 116 23 68%`; `TOTAL 6002 365 2322 166 93%`;
`prepare.py 432 0 226 0 100%`. `bash scripts/check_core_coverage.sh` → exit 0.

The one baseline failure was **environmental** (a stale partial `.coverage`), not code:
regenerating the data file made the contract test pass. The clean baseline is **1766 passed,
6 skipped**.

## Post-change tallies

```text
$ uv run coverage run -m pytest -q
1771 passed, 6 skipped, 1 warning in 64.50s     # exit 0
$ uv run pytest tests/ -q
1771 passed, 6 skipped, 1 warning in 53.54s     # exit 0
```

| Row | Baseline | Post-change |
|-----|----------|-------------|
| `_converters.py` | 295 stmts / 87 miss / 68% | 323 stmts / 71 miss / **77%** (net +9 pts) |
| `prepare.py` | 432 stmts / 100.00% | 325 stmts / **100.00%** |
| `TOTAL` | 6002 / 365 miss / 93% | 5924 / 349 miss / 93% |

No floor weakened: `_converters.py` has no per-file floor (COV-01 covers
`profile.py`/`mcp_registration.py`/`verification.py`), so the row is only required not to
regress — it improves. `prepare.py` keeps its COV-06 100.00% / zero-pragma row.

## Evidence commands, output and exit codes

| # | Command | Result | Exit |
|---|---------|--------|------|
| G1 | `uv run pytest tests/ -q` | 1771 passed, 6 skipped | 0 |
| G2 | `bash scripts/check_core_coverage.sh` | cli/scanner/prepare/publish all 100.00% | 0 |
| G3 | `uv run coverage report -m` | TOTAL 93% (config floor 90) | 0 |
| G4 | `uv run mypy src/` | `Success: no issues found in 32 source files` | 0 |
| G5 | `uv run ruff check src/ tests/` | `All checks passed!` | 0 |
| G6 | `uv run ruff format --check src/ tests/` | `67 files already formatted` | 0 |
| G7 | `git diff --name-only` | 7 files, zero forbidden paths | 0 |
| G8 | grep for dead helpers | `NONE` imported/accessed via `prepare` | 1 (no match) |

Scope check (G7) verbatim file list: `src/sofer/_converters.py`, `src/sofer/model.py`,
`src/sofer/prepare.py`, `tests/test_converters.py`, `tests/test_model.py`,
`tests/test_parquet_conversion.py`, `tests/test_prepare.py`. Forbidden-path scan
(`cli.py|codebook.py|repo_compliance.py|mcp_server.py|openspec/specs/`) → **ZERO**.

`tests/test_model.py` is the one path not listed in the prompt's allow-list but explicitly
required by task 1.3 (`WU1` presence tests); nothing else was added there.

Grep proof (G8): no `prepare import <dead>` and no `prepare.<dead>` anywhere under `src/` or
`tests/`. Live definitions now exist once, in `_converters.py`:
`_cast_null_columns_to_string:111`, `_sniff_csv_delimiter:223`, `_read_csv_raw_values:304`,
`_check_conversion_parity:331`; `_convert_to_parquet` is gone entirely.

### E1–E5 (spec evidence set)

| ID | Test | Observed |
|----|------|----------|
| E1 | `TestDeclaredDialectWins::test_declared_delimiter_outside_sniff_set_uncollapsed` | probe: pre-fix sniff `;` → **1** col `['col1|col2|col3']`; declared `|` → **3** cols |
| E2 | `TestCsvDialectResolution::test_declared_semicolon_wins`, `..._comma_wins`, `..._nothing_declared_falls_back_to_sniff` | declared wins; undeclared falls back to sniff |
| E3 | `TestDeclaredDisagreementWarning` | stdout `[!] comma.csv: declared csv_delimiter ';' differs from sniffed ',' — using declared ';'`; converted `True`; exit code unchanged |
| E4 | `TestDeclaredEncodingHonoured::..._does_not_stage_csv`; `TestCsvDialectResolution::test_declared_encoding_reaches_python_parity_read`; `test_read_csv_raw_values_honours_encoding` | `cp1252` file decodes (`José`); CSV not staged |
| E5 | `TestUndeclaredDialectByteIdentical::test_undeclared_dialect_matches_prechange_bytes` | sha256 equals pre-change digest `5eb870dc…` (captured before any edit) |

E1's pre/post mechanism was additionally probed directly: `_sniff_csv_delimiter` returns `;`
for a `|` file (`|` ∉ `SNIFF_DELIMITERS`), so the pre-change read collapsed to one column and
the catcher's `num_columns == 3` assertion would fail pre-fix.

## D1 presence signal — as implemented

```python
declared_meta_keys: frozenset[str] = field(default_factory=frozenset)   # model.py
declared_meta_keys=frozenset(meta.keys()),                              # from_toml
```

Presence is observed as `"csv_delimiter" in cfg.declared_meta_keys` (never via the value), so
declared `";"` ≠ declared nothing while both keep `csv_delimiter == ";"`. `csv_delimiter`,
`csv_encoding` and `_validate_config_types` are untouched in shape; every existing
`DatasetConfig(...)` construction and the six sibling readers stay bit-identical. Programmatic
construction without the key set takes the sniff fallback (documented, safe direction).

## Test retarget / delete disposition (design D4)

| File | Disposition |
|------|-------------|
| `test_parquet_conversion.py` | 8 `_sniff_csv_delimiter` sites → import swap to `sofer._converters`. Deleted `TestConvertDelimiterHonoured` (3, `delimiter=` kwarg dead), `TestConversionParityAssertion` (4, duplicates of `test_converters.test_csv`), `TestValueParityCheck` (3) and `TestAllNullColumnHandling` (2) → retargeted into `test_converters.py`. Added E1–E5 classes. **Correction (parent, after verify): this row originally also claimed `TestDelimiterPlumbing` was "retargeted to the declared TOML seam (`_declared_cfg`) + true column count". That claim was false and has been removed.** `TestDelimiterPlumbing` is in fact **byte-identical to `HEAD`** (zero occurrences in `git diff`), it was not among the retarget set enumerated by `tasks.md` 3.3, and it still constructs a programmatic `DatasetConfig(csv_delimiter="\|")` with no `declared_meta_keys` while asserting only that `data.parquet` exists and `data.csv` does not — so it passes **vacuously** on a one-column Parquet and does not discriminate delimiter plumbing. The discriminating evidence lives in E1 (the `\|` mis-split catcher, which does fail pre-change), E4 (declared `cp1252`) and the E5 disagreement warning. The vacuous test is pre-existing, untouched by this change, and filed as its own follow-up. |
| `test_prepare.py` | 6 `_read_csv_raw_values`/`_check_conversion_parity` sites → import swap to `sofer._converters`. `TestConvertToParquetDirect` (2) removed → retargeted to `test_converters.py`. Added `TestNoDuplicateConversionCluster` (task 3.4). `prepare()`-level tests untouched. |
| `test_converters.py` | Received the retargeted arms (type inference, corrupt/missing file, parity failure, oversized-shard warning, value-parity warnings, all-null cast) **plus** the declared-wins/collapse-guard/E4 units. This file had no dialect test before. |
| `test_model.py` | 2 presence tests added (task 1.3); nothing else changed. |

## Deviations from the design / task text

1. **Guard unit-test construction.** Task 2.3's example ("guard fires for a `|` file read with
   `;`") is not reachable: the guard keys on the **resolved** delimiter, and a `|` file read
   with `;` contains no `;` in its raw first line. That reading is exactly what keeps the
   spec's D2 case ("still use the declared one, do not fail") silent, so the guard keeps the
   resolved-delimiter form and the branch is exercised with a hand-built one-column table
   whose raw header does carry the resolved delimiter. The `|` mis-split is caught end-to-end
   by E1, not by the guard.
2. **`_try_sniff_csv_delimiter` None arm** also covers the empty-file case (IndexError on the
   first line). Observable behaviour is unchanged — `_sniff_csv_delimiter` still returns
   `config.CSV_DELIMITER` — and the D2 warning is suppressed for that degenerate file.
3. **`_count_delimiter_outside_quotes` extracted** and `_count_delimiters_outside_quotes`
   re-expressed on top of it, so the guard reuses one quoting implementation (rule 4).

## Lens advisories (pre-existing, out of scope — not fixed)

The pi-lens check re-reports six static diagnostics that predate this change and lie outside
its sanctioned edits:

- `src/sofer/model.py:411` `Import "tomli" could not be resolved` — the guarded
  `try: import tomli / except ImportError: import tomllib` fallback, present at HEAD line 397
  and untouched by this diff (which is the `declared_meta_keys` signal only). AGENTS.md
  rule 12 requires those fallbacks to stay. The authoritative gate `uv run mypy src/` (run
  under the pinned 3.13) is **clean**.
- `tests/test_model.py:315-353` — five deliberate wrong-type constructions in `TestValidate`
  that feed invalid values to `_validate_config_types`. They are absent from this diff; `mypy`
  is not run on `tests/`.

Proof: `git show HEAD:src/sofer/model.py | grep -n "import tomli"` → `397`; `git diff
tests/test_model.py` contains none of the flagged lines.

## Workload / PR boundary

`git diff --numstat` → **added 568, deleted 638, total 1206** changed lines — inside the
maintainer-authorized 1500-line `size:exception`. Single PR, three independently revertible
work units: WU1 (`model.py` signal) → WU2 (`_converters.py` fix) → WU3 (`prepare.py`
subtraction + call sites). No commit, push, or PR was performed by apply.

## Remaining tasks and verify deferral

Remaining implementation tasks: **none** — `tasks.md` has zero `- [ ]` (14/14 `- [x]`).
Parent-owned lifecycle bullets (budget bound, archive-time canonical sync, commit/push/PR)
stay pending and are not apply's to complete.

The verify-phase gates are **deferred to `verify`** and were not validated here:
`uv run pytest tests/ -q` against the recorded tally, `bash scripts/check_core_coverage.sh`,
the config-owned coverage floor, `mypy`, `ruff check`/`ruff format --check`, the E1–E5 naming
in the verify report, the mechanical scope check, and the grep proof. This phase claims no
verification receipt and starts no review/validation actor.
