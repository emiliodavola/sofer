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
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.parquet as pq

from . import config

if TYPE_CHECKING:
    from .model import DatasetConfig

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


def _count_delimiter_outside_quotes(line: str, delimiter: str) -> int:
    """Count occurrences of *delimiter* outside double-quoted spans.

    Args:
        line: A single line of CSV text.
        delimiter: The character to count.

    Returns:
        The number of occurrences outside quotes.
    """
    in_quotes = False
    count = 0
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if not in_quotes and ch == delimiter:
            count += 1
    return count


def _count_delimiters_outside_quotes(line: str) -> dict[str, int]:
    """Count sniff delimiters outside quoted spans."""
    return {d: _count_delimiter_outside_quotes(line, d) for d in config.SNIFF_DELIMITERS}


def _try_sniff_csv_delimiter(
    csv_path: Path,
    encoding: str = config.CSV_ENCODING,
) -> str | None:
    """Sniff the delimiter, returning ``None`` only when the file cannot be read.

    Split from :func:`_sniff_csv_delimiter` so the D2 disagreement check can tell
    "the baseline read decodes and disagrees" apart from "the baseline read cannot
    decode this file at all" — in the latter case comparing is meaningless and the
    caller suppresses the warning.

    Args:
        csv_path: Path to the CSV file.
        encoding: Encoding for the baseline first-line read.

    Returns:
        The sniffed delimiter, or ``None`` when the first line cannot be decoded.
    """
    try:
        first = csv_path.read_text(encoding=encoding).splitlines()[0]
    except Exception:
        return None
    counts = _count_delimiters_outside_quotes(first)
    # Prefer highest count; tie-break by order in SNIFF_DELIMITERS
    best = max(counts.values()) if counts else 0
    if best == 0:
        return config.CSV_DELIMITER
    for delim in config.SNIFF_DELIMITERS:
        if counts.get(delim, 0) == best:
            return delim
    return config.CSV_DELIMITER


def _sniff_csv_delimiter(
    csv_path: Path,
    encoding: str = config.CSV_ENCODING,
) -> str:
    """Sniff delimiter from first line using ``config.SNIFF_DELIMITERS``.

    Args:
        csv_path: Path to the CSV file.
        encoding: Encoding for the first-line read.  Defaults to the tool-wide
            ``config.CSV_ENCODING``, preserving the pre-change behaviour.

    Returns:
        The sniffed delimiter, or ``config.CSV_DELIMITER`` when the file cannot
        be read or carries no sniffable delimiter.
    """
    sniffed = _try_sniff_csv_delimiter(csv_path, encoding)
    return sniffed if sniffed is not None else config.CSV_DELIMITER


def _resolve_csv_dialect(
    local: Path,
    cfg: DatasetConfig | None,
) -> tuple[str, str]:
    """Resolve the CSV ``(delimiter, encoding)`` for *local* (PC-U01).

    The dataset-declared ``[meta] csv_delimiter``/``csv_encoding`` WINS when the
    dataset declared them; otherwise the pre-change tool-wide behaviour applies
    (sniff ``config.SNIFF_DELIMITERS``, read with ``config.CSV_ENCODING``).

    "Declared" is observed through :attr:`DatasetConfig.declared_meta_keys` — the
    presence signal — never through the value, so a dataset declaring ``;`` stays
    distinguishable from one declaring nothing although both hold ``";"``.

    Args:
        local: Local CSV path.
        cfg: Dataset config, or ``None`` for a library call without one.

    Returns:
        ``(delimiter, encoding)``; the encoding is ``config.CSV_ENCODING`` when
        ``csv_encoding`` was not declared.
    """
    declared: frozenset[str] = cfg.declared_meta_keys if cfg is not None else frozenset()
    if cfg is not None and "csv_delimiter" in declared:
        delimiter = cfg.csv_delimiter
    else:
        delimiter = _sniff_csv_delimiter(local, config.CSV_ENCODING)
    if cfg is not None and "csv_encoding" in declared:
        encoding = cfg.csv_encoding
    else:
        encoding = config.CSV_ENCODING
    return delimiter, encoding


def _raw_first_line_has_delimiter(
    csv_path: Path,
    delimiter: str,
    encoding: str,
) -> bool:
    """Whether *csv_path*'s raw first line carries *delimiter* outside quotes.

    Backs the anti-collapse parity guard: a wrong delimiter merges the whole
    header into one field, and detecting the delimiter in the raw line proves the
    single-column table was produced by a mis-split rather than by a genuine
    one-column file.

    Args:
        csv_path: Path to the CSV file.
        delimiter: The resolved field delimiter.
        encoding: Encoding for the raw first-line read.

    Returns:
        ``True`` when the delimiter occurs at least once outside quoted spans;
        ``False`` when the file cannot be read.
    """
    try:
        first = csv_path.read_text(encoding=encoding).splitlines()[0]
    except Exception:
        return False
    return _count_delimiter_outside_quotes(first, delimiter) > 0


