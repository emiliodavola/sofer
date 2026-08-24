"""Render a status-annotated ``README.md`` from a ``metadata.yaml`` document.

The ``render`` command is the read half of sofer v2's documentation pipeline:
it loads a ``metadata.yaml`` document and projects it into a human-readable
``README.md``. Rendering is a pure projection — ``metadata.yaml`` remains the
source of truth, nothing is recomputed, and neither the metadata document nor
any dataset file is modified (RND-01/RND-02).

Inference states are rendered distinctly (RND-03) so a reader can tell a fact
from a guess:

- ``confirmed`` → the plain type label (``email``);
- ``inferred`` → ``email (inferred, 78%)`` with the confidence as a whole
  percentage via round-half-to-even;
- ``unknown`` → the literal ``unknown`` — never blank, never fabricated.

Unknown human-input fields (description, license, source) are rendered as
``unknown`` for the same reason.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .metadata import Metadata, SemanticType, load
from .model import InferenceStatus
from .pii import PiiDetection

# On-disk artifact names shared with the profile writer (profile.py writes the
# same ``metadata.yaml`` this module reads back).
_METADATA_FILENAME = "metadata.yaml"
_README_FILENAME = "README.md"

# Placeholder for an empty table cell (e.g. no PII findings).
_EMPTY_CELL = "—"


def render(package_path: Path, output_dir: Path | None = None) -> int:
    """Render ``README.md`` from a ``metadata.yaml`` document and return an exit code.

    Orchestration (spec RND-01/RND-02):

    1. Resolve ``metadata.yaml`` from *package_path* — either the file itself
       or a directory containing it (RND-01).
    2. Load the document via :func:`sofer.metadata.load`.
    3. Project it into ``README.md`` markdown via :func:`_render_readme`.
    4. Write ``README.md`` next to ``metadata.yaml`` (or into *output_dir*).

    Rendering never recomputes inference and never modifies ``metadata.yaml``.

    Args:
        package_path: Path to ``metadata.yaml``, or the directory containing it.
        output_dir:  Directory for ``README.md`` (default: the metadata.yaml
            directory).

    Returns:
        ``0`` on success, ``1`` when no ``metadata.yaml`` can be resolved.
    """
    package_path = Path(package_path)
    metadata_path = _resolve_metadata_path(package_path)
    if metadata_path is None:
        print(f"Error: No metadata.yaml found at: {package_path}", file=sys.stderr)
        return 1

    readme = _render_readme(load(metadata_path))

    out_dir = Path(output_dir) if output_dir is not None else metadata_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    readme_path = out_dir / _README_FILENAME
    readme_path.write_text(readme, encoding="utf-8")

    print(f"  OK  Wrote {readme_path}")
    return 0


def _resolve_metadata_path(package_path: Path) -> Path | None:
    """Resolve *package_path* to a concrete ``metadata.yaml`` file (RND-01).

    A direct file path is used as-is; a directory is searched for a
    ``metadata.yaml`` inside it. Returns ``None`` when neither yields a file.
    """
    if package_path.is_file():
        return package_path
    candidate = package_path / _METADATA_FILENAME
    if candidate.is_file():
        return candidate
    return None


def _render_readme(meta: Metadata) -> str:
    """Project a :class:`Metadata` document into full ``README.md`` markdown.

    Pure function: same document → same string. The title falls back to the
    file path when the dataset name is empty (as it is right after ``profile``),
    and unknown human fields are rendered as ``unknown`` rather than left blank.

    Args:
        meta: The :class:`Metadata` document to project.

    Returns:
        The complete ``README.md`` markdown string.
    """
    title = meta.dataset.name or meta.file.path or "Dataset"
    description = meta.dataset.description or "unknown"
    license_ = meta.dataset.license or "unknown"
    source = meta.dataset.source or "unknown"

    schema_rows = [
        (
            f"| {col.name} | {col.storage_type} | "
            f"{_render_semantic(col.semantic_type)} | {_render_pii(col.pii)} |"
        )
        for col in meta.structure.schema
    ]

    lines = [
        f"# {title}",
        "",
        description,
        "",
        "## Overview",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| File | {meta.file.path or 'unknown'} |",
        f"| Format | {meta.file.format or 'unknown'} |",
        f"| Rows | {meta.file.rows} |",
        f"| Columns | {meta.file.columns} |",
        f"| License | {license_} |",
        f"| Source | {source} |",
        "",
        "## Schema",
        "",
        "| Column | Storage type | Semantic type | PII |",
        "|--------|--------------|---------------|-----|",
        *schema_rows,
        "",
        "## Missing fields (human input)",
        "",
    ]
    missing = meta.documentation.missing_fields
    if missing:
        lines.extend(f"- {field}" for field in missing)
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def _render_semantic(sem: SemanticType) -> str:
    """Render a semantic type according to its inference status (RND-03).

    ``confirmed`` renders the plain label, ``inferred`` appends the confidence
    percentage (``email (inferred, 78%)``), and ``unknown`` renders the literal
    ``unknown``. A fabricated type is never emitted.
    """
    if sem.status is InferenceStatus.UNKNOWN:
        return "unknown"
    label = sem.type if sem.type is not None else "unknown"
    if sem.status is InferenceStatus.INFERRED:
        pct = _percent(sem.confidence) if sem.confidence is not None else 0
        return f"{label} (inferred, {pct}%)"
    return label


def _percent(confidence: float) -> int:
    """Round a confidence (0.0-1.0) to a whole percentage.

    Uses Python's built-in ``round`` — nearest integer, round-half-to-even —
    so the value is rounded, never truncated (RND-03).
    """
    return round(confidence * 100)


def _render_pii(findings: list[PiiDetection]) -> str:
    """Render PII findings as ``label (note)`` entries, or an empty cell.

    A column with no findings renders :data:`_EMPTY_CELL` rather than an
    ambiguous blank cell.
    """
    if not findings:
        return _EMPTY_CELL
    return ", ".join(f"{d.label} ({d.note})" for d in findings)
