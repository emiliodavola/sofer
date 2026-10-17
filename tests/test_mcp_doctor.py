"""``sofer mcp doctor`` — the launch measurement and its report (issue #322).

What these pin, in the order the command uses them:

- entry-point resolution, and the module fallback when ``sofer-mcp`` is not on
  ``PATH`` (issue #322 §"Proposed solution" 3);
- the measurement itself, whose transport is injected so that no test spawns a
  subprocess to prove a code path — plus one *real* spawn, so the injected
  transport is not the only one ever exercised;
- the per-agent rows: the key that carries the cold-start deadline, the value
  ``sofer mcp add`` writes there in the adapter's own unit, and opencode's
  documented "carries no timeout key" note (MCP-REG-05) instead of a fabricated
  value;
- the verdict, and the informational exit code: a slow machine is not a broken
  registration, so only "nothing could be measured" fails (decision D1);
- the ``--json`` payload, which is CLI-R10's stable-key object and never a
  Python ``repr``.

The row model is the whole point of the first draft being wrong: an agent's
cold-start deadline is ``connect_timeout_key or timeout_key`` — pi and gemini
declare a *single* ``timeout`` that receives the request value — and gemini's
unit is milliseconds, so a row cannot carry one value with one implicit unit.
Every assertion that depends on the configured budgets reads ``sofer.config``
rather than a literal, so a configured change cannot make these tests lie
(AGENTS.md rule 1).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import PROCESS_TIMEOUT_SECONDS, run_cli

from sofer import cli, config, mcp_doctor, mcp_registration


def _entry_point() -> mcp_doctor.EntryPoint:
    """The console-script entry point, as resolution would return it."""
    return mcp_doctor.EntryPoint(label="sofer-mcp", command=("sofer-mcp",))


def _timeouts() -> mcp_registration.Timeouts:
    """The deadlines ``mcp add`` defaults to, from the live ``[tool.sofer]`` keys."""
    return mcp_registration.Timeouts(
        request_seconds=config.MCP_REQUEST_TIMEOUT_SECONDS,
        connect_seconds=config.MCP_CONNECT_TIMEOUT_SECONDS,
    )


def _ok_measurement(elapsed_ms: int = 1800) -> mcp_doctor.Measurement:
    """A successful measurement of *elapsed_ms*."""
    return mcp_doctor.Measurement(
        entry_point="sofer-mcp", elapsed_ms=elapsed_ms, ok=True, error=None
    )


def _report(agents: tuple[str, ...], elapsed_ms: int = 1800) -> mcp_doctor.Report:
    """A report over *agents* from a successful measurement."""
    return mcp_doctor.build_report(
        agents,
        measurement=_ok_measurement(elapsed_ms),
        timeouts=_timeouts(),
        budget_seconds=config.MCP_CONNECT_TIMEOUT_SECONDS,
    )


class TestEntryPointResolution:
    """``sofer-mcp`` when it is on ``PATH``, the module entry point when it is not."""

    def test_prefers_the_console_script(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mcp_doctor.shutil, "which", lambda _name: "/usr/bin/sofer-mcp")
        resolved = mcp_doctor.resolve_entry_point()
        assert resolved.label == "sofer-mcp"
        assert any("sofer-mcp" in part for part in resolved.command)

    def test_falls_back_to_the_module_entry_point(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Issue #322 §"Proposed solution" 3: an uninstalled checkout still measures."""
        monkeypatch.setattr(mcp_doctor.shutil, "which", lambda _name: None)
        resolved = mcp_doctor.resolve_entry_point()
        assert resolved.label != "sofer-mcp"
        assert mcp_doctor.MODULE_ENTRY_POINT[0] in resolved.command

    def test_the_fallback_names_the_module_it_runs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mcp_doctor.shutil, "which", lambda _name: None)
        resolved = mcp_doctor.resolve_entry_point()
        assert "sofer.mcp_server" in " ".join(resolved.command)


