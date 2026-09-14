# Archive Report — 2026-09-13-fix-cli-console-encoding

**Change**: `2026-09-13-fix-cli-console-encoding` — cp1252 console streams crash the CLI with a raw `UnicodeEncodeError` instead of a degraded character
**Origin**: GitHub issue **emiliodavola/sofer#161** (`PYTHONIOENCODING=cp1252 sofer scan --help` → `rc=1`, `UnicodeEncodeError: '\u2192'`)
**Date**: 2026-09-13
**Artifact store**: `openspec` (repo-local planning home `openspec/`; `openspec/config.yaml` header declares the hybrid openspec+engram mode — archive ran file-backed per the `openspec` rules, and this report is also shadowed to Engram: observation ID **1210**, topic `sdd/2026-09-13-fix-cli-console-encoding/archive-report`, matching the newest archived-report precedent)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and no PR opened** — see *Delivery*)
**Verify verdict**: **`pass_with_warnings`** — `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 7/7`; the admitted `gentle-ai.verify-result/v1` envelope is the first block of `verify-report.md`
**Branch**: `fix/161-cli-console-encoding` @ working tree (HEAD **`1803acf`** `fix: revert Python version to 3.10`); **0 SDD-phase commits** (parent owns commits)
**Archived path**: `openspec/changes/archive/2026-09-13-fix-cli-console-encoding/`

## Summary

Accepted as one unit (no rollback) and archived. The change makes the CLI survive a console or redirected stream whose encoding cannot represent an emitted character, instead of aborting with a `UnicodeEncodeError` traceback — and closes the spec/test blind spot that let the defect ship behind a green suite.

What shipped (300 implementation lines across 5 files):

