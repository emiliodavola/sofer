"""
Shared sentinel values treated as missing across all CSV/Parquet paths.

Single source of truth — every module that needs to detect missing-value
markers imports from here.
"""

from __future__ import annotations

from collections.abc import Iterable

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


def count_unique_non_missing(values: Iterable[str]) -> int:
    """Count the DISTINCT NON-MISSING values in *values*.

    A value is treated as missing when it is whitespace-only or when its
    uppercase form is in :data:`MISSING_VALUE_SENTINELS` (so ``"NA"``,
    ``"na"``, and ``"Na"`` are all excluded).

    Precondition: *values* are strings. ``None`` entries must be coerced to
    strings upstream (the Parquet sample path renders nulls as ``""`` before
    calling; CSV readers never yield ``None``).

    Args:
        values: Sampled column values (strings).

    Returns:
        The number of distinct non-missing values.
    """
    non_missing = {
        v for v in values if v.strip() and v.strip().upper() not in MISSING_VALUE_SENTINELS
    }
    return len(non_missing)
