"""
Assisted failure reporting for the CLI and the MCP server (issue #244).

Single home (AGENTS.md rule 4) for the execution-context collection, the
confidentiality rules, and the delivery paths shared by both adapters:

- :func:`collect_failure_context` captures a strict allowlist of facts about a
  runtime failure — command, arguments, exception type/message, traceback,
  ``sofer``/Python/platform metadata — and never reads a dataset or an
  environment-variable value.
- :func:`anonymize_paths` replaces the user's home directory with ``~`` in both
  POSIX and Windows forms.
- :func:`build_issue_body` renders the reviewable markdown body.
- :func:`persist_report` writes exactly one JSON file per failure under sofer's
  state directory (timestamped, never overwritten) so a report is never lost
  when ``gh`` is missing, unauthenticated, or offline.
- :func:`attempt_send` / :func:`create_issue` deliver through ``gh``;
  :func:`send_persisted_report` retries a saved report.
- :func:`report_cli_failure` is the interactive CLI entry point: it prints the
  original traceback, asks for consent, shows the full body for review, and
  sends or persists.

Nothing here is ever filed without explicit consent, and the persisted file,
the retry command and the manual issue URL form the three independent recovery
layers that guarantee no reportable failure is lost.
"""

from __future__ import annotations

import json
import os
import platform as _platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from . import config
from ._version import get_version

#: Application segment under the OS state directory. Not a user-tunable
#: default: it is the tool's own identity (AGENTS.md rule 1 covers tunables,
#: not the package name).
_STATE_APP_DIR = "sofer"

#: Filename prefix for persisted reports.
_REPORT_FILE_PREFIX = "failure"

#: Answers accepted as "yes" at an interactive prompt (case-insensitive).
_AFFIRMATIVE_ANSWERS = frozenset({"y", "yes"})

#: Truncation marker inserted when a traceback exceeds the configured cap.
_TRUNCATION_MARKER = "\n... [traceback truncated: {omitted} characters omitted] ...\n"

#: Matches a plausible Python exception class name: a capitalized identifier
#: ending in ``Error``/``Exception``, not embedded in a longer identifier. The
#: capitalization + boundary requirement rejects lowercase data-derived tokens
#: such as ``temperatureError``, so the MCP duplicate-search query stays bounded
#: to a class-like token.
_ERROR_TYPE_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Za-z0-9_]*(?:Error|Exception)\b")


@dataclass(frozen=True)
class FailureContext:
    """Allowlisted facts about a runtime failure.

    Attributes:
        command: The invoked subcommand token (e.g. ``"validate"``), or
            ``"sofer"`` when no subcommand token is present.
        argv: The command-line arguments after the program name, anonymized.
        error_type: The exception class name.
        error_message: The exception message, anonymized.
        traceback_text: The formatted traceback, anonymized and truncated.
        sofer_version: Installed ``sofer`` version.
        python_version: Interpreter version (``major.minor.patch``).
        platform: Platform string, anonymized.
        timestamp: ISO-8601 UTC capture time.
    """

    command: str
    argv: tuple[str, ...]
    error_type: str
    error_message: str
    traceback_text: str
    sofer_version: str
    python_version: str
    platform: str
    timestamp: str


def _utc_now() -> str:
    """Return the current time as an ISO-8601 UTC string with microseconds."""
    return datetime.now(timezone.utc).isoformat()


def anonymize_paths(text: str, *, home: Path | None = None) -> str:
    """Replace the user's home directory with ``~`` in both path forms.

    Covers the POSIX form (``/home/alice``), the Windows form
    (``C:\\Users\\alice``) and the forward-slash variant of the Windows form,
    so a traceback rendered on either platform is anonymized. The longest
    candidate is replaced first to avoid a shorter prefix shadowing it, and a
    candidate made only of separators (a filesystem root such as ``/``) is
    skipped so a root home never rewrites unrelated path separators.

    Args:
        text: The string to anonymize.
        home: Override for the home directory (tests); defaults to
            :func:`pathlib.Path.home`.

    Returns:
        The anonymized string; empty input is returned unchanged.
    """
    if not text:
        return text
    home_path = home if home is not None else Path.home()
    candidates = {
        str(home_path),
        home_path.as_posix(),
        str(home_path).replace("/", "\\"),
        str(home_path).replace("\\", "\\\\"),
    }
    result = text
    for candidate in sorted(candidates, key=len, reverse=True):
        if candidate.strip("/\\"):
            result = result.replace(candidate, "~")
    return result


