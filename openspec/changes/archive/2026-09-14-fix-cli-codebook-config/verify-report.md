```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:b2612c30c06e48cbd591bab6de90e7ccc1feadf27d0d589f04c1f0bd9b7e437e
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 5/5
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:640a0b5db38137126961f8da42afa407eaa4e5019c4e5ca389524384d27df80e
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
```

# Verify Report — `2026-09-14-fix-cli-codebook-config` (issue #182)

**Verdict: PASS** · Branch `fix/182-cli-codebook-config` · Store: hybrid (this file + Engram topic key `sdd/2026-09-14-fix-cli-codebook-config/verify-report`).
**Artifacts read:** `proposal.md`, `specs/codebook/spec.md` (CB-R11 delta + Test Mapping), `design.md` (D1–D6, Option B), `tasks.md` (19/19), `apply-progress.md`, and the working-tree diff.

## Hash provenance (reproducible)

- `evidence_revision` — `sha256` of `git diff` output over the three modified tracked files (`src/sofer/cli.py`, `src/sofer/codebook.py`, `tests/test_cli.py`); the untracked `openspec/changes/**` are spec/test-plan text, not the code candidate.
- `test_output_hash` — `sha256` of `/tmp/verify_full.txt`, captured from `uv run pytest tests/ -q > /tmp/verify_full.txt 2>&1`.
- `build_output_hash` — `sha256` of `/tmp/verify_build.txt`, captured from `uv run ruff check src/ tests/ > /tmp/verify_build.txt 2>&1 && uv run mypy src/ >> /tmp/verify_build.txt 2>&1`.

## Structured status and `actionContext`

Native status: `artifactStore: openspec`, `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`, `tasks` 19/19 complete, `applyState: all_done`, `verify: ready`, `blockedReasons: []`. Every changed path resolves inside the single allowed root, so no `blocked` condition applied. Runtime gate: `sdd-attempt acquire` with the pre-existing active token `sha256:f2bc4d99…a5c2f0` returned `state: proceed` (the existing attempt was continued, not replaced).

## Task completion

`openspec/changes/2026-09-14-fix-cli-codebook-config/tasks.md`: **0** unchecked implementation markers (`^\s*- \[ \]`) and **19** checked (`- [x]`). The non-checkbox `§ Verify Gates` and `§ Parent-Owned Lifecycle` sections were left as intended. No unchecked implementation task lines exist, so archive is not blocked on completeness.

## CB-R11 coverage — 1 ADDED requirement, 5 scenarios (all mapped, all reproduced)

| # | Scenario | Evidence |
|---|---|---|
| 1 | Configured delimiter/encoding reflected | `tests/test_cli.py::TestCodebookToolConfigParity::test_codebook_honors_tool_sofer_delimiter` (`csv_delimiter = ","` → asserts `\| 1 \| \`name\`` and `\| 2 \| \`age\``) and `…::test_codebook_honors_tool_sofer_encoding` (`cp1252`-only byte `0xE1` succeeds). Both drive `run_cli`, both GREEN. |
| 2 | CLI and MCP agree; no MCP edit | CLI twin asserts the exact two structural strings the MCP test asserts. `git diff --quiet -- src/sofer/mcp_server.py tests/test_mcp_server.py` → unchanged; 13 MCP codebook tests GREEN, including `test_codebook_honors_tool_sofer_delimiter`. Parity rests on real asserted output, not a comment. |
| 3 | Undecodable input → diagnostic, no traceback | `…::test_codebook_undecodable_file_is_diagnostic` (byte `0x81`): `rc == 1`, stderr starts `Error: `, contains `Cannot decode`, `"Traceback" not in stderr`. GREEN. |
| 4 | Unknown codec → same diagnostic | `…::test_codebook_unknown_codec_is_diagnostic` (`csv_encoding = "not-a-codec"`): same three assertions plus `not-a-codec in stderr`. GREEN. |
| 5 | Existing fallback policy only | `_csv_reader.py` byte-identical (`git diff --quiet` → unchanged); `ENCODING_FALLBACKS = ["utf-8-sig", "utf-8"]` is the sole chain. Precedent `tests/test_quality.py::test_encoding_fallback_latin1` (`latin-1 → ValueError("Cannot decode")`) still GREEN. The scenario-3 test's `rc == 1` is substantive here: byte `0x81` *is* decodable by latin-1, so a latin-1/cp1252 rescue would have produced `rc == 0` — the test would fail if such a retry existed. |

