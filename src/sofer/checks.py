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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import config
from .model import QUALITY_CHECK_NAMES, DatasetConfig, QualityResult
from .repo_compliance import normalize_header
from .scanner import raw_source_for_local

_META_PLACEHOLDER_FIELDS: tuple[str, ...] = ("description", "license", "source")
"""The ``[meta]`` scalar fields the agent-facing gate inspects (issue #288).

The set the ``sofer init`` template fills with placeholders; ``tags`` is checked
separately because it is a list.
"""


def _looks_like_placeholder(text: str, prefixes: tuple[str, ...]) -> bool:
    """Return True when *text* is empty or opens with a template prefix.

    Args:
        text: The candidate value, already stripped.
        prefixes: Lower-cased prefixes that mark a template placeholder.

    Returns:
        ``True`` for an empty value, or one beginning with a prefix.
    """
    return not text or text.lower().startswith(prefixes)


def meta_placeholder_warnings(cfg: DatasetConfig) -> list[str]:
    """Return warnings for ``[meta]`` fields still carrying template placeholders.

    ``sofer init`` writes a TOML whose ``[meta]`` block is all placeholders, and
    nothing in the pipeline said they had to be replaced: they travelled through
    validate, prepare, codebook_all, profile_all and render_all with every
    envelope reporting ``ok: true``, and the only way to notice was to read the
    generated Dataset Card (issue #288). An MCP consumer has no other source of
    truth than the tool descriptions and envelopes, so the check belongs in the
    surface those carry.

    The force is deliberately a **warning** (maintainer decision D3): a failure
    would break every existing config that still carries a placeholder, which is
    a contract change rather than a fix. A warning reaches the agent through the
    envelope while leaving the run's exit code alone.

    Args:
        cfg: Dataset configuration.

    Returns:
        One message per offending field, in a fixed order; ``[]`` when every
        inspected field carries a real value.
    """
    return meta_placeholder_warnings_for(
        {
            "description": cfg.description,
            "license": cfg.license,
            "source": cfg.source,
            "tags": cfg.tags,
        }
    )


def meta_placeholder_warnings_for(values: Mapping[str, Any]) -> list[str]:
    """Return the placeholder warnings for one ``[meta]`` mapping.

    The same implementation :func:`meta_placeholder_warnings` delegates to, so
    the validator and the tools that write ``[meta]`` cannot disagree about what
    a placeholder is (AGENTS.md rule 4). Taking the mapping directly is what lets
    ``sofer_meta_set`` report the state its own edit would leave behind — computed
    from the resulting table in hand, never from a re-read of the file, so a
    ``dry_run`` reports the planned state rather than the current one.

    A missing or ``None`` value is treated exactly as an empty string, and a
    non-list ``tags`` as no tags, because the mapping may come from an operator's
    TOML or from an edit in progress.

    Args:
        values: The ``[meta]`` table as a mapping.

    Returns:
        One message per offending field, in a fixed order; ``[]`` when every
        inspected field carries a real value.
    """
    prefixes = tuple(p.lower() for p in config.META_PLACEHOLDER_PREFIXES)
    warnings: list[str] = []
    for field_name in _META_PLACEHOLDER_FIELDS:
        raw = values.get(field_name) or ""
        text = str(raw).strip()
        if _looks_like_placeholder(text, prefixes):
            shown = text or "(empty)"
            warnings.append(
                f"[meta] {field_name} still looks like a template placeholder "
                f"({shown!r}): replace it before prepare, or the generated Dataset "
                f"Card and LICENSE ship the placeholder."
            )
    tags = values.get("tags")
    raw_tags: list[Any] = tags if isinstance(tags, list) else []
    placeholder_tags = [
        str(t) for t in raw_tags if _looks_like_placeholder(str(t).strip(), prefixes)
    ]
    if placeholder_tags:
        warnings.append(
            f"[meta] tags still look like template placeholders "
            f"({', '.join(repr(t) for t in placeholder_tags)}): replace them before "
            f"prepare, or the generated card advertises placeholder tags."
        )
    return warnings


