```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:0dd0a828a85fb4842700feeb5ca417519c731bde61f59c20fbe2fccba23c0185
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 12/12
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:ada59bcadda3d372738f5ae02b157091889783dbed932a874ffd9dd7679412a4
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
```

# Verify Report — fix-prepare-csv-config-tier (issue #181)

Branch `fix/181-prepare-csv-config-tier` @ `568cc67` + uncommitted working tree. Store: `openspec` (this
file) mirrored to Engram `sdd/2026-09-14-fix-prepare-csv-config-tier/verify-report`.

**Verdict: PASS.** All 14 implementation tasks complete, 3/3 requirements and 12/12 scenarios verified,
every gate green. Four WARNING/INFO findings are recorded below; none blocks archive, and one (W1) should
be handled by the parent before the PR because it lies inside the changed test file.

**Hash provenance (one sentence each):** `evidence_revision` is the sha256 of the raw `git diff` text of the
verified candidate (568 insertions / 638 deletions, 7 files, captured to `/tmp/v181_diff.txt`);
`test_output_hash` is the sha256 of the captured stdout+stderr of `uv run pytest tests/ -q`
(`/tmp/v181_full.txt`); `build_output_hash` is the sha256 of the captured stdout+stderr of
`uv run ruff check src/ tests/ && uv run mypy src/` (`/tmp/v181_build.txt`).

## Structured status and actionContext

- `artifactStore: openspec`, `nextRecommended: verify` → authoritative; all of `spec`/`tasks`/`apply-progress`
  present and non-empty.
- `taskProgress`: 14/14, `allComplete: true`. `dependencies.verify: ready`; `blockedReasons: []`.
- `actionContext.mode: repo-local`, `workspaceRoot` / `allowedEditRoots` = `C:\Users\elaze\Desktop\sofer`;
  every changed path lies inside that root. No `workspace-planning` mode, so no `allowedEditRoots` blocker.
- No active `size:exception` conflict: see Review Workload below.
- Attempt: continued the existing active verify attempt
  `sha256:ea19373b6455acbfb1c95782ffe62f93f8bb172b59793f6b39489a80d021b0b0` (work unit
  `prepare-csv-dialect-verification`, `state: proceed`).

## Requirements and scenario coverage (3 requirements / 12 scenarios)

Counts re-derived from the deltas, not copied: `specs/parquet-conversion/spec.md` = **PC-U01** MODIFIED
(8 scenarios) + **PC-U06** ADDED (2 scenarios) = 2 requirements / 10 scenarios; `specs/tool-config/spec.md` =
**TC-04** MODIFIED (2 scenarios) = 1 requirement / 2 scenarios. Total **3 / 12** — agrees with the parent.

| # | Requirement | Scenario | Evidence | Verdict |
|---|-------------|----------|----------|---------|
| 1 | PC-U01 | CSV sniff when nothing is declared | `test_converters.py::TestCsvDialectResolution::test_nothing_declared_falls_back_to_sniff`; verify probe P1 (sniff → `;`) | verified |
| 2 | PC-U01 | Declared delimiter outside the sniff set wins (mis-split catcher) | **E1** `TestDeclaredDialectWins::test_declared_delimiter_outside_sniff_set_uncollapsed` (end-to-end `prepare()`, 3 columns); verify probes P2/P3 | verified (clause-2 caveat, see D-1) |
| 3 | PC-U01 | Declared encoding is honoured | **E4** `TestDeclaredEncodingHonoured::test_declared_encoding_decodes_and_does_not_stage_csv`; `TestCsvDialectResolution::test_declared_encoding_reaches_python_parity_read`; `test_read_csv_raw_values_honours_encoding` | verified |
| 4 | PC-U01 | Declaration disagrees — warn, keep declared | **E3** `TestDeclaredDisagreementWarning`; verify probe P5 through `prepare()` (`rc == 0`) | verified |
| 5 | PC-U01 | No declared dialect is byte-identical to today | **E5** `TestUndeclaredDialectByteIdentical`; independently reproduced twice by probe P1 (see W4) | verified |
| 6 | PC-U01 | TSV hardcoded tab | `test_converters.py::TestConvertFileToParquet::test_tsv` (preserved) | verified |
| 7 | PC-U01 | JSONL fallback | **No repo test executes the fallback arm** (coverage Missing 679, 681-707). Verified by verify probe P6c (forced fast-path failure → `c.parquet` written). See W2. | verified by probe only (weaker) |
| 8 | PC-U01 | Parquet passthrough and recursive skip | `TestConvertFileToParquet::test_parquet_passthrough`; `test_mirror.py::test_recursive_entry_ignored` | verified |
| 9 | PC-U06 | The duplicated cluster is gone and unreferenced | `test_prepare.py::TestNoDuplicateConversionCluster` (2 tests) + repo-wide grep (below) | verified (structural, flagged weaker in the delta itself) |
| 10 | PC-U06 | Single home is exercised | `TestDeclaredDialectWins::test_undeclared_dialect_prepare_delegated_to_single_home` — spy asserting `prepare()` calls `sofer._converters.convert_file_to_parquet` with the `cfg` object | verified (behavioural) |
| 11 | TC-04 | Override honored within the same invocation | `tests/test_config.py:415::test_csv_delimiter_override_effective_same_invocation` (pre-existing, unchanged file) | verified |
| 12 | TC-04 | Single-file commands without a dataset TOML | `tests/test_config.py:400::test_single_file_codebook_without_config_anchors_cwd` (pre-existing, unchanged file) | verified |

