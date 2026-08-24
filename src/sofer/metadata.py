"""Deterministic ``metadata.yaml`` schema and (de)serialization.

``metadata.yaml`` is the machine-readable source of truth for dataset
documentation in sofer v2. This module defines the schema dataclasses
(:class:`Metadata` and its sections), the :data:`METADATA_VERSION` constant,
and three functions — :func:`serialize`, :func:`load`, and
:func:`missing_fields` — that map between the in-memory dataclasses and
deterministic, round-trippable YAML (spec MTA-01..MTA-06).

Serialization is deterministic: keys are sorted (``sort_keys=True``) and no set
iteration is used, so equal documents always produce byte-identical output
(MTA-03). Enum values are converted to their string form before dumping and
converted back on load, so the round-trip is lossless.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .model import InferenceStatus
from .pii import PiiDetection

# Metadata schema version, emitted as ``metadata_version`` in every document.
# A module constant (never an inline literal — AGENTS.md rule 1), so a future
# schema bump is a single edit and MTA-02 can assert equality against it.
METADATA_VERSION: str = "1"


@dataclass
class DatasetMetadata:
    """Human-authored dataset-level documentation (the ``dataset`` section).

    Attributes:
        name:        Short human-readable dataset name.
        description: Free-text description (empty = missing human input).
        license:     SPDX identifier or ``"restricted"`` (empty = missing).
        source:      Origin institution or organisation (empty = missing).
    """

    name: str = ""
    description: str = ""
    license: str = ""
    source: str = ""


@dataclass
class FileMetadata:
    """Machine-detected properties of the profiled file (the ``file`` section).

    Attributes:
        path:      Dataset file path (as given to ``profile``).
        format:    Detected format (e.g. ``csv``, ``parquet``).
        encoding:  File encoding when known.
        delimiter: Field delimiter when the format has one.
        rows:      Number of data rows read.
        columns:   Number of columns detected.
    """

    path: str = ""
    format: str = ""
    encoding: str = ""
    delimiter: str = ""
    rows: int = 0
    columns: int = 0


@dataclass
class SemanticType:
    """The new semantic inference result for a column (``semantic_type``).

    When no detector matched, ``status`` is ``unknown`` and ``type``,
    ``confidence``, and ``basis`` are ``None`` (spec MTA-06) — a fabricated
    type is never emitted.

    Attributes:
        type:       Detected semantic type (e.g. ``"email"``), or ``None``.
        status:     One of ``confirmed`` / ``inferred`` / ``unknown``.
        confidence: Rounded confidence float, or ``None`` when unknown.
        basis:      Detector name that produced the result (e.g. ``"email"``).
    """

    type: str | None = None
    status: InferenceStatus = InferenceStatus.UNKNOWN
    confidence: float | None = None
    basis: str | None = None


@dataclass
class ColumnMetadata:
    """One entry of ``structure.schema[]`` (spec MTA-06).

    ``storage_type`` is the coarse pre-existing vocabulary (``numeric`` /
    ``categorical/text`` / ``mixed (mostly numeric)`` / ``unknown``) and is
    deliberately NOT merged with ``semantic_type`` — they answer different
    questions ("how is it stored" vs "what does it mean").

    Attributes:
        name:          Column name.
        storage_type:  Coarse storage type from ``codebook.infer_column_type``.
        nullable:      Whether the column contains missing values.
        missing_pct:   Percentage of missing values (0.0-100.0).
        unique:        Number of distinct values observed.
        example:       A representative sample value.
        description:   Human-authored column description (empty = missing input).
        semantic_type: Semantic inference result (:class:`SemanticType`).
        pii:           PII findings — a list of ``{label, confidence, note}``.
    """

    name: str
    storage_type: str
    nullable: bool = True
    missing_pct: float = 0.0
    unique: int = 0
    example: str = ""
    description: str = ""
    semantic_type: SemanticType = field(default_factory=SemanticType)
    pii: list[PiiDetection] = field(default_factory=list)


@dataclass
class StructureMetadata:
    """The detected schema (the ``structure`` section).

    Attributes:
        schema: One :class:`ColumnMetadata` per dataset column, in file order.
    """

    schema: list[ColumnMetadata] = field(default_factory=list)


@dataclass
class QualityMetadata:
    """Summary of quality-check results (the ``quality`` section).

    Attributes:
        total_checks: Number of quality checks run.
        passed:       Checks that passed.
        warnings:     Checks that produced warnings.
        failures:     Checks that failed.
    """

    total_checks: int = 0
    passed: int = 0
    warnings: int = 0
    failures: int = 0


@dataclass
class DocumentationMetadata:
    """Human-input gaps (the ``documentation`` section).

    Attributes:
        missing_fields: Names of human-input fields that are still empty, e.g.
            ``description``, ``license``, ``source``, or ``<column>.description``.
    """

    missing_fields: list[str] = field(default_factory=list)


@dataclass
class GeneratedMetadata:
    """Provenance of the metadata document (the ``generated`` section).

    Attributes:
        tool:      Producer identifier — always ``"sofer"``.
        version:   The sofer ``__version__`` that generated the document.
        timestamp: ISO-8601 generation timestamp (populated by ``profile``).
    """

    tool: str = "sofer"
    version: str = __version__
    timestamp: str = ""


@dataclass
class Metadata:
    """Top-level metadata document — ``metadata.yaml`` (spec MTA-01).

    Attributes:
        metadata_version: Schema version, sourced from :data:`METADATA_VERSION`.
        dataset:          Human-authored dataset documentation.
        file:             Machine-detected file properties.
        structure:        Detected schema (``schema[]``).
        quality:          Quality-check summary.
        documentation:    Human-input gaps (``missing_fields``).
        generated:        Provenance of this document.
    """

    metadata_version: str = METADATA_VERSION
    dataset: DatasetMetadata = field(default_factory=DatasetMetadata)
    file: FileMetadata = field(default_factory=FileMetadata)
    structure: StructureMetadata = field(default_factory=StructureMetadata)
    quality: QualityMetadata = field(default_factory=QualityMetadata)
    documentation: DocumentationMetadata = field(default_factory=DocumentationMetadata)
    generated: GeneratedMetadata = field(default_factory=GeneratedMetadata)


def _plain(value: Any) -> Any:
    """Recursively convert a value to plain, YAML-serializable Python data.

    Dataclasses become dicts (keyed by field name, in declaration order), enum
    members become their string ``.value`` (e.g. ``InferenceStatus.INFERRED`` →
    ``"inferred"``), and dicts/lists recurse. Plain scalars pass through.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def serialize(meta: Metadata) -> str:
    """Return deterministic YAML for ``meta`` (spec MTA-03).

    Keys are sorted (``sort_keys=True``) and no set iteration is used, so the
    same document always serializes to byte-identical YAML. Enum values are
    emitted as their string form, and ``metadata_version`` is sourced from
    :data:`METADATA_VERSION`.

    Args:
        meta: The :class:`Metadata` document to serialize.

    Returns:
        The YAML string (UTF-8 encodable, deterministic ordering).
    """
    return yaml.safe_dump(_plain(meta), sort_keys=True, allow_unicode=True)


