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

import re
import sys
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from . import config
from ._converters import (
    sanitize_sheet_name,  # noqa: F401 — re-exported for parity, used via _read_xlsx_sheets
)
from ._formats import SUPPORTED_FORMATS
from .codebook import _read_xlsx_sheets
from .metadata import Metadata, SemanticType, load
from .model import InferenceStatus
from .pii import PiiDetection

if TYPE_CHECKING:
    from .model import DatasetConfig

# On-disk artifact names shared with the profile writer (profile.py writes the
# same ``metadata.yaml`` this module reads back).
_METADATA_FILENAME = "metadata.yaml"
_README_FILENAME = "README.md"

# Placeholder for an empty table cell (e.g. no PII findings).
_EMPTY_CELL = "—"


def _render_output_for_rel(
    renders_dir: Path,
    rel_stem: Path,
    sheet: str | None,
) -> Path:
    """Compute the render output path for a ``(rel_stem, sheet)`` pair.

    Mirrors ``profile._profile_output_for_rel`` — ``PurePath.suffixes``
    replaces only the last suffix; multisheet inserts ``__<sanitized>``.

    Args:
        renders_dir: Base renders directory (``write_root / RENDER_DIR``).
        rel_stem: Relative stem derived from ``relative_to(data_dir)``.
        sheet: Sanitized sheet name or ``None`` (single-table).

    Returns:
        Absolute output path for the ``README.md``.
    """
    if sheet is None:
        suffixes = PurePath(rel_stem.name).suffixes
        if len(suffixes) > 1:
            target_suffix = "".join(suffixes[:-1]) + ".README.md"
        else:
            target_suffix = ".README.md"
        return (renders_dir / rel_stem).with_suffix(target_suffix)
    base_single = _render_output_for_rel(renders_dir, rel_stem, None)
    base_str = str(base_single)
    base_no_ext = (
        base_str[: -len(".README.md")]
        if base_str.endswith(".README.md")
        else str(base_single.with_suffix(""))
    )
    return Path(base_no_ext + f"__{sheet}.README.md")


def _profile_output_for_rel(
    profiles_dir: Path,
    rel_stem: Path,
    sheet: str | None,
) -> Path:
    """Compute the profile metadata path for a ``(rel_stem, sheet)`` pair.

    Used by render to resolve per-sheet ``metadata.yaml`` locations
    (``profiles/<rel>/<stem>__<sheet>.metadata.yaml``).
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


def _normalize_render_collision_key(path: Path) -> str:
    """Normalize a render path for collision detection (``__+`` -> ``_``)."""
    return re.sub(r"__+", "_", path.as_posix())


def render(
    package_path: Path,
    output_dir: Path | None = None,
    *,
    force: bool = False,
) -> int:
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
        force: When ``False`` and the destination exists, raise
            ``FileExistsError`` with a ``use --force to overwrite`` hint
            (RND-05). When ``True``, overwrite unconditionally.

    Returns:
        ``0`` on success, ``1`` when no ``metadata.yaml`` can be resolved.

    Raises:
        FileExistsError: When the destination exists and *force* is ``False``.
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
    if readme_path.exists() and not force:
        raise FileExistsError(f"use --force to overwrite {readme_path}")
    readme_path.write_text(readme, encoding="utf-8")

    print(f"  OK  Wrote {readme_path}")
    return 0


def generate_all_renders(
    cfg: DatasetConfig,
    output_dir: str | Path | None = None,
) -> list[str]:
    """Generate one ``README.md`` per ``[[file]]`` entry under ``renders/``.

    Each README is written to ``{RENDER_DIR}/<rel-stem>.README.md``,
    where ``<rel-stem>`` mirrors :func:`sofer.profile.generate_all_profiles`.
    For ``.xlsx`` with N>1 sheets N READMEs are emitted as
    ``renders/<rel>/<stem>__<sanitized>.README.md`` using the identical
    ``sanitize_sheet_name`` + ``seen`` dedup ``_{n}`` and
    ``__<sanitized>`` insertion as profile (parity with
    ``codebook``/``prepare`` ``stem__sheet``). Collision map is built from
    sheet-expanded outputs normalized via ``re.sub(r"__+","_",path)``;
    non-colliding READMEs are written first (sourcing each ``metadata.yaml``
    from ``profiles_dir`` mirroring ``write_root``), then ``ValueError``
    naming every colliding source as ``<path>::<sheet>`` is raised.
    Entries whose ``metadata.yaml`` is missing are skipped with a warning.

    Args:
        cfg: A ``DatasetConfig`` loaded from a TOML file.
        output_dir: When given (Option B), READMEs are written under
            ``output_dir/renders/`` and profiles are resolved from
            ``output_dir/profiles/`` (same *write_root*). When ``None``,
            both resolve under ``cache/``.

    Returns:
        List of generated README file paths.

    Raises:
        ValueError: When two or more files resolve to the same output path.
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
    renders_dir = write_root / config.RENDER_DIR

    # ── First pass: collect valid file entries ───────────────────────
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
                out = _render_output_for_rel(renders_dir, rel_stem, None)
                expanded.append((local, None, out))
                xlsx_cache[local] = sheets
                continue
            if len(sheets) == 1:
                first_key = next(iter(sheets))
                out = _render_output_for_rel(renders_dir, rel_stem, None)
                expanded.append((local, first_key, out))
                xlsx_cache[local] = sheets
            else:
                for sanitized in sheets:
                    out = _render_output_for_rel(renders_dir, rel_stem, sanitized)
                    expanded.append((local, sanitized, out))
                xlsx_cache[local] = sheets
        else:
            out = _render_output_for_rel(renders_dir, rel_stem, None)
            expanded.append((local, None, out))

    if not expanded:
        return []

    collision_map: dict[str, list[tuple[Path, str | None, Path]]] = {}
    for local, sheet, out in expanded:
        key = _normalize_render_collision_key(out)
        collision_map.setdefault(key, []).append((local, sheet, out))

    colliding_keys: set[str] = {k for k, v in collision_map.items() if len(v) > 1}
    colliding_expanded: set[tuple[Path, str | None]] = set()
    for key in colliding_keys:
        for local, sheet, _out in collision_map[key]:
            colliding_expanded.add((local, sheet))

    # ── Generate per-(file,sheet) READMEs (non-colliding only) ─────
    generated: list[str] = []

    for local, sheet, out_path in expanded:
        if (local, sheet) in colliding_expanded:
            continue

        if local.is_relative_to(data_dir):
            rel_stem = local.relative_to(data_dir)
        else:
            rel_stem = local.relative_to(base_dir)

        cached = xlsx_cache.get(local)
        meta_sheet = None if cached is not None and len(cached) == 1 else sheet
        metadata_path = _profile_output_for_rel(profiles_dir, rel_stem, meta_sheet)

        if not metadata_path.is_file():
            print(
                f"  \u26a0  Skipping missing metadata.yaml for {local}: {metadata_path}",
                file=sys.stderr,
            )
            continue

        try:
            meta = load(metadata_path)
        except Exception as exc:
            print(f"  \u2717  Error reading {metadata_path}: {exc}", file=sys.stderr)
            continue

        readme = _render_readme(meta)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(readme, encoding="utf-8")
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
            f"share the same path(s). No README written for colliding outputs."
        )

    return generated


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