Scenario 2's second THEN clause ("the parity check SHALL be structurally unable to agree with a wrong
delimiter") is delivered by the architecture (one resolved pair feeding both the Parquet read and the parity
read) plus the anti-collapse guard, not by a general wrong-delimiter detector — probe P2 shows parity still
agrees on the `;`-on-`|`-file shape. Adjudicated in D-1; recorded here rather than silently counted.

## Task completion

`tasks.md` has **zero unchecked implementation markers** — the exact-`- [ ]` scan returns nothing; all 14
apply-phase tasks are `- [x]` (`sdd-owner: implementation`). The remaining `tasks.md` bullets are
deliberately unchecked parent-owned lifecycle items (budget bound, archive-time canonical sync,
commit/push/PR) and are not apply's to complete, so they are not completeness defects.

## Verification commands (each in its own shell call; exit codes captured from the command itself)

| Gate | Command | Exit | Observed |
|------|---------|------|----------|
| G1 full suite | `uv run pytest tests/ -q` | 0 | `1771 passed, 6 skipped, 1 warning in 54.34s` |
| G2 coverage run | `uv run coverage run -m pytest -q` | 0 | `1771 passed, 6 skipped, 1 warning in 65.98s` |
| G3 coverage floor | `uv run coverage report -m` | 0 | TOTAL line below |
| G4 core coverage | `bash scripts/check_core_coverage.sh` | 0 | `cli.py 574/0 100%`, `scanner.py 159/0 100%`, `prepare.py 325/0 100%`, `publish.py 326/0 100%`, empty `Missing` |
| G5 build (config-declared) | `uv run ruff check src/ tests/ && uv run mypy src/` | 0 | `All checks passed!` / `Success: no issues found in 32 source files` |
| G6 format | `uv run ruff format --check src/ tests/` | 0 | `67 files already formatted` |
| G7 scope | `git diff --name-only` | 0 | 7 files, zero forbidden paths |
| G8 dead code | `grep -rn --include='*.py' … src/ tests/` | 0 (matches only in `_converters.py` / tests importing `sofer._converters`) | see below |

G3 TOTAL line verbatim:

```text
TOTAL                             5924    349   2286    156    93%
```

