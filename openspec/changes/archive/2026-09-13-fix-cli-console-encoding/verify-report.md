```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:1399e1cd7bb6e4b58ce1966eca42be8da9b5cf6026b09af6762d0ee6781a28db
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 7/7
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:be8b556f4905054ec808cf92f7fa0242382d0161bdff42edf8feb1bdb074de0e
build_command: UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 ruff check src/ tests/ && UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
```

# Verify report: fix-cli-console-encoding (GitHub #161)

> **Change:** `2026-09-13-fix-cli-console-encoding` · **Store:** openspec · **Phase:** `sdd-verify` ·
> **Language:** English · **Host:** Windows 10 x64. **Two interpreters were used, deliberately:**
> the **ambient venv** (Python **3.10.20**, `.python-version` = `3.10`) for the test evidence, and the
> **CI-mirroring interpreter** (Python **3.13.12**, `UV_PROJECT_ENVIRONMENT=/tmp/venv313`, **no `tomli`**)
> for the build evidence — because `.github/workflows/ci.yml` pins the lint job (`:15`) and the coverage
> job (`:61`) to `3.13` while the test matrix (`:28`) spans `3.10`–`3.14`.
> **Tree verified:** working tree on `fix/161-cli-console-encoding` (HEAD = **`1803acf`**
> `fix: revert Python version to 3.10`), uncommitted diff = the change under review.
> **`evidence_revision` used:** `sha256:1399e1cd7bb6e4b58ce1966eca42be8da9b5cf6026b09af6762d0ee6781a28db`
> — read as `projection.current_snapshot_identity` from
> `gentle-ai review status --cwd /c/Users/elaze/Desktop/sofer --contract gentle-ai.review-integration/v2
> --agent pi --next-transition` (it equals `target_identity` too). It is stated here so the
> `evidence_revision` field is traceable to a real read, not assumed.
>
> **Rerun provenance (third pass over this change; a correction of the envelope, not of the audit).**
> - **Pass 1** verified the substance: verdict `passed`, 7/7 frozen scenarios mapped to passing tests,
>   RED reproduced against HEAD, 300 implementation lines, no scope drift. **Its audit stands and is not
>   re-litigated here.**
> - **Pass 2** re-emitted the report in the file shape the native gate accepts (a
>   `gentle-ai.verify-result/v1` envelope as the first non-empty line). It was **admitted** (`rc=0`) but
>   had to carry `verdict: fail`, because the mandated `build_command` and the COV-06 gate were red in the
>   **local 3.10 interpreter** and the validator refuses a passing verdict alongside failing evidence
>   (empirically probed in §11.3).
> - **This pass changes exactly one thing: where the build/gate evidence is captured.** The same
>   commands were re-run in the **CI interpreter (3.13)**, where the `tomli` fallback that makes the 3.10
>   environment red does not exist. Both are **green**, so the envelope now carries its honest value —
>   **`verdict: pass_with_warnings`**, `blockers: 0`, `critical_findings: 0`. **No finding was weakened or
>   removed in the process**; `V-04` moved from *“environmental, unexplained”* to **diagnosed** (§6).
> - **The environment diagnosis is the parent’s, not re-derived here.** It was established by direct
>   measurement and is re-confirmed by this pass (§2.2b/§2.2c/§2.3c): the `.python-version` = `3.10` pin vs
>   the 3.13 CI jobs, the absence of `tomli` under 3.13, and the packaging-test env-var trap. **Do not
>   re-open this as a defect of the change** — it is tracked as GitHub issue **#178**.
>
> **Inputs read by this phase:** `tasks.md`, `apply-progress.md`, `specs/process-boundary/spec.md`,
> `specs/cli/spec.md`, `design.md`, `proposal.md`, `sync-report.md`, `openspec/config.yaml`,
> `AGENTS.md` rules 6/7/12/13/14. Native SDD status was supplied in-prompt and is authoritative
> (`isNonAuthoritative: false`), so no status-contract file lookup was needed.
>
> **Envelope shape determined from the native validator, not assumed.** `blockers` and
> `critical_findings` are integer **counts** (the list forms `[]` / `[...]` are refused with
> `invalid blockers in verify result envelope`); `requirements` / `scenarios` are `completed/total`
> (`2/2`, `7/7` — the bare integers `2` / `7` are refused with `invalid requirements in verify result
> envelope`); the three hashes are `sha256:<64 lowercase hex>`; and a passing verdict is refused whenever
> any evidence is red. Here **both pieces of evidence are green** (`test_exit_code: 0`,
> `build_exit_code: 0`), so `pass_with_warnings` is admitted *and* honest: the change has no blocking
> defect, and the four residual findings below are informational.

---

## 1. Verdict

**`pass_with_warnings` — no blocking defect; `blockers: 0`, `critical_findings: 0`; no archive blocker on
the change’s own merits.** The change’s delta is verified: 7/7 frozen scenarios have a mapped passing
test, `V-01` is **closed**, the diff contains no defect, and both mandated evidence commands are green in
the interpreter CI actually uses.

`pass_with_warnings` (rather than `pass`) is the honest value because four **non-blocking** findings stay
open:

- **`V-02`** — assertion-quality note: `stdout.encode("cp1252")` is a round-trip tautology (no test is
  vacuous; the encodability assertions just contribute nothing).
- **`V-03`** — repo-wide `uv run ruff format --check src/ tests/` is red on **six untouched files**
  (pre-existing drift; needs its own housekeeping commit).
- **`I-01`** — test isolation: `HF_TOKEN` leaks out of `test_mcp_server.py` into
  `test_mcp_registration.py`; the full suite is green only by alphabetical accident.
- **`V-04`** — **diagnosed and tracked as #178**: the local `.python-version` = `3.10` pin makes the
  ambient `mypy` and COV-06 rows red while CI’s 3.13 jobs are green. Two clauses are also explicitly
  **not exercised** in this environment (§9).

| Area | Verdict |
|---|---|
| Task completion | **PASS** — 36/36 implementation rows `- [x]`; only the two `sdd-owner: parent` rows remain `- [ ]` |
| Frozen spec coverage (PB-02 ×4, CLI-R11 ×3) | **PASS** — 7/7 scenarios have a mapped passing test; `V-01` **closed** by `test_interpolated_stdout_value_strict_cp1252` |
| Implementation correctness | **PASS** — pre-fix crash reproduced against HEAD’s `src` (`8 failed`), post-fix GREEN (`20 passed`, focused selection) |
| Design coherence | **PASS** — guard shape, call-site placement, `CONSOLE_ERRORS` placement and all five ASCII edits implemented exactly as designed; all six `Interfaces/Contracts` guarantees independently re-derived |
| Tests | **PASS** — **ambient 3.10**: `1766 passed, 6 skipped` (1772 collected); **3.13 (packaging test deselected)**: `1765 passed, 6 skipped, 1 deselected`; measured pre-change baseline `1747 passed, 6 skipped` (1753 collected); delta exactly `+19` |
| Gate — coverage / rule 14 (COV-06) | **PASS in the CI interpreter** — `bash scripts/check_core_coverage.sh` → **`rc=0`**, all four gated files **100%** (`cli.py` 574 stmts / 166 branch, `BrPart 0`; `scanner.py` 159/76; `prepare.py` 432/226; `publish.py` 326/138), zero `# pragma: no cover`. Red in the ambient 3.10 venv for pre-existing environmental reasons (§2.3, `V-04`). |
| Gate — lint / types / whitespace | **PASS in the CI interpreter** — Python 3.13: `ruff check src/ tests/` → `All checks passed!`; `mypy src/` → `Success: no issues found in 32 source files` (`mypy src/ scripts/` → 33 files). Red in the ambient 3.10 venv for pre-existing environmental reasons (§2.2, `V-04`). `git diff --check` rc=0 |
| Review workload / PR boundary | **PASS** — 300 implementation+docs changed lines + 51 canonical-spec sync lines = 351 total, single PR, no chain, no `size:exception`, no scope drift |
| Strict TDD | **N/A** — `strict_tdd: false` in `openspec/config.yaml`, in `apply-progress.md`, and not activated by the parent prompt |