class TestMeasurement:
    """The round trip, its unit, its failure modes, and the child's cleanup."""

    def test_the_round_trip_is_reported_in_milliseconds(self) -> None:
        measurement = mcp_doctor.measure(
            _entry_point(), timeout_seconds=1.0, round_trip=lambda *_a: 1.5
        )
        assert measurement.elapsed_ms == 1500
        assert measurement.ok is True
        assert measurement.error is None

    def test_a_timeout_is_a_failure_that_names_the_budget(self) -> None:
        def _boom(*_args: Any) -> float:
            raise subprocess.TimeoutExpired(cmd="sofer-mcp", timeout=2)

        measurement = mcp_doctor.measure(_entry_point(), timeout_seconds=2.0, round_trip=_boom)
        assert measurement.ok is False
        assert measurement.error is not None
        assert "2" in measurement.error

    def test_a_start_failure_names_the_entry_point_it_tried(self) -> None:
        def _boom(*_args: Any) -> float:
            raise FileNotFoundError("no such executable")

        measurement = mcp_doctor.measure(_entry_point(), timeout_seconds=1.0, round_trip=_boom)
        assert measurement.ok is False
        assert "sofer-mcp" in (measurement.error or "")

    def test_the_measurement_records_which_entry_point_ran(self) -> None:
        measurement = mcp_doctor.measure(
            mcp_doctor.EntryPoint(label="python -m sofer.mcp_server", command=("python",)),
            timeout_seconds=1.0,
            round_trip=lambda *_a: 0.5,
        )
        assert measurement.entry_point == "python -m sofer.mcp_server"


class TestAgentRows:
    """The cold-start key, the value written there, and the unit it is in."""

    def test_codex_reports_its_startup_key_and_seconds(self) -> None:
        rows = mcp_doctor.agent_rows(("codex",), _timeouts())
        assert rows[0].key == mcp_registration.ADAPTERS["codex"]["connect_timeout_key"]
        assert rows[0].value == config.MCP_CONNECT_TIMEOUT_SECONDS
        assert rows[0].unit == "seconds"
        assert rows[0].note is None

    def test_hermes_reports_its_connect_key(self) -> None:
        rows = mcp_doctor.agent_rows(("hermes",), _timeouts())
        assert rows[0].key == mcp_registration.ADAPTERS["hermes"]["connect_timeout_key"]
        assert rows[0].value == config.MCP_CONNECT_TIMEOUT_SECONDS

    def test_a_single_key_agent_reports_that_key_and_its_request_value(self) -> None:
        """pi declares no separate connect key, so its one ``timeout`` is the answer."""
        rows = mcp_doctor.agent_rows(("pi",), _timeouts())
        assert mcp_registration.ADAPTERS["pi"]["connect_timeout_key"] is None
        assert rows[0].key == mcp_registration.ADAPTERS["pi"]["timeout_key"]
        assert rows[0].value == config.MCP_REQUEST_TIMEOUT_SECONDS

    def test_gemini_reports_milliseconds_not_seconds(self) -> None:
        """The unit is the adapter's, so the row cannot imply a wrong magnitude."""
        rows = mcp_doctor.agent_rows(("gemini",), _timeouts())
        assert mcp_registration.ADAPTERS["gemini"]["timeout_unit"] == "milliseconds"
        assert rows[0].value == config.MCP_REQUEST_TIMEOUT_SECONDS * 1000
        assert rows[0].unit == "milliseconds"

    def test_opencode_reports_its_scalar_connect_budget(self) -> None:
        """#320: opencode stops being MCP-REG-05's example, so its row carries a value."""
        rows = mcp_doctor.agent_rows(("opencode",), _timeouts())
        assert rows[0].key == "timeout"
        assert rows[0].value == _timeouts().connect_seconds * 1000
        assert rows[0].unit == "milliseconds"
        assert rows[0].note is None

    def test_every_registered_agent_gets_a_row(self) -> None:
        rows = mcp_doctor.agent_rows(mcp_registration.AGENT_NAMES, _timeouts())
        assert [row.agent for row in rows] == list(mcp_registration.AGENT_NAMES)

    def test_the_row_value_matches_what_mcp_add_would_write(self) -> None:
        """Single-sourced from ``timeout_entry_keys``, not re-derived here."""
        timeouts = _timeouts()
        for row in mcp_doctor.agent_rows(mcp_registration.AGENT_NAMES, timeouts):
            written = mcp_registration.timeout_entry_keys(row.agent, timeouts)
            if row.key is None:
                assert written == {}
            else:
                assert written[row.key] == row.value


