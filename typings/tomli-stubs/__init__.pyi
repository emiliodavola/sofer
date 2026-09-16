"""Stub for the marker-only ``tomli`` backport (``tomli>=2.0; python_version < '3.11'``).

``tomli`` is absent from the 3.13 gate interpreter *by design* (AGENTS.md rule 12):
installing it there would make the fallback arm dead on the pinned interpreter and
break the ``cli.py`` COV-06 row. Four of the five modules that select the TOML
parser (`cli.py`, `config.py`, `mcp_registration.py`, `model.py`) still name it
behind a ``try`` / ``except ImportError``, so the **pyright** gate needs a
declaration for them (`mcp_server.py` is version-gated, so a static checker prunes
its ``tomli`` arm; mypy resolves the rest through the global
`ignore_missing_imports = true` — COR-1). Only ``load`` is modelled — the one
entry point those modules use.
"""

from typing import Any, BinaryIO

def load(fp: BinaryIO, /) -> dict[str, Any]: ...
