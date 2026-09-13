# Sync Note — 2026-09-11-fix-auth-status-hints

**Phase:** sdd-sync (canonical merge), executed 2026-09-11 on `fix/144-auth-status-hints`.
**Status:** synced — canonical spec updated; change remains active (NOT archived).
**Artifact store:** openspec. Repo convention has no `sync-report.md` (0 exist); this note is the
handoff for the archive phase, which MUST fold the material below into `archive-report.md`
under its `## Spec Sync` section (precedent: `2026-09-09-feat-mcp-init-tool/archive-report.md`).

## Spec Sync (canonical merge — DONE, do NOT re-apply)

- **`openspec/specs/mcp-server/spec.md` — ADDED `### Requirement: Approval-phrase configuration diagnostics (APX-01)`** with all 4 scenarios, inserted immediately after requirement `Auth status preflight read-only (10.8)` (canonical line 434, between 10.8 and `Bootstrap Phase 0 conditional canonical`).
- Provenance line added on merge (repo convention — verified against 40+ existing lines in `openspec/specs/`):
  `> Added by change \`2026-09-11-fix-auth-status-hints\` (archived 2026-09-11).`
  If the actual archive date differs from 2026-09-11, amend this date during archive.
- Placement rationale: the primary surface is `sofer_auth_status`'s `hints` (the 10.8 envelope) and the
  secondary surface is the `PUBLISH_APPROVAL_NOT_CONFIGURED` refusal message (MSP-R05, untouched). Grouping
  APX-01 next to 10.8 keeps the auth-status contract contiguous and composes cleanly with the #145 sibling
  delta (10.8 posture fields, `2026-09-11-fix-auth-status-diagnostics` → future `fix-auth-status-posture`),
  which lands later in the same neighborhood. The native helper's ADD would have appended at the end of the
  Requirements section (after MSP-R13); manual placement by judgment was mandated by the sync phase — do not
  re-run `applyDeltaSpec` to "verify".
- Declared transforms applied on merge (nothing else changed):
  1. Delta's `*Introduced by change ... (issue #144).*` italic line → canonical provenance blockquote.
  2. Delta's `*Tests:*` / backtick / `(extended)` test-pointer runs (13 lines) dropped — canonical format
     carries no test pointers (0 occurrences repo-wide); traceability lives in this delta + `verify-report.md`.
  3. Zero edits to existing canonical content; no other requirement touched (10.8 body left for #145).
- Idempotency (verified against the real `lib/openspec-deltas.ts`): re-applying this delta to the canonical
  now **throws** `Cannot add existing canonical requirement "Approval-phrase configuration diagnostics (APX-01)"`
  — a re-application can never silently duplicate. **Archive phase: do NOT re-apply the ADD; the sync is done.**

## Verification performed (exact)

```text
node (native helper parse + re-apply):
  canonical blocks: 24 | unique names: 24 | duplicates: 0
  APX-01 blocks in canonical: 1 | APX-01 scenarios: 4 | provenance present: true | test scaffolding: none
  RE-APPLY throws: Cannot add existing canonical requirement "Approval-phrase configuration diagnostics (APX-01)"
  delta ops -> added: 1, modified: 0, removed: 0
  fidelity: canonical APX-01 block byte-equal to delta block modulo the 3 declared transforms (56 lines compared)
git diff --check          -> clean (no whitespace errors)
git diff --stat canonical -> openspec/specs/mcp-server/spec.md | 59 insertions(+), 0 deletions
counts: requirement headers 23 -> 24; scenario headers 81 -> 85; APX-01 occurrences == 1; tabs == 0; LF-only
delta file untouched: openspec/changes/2026-09-11-fix-auth-status-hints/specs/mcp-server/spec.md byte-identical
posture symbols (phrase_source/server_process_id/server_started_at/server_version): 0 in canonical post-merge
  (issue #145 isolation honored — APX-01 adds no posture field)
```

## For the archive phase

1. Include a `## Spec Sync` section in the future `archive-report.md` citing the canonical merge above
   (the ADD is already absorbed — mirror the wording of `feat-mcp-init-tool`'s "already absorbed" precedent).
2. Do not run `applyDeltaSpec` against this delta on the canonical (it throws — expected, not an error).
3. The delta `specs/mcp-server/spec.md` is intentionally left byte-identical for the archival record.