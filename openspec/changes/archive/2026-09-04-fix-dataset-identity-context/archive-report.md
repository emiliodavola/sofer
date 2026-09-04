# Archive Report: fix-dataset-identity-context

**Change**: fix-dataset-identity-context (GitHub issue #116)
**Archived**: 2026-09-04 → `openspec/changes/archive/2026-09-04-fix-dataset-identity-context/`
**Artifact store**: hybrid (OpenSpec files + Engram `sdd/fix-dataset-identity-context/archive-report`)
**Archive mode**: standard — no `reviewGate` present (receipt-driven development kill switch off for this candidate; no review artifact exists); archive proceeded under ordinary repository policy.

## Final State (at close)

- **Verdict: PASS** — all 9/9 requirements implemented, 52/52 scenarios covered by passing tests.
- **Full suite**: 1332 passed / 2 skipped (exit 0); mypy clean (30 source files); ruff check + format clean (60 files); `git diff --check` clean.
- Issue #116 ground-truth reproduction passes over the real MCP stdio process (`TestParentRootIdentity`).
- Zero CRITICAL / zero WARNING findings. 3 SUGGESTIONs carried as follow-ups (below).
- **Task Completion Gate**: archived `tasks.md` shows 24/24 tasks checked, 0 unchecked. (verify-report's "22 total" excludes the two Phase-5 gate rows 5.1/5.2; completion state is unanimous across all sources.)
- **`SOFER_TRACE.md` (PB-08)**: untracked, unmodified, never staged — git status confirms it remains `??` only, untouched by this archive.

## Spec Deltas Synced (archive-replace by requirement ID)

| Domain | Requirement | Action | Scenarios |
|--------|-------------|--------|-----------|
| mcp-server | INIT-05 | ADDED (identity validation before any write) | 5 |
| mcp-server | INIT-02 | MODIFIED (fail-closed strict-descendant cwd; supersedes back-compat) | 7 |
| mcp-server | INIT-03 | MODIFIED (canonical identity reporting; heading renamed) | 4 |
| mcp-server | MSP-R03 | MODIFIED (output_schema identity fields) | 4 |
| mcp-server | MSP-R10 | MODIFIED (`discovery_root` bound; `_bound_discovery` retired) | 5 |
| cli | CLI-R07 | MODIFIED (`--user` required, pre-write rejection, absolute config_path) | 15 |
| tool-config | TC-05 | MODIFIED (`discovery_root` param) | 2 |
| process-boundary | PB-04 | MODIFIED (real-process parent-root/child-cwd scenarios) | 7 |
| process-boundary | PB-09 | MODIFIED (second module-scoped stdio fixture) | 3 |

Total: **52/52 scenarios** live in `openspec/specs/`, matching the verified compliance map. All other requirement blocks preserved untouched. Requirement IDs verified unique per domain (mcp-server 22, cli 8, tool-config 12, process-boundary 9).

Merge notes:
- PB-04's MODIFIED block drops the "Malformed config" and "Delivery handoff" scenarios (still carried in the requirement's body prose) in favor of the two real-process parent-root scenarios — consistent with the verified 52/52 map and the delta-as-authoritative archive-replace convention.
- History annotations follow the repo convention: each synced requirement gained a `Modified by \`fix-dataset-identity-context\` (archived 2026-09-04)` clause; INIT-05 gained `Added by \`fix-dataset-identity-context\` (archived 2026-09-04)`.

## Artifacts Archived

proposal.md, specs/ (cli, mcp-server, process-boundary, tool-config), design.md, tasks.md (24/24 complete), apply-progress.md, verify-report.md, exploration.md. Moved mechanically (`mv` — folder was untracked), byte-identity verified by **empty `diff -r` readback** (pre-move snapshot vs archived tree, exit 0).

## Engram Persistence

`mem_save` topic_key `sdd/fix-dataset-identity-context/archive-report`, type `architecture`, project `sofer`, capture_prompt false. Artifacts were read from the filesystem (openspec/hybrid retrieval), so no Engram observation IDs apply to the artifact set.

## Follow-ups (verify SUGGESTIONs, not applied)

1. PB-09 spec prose names the Root-unwrap helper `_mcp_payload`; the code calls it `mcp_payload` (public). Cosmetic — align prose or rename at a future change.
2. `codebook.generate` retains inert `delimiter: str = ";"` / `encoding: str = "utf-8-sig"` signature defaults for direct library calls; tool paths already inject config values. Consider removing the defaults if rule-3 is enforced at the signature level.
3. Interior-space names (`"my dataset"`) are still accepted by `validate_identity` (recorded decision S3 in apply-progress; contract-faithful per INIT-05 wording). A future tightening could reject interior whitespace in `name`.

## Risks / Notes

- None blocking. The PB-04 scenario-set change (2 scenarios replaced by 2 real-process scenarios) is the only non-additive merge; it matches the verified delta and the 52/52 map. No merge conflicts were encountered in any of the 9 synced blocks.