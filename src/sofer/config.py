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

from . import _toml

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
    # Quality-scan bounds (issue #290). ``quality_max_dup_tracking`` is a hard
    # cap on the distinct row hashes the ``duplicates`` check tracks (a dict
    # entry + 32-char md5 hexdigest ≈ 200 B, so 1 M tracked rows ≈ 200 MB —
    # bounded, and that bound is the whole reason the cap exists).
    # ``quality_full_scan`` is the tri-state policy (``QUALITY_FULL_SCAN_MODES``)
    # and ``quality_row_requiring_checks`` names the active fail checks that
    # actually need every row before ``auto`` chooses the full scan.
    "quality_max_dup_tracking": 1_000_000,
    "quality_full_scan": "auto",
    "quality_row_requiring_checks": ["corrupt_records"],
    # Cap for unclassified filenames listed by splits.validate_layout
    # (issue #189): the slice and its ellipsis guard derive from this one value.
    "splits_max_unclassified_names": 5,
    # Metadata-core (profile/render) inference knobs.
    # ``semantic_priors["email"] = 0.98``: an email column's ``@`` + TLD
    # structure is distinctive, so a regex match-rate near 1.0 is highly
    # reliable — the prior reflects that. Kept in config (not a class
    # attribute) so recalibration is a TOML edit, not a code change.
    "semantic_priors": {"email": 0.98},
    "confirm_threshold": 0.8,
    "min_threshold": 0.5,
    "detect_threshold": 0.5,
    # Agent-facing metadata gate (issue #288). `sofer init` writes a [meta] block
    # of placeholders and nothing said they had to be replaced, so they travelled
    # through validate -> prepare -> codebook_all -> profile_all -> render_all with
    # every envelope reporting ok: true, surfacing only in the generated card.
    # A value that is empty or begins with one of these prefixes (case-insensitive)
    # is reported as a template placeholder. A WARNING, never a failure: a `fail`
    # would break every existing config that still carries one, which is a contract
    # change rather than a fix (maintainer decision D3).
    "meta_placeholder_prefixes": ["TODO", "YOUR_", "example"],
    "profile_max_sample": 100_000,
    "confidence_round_digits": 4,
    # Size guard for MCP agent resource reads (sofer://dataset, sofer://codebook,
    # sofer://metadata): resources larger than this are refused with a clear
    # error naming the limit instead of being slurped into an LLM context.
    "agent_resource_max_bytes": 50_000_000,
    # Size cap for the MCP tool "output" envelope (captured stdout/stderr).
    # Larger outputs are truncated with a "... [truncated: N bytes]" marker so
    # a verbose validation/prepare/codebook run can never blow up the agent
    # context. Separate from agent_resource_max_bytes (which REFUSES a whole
    # resource): the output envelope is truncated, not refused.
    "output_max_bytes": 1_000_000,
    # Card collapse threshold: columns per table above which Data Fields
    # collapses; multi-table datasets always per-sheet collapsible. Tool-wide.
    "card_collapse_threshold": 15,
    # Mixed-schema config generation (issue #292): one HF `configs` entry per
    # column-signature group. `card_config_slug_invalid_pattern` matches every
    # run of characters not allowed in a config identifier (HF allows
    # ``[a-z0-9._-]``); runs collapse to `card_config_slug_separator`.
    # `card_config_slug_max_length` caps the slug and
    # `card_config_slug_fallback` names a group whose slug would be empty.
    "card_config_slug_invalid_pattern": r"[^a-z0-9._-]+",
    "card_config_slug_separator": "-",
    "card_config_slug_max_length": 96,
    "card_config_slug_fallback": "default",
    # Group-aware default-load warning (issue #303): how many emitted config
    # names the warning lists before eliding the rest. A corpus with dozens of
    # column-signature groups would otherwise print an unreadable wall of names
    # in the one message that tells the user how to load the repo.
    "card_config_group_warn_limit": 5,
    # Assisted failure reporting (issue #244). ``failure_report_dir`` is the
    # subdirectory under sofer's state home that holds one JSON file per
    # unsent failure; ``failure_report_repo`` is the ``owner/repo`` issues are
    # filed against; the last two bound the report size and the ``gh`` call.
    "failure_report_dir": "failure-reports",
    "failure_report_repo": "emiliodavola/sofer",
    "failure_report_traceback_max_chars": 20_000,
    "failure_report_manual_url_max_chars": 6_000,
    "failure_report_gh_timeout_seconds": 30,
    "failure_report_duplicate_limit": 5,
    "failure_report_duplicate_query_tokens": 8,
    # ── MCP registration timeouts (issues #287, #296) ──
    # Host-side deadlines ``sofer mcp add`` writes into the ``sofer`` entry.
    # Both deadlines failed against hosts' defaults and both surfaced as
    # ``Connection failed`` / ``request timed out`` — indistinguishable from a
    # broken registration. ``mcp_connect_timeout_seconds`` is ~4x the measured
    # 16-32 s cold start of ``sofer-mcp`` (heavy imports before ``initialize``
    # can be answered); ``mcp_request_timeout_seconds`` covers the measured
    # ~680 s ``prepare`` on a 3.2 GB / 66.2 M-row corpus with margin.
    # ``mcp_progress_heartbeat_seconds`` is how often a long tool re-announces
    # progress, which is what resets a host deadline that the registered value
    # could not raise (issue #296 §3).
    "mcp_request_timeout_seconds": 900,
    "mcp_connect_timeout_seconds": 120,
    "mcp_progress_heartbeat_seconds": 20,
    # ── HF upload diagnostics (issue #289) ──
    # Number of ADDITIONAL ``upload_folder`` attempts after the first failure.
    # ``1`` is the maintainer-settled bound (decision D2): exactly one retry,
    # no automatic xet fallback. Env-var NAMES probed to report which Hub
    # transfer backend is active (never hardcoded in ``publish``), and the
    # character cap for the exception message echoed in the failure report.
    "hf_upload_retry_count": 1,
    "hf_backend_disable_env": "HF_HUB_DISABLE_XET",
    "hf_backend_prefix_env": "HF_XET_",
    "hf_upload_error_max_chars": 500,
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
            with open(toml_path, "rb") as fh:
                toml_data = _toml.load(fh)
        except Exception:
            toml_data = {}

    tool_section: dict[str, Any] = toml_data.get("tool", {}).get("sofer", {})

    merged = dict(_DEFAULTS)
    # Keys with dedicated post-loop validation keep their specific
    # diagnostics; every other key is type-checked here so a malformed
    # TOML value never reaches a module constant (and thus a reader or
    # comparison) as an arbitrary Python type (TC-13, #118).
    _post_loop_keys = {
        "semantic_priors",
        "profile_dir",
        "render_dir",
        "card_collapse_threshold",
    }
    for key, default in _DEFAULTS.items():
        val = tool_section.get(key)
        if val is None:
            continue
        if key in _post_loop_keys:
            merged[key] = val
            continue
        if isinstance(default, list):
            if isinstance(val, list):
                merged[key] = val
            elif isinstance(val, str):
                merged[key] = [val]
            else:
                raise ValueError(
                    f"'{key}' in [tool.sofer] must be an array, got {type(val).__name__}: {val!r}"
                )
        elif isinstance(default, bool):
            if not isinstance(val, bool):
                raise ValueError(
                    f"'{key}' in [tool.sofer] must be a boolean, got {type(val).__name__}: {val!r}"
                )
            merged[key] = val
        elif isinstance(default, int):
            if not isinstance(val, int) or isinstance(val, bool):
                raise ValueError(
                    f"'{key}' in [tool.sofer] must be an integer, got {type(val).__name__}: {val!r}"
                )
            merged[key] = val
        elif isinstance(default, float):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(
                    f"'{key}' in [tool.sofer] must be a number, got {type(val).__name__}: {val!r}"
                )
            merged[key] = float(val) if isinstance(val, int) else val
        elif isinstance(default, str):
            if not isinstance(val, str):
                raise ValueError(
                    f"'{key}' in [tool.sofer] must be a string, got {type(val).__name__}: {val!r}"
                )
            merged[key] = val
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
    # collide. ``failure_report_dir`` and ``failure_report_repo`` are likewise
    # non-empty: an empty directory would scatter report files in the state
    # home, and an empty repo would produce an unusable issue URL.
    for _key in ("profile_dir", "render_dir", "failure_report_dir", "failure_report_repo"):
        _val = merged.get(_key, "")
        if not isinstance(_val, str) or not _val.strip():
            raise ValueError(f"'{_key}' in [tool.sofer] must be a non-empty string")

    # ``card_collapse_threshold`` must be a non-negative integer (tool-wide,
    # never from per-dataset TOML [meta]).
    _thr = merged.get("card_collapse_threshold")
    if not isinstance(_thr, int) or isinstance(_thr, bool) or _thr < 0:
        raise ValueError("'card_collapse_threshold' in [tool.sofer] must be a non-negative integer")

    # Failure-report bounds must be positive: a non-positive traceback cap
    # would truncate every report to nothing, and a non-positive gh timeout is
    # meaningless (subprocess would reject it).
    for _key in (
        "failure_report_traceback_max_chars",
        "failure_report_manual_url_max_chars",
        "failure_report_gh_timeout_seconds",
        "failure_report_duplicate_limit",
        "failure_report_duplicate_query_tokens",
    ):
        _val = merged.get(_key)
        if not isinstance(_val, int) or isinstance(_val, bool) or _val < 1:
            raise ValueError(f"'{_key}' in [tool.sofer] must be a positive integer")

    # HF upload diagnostics (issue #289): the retry count is a non-negative
    # integer (0 disables the retry), and the error cap must be positive so a
    # failure report is never truncated to nothing.
    _retry = merged.get("hf_upload_retry_count")
    if not isinstance(_retry, int) or isinstance(_retry, bool) or _retry < 0:
        raise ValueError("'hf_upload_retry_count' in [tool.sofer] must be a non-negative integer")
    _err_cap = merged.get("hf_upload_error_max_chars")
    if not isinstance(_err_cap, int) or isinstance(_err_cap, bool) or _err_cap < 1:
        raise ValueError("'hf_upload_error_max_chars' in [tool.sofer] must be a positive integer")

    # Quality scan bounds (issue #290): the full-scan policy is a closed
    # tri-state, and the duplicate cap must be a positive integer — 0 would
    # silently disable duplicate detection instead of bounding it.
    if merged.get("quality_full_scan") not in QUALITY_FULL_SCAN_MODES:
        raise ValueError(
            "'quality_full_scan' in [tool.sofer] must be one of "
            f"{', '.join(repr(mode) for mode in QUALITY_FULL_SCAN_MODES)}"
        )
    _dup_cap = merged.get("quality_max_dup_tracking")
    if not isinstance(_dup_cap, int) or isinstance(_dup_cap, bool) or _dup_cap < 1:
        raise ValueError("'quality_max_dup_tracking' in [tool.sofer] must be a positive integer")

    # MCP registration timeouts (issues #287, #296): all three must be positive
    # integers. A non-positive host deadline would make the registered server
    # unusable — exactly the failure these keys exist to prevent — and a
    # non-positive heartbeat would spin.
    for _key in (
        "mcp_request_timeout_seconds",
        "mcp_connect_timeout_seconds",
        "mcp_progress_heartbeat_seconds",
    ):
        _val = merged.get(_key)
        if not isinstance(_val, int) or isinstance(_val, bool) or _val < 1:
            raise ValueError(f"'{_key}' in [tool.sofer] must be a positive integer")

    # The group-aware warning cap must be a positive integer: 0 would name no
    # config at all, which is the defect the cap exists inside of (issue #303).
    _warn_limit = merged.get("card_config_group_warn_limit")
    if not isinstance(_warn_limit, int) or isinstance(_warn_limit, bool) or _warn_limit < 1:
        raise ValueError(
            "'card_config_group_warn_limit' in [tool.sofer] must be a positive integer"
        )

    # The placeholder prefixes are string patterns, never values: an empty entry or
    # a non-string would make the agent-facing gate match everything or nothing
    # (issue #288).
    _prefixes = merged.get("meta_placeholder_prefixes")
    if (
        not isinstance(_prefixes, list)
        or not _prefixes
        or not all(isinstance(p, str) and p.strip() for p in _prefixes)
    ):
        raise ValueError(
            "'meta_placeholder_prefixes' in [tool.sofer] must be a non-empty list of "
            "non-empty strings"
        )

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
# Console error handler for sys.stdout/sys.stderr (CLI-R11, issue #161): an emitted
# character the active console encoding cannot represent is substituted in the stream
# instead of aborting the command. Deliberately NOT a _DEFAULTS entry: this is the
# console guard's implementation policy, not a tool-wide user option. _read_tool_section
# iterates _DEFAULTS, so adding it there would silently make [tool.sofer] console_errors
# settable and drift the behaviour away from the CLI-R11 contract.
CONSOLE_ERRORS: str = "replace"
PROBE_CHUNK_BYTES: int = _DEFAULTS["probe_chunk_bytes"]
CSV_DELIMITER: str = _DEFAULTS["csv_delimiter"]
CSV_ENCODING: str = _DEFAULTS["csv_encoding"]

