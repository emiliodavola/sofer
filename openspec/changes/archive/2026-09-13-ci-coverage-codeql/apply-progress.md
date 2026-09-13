# Apply Progress — CI coverage gate and CodeQL scanning (2026-09-13-ci-coverage-codeql)

Branch `feat/ci-coverage-codeql` (base `dev`) · Artifact store: openspec · Strict TDD: disabled
(`openspec/config.yaml` `strict_tdd: false`) — implementation-then-gates per parent confirmation.

## Structured status consumed

Native SDD status JSON reports `applyState: blocked` with "change selection ambiguous" (7 candidates);
superseded by explicit parent tasking of this change. `actionContext.mode: repo-local`,
`allowedEditRoots = [repo root]`, `warnings: []`. No edit-root conflict. Authority: parent prompt + session preflight.

## Work units (all implemented, gates green)

### Work unit A — coverage gate (pyproject.toml + ci.yml + release.yml)

- **A.1 [x]** — `[tool.coverage.report] fail_under = 90` added beside `show_missing = true`; tomllib parse
  yields `{'show_missing': True, 'fail_under': 90}`.
- **A.2 [x]** — ci.yml standalone `coverage` job appended after `test` (no `needs`); step order
  `coverage run -m pytest` → `coverage report -m` (gate, before html) → `coverage html` →
  `actions/upload-artifact@v4` (`name: coverage-html`, `path: htmlcov`); comment boxes per D2 with the
  C.2 wording deviation (below).
- **A.3 [x]** — release.yml `coverage` job between `test` and `build` with `needs: [lint, test]`; rewired:
  `build → [lint, test, coverage]`, `citation-check → [coverage]` (first explicit `needs`, now waits on
  lint/test/coverage — intended gated chain), `release → [lint, test, build, citation-check, coverage]`.
  Parsed edges equal the D2 table.
- **A.4 [ ]** — verify+commit: verification done (`git diff --stat` scope, `git diff --check` clean);
  **commit deferred to parent** (explicit constraint: do not commit).

### Work unit B — CodeQL workflow + config

- **B.1 [x]** — `.github/workflows/codeql.yml` per D3: push/PR `[main, dev]` + schedule `"0 3 * * 1"`;
  `permissions {actions: read, contents: read, security-events: write}`; no matrix, no concurrency,
  no upload-artifact; `init` with literal `languages: python` + `config-file: ./.github/codeql/config.yml`;
  `analyze@v3`.
- **B.2 [x]** — `.github/codeql/config.yml` per D4: quoted name, `paths-ignore: [docs/, .github/, openspec/,
  cache/, tmp/]`, no `queries:` key, `src/sofer/` absent.
- **B.3 [ ]** — verify+commit: both files parse, pins hold; **commit deferred to parent**.

### Work unit D — docs

- **D.1 [x]** — CONTRIBUTING dev-commands block gains both coverage commands (gate: 90%); Testing section
  replaces `- Target: no drop in coverage.` with the D8 gated-floor line (90%, spec-change requirement);
  GREP: `90%` + both commands present, `no drop in coverage` absent.
- **D.2 [x]** — README ToC entry + `## Quality gates and security scanning` section (D8 exact text) between
  `Architecture summary` and `Related`; no badge.
- **D.3 [x]** — README_ES mirrored ToC entry + `## Controles de calidad y escaneo de seguridad` section in the
  same position; prose translated, technical content English (rule 13); same working change as D.2.
- **D.4 [x]** — PR template checklist gains the coverage item after `New behaviour covered by tests`.
- **D.5 [ ]** — verify (grep anchors ✓) + **commit deferred to parent**.

### Work unit E — openspec/config.yaml (gitignored, NOT committed)

- **E.1 [x]** — D5 edits: `testing.coverage.available: false→true`, `command: null → "uv run coverage run -m pytest"`,
  `rules.verify.coverage_threshold: 0→85`; `testing.ci_test_command` and `testing.test_command` unchanged
  (PB-05 guard). yaml parse confirms all three values.
