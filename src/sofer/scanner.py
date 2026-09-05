"""
File discovery and TOML registration for the ``scan`` command.

MOVE-then-copy orchestrator: discover loose → check collisions → move to
raw/ → discover → check flatten → merge → copy → write.

Pipeline: raw/ (tracked) -> cache/ (OUTPUT_DIR, gitignored) -> build/
(gitignored). ``scan`` MOVEs loose supported files (``.csv``, ``.tsv``,
``.xlsx``, ``.jsonl``, ``.parquet``) not under ``raw/``/``cache/``/
``EXCLUSIONS`` into ``raw/`` preserving ``relative_to(base_dir)`` tree
via :func:`move_to_raw` (``dest = raw_dir / rel``, lazy ``mkdir -p``
parent), checks raw-dest collisions atomically via
:func:`check_raw_collisions`, then copies ``raw/`` → ``cache/`` via
:func:`flatten_first_level` and :func:`copy_files` (``raw/DPTO.csv`` →
``cache/DPTO.csv``). ``EXCLUSIONS`` (``.git``, ``__pycache__``,
``.venv``, ``node_modules``, ``dist``, ``build``) are pruned;
``cache/`` (``OUTPUT_DIR``) excluded via ``EXCLUSIONS|{OUTPUT_DIR}``;
``raw/`` excluded only during the MOVE discovery phase via
``EXCLUSIONS|{RAW_DIR, OUTPUT_DIR}``.

``copy_files`` is idempotent on re-scan (an already-identical destination is
skipped, SCN-08) and ``write_toml`` commits atomically (temp file +
``os.replace``) so a TOML write failure can never leave a partial config.
The TOML is written LAST (after all copies) so a failure cannot leave an
inconsistent cache/TOML state — recovery is a plain re-run with ``--force``.

All functions are pure logic — they raise on errors; the CLI handler
catches and translates to exit codes.

Symlinks are EXCLUDED from discovery (SCN-01): :func:`discover_files`
skips symlinked entries AND entries reached through a symlinked (or, on
Windows, junctioned) directory. On Python 3.10-3.12 ``Path.rglob`` follows
directory links, so a link inside the scan root pointing OUTSIDE it would
otherwise have its contents discovered, copied into ``cache/`` by
:func:`copy_files`, registered, and published — an exfiltration vector.
"""

from __future__ import annotations

import filecmp
import os
import shutil
import stat
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

import tomli_w

from . import config
from ._formats import SUPPORTED_FORMATS
from .model import FileEntry

#: Directory names excluded from recursive file discovery (scan command).
EXCLUSIONS: frozenset[str] = frozenset(
    {".git", "__pycache__", ".venv", "node_modules", "dist", "build"}
)


def _is_link(path: Path) -> bool:
    """Return ``True`` when *path* is a symlink or a Windows reparse point.

    ``Path.is_symlink()`` alone misses NTFS junctions (``mklink /J``): on
    every supported Python version junctions report ``is_symlink() == False``
    (``Path.is_junction()`` exists only on 3.12+). Junctions are detected via
    the ``FILE_ATTRIBUTE_REPARSE_POINT`` stat flag on Windows. POSIX never
    has reparse points, so the ``os.name != "nt"`` short-circuit keeps the
    check free of platform-specific stat fields.

    Args:
        path: The path to inspect.

    Returns:
        ``True`` when *path* is a symlink or (Windows) a reparse point such
        as a junction.
    """
    if path.is_symlink():
        return True
    if os.name != "nt":
        return False
    try:
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def flatten_first_level(relative: Path) -> Path:
    """Drop the first path segment; root-level paths are returned unchanged.

    ``raw/DPTO.csv`` becomes ``DPTO.csv``, ``raw/Labels/a.csv`` becomes
    ``Labels/a.csv``, and a root-level ``x.csv`` is returned as ``x.csv``.
    """
    parts = relative.parts
    if len(parts) <= 1:
        return relative
    return Path(*parts[1:])


