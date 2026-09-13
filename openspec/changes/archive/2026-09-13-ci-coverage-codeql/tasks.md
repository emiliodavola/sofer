# Tasks — CI coverage gate and CodeQL scanning (2026-09-13-ci-coverage-codeql)

Branch: `feat/ci-coverage-codeql` (base `dev`) · Artifact store: openspec · Strict TDD: disabled (config.yaml `strict_tdd: false`) — the C-phase test module is written GREEN-last by construction (it asserts A+B+D+E content), so no RED phase is authored.

Execution order: **A → B → D → E → C → V → G**. Phases C (tests) and V (verify) must land only after A+B+D+E — tests #13–15 assert docs and config content, so C is green at its commit boundary only when the earlier phases are in place.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | **~390** committed code/docs/config lines (validated; D9 estimated ~365): A ≈ 70 (pyproject +1, ci.yml ≈ 33, release.yml ≈ 37), B ≈ 39 (codeql.yml ≈ 29, config ≈ 10), D ≈ 29 (CONTRIBUTING ≈ +7/−1, README ≈ +11, README_ES ≈ +11, PR template +1), C ≈ 250 (test module, per D6). Plus ~110 SDD artifacts committed with the PR (tasks.md ≈ 70, verify-report.md ≈ 40). `openspec/config.yaml` (E) is gitignored — not in the diff |
| 400-line budget risk | **Medium** — the committed code diff sits at the threshold (±10 lines); the swing factor is the C test module (240–280). Not "likely >400", so no pre-apply chain trigger per D9 |
| Chained PRs recommended | **No** (pre-apply, per D9) — but the four work units are PR-ready slices; see Suggested split for the monitor-and-promote fallback |
| Suggested split | Single PR, 4 work-unit commits: A → B → D → C (E local-only, V evidence appended). Chained fallback if the apply diff crosses 400 at any commit boundary: PR 1 = A+B (~110), PR 2 = D+C (~280) |
| Delivery strategy | `ask-on-risk` — pause and ask only if the committed diff crosses 400 lines at a work-unit boundary; otherwise single PR, no pause |
| Chain strategy | `pending` — deferred until chaining is selected (session preflight); D9 chose single PR, confirmed as long as the diff stays ≤ 400 |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium
```

Monitor condition (encoded for V.5/G.2): if the running diff crosses 400 changed lines at any commit boundary, STOP and ask (ask-on-risk — never silently chain, never accept a size:exception).

## Preconditions

- [ ] Working tree is on `feat/ci-coverage-codeql`; the SDD artifacts (proposal, spec, design) are committed; tree is otherwise clean. <!-- sdd-owner: implementation -->
- [x] Baseline recorded: `uv run pytest tests/ -q` → 1151 collected, 1149 passed, 2 skipped (AGENTS.md numbers; config.yaml context's "1029" is stale). <!-- sdd-owner: implementation -->

## Phase A — Work unit A: coverage gate (pyproject.toml + ci.yml + release.yml)

Commit at end of phase: `ci: gate CI and release on 90% total coverage` — include the D2 note that `citation-check` gains its first explicit `needs` and now waits on lint/test/coverage (intended gated-chain behavior).

- [x] A.1 — `pyproject.toml` `[tool.coverage.report]`: add `fail_under = 90` next to the existing `show_missing = true`. Do NOT add `[tool.coverage.xml]` or `[tool.coverage.html]` keys. Verify: `tomllib` parse of the file shows both `fail_under == 90` and `show_missing is True`. <!-- sdd-owner: implementation -->
- [x] A.2 — `.github/workflows/ci.yml`: add the `coverage` job **after** the existing `test` job, verbatim from design.md Decision 2 (standalone job — **no `needs`**, mirrors lint/test parallelism; step order: `uv run coverage run -m pytest` → `uv run coverage report -m` (the gate, runs BEFORE html) → `uv run coverage html` → `actions/upload-artifact@v4` with `name: coverage-html`, `path: htmlcov`; no `retention-days`). Comment boxes per the D2 listing so the purpose comments survive to the final file. Verify: YAML parses; job id `coverage` present; report-step `run` is exactly `uv run coverage report -m`. <!-- sdd-owner: implementation -->
- [x] A.3 — `.github/workflows/release.yml`: add the identical `coverage` job between `test` and `build`, with `needs: [lint, test]`; then rewire `needs` exactly per D2's table: `build` → `[lint, test, coverage]`, `citation-check` → `[coverage]`, `release` → `[lint, test, build, citation-check, coverage]`. Verify: parsed `needs` edges equal the D2 table. <!-- sdd-owner: implementation -->
- [ ] A.4 — Verify and commit A as one work unit: `git diff --stat` = `pyproject.toml` + `.github/workflows/ci.yml` + `.github/workflows/release.yml` only; `git diff --check` clean; commit message covers the citation-check gating change (G.2 will re-read the story). <!-- sdd-owner: implementation -->

## Phase B — Work unit B: CodeQL workflow + config

Commit at end of phase: `ci: add CodeQL advanced-setup workflow and config`

- [x] B.1 — Create `.github/workflows/codeql.yml` verbatim from design.md Decision 3: triggers `push`/`pull_request` on `[main, dev]` + `schedule` cron `"0 3 * * 1"`; `permissions: {actions: read, contents: read, security-events: write}`; `jobs.analyze` → `init` with literal `languages: python` and `config-file: ./.github/codeql/config.yml`, then `analyze@v3`. Deliberately absent: `strategy.matrix`, `concurrency` block, `upload-artifact` step (D3). Verify: YAML parses; the three triggers, the permission set, and the `init` params match the Interfaces contract. <!-- sdd-owner: implementation -->
- [x] B.2 — Create `.github/codeql/config.yml` verbatim from design.md Decision 4: quoted `name: "sofer CodeQL config"`; `paths-ignore: [docs/, .github/, openspec/, cache/, tmp/]`; **no `queries:` key**; `src/sofer/` SHALL NOT be listed. Verify: parsed list ⊇ {docs/, .github/, openspec/} and excludes `src/sofer/`. <!-- sdd-owner: implementation -->
- [ ] B.3 — Verify both files parse (`yaml.safe_load` on each) and the interface pins hold (cron string, config-file ref, action pins `@v3`); commit B as one work unit. <!-- sdd-owner: implementation -->

## Phase D — Work unit D: docs (CONTRIBUTING + README + README_ES + PR template)

Commit at end of phase: `docs: document the coverage gate and weekly CodeQL scan` — README + README_ES land in the SAME commit (AGENTS.md rule 13).

- [x] D.1 — `CONTRIBUTING.md`: Development commands block gains the two coverage commands from D8 (`uv run coverage run -m pytest` and `uv run coverage report -m`, technical English); Testing section replaces the entire `- Target: no drop in coverage.` line with the D8 gated-floor line mentioning `fail_under = 90`, the verify-report wording, and the spec-change requirement. Verify: file contains `90%` and both commands; `no drop in coverage` is absent. <!-- sdd-owner: implementation -->
- [x] D.2 — `README.md`: add ToC entry `- [Quality gates and security scanning](#quality-gates-and-security-scanning)` between `Architecture summary` and `Related`; add the `## Quality gates and security scanning` section (D8 exact text) after `## Architecture summary`, before `## Related`. No badge added. <!-- sdd-owner: implementation -->
- [x] D.3 — `README_ES.md`: mirrored ToC entry (`Controles de calidad y escaneo de seguridad`) + mirrored section in the same position, prose translated per D8, technical content (commands, YAML keys, filenames, URLs) stays English in both files. Verify: heading mirrors README; no badge added. Same commit as D.2. <!-- sdd-owner: implementation -->
- [x] D.4 — `.github/PULL_REQUEST_TEMPLATE.md`: Checklist gains the D8 coverage item after `New behaviour covered by tests`, before the README items. Verify: checklist contains the coverage item AND the existing README_ES sync item. <!-- sdd-owner: implementation -->
- [ ] D.5 — Verify D (grep the four files for the D8 anchors), commit D as one work unit. <!-- sdd-owner: implementation -->

## Phase E — Work unit E: openspec/config.yaml (local edit, gitignored, NOT committed)

- [x] E.1 — Edit `openspec/config.yaml` per D5's exact edit table: `testing.coverage.available: false → true`; `testing.coverage.command: null → "uv run coverage run -m pytest"`; `rules.verify.coverage_threshold: 0 → 85`. `testing.ci_test_command` and `testing.test_command` SHALL stay unchanged (PB-05 owns the CI test gate — CI-01's anti-pattern guard). Verify: `yaml.safe_load` shows all three values. <!-- sdd-owner: implementation -->
- [x] E.2 — Confirm `.gitignore` covers `/openspec/config.yaml` (already present); do NOT `git add` it; the edit is working-tree SDD state recorded as evidence in the verify report (V.6). <!-- sdd-owner: implementation -->

