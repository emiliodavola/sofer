"""Offline tests for ``sofer.mcp_server`` (MSP-R01..R12, CF-1/CF-2 security).

Every test runs without a network or an LLM: tool functions directly,
in-memory fastmcp clients, a real stdio subprocess smoke test, and
``publish._api`` monkeypatching for the HF path. Config state isolation
uses the shared ``restore_tool_config`` fixture.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import sofer.config as config
import sofer.publish as publish_mod
from sofer import mcp_server as ms
from sofer.mcp_server import (
    HFTokenError,
    MCPToolError,
    PublishRefusedError,
    build_server,
    sofer_codebook,
    sofer_codebook_all,
    sofer_prepare,
    sofer_profile,
    sofer_publish,
    sofer_publish_confirm,
    sofer_render,
    sofer_scan_apply,
    sofer_scan_dry_run,
    sofer_validate,
)
from sofer.model import DatasetConfig
from sofer.prepare import prepare as domain_prepare

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run one async client interaction per test."""
    return asyncio.run(coro)


def _make_dataset(root: Path, *, confidential: bool = False, name: str = "test-ds") -> Path:
    """Write a minimal, quality-passing dataset (TOML + CSV) under *root*."""
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


def _prepare_package(root: Path) -> None:
    """Prepare the dataset package so publish_confirm has something to upload."""
    cfg = DatasetConfig.from_toml(root / "dataset.toml")
    domain_prepare(cfg, root / "build")


def _mock_hf_api(monkeypatch, *, existing: list[str] | None = None) -> None:
    """Stub every HF API method publish could reach (offline tests)."""
    monkeypatch.setattr(publish_mod._api, "create_repo", lambda *a, **kw: None)
    monkeypatch.setattr(publish_mod._api, "list_repo_files", lambda *a, **kw: existing or [])
    monkeypatch.setattr(publish_mod._api, "upload_folder", lambda *a, **kw: None)


def _call(server: ms._FastMCP, name: str, args: dict | None = None):
    """Call a tool through an in-memory client; returns the CallToolResult."""

    async def _go():
        async with Client(server) as client:
            return await client.call_tool(name, args)

    return _run(_go())


def _tool_schema(server: ms._FastMCP, name: str) -> dict:
    async def _go():
        async with Client(server) as client:
            tools = await client.list_tools()
            return {t.name: t for t in tools}[name]

    tool = _run(_go())
    return dict(tool.inputSchema)


def _make_link(link: Path, target: Path) -> bool:
    """Create a symlink (or NTFS junction on win32) ``link -> target``.

    Returns ``True`` on success. On win32, ``os.symlink`` requires
    developer-mode privileges — falls back to ``mklink /J`` (junction). When
    the OS refuses both, returns ``False`` so the caller skips with a
    documented reason instead of stalling.
    """
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
        return True
    except OSError:
        if os.name != "nt":
            return False
        try:
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and link.exists()
        except OSError:
            return False


# ---------------------------------------------------------------------------
#  7.1 — Import without the extra fails clearly (MSP-R02)
# ---------------------------------------------------------------------------


class TestImportWithoutExtra:
    def test_import_raises_without_fastmcp(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "fastmcp", None)
        sys.modules.pop("sofer.mcp_server", None)
        with pytest.raises(ImportError) as excinfo:
            importlib.import_module("sofer.mcp_server")
        assert "sofer[mcp]" in str(excinfo.value)
        assert "pip install" in str(excinfo.value)


# ---------------------------------------------------------------------------
#  7.2 — In-memory client: roster, schemas, validate round-trip (MSP-R03/R11)
# ---------------------------------------------------------------------------


@pytest.fixture
def server(tmp_path: Path):
    """A server rooted at a fresh temp dir with a minimal dataset."""
    _make_dataset(tmp_path)
    return build_server(root=tmp_path)


class TestToolRoster:
    _EXPECTED: frozenset[str] = frozenset(
        {
            "sofer_validate",
            "sofer_prepare",
            "sofer_publish",
            "sofer_publish_confirm",
            "sofer_codebook",
            "sofer_codebook_all",
            "sofer_profile",
            "sofer_render",
            "sofer_scan_dry_run",
            "sofer_scan_apply",
        }
    )

    def test_exactly_ten_callables(self, server):
        async def _go():
            async with Client(server) as client:
                tools = await client.list_tools()
                return {t.name for t in tools}

        assert _run(_go()) == self._EXPECTED

    def test_validate_round_trip(self, server, tmp_path):
        result = _call(server, "sofer_validate", {"config": str(tmp_path / "dataset.toml")})
        assert not result.is_error
        envelope = result.data
        assert envelope["ok"] is True
        assert envelope["exit_code"] == 0
        for key in (
            "passed",
            "errors",
            "warnings",
            "quality_failures",
            "quality_warnings",
            "ran_checks",
            "confidential",
            "config_errors",
        ):
            assert key in envelope, f"envelope missing {key}"
        assert envelope["confidential"] is False
        assert envelope["config_errors"] == []

    def test_validate_is_read_only(self, server, tmp_path):
        before = sorted(p.name for p in tmp_path.rglob("*"))
        _call(server, "sofer_validate", {"config": str(tmp_path / "dataset.toml")})
        after = sorted(p.name for p in tmp_path.rglob("*"))
        assert before == after


