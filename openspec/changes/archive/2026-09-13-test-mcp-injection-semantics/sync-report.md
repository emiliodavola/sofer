# Sync Report — test-mcp-injection-semantics

```yaml
schema: gentle-ai.sync-result/v1
change: 2026-09-13-test-mcp-injection-semantics
status: synced
artifact_store: openspec (hybrid; engram shadow saved)
branch: test/139-mcp-injection-semantics
```

## Status

**SYNCED (contained)** — this archived change's delta spec was absorbed into the canonical
spec as follow-up sync debt. Its content lands in canonical **via the later authoritative
amendment** (`2026-09-13-fix-prompt-intro-repr`, PR #171, merged after PR #170), not as a
standalone requirement block. The change stays in `openspec/changes/archive/`; nothing was
moved, committed, or re-opened.

## Domains synced

| Domain | Delta file | Canonical target |
|---|---|---|
| mcp-server | `openspec/changes/archive/2026-09-13-test-mcp-injection-semantics/specs/mcp-server/spec.md` | `openspec/specs/mcp-server/spec.md` |

## Canonical files updated

- `openspec/specs/mcp-server/spec.md` — MODIFIED `MSP-R08` (absorbed through the
  fix-prompt-intro-repr amendment; no separate hunk carries this change's slug).

## Requirements absorbed (names)

- **MODIFIED — MSP-R08** `Prompts` — **content absorbed via later amend.** The delta's
  injection-semantics contract and its probe suite are fully contained in the canonical
  MSP-R08 block as absorbed by `2026-09-13-fix-prompt-intro-repr`:
  - pre-existing scenarios byte-identical (2);
  - the six #139 probe scenarios (`Hostile payload cannot alter the
    prepare_dataset/assess_dataset/finalize_and_publish workflow`, `Canonical chain order is
    payload-invariant`, + the intro scope-guard) preserved verbatim, **except** the scenario
    "Intro raw interpolation is a recorded known limitation, not asserted", which the later
    change (PR #171) rewrote into the resolved contract per the batch amend rule (later
    delta authoritative);
  - the delta's provenance is preserved inside MSP-R08's blockquote: "Modified by
    \`2026-09-13-test-mcp-injection-semantics\` — adds the injection-semantics contract and
    its probe suite (test-only; no runtime change)".

No new requirement ID was introduced by this change; the absorb is tracked here and in the
fix-prompt-intro-repr sync-report for full provenance.

## Active same-domain collisions

- **None (batch-managed).** The four 09-12/09-13 mcp-server deltas were absorbed in
  dependency order (scan-parity → residual-parity appends; injection-semantics → prompt-intro
  repr as the MSP-R08 amend chain).

## Destructive sync approvals / blockers

- No `## REMOVED Requirements`, no `## RENAMED Requirements`. The known-limitation scenario
  replacement is the documented, intended resolution of issue #169 by the later change —
  not a destructive REMOVED. No approval gate required.

## Validation commands / checks performed

- Byte-parity script: canonical MSP-R08 == fix-prompt-intro-repr delta
  (11701 bytes, `ALL PASS`); scenario-level check confirmed the ONLY injection-semantics
  scenario absent from canonical is the replaced known-limitation scenario; the remaining six
  are present verbatim.
- `git diff --check` → clean; LF/UTF-8 without BOM confirmed.
- No delta-section headers leaked into canonical.

## Structured status & actionContext findings

- Native status JSON (`changeName: null`) is non-authoritative for this batch; the parent
  pinned the six archived changes with explicit mappings. `actionContext.mode: repo-local`,
  `allowedEditRoots` covers the workspace; no warnings.
- `openspec/config.yaml` hybrid mode → filesystem sync performed and
  `sdd/2026-09-13-test-mcp-injection-semantics/sync-report` shadowed to Engram
  (type `architecture`).

## Next recommended phase

None — the change is already archived; this phase cleared the outstanding sync debt. The
parent owns committing this batch on `chore/spec-sync-archived` (no commit performed here).