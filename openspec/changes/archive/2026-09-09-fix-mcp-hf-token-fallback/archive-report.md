# Archive Report — fix-mcp-hf-token-fallback

**Change**: fix-mcp-hf-token-fallback
**Issue**: GitHub #107 / PR #107 (merge `91c8b72`)
**Date**: 2026-09-09
**Artifact store**: hybrid (OpenSpec files + Engram)
**Status**: archived
**Verify verdict**: PASS by merge — PR #107 merged to `dev` as `91c8b72`, CI green; content re-verified in the #115/#116 batch (1421 passed, 6 skipped)
**Branch**: fix/116-pr4 @ 6f9dc76 (PR #138 landing)

## Summary

Hardening change for MCP token handling. Only `tasks.md` survives (14/14 `[x]`); the change shipped no spec delta — the behavior it encodes is part of the live `mcp-server` spec surface (MSP-R05 confirm/`HF_TOKEN` gating, MSP-R03 roster).

Implemented helpers in `src/sofer/mcp_server.py`: `_load_dotenv_if_available()` (dotenv bootstrap with `override=False`, `ImportError` swallowed), `_is_truthy_env()` (`{"1","true","yes","on"}` lowercased), `_clean_token()` (strips CR/LF/whitespace, `or None`), plus env-missing error paths for publish confirm. Token fallback means a `.env`-provided `HF_TOKEN` is honored before the environment check, and dirty/multiline tokens are normalized before the HF call.

## Spec Sync

None — no delta was authored for this change. Live behavior contract lives in `openspec/specs/mcp-server/spec.md` (MSP-R05: publish refuses hf without token; confirm errors without `HF_TOKEN`). The `_clean_token`/`_is_truthy_env`/dotenv helpers are implementation details under that contract.

## Verification Evidence

| Gate | Result |
|------|--------|
| Merge | PR #107 merged `91c8b72` to `dev` (2026-08-31), CI green |
| Suite (post-batch) | `uv run pytest tests/ -q` → 1421 passed, 6 skipped (fix/116-pr4, 2026-09-09) |
| Lint/type | `ruff check` clean, `mypy src/` clean (same run) |

## Archive Mechanics

- Move: `git mv openspec/changes/fix-mcp-hf-token-fallback openspec/changes/archive/2026-09-09-fix-mcp-hf-token-fallback` (single tracked file, rename preserved).
- `archive-report.md` additive, excluded from the readback.
- Active changes dir no longer contains `fix-mcp-hf-token-fallback`.
