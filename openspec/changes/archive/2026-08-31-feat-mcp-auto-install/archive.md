# Archive Report — feat-mcp-auto-install

- **Change**: `feat-mcp-auto-install` (MSP-R02 + MSP-R12 + PKG-03/PKG-06 — mcp auto-install)
- **Date**: 2026-08-31
- **Store**: hybrid (Engram + openspec)
- **Archived to**: `openspec/changes/archive/2026-08-31-feat-mcp-auto-install/`
- **Status**: archived — all 10 tasks complete, verify PASS (no CRITICAL)

## Lineage — Engram Observation IDs

| Artifact | Observation ID | Title / topic_key |
|----------|---------------|-------------------|
| exploration | #748 | `Explore MCP auto-install` / `sdd/feat-mcp-auto-install/exploration` |
| proposal | #749 | `sdd/feat-mcp-auto-install/proposal` |
| spec | #750 | `sdd/feat-mcp-auto-install/spec` |
| design | #751 | `sdd/feat-mcp-auto-install/design` |
| tasks | #752 | `sdd/feat-mcp-auto-install/tasks` |
| apply-progress | #753 | `feat-mcp-auto-install apply progress` / `sdd/feat-mcp-auto-install/apply-progress` |
| verify-report | #755 | `sdd/feat-mcp-auto-install/verify-report` |
| archive-report | (this report) | `sdd/feat-mcp-auto-install/archive-report` |

`capture_prompt: false` for all SDD artifacts (automated pipeline outputs). Engram is source of truth for recovery; filesystem delta + main specs are audit trail.

## Task Completion Gate