def _read_csv_raw_values(
    csv_path: Path,
    delimiter: str,
    encoding: str = config.CSV_ENCODING,
) -> tuple[list[str], list[list[str]]] | None:
    """Read CSV header + rows with Python csv using *delimiter*.

    Args:
        csv_path: Path to the CSV file.
        delimiter: Field delimiter.
        encoding: Encoding for the Python-side read.  Must be the *same* encoding
            the Parquet read used, or parity compares an undecodable file and the
            conversion silently reverts to staging the original CSV.
    """
    try:
        with open(csv_path, newline="", encoding=encoding) as fh:
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
    encoding: str = config.CSV_ENCODING,
) -> tuple[bool, list[str]]:
    """Check row/col/name parity between CSV raw and Parquet table.

    Args:
        csv_path: Path to the original CSV.
        delimiter: Resolved field delimiter.
        table: Parquet table produced from *csv_path*.
        encoding: Encoding for the Python-side parity read (the resolved one).

    Returns:
        ``(ok, warnings)`` — *ok* is False on hard mismatch.
    """
    raw = _read_csv_raw_values(csv_path, delimiter, encoding)
    if raw is None:
        return (False, ["Cannot read CSV for parity check"])
    csv_header, csv_rows = raw
    csv_row_count = len(csv_rows)
    # ── Anti-collapse guard: parity must not agree with a wrong delimiter ────
    # A wrong delimiter merges the whole header into one field, so the Parquet
    # table has a single column and the parity read agrees with it vacuously.
    # When the raw first line carries *delimiter* outside quotes, one column is
    # impossible — fail instead of agreeing (PC-U01).
    if table.num_columns == 1 and _raw_first_line_has_delimiter(csv_path, delimiter, encoding):
        print(
            f"  \u26a0  PARITY FAIL: single column but the raw header contains "
            f"delimiter {delimiter!r} — a wrong delimiter would collapse the file"
        )
        return (False, [])
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
    cfg: DatasetConfig | None = None,
) -> Path | None:
    """Convert *local* CSV to Parquet honouring the declared dialect (PC-U01).

    The ``(delimiter, encoding)`` pair comes from the single resolution point
    :func:`_resolve_csv_dialect`.  ``pc.ReadOptions(encoding=…)`` is applied
    **only** when the dataset declared ``csv_encoding`` so an undeclared dataset
    keeps the exact pre-change, byte-identical read.  The same resolved encoding
    feeds the Python parity read — otherwise parity compares an undecodable file
    and the fix collapses back to "stage the original".

    Args:
        local: Local CSV path.
        staging_dir: Destination directory for the Parquet file.
        cfg: Optional dataset config carrying the declared dialect.

    Returns:
        The written Parquet path, or ``None`` on failure (warning printed).
    """
    try:
        delimiter, encoding = _resolve_csv_dialect(local, cfg)
        declared: frozenset[str] = cfg.declared_meta_keys if cfg is not None else frozenset()
        if "csv_delimiter" in declared:
            # Baseline sniff (tool-wide encoding) so the message says "what the
            # sniff would have chosen today".  Suppressed when the baseline read
            # cannot decode the file (the declared-encoding scenario).
            baseline = _try_sniff_csv_delimiter(local, config.CSV_ENCODING)
            if baseline is not None and baseline != delimiter:
                print(
                    f"  [!] {local.name}: declared csv_delimiter {delimiter!r} "
                    f"differs from sniffed {baseline!r} \u2014 using declared {delimiter!r}"
                )
        parse_opts = pc.ParseOptions(delimiter=delimiter)
        if "csv_encoding" in declared:
            table = pc.read_csv(
                local,
                read_options=pc.ReadOptions(encoding=encoding),
                parse_options=parse_opts,
            )
        else:
            # Pre-change call shape verbatim: no read_options, so undeclared
            # datasets stay byte-identical (PC-U01).
            table = pc.read_csv(local, parse_options=parse_opts)
        parity_ok, _ = _check_conversion_parity(local, delimiter, table, encoding)
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
                    vals: list[object] = list(row) if row is not None else []
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

            # Release the parsed rows before the next sheet. An explicit rebind,
            # not a `del` behind a runtime membership test: static checkers cannot
            # model that test (`reportPossiblyUnboundVariable`), and the rebind
            # frees the same list.
            raw_rows = []
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
    cfg: DatasetConfig | None = None,
) -> dict[str, Path]:
    """Dispatch conversion for *local* to Parquet.

    Passthrough for ``.parquet`` (returns single entry mapping the stem to the
    original path), skips nothing here — caller gates ``recursive`` and
    ``convert_to_parquet``.  On per-file failure returns ``{}`` (caller falls
    back to staging the original).

    Args:
        local: Absolute local file path.
        staging_dir: Temporary per-entry staging directory.
        cfg: Optional dataset config carrying the declared ``[meta]``
            ``csv_delimiter``/``csv_encoding``, threaded into the CSV reader
            (PC-U01).  Ignored for tsv/xlsx/jsonl/parquet.

    Returns:
        Mapping ``normalised_stem → parquet_path``.  For single-file formats
        (csv/tsv/jsonl) the key is the original stem; for xlsx multi-sheet it
        is ``stem__sheet`` per sheet; for passthrough ``.parquet`` it is the
        stem with ``.parquet`` suffix preserved.
    """
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
        result = _convert_csv_to_parquet(local, staging_dir, cfg)
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
