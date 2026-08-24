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

import sys
from datetime import datetime, timezone
from pathlib import Path

from ._csv_reader import stream_csv
from ._formats import SUPPORTED_FORMATS
from ._sentinels import count_unique_non_missing
from .codebook import _read_file, infer_column_type
from .config import CSV_DELIMITER, CSV_ENCODING, PROFILE_MAX_SAMPLE
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

# Formats read through the bounded streaming CSV reader. TSV uses a tab
# delimiter; CSV uses the configured delimiter (CSV_DELIMITER).
_STREAMED_FORMATS = frozenset({".csv", ".tsv"})

_METADATA_FILENAME = "metadata.yaml"


def profile(dataset_path: Path, output_dir: Path | None = None) -> int:
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

    Returns:
        ``0`` on success, ``1`` when the format is unsupported or the file
        does not exist.
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
        delimiter = "\t" if suffix == ".tsv" else CSV_DELIMITER
        headers, columns, rows = _stream_columns(dataset_path, delimiter)
        encoding = CSV_ENCODING
    else:
        headers, columns, _dtypes = _read_file(str(dataset_path))
        rows = len(columns[0]) if columns else 0
        encoding = ""
        delimiter = ""

    schema = [_build_column(name, values) for name, values in zip(headers, columns)]

    meta = Metadata(
        file=FileMetadata(
            path=str(dataset_path),
            format=suffix.lstrip("."),
            encoding=encoding,
            delimiter=delimiter,
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
    metadata_path.write_text(serialize(meta), encoding="utf-8")

    print(f"  OK  Wrote {metadata_path}")
    gaps = meta.documentation.missing_fields
    if gaps:
        print(f"  Missing fields (human input): {', '.join(gaps)}")
    return 0


def _stream_columns(
    path: Path,
    delimiter: str,
) -> tuple[list[str], list[list[str]], int]:
    """Read a CSV/TSV via :func:`stream_csv`, returning columnar data.

    The first ``(header, None)`` yield sets the header and column buckets;
    subsequent ``(header, row)`` yields append each field to its column.
    Rows with more fields than the header are truncated to the header width.

    Args:
        path:      Path to the CSV/TSV file.
        delimiter: Field delimiter (``CSV_DELIMITER`` for CSV, ``\\t`` for TSV).

    Returns:
        ``(headers, columns, rows)`` — *columns* is one ``list[str]`` per
        column (column-major, matching ``codebook._read_file``'s shape) and
        *rows* is the number of data rows read (bounded by
        ``PROFILE_MAX_SAMPLE``).
    """
    headers: list[str] = []
    columns: list[list[str]] = []
    rows = 0
    for header, row in stream_csv(
        path,
        delimiter=delimiter,
        encoding=CSV_ENCODING,
        max_sample=PROFILE_MAX_SAMPLE,
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
    """Return the current UTC time as an ISO-8601 string (``generated`` provenance)."""
    return datetime.now(timezone.utc).isoformat()
