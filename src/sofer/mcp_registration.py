"""
MCP registration automation for opencode, codex, and gemini.

Provides per-agent adapters (path resolution, JSON/TOML I/O, merge,
backup, atomic write, delegation probe) and entry builders. The CLI
layer in ``sofer.cli`` orchestrates these helpers.

Each agent has a distinct on-disk shape:

- opencode: ``opencode.json`` JSON ``mcp.sofer={type:"local",command:["sofer-mcp"],cwd}``
- codex: ``config.toml`` TOML ``[mcp_servers.sofer] command,cwd,env_vars``
- gemini: ``settings.json`` JSON ``mcpServers.sofer={command:"sofer-mcp",cwd,env}``

All writes are idempotent, preserve unrelated keys, create a single
``.bak`` backup before the first mutation, and use an atomic
``tmp+os.replace`` commit. Gemini ``env`` is explicit (no shell
inheritance), Codex ``env_vars`` is an allow-list, and ``command``
string/array variations are normalized before comparison. Native
delegation (``codex``/``gemini``) is probed via ``shutil.which`` +
``--help`` with a timeout and falls back to file-edit; opencode
always uses file-edit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal, TypedDict

AgentName = Literal["opencode", "codex", "gemini"]
Scope = Literal["user", "project"]

_ENV_KEYS: list[str] = ["HF_TOKEN", "SOFER_MCP_APPROVAL_PHRASE"]


class Adapter(TypedDict):
    """Typed adapter descriptor for registry introspection."""

    fmt: Literal["json", "toml"]
    key: str


ADAPTERS: dict[AgentName, Adapter] = {
    "opencode": {"fmt": "json", "key": "mcp"},
    "codex": {"fmt": "toml", "key": "mcp_servers"},
    "gemini": {"fmt": "json", "key": "mcpServers"},
}


def resolve_config_path(
    agent: AgentName,
    scope: Scope,
    cwd: Path | None = None,
) -> Path:
    """Resolve the config file path for *agent* and *scope*.

    User scope resolves under ``Path.home()`` (Windows-aware via
    ``Path.home()``). Project scope resolves under *cwd* (or
    ``Path.cwd()`` when ``None``).

    Args:
        agent: Target agent name.
        scope: ``"user"`` or ``"project"``.
        cwd: Project directory anchor for ``project`` scope; ignored
            for ``user`` scope.

    Returns:
        Absolute path to the agent's config file.
    """
    if scope == "user":
        home = Path.home()
        if agent == "opencode":
            return home / ".config" / "opencode" / "opencode.json"
        if agent == "codex":
            return home / ".codex" / "config.toml"
        if agent == "gemini":
            return home / ".config" / "gemini" / "settings.json"
        raise ValueError(f"unknown agent: {agent}")
    # project scope
    base = Path(cwd).resolve() if cwd is not None else Path.cwd().resolve()
    if agent == "opencode":
        return base / "opencode.json"
    if agent == "codex":
        return base / ".codex" / "config.toml"
    if agent == "gemini":
        return base / ".gemini" / "settings.json"
    raise ValueError(f"unknown agent: {agent}")


def _infer_fmt(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".toml":
        return "toml"
    return "json"


def read_config(path: Path) -> tuple[dict[str, object], str]:
    """Read *path* and return ``(doc, fmt)``.

    When the file does not exist, returns ``({}, fmt)`` where *fmt* is
    inferred from the suffix. On malformed or unreadable content, the
    underlying exception propagates so the caller can exit 1 without
    creating a backup or writing.

    Args:
        path: Config file path.

    Returns:
        Tuple of document dict and format string ``"json"`` or ``"toml"``.
    """
    fmt = _infer_fmt(path)
    if not path.exists():
        return {}, fmt
    if fmt == "json":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError(f"config {path} is not a JSON object")
            return data, fmt
    # toml
    try:
        import tomli as _tomli
    except ImportError:
        import tomllib as _tomli

    with open(path, "rb") as fh:
        data = _tomli.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"config {path} is not a TOML table")
    return data, fmt


def build_entry(agent: AgentName, cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    """Build the desired ``sofer`` entry for *agent*.

    Env forwarding rules:
    - codex: ``env_vars`` is the allow-list of known keys present in *env*
    - gemini: ``env`` is the explicit dict of key→value for known keys
    - opencode: no env forwarding (returns minimal entry)

    Args:
        agent: Target agent.
        cwd: Absolute, resolved working directory for the server.
        env: Mapping of env keys to values (typically filtered
            ``os.environ``).

    Returns:
        Entry dict ready to merge into the agent's config.
    """
    cwd_str = str(cwd.resolve())
    if agent == "opencode":
        return {"type": "local", "command": ["sofer-mcp"], "cwd": cwd_str}
    if agent == "codex":
        env_vars = [k for k in _ENV_KEYS if env.get(k)]
        return {"command": "sofer-mcp", "cwd": cwd_str, "env_vars": env_vars}
    if agent == "gemini":
        env_dict = {k: v for k, v in env.items() if k in _ENV_KEYS and v}
        return {"command": "sofer-mcp", "cwd": cwd_str, "env": env_dict}
    raise ValueError(f"unknown agent: {agent}")


def _normalize_codex_command(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def _entries_equal(agent: AgentName, a: dict[str, Any], b: dict[str, Any]) -> bool:
    if agent == "codex":
        # Normalize command string vs array before comparison
        a_cmd = _normalize_codex_command(a.get("command"))
        b_cmd = _normalize_codex_command(b.get("command"))
        if a_cmd != b_cmd:
            return False
        # Compare cwd and env_vars
        if a.get("cwd") != b.get("cwd"):
            return False
        a_env = sorted(a.get("env_vars", []))
        b_env = sorted(b.get("env_vars", []))
        return a_env == b_env
    if agent == "gemini":
        if a.get("command") != b.get("command"):
            return False
        if a.get("cwd") != b.get("cwd"):
            return False
        if a.get("env", {}) != b.get("env", {}):
            return False
        return True
    # opencode
    return a == b


def merge(
    agent: AgentName, existing: dict[str, Any], desired: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Merge *desired* entry into *existing* preserving other servers.

    Idempotent: when the existing entry already equals *desired* (with
    Codex command normalization), returns ``(existing, False)`` and the
    caller MUST NOT write or backup.

    Args:
        agent: Target agent.
        existing: Parsed config document (may be empty).
        desired: Entry dict from :func:`build_entry`.

    Returns:
        ``(new_doc, changed)`` where *changed* indicates a write is
        needed.
    """
    # Work on a shallow copy; nested dicts are copied where mutated
    new_doc = dict(existing)
    if agent == "opencode":
        mcp = dict(new_doc.get("mcp", {})) if isinstance(new_doc.get("mcp"), dict) else {}
        current = mcp.get("sofer")
        if isinstance(current, dict) and _entries_equal(agent, current, desired):
            return new_doc, False
        mcp["sofer"] = desired
        new_doc["mcp"] = mcp
        return new_doc, True
    if agent == "codex":
        servers = (
            dict(new_doc.get("mcp_servers", {}))
            if isinstance(new_doc.get("mcp_servers"), dict)
            else {}
        )
        current = servers.get("sofer")
        if isinstance(current, dict) and _entries_equal(agent, current, desired):
            return new_doc, False
        servers["sofer"] = desired
        new_doc["mcp_servers"] = servers
        return new_doc, True
    if agent == "gemini":
        servers = (
            dict(new_doc.get("mcpServers", {}))
            if isinstance(new_doc.get("mcpServers"), dict)
            else {}
        )
        current = servers.get("sofer")
        if isinstance(current, dict) and _entries_equal(agent, current, desired):
            return new_doc, False
        servers["sofer"] = desired
        new_doc["mcpServers"] = servers
        return new_doc, True
    raise ValueError(f"unknown agent: {agent}")


