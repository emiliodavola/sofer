"""Surgical ``[[file]]`` editor for the dataset TOML (issue #344).

The ``sofer init`` template advertises a recursive folder entry, and
:class:`sofer.model.FileEntry` implements ``recursive``,
``convert_to_parquet``/``upload_as_csv``, ``include_in_schema`` and
``column_types`` downstream — but no MCP tool could write any of them. The
only writer of ``[[file]]`` blocks was ``scanner.merge_entries``, which emits
one flat entry per discovered file, so a fully MCP-driven run could reach the
template's own folder shape only by leaving the tool surface.

**Why a surgical editor instead of a serializer.** The repository's only TOML
writer is :func:`sofer.scanner.write_toml`, which reserializes the whole
document with ``tomli_w``; applied to a dataset TOML it strips the guidance
comments ``sofer init`` writes. This editor replaces exactly the
``[[file]]`` array-of-tables region and leaves every other byte alone — the
same contract as :mod:`sofer.meta_edit` for ``[meta]``.

The region is located by re-parsing document prefixes with
:func:`sofer._toml.loads`: a prefix that does not parse means the candidate
line sits inside an open multi-line value, so it is skipped. The edited text
is parsed again and the ``[[file]]`` list is read back before it is returned,
so a caller can never receive text that lost an entry or broke another table.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from . import _toml, config

FileKind: TypeAlias = Literal["text", "flag", "table"]
"""Value kind of one settable ``[[file]]`` key."""

FILE_KEYS: Mapping[str, FileKind] = MappingProxyType(
    {
        "local": "text",
        "remote": "text",
        "recursive": "flag",
        "convert_to_parquet": "flag",
        "upload_as_csv": "flag",
        "include_in_schema": "flag",
        "column_types": "table",
    }
)
"""The settable surface — one entry per ``[[file]]`` key the model reads."""

REQUIRED_FILE_KEYS: tuple[str, ...] = ("local", "remote")

_FILE_TABLE = "file"
_FILE_HEADER_RE = re.compile(r"^[ \t]*\[\[file\]\][ \t]*(?:#.*)?\r?$")
_ANY_HEADER_RE = re.compile(r"^[ \t]*\[\[?[A-Za-z0-9_.\-]+\]\]?[ \t]*(?:#.*)?\r?$")


class FileEditError(ValueError):
    """Raised when a ``[[file]]`` edit cannot be performed safely.

    Every refusal is total: nothing is written, and the message names the
    entry or the reason the caller can act on.
    """


@dataclass(frozen=True)
class FileWrite:
    """Outcome of one :func:`set_files` call.

    Attributes:
        text: The document text after the edit (the planned text under
            ``dry_run``).
        changed: Whether the edit would change the file.
        entries: The normalized entries the document carries after the edit.
        dry_run: Whether the write was suppressed.
    """

    text: str
    changed: bool
    entries: tuple[dict[str, Any], ...]
    dry_run: bool


def normalize_entries(raw_entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate and canonicalize ``[[file]]`` entries.

    Args:
        raw_entries: The caller's entries. Each one is a mapping of
            :data:`FILE_KEYS`; ``local`` and ``remote`` are required.

    Returns:
        Entries in canonical key order (required keys first, then the optional
        keys in registry order).

    Raises:
        FileEditError: A key is unknown, a value has the wrong kind, or a
            required key is missing or blank.
    """
    if isinstance(raw_entries, (str, bytes)) or not isinstance(raw_entries, Sequence):
        raise FileEditError("entries must be an array of [[file]] tables")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_entries, start=1):
        if not isinstance(raw, Mapping):
            raise FileEditError(f"entry {index} must be a table of [[file]] keys")
        unknown = sorted(key for key in raw if key not in FILE_KEYS)
        if unknown:
            raise FileEditError(
                f"entry {index} has unknown key(s) {', '.join(unknown)}; "
                f"accepted: {', '.join(FILE_KEYS)}"
            )
        entry: dict[str, Any] = {}
        for key, kind in FILE_KEYS.items():
            if key not in raw:
                continue
            value = raw[key]
            if kind == "text":
                if not isinstance(value, str) or not value.strip():
                    raise FileEditError(f"entry {index}: '{key}' must be a non-empty string")
                entry[key] = value.strip()
            elif kind == "flag":
                if not isinstance(value, bool):
                    raise FileEditError(f"entry {index}: '{key}' must be true or false")
                entry[key] = value
            else:
                entry[key] = _normalize_column_types(index, value)
        for key in REQUIRED_FILE_KEYS:
            if key not in entry:
                raise FileEditError(f"entry {index}: '{key}' is required")
        normalized.append(entry)
    return normalized


