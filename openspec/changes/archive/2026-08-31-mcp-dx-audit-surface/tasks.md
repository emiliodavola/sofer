# Tasks: mcp-dx-audit-surface

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500 (src 350 + tests 80 + fixtures 20 + docs 50) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR `feat/mcp-dx-audit-surface` → `dev` |
| Delivery strategy | auto-forecast |
| Chain strategy | pending (single-pr; chain only if slice >400) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | PR | Notes |
|------|------|----|-------|
| 1 | P1 surface | PR1 | No-break |
| 2 | P2 envelope | PR1 | Dep 1 |
| 3 | P3 preflight+rename | PR1 | Dep 2 |
| 4 | P4 split | PR1 | Dep 3 |

## Phase 1: P1 Surface — No-Break

- [x] 1.1 Instructions → `Phase 0 → Phase 1 → Phase 2` + single UNTRUSTED | T:refactor D:- S:10.4/10.10 F:`mcp_server.py:1796` E:S V:`pytest -k Instructions` + `jq Phase 0`
- [x] 1.2 Rewrite 11 descriptions ≤3 sent + `When to use:`/`Example:`/`Requires`/`Next`; strip `MSP-R*`/`CF-*` | T:refactor D:1.1 S:10.10 F:`mcp_server.py:637` E:S V:`jq test("MSP-R")==false`
- [x] 1.3 `Annotated[Field(description)]` ~28 params + `Literal["local"/"hf"]` + `annotations` + `output_schema` | T:feature D:1.2 S:10.1/10.5 F:`mcp_server.py` E:S V:`jq length==14 and all(.description!="")`
- [x] 1.4 Fix Bootstrap `Not part of canonical` at 1283,1347,1430 → `Phase 0: init→scan REQUIRED` | T:bugfix D:1.1 S:10.11 F:`mcp_server.py:1274` E:S V:`grep "Not part of canonical"->0`
- [x] 1.5 Create `tests/test_mcp_schema.py` skeleton | T:test D:1.3 S:10.1/10.10 F:`tests/test_mcp_schema.py` E:S V:`pytest -k "not happy" -q`

## Phase 2: P2 Envelope

- [x] 2.1 Add `error_code` enum + envelope `{ok:false,error_code,next,config_errors}` + `_refusal` | T:feature D:P1 S:10.3 F:`mcp_server.py:624` E:M V:`pytest -k Envelope -q`
- [x] 2.2 Wire `publish_confirm` refusals to envelope (`PUBLISH_RISK_NOT_ACKD` etc.); `PathOutsideRootError` still throws | T:feature D:2.1 S:10.3 F:`mcp_server.py:734` E:M V:`pytest -k TestPublishAuthorizationLadder -q`
- [x] 2.3 Envelope tests: bad config, `acknowledge_risk=false`, outside-root throw | T:test D:2.2 S:10.3 F:`tests/test_mcp_schema.py` E:S V:`pytest tests/test_mcp_schema.py tests/test_mcp_server.py -q`

## Phase 3: P3 Preflight + Output Rename

- [x] 3.1 Implement `sofer_auth_status(config)` `readOnlyHint:true` → `{token, confidential, requires_approval_phrase, next}` no leak | T:feature D:P2 S:10.8 F:`mcp_server.py` E:S V:`jq select(.name=="sofer_auth_status")|.annotations.readOnlyHint==true`
- [x] 3.2 Rename `output` → `output_file`/`output_dir` no shim | T:breaking D:3.1 S:10.7 F:`mcp_server.py:679` E:M V:`jq all(has("output")==false)`
- [x] 3.3 Fixtures `tests/fixtures/mcp-happy-path/` TOML+CSV (2 rows `;`) | T:test D:3.2 S:10.11 F:`tests/fixtures/mcp-happy-path/*` E:S V:`ls fixtures/mcp-happy-path ->2`
- [x] 3.4 Expand schema tests: 14 count, enum, no `all_files`/`no_checks`/`output`, typed `output_schema` | T:test D:3.3 S:10.5/10.6/10.9 F:`tests/test_mcp_schema.py` E:S V:`pytest tests/test_mcp_schema.py -q`

## Phase 4: P4 Split + Normalization + Docs

- [x] 4.1 Split `sofer_profile`/`sofer_render` → `sofer_profile_all`/`sofer_render_all`; remove `all_files` | T:breaking D:P3 S:10.6 F:`mcp_server.py:1025` E:M V:`jq length==14 and all(has("all_files")==false)`
- [x] 4.2 Rename `no_checks` → `run_checks:bool=true` | T:breaking D:4.1 S:10.9 F:`mcp_server.py:471` E:S V:`jq all(has("no_checks")==false)`
- [x] 4.3 Sync `README.md`+`README_ES.md` phased diagram + `CHANGELOG.md` migration | T:docs D:4.2 S:10.12 F:`README*.md`+`CHANGELOG.md` E:S V:`grep "Phase 0" README.md README_ES.md`
- [x] 4.4 Offline happy path `validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status` mock `publish._api` + `mypy src/` | T:test D:4.3 S:10.11 F:`tests/test_mcp_schema.py::TestHappyPath` E:S V:`pytest tests/ -q && mypy src/`

