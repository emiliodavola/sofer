"""
Tests for the MCP ``sofer_report_failure`` tool (issue #244, MSP-R19).

The tool prepares a confidential failure report, searches open issues for
duplicates, and only files when called with ``confirm=true``. These tests drive
it through the real in-memory ``Client`` boundary and stub the ``gh``-touching
helpers so nothing reaches the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import call_tool

from sofer import failure_report
from sofer.mcp_server import build_server


def _call(server, name, args):  # type: ignore[no-untyped-def]
    return call_tool(server, name, args)


class TestReportFailureTool:
    def test_not_confirmed_prepares_without_sending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(failure_report, "search_open_issues", lambda repo, q: ([], None))
        sent: list[tuple[str, str, str]] = []
        monkeypatch.setattr(
            failure_report, "attempt_send", lambda *a: sent.append(a) or (None, "no")
        )
        server = build_server(root=tmp_path)
        env = _call(
            server,
            "sofer_report_failure",
            {"error": "ValueError: bad", "command": "sofer_validate"},
        ).data
        assert env["ok"] is True
        assert env["created"] is False
        assert "## Traceback" in env["body"]
        assert env["manual_url"].startswith("https://github.com/")
        assert env["hints"]["action"] == "confirm_report_failure"
        assert sent == []

    def test_duplicates_block_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dups = [{"number": 3, "title": "dup", "url": "https://github.com/o/r/issues/3"}]
        monkeypatch.setattr(failure_report, "search_open_issues", lambda repo, q: (dups, None))

        def _must_not_send(*_a):  # type: ignore[no-untyped-def]
            raise AssertionError("attempt_send must not run when duplicates block")

        monkeypatch.setattr(failure_report, "attempt_send", _must_not_send)
        server = build_server(root=tmp_path)
        env = _call(
            server,
            "sofer_report_failure",
            {"error": "boom", "command": "sofer_prepare", "confirm": True},
        ).data
        assert env["ok"] is False
        assert env["error_code"] == "DUPLICATE_REPORT"
        assert env["duplicates"] == dups

    def test_force_overrides_duplicates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dups = [{"number": 3, "title": "dup", "url": "u"}]
        monkeypatch.setattr(failure_report, "search_open_issues", lambda repo, q: (dups, None))
        monkeypatch.setattr(
            failure_report, "attempt_send", lambda *a: ("https://github.com/o/r/issues/9", None)
        )
        server = build_server(root=tmp_path)
        env = _call(
            server,
            "sofer_report_failure",
            {"error": "boom", "confirm": True, "force": True},
        ).data
        assert env["ok"] is True
        assert env["created"] is True
        assert env["issue_url"] == "https://github.com/o/r/issues/9"

    def test_confirmed_send_creates_issue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(failure_report, "search_open_issues", lambda repo, q: ([], None))
        monkeypatch.setattr(
            failure_report, "attempt_send", lambda *a: ("https://github.com/o/r/issues/4", None)
        )
        server = build_server(root=tmp_path)
        env = _call(server, "sofer_report_failure", {"error": "boom", "confirm": True}).data
        assert env["ok"] is True
        assert env["created"] is True
        assert env["issue_url"].endswith("/4")

    def test_send_failure_persists_locally(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setattr(failure_report, "search_open_issues", lambda repo, q: ([], None))
        monkeypatch.setattr(
            failure_report, "attempt_send", lambda *a: (None, "gh is not authenticated")
        )
        server = build_server(root=tmp_path)
        env = _call(
            server,
            "sofer_report_failure",
            {"error": "boom", "command": "sofer_validate", "confirm": True},
        ).data
        assert env["ok"] is False
        assert env["error_code"] == "REPORT_PERSISTED"
        assert Path(env["persisted_path"]).exists()
        assert env["retry_command"].startswith("sofer report-failure")
        assert env["hints"]["action"] == "gh_auth_login"

    def test_duplicate_query_carries_no_message_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The search query sent to GitHub contains only the anonymized command
        and the error TYPE — never a path, username, or dataset-derived token."""
        captured: dict[str, str] = {}

        def _search(repo: str, query: str) -> tuple[list[dict], None]:
            captured["query"] = query
            return [], None

        monkeypatch.setattr(failure_report, "search_open_issues", _search)
        server = build_server(root=tmp_path)
        _call(
            server,
            "sofer_report_failure",
            {
                "error": "FileNotFoundError: /home/alice/patient_records.csv user Sm1thJ0hn",
                "command": "sofer_validate",
            },
        )
        assert captured["query"] == "sofer_validate FileNotFoundError"
        for token in ("alice", "patient_records", "Sm1thJ0hn"):
            assert token not in captured["query"]

    def test_confidentiality_anonymizes_and_never_leaks_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SOFER_MCP_SECRET", "hunter2-xyz")
        monkeypatch.setattr(failure_report, "search_open_issues", lambda repo, q: ([], None))
        server = build_server(root=tmp_path)
        home = str(Path.home())
        env = _call(
            server,
            "sofer_report_failure",
            {"error": f"ValueError: at {home}/x.csv", "command": "sofer_validate"},
        ).data
        blob = json.dumps(env)
        assert "hunter2-xyz" not in blob
        assert home not in env["body"]
        assert "~" in env["body"]
