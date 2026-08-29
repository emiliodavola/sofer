"""
Shared mirror-layout helpers for the prepare / publish split.

The *mirror layout* is the structure the HF repo expects: every declared
artifact (Parquet, CSV, compliance, codebook) at its remote-relative path
under a single root.  ``prepare`` writes this layout into its output
directory; ``publish`` copies the planned artifacts out of it.

This module is the single home for remote-path validation, planned-remote
derivation (logical :func:`planned_remotes` and ground-truth
:func:`expanded_planned_remotes` for multi-sheet XLSX, PUB-10), and
dir-aware mirror copies — including the ``recursive=true`` staging fix
(RC-R04, where ``shutil.copy2`` on a directory raised
PermissionError/IsADirectoryError).
"""

from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import DatasetConfig


def _validate_remote_paths(cfg: DatasetConfig) -> list[str]:
    """Validate that every ``FileEntry.remote`` is a file path, not a directory.

    A remote path ending with ``/`` (or ``\\``) that is not declared as
    ``recursive`` is considered invalid.

    Args:
        cfg: Dataset configuration whose ``files`` are being validated.

    Returns:
        A list of error messages (empty = all paths are valid).
    """
    errors: list[str] = []
    for i, entry in enumerate(cfg.files):
        stripped = entry.remote.rstrip("/").rstrip("\\")
        # Directory path detected — trailing slash removed something
        if stripped != entry.remote and not entry.recursive:
            errors.append(
                f"File entry {i + 1}: remote='{entry.remote}' looks like a "
                f"directory path (trailing slash). Set recursive=true if this "
                f"is a directory, or provide a valid file path."
            )
        # Empty path after stripping
        if not stripped:
            errors.append(f"File entry {i + 1}: remote='{entry.remote}' is not a valid file path.")
    return errors


def parquet_remote_for(remote: str) -> str:
    """Return the staged-Parquet remote key for *remote*.

    The single definition of the remote → ``.parquet`` key derivation shared
    by every producer (prepare staging) and consumer (publish, schema-report
    lookup) of staged-Parquet paths.  Pure, total, and idempotent:
    backslash separators are normalized to forward slashes first (RC-R15)
    so a TOML remote like ``data\\a\\train.csv`` yields the same key on both
    handshake sides; the suffix is then replaced with ``.parquet``.
    Case is preserved — callers gate eligibility via ``.lower()`` themselves.

    Args:
        remote: Verbatim ``FileEntry.remote`` path (e.g. ``data/PROV/train.csv``).

    Returns:
        The POSIX-normalized remote with its suffix replaced by ``.parquet``
        (e.g. ``data/PROV/train.parquet``).
    """
    posix_remote = remote.replace("\\", "/")
    return str(PurePosixPath(posix_remote).with_suffix(".parquet"))


def _is_convertible_entry(entry) -> bool:
    """Return True when *entry* is convertible (universal set, normalized)."""
    # Import here to avoid cycle — _converters never imports _mirror
    from ._converters import CONVERTIBLE_SUFFIXES

    if entry.recursive:
        return False
    return PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower() in CONVERTIBLE_SUFFIXES


def _normalized_parquet_key(remote: str) -> str:
    """Return the normalised Parquet key for *remote* (suffix → .parquet, then normalize)."""
    from ._converters import normalize_parquet_remote

    return normalize_parquet_remote(parquet_remote_for(remote)).lower()