- **E.2 [x]** — `.gitignore:56` covers `/openspec/config.yaml`; never `git add`ed.

### Work unit C — tests/test_ci_workflows.py (16 inventory functions = 15 scenario tests + 1 supporting)

- **C.1 [x]** — module docstring, typed helpers `_REPO_ROOT/_read_text/_load_yaml/_load_toml/_as_list/
  _workflow/_triggers/_workflow_names/_coverage_jobs/_openspec_config` (+`_find_step`) with Args/Returns
  docstrings; `_triggers` owns the YAML 1.1 `on:`→`True` normalization once; `_load_toml` mirrors
  test_cli.py's fallback (inverted so stdlib `tomllib` is tried first — `tomli` is a py<3.11 marker dep);
  `_openspec_config` → `pytest.skip` when `openspec/config.yaml` absent (D5 trackedness guard).
- **C.2 [x]** — tests #0–7 (presence; CI-01 S1–S3; CI-02 S1–S3; CI-03 S1) incl. the C.2 resolution.
- **C.3 [x]** — tests #8–12 (CI-04 S1–S3, CI-05 S1–S2): trigger sets, dev-included PR, exact permission set,
  init `languages: python` + config ref, `analyze@v3` exists (D3 spec-wording resolution).
- **C.4 [x]** — tests #13–15 (CI-06 S1/S2/S4): config skip-if-absent, CONTRIBUTING floor + commands +
  placeholder gone, PR template item + README_ES sync item.
