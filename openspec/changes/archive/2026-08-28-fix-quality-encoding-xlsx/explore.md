# Exploration: fix-quality-encoding-xlsx

## Current State

`QualityValidator.run()` (`src/sofer/quality.py:110`) iterates every `[[file]]`
entry, resolves it, and unconditionally calls both
`_check_encoding_validation(resolved)` and `_process_file(resolved)` — no
format guard. Both paths assume text CSV:

- `_check_encoding_validation` (`quality.py:489`) reads the first
  `config.PROBE_CHUNK_BYTES` (8 KB) and tries `chunk.decode(enc)` for each
  `ENCODING_FALLBACKS` entry. Current `ENCODING_FALLBACKS`
  (`src/sofer/_csv_reader.py:27`) is `["utf-8-sig", "utf-8"]` only — the spec
  at `openspec/specs/data-quality/spec.md §4.9` describes
  `utf-8-sig → utf-8 → latin-1 → cp1252` but the implementation was narrowed to
  UTF-8-only (quality gate rejects non-UTF-8). On a binary `.xlsx` (ZIP
  container, magic bytes `PK\x03\x04`) the probe either fails UTF-8 decode
  (→ `encoding_validation: fail`) or, if the 8 KB slice happens to be
  valid UTF-8, `stream_csv` still fails downstream.
- `_process_file` (`quality.py:189`) calls `stream_csv` (`_csv_reader.py:35`)
  with `delimiter=cfg.csv_delimiter`, `encoding=cfg.csv_encoding`. `stream_csv`
  builds a fallback chain from `ENCODING_FALLBACKS` and raises `ValueError:
  Cannot decode ... all encodings exhausted` on binary input. `run()` catches
  that `ValueError` and silently returns from `_process_file`, but the encoding
  failure has already been recorded as a `fail`-severity `QualityResult`. For
  the reported reproduction (2 `.xlsx` files, `sofer publish --target local`)
  that yields `2 failed` (one per xlsx), `7 passed, 1 skipped` in
  `ValidationReport.print_summary` (`checks.py:87`).

`prepare.py` is correct: the conversion loop (`prepare.py:671`) only considers
`remote_lower.endswith(".csv")` or `.parquet`; everything else is staged as-is
via `copy_to_mirror` (`prepare.py:766`). The user correctly observes
`0 parquet(s) generated is expected` for xlsx-only datasets. Quality is the
only subsystem that treats xlsx/parquet/jsonl as if they were CSV.

Other readers are consistent with the fix direction: `repo_compliance.py`
detects Parquet vs CSV by suffix (Parquet branch reads via `pq.ParquetFile`);
`prepare._convert_to_parquet` is gated on `.csv`; `_formats.SUPPORTED_FORMATS`
lists `.csv/.tsv` as text and `.parquet/.xlsx/.jsonl` as binary. No other
quality sub-check is binary-aware; all of `_distribute_row`, `format_consistency`,
`cross_file_types`, `corrupt_records`, etc. operate on the rows produced by
`stream_csv`.

### Reported symptom vs spec drift

- Symptom matches code: `encoding_validation` default `fail` blocks
  `publish` (PUB-01 quality gate) even though binary files are not CSV.
- Spec drift: `data-quality §4.9` still documents a 4-encoding fallback
  (`latin-1`/`cp1252`); implementation enforces UTF-8-only. The fix scope
  explicitly excludes re-adding latin-1/cp1252 — the bug is the missing
  format filter, not the fallback width.

## Affected Areas

- `src/sofer/quality.py` — primary fix. Guard `run()` loop and/or
  `_check_encoding_validation` + `_process_file` to skip non-CSV inputs.
  Owns `_BUILTIN_DEFAULTS`, `run`, `_check_encoding_validation`,
  `_process_file`, `_infer_file_types`, `ran_checks` accounting.
- `src/sofer/_csv_reader.py` — defines `ENCODING_FALLBACKS` and `stream_csv`.
  Not changed for the suffix fix, but referenced for encoding semantics and
  the narrowed fallback chain (spec vs implementation). Potential home for a
  shared `is_text_csv()` helper if not placed in `_formats.py`.
- `src/sofer/_formats.py` — registry `SUPPORTED_FORMATS` and natural home for
  `TEXT_SUFFIXES = {".csv", ".tsv"}` or `is_quality_eligible(path)`. Keeps
  format knowledge in one module per `one-module-per-concern`.
