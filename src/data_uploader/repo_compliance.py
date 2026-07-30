"""
HF Dataset Compliance — Dataset Card, LICENSE, and schema report generation.

All public functions are *pure*: they take config/schema data and return strings
or structured data.  No file I/O, no network calls — the orchestrator (``upload``)
handles reading and writing.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from .codebook import infer_column_type
from .model import DatasetConfig

_SCHEMA_SAMPLE_SIZE = 10_000

# Sentinel values treated as missing (same across CSV and Parquet paths).
_NULL_SENTINELS = frozenset({"NA", "N/A", "NOTAPPLICABLE", "MISSING", "NULL", ""})

# Map our internal dtype strings to HF Dataset Feature types
_HF_FEATURE_MAP: dict[str, str] = {
    "numeric": "float64",
    "categorical/text": "string",
    "mixed (mostly numeric)": "string",
    "unknown": "string",
}


def _hf_feature_type(dtype: str) -> str:
    """Map internal dtype to HF Dataset Feature type string."""
    return _HF_FEATURE_MAP.get(dtype, "string")


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
    """

    name: str
    dtype: str
    nullable: bool
    example: str
    unique: int
    missing: float


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
                    sample = fh.read(8192)
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
        limit = min(num_rows, _SCHEMA_SAMPLE_SIZE)

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