def load(path: str | Path) -> Metadata:
    """Load a ``metadata.yaml`` file back into a :class:`Metadata` document.

    Reverses :func:`serialize`: string enum values are converted back to
    :class:`InferenceStatus`, and nested mappings back to their dataclasses, so
    ``load(serialize(meta)) == meta`` (lossless round-trip, MTA-03).

    Args:
        path: Path to the ``metadata.yaml`` file.

    Returns:
        The reconstructed :class:`Metadata` document.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return _from_dict(raw)


def missing_fields(meta: Metadata) -> list[str]:
    """Return the human-input fields that are still empty (PRF-04).

    A metadata document is generated from the dataset alone, so the fields a
    human must supply — the dataset ``description``, ``license``, and ``source``,
    plus each column's ``description`` — start empty and are surfaced here as a
    flat list of gaps (e.g. ``["description", "license", "source",
    "user_email.description"]``).

    Args:
        meta: The :class:`Metadata` document to inspect.

    Returns:
        List of missing human-input field names (empty = complete).
    """
    gaps: list[str] = []
    if not meta.dataset.description:
        gaps.append("description")
    if not meta.dataset.license:
        gaps.append("license")
    if not meta.dataset.source:
        gaps.append("source")
    for column in meta.structure.schema:
        if not column.description:
            gaps.append(f"{column.name}.description")
    return gaps


def _from_dict(raw: dict[str, Any]) -> Metadata:
    """Reconstruct a :class:`Metadata` document from plain YAML data."""
    dataset = DatasetMetadata(**raw.get("dataset", {}))
    file = FileMetadata(**raw.get("file", {}))
    quality = QualityMetadata(**raw.get("quality", {}))
    documentation = DocumentationMetadata(
        missing_fields=list(raw.get("documentation", {}).get("missing_fields", []))
    )
    generated = GeneratedMetadata(**raw.get("generated", {}))
    structure = StructureMetadata(
        schema=[_column_from_dict(c) for c in raw.get("structure", {}).get("schema", [])]
    )
    return Metadata(
        metadata_version=raw.get("metadata_version", METADATA_VERSION),
        dataset=dataset,
        file=file,
        structure=structure,
        quality=quality,
        documentation=documentation,
        generated=generated,
    )


def _column_from_dict(raw: dict[str, Any]) -> ColumnMetadata:
    """Reconstruct one :class:`ColumnMetadata` from plain YAML data."""
    sem = raw.get("semantic_type") or {}
    semantic_type = SemanticType(
        type=sem.get("type"),
        status=InferenceStatus(sem.get("status", InferenceStatus.UNKNOWN.value)),
        confidence=sem.get("confidence"),
        basis=sem.get("basis"),
    )
    return ColumnMetadata(
        name=raw["name"],
        storage_type=raw["storage_type"],
        nullable=raw.get("nullable", True),
        missing_pct=raw.get("missing_pct", 0.0),
        unique=raw.get("unique", 0),
        example=raw.get("example", ""),
        description=raw.get("description", ""),
        semantic_type=semantic_type,
        pii=[PiiDetection(**p) for p in raw.get("pii", [])],
    )
