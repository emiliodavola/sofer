# Proposal: CI coverage gate and CodeQL scanning

## Intent

sofer has no automated coverage or security-scanning presence in CI: `ci.yml`
runs lint + the full test suite, `release.yml` mirrors the gates, and neither
measures coverage; the repo has no CodeQL workflow, and the GitHub API confirms
code scanning is not enabled. The local baseline is 88% total coverage
(5995 stmts, 638 missed, 2318 partial) with the weakest files `cli.py` (84%),
`profile.py` (80%), `mcp_registration.py` (80%), and `publish.py` (87%).

This change makes three independent, non-blocking-to-merge guarantees:

1. **A coverage gate** — total coverage SHALL not drop below 90%, enforced by
   `pyproject.toml` (`[tool.coverage.report] fail_under = 90`, the value lives in
   config, never in a workflow), gating both PR CI and the release workflow.
   Coverage evidence is fully self-hosted: an `htmlcov` GitHub Actions artifact
   plus a missing-lines report in the job log. No Codecov, no badge, no XML
   upload.
2. **CodeQL scanning** — a versioned Advanced-Setup workflow in the repo
   (push + PR to `main`/`dev`, plus a weekly schedule) uploading SARIF results
   to the Security tab. Code scanning is deliberately enabled by the workflow,
   not by GitHub's Default Setup UI.
3. **Config + docs truth** — `openspec/config.yaml` flips
   `testing.coverage.available` to true with `coverage_threshold: 90`, and
   CONTRIBUTING / README / README_ES / PR template document the gate.

Scope and thresholds are user-confirmed (pre-proposal handoff); branch
protection and CodeQL alert-gating are explicitly out (solo dev).

## Scope

### In Scope

- `pyproject.toml`: add `fail_under = 90` to the existing
  `[tool.coverage.report]` (keeps `show_missing = true`); no `[tool.coverage.xml]`,
  no `[tool.coverage.html]` output settings. Values live in config — workflows
  read the gate from coverage.py, they do not hardcode it.
- `.github/workflows/ci.yml`: new `coverage` job (ubuntu-latest, Python 3.13)
  running `uv run coverage run -m pytest` → `coverage report -m` (the gate;
  missing lines go to the job log) → `coverage html` → upload `htmlcov` as an
  actions artifact. Existing lint/test jobs unchanged (PB-05 complete-suite gate
  stays `uv run pytest -v`).
- `.github/workflows/release.yml`: new `coverage` job (`needs: [lint, test]`);
  `build`, `citation-check`, and `release` SHALL NOT run unless the coverage job
  is green — a tag push below 90% produces no release.
- `.github/workflows/codeql.yml` (new, versioned in repo): Advanced Setup for
  `python`; triggers push `[main, dev]`, `pull_request [main, dev]`, and a
  weekly `schedule` cron; `permissions: security-events: write`; SARIF uploaded
  by the `analyze` action (default when the permission is granted).
- `.github/codeql/config.yml` (new): `paths-ignore` for non-code directories
  (e.g. `docs/`, `.github/`, `openspec/`), default queries.
- `openspec/config.yaml`: `testing.coverage.available: true`,
  `testing.coverage.command`, `rules.verify.coverage_threshold: 90`.
- `openspec/specs/ci/spec.md` (new `ci` spec domain — see Affected Specs).
- `CONTRIBUTING.md`: document the gate, add coverage commands to Development
  commands, refresh the vague "Target: no drop in coverage" line.
- `README.md` + `README_ES.md`: a short quality-gates/CI section (technical
  content in English in both files; mirrored headings per AGENTS.md rule 13).
- `.github/PULL_REQUEST_TEMPLATE.md`: Checklist gains a coverage-gate item
  (README_ES sync item already present).

### Out of Scope

- **Branch protection** on `main`/`dev` (user-rejected; solo dev).
- **CodeQL alert-protection merge gating** — alerts appear in the Security tab,
  nothing blocks merges on alert severity.
