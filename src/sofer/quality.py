"""
Data-quality checks for CSV/TSV content (P0).

The :class:`QualityValidator` runs all active P0 checks in a **single pass**
per file — each eligible file is opened once and every row is distributed to
all active accumulators simultaneously.

Per-row memory is bounded and independent of the dataset size (issue #290):
the ``empty_columns`` bookkeeping is a per-column "seen non-empty" boolean,
the ``duplicates`` hash table is capped at ``config.QUALITY_MAX_DUP_TRACKING``,
and the per-row finding lists stop growing at their report limits. The
full-scan decision is explicit and config-owned (``config.QUALITY_FULL_SCAN``,
with an optional per-dataset override): ``auto`` scans every row only for the
config-declared row-requiring checks, ``always`` scans every row, and ``never``
honours ``max_sample`` even with a ``fail`` check active.

Only text-eligible files (``.csv`` / ``.tsv``, case-insensitive via
``is_text_eligible`` from :mod:`sofer._formats`) are scanned.  Non-eligible
suffixes (``.xlsx``, ``.parquet``, ``.jsonl``, ``.gz``, no extension) are
skipped without I/O, without accumulator updates, and without ``ran_checks``
entries.  ``_check_encoding_validation`` enforces UTF-8-only
(``utf-8-sig → utf-8``) — ``latin-1``/``cp1252`` are not retried; a
``ValueError`` from :func:`sofer._csv_reader.stream_csv` remains the safety
net for mislabeled ``.csv`` files containing binary bytes.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import config
from ._csv_reader import ENCODING_FALLBACKS, stream_csv
from ._formats import is_text_eligible
from ._sentinels import MISSING_VALUE_SENTINELS
from .checks import ValidationReport
from .codebook import infer_column_type
from .model import QUALITY_CHECK_NAMES, DatasetConfig, QualityCheck, QualityResult

# ---------------------------------------------------------------------------
#  Built-in defaults — used when the user gives no explicit [[quality]] config
# ---------------------------------------------------------------------------

_BUILTIN_DEFAULTS: dict[str, dict[str, Any] | None] = {
    "duplicates": {"severity": "warn"},
    "empty_rows": {"severity": "warn"},
    "empty_columns": {"severity": "warn"},
    "null_profiling": {"severity": "warn", "max_null_pct": 50.0},
    "format_consistency": {"severity": "warn"},
    "corrupt_records": {"severity": "fail"},
    "encoding_validation": {"severity": "fail"},
    "cross_file_types": {"severity": "warn"},
    "value_range": None,  # skipped unless explicitly configured
}


def _is_empty(value: str) -> bool:
    """Return True when *value* should be considered empty / missing."""
    cleaned = value.strip()
    return not cleaned or cleaned.upper() in MISSING_VALUE_SENTINELS


def _capped_append(target: list[Any], item: Any, limit: int) -> None:
    """Append *item* to *target* only while it holds fewer than *limit* items.

    Bounds the per-row finding lists so their memory is independent of the
    dataset size (issue #290): the report only ever prints the first *limit*
    entries, so anything beyond that is dead weight.

    Args:
        target: The list accumulator to grow.
        item: The finding to append.
        limit: Maximum length of *target*.
    """
    if len(target) < limit:
        target.append(item)


# ---------------------------------------------------------------------------
#  QualityValidator
# ---------------------------------------------------------------------------


class QualityValidator:
    """Streaming content-quality checker for one dataset.

    Args:
        cfg: Parsed dataset configuration (may or may not have ``[[quality]]``
             entries — built-in defaults fill in anything unspecified).
    """

    def __init__(self, cfg: DatasetConfig) -> None:
        self.cfg = cfg
        self._report = ValidationReport(cfg.name)

        # ── Merge user config with built-in defaults ────────────────────
        user_overrides: dict[str, QualityCheck] = {}
        for qc in cfg.quality.checks:
            user_overrides[qc.check] = qc

        self._checks: dict[str, dict[str, Any]] = {}
        for check_name, default_cfg in _BUILTIN_DEFAULTS.items():
            if default_cfg is None:
                # value_range — only activate when user provides min/max
                if check_name in user_overrides:
                    uc = user_overrides[check_name]
                    if uc.min is not None or uc.max is not None:
                        self._checks[check_name] = {
                            "severity": uc.severity or cfg.quality.default_severity,
                            "columns": uc.columns,
                            "min": uc.min,
                            "max": uc.max,
                        }
                continue

            if check_name in user_overrides:
                uc = user_overrides[check_name]
                merged: dict[str, Any] = dict(default_cfg)
                merged["severity"] = uc.severity or cfg.quality.default_severity
                if uc.columns is not None:
                    merged["columns"] = uc.columns
                if uc.max_null_pct is not None:
                    merged["max_null_pct"] = uc.max_null_pct
                if uc.min_unique is not None:
                    merged["min_unique"] = uc.min_unique
                if uc.ignore_values is not None:
                    merged["ignore_values"] = uc.ignore_values
                self._checks[check_name] = merged
            else:
                self._checks[check_name] = dict(default_cfg)

        # Make sure user-supplied max_sample is respected
        self._max_sample = cfg.quality.max_sample
        self._had_eligible: bool = False

        # Full-scan policy and duplicate cap — re-read from config in run()
        # (call-site read, never frozen at import); the per-dataset
        # ``quality.full_scan`` override wins over the tool-wide default.
        self._full_scan_mode: str = cfg.quality.full_scan or config.QUALITY_FULL_SCAN
        self._dup_tracking_cap: int = config.QUALITY_MAX_DUP_TRACKING

        # ── Accumulator state (reset per run) ───────────────────────────
        self._reset_accumulators()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def run(self) -> ValidationReport:
        """Execute every active quality check across all eligible files.

        Only text-eligible files (``.csv``/``.tsv``, case-insensitive) are
        scanned.  Non-eligible files are skipped after the ``exists``/
        ``is_dir`` guards with no I/O, no accumulator updates, and no
        ``ran_checks`` entries.

        Returns:
            A :class:`ValidationReport` whose ``quality_results`` list holds
            every finding.
        """
        self._reset_accumulators()
        self._full_scan_mode = self.cfg.quality.full_scan or config.QUALITY_FULL_SCAN
        self._dup_tracking_cap = config.QUALITY_MAX_DUP_TRACKING
        base = self.cfg._base_dir if self.cfg._base_dir else Path.cwd()

        for entry in self.cfg.files:
            resolved = entry.resolve(base)
            if not resolved.exists() or resolved.is_dir():
                continue
            if not is_text_eligible(resolved):
                continue

            self._had_eligible = True

            # ── Pre-scan: encoding validation ──────────────────────────
            self._check_encoding_validation(resolved)

            # ── Streaming pass — interleave all per-row checks ─────────
            self._process_file(resolved)

        # ── Post-scan checks ───────────────────────────────────────────
        self._check_cross_file_types()
        self._check_duplicates()
        self._check_empty_rows()
        self._check_empty_columns()
        self._check_null_profiling()
        self._check_format_consistency()
        self._check_corrupt_records()
        self._check_value_range()

        self._report.quality_results = self._results
        self._report.ran_checks = self._ran_checks
        return self._report

    # ------------------------------------------------------------------
    #  Accumulator initialisation
    # ------------------------------------------------------------------

    def _reset_accumulators(self) -> None:
        self._results: list[QualityResult] = []
        self._had_eligible = False
        # Per-file state
        self._file_headers: dict[str, list[str]] = {}
        self._file_row_count: dict[str, int] = {}
        # duplicates
        self._dup_hashes: dict[str, int] = {}  # hash → first row number
        # Duplicate pairs grouped by file: naming the file keeps the finding
        # traceable back to a table (issue #293), and capping each file's list at
        # the report limit keeps memory independent of the dataset size while
        # every affected file can still reach the report (issue #290).
        self._dup_findings: dict[str, list[tuple[int, int]]] = {}
        self._dup_hashes_capped: bool = False  # cap hit → finding is partial
        # empty rows
        self._empty_row_numbers: list[int] = []
        # empty columns — per-column "seen non-empty" boolean, keyed file::col
        self._col_nonempty: dict[str, bool] = {}
        # null profiling
        self._null_counts: dict[str, tuple[int, int]] = {}  # col → (total, null)
        # format consistency
        self._col_samples: dict[str, list[str]] = defaultdict(list)
        # corrupt records
        # (file, row, actual, expected)
        self._corrupt_findings: list[tuple[str, int, int, int]] = []
        # value range
        self._col_min: dict[str, float | None] = {}
        self._col_max: dict[str, float | None] = {}
        # cross-file types
        self._file_col_types: dict[str, dict[str, str]] = defaultdict(dict)
        # current file tracking
        self._current_file: str = ""
        self._current_header: list[str] = []
        # partial scan tracking (Issue #14)
        self._scan_is_partial: bool = False
        # ran checks tracking (Issue #14)
        self._ran_checks: set[str] = set()

    def _needs_full_scan(self) -> bool:
        """Return True when an active ``fail`` check needs every row.

        The row-requiring names are config-declared
        (``config.QUALITY_ROW_REQUIRING_CHECKS``), so a cheap fixed-size probe
        such as the 8 KB ``encoding_validation`` check never turns a ``fail``
        severity into an unsampled pass over every row (issue #290).
        """
        row_requiring = set(config.QUALITY_ROW_REQUIRING_CHECKS)
        return any(
            cfg.get("severity") == "fail" and name in row_requiring
            for name, cfg in self._checks.items()
        )

    # ------------------------------------------------------------------
    #  File processing (single pass, interleaved)
    # ------------------------------------------------------------------

    def _process_file(self, resolved: Path) -> None:
        """Open one CSV/TSV and distribute all rows to active accumulators.

        Non-eligible paths return immediately with no accumulator updates and
        no ``ran_checks`` mutation (defensive guard for direct calls).
        """
        if not is_text_eligible(resolved):
            return
        fname = resolved.name
        self._current_file = fname
        self._file_row_count[fname] = 0

        # Full-scan decision (issue #290): the tri-state policy decides, not
        # severity alone. ``auto`` scans every row only when an active fail
        # check is in the declared row-requiring set.
        effective_max_sample: int | None
        if self._full_scan_mode == "always":
            effective_max_sample = None
        elif self._full_scan_mode == "never":
            effective_max_sample = self._max_sample
        elif self._needs_full_scan():
            effective_max_sample = None
        else:
            effective_max_sample = self._max_sample
        if effective_max_sample is not None:
            self._scan_is_partial = True

        try:
            gen = stream_csv(
                resolved,
                delimiter=self.cfg.csv_delimiter,
                encoding=self.cfg.csv_encoding,
                max_sample=effective_max_sample,
            )
            header, _ = next(gen)
        except ValueError:
            # Encoding issue — already reported by _check_encoding_validation
            return
        except StopIteration:
            # Completely empty file (no header)
            return
        except (OSError, csv.Error) as exc:
            # Unreadable or corrupt file — produce a fail finding (Issue #14)
            self._add_result(
                "corrupt_records",
                "fail",
                f"Cannot read '{fname}': {exc}",
            )
            return
        self._current_header = header
        self._file_headers[fname] = header

        # Initialise per-column accumulators for this file's header
        # Key includes fname to avoid cross-file collision (Issue #14)
        for col_name in header:
            self._col_nonempty.setdefault(f"{fname}::{col_name}", False)

        row_number = 0
        for _header, row in gen:
            if row is None:  # header-only yield already consumed
                continue
            row_number += 1
            self._file_row_count[fname] = row_number
            self._distribute_row(row_number, row)

        # After file processed, infer column types for cross-file comparison
        self._infer_file_types(fname, header)

    def _distribute_row(self, row_number: int, row: list[str]) -> None:
        """Send one data row to every active per-row accumulator."""
        # corrupt_records — needs raw row length first
        if "corrupt_records" in self._checks:
            if len(row) != len(self._current_header):
                _capped_append(
                    self._corrupt_findings,
                    (self._current_file, row_number, len(row), len(self._current_header)),
                    config.REPORT_MAX_CORRUPT_RECORDS,
                )
                return  # skip other checks for corrupt rows

        has_any_nonempty = False
        for col_idx, value in enumerate(row):
            col_name = (
                self._current_header[col_idx]
                if col_idx < len(self._current_header)
                else f"col_{col_idx}"
            )
            is_missing = _is_empty(value)

            # empty_rows
            if not is_missing:
                has_any_nonempty = True

            # empty_columns — per-column "seen non-empty" boolean (issue #290):
            # a value set here was the largest per-row accumulator.
            if not is_missing:
                self._col_nonempty[f"{self._current_file}::{col_name}"] = True

            # null_profiling
            key_n = f"{self._current_file}:{col_name}"
            if key_n in self._null_counts:
                t, n = self._null_counts[key_n]
                self._null_counts[key_n] = (t + 1, n + (1 if is_missing else 0))
            else:
                self._null_counts[key_n] = (1, 1 if is_missing else 0)

            # format_consistency — collect values (capped)
            if "format_consistency" in self._checks:
                if len(self._col_samples[col_name]) < self._max_sample:
                    self._col_samples[col_name].append(value)

            # value_range
            if "value_range" in self._checks:
                cfg = self._checks["value_range"]
                tracked_cols = cfg.get("columns")
                if tracked_cols is None or col_name in tracked_cols:
                    if not is_missing:
                        try:
                            num = float(value.replace(",", "."))
                            prev_min = self._col_min.get(col_name)
                            prev_max = self._col_max.get(col_name)
                            if prev_min is None or num < prev_min:
                                self._col_min[col_name] = num
                            if prev_max is None or num > prev_max:
                                self._col_max[col_name] = num
                        except ValueError:
                            pass

        # duplicates — hash the entire row (scoped per file to avoid cross-file
        # false positives). New hashes stop at the cap; the cap is reported as
        # a partial finding instead of silently evicting tracked rows (issue #290).
        if "duplicates" in self._checks:
            row_str = f"{self._current_file}|{'|'.join(row)}"
            h = hashlib.md5(row_str.encode("utf-8"), usedforsecurity=False).hexdigest()
            if h in self._dup_hashes:
                self._record_duplicate_pair(self._dup_hashes[h], row_number)
            elif len(self._dup_hashes) < self._dup_tracking_cap:
                self._dup_hashes[h] = row_number
            else:
                self._dup_hashes_capped = True

        # empty_rows
        if not has_any_nonempty:
            _capped_append(self._empty_row_numbers, row_number, config.REPORT_MAX_ITEMS)

    # ------------------------------------------------------------------
    #  Post-scan check methods (produce QualityResult entries)
    # ------------------------------------------------------------------

    def _add_result(
        self,
        check: str,
        severity: str,
        message: str,
        *,
        from_sample: bool = False,
        partial: bool = False,
    ) -> None:
        """Append one finding to the report.

        Args:
            check: Check name identifier.
            severity: ``"warn"`` or ``"fail"``.
            message: Human-readable description of the finding.
            from_sample: ``True`` when the evidence comes from the per-row
                streaming pass (not from a fixed-size probe such as the 8 KB
                encoding check). A sampled scan makes streaming ``warn``
                findings partial as before, and streaming ``fail`` findings
                partial under ``quality_full_scan = "never"``.
            partial: Force the partial flag regardless of scan mode — used when
                an accumulator was itself capped (the duplicate-tracking cap).
        """
        if not partial and self._scan_is_partial:
            if severity == "warn":
                partial = True
            elif from_sample and self._full_scan_mode == "never":
                partial = True
        self._results.append(
            QualityResult(check=check, severity=severity, message=message, partial=partial)
        )
        # Track that this check actually ran (Issue #14)
        self._ran_checks.add(check)

    def _record_duplicate_pair(self, first_row: int, dup_row: int) -> None:
        """Record one duplicate pair under its file, capped at the report limit.

        The list is per file so the report can attribute every pair (issue #293)
        while the cap keeps memory bounded and still lets every affected file
        reach the report (issue #290).

        Args:
            first_row: Row number of the first occurrence.
            dup_row:   Row number of the duplicate occurrence.
        """
        pairs = self._dup_findings.setdefault(self._current_file, [])
        _capped_append(pairs, (first_row, dup_row), config.REPORT_MAX_ITEMS)

    def _check_duplicates(self) -> None:
        """Emit the ``duplicates`` finding, attributed to the file it came from.

        The row hash is namespaced per file, so a bare row number is not
        resolvable from the report — every pair names its file (issue #293).
        Pairs are taken round-robin across files so one noisy file cannot spend
        the whole ``REPORT_MAX_ITEMS`` budget and hide the other affected files,
        and when the hash-tracking cap was hit the finding is marked partial and
        the cap is named (issue #290).
        """
        if "duplicates" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("duplicates")
        if not self._dup_findings and not self._dup_hashes_capped:
            return
        limit = config.REPORT_MAX_ITEMS
        parts: list[str] = []
        for depth in range(max((len(p) for p in self._dup_findings.values()), default=0)):
            if len(parts) >= limit:
                break
            for fname, pairs in self._dup_findings.items():
                if depth < len(pairs) and len(parts) < limit:
                    first, dup = pairs[depth]
                    parts.append(f"{fname}: Row {first} = Row {dup}")
        sev = self._checks["duplicates"]["severity"]
        pairs_str = "; ".join(parts)
        if self._dup_hashes_capped:
            cap_note = f"partial — tracking capped at {self._dup_tracking_cap} distinct rows"
            message = (
                f"Duplicate rows: {pairs_str} ({cap_note})"
                if parts
                else f"Duplicates: none found within the cap ({cap_note})"
            )
        else:
            message = f"Duplicate rows: {pairs_str}"
        self._add_result(
            "duplicates",
            sev,
            message,
            from_sample=True,
            partial=self._dup_hashes_capped,
        )

    def _check_empty_rows(self) -> None:
        if "empty_rows" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("empty_rows")
        if not self._empty_row_numbers:
            return
        sample = ", ".join(str(r) for r in self._empty_row_numbers[: config.REPORT_MAX_ITEMS])
        sev = self._checks["empty_rows"]["severity"]
        self._add_result("empty_rows", sev, f"Empty rows: {sample}", from_sample=True)

    def _check_empty_columns(self) -> None:
        if "empty_columns" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("empty_columns")
        # Group empty columns per-file using the "fname::col" key format
        per_file: dict[str, list[str]] = defaultdict(list)
        for key, seen_nonempty in self._col_nonempty.items():
            if not seen_nonempty and "::" in key:
                fname, col = key.split("::", 1)
                per_file[fname].append(col)
        if not per_file:
            return
        sev = self._checks["empty_columns"]["severity"]
        for fname, cols in per_file.items():
            # Skip zero-row files — a header-only file has no data to check
            if self._file_row_count.get(fname, 0) == 0:
                continue
            self._add_result(
                "empty_columns",
                sev,
                f"Fully empty columns in '{fname}': {', '.join(cols)}",
                from_sample=True,
            )

    def _check_null_profiling(self) -> None:
        if "null_profiling" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("null_profiling")
        threshold = self._checks["null_profiling"].get("max_null_pct", 50.0)
        over_limit: list[str] = []
        per_file: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
        for key, (total, nulls) in self._null_counts.items():
            # key format: "filename:colname"
            if ":" in key:
                fname, col = key.split(":", 1)
                per_file[fname][col] = (total, nulls)
        # Aggregate across files per column (simple: sum counts across files)
        agg: dict[str, tuple[int, int]] = {}
        for fname, cols in per_file.items():
            for col, (total, nulls) in cols.items():
                if col in agg:
                    pt, pn = agg[col]
                    agg[col] = (pt + total, pn + nulls)
                else:
                    agg[col] = (total, nulls)
        for col, (total, nulls) in agg.items():
            if total == 0:
                continue
            pct = nulls / total * 100
            if pct > threshold:
                over_limit.append(f"{col} ({pct:.1f}%)")
        if not over_limit:
            return
        sev = self._checks["null_profiling"]["severity"]
        msg = f"Columns exceeding {threshold}% nulls: {'; '.join(over_limit)}"
        self._add_result("null_profiling", sev, msg, from_sample=True)

    def _check_format_consistency(self) -> None:
        if "format_consistency" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("format_consistency")
        ignore = self._checks["format_consistency"].get("ignore_values", [])
        ignore_set = {v.upper() for v in ignore}
        mixed_cols: list[str] = []
        for col_name, values in self._col_samples.items():
            # Filter standard empty sentinels AND user-configured ignore_values
            filtered = [
                v for v in values if not _is_empty(v) and v.strip().upper() not in ignore_set
            ]
            if not filtered:
                continue
            col_type = infer_column_type(filtered)
            if col_type == "mixed (mostly numeric)":
                mixed_cols.append(col_name)
        if not mixed_cols:
            return
        sev = self._checks["format_consistency"]["severity"]
        self._add_result(
            "format_consistency",
            sev,
            f"Mixed-type columns: {', '.join(mixed_cols)}",
            from_sample=True,
        )

    def _check_corrupt_records(self) -> None:
        if "corrupt_records" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("corrupt_records")
        if not self._corrupt_findings:
            return
        sev = self._checks["corrupt_records"]["severity"]
        limit = config.REPORT_MAX_CORRUPT_RECORDS
        for fname, row, actual, expected in self._corrupt_findings[:limit]:
            self._add_result(
                "corrupt_records",
                sev,
                f"Row {row} in '{fname}' has {actual} fields, header has {expected}",
                from_sample=True,
            )

    def _check_value_range(self) -> None:
        if "value_range" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("value_range")
        cfg = self._checks["value_range"]
        sev = cfg["severity"]
        col_min = cfg.get("min")
        col_max = cfg.get("max")
        tracked_cols = cfg.get("columns")

        over: list[str] = []
        for col_name in tracked_cols or []:
            actual_min = self._col_min.get(col_name)
            actual_max = self._col_max.get(col_name)
            if actual_min is not None and col_min is not None and actual_min < col_min:
                over.append(f"{col_name}: min {actual_min} < {col_min}")
            if actual_max is not None and col_max is not None and actual_max > col_max:
                over.append(f"{col_name}: max {actual_max} > {col_max}")
        if not over:
            return
        for msg in over:
            self._add_result("value_range", sev, f"Out of range — {msg}", from_sample=True)

    def _check_cross_file_types(self) -> None:
        if "cross_file_types" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("cross_file_types")
        sev = self._checks["cross_file_types"]["severity"]
        # Find shared column names across files (skip zero-row files)
        all_cols: set[str] = set()
        active_files = {f for f in self._file_col_types if self._file_row_count.get(f, 0) > 0}
        for fname in active_files:
            cols = self._file_col_types[fname]
            all_cols.update(cols.keys())
        for col in all_cols:
            types_found: dict[str, str] = {}
            for fname in active_files:
                cols = self._file_col_types[fname]
                if col in cols:
                    types_found[fname] = cols[col]
            # Compare types — if they differ, report
            unique_types = set(types_found.values())
            if len(unique_types) > 1:
                details = "; ".join(f"{f}={t}" for f, t in types_found.items())
                self._add_result(
                    "cross_file_types",
                    sev,
                    f"Type mismatch for '{col}': {details}",
                    from_sample=True,
                )

    def _check_encoding_validation(self, resolved: Path) -> None:
        """Probe the first 8 KB with ``utf-8-sig → utf-8``.

        Non-eligible paths return immediately with no finding and no
        ``ran_checks`` mutation (defensive guard for direct calls).  Only
        text-eligible files (``.csv``/``.tsv``) are probed; ``latin-1``/
        ``cp1252`` are not retried.
        """
        if not is_text_eligible(resolved):
            return
        if "encoding_validation" not in self._checks:
            return
        self._ran_checks.add("encoding_validation")
        sev = self._checks["encoding_validation"]["severity"]
        # Read first 8 KB and try each encoding
        try:
            chunk = resolved.read_bytes()[: config.PROBE_CHUNK_BYTES]
        except OSError:
            self._add_result("encoding_validation", sev, f"Cannot read '{resolved.name}'")
            return
        for enc in ENCODING_FALLBACKS:
            try:
                chunk.decode(enc)
                return  # success
            except (UnicodeDecodeError, UnicodeError):
                continue
        msg = f"Cannot decode '{resolved.name}' — all encodings failed"
        self._add_result("encoding_validation", sev, msg)

    # ------------------------------------------------------------------
    #  Cross-file type collection
    # ------------------------------------------------------------------

    def _infer_file_types(self, fname: str, header: list[str]) -> None:
        """Infer column types from collected samples for cross-file comparison."""
        for col_name in header:
            values = self._col_samples.get(col_name, [])
            filtered = [v for v in values if not _is_empty(v)]
            if filtered:
                self._file_col_types[fname][col_name] = infer_column_type(filtered)
            else:
                self._file_col_types[fname][col_name] = "unknown"


# ---------------------------------------------------------------------------
#  Quality report file writer (Issue #14)
# ---------------------------------------------------------------------------


def write_quality_report(report: ValidationReport, path: Path) -> None:
    """Write a ``quality-report.md`` file with findings grouped by severity.

    Args:
        report: The validation report from :meth:`QualityValidator.run`.
        path:   Output file path for the Markdown report.
    """
    lines: list[str] = []
    lines.append(f"# Quality Report — {report.name}")
    lines.append("")

    if not report.quality_results:
        lines.append("✅ No quality issues found.")
        path.write_text("\n".join(lines) + "\n", encoding=config.OUTPUT_ENCODING)
        return

    # Group by severity, then by check
    fail_findings = [r for r in report.quality_results if r.severity == "fail"]
    warn_findings = [r for r in report.quality_results if r.severity == "warn"]

    if fail_findings:
        lines.append("## ❌ Failures")
        lines.append("")
        for r in fail_findings:
            lines.append(f"- **{r.check}**: {r.message}")
        lines.append("")

    if warn_findings:
        lines.append("## [!] Warnings")
        lines.append("")
        for r in warn_findings:
            partial_note = " *(partial — sample-based)*" if r.partial else ""
            lines.append(f"- **{r.check}**: {r.message}{partial_note}")
        lines.append("")

    # Passed / skipped summary
    found = {r.check for r in report.quality_results}
    passed = len(report.ran_checks - found)
    skipped = len(QUALITY_CHECK_NAMES - report.ran_checks - found)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- {passed} check(s) passed with no findings")
    if skipped:
        lines.append(f"- {skipped} check(s) skipped (not configured)")
    lines.append(f"- {len(fail_findings)} failure(s)")
    lines.append(f"- {len(warn_findings)} warning(s)")

    path.write_text("\n".join(lines) + "\n", encoding=config.OUTPUT_ENCODING)
