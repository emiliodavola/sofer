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
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import config
from ._converters import sanitize_sheet_name
from ._formats import SUPPORTED_FORMATS
from ._sentinels import MISSING_VALUE_SENTINELS, count_unique_non_missing

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
    if ratio > config.CODEBOOK_NUMERIC_THRESHOLD:
        return "numeric"
    if ratio > config.CODEBOOK_MIXED_THRESHOLD:
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
        try:
            headers = next(reader)
        except StopIteration:
            # Completely empty file — mirror the _csv_reader.py:112-116
            # precedent: yield no headers and no columns so callers render
            # the "no data rows" placeholder instead of crashing.
            return [], [], None
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


def _read_xlsx_sheets(
    path: str,
) -> dict[str, tuple[list[str], list[list[str]], dict[str, str] | None]]:
    """Read all sheets of an Excel file, reusing ``sanitize_sheet_name`` dedup.

    Iterates ``wb.sheetnames`` in order, sanitizes each name via
    :func:`sanitize_sheet_name` with ``seen`` dedup (``_{n}``) verbatim from
    ``_converters._convert_xlsx_to_parquet``.  Empty/header-only sheets yield
    ``([], [], None)`` as a placeholder so callers render the marker codebook
    instead of crashing.

    Returns:
        Mapping ``sanitized_sheet -> (headers, columns, dtypes)``.
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet_names: list[str] = list(wb.sheetnames)
        seen: dict[str, int] = {}
        result: dict[str, tuple[list[str], list[list[str]], dict[str, str] | None]] = {}
        for sheet_name in sheet_names:
            sanitized = sanitize_sheet_name(sheet_name)
            base = sanitized
            count = seen.get(base, 0)
            if count > 0:
                sanitized = f"{base}_{count + 1}"
            seen[base] = count + 1
            if sanitized != base:
                seen[sanitized] = seen.get(sanitized, 0) + 1

            ws = wb[sheet_name]
            try:
                header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
            except StopIteration:
                header_row = None

            if header_row is None or all(v is None for v in header_row):
                result[sanitized] = ([], [], None)
                continue

            headers = [str(v) if v is not None else f"col_{i}" for i, v in enumerate(header_row)]
            n_cols = len(headers)
            columns: list[list[str]] = [[] for _ in range(n_cols)]
            dtypes: dict[str, str] = {}
            dtype_determined = [False] * n_cols

            for row in ws.iter_rows(min_row=2, values_only=True):
                if row is None:
                    continue
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

            for i, name in enumerate(headers):
                if name not in dtypes:
                    dtypes[name] = "unknown"

            result[sanitized] = (headers, columns, dtypes)
        return result
    finally:
        try:
            wb.close()
        except Exception:
            pass


def _read_xlsx(path: str) -> tuple[list[str], list[list[str]], dict[str, str] | None]:
    """Read the first sheet of an Excel file via :func:`_read_xlsx_sheets`.

    Preserves backward compatibility for :func:`generate` (single-sheet path).
    """
    sheets = _read_xlsx_sheets(path)
    if not sheets:
        return [], [], None
    # First sheet in workbook order is the first inserted key.
    first_key = next(iter(sheets))
    return sheets[first_key]


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
    max_sample: int | None = None,
) -> str:
    """Build a markdown codebook from columnar data.

    This function is format-agnostic — it receives already-parsed
    ``(headers, columns, dtypes?)`` and renders the markdown table.
    When *dtypes* is not ``None``, an extra ``| Actual Type |``
    column is added.

    Args:
        headers: Column names.
        columns: Per-column value lists.
        dtypes: Optional declared dtype mapping; adds the Actual Type column.
        file_path: Source file path shown in the header.
        max_sample: Maximum rows to analyse; ``None`` resolves to the
            ``codebook_max_sample`` value from ``[tool.sofer]`` at call time.

    Returns:
        The rendered markdown document.
    """
    if max_sample is None:
        max_sample = config.CODEBOOK_MAX_SAMPLE
    path = Path(file_path)

    # Empty or headerless input (adv5): render an explicit placeholder so the
    # codebook is a marker, not a crash or a degenerate zero-column table.
    if not headers:
        return (
            f"# Codebook: {path.name}\n\n"
            "**No data rows found** — the file is empty or headerless.\n\n"
            "_Generated by sofer_"
        )

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
        n_unique = count_unique_non_missing(col_values)
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
    max_sample: int | None = None,
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
        max_sample: Maximum rows to read for analysis; ``None`` resolves to
                    the ``codebook_max_sample`` value from ``[tool.sofer]``
                    at call time (never frozen from the import-time default).

    Returns:
        The codebook as a markdown string.
    """
    if max_sample is None:
        max_sample = config.CODEBOOK_MAX_SAMPLE
    headers, columns, dtypes = _read_file(csv_path, delimiter=delimiter, encoding=encoding)
    codebook = _build_markdown(headers, columns, dtypes, csv_path, max_sample)

    if output_path:
        Path(output_path).write_text(codebook, encoding=config.OUTPUT_ENCODING)

    return codebook


