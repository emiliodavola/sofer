# Tasks: MCP Build Clarity — prepare→codebook→profile→render

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~280–350 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (prompts + docs + tests) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Prompts + server instructions + tool docs + README/ES + tests — full B branch | PR 1 → feat/mcp-build-clarity → main | Single autonomous slice; no sofer_build |

## Phase 1: Prompts — canonical chain in `src/sofer/mcp_server.py`

- [x] 1.1 Rewrite `_prompt_prepare_dataset(config, output?)` (L1372) — via `_with_untrusted_note` embed canonical `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm`, per-step args (`config`, `output`, `all_files=True`, `force`), when-to-use vs `assess_dataset`, and copy-paste chain with `config`/`output` interpolation
- [x] 1.2 Rewrite `_prompt_assess_dataset(config, dataset)` (L1386) — state when-to-use `assess_dataset` vs `prepare_dataset`, sequence `sofer_validate → sofer_profile(dataset) → sofer_render(package=dataset)` and note full chain; keep `_with_untrusted_note`
- [x] 1.3 Rewrite `_prompt_finalize_and_publish(config, output?)` (L1403) — sequence `validate → prepare → codebook_all → profile → render → sofer_publish(dry_run=True)`, explicit STOP before `sofer_publish_confirm` with `acknowledge_risk`/`acknowledge_confidential`/`approval_phrase` gate
- [x] 1.4 Update `build_server()` server `instructions` string — add one-line canonical order pointer so `initialize` exposes chain without reading source

## Phase 2: Documentation — canonical workflow

- [x] 2.1 Update `README.md` § AI and MCP server — add ordered chain `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm`, args table (`config`/`dataset`/`package`/`output`/`force`/`all_files`), when-to-use per tool, and copy-paste chaining example (`sofer_validate(...); sofer_prepare(...); sofer_codebook_all(...); sofer_profile(..., all_files=True); sofer_render(..., all_files=True)`)
- [x] 2.2 Mirror `README_ES.md` — same chain/args/example (prose ES, code/commands EN) per AGENTS.md rule 13

## Phase 3: Tool docs wiring

- [x] 3.1 Update `tools/list` docstrings in `src/sofer/mcp_server.py` (`_register_tools`) — each `sofer_*` description states side effects and when-to-use vs full chain (MSP-R08/MCP-BC01); no new tool added

## Phase 4: Testing & Verification

- [x] 4.1 Extend `tests/test_mcp_server.py::TestPrompts` — assert `prepare_dataset` contains ordered `sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile → sofer_render`, copy-paste args (`config`, `output`, `all_files=True`); `assess_dataset` contains when-to-use + `sofer_profile`/`sofer_render`; `finalize_and_publish` contains `dry_run=True` STOP
- [x] 4.2 Add `tools/list` assertion — `sofer_build` NOT in list (MCP-BC02 B branch) and each tool description contains when-to-use
- [x] 4.3 Add README grep tests — `README.md` and `README_ES.md` contain ordered chain and example with `all_files`/`force`
- [x] 4.4 Run `uv run pytest tests/ -q` and `uv run ruff check src/ tests/ && uv run mypy src/` — 0 failures, no regressions

## Phase 5: Cleanup

- [x] 5.1 Verify `prepare.py`, `profile.py`, `render.py`, `codebook.py` unchanged (B = prompts/docs only, no logic fork)
- [x] 5.2 Confirm no `sofer_build` registration in `mcp_server.py` and specs note `sofer_build` deferred (design gate for future A)
