"""Typed workflow metadata and result envelopes shared by adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

PHASE_BOOTSTRAP = "bootstrap"
PHASE_BUILD = "build"
PHASE_PUBLISH = "publish"
PHASE_TRIAGE = "triage"

# Argument placeholder used by registry templates that need the canonical
# dataset TOML path to become executable (MSP-R13 binding contract).
_CONFIG_PATH_ARG = "config"
_CONFIG_PATH_MARKER = "<config_path>"


@dataclass(frozen=True)
class WorkflowCall:
    """Describe an executable continuation or recovery operation.

    Parameters
    ----------
    tool : str or None
        Exact adapter tool or command name. ``None`` means that a human input
        is required before any tool can be called.
    arguments : Mapping[str, Any]
        Arguments that can be passed to *tool* without inferred state.
    reason : str, default=""
        Human-readable explanation for the continuation.
    input_required : tuple of str, default=()
        Human values required before this continuation becomes executable.
    """

    tool: str | None
    arguments: Mapping[str, Any]
    reason: str = ""
    input_required: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze nested argument mappings and sequences at construction."""
        object.__setattr__(self, "arguments", _freeze_argument(self.arguments))

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable copy of this executable call.

        Returns
        -------
        dict of str and object
            JSON-compatible tool name, arguments, reason, and any required
            human inputs.
        """
        result = {
            "tool": self.tool,
            "arguments": _thaw_argument(self.arguments),
            "reason": self.reason,
        }
        if self.input_required:
            result["input_required"] = list(self.input_required)
        return result


@dataclass(frozen=True)
class WorkflowTemplate:
    """Describe a registry continuation before request values are bound.

    Parameters
    ----------
    tool : str
        Registered adapter name.
    arguments : Mapping[str, Any]
        Argument template. ``<config_path>`` is bound per request.
    reason : str, default=""
        Human-readable explanation for the continuation.
    """

    tool: str
    arguments: Mapping[str, Any]
    reason: str = ""

    def __post_init__(self) -> None:
        """Freeze template arguments so registry metadata cannot drift."""
        object.__setattr__(self, "arguments", _freeze_argument(self.arguments))

    def to_dict(self) -> dict[str, Any]:
        """Return the unbound registry template.

        Returns
        -------
        dict of str and object
            JSON-compatible template fields with ``<config_path>`` intact.
        """
        return {
            "tool": self.tool,
            "arguments": _thaw_argument(self.arguments),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class HumanGate:
    """Represent a deliberate non-tool workflow handoff.

    Parameters
    ----------
    name : str
        Human-readable gate name.
    reason : str, default=""
        Action the human must take before the workflow can continue.
    """

    name: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the explicit human-gate envelope.

        Returns
        -------
        dict of str
            Non-tool gate kind, name, and human action.
        """
        return {"kind": "human_gate", "name": self.name, "reason": self.reason}


