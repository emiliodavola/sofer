# Archive Report: fix-quality-encoding-xlsx

**Change**: fix-quality-encoding-xlsx
**Branch**: fix/quality-encoding-xlsx
**Archived**: 2026-08-28
**Archived to**: openspec/changes/archive/2026-08-28-fix-quality-encoding-xlsx/
**Mode**: hybrid (Engram + openspec)
**Verdict**: PASS — 923 passed, 2 skipped, ruff+mypy clean, 12/12 scenarios compliant

---

## 1. Final State

QualityValidator now gates all P0 checks to text-eligible files only. Binary formats
(.xlsx/.parquet/.jsonl/.csv.gz→.gz/no-extension) are skipped with no I/O, no
QualityResult, no ran_checks mutation. Binary-only datasets yield empty
quality_results + empty ran_checks so publish is not blocked (0 failed).

| Artifact | Location | Status |
|----------|----------|--------|
| explore | sdd/fix-quality-encoding-xlsx/explore (#659) + openspec/changes/archive/.../explore.md | archived |
| proposal | sdd/fix-quality-encoding-xlsx/proposal (#660) + archive/proposal.md | archived |
| spec (delta) | sdd/fix-quality-encoding-xlsx/spec (#661) + archive/specs/data-quality/spec.md | synced to base |
| design | sdd/fix-quality-encoding-xlsx/design (#662) + archive/design.md | archived |
| tasks | sdd/fix-quality-encoding-xlsx/tasks (#663) + archive/tasks.md (17/17 ✅) | archived |
| apply-progress | sdd/fix-quality-encoding-xlsx/apply-progress (#664) + archive/apply-progress.md | archived |
| verify-report | sdd/fix-quality-encoding-xlsx/verify-report (#666) + archive/verify-report.md (PASS) | archived |
| base spec | openspec/specs/data-quality/spec.md | updated — 2 added, 2 modified requirements |

---

## 2. Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| data-quality | Updated | 2 ADDED, 2 MODIFIED requirements |
| data-quality §3.1 | Updated (coherence) | Encoding fallback narrowed to UTF-8-only (latin-1/cp1252 removed) |

### Delta Applied

**ADDED Requirements → Appended as §4.11 / §4.12:**
- **Text-eligible scope for all P0 checks** (§4.11) — All P0 checks MUST apply only to
  TEXT_SUFFIXES = {".csv",".tsv"} via is_text_eligible() in src/sofer/_formats.py;
  binary suffixes skipped, binary-only → empty results. 4 scenarios: binary skipped,
  TSV eligible, case-insensitive/no-extension, binary-only no cross-file.
- **UTF-8-only enforcement** (§4.12) — ENCODING_FALLBACKS SHALL be ["utf-8-sig","utf-8"]
  only; latin-1/cp1252 MUST NOT be retried; shared between stream_csv and
  _check_encoding_validation.

**MODIFIED Requirements → Replaced:**
- **QualityValidator.run() - eligibility-gated dispatch** (§4.10) — Replaced/added:
  run() SHALL skip not is_text_eligible after exists/is_dir; defensive early-returns
  in helpers; only eligible files contribute to ran_checks. 4 scenarios: filters before
  accumulators, defensive guard, binary-only empty ran_checks, mixed ran_checks.
- **Encoding validation - detect non-UTF-8 files in text-eligible inputs** (§4.9) —
  Replaced §4.9: scoped to text-eligible .csv/.tsv case-insensitive, 8KB probe with
  ["utf-8-sig","utf-8"] only, non-eligible skipped. 3 scenarios: valid UTF-8 pass,
  non-UTF-8 fail, xlsx skipped. Preserved known-limitation note.

**Additional coherence fix (not in delta but required for consistency):**
- §3.1 Behaviour point 6 and scenarios updated: Latin-1 fallback scenario → UTF-8-only
  (ValueError when both utf-8-sig/utf-8 fail); unrecoverable scenario narrowed to 2 encodings.
- §4.0 QualityValidator class description extended to reference eligibility gating (§4.10/§4.11).

No destructive delta — no requirements removed, no large sections deleted. Preserved all
other P0 check requirements (§4.1–§4.8), data model (§2), integration (§5), behavioural
rules (§6). No REMOVED or RENAMED requirements in delta.

**Source of Truth Updated:**
- openspec/specs/data-quality/spec.md — now contains §4.9–§4.12 as above; base spec is
  consistent with implementation (TEXT_SUFFIXES + is_text_eligible + _had_eligible gating
  + UTF-8-only ENCODING_FALLBACKS).

---

## 3. Retained Decisions

| Decision | Rationale | Retained |
|----------|-----------|----------|
| TEXT_SUFFIXES frozenset in _formats.py + is_text_eligible(Path)->bool | One module per concern; SUPPORTED_FORMATS already there; single source of truth | Yes — src/sofer/_formats.py:26-44 |
| Guard placement: run() filter (primary) + helper early-returns (defense in depth) | Primary prevents I/O on binaries; helpers protect direct calls + ran_checks | Yes — quality.py:140-143 + 216-217 + 540-541 |
| No new [tool.sofer] key (quality_eligible_suffixes) | Invariant not preference; YAGNI; zero config/README churn | Yes — config.py unchanged |
| Suffix-only (path.suffix.lower()) not magic-byte/NUL sniffing | O(1) deterministic; mislabeled .csv with PK bytes should fail via ValueError | Yes — is_text_eligible uses suffix.lower() |
| UTF-8-only ENCODING_FALLBACKS ["utf-8-sig","utf-8"] | Quality gate rejects non-UTF-8; stale spec 4-encoding chain reconciled | Yes — _csv_reader.py:27 |
| _had_eligible gating for post-scan checks + ran_checks | Binary-only yields empty results so publish shows 0 failed not spurious passed | Yes — quality.py _had_eligible |
| Single PR, no chained PRs (398 lines, <400 budget) | Forecast 30-50 prod lines, actual 94 prod + 311 test; low review risk | Yes — branch fix/quality-encoding-xlsx |

Rejected alternatives remain rejected: magic-byte, config-driven allowlist, re-adding latin-1.

---

## 4. Task Completion Gate

17/17 tasks complete — no unchecked implementation tasks.

- Phase 1 Foundation — _formats.py (3 tasks) ✅
- Phase 2 Core Implementation — gated dispatch (5 tasks) ✅
- Phase 3 Testing/Verification (7 tasks) ✅
- Phase 4 Documentation/Polish (2 tasks) ✅

Archived tasks.md has 0 unchecked boxes. apply-progress.md and verify-report.md confirm
completion (verify-report verdict PASS, 12/12 scenarios, 923 tests).

No stale-checkbox reconciliation needed. No exceptional repair.

---

## 5. Verification Summary (from verify-report #666)

- **Tasks**: 17/17 complete, 0 incomplete
- **Build**: ruff check src/ tests/ — All checks passed; mypy src/ — Success 26 files; ruff format — 62 files formatted
- **Tests**: 923 passed, 2 skipped, 0 failed (full suite); 61 passed in tests/test_quality.py
- **Scenarios**: 12/12 compliant across 4 requirements (Text-eligible scope ×4, UTF-8-only ×1, Gated dispatch ×4, Encoding validation ×3)
- **Critical/Blockers**: 0
- **Coherence**: All 4 architecture decisions followed; no deviations; design docs match implementation.

Evidence revision: sha256:e03a2568539c6272cc54d3fa2ca02fa6d234080d840b1074aadbf23ba228a659
Test hash: sha256:f19ddb4e62607bc5f77b15eb0c032fe87f2e2189f5ae764d8d3ea3dd04cef682

---

## 6. Files Changed (delivered)

| File | Action | Lines |
|------|--------|-------|
| src/sofer/_formats.py | Modified — TEXT_SUFFIXES + is_text_eligible | 32 |
| src/sofer/quality.py | Modified — gated dispatch + _had_eligible + guards + docstrings | 62 |
| tests/test_quality.py | Modified — 27 new tests across 7 classes | 311 |
| openspec/specs/data-quality/spec.md | Updated — §3.1 + §4.0 + §4.9 replaced + §4.10–4.12 added | ~130 |
| src/sofer/_csv_reader.py | Unchanged | 0 |
| src/sofer/config.py | Unchanged (deliberate) | 0 |

---

## 7. Archive Contents

- proposal.md ✅
- specs/data-quality/spec.md (delta) ✅
- design.md ✅
- tasks.md ✅ (17/17)
- apply-progress.md ✅
- verify-report.md ✅ (PASS)
- archive-report.md (this file) ✅

Active changes directory no longer has this change:
  openspec/changes/fix-quality-encoding-xlsx/ → moved to archive

---

## 8. Traceability — Engram Observation IDs

| Artifact | Topic Key | ID | Sync ID |
|----------|-----------|----|---------|
| explore | sdd/fix-quality-encoding-xlsx/explore | #659 | obs-7b10a34a7305bca8 |
| proposal | sdd/fix-quality-encoding-xlsx/proposal | #660 | obs-b7e05818dac005f7 |
| spec | sdd/fix-quality-encoding-xlsx/spec | #661 | obs-c2bc72787d7f9a71 |
| design | sdd/fix-quality-encoding-xlsx/design | #662 | obs-cbdcf10dee9d591e |
| tasks | sdd/fix-quality-encoding-xlsx/tasks | #663 | obs-3a307872a1742cad |
| apply-progress | sdd/fix-quality-encoding-xlsx/apply-progress | #664 | obs-a7421e08ad405663 |
| verify-report | sdd/fix-quality-encoding-xlsx/verify-report | #666 | obs-e5605af4e1541b36 |
| archive-report | sdd/fix-quality-encoding-xlsx/archive-report | (this save) | — |

All artifacts read via Engram per hybrid retrieval (Section B); filesystem artifacts
read from openspec/changes/fix-quality-encoding-xlsx/ before move and verified in
archive after move.

---

## 9. Close

SDD cycle complete: explore → proposal → spec → design → tasks → apply → verify (PASS) → archive.
No destructive merge, no warnings, no blockers. Ready for next change.

sync_id: obs-archive-fix-quality-encoding-xlsx
