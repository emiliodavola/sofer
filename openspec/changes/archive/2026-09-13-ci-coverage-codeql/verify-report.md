# Verify Report — CI coverage gate and CodeQL scanning (2026-09-13-ci-coverage-codeql)

**Status: PASS (implementation) — ARCHIVE NOT READY (parent-owned commits pending)**

Authoritative verify report (rewritten by the verify phase; consolidates the apply draft
and the 2026-09-13 addendum). Branch `feat/ci-coverage-codeql` (base `dev`). Artifact
store: openspec. Strict TDD: **disabled** (`openspec/config.yaml` `strict_tdd: false`) —
no TDD cycle evidence is required; the C-phase test module was authored GREEN-last by
construction (it asserts A+B+D+E content). Floor under verification: **90** (user
directive, 2026-09-13; config `rules.verify.coverage_threshold: 90`).

The gate is **RED by design** under the amended floor: measured total is 88% < 90, so the
config-driven gate exits rc 2. This is the verified-as-designed state — the armed gate is
the forcing function for the coverage-raising follow-up change. It is not a failure of this
change. The positive exit-code leg is proven by the `--fail-under=88` probe (rc 0), and the
negative leg by `--fail-under=100` (rc 2); probes are verify-phase evidence only and never
appear in a shipped workflow (CI-01, test #2 enforces).

---

## 1. Gate evidence — exact outputs (rerun by this verify phase)

| # | Command | Exact output | rc |
| --- | ------- | ------------ | -- |
| G1 | `uv run pytest tests/ -q` | `1567 passed, 6 skipped, 13 warnings in 44.43s` | 0 |
| G2 | `uv run pytest tests/test_ci_workflows.py -q` | `................` `16 passed in 0.10s` (test #13 RUNS, not skipped — config.yaml present locally) | 0 |
| G3 | `uv run ruff check src/ tests/ scripts/` | `All checks passed!` | 0 |
| G4 | `uv run mypy src/ scripts/` | `Success: no issues found in 33 source files` | 0 |
| G5 | `git diff --check` | clean (0 whitespace errors) | 0 |
| V1 | `uv run coverage run -m pytest` (complete suite under instrumentation, PB-05) | `1567 passed, 6 skipped, 13 warnings` | 0 |
| V1 | `uv run coverage report -m` (config `fail_under = 90`, no flag) | `TOTAL 5995 638 2318 280 88%` + `Coverage failure: total of 88 is less than fail-under=90` — per-file missed lines listed (`-m`, `show_missing`) | **2 (red by design)** |
| V1b | `uv run coverage report -m --fail-under=88` (probe, re-reads V1 `.coverage`) | `TOTAL 5995 638 2318 280 88%` | 0 |
| V2 | `uv run coverage report -m --fail-under=100` (probe, re-reads V1 `.coverage`) | `Coverage failure: total of 88 is less than fail-under=100` | 2 |

V1/V1b/V2 prove the config-driven gate's exit-code contract end-to-end: the same
`.coverage` dataset yields rc 2 at an armed floor above the measurement, rc 0 at a floor
at-or-below it, and rc 2 at a floor above it — coverage.py enforces `[tool.coverage.report]
fail_under` itself, with no flag in any workflow.

**90-floor red-gate verdict**: the gate is armed at 90 while today's total is 88%; every
PR/release run below the floor fails at `coverage report -m` (rc 2) with the missing-lines
report in the log. This is the user-chosen forcing function (proposal + design amendment),
the expected verified state, and NOT an implementation defect. Per-file gaps to close in
the follow-up: `cli.py` 84%, `profile.py` 80%, `mcp_registration.py` 80%, `publish.py` 87%
(proposal baseline).

---

## 2. Per-requirement verification (CI-01..CI-06)

| Req | Scenario | Verification | Result |
| --- | -------- | ------------ | ------ |
| CI-01 | Config declares the 90% floor | `_load_toml("pyproject.toml")["tool"]["coverage"]["report"]` — `fail_under = 90` beside `show_missing = true` (pyproject.toml:97–98). Test `test_pyproject_declares_coverage_fail_under_90` (L39) | **PASS** |
| CI-01 | Gate is config-driven | Raw-text scan of ci.yml + release.yml: **zero** hits for `fail_under` / `--fail-under` / `fail-under` (grep rc 1 = no match; repo-wide the value exists only at pyproject.toml:98); each `coverage` job's report-step `run` is exactly `uv run coverage report -m`. Test `test_coverage_gate_is_config_driven_without_cli_floor` (L145). Local gate run: V1 rc 2, V1b rc 0, V2 rc 2 (exit-code leg) | **PASS** |
| CI-01 | Report honors show_missing | `show_missing is True`; `-m` on the report step puts per-file missed lines in the log (V1 output). Test `test_coverage_report_honors_show_missing` (L160) | **PASS** |
| CI-02 | htmlcov artifact step present | Both `coverage` jobs run `uv run coverage html` + `actions/upload-artifact@v4` with `name: coverage-html`, `path: htmlcov` (ci.yml coverage job; release.yml coverage job). Test `test_coverage_jobs_generate_and_upload_htmlcov` (L173) | **PASS** |
| CI-02 | Missing-lines list in the job log | Report step `run == "uv run coverage report -m"` in both workflows (gate step runs BEFORE `coverage html`). Test `test_coverage_report_step_lists_missing_lines` (L185) | **PASS** |
| CI-02 | No XML or third-party coverage references | Case-insensitive full-text scan of both workflows: zero matches for `coverage xml`, `codecov`, `coveralls`, `badge`. Test `test_no_xml_codecov_or_badge_references_in_workflows` (L190). No badge in READMEs (S3 mirror check) | **PASS** |
| CI-03 | Coverage job in the release needs chain | release.yml: `coverage` job exists; `coverage.needs == [lint, test]`; `build.needs ⊇ {coverage}`; `citation-check.needs == [coverage]` (its first explicit `needs`; now waits on lint/test/coverage — intended gated chain); `release.needs ⊇ {coverage}`. Test `test_release_is_gated_on_the_coverage_job` (L199) | **PASS** |
| CI-03 | Tag push below the floor yields no release | **Static evidence (needs-DAG proof, §4)**: `coverage → {build, citation-check, release}` direct edges + GitHub transitive skip-on-failed-need ⇒ failed coverage skips all dependents ⇒ `softprops/action-gh-release` never runs ⇒ no wheel-build validation, no GitHub Release. No publish path bypasses the gate | **PASS** |
| CI-04 | Push, PR, and weekly triggers present | codeql.yml: `push.branches == [main, dev]`, `pull_request.branches == [main, dev]`, one `schedule` cron `"0 3 * * 1"` (matches `\d+ \d+ \* \* \d+`). Test `test_codeql_has_push_pr_and_weekly_triggers` (L216) | **PASS** |
| CI-04 | Pull request includes dev | `set(pull_request.branches) == {"main", "dev"}`. Test `test_codeql_pull_request_targets_dev` (L227) | **PASS** |
| CI-04 | SARIF upload permission granted | `permissions == {actions: read, contents: read, security-events: write}` (full block, D4); `init` declares `languages: python`; `github/codeql-action/analyze@v3` exists (spec-wording resolution per D3 — `languages` is an `init` param, not duplicated onto `analyze`). Test `test_codeql_security_write_permission_and_python` (L235) | **PASS** |
| CI-05 | Config file referenced by init | `init` step: `config-file == "./.github/codeql/config.yml"`, `languages == "python"` (Advanced Setup). Test `test_codeql_init_references_config_file` (L256) | **PASS** |
| CI-05 | Paths-ignore covers non-code trees | `.github/codeql/config.yml`: `paths-ignore` ⊇ `{docs/, .github/, openspec/}` plus `cache/`, `tmp/` (generated artifacts); `src/sofer/` NOT listed; no `queries:` key (default queries). Test `test_codeql_paths_ignore_covers_non_code_trees` (L270) | **PASS** |
| CI-06 | Config declares coverage available at 90 | **Working-tree evidence (§5)**: gitignored `openspec/config.yaml` — `testing.coverage.available: true`, `testing.coverage.command: "uv run coverage run -m pytest"`, `rules.verify[last].coverage_threshold: 90`; `ci_test_command`/`test_command` unchanged (PB-05 guard). Test `test_openspec_config_declares_coverage_available_at_90` (L282, skip-if-absent guard — runs here) | **PASS** |
| CI-06 | CONTRIBUTING documents the floor | CONTRIBUTING.md:30–31 both coverage commands (gate: 90%); :106–109 `Total coverage is gated at **90%** (fail_under = 90 in pyproject.toml)` + spec-change requirement; `no drop in coverage` absent. Test `test_contributing_documents_coverage_floor` (L295) | **PASS** |
| CI-06 | README mirrors README_ES | **Static evidence (mirror diff, §4)**: headings `## Quality gates and security scanning` (README.md:750, ToC :36) / `## Controles de calidad y escaneo de seguridad` (README_ES.md:789, ToC :38) both at column 0, both between Architecture/Related and Resumen/Referencias; backtick technical tokens **identical** in both files; only prose translated; no badge added | **PASS** |
| CI-06 | PR template checklist item | PULL_REQUEST_TEMPLATE.md Checklist: `- [ ] Coverage gate met — uv run coverage report -m ≥ 90% (CI enforces fail_under = 90)` after "New behaviour covered by tests", alongside the existing `README_ES.md updated` item. Test `test_pr_template_has_coverage_checklist_item` (L306) | **PASS** |

**17/17 scenarios resolved** (spec Test Mapping): 15 pytest-assertable scenarios → the 15
scenario-mapped test functions; CI-03 S2 (no release below floor) and CI-06 S3 (README
mirror) → verify-phase static evidence per the PB-05/MSP-R12 precedent. The module ships
16 functions (the 15 mapped + `test_ci_workflow_files_present`, the supporting presence
guard, D6 row 0). "16/17" reconciliation: 16 functions cover the 17 scenarios as
15-tests + 2-static.

---

## 3. Scenario/test mapping (rule 6)

Every spec scenario resolves to a green test (G2 run, 16 passed) or recorded static
evidence (§4). Full cross-check: CI-01 S1→T1, CI-01 S2→T2+V1/V1b/V2, CI-01 S3→T3, CI-02
S1→T4, CI-02 S2→T5, CI-02 S3→T6, CI-03 S1→T7, CI-03 S2→DAG proof, CI-04 S1→T8, CI-04
S2→T9, CI-04 S3→T10, CI-05 S1→T11, CI-05 S2→T12, CI-06 S1→T13, CI-06 S2→T14, CI-06
S3→mirror diff, CI-06 S4→T15.

---

## 4. Static evidence (non-pytest)

### CI-03 S2 — needs-DAG proof (no release below floor)

Parsed `.github/workflows/release.yml` edges (diff vs base `dev`):
```
coverage       -> [lint, test]                      (new job between test and build)
build          -> [lint, test, coverage]            (+coverage)
citation-check -> [coverage]                        (none -> [coverage]; first explicit needs)
release        -> [lint, test, build, citation-check, coverage]   (+coverage)
```
`coverage` is a **direct** dependency of `build`, `citation-check`, and `release`;
GitHub's skip-on-failed-need is transitive, so a tag push whose coverage job fails
(88% < 90) skips every dependent job and `softprops/action-gh-release` never executes —
no GitHub Release, no wheel-build validation. The explicit edge on `release` makes the
gate auditable rather than relying on implicit propagation. Diff evidence:
`+needs: [lint, test, coverage]` (build), `+needs: [coverage]` (citation-check),
`-needs: [lint, test, build, citation-check]` / `+needs: [lint, test, build, citation-check, coverage]` (release).

### CI-06 S3 — README/README_ES mirror diff (rule 13)

- Headings mirror at column 0, same section position: `## Quality gates and security
  scanning` (README.md:750, ToC entry :36 after `Architecture summary`, before `Related`)
  ↔ `## Controles de calidad y escaneo de seguridad` (README_ES.md:789, ToC entry :38,
  before `Referencias`).
- Backtick technical tokens identical between the two section bodies (diff = empty):
  `pyproject.toml`, `[tool.coverage.report] fail_under = 90`, `ci.yml`, `release.yml`,
  `htmlcov`, `coverage-html`, `uv run coverage report -m`, `.github/workflows/codeql.yml`,
  `.github/codeql/config.yml`, `main`, `dev`.
- Only prose is translated; **no badge** added in either file (scanned).

---

## 5. CI-06 S1 local values — openspec/config.yaml (gitignored, working-tree evidence)

`.gitignore:56` covers `/openspec/config.yaml`; the file is untracked SDD state, absent
from CI checkouts. Test #13 skips when absent (D5 guard, correct under both readings);
**it ran here** because the file exists in the working tree, and the asserted values are:

```yaml
testing:
  coverage:
    available: true
    command: "uv run coverage run -m pytest"
rules:
  verify:
    - ...
    - coverage_threshold: 90      # rules.verify is a list; [last] entry
```

`testing.ci_test_command` (`"uv run pytest -v"`) and `testing.test_command`
(`"uv run pytest tests/ -q"`) are **unchanged** — PB-05 owns the CI test gate (CI-01's
anti-pattern guard). Pre-existing staleness not introduced by this change (noted in §8):
the `context:` block still claims "1029 tests", and `rules.verify` `build_command` predates
the `scripts/` addition.

---

## 6. Accepted deviations (parent-accepted at tasking / addendum)

1. **C.2 comment-wording deviation** — design D6 test #2 scans ci.yml + release.yml raw
   text for `fail_under` / `--fail-under` / `fail-under`, while design D2's comment boxes
   contained those substrings verbatim (guaranteed RED). Resolution: the coverage-job
   comment boxes were reworded to "the gate is config-declared and never flag-driven —
   coverage.py reads the floor itself, so no threshold literal or CLI flag belongs in
   this file", keeping the repo's `# ── ... ──` convention. Post-edit raw-text scan of
   both workflows: zero forbidden substrings; the floor value exists only in
   pyproject.toml. This is also what makes the CI-01 "config-only floor" contract pass.
2. **`_load_toml` importlib approach** — resolves the TOML parser via
   `importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")` instead
   of a static fallback import: same runtime behavior and intent as the
   `tests/test_cli.py` fallback, with no static `tomli` import for static analysis to fail
   on in a 3.11+ venv (tomli is a marker-only py<3.11 dependency).

Both deviate only in mechanism; the asserted contracts are unchanged.

---

## 7. Review workload / PR-boundary verification

- Forecast (design D9): ~365–390 lines; actual: tracked `+122 / −6 = 128` lines across 7
  files + new files `codeql.yml` 37 + `codeql/config.yml` 13 + `test_ci_workflows.py`
  350 = **≈ 528 total changed lines**. D9 undercounted the test module (rule-2 docstrings)
  and the workflow additions.
- The 400-line monitor FIRED at apply (V.5) → ask-on-risk handoff → **resolved by explicit
  user authorization of a size exception up to 1500 lines, single PR** (proposal +
  apply-progress amendments). No re-chaining was required; the ~528-line diff is inside
  the authorized budget. `size:exception` is explicitly recorded.
- **No scope creep**: zero `src/sofer/` changes (`git diff --name-only` and `git status`
  both empty for `src/sofer`); the only new module is the static-inspection test module;
  PB-05 (`uv run pytest -v` CI gate) untouched; no new dependencies (coverage.py and
  pyyaml already present). Suite count does not regress: baseline **1551 → 1567 passed**
  (+16 = the new module), 6 skipped (win32-conditional), matching the parent's input.

---

## 8. Risks and residuals

| Item | Severity | Status |
| ---- | -------- | ------ |
| Gate red at 90 until coverage-raising follow-up (88% today) | Expected by design | The armed forcing function; every PR/release below floor fails loudly at `coverage report -m` with missing lines in the log. No action needed from this change |
| `openspec/config.yaml` untracked → CI-06 S1 test can't assert in CI | Medium | Skip-if-absent guard (correct under both readings); tracked invariants (pyproject floor, workflows) carry CI weight; values recorded as working-tree evidence (§5) |
| Unchecked commit markers (P1, A.4, B.3, D.5, C.6, V.6) + parent gates G.1–G.3 | Archive blocker | Commit-deferred to parent by explicit "do not commit" constraint; G.2 (delivery) factually resolved by the user's size exception; G.1 (review) and G.3 (spec promotion of `openspec/specs/ci/spec.md`) are parent-owned |
| `.pi-lens.json` guard file left untracked in the tree | Cosmetic | Apply-phase incident artifact (pi-lens deferred-autofix corruption; disabled mutation controls); deletable at parent's discretion after commits |
| Stale `context:` ("1029 tests") and `rules.verify.build_command` in config.yaml | Pre-existing | Not introduced by this change; out of CI-06 scope (S1 pins only the three coverage facts) |
| README/README_ES drift | Low | Mirrored section landed in one working change; PR-template item pins future sync |
| CodeQL `languages` on `init` vs spec S3 wording | Low | Documented intent-level resolution (D3); test asserts init + analyze existence + write permission |
| `citation-check` now waits on lint/test/coverage | Very low | Intended gated-chain behavior; documented at apply |

---

## 9. Exact unchecked `- [ ]` task lines (archive blockers)

Implementation tasks A.1–A.3, B.1–B.2, D.1–D.4, E.1–E.2, C.1–C.5, V.1–V.5 are all `[x]`
(22 checked). The following remain unchecked — every one is a commit/ownership marker
deferred to the parent (constraint: do not commit) or a parent-owned lifecycle gate; none
is an incomplete implementation task:

```
L29 - [ ] Working tree is on `feat/ci-coverage-codeql`; the SDD artifacts (proposal, spec, design) are committed; tree is otherwise clean. <!-- sdd-owner: implementation -->
L39 - [ ] A.4 — Verify and commit A as one work unit ... <!-- sdd-owner: implementation -->
L47 - [ ] B.3 — Verify both files parse ... commit B as one work unit. <!-- sdd-owner: implementation -->
L57 - [ ] D.5 — Verify D ... commit D as one work unit. <!-- sdd-owner: implementation -->
L73 - [ ] C.6 — Commit C as one work unit. <!-- sdd-owner: implementation -->
L82 - [ ] V.6 — Write ... verify-report.md ... commit the SDD artifacts (tasks.md, verify-report.md) ... <!-- sdd-owner: implementation -->
L86 - [ ] G.1 — Bounded post-apply review ... <!-- sdd-owner: parent -->
L87 - [ ] G.2 — Lifecycle gate (delivery) ... <!-- sdd-owner: parent -->
L88 - [ ] G.3 — Lifecycle gate (spec promotion) ... <!-- sdd-owner: parent -->
```

**Verdict on archive**: verification is PASS, but **archive is NOT ready** — the work
units are un-committed (the whole `openspec/changes/2026-09-13-ci-coverage-codeql/`
directory and the 3 new implementation files are untracked), and G.1/G.3 remain for the
parent. Per the checkpoint contract: a partial slice with unchecked commit markers is
reported as remaining scope, never as a clean archive-pass. This report itself is the
V.6 deliverable; its commit belongs to the parent.

---

## 10. Environment incident (carried from apply, for the record)

During apply, a pi-lens deferred/LLM content pass rewrote coverage references 85→90 across
deliverables and the untracked SDD artifacts; all files were repaired to the then-current
85 contract and re-gated. An archived verify-report touched by the incident was reverted
(`git checkout -- openspec/changes/archive/2026-08-28-fix-quality-encoding-xlsx/verify-report.md`)
and confirmed clean in `git status`. `.pi-lens.json` (project mutation-controls disabled)
was left as a guard. The floor was subsequently lifted 85→90 by user directive and every
deliverable re-synced under the 90 contract; this verify phase confirms the 90 contract
holds end-to-end in the current working tree.