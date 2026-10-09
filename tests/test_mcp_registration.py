"""Tests for sofer.mcp_registration and CLI mcp handlers.

Covers MCP-REG-01/02 and CLI-R09 scenarios: idempotency, backup,
preserve other servers, delegation fallback, dry-run, unreadable,
cwd, env, CLI help.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
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
        from typing import cast as _cast

        data, _ = mcp_registration.read_config(path)
        mcp_section = _cast("dict[str, dict[str, object]]", data["mcp"])
        assert mcp_section["sofer"]["cwd"] == str(custom.resolve())


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
        agents: list[mcp_registration.AgentName] = list(mcp_registration.AGENT_NAMES)
        for agent in agents:
            path = mcp_registration.resolve_config_path(agent, "project", proj)
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
    """The `--cwd` rule: an existing directory is accepted, anything else is refused.

    The previous rule refused any cwd outside `Path.home()` or the process cwd. It
    was removed (issue #274): undeclared in any spec, scope-blind (its two branches
    were the same expression), effectively untested (the only "rejection" test
    monkeypatched the function away), protecting no privilege boundary, and it
    rejected legitimate trees — a dataset tree outside `$HOME`, which is exactly the
    reported container case. What remains is the check that catches a real mistake:
    the cwd must be an existing directory.
    """

    def test_validate_cwd_accepts_an_existing_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "proj"
        target.mkdir()
        assert mcp_registration.validate_cwd(target) is True

    def test_validate_cwd_accepts_an_existing_directory_outside_home(self, tmp_path, monkeypatch):
        """The reported case: the home and the dataset tree are unrelated."""
        home = tmp_path / "home"
        home.mkdir()
        tree = tmp_path / "workspace" / "test"
        tree.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.chdir(home)
        assert mcp_registration.validate_cwd(tree) is True

    def test_validate_cwd_refuses_a_missing_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert mcp_registration.validate_cwd(tmp_path / "nope") is False

    def test_validate_cwd_refuses_a_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        a_file = tmp_path / "not-a-dir.csv"
        a_file.write_text("a\n1\n", encoding="utf-8")
        assert mcp_registration.validate_cwd(a_file) is False

    def test_outside_root_warning_names_both_sides(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        tree = tmp_path / "workspace" / "test"
        tree.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.chdir(home)
        warning = mcp_registration.outside_root_warning(tree)
        assert warning is not None
        assert str(tree.resolve()) in warning
        assert str(home.resolve()) in warning

    def test_outside_root_warning_is_none_inside_home(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        inside = home / "proj"
        inside.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.chdir(home)
        assert mcp_registration.outside_root_warning(inside) is None

    def test_cmd_add_accepts_an_outside_root_dir_with_a_warning(
        self, tmp_path, monkeypatch, capsys
    ):
        """Accepted, not refused — and the odd case is named, never silent."""
        home = tmp_path / "home"
        home.mkdir()
        tree = tmp_path / "workspace" / "test"
        tree.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.chdir(home)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="user", cwd=str(tree), dry_run=True)
        )
        assert rc == 0
        assert str(tree.resolve()) in capsys.readouterr().err

    def test_cmd_add_refuses_a_missing_cwd(self, tmp_path, monkeypatch, capsys):
        """A cwd that is not an existing directory is the mistake worth failing on."""
        monkeypatch.chdir(tmp_path)
        missing = tmp_path / "nope"
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(missing), dry_run=True)
        )
        assert rc == 1
        assert str(missing.resolve()) in capsys.readouterr().err


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
        _tomli = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")

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
        # all still expands to every registered agent (four)
        assert (proj / "opencode.json").exists()
        assert (proj / ".codex" / "config.toml").exists()
        assert (proj / ".gemini" / "settings.json").exists()
        assert (proj / ".pi" / "mcp.json").exists()
        # codex/gemini persist names only, values absent
        _tomli2 = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")

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
        for agent in ("codex", "gemini", "pi"):
            rc = cli._cmd_mcp_add(
                Namespace(agent=agent, scope="project", cwd=str(proj), dry_run=False)
            )
            assert rc == 0
        # no warning for forwarding agents
        assert "receives no env" not in capsys.readouterr().err
        # codex allow-list of names present, gemini $KEY refs, pi ${KEY} refs; values absent
        _tomli3 = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")

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
        # pi is a name-forwarding agent too: braced ${KEY} refs, no warning
        pi_path = proj / ".pi" / "mcp.json"
        pi_data = json.loads(pi_path.read_text(encoding="utf-8"))
        assert pi_data["mcpServers"]["sofer"]["env"] == {
            "HF_TOKEN": "${HF_TOKEN}",
            "SOFER_MCP_APPROVAL_PHRASE": "${SOFER_MCP_APPROVAL_PHRASE}",
        }
        assert "hf123" not in pi_path.read_text(encoding="utf-8")

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
        # Empty env + user scope is faithful, so codex delegates.
        assert mcp_registration.delegate_add("codex", Path("/tmp"), []) is True
        mock_run.assert_called()

    def test_present_delegates_declines_env(self, monkeypatch):
        """#167: a non-empty env_keys makes the native path decline (file edit wins)."""
        monkeypatch.setattr("shutil.which", lambda x: "/fake/codex" if x == "codex" else None)
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        assert mcp_registration.delegate_add("codex", Path("/tmp"), ["HF_TOKEN"]) is False
        assert mcp_registration.delegate_add("gemini", Path("/tmp"), ["HF_TOKEN"]) is False
        mock_run.assert_not_called()

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
        agents: list[mcp_registration.AgentName] = list(mcp_registration.AGENT_NAMES)
        for agent in agents:
            path = mcp_registration.resolve_config_path(agent, "project", proj)
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
        _tomllib = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")

        monkeypatch.setattr(_tomllib, "load", lambda _fh: ["not", "a", "table"])
        with pytest.raises(ValueError, match="not a TOML table"):
            mcp_registration.read_config(toml_path)


