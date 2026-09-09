# Proposal: MCP Build Clarity — prepare→codebook→profile→render

## Intent

MCP agents see `sofer_prepare` as a full build but it only does Parquet+Card+optional codebooks. `profile`/`render` are separate calls. Prompts `prepare_dataset` (L1372) and `assess_dataset` (L1386) don't state the canonical order, so agents chain 3 calls without guidance. UX/orchestration gap, not a generation bug. Need explicit sequencing or atomic orchestration without breaking atomics.

## Scope

### In Scope
- Evaluate A vs B vs hybrid; decision deferred to design.
- A candidate: `sofer_build` → `prepare → codebook_all → profile(all_files) → render(all_files)` atomically, unified envelope, `force` propagation, per-step containment, partial-failure reporting.
- B: clarify prompts + docs — update `prepare_dataset`/`assess_dataset`/`finalize_and_publish` and `README.md`/`README_ES.md` with canonical `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm` and per-step args/examples.
- Keep atomic tools if A is added; no change to `prepare` semantics.

### Out of Scope
- Implicit profile/render inside `sofer_prepare`.
- Domain logic changes to profile/render/codebook/Parquet.
- HF upload inside build; new transports.

## Capabilities

### New Capabilities
- `mcp-build-orchestration`: atomic `sofer_build` (conditional — only if design selects A/hybrid).

### Modified Capabilities
- `mcp-server`: prompt sequencing, tool ordering guidance, chaining examples (required under any option).

## Approach

Compare A/B/hybrid on UX, maintenance, partial-failure cost. Lean: **B or hybrid-light** — fix prompts/docs first; add `sofer_build` only if chaining stays error-prone. If A: thin adapter over `run_prepare`/`generate_all_codebooks`/`generate_all_profiles`/`generate_all_renders`, no reimpl; aggregate `files`, fail on first error with partial envelope; honor `force`; reuse validation/containment.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modified | Prompts L1372/L1386/L1403; optionally `sofer_build` + `_register_tools` |
| `openspec/specs/mcp-server/spec.md` | Modified | Sequencing + prompt contracts |
| `README.md`, `README_ES.md` | Modified | Workflow + MCP chaining docs |
| `prepare.py`, `profile.py`, `render.py` | Unchanged | Reused, not forked |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| A envelope/partial-failure complexity | Med | Keep B viable; A aggregates existing envelopes only; design gate |
| B still leaves missed steps | Med | Explicit sequence + copy-paste example chain; agent dry-run validation |
| `force`/containment drift | Low | Single `force` propagated; reuse per-tool guards; tests |

## Rollback Plan

Revert prompt edits or unregister `sofer_build`; atomics remain. No migration. Git revert.

## Dependencies

- Tools: `sofer_validate`, `sofer_prepare`, `sofer_codebook_all`, `sofer_profile(all_files)`, `sofer_render(all_files)`.
- Config `profile_dir`/`render_dir` containment.

## Success Criteria

- [ ] Design decision (A/B/hybrid) recorded with tradeoff rationale.
- [ ] Prompts expose canonical sequence without reading source.
- [ ] If B: order, args, when-to-use and example chain in prompts+README.
- [ ] If A: atomic, idempotent with `force`, partial-failure envelope, atomics preserved.
- [ ] No breaking change to existing MCP tools.
