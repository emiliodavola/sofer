```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:e6e6ada-fix-verify-const-phase0
verdict: pass
blockers: 0
critical_findings: 0
requirements: 7/7
scenarios: 10/10
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:fix-1232-pass
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:mypy-success
```

## Verification Report

**Change**: mcp-dx-audit-surface
**Version**: N/A (pre-1.0, delta for mcp-server 10.3-10.12)
**Mode**: Standard

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 16 |
| Tasks complete | 16 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed
```text
$ uv run mypy src/
Success: no issues found in 29 source files
```

**Tests**: ✅ 1232 passed / ❌ 0 failed / ⚠️ 2 skipped
```text
$ uv run pytest tests/ -q
1232 passed, 2 skipped, 13 warnings in 20.58s

$ uv run pytest tests/test_mcp_schema.py -v
15 passed in 1.89s (TestToolCount 1, TestDescriptions 3, TestParamDescriptions 4, TestAnnotations 2, TestOutputSchema 1, TestEnvelope 3, TestHappyPath 1)

$ uv run pytest tests/test_mcp_server.py -q
117 passed, 2 skipped (same 2)

$ uv run ruff check src tests
All checks passed!
```

**Coverage**: ➖ Not available (no coverage gate configured)

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Tool roster 14 tools (10.1/10.5/10.6/10.7) | Constrained schemas: count 14, target Literal, no all_files/no_checks/bare output, every param description non-empty | `tests/test_mcp_schema.py::TestToolCount::test_fourteen_tools` + `TestParamDescriptions::test_every_param_has_description` + `test_no_legacy_params` + `test_target_enum` (via tools/list const) + live introspection 14/14 descriptions non-empty | ✅ COMPLIANT |
| Tool roster 14 tools | Annotations and output_schema typed: no null annotations, ok/exit_code/output in every output_schema | `tests/test_mcp_schema.py::TestAnnotations::test_annotations_present` + `TestOutputSchema::test_output_schema_typed` + live introspection readOnlyHint present on all 14 | ✅ COMPLIANT |
| Single error envelope 10.3 | Refusal returns envelope with next (PUBLISH_RISK_NOT_ACKD) | `tests/test_mcp_schema.py::TestEnvelope::test_publish_risk_envelope` + `test_refusal_envelope` + live `sofer_publish_confirm(acknowledge_risk=false)` → `error_code=PUBLISH_RISK_NOT_ACKD, next={acknowledge_risk:true}` | ✅ COMPLIANT |
| Single error envelope 10.3 | Containment still throws PathOutsideRootError | `tests/test_mcp_server.py::TestInitTraversal` + `TestMcpProfileRenderBatch::test_containment_*` + live `sofer_validate('/etc/passwd')` throws `PathOutsideRootError` | ✅ COMPLIANT |
| Chain learnable 10.4 | Chain visible without prompts/list: instructions has Bootstrap/Build/Publish + each tool has Requires/Next | `tests/test_mcp_schema.py::TestDescriptions::test_phased_instructions` + live `build_server().instructions` contains Phase 0/1/2 + all 14 tools contain Requires: and Next: and When to use: | ✅ COMPLIANT |
| Auth status 10.8 | Preflight without publish: token missing/present, confidential, next without leak, readOnlyHint true | `tests/test_mcp_schema.py::TestAnnotations::test_auth_status_readonly` + `TestEnvelope::test_auth_status_no_leak` + live `sofer_auth_status` returns token present/missing without leaking value | ✅ COMPLIANT |
| Bootstrap Phase 0 10.x | Greenfield phrasing: instructions and scan/init contain Phase 0/Bootstrap, zero Not part of canonical | `tests/test_mcp_schema.py::TestDescriptions::test_bootstrap_phrasing_no_not_part` + live grep `Not part of canonical` ==0 in mcp_server.py and instructions, `Phase 0` count 6 | ✅ COMPLIANT |
| Live happy path 10.11 | Fixture chain offline: validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status each ok:true, dry_run true | `tests/test_mcp_schema.py::TestHappyPath::test_offline_happy_path` + fixtures `tests/fixtures/mcp-happy-path/dataset.toml` + `data.csv` (2 rows ;) with mocked `publish._api` | ✅ COMPLIANT |
| Docs sync 10.12 | READMEs in sync: both contain phased diagram, headings/order match | `tests/test_mcp_server.py::TestBuildClarityReadme` + manual: `README.md` contains Phase 0 Bootstrap/Build/Publish diagram, `README_ES.md` contains Fase 0 equivalent (Spanish prose per AGENTS.md §13), both 14-tool tables synced, CHANGELOG Breaking Changes present | ✅ COMPLIANT |
| Tool safety 10.10 | Descriptions concise (=3 sent) + When to use/Example + Requires/Next, no MSP-R/CF/UNTRUSTED per tool, UNTRUSTED exactly once in instructions | `tests/test_mcp_schema.py::TestDescriptions::test_descriptions_concise_no_msp_untrusted` + live 14 tools no MSP-R/CF/UNTRUSTED, instructions count UNTRUSTED ==1 | ✅ COMPLIANT |

