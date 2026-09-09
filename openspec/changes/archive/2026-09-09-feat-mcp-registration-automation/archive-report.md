# Archive Report — feat-mcp-registration-automation

**Change**: feat-mcp-registration-automation
**Issue**: GitHub #96 / PR #96 (merge `210e4fc`); residual follow-ups in #121 (credential containment) landed in the #115/#116 batch
**Date**: 2026-09-09
**Artifact store**: hybrid (OpenSpec files + Engram)
**Status**: archived
**Verify verdict**: PASS — change-level `verify-report.md` (verdict: pass, `uv run pytest tests/ -q`); PR #96 merged to `dev` as `210e4fc` (2026-08-31); content re-verified in the #115/#116 batch (1421 passed, 6 skipped)
**Branch**: fix/116-pr4 @ 6f9dc76 (PR #138 landing)

## Summary

Registration automation for the MCP server: `sofer mcp add/remove` registers `sofer-mcp` in opencode (`opencode.json`), codex (`config.toml`), and gemini (`settings.json`) agent configs — idempotent, key-preserving, `.bak` backup before first mutation, atomic write, native-delegation-first with file-merge fallback, `--dry-run`/`--scope`/`--cwd` support. Tasks 17/17 `[x]` with `apply-progress.md` + `verify-report.md` + `exploration.md`/`explore.md`.

**Env-forwarding refinement (post-merge, from the #115/#116 batch)**: the original delta wrote Gemini `env` as an explicit key→value dict. The #115/#116 batch (issue #121, credential containment, PR #138) changed both Gemini `env` and Codex `env_vars` to persist **env NAMES only** — Gemini stores `{"HF_TOKEN": "$HF_TOKEN", ...}` `$KEY` references (expanded by the Gemini CLI at runtime) and Codex stores the allow-list of names; secret values are never written to disk. The new live spec reflects this verified behavior.

## Spec Sync

- **Domain**: `cli` — live spec `openspec/specs/cli/spec.md` updated: ADDED **CLI-R09** "mcp add/remove help" (`sofer --help` and `sofer mcp*` list `add`/`remove` with `--agent`/`--scope`/`--cwd`/`--dry-run`), appended after CLI-R08 (next free ID, matching the delta).
- **Domain**: `mcp-registration` — **new live spec** `openspec/specs/mcp-registration/spec.md` created (precedent: `sofer-v2-metadata-core` archive cc5956f created 5 new base specs). Carries MCP-REG-01 (add) with its agent-file-entry table + 10 scenarios and MCP-REG-02 (remove) + 5 scenarios, adapted to the env-NAMES-only model above. The delta's `specs/mcp-registration/spec.md` is preserved verbatim in the archive for traceability.
- **Delta**: `openspec/changes/feat-mcp-registration-automation/specs/{cli,mcp-registration}/spec.md` (ADDED-only; cli is a MODIFIED append, mcp-registration a new domain).

## Verification Evidence

| Gate | Result |
|------|--------|
| Merge | PR #96 merged `210e4fc` to `dev` (2026-08-31), CI green |
| Suite (post-batch) | `uv run pytest tests/ -q` → 1421 passed, 6 skipped (fix/116-pr4, 2026-09-09) |
| Lint/type | `ruff check` clean, `mypy src/` clean (same run) |
| Env-names-only proof | `tests/test_mcp_registration.py` — `test_gemini_env_both_tokens` asserts `env == {"HF_TOKEN": "$HF_TOKEN", ...}` (CF-3); `test_codex_env_vars_allow_list` asserts names-only |

## Archive Mechanics

- Move: `git mv openspec/changes/feat-mcp-registration-automation openspec/changes/archive/2026-09-09-feat-mcp-registration-automation` (8 tracked files as renames).
- `archive-report.md` additive; active changes dir no longer contains `feat-mcp-registration-automation`.
