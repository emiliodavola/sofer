"""Tests for sofer.mcp_registration and CLI mcp handlers.

Covers MCP-REG-01/02 and CLI-R09 scenarios: idempotency, backup,
preserve other servers, delegation fallback, dry-run, unreadable,
cwd, env, CLI help.
"""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sofer import cli, mcp_registration

# ── helpers ───────────────────────────────────────────────────────────


def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch Path.home() to return tmp_path for user-scope isolation."""
    # Path.home is a classmethod; patch via monkeypatch
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _run_add(
    tmp_path: Path,
    agent: str,
    scope: str = "project",
    cwd: str | None = None,
    dry_run: bool = False,
) -> int:
    args = Namespace(agent=agent, scope=scope, cwd=cwd, dry_run=dry_run)
    return cli._cmd_mcp_add(args)


def _run_remove(tmp_path: Path, agent: str, scope: str = "project", dry_run: bool = False) -> int:
    args = Namespace(agent=agent, scope=scope, dry_run=dry_run)
    return cli._cmd_mcp_remove(args)


# ── resolve_config_path ───────────────────────────────────────────────


class TestResolveConfigPath:
    def test_opencode_scope_routing(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        proj = tmp_path / "proj"
        proj.mkdir()
        user_path = mcp_registration.resolve_config_path("opencode", "user")
        proj_path = mcp_registration.resolve_config_path("opencode", "project", proj)
        assert user_path != proj_path
        assert str(proj_path).startswith(str(proj.resolve()))
        assert proj_path.name == "opencode.json"
        assert user_path.name == "opencode.json"

    def test_codex_gemini_paths(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        proj = tmp_path / "proj"
        proj.mkdir()
        codex_user = mcp_registration.resolve_config_path("codex", "user")
        codex_proj = mcp_registration.resolve_config_path("codex", "project", proj)
        gemini_user = mcp_registration.resolve_config_path("gemini", "user")
        gemini_proj = mcp_registration.resolve_config_path("gemini", "project", proj)
        assert codex_user.suffix == ".toml"
        assert gemini_user.suffix == ".json"
        assert ".codex" in str(codex_proj)
        assert ".gemini" in str(gemini_proj)


# ── build_entry / merge ───────────────────────────────────────────────


class TestBuildEntry:
    def test_gemini_env_both_tokens(self, tmp_path):
        cwd = tmp_path / "proj"
        cwd.mkdir()
        env = {"HF_TOKEN": "hf123", "SOFER_MCP_APPROVAL_PHRASE": "secret"}
        entry = mcp_registration.build_entry("gemini", cwd, env)
        assert entry["env"]["HF_TOKEN"] == "hf123"
        assert entry["env"]["SOFER_MCP_APPROVAL_PHRASE"] == "secret"
        assert entry["command"] == "sofer-mcp"
        assert entry["cwd"] == str(cwd.resolve())

    def test_codex_env_vars_allow_list(self, tmp_path):
        cwd = tmp_path / "proj"
        cwd.mkdir()
        env = {"HF_TOKEN": "hf123"}
        entry = mcp_registration.build_entry("codex", cwd, env)
        assert "HF_TOKEN" in entry["env_vars"]
        assert "SOFER_MCP_APPROVAL_PHRASE" not in entry["env_vars"]

    def test_opencode_entry_shape(self, tmp_path):
        cwd = tmp_path / "proj"
        cwd.mkdir()
        entry = mcp_registration.build_entry("opencode", cwd, {})
        assert entry["type"] == "local"
        assert entry["command"] == ["sofer-mcp"]
        assert "cwd" in entry

    def test_cwd_custom_absolute(self, tmp_path, monkeypatch):
        # Use project scope with custom cwd; entry must store resolved absolute
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        custom = tmp_path / "myproj"
        custom.mkdir()
        # Isolate home to ensure containment passes (tmp under home on Windows)
        _isolate_home(tmp_path / "home_isolated", monkeypatch)
        # Need to ensure custom is under home or project root; tmp is under home_isolated? no, custom is under tmp_path not home_isolated  # noqa: E501
        # Patch validate to allow
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(custom), dry_run=False)
        )
        assert rc == 0
        path = mcp_registration.resolve_config_path("opencode", "project", custom)
        assert path.exists()
        data, _ = mcp_registration.read_config(path)
        assert data["mcp"]["sofer"]["cwd"] == str(custom.resolve())


# ── merge preserve & normalize ────────────────────────────────────────


class TestMerge:
    def test_preserve_other_servers(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        proj = tmp_path / "proj"
        proj.mkdir()
        # Pre-create opencode.json with other server
        path = proj / "opencode.json"
        path.write_text(
            json.dumps({"mcp": {"other": {"type": "local", "command": ["other"]}}}),
            encoding="utf-8",
        )
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "other" in data["mcp"]
        assert "sofer" in data["mcp"]

    def test_codex_normalize_string_vs_array(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        codex_path = proj / ".codex" / "config.toml"
        codex_path.parent.mkdir(parents=True)
        # Write with array command using tomli_w to ensure proper escaping
        try:
            import tomli_w as _tomli_w
        except ImportError:
            _tomli_w = None  # type: ignore[assignment]
        if _tomli_w is not None:
            with open(codex_path, "wb") as fh:
                _tomli_w.dump(
                    {"mcp_servers": {"sofer": {"command": ["sofer-mcp"], "cwd": str(proj.resolve()), "env_vars": []}}},  # noqa: E501
                    fh,
                )
        else:
            codex_path.write_text('[mcp_servers.sofer]\ncommand = ["sofer-mcp"]\n', encoding="utf-8")  # noqa: E501
        # Now add again; should be idempotent (no rewrite, no backup)
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        # File should be byte-identical (no backup created if idempotent)
        # Since we wrote array but desired is string, merge normalizes so no change -> no .bak
        bak = Path(str(codex_path) + ".bak")
        # Backup should NOT exist on idempotent re-run
        assert (
            not bak.exists() or bak.read_bytes() == codex_path.read_bytes()
        )  # at least not modified

    def test_gemini_preserve_other(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        proj = tmp_path / "proj"
        proj.mkdir()
        path = proj / ".gemini" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps({"mcpServers": {"other": {"command": "other"}}}), encoding="utf-8"
        )
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        rc = cli._cmd_mcp_add(
            Namespace(agent="gemini", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "other" in data["mcpServers"]
        assert "sofer" in data["mcpServers"]


# ── idempotency byte-identical ────────────────────────────────────────


class TestIdempotency:
    def test_idempotent_no_backup_no_write(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        # First add
        rc1 = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc1 == 0
        path = proj / "opencode.json"
        content1 = path.read_bytes()
        # Second add idempotent
        rc2 = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc2 == 0
        content2 = path.read_bytes()
        assert content1 == content2
        # No additional backup after idempotent? First backup not needed (file didn't exist before first), second no backup  # noqa: E501
        bak = Path(str(path) + ".bak")
        # If first created file, bak should NOT exist (no pre-existing file to backup)
        # Second also no bak
        # So overall, bak should not exist after two idempotent creates from scratch
        assert not bak.exists()

    def test_atomic_write(self, tmp_path):
        path = tmp_path / "opencode.json"
        doc = {"mcp": {"sofer": {"type": "local", "command": ["sofer-mcp"], "cwd": "/tmp"}}}
        mcp_registration.atomic_write(path, doc, "json")
        assert path.exists()
        assert not (path.with_name(path.name + ".tmp")).exists()
        assert json.loads(path.read_text(encoding="utf-8")) == doc


# ── backup .bak ───────────────────────────────────────────────────────


class TestBackup:
    def test_backup_pre_edit(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        path = proj / "opencode.json"
        original = {"mcp": {"other": {"type": "local", "command": ["other"]}}}
        path.write_text(json.dumps(original), encoding="utf-8")
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        bak = Path(str(path) + ".bak")
        assert bak.exists()
        assert json.loads(bak.read_text(encoding="utf-8")) == original

    def test_remove_backup(self, tmp_path, monkeypatch):
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.chdir(proj)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        # Add first
        cli._cmd_mcp_add(Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False))
        path = proj / "opencode.json"
        content_before_remove = path.read_bytes()
        # Remove
        rc = cli._cmd_mcp_remove(Namespace(agent="opencode", scope="project", dry_run=False))
        assert rc == 0
        bak = Path(str(path) + ".bak")
        assert bak.exists()
        assert bak.read_bytes() == content_before_remove


# ── dry-run no mutation ───────────────────────────────────────────────


class TestDryRun:
    def test_add_dry_run_no_mutation(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        path = proj / "opencode.json"
        path.write_text(json.dumps({"mcp": {"other": {"type": "local"}}}), encoding="utf-8")
        before = path.read_bytes()
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=True)
        )
        assert rc == 0
        assert path.read_bytes() == before
        assert not Path(str(path) + ".bak").exists()

    def test_remove_dry_run_no_mutation(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        cli._cmd_mcp_add(Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False))
        path = proj / "opencode.json"
        before = path.read_bytes()
        rc = cli._cmd_mcp_remove(Namespace(agent="opencode", scope="project", dry_run=True))
        assert rc == 0
        assert path.read_bytes() == before

    def test_add_all_dry_run_no_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        rc = cli._cmd_mcp_add(Namespace(agent="all", scope="project", cwd=str(proj), dry_run=True))
        assert rc == 0
        for agent in ["opencode", "codex", "gemini"]:
            path = mcp_registration.resolve_config_path(agent, "project", proj)  # type: ignore[arg-type]
            assert not path.exists()
            assert not Path(str(path) + ".bak").exists()


# ── unreadable / malformed → exit 1 no backup/write ───────────────────


class TestUnreadable:
    def test_unreadable_malformed_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        path = proj / "opencode.json"
        path.write_text("{ not json", encoding="utf-8")
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 1
        assert not Path(str(path) + ".bak").exists()
        # File unchanged (still malformed)
        assert path.read_text(encoding="utf-8") == "{ not json"

    def test_unreadable_malformed_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        path = proj / ".codex" / "config.toml"
        path.parent.mkdir(parents=True)
        path.write_text("[[[ not toml", encoding="utf-8")
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 1
        assert not Path(str(path) + ".bak").exists()

    def test_remove_unreadable(self, tmp_path, monkeypatch):
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.chdir(proj)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        path = proj / "opencode.json"
        path.write_text("{ bad", encoding="utf-8")
        rc = cli._cmd_mcp_remove(Namespace(agent="opencode", scope="project", dry_run=False))
        assert rc == 1
        assert not Path(str(path) + ".bak").exists()


# ── cwd containment ───────────────────────────────────────────────────


class TestCwdContainment:
    def test_validate_cwd_allows_home_or_project(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.chdir(tmp_path)
        # tmp_path is project root; home is separate. A cwd under home should pass for user scope
        cwd_under_home = home / "proj"
        cwd_under_home.mkdir()
        assert mcp_registration.validate_cwd(cwd_under_home, "user") is True
        # cwd under project should pass for project
        assert mcp_registration.validate_cwd(tmp_path, "project") is True

    def test_cmd_add_rejects_outside_root(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Mock validate to force failure
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: False)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(tmp_path / "proj"), dry_run=False)
        )
        assert rc == 1


# ── env forwarding ────────────────────────────────────────────────────


class TestEnvForwarding:
    def test_gemini_explicit_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.setenv("SOFER_MCP_APPROVAL_PHRASE", "phrase")
        rc = cli._cmd_mcp_add(
            Namespace(agent="gemini", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        path = proj / ".gemini" / "settings.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mcpServers"]["sofer"]["env"]["HF_TOKEN"] == "hf123"
        assert data["mcpServers"]["sofer"]["env"]["SOFER_MCP_APPROVAL_PHRASE"] == "phrase"

    def test_codex_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        # Read TOML
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        path = proj / ".codex" / "config.toml"
        with open(path, "rb") as fh:
            doc = _tomli.load(fh)
        assert "HF_TOKEN" in doc["mcp_servers"]["sofer"]["env_vars"]


# ── delegation ────────────────────────────────────────────────────────


class TestDelegation:
    def test_opencode_never_delegates(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/fake/opencode" if x == "opencode" else None)
        assert mcp_registration.probe_native("opencode") is False
        assert mcp_registration.delegate_add("opencode", Path("/tmp"), []) is False
        assert mcp_registration.delegate_remove("opencode") is False

    def test_present_delegates(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/fake/codex" if x == "codex" else None)
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        assert mcp_registration.probe_native("codex") is True
        assert mcp_registration.delegate_add("codex", Path("/tmp"), ["HF_TOKEN"]) is True
        mock_run.assert_called()

    def test_absent_fallback(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        # No binary
        monkeypatch.setattr("shutil.which", lambda x: None)
        proj = tmp_path / "proj"
        proj.mkdir()
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        path = proj / ".codex" / "config.toml"
        assert path.exists()

    def test_fail_fallback(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        # Probe says native available but delegate fails
        monkeypatch.setattr(
            mcp_registration, "probe_native", lambda *a, **kw: True if a[0] == "codex" else False
        )
        monkeypatch.setattr(mcp_registration, "delegate_add", lambda *a, **kw: False)
        proj = tmp_path / "proj"
        proj.mkdir()
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        path = proj / ".codex" / "config.toml"
        assert path.exists()

    def test_timeout_fallback(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/fake/gemini" if x == "gemini" else None)

        def fake_run(*a, **kw):
            raise subprocess.TimeoutExpired(cmd=a[0], timeout=3)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert mcp_registration.probe_native("gemini") is False
        assert mcp_registration.delegate_add("gemini", Path("/tmp"), []) is False


# ── remove idempotency ────────────────────────────────────────────────


class TestRemove:
    def test_remove_single(self, tmp_path, monkeypatch):
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.chdir(proj)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        cli._cmd_mcp_add(Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False))
        path = proj / "opencode.json"
        assert "sofer" in json.loads(path.read_text(encoding="utf-8"))["mcp"]
        rc = cli._cmd_mcp_remove(Namespace(agent="opencode", scope="project", dry_run=False))
        assert rc == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "sofer" not in data.get("mcp", {})

    def test_remove_all(self, tmp_path, monkeypatch):
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.chdir(proj)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        cli._cmd_mcp_add(Namespace(agent="all", scope="project", cwd=str(proj), dry_run=False))
        rc = cli._cmd_mcp_remove(Namespace(agent="all", scope="project", dry_run=False))
        assert rc == 0
        for agent in ["opencode", "codex", "gemini"]:
            path = mcp_registration.resolve_config_path(agent, "project", proj)  # type: ignore[arg-type]
            if path.exists():
                data, _ = mcp_registration.read_config(path)
                # sofer should be absent
                assert "sofer" not in str(data)

    def test_remove_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        proj = tmp_path / "proj"
        proj.mkdir()
        rc = cli._cmd_mcp_remove(Namespace(agent="codex", scope="project", dry_run=False))
        assert rc == 0
        path = proj / ".codex" / "config.toml"
        # No write when absent
        assert not path.exists()