- **Tasks artifact**: `openspec/changes/feat-mcp-auto-install/tasks.md` → archived as `openspec/changes/archive/2026-08-31-feat-mcp-auto-install/tasks.md` — 10/10 `[x]` (phases 1–5, single PR ~74 lines)
- **Apply progress**: Engram #753 — 10/10 complete, files changed: `pyproject.toml` (fastmcp to dependencies + alias), `uv.lock` (unconditional), `src/sofer/mcp_server.py:55-64` (pip+uv tool+PEP508 guard), `README.md` + `README_ES.md` (Install canonical `sofer @` + alias + `uv tool`/`uvx --with`, intro included-by-default), `tests/test_mcp_server.py` (TestImportWithoutExtra + TestWheelPackaging)
- **Verify**: Engram #755 + `verify.md` — **PASS**, 1163 passed 2 skipped, ruff + mypy + ruff format green, all spec scenarios proven (MSP-R02 7 scenarios, MSP-R12 5 scenarios, PKG-03 2 scenarios, PKG-06 2 scenarios), wheel METADATA/entry_points correct, both CLIs `sofer`+`sofer-mcp` exit 0, warnings only non-blocking (hatchling local skip)
- **Gate result**: ✅ PASS — no unchecked implementation tasks, no CRITICAL blockers, stale-checkbox reconciliation not needed

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-server` | Updated | **2 MODIFIED** — MSP-R02 Import without the extra fails clearly (lean → included-by-default, 7 scenarios: lean install includes fastmcp, alias works, guard pip+uv+PEP508, import succeeds, METADATA unconditional, uv.lock unconditional, existing tests green) + MSP-R12 Packaging and documentation (optional → required+alias, 5 scenarios: Wheel script and Requires-Dist, Alias optional, README Install correct, README AI/MCP fixed, README_ES mirrors) |
| `packaging` | Updated | **1 MODIFIED** PKG-03 Installability and entry point (single → both CLIs, 2 scenarios: Both entry points in wheel, Both CLIs run) + **1 ADDED** PKG-06 MCP runtime dependency included by default (2 scenarios: dependencies include fastmcp, Alias identical pin) |

**Merge contract**: MODIFIED → replaced matching requirement preserving other requirements (MSP-R01,R03-R11 and PKG-01,02,04,05 preserved); ADDED → appended (PKG-06); no REMOVED/RENAMED; existing IDs preserved, no duplication.

### Main specs updated

- `openspec/specs/mcp-server/spec.md` — now contains updated MSP-R02 + MSP-R12 (MSP-R01,R03-R11 untouched)
- `openspec/specs/packaging/spec.md` — now contains updated PKG-03 + added PKG-06 (PKG-01,02,04,05 untouched, PKG-06 appended after PKG-05)

## Archive Contents

- `proposal.md` ✅ (intent broken-by-default sofer-mcp + PEP 508 docs, scope in/out, promotion+alias approach, risks, rollback)
- `exploration.md` ✅ (pyproject optional vs required, PEP 508 placement, uv.lock, guard retention, README divergence)
- `specs/` ✅ (mcp-server/spec.md delta MSP-R02/R12, packaging/spec.md delta PKG-03/06)
- `design.md` ✅ (dependency placement promotion+alias, guard retention, uv lock+build, data flow pip/uv/uvx, 6 file changes)
- `tasks.md` ✅ (10/10 tasks complete, review workload Low, single PR ~100 lines forecast, dependencies 1.1→1.2→2.1→4.x→5.x)
- `verify.md` ✅ (PASS — completeness + correctness matrix + build evidence + design coherence + docs cross-checks)
- `archive.md` ✅ (this file)

Active changes directory no longer has this change after move.

## Source of Truth Updated

The following specs now reflect the new behavior and are the authoritative source for future changes:

- `openspec/specs/mcp-server/spec.md` — MSP-R02 + MSP-R12
- `openspec/specs/packaging/spec.md` — PKG-03 + PKG-06

## Project Config Updated

- `openspec/project.md` — Structure note updated: `mcp_server.py — fastmcp (included by default; sofer[mcp] is alias)`; Testing line updated to 1163 passed on 2026-08-31 with MSP-R02/R12/PKG-03/PKG-06 + mcp auto-install note; Last-updated footer stamped 2026-08-31 — feat-mcp-auto-install archived.
- `openspec/config.yaml` — unchanged (no archive rule trigger, no new testing infra; `rules.archive: Warn before merging destructive deltas` respected — merge not destructive)

## README / Docs Sync

- `README.md` + `README_ES.md` already synced in apply (Install canonical `pip install "sofer @ git+..."` + `uv tool install "sofer @ git+..." --force` + alias `sofer[mcp] @` + `uvx --from git+... --with "sofer[mcp]" sofer-mcp --help`; AI/MCP intro flipped to included by default; broken `git+...[mcp]` absent) — confirmed via grep (0 broken, 2 correct `sofer[mcp] @ git` per README), headings/order match, English commands identical, same commit per AGENTS.md §13 ✅ no further edit
- `pyproject.toml` `[project.dependencies]` `fastmcp>=3.4,<4` unconditional + `[project.optional-dependencies].mcp` alias identical pin + `[dependency-groups].dev` pin — authoritative, `uv.lock` regenerated ✅
- Wheel `METADATA` `Requires-Dist: fastmcp<4,>=3.4` unconditional + `Provides-Extra: mcp` retained ✅

## Verification post-sync

- Main specs contain new requirements (grep `MSP-R02`, `MSP-R12`, `PKG-03`, `PKG-06` each count >=1) ✅
- No duplicated requirement headers (single MSP-R02, single MSP-R12, single PKG-03, single PKG-06) ✅
- Existing requirements preserved (MSP-R01,R03-R11; PKG-01,02,04,05) ✅
- Broken PEP 508 `sofer.git@vX.Y.Z[mcp]` count 0 in both READMEs ✅
- Change folder moved to `openspec/changes/archive/2026-08-31-feat-mcp-auto-install/` ✅
- Engram archive-report saved with lineage IDs ✅

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. `sofer-mcp` now installs out-of-the-box via `pip install "sofer @ git+..."` / `uv tool install "sofer @ git+..." --force` with `fastmcp` in `dependencies`; alias `sofer[mcp] @` remains valid; guard retained degraded-only with `pip`+`uv tool`+PEP 508 hint; both entry points `sofer`+`sofer-mcp` verified. Ready for the next change.

## Risks / Follow-ups

- **WARNING (verify #755/1)**: `TestWheelPackaging` skips locally when `hatchling` not in venv (dev group); METADATA proven via manual wheel ZipFile inspect + CI authoritative — non-blocking.
- **WARNING (verify #755/2)**: Guard message uses `sofer[mcp] @` for both pip/uv; canonical `sofer @` also valid but guard showing alias is spec-compliant — non-blocking; docs show both.
- **SUGGESTION**: Add `hatchling` to `dev` group or use `uv build` helper so wheel test runs locally without `uv run --with hatchling` workaround; CI release.yml wheel-build job remains authoritative.
- No CRITICAL issues; rollback via revert `pyproject.toml`/`uv.lock`/guard/READMEs/specs + `uv lock`.

---
*Archive performed by sdd-archive sub-agent, auto mode, hybrid store, single PR delivery (~74 diff lines, budget 2000). No git tag or version bump per AGENTS.md 12 (tag-driven release is manual).*
