"""Registry-integrity tests for the canonical workflow (MSP-R13, #117).

These tests validate ``sofer.workflow``'s single authoritative registry:
every canonical tool has exactly one entry, every continuation names a tool
that exists, the branch chains match #117, and the envelope types serialize
to stable JSON (CLI-R10 foundation).
"""

from __future__ import annotations

import json

from sofer import workflow
from sofer.workflow import (
    HumanGate,
    WorkflowCall,
    WorkflowMetadata,
    WorkflowTemplate,
    _template_to_call,
    bind_continuation,
    failure_result,
    metadata_for,
    select_workflow_branch,
    success_result,
)

# The canonical roster from #117 / the server's registered sofer_* tools.
CANONICAL_TOOLS = (
    "sofer_init",
    "sofer_scan_dry_run",
    "sofer_scan_apply",
    "sofer_validate",
    "sofer_prepare",
    "sofer_codebook_all",
    "sofer_profile_all",
    "sofer_render_all",
    "sofer_codebook",
    "sofer_profile",
    "sofer_render",
    "sofer_auth_status",
    "sofer_publish",
    "sofer_publish_confirm",
)


def test_every_canonical_tool_has_exactly_one_registry_entry():
    for tool in CANONICAL_TOOLS:
        entry = metadata_for(tool)
        assert isinstance(entry, WorkflowMetadata)
        assert entry.tool == tool


def test_registry_keys_match_canonical_roster():
    assert set(workflow.WORKFLOW_METADATA) == set(CANONICAL_TOOLS)


def test_every_branch_tool_is_registered():
    for branch, tools in workflow.WORKFLOW_BRANCHES.items():
        for tool in tools:
            clean = tool.split("(")[0].strip()
            if clean.startswith("STOP") or clean == "sofer_publish":
                continue  # branch labels are informational; real checks below
            assert clean in workflow.WORKFLOW_METADATA, f"{tool} not registered"


def test_every_template_continuation_names_a_registered_tool():
    for entry in workflow.WORKFLOW_METADATA.values():
        nxt = entry.next
        if isinstance(nxt, WorkflowTemplate):
            assert nxt.tool in workflow.WORKFLOW_METADATA, nxt.tool
            assert nxt.arguments, "continuation without arguments is not executable"


def test_greenfield_branch_chain():
    assert workflow.WORKFLOW_BRANCHES["greenfield"] == (
        "sofer_init",
        "sofer_scan_dry_run",
        "sofer_scan_apply",
        "sofer_validate",
    )
    assert metadata_for("sofer_init").next.tool == "sofer_scan_dry_run"  # type: ignore[union-attr]
    assert metadata_for("sofer_scan_dry_run").next.tool == "sofer_scan_apply"  # type: ignore[union-attr]
    assert metadata_for("sofer_scan_apply").next.tool == "sofer_validate"  # type: ignore[union-attr]


def test_existing_config_branch_routes_render_all_to_auth_status():
    assert workflow.WORKFLOW_BRANCHES["existing_config"] == (
        "sofer_validate",
        "sofer_prepare",
        "sofer_codebook_all",
        "sofer_profile_all",
        "sofer_render_all",
    )
    # Acceptance criterion: render_all points to auth_status before publish dry-run.
    assert metadata_for("sofer_render_all").next.tool == "sofer_auth_status"  # type: ignore[union-attr]


def test_delivery_branch_gate_is_typed_human_gate_before_confirm():
    assert metadata_for("sofer_auth_status").next.tool == "sofer_publish"  # type: ignore[union-attr]
    publish_next = metadata_for("sofer_publish").next
    assert isinstance(publish_next, HumanGate), "publish must end in a human gate"
    assert publish_next.name == "STOP human approval"
    # publish_confirm is reachable only after the gate; its registry entry has no
    # tool continuation.
    assert metadata_for("sofer_publish_confirm").next is None


def test_triage_never_advertises_config_bearing_publish():
    for tool in ("sofer_codebook", "sofer_profile", "sofer_render"):
        entry = metadata_for(tool)
        assert entry.branch == "triage"
        nxt = entry.next
        if isinstance(nxt, WorkflowTemplate):
            assert nxt.tool != "sofer_publish"


def test_select_workflow_branch():
    assert select_workflow_branch(None, config_exists=False) == "greenfield"
    assert select_workflow_branch("x.toml", config_exists=False) == "greenfield"
    assert select_workflow_branch("x.toml", config_exists=True, file_count=0) == "greenfield"
    assert select_workflow_branch("x.toml", config_exists=True, file_count=2) == "existing_config"
    assert select_workflow_branch(None, config_exists=False, triage=True) == "triage"


def test_template_binding_degrades_to_input_required():
    template = WorkflowTemplate("sofer_scan_dry_run", {"config": "<config_path>"})
    assert _template_to_call(template, None) is None
    call = _template_to_call(template, "/abs/dataset.toml")
    assert isinstance(call, WorkflowCall)
    assert call.tool == "sofer_scan_dry_run"
    assert call.arguments == {"config": "/abs/dataset.toml"}


def test_bind_continuation_degrades_to_input_required():
    template = WorkflowTemplate("sofer_scan_dry_run", {"config": "<config_path>"})
    bound = bind_continuation(template)
    assert bound.tool == "sofer_scan_dry_run"
    assert bound.arguments == {}
    assert bound.input_required == ("config",)
    bound2 = bind_continuation(template, "/abs/x.toml")
    assert bound2.arguments == {"config": "/abs/x.toml"}
    assert bound2.input_required == ()


def test_bind_continuation_without_marker_keeps_arguments():
    template = WorkflowTemplate("sofer_codebook", {"file": "x.csv"})
    bound = bind_continuation(template)
    assert bound.arguments == {"file": "x.csv"}
    assert bound.input_required == ()


def test_result_envelopes_are_stable_json():
    ok = success_result(
        phase=workflow.PHASE_PUBLISH,
        output="pc",
        next_call=WorkflowCall("sofer_publish", {"config": "x.toml", "dry_run": True}),
        config_path="x.toml",
    )
    json.dumps(ok.to_dict())  # must not raise
    assert ok.to_dict()["ok"] is True
    assert ok.to_dict()["exit_code"] == 0
    assert ok.to_dict()["next"]["tool"] == "sofer_publish"

    err = failure_result(
        phase=workflow.PHASE_BUILD,
        error_code="CONFIG_ERROR",
        message="csv_delimiter must be a single-character string",
        config_errors=("csv_delimiter must be a single-character string",),
        next_call=None,
    )
    payload = json.dumps(err.to_dict())
    assert '"error_code": "CONFIG_ERROR"' in payload
    decoded = json.loads(payload)
    assert decoded["ok"] is False
    assert decoded["exit_code"] == 1
    assert decoded["config_errors"] == list(err.config_errors)
    assert decoded["next"] == {}


def test_workflow_branch_lines_carry_the_four_branches():
    lines = workflow.workflow_branch_lines()
    assert len(lines) == 4
    assert "Greenfield" in lines[0] or "greenfield" in lines[0]
    assert any("publish" in line.lower() for line in lines)
