"""
Tests for :mod:`sofer.failure_report` — the assisted failure reporter (#244).

Covers the confidentiality contract (allowlist, path anonymization, no secret
or dataset leak), the issue body/title builder, on-disk persistence (one file
per failure, timestamped, never overwritten), the ``gh`` delivery paths
(success, missing binary, unauthenticated, offline), the retry command, and
the interactive CLI orchestration.
"""

from __future__ import annotations

import builtins
import json
import os
import subprocess
import types
from argparse import Namespace
from pathlib import Path

import pytest

from sofer import cli, config, failure_report


def _raise_value_error(message: str = "boom") -> BaseException:
    """Return a ValueError carrying a real traceback (caught inside a try)."""
    try:
        raise ValueError(message)
    except ValueError as exc:  # pragma: no cover - trivial capture
        return exc


class TestAnonymize:
    def test_home_replaced_posix(self) -> None:
        home = Path("/home/alice")
        assert (
            failure_report.anonymize_paths("/home/alice/datasets/x.csv", home=home)
            == "~/datasets/x.csv"
        )

    def test_home_replaced_windows_backslash_form(self) -> None:
        home = Path(r"C:\Users\alice")
        out = failure_report.anonymize_paths(r"at C:\Users\alice\data\x.csv", home=home)
        assert "alice" not in out
        assert "~" in out

    def test_empty_and_no_match_are_unchanged(self) -> None:
        assert failure_report.anonymize_paths("", home=Path("/h")) == ""
        assert failure_report.anonymize_paths("plain text", home=Path("/nope")) == "plain text"

    def test_root_home_separator_is_not_replaced(self) -> None:
        assert failure_report.anonymize_paths("/etc/hosts", home=Path("/")) == "/etc/hosts"

    def test_home_replaced_doubled_backslash_form(self) -> None:
        home = Path(r"C:\Users\alice")
        out = failure_report.anonymize_paths(r"C:\\Users\\alice\\x.csv", home=home)
        assert "alice" not in out
        assert "~" in out


class TestStateHome:
    def test_override_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "s"))
        assert failure_report.state_home() == tmp_path / "s"

    def test_posix_xdg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOFER_STATE_HOME", raising=False)
        monkeypatch.setenv("XDG_STATE_HOME", "/xdg")
        assert failure_report.state_home() == Path("/xdg") / "sofer"

    def test_posix_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOFER_STATE_HOME", raising=False)
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
        assert failure_report.state_home() == tmp_path / ".local" / "state" / "sofer"

    def test_windows_with_localappdata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOFER_STATE_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", "/local")
        monkeypatch.setattr(
            failure_report, "os", types.SimpleNamespace(name="nt", environ=os.environ)
        )
        assert failure_report.state_home() == Path("/local") / "sofer"

    def test_windows_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOFER_STATE_HOME", raising=False)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
        monkeypatch.setattr(
            failure_report, "os", types.SimpleNamespace(name="nt", environ=os.environ)
        )
        assert failure_report.state_home() == tmp_path / "AppData" / "Local" / "sofer"


