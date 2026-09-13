# Design: CI coverage gate and CodeQL scanning

## Technical Approach

Three independent, non-blocking-to-merge guarantees, per the proposal:

1. **Coverage gate at 90%** — the floor lives in `pyproject.toml`
   `[tool.coverage.report] fail_under = 90` (config, never a workflow literal).
   coverage.py enforces the gate itself: the `coverage` job in `ci.yml` and
   `release.yml` runs the complete suite under instrumentation
   (`uv run coverage run -m pytest`), reports with `-m` (missing lines → log),
   and uploads `htmlcov` as a self-hosted artifact. No Codecov, no XML, no badge.
2. **CodeQL Advanced Setup** — a versioned `.github/workflows/codeql.yml`
   (push + PR to `main`/`dev` + weekly schedule) with an explicit
   `.github/codeql/config.yml` (`paths-ignore` for non-code trees). SARIF lands
   in the Security tab via the `analyze` step (`permissions: security-events: write`).
3. **Config + docs truth** — `openspec/config.yaml` flips coverage to available
   at threshold 90; CONTRIBUTING, README/README_ES (mirrored, rule 13), and the
   PR template document the gate.

No production code changes: `src/sofer/` is untouched. The only new module is
`tests/test_ci_workflows.py`, a static-inspection suite that pins every
pytest-assertable scenario of the new `ci` spec (CI-01..CI-06).

## Architecture Decisions

