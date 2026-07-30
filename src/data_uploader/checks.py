"""
Data integrity checks.

This module runs **before** any upload and validates that the local data
matches the declared configuration — file existence, size, CSV schema, etc.

The :class:`DatasetValidator` is generic: it works for any dataset described
by a :class:`DatasetConfig`.  Custom per-dataset checks can be added later
without modifying this module.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .model import DatasetConfig, QualityResult


class ValidationReport:
    """Result of a full validation run.

    Attributes:
        name:     Dataset name (for display).
        errors:   List of hard failures that should block upload.
        warnings: Advisory messages that don't block upload.
    """

    def __init__(self, name: str):
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.quality_results: list[QualityResult] = []

    @property
    def passed(self) -> bool:
        """True when there are zero errors and zero fail-severity quality results."""
        if self.errors:
            return False
        if any(r.severity == "fail" for r in self.quality_results):
            return False
        return True

    def print_summary(self) -> None:
        """Print a human-readable summary to stdout."""
        print(f"\n  Validation report: {self.name}")
        print(f"  {'─' * 50}")
        print(f"  Errors:   {len(self.errors)}")
        for e in self.errors:
            print(f"    ✗  {e}")
        print(f"  Warnings: {len(self.warnings)}")
        for w in self.warnings:
            print(f"    ⚠  {w}")
        if self.quality_results:
            print(f"  {'─' * 30}")
            q_errors = [r for r in self.quality_results if r.severity == "fail"]
            q_warnings = [r for r in self.quality_results if r.severity == "warn"]
            q_passed = _count_passed_quality(self.quality_results)
            print("  Quality checks")
            print(f"  Errors:   {len(q_errors)}")
            for r in q_errors:
                print(f"    ✗  {r.check}: {r.message}")
            print(f"  Warnings: {len(q_warnings)}")
            for r in q_warnings:
                print(f"    ⚠  {r.check}: {r.message}")
            q_summary = f"{q_passed} passed, {len(q_errors)} failed, {len(q_warnings)} warnings"
            print(f"  ✓  Quality: {q_summary}")
        if self.passed and not self.quality_results:
            print("  ✓  All checks passed.\n")
        elif self.passed:
            print()
        else:
            print()


def _count_passed_quality(results: list[QualityResult]) -> int:
    """Count how many check *types* have zero findings of any severity.

    A check type (e.g. ``"duplicates"``) is considered "passed" when there
    is no ``QualityResult`` with that check name.  We compute this by
    subtracting unique check names that *did* produce results from the total
    known check types.
    """
    # Known check types per the built-in defaults
    all_check_types = {
        "duplicates",
        "empty_rows",
        "empty_columns",
        "null_profiling",
        "format_consistency",
        "corrupt_records",
        "value_range",
        "cross_file_types",
        "encoding_validation",
    }
    found = {r.check for r in results}
    return len(all_check_types - found)


class DatasetValidator:
    """Runs all built-in checks against a dataset.

    Args:
        cfg: The parsed dataset configuration.
    """

    def __init__(self, cfg: DatasetConfig):
        self.cfg = cfg
        self.report = ValidationReport(cfg.name)

    # ── individual checks ─────────────────────────────────────────────

    def _check_files_exist(self) -> None:
        """Fail if any declared file/directory is missing."""
        base = self.cfg._base_dir if self.cfg._base_dir else Path.cwd()
        for entry in self.cfg.files:
            resolved = entry.resolve(base)
            if not resolved.exists():
                self.report.errors.append(f"Missing: {resolved}")

    def _check_min_files(self) -> None:
        """Fail if fewer file entries than configured."""
        if len(self.cfg.files) < self.cfg.min_files:
            self.report.errors.append(
                f"Expected ≥ {self.cfg.min_files} file entries, got {len(self.cfg.files)}."
            )

    def _check_total_size(self) -> None:
        """Warn if total data size is below the configured threshold."""
        if self.cfg.min_total_size_mb == 0:
            return
        total_mb = 0.0
        base = self.cfg._base_dir if self.cfg._base_dir else Path.cwd()
        for entry in self.cfg.files:
            resolved = entry.resolve(base)
            if resolved.exists() and not resolved.is_dir():
                total_mb += resolved.stat().st_size / (1024 * 1024)
        if total_mb < self.cfg.min_total_size_mb:
            self.report.warnings.append(
                f"Total size {total_mb:.1f} MB is below the "
                f"configured minimum of {self.cfg.min_total_size_mb} MB."
            )

    def _check_csv_columns(self) -> None:
        """Fail when expected columns are missing from a CSV.

        The file is located by matching its remote path against the
        file entries declared in the TOML.
        """
        base = self.cfg._base_dir if self.cfg._base_dir else Path.cwd()
        for col_check in self.cfg.column_checks:
            # find the matching file entry
            matched: Path | None = None
            for entry in self.cfg.files:
                resolved = entry.resolve(base)
                if resolved.name == col_check.filename or entry.remote == col_check.filename:
                    matched = resolved
                    break
            # _check_files_exist already handles absolute vs relative
            if matched is None or not matched.exists():
                self.report.warnings.append(
                    f"Cannot check columns for '{col_check.filename}': "
                    f"file not found among entries."
                )
                continue

            try:
                with open(matched, newline="", encoding="utf-8-sig") as fh:
                    reader = csv.reader(fh, delimiter=";")
                    headers = [h.strip().lower() for h in next(reader)]
            except Exception as exc:
                self.report.warnings.append(f"Cannot read '{matched.name}': {exc}")
                continue

            missing = [col for col in col_check.expected if col.lower() not in headers]
            if missing:
                self.report.errors.append(f"Columns missing in {matched.name}: {missing}")

    # ── run all ───────────────────────────────────────────────────────

    def run_all(self) -> ValidationReport:
        """Execute every built-in check and return the report."""
        self._check_files_exist()
        self._check_min_files()
        self._check_total_size()
        self._check_csv_columns()
        return self.report