# ---------------------------------------------------------------------------
#  7.3 — No silent default config name (MSP-R10)
# ---------------------------------------------------------------------------


class TestNoSilentDefault:
    def test_codebook_requires_path(self, server):
        schema = _tool_schema(server, "sofer_codebook")
        assert "path" in schema.get("required", [])

    def test_scan_requires_config(self, server):
        schema = _tool_schema(server, "sofer_scan_apply")
        assert "config" in schema.get("required", [])

    def test_missing_required_arg_raises_schema_error(self, server):
        with pytest.raises(ToolError, match="Missing required argument"):
            _call(server, "sofer_codebook", {})


# ---------------------------------------------------------------------------
#  7.4 — Stdio smoke test with clean framing (MSP-R01/R11)
# ---------------------------------------------------------------------------


class TestStdioSmoke:
    def test_spawned_server_handshake_clean_framing(self, tmp_path):
        _make_dataset(tmp_path)

        async def _go():
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            params = StdioServerParameters(
                command=sys.executable,
                args=["-c", "from sofer.mcp_server import main; main()"],
                cwd=str(tmp_path),
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    assert init is not None
                    tools = await session.list_tools()
                    assert len(tools.tools) == 10
                    result = await session.call_tool(
                        "sofer_validate", {"config": str(tmp_path / "dataset.toml")}
                    )
                    assert not result.isError
                    text = result.content[0].text
                    assert "config_errors" in text
                    assert '"ok":true' in text

        _run(_go())


# ---------------------------------------------------------------------------
#  7.5 — Streams restored after a raising path (MSP-R04)
# ---------------------------------------------------------------------------


class TestStreamRestore:
    def test_stdout_stderr_restored_after_raise(self, tmp_path, monkeypatch):
        _make_dataset(tmp_path)
        build_server(root=tmp_path)

        fake_out = object()
        fake_err = object()
        monkeypatch.setattr(sys, "stdout", fake_out)
        monkeypatch.setattr(sys, "stderr", fake_err)

        with pytest.raises(MCPToolError, match="sofer_publish_confirm"):
            sofer_publish(str(tmp_path / "dataset.toml"), target="hf", dry_run=False)

        assert sys.stdout is fake_out
        assert sys.stderr is fake_err


# ---------------------------------------------------------------------------
#  7.6 — Network tools offline via seam (MSP-R05/R11)
# ---------------------------------------------------------------------------


class TestNetworkOffline:
    def test_confirm_uploads_via_fake_api(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        envelope = sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)
        assert envelope["ok"] is True
        assert envelope["exit_code"] == 0
        assert envelope["skipped_protected"] == []
        assert envelope["partial"] is False
        assert envelope["acknowledge_risk"] is True

    def test_confirm_upload_failure_ok_false(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("upload exploded")

        _mock_hf_api(monkeypatch)
        # publish._hf_upload_folder swallows _api.upload_folder errors
        # internally (publish.py:151-181); patch the module seam so the
        # failure propagates to publish's rc (design test-gap row).
        monkeypatch.setattr(publish_mod, "_hf_upload_folder", _boom)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        envelope = sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1
        assert "upload exploded" in envelope["output"]

    def test_empty_token_fails_like_missing(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.setenv("HF_TOKEN", "")
        monkeypatch.delenv("HF_HUB_TOKEN", raising=False)
        build_server(root=tmp_path)

        with pytest.raises(HFTokenError, match="HF_TOKEN"):
            sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)

    def test_hf_hub_token_alias_accepted(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setenv("HF_HUB_TOKEN", "alias_token")
        build_server(root=tmp_path)

        envelope = sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)
        assert envelope["ok"] is True


# ---------------------------------------------------------------------------
#  7.7 — Security: auth refusals + containment vectors (CF-1/CF-2, MSP-R05/R11)
# ---------------------------------------------------------------------------


class TestPublishAuthorizationLadder:
    def test_refuses_without_acknowledge_risk(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="acknowledge_risk"):
            sofer_publish_confirm(str(tmp_path / "dataset.toml"))

    def test_refuses_confidential_without_acknowledge(
        self, tmp_path, monkeypatch, restore_tool_config
    ):
        _make_dataset(tmp_path, confidential=True)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="confidential"):
            sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)

    def test_confidential_acknowledged_proceeds(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path, confidential=True)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        envelope = sofer_publish_confirm(
            str(tmp_path / "dataset.toml"),
            acknowledge_risk=True,
            acknowledge_confidential=True,
        )
        assert envelope["ok"] is True
        assert envelope["confidential"] is True

    def test_phrase_mismatch_refused(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path, approval_phrase="s3cret")

        with pytest.raises(PublishRefusedError, match="approval phrase"):
            sofer_publish_confirm(
                str(tmp_path / "dataset.toml"),
                acknowledge_risk=True,
                approval_phrase="wrong",
            )

    def test_phrase_match_proceeds(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path, approval_phrase="s3cret")

        envelope = sofer_publish_confirm(
            str(tmp_path / "dataset.toml"),
            acknowledge_risk=True,
            approval_phrase="s3cret",
        )
        assert envelope["ok"] is True

    def test_phrase_from_env(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        monkeypatch.setenv("SOFER_MCP_APPROVAL_PHRASE", "env-phrase")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="approval phrase"):
            sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)
        envelope = sofer_publish_confirm(
            str(tmp_path / "dataset.toml"),
            acknowledge_risk=True,
            approval_phrase="env-phrase",
        )
        assert envelope["ok"] is True


