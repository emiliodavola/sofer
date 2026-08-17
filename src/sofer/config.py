"""
Tool-wide configuration loaded from ``pyproject.toml`` under ``[tool.sofer]``.

Every value has a sensible default — the ``pyproject.toml`` section is optional.
Module-level constants are read once at import time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
#  Hard-coded fallback defaults — used when pyproject.toml is absent or
#  the ``[tool.sofer]`` section is missing keys.
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    # sofer artifact cache — ``data/`` stays reserved for raw source files
    # (user decision for the prepare/publish split).
    "output_dir": "cache",
    "default_config_name": "dataset.toml",
    "parquet_row_group_size": 100_000,
    "parquet_compression": "zstd",
    "parquet_shard_warning_mb": 500,
    "report_max_items": 10,
    "report_max_modified": 5,
    "report_max_corrupt_records": 20,
    "report_line_width": 50,
    "report_sub_line_width": 30,
    "codebooks_dir": "codebooks",
    "codebook_max_sample": 100_000,
    "codebook_numeric_threshold": 0.9,
    "codebook_mixed_threshold": 0.5,
    "output_encoding": "utf-8",
    "probe_chunk_bytes": 8192,
    "csv_delimiter": ";",
    "csv_encoding": "utf-8-sig",
    "sniff_delimiters": [";", ",", "\t"],
    "card_fallback_rows_per_file": 100,
    "card_modality_tags": [
        "tabular",
        "text",
        "image",
        "audio",
        "video",
        "timeseries",
        "geospatial",
        "3d",
    ],
    "card_boolean_values": ["true", "false", "1", "0", "yes", "no"],
    "schema_dup_threshold": 3,
    # Metadata-core (profile/render) inference knobs.
    # ``semantic_priors["email"] = 0.98``: an email column's ``@`` + TLD
    # structure is distinctive, so a regex match-rate near 1.0 is highly
    # reliable — the prior reflects that. Kept in config (not a class
    # attribute) so recalibration is a TOML edit, not a code change.
    "semantic_priors": {"email": 0.98},
    "confirm_threshold": 0.8,
    "min_threshold": 0.5,
    "detect_threshold": 0.5,
    "profile_max_sample": 100_000,
    "confidence_round_digits": 4,
}


def _find_project_root() -> Path:
    """Walk up from this file until a ``pyproject.toml`` is found."""
    current = Path(__file__).resolve().parent
    for ancestor in current.parents:
        if (ancestor / "pyproject.toml").is_file():
            return ancestor
    # Fallback: working directory
    return Path.cwd()


def _load_tool_config() -> dict[str, Any]:
    """Read ``[tool.sofer]`` from the project's ``pyproject.toml``.

    All keys are optional — missing keys fall back to :data:`_DEFAULTS`.
    Returns a merged ``dict``: TOML values take precedence over defaults.
    """
    root = _find_project_root()
    toml_path = root / "pyproject.toml"

    toml_data: dict[str, Any] = {}
    if toml_path.is_file():
        try:
            import tomli as _tomli
        except ImportError:  # Python ≥ 3.11
            import tomllib as _tomli

        try:
            with open(toml_path, "rb") as fh:
                toml_data = _tomli.load(fh)
        except Exception:
            toml_data = {}

    tool_section: dict[str, Any] = toml_data.get("tool", {}).get("sofer", {})

    merged = dict(_DEFAULTS)
    for key, default in _DEFAULTS.items():
        val = tool_section.get(key)
        if val is not None:
            # Ensure types match the defaults where they matter
            if isinstance(default, list) and isinstance(val, list):
                merged[key] = val
            elif isinstance(default, list) and isinstance(val, str):
                merged[key] = [val]
            else:
                merged[key] = val

    # ``semantic_priors`` maps a detector name to a prior probability. A
    # non-dict value (e.g. a stray string) is a user config error — reject it
    # loudly rather than silently keeping the default (AGENTS.md rule 3: never
    # bypass a user-provided config value).
    if "semantic_priors" in tool_section and not isinstance(tool_section["semantic_priors"], dict):
        raise ValueError(
            "'semantic_priors' in [tool.sofer] must be a table mapping detector "
            "names to prior probabilities, e.g. semantic_priors = { email = 0.98 }"
        )

    return merged


# ---------------------------------------------------------------------------
#  Module-level constants — read once at import
# ---------------------------------------------------------------------------

_tool = _load_tool_config()

OUTPUT_DIR: str = _tool["output_dir"]
DEFAULT_CONFIG_NAME: str = _tool["default_config_name"]

PARQUET_ROW_GROUP_SIZE: int = _tool["parquet_row_group_size"]
PARQUET_COMPRESSION: str = _tool["parquet_compression"]
PARQUET_SHARD_WARNING_MB: int = _tool["parquet_shard_warning_mb"]

REPORT_MAX_ITEMS: int = _tool["report_max_items"]
REPORT_MAX_MODIFIED: int = _tool["report_max_modified"]
REPORT_MAX_CORRUPT_RECORDS: int = _tool["report_max_corrupt_records"]
REPORT_LINE_WIDTH: int = _tool["report_line_width"]
REPORT_SUB_LINE_WIDTH: int = _tool["report_sub_line_width"]

CODEBOOKS_DIR: str = _tool["codebooks_dir"]
CODEBOOK_MAX_SAMPLE: int = _tool["codebook_max_sample"]
CODEBOOK_NUMERIC_THRESHOLD: float = _tool["codebook_numeric_threshold"]
CODEBOOK_MIXED_THRESHOLD: float = _tool["codebook_mixed_threshold"]

OUTPUT_ENCODING: str = _tool["output_encoding"]
PROBE_CHUNK_BYTES: int = _tool["probe_chunk_bytes"]
CSV_DELIMITER: str = _tool["csv_delimiter"]
CSV_ENCODING: str = _tool["csv_encoding"]

SNIFF_DELIMITERS: list[str] = _tool["sniff_delimiters"]

CARD_FALLBACK_ROWS_PER_FILE: int = _tool["card_fallback_rows_per_file"]
CARD_MODALITY_TAGS: list[str] = _tool["card_modality_tags"]
CARD_BOOLEAN_VALUES: list[str] = _tool["card_boolean_values"]

SCHEMA_DUP_THRESHOLD: int = _tool["schema_dup_threshold"]

# Metadata-core (profile/render) inference knobs.
SEMANTIC_PRIORS: dict[str, float] = _tool["semantic_priors"]
CONFIRM_THRESHOLD: float = _tool["confirm_threshold"]
MIN_THRESHOLD: float = _tool["min_threshold"]
DETECT_THRESHOLD: float = _tool["detect_threshold"]
PROFILE_MAX_SAMPLE: int = _tool["profile_max_sample"]
CONFIDENCE_ROUND_DIGITS: int = _tool["confidence_round_digits"]
