"""Measure the real ``sofer-mcp`` cold start and compare it with the written deadline.

Issue #322. PR #311 writes each host's connect/startup deadline into the
registration entry from a value chosen against a *measurement* (the 16-32 s the
specs quote) rather than a measurement of **this** machine. On a slower host, a
cold container, or after a dependency lands in the import path, the written value
can be too small - and the failure is indistinguishable from a broken
registration, which is the symptom #287 exists to remove.

This module supplies the missing diagnostic: it spawns the real server, times the
stdio ``initialize`` round trip (import timing measures the wrong thing - the
host's deadline covers connect **and** handshake), and reports the measurement
beside the per-agent key and the value ``sofer mcp add`` would write there.

Three contracts this module keeps deliberately:

- **No MCP SDK import.** It must stay importable without the optional ``mcp``
  extra, because one of its most useful answers is "the server could not start":
  a doctor that refused to load without the very dependency it diagnoses would be
  useless in exactly the case that matters. The child needs the extra, not this
  module.
- **The measurement never changes an exit code by itself.** A slow machine is not
  a broken registration; the same informational contract as
  :func:`sofer.mcp_registration.dropped_timeout_note`. Only "nothing could be
  measured" is a failure, and the caller reads that from :attr:`Measurement.ok`.
- **The values are single-sourced.** Every key and value a row reports comes from
  :func:`sofer.mcp_registration.timeout_entry_keys`, so the doctor cannot disagree
  with what ``mcp add`` writes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from sofer import mcp_registration
from sofer._version import get_version

#: Console-script name declared by ``[project.scripts]`` in pyproject.toml.
CONSOLE_SCRIPT_NAME: str = "sofer-mcp"

#: Module entry point used when the console script is not on ``PATH``, so an
#: uninstalled checkout still measures (issue #322 §"Proposed solution" 3).
MODULE_ENTRY_POINT: tuple[str, ...] = ("-c", "from sofer.mcp_server import main; main()")

#: Label for the fallback entry point in reports and error messages.
MODULE_ENTRY_LABEL: str = "python -m sofer.mcp_server"

#: The MCP wire version this client asks for. The server negotiates and echoes
#: its own choice, so a mismatch surfaces as a protocol answer rather than a
#: silent misread.
PROTOCOL_VERSION: str = "2025-06-18"

#: Client name this module identifies itself with during ``initialize``.
_CLIENT_NAME: str = "sofer-mcp-doctor"

#: JSON-RPC id of the single request this module sends.
_INITIALIZE_REQUEST_ID: int = 1

#: How much of the child's stderr to quote when it fails to answer.
_STDERR_TAIL_CHARS: int = 400

#: How long to wait for a killed child to be reaped.
_REAP_TIMEOUT_SECONDS: float = 5.0


@dataclass(frozen=True)
class EntryPoint:
    """One way to launch the server, in the order resolution prefers them.

    Attributes:
        label: Human-facing name, used in reports and error messages.
        command: argv prefix, ready to pass to ``subprocess.Popen``.
    """

    label: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class Measurement:
    """The outcome of one real launch attempt.

    Attributes:
        entry_point: Label of the entry point that was attempted.
        elapsed_ms: Wall clock of the ``initialize`` round trip, in milliseconds.
        ok: Whether the round trip completed and its answer parsed.
        error: Why it did not, prefixed with the entry point tried; ``None`` on success.
    """

    entry_point: str
    elapsed_ms: int
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class AgentRow:
    """What ``sofer mcp add`` writes for one agent's cold-start deadline.

    Attributes:
        agent: Registry agent name.
        key: The entry key carrying the cold-start deadline -
            ``connect_timeout_key or timeout_key`` - or ``None`` when the agent's
            schema accepts no timeout at all (opencode today).
        value: The value written to :attr:`key`, in :attr:`unit`, or ``None``.
        unit: The adapter's unit for that key, or ``None`` when there is no key.
        note: MCP-REG-05's ``dropped_timeout_note`` when the agent has no key.
    """

    agent: str
    key: str | None
    value: int | None
    unit: str | None
    note: str | None


@dataclass(frozen=True)
class Report:
    """A measurement plus what each agent would be configured with.

    Attributes:
        measurement: The launch measurement.
        rows: One :class:`AgentRow` per requested agent, in the requested order.
        budget_seconds: The configured connect deadline the measurement is compared to.
        exceeds_budget: Whether the measurement is above that deadline.
        guidance: What to raise when it is, naming both flags; ``None`` otherwise.
    """

    measurement: Measurement
    rows: tuple[AgentRow, ...]
    budget_seconds: int
    exceeds_budget: bool
    guidance: str | None


def resolve_entry_point(which: Callable[[str], str | None] | None = None) -> EntryPoint:
    """Return the entry point to measure.

    Args:
        which: ``shutil.which``-compatible lookup, injected for tests.

    Returns:
        The console script when it is on ``PATH``, else the module entry point.
    """
    lookup = which or shutil.which
    found = lookup(CONSOLE_SCRIPT_NAME)
    if found:
        return EntryPoint(label=CONSOLE_SCRIPT_NAME, command=(found,))
    return EntryPoint(label=MODULE_ENTRY_LABEL, command=(sys.executable, *MODULE_ENTRY_POINT))


def measure(
    entry_point: EntryPoint,
    *,
    timeout_seconds: float,
    round_trip: Callable[[EntryPoint, float], float] | None = None,
) -> Measurement:
    """Time the ``initialize`` round trip of *entry_point*.

    Args:
        entry_point: What to spawn.
        timeout_seconds: The host deadline to reproduce; exceeding it is the finding.
        round_trip: Transport, injected for tests. Defaults to the real spawn.

    Returns:
        A :class:`Measurement`. A failure is always reported, never raised: a
        diagnostic that crashes instead of reporting is useless to the user who
        needs it.
    """
    transport = round_trip or _spawn_round_trip
    try:
        elapsed_seconds = transport(entry_point, timeout_seconds)
    except Exception as exc:
        return Measurement(
            entry_point=entry_point.label,
            elapsed_ms=0,
            ok=False,
            error=f"{entry_point.label}: {exc}",
        )
    return Measurement(
        entry_point=entry_point.label,
        elapsed_ms=round(elapsed_seconds * 1000),
        ok=True,
    )


def agent_rows(agents: Iterable[str], timeouts: mcp_registration.Timeouts) -> tuple[AgentRow, ...]:
    """Build one row per agent from the values ``mcp add`` would write.

    The cold-start key is ``connect_timeout_key or timeout_key``: pi, gemini and
    the single-key hosts declare one ``timeout`` that receives the request value,
    and only codex and hermes declare a separate startup key. The row therefore
    carries the adapter's own unit, so gemini's milliseconds cannot be read as
    seconds.

    Args:
        agents: Registry agent names, in the order to report.
        timeouts: The deadlines to read the values from.

    Returns:
        One :class:`AgentRow` per agent; an agent whose schema accepts no timeout
        carries its MCP-REG-05 note and no value.
    """
    rows: list[AgentRow] = []
    for agent in agents:
        spec = mcp_registration.ADAPTERS.get(agent)
        if spec is None:
            rows.append(AgentRow(agent, None, None, None, None))
            continue
        key = spec["connect_timeout_key"] or spec["timeout_key"]
        if key is None:
            rows.append(
                AgentRow(
                    agent,
                    None,
                    None,
                    None,
                    mcp_registration.dropped_timeout_note(agent, timeouts),
                )
            )
            continue
        written = mcp_registration.timeout_entry_keys(agent, timeouts)
        rows.append(AgentRow(agent, key, written[key], spec["timeout_unit"], None))
    return tuple(rows)


def build_report(
    agents: Iterable[str],
    *,
    measurement: Measurement,
    timeouts: mcp_registration.Timeouts,
    budget_seconds: int,
) -> Report:
    """Collate a measurement and the per-agent rows into one report.

    Args:
        agents: Registry agent names to report.
        measurement: The launch measurement.
        timeouts: The deadlines the rows read their values from.
        budget_seconds: The configured connect deadline to compare against.

    Returns:
        A :class:`Report` with the verdict and, when the budget is exceeded, the
        guidance naming both flags. A failed measurement never reports a verdict.
    """
    exceeds = measurement.ok and measurement.elapsed_ms > budget_seconds * 1000
    guidance: str | None = None
    if exceeds:
        guidance = (
            f"the measured cold start ({measurement.elapsed_ms} ms) is above the configured "
            f"connect deadline ({budget_seconds} s). Raise it with "
            "`sofer mcp add --agent <agent> --connect-timeout <seconds>` (and "
            "`--timeout <seconds>` for the per-request deadline), or raise "
            "`[tool.sofer] mcp_connect_timeout_seconds`."
        )
    return Report(
        measurement=measurement,
        rows=agent_rows(agents, timeouts),
        budget_seconds=budget_seconds,
        exceeds_budget=exceeds,
        guidance=guidance,
    )


def to_payload(report: Report, *, exit_code: int) -> dict[str, Any]:
    """Return the CLI-R10 stable-key JSON object for *report*.

    Args:
        report: The report to serialize.
        exit_code: The exit code the command will return.

    Returns:
        A JSON-serializable dict of primitives only - the CLI-R10 keys (``ok``,
        ``exit_code``, ``message``) plus this command's own keys, so the line is
        never a Python ``repr``.
    """
    measurement = report.measurement
    return {
        "ok": measurement.ok and exit_code == 0,
        "exit_code": exit_code,
        "message": _summary(measurement, report.budget_seconds),
        "entry_point": measurement.entry_point,
        "measured_ms": measurement.elapsed_ms,
        "connect_timeout_seconds": report.budget_seconds,
        "exceeds_budget": report.exceeds_budget,
        "guidance": report.guidance,
        "error": measurement.error,
        "agents": [
            {
                "agent": row.agent,
                "key": row.key,
                "value": row.value,
                "unit": row.unit,
                "note": row.note,
            }
            for row in report.rows
        ],
    }


def render_json(report: Report, *, exit_code: int) -> str:
    """Serialize :func:`to_payload` as one line of JSON.

    Args:
        report: The report to serialize.
        exit_code: The exit code the command will return.

    Returns:
        The JSON text, with no Python ``repr`` syntax.
    """
    return json.dumps(to_payload(report, exit_code=exit_code))


def render_human(report: Report) -> str:
    """Render the report for a human reading a terminal.

    Args:
        report: The report to render.

    Returns:
        The text to print, ending in a newline.
    """
    measurement = report.measurement
    lines = ["sofer mcp doctor — the real cold start of `sofer-mcp`", ""]
    if measurement.ok:
        lines.append(
            f"  measured      {measurement.elapsed_ms} ms   (stdio `initialize` round trip)"
        )
    else:
        lines.append(f"  measured      FAILED (0 ms) — {measurement.error}")
    lines.append(f"  entry point   {measurement.entry_point}")
    lines.append(
        f"  budget        {report.budget_seconds} s    ([tool.sofer] mcp_connect_timeout_seconds)"
    )
    lines.append("")
    lines.append("Per-agent cold-start deadline that `sofer mcp add` writes:")
    lines.append("")
    for row in report.rows:
        if row.key is None:
            lines.append(f"  {row.agent:<10} — {row.note or 'carries no timeout key'}")
        else:
            lines.append(f"  {row.agent:<10} {row.key} = {row.value} {row.unit}")
    if report.guidance:
        lines.append("")
        lines.append(f"  !  {report.guidance}")
    return "\n".join(lines) + "\n"


def _summary(measurement: Measurement, budget_seconds: int) -> str:
    """Return the one-line status message carried by the JSON payload.

    Args:
        measurement: The measurement to summarize.
        budget_seconds: The configured connect deadline.

    Returns:
        A single sentence, never empty.
    """
    if not measurement.ok:
        return f"could not measure the cold start: {measurement.error}"
    return (
        f"measured cold start {measurement.elapsed_ms} ms against a "
        f"{budget_seconds} s connect deadline"
    )


def _initialize_request() -> dict[str, Any]:
    """Return the single ``initialize`` JSON-RPC request this module sends.

    Returns:
        The request object, with the client identity this module reports.
    """
    return {
        "jsonrpc": "2.0",
        "id": _INITIALIZE_REQUEST_ID,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": _CLIENT_NAME, "version": get_version()},
        },
    }


def _spawn_round_trip(entry_point: EntryPoint, timeout_seconds: float) -> float:
    """Spawn the server, perform one ``initialize`` round trip, return elapsed seconds.

    The MCP stdio transport frames one JSON-RPC message per line, verified
    against the real server (no ``Content-Length`` headers). A
    ``threading.Timer`` kills the child at the deadline, which makes the blocked
    read return empty and turns the deadline into a reported failure instead of a
    hang - portable, unlike a ``select``-based read.

    Args:
        entry_point: What to spawn.
        timeout_seconds: Budget for the answer.

    Returns:
        Elapsed wall clock in seconds.

    Raises:
        subprocess.TimeoutExpired: The child did not answer within the budget.
        OSError: The child could not be started.
        ValueError: The child answered with something that is not an ``initialize`` result.
    """
    proc = subprocess.Popen(
        list(entry_point.command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    try:
        if proc.stdin is None or proc.stdout is None:
            raise OSError("the child was spawned without pipes")
        started = time.perf_counter()
        proc.stdin.write(json.dumps(_initialize_request()) + "\n")
        proc.stdin.flush()
        timer = threading.Timer(timeout_seconds, proc.kill)
        timer.start()
        try:
            answer = proc.stdout.readline()
        finally:
            timer.cancel()
        elapsed_seconds = time.perf_counter() - started
        if not answer.strip():
            _kill(proc)
            raise subprocess.TimeoutExpired(cmd=entry_point.label, timeout=timeout_seconds)
        try:
            payload = json.loads(answer)
        except json.JSONDecodeError as exc:
            _kill(proc)
            raise ValueError(
                f"the answer was not JSON ({exc}); stderr: {_stderr_tail(proc)}"
            ) from exc
        if not isinstance(payload.get("result"), dict):
            _kill(proc)
            raise ValueError(f"unexpected answer from the server; stderr: {_stderr_tail(proc)}")
        return elapsed_seconds
    finally:
        _kill(proc)


def _kill(proc: subprocess.Popen[str]) -> None:
    """Kill *proc* and reap it; a no-op when it already exited.

    Args:
        proc: The child to kill.
    """
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=_REAP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def _stderr_tail(proc: subprocess.Popen[str]) -> str:
    """Return a bounded tail of the child's stderr, for a failure message.

    Only called after the child exited (or was killed), so the read cannot block.

    Args:
        proc: The child whose stderr to read.

    Returns:
        The tail of stderr, or an empty string when there is nothing to read.
    """
    stream = proc.stderr
    if stream is None:
        return ""
    try:
        text: str = stream.read()
    except (OSError, ValueError):
        return ""
    return text.strip()[-_STDERR_TAIL_CHARS:]
