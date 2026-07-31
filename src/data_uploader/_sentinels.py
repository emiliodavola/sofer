"""
Shared sentinel values treated as missing across all CSV/Parquet paths.

Single source of truth — every module that needs to detect missing-value
markers imports from here.
"""

from __future__ import annotations

# fmt: off
MISSING_VALUE_SENTINELS: frozenset[str] = frozenset(
    {
        "",
        "N/A", "NA", "n/a", "na",
        "null", "NULL",
        "None", "NONE",
        " ",
        "-", "--",
        "??",
        "NOTAPPLICABLE", "MISSING",
    }
)
# fmt: on
