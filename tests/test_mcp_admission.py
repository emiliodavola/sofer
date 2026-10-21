"""Init admission gate (issue #360) — public-boundary regression matrix.

Covers the normative contract in issue #360: D1/D2 (session meaning and
default-deny), D3 (create/attach mode), D4 (state machine and concurrency), D5
(matching and resources), D6 (refusal envelopes), and the E1-E14 acceptance
examples through the real MCP client boundary. The framework lifecycle proof
(FastMCP 4.0.11 session identity) lives in :class:`TestFrameworkLifecycle`.

Every test drives a real ``Client``; direct Python calls bypass the dispatch
middleware by design and are never used to prove the gate.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import PROCESS_TIMEOUT_SECONDS, _make_dataset
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_context

from sofer import mcp_admission as admission
from sofer import mcp_server as ms

#: Every non-init tool with arguments valid enough to reach a handler. The gate
#: must refuse all of them BEFORE any handler runs, so these are the strongest
#: possible probes for D2.
VALID_ARGS: dict[str, dict[str, Any]] = {
    "sofer_validate": {"config": "dataset.toml"},
    "sofer_meta_check": {"config": "dataset.toml"},
    "sofer_meta_set": {"config": "dataset.toml", "values": {"license": "MIT"}},
    "sofer_file_set": {"config": "dataset.toml", "entries": []},
    "sofer_prepare": {"config": "dataset.toml"},
    "sofer_publish": {"config": "dataset.toml", "dry_run": True},
    "sofer_publish_confirm": {"config": "dataset.toml"},
    "sofer_codebook": {"path": "data.csv"},
    "sofer_codebook_all": {"config": "dataset.toml"},
    "sofer_profile": {"dataset": "data.csv"},
    "sofer_profile_all": {"config": "dataset.toml"},
    "sofer_render": {"package": "metadata.yaml"},
    "sofer_render_all": {"config": "dataset.toml"},
    "sofer_auth_status": {"config": "dataset.toml"},
    "sofer_repo_settings": {"config": "dataset.toml"},
    "sofer_scan_dry_run": {"config": "dataset.toml"},
    "sofer_scan_apply": {"config": "dataset.toml"},
    "sofer_report_failure": {"error": "boom"},
}

NON_INIT_TOOLS: tuple[str, ...] = tuple(VALID_ARGS)


@pytest.fixture(autouse=True)
def _restore(restore_tool_config: Any) -> Iterator[None]:
    """Keep the global ``sofer.config`` state pristine (TOML parsing mutates it)."""
    yield


def _run(coro: Any) -> Any:
    """Run one async client interaction per test (asyncio.run convention)."""
    return asyncio.run(coro)


async def _call(client: Client, name: str, arguments: dict[str, Any] | None) -> Any:
    """Call one tool and return its full envelope."""
    result = await client.call_tool(name, arguments or {})
    return result.structured_content


def _tree(root: Path) -> dict[str, str]:
    """Hash every file under *root* (relative POSIX path -> sha256)."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_config(
    root: Path,
    filename: str = "dataset.toml",
    *,
    name: str = "atlas",
    user: str = "myuser",
    files: str = "",
    meta: str = "",
) -> Path:
    """Write a model-valid dataset TOML with a controllable filename."""
    body = f'[dataset]\nname = "{name}"\nrepo_id = "{user}/{name}"\n\n[meta]\n{meta}'
    if files:
        body += "\n" + files
    path = root / filename
    path.write_text(body, encoding="utf-8")
    return path


async def _attach(client: Client, config: str = "dataset.toml", **extra: Any) -> Any:
    """Attach the session through the real gate and return the envelope."""
    return await _call(client, "sofer_init", {"config": config, **extra})


async def _resource_error(coro: Any) -> dict[str, Any]:
    """Await a resource read that must fail and parse its JSON envelope."""
    from mcp.shared.exceptions import MCPError

    with pytest.raises(MCPError) as excinfo:
        await coro
    return json.loads(str(excinfo.value))