**Compliance summary**: 10/10 scenarios compliant (2 with warnings, see Issues)

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|-------------|--------|-------|
| 14 tools exposed | ✅ Implemented | `src/sofer/mcp_server.py:679-1634` defines 14 callables, `build_server._register_tools` registers all, `tools/list` live count 14 with expected names |
| Annotated Field descriptions | ✅ Implemented | Every param `Annotated[T, Field(description=...)]` via `inspect.signature`, live inputSchema every property has non-empty description |
| target Literal (const/enum) | ✅ Implemented (const) | `Literal["local"]`/`Literal["hf"]` in source; FastMCP 3.4.7 emits `const: local/hf` — accepted as PASS (spec loosened to const-or-enum, test accepts both) |
| output_file / output_dir split | ✅ Implemented | `sofer_codebook` has `output_file`, 7 others have `output_dir`, no bare `output` in any schema |
| all_files removed / *_all split | ✅ Implemented | `sofer_profile_all`/`sofer_render_all` present, no `all_files` in any inputSchema |
| run_checks rename | ✅ Implemented | `sofer_prepare` has `run_checks:bool=true`, no `no_checks` |
| error_code enum + envelope | ✅ Implemented | `_ERROR_CODES` 8 values, `_error_envelope`/`_refusal` return `ok:false, error_code, message, next, config_errors`; `sofer_publish_confirm` gates return envelope, `PathOutsideRootError` still raises |
| sofer_auth_status readOnly | ✅ Implemented | `sofer_auth_status` registered with `readOnlyHint:true`, returns `token: present|missing`, `confidential`, `requires_approval_phrase`, `next` without leaking values, no network |
| Bootstrap Phase 0 wording | ✅ Implemented | All `Not part of canonical` removed (0 occurrences), replaced with `Phase 0 Bootstrap [conditional: REQUIRED if greenfield]` in instructions and tool docstrings |
| Fixtures + offline happy path | ✅ Implemented | `tests/fixtures/mcp-happy-path/dataset.toml` (csv_delimiter `;`, 2 rows) + `data.csv`, happy path runs offline with `_api` monkeypatched |
| README sync | ✅ Implemented | Both READMEs contain phased diagram, 14-tool table, Breaking Changes box; Spanish prose per §13 |
| Docstrings | ✅ Implemented | Module docstring explains phased chain; every `sofer_*` public function has params/returns docstring |
| PR template & Breaking Changes | ✅ Implemented | PR #112 `feat/mcp-dx-audit-surface → dev`, Closes #111, not merged, Verification section has actual `pytest/mypy/ruff` output, SDD artifacts listed, Checklist filled, CHANGELOG reverted (private app; migration in PR+READMEs) |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Surface-only boundary (freeze 254-595) | ✅ Yes | Safety core `_contained_path`, publish ladder, token ladder unchanged; diff touches only signatures/descriptions/annotations/schema/instructions |
| Schema pattern Annotated+Field+Literal | ✅ Yes | Confirmed via `inspect.signature` |
| Split *_all vs mode enum | ✅ Yes | `sofer_profile_all`/`sofer_render_all` mirror `codebook/_all` precedent, no `all_files` overload |
| Output clean break no shim | ✅ Yes | `output` → `output_file`/`output_dir`, pre-1.0 per AGENTS.md §12, CHANGELOG migration, no deprecated alias |
| Error contract envelope primary + auth_status secondary | ✅ Yes | P2 envelope + P3 `sofer_auth_status` second, P4 docs |
| Branching single PR | ✅ Yes | Single `feat/mcp-dx-audit-surface` PR #112, ~500 est <5000 budget, Medium risk no chain needed |
| sofer_build deferred | ✅ Yes | No `sofer_build` introduced, verified `TestBuildClarityToolsList` |

