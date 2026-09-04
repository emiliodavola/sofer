"""Process-boundary regression suite: stdio, CWD, recovery, config states.

Phases 3-4 (PRs 3-4) of the ``test-mcp-cli-regression-suite`` change (#119).
Proves the registered MCP server through the real stdio transport (PB-01),
the nested-dataset CWD containment of ``sofer_init`` (PB-04), the recovery
contract of PB-03 (executing the documented hint VALUES and asserting the
replayed call reaches a different gate or the intended branch), the
config-state scenarios of PB-04 (empty / existing / greenfield / triage /
malformed configs plus the delivery handoff), and the offline guarantee of
PB-06 (``publish._api`` monkeypatched, no real credentials).

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
``build_server()``; async uses ``asyncio.run`` (no pytest-asyncio). Config
fixtures come from ``tests/fixtures/`` (``mcp-config-states/`` for the
deliberately empty/malformed TOMLs, ``mcp-happy-path/`` for the offline
delivery handoff) — never re-implemented here.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import PROCESS_TIMEOUT_SECONDS, _make_dataset, call_tool

from sofer.mcp_server import build_server

#: Offline happy-path fixture tree (dataset.toml + data.csv), PB-04.
MCP_HAPPY_PATH = Path(__file__).parent / "fixtures" / "mcp-happy-path"
#: Deliberately empty and malformed dataset TOMLs, PB-04.
MCP_CONFIG_STATES = Path(__file__).parent / "fixtures" / "mcp-config-states"


def _run(coro: Any) -> Any:
    """Run one async client interaction per test (asyncio.run convention)."""
    return asyncio.run(coro)


def _call(server: Any, name: str, args: dict[str, Any] | None = None) -> Any:
    """Call a registered tool through the shared client wrapper (PB-09)."""
    return call_tool(server, name, args)


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
                # read_timeout_seconds (mcp 1.29.1 ClientSession kwarg) makes a
                # server that never responds fail this test loudly via a
                # timeout instead of hanging CI indefinitely (R4 hardening).
                async with ClientSession(
                    read, write, read_timeout_seconds=timedelta(seconds=PROCESS_TIMEOUT_SECONDS)
                ) as session:
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

        envelope = _call(server, "sofer_init", {"name": "nested-ds", "user": "testuser"}).data
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
        _make_dataset(tmp_path)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        server = build_server(root=tmp_path, approval_phrase="s3cret")
        args: dict[str, Any] = {"config": str(tmp_path / "dataset.toml")}

        first = _call(server, "sofer_publish_confirm", args).data
        assert first["ok"] is False
        assert first["acknowledge_risk"] is False
        # Boundary-visible refusal (output_schema drops error_code/next): the
        # reason is the human-readable message naming the required hint.
        assert "acknowledge_risk=True" in first["output"]

        # Replay with the documented hint VALUE for the risk gate refusal (mcp_server
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
        args: dict[str, Any] = {"name": "my-ds", "user": "testuser", "cwd": str(tmp_path)}

        first = _call(server, "sofer_init", args).data
        assert first["ok"] is True
        (tmp_path / "my-ds.toml").write_text("custom", encoding="utf-8")

        refused = _call(server, "sofer_init", args).data
        assert refused["ok"] is False
        assert refused["exit_code"] == 1
        assert any("File already exists" in e for e in refused["config_errors"])

        # Documented hint VALUE for the file-exists refusal (mcp_server.py:
        # {"force": True}) merged into the replayed args.
        replayed = _call(server, "sofer_init", {**args, "force": True}).data
        assert replayed["ok"] is True
        expected = _INIT_TEMPLATE.format(name="my-ds", user="testuser")
        assert (tmp_path / "my-ds.toml").read_text(encoding="utf-8") == expected

    def test_replay_corrected_name_past_name_empty(
        self, tmp_path: Path, restore_tool_config: Any
    ) -> None:
        """Name-empty refusal (documented hint ``{}``) replayed with a
        corrected non-empty name reaches the intended branch."""
        from sofer.cli import _INIT_TEMPLATE

        server = build_server(root=tmp_path)

        refused = _call(
            server, "sofer_init", {"name": "   ", "user": "testuser", "cwd": str(tmp_path)}
        ).data
        assert refused["ok"] is False
        assert refused["exit_code"] == 1
        assert any("non-empty" in e for e in refused["config_errors"])
        assert not list(tmp_path.glob("*.toml"))

        # Documented hint VALUE for the name-empty refusal is {} — the
        # correction is a non-empty name in the replayed args.
        replayed = _call(
            server, "sofer_init", {"name": "my-ds", "user": "testuser", "cwd": str(tmp_path)}
        ).data
        assert replayed["ok"] is True
        expected = _INIT_TEMPLATE.format(name="my-ds", user="testuser")
        assert (tmp_path / "my-ds.toml").read_text(encoding="utf-8") == expected


class TestConfigStates:
    """PB-04: config-state scenarios through the client boundary.

    Uses the real fixture TOMLs (``mcp-config-states/`` for the deliberately
    empty and malformed configs, ``mcp-happy-path/`` for the registered
    happy-path tree) — never dataclass or private-helper construction alone.
    """

    def test_empty_config_documented_result(self, tmp_path: Path, restore_tool_config: Any) -> None:
        """Empty TOML (valid, no ``[[file]]``) validates to the documented
        empty-config refusal: ``ok:False`` + ``config_errors`` naming the
        missing file entries."""
        shutil.copy2(MCP_CONFIG_STATES / "empty.toml", tmp_path / "empty.toml")
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_validate", {"config": str(tmp_path / "empty.toml")}).data
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1
        assert any("No [[file]] entries" in error for error in envelope["config_errors"]), envelope[
            "config_errors"
        ]
        # The human-readable refusal is the boundary-visible ``output``
        # (error_code/message/next are dropped by output_schema).
        assert "No [[file]] entries" in envelope["output"]

    def test_existing_config_validates_without_registration(
        self, tmp_path: Path, restore_tool_config: Any
    ) -> None:
        """The happy-path TOML (registered files) validates through the client
        WITHOUT re-registration: no scan, files already declared on disk."""
        shutil.copy2(MCP_HAPPY_PATH / "dataset.toml", tmp_path / "dataset.toml")
        shutil.copy2(MCP_HAPPY_PATH / "data.csv", tmp_path / "data.csv")
        server = build_server(root=tmp_path)

        envelope = _call(server, "sofer_validate", {"config": str(tmp_path / "dataset.toml")}).data
        assert envelope["ok"] is True, envelope
        assert envelope["exit_code"] == 0
        assert envelope["config_errors"] == []

    def test_greenfield_bootstrap_init_scan_apply_validate(
        self, tmp_path: Path, restore_tool_config: Any
    ) -> None:
        """Greenfield bootstrap: ``sofer_init`` scaffolds TOML + ``raw/``,
        ``sofer_scan_apply`` registers the discovered file and copies it into
        ``cache/``, and ``sofer_validate`` then passes.

        ``user`` is passed so the generated ``repo_id`` carries a real user
        (the init template's ``YOUR_USER`` placeholder would otherwise trip
        validation); the template's placeholder ``[[file]]`` entries are
        stripped by the scanner's merge (scanner.merge_entries).
        """
        server = build_server(root=tmp_path)

        init = _call(
            server,
            "sofer_init",
            {"name": "green-ds", "user": "myuser", "cwd": str(tmp_path)},
        ).data
        assert init["ok"] is True, init
        assert (tmp_path / "green-ds.toml").is_file()
        assert (tmp_path / "raw").is_dir()

        (tmp_path / "raw" / "data.csv").write_text("col_a;col_b\n1;2\n3;4\n", encoding="utf-8-sig")
        applied = _call(
            server, "sofer_scan_apply", {"config": str(tmp_path / "green-ds.toml")}
        ).data
        assert applied["ok"] is True, applied
        assert applied["copied"] == 1
        assert (tmp_path / "cache" / "data.csv").is_file()

        validated = _call(
            server, "sofer_validate", {"config": str(tmp_path / "green-ds.toml")}
        ).data
        assert validated["ok"] is True, validated

    def test_triage_scan_dry_run_preview_read_only(
        self, tmp_path: Path, restore_tool_config: Any
    ) -> None:
        """Triage preview: ``sofer_scan_dry_run`` lists the candidates it
        would register/copy WITHOUT copying files or writing the TOML."""
        _make_dataset(tmp_path)
        (tmp_path / "new.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")
        before = (tmp_path / "dataset.toml").read_text(encoding="utf-8")
        server = build_server(root=tmp_path)

        preview = _call(
            server, "sofer_scan_dry_run", {"config": str(tmp_path / "dataset.toml")}
        ).data
        assert preview["ok"] is True, preview
        assert preview["discovered"] == 2  # data.csv (registered) + new.csv
        assert preview["registered"] == 1  # only new.csv is new
        assert "new.csv" in preview["output"]  # candidates are listed
        assert "->" in preview["output"]
        assert not (tmp_path / "cache").exists(), "dry-run must not copy files"
        assert (tmp_path / "dataset.toml").read_text(encoding="utf-8") == before

    def test_malformed_config_refuses_with_config_errors(
        self, tmp_path: Path, restore_tool_config: Any
    ) -> None:
        """Unparseable TOML validates to a refusal envelope carrying
        ``config_errors`` naming the parse failure."""
        shutil.copy2(MCP_CONFIG_STATES / "malformed.toml", tmp_path / "malformed.toml")
        server = build_server(root=tmp_path)

        envelope = _call(
            server, "sofer_validate", {"config": str(tmp_path / "malformed.toml")}
        ).data
        assert envelope["ok"] is False
        assert envelope["exit_code"] == 1
        assert any("Failed to read TOML" in error for error in envelope["config_errors"]), envelope[
            "config_errors"
        ]
        assert "Failed to read TOML" in envelope["output"]


class TestDeliveryHandoff:
    """PB-04/PB-06: the full offline delivery chain through the client."""

    def test_handoff_pipeline_reaches_upload_branch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        restore_tool_config: Any,
    ) -> None:
        """validate -> prepare -> codebook_all -> profile_all -> render_all ->
        publish(dry_run=True) -> publish_confirm through the client, with
        ``publish._api`` monkeypatched and ``HF_TOKEN`` set (PB-06): the
        dry-run plan is returned and the confirm reaches the upload branch
        (proven by the ``upload_folder`` spy, never by real network).
        """
        for item in MCP_HAPPY_PATH.iterdir():
            dest = tmp_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        import sofer.config as cfg

        cfg.reload(tmp_path)

        import sofer.publish as pub_mod

        monkeypatch.setattr(pub_mod._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(pub_mod._api, "list_repo_files", lambda *a, **kw: [])
        upload_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        def _fake_upload(*a: Any, **kw: Any) -> None:
            upload_calls.append((a, kw))

        monkeypatch.setattr(pub_mod._api, "upload_folder", _fake_upload)

        def _fake_hf_api(*_a: Any, **_kw: Any) -> Any:
            return pub_mod._api

        monkeypatch.setattr(pub_mod, "HfApi", _fake_hf_api)
        monkeypatch.setenv("HF_TOKEN", "hf_test_token")
        server = build_server(root=tmp_path)
        config_arg = str(tmp_path / "dataset.toml")

        validated = _call(server, "sofer_validate", {"config": config_arg}).data
        assert validated["ok"] is True, validated

        prepared = _call(server, "sofer_prepare", {"config": config_arg}).data
        assert prepared["ok"] is True, prepared

        codebooks = _call(server, "sofer_codebook_all", {"config": config_arg}).data
        assert codebooks["ok"] is True, codebooks

        profiles = _call(server, "sofer_profile_all", {"config": config_arg}).data
        assert profiles["ok"] is True, profiles

        renders = _call(server, "sofer_render_all", {"config": config_arg}).data
        assert renders["ok"] is True, renders

        plan = _call(server, "sofer_publish", {"config": config_arg, "dry_run": True}).data
        assert plan["ok"] is True, plan
        assert plan["dry_run"] is True

        # confidential=false in the fixture, so acknowledge_risk alone
        # satisfies the acknowledgments (no confidential ack, no approval
        # phrase on this server).
        confirmed = _call(
            server,
            "sofer_publish_confirm",
            {"config": config_arg, "acknowledge_risk": True},
        ).data
        assert confirmed["ok"] is True, confirmed
        assert confirmed["acknowledge_risk"] is True
        assert len(upload_calls) == 1, f"expected 1 upload_folder call, got {len(upload_calls)}"
        # The mocked boundary receives the real HfApi.upload_folder call, which
        # publish.py:184 issues keyword-only (folder_path/path_in_repo/repo_id/
        # repo_type), so the spy's positional tuple is empty and the args live
        # in the kwargs dict. publish.py:716-719 stages into
        # tempfile.mkdtemp()/"repo" and rmtree()s that tmpdir in a finally
        # right after the upload call (publish.py:745), so the staging dir no
        # longer exists at assert time — pin the staging contract instead:
        # a "repo" leaf directly under a mkdtemp dir under the system temp.
        upload_kwargs = upload_calls[0][1]
        assert upload_kwargs["repo_id"] == "user/mcp-happy-path", upload_kwargs
        staging = Path(upload_kwargs["folder_path"])
        assert staging.name == "repo", upload_kwargs
        assert staging.parent.parent == Path(tempfile.gettempdir()), upload_kwargs
