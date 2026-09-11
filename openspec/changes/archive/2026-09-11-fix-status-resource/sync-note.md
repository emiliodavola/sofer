# Sync Note — 2026-09-11-fix-status-resource

**Phase:** sdd-sync (canonical merge), executed 2026-09-11 on `fix/146-status-resource`.
**Status:** synced — canonical spec updated; change remains active (NOT archived).
**Artifact store:** openspec (config.yaml header says "hybrid (openspec + engram)"; the native status
resolved `artifactStore: openspec`). Repo convention has no `sync-report.md` (0 exist); this note is
the handoff for the archive phase, which MUST fold the material below into `archive-report.md` under
its `## Spec Sync` section (precedent: `2026-09-11-fix-auth-status-posture/sync-note.md`).

## Spec Sync (canonical merge — DONE, do NOT re-apply)

- **`openspec/specs/mcp-server/spec.md` — MODIFIED `### Requirement: Resources (MSP-R07)`**
  (additive amendment: ONE static resource `sofer://status` + never-leak and boundary clauses; the
  three URI templates and their containment/size-guard semantics stay unchanged). The requirement was
  replaced in place at its existing location (canonical line 181, between `Scan non-interactivity
  (MSP-R06)` and `Prompts (MSP-R08)`); no requirement was added, moved, or removed. Net diff:
  `1 file changed, 35 insertions(+), 1 deletion(-)` (the single deletion is the old two-part
  provenance line collapsed to one).
