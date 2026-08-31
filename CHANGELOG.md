# Changelog

## [Unreleased] — MCP DX Audit Surface (feat/mcp-dx-audit-surface)

### Breaking Changes (pre-1.0, minor bump)
- **MCP tool params renamed (clean break, no shim):**
  - `output` → `output_file` (sofer_codebook single file) / `output_dir` (sofer_codebook_all, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all)
  - `no_checks` → `run_checks: bool = true` (sofer_prepare)
  - `sofer_profile` / `sofer_render` split: new `sofer_profile_all(config)` and `sofer_render_all(config)` for batch; single-file tools keep `dataset`/`package` and lose `all_files` + `config` overload; `all_files` removed globally
  - `target` is now `Literal["local"]` for `sofer_publish` and `Literal["hf"]` for `sofer_publish_confirm` (enum in JSON Schema)
- **14 tools (was 11):** new `sofer_profile_all`, `sofer_render_all`, `sofer_auth_status`
- **Error contract:** expected failures now return `{ok:false, error_code, message, next, config_errors}` instead of throwing `McpError`/`PublishRefusedError`; only `PathOutsideRootError` (containment) still throws. `error_code` enum: `CONFIG_ERROR | VALIDATION_FAILED | QUALITY_GATE_FAILED | PUBLISH_RISK_NOT_ACKD | PUBLISH_CONFIDENTIAL_NOT_ACKD | PUBLISH_APPROVAL_REQUIRED | PATH_OUTSIDE_ROOT | TARGET_INVALID`
- **Migration:**
  ```python
  # before
  sofer_prepare(config="ds.toml", output="./out", no_checks=True, all_files=False)
  sofer_profile(dataset="ds.toml", all_files=True, output="./out")
  sofer_codebook(path="data.csv", output="./cb.md")
  # after
  sofer_prepare(config="ds.toml", output_dir="./out", run_checks=False)
  sofer_profile_all(config="ds.toml", output_dir="./out")
  sofer_codebook(path="data.csv", output_file="./cb.md")
  ```

### Added
- **Phased instructions:** server `instructions` now contains `Phase 0 Bootstrap [conditional: REQUIRED if greenfield]` → `Phase 1 Build` → `Phase 2 Publish` diagram; each tool has `Requires:` / `Next:` so `tools/list` alone teaches `init→scan→validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→STOP→publish_confirm`
- **`sofer_auth_status(config)`** (`readOnlyHint:true`): `{token:"present"|"missing", confidential, requires_ack_confidential, requires_approval_phrase, next}` — no token/phrase leak, no network, preflight before `publish_confirm`
- **Schema:** every param is `Annotated[Field(description)]` (LLM-visible), `target` enum, per-tool `annotations` (`readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint`), typed `output_schema` (`ok`, `exit_code`, `output` plus specific fields)
- **Fixtures:** `tests/fixtures/mcp-happy-path/` (TOML + CSV 2 rows `;`) and offline `tests/test_mcp_schema.py` (14 tools, enum, no legacy params, annotations, output_schema, single UNTRUSTED, Bootstrap wording, envelope, happy path with mocked `publish._api`)

### Changed
- **Tool descriptions:** ≤3 sentences + `When to use:` / `Example:` / `Requires:` / `Next:`; no `MSP-R*`/`CF-*`/`UNTRUSTED` per tool (moved single `UNTRUSTED` to `instructions`); Bootstrap phrasing `Not part of canonical` → `Phase 0: init→scan REQUIRED for greenfield`
- **Publish ladder:** quality gate before token check stays; `publish_confirm` refusals now envelope with `error_code` + `next` (`PUBLISH_RISK_NOT_ACKD→{acknowledge_risk:true}` etc.); `PathOutsideRootError` still throws
- **README.md / README_ES.md:** synced phased diagram, 14-tool table, canonical chain one-liner, Bootstrap Phase 0 note, Breaking Changes migration box

### Docs
- `src/sofer/mcp_server.py` module docstring now explains phased diagram; every public function carries params/returns docstring