- **Codecov / any third-party coverage service**, coverage badges, and
  **XML upload** (Cobertura).
- **Raising per-file coverage** — the weakest files stay as they are; the change
  only pins the total floor. Per-region coverage work is a later change.
- **CodeQL Default Setup via the GitHub UI** (workflow-in-repo only).
- Coverage on the Windows matrix or across all five Python versions (one
  deterministic ubuntu/Python 3.13 run).
- `pytest-cov` plugin or any new dependency (coverage.py is already in
  `[dependency-groups] dev`).
- Alerts triage or SARIF upload for external tools.

## Capabilities

### New Capabilities

- **Coverage gate (total ≥ 90%)** enforced in CI and at release, with self-hosted
  evidence (htmlcov artifact + `coverage report -m` missing-lines log).
- **CodeQL Advanced Setup scanning** on push/PR to `main`+`dev` and weekly,
  SARIF in the Security tab after the workflow lands on the default branch.
- **`ci` spec domain** pinning the coverage/scanning contracts as
  Given/When/Then scenarios (rules.specs).

### Modified Capabilities

- `openspec/config.yaml` coverage availability flip (false → true, threshold
  0 → 90), making coverage part of declared SDD verify state.
- Documentation surface (CONTRIBUTING, README/README_ES, PR template) describing
  the gate and the scan cadence.
- `release.yml` gains an additional gate before publishing.

## Approach

- **Gate value in config**: `pyproject.toml` `[tool.coverage.report]` gains
  `fail_under = 90` next to the existing `show_missing = true`. coverage.py
  enforces the gate itself (`coverage report` exits non-zero below the floor) —
  workflows invoke `coverage report -m` and never hardcode a threshold, per
  rules.proposal "no hardcoded values".
