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
                    result = await session.call_tool("sofer_validate", {"config": "dataset.toml"})
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


class TestRecoveryPublishConfirm:
    """PB-03: replay the documented risk-gate hint past the risk gate."""

    def test_replay_acknowledge_risk_progresses_to_approval_gate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_tool_config: Any
    ) -> None:
        """First call refused at the risk gate; the replayed call (with the
        documented ``acknowledge_risk=True`` hint, token still present) must
        be refused at the APPROVAL gate — the literal next check AFTER the
        risk gate in ``sofer_publish_confirm`` (mcp_server.py) — proving the
        risk gate accepted the acknowledgment and progression continued.

        (A token-stripped replay cannot prove this: the token check is pinned
        BEFORE the risk gate, so it would only show a different gate by
        ordering, never that ``acknowledge_risk=True`` was accepted.)
        """
        _write_minimal_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        server = build_server(root=tmp_path, approval_phrase="s3cret")
        args: dict[str, Any] = {"config": str(tmp_path / "dataset.toml")}

        first = _call(server, "sofer_publish_confirm", args).data
        assert first["ok"] is False
        assert first["acknowledge_risk"] is False
        # Boundary-visible refusal (output_schema drops error_code/next): the
        # reason is the human-readable message naming the required hint.
        assert "acknowledge_risk=True" in first["output"]

        # Replay with the documented next hint for the risk gate (mcp_server
        # risk gate: {"acknowledge_risk": True}); the token is STILL present.
        replayed = _call(server, "sofer_publish_confirm", {**args, "acknowledge_risk": True}).data
        assert replayed["ok"] is False
        # The approval gate (the next check after risk) refuses now — not the
        # risk message — proving the risk gate accepted the acknowledgment.
        assert "approval phrase" in replayed["output"].lower()
        assert "acknowledge_risk=True" not in replayed["output"]


class TestRecoveryInit:
    """PB-03: init refusals replayed with the documented corrections."""

    def test_replay_force_past_file_exists(self, tmp_path: Path, restore_tool_config: Any) -> None:
        """File-exists refusal replayed with the documented ``force=True``
        hint reaches the intended branch (template overwritten)."""
        from sofer.cli import _INIT_TEMPLATE

        server = build_server(root=tmp_path)
        args: dict[str, Any] = {"name": "my-ds"}

        first = _call(server, "sofer_init", args).data
        assert first["ok"] is True
        (tmp_path / "my-ds.toml").write_text("custom", encoding="utf-8")

        refused = _call(server, "sofer_init", args).data
        assert refused["ok"] is False
        assert refused["exit_code"] == 1
        assert any("File already exists" in e for e in refused["config_errors"])

        # Documented next hint for the file-exists refusal (mcp_server.py:
        # {"force": True}) merged into the replayed args.
        replayed = _call(server, "sofer_init", {**args, "force": True}).data
        assert replayed["ok"] is True
        expected = _INIT_TEMPLATE.format(name="my-ds", user="YOUR_USER")
        assert (tmp_path / "my-ds.toml").read_text(encoding="utf-8") == expected

    def test_replay_corrected_name_past_name_empty(
        self, tmp_path: Path, restore_tool_config: Any
    ) -> None:
        """Name-empty refusal (documented hint ``{}``) replayed with a
        corrected non-empty name reaches the intended branch."""
        from sofer.cli import _INIT_TEMPLATE

        server = build_server(root=tmp_path)

        refused = _call(server, "sofer_init", {"name": "   "}).data
        assert refused["ok"] is False
        assert refused["exit_code"] == 1
        assert any("non-empty" in e for e in refused["config_errors"])
        assert not list(tmp_path.glob("*.toml"))

        # Documented next hint for the name-empty refusal is {} — the
        # correction is a non-empty name in the replayed args.
        replayed = _call(server, "sofer_init", {"name": "my-ds"}).data
        assert replayed["ok"] is True
        expected = _INIT_TEMPLATE.format(name="my-ds", user="YOUR_USER")
        assert (tmp_path / "my-ds.toml").read_text(encoding="utf-8") == expected
