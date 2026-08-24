# Archive Report — tool-sofer-config-discovery

**Change**: tool-sofer-config-discovery
**Branch**: fix/tool-sofer-config-discovery @ 95e1db4 (commits fe8910b, 8b94edb, 95e1db4)
**Archived to**: `openspec/changes/archive/2026-08-24-tool-sofer-config-discovery/`
**Archive date**: 2026-08-24
**Verdict**: ✅ ARCHIVED — **PASS WITH WARNINGS** (2 non-blocking warnings carried)

## Verification Source

Engram observation #545 — verify-report for this change (verdict
`pass_with_warnings`, blockers 0, critical 0). Filesystem copy:
`verify-report.md` in this folder.

### SDD artifact traceability (Engram observation IDs)

| Artifact | Topic key | Observation ID |
|----------|-----------|----------------|
| exploration | `sdd/tool-sofer-config-discovery/explore` | #537 |
| proposal | `sdd/tool-sofer-config-discovery/proposal` | #538 |
| spec | `sdd/tool-sofer-config-discovery/spec` | #539 |
| design | `sdd/tool-sofer-config-discovery/design` | #540 |
| tasks | `sdd/tool-sofer-config-discovery/tasks` | #543 |
| apply-progress | `sdd/tool-sofer-config-discovery/apply-progress` | #544 |
| verify-report | `sdd/tool-sofer-config-discovery/verify-report` | #545 |
| archive-report | `sdd/tool-sofer-config-discovery/archive-report` | this save |

## Task Completion Gate

`tasks.md`: **29/29 tasks checked** (Phases 1–5, WU-1..WU-3). No stale
unchecked implementation tasks; apply-progress (#544) and verify-report
(#545) independently confirm all phases complete. Gate PASSED — spec sync
and archive move proceeded normally. No archive-time reconciliation needed.

## Final Task Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 (WU-1) | config.py core + test seam migration + conftest | ✅ 6/6 |
| 2 (WU-2) | Consumer de-freeze: 10 modules, sentinels, argparse defaults, test imports | ✅ 8/8 |
| 3 (WU-3 start) | Reload hooks in `model.from_toml` + `cli.main`; single-fire audit | ✅ 3/3 |
| 4 | Tests TC-01..TC-08 (one per requirement) | ✅ 9/9 |
| 5 (WU-3 rest) | README docs, release-note note, final regression | ✅ 3/3 |

Final regression at verification time: **750 passed** (+24 net-new tests),
`ruff check .` clean, `mypy src/` clean under Python 3.13. Note: tasks.md's
quoted "422 baseline" was stale (suite was already ~726 pre-change) —
recorded as SUGGESTION S-3 in the verify report.

## Spec Sync Summary

New capability `tool-config` — no prior main spec existed, so the delta was
promoted verbatim to the source of truth:

| Domain | Action | Details |
|--------|--------|---------|
| tool-config | **Created** | `openspec/specs/tool-config/spec.md` — 9 requirements (TC-01..TC-09), 15 scenarios. 0 MODIFIED / REMOVED / RENAMED; no existing capability's behavior changed. |

Pre-sync correction applied (verification WARNING W-2): the TC-04 "Override
honored within the same invocation" scenario originally claimed
`sofer prepare --config mydata/dataset.toml` reads CSVs with the tool-wide
`csv_delimiter`. That is architecturally wrong — `prepare` consumes the
DATASET-level `[meta] csv_delimiter` (`model.py:445`), while the tool-wide
consumer is `sofer profile` via `stream_csv` reader defaults
(`profile.py:98`). The scenario now exercises `sofer profile data.csv` from a
cwd whose tree sets the override, with an explanatory note distinguishing
the dataset-level key. This matches the actual covering integration test
(`test_csv_delimiter_override_effective_same_invocation`) and the judged
deviation D-2. Both the archived delta and the synced main spec carry the
correction.

## Deviations Accepted (from verify report #545)

1. **D-1 — `_UNSET` sentinel instead of plain `None` default in `stream_csv`**
   → ACCEPTED (necessary). `quality.py` passes `max_sample=None` explicitly to
   mean "full-file scan" for fail-severity checks (Issue #14); a plain `None`
   sentinel would have silently capped those scans at `codebook_max_sample`.
   Strictly safer than the planned pattern.
2. **D-2 — TC-04 delimiter scenario tested via `profile` instead of `prepare`**
   → ACCEPTED (spec text imprecise, not implementation wrong). Resolved at
   archive time by correcting the scenario (see W-2 above).
3. **D-3 — OpenSpec artifacts committed alongside code in commit 3**
   → ACCEPTED (cosmetic).

## Warnings Carried Forward

- **W-1 — Reader-side visibility vs design claim (OPEN, for future work).**
  Design AD-2 claims concurrent readers see "old-or-new complete state,
  never a partial mix". Implementation swaps each config constant individually
  under `threading.Lock`, but readers (`config.X` attribute access) never
  acquire that lock — a reader interleaved mid-swap can observe a mix of old
  and new values across different constants. Harmless today (single-threaded
  CLI/library flows; CPython per-name reads are atomic); the lock currently
  only protects writers-from-writers. **Future options**: either weaken the
  AD-2 wording in the design doc, or add snapshot-read-under-lock in a
  follow-up change if sofer ever runs reload concurrently with readers.
- **W-2 — Imprecise TC-04 scenario** → RESOLVED during this archive (see
  Spec Sync Summary). No residual action.

Suggestions noted but non-blocking: S-1 (`_DEFAULTS` mutable values aliased,
not deep-copied, into module constants — future mutation hazard), S-2
(commit 3 also removed a redundant top-of-README quickstart block — cosmetic
scope creep), S-3 (stale "422 tests" baseline figure in task templates).

## PR Description Pointers

The PR description MUST repeat:

1. **Release-note item — editable-install behavior shift (REQUIRED)**:
   maintainers running sofer from an editable install no longer pick up
   **sofer's own repo `[tool.sofer]`** at runtime. Tool-wide overrides must
   live in a `pyproject.toml` on the walk-up path from the dataset TOML or
   cwd. (Documented in README §[tool.sofer]; there is no CHANGELOG file, so
   the PR description/release notes are the carrier.)
2. New capability spec: `openspec/specs/tool-config/spec.md` (TC-01..TC-09).
3. Internal API break: `from .config import X` frozen imports are gone;
   consumers use `from . import config` attribute access.
4. Cosmetic scope note: commit 3 also removed the redundant top-of-README
   quickstart block (S-2).
5. Verification evidence: 750 passed, ruff clean, mypy clean (Python 3.13);
   verdict `pass_with_warnings` (W-1 documented above, accepted).

## Archive Contents

- proposal.md ✅
- exploration.md ✅
- specs/tool-config/spec.md ✅ (delta, W-2-corrected)
- design.md ✅
- tasks.md ✅ (29/29 complete)
- verify-report.md ✅
- archive-report.md ✅ (this file)

## Source of Truth Updated

- `openspec/specs/tool-config/spec.md` (created)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
