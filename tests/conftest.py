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
``mcp_stdio_server`` fixture (one stdio spawn config per module) and its
parent-root sibling ``mcp_stdio_parent_root`` (the PB-09 second fixture for
the parent-root/child-cwd layout), and ``_make_dataset`` (canonical
minimal-dataset helper — the single home for the fixture logic, AGENTS.md
rule 4).
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


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``reads_cwd_dotenv`` marker (opt-out of the #207 isolation)."""
    config.addinivalue_line(
        "markers",
        "reads_cwd_dotenv: test deliberately reads a `.env` from its own cwd "
        "(opts out of the #207 ambient-dotenv isolation).",
    )


@pytest.fixture(autouse=True)
def _isolate_cwd_dotenv(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Neutralize the ambient ``.env`` for tests that do not opt in (#207).

    ``sofer.mcp_server._read_dotenv_values`` merges two legs: an explicit
    ``Path.cwd() / ".env"`` read and a bare ``dotenv_values()`` fallback
    whose ``find_dotenv(usecwd=False)`` is *caller-file-anchored* — i.e. it
    resolves to the repository-root ``.env`` whenever the suite runs from
    the checkout, regardless of ``chdir``. So a developer-local ``.env``
    used to flip token-resolution tests (PB-06: deterministic and offline).
    Stubbing the read — rather than root-anchoring the load (a
    product-behaviour change) or ``chdir``-ing each test (which cannot
    escape the caller-anchored leg) — keeps production untouched. Tests
    that deliberately exercise ``.env`` reads opt out with
    ``@pytest.mark.reads_cwd_dotenv``; for them the fallback leg is scoped
    to their own ``tmp_path`` so the ambient repository ``.env`` cannot
    merge in either.
    """
    if request.node.get_closest_marker("reads_cwd_dotenv") is not None:
        scoped = request.getfixturevalue("tmp_path")

        def _scoped_find_dotenv(*args: object, **kwargs: object) -> str:
            return os.fspath(scoped / ".env")

        monkeypatch.setattr("dotenv.main.find_dotenv", _scoped_find_dotenv)
        return
    import sofer.mcp_server as mcp_server

    def _empty_dotenv() -> dict[str, str]:
        return {}

    monkeypatch.setattr(mcp_server, "_read_dotenv_values", _empty_dotenv)


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

    command: str | None = None
    """Executable to spawn; ``None`` (default) uses ``sys.executable`` with
    *args*. Set to a console-script path (e.g. ``shutil.which("sofer-mcp")``)
    to prove the installed entry point instead of the checkout module."""

    def spawn(self) -> StdioServerParameters:
        """Return stdio parameters for one client session (one spawn each)."""
        return StdioServerParameters(
            command=self.command or sys.executable,
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


@pytest.fixture(scope="module")
def mcp_stdio_parent_root(tmp_path_factory: pytest.TempPathFactory) -> McpStdioServer:
    """Yield one stdio server spawn config per module for the parent-root layout (PB-09).

    Second module-scoped stdio fixture — PB-09 permits one extra fixture for
    the parent-root/child-cwd layout. Creates a parent server-root directory
    containing an existing ``child/`` dataset directory and returns the spawn
    configuration for ``sofer.mcp_server.main()`` with server root = parent.
    One spawn per module (lean-spawn bound). Used by
    ``TestParentRootIdentity`` (PB-04) to prove the ground-truth reproduction:
    ``cwd=None`` at the parent root fails closed naming ``cwd``, while
    ``cwd="child"`` anchors identity under ``child/``.
    """
    parent = tmp_path_factory.mktemp("mcp-stdio-parent")
    (parent / "child").mkdir()
    return McpStdioServer(cwd=parent)
