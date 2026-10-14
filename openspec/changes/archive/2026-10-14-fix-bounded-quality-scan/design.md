# Design — `2026-10-14-fix-bounded-quality-scan`

> **Change** `2026-10-14-fix-bounded-quality-scan` (issue **#290**) · branch
> `fix/290-bounded-quality-scan` from `dev@4ca823e` · store **hybrid**.

---

## 1. The defect, precisely

Two independent facts make the validator unbounded on a large corpus:

1. `_has_fail_checks()` (`quality.py`) returned `True` when *any* active check had `fail` severity,
   and `_process_file` then passed `max_sample=None` to `stream_csv`. The built-in defaults make
   both `corrupt_records` and `encoding_validation` `fail`, so the default dataset always took the
   full pass — the 8 KB `encoding_validation` probe included; `[quality] max_sample` was silently
   ignored unless the user downgraded both.
2. Per-row accumulators grew with the row count: `_col_nonempty` stored a distinct value set per
   column, `_dup_hashes` stored one hash per distinct row, and `_dup_findings`,
   `_empty_row_numbers` and `_corrupt_findings` were truncated only at report time.

## 2. The decisions (D1–D5, from the ODD task)

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | New knobs are `[tool.sofer]` defaults read through `config.py` (`QUALITY_MAX_DUP_TRACKING`, `QUALITY_FULL_SCAN`, `QUALITY_ROW_REQUIRING_CHECKS`), never literals in `quality.py`. | AGENTS.md rule 1. The parity guard `tests/test_config.py::test_repo_pyproject_declares_every_default_key` requires each `_DEFAULTS` key in `pyproject.toml [tool.sofer]`. |
| **D2** | Hitting the duplication cap **stops inserting new hashes** and marks the `duplicates` finding partial with the cap named — no eviction. | Evicting would drop the first-seen row number that `Row a = Row b` needs and silently hide later duplicates; a named partial is honest. |
| **D3** | S3 is a **narrower predicate**, not per-check multi-pass scanning: the scan is full only when an active `fail` check is in the config-declared row-requiring set (default `["corrupt_records"]`); `encoding_validation` is never in it. | The validator is deliberately single-pass (`openspec/project.md`); a per-check multi-pass would triple I/O on multi-GB files (see §4). |
| **D4** | S4's control is tri-state: `auto` (today's heuristic is the default), `always`, `never`. `never` honours `[quality] max_sample` even with `fail` checks and marks the affected findings `partial`. | "Honoured when set" needs a value that means "I know what I am giving up"; a pure boolean cannot express today's heuristic as the default. |
| **D5** | The default `QUALITY_MAX_DUP_TRACKING` is a bounded value that keeps the reported 66 M-row corpus far below 1 GB, and the cap plus the partial marking are documented in both READMEs. | A cap nobody knows about is a silent coverage change. |

## 3. The cap arithmetic

A `_dup_hashes` entry is a `str` key (32-char md5 hexdigest) mapped to an `int` first-row number,
inside a `dict` slot. Measured with `tracemalloc` over 200 000 real md5 keys (`sys.getsizeof` on the
parts: hexdigest string **73 B**, non-interned int **28 B**):

| Component | Bytes |
| --- | --- |
| md5 hexdigest string (32 chars) | 73 |
| `int` value (not interned once row > 256) | 28 |
| dict slot + entry bookkeeping (derived) | ≈ 42 |
| **Total per tracked row (measured)** | **≈ 143 B** |

At **1 000 000** tracked rows that is **≈ 137 MB** — measured, comfortably below the
parent-approved ~256 MB boundary and far below the 1 GB budget, and independent of the 66.2 M-row
corpus size. The measured `tracemalloc` total for 200 000 entries was 28 681 360 B. The cap is a
`[tool.sofer]` key so a workload with an unusually high distinct-row rate can raise it, at the cost
it explicitly accepts.

## 4. The rejected alternative

**Per-check multi-pass scanning** — scan the file once for each check that needs a different
sampling regime. Rejected because:

- it multiplies I/O by the number of regimes on files that are already multi-GB;
- it breaks the documented single-pass invariant (`openspec/project.md`, module docstring);
- the reported defect is *unbounded memory*, and a narrower full-scan predicate plus bounded
  accumulators fixes it without changing the I/O shape at all.