class TestContext:
    def test_context_is_allowlisted_and_env_free(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOFER_TEST_SECRET", "hunter2-secret")
        home = Path("/home/alice")
        exc = _raise_value_error("/home/alice/private/x.csv")
        ctx = failure_report.collect_failure_context(
            ["validate", "/home/alice/private/dataset.toml"], exc, home=home
        )
        assert ctx.command == "validate"
        assert ctx.error_type == "ValueError"
        assert ctx.argv == ("validate", "~/private/dataset.toml")
        assert ctx.error_message == "~/private/x.csv"
        assert "/home/alice" not in ctx.traceback_text
        assert "hunter2-secret" not in ctx.traceback_text
        assert ctx.sofer_version
        assert ctx.python_version
        assert ctx.timestamp

    def test_command_falls_back_to_sofer_when_argv_empty(self) -> None:
        ctx = failure_report.collect_failure_context([], _raise_value_error())
        assert ctx.command == "sofer"
        assert ctx.argv == ()

    def test_traceback_is_truncated_at_config_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(config, "FAILURE_REPORT_TRACEBACK_MAX_CHARS", 120)
        exc = _raise_value_error("y" * 500)
        ctx = failure_report.collect_failure_context(["validate"], exc)
        assert len(ctx.traceback_text) <= 120
        assert "truncated" in ctx.traceback_text

    def test_tiny_cap_never_returns_the_full_traceback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A cap smaller than the marker must not invert ``text[-0:]`` into the
        whole traceback (the tail slice is guarded)."""
        monkeypatch.setattr(config, "FAILURE_REPORT_TRACEBACK_MAX_CHARS", 10)
        exc = _raise_value_error("z" * 500)
        ctx = failure_report.collect_failure_context(["validate"], exc)
        assert "z" * 100 not in ctx.traceback_text
        assert "truncated" in ctx.traceback_text


class TestBody:
    def test_title_and_body_carry_allowlisted_facts(self) -> None:
        ctx = failure_report.collect_failure_context(
            ["prepare", "dataset.toml"], _raise_value_error()
        )
        title = failure_report.build_issue_title(ctx)
        body = failure_report.build_issue_body(ctx, repo="owner/repo")
        assert title == "[crash] sofer prepare: ValueError"
        for token in (
            "## Summary",
            "## Command",
            "## Traceback",
            "## Environment",
            "## Confidentiality",
        ):
            assert token in body
        assert ctx.sofer_version in body
        assert ctx.python_version in body
        assert "owner/repo" in body
        assert "sofer prepare dataset.toml" in body

    def test_body_carries_no_dataset_data(self) -> None:
        exc = _raise_value_error("row cell value 42")
        ctx = failure_report.collect_failure_context(["validate"], exc, home=Path("/home/alice"))
        body = failure_report.build_issue_body(ctx, repo="owner/repo")
        assert "row cell value 42" not in body.replace(ctx.error_message, "")
        assert "no dataset contents" in body


class TestPersistence:
    def test_one_file_per_failure_never_overwrites(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        first = failure_report.persist_report("owner/repo", "t1", "b1", stamp="20260925T000000")
        second = failure_report.persist_report("owner/repo", "t2", "b2", stamp="20260925T000000")
        assert first != second
        assert first.exists() and second.exists()
        assert failure_report.load_report(first)["title"] == "t1"
        assert failure_report.load_report(second)["title"] == "t2"
        assert failure_report.load_report(first)["repo"] == "owner/repo"

    def test_reports_dir_uses_config_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(config, "FAILURE_REPORT_DIR", "custom-reports")
        assert failure_report.reports_dir() == tmp_path / "state" / "custom-reports"

    def test_load_report_rejects_non_object(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError):
            failure_report.load_report(path)

    def test_retry_command_shape(self) -> None:
        assert failure_report.retry_command("/tmp/x.json") == 'sofer report-failure "/tmp/x.json"'

    def test_manual_issue_url_prefills_title_and_body(self) -> None:
        url = failure_report.manual_issue_url("owner/repo", "a title", "a body")
        assert url.startswith("https://github.com/owner/repo/issues/new?")
        assert "title=a+title" in url
        assert "body=a+body" in url

    def test_manual_issue_url_omits_oversized_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(config, "FAILURE_REPORT_MANUAL_URL_MAX_CHARS", 10)
        url = failure_report.manual_issue_url("owner/repo", "a title", "x" * 100)
        assert "body=" not in url
        assert "title=a+title" in url


def _fake_run(returncodes: dict[str, tuple[int, str, str]]):
    """Return a fake ``subprocess.run`` keyed by the gh subcommand token."""

    def _run(args, **_kwargs):  # type: ignore[no-untyped-def]
        key = " ".join(args[1:3])
        rc, out, err = returncodes.get(key, (1, "", "unknown gh command"))
        return subprocess.CompletedProcess(args=args, returncode=rc, stdout=out, stderr=err)

    return _run


class TestSend:
    def test_missing_gh_never_calls_create(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: None)
        called = {"create": False}
        monkeypatch.setattr(
            failure_report,
            "create_issue",
            lambda *a: called.__setitem__("create", True) or (True, "x"),
        )
        url, reason = failure_report.attempt_send("o/r", "t", "b")
        assert url is None
        assert reason == "gh CLI not found"
        assert called["create"] is False

    def test_unauthenticated_skips_create(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: "/usr/bin/gh")
        monkeypatch.setattr(
            failure_report.subprocess, "run", _fake_run({"auth status": (1, "", "not logged in")})
        )
        url, reason = failure_report.attempt_send("o/r", "t", "b")
        assert url is None
        assert reason == "gh is not authenticated"

    def test_authenticated_creates_issue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: "/usr/bin/gh")
        monkeypatch.setattr(
            failure_report.subprocess,
            "run",
            _fake_run(
                {
                    "auth status": (0, "", ""),
                    "issue create": (0, "https://github.com/o/r/issues/7\n", ""),
                }
            ),
        )
        url, reason = failure_report.attempt_send("o/r", "t", "b")
        assert url == "https://github.com/o/r/issues/7"
        assert reason is None

    def test_create_issue_propagates_gh_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: "/usr/bin/gh")
        monkeypatch.setattr(
            failure_report.subprocess, "run", _fake_run({"issue create": (1, "", "boom")})
        )
        ok, detail = failure_report.create_issue("o/r", "t", "b")
        assert ok is False
        assert detail == "boom"

    def test_run_gh_returns_none_on_oserror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*_a, **_k):  # type: ignore[no-untyped-def]
            raise FileNotFoundError("gh")

        monkeypatch.setattr(failure_report.subprocess, "run", _raise)
        assert failure_report._run_gh(["auth", "status"]) is None

    def test_gh_authenticated_false_without_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: None)
        assert failure_report.gh_authenticated() is False

    def test_create_issue_false_when_run_gh_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(failure_report, "_run_gh", lambda _args: None)
        ok, detail = failure_report.create_issue("o/r", "t", "b")
        assert ok is False
        assert detail == "gh CLI is not available"

    def test_offline_persists_and_prints_safety_net(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: None)
        ctx = failure_report.collect_failure_context(["validate"], _raise_value_error())
        title = failure_report.build_issue_title(ctx)
        body = failure_report.build_issue_body(ctx, repo="owner/repo")
        path = failure_report.persist_report("owner/repo", title, body)
        rc = failure_report.send_persisted_report(path)
        out = capsys.readouterr().out
        assert rc == 1
        assert str(path) in out
        assert 'sofer report-failure "' in out
        assert "github.com/owner/repo/issues/new" in out
        assert "gh auth login" in out

    def test_offline_long_body_prints_paste_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: None)
        monkeypatch.setattr(config, "FAILURE_REPORT_MANUAL_URL_MAX_CHARS", 10)
        ctx = failure_report.collect_failure_context(["validate"], _raise_value_error())
        title = failure_report.build_issue_title(ctx)
        body = failure_report.build_issue_body(ctx, repo="owner/repo")
        path = failure_report.persist_report("owner/repo", title, body)
        assert failure_report.send_persisted_report(path) == 1
        out = capsys.readouterr().out
        assert "too long to prefill" in out
        assert str(path) in out

    def test_retry_success_prints_url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "report.json"
        path.write_text(json.dumps({"repo": "o/r", "title": "t", "body": "b"}), encoding="utf-8")
        monkeypatch.setattr(
            failure_report, "attempt_send", lambda *a: ("https://github.com/o/r/issues/9", None)
        )
        assert failure_report.send_persisted_report(path) == 0
        assert "https://github.com/o/r/issues/9" in capsys.readouterr().out


class TestCliIntegration:
    def test_non_tty_creates_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "_stdin_is_interactive", lambda: False)
        rc = failure_report.report_cli_failure(["validate"], _raise_value_error())
        assert rc == 1
        assert not (tmp_path / "state").exists()
        assert "ValueError" in capsys.readouterr().err

    def test_decline_creates_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "_stdin_is_interactive", lambda: True)
        monkeypatch.setattr(builtins, "input", lambda _prompt: "n")
        assert failure_report.report_cli_failure(["validate"], _raise_value_error()) == 1
        assert not (tmp_path / "state").exists()

    def test_accept_then_review_decline_persists_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "_stdin_is_interactive", lambda: True)
        answers = iter(["y", "n"])
        monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))
        assert failure_report.report_cli_failure(["validate"], _raise_value_error()) == 1
        assert not (tmp_path / "state").exists()

    def test_accept_reviews_body_then_sends(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "_stdin_is_interactive", lambda: True)
        answers = iter(["y", "y"])
        monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))
        sent: dict[str, str] = {}

        def _attempt(repo: str, title: str, body: str) -> tuple[str | None, str | None]:
            sent.update(repo=repo, title=title, body=body)
            return "https://github.com/o/r/issues/1", None

        monkeypatch.setattr(failure_report, "attempt_send", _attempt)
        assert failure_report.report_cli_failure(["validate"], _raise_value_error()) == 1
        out = capsys.readouterr().out
        assert "BEGIN REPORT" in out and "END REPORT" in out
        assert "## Traceback" in sent["body"]
        assert "https://github.com/o/r/issues/1" in out

    def test_accept_then_offline_persists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "_stdin_is_interactive", lambda: True)
        answers = iter(["y", "y"])
        monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))
        monkeypatch.setattr(failure_report.shutil, "which", lambda _name: None)
        assert failure_report.report_cli_failure(["validate"], _raise_value_error()) == 1
        files = list((tmp_path / "state" / config.FAILURE_REPORT_DIR).glob("*.json"))
        assert len(files) == 1

    def test_eof_on_prompt_is_decline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "_stdin_is_interactive", lambda: True)

        def _eof(_prompt: str) -> str:
            raise EOFError

        monkeypatch.setattr(builtins, "input", _eof)
        assert failure_report.report_cli_failure(["validate"], _raise_value_error()) == 1
        assert not (tmp_path / "state").exists()

    def test_stdin_is_interactive_handles_broken_stream(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _Broken:
            def isatty(self) -> bool:
                raise ValueError("closed")

        monkeypatch.setattr(failure_report.sys, "stdin", _Broken())
        assert failure_report._stdin_is_interactive() is False


class TestCliWiring:
    def test_cmd_report_failure_delegates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: dict[str, object] = {}

        def _send(path: Path) -> int:
            seen["path"] = path
            return 0

        monkeypatch.setattr(failure_report, "send_persisted_report", _send)
        assert cli._cmd_report_failure(Namespace(file="some/report.json")) == 0
        assert seen["path"] == Path("some/report.json")
