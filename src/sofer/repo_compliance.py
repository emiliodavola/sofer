"""
HF Dataset Compliance — Dataset Card, LICENSE, and schema report generation.

All public functions are *pure*: they take config/schema data and return strings
or structured data.  No file I/O, no network calls — the orchestrator (``prepare``)
handles reading and writing.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from . import config
from ._mirror import planned_remotes
from ._parquet_helpers import _parquet_to_hf_dtype
from ._sentinels import MISSING_VALUE_SENTINELS, count_unique_non_missing
from .codebook import infer_column_type
from .model import DatasetConfig


def normalize_header(col_name: str) -> str:
    """Normalize a column name by stripping leading/trailing whitespace.

    Column names are case-sensitive in HF datasets, so we preserve the
    original casing and only remove surrounding whitespace inserted by
    careless CSV exports.
    """
    return col_name.strip()


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
    encoding: str = "utf-8-sig",
) -> tuple[list[str], list[list[str]]] | None:
    """Read the header and a sample of rows from a CSV file.

    Returns ``(headers, rows)`` on success, or ``None`` if the file cannot
    be read.  When *delimiter* is ``None``, auto-detect with ``csv.Sniffer``
    as a fallback after trying the default ``";"``.
    """
    try:
        with open(path, newline="", encoding=encoding) as fh:
            if delimiter is None:
                # First try ";", Sniffer fallback
                try:
                    sample = fh.read(config.PROBE_CHUNK_BYTES)
                    fh.seek(0)
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ";"

            reader = csv.reader(fh, delimiter=delimiter)
            headers = next(reader)
            rows = list(reader)
    except Exception:
        return None

    return headers, rows


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


def _read_parquet_sample(
    parquet_path: Path,
) -> tuple[list[str], list[list[str]], pq.ParquetFile] | None:
    """Read header, sample rows, and the ParquetFile handle from a Parquet file.

    Returns ``(column_names, sample_rows, parquet_file)`` on success, or
    ``None`` if the file cannot be read.

    Iterates over pyarrow arrays directly — does not depend on pandas.
    """
    try:
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
    except Exception:
        return None


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
        csv_encoding:  File encoding (default ``"utf-8-sig"``).
        staging_dir:   Directory containing converted Parquet files.  When set,
                       the function checks for a ``.parquet`` file for each CSV
                       entry before falling back to CSV reading.

    Returns:
        ``(columns, row_counts)`` where *row_counts* maps each sampled file's
        origin basename (``"x.parquet"`` / ``"x.csv"``) to its EXACT row count
        (Parquet metadata vs. fully-read CSV rows).  Files that cannot be read
        contribute no entry.  Same-basename collisions overwrite each other —
        a documented MVP limitation.
    """
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    delimiter = csv_delimiter or cfg.csv_delimiter
    csv_encoding = csv_encoding or cfg.csv_encoding
    columns: list[ColumnSchema] = []
    row_counts: dict[str, int] = {}
    seen_names: dict[str, tuple[str, int]] = {}
    _dup_map: dict[str, list[str]] = {}
    _had_potential_csv_entries = False

    for entry in cfg.files:
        remote = entry.remote.lower()
        if entry.recursive or not remote.endswith(".csv"):
            continue

        _had_potential_csv_entries = True

        if not entry.include_in_schema:
            continue

        local = entry.resolve(base)
        entry_stem = Path(entry.remote).stem

        # Determine if we can read from Parquet instead of CSV
        use_parquet = False
        parquet_path = None
        origin_name = local.name  # used for disambiguation

        if staging_dir is not None and not entry.upload_as_csv:
            candidate = staging_dir / f"{entry_stem}.parquet"
            if candidate.exists():
                use_parquet = True
                parquet_path = candidate
                origin_name = f"{entry_stem}.parquet"

        parquet_result = None
        if use_parquet and parquet_path is not None:
            # ── Read from Parquet ────────────────────────────────────────
            parquet_result = _read_parquet_sample(parquet_path)
            if parquet_result is None:
                # Fall back to CSV if Parquet read fails
                use_parquet = False

        if use_parquet:
            assert parquet_result is not None
            headers, rows, pf = parquet_result
            sample = rows[: min(len(rows), config.SCHEMA_SAMPLE_SIZE)]
            row_counts[origin_name] = pf.metadata.num_rows

            for idx, col in enumerate(headers):
                col_name = col

                # disambiguate duplicate column names across files
                if col_name in seen_names:
                    prev_origin, _ = seen_names[col_name]
                    _dup_map.setdefault(col_name, [prev_origin]).append(origin_name)
                    continue
                else:
                    seen_names[col_name] = (origin_name, len(columns))

                # dtype from Parquet physical type
                pa_field = pf.schema_arrow.field(idx)
                dtype = _map_parquet_type(pa_field.type)
                nullable = pa_field.nullable

                col_values: list[str] = []
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
                        origin=origin_name,
                    )
                )
        else:
            # ── Read from CSV (original behaviour) ───────────────────────
            result = _read_csv_sample(local, delimiter=delimiter, encoding=csv_encoding)
            if result is None:
                continue  # skip missing / unreadable files gracefully

            headers, rows = result
            # Normalize headers: strip whitespace, preserve case
            headers = [normalize_header(h) for h in headers]
            sample = rows[: min(len(rows), config.SCHEMA_SAMPLE_SIZE)]
            row_counts[local.name] = len(rows)

            for idx, col in enumerate(headers):
                col_name = col

                # disambiguate duplicate column names across files
                if col_name in seen_names:
                    prev_origin, _ = seen_names[col_name]
                    _dup_map.setdefault(col_name, [prev_origin]).append(local.name)
                    continue
                else:
                    seen_names[col_name] = (local.name, len(columns))

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
                        origin=local.name,
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
                        f"using first occurrence."
                    )
        else:
            # Sort by frequency (most duplicated first), take top 5
            top5 = sorted(_dup_map, key=lambda k: len(_dup_map[k]), reverse=True)[:5]
            top5_str = ", ".join(top5)
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
        csv_encoding:  File encoding (default ``"utf-8-sig"``).
        staging_dir:   Directory containing converted Parquet files.  When set,
                       the function checks for a ``.parquet`` file for each CSV
                       entry before falling back to CSV reading.

    Returns:
        A list of :class:`ColumnSchema` entries — one per column across all
        files, each carrying its source file in :attr:`ColumnSchema.origin`.
        Duplicate names keep only their first occurrence (first-occurrence-wins;
        see the duplicate warnings emitted below).  Callers that also need exact
        per-file row counts should use :func:`build_schema_report_with_rows`.
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
        csv_encoding:  File encoding (default ``"utf-8-sig"``).
        staging_dir:   Directory containing converted Parquet files (see
                       :func:`build_schema_report`).

    Returns:
        ``(columns, row_counts)`` — the same schema report as
        :func:`build_schema_report`, plus a dict mapping each sampled file's
        origin basename to its EXACT row count (Parquet:
        ``pf.metadata.num_rows``; CSV: ``len(rows)`` on the fully read file).
        Row counts are never capped by the schema sample size.
    """
    return _build_schema_report_impl(cfg, csv_delimiter, csv_encoding, staging_dir)


# ═══════════════════════════════════════════════════════════════════════════════
#  Dataset Card (README.md)
# ═══════════════════════════════════════════════════════════════════════════════


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


def build_dataset_card(
    cfg: DatasetConfig,
    schema: list[ColumnSchema],
    recipe_content: str | None = None,
    study_design_content: str | None = None,
    empty_columns: list[str] | None = None,
    duplicate_rows: dict[str, int] | None = None,
    row_counts: dict[str, int] | None = None,
    keep_csv: bool = False,
) -> str:
    """Generate a HF-standard Dataset Card (``README.md`` with YAML frontmatter).

    Follows the official Hugging Face Dataset Card template:
    https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/templates/datasetcard_template.md

    Args:
        cfg:                   Dataset configuration.
        schema:                Column schema list from :func:`build_schema_report`.
        recipe_content:        Pre-loaded recipe content, or ``None``.
        study_design_content:  Pre-loaded study design content, or ``None``.
        empty_columns:         Optional list of column names that are entirely empty.
        duplicate_rows:        Optional dict mapping filenames to duplicate row counts.
        row_counts:            Optional dict mapping each file's origin basename to
                               its exact data-row count (from
                               :func:`build_schema_report_with_rows`).  When given,
                               the train split's ``num_examples`` is their sum;
                               otherwise it falls back to
                               ``CARD_FALLBACK_ROWS_PER_FILE`` per declared file.
        keep_csv:              Whether converted CSVs are also delivered at their
                               original remote (the publish ``--keep-csv`` flag).
                               Governs the Dataset Structure listing only.

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

    # -- configs (always emit when files declared) --------------------------
    if cfg.files:
        config_name = cfg.config_names[0] if cfg.config_names else (cfg.pretty_name or cfg.name)
        data_files: list[dict[str, object]] = []
        for e in cfg.files:
            data_files.append({"split": "train", "path": e.remote})
        if not data_files:
            data_files.append({"split": "train", "path": "data/*"})
        frontmatter["configs"] = [
            {
                "config_name": config_name,
                "data_files": data_files,
                "default": True,
            }
        ]

    # -- dataset_info -------------------------------------------------------
    if schema:
        # features — a LIST of {name, dtype}; every schema entry is included
        # (attribution is structural via ColumnSchema.origin, RC-R06).
        features_list: list[dict[str, str]] = []
        for s in schema:
            hf_dtype = s.hf_dtype if s.hf_dtype is not None else _hf_feature_type(s.dtype)
            features_list.append({"name": s.name, "dtype": hf_dtype})

        dataset_info: dict[str, object] = {"features": features_list}

        config_name = cfg.config_names[0] if cfg.config_names else (cfg.pretty_name or cfg.name)
        dataset_info["config_name"] = config_name

        # splits — single train split; num_examples from exact row counts
        # when available, else the conservative per-file fallback (D7).
        if cfg.files:
            if row_counts:
                approx_rows = sum(row_counts.values())
            else:
                approx_rows = len(cfg.files) * config.CARD_FALLBACK_ROWS_PER_FILE
            splits = [{"name": "train", "num_examples": approx_rows}]
            dataset_info["splits"] = splits

        frontmatter["dataset_info"] = dataset_info

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
    lines.append("- **Repository:** " + _ns)
    lines.append("")

    # ── Uses ───────────────────────────────────────────────────────────────
    lines.append("## Uses")
    lines.append("")
    lines.append("### Direct Use")
    lines.append("")
    lines.append("[More Information Needed]")
    lines.append("")
    lines.append("### Out-of-Scope Use")
    lines.append("")
    lines.append("[More Information Needed]")
    lines.append("")

    # ── Dataset Structure ──────────────────────────────────────────────────
    lines.append("## Dataset Structure")
    lines.append("")

    if cfg.files:
        # Delivered repo-relative paths — same mapping the upload pipeline
        # uses (conversion, upload_as_csv, recursive, keep_csv), RC-R08.
        delivered = planned_remotes(cfg, keep_csv)
        file_list = "\n".join(f"  - `{remote}`" for remote in delivered)
        lines.append(f"This dataset contains **{len(delivered)} file(s)**:")
        lines.append("")
        lines.append(file_list)
        lines.append("")
    else:
        lines.append("No data files declared.")
        lines.append("")

    # Codebook table
    if schema:
        lines.append("### Data Fields")
        lines.append("")
        lines.append(
            "| Column | Type | File | Nullable | Example | Unique (sample) | Missing (%) |"
        )
        lines.append(
            "|--------|------|------|----------|---------|-----------------|-------------|"
        )
        for s in schema:
            file_cell = s.origin if s.origin else "-"
            lines.append(
                f"| `{s.name}` | {s.dtype} | {file_cell} | {'Yes' if s.nullable else 'No'} | "
                f"`{s.example}` | {s.unique} | {s.missing}% |"
            )
        lines.append("")
        lines.append(
            f"*Statistics (unique, missing%) based on a {config.SCHEMA_SAMPLE_SIZE:,}-row sample."
            " Exact counts may differ in the full dataset.*"
        )
        lines.append("")

    # ── Data Quality Notes (empty columns, duplicate rows) ──────────────────
    schema_empty = [s.name for s in schema if s.missing == 100.0]
    all_empty = schema_empty
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

    if study_design_content is not None:
        lines.append(study_design_content.strip())
        lines.append("")
    else:
        lines.append("[More Information Needed]")
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
    lines.append("[More Information Needed]")
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
    lines.append(_ns)
    lines.append("")

    return header + "\n".join(lines)
