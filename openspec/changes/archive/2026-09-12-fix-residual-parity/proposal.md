# Proposal: fix-residual-parity

## Intent

Close the last two open CLI↔MCP parity gaps declared as `known_gaps` in the
parity guard (`tests/test_parity.py`, PR #163 — paritially addressed by
`fix-scan-parity-mcp`): **#153** (publish cleanup `--clean`/`--clean-cache` not
exposed on the MCP publish tools) and **#155** (batch codebook `max_sample` not
threaded through `sofer_codebook_all`). The production implementation is
already done and committed (01ff605): `src/sofer/mcp_server.py` exposes
`clean`/`clean_cache` on `sofer_publish`/`sofer_publish_confirm` and
`max_sample` on `sofer_codebook_all`; `src/sofer/codebook.py` threads
`max_sample` through `generate_all`; `src/sofer/cli.py` forwards
`--max-sample` to the `--all-files` batch path. TDD was completed in that
session: 9 behavior tests (7 MCP + 1 codebook unit + 1 CLI parity) are GREEN.
This change's own code edit is the designed **RED→GREEN guard flip** — moving
the now-implemented params from `known_gaps`/`exempt_flags` into `flag_map` —
plus the SDD artifacts (this proposal, spec deltas, tasks, verify report).

## Scope

### In Scope
- Guard flip in `tests/test_parity.py`:
  - publish area: `clean`/`clean_cache` moved from `exempt_flags` (gap reason)
    + `known_gaps` → `flag_map` (`{"clean": "clean", "clean_cache": "clean_cache"}`);
    the 4 `known_gaps` tuples `(clean|clean_cache, sofer_publish|sofer_publish_confirm)`
    are deleted and the `exempt_flags` entries referencing the gap are removed.
  - codebook area: `known_gaps` entry `("max_sample", "sofer_codebook_all")`
    deleted (`max_sample` was already in `flag_map` for the single-file tool).
- Spec deltas (change-local, applied to canonical on merge):
  - `specs/mcp-server/spec.md`: NEW **MSP-R16** (publish cleanup) + NEW
    **MSP-R17** (batch codebook `max_sample`), full block format with scenarios.
  - `specs/codebook/spec.md`: NEW **CB-R10** (`generate_all` `max_sample`
    threading), matching the existing CB requirement/scenario format.
- Verify report + tasks (this change).

### Out of Scope
- `src/sofer/` production code — already implemented and committed (01ff605);
  untouched here per the change boundary.
- Any test other than `tests/test_parity.py`.
- No new CLI surface: `publish --clean/--clean-cache` and `codebook
  --max-sample` already existed; this change only exposes their MCP
  counterparts and threads the batch `max_sample` (already done).

## Capabilities

### New Capabilities
- `mcp-server` MSP-R16: `clean`/`clean_cache` on `sofer_publish` and
  `sofer_publish_confirm` (forwarded to `publish.publish`, PUB-11 gated in the
  domain; `clean_cache` without `clean` refused with
  `CLEAN_CACHE_WITHOUT_CLEAN`).
- `mcp-server` MSP-R17: `max_sample` on `sofer_codebook_all` (forwarded to
  `codebook.generate_all`; `None` = `[tool.sofer] codebook_max_sample`).
- `codebook` CB-R10: `generate_all(max_sample=None)` threads the cap into every
  per-file codebook (single-format, placeholder, single-sheet and per-sheet
  `.xlsx`), with `**Analysed rows:**` `(sample)`/`(full scan)` labelling.

### Modified Capabilities
- None at the domain level: `publish.publish` already carried `clean`/`clean_cache`
  (PUB-11); `generate_codebook`/`_build_markdown` already resolved `None` →
  `codebook_max_sample`. This change only bridges the MCP/batch surfaces.

## Approach

