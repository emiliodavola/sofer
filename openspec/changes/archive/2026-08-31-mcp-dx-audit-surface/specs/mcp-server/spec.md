# Delta for mcp-server

## ADDED Requirements

### Requirement: Single error envelope with error_code enum (10.3)
System MUST return expected failures as `{"ok":false,"error_code":E,"message":str,"next":obj,"config_errors":[...]}` and MUST NOT throw `McpError` for them; only transport/containment MAY throw typed `PathOutsideRootError`/`PublishRefusedError`. `error_code` MUST be `CONFIG_ERROR|VALIDATION_FAILED|QUALITY_GATE_FAILED|PUBLISH_RISK_NOT_ACKD|PUBLISH_CONFIDENTIAL_NOT_ACKD|PUBLISH_APPROVAL_REQUIRED|PATH_OUTSIDE_ROOT|TARGET_INVALID`.
#### Scenario: Refusal returns envelope with next
- GIVEN `sofer_publish_confirm(acknowledge_risk=false)`
- WHEN executed
- THEN return `ok:false, error_code=PUBLISH_RISK_NOT_ACKD, next={acknowledge_risk:true}` without throw
#### Scenario: Containment still throws
- GIVEN path outside server root
- WHEN any tool/resource called
- THEN raise `PathOutsideRootError` (transport maps to isError)

### Requirement: Chain learnable from tools/list (10.4)
Server `instructions` MUST contain phased diagram `Phase 0 Bootstrap (conditional) → Phase 1 Build → Phase 2 Publish` and each tool description MUST include `Requires:` and `Next:`. `tools/list` alone SHALL teach `init→scan(if greenfield)→validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→STOP→publish_confirm`.
#### Scenario: Chain visible without prompts/list
- GIVEN `initialize` + `tools/list`
- WHEN inspected without `prompts/list` or README
- THEN `instructions` SHALL contain Bootstrap/Build/Publish headings and each tool SHALL list Requires/Next

### Requirement: Auth status preflight read-only (10.8)
System MUST expose `sofer_auth_status(config)` with `annotations.readOnlyHint:true`, returning `{token:"present"|"missing", confidential:bool, requires_approval_phrase:bool, next:obj}` without leaking token/phrase values or requiring network.
#### Scenario: Preflight without publish
- GIVEN config `confidential=true`, no `HF_TOKEN`
- WHEN `sofer_auth_status(config)` called
- THEN return `token=missing, confidential=true` and `next` lists `acknowledge_risk` and `acknowledge_confidential` steps

### Requirement: Bootstrap Phase 0 conditional canonical
`init→scan` MUST be REQUIRED when no TOML or `[[file]]` empty, OPTIONAL otherwise. Prior `Not part of canonical` phrasing at `mcp_server.py:1283,1347,1430` and in instructions/docs MUST be removed and replaced with Phase 0 wording.
#### Scenario: Greenfield phrasing
- GIVEN `instructions` and scan/init descriptions
- WHEN inspected
- THEN they SHALL state `Phase 0: init→scan REQUIRED for greenfield` and contain zero occurrences of `Not part of canonical`

### Requirement: Live happy path fixtures and docs sync (10.11,10.12)
System MUST ship fixtures `tests/fixtures/mcp-happy-path/` plus offline `tests/test_mcp_schema.py` asserting 10.1/10.2/10.5/10.7/10.10 via `tools/list` and running `validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status` with `publish._api` monkeypatched. `README.md`+`README_ES.md` MUST mirror phased diagram in same commit.
#### Scenario: Fixture chain offline
- GIVEN fixtures present
- WHEN happy-path sequence runs offline
- THEN each step SHALL return `ok:true` and `publish` SHALL be `dry_run:true`
#### Scenario: READMEs in sync
- GIVEN `README.md` and `README_ES.md`
- WHEN inspected
- THEN both SHALL contain Phase 0→1→2 diagram and headings/order SHALL match

## MODIFIED Requirements

### Requirement: Tool roster and schema contract (MSP-R03)
Server SHALL expose 14 callables: `sofer_validate, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init, sofer_auth_status`. Every param SHALL be `Annotated[Field(description)]` non-empty (10.1); `target` SHALL be `Literal["local"]`/`Literal["hf"]` enum (10.5); `output` SHALL split to `output_file` vs `output_dir` (10.7); `all_files` removed — batch via `*_all` (10.6); `no_checks` → `run_checks:bool=true` (10.9); every tool SHALL have `annotations` and typed `output_schema`. (Previously: 11 callables, polymorphic profile/render, free-string target, dual-typed output, bare params, generic schema.)
#### Scenario: Constrained schemas
- GIVEN `tools/list`
- WHEN inspected
- THEN count SHALL be 14, `target` SHALL have `enum`, no tool SHALL expose `all_files`/`no_checks`/`output` (only `output_file`/`output_dir`/`run_checks`), and every `properties[*].description` SHALL be non-empty
#### Scenario: Annotations and output_schema typed
- GIVEN `tools/list`
- WHEN inspected
- THEN no `annotations` SHALL be null and each `output_schema` SHALL declare `ok:bool, exit_code:int, output:str` plus specific fields

### Requirement: Tool safety contract (MSP-R04)
Every tool description SHALL be ≤3 sentences plus `When to use:` (≤1 sentence) and `Example:` single call, SHALL include `Requires`/`Next`, and SHALL NOT contain `MSP-R*`, `CF-*`, or `UNTRUSTED`. `UNTRUSTED` SHALL appear exactly once in server `instructions`, not per-tool (10.10). (Previously: ~280-word walls with MSP refs and 11× UNTRUSTED duplication.)
#### Scenario: Descriptions concise and UNTRUSTED single-sourced
- GIVEN `tools/list` descriptions and `instructions`
- WHEN measured
- THEN pre-`When to use:` sentences SHALL be ≤3, no description SHALL contain `MSP-R` or `UNTRUSTED`, and `instructions` SHALL contain exactly one `UNTRUSTED` occurrence

## REMOVED Requirements
None — renames (`output→output_file/dir`, `no_checks→run_checks`, `all_files→*_all` split) are MODIFIED with clean pre-1.0 break; no shim (CHANGELOG migration).

## RENAMED Requirements
None.
