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
can never leave a truncated document. The staging file is created exclusively
by each call (issue #365) - a predictable ``<destination>.tmp`` sibling is
never opened, because it may already belong to the user or to another writer.
"""

from __future__ import annotations

import contextlib
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, BinaryIO

_STAGING_PREFIX = ".sofer-"
"""Prefix of the staging file :func:`atomic_write_text` creates.

The name is deliberately independent of the destination's name: a staging
file that repeated it grew the basename by fourteen characters, which would
push a 242-character destination - writable before - past ``NAME_MAX``.
"""

_STAGING_SUFFIX = ".tmp"
"""Suffix that keeps a leftover staging file recognizable as such."""


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


def _destination_mode(path: Path) -> int | None:
    """Return *path*'s permission bits, or ``None`` when it does not exist.

    Best effort by design: a destination whose metadata cannot be read is
    still written, and the new file then keeps the restrictive mode the
    temporary-file API gives it. Failing the write here would turn a
    preservation nicety into a new restriction, which issue #365 rules out.
    """
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None


def _copy_mode(staging: Path, mode: int | None) -> None:
    """Give *staging* the destination's permission bits, when they are known.

    Also best effort: a filesystem that refuses ``chmod`` (some SMB, FUSE or
    NFS mounts do) must not turn a write the previous writer completed into a
    hard failure. The file then keeps the staging mode, which is never wider
    than the destination's.
    """
    if mode is None:
        return
    with contextlib.suppress(OSError):
        os.chmod(staging, mode)


def _discard(staging: Path) -> None:
    """Remove the staging file this call created, ignoring a cleanup failure.

    Cleanup must not mask the exception already propagating, and the path is
    ours alone by construction.
    """
    with contextlib.suppress(OSError):
        staging.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Replace *path* with *text* through an exclusively created temporary file.

    No ``.bak`` is written: the replace is atomic and every refusal happens
    before it. ``newline=""`` suppresses translation, so the bytes outside the
    edited region are the bytes that were read (CRLF documents stay CRLF).

    The staging file is unique to this call and its name does not grow with
    the destination (issue #365): a fixed ``<destination>.tmp`` sibling is
    never opened. That path may already hold the user's data or another
    writer's staging file, and opening it would also follow a symlink and
    truncate its target. The staging file is removed on any failure, not only
    on ``OSError``, so an intervention cannot leave a unique orphan behind.

    The destination's existing permission bits are carried over to the new
    file. A destination that does not exist yet keeps the mode the
    temporary-file API assigns (``0600``), which is never wider than before.
    No ``fsync`` is issued, so this guarantees atomic replacement, not
    durability across a power loss.

    Args:
        path: The destination file.
        text: The complete new content.
        encoding: Text encoding for the write.

    Raises:
        OSError: The write failed; the destination is left untouched and the
            temporary file this call created is removed.
    """
    mode = _destination_mode(path)
    staging: Path | None = None
    replaced = False
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline="",
            dir=path.parent,
            prefix=_STAGING_PREFIX,
            suffix=_STAGING_SUFFIX,
            delete=False,
        ) as handle:
            staging = Path(handle.name)
            handle.write(text)
        _copy_mode(staging, mode)
        os.replace(staging, path)
        replaced = True
    finally:
        if not replaced and staging is not None:
            _discard(staging)
