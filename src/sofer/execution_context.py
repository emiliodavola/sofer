"""
Execution context for dataset identity.

Single home (AGENTS.md rule 4) for the shared identity contract consumed by
both adapters — the MCP ``sofer_init`` tool and the CLI ``init`` command:

- :func:`validate_identity` rejects unsafe, blank, or placeholder identities
  before any write (INIT-05 / CLI-R07);
- :func:`resolve_dataset_root` enforces the fail-closed ``cwd`` policy
  (INIT-02): the dataset root must be a strict descendant of the server root
  when no explicit ``cwd`` is given, and an explicit ``cwd`` must stay inside
  the server root;
- :class:`DatasetIdentity` and :func:`report_identity` produce the canonical,
  absolute ``config_path`` / ``dataset_root`` reported by the CLI print and
  the MCP envelope + ``output_schema`` (INIT-03 / MSP-R03).

Keeping the contract here keeps both adapters thin and identical. Imports stay
stdlib-only plus ``model._PLACEHOLDERS``: the direction
``execution_context -> model -> config`` is acyclic, and nothing from
``mcp_server`` is imported — its ``PathOutsideRootError`` remains the
boundary exception for string-``cwd`` escapes (D5).
"""

from __future__ import annotations

import ntpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

from .model import _PLACEHOLDERS

#: ``user`` SHALL match ``^[\w\-]+$`` (INIT-05): letters, digits, and
#: underscore (``\w``) plus explicit hyphens. The end anchor is ``\Z`` (end
#: of string), NOT ``$`` — in Python ``$`` matches before a trailing ``\n``,
#: so a ``user="alice\n"`` would otherwise pass; the ``\Z`` anchor plus the
#: control-character check below reject it.
_USER_RE = re.compile(r"^[\w\-]+\Z")

#: Control characters banned from ``name`` / ``user`` (INIT-05) — covers
#: ``\n``, ``\t``, ``\r`` and the rest of ``[\x00-\x1f]`` plus DEL (``\x7f``).
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


class IdentityResolutionError(Exception):
    """Raised when the dataset root cannot be resolved safely (D4).

    :func:`resolve_dataset_root` raises it for containment violations (an
    explicit ``cwd`` escaping the server root) and for the fail-closed
    ``cwd=None`` case where the live working directory is not a strict
    descendant of the server root — the message then names the required
    ``cwd`` argument with actionable guidance. The MCP adapter maps it to an
    envelope refusal (``CONFIG_ERROR``); the CLI never raises it (no bound).

    Defined here rather than in ``model.py`` so the import direction
    ``execution_context -> model -> config`` stays acyclic.
    """


@dataclass(frozen=True)
class DatasetIdentity:
    """A validated dataset identity.

    Attributes:
        name: Dataset name — a single path component (see
            :func:`validate_identity`).
        user: Hugging Face user or organization — a single component.
        dataset_root: Absolute, resolved directory the dataset lives in.
    """

    name: str
    user: str
    dataset_root: Path

    @property
    def config_path(self) -> Path:
        """Absolute path of the dataset TOML: ``dataset_root / f"{name}.toml"``.

        Derived, never stored — the invariant
        ``config_path == dataset_root / name.toml`` is unbreakable by
        construction (D2).
        """
        return self.dataset_root / f"{self.name}.toml"

    @classmethod
    def from_parts(cls, name: str, user: str, dataset_root: Path) -> DatasetIdentity:
        """Build an identity from already-validated parts (D2).

        Callers MUST run :func:`validate_identity` first; this constructor
        only normalizes (``dataset_root.resolve()``) and never re-validates.

        Args:
            name: Dataset name.
            user: Hugging Face user or organization.
            dataset_root: Directory the dataset lives in.

        Returns:
            A frozen :class:`DatasetIdentity` with an absolute, resolved
            ``dataset_root``.
        """
        return cls(name=name, user=user, dataset_root=dataset_root.resolve())


def _is_non_empty(value: str | None) -> TypeGuard[str]:
    """Type guard: True when *value* is a non-blank string.

    ``None`` and whitespace-only strings count as empty (INIT-05 treats
    ``None``/``""``/``"   "`` alike).
    """
    return value is not None and bool(value.strip())


def _is_single_component(name: str) -> bool:
    """True when *name* is a safe single path component (INIT-05).

    Rejects separators (``/``, ``\\``), drive/UNC prefixes via
    ``ntpath.splitdrive``, exact ``.`` / ``..``, quotes, control characters,
    and leading/trailing whitespace. Nested traversal such as ``a/../b`` is
    already covered by the separator rule.
    """
    if name != name.strip():
        return False
    if _CONTROL_CHARS_RE.search(name):
        return False
    if "/" in name or "\\" in name:
        return False
    if ntpath.splitdrive(name)[0]:
        return False
    if name in (".", ".."):
        return False
    if '"' in name or "'" in name:
        return False
    return True


