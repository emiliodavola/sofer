# Archive Report — 2026-09-14-fix-prepare-csv-config-tier

**Change**: `2026-09-14-fix-prepare-csv-config-tier`
**Issue**: GitHub #181 (prepare ignored the dataset's declared CSV dialect)
**Date**: 2026-09-14 (archived 2026-09-14)
**Artifact store**: `openspec` (this file) mirrored to Engram `sdd/2026-09-14-fix-prepare-csv-config-tier/archive-report` (observation id `1251`)
**Status**: **archived — PASS** (canonical sync performed at archive time)
**Verify verdict**: **PASS** — `blockers: 0`, `critical_findings: 0`, `requirements: 3/3`, `scenarios: 12/12`, `test_exit_code: 0`; validated by `gentle-ai sdd-verify-validate` → `{"valid": true, "verdict": "pass"}` (exit 0); `evidence_revision: sha256:0dd0a828a85fb4842700feeb5ca417519c731bde61f59c20fbe2fccba23c0185`
**Branch**: `fix/181-prepare-csv-config-tier`
**Commits**: `fc8818a` `fix(prepare): read the dataset's declared CSV dialect, and retire the dead cluster` (7 files) · `bbb851e` `docs(sdd): add the prepare-csv-config-tier change artifacts` (HEAD)
**Archived path**: `openspec/changes/archive/2026-09-14-fix-prepare-csv-config-tier/`

## Summary

`prepare` now resolves the CSV dialect from the dataset's declared `[meta] csv_delimiter`/`csv_encoding`
(declared wins), keeps the tool-wide sniff as the fallback when nothing is declared, actually honours a
declared encoding, emits a non-blocking warning when the declaration disagrees with the file, and carries
one reader home in `_converters.py` after the 249-line dead duplicate cluster in `prepare.py` was removed.

## Artifacts read

`proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`,
`specs/parquet-conversion/spec.md`, `specs/tool-config/spec.md`, `openspec/config.yaml`; canonical targets
`openspec/specs/parquet-conversion/spec.md` and `openspec/specs/tool-config/spec.md`. No `sync-report.md`
exists for this change.

## Archive preconditions / final task gate

- The verify report is present and clearly passing (no `FAIL`, `CRITICAL`, `BLOCKED` or verification blocker).
- The persisted `tasks.md` was re-read immediately before the sync: **14 `- [x]`, zero `- [ ]`** → no
  stale-checkbox reconciliation was needed and none was performed.
- `sync-report.md` is absent → the archive-time sync fallback ran under the parent prompt's **explicit
  approval**.
- Destructive merge guard: no `REMOVED` requirements; the two `MODIFIED` replacements (PC-U01, TC-04) were
  explicitly instructed by the parent prompt. Nothing else was replaced or deleted.

## Canonical sync

| Domain spec | Delta | Operation | `git diff --numstat` |
| --- | --- | --- | --- |
| `openspec/specs/parquet-conversion/spec.md` | PC-U01 | MODIFIED → replaced in place | 48 insertions / 5 deletions |
| `openspec/specs/parquet-conversion/spec.md` | PC-U06 | ADDED → appended directly after PC-U05 (the last `PC-*` requirement), before the unnumbered pipeline requirement | (included in the row above) |
| `openspec/specs/tool-config/spec.md` | TC-04 | MODIFIED → replaced in place | 8 insertions / 1 deletion |

`git diff --stat` for the two files: **56 insertions, 6 deletions** — both insertions and deletions are
visible, i.e. genuine replacements, not additive appends (unlike an earlier purely additive sync in this
repo).

- **PC-U01** — the `.csv` reader row was replaced with the declared-then-sniff form; the resolution-order
  paragraph was added; scenario `CSV sniff` became `CSV sniff when nothing is declared`; scenarios
  `Declared delimiter outside the sniff set wins (mis-split catcher)`, `Declared encoding is honoured`,
  `Declaration disagrees with the file — warn, keep declared` and `No declared dialect is byte-identical to
  today` were added; the `(Previously: ...)` provenance was retained. The `.tsv/.xlsx/.jsonl/.parquet` rows
  and the writer/parity sentence are unchanged.
