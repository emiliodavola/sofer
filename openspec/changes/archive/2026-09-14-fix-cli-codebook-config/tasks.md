# Tasks: fix-cli-codebook-config

**Change**: `2026-09-14-fix-cli-codebook-config` · **Issue**: #182 · **Branch**: `fix/182-cli-codebook-config`
(`.git/HEAD` → `ref: refs/heads/fix/182-cli-codebook-config`, verified this phase)
**Store**: hybrid — this file **and** Engram topic key `sdd/2026-09-14-fix-cli-codebook-config/tasks` (type `architecture`)
**Basis**: spec delta `specs/codebook/spec.md` (**CB-R11**, 5 scenarios) + `design.md` (D1–D6). Strict TDD off (`config.yaml`), tests follow the delta.
**Decided approach — Option B, chosen deliberately**: `codebook._read_csv`'s CSV arm delegates to `_csv_reader.stream_csv`
(one CSV reader in the repo, AGENTS rule 4) instead of a bare `open()`. Rationale: Option A cannot walk the
`utf-8-sig → utf-8` fallback that CB-R11 scenarios 3 & 5 require without re-rolling the chain (a rule-4 violation).
**Accepted risk of B**: it touches the shared `_read_file` CSV arm also used by `--all-files` (mitigated by preserving the
explicit-parameter behaviour that `generate_all` relies on and by passing `max_sample=None` explicitly so rows are never
capped twice). If B cannot land inside the budget, the only sanctioned fallback is A **plus** a spec correction to
scenarios 3/5 — never a locally re-rolled encoding chain.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~70 (range 55–95: ~25 production + ~45 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

### Suggested Work Units

| WU | Goal | Scope | Boundaries (start → finish · verify · rollback) |
|----|------|-------|-------------------------------------------------|
| WU1 | CLI reads resolved config, fails cleanly | `src/sofer/cli.py` `_cmd_codebook` single-file branch | Start when baseline tally captured → finish when kwargs + `except (ValueError, LookupError)` land · verify `-k codebook_` focused run · rollback: revert one hunk |
| WU2 | One CSV reader repo-wide | `src/sofer/codebook.py` `_read_csv` → `stream_csv` adapter | Start after WU1 → finish when adapter passes `delimiter`/`encoding` through, `max_sample=None`, `_read_tsv` unchanged · verify `tests/test_codebook.py` + `--all-files` tests · rollback: restore `_read_csv` body |
| WU3 | CB-R11 parity pinned at the subprocess boundary | `tests/test_cli.py` (4 tests) | Start after WU2 → finish when all 4 pass via `run_cli` · verify focused + full suite + `check_core_coverage.sh` · rollback: drop the 4 test hunks |

## Apply Tasks

### 1. `src/sofer/cli.py` — resolved config + diagnostic (D1, D2, D3)

- [x] 1.1 Capture the pre-change baseline suite tally *before editing anything* — `uv run pytest tests/ -q`; record the exact
  `N passed, M skipped` line. Do **not** trust the last known `1766 passed, 6 skipped`; re-derive it. <!-- sdd-owner: implementation -->
  - Evidence: the baseline line quoted verbatim in the apply summary; every later tally is compared against it.
- [x] 1.2 In `_cmd_codebook`'s single-file branch (`cli.py:224-238`), resolve `delimiter = config.CSV_DELIMITER` and
  `encoding = config.CSV_ENCODING` at call time beside the existing `max_sample` resolution, and pass both into
  `generate_codebook(args.csv, output_path=…, delimiter=delimiter, encoding=encoding, max_sample=max_sample)`. <!-- sdd-owner: implementation -->
  - Evidence: `cli.py` diff shows the two kwargs; `main()` already calls `config.reload(None)` before dispatch (TC-04).
- [x] 1.3 Wrap the `generate_codebook(...)` call in `try:` and add `except (ValueError, LookupError) as exc:` →
  `print(f"Error: {exc}", file=sys.stderr)` + `return 1`, reusing the `--all-files` sibling idiom (`cli.py:210-213`) verbatim.
  No `except Exception`; `codebook.generate`'s defaults untouched. <!-- sdd-owner: implementation -->
  - Evidence: `UnicodeDecodeError ⊂ UnicodeError ⊂ ValueError`, so decode exhaustion reaches this handler; `LookupError` covers a bad codec name (TC-13).
- [x] 1.4 Extend `_cmd_codebook`'s docstring to document the resolved config source and the diagnostic contract (AGENTS rule 2). <!-- sdd-owner: implementation -->
  - Evidence: `uv run mypy src/` clean and a diff line in the docstring naming `config.CSV_DELIMITER` / `config.CSV_ENCODING`.

### 2. `src/sofer/codebook.py` — delegate to the single CSV reader (D4-B)

- [x] 2.1 Rewrite `_read_csv` (`codebook.py:65-92`) as a thin adapter over `_csv_reader.stream_csv(path, delimiter=…, encoding=…, max_sample=None)`:
  consume the `(header, row)` generator, take the first yield as headers, transpose the remaining rows into the column-wise
  `tuple[list[str], list[list[str]], None]` shape callers expect, and preserve the empty-file `([], [], None)` return. <!-- sdd-owner: implementation -->
  - Evidence: `tests/test_codebook.py` green; the existing empty-file placeholder path still returns no headers.
- [x] 2.2 Pass `max_sample=None` **explicitly** to `stream_csv` so its config-default resolution never caps a full scan —
  `generate` already applies `_build_markdown(max_sample)` and a silent cap would double-sample. <!-- sdd-owner: implementation -->
  - Evidence: `grep -n "max_sample=None" src/sofer/codebook.py` shows the explicit argument on the `stream_csv` call.
- [x] 2.3 Keep `_read_file`'s explicit `delimiter`/`encoding` parameters and `_read_tsv` behaviour intact (it delegates to
  `_read_csv` with `delimiter="\t"`), so `--all-files`' dataset-`[meta]` tier (`codebook.py:505-506`) and every direct
  library caller are unchanged; drop `import csv` if ruff reports it unused. <!-- sdd-owner: implementation -->
  - Evidence: `uv run pytest tests/ -q` includes the `--all-files` codebook tests; `uv run ruff check src/ tests/` clean.
