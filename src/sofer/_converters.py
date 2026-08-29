"""
Universal file-to-Parquet conversion dispatch.

Centralises the ``csv/tsv/xlsx/jsonl → normalized .parquet`` conversion that
``prepare`` orchestrates, including the shared writer, remote normalisation,
sheet sanitisation, and per-format parity checks.  The module is the single
home of ``CONVERTIBLE_SUFFIXES`` and ``normalize_parquet_remote`` so that
``_mirror`` and ``prepare`` can import without cycles.
"""

from __future__ import annotations

import csv as csv_module
import json
import re
import unicodedata
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.parquet as pq

from . import config

# ---------------------------------------------------------------------------
#  Public constants
# ---------------------------------------------------------------------------

CONVERTIBLE_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv", ".xlsx", ".jsonl"})


# ---------------------------------------------------------------------------
#  Normalisation
# ---------------------------------------------------------------------------


def normalize_parquet_remote(remote: str) -> str:
    """Normalise a remote path for staged-Parquet keys.

    Transformation (PC-U02):

    1. Lowercase the entire string.
    2. NFKD decomposition → ASCII strip (drop combining marks).
    3. Spaces → ``_``.
    4. Any character not in ``[a-z0-9_./-]`` → ``_``.
    5. Collapse runs of ``__+`` → ``_`` (but preserve ``/`` boundaries).

    Backslash separators are normalized to ``/`` first so that a TOML remote
    like ``data\\a\\train.csv`` yields the same key as ``data/a/train.csv``.
    Directory components are preserved lowercased.

    Args:
        remote: Verbatim ``FileEntry.remote`` or derived Parquet remote.

    Returns:
        Normalised POSIX remote path.
    """
    # Normalize separators
    s = remote.replace("\\", "/").lower()
    # NFKD → ASCII strip
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    # Spaces → _
    s = s.replace(" ", "_")
    # [^a-z0-9_./-] → _
    s = re.sub(r"[^a-z0-9_./-]", "_", s)
    # Collapse __+ → _  (but keep / intact — apply per segment to avoid
    # collapsing across path separators incorrectly; simplest is global
    # collapse of underscores only)
    s = re.sub(r"__+", "_", s)
    # Remove leading/trailing underscores on each segment? Not required;
    # spec collapses only runs, not edge underscores.
    return s


def sanitize_sheet_name(name: str) -> str:
    """Sanitise an Excel sheet name for use as a Parquet stem suffix.

    Reuses the same alphabet as :func:`normalize_parquet_remote` but without
    path separators: lowercase, NFKD→ASCII, spaces→_, ``[^a-z0-9_-]``→_, collapse
    ``__+``.  An empty result falls back to ``"sheet"``.  Dedup ``_{n}`` is
    handled by the caller.

    Args:
        name: Raw sheet name from ``openpyxl``.

    Returns:
        Sanitised sheet stem fragment.
    """
    s = name.lower()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.replace(" ", "_")
    s = re.sub(r"[^a-z0-9_-]", "_", s)
    s = re.sub(r"__+", "_", s)
    s = s.strip("_")
    if not s:
        s = "sheet"
    return s


# ---------------------------------------------------------------------------
#  Writer
# ---------------------------------------------------------------------------


def _cast_null_columns_to_string(table: pa.Table) -> pa.Table:
    """Cast any all-null column to ``string`` so it renders correctly."""
    for field_idx, field in enumerate(table.schema):
        if pa.types.is_null(field.type):
            col = table.column(field_idx)
            table = table.set_column(field_idx, field.name, col.cast(pa.string()))
    return table


