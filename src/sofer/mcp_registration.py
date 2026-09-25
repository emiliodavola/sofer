"""
MCP registration automation for opencode, codex, gemini, and pi.

Provides per-agent adapters (path resolution, JSON/TOML I/O, merge,
backup, atomic write, delegation probe) and entry builders. The CLI
layer in ``sofer.cli`` orchestrates these helpers.

The supported agent set and every per-agent capability live in the single
:data:`ADAPTERS` registry: adding an agent is one entry there, and
:data:`AGENT_NAMES` (CLI ``choices`` / ``all`` expansion), path
resolution, entry building, merge/remove, native delegation and the
env-drop probe all derive from it (#235, #142).

Each agent has a distinct on-disk shape:

- opencode: ``opencode.json`` JSON ``mcp.sofer={type:"local",command:["sofer-mcp"],cwd}``
- codex: ``config.toml`` TOML ``[mcp_servers.sofer] command,cwd,env_vars``
- gemini: ``settings.json`` JSON ``mcpServers.sofer={command:"sofer-mcp",cwd,env}``
- pi: ``mcp.json`` JSON ``mcpServers.sofer={command:"sofer-mcp",cwd,env}``

All writes are idempotent, preserve unrelated keys, create a single
``.bak`` backup before the first mutation, and use an atomic
``tmp+os.replace`` commit. Codex ``env_vars`` and the ``env`` mappings of
Gemini/Pi persist env NAMES only (an allow-list of keys present in the
environment) — secret values (``HF_TOKEN``, ``SOFER_MCP_APPROVAL_PHRASE``)
are never written to disk. Codex/Gemini use a bare ``$KEY`` reference; Pi's
``pi-mcp-adapter`` only interpolates braced ``${KEY}`` references, so Pi
entries use that form. ``command`` string/array variations are normalized
before comparison. Native delegation (``codex``/``gemini``) is probed via
``shutil.which`` + ``--help`` with a timeout and falls back to file-edit;
opencode and pi always use file-edit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypedDict

from . import _toml

AgentName: TypeAlias = str
"""Registry key for one supported MCP agent — the domain of :data:`ADAPTERS`.

