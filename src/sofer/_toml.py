"""Central TOML-parser selection (issue #192).

Single home for the ``tomli``/``tomllib`` fallback previously duplicated in
five modules (``cli.py``, ``config.py``, ``mcp_registration.py``,
``mcp_server.py``, ``model.py``). On Python 3.11+ the parser is stdlib
``tomllib``; below that it is the conditional ``tomli`` backport
(``pyproject.toml`` declares ``tomli>=2.0; python_version < '3.11'``).

Both arms stay reachable from tests on any interpreter -- the ``except``
branch is exercised by blocking ``tomllib`` via ``sys.modules`` -- so this
module measures 100% line+branch coverage wherever the suite runs, and the
two imports never share one name (no ``no-redef``).
"""

from __future__ import annotations

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
