"""
HF Dataset Compliance — Dataset Card, LICENSE, and schema report generation.

All public functions are *pure*: they take config/schema data and return strings
or structured data.  No file I/O, no network calls — the orchestrator (``prepare``)
handles reading and writing.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from . import config
from ._converters import is_convertible_remote
from ._mirror import expanded_planned_remotes, parquet_remote_for, planned_remotes
from ._parquet_helpers import _parquet_to_hf_dtype
from ._sentinels import MISSING_VALUE_SENTINELS, count_unique_non_missing
from .codebook import infer_column_type
from .model import DatasetConfig, FileEntry


def normalize_header(col_name: str) -> str:
    """Normalize a column name by stripping leading/trailing whitespace.

    Column names are case-sensitive in HF datasets, so we preserve the
    original casing and only remove surrounding whitespace inserted by
    careless CSV exports.
    """
    return col_name.strip()


_MORE_INFO: str = "[More Information Needed]"
"""Sentinel for a card section with no configured content.

A module constant used at every such site (issue #291) so the sentinel the card
emits and the value the tests assert cannot drift, and so a future change to
"omit the section instead" is one edit rather than four.
"""


# Map our internal dtype strings to HF Dataset Feature types (CSV fallback path)
_HF_FEATURE_MAP: dict[str, str] = {
    "numeric": "float64",
    "categorical/text": "string",
    "mixed (mostly numeric)": "string",
    "unknown": "string",
}

# Canonical size_categories enumeration from huggingface_hub.DatasetCardData
_SIZE_CATEGORIES: frozenset[str] = frozenset(
    {
        "n<1K",
        "1K<n<10K",
        "10K<n<100K",
        "100K<n<1M",
        "1M<n<10M",
        "10M<n<100M",
        "100M<n<1B",
        "1B<n<10B",
        "10B<n<100B",
        "100B<n<1T",
        "n>1T",
        "other",
    }
)

# Known SPDX license identifiers we support (used to detect "other" license flow)
_KNOWN_SPDX_IDS: frozenset[str] = frozenset(
    {"cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "mit", "apache-2.0", "unlicense", "pddl"}
)

# Supported values for annotations_creators / language_creators
_KNOWN_CREATORS: frozenset[str] = frozenset(
    {"found", "crowdsourced", "expert-generated", "machine-generated", "no-annotation", "other"}
)

# Supported values for multilinguality
_KNOWN_MULTILINGUALITY: frozenset[str] = frozenset(
    {"monolingual", "multilingual", "translation", "other"}
)


def _hf_feature_type(dtype: str) -> str:
    """Map internal dtype to HF Dataset Feature type string (CSV fallback)."""
    return _HF_FEATURE_MAP.get(dtype, "string")


def _validate_size_category(value: str) -> str | None:
    """Validate a single size_category value against the canonical enumeration.

    Returns the value if valid, or ``None`` if invalid.
    """
    if value.strip() in _SIZE_CATEGORIES:
        return value.strip()
    return None


def _csv_values_look_like_bool(values: list[str]) -> bool:
    """Check if all non-null CSV values look like boolean literals."""
    bool_vals = set(config.CARD_BOOLEAN_VALUES)
    non_null = [
        v.strip().lower()
        for v in values
        if v.strip() and v.strip().upper() not in MISSING_VALUE_SENTINELS
    ]
    if not non_null:
        return False
    return all(v in bool_vals for v in non_null)


# ═══════════════════════════════════════════════════════════════════════════════
#  ColumnSchema
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ColumnSchema:
    """Describes a single column in the dataset.

    Attributes:
        name:     Column header as it appears in the CSV.
        dtype:    Inferred data type (one of ``"numeric"``,
                  ``"categorical/text"``, ``"mixed (mostly numeric)"``,
                  ``"unknown"``).
        nullable: Whether missing values were observed in the sample.
        example:  A non-missing example value (string).
        unique:   Number of unique values observed in the sample,
                  excluding missing-value sentinels.
        missing:  Percentage of rows with missing values (float 0.0-100.0).
        hf_dtype: HF Dataset feature type string (e.g. ``"int64"``, ``"string"``,
                  ``"bool"``).  Populated from the Parquet schema when available;
                  ``None`` when the type could not be determined from native
                  schema metadata.
        origin:   Source file's basename as sampled (e.g. ``"survey.csv"`` or
                  ``"survey.parquet"``).  ``""`` when constructed without
                  provenance (e.g. hand-built test fixtures).
    """

    name: str
    dtype: str
    nullable: bool
    example: str
    unique: int
    missing: float
    hf_dtype: str | None = None
    origin: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
#  License templates (short-form SPDX texts)
# ═══════════════════════════════════════════════════════════════════════════════

_LICENSE_TEMPLATES: dict[str, str] = {
    "cc0-1.0": """Creative Commons Zero v1.0 Universal

This dataset is dedicated to the public domain under the CC0 1.0 Universal
(CC0 1.0) Public Domain Dedication.

To the extent possible under law, the dataset creator has waived all copyright
and related or neighboring rights to this dataset.

https://creativecommons.org/publicdomain/zero/1.0/
""",
    "cc-by-4.0": """Creative Commons Attribution 4.0 International

This dataset is licensed under the Creative Commons Attribution 4.0
International License.

You are free to:
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material for any purpose,
  even commercially.

Under the following terms:
- Attribution — You must give appropriate credit, provide a link to the
  license, and indicate if changes were made.

https://creativecommons.org/licenses/by/4.0/
""",
    "cc-by-sa-4.0": """Creative Commons Attribution-ShareAlike 4.0 International

This dataset is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License.

You are free to share and adapt the dataset, provided you:
- Give appropriate credit
- Distribute your contributions under the same license

https://creativecommons.org/licenses/by-sa/4.0/
""",
    "mit": """MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this dataset and associated documentation files, to deal in the dataset
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
dataset.

THE DATASET IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
""",
    "apache-2.0": """Apache License, Version 2.0, January 2004

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
""",
    "unlicense": """This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or distribute
this dataset, either in source code form or as a compiled binary, for any
purpose, commercial or non-commercial, and by any means.

In jurisdictions that recognize copyright waivers, the dataset creator
waives all copyright interest in the dataset.
""",
    "pddl": """Open Data Commons Public Domain Dedication and License (PDDL)

This dataset is made available under the Public Domain Dedication and License
v1.0 whose full text can be found at:

http://www.opendatacommons.org/licenses/pddl/1.0/