def _truncate(text: str) -> str:
    """Cap *text* at ``config.FAILURE_REPORT_TRACEBACK_MAX_CHARS``.

    Keeps the head and the tail (the tail carries the exception line) with a
    marker naming the number of omitted characters.
    """
    limit = config.FAILURE_REPORT_TRACEBACK_MAX_CHARS
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    marker = _TRUNCATION_MARKER.format(omitted=omitted)
    budget = max(0, limit - len(marker))
    head = budget // 2
    tail = budget - head
    return text[:head] + marker + (text[-tail:] if tail else "")


def collect_failure_context(
    argv: list[str] | tuple[str, ...],
    exc: BaseException,
    *,
    home: Path | None = None,
) -> FailureContext:
    """Collect the allowlisted execution context for *exc*.

    No environment value and no dataset content is read. Every emitted string
    is passed through :func:`anonymize_paths`.

    Args:
        argv: Command-line arguments after the program name (``sys.argv[1:]``).
        exc: The uncaught exception.
        home: Override for the home directory (tests).

    Returns:
        A populated :class:`FailureContext`.
    """
    anonymized_argv = tuple(anonymize_paths(arg, home=home) for arg in argv)
    command = anonymized_argv[0] if anonymized_argv else _STATE_APP_DIR
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return FailureContext(
        command=command,
        argv=anonymized_argv,
        error_type=type(exc).__name__,
        error_message=anonymize_paths(str(exc), home=home),
        traceback_text=_truncate(anonymize_paths(formatted, home=home)),
        sofer_version=get_version(),
        python_version=_platform.python_version(),
        platform=anonymize_paths(_platform.platform(), home=home),
        timestamp=_utc_now(),
    )


def context_from_parts(
    command: str,
    error: str,
    trace: str = "",
    *,
    home: Path | None = None,
) -> FailureContext:
    """Build a :class:`FailureContext` from agent-supplied strings (MCP path).

    The MCP adapter has no live exception object: the agent passes the failed
    command/tool and the error text it observed. The same anonymization and
    truncation as :func:`collect_failure_context` applies, and the command is
    carried as the sole argument so the body shows ``sofer <command>``.

    Args:
        command: The command or MCP tool that failed.
        error: The error message or summary.
        trace: Optional traceback text.
        home: Override for the home directory (tests).

    Returns:
        A populated :class:`FailureContext`.
    """
    clean_command = anonymize_paths(command, home=home)
    return FailureContext(
        command=clean_command or _STATE_APP_DIR,
        argv=(clean_command,) if clean_command else (),
        error_type=_error_type_from(error),
        error_message=anonymize_paths(error, home=home),
        traceback_text=_truncate(anonymize_paths(trace, home=home)),
        sofer_version=get_version(),
        python_version=_platform.python_version(),
        platform=anonymize_paths(_platform.platform(), home=home),
        timestamp=_utc_now(),
    )


def _error_type_from(error: str) -> str:
    """Return the first plausible ``*Error``/``*Exception`` class token, else ``Failure``."""
    match = _ERROR_TYPE_RE.search(error)
    return match.group(0) if match else "Failure"


def build_issue_title(ctx: FailureContext) -> str:
    """Return a short, searchable issue title for *ctx*."""
    return f"[crash] {_STATE_APP_DIR} {ctx.command}: {ctx.error_type}"


