# Sync Report — fix-residual-parity

```yaml
schema: gentle-ai.sync-result/v1
change: 2026-09-12-fix-residual-parity
status: synced
artifact_store: openspec (hybrid; engram shadow saved)
branch: fix/153-155-residual-parity
```

## Status

**SYNCED** — this archived change's delta specs were absorbed into the canonical specs as
follow-up sync debt. The change stays in `openspec/changes/archive/`; nothing was moved,
committed, or re-opened.

## Domains synced

| Domain | Delta file | Canonical target |
|---|---|---|
| codebook | `openspec/changes/archive/2026-09-12-fix-residual-parity/specs/codebook/spec.md` | `openspec/specs/codebook/spec.md` |
| mcp-server | `openspec/changes/archive/2026-09-12-fix-residual-parity/specs/mcp-server/spec.md` | `openspec/specs/mcp-server/spec.md` |

## Canonical files updated

- `openspec/specs/codebook/spec.md` — ADDED `CB-R10` (+37 lines).
- `openspec/specs/mcp-server/spec.md` — ADDED `MSP-R16`, `MSP-R17` (part of the +216/+3 hunk set).

## Requirements absorbed (names)

- **ADDED — CB-R10** `generate_all max_sample threading`: appended after CB-R09 with the
  delta's own provenance (`> Added by change \`fix-residual-parity\` (closes #155).`) and both
  scenarios (override caps per-file analysis; omitted resolves to config default at call time).
- **ADDED — MSP-R16** `Publish cleanup`: `clean`/`clean_cache` forwarded to `publish.publish`,
  `CLEAN_CACHE_WITHOUT_CLEAN` refusal, never-delete-on-dry-run (3 scenarios).
- **ADDED — MSP-R17** `Batch codebook max_sample`: `sofer_codebook_all(max_sample=…)` with
  call-time config resolution (2 scenarios).

## Ordering note (append position)

The mcp-server appends are placed **in requirement-ID order** — MSP-R14/R15 (scan-parity)
before MSP-R16/R17 — matching the deltas' own dependency note ("Requirement IDs continue from
the active fix-scan-parity-mcp change (MSP-R14/R15)") and the true merge order (PR #164 then
PR #165). Appending is additive; no existing requirement was disturbed.

## Active same-domain collisions

- **None.** The four other batch changes targeting `openspec/specs/mcp-server/spec.md`
  (scan-parity, prompt-intro-repr, injection-semantics) are all archived and were absorbed in
  this same batch in dependency order; the batch applies ADD/MODIFY without conflict.

## Destructive sync approvals / blockers

- No `## REMOVED Requirements`, no `## RENAMED Requirements`, no MODIFIED blocks in this
  change — pure ADD. No approval gate required.

## Validation commands / checks performed

- Byte-parity script: canonical CB-R10, MSP-R16, MSP-R17 blocks == delta blocks (`ALL PASS`).
- `git diff --check` → clean; LF/UTF-8 without BOM confirmed.
- Counts: codebook requirements 8→9 (scenarios 31→33); mcp-server requirements 24→28
  (scenarios 92→113 across the whole four-delta batch). No delta-section headers leaked.

## Structured status & actionContext findings

- Native status JSON (`changeName: null`) is non-authoritative for this batch; the parent
  pinned the six archived changes with explicit mappings. `actionContext.mode: repo-local`,
  `allowedEditRoots` covers the workspace; no warnings.
- `openspec/config.yaml` hybrid mode → filesystem sync performed and
  `sdd/2026-09-12-fix-residual-parity/sync-report` shadowed to Engram (type `architecture`).

## Next recommended phase

None — the change is already archived; this phase cleared the outstanding sync debt. The
parent owns committing this batch on `chore/spec-sync-archived` (no commit performed here).