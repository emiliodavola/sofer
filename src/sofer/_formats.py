"""
Supported file-format registry for the ``scan`` command and text-eligibility gate.

``SUPPORTED_FORMATS`` maps every file extension the scanner recognises to a
human-readable label.  Extending is a matter of adding one dict entry.

``TEXT_SUFFIXES`` is the allowlist for P0 quality checks.  A file is
text-eligible when ``Path.suffix.lower()`` is in this set — only ``.csv``
and ``.tsv`` (case-insensitive) are eligible.  ``Path.suffix`` returns the
final suffix only, so ``.csv.gz`` yields ``.gz`` (not eligible) and a file
with no extension such as ``README`` yields ``""`` (not eligible).
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_FORMATS: dict[str, str] = {
    ".csv": "CSV",
    ".tsv": "TSV",
    ".parquet": "Parquet",
    ".xlsx": "Excel",
    ".jsonl": "JSON Lines",
}

TEXT_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv"})
"""Suffixes eligible for P0 quality checks — only text formats are scanned."""


def is_text_eligible(path: Path) -> bool:
    """Return ``True`` when *path* is eligible for P0 quality checks.

    Eligibility is determined by the file suffix (case-insensitive):
    ``path.suffix.lower() in TEXT_SUFFIXES``.  Only ``.csv`` and ``.tsv``
    are eligible; all other suffixes (``.xlsx``, ``.parquet``, ``.jsonl``,
    ``.gz``, ``""`` for no extension) return ``False``.

    Args:
        path: File path whose suffix is inspected.

    Returns:
        ``True`` for ``.csv``/``.tsv`` (any case), ``False`` otherwise.
    """
    return path.suffix.lower() in TEXT_SUFFIXES