- **Coverage job** (ci.yml + release.yml, identical shape):
  `actions/checkout@v4` → `astral-sh/setup-uv@v5` (Python 3.13) → `uv sync` →
  `uv run coverage run -m pytest` → `uv run coverage report -m` → `uv run
  coverage html` → `upload-artifact` (htmlcov). One OS × one Python keeps
  measurements deterministic; the job re-runs the complete suite under coverage
  (never a focused subset, consistent with PB-05's gate discipline).
- **Release gating**: the release workflow's `coverage` job sits between `test`
  and `build`; `build`/`release` gain it in their `needs`. A tag push below 90%
  fails before any release artifact/GitHub Release is produced; there is no
  publish-on-coverage-drift path.
- **CodeQL workflow**: standard Advanced-Setup layout (`init` with
  `config-file: ./.github/codeql/config.yml` → `analyze`), `languages: python`,
  triggers `push` + `pull_request` on `[main, dev]` and a weekly `schedule`
  cron (design phase picks the concrete time; e.g. `0 3 * * 1`). `analyze`
  uploads SARIF (requires `permissions: security-events: write`); no separate
  upload-sarif action is needed for CodeQL's own results.
- **paths-ignore**: `.github/codeql/config.yml` excludes non-code trees
  (docs, `.github`, `openspec/`, generated artifacts) so scan noise stays near
  zero on a Python-only repo.
- **openspec/config.yaml**: flip `testing.coverage.available` to true, set
  `command` to the coverage invocation, set `rules.verify.coverage_threshold`
  to 90 — the SDD verify phase then enforces the same floor the CI does.
- **Docs + template**: CONTRIBUTING Development commands gain
  `uv run coverage run -m pytest` / `uv run coverage report -m`; the Testing
  section replaces "no drop in coverage" with the concrete 90% floor. README and
  README_ES get a mirrored short section describing the gate and scanning
  cadence (technical content in English in both, rule 13). PR template Checklist
  gains a coverage item.

## Decision Points

| # | Decision | Recommendation | Tradeoff | Status |
| --- | ---------- | ---------------- | ---------- | -------- |
| 1 | Gate value | **90%** (`fail_under = 90` in config) | Floor set above the 88% baseline by explicit user directive (2026-09-13): gate is red until coverage ≥ 90 — a forcing function, not a false-red risk | **Changed** (user, 2026-09-13; size exception to 1500 lines) |
| 2 | Coverage evidence | **Self-hosted** GH artifact (htmlcov) + `coverage report -m` in log | No third-party data sharing or OAuth; zero-config hosting | **Locked** (handoff) |
| 3 | Codecov / badge / XML | **Rejected** | Avoids external service + badge surface; XML adds no consumer today | **Locked** (handoff) |
| 4 | CodeQL provisioning | **Advanced Setup via versioned workflow** | Versioned + reviewable + triggers controllable; UI Default Setup creates an opaque config | **Locked** (handoff) |
| 5 | Scan cadence | push/PR `[main, dev]` + weekly schedule | Weekly covers the dormant-branch case without paying per-commit cost on `dev` churn | **Locked** (handoff) |
| 6 | Coverage job placement | **Dedicated `coverage` job** (ubuntu, 3.13) in both workflows | One extra full-suite run (~1–2 min); the alternative (in-matrix) multiplies the gate across 10 matrix legs and complicates the artifact | Design-phase confirm |
| 7 | Spec domain | **New `ci` domain** (see Affected Specs) | `packaging` is distribution contract; `process-boundary` is boundary suites; CI infra is its own concern, PB-05 stays untouched | This proposal |
| 8 | Branch protection / alert gating | **Not applied** | Solo dev; CodeQL alerts are informational only | **Locked** (handoff) |

## Affected Areas

| Area | Impact | Description |
| ------ | -------- | ------------- |
| `.github/workflows/ci.yml` | Modified | New `coverage` job: gate (`coverage report -m`), htmlcov artifact upload; lint/test jobs untouched |
| `.github/workflows/release.yml` | Modified | New `coverage` job; `build`/`release` `needs` extended so releases stop below 90% |
| `.github/workflows/codeql.yml` | New | Advanced Setup; push/PR `[main, dev]` + weekly schedule; SARIF upload via `analyze` |
| `.github/codeql/config.yml` | New | `paths-ignore` for non-code trees; default queries |
| `pyproject.toml` | Modified | `[tool.coverage.report] fail_under = 90` (show_missing kept); no xml/html output keys |
| `openspec/config.yaml` | Modified | `testing.coverage.available: true`, `command` set, `rules.verify.coverage_threshold: 90` |
| `openspec/specs/ci/spec.md` | New | New domain: coverage gate, artifact/log evidence, release gating, CodeQL cadence + paths-ignore, config availability |
| `openspec/specs/process-boundary/spec.md` | None | PB-05 unchanged; `ci` spec cross-references it for the complete-suite gate |
| `openspec/specs/packaging/spec.md` | None | Untouched — release-gating scenarios live in `ci`, not the distribution contract |
| `CONTRIBUTING.md` | Modified | Coverage commands + 90% floor documented |
| `README.md`, `README_ES.md` | Modified | Mirrored quality-gates/CI section (rule 13); no new badge |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modified | Checklist gains coverage-gate item |
| `.gitignore` | None | Already covers `.coverage`, `.coverage.*`, `htmlcov/` |
| `src/sofer/*` | None | Zero production code changes |
| `tests/` | New | `tests/test_ci_workflows.py` (static inspection of workflow/config files) |

## Affected Specs

**Recommendation: new `ci` spec domain** (`openspec/specs/ci/spec.md`) rather
than extending `packaging` or `process-boundary`.

- `packaging`'s purpose is the distribution contract (build system, tags,
  metadata, installability, PKG-01..PKG-06). CI workflow gates are not
  distribution; shoehorning them in would dilute the domain's audit trail.