class TestFrameworkLifecycle:
    """D8: the harness session holder is stable per session and fresh after it.

    FastMCP 4.0.11 builds a request-scoped ``Connection`` per request on the
    modern protocol but one server-owned ``outbound`` channel per live client
    session. sofer stores admission state on that channel; this test fails
    loudly if an upgrade changes the lifecycle the design depends on.
    """

    def test_outbound_channel_is_session_scoped(self) -> None:
        import fastmcp

        probe_server = FastMCP("probe")

        @probe_server.tool
        def probe() -> list[int]:
            ctx = get_context()
            request = ctx.request_context
            assert request is not None
            connection = request.session._connection
            return [id(connection.outbound), id(connection)]

        async def _go() -> tuple[list[int], list[int], list[int]]:
            async with Client(probe_server) as client:
                first = await client.call_tool("probe", {})
                second = await client.call_tool("probe", {})
            async with Client(probe_server) as other:
                fresh = await other.call_tool("probe", {})
            return first.data, second.data, fresh.data  # type: ignore[return-value]

        first, second, fresh = _run(_go())
        assert first[0] == second[0], (
            f"fastmcp {fastmcp.__version__}: outbound channel changed within one "
            "session; the admission-state holder is no longer session-scoped"
        )
        assert first[0] != fresh[0], "a new client session must get a fresh holder"


