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
from typing import TYPE_CHECKING

from . import config
from ._csv_reader import stream_csv
from ._formats import SUPPORTED_FORMATS
from ._sentinels import count_unique_non_missing
from .codebook import _read_file, infer_column_type
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


def profile(
    dataset_path: Path,
    output_dir: Path | None = None,
    *,
    force: bool = False,
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
        delimiter = "\t" if suffix == ".tsv" else config.CSV_DELIMITER
        headers, columns, rows = _stream_columns(dataset_path, delimiter)
        encoding = config.CSV_ENCODING
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
) -> list[str]:
    """Generate one ``metadata.yaml`` per ``[[file]]`` entry under ``profiles/``.

    Each profile is written to ``{PROFILE_DIR}/<rel-stem>.metadata.yaml``,
    where ``<rel-stem>`` is the file's path relative to the ``cache/``
    directory (falling back to the TOML config directory for files outside
    ``cache/``). When two or more entries resolve to the same output path the
    system writes profiles for all non-colliding files first, then raises
    ``ValueError`` naming every colliding source — no profile is written for
    any colliding file.

    Args:
        cfg: A ``DatasetConfig`` loaded from a TOML file.
        output_dir: When given (Option B), profiles are written under
            ``output_dir/profiles/`` and the shared ``cache/profiles/``
            directory is never mutated. When ``None`` (default), profiles go
            to ``cache/profiles/``.

    Returns:
        List of generated profile file paths.

    Raises:
        ValueError: When two or more files resolve to the same output path
            (after non-colliding profiles have already been written).
    """
    from pathlib import PurePath

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

    # ── Pre-compute output paths and detect collisions ───────────────
    output_paths: dict[Path, Path] = {}
    collision_sources: dict[Path, list[Path]] = {}

    for local, _suffix in entries:
        if local.is_relative_to(data_dir):
            rel_stem = local.relative_to(data_dir)
        else:
            rel_stem = local.relative_to(base_dir)

        suffixes = PurePath(rel_stem.name).suffixes
        if len(suffixes) > 1:
            target_suffix = "".join(suffixes[:-1]) + ".metadata.yaml"
        else:
            target_suffix = ".metadata.yaml"
        out_path = (profiles_dir / rel_stem).with_suffix(target_suffix)

        output_paths[local] = out_path
        if out_path not in collision_sources:
            collision_sources[out_path] = []
        collision_sources[out_path].append(local)

    # ── Partition: non-colliding vs colliding ────────────────────────
    colliding_locals: set[Path] = set()
    for out_path, sources in collision_sources.items():
        if len(sources) > 1:
            colliding_locals.update(sources)

    # ── Generate per-file profiles (non-colliding only) ─────────────
    generated: list[str] = []

    for local, suffix in entries:
        if local in colliding_locals:
            continue

        try:
            headers, columns, rows, encoding, delimiter = _read_dataset_for_profile(local, suffix)
        except Exception as exc:
            print(f"  \u2717  Error reading {local}: {exc}", file=sys.stderr)
            continue

        schema = [_build_column(name, values) for name, values in zip(headers, columns)]
        meta = Metadata(
            file=FileMetadata(
                path=str(local),
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

        output_path = output_paths[local]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialize(meta), encoding="utf-8")
        generated.append(str(output_path))
        print(f"  OK  {output_path}")

    # ── If collisions exist: raise ValueError after partial write ────
    if colliding_locals:
        for out_path, sources in collision_sources.items():
            if len(sources) > 1:
                rel_out = (
                    out_path.relative_to(write_root).as_posix()
                    if out_path.is_relative_to(write_root)
                    else str(out_path)
                )
                try:
                    rel_out_disp = out_path.relative_to(base_dir).as_posix()
                except ValueError:
                    rel_out_disp = rel_out
                source_list = ", ".join(
                    s.relative_to(base_dir).as_posix() if s.is_relative_to(base_dir) else str(s)
                    for s in sources
                )
                print(
                    f"  X  Collision: {rel_out_disp} is target for: {source_list}",
                    file=sys.stderr,
                )
        raise ValueError(
            f"Collision detected: {len(colliding_locals)} file(s) "
            f"share the same output path(s). No profile written "
            f"for colliding files."
        )

    return generated


def _read_dataset_for_profile(
    path: Path, suffix: str
) -> tuple[list[str], list[list[str]], int, str, str]:
    """Read *path* for profile batch, returning columnar data plus meta.

    Args:
        path: Absolute path to the dataset file.
        suffix: Lowercased suffix (already validated against
            :data:`SUPPORTED_FORMATS`).

    Returns:
        ``(headers, columns, rows, encoding, delimiter)``.
    """
    if suffix in _STREAMED_FORMATS:
        delimiter = "\t" if suffix == ".tsv" else config.CSV_DELIMITER
        headers, columns, rows = _stream_columns(path, delimiter)
        encoding = config.CSV_ENCODING
        return headers, columns, rows, encoding, delimiter
    headers, columns, _dtypes = _read_file(str(path))
    rows = len(columns[0]) if columns else 0
    return headers, columns, rows, "", ""


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
        encoding=config.CSV_ENCODING,
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
    """Return the current UTC time as an ISO-8601 string (``generated`` provenance)."""
    return datetime.now(timezone.utc).isoformat()
