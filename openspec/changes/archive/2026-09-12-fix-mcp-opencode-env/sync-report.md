# Sync Report — fix-mcp-opencode-env

```yaml
schema: gentle-ai.sync-result/v1
change: 2026-09-12-fix-mcp-opencode-env
status: synced
artifact_store: openspec (hybrid; engram shadow saved)
branch: fix/147-opencode-env-warning
```

## Status

**SYNCED** — this archived change's delta specs were absorbed into the canonical specs
as follow-up sync debt (its archive-report recorded the absorb as outstanding). The change
stays in `openspec/changes/archive/`; nothing was moved, committed, or re-opened.

## Domains synced

| Domain | Delta file | Canonical target |
|---|---|---|
| cli | `openspec/changes/archive/2026-09-12-fix-mcp-opencode-env/specs/cli/spec.md` | `openspec/specs/cli/spec.md` |
| mcp-registration | `openspec/changes/archive/2026-09-12-fix-mcp-opencode-env/specs/mcp-registration/spec.md` | `openspec/specs/mcp-registration/spec.md` |

## Canonical files updated

- `openspec/specs/cli/spec.md` — MODIFIED `CLI-R09` (11 added lines, 0 removed).
- `openspec/specs/mcp-registration/spec.md` — ADDED `MCP-REG-03` (+71 lines).

## Requirements absorbed (names)

- **MODIFIED — CLI-R09** `mcp add/remove help`: full-block replacement per the delta —
  the four pre-existing scenarios are byte-identical; added the env-forwarding prose
  paragraph, the `(Previously: …)` note, and the new scenario **"add help documents env
  forwarding"**. Provenance blockquote extended to two lines, verbatim from the delta:
  `> Added by change \`feat-mcp-registration-automation\` (archived 2026-09-09).` /
  `> Extended by change \`2026-09-12-fix-mcp-opencode-env\` (additive env-forwarding scenario).`
- **ADDED — MCP-REG-03** `OpenCode env-drop warning`: appended after MCP-REG-02 with the
  delta's own provenance (`> Added by change \`2026-09-12-fix-mcp-opencode-env\` (closes #147).`)
  and all 5 scenarios (env-set warning, dry-run preview, all-member once-only, no-env/no-forward
  silence, values-never-leak). The delta's `<!-- Informational -->` test-mapping table was NOT
  copied (it is not part of the requirement block).

## Active same-domain collisions

- **None.** No active change touches `openspec/specs/cli/spec.md` or
  `openspec/specs/mcp-registration/spec.md`. Native status `collisions: []`,
  `sameDomainActiveChanges: []`.

## Destructive sync approvals / blockers

- No `## REMOVED Requirements`, no `## RENAMED Requirements`. The only MODIFIED block
  (CLI-R09) is additive scenario/prose-only within a full-block replacement whose
  pre-existing scenarios were verified byte-identical. No approval gate required.

## Validation commands / checks performed

- Byte-parity script: canonical CLI-R09 block == delta CLI-R09 block (1837 bytes);
  canonical MCP-REG-03 block == delta MCP-REG-03 block. `ALL PASS`.
- `git diff --check` → clean (exit 0); LF/UTF-8 without BOM confirmed via `file`.
- Counts: cli requirements 9→10, scenarios 43→45; mcp-registration requirements 2→3,
  scenarios 16→21. No delta-section headers (`## MODIFIED/ADDED Requirements`, `# Spec delta`)
  leaked into canonical.
- `git status` — only the four intended canonical spec files modified (plus this report).

## Structured status & actionContext findings

- Native status JSON: `changeName: null`, `nextRecommended: "No active SDD changes found."` —
  non-authoritative for this batch task; the parent prompt pinned the six archived changes
  with an explicit delta→canonical mapping, which this phase executed.
- `actionContext.mode: repo-local`; `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` —
  all synced paths inside the workspace root. No warnings to act on.
- `openspec/config.yaml` mode: **hybrid (openspec + engram)** → filesystem sync performed and
  `sdd/2026-09-12-fix-mcp-opencode-env/sync-report` shadowed to Engram (type `architecture`).

## Next recommended phase

None — the change is already archived; this phase cleared the outstanding sync debt. The
parent owns committing this batch on `chore/spec-sync-archived` (no commit performed here).