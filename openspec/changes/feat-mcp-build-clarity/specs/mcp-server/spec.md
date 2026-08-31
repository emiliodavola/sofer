# Delta for mcp-server

## MODIFIED Requirements

### Requirement: Prompts (MSP-R08)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

The server SHALL expose 3 workflow templates — `prepare_dataset`, `assess_dataset`, `finalize_and_publish` — encoding canonical order `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm`. Each prompt SHALL state per-step args (`config`, `dataset`/`package`, `output`, `force`), when-to-use guidance, and a copy-paste chaining example in canonical order. `prepare_dataset` and `assess_dataset` SHALL sequence `sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile(all_files) → sofer_render(all_files)` (or documented subset) without source reads. Any publish step SHALL require `sofer_publish(dry_run=True)` then stop for human approval before `sofer_publish_confirm`.
(Previously: only validate→prepare idiom without canonical order, per-step args, when-to-use, or chaining examples.)

#### Scenario: Prompt list shows 3 templates

- GIVEN the server running
- WHEN `prompts/list` is called
- THEN exactly 3 prompts SHALL be returned

#### Scenario: Confirm-before-publish idiom enforced

- GIVEN each prompt template
- WHEN inspected
- THEN every HF-publish step SHALL mandate a human-approval stop before confirm

#### Scenario: prepare_dataset exposes canonical order and chaining example

- GIVEN `prepare_dataset` prompt with `config="ds.toml"`
- WHEN template inspected
- THEN it SHALL list `sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile → sofer_render` in order
- AND include a copy-paste chain with `config`, `output`, `all_files=True`

#### Scenario: assess_dataset exposes order and when-to-use

- GIVEN `assess_dataset` prompt
- WHEN inspected
- THEN it SHALL state when to use assess vs `prepare_dataset` and sequence `sofer_validate → sofer_profile(dataset) → sofer_render(package=dataset)` noting the full chain

#### Scenario: finalize_and_publish exposes full chain to dry-run

- GIVEN `finalize_and_publish` prompt
- WHEN inspected
- THEN it SHALL sequence `validate → prepare → codebook_all → profile → render → sofer_publish(dry_run=True)` and stop before confirm

## ADDED Requirements

### Requirement: Canonical build documentation and when-to-use (MCP-BC01)

Prompt descriptions and `README.md`/`README_ES.md` SHALL document canonical order `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm`, per-tool args, and when to use each atomic tool vs the full chain. Docs alone SHALL NOT imply a new tool.

#### Scenario: README documents canonical chain

- GIVEN `README.md` (and mirrored `README_ES.md`)
- WHEN MCP/AI section inspected
- THEN it SHALL contain the ordered chain and a copy-paste example with `config` and `all_files`/`output`/`force`

#### Scenario: Tool docs state when-to-use

- GIVEN `tools/list` descriptions
- WHEN inspected
- THEN each SHALL state side effects and when to use that tool vs the full sequence

### Requirement: Conditional build orchestration sofer_build (MCP-BC02)

Conditional on design decision. If **B (docs/prompts only)**, no new tool SHALL be added; sequencing is satisfied by MSP-R08 + MCP-BC01. If **A or hybrid**, the system SHALL expose `sofer_build` as thin adapter over `run_prepare → generate_all_codebooks → generate_all_profiles → generate_all_renders` with no reimplemented logic, preserving atomics. When present, `sofer_build` SHALL accept `config: str, output: str|None, force: bool=False`, propagate `force`, enforce per-step server-root containment, aggregate into envelope `{"ok": bool, "exit_code": int, "output": str, "files": str[], "steps": {...}}`, fail on first error with partial `files`/`steps`, and never perform HF upload or implicitly bundle profile/render into prepare.

#### Scenario: B selected — no sofer_build

- GIVEN design decision is B
- WHEN `tools/list` is called
- THEN `sofer_build` SHALL NOT appear

#### Scenario: A/hybrid selected — sofer_build appears

- GIVEN design decision is A or hybrid
- WHEN `tools/list` is called
- THEN `sofer_build` SHALL appear with schema `{config, output, force}` and per-step containment

#### Scenario: Partial-failure envelope

- GIVEN `sofer_build` where profile step fails
- WHEN called
- THEN result SHALL be `{"ok": false, "files": [...partial...], "steps": {"prepare": {...}, "codebook_all": {...}, "profile": {"ok": false}}}` and no later step SHALL run

#### Scenario: Force propagation and containment

- GIVEN existing artifacts and `sofer_build(config, force=False)` then `force=True`
- WHEN each is called
- THEN first SHALL refuse overwrite, second SHALL regenerate, both respecting server-root containment