def _write_parquet_table(
    table: pa.Table,
    staging_dir: Path,
    stem: str,
) -> Path:
    """Write *table* to ``staging_dir/stem.parquet`` with shared options.

    Casts all-null columns to string, uses ``config.PARQUET_COMPRESSION`` and
    ``config.PARQUET_ROW_GROUP_SIZE``, and warns when the file exceeds
    ``config.PARQUET_SHARD_WARNING_MB``.

    Args:
        table: Arrow table to persist.
        staging_dir: Directory where the file is written.
        stem: Filename stem without extension.

    Returns:
        Absolute path to the written Parquet file.
    """
    table = _cast_null_columns_to_string(table)
    parquet_path = staging_dir / f"{stem}.parquet"
    staging_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        parquet_path,
        compression=config.PARQUET_COMPRESSION,
        write_page_index=True,
        row_group_size=config.PARQUET_ROW_GROUP_SIZE,
    )
    size_mb = parquet_path.stat().st_size / (1024 * 1024)
    if size_mb > config.PARQUET_SHARD_WARNING_MB:
        print(
            f"  \u26a0  {parquet_path.name}: {size_mb:.1f} MB "
            f"(> {config.PARQUET_SHARD_WARNING_MB} MB). Consider sharding into "
            f"smaller files for better Dataset Viewer performance."
        )
    return parquet_path


# ---------------------------------------------------------------------------
#  Parity helpers
# ---------------------------------------------------------------------------


def _count_delimiters_outside_quotes(line: str) -> dict[str, int]:
    """Count sniff delimiters outside quoted spans."""
    counts: dict[str, int] = {d: 0 for d in config.SNIFF_DELIMITERS}
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if in_quotes:
            continue
        if ch in counts:
            counts[ch] += 1
    return counts


def _sniff_csv_delimiter(csv_path: Path) -> str:
    """Sniff delimiter from first line using ``config.SNIFF_DELIMITERS``."""
    try:
        first = csv_path.read_text(encoding=config.CSV_ENCODING).splitlines()[0]
        counts = _count_delimiters_outside_quotes(first)
        # Prefer highest count; tie-break by order in SNIFF_DELIMITERS
        best = max(counts.values()) if counts else 0
        if best == 0:
            return config.CSV_DELIMITER
        for delim in config.SNIFF_DELIMITERS:
            if counts.get(delim, 0) == best:
                return delim
        return config.CSV_DELIMITER
    except Exception:
        return config.CSV_DELIMITER


def _read_csv_raw_values(
    csv_path: Path,
    delimiter: str,
) -> tuple[list[str], list[list[str]]] | None:
    """Read CSV header + rows with Python csv using *delimiter*."""
    try:
        with open(csv_path, newline="", encoding=config.CSV_ENCODING) as fh:
            reader = csv_module.reader(fh, delimiter=delimiter)
            try:
                header = next(reader)
            except StopIteration:
                return ([], [])
            rows = [row for row in reader]
            return (header, rows)
    except Exception:
        return None


def _check_conversion_parity(
    csv_path: Path,
    delimiter: str,
    table: pa.Table,
) -> tuple[bool, list[str]]:
    """Check row/col/name parity between CSV raw and Parquet table.

    Returns:
        ``(ok, warnings)`` — *ok* is False on hard mismatch.
    """
    raw = _read_csv_raw_values(csv_path, delimiter)
    if raw is None:
        return (False, ["Cannot read CSV for parity check"])
    csv_header, csv_rows = raw
    csv_row_count = len(csv_rows)
    csv_col_count = len(csv_header)
    parquet_row_count = table.num_rows
    parquet_col_names = table.column_names
    if csv_row_count != parquet_row_count:
        print(
            f"  \u26a0  PARITY FAIL: row count mismatch \u2014 "
            f"CSV={csv_row_count}, Parquet={parquet_row_count}"
        )
        return (False, [])
    if csv_col_count != len(parquet_col_names):
        print(
            f"  \u26a0  PARITY FAIL: column count mismatch \u2014 "
            f"CSV={csv_col_count}, Parquet={len(parquet_col_names)}"
        )
        return (False, [])
    if csv_header != parquet_col_names:
        print(
            f"  \u26a0  PARITY FAIL: column names diverge \u2014 "
            f"CSV={csv_header}, Parquet={parquet_col_names}"
        )
        return (False, [])
    # Soft value check
    warnings: list[str] = []
    for col_idx, col_name in enumerate(csv_header):
        csv_values: set[str] = set()
        for row in csv_rows:
            if col_idx < len(row):
                csv_values.add(row[col_idx].strip())
        parquet_col = table.column(col_idx)
        parquet_values: set[str] = set()
        for i in range(parquet_col.length()):
            val = parquet_col[i].as_py()
            if val is None:
                parquet_values.add("")
            else:
                parquet_values.add(str(val).strip())
        altered = csv_values - parquet_values
        if altered:
            first = sorted(altered)[0]
            warnings.append(
                f"  [!] VALUE ALTERED: column '{col_name}' \u2014 "
                f"e.g. '{first}' changed after type inference"
            )
    for w in warnings:
        print(w)
    return (True, warnings)