@dataclass(frozen=True)
class WorkflowMetadata:
    """Describe a tool's phase, branch, preconditions, and continuation.

    Parameters
    ----------
    tool : str
        Registered tool name.
    phase : str
        Canonical workflow phase.
    requires : tuple of str
        Preconditions exposed to clients.
    branch : str
        Workflow branch selected by the adapter.
    next : WorkflowTemplate, HumanGate, or None, default=None
        Registry continuation or deliberate human handoff.
    """

    tool: str
    phase: str
    requires: tuple[str, ...]
    branch: str
    next: WorkflowTemplate | HumanGate | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return metadata in the MCP/CLI contract shape.

        Returns
        -------
        dict of str and object
            Registry metadata with a serializable continuation or gate.
        """
        return {
            "tool": self.tool,
            "phase": self.phase,
            "requires": list(self.requires),
            "branch": self.branch,
            "next": self.next.to_dict() if self.next is not None else {},
        }


@dataclass(frozen=True)
class WorkflowResult:
    """Represent one workflow result without retaining request state.

    Parameters
    ----------
    ok : bool
        Whether the operation completed successfully.
    exit_code : int
        CLI-compatible result code.
    output : str
        Captured human-readable output.
    phase : str
        Workflow phase that produced the result.
    requires : tuple[str, ...]
        Preconditions relevant to this result.
    next : WorkflowCall or None, default=None
        Executable continuation, if one exists.
    config_path : str or None, default=None
        Canonical dataset TOML path when configured.
    dataset_root : str or None, default=None
        Effective dataset directory when known.
    error_code : str or None, default=None
        Stable machine-readable refusal code.
    message : str, default=""
        Human-readable error or status message.
    config_errors : tuple[str, ...], default=()
        Configuration validation failures.
    """

    ok: bool
    exit_code: int
    output: str
    phase: str
    requires: tuple[str, ...] = ()
    next: WorkflowCall | HumanGate | None = None
    config_path: str | None = None
    dataset_root: str | None = None
    error_code: str | None = None
    message: str = ""
    config_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return the stable machine-readable result envelope.

        Returns
        -------
        dict of str and object
            Complete result fields, including status, context, diagnostics,
            and serialized continuation data.
        """
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "output": self.output,
            "phase": self.phase,
            "requires": list(self.requires),
            "next": self.next.to_dict() if self.next is not None else {},
            "config_path": self.config_path,
            "dataset_root": self.dataset_root,
            "error_code": self.error_code,
            "message": self.message,
            "config_errors": list(self.config_errors),
        }