---

## 2. Exact commands and observed output

### 2.1 Full suite (rule 6 / AGENTS.md) — mandated `test_command`, ambient interpreter

The mandated `test_command` is the **ambient-venv** run, because that is the environment the repo’s own
`.python-version` selects for developers and the one the suite is normally driven in.

```text
$ uv run pytest tests/ -q > /tmp/sdd-verify-rerun2/test_output.txt 2>&1
# rc=0
...
1766 passed, 6 skipped, 14 warnings in 61.09s (0:01:01)

$ sha256sum /tmp/sdd-verify-rerun2/test_output.txt
be8b556f4905054ec808cf92f7fa0242382d0161bdff42edf8feb1bdb074de0e  /tmp/sdd-verify-rerun2/test_output.txt
# 5301 bytes captured; this is `test_output_hash` above, `test_exit_code: 0`.
```

Suite-shape counts (unchanged from pass 2, re-confirmed):

```text
$ uv run pytest tests/ --collect-only -q
1772 tests collected

$ uv run pytest tests/test_cli.py --collect-only -q
166 tests collected            # was 165 before the V-01 follow-up

$ uv run pytest tests/test_cli.py -q --collect-only -k cp1252
17/166 tests collected (149 deselected)
```

**`+19` delta is exact and measured, not inferred:** `166 − 147 = 19` new tests
(`12` parametrized help cases replacing `1` → `+11`, plus `T2–T5` `+4`, plus `T6–T8` `+3`, plus the
`V-01` closure test `+1`), and `1772 − 19 = 1753` collected pre-change = `1747 passed + 6 skipped`.

**Parity run under the CI interpreter (3.13), packaging test deselected** — this is evidence for
`V-04`, not a second mandated command:

```text
$ UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 pytest tests/ -q \
      --deselect "tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version"
# rc=0
1765 passed, 6 skipped, 1 deselected, 14 warnings in 54.56s

$ sha256sum /tmp/sdd-verify-rerun2/test313_output.txt
e8689a0e03fa5089ebd411f3a8005dc7bf75f13cdf7db8ff76f3bbdcfaea8988  /tmp/sdd-verify-rerun2/test313_output.txt
```

**Why exactly one test is deselected there, and why that is not a loophole.** `UV_PROJECT_ENVIRONMENT`
is inherited by the temporary venv that `test_console_script_help_and_version` builds for itself, which
mixes the 3.13 `pyarrow` into the 3.10 interpreter it spawns
(`ModuleNotFoundError: No module named 'pyarrow.lib'`). In the ambient venv it passes normally:

```text
$ env -u UV_PROJECT_ENVIRONMENT uv run pytest \
      "tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version" -q
1 passed in 6.05s
```

So the deselection is a **foreign-interpreter artifact of the env-var scope**, not a hidden failure: the
test is green in the environment it targets (3.10), and the *only* difference between the two suite runs
is that one test. That is why `test_output_hash`/`test_command` remain the ambient full-suite run.

### 2.2 Gates in the CI interpreter — mandated `build_command`

```text
$ UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 ruff check src/ tests/ \
    && UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/ \
    > /tmp/sdd-verify-rerun2/build_output.txt 2>&1
# rc=0
All checks passed!
Success: no issues found in 32 source files

$ sha256sum /tmp/sdd-verify-rerun2/build_output.txt
beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7  /tmp/sdd-verify-rerun2/build_output.txt
# 64 bytes captured; this is `build_output_hash` above, `build_exit_code: 0`.
```

This mirrors the CI lint job, which the workflow pins to the same interpreter:

```text
$ grep -n "python-version\|mypy" .github/workflows/ci.yml
15:          python-version: "3.13"          # lint job — the job that runs mypy
20:      - name: Type check with mypy
21:        run: uv run mypy src/ scripts/
28:        python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]   # test matrix
61:          python-version: "3.13"          # coverage job
```

CI’s mypy step also covers `scripts/`; the parent-mandated evidence command keeps the narrower `src/`,
so the wider form was run as an extra, informational check:

```text
$ UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/ scripts/
Success: no issues found in 33 source files        # rc=0  (informational; not hashed)
```

### 2.2b Why the ambient (3.10) venv is red — proven, not asserted

```text
$ uv run python --version && cat .python-version
Python 3.10.20
3.10

$ uv run mypy src/
src\sofer\mcp_registration.py:130: error: Name "_tomli" already defined (by an import)  [no-redef]
src\sofer\config.py:153: error: Name "_tomli" already defined (by an import)  [no-redef]
src\sofer\model.py:399: error: Name "_tomli" already defined (by an import)  [no-redef]
src\sofer\cli.py:440: error: Name "_tomli" already defined (by an import)  [no-redef]
src\sofer\mcp_server.py:689: error: Name "_tomli" already defined (by an import)  [no-redef]
Found 5 errors in 5 files (checked 32 source files)         # rc=1
```

### 2.2c Why 3.13 is green — the single root cause, measured

```text
$ UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 python -c "import sys; print(sys.version.split()[0]); import tomli"
3.13.12
ModuleNotFoundError: No module named 'tomli'          # ← the CI lint job's state, exactly

$ uv run python -c "import tomli, sys; print('tomli', tomli.__version__, 'py', sys.version.split()[0])"
tomli 2.4.1 py 3.10.20                                 # ← the ambient state, exactly
```

`tomli` is declared `tomli>=2.0; python_version < '3.11'`, so it exists only under the 3.10 pin. With
`tomli` installed, `import tomli as _tomli` **and** the `except ImportError: import tomllib as _tomli`
fallback both define `_tomli` → `[no-redef]`, and the fallback lines are unreachable → the coverage miss.
With `tomli` absent (3.13) the `except` arm runs and the name is defined once. **This is the same latent
issue `AGENTS.md` rule 12 documents** (“do not add mypy to the version matrix: under 3.10 the
`import tomli as tomllib` fallback triggers `no-redef` errors”), and it is filed as **#178**
(`dev-env: .python-version 3.10 makes local mypy and the COV-06 coverage gate unsatisfiable (CI runs 3.13)`,
OPEN).

**Not caused by this change:** none of the five lines is touched by the diff — the earliest `src/sofer/cli.py`
hunk is at `+550` while the failing line is `440`, i.e. the `_cmd_scan` TOML loader (see `D6`, §5).

```text
$ git diff --check
# rc=0 (only CRLF→LF notices; no whitespace errors, no conflict markers)

$ uv run ruff format --check src/sofer/cli.py src/sofer/config.py tests/test_cli.py
3 files already formatted                              # rc=0 — the files this change touches

$ uv run ruff format --check src/ tests/
6 files would be reformatted, 61 files already formatted   # rc=1 — pre-existing, see V-03/D4
  tests/test_ci_workflows.py   tests/test_coverage_contract.py   tests/test_mcp_registration.py
  tests/test_profile.py        tests/test_publish.py             tests/test_splits.py
```

### 2.3 Rule-14 coverage gate (COV-06) — measured in the CI interpreter