1. **Boundary encoding guard** — `src/sofer/cli.py` `_configure_console_streams()` (line 1557), called as the **first statement of `main()`** (line 1606), before `_build_parser()` / `parse_args()`. Each of `sys.stdout` / `sys.stderr` is reconfigured **in place** (`stream.reconfigure(errors=config.CONSOLE_ERRORS)`, line 1584) behind an `isinstance(stream, io.TextIOWrapper)` capability check with a `try/except (ValueError, OSError)` arm, so an unreconfigurable stream (an in-memory capture object, pytest's captured stdout, a closed wrapper) is left untouched rather than raising. No stream swapping — the MCP `_capture_output` path (MSP-R01 stdout cleanliness) is undisturbed.
2. **`CONSOLE_ERRORS: str = "replace"`** — `src/sofer/config.py:361`, a **module constant, deliberately not a `_DEFAULTS` entry** (Decision D3): substitution is visible (`?`), never silent; no new `[tool.sofer]` surface and therefore no `tool-config` spec delta.
3. **Five ASCII edits** — the `U+2192` glyph the CLI itself authors at `cli.py:1072`, `:1073`, `:1429` (three argparse `description=` strings) and `cli.py:549`, `:569` (the `scan` confirm preview and `--dry-run` prints) became `->`. The other 58 `print()` sites keep their glyphs, now protected by the guard.
4. **Docs** — one mirrored "Console encoding" row in the existing *Windows notes* table of `README.md` and `README_ES.md` (AGENTS.md rule 13), one line each.
5. **Tests** — `tests/test_cli.py` +237/−5: the cp1252 help boundary parametrized over all 12 invocations, real runtime console paths (`validate` config-error, `scan --dry-run`), the warning path (`codebook --all-files`), the interpolated-value paths, and the guard's own rule-14 arms — all through the shared `tests/conftest.py::run_cli` subprocess helper (PB-09 reused, never re-implemented).

**Final verification state is `pass_with_warnings`, and the evidence is deliberately interpreter-split** (final, not a defect):

- the mandated **test** command was captured in the **ambient venv** (Python 3.10.20): `uv run pytest tests/ -q` → **1766 passed, 6 skipped**, rc 0, `test_output_hash: sha256:be8b556f…de0e`;
- the mandated **build** command and the rule-14 / COV-06 gate were captured under the **CI interpreter** (`UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13`): `ruff check` clean, `mypy` clean (32 files), `bash scripts/check_core_coverage.sh` rc 0 with all four gated files at 100%, `BrPart 0`, zero `# pragma: no cover`, `build_output_hash: sha256:beb5f2fb…a3d7`.

The local 3.10 reds (5 × mypy `[no-redef]` on the **untouched** `tomli`/`tomllib` fallback sites; `cli.py` 99% at `Missing 439-440`) are the pre-existing condition AGENTS.md rule 12 already documents, **diagnosed and tracked as issue #178**; `.github/workflows/ci.yml` pins the lint job (`:15`) and the coverage job (`:61`) to 3.13, where both are green.

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (`sync-report.md` status `synced`, archived with this change). Archive reads a *completed* sync; it does not perform one. No archive-time sync fallback was needed or executed. The only archive-time canonical edits are the two provenance lines normalized below.

| Field | Value |
|---|---|
| Domains synced | **`process-boundary`** and **`cli`** (2 of 2) |
| ADDED requirements | **`Console output survives an unencodable character (CLI-R11)`** — 3 scenarios |
| MODIFIED requirements | **`CLI user-visible output via executable subprocess (PB-02)`** — full-block replacement in place (same ID, heading, position); 3 scenarios → 4 (one expanded in place, one added, two carried byte-identical) |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical delta | `openspec/specs/cli/spec.md` **+32** (CLI-R11 appended after CLI-R10); `openspec/specs/process-boundary/spec.md` **+16/−3** (the PB-02 block replacement — the 3 deletions are the old PB-02 prose line and the two old cp1252-help bullets the delta itself replaces) |
| Canonical outcome | `cli` **10 → 11** requirements, **45 → 48** scenarios; `process-boundary` **9 → 9** requirements, **30 → 31** scenarios |
| Destructive merge | **Not applicable** — ADD 1 / MODIFIED 1 (non-destructive, ID and position preserved, both pre-existing scenarios proven byte-identical) / REMOVED 0; `openspec/config.yaml` `rules.archive` ("Warn before merging destructive deltas.") **honored** — nothing destructive was merged, no destructive approval was required or given |
| Same-domain collisions | **none** — no other active change touches either canonical spec (the only non-archive change dir was this one) |

### Provenance normalization (archive-time, step 4)

The repo convention is documented and explicit — `openspec/changes/archive/2026-09-11-fix-status-resource/sync-note.md` lines 19–26: *"Provenance line updated on merge (repo convention — verified against 40+ existing lines in `openspec/specs/`; MODIFIED form matches `mcp-server/spec.md` …)"* and *"canonical single-line blockquote with the archive-date convention (`(archived 2026-09-11)`); the `issue #146` reference lives in this delta + `verify-report.md` (**canonical provenance carries no `issue #` refs** …)"*. The two immediately preceding archive passes on the same day (`2026-09-13-ci-coverage-codeql`, `2026-09-13-raise-per-file-coverage`) both normalized their provenance line to `(archived 2026-09-13)` per the same instruction, and the option was pre-flagged by `sync-report.md` §11. The convention is therefore **established, not ambiguous**, and both lines were normalized (date unchanged — archive date 2026-09-13 equals the provenance date):

```diff
# openspec/specs/process-boundary/spec.md:59  (PB-02, directly under the requirement heading)
- > Modified by `2026-09-13-fix-cli-console-encoding` (GitHub #161).
+ > Modified by `2026-09-13-fix-cli-console-encoding` (archived 2026-09-13).

# openspec/specs/cli/spec.md:378  (CLI-R11, inside the requirement block, matching CLI-R05/R06/R09)
- > Added by change `2026-09-13-fix-cli-console-encoding` (GitHub #161).
+ > Added by change `2026-09-13-fix-cli-console-encoding` (archived 2026-09-13).
```

Two lines changed, nothing else — no requirement text, scenario, heading, RFC 2119 keyword, or surrounding prose touched. Per the documented convention the `(GitHub #161)` issue reference is **dropped from the canonical line and preserved in the change artifacts** (proposal, both deltas, `sync-report.md`, `verify-report.md`, this report) — the same disposition `fix-status-resource` applied to `issue #146`. **Minority precedent, recorded honestly:** six archived changes still carry an un-normalized issue-form provenance (`fix-scan-parity-mcp` `(closes #154)`/`(closes #152)`, `fix-residual-parity` `(closes #153)`/`(closes #155)`, `fix-xlsx-staged-parquet-warning` `(closes #150)`, `fix-mcp-opencode-env` `(closes #147)`, `2026-09-13-test-mcp-injection-semantics` / `2026-09-13-fix-prompt-intro-repr` descriptive form); those were synced mid-flight and never went through an archive normalization pass, so they are gaps in application, not a competing convention.

## Verification Evidence

| Gate | Result |
|---|---|
| Native verify envelope | `gentle-ai.verify-result/v1` as the first block of `verify-report.md`: `verdict: pass_with_warnings`, `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 7/7`, `test_exit_code: 0`, `build_exit_code: 0`, `evidence_revision: sha256:1399e1cd7bb6e4b58ce1966eca42be8da9b5cf6026b09af6762d0ee6781a28db` |
| Envelope admission | `gentle-ai sdd-verify-validate --input <verify-report.md> --requirements 2 --scenarios 7` → **exit 0**, `{"valid": true, "verdict": "pass_with_warnings"}` |
| Pytest (ambient 3.10) | `uv run pytest tests/ -q` → **1766 passed, 6 skipped**, 14 warnings, rc **0** (61.09s); `sha256:be8b556f…de0e`; measured pre-change baseline **1747 passed / 6 skipped** → delta exactly **+19**; `tests/test_cli.py` collects **166**; `-k cp1252` = **17** |
| Pytest (CI interpreter 3.13) | `UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 pytest tests/ -q` (packaging test deselected, trap documented in `verify-report.md` §6 `V-04`) → **1765 passed, 6 skipped, 1 deselected** |
| Build (CI interpreter) | `ruff check src/ tests/` → `All checks passed!`; `mypy src/` → `Success: no issues found in 32 source files`; `mypy src/ scripts/` → 33 files; `sha256:beb5f2fb…a3d7` |
| Rule-14 / COV-06 gate (CI interpreter) | `bash scripts/check_core_coverage.sh` → **rc 0**; `cli.py` 574 stmts / 166 branch, `scanner.py` 159/76, `prepare.py` 432/226, `publish.py` 326/138 — **all four 100%, `BrPart 0`**; zero `# pragma: no cover` in the four gated files |
| RED / GREEN | RED reproduced against HEAD's `src` (`8 failed`), GREEN on the working tree (`20 passed` focused selection, `1766 passed` full); the `V-01` closure test's RED re-reproduced at HEAD `cli.py:474` (the crash came from the **interpolated** value behind an already-ASCII `-> raw/` literal) |
| Whitespace / scope | `git diff --check` rc 0; no scope drift (every changed line traceable to tasks 3.1–3.5 / 1.1–1.8 / 6.1–6.2) |
| Strict TDD | **N/A** — `strict_tdd: false` in `openspec/config.yaml`; apply-progress records the section as not applicable; the design still demanded provable RED and verify reproduced it independently |

### Scenario → test mapping (final form)

7 frozen scenarios, all with a named passing test (AGENTS.md rule 6):

| Requirement | Scenario | Test (`tests/test_cli.py`, `TestSubprocessBoundary` unless noted) | Outcome |
|---|---|---|---|
| PB-02 | Help via subprocess | `test_help_exits_zero_and_lists_every_subcommand` | PASSED |
| PB-02 | cp1252 help on the ubuntu matrix (12 invocations) | `test_help_strict_cp1252[argv0…argv11]` (parametrized over `--help`, 9 × `<cmd> --help`, `mcp add --help`, `mcp remove --help`) | 12 × PASSED |
| PB-02 | cp1252 runtime console output | `test_runtime_output_strict_cp1252` (validate half) + `test_scan_dry_run_strict_cp1252` (dry-run half) | 2 × PASSED |
| PB-02 | Dispatch exit codes | `test_unknown_command_exits_2` | PASSED |
| CLI-R11 | Runtime output with an unencodable character keeps the command's result | `test_runtime_output_strict_cp1252` (shared with the PB-02 runtime scenario) | PASSED |
| CLI-R11 | ASCII literal with an unencodable interpolated value does not abort | `test_interpolated_unencodable_value_strict_cp1252` (**stderr** / argv vector) **+** `test_interpolated_stdout_value_strict_cp1252` (**stdout** / TOML-declared-path vector, added by the `V-01` closure, +37 lines) | PASSED (both halves) |
| CLI-R11 | Console warning path carrying a glyph degrades instead of aborting | `test_codebook_warning_strict_cp1252` | PASSED |
| CLI-R11 | normative clause, rule-14 arms (not a frozen scenario) | `TestConsoleEncodingGuard::test_console_streams_reconfigured_in_place` / `::test_console_guard_skips_stream_without_reconfigure` / `::test_console_guard_survives_unreconfigurable_text_wrapper` | 3 × PASSED |

**`V-01` closure (final-state handoff fact 1, which outranks the frozen `verify-report.md` wording):** `V-01` — CLI-R11 scenario 2's **stdout** clause had no test — was **CLOSED after the verify report was first written**, by a bounded **test-only** follow-up recorded in `apply-progress.md` § `V-01 closure` (`tests/test_cli.py` only, +37 lines; `src/**`, `README*`, `openspec/specs/**`, `tasks.md`, `verify-report.md`, `tests/conftest.py` and the frozen deltas untouched). Ambient suite **1765 → 1766 passed / 6 skipped**; `test_cli.py` 165 → 166; `-k cp1252` 16 → 17. The frozen verify report still carries the pre-follow-up wording **by design**; the mapping above is the final state.

**Explicitly not verified (with reason, unchanged):** (1) PB-02's *"run on the ubuntu CI matrix"* clause — no CI run was executed from this Windows host; the local equivalent (child process forced to `PYTHONIOENCODING=cp1252`, `errors="strict"` decoding) was executed and `ci.yml` statically inspected; (2) the *"Windows-only behavior SHALL skip without privileges"* clause — this change adds no Windows-only test, so the clause is untouched, not proven.

## Open Non-Blocking Findings (recorded, **not fixed here**)

| ID | Finding | Disposition |
|---|---|---|
| `V-02` | Assertion-quality note: `result.stdout.encode("cp1252")` / `stderr.encode("cp1252")` is a **round-trip tautology** (`run_cli(..., encoding="cp1252", errors="strict")` already decoded those bytes from cp1252). Every test T1–T5 has a real discriminator (`rc`, ASCII substring, absence of a traceback), so **no test is vacuous** — the encodability assertions simply contribute nothing | No issue; worth a one-line comment if the tests are ever touched |
| `V-03` | Repo-wide `uv run ruff format --check src/ tests/` is red on **six untouched files** (pre-existing drift; the branch does not regress it, but the repo-wide formatter gate as written in `tasks.md` 7.2 cannot pass on `dev` either) | Filed as GitHub issue **#177** |
| `I-01` | Test isolation: `HF_TOKEN` leaks out of `test_mcp_server.py` into `test_mcp_registration.py`; full-suite greenness depends on alphabetical file ordering | Filed as GitHub issue **#176** |
| `I-02` | Stale test-count documentation (`AGENTS.md` rule 6 says `1149/2`; `openspec/config.yaml` says `1029/2`; measured is `1766/6`) | Already covered by existing issue **#162** — **no duplicate filed** |
| `V-04` | Local `.python-version` = 3.10 pin makes the ambient `mypy` and the COV-06 coverage gate red (5 × `[no-redef]` on untouched `tomli`/`tomllib` fallback sites; `cli.py` 99% at `Missing 439-440`) while CI's 3.13 jobs are green | Filed as GitHub issue **#178**; diagnosed and pre-existing — **not a defect of this change** |

## Non-Goals That Stayed Out

Nine declared non-goals, all honored by the final diff:

1. **Normalizing the remaining 58 Metric-A `print()` sites to ASCII** — glyphs preserved; the guard protects them.
2. **Forcing UTF-8 globally** (`PYTHONUTF8` / `sys.flags.utf8_mode` / re-exec) — would change `locale.getpreferredencoding` for dataset reads pinned by the `data-quality` capability.
3. **Changing file-output encodings** — quality report / codebook markdown / Dataset Card keep their explicit UTF-8 (`config.OUTPUT_ENCODING`); no writer file appears in the diff.
4. **`errors="ignore"`** — rejected as silent output loss; `"replace"` (visible `?`) chosen.
5. **Mutating the user's environment** (`PYTHONIOENCODING`, `PYTHONLEGACYWINDOWSSTDIO`, `chcp`) — outside a CLI's remit.
6. **The MCP capture path** — no defect there; MSP-R01 stdout cleanliness undisturbed.
7. **ASCII-ifying spec prose** — `openspec/specs/cli/spec.md` still contains `raw/→cache/→build/` (CLI-R02) and was deliberately **not** touched; the sync verification asserts this explicitly.
8. **A new `[tool.sofer]` option** (`console_errors`) and the `tool-config` delta it would require — Decision D3 chose a module constant; no `_DEFAULTS` entry.
9. **Translating/reflowing help text, changing report widths, or making the exit code depend on an encoding failure.** Also: no second subprocess helper (`tests/conftest.py` untouched, PB-09), no glyph assertion (so the tests do not pre-commit the strategy), no stream swapping, no pragma.

## Rollback

**Plain revert — one unit.** No persisted state, no data migration, no new config surface, no schema change, no dependency added: reverting `src/sofer/cli.py` (+44/−5), `src/sofer/config.py` (+7), `tests/test_cli.py` (+237/−5), `README.md` (+1), `README_ES.md` (+1) restores the prior behavior exactly — cp1252 consoles crash as before. The only user-visible artifacts are the five ASCII edits and the README note, both trivially revertible. **Rollback of the archive itself** is lossless: move the folder back to `openspec/changes/2026-09-13-fix-cli-console-encoding/` and drop `archive-report.md`; reverting the two provenance lines is a one-line-each edit. Nothing under `openspec/changes/archive/**` was deleted or modified.

## Task Completion Gate (re-read immediately before the archive report write and the move)

Persisted tasks artifact re-read at `openspec/changes/2026-09-13-fix-cli-console-encoding/tasks.md` **before** the sync/report write and the folder move:

```text
$ grep -n "^\s*- \[ \]"  .../tasks.md   → no match (rc=1)
$ grep -c "^\s*- \[x\]"  .../tasks.md   → 38
$ grep -cE "^\s*- \[[ x]\]" .../tasks.md → 38
```

**38/38 boxes checked — zero `- [ ]` markers remain, implementation or parent.** The two `sdd-owner: parent` lifecycle rows (8.1 bounded review, 8.2 accept-vs-rollback + trigger archive/sync) were **closed by the parent**, matching the native status (`taskProgress: 38/38 complete`, `deferredParentActions: 2/2 complete`, `unchecked: []`). **No mechanical checkbox repair was performed and none was needed** — nothing was flipped by this phase.

**The `- [ ]` implementation-task lines that would have blocked archive: NONE.** The `V-01` closure added no task row, so no checkbox was left behind by the follow-up.

## Structured Status & actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` | archive ran file-backed per the openspec rules; the canonical merge was already performed by the sync phase; no archive-time sync fallback |
| `planningHome` | repo-local `openspec/` | every required artifact read from disk before the move: `proposal.md`, `specs/{cli,process-boundary}/spec.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `sync-report.md`, `explore.md`, `preproposal.md`, `openspec/config.yaml` |
| `actionContext.mode` | `repo-local`, `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` | no `workspace-planning` gate applies; every path written this pass (report, move target, the two provenance lines) is inside the authoritative workspace and allowed edit root — **no stop condition fired** |
| `dependencies` (in the parent's intermediate snapshot) | `verify: ready`, `sync: blocked`, `archive: blocked` | the native pipeline ordering rule, resolved from artifacts + the parent's final-state facts (which outrank the snapshot): verify report present with the admitted envelope (`pass_with_warnings`, 0 blockers / 0 CRITICAL), `V-01` closed by the test-only follow-up, `sync-report.md` status `synced`, both canonical specs updated → **archive state `ready`, `next: archive`** |
| `taskProgress` / `deferredParentActions` | 38/38 complete / 2/2 complete / `unchecked: []` | confirmed against the persisted artifact (see Task Completion Gate) |
| `relationships` / `collisions` | `[]` / `[]` | archive's own scan found no other active change: after the move, `openspec/changes/` contains only `archive/` |
| `rules.archive` | *"Warn before merging destructive deltas."* | honored — no destructive delta; the only canonical edits are the two convention-mandated provenance lines |
| Review decision (parent row 8.1) | receipt-driven-development switch **off** (`gentle-ai review mode status` → `off (decided by default)`) | no bounded review transaction was started for this candidate and **no review authority was minted** — the owner's decision, not a skipped review |

## Archive Mechanics

- **`git mv` / any git write command: NOT used** (explicit constraint — the parent versions everything). The whole change root was untracked (`git ls-files <change dir>` → **0 tracked files**; `git status` reports `?? openspec/changes/2026-09-13-fix-cli-console-encoding/`), so the move is a **plain filesystem rename** into `openspec/changes/archive/` — identical audit-trail outcome, since the parent's upcoming commit will add these files at their final archived path.
- **Files archived (11, moved):** `proposal.md`, `preproposal.md`, `explore.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `sync-report.md`, `specs/cli/spec.md`, `specs/process-boundary/spec.md` + `archive-report.md` (written into the change root **before** the move per the openspec-mode contract, then moved with the tree). The full change directory is preserved — nothing pruned, `explore.md` / `preproposal.md` included (10 archived changes keep their `explore.md`).
- The vacated `openspec/changes/2026-09-13-fix-cli-console-encoding/` tree was removed (empty).
- **Audit trail intact:** active artifacts were **moved, never deleted or modified**. The only content edits of this pass are the two documented canonical provenance lines. Nothing under `src/**`, `tests/**`, `README*`, `AGENTS.md`, `openspec/changes/archive/**`, or any sibling change directory was touched.
- **No commit made, nothing staged** — the parent commits the move and this report.

### Sanity checks run and reported

```text
$ grep -c "^### Requirement" openspec/specs/cli/spec.md               → 11   (expected 11) ✓
$ grep -c "^### Requirement" openspec/specs/process-boundary/spec.md  → 9    (expected 9)  ✓
$ grep -c "^#### Scenario"   openspec/specs/cli/spec.md               → 48
$ grep -c "^#### Scenario"   openspec/specs/process-boundary/spec.md  → 31   (matches sync-report)
$ ls openspec/changes/                                                → archive/ only ✓
$ grep -rn "pragma: no cover" src/sofer/{cli,scanner,prepare,publish}.py  → no match ✓ (the four
    rule-14 gated files carry ZERO pragmas; the two pragma tokens in the tree are
    src/sofer/mcp_registration.py:350 and src/sofer/mcp_server.py:75 — both BYTE-IDENTICAL to HEAD,
    outside this change's diff, and outside the four gated modules, so rule 14 is unviolated)
$ git status --porcelain  (reported, not changed — the parent commits)
 M README.md                     (the change's own 300-line implementation diff)
 M README_ES.md
 M openspec/specs/cli/spec.md            (sync + the archive provenance line)
 M openspec/specs/process-boundary/spec.md  (sync + the archive provenance line)
 M src/sofer/cli.py
 M src/sofer/config.py
 M tests/test_cli.py
?? openspec/changes/archive/2026-09-13-fix-cli-console-encoding/   (untracked after the move)
$ gentle-ai sdd-status → no longer lists 2026-09-13-fix-cli-console-encoding as an active change ✓
```

## Delivery

| Field | Value |
|---|---|
| Branch | `fix/161-cli-console-encoding` @ working-tree diff (HEAD `1803acf`, on top of the #175 merge); **0 SDD-phase commits**, nothing staged |
| PR | **NOT opened** — parent-owned: work-unit commits → **single PR into `dev`** via `.github/PULL_REQUEST_TEMPLATE.md` with the real verification output from the verify report |
| Implementation size | **300 changed lines across 5 files** — `tests/test_cli.py` +237/−5, `src/sofer/cli.py` +44/−5, `src/sofer/config.py` +7, `README.md` +1, `README_ES.md` +1 — **single PR, no chain, no `size:exception`** |
| Canonical-spec sync | **51** further lines (cli +32, process-boundary +16/−3), charged to the sync phase, not the code-review surface |
| Review budget | 300 implementation lines (351 with the sync output) — both well under the 400-line threshold and the 1500-line session review budget; 400-line chain risk **Low**, confirmed |
| Merge target | `dev` only (AGENTS.md rule 12); `main` receives changes only via release-time merges from `dev` |
| Issue | Closes GitHub **#161** (the #177/#178/#176 findings are separate, already-filed issues) |
| Release / tag | **none** — no version bump (hatch-vcs derives the version from tags); no tag pushed |
| Post-archive watch | CI on `dev` for the PR (ubuntu / Python 3.13) — the four 100% rule-14 rows are binary gates with no margin by design; PB-02's ubuntu-matrix clause is the one thing never exercised locally |

## Next Steps

1. **Parent:** commit the work units on `fix/161-cli-console-encoding` (implementation + docs + tests, then the canonical spec sync and the archive move/report) and open the single PR into `dev`, filling the PR template with the real verification output from `verify-report.md`.
2. **Post-merge:** watch the CI arbiter (ubuntu / Python 3.13) and the rule-14 coverage job; close issue #161 on merge.
3. **Separate, already-filed housekeeping (do not fold into this PR):** #176 (`HF_TOKEN` test-isolation leak), #177 (repo-wide `ruff format --check` drift), #178 (`.python-version` 3.10 dev-env mismatch), #162 (stale test-count prose).