def build_issue_body(ctx: FailureContext, *, repo: str) -> str:
    """Render the reviewable markdown issue body for *ctx*.

    The body carries only the allowlisted facts: no dataset content, no
    environment values, and home paths replaced by ``~``.

    Args:
        ctx: The failure context.
        repo: The target ``owner/repo`` (named in the confidentiality note).

    Returns:
        The complete markdown body shown for review and sent verbatim.
    """
    invocation = " ".join((_STATE_APP_DIR, *ctx.argv)) if ctx.argv else _STATE_APP_DIR
    return (
        "> Generated by `sofer report-failure`. Review the field values before sending; "
        "edit out anything you do not want public.\n"
        "\n"
        "## Summary\n"
        "\n"
        f"`{invocation}` failed with `{ctx.error_type}`.\n"
        "\n"
        "## Command\n"
        "\n"
        "```text\n"
        f"{invocation}\n"
        "```\n"
        "\n"
        "## Error\n"
        "\n"
        "```text\n"
        f"{ctx.error_type}: {ctx.error_message}\n"
        "```\n"
        "\n"
        "## Traceback\n"
        "\n"
        "```text\n"
        f"{ctx.traceback_text}"
        "\n"
        "```\n"
        "\n"
        "## Environment\n"
        "\n"
        f"- `sofer`: {ctx.sofer_version}\n"
        f"- `python`: {ctx.python_version}\n"
        f"- `platform`: {ctx.platform}\n"
        f"- `captured_at`: {ctx.timestamp}\n"
        "\n"
        "## Confidentiality\n"
        "\n"
        f"This report was assembled by sofer's assisted reporter for `{repo}`. It contains no "
        "dataset contents and no environment-variable values; local paths are anonymized "
        "(`~` is the home directory).\n"
    )


def state_home() -> Path:
    """Return sofer's state directory for persisted reports.

    Resolution order: the ``SOFER_STATE_HOME`` override (used by tests and
    hermetic installs), ``LOCALAPPDATA`` on Windows, ``XDG_STATE_HOME`` on
    POSIX, then ``~/.local/state``. The :data:`_STATE_APP_DIR` segment is
    appended except when ``SOFER_STATE_HOME`` is set, which is taken verbatim
    as the app-specific directory.
    """
    override = os.environ.get("SOFER_STATE_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", "").strip()
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / _STATE_APP_DIR
    xdg = os.environ.get("XDG_STATE_HOME", "").strip()
    root = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return root / _STATE_APP_DIR


def reports_dir() -> Path:
    """Return the directory persisted reports are written to."""
    return state_home() / config.FAILURE_REPORT_DIR


def persist_report(
    repo: str,
    title: str,
    body: str,
    *,
    stamp: str | None = None,
) -> Path:
    """Write one JSON report file per failure; never overwrite an existing one.

    Args:
        repo: Target ``owner/repo``.
        title: Issue title.
        body: Issue body (already anonymized).
        stamp: Optional UTC timestamp token override (tests); defaults to the
            current UTC time.

    Returns:
        The path of the written file (``failure-<stamp>-<pid>[-n].json``).
    """
    directory = reports_dir()
    directory.mkdir(parents=True, exist_ok=True)
    token = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    candidate = directory / f"{_REPORT_FILE_PREFIX}-{token}-{os.getpid()}.json"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{_REPORT_FILE_PREFIX}-{token}-{os.getpid()}-{counter}.json"
        counter += 1
    payload: dict[str, Any] = {
        "repo": repo,
        "title": title,
        "body": body,
        "created_at": _utc_now(),
    }
    candidate.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding=config.OUTPUT_ENCODING,
    )
    return candidate


def load_report(path: Path) -> dict[str, Any]:
    """Load a persisted report document.

    Args:
        path: Path to a JSON report written by :func:`persist_report`.

    Returns:
        The decoded mapping.

    Raises:
        ValueError: When the file does not decode to a JSON object.
    """
    data = json.loads(Path(path).read_text(encoding=config.OUTPUT_ENCODING))
    if not isinstance(data, dict):
        raise ValueError(f"report file is not a JSON object: {path}")
    return data