The narrower predicate is strictly better for the reported case: with `corrupt_records` at `warn`
(the user's escape hatch), the corpus is now sampled by default and the 8 KB probe no longer drags
the whole file into memory.

## 5. The edits

### 5.1 `src/sofer/quality.py`

- `_col_nonempty: dict[str, bool]` keyed `file::col`; `_process_file` seeds each column `False` and
  `_distribute_row` sets `True` on the first non-empty value. Memory is O(columns).
- `_dup_hashes` insertion stops at `config.QUALITY_MAX_DUP_TRACKING`; `_dup_hashes_capped` is set on
  the first refused insert. `_check_duplicates` emits the finding when capped even with no pairs, and
  forces `partial=True` with the cap named.
- `_capped_append(target, item, limit)` bounds `_dup_findings` / `_empty_row_numbers` at
  `REPORT_MAX_ITEMS` and `_corrupt_findings` at `REPORT_MAX_CORRUPT_RECORDS` at accumulation time.
- `_has_fail_checks()` → `_needs_full_scan()`, which consults
  `config.QUALITY_ROW_REQUIRING_CHECKS`.
- `run()` re-reads `config.QUALITY_FULL_SCAN` / `config.QUALITY_MAX_DUP_TRACKING` at call time; the
  per-dataset `cfg.quality.full_scan` value wins when set.
- `_add_result(..., from_sample=False, partial=False)` centralises the `partial` contract: a warn
  finding is partial when the scan was sampled (as before), a streaming finding is also partial when
  the mode is `never`, and a capped accumulator forces it regardless.

### 5.2 `src/sofer/config.py`

- `_DEFAULTS` gains `quality_max_dup_tracking = 1_000_000`, `quality_full_scan = "auto"`,
  `quality_row_requiring_checks = ["corrupt_records"]`; the module constants mirror them.
- `QUALITY_FULL_SCAN_MODES = ("auto", "always", "never")` is the policy vocabulary, deliberately
  **not** a `_DEFAULTS` key (it is the validator's contract, not a user option).
- `_read_tool_section` rejects a `quality_full_scan` outside the closed set and a non-positive
  `quality_max_dup_tracking`.

### 5.3 `src/sofer/model.py`

- `QualityConfig.full_scan: str | None = None`.
- `from_toml` accepts the optional `[quality]` policy table (`full_scan`, `max_sample`); TOML forbids
  it in the same file as the `[[quality]]` per-check array, so the two are mutually exclusive. An
  unknown mode is warned and ignored, matching the unknown-check-name behaviour.

### 5.4 Config-surface change: `quality_value_preview_len` removed

`quality_value_preview_len` (`[tool.sofer]`, default 50, issue #189) truncated the values stored in
`_col_nonempty`. With S1 that accumulator stores a boolean, so the key has **no reader left**. This
change removes it rather than keeping a knob that lies:

| Surface | Change |
| --- | --- |
| `src/sofer/config.py` | `_DEFAULTS` entry and `QUALITY_VALUE_PREVIEW_LEN` module constant removed |
| `pyproject.toml` | `quality_value_preview_len = 50` and its comment removed |
| `docs/configuration.md` | the key was never documented there — no entry to remove; a new "Quality scan bounds" section documents the replacement keys |
| `tests/test_config.py` | `test_quality_value_preview_len_default` removed; the two reload/override vehicles re-pointed to `schema_sample_size`; `test_quality_value_preview_len_key_removed` pins the removal |
| `tests/test_quality.py` | `TestValuePreviewLen` (which asserted the truncation of stored values) rewritten as `TestColNonemptyBoolean` |

A reviewer must be able to see this removal in the diff; it is listed here and in the archive report.

## 6. `partial` semantics (the contract S6 asks for)

A `QualityResult.partial` is `True` when its evidence is not a complete view:

- the scan was sampled *and* the finding is a streaming `warn` finding;
- the scan was sampled *and* the mode is `never` and the finding is streaming (any severity);
- the duplicate-tracking cap was hit (`partial=True`, the cap named in the message).

`encoding_validation` is a fixed-size probe and is never marked partial by sampling.

## 7. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | `auto` now full-scans only when `corrupt_records` is `fail`. A dataset that downgraded it to `warn` and relied on the old implicit full pass will sample. | **Med** | Deliberate: that implicit pass *is* the reported defect. The sampled findings are marked `partial`, and `quality_full_scan = "always"` restores the strict behaviour. Recorded in both READMEs. |
| R2 | The duplicate cap can miss a later duplicate whose first occurrence fell beyond the cap. | Med | Named by D2 and surfaced as a `partial` finding with the cap printed. No silent coverage loss. |
| R3 | Removing `quality_value_preview_len` breaks a user config that set it. | Low | `_read_tool_section` iterates `_DEFAULTS`, so an unknown `[tool.sofer]` key is ignored (no error). Declared in §5.4. |
| R4 | `[quality]` policy table and `[[quality]]` checks are mutually exclusive. | Low | A TOML grammar constraint, not a sofer choice; documented in `docs/configuration.md` and the spec delta. |

## 8. Rollback

Revert-only: restoring the previous `quality.py` bodies, the `config.py` defaults and the
`[tool.sofer]` lines restores the previous behaviour exactly. No migration, no persisted state.

## 9. Verifications

The RED/GREEN evidence, the gate battery, and the coverage numbers are recorded in `tasks.md` and
`archive-report.md`.