The data was regenerated under 3.13 (same deselected packaging test) and the repo’s own gate script was
then run unchanged:

```text
$ UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 coverage run -m pytest -q \
      --deselect "tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version"
1765 passed, 6 skipped, 1 deselected, 14 warnings in 68.19s        # rc=0

$ bash scripts/check_core_coverage.sh
Name               Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------
src\sofer\cli.py     574      0    166      0   100%
--------------------------------------------------------------
TOTAL                574      0    166      0   100%
Name                   Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------
src\sofer\scanner.py     159      0     76      0   100%
------------------------------------------------------------------
TOTAL                    159      0     76      0   100%
Name                   Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------
src\sofer\prepare.py     432      0    226      0   100%
------------------------------------------------------------------
TOTAL                    432      0    226      0   100%
Name                   Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------
src\sofer\publish.py     326      0    138      0   100%
------------------------------------------------------------------
TOTAL                    326      0    138      0   100%
# gate rc=0
```

All four gated rows are **100.00%** with `Miss 0`, `BrPart 0` — which also proves both arms of the
`isinstance` gate and both `continue` arms executed. Zero pragmas:

```text
$ grep -c "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py
src/sofer/cli.py:0
src/sofer/scanner.py:0
src/sofer/prepare.py:0
src/sofer/publish.py:0
# grep rc=1 — no match
```

**Ambient-interpreter reading for contrast (pre-existing and environmental, `V-04`).** Under 3.10 the
same gate reports `cli.py` at **99%**, `Missing 439-440` — the `except ImportError:` / `import tomllib as
_tomli` pair that a 3.10 interpreter with `tomli` installed cannot reach. The change adds **10**
statements and **0** misses (`574 − 564`, `2 − 2`); HEAD’s own untouched `cli.py` measures 99% with the
same two misses at `438-439` in the same environment. This is why the first pass (run under Python 3.11)
measured a clean 100% and pass 2 (run under 3.10) did not.

### 2.4 `Interfaces/Contracts` re-derived by execution (not read from prose)

```text
console_errors in _DEFAULTS: False        # reload() cannot rebind CONSOLE_ERRORS
CONSOLE_ERRORS value: replace
before (encoding, errors, line_buffering, write_through): ('ascii', 'strict', True, True)
after : ('ascii', 'replace', True, True)
encoding/line_buffering/write_through preserved: True
newline translation preserved (newline='\r\n' -> b'\r\n'): True
idempotent: True                          # second call is a no-op; identity preserved
```

`git diff` of the guard contains no `sys.stdout =` / `sys.stderr =` assignment (only the prose word
“replaced” inside the docstring), so stream identity is structurally preserved — matching the
`mcp_server._capture_output` requirement.

### 2.5 Dogfood of the issue’s own reproduction (same host)

```text
$ PYTHONIOENCODING=cp1252 uv run sofer scan --help        -> rc=0  stdout 2012 B  UnicodeEncodeError in stderr: 0
$ PYTHONIOENCODING=cp1252 uv run sofer prepare --help     -> rc=0  stdout 1495 B  UnicodeEncodeError in stderr: 0
$ PYTHONIOENCODING=cp1252 uv run sofer --help             -> rc=0  stdout 1716 B  UnicodeEncodeError in stderr: 0
$ PYTHONIOENCODING=cp1252 uv run sofer validate <cfg-error TOML>
                                                     -> rc=1  'Configuration errors' in stdout: 1
                                                              UnicodeEncodeError in stderr: 0
```

Pre-fix, against HEAD’s `cli.py` (scratch package on `PYTHONPATH`):

```text
$ PYTHONIOENCODING=cp1252 PYTHONPATH=<HEAD-src> uv run python -m sofer.cli scan --help     -> rc=1
  UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 830
$ PYTHONIOENCODING=cp1252 PYTHONPATH=<HEAD-src> uv run python -m sofer.cli prepare --help  -> rc=1
  UnicodeEncodeError (position 255)
```

### 2.6 Scope (no drift)

```text
$ git status --porcelain
 M README.md
 M README_ES.md
 M openspec/specs/cli/spec.md                  # ← sdd-sync output (sync-report.md present)
 M openspec/specs/process-boundary/spec.md     # ← sdd-sync output
 M src/sofer/cli.py
 M src/sofer/config.py
 M tests/test_cli.py
?? openspec/changes/2026-09-13-fix-cli-console-encoding/

$ git diff --numstat
1       0       README.md
1       0       README_ES.md
32      0       openspec/specs/cli/spec.md
16      3       openspec/specs/process-boundary/spec.md
44      5       src/sofer/cli.py
7       0       src/sofer/config.py
237     5       tests/test_cli.py
```

The **change’s own** implementation surface is still exactly five files and **300** changed lines
(`290 + / 10 −`): `README.md`, `README_ES.md`, `src/sofer/cli.py`, `src/sofer/config.py`,
`tests/test_cli.py`. The two `openspec/specs/**` files carry the **`sdd-sync` result** (51 lines,
`48 + / 3 −`), a separate phase’s output already recorded in `sync-report.md`; they are not
implementation lines. No other `src/` file, no `tests/conftest.py` (no second subprocess helper —
PB-09 holds), and the change directory is fully accounted for.

### 2.7 The five ASCII edits, proven by AST (not by grep)

Parsed both `git show HEAD:src/sofer/cli.py` and the working copy with `ast` and diffed the
multiset of string constants:

```text
removed vs HEAD:  "     → "  ×2
                  '...universal csv/tsv/xlsx/jsonl → normalized Parquet...'      (prepare description)
                  'Two-phase scan for the raw/ -> cache/ -> build/...'           (scan description)
added vs HEAD:    "     -> " ×2, the same two descriptions with "->"
                  the rewritten main() docstring (orchestration step 0 added)
                  the new helper's docstring
```

Those four string constants are exactly the five agreed sites (`:549`, `:569`, the two adjacent
literals at `:1072/:1073` that argparse concatenates into one constant, and `:1429`). Remaining
`U+2192` in `cli.py` — verified by AST node kind, not by grep — is **4 docstrings** (lines
113, 399, 607, 739) and **2 comments** (lines 454, 520); character count drops `27 → 22`. No emitted
string constant retains a glyph.

---

## 3. Frozen scenario verification (per requirement, per scenario)

### PB-02 — `CLI user-visible output via executable subprocess` (MODIFIED)

| # | Scenario | Test | Command | Observed |
|---|---|---|---|---|
| 1 | Help via subprocess | `test_help_exits_zero_and_lists_every_subcommand` | `uv run pytest "tests/test_cli.py::TestSubprocessBoundary::test_help_exits_zero_and_lists_every_subcommand"` | **PASSED** |
| 2 | cp1252 help on the ubuntu matrix (12 invocations) | `test_help_strict_cp1252[argv0..argv11]` | `uv run pytest tests/test_cli.py -q --collect-only -k cp1252` then `-k "cp1252 or ConsoleEncodingGuard"` | **12 × PASSED** (`17/166 collected`; `20 passed, 146 deselected` in the focused selection) |
| 3 | cp1252 runtime console output | `test_runtime_output_strict_cp1252` (validate half) + `test_scan_dry_run_strict_cp1252` (dry-run half) | same selection | **PASSED** (both) |
| 4 | Dispatch exit codes | `test_unknown_command_exits_2` | `uv run pytest "tests/test_cli.py::TestSubprocessBoundary::test_unknown_command_exits_2"` | **PASSED** |