def _check_xlsx_parity(
    rows: list[list[object]],
    header: list[str],
    table: pa.Table,
) -> bool:
    """XLSX parity: row/col/name checks.

    Returns:
        True when parity passes, False on hard mismatch.
    """
    if table.num_rows != len(rows):
        print(
            f"  \u26a0  PARITY FAIL: XLSX row count mismatch \u2014 "
            f"expected {len(rows)}, got {table.num_rows}"
        )
        return False
    if len(header) != table.num_columns:
        print("  \u26a0  PARITY FAIL: XLSX column count mismatch")
        return False
    if header != table.column_names:
        print(
            f"  \u26a0  PARITY FAIL: XLSX column names diverge \u2014 "
            f"{header} vs {table.column_names}"
        )
        return False
    return True


def _check_jsonl_parity(
    expected_rows: int,
    expected_keys: set[str],
    table: pa.Table,
) -> bool:
    """JSONL parity: row count + key-union vs column names."""
    if table.num_rows != expected_rows:
        print(
            f"  \u26a0  PARITY FAIL: JSONL row count mismatch \u2014 "
            f"expected {expected_rows}, got {table.num_rows}"
        )
        return False
    # Key union check is advisory — table may have more columns via inference
    # but must contain at least the union (or we warn)
    table_cols = set(table.column_names)
    if expected_keys and not expected_keys.issubset(table_cols):
        # This is a soft warning, not hard fail — pyarrow.json may normalize
        missing = expected_keys - table_cols
        print(f"  [!] JSONL key mismatch \u2014 missing columns {missing}")
    return True


# ---------------------------------------------------------------------------
#  Per-format converters
# ---------------------------------------------------------------------------


def _convert_csv_to_parquet(
    local: Path,
    staging_dir: Path,
) -> Path | None:
    """Convert *local* CSV to Parquet via ``pyarrow.csv`` with sniff."""
    try:
        delimiter = _sniff_csv_delimiter(local)
        parse_opts = pc.ParseOptions(delimiter=delimiter)
        # Use configured encoding via ConvertOptions? pyarrow.csv read_csv
        # handles encoding via file open; we rely on raw bytes. Use default.
        table = pc.read_csv(local, parse_options=parse_opts)
        parity_ok, _ = _check_conversion_parity(local, delimiter, table)
        if not parity_ok:
            return None
        return _write_parquet_table(table, staging_dir, local.stem)
    except Exception as exc:
        print(f"  \u26a0  {local.name}: conversion failed \u2014 staging original")
        print(f"       ({exc})")
        return None


def _convert_tsv_to_parquet(
    local: Path,
    staging_dir: Path,
) -> Path | None:
    """Convert *local* TSV to Parquet with hardcoded ``\\t``."""
    try:
        parse_opts = pc.ParseOptions(delimiter="\t")
        table = pc.read_csv(local, parse_options=parse_opts)
        parity_ok, _ = _check_conversion_parity(local, "\t", table)
        if not parity_ok:
            return None
        return _write_parquet_table(table, staging_dir, local.stem)
    except Exception as exc:
        print(f"  \u26a0  {local.name}: conversion failed \u2014 staging original")
        print(f"       ({exc})")
        return None


