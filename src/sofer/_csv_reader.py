"""
Shared streaming CSV reader with encoding fallback.

Provides :func:`stream_csv`, a generator that yields ``(header, row)`` tuples
and handles encoding detection by trying a fallback chain:
``utf-8-sig → utf-8``.
"""

from __future__ import annotations

import csv
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config

_UNSET: Any = object()
"""Sentinel distinguishing "parameter not given" from an explicit ``None``.

An explicit ``max_sample=None`` legitimately means "scan the entire file"
(used by fail-severity quality checks, Issue #14), so the config-default
resolution needs its own marker — a plain ``None`` default would conflate
the two and silently cap full scans at ``codebook_max_sample``.
"""

ENCODING_FALLBACKS = ["utf-8-sig", "utf-8"]
"""Ordered list of UTF-8 encodings tried when opening a CSV file.

    Non-UTF-8 files are rejected — the quality gate enforces UTF-8 before
    upload, so the reader should never encounter latin-1/cp1252 content.
    """


def stream_csv(
    path: Path,
    delimiter: str | Any = _UNSET,
    encoding: str | Any = _UNSET,
    max_sample: int | Any | None = _UNSET,
) -> Generator[tuple[list[str], list[str] | None], None, None]:
    """Yield ``(header, row)`` tuples from a CSV file, one at a time.

    The first yield always carries ``row=None`` (the header row only).
    Subsequent yields carry parsed data rows as ``list[str]``.

    Encoding fallback chain (tried in order):
    ``utf-8-sig → utf-8``.  Non-UTF-8 files raise ``ValueError``.

    Args:
        path:       Path to the CSV file.
        delimiter:  CSV field delimiter (default: ``csv_delimiter`` from
                    ``[tool.sofer]``, resolved at call time).
        encoding:   Initial encoding to try (default: ``csv_encoding`` from
                    ``[tool.sofer]``, resolved at call time).
        max_sample: Maximum number of data rows to yield. Omit for the
                    ``codebook_max_sample`` value from ``[tool.sofer]``
                    (resolved at call time); pass ``None`` explicitly to
                    scan the entire file.

    Yields:
        ``(header, row)`` tuples. The first yield has ``row=None``.

    Raises:
        ValueError: When none of the encoding fallbacks succeed.
    """
    # Resolve unset parameters through the config module at call time so a
    # reload between import and call is honored (never freeze at def time).
    if delimiter is _UNSET:
        delimiter = config.CSV_DELIMITER
    if encoding is _UNSET:
        encoding = config.CSV_ENCODING
    if max_sample is _UNSET:
        max_sample = config.CODEBOOK_MAX_SAMPLE

    # Ensure encoding is the first in the chain
    fallbacks = _build_fallback_chain(encoding)

    # Try each encoding in order
    last_error: Exception | None = None
    for enc in fallbacks:
        try:
            yield from _read_csv(path, delimiter, enc, max_sample)
            return
        except (UnicodeDecodeError, UnicodeError, csv.Error) as exc:
            last_error = exc
            continue

    msg = f"Cannot decode '{path.name}' — all encodings exhausted."
    raise ValueError(msg) from last_error


@dataclass(frozen=True)
class ColumnarRead:
    """One CSV/TSV read transposed into columns, with its row-width report.

    ``profile`` and ``codebook`` document the same file and used to disagree
    about ragged rows: the codebook padded a short row with ``""`` while the
    profile simply skipped the missing field, so the same column reported
    33.3% and 0.0% missing (issue #395). Both now go through
    :func:`read_columns`, so the numbers cannot drift apart.

    Attributes:
        headers: Header row, in file order.
        columns: One value list per header, all of length ``rows`` (a short
            row contributes ``""``, a long row is truncated).
        rows: Data rows read (bounded by *max_sample* when given).
        ragged_padded: Rows with fewer fields than the header, padded with ``""``.
        ragged_truncated: Rows with more fields than the header, truncated.
        extra_fields_dropped: Total fields discarded by that truncation.
    """

    headers: list[str]
    columns: list[list[str]]
    rows: int
    ragged_padded: int
    ragged_truncated: int
    extra_fields_dropped: int

    @property
    def is_ragged(self) -> bool:
        """Whether any row did not match the header width."""
        return bool(self.ragged_padded or self.ragged_truncated)


def read_columns(
    path: Path,
    *,
    delimiter: str | Any = _UNSET,
    encoding: str | Any = _UNSET,
    max_sample: int | Any | None = _UNSET,
) -> ColumnarRead:
    """Read *path* into columns under one explicit row-width policy.

    The policy every documentation consumer shares (issue #395): keep every
    data row, pad a short row with ``""`` and truncate a long one, and count
    both so the artifact can say what happened. A fallback-encoding restart
    (the reader re-yields the header) resets the accumulators instead of
    doubling the rows.

    Args:
        path: Path to the CSV/TSV file.
        delimiter: Field delimiter (default resolved from ``[tool.sofer]``).
        encoding: First encoding tried (default resolved from ``[tool.sofer]``).
        max_sample: Maximum data rows to read; ``None`` scans the whole file.

    Returns:
        A :class:`ColumnarRead`. An empty or headerless file yields empty
        headers and zero rows.

    Raises:
        ValueError: When none of the encoding fallbacks succeed.
    """
    headers: list[str] = []
    columns: list[list[str]] = []
    rows = ragged_padded = ragged_truncated = extra_fields_dropped = 0

    for header, row in stream_csv(
        path, delimiter=delimiter, encoding=encoding, max_sample=max_sample
    ):
        if row is None:
            headers = list(header)
            columns = [[] for _ in headers]
            rows = ragged_padded = ragged_truncated = extra_fields_dropped = 0
            continue
        width = len(columns)
        rows += 1
        if len(row) < width:
            ragged_padded += 1
        elif len(row) > width:
            ragged_truncated += 1
            extra_fields_dropped += len(row) - width
        for index in range(width):
            columns[index].append(row[index] if index < len(row) else "")

    return ColumnarRead(
        headers=headers,
        columns=columns,
        rows=rows,
        ragged_padded=ragged_padded,
        ragged_truncated=ragged_truncated,
        extra_fields_dropped=extra_fields_dropped,
    )


def _build_fallback_chain(start_encoding: str) -> list[str]:
    """Build the full fallback chain, deduplicating if *start_encoding* is
    already in the default list."""
    chain = [start_encoding]
    for enc in ENCODING_FALLBACKS:
        if enc not in chain:
            chain.append(enc)
    return chain


def _read_csv(
    path: Path,
    delimiter: str,
    encoding: str,
    max_sample: int | None,
) -> Generator[tuple[list[str], list[str] | None], None, None]:
    """Read a CSV with the given encoding and yield (header, row) tuples."""
    with open(path, newline="", encoding=encoding) as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            # Completely empty file
            yield [], None
            return

        yield header, None  # header-only yield

        if max_sample is None:
            yield from ((header, row) for row in reader)
        else:
            count = 0
            for row in reader:
                if count >= max_sample:
                    return
                yield header, row
                count += 1