93% ≥ the config-owned floor `fail_under = 90` (`pyproject.toml:98`, `branch = true` at `:93`).
`prepare.py` = `325 0 180 0 100%` (down from 432 statements, matching the parent's measurement);
`_converters.py` = `323 71 126 13 77%`, **up** from the apply-recorded baseline `295 87 116 23 68%`
(no net-negative; `_converters.py` has no per-file floor — COV-01 covers `profile.py` /
`mcp_registration.py` / `verification.py`).

Test-tally accounting (net +5, fully explained): `git diff -U0` shows **26 added** and **21 removed** test
functions → 1766 + 5 = **1771 passed**; skips unchanged at 6. No test was deselected or newly skipped.

## Evidence set E1–E5

- **E1** (catcher, does not exist at HEAD) — `TestDeclaredDialectWins::test_declared_delimiter_outside_sniff_set_uncollapsed`
  runs `prepare()` on a `|` file with `[meta] csv_delimiter = "|"` and asserts 3 columns and the uncollapsed
  header. Verified discriminating against pre-change behaviour by probe P2: `_sniff_csv_delimiter` (tool-wide)
  returns `;` for a `|` file, `pc.read_csv` with `;` yields **1** column `['col1|col2|col3']`, and
  `_check_conversion_parity(pipe, ';', collapsed)` returns `ok=True` — i.e. the old parity agreed vacuously,
  so the catcher's `num_columns == 3` assertion genuinely fails pre-fix. The replacement claim that no such
  end-to-end test existed is confirmed: at HEAD the only delimiter tests were `TestConvertDelimiterHonoured`
  (which exercised the **dead** `prepare._convert_to_parquet(delimiter=…)`) and `TestDelimiterPlumbing`
  (existence-only) — see W1.
- **E2** (declared wins) — `TestCsvDialectResolution` + probe P3 (declared `|` ⇒ 3 columns). The `;`/`,`
  members of this pair are non-discriminating; see W3.
- **E3** (disagreement warning) — `TestDeclaredDisagreementWarning` plus probe P5 through `prepare()`:
  stdout carried `[!] data.csv: declared csv_delimiter ';' differs from sniffed ',' — using declared ';'`,
  the conversion succeeded, and `prepare()` returned **0** (unchanged exit code; stdout, not stderr).
- **E4** (declared encoding honoured) — `cp1252` file decodes to `José` and `data.csv` is not staged;
  unit-level parity/raw-read tests cover the encoding threading into the Python parity read.
- **E5** (undeclared ⇒ byte-identical) — `TestUndeclaredDialectByteIdentical` compares against the literal
  `5eb870dc0bc2832dadbd5a4d6b570dde6c53a2beec412081f229715fe92e648c`. **Tested, not accepted**: probe P1
  reproduced that digest independently (a) through the post-change code with an undeclared config and (b)
  through the pre-change read shape copied from `git show HEAD:src/sofer/_converters.py` (sniff → `pc.read_csv(local,
  parse_options=…)` with no `read_options`). Both equal the literal, so byte-identity holds by construction.

## Migration / cleanup findings

- **Dead cluster**: `git diff --numstat src/sofer/prepare.py` → `9 insertions / 256 deletions`; the deleted
  `def` lines are exactly `_sniff_csv_delimiter`, `_count_delimiters_outside_quotes`,
  `_cast_null_columns_to_string`, `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet`
  (249-line cluster + the two now-unused imports `csv as csv_module` / `pyarrow.csv as pc` + separators;
  `ruff check` confirms nothing dangles).
- **Grep proof** (`grep -rn --include='*.py' -E '_convert_to_parquet|_sniff_csv_delimiter|_try_sniff_csv_delimiter|_read_csv_raw_values|_check_conversion_parity' src/ tests/`):
  `src/sofer/prepare.py` matches **nothing**; definitions survive once each in `src/sofer/_converters.py`
  (lines 111, 190, 223, 304, 331) and every test reference imports from `sofer._converters`.
  `_convert_to_parquet` no longer exists anywhere. (A `-r` scan without `--include` also hits stale
  `__pycache__/*.pyc` bytecode, which is build residue, not source.)
- **Mechanical scope**: `git diff --name-only` = `src/sofer/_converters.py`, `src/sofer/model.py`,
  `src/sofer/prepare.py`, `tests/test_converters.py`, `tests/test_model.py`,
  `tests/test_parquet_conversion.py`, `tests/test_prepare.py`. Scan for
  `cli.py|codebook.py|repo_compliance.py|mcp_server.py|openspec/specs/` → **zero** matches.
  `tests/test_model.py` is outside the prompt's 7-file allow-list but is explicitly required by task 1.3.
- **Single resolution point** (D3) verified in the diff: `prepare.py:510` calls
  `convert_file_to_parquet(local, entry_tmp, cfg)`; `_resolve_csv_dialect` is the only delimiter/encoding
  decision; `pc.ReadOptions(encoding=…)` is passed **only** when `csv_encoding` is declared.

## Strict TDD

**Not active.** `openspec/config.yaml` declares `strict_tdd: false` (top-level and `testing.strict_tdd`), and
`rules.apply.tdd: false`; `apply-progress.md` contains no `TDD Cycle Evidence` table, which is therefore not
required. No CRITICAL is raised on this axis. Assertion quality was audited anyway (see W3) because the
change rewrites most of a test module.

## Review workload / PR boundary

- `tasks.md` forecast: single PR, no chained PR, `Delivery strategy: exception-ok`, `Chain strategy:
  size-exception`, with the maintainer's explicit authorization of up to **1500** changed lines. The
  authorization is recorded in `tasks.md`, `design.md` and `proposal.md` — not inferred.
- Actual: `git diff --numstat` → **568 insertions + 638 deletions = 1206 changed lines**, inside 1500. The
  deletion (`prepare.py`) rode with the fix exactly as authorized; no `size:exception` beyond the recorded
  bound was needed.
- Scope: the diff touches only the five files sanctioned by design D6 plus `tests/test_model.py` (task 1.3)
  and `tests/test_converters.py` — no scope creep, no forbidden path, no canonical spec edited.
- No commit/push/PR was performed by verify (correctly deferred to the parent).

## Deviation adjudication (as disclosed by apply)

- **D-1 — guard keys on the resolved delimiter; its branch is exercised with a hand-built one-column table,
  while the `|` mis-split is caught end-to-end. Sound?** **Sound, with one wording caveat.** Probe P3 shows
  `_raw_first_line_has_delimiter(pipe_file, ';')` is `False`, so the guard can never fire for the `|`-read-as-`;`
  shape; that is precisely what keeps PC-U01's "still use the declared one, do not fail" scenario silent (a
  guard keyed on "any `SNIFF_DELIMITERS` character present" would fire and break it). The guard's stated
  precondition (single column *and* the resolved delimiter present outside quotes) is also false-positive
  free: if the header carries the resolved delimiter unquoted, a correct parse cannot yield one column. The
  consequence is that the spec's clause 2 is a *narrower* property than its wording suggests — it is true of
  the post-change pipeline because one resolution feeds both reads, not because the guard is a general
  detector (probe P2: parity still agrees for `;`-on-`|`). Adjudication: acceptable; recorded rather than
  counted as a scenario failure.
