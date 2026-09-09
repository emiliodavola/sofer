# Proposal — fix-mcp-workflow-registry

**Issue**: GitHub #117 (child of epic #115)
**Date**: 2026-09-09
**Status**: proposed

## Problem

The MCP server exposes several competing workflow representations: the
`_PHASED_INSTRUCTIONS` server instructions block, tool docstrings, prompts,
CLI status strings, and ad-hoc `next` hints embedded in every runtime
envelope. There is no authoritative registry: `tools/list` learns about tools
from docstrings, envelopes build their `next` hints locally per tool, and
some continuations carry placeholders (`<from human>`), unsupported
arguments, or skip the `sofer_auth_status` preflight before publish
dry-runs. Wrap-around is untestable at the contract level: nothing proves
that a continuation names a tool that exists with arguments the tool accepts.

## Expected behaviour (from #117)

One authoritative workflow registry used by `tools/list`, tool descriptions,
output schemas, prompts, and runtime envelopes. Canonical branches:

```text
Greenfield:        sofer_init → sofer_scan_dry_run → sofer_scan_apply → sofer_validate
Existing config:   sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile_all → sofer_render_all
Single-file triage: sofer_codebook / sofer_profile / sofer_render
Delivery:          sofer_auth_status → sofer_publish(dry_run=true) → HUMAN APPROVAL STOP → sofer_publish_confirm
```

A continuation is executable only when its tool exists and every required
argument is present. A human approval stop is a typed human gate, not a fake
tool call. When a required human value is unknowable, the response says input
is required instead of fabricating credentials or emitting a
guaranteed-failing call.

## Approach

1. **Port the typed workflow layer from the preserved reference work**
   (`c4dab7f:src/sofer/workflow.py`, 551 lines frozen as evidence): the
   `WorkflowCall` / `WorkflowTemplate` / `HumanGate` / `WorkflowMetadata` /
   `WorkflowResult` envelope types are exactly the contract #117 needs.
   Rebase them onto today's source (post-#138: scan dry-run, auth_status,
   containment) instead of copying slice-1 integration blindly.
2. **Build one registry** keyed by tool name with phase, branch, requires,
   and next/gate metadata; mark every registered tool with exactly one entry.
3. **Generate from the registry**: `tools/list` descriptions surface the
   phase/branch/next metadata; runtime envelopes build their `next` from the
   registry (executable: real tool name + real arguments or an explicit
   `input_required` list); prompts and instructions read the same source.
4. **Executable recovery tests**: run a **registered FastMCP client** that
   actually calls the returned `next` tool with the returned arguments —
   signature binding alone is insufficient.
5. **CLI parity**: machine-readable status as stable JSON (not Python repr).

## Out of scope

- Path containment / symlink / credential persistence (#121 follow-ups)
- Scan transactionality and dry-run semantics (#120)
- Build/cache/publish artifact manifest (#122)
- New `sofer_build` tool
- `SOFER_TRACE.md`

## Key decisions

- **Reuse the reference `workflow.py` types verbatim where stable**, per
  AGENTS.md rule 4 (no duplicated logic); the reference carries its own
  change SDD (`fix-mcp-end-to-end-reliability`) that is NOT being revived —
  only the leaf workflow module is ported and integrated.
- **`sofer_render` triage never advertises a config-bearing publish call**;
  **`sofer_render_all` points to `sofer_auth_status` before publish
  dry-run** (acceptance criteria).
- **Recovery metadata is structured and truthful**: missing config / invalid
  config / invalid output / missing identity each carry `error_code`,
  `message`, and an executable-or-input-required `next`.