Requirement prose re-checked point by point: every subcommand covered (`12` invocations = `--help`,
9 × `<cmd> --help`, `mcp add/remove --help`) ✓; **both** a help path and real runtime paths exercised
✓; `env={"PYTHONIOENCODING": "cp1252"}` with `encoding="cp1252"` ⇒ `run_cli` uses `errors="strict"` ✓;
no assertion names a glyph (`grep`-audited and read in full) ✓; no Windows-only test added, so the
“skip without privileges” clause is untouched ✓.

### CLI-R11 — `Console output survives an unencodable character` (ADDED)

| # | Scenario | Test | Observed |
|---|---|---|---|
| 1 | Runtime output with an unencodable character keeps the command’s result | `test_runtime_output_strict_cp1252` | **PASSED** — `rc==1`, `"Configuration errors" in stdout`, `stdout.encode("cp1252")`, no `UnicodeEncodeError` |
| 2 | ASCII literal with an unencodable interpolated value does not abort | `test_interpolated_unencodable_value_strict_cp1252` (**stderr** half, argv vector) **+** `test_interpolated_stdout_value_strict_cp1252` (**stdout** half, TOML-declared-path vector — the `V-01` closure) | **PASSED (both halves)** — previously `V-01`; now closed, see §4.2 |
| 3 | Console warning path carrying a glyph degrades instead of aborting | `test_codebook_warning_strict_cp1252` | **PASSED** — `rc==0`, `"Unsupported format" in stderr`, `stderr.encode("cp1252")`, no traceback |

Requirement-prose clauses re-checked: substitution is visible (`errors="replace"`, asserted as the
literal byte `b"?"` in T6) ✓; `errors="ignore"` is nowhere used (`git diff` contains no `ignore`
handler) ✓; a non-reconfigurable stream is left untouched (T7 `io.StringIO`, T8 closed
`TextIOWrapper`, both asserting identity) ✓; file-output encodings untouched (no writer file in the
diff) ✓; help output included (`--help` for every subcommand, plus nested `mcp`) ✓.

### Rule-6 traceability matrix (AGENTS.md 6)

| Frozen scenario | Test (final outcome, measured) |
|---|---|
| PB-02 Help via subprocess | `TestSubprocessBoundary::test_help_exits_zero_and_lists_every_subcommand` — PASSED |
| PB-02 cp1252 help (ubuntu matrix) | `TestSubprocessBoundary::test_help_strict_cp1252[argv0…argv11]` — 12 PASSED |
| PB-02 cp1252 runtime console output | `TestSubprocessBoundary::test_runtime_output_strict_cp1252` + `::test_scan_dry_run_strict_cp1252` — 2 PASSED |
| PB-02 Dispatch exit codes | `TestSubprocessBoundary::test_unknown_command_exits_2` — PASSED |
| CLI-R11 Runtime output keeps the result | `TestSubprocessBoundary::test_runtime_output_strict_cp1252` (shared) — PASSED |
| CLI-R11 ASCII literal + unencodable interpolated value | `TestSubprocessBoundary::test_interpolated_unencodable_value_strict_cp1252` (stderr/argv) + `::test_interpolated_stdout_value_strict_cp1252` (stdout/TOML, `V-01` closure) — 2 PASSED |
| CLI-R11 Console warning path degrades | `TestSubprocessBoundary::test_codebook_warning_strict_cp1252` — PASSED |
| CLI-R11 normative clause, rule-14 arms | `TestConsoleEncodingGuard::{test_console_streams_reconfigured_in_place, test_console_guard_skips_stream_without_reconfigure, test_console_guard_survives_unreconfigurable_text_wrapper}` — 3 PASSED |

**No scenario is unmapped. No scenario clause remains unasserted.**

---

## 4. RED / GREEN evidence

### 4.1 Focused selection, re-reproduced in this pass

Method: a scratch package under `/tmp/sddv3-head/sofer/` containing the working-tree `src/sofer/*.py` with
`cli.py` and `config.py` overwritten by `git show HEAD:…` (selected via `PYTHONPATH`, precedence over the
hatchling `.pth` entry — confirmed:
`PYTHONPATH=/tmp/sddv3-head uv run python -c "import sofer.cli as m; print(m.__file__, hasattr(m, '_configure_console_streams'))"`
→ `...\sddv3-head\sofer\cli.py False`).

```text
# RED — the new tests against HEAD's src
$ PYTHONPATH=/tmp/sddv3-head uv run pytest tests/test_cli.py -q \
      -k "cp1252 or ConsoleEncodingGuard" -p no:randomly
8 failed, 12 passed, 146 deselected in 11.26s
  FAILED test_help_strict_cp1252[argv2]      (scan --help)
  FAILED test_help_strict_cp1252[argv4]      (prepare --help)
  FAILED test_runtime_output_strict_cp1252
  FAILED test_scan_dry_run_strict_cp1252
  FAILED test_interpolated_stdout_value_strict_cp1252        ← V-01 closure discriminator
  FAILED TestConsoleEncodingGuard::test_console_streams_reconfigured_in_place
  FAILED TestConsoleEncodingGuard::test_console_guard_skips_stream_without_reconfigure
  FAILED TestConsoleEncodingGuard::test_console_guard_survives_unreconfigurable_text_wrapper

# GREEN — same tests against the working tree
$ uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard" -p no:randomly
20 passed, 146 deselected in 10.49s
```

The `8 failed / 12 passed` split is the `7 failed / 12 passed` recorded by the first pass plus the `V-01`
closure discriminator; the three `TestConsoleEncodingGuard` failures report
`AttributeError: module 'sofer.cli' has no attribute '_configure_console_streams'` at `tests\test_cli.py:1650`.
The 12 passes are the 10 other help invocations plus T4 and T5.

### 4.2 `V-01` closure — verified independently in this pass (not taken on trust)

The candidate gained one test-only follow-up (`tests/test_cli.py::TestSubprocessBoundary::
test_interpolated_stdout_value_strict_cp1252`, `+37` lines; recorded in `apply-progress.md` § `V-01 closure`).
Its discriminator is one of the eight RED failures above; its isolated form, reproduced here:

```text
$ PYTHONPATH=/tmp/sddv3-head uv run pytest \
      "tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252" \
      -q -p no:randomly --tb=long
1 failed
E     File ".../sddv3-head/sofer/cli.py", line 474, in _cmd_scan
E       print(f"     -> raw/{rel.as_posix()}")
E       UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 16: character maps to <undefined>
E     assert 1 == 0

$ uv run pytest "tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252" \
      -q -p no:randomly
1 passed
```

**Genuine RED discriminator, and it isolates the clause `V-01` flagged:** the crash site is the **ASCII
literal** `-> raw/` with the **interpolated** `rel` path carrying `U+2192` at position 16 — the failure
comes from the interpolation, not from a program-authored glyph (HEAD’s MOVE-preview literal was already
ASCII). The counting numbers that move with the closure: `tests/test_cli.py` `165 → 166` collected,
`-k cp1252` `16 → 17`, suite `1765 → 1766` passed. **`V-01` is CLOSED.**

### 4.3 Failure reasons reproduced earlier (unchanged, still valid)

| Test | Pre-fix failure |
|---|---|
| `test_help_strict_cp1252[argv2]` | `assert result.returncode == 0` → traceback; `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 830` |
| `test_help_strict_cp1252[argv4]` | same shape, `prepare` description |
| `test_runtime_output_strict_cp1252` | `AssertionError: assert 'Configuration errors' in ''`; stderr contained `UnicodeEncodeError … '\u2717' in position 4` (stdout empty — the `✗` write aborts before the report) |
| `test_scan_dry_run_strict_cp1252` | `assert 1 == 0`; traceback at HEAD `cli.py:569` `print(f"     \u2192 …")` |
| `test_interpolated_stdout_value_strict_cp1252` | `assert 1 == 0`; traceback at HEAD `cli.py:474` (ASCII literal + interpolated `U+2192`) |
| T6 / T7 / T8 | `AttributeError: module 'sofer.cli' has no attribute '_configure_console_streams'` |