- **Zero production duplication**: the MCP tools forward params verbatim to the
  existing domain entry points (`publish.publish`, `codebook.generate_all`).
  The only new production logic was the `CLEAN_CACHE_WITHOUT_CLEAN` refusal
  gate on both publish tools (`next_hint={"clean": True}`) and the single-line
  `max_sample=` thread in `generate_all`.
- **PUB-11 stays in the domain**: cleanup SHALL happen only after a successful
  delivery — never on dry-run, quality-gate block, or failure. The MCP layer
  only adds the explicit-opt-in refusal for `clean_cache` without `clean`.
- **Guard flip as the RED→GREEN step**: with the implementation committed,
  `known_gaps`'s negative assertions fail by design (A6); the flip re-declares
  the params as mapped and the guard turns green. Verified: RED `2 failed,
  9 passed` → GREEN `11 passed`.
- TDD completed in the implementation session (01ff605): behavior tests written
  first (RED — schema rejection / absent params), implementation (GREEN);
  re-verified here: 7 MCP + 1 codebook + 1 CLI = 9 passed.

## Decision Points

| # | Decision | Recommendation | Tradeoff |
|---|----------|----------------|----------|
| 1 | `clean_cache=True` without `clean=True` | **Refuse** (`CLEAN_CACHE_WITHOUT_CLEAN`, `next_hint clean: True`) | Ignoring invites a later silent flip-on of cache deletion when `clean` is added; refusal is explicit-opt-in (PUB-11) and self-documenting to agents |
| 2 | `max_sample=None` semantics | **`None` = `[tool.sofer] codebook_max_sample` config default** (default `100_000`), resolved at call time | Matches the single-file CLI/MCP path (CB-R08); never a frozen argparse literal — AGENTS rule 1; per-call resolution honors TOML reloads |
| 3 | Cleanup gating location | **Domain (`publish.publish`, PUB-11)** — success-only | MCP stays a thin surface; dry-run/quality-gate-block/failure never delete, covered by behavior tests |
| 4 | Batch `--max-sample` CLI forwarding | **Forward `args.max_sample` as-is** (`None` → config default downstream) | CLI `--all-files` parity with `sofer_codebook_all`; no duplicate defaulting |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_server.py` | Modified (committed 01ff605) | `clean`/`clean_cache` on both publish tools + refusal gate; `max_sample` on `sofer_codebook_all` |
| `src/sofer/codebook.py` | Modified (committed 01ff605) | `generate_all(max_sample=None)` threaded into every `_build_markdown` call |
| `src/sofer/cli.py` | Modified (committed 01ff605) | `codebook --all-files` forwards `--max-sample` to `generate_all_codebooks` |
| `tests/test_mcp_server.py` | Modified (committed 01ff605) | `TestPublishCleanup` (5) + `TestCodebookAllMaxSample` (2) |
| `tests/test_codebook.py`, `tests/test_cli.py` | Modified (committed 01ff605) | 1 codebook unit + 1 CLI parity test |
| `tests/test_parity.py` | Modified (this change) | Guard flip: publish + codebook areas re-declared |
| `openspec/changes/…/specs/mcp-server/spec.md` | New (this change) | NEW MSP-R16 + MSP-R17 |
| `openspec/changes/…/specs/codebook/spec.md` | New (this change) | NEW CB-R10 |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `known_gaps` flip ordering confusion | Low | A6 negative asserts fail loudly at the flip; RED captured before the edit |
| `clean_cache` without `clean` silently ignored by some caller | Low | Refusal gate on both tools + domain gate; test `test_publish_confirm_clean_cache_requires_clean` |
| Batch `max_sample` bypassing config default | Low | `None` resolves inside `_build_markdown` at call time, same as single-file (CB-R08); test `test_codebook_all_default_uses_config` |
| Pre-existing full-suite failures unrelated to this flip | Med | 2 `test_cli.py` failures + 1 ruff error + 3 format files trace to production commit 01ff605 (out of this change's edit surface); documented in the verify report |