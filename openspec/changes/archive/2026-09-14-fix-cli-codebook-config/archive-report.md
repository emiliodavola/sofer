# Archive Report — 2026-09-14-fix-cli-codebook-config

**Change**: `2026-09-14-fix-cli-codebook-config`
**Issue**: GitHub #182
**Date**: 2026-09-14
**Artifact store**: `openspec` (hybrid — every artifact also mirrored to Engram under `sdd/2026-09-14-fix-cli-codebook-config/**`)
**Status**: **archived**
**Verify verdict**: **PASS** — `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 5/5`; envelope validated by `gentle-ai sdd-verify-validate` → `{"valid": true, "verdict": "pass", "evidence_revision": "sha256:b2612c30c06e48cbd591bab6de90e7ccc1feadf27d0d589f04c1f0bd9b7e437e"}`, exit 0
**Branch**: `fix/182-cli-codebook-config`
**Archived path**: `openspec/changes/archive/2026-09-14-fix-cli-codebook-config/`

## Summary

Closes #182: `sofer codebook FILE` read the *literal* `;` / `utf-8-sig` defaults frozen inside `codebook.generate` instead of the resolved `[tool.sofer]` values that the MCP surface already passed. The CLI single-file branch now resolves `config.CSV_DELIMITER` / `config.CSV_ENCODING` at call time (beside the existing `max_sample` resolution, after `main()`'s single `config.reload(None)`) and turns an undecodable input or unknown codec into `Error: <message>` on stderr with a non-zero exit, instead of an uncaught traceback.

The maintainer chose **Option B** for the reader: `codebook._read_csv` is now a thin adapter over `_csv_reader.stream_csv`, so the repository has one CSV reader (AGENTS.md rule 4). Option A (bare `open()`) was rejected because it cannot walk the `utf-8-sig → utf-8` fallback that CB-R11 scenarios 3 and 5 require without re-rolling the chain — itself a rule-4 violation.

## Artifacts read

`proposal.md`, `specs/codebook/spec.md` (CB-R11 delta + Test Mapping), `design.md` (D1–D6, Option B), `tasks.md`, `apply-progress.md`, `verify-report.md`, and `openspec/config.yaml`.

## Delivery

| Commit | Subject |
| --- | --- |
| `6f078b3` | `fix(cli): read the configured CSV delimiter and encoding in 'sofer codebook FILE'` — `src/sofer/cli.py`, `src/sofer/codebook.py`, `tests/test_cli.py` |
| `b304963` | `docs(sdd): add the cli-codebook-config change artifacts` |

HEAD is `b304963`; the working tree was clean at archive time. Delivered as a single PR against `dev`, single work unit, no chaining, no `size:exception`, no tag movement.

**Final measured numbers** (reproduced independently by the verify phase):

- `uv run pytest tests/ -q` → `1772 passed, 6 skipped` versus a pre-change baseline of `1766 passed, 6 skipped` — **+6 tests, 0 failures, 0 removals**
- `bash scripts/check_core_coverage.sh` → exit 0, `src/sofer/cli.py` at **100%** with an **empty `Missing` column**
- `uv run mypy src/` → `Success: no issues found in 32 source files`, exit 0
- `uv run ruff check src/ tests/` → `All checks passed!`; `uv run ruff format --check src/ tests/` → `67 files already formatted`, exit 0
- TOTAL coverage unchanged at **93%** (config-owned floor stays `fail_under = 90`)
- Diff: exactly `src/sofer/cli.py`, `src/sofer/codebook.py`, `tests/test_cli.py` (+222 / −20); zero paths under `_converters.py`, `prepare.py`, `mcp_server.py` or `test_mcp_server.py`; `_csv_reader.py` byte-identical
- Review workload: 242 changed lines, inside the 400-line budget → single PR, no chain

## Spec Sync

**Absorbed into the canonical specs.** `openspec/specs/codebook/spec.md` now carries **CB-R11 — "Single-file codebook reads through the resolved tool-wide config"**, appended after CB-R10's final scenario with an `> Added by change \`2026-09-14-fix-cli-codebook-config\` (GitHub #182).` provenance line, the requirement clause, and all **five scenarios verbatim** from the delta. The sync is **purely additive**: `git diff --numstat` → `55 0` (55 insertions, **0 deletions**), so CB-R01…CB-R04 and CB-R06…CB-R10 keep their text byte-for-byte. No `MODIFIED`, `REMOVED` or `RENAMED` operation was involved, so no destructive-merge approval was required.

- **Domains synced**: `codebook` (1 of 1).
- **ADDED requirement names**: `CB-R11 — Single-file codebook reads through the resolved tool-wide config`.
- **MODIFIED / REMOVED / RENAMED requirement names**: none.
- **Active same-domain change warnings**: none — this was the only active change under `openspec/changes/*/specs/codebook/`, and the native status reported `sameDomainActiveChanges: []`.
- The canonical `codebook` spec has **no `## Test Mapping` section**; none was invented. The delta's mapping remains preserved in this archived folder.

**Archive-time sync fallback**: no `sync-report.md` existed for this change. The parent prompt explicitly approved and instructed the archive-time sync, and `tasks.md` § *Parent-Owned Lifecycle* already recorded it as an owner:"parent" step (*"Canonical spec sync of `openspec/specs/codebook/spec.md` (CB-R11) at archive time"*). The sync therefore ran here, after the Final Task Completion Gate passed.

## Option B — the decision and the blast radius it accepted

