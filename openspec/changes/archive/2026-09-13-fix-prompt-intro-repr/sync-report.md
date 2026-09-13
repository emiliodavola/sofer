# Sync Report — fix-prompt-intro-repr

```yaml
schema: gentle-ai.sync-result/v1
change: 2026-09-13-fix-prompt-intro-repr
status: synced
artifact_store: openspec (hybrid; engram shadow saved)
branch: fix/169-prompt-intro-repr
```

## Status

**SYNCED** — this archived change's delta spec was absorbed into the canonical spec as
follow-up sync debt. The change stays in `openspec/changes/archive/`; nothing was moved,
committed, or re-opened.

## Domains synced

| Domain | Delta file | Canonical target |
|---|---|---|
| mcp-server | `openspec/changes/archive/2026-09-13-fix-prompt-intro-repr/specs/mcp-server/spec.md` | `openspec/specs/mcp-server/spec.md` |

## Canonical files updated

- `openspec/specs/mcp-server/spec.md` — MODIFIED `MSP-R08` (full-block replacement,
  part of the +216/+3 hunk set).

## Requirements absorbed (names)

- **MODIFIED — MSP-R08** `Prompts`: full-block replacement per the delta with the
  **resolved** repr-intro contract. The two pre-existing scenarios ("Prompt list shows 3
  templates", "Confirm-before-publish idiom enforced") are byte-identical; the six #139
  injection-semantics scenarios are preserved byte-identical except the intro-limitation
  scenario, which this change rewrites into the resolved contract; four net-new scenarios
  (intro-region containment for all three templates + zero-raw-interpolation cross-template
  scan) are added. Total 11 scenarios. Provenance blockquote preserved verbatim, recording
  BOTH 09-13 amendments:
  `> Added by change \`sofer-mcp-server\` (archived 2026-08-28). Modified by
  \`2026-09-13-test-mcp-injection-semantics\` — adds the injection-semantics contract….
  Modified by \`2026-09-13-fix-prompt-intro-repr\` — resolves the #169 known-limitation
  carve-out: … (issue #169).`

## Dependency resolution (authoritative amend)

MSP-R08 is amended by BOTH `2026-09-13-test-mcp-injection-semantics` (PR #170, test-only
contract, records raw-intro as known limitation #169) and `2026-09-13-fix-prompt-intro-repr`
(PR #171, merged **after** #170, resolves #169 by repr-containing the intro `config`/`dataset`
interpolations). Per the batch rule "later deltas are authoritative; apply the amend on top",
the canonical MSP-R08 block is this change's resolved version: it retains the #139 probe
scenarios verbatim and replaces the known-limitation carve-out with the resolved contract.
The injection-semantics delta is therefore **contained** in this block (see its own
sync-report); no standalone requirement block carries the #139 slug, and its provenance is
preserved inside MSP-R08's blockquote.

## Active same-domain collisions

- **None (batch-managed).** Other 09-12/09-13 batch changes touching
  `openspec/specs/mcp-server/spec.md` were absorbed in dependency order.

## Destructive sync approvals / blockers

- No `## REMOVED Requirements`, no `## RENAMED Requirements`. The MODIFIED block
  (MSP-R08) is a scenario/prose-level upgrade whose pre-existing scenarios were verified
  byte-identical. No approval gate required.

## Validation commands / checks performed

- Byte-parity script: canonical MSP-R08 block == delta block (11701 bytes, `ALL PASS`);
  scenario inventory: only the known-limitation scenario is absent (intended replacement),
  resolved-intro scenario and all four new intro scenarios present.
- `git diff --check` → clean; LF/UTF-8 without BOM confirmed.
- Confirmed the runtime fix exists in code (`mcp_server.py:2987` uses `{config!r}`), so the
  resolved contract describes current behavior.
- No delta-section headers leaked into canonical.

## Structured status & actionContext findings

- Native status JSON (`changeName: null`) is non-authoritative for this batch; the parent
  pinned the six archived changes with explicit mappings. `actionContext.mode: repo-local`,
  `allowedEditRoots` covers the workspace; no warnings.
- `openspec/config.yaml` hybrid mode → filesystem sync performed and
  `sdd/2026-09-13-fix-prompt-intro-repr/sync-report` shadowed to Engram (type `architecture`).

## Next recommended phase

None — the change is already archived; this phase cleared the outstanding sync debt. The
parent owns committing this batch on `chore/spec-sync-archived` (no commit performed here).