| # | Decision | Options | Tradeoffs | Choice |
| --- | ---------- | --------- | ----------- | -------- |
| D1 | Weekly CodeQL cron | `0 3 * * 1` vs `0 0 * * 1` vs `0 2 * * 3` | Midnight is the GitHub-suggested default but can coincide with nightly maintenance; mid-week loses the post-weekend baseline; 03:00 UTC Monday is off-peak in EU/US and catches weekend drift early | **`0 3 * * 1`** — Monday 03:00 UTC |
| D2 | `coverage` job shape & wiring | In-matrix vs dedicated job; ci.yml `needs` vs standalone | 10 matrix legs × coverage multiplies runtime and fragments the artifact; a dedicated ubuntu/3.13 leg matches the lint-job pattern and yields one deterministic measurement + one artifact | **Dedicated job**, identical shape in both workflows; ci.yml **standalone** (no needs, mirrors `lint`/`test` parallelism); release.yml `needs: [lint, test]` |
| D3 | CodeQL job layout | Matrix (`strategy.matrix.language`) vs literal `languages: python`; concurrency block vs none | Matrix indirection makes the static tests assert template syntax instead of the contract, and the spec pins `languages: python` literally; trigger sets are non-overlapping by construction (push only on `main`/`dev`), and cancel-in-progress could drop a SARIF upload | **No matrix, literal `languages: python`**, no `concurrency` block |
| D4 | CodeQL permissions | Only `security-events: write` vs explicit full set | Declaring *any* `permissions:` block resets all unlisted scopes to `none` — `contents: read` then becomes *required* for checkout, and `actions: read` is GitHub's documented minimum for CodeQL | **`actions: read`, `contents: read`, `security-events: write`** |
| D5 | `paths-ignore` scope | Add every gitignored dir vs only real non-code trees | `dist/`, `htmlcov/`, `__pycache__/`, `.venv/` are gitignored and never present in the checked-out tree the workflow analyzes (no build step) — listing them is dead config; `docs/`, `.github/`, `openspec/`, `cache/`, `tmp/` are the live non-code trees | **docs/, .github/, openspec/, cache/, tmp/** — never `src/sofer/` |
| D6 | `openspec/config.yaml` | Flip `available` only vs also set `command` + `rules.verify.coverage_threshold` | CI-06 pins all three declared facts; the SDD verify phase must enforce the same floor CI does | **`available: true`, `command: "uv run coverage run -m pytest"`, `rules.verify.coverage_threshold: 90`**; `ci_test_command` stays `"uv run pytest -v"` (PB-05 owns the CI test gate) |
| D7 | CI-01 negative-leg proof | Edit pyproject temporarily vs probe flag vs rcfile | Editing the tracked pyproject in the working tree risks accidental commit; a throwaway `--rcfile` with `fail_under = 99` proves the *config key* drives the exit code but adds a temp file; `--fail-under=100` is a one-flag probe, guaranteed above the 88% baseline, cheap (re-reads existing `.coverage`), and scoped to the verify report — workflows never pass flags (CI-01) | **Verify probe: `uv run coverage report -m --fail-under=100` → non-zero** (documented as evidence, never a workflow value) |
| D8 | Docs surface | New README section placement, CONTRIBUTING floor line, PR-template item | ToC lists every `##` section in both READMEs → the new section must be added there too; the dataset-quality section name `Validación y controles de calidad` is already taken by the tool's *dataset* checks, so the new section must not collide | **`## Quality gates and security scanning` / `## Controles de calidad y escaneo de seguridad`** before `Related`/`Referencias`, ToC entry added to both; one CONTRIBUTING replacement line; one checklist item |
| D9 | Delivery shape | Single PR vs chained | Estimated ~365 changed lines < 400 canonical threshold (and far below the 1500 review budget) → no chain trigger | **Single PR**, 4 commits, no ask-on-risk pause |

---

## Decision 1 — Weekly CodeQL cron value

**Chosen: `"0 3 * * 1"`** (every Monday at 03:00 UTC).

Rationale:

- **Cadence is locked** (proposal decision 5): weekly covers the dormant-branch
  case without paying per-commit scan cost on `dev` churn.
- **03:00 UTC is off-peak** in both EU and US timezones — low runner contention
  and no overlap with business-hours push/PR CI. GitHub Actions schedules run in
  UTC, so the value is timezone-deterministic regardless of the maintainer's host.
- **Monday** lands the scan on the baseline accumulated over the weekend and
  surfaces findings at the start of the work week — chosen over GitHub's
  suggested `0 0 * * 1` to avoid the midnight maintenance window, and over a
  mid-week day because Monday's catching-the-weekend baseline is the more useful
  signal.
- GitHub schedules can dispatch a few minutes late; irrelevant for a security scan.

No `concurrency` block is added (see D3): the trigger sets never overlap for the
same commit — `push` fires only on `main`/`dev` (feature branches trigger only
`pull_request`), so there is no duplicate-scan pressure to dedupe.

## Decision 2 — `coverage` job (final YAML)

**Shared job shape** (identical in `ci.yml` and `release.yml`; only the `needs`
wiring differs):

```yaml
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: uv sync

      # ── Complete-suite coverage gate (CI-01 + PB-05) ─────────────────────
      # `coverage run -m pytest` re-executes the FULL suite under
      # instrumentation — never a focused subset. The 90% floor lives in
      # pyproject.toml [tool.coverage.report] fail_under; it is never
      # hardcoded here and no --fail-under flag may be added.
      - name: Run tests under coverage
        run: uv run coverage run -m pytest

      # The gate: coverage.py reads fail_under from config and exits non-zero
      # below the floor. `-m` puts per-file missed lines in the job log.
      - name: Report coverage with missing lines (the gate)
        run: uv run coverage report -m

      - name: Generate HTML coverage report
        run: uv run coverage html

      # Self-hosted evidence (CI-02): htmlcov artifact, no third-party service.
      # retention-days deliberately omitted — GitHub's 90-day default is
      # platform policy, not a value this repo should hardcode.
      - name: Upload htmlcov artifact
        uses: actions/upload-artifact@v4
        with:
          name: coverage-html
          path: htmlcov
```

**Placement in `ci.yml`**: after the existing `test` job, as a standalone job —
**no `needs`** (runs in parallel with `lint`/`test`, mirroring the existing
parallel `lint`/`test` layout). The coverage signal stays available even if
another leg fails.

**Placement in `release.yml`**: between `test` and `build`, with
`needs: [lint, test]`. The `needs` wiring changes:

| Job | Current `needs` | New `needs` |
| ----- | ----------------- | ------------- |
| `coverage` | — (new) | `[lint, test]` |
| `build` | `[lint, test]` | `[lint, test, coverage]` |
| `citation-check` | *(none — ran parallel)* | `[coverage]` |
| `release` | `[lint, test, build, citation-check]` | `[lint, test, build, citation-check, coverage]` |

Notes:

- `citation-check` gains an explicit `needs` for the first time; because its need
  (`coverage`) itself needs `[lint, test]`, a lint/test failure now also skips
  `citation-check` (previously it ran unconditionally). This is the intended
  gated-chain behavior — document it in the commit message.
- GitHub `needs` are direct-only and skip propagation through a failed need is
  transitive; the explicit edge on `release` makes the gate auditable rather than
  relying on implicit propagation.
- **Gate ordering**: the report step (`coverage report -m`) runs *before* `coverage
  html`. A tag push below the floor fails fast at the gate; `html`/upload skip,
  and the missing-lines list in the log is already the required evidence.
- Action versions mirror the repo's existing pins: `actions/checkout@v4`,
  `astral-sh/setup-uv@v5`. `actions/upload-artifact@v4` is added only here —
  **not** in `codeql.yml` (the CodeQL `analyze` step uploads its own SARIF; see
  D3).
- `coverage` is a `[dependency-groups] dev` member already present in the lockfile;
  no new dependency (proposal out-of-scope).
- One OS × one Python (ubuntu-latest, 3.13): keeps the measurement comparable to
  the local baseline (proposal reports 88% locally) and deterministic.

## Decision 3 — `codeql.yml` (final YAML)

```yaml
name: CodeQL

# Advanced Setup, versioned in the repo (CI-04): enabled by this workflow —
# never by GitHub's Default Setup UI. The weekly cron keeps dormant-branch
# coverage; the Monday 03:00 UTC slot is off-peak.
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
  schedule:
    - cron: "0 3 * * 1"

# Declaring any permissions block resets the rest to `none`, so `contents: read`
# is REQUIRED for checkout, `actions: read` is GitHub's documented minimum for
# CodeQL, and `security-events: write` lets the analyze step upload SARIF.
permissions:
  actions: read
  contents: read
  security-events: write

jobs:
  analyze:
    name: Analyze Python
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: python
          config-file: ./.github/codeql/config.yml

      # Uploads SARIF to the Security tab by default because
      # permissions.security-events = write. No separate upload-sarif step.
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
```

Decisions embedded in this listing:

- **No `strategy.matrix`**: `languages: python` is a literal on `init` (canonical
  Advanced Setup for a single-language repo), so the static tests assert the
  contract directly instead of template syntax (`${{ matrix.language }}`).
- **No `concurrency` block** (rejected option): triggers never overlap per commit
  (push limited to `main`/`dev`; PRs from feature branches), and
  `cancel-in-progress` could suppress a SARIF upload on the very ref that matters.
  GitHub's own Advanced Setup template omits it.
- **Actions**: `github/codeql-action@v3` for both `init` and `analyze` (same
  major pin so their internals interoperate). `actions/upload-artifact@v4` is
  used **only** in the `coverage` job — the `analyze` step uploads CodeQL's own
  results; adding an artifact step here would be a copy-paste error.
- **Spec-precision note (CI-04 S3 wording)**: the spec's SARIF scenario says "the
  `analyze` step SHALL declare `languages: python`". In canonical CodeQL v3,
  `languages` is an `init` parameter — `analyze` consumes the initialized
  database. The design resolves the tension at the intent level: `init` declares
  `languages: python` (satisfying CI-05 S1 verbatim), `permissions.security-events
  == write`, and an `analyze` step exists; the CI-04 S3 test asserts exactly those
  three facts. `languages` is *not* duplicated onto `analyze` (it would be an
  ignored parameter).
- **Name/job-id convention**: job id `analyze` with display name
  `Analyze Python` (matches GitHub's official template surface).
  `timeout-minutes` is omitted — a small single-language scan on a small repo
  does not justify a new magic number the proposal/spec never requested.

## Decision 4 — `.github/codeql/config.yml` (final listing)

```yaml
# CodeQL Advanced-Setup config (CI-05). Default Python queries — no `queries:`
# block, so the scan stays low-volume on a Python-only repo and remains the
# GitHub default suite.
#
# paths-ignore covers non-code trees and gitignored generated artifacts.
# src/sofer/ (the code tree) SHALL remain scanned — never add it here.
name: "sofer CodeQL config"

paths-ignore:
  - docs/
  - .github/
  - openspec/
  - cache/
  - tmp/
```

Notes:

- `name:` is quoted per YAML 1.1 hygiene (defensive; PyYAML would otherwise
  coerce nothing here, but quoting matches the repo's quoted-scalar convention).
- **No `queries:` key** — the spec pins "default queries"; adding
  `security-and-quality` would change the suite and raise alert volume, directly
  contradicting the proposal's risk mitigation ("default Python queries are
  low-volume").
- `docs/`, `.github/`, `openspec/` are the required spec entries (CI-05 S2
  verbatim); `cache/` and `tmp/` are the "generated artifacts" spec clause —
  both are gitignored and may exist in a developer checkout. `dist/`,
  `htmlcov/`, `.venv/`, `__pycache__/` are deliberately **not** listed: they are
  gitignored and cannot exist in the checked-out tree the workflow analyzes
  (the workflow has no build/install step), so listing them is dead config.
- `tests/` stays scanned (tests are code; the spec only excludes non-code trees).

## Decision 5 — `openspec/config.yaml` edits

Exact edits (the file is SDD-local state — see the trackedness note below):

| Key | Before | After |
| ----- | -------- | ------- |
| `testing.coverage.available` | `false` | `true` |
| `testing.coverage.command` | `null` | `"uv run coverage run -m pytest"` |
| `rules.verify.coverage_threshold` | `0` | `90` |
| `testing.ci_test_command` | `"uv run pytest -v"` | **unchanged** |
| `testing.test_command` | `"uv run pytest tests/ -q"` | **unchanged** |

The exact `testing.coverage.command` string is:

```yaml
testing:
  coverage:
    available: true
    command: "uv run coverage run -m pytest"
```

**Why `ci_test_command` stays unchanged**: PB-05 (process-boundary) pins the CI
test gate as the complete suite via `uv run pytest -v`, and `ci_test_command`
describes that gate. The coverage job runs the *same* complete suite under
instrumentation (`coverage run -m pytest`); it does not replace the test gate.
Mutating `ci_test_command` would silently alter the process-boundary contract
without a spec change — the exact anti-pattern CI-01 exists to prevent.

**Trackedness note (critical implementation fact)**: `.gitignore` carries
`/openspec/config.yaml` and `/openspec/init.json` under the deliberate header
"SDD generated artifacts (regenerated by sdd-init)" — i.e., config.yaml is
likely **untracked and absent from CI checkouts**. CI-06 S1's test must
therefore **skip when the file is absent** (`pytest.skip` + docstring), which is
correct under *both* readings: if the file is tracked, the assertion runs; if it
is not, CI skips and the locally-executed SDD verify phase records the asserted
values as working-tree evidence. The tracked invariants that *do* run everywhere
(pyproject `fail_under = 90`, workflow shapes) carry the gate's CI-executable
weight. Flag this to the parent for confirmation but do not block on it — the
guard is safe either way.

## Decision 6 — `tests/test_ci_workflows.py` design

### File-level layout

```
tests/test_ci_workflows.py
```

- Module-level docstring (AGENTS.md rule 2): purpose — static inspection of the
  CI/CodeQL/config/doc surface for the `ci` spec (CI-01..CI-06); every pytest
  function maps 1:1 to a spec scenario (rule 6).
- **Helpers stay module-local** (rule 4): they are used only by this module, so a
  `conftest.py` hoist is not warranted — extract only if a second consumer
  appears. All helpers carry type annotations (PB-07: "new test helpers SHALL be
  type-annotated even though mypy excludes `tests/`") and param/return docstrings.

### Constants and helpers

```python
_REPO_ROOT = Path(__file__).resolve().parents[1]  # tests/ -> repo root

def _read_text(rel: str) -> str                # utf-8 read; fails loudly on missing file
def _load_yaml(rel: str) -> dict[str, Any]     # yaml.safe_load wrapper
def _load_toml(rel: str) -> dict[str, Any]     # tomllib w/ tomli fallback (py3.10),
                                               # mirroring tests/test_cli.py's pattern
def _as_list(value: Any) -> list[Any]          # normalize `needs` (str | list | None)
def _workflow(rel: str) -> tuple[dict[str, Any], str]
                                               # (parsed YAML, raw text) for a workflow
def _triggers(wf: dict[str, Any]) -> dict[str, Any]
                                               # resolve the `on` key
def _workflow_names() -> tuple[str, ...]       # sorted .github/workflows/*.yml names
def _coverage_jobs() -> list[dict[str, Any]]   # `coverage` job dicts from ci + release
def _openspec_config() -> dict[str, Any]       # parse openspec/config.yaml; pytest.skip
                                               # if absent (gitignored — see D5 note)
```

**PyYAML `on:` gotcha (must be encoded in `_triggers`)**: YAML 1.1 treats the
top-level `on` key as boolean `True`, so `yaml.safe_load` yields
`{True: {...}}` — `wf.get("on", wf.get(True))`. This is the single most common
implementation mistake for workflow tests; the helper owns it in exactly one
place.

`_as_list` is needed because GitHub `needs` may be a single string or a list and
`citation-check` currently has none.

### Test function inventory (15 static tests, 1:1 with the spec Test Mapping)

| # | Function | Scenario | Core assertion |
| --- | ---------- | ---------- | ---------------- |
| 0 | `test_ci_workflow_files_present` | supporting | `.github/workflows/*.yml` ⊇ `{ci.yml, release.yml, codeql.yml}` (fail loudly before any parse) |
| 1 | `test_pyproject_declares_coverage_fail_under_90` | CI-01 S1 | `_load_toml("pyproject.toml")["tool"]["coverage"]["report"]["fail_under"] == 90` |
| 2 | `test_coverage_gate_is_config_driven_without_cli_floor` | CI-01 S2 | raw text of ci.yml + release.yml contains no `--fail-under`, `fail_under`, or `fail-under`; each `coverage` job's report-step `run` is exactly `"uv run coverage report -m"` |
| 3 | `test_coverage_report_honors_show_missing` | CI-01 S3 | `[tool.coverage.report].show_missing is True` **and** the report step invokes `-m` (missing lines → log) |
| 4 | `test_coverage_jobs_generate_and_upload_htmlcov` | CI-02 S1 | each `coverage` job has a step running `"uv run coverage html"` and an `actions/upload-artifact@v4` step with `path: htmlcov`, `name: coverage-html` |
| 5 | `test_coverage_report_step_lists_missing_lines` | CI-02 S2 | report step `run == "uv run coverage report -m"` in both workflows |
| 6 | `test_no_xml_codecov_or_badge_references_in_workflows` | CI-02 S3 | case-insensitive full-text scan of ci.yml + release.yml for `coverage xml`, `codecov`, `coveralls`, `badge` → zero matches |
| 7 | `test_release_is_gated_on_the_coverage_job` | CI-03 S1 | release.yml: `coverage` job exists; `coverage.needs == [lint, test]`; `build.needs ⊇ {coverage}`; `citation-check.needs == [coverage]`; `release.needs ⊇ {coverage}` |
| 8 | `test_codeql_has_push_pr_and_weekly_triggers` | CI-04 S1 | `_triggers` resolves; `push.branches == [main, dev]`; `pull_request.branches == [main, dev]`; one `schedule` cron matching `^\d+ \d+ \* \* \d+$` |
| 9 | `test_codeql_pull_request_targets_dev` | CI-04 S2 | `pull_request.branches` set-equals `{main, dev}` |
| 10 | `test_codeql_security_write_permission_and_python` | CI-04 S3 | `permissions == {actions: read, contents: read, security-events: write}`; `init` step declares `languages: python`; an `analyze` step on `github/codeql-action/analyze@v3` exists (spec-wording resolution per D3) |
| 11 | `test_codeql_init_references_config_file` | CI-05 S1 | `init` step: `config-file == "./.github/codeql/config.yml"` and `languages == "python"` |
| 12 | `test_codeql_paths_ignore_covers_non_code_trees` | CI-05 S2 | parse `.github/codeql/config.yml`: `paths-ignore ⊇ {docs/, .github/, openspec/}` and `src/sofer/` not listed |
| 13 | `test_openspec_config_declares_coverage_available_at_90` | CI-06 S1 | `_openspec_config()`: `testing.coverage.available is True`; `testing.coverage.command == "uv run coverage run -m pytest"`; `rules.verify.coverage_threshold == 90` (skips when file absent — D5 note) |
| 14 | `test_contributing_documents_coverage_floor` | CI-06 S2 | CONTRIBUTING.md contains `90%` + both coverage commands; `"no drop in coverage"` absent |
| 15 | `test_pr_template_has_coverage_checklist_item` | CI-06 S4 | PULL_REQUEST_TEMPLATE.md Checklist contains a `coverage` item **and** the existing README_ES sync item |

### Verify-phase evidence (not pytest-assertable — PB-05/MSP-R12 precedent)

| Scenario | Evidence recorded in the verify report |
|----------|----------------------------------------|
| CI-03 S2 (no release below floor) | needs-DAG proof: `coverage → {build, citation-check, release}` edges; GitHub's documented skip-on-failed-need semantics mean a failed `coverage` skips every dependent job and `action-gh-release` never runs |
| CI-06 S3 (README mirrors README_ES) | section-heading equality diff + English-technical-content spot check (rule 13) |

## Decision 7 — CI-01 negative-leg proof (verify phase)

The gate's positive leg is any CI run: `uv run coverage report -m` exits 0
when measured ≥ 90 (floor amended to 90 by user directive — measured 88%
today, so V1 is red by design and the positive exit-code leg is proven with the
`--fail-under=88` probe). The negative leg — *does the gate actually fail below
the floor?* — is proven at verify phase with a cheap, deterministic probe:

```bash
# V1 — gate run (regenerates .coverage, complete suite, PB-05); RC 2 at 88% < 90
uv run coverage run -m pytest
uv run coverage report -m          # expect rc == 2 below the 90 floor (red by design)

# V1b — positive-leg probe (re-reads the existing .coverage; no re-run)
uv run coverage report -m --fail-under=88   # expect rc == 0

# V2 — negative leg (re-reads the existing .coverage; no re-run)
uv run coverage report -m --fail-under=100   # expect rc != 0
```

Why this is the right probe:

- `--fail-under=100` is guaranteed above the current measurement (88%), so the
  negative leg is deterministic without touching tracked files.
- It reuses the `.coverage` data file generated by V1 — no second test near-run.
- coverage.py's documented behavior: `coverage report` exits with status **2**
  when the measured total is below `fail_under`; the probe's non-zero exit
  exercises exactly that enforcement path.
- **Scope discipline**: the `--fail-under=N` flag is a verify-report evidence
  probe only — it never appears in a shipped workflow (CI-01 forbids it there;
  the static test #2 enforces that). The floor itself is read by the probe from
  config in V1 (no flag), proving the config-driven path.
- Optional stronger variant (record in the verify report if used): a throwaway
  `--rcfile` with `fail_under = 99` re-proves the *config key* drives the exit
  code; V2 above is the primary, single-flag form.

Cleanup: `.coverage`/`.coverage.*`/`htmlcov/` are gitignored (verified), so the
verify run never dirties the tree.

## Decision 8 — Docs (exact wording)

### README.md — new section (after `## Architecture summary`, before `## Related`)

ToC addition (after `Architecture summary`, before `Related`):
`- [Quality gates and security scanning](#quality-gates90%d-security-scanning)`

```markdown
## Quality gates and security scanning

- **Coverage gate**: total test coverage is gated at **90%** — the floor lives
  in `pyproject.toml` (`[tool.coverage.report] fail_under = 90`) and is enforced
  by coverage.py on every PR (`ci.yml`) and before every release
  (`release.yml`). Evidence is self-hosted: an `htmlcov` artifact
  (`coverage-html`) plus a missing-lines report in the job log
  (`uv run coverage report -m`). No third-party coverage service is used.
- **CodeQL scanning**: the Python codebase is scanned on every push and pull
  request to `main`/`dev`, and weekly (`.github/workflows/codeql.yml`,
  Advanced Setup with `.github/codeql/config.yml`). SARIF results appear in the
  **Security** tab; alerts are informational and never block merges.
```

### README_ES.md — mirrored section (same position; prose translated, technical content English — rule 13)

ToC addition: `- [Controles de calidad y escaneo de seguridad](#cont90%es-de-calidad-y-escaneo-de-seguridad)`

```markdown
## Controles de calidad y escaneo de seguridad

- **Coverage gate**: la cobertura total de tests está limitada al **90%** — el
  valor mínimo vive en `pyproject.toml` (`[tool.coverage.report] fail_under = 90`)
  y lo aplica coverage.py en cada PR (`ci.yml`) y antes de cada release
  (`release.yml`). La evidencia es autogestionada: un artefacto `htmlcov`
  (`coverage-html`) además de un informe de líneas no cubiertas en el log del job
  (`uv run coverage report -m`). No se usa ningún servicio de cobertura externo.
- **CodeQL scanning**: el código Python se analiza en cada push y pull request a
  `main`/`dev`, y semanalmente (`.github/workflows/codeql.yml`, Advanced Setup
  con `.github/codeql/config.yml`). Los resultados SARIF aparecen en la pestaña
  **Security**; las alertas son informativas y nunca bloquean merges.
```

The section name deliberately avoids clashing with the tool's dataset-level
`Validación y controles de calidad` section (which covers sofer's *data* checks,
not the repo's CI).

### CONTRIBUTING.md90%
90%
Development commands block gains (technical, English):

```bash
uv run coverage run -m pytest   # complete suite under coverage (gate: 90%)
uv run coverage report -m       # totals + per-file missed lines; fails below 90%
```
90%
Testing section — replacement line (removes the "Target: no drop in coverage."
placeholder):

```markdown
- Total coverage is gated at **90%** (`fail_under = 90` in `pyproject.toml`):
  CI and the release workflow fail below the floor, and `uv run coverage report
  -m` lists the missed lines. Raising the floor is a spec change
  (`openspec/specs/ci/spec.md` CI-01), never an ad-hoc workflow tweak.
```

### `.github/PULL_REQUEST_TEMPLATE.md`90%

Checklist gains (after "New behaviour covered by tests", before the README items):

```markdown
- [ ] Coverage gate met — `uv run coverage report -m` ≥ 90% (CI enforces `fail_under = 90`)
```

## Decision 9 — Task / commit / PR plan

**Confirmed: nothing in `src/sofer/` changes.** Every edit is a workflow,
config, docs, or new test file; the only Python file is
`tests/test_ci_workflows.py`. No CLI surface change → no `_cmd_*` orchestration
update, no `cli.py` help-text or Command-reference rewrite.
90%
### Commits (work units, each green at its boundary)

| Commit | Files | Unit |
| -------- | ------- | ------ |
| `ci: gate CI and release on 90% total coverage` | `pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml` | The enforcement machinery + release gating |
| `ci: add CodeQL advanced-setup workflow and config` | `.github/workflows/codeql.yml`, `.github/codeql/config.yml` | Scanning cadence + paths-ignore |
| `test(ci): pin coverage and CodeQL workflow contracts (CI-01..CI-06)` | `tests/test_ci_workflows.py` | The spec scenarios (rule 6). Deliberately separate: it asserts *both* workflow commits and the docs edits, so it can only land green after them |
| `docs: document the coverage gate and weekly CodeQL scan` | `CONTRIBUTING.md`, `README.md`, `README_ES.md`, `.github/PULL_REQUEST_TEMPLATE.md` | Rule-13 mirror written in the same commit (README + README_ES), per AGENTS.md rule 13 |

`openspec/config.yaml` is gitignored SDD state (D5 note) — its edit is recorded
in the verify report, not committed. The SDD artifacts themselves
(`openspec/changes/2026-09-13-ci-coverage-codeql/{proposal,spec,design,tasks,verify-report}.md`)
are committed.

### Review budget

~365 changed lines total (≈103 workflow/config YAML, ≈250 test module, ≈12 docs
and template) — under the 400 canonical threshold and far under the 1500 budget.
**No chain trigger; single PR.** Delivery strategy stays `ask-on-risk` with no
pause required (no size:exception, no ambiguous scope, nothing destructive or
publishing beyond workflows that only take effect after merge).

## Data Flow / Orchestration

```
PR / push to main|dev ──┬─> lint (ruff + mypy) ──┐
                        ├─> test (matrix 10 legs)─┤
                        └─> coverage ──> report -m (gate: fail_under=90 from pyproject)
                             │  ok                │  fail ──> ❌ PR red; missing lines in log
                             ▼                    ▼
                        htmlcov ──> upload-artifact coverage-html

tag push v* ──┬─> lint ──┐
              ├─> test ──┤
              └─> coverage (needs lint,test) ──> report -m (gate)
                     │ ok                                       │ fail
                     ▼                                          ▼
              build ─┐                                build / citation-check /
              citation-check ─┐                       release SKIPPED → no Release
              release ────────┘
              (needs lint,test,coverage,build,citation-check)

push|PR|weekly ──> codeql.yml analyze: init(config-file, languages: python)
                  → analyze → SARIF → Security tab (informational)
```

## Interfaces / Contracts

| Contract | Exact value |
| ---------- | ------------- |
| Coverage floor | `fail_under = 90` in `pyproject.toml [tool.coverage.report]` (single source of truth) |
| Gate invocation | `uv run coverage report -m` — no flags in any workflow |
| `testing.coverage.command` | `"uv run coverage run -m pytest"` |
| Artifact | `name: coverage-html`, `path: htmlcov`, default retention (90d) |
| Cron | `"0 3 * * 1"` (quoted string) |
| CodeQL act90%s | `github/codeql-action/{init,analyze}@v3`; upload-artifact is NOT used by codeql.yml |
| Config ref | `config-file: ./.github/codeql/config.yml`, `languages: python` on `init` |
| `paths-ignore` | `docs/`, `.github/`, `openspec/`, `cache/`, `tmp/` — never `src/sofer/` |

**No-hardcoded-values compliance** (AGENTS.md rule 1): the one tunable policy
value — the 90% floor — lives in config and is read by coverage.py; workflows
carry zero threshold literals (test #2 enforces). The remaining literals in the
new YAML are *interface identifiers* (job ids `coverage`/`analyze`, artifact name,
cron, trigger branches, action versions), the same class of literal the existing
workflows already carry (`tags: ["v*"]`, `branches: [main, dev]`,
`setup-uv@v5`, etc.). `retention-days` is deliberately omitted rather than
hardcoded.

**Docstrings / documentation note** (rule 2): the new test module gets a
module-level docstring; every helper carries Args/Returns docstrings (conftest
style); every new workflow block carries a `# ── ... ──` purpose comment
matching the repo's comment-box convention; the section headings above are the
exact mirror anchors for both READMEs.

## Testing Strategy

| Layer | What | Where |
| ------- | ------ | ------- |
| Static (15 tests) | Workflow YAML parse + config/doc checks | `tests/test_ci_workflows.py` (inventory in Decision 6) |
| Runtime | Local gate exit codes | Verify phase V1/V2 (Decision 7) |
| Static evidence | no-release DAG + README mirror | Verify report (Decision 6 mapping) |
| Gates | `uv run pytest tests/ -q`, `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/ scripts/` | Rule 5; CI mypy runs on 3.13 only |

No existing test changes: PB-05 (complete-run gate), the 1149 passing tests, and
the two existing skips are untouched; the suite grows, never shrinks. `pyyaml`
(a runtime dependency) and `tomli`/`tomllib` are already in the dev environment —
no new dependency.

## Risks

| Risk | Severity | Mitigation |
| ------ | ---------- | ----------- |
| `openspec/config.yaml` untracked → CI-06 S1 test can't run in CI | Medium | Skip-if-absent guard (correct under both tracked/untracked readings, D5); tracked invariants carry CI weight; verify phase asserts the values locally |
| PyYAML `on:` → `True` key confuses trigger parsing | Medium | `_triggers` helper owns the normalization in one place (Decision 6) |
| Below-floor tag push blocks release | Low | Coverage gate runs on every PR to `main`/`dev`; drift surfaces pre-tag; AGENTS.md rule 12 re-tag path untouched |
| CodeQL SARIF upload denied by permission mistake | Low | Explicit full `permissions` block (D3); verify check parses the workflow |
| README/README_ES drift (rule 13) | Low | Mirrored section lands in one commit; PR-template item already pins the sync; verify-phase diff |
| `languages` on `init` vs spec wording ("analyze SHALL declare") | Low | Documented resolution at intent level (D3); test asserts init + analyze existence + permission |
| citation-check now waits on lint/test/coverage | Very low | Intended gated chain; documented in the commit message |

## Rollback Plan

- Coverage gate: remove `fail_under = 90` + both `coverage` jobs → CI/release
  return to current state in one commit.
- CodeQL: delete `codeql.yml` + `.github/codeql/` → scanning stops next cycle;
  existing SARIF alerts remain viewable (GitHub default).
- Config + docs: revert the plain-text edits.
- No production code or release artifacts touched (D9), so rollback cannot affect
  shipped behavior.

## Success Criteria — design check

1. `uv run coverage report -m` honors the config floor (90): rc 2 at measured 88% (red by design, forcing function); positive-leg probe `--fail-under=88` rc 0; the
   `--fail-under=100` probe exits non-zero (V2, Decision 7).
2. Fresh PR: `coverage` job green on ci.yml; artifact `coverage-html`
   downloadable; missing lines in log; tests 2/6 enforce no floor/XML/Codecov
   literals in either workflow.
3. release.yml `needs` wiring = Decision 2 table; test #7 pins it.
4. codeql.yml parses with push/PR `[main, dev]` + weekly cron (tests 8/9); SARIF
   appears after landing on `main` (post-merge CI observation).
5. 15 new tests green + the full suite count does not regress; ruff + mypy pass.
6. README/README_ES mirror (rule 13) via verify-phase heading diff; CONTRIBUTING
   and the PR template reflect the gate.

## Amendment (2026-09-13): floor 85 → 90 (user directive)

- All `fail_under` / `coverage_threshold` contract values amended 85 → 90; the
  gate remains config-owned (CI-01 shape unchanged).
- Today's 88% baseline is below the 90 floor, so the gate is red until the
  coverage-raising follow-up lands; the positive exit-code leg is proven by the
  `--fail-under=88` verify probe (V1b), never a workflow flag.
- Test module: `_load_toml` resolves the parser via
  `importlib.import_module` conditioned on `sys.version_info` (tomllib on
  3.11+, marker-only tomli on 3.10) instead of a static fallback import — same
  intent as the `tests/test_cli.py` fallback, with no static `tomli` import for
  static analysis to fail on in a 3.11 venv.
- Delivery: user-authorized size exception to 1500 lines (single PR).