class TestReportVerdict:
    """Below the budget is a pass; above it is a pass that names what to raise."""

    def test_a_measurement_below_the_budget_does_not_exceed(self) -> None:
        report = _report(("pi",), elapsed_ms=1800)
        assert report.exceeds_budget is False
        assert report.guidance is None

    def test_a_measurement_above_the_budget_names_both_flags(self) -> None:
        report = _report(("pi",), elapsed_ms=config.MCP_CONNECT_TIMEOUT_SECONDS * 1000 + 5000)
        assert report.exceeds_budget is True
        assert report.guidance is not None
        assert "--connect-timeout" in report.guidance
        assert "--timeout" in report.guidance

    def test_a_failed_measurement_never_claims_to_exceed(self) -> None:
        report = mcp_doctor.build_report(
            ("pi",),
            measurement=mcp_doctor.Measurement(
                entry_point="sofer-mcp", elapsed_ms=0, ok=False, error="boom"
            ),
            timeouts=_timeouts(),
            budget_seconds=config.MCP_CONNECT_TIMEOUT_SECONDS,
        )
        assert report.exceeds_budget is False


class TestJsonPayload:
    """CLI-R10: machine-readable status is stable JSON with the documented keys."""

    def test_the_payload_carries_the_stable_keys(self) -> None:
        payload = mcp_doctor.to_payload(_report(("pi",)), exit_code=0)
        assert payload["ok"] is True
        assert payload["exit_code"] == 0

    def test_the_payload_carries_the_measurement_and_the_rows(self) -> None:
        payload = mcp_doctor.to_payload(_report(("pi", "opencode"), elapsed_ms=1874), exit_code=0)
        assert payload["measured_ms"] == 1874
        assert payload["entry_point"] == "sofer-mcp"
        assert payload["connect_timeout_seconds"] == config.MCP_CONNECT_TIMEOUT_SECONDS
        assert [row["agent"] for row in payload["agents"]] == ["pi", "opencode"]
        # Issue #320: opencode used to be the row carrying a note instead of a
        # value. It now carries its own scalar, in the adapter's unit.
        opencode_row = payload["agents"][1]
        assert opencode_row["note"] is None
        assert opencode_row["key"] == "timeout"
        assert opencode_row["value"] == config.MCP_CONNECT_TIMEOUT_SECONDS * 1000
        assert opencode_row["unit"] == "milliseconds"

    def test_the_serialized_payload_is_json_not_a_repr(self) -> None:
        text = mcp_doctor.render_json(_report(("pi",)), exit_code=0)
        assert json.loads(text)["ok"] is True
        assert "{'ok'" not in text

    def test_a_failed_measurement_reports_not_ok(self) -> None:
        report = mcp_doctor.build_report(
            ("pi",),
            measurement=mcp_doctor.Measurement(
                entry_point="sofer-mcp", elapsed_ms=0, ok=False, error="boom"
            ),
            timeouts=_timeouts(),
            budget_seconds=config.MCP_CONNECT_TIMEOUT_SECONDS,
        )
        assert mcp_doctor.to_payload(report, exit_code=1)["ok"] is False

    def test_the_payload_serializes_without_a_custom_encoder(self) -> None:
        """Nothing in the payload may be a dataclass or a Path."""
        text = mcp_doctor.render_json(_report(("pi", "gemini")), exit_code=0)
        json.dumps(json.loads(text))


class TestHumanReport:
    """The line a user reads: the measurement, the budget, and the key that receives it."""

    def test_the_report_names_the_measurement_and_the_budget(self) -> None:
        text = mcp_doctor.render_human(_report(("pi",), elapsed_ms=1874))
        assert "1874" in text
        assert str(config.MCP_CONNECT_TIMEOUT_SECONDS) in text

    def test_the_report_names_the_agent_key(self) -> None:
        text = mcp_doctor.render_human(_report(("codex",)))
        assert mcp_registration.ADAPTERS["codex"]["connect_timeout_key"] in text

    def test_the_report_repeats_opencodes_note(self) -> None:
        assert "opencode" in mcp_doctor.render_human(_report(("opencode",)))


