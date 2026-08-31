"""
Tool-wide configuration loaded from ``pyproject.toml`` under ``[tool.sofer]``.

Every value has a sensible default — the ``pyproject.toml`` section is optional.

Discovery anchoring (issue #56): the nearest ``pyproject.toml`` is found by
walking up from a caller-supplied *start* directory — the dataset TOML's
directory when known, otherwise the current working directory — **never**
from the installed package location. Module-level constants are bound from
built-in defaults at import time (zero filesystem access) and rebound by
:func:`reload` once an anchor is known, so all consumers read live values
through attribute access (``config.X``).
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
#  Hard-coded fallback defaults — used when pyproject.toml is absent or
#  the ``[tool.sofer]`` section is missing keys.
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    # sofer artifact cache — ``cache/`` holds scan copies ready for prepare;
    # ``raw/`` is the tracked source root scanned via ``flatten_first_level``
    # (``raw/DPTO.csv → cache/DPTO.csv``).
    "output_dir": "cache",
    "raw_dir": "raw",
    "default_config_name": "dataset.toml",
    "profile_dir": "profiles",
    "render_dir": "renders",
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
    # Rows sampled per file for schema inference in the schema report
    # (repo_compliance.build_schema_report). Balances statistical confidence
    # against read-time cost; also surfaced in the card's stats footnote.
    "schema_sample_size": 10_000,
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
    # Size guard for MCP agent resource reads (sofer://dataset, sofer://codebook,
    # sofer://metadata): resources larger than this are refused with a clear
    # error naming the limit instead of being slurped into an LLM context.
    "agent_resource_max_bytes": 50_000_000,
    # Card collapse threshold: columns per table above which Data Fields
    # collapses; multi-table datasets always per-sheet collapsible. Tool-wide.
    "card_collapse_threshold": 15,
}

# Guard around constant rebinding in :func:`reload` — concurrent readers see
# either the old or the new complete state, never a partial mix.
_LOCK = threading.Lock()

# Absolute path of the pyproject.toml the current constants were resolved
# from, or ``None`` when built-in defaults apply. Rebound by :func:`reload`.
SOURCE_PATH: Path | None = None


def _find_project_root(
    start: str | Path | None = None, stop_at: str | Path | None = None
) -> Path | None:
    """Walk up from *start* until a directory containing ``pyproject.toml``.

    Args:
        start: Directory anchoring the walk-up. When ``None``, the current
            working directory is used. The start directory itself is part of
            the search. The installed package location is never consulted.
        stop_at: Optional upper bound for the walk-up (MCP server containment):
            discovery never walks ABOVE this directory, so a ``pyproject.toml``
            outside the boundary is ignored and defaults apply. ``None`` keeps
            the CLI behavior — walk up to the filesystem root. A *start* that
            is itself outside *stop_at* yields ``None`` (nothing is searched).

    Returns:
        The first directory (starting at *start*, then each parent up to
        *stop_at* or the filesystem root) containing a ``pyproject.toml``, or
        ``None`` when no such file exists within the search bounds.
    """
    start_dir = Path(start).resolve() if start is not None else Path.cwd().resolve()
    stop = Path(stop_at).resolve() if stop_at is not None else None
    for candidate in (start_dir, *start_dir.parents):
        if stop is not None and not candidate.is_relative_to(stop):
            break  # bounded discovery: never walk above stop_at
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def _read_tool_section(toml_path: Path | None) -> dict[str, Any]:
    """Read and validate the ``[tool.sofer]`` table from *toml_path*.

    All keys are optional — missing keys fall back to :data:`_DEFAULTS`.

    Args:
        toml_path: Absolute path to the discovered ``pyproject.toml``, or
            ``None`` when nothing was found on the walk-up.

    Returns:
        A merged ``dict``: TOML values take precedence over defaults.
    """
    toml_data: dict[str, Any] = {}
    if toml_path is not None and toml_path.is_file():
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

    # ``profile_dir`` / ``render_dir`` must be non-empty strings — an empty
    # value would resolve output writes to the write root itself and silently
    # collide.
    for _key in ("profile_dir", "render_dir"):
        _val = merged.get(_key, "")
        if not isinstance(_val, str) or not _val.strip():
            raise ValueError(f"'{_key}' in [tool.sofer] must be a non-empty string")

    # ``card_collapse_threshold`` must be a non-negative integer (tool-wide,
    # never from per-dataset TOML [meta]).
    _thr = merged.get("card_collapse_threshold")
    if not isinstance(_thr, int) or isinstance(_thr, bool) or _thr < 0:
        raise ValueError("'card_collapse_threshold' in [tool.sofer] must be a non-negative integer")

    return merged


def _discover(
    start: str | Path | None = None, stop_at: str | Path | None = None
) -> tuple[dict[str, Any], Path | None]:
    """Resolve ``[tool.sofer]`` following the fixed precedence order.

    Resolution (spec TC-02):

        1. nearest ``pyproject.toml`` walking up from *start* (the dataset
           TOML directory when known),
        2. nearest ``pyproject.toml`` walking up from the current working
           directory (only consulted when *start* was given and step 1
           found nothing),
        3. built-in ``_DEFAULTS``.

    A found ``pyproject.toml`` without a ``[tool.sofer]`` section is still
    selected as the source but contributes only default values.

    Args:
        start: Anchor directory (see :func:`_find_project_root`); ``None``
            anchors directly on the current working directory.
        stop_at: Optional upper bound for the walk-up (see
            :func:`_find_project_root`); ``None`` keeps the CLI behavior.

    Returns:
        ``(merged, source_path)`` where *merged* is the effective value dict
        and *source_path* is the absolute path of the selected
        ``pyproject.toml``, or ``None`` when built-in defaults apply.
    """
    root = _find_project_root(start, stop_at)
    if root is None and start is not None:
        # Dataset-anchor miss -> cwd fallback (precedence step 2). The
        # fallback honors *stop_at* too — an out-of-bounds cwd yields defaults.
        root = _find_project_root(None, stop_at)
    toml_path = root / "pyproject.toml" if root is not None else None
    return _read_tool_section(toml_path), toml_path


def reload(start: str | Path | None = None, stop_at: str | Path | None = None) -> None:
    """Re-resolve ``[tool.sofer]`` and rebind every module constant.

    Discovery anchors on *start*: pass a dataset TOML's directory for the
    dataset-anchored resolution (Phase 1), or ``None`` to anchor on the
    current working directory (Phase 0 bootstrap). Resolution is a pure
    function of (anchor, filesystem) — calling twice is harmless.

    Records :data:`SOURCE_PATH` (``None`` means built-in defaults were used)
    and emits one stderr line describing the source when the ``SOFER_VERBOSE``
    environment variable is truthy. Stdout is never touched.

    Args:
        start: Directory anchoring the walk-up; ``None`` anchors on cwd.
        stop_at: Optional upper bound for the walk-up (see
            :func:`_find_project_root`); ``None`` keeps the CLI behavior.
    """
    merged, source = _discover(start, stop_at)

    with _LOCK:
        # ``SOURCE_PATH`` is included so concurrent readers see the source
        # and the values resolved from it atomically.
        for key, value in merged.items():
            globals()[key.upper()] = value
        globals()["SOURCE_PATH"] = source

    if os.environ.get("SOFER_VERBOSE", "").strip().lower() in ("1", "true", "yes", "on"):
        shown = str(source) if source is not None else "built-in defaults"
        print(f"[tool.sofer] source: {shown}", file=sys.stderr)


def _load_tool_config() -> dict[str, Any]:
    """Read ``[tool.sofer]`` from the nearest ``pyproject.toml`` above cwd.

    Convenience wrapper over :func:`_discover` returning only the merged
    value dict (kept for direct callers and tests).

    Returns:
        A merged ``dict``: TOML values take precedence over defaults.
    """
    merged, _source = _discover(None)
    return merged


# ---------------------------------------------------------------------------
#  Module-level constants — bound from built-in defaults at import time.
#
#  Import performs NO filesystem access (TC-03 hardening): real discovery
#  happens in :func:`reload`, invoked by the CLI entry point (cwd anchor)
#  and by ``DatasetConfig.from_toml`` (dataset-directory anchor).
# ---------------------------------------------------------------------------

OUTPUT_DIR: str = _DEFAULTS["output_dir"]
RAW_DIR: str = _DEFAULTS["raw_dir"]
PROFILE_DIR: str = _DEFAULTS["profile_dir"]
RENDER_DIR: str = _DEFAULTS["render_dir"]
DEFAULT_CONFIG_NAME: str = _DEFAULTS["default_config_name"]

PARQUET_ROW_GROUP_SIZE: int = _DEFAULTS["parquet_row_group_size"]
PARQUET_COMPRESSION: str = _DEFAULTS["parquet_compression"]
PARQUET_SHARD_WARNING_MB: int = _DEFAULTS["parquet_shard_warning_mb"]

REPORT_MAX_ITEMS: int = _DEFAULTS["report_max_items"]
REPORT_MAX_MODIFIED: int = _DEFAULTS["report_max_modified"]
REPORT_MAX_CORRUPT_RECORDS: int = _DEFAULTS["report_max_corrupt_records"]
REPORT_LINE_WIDTH: int = _DEFAULTS["report_line_width"]
REPORT_SUB_LINE_WIDTH: int = _DEFAULTS["report_sub_line_width"]

CODEBOOKS_DIR: str = _DEFAULTS["codebooks_dir"]
CODEBOOK_MAX_SAMPLE: int = _DEFAULTS["codebook_max_sample"]
CODEBOOK_NUMERIC_THRESHOLD: float = _DEFAULTS["codebook_numeric_threshold"]
CODEBOOK_MIXED_THRESHOLD: float = _DEFAULTS["codebook_mixed_threshold"]

OUTPUT_ENCODING: str = _DEFAULTS["output_encoding"]
PROBE_CHUNK_BYTES: int = _DEFAULTS["probe_chunk_bytes"]
CSV_DELIMITER: str = _DEFAULTS["csv_delimiter"]
CSV_ENCODING: str = _DEFAULTS["csv_encoding"]

SNIFF_DELIMITERS: list[str] = _DEFAULTS["sniff_delimiters"]

CARD_FALLBACK_ROWS_PER_FILE: int = _DEFAULTS["card_fallback_rows_per_file"]
CARD_MODALITY_TAGS: list[str] = _DEFAULTS["card_modality_tags"]
CARD_BOOLEAN_VALUES: list[str] = _DEFAULTS["card_boolean_values"]

SCHEMA_DUP_THRESHOLD: int = _DEFAULTS["schema_dup_threshold"]
SCHEMA_SAMPLE_SIZE: int = _DEFAULTS["schema_sample_size"]

# Metadata-core (profile/render) inference knobs.
SEMANTIC_PRIORS: dict[str, float] = _DEFAULTS["semantic_priors"]
CONFIRM_THRESHOLD: float = _DEFAULTS["confirm_threshold"]
MIN_THRESHOLD: float = _DEFAULTS["min_threshold"]
DETECT_THRESHOLD: float = _DEFAULTS["detect_threshold"]
PROFILE_MAX_SAMPLE: int = _DEFAULTS["profile_max_sample"]
CONFIDENCE_ROUND_DIGITS: int = _DEFAULTS["confidence_round_digits"]

# MCP agent resource size guard (see ``_DEFAULTS["agent_resource_max_bytes"]``).
AGENT_RESOURCE_MAX_BYTES: int = _DEFAULTS["agent_resource_max_bytes"]

CARD_COLLAPSE_THRESHOLD: int = _DEFAULTS["card_collapse_threshold"]
