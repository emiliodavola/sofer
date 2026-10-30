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
net for mislabeled ``.csv`` files containing binary bytes.  The probe reads at
most ``config.PROBE_CHUNK_BYTES`` of the file it judges (issue #326).
"""

from __future__ import annotations

import codecs
import csv
import hashlib
import os
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import config
from ._csv_reader import ENCODING_FALLBACKS, stream_csv
from ._formats import field_delimiter, is_text_eligible
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


_ROW_LENGTH_PREFIX_BYTES = 4
"""Width of the length prefix that frames each part of a row digest.

Four bytes frame a part of up to 4 GiB, far beyond any CSV cell the reader
materializes, and they make the concatenation unambiguous (issue #368).
"""


def _row_digest(file_identity: str, row: list[str]) -> str:
    """Return the duplicate-detection digest of one parsed row.

    The parts are length-framed before hashing, never joined with a separator:
    any chosen separator can occur inside a cell, so ``['a|b', 'c']`` and
    ``['a', 'b|c']`` produced the same preimage and two different rows were
    reported as exact duplicates (issue #368). Framing keeps field boundaries,
    empty fields, backslashes and Unicode content intact without normalizing
    any value, and two different rows cannot encode to the same bytes.

    MD5 stays: it is an equality fingerprint inside one scan, never a security
    primitive (``usedforsecurity=False``).

    Args:
        file_identity: The namespace the comparison is scoped to.
        row: The parsed field strings, exactly as the reader produced them.

    Returns:
        The hexadecimal digest of the framed parts.
    """
    digest = hashlib.md5(usedforsecurity=False)
    for part in (file_identity, *row):
        encoded = part.encode("utf-8")
        digest.update(len(encoded).to_bytes(_ROW_LENGTH_PREFIX_BYTES, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _source_identity(resolved: Path, base: Path) -> str:
    """Return the collision-free identity of one source (issue #369).

    A source under the dataset root is named by its dataset-relative POSIX
    path, which is stable across checkouts and readable in a report; one
    outside it keeps its resolved absolute POSIX path, which is equally
    unique. The identity is internal — what the report prints is decided by
    :func:`_display_names`.
    """
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return resolved.as_posix()


def _build_display_map(sources: Sequence[tuple[Path, str]]) -> dict[str, str]:
    """Map each source identity to the name the report should print.

    The basename stays the printed name while it is unambiguous, so every
    existing single-file message is unchanged. Identities that share a
    basename print their identity instead (``a/data.csv``), which is what lets
    an operator resolve a finding when two declared sources collide
    (issue #369).
    """
    by_basename: dict[str, list[str]] = defaultdict(list)
    for _resolved, identity in sources:
        by_basename[Path(identity).name].append(identity)
    display: dict[str, str] = {}
    for basename, identities in by_basename.items():
        for identity in identities:
            display[identity] = identity if len(identities) > 1 else basename
    return display


def _decodes_probe(chunk: bytes, encoding: str, *, final: bool) -> bool:
    """Return whether *chunk* decodes as *encoding*, tolerating a split tail.

    ``final`` says whether the probe reached physical end-of-file. When it did
    not, an incomplete sequence at the tail is completed by bytes this probe
    never reads, so the incremental decoder holds those bytes back instead of
    rejecting them (issue #370). Invalid bytes that are decidable inside the
    chunk still raise, and ``errors="strict"`` never hides them.

    Args:
        chunk: The bytes the probe read.
        encoding: One candidate encoding from ``ENCODING_FALLBACKS``.
        final: ``True`` when ``chunk`` ends at physical end-of-file.

    Returns:
        ``True`` when the chunk is decodable under the rule above.
    """
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    try:
        decoder.decode(chunk, final)
    except UnicodeError:
        return False
    return True


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

        # Resolve every source once: the identity keys all per-source
        # bookkeeping, and the display map can only tell an ambiguous basename
        # apart after seeing the whole declaration (issue #369).
        sources: list[tuple[Path, str]] = []
        for entry in self.cfg.files:
            resolved = entry.resolve(base)
            if not resolved.exists() or resolved.is_dir():
                continue
            if not is_text_eligible(resolved):
                continue
            sources.append((resolved, _source_identity(resolved, base)))
        self._display_names: dict[str, str] = _build_display_map(sources)

        for resolved, identity in sources:
            self._had_eligible = True

            # ── Pre-scan: encoding validation ──────────────────────────
            encoding_reported = self._check_encoding_validation(resolved)

            # ── Streaming pass — interleave all per-row checks ─────────
            self._process_file(
                resolved,
                identity=identity,
                display=self._display(identity),
                encoding_reported=encoding_reported,
            )

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
        # Per-source state: every mapping is keyed by the collision-free source
        # identity (``a/data.csv``), never by the basename (issue #369).
        self._file_headers: dict[str, list[str]] = {}
        self._file_row_count: dict[str, int] = {}
        # duplicates
        self._dup_hashes: dict[str, int] = {}  # hash → first row number
        # Duplicate pairs grouped by source: naming the source keeps the finding
        # traceable back to a table (issue #293), and capping each source's list
        # at the report limit keeps memory independent of the dataset size while
        # every affected source can still reach the report (issue #290).
        self._dup_findings: dict[str, list[tuple[int, int]]] = {}
        self._dup_hashes_capped: bool = False  # cap hit → finding is partial
        # empty rows
        self._empty_row_numbers: list[int] = []
        # empty columns — per-column "seen non-empty" boolean, keyed by the
        # structured pair (source, column): a path or a header may itself
        # contain any separator a compound string would use (issue #369).
        self._col_nonempty: dict[tuple[str, str], bool] = {}
        # null profiling
        self._null_counts: dict[tuple[str, str], tuple[int, int]] = {}
        # format consistency
        self._col_samples: dict[str, list[str]] = defaultdict(list)
        # cross-file types — this source's own bounded sample, dropped once its
        # types are inferred, so memory stays per-source rather than
        # per-dataset (issue #367)
        self._file_samples: dict[str, list[str]] = defaultdict(list)
        # corrupt records
        # (source, row, actual, expected)
        self._corrupt_findings: list[tuple[str, int, int, int]] = []
        # value range
        self._col_min: dict[str, float | None] = {}
        self._col_max: dict[str, float | None] = {}
        # cross-file types
        self._file_col_types: dict[str, dict[str, str]] = defaultdict(dict)
        # current source tracking
        self._current_source: str = ""
        self._current_display: str = ""
        self._current_header: list[str] = []
        # identity → the name the report uses (basename unless ambiguous)
        self._display_names = {}
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

    def _display(self, identity: str) -> str:
        """Return the name the report prints for *identity* (issue #369)."""
        return self._display_names.get(identity, Path(identity).name)

    def _process_file(
        self,
        resolved: Path,
        *,
        identity: str | None = None,
        display: str | None = None,
        encoding_reported: bool = False,
    ) -> None:
        """Open one CSV/TSV and distribute all rows to active accumulators.

        Non-eligible paths return immediately with no accumulator updates and
        no ``ran_checks`` mutation (defensive guard for direct calls).

        Rows are read with the separator the format defines: a ``.tsv`` is
        tab-delimited regardless of the dataset's CSV delimiter, and a ``.csv``
        keeps the configured one (issue #366).

        Args:
            resolved: The file to stream.
            identity: The collision-free identity all per-source bookkeeping is
                keyed by; a direct helper call falls back to the basename.
            display: The name findings print for this source.
            encoding_reported: ``True`` when :meth:`_check_encoding_validation`
                already appended a finding for this file, so a mid-stream
                decode failure is not reported a second time.
        """
        if not is_text_eligible(resolved):
            return
        self._file_samples = defaultdict(list)
        source = identity if identity is not None else resolved.name
        label = display if display is not None else resolved.name
        self._current_source = source
        self._current_display = label
        self._file_row_count[source] = 0

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
                delimiter=field_delimiter(resolved, self.cfg.csv_delimiter),
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
                f"Cannot read '{label}': {exc}",
            )
            return
        self._current_header = header
        self._file_headers[source] = header

        # Initialise per-column accumulators for this source's header
        for col_name in header:
            self._col_nonempty.setdefault((source, col_name), False)

        row_number = 0
        while True:
            try:
                _header, row = next(gen)
            except StopIteration:
                break
            except ValueError as exc:
                # The decoded prefix passed but the stream did not: a mislabeled
                # file whose first invalid byte sits past the probe window. It
                # must become a finding, never an exception out of ``run()``
                # (issue #370). When the probe already reported the file, the
                # same problem is not reported twice.
                if not encoding_reported:
                    self._add_result(
                        "corrupt_records",
                        "fail",
                        f"Cannot read '{label}': {exc}",
                    )
                return
            if row is None:  # header-only yield already consumed
                continue
            row_number += 1
            self._file_row_count[source] = row_number
            self._distribute_row(row_number, row)

        # After the source is processed, infer column types for cross-file comparison
        self._infer_file_types(source, header)
        self._file_samples = defaultdict(list)

    def _distribute_row(self, row_number: int, row: list[str]) -> None:
        """Send one data row to every active per-row accumulator."""
        # corrupt_records — needs raw row length first
        if "corrupt_records" in self._checks:
            if len(row) != len(self._current_header):
                _capped_append(
                    self._corrupt_findings,
                    (self._current_source, row_number, len(row), len(self._current_header)),
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
                self._col_nonempty[(self._current_source, col_name)] = True

            # null_profiling
            key_n = (self._current_source, col_name)
            if key_n in self._null_counts:
                t, n = self._null_counts[key_n]
                self._null_counts[key_n] = (t + 1, n + (1 if is_missing else 0))
            else:
                self._null_counts[key_n] = (1, 1 if is_missing else 0)

            # format_consistency — collect values (capped)
            if "format_consistency" in self._checks:
                if len(self._col_samples[col_name]) < self._max_sample:
                    self._col_samples[col_name].append(value)

            # cross_file_types — this source's own bounded sample (issue #367).
            # Independent of format_consistency: inferring a source's types must
            # not depend on an unrelated dataset-level check being active.
            if "cross_file_types" in self._checks:
                if len(self._file_samples[col_name]) < self._max_sample:
                    self._file_samples[col_name].append(value)

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
            h = _row_digest(self._current_source, row)
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
        pairs = self._dup_findings.setdefault(self._current_source, [])
        _capped_append(pairs, (first_row, dup_row), config.REPORT_MAX_ITEMS)

    def _check_duplicates(self) -> None:
        """Emit the ``duplicates`` finding, attributed to the file it came from.

        The row hash is namespaced per file, so a bare row number is not
        resolvable from the report — every pair names its file (issue #293).
        Pairs are taken round-robin across files so one noisy file cannot spend
        the whole ``REPORT_MAX_ITEMS`` budget and hide the other affected files,
        and when the hash-tracking cap was hit the finding is marked partial and
        the cap is named (issue #290).

        ``min_unique`` (issue #399) turns the check into a repetition guard: the
        batch must hold at least that many distinct records. The unit is the
        same ``(source, row)`` hash the pairs use, so identical rows in two
        different files still count as two records (issue #368). A capped hash
        table cannot prove the count, so that case is reported as partial rather
        than guessed.
        """
        if "duplicates" not in self._checks:
            return
        if not self._had_eligible:
            return
        self._ran_checks.add("duplicates")
        sev = self._checks["duplicates"]["severity"]

        min_unique = self._checks["duplicates"].get("min_unique")
        if min_unique is not None:
            distinct = len(self._dup_hashes)
            if self._dup_hashes_capped:
                self._add_result(
                    "duplicates",
                    sev,
                    f"Distinct records: at least {distinct}; tracking capped at "
                    f"{self._dup_tracking_cap}, so min_unique {min_unique} is not verifiable",
                    from_sample=True,
                    partial=True,
                )
            elif distinct < min_unique:
                self._add_result(
                    "duplicates",
                    sev,
                    f"Distinct records: {distinct} < min_unique {min_unique}",
                    from_sample=True,
                )

        if not self._dup_findings and not self._dup_hashes_capped:
            return
        limit = config.REPORT_MAX_ITEMS
        parts: list[str] = []
        for depth in range(max((len(p) for p in self._dup_findings.values()), default=0)):
            if len(parts) >= limit:
                break
            for source, pairs in self._dup_findings.items():
                if depth < len(pairs) and len(parts) < limit:
                    first, dup = pairs[depth]
                    parts.append(f"{self._display(source)}: Row {first} = Row {dup}")
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
        # Group empty columns per source using the structured (source, col) key
        per_source: dict[str, list[str]] = defaultdict(list)
        for (source, col), seen_nonempty in self._col_nonempty.items():
            if not seen_nonempty:
                per_source[source].append(col)
        if not per_source:
            return
        sev = self._checks["empty_columns"]["severity"]
        for source, cols in per_source.items():
            # Skip zero-row sources — a header-only file has no data to check
            if self._file_row_count.get(source, 0) == 0:
                continue
            self._add_result(
                "empty_columns",
                sev,
                f"Fully empty columns in '{self._display(source)}': {', '.join(cols)}",
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
        # Aggregate across sources per column (dataset-level statistic): the
        # structured key makes the source part explicit, so no separator in a
        # path or a header can be mistaken for the boundary (issue #369).
        agg: dict[str, tuple[int, int]] = {}
        for (_source, col), (total, nulls) in self._null_counts.items():
            if col in agg:
                prev_total, prev_nulls = agg[col]
                agg[col] = (prev_total + total, prev_nulls + nulls)
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
        for source, row, actual, expected in self._corrupt_findings[:limit]:
            self._add_result(
                "corrupt_records",
                sev,
                f"Row {row} in '{self._display(source)}' has {actual} fields, "
                f"header has {expected}",
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
        # Find shared column names across sources (skip zero-row sources)
        all_cols: set[str] = set()
        active_files = {f for f in self._file_col_types if self._file_row_count.get(f, 0) > 0}
        for source in active_files:
            cols = self._file_col_types[source]
            all_cols.update(cols.keys())
        for col in all_cols:
            types_found: dict[str, str] = {}
            for source in active_files:
                cols = self._file_col_types[source]
                if col in cols:
                    types_found[source] = cols[col]
            # Compare types — if they differ, report
            unique_types = set(types_found.values())
            if len(unique_types) > 1:
                details = "; ".join(
                    f"{self._display(source)}={kind}" for source, kind in types_found.items()
                )
                self._add_result(
                    "cross_file_types",
                    sev,
                    f"Type mismatch for '{col}': {details}",
                    from_sample=True,
                )

    def _check_encoding_validation(self, resolved: Path) -> bool:
        """Probe the first ``config.PROBE_CHUNK_BYTES`` with ``utf-8-sig → utf-8``.

        Non-eligible paths return immediately with no finding and no
        ``ran_checks`` mutation (defensive guard for direct calls).  Only
        text-eligible files (``.csv``/``.tsv``) are probed; ``latin-1``/
        ``cp1252`` are not retried.

        The prefix is read with a **bounded** read (issue #326): the probe only
        answers a question about the file's first ``probe_chunk_bytes``, so
        materializing the file to slice it made the pass's peak follow the
        corpus size (1:1 on a 63 MiB CSV) instead of the configured width.

        What the judged prefix proves (issue #370): a sequence cut by the
        window is completed by bytes the probe deliberately does not read, so
        it is not evidence of a bad encoding; only a sequence cut by physical
        end-of-file is.  The file's size, read from the open descriptor, tells
        the two apart without a second read, which keeps the bound intact.

        Returns:
            ``True`` when a finding was appended for this file, so the caller
            can avoid reporting the same decode failure twice; ``False`` when
            the file passed, was skipped, or held no active check.
        """
        if not is_text_eligible(resolved):
            return False
        if "encoding_validation" not in self._checks:
            return False
        self._ran_checks.add("encoding_validation")
        sev = self._checks["encoding_validation"]["severity"]
        # Read the first probe-sized chunk and learn whether it reached EOF
        try:
            with resolved.open("rb") as fh:
                chunk = fh.read(config.PROBE_CHUNK_BYTES)
                size = os.fstat(fh.fileno()).st_size
        except OSError:
            self._add_result("encoding_validation", sev, f"Cannot read '{resolved.name}'")
            return True
        final = len(chunk) >= size
        for enc in ENCODING_FALLBACKS:
            if _decodes_probe(chunk, enc, final=final):
                return False  # success
        msg = f"Cannot decode '{resolved.name}' — all encodings failed"
        self._add_result("encoding_validation", sev, msg)
        return True

    # ------------------------------------------------------------------
    #  Cross-file type collection
    # ------------------------------------------------------------------

    def _infer_file_types(self, source: str, header: list[str]) -> None:
        """Infer column types from *source*'s own samples for cross-file comparison.

        The sample belongs to the source being streamed, so an earlier source
        that fills the configured budget cannot decide a later one's type
        (issue #367). Missing values are filtered before inference, and a
        column with no non-missing value stays ``"unknown"``.
        """
        for col_name in header:
            values = self._file_samples.get(col_name, [])
            filtered = [v for v in values if not _is_empty(v)]
            if filtered:
                self._file_col_types[source][col_name] = infer_column_type(filtered)
            else:
                self._file_col_types[source][col_name] = "unknown"


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
