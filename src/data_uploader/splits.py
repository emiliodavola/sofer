"""
Split detection for Hugging Face dataset repositories.

Detects train / validation / test splits from remote file paths following the
official HF conventions documented at
https://huggingface.co/docs/hub/datasets-repository-structure.

Key rules:
- Split names must be delimited by non-word characters (``test-file.csv`` OK,
  ``testfile.csv`` not).
- Detection cascade: directory name → filename → shard pattern → single-split.
- Multi-file splits: all files sharing the same split keyword are grouped
  into that split.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Split keyword registry ─────────────────────────────────────────────────────

_SPLIT_KEYWORDS: dict[str, list[str]] = {
    "train": ["train", "training"],
    "validation": ["validation", "valid", "val", "dev"],
    "test": ["test", "testing", "eval", "evaluation"],
}

# Reverse mapping: slug → canonical name.
_SLUG_TO_CANONICAL: dict[str, str] = {}
for _canon, _slugs in _SPLIT_KEYWORDS.items():
    for _s in _slugs:
        _SLUG_TO_CANONICAL[_s] = _canon


# ═══════════════════════════════════════════════════════════════════════════════
#  Data structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SplitInfo:
    """A detected data split with its remote file paths.

    Attributes:
        name:  Canonical split name (``"train"``, ``"validation"``, ``"test"``).
        files: Remote paths belonging to this split.
    """

    name: str
    files: list[str]


@dataclass
class SplitReport:
    """Result of split detection for a set of remote files.

    Attributes:
        splits:       Detected splits (at least one when files are present).
        unclassified: Files that could not be assigned to any split.
        warnings:     Human-readable warnings about ambiguous or invalid layouts.
    """

    splits: list[SplitInfo] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  Keyword detection
# ═══════════════════════════════════════════════════════════════════════════════


def detect_split_keyword(name: str) -> str | None:
    """Test whether *name* contains a recognised split keyword.

    The keyword must be delimited by non-word characters per the HF rule:
    ``"test-file.csv"`` is a match (``test`` is delimited by ``-``);
    ``"testfile.csv"`` is not.

    Args:
        name: A filename or directory name (lowercased before matching).

    Returns:
        The canonical split name (``"train"`` / ``"validation"`` / ``"test"``)
        or ``None``.
    """
    # Split on anything that is NOT a word character (letter/digit/underscore).
    parts: list[str] = re.split(r"[_\-\s.]+", name.lower())
    for part in parts:
        if part in _SLUG_TO_CANONICAL:
            return _SLUG_TO_CANONICAL[part]
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Detection cascade (directory → filename → shard → fallback)
# ═══════════════════════════════════════════════════════════════════════════════


def _detect_directory_splits(files: list[str]) -> SplitReport:
    """Strategy 1 — split encoded in the top-level directory name.

    Examples:
        ``train/data.csv``, ``test/data.csv`` → train / test split.
    """
    splits_buckets: dict[str, list[str]] = {}
    unclassified: list[str] = []

    for f in files:
        if "/" in f or "\\" in f:
            first_dir = re.split(r"[/\\]", f)[0].lower()
            kw = detect_split_keyword(first_dir)
            if kw:
                splits_buckets.setdefault(kw, []).append(f)
            else:
                unclassified.append(f)
        else:
            unclassified.append(f)

    if not splits_buckets:
        return SplitReport(unclassified=list(files))

    return SplitReport(
        splits=[SplitInfo(name=name, files=files) for name, files in splits_buckets.items()],
        unclassified=unclassified,
    )


def _detect_filename_splits(files: list[str]) -> SplitReport:
    """Strategy 2 — split keyword in the filename stem.

    Examples:
        ``train.csv``, ``test.csv`` → train / test split.
        ``my-train-data.csv`` → train split (``train`` delimited by ``-``).
    """
    splits_buckets: dict[str, list[str]] = {}
    unclassified: list[str] = []

    for f in files:
        basename = f.rsplit("/", 1)[-1] if "/" in f else f
        kw = detect_split_keyword(basename)
        if kw:
            splits_buckets.setdefault(kw, []).append(f)
        else:
            unclassified.append(f)

    if not splits_buckets:
        return SplitReport(unclassified=list(files))

    return SplitReport(
        splits=[SplitInfo(name=name, files=files) for name, files in splits_buckets.items()],
        unclassified=unclassified,
    )


def _detect_shard_splits(files: list[str]) -> SplitReport:
    """Strategy 3 — custom shard pattern ``xxxxx-of-xxxxx``.

    Example:
        ``train-00001-of-00005.parquet``,
        ``test-00001-of-00003.parquet`` → train / test split.
    """
    pattern = re.compile(r"^(.+?)[\-_](\d{5})-of-(\d{5})\.(\w+)$", re.IGNORECASE)

    splits_buckets: dict[str, list[str]] = {}
    unclassified: list[str] = []

    for f in files:
        basename = f.rsplit("/", 1)[-1] if "/" in f else f
        m = pattern.match(basename)
        if m:
            prefix = m.group(1).lower()
            kw = detect_split_keyword(prefix)
            if kw:
                splits_buckets.setdefault(kw, []).append(f)
            else:
                unclassified.append(f)
        else:
            unclassified.append(f)

    if len(splits_buckets) < 2:
        return SplitReport(unclassified=list(files))

    return SplitReport(
        splits=[SplitInfo(name=name, files=files) for name, files in splits_buckets.items()],
        unclassified=unclassified,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

_EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        "readme.md",
        "license",
        ".gitattributes",
        ".gitignore",
    }
)


def detect_splits(files: list[str]) -> SplitReport:
    """Detect dataset splits from a list of remote file paths.

    Detection cascade (first strategy that produces at least one split wins):

    1. **Directory name** — ``train/data.csv``, ``test/data.csv``
    2. **Filename** — ``train.csv``, ``test.csv``
    3. **Shard pattern** — ``train-00001-of-00005.parquet``
    4. **Single-split fallback** — all files assigned to ``train``

    Files matching :data:`_EXCLUDED_FILES` (README.md, LICENSE, …) are ignored
    during classification.

    Args:
        files: Remote file paths (e.g. ``["train.csv", "test.csv"]``).

    Returns:
        A :class:`SplitReport` with detected splits, unclassified files,
        and warnings.
    """
    if not files:
        return SplitReport()

    # Exclude metadata files that are never data splits.
    data_files = [f for f in files if f.lower() not in _EXCLUDED_FILES]

    if not data_files:
        return SplitReport(
            splits=[SplitInfo(name="train", files=list(files))],
            warnings=["Only metadata files found — assigned to 'train' split."],
        )

    # Cascade
    for detector in [
        _detect_directory_splits,
        _detect_filename_splits,
        _detect_shard_splits,
    ]:
        result = detector(data_files)
        if result.splits:
            return result

    # ── Fallback: single train split ──────────────────────────────────────
    return SplitReport(
        splits=[SplitInfo(name="train", files=list(data_files))],
        warnings=["No splits detected — all data files assigned to 'train' split."],
    )


def validate_layout(files: list[str]) -> list[str]:
    """Check that the file layout is viewer-loadable by the HF Datasets library.

    A viewer-loadable dataset needs at least a ``train`` split accessible
    without custom loading scripts.  This function runs :func:`detect_splits`
    internally and surfaces layout issues as human-readable warnings.

    **This does NOT enforce a ``data/`` folder** — root-level
    ``train.csv`` / ``test.csv`` is perfectly valid per the HF docs.

    Args:
        files: Remote file paths as returned by ``HfApi.list_repo_files()``
               or the local upload manifest.

    Returns:
        A list of warning strings (empty = layout is valid).
    """
    warnings: list[str] = []
    report = detect_splits(files)

    split_names = {s.name for s in report.splits}
    if "train" not in split_names:
        warnings.append(
            "No 'train' split detected. The HF dataset viewer requires at "
            "least a train split for automatic loading. Consider naming a "
            "file with 'train' in the filename (e.g. 'train.csv') or "
            "placing files in a 'train/' directory."
        )

    if report.unclassified:
        names = ", ".join(report.unclassified[:5])
        suffix = " …" if len(report.unclassified) > 5 else ""
        warnings.append(
            f"{len(report.unclassified)} file(s) could not be classified "
            f"into a split: {names}{suffix}. "
            f"Unclassified files may not be loaded by the dataset viewer."
        )

    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
#  Split mapping validation (load_dataset() compatibility)
# ═══════════════════════════════════════════════════════════════════════════════


def validate_split_mapping(remotes: list[str]) -> list[str]:
    """Validate that remote file paths map correctly to HF split detection rules.

    Checks:
        - Split keywords must be delimited by non-word characters
          (``detect_split_keyword`` already enforces this — files that pass
          detection are valid).
        - Files within a detected split must all contain the split keyword in
          their filename or directory name.
        - Single-split fallback: when *multiple* files all fall into ``train``
          (no split keyword detected in any file), emit a warning about the
          ``load_dataset()`` behaviour.

    Args:
        remotes: Remote file paths (existing or planned).

    Returns:
        A list of warning strings (empty = layout follows HF conventions).
    """
    warnings: list[str] = []
    data_files = [f for f in remotes if f.lower() not in _EXCLUDED_FILES]

    if not data_files:
        return warnings

    report = detect_splits(remotes)

    # ── Default-load warning: multiple files, all in train fallback ───────
    if len(data_files) > 1:
        has_fallback = any("No splits detected" in w for w in report.warnings)
        if has_fallback:
            warnings.append(
                f"Default-load warning: {len(data_files)} data files have no "
                f"split keywords. When a user calls load_dataset() without "
                f"data_files, ALL files will be loaded into a single 'train' split "
                f"(which may be slow for large repos). Consider adding split "
                f"keywords to filenames (e.g. 'train.csv', 'test.csv') or "
                f"using directory-based splits (e.g. 'train/data.csv')."
            )

    # ── Per-split keyword consistency ─────────────────────────────────────
    for s in report.splits:
        for f in s.files:
            basename = f.rsplit("/", 1)[-1] if "/" in f else f
            kw = detect_split_keyword(basename)

            # Check directory name as well (dir-based splits)
            dir_kw: str | None = None
            if "/" in f or "\\" in f:
                import re as _re

                first_dir = _re.split(r"[/\\]", f)[0].lower()
                dir_kw = detect_split_keyword(first_dir)

            if kw is None and dir_kw is None:
                warnings.append(
                    f"File '{f}' was assigned to split '{s.name}' but does "
                    f"not contain a detectable split keyword. It may not be "
                    f"loaded correctly by the HF dataset viewer."
                )

    return warnings