- **PC-U06** — appended with the marker
  ``> Added by change `2026-09-14-fix-prepare-csv-config-tier` (GitHub #181).``, matching the neighbouring
  canonical provenance style.
- **TC-04** — the note now reads that `prepare` uses the DATASET-level
  `[meta] csv_delimiter`/`csv_encoding` when the dataset declares them, and falls back to the tool-wide
  `csv_delimiter` key and `config.CSV_ENCODING` only when it declares neither, with the resolution order
  normative in `parquet-conversion` **PC-U01** — replacing the flat "not this tool-wide key" claim; the
  `(Previously: ...)` line records the superseded wording.
- House-style ``> Modified by `2026-09-14-fix-prepare-csv-config-tier` (archived 2026-09-14; GitHub #181) — …``
  provenance lines were added under the two modified requirement headings.
- Post-sync checks: exactly one `PC-U01)`, one `PC-U06)` and one `TC-04)` heading each; every other
  requirement keeps byte-for-byte text (no other hunks exist in the diff); the only surviving occurrences of
  the retired wording are inside the deliberate `(Previously: ...)` lines.
- Active same-domain change warnings: **none** — no other change folder existed under `openspec/changes/`
  when the sync ran (`sameDomainActiveChanges: []`).

## Decision recorded

**Declared-wins** — the dataset's declared `[meta] csv_delimiter`/`csv_encoding` governs conversion; where
the dataset declares neither, sniff + tool-wide `config.CSV_ENCODING` remains the fallback. Justification
(aligning an outlier, not inventing policy): five of the eight dialect readers already resolved from the
dataset tier — `checks.py:174-175`, `quality.py:232-233`, `codebook.py:505-506`, `mcp_server.py:1543-1544`,
`repo_compliance.py:522-523` — plus `prepare.py:805-806` already forwarded both keys to the schema report;
`_converters.py` was the outlier being aligned.

**Presence signal** — `declared_meta_keys: frozenset[str]`, because `from_toml` maps "declared nothing" and
"declared `;`" onto the same value; presence is read independently of the value.

**Medium scope note (documented cost, not a regression)** — a *programmatic*
`DatasetConfig(csv_delimiter=…)` without `declared_meta_keys` still sniffs, so a library consumer can reach
that fallback path (verify probe D-2: `csv_delimiter="|"` with an empty declared-key set produced a
one-column Parquet while `prepare()` returned 0). No production code constructs `DatasetConfig`
programmatically (`grep -rn "DatasetConfig(" src/sofer/` → none), so the CLI path is unaffected and the
fallback direction equals pre-change behaviour. Recorded as a bounded follow-up, not a defect.

## Dead cluster removal and rollback

- `git diff --numstat src/sofer/prepare.py` → 9 insertions / 256 deletions; the removed cluster is **249
  lines** (`_sniff_csv_delimiter`, `_count_delimiters_outside_quotes`, `_cast_null_columns_to_string`,
  `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet`) plus the two now-unused imports
  and separators. `_convert_to_parquet` had zero production callers.
- Rollback: `git revert` per work unit — WU1 (`model.py` presence signal, no behaviour change), WU2
  (`_converters.py` fix), WU3 (`prepare.py` subtraction + call sites). Reverting WU3 restores dead code only
  (no behaviour change); reverting WU2 returns conversion to tool-wide sniffing; reverting WU1 drops the
  unused field. No migration or data cleanup.

## Measured final state

- `uv run pytest tests/ -q` → **1771 passed, 6 skipped** (`test_exit_code: 0`); pre-change baseline
  re-derived on the branch: **1766 passed, 6 skipped** (net +5 = 26 added / 21 removed test functions).
- Coverage TOTAL **93%** (`5924 stmts / 349 miss / 2286 branch / 156 partial`) against the config-owned
  floor `fail_under = 90` (`pyproject.toml:98`; `branch = true` at `:93`).
- `bash scripts/check_core_coverage.sh` → exit 0: `cli.py` 574/0 100%, `scanner.py` 159/0 100%,
  `prepare.py` **325**/0 100%, `publish.py` 326/0 100%, empty `Missing` column.
- `prepare.py` statements **432 → 325** after the dead-cluster removal, 100.00% preserved with zero
  `# pragma: no cover` (AGENTS.md rule 14).
- `_converters.py` 295 stmts / 87 miss / 68% → 323 / 71 / 77% (no per-file floor; no net-negative).
- `uv run mypy src/`, `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/` all clean
  (exit 0).

## Delivery / workload

- Diff: 7 files, **568 insertions / 638 deletions = 1206 changed lines**, inside the maintainer's explicit
  **1500-line `exception-ok`** authorization (recorded in `tasks.md`, `design.md`, `proposal.md` — not
  inferred).
- Scope at change time: zero paths under `cli.py`, `codebook.py`, `repo_compliance.py`, `mcp_server.py` or
  `openspec/specs/**`; the only canonical edits are this archive-time sync.

## Record correction carried by this report

`apply-progress.md` originally claimed `TestDelimiterPlumbing` was "retargeted to the declared TOML seam
(`_declared_cfg`) + true column count". Verify disproved it: the test is byte-identical to `HEAD`, still
constructs a programmatic `DatasetConfig(csv_delimiter="|")` with no `declared_meta_keys`, and asserts only
existence/absence, so it passes vacuously on a one-column Parquet. The parent corrected the artifact (the
false claim is marked removed in `apply-progress.md`); the test-quality findings are tracked in issue
**#205**. The discriminating evidence is E1 (the `|` mis-split catcher, which fails pre-change), E4
(declared `cp1252`) and E3/E5, not that test.

## Pre-existing findings left untouched (not regressions)

- **W2** — the JSONL fallback arm has no persistent test (coverage lines 679, 681–707 Missing); verify
  proved it only by a forced-failure probe, and the inline "from_pylist handles sparse keys (union)" comment
  is inaccurate on pyarrow 25.0.0. `_convert_jsonl_to_parquet` is outside the touched functions.
- **W3** — `TestCsvDialectResolution::test_declared_{semicolon,comma}_wins` inputs do not discriminate the
  declared-wins branch; the "E2 declared wins" label is stronger than those two tests warrant. No functional
  gap.
- **W4** — E5 pins a literal pre-change Parquet digest while `pyproject.toml` permits any `pyarrow>=14.0`;
  producer-version brittleness, currently correct (independently reproduced twice).
- **INFO** — the `⚠` raise-path `UnicodeEncodeError` on a cp1252 stdout, present at `HEAD`.
- The `tomli`/`tomllib` guarded import in `src/sofer/model.py` (required by AGENTS.md rule 12) and the
  deliberate invalid constructions in `tests/test_model.py::TestValidate` — pre-existing, outside the diff;
  the authoritative `uv run mypy src/` gate is clean.
- The apply-recorded baseline failure (`tests/test_coverage_contract.py`, TOTAL 89.5% from a stale partial
  `.coverage`) did **not** reproduce at verify time; the stale-DB condition no longer exists.

## Style deviations

No **in-process carrier** style deviation applies to this change: no artifact records one and the change
introduces none. The three recorded deviations are D1 (the anti-collapse guard keys on the *resolved*
delimiter, so its branch is exercised with a hand-built one-column table while the `|` mis-split is caught
end-to-end by E1), D2 (the `_try_sniff_csv_delimiter` `None` arm also covers an empty file; observable
behaviour unchanged and the disagreement warning is suppressed for that degenerate file), D3
(`_count_delimiter_outside_quotes` extracted so the guard reuses one quoting implementation).

## Blockers

None.
