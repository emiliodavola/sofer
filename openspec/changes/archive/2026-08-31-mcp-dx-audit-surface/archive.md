# Archive Report — mcp-dx-audit-surface

- **Change**: `mcp-dx-audit-surface` (MCP DX Audit — Secure core, agent-hostile surface, #111 → #112)
- **Date**: 2026-08-31
- **Store**: hybrid (Engram + openspec — `both`)
- **Archived to**: `openspec/changes/archive/2026-08-31-mcp-dx-audit-surface/`
- **Status**: archived — all 16 tasks complete, verify PASS_WITH_WARNINGS (0 CRITICAL, 2 WARNINGS)
- **PR**: https://github.com/emiliodavola/sofer/pull/112 (`feat/mcp-dx-audit-surface` → `dev`, Closes #111) — ready, NOT merged (human review pending)
- **Issue**: #111 — DO NOT close until PR merged; archive is audit trail only

## SDD Session Preflight

| Field | Value |
|-------|-------|
| execution_mode | auto |
| artifact_store.mode | both (hybrid) |
| delivery_strategy | auto-forecast |
| review_budget_lines | 5000 |
| project | sofer |
| change_name | mcp-dx-audit-surface |
| issue | #111 |
| branch | `feat/mcp-dx-audit-surface` (single PR, auto-forecast Medium risk, ~500 lines est) |
| review_budget | Single PR `feat/mcp-dx-audit-surface` → `dev`; 400-line budget risk Medium — chain not needed (actual diff 2232 insertions/636 deletions across 14 files exceeds budget but is surface-only refactor; reviewer slice is logical via P1-P4; auto-forecast accepted) |

> **Preflight provenance**: Inputs as injected by orchestrator — proposal 792, spec 793, design 794, tasks 795, apply-progress (`feat/mcp-dx-audit-surface`, PR #112), verify-report 796 + `verify.md` (PASS_WITH_WARNINGS), delta `openspec/changes/mcp-dx-audit-surface/specs/mcp-server/spec.md`, main `openspec/specs/mcp-server/spec.md`, READMEs+CHANGELOG already updated in apply.

## Lineage — Engram Observation IDs

| Artifact | Observation ID | Title / topic_key |
|----------|---------------|-------------------|
| exploration | #791 | `sdd/mcp-dx-audit-surface/explore` / `sdd/mcp-dx-audit-surface/explore` |
| proposal | #792 | `sdd/mcp-dx-audit-surface/proposal` |
| spec (delta) | #793 | `sdd/mcp-dx-audit-surface/spec` |
| design | #794 | `sdd/mcp-dx-audit-surface/design` |
| tasks | #795 | `sdd/mcp-dx-audit-surface/tasks` |
| apply-progress | (filesystem only) | `openspec/changes/mcp-dx-audit-surface/apply-progress.md` — no Engram `sdd/mcp-dx-audit-surface/apply-progress` exists; filesystem is authoritative (Engram search returned 0 for that key) |
| verify-report | #796 | `sdd/mcp-dx-audit-surface/verify-report` |
| archive-report | (this report) | `sdd/mcp-dx-audit-surface/archive-report` |

`capture_prompt: false` for all SDD artifacts (automated pipeline outputs). Engram is source of truth for recovery; filesystem delta + main specs are audit trail. Task says "artifact_store.mode: both" — both stores updated per skill hybrid persistence.

## Task Completion Gate

- **Tasks artifact**: `openspec/changes/mcp-dx-audit-surface/tasks.md` — **16/16 `[x]`** (P1 1.1-1.5, P2 2.1-2.3, P3 3.1-3.4, P4 4.1-4.4) — no stale unchecked implementation tasks
- **Apply progress**: `openspec/changes/mcp-dx-audit-surface/apply-progress.md` — **16/16 complete** — P1 surface (instructions phased, descriptions, Annotated+Literal+annotations+output_schema, Bootstrap fix, skeleton), P2 envelope (error_code enum + envelope + publish_confirm wiring), P3 preflight+rename (sofer_auth_status readOnlyHint, output→output_file/dir, fixtures, schema tests), P4 split (profile_all/render_all, no_checks→run_checks, README+CHANGELOG sync, offline happy path) — branch `feat/mcp-dx-audit-surface` single commit `3068aa9 feat(mcp): make canonical chain learnable from tools/list (14 tools, envelope, auth_status)`; files changed: `src/sofer/mcp_server.py` (14 tools), `tests/test_mcp_schema.py` (new 315 lines, 15 tests), `tests/test_mcp_server.py` (migrated), `tests/fixtures/mcp-happy-path/` (dataset.toml+data.csv), `README.md`+`README_ES.md` (phased diagram, 14-tool table, Breaking Changes), `CHANGELOG.md` (migration), `openspec/changes/mcp-dx-audit-surface/tasks.md` marked complete
- **Verify**: Engram #796 + `verify.md` — **PASS_WITH_WARNINGS** — 1232 passed / 2 skipped / 0 failed (20.58s), `uv run mypy src/` Success 29 files, `ruff check src tests` All checks passed, 10/10 scenarios compliant (2 with warnings), 7/7 requirements, 0 blockers, 0 critical_findings
- **Gate result**: ✅ PASS — no unchecked implementation tasks, no CRITICAL blockers, no stale-checkbox reconciliation needed. Per skill Task Completion Gate, sync and archive may proceed. CRITICAL issues would block — none present.

## Implementation Summary

**Scope delivered (surface-only, safety core frozen 254-595):**

- **P1 No-break (S)**: `instructions` → `Phase 0 → Phase 1 → Phase 2` + single UNTRUSTED; 11 descriptions rewritten ≤3 sent + `When to use:`/`Example:`/`Requires`/`Next`; strip `MSP-R*`/`CF-*`; `Annotated[Field(description)]` ~28 params + `Literal["local"/"hf"]` + `annotations` + `output_schema`; Bootstrap `Not part of canonical` at 1283,1347,1430 → `Phase 0: init→scan REQUIRED`; skeleton `tests/test_mcp_schema.py`
- **P2 Envelope (M)**: `error_code` enum 8 values + envelope `{ok:false,error_code,message,next,config_errors}` + `_refusal` helper; `publish_confirm` 4-gate ladder returns envelope (`PUBLISH_RISK_NOT_ACKD` etc.), `PathOutsideRootError` still throws (transport isError); envelope tests added
- **P3 Preflight+rename**: `sofer_auth_status(config)` `readOnlyHint:true` returns `{token:"present"|"missing", confidential, requires_approval_phrase, next}` no leak, no network; `output` → `output_file` (single) / `output_dir` (dirs) clean break pre-1.0 no shim; fixtures `tests/fixtures/mcp-happy-path/` (TOML `csv_delimiter ;`, 2 rows); schema tests tightened (14 count, enum, no legacy, typed output_schema)
- **P4 Split+Docs**: `sofer_profile`/`sofer_render` → `sofer_profile_all`/`sofer_render_all` via `*_all(config)` mirroring `codebook/_all`, `all_files` removed; `no_checks` → `run_checks:bool=true`; `README.md`+`README_ES.md` phased diagram + 14-tool table + Breaking Changes box in same commit per AGENTS.md §13 (Spanish prose `Fase 0`); `CHANGELOG.md` migration (`output`→`output_file/dir`, `run_checks`, `*_all`); offline happy path `validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status` mock `publish._api` + `mypy src/`

**Files changed (origin/dev → HEAD, 14 files, +2232/-636):**

- `src/sofer/mcp_server.py` — 1525 lines changed (signatures, annotations, envelope, auth_status, splits, phased instructions)
- `tests/test_mcp_schema.py` — new 314 lines, 15 tests (TestToolCount, TestDescriptions ×3, TestParamDescriptions ×4, TestAnnotations ×2, TestOutputSchema, TestEnvelope ×3, TestHappyPath)
- `tests/test_mcp_server.py` — migrated 240 lines (envelope/output/14-count, _unwrap helper)
- `tests/fixtures/mcp-happy-path/dataset.toml` + `data.csv` — new fixture
- `README.md`, `README_ES.md` — phased diagram + 14-tool table + Breaking Changes
- `CHANGELOG.md` — +37 migration notes
- `openspec/` — proposal/design/specs/tasks/apply-progress untouched content; verify.md untracked added in apply

**Delivery:** Single PR `feat/mcp-dx-audit-surface` → `dev` (auto-forecast, Medium risk, budget 5000, est ~500 single-commit) — no chained PRs. Branch commit `3068aa9` already pushed to `origin/feat/mcp-dx-audit-surface`, up-to-date. `CHANGELOG.md` and READMEs already updated in apply phase per task input — no further doc edit in archive.

## Verification Verdict — PASS_WITH_WARNINGS

**Verdict**: `pass_with_warnings` (v1 schema `gentle-ai.verify-result/v1`, evidence_revision `sha256:44d1b6a...`)

| Metric | Value |
|--------|-------|
| Tasks total / complete | 16 / 16 |
| Requirements | 7/7 |
| Scenarios | 10/10 |
| Test command | `uv run pytest tests/ -q` → 1232 passed, 2 skipped, 0 failed, exit 0 |
| Build command | `uv run mypy src/` → Success 29 files, exit 0 |
| Linter | `uv run ruff check src tests` → All checks passed |
| Blockers / critical_findings | 0 / 0 |
| Coverage | Not gated (none configured) |

**Spec Compliance Matrix (7 req → 10 scenarios, all COMPLIANT):**

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Tool roster 14 tools (10.1/10.5/10.6/10.7) | Constrained schemas: count 14, target Literal, no all_files/no_checks/bare output, every param description non-empty | `TestToolCount::test_fourteen_tools` + `TestParamDescriptions::test_every_param_has_description` + `test_no_legacy_params` + `test_target_enum` (const) + live 14/14 non-empty | ✅ |
| Tool roster 14 tools | Annotations and output_schema typed | `TestAnnotations::test_annotations_present` + `TestOutputSchema::test_output_schema_typed` + live readOnlyHint all 14 | ✅ |
| Single error envelope 10.3 | Refusal returns envelope with next (PUBLISH_RISK_NOT_ACKD) | `TestEnvelope::test_publish_risk_envelope` + `test_refusal_envelope` + live `sofer_publish_confirm(acknowledge_risk=false)` → `error_code=PUBLISH_RISK_NOT_ACKD` | ✅ |
| Single error envelope 10.3 | Containment still throws PathOutsideRootError | `TestInitTraversal` + `TestMcpProfileRenderBatch::test_containment_*` + live `sofer_validate('/etc/passwd')` throws | ✅ |
| Chain learnable 10.4 | Chain visible without prompts/list | `TestDescriptions::test_phased_instructions` + live `build_server().instructions` contains Phase 0/1/2 + all 14 tools Requires:/Next: | ✅ |
| Auth status 10.8 | Preflight without publish | `TestAnnotations::test_auth_status_readonly` + `TestEnvelope::test_auth_status_no_leak` + live `sofer_auth_status` no leak | ✅ |
| Bootstrap Phase 0 10.x | Greenfield phrasing zero Not part of canonical | `TestDescriptions::test_bootstrap_phrasing_no_not_part` + live grep 0 + Phase 0 count 6 | ✅ |
| Live happy path 10.11 | Fixture chain offline each ok:true dry_run true | `TestHappyPath::test_offline_happy_path` + fixtures with mocked `_api` | ✅ |
| Docs sync 10.12 | READMEs in sync phased diagram | `TestBuildClarityReadme` + manual both contain diagram, 14-tool tables, CHANGELOG | ✅ |
| Tool safety 10.10 | Descriptions concise + UNTRUSTED single-sourced | `TestDescriptions::test_descriptions_concise_no_msp_untrusted` + live 14 no MSP-R/CF/UNTRUSTED, instructions UNTRUSTED==1 | ✅ |

**WARNINGS (non-blocking, accepted for archive):**

- **W1 — target `const` not `enum`**: `Literal["local"]`/`Literal["hf"]` via `Annotated` renders as FastMCP `{"const":"local"}` / `{"const":"hf"}` not `{"enum":["local"]}`. Semantically stricter (const ≡ single-value enum) and agent-correct, but spec scenario literal `has(enum)` fails. Impact none. **Recommendation accepted**: treat `const` as compliant; no code change for archive. Future: tighten test to accept `const`/`enum`.
- **W2 — README_ES `Fase 0` translation**: `README_ES.md` has `Fase 0 Bootstrap [condicional: REQUERIDO si greenfield]` per AGENTS.md §13 (Spanish prose, English technical content stays English: commands, flags, TOML). Grep `Phase 0` fails on ES but intent met (headings/order sync, phased diagram structure identical). **Accepted**: update task grep to `Phase 0|Fase 0` if needed; intent proven.

**SUGGESTIONS (post-archive follow-ups):**

- S1 tightening `test_target_enum` fallback, S2 enforcing ≤4 sentences, S3 README UNTRUSTED count 2 vs instructions 1 (docs hygiene not violation), S4 prompt-less integration test for chain — none block archive.

**Coherence**: All 7 design decisions followed (surface-only boundary frozen 254-595, Annotated+Field+Literal, split *_all mirroring codebook, clean break no shim, envelope primary+auth_status secondary, single PR, sofer_build deferred).

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-server` | Updated | **2 MODIFIED** — MSP-R03 Tool roster and schema contract (10 callables/8 logical → 14 callables: Added sofer_profile_all, sofer_render_all, sofer_auth_status; Annotated Field non-empty, target Literal enum const, output→output_file/dir split, all_files removed, no_checks→run_checks, annotations + typed output_schema; 2 scenarios constrained schemas + annotations/output_schema) + MSP-R04 Tool safety contract (~280-word walls + 11× UNTRUSTED → ≤3 sent + When to use/Example + Requires/Next, no MSP-R/CF/UNTRUSTED per tool, UNTRUSTED exactly once in instructions; 1 scenario concise+single-sourced) |
| `mcp-server` | Appended | **5 ADDED** — Single error envelope 10.3 (8 error_code + next + config_errors, 2 scenarios refusal+containment) + Chain learnable 10.4 (phased Bootstrap→Build→Publish diagram + Requires/Next, 1 scenario) + Auth status 10.8 (sofer_auth_status readOnlyHint, 1 scenario preflight) + Bootstrap Phase 0 conditional canonical (init→scan REQUIRED if greenfield, removal Not part of canonical, 1 scenario) + Live happy path + docs sync 10.11/10.12 (fixtures + TestHappyPath + README sync, 2 scenarios) |

**Merge contract**: MODIFIED → replaced matching requirement preserving all other requirements (MSP-R01,R02,R05-R12 preserved verbatim with existing archived/modified provenance); ADDED → appended after MSP-R12 in delta order; no REMOVED/RENAMED; no duplication; provenance updated: modified add `Modified by mcp-dx-audit-surface (2026-08-31)`, added add `Added by change mcp-dx-audit-surface (archived 2026-08-31)`. Existing IDs preserved.

### Main specs updated

- `openspec/specs/mcp-server/spec.md` — now contains updated MSP-R03 + MSP-R04 + 5 added requirements (10.3,10.4,10.8,Phase0,10.11/10.12). Total: 12 original (R01-R12 with R02 still showing feat-mcp-auto-install mod) → now 17 requirements (12 updated + 5 added). All preserved requirements verified via grep.

## Archive Contents

- `proposal.md` ✅ (intent tools/list must teach chain, Bootstrap Phase 0 conditional canonical, safety core surface-only, schema/envelope/chain/naming/sync scope, out-of-scope sofer_build deferred, 4-phase approach P1-P4, risks, rollback revert branch, dependencies fastmcp 3.4)
- `explore.md` ✅ (ex `exploration.md` equivalent — 11 tools live introspection zero descriptions/no annotations/generic schema, safety core PASS containment/ladder/token, chain FAIL prompts-only, 17/17 claims confirmed, 4 alternatives evaluated, affects mcp_server.py + specs + READMEs)
- `specs/mcp-server/spec.md` ✅ (delta — 5 ADDED + 2 MODIFIED, 10.3-10.12, strict clean break pre-1.0)
- `design.md` ✅ (surface-only refactor mcp_server.py, decisions surface boundary A, Annotated+Literal A, split *_all A, clean break A, envelope+auth_status A, run_checks normalize, single branch; data flow phased diagram; 5 file changes; interfaces 14 tools + error envelope + FastMCP pattern; testing 4 layers)
- `tasks.md` ✅ (16/16 tasks complete, Review Workload Forecast Medium single PR, 4 phases P1-P4 with file/estimate/verify per task)
- `apply-progress.md` ✅ (16/16 P1-P4 complete, files changed list, verification pytest 1232/mypy/ruff/jq, next sdd-verify→sdd-archive)
- `verify.md` ✅ (PASS_WITH_WARNINGS — completeness, build/tests, compliance matrix 10/10, correctness matrix 14 checks, coherence, W1/W2 warnings, S1-S4 suggestions, verdict pass_with_warnings)
- `archive.md` ✅ (this file — preflight, lineage, gate, implementation, verification, specs synced, contents, source of truth, next steps, risks)

Active changes directory no longer has this change after move — verified via `openspec/changes/archive/2026-08-31-mcp-dx-audit-surface/` existence and absence at active path.

## Source of Truth Updated

The following specs now reflect the new behavior and are the authoritative source for future changes:

- `openspec/specs/mcp-server/spec.md` — MSP-R03, MSP-R04, plus 5 new requirements (10.3 Single error envelope, 10.4 Chain learnable, 10.8 Auth status, Bootstrap Phase 0, 10.11/10.12 Fixtures+docs sync). Future deltas MUST NOT re-introduce `output` bare, `all_files`, `no_checks`, or `Not part of canonical` without a new spec.

## Project Config Updated

- `openspec/project.md` — not changed (no structural note change; mcp_server still thin adapter, 14 tools now; testing line could be bumped to 1232 passed but left to next init reconciliation — not required for archive)
- `openspec/config.yaml` — unchanged (no archive rule trigger; `rules.archive: Warn before merging destructive deltas` respected — merge not destructive, warnings documented)
- `CHANGELOG.md` — Breaking Changes migration present from apply (output_* / run_checks / *_all) — authoritative in repo

## README / Docs Sync

- `README.md` + `README_ES.md` already synced in apply (phased diagram Phase 0 Bootstrap conditional REQUIRED if greenfield → Phase 1 Build `validate→prepare→codebook_all→profile_all→render_all` → Phase 2 Publish `publish(dry_run)→STOP→publish_confirm` 4-gate; 14-tool table; Breaking Changes box; Spanish prose Fase 0 per §13) — confirmed via grep `Phase 0` in README.md count 6, `Fase 0` in README_ES.md, both contain `sofer_auth_status` + `sofer_profile_all`/`sofer_render_all` + `output_file`/`output_dir` + `run_checks`; `Not part of canonical` count 0 across both + mcp_server.py instructions ✅ no further edit in archive per task input ("READMEs and CHANGELOG already updated in apply phase")
- Spec and README stay in lockstep (chain taught via tools/list + instructions, not prompts/docs alone)

## Verification post-sync

- Main spec contains new requirements (grep `Single error envelope`, `Chain learnable`, `Auth status preflight`, `Bootstrap Phase 0`, `Live happy path fixtures` each ≥1) ✅
- Modified requirements present singletons (single MSP-R03, single MSP-R04) — grep count `### Requirement: Tool roster` ==1, `### Requirement: Tool safety contract` ==1 ✅
- Existing requirements preserved (MSP-R01,R02,R05-R12) — each grep ==1 ✅
- No duplicated requirement headers, no `Not part of canonical` in main spec (count 0, replaced with Phase 0 language) ✅
- ADDED count 5, MODIFIED count 2, total mcp-server requirements 17 ✅
- Change folder moved to `openspec/changes/archive/2026-08-31-mcp-dx-audit-surface/` ✅
- Archive contains all 8 artifacts (proposal, explore, specs, design, tasks, apply-progress, verify, archive) ✅
- Active `openspec/changes/mcp-dx-audit-surface/` no longer exists ✅
- Engram archive-report saved with lineage IDs ✅ (this save)
- `git diff --stat HEAD` shows main spec + archive move as only remaining untracked/moved work beyond already-committed `3068aa9` (verify.md + archive.md + spec sync) — ready for human review before merge

## Next Steps — Human Review + Merge (DO NOT AUTO-MERGE)

Per task: **DO NOT merge PR — leave open for human review**.

1. **Review PR #112**: https://github.com/emiliodavola/sofer/pull/112 (`feat/mcp-dx-audit-surface` → `dev`) — 14 files, +2232/-636, single commit `3068aa9` + archived spec sync + this archive report. Verify: `uv run pytest tests/ -q` (1232 passed), `uv run mypy src/` (Success), `uv run ruff check src tests` (All checks), `Not part of canonical` 0, `Phase 0` in instructions, 14 tools, `output_file`/`output_dir`, no `all_files`/`no_checks`, `const` vs `enum` accepted.
2. **Merge PR**: human `gh pr view 112`, approve, `gh pr merge 112 --squash` or via GitHub UI (commit message already `feat(mcp): make canonical chain learnable from tools/list (14 tools, envelope, auth_status)` — do NOT add Co-Authored-By per AGENTS.md). Ensure `Closes #111` links.
3. **Close #111**: After merge, `gh issue close 111` or auto via Closes. Do NOT close before merge — issue stays open while PR ready/not merged.
4. **Post-merge hygiene**: Delete branch `feat/mcp-dx-audit-surface` remotely after merge if not auto-deleted; verify `openspec/specs/mcp-server/spec.md` on `dev` reflects merged state (17 reqs).
5. **Follow-ups (non-blocking)**: Address suggestions S1-S4 and warnings W1-W2 in next iteration if desired — tighten `test_target_enum` to assert `const`/`enum`, cap description sentences ≤4, keep prompt-less chain integration test; no immediate code change required.

**Delivery strategy note**: `auto-forecast` Medium risk single PR delivered; next change `feat/mcp-build-clarity` remains independent (deferred sofer_build atom) — do not conflate.

## Risks / Follow-ups

- **W1 const vs enum** — accepted; spec validated via implementation. If future reviewer requires `enum` literal, adapt `mcp_server` to emit `enum` or update spec/test to accept `const`. Non-blocking for archive.
- **W2 Fase 0 translation** — accepted per AGENTS.md §13; verification script grep should accept `Phase 0|Fase 0`. Non-blocking.
- **S1-S4** — see verification suggestions; consider in next change `feat/mcp-build-clarity` or a test-hardening follow-up; none block merge.
- **No CRITICAL issues**; rollback via `git revert 3068aa9` + revert spec sync + restore archived folder if needed (no DB, no network).
- **Token/phrase never logged** — `_get_hf_token` + `hmac.compare_digest` preserved; envelope does not leak values — verified.
- No deps added; `fastmcp>=3.4,<4` remains in `dependencies` (via feat-mcp-auto-install).

---

*Archive performed by sdd-archive sub-agent, auto mode, hybrid store (both), single PR delivery (~2232 diff lines, budget 5000). No git tag or version bump per AGENTS.md §12 (tag-driven release is manual). PR #112 remains open for human review/merge; issue #111 remains open until merged.*

*Skill resolution: paths-injected — `sdd-archive` (+ `_shared/sdd-phase-common`, `openspec-convention`, `engram-convention`, `sdd-status-contract`) loaded via `skill()` tool per orchestrator Skills to load before work block.*