- Provenance line updated on merge (repo convention — verified against 40+ existing lines in
  `openspec/specs/`; MODIFIED form matches `mcp-server/spec.md` lines 252/549/601 and the #145 merge):
  `> Added by change \`sofer-mcp-server\` (archived 2026-08-28). Modified by \`2026-09-11-fix-status-resource\` (archived 2026-09-11).`
  If the actual archive date differs from 2026-09-11, amend this date during archive.
- Declared transforms applied on merge (nothing else changed):
  1. Delta's two-line provenance blockquote (`Modified by\n> change \`...\` (issue #146).`) → canonical
     single-line blockquote with the archive-date convention (`(archived 2026-09-11)`); the `issue #146`
     reference lives in this delta + `verify-report.md` (canonical provenance carries no `issue #` refs —
     0 occurrences in the canonical file).
  2. Delta's `*Tests:*` test-pointer runs (9 lines across 5 scenario blocks) dropped — canonical format
     carries no test pointers (0 occurrences in the canonical file); traceability lives in this delta +
     `verify-report.md`.
  3. Delta's `(kept verbatim from canonical MSP-R07)` scenario annotations (3) dropped — canonical
     scenario headers carry no such annotations.
  4. Blank-line normalization: single blank line before each `#### Scenario:` and after the requirement
     header (the `*Tests:*`-strip collapsed separators; re-expanded to canonical spacing), single blank
     line before the trailing `---`.
- **`10.8` (`Auth status preflight read-only (10.8)`, #145) and `APX-01` (`Approval-phrase
  configuration diagnostics`, #144) are byte-intact** — verified by SHA-256 of each block from its
  requirement header to EOF, before and after the sync:
  - 10.8-tail: `a5c25bcf314fb08ee7f206a10403b49fdb80102bf23cce3b867ec383a4167328` (unchanged)
  - APX-01-tail: `5291acbb84f98a3c5b319d7f0a2a84513257b9d5099524d5c2a29046c4829aff` (unchanged —
    identical to the hash recorded by the #145 sync-note after its merge)
  They were NOT re-added and NOT touched (issue #144/#145 isolation honored).
- The delta `specs/mcp-server/spec.md` is intentionally left byte-identical (untracked, 7928 bytes) for
  the archival record.

## Verification performed (exact)

```text
config-count checks (canonical openspec/specs/mcp-server/spec.md):
  requirement headers 24 -> 24 (MODIFIED, not added) | unique names 24
  scenario headers   90 -> 92 (+2: MSP-R07 3 -> 5 scenarios; canonical scenarios kept verbatim)
  MSP-R07 occurrences == 1 | 10.8 occurrences == 1 | APX-01 occurrences == 1
  *Tests:* occurrences == 0 | (kept verbatim ...) == 0 | (existing pin, unmodified) == 0
  issue #146 occurrences == 0 (canonical) | tabs == 0 | trailing-whitespace lines == 0
  10.8-tail SHA-256 unchanged: a5c25bcf314fb08ee7f206a10403b49fdb80102bf23cce3b867ec383a4167328
  APX-01-tail SHA-256 unchanged: 5291acbb84f98a3c5b319d7f0a2a84513257b9d5099524d5c2a29046c4829aff
  line endings: LF-only (0 CRLF, 0 bare CR) | file 802 -> 836 lines (wc -l) | 48495 -> 52775 bytes
git diff --check          -> clean (no whitespace errors)
git diff --stat canonical -> openspec/specs/mcp-server/spec.md | 35 insertions(+), 1 deletion(-)
delta file untouched: openspec/changes/2026-09-11-fix-status-resource/specs/mcp-server/spec.md
  byte-identical (7928 bytes, 89 lines, no trailing newline)
change folder NOT moved: openspec/changes/2026-09-11-fix-status-resource/ still active
  (archive dir contains 0 entries matching fix-status-resource)
```

## Idempotency

- A **MODIFIED** block is applied by *replacing by name*; the canonical now contains exactly one
  `### Requirement: Resources (MSP-R07)` header (count == 1, 24 unique requirement names), so a
  re-application **cannot duplicate** MSP-R07 — verified in-memory after the merge (canonical re-split
  on `### Requirement:` headers: 24 blocks, all unique). This differs from the ADDED guard used by #144
  (`Cannot add existing canonical requirement ...` throws), which does not apply to a MODIFIED-only
  delta.
- **Archive phase: do NOT re-apply this delta.** Re-applying would overwrite the canonical MSP-R07 with
  the *raw* delta block, re-introducing the `*Tests:*` scaffolding, the `(issue #146)` provenance form,
  and the `(kept verbatim ...)` annotations — i.e. a regression relative to the transformed canonical
  above. The sync is absorbed; the guard is this note + the status engine.

## Status / actionContext findings

- `actionContext.mode: repo-local`; `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]`; the
  canonical target lies inside the authoritative workspace — no blocked reason.
- Native status reported `dependencies.sync: "blocked"` / `dependencies.archive: "blocked"` while
  `verify-report.md` is unambiguously clean (verdict pass, critical_findings 0, blockers 0, every
  #146 acceptance criterion PASS, `uv run pytest tests/ -q` → 1495 passed / 6 skipped, exit 0) and
  `taskProgress` is 18/18 complete (`applyState: all_done`). The sync prerequisite ("only after
  verification is clean") is therefore satisfied; the parent prompt explicitly mandated this sync. The
  stale `blocked` label is attributable to the missing `syncReport` artifact
  (`artifacts.syncReport: "missing"`) — deps flip after this note lands. Recorded here for
  transparency. `deferredParentActions` (commit / push+PR / post-apply review) remain 0/3 — parent
  lifecycle work, untouched by sync.
- `relationships.sameDomainActiveChanges: []`, `collisions: []` — no active same-domain collision;
  this is the only active change touching `mcp-server` specs. No archive/sync ordering conflict.
- `openspec/config.yaml` exists but defines no `rules.sync` (only proposal/specs/design/tasks/apply/
  verify/archive rules) — nothing to apply; the closest adjacent rule (`archive: Warn before merging
  destructive deltas`) does not bite: this delta is additive (MODIFIED only, no REMOVED).

## For the archive phase

1. Include a `## Spec Sync` section in the future `archive-report.md` citing the MODIFIED MSP-R07 merge
   above (mirror the "already absorbed" wording used by `feat-mcp-init-tool` / `fix-auth-status-hints` /
   `fix-auth-status-posture`).
2. Do not run `applyDeltaSpec` against this delta on the canonical (it would regress the transforms —
   expected, not an error).
3. The delta `specs/mcp-server/spec.md` is intentionally left byte-identical for the archival record.
4. Amend the provenance date (`archived 2026-09-11`) if the actual archive date differs.