- **C.5 [x]** — `uv run pytest tests/test_ci_workflows.py -q` → 16 passed (test #13 RUNS because E is done);
  `uv run pytest tests/ -q` → 1567 passed, 6 skipped; `uv run ruff check src/ tests/ scripts/` clean;
  `uv run mypy src/ scripts/` clean.
- **C.6 [ ]** — **commit deferred to parent**.

### Phase V — verify evidence (apply-owned)

- **V.1 [x]** — positive leg: `uv run coverage run -m pytest` → rc 0 (1567 passed, 6 skipped);
  `uv run coverage report -m` → rc 0, **TOTAL 88%** ≥ 85 (3pt headroom), per-file missing lines listed.
- **V.2 [x]** — negative leg: `uv run coverage report -m --fail-under=100` → **rc 2**
  ("Coverage failure: total of 88 is less than fail-under=100"). Probe-only; never a workflow value
  (test #2 enforces).
- **V.3 [x]** — needs-DAG: `coverage → [lint, test]`; `build ⊇ coverage`; `citation-check = [coverage]`;
  `release ⊇ coverage`. GitHub skip-on-failed-need (transitive) → failed coverage skips build/citation-check/
  release; `action-gh-release` never runs below the floor.
- **V.4 [x]** — mirror: `## Quality gates and security scanning` (en) / `## Controles de calidad y escaneo
  de seguridad` (es) both at column 0 in ToC+section; technical content English in both; no badge added.
- **V.5 [x]** — full gates green (table below); `git diff --check` clean; **400-line monitor FIRED → STOP
  per constraint 8 (see Budget).**
- **V.6 [ ]** — verify-report.md written by this apply (captures V.1–V.5, E.1 values, C.2 choice, count
  reconciliation); **commit of SDD artifacts deferred to parent**.

## C.2 wording deviation (parent-accepted at tasking)

D6 inventory test #2 scans the RAW TEXT of ci.yml + release.yml for `fail_under` / `--fail-under` /
`fail-under`; D2's comment box contained both substrings verbatim, so verbatim implementation of D2+D6 is
guaranteed RED. Parent-accepted resolution: reword the comment boxes so the raw-text scan and the comments
do not collide, keeping the repo's `# ── ... ──` convention. Exact adopted wording (identical in ci.yml and
release.yml):

```yaml
# ── Complete-suite coverage gate (CI-01 + PB-05) ─────────────────────
# `uv run coverage run -m pytest` re-executes the FULL suite under
# instrumentation — never a focused subset. The 90% floor is declared
# once in pyproject.toml under [tool.coverage.report]; the gate is
# config-declared and never flag-driven — coverage.py reads the floor
# itself, so no threshold literal or CLI flag belongs in this file.
...
# The gate: coverage.py enforces the config-declared floor and exits
# non-zero below it. `-m` puts per-file missed lines in the job log.
```

Post-edit raw-text scan of both workflows: zero hits for `fail_under`, `--fail-under`, `fail-under`
(and zero for `coverage xml`/`codecov`/`coveralls`/`badge`).

## Test-count reconciliation (16 vs "15")

D6's inventory table lists **16 functions** (rows 0–15): test #0 `test_ci_workflow_files_present` is the
"supporting" presence guard; the remaining **15** map 1:1 to the spec Test Mapping's pytest-assertable
scenarios (CI-03 S2 "no release below floor" and CI-06 S3 "README mirrors README_ES" are verify-phase
evidence, not pytest tests). Prose counts of "15 tests / 15 passed" in the tasks are the scenario count;
the module ships all 16 inventory rows verbatim (C.2 explicitly scopes "Tests #0–7 (presence, …)").
Module run: **16 passed**. Full suite grew from 1551→1567 passing (this module's +16); suite never shrinks.

## Gates — exact outputs

| Gate | Command | Result | rc |
| ---- | ------- | ------ | -- |
| G1 | `uv run pytest tests/ -q` | `1567 passed, 6 skipped, 13 warnings in 44.13s` | 0 |
| G2 | `uv run pytest tests/test_ci_workflows.py -v` | 16 passed (all names `*_85`/`*_available_at_85`) | 0 |
| G3 | `uv run ruff check src/ tests/ scripts/` | `All checks passed!` | 0 |
| G4 | `uv run mypy src/ scripts/` | `Success: no issues found in 33 source files` | 0 |
| V1 | `uv run coverage run -m pytest` | `1567 passed, 6 skipped, 13 warnings` (under instrumentation) | 0 |
| V1 | `uv run coverage report -m` | `TOTAL 5995 638 2318 280 88%` (missing lines listed) | 0 |
| V2 | `uv run coverage report -m --fail-under=100` | `Coverage failure: total of 88 is less than fail-under=100` | 2 |
| V5 | `git diff --check` | clean (0 trailing-whitespace hits) | 0 |

Baseline note: the tasks.md precondition numbers (`1151 collected / 1149 passed / 2 skipped`, from
AGENTS.md) are stale — the suite on this branch measures `1551 passed, 6 skipped` before this change
(1567 − 16 new) and `1567 passed, 6 skipped` after; skip count 6 reflects win32-conditional skips.

## Files changed

Modified (7): `pyproject.toml` (+1), `.github/workflows/ci.yml` (+39),
`.github/workflows/release.yml` (+44/−3), `CONTRIBUTING.md` (+9/−3), `README.md` (+14), `README_ES.md`
(+14), `.github/PULL_REQUEST_TEMPLATE.md` (+1).
New (3): `.github/workflows/codeql.yml` (37), `.github/codeql/config.yml` (13),
`tests/test_ci_workflows.py` (347).
Local-only (gitignored): `openspec/config.yaml` (E.1 values, not committed).
Guard file (untracked, deletable): `.pi-lens.json` (project mutation-controls disabled — see incident).

## Line budget — 400-line monitor FIRED (ask-on-risk)

- Tracked diff: `+122 / −6` = **128 changed lines** (numstat above).
- New files: 37 + 13 + 347 = **397**.
- **Total ≈ 525 changed lines > 400 attempt budget** → per constraint 8: STOP, check off completed tasks,
  and report the count; the parent will ask the user. D9's forecast (~390, C≈250) undercounted the test
  module (actual 347: 16 functions with mandatory module/helper docstrings, AGENTS.md rule 2) and A
  (workflows 39+44 vs 33+37 estimated). No silent size acceptance: delivery shape (single PR with size
  exception, or chained PRs PR1=A+B(~138) / PR2=D+C(~388)) is the parent/user decision (G.2).

## Environment incident — pi-lens deferred autofix corruption (recorded per "no silent work")

During apply, a pi-lens deferred/LLM content pass repeatedly rewrote coverage references **85→90** across
the working tree: README.md, README_ES.md, CONTRIBUTING.md, PULL_REQUEST_TEMPLATE.md, pyproject.toml,
both workflow comment boxes, the test module (assertions, function names, docstrings), and the untracked
SDD change artifacts (proposal/design/spec/tasks). It also touched an archived verify-report (reverted:
`git checkout -- openspec/changes/archive/2026-08-28-fix-quality-encoding-xlsx/verify-report.md`).
Mitigation: repaired every file to the 85 contract, re-ran the full gate battery after repair, left
`.pi-lens.json` (project mutation-controls `format/autofix/actionableWarnings.autoFix` = disabled) as a
guard; final audit shows zero `90%`/`fail_under = 90` in deliverables (repo-compliance spec line 1475's
"90% (branch coverage)" is pre-existing, unrelated). **Parent: delete `.pi-lens.json` after committing if
not wanted; re-audit `grep -rn "90"` before committing.**

## Remaining tasks (exact unchecked `- [ ]` lines — commits only)

- `- [ ] P1 — Working tree is on feat/ci-coverage-codeql; the SDD artifacts (proposal, spec, design) are committed; tree is otherwise clean.` (artifacts untracked — parent-owned commit)
- `- [ ] A.4 — Verify and commit A as one work unit` (verify done; commit deferred)
- `- [ ] B.3 — … commit B as one work unit` (verify done; commit deferred)
- `- [ ] D.5 — Verify D … commit D as one work unit` (verify done; commit deferred)
- `- [ ] C.6 — Commit C as one work unit` (commit deferred)
- `- [ ] V.6 — Write … verify-report.md … commit the SDD artifacts (tasks.md, verify-report.md)` (report written here; commit deferred)
- G.1 / G.2 / G.3 — parent-owned markers, untouched (G.2 must resolve the 400-line crossing).

## Delivery handoff

Implementation complete and green. Budget monitor fired (525 > 400) → **parent/user decision required**
(ask-on-risk): single PR with size exception, or chained PRs (PR 1 = A+B ~138 lines, PR 2 = D+C ~388
lines). `openspec/config.yaml` is working-tree SDD state (gitignored) — evidence recorded in
verify-report.md, not committed.
## Addendum (2026-09-13): floor lift 85 → 90 (user directive)

Post-apply, the user directed `fail_under = 90`. Decision: gate armed at 90 as a
forcing function — red until per-file coverage ≥ 90 (follow-up change). All value
references lifted 85 → 90 across `pyproject.toml`, ci.yml/release.yml comments,
the test module (function names + assertions), CONTRIBUTING, README, README_ES,
the PR template, `openspec/config.yaml`, and the SDD artifacts (spec CI-01/CI-06,
proposal DP1, design contracts).

Re-gated after the lift:

| Gate | Result | rc |
| ---- | ------ | -- |
| `uv run ruff check tests/test_ci_workflows.py` (+full `src/ tests/ scripts/`) | All checks passed! | 0 |
| `uv run pytest tests/test_ci_workflows.py -q` | 16 passed | 0 |
| `uv run pytest tests/ -q` | 1567 passed, 6 skipped | 0 |
| V1 `uv run coverage report -m` (floor 90) | `Coverage failure: total of 88 is less than fail-under=90` | 2 |
| V1b probe `--fail-under=88` | total 88 ≥ 88 | 0 |
| V2 probe `--fail-under=100` | `Coverage failure: total of 88 is less than fail-under=100` | 2 |

`_load_toml` switched to `importlib.import_module` (+`sys.version_info`) — same
runtime behavior, removes the static `tomli` import that static analysis cannot
resolve in the local 3.11 venv (tomli is a marker-only py<3.11 dependency).

Budget: user authorized a size exception up to 1500 lines (single PR); the
~525-line diff is within it.