## Phase C — Work unit C: tests/test_ci_workflows.py (15 static tests, CI-01..CI-06)

Commit at end of phase: `test(ci): pin coverage and CodeQL workflow contracts (CI-01..CI-06)` — lands last among A/B/D/E so it is green at its boundary.

- [x] C.1 — Create `tests/test_ci_workflows.py` skeleton per D6: module-level docstring (purpose: static inspection of the CI/CodeQL/config/doc surface for the `ci` spec; 1:1 scenario mapping, rule 6); helpers `_REPO_ROOT`, `_read_text`, `_load_yaml`, `_load_toml` (mirror the `tomli`/`tomllib` fallback at `tests/test_cli.py:117`), `_as_list`, `_workflow`, `_triggers` (**must** normalize the PyYAML 1.1 `on:` → boolean `True` key — `wf.get("on", wf.get(True))`), `_workflow_names`, `_coverage_jobs`, `_openspec_config` (skips with `pytest.skip` + docstring when `openspec/config.yaml` is absent — D5 trackedness guard, correct under both tracked/untracked readings). All helpers type-annotated (PB-07) with Args/Returns docstrings (rule 2). <!-- sdd-owner: implementation -->
- [x] C.2 — Tests #0–7 (presence, CI-01 S1–S3, CI-02 S1–S3, CI-03 S1) per the D6 inventory table. **Design conflict to resolve at apply** (D6 test #2 scans ci.yml+release.yml raw text for `fail_under`/`--fail-under`/`fail-under`, but D2's comment box contains both substrings verbatim — verbatim implementation of both is guaranteed RED): implement test #2 to enforce the CI-01 S2 intent — no `--fail-under=N` flag and no numeric floor literal in any workflow step invocation — and adjust the A.2/A.3 comment wording so the raw-text scan and the comments do not collide; record the exact wording deviation and rationale in the verify report (V.6) for parent review at G.2. <!-- sdd-owner: implementation -->
- [x] C.3 — Tests #8–12 (CI-04 S1–S3, CI-05 S1–S2) per D6: trigged sets, dev-included PR, exact permission set `{actions: read, contents: read, security-events: write}`, `init` declares `languages: python` + config ref, an `analyze@v3` step exists (spec-wording resolution per D3 — `languages` is NOT duplicated onto `analyze`). <!-- sdd-owner: implementation -->
- [x] C.4 — Tests #13–15 (CI-06 S1/S2/S4) per D6: config availability (skip-if-absent), CONTRIBUTING floor + commands + placeholder gone, PR template checklist coverage + README_ES items. <!-- sdd-owner: implementation -->
- [x] C.5 — Verify: `uv run pytest tests/test_ci_workflows.py -q` → 15 passed (test #13 RUNS, not skipped, because E is done); `uv run pytest tests/ -q` → 1151 collected, 2 skipped, count not regressed; `uv run ruff check src/ tests/ scripts/` and `uv run mypy src/ scripts/` clean. <!-- sdd-owner: implementation -->
- [ ] C.6 — Commit C as one work unit. <!-- sdd-owner: implementation -->

## Phase V — Verify evidence (apply-owned; recorded in the verify report)

- [x] V.1 — Gate positive leg (CI-01 S2 runtime): `uv run coverage run -m pytest` (complete suite, PB-05) then `uv run coverage report -m` → exit 0, per-file missing lines listed. `.coverage`/`htmlcov` are gitignored (confirmed) — tree stays clean. <!-- sdd-owner: implementation -->
- [x] V.2 — Gate negative leg (D7 probe): `uv run coverage report -m --fail-under=100` → non-zero exit (documented coverage.py enforcement; probe never appears in a shipped workflow — test #2 enforces that). <!-- sdd-owner: implementation -->
- [x] V.3 — needs-DAG proof (CI-03 S2 static evidence): extract release.yml `needs` edges and record `coverage → {build, citation-check, release}` plus GitHub's skip-on-failed-need semantics (`action-gh-release` never runs below the floor). <!-- sdd-owner: implementation -->
- [x] V.4 — README/README_ES mirror diff (CI-06 S3 static evidence): section-heading equality + English-technical-content spot check (rule 13). <!-- sdd-owner: implementation -->
- [x] V.5 — Full gates: `uv run pytest tests/ -q` (count check), `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/ scripts/`, `git diff --check` (PB-07). If the running diff crossed 400 lines at any commit boundary, STOP and hand to G.2 (ask-on-risk) instead of proceeding. <!-- sdd-owner: implementation -->
- [ ] V.6 — Write `openspec/changes/2026-09-13-ci-coverage-codeql/verify-report.md` capturing V.1–V.5, the E.1 values (config.yaml trackedness note per D5), and the C.2 conflict-resolution choice; commit the SDD artifacts (tasks.md, verify-report.md) with the apply work. <!-- sdd-owner: implementation -->

## Phase G — Post-apply review and lifecycle gates (parent-owned)

- [ ] G.1 — Bounded post-apply review: read the 4-commit story (A → B → D → C) against D9's work-unit table — boundaries, conventional commit messages, the citation-check gating note, tests-with-code/docs-with-feature units (work-unit-commits skill). <!-- sdd-owner: parent -->
- [ ] G.2 — Lifecycle gate (delivery): confirm single-PR delivery per D9 with no ask-on-risk pause triggered (V.5 monitor); if the diff crossed 400, decide with the user between chained PRs (PR 1 = A+B → PR 2 = D+C) before any PR is opened. <!-- sdd-owner: parent -->
- [ ] G.3 — Lifecycle gate (spec promotion): decide placement of the new `openspec/specs/ci/spec.md` domain file — the proposal lists it In Scope/Affected, the D9 commit list does not — and create it from the change-boundary spec at the chosen point (feature PR vs archive), per repo precedent (e.g. process-boundary "Modified by" notes are added at archive). <!-- sdd-owner: parent -->
