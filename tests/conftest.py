"""
Shared pytest fixtures for the sofer test suite.

Provides ``pytree``, a factory fixture that builds temporary
``pyproject.toml`` layouts (with or without a ``[tool.sofer]`` section,
nested trees), and ``restore_tool_config``, which snapshots and restores the
``sofer.config`` module constants around tests that call ``config.reload()``
so global state never leaks between tests.

Also hosts the shared process-boundary helpers (PB-01..PB-09): ``mcp_payload``
(the Root-model unwrap), ``call_tool`` (shared client-boundary call wrapper),
``run_cli`` (executable CLI subprocess), the module-scoped
``mcp_stdio_server`` fixture (one stdio spawn config per module), and
``_make_dataset`` (canonical minimal-dataset helper — the single home for the
fixture logic, AGENTS.md rule 4).
Sibling test modules reuse these helpers instead of re-implementing them.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
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

#: Shared wall-clock budget (seconds) for subprocess/stdio boundaries: the
#: ``run_cli`` subprocess timeout and the stdio ``read_timeout_seconds``
#: values. Test-harness config — a conftest constant is the right home
#: (AGENTS.md rule 1), not ``sofer.config``.
PROCESS_TIMEOUT_SECONDS = 30.0


def mcp_payload(result: Any) -> Any:
    """Unwrap a FastMCP Root model to the full envelope dict when ``output_schema`` is set.

    FastMCP wraps tool results in a Root model whose single field holds the
    tool's envelope when the tool declares an ``output_schema``. This shared
    helper (PB-09) peels that wrapper so tests assert against plain dicts
    (``ok``/``exit_code``/``output``/``next``/``config_errors`` ...). It is the
    single home for the unwrap logic — module-level unwrappers delegate here
    (D2) instead of re-implementing it.

    The unwrap is deliberately NON-LOSSY: the whole envelope is returned
    WITHOUT field filtering, so future schema fields added to an envelope
    survive into assertions instead of being silently dropped by an allowlist.
    Three wrapper shapes are unwrapped: a pydantic ``RootModel`` whose ``root``
    value is the envelope dict, a pydantic model exposing ``model_dump()``, and
    FastMCP's ``types.Root`` dataclass whose fields ARE the envelope.

    Args:
        result: The raw ``CallToolResult.data`` value from a client call.

    Returns:
        The full envelope dict for the wrapper shapes above; ``None``
        unchanged; otherwise the input unchanged.
    """
    if result is None:
        return None
    root = getattr(result, "root", None)
    if isinstance(root, dict):
        # pydantic RootModel — the root value IS the whole envelope.
        return root
    if hasattr(result, "model_dump"):
        dumped = result.model_dump()
        if isinstance(dumped, dict) and "root" in dumped and len(dumped) == 1:
            # model_dump() wraps the envelope under a single "root" key.
            return dumped["root"]
        return dumped
    if is_dataclass(result) and not isinstance(result, type):
        # FastMCP types.Root — the dataclass fields ARE the envelope fields;
        # asdict() converts every field non-lossily (no allowlist to go stale).
        return asdict(result)
    return result


def call_tool(server: Any, name: str, arguments: dict[str, Any] | None = None) -> Any:
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
    timeout: float | None = PROCESS_TIMEOUT_SECONDS,
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
        timeout: Wall-clock budget for the subprocess; ``None`` disables it.
            Defaults to 30s so a hung CLI fails the test loudly via
            ``TimeoutExpired`` (PB-02 hardening) instead of stalling CI.

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
        timeout=timeout,
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


def _make_dataset(root: Path, *, confidential: bool = False, name: str = "test-ds") -> Path:
    """Write a minimal, quality-passing dataset (TOML + CSV) under *root*.

    Single canonical home for the minimal-dataset helper (AGENTS.md rule 4):
    ``tests/test_mcp_server.py`` imports it from here, and the module-scoped
    ``mcp_stdio_server`` fixture uses it for its server root. The CSV uses the
    default ``;`` delimiter and the TOML declares one registered ``[[file]]``.

    Args:
        root: Directory the dataset files are written into.
        confidential: Value for the ``[meta] confidential`` flag.
        name: Dataset name for the ``[dataset] name`` field.

    Returns:
        The written ``dataset.toml`` path.
    """
    (root / "data.csv").write_text("col_a;col_b\n1;2\n3;4\n", encoding="utf-8-sig")
    lines = [
        "[dataset]",
        f'name = "{name}"',
        'repo_id = "user/test-ds"',
        "",
        "[meta]",
        f"confidential = {str(confidential).lower()}",
        "",
        "[[file]]",
        'local = "data.csv"',
        'remote = "data.csv"',
        "",
    ]
    toml = root / "dataset.toml"
    toml.write_text("\n".join(lines), encoding="utf-8")
    return toml


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
    _make_dataset(root)
    return McpStdioServer(cwd=root)
