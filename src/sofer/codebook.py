"""
Automatic codebook generation from tabular data files.

A *codebook* documents every column in a dataset: name, inferred type,
unique values, missing percentage, and a sample value.  This follows the
data-sharing standard recommended by the `Leek group guide`_.

.. _Leek group guide: https://github.com/jtleek/datasharing

Supports CSV, TSV, Parquet, Excel (.xlsx), and JSON Lines (.jsonl).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ._formats import SUPPORTED_FORMATS
from ._sentinels import MISSING_VALUE_SENTINELS
from .config import (
    CODEBOOK_MAX_SAMPLE,
    CODEBOOK_MIXED_THRESHOLD,
    CODEBOOK_NUMERIC_THRESHOLD,
    CODEBOOKS_DIR,
    OUTPUT_DIR,
    OUTPUT_ENCODING,
)

if TYPE_CHECKING:
    from .model import DatasetConfig


def infer_column_type(values: list[str]) -> str:
    """Guess the semantic type of a column from a sample of its values.

    Returns one of ``"numeric"``, ``"categorical/text"``,
    ``"mixed (mostly numeric)"``, or ``"unknown"``.
    """
    numeric_count = 0
    total = len(values)
    for v in values:
        cleaned = v.strip()
        if not cleaned or cleaned.upper() in MISSING_VALUE_SENTINELS:
            continue
        try:
            float(cleaned.replace(",", "."))
            numeric_count += 1
        except ValueError:
            pass
    if total == 0:
        return "unknown"
    if numeric_count == 0:
        return "categorical/text"
    ratio = numeric_count / total
    if ratio > CODEBOOK_NUMERIC_THRESHOLD:
        return "numeric"
    if ratio > CODEBOOK_MIXED_THRESHOLD:
        return "mixed (mostly numeric)"
    return "categorical/text"


def _infer_type(values: list[str]) -> str:
    """Deprecated alias for :func:`infer_column_type`.

    Use :func:`infer_column_type` directly instead.
    """
    import warnings

    warnings.warn(
        "_infer_type is deprecated, use infer_column_type",
        DeprecationWarning,
        stacklevel=2,
    )
    return infer_column_type(values)


# ══════════════════════════════════════════════════════════════════════════
#  Format-specific readers
# ══════════════════════════════════════════════════════════════════════════


def _read_csv(
    path: str,
    encoding: str = "utf-8-sig",
    delimiter: str = ";",
) -> tuple[list[str], list[list[str]], None]:
    """Read a CSV file and return ``(headers, columns, None)``.

    Columns are returned column-by-column (not row-by-row) so that
    :func:`infer_column_type` can consume them directly.
    """
    with open(path, newline="", encoding=encoding) as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        headers = next(reader)
        rows = list(reader)

    n_cols = len(headers)
    columns: list[list[str]] = [[] for _ in range(n_cols)]
    for row in rows:
        for i in range(n_cols):
            columns[i].append(row[i] if i < len(row) else "")

    return headers, columns, None


def _read_tsv(
    path: str,
    encoding: str = "utf-8-sig",
) -> tuple[list[str], list[list[str]], None]:
    """Read a TSV file using ``csv.reader(delimiter='\\\\t')``."""
    return _read_csv(path, encoding=encoding, delimiter="\t")


def _read_parquet(path: str) -> tuple[list[str], list[list[str]], dict[str, str]]:
    """Read a Parquet file via ``pyarrow``.

    Returns ``(headers, columns, dtypes)`` where *dtypes* maps each
    column name to its Parquet storage type (e.g. ``"int64"``).
    """
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    headers = table.column_names
    n_cols = len(headers)
    columns: list[list[str]] = [[] for _ in range(n_cols)]
    dtypes: dict[str, str] = {}

    for i, name in enumerate(headers):
        col = table.column(i).to_pylist()
        dtypes[name] = str(table.column(i).type)
        for v in col:
            columns[i].append("" if v is None else str(v))

    return headers, columns, dtypes


def _read_xlsx(path: str) -> tuple[list[str], list[list[str]], dict[str, str] | None]:
    """Read the first sheet of an Excel file via ``openpyxl``.

    Returns ``(headers, columns, dtypes)``.  *dtypes* reflects the
    Python type of the first non-empty value in each column.
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    headers = [str(v) if v is not None else f"col_{i}" for i, v in enumerate(header_row)]
    n_cols = len(headers)

    columns: list[list[str]] = [[] for _ in range(n_cols)]
    dtypes: dict[str, str] = {}
    dtype_determined = [False] * n_cols

    for row in ws.iter_rows(min_row=2, values_only=True):
        for i in range(n_cols):
            val = row[i] if i < len(row) else None
            if val is None:
                columns[i].append("")
            else:
                columns[i].append(str(val))
                if not dtype_determined[i]:
                    if isinstance(val, bool):
                        dtypes[headers[i]] = "bool"
                    elif isinstance(val, int):
                        dtypes[headers[i]] = "int"
                    elif isinstance(val, float):
                        dtypes[headers[i]] = "float"
                    elif isinstance(val, str):
                        dtypes[headers[i]] = "string"
                    else:
                        dtypes[headers[i]] = "object"
                    dtype_determined[i] = True

    wb.close()

    for i, name in enumerate(headers):
        if name not in dtypes:
            dtypes[name] = "unknown"

    return headers, columns, dtypes


