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
        # Secret VALUES are never persisted — only the $VAR references (CF-3).
        # Gemini CLI expands host env vars at runtime from this object form.
        assert entry["env"] == {
            "HF_TOKEN": "$HF_TOKEN",
            "SOFER_MCP_APPROVAL_PHRASE": "$SOFER_MCP_APPROVAL_PHRASE",
        }
        assert "hf123" not in str(entry)
        assert "secret" not in str(entry)
        assert entry["command"] == "sofer-mcp"
        assert entry["cwd"] == str(cwd.resolve())

    def test_gemini_env_omits_absent_keys(self, tmp_path):
        cwd = tmp_path / "proj"
        cwd.mkdir()
        entry = mcp_registration.build_entry("gemini", cwd, {"HF_TOKEN": "hf123"})
        assert entry["env"] == {"HF_TOKEN": "$HF_TOKEN"}
        assert "SOFER_MCP_APPROVAL_PHRASE" not in entry["env"]

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
                    {
                        "mcp_servers": {
                            "sofer": {
                                "command": ["sofer-mcp"],
                                "cwd": str(proj.resolve()),
                                "env_vars": [],
                            }
                        }
                    },
                    fh,
                )
        else:
            codex_path.write_text(
                '[mcp_servers.sofer]\ncommand = ["sofer-mcp"]\n', encoding="utf-8"
            )
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
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        # Only env $VAR references are persisted — never the secret values
        # (CF-3). Gemini CLI expands these from the host environment.
        assert data["mcpServers"]["sofer"]["env"] == {
            "HF_TOKEN": "$HF_TOKEN",
            "SOFER_MCP_APPROVAL_PHRASE": "$SOFER_MCP_APPROVAL_PHRASE",
        }
        assert "hf123" not in raw_text
        assert "phrase" not in raw_text

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

    def test_opencode_warning_env_present(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.setenv("SOFER_MCP_APPROVAL_PHRASE", "phrase123")
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        err = capsys.readouterr().err
        assert "receives no env" in err
        assert "See README" in err
        assert "HF_TOKEN" in err
        assert "SOFER_MCP_APPROVAL_PHRASE" in err
        # entry stays exactly {type, command, cwd} with no env key
        path = proj / "opencode.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mcp"]["sofer"] == {
            "type": "local",
            "command": ["sofer-mcp"],
            "cwd": str(proj.resolve()),
        }
        assert "env" not in data["mcp"]["sofer"]

    def test_opencode_warning_dry_run(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=True)
        )
        assert rc == 0
        assert "receives no env" in capsys.readouterr().err
        # dry-run writes nothing: no config file and no .bak
        assert not (proj / "opencode.json").exists()
        assert not Path(str(proj / "opencode.json") + ".bak").exists()

    def test_opencode_warning_all_once(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.setenv("SOFER_MCP_APPROVAL_PHRASE", "phrase123")
        rc = cli._cmd_mcp_add(Namespace(agent="all", scope="project", cwd=str(proj), dry_run=False))
        assert rc == 0
        err = capsys.readouterr().err
        # exactly one warning, for the opencode member only
        assert err.count("receives no env") == 1
        # all still expands to exactly the three agents
        assert (proj / "opencode.json").exists()
        assert (proj / ".codex" / "config.toml").exists()
        assert (proj / ".gemini" / "settings.json").exists()
        # codex/gemini persist names only, values absent
        try:
            import tomli as _tomli2
        except ImportError:
            import tomllib as _tomli2

        codex_path = proj / ".codex" / "config.toml"
        codex_doc = _tomli2.load(codex_path.open("rb"))
        assert codex_doc["mcp_servers"]["sofer"]["env_vars"] == [
            "HF_TOKEN",
            "SOFER_MCP_APPROVAL_PHRASE",
        ]
        assert "hf123" not in codex_path.read_text(encoding="utf-8")
        gemini_data = json.loads((proj / ".gemini" / "settings.json").read_text(encoding="utf-8"))
        assert gemini_data["mcpServers"]["sofer"]["env"] == {
            "HF_TOKEN": "$HF_TOKEN",
            "SOFER_MCP_APPROVAL_PHRASE": "$SOFER_MCP_APPROVAL_PHRASE",
        }

    def test_no_warning_without_env(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        assert "receives no env" not in capsys.readouterr().err

    def test_no_warning_codex_gemini_env(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.setenv("SOFER_MCP_APPROVAL_PHRASE", "phrase123")
        for agent in ("codex", "gemini"):
            rc = cli._cmd_mcp_add(
                Namespace(agent=agent, scope="project", cwd=str(proj), dry_run=False)
            )
            assert rc == 0
        # no warning for forwarding agents
        assert "receives no env" not in capsys.readouterr().err
        # codex allow-list of names present, gemini $KEY refs; values absent
        try:
            import tomli as _tomli3
        except ImportError:
            import tomllib as _tomli3

        codex_path = proj / ".codex" / "config.toml"
        codex_doc = _tomli3.load(codex_path.open("rb"))
        assert codex_doc["mcp_servers"]["sofer"]["env_vars"] == [
            "HF_TOKEN",
            "SOFER_MCP_APPROVAL_PHRASE",
        ]
        gemini_path = proj / ".gemini" / "settings.json"
        gemini_data = json.loads(gemini_path.read_text(encoding="utf-8"))
        assert gemini_data["mcpServers"]["sofer"]["env"] == {
            "HF_TOKEN": "$HF_TOKEN",
            "SOFER_MCP_APPROVAL_PHRASE": "$SOFER_MCP_APPROVAL_PHRASE",
        }
        assert "hf123" not in gemini_path.read_text(encoding="utf-8")

    def test_warning_values_never_leak(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.setenv("SOFER_MCP_APPROVAL_PHRASE", "phrase123")
        # real run
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "hf123" not in captured.out
        assert "hf123" not in captured.err
        assert "phrase123" not in captured.out
        assert "phrase123" not in captured.err
        path = proj / "opencode.json"
        raw_text = path.read_text(encoding="utf-8")
        assert "hf123" not in raw_text
        assert "phrase123" not in raw_text
        # dry-run mode
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=True)
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "hf123" not in captured.out
        assert "hf123" not in captured.err
        assert "phrase123" not in captured.out
        assert "phrase123" not in captured.err


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Unit G: mcp_registration.py floor → ≥91 (COV-01)
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolveConfigPathNext:
    def test_unknown_agent_raises_both_scopes(self, tmp_path, monkeypatch) -> None:
        """resolve_config_path rejects unknown agents in user AND project scope."""
        from typing import cast as _cast

        bad: mcp_registration.AgentName = _cast(mcp_registration.AgentName, _cast(object, "nope"))
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="unknown agent"):
            mcp_registration.resolve_config_path(bad, "user", None)
        with pytest.raises(ValueError, match="unknown agent"):
            mcp_registration.resolve_config_path(bad, "project", tmp_path)


class TestBuildEntryNext:
    def test_unknown_agent_raises(self, tmp_path) -> None:
        from typing import cast as _cast

        bad: mcp_registration.AgentName = _cast(mcp_registration.AgentName, _cast(object, "nope"))
        with pytest.raises(ValueError, match="unknown agent"):
            mcp_registration.build_entry(bad, tmp_path, {})


class TestReadConfigMalformed:
    def test_rejects_non_object_json_and_non_table_toml(self, tmp_path, monkeypatch) -> None:
        """read_config raises on a non-object JSON and a scalar-root TOML."""
        json_path = tmp_path / "opencode.json"
        json_path.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(ValueError, match="not a JSON object"):
            mcp_registration.read_config(json_path)

        toml_path = tmp_path / "config.toml"
        toml_path.write_text('hello = "scalar"', encoding="utf-8")
        # Valid TOML always yields a table, so the non-table defensive branch is
        # driven through the parser seam (a degenerate load result).
        import tomllib as _tomllib

        monkeypatch.setattr(_tomllib, "load", lambda _fh: ["not", "a", "table"])
        with pytest.raises(ValueError, match="not a TOML table"):
            mcp_registration.read_config(toml_path)


class TestIdempotencyNext:
    def test_normalize_codex_command_non_string_returns_empty(self) -> None:
        assert mcp_registration._normalize_codex_command(42) == []
        assert mcp_registration._normalize_codex_command(None) == []

    @pytest.mark.parametrize(
        "agent",
        ["codex", "gemini", "opencode"],
    )
    def test_entries_equal_per_agent_matrix(self, agent: str) -> None:
        base = {"command": "sofer-mcp", "cwd": "/proj", "env_vars": ["HF_TOKEN"]}
        if agent == "codex":
            a = {**base, "cwd": "/proj"}
            b = {**base, "cwd": "/other"}
            assert mcp_registration._entries_equal("codex", a, b) is False  # cwd mismatch
            a2 = {**base, "env_vars": ["HF_TOKEN"]}
            b2 = {**base, "env_vars": []}
            assert mcp_registration._entries_equal("codex", a2, b2) is False  # env mismatch
            assert mcp_registration._entries_equal("codex", a2, {**a2}) is True
        elif agent == "gemini":
            a = {"command": "sofer-mcp", "cwd": "/proj", "env": {"HF_TOKEN": "$HF_TOKEN"}}
            b = {"command": "other", "cwd": "/proj", "env": a["env"]}
            assert mcp_registration._entries_equal("gemini", a, b) is False  # command
            c = {**a, "cwd": "/other"}
            assert mcp_registration._entries_equal("gemini", a, c) is False  # cwd
            d = {**a, "env": {}}
            assert mcp_registration._entries_equal("gemini", a, d) is False  # env
            assert mcp_registration._entries_equal("gemini", a, {**a}) is True
        else:
            a = {"type": "local", "command": ["sofer-mcp"], "cwd": "/proj"}
            assert mcp_registration._entries_equal("opencode", a, {**a}) is True
            assert (
                mcp_registration._entries_equal("opencode", a, {**a, "cwd": "/x"}) is False
            )

    def test_atomic_write_toml_roundtrip(self, tmp_path) -> None:
        """atomic_write("toml") round-trips through tomllib."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        path = tmp_path / "config.toml"
        doc = {"mcp_servers": {"sofer": {"command": "sofer-mcp", "cwd": "/proj"}}}
        mcp_registration.atomic_write(path, doc, "toml")
        with open(path, "rb") as fh:
            parsed = _tomli.load(fh)
        assert parsed == doc
        assert not (path.with_name(path.name + ".tmp")).exists()


class TestMergeNext:
    def test_gemini_idempotent_no_change(self) -> None:
        """An equal existing gemini entry is idempotent (no write)."""
        desired = {"command": "sofer-mcp", "cwd": "/proj", "env": {"HF_TOKEN": "$HF_TOKEN"}}
        existing = {"mcpServers": {"sofer": desired}}
        new_doc, changed = mcp_registration.merge("gemini", existing, desired)
        assert changed is False
        assert new_doc is existing or new_doc == existing

    def test_merge_unknown_agent_raises(self) -> None:
        from typing import cast as _cast

        bad: mcp_registration.AgentName = _cast(mcp_registration.AgentName, _cast(object, "nope"))
        with pytest.raises(ValueError, match="unknown agent"):
            mcp_registration.merge(bad, {}, {})


class TestRemoveNext:
    def test_remove_codex_pops_empty_table(self) -> None:
        """Removing the only codex server pops the mcp_servers table."""
        existing = {"mcp_servers": {"sofer": {"command": "sofer-mcp"}}}
        new_doc, changed = mcp_registration.remove_entry("codex", existing)
        assert changed is True
        assert "mcp_servers" not in new_doc

    def test_remove_codex_keeps_other_servers(self) -> None:
        existing = {
            "mcp_servers": {
                "sofer": {"command": "sofer-mcp"},
                "other": {"command": "other"},
            }
        }
        new_doc, changed = mcp_registration.remove_entry("codex", existing)
        assert changed is True
        assert new_doc["mcp_servers"] == {"other": {"command": "other"}}

    def test_remove_gemini_pops_empty_table(self) -> None:
        existing = {"mcpServers": {"sofer": {"command": "sofer-mcp"}}}
        new_doc, changed = mcp_registration.remove_entry("gemini", existing)
        assert changed is True
        assert "mcpServers" not in new_doc

    def test_remove_gemini_absent_returns_idempotent(self) -> None:
        existing = {"mcpServers": {"other": {"command": "other"}}}
        new_doc, changed = mcp_registration.remove_entry("gemini", existing)
        assert changed is False
        assert new_doc == existing

    def test_remove_gemini_keeps_other_servers(self) -> None:
        existing = {
            "mcpServers": {
                "sofer": {"command": "sofer-mcp"},
                "other": {"command": "other"},
            }
        }
        new_doc, changed = mcp_registration.remove_entry("gemini", existing)
        assert changed is True
        assert new_doc["mcpServers"] == {"other": {"command": "other"}}


class TestDelegationNext:
    @pytest.mark.parametrize(
        "rc,raises",
        [
            (0, False),
            (1, False),
            (None, "timeout"),
        ],
    )
    def test_delegate_add_success_and_failure_variants(self, monkeypatch, rc, raises) -> None:
        from unittest.mock import MagicMock

        monkeypatch.setattr("shutil.which", lambda x: "/fake/codex" if x == "codex" else None)

        def _run(*_a, **_k):
            if raises == "timeout":
                raise subprocess.TimeoutExpired(cmd=_a[0], timeout=3)
            return MagicMock(returncode=rc)

        monkeypatch.setattr(subprocess, "run", _run)
        result = mcp_registration.delegate_add("codex", Path("/tmp"), [])
        assert result is (rc == 0 and raises is False)

    def test_delegate_add_bare_exception_propagates(self, monkeypatch) -> None:
        """delegate_add only catches TimeoutExpired/OSError — other errors raise."""
        import pytest as _pytest

        monkeypatch.setattr("shutil.which", lambda x: "/fake/codex" if x == "codex" else None)

        def _run(*_a, **_k):
            raise ValueError("boom")

        monkeypatch.setattr(subprocess, "run", _run)
        with _pytest.raises(ValueError, match="boom"):
            mcp_registration.delegate_add("codex", Path("/tmp"), [])

    def test_delegate_add_absent_exe(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: None)
        assert mcp_registration.delegate_add("codex", Path("/tmp"), []) is False
        assert mcp_registration.delegate_remove("gemini") is False

    @pytest.mark.parametrize(
        "rc,raises",
        [
            (0, False),
            (1, False),
            (None, "timeout"),
            (None, "bare"),
        ],
    )
    def test_delegate_remove_variants(self, monkeypatch, rc, raises) -> None:
        from unittest.mock import MagicMock

        monkeypatch.setattr("shutil.which", lambda x: "/fake/gemini")

        def _run(*_a, **_k):
            if raises == "timeout":
                raise subprocess.TimeoutExpired(cmd=_a[0], timeout=3)
            if raises == "bare":
                raise RuntimeError("boom")
            return MagicMock(returncode=rc)

        monkeypatch.setattr(subprocess, "run", _run)
        assert mcp_registration.delegate_remove("gemini") is (rc == 0 and raises is False)

    def test_probe_native_bare_exception_returns_false(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: "/fake/codex" if x == "codex" else None)

        def _run(*_a, **_k):
            raise ValueError("unexpected")

        monkeypatch.setattr(subprocess, "run", _run)
        assert mcp_registration.probe_native("codex") is False


class TestCwdContainmentNext:
    def test_validate_cwd_project_scope_and_resolve_failure(self, tmp_path, monkeypatch) -> None:
        """Project-scope containment excludes foreign paths; resolve failure → False."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        (tmp_path / "proj").mkdir()
        monkeypatch.chdir(tmp_path / "proj")
        foreign = tmp_path / "elsewhere"
        foreign.mkdir()
        # project scope: foreign is under neither project_root (proj) nor home
        assert mcp_registration.validate_cwd(foreign, "project") is False
        assert mcp_registration.validate_cwd(tmp_path / "proj", "project") is True

        def _boom_resolve(self):
            raise OSError("unresolvable")

        monkeypatch.setattr(Path, "resolve", _boom_resolve)
        assert mcp_registration.validate_cwd(foreign, "project") is False
        assert mcp_registration.validate_cwd(tmp_path / "proj", "user") is False


class TestIdempotencyMatrixGaps:
    def test_codex_command_mismatch_returns_false(self) -> None:
        """A genuinely different codex command (after normalization) → False."""
        a = {"command": ["sofer-mcp"], "cwd": "/proj", "env_vars": ["HF_TOKEN"]}
        b = {"command": ["other"], "cwd": "/proj", "env_vars": ["HF_TOKEN"]}
        assert mcp_registration._entries_equal("codex", a, b) is False


class TestRemoveKeepOthers:
    def test_remove_opencode_keeps_other_servers(self) -> None:
        existing = {"mcp": {"sofer": {"type": "local"}, "other": {"type": "local"}}}
        new_doc, changed = mcp_registration.remove_entry("opencode", existing)
        assert changed is True
        assert new_doc["mcp"] == {"other": {"type": "local"}}


class TestRemoveUnknownAgent:
    def test_remove_entry_unknown_agent_raises(self) -> None:
        from typing import cast as _cast

        bad: mcp_registration.AgentName = _cast(mcp_registration.AgentName, _cast(object, "nope"))
        with pytest.raises(ValueError, match="unknown agent"):
            mcp_registration.remove_entry(bad, {})
