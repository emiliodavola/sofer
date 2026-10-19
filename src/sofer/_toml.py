"""Central TOML-parser selection and atomic document writes (issues #192, #344).

Single home for the ``tomli``/``tomllib`` fallback previously duplicated in
five modules (``cli.py``, ``config.py``, ``mcp_registration.py``,
``mcp_server.py``, ``model.py``). On Python 3.11+ the parser is stdlib
``tomllib``; below that it is the conditional ``tomli`` backport
(``pyproject.toml`` declares ``tomli>=2.0; python_version < '3.11'``).

Both arms stay reachable from tests on any interpreter -- the ``except``
branch is exercised by blocking ``tomllib`` via ``sys.modules`` -- so this
module measures 100% line+branch coverage wherever the suite runs, and the
two imports never share one name (no ``no-redef``).

:func:`atomic_write_text` is the single home for the same-directory
temporary-file replacement shared by the surgical TOML editors
(:mod:`sofer.meta_edit`, :mod:`sofer.file_edit`): a crash or failure mid-write
can never leave a truncated document.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, BinaryIO


def _parser() -> Any:
    """Return the TOML parser module for this interpreter."""
    try:
        import tomllib as _stdlib_parser

        return _stdlib_parser
    except ImportError:  # Python < 3.11: the backport is a hard dependency there.
        import tomli as _backport_parser

        return _backport_parser


def load(fp: BinaryIO) -> dict[str, Any]:
    """Parse TOML from an open binary file object.

    Mirrors :func:`tomllib.load`; decode errors propagate to the caller.
    """
    data: dict[str, Any] = _parser().load(fp)
    return data


def loads(text: str) -> dict[str, Any]:
    """Parse TOML from a string.

    Mirrors :func:`tomllib.loads`. Added for the ``[meta]`` editor (issue #323),
    which re-parses document prefixes to decide where a table, an assignment and
    a value end — the same selection applies there as everywhere else, so the
    editor does not import ``tomllib`` directly and break on Python 3.10, where
    only the ``tomli`` backport exists.

    Decode errors propagate to the caller. Both parsers raise a ``ValueError``
    subclass (``tomllib.TOMLDecodeError`` / ``tomli.TOMLDecodeError``), so a
    caller that only needs "this text is not TOML" can catch ``ValueError``.
    """
    data: dict[str, Any] = _parser().loads(text)
    return data


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Replace *path* with *text* through a same-directory temporary file.

    No ``.bak`` is written: the replace is atomic and every refusal happens
    before it. ``newline=""`` suppresses translation, so the bytes outside the
    edited region are the bytes that were read (CRLF documents stay CRLF).

    Args:
        path: The destination file.
        text: The complete new content.
        encoding: Text encoding for the write.

    Raises:
        OSError: The write failed; the destination is left untouched and the
            temporary file is removed.
    """
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
