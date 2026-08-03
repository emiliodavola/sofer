"""
Supported file-format registry for the ``scan`` command.

Each key is a file extension (with leading dot) and each value is a
human-readable label.  Extending is a matter of adding one dict entry.
"""

from __future__ import annotations

SUPPORTED_FORMATS: dict[str, str] = {
    ".csv": "CSV",
    ".tsv": "TSV",
    ".parquet": "Parquet",
    ".xlsx": "Excel",
    ".jsonl": "JSON Lines",
}