- [x] 2.4 Update `_read_csv`'s docstring to name the delegated reader and the fallback policy (explicit params first, then
  `utf-8-sig → utf-8`; no `latin-1`/`cp1252`) (AGENTS rule 2). <!-- sdd-owner: implementation -->
  - Evidence: docstring names `_csv_reader.stream_csv`; `_csv_reader.py` itself is byte-identical (`git diff --stat`).

### 3. `tests/test_cli.py` — four CB-R11 boundary tests (D5)

- [x] 3.1 Add `test_codebook_honors_tool_sofer_delimiter`: `[tool.sofer] csv_delimiter = ","` + a `,`-delimited file,
  invoked through `tests/conftest.py::run_cli` → codebook shows **2 columns** (the structure `test_mcp_server.py:3564` already asserts). <!-- sdd-owner: implementation -->
  - Evidence: test green via `run_cli`; scenario 1 + MCP-parity scenario.
- [x] 3.2 Add `test_codebook_honors_tool_sofer_encoding`: `[tool.sofer] csv_encoding = "cp1252"` + cp1252-only bytes →
  success with the same columns; a non-default-encoding file must fail under the old literal default. <!-- sdd-owner: implementation -->
  - Evidence: test green; confirms the configured encoding is honoured first (scenario 1).
- [x] 3.3 Add `test_codebook_undecodable_file_is_diagnostic`: bytes undecodable under the configured encoding **and** both
  fallbacks → `rc != 0`, stderr starts with `Error: `, `"Traceback"` absent. <!-- sdd-owner: implementation -->
  - Evidence: test green; executes the `ValueError` arm of 1.3 (scenarios 3 + 5).
- [x] 3.4 Add `test_codebook_unknown_codec_is_diagnostic`: `[tool.sofer] csv_encoding = "not-a-codec"` → same three
  assertions. This is the `LookupError` arm that keeps `cli.py` at 100.00%. <!-- sdd-owner: implementation -->
  - Evidence: test green; `# pragma: no cover` stays forbidden (rule 14) and the arm is genuinely executed (scenario 4).

- [x] 3.5 Add the two in-process carriers for the `ValueError`/`LookupError` arms
  (`TestCodebookSingleFileDiagnosticArmsInProcess`). **Added during apply, not in D5** — D5 assumed the `run_cli`
  boundary tests feed the coverage measurement, but `uv run coverage run -m pytest` instruments only the test process
  (subprocess execution is never recorded: the four boundary tests alone leave `cli.py` at 5%), so without an in-process
  carrier the COV-06 per-file gate measured 99% with lines 264-266 missing. The spec delta's Test Mapping explicitly
  permits an in-process `_cmd_codebook` call that MUST NOT replace the boundary test; this mirrors the
  `TestCodebookAllFilesErrors` precedent for the `--all-files` arm. <!-- sdd-owner: implementation -->
  - Evidence: `bash scripts/check_core_coverage.sh` exit 0 with `cli.py` at 100.00% and an empty `Missing` column.