SNIFF_DELIMITERS: list[str] = _DEFAULTS["sniff_delimiters"]

CARD_FALLBACK_ROWS_PER_FILE: int = _DEFAULTS["card_fallback_rows_per_file"]
CARD_MODALITY_TAGS: list[str] = _DEFAULTS["card_modality_tags"]
CARD_BOOLEAN_VALUES: list[str] = _DEFAULTS["card_boolean_values"]

SCHEMA_DUP_THRESHOLD: int = _DEFAULTS["schema_dup_threshold"]
SCHEMA_SAMPLE_SIZE: int = _DEFAULTS["schema_sample_size"]

QUALITY_MAX_DUP_TRACKING: int = _DEFAULTS["quality_max_dup_tracking"]
QUALITY_FULL_SCAN: str = _DEFAULTS["quality_full_scan"]
QUALITY_ROW_REQUIRING_CHECKS: list[str] = _DEFAULTS["quality_row_requiring_checks"]
SPLITS_MAX_UNCLASSIFIED_NAMES: int = _DEFAULTS["splits_max_unclassified_names"]

QUALITY_FULL_SCAN_MODES: tuple[str, ...] = ("auto", "always", "never")
"""Closed set of ``quality_full_scan`` values (issue #290).

Deliberately NOT a ``_DEFAULTS`` entry: this is the policy vocabulary the
value is validated against, not a tunable user option — adding it to
``_DEFAULTS`` would make ``[tool.sofer] quality_full_scan_modes`` settable and
detach the validator from the tri-state it is meant to enforce.
"""