def retry_command(path: Path | str) -> str:
    """Return the shell command that retries a persisted report."""
    return f'{_STATE_APP_DIR} report-failure "{path}"'


def manual_issue_url(repo: str, title: str, body: str) -> str:
    """Return a ``github.com/<repo>/issues/new`` URL, prefilling the title.

    The body is prefilled only when it fits within
    ``config.FAILURE_REPORT_MANUAL_URL_MAX_CHARS``; a longer body would produce
    a URL no browser or shell accepts, so it is omitted and the caller points
    the user at the saved file instead.
    """
    params = {"title": title}
    if len(body) <= config.FAILURE_REPORT_MANUAL_URL_MAX_CHARS:
        params["body"] = body
    return f"https://github.com/{repo}/issues/new?{urlencode(params)}"


def gh_available() -> bool:
    """Whether the ``gh`` CLI is on ``PATH``."""
    return shutil.which("gh") is not None


def _run_gh(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    """Run ``gh`` with *args*, returning ``None`` when it cannot be executed."""
    try:
        return subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding=config.OUTPUT_ENCODING,
            errors="replace",
            check=False,
            timeout=config.FAILURE_REPORT_GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def gh_authenticated() -> bool:
    """Whether ``gh auth status`` succeeds (and ``gh`` exists)."""
    if not gh_available():
        return False
    proc = _run_gh(["auth", "status"])
    return proc is not None and proc.returncode == 0


def create_issue(repo: str, title: str, body: str) -> tuple[bool, str]:
    """Create a GitHub issue through ``gh``.

    Args:
        repo: Target ``owner/repo``.
        title: Issue title.
        body: Issue body.

    Returns:
        ``(True, url)`` on success, ``(False, stderr)`` on failure. The URL
        falls back to the ``gh`` stdout when it cannot be parsed.
    """
    handle, name = tempfile.mkstemp(suffix=".md", prefix="sofer-report-")
    os.close(handle)
    body_path = Path(name)
    try:
        body_path.write_text(body, encoding=config.OUTPUT_ENCODING)
        proc = _run_gh(
            ["issue", "create", "--repo", repo, "--title", title, "--body-file", str(body_path)]
        )
    finally:
        body_path.unlink(missing_ok=True)
    if proc is None:
        return False, "gh CLI is not available"
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "gh issue create failed").strip()
    return True, proc.stdout.strip()


def attempt_send(repo: str, title: str, body: str) -> tuple[str | None, str | None]:
    """Try to file the report, returning ``(url, reason)``.

    Exactly one element is non-``None``. The auth preflight avoids ``gh``
    opening an interactive login (which would hang a non-interactive run).
    """
    if not gh_available():
        return None, "gh CLI not found"
    if not gh_authenticated():
        return None, "gh is not authenticated"
    ok, detail = create_issue(repo, title, body)
    return (detail, None) if ok else (None, detail)


def duplicate_query(command: str, error_type: str) -> str:
    """Build a ``gh issue list --search`` query from a failure's identifiers.

    Callers MUST pass only the anonymized command and the error TYPE (never the
    error message, a path, or any dataset-derived text): the query is sent to
    GitHub, so it must be free of user data. The first
    ``failure_report_duplicate_query_tokens`` identifier tokens are kept; the
    result falls back to the command or the error type when no token is found.
    """
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]+", f"{command} {error_type}")
    limit = config.FAILURE_REPORT_DUPLICATE_QUERY_TOKENS
    return " ".join(words[:limit]) or command or error_type