def _freeze_argument(value: Any) -> Any:
    """Recursively convert workflow arguments to immutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_argument(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_argument(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_argument(item) for item in value)
    return value


def _thaw_argument(value: Any) -> Any:
    """Convert immutable workflow arguments into JSON-compatible containers."""
    if isinstance(value, Mapping):
        return {key: _thaw_argument(item) for key, item in value.items()}
    if isinstance(value, (tuple, frozenset)):
        return [_thaw_argument(item) for item in value]
    return value


def bind_continuation(template: WorkflowTemplate, config_path: str | None = None) -> WorkflowCall:
    """Bind a registry template to a concrete request, degrading to input-required.

    A template argument of ``<config_path>`` needs the canonical dataset TOML
    path to become executable. When the request carries no config, the
    continuation SHALL still be emitted — as the same tool with
    ``input_required`` naming ``config`` — so the caller can say exactly what
    input is missing (MSP-R13) instead of dropping the continuation.

    Args:
        template: The registry continuation to bind.
        config_path: Canonical dataset TOML path, or ``None``.

    Returns:
        An executable :class:`WorkflowCall`. When *config_path* is missing and
        the template depends on it, the call carries ``input_required=("config",)``
        with no arguments.
    """
    call = _template_to_call(template, config_path)
    if call is not None:
        return call
    if _CONFIG_PATH_MARKER in template.arguments.values():
        return WorkflowCall(
            template.tool,
            {},
            reason=template.reason,
            input_required=(_CONFIG_PATH_ARG,),
        )
    return WorkflowCall(template.tool, {}, reason=template.reason)


def _template_to_call(template: WorkflowTemplate, config_path: str | None) -> WorkflowCall | None:
    """Bind a registry template to a concrete request identity."""
    arguments: dict[str, Any] = {}
    for key, value in template.arguments.items():
        if value == "<config_path>":
            if config_path is None:
                return None
            arguments[key] = config_path
        else:
            arguments[key] = value
    return WorkflowCall(template.tool, arguments, template.reason)


_WORKFLOW_METADATA = {
    "sofer_init": WorkflowMetadata(
        "sofer_init",
        PHASE_BOOTSTRAP,
        ("valid name", "valid user"),
        "greenfield",
        WorkflowTemplate("sofer_scan_dry_run", {"config": "<config_path>"}),
    ),
    "sofer_scan_dry_run": WorkflowMetadata(
        "sofer_scan_dry_run",
        PHASE_BOOTSTRAP,
        ("canonical config_path",),
        "greenfield",
        WorkflowTemplate("sofer_scan_apply", {"config": "<config_path>"}),
    ),
    "sofer_scan_apply": WorkflowMetadata(
        "sofer_scan_apply",
        PHASE_BOOTSTRAP,
        ("successful scan dry-run",),
        "greenfield",
        WorkflowTemplate("sofer_validate", {"config": "<config_path>"}),
    ),
    "sofer_validate": WorkflowMetadata(
        "sofer_validate",
        PHASE_BUILD,
        ("canonical config_path",),
        "existing_config",
        WorkflowTemplate("sofer_prepare", {"config": "<config_path>"}),
    ),
    "sofer_codebook": WorkflowMetadata(
        "sofer_codebook", PHASE_TRIAGE, ("explicit data path",), "triage"
    ),
    "sofer_profile": WorkflowMetadata(
        "sofer_profile",
        PHASE_TRIAGE,
        ("explicit data path",),
        "triage",
        None,
    ),
    "sofer_render": WorkflowMetadata(
        "sofer_render",
        PHASE_TRIAGE,
        ("explicit metadata path",),
        "triage",
        None,
    ),
    "sofer_prepare": WorkflowMetadata(
        "sofer_prepare",
        PHASE_BUILD,
        ("valid configuration",),
        "existing_config",
        WorkflowTemplate("sofer_codebook_all", {"config": "<config_path>"}),
    ),
    "sofer_codebook_all": WorkflowMetadata(
        "sofer_codebook_all",
        PHASE_BUILD,
        ("prepared dataset",),
        "existing_config",
        WorkflowTemplate("sofer_profile_all", {"config": "<config_path>"}),
    ),
    "sofer_profile_all": WorkflowMetadata(
        "sofer_profile_all",
        PHASE_BUILD,
        ("prepared dataset",),
        "existing_config",
        WorkflowTemplate("sofer_render_all", {"config": "<config_path>"}),
    ),
    "sofer_render_all": WorkflowMetadata(
        "sofer_render_all",
        PHASE_BUILD,
        ("profiles available",),
        "existing_config",
        WorkflowTemplate("sofer_auth_status", {"config": "<config_path>"}),
    ),
    "sofer_auth_status": WorkflowMetadata(
        "sofer_auth_status",
        PHASE_PUBLISH,
        ("prepared package",),
        "delivery",
        WorkflowTemplate("sofer_publish", {"config": "<config_path>", "dry_run": True}),
    ),
    "sofer_publish": WorkflowMetadata(
        "sofer_publish",
        PHASE_PUBLISH,
        ("auth_status passed",),
        "delivery",
        HumanGate(
            "STOP human approval",
            "Present the dry-run plan and obtain explicit human approval before publish_confirm.",
        ),
    ),
    "sofer_publish_confirm": WorkflowMetadata(
        "sofer_publish_confirm", PHASE_PUBLISH, ("human approval",), "delivery"
    ),
}
WORKFLOW_METADATA: Mapping[str, WorkflowMetadata] = MappingProxyType(_WORKFLOW_METADATA)

WORKFLOW_BRANCHES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "greenfield": (
            "sofer_init",
            "sofer_scan_dry_run",
            "sofer_scan_apply",
            "sofer_validate",
        ),
        "existing_config": (
            "sofer_validate",
            "sofer_prepare",
            "sofer_codebook_all",
            "sofer_profile_all",
            "sofer_render_all",
        ),
        "triage": ("sofer_codebook", "sofer_profile", "sofer_render"),
        "delivery": (
            "sofer_auth_status",
            "sofer_publish(dry_run=true)",
            "STOP human approval",
            "sofer_publish_confirm",
        ),
    }
)


def workflow_branch_lines() -> tuple[str, ...]:
    """Return canonical branch descriptions for runtime surfaces.

    Returns
    -------
    tuple of str
        Branch descriptions in the order presented to CLI and MCP users.
    """
    return (
        "Phase 0 Bootstrap [conditional: REQUIRED if greenfield - no TOML / empty [[file]]]: "
        + " -> ".join(WORKFLOW_BRANCHES["greenfield"]),
        "Phase 1 Build (existing configuration): "
        + " -> ".join(WORKFLOW_BRANCHES["existing_config"]),
        "Config-free triage: " + " -> ".join(WORKFLOW_BRANCHES["triage"]),
        "Phase 2 Publish: " + " -> ".join(WORKFLOW_BRANCHES["delivery"]),
    )


def metadata_for(tool: str) -> WorkflowMetadata:
    """Return the registered metadata for *tool*.

    Parameters
    ----------
    tool : str
        Registered workflow tool name.

    Returns
    -------
    WorkflowMetadata
        Immutable metadata contract.

    Raises
    ------
    KeyError
        If *tool* is not part of the canonical roster.
    """
    return WORKFLOW_METADATA[tool]


def select_workflow_branch(
    config_path: str | None,
    *,
    config_exists: bool,
    file_count: int | None = None,
    triage: bool = False,
) -> str:
    """Select the canonical branch from explicit request facts.

    Parameters
    ----------
    config_path : str or None
        Explicit TOML identity, when the operation is configuration-based.
    config_exists : bool
        Whether the explicit configuration exists on disk.
    file_count : int or None, default=None
        Number of registered ``[[file]]`` entries when the configuration was
        loaded.  Zero entries still require the greenfield bootstrap branch.
    triage : bool, default=False
        Whether the request is a config-free single-file operation.

    Returns
    -------
    str
        One of ``"greenfield"``, ``"existing_config"``, or ``"triage"``.
    """
    if triage:
        return "triage"
    if config_path is None or not config_exists or not file_count:
        return "greenfield"
    return "existing_config"


def success_result(
    *,
    phase: str,
    output: str,
    next_call: WorkflowCall | HumanGate | None = None,
    requires: tuple[str, ...] = (),
    config_path: str | None = None,
    dataset_root: str | None = None,
) -> WorkflowResult:
    """Create a successful workflow result with a zero exit code.

    Parameters
    ----------
    phase : str
        Workflow phase that produced the result.
    output : str
        Human-readable operation output.
    next_call : WorkflowCall or HumanGate or None, default=None
        Executable continuation or deliberate human handoff.
    requires : tuple of str, default=()
        Preconditions relevant to the result.
    config_path : str or None, default=None
        Canonical dataset TOML path.
    dataset_root : str or None, default=None
        Effective dataset directory.

    Returns
    -------
    WorkflowResult
        Successful result with ``ok=True`` and ``exit_code=0``.
    """
    return WorkflowResult(
        ok=True,
        exit_code=0,
        output=output,
        phase=phase,
        requires=requires,
        next=next_call,
        config_path=config_path,
        dataset_root=dataset_root,
    )


def failure_result(
    *,
    phase: str,
    error_code: str,
    message: str,
    requires: tuple[str, ...] = (),
    next_call: WorkflowCall | HumanGate | None = None,
    config_errors: tuple[str, ...] = (),
    config_path: str | None = None,
    dataset_root: str | None = None,
) -> WorkflowResult:
    """Create a failed workflow result with a non-zero exit code.

    Parameters
    ----------
    phase : str
        Workflow phase that produced the refusal.
    error_code : str
        Stable machine-readable error code.
    message : str
        Human-readable refusal message.
    requires : tuple of str, default=()
        Preconditions relevant to the result.
    next_call : WorkflowCall or HumanGate or None, default=None
        Executable recovery or deliberate human handoff.
    config_errors : tuple of str, default=()
        Configuration diagnostics included in the result.
    config_path : str or None, default=None
        Canonical dataset TOML path when known.
    dataset_root : str or None, default=None
        Effective dataset directory when known.

    Returns
    -------
    WorkflowResult
        Failed result with ``ok=False`` and ``exit_code=1``.
    """
    return WorkflowResult(
        ok=False,
        exit_code=1,
        output="",
        phase=phase,
        requires=requires,
        next=next_call,
        config_path=config_path,
        dataset_root=dataset_root,
        error_code=error_code,
        message=message,
        config_errors=config_errors,
    )
