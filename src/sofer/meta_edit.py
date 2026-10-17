"""Surgical ``[meta]`` editor for the dataset TOML (issue #323).

The metadata step of the canonical chain is the one step no tool could perform:
``sofer_validate`` warns while ``[meta]`` still carries the ``sofer init``
placeholders, ``_PHASED_INSTRUCTIONS`` tells the agent to fill them, and an MCP
consumer has no way to write a file. This module is the write half — the
registry of settable keys plus an editor that touches only the ``[meta]``
table.

**Why a surgical editor instead of a serializer.** The repository's only TOML
writer is :func:`sofer.scanner.write_toml`, which reserializes the whole
document with ``tomli_w``; applied to a dataset TOML that strips the ~60
comment lines the ``sofer init`` template writes as guidance (``cli.py:1049``).
The issue asks for the opposite: *"preserving every other key and the file's
formatting where the format allows"*. The project's TOML parser — :mod:`sofer._toml`,
which selects stdlib ``tomllib`` on Python 3.11+ and the ``tomli`` backport below
that — is the authority for the three questions a line scanner must not guess:

1. Which line is the real ``[meta]`` header — a line reading ``[meta]`` can sit
   inside a multi-line string of an earlier table.
2. Which line is a real top-level assignment of a key, for the same reason.
3. Where a value ends — a pre-existing multi-line array or ``\"\"\"`` string is
   replaced over its whole range, never by a first-line substitution.

Each question is answered by re-parsing the document prefix with
:func:`sofer._toml.loads`:
a prefix that is not valid TOML means the candidate line is inside an open
value, so it is skipped. The edited text is then parsed again and every
requested key is read back before :func:`set_meta` replaces the file, so a
refusal is always a refusal and never a half-written TOML.

Values are written single-line (basic strings with ``\\n`` escapes, inline
arrays, ``true``/``false``) so the file stays line-addressable and the diff
stays small; TOML basic-string escapes are a superset of JSON's, so
:func:`json.dumps` produces a valid, single-line TOML string for every value.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from . import _toml, config
from .model import DatasetConfig

MetaKind: TypeAlias = Literal["text", "list", "flag"]
"""Value kind of one settable ``[meta]`` key.