def search_open_issues(repo: str, query: str) -> tuple[list[dict[str, Any]], str | None]:
    """Search *repo*'s open issues for a possible duplicate of *query*.

    Args:
        repo: Target ``owner/repo``.
        query: Search terms (see :func:`duplicate_query`).

    Returns:
        ``(matches, reason)`` — ``matches`` is the parsed ``gh issue list``
        JSON (``number``/``title``/``url``), and ``reason`` is ``None`` on a
        clean search or a short explanation when ``gh`` is unavailable,
        unauthenticated, offline, or returned unparseable output. An empty
        search never blocks filing.
    """
    if not gh_available():
        return [], "gh CLI not found"
    if not gh_authenticated():
        return [], "gh is not authenticated"
    proc = _run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--search",
            query,
            "--json",
            "number,title,url",
            "--limit",
            str(config.FAILURE_REPORT_DUPLICATE_LIMIT),
        ]
    )
    if proc is None or proc.returncode != 0:
        return [], "gh issue list failed"
    try:
        parsed = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return [], "could not parse gh output"
    if not isinstance(parsed, list):
        return [], "unexpected gh output"
    return [item for item in parsed if isinstance(item, dict)], None


def _print_recovery(repo: str, title: str, body: str, path: Path) -> None:
    """Print the triple safety net for an unsent report.

    Names the saved file, the retry command, the prefilled manual issue URL,
    and the permanent fix (``gh auth login``) — never a secret value.
    """
    print("")
    print("  X  The failure report could not be sent automatically.")
    print(f"     Saved report:     {path}")
    print(f"     Retry later:       {retry_command(path)}")
    print(f"     Or open manually:  {manual_issue_url(repo, title, body)}")
    if len(body) > config.FAILURE_REPORT_MANUAL_URL_MAX_CHARS:
        print(f"     (The body is too long to prefill in the URL; paste it from {path}.)")
    print("     Permanent fix:     gh auth login")


def send_persisted_report(path: Path | str) -> int:
    """Send a persisted report through ``gh``; print the URL or the recovery layers.

    Args:
        path: Path to a JSON report written by :func:`persist_report`.

    Returns:
        ``0`` when the issue was created, ``1`` otherwise.
    """
    data = load_report(Path(path))
    repo = str(data.get("repo") or config.FAILURE_REPORT_REPO)
    title = str(data.get("title", ""))
    body = str(data.get("body", ""))
    url, _reason = attempt_send(repo, title, body)
    if url is not None:
        print(f"  i  Report filed: {url}")
        return 0
    _print_recovery(repo, title, body, Path(path))
    return 1


def report_cli_failure(argv: list[str] | tuple[str, ...], exc: BaseException) -> int:
    """Offer to report an uncaught CLI failure, then send or persist it.

    Prints the original traceback first (preserving the pre-change failure
    output), then — only when ``sys.stdin`` is a TTY — asks for consent, shows
    the full anonymized body for review, and files it. Declining either prompt
    creates nothing. The caller always keeps exit code ``1`` for the failure.

    Args:
        argv: Command-line arguments after the program name.
        exc: The uncaught exception.

    Returns:
        ``1`` always (the originating command failed).
    """
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(anonymize_paths(formatted), file=sys.stderr, end="")

    if not _stdin_is_interactive():
        return 1

    repo = config.FAILURE_REPORT_REPO
    if not _ask_yes_no(f"\nReport this failure to {repo}?"):
        print("  i  No report created.")
        return 1

    ctx = collect_failure_context(argv, exc)
    title = build_issue_title(ctx)
    body = build_issue_body(ctx, repo=repo)
    print("\n----- BEGIN REPORT -----")
    print(body, end="")
    print("----- END REPORT -----\n")
    if not _ask_yes_no("Send this report?"):
        print("  i  Report not sent.")
        return 1

    url, _reason = attempt_send(repo, title, body)
    if url is not None:
        print(f"  i  Report filed: {url}")
        return 1
    path = persist_report(repo, title, body)
    _print_recovery(repo, title, body, path)
    return 1


def _stdin_is_interactive() -> bool:
    """Whether stdin is an interactive TTY (prompt gate)."""
    try:
        return bool(sys.stdin.isatty())
    except (AttributeError, ValueError):
        return False


def _ask_yes_no(question: str) -> bool:
    """Prompt *question* and return True only on an affirmative answer.

    ``EOFError`` (closed stdin) counts as "no".
    """
    try:
        answer = input(f"{question} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in _AFFIRMATIVE_ANSWERS