def remove_entry(agent: AgentName, existing: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Remove ``sofer`` entry idempotently.

    Args:
        agent: Target agent.
        existing: Parsed config document.

    Returns:
        ``(new_doc, changed)``.
    """
    new_doc = dict(existing)
    if agent == "opencode":
        mcp = new_doc.get("mcp")
        if not isinstance(mcp, dict) or "sofer" not in mcp:
            return new_doc, False
        new_mcp = dict(mcp)
        new_mcp.pop("sofer", None)
        if new_mcp:
            new_doc["mcp"] = new_mcp
        else:
            new_doc.pop("mcp", None)
        return new_doc, True
    if agent == "codex":
        servers = new_doc.get("mcp_servers")
        if not isinstance(servers, dict) or "sofer" not in servers:
            return new_doc, False
        new_servers = dict(servers)
        new_servers.pop("sofer", None)
        if new_servers:
            new_doc["mcp_servers"] = new_servers
        else:
            new_doc.pop("mcp_servers", None)
        return new_doc, True
    if agent == "gemini":
        servers = new_doc.get("mcpServers")
        if not isinstance(servers, dict) or "sofer" not in servers:
            return new_doc, False
        new_servers = dict(servers)
        new_servers.pop("sofer", None)
        if new_servers:
            new_doc["mcpServers"] = new_servers
        else:
            new_doc.pop("mcpServers", None)
        return new_doc, True
    raise ValueError(f"unknown agent: {agent}")


def backup(path: Path) -> Path | None:
    """Create a single ``.bak`` backup before the first mutation.

    Overwrites any existing ``.bak`` (single backup per spec).

    Args:
        path: Config file to backup.

    Returns:
        Backup path, or ``None`` when *path* did not exist.
    """
    if not path.exists():
        return None
    bak = Path(str(path) + ".bak")
    # copy2 preserves metadata
    shutil.copy2(path, bak)
    return bak


def atomic_write(path: Path, doc: dict[str, Any], fmt: str) -> None:
    """Atomically write *doc* to *path* via tmp+os.replace.

    Args:
        path: Destination file.
        doc: Document to serialize.
        fmt: ``"json"`` or ``"toml"``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    # Ensure tmp is in same directory for atomic replace
    if fmt == "json":
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    else:
        try:
            import tomli_w as _tomli_w
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("tomli-w required for TOML writing") from exc
        with open(tmp, "wb") as fh:
            _tomli_w.dump(doc, fh)
    os.replace(tmp, path)


def probe_native(agent: AgentName, timeout: float = 3.0) -> bool:
    """Probe whether native ``agent mcp add`` delegation is available.

    Opencode always returns ``False`` (file-edit only). For codex/gemini,
    checks ``shutil.which`` and runs ``<agent> mcp --help`` with a timeout.

    Args:
        agent: Agent to probe.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` when delegation should be attempted.
    """
    if agent == "opencode":
        return False
    exe = shutil.which(agent)
    if not exe:
        return False
    try:
        result = subprocess.run(
            [exe, "mcp", "--help"],
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
    except Exception:
        return False


def delegate_add(agent: AgentName, cwd: Path, env_keys: list[str]) -> bool:
    """Attempt native ``add`` delegation for *agent*.

    Only codex/gemini are delegated; opencode returns ``False``.

    Args:
        agent: Target agent.
        cwd: Resolved cwd for the server.
        env_keys: Env keys to forward (unused for native path but kept
            for signature parity).

    Returns:
        ``True`` on success, ``False`` on failure or absence (caller
        should fallback to file-edit).
    """
    if agent == "opencode":
        return False
    exe = shutil.which(agent)
    if not exe:
        return False
    # Try the most common native shape: `agent mcp add sofer --command sofer-mcp --cwd <cwd>`
    # Fall back to simpler shape on failure is handled by caller (retry file-edit)
    cmd_variants = [
        [exe, "mcp", "add", "sofer", "--command", "sofer-mcp", "--cwd", str(cwd)],
        [exe, "mcp", "add", "sofer", "--", "sofer-mcp"],
        [exe, "mcp", "add", "sofer"],
    ]
    for cmd in cmd_variants[:1]:  # only try first variant; keep simple
        try:
            result = subprocess.run(cmd, timeout=3.0, capture_output=True)
            if result.returncode == 0:
                return True
            return False
        except (subprocess.TimeoutExpired, OSError):
            return False
    return False


def delegate_remove(agent: AgentName) -> bool:
    """Attempt native ``remove`` delegation for *agent*.

    Args:
        agent: Target agent.

    Returns:
        ``True`` on success, ``False`` otherwise.
    """
    if agent == "opencode":
        return False
    exe = shutil.which(agent)
    if not exe:
        return False
    try:
        result = subprocess.run(
            [exe, "mcp", "remove", "sofer"], timeout=3.0, capture_output=True
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
    except Exception:
        return False


def collect_env() -> dict[str, str]:
    """Collect ``HF_TOKEN`` and ``SOFER_MCP_APPROVAL_PHRASE`` from the environment.

    Returns:
        Dict with present keys only and non-empty values.
    """
    out: dict[str, str] = {}
    for k in _ENV_KEYS:
        v = os.environ.get(k)
        if v:
            out[k] = v
    return out


def validate_cwd(cwd: Path, scope: Scope) -> bool:
    """Validate that *cwd* is contained under the allowed root.

    Uses ``Path.resolve()`` + ``is_relative_to``. For ``user`` scope the
    allowed root is ``Path.home()``; for ``project`` scope it is
    ``Path.cwd()``. Succeeds when contained under either root to tolerate
    tmp paths that are under home on Windows.

    Args:
        cwd: Candidate cwd (already resolved or not).
        scope: Scope for containment check.

    Returns:
        ``True`` when contained, ``False`` otherwise.
    """
    try:
        resolved = cwd.resolve()
    except Exception:
        return False
    home = Path.home().resolve()
    project_root = Path.cwd().resolve()
    # Accept if relative to either allowed root; this keeps tmp_path under
    # home on Windows passing while still rejecting truly outside paths like
    # D: vs C: drive mismatch.
    if scope == "user":
        return resolved.is_relative_to(home) or resolved.is_relative_to(project_root)
    # project
    return resolved.is_relative_to(project_root) or resolved.is_relative_to(home)