def _validate_case_fold_collisions(cfg: DatasetConfig) -> list[str]:
    """Detect convertible remotes that differ only by case/normalization but share a Parquet key.

    Universal: every ``.csv/.tsv/.xlsx/.jsonl`` entry that is not ``recursive``
    is scanned.  Normalisation via :func:`sofer._converters.normalize_parquet_remote`
    is applied before case-folding so that accent/space variants are also caught.
    ``convert_to_parquet`` / ``include_in_schema`` do NOT exclude an entry.

    Verbatim-equal normalised keys are left to RC-R11's warning and skipped here.

    Args:
        cfg: Dataset configuration whose ``files`` are being validated.

    Returns:
        A list of error messages (empty = no case-fold collisions).
    """
    errors: list[str] = []
    seen: dict[str, str] = {}
    for entry in cfg.files:
        if not _is_convertible_entry(entry):
            continue
        key = _normalized_parquet_key(entry.remote)
        current = entry.remote
        first = seen.get(key)
        if first is not None and first != current:
            errors.append(
                f"Case-fold collision: remotes '{first}' and '{current}' differ "
                f"only by case and would map to the same staged Parquet file; "
                f"rename one of them."
            )
        else:
            seen[key] = current
    return errors


def planned_remotes(cfg: DatasetConfig, keep_csv: bool) -> list[str]:
    """Return the *logical* remote paths a publish would deliver for *cfg*.

    Logical placeholder: every convertible entry (``.csv/.tsv/.xlsx/.jsonl``)
    that is not ``recursive`` and has ``convert_to_parquet`` maps to its
    **normalised** ``.parquet`` remote.  For ``.xlsx`` this is the single
    stem placeholder (``stem.parquet``) — sheet names are not known without
    opening the workbook, so the ground-truth N remotes (``stem__sheet.parquet``)
    are resolved only by :func:`expanded_planned_remotes` when the staging
    mirror is available.  The single placeholder keeps dry-run before prepare
    useful and avoids workbook I/O at plan time.

    To obtain the ground truth when the mirror exists, call
    :func:`expanded_planned_remotes` instead — it globs
    ``staging_dir/<dir>/<stem>__*.parquet`` for eligible ``.xlsx`` and falls
    back to this logical list when the mirror is absent (PUB-10).

    Args:
        cfg: Dataset configuration.
        keep_csv: When ``True`` and a CSV was converted to Parquet, also
            include the original CSV remote (CSV-only).

    Returns:
        List of remote paths, in ``cfg.files`` declaration order.
    """
    from ._converters import CONVERTIBLE_SUFFIXES, normalize_parquet_remote

    planned: list[str] = []
    for entry in cfg.files:
        if entry.recursive:
            planned.append(entry.remote.rstrip("/\\"))
            continue
        suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()
        is_convertible = suffix in CONVERTIBLE_SUFFIXES
        # Eligibility: convertible suffix + convert_to_parquet (upload_as_csv for csv)
        eligible = False
        if is_convertible:
            if suffix == ".csv":
                eligible = bool(entry.convert_to_parquet)
            else:
                eligible = bool(entry.convert_to_parquet)
        if eligible:
            normalized = normalize_parquet_remote(parquet_remote_for(entry.remote))
            planned.append(normalized)
            if keep_csv and suffix == ".csv":
                planned.append(entry.remote)
        else:
            planned.append(entry.remote)
    return planned


