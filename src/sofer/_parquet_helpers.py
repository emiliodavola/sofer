"""
Shared Parquet-to-HF type mapping.

Extracted from ``repo_compliance.py`` and ``uploader.py`` to eliminate a
duplication that had drifted subtly (identical bodies, different function names).
"""

from __future__ import annotations

import pyarrow as pa


def _parquet_to_hf_dtype(pa_type: object) -> str | None:
    """Map a pyarrow physical type to an HF Dataset feature type string.

    Returns ``None`` for ``null`` type (should be omitted from features list).
    """
    # Integral types
    if pa.types.is_int8(pa_type) or pa.types.is_int16(pa_type) or pa.types.is_int32(pa_type):
        return "int32"
    if pa.types.is_int64(pa_type):
        return "int64"

    # Floating point
    if pa.types.is_float32(pa_type):
        return "float32"
    if pa.types.is_float64(pa_type):
        return "float64"

    # Boolean
    if pa.types.is_boolean(pa_type):
        return "bool"

    # String types
    if pa.types.is_string(pa_type) or pa.types.is_large_string(pa_type):
        return "string"

    # Binary types → string
    if (
        pa.types.is_binary(pa_type)
        or pa.types.is_large_binary(pa_type)
        or pa.types.is_fixed_size_binary(pa_type)
    ):
        return "string"

    # Temporal types
    if pa.types.is_date32(pa_type):
        return "date32"
    if pa.types.is_date64(pa_type):
        return "timestamp[ms]"
    if pa.types.is_timestamp(pa_type):
        return "timestamp[s]"
    if pa.types.is_time32(pa_type) or pa.types.is_time64(pa_type):
        return "time64"

    # Decimal
    if pa.types.is_decimal(pa_type):
        return "float64"

    # Null — omit from features
    if pa.types.is_null(pa_type):
        return None

    return "string"