def _read_jsonl(path: str) -> tuple[list[str], list[list[str]], None]:
    """Read a JSON Lines file, unifying keys across all objects.

    Keys are collected in discovery order so that the column order is
    stable within a file.
    """
    all_keys: list[str] = []
    rows: list[dict[str, object]] = []

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            for k in obj:
                if k not in all_keys:
                    all_keys.append(k)
            rows.append(obj)

    n_cols = len(all_keys)
    columns: list[list[str]] = [[] for _ in range(n_cols)]

    for row in rows:
        for i, key in enumerate(all_keys):
            val = row.get(key)
            columns[i].append("" if val is None else str(val))

    return all_keys, columns, None


# ══════════════════════════════════════════════════════════════════════════
#  Dispatcher
# ══════════════════════════════════════════════════════════════════════════


def _read_file(
    path: str,
    delimiter: str = ";",
    encoding: str = "utf-8-sig",
) -> tuple[list[str], list[list[str]], dict[str, str] | None]:
    """Route to the correct format-specific reader based on file suffix.

    Raises ``ValueError`` for unsupported formats.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return _read_csv(path, encoding=encoding, delimiter=delimiter)
    elif suffix == ".tsv":
        return _read_tsv(path, encoding=encoding)
    elif suffix == ".parquet":
        return _read_parquet(path)
    elif suffix == ".xlsx":
        return _read_xlsx(path)
    elif suffix == ".jsonl":
        return _read_jsonl(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


# ══════════════════════════════════════════════════════════════════════════
#  Markdown builder
# ══════════════════════════════════════════════════════════════════════════


def _build_markdown(
    headers: list[str],
    columns: list[list[str]],
    dtypes: dict[str, str] | None,
    file_path: str,
    max_sample: int = CODEBOOK_MAX_SAMPLE,
) -> str:
    """Build a markdown codebook from columnar data.

    This function is format-agnostic — it receives already-parsed
    ``(headers, columns, dtypes?)`` and renders the markdown table.
    When *dtypes* is not ``None``, an extra ``| Actual Type |``
    column is added.
    """
    path = Path(file_path)
    total_rows = len(columns[0]) if columns else 0
    n_analysed = min(total_rows, max_sample)

    lines = [
        f"# Codebook: {path.name}",
        "",
        f"**File:** `{path.name}`",
        f"**Rows:** {total_rows:,}",
        f"**Columns:** {len(headers)}",
        f"**Analysed rows:** {n_analysed:,} "
        f"({'full scan' if total_rows <= max_sample else 'sample'})",
        "",
    ]

    if dtypes is not None:
        lines.append("| # | Column | Type | Actual Type | Unique | Missing (%) | Example |")
        lines.append("|---|--------|------|-------------|--------|-------------|---------|")
    else:
        lines.append("| # | Column | Type | Unique | Missing (%) | Example |")
        lines.append("|---|--------|------|--------|-------------|---------|")

    for idx, col_name in enumerate(headers, 1):
        col_values = columns[idx - 1][:n_analysed]
        n_unique = len(set(col_values))
        n_missing = sum(
            1 for v in col_values if not v.strip() or v.strip().upper() in MISSING_VALUE_SENTINELS
        )
        pct_missing = round(n_missing / len(col_values) * 100, 1) if col_values else 0.0
        col_type = infer_column_type(col_values)
        example = next(
            (
                v
                for v in col_values
                if v.strip() and v.strip().upper() not in MISSING_VALUE_SENTINELS
            ),
            "",
        )

        if dtypes is not None:
            actual_type = dtypes.get(col_name, "")
            lines.append(
                f"| {idx} | `{col_name}` | {col_type} | {actual_type} | "
                f"{n_unique} | {pct_missing}% | `{example}` |"
            )
        else:
            lines.append(
                f"| {idx} | `{col_name}` | {col_type} | {n_unique} | {pct_missing}% | `{example}` |"
            )

    lines.extend(["", "", "_Generated by sofer_"])
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════


def generate(
    csv_path: str,
    output_path: str | None = None,
    delimiter: str = ";",
    encoding: str = "utf-8-sig",
    max_sample: int = CODEBOOK_MAX_SAMPLE,
) -> str:
    """Generate a markdown codebook from a data file.

    Supports CSV, TSV, Parquet, Excel (.xlsx), and JSON Lines (.jsonl).

    The codebook analyses up to *max_sample* rows to infer column types,
    unique value counts, and missing-data proportions.

    Args:
        csv_path:   Path to the input data file.
        output_path: If given, write the codebook to this file.
        delimiter:  CSV delimiter character (default ``;``).  Only used
                    for CSV/TSV files; ignored for other formats.
        encoding:   File encoding (default ``utf-8-sig``).  Only used
                    for CSV/TSV files; ignored for other formats.
        max_sample: Maximum rows to read for analysis.

    Returns:
        The codebook as a markdown string.
    """
    headers, columns, dtypes = _read_file(csv_path, delimiter=delimiter, encoding=encoding)
    codebook = _build_markdown(headers, columns, dtypes, csv_path, max_sample)

    if output_path:
        Path(output_path).write_text(codebook, encoding=OUTPUT_ENCODING)

    return codebook


def generate_all(cfg: DatasetConfig) -> list[str]:
    """Generate one codebook per ``[[file]]`` entry under ``data/codebooks/``.

    Each codebook is written to ``{CODEBOOKS_DIR}/<rel-stem>.md``, where
    ``<rel-stem>`` is the file's path relative to the ``data/`` directory
    (falling back to the TOML config directory for files outside ``data/``).
    When two or more entries resolve to the same output path the system
    writes codebooks for all non-colliding files first, then raises
    ``ValueError`` naming every colliding source on stderr — no codebook
    is written for any colliding file and the root index is not generated.

    Args:
        cfg: A ``DatasetConfig`` loaded from a TOML file.

    Returns:
        List of generated codebook file paths (including the root index
        when there are no collisions).

    Raises:
        ValueError: When two or more files resolve to the same output path
            (after non-colliding codebooks have already been written).
    """

    from pathlib import PurePath

    base_dir = cfg._base_dir.resolve()
    data_dir = base_dir / OUTPUT_DIR
    codebooks_dir = data_dir / CODEBOOKS_DIR

    # ── First pass: collect valid, readable file entries ─────────────
    entries: list[tuple[Path, str]] = []
    for file_entry in cfg.files:
        local = file_entry.resolve(base_dir)

        if local.is_dir():
            print(f"  ⚠  Skipping directory: {local}", file=sys.stderr)
            continue

        if not local.exists():
            print(f"  ⚠  Skipping missing file: {local}", file=sys.stderr)
            continue

        suffix = local.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            print(f"  ⚠  Unsupported format, skipping: {local}", file=sys.stderr)
            continue

        entries.append((local, suffix))

    if not entries:
        return []

    # ── Pre-compute output paths and detect collisions ───────────────
    output_paths: dict[Path, Path] = {}  # local → output path
    collision_sources: dict[Path, list[Path]] = {}  # output → source files

    for local, _suffix in entries:
        # Derive rel-stem: under data/ → relative to data dir,
        # otherwise fall back to relative to base dir.
        if local.is_relative_to(data_dir):
            rel_stem = local.relative_to(data_dir)
        else:
            rel_stem = local.relative_to(base_dir)

        # Compute output path: only the last suffix is replaced.
        out = (codebooks_dir / rel_stem).with_suffix(
            "".join(PurePath(rel_stem.name).suffixes[:-1]) + ".md"
            if len(PurePath(rel_stem.name).suffixes) > 1
            else ".md"
        )

        output_paths[local] = out
        if out not in collision_sources:
            collision_sources[out] = []
        collision_sources[out].append(local)

    # ── Partition: non-colliding vs colliding ────────────────────────
    colliding_locals: set[Path] = set()
    for out, sources in collision_sources.items():
        if len(sources) > 1:
            colliding_locals.update(sources)

    # ── Generate per-file codebooks (non-colliding only) ─────────────
    generated: list[str] = []
    outputs: list[tuple[Path, int]] = []  # (output_path, n_cols)

    for local, suffix in entries:
        if local in colliding_locals:
            continue

        try:
            headers, columns, dtypes = _read_file(str(local))
        except Exception as exc:
            print(f"  ✗  Error reading {local}: {exc}", file=sys.stderr)
            continue

        output_path = output_paths[local]
        codebook = _build_markdown(headers, columns, dtypes, str(local))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(codebook, encoding=OUTPUT_ENCODING)
        generated.append(str(output_path))
        outputs.append((output_path, len(headers)))
        print(f"  OK  {output_path}")

    # ── If collisions exist: raise ValueError after partial write ────
    if colliding_locals:
        for out, sources in collision_sources.items():
            if len(sources) > 1:
                rel_out = out.relative_to(base_dir).as_posix()
                source_list = ", ".join(
                    s.relative_to(base_dir).as_posix() for s in sources
                )
                print(
                    f"  X  Collision: {rel_out} is target for: {source_list}",
                    file=sys.stderr,
                )
        raise ValueError(
            f"Collision detected: {len(colliding_locals)} file(s) "
            f"share the same output path(s). No codebook written "
            f"for colliding files."
        )

    # ── Root index (only when no collisions) ─────────────────────────
    root_path = base_dir / "codebook.md"
    total_cols = sum(n for _, n in outputs)
    total_tables = len(outputs)

    index_lines = [
        f"# Codebook Index: {cfg.name}",
        "",
        f"**Repository:** `{cfg.repo_id}`",
        f"**Tables:** {total_tables} | **Total columns:** {total_cols}",
        "",
        "## Contents",
    ]

    for out_path, n_cols in outputs:
        rel = out_path.relative_to(base_dir).as_posix()
        index_lines.append(f"- [`{rel}`]({rel}) — {n_cols} columns")

    index_lines.extend(["", "", "_Generated by sofer_"])
    root_path.write_text("\n".join(index_lines), encoding=OUTPUT_ENCODING)
    generated.append(str(root_path))

    return generated