class TestDefaultDeny:
    """D1/D2 + T1: every non-init tool is refused before its handler."""

    @pytest.mark.parametrize("tool", NON_INIT_TOOLS)
    def test_every_non_init_tool_is_refused_before_init(self, tmp_path: Path, tool: str) -> None:
        _make_dataset(tmp_path)
        server = ms.build_server(root=tmp_path)
        before = _tree(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(server) as client:
                return await _call(client, tool, VALID_ARGS[tool])

        envelope = _run(_go())
        assert envelope["ok"] is False, envelope
        assert envelope["exit_code"] == 1
        assert envelope["error_code"] == "INITIALIZATION_REQUIRED", envelope
        assert envelope["config_errors"] == []
        assert envelope["next"]["tool"] == "sofer_init"
        assert _tree(tmp_path) == before, f"{tool} mutated the tree before init"

    @pytest.mark.parametrize(
        "tool",
        ["sofer_validate", "sofer_codebook", "sofer_prepare", "sofer_scan_apply"],
    )
    def test_invalid_business_arguments_are_still_refused(self, tmp_path: Path, tool: str) -> None:
        _make_dataset(tmp_path)
        server = ms.build_server(root=tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(server) as client:
                return await _call(client, tool, {})

        envelope = _run(_go())
        assert envelope["error_code"] == "INITIALIZATION_REQUIRED", envelope

    def test_unknown_tool_keeps_the_framework_error_and_never_unlocks(self, tmp_path: Path) -> None:
        _make_dataset(tmp_path)
        server = ms.build_server(root=tmp_path)

        async def _go() -> tuple[str, dict[str, Any]]:
            async with Client(server) as client:
                with pytest.raises(ToolError, match="Unknown tool"):
                    await client.call_tool("not_a_sofer_tool", {})
                return await _call(client, "sofer_validate", {"config": "dataset.toml"})

        assert _run(_go())["error_code"] == "INITIALIZATION_REQUIRED"

    def test_discovery_is_available_without_init(self, tmp_path: Path) -> None:
        _make_dataset(tmp_path)
        server = ms.build_server(root=tmp_path)

        async def _go() -> tuple[int, int, int, str, str, dict[str, Any]]:
            async with Client(server) as client:
                tools = len(await client.list_tools())
                resources = len(await client.list_resources())
                prompts = len(await client.list_prompts())
                prompt = await client.get_prompt("prepare_dataset", {"config": "dataset.toml"})
                status = await client.read_resource("sofer://status")
                refused = await _call(client, "sofer_validate", {"config": "dataset.toml"})
                return (  # type: ignore[return-value]
                    tools,
                    resources,
                    prompts,
                    prompt.messages[0].content.text,  # type: ignore[union-attr]
                    status[0].text,  # type: ignore[union-attr]
                    refused,
                )

        tools, resources, prompts, prompt_text, status_text, refused = _run(_go())
        assert tools == 19
        assert resources >= 1
        assert prompts == 3
        assert "sofer_init" in prompt_text
        assert "approval_configured" in status_text
        assert refused["error_code"] == "INITIALIZATION_REQUIRED"


class TestModeContract:
    """D3 + T3: create vs attach and the read-only attach contract."""

    def test_attach_without_identity_and_nonstandard_filename(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "custom.toml")

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                attached = await _attach(client, "custom.toml")
                checked = await _call(client, "sofer_meta_check", {"config": "custom.toml"})
                return attached, checked

        attached, checked = _run(_go())
        assert attached["ok"] is True, attached
        assert attached["session_ready"] is True
        assert attached["initialization_mode"] == "attach"
        assert attached["config_path"] == str((tmp_path / "custom.toml").resolve())
        assert attached["dataset_root"] == str(tmp_path.resolve())
        assert attached["next"]["tool"] == "sofer_meta_check"
        assert checked["ok"] is True, checked

    def test_attach_writes_nothing(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "custom.toml")
        before = _tree(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _attach(client, "custom.toml")

        assert _run(_go())["session_ready"] is True
        assert _tree(tmp_path) == before

    @pytest.mark.parametrize(
        ("extra", "fragment"),
        [
            ({"cwd": "."}, "cwd"),
            ({"force": True}, "force"),
            ({"move_existing": True}, "move_existing"),
        ],
    )
    def test_attach_rejects_create_only_options(
        self, tmp_path: Path, extra: dict[str, Any], fragment: str
    ) -> None:
        _write_config(tmp_path)
        before = _tree(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _attach(client, "dataset.toml", **extra)

        envelope = _run(_go())
        assert envelope["ok"] is False
        assert envelope["error_code"] == "CONFIG_ERROR"
        assert any(fragment in error for error in envelope["config_errors"]), envelope
        assert envelope["session_ready"] is False
        assert _tree(tmp_path) == before

    def test_empty_config_is_not_create_mode(self, tmp_path: Path) -> None:
        before = _tree(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _call(client, "sofer_init", {"config": "   "})

        envelope = _run(_go())
        assert envelope["ok"] is False
        assert envelope["error_code"] == "CONFIG_ERROR"
        assert envelope["initialization_mode"] == "attach"
        assert not (tmp_path / "fixture-dataset.toml").exists()
        assert _tree(tmp_path) == before

    def test_missing_config_never_falls_back_to_create(self, tmp_path: Path) -> None:
        before = _tree(tmp_path)

        async def _go() -> None:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _call(client, "sofer_init", {"config": "absent.toml"})

        with pytest.raises(ToolError, match="config not found"):
            _run(_go())
        assert _tree(tmp_path) == before

    @pytest.mark.parametrize(
        ("extra", "fragment"),
        [
            ({"name": "beta"}, "name assertion mismatch"),
            ({"user": "someone-else"}, "user assertion mismatch"),
            ({"name": "  "}, "name must be non-empty"),
        ],
    )
    def test_identity_assertions_must_match_exactly(
        self, tmp_path: Path, extra: dict[str, Any], fragment: str
    ) -> None:
        _write_config(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _attach(client, "dataset.toml", **extra)

        envelope = _run(_go())
        assert envelope["ok"] is False
        assert any(fragment in error for error in envelope["config_errors"]), envelope

    def test_malformed_toml_is_an_attach_refusal(self, tmp_path: Path) -> None:
        (tmp_path / "broken.toml").write_text("[dataset\nname = 1\n", encoding="utf-8")

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _attach(client, "broken.toml")

        envelope = _run(_go())
        assert envelope["ok"] is False
        assert "Failed to read TOML" in envelope["config_errors"][0]
        assert envelope["session_ready"] is False

    @pytest.mark.parametrize(
        "files",
        [
            "",  # empty [[file]]
            '[[file]]\nlocal = "missing.csv"\nremote = "missing.csv"\n',  # missing source
        ],
    )
    def test_repairable_conditions_do_not_block_attach(self, tmp_path: Path, files: str) -> None:
        _write_config(tmp_path, files=files)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _attach(client, "dataset.toml")

        envelope = _run(_go())
        assert envelope["ok"] is True, envelope
        assert envelope["session_ready"] is True

    def test_create_requires_name_and_user(self, tmp_path: Path) -> None:
        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _call(client, "sofer_init", {"cwd": "."})

        envelope = _run(_go())
        assert envelope["ok"] is False
        assert envelope["error_code"] == "CONFIG_ERROR"
        assert envelope["initialization_mode"] == "create"
        assert envelope["session_ready"] is False

    def test_create_success_is_ready_and_points_at_scan(self, tmp_path: Path) -> None:
        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _call(
                    client,
                    "sofer_init",
                    {"name": "fresh", "user": "myuser", "cwd": "."},
                )

        envelope = _run(_go())
        assert envelope["ok"] is True, envelope
        assert envelope["session_ready"] is True
        assert envelope["initialization_mode"] == "create"
        assert envelope["next"]["tool"] == "sofer_scan_dry_run"
        assert (tmp_path / "fresh.toml").exists()

    @pytest.mark.parametrize("mode", ["create", "attach"])
    def test_preview_never_grants_readiness(self, tmp_path: Path, mode: str) -> None:
        _write_config(tmp_path)
        before = _tree(tmp_path)

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                if mode == "attach":
                    preview = await _call(
                        client, "sofer_init", {"config": "dataset.toml", "dry_run": True}
                    )
                else:
                    preview = await _call(
                        client,
                        "sofer_init",
                        {"name": "fresh", "user": "myuser", "cwd": ".", "dry_run": True},
                    )
                refused = await _call(client, "sofer_validate", {"config": "dataset.toml"})
                return preview, refused

        preview, refused = _run(_go())
        assert preview["ok"] is True
        assert preview["session_ready"] is False
        assert preview["next"]["tool"] == "sofer_init"
        assert preview["next"]["arguments"]["dry_run"] is False
        assert refused["error_code"] == "INITIALIZATION_REQUIRED"
        assert _tree(tmp_path) == before


class TestStateTransitions:
    """D4 + T4: U / I / R(A) transitions, no cached readiness."""

    def test_preview_from_ready_locks_both_targets(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "a.toml", name="alpha")
        _write_config(tmp_path, "b.toml", name="beta")

        async def _go() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml")
                preview = await _call(client, "sofer_init", {"config": "b.toml", "dry_run": True})
                a_call = await _call(client, "sofer_meta_check", {"config": "a.toml"})
                b_call = await _call(client, "sofer_meta_check", {"config": "b.toml"})
                return preview, a_call, b_call

        preview, a_call, b_call = _run(_go())
        assert preview["session_ready"] is False
        assert a_call["error_code"] == "INITIALIZATION_REQUIRED"
        assert b_call["error_code"] == "INITIALIZATION_REQUIRED"

    def test_ordinary_mismatch_preserves_the_active_context(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "a.toml", name="alpha")
        _write_config(tmp_path, "b.toml", name="beta")

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml")
                mismatched = await _call(client, "sofer_meta_check", {"config": "b.toml"})
                admitted = await _call(client, "sofer_meta_check", {"config": "a.toml"})
                return mismatched, admitted

        mismatched, admitted = _run(_go())
        assert mismatched["error_code"] == "INITIALIZATION_CONTEXT_MISMATCH"
        assert admitted["ok"] is True

    def test_a_to_b_to_a_requires_explicit_reinit(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "a.toml", name="alpha")
        _write_config(tmp_path, "b.toml", name="beta")

        async def _go() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml")
                await _attach(client, "b.toml")
                back = await _call(client, "sofer_meta_check", {"config": "a.toml"})
                reattached = await _attach(client, "a.toml")
                admitted = await _call(client, "sofer_meta_check", {"config": "a.toml"})
                return back, reattached, admitted

        back, reattached, admitted = _run(_go())
        assert back["error_code"] == "INITIALIZATION_CONTEXT_MISMATCH"
        assert reattached["session_ready"] is True
        assert admitted["ok"] is True

    def test_failed_attach_from_ready_leaves_uninitialized(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "a.toml", name="alpha")
        _write_config(tmp_path, "bad.toml", name="beta")

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml")
                failed = await _attach(
                    client, "bad.toml", name="alpha"
                )  # identity assertion mismatch
                a_call = await _call(client, "sofer_meta_check", {"config": "a.toml"})
                return failed, a_call

        failed, a_call = _run(_go())
        assert failed["ok"] is False
        assert a_call["error_code"] == "INITIALIZATION_REQUIRED"

    def test_same_context_reattach_is_admitted(self, tmp_path: Path) -> None:
        _write_config(tmp_path)

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                first = await _attach(client)
                second = await _attach(client)
                return first, second

        first, second = _run(_go())
        assert first["session_ready"] is True
        assert second["session_ready"] is True


class TestMatchingAndResources:
    """D5 + T6: root/config matching, standalone tools, and resource rules."""

    def test_two_tomls_under_one_root_require_the_active_config(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "a.toml", name="alpha")
        _write_config(tmp_path, "b.toml", name="beta")

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml")
                other = await _call(client, "sofer_meta_check", {"config": "b.toml"})
                active = await _call(client, "sofer_meta_check", {"config": "a.toml"})
                return other, active

        other, active = _run(_go())
        assert other["error_code"] == "INITIALIZATION_CONTEXT_MISMATCH"
        assert active["ok"] is True

    def test_omitted_root_uses_the_registration_root_not_the_last_init(
        self, tmp_path: Path
    ) -> None:
        alpha = tmp_path / "alpha"
        alpha.mkdir()
        _write_config(alpha, "a.toml", name="alpha")

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml", root=str(alpha))
                omitted = await _call(client, "sofer_meta_check", {"config": str(alpha / "a.toml")})
                explicit = await _call(
                    client,
                    "sofer_meta_check",
                    {"config": str(alpha / "a.toml"), "root": str(alpha)},
                )
                return omitted, explicit

        omitted, explicit = _run(_go())
        assert omitted["error_code"] == "INITIALIZATION_CONTEXT_MISMATCH"
        assert explicit["ok"] is True

    def test_standalone_tools_are_bound_by_the_active_root(self, tmp_path: Path) -> None:
        beta = tmp_path / "beta"
        beta.mkdir()
        (beta / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        _write_config(beta, "b.toml", name="beta")
        _write_config(tmp_path, "a.toml", name="alpha")

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client, "a.toml")
                inside = await _call(
                    client,
                    "sofer_codebook",
                    {"path": str(beta / "data.csv"), "root": str(tmp_path)},
                )
                await _attach(client, "b.toml", root=str(beta))
                outside = await _call(client, "sofer_codebook", {"path": str(beta / "data.csv")})
                return inside, outside

        inside, outside = _run(_go())
        assert inside["ok"] is True, inside
        # The explicit beta root resolves fine, but the request omitted `root`:
        # it maps to the registration root, which differs from active R(beta).
        assert outside["error_code"] == "INITIALIZATION_CONTEXT_MISMATCH"

    def test_status_resource_is_available_before_init(self, tmp_path: Path) -> None:
        async def _go() -> str:
            async with Client(ms.build_server(root=tmp_path)) as client:
                contents = await client.read_resource("sofer://status")
                return contents[0].text  # type: ignore[return-value]

        assert "approval_configured" in _run(_go())

    def test_content_resources_are_blocked_before_init(self, tmp_path: Path) -> None:
        _make_dataset(tmp_path)
        server = ms.build_server(root=tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(server) as client:
                return await _resource_error(client.read_resource("sofer://dataset/dataset.toml"))

        envelope = _run(_go())
        assert envelope["error_code"] == "INITIALIZATION_REQUIRED"
        assert envelope["next"]["action"] == "resources/read"
        assert envelope["next"]["uri"] == "sofer://dataset/dataset.toml"
        assert envelope["config_errors"] == []

    def test_dataset_resource_requires_the_active_config(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "a.toml", name="alpha")
        _write_config(tmp_path, "b.toml", name="beta")
        server = ms.build_server(root=tmp_path)

        async def _go() -> tuple[str, dict[str, Any]]:
            async with Client(server) as client:
                await _attach(client, "a.toml")
                allowed = await client.read_resource("sofer://dataset/a.toml")
                mismatched = await _resource_error(client.read_resource("sofer://dataset/b.toml"))
                return allowed[0].text, mismatched  # type: ignore[return-value]

        allowed_text, mismatched = _run(_go())
        assert 'name = "alpha"' in allowed_text
        assert mismatched["error_code"] == "INITIALIZATION_CONTEXT_MISMATCH"

    def test_codebook_resource_is_contained_in_the_active_root(self, tmp_path: Path) -> None:
        beta = tmp_path / "beta"
        beta.mkdir()
        (beta / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        alpha = tmp_path / "alpha"
        alpha.mkdir()
        _write_config(alpha, "a.toml", name="alpha")
        server = ms.build_server(root=tmp_path)

        async def _go() -> dict[str, Any]:
            from mcp.shared.exceptions import MCPError

            async with Client(server) as client:
                await _attach(client, "a.toml", root=str(alpha))
                with pytest.raises(MCPError) as excinfo:
                    await client.read_resource(f"sofer://codebook/{beta / 'data.csv'}")
                assert "outside" in str(excinfo.value).lower()
                return {"message": str(excinfo.value)}

        assert "message" in _run(_go())


class TestEnvelopes:
    """D3/D6 + T7: deterministic refusals, continuations, and init fields."""

    def test_required_refusal_uses_the_known_config(self, tmp_path: Path) -> None:
        _write_config(tmp_path)
        before = _tree(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _call(client, "sofer_validate", {"config": "dataset.toml"})

        envelope = _run(_go())
        assert envelope["next"]["tool"] == "sofer_init"
        assert envelope["next"]["arguments"].get("config") == "dataset.toml"
        assert envelope["config_errors"] == []
        assert _tree(tmp_path) == before

    def test_required_refusal_asks_for_config_when_unknown(self, tmp_path: Path) -> None:
        _make_dataset(tmp_path)

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _call(client, "sofer_codebook", {"path": "data.csv"})

        envelope = _run(_go())
        assert envelope["next"]["tool"] == "sofer_init"
        assert envelope["next"]["arguments"] == {}
        assert envelope["next"]["input_required"] == ["config"]

    def test_required_refusal_echoes_an_explicit_root(self, tmp_path: Path) -> None:
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")

        async def _go() -> dict[str, Any]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                return await _call(
                    client,
                    "sofer_codebook",
                    {"path": "data.csv", "root": str(tmp_path)},
                )

        envelope = _run(_go())
        assert envelope["next"]["arguments"] == {"root": str(tmp_path.resolve())}
        assert envelope["next"]["input_required"] == ["config"]

    def test_config_error_carries_diagnostics_but_admission_does_not(self, tmp_path: Path) -> None:
        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                admission_refusal = await _call(client, "sofer_validate", {"config": "x.toml"})
                config_error = await _call(
                    client, "sofer_init", {"name": "bad/name", "user": "myuser", "cwd": "."}
                )
                return admission_refusal, config_error

        admission_refusal, config_error = _run(_go())
        assert admission_refusal["config_errors"] == []
        assert config_error["config_errors"], config_error
        assert config_error["error_code"] == "CONFIG_ERROR"


class TestConcurrency:
    """D4 + T5: deterministic barriers for init-vs-init and init-vs-work."""

    def test_second_init_while_init_runs_is_in_progress(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_config(tmp_path)
        entered = threading.Event()
        release = threading.Event()
        original = ms.DatasetConfig.from_toml.__func__

        def slow_from_toml(
            cls: type[ms.DatasetConfig], path: Any, discovery_root: Any = None
        ) -> ms.DatasetConfig:
            entered.set()
            assert release.wait(PROCESS_TIMEOUT_SECONDS)
            return original(cls, path, discovery_root)

        monkeypatch.setattr(ms.DatasetConfig, "from_toml", classmethod(slow_from_toml))

        async def _go() -> tuple[dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                first = asyncio.create_task(_attach(client))
                assert await asyncio.to_thread(entered.wait, PROCESS_TIMEOUT_SECONDS)
                second = await _call(client, "sofer_init", {"config": "dataset.toml"})
                release.set()
                return await first, second

        first, second = _run(_go())
        assert second["error_code"] == "INITIALIZATION_IN_PROGRESS", second
        assert first["session_ready"] is True

    def test_init_while_protected_work_runs_is_busy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_config(tmp_path)
        entered = threading.Event()
        release = threading.Event()
        real_execution = ms._tool_execution

        @contextlib.contextmanager
        def slow_execution() -> Iterator[None]:
            entered.set()
            assert release.wait(PROCESS_TIMEOUT_SECONDS)
            with real_execution():
                yield

        async def _go() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            async with Client(ms.build_server(root=tmp_path)) as client:
                await _attach(client)
                monkeypatch.setattr(ms, "_tool_execution", slow_execution)
                working = asyncio.create_task(
                    _call(client, "sofer_meta_check", {"config": "dataset.toml"})
                )
                assert await asyncio.to_thread(entered.wait, PROCESS_TIMEOUT_SECONDS)
                busy = await _call(client, "sofer_init", {"config": "dataset.toml"})
                release.set()
                admitted = await working
                return (
                    busy,
                    admitted,
                    await _call(client, "sofer_meta_check", {"config": "dataset.toml"}),
                )

        busy, admitted, after = _run(_go())
        assert busy["error_code"] == "INITIALIZATION_CONTEXT_BUSY", busy
        assert admitted["ok"] is True
        assert after["ok"] is True


class TestAdmissionStateMachine:
    """Unit-level D4 outcomes the public boundary reaches only via timing."""

    def test_failed_or_cancelled_init_never_restores_the_previous_context(self) -> None:
        state = admission.SessionAdmission()
        assert state.claim_init({}) is None
        first = admission.AdmissionContext(Path("/work/a"), Path("/work/a/a.toml"))
        state.settle_init(first)
        assert state.state == admission.READY

        assert state.claim_init({}) is None
        state.settle_init(None)  # dry run, failure, exception, or cancellation
        assert state.state == admission.UNINITIALIZED
        assert state.context is None

    def test_init_is_refused_while_initializing(self) -> None:
        state = admission.SessionAdmission()
        assert state.claim_init({}) is None
        refusal = state.claim_init({})
        assert refusal is not None
        assert refusal.error_code == admission.ERROR_INIT_IN_PROGRESS

    def test_init_is_refused_while_admitted_work_holds_a_lease(self) -> None:
        state = admission.SessionAdmission()
        context = admission.AdmissionContext(Path("/work"), Path("/work/a.toml"))
        state.settle_init(context)
        assert (
            state.claim_protected(
                requested_root=Path("/work"),
                requested_config=Path("/work/a.toml"),
                requires_config=True,
                arguments={},
                config_argument="a.toml",
            )
            is None
        )
        refusal = state.claim_init({})
        assert refusal is not None
        assert refusal.error_code == admission.ERROR_INIT_CONTEXT_BUSY
        assert state.context == context

    def test_unknown_tools_default_to_protected(self) -> None:
        assert admission.classify_tool("sofer_init") == "init"
        assert admission.classify_tool("sofer_validate") == "config"
        assert admission.classify_tool("sofer_codebook") == "standalone"
        assert admission.classify_tool("sofer_report_failure") == "report"
        assert admission.classify_tool("sofer_future_tool") == "protected"

    def test_session_unavailable_refusal_is_terminal(self) -> None:
        refusal = admission.session_unavailable_refusal()
        assert refusal.error_code == admission.ERROR_INIT_SESSION_UNAVAILABLE
        assert refusal.next_call == {}

    def test_mismatch_refusal_shapes_each_inferable_target(self) -> None:
        active = admission.AdmissionContext(Path("/work/a"), Path("/work/a/a.toml"))
        root_only = admission.context_mismatch_refusal(
            active=active, requested_root=Path("/work/b"), requested_config=None
        )
        assert root_only.next_call["tool"] == "sofer_init"
        assert Path(root_only.next_call["arguments"]["root"]) == Path("/work/b")
        neither = admission.context_mismatch_refusal(
            active=active, requested_root=None, requested_config=None
        )
        assert neither.next_call == {}

    def test_release_without_a_lease_is_a_no_op(self) -> None:
        state = admission.SessionAdmission()
        state.release()
        assert state.active == 0


class TestStdioSession:
    """D1/D2/D8 + T2: a real stdio session keeps state; a new one starts clean."""

    def test_stdio_refusal_attach_then_allowed_and_new_session_is_clean(
        self, tmp_path: Path
    ) -> None:
        from conftest import McpStdioServer
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        _make_dataset(tmp_path)
        spawned = McpStdioServer(cwd=tmp_path)
        params = spawned.spawn()

        async def _session() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            async with stdio_client(params) as (read, write):
                async with ClientSession(
                    read, write, read_timeout_seconds=PROCESS_TIMEOUT_SECONDS
                ) as session:
                    await session.initialize()
                    refused = await session.call_tool("sofer_codebook", {"path": "data.csv"})
                    attached = await session.call_tool("sofer_init", {"config": "dataset.toml"})
                    allowed = await session.call_tool("sofer_codebook", {"path": "data.csv"})
                    return (
                        json.loads(refused.content[0].text),  # type: ignore[union-attr]
                        json.loads(attached.content[0].text),  # type: ignore[union-attr]
                        json.loads(allowed.content[0].text),  # type: ignore[union-attr]
                    )

        async def _fresh() -> dict[str, Any]:
            async with stdio_client(params) as (read, write):
                async with ClientSession(
                    read, write, read_timeout_seconds=PROCESS_TIMEOUT_SECONDS
                ) as session:
                    await session.initialize()
                    result = await session.call_tool("sofer_codebook", {"path": "data.csv"})
                    return json.loads(result.content[0].text)  # type: ignore[union-attr]

        refused, attached, allowed = _run(_session())
        assert refused["error_code"] == "INITIALIZATION_REQUIRED"
        assert attached["session_ready"] is True
        assert allowed["ok"] is True, allowed

        fresh = _run(_fresh())
        assert fresh["error_code"] == "INITIALIZATION_REQUIRED"