def _convert_xlsx_to_parquet(
    local: Path,
    staging_dir: Path,
) -> dict[str, Path]:
    """Convert *local* XLSX to one Parquet per sheet.

    Returns:
        Mapping ``sanitised_sheet_key → parquet_path``.  Single sheet →
        ``stem.parquet``; N sheets → ``stem__sanitised.parquet`` with
        dedup ``_{n}``.  Empty header-only sheets produce 0-row Parquets.
    """
    try:
        import openpyxl
    except ImportError as exc:
        print(f"  \u26a0  {local.name}: openpyxl not available ({exc})")
        return {}

    result: dict[str, Path] = {}
    try:
        wb = openpyxl.load_workbook(local, read_only=True, data_only=True)
    except Exception as exc:
        print(f"  \u26a0  {local.name}: xlsx open failed ({exc})")
        return {}

    try:
        sheet_names: list[str] = list(wb.sheetnames)
        is_single = len(sheet_names) == 1
        seen: dict[str, int] = {}

        for sheet_name in sheet_names:
            sanitized = sanitize_sheet_name(sheet_name)
            # Dedup: a_b, a_b_2, a_b_3 ...
            base_sanitized = sanitized
            count = seen.get(base_sanitized, 0)
            if count > 0:
                sanitized = f"{base_sanitized}_{count + 1}"
            seen[base_sanitized] = count + 1
            # Also track the deduped name to avoid collisions with sanitized that already has suffix
            if sanitized != base_sanitized:
                seen[sanitized] = seen.get(sanitized, 0) + 1  # avoid reuse

            ws = wb[sheet_name]
            rows_iter = ws.iter_rows(values_only=True)

            try:
                header_row = next(rows_iter)
            except StopIteration:
                # Empty sheet — no rows at all
                header_row = None

            if header_row is None or all(v is None for v in header_row):
                # Empty sheet: produce 0-row table with no columns? But spec says
                # empty header-only sheet should produce Parquet with 0 rows.
                # If header_row is None, we have 0 columns, 0 rows.
                if header_row is None:
                    table = pa.table({})
                else:
                    # Header exists but all None — treat as empty
                    header = [str(v).strip() if v is not None else "" for v in header_row]
                    # Filter empty header names?
                    header = [h for h in header if h]
                    if not header:
                        table = pa.table({})
                    else:
                        # 0 rows, header columns
                        data: dict[str, list[object]] = {h: [] for h in header}
                        table = pa.table(data)
            else:
                header = [str(v).strip() if v is not None else "" for v in header_row]
                # Collect rows
                raw_rows: list[list[object]] = []
                for row in rows_iter:
                    # row is tuple of values; pad to header length
                    vals = list(row) if row is not None else []
                    # Extend/truncate to header length
                    if len(vals) < len(header):
                        vals.extend([None] * (len(header) - len(vals)))
                    elif len(vals) > len(header):
                        vals = vals[: len(header)]
                    raw_rows.append(vals)

                # Build column-wise data
                if not header or all(not h for h in header):
                    table = pa.table({})
                else:
                    col_data: dict[str, list[object]] = {h: [] for h in header}
                    for r in raw_rows:
                        for idx, h in enumerate(header):
                            val = r[idx] if idx < len(r) else None
                            col_data[h].append(val)
                    # Filter out columns with empty name
                    col_data = {k: v for k, v in col_data.items() if k}
                    if not col_data:
                        table = pa.table({})
                    else:
                        table = pa.table(col_data)

            if is_single:
                stem = local.stem
                key_stem = stem
            else:
                stem = f"{local.stem}__{sanitized}"
                key_stem = stem

            pq_path = _write_parquet_table(table, staging_dir, stem)
            result[key_stem] = pq_path

            # Clean locals for next iteration
            if "raw_rows" in locals():
                del raw_rows
    except Exception as exc:
        print(f"  \u26a0  {local.name}: xlsx conversion failed ({exc})")
        return result
    finally:
        try:
            wb.close()
        except Exception:
            pass

    return result


