"""Sync the version and date-released fields of a CITATION.cff file.

sofer's releases are tag-driven: the package version is derived from the tag at
build time (hatch-vcs), but the CITATION.cff shipped in the repository carries
its own hardcoded ``version`` and ``date-released`` fields that are easy to
forget when cutting a release. This script keeps the two in sync.

The update path edits only the two target lines, preserving every other byte of
the file (surgical line replacement, never a YAML round-trip, which would
reformat the whole file and produce noisy diffs), including line endings: both
LF and CRLF files keep their endings untouched. The ``--check`` path is used by
the release workflow as a guard: it fails the release when the CFF does not
declare the tagged version.

The script is stdlib-only on purpose, so the CI guard job can run it with the
bare runner Python, without a ``uv sync``.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ISO_DATE_FORMAT = "%Y-%m-%d"


def _top_level_field(text: str, key: str) -> re.Match[str] | None:
    """Return the match for a column-0 ``key:`` field in ``text``, or None.

    The pattern is anchored at column 0 with no indentation allowed, so nested
    fields inside an indented block such as ``preferred-citation:`` are never
    matched, and a field such as ``cff-version:`` never matches the ``version``
    key. The value class ``[^\\r\\n]*`` keeps a trailing carriage return out of
    the captured value. Group 1 is the ``key:`` prefix, group 2 is the raw
    value.
    """
    return re.search(rf"^({re.escape(key)}\s*:)([^\r\n]*)", text, re.MULTILINE)


def _replace_field(text: str, key: str, value: str) -> str:
    """Replace the value of the column-0 ``key:`` line with ``value``.

    The pattern stops at the end of the line without consuming a trailing
    carriage return, so a CRLF file keeps ``\\r\\n`` endings on every line
    instead of degrading to mixed endings. A lambda replacement avoids
    interpreting backslashes or group references in ``value``.
    """
    pattern = re.compile(rf"^({re.escape(key)}\s*:)[^\r\n]*", re.MULTILINE)
    return pattern.sub(lambda m: f"{m.group(1)} {value}", text, count=1)


def _count_top_level_field(text: str, key: str) -> int:
    """Count column-0 occurrences of the ``key:`` field in ``text``."""
    return len(re.findall(rf"^{re.escape(key)}\s*:", text, re.MULTILINE))


def _is_valid_iso_date(value: str) -> bool:
    """Return True when ``value`` is a well-formed ISO ``YYYY-MM-DD`` date."""
    try:
        datetime.strptime(value, _ISO_DATE_FORMAT)
    except ValueError:
        return False
    return True


def update_citation_version(text: str, version: str, date_released: str) -> str:
    """Return ``text`` with the ``version`` and ``date-released`` lines replaced.

    Parameters
    ----------
    text : str
        The full CITATION.cff content.
    version : str
        The release version to write, e.g. ``"0.3.0"``.
    date_released : str
        The ISO ``YYYY-MM-DD`` release date to write.

    Returns
    -------
    str
        The input text with only the two top-level lines replaced; every other
        byte is preserved exactly, including line endings.

    Raises
    ------
    ValueError
        If either field is missing, or if either appears more than once at the
        top level (column 0). Nested fields inside indented blocks such as
        ``preferred-citation:`` are not counted.
    """
    for key in ("version", "date-released"):
        count = _count_top_level_field(text, key)
        if count == 0:
            raise ValueError(f"CITATION.cff is missing the '{key}:' field")
        if count > 1:
            raise ValueError(f"expected exactly one top-level '{key}:' field, found {count}")
    text = _replace_field(text, "version", version)
    return _replace_field(text, "date-released", date_released)


def check_citation_version(text: str, version: str) -> bool:
    """Return True when ``text`` declares ``version`` with a valid ISO date.

    Parameters
    ----------
    text : str
        The full CITATION.cff content.
    version : str
        The expected release version, e.g. ``"0.3.0"``.

    Returns
    -------
    bool
        True when the CFF declares exactly the expected ``version:`` value
        (surrounding single or double quotes allowed) and a well-formed,
        non-empty ``YYYY-MM-DD`` ``date-released:``; False on version mismatch
        or on a missing, empty, or non-ISO ``date-released:``.

    Raises
    ------
    ValueError
        If either field appears more than once at the top level (column 0).
        Nested fields inside indented blocks such as ``preferred-citation:``
        are not counted.
    """
    for key in ("version", "date-released"):
        if _count_top_level_field(text, key) > 1:
            count = _count_top_level_field(text, key)
            raise ValueError(f"expected exactly one top-level '{key}:' field, found {count}")
    version_line = _top_level_field(text, "version")
    date_line = _top_level_field(text, "date-released")
    if version_line is None or date_line is None:
        return False
    declared_version = version_line.group(2).strip(" \t\"'")
    declared_date = date_line.group(2).strip()
    return declared_version == version and _is_valid_iso_date(declared_date)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI: sync or verify the CITATION.cff version fields.

    Orchestration flow:
    1. Parse ``--version`` (required), ``--date`` (defaults to today in UTC),
       ``--cff-path`` (defaults to ``CITATION.cff`` in the cwd) and ``--check``.
    2. Validate ``--date`` when provided; reject malformed values with exit 1.
    3. Read the CFF as UTF-8 bytes; exit 1 when the file cannot be read.
    4. With ``--check``: print OK and exit 0 when the CFF declares the expected
       version with a valid ISO date-released, otherwise print FAIL to stderr
       and exit 1.
    5. Without ``--check``: replace the two fields, write the file back and
       print a confirmation; exit 1 with a clear message when a field is
       missing or duplicated, or the file cannot be written.

    Parameters
    ----------
    argv : list[str] | None, default=None
        CLI arguments; defaults to ``sys.argv[1:]`` when None.

    Returns
    -------
    int
        Exit code: 0 on success; 1 on validation/update errors; 2 on argument
        parsing errors (raised by argparse).
    """
    parser = argparse.ArgumentParser(
        prog="update_citation",
        description=(
            "Sync or verify the version and date-released fields of a CITATION.cff "
            "file against a release version."
        ),
    )
    parser.add_argument(
        "--version",
        required=True,
        help="The release version to sync or verify (e.g. 0.3.0).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="ISO release date (YYYY-MM-DD); defaults to today in UTC.",
    )
    parser.add_argument(
        "--cff-path",
        default="CITATION.cff",
        help="Path to the CITATION.cff file (default: CITATION.cff in the cwd).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify only, do not write. Exit 0 when the CFF matches, 1 otherwise.",
    )
    args = parser.parse_args(argv)

    date_released = args.date or datetime.now(timezone.utc).date().isoformat()
    if not _is_valid_iso_date(date_released):
        print(
            f"error: malformed --date '{date_released}'; expected YYYY-MM-DD",
            file=sys.stderr,
        )
        return 1

    cff_path = Path(args.cff_path)
    try:
        text = cff_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read {cff_path}: {exc}", file=sys.stderr)
        return 1

    if args.check:
        try:
            matches = check_citation_version(text, args.version)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if matches:
            print(f"OK: {cff_path} declares version {args.version} with a valid date-released.")
            return 0
        print(
            f"FAIL: {cff_path} does not declare version {args.version} with a valid date-released.",
            file=sys.stderr,
        )
        return 1

    try:
        updated = update_citation_version(text, args.version, date_released)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        cff_path.write_bytes(updated.encode("utf-8"))
    except OSError as exc:
        print(f"error: cannot write {cff_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Updated {cff_path}: version={args.version}, date-released={date_released}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
