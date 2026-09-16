"""Shared helpers for post-publish cleanup and prepare orphan pruning.

This module is the single source of truth for what belongs in the
prepare output directory (``build/`` or ``--output`` override) and for
how ``publish --clean`` removes ``build/`` and, opt-in, ``cache/``.

- :func:`allowed_output_remotes` builds the allowlist from
  :func:`sofer._mirror.expanded_planned_remotes` plus the auto-generated
  compliance set (``README.md``, ``LICENSE``, ``codebook.md``,
  ``codebooks/**``) and, when *keep_csv* is ``True``, the original CSV
  remotes.  Dual ``__``/``_`` handling for XLSX sheets is inherited from
  ``expanded_planned_remotes`` (which globs ``__*.parquet`` then falls
  back to ``_*.parquet`` filtered by ``c.stem != stem``), so a single-
  underscore sheet such as ``DATA_GOT_ALL.xlsx → data_got_all_aristas.parquet``
  is recognised as owned.

- :func:`prune_orphans` removes every regular file under *output_dir*
  whose POSIX-relative path (case-insensitive) is not in that allowlist.
  Each deletion is wrapped in ``try/except`` and logged via ``print``
  with the absolute path; a failure never aborts the sweep.

- :func:`clean_build` / :func:`clean_cache` are the opt-in teardown
  helpers used by ``publish --clean``.  Existence is checked before
  ``shutil.rmtree`` and every removal is guarded by ``try/except`` without
  ``ignore_errors=True`` semantics.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    from .model import DatasetConfig

# Re-exported for tests / callers that want to check compliance membership.
_AUTO_GENERATED: frozenset[str] = frozenset({"readme.md", "license", "codebook.md"})
_AUTO_GENERATED_PREFIXES: tuple[str, ...] = ("codebooks/",)


def _is_auto_generated(remote: str) -> bool:
    """Return ``True`` when *remote* is an auto-generated compliance path.

    Mirrors :func:`sofer.publish._is_auto_generated` so the two modules do
    not diverge.  Matching is case-insensitive and ``codebooks/`` is a
    prefix match covering every per-file codebook page.

    Args:
        remote: POSIX-relative remote path.

    Returns:
        ``True`` when the path is a compliance file that must never be
        treated as an orphan.
    """
    lower = remote.lower()
    return lower in _AUTO_GENERATED or lower.startswith(_AUTO_GENERATED_PREFIXES)


def allowed_output_remotes(
    cfg: DatasetConfig,
    keep_csv: bool,
    output_dir: Path,
) -> set[str]:
    """Return the allowlist of POSIX remotes that belong in *output_dir*.

    The set is the union of:

    - ``expanded_planned_remotes(cfg, keep_csv, output_dir)`` (ground truth
      for multi-sheet XLSX, dual ``__``/``_`` guard via the mirror glob),
    - auto-generated compliance files (``README.md``, ``LICENSE``,
      ``codebook.md`` and the ``codebooks/**`` prefix family),
    - the package artifact manifest (``manifest.json``, PRP-11/#122),
      which prepare re-creates at the end of every run and must never be
      pruned as an orphan,
    - the ``keep_csv`` CSV remotes already included by the first item when
      *keep_csv* is ``True`` (CSV-only, never for XLSX).

    The ``codebooks/**`` prefix is not enumerated as individual members;
    instead ``README.md``, ``LICENSE`` and ``codebook.md`` are inserted
    explicitly and any path under ``codebooks/`` is treated as allowed by
    :func:`prune_orphans` via :func:`_is_auto_generated`.  The returned
    strings are the verbatim POSIX remotes (already normalised on disk);
    callers compare case-insensitively.

    Args:
        cfg:        Dataset configuration.
        keep_csv:   When ``True``, also keep original CSVs alongside Parquet.
        output_dir: Prepared package directory (mirror layout root; used to
                    expand XLSX sheets via the ground-truth glob).

    Returns:
        Lowercased set of allowed POSIX-relative paths.
    """
    from ._mirror import expanded_planned_remotes

    # Ground truth — handles single-underscore XLSX via fallback glob.
    raw = expanded_planned_remotes(cfg, keep_csv, output_dir)
    allowed: set[str] = {r.lower() for r in raw}

    # Compliance files are always owned, even before the first codebook run.
    for name in ("README.md", "LICENSE", "codebook.md"):
        allowed.add(name.lower())

    # Recursive entries are not enumerated by expanded_planned_remotes as
    # individual file paths — they are directory prefixes.  We cannot expand
    # them without walking the source tree, but pruning must not delete
    # staged recursive content.  Instead, any path that falls under a
    # recursive remote prefix is considered owned by the helper that checks
    # prefixes in prune_orphans.  To keep this function's return type simple
    # (set of exact remotes) we record the recursive prefixes lowercased
    # with a trailing slash; prune_orphans checks prefix membership.
    for entry in cfg.files:
        if entry.recursive:
            # Remote like "assets/" -> keep everything under that prefix.
            prefix = entry.remote.rstrip("/\\").lower()
            if prefix:
                # Store as prefix sentinel with trailing slash.
                allowed.add(prefix + "/")

    return allowed


def prune_orphans(output_dir: Path, allowed: set[str]) -> list[Path]:
    """Delete every file under *output_dir* not present in *allowed*.

    Traverses ``output_dir.rglob("*")`` for regular files only.  A file
    is considered owned when either:

    - its POSIX-relative path lowercased is in *allowed*, or
    - it is an auto-generated compliance path (``README.md``, ``LICENSE``,
      ``codebook.md``, ``codebooks/**`` - case-insensitive), or
    - its lowercased relative path is a child of a recursive prefix entry
      in *allowed* (members ending with ``/``).

    Deletions are reported with the absolute path and each file is wrapped
    in ``try/except`` so one failure never aborts the sweep.  Empty
    directories left behind are not removed (they are harmless and
    ``prepare`` recreates its tree on the next run).

    Args:
        output_dir: Prepared package directory to sweep.
        allowed:    Lowercased allowlist from :func:`allowed_output_remotes`.

    Returns:
        List of absolute paths that were successfully removed.
    """
    if not output_dir.is_dir():
        return []

    # Normalise allowed: exact files vs prefix sentinels (trailing /).
    allowed_files = {a for a in allowed if not a.endswith("/")}
    allowed_prefixes = tuple(a for a in allowed if a.endswith("/"))

    removed: list[Path] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(output_dir).as_posix().lower()
        except ValueError:
            continue
        # Compliance / codebooks prefix always allowed.
        if _is_auto_generated(rel):
            continue
        # Recursive prefix: "assets/" keeps "assets/a.txt", "assets/nested/b.txt"
        if allowed_prefixes and any(rel.startswith(p) for p in allowed_prefixes):
            continue
        if rel in allowed_files:
            continue
        # Also allow the CSV-original case when keep_csv added it — it's already
        # in allowed_files lowercased.  No extra check needed.

        # Orphan -> delete with guard.
        try:
            path.unlink()
            print(f"  pruned orphan: {path.resolve()}")
            removed.append(path.resolve())
        except Exception as exc:
            print(f"  !  failed to prune {path.resolve()}: {exc}")

    return removed


def clean_build(cfg: DatasetConfig, override: str | None) -> None:
    """Remove the resolved build directory when it exists.

    Resolution matches :func:`sofer.prepare.resolve_output_dir` so a
    ``--output`` override is honoured.  The check is existence-gated and
    guarded by ``try/except`` without ``ignore_errors=True``.

    Args:
        cfg:      Dataset configuration.
        override: ``--output`` value (``None`` = ``cfg.build_dir``).
    """
    base = cfg._base_dir if getattr(cfg, "_base_dir", None) else Path.cwd()
    cfg_build_dir: str = getattr(cfg, "build_dir", "build")
    name: str = override if override is not None else cfg_build_dir
    out = Path(name)
    if not out.is_absolute():
        out = base / out
    target = out.resolve()
    if not target.exists():
        return
    try:
        shutil.rmtree(target)
        print(f"  cleaned build: {target.resolve()}")
    except Exception as exc:
        print(f"  !  failed to clean build {target.resolve()}: {exc}")


def clean_cache(base_dir: Path) -> None:
    """Remove the tool-wide ``cache/`` directory anchored to *base_dir*.

    ``cache/`` (``config.OUTPUT_DIR``) is shared across datasets in the
    same TOML directory (HIGH blast radius).  Callers must warn that
    siblings share it before invoking this helper.  Existence is checked
    before ``shutil.rmtree`` and failures are reported without
    ``ignore_errors=True``.

    Args:
        base_dir: Dataset TOML directory (``cfg._base_dir`` or ``Path.cwd()``).
    """
    target = base_dir / config.OUTPUT_DIR
    if not target.exists():
        return
    try:
        shutil.rmtree(target)
        print(f"  cleaned cache: {target.resolve()}")
        print("  !  cache/ is shared tool-wide — sibling datasets may be affected.")
    except Exception as exc:
        print(f"  !  failed to clean cache {target.resolve()}: {exc}")
