# Design: MCP Build Clarity — prepare→codebook→profile→render

## Technical Approach

Choose **B (prompts/docs only)**. No new MCP tool. Enrich 3 prompts (`prepare_dataset`, `assess_dataset`, `finalize_and_publish`) and `README.md`/`README_ES.md` with canonical order `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm`, per-step args, when-to-use, and copy-paste chaining example. Satisfies delta spec via **MCP-BC01 + MSP-R08**; **MCP-BC02** takes B branch. Thin `sofer_build` deferred — add later only if agent dry-run validation shows chaining still error-prone.

## Architecture Decisions

### Decision: Build orchestration — A vs B vs hybrid

**Choice**: B — prompts/docs only; defer `sofer_build`.

**Alternatives considered**: A (new `sofer_build` atomic adapter); hybrid (B + optional `sofer_build`).

| Option | Tradeoff | Decision |
|--------|----------|----------|
| A: `sofer_build` atomic | Single call; new envelope `{ok, exit_code, output, files, steps}` fail-first + partial; `force` heterogeneous (prepare honors, profile/render batch overwrites, codebook collision partial→`ValueError`); containment drift across 4 domains; +150 LOC + tests; duplicates docs work | **Reject** — maintenance outweighs convenience |
| B: prompts+README clarity | 5 stdio calls (cheap local). Zero new surface; reuses per-tool envelopes; per-step containment isolated; 3 prompts + docs edit | **Accept** — lean, fixes root cause |
| Hybrid | Both; max convenience | **Defer** — only if post-B metrics miss steps |

**Rationale**: Agents think `sofer_prepare` is a full build (only Parquet+Card+optional codebooks). Teaching order covers multisheet dedup (`__sheet`), `profile_dir`/`render_dir` containment, `OUTPUT_DIR` vs `build_dir`. Adapter hides that learning. B covers `assess_dataset` single-file and `finalize_and_publish` dry-run stop; `sofer_build` does not.

### Decision: Prompt/README shape

**Choice**: Each prompt embeds chain, args (`config`/`dataset`/`package`/`output`/`force`/`all_files`), when-to-use, example; README mirrors in AI/MCP section.

**Alternatives considered**: Helper doc without prompt changes; central server instructions only.

**Rationale**: Prompts (`prompts/list`) are agent entry; README is human entry. Both get same canonical block (MCP-BC01/MSP-R08) via `_with_untrusted_note` single source.

### Decision: Deferred sofer_build contract (if later)

**Choice**: Thin adapter over `run_prepare → generate_all_codebooks → generate_all_profiles → generate_all_renders`, no reimpl.

**Alternatives considered**: Reimpl in `mcp_server.py`; bundling profile/render into prepare.

**Rationale**: Preserve sheet/ collision/ delimiter (`cfg.csv_delimiter`/`encoding`) logic. Adapter only propagates `config, output?, force`, enforces `_contained_path` + `_validate_output_targets` per step, aggregates `{ok, exit_code, output, files, steps}`, fail-first partial, never HF upload.

## Data Flow

B chain — prompt-driven:

```
prompts/list → prepare_dataset
Agent ──sofer_validate(cfg)──→ checks/quality
      ──sofer_prepare(cfg,output,force)──→ prepare.py → build/ (Parquet+README+LICENSE; --all-files→build/codebooks)
      ──sofer_codebook_all(cfg,output)──→ generate_all → cache/codebooks or build/codebooks + codebook.md
      ──sofer_profile(all_files,output)──→ generate_all_profiles → write_root/profiles/<rel>.metadata.yaml
      ──sofer_render(all_files,output)──→ generate_all_renders (reads profiles/) → write_root/renders/<rel>.README.md
      ──sofer_publish(dry_run) → STOP → sofer_publish_confirm (HF)
```

Per-step `_tool_execution` + `_capture_output` + `_contained_path`; `generate_all_*` collision → partial then `ValueError`→`{ok:false}`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modify | Rewrite `_prompt_*` (L1372/L1386/L1403) with chain, args, when-to-use, copy-paste; update server instructions + tool docstrings |
| `README.md` | Modify | AI/MCP section: ordered chain, args table, when-to-use, example (`config`, `output`, `all_files=True`, `force`) |
| `README_ES.md` | Modify | Mirror (prose ES, code EN) |
| `prepare.py`, `profile.py`, `render.py`, `codebook.py` | Unchanged | Reused, no fork |
| `mcp_server.py` (A deferred) | Create if later | `sofer_build(config, output?, force)` thin adapter + `_register_tools` |

## Interfaces / Contracts

B adds no tool. Prompt shape (`prepare_dataset`):

```python
# _prompt_prepare_dataset(config, output?)
"Canonical: sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile(all_files) → sofer_render(all_files) → sofer_publish(dry_run) → sofer_publish_confirm\n"
"1. sofer_validate(config={config!r})\n"
"2. sofer_prepare(config={config!r}, output={output!r})\n"
"3. sofer_codebook_all(config={config!r}, output={output!r})\n"
"4. sofer_profile(dataset={config!r}, all_files=True, output={output!r})\n"
"5. sofer_render(package={config!r}, all_files=True, output={output!r})\n"
"When-to-use + copy-paste chain: sofer_validate(...); sofer_prepare(...); ..."
```

Deferred `sofer_build` envelope: `{"ok": bool, "exit_code": int, "output": str, "files": str[], "steps": {prepare:{...}, codebook_all:{...}, profile:{...}, render:{...}}}` — fail-first partial, `force`→prepare, containment per step, no HF.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Prompts have chain, args, when-to-use, example | `build_server()` → `prompts/list` (3) + string asserts; `tools/list` when-to-use |
| Unit | No `sofer_build` in B | `tools/list` excludes it |
| Unit | README chain | Grep ordered chain + `all_files`/`force` example in both READMEs |
| Existing | No regression | `uv run pytest tests/ -q` |

## Migration / Rollout

No migration. Additive docs-only. Rollback `git revert`. Later `sofer_build` is additive without breaking atomics.

## Open Questions

- [x] A/B/hybrid resolved: **B** — prompts/docs only.
- [ ] Gate for A: if agents still miss profile/render after B, promote thin adapter.
