"""
Shared streaming CSV reader with encoding fallback.

Provides :func:`stream_csv`, a generator that yields ``(header, row)`` tuples
and handles encoding detection by trying a fallback chain:
``utf-8-sig → utf-8``.
"""

from __future__ import annotations

import csv
from collections.abc import Generator
from pathlib import Path

ENCODING_FALLBACKS = ["utf-8-sig", "utf-8"]
"""Ordered list of UTF-8 encodings tried when opening a CSV file.

    Non-UTF-8 files are rejected — the quality gate enforces UTF-8 before
    upload, so the reader should never encounter latin-1/cp1252 content.
    """


def stream_csv(
    path: Path,
    delimiter: str = ";",
    encoding: str = "utf-8-sig",
    max_sample: int | None = 100_000,
) -> Generator[tuple[list[str], list[str] | None], None, None]:
    """Yield ``(header, row)`` tuples from a CSV file, one at a time.

    The first yield always carries ``row=None`` (the header row only).
    Subsequent yields carry parsed data rows as ``list[str]``.

    Encoding fallback chain (tried in order):
    ``utf-8-sig → utf-8``.  Non-UTF-8 files raise ``ValueError``.

    Args:
        path:       Path to the CSV file.
        delimiter:  CSV field delimiter (default ``;``).
        encoding:   Initial encoding to try (default ``utf-8-sig``).
        max_sample: Maximum number of data rows to yield (default 100 000).
                    Pass ``None`` to scan the entire file.

    Yields:
        ``(header, row)`` tuples. The first yield has ``row=None``.

    Raises:
        ValueError: When none of the encoding fallbacks succeed.
    """
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
