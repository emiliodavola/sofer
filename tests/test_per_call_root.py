"""Per-call containment root (issue #347) - contract matrix subset.

The whole matrix lives in the issue (B1-B18); this module owns the rows that
prove the mechanism end to end: resolution precedence, the envelope echo, the
continuation stamp, the typed failures, the allowlist, isolation, and the
schema surface.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from conftest import _make_dataset, call_tool
from fastmcp import Client

from sofer import mcp_server as ms
from sofer.mcp_server import RootUnavailableError, build_server

PATH_BEARING = (
    "sofer_validate",
    "sofer_meta_check",
    "sofer_meta_set",
    "sofer_file_set",
    "sofer_prepare",
    "sofer_publish",
    "sofer_publish_confirm",
    "sofer_codebook",
    "sofer_codebook_all",
    "sofer_profile",
    "sofer_profile_all",
    "sofer_render",
    "sofer_render_all",
    "sofer_auth_status",
    "sofer_repo_settings",
    "sofer_scan_dry_run",
    "sofer_scan_apply",
    "sofer_init",
)


def _tools(server: Any) -> dict[str, Any]:
    async def _list() -> dict[str, Any]:
        async with Client(server) as client:
            return {tool.name: tool for tool in await client.list_tools()}

    return asyncio.run(_list())


def _call(server: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return call_tool(server, name, args).data


def _foreign_dataset(tmp_path: Path) -> Path:
    """A valid dataset OUTSIDE the registration root, in its own directory."""
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _make_dataset(foreign)
    return foreign


class TestResolution:
    """``_resolve_call_root`` and the ``_get_root`` precedence chain."""

    def test_omitted_root_keeps_the_registration_root(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        build_server(root=tmp_path)

        envelope = ms.sofer_validate(config="dataset.toml")

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(tmp_path.resolve())
        assert "root" not in envelope["next"]["arguments"]

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_root_is_unset(self, tmp_path, blank) -> None:
        _make_dataset(tmp_path)
        build_server(root=tmp_path)

        envelope = ms.sofer_validate(config="dataset.toml", root=blank)

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(tmp_path.resolve())
        assert "root" not in envelope["next"]["arguments"]

    def test_foreign_root_runs_there_and_is_echoed(self, tmp_path) -> None:
        registration = tmp_path / "registration"
        registration.mkdir()
        foreign = _foreign_dataset(tmp_path)
        build_server(root=registration)

        envelope = ms.sofer_validate(config="dataset.toml", root=str(foreign))

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(foreign.resolve())
        assert envelope["next"]["arguments"]["root"] == str(foreign.resolve())

    def test_relative_root_anchors_on_the_registration_root(self, tmp_path, monkeypatch) -> None:
        registration = tmp_path / "registration"
        sibling = registration / "sibling"
        sibling.mkdir(parents=True)
        _make_dataset(sibling)
        third = tmp_path / "third"
        third.mkdir()
        monkeypatch.chdir(third)
        build_server(root=registration)

        envelope = ms.sofer_validate(config="dataset.toml", root="sibling")

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(sibling.resolve())

    def test_relative_root_with_dotdot_is_admitted_when_it_exists(self, tmp_path) -> None:
        registration = tmp_path / "registration"
        registration.mkdir()
        sibling = _foreign_dataset(tmp_path)
        build_server(root=registration)

        envelope = ms.sofer_validate(config="dataset.toml", root="../foreign")

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(sibling.resolve())

    def test_missing_root_raises_a_typed_error(self, tmp_path) -> None:
        build_server(root=tmp_path)

        with pytest.raises(RootUnavailableError, match="not found"):
            ms.sofer_validate(config="dataset.toml", root=str(tmp_path / "absent"))

    def test_file_root_raises_a_typed_error(self, tmp_path) -> None:
        target = tmp_path / "a-file"
        target.write_text("x", encoding="utf-8")
        build_server(root=tmp_path)

        with pytest.raises(RootUnavailableError, match="not a directory"):
            ms.sofer_validate(config="dataset.toml", root=str(target))

    def test_a_failure_leaves_no_bound_root(self, tmp_path) -> None:
        _make_dataset(tmp_path)
        build_server(root=tmp_path)

        with pytest.raises(RootUnavailableError):
            ms.sofer_validate(config="dataset.toml", root=str(tmp_path / "absent"))

        assert ms._EFFECTIVE_ROOT.get() is None
        envelope = ms.sofer_validate(config="dataset.toml")
        assert envelope["ok"] is True
        assert envelope["effective_root"] == str(tmp_path.resolve())

    def test_concurrent_calls_do_not_leak_roots(self, tmp_path) -> None:
        registration = tmp_path / "registration"
        registration.mkdir()
        first = _foreign_dataset(tmp_path)
        second = tmp_path / "second"
        second.mkdir()
        _make_dataset(second)
        build_server(root=registration)

        def _run(root: Path) -> str:
            return ms.sofer_validate(config="dataset.toml", root=str(root))["effective_root"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(_run, (first, second)))

        assert results == [str(first.resolve()), str(second.resolve())]
        assert ms._EFFECTIVE_ROOT.get() is None


class TestAllowlist:
    """``SOFER_MCP_ROOT_ALLOWLIST`` is build-time posture, pathsep-split."""

    def test_entries_admit_themselves_and_descendants(self, tmp_path, monkeypatch) -> None:
        allowed = tmp_path / "allowed"
        child = allowed / "child"
        child.mkdir(parents=True)
        _make_dataset(child)
        monkeypatch.setenv(ms._MCP_ROOT_ALLOWLIST_ENV_VAR, str(allowed))
        build_server(root=tmp_path)

        envelope = ms.sofer_validate(config="dataset.toml", root=str(child))

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(child.resolve())

    def test_a_root_outside_the_allowlist_names_it(self, tmp_path, monkeypatch) -> None:
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        foreign = _foreign_dataset(tmp_path)
        monkeypatch.setenv(ms._MCP_ROOT_ALLOWLIST_ENV_VAR, str(allowed))
        build_server(root=tmp_path)

        with pytest.raises(RootUnavailableError, match=ms._MCP_ROOT_ALLOWLIST_ENV_VAR):
            ms.sofer_validate(config="dataset.toml", root=str(foreign))

    def test_omitted_root_is_never_gated(self, tmp_path, monkeypatch) -> None:
        registration = tmp_path / "registration"
        registration.mkdir()
        _make_dataset(registration)
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv(ms._MCP_ROOT_ALLOWLIST_ENV_VAR, str(allowed))
        build_server(root=registration)

        envelope = ms.sofer_validate(config="dataset.toml")

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(registration.resolve())

    def test_a_comma_in_an_entry_survives(self, tmp_path, monkeypatch) -> None:
        allowed = tmp_path / "allowed,comma"
        allowed.mkdir()
        _make_dataset(allowed)
        monkeypatch.setenv(ms._MCP_ROOT_ALLOWLIST_ENV_VAR, str(allowed))
        build_server(root=tmp_path)

        envelope = ms.sofer_validate(config="dataset.toml", root=str(allowed))

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(allowed.resolve())


class TestEnvelopeAndChain:
    """The central echo, refusal envelopes, and continuation replay."""

    def test_refusal_envelopes_echo_the_effective_root(self, tmp_path) -> None:
        foreign = _foreign_dataset(tmp_path)
        build_server(root=tmp_path)

        envelope = ms.sofer_validate(config="missing.toml", root=str(foreign))

        assert envelope["ok"] is False, envelope
        assert envelope["effective_root"] == str(foreign.resolve())

    def test_the_validate_chain_replays_in_the_foreign_directory(self, tmp_path) -> None:
        foreign = _foreign_dataset(tmp_path)
        build_server(root=tmp_path)

        validate = ms.sofer_validate(config="dataset.toml", root=str(foreign))
        assert validate["ok"] is True, validate

        prepared = ms.sofer_prepare(**validate["next"]["arguments"])

        assert prepared["ok"] is True, prepared
        assert (foreign / "build").is_dir()

    def test_human_gate_payloads_are_left_untouched(self, tmp_path) -> None:
        foreign = _foreign_dataset(tmp_path)
        build_server(root=tmp_path)

        envelope = ms.sofer_publish(config="dataset.toml", root=str(foreign), dry_run=True)

        assert envelope["ok"] is True, envelope
        assert "arguments" not in envelope["next"] or "root" not in envelope["next"]["arguments"]

    def test_sofer_init_cwd_is_contained_under_the_effective_root(self, tmp_path) -> None:
        foreign = tmp_path / "foreign"
        (foreign / "dataset").mkdir(parents=True)
        build_server(root=tmp_path)

        envelope = ms.sofer_init(
            name="nested", user="user", cwd="dataset", root=str(foreign), dry_run=True
        )

        assert envelope["ok"] is True, envelope
        assert envelope["effective_root"] == str(foreign.resolve())
        assert envelope["dataset_root"] == str((foreign / "dataset").resolve())


class TestSchemaSurface:
    """``root`` comes from the signature; ``effective_root`` from one schema home."""

    def test_every_path_bearing_tool_exposes_an_optional_root(self, tmp_path) -> None:
        tools = _tools(build_server(root=tmp_path))

        for name in PATH_BEARING:
            props = tools[name].inputSchema.get("properties", {})
            assert "root" in props, f"{name} input schema missing root"
            root_schema = props["root"]
            assert root_schema.get("description"), f"{name} root without description"
            rendered = str(root_schema)
            assert "string" in rendered and "null" in rendered, (name, root_schema)

    def test_report_failure_stays_outside_the_root_surface(self, tmp_path) -> None:
        tools = _tools(build_server(root=tmp_path))

        props = tools["sofer_report_failure"].inputSchema.get("properties", {})
        assert "root" not in props
        assert "root" not in tools["sofer_report_failure"].outputSchema.get("properties", {})

    def test_every_output_schema_declares_effective_root(self, tmp_path) -> None:
        tools = _tools(build_server(root=tmp_path))

        for name, tool in tools.items():
            props = tool.outputSchema.get("properties", {})
            assert props.get("effective_root", {}).get("type") == "string", name
            assert "effective_root" not in tool.outputSchema.get("required", []), name