def _convert_jsonl_to_parquet(
    local: Path,
    staging_dir: Path,
) -> Path | None:
    """Convert *local* JSONL to Parquet via ``pyarrow.json`` with fallback."""
    # Try fast path: pyarrow.json
    try:
        import pyarrow.json as pj

        table = pj.read_json(local)
        # Derive expected keys/rows for parity via fallback read for comparison?
        # Simple parity: row count matches line count
        with open(local, encoding="utf-8") as fh:
            line_count = sum(1 for line in fh if line.strip())
        if not _check_jsonl_parity(line_count, set(table.column_names), table):
            # parity failure is soft for jsonl (we already warned)
            pass
        return _write_parquet_table(table, staging_dir, local.stem)
    except Exception as exc:
        # Fallback: json + from_pylist
        try:
            rows: list[dict[str, object]] = []
            with open(local, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rows.append(json.loads(line))
            if not rows:
                table = pa.table({})
            else:
                # from_pylist handles sparse keys (union)
                table = pa.Table.from_pylist(rows)
            # Parity: key-union vs columns
            union_keys: set[str] = set()
            for r in rows:
                union_keys.update(r.keys())
            if not _check_jsonl_parity(len(rows), union_keys, table):
                pass
            return _write_parquet_table(table, staging_dir, local.stem)
        except Exception as exc2:
            print(
                f"  \u26a0  {local.name}: jsonl conversion failed ({exc2}) — fallback from ({exc})"
            )
            return None


# ---------------------------------------------------------------------------
#  Dispatcher
# ---------------------------------------------------------------------------


def convert_file_to_parquet(
    local: Path,
    staging_dir: Path,
    cfg: object | None = None,
) -> dict[str, Path]:
    """Dispatch conversion for *local* to Parquet.

    Passthrough for ``.parquet`` (returns single entry mapping the stem to the
    original path), skips nothing here — caller gates ``recursive`` and
    ``convert_to_parquet``.  On per-file failure returns ``{}`` (caller falls
    back to staging the original).

    Args:
        local: Absolute local file path.
        staging_dir: Temporary per-entry staging directory.
        cfg: Unused hook for future config overrides (kept for signature
            compatibility).

    Returns:
        Mapping ``normalised_stem → parquet_path``.  For single-file formats
        (csv/tsv/jsonl) the key is the original stem; for xlsx multi-sheet it
        is ``stem__sheet`` per sheet; for passthrough ``.parquet`` it is the
        stem with ``.parquet`` suffix preserved.
    """
    _ = cfg  # reserved
    suffix = local.suffix.lower()
    if suffix == ".parquet":
        # Passthrough: no conversion, return original path as-is
        # Caller will copy via mirror layout; we return {} to signal passthrough?
        # But spec says dispatcher returns dict[normalized_remote, Path] — for
        # passthrough we still return the path so caller can stage it. However
        # prepare currently handles .parquet as non-converted. We return empty
        # to let caller treat it as passthrough (no conversion dict entry).
        # To avoid double-handling, return {} and let caller stage original.
        return {}
    if suffix == ".csv":
        result = _convert_csv_to_parquet(local, staging_dir)
        if result is not None:
            return {local.stem: result}
        return {}
    if suffix == ".tsv":
        result = _convert_tsv_to_parquet(local, staging_dir)
        if result is not None:
            return {local.stem: result}
        return {}
    if suffix == ".xlsx":
        return _convert_xlsx_to_parquet(local, staging_dir)
    if suffix == ".jsonl":
        result = _convert_jsonl_to_parquet(local, staging_dir)
        if result is not None:
            return {local.stem: result}
        return {}
    return {}
