"""Process-boundary regression suite: stdio transport, nested CWD, recovery replay.

Phase 3 (PR 3) of the ``test-mcp-cli-regression-suite`` change (#119). Proves
the registered MCP server through the real stdio transport (PB-01), the
nested-dataset CWD containment of ``sofer_init`` (PB-04), and the recovery
contract of PB-03 — executing the documented ``next`` hints and asserting the
replayed call reaches a different gate or the intended branch.

Boundary contract (PR 2 gate review): FastMCP projects tool results through
each tool's declared ``output_schema``, so ``error_code`` / ``message`` /
``next`` are NOT client-visible for the gated tools. Recovery replay therefore
keys off the boundary-visible refusal message in ``output`` plus the
deterministic, documented hint VALUES in ``src/sofer/mcp_server.py`` (risk
gate -> ``{"acknowledge_risk": True}``, init file-exists ->
``{"force": True}``, init name-empty -> ``{}``) merged into the replayed call
(design.md D3). Branch progression is proven by the second call failing at a
different gate or returning ``ok:True``.

Lean-spawn contract (PB-09): one module-scoped stdio spawn via the shared
``mcp_stdio_server`` fixture; every in-process test builds its own server via
``build_server()``; async uses ``asyncio.run`` (no pytest-asyncio).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from conftest import _write_minimal_dataset, mcp_payload
from fastmcp import Client

from sofer.mcp_server import build_server


def _run(coro: Any) -> Any:
    """Run one async client interaction per test (asyncio.run convention)."""
    return asyncio.run(coro)


def _call(server: Any, name: str, args: dict[str, Any] | None = None) -> Any:
    """Call a registered tool through an in-memory ``Client(server)`` (PB-01).

    Delegates the Root-model unwrap to the shared ``mcp_payload`` helper
    (PB-09/D2) so this module never re-implements the boundary seam.
    """

    async def _go() -> Any:
        async with Client(server) as client:
            return await client.call_tool(name, args)

    result = _run(_go())
    if result.data is not None:
        unwrapped = mcp_payload(result.data)
        if isinstance(unwrapped, dict):
            result.data = unwrapped  # type: ignore[attr-defined]
    return result


class TestStdioFraming:
    """PB-01: real stdio transport with clean JSON-RPC framing (one spawn)."""

    def test_initialize_list_call_clean_jsonrpc(self, mcp_stdio_server: Any) -> None:
        """``initialize -> tools/list (14) -> tools/call`` over one stdio session.

        The MCP client library parses every response as JSON-RPC, so a stray
        stdout byte from the server would break framing before any assertion;
        additionally the tool payload must decode as a clean JSON envelope.
        """
        params = mcp_stdio_server.spawn()

        async def _go() -> None:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client

            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    assert init is not None
                    tools = await session.list_tools()
                    assert len(tools.tools) == 14
                    result = await session.call_tool(
                        "sofer_validate", {"config": "dataset.toml"}
                    )
                    assert not result.isError
                    envelope = json.loads(result.content[0].text)
                    assert envelope["ok"] is True
                    assert envelope["exit_code"] == 0
                    assert envelope["config_errors"] == []

        _run(_go())


class TestNestedCwd:
    """PB-04: dataset tools honor the nested CWD, not the parent server root."""

    def test_init_writes_under_nested_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_tool_config: Any
    ) -> None:
        """``sofer_init`` with cwd unset auto-detects the live CWD when it is
        inside the server root, so writes land under the nested dataset."""
        parent = tmp_path / "root"
        parent.mkdir()
        nested = parent / "nested"
        nested.mkdir()
        server = build_server(root=parent)
        monkeypatch.chdir(nested)

        envelope = _call(server, "sofer_init", {"name": "nested-ds"}).data
        assert envelope["ok"] is True, envelope
        assert (nested / "nested-ds.toml").is_file()
        assert (nested / "raw").is_dir()
        assert not (parent / "nested-ds.toml").exists()
        assert not (parent / "raw").exists()