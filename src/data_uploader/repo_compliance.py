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

import yaml

from .codebook import infer_column_type
from .model import DatasetConfig

_SCHEMA_SAMPLE_SIZE = 10_000


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


def build_schema_report(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str = "utf-8-sig",
) -> list[ColumnSchema]:
    """Analyse CSV files declared in *cfg* and produce a typed schema report.

    Args:
        cfg:          Dataset configuration.
        csv_delimiter: Delimiter override (``None`` = use ``cfg.csv_delimiter``,
                       with Sniffer fallback).
        csv_encoding:  File encoding (default ``"utf-8-sig"``).

    Returns:
        A list of :class:`ColumnSchema` entries — one per column across all
        CSV files.  Columns with the same name in different files are
        disambiguated via a ``filename::`` prefix.
    """
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    delimiter = csv_delimiter or cfg.csv_delimiter
    columns: list[ColumnSchema] = []
    seen_names: dict[str, tuple[str, int]] = {}  # col_name → (filename, original_index_in_list)

    for entry in cfg.files:
        remote = entry.remote.lower()
        if entry.recursive or not remote.endswith(".csv"):
            continue

        local = entry.resolve(base)
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
                    # First occurrence needs renaming too
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

            dtype = infer_column_type(col_values)

            non_missing = [
                v
                for v in col_values
                if v.strip()
                and v.strip().upper() not in ("NA", "N/A", "NOTAPPLICABLE", "MISSING", "NULL", "")
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

    Args:
        cfg:            Dataset configuration.
        schema:         Column schema list from :func:`build_schema_report`.
        recipe_content: Pre-loaded recipe content, or ``None``.

    Returns:
        Complete ``README.md`` content as a single string.
    """
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

    yaml_block = yaml.safe_dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    header = f"---\n{yaml_block}\n---\n"

    # ── Helper ─────────────────────────────────────────────────────────────
    _ns = "[Not specified]"

    # ── Section: Dataset Description ────────────────────────────────────────
    desc = cfg.description.strip() if cfg.description else _ns
    source = cfg.source.strip() if cfg.source else _ns
    dataset_description = f"""## Dataset Description

- **Description:** {desc}
- **Source:** {source}
"""

    # ── Section: Raw Data Provenance ────────────────────────────────────────
    collection = cfg.collection_method.strip() if cfg.collection_method else _ns
    raw_provenance = f"""## Raw Data Provenance

- **Collection method:** {collection}
- **Source organisation:** {source}
"""

    # ── Section: Tidy Data Description ──────────────────────────────────────
    if cfg.files:
        file_list = "\n".join(f"  - `{e.local}` → `{e.remote}`" for e in cfg.files)
        tidy_desc = f"""## Tidy Data Description

This dataset contains **{len(cfg.files)} file(s)**:

{file_list}
"""
    else:
        tidy_desc = """## Tidy Data Description

No data files declared.
"""

    # ── Section: Codebook ──────────────────────────────────────────────────
    if schema:
        rows = "\n".join(
            f"| `{s.name}` | {s.dtype} | {'Yes' if s.nullable else 'No'} | "
            f"`{s.example}` | {s.unique} | {s.missing}% |"
            for s in schema
        )
        codebook = f"""## Codebook / Variable Reference

| Column | Type | Nullable | Example | Unique (sample) | Missing (%) |
|--------|------|----------|---------|-----------------|-------------|
{rows}
"""
    else:
        codebook = """## Codebook / Variable Reference

No schema information available.
"""

    # ── Section: Processing Recipe ─────────────────────────────────────────
    if recipe_content is not None:
        recipe_lang = _infer_language(cfg.recipe) if cfg.recipe else ""
        recipe = f"""## Processing Recipe

```{recipe_lang}
{recipe_content}
```
"""
    elif cfg.recipe:
        recipe = f"""## Processing Recipe

Recipe file declared but not found: {cfg.recipe}
"""
    else:
        recipe = ""

    # ── Section: Citation ──────────────────────────────────────────────────
    citation = cfg.citation.strip() if cfg.citation else _ns
    citation_section = f"""## Citation

{citation}
"""

    # ── Section: License ───────────────────────────────────────────────────
    lic = cfg.license.strip() if cfg.license else _ns
    license_section = f"""## License

{lic}
"""

    # ── Assemble ───────────────────────────────────────────────────────────
    body_paragraphs = [
        dataset_description,
        raw_provenance,
        tidy_desc,
        codebook,
        recipe,
        citation_section,
        license_section,
    ]

    body = "\n".join(p for p in body_paragraphs if p)
    return header + body