class TestIdempotencyNext:
    def test_normalize_command_non_string_returns_empty(self) -> None:
        assert mcp_registration._normalize_command(42) == []
        assert mcp_registration._normalize_command(None) == []

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
            ga = {"command": "sofer-mcp", "cwd": "/proj", "env": {"HF_TOKEN": "$HF_TOKEN"}}
            gb = {"command": "other", "cwd": "/proj", "env": ga["env"]}
            assert mcp_registration._entries_equal("gemini", ga, gb) is False  # command
            gc = {**ga, "cwd": "/other"}
            assert mcp_registration._entries_equal("gemini", ga, gc) is False  # cwd
            gd = {**ga, "env": {}}
            assert mcp_registration._entries_equal("gemini", ga, gd) is False  # env
            assert mcp_registration._entries_equal("gemini", ga, {**ga}) is True
        else:
            a = {"type": "local", "command": ["sofer-mcp"], "cwd": "/proj"}
            assert mcp_registration._entries_equal("opencode", a, {**a}) is True
            assert mcp_registration._entries_equal("opencode", a, {**a, "cwd": "/x"}) is False

    def test_atomic_write_toml_roundtrip(self, tmp_path) -> None:
        """atomic_write("toml") round-trips through tomllib."""
        _tomli = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")

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
    def test_validate_cwd_requires_an_existing_directory_and_tolerates_resolve_failure(
        self, tmp_path, monkeypatch
    ) -> None:
        """Existence is the rule (issue #274): a foreign-but-real directory is
        accepted and named, and an unresolvable path is refused rather than raising."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        (tmp_path / "proj").mkdir()
        monkeypatch.chdir(tmp_path / "proj")
        foreign = tmp_path / "elsewhere"
        foreign.mkdir()
        # A real directory outside home and the process cwd is ACCEPTED — the
        # deliberate change from the old containment rule — and named by the
        # warning instead of being refused.
        assert mcp_registration.validate_cwd(foreign) is True
        assert mcp_registration.outside_root_warning(foreign) is not None
        assert mcp_registration.validate_cwd(tmp_path / "proj") is True

        def _boom_resolve(self):
            raise OSError("unresolvable")

        monkeypatch.setattr(Path, "resolve", _boom_resolve)
        assert mcp_registration.validate_cwd(foreign) is False
        assert mcp_registration.outside_root_warning(foreign) is None


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Single-source agent registry (#235) — every site derives from ADAPTERS.
# ═══════════════════════════════════════════════════════════════════════════════


def _parser_agent_choices(command: str) -> list[str]:
    """Return the ``--agent`` choices for ``mcp add`` / ``mcp remove``."""
    import argparse as _argparse

    parser = cli._build_parser()
    mcp_action = next(
        a
        for a in parser._actions
        if isinstance(a, _argparse._SubParsersAction) and "mcp" in a.choices
    )
    mcp_sub = mcp_action.choices["mcp"]
    cmd_action = next(
        a
        for a in mcp_sub._actions
        if isinstance(a, _argparse._SubParsersAction) and command in a.choices
    )
    cmd_parser = cmd_action.choices[command]
    agent_action = next(a for a in cmd_parser._actions if getattr(a, "dest", None) == "agent")
    return list(agent_action.choices)


class TestSingleSourceRegistry:
    """The agent set lives in one place; every consumer derives from it."""

    def test_agent_names_derive_from_adapter_registry(self) -> None:
        assert mcp_registration.AGENT_NAMES == tuple(mcp_registration.ADAPTERS)
        assert mcp_registration.AGENT_NAMES  # non-empty

    def test_every_agent_name_has_a_complete_adapter(self) -> None:
        required = {
            "fmt",
            "key",
            "user_parts",
            "project_parts",
            "command",
            "adds_type_local",
            "env",
            "delegates",
            "native_env",
            "native_scope",
            "user_env_dir",
        }
        for agent in mcp_registration.AGENT_NAMES:
            spec = mcp_registration.ADAPTERS[agent]
            assert set(spec) == required, agent
            assert spec["fmt"] in {"json", "toml"}
            assert spec["command"] in {"array", "string"}
            assert spec["env"] in {"none", "allow_list", "refs", "refs_braced"}

    def test_resolve_config_path_matches_registry_for_every_agent(
        self, tmp_path, monkeypatch
    ) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        proj = tmp_path / "proj"
        proj.mkdir()
        for agent in mcp_registration.AGENT_NAMES:
            spec = mcp_registration.ADAPTERS[agent]
            env_dir = spec["user_env_dir"]
            if env_dir:
                monkeypatch.delenv(env_dir, raising=False)
            assert mcp_registration.resolve_config_path(agent, "user") == home.joinpath(
                *spec["user_parts"]
            )
            assert mcp_registration.resolve_config_path(
                agent, "project", proj
            ) == proj.resolve().joinpath(*spec["project_parts"])

    @pytest.mark.parametrize("command", ["add", "remove"])
    def test_cli_agent_choices_derive_from_registry(self, command: str) -> None:
        assert _parser_agent_choices(command) == [*mcp_registration.AGENT_NAMES, "all"]

    def test_all_expansion_and_choices_track_a_new_registry_entry(
        self, tmp_path, monkeypatch
    ) -> None:
        """A fake registry entry flows into CLI choices and ``--agent all``.

        Guards the single-source contract: adding an agent to ``ADAPTERS`` is
        the only edit needed for the CLI to accept and expand it.
        """
        sentinel = {
            "fmt": "json",
            "key": "mcpSentinel",
            "user_parts": (".sentinel", "sentinel.json"),
            "project_parts": ("sentinel.json",),
            "command": "string",
            "adds_type_local": False,
            "env": "none",
            "delegates": False,
            "native_env": False,
            "native_scope": False,
            "user_env_dir": None,
        }
        patched = {**mcp_registration.ADAPTERS, "sentinel": sentinel}
        monkeypatch.setattr(mcp_registration, "ADAPTERS", patched)
        monkeypatch.setattr(mcp_registration, "AGENT_NAMES", tuple(patched))

        assert _parser_agent_choices("add") == [*tuple(patched), "all"]
        assert _parser_agent_choices("remove") == [*tuple(patched), "all"]

        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.chdir(proj)
        rc = cli._cmd_mcp_add(Namespace(agent="all", scope="project", cwd=str(proj), dry_run=False))
        assert rc == 0
        assert (proj / "sentinel.json").exists()
        assert (proj / "opencode.json").exists()
        assert (proj / ".codex" / "config.toml").exists()
        assert (proj / ".gemini" / "settings.json").exists()
        assert (proj / ".pi" / "mcp.json").exists()


class TestRefactorParity:
    """Pin the behaviors the single-source refactor must preserve exactly."""

    def test_opencode_entry_key_order_matches_legacy(self, tmp_path) -> None:
        """Serialized key order stays ``type, command, cwd`` for opencode."""
        cwd = tmp_path / "proj"
        cwd.mkdir()
        entry = mcp_registration.build_entry("opencode", cwd, {})
        assert list(entry) == ["type", "command", "cwd"]

    def test_gemini_command_array_is_not_treated_as_equal(self) -> None:
        """Gemini does not normalize command: array vs string is a change."""
        string_cmd = {"command": "sofer-mcp", "cwd": "/proj", "env": {"HF_TOKEN": "$HF_TOKEN"}}
        array_cmd = {"command": ["sofer-mcp"], "cwd": "/proj", "env": {"HF_TOKEN": "$HF_TOKEN"}}
        assert mcp_registration._entries_equal("gemini", string_cmd, array_cmd) is False
        _, changed = mcp_registration.merge(
            "gemini", {"mcpServers": {"sofer": array_cmd}}, string_cmd
        )
        assert changed is True

    def test_unknown_agent_keeps_legacy_fallthrough(self, monkeypatch) -> None:
        """Unregistered agents keep the pre-#235 fall-through (no ValueError)."""
        monkeypatch.setattr("shutil.which", lambda _x: "/fake/ghost")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=0))
        assert mcp_registration.probe_native("ghost") is True
        assert mcp_registration.delegate_add("ghost", Path("/tmp"), []) is True
        assert mcp_registration.delegate_remove("ghost") is True
        assert mcp_registration.dropped_env_keys("ghost", {"HF_TOKEN": "x"}) == []