---

## 5. Deviation adjudications

### D2 — “T4 and T5 are not RED” → **CONFIRMED**, and I add the decisive missing experiment

Reproduced the interpreter fact:

```text
$ PYTHONIOENCODING=cp1252 uv run python -c "import sys; print('stdout', sys.stdout.encoding, sys.stdout.errors); print('stderr', sys.stderr.encoding, sys.stderr.errors)"
stdout cp1252 strict
stderr cp1252 backslashreplace

$ PYTHONIOENCODING=cp1252:strict …      → stdout strict  / stderr backslashreplace   ← the errors field is IGNORED for stderr
$ PYTHONIOENCODING=cp1252:ignore …      → stdout ignore  / stderr backslashreplace
$ PYTHONIOENCODING=utf-8:strict  …      → stdout strict  / stderr backslashreplace
$ (bare, redirected stdout)             → out cp1252 surrogateescape / err cp1252 backslashreplace
```

**The proposed `PYTHONIOENCODING=cp1252:strict` variant cannot work** — CPython pins stderr’s error
handler to `backslashreplace` regardless of the `errors` field. The only way to make the child’s
stderr strict is to inject code into it (`sitecustomize`, `-c` wrapper), which would violate PB-09’s
`run_cli` contract. **Recommendation: do not add it.** It is not “worth adding later” — it is
unreachable through the frozen test boundary.

**Are T4/T5 legitimate regression guards or vacuous?** Verdict: **legitimate regression guards, and
not vacuous — but they carry no discriminating power for this fix on any interpreter reachable from
`run_cli`.** The masked vector is real, which is the piece apply only inferred:

```text
$ PYTHONIOENCODING=cp1252 PYTHONPATH=<HEAD-src> uv run python   # stderr manually reconfigured to strict
  sys.stderr.reconfigure(errors="strict"); runpy.run_module("sofer.cli", run_name="__main__")

T4 vector: …/sofer/cli.py:432  print(f"  X  Config file not found: {config_path}", file=sys.stderr)
           UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 53
T5 vector: Error: 'charmap' codec can't encode character '\u26a0' in position 2   → SystemExit code = 1
```

So both scenarios name a genuinely unencodable path; the crash is suppressed by CPython’s stderr
default, not by the tests being weak. Their assertions (`rc`, ASCII substring, strict-decodable
stderr, no `UnicodeEncodeError`) would catch a future regression that made stderr strict — e.g. if
`CONSOLE_ERRORS` were ever changed, or a second `reconfigure` were introduced.

**Is keeping them (with no rendering assertion) the right call? Yes.** CLI-R11 deliberately leaves
`?` vs an escape sequence open (“a placeholder or an escape sequence”); asserting either would
over-constrain the contract, violating R9 and the design’s Decision 5.

**Does the CLI-R11 requirement text remain honest given that stderr defaults to lossy-but-safe?**
**Yes.** The requirement constrains sofer’s behaviour *given* a non-representing encoding, and
`backslashreplace` is itself a *visible* substitution — the requirement forbids only silent loss
(`ignore`), which is exactly what CPython’s default also avoids. Nothing in the requirement text
claims pre-fix stderr was broken; only the **design’s RED column** for T4/T5 was wrong, and the
apply artifact recorded that honestly.

### D3 — order-dependent MCP failure → **CONFIRMED as real, pre-existing, and root-caused**

```text
$ uv run pytest "tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array" -q
1 passed in 0.29s                                       # isolation: PASS

$ uv run pytest tests/test_mcp_server.py tests/test_mcp_process.py tests/test_mcp_registration.py -q
1 failed, 323 passed, 3 skipped in 21.27s               # apply's exact selection
FAILED tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array

$ PYTHONPATH=<HEAD-src> uv run pytest <same three files> -q
1 failed, 323 passed, 3 skipped in 21.73s               # identical with HEAD's src ⇒ pre-existing
$ PYTHONPATH=<HEAD-src> uv run pytest "<the single test>" -q
1 passed in 0.32s

$ uv run pytest tests/test_mcp_registration.py -q        → 67 passed          # file alone: PASS
$ uv run pytest tests/test_mcp_registration.py tests/test_mcp_process.py -q → 81 passed  # PASS
$ uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q  → 1 failed, 309 passed, 3 skipped
$ uv run pytest tests/test_mcp_server.py "<the single test>" -q             → 1 failed, 243 passed, 3 skipped  ← minimal repro
```

**It is not really “order-dependent” in a mysterious way — it is a leaked-environment defect.** The
minimal 2-node reproduction and the root cause:

```text
$ HF_TOKEN=hf-x SOFER_MCP_APPROVAL_PHRASE=phrase-x uv run pytest "<the single test>" -q
1 failed in 0.50s                                       # an ambient HF_TOKEN alone is sufficient

$ PYTHONPATH=/tmp/envplugins uv run pytest tests/test_mcp_server.py -q -p envprobe   # probe prints os.environ at sessionfinish
ENVPROBE leaked: {'HF_TOKEN': 'from-dotenv'}
243 passed, 3 skipped

$ PYTHONPATH=/tmp/envplugins uv run pytest tests/test_mcp_server.py -q -p envprobe -k "not dotenv"
ENVPROBE leaked: {}                                     # no leak without the dotenv tests
$ … -k "test_dotenv_loads_when_env_absent"   → ENVPROBE leaked: {'HF_TOKEN': 'from-dotenv'}
$ … -k "test_dotenv_not_override_env"        → ENVPROBE leaked: {}
```

**Minimal reproduction (for the issue body):**

```bash
uv run pytest tests/test_mcp_server.py \
  tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array -q
```

Failing condition: any pytest session in which `tests/test_mcp_server.py` runs **before**
`tests/test_mcp_registration.py`, or any session whose ambient environment already carries
`HF_TOKEN` / `SOFER_MCP_APPROVAL_PHRASE`. Passing conditions: the test alone; the whole
`test_mcp_registration.py` file; `test_mcp_registration.py` + `test_mcp_process.py`; and the full
suite — **the full suite is green only by alphabetical accident** (`test_mcp_registration.py` sorts
before `test_mcp_server.py`), so “full suite green” is *not* evidence of isolation here. That is why
`apply-progress.md` saw it and the full-suite gate did not.

**One-line root-cause hypothesis:** `sofer.mcp_server._get_hf_token()` →
`_load_dotenv_if_available()` calls `dotenv.load_dotenv(override=False)`, which writes `HF_TOKEN`
into the process `os.environ` *outside* `monkeypatch`’s bookkeeping —
`tests/test_mcp_server.py::TestHfTokenFallback::test_dotenv_loads_when_env_absent` sets up a tmp
`.env` with `HF_TOKEN=from-dotenv` after `monkeypatch.delenv("HF_TOKEN")` on an *absent* variable
(a no-op that records nothing to undo), so the leak survives; the codex desired entry derives its
`env_vars` allow-list from `os.environ` (`collect_env()` / `_present_env_keys`), the pre-written
`env_vars = []` therefore no longer matches, the merge rewrites `.codex/config.toml` and creates
`config.toml.bak`, and the assertion `not bak.exists() or bak.read_bytes() == codex_path.read_bytes()`
fails with `At index 30 diff: b'[' != b'"'` (array form in `.bak`, normalized string form live).
**Not fixed here (out of scope); file as its own test-isolation issue.**

