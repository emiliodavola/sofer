"""Profile a dataset read-only and emit a ``metadata.yaml`` document.

The ``profile`` command is the entry point of sofer v2's documentation
pipeline. It detects the dataset format from its extension, reads the dataset
(CSV/TSV through the bounded, encoding-fallback
:func:`sofer._csv_reader.stream_csv`; Parquet/XLSX/JSONL through
:func:`sofer.codebook._read_file`), infers a coarse storage type and a semantic
type per column, flags possible PII, assembles a
:class:`sofer.metadata.Metadata` document, serializes it to ``metadata.yaml``,
and reports the human-input fields that are still missing. It never modifies
the source dataset (PRF-03).
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from . import config
from ._converters import (
    sanitize_sheet_name,  # noqa: F401 — re-exported for parity, used via _read_xlsx_sheets
)
from ._csv_reader import stream_csv
from ._formats import SUPPORTED_FORMATS
from ._sentinels import count_unique_non_missing
from .codebook import _read_file, _read_xlsx_sheets, infer_column_type
from .metadata import (
    ColumnMetadata,
    DocumentationMetadata,
    FileMetadata,
    GeneratedMetadata,
    Metadata,
    SemanticType,
    StructureMetadata,
    missing_fields,
    serialize,
)
from .pii import infer_pii_types
from .semantic import _is_missing, infer_semantic_types

if TYPE_CHECKING:
    from .model import DatasetConfig

# Formats read through the bounded streaming CSV reader. TSV uses a tab
# delimiter; CSV uses the configured delimiter (CSV_DELIMITER).
_STREAMED_FORMATS = frozenset({".csv", ".tsv"})

_METADATA_FILENAME = "metadata.yaml"


def _profile_output_for_rel(
    profiles_dir: Path,
    rel_stem: Path,
    sheet: str | None,
) -> Path:
    """Compute the profile output path for a ``(rel_stem, sheet)`` pair.

    Mirrors ``codebook._codebook_output_for_rel`` — ``PurePath.suffixes``
    replaces only the last suffix; multisheet inserts ``__<sanitized>``.

    Args:
        profiles_dir: Base profiles directory (``write_root / PROFILE_DIR``).
        rel_stem: Relative stem derived from ``relative_to(data_dir)``.
        sheet: Sanitized sheet name or ``None`` (single-table).

    Returns:
        Absolute output path for the ``metadata.yaml``.
    """
    if sheet is None:
        suffixes = PurePath(rel_stem.name).suffixes
        if len(suffixes) > 1:
            target_suffix = "".join(suffixes[:-1]) + ".metadata.yaml"
        else:
            target_suffix = ".metadata.yaml"
        return (profiles_dir / rel_stem).with_suffix(target_suffix)
    base_single = _profile_output_for_rel(profiles_dir, rel_stem, None)
    base_str = str(base_single)
    base_no_ext = (
        base_str[: -len(".metadata.yaml")]
        if base_str.endswith(".metadata.yaml")
        else str(base_single.with_suffix(""))
    )
    return Path(base_no_ext + f"__{sheet}.metadata.yaml")


def _normalize_profile_collision_key(path: Path) -> str:
    """Normalize a profile path for collision detection (``__+`` -> ``_``).

    Mirrors ``_normalize_codebook_collision_key`` so ``a__ventas`` and
    ``a_ventas`` collide.
    """
    return re.sub(r"__+", "_", path.as_posix())


def profile(
    dataset_path: Path,
    output_dir: Path | None = None,
    *,
    force: bool = False,
    delimiter: str | None = None,
    encoding: str | None = None,
) -> int:
    """Profile *dataset_path* read-only and return an exit code.

    Orchestration (spec PRF-02):

    1. Detect the format from the file extension via
       :data:`sofer._formats.SUPPORTED_FORMATS`. An unsupported extension
       prints a clean error and returns ``1`` (no ``metadata.yaml``).
    2. Read the dataset: CSV/TSV via :func:`stream_csv` (bounded by
       ``PROFILE_MAX_SAMPLE``, config delimiter/encoding, encoding fallback);
       Parquet/XLSX/JSONL via :func:`sofer.codebook._read_file`.
    3. Per column: infer the coarse ``storage_type`` via
       :func:`sofer.codebook.infer_column_type`, the semantic type via
       :func:`sofer.semantic.infer_semantic_types`, and PII findings via
       :func:`sofer.pii.infer_pii_types`.
    4. Assemble the :class:`Metadata` document, derive its
       :func:`sofer.metadata.missing_fields`, and serialize it to
       ``metadata.yaml`` next to the dataset (or in *output_dir*).
    5. Print the missing human-input fields.

    The source dataset is opened strictly for reading — its bytes are never
    modified (PRF-03).

    Args:
        dataset_path: Path to the dataset file to profile.
        output_dir:  Directory for ``metadata.yaml`` (default: the dataset's
            directory).
        force: When ``False`` and the destination exists, raise
            ``FileExistsError`` with a ``use --force to overwrite`` hint
            (PRF-06). When ``True``, overwrite unconditionally.
        delimiter: Explicit CSV field delimiter for this call (PRF-07); when
            ``None`` the configured ``config.CSV_DELIMITER`` applies. ``.tsv``
            stays tab-delimited by format, and non-streamed formats ignore it.
        encoding: Explicit file encoding for this call (PRF-07); when ``None``
            the configured ``config.CSV_ENCODING`` applies, still fronting the
            shared ``utf-8-sig → utf-8`` fallback chain.

    Returns:
        ``0`` on success, ``1`` when the format is unsupported or the file
        does not exist.

    Raises:
        FileExistsError: When the destination exists and *force* is ``False``.
    """
    dataset_path = Path(dataset_path)
    suffix = dataset_path.suffix.lower()

    if suffix not in SUPPORTED_FORMATS:
        print(
            f"Error: Unsupported file format: '{dataset_path.name}' "
            f"(extension '{suffix or '<none>'}' is not supported).",
            file=sys.stderr,
        )
        print(
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}.",
            file=sys.stderr,
        )
        return 1

    if not dataset_path.exists():
        print(f"Error: Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    if suffix in _STREAMED_FORMATS:
        resolved_delimiter = (
            "\t"
            if suffix == ".tsv"
            else (delimiter if delimiter is not None else config.CSV_DELIMITER)
        )
        resolved_encoding = encoding if encoding is not None else config.CSV_ENCODING
        headers, columns, rows = _stream_columns(
            dataset_path, resolved_delimiter, resolved_encoding
        )
    else:
        headers, columns, _dtypes = _read_file(str(dataset_path))
        rows = len(columns[0]) if columns else 0
        resolved_encoding = ""
        resolved_delimiter = ""

    schema = [_build_column(name, values) for name, values in zip(headers, columns)]

    meta = Metadata(
        file=FileMetadata(
            path=str(dataset_path),
            format=suffix.lstrip("."),
            encoding=resolved_encoding,
            delimiter=resolved_delimiter,
            rows=rows,
            columns=len(headers),
        ),
        structure=StructureMetadata(schema=schema),
        generated=GeneratedMetadata(timestamp=_now_iso()),
    )
    meta.documentation = DocumentationMetadata(missing_fields=missing_fields(meta))

    out_dir = Path(output_dir) if output_dir is not None else dataset_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = out_dir / _METADATA_FILENAME
    if metadata_path.exists() and not force:
        raise FileExistsError(f"use --force to overwrite {metadata_path}")
    metadata_path.write_text(serialize(meta), encoding="utf-8")

    print(f"  OK  Wrote {metadata_path}")
    gaps = meta.documentation.missing_fields
    if gaps:
        print(f"  Missing fields (human input): {', '.join(gaps)}")
    return 0


def generate_all_profiles(
    cfg: DatasetConfig,
    output_dir: str | Path | None = None,
    delimiter: str | None = None,
    encoding: str | None = None,
) -> list[str]:
    """Generate one ``metadata.yaml`` per ``[[file]]`` entry under ``profiles/``.

    Each profile is written to ``{PROFILE_DIR}/<rel-stem>.metadata.yaml``,
    where ``<rel-stem>`` is the file's path relative to the ``cache/``
    directory (falling back to the TOML config directory for files outside
    ``cache/``). For ``.xlsx`` with N>1 sheets N profiles are emitted as
    ``profiles/<rel>/<stem>__<sanitized>.metadata.yaml`` (single-sheet
    stays suffix-less). Sanitization reuses :func:`sanitize_sheet_name`
    with ``seen`` dedup ``_{n}`` verbatim; collision keys are normalized
    via ``re.sub(r"__+","_",path)`` so ``a__ventas`` and ``a_ventas``
    collide. Non-colliding outputs are written before ``ValueError`` is
    raised naming every colliding source as ``<path>::<sheet>``.

    Args:
        cfg: A ``DatasetConfig`` loaded from a TOML file.
        output_dir: When given (Option B), profiles are written under
            ``output_dir/profiles/`` and the shared ``cache/profiles/``
            directory is never mutated. When ``None`` (default), profiles go
            to ``cache/profiles/``.
        delimiter: Explicit CSV field delimiter applied to every ``.csv``
            entry (PRF-07); ``None`` resolves to ``config.CSV_DELIMITER``.
            ``.tsv`` stays tab-delimited and non-streamed formats ignore it.
        encoding: Explicit encoding applied to every ``.csv``/``.tsv`` entry
            (PRF-07); ``None`` resolves to ``config.CSV_ENCODING``.

    Returns:
        List of generated profile file paths.

    Raises:
        ValueError: When two or more files resolve to the same output path
            (after non-colliding profiles have already been written).
    """
    base_dir = cfg._base_dir.resolve()
    data_dir = base_dir / config.OUTPUT_DIR

    if output_dir is None:
        write_root = data_dir
    else:
        out = Path(output_dir)
        if not out.is_absolute():
            out = base_dir / out
        write_root = out.resolve()
    profiles_dir = write_root / config.PROFILE_DIR

    # ── First pass: collect valid, readable file entries ─────────────
    entries: list[tuple[Path, str]] = []
    for file_entry in cfg.files:
        local = file_entry.resolve(base_dir)

        if local.is_dir():
            print(f"  \u26a0  Skipping directory: {local}", file=sys.stderr)
            continue

        if not local.exists():
            print(f"  \u26a0  Skipping missing file: {local}", file=sys.stderr)
            continue

        suffix = local.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            print(f"  \u26a0  Unsupported format, skipping: {local}", file=sys.stderr)
            continue

        entries.append((local, suffix))

    if not entries:
        return []

    # ── Sheet-expanded output paths and normalized collision map ──────
    expanded: list[tuple[Path, str | None, Path]] = []
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
                print(f"  \u26a0  Error reading {local}: {exc}", file=sys.stderr)
                continue
            if not sheets:
                out = _profile_output_for_rel(profiles_dir, rel_stem, None)
                expanded.append((local, None, out))
                xlsx_cache[local] = sheets
                continue
            if len(sheets) == 1:
                first_key = next(iter(sheets))
                out = _profile_output_for_rel(profiles_dir, rel_stem, None)
                expanded.append((local, first_key, out))
                xlsx_cache[local] = sheets
            else:
                for sanitized in sheets:
                    out = _profile_output_for_rel(profiles_dir, rel_stem, sanitized)
                    expanded.append((local, sanitized, out))
                xlsx_cache[local] = sheets
        else:
            out = _profile_output_for_rel(profiles_dir, rel_stem, None)
            expanded.append((local, None, out))

    if not expanded:
        return []

    collision_map: dict[str, list[tuple[Path, str | None, Path]]] = {}
    for local, sheet, out in expanded:
        key = _normalize_profile_collision_key(out)
        collision_map.setdefault(key, []).append((local, sheet, out))

    colliding_keys: set[str] = {k for k, v in collision_map.items() if len(v) > 1}
    colliding_expanded: set[tuple[Path, str | None]] = set()
    for key in colliding_keys:
        for local, sheet, _out in collision_map[key]:
            colliding_expanded.add((local, sheet))

    # ── Generate per-(file,sheet) profiles (non-colliding only) ─────
    generated: list[str] = []

    for local, suffix in entries:
        if suffix != ".xlsx":
            if (local, None) in colliding_expanded:
                continue
            out_path = next((o for lo, sh, o in expanded if lo == local and sh is None), None)
            if out_path is None:
                continue
            try:
                headers, columns, rows, used_encoding, used_delimiter = _read_dataset_for_profile(
                    local, suffix, delimiter=delimiter, encoding=encoding
                )
            except Exception as exc:
                print(f"  \u2717  Error reading {local}: {exc}", file=sys.stderr)
                continue
            schema = [_build_column(name, values) for name, values in zip(headers, columns)]
            meta = Metadata(
                file=FileMetadata(
                    path=str(local),
                    format=suffix.lstrip("."),
                    encoding=used_encoding,
                    delimiter=used_delimiter,
                    rows=rows,
                    columns=len(headers),
                ),
                structure=StructureMetadata(schema=schema),
                generated=GeneratedMetadata(timestamp=_now_iso()),
            )
            meta.documentation = DocumentationMetadata(missing_fields=missing_fields(meta))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(serialize(meta), encoding="utf-8")
            generated.append(str(out_path))
            print(f"  OK  {out_path}")
        else:
            sheets = xlsx_cache.get(local, {})
            if not sheets:
                if (local, None) in colliding_expanded:
                    continue
                out_path = next((o for lo, sh, o in expanded if lo == local and sh is None), None)
                if out_path is None:
                    continue
                schema = []
                meta = Metadata(
                    file=FileMetadata(
                        path=str(local),
                        format="xlsx",
                        encoding="",
                        delimiter="",
                        rows=0,
                        columns=0,
                    ),
                    structure=StructureMetadata(schema=schema),
                    generated=GeneratedMetadata(timestamp=_now_iso()),
                )
                meta.documentation = DocumentationMetadata(missing_fields=missing_fields(meta))
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(serialize(meta), encoding="utf-8")
                generated.append(str(out_path))
                print(f"  OK  {out_path}")
                continue
            if len(sheets) == 1:
                first_key = next(iter(sheets))
                if (local, first_key) in colliding_expanded:
                    continue
                out_path = next(
                    (o for lo, sh, o in expanded if lo == local and sh == first_key),
                    None,
                )
                if out_path is None:
                    continue
                headers, columns, _dtypes = sheets[first_key]
                rows = len(columns[0]) if columns else 0
                schema = [_build_column(name, values) for name, values in zip(headers, columns)]
                meta = Metadata(
                    file=FileMetadata(
                        path=str(local),
                        format="xlsx",
                        encoding="",
                        delimiter="",
                        rows=rows,
                        columns=len(headers),
                    ),
                    structure=StructureMetadata(schema=schema),
                    generated=GeneratedMetadata(timestamp=_now_iso()),
                )
                meta.documentation = DocumentationMetadata(missing_fields=missing_fields(meta))
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(serialize(meta), encoding="utf-8")
                generated.append(str(out_path))
                print(f"  OK  {out_path}")
            else:
                for sanitized, (headers, columns, _dtypes) in sheets.items():
                    if (local, sanitized) in colliding_expanded:
                        continue
                    out_path = next(
                        (o for lo, sh, o in expanded if lo == local and sh == sanitized),
                        None,
                    )
                    if out_path is None:
                        continue
                    rows = len(columns[0]) if columns else 0
                    schema = [_build_column(name, values) for name, values in zip(headers, columns)]
                    meta = Metadata(
                        file=FileMetadata(
                            path=str(local),
                            format="xlsx",
                            encoding="",
                            delimiter="",
                            rows=rows,
                            columns=len(headers),
                        ),
                        structure=StructureMetadata(schema=schema),
                        generated=GeneratedMetadata(timestamp=_now_iso()),
                    )
                    meta.documentation = DocumentationMetadata(missing_fields=missing_fields(meta))
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(serialize(meta), encoding="utf-8")
                    generated.append(str(out_path))
                    print(f"  OK  {out_path}")

    # ── If collisions exist: raise ValueError after partial write ────
    if colliding_expanded:
        for key in sorted(colliding_keys):
            entries_for_key = collision_map[key]
            rep_out = entries_for_key[0][2]
            try:
                rel_out = rep_out.relative_to(base_dir).as_posix()
            except ValueError:
                rel_out = rep_out.as_posix()
            parts: list[str] = []
            for lo, sh, _o in entries_for_key:
                try:
                    base_rel = lo.relative_to(base_dir).as_posix()
                except ValueError:
                    base_rel = lo.as_posix()
                if sh is not None:
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
            f"share the same path(s). No profile written for colliding outputs."
        )

    return generated


def _read_dataset_for_profile(
    path: Path,
    suffix: str,
    delimiter: str | None = None,
    encoding: str | None = None,
) -> tuple[list[str], list[list[str]], int, str, str]:
    """Read *path* for profile batch, returning columnar data plus meta.

    Args:
        path: Absolute path to the dataset file.
        suffix: Lowercased suffix (already validated against
            :data:`SUPPORTED_FORMATS`).
        delimiter: Explicit CSV delimiter (PRF-07); ``None`` resolves to
            ``config.CSV_DELIMITER``. ``.tsv`` stays tab-delimited.
        encoding: Explicit encoding (PRF-07); ``None`` resolves to
            ``config.CSV_ENCODING``.

    Returns:
        ``(headers, columns, rows, encoding, delimiter)`` with the dialect
        actually used.
    """
    if suffix in _STREAMED_FORMATS:
        used_delimiter = (
            "\t"
            if suffix == ".tsv"
            else (delimiter if delimiter is not None else config.CSV_DELIMITER)
        )
        used_encoding = encoding if encoding is not None else config.CSV_ENCODING
        headers, columns, rows = _stream_columns(path, used_delimiter, used_encoding)
        return headers, columns, rows, used_encoding, used_delimiter
    headers, columns, _dtypes = _read_file(str(path))
    rows = len(columns[0]) if columns else 0
    return headers, columns, rows, "", ""


def _stream_columns(
    path: Path,
    delimiter: str,
    encoding: str | None = None,
) -> tuple[list[str], list[list[str]], int]:
    """Read a CSV/TSV via :func:`stream_csv`, returning columnar data.

    The first ``(header, None)`` yield sets the header and column buckets;
    subsequent ``(header, row)`` yields append each field to its column.
    Rows with more fields than the header are truncated to the header width.

    Args:
        path:      Path to the CSV/TSV file.
        delimiter: Field delimiter (``CSV_DELIMITER`` for CSV, ``\\t`` for TSV).
        encoding:  Initial encoding; ``None`` resolves to
            ``config.CSV_ENCODING`` at call time.

    Returns:
        ``(headers, columns, rows)`` — *columns* is one ``list[str]`` per
        column (column-major, matching ``codebook._read_file``'s shape) and
        *rows* is the number of data rows read (bounded by
        ``PROFILE_MAX_SAMPLE``).
    """
    resolved_encoding = encoding if encoding is not None else config.CSV_ENCODING
    headers: list[str] = []
    columns: list[list[str]] = []
    rows = 0
    for header, row in stream_csv(
        path,
        delimiter=delimiter,
        encoding=resolved_encoding,
        max_sample=config.PROFILE_MAX_SAMPLE,
    ):
        if row is None:
            headers = list(header)
            columns = [[] for _ in headers]
            continue
        rows += 1
        for index, value in enumerate(row):
            if index < len(columns):
                columns[index].append(value)
    return headers, columns, rows


def _build_column(name: str, values: list[str]) -> ColumnMetadata:
    """Assemble one :class:`ColumnMetadata` from a column's values.

    Derives the coarse ``storage_type`` via ``codebook.infer_column_type``,
    the nullability/missing/unique/example stats (reusing the shared
    ``_is_missing`` sentinel check), the semantic type via
    :func:`sofer.semantic.infer_semantic_types` (first match, else ``unknown``),
    and the PII findings via :func:`sofer.pii.infer_pii_types`.

    Args:
        name:   Column name.
        values: The column's sampled values.

    Returns:
        A fully populated :class:`ColumnMetadata` (with an empty human
        ``description`` — surfaced later by :func:`missing_fields`).
    """
    total = len(values)
    missing = sum(1 for value in values if _is_missing(value))
    missing_pct = round(missing / total * 100, 1) if total else 0.0
    example = next((value for value in values if not _is_missing(value)), "")

    detections = infer_semantic_types(values)
    if detections:
        detection = detections[0]
        semantic_type = SemanticType(
            type=detection.type,
            status=detection.status,
            confidence=detection.confidence,
            basis=detection.type,
        )
    else:
        semantic_type = SemanticType()

    return ColumnMetadata(
        name=name,
        storage_type=infer_column_type(values),
        nullable=missing > 0,
        missing_pct=missing_pct,
        unique=count_unique_non_missing(values),
        example=example,
        semantic_type=semantic_type,
        pii=infer_pii_types(values),
    )


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (``generated`` provenance).

    Honors ``SOURCE_DATE_EPOCH`` (reproducible-builds convention): when the
    environment variable holds a POSIX epoch, the timestamp is derived from it,
    so identical inputs produce byte-identical metadata (TC-13 determinism,
    #118). Absent the variable, the current UTC time is used.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if epoch:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()