- `process-boundary` pins the test suite's boundary behavior; its PB-05
  (complete-run gate) is adjacent but behavioral — the `ci` spec SHALL
  cross-reference PB-05 for the invariant that the coverage run executes the
  complete suite, and PB-05 SHALL remain unchanged.

Planned requirements/scenarios for the new `ci` domain (RFC 2119 keywords,
Given/When/Then per rules.specs; every scenario maps to a test per rule 6):

| Req | Requirement | Scenarios | Maps to |
| ----- | ------------- | ----------- | --------- |
| CI-01 | Coverage gate SHALL live in `[tool.coverage.report] fail_under` (config, not workflow); incantations SHALL never hardcode a floor or pass `--fail-under=N` | 3 (config declares 90; gate is config-driven incl. local exit-code leg; report honors show_missing) | `tests/test_ci_workflows.py` (tomllib parse + YAML no-hardcoded-floor) + local `coverage report` exit code (CI-01 S2 runtime leg) |
| CI-02 | CI SHALL produce self-hosted evidence: `htmlcov` artifact + missing-lines list in the job log; SHALL NOT upload XML or reference Codecov/badges | 3 (artifact step present; `coverage report -m` in log; no xml/codecov in workflows) | `tests/test_ci_workflows.py` (YAML inspection) |
| CI-03 | Release SHALL be gated on the coverage job (`build`, `citation-check`, `release` `needs` include it); no release below 90% | 2 (coverage in release `needs`; tag push below floor yields no release) | `tests/test_ci_workflows.py` (needs wiring) + verify-phase static evidence (no-release below floor, PB-05/MSP-R12 precedent) |
| CI-04 | CodeQL SHALL scan python on push/PR to `main`+`dev` and on a weekly schedule, uploading SARIF (`security-events: write`) | 3 (three triggers present; pull_request includes dev; SARIF upload permission granted) | `tests/test_ci_workflows.py` (YAML inspection) |
| CI-05 | CodeQL config SHALL `paths-ignore` non-code trees; advanced setup, not UI Default Setup | 2 (config file referenced by init; paths-ignore covers non-code dirs) | `tests/test_ci_workflows.py` |
| CI-06 | `openspec/config.yaml` SHALL declare coverage available with `coverage_threshold: 90`; docs (CONTRIBUTING, README + README_ES §13, PR template) SHALL describe the gate | 4 (config flags true at 90; README mirrors README_ES; CONTRIBUTING documents floor; template checklist item) | config/CONTRIBUTING/template assertions in `tests/test_ci_workflows.py`; README/README_ES mirror verified statically at verify phase (PB-05/MSP-R12 precedent for doc scenarios) |

Doc-sync scenarios (CI-06 README/README_ES mirror) follow the repo precedent of
static diff evidence in the verify-report (as done for MSP-R12 and PB-05),
because translated-doc equivalence is not a pytest-assertable property.

## Impact and Risks

| Impact | Severity | Mitigation |
| -------- | ---------- | ------------ |
| Coverage job adds ~1–2 min per CI run (second full-suite pass on ubuntu/3.13) | Low | Bounded to one deterministic leg; artifact expires by default (90 days); value (gate + evidence) exceeds the cost |
| Future change drops below 90% and CI goes red | Low | 3pt headroom at the locked floor; `coverage report -m` pinpoints regions; lowering the floor silently is a spec change (CI-01), not an ad-hoc tweak; fixes raise coverage, never relax the floor without an explicit spec edit |
| Release tag fails because dev drifted below the floor | Very low | `ci.yml` coverage gate runs on every PR/merge to `main`+`dev`, so drift surfaces pre-tag; the failure is loud and fixable before re-tagging (AGENTS.md rule 12 re-tag path untouched) |
| CodeQL alert noise on a Python-only repo | Low | Default Python queries are low-volume; alerts are informational (no merge gating, decision point 8); `paths-ignore` excludes docs/openspec so findings stay code-relevant |
| CodeQL workflow licensing/permission misconfig (SARIF upload denied) | Low | `security-events: write` is the documented requirement for SARIF upload; verify phase checks the workflow parses and the permission is present |
| README/README_ES drift (rule 13) | Low | Mirrored section written in one commit; PR template checklist item already covers the sync; verify-phase static diff |
| Coverage measurement variance (branch coverage) vs local baseline | Low | Gate runs the same command (`coverage run -m pytest` + `report -m`) with the same `[tool.coverage.run]` config; only ubuntu/3.13 |

