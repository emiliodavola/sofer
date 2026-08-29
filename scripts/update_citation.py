"""Sync the version and date-released fields of a CITATION.cff file.

sofer's releases are tag-driven: the package version is derived from the tag at
build time (hatch-vcs), but the CITATION.cff shipped in the repository carries
its own hardcoded ``version`` and ``date-released`` fields that are easy to
forget when cutting a release. This script keeps the two in sync.

The update path edits only the two target lines, preserving every other byte of
the file (surgical line replacement, never a YAML round-trip, which would
reformat the whole file and produce noisy diffs). The ``--check`` path is used
by the release workflow as a guard: it fails the release when the CFF does not
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


def _field_line(text: str, key: str) -> re.Match[str] | None:
    """Return the match for the ``key:`` line in ``text``, or None if absent.

    The key is anchored at the start of a line (after optional indentation), so
    a field such as ``cff-version:`` never matches the ``version`` key. Group 1
    is the ``key:`` prefix, group 2 is the raw value.
    """
    return re.search(rf"^(\s*{re.escape(key)}\s*:)(.*)$", text, re.MULTILINE)


def _replace_field(text: str, key: str, value: str) -> str:
    """Replace the value of the ``key:`` line with ``value`` (first match only).

    A lambda replacement avoids interpreting backslashes or group references in
    ``value``; only the first occurrence is replaced.
    """
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*:).*$", re.MULTILINE)
    return pattern.sub(lambda m: f"{m.group(1)} {value}", text, count=1)


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
        The input text with only the two target lines replaced; every other
        byte is preserved exactly.

    Raises
    ------
    ValueError
        If either the ``version:`` or ``date-released:`` line is missing.
    """
    if _field_line(text, "version") is None:
        raise ValueError("CITATION.cff is missing the 'version:' field")
    if _field_line(text, "date-released") is None:
        raise ValueError("CITATION.cff is missing the 'date-released:' field")
    text = _replace_field(text, "version", version)
    return _replace_field(text, "date-released", date_released)


def check_citation_version(text: str, version: str) -> bool:
    """Return True when ``text`` declares ``version`` with a non-empty date.

    Parameters
    ----------
    text : str
        The full CITATION.cff content.
    version : str
        The expected release version, e.g. ``"0.3.0"``.

    Returns
    -------
    bool
        True when the CFF declares exactly the expected ``version:`` value and
        a non-empty ``date-released:``; False on version mismatch or on a
        missing/empty ``date-released:``.
    """
    version_line = _field_line(text, "version")
    date_line = _field_line(text, "date-released")
    if version_line is None or date_line is None:
        return False
    declared_version = version_line.group(2).strip()
    declared_date = date_line.group(2).strip()
    return declared_version == version and bool(declared_date)


def _is_valid_iso_date(value: str) -> bool:
    """Return True when ``value`` is a well-formed ISO ``YYYY-MM-DD`` date."""
    try:
        datetime.strptime(value, _ISO_DATE_FORMAT)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    """Run the CLI: sync or verify the CITATION.cff version fields.

    Orchestration flow:
    1. Parse ``--version`` (required), ``--date`` (defaults to today in UTC),
       ``--cff-path`` (defaults to ``CITATION.cff`` in the cwd) and ``--check``.
    2. Validate ``--date`` when provided; reject malformed values with exit 1.
    3. Read the CFF as UTF-8 bytes; exit 1 when the file cannot be read.
    4. With ``--check``: print OK and exit 0 when the CFF declares the expected
       version with a non-empty date-released, otherwise print FAIL to stderr
       and exit 1.
    5. Without ``--check``: replace the two fields, write the file back and
       print a confirmation; exit 1 with a clear message when a field is
       missing or the file cannot be written.

    Parameters
    ----------
    argv : list[str] | None, default=None
        CLI arguments; defaults to ``sys.argv[1:]`` when None.

    Returns
    -------
    int
        Exit code: 0 on success, 1 on any error.
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
        if check_citation_version(text, args.version):
            print(f"OK: {cff_path} declares version {args.version} with a date-released.")
            return 0
        print(
            f"FAIL: {cff_path} does not declare version {args.version} with a date-released.",
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