### 4. Evidence gates (run after 1–3)

- [x] 4.1 Re-run the full suite and compare against the 1.1 baseline: `uv run pytest tests/ -q` → the same baseline tally
  **plus** 4 new tests, 0 failures (AGENTS rule 6). <!-- sdd-owner: implementation -->
  - Evidence: post-change line quoted verbatim beside the baseline line; delta explained test-by-test.
- [x] 4.2 Focused run: `uv run pytest tests/test_cli.py tests/test_codebook.py -q` → green. <!-- sdd-owner: implementation -->
  - Evidence: command output pasted, 0 failures.
- [x] 4.3 Core-coverage mandate: `bash scripts/check_core_coverage.sh` → exit 0 with `cli.py` at **100%** and an **empty
  `Missing` column**. <!-- sdd-owner: implementation -->
  - Evidence: pasted `coverage report -m` row for `src/sofer/cli.py` at 100.00%, no missing lines.
- [x] 4.4 Static gates: `uv run mypy src/` clean; `uv run ruff check src/ tests/` clean; `uv run ruff format --check src/ tests/` clean. <!-- sdd-owner: implementation -->
  - Evidence: all three exit 0 with no output.
- [x] 4.5 Mechanical scope check: `git diff --stat` shows **zero** paths under `src/sofer/_converters.py` and
  `src/sofer/prepare.py` (issue #181), and **zero** changes under `src/sofer/mcp_server.py` or `tests/test_mcp_server.py`. <!-- sdd-owner: implementation -->
  - Evidence: pasted `git diff --stat`; changed paths are exactly `src/sofer/cli.py`, `src/sofer/codebook.py`, `tests/test_cli.py`, `openspec/changes/2026-09-14-fix-cli-codebook-config/**`.
- [x] 4.6 Repo-wide grep proving no behaviour still references the old duplicated reader path: no CSV parsing or fallback
  chain remains outside `_csv_reader.py` (e.g. `grep -rn "csv\.reader\|ENCODING_FALLBACKS" src/sofer/` reports only
  `_csv_reader.py`). <!-- sdd-owner: implementation -->
  - Evidence: pasted grep output; `src/sofer/codebook.py` contributes zero hits for `csv.reader` and zero for the fallback list.

## Verify Gates

Owner: **verify phase** (no checkboxes — these must not gate `apply` completion).

- Run the change's spec delta review: each CB-R11 scenario (5) maps to a named test from §3, with the `latin-1`-rejection
  precedent `tests/test_quality.py:750-757` still green. Owner: verify.
- Re-run the full suite and confirm scenario coverage per `openspec/config.yaml` `verify.test_command`. Owner: verify.
- Confirm `cli.py` 100.00% and rollback feasibility (single-commit revert, no migration, no persisted artifact). Owner: verify.

## Parent-Owned Lifecycle (post-apply, not gated by checkboxes)

Owner: **parent/orchestrator** — no `- [ ]` items below.

- Bounded review of the apply diff against D1–D6 and the CB-R11 delta. Owner: parent.
- Canonical spec sync of `openspec/specs/codebook/spec.md` (CB-R11) at archive time. Owner: parent.
- Delivery: commit / push / PR (branch `fix/182-cli-codebook-config`) and issue #182 closure. Owner: parent.

## Out of Scope (explicit non-goals)

Zero paths under `src/sofer/_converters.py` / `src/sofer/prepare.py` — that delimiter/encoding defect is issue **#181**, a
separate change with its own SDD cycle. Zero MCP changes: `mcp_server.py:1481-1487` and `:2890-2893` are already correct and
pinned by `tests/test_mcp_server.py:3564-3574`. No change to `codebook.generate`'s parameter defaults, to `generate_all`'s
dataset-`[meta]` tier (`codebook.py:505-506`), or to `_read_tsv` semantics. No new CLI flag; therefore no `README.md` /
`README_ES.md`, `pyproject.toml`, or workflow change. No codec-name validation at config-merge time (would re-open TC-13).
Do not modify `proposal.md`, `design.md`, the spec delta, `openspec/specs/**`, or `openspec/changes/archive/**`. No commit,
push or PR.

## Closing Note

§1–§4 are the only `apply` work; all twelve boxes close before `apply` finishes. §Verify Gates and §Parent-Owned Lifecycle
carry no checkboxes by design, so the checkbox count reaching zero means implementation is done and the verify phase can
start. Estimated ~70 changed lines against a 400-line budget → `Low` risk, single PR, no chain needed
(`Decision needed before apply: No`).
