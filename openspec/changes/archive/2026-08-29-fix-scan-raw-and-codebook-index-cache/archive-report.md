# Archive Report: fix-scan-raw-and-codebook-index-cache

**Change**: fix-scan-raw-and-codebook-index-cache
**Branch**: fix/scan-raw-and-codebook-index-cache
**PR**: #89 (closes #87, #88)
**Archived**: 2026-08-29
**Archived to**: `openspec/changes/archive/2026-08-29-fix-scan-raw-and-codebook-index-cache/`
**Mode**: hybrid (Engram + openspec)
**Verdict**: PASS — 0 critical, 0 warnings, 12/12 scenarios compliant

---

## 1. Intent

Fix `raw/ -> cache/ -> build/` contract:

- **Bug 1 — scan (#87)**: `scan` created `raw/` scaffold but did not MOVE `.csv/.tsv/.xlsx/.jsonl/.parquet` with subfolder tree into `raw/`. Correct is MOVE preserving `relative_to(base_dir)` into `raw/` (SHALL, not copy).
- **Bug 2 — codebook (#88)**: `generate_all` wrote `cache/codebooks/*` but index to `base_dir/codebook.md` (`codebook.py:441`). Must be `cache/codebook.md` (`write_root/codebook.md` when `output_dir is None`).

User clarifies: MOVE, not copy. Single PR, atomic, preserving `raw/->cache/ via flatten_first_level + shutil.copy2` and `cache->build/` stages.

## 2. Phases

| Phase | Artifact | ID / Path | Status |
|-------|----------|-----------|--------|
| Proposal | `sdd/fix-scan-raw-and-codebook-index-cache/proposal` + `proposal.md` | #699 | done — intent/scope/approach, affected areas (scanner/cli/codebook), risks/rollback, success criteria |
| Spec | `sdd/fix-scan-raw-and-codebook-index-cache/spec` + `specs/{scan,codebook}/spec.md` | #700 | done — 2 MODIFIED requirements (SCN-07 Move-to-Raw 8 scenarios, CB-R04 Root Index 4 scenarios), 12 scenarios total |
| Design | `sdd/fix-scan-raw-and-codebook-index-cache/design` + `design.md` | #701 | done — 103 lines, 5 decisions (preserve tree, pre-flight collision, two-phase discovery, single prompt gate, one-liner write_root), flow, contracts, testing strategy |
| Tasks | `sdd/fix-scan-raw-and-codebook-index-cache/tasks` + `tasks.md` | #702 | done — 12 tasks across 4 phases, 400-line budget Low, single PR work-unit |
| Apply-progress | `sdd/fix-scan-raw-and-codebook-index-cache/apply-progress` + `tasks.md` updates | #703 | done — 3 commits (a32519b fix, 19b03ab test, a33228e docs), 12/12 tasks [x] |
| Verify-report | `sdd/fix-scan-raw-and-codebook-index-cache/verify-report` + `verify.md` | #704 | PASS — 0 blockers, 0 critical, 2/2 requirements, 12/12 scenarios COMPLIANT, 1022 passed + ruff/mypy green |

**Task Completion Gate**: `tasks.md` 12/12 checked — no stale unchecked tasks. Verified via file `archive/tasks.md` (all [x] P1 1.1-1.4, P2 2.1-2.2, P3 3.1-3.3, P4 4.1-4.3) and Engram #702/#703.

## 3. Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| scan | Updated (MODIFIED) | SCN-07 Source Layout and Move-to-Raw: `mkdir -p raw/` then MOVE 5 exts preserving `relative_to(base_dir)` via `shutil.move`, pre-flight `check_raw_collisions` atomic exit 1, `--dry-run`/`--force`/`[y/N]` gate, then `raw/->cache/` flatten copy. 8 scenarios (tree, 5 exts, EXCLUSIONS, dry-run, collision, abort atomic, idempotency, docs diagram). Previously copy-only. |
| codebook | Updated (MODIFIED) | CB-R04 Root Index: `write_root/codebook.md` — `cache/codebook.md` when `output_dir is None` (standalone), `output_dir/codebook.md` when set (prepare). Colocated `codebooks/` prefix, MUST NOT write `base_dir/codebook.md` standalone. 4 scenarios (standalone cache, prepare build, nested Labels/, relative links). Previously `base_dir/codebook.md` always. |

**Source of Truth Updated**:
- `openspec/specs/scan/spec.md` — SCN-07 replaced Copy-Only with Move-to-Raw (preserves SCN-01..SCN-06)
- `openspec/specs/codebook/spec.md` — CB-R04 replaced (preserves CB-R01, CB-R02, CB-R03, CB-R06, CB-R07, CB-R08)

No REMOVED or RENAMED requirements; no destructive delta — preserved all other requirements per archive skill merge contract. Merge verified: scan spec SCN-07 header now `Move-to-Raw`, codebook spec contains `write_root` routing.

## 4. Archive Contents

- proposal.md ✅ (77 lines, SCN-07 + CB-R04 scope, approach 1C+2A chosen, 5 risks, rollback single commit)
- specs/scan/spec.md ✅ (delta 58 lines, 1 MODIFIED requirement, 8 scenarios)
- specs/codebook/spec.md ✅ (delta 34 lines, 1 MODIFIED requirement, 4 scenarios)
- design.md ✅ (103 lines, 5 decisions + data flow, interfaces `check_raw_collisions`/`move_to_raw`, testing strategy, migration note)
- tasks.md ✅ (12/12 complete, 4 phases, estimates P1~1.5h P2~2h P3~2h P4~0.5h)
- verify.md ✅ (PASS, 12/12 COMPLIANT, 1022 passed, warnings section with 1 intentional non-blocker)
- exploration.md ✅ (120 lines, Bug 2 confirmed line 441, Bug 1 characterized, approaches 1A/1B/1C + 2A/2B evaluated)
- archive-report.md ✅ (this file)

**Active changes directory** no longer contains `fix-scan-raw-and-codebook-index-cache` — moved to `archive/2026-08-29-fix-scan-raw-and-codebook-index-cache/`.

## 5. File Changes (3 commits on branch fix/scan-raw-and-codebook-index-cache)

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/scanner.py` | Modified | Added `check_raw_collisions(candidates, raw_dir, base_dir)` (dest=raw_dir/rel, ValueError naming both) + `move_to_raw(...)` (mkdir parents, shutil.move, no flatten) + docstring `raw/->cache/->build/` MOVE-then-copy |
| `src/sofer/codebook.py:439-441` | Modified | `root_path = write_root / "codebook.md"` when `output_dir is None` (was `base_dir`), colocated `codebooks_dir = write_root/CODEBOOKS_DIR`, links `relative_to(write_root)` |
| `src/sofer/cli.py` | Modified | Rewrote `_cmd_scan` two-phase: P1 discover `EXCLUSIONS|{RAW_DIR,OUTPUT_DIR}` (5 exts via SUPPORTED_FORMATS), `raw_dir.mkdir` skip dry-run, atomic `check_raw_collisions` exit 1, `[y/N]`/`--force`/`--dry-run` gate with `-> raw/<rel>` preview, `move_to_raw`; P2 discover `EXCLUSIONS|{OUTPUT_DIR}`, `check_flatten→merge→copy(raw→cache flatten, copy2)→write` |
| `src/sofer/cli.py` (parser) | Modified | Scan help documents `mkdir -p raw/`, MOVE `relative_to`, `--dry-run` preview, EXCLUSIONS |
| `tests/test_codebook.py` | Modified | 6 asserts to `cache/codebook.md` (556,573,591,679,772,806) + assert no `base_dir/codebook.md` |
| `tests/test_scanner.py` | Modified | Added `TestCheckRawCollisions`/`TestMoveToRaw` (tree+5 exts+EXCLUSIONS+f.txt+dry-run) + `TestScanMoveScenarios` 8 scenarios + adapt idempotency/docs |
| `tests/test_cli.py` | Modified | Added `TestScanMoveCLI` (e2e tree, dry-run no FS/TOML, collision atomic, N abort, 5-exts vs f.txt) |
| `tests/test_mcp_server.py` | Modified | Updated to `cache/codebook.md` |
| `.gitignore` | Modified | Added `cache/` |
| `README.md`, `README_ES.md`, `docs/configuration.md` | Modified | Pipeline diagram `raw/→cache/→build/` + `raw/DPTO.csv→cache/DPTO.csv` |

Commits:
- `a32519b fix(scanner,codebook,cli): implement scan MOVE-then-Copy and cache index fix`
- `19b03ab test(scanner,codebook,cli): update tests for MOVE and cache index`
- `a33228e docs: update pipeline docs and gitignore, mark SDD tasks complete`

665 insertions across source+tests+docs per apply-progress; single PR verified within 400-line-budget Low forecast (work-unit 1).

## 6. Test Evidence

```
$ uv run pytest tests/ -q
1022 passed, 2 skipped, 13 warnings in 14.70s

$ uv run pytest tests/test_scanner.py -q -v
71 passed in 1.00s

$ uv run pytest tests/test_cli.py -k scan -v
13 passed (TestScanParser 8 + TestScanMoveCLI 5)

$ uv run pytest tests/test_codebook.py -v
73 passed

$ uv run pytest tests/test_mcp_server.py -v
74 passed, 2 skipped

$ uv run ruff check src/ tests/
All checks passed!

$ uv run mypy src/
Success: no issues found in 27 source files
```

12/12 delta scenarios covered COMPLIANT (8 SCN-07 + 4 CB-R04). Verify report #704: schema gentle-ai.verify-result/v1, evidence_revision sha256:ee8250fb..., test_exit_code 0, build_exit_code 0.

## 7. Warnings (non-blocking, per verify-report id 704)

**WARNING**: None

Note carried from verifier: `dry_run + candidates` returns early after P1 preview (no P2 copy preview in same run). Intentional atomicity — no FS/TOML mutation, covered by dry-run tests. Not a deviation. If product wants dry-run to also preview P2 flattened copies, file follow-up enhancement.

**SUGGESTION** (non-blocking):
- Consider explicit unit test asserting `codebook.py` docstring reflects `cache/codebook.md` vs `build/codebook.md` locations (covered indirectly via 6 codebook tests + integration).

No CRITICAL issues — archive not blocked; strict-vs-OpenSpec policy passed.

## 8. Breaking Change Note

- **Scan**: previously copy-only to `cache/` leaving loose files in place; now **MOVEs** loose supported files into `raw/` preserving tree, removing originals. Users with intentionally loose files outside `raw/` must now expect relocation on `scan`. Mitigated by `--dry-run` preview + `[y/N]` prompt (unless `--force`) + atomic collision guard.
- **Codebook**: `codebook --all-files` consumers must read `cache/codebook.md` (was `./codebook.md`). Release note required. `cache/` now gitignored — untracked codebooks no longer pollute `git status`. No dual-write drift (rejected per design).

## 9. Next Steps (follow-up)

- Release note for breaking `cache/codebook.md` relocation (#88) and `scan` MOVE semantics (#87).
- Optional: non-interactive `scan` without `--force` auto-abort hint (open question from design.md).
- Optional: ensure `raw/.gitkeep` when empty (open question).
- No code debt — single-commit revert available per proposal rollback plan.

## 10. SDD Cycle Complete

The change has been fully planned, implemented, verified (PASS), and archived. Main specs now reflect MOVE-to-raw (SCN-07) and cache index (CB-R04). Branch `fix/scan-raw-and-codebook-index-cache` retains 3 commits and is ready for PR #89 `fix/scan-raw-and-codebook-index-cache -> dev`.

**Traceability**: Engram IDs 699/700/701/702/703/704 + filesystem archive `openspec/changes/archive/2026-08-29-fix-scan-raw-and-codebook-index-cache/` is audit trail — never delete or modify archived changes.

---

*Generated by sdd-archive sub-agent (muse-spark-1.2-contributor) — hybrid persistence, Task Completion Gate passed, CRITICAL=0, Verify PASS.*