- `src/sofer/prepare.py` — reference implementation for correct format gating
  (`remote_lower.endswith(".csv")` / `".parquet"`). No change needed; used as
  pattern to align quality with.
- `src/sofer/repo_compliance.py` — analogous suffix branching (`Parquet` vs
  `CSV` via `build_schema_report`); no change, but confirms suffix-filter
  pattern is established.
- `src/sofer/checks.py` / `src/sofer/model.py` — `QUALITY_CHECK_NAMES`,
  `_count_passed_quality`, `ValidationReport.ran_checks` accounting. Must
  decide whether skipped binary files leave `ran_checks` unchanged (current
  skipped-count math) or explicitly avoid marking `encoding_validation` as
  "ran" when nothing eligible was scanned.
- `src/sofer/config.py` — if a config-driven allowlist alternative is chosen,
  new key (e.g. `quality_eligible_suffixes`) would live here under
  `[tool.sofer]`. Not recommended (see below).
- `tests/test_quality.py`, `tests/test_publish.py`, `tests/test_prepare.py` —
  verification surface. Existing `TestCheckEncodingValidation` covers UTF-8
  vs latin-1; needs new cases for `.xlsx`/`.parquet`/`.jsonl` skipped.

## Approaches

### 1. Suffix allowlist filter in `QualityValidator` (recommended)

Gate `QualityValidator` to text formats only.

- Implementation: define `QUALITY_ELIGIBLE_SUFFIXES = {".csv", ".tsv"}` in
  `src/sofer/_formats.py` (or `src/sofer/quality.py` if keeping the change
  local) and early-return in both `_check_encoding_validation` and
  `_process_file` when `resolved.suffix.lower() not in ELIGIBLE`, or filter
  once at the top of `run()`:
  ```python
  if resolved.suffix.lower() not in TEXT_SUFFIXES:
      continue  # skip encoding + streaming checks entirely
  ```
  Directories already `continue`; add suffix check alongside. Helper is
  `PurePath.suffix.lower()` — handles `.XLSX`, `.CSV`, no-extension files.

- Pros: minimal, matches `prepare.py` precedent; zero new I/O; keeps format
  knowledge in `_formats.py`; trivial to test; preserves UTF-8-only policy;
  fixes both `encoding_validation` and all streaming checks at once.
- Cons: suffix-spoofed files (e.g. `.csv` that is actually ZIP) still fail
  — but that is correct (user mislabeled the file). Does not detect binary
  content inside a `.csv`.
- Effort: Low. One constant + 3–5 line guard. No new dependency.

### 2. Magic-byte / content sniffing (`PK` header, NUL-byte heuristic)

Peek first bytes and skip files that look binary.

- Implementation: in `_check_encoding_validation`, before decoding, check
  `chunk[:4] == b"PK\x03\x04"` (ZIP/xlsx), or `b"\x00" in chunk`, or
  `chunk[:4] in (b"\x89PNG", b"%PDF")`. If binary, return without emitting a
  finding. Optionally reuse for `stream_csv`.
- Pros: robust to wrong/missing extensions; catches mislabeled binaries even
  when named `.csv`.
- Cons: heuristic; 8 KB peek can be valid UTF-8 for some binaries (spec
  acknowledges this as an accepted P0 limitation); reads bytes twice
  (`_check_encoding_validation` + `stream_csv`); spreads binary detection
  across two modules; still needs suffix logic for `parquet`/`jsonl` which
  are text but not CSV.
- Effort: Medium. Requires deciding threshold, adding branch coverage, and
  handling the double-read.

### 3. Config-driven allowlist (`[tool.sofer] quality_eligible_suffixes`)

Make the set of quality-checked suffixes user-configurable via
`pyproject.toml` / `config.py`.

- Implementation: add `quality_eligible_suffixes: list[str] = [".csv", ".tsv"]`
  to `_DEFAULTS` in `config.py`, merge in `_discover`, and read via
  `config.QUALITY_ELIGIBLE_SUFFIXES` in `quality.py`.
- Pros: flexible for future formats (e.g. `.psv`); follows AGENTS.md rule
  "tool-wide defaults belong in `[tool.sofer]`".
- Cons: over-engineering for the reported bug; adds config surface and docs
  burden; users should not need to configure "xlsx is not CSV"; indirection
  makes the fix harder to reason about. Violates YAGNI for a clear
  correctness bug where quality checks MUST be CSV/TSV-only (user expectation
  in the issue).
