# Tasks: fix-residual-parity

Closes #153 + #155: residual parity — publish cleanup (`clean`/`clean_cache`)
on the MCP publish tools and batch codebook `max_sample` threading. Flipped
from the parity guard's `known_gaps`. Production implementation already
committed (01ff605); this change's own code edit is the designed RED→GREEN
guard flip.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~45 code (guard flip) + ~340 docs (change artifacts) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main (not needed) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Implementation + tests (committed 01ff605) | PR 1 | 7 MCP + 1 codebook + 1 CLI tests |
| 2 | Guard flip + spec deltas + verify | PR 1 | Single residual-parity PR on `dev` |

## Phase 1: Tests (RED)

- [x] 1.1 `tests/test_mcp_server.py` `TestPublishCleanup` (5): confirm clean
      deletes the build after success and keeps `cache/`; `clean_cache` without
      `clean` refused (`CLEAN_CACHE_WITHOUT_CLEAN`); `clean_cache` deletes
      `cache/`; dry-run clean never deletes; local clean deletes the
      destination.
- [x] 1.2 `tests/test_mcp_server.py` `TestCodebookAllMaxSample` (2): override
      caps (`**Analysed rows:** 1 (sample)`); omitted uses the config default.
- [x] 1.3 `tests/test_codebook.py` `test_generate_all_max_sample_override` (1):
      `generate_all` threads `max_sample` into per-file codebooks.
- [x] 1.4 `tests/test_cli.py` `test_codebook_all_files_max_sample_parity` (1):
      CLI `codebook --all-files --max-sample` forwards to `generate_all`.

Evidence 1.1-1.4: RED observed in the implementation session (tests written
before the implementation commit 01ff605 — schema/param absence failures);
GREEN re-verified here: 7 MCP + 1 codebook + 1 CLI = **9 passed**.

## Phase 2: Implementation (GREEN, committed 01ff605)

- [x] 2.1 `mcp_server.py`: `clean`/`clean_cache` on `sofer_publish` and
      `sofer_publish_confirm`, forwarded to `publish.publish`; refusal gate
      `CLEAN_CACHE_WITHOUT_CLEAN` (`next_hint={"clean": True}`) when
      `clean_cache` without `clean`.
- [x] 2.2 `codebook.py`: `generate_all(max_sample: int | None = None)` threaded
      into every `_build_markdown` call (single, placeholder, single-sheet,
      per-sheet).
- [x] 2.3 `cli.py`: `codebook --all-files` forwards `args.max_sample` to
      `generate_all_codebooks`.

Evidence 2.1-2.3:
`uv run pytest tests/test_mcp_server.py -k "PublishCleanup or CodebookAllMaxSample" -q`
→ 7 passed; `uv run pytest tests/test_codebook.py -k generate_all_max_sample -q`
→ 1 passed; `uv run pytest tests/test_cli.py -k codebook_all_files_max_sample -q`
→ 1 passed.

## Phase 3: Parity guard flip (RED→GREEN, by design)

- [x] 3.1 `tests/test_parity.py` publish area: `clean`/`clean_cache` moved
      `exempt_flags`/`known_gaps` → `flag_map`
      (`{"clean": "clean", "clean_cache": "clean_cache"}`); the 4 `known_gaps`
      tuples and the gap-referencing `exempt_flags` entries deleted.
- [x] 3.2 `tests/test_parity.py` codebook area: `known_gaps` entry
      `("max_sample", "sofer_codebook_all")` deleted.

Evidence 3.1-3.2: RED — `uv run pytest tests/test_parity.py -q` →
**2 failed, 9 passed** (A6: `sofer_codebook_all.max_sample now exists (#155)`;
publish `clean`/`clean_cache` now exist (#153)). GREEN — **11 passed**.

## Phase 4: Spec delta + verify + gates

- [x] 4.1 Spec deltas: `specs/mcp-server/spec.md` NEW MSP-R16 (publish
      cleanup) + NEW MSP-R17 (batch codebook `max_sample`); `specs/codebook/spec.md`
      NEW CB-R10 (`generate_all` threading). Scenarios per requirement.
- [x] 4.2 Gates: full suite, ruff, ruff format, mypy, `git diff --check`
      (results in the verify report; see the known-documented item for the
      the two placeholder-validation CLI failures surfaced by the full-suite run were fixture gaps (missing `max_sample=None` in hand-built Namespaces), closed by fixture completion; all gates green, 1524 passed / 6 skipped).
- [x] 4.3 Verify report + archive on merge.