This is a plain ``str`` alias on purpose: :data:`ADAPTERS` is the single
source of truth for the agent set, and ``typing.Literal`` cannot be derived
from runtime data. Adding an agent means adding exactly one :data:`ADAPTERS`
entry (plus a new field only if the agent needs a shape no other agent has).
"""

Scope = Literal["user", "project"]

_ENV_KEYS: list[str] = ["HF_TOKEN", "SOFER_MCP_APPROVAL_PHRASE"]


class Adapter(TypedDict):
    """Single-source descriptor for one MCP agent.

    Every per-agent branch in this module reads this table — config path,
    entry shape, native delegation, env capability — so adding an agent is
    one entry here (#235).

    Attributes:
        fmt: Config serialization format consumed by ``cli.py`` atomic writes.
        key: Config table that holds the servers mapping.
        user_parts: Path components under ``Path.home()``, also the fallback
            when ``user_env_dir`` is set but its variable is absent.
        project_parts: Path components under the project root.
        command: ``"array"`` for ``["sofer-mcp"]``, ``"string"`` for ``"sofer-mcp"``.
        adds_type_local: Whether the entry carries ``type="local"`` (opencode).
        env: ``"none"`` (dropped), ``"allow_list"`` (``env_vars``), ``"refs"``
            (``env`` ``$KEY`` references) or ``"refs_braced"`` (``env`` ``${KEY}``
            references, Pi's interpolation form).
        delegates: Whether a native ``<agent> mcp add/remove`` is attempted.
        user_env_dir: Environment variable naming a directory that overrides
            the user-scope config directory (the file name is
            ``user_parts[-1]``); ``None`` for agents without such an override.
    """

    fmt: Literal["json", "toml"]
    key: str
    user_parts: tuple[str, ...]
    project_parts: tuple[str, ...]
    command: Literal["array", "string"]
    adds_type_local: bool
    env: Literal["none", "allow_list", "refs", "refs_braced"]
    delegates: bool
    user_env_dir: str | None


ADAPTERS: dict[AgentName, Adapter] = {
    "opencode": {
        "fmt": "json",
        "key": "mcp",
        "user_parts": (".config", "opencode", "opencode.json"),
        "project_parts": ("opencode.json",),
        "command": "array",
        "adds_type_local": True,
        "env": "none",
        "delegates": False,
        "user_env_dir": None,
    },
    "codex": {
        "fmt": "toml",
        "key": "mcp_servers",
        "user_parts": (".codex", "config.toml"),
        "project_parts": (".codex", "config.toml"),
        "command": "string",
        "adds_type_local": False,
        "env": "allow_list",
        "delegates": True,
        "user_env_dir": None,
    },
    "gemini": {
        "fmt": "json",
        "key": "mcpServers",
        "user_parts": (".config", "gemini", "settings.json"),
        "project_parts": (".gemini", "settings.json"),
        "command": "string",
        "adds_type_local": False,
        "env": "refs",
        "delegates": True,
        "user_env_dir": None,
    },
    "pi": {
        "fmt": "json",
        "key": "mcpServers",
        "user_parts": (".pi", "agent", "mcp.json"),
        "project_parts": (".pi", "mcp.json"),
        "command": "string",
        "adds_type_local": False,
        "env": "refs_braced",
        "delegates": False,
        "user_env_dir": "PI_CODING_AGENT_DIR",
    },
}

AGENT_NAMES: tuple[AgentName, ...] = tuple(ADAPTERS)
"""The supported agent set, derived from :data:`ADAPTERS` (single source)."""


def _adapter(agent: AgentName) -> Adapter:
    """Return the adapter descriptor for *agent*.

    Args:
        agent: Registry agent key.

    Returns:
        The :class:`Adapter` registered for *agent*.

    Raises:
        ValueError: When *agent* is not a registered agent.
    """
    try:
        return ADAPTERS[agent]
    except KeyError:
        raise ValueError(f"unknown agent: {agent}") from None


def _delegates(agent: AgentName) -> bool:
    """Return whether native ``mcp add/remove`` is attempted for *agent*.

    Registered agents read their ``delegates`` capability. Unregistered
    names keep the pre-#235 fall-through (attempt native) so this refactor
    changes no callable's contract.

    Args:
        agent: Registry agent key.

    Returns:
        ``True`` when native delegation should be attempted.
    """
    spec = ADAPTERS.get(agent)
    return spec["delegates"] if spec is not None else True


def resolve_config_path(
    agent: AgentName,
    scope: Scope,
    cwd: Path | None = None,
) -> Path:
    """Resolve the config file path for *agent* and *scope*.

    User scope resolves under ``Path.home()`` (Windows-aware via
    ``Path.home()``), unless the adapter declares a ``user_env_dir`` whose
    environment variable is set to a non-empty value — then the directory
    it names replaces the home prefix and the file name is
    ``user_parts[-1]`` (Pi's ``$PI_CODING_AGENT_DIR/mcp.json``). Project
    scope resolves under *cwd* (or ``Path.cwd()`` when ``None``).

    Args:
        agent: Target agent name.
        scope: ``"user"`` or ``"project"``.
        cwd: Project directory anchor for ``project`` scope; ignored
            for ``user`` scope.

    Returns:
        Absolute path to the agent's config file.
    """
    spec = _adapter(agent)
    if scope == "user":
        env_dir = spec["user_env_dir"]
        override = os.environ.get(env_dir) if env_dir else None
        if override:
            return Path(override).joinpath(spec["user_parts"][-1])
        return Path.home().joinpath(*spec["user_parts"])
    base = Path(cwd).resolve() if cwd is not None else Path.cwd().resolve()
    return base.joinpath(*spec["project_parts"])


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
    # toml (parser resolved once in `sofer._toml`, #192)
    with open(path, "rb") as fh:
        data = _toml.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"config {path} is not a TOML table")
    return data, fmt


def build_entry(agent: AgentName, cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    """Build the desired ``sofer`` entry for *agent*.

    Env forwarding rules:
    - codex: ``env_vars`` is the allow-list of known keys present in *env*
    - gemini: ``env`` is a mapping of known key -> ``$KEY`` reference (Gemini
      CLI expands host environment variables at runtime, so the secret values
      are never persisted to settings.json)
    - pi: ``env`` is a mapping of known key -> ``${KEY}`` reference — Pi's
      ``pi-mcp-adapter`` only interpolates the braced form, so the bare
      ``$KEY`` used by Gemini would be persisted literally
    - opencode: no env forwarding (returns minimal entry); the entry stays
      env-less and the selection-time warning when env would be dropped is
      the CLI's responsibility

    Args:
        agent: Target agent.
        cwd: Absolute, resolved working directory for the server.
        env: Mapping of env keys to values (typically filtered
            ``os.environ``).

    Returns:
        Entry dict ready to merge into the agent's config.
    """
    spec = _adapter(agent)
    cwd_str = str(cwd.resolve())
    entry: dict[str, Any] = {}
    if spec["adds_type_local"]:
        entry["type"] = "local"
    entry["command"] = ["sofer-mcp"] if spec["command"] == "array" else "sofer-mcp"
    entry["cwd"] = cwd_str
    if spec["env"] == "allow_list":
        entry["env_vars"] = _present_env_keys(env)
    elif spec["env"] == "refs":
        entry["env"] = {k: f"${k}" for k in _present_env_keys(env)}
    elif spec["env"] == "refs_braced":
        entry["env"] = {k: f"${{{k}}}" for k in _present_env_keys(env)}
    return entry


def _normalize_command(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def _entries_equal(agent: AgentName, a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Return True when *a* and *b* are the same entry for *agent*.

    The comparison follows the adapter's ``env`` capability, so it stays
    single-sourced: the ``allow_list`` agents (codex) normalize command
    string/array variations and compare sorted ``env_vars``; the ``refs`` /
    ``refs_braced`` agents (gemini, pi) compare raw command, ``cwd`` and the
    ``env`` mapping; the ``none`` agents (opencode) compare full structural
    equality. Unregistered names also fall back to full equality.
    """
    spec = ADAPTERS.get(agent)
    env_kind = spec["env"] if spec is not None else None
    if env_kind == "allow_list":
        if _normalize_command(a.get("command")) != _normalize_command(b.get("command")):
            return False
        if a.get("cwd") != b.get("cwd"):
            return False
        return sorted(a.get("env_vars", [])) == sorted(b.get("env_vars", []))
    if env_kind in ("refs", "refs_braced"):
        if a.get("command") != b.get("command"):
            return False
        if a.get("cwd") != b.get("cwd"):
            return False
        return a.get("env") == b.get("env")
    # opencode (env "none") and unregistered names: full structural equality.
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
    key = _adapter(agent)["key"]
    current_table = new_doc.get(key)
    servers = dict(current_table) if isinstance(current_table, dict) else {}
    current = servers.get("sofer")
    if isinstance(current, dict) and _entries_equal(agent, current, desired):
        return new_doc, False
    servers["sofer"] = desired
    new_doc[key] = servers
    return new_doc, True


def remove_entry(agent: AgentName, existing: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Remove ``sofer`` entry idempotently.

    Args:
        agent: Target agent.
        existing: Parsed config document.

    Returns:
        ``(new_doc, changed)``.
    """
    new_doc = dict(existing)
    key = _adapter(agent)["key"]
    servers = new_doc.get(key)
    if not isinstance(servers, dict) or "sofer" not in servers:
        return new_doc, False
    new_servers = dict(servers)
    new_servers.pop("sofer", None)
    if new_servers:
        new_doc[key] = new_servers
    else:
        new_doc.pop(key, None)
    return new_doc, True


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

    opencode and pi always return ``False`` (file-edit only). For
    codex/gemini, checks ``shutil.which`` and runs ``<agent> mcp --help``
    with a timeout. Whether an agent delegates comes from :data:`ADAPTERS`.

    Args:
        agent: Agent to probe.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` when delegation should be attempted.
    """
    if not _delegates(agent):
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

    Only agents whose adapter declares ``delegates=True`` are delegated;
    the rest (opencode, pi) return ``False``. A single native shape is used —
    ``<agent> mcp add sofer --command sofer-mcp --cwd <cwd>`` — and a
    non-zero exit falls back to the caller's file edit (no shape retry).

    Args:
        agent: Target agent.
        cwd: Resolved cwd for the server.
        env_keys: Env keys to forward (unused for native path but kept
            for signature parity).

    Returns:
        ``True`` on success, ``False`` on failure or absence (caller
        should fallback to file-edit).
    """
    if not _delegates(agent):
        return False
    exe = shutil.which(agent)
    if not exe:
        return False
    cmd = [exe, "mcp", "add", "sofer", "--command", "sofer-mcp", "--cwd", str(cwd)]
    try:
        result = subprocess.run(cmd, timeout=3.0, capture_output=True)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def delegate_remove(agent: AgentName) -> bool:
    """Attempt native ``remove`` delegation for *agent*.

    Only agents whose adapter declares ``delegates=True`` are delegated;
    the rest (opencode, pi) return ``False``.

    Args:
        agent: Target agent.

    Returns:
        ``True`` on success, ``False`` otherwise.
    """
    if not _delegates(agent):
        return False
    exe = shutil.which(agent)
    if not exe:
        return False
    try:
        result = subprocess.run([exe, "mcp", "remove", "sofer"], timeout=3.0, capture_output=True)
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


def _present_env_keys(env: Mapping[str, str]) -> list[str]:
    """Known env keys from ``_ENV_KEYS`` present (non-empty) in *env*.

    Single source for which of ``HF_TOKEN`` / ``SOFER_MCP_APPROVAL_PHRASE``
    are set in the environment. NAMES only — values are never returned.

    Args:
        env: Environment mapping to query (typically ``collect_env()``
            output or ``os.environ``). Keys only, never values.

    Returns:
        Allow-list of known keys present with non-empty values, in
        ``_ENV_KEYS`` order. Values are never returned.
    """
    return [k for k in _ENV_KEYS if env.get(k)]


def dropped_env_keys(agent: AgentName, env: Mapping[str, str]) -> list[str]:
    """Known env NAMES that would be dropped for *agent*.

    Agents whose adapter declares ``env="none"`` cannot carry env, so every
    present known key is dropped; agents that forward names (``env_vars``
    allow-list / ``env`` ``$KEY`` refs) drop nothing. Reads *env* keys only;
    returns NAMES never values. Returns ``[]`` (not ``None``) when nothing
    is dropped.

    Args:
        agent: Target agent name.
        env: Environment mapping to query. Keys only, never values.

    Returns:
        Names of known env keys that would be dropped for *agent*, in
        ``_ENV_KEYS`` order; ``[]`` (never ``None``) when nothing is dropped.
    """
    spec = ADAPTERS.get(agent)
    if spec is not None and spec["env"] == "none":
        return _present_env_keys(env)
    return []


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