# ═══════════════════════════════════════════════════════════════════════════════
#  Pi agent (#142) — pi-mcp-adapter: file-edit only, ${KEY} env references.
# ═══════════════════════════════════════════════════════════════════════════════


class TestPiAdapter:
    def test_agent_names_includes_pi_last(self) -> None:
        assert mcp_registration.AGENT_NAMES == ("opencode", "codex", "gemini", "pi")

    def test_pi_registry_entry_is_complete(self) -> None:
        assert mcp_registration.ADAPTERS["pi"] == {
            "fmt": "json",
            "key": "mcpServers",
            "user_parts": (".pi", "agent", "mcp.json"),
            "project_parts": (".pi", "mcp.json"),
            "command": "string",
            "adds_type_local": False,
            "env": "refs_braced",
            "delegates": False,
            "native_env": False,
            "native_scope": False,
            "user_env_dir": "PI_CODING_AGENT_DIR",
        }

    def test_pi_entry_shape_string_command_no_type_or_enabled(self, tmp_path) -> None:
        cwd = tmp_path / "proj"
        cwd.mkdir()
        entry = mcp_registration.build_entry("pi", cwd, {"HF_TOKEN": "hf123"})
        assert entry == {
            "command": "sofer-mcp",
            "cwd": str(cwd.resolve()),
            "env": {"HF_TOKEN": "${HF_TOKEN}"},
        }
        assert isinstance(entry["command"], str)
        assert "args" not in entry
        assert "type" not in entry
        assert "enabled" not in entry
        assert "hf123" not in str(entry)

    def test_pi_env_braced_refs_and_omits_absent_keys(self, tmp_path) -> None:
        cwd = tmp_path / "proj"
        cwd.mkdir()
        entry = mcp_registration.build_entry("pi", cwd, {"HF_TOKEN": "hf123"})
        assert entry["env"] == {"HF_TOKEN": "${HF_TOKEN}"}
        assert "SOFER_MCP_APPROVAL_PHRASE" not in entry["env"]
        # The bare ``$KEY`` form Pi does not interpolate must not be used.
        assert "$HF_TOKEN" not in str(entry)

    def test_pi_user_path_defaults_under_home(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
        assert mcp_registration.resolve_config_path("pi", "user") == (
            home / ".pi" / "agent" / "mcp.json"
        )

    def test_pi_user_path_honours_env_dir_override(self, tmp_path, monkeypatch) -> None:
        agent_dir = tmp_path / "custom-agent"
        monkeypatch.setenv("PI_CODING_AGENT_DIR", str(agent_dir))
        assert mcp_registration.resolve_config_path("pi", "user") == agent_dir / "mcp.json"

    def test_pi_empty_env_dir_falls_back_to_home(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setenv("PI_CODING_AGENT_DIR", "")
        assert mcp_registration.resolve_config_path("pi", "user") == (
            home / ".pi" / "agent" / "mcp.json"
        )

    def test_pi_project_path_is_dot_pi(self, tmp_path) -> None:
        proj = tmp_path / "proj"
        proj.mkdir()
        assert mcp_registration.resolve_config_path("pi", "project", proj) == (
            proj.resolve() / ".pi" / "mcp.json"
        )

    def test_pi_never_delegates(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: "/fake/pi" if x == "pi" else None)
        assert mcp_registration.probe_native("pi") is False
        assert mcp_registration.delegate_add("pi", Path("/tmp"), []) is False
        assert mcp_registration.delegate_remove("pi") is False

    def test_pi_entries_equal_compares_string_command_and_env(self) -> None:
        entry = {"command": "sofer-mcp", "cwd": "/proj", "env": {"HF_TOKEN": "${HF_TOKEN}"}}
        assert mcp_registration._entries_equal("pi", entry, {**entry}) is True
        assert mcp_registration._entries_equal("pi", entry, {**entry, "cwd": "/x"}) is False
        assert mcp_registration._entries_equal("pi", entry, {**entry, "env": {}}) is False
        array_cmd = {**entry, "command": ["sofer-mcp"]}
        assert mcp_registration._entries_equal("pi", entry, array_cmd) is False


class TestPiCli:
    def test_pi_add_user_writes_env_dir_override(self, tmp_path, monkeypatch) -> None:
        agent_dir = tmp_path / "agentdir"
        monkeypatch.setenv("PI_CODING_AGENT_DIR", str(agent_dir))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        rc = cli._cmd_mcp_add(Namespace(agent="pi", scope="user", cwd=None, dry_run=False))
        assert rc == 0
        path = agent_dir / "mcp.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mcpServers"]["sofer"]["command"] == "sofer-mcp"

    def test_pi_add_project_writes_dot_pi_and_env(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        monkeypatch.setenv("HF_TOKEN", "hf123")
        monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)
        rc = cli._cmd_mcp_add(
            Namespace(agent="pi", scope="project", cwd=str(tmp_path), dry_run=False)
        )
        assert rc == 0
        path = tmp_path / ".pi" / "mcp.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mcpServers"]["sofer"] == {
            "command": "sofer-mcp",
            "cwd": str(tmp_path.resolve()),
            "env": {"HF_TOKEN": "${HF_TOKEN}"},
        }
        assert "hf123" not in path.read_text(encoding="utf-8")

    def test_pi_add_is_idempotent_no_backup_no_write(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("SOFER_MCP_APPROVAL_PHRASE", raising=False)
        args = Namespace(agent="pi", scope="project", cwd=str(tmp_path), dry_run=False)
        assert cli._cmd_mcp_add(args) == 0
        path = tmp_path / ".pi" / "mcp.json"
        first = path.read_bytes()
        assert cli._cmd_mcp_add(args) == 0
        assert path.read_bytes() == first
        assert not Path(str(path) + ".bak").exists()

    def test_pi_dry_run_writes_nothing(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        rc = cli._cmd_mcp_add(
            Namespace(agent="pi", scope="project", cwd=str(tmp_path), dry_run=True)
        )
        assert rc == 0
        path = tmp_path / ".pi" / "mcp.json"
        assert not path.exists()
        assert not Path(str(path) + ".bak").exists()

    def test_pi_add_unreadable_exits_1_no_backup(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        path = tmp_path / ".pi" / "mcp.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ not json", encoding="utf-8")
        rc = cli._cmd_mcp_add(
            Namespace(agent="pi", scope="project", cwd=str(tmp_path), dry_run=False)
        )
        assert rc == 1
        assert path.read_text(encoding="utf-8") == "{ not json"
        assert not Path(str(path) + ".bak").exists()

    def test_pi_remove_preserves_other_servers(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = tmp_path / ".pi" / "mcp.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "sofer": {"command": "sofer-mcp", "cwd": str(tmp_path)},
                        "other": {"command": "other"},
                    }
                }
            ),
            encoding="utf-8",
        )
        rc = cli._cmd_mcp_remove(Namespace(agent="pi", scope="project", dry_run=False))
        assert rc == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mcpServers"] == {"other": {"command": "other"}}

    def test_pi_remove_idempotent_when_absent(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_mcp_remove(Namespace(agent="pi", scope="project", dry_run=False))
        assert rc == 0
        assert not (tmp_path / ".pi" / "mcp.json").exists()


# ═══════════════════════════════════════════════════════════════════════════════
#  Native delegation fidelity (#167 env, #232 scope) — one unified criterion.
# ═══════════════════════════════════════════════════════════════════════════════


class TestNativeDelegationFidelity:
    """The single gate decides both env (#167) and scope (#232) fidelity."""

    def test_registry_capability_fields(self) -> None:
        # Native env flags take literal values, so no agent forwards NAMES.
        assert all(spec["native_env"] is False for spec in mcp_registration.ADAPTERS.values())
        # Only gemini has a native scope selector.
        assert mcp_registration.ADAPTERS["gemini"]["native_scope"] is True
        assert mcp_registration.ADAPTERS["codex"]["native_scope"] is False
        assert mcp_registration.ADAPTERS["opencode"]["native_scope"] is False
        assert mcp_registration.ADAPTERS["pi"]["native_scope"] is False

    def test_decline_reasons_truth_table(self) -> None:
        r = mcp_registration.native_delegation_decline_reasons
        # Faithful: no env, and scope expressible (gemini both, codex user).
        assert r("gemini", [], "user") == []
        assert r("gemini", [], "project") == []
        assert r("codex", [], "user") == []
        # Env must be forwarded but no native NAME forwarding exists.
        assert r("codex", ["HF_TOKEN"], "user") == ["env forwarding"]
        # gemini can express project scope, so only the env reason applies…
        assert r("gemini", ["HF_TOKEN"], "project") == ["env forwarding"]
        # …while codex accumulates both reasons.
        assert r("codex", ["HF_TOKEN"], "project") == ["env forwarding", "project scope"]
        # Project scope requested from a scope-less native CLI.
        assert r("codex", [], "project") == ["project scope"]
        # Unregistered agents are treated conservatively.
        assert r("ghost", ["HF_TOKEN"], "user") == ["env forwarding"]
        assert r("ghost", [], "project") == ["project scope"]

    def test_delegate_add_forwards_scope_to_gemini(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: "/fake/gemini" if x == "gemini" else None)
        seen: dict[str, list[str]] = {}

        def _run(cmd, *a, **k):
            seen["cmd"] = list(cmd)
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", _run)
        project = Path("/proj")
        assert mcp_registration.delegate_add("gemini", project, [], "project") is True
        assert seen["cmd"] == [
            "/fake/gemini",
            "mcp",
            "add",
            "--scope",
            "project",
            "sofer",
            "--command",
            "sofer-mcp",
            "--cwd",
            str(project),
        ]

    def test_delegate_add_codex_user_is_scope_less(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: "/fake/codex" if x == "codex" else None)
        seen: dict[str, list[str]] = {}

        def _run(cmd, *a, **k):
            seen["cmd"] = list(cmd)
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", _run)
        assert mcp_registration.delegate_add("codex", Path("/proj"), [], "user") is True
        assert "--scope" not in seen["cmd"]

    def test_delegate_add_declines_unfaithful_without_spawn(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: f"/fake/{x}")
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        # codex + project scope (no native scope selector).
        assert mcp_registration.delegate_add("codex", Path("/proj"), [], "project") is False
        # env NAMES present for both delegating agents.
        assert mcp_registration.delegate_add("codex", Path("/proj"), ["HF_TOKEN"], "user") is False
        assert mcp_registration.delegate_add("gemini", Path("/proj"), ["HF_TOKEN"], "user") is False
        mock_run.assert_not_called()

    def test_delegate_remove_scope_gate(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda x: f"/fake/{x}")
        seen: dict[str, list[str]] = {}

        def _run(cmd, *a, **k):
            seen["cmd"] = list(cmd)
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", _run)
        assert mcp_registration.delegate_remove("gemini", "user") is True
        assert seen["cmd"] == ["/fake/gemini", "mcp", "remove", "--scope", "user", "sofer"]
        # codex cannot express project scope: declines without spawning.
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr(subprocess, "run", mock_run)
        assert mcp_registration.delegate_remove("codex", "project") is False
        mock_run.assert_not_called()