def expanded_planned_remotes(
    cfg: DatasetConfig, keep_csv: bool, staging_dir: Path | None
) -> list[str]:
    """Return the ground-truth remotes for *cfg*, expanding multi-sheet XLSX via mirror glob.

    For convertible ``.xlsx`` entries that are not ``recursive`` and have
    ``convert_to_parquet`` true, the helper inspects the staging mirror
    instead of opening workbooks (PUB-10):

    - When *staging_dir* is ``None`` or not a directory, it delegates to
      :func:`planned_remotes` (logical single placeholder).
    - When the mirror exists, it globs ``staging_dir/<dir>/<stem>__*.parquet``
      (sorted) where ``<dir>/<stem>`` is the normalized placeholder
      (``normalize_parquet_remote(parquet_remote_for(remote))``).  If the glob
      matches, each match is emitted as its mirror-relative POSIX path
      (already normalized on disk); otherwise the single normalized placeholder
      is emitted (single-sheet, no phantom ``__``).
    - All other entries follow :func:`planned_remotes` exactly, including the
      ``keep_csv`` CSV-only rule and the ``recursive`` passthrough.

    The glob is sorted so declaration order plus per-XLSX alphabetical sheet
    order is deterministic.  No workbook I/O is performed — dedup and
    normalization are already reflected in the staged filenames.  The helper
    reuses :func:`sofer._converters.normalize_parquet_remote` for the fallback
    placeholder and :func:`sofer._converters.sanitize_sheet_name` rationale
    (sheet names are already sanitized on disk).

    Args:
        cfg: Dataset configuration whose ``files`` are examined.
        keep_csv: When ``True`` and a CSV was converted, also include the
            original CSV remote (CSV-only, never for XLSX).
        staging_dir: Mirror layout root (e.g. ``prepare`` output directory).
            ``None`` or not a directory triggers the logical fallback.

    Returns:
        List of remote paths, in ``cfg.files`` declaration order, with each
        eligible XLSX expanded to N ``__`` remotes when the mirror contains
        them.
    """
    if staging_dir is None or not Path(staging_dir).is_dir():
        return planned_remotes(cfg, keep_csv)

    from ._converters import CONVERTIBLE_SUFFIXES, normalize_parquet_remote

    expanded: list[str] = []
    for entry in cfg.files:
        if entry.recursive:
            expanded.append(entry.remote.rstrip("/\\"))
            continue
        suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()
        is_convertible = suffix in CONVERTIBLE_SUFFIXES
        eligible = is_convertible and bool(entry.convert_to_parquet)
        if eligible and suffix == ".xlsx":
            placeholder = normalize_parquet_remote(parquet_remote_for(entry.remote))
            parent = PurePosixPath(placeholder).parent
            stem = PurePosixPath(placeholder).stem
            search_dir = Path(staging_dir) / parent if str(parent) != "." else Path(staging_dir)
            candidates: list[Path] = []
            if search_dir.is_dir():
                # Primary: double-underscore sheet files (spec)
                candidates = sorted(search_dir.glob(f"{stem}__*.parquet"))
                candidates = [c for c in candidates if c.is_file()]
                # Fallback for current single-underscore staging (backward compat)
                # when prepare stored sheets as report_ventas.parquet (collapsed).
                if not candidates:
                    alt = sorted(search_dir.glob(f"{stem}_*.parquet"))
                    # Filter to keep only those that look like sheet files
                    # (exclude the placeholder itself).  For single-underscore
                    # layout, sheet files are report_ventas.parquet vs
                    # placeholder report.parquet — they differ by suffix.
                    alt = [c for c in alt if c.is_file() and c.stem != stem]
                    if alt:
                        candidates = alt
            if candidates:
                for cand in candidates:
                    rel = cand.relative_to(Path(staging_dir)).as_posix()
                    expanded.append(rel)
                continue
            # No sheets found — single-sheet fallback
            expanded.append(placeholder)
            continue
        if eligible:
            normalized = normalize_parquet_remote(parquet_remote_for(entry.remote))
            expanded.append(normalized)
            if keep_csv and suffix == ".csv":
                expanded.append(entry.remote)
        else:
            expanded.append(entry.remote)
    return expanded


def copy_to_mirror(src: Path, dest_root: Path, remote: str) -> None:
    """Copy a file or directory tree into the mirror layout under *dest_root*.

    Directories are copied recursively with :func:`shutil.copytree`
    (``dirs_exist_ok=True``); plain files use :func:`shutil.copy2`.  Never
    calls ``copy2`` on a directory (RC-R04: staging a ``recursive=true``
    entry previously crashed with PermissionError / IsADirectoryError).

    Args:
        src:       Source file or directory.
        dest_root: Root of the mirror layout (e.g. the staging directory).
        remote:    Remote-relative destination path (POSIX separators;
                   a trailing slash on a directory is harmless).
    """
    if src.is_dir():
        shutil.copytree(src, dest_root / remote, dirs_exist_ok=True)
    else:
        dest = dest_root / remote
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
