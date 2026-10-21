"""Per-session init admission for the MCP dispatch gate (issue #360).

The MCP server admits exactly one dataset context per live protocol session:
before that session called ``sofer_init`` successfully, every protected tool
and every data-bearing resource read is refused. This module owns the state
machine, the refusal vocabulary, and the tool classification. It never touches
the filesystem, the MCP framework, or dataset contents: the caller resolves
paths and builds envelopes, keeping the policy testable on its own.

Lifecycle (issue #360 D4)::

    U --admitted init--> I --non-dry-run success--> R(A)
    I --dry run/failure/cancel--> U
    R(A) --admitted init--> I --success--> R(B)
    R(A) --mismatched request--> R(A)   (refused, unchanged)

The state object is stored on a framework-owned object that lives exactly as
long as one client session (see ``mcp_server._session_admission``); it is never
persisted, never keyed by a client-supplied identifier, and never shared
between sessions.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from . import workflow

#: The single tool permitted while a session is uninitialized.
INIT_TOOL = "sofer_init"

#: Configuration-based tools: after init they must target the active config.
CONFIG_TOOLS: frozenset[str] = frozenset(
    {
        "sofer_validate",
        "sofer_meta_check",
        "sofer_meta_set",
        "sofer_file_set",
        "sofer_prepare",
        "sofer_publish",
        "sofer_publish_confirm",
        "sofer_codebook_all",
        "sofer_profile_all",
        "sofer_render_all",
        "sofer_auth_status",
        "sofer_repo_settings",
        "sofer_scan_dry_run",
        "sofer_scan_apply",
    }
)

#: Standalone path-based tools: bound only by the active root, never by a TOML.
STANDALONE_TOOLS: frozenset[str] = frozenset({"sofer_codebook", "sofer_profile", "sofer_render"})

#: Failure reporting is protected too: no diagnostic-tool exemption (D1).
REPORT_TOOL = "sofer_report_failure"

ToolPolicy = Literal["init", "config", "standalone", "report", "protected"]

#: Admission-state sentinels. ``U`` and ``I`` are deliberately short: the
#: tables in issue #360 use them and the refusal messages name them in prose.
UNINITIALIZED = "U"
INITIALIZING = "I"
READY = "R"

ERROR_INIT_REQUIRED = "INITIALIZATION_REQUIRED"
ERROR_INIT_IN_PROGRESS = "INITIALIZATION_IN_PROGRESS"
ERROR_INIT_CONTEXT_BUSY = "INITIALIZATION_CONTEXT_BUSY"
ERROR_INIT_CONTEXT_MISMATCH = "INITIALIZATION_CONTEXT_MISMATCH"
ERROR_INIT_SESSION_UNAVAILABLE = "INITIALIZATION_SESSION_UNAVAILABLE"


def classify_tool(name: str) -> ToolPolicy:
    """Return the admission policy for a registered tool name.

    Unknown and future tools default to ``"protected"`` (D2/D5): a tool that
    nobody classified still requires a ready session, so adding a tool can
    never silently bypass the gate.

    Args:
        name: The tool name from the ``tools/call`` request.

    Returns:
        ``"init"``, ``"config"``, ``"standalone"``, ``"report"``, or
        ``"protected"``.
    """
    if name == INIT_TOOL:
        return "init"
    if name in CONFIG_TOOLS:
        return "config"
    if name in STANDALONE_TOOLS:
        return "standalone"
    if name == REPORT_TOOL:
        return "report"
    return "protected"


@dataclass(frozen=True)
class AdmissionContext:
    """The one dataset context a ready session is bound to.

    Attributes:
        root: Canonical effective containment root ``R``.
        config: Canonical dataset TOML path ``C``.
    """

    root: Path
    config: Path

    def matches_root(self, other: Path) -> bool:
        """Return whether *other* is the same canonical root as ``R``."""
        return _same_path(self.root, other)

    def matches_config(self, other: Path) -> bool:
        """Return whether *other* is the same canonical config as ``C``."""
        return _same_path(self.config, other)


@dataclass(frozen=True)
class AdmissionRefusal:
    """A machine-readable admission refusal, pre-envelope.

    The dispatch layer turns this into the common ``ok:false`` envelope; this
    module never builds the transport representation (D6).

    Attributes:
        error_code: One of the ``ERROR_INIT_*`` constants.
        message: Human-readable explanation naming the recovery.
        next_call: The executable ``next`` continuation, or ``{}`` when none
            can be inferred safely.
        next_hint: Flat ``hints`` payload; empty for admission refusals.
    """

    error_code: str
    message: str
    next_call: dict[str, Any] = field(default_factory=dict)
    next_hint: dict[str, Any] = field(default_factory=dict)


def _same_path(left: Path, right: Path) -> bool:
    """Compare two paths after canonical resolution (symlink- and case-safe)."""
    return left.resolve() == right.resolve()


def _arguments_with_root(arguments: dict[str, Any], root: Path | None) -> dict[str, Any]:
    """Copy *arguments* and add the explicit ``root`` when one was supplied."""
    result = dict(arguments)
    if root is not None:
        result["root"] = str(root)
    return result


def required_refusal(
    *,
    arguments: dict[str, Any],
    call_root: Path | None,
    config_argument: str | None,
) -> AdmissionRefusal:
    """Build ``INITIALIZATION_REQUIRED`` with an attach-or-create continuation.

    When the refused request already names a config path (or an explicit
    root), the continuation is an executable attach with those values;
    otherwise it asks the caller for the config input while explaining the
    create alternative (D6).
    """
    if config_argument is not None and config_argument.strip():
        next_call = workflow.WorkflowCall(
            INIT_TOOL,
            _arguments_with_root({"config": config_argument}, call_root),
            reason=(
                "No dataset context is initialized for this session. Attach the "
                "existing configuration, or create one with name/user/cwd."
            ),
        ).to_dict()
    elif call_root is not None:
        next_call = workflow.WorkflowCall(
            INIT_TOOL,
            _arguments_with_root({}, call_root),
            reason=(
                "No dataset context is initialized for this session. Pass config "
                "to attach an existing configuration, or pass name/user/cwd to create one."
            ),
            input_required=("config",),
        ).to_dict()
    else:
        next_call = workflow.WorkflowCall(
            INIT_TOOL,
            {},
            reason=(
                "No dataset context is initialized for this session. Pass config "
                "to attach an existing configuration, or pass name/user/cwd to create one."
            ),
            input_required=("config",),
        ).to_dict()
    return AdmissionRefusal(
        ERROR_INIT_REQUIRED,
        (
            "INITIALIZATION_REQUIRED: call sofer_init before any other tool. "
            "Pass config=<dataset TOML> to attach an existing dataset, or "
            "name=<dataset name>, user=<hf user>, cwd=<dataset dir> to create one."
        ),
        next_call,
    )


def in_progress_refusal() -> AdmissionRefusal:
    """Build ``INITIALIZATION_IN_PROGRESS``: an init is already running."""
    return AdmissionRefusal(
        ERROR_INIT_IN_PROGRESS,
        (
            "INITIALIZATION_IN_PROGRESS: sofer_init is still running in this "
            "session. Wait for its result, then retry the rejected request "
            "explicitly; do not start a second init."
        ),
    )


def context_busy_refusal(init_arguments: dict[str, Any]) -> AdmissionRefusal:
    """Build ``INITIALIZATION_CONTEXT_BUSY``: admitted work is still running."""
    return AdmissionRefusal(
        ERROR_INIT_CONTEXT_BUSY,
        (
            "INITIALIZATION_CONTEXT_BUSY: another admitted request is still "
            "executing in this session. Wait for it to finish, then retry this "
            "init; the active context is unchanged."
        ),
        workflow.WorkflowCall(
            INIT_TOOL,
            init_arguments,
            reason="Retry this init after the executing request finishes.",
        ).to_dict(),
    )


def context_mismatch_refusal(
    *,
    active: AdmissionContext,
    requested_root: Path | None,
    requested_config: Path | None,
) -> AdmissionRefusal:
    """Build ``INITIALIZATION_CONTEXT_MISMATCH`` for another dataset target."""
    if requested_config is not None:
        target: dict[str, Any] = {"config": str(requested_config)}
        if requested_root is not None:
            target["root"] = str(requested_root)
        next_call = workflow.WorkflowCall(
            INIT_TOOL,
            target,
            reason="Initialize the requested dataset explicitly; the active one is unchanged.",
        ).to_dict()
    elif requested_root is not None:
        next_call = workflow.WorkflowCall(
            INIT_TOOL,
            {"root": str(requested_root)},
            reason="Initialize the requested root explicitly; the active one is unchanged.",
            input_required=("config",),
        ).to_dict()
    else:
        next_call = {}
    return AdmissionRefusal(
        ERROR_INIT_CONTEXT_MISMATCH,
        (
            "INITIALIZATION_CONTEXT_MISMATCH: this session is initialized for "
            f"config={active.config} root={active.root}. Call sofer_init for the "
            "requested target; do not substitute the active one."
        ),
        next_call,
    )


def session_unavailable_refusal() -> AdmissionRefusal:
    """Build ``INITIALIZATION_SESSION_UNAVAILABLE`` when no session identity exists."""
    return AdmissionRefusal(
        ERROR_INIT_SESSION_UNAVAILABLE,
        (
            "INITIALIZATION_SESSION_UNAVAILABLE: this transport exposes no live "
            "server-owned session, so init admission cannot be tracked. Use a "
            "session-based transport (stdio) and retry."
        ),
    )


class SessionAdmission:
    """Atomic per-session admission state machine.

    Every transition runs under one lock, so concurrent requests on the same
    session observe exactly one outcome (D4). The object is created once per
    live session and discarded with it.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: str = UNINITIALIZED
        self._context: AdmissionContext | None = None
        self._active: int = 0

    @property
    def state(self) -> str:
        """Return the current state sentinel (``U``, ``I`` or ``R``)."""
        with self._lock:
            return self._state

    @property
    def context(self) -> AdmissionContext | None:
        """Return the active context, or ``None`` when the session is not ready."""
        with self._lock:
            return self._context

    @property
    def active(self) -> int:
        """Return the count of admitted requests whose work has not finished."""
        with self._lock:
            return self._active

    def claim_init(self, init_arguments: dict[str, Any]) -> AdmissionRefusal | None:
        """Admit an init request, discarding any previous context first.

        Args:
            init_arguments: The request arguments, echoed by a busy refusal.

        Returns:
            ``None`` when admitted (state becomes ``I``), otherwise the refusal
            that leaves the session unchanged.
        """
        with self._lock:
            if self._state == INITIALIZING:
                return in_progress_refusal()
            if self._state == READY and self._active > 0:
                return context_busy_refusal(init_arguments)
            # D4: discard A BEFORE root/argument validation.
            self._state = INITIALIZING
            self._context = None
            self._active = 1
            return None

    def claim_protected(
        self,
        *,
        requested_root: Path | None,
        requested_config: Path | None,
        requires_config: bool,
        arguments: dict[str, Any],
        config_argument: str | None,
        hint_root: Path | None = None,
    ) -> AdmissionRefusal | None:
        """Admit a protected request against the active context.

        A ``None`` target means the caller could not resolve that argument
        (for example an invalid path spelling): the request is admitted so the
        handler keeps its existing validation error, and no context switch can
        happen because the handler fails before domain work (D5).

        Args:
            requested_root: The resolved per-call root, or ``None`` when it
                could not be resolved or was omitted.
            requested_config: The resolved config path, or ``None``.
            requires_config: Whether the tool is configuration-based.
            arguments: The original request arguments, echoed by the
                ``INITIALIZATION_REQUIRED`` continuation.
            config_argument: The raw ``config`` argument, or ``None``.
            hint_root: The explicitly supplied root, or ``None`` when the caller
                omitted it (an omitted root must not appear in the suggested
                attach arguments).

        Returns:
            ``None`` when admitted, otherwise the refusal.
        """
        with self._lock:
            if self._state == UNINITIALIZED:
                return required_refusal(
                    arguments=arguments,
                    call_root=hint_root,
                    config_argument=config_argument,
                )
            if self._state == INITIALIZING:
                return in_progress_refusal()
            active = self._context
            if active is None:
                return in_progress_refusal()
            if requested_root is not None and not active.matches_root(requested_root):
                return context_mismatch_refusal(
                    active=active,
                    requested_root=requested_root,
                    requested_config=requested_config,
                )
            if (
                requires_config
                and requested_config is not None
                and not active.matches_config(requested_config)
            ):
                return context_mismatch_refusal(
                    active=active,
                    requested_root=requested_root,
                    requested_config=requested_config,
                )
            self._active += 1
            return None

    def settle_init(self, context: AdmissionContext | None) -> None:
        """Publish init's outcome and release the init lease.

        Args:
            context: The context to publish when a non-dry-run init completed
                successfully, or ``None`` for a preview, refusal, exception, or
                cancellation. ``None`` settles in ``U`` and never restores the
                discarded context.
        """
        with self._lock:
            self._active = 0
            if context is None:
                self._state = UNINITIALIZED
                self._context = None
                return
            self._state = READY
            self._context = context

    def release(self) -> None:
        """Release one admitted non-init request's lease."""
        with self._lock:
            if self._active > 0:
                self._active -= 1