def check_raw_collisions(
    candidates: list[Path],
    raw_dir: Path,
    base_dir: Path,
) -> None:
    """Raise :class:`ValueError` if any MOVE destination already exists.

    Each *candidate* is mapped to ``dest = raw_dir / rel`` where
    ``rel = src.relative_to(base_dir)``, preserving the full relative tree
    (no flatten). When any ``dest`` already exists on disk, the error names
    both the source and the destination and the caller must abort before any
    move.

    Args:
        candidates: Absolute paths to loose files that would be moved.
        raw_dir: Absolute path to the ``raw/`` directory.
        base_dir: Absolute base directory for ``relative_to``.

    Raises:
        ValueError: When any destination already exists. The message names
            every colliding source and its destination.
    """
    errors: list[str] = []
    for src in candidates:
        rel = src.relative_to(base_dir)
        dest = raw_dir / rel
        if dest.exists():
            errors.append(
                f"Collision in raw/: {dest.as_posix()} already exists (from {src.as_posix()})"
            )

    if errors:
        raise ValueError("\n".join(errors))


def check_flatten_collisions(discovered: list[Path], base_dir: Path) -> None:
    """Raise :class:`ValueError` if two or more discovered files flatten to the same destination.

    The error message names every colliding source path and the destination they
    conflict on.

    Args:
        discovered: Absolute or relative paths to discovered files.
        base_dir: The base directory against which relative paths are computed.

    Raises:
        ValueError: When any flattened destination is produced by more than one
            source file.  The message names all sources for each collision.
    """
    from collections import defaultdict

    collisions: dict[Path, list[Path]] = defaultdict(list)
    for src in discovered:
        relative = src.relative_to(base_dir)
        flat = flatten_first_level(relative)
        collisions[flat].append(src)

    errors: list[str] = []
    for flat, sources in sorted(collisions.items()):
        if len(sources) > 1:
            src_list = " and ".join(s.as_posix() for s in sorted(sources))
            errors.append(f"Collision in cache/: {flat.as_posix()} from {src_list}")

    if errors:
        raise ValueError("\n".join(errors))