def _normalize_column_types(index: int, value: Any) -> dict[str, str]:
    """Validate one ``column_types`` table against the accepted vocabulary."""
    if not isinstance(value, Mapping):
        raise FileEditError(
            f"entry {index}: 'column_types' must be a table of {{column = \"type\"}}"
        )
    accepted = ", ".join(sorted(config.COLUMN_TYPES_SUPPORTED))
    result: dict[str, str] = {}
    for column, type_name in value.items():
        if not isinstance(column, str) or not column.strip():
            raise FileEditError(f"entry {index}: column_types keys must be non-empty strings")
        if not isinstance(type_name, str) or type_name not in config.COLUMN_TYPES_SUPPORTED:
            raise FileEditError(
                f"entry {index}: column_types[{column!r}] must be one of {accepted} "
                f"(got {type_name!r})"
            )
        result[column] = type_name
    return result


def apply_file_edit(text: str, entries: Sequence[Mapping[str, Any]]) -> str:
    """Return *text* with its ``[[file]]`` array replaced by *entries*.

    Every other byte of the document — comments, blank lines, key order,
    unrelated tables — is preserved. The result is parsed again, the
    ``[[file]]`` list is read back, and every other top-level table is compared
    against the input before the text is returned.

    Args:
        text: The current TOML document.
        entries: The complete replacement list of ``[[file]]`` tables.

    Returns:
        The edited document.

    Raises:
        FileEditError: The input does not parse, an entry is invalid, or the
            edit would not carry the requested entries or would change another
            table.
    """
    normalized = normalize_entries(entries)
    document = _parse(text)
    lines = text.splitlines(keepends=True)
    start, end = _find_file_region(lines, document)
    rendered = _render_entries(normalized)
    if start is None:
        if _FILE_TABLE in document:
            raise FileEditError(
                "the document declares 'file' without a [[file]] table header "
                "(an inline array or dotted keys); edit that form by hand"
            )
        prefix = text if (not text or text.endswith("\n")) else text + "\n"
        updated = f"{prefix}\n{rendered}"
    else:
        updated = "".join(lines[:start]) + rendered + "".join(lines[end:])
    _verify(document, updated, normalized)
    return updated