# Metadata-core (profile/render) inference knobs.
SEMANTIC_PRIORS: dict[str, float] = _DEFAULTS["semantic_priors"]
CONFIRM_THRESHOLD: float = _DEFAULTS["confirm_threshold"]
MIN_THRESHOLD: float = _DEFAULTS["min_threshold"]
DETECT_THRESHOLD: float = _DEFAULTS["detect_threshold"]
PROFILE_MAX_SAMPLE: int = _DEFAULTS["profile_max_sample"]
CONFIDENCE_ROUND_DIGITS: int = _DEFAULTS["confidence_round_digits"]

# Agent-facing metadata gate (issue #288) — see the _DEFAULTS comment.
META_PLACEHOLDER_PREFIXES: list[str] = _DEFAULTS["meta_placeholder_prefixes"]

# MCP agent resource size guard (see ``_DEFAULTS["agent_resource_max_bytes"]``).
AGENT_RESOURCE_MAX_BYTES: int = _DEFAULTS["agent_resource_max_bytes"]

# MCP tool output envelope cap (see ``_DEFAULTS["output_max_bytes"]``).
OUTPUT_MAX_BYTES: int = _DEFAULTS["output_max_bytes"]

CARD_COLLAPSE_THRESHOLD: int = _DEFAULTS["card_collapse_threshold"]

