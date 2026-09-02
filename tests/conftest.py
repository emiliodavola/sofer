"""
Shared pytest fixtures for the sofer test suite.

Provides ``pytree``, a factory fixture that builds temporary
``pyproject.toml`` layouts (with or without a ``[tool.sofer]`` section,
nested trees), and ``restore_tool_config``, which snapshots and restores the
``sofer.config`` module constants around tests that call ``config.reload()``
so global state never leaks between tests.

Also hosts the shared process-boundary helpers (PB-01..PB-09): ``mcp_payload``
(the Root-model unwrap), ``call_tool`` (shared client-boundary call wrapper),
``run_cli`` (executable CLI subprocess), and the module-scoped
``mcp_stdio_server`` fixture (one stdio spawn config per module).
Sibling test modules reuse these helpers instead of re-implementing them.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client
from mcp import StdioServerParameters

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


# ---------------------------------------------------------------------------
#  Process-boundary helpers (PB-01..PB-09)
# ---------------------------------------------------------------------------


def mcp_payload(result: Any) -> Any:
    """Unwrap a FastMCP Root model to a plain dict when ``output_schema`` is set.

    FastMCP wraps tool results in a Root model whose single field holds the
    tool's envelope when the tool declares an ``output_schema``. This shared
    helper (PB-09) peels that wrapper so tests assert against plain dicts
    (``ok``/``exit_code``/``output``/``next``/``config_errors`` ...). It is the
    single home for the unwrap logic — module-level unwrappers delegate here
    (D2) instead of re-implementing it.

    Args:
        result: The raw ``CallToolResult.data`` value from a client call.

    Returns:
        A plain dict when the result is a Root model carrying known envelope
        fields; otherwise the unwrapped ``root`` value or the input unchanged.
    """
    if result is None:
        return None
    if hasattr(result, "ok") and not isinstance(result, dict):
        try:
            unwrapped: dict[str, Any] = {}
            for key in (
                "ok",
                "exit_code",
                "output",
                "config_errors",
                "error_code",
                "message",
                "next",
                "passed",
                "errors",
                "warnings",
                "quality_failures",
                "quality_warnings",
                "ran_checks",
                "confidential",
                "target",
                "dry_run",
                "acknowledge_risk",
                "acknowledge_confidential",
                "skipped_protected",
                "partial",
                "files",
                "pii_findings",
                "discovered",
                "registered",
                "copied",
                "output_path",
                "token",
                "requires_ack_confidential",
                "requires_approval_phrase",
            ):
                if hasattr(result, key):
                    unwrapped[key] = getattr(result, key)
            if unwrapped:
                return unwrapped
        except Exception:
            pass
    if hasattr(result, "model_dump"):
        try:
            dumped = getattr(result, "model_dump")()
            if isinstance(dumped, dict) and "root" in dumped and len(dumped) == 1:
                return dumped["root"]
            return dumped
        except Exception:
            pass
    if hasattr(result, "root"):
        return getattr(result, "root")
    return result


def call_tool(
    server: Any, name: str, arguments: dict[str, Any] | None = None
) -> Any:
    """Call a registered tool through an in-memory ``Client(server)`` (PB-01).

    Shared implementation of the client-boundary call wrapper (PB-09): opens a
    ``Client(server)`` context, invokes ``client.call_tool(name, arguments)``,
    and delegates the Root-model unwrap to :func:`mcp_payload`. Sibling
    modules keep a module-local ``_call`` thin alias that delegates here
    (AGENTS.md rule 4 — the wrapper lives in exactly one place).

    Args:
        server: The FastMCP server instance to connect an in-memory client to.
        name: The registered tool name (e.g. ``"sofer_validate"``).
        arguments: Tool input arguments; ``None`` for tools that take none.

    Returns:
        The ``CallToolResult`` with ``data`` unwrapped to a plain dict when
        the result carries an envelope (via :func:`mcp_payload`).
    """

    async def _go() -> Any:
        async with Client(server) as client:
            return await client.call_tool(name, arguments)

    result = asyncio.run(_go())
    if result.data is not None:
        unwrapped = mcp_payload(result.data)
        if isinstance(unwrapped, dict):
            result.data = unwrapped  # type: ignore[attr-defined]
    return result


def run_cli(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    encoding: str = "utf-8",
) -> subprocess.CompletedProcess[str]:
    """Run the sofer CLI as an executable subprocess (PB-02).

    Spawns ``[sys.executable, "-m", "sofer.cli", ...]`` so user-visible output
    (help text, dispatch errors) is observed through the same boundary real
    users hit, never through in-process parser calls. The caller asserts on the
    returned process (exit code, stdout, stderr); this helper never asserts
    itself, so both the rc 0 ``--help`` path and the rc 2 unknown-command path
    work. Decoding is strict so encoding regressions (e.g. non-cp1252 glyphs)
    fail loudly instead of silently substituting.

    Args:
        argv: CLI arguments after ``sofer.cli`` (e.g. ``["--help"]``).
        cwd: Working directory for the subprocess.
        env: Extra environment variables layered over ``os.environ``.
        encoding: Text decoding used for stdout/stderr (e.g. ``"cp1252"``).

    Returns:
        The completed subprocess result with text-mode stdout/stderr.
    """
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "sofer.cli", *argv],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        encoding=encoding,
        errors="strict",
        check=False,
    )


@dataclass(frozen=True)
class McpStdioServer:
    """Spawn configuration for the module-scoped stdio server (PB-09).

    One stdio subprocess serves exactly one client session, so ``spawn()``
    returns parameters for a fresh subprocess per session. The fixture that
    yields this object is module-scoped: the server-root cwd (with a minimal
    dataset) is created once per module, bounding subprocess wall-clock to one
    spawn per module instead of one per test (PB-09 lean-spawn bound).
    """

    cwd: Path
    """Server-root working directory; becomes the subprocess server root."""

    args: tuple[str, ...] = ("-c", "from sofer.mcp_server import main; main()")
    """Python args invoking the MCP server entry point over stdio."""

    def spawn(self) -> StdioServerParameters:
        """Return stdio parameters for one client session (one spawn each)."""
        return StdioServerParameters(
            command=sys.executable,
            args=list(self.args),
            cwd=str(self.cwd),
        )


def _write_minimal_dataset(root: Path) -> None:
    """Write a minimal quality-passing dataset (TOML + CSV) under *root*."""
    (root / "data.csv").write_text("col_a;col_b\n1;2\n3;4\n", encoding="utf-8-sig")
    (root / "dataset.toml").write_text(
        "\n".join(
            [
                "[dataset]",
                'name = "test-ds"',
                'repo_id = "user/test-ds"',
                "",
                "[meta]",
                "confidential = false",
                "",
                "[[file]]",
                'local = "data.csv"',
                'remote = "data.csv"',
                "",
            ]
        ),
        encoding="utf-8",
    )


@pytest.fixture(scope="module")
def mcp_stdio_server(tmp_path_factory: pytest.TempPathFactory) -> McpStdioServer:
    """Yield one stdio server spawn config per module (PB-09).

    Creates a single server-root directory per module containing a minimal
    quality-passing dataset, and returns the spawn configuration for
    ``sofer.mcp_server.main()``. Because one stdio subprocess serves exactly
    one client session, each session calls ``spawn()`` for a fresh subprocess;
    the fixture itself is created once per module, honoring the lean-spawn
    bound (never one subprocess per test).
    """
    root = tmp_path_factory.mktemp("mcp-stdio")
    _write_minimal_dataset(root)
    return McpStdioServer(cwd=root)