### D4 — repo-wide `ruff format --check` red on six untouched files → **CONFIRMED, pre-existing**

Re-confirmed in this pass (§2.2): `6 files would be reformatted, 61 files already formatted` (rc=1),
and the six are `tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`,
`tests/test_mcp_registration.py`, `tests/test_profile.py`, `tests/test_publish.py`,
`tests/test_splits.py`. None of the six appears in `git status --porcelain`, so their bytes are HEAD’s
bytes and `pyproject.toml` (the ruff config) is unmodified ⇒ pre-existing drift, not a regression. The
three files this change touched are reported as “already formatted” **when scoped** — worth noting for
the review: the repo-wide check is red on the branch before and after. **Warrants its own issue**
(single `ruff format` housekeeping commit on `dev`), non-blocking for this change.

### D1 — baseline count drift → **CONFIRMED, and the drift is wider than recorded**

The documented baselines are stale **in two places**, not one:

| Source | Documented | Actual (measured) |
|---|---|---|
| `AGENTS.md` rule 6 | “1149 tests currently pass (1151 collected, 2 skipped)” | **1747 passed / 6 skipped (1753 collected)** pre-change |
| `openspec/config.yaml` `context` | “1029 tests (2 skipped, 1031 collected, 334 spec scenarios)” | same 1753 |
| `tasks.md` 0.1 | “1149 passed / 2 skipped (1151 collected)” | same 1753 |

Measured exactly: `1772 collected` now; `test_cli.py` went `147 → 166` (+19, both measured) ⇒
`1753` pre-change. The tasks artifact’s real invariant (“no failures, count preserved or higher”) was
honoured: `1766 ≥ 1747` and the skip count is unchanged at 6. Non-blocking doc drift, **not caused by
this change** — recommend a separate doc-sync issue covering both `AGENTS.md` rule 6 and
`openspec/config.yaml`.

### D5 — T5 used the file variant, not the directory fallback → **CONFIRMED**

T5 registers `notes.txt` (unsupported format) beside `data.csv`, exits `0`, and asserts the ASCII
substring `Unsupported format` on stderr. It passes on the working tree, and the file variant did
pass `DatasetConfig.validate()` as assumption A2 predicted, so `Skipping directory` was unnecessary.
The frozen scenario names both variants, so choosing either satisfies the contract.

### D6 — pi-lens advisories on pre-existing lines → **CONFIRMED as untouched/out of scope**

I cannot re-verify that the advisories *fired* (no advisory log is persisted), but the substantive
claim is verifiable and holds: `git diff` contains **no** `tomli`, `shutil.move` or `float(val)` line
at all, i.e. every line those advisories concerned is byte-identical to HEAD and untouched by this
diff. No new suppression and no new `# type: ignore` was added (`grep` rc=1 in `cli.py`; `mypy` clean
under `warn_unused_ignores = true`). Rule 14 forbids new pragmas, so doing nothing was correct.
**This adjudication is load-bearing for `V-04`:** the same untouched `import tomli as _tomli`
fallback is what makes the ambient 3.10 mypy and COV-06 rows red.

---

## 6. Findings

### Blocking

**None.** `blockers: 0` and `critical_findings: 0` in the envelope reflect this: nothing in the change’s
diff is defective, and both mandated evidence commands are green in the CI interpreter.

### Closed in this pass

- **`V-01` — CLI-R11 scenario 2’s stdout clause had no test. CLOSED.** The candidate’s post-verify
  follow-up adds `tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252`
  (+37 lines), which drives the **TOML-declared-path** vector (`[[file]] local = "data→.csv"`, the arrow
  written as the ASCII source escape) through `scan dataset.toml --dry-run` and asserts `rc == 0` + the
  ASCII substring + `stdout.encode("cp1252")` + no traceback. Its RED was re-reproduced here: on HEAD the
  crash comes from the **interpolated** value at `cli.py:474` behind an already-ASCII `-> raw/` literal
  (§4.2). Both halves of the frozen scenario (stderr/argv and stdout/TOML) are now covered by genuine
  discriminators. The finding’s substantive note stands as a permanent record: the original test asserted
  **stderr** while the scenario text said **stdout**, and the delta’s informational mapping table described
  a vector the test did not implement — that is why the closure test exists.

### Non-blocking — still open, requiring a disposition at parent 8.2

- **`V-02` — assertion-quality note (not a defect).** `result.stdout.encode("cp1252")` /
  `result.stderr.encode("cp1252")` is a **round-trip tautology**: `run_cli(…, encoding="cp1252",
  errors="strict")` already decoded those bytes from cp1252, so re-encoding cannot fail. The design
  anticipated this (it explicitly rejected “assert only encodability”), and every one of T1–T5 has a
  real discriminator (`rc` and/or the ASCII substring and/or the absence of a traceback), so no test
  is vacuous — but the encodability assertions contribute nothing. Worth a one-line comment if the
  tests are ever touched; not worth a change now.
- **`V-03` — repo-wide `ruff format --check` is red on six untouched files.** Pre-existing (see D4).
  The branch does not regress it, but the repo-wide formatter gate as written in `tasks.md` 7.2
  cannot pass on `dev` either. Needs its own housekeeping issue.

### `V-04` — **diagnosed and tracked** (environmental, pre-existing, non-blocking)

**Symptom.** In the **ambient venv only** (Python 3.10.20 + `tomli` 2.4.1, i.e. after HEAD `1803acf`
reverted `.python-version` from `3.11` to `3.10`) two gates are red:
`uv run mypy src/` → **rc=1** with 5 × `[no-redef]` (§2.2b), and
`bash scripts/check_core_coverage.sh` → **rc=2** with `cli.py` at **99%**, `Missing 439-440` (§2.3).

**Diagnosis (parent-established, re-confirmed here).** Both red rows have **one** root cause: the local
3.10 interpreter installs `tomli` (declared `tomli>=2.0; python_version < '3.11'`), so
(a) `import tomli as _tomli` **and** the `except ImportError: import tomllib as _tomli` fallback both
define `_tomli` → `[no-redef]` in five **untouched** fallback sites
(`mcp_registration.py:130`, `config.py:153`, `model.py:399`, `cli.py:440`, `mcp_server.py:689`), and
(b) the fallback lines 439-440 can never execute, so they are uncovered. `.github/workflows/ci.yml` pins
the **lint job (`:15`) and the coverage job (`:61`) to 3.13**; under 3.13 `tomli` is absent
(`ModuleNotFoundError: No module named 'tomli'`, §2.2c), the name is defined once, and the `except` arm
executes. That is exactly why the 3.13 evidence in §2.2/§2.3 is green. It is also the latent issue
`AGENTS.md` rule 12 already documents for mypy.

**Measured green evidence in the CI interpreter (this pass).**

```text
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 ruff check src/ tests/   -> All checks passed!
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/                -> Success: no issues found in 32 source files
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/ scripts/       -> Success: no issues found in 33 source files
bash scripts/check_core_coverage.sh (data regenerated under 3.13)                -> rc=0, four files 100%
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 pytest tests/ -q --deselect <packaging test>
                                                                                 -> 1765 passed, 6 skipped, 1 deselected
```