The dataset is provided as-is, without warranty of any kind.
""",
}


def build_license_file(license_id: str) -> str:
    """Return the content for a ``LICENSE`` file.

    Args:
        license_id: An SPDX identifier (e.g. ``"cc0-1.0"``) or a free-text
                    string.  Pass ``""`` or ``"restricted"`` for the generic
                    fallback.

    Returns:
        The full license text as a string.  Always returns a valid value —
        never raises.
    """
    key = license_id.strip().lower()

    if key in _LICENSE_TEMPLATES:
        return _LICENSE_TEMPLATES[key]

    if not key or key == "restricted":
        return (
            "No license has been declared for this dataset.\n\n"
            "To choose a license for your dataset, visit:\n"
            "  https://choosealicense.com/\n"
        )

    if key == "other":
        return (
            "This dataset is licensed under custom terms.\n\n"
            "See the LICENSE file in this repository for the full license text.\n"
        )

    return (
        f"This dataset is shared under the following terms: {license_id}\n\n"
        "If you need a standard open-source license, visit:\n"
        "  https://choosealicense.com/\n"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Schema report
# ═══════════════════════════════════════════════════════════════════════════════


def _read_csv_sample(
    path: Path,
    delimiter: str | None = None,
    encoding: str | None = None,
    sample_size: int | None = None,
) -> tuple[list[str], list[list[str]], int] | None:
    """Read a CSV once, keeping a bounded sample and the exact record count.

    Returns ``(headers, sample, row_count)`` on success, or ``None`` if the file
    cannot be read. ``sample`` holds at most *sample_size* data records;
    ``row_count`` counts every data record, so it cannot be recovered from
    ``len(sample)`` (issue #373). One pass, not two: the loop that counts is the
    loop that keeps the prefix, so retained memory is bounded by the sample and
    the widest record, never by the total row count.

    Counting follows ``csv.reader`` record semantics, not physical lines: a
    quoted multiline value is one record and a blank line is one empty record.
    A decode or parse failure after the prefix still returns ``None`` and
    discards the whole file -- a counted schema built from the prefix of an
    unreadable file would claim a completeness the file does not have.

    When *delimiter* is ``None``, auto-detect with ``csv.Sniffer`` with the
    configured ``csv_delimiter`` as fallback.  When *encoding* is ``None``, the
    configured ``csv_encoding`` applies.  Neither default is a literal
    (AGENTS.md rule 3, issue #202): the schema-report caller passes the dataset
    ``cfg`` values explicitly, and direct callers inherit the tool-wide
    ``[tool.sofer]`` configuration.  *sample_size* resolves to the configured
    ``schema_sample_size`` at call time.
    """
    effective_encoding = encoding if encoding is not None else config.CSV_ENCODING
    limit = sample_size if sample_size is not None else config.SCHEMA_SAMPLE_SIZE
    try:
        with open(path, newline="", encoding=effective_encoding) as fh:
            if delimiter is None:
                try:
                    probe = fh.read(config.PROBE_CHUNK_BYTES)
                    fh.seek(0)
                    dialect = csv.Sniffer().sniff(probe)
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = config.CSV_DELIMITER

            reader = csv.reader(fh, delimiter=delimiter)
            headers = next(reader)
            sample: list[list[str]] = []
            row_count = 0
            for row in reader:
                if row_count < limit:
                    sample.append(row)
                row_count += 1
    except Exception:
        return None

    return headers, sample, row_count


def _map_parquet_type(pa_type: object) -> str:
    """Map a pyarrow physical type to a ``ColumnSchema.dtype`` string.

    See the parquet-conversion spec § 3.2 for the full mapping table.
    """
    import pyarrow as pa

    # Integral types
    if pa.types.is_integer(pa_type):
        return "numeric"

    # Floating point
    if pa.types.is_floating(pa_type):
        return "numeric"

    # Decimal
    if pa.types.is_decimal(pa_type):
        return "numeric"

    # Boolean
    if pa.types.is_boolean(pa_type):
        return "categorical/text"

    # String / binary types
    if pa.types.is_string(pa_type) or pa.types.is_large_string(pa_type):
        return "categorical/text"
    if pa.types.is_binary(pa_type) or pa.types.is_large_binary(pa_type):
        return "categorical/text"
    if pa.types.is_fixed_size_binary(pa_type):
        return "categorical/text"

    # Temporal types (stored as text in the model)
    if pa.types.is_timestamp(pa_type) or pa.types.is_date(pa_type) or pa.types.is_time(pa_type):
        return "categorical/text"

    # Nested / complex
    if pa.types.is_list(pa_type) or pa.types.is_map(pa_type) or pa.types.is_struct(pa_type):
        return "unknown"

    # Fallback for anything else
    return "categorical/text"


def _classify_parquet_read_failure(exc: Exception) -> str:
    """Classify a staged-Parquet read failure into a closed vocabulary token.

    Returns one of:

    - ``"corrupt/parse"`` — invalid/truncated data, i.e. a
      :class:`pyarrow.ArrowInvalid` error;
    - ``"io/permission"`` — filesystem-level errors (:class:`OSError`, which
      :class:`pyarrow.ArrowIOError` and :class:`PermissionError` both subclass);
    - ``"other"`` — any other exception.

    The returned token is the single source of truth for the RC-R17 warning
    vocabulary; callers interpolate it verbatim rather than re-deriving it.

    Args:
        exc: The exception raised while reading a staged Parquet file.

    Returns:
        One of ``"corrupt/parse"``, ``"io/permission"``, or ``"other"``.
    """
    if isinstance(exc, pa.ArrowInvalid):
        return "corrupt/parse"
    if isinstance(exc, OSError):
        return "io/permission"
    return "other"


def _read_parquet_sample(
    parquet_path: Path,
) -> tuple[list[str], list[list[str]], pq.ParquetFile]:
    """Read header, sample rows, and the ParquetFile handle from a Parquet file.

    Returns ``(column_names, sample_rows, parquet_file)``.

    Raises:
        On any read failure — e.g. :class:`pyarrow.ArrowInvalid` for corrupt or
        truncated data, or :class:`OSError` for IO/permission errors.  Callers
        are expected to catch and classify the exception (see
        :func:`_classify_parquet_read_failure`) before falling back to CSV.

    Iterates over pyarrow arrays directly — does not depend on pandas.
    """
    pf = pq.ParquetFile(parquet_path)
    column_names = pf.schema_arrow.names

    # Read first row group for sampling
    table = pf.read_row_groups([0])
    num_rows = table.num_rows
    limit = min(num_rows, config.SCHEMA_SAMPLE_SIZE)

    # Convert to list-of-lists for compatibility with CSV path
    rows: list[list[str]] = []
    for i in range(limit):
        row: list[str] = []
        for col in column_names:
            col_array = table.column(col)
            val = col_array[i].as_py() if i < len(col_array) else None
            if val is None:
                row.append("")
            else:
                row.append(str(val))
        rows.append(row)

    return column_names, rows, pf


def _warn_duplicate_remotes(cfg: DatasetConfig) -> None:
    """Emit one ``[!]`` warning per remote declared by 2+ ``[[file]]`` entries.

    Exact row counts are keyed by verbatim :attr:`FileEntry.remote`; when two
    entries declare the same remote they would overwrite one another's count.
    This pre-pass makes the resulting first-wins overwrite visible instead of
    silent.  It guards the keying invariant only — it never aborts the run.

    Deterministic: iterates ``cfg.files`` in declaration order, so warnings
    are emitted in first-declaration order of each duplicated remote.
    Never raises.
    """
    seen: dict[str, int] = {}
    for entry in cfg.files:
        seen[entry.remote] = seen.get(entry.remote, 0) + 1
    for remote, n in seen.items():
        if n > 1:
            print(
                f"  [!] Duplicate remote '{remote}' declared by multiple "
                f"[[file]] entries; keeping the first entry's row count."
            )


_WARN_STAGED_PARQUET_MISSING = (
    "  [!] Staged Parquet '{key}' not found in staging directory; "
    "falling back to original-file inference."
)
_WARN_STAGED_PARQUET_UNREADABLE = (
    "  [!] Staged Parquet '{key}' exists but could not be read "
    "({failure_class}); falling back to original-file inference."
)


def _staged_xlsx_sheet_parquets(staging_dir: Path, parquet_key: str) -> list[Path]:
    """Return staged per-sheet Parquets for an XLSX entry, dual-layout aware.

    Primary (spec) layout: ``stem__*.parquet`` double-underscore sheet files.
    Fallback (current prepare staging, backward compat): ``stem_*.parquet``
    collapsed single-underscore names — ``normalize_parquet_remote`` collapses
    runs of ``__+`` to ``_`` (``_converters.py``), so ``prepare`` writes
    ``data_got_all_aristas.parquet``, never ``data_got_all__aristas.parquet``
    and never a bare base ``data_got_all.parquet`` for multi-sheet sources.

    The fallback EXCLUDES the bare base placeholder (``c.stem != base_stem``)
    so a single-sheet artifact ``stem.parquet`` is never mistaken for a sheet
    file.  Mirrors the established precedent in
    :func:`sofer._mirror.expanded_planned_remotes` (PUB-10) and
    :func:`sofer.prepare._check_local_overwrite` (PRP-07); base-vs-sheet
    collisions are therefore no more permissive than ``allowed_output_remotes``.

    Args:
        staging_dir: Directory containing converted Parquet files.  Callers
            only invoke this when ``staging_dir is not None``.
        parquet_key: The normalized remote-relative ``.parquet`` key (lowercase)
            produced by :func:`normalize_parquet_remote`.

    Returns:
        Sorted list of matching sheet files; ``[]`` when the search directory is
        missing or nothing matches.  Never includes the bare base
        ``stem.parquet`` placeholder — the caller handles that single-file case
        separately.
    """
    base_parent = PurePosixPath(parquet_key).parent
    base_stem = PurePosixPath(parquet_key).stem
    search_dir = staging_dir / base_parent if str(base_parent) != "." else staging_dir
    if not search_dir.is_dir():
        return []
    primary = sorted(search_dir.glob(f"{base_stem}__*.parquet"))
    primary = [p for p in primary if p.is_file()]
    if primary:
        return primary
    alt = sorted(search_dir.glob(f"{base_stem}_*.parquet"))
    return [p for p in alt if p.is_file() and p.stem != base_stem]


def _is_schema_eligible(entry: FileEntry) -> bool:
    """Whether the schema report *attempts* to read *entry* (RC-R05/RC-R12).

    Convertible and not opted out.  A planned remote whose declaring entry is
    not eligible can never carry a signature **by declaration** (recursive
    tree, non-convertible remote, ``include_in_schema = false``); one that is
    eligible but yields no column **could not be read**.  Those two cases must
    not share a grouping policy (#304 D1).

    Convertibility itself comes from
    :func:`sofer._converters.is_convertible_remote`, the single owner of that
    rule (issue #372); ``include_in_schema`` is this caller's own filter.
    """
    return (
        is_convertible_remote(entry.remote, recursive=entry.recursive) and entry.include_in_schema
    )


def _note_column_origin(
    seen_names: dict[str, str],
    dup_map: dict[str, list[str]],
    col_name: str,
    origin: str,
) -> None:
    """Record *origin* as one source of *col_name* for the RC-R02 warning.

    Purely informational bookkeeping: the caller always emits its own
    ``ColumnSchema`` entry for the column, so a name repeated across files
    yields one entry per origin (#304) while the duplicate report keeps naming
    every repetition.

    Args:
        seen_names: First origin seen for each column name (mutated).
        dup_map:    Column name -> every origin declaring it (mutated).
        col_name:   Header as collected.
        origin:     The declaring origin (staged Parquet key or remote).
    """
    if col_name in seen_names:
        dup_map.setdefault(col_name, [seen_names[col_name]]).append(origin)
    else:
        seen_names[col_name] = origin


def _build_schema_report_impl(
    cfg: DatasetConfig,
    csv_delimiter: str | None,
    csv_encoding: str | None,
    staging_dir: Path | None,
) -> tuple[list[ColumnSchema], dict[str, int]]:
    """Shared body of :func:`build_schema_report` and its *with_rows* variant.

    Args:
        cfg:           Dataset configuration.
        csv_delimiter: Delimiter override (``None`` = use ``cfg.csv_delimiter``,
                       with Sniffer fallback).
        csv_encoding:  File encoding (``None`` = use ``cfg.csv_encoding``).
        staging_dir:   Directory containing converted Parquet files.  When set,
                       the function checks for a ``.parquet`` file for each CSV
                       entry before falling back to CSV reading.

    Returns:
        ``(columns, row_counts)`` where *row_counts* maps each counted file's
        verbatim remote path (``entry.remote``, POSIX-style — identical to how
        ``planned_remotes`` and ``configs.data_files`` render remotes) to its
        EXACT row count (Parquet metadata vs. fully-read CSV rows).  Remotes
        are unique per well-formed dataset; if duplicates are declared anyway,
        the FIRST entry's count is kept (``setdefault``) after a ``[!]``
        warning from :func:`_warn_duplicate_remotes`.  Files that cannot be
        read contribute no entry.

        Gate-review note: because unreadable files contribute no entry, if the
        first-declared entry's file cannot be read while a later same-remote
        entry's file can, the later entry stores its count under the shared
        remote key.
    """
    _warn_duplicate_remotes(cfg)
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    delimiter = csv_delimiter or cfg.csv_delimiter
    csv_encoding = csv_encoding or cfg.csv_encoding
    columns: list[ColumnSchema] = []
    row_counts: dict[str, int] = {}
    seen_names: dict[str, str] = {}
    _dup_map: dict[str, list[str]] = {}
    _had_potential_csv_entries = False
    _warned_missing: set[str] = set()
    _warned_unreadable: set[str] = set()

    from ._converters import normalize_parquet_remote

    for entry in cfg.files:
        if not is_convertible_remote(entry.remote, recursive=entry.recursive):
            continue

        _had_potential_csv_entries = True

        if not entry.include_in_schema:
            continue

        suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()

        local = entry.resolve(base)

        # Determine if we can read from Parquet instead of original
        use_parquet = False
        parquet_path = None
        parquet_key = ""
        origin_name = local.name  # used for disambiguation
        # XLSX multi-sheet: we will handle per-sheet below
        is_xlsx = suffix == ".xlsx"

        # Resolve the staged Parquet by its **normalized** remote-relative key
        if staging_dir is not None and bool(entry.convert_to_parquet):
            parquet_key = normalize_parquet_remote(parquet_remote_for(entry.remote))
            # For XLSX, check multi-sheet files first
            if is_xlsx:
                sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)
                single = staging_dir / PurePosixPath(parquet_key)
                if single.is_file():
                    sheet_paths.append(single)
                if sheet_paths:
                    # Mark for multi-sheet handling — we will loop per sheet
                    parquet_path = sheet_paths[0]  # placeholder for single-path logic
                    # We set a flag to handle multi-sheet separately
                    use_parquet = True  # actual handling is per-sheet below
                    origin_name = parquet_key  # will be overridden per sheet
                elif parquet_key not in _warned_missing:
                    _warned_missing.add(parquet_key)
                    print(_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key))
            else:
                candidate = staging_dir / PurePosixPath(parquet_key)
                if candidate.exists():
                    use_parquet = True
                    parquet_path = candidate
                    origin_name = parquet_key
                elif parquet_key not in _warned_missing:
                    _warned_missing.add(parquet_key)
                    print(_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key))

        # For XLSX multi-sheet, collect sheet paths to iterate
        xlsx_sheet_paths: list[Path] = []
        if is_xlsx and staging_dir is not None and bool(entry.convert_to_parquet):
            xlsx_sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)
            single = staging_dir / PurePosixPath(parquet_key)
            if single.is_file():
                xlsx_sheet_paths.append(single)

        parquet_result = None
        if use_parquet and parquet_path is not None and not is_xlsx:
            # ── Read from Parquet (single file) ───────────────────────────
            try:
                parquet_result = _read_parquet_sample(parquet_path)
            except Exception as exc:  # classify + fall back (RC-R17)
                failure_class = _classify_parquet_read_failure(exc)
                if parquet_key not in _warned_unreadable:
                    _warned_unreadable.add(parquet_key)
                    print(
                        _WARN_STAGED_PARQUET_UNREADABLE.format(
                            key=parquet_key, failure_class=failure_class
                        )
                    )
                use_parquet = False

        if use_parquet and is_xlsx and xlsx_sheet_paths and staging_dir is not None:
            # ── XLSX multi-sheet: each sheet parquet contributes columns ─
            for sheet_path in xlsx_sheet_paths:
                assert staging_dir is not None
                sheet_origin = sheet_path.relative_to(staging_dir).as_posix()
                try:
                    headers_s, rows_s, pf_s = _read_parquet_sample(sheet_path)
                except Exception as exc:
                    failure_class = _classify_parquet_read_failure(exc)
                    if sheet_origin not in _warned_unreadable:
                        _warned_unreadable.add(sheet_origin)
                        print(
                            _WARN_STAGED_PARQUET_UNREADABLE.format(
                                key=sheet_origin, failure_class=failure_class
                            )
                        )
                    continue
                sample_s = rows_s[: min(len(rows_s), config.SCHEMA_SAMPLE_SIZE)]
                row_counts.setdefault(entry.remote + f"::{sheet_origin}", pf_s.metadata.num_rows)
                # Also keep primary remote count as sum? Keep per-sheet counts only
                for idx, col in enumerate(headers_s):
                    col_name = col
                    # Every origin keeps its own entry; the name only feeds the
                    # RC-R02 duplicate warning (#304).
                    _note_column_origin(seen_names, _dup_map, col_name, sheet_origin)
                    pa_field = pf_s.schema_arrow.field(idx)
                    dtype = _map_parquet_type(pa_field.type)
                    nullable = pa_field.nullable
                    col_values: list[str] = []
                    for row in sample_s:
                        v = row[idx] if idx < len(row) else ""
                        col_values.append(v)
                    n_total = len(sample_s)
                    n_missing = sum(
                        1
                        for v in col_values
                        if not v.strip() or v.strip().upper() in MISSING_VALUE_SENTINELS
                    )
                    pct_missing = round(n_missing / n_total * 100, 1) if n_total else 0.0
                    non_missing = [
                        v
                        for v in col_values
                        if v.strip() and v.strip().upper() not in MISSING_VALUE_SENTINELS
                    ]
                    example = non_missing[0] if non_missing else ""
                    n_unique = count_unique_non_missing(col_values)
                    columns.append(
                        ColumnSchema(
                            name=col_name,
                            dtype=dtype,
                            nullable=nullable,
                            example=example,
                            unique=n_unique,
                            missing=pct_missing,
                            hf_dtype=_parquet_to_hf_dtype(pa_field.type),
                            origin=sheet_origin,
                        )
                    )
            # Skip single-file parquet branch and fallback for this entry
            continue

        if use_parquet and not is_xlsx:
            assert parquet_result is not None
            headers, rows, pf = parquet_result
            sample = rows[: min(len(rows), config.SCHEMA_SAMPLE_SIZE)]
            # Key by verbatim remote (first-wins via setdefault) — NOT the
            # flat-stem parquet origin, which collides across subdirectories.
            row_counts.setdefault(entry.remote, pf.metadata.num_rows)

            for idx, col in enumerate(headers):
                col_name = col

                # Every origin keeps its own entry; the name only feeds the
                # RC-R02 duplicate warning (#304).
                _note_column_origin(seen_names, _dup_map, col_name, origin_name)

                # dtype from Parquet physical type
                pa_field = pf.schema_arrow.field(idx)
                dtype = _map_parquet_type(pa_field.type)
                nullable = pa_field.nullable

                col_values2: list[str] = []
                for row in sample:
                    v = row[idx] if idx < len(row) else ""
                    col_values2.append(v)

                n_total = len(col_values2)
                n_missing = sum(
                    1
                    for v in col_values2
                    if not v.strip() or v.strip().upper() in MISSING_VALUE_SENTINELS
                )
                pct_missing = round(n_missing / n_total * 100, 1) if n_total else 0.0

                non_missing = [
                    v
                    for v in col_values2
                    if v.strip() and v.strip().upper() not in MISSING_VALUE_SENTINELS
                ]
                example = non_missing[0] if non_missing else ""
                n_unique = count_unique_non_missing(col_values2)

                columns.append(
                    ColumnSchema(
                        name=col_name,
                        dtype=dtype,
                        nullable=nullable,
                        example=example,
                        unique=n_unique,
                        missing=pct_missing,
                        hf_dtype=_parquet_to_hf_dtype(pa_field.type),
                        origin=origin_name,
                    )
                )
        else:
            # ── Read from original file (fallback for any convertible suffix) ─
            row_count: int | None = None
            if suffix == ".xlsx":
                try:
                    import openpyxl

                    wb_f = openpyxl.load_workbook(local, read_only=True, data_only=True)
                    ws_f = wb_f[wb_f.sheetnames[0]]
                    rows_iter_f = ws_f.iter_rows(values_only=True)
                    try:
                        header_row_f = next(rows_iter_f)
                    except StopIteration:
                        continue
                    if header_row_f is None or all(v is None for v in header_row_f):
                        continue
                    headers_f = [str(v).strip() if v is not None else "" for v in header_row_f]
                    headers_f = [normalize_header(h) for h in headers_f]
                    rows_f: list[list[str]] = []
                    for row_f in rows_iter_f:
                        vals_f = [str(v) if v is not None else "" for v in (row_f or [])]
                        # pad/truncate
                        if len(vals_f) < len(headers_f):
                            vals_f.extend([""] * (len(headers_f) - len(vals_f)))
                        elif len(vals_f) > len(headers_f):
                            vals_f = vals_f[: len(headers_f)]
                        rows_f.append(vals_f)
                    wb_f.close()
                    headers, rows = headers_f, rows_f
                except Exception:
                    continue
            elif suffix == ".jsonl":
                try:
                    import json as _json

                    json_rows: list[dict[str, object]] = []
                    with open(local, encoding="utf-8") as jf:
                        for line in jf:
                            line = line.strip()
                            if not line:
                                continue
                            json_rows.append(_json.loads(line))
                    if not json_rows:
                        continue
                    # Union of keys
                    headers = sorted({k for r in json_rows for k in r.keys()})
                    headers = [normalize_header(h) for h in headers]
                    rows = [[str(r.get(h, "")) for h in headers] for r in json_rows]
                except Exception:
                    continue
            else:
                # csv/tsv: one pass that keeps only the configured sample while
                # counting every record (issue #373). Retaining the whole file
                # would make schema_sample_size a bound on inference work, not on
                # memory.
                tsv_delim = "\t" if suffix == ".tsv" else delimiter
                csv_sample = _read_csv_sample(
                    local,
                    delimiter=tsv_delim,
                    encoding=csv_encoding,
                    sample_size=config.SCHEMA_SAMPLE_SIZE,
                )
                if csv_sample is None:
                    continue  # skip missing / unreadable files gracefully
                headers, rows, row_count = csv_sample
                # ``rows`` is already capped by the reader; the exact total is
                # ``row_count`` and must not be taken from ``len(rows)``.
            # Normalize headers: strip whitespace, preserve case
            headers = [normalize_header(h) for h in headers]
            sample = rows[: min(len(rows), config.SCHEMA_SAMPLE_SIZE)]
            if row_count is None:
                row_count = len(rows)
            # Key by verbatim remote (first-wins via setdefault) — local
            # filenames collide across subdirectories with the same basename.
            row_counts.setdefault(entry.remote, row_count)

            for idx, col in enumerate(headers):
                col_name = col

                # Every origin keeps its own entry; the name only feeds the
                # RC-R02 duplicate warning (#304).
                _note_column_origin(seen_names, _dup_map, col_name, entry.remote)

                col_values = []
                for row in sample:
                    v = row[idx] if idx < len(row) else ""
                    col_values.append(v)

                n_total = len(sample)
                n_missing = sum(
                    1
                    for v in col_values
                    if not v.strip() or v.strip().upper() in MISSING_VALUE_SENTINELS
                )
                pct_missing = round(n_missing / n_total * 100, 1) if n_total else 0.0

                dtype = infer_column_type(col_values)

                # Detect boolean columns from CSV values
                hf_dtype: str | None = None
                if dtype == "categorical/text" and _csv_values_look_like_bool(col_values):
                    hf_dtype = "bool"
                elif dtype == "numeric":
                    hf_dtype = _HF_FEATURE_MAP["numeric"]  # "float64" — fallback

                non_missing = [
                    v
                    for v in col_values
                    if v.strip() and v.strip().upper() not in MISSING_VALUE_SENTINELS
                ]
                example = non_missing[0] if non_missing else ""
                n_unique = count_unique_non_missing(col_values)

                columns.append(
                    ColumnSchema(
                        name=col_name,
                        dtype=dtype,
                        nullable=n_missing > 0,
                        example=example,
                        unique=n_unique,
                        missing=pct_missing,
                        hf_dtype=hf_dtype,
                        origin=entry.remote,
                    )
                )

    if not columns and _had_potential_csv_entries:
        print("  [!] All files excluded from schema (include_in_schema = false on every entry).")

    if _dup_map:
        n_dups = len(_dup_map)
        if n_dups <= config.SCHEMA_DUP_THRESHOLD:
            for col_name, origins in _dup_map.items():
                prev_origin = origins[0]
                for other_origin in origins[1:]:
                    print(
                        f"  [!] Duplicate column '{col_name}' across files "
                        f"({prev_origin}, {other_origin}); "
                        f"each file keeps its own schema entries."
                    )
        else:
            # Sort by frequency (most duplicated first), honouring the
            # configured report cap shared with publish output (issue #189).
            limit = config.REPORT_MAX_MODIFIED
            top = sorted(_dup_map, key=lambda k: len(_dup_map[k]), reverse=True)[:limit]
            top5_str = ", ".join(top)
            print(
                f"  [i] {n_dups} columns appear in multiple files. "
                f"Most duplicated: {top5_str}.\n"
                f"      This is normal for relational datasets where label/lookup tables "
                f"share column names with data tables.\n"
                f"      Tip: add `include_in_schema = false` to label file entries "
                f"in dataset.toml to exclude them from the schema report."
            )

    return columns, row_counts


def build_schema_report(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str | None = None,
    staging_dir: Path | None = None,
) -> list[ColumnSchema]:
    """Analyse CSV / Parquet files declared in *cfg* and produce a typed schema report.

    When *staging_dir* is provided and a matching ``.parquet`` file exists for a
    CSV entry (and the entry is not marked ``upload_as_csv``), the function reads
    column names and types from the Parquet schema instead of inferring from CSV
    sample data.

    Args:
        cfg:           Dataset configuration.
        csv_delimiter: Delimiter override (``None`` = use ``cfg.csv_delimiter``,
                       with Sniffer fallback).
        csv_encoding:  File encoding (``None`` = use ``cfg.csv_encoding``).
        staging_dir:   Directory containing converted Parquet files.  When set,
                       the function checks for a ``.parquet`` file for each CSV
                       entry before falling back to CSV reading.

    Returns:
        A list of :class:`ColumnSchema` entries — one per ``(origin, name)``
        pair, so a column name declared by several files yields one entry per
        file, each carrying its source file in :attr:`ColumnSchema.origin`.
        The duplicate warnings emitted below are informational and never remove
        an entry (#304).  Callers that also need exact per-file row counts
        should use :func:`build_schema_report_with_rows`.
    """
    columns, _row_counts = _build_schema_report_impl(cfg, csv_delimiter, csv_encoding, staging_dir)
    return columns


def build_schema_report_with_rows(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str | None = None,
    staging_dir: Path | None = None,
) -> tuple[list[ColumnSchema], dict[str, int]]:
    """Like :func:`build_schema_report`, but also return exact per-file row counts.

    Args:
        cfg:           Dataset configuration.
        csv_delimiter: Delimiter override (``None`` = use ``cfg.csv_delimiter``,
                       with Sniffer fallback).
        csv_encoding:  File encoding (``None`` = use ``cfg.csv_encoding``).
        staging_dir:   Directory containing converted Parquet files (see
                       :func:`build_schema_report`).

    Returns:
        ``(columns, row_counts)`` — the same schema report as
        :func:`build_schema_report`, plus a dict mapping each counted file's
        verbatim remote path (``entry.remote``, POSIX-style) to its EXACT
        row count (Parquet: ``pf.metadata.num_rows``; CSV: ``len(rows)`` on
        the fully read file).  Remotes are unique per well-formed dataset;
        duplicate declarations keep the FIRST entry's count and emit a
        ``[!]`` warning.  Row counts are never capped by the schema sample
        size.
    """
    return _build_schema_report_impl(cfg, csv_delimiter, csv_encoding, staging_dir)


# ═══════════════════════════════════════════════════════════════════════════════
#  Dataset Card (README.md)
# ═══════════════════════════════════════════════════════════════════════════════


def _sheet_label_from_origin(origin: str) -> str:
    """Derive a human label from a ColumnSchema origin for card summaries."""
    if not origin:
        return "unknown"
    stem = PurePosixPath(origin).stem
    if not stem:
        return "unknown"
    if "__" in origin:
        # Preserve explicitly namespaced sheet suffix (pre-normalized)
        return stem.split("__")[-1]
    return stem


def _group_by_origin(schema: list[ColumnSchema]) -> dict[str, list[ColumnSchema]]:
    """Group ColumnSchema entries by sheet/file origin for per-table card rendering.

    Groups by the verbatim ``origin`` value; display labels are derived from
    the origin's stem with common-prefix stripping so ``data_got_all_aristas``
    / ``data_got_all_nodos`` become ``aristas`` / ``nodos`` while ``a`` / ``b``
    stay ``a`` / ``b``.
    """
    if not schema:
        return {}
    raw: dict[str, list[ColumnSchema]] = {}
    for col in schema:
        key = col.origin if col.origin else "unknown"
        raw.setdefault(key, []).append(col)

    if len(raw) == 1:
        origin = next(iter(raw))
        label = _sheet_label_from_origin(origin)
        # Single group: keep full stem; label already full stem.
        return {label: next(iter(raw.values()))}

    # Multiple groups: compute longest common prefix among stems for suffix extraction
    stems = [PurePosixPath(k).stem if k != "unknown" else "unknown" for k in raw.keys()]
    prefix = stems[0]
    for st in stems[1:]:
        while prefix and not st.startswith(prefix):
            prefix = prefix[:-1]
        if not prefix:
            break

    result: dict[str, list[ColumnSchema]] = {}
    for (origin, cols), stem in zip(raw.items(), stems):
        if prefix and stem.startswith(prefix):
            suffix = stem[len(prefix) :].lstrip("_")
            label = suffix if suffix else stem
        else:
            # No common prefix — if origin was normalized collapsed (``_``) and we
            # have a sheet-like suffix, try "__" split first, then keep full stem.
            if "__" in origin:
                label = stem.split("__")[-1]
            else:
                label = stem
        # Ensure uniqueness of display label
        base = label
        n = 2
        while label in result:
            label = f"{base}_{n}"
            n += 1
        result[label] = cols
    return result


def _infer_language(filename: str) -> str:
    """Infer the programming language for fenced code blocks from a file path."""
    ext = Path(filename).suffix.lower()
    lang_map = {
        ".r": "r",
        ".rmd": "r",
        ".py": "python",
        ".jl": "julia",
        ".ipynb": "json",
        ".sh": "bash",
        ".sql": "sql",
        ".do": "stata",
        ".m": "matlab",
    }
    return lang_map.get(ext, "")


# ═══════════════════════════════════════════════════════════════════════════════
#  Mixed-schema config generation (issue #292)
# ═══════════════════════════════════════════════════════════════════════════════


def _feature_dtype(col: ColumnSchema) -> str:
    """Return the HF feature dtype a column emits in ``dataset_info.features``.

    Single source of truth shared by the feature list and the grouping
    signature, so a group's signature is exactly the schema of its emitted
    features.
    """
    return col.hf_dtype if col.hf_dtype is not None else _hf_feature_type(col.dtype)


def _slugify_config_name(value: str) -> str:
    """Return a validated HF config identifier slug (issue #292, S3/D3).

    Lowercases *value*, transliterates accents to ASCII, collapses every run
    of characters outside the configured ``[a-z0-9._-]`` set to the configured
    separator, trims separators from both ends, and truncates to the configured
    maximum length.  ``pretty_name`` must never be passed here (S3); callers
    pass ``[dataset] name`` or a remote file stem.

    Args:
        value: Candidate identifier source (name or file stem).

    Returns:
        A non-empty slug matching ``[a-z0-9._-]+``, or the configured
        fallback when nothing usable survives sanitization.
    """
    separator = config.CARD_CONFIG_SLUG_SEPARATOR
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(config.CARD_CONFIG_SLUG_INVALID_PATTERN, separator, ascii_value.lower())
    # Collapse separator runs so a replacement beside a literal hyphen (" - ")
    # cannot leave "---" in the identifier.
    slug = re.sub(re.escape(separator) + "+", separator, slug)
    slug = slug.strip(separator + "_.")
    if len(slug) > config.CARD_CONFIG_SLUG_MAX_LENGTH:
        slug = slug[: config.CARD_CONFIG_SLUG_MAX_LENGTH].strip(separator + "_.")
    return slug or config.CARD_CONFIG_SLUG_FALLBACK


def _origin_signatures(schema: list[ColumnSchema]) -> dict[str, tuple[tuple[str, str], ...]]:
    """Map every schema origin to its ordered ``(name, dtype)`` signature (D2).

    Origins are the remote paths the schema report attributed its columns to
    (``ColumnSchema.origin``); origin-less fixtures are ignored here and
    handled separately by :func:`_features_for_group`.
    """
    by_origin: dict[str, list[tuple[str, str]]] = {}
    for col in schema:
        if not col.origin:
            continue
        by_origin.setdefault(col.origin, []).append((col.name, _feature_dtype(col)))
    return {origin: tuple(cols) for origin, cols in by_origin.items()}


def _remote_origin_aliases(
    cfg: DatasetConfig,
    remotes: list[str],
) -> dict[str, list[str]]:
    """Map each planned remote to the schema/row-count keys that describe it.

    A staged-Parquet schema origin is the normalised ``.parquet`` remote and
    already equals the planned remote (RC-R05).  The CSV fallback path, and
    every ``build_schema_report_with_rows`` call without a staging mirror,
    keys both the ``ColumnSchema.origin`` and the row count by the entry's
    declared ``FileEntry.remote`` instead.  Returning both candidates lets
    grouping and counts resolve with or without a mirror.

    Args:
        cfg:     Dataset configuration.
        remotes: Planned remote paths.

    Returns:
        Mapping ``planned remote -> [candidate origin/count keys]`` in lookup
        priority order (the remote itself first).
    """
    from ._converters import normalize_parquet_remote

    aliases: dict[str, list[str]] = {}
    for remote in remotes:
        candidates = [remote]
        for entry in cfg.files:
            if normalize_parquet_remote(parquet_remote_for(entry.remote)) == remote:
                if entry.remote not in candidates:
                    candidates.append(entry.remote)
        aliases[remote] = candidates
    return aliases


def _schema_eligible_remotes(
    cfg: DatasetConfig,
    remotes: list[str],
    aliases: dict[str, list[str]] | None = None,
) -> set[str]:
    """Return the planned remotes the schema report *attempts* to read (#304).

    A remote is schema-eligible when a declaring ``[[file]]`` entry that maps to
    it (:func:`_remote_origin_aliases`) is convertible and not
    ``include_in_schema = false`` (:func:`_is_schema_eligible`).  The grouping
    uses this to separate "eligible but could not be read" — signature unknown —
    from "declared non-schema" (recursive tree, non-convertible remote,
    explicit opt-out), which keeps its own config group (RC-R03/RC-R12).

    Args:
        cfg:     Dataset configuration.
        remotes: Planned remote paths.
        aliases: Pre-computed alias map (``None`` to derive it here).

    Returns:
        The subset of *remotes* that the schema report attempts to read.
    """
    from ._converters import normalize_parquet_remote

    lookup = aliases if aliases is not None else _remote_origin_aliases(cfg, remotes)
    eligible_keys: set[str] = set()
    for entry in cfg.files:
        if not _is_schema_eligible(entry):
            continue
        eligible_keys.add(entry.remote)
        eligible_keys.add(normalize_parquet_remote(parquet_remote_for(entry.remote)))

    return {
        remote
        for remote in remotes
        if any(key in eligible_keys for key in lookup.get(remote, [remote]))
    }


def group_remotes_by_schema(
    remotes: list[str],
    schema: list[ColumnSchema],
    aliases: dict[str, list[str]] | None = None,
    schema_eligible: set[str] | None = None,
) -> list[list[str]] | None:
    """Group planned remotes into one config group per column signature.

    Issue #292: the previous card merged every remote into one ``train`` split,
    which is unloadable when the files do not share a schema.  This groups the
    remotes whose ``ColumnSchema.origin`` yields the same ordered
    ``(name, dtype)`` signature.  A remote with no schema entry is classified
    before it is grouped (#304):

    - **declared non-schema** (recursive tree, non-convertible suffix, or
      ``include_in_schema = false``) keeps its own group, as before
      (RC-R03/RC-R12).  These are the remotes absent from *schema_eligible*.
    - **unassessed** (schema-eligible, yet no column: the file could not be
      read) is *signature unknown*.  It joins the sole signature group when
      exactly one exists, and otherwise makes the corpus ungroupable — an
      unknown signature never invents a group of its own.

    Args:
        remotes: Planned remote paths (declaration order).
        schema:  Column schema report (``build_schema_report``).
        aliases: Optional ``remote -> [origin keys]`` map
                 (:func:`_remote_origin_aliases`); ``None`` matches the
                 remote itself only.
        schema_eligible: Remotes the schema report attempted to read
                 (:func:`_schema_eligible_remotes`); ``None``/empty treats every
                 unresolved remote as declared non-schema.

    Returns:
        A list of remote-path groups, or ``None`` when the corpus is
        **ungroupable** — it declares more than one remote and the schema
        report carries no column for any of them, so every grouping would be a
        guess (S2/D1); the caller then emits no ``configs``/``dataset_info``.
    """
    signatures = _origin_signatures(schema)
    if not signatures:
        # No origin attribution at all.  A non-empty schema still describes one
        # table (hand-built fixtures); an empty one is ungroupable when it
        # would merge several remotes on a guess (S2/D1).
        if schema:
            return [list(remotes)]
        return None if len(remotes) > 1 else [list(remotes)]

    lookup = aliases or {}
    groups: dict[tuple[tuple[str, str], ...], list[str]] = {}
    unresolved: list[str] = []
    for remote in remotes:
        signature: tuple[tuple[str, str], ...] | None = None
        for candidate in lookup.get(remote, [remote]):
            signature = signatures.get(candidate)
            if signature is not None:
                break
        if signature is None:
            unresolved.append(remote)
        else:
            groups.setdefault(signature, []).append(remote)

    eligible = schema_eligible or set()
    unknown = [remote for remote in unresolved if remote in eligible]
    declared = [remote for remote in unresolved if remote not in eligible]

    grouped = list(groups.values())
    if not grouped:
        # Signatures exist but none is attributable to a planned remote
        # (origin-less hand-built fixtures): one group for every remote.
        return [list(remotes)]
    if unknown and len(grouped) > 1:
        # A schema-eligible remote yielded no column, so it could not be read
        # and no grouping can be vouched for (#304 D1).
        return None
    if len(grouped) == 1:
        # A sole signature group absorbs both kinds of unresolved remote.
        grouped[0].extend(unknown)
        grouped[0].extend(declared)
        return grouped
    if declared:
        grouped.append(declared)
    return grouped


def _config_name_for_group(
    cfg: DatasetConfig,
    group_remotes: list[str],
    total_groups: int,
) -> str:
    """Return the slugged ``config_name`` for one group (D3).

    A single group keeps ``cfg.config_names[0]`` when declared, else the slug
    of ``[dataset] name``.  Multiple groups take the slug of the group's first
    remote file stem.  ``pretty_name`` is never consulted (S3).

    Args:
        cfg:           Dataset configuration.
        group_remotes: Remotes assigned to this group (declaration order).
        total_groups:  Number of groups the card will emit.

    Returns:
        A validated config identifier slug.
    """
    if total_groups <= 1:
        base = cfg.config_names[0] if cfg.config_names else cfg.name
    else:
        base = PurePosixPath(group_remotes[0].replace("\\", "/")).stem or cfg.name
    return _slugify_config_name(base)


def _name_groups(
    cfg: DatasetConfig,
    groups: list[list[str]],
) -> list[tuple[str, list[str]]]:
    """Pair each remote group with a unique slugged config name (D3).

    Slugs that collide (for example two same-stem remotes in different
    directories) get a numeric suffix so no two configs share a name.
    """
    names = [_config_name_for_group(cfg, group, len(groups)) for group in groups]
    counts: dict[str, int] = {}
    named: list[tuple[str, list[str]]] = []
    for name, group in zip(names, groups):
        count = counts.get(name, 0) + 1
        counts[name] = count
        named.append((name if count == 1 else f"{name}_{count}", group))
    return named


def schema_config_plan(
    cfg: DatasetConfig,
    schema: list[ColumnSchema],
    keep_csv: bool = False,
    staging_dir: Path | None = None,
) -> list[tuple[str, list[str]]] | None:
    """Compute the ``(config_name, remotes)`` plan the card will emit.

    The single home for the remote derivation plus schema grouping shared by
    :func:`build_dataset_card` and the prepare-time config warning (AGENTS.md
    rule 4).

    Args:
        cfg:         Dataset configuration.
        schema:      Column schema report.
        keep_csv:    Whether converted CSVs are also delivered at their remote.
        staging_dir: Mirror layout root for XLSX expansion (see
                     :func:`sofer._mirror.expanded_planned_remotes`).

    Returns:
        One ``(config_name, remotes)`` pair per schema group, or ``None`` when
        the corpus is ungroupable (see :func:`group_remotes_by_schema`).
    """
    if staging_dir is not None and staging_dir.is_dir():
        remotes = expanded_planned_remotes(cfg, keep_csv, staging_dir)
    else:
        remotes = planned_remotes(cfg, keep_csv)
    aliases = _remote_origin_aliases(cfg, remotes)
    groups = group_remotes_by_schema(
        remotes, schema, aliases, _schema_eligible_remotes(cfg, remotes, aliases)
    )
    if groups is None:
        return None
    return _name_groups(cfg, groups)


def _features_for_group(
    group_remotes: list[str],
    schema: list[ColumnSchema],
    single_group: bool,
    aliases: dict[str, list[str]] | None = None,
) -> list[dict[str, str]]:
    """Return the ``dataset_info.features`` list for one config group.

    Columns are attributed structurally via :attr:`ColumnSchema.origin`
    (RC-R06), resolved through the same alias map grouping and row counts use
    (:func:`_remote_origin_aliases`), so a CSV-fallback schema whose origins are
    the declared ``.csv`` remotes still matches its planned ``.parquet`` remote
    (#304 S6).  A single-group card keeps every schema entry — including
    origin-less hand-built fixtures — exactly as before.

    A config's features describe ONE schema, so a name repeated across the
    group's files is listed once, at its first occurrence.  Since #304 the
    schema report carries one entry per ``(origin, name)``, so that repetition
    is real data rather than a healed display artifact.

    Args:
        group_remotes: Planned remotes assigned to this config group.
        schema:        Column schema report.
        single_group:  Whether the card emits exactly one config.
        aliases:       Optional ``remote -> [origin keys]`` map.

    Returns:
        One ``{"name": ..., "dtype": ...}`` dict per distinct column name.
    """
    allowed: set[str] | None = None
    if not single_group:
        allowed = set()
        for remote in group_remotes:
            allowed.update((aliases or {}).get(remote, [remote]))

    features: list[dict[str, str]] = []
    seen: set[str] = set()
    for col in schema:
        if allowed is not None and col.origin not in allowed:
            continue
        if col.name in seen:
            continue
        seen.add(col.name)
        features.append({"name": col.name, "dtype": _feature_dtype(col)})
    return features


def _row_count_for_remote(
    remote: str,
    row_counts: dict[str, int] | None,
    aliases: dict[str, list[str]] | None,
) -> int | None:
    """Return the exact row count recorded for *remote*, if any.

    Looks under the planned remote and its origin aliases (the CSV fallback
    keys counts by ``FileEntry.remote``, RC-R07); XLSX sheet counts are keyed
    ``<declared file>::<sheet remote>``, so a ``::`` suffix match is the last
    resort.
    """
    if not row_counts:
        return None
    for candidate in (aliases or {}).get(remote, [remote]):
        if candidate in row_counts:
            return row_counts[candidate]
    suffix = "::" + remote
    for key, value in row_counts.items():
        if key.endswith(suffix):
            return value
    return None


def _build_dataset_info(
    config_name: str,
    group_remotes: list[str],
    schema: list[ColumnSchema],
    row_counts: dict[str, int] | None,
    single_group: bool,
    aliases: dict[str, list[str]] | None = None,
    with_splits: bool = True,
) -> dict[str, object]:
    """Build one ``dataset_info`` block for a config group (D5).

    ``num_examples`` sums the group's exact row counts when any are known,
    else falls back to the conservative per-file product for **that group
    only** (RC-R12).  The single builder is shared by the single-group and
    multi-group paths (AGENTS.md rule 4).
    """
    info: dict[str, object] = {
        "config_name": config_name,
        "features": _features_for_group(group_remotes, schema, single_group, aliases),
    }

    if not with_splits:
        return info
    exact = [_row_count_for_remote(remote, row_counts, aliases) for remote in group_remotes]
    known = [count for count in exact if count is not None]
    if known:
        approx_rows = sum(known)
    else:
        approx_rows = len(group_remotes) * config.CARD_FALLBACK_ROWS_PER_FILE
    info["splits"] = [{"name": "train", "num_examples": approx_rows}]
    return info


def _md_visible(value: str) -> str:
    """Render *value* as printable text safe for a Markdown table cell.

    A sampled value can hold anything the source file held: a corpus reported in
    #348 has a data value that is a single NUL byte, and interpolating it
    verbatim made ``build/README.md`` — the Dataset Card, published as the
    repository's landing page — a file that ``grep`` and ``diff`` classify as
    binary. A ``|`` is the same class of defect one step milder: it splits the
    row into extra cells.

    Args:
        value: Raw data-derived text (a column name, an origin, a sample value).

    Returns:
        The same text with every Unicode ``Cc`` character replaced by its
        ``\\xNN`` escape (so a NUL reads ``\\x00`` and a newline ``\\x0a``, and
        neither can break the row or the file), and every ``|`` escaped as
        ``\\|``. GFM honours the backslash inside a code span, which is what
        keeps the cell from splitting. The escape character itself is a backslash
        in both cases, so the result is idempotent-safe to read but never
        re-escaped here.
    """
    escaped = "".join(
        f"\\x{ord(ch):02x}" if unicodedata.category(ch) == "Cc" else ch for ch in value
    )
    return escaped.replace("|", "\\|")


def _md_cell(value: str) -> str:
    """Render *value* as one code-spanned Markdown table cell.

    Args:
        value: Raw data-derived text.

    Returns:
        The value escaped by :func:`_md_visible` inside a code span. The fence is
        one backtick, or two when the escaped text itself contains a backtick — a
        single-backtick span would end early and leave the rest of the value
        outside the span, which is the same defect as an unescaped separator: the
        cell would stop meaning what the data says.
    """
    text = _md_visible(value)
    fence = "``" if "`" in text else "`"
    return f"{fence}{text}{fence}"


def _data_fields_row(entry: ColumnSchema) -> str:
    """Render one Data Fields table row.

    The single home for the row format, shared by the flat table and the
    per-sheet collapsible tables (RC-R21), so the two branches cannot drift.
    Every data-derived cell goes through :func:`_md_cell`.

    Args:
        entry: The column to render.

    Returns:
        A Markdown table row with the seven cells
        ``Column | Type | File | Nullable | Example | Unique (sample) | Missing (%)``.
        The File cell stays unfenced (its value is a file name, and the card has
        always printed it bare); ``dtype``, ``unique`` and ``missing`` are
        generated vocabularies and numbers, so they are interpolated as-is.
    """
    file_cell = _md_visible(entry.origin) if entry.origin else "-"
    nullable = "Yes" if entry.nullable else "No"
    return (
        f"| {_md_cell(entry.name)} | {entry.dtype} | {file_cell} | {nullable} | "
        f"{_md_cell(entry.example)} | {entry.unique} | {entry.missing}% |"
    )


def build_dataset_card(
    cfg: DatasetConfig,
    schema: list[ColumnSchema],
    recipe_content: str | None = None,
    study_design_content: str | None = None,
    empty_columns: list[str] | None = None,
    duplicate_rows: dict[str, int] | None = None,
    row_counts: dict[str, int] | None = None,
    keep_csv: bool = False,
    staging_dir: Path | None = None,
) -> str:
    """Generate a HF-standard Dataset Card (``README.md`` with YAML frontmatter).

    Follows the official Hugging Face Dataset Card template:
    https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/templates/datasetcard_template.md

    Dataset Structure and ``configs.data_files`` are derived via
    :func:`sofer._mirror.expanded_planned_remotes` when *staging_dir* exists
    (ground truth, RC-Universal-Card), otherwise via the logical
    :func:`planned_remotes` placeholder (fallback before prepare, PUB-10).

    Args:
        cfg:                   Dataset configuration.
        schema:                Column schema list from :func:`build_schema_report`.
        recipe_content:        Pre-loaded recipe content, or ``None``.
        study_design_content:  Pre-loaded study design content, or ``None``.
        empty_columns:         Optional list of column names that are entirely empty.
        duplicate_rows:        Optional dict mapping filenames to duplicate row counts.
        row_counts:            Optional dict mapping each file's verbatim
                               remote path (``entry.remote``, POSIX-style —
                               keys are unique per well-formed dataset) to its
                               exact data-row count (from
                               :func:`build_schema_report_with_rows`).  Each
                               config group sums its own remotes' counts;
                               a group without any exact count falls back to
                               ``CARD_FALLBACK_ROWS_PER_FILE`` per group
                               remote.
        keep_csv:              Whether converted CSVs are also delivered at their
                               original remote (the publish ``--keep-csv`` flag).
                               Governs the Dataset Structure listing only.
        staging_dir:           Mirror layout root for XLSX expansion.  ``None``
                               or not a directory falls back to the logical
                               placeholder; when it exists each eligible XLSX
                               expands to N ``stem__sheet.parquet`` entries.

    Returns:
        Complete ``README.md`` content as a single string.
    """
    _ns = "[Not specified]"

    # ── YAML frontmatter ───────────────────────────────────────────────────
    frontmatter: dict[str, object] = {}

    # -- Core metadata -------------------------------------------------------
    frontmatter["pretty_name"] = cfg.pretty_name or cfg.name
    if cfg.task_categories:
        frontmatter["task_categories"] = cfg.task_categories

    # -- Tags (always include modality and library tags) ---------------------
    tags: list[str] = list(cfg.tags)
    # Always emit 'datasets' library tag since this IS a datasets-library-compatible repo.
    if "datasets" not in tags:
        tags.append("datasets")
    # Emit 'tabular' as default modality when not already present.
    if not any(t in tags for t in config.CARD_MODALITY_TAGS):
        tags.append("tabular")
    frontmatter["tags"] = tags

    # -- size_categories: validate + emit as list ---------------------------
    if cfg.size_categories:
        categories = [c.strip() for c in cfg.size_categories.split(",") if c.strip()]
        validated: list[str] = []
        for c in categories:
            vc = _validate_size_category(c)
            if vc:
                validated.append(vc)
            else:
                print(
                    f"  [!] Invalid size_category: '{c}' — ignoring. "
                    f"Valid values: {', '.join(sorted(_SIZE_CATEGORIES))}"
                )
        if validated:
            frontmatter["size_categories"] = validated

    # -- source_datasets: emit as repo ID (validate format loosely) ----------
    if cfg.source:
        # Per HF spec, source_datasets should be a dataset repo ID
        # (e.g. 'wikipedia', 'laion/laion-2b'). cfg.source is conventionally
        # an institution name; we emit it but users should verify it.
        frontmatter["source_datasets"] = [cfg.source]

    # -- configs + dataset_info (one per schema group, issue #292) ----------
    # The card groups the planned remotes by column signature and emits one
    # `configs` entry plus its own `dataset_info` per group.  A corpus whose
    # remotes carry no schema at all is ungroupable: it emits neither block
    # and lets the Hub infer per-file (S2/D1).
    plan = schema_config_plan(cfg, schema, keep_csv, staging_dir) if cfg.files else None
    if plan is not None and cfg.files:
        configs: list[dict[str, object]] = []
        for config_name, group_remotes in plan:
            data_files: list[dict[str, object]] = [
                {"split": "train", "path": r} for r in group_remotes
            ]
            if not data_files:
                data_files.append({"split": "train", "path": "data/*"})
            entry: dict[str, object] = {
                "config_name": config_name,
                "data_files": data_files,
            }
            # D4: only a single-config card carries `default`; with several
            # schema groups load_dataset() must not silently pick one table.
            if len(plan) == 1:
                entry["default"] = True
            configs.append(entry)
        frontmatter["configs"] = configs

    # -- dataset_info (one block per config) --------------------------------
    # Kept independent of `cfg.files` (a schema-only card still reports its
    # features) but suppressed when the corpus is ungroupable, matching the
    # config suppression above.
    if schema and (plan is not None or not cfg.files):
        if plan is None:
            plan = [(_config_name_for_group(cfg, [], 1), [])]
        single_group = len(plan) == 1
        aliases = _remote_origin_aliases(cfg, [r for _n, group in plan for r in group])
        infos = [
            _build_dataset_info(
                config_name,
                group_remotes,
                schema,
                row_counts,
                single_group,
                aliases,
                with_splits=bool(cfg.files),
            )
            for config_name, group_remotes in plan
        ]
        frontmatter["dataset_info"] = infos[0] if single_group else infos

    # -- Language -----------------------------------------------------------
    if cfg.language:
        frontmatter["language"] = cfg.language

    # -- License ------------------------------------------------------------
    license_id = cfg.license.strip().lower() if cfg.license else ""
    if license_id:
        if license_id in _KNOWN_SPDX_IDS:
            frontmatter["license"] = cfg.license
        else:
            # "other" license flow
            frontmatter["license"] = "other"
            if cfg.license_name:
                frontmatter["license_name"] = cfg.license_name
            frontmatter["license_link"] = cfg.license_link or "LICENSE"
            if cfg.license_details:
                frontmatter["license_details"] = cfg.license_details
            elif license_id not in ("", "restricted"):
                frontmatter["license_details"] = cfg.license

    # -- Optional metadata --------------------------------------------------
    if cfg.annotations_creators:
        frontmatter["annotations_creators"] = cfg.annotations_creators
    if cfg.language_creators:
        frontmatter["language_creators"] = cfg.language_creators
    if cfg.language_details:
        frontmatter["language_details"] = cfg.language_details
    if cfg.multilinguality:
        frontmatter["multilinguality"] = cfg.multilinguality
    if cfg.task_ids:
        frontmatter["task_ids"] = cfg.task_ids
    if cfg.paperswithcode_id:
        frontmatter["paperswithcode_id"] = cfg.paperswithcode_id
    if cfg.config_names and len(cfg.config_names) > 1:
        frontmatter["config_names"] = cfg.config_names

    # ── Render YAML frontmatter ────────────────────────────────────────────
    yaml_block = yaml.safe_dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    header = f"---\n{yaml_block}\n---\n"

    # ══════════════════════════════════════════════════════════════════════════
    # Card body
    # ══════════════════════════════════════════════════════════════════════════

    desc = cfg.description.strip() if cfg.description else _ns
    source = cfg.source.strip() if cfg.source else _ns
    collection = cfg.collection_method.strip() if cfg.collection_method else _ns
    citation = cfg.citation.strip() if cfg.citation else _ns
    lic_display = cfg.license.strip() if cfg.license else _ns

    # ── Title ──────────────────────────────────────────────────────────────
    name = cfg.pretty_name or cfg.name
    lines = [f"# Dataset Card for {name}", "", desc, ""]

    # ── Dataset Details ────────────────────────────────────────────────────
    lines.append("## Dataset Details")
    lines.append("")
    lines.append("### Dataset Description")
    lines.append("")
    lines.append(f"- **Curated by:** {source}")
    lines.append(f"- **Language(s):** {', '.join(cfg.language) if cfg.language else _ns}")
    lines.append(f"- **License:** {lic_display}")
    lines.append("")

    # Optional: Funded by / Shared by
    if cfg.funded_by:
        lines.append(f"- **Funded by:** {cfg.funded_by}")
        lines.append("")
    if cfg.shared_by:
        lines.append(f"- **Shared by:** {cfg.shared_by}")
        lines.append("")

    if collection:
        lines.append(f"- **Collection method:** {collection}")
        lines.append("")

    lines.append("### Dataset Sources")
    lines.append("")
    # Issue #291: the card knows the repository/source split, and `source` is
    # conventionally an institution name, so a declared `repository` wins and an
    # undeclared one falls back to the source rather than to a bare sentinel.
    repository = cfg.repository.strip() or cfg.source.strip() or _ns
    lines.append("- **Repository:** " + repository)
    lines.append("")

    # ── Uses ───────────────────────────────────────────────────────────────
    lines.append("## Uses")
    lines.append("")
    lines.append("### Direct Use")
    lines.append("")
    lines.append(cfg.direct_use.strip() or _MORE_INFO)
    lines.append("")
    lines.append("### Out-of-Scope Use")
    lines.append("")
    lines.append(cfg.out_of_scope_use.strip() or _MORE_INFO)
    lines.append("")

    # ── Dataset Structure ──────────────────────────────────────────────────
    lines.append("## Dataset Structure")
    lines.append("")

    if cfg.files:
        # Delivered repo-relative paths — same mapping the upload pipeline
        # uses (conversion, upload_as_csv, recursive, keep_csv), RC-R08.
        # Expanded when the mirror exists (RC-Universal-Card).
        if staging_dir is not None and staging_dir.is_dir():
            delivered = expanded_planned_remotes(cfg, keep_csv, staging_dir)
        else:
            delivered = planned_remotes(cfg, keep_csv)
        file_list = "\n".join(f"  - `{remote}`" for remote in delivered)
        lines.append(f"This dataset contains **{len(delivered)} file(s)**:")
        lines.append("")
        lines.append(file_list)
        lines.append("")
    else:
        lines.append("No data files declared.")
        lines.append("")

    # Codebook table — per-sheet collapsible (RC-R21: cada tabla por separado)
    if schema:
        groups = _group_by_origin(schema)
        thr = config.CARD_COLLAPSE_THRESHOLD
        # Collapse when per-table exceeds threshold OR when there are multiple tables
        should_wrap: bool
        if len(groups) > 1:
            should_wrap = True
        elif len(groups) == 1:
            cols_single = next(iter(groups.values()))
            should_wrap = len(cols_single) > thr
        else:
            should_wrap = False

        if not should_wrap:
            lines.append("### Data Fields")
            lines.append("")
            lines.append(
                "| Column | Type | File | Nullable | Example | Unique (sample) | Missing (%) |"
            )
            lines.append(
                "|--------|------|------|----------|---------|-----------------|-------------|"
            )
            for s in schema:
                lines.append(_data_fields_row(s))
            lines.append("")
            lines.append(
                f"*Statistics (unique, missing%) based on a {config.SCHEMA_SAMPLE_SIZE:,}-row sample."  # noqa: E501
                " Exact counts may differ in the full dataset.*"
            )
            lines.append("")
        else:
            lines.append("### Data Fields")
            lines.append("")
            for label, cols in groups.items():
                table_lines = [
                    "| Column | Type | File | Nullable | Example | Unique (sample) | Missing (%) |",
                    "|--------|------|------|----------|---------|-----------------|-------------|",
                ]
                for s in cols:
                    table_lines.append(_data_fields_row(s))
                table_str = "\n".join(table_lines)
                lines.append(
                    f"<details><summary>Data Fields -- {label} ({len(cols)} columns)</summary>"
                )
                lines.append("")
                lines.append(table_str)
                lines.append("")
                lines.append("</details>")
                lines.append("")
            lines.append(
                f"*Statistics (unique, missing%) based on a {config.SCHEMA_SAMPLE_SIZE:,}-row sample."  # noqa: E501
                " Exact counts may differ in the full dataset.*"
            )
            lines.append("")

    # ── Data Quality Notes (empty columns, duplicate rows) ──────────────────
    # One entry per (origin, name) means a repeated empty name would otherwise
    # be listed once per file that declares it (#304).
    all_empty: list[str] = []
    for s in schema:
        if s.missing == 100.0 and s.name not in all_empty:
            all_empty.append(s.name)
    if empty_columns:
        for col in empty_columns:
            if col not in all_empty:
                all_empty.append(col)

    has_quality_notes = bool(all_empty) or (duplicate_rows is not None and bool(duplicate_rows))
    if has_quality_notes:
        lines.append("### Data Quality Notes")
        lines.append("")
        if all_empty:
            lines.append(f"- **Empty columns:** {', '.join(f'`{c}`' for c in all_empty)}")
            lines.append("")
        if duplicate_rows:
            for filename, count in duplicate_rows.items():
                if count > 0:
                    lines.append(f"- **Duplicate rows in `{filename}`:** {count}")
            lines.append("")

    # ── Dataset Creation ───────────────────────────────────────────────────
    lines.append("## Dataset Creation")
    lines.append("")
    lines.append("### Curation Rationale")
    lines.append("")

    # Issue #324: this section's only fill path was `[meta] study_design`, a
    # *path* to a markdown file, while every neighbouring section takes a plain
    # multi-line string. A declared `curation_rationale` wins, the resolved
    # file's content is the fallback, and the sentinel is last. When the key is
    # absent the branch taken is the pre-#324 one, byte for byte.
    if cfg.curation_rationale.strip():
        rationale = cfg.curation_rationale.strip()
    elif study_design_content is not None:
        rationale = study_design_content.strip()
    else:
        rationale = _MORE_INFO
    lines.append(rationale)
    lines.append("")

    if collection:
        lines.append("### Source Data")
        lines.append("")
        lines.append("#### Data Collection and Processing")
        lines.append("")
        lines.append(collection)
        lines.append("")

    # Processing recipe
    if recipe_content is not None:
        recipe_lang = _infer_language(cfg.recipe) if cfg.recipe else ""
        lines.append("#### Processing Recipe")
        lines.append("")
        lines.append(f"```{recipe_lang}")
        lines.append(recipe_content)
        lines.append("```")
        lines.append("")
    elif cfg.recipe:
        lines.append(f"Recipe file declared but not found: {cfg.recipe}")
        lines.append("")

    # ── Bias, Risks, and Limitations ───────────────────────────────────────
    lines.append("## Bias, Risks, and Limitations")
    lines.append("")
    lines.append(cfg.bias_risks_limitations.strip() or _MORE_INFO)
    lines.append("")

    # ── Citation ───────────────────────────────────────────────────────────
    lines.append("## Citation")
    lines.append("")
    lines.append("**BibTeX:**")
    lines.append("")
    lines.append(f"{citation}")
    lines.append("")

    # ── License ────────────────────────────────────────────────────────────
    lines.append("## License")
    lines.append("")
    lines.append(lic_display)
    lines.append("")

    # ── Optional sections ──────────────────────────────────────────────────
    if cfg.dataset_card_authors:
        lines.append("## Dataset Card Authors")
        lines.append("")
        lines.append(cfg.dataset_card_authors)
        lines.append("")

    if cfg.paper_url:
        lines.append("## Paper")
        lines.append("")
        lines.append(f"- [{cfg.paper_url}]({cfg.paper_url})")
        lines.append("")

    if cfg.demo_url:
        lines.append("## Demo")
        lines.append("")
        lines.append(f"- [{cfg.demo_url}]({cfg.demo_url})")
        lines.append("")

    # ── Contact ────────────────────────────────────────────────────────────
    lines.append("## Dataset Card Contact")
    lines.append("")
    lines.append(cfg.contact.strip() or _ns)
    lines.append("")

    return header + "\n".join(lines)


_CARD_FRONTMATTER_FENCE: str = "---"
"""Delimiter framing a Dataset Card's YAML frontmatter (see the ``header``
:func:`build_dataset_card` renders, and :func:`card_config_names`). A module
constant so the reader and the writer cannot drift.
"""


def card_config_names(build_dir: Path) -> list[str]:
    """Return the ``configs[].config_name`` values a built Dataset Card emitted.

    The dry-run warning tells the user to load a multi-table corpus one table at
    a time with ``load_dataset(repo, name='<config>')``, but could not name the
    configs (issue #303): they are computed inside :func:`build_dataset_card`,
    which returns only the card text, so the caller that prints the warning never
    sees them. They are known exactly once the card exists, so this reads them
    back from the artifact — the names that shipped, not a second derivation that
    could disagree with it. Required by ``repo-compliance`` RC-Universal-Card,
    "Actionable warning" (S4).

    Args:
        build_dir: Package directory holding the generated ``README.md``.

    Returns:
        The emitted config names, in card order. ``[]`` when the card is absent,
        unreadable, unfenced, has no ``configs`` block (an ungroupable corpus
        emits none — RC-Universal-Card S2/D1), or does not name every entry with
        a non-empty string. Each of those falls back to the placeholder form of
        the warning rather than naming a guess.
    """
    try:
        text = (Path(build_dir) / "README.md").read_text(encoding=config.OUTPUT_ENCODING)
    except OSError:
        return []
    # maxsplit=2 keeps a fenced block inside the YAML (a multi-line citation,
    # say) from being read as the closing fence.
    parts = text.split(_CARD_FRONTMATTER_FENCE, 2)
    if len(parts) < 3 or parts[0].strip():
        return []
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return []
    if not isinstance(frontmatter, dict):
        return []
    configs = frontmatter.get("configs")
    if not isinstance(configs, list):
        return []
    names: list[str] = []
    for entry in configs:
        if not isinstance(entry, dict):
            return []
        name = entry.get("config_name")
        if not isinstance(name, str) or not name:
            return []
        names.append(name)
    return names