- **D-2 — a programmatic `DatasetConfig(csv_delimiter=…)` without `declared_meta_keys` still sniffs:
  documented bounded cost of D1, or a silent hole?** **A real hole, documented and bounded — but worth a
  follow-up.** Probe P4 reproduces it: a programmatic config with `csv_delimiter="|"` (empty
  `declared_meta_keys`) produced a **one-column** Parquet named `'col1|col2'` while `prepare()` returned 0.
  Bounds: `grep -rn "DatasetConfig(" src/sofer/` shows **no** production programmatic construction (configs
  come from `from_toml`, which populates the set), so only library callers reach it; the fallback direction
  equals pre-change behaviour (no regression); the model docstring and design D1 both state the cost. It is
  more than a test-shadow, though: the five value-based sibling readers (`checks.py:175`, `quality.py:232`,
  `codebook.py:505`, `mcp_server.py:1543`, `repo_compliance.py:522`) still honour a programmatic
  declaration, so such a config is honoured by them and ignored by conversion — a pre-existing divergence
  that this change closes for TOML datasets only. Not a blocker; recommend a follow-up (populate presence
  for explicitly-set fields, or fall back to the value when `declared_meta_keys` is empty).
- **D-3 — `TestDelimiterPlumbing` retargeted to a declared TOML.** **Not true in the code: see W1.**
- **D-4 — E5 uses a literal pre-change sha256, stable only while pyarrow stays pinned.** Confirmed; see W4.

## Findings

**W1 (WARNING — inside the changed test file; should be handled before the PR, not an archive blocker).**
`tests/test_parquet_conversion.py::TestDelimiterPlumbing::test_custom_delimiter_used_via_upload` is
byte-identical to HEAD (compared via `git show HEAD:tests/test_parquet_conversion.py`), so deviation 3's
"retargeted to the declared TOML seam (`_declared_cfg`) + true column count" is contradicted by the code. It
still builds a programmatic `DatasetConfig(csv_delimiter="|")` and asserts only that `data.parquet` exists and
`data.csv` does not. Probe P4 shows that exact path now writes the collapsed one-column Parquet while
`prepare()` returns 0, so the test passes vacuously — the assertion shape the proposal itself called out as
inadequate. It provides no false evidence for E1 (E1 is separate and strong), and it is not a functional
regression (conversion ignored `cfg.csv_delimiter` at HEAD too). Recommended action for the parent: retarget
the test to `_declared_cfg` + `num_columns == 2`, or correct the apply-progress record; do not read the
current pass as evidence of delimiter plumbing.

