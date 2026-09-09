# Archive Report — feat-mcp-build-clarity

**Change**: feat-mcp-build-clarity
**Issue**: GitHub #109 / PR #109 (merge `f33ac17`)
**Date**: 2026-09-09
**Artifact store**: hybrid (OpenSpec files + Engram)
**Status**: archived
**Verify verdict**: PASS by merge — PR #109 merged to `dev` as `f33ac17` (2026-08-31), CI green; content re-verified in the #115/#116 batch (1421 passed, 6 skipped)
**Branch**: fix/116-pr4 @ 6f9dc76 (PR #138 landing)

## Summary

Build-clarity change: pinned the 3 workflow prompt templates (`prepare_dataset`, `assess_dataset`, `finalize_and_publish`) to the canonical order `validate → prepare → codebook_all → profile(all_files) → render(all_files) → publish(dry_run) → publish_confirm`, with per-step args, when-to-use guidance, copy-paste chaining examples, and the mandatory human-approval stop before confirm. Docs (README/README_ES) state the chain without implying a new tool. Tasks 13/13 `[x]`.

**Design decision MCP-BC02 → B**: the conditional `sofer_build` orchestration tool was **not** implemented — option B (docs/prompts only) was selected. Sequencing is satisfied by MSP-R08 + MSP-R04/10.4. Confirmed against live code: zero references to `sofer_build` in `src/` and in the live spec; `tools/list` intentionally does not expose it.

## Spec Sync

None required — the delta content was absorbed into the live spec by later syncs:

- **MSP-R08 (MODIFIED by delta)**: already live in `openspec/specs/mcp-server/spec.md` — the 3 named templates (`prepare_dataset`, `assess_dataset`, `finalize_and_publish`) with the "Prompt list shows 3 templates" and "Confirm-before-publish idiom enforced" scenarios.
- **MCP-BC01 (ADDED by delta)**: documentation surface covered by live MSP-R12 ("Packaging and documentation" — `README.md` Install/AI-MCP scenarios, `README_ES mirrors README §13`) and 10.4 ("Chain learnable from tools/list" — `instructions` phased diagram + `Requires:`/`Next:` per tool).
- **MCP-BC02 (ADDED by delta, conditional)**: resolved as decision B — not implemented, therefore not a live requirement (see Summary).

## Verification Evidence

| Gate | Result |
|------|--------|
| Merge | PR #109 merged `f33ac17` to `dev` (2026-08-31), CI green |
| Suite (post-batch) | `uv run pytest tests/ -q` → 1421 passed, 6 skipped (fix/116-pr4, 2026-09-09) |
| Lint/type | `ruff check` clean, `mypy src/` clean (same run) |
| `sofer_build` absence | `grep sofer_build src/ openspec/specs/mcp-server/spec.md` → 0 matches |

## Archive Mechanics

- Move: `git mv openspec/changes/feat-mcp-build-clarity openspec/changes/archive/2026-09-09-feat-mcp-build-clarity` (4 tracked files as renames + specs delta).
- `archive-report.md` additive; active changes dir no longer contains `feat-mcp-build-clarity`.