class TestContainment:
    def test_config_outside_root_refused(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        evil = outside / "evil.toml"
        evil.write_text("[dataset]\nname='x'\nrepo_id='u/x'\n", encoding="utf-8")
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        server = build_server(root=root)

        with pytest.raises(ToolError, match="outside the server root"):
            _call(server, "sofer_validate", {"config": str(evil)})

    def test_config_with_dotdot_refused(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        server = build_server(root=root)

        with pytest.raises(ToolError, match="outside the server root"):
            _call(server, "sofer_validate", {"config": "../evil.toml"})

    def test_file_local_absolute_outside_root(self, tmp_path, restore_tool_config):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secrets.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        local_path = (outside / "secrets.csv").as_posix()
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[[file]]\n"
            f"local = '{local_path}'\nremote = 'secrets.csv'\n",
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_validate", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any("outside the server root" in e for e in envelope["config_errors"])

    def test_file_local_dotdot_escape(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[[file]]\n"
            'local = "../evil.csv"\nremote = "evil.csv"\n',
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_validate", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any("outside the server root" in e for e in envelope["config_errors"])

    def test_symlink_inside_root_to_outside(self, tmp_path, restore_tool_config):
        outside = tmp_path / "outside"
        outside.mkdir()
        secret = outside / "secret.csv"
        secret.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        link = root / "leak.csv"
        if not _make_link(link, secret):
            pytest.skip(
                "symlink/junction creation requires elevated privileges on "
                "this win32 host — containment is covered by the other vectors"
            )
        server = build_server(root=root)

        with pytest.raises(ToolError, match="outside the server root"):
            _call(server, "sofer_codebook", {"path": "leak.csv"})

    def test_junction_dir_inside_root_to_outside(self, tmp_path, restore_tool_config):
        """NTFS junction (works without elevation): a [[file]] local dir that
        is a junction to an outside directory is rejected by containment."""
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "s.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        junction = root / "leakdir"
        if not _make_link(junction, outside):
            pytest.skip(
                "junction creation is unavailable on this host — the symlink "
                "containment vector is covered by the other tests"
            )
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[[file]]\n"
            "local = 'leakdir'\nremote = 'leakdir/'\nrecursive = true\n",
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_validate", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any("outside the server root" in e for e in envelope["config_errors"])

    def test_remote_dotdot_rejected(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[[file]]\n"
            'local = "data.csv"\nremote = "../x.csv"\n',
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_validate", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any("remote is unsafe" in e for e in envelope["config_errors"])

    def test_remote_absolute_win_drive_rejected(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[[file]]\n"
            'local = "data.csv"\nremote = "C:/evil.csv"\n',
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_validate", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any("remote is unsafe" in e for e in envelope["config_errors"])

    def test_remote_drive_relative_no_slash_rejected(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[[file]]\n"
            'local = "data.csv"\nremote = "C:evil.csv"\n',
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_validate", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any("remote is unsafe" in e for e in envelope["config_errors"])

    def test_output_dir_outside_root_refused(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        outside = tmp_path / "outside"
        server = build_server(root=root)

        with pytest.raises(ToolError, match="outside the server root"):
            _call(
                server,
                "sofer_codebook",
                {"path": "data.csv", "output": str(outside / "cb.md")},
            )

    def test_remote_unsafe_unit_vectors(self):
        from sofer.mcp_server import _remote_is_unsafe

        assert _remote_is_unsafe("../x")
        assert _remote_is_unsafe("C:/evil")
        assert _remote_is_unsafe("C:evil")
        assert _remote_is_unsafe("//server/share/x")
        assert _remote_is_unsafe("a/../b")
        assert _remote_is_unsafe(r"..\..\x")
        assert not _remote_is_unsafe("x/y.csv")
        assert not _remote_is_unsafe("data.csv")


# ---------------------------------------------------------------------------
#  7.8 — Multi-call config determinism (CF-1 reliability, MSP-R11)
# ---------------------------------------------------------------------------


class TestConfigDeterminism:
    def test_validate_a_then_scan_b_uses_b_anchor(self, tmp_path, monkeypatch, restore_tool_config):
        tree_a = tmp_path / "treeA"
        tree_a.mkdir()
        (tree_a / "pyproject.toml").write_text(
            '[tool.sofer]\noutput_dir = "cache-a"\n', encoding="utf-8"
        )
        (tree_a / "raw").mkdir()
        (tree_a / "raw" / "a.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        _make_dataset(tree_a, name="ds-a")

        tree_b = tmp_path / "treeB"
        tree_b.mkdir()
        (tree_b / "pyproject.toml").write_text(
            '[tool.sofer]\noutput_dir = "cache-b"\n', encoding="utf-8"
        )
        (tree_b / "raw").mkdir()
        (tree_b / "raw" / "b.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        _make_dataset(tree_b, name="ds-b")

        server = build_server(root=tmp_path)

        # Residue source: A's scan-anchored config state (cache-a).
        envelope_a = _call(server, "sofer_validate", {"config": str(tree_a / "dataset.toml")}).data
        assert envelope_a["ok"] is True

        # B's scan MUST self-anchor on B's own tree (cache-b).
        envelope_b = _call(
            server, "sofer_scan_apply", {"config": str(tree_b / "dataset.toml")}
        ).data
        assert envelope_b["ok"] is True, envelope_b

        toml_b = (tree_b / "dataset.toml").read_text(encoding="utf-8")
        assert 'local = "cache-b/b.csv"' in toml_b
        assert (tree_b / "cache-b" / "b.csv").is_file()
        assert "cache-a" not in toml_b
        assert not (tree_b / "cache-a").exists()


# ---------------------------------------------------------------------------
#  7.9 — Resources: containment, size guard, missing-file errors (MSP-R07)
# ---------------------------------------------------------------------------


class TestResources:
    def test_dataset_resource_raw_toml(self, tmp_path):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                contents = await client.read_resource(
                    f"sofer://dataset/{tmp_path / 'dataset.toml'}"
                )
                return contents[0].text

        text = _run(_go())
        assert "[dataset]" in text
        assert 'name = "test-ds"' in text

    def test_codebook_resource_generates_on_demand(self, tmp_path):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                contents = await client.read_resource(f"sofer://codebook/{tmp_path / 'data.csv'}")
                return contents[0].text

        text = _run(_go())
        assert "# Codebook: data.csv" in text
        assert "| 1 | `col_a`" in text
        assert not (tmp_path / "codebook.md").exists(), "resource must not write"

    def test_metadata_resource_when_present(self, tmp_path):
        _make_dataset(tmp_path)
        (tmp_path / "metadata.yaml").write_text("metadata_version: '1'\n", encoding="utf-8")
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                contents = await client.read_resource(
                    f"sofer://metadata/{tmp_path / 'metadata.yaml'}"
                )
                return contents[0].text

        assert "metadata_version" in _run(_go())

    def test_metadata_missing_clear_error(self, tmp_path):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                await client.read_resource("sofer://metadata/absent.yaml")

        from mcp import McpError

        with pytest.raises(McpError) as excinfo:
            _run(_go())
        assert "metadata not found" in str(excinfo.value)
        assert "absent.yaml" in str(excinfo.value)

    def test_resource_containment_refused(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "evil.toml").write_text("[dataset]\n", encoding="utf-8")
        server = build_server(root=root)

        async def _go():
            async with Client(server) as client:
                await client.read_resource(f"sofer://dataset/{outside / 'evil.toml'}")

        from mcp import McpError

        with pytest.raises(McpError, match="outside the server root"):
            _run(_go())

    def test_resource_extension_allowlist(self, tmp_path):
        _make_dataset(tmp_path)
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                await client.read_resource(f"sofer://dataset/{tmp_path / 'notes.txt'}")

        from mcp import McpError

        with pytest.raises(McpError, match="one of these extensions"):
            _run(_go())

    def test_resource_size_guard(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        monkeypatch.setattr(config, "AGENT_RESOURCE_MAX_BYTES", 10)
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                await client.read_resource(f"sofer://dataset/{tmp_path / 'dataset.toml'}")

        from mcp import McpError

        with pytest.raises(McpError, match="resource size limit"):
            _run(_go())


# ---------------------------------------------------------------------------
#  7.10 — Prompts: 3 templates, argument substitution, approval stop (MSP-R08)
# ---------------------------------------------------------------------------


class TestPrompts:
    def test_prompt_list_shows_three(self, tmp_path):
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                prompts = await client.list_prompts()
                return {p.name for p in prompts}

        assert _run(_go()) == {"prepare_dataset", "assess_dataset", "finalize_and_publish"}

    def test_prompt_arguments_substituted(self, tmp_path):
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                prompt = await client.get_prompt("prepare_dataset", {"config": "my/dataset.toml"})
                return prompt.messages[0].content.text

        text = _run(_go())
        assert "my/dataset.toml" in text

    def test_publish_prompt_mandates_approval_stop(self, tmp_path):
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                prompt = await client.get_prompt(
                    "finalize_and_publish", {"config": "my/dataset.toml"}
                )
                return prompt.messages[0].content.text

        text = _run(_go())
        assert "STOP" in text
        assert "approval" in text.lower()
        assert "sofer_publish_confirm" in text
        assert "UNTRUSTED" in text


# ---------------------------------------------------------------------------
#  7.11 — Empty/headerless codebook marker at the tool level (adv5)
# ---------------------------------------------------------------------------


class TestEmptyCodebookTool:
    def test_empty_csv_returns_marker(self, tmp_path):
        (tmp_path / "empty.csv").write_text("", encoding="utf-8")
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_codebook", {"path": "empty.csv"}).data
        assert envelope["ok"] is True
        assert "**No data rows found** — the file is empty or headerless." in envelope["output"]


# ---------------------------------------------------------------------------
#  7.12 — verify-skip note + confirm skipped_protected/partial (MSP-R03/R05)
# ---------------------------------------------------------------------------


class TestVerifyAndProtected:
    def test_prepare_verify_skips_without_datasets(
        self, tmp_path, monkeypatch, restore_tool_config
    ):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)
        # Block the optional `datasets` import — verification must skip
        # non-blockingly (verification.py:66-73).
        monkeypatch.setitem(sys.modules, "datasets", None)

        async def _go():
            async with Client(server) as client:
                return await client.call_tool(
                    "sofer_prepare",
                    {"config": str(tmp_path / "dataset.toml"), "verify": True},
                )

        result = _run(_go())
        envelope = result.data
        assert envelope["ok"] is True
        assert "SKIPPED" in envelope["output"] or "not installed" in envelope["output"]

    def test_confirm_surfaces_skipped_protected(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch, existing=["data.parquet"])
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        envelope = sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)
        assert envelope["ok"] is True
        assert envelope["partial"] is True
        assert "data.parquet" in envelope["skipped_protected"]
        assert envelope["skipped_protected"] == sorted(envelope["skipped_protected"])


# ---------------------------------------------------------------------------
#  7.13 — publish/confirm wiring: dry-run never writes HF (MSP-R05)
# ---------------------------------------------------------------------------


class TestPublishDryRun:
    def test_publish_dry_run_default_no_network(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        build_server(root=tmp_path)

        envelope = sofer_publish(str(tmp_path / "dataset.toml"))
        assert envelope["ok"] is True
        assert envelope["dry_run"] is True
        assert "Dry-run" in envelope["output"] or "no files uploaded" in envelope["output"]

    def test_publish_hf_without_confirm_raises(self, tmp_path, restore_tool_config):
        _make_dataset(tmp_path)
        build_server(root=tmp_path)

        with pytest.raises(MCPToolError, match="sofer_publish_confirm"):
            sofer_publish(str(tmp_path / "dataset.toml"), target="hf", dry_run=False)


def test_scan_apply_never_prompts_and_chains_scanner():
    """MSP-R06: sofer_scan_apply chains the pure scanner without input()."""
    import inspect

    src = inspect.getsource(sofer_scan_apply)
    assert "input(" not in src
    assert "discover_files" in src
    assert "check_flatten_collisions" in src
    assert "merge_entries" in src
    assert "copy_files" in src
    assert "write_toml" in src


# ---------------------------------------------------------------------------
#  MSP-R12 — wheel packaging: entry point + mcp extra (CI-marked integration)
# ---------------------------------------------------------------------------


class TestWheelPackaging:
    @pytest.mark.skipif(
        importlib.util.find_spec("hatchling") is None,
        reason=(
            "hatchling build backend is not installed in the dev environment "
            "(CI builds the wheel; locally this is covered by pyproject.toml)"
        ),
    )
    def test_wheel_declares_script_and_extra(self, tmp_path):
        import zipfile

        repo_root = Path(__file__).resolve().parents[1]
        dist = tmp_path / "dist"
        dist.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "hatchling",
                "build",
                "-t",
                "wheel",
                "-d",
                str(dist),
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        wheels = list(dist.glob("*.whl"))
        assert len(wheels) == 1
        with zipfile.ZipFile(wheels[0]) as zf:
            entry_points = [n for n in zf.namelist() if n.endswith("entry_points.txt")]
            metadata = [n for n in zf.namelist() if n.endswith("METADATA")]
            assert entry_points, "wheel is missing entry_points.txt"
            ep = zf.read(entry_points[0]).decode("utf-8")
            assert "sofer-mcp = sofer.mcp_server:main" in ep
            assert metadata, "wheel is missing METADATA"
            meta = zf.read(metadata[0]).decode("utf-8")
            assert "Provides-Extra: mcp" in meta
            assert "Requires-Dist: fastmcp>=3.4,<4" in meta


# ---------------------------------------------------------------------------
#  Review fix 1 — publish authorization ladder bypass via non-"local" targets
#  (MSP-R05): publish.py routes ANY non-"local" target into the HF branch, so
#  sofer_publish must refuse every non-local REAL run, not just target="hf".
# ---------------------------------------------------------------------------


class TestPublishTargetLadder:
    def test_garbage_target_dry_run_false_refused_no_api(
        self, tmp_path, monkeypatch, restore_tool_config
    ):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        calls: list[str] = []
        monkeypatch.setattr(
            publish_mod._api, "create_repo", lambda *a, **kw: calls.append("create_repo")
        )
        monkeypatch.setattr(
            publish_mod._api,
            "list_repo_files",
            lambda *a, **kw: calls.append("list_repo_files"),
        )
        monkeypatch.setattr(
            publish_mod._api, "upload_folder", lambda *a, **kw: calls.append("upload_folder")
        )
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="unknown target"):
            sofer_publish(str(tmp_path / "dataset.toml"), target="garbage", dry_run=False)
        assert calls == [], "publish._api must never be reached for a refused target"

    def test_aws_target_dry_run_false_refused(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="unknown target"):
            sofer_publish(str(tmp_path / "dataset.toml"), target="aws", dry_run=False)

    def test_garbage_target_dry_run_ok_no_network(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        calls: list[str] = []
        monkeypatch.setattr(
            publish_mod._api, "create_repo", lambda *a, **kw: calls.append("create_repo")
        )
        monkeypatch.setattr(
            publish_mod._api,
            "list_repo_files",
            lambda *a, **kw: calls.append("list_repo_files"),
        )
        monkeypatch.setattr(
            publish_mod._api, "upload_folder", lambda *a, **kw: calls.append("upload_folder")
        )
        build_server(root=tmp_path)

        envelope = sofer_publish(str(tmp_path / "dataset.toml"), target="garbage", dry_run=True)
        assert envelope["ok"] is True
        assert envelope["dry_run"] is True
        assert "Dry-run" in envelope["output"] or "no files uploaded" in envelope["output"]
        assert calls == [], "a dry-run plan must never touch publish._api"

    def test_local_target_dry_run_false_copies_package(self, tmp_path, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        build_server(root=tmp_path)

        deliver = tmp_path / "deliver"
        envelope = sofer_publish(
            str(tmp_path / "dataset.toml"),
            target="local",
            dry_run=False,
            output=str(deliver),
        )
        assert envelope["ok"] is True, envelope
        assert envelope["exit_code"] == 0
        assert (deliver / "data.parquet").is_file(), "local copy must deliver the package"


# ---------------------------------------------------------------------------
#  Review fix 2 — config-content output paths must never escape the server
#  root: [dataset] build_dir / [tool.sofer] output_dir / codebooks_dir are
#  agent-controlled TOML values and get the same containment as the output
#  ARG (MSP-R07); [tool.sofer] discovery is bounded at the server root.
# ---------------------------------------------------------------------------


class TestOutputTargetContainment:
    def test_prepare_refuses_escaped_build_dir(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\nbuild_dir = '../../evil'\n\n"
            "[[file]]\nlocal='data.csv'\nremote='data.csv'\n",
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_prepare", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1
        assert any(
            "build_dir" in e and "outside the server root" in e for e in envelope["config_errors"]
        )
        assert not (tmp_path / "evil").exists(), "nothing may be written outside the root"

    def test_prepare_refuses_absolute_build_dir_outside_root(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        evil_abs = (tmp_path / "abs-evil").as_posix()
        (root / "dataset.toml").write_text(
            f"[dataset]\nname='x'\nrepo_id='u/x'\nbuild_dir = '{evil_abs}'\n\n"
            "[[file]]\nlocal='data.csv'\nremote='data.csv'\n",
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_prepare", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert any(
            "build_dir" in e and "outside the server root" in e for e in envelope["config_errors"]
        )
        assert not (tmp_path / "abs-evil").exists()

    def test_prepare_relative_build_dir_inside_root_works(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\nbuild_dir = 'pkg'\n\n"
            "[[file]]\nlocal='data.csv'\nremote='data.csv'\n",
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_prepare", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is True, envelope
        assert (root / "pkg" / "data.parquet").is_file()

    def test_scan_apply_refuses_in_root_escaped_output_dir(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        (root / "pyproject.toml").write_text(
            '[tool.sofer]\noutput_dir = "../../evil"\n', encoding="utf-8"
        )
        _make_dataset(root)
        (root / "raw").mkdir()
        (root / "raw" / "new.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        before = (root / "dataset.toml").read_text(encoding="utf-8")
        server = build_server(root=root)

        envelope = _call(server, "sofer_scan_apply", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1
        assert any(
            "output_dir" in e and "outside the server root" in e for e in envelope["config_errors"]
        )
        assert not (tmp_path / "evil").exists(), "refused scan must not write outside root"
        assert (root / "dataset.toml").read_text(encoding="utf-8") == before

    def test_scan_ignores_pyproject_above_root(self, tmp_path, restore_tool_config):
        # A [tool.sofer] in a pyproject ABOVE the server root must not steer
        # the scan — discovery is bounded at the root (fix 2b).
        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\noutput_dir = "../../evil"\n', encoding="utf-8"
        )
        root = tmp_path / "root"
        root.mkdir()
        _make_dataset(root)
        (root / "raw").mkdir()
        (root / "raw" / "new.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        server = build_server(root=root)

        envelope = _call(server, "sofer_scan_apply", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is True, envelope
        assert (root / "cache" / "new.csv").is_file(), "files must land under the default cache"
        assert not (root / "evil-cache").exists()
        assert not (tmp_path / "evil").exists(), "nothing may escape the root"
        toml = (root / "dataset.toml").read_text(encoding="utf-8")
        assert 'local = "cache/new.csv"' in toml
        assert "evil" not in toml


# ---------------------------------------------------------------------------
#  Review fix 3 — MSP-R05 security ordering: the quality gate runs BEFORE the
#  HF token check, so a failing config with no token fails deterministically
#  (ok:False) instead of raising HFTokenError.
# ---------------------------------------------------------------------------


class TestQualityGateBeforeToken:
    def test_failing_quality_no_token_returns_ok_false(
        self, tmp_path, monkeypatch, restore_tool_config
    ):
        _make_dataset(tmp_path)
        # Duplicate rows + a fail-severity duplicates check → quality fails.
        (tmp_path / "data.csv").write_text("col_a;col_b\n1;2\n1;2\n", encoding="utf-8-sig")
        (tmp_path / "dataset.toml").write_text(
            "[dataset]\nname='test-ds'\nrepo_id='user/test-ds'\n\n[meta]\n\n"
            "[[file]]\nlocal='data.csv'\nremote='data.csv'\n\n"
            "[[quality]]\ncheck='duplicates'\nseverity='fail'\n",
            encoding="utf-8",
        )
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HF_HUB_TOKEN", raising=False)
        build_server(root=tmp_path)

        envelope = sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1


# ---------------------------------------------------------------------------
#  Review fix 4 — behavioral tests for the four untested callables:
#  sofer_profile (MSP-R09), sofer_render, sofer_codebook_all (collision +
#  [meta] delimiter injection), sofer_scan_dry_run.
# ---------------------------------------------------------------------------


class TestProfileBehavior:
    def test_profile_surfaces_pii_findings(self, tmp_path, restore_tool_config):
        (tmp_path / "people.csv").write_text(
            "name;email\nAlice;a@b.com\nBob;c@d.com\n", encoding="utf-8-sig"
        )
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_profile", {"dataset": "people.csv"}).data
        assert envelope["ok"] is True, envelope
        assert envelope["exit_code"] == 0
        assert (tmp_path / "metadata.yaml").is_file(), "profile must write metadata.yaml"
        assert any(
            f["column"] == "email" and f["label"] == "email" for f in envelope["pii_findings"]
        ), envelope["pii_findings"]


class TestRenderBehavior:
    def test_render_writes_readme_next_to_metadata(self, tmp_path, restore_tool_config):
        (tmp_path / "people.csv").write_text(
            "name;email\nAlice;a@b.com\nBob;c@d.com\n", encoding="utf-8-sig"
        )
        server = build_server(root=tmp_path)
        profiled = _call(server, "sofer_profile", {"dataset": "people.csv"}).data
        assert profiled["ok"] is True

        envelope = _call(server, "sofer_render", {"package": str(tmp_path)}).data
        assert envelope["ok"] is True, envelope
        assert envelope["exit_code"] == 0
        readme = tmp_path / "README.md"
        assert readme.is_file(), "render must write README.md"
        assert "Wrote" in envelope["output"]
        assert "# " in readme.read_text(encoding="utf-8")


class TestCodebookAllBehavior:
    def test_codebook_all_writes_files_and_index(self, tmp_path, restore_tool_config):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        envelope = _call(
            server, "sofer_codebook_all", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert envelope["ok"] is True, envelope
        assert envelope["exit_code"] == 0
        assert len(envelope["files"]) >= 2, envelope["files"]
        assert all(Path(f).is_file() for f in envelope["files"])
        assert (tmp_path / "codebook.md").is_file(), "root index must be generated"

    def test_codebook_all_collision_ok_false(self, tmp_path, restore_tool_config):
        root = tmp_path / "root"
        root.mkdir()
        (root / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        (root / "cache").mkdir()
        (root / "cache" / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        (root / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n"
            "[[file]]\nlocal='data.csv'\nremote='data.csv'\n\n"
            "[[file]]\nlocal='cache/data.csv'\nremote='cache/data.csv'\n",
            encoding="utf-8",
        )
        server = build_server(root=root)

        envelope = _call(server, "sofer_codebook_all", {"config": str(root / "dataset.toml")}).data
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1
        assert "Collision" in envelope["output"]

    def test_codebook_all_honors_meta_delimiter(self, tmp_path, restore_tool_config):
        (tmp_path / "data.csv").write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8-sig")
        (tmp_path / "dataset.toml").write_text(
            "[dataset]\nname='x'\nrepo_id='u/x'\n\n[meta]\ncsv_delimiter = ','\n\n"
            "[[file]]\nlocal='data.csv'\nremote='data.csv'\n",
            encoding="utf-8",
        )
        server = build_server(root=tmp_path)

        envelope = _call(
            server, "sofer_codebook_all", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert envelope["ok"] is True, envelope
        codebook = tmp_path / "cache" / "codebooks" / "data.md"
        assert codebook.is_file(), f"missing {codebook}"
        text = codebook.read_text(encoding="utf-8")
        assert "| 1 | `name`" in text, text
        assert "| 2 | `age`" in text, text


class TestScanDryRunBehavior:
    def test_scan_dry_run_counts_and_writes_nothing(self, tmp_path, restore_tool_config):
        _make_dataset(tmp_path)
        (tmp_path / "new.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        before = (tmp_path / "dataset.toml").read_text(encoding="utf-8")
        server = build_server(root=tmp_path)

        envelope = _call(
            server, "sofer_scan_dry_run", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert envelope["ok"] is True, envelope
        assert envelope["discovered"] == 2, envelope
        assert envelope["registered"] == 1, envelope
        assert not (tmp_path / "cache").exists(), "dry-run must not copy files"
        assert (tmp_path / "dataset.toml").read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
#  Review fix 5 — MSP-R03 prepare overwrite refusal: a second sofer_prepare
#  without force refuses; force=True regenerates.
# ---------------------------------------------------------------------------


class TestPrepareOverwrite:
    def test_second_prepare_without_force_refuses(self, tmp_path, restore_tool_config):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        first = _call(server, "sofer_prepare", {"config": str(tmp_path / "dataset.toml")}).data
        assert first["ok"] is True, first

        second = _call(server, "sofer_prepare", {"config": str(tmp_path / "dataset.toml")}).data
        assert second["ok"] is False
        assert second["exit_code"] == 1
        assert "Refusing to overwrite" in second["output"]

        third = _call(
            server, "sofer_prepare", {"config": str(tmp_path / "dataset.toml"), "force": True}
        ).data
        assert third["ok"] is True, third


# ---------------------------------------------------------------------------
#  Review fix 6 — surfacing scenarios: confidential flag on validate (MSP-R09)
#  and the tool-level [tool.sofer] delimiter injection (MSP-R10).
# ---------------------------------------------------------------------------


class TestSurfacingScenarios:
    def test_validate_surfaces_confidential_true(self, tmp_path):
        _make_dataset(tmp_path, confidential=True)
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_validate", {"config": str(tmp_path / "dataset.toml")}).data
        assert envelope["ok"] is True
        assert envelope["confidential"] is True

    def test_codebook_honors_tool_sofer_delimiter(self, tmp_path, restore_tool_config):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\ncsv_delimiter = ","\n', encoding="utf-8"
        )
        (tmp_path / "data.csv").write_text("name,age\nAlice,30\n", encoding="utf-8-sig")
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_codebook", {"path": "data.csv"}).data
        assert envelope["ok"] is True, envelope
        assert "| 1 | `name`" in envelope["output"], envelope["output"]
        assert "| 2 | `age`" in envelope["output"], envelope["output"]


# ---------------------------------------------------------------------------
#  Review advisories — empty remote unsafe, absent HF_TOKEN, confirm refuses
#  local targets, one-server-per-process docstring, concurrency under the
#  execution lock.
# ---------------------------------------------------------------------------


class TestAdvisoryHardening:
    def test_remote_empty_is_unsafe(self):
        from sofer.mcp_server import _remote_is_unsafe

        assert _remote_is_unsafe("")

    def test_token_fully_absent_raises(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        _prepare_package(tmp_path)
        _mock_hf_api(monkeypatch)
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HF_HUB_TOKEN", raising=False)
        build_server(root=tmp_path)

        with pytest.raises(HFTokenError, match="HF_TOKEN"):
            sofer_publish_confirm(str(tmp_path / "dataset.toml"), acknowledge_risk=True)

    def test_confirm_refuses_local_target(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="sofer_publish"):
            sofer_publish_confirm(
                str(tmp_path / "dataset.toml"), target="local", acknowledge_risk=True
            )

    def test_confirm_refuses_unknown_target(self, tmp_path, monkeypatch, restore_tool_config):
        _make_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        build_server(root=tmp_path)

        with pytest.raises(PublishRefusedError, match="sofer_publish"):
            sofer_publish_confirm(
                str(tmp_path / "dataset.toml"), target="aws", acknowledge_risk=True
            )

    def test_build_server_docstring_warns_one_server_per_process(self):
        import inspect

        doc = inspect.getdoc(build_server) or ""
        assert "One-server-per-process" in doc

    def test_concurrent_calls_serialized(self, tmp_path):
        _make_dataset(tmp_path)
        server = build_server(root=tmp_path)

        async def _go():
            async with Client(server) as client:
                results = await asyncio.gather(
                    client.call_tool("sofer_validate", {"config": str(tmp_path / "dataset.toml")}),
                    client.call_tool("sofer_validate", {"config": str(tmp_path / "dataset.toml")}),
                )
                return [r.data for r in results]

        envelopes = _run(_go())
        assert len(envelopes) == 2
        for envelope in envelopes:
            assert envelope["ok"] is True
            assert envelope["exit_code"] == 0
            assert "config_errors" in envelope

    def test_every_tool_acquires_execution_lock(self):
        import inspect

        callables = [
            sofer_validate,
            sofer_prepare,
            sofer_publish,
            sofer_publish_confirm,
            sofer_codebook,
            sofer_codebook_all,
            sofer_profile,
            sofer_render,
            sofer_scan_dry_run,
            sofer_scan_apply,
        ]
        for fn in callables:
            src = inspect.getsource(fn)
            assert "_tool_execution()" in src, f"{fn.__name__} does not acquire the exec lock"
            assert "_capture_output()" in src, f"{fn.__name__} does not capture stdout"