**Trap to avoid (recorded so it is not rediscovered the hard way):** do **not** export
`UV_PROJECT_ENVIRONMENT` for a whole-suite run without deselecting
`tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version`. That test builds its
own temporary venv and **inherits** the variable, mixing the 3.13 `pyarrow` into the 3.10 interpreter it
spawns (`ModuleNotFoundError: No module named 'pyarrow.lib'`). It passes in the ambient venv
(`env -u UV_PROJECT_ENVIRONMENT uv run pytest <that test> -q` → `1 passed`, re-confirmed in this pass),
which is why the mandated `test_command` stays the ambient full-suite run and the 3.13 suite run carries
the one deselection with this reason recorded.

**Proof the change did not cause it:** (i) the same 5 mypy errors reproduce against HEAD’s `src` and all
five sites are on `import tomli as _tomli` fallback lines the diff does not touch (D6); (ii) HEAD’s own
untouched `cli.py` measures the same 2 misses at `438-439` and also **99%** in this environment; (iii)
the change adds `10` statements and `0` new misses (`574 − 564`, `2 − 2`).

**Disposition.** **Tracked as GitHub issue #178** — `dev-env: .python-version 3.10 makes local mypy and
the COV-06 coverage gate unsatisfiable (CI runs 3.13)` (OPEN). Accept as a local-environment artifact:
CI is green and the diff needs no change. **Not a defect of this change; do not fix here.**

### Pre-existing / out of scope — separate issues recommended

- **`I-01` (new issue): test isolation — `HF_TOKEN` leaks from `test_mcp_server.py`.** Full details,
  minimal reproduction and root-cause hypothesis in §5/D3. Severity: the suite’s greenness currently
  depends on file ordering.
- **`I-02` (new issue): stale test-count documentation in `AGENTS.md` rule 6 and `openspec/config.yaml`**
  (`1149/2` and `1029/2` vs the measured `1747/6`).
- **`I-03` (new issue): `ruff format` drift across six `tests/` files** (D4).
- **`I-04` (#178, already filed): the `.python-version` = 3.10 dev-env mismatch** — see `V-04` above.

---

## 7. Task checkbox verification

```text
$ grep -c "^\s*- \[x\]" openspec/changes/2026-09-13-fix-cli-console-encoding/tasks.md → 36
$ grep -n "^\s*- \[ \]" openspec/changes/2026-09-13-fix-cli-console-encoding/tasks.md
240:- [ ] 8.1 Start or reuse the bounded review over the finalized diff (single PR, no chaining), confirming: guard is the first statement of `main()`, no stream swapping, no `_DEFAULTS` entry, no pragma, no glyph assertion, and the docs row mirrored in both READMEs. <!-- sdd-owner: parent -->
241:- [ ] 8.2 Decide accept vs. rollback as one unit and trigger the archive/sync step so the frozen PB-02 and CLI-R11 deltas land in the canonical specs; do not hand-edit `openspec/specs/**` in this change. <!-- sdd-owner: parent -->
```

**Zero unchecked implementation tasks.** The only two unchecked lines are the two `sdd-owner: parent`
lifecycle rows (8.1, 8.2); they are not implementation work and are **not** archive blockers of the kind
this phase forbids. The `V-01` follow-up added no task row, so there was no checkbox to flip (native
status: `taskProgress 36/36`).

**Archive readiness: not yet ready — 8.1/8.2 remain open (parent-owned).** This phase raises **no
critical finding, no blocker and no unchecked implementation task**, so it removes itself as an archive
obstacle; the envelope is now `pass_with_warnings` (`blockers: 0`, `critical_findings: 0`). Note that
`sdd-sync` has **already run** — `sync-report.md` is present and both canonical specs are modified in the
working tree (`openspec/specs/cli/spec.md` +32, `openspec/specs/process-boundary/spec.md` +16/−3) — so the
action named in 8.2 is partially done already; the row itself is parent-owned and was not modified by
this phase.

---

## 8. Review workload / PR boundary

| Item | Forecast (`tasks.md`) | Actual (measured `git diff --numstat`) |
|---|---|---|
| Implementation + docs changed lines | ~155–168 | **300** (`290 + / 10 −`) |
| `src/` files | 2 (`config.py`, `cli.py`) | 2 (`config.py` +7, `cli.py` +44/−5) |
| Test files | 1 (`tests/test_cli.py`) | 1 (`+237/−5`) |
| Docs | `README.md` + `README_ES.md` | each `+1` |
| Canonical-spec sync (separate phase) | — | `openspec/specs/cli/spec.md` +32, `openspec/specs/process-boundary/spec.md` +16/−3 = **51** |
| 400-line budget risk | Low | **confirmed Low** (300 implementation lines; 351 including the sync output, both < 400) |
| Chained PRs recommended | No | **honoured** — single PR, no chain, only one work boundary |
| Chain strategy | pending / moot | **not selected, not needed** |
| `size:exception` | not required | **not self-granted** (the only matches in the change dir are statements that it is *not* used) |
| Session review budget (1500) | — | 351 ≪ 1500 |

The native ledger charges SDD-artifact lines (`tasks.md` checkbox diff, `apply-progress.md`,
`sync-report.md`, this report) to the attempt; that is process accounting, not review surface. The code
review boundary is the **300-line** diff plus the 51-line canonical-spec sync above, both inside the
400-line threshold. No scope creep was found — every changed line is traceable to tasks 3.1–3.5, 1.1–1.8 or
6.1–6.2, and no non-goal was violated (no glyph normalization beyond the five agreed sites, no `_DEFAULTS`
key, no stream swapping, no `errors="ignore"`, no MCP-path change, no second helper, no glyph assertion, no
unmandated help text). The only post-verify addition is the test-only `V-01` closure, confined to
`tests/test_cli.py`.

---

## 9. Requirements NOT verified (with reason)

1. **PB-02 requirement prose, “These invocations SHALL run on the ubuntu CI matrix”** — environment
   limitation: this host is Windows and **no CI run was executed by this phase**. What *is* verified is
   the local equivalent (child process forced to `PYTHONIOENCODING=cp1252` with `errors="strict"`
   decoding), and static inspection of `.github/workflows/ci.yml` (`os: [ubuntu-latest,
   windows-latest]`, `python-version: ["3.10"…"3.14"]`), which shows the new tests will execute on the
   ubuntu matrix. **Still not exercised; unchanged from passes 1–2.**
2. **“Windows-only behavior SHALL skip without privileges rather than fail”** — **not exercised**,
   because this change adds no Windows-only test (nothing to skip); the clause is untouched, not proven.

Everything else in both frozen deltas is verified by a command and an observed output in §2–§4. The
former item 1 of this list (CLI-R11 scenario 2’s stdout clause) is **no longer unverified — `V-01` is
closed** (§4.2).

---

## 10. Strict TDD / skill resolution

- **Strict TDD: inactive.** `openspec/config.yaml` sets `strict_tdd: false` (and
  `testing.strict_tdd: false`); `apply-progress.md` records it as not active; the parent prompt does not
  activate it. Therefore no `TDD Cycle Evidence` table is required, no RED-GREEN-REFACTOR audit is
  required, and the global `strict-tdd-verify` support guidance was not applicable (no project-local
  `.pi/gentle-ai/support/` override exists; the global support dir exists but was not needed). The design
  still demanded provable RED and this report reproduced it independently (§4), which exceeds the
  inactive-strict-TDD bar.
- **Skill resolution:** `none`. The prompt injected no `## Skills to load before work` paths, and no
  phase skill is required for verification with strict TDD inactive. No fallback registry/path lookup was
  performed beyond confirming the absence of a project-local support override.

---

## 11. Admission proof (native gate) and artifact hashes

### 11.1 Envelope and hashes