`codebook._read_csv` was rewritten as an adapter over `_csv_reader.stream_csv(path, delimiter=…, encoding=…, max_sample=None)` instead of keeping its own `open()`. Rationale: it makes CB-R11 scenario 5 true *by reuse* (configured encoding honoured first, then the repository's `utf-8-sig → utf-8` chain) and removes the duplicate reader for the codebook path (AGENTS.md rule 4).

The accepted cost is that this touches the shared `_read_file` CSV arm, which `--all-files` also uses. Verify confirmed each guardrail:

- **`;`-default repository unchanged** — the full suite is the detector: `1772 passed, 6 skipped`, 0 failures; the `--all-files` codebook tests are green.
- **`generate_all`'s explicit-parameter path undisturbed** — `codebook.py:522-523` still resolves the dataset-`[meta]` tier and passes `delimiter`/`encoding` explicitly into `_read_file` → `_read_csv`; `_read_tsv` still delivers a tab delimiter (2 TSV tests green).
- **`max_sample=None` passed explicitly** — the reader never applies `codebook_max_sample` on top of `generate`'s own `_build_markdown(max_sample)` cap, so rows are never capped twice.
- **Fallback-restart adapter branch genuinely exercised** — the undecodable-input tests make the reader restart under `utf-8-sig`/`utf-8`, so the partial-column reset executes rather than being defensive dead code.
- **Empty-file placeholder contract preserved** — `test_generate_empty_csv_returns_placeholder` green.

## Documented deviation — the two in-process coverage carriers

**Adjudicated legitimate by verify.** `uv run coverage run -m pytest` instruments only the test process and CI defines no `COVERAGE_PROCESS_START`, so the four subprocess-boundary tests cannot contribute to `cli.py`'s coverage (they are not "unreachable", their execution simply is not recorded). Without an in-process carrier the COV-06 per-file gate measured 99% with lines 264–266 missing. Two in-process carrier tests (`TestCodebookSingleFileDiagnosticArmsInProcess`) were therefore added for the new `ValueError` / `LookupError` diagnostic arms, following the existing `TestCodebookAllFilesErrors` precedent for the `--all-files` arm.

The delta's Test Mapping explicitly permits this (*"an in-process `_cmd_codebook` call MAY be added but MUST NOT replace the boundary test"*), and the carriers genuinely exercise the arms rather than proving them vacuously — they drive the real reader with real files (only the resolved config constants are monkeypatched), and deleting either `except` arm would make the test error. They **supplement** the boundary tests and replace none: `git diff --numstat -- tests/test_cli.py` → `158 0` (158 insertions, **0 deletions**). Result: `cli.py` back to 100.00% with an empty `Missing` column.

## Task completion

`tasks.md` carries exactly **19 `- [x]`** and **0 `- [ ]`** at archive time — re-verified immediately before the spec sync, the report write and the move. No unchecked implementation task line exists, so the archive was not blocked on completeness and **no stale-checkbox reconciliation was performed or needed**. The counts are deliberately 19/0 rather than including open verify/lifecycle boxes because the native provider counts checkboxes to decide whether `apply` has finished; the § *Verify Gates* and § *Parent-Owned Lifecycle* steps are plain non-checkbox text by design. **Do not re-add checkboxes to the archived `tasks.md`.**

## Structured status and `actionContext` findings

`artifactStore: openspec`, `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`, `tasks` 19/19 complete, `applyState: all_done`, `dependencies.verify: all_done`, `archive: ready`, `nextRecommended: "archive"`, `blockedReasons: []`, `remediationState.required: false`. Every archive write (the canonical spec append, the archive report, and the directory move) resolves inside the single allowed root, so no `blocked` condition applied and no `workspace-planning` restriction was in force. The verify report resolved and read as clearly passing at the authoritative locator.

## Destructive merge approvals / blockers

None. The sync applied one ADDED requirement only; no canonical requirement was removed or replaced, so the destructive-merge guard never triggered and no explicit destructive approval was required. No blocker was encountered during archive.

## Pre-existing findings — NOT regressions (left untouched, not fixed)

All four were proven outside the verified diff (`git diff` contains zero occurrences of the flagged symbols; each source line is identical at HEAD, merely shifted by the insertions above it) and were left unmodified:

- **`import tomli` in `cli.py`** — unresolved in the local static analyzer because `tomli` is not installed; the `tomllib` arm is live. Documented in AGENTS.md rule 12 as a known latent condition of this environment.
- **`shutil.move(str(src), str(dest))` region in `_cmd_init`** — HEAD L1019 → current L1046; outside every diff hunk.
- **`_read_jsonl`** — its bare `open` / `json.loads` advisories sit in an untouched function, shifted by the insertions above it.
- **`from conftest import …` convention** — the repo-wide pytest convention in `tests/test_cli.py`; pre-existing and unmodified.

## Accepted limitations (owned, not closed here)

- **#181** — the `prepare` conversion defect (delimiter outside `SNIFF_DELIMITERS` → one-column Parquet, `cfg.csv_encoding` never consulted). Explicit non-goal of this change; zero paths under `_converters.py` / `prepare.py` were touched. It has its own change and SDD cycle.
- **#202** — latent hardcoded defaults in `repo_compliance.py`. Outside this change's scope; left untouched.

## Files

`proposal.md`, `specs/codebook/spec.md` (delta), `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `archive-report.md` (complete).

## Engram mirror

Every artifact of this change is mirrored to Engram under the topic prefix `sdd/2026-09-14-fix-cli-codebook-config/` (`proposal`, `spec`, `design`, `tasks`, `apply-progress`, `verify-report`, `archive-report`; type `architecture`, project `sofer`). This archive report's observation is Engram id **1244** (topic key `sdd/2026-09-14-fix-cli-codebook-config/archive-report`).
