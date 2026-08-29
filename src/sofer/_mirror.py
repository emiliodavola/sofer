"""
Shared mirror-layout helpers for the prepare / publish split.

The *mirror layout* is the structure the HF repo expects: every declared
artifact (Parquet, CSV, compliance, codebook) at its remote-relative path
under a single root.  ``prepare`` writes this layout into its output
directory; ``publish`` copies the planned artifacts out of it.

This module is the single home for remote-path validation, planned-remote
derivation, and dir-aware mirror copies — including the ``recursive=true``
staging fix (RC-R04, where ``shutil.copy2`` on a directory raised
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
    """Return the remote paths a publish would deliver for *cfg*.

    Universal: every convertible entry (``.csv/.tsv/.xlsx/.jsonl``) that is not
    ``recursive`` and has ``convert_to_parquet`` (with ``upload_as_csv`` alias
    for csv) maps to its **normalised** ``.parquet`` remote; XLSX with N sheets
    would ideally expand to N remotes — but sheet names are not known without
    opening the file, so we emit the single normalised stem remote here and let
    ``prepare`` record the actual N files via the conversion dispatcher.  For
    the diff/copy contract the single remote is sufficient; multi-sheet
    expansion is handled in the staging step (publish copies whatever Parquets
    exist in the mirror layout under the normalized prefix).

    When ``convert_to_parquet`` is False (or deprecated ``upload_as_csv`` for
    csv) the original remote is kept.  For XLSX the normalised stem remote is
    expanded to N ``stem__sheet.parquet`` entries only when the caller knows
    the sheet count — otherwise the single normalised remote is returned and
    publish's ``_copy_package`` stages all matching files.

    To keep the delegation invariant (PUB-09) without opening workbooks at
    planning time, we emit the **normalised** ``parquet_remote_for`` for every
    convertible entry; XLSX N-expansion is achieved by ``prepare`` staging N
    files and by ``publish._copy_package`` globbing the mirror layout for
    ``stem__*.parquet`` when the entry suffix is ``.xlsx``.

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
