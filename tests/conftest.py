"""
Shared pytest fixtures for the sofer test suite.

Provides ``pytree``, a factory fixture that builds temporary
``pyproject.toml`` layouts (with or without a ``[tool.sofer]`` section,
nested trees), and ``restore_tool_config``, which snapshots and restores the
``sofer.config`` module constants around tests that call ``config.reload()``
so global state never leaks between tests.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import sofer.config as config


@pytest.fixture
def pytree(tmp_path: Path) -> Callable[..., Path]:
    """Return a factory building temp ``pyproject.toml`` layouts under tmp_path.

    The factory creates the requested directory (and parents) inside the
    per-test ``tmp_path``, optionally writing a ``pyproject.toml`` into it.

    Usage:
        root = pytree()                                   # bare tree, no file
        root = pytree("[tool.sofer]\\ncsv_delimiter = ','")  # tree with section
        root = pytree('[project]\\nname = "x"')             # section-less file
        leaf = pytree(None, at="a/b/c")                   # nested dir, no file

    Args:
        toml: Full text of the pyproject.toml to write; ``None`` writes no
            file at all.
        at: Relative subdirectory of the tree where the directory/file is
            created; defaults to the tree root.

    Returns:
        The created directory as a :class:`~pathlib.Path`.
    """

    def _make(toml: str | None = None, *, at: str = ".") -> Path:
        target = tmp_path / at
        target.mkdir(parents=True, exist_ok=True)
        if toml is not None:
            (target / "pyproject.toml").write_text(toml, encoding="utf-8")
        return target

    return _make


@pytest.fixture
def restore_tool_config():
    """Snapshot ``sofer.config`` module constants; restore them on teardown.

    Tests that call :func:`sofer.config.reload` mutate process-wide state —
    this fixture guarantees each test starts from the pristine import-time
    defaults regardless of what a previous test reloaded.
    """
    saved = {key: getattr(config, key.upper()) for key in config._DEFAULTS}
    saved_source = config.SOURCE_PATH
    yield
    for key, value in saved.items():
        setattr(config, key.upper(), value)
    config.SOURCE_PATH = saved_source
