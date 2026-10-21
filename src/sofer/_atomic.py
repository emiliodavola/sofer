"""Single home for same-directory atomic file replacement (issues #365, #371).

Three writers used to own their own temporary-file mechanics: the surgical TOML
editors (:mod:`sofer.meta_edit`, :mod:`sofer.file_edit`), the scanner's
:func:`sofer.scanner.write_toml`, and MCP client-config registration
(:mod:`sofer.mcp_registration`). Fixing a staging-hazard in one of them never
reached the other two, and their cleanup behaviour had already started to
diverge.

This module owns exactly one policy: create a staging file that belongs to this
call, write through the handle it owns, close it, then replace the destination
with :func:`os.replace`. Serialization stays in the callers -- TOML, JSON and
YAML documents have different byte-preservation contracts -- and so do their
error translation, backups, merging and authorization logic.

The staging file is never a predictable ``<destination>.tmp`` sibling: that path
may already hold the user's data or another writer's staging file, and opening
it would follow a symlink and truncate its target. It is created exclusively by
the interpreter's temporary-file API in the destination's own directory (so the
replacement cannot cross a mount), and it is removed on any failure, not only
on :class:`OSError`.
"""

from __future__ import annotations

import contextlib
import os
import stat
import tempfile
from pathlib import Path

_STAGING_PREFIX = ".sofer-"
"""Prefix of the staging file :func:`atomic_write_text` creates.

The name is deliberately independent of the destination's name: a staging file
that repeated it grew the basename by fourteen characters, which would push a
242-character destination - writable before - past ``NAME_MAX``.
"""

_STAGING_SUFFIX = ".tmp"
"""Suffix that keeps a leftover staging file recognizable as such."""


def _destination_mode(path: Path) -> int | None:
    """Return *path*'s permission bits, or ``None`` when it does not exist.

    Best effort by design: a destination whose metadata cannot be read is still
    written, and the new file then keeps the restrictive mode the temporary-file
    API gives it. Failing the write here would turn a preservation nicety into a
    new restriction, which issue #365 rules out.
    """
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None


def _copy_mode(staging: Path, mode: int | None) -> None:
    """Give *staging* the destination's permission bits, when they are known.

    Also best effort: a filesystem that refuses ``chmod`` (some SMB, FUSE or NFS
    mounts do) must not turn a write the previous writer completed into a hard
    failure. The replacement then keeps the staging mode (``0600``), which
    matches what the previous writer left for an ordinary destination, is wider
    than a destination narrower than ``0600`` (a read-only ``0400``, say) and
    narrower than a group- or world-readable one. Nothing in the return value
    reports that the carry-over failed.
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


def atomic_write_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str | None = "",
) -> None:
    """Replace *path* with *text* through an exclusively created temporary file.

    No ``.bak`` is written: the replace is atomic and every refusal happens
    before it. The staging file is unique to this call and its name does not
    grow with the destination (issue #365): a fixed ``<destination>.tmp``
    sibling is never opened. It is removed on any failure, not only on
    ``OSError``, so an interruption does not leave one behind; a cleanup the
    filesystem itself refuses is swallowed, and that file stays.

    The destination's existing permission bits are carried over to the new file
    when the filesystem allows ``chmod``. A destination that does not exist yet
    keeps the mode the temporary-file API assigns (``0600``). No ``fsync`` is
    issued, so this guarantees atomic replacement, not durability across a power
    loss.

    Args:
        path: The destination file.
        text: The complete new content.
        encoding: Text encoding for the write.
        newline: Newline translation policy, passed to :func:`open` unchanged.
            The default ``""`` suppresses translation, so the bytes outside an
            edited region are the bytes that were read (CRLF documents stay
            CRLF) and serialized text lands exactly as produced. Callers whose
            pre-existing contract relies on platform translation (the MCP
            registration JSON branch, the scanner's TOML writer) pass ``None``
            explicitly; this module never normalizes one policy into the other.

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
            newline=newline,
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
