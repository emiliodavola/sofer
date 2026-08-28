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
    sofer_publish,
    sofer_publish_confirm,
    sofer_scan_apply,
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
