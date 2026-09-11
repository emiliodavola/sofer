# Sync Note — 2026-09-11-fix-auth-status-posture

**Phase:** sdd-sync (canonical merge), executed 2026-09-11 on `fix/145-auth-status-posture`.
**Status:** synced — canonical spec updated; change remains active (NOT archived).
**Artifact store:** openspec. Repo convention has no `sync-report.md` (0 exist); this note is the
handoff for the archive phase, which MUST fold the material below into `archive-report.md` under its
`## Spec Sync` section (precedent: `2026-09-11-fix-auth-status-hints/sync-note.md`,
`2026-09-09-feat-mcp-init-tool/archive-report.md`).

## Spec Sync (canonical merge — DONE, do NOT re-apply)

- **`openspec/specs/mcp-server/spec.md` — MODIFIED `### Requirement: Auth status preflight read-only (10.8)`**
  (wholesale replacement of the envelope contract + posture semantics). The requirement was replaced
  in place at its existing location (canonical line 420, between `Server instructions`-adjacent
  requirements and `Approval-phrase configuration diagnostics (APX-01)`); no requirement was added,
  moved, or removed. Net diff: `1 file changed, 52 insertions(+), 2 deletions(-)`.
- Provenance line updated on merge (repo convention — verified against 40+ existing lines in
  `openspec/specs/`; MODIFIED form matches `mcp-server/spec.md` lines 252/549/601):
  `> Added by change \`mcp-dx-audit-surface\` (archived 2026-08-31). Modified by \`2026-09-11-fix-auth-status-posture\` (archived 2026-09-11).`
  If the actual archive date differs from 2026-09-11, amend this date during archive.
- Declared transforms applied on merge (nothing else changed):
  1. Delta's two-line provenance blockquote (`Modified by\n> change \`...\` (issue #145).`) → canonical
     single-line blockquote with the archive-date convention (`(archived 2026-09-11)`); the `issue #145`
     reference lives in this delta + `verify-report.md` (canonical provenance carries no `issue #` refs —
     0 occurrences repo-wide outside prose).
  2. Delta's `*Tests:*` test-pointer runs (9 lines across 6 scenario blocks) dropped — canonical format
     carries no test pointers (0 occurrences repo-wide); traceability lives in this delta +
     `verify-report.md`.
  3. Delta's `(kept verbatim from canonical 10.8)` scenario annotation dropped — canonical scenario
     headers carry no such annotations.
  4. Blank-line normalization: single blank line before each `#### Scenario:` and after the requirement
     header (the `*Tests:*`-strip collapsed separators; re-expanded to canonical spacing).
- **`APX-01` (`Approval-phrase configuration diagnostics`) is byte-intact** — verified by SHA-256 of
  the block from its requirement header to EOF: `5291acbb84f98a3c5b319d7f0a2a84513257b9d5099524d5c2a29046c4829aff`
  before and after the sync. It was NOT re-added and NOT touched (issue #144 isolation honored).
- The delta `specs/mcp-server/spec.md` is intentionally left byte-identical (untracked, 8778 bytes) for
  the archival record.

## Verification performed (exact)

```text
node (native helper lib/openspec-deltas.ts — parse + in-memory re-apply, result discarded):
  canonical blocks: 24 | unique names: 24 | duplicates: 0
  10.8 blocks in canonical: 1 | APX-01 blocks in canonical: 1
  delta ops -> added: 0, modified: 1, removed: 0
  re-apply (MODIFIED) -> blocks: 24 | unique: 24 | 10.8 count: 1 (replaces by name; no duplication)
  fidelity: embedded canonical 10.8 block == delta block modulo the 4 declared transforms (exact,
            modulo the intentional blank line before the following `---` separator)

config-count checks (canonical openspec/specs/mcp-server/spec.md):
  requirement headers 24 -> 24 (MODIFIED, not added)
  scenario headers   85 -> 90 (+5 new posture GWT scenarios, canonical scenario kept)
  10.8 occurrences == 1 | APX-01 occurrences == 1 | *Tests:* occurrences == 0 | tabs == 0
  APX-01 block SHA-256 unchanged: 5291acbb84f98a3c5b319d7f0a2a84513257b9d5099524d5c2a29046c4829aff
  line endings: LF-only (0 CRLF, 0 bare CR) | file 752 -> 802 lines
git diff --check          -> clean (no whitespace errors)
git diff --stat canonical -> openspec/specs/mcp-server/spec.md | 52 insertions(+), 2 deletions(-)
delta file untouched: openspec/changes/2026-09-11-fix-auth-status-posture/specs/mcp-server/spec.md
  byte-identical (8778 bytes)
change folder NOT moved: openspec/changes/2026-09-11-fix-auth-status-posture/ still active
  (archive dir contains 0 entries matching fix-auth-status-posture)
```

## Idempotency

- The native helper's `applyDeltaSpec` handles a **MODIFIED** block by *replacing by name* (via
  `requireCanonicalBlock` + `replacements`), so a re-application **cannot duplicate** 10.8 — verified
  in-memory above (re-apply → still exactly 1 block, 24 unique names). This differs from the ADDED
  guard used by #144 (`Cannot add existing canonical requirement ...` throws), which does not apply to
  a MODIFIED-only delta.
- **Archive phase: do NOT re-apply this delta.** Re-applying would overwrite the canonical 10.8 with the
  *raw* delta block, re-introducing the `*Tests:*` scaffolding, the `(issue #145)` provenance form, and
  the `(kept verbatim ...)` annotation — i.e. a regression relative to the transformed canonical above.
  The sync is absorbed; the guard is this note + the status engine.

## Status / actionContext findings

- `actionContext.mode: repo-local`; `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]`; the
  canonical target lies inside the authoritative workspace — no blocked reason.
- Injected native status reported `dependencies.sync: "blocked"` / `verify: "ready"` while
  `artifacts.verifyReport: "done"` and `verify-report.md` is unambiguously clean (verdict pass,
  blockers 0, critical 0, scenarios 5/5, test exit 0, all gates green) and `taskProgress` is 38/38
  complete (`applyState: all_done`). The sync prerequisite ("only after verification is clean") is
  therefore satisfied; the parent prompt explicitly mandated this sync. The stale `blocked` label is
  attributable to the missing `syncReport` artifact (`artifacts.syncReport: "missing"`), not to a real
  blocker. Recorded here for transparency.
- `relationships.sameDomainActiveChanges: []`, `collisions: []` — no active same-domain collision;
  this is the only active change and the only one touching `mcp-server` specs. No archive/sync ordering
  conflict.
- No `openspec/config.yaml` present — no `rules.sync` to apply.

## For the archive phase

1. Include a `## Spec Sync` section in the future `archive-report.md` citing the MODIFIED 10.8 merge
   above (mirror the "already absorbed" wording used by `feat-mcp-init-tool` / `fix-auth-status-hints`).
2. Do not run `applyDeltaSpec` against this delta on the canonical (it would regress the transforms —
   expected, not an error).
3. The delta `specs/mcp-server/spec.md` is intentionally left byte-identical for the archival record.
4. Amend the provenance date (`archived 2026-09-11`) if the actual archive date differs.
