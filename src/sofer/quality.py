"""
Data-quality checks for CSV content.

The :class:`QualityValidator` runs all active P0 checks in a **single pass**
per file — each CSV is opened once and every row is distributed to all active
accumulators simultaneously.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from ._csv_reader import ENCODING_FALLBACKS, stream_csv
from ._sentinels import MISSING_VALUE_SENTINELS
from .checks import ValidationReport
from .codebook import infer_column_type
from .config import (
    OUTPUT_ENCODING,
    PROBE_CHUNK_BYTES,
    REPORT_MAX_CORRUPT_RECORDS,
    REPORT_MAX_ITEMS,
)
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

        # ── Accumulator state (reset per run) ───────────────────────────
        self._reset_accumulators()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def run(self) -> ValidationReport:
        """Execute every active quality check across all CSV files.

        Returns:
            A :class:`ValidationReport` whose ``quality_results`` list holds
            every finding.
        """
        self._reset_accumulators()
        base = self.cfg._base_dir if self.cfg._base_dir else Path.cwd()

        for entry in self.cfg.files:
            resolved = entry.resolve(base)
            if not resolved.exists() or resolved.is_dir():
                continue

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
        # Per-file state
        self._file_headers: dict[str, list[str]] = {}
        self._file_row_count: dict[str, int] = {}
        # duplicates
        self._dup_hashes: dict[str, int] = {}  # hash → first row number
        self._dup_findings: list[tuple[int, int]] = []  # (first_row, dup_row)
        # empty rows
        self._empty_row_numbers: list[int] = []
        # empty columns — initialised per file in _process_file
        self._col_nonempty: dict[str, set[str]] = defaultdict(set)
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

    def _has_fail_checks(self) -> bool:
        """Return True when any active check has ``fail`` severity."""
        return any(cfg.get("severity") == "fail" for cfg in self._checks.values())

    # ------------------------------------------------------------------
    #  File processing (single pass, interleaved)
    # ------------------------------------------------------------------

    def _process_file(self, resolved: Path) -> None:
        """Open one CSV and distribute all rows to active accumulators."""
        fname = resolved.name
        self._current_file = fname
        self._file_row_count[fname] = 0

        # Fail-severity checks always scan the full file (Issue #14)
        effective_max_sample: int | None = self._max_sample
        if self._has_fail_checks():
            effective_max_sample = None
        elif self._max_sample is not None:
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
            _ = self._col_nonempty[f"{fname}::{col_name}"]  # ensure entry exists

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
                self._corrupt_findings.append(
                    (self._current_file, row_number, len(row), len(self._current_header))
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

            # empty_columns — track if we've seen any non-empty value
            # Key with file prefix to isolate per-file (Issue #14)
            if not is_missing:
                self._col_nonempty[f"{self._current_file}::{col_name}"].add(value[:50])

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

        # duplicates — hash the entire row (scoped per file to avoid cross-file false positives)
        if "duplicates" in self._checks:
            row_str = f"{self._current_file}|{'|'.join(row)}"
            h = hashlib.md5(row_str.encode("utf-8"), usedforsecurity=False).hexdigest()
            if h in self._dup_hashes:
                self._dup_findings.append((self._dup_hashes[h], row_number))
            else:
                self._dup_hashes[h] = row_number

        # empty_rows
        if not has_any_nonempty:
            self._empty_row_numbers.append(row_number)

    # ------------------------------------------------------------------
    #  Post-scan check methods (produce QualityResult entries)
    # ------------------------------------------------------------------

    def _add_result(self, check: str, severity: str, message: str) -> None:
        partial = False
        if severity == "warn" and self._scan_is_partial:
            partial = True
        self._results.append(
            QualityResult(check=check, severity=severity, message=message, partial=partial)
        )
        # Track that this check actually ran (Issue #14)
        self._ran_checks.add(check)

    def _check_duplicates(self) -> None:
        if "duplicates" not in self._checks:
            return
        self._ran_checks.add("duplicates")
        if not self._dup_findings:
            return
        pairs = "; ".join(f"Row {a} = Row {b}" for a, b in self._dup_findings[:REPORT_MAX_ITEMS])
        sev = self._checks["duplicates"]["severity"]
        self._add_result("duplicates", sev, f"Duplicate rows: {pairs}")

    def _check_empty_rows(self) -> None:
        if "empty_rows" not in self._checks:
            return
        self._ran_checks.add("empty_rows")
        if not self._empty_row_numbers:
            return
        sample = ", ".join(str(r) for r in self._empty_row_numbers[:REPORT_MAX_ITEMS])
        sev = self._checks["empty_rows"]["severity"]
        self._add_result("empty_rows", sev, f"Empty rows: {sample}")

    def _check_empty_columns(self) -> None:
        if "empty_columns" not in self._checks:
            return
        self._ran_checks.add("empty_columns")
        # Group empty columns per-file using the "fname::col" key format
        per_file: dict[str, list[str]] = defaultdict(list)
        for key, vals in self._col_nonempty.items():
            if not vals:
                if "::" in key:
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
            )

    def _check_null_profiling(self) -> None:
        if "null_profiling" not in self._checks:
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
        self._add_result("null_profiling", sev, msg)

    def _check_format_consistency(self) -> None:
        if "format_consistency" not in self._checks:
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
        self._add_result("format_consistency", sev, f"Mixed-type columns: {', '.join(mixed_cols)}")

    def _check_corrupt_records(self) -> None:
        if "corrupt_records" not in self._checks:
            return
        self._ran_checks.add("corrupt_records")
        if not self._corrupt_findings:
            return
        sev = self._checks["corrupt_records"]["severity"]
        for fname, row, actual, expected in self._corrupt_findings[:REPORT_MAX_CORRUPT_RECORDS]:
            self._add_result(
                "corrupt_records",
                sev,
                f"Row {row} in '{fname}' has {actual} fields, header has {expected}",
            )

    def _check_value_range(self) -> None:
        if "value_range" not in self._checks:
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
            self._add_result("value_range", sev, f"Out of range — {msg}")

    def _check_cross_file_types(self) -> None:
        if "cross_file_types" not in self._checks:
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
                self._add_result("cross_file_types", sev, f"Type mismatch for '{col}': {details}")

    def _check_encoding_validation(self, resolved: Path) -> None:
        if "encoding_validation" not in self._checks:
            return
        self._ran_checks.add("encoding_validation")
        sev = self._checks["encoding_validation"]["severity"]
        # Read first 8 KB and try each encoding
        try:
            chunk = resolved.read_bytes()[:PROBE_CHUNK_BYTES]
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
        path.write_text("\n".join(lines) + "\n", encoding=OUTPUT_ENCODING)
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

    path.write_text("\n".join(lines) + "\n", encoding=OUTPUT_ENCODING)