**No scenario has weaker evidence than the others.** Scenario 5 is the only one that is *partly* by construction (untouched reader + constant) rather than a dedicated new assertion, but the scenario-3 test supplies the behavioural falsifier described above, and the `[tool.sofer]` fallback policy lives in exactly one unchanged place — no second hand-rolled chain exists in `codebook.py` (`grep` confirms zero `csv.reader` / `ENCODING_FALLBACKS` hits there).

## Adjudication — the two in-process coverage carriers

**Legitimate.** The delta's Test Mapping explicitly permits it: *"an in-process `_cmd_codebook` call MAY be added but MUST NOT replace the boundary test."* Apply added `TestCodebookSingleFileDiagnosticArmsInProcess` (2 tests) and kept all 4 boundary tests. The in-process tests genuinely exercise the arms rather than proving them vacuously:

- They call `cli._cmd_codebook(Namespace(...))` with real files and the **real** reader — no mock of the exception path; only `config.CSV_DELIMITER`/`CSV_ENCODING` are monkeypatched. `0x81` under cp1252 and `"not-a-codec"` produce the real `ValueError` / `LookupError`.
- If either `except` arm were deleted, the exception would escape `_cmd_codebook` and the test would error — the tests discriminate the fix, not merely execute it.
- Coverage reproduces: after a fresh `uv run coverage run -m pytest`, `bash scripts/check_core_coverage.sh` → **exit 0**, `src\sofer\cli.py 580 stmts, 0 miss, 166 branch, 0 BrPart, 100%`, **empty `Missing` column**. The apply-reported `99% / Missing 264-266` state is gone.

The premise is correct: `coverage run -m pytest` instruments only the test process and no `COVERAGE_PROCESS_START` is defined, so `run_cli` subprocess execution is not recorded. The carrier mirrors the repo's existing `TestCodebookAllFilesErrors` precedent for the `--all-files` arm.

**Boundary tests were not removed or weakened:** `git diff --numstat -- tests/test_cli.py` → `158 0` (158 insertions, **0 deletions**). The addition is purely additive; the delta requires the boundary tests and they are present and GREEN.

## Option B blast radius (widened by `codebook._read_csv` → `stream_csv`)

- **`;`-default repository unchanged:** full suite is the detector — `1772 passed, 6 skipped`, 0 failures. The `--all-files` codebook tests (including `TestCodebookAllFilesErrors`, `test_codebook_all_files_max_sample_parity`, `test_codebook_warning_strict_cp1252`) are GREEN.
- **`generate_all` explicit-parameter path undisturbed:** `codebook.py:522-523` still resolves `cfg.csv_delimiter` / `cfg.csv_encoding` from the dataset `[meta]` tier, and passes them explicitly into `_read_file` → `_read_csv`; the `_read_file` and `_read_tsv` signatures are intact (`_read_tsv` still delivers a tab delimiter; 2 TSV tests GREEN).
- **`max_sample=None` explicit, no double cap:** `codebook.py:95` passes `max_sample=None` into `stream_csv`, so the reader never applies `codebook_max_sample`; sampling happens once, in `_build_markdown`.
- **Fallback-restart adapter branch is genuinely exercised:** the undecodable-input tests make the reader restart under `utf-8-sig`/`utf-8`, so the partial-column reset executes rather than being defensive dead code.
- Empty-file placeholder contract preserved: `test_generate_empty_csv_returns_placeholder` GREEN.

## Commands run (exact)

| Command | Result | Exit |
|---|---|---|
| `uv run pytest tests/ -q` | `1772 passed, 6 skipped, 1 warning in 54.96s` | 0 |
| `uv run pytest tests/test_cli.py tests/test_codebook.py -q` | `253 passed, 1 skipped, 1 warning in 23.53s` | 0 |
| `uv run coverage run -m pytest -q` then `bash scripts/check_core_coverage.sh` | `cli.py 100%`, empty `Missing`; `scanner`/`prepare`/`publish` 100% | 0 |
| `uv run mypy src/` | `Success: no issues found in 32 source files` | 0 |
| `uv run ruff check src/ tests/` | `All checks passed!` | 0 |
| `uv run ruff format --check src/ tests/` | `67 files already formatted` | 0 |
| `git diff --stat` / `--name-only` | exactly `src/sofer/cli.py`, `src/sofer/codebook.py`, `tests/test_cli.py` | — |
| `git diff --name-only \| grep -E "_converters.py\|prepare.py\|mcp_server.py\|test_mcp_server.py"` | no output (zero forbidden paths) | — |