def _render_entries(entries: Sequence[Mapping[str, Any]]) -> str:
    """Render entries as ``[[file]]`` blocks (``tomli_w`` writes inline arrays).

    Values are rendered with :func:`json.dumps`: JSON basic strings are a
    subset of TOML basic strings (``"`` and ``\\`` escaped, non-ASCII as
    ``\\uXXXX``), so every legal ``local``/``remote``/column name round-trips.
    """
    blocks: list[str] = []
    for entry in entries:
        lines = ["[[file]]"]
        for key, value in entry.items():
            if key == "column_types":
                inner = ", ".join(
                    f"{json.dumps(column)} = {json.dumps(type_name)}"
                    for column, type_name in value.items()
                )
                lines.append(f"column_types = {{ {inner} }}")
            elif isinstance(value, bool):
                lines.append(f"{key} = {'true' if value else 'false'}")
            else:
                lines.append(f"{key} = {json.dumps(value)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n" if blocks else ""


def set_files(
    path: str | Path,
    entries: Sequence[Mapping[str, Any]],
    *,
    dry_run: bool = False,
) -> FileWrite:
    """Write *entries* into the ``[[file]]`` array of the TOML at *path*.

    The document is edited in memory, verified, and then committed with a
    same-directory temporary file plus ``os.replace`` — a crash or failure
    mid-write can never leave a truncated TOML. No ``.bak`` is written: the
    edit is atomic and every refusal happens before the replace.

    Args:
        path: The dataset TOML path.
        entries: The complete replacement list of ``[[file]]`` tables.
        dry_run: When ``True``, compute and verify the edit but write nothing.

    Returns:
        The :class:`FileWrite` outcome.

    Raises:
        FileEditError: The file cannot be read, the document would not parse,
            an entry is invalid, or the edit would change another table.
    """
    target = Path(path)
    original = _read_text(target)
    normalized = normalize_entries(entries)
    updated = apply_file_edit(original, normalized)
    changed = updated != original
    if changed and not dry_run:
        try:
            _toml.atomic_write_text(target, updated, encoding=config.OUTPUT_ENCODING)
        except OSError as exc:
            raise FileEditError(f"cannot write {target}: {exc}") from exc
    return FileWrite(
        text=updated,
        changed=changed,
        entries=tuple(normalized),
        dry_run=dry_run,
    )


def _read_text(path: Path) -> str:
    """Read the document preserving its line endings."""
    try:
        with open(path, encoding=config.OUTPUT_ENCODING, newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise FileEditError(f"cannot read {path}: {exc}") from exc


def _parse(text: str) -> dict[str, Any]:
    """Parse *text*, mapping a decode error to :class:`FileEditError`."""
    try:
        return _toml.loads(text)
    except Exception as exc:  # both parsers raise a ValueError subclass
        raise FileEditError(f"the document is not valid TOML: {exc}") from exc


def _prefix_parses(lines: Sequence[str], end: int) -> dict[str, Any] | None:
    """Return the parsed prefix ``lines[:end]``, or ``None`` when it does not parse."""
    try:
        return _toml.loads("".join(lines[:end]))
    except Exception:
        return None


def _find_file_region(lines: Sequence[str], document: Mapping[str, Any]) -> tuple[int | None, int]:
    """Locate the ``[[file]]`` array-of-tables region.

    Args:
        lines: The document as lines, line endings preserved.
        document: The parsed document.

    Returns:
        ``(start, end)`` line indices: ``start`` is the first real ``[[file]]``
        header (``None`` when the document has none) and ``end`` is the first
        line after the last entry's content, so trailing comments and blank
        lines are never consumed.
    """
    start: int | None = None
    first_boundary = len(lines)
    for index, line in enumerate(lines):
        if not _ANY_HEADER_RE.match(line):
            continue
        if _prefix_parses(lines, index) is None:
            continue
        is_file_header = bool(_FILE_HEADER_RE.match(line))
        if is_file_header:
            if start is None:
                start = index
            elif index > first_boundary:
                raise FileEditError(
                    "the [[file]] entries are not a contiguous region in this document; "
                    "edit that form by hand"
                )
            continue
        if start is not None and first_boundary == len(lines):
            first_boundary = index
    if start is None:
        return None, 0
    target = document.get(_FILE_TABLE, [])
    for end in range(start + 1, first_boundary + 1):
        parsed = _prefix_parses(lines, end)
        if parsed is not None and parsed.get(_FILE_TABLE, []) == target:
            return start, end
    return start, first_boundary


def _verify(
    before: Mapping[str, Any], updated: str, normalized: Sequence[Mapping[str, Any]]
) -> None:
    """Refuse an edit that lost entries or changed another top-level table."""
    try:
        after = _toml.loads(updated)
    except Exception as exc:
        raise FileEditError(f"the edited document would not parse: {exc}") from exc
    if after.get(_FILE_TABLE, []) != list(normalized):
        raise FileEditError("the edited document would not carry the requested [[file]] entries")
    before_rest = {key: value for key, value in before.items() if key != _FILE_TABLE}
    after_rest = {key: value for key, value in after.items() if key != _FILE_TABLE}
    if before_rest != after_rest:
        raise FileEditError(
            "the [[file]] entries are not a contiguous region in this document; "
            "edit that form by hand"
        )