## Rollback Plan

- **Coverage gate**: remove `fail_under = 90` from `pyproject.toml` and delete
  the `coverage` job from both workflows — CI/release return to the current
  state in one commit; no data migration.
- **CodeQL**: delete `.github/workflows/codeql.yml` + `.github/codeql/` —
  scanning stops after the next run cycle; existing SARIF alerts remain
  viewable but no new results are produced (GitHub default behavior for a
  removed workflow).
- **Config + docs**: revert `openspec/config.yaml`, CONTRIBUTING, README(s),
  PR template — all plain-text edits, trivially revertible.
- No production code, no dataset behavior, no release artifacts are touched, so
  rollback of this change cannot affect shipped behavior.

## Non-Goals

- Branch protection or required status checks on `main`/`dev`.
- CodeQL alert-severity merge gating or any "scanning fails the PR" flow.
- Third-party coverage services (Codecov), coverage badges, or XML upload.
- Raising per-file coverage on `cli.py`/`profile.py`/`mcp_registration.py`/
  `publish.py` — the gate pins the total floor only.
- CodeQL Default Setup via the GitHub UI.
- Coverage instrumentation on Windows or across the full Python matrix.
- New dependencies (coverage.py and pyyaml already present; no pytest-cov).

## Success Criteria

1. `uv run coverage report -m` honors the config floor (90): exits 0 when measured ≥ 90 and non-zero below it. Amended by user directive (2026-09-13) from 85 → 90; measured 88% today, so the gate is red by design (forcing function) until the follow-up coverage-raising change lands; the positive exit-code leg is proven by the `--fail-under=88` probe (rc 0).
2. Fresh PR to `main`/`dev`: `coverage` job green; htmlcov artifact downloadable;
   missing-lines list present in the job log; no XML/Codecov references in either
   workflow.
3. `release.yml` `needs` wiring provably includes `coverage` such that a tag push
   below 90% produces no release (static inspection test + CI evidence).
4. `codeql.yml` parses with push/PR `[main, dev]` + weekly schedule; SARIF uploads
   after merge to the default branch (Security tab shows the analysis).
5. New `ci` spec: every scenario maps to a green test or verify-phase static
   evidence; the full suite count does not regress; `uv run pytest tests/ -q`,
   ruff, and mypy all pass.
6. README.md and README_ES.md mirror the new section (rule 13); CONTRIBUTING and
   the PR template reflect the gate.

## Amendment (2026-09-13): floor 85 → 90 (user directive)

- The coverage floor was changed from 85 to 90 by explicit user directive
  ("quiero que fail_under sea 90") after this proposal was drafted. Scope and
  decisions unchanged: config-owned gate, self-hosted evidence, CodeQL Advanced
  Setup, no branch protection, single PR.
- Consequence accepted by the user: the gate is armed at 90 while the measured
  baseline is 88% — CI is red by design until a follow-up change raises
  per-file coverage (cli.py 84%, profile.py 80%, mcp_registration.py 80%,
  publish.py 87%). The red gate is the forcing function for that work.
- Delivery: user authorized a size exception up to 1500 changed lines.
- Verify evidence (floor 90): `uv run coverage report -m` rc 2 at 88% < 90 (V1,
  red by design); positive-leg probe `--fail-under=88` rc 0 (V1b); negative-leg
  probe `--fail-under=100` rc 2 (V2).