**Baseline accounting (independently reproduced).** With the three files stashed to HEAD: `1765 passed, 1 failed, 6 skipped` — the single failure is `test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present` reading a `.coverage` DB whose execution data predates the reverted source (the same foreign-DB artifact class apply documented). Since `1765 + 1 + 6 = 1772` collected, the pre-change baseline is **1766 passed, 6 skipped** once that artifact is absent — exactly the apply-reported baseline. Post-change: `1772 passed, 6 skipped` collected `= 1778`, i.e. baseline `+6`. The six added tests are exactly the 4 `TestCodebookToolConfigParity` boundary tests plus the 2 `TestCodebookSingleFileDiagnosticArmsInProcess` carriers (verified: `-k` run → `6 passed, 166 deselected`). **+6 tests, zero failures, zero removals.**

## Strict TDD

Not active: `openspec/config.yaml` `strict_tdd: false` and no strict-TDD evidence was asserted in `apply-progress.md`. A `TDD Cycle Evidence` table is therefore not required and was not expected; no strict-TDD finding is raised.

## Assertion quality of the added tests (audited)

All six assert on rendered output and process outcome, not on internals: `returncode`, `stderr` prefix/content, absence of `Traceback`, and specific markdown column rows (`\| 1 \| \`name\``, `\| 2 \| \`age\``). No tautologies, no ghost loops, no type-only assertions, no smoke-only tests, no CSS/implementation-detail coupling. The two in-process carriers assert `rc == 1` and the `Error: ` stderr envelope. Quality is sound.

## Review workload / PR boundary

Forecast: `~70` changed lines, `400`-line budget risk **Low**, `Chained PRs recommended: No`, single PR, `Chain strategy: pending`. Actual: `242` changed lines (`33+6`, `31+14`, `158+0`) — inside the canonical 400 threshold, so single PR / no chain. No scope creep: the diff is confined to the three declared files; `_converters.py`, `prepare.py`, `mcp_server.py`, `test_mcp_server.py`, `_csv_reader.py` are byte-identical, and the `codebook.generate`/`generate_all` signatures/defaults and the dataset-`[meta]` tier are untouched. No `size:exception` was used or needed.

## Pre-existing findings — NOT regressions (left untouched, not fixed)

The pi-lens/static analyzer surfaced the same advisories apply reported. Proven outside the verified diff: `git diff` contains **0** occurrences of `tomli`, `shutil.move`, `_read_jsonl`, or `from conftest`, and each flagged source line is identical at HEAD, merely shifted by the insertions above it (e.g. `shutil.move(str(src), str(dest))` HEAD L1019 → current L1046; `_read_jsonl`'s `open`/`json.loads` HEAD L230/L235 → current L247/L252; `from conftest import run_cli` HEAD L16 unshifted). These are pre-existing conditions of this environment, explicitly out of scope (AGENTS.md rule 12), and were **not** modified.

## `.coverage` artifact adjudication

**Cleared.** After the mandated fresh `uv run coverage run -m pytest`, `tests/test_coverage_contract.py` reports `3 passed` in isolation, and both full runs (plain and under coverage) tally `1772 passed, 6 skipped` — the spurious `TOTAL 89.8%` apply observed while an old `.coverage` DB was measured against new source does not reproduce. This is the documented "old execution data vs new source" artifact, not a product defect; on a clean checkout the DB is absent and the test skips (CI-unaffected).

## Blockers

None. `verdict: pass`, `blockers: 0`, `critical_findings: 0`.

## Risks (carried)

- The `_read_tsv` diff line spells the tab delimiter as a literal tab instead of the escape `"\t"` — semantically identical and formatter-clean, but a reviewer may read it as a change; it is cosmetic only.
- Rollback remains a single revert of 3 files (no migration, no persisted artifact, no config/workflow surface).

## skill_resolution

`none` — no executor/phase skill path was injected for this verify phase, and no project/user verify skill was available in the injected list; no fallback loading was required (read-only verification plus the repo's own test/coverage gates).
