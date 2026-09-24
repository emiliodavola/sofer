"""Central TOML-parser helper (issue #192).

Both selection arms are covered on any interpreter: the ``except`` branch is
reached by blocking stdlib ``tomllib`` in ``sys.modules`` and injecting a
fake ``tomli`` backport, so the coverage gate never depends on which Python
runs the suite.
"""

from __future__ import annotations

import io
import sys
import types

from sofer import _toml


def test_load_parses_toml_with_stdlib_parser() -> None:
    data = _toml.load(io.BytesIO(b"[tool.sofer]\nfoo = 1\n"))
    assert data == {"tool": {"sofer": {"foo": 1}}}


def test_load_falls_back_to_tomli_backport(monkeypatch) -> None:
    fake = types.ModuleType("tomli")
    fake.load = lambda fp: {"backport": True}  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tomli", fake)
    # `None` makes `import tomllib` raise ImportError.
    monkeypatch.setitem(sys.modules, "tomllib", None)
    assert _toml.load(io.BytesIO(b"ignored")) == {"backport": True}