def _codebook_output_for_rel(
    codebooks_dir: Path,
    rel_stem: Path,
    sheet_sanitized: str | None = None,
) -> Path:
    """Compute the codebook output path for a (rel_stem, sheet) pair."""
    from pathlib import PurePath

    # Single-table: rel_stem.md ; multisheet: stem__sheet.md
    if sheet_sanitized is None:
        base = (codebooks_dir / rel_stem).with_suffix(
            "".join(PurePath(rel_stem.name).suffixes[:-1]) + ".md"
            if len(PurePath(rel_stem.name).suffixes) > 1
            else ".md"
        )
        return base
    # Multi-sheet: insert __sanitized before .md, preserving prior suffixes handling
    # Use the single-table base stem then inject __sheet
    base_single = (codebooks_dir / rel_stem).with_suffix(
        "".join(PurePath(rel_stem.name).suffixes[:-1]) + ".md"
        if len(PurePath(rel_stem.name).suffixes) > 1
        else ".md"
    )
    # base_single is codebooks/<rel>/<stem>.md ; insert __sheet before .md
    stem_no_ext = base_single.with_suffix("")
    return Path(str(stem_no_ext) + f"__{sheet_sanitized}.md")


def _normalize_codebook_collision_key(path: Path) -> str:
    """Normalize a codebook path for collision detection (``__+`` → ``_``).

    Mirrors ``normalize_parquet_remote``'s ``__+`` collapse so ``a__ventas.md``
    and ``a_ventas.md`` are considered colliding.
    """
    return re.sub(r"__+", "_", path.as_posix())