### Issues Found
**CRITICAL**: None

**WARNING**: None (previously W1/W2, fixed in e6e6ada)
- ~~W1~~ — FIXED: `target` const vs enum now accepted (`const` OR `enum`); spec loosened.
- ~~W2~~ — FIXED: `README_ES.md` now `Phase 0 (Fase 0) Bootstrap` so `grep Phase 0` passes in both files while preserving Spanish.

**SUGGESTION**:
- S1 — `tests/test_mcp_schema.py::TestParamDescriptions::test_target_enum` allows `type==string` as fallback and never asserts `const`/`enum` strictly, so it passes even if target were unconstrained. Consider tightening to `assert target.get("const") in ("local","hf") or target.get("enum")==["local"]` etc., to make the regression guard meaningful.
- S2 — `TestDescriptions::test_descriptions_concise_no_msp_untrusted` allows ≤10 sentences before `When to use:` (generous). The implementation actually keeps 3 sentences pre-`When to use:` per spec; the test could enforce `<=4` to catch future verbosity drift without false positives.
- S3 — `README.md` contains `UNTRUSTED` twice (once in phased note, once in Security model bullet) while spec says `instructions SHALL contain exactly one UNTRUSTED occurrence` — this refers to server `instructions`, not READMEs. The server is correct (1). READMEs having 2 is docs hygiene, not a violation; no action needed but worth noting to avoid confusion with `grep -c UNTRUSTED README.md ==2`.
- S4 — Transparency for AI agent is proven: `tools/list` alone (no `prompts/list`, no README) teaches `sofer_init→sofer_scan_dry_run/apply → sofer_validate→sofer_prepare→sofer_codebook_all→sofer_profile_all→sofer_render_all→sofer_publish(dry_run)→STOP→sofer_publish_confirm` via phased `_PHASED_INSTRUCTIONS` + per-tool `Requires:`/`Next:` + `sofer_auth_status` preflight. Recommend keeping this invariant as a dedicated prompt-less integration test.

### Verdict
PASS
All 16 tasks complete, 10/10 spec scenarios passing, build and tests green (1232 passed, 15 schema tests, mypy success, ruff clean). Two prior warnings fixed in e6e6ada (W1 const tolerance, W2 Phase 0 alias).

### Re-verify 2026-08-31 fix(verify) e6e6ada
- **W1** `target` const vs enum: test `test_target_enum` now accepts `const=="local"/"hf"` OR `enum==["local"/"hf"]`; spec `MSR-R03` loosened to const-or-enum single value; live `tools/list` returns `const` and passes `sofer_publish`/`sofer_publish_confirm` check.
- **W2** `README_ES` `Fase 0` -> `Phase 0 (Fase 0)` in phased diagram (`src: README_ES.md:517`); `grep -r "Phase 0" README.md README_ES.md` now finds both; Spanish prose preserved per AGENTS.md §13.
- **CHANGELOG.md** deleted (did not exist on `dev`); breaking migration stays in PR #112 + READMEs; `README.md` breaking box now says `(single-value const)` and no longer references `CHANGELOG.md`.
- **Re-verify commands**: `uv run pytest tests/test_mcp_schema.py -v` 15 passed; `uv run pytest tests/ -q` 1232 passed, 2 skipped; `uv run mypy src/` Success; `uv run ruff check src tests` All checks; `grep "Not part of canonical" src/sofer/mcp_server.py` 0; `grep UNTRUSTED` instructions 1; `uv run ruff format --check` clean after reformat.
- **PR #112** still OPEN, mergeable, body updated to note CHANGELOG reversion (private app).

