# Archive Report — installable-cli-pypi

**Change**: installable-cli-pypi
**Branch**: feat/installable-cli-pypi @ fbe48b3 (commits 5691756, 08b64ad, fbe48b3; base f14f874)
**Archived to**: `openspec/changes/archive/2026-08-26-installable-cli-pypi/`
**Archive date**: 2026-08-26
**Verdict**: ✅ ARCHIVED — **PASS** (0 blockers, 0 critical findings)

## Verification Source

Engram verify-report for this change (topic key
`sdd/installable-cli-pypi/verify-report`, observation #605, project sofer) —
verdict **PASS**, blockers 0, critical findings 0, requirements 7/7, scenarios
16/16. Gate outputs re-run fresh at verification time: `uv run pytest tests/ -q`
→ 803 passed (exit 0); ruff check/format clean; `uv run mypy src/` → clean
(25 source files); `uv build` → `sofer-0.1.dev146+gfbe48b312-py3-none-any.whl`;
wheel METADATA verified directly (Version, License-Expression MIT, License-File,
9 classifiers, 3 Project-URL, Author Emilio Davola, README embedded, entry point
`sofer = sofer.cli:main`, `licenses/LICENSE` present).

### SDD artifact traceability

| Artifact | Source | Location / ID |
|----------|--------|---------------|
| proposal | filesystem | `openspec/changes/installable-cli-pypi/proposal.md` (read) |
| design (corrected) | filesystem | `openspec/changes/installable-cli-pypi/design.md` (read) |
| delta spec (cli) | filesystem | `openspec/changes/installable-cli-pypi/specs/cli/spec.md` (read) |
| tasks | filesystem | `openspec/changes/installable-cli-pypi/tasks.md` (read) |
| verify-report | Engram | observation **#605** (`sdd/installable-cli-pypi/verify-report`) |
| archive-report | Engram + filesystem | this save + this file |

## Task Completion Gate

`tasks.md`: **18/18 checkboxes checked** (Phase 1: 7, Phase 2: 6, Phase 3: 5) —
no stale unchecked implementation tasks. Gate PASSED; spec sync and archive move
proceeded normally. (Launch prompt quoted 15/15; the persisted file is the
source of truth and shows 18/18, matching the verify-report.)

## Final Task Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Version resolver (`_version.py`, `__init__.py`, `cli.py`, `metadata.py`, test rework) | ✅ 7/7 |
| 2 | Packaging + workflow + docs (pyproject, release.yml, AGENTS.md, README, live PKG-01 fix) | ✅ 6/6 |
| 3 | Packaging tests (`tests/test_packaging.py`: resolver, source scan, build smoke, installed-CLI E2E) | ✅ 5/5 |

## Spec Sync Summary

| Domain | Action | Details |
|--------|--------|---------|
| packaging | Confirmed (created this change) | `openspec/specs/packaging/spec.md` is the **finalized live version** — created in implementation commit 08b64ad and corrected by task 2.5: PKG-01 now carries the verified dev-version shapes (`0.3.1.dev1+g<sha>` off-tag / `0.1.dev1+g<sha>` zero-tag); no `0.2.0.post5` example remains (confirmed by verify-report and direct read). PKG-01..05 live, no further action. |
| cli | Updated | **CLI-R05 ADDED** (after CLI-R04 — numbering confirmed continuous) — `sofer --version` prints `sofer v<version>` resolved at runtime from installed metadata, never a static constant; non-empty + PEP 440-valid; works standalone without `uv run`. 3 scenarios. |
| cli | Updated | **CLI-R06 ADDED** — `generated.version` document stamping uses the SAME shared resolver as `--version`; static `__version__` removed; dev fallback non-empty. 2 scenarios. |

All existing CLI requirements (CLI-R01..CLI-R04) preserved untouched. Each new
section carries the repo's provenance note convention
(`> Added by change \`installable-cli-pypi\` (archived 2026-08-26).`).

## Verification warnings carried to close (non-blocking, design-accepted)

- **W-1**: `.pth` installed-CLI E2E verified only on win32; POSIX parity pending
  first ubuntu CI run (test is `os.name`-portable; design D7 scoped this).
- **W-2**: PKG-01 tagged==tag and PKG-02 LICENSE-bundled scenarios covered by
  tag-triggered `release.yml` build-job steps not yet executed; assertions
  correct by inspection, wheel-side facts manually verified. First tagged
  release confirms (design D4 intended).

Both were recorded as WARNINGS at verification time, have zero blockers, and
remain open confirmations — not defects — at archive close.

## Archive Contents

- proposal.md ✅
- explore.md ✅
- specs/cli/spec.md ✅ (delta — 2 ADDED requirements, 5 scenarios)
- design.md ✅
- tasks.md ✅ (18/18 complete)
- archive-report.md ✅ (this file)

## Source of Truth Updated

- `openspec/specs/cli/spec.md` (CLI-R05 added; CLI-R06 added)
- `openspec/specs/packaging/spec.md` (already live and finalized — created this change, no further edit)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.