def validate_identity(name: str | None, user: str | None) -> list[str]:
    """Validate a ``(name, user)`` identity pair, returning error strings.

    Returns a list of human-readable error messages (empty = valid); it never
    raises. The FIRST error for a missing/blank ``name`` is exactly
    ``"name must be non-empty"`` so existing MCP envelope tests that grep for
    ``"non-empty"`` keep passing (INIT-05, D3).

    Matrix:
        - both ``name`` and ``user`` are mandatory and non-empty
          (``None`` / ``""`` / whitespace-only are rejected);
        - ``name`` must be a single component (see
          :func:`_is_single_component`);
        - ``user`` must match ``^[\\w\\-]+$`` (end-anchored, so a trailing
          newline fails), must not contain control characters, and must not
          be a normalized ``model._PLACEHOLDERS`` value (``YOUR_USER``,
          ``your-username``, ...). The placeholder ban applies to ``user``
          only.

    Args:
        name: Dataset name, or ``None``.
        user: Hugging Face user or organization, or ``None``.

    Returns:
        A list of error messages; empty when the identity is valid.
    """
    errors: list[str] = []

    if not _is_non_empty(name):
        errors.append("name must be non-empty")
    elif not _is_single_component(name):
        errors.append(
            "name must be a single path component without separators, "
            f"drives, quotes, or control characters, got '{name}'"
        )

    if not _is_non_empty(user):
        errors.append("user must be non-empty")
    else:
        if _CONTROL_CHARS_RE.search(user):
            errors.append(f"user must not contain control characters, got '{user}'")
        elif not _USER_RE.match(user):
            errors.append(f"user must match ^[\\w\\-]+$, got '{user}'")
        elif user.strip().lower() in _PLACEHOLDERS:
            errors.append(
                f"user must not be a placeholder ('{user}'); use your Hugging Face username"
            )

    return errors


def resolve_dataset_root(
    cwd: str | Path | None,
    *,
    live_cwd: Path,
    server_root: Path | None = None,
) -> Path:
    """Resolve the dataset root directory from a ``cwd`` argument (D5).

    Three modes:

    (a) ``server_root=None`` — the CLI no-bound mode. Returns
        ``live_cwd.resolve()``; ``cwd`` MUST be ``None`` here.

    (b) ``cwd`` given — inline containment: expand ``~``, absolutize against
        ``server_root``, resolve, then require ``is_relative_to``. Escapes
        raise :class:`IdentityResolutionError`. (The MCP adapter keeps its own
        ``_contained_path`` for this mode so escapes surface as
        ``PathOutsideRootError`` per INIT-02 — this branch is exercised by
        the unit matrix only, S7.)

    (c) ``cwd=None`` with ``server_root`` — fail-closed strict descendant:
        ``live_cwd`` must satisfy ``live != root AND live.is_relative_to(root)``.
        Otherwise an :class:`IdentityResolutionError` names the required
        ``cwd`` argument with actionable guidance; the server root is NEVER
        silently selected.

    Args:
        cwd: Explicit working directory, or ``None``.
        live_cwd: The live process working directory (caller resolves it).
        server_root: MCP server root; ``None`` means no bound (CLI).

    Returns:
        The resolved dataset root directory.

    Raises:
        IdentityResolutionError: When the requested root escapes the bound,
            when ``cwd`` is given without a bound, or when ``cwd`` is
            required but missing.
    """
    if server_root is None:
        if cwd is not None:
            raise IdentityResolutionError(
                "cwd is not supported without a server root; pass cwd=None"
            )
        return live_cwd.resolve()

    root = server_root.resolve()

    if cwd is not None:
        expanded = Path(str(cwd)).expanduser()
        candidate = expanded if expanded.is_absolute() else root / expanded
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise IdentityResolutionError(
                f"cwd '{cwd}' escapes the server root '{root}'; pass a directory inside it"
            )
        return resolved

    live = live_cwd.resolve()
    if live == root or not live.is_relative_to(root):
        raise IdentityResolutionError(
            f"cwd is required: the live working directory '{live}' is not a "
            f"strict descendant of the server root '{root}'. "
            'pass cwd="<dataset dir>" to select the dataset directory'
        )
    return live


def report_identity(identity: DatasetIdentity) -> dict[str, str]:
    """Report the canonical identity as absolute strings (INIT-03 / PB-03).

    Args:
        identity: A :class:`DatasetIdentity`.

    Returns:
        ``{"config_path": str(identity.config_path), "dataset_root": str(identity.dataset_root)}``
        — both absolute.
    """
    return {
        "config_path": str(identity.config_path),
        "dataset_root": str(identity.dataset_root),
    }