# Mixed-schema config generation (issue #292) — see the _DEFAULTS comments.
CARD_CONFIG_SLUG_INVALID_PATTERN: str = _DEFAULTS["card_config_slug_invalid_pattern"]
CARD_CONFIG_SLUG_SEPARATOR: str = _DEFAULTS["card_config_slug_separator"]
CARD_CONFIG_SLUG_MAX_LENGTH: int = _DEFAULTS["card_config_slug_max_length"]
CARD_CONFIG_SLUG_FALLBACK: str = _DEFAULTS["card_config_slug_fallback"]

# Group-aware default-load warning cap (issue #303) — see the _DEFAULTS comment.
CARD_CONFIG_GROUP_WARN_LIMIT: int = _DEFAULTS["card_config_group_warn_limit"]

# Assisted failure reporting (issue #244): state subdirectory, target repo,
# traceback cap, and gh timeout — read live through attribute access.
FAILURE_REPORT_DIR: str = _DEFAULTS["failure_report_dir"]
FAILURE_REPORT_REPO: str = _DEFAULTS["failure_report_repo"]
FAILURE_REPORT_TRACEBACK_MAX_CHARS: int = _DEFAULTS["failure_report_traceback_max_chars"]
FAILURE_REPORT_MANUAL_URL_MAX_CHARS: int = _DEFAULTS["failure_report_manual_url_max_chars"]
FAILURE_REPORT_GH_TIMEOUT_SECONDS: int = _DEFAULTS["failure_report_gh_timeout_seconds"]
FAILURE_REPORT_DUPLICATE_LIMIT: int = _DEFAULTS["failure_report_duplicate_limit"]
FAILURE_REPORT_DUPLICATE_QUERY_TOKENS: int = _DEFAULTS["failure_report_duplicate_query_tokens"]

# MCP registration timeouts (issues #287, #296): the deadlines ``sofer mcp add``
# writes into the ``sofer`` entry, plus the heartbeat that keeps a long tool's
# host deadline reset. Read live through attribute access.
MCP_REQUEST_TIMEOUT_SECONDS: int = _DEFAULTS["mcp_request_timeout_seconds"]
MCP_CONNECT_TIMEOUT_SECONDS: int = _DEFAULTS["mcp_connect_timeout_seconds"]
MCP_PROGRESS_HEARTBEAT_SECONDS: int = _DEFAULTS["mcp_progress_heartbeat_seconds"]

# HF upload diagnostics (issue #289): bounded retry count, the env-var NAMES
# probed for the active transfer backend, and the exception-message cap.
HF_UPLOAD_RETRY_COUNT: int = _DEFAULTS["hf_upload_retry_count"]
HF_BACKEND_DISABLE_ENV: str = _DEFAULTS["hf_backend_disable_env"]
HF_BACKEND_PREFIX_ENV: str = _DEFAULTS["hf_backend_prefix_env"]
HF_UPLOAD_ERROR_MAX_CHARS: int = _DEFAULTS["hf_upload_error_max_chars"]