**W2 (WARNING — pre-existing evidence gap, untouched by this diff).** The delta's Evidence table backs the
"JSONL fallback" scenario with an existing preserved test, but no test in the repository (HEAD or working
tree) executes the `json + pa.Table.from_pylist` arm: `coverage report` marks lines `679, 681-707` Missing
(`682` is `# Fallback: json + from_pylist`, `695` is `from_pylist`) and `git grep from_pylist HEAD -- tests/`
is empty. Verify probe P6c forced the fast path to raise and the fallback did write `c.parquet`, so the
scenario's THEN clause holds — but only by verify-phase execution, not by a permanent test. Two secondary
observations from the same probe: the inline comment "from_pylist handles sparse keys (union)" is inaccurate
on pyarrow 25.0.0 (P6c: only the first row's keys survive and the sparse column `c` is dropped, with just the
soft `[!] JSONL key mismatch` warning), and the natural GIVEN ("sparse keys where `pyarrow.json` raises") is
not reproducible on this pyarrow, since sparse keys take the fast path (P6b). `_convert_jsonl_to_parquet` is
outside this diff's touched functions (design D6); flag only, do not fix here.

**W3 (WARNING — assertion strength).** `TestCsvDialectResolution::test_declared_semicolon_wins` and
`test_declared_comma_wins` use `a;b` and `a,b` inputs, for which `_sniff_csv_delimiter` already yields the
declared delimiter, so both pass unchanged if the declared value is ignored — they do not discriminate the
declared-wins branch. The discriminating evidence for declared-wins is E1 (`|` ∉ `SNIFF_DELIMITERS`), E4
(`cp1252`), the disagreement-warning test, and probes P2/P3/P5. No functional gap; the "E2 declared wins"
label is stronger than these two tests warrant.

**W4 (WARNING — test brittleness).** E5 pins a literal pre-change Parquet digest while `pyproject.toml:25`
declares `pyarrow>=14.0` (installed 25.0.0). Parquet bytes are producer-version sensitive, so a permitted
pyarrow upgrade can fail E5 without any behaviour change. The digit is currently correct — independently
reproduced twice by probe P1 — so this is maintainability, not correctness. Suggested follow-up: derive the
fixture bytes at test time from the pre-change read shape, or pin pyarrow exactly.

**INFO — pre-existing, outside the diff.** The `⚠` (U+26A0) prints on the conversion-failure path raise
`UnicodeEncodeError` when stdout is cp1252 (hit by probe P6a outside pytest). Present at HEAD
(`git show HEAD:src/sofer/_converters.py`, failure print in `_convert_csv_to_parquet`), unrelated to this
change, out of scope; noted because the project tracks Windows safety (AGENTS.md rule 10).

## Pre-existing static warnings — explicitly not regressions

The `tomli`/`tomllib` guarded import in `src/sofer/model.py` (HEAD line 397, required by AGENTS.md rule 12,
absent from this diff) and the deliberately invalid constructions in `tests/test_model.py::TestValidate`
(absent from this diff, and `mypy` is not run on `tests/`) are **pre-existing and outside the diff**. The
authoritative gate `uv run mypy src/` is clean (exit 0, 32 files, run under the pinned 3.13 from
`.python-version`). They are neither regressions nor findings, and were not fixed.

The apply-recorded baseline failure (`tests/test_coverage_contract.py`, TOTAL measured 89.5% from a stale
partial `.coverage`): **not reproduced.** With the `.coverage` data file present and freshly regenerated,
both `uv run pytest tests/ -q` (exit 0, first try) and `uv run coverage run -m pytest -q` (exit 0) passed
clean, and the contract test is among the 1771 passes. Consistent with apply's environmental diagnosis; the
stale-DB condition no longer exists.

## Blockers

None. Archive prerequisites are satisfied except the parent-owned lifecycle steps (canonical sync of PC-U01
and TC-04 as genuine replacements, PC-U06 appended, then commit/push/PR). W1 should be resolved in the same
PR because it sits in a changed test file; W2/W3/W4 are follow-ups.