class TestCommandHandler:
    """The handler's exit code, its budget source, and its stream discipline (D1)."""

    def _args(self, **overrides: Any) -> argparse.Namespace:
        base: dict[str, Any] = {"agent": None, "json": False}
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_a_measurement_over_budget_still_exits_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D1: informational, exactly like ``dropped_timeout_note``. A slow machine
        is not a broken registration, and an exit code that said so would recreate
        the confusion the issue exists to remove."""
        monkeypatch.setattr(
            mcp_doctor,
            "measure",
            lambda *a, **k: _ok_measurement(config.MCP_CONNECT_TIMEOUT_SECONDS * 1000 + 5000),
        )
        assert cli._cmd_mcp_doctor(self._args()) == 0
        assert "--connect-timeout" in capsys.readouterr().out

    def test_nothing_measurable_exits_one_and_names_what_it_tried(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            mcp_doctor,
            "measure",
            lambda *a, **k: mcp_doctor.Measurement(
                entry_point="sofer-mcp", elapsed_ms=0, ok=False, error="boom"
            ),
        )
        assert cli._cmd_mcp_doctor(self._args()) == 1
        captured = capsys.readouterr()
        assert "sofer-mcp" in captured.err + captured.out

    def test_the_handler_uses_the_configured_connect_deadline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rule 1: the budget compared is the ``[tool.sofer]`` value, never a literal."""
        seen: list[Any] = []

        def _capture(*_args: Any, **kwargs: Any) -> mcp_doctor.Measurement:
            seen.append(kwargs.get("timeout_seconds"))
            return _ok_measurement()

        monkeypatch.setattr(mcp_doctor, "measure", _capture)
        cli._cmd_mcp_doctor(self._args())
        assert seen == [float(config.MCP_CONNECT_TIMEOUT_SECONDS)]

    def test_the_json_flag_emits_json_on_stdout(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(mcp_doctor, "measure", lambda *a, **k: _ok_measurement())
        assert cli._cmd_mcp_doctor(self._args(json=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["measured_ms"] == 1800

    def test_the_agent_flag_restricts_the_rows(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(mcp_doctor, "measure", lambda *a, **k: _ok_measurement())
        assert cli._cmd_mcp_doctor(self._args(agent="codex", json=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert [row["agent"] for row in payload["agents"]] == ["codex"]

    def test_the_all_agent_value_is_accepted(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(mcp_doctor, "measure", lambda *a, **k: _ok_measurement())
        assert cli._cmd_mcp_doctor(self._args(agent="all", json=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(payload["agents"]) == len(mcp_registration.AGENT_NAMES)


class TestCliSurface:
    """Rule 14: ``cli.py`` is under a 100.00% line mandate, so its surface is hit
    through the real subprocess boundary the PB-02 helper provides."""

    def test_mcp_help_lists_doctor(self, tmp_path: Path) -> None:
        result = run_cli(["mcp", "--help"], cwd=tmp_path)
        assert result.returncode == 0
        assert "doctor" in result.stdout

    def test_doctor_help_lists_its_flags(self, tmp_path: Path) -> None:
        result = run_cli(["mcp", "doctor", "--help"], cwd=tmp_path)
        assert result.returncode == 0
        assert "--agent" in result.stdout
        assert "--json" in result.stdout

    def test_doctor_help_documents_what_is_measured(self, tmp_path: Path) -> None:
        result = run_cli(["mcp", "doctor", "--help"], cwd=tmp_path)
        assert "initialize" in result.stdout


class TestRealLaunch:
    """The one test that spawns the real server, so the injected transport is not
    the only thing ever exercised (issue #322: measure the *real* launch)."""

    def test_the_real_launch_is_measured_and_reported_as_json(self, tmp_path: Path) -> None:
        result = run_cli(
            ["mcp", "doctor", "--json"],
            cwd=tmp_path,
            timeout=PROCESS_TIMEOUT_SECONDS * 4,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["measured_ms"] > 0
