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

from . import config

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
        limit = config.SPLITS_MAX_UNCLASSIFIED_NAMES
        names = ", ".join(report.unclassified[:limit])
        suffix = " …" if len(report.unclassified) > limit else ""
        warnings.append(
            f"{len(report.unclassified)} file(s) could not be classified "
            f"into a split: {names}{suffix}. "
            f"Unclassified files may not be loaded by the dataset viewer."
        )

    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
#  Split mapping validation (load_dataset() compatibility)
# ═══════════════════════════════════════════════════════════════════════════════


def _config_name_hint(config_names: list[str] | None, warn_limit: int | None = None) -> str:
    """Return the ``load_dataset`` recommendation the warning prints.

    Names the configs the card actually emitted when they are known: the
    instruction ``name='<config>'`` is not actionable without opening the card's
    frontmatter, and for an agent driving the MCP surface the tool result carries
    the warning but not the card (issue #303). Falls back to the placeholder form
    when they are not known, which is the only case the caller cannot name them
    (no built card on disk).

    Args:
        config_names: Emitted ``config_name`` values, or ``None``/empty when the
            caller does not have them.
        warn_limit: How many names to list before eliding; defaults to the
            ``[tool.sofer]`` cap so a corpus with dozens of groups still yields a
            readable line.

    Returns:
        A bare ``name='...'`` list (the caller supplies the surrounding prose).
    """
    if not config_names:
        return "name='<config>'"
    limit = config.CARD_CONFIG_GROUP_WARN_LIMIT if warn_limit is None else warn_limit
    shown = [f"name='{name}'" for name in config_names[:limit]]
    remaining = len(config_names) - len(shown)
    listed = ", ".join(shown)
    if remaining > 0:
        listed += f", ... and {remaining} more"
    return listed


def _carries_split_keyword(path: str) -> bool:
    """Test whether *path* names the split it was assigned to.

    The same predicate the per-file consistency message is built on: the last
    path segment's name, or the first directory segment, must carry a keyword.
    It is factored out so the split-level and the per-file readings cannot
    disagree.

    Args:
        path: Remote file path, possibly directory-qualified.

    Returns:
        ``True`` when the filename or its first directory names a split.
    """
    basename = path.rsplit("/", 1)[-1] if "/" in path else path
    if detect_split_keyword(basename) is not None:
        return True
    if "/" in path or "\\" in path:
        first_dir = re.split(r"[/\\]", path)[0].lower()
        return detect_split_keyword(first_dir) is not None
    return False


def validate_split_mapping(
    remotes: list[str],
    config_names: list[str] | None = None,
    warn_limit: int | None = None,
) -> list[str]:
    """Validate that remote file paths map correctly to HF split detection rules.

    Checks:
        - Split keywords must be delimited by non-word characters
          (``detect_split_keyword`` already enforces this — files that pass
          detection are valid).
        - Files within a detected split must all contain the split keyword in
          their filename or directory name.  This message is emitted only when
          the split carries a keyword in *some* of its files: a split whose
          files all lack one is the single-split fallback the next bullet
          already describes, and restating that once per file would scale the
          warning with the corpus size — 65 tables printed 66 lines for one
          problem (issue #316).
        - Single-split fallback: when *multiple* files all fall into ``train``
          (no split keyword detected in any file), emit a warning about the
          ``load_dataset()`` behaviour.  The generated card groups those files
          by column schema, so the warning states what a single-config card and
          a multi-config card each do, and — when *config_names* is supplied —
          names the emitted configs instead of leaving a placeholder the reader
          cannot resolve without opening the card (issue #303, RC-Universal-Card
          "Actionable warning" S4).

    Args:
        remotes: Remote file paths (existing or planned).
        config_names: ``configs[].config_name`` values read back from the built
            card, or ``None`` when the card is absent (the placeholder form is
            used instead).
        warn_limit: How many names to list before eliding; ``None`` reads the
            ``[tool.sofer]`` cap.

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
                f"split keywords. The generated card groups them by column "
                f"schema: a single-config card loads every file into one 'train' "
                f"split when load_dataset() is called without a config name "
                f"(which may be slow for large repos), while a multi-config card "
                f"is loaded one table at a time, one call per emitted config "
                f"({_config_name_hint(config_names, warn_limit)}). Consider "
                f"adding split keywords to filenames "
                f"(e.g. 'train.csv', 'test.csv') or using directory-based splits "
                f"(e.g. 'train/data.csv') to split a table across splits."
            )

    # ── Per-split keyword consistency ─────────────────────────────────────
    # Only a split that carries a keyword in *some* of its files can have a
    # genuinely inconsistent file. A split where none of the files carries one
    # is the fallback split the summary above already describes, so restating
    # it per file adds nothing and makes the warning count grow with the corpus
    # (issue #316).
    for s in report.splits:
        if not any(_carries_split_keyword(f) for f in s.files):
            continue
        for f in s.files:
            if not _carries_split_keyword(f):
                warnings.append(
                    f"File '{f}' was assigned to split '{s.name}' but does "
                    f"not contain a detectable split keyword. It may not be "
                    f"loaded correctly by the HF dataset viewer."
                )

    return warnings