def generate_all(
    cfg: DatasetConfig,
    output_dir: str | Path | None = None,
    delimiter: str | None = None,
    encoding: str | None = None,
) -> list[str]:
    """Generate one codebook per ``[[file]]`` entry under ``output_dir``.

    For ``.xlsx`` with N sheets, N codebooks are emitted as
    ``codebooks/<rel>/<stem>__<sanitized>.md`` (single sheet → ``stem.md``).
    Each sheet's sanitization reuses :func:`sanitize_sheet_name` with ``seen``
    dedup ``_{n}`` verbatim.  The collision map is built from sheet-expanded
    output paths with dual ``__``/``_`` collapse (``__+`` → ``_``) so
    ``a__ventas`` and ``a_ventas`` collide.  Non-colliding outputs are written
    before ``ValueError`` is raised.

    Args:
        cfg: A ``DatasetConfig`` loaded from a TOML file.
        output_dir: When given (the CLI/MCP adapters pass the package
            ``build_dir``; ``prepare`` passes its output directory), per-file
            codebooks are written under ``output_dir/codebooks/`` and the
            root index to ``output_dir/codebook.md``; the shared
            ``cache/codebooks/`` directory is never mutated.  When ``None``,
            codebooks fall back to ``cache/codebooks/`` with the root index
            next to them (``cache/codebook.md``).
        delimiter: CSV delimiter override. ``None`` resolves to
            ``cfg.csv_delimiter`` (the dataset's ``[meta] csv_delimiter`` —
            the authoritative source; rule-3 fix for the CLI's hardcoded
            ``";"``).  Only used for CSV/TSV files; ignored for other formats.
        encoding: CSV encoding override. ``None`` resolves to
            ``cfg.csv_encoding`` (``[meta] csv_encoding``).

    Returns:
        List of generated codebook file paths (including the root index
        when there are no collisions).

    Raises:
        ValueError: When two or more files resolve to the same output path
            (after non-colliding codebooks have already been written).
    """

    base_dir = cfg._base_dir.resolve()
    data_dir = base_dir / config.OUTPUT_DIR

    # Rule-3 fix (D2/MSP-R10): the dataset's own [meta] values are the
    # authoritative delimiter/encoding — never the hardcoded ";" default.
    delimiter = cfg.csv_delimiter if delimiter is None else delimiter
    encoding = cfg.csv_encoding if encoding is None else encoding

    # Option B: codebooks written directly into the caller's output dir.
    if output_dir is None:
        write_root = data_dir
        root_path = write_root / "codebook.md"
    else:
        # Anchor relative output dirs to the config dir (PRP-06), matching
        # how every other artifact path resolves — never the process CWD.
        out = Path(output_dir)
        if not out.is_absolute():
            out = base_dir / out
        write_root = out.resolve()
        root_path = write_root / "codebook.md"
    codebooks_dir = write_root / config.CODEBOOKS_DIR

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

    # ── Sheet-expanded output paths and normalized collision map ──────
    # expanded: list of (local, sheet_sanitized|None, output_path)
    expanded: list[tuple[Path, str | None, Path]] = []
    # For non-xlsx, single entry per local; for xlsx, expand via _read_xlsx_sheets
    # to reuse sanitization/dedup verbatim. Read once here for collision keys
    # and cache sheets data for later write to avoid double read.
    xlsx_cache: dict[Path, dict[str, tuple[list[str], list[list[str]], dict[str, str] | None]]] = {}

    for local, suffix in entries:
        if local.is_relative_to(data_dir):
            rel_stem = local.relative_to(data_dir)
        else:
            rel_stem = local.relative_to(base_dir)

        if suffix == ".xlsx":
            try:
                sheets = _read_xlsx_sheets(str(local))
            except Exception as exc:
                print(f"  ⚠  Error reading {local}: {exc}", file=sys.stderr)
                continue
            if not sheets:
                # No sheets (empty workbook) — treat as placeholder single
                out = _codebook_output_for_rel(codebooks_dir, rel_stem, None)
                expanded.append((local, None, out))
                xlsx_cache[local] = sheets
                continue
            if len(sheets) == 1:
                # Single sheet stays stem.md backward compat
                first_key = next(iter(sheets))
                # Keep the sanitized key but emit without suffix
                out = _codebook_output_for_rel(codebooks_dir, rel_stem, None)
                expanded.append((local, first_key, out))
                xlsx_cache[local] = sheets
            else:
                for sanitized in sheets:
                    out = _codebook_output_for_rel(codebooks_dir, rel_stem, sanitized)
                    expanded.append((local, sanitized, out))
                xlsx_cache[local] = sheets
        else:
            out = _codebook_output_for_rel(codebooks_dir, rel_stem, None)
            expanded.append((local, None, out))

    if not expanded:
        return []

    # Build normalized collision map: normalized_key -> list of (local, sheet, out)
    collision_map: dict[str, list[tuple[Path, str | None, Path]]] = {}
    for local, sheet, out in expanded:
        key = _normalize_codebook_collision_key(out)
        collision_map.setdefault(key, []).append((local, sheet, out))

    colliding_keys: set[str] = {k for k, v in collision_map.items() if len(v) > 1}
    # Per-expanded-entry colliding set for partial-write semantics
    colliding_expanded: set[tuple[Path, str | None]] = set()
    for key in colliding_keys:
        for local, sheet, _out in collision_map[key]:
            colliding_expanded.add((local, sheet))

    # ── Generate per-(file,sheet) codebooks (non-colliding only) ─────
    generated: list[str] = []
    outputs: list[tuple[Path, int]] = []  # (output_path, n_cols)

    for local, suffix in entries:
        # Non-xlsx single path
        if suffix != ".xlsx":
            # Check colliding
            if (local, None) in colliding_expanded:
                continue
            # Find its out
            out_path = next((o for lo, sh, o in expanded if lo == local and sh is None), None)
            if out_path is None:
                continue
            try:
                headers, columns, dtypes = _read_file(
                    str(local), delimiter=delimiter, encoding=encoding
                )
            except Exception as exc:
                print(f"  ⚠  Error reading {local}: {exc}", file=sys.stderr)
                continue
            codebook = _build_markdown(headers, columns, dtypes, str(local))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(codebook, encoding=config.OUTPUT_ENCODING)
            generated.append(str(out_path))
            outputs.append((out_path, len(headers)))
            print(f"  OK  {out_path}")
        else:
            sheets = xlsx_cache.get(local, {})
            if not sheets:
                # Empty workbook placeholder
                if (local, None) in colliding_expanded:
                    continue
                out_path2 = next((o for lo, sh, o in expanded if lo == local and sh is None), None)
                if out_path2 is None:
                    continue
                # No sheets: placeholder using local name
                codebook = _build_markdown([], [], None, str(local))
                out_path2.parent.mkdir(parents=True, exist_ok=True)
                out_path2.write_text(codebook, encoding=config.OUTPUT_ENCODING)
                generated.append(str(out_path2))
                outputs.append((out_path2, 0))
                print(f"  OK  {out_path2}")
                continue
            if len(sheets) == 1:
                # Single sheet -> stem.md using first sheet's data
                first_key = next(iter(sheets))
                if (local, first_key) in colliding_expanded:
                    continue
                out_path3 = next(
                    (o for lo, sh, o in expanded if lo == local and sh == first_key), None
                )
                if out_path3 is None:
                    continue
                headers, columns, dtypes = sheets[first_key]
                # File display name stays local.name (e.g., Report.xlsx) — _build_markdown
                # will title as local.name even for single-sheet.
                codebook = _build_markdown(headers, columns, dtypes, str(local))
                out_path3.parent.mkdir(parents=True, exist_ok=True)
                out_path3.write_text(codebook, encoding=config.OUTPUT_ENCODING)
                generated.append(str(out_path3))
                outputs.append((out_path3, len(headers)))
                print(f"  OK  {out_path3}")
            else:
                for sanitized, (headers, columns, dtypes) in sheets.items():
                    if (local, sanitized) in colliding_expanded:
                        continue
                    out_path4 = next(
                        (o for lo, sh, o in expanded if lo == local and sh == sanitized),
                        None,
                    )
                    if out_path4 is None:
                        continue
                    # For per-sheet codebook, show sheet-qualified filename in title?
                    # Keep original local path for _build_markdown but the output path
                    # carries __sheet for traceability.
                    try:
                        codebook = _build_markdown(
                            headers, columns, dtypes, str(local), max_sample=None
                        )
                    except Exception as exc:
                        print(
                            f"  ⚠  Error building {local} sheet {sanitized}: {exc}", file=sys.stderr
                        )
                        continue
                    out_path4.parent.mkdir(parents=True, exist_ok=True)
                    out_path4.write_text(codebook, encoding=config.OUTPUT_ENCODING)
                    generated.append(str(out_path4))
                    outputs.append((out_path4, len(headers)))
                    print(f"  OK  {out_path4}")

    # ── If collisions exist: raise ValueError after partial write ────
    if colliding_expanded:
        for key in sorted(colliding_keys):
            entries_for_key = collision_map[key]
            # Representative out for message — first exact out
            rep_out = entries_for_key[0][2]
            try:
                rel_out = rep_out.relative_to(base_dir).as_posix()
            except ValueError:
                rel_out = rep_out.as_posix()
            # List all colliding sources with sheet suffix when present
            parts: list[str] = []
            for lo, sh, _o in entries_for_key:
                try:
                    base_rel = lo.relative_to(base_dir).as_posix()
                except ValueError:
                    base_rel = lo.as_posix()
                if sh is not None:
                    # Show sheet suffix for clarity
                    parts.append(f"{base_rel}::{sh}")
                else:
                    parts.append(base_rel)
            source_list = ", ".join(parts)
            print(
                f"  X  Collision: {rel_out} is target for: {source_list}",
                file=sys.stderr,
            )
        raise ValueError(
            f"Collision detected: {len(colliding_expanded)} expanded output(s) "
            f"share the same path(s). No codebook written for colliding outputs."
        )

    # ── Root index (only when no collisions) ─────────────────────────
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
        rel = out_path.relative_to(write_root).as_posix()
        index_lines.append(f"- [`{rel}`]({rel}) — {n_cols} columns")

    index_lines.extend(["", "", "_Generated by sofer_"])
    root_path.write_text("\n".join(index_lines), encoding=config.OUTPUT_ENCODING)
    generated.append(str(root_path))

    return generated
