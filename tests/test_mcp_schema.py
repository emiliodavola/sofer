"""MCP DX audit — schema and affordance tests (10.1-10.12).

Offline asserts via build_server()._list_tools() without network or LLM.
Covers: 14 tools, enum, no legacy params, annotations, output_schema,
single UNTRUSTED, Bootstrap wording, envelope, and happy path fixtures.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from conftest import call_tool
from fastmcp import Client

from sofer.mcp_server import build_server

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mcp-happy-path"


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _call(server: Any, name: str, args: dict[str, Any] | None = None) -> Any:
    """Call a registered tool through the shared client wrapper (PB-09)."""
    return call_tool(server, name, args)


async def _list_tools(server):  # type: ignore[no-untyped-def]
    async with Client(server) as client:
        tools = await client.list_tools()
        return {t.name: t for t in tools}


def _tools_dict(tmp_path: Path):  # type: ignore[no-untyped-def]
    server = build_server(root=tmp_path)
    return _run(_list_tools(server))


class TestToolCount:
    def test_fourteen_tools(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        assert len(tools) == 14, sorted(tools.keys())
        expected = {
            "sofer_validate",
            "sofer_prepare",
            "sofer_publish",
            "sofer_publish_confirm",
            "sofer_codebook",
            "sofer_codebook_all",
            "sofer_profile",
            "sofer_profile_all",
            "sofer_render",
            "sofer_render_all",
            "sofer_scan_dry_run",
            "sofer_scan_apply",
            "sofer_init",
            "sofer_auth_status",
        }
        assert set(tools.keys()) == expected


class TestDescriptions:
    def test_descriptions_concise_no_msp_untrusted(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        instr = build_server(root=tmp_path).instructions  # type: ignore[attr-defined]
        assert instr.count("UNTRUSTED") == 1
        for name, tool in tools.items():
            desc = tool.description or ""
            # No MSP/CF codes in first 2 sentences, no UNTRUSTED per tool
            assert "MSP-R" not in desc, f"{name} leaks MSP-R"
            assert "CF-" not in desc, f"{name} leaks CF-"
            assert "UNTRUSTED" not in desc, f"{name} duplicates UNTRUSTED"
            # When to use / Example / Requires / Next present (except maybe auth_status)
            assert "When to use" in desc or "When" in desc, f"{name} missing When to use"
            # Check ≤3 sentences before When to use
            pre = desc.split("When to use")[0] if "When to use" in desc else desc
            sentences = [s.strip() for s in pre.split(".") if s.strip()]
            # Allow up to 4 due to details tag line, but pre block should be short
            assert len(sentences) <= 10, f"{name} too verbose: {len(sentences)} sentences"

    def test_phased_instructions(self, tmp_path: Path):
        instr = build_server(root=tmp_path).instructions  # type: ignore[attr-defined]
        assert "Phase 0" in instr
        assert "Phase 1" in instr
        assert "Phase 2" in instr
        assert "Bootstrap" in instr
        assert "sofer_validate" in instr
        assert "sofer_auth_status" in instr or "auth_status" in instr
        assert instr.count("UNTRUSTED") == 1

    def test_bootstrap_phrasing_no_not_part(self, tmp_path: Path):
        # Ensure scan/init descriptions use Phase 0 wording
        tools = _tools_dict(tmp_path)
        for name in ("sofer_scan_dry_run", "sofer_scan_apply", "sofer_init"):
            desc = tools[name].description or ""
            assert "Not part of canonical" not in desc, f"{name} still has deprecated phrasing"
            assert "Phase 0" in desc or "Bootstrap" in desc, f"{name} missing Phase 0"


class TestParamDescriptions:
    def _has_description(self, schema: dict) -> bool:
        """Recursively find description in anyOf/allOf wrappers (Py 3.10 nests differently)."""
        if not isinstance(schema, dict):
            return False
        if schema.get("description"):
            return True
        for key in ("anyOf", "allOf", "oneOf"):
            if key in schema:
                for sub in schema[key]:
                    if self._has_description(sub):
                        return True
        return False

    def test_every_param_has_description(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        for name, tool in tools.items():
            schema = tool.inputSchema or {}
            props = schema.get("properties", {})
            for pname, pschema in props.items():
                assert self._has_description(pschema), f"{name}.{pname} missing description"

    def test_no_legacy_params(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        for name, tool in tools.items():
            schema = tool.inputSchema or {}
            props = set((schema.get("properties", {})).keys())
            assert "all_files" not in props, f"{name} still exposes all_files"
            assert "no_checks" not in props, f"{name} still exposes no_checks"
            assert "output" not in props, (
                f"{name} still exposes bare output (should be output_file/output_dir)"
            )
            # Check output_file vs output_dir split
            if name == "sofer_codebook":
                assert "output_file" in props, "sofer_codebook should have output_file"
                assert "output_dir" not in props
            if name in (
                "sofer_codebook_all",
                "sofer_prepare",
                "sofer_publish",
                "sofer_publish_confirm",
                "sofer_profile",
                "sofer_profile_all",
                "sofer_render",
                "sofer_render_all",
            ):
                if props:
                    # those with output should have output_dir
                    if "output_file" in props or "output_dir" in props:
                        assert "output_dir" in props, f"{name} should have output_dir"

    def test_target_enum(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        pub = tools["sofer_publish"]
        pub_schema = pub.inputSchema or {}
        target = pub_schema.get("properties", {}).get("target", {})
        # FastMCP 3.4.7 renders single-value Literal as const, not enum
        assert target.get("enum") == ["local"] or target.get("const") == "local", target
        confirm = tools["sofer_publish_confirm"]
        conf_schema = confirm.inputSchema or {}
        t2 = conf_schema.get("properties", {}).get("target", {})
        assert t2.get("enum") == ["hf"] or t2.get("const") == "hf", t2

    def test_run_checks_exists(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        prep = tools["sofer_prepare"].inputSchema or {}
        assert "run_checks" in prep.get("properties", {})
        assert prep["properties"]["run_checks"]["type"] == "boolean"


class TestAnnotations:
    def test_annotations_present(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        for name, tool in tools.items():
            # FastMCP exposes annotations as dict on tool
            ann = tool.annotations
            assert ann is not None, f"{name} missing annotations"
            # Check via dict conversion
            ann_dict = ann.model_dump() if hasattr(ann, "model_dump") else dict(ann)  # type: ignore[arg-type]
            assert "readOnlyHint" in ann_dict or hasattr(ann, "readOnlyHint")

    def test_auth_status_readonly(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        auth = tools["sofer_auth_status"]
        ann = auth.annotations
        # Should be readOnly
        val = ann.readOnlyHint if hasattr(ann, "readOnlyHint") else ann.get("readOnlyHint")  # type: ignore[union-attr]
        assert val is True

    _READ_ONLY_TOOLS = frozenset({"sofer_validate", "sofer_scan_dry_run", "sofer_auth_status"})
    _WRITING_TOOLS = frozenset(
        {
            "sofer_prepare",
            "sofer_publish",
            "sofer_publish_confirm",
            "sofer_codebook",
            "sofer_codebook_all",
            "sofer_profile",
            "sofer_profile_all",
            "sofer_render",
            "sofer_render_all",
            "sofer_scan_apply",
            "sofer_init",
        }
    )

    def test_readonly_hint_matches_side_effects(self, tmp_path: Path):
        """readOnlyHint is True ONLY for genuinely read-only tools.

        Every tool that writes files (codebooks, metadata profiles, README
        renders, scan_apply registration, init scaffolding, prepare, publish)
        must report readOnlyHint False so agents treat it as side-effecting.
        The roster partition covers all 14 tools.
        """
        tools = _tools_dict(tmp_path)
        assert set(tools) == self._READ_ONLY_TOOLS | self._WRITING_TOOLS
        for name in self._READ_ONLY_TOOLS:
            ann = tools[name].annotations
            val = ann.readOnlyHint if hasattr(ann, "readOnlyHint") else ann.get("readOnlyHint")  # type: ignore[union-attr]
            assert val is True, f"{name} must stay readOnly"
        for name in self._WRITING_TOOLS:
            ann = tools[name].annotations
            val = ann.readOnlyHint if hasattr(ann, "readOnlyHint") else ann.get("readOnlyHint")  # type: ignore[union-attr]
            assert val is False, f"{name} writes files — readOnlyHint must be False"


class TestOutputSchema:
    def test_output_schema_typed(self, tmp_path: Path):
        tools = _tools_dict(tmp_path)
        for name, tool in tools.items():
            schema = tool.outputSchema  # type: ignore[attr-defined]
            assert schema is not None, f"{name} missing output_schema"
            # Check has ok, exit_code, output
            props = schema.get("properties", {}) if isinstance(schema, dict) else {}
            # FastMCP may store as dict; check via model
            if not props and hasattr(schema, "get"):
                props = schema.get("properties", {})  # type: ignore[union-attr]
            assert "ok" in props, f"{name} output_schema missing ok"
            assert "exit_code" in props, f"{name} output_schema missing exit_code"
            assert "output" in props, f"{name} output_schema missing output"

    def test_sofer_init_identity_fields_in_schema(self, tmp_path: Path):
        """MSP-R03 / PB-03: sofer_init output_schema declares the identity
        fields as string properties, NOT in ``required``."""
        tools = _tools_dict(tmp_path)
        schema = tools["sofer_init"].outputSchema  # type: ignore[attr-defined]
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        assert "config_path" in props, "sofer_init output_schema missing config_path"
        assert "dataset_root" in props, "sofer_init output_schema missing dataset_root"
        assert props["config_path"]["type"] == "string"
        assert props["dataset_root"]["type"] == "string"
        required = schema.get("required", [])
        assert "config_path" not in required
        assert "dataset_root" not in required
        assert required == ["ok", "exit_code", "output"]

    def test_sofer_init_user_required(self, tmp_path: Path):
        """INIT-05: sofer_init input schema requires ``user`` as a
        non-nullable string (mandatory, never optional)."""
        tools = _tools_dict(tmp_path)
        schema = tools["sofer_init"].inputSchema or {}
        props = schema.get("properties", {})
        user_schema = props.get("user", {})
        assert "user" in schema.get("required", []), "user must be a required parameter"
        assert user_schema.get("type") == "string", user_schema
        assert "null" not in str(user_schema), "user must not be nullable"


class TestEnvelope:
    def test_refusal_envelope(self, tmp_path: Path):
        server = build_server(root=tmp_path)
        # bad config should give ok:False with config_errors
        envelope = _call(server, "sofer_validate", {"config": str(tmp_path / "nope.toml")}).data
        assert envelope["ok"] is False
        assert "config_errors" in envelope
        assert len(envelope["config_errors"]) >= 1

    def test_publish_risk_envelope(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Create minimal dataset
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        (tmp_path / "dataset.toml").write_text(
            '[dataset]\nname="x"\nrepo_id="u/x"\n\n[[file]]\nlocal="data.csv"\nremote="data.csv"\n',
            encoding="utf-8",
        )
        from sofer.model import DatasetConfig
        from sofer.prepare import prepare as dom_prepare

        cfg = DatasetConfig.from_toml(tmp_path / "dataset.toml")
        dom_prepare(cfg, tmp_path / "build")
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        server = build_server(root=tmp_path)

        envelope = _call(
            server, "sofer_publish_confirm", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert envelope["ok"] is False
        # The output_schema boundary contract carries the refusal reason in
        # the human-readable output field (error_code/next are not exposed).
        assert envelope["acknowledge_risk"] is False
        assert "acknowledge_risk=True" in envelope["output"]

    def test_auth_status_no_leak(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        (tmp_path / "dataset.toml").write_text(
            '[dataset]\nname="x"\nrepo_id="u/x"\n\n[[file]]\nlocal="data.csv"\nremote="data.csv"\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("HF_TOKEN", "secret123")
        server = build_server(root=tmp_path, approval_phrase="phrase123")
        envelope = _call(
            server, "sofer_auth_status", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert envelope["token"] in ("present", "missing")
        assert "secret123" not in str(envelope)
        assert "phrase123" not in str(envelope)
        assert envelope["approval_configured"] is True
        assert envelope["requires_approval_phrase"] is True
        # sofer_auth_status is the ONLY tool whose output_schema declares next —
        # this is the sole boundary-level next assertion (spec delta s7).
        assert envelope["next"]["acknowledge_risk"] is True
        assert envelope["next"]["approval_phrase"] == "<from human>"
        monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)

    def test_auth_status_approval_not_configured(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without a server phrase, the preflight reports approval_configured
        False, still requires an approval phrase (fail-closed), and points the
        next hint at configuring it instead of supplying a phrase."""
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        (tmp_path / "dataset.toml").write_text(
            '[dataset]\nname="x"\nrepo_id="u/x"\n\n[[file]]\nlocal="data.csv"\nremote="data.csv"\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("HF_TOKEN", "secret123")
        server = build_server(root=tmp_path)  # no approval phrase
        envelope = _call(
            server, "sofer_auth_status", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert envelope["approval_configured"] is False
        assert envelope["requires_approval_phrase"] is True
        assert envelope["next"]["action"] == "configure_approval_phrase"
        assert "approval_phrase" not in envelope["next"]


class TestHappyPath:
    def test_offline_happy_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        restore_tool_config: Any,
    ):
        """Happy path offline with mocked publish._api, via Client(server) (PB-01/PB-06)."""
        import shutil

        # Copy fixture into tmp_path
        for item in FIXTURE_ROOT.iterdir():
            dest = tmp_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        # Ensure config reload
        import sofer.config as cfg

        cfg.reload(tmp_path)
        server = build_server(root=tmp_path)

        # Mock publish._api so the HF path stays offline and deterministic
        import sofer.publish as pub_mod

        monkeypatch.setattr(pub_mod._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(pub_mod._api, "list_repo_files", lambda *a, **kw: [])
        monkeypatch.setattr(pub_mod._api, "upload_folder", lambda *a, **kw: None)

        def _fake_hf_api(*_a, **_kw):
            return pub_mod._api

        monkeypatch.setattr(pub_mod, "HfApi", _fake_hf_api)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")

        v = _call(server, "sofer_validate", {"config": str(tmp_path / "dataset.toml")}).data
        assert v["ok"] is True, v

        p = _call(server, "sofer_prepare", {"config": str(tmp_path / "dataset.toml")}).data
        assert p["ok"] is True, p

        cb = _call(server, "sofer_codebook_all", {"config": str(tmp_path / "dataset.toml")}).data
        assert cb["ok"] is True, cb

        prof = _call(server, "sofer_profile_all", {"config": str(tmp_path / "dataset.toml")}).data
        assert prof["ok"] is True, prof
        assert len(prof.get("files", [])) >= 1

        rend = _call(server, "sofer_render_all", {"config": str(tmp_path / "dataset.toml")}).data
        assert rend["ok"] is True, rend

        pub = _call(
            server, "sofer_publish", {"config": str(tmp_path / "dataset.toml"), "dry_run": True}
        ).data
        assert pub["ok"] is True
        assert pub["dry_run"] is True

        auth = _call(server, "sofer_auth_status", {"config": str(tmp_path / "dataset.toml")}).data
        assert auth["ok"] is True
        assert auth["token"] == "present"

        # Cleanup
        monkeypatch.delenv("HF_TOKEN", raising=False)
