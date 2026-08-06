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


def planned_remotes(cfg: DatasetConfig, keep_csv: bool) -> list[str]:
    """Return the remote paths a publish would deliver for *cfg*.

    Derived from the data-file planning logic of ``publish._repo_diff_summary``
    (and the equivalent list in :func:`sofer.publish.publish`):

    - recursive directory entries resolve to their path with the trailing
      slash stripped — a copyable path, unlike the ``*`` marker used in the
      human-readable diff;
    - CSV entries eligible for conversion map to their ``.parquet`` remote
      (plus the original CSV remote when *keep_csv* is ``True``);
    - every other entry is its own remote path.

    Compliance files (README.md / LICENSE) and codebooks are NOT included —
    callers stage those separately.

    Args:
        cfg: Dataset configuration.
        keep_csv: When ``True`` and a CSV was converted to Parquet, also
            include the original CSV remote.

    Returns:
        List of remote paths, in ``cfg.files`` declaration order.
    """
    planned: list[str] = []
    for entry in cfg.files:
        if entry.recursive:
            planned.append(entry.remote.rstrip("/\\"))
        elif entry.remote.lower().endswith(".csv") and not entry.upload_as_csv:
            planned.append(str(PurePosixPath(entry.remote).with_suffix(".parquet")))
            if keep_csv:
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
