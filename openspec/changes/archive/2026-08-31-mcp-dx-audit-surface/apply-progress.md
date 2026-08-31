# Apply Progress — mcp-dx-audit-surface

## Status: 16/16 complete — Ready for verify

### P1 Surface — No-Break
- [x] 1.1 Instructions → Phase 0 → Phase 1 → Phase 2 + single UNTRUSTED — `src/sofer/mcp_server.py` _PHASED_INSTRUCTIONS, `build_server` instructions
- [x] 1.2 Rewrite 11+3 descriptions ≤3 sent + When to use/Example/Requires/Next; strip MSP-R*/CF-* — all 14 tools, details removed, Requires/Next in each docstring
- [x] 1.3 Annotated[Field(description)] ~28 params + Literal["local"/"hf"] + annotations + output_schema — every param Annotated, target Literal, _register_tools with annotations/output_schema typed
- [x] 1.4 Fix Bootstrap phrasing at scan/init — replaced "Not part of canonical" with "Phase 0 Bootstrap, conditional canonical"
- [x] 1.5 Create tests/test_mcp_schema.py skeleton — 15 tests covering 14 count, enum, no legacy, annotations, output_schema, UNTRUSTED, phased, envelope

### P2 Envelope
- [x] 2.1 Add error_code enum + envelope {ok:false,error_code,next,config_errors} + _refusal helper — _ERROR_CODES, _error_envelope, _refusal with quality before token stays
- [x] 2.2 Wire publish_confirm refusals to envelope (PUBLISH_RISK_NOT_ACKD etc.); PathOutsideRootError still throws — all gates return envelope, containment raises
- [x] 2.3 Envelope tests — TestEnvelope in test_mcp_schema.py and updated test_mcp_server.py

### P3 Preflight + Output Rename
- [x] 3.1 Implement sofer_auth_status(config) readOnlyHint:true — returns {token:"present"|"missing", confidential, requires_approval_phrase, next} never leaks
- [x] 3.2 Rename output → output_file/output_dir no shim — clean break pre-1.0
- [x] 3.3 Fixtures tests/fixtures/mcp-happy-path/ TOML+CSV (delim ;) 2 rows — created dataset.toml + data.csv
- [x] 3.4 Expand schema tests: 14 count, enum, no all_files/no_checks/output, typed output_schema — TestToolCount, TestParamDescriptions, TestAnnotations, TestOutputSchema

### P4 Split + Normalization + Docs
- [x] 4.1 Split sofer_profile/sofer_render → sofer_profile_all/sofer_render_all; remove all_files — 14 tools, no all_files in any schema
- [x] 4.2 Rename no_checks → run_checks:bool=true — sofer_prepare now run_checks
- [x] 4.3 Sync README.md+README_ES.md phased diagram + CHANGELOG.md migration — both READMEs updated with 14-tool table, phased diagram, Breaking Changes box; CHANGELOG.md created
- [x] 4.4 Offline happy path validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status mock publish._api + mypy src/ — TestHappyPath passes, mypy src/ Success, ruff check src tests passes

### Verification
- `uv run pytest tests/ -q` → 1232 passed, 2 skipped
- `uv run pytest tests/test_mcp_schema.py -q` → 15 passed
- `uv run mypy src/` → Success: no issues found in 29 source files
- `uv run ruff check src tests` → All checks passed (after format)
- `jq` on tools/list → 14 tools, every param description non-empty, target enum, no all_files/no_checks/output, annotations readOnlyHint present, output_schema typed

### Files Changed
- `src/sofer/mcp_server.py` — 14 tools, Annotated, Literal, annotations, output_schema, phased instructions, envelope, auth_status, output split, run_checks, profile/render split
- `tests/test_mcp_server.py` — migrated 29 tests to new envelope/output/14-count, added _unwrap helper
- `tests/test_mcp_schema.py` — new 15 tests
- `tests/fixtures/mcp-happy-path/` — new fixture
- `README.md`, `README_ES.md` — phased diagram + 14-tool table + Breaking Changes
- `CHANGELOG.md` — new migration notes
- `openspec/changes/mcp-dx-audit-surface/tasks.md` — marked complete

### Next
- sdd-verify → sdd-archive