- Effort: Medium. New config key + merge logic + docs + README sync.

## Recommendation

**Approach 1 — suffix allowlist via `_formats.py`.**

Reasoning:

1. The bug is a missing format guard, not an encoding problem. Aligning
   `quality.py` with `prepare.py`'s existing `endswith(".csv")` pattern is
   the smallest correct fix and preserves the architecture rule
   "one module per concern" (format registry lives in `_formats.py`).
2. The expected fix per the issue is `quality checks should be CSV/TSV-only
   and skip binary formats (xlsx, parquet, jsonl)` — exactly a suffix
   allowlist. Magic-byte detection is a defense-in-depth enhancement, not a
   replacement (a `.csv` that contains ZIP bytes SHOULD fail encoding).
3. Config-driven allowlisting is premature. If a future format needs quality
   coverage, add it to `TEXT_SUFFIXES` in code — the allowlist is a product
   invariant, not a user preference. No new `[tool.sofer]` key needed.

Concrete sketch (for proposal, not applied here):

```python
# src/sofer/_formats.py
TEXT_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv"})
def is_text_eligible(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES
```

```python
# src/sofer/quality.py — in run() loop, after exists/is_dir check
from ._formats import is_text_eligible
if not is_text_eligible(resolved):
    continue
```

Alternative local placement: inline `if resolved.suffix.lower() not in {".csv", ".tsv"}: continue`
keeps the diff smaller; preferred if the change aims for < 400-line PR budget.

Spec note: keep `ENCODING_FALLBACKS = ["utf-8-sig", "utf-8"]` as-is. The
`data-quality §4.9` 4-encoding chain is stale; the proposal should delta
that spec to document UTF-8-only enforcement and explicitly scope all quality
checks to CSV/TSV (add `GIVEN a .xlsx file WHEN QualityValidator.run() THEN
no encoding_validation finding SHALL be appended` scenario). Also note that
`stream_csv`'s `ValueError` path remains the safety net for mislabeled
binaries named `.csv`.

## Risks

- **Suffix case sensitivity / double extensions**: `.XLSX`, `.Csv`, `data.csv.gz`
  — use `.suffix.lower()` (only last suffix) so `.csv.gz` is treated as `.gz`
  (skip, correct for now). Document that compressed CSVs are out of scope.
- **`ran_checks` / summary accounting**: if `run()` skips all files (xlsx-only
  dataset), `ran_checks` will still contain `encoding_validation` (added at
  entry of `_check_encoding_validation`). The guard should either not add to
  `ran_checks` when skipping, or add a file-count check so the summary does
  not show `0 passed` vs `1 skipped` incorrectly. The prepare report's
  `0 parquet(s) generated` is expected and non-blocking — ensure quality
  summary similarly shows `0 failed` rather than blocking publish.
- **`.tsv` handling**: `_formats.SUPPORTED_FORMATS` includes `.tsv`; quality
  must include it. Forgetting `.tsv` would regress TSV datasets. Tests must
  cover `.tsv` explicitly.
- **`parquet`/`jsonl`/`xlsx` staged via `copy_to_mirror`**: these files are
  legitimately delivered; skipping quality must not affect their staging or
  `build_schema_report` (which already suffix-branches).
- **Spec drift on encoding fallbacks**: if the fix re-adds `latin-1`/`cp1252`
  to satisfy the stale spec, it contradicts the UTF-8-only quality gate and
  weakens the encoding guarantee. The delta spec should reconcile this.
- **Recursive `FileEntry` (directory) entries**: `run()` already skips
  `is_dir()`; suffix check must run after that to avoid `Path.suffix` on
  directories (which is `""` and would skip correctly but is redundant).

## Ready for Proposal

Yes. Scope is bounded and well-understood. Next phase is `sdd-propose` for
`fix-quality-encoding-xlsx` (hybrid store). Proposal should define:

- In-scope: suffix guard in `QualityValidator` (xlsx/parquet/jsonl skipped),
  delta spec for `data-quality §4.9` + `quality.py run()` scoping, tests for
  skipped binary formats.
- Out-of-scope: re-adding latin-1/cp1252, magic-byte detection, config key,
  changes to `prepare.py` staging.

Branch `fix/quality-encoding-xlsx` is already cut from `dev`; `strict_tdd`
is false, verification command is `uv run pytest tests/ -q` per
`openspec/config.yaml`.
