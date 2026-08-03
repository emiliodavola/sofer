"""
File discovery and TOML registration for the ``scan`` command.

Four-phase orchestrator: discover → merge → copy → write.

All functions are pure logic — they raise on errors; the CLI handler
catches and translates to exit codes.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

import tomli_w

from ._formats import SUPPORTED_FORMATS
from .model import FileEntry

EXCLUSIONS: frozenset[str] = frozenset(
    {".git", "__pycache__", ".venv", "node_modules", "dist", "build"}
)


def _file_entry_from_raw(entry: dict[str, Any]) -> FileEntry:
    """Build a :class:`FileEntry` from a raw TOML ``[[file]]`` dict."""
    return FileEntry(
        local=Path(entry["local"]),
        remote=entry["remote"],
        recursive=entry.get("recursive", False),
        upload_as_csv=entry.get("upload_as_csv", False),
    )


def discover_files(
    root: Path,
    extensions: Iterable[str] | None = None,
    exclude_dirs: frozenset[str] = EXCLUSIONS,
) -> list[Path]:
    """Walk *root* recursively and return sorted absolute paths to supported files.

    Directory names in *exclude_dirs* are pruned from the walk.
    Only files whose suffix matches a key in :data:`SUPPORTED_FORMATS` are kept.
    When *extensions* is supplied (e.g. via ``--ext .csv``), only those suffixes
    are considered — the global registry is ignored.

    Returns an empty list when no supported files are found.
    """
    if extensions is not None:
        ext_set = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    else:
        ext_set = set(SUPPORTED_FORMATS.keys())

    results: list[Path] = []
    for entry in root.rglob("*"):
        # Skip entries whose path contains an excluded directory name anywhere.
        if any(part in exclude_dirs for part in entry.parts):
            continue
        if entry.is_file() and entry.suffix.lower() in ext_set:
            results.append(entry)

    results.sort()
    return results


def merge_entries(
    discovered: list[Path],
    raw_toml: dict[str, Any],
    base_dir: Path,
    data_dir: Path,
) -> dict[str, Any]:
    """Add new ``[[file]]`` entries for each file in *discovered*.

    Deduplication: a discovered file is skipped when its computed destination
    path (``data_dir / relative_to(base_dir)``) resolves to the same absolute
    path as an existing entry's ``FileEntry.local`` after resolving against
    *base_dir*.

    New entries are shaped as::

        [[file]]
        local = "data/<relative>"
        remote = "<Posix relative>"

    The *raw_toml* dict is mutated in-place and also returned for convenience.
    All non-``[[file]]`` top-level keys (``[dataset]``, ``[meta]``, ``[[check]]``,
    ``[[quality]]``) are preserved untouched.
    """
    # Build the set of already-registered resolved destination paths.
    existing: set[Path] = set()
    for entry in raw_toml.get("file", []):
        try:
            fe = _file_entry_from_raw(entry)
        except Exception:
            # If we can't parse the entry, skip dedup for it — it'll be
            # preserved in the TOML but won't block new discoveries.
            continue
        existing.add(fe.resolve(base_dir))

    # Ensure the "file" key exists (it's an array-of-tables in TOML).
    file_entries: list[dict[str, Any]] = raw_toml.setdefault("file", [])

    added = 0
    for src in discovered:
        relative = src.relative_to(base_dir)
        dest = data_dir / relative

        if dest in existing:
            continue

        file_entries.append(
            {
                "local": "data/" + str(PurePosixPath(relative)),
                "remote": str(PurePosixPath(relative)),
            }
        )
        existing.add(dest)
        added += 1

    return raw_toml


def copy_files(
    discovered: list[Path],
    base_dir: Path,
    data_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> list[tuple[Path, Path]]:
    """Copy discovered files into *data_dir*, preserving subdirectory structure.

    Each file is copied via :func:`shutil.copy2` to
    ``data_dir / <relative to base_dir>``.  Parent directories are created
    lazily on first use.

    Parameters:
        dry_run: When ``True``, only compute what *would* be copied — do not
            touch the filesystem.
        force: When ``True``, overwrite existing destination files silently.
            When ``False`` (the default), :class:`FileExistsError` is raised
            on collision.

    Returns:
        A list of ``(source, destination)`` tuples for every file that was
        copied (or would have been copied under ``dry_run=True``).

    Raises:
        FileExistsError: If a destination already exists and *force* is ``False``.
    """
    copied: list[tuple[Path, Path]] = []

    for src in discovered:
        relative = src.relative_to(base_dir)
        dest = data_dir / relative

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and not force:
                raise FileExistsError(
                    f"Destination already exists: {dest} (use --force to overwrite)"
                )
            shutil.copy2(src, dest)

        copied.append((src, dest))

    return copied


def write_toml(raw_toml: dict[str, Any], config_path: Path) -> None:
    """Serialize *raw_toml* and overwrite *config_path*."""
    config_path.write_text(tomli_w.dumps(raw_toml), encoding="utf-8")