class ValidationReport:
    """Result of a full validation run.

    Attributes:
        name:     Dataset name (for display).
        errors:   List of hard failures that should block upload.
        warnings: Advisory messages that don't block upload.
        quality_results: Per-check quality findings.
        ran_checks:      Set of check names that actually executed (Issue #14).
    """

    def __init__(self, name: str):
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.quality_results: list[QualityResult] = []
        self.ran_checks: set[str] = set()

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
        print(f"  {'-' * config.REPORT_LINE_WIDTH}")
        print(f"  Errors:   {len(self.errors)}")
        for e in self.errors:
            print(f"    X  {e}")
        print(f"  Warnings: {len(self.warnings)}")
        for w in self.warnings:
            print(f"    WARN  {w}")
        if self.quality_results:
            print(f"  {'-' * config.REPORT_SUB_LINE_WIDTH}")
            q_errors = [r for r in self.quality_results if r.severity == "fail"]
            q_warnings = [r for r in self.quality_results if r.severity == "warn"]
            q_passed, q_skipped = _count_passed_quality(self.quality_results, self.ran_checks)
            print("  Quality checks")
            print(f"  Errors:   {len(q_errors)}")
            for r in q_errors:
                print(f"    X  {r.check}: {r.message}")
            print(f"  Warnings: {len(q_warnings)}")
            for r in q_warnings:
                partial_note = " (partial)" if r.partial else ""
                print(f"    WARN  {r.check}: {r.message}{partial_note}")
            parts = [f"{q_passed} passed"]
            if q_skipped > 0:
                parts.append(f"{q_skipped} skipped")
            parts.append(f"{len(q_errors)} failed")
            parts.append(f"{len(q_warnings)} warnings")
            q_summary = ", ".join(parts)
            print(f"  OK  Quality: {q_summary}")
        if self.passed and not self.quality_results:
            print("  OK  All checks passed.\n")
        elif self.passed:
            print()
        else:
            print()


def _count_passed_quality(
    results: list[QualityResult],
    ran_checks: set[str],
) -> tuple[int, int]:
    """Count how many checks passed vs were skipped.

    A check is "passed" when it actually ran and produced no findings.
    A check is "skipped" when it was never executed (e.g., value_range
    without config).

    Returns:
        (passed, skipped) tuple.
    """
    found = {r.check for r in results}
    passed = len(ran_checks - found)
    skipped = len(QUALITY_CHECK_NAMES - ran_checks - found)
    return (passed, skipped)


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

    def _check_cache_only_registrations(self) -> None:
        """Fail when a ``cache/``-registered file has no source under ``raw/``.

        ``cache/`` (``OUTPUT_DIR``) is the tool-wide, sibling-shared staging
        directory that ``publish --clean --clean-cache`` deletes, so a
        ``[[file]]`` entry that points there with no matching ``raw/`` source has
        an untracked source: one authorized cleanup destroys the only copy
        (issue #339). The error names the expected ``raw/`` path and the repair.
        """
        base = self.cfg._base_dir if self.cfg._base_dir else Path.cwd()
        data_dir = base / config.OUTPUT_DIR
        raw_dir = base / config.RAW_DIR
        for entry in self.cfg.files:
            source = raw_source_for_local(entry.local, base, raw_dir, data_dir)
            if source is None or source.exists():
                continue
            self.report.errors.append(
                f"{entry.local.as_posix()} is registered from {config.OUTPUT_DIR}/ "
                f"(disposable) but its "
                f"source {source.relative_to(base).as_posix()} does not exist — re-run scan so "
                f"{config.RAW_DIR}/ holds the source, or delete the stale [[file]] entry."
            )

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
                with open(matched, newline="", encoding=self.cfg.csv_encoding) as fh:
                    reader = csv.reader(fh, delimiter=self.cfg.csv_delimiter)
                    headers = [normalize_header(h).lower() for h in next(reader)]
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
        # Tracked-source gate (issue #339): a [[file]] entry registered from the
        # disposable cache/ with no raw/ source is one cleanup away from losing
        # its only copy, so it is an error, not a warning.
        self._check_cache_only_registrations()
        self._check_min_files()
        self._check_total_size()
        self._check_csv_columns()
        # Agent-facing metadata gate (issue #288): a placeholder in [meta] is a
        # warning, so it never changes the exit code, but it reaches the CLI
        # summary and the MCP envelope that would otherwise report ok: true.
        self.report.warnings.extend(meta_placeholder_warnings(self.cfg))
        return self.report