def collect_init_moves(
    root: Path,
    toml_name: str,
    raw_dir: Path,
) -> tuple[list[Path], list[Path]]:
    """Collect the ``--move-existing`` move set for ``sofer init``.

    Single shared home (AGENTS.md rule 4) for the collection logic that the
    CLI ``_cmd_init`` and MCP ``sofer_init`` adapters both need: depth-1
    ``SUPPORTED_FORMATS`` files directly under *root* — excluding the TOML
    itself (``entry.name == toml_name``) and any symlink/junction
    (:func:`_is_link`, SCN-01 exfiltration guard) — become the sorted
    *candidates*; supported files already present under *raw_dir* become
    *existing*. The flatten-collision check against the two lists is the
    caller's concern (the CLI gates it on non-empty candidates, the MCP runs
    it whenever ``move_existing`` is set).

    Args:
        root:      Dataset root whose depth-1 files are inspected.
        toml_name: The TOML filename to exclude from the move set.
        raw_dir:   The ``raw/`` directory whose existing files are collected.

    Returns:
        ``(candidates, existing)`` — sorted absolute move candidates and the
        existing supported files under *raw_dir* (possibly empty).
    """
    candidates: list[Path] = []
    for entry in root.iterdir():
        if not entry.is_file():
            continue
        if _is_link(entry):
            # Symlinks/junctions are never moved into raw/ (SCN-01
            # exfiltration guard, mirrored from discover_files).
            continue
        if entry.suffix.lower() not in SUPPORTED_FORMATS:
            continue
        if entry.name == toml_name:
            continue
        candidates.append(entry.resolve())
    candidates.sort()

    existing: list[Path] = []
    if raw_dir.exists():
        for q in raw_dir.rglob("*"):
            if q.is_file() and q.suffix.lower() in SUPPORTED_FORMATS:
                existing.append(q.resolve())
    return candidates, existing


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

    Symlinks (and Windows junctions) are excluded from discovery (SCN-01): a
    symlinked entry itself is skipped, and so is any entry whose path passes
    through a linked directory. This matters on Python 3.10-3.12, where
    ``Path.rglob`` follows directory links — without the ancestor guard a
    link inside the scan root pointing OUTSIDE it would have its contents
    discovered, copied into ``cache/``, registered, and publishable.

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
        if _is_link(entry):
            continue
        # On 3.10-3.12 rglob follows directory links: a file reached THROUGH
        # a linked directory is itself not a link, so also reject entries whose
        # path contains a link ancestor (checked up to, but not including, the
        # scan root itself).
        linked_ancestor = False
        for parent in entry.parents:
            if parent == root:
                break
            if _is_link(parent):
                linked_ancestor = True
                break
        if linked_ancestor:
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
    path (``data_dir / flatten_first_level(relative_to(base_dir))``) resolves
    to the same absolute path as an existing entry's ``FileEntry.local`` after
    resolving against *base_dir*.

    Paths are flattened by dropping the first segment:
    ``raw/DPTO.csv`` → ``DPTO.csv``, ``raw/Labels/a.csv`` → ``Labels/a.csv``.

    New entries are shaped as::

        [[file]]
        local = "<output-dir>/<flattened>"
        remote = "<Posix flattened>"

    where ``<output-dir>`` is *data_dir* expressed relative to *base_dir*
    (e.g. ``cache/`` with the default OUTPUT_DIR), so the registered local
    path always resolves back to the copy destination.

    The *raw_toml* dict is mutated in-place and also returned for convenience.
    All non-``[[file]]`` top-level keys (``[dataset]``, ``[meta]``, ``[[check]]``,
    ``[[quality]]``) are preserved untouched.
    """
    # Strip template entries left over from ``sofer init`` (their local
    # path is a placeholder that starts with ``TODO:`` and would cause
    # spurious errors downstream in validate / prepare / publish).
    # Also strip Windows-safe placeholder ``raw/example.csv`` / ``raw/example/``
    # introduced in fix-sofer-init-cwd-windows-todo (INIT-01).
    raw_toml["file"] = [
        e
        for e in raw_toml.get("file", [])
        if not str(e.get("local", "")).startswith("TODO:")
        and not str(e.get("local", "")).startswith("raw/example")
    ]

    # Build the set of already-registered resolved destination paths and
    # their remotes. Dedup keys on BOTH: the resolved local path (new layout)
    # and the remote (migration-safe — a pre-cache TOML with local="data/a.csv"
    # still carries remote="a.csv", so a re-scan won't duplicate it).
    existing: set[Path] = set()
    existing_remotes: set[str] = set()
    for entry in raw_toml.get("file", []):
        try:
            fe = _file_entry_from_raw(entry)
        except Exception:
            # If we can't parse the entry, skip dedup for it — it'll be
            # preserved in the TOML but won't block new discoveries.
            continue
        existing.add(fe.resolve(base_dir))
        if fe.remote:
            existing_remotes.add(PurePosixPath(fe.remote).as_posix())

    # Ensure the "file" key exists (it's an array-of-tables in TOML).
    file_entries: list[dict[str, Any]] = raw_toml.setdefault("file", [])

    added = 0
    for src in discovered:
        relative = src.relative_to(base_dir)
        flat = flatten_first_level(relative)
        dest = data_dir / flat

        if dest in existing:
            continue
        if PurePosixPath(flat).as_posix() in existing_remotes:
            continue

        # The registered local path mirrors the copy destination (data_dir /
        # flat), expressed relative to base_dir so it survives relocation.
        try:
            local = (data_dir.relative_to(base_dir) / flat).as_posix()
        except ValueError:  # data_dir outside base_dir → fall back to its name
            local = f"{data_dir.name}/{flat.as_posix()}"

        file_entries.append(
            {
                "local": local,
                "remote": str(PurePosixPath(flat)),
            }
        )
        existing.add(dest)
        added += 1

    return raw_toml


def move_to_raw(
    candidates: list[Path],
    base_dir: Path,
    raw_dir: Path,
    *,
    dry_run: bool = False,
) -> list[tuple[Path, Path]]:
    """Move *candidates* into ``raw/`` preserving ``relative_to(base_dir)`` tree.

    Each source is moved via :func:`shutil.move` to ``dest = raw_dir /
    src.relative_to(base_dir)``. Parent directories are created lazily.
    No flatten is applied — ``a/b/x.csv`` stays ``raw/a/b/x.csv``.

    Args:
        candidates: Absolute paths to loose files to move.
        base_dir: Absolute base directory for ``relative_to``.
        raw_dir: Absolute path to the ``raw/`` directory.
        dry_run: When ``True``, only compute destinations — do not touch the
            filesystem.

    Returns:
        A list of ``(source, destination)`` tuples for every file that was
        moved (or would have been moved under ``dry_run=True``).
    """
    moved: list[tuple[Path, Path]] = []

    for src in candidates:
        rel = src.relative_to(base_dir)
        dest = raw_dir / rel

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))

        moved.append((src, dest))

    return moved


def _files_identical(a: Path, b: Path) -> bool:
    """Return ``True`` when *a* and *b* have identical byte content.

    Powers the idempotent re-scan contract (SCN-08): :func:`copy_files`
    treats a destination that already mirrors the source byte-for-byte as
    already copied, while a destination that *differs* still raises
    :class:`FileExistsError` unless ``--force``.

    Args:
        a: First path to compare.
        b: Second path to compare.

    Returns:
        ``True`` when both paths are regular files with identical content;
        ``False`` on any difference or comparison failure (missing file,
        unreadable, differing bytes).
    """
    try:
        return filecmp.cmp(a, b, shallow=False)
    except OSError:
        return False


def copy_files(
    discovered: list[Path],
    base_dir: Path,
    data_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> list[tuple[Path, Path]]:
    """Copy discovered files into *data_dir*, flattening the first path segment.

    Each file is copied via :func:`shutil.copy2` to
    ``data_dir / <flatten_first_level(relative)>``.  Parent directories are
    created lazily on first use.

    Idempotent re-scan (SCN-08): when a destination already exists with
    content identical to the source, it is skipped (not re-copied, no error),
    so ``scan`` run twice against unchanged sources is safe. A destination
    whose content *differs* from the source is still protected — it raises
    :class:`FileExistsError` unless *force* is ``True``.

    Parameters:
        dry_run: When ``True``, only compute what *would* be copied — do not
            touch the filesystem.
        force: When ``True``, overwrite existing destination files silently.
            When ``False`` (the default), an already-identical destination is
            skipped and a differing destination raises
            :class:`FileExistsError`.

    Returns:
        A list of ``(source, destination)`` tuples for every file that was
        copied (or would have been copied under ``dry_run=True``). Files
        skipped as already-identical are not included.

    Raises:
        FileExistsError: If a destination already exists with *different*
            content and *force* is ``False``.
    """
    copied: list[tuple[Path, Path]] = []

    for src in discovered:
        relative = src.relative_to(base_dir)
        flat = flatten_first_level(relative)
        dest = data_dir / flat

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and not force:
                if _files_identical(src, dest):
                    # Already copied with identical content — re-scan is
                    # idempotent, skip without error (SCN-08).
                    continue
                raise FileExistsError(
                    f"Destination already exists and differs: {dest} (use --force to overwrite)"
                )
            shutil.copy2(src, dest)

        copied.append((src, dest))

    return copied


def write_toml(raw_toml: dict[str, Any], config_path: Path) -> None:
    """Serialize *raw_toml* and atomically replace *config_path* (SCN-08).

    The TOML is written to a temporary file in the same directory, then moved
    into place with :func:`os.replace` — so a crash or failure mid-write can
    never leave a truncated or partial TOML at *config_path*.
    """
    tmp = config_path.with_name(config_path.name + ".tmp")
    tmp.write_text(tomli_w.dumps(raw_toml), encoding=config.OUTPUT_ENCODING)
    os.replace(tmp, config_path)
