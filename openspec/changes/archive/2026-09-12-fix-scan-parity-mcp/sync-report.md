# Sync Report — fix-scan-parity-mcp

```yaml
schema: gentle-ai.sync-result/v1
change: 2026-09-12-fix-scan-parity-mcp
status: synced
artifact_store: openspec (hybrid; engram shadow saved)
branch: fix/152-154-scan-parity
```

## Status

**SYNCED** — this archived change's delta spec was absorbed into the canonical spec as
follow-up sync debt. The change stays in `openspec/changes/archive/`; nothing was moved,
committed, or re-opened.

## Domains synced

| Domain | Delta file | Canonical target |
|---|---|---|
| mcp-server | `openspec/changes/archive/2026-09-12-fix-scan-parity-mcp/specs/mcp-server/spec.md` | `openspec/specs/mcp-server/spec.md` |

## Canonical files updated

- `openspec/specs/mcp-server/spec.md` — MODIFIED `MSP-R06`, ADDED `MSP-R14`, `MSP-R15`
  (part of the +216/+3 hunk set).

## Requirements absorbed (names)

- **MODIFIED — MSP-R06** `Scan non-interactivity`: full-block replacement per the delta —
  the pre-existing scenario **"Apply never blocks on input"** is byte-identical; the contract
  line now also specifies the `move_loose=True` Phase-1 MOVE chain (`discover_files(exclude
  raw/) → check_raw_collisions → move_to_raw → discover_files → …`, MOVE before COPY);
  added scenario **"Apply with move_loose chains the MOVE phase (unchanged scenarios
  preserved)"**. Provenance blockquote extended, verbatim from the delta:
  `> Added by change \`sofer-mcp-server\` (archived 2026-08-28); modified by \`fix-scan-parity-mcp\`.`
- **ADDED — MSP-R14** `Scan extensions filter`: `extensions: list[str] | None` on both scan
  tools, unsupported-suffix refusal, case-insensitive dot-optional matching (3 scenarios).
- **ADDED — MSP-R15** `Scan Phase-1 move opt-in`: `move_loose: bool = False` opt-in safety,
  atomic collision abort, `moved: int` in the envelope, dry-run preview semantics
  (3 scenarios).

## Active same-domain collisions

- **None (batch-managed).** The other three batch changes targeting
  `openspec/specs/mcp-server/spec.md` (residual-parity, prompt-intro-repr,
  injection-semantics) are archived and were absorbed in the same batch in dependency order;
  MSP-R14/R15 are appended before residual-parity's MSP-R16/R17 (requirement-ID order,
  matching the deltas' own dependency note).

## Destructive sync approvals / blockers

- No `## REMOVED Requirements`, no `## RENAMED Requirements`. The single MODIFIED block
  (MSP-R06) is additive within a full-block replacement whose pre-existing scenario was
  verified byte-identical. No approval gate required.

## Validation commands / checks performed

- Byte-parity script: canonical MSP-R06, MSP-R14, MSP-R15 blocks == delta blocks
  (`ALL PASS`).
- `git diff --check` → clean; LF/UTF-8 without BOM confirmed.
- Counts: mcp-server scenarios grew by the batch's additive scenarios; MSP-R06 scenario
  "Apply never blocks on input" present exactly once (1 occurrence check passed).
- No delta-section headers leaked into canonical.

## Structured status & actionContext findings

- Native status JSON (`changeName: null`) is non-authoritative for this batch; the parent
  pinned the six archived changes with explicit mappings. `actionContext.mode: repo-local`,
  `allowedEditRoots` covers the workspace; no warnings.
- `openspec/config.yaml` hybrid mode → filesystem sync performed and
  `sdd/2026-09-12-fix-scan-parity-mcp/sync-report` shadowed to Engram (type `architecture`).

## Next recommended phase

None — the change is already archived; this phase cleared the outstanding sync debt. The
parent owns committing this batch on `chore/spec-sync-archived` (no commit performed here).