``text`` is a TOML string, ``list`` an array of strings, ``flag`` a boolean.
The kind decides how :func:`format_meta_value` renders the value and which
Python type :func:`apply_meta_edit` accepts for it.
"""


class MetaEditError(ValueError):
    """Raised when a ``[meta]`` edit cannot be performed safely.

    Every refusal is total: nothing is written, and the message names the key
    or the reason the caller can act on. ``MetaEditError`` covers an unreadable
    or unparseable TOML, an unknown key, a value of the wrong kind, and an edit
    whose result would not parse or would not carry the requested value.
    """


# ---------------------------------------------------------------------------
#  Key registry — one entry per [meta] key DatasetConfig reads
# ---------------------------------------------------------------------------

# Every key ``DatasetConfig.from_toml`` reads from the ``[meta]`` table
# (model.py: the ``meta.get(...)`` block), with the kind of value it holds.
# This IS the settable surface: a key the model reads but the registry omits
# could never be written by a tool, and a key the registry lists but the model
# does not read would be written into a void. Both directions are pinned by
# ``tests/test_meta_edit.py::TestRegistry`` (the forward guard parses a TOML
# per key and reads the attribute back; the reverse guard extracts the
# ``meta.get`` calls from the model source and compares the sets).
#
# The four path-valued keys (``readme``, ``codebook``, ``study_design``,
# ``recipe``) are ``str`` here even though the model types them ``str | None``
# and resolves them as paths: writing the path string is exactly what a TOML
# author does, and existence is checked by the validators, not here.
META_KEYS: Mapping[str, MetaKind] = MappingProxyType(
    {
        # -- the four the placeholder gate names (issue #288) -------------
        "description": "text",
        "license": "text",
        "source": "text",
        "tags": "list",
        # -- documentation files (paths, resolved by the card) ------------
        "readme": "text",
        "codebook": "text",
        "study_design": "text",
        "recipe": "text",
        # -- data-sharing / card fields -----------------------------------
        "confidential": "flag",
        "confidentiality_reason": "text",
        "language": "list",
        "pretty_name": "text",
        "task_categories": "list",
        "size_categories": "text",
        "citation": "text",
        "collection_method": "text",
        "csv_delimiter": "text",
        "csv_encoding": "text",
        "annotations_creators": "list",
        "language_creators": "list",
        "language_details": "list",
        "multilinguality": "text",
        "task_ids": "list",
        "paperswithcode_id": "text",
        "config_names": "list",
        "license_name": "text",
        "license_link": "text",
        "license_details": "text",
        "funded_by": "text",
        "shared_by": "text",
        "paper_url": "text",
        "demo_url": "text",
        "dataset_card_authors": "text",
        # -- card sections that used to be sentinels (issues #291, #314, #324)
        "repository": "text",
        "direct_use": "text",
        "out_of_scope_use": "text",
        "bias_risks_limitations": "text",
        "contact": "text",
        "curation_rationale": "text",
    }
)
"""The settable ``[meta]`` surface — one registry for CLI and MCP (issue #323).

``sofer meta set`` and ``sofer_meta_set`` both read this mapping, so the two
surfaces cannot accept different keys or disagree on a value's kind.
"""

_META_TABLE = "meta"
_META_HEADER = f"[{_META_TABLE}]"
_META_HEADER_RE = re.compile(r"^\[\s*(?:meta|\"meta\"|'meta')\s*\](?:\s*#.*)?$")
"""The ``[meta]`` table header, with an optional trailing comment.

Quoted spellings (``["meta"]``) and inner whitespace (``[ meta ]``) count: they
are the same table, and refusing one would mean appending a second ``[meta]``
table (which TOML rejects) for a document that is perfectly valid.
"""

_TABLE_LINE_RE = re.compile(r"^\s*\[")
"""A candidate table header line (validated by re-parsing, not by the regex)."""

_TRUE_WORDS: tuple[str, ...] = ("true",)
_FALSE_WORDS: tuple[str, ...] = ("false",)
"""The boolean spellings :func:`parse_meta_value` accepts for a ``flag`` key.

Module constants rather than literals inside the parser (AGENTS.md rule 1), so
the accepted set has one home and the error message cannot list a spelling the
parser rejects.
"""


def _assignment_re(key: str) -> re.Pattern[str]:
    """Return the pattern matching a top-level assignment of *key*.

    The quoted spellings (``"description" = ...``) are accepted too: they are
    valid TOML a human may have written, and not recognizing one would append a
    second assignment of the same key — which TOML rejects — for a document that
    parses. A recognized quoted key is replaced by the canonical unquoted form,
    so the edit also normalizes what it rewrote.

    Args:
        key: The registry key to locate.

    Returns:
        A pattern matching the assignment line.
    """
    escaped = re.escape(key)
    return re.compile(rf"^[ \t]*(?:{escaped}|\"{escaped}\"|'{escaped}')[ \t]*=")


def _parses(text: str) -> bool:
    """Return True when *text* is a complete, valid TOML document.

    The single authority behind every locator in this module: a document
    prefix that does not parse means the candidate line sits inside an open
    value (a multi-line string or array), which is exactly the case a regex
    cannot see.

    Args:
        text: Candidate TOML text.

    Returns:
        ``True`` when the TOML parser accepts the text.
    """
    try:
        _toml.loads(text)
    except ValueError:
        return False
    return True


def _parse(text: str) -> dict[str, Any]:
    """Parse *text* or raise :class:`MetaEditError` naming the failure.

    Args:
        text: The TOML document to parse.

    Returns:
        The parsed document.

    Raises:
        MetaEditError: The text is not a valid TOML document.
    """
    try:
        return _toml.loads(text)
    except ValueError as exc:
        raise MetaEditError(f"not a valid TOML document: {exc}") from exc


def _meta_table(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return the document's ``[meta]`` table as a mapping (``{}`` when absent).

    Args:
        document: A parsed TOML document.

    Returns:
        The ``meta`` table, or an empty mapping when the document has none.

    Raises:
        MetaEditError: ``meta`` exists but is not a table (e.g. ``meta = 5``),
            because no edit can be expressed for it.
    """
    value = document.get(_META_TABLE)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise MetaEditError(
            f"'{_META_TABLE}' is declared as {type(value).__name__}, not a table: cannot edit it"
        )
    return dict(value)


def format_meta_value(kind: MetaKind, value: Any) -> str:
    """Render *value* as a single-line TOML literal of *kind*.

    TOML basic-string escapes are a superset of JSON's, so ``json.dumps``
    produces a valid TOML string (``"`` and ``\\`` escaped, newlines as the
    literal two characters ``\\n``) and keeps the value on one line — which is
    what lets the editor address a value by line range.

    Args:
        kind: The key's declared kind.
        value: The value to render.

    Returns:
        The TOML literal, without the key or the ``=``.

    Raises:
        MetaEditError: *value* does not match *kind*.
    """
    if kind == "text":
        if not isinstance(value, str):
            raise MetaEditError(f"expected a string, got {type(value).__name__}")
        return json.dumps(value, ensure_ascii=False)
    if kind == "list":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise MetaEditError("expected a list of strings")
        items = ", ".join(json.dumps(item, ensure_ascii=False) for item in value)
        return f"[{items}]"
    if not isinstance(value, bool):
        raise MetaEditError(f"expected true or false, got {type(value).__name__}")
    return "true" if value else "false"


def _validate_keys(values: Mapping[str, Any]) -> dict[str, str]:
    """Validate *values* against the registry and render every literal.

    Args:
        values: ``{key: value}`` as supplied by the caller.

    Returns:
        ``{key: toml literal}``, in the caller's order.

    Raises:
        MetaEditError: A key is unknown, or a value does not match its kind.
            The message names the key and, for the kind mismatch, the accepted
            form.
    """
    rendered: dict[str, str] = {}
    for key, value in values.items():
        kind = META_KEYS.get(key)
        if kind is None:
            known = ", ".join(sorted(META_KEYS))
            raise MetaEditError(f"unknown [meta] key '{key}'; settable keys are: {known}")
        try:
            rendered[key] = format_meta_value(kind, value)
        except MetaEditError as exc:
            raise MetaEditError(f"[meta] {key}: {exc}") from exc
    return rendered


def parse_meta_value(key: str, raw: str) -> Any:
    """Return the typed value of a CLI ``--set KEY=VALUE`` assignment.

    The inverse of :func:`format_meta_value` for the one surface that receives
    its values as text (maintainer decision D9: one uniform ``--set`` flag
    instead of a flag per key, so all of :data:`META_KEYS` is reachable from
    the CLI). The registry kind decides the reading:

    - ``text``: the raw string, verbatim (commas and ``=`` included);
    - ``list``: comma-separated items, surrounding whitespace stripped, empty
      items dropped, so ``--set tags=`` writes ``[]``;
    - ``flag``: ``true`` or ``false``, case-insensitive, and nothing else.

    Keeping this here rather than in ``cli.py`` keeps the kind-to-text mapping
    in one module: the registry, its formatting and its parsing cannot drift.

    Args:
        key: The ``[meta]`` key being assigned.
        raw: The text after the first ``=`` on one ``--set`` argument.

    Returns:
        The typed value for :func:`apply_meta_edit`.

    Raises:
        MetaEditError: *key* is not registered, or *raw* cannot be read as its
            kind (a bad boolean spelling).
    """
    kind = META_KEYS.get(key)
    if kind is None:
        known = ", ".join(sorted(META_KEYS))
        raise MetaEditError(f"unknown [meta] key '{key}'; settable keys are: {known}")
    if kind == "text":
        return raw
    if kind == "list":
        return [item.strip() for item in raw.split(",") if item.strip()]
    word = raw.strip().lower()
    if word in _TRUE_WORDS:
        return True
    if word in _FALSE_WORDS:
        return False
    raise MetaEditError(
        f"[meta] {key}: expected 'true' or 'false', got {raw!r} "
        f"(accepted: {', '.join(_TRUE_WORDS + _FALSE_WORDS)})"
    )


def _literal_value(literal: str) -> Any:
    """Return the Python value a TOML literal denotes.

    The comparison key for "does this key already hold the requested value?" and
    for the edit's own read-back gate: both ask what the literal MEANS, never how
    it is spelled.

    Args:
        literal: A TOML literal produced by :func:`format_meta_value`.

    Returns:
        The parsed value.
    """
    return _toml.loads(f"v = {literal}")["v"]


# ---------------------------------------------------------------------------
#  Block and value location
# ---------------------------------------------------------------------------


def _eol_of(line: str) -> str:
    """Return *line*'s terminator as written (``""`` when it has none).

    Lines are kept **with** their terminators (:meth:`str.splitlines` with
    ``keepends=True``) so putting the document back together is a plain join
    and every byte outside an edited key survives, whatever mix of ``\\n`` and
    ``\\r\\n`` the file uses. This is what makes the byte-for-byte promise real
    rather than a promise about the native platform's newline.

    Args:
        line: One line, terminator included.

    Returns:
        ``"\\r\\n"``, ``"\\n"``, ``"\\r"`` or ``""``.
    """
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith(("\n", "\r")):
        return line[-1]
    return ""


def _document_eol(lines: list[str]) -> str:
    """Return the terminator a newly inserted line should carry.

    The first terminator the document uses, so a CRLF file stays CRLF and an
    LF file stays LF on the platform that does not use it natively. Defaults to
    ``"\\n"`` for a document with no terminator at all (a single bare line).

    Args:
        lines: The document split into lines, terminators kept.

    Returns:
        The terminator to append to an inserted line.
    """
    for line in lines:
        eol = _eol_of(line)
        if eol:
            return eol
    return "\n"


def _find_meta_header(lines: list[str]) -> int | None:
    """Return the index of the real ``[meta]`` header, or ``None``.

    A candidate is the real header only when everything before it parses as
    TOML, which is what rules out a ``[meta]`` line that happens to sit inside
    an earlier table's multi-line string.

    Args:
        lines: The document split into lines, terminators kept.

    Returns:
        The header's index, or ``None`` when the document has no ``[meta]``
        table.
    """
    for index, line in enumerate(lines):
        if not _META_HEADER_RE.match(line.strip()):
            continue
        if index == 0 or _parses("".join(lines[:index])):
            return index
    return None


def _meta_body_end(lines: list[str], header: int) -> int:
    """Return the exclusive end index of the ``[meta]`` table body.

    The body ends at the first following table header; a ``[...]``-looking
    line inside an open value of the block is skipped for the same reason as in
    :func:`_find_meta_header`.

    Args:
        lines: The document split into lines, terminators kept.
        header: Index of the ``[meta]`` header.

    Returns:
        The first index at or after ``header`` that is outside the table.
    """
    for index in range(header + 1, len(lines)):
        if not _TABLE_LINE_RE.match(lines[index]):
            continue
        if _parses("".join(lines[:index])):
            return index
    return len(lines)


def _find_assignment(lines: list[str], header: int, end: int, key: str) -> int | None:
    """Return the index of *key*'s real assignment line inside ``[meta]``.

    Args:
        lines: The document split into lines, terminators kept.
        header: Index of the ``[meta]`` header.
        end: Exclusive end index of the table body.
        key: The registry key to locate.

    Returns:
        The assignment's line index, or ``None`` when the key is not declared
        in ``[meta]``.
    """
    pattern = _assignment_re(key)
    for index in range(header + 1, end):
        if not pattern.match(lines[index]):
            continue
        if index == header + 1 or _parses("".join(lines[:index])):
            return index
    return None


def _value_end(lines: list[str], start: int, end: int, key: str) -> int:
    """Return the exclusive end index of *key*'s value, given its start line.

    Extends the candidate range one line at a time until the document prefix
    parses *and* carries ``meta.<key>``; the first such range ends the value.
    This is what replaces a multi-line array or string over its whole extent.

    Args:
        lines: The document split into lines, terminators kept.
        start: Index of the assignment line.
        end: Exclusive end index of the table body.
        key: The key being replaced.

    Returns:
        The exclusive end index of the value.

    Raises:
        MetaEditError: No range ending at or before *end* yields a parseable
            document carrying the key — the document is malformed in a way the
            caller must inspect by hand.
    """
    for stop in range(start + 1, end + 1):
        candidate = "".join(lines[:stop])
        if not _parses(candidate):
            continue
        if key in _meta_table(_toml.loads(candidate)):
            return stop
    raise MetaEditError(f"cannot locate the value of [meta] {key}; edit the file by hand")


# ---------------------------------------------------------------------------
#  The edit
# ---------------------------------------------------------------------------


def apply_meta_edit(text: str, values: Mapping[str, Any]) -> str:
    """Return *text* with every key in *values* written into its ``[meta]`` table.

    Only the ``[meta]`` table is touched: every other byte of the document —
    comments, blank lines, key order, unrelated tables — is preserved. Missing
    keys are appended to the end of the table; existing keys are replaced over
    their whole value range. The result is parsed again and each requested key
    is read back before it is returned, so a caller can never receive text that
    lost a value or broke the document.

    Args:
        text: The current TOML document.
        values: ``{key: value}`` to write; unknown keys and wrong value kinds
            are refused (see :data:`META_KEYS`).

    Returns:
        The edited document.

    Raises:
        MetaEditError: The input does not parse, a key or value is invalid, or
            the edited document would not parse or would not carry a requested
            value.
    """
    rendered = _validate_keys(values)
    if not rendered:
        return text
    document = _parse(text)
    current = _meta_table(document)
    lines = text.splitlines(keepends=True)
    header = _find_meta_header(lines)
    if header is None:
        if _META_TABLE in document:
            # A top-level `meta = { ... }` or `meta.description = ...` is the
            # same table in a form this editor does not address line by line.
            # Refusing with the reason beats appending a `[meta]` header and
            # letting `tomllib` report a duplicate declaration on a document
            # that is itself valid.
            raise MetaEditError(
                f"the document declares '{_META_TABLE}' without a [{_META_TABLE}] table "
                "header (an inline table or dotted keys); edit that form by hand"
            )
        return _append_meta_table(text, rendered)

    touched = False
    insertions: list[str] = []
    for key, literal in rendered.items():
        # The VALUE decides, not the line's bytes. A key that already holds the
        # requested value is left exactly as the author wrote it —
        # `description = """New"""`, `"description" = "New"` and
        # `description="New"` are all already correct, and rewriting them would
        # be formatting work the caller did not ask for (the verifier's
        # "stable only after one normalization write" counterexample).
        if key in current and current[key] == _literal_value(literal):
            continue
        end = _meta_body_end(lines, header)
        start = _find_assignment(lines, header, end, key)
        if start is None:
            insertions.append(f"{key} = {literal}")
            continue
        stop = _value_end(lines, start, end, key)
        # The replacement carries the terminator the assignment already had, so
        # rewriting a value can never change the document's line endings — and a
        # value that ended the file without a newline stays that way.
        terminator = _eol_of(lines[start])
        if stop > start + 1 and not _eol_of(lines[stop - 1]):
            terminator = ""
        new_line = f"{key} = {literal}{terminator}"
        if stop - start == 1 and lines[start] == new_line:
            continue
        lines = [*lines[:start], new_line, *lines[stop:]]
        touched = True

    if insertions:
        header = _find_meta_header(lines)
        assert header is not None  # the table existed before the loop
        at = _meta_body_end(lines, header)
        while at > header + 1 and (
            not lines[at - 1].strip() or lines[at - 1].lstrip().startswith("#")
        ):
            at -= 1
        # ``at >= header + 1 >= 1``: a header exists, so there is always a line
        # before the insertion point. An unterminated one ended the file and
        # must be terminated first, or the new key would land inside its value.
        eol = _eol_of(lines[at - 1])
        if not eol:
            eol = _document_eol(lines)
            lines[at - 1] = lines[at - 1] + eol
        lines = [*lines[:at], *(f"{line}{eol}" for line in insertions), *lines[at:]]
        touched = True

    # A no-op edit returns the input VERBATIM: re-running with the values the
    # file already holds must not even normalize a missing trailing newline,
    # or the idempotency the callers promise (no write, no ``.bak``) breaks.
    if not touched:
        return text
    result = "".join(lines)
    _verify_edit(result, rendered)
    _verify_posture_pair(result)
    return result


def _append_meta_table(text: str, rendered: Mapping[str, str]) -> str:
    """Return *text* with a new ``[meta]`` table appended at the end.

    Appending is always a valid position for a new top-level table, so a
    document without ``[meta]`` needs no header scan. The existing text is
    carried over byte for byte; the only bytes added are the one that puts the
    new table on its own line (when the file did not end with one), one blank
    line so the document reads like the hand-written file it is, and the table
    itself. The result is verified by the caller exactly like an in-place edit.

    Args:
        text: The current TOML document.
        rendered: ``{key: toml literal}`` to write.

    Returns:
        The edited document.
    """
    lines = text.splitlines(keepends=True)
    eol = _document_eol(lines)
    prefix = text
    if prefix and not _eol_of(lines[-1]):
        prefix += eol
    if prefix.strip():
        prefix += eol
    body = "".join(f"{key} = {literal}{eol}" for key, literal in rendered.items())
    result = f"{prefix}{_META_HEADER}{eol}{body}"
    _verify_edit(result, rendered)
    return result


def _verify_posture_pair(text: str) -> None:
    """Refuse a document whose confidentiality opt-out carries no reason (#338).

    ``[meta] confidential = false`` is an explicit posture change and needs its
    own authorization value. The editor writes one key per call, so the reason
    may arrive in this call or already be in the file; either state satisfies this
    check, and so does writing ``confidential = true``. Refusing **before** the
    atomic replace is what keeps the writer from leaving behind a config that
    ``DatasetConfig.validate()`` must reject.

    Args:
        text: The edited document, as it would be written.

    Raises:
        MetaEditError: When ``confidential`` is ``false`` and
            ``confidentiality_reason`` is missing or blank.
    """
    table = _meta_table(_parse(text))
    if table.get("confidential") is not False:
        return
    if str(table.get("confidentiality_reason") or "").strip():
        return
    raise MetaEditError(
        "[meta] confidential = false requires a non-empty confidentiality_reason — pass "
        'confidentiality_reason = "<why>" in the same write, or keep confidential = true.'
    )


def _verify_edit(text: str, rendered: Mapping[str, str]) -> None:
    """Assert the edited document parses and carries every requested value.

    The gate that makes every refusal total: an edit that would produce
    unparseable TOML — or drop a value the caller asked for — raises here,
    before anything is written.

    Args:
        text: The edited document.
        rendered: ``{key: toml literal}`` that must be present afterwards.

    Raises:
        MetaEditError: The document does not parse, or a requested key is
            absent or holds a different value.
    """
    document = _parse(text)
    table = _meta_table(document)
    for key, literal in rendered.items():
        expected = _literal_value(literal)
        if key not in table:
            raise MetaEditError(f"the edit would drop [meta] {key}; nothing written")
        if table[key] != expected:
            raise MetaEditError(
                f"the edit would store [meta] {key} as {table[key]!r}, not {expected!r}; "
                "nothing written"
            )


# ---------------------------------------------------------------------------
#  File-level API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetaWrite:
    """Outcome of one :func:`set_meta` call.

    Attributes:
        text: The document text after the edit (the input text when nothing
            changed, and the *planned* text under ``dry_run``).
        changed: Whether the edit would change the file.
        written: Keys whose value in the file changed, in the caller's order.
        unchanged: Keys already carrying the requested value.
        meta: The ``[meta]`` table after the edit.
        dry_run: Whether the write was suppressed.
    """

    text: str
    changed: bool
    written: tuple[str, ...]
    unchanged: tuple[str, ...]
    meta: dict[str, Any]
    dry_run: bool


def read_meta(path: str | Path) -> dict[str, Any]:
    """Return the dataset TOML's ``[meta]`` table as a mapping.

    Args:
        path: The dataset TOML path.

    Returns:
        The ``[meta]`` table; ``{}`` when the document declares none.

    Raises:
        MetaEditError: The file cannot be read, does not parse, or declares
            ``meta`` as something other than a table.
    """
    return _meta_table(_parse(_read_text(path)))


def _read_text(path: str | Path) -> str:
    """Return the dataset TOML's text, byte-faithfully.

    ``newline=""`` on purpose: Python's universal-newline mode translates
    ``\\r\\n`` to ``\\n`` while reading (and back while writing), which would
    rewrite every line of the file — not just the ``[meta]`` table — with the
    platform's native ending. The verifier caught exactly that on Windows with
    an LF document, which is why the promise is "byte for byte" and the I/O
    layer has to earn it.

    ``open`` is used rather than ``Path.read_text`` because the ``newline``
    argument only exists there from Python 3.13, and this package supports 3.10.

    Args:
        path: The dataset TOML path.

    Returns:
        The file's text, decoded with the configured output encoding and with
        line endings exactly as stored.

    Raises:
        MetaEditError: The file cannot be read.
    """
    try:
        with open(path, encoding=config.OUTPUT_ENCODING, newline="") as handle:
            return handle.read()
    except OSError as exc:
        raise MetaEditError(f"cannot read {path}: {exc}") from exc


def set_meta(
    path: str | Path,
    values: Mapping[str, Any],
    *,
    dry_run: bool = False,
) -> MetaWrite:
    """Write *values* into the ``[meta]`` table of the TOML at *path*.

    The document is edited in memory, verified, and then committed with a
    same-directory ``tmp`` file plus ``os.replace`` — a crash or failure
    mid-write can never leave a truncated TOML. No ``.bak`` is written: the
    edit is atomic, it is limited to the ``[meta]`` table, and every refusal
    happens before the replace (the same contract as ``scanner.write_toml``,
    the writer ``sofer scan --apply`` already uses on this file).

    Args:
        path: The dataset TOML path.
        values: ``{key: value}`` to write.
        dry_run: When ``True``, compute and verify the edit but write nothing.

    Returns:
        The :class:`MetaWrite` outcome.

    Raises:
        MetaEditError: See :func:`apply_meta_edit`.
    """
    target = Path(path)
    original = _read_text(target)
    updated = apply_meta_edit(original, values)
    before = _meta_table(_parse(original))
    after = _meta_table(_parse(updated))
    missing = object()
    written = tuple(key for key in values if before.get(key, missing) != after.get(key, missing))
    unchanged = tuple(key for key in values if key not in written)
    changed = updated != original
    if changed and not dry_run:
        _atomic_replace(target, updated)
    return MetaWrite(
        text=updated,
        changed=changed,
        written=written,
        unchanged=unchanged,
        meta=after,
        dry_run=dry_run,
    )


def _atomic_replace(path: Path, text: str) -> None:
    """Replace *path* with *text* through a same-directory temporary file.

    Args:
        path: The destination file.
        text: The complete new content.

    Raises:
        MetaEditError: The write failed; the destination is left untouched and
            the temporary file is removed.
    """
    tmp = path.with_name(path.name + ".tmp")
    try:
        # ``newline=""`` mirrors _read_text: no translation on write either, so
        # the bytes outside the edited table are the bytes that were read.
        with open(tmp, "w", encoding=config.OUTPUT_ENCODING, newline="") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise MetaEditError(f"cannot write {path}: {exc}") from exc


def build_predates_write(cfg: DatasetConfig, config_path: str | Path) -> str | None:
    """Return the note for a build tree that predates a ``[meta]`` write.

    ``sofer_prepare`` bakes ``[meta]`` into the Dataset Card and the LICENSE
    file under the configured ``build_dir``. Editing ``[meta]`` afterwards
    leaves those artifacts holding the old values, which is worth naming and
    not worth refusing: re-writing a value and re-running prepare is the normal
    loop (maintainer decision D7 — the same informational contract as the other
    stderr notes, and it never changes an exit code).

    Args:
        cfg: The dataset configuration that was loaded before the write.
        config_path: The dataset TOML path (the build directory is relative to
            its parent).

    Returns:
        A ready-to-print note, or ``None`` when no build tree exists.
    """
    build_dir = Path(config_path).parent / cfg.build_dir
    if not build_dir.is_dir():
        return None
    return (
        f"  !  the build tree at {build_dir} predates this write: the Dataset Card "
        "and LICENSE there still carry the previous [meta] values — re-run "
        "sofer_prepare to rebuild them"
    )