def build_schema_report(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str = "utf-8-sig",
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
        files.  Columns with the same name in different files are disambiguated
        via a ``filename::`` prefix (``.parquet`` extension when read from
        Parquet).
    """
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    delimiter = csv_delimiter or cfg.csv_delimiter
    columns: list[ColumnSchema] = []
    seen_names: dict[str, tuple[str, int]] = {}

    for entry in cfg.files:
        remote = entry.remote.lower()
        if entry.recursive or not remote.endswith(".csv"):
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
            sample = rows[: min(len(rows), _SCHEMA_SAMPLE_SIZE)]

            for idx, col in enumerate(headers):
                col_name = col

                # disambiguate duplicate column names across files
                if col_name in seen_names:
                    prev_origin, prev_idx = seen_names[col_name]
                    if prev_origin != origin_name:
                        prev_col = columns[prev_idx]
                        columns[prev_idx] = ColumnSchema(
                            name=f"{prev_origin}::{col}",
                            dtype=prev_col.dtype,
                            nullable=prev_col.nullable,
                            example=prev_col.example,
                            unique=prev_col.unique,
                            missing=prev_col.missing,
                        )
                        col_name = f"{origin_name}::{col}"
                        seen_names[col_name] = (origin_name, len(columns))
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
                    if not v.strip()
                    or v.strip().upper() in ("NA", "N/A", "NOTAPPLICABLE", "MISSING", "NULL")
                )
                pct_missing = round(n_missing / n_total * 100, 1) if n_total else 0.0

                non_missing = [
                    v for v in col_values if v.strip() and v.strip().upper() not in _NULL_SENTINELS
                ]
                example = non_missing[0] if non_missing else ""
                n_unique = len(set(col_values))

                columns.append(
                    ColumnSchema(
                        name=col_name,
                        dtype=dtype,
                        nullable=nullable,
                        example=example,
                        unique=n_unique,
                        missing=pct_missing,
                    )
                )
        else:
            # ── Read from CSV (original behaviour) ───────────────────────
            result = _read_csv_sample(local, delimiter=delimiter, encoding=csv_encoding)
            if result is None:
                continue  # skip missing / unreadable files gracefully

            headers, rows = result
            sample = rows[: min(len(rows), _SCHEMA_SAMPLE_SIZE)]

            for idx, col in enumerate(headers):
                col_name = col

                # disambiguate duplicate column names across files
                if col_name in seen_names:
                    prev_origin, prev_idx = seen_names[col_name]
                    if prev_origin != local.name:
                        prev_col = columns[prev_idx]
                        columns[prev_idx] = ColumnSchema(
                            name=f"{prev_origin}::{col}",
                            dtype=prev_col.dtype,
                            nullable=prev_col.nullable,
                            example=prev_col.example,
                            unique=prev_col.unique,
                            missing=prev_col.missing,
                        )
                        col_name = f"{local.name}::{col}"
                        seen_names[col_name] = (local.name, len(columns))
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
                    if not v.strip()
                    or v.strip().upper() in ("NA", "N/A", "NOTAPPLICABLE", "MISSING", "NULL")
                )
                pct_missing = round(n_missing / n_total * 100, 1) if n_total else 0.0

                dtype = infer_column_type(col_values)

                non_missing = [
                    v for v in col_values if v.strip() and v.strip().upper() not in _NULL_SENTINELS
                ]
                example = non_missing[0] if non_missing else ""
                n_unique = len(set(col_values))

                columns.append(
                    ColumnSchema(
                        name=col_name,
                        dtype=dtype,
                        nullable=n_missing > 0,
                        example=example,
                        unique=n_unique,
                        missing=pct_missing,
                    )
                )

    return columns


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
) -> str:
    """Generate a HF-standard Dataset Card (``README.md`` with YAML frontmatter).

    Follows the official Hugging Face Dataset Card template:
    https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/templates/datasetcard_template.md

    Args:
        cfg:            Dataset configuration.
        schema:         Column schema list from :func:`build_schema_report`.
        recipe_content: Pre-loaded recipe content, or ``None``.

    Returns:
        Complete ``README.md`` content as a single string.
    """
    _ns = "[Not specified]"

    # ── YAML frontmatter ───────────────────────────────────────────────────
    frontmatter: dict[str, object] = {}

    if cfg.language:
        frontmatter["language"] = cfg.language
    if cfg.license:
        frontmatter["license"] = cfg.license
    frontmatter["pretty_name"] = cfg.pretty_name or cfg.name
    if cfg.task_categories:
        frontmatter["task_categories"] = cfg.task_categories
    if cfg.size_categories:
        frontmatter["size_categories"] = cfg.size_categories
    if cfg.tags:
        frontmatter["tags"] = cfg.tags
    if cfg.source:
        frontmatter["source_datasets"] = [cfg.source]

    # dataset_info with features (for Dataset Viewer)
    if schema:
        features = {s.name: _hf_feature_type(s.dtype) for s in schema}
        frontmatter["dataset_info"] = {"features": features}

    yaml_block = yaml.safe_dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    header = f"---\n{yaml_block}\n---\n"

    desc = cfg.description.strip() if cfg.description else _ns
    source = cfg.source.strip() if cfg.source else _ns
    collection = cfg.collection_method.strip() if cfg.collection_method else _ns
    citation = cfg.citation.strip() if cfg.citation else _ns
    lic = cfg.license.strip() if cfg.license else _ns

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
    lines.append(f"- **License:** {lic}")
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
        file_list = "\n".join(f"  - `{e.local}` -> `{e.remote}`" for e in cfg.files)
        lines.append(f"This dataset contains **{len(cfg.files)} file(s)**:")
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
        lines.append("| Column | Type | Nullable | Example | Unique (sample) | Missing (%) |")
        lines.append("|--------|------|----------|---------|-----------------|-------------|")
        for s in schema:
            lines.append(
                f"| `{s.name}` | {s.dtype} | {'Yes' if s.nullable else 'No'} | "
                f"`{s.example}` | {s.unique} | {s.missing}% |"
            )
        lines.append("")

    # ── Dataset Creation ───────────────────────────────────────────────────
    lines.append("## Dataset Creation")
    lines.append("")
    lines.append("### Curation Rationale")
    lines.append("")
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
    lines.append(lic)
    lines.append("")

    # ── Contact ────────────────────────────────────────────────────────────
    lines.append("## Dataset Card Contact")
    lines.append("")
    lines.append(_ns)
    lines.append("")

    return header + "\n".join(lines)
