# Archive Report: test-mcp-cli-regression-suite

**Change**: `test-mcp-cli-regression-suite` (GitHub #119, child of #115)
**Date archived**: 2026-09-02
**Artifact store**: hybrid (openspec + Engram) — both
**Execution mode**: auto
**Status**: archived — SDD cycle complete
**Verify verdict**: PASS 26/26 (verify-report #929 — 0 blockers, 0 critical; requirements 9/9)
**HEAD**: `1f723c8` (all work committed; verify-report PASS, 27/27 tasks checked)
**Branch**: `test/mcp-cli-regression-suite` (tracker branch; archive ships with the PR merge)

## Summary

Test-only regression suite (PB-01…PB-09, 26 scenarios) pinning sofer's MCP server and CLI through the same boundaries real agents use: in-process FastMCP `Client(server)` for registered tools (roster, schemas, envelopes, `tools/call` round-trip), real stdio subprocess transport with clean JSON-RPC framing, and executable CLI subprocesses (`[sys.executable, "-m", "sofer.cli", ...]`). Zero production changes — `src/sofer/` untouched.

- New `tests/test_mcp_process.py`: stdio framing, nested-CWD init placement, recovery replay (publish_confirm risk gate, init file-exists/name-empty), config states (empty/existing/greenfield/triage/malformed), delivery handoff.
- Shared boundary helpers in `tests/conftest.py`: `mcp_payload` (Root-unwrap), `run_cli` (cp1252 env), module-scoped `mcp_stdio_server` — one spawn per module; reused across modules, not duplicated.
- Converted direct-call tests (`sofer_publish_confirm` ×22, `sofer_init` ×25, `sofer_validate`, `test_offline_happy_path`) through `Client(server)`; `test_mcp_server._unwrap` delegates to `mcp_payload`.
- `tests/test_cli.py` `TestSubprocessBoundary`: `--help` rc 0 + all subcommands, strict cp1252 with re-encode assertion (ubuntu CI via `PYTHONIOENCODING`), unknown-command rc 2.
- `.github/workflows/ci.yml`: `uv run pytest -v` annotated as the deliberate complete-suite gate (comment-only change; `push` trigger on all branches so chained slice branches run it).
- New fixtures `tests/fixtures/mcp-config-states/{empty,malformed}.toml`, kept out of `mcp-happy-path/`.

Boundary correction documented during apply (design.md Open Questions): FastMCP projects tool results through each `output_schema`, so refusal envelopes at the client boundary drop `error_code`/`message`/`next` and non-`hf` targets surface as schema `ToolError`. PB-03 recovery replay therefore keys off boundary-visible `output` messages plus the deterministic, documented `next` hint VALUES, asserting the replayed call reaches a DIFFERENT gate or `ok:True`.

## Files Changed (implementation, merged via chained PRs on the tracker branch)

| File | Action | Details |
|------|--------|---------|
| `tests/conftest.py` | Modified | `mcp_payload(result)` Root-unwrap; `run_cli(argv, *, cwd, env=None, encoding="utf-8")`; module-scoped `mcp_stdio_server` |
| `tests/test_mcp_process.py` | Created | Stdio framing (PB-01), nested CWD (PB-04), recovery replay (PB-03), config states + delivery handoff (PB-04), all via `Client(server)`/stdio |
| `tests/test_mcp_server.py` | Modified | 22 publish_confirm + 25 init + 1 validate direct calls → `_call(server, ...)`; `_unwrap` delegates to `mcp_payload` |
| `tests/test_mcp_schema.py` | Modified | Direct validate/publish_confirm conversions; `test_offline_happy_path` via `Client(server)`; `publish._api` monkeypatch + `HF_TOKEN` retained for upload-branch test |
| `tests/test_cli.py` | Modified | `TestSubprocessBoundary`: `--help` rc 0 lists all 9 subcommands; strict cp1252 re-encode; unknown command rc 2 |
| `tests/fixtures/mcp-config-states/` | Created | `empty.toml` + `malformed.toml` for PB-04 |
| `.github/workflows/ci.yml` | Modified | Comment-only annotation: `uv run pytest -v` is the complete-run gate (PB-05) |

`src/sofer/` read-only throughout (zero production drift).

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| process-boundary | Created | NEW domain — `openspec/specs/process-boundary/` did not exist; delta spec copied verbatim (byte-identical, sha256 `F166D7DD17F9DE29C5841ABD62BD75A4E8A338BB114FE9D276CBDDD10165340F`). 9 requirements (PB-01…PB-09), 26 scenarios. |

No MODIFIED/REMOVED/RENAMED deltas; the delta is a full spec for a new domain. Copy was non-destructive — no warning required per `openspec/config.yaml` `rules.archive: Warn before merging destructive deltas`.

**Index**: `openspec/specs` contains 15 domain specs now (process-boundary added); no separate index file — each domain `spec.md` is the source of truth.

## Task Completion

| Phase | Tasks | Status |
|-------|-------|--------|
| 1 Shared boundary fixtures (PR 1) | 1.1 mcp_payload · 1.2 run_cli · 1.3 mcp_stdio_server · 1.4 _unwrap delegation · 1.5 gate | 5/5 ✅ |
| 2 Route registered tools through Client(server) (PR 2) | 2.1 publish_confirm conversions · 2.2 init conversions · 2.3 validate conversions · 2.4 test_mcp_schema · 2.5 gate | 5/5 ✅ |
| 3 Process module — stdio, CWD, recovery (PR 3) | 3.1 config fixtures · 3.2 stdio framing · 3.3 nested CWD · 3.4 publish_confirm recovery · 3.5 init recovery · 3.6 gate | 6/6 ✅ |
| 4 Process module — config states + handoff (PR 4) | 4.1 empty · 4.2 existing · 4.3 greenfield+triage · 4.4 malformed · 4.5 handoff · 4.6 gate | 6/6 ✅ |
| 5 CLI subprocess + CI + final gates (PR 5) | 5.1 --help subprocess · 5.2 cp1252 · 5.3 dispatch rc 2 · 5.4 ci.yml annotation · 5.5 final gate | 5/5 ✅ |
| **Total** | **27** | **27/27 ✅** |

All task checkboxes `[x]` in archived `tasks.md` (verified `rg -c "^- \[ \]"` → 0 unchecked). No stale unchecked tasks, no exceptional reconciliation needed — `sdd-apply` marked all persisted tasks complete and `verify-report` confirms `Tasks complete: 27/27`.

## Verification Evidence

- **Test command**: `uv run pytest tests/ -q` → `1270 passed, 2 skipped (pre-existing), 13 warnings in 25.80s` — exit 0 (hash `sha256:1981c0a0b634a2103d1d00b89122b729c69c4d0d48996280c42111183ca52204`); 1272 collected (1269 baseline + 3 new), count not regressed.
- **Build**: `uv run ruff check src/ tests/` → all passed; `uv run mypy src/ scripts/` → `Success: no issues found in 30 source files`; `git diff --check dev...HEAD` → clean — exit 0 (hash `sha256:f60b2867b79b4087fa0b79626b505f5c54fa6cb39c43fb18fc81ea025d4be167`).
- **Credential-free (PB-06)**: full suite green with `HF_TOKEN`, `HF_HUB_TOKEN`, `HUGGING_FACE_HUB_TOKEN` all absent — zero credential-dependent skips/failures.
- **Spec compliance**: 26/26 scenarios COMPLIANT (runtime-executed for all behavioral scenarios; static diff/CI evidence for PB-01-s4, PB-05, PB-08).
- **Correctness**: PB-01 conversions 22+25+1 through `_call(server, ...)`; zero new `+` lines call registered tools directly; PB-02 cp1252 test re-encodes stdout as cp1252 (not decode-only); PB-03 replays assert branch progression (different gate or `ok:True`); PB-04 via real fixture TOMLs + filesystem-path assertions; PB-06 `publish._api` monkeypatched; PB-09 helpers typed and single-homed, one `build_server()` per test, module-scoped stdio spawn, `asyncio.run`, no pytest-asyncio, no new deps.
- **Coherence**: D1–D7 all followed; D3 documented boundary correction (client-boundary envelope projection) reflected in design.md Open Questions.
- **Critical issues**: 0; **Warnings**: 2 non-blocking (orchestrator brief task-count discrepancy 20 vs authoritative 27; pre-existing `_make_dataset`/`_write_minimal_dataset` near-duplicate fixtures, predates change); **Suggestions**: 2 non-blocking (future boundary-hygiene pass for remaining `sofer_publish` ×7 / `sofer_scan_apply` ×2 direct calls; consider `.gitignore` for `SOFER_TRACE.md`).
- **Verdict**: **PASS** — Archive-ready.

## Rollback Plan

Pure test change — delete `tests/test_mcp_process.py` and `tests/fixtures/mcp-config-states/`, revert `conftest.py`/`test_mcp_server.py`/`test_mcp_schema.py`/`test_cli.py`/`ci.yml` edits. No production surface, no migration, no data impact.

## Lessons & Follow-ups

- **Client boundary ≠ direct-call boundary**: FastMCP `output_schema` projection drops `error_code`/`message`/`next` and turns invalid `target` values into schema `ToolError` — recovery tests MUST key off boundary-visible signals (human-readable `output` + deterministic hint values), not the direct-call envelope.
- **Chained-slice CI**: a `pull_request` `branches:` filter applies to the PR base, so slice PRs targeting `test/...` branches need the `push` trigger to run the gate.
- **cp1252 on ubuntu**: `PYTHONIOENCODING=cp1252` + `encoding="cp1252", errors="strict"` + a re-encode assertion proves zero non-cp1252 glyphs cross-platform without a Windows runner.
- **Per-process globals**: `_SERVER_ROOT`/`_APPROVAL_PHRASE` require one `build_server()` per test; module-scoped stdio fixture bounds subprocess wall-clock.
- **PR 2 forecast miss**: landed at 436 changed lines vs ~250–350 forecast (1.25–1.7×); plan later slices against the upper bound.
- **Follow-up (deferred, non-blocking)**: route the remaining pre-existing `sofer_publish` (7 sites) and `sofer_scan_apply` (2 sites) direct calls through `Client(server)` in a future boundary-hygiene pass (would need a spec amendment); optionally gitignore `SOFER_TRACE.md`.

## Engram Traceability

| Artifact | Observation ID | sync_id | Topic key |
|----------|---------------|---------|-----------|
| explore | #916 | obs-36114706f7a3c6a3 | sdd/test-mcp-cli-regression-suite/explore |
| proposal | #917 | obs-c7b0d9cfd0e71739 | sdd/test-mcp-cli-regression-suite/proposal |
| spec (delta) | #918 | obs-ee705d66eb7c72fd | sdd/test-mcp-cli-regression-suite/spec |
| design | #919 | obs-129f0c82761051fb | sdd/test-mcp-cli-regression-suite/design |
| tasks | #920 | obs-b3def8417b015013 | sdd/test-mcp-cli-regression-suite/tasks |
| apply-progress | #921 | obs-50243b701c57488d | sdd/test-mcp-cli-regression-suite/apply-progress |
| verify-report | #929 | obs-4d55ab23ae4d214f | sdd/test-mcp-cli-regression-suite/verify-report |
| archive-report | (this) | — | sdd/test-mcp-cli-regression-suite/archive-report |

Delta spec file: `openspec/changes/archive/2026-09-02-test-mcp-cli-regression-suite/specs/process-boundary/spec.md` → canonical `openspec/specs/process-boundary/spec.md` (copied verbatim — new domain, no merge needed).
Archived to: `openspec/changes/archive/2026-09-02-test-mcp-cli-regression-suite/` (closed 2026-09-02; hybrid artifact store).

Filesystem archive contains: `proposal.md` ✅ · `exploration.md` ✅ · `specs/process-boundary/spec.md` (PB-01…PB-09 delta) ✅ · `design.md` ✅ · `tasks.md` (27/27) ✅ · `apply-progress.md` ✅ · `verify-report.md` ✅ · `archive-report.md` (this) ✅
Active changes directory no longer contains `test-mcp-cli-regression-suite` (moved to archive).

## Source of Truth Updated

The following spec now reflects the new behavior:

- `openspec/specs/process-boundary/spec.md` — NEW domain (created 2026-09-02): 9 requirements (PB-01 Registered MCP tools via public boundary, PB-02 CLI user-visible output via executable subprocess, PB-03 Recovery replay executes returned calls, PB-04 Config-state scenario coverage, PB-05 Complete-run gate, PB-06 Deterministic and offline, PB-07 Quality gates, PB-08 SOFER_TRACE.md untouched, PB-09 Shared fixtures and per-test server isolation), 26 scenarios.

The contracts these tests pin were already stated by the `mcp-server` (MSP-R01/R02) and `cli` (CLI-R01/R02) specs — this change adds no production behavior, only the regression suite that makes boundary regressions visible.