The envelope is the first non-empty line of this file (no title, no blank line, no front matter before it)
and closes with a bare ```` ``` ```` fence.

```text
$ sha256sum /tmp/sdd-verify-rerun2/test_output.txt /tmp/sdd-verify-rerun2/build_output.txt
be8b556f4905054ec808cf92f7fa0242382d0161bdff42edf8feb1bdb074de0e  /tmp/sdd-verify-rerun2/test_output.txt
beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7  /tmp/sdd-verify-rerun2/build_output.txt
```

- `test_output_hash` = sha256 of the **complete captured stdout+stderr** of `uv run pytest tests/ -q`
  (**5301** bytes), captured in the **ambient 3.10** venv; `test_exit_code = 0` is that invocation’s real
  exit code.
- `build_output_hash` = sha256 of the **complete captured combined output** of the two `3.13` commands
  joined by `&&` (**64** bytes: `All checks passed!\nSuccess: no issues found in 32 source files\n`);
  `build_exit_code = 0` is that chain’s real exit code.
- `evidence_revision` = the candidate’s `current_snapshot_identity` read from
  `gentle-ai review status --cwd /c/Users/elaze/Desktop/sofer --contract gentle-ai.review-integration/v2
  --agent pi --next-transition`
  (`"current_snapshot_identity": "sha256:1399e1cd7bb6e4b58ce1966eca42be8da9b5cf6026b09af6762d0ee6781a28db"`,
  identical to `projection.initial_snapshot_identity` and to `target_identity`).
- `test313_output_hash` (documented in §2.1, **not** an envelope field):
  `e8689a0e03fa5089ebd411f3a8005dc7bf75f13cdf7db8ff76f3bbdcfaea8988`.

Every capture was taken in this pass and retained until this report was written.

### 11.2 Validator run

```text
$ gentle-ai sdd-verify-validate --input openspec/changes/2026-09-13-fix-cli-console-encoding/verify-report.md --requirements 2 --scenarios 7
{
  "valid": true,
  "verdict": "pass_with_warnings",
  "evidence_revision": "sha256:1399e1cd7bb6e4b58ce1966eca42be8da9b5cf6026b09af6762d0ee6781a28db"
}
# rc=0
```

**Result: admitted (rc=0) with `verdict: pass_with_warnings`** — the invariant proof that the envelope now
reflects the CI interpreter honestly. Compare the two earlier revisions of this file: the first was
refused (`verify report admission denied: missing valid gentle-ai.verify-result/v1 envelope`), the second
was admitted but could only carry `verdict: fail`.

### 11.3 How the envelope's exact field shapes and the verdict rules were determined

The shapes were found by probing the validator against a scratch copy of the envelope in
`/tmp/sdd-verify-rerun/probe*.md` (never against this report), because the written contract in `--help`
specifies types only for the three hashes and the verdict:

```text
$ gentle-ai sdd-verify-validate --help
  required envelope fields: schema, evidence_revision, verdict, blockers, critical_findings, requirements,
    scenarios, test_command, test_exit_code, test_output_hash, build_command, build_exit_code,
    build_output_hash
  evidence_revision, test_output_hash, and build_output_hash must each be sha256:<64 lowercase hex>.
  accepted verdicts: pass, pass_with_warnings, fail
  requirements and scenarios are completed/total; each completed count must not exceed its total.
  --requirements and --scenarios must exactly equal their report totals.
  Independent test and build execution evidence is required for a passing verification result.

# shape probes (same body, one field varied)
blockers: []              -> Error: ... invalid blockers in verify result envelope
blockers: 0               -> (advances)   ⇒ blockers/critical_findings are INTEGER COUNTS
requirements: 2           -> Error: ... invalid requirements in verify result envelope
requirements: 2/2         -> (advances)   ⇒ requirements/scenarios are "completed/total"
verdict: pass_with_warnings + build_exit_code: 0  -> admitted
verdict: pass_with_warnings + build_exit_code: 1  -> Error: ... passing verdict contradicts failing or
                                                      incomplete evidence
verdict: fail              + build_exit_code: 1  -> admitted
verdict: pass_with_warnings + blockers: 2         -> Error: ... passing verdict contradicts failing or
                                                      incomplete evidence
```

The operative rule for this pass: **a passing verdict is refused when any evidence is red.** In the
ambient interpreter the mandated `build_command` exited `1`, so pass 2’s honest envelope had to be
`fail`. With the build evidence captured in the **CI interpreter**, `build_exit_code` is `0` and
`verdict: pass_with_warnings` is both admitted and truthful. The count fields stay in the `2/2` / `7/7`
form the validator accepts while matching the parent-supplied totals (`--requirements 2 --scenarios 7`).

---

## 12. Commands executed (verbatim index)

```text
# mandated evidence (captured to files, hashed above)
uv run pytest tests/ -q
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 ruff check src/ tests/ && UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/

# CI-interpreter parity / V-04 diagnosis
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 pytest tests/ -q --deselect "tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version"
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 coverage run -m pytest -q --deselect "tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version"
bash scripts/check_core_coverage.sh
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 mypy src/ scripts/
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 python --version
UV_PROJECT_ENVIRONMENT=/tmp/venv313 uv run --python 3.13 python -c "import sys;print(sys.version.split()[0]); import tomli"
uv run python --version && cat .python-version
uv run python -c "import tomli, sys; print('tomli', tomli.__version__, 'py', sys.version.split()[0])"
uv run mypy src/
env -u UV_PROJECT_ENVIRONMENT uv run pytest "tests/test_packaging.py::TestInstalledCli::test_console_script_help_and_version" -q
grep -n "python-version\|mypy" .github/workflows/ci.yml
grep -n 'python-version' .github/workflows/ci.yml

# suite shape / counts
uv run pytest tests/ --collect-only -q
uv run pytest tests/test_cli.py --collect-only -q
uv run pytest tests/test_cli.py -q --collect-only -k cp1252

# RED / GREEN (re-reproduced in this pass)
mkdir -p /tmp/sddv3-head && cp -r src/sofer /tmp/sddv3-head/sofer
git show HEAD:src/sofer/cli.py    > /tmp/sddv3-head/sofer/cli.py
git show HEAD:src/sofer/config.py > /tmp/sddv3-head/sofer/config.py
PYTHONPATH=/tmp/sddv3-head uv run python -c "import sofer.cli as m; print(m.__file__, hasattr(m,'_configure_console_streams'))"
PYTHONPATH=/tmp/sddv3-head uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard" -p no:randomly
uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard" -p no:randomly

# rule-14 / COV-06
grep -c "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py

# scope / whitespace / formatting
git status --porcelain && git diff --numstat && git diff --check
uv run ruff format --check src/ tests/
uv run ruff format --check src/sofer/cli.py src/sofer/config.py tests/test_cli.py
sha256sum /tmp/sdd-verify-rerun2/{test,test313,build}_output.txt

# review authority
gentle-ai review status --cwd /c/Users/elaze/Desktop/sofer --contract gentle-ai.review-integration/v2 --agent pi --next-transition

# admission
gentle-ai sdd-verify-validate --help
gentle-ai sdd-verify-validate --input openspec/changes/2026-09-13-fix-cli-console-encoding/verify-report.md --requirements 2 --scenarios 7
```

No git write command was executed. Scratch trees live outside the repository
(`C:\Users\elaze\AppData\Local\Temp\sddv3-head`, `/tmp/sdd-verify-rerun2`); the only file written by this
phase is this report. The working tree is otherwise byte-identical to the state found at the start of this
phase (same seven modified paths and one untracked change directory as `git status --porcelain` reports
above).
