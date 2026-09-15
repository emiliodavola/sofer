# Tasks — fix-prepare-csv-config-tier (issue #181)

Branch `fix/181-prepare-csv-config-tier` (`.git/HEAD` → `ref: refs/heads/fix/181-prepare-csv-config-tier`).
Store: **hybrid** — this file + Engram topic `sdd/2026-09-14-fix-prepare-csv-config-tier/tasks`.
Inputs: `proposal.md`; two spec deltas (**PC-U01** MODIFIED + **PC-U06** ADDED in
`specs/parquet-conversion/spec.md`, **TC-04** MODIFIED in `specs/tool-config/spec.md`); `design.md` — D1–D6 are
the plan of record (D1 presence signalled by a **declared-keys set**, never `str | None`; D3 one resolution point
`_resolve_csv_dialect(local, cfg)` in `_converters.py`; D5 precedence normative in PC-U01 with TC-04 pointing at
it; D6 work units WU1 → WU2 → WU3). Defect statement is the corrected one: the configured encoding is **never
consulted** (with the default `utf8` an invalid byte yields a **binary** value such as `b'\xf1'` rather than
necessarily failing), and a delimiter outside `SNIFF_DELIMITERS` collapses the file to **one column** because the
parity read agrees vacuously.
**D7 is CLOSED — resolved by probe, not carried as risk:** `pyarrow 25.0.0` accepts `encoding='utf-8-sig'` (OK,
readback `'utf-8-sig'`), `'utf8'` (OK), `'cp1252'` (OK), `'latin-1'` (OK). Reading **R1** stands: pass the
declared name verbatim — no alias map, no plan-B fallback, no probe task.
Delivery: **`exception-ok`** — the maintainer explicitly authorized up to **1500 changed lines** (review budget
1500) so the 249-line `src/sofer/prepare.py:81-329` dead cluster rides with the fix. Recorded authorization, not
inferred.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~950–1250 (249 deletions in `prepare.py`, 43 retargeted/removed test sites, ~150 impl lines, new tests) |
| 400-line budget risk | High |
| Chained PRs recommended | No — the maintainer authorized the `size:exception` (1500-line budget) |
| Suggested split | Single PR, three reviewable internal commits: WU1 (presence signal) → WU2 (the fix) → WU3 (subtraction + call sites) |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High
```

## Suggested Work Units

| Unit | Scope | Boundaries (start → finish · verify · rollback) |
|------|-------|------------------------------------------------|
| WU1 | `model.py` presence signal + `from_toml` tests; **no behaviour change** | Start: baseline captured → Finish: `declared_meta_keys` populated · Verify: `tests/test_model.py` green, all 244 `DatasetConfig(` sites untouched · Rollback: drop the field (no behaviour delta) |
| WU2 | `_converters.py` resolution + encoding into read **and** parity + warning + collapse guard (+ its own new tests) — the **fix**; WU2 stands alone and green because the dead `prepare.py` copies still import cleanly | Start: `_resolve_csv_dialect` added → Finish: E2–E5 + catcher pass · Verify: `tests/test_converters.py` + `tests/test_parquet_conversion.py` green · Rollback: revert WU2 alone → conversion returns to tool-wide sniffing |
| WU3 | Delete `prepare.py:81-329`, pass `cfg` at `:757`, dispose all 43 call sites, spy/absence tests — **pure subtraction** in the reviewer's view | Start: `cfg` threaded → Finish: legacy symbols absent · Verify: core-coverage script exit 0, full suite green · Rollback: `git revert` restores dead code only (no behaviour change) |

## Apply Tasks

### WU1 — presence signal (`model.py`; no behaviour change)

- [x] 1.1 Capture the pre-change baseline **before touching any file**: `uv run pytest tests/ -q`, then `uv run coverage run -m pytest` + `uv run coverage report -m`; record the pass/skip tally, the TOTAL row and the `_converters.py` row. <!-- sdd-owner: implementation -->
  - Evidence: the recorded tally + rows, **re-derived on this branch** — never reuse a tally quoted in the artifacts or in AGENTS.md.
- [x] 1.2 Add `declared_meta_keys: frozenset[str] = field(default_factory=frozenset)` to `DatasetConfig` (`src/sofer/model.py:321` region) and populate it in `from_toml` (`:350`–`:531`) as `frozenset(meta.keys())`; leave `csv_delimiter = ";"` / `csv_encoding = "utf-8-sig"` and `_validate_config_types` (`:646-649`) untouched in shape. <!-- sdd-owner: implementation -->
  - Evidence: `uv run pytest tests/test_model.py -q` green; the 244 existing `DatasetConfig(` constructions and the six sibling readers stay bit-identical.
- [x] 1.3 Add the presence tests to `tests/test_model.py::TestFromToml`: declaring `csv_delimiter = ";"` gives membership `True`, declaring nothing gives the same value `";"` with membership `False` (declared `;` ≠ declared nothing). <!-- sdd-owner: implementation -->
  - Evidence: the two new tests assert membership independently of the value, and pass.

### WU2 — the fix (`_converters.py`)

- [x] 2.1 Add `_resolve_csv_dialect(local, cfg) -> tuple[str, str]` to `src/sofer/_converters.py` (declared key present ⇒ `cfg` value, else `_sniff_csv_delimiter(local, config.CSV_ENCODING)` / `config.CSV_ENCODING`); add the optional `encoding` parameter to `_sniff_csv_delimiter` and `_try_sniff_csv_delimiter(...) -> str | None` (`None` only when the file cannot be decoded) for the D2 comparison. <!-- sdd-owner: implementation -->
  - Evidence: `tests/test_converters.py::TestConvertFileToParquet` covers both branches, including a declared `;` distinct from "declared nothing"; the eight existing sniff arms are preserved.
- [x] 2.2 Apply the resolved dialect in `_convert_csv_to_parquet` (`:326-345`): `pc.ReadOptions(encoding=resolved_encoding)` passed **only** when `csv_encoding` is declared, and the **same** resolved encoding threaded into `_read_csv_raw_values` and `_check_conversion_parity` (otherwise parity compares without decoding and the fix collapses back to "stage the original"). <!-- sdd-owner: implementation -->
  - Evidence: unit test where the declared encoding parses cleanly while the tool-wide read yields a binary value (e.g. `b'\xf1'`) — accurate framing, not "it fails".
- [x] 2.3 Add the anti-collapse guard in `_check_conversion_parity`: `table.num_columns == 1` **and** the raw first line containing the resolved delimiter outside quotes ⇒ parity fails; delimiter count `0` ⇒ guard silent. <!-- sdd-owner: implementation -->
  - Evidence: unit test that the guard fires for a `|` file read with `;` and stays silent on the D2 disagreement case (spec: "still use the declared one, do not fail").
- [x] 2.4 Emit the D2 warning on **stdout** (`print`, matching `_converters.py:330, :340, :589`) naming **both** values, only when a delimiter is declared, the baseline sniff decodes, and the sniffed delimiter differs. <!-- sdd-owner: implementation -->
  - Evidence: captured stdout text contains both values; the exit code assertion still expects `0` (`prepare.py:936`), i.e. non-blocking.
- [x] 2.5 Add the mis-split catcher to `tests/test_parquet_conversion.py`: a dataset declaring `csv_delimiter = "|"` (`|` ∉ `SNIFF_DELIMITERS`) converts end-to-end with the **true** column count and an uncollapsed header. <!-- sdd-owner: implementation -->
  - Evidence: this test **does not exist today** — the only end-to-end delimiter test (`:713-736`) asserts merely that `data.parquet` exists and `data.csv` does not, which a one-column Parquet satisfies; the catcher fails pre-fix and passes after 2.1–2.3.
- [x] 2.6 Add the byte-identity test: an undeclared-dialect dataset's Parquet digest equals the pre-change fixture digest (`hashlib`). <!-- sdd-owner: implementation -->
  - Evidence: recorded digest equality, guarding the "no `read_options` when nothing is declared ⇒ byte-identical" rule by construction.

### WU3 — subtraction + call sites (`prepare.py` + 43 test sites)

- [x] 3.1 Thread config into the live path: `src/sofer/prepare.py:757` → `convert_file_to_parquet(local, entry_tmp, cfg)`; drop `_ = cfg  # reserved` at `_converters.py:565`; forward `cfg` in the dispatcher. <!-- sdd-owner: implementation -->
  - Evidence: spy test asserting a `prepare()` run routes CSV conversion through `sofer._converters.convert_file_to_parquet` with the resolved dialect (PC-U06 "single home is exercised", stronger than absence alone).
- [x] 3.2 Delete `src/sofer/prepare.py:81-329` (249 lines: five helper copies + `_convert_to_parquet`, **0 production callers**) after re-checking the range; keep `_cast_null_columns_to_string`'s one live copy at `_converters.py:107` (the third copy is the dead one). <!-- sdd-owner: implementation -->
  - Evidence: repo-wide grep shows `_convert_to_parquet`, `_sniff_csv_delimiter`, `_read_csv_raw_values`, `_check_conversion_parity`, `_cast_null_columns_to_string` are no longer **defined** in `prepare.py`, and nothing in `src/` or `tests/` imports them.
- [x] 3.3 Retarget the 43 call sites per design D4 (27 `tests/test_parquet_conversion.py`, 16 `tests/test_prepare.py`): `_convert_to_parquet` units + the `delimiter=` precedence trio → `tests/test_converters.py::TestConvertFileToParquet` (which today has **no** dialect test); `_sniff_csv_delimiter` ×8 → import swap to `sofer._converters`; `_read_csv_raw_values` / `_check_conversion_parity` → `sofer._converters` with the extended `encoding` argument; delete only verified duplicates of arms already live in `tests/test_converters.py`. <!-- sdd-owner: implementation -->
  - Evidence: before/after `_converters.py` coverage row with no net-negative (no COV-01 floor weakened) plus green `tests/test_converters.py`, `tests/test_parquet_conversion.py`, `tests/test_prepare.py`.
- [x] 3.4 Add the structural absence test (PC-U06 "duplicated cluster is gone and unreferenced") to `tests/test_prepare.py`. <!-- sdd-owner: implementation -->
  - Evidence: full-text scan of `prepare.py` finds zero definitions of the five names and the import check passes; flagged as weaker than 3.1/3.2 behavioural evidence in the spec's Evidence table.
- [x] 3.5 Re-derive both invariants after the deletion: `bash scripts/check_core_coverage.sh` → exit 0 (`prepare.py` still 100.00%, zero `# pragma: no cover`) and the full-suite tally. <!-- sdd-owner: implementation -->
  - Evidence: script exit code 0 plus the re-derived tally compared against task 1.1's baseline.

## Verify-Phase Gates (plain bullets — owner: verify phase)

- `uv run pytest tests/ -q` green with the apply-recorded tally — owner: verify.
- `bash scripts/check_core_coverage.sh` → exit 0; `uv run coverage report -m` at or above the config-owned floor — owner: verify.
- `uv run mypy src/` clean; `uv run ruff check src/ tests/` and `uv run ruff format --check` clean — owner: verify.
- E1–E5 all present and named in the verify report (E1 catcher, E2 declared wins, E3 disagreement warning, E4 declared encoding honoured, E5 byte-identical) — owner: verify.
- Mechanical scope check: `git diff --name-only` contains **zero** `cli.py`, `codebook.py`, `repo_compliance.py`, `mcp_server.py` or `openspec/specs/**` paths — owner: verify.
- Grep proof the `prepare.py` dead helpers are gone and unreferenced across `src/` and `tests/` — owner: verify.

## Parent-Owned Lifecycle (plain bullets — no checkboxes)

- Bound the diff against the authorized 1500-line `size:exception` budget — owner: parent.
- Archive-time canonical sync (PC-U01 + TC-04 as genuine **replacements**, PC-U06 appended) and change archival — owner: parent.
- Commit, push and PR creation (apply does not perform these) — owner: parent.

## Out of Scope (explicit non-goals)

Zero `cli.py` / `codebook.py` paths (issue **#182**, fixed by PR #203); zero `repo_compliance.py` (issue
**#202**); zero MCP changes; the explicit dialect override is issue **#204**. No config-tier or anchoring change
beyond the conversion path, no new CLI flag, no README / `pyproject.toml` / workflow change. Do not modify
`proposal.md`, `design.md`, the two spec deltas, `openspec/specs/**` or `openspec/changes/archive/**`. No commit,
push or PR.

Note: every task above is apply-phase owned (`sdd-owner: implementation`); verify and lifecycle steps are
deliberately unchecked plain bullets so the apply phase can reach a fully checked tasks list.
