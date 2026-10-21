# Agent Instructions — sofer

## Workflow: Organic Driven Development (ODD)

ODD is the workflow for new work. It has four moves:

1. **Authorization.** Analysis, review, and planning requests are read-only. Implement only when the
   user explicitly asks for implementation.
2. **Proportionate exploration.** Verify the request against the code and docs before writing;
   explore only as deep as the decision requires.
3. **Implementation.** Make the smallest coherent change. Small changes go directly; a dossier is
   not required merely because work touches several files.
4. **Verification.** Run the applicable gates and report actual results, including failures,
   skips, and unavailable checks.

The issue and PR are the default record for scope, decisions, verification, and delivery. Create a
durable task document (for example under `odd/tasks/`) only when essential decisions, dependencies,
or unfinished work cannot live in the issue/PR and would otherwise be lost across sessions. State
that continuity need before creating the document. Do not duplicate issue/PR content by routine.

SDD is not required for new ODD work: no new proposal, design, change folder, or archive report is
needed. OpenSpec remains the record of existing contracts — the specs, `## Test Mapping` tables, the
registry, the archives, and `scripts/check_test_mapping.py` stay in force and unchanged in scope.
When an authorized change alters an existing OpenSpec contract, update that contract in place; do not
require parallel ODD and SDD dossiers, and do not extend mapping requirements automatically to every
ODD task. Historical OpenSpec records are never rewritten.

Keep the full-suite cadence from rule 6: `uv run pytest tests/ -q` after every change batch. Focused
tests may support iteration; they never replace the full suite.

### GitHub assignment

Every issue or pull request an agent creates SHALL be assigned to the authenticated GitHub user
(`gh api user --jq .login`, or `--assignee @me`) unless the user says otherwise. Assign at creation
time. If the assignment fails, do not block delivery: record the failed assignment and its reason in
the report.

## Code Quality Standards

### 1. No hardcoded values
- **Never** inline magic numbers or default strings in function bodies.
- Tool-wide defaults belong in `pyproject.toml` under `[tool.sofer]`, loaded via `src/sofer/config.py`.
- Dataset-level config belongs in the per-dataset TOML file, loaded via `DatasetConfig`.
- Before writing a numeric literal or default string, ask: "Should this be configurable?"

Examples of what to extract:
- Default delimiters, encodings, sample sizes
- Report truncation limits (`[:10]`, `[:5]`)
- Thresholds for type inference, quality checks
- Output directory names, default filenames
- Parquet settings (compression, row group size)

### 2. Documentation mandatory
- Every **module** must have a module-level docstring explaining its purpose.
- Every **public function/class** must have a docstring with parameters and return values.
- Every **CLI handler** (`_cmd_*`) must document the orchestration flow it performs.
- Complex private methods (especially in `quality.py`) need docstrings explaining the algorithm.
- Docstrings are for humans AND LLMs — be precise about contracts and edge cases.

### 3. Read from config, don't bypass it
The most critical bug pattern we've seen: code that uses a hardcoded default instead of reading from the user's TOML config.
- `checks.py` and `repo_compliance.py` must use `cfg.csv_delimiter` and `cfg.csv_encoding`, not hardcoded `";"` and `"utf-8-sig"`.
- Any function that accepts a file path should get its encoding/delimiter from config, not from a default parameter.
- Pattern: pass `cfg` or config values explicitly — don't rely on `config.py` defaults when a user-provided TOML value exists.

### 4. No duplicated logic
- If you find yourself copy-pasting a function (even with a different name), extract it to a shared module.
- Example: `_parquet_to_hf_dtype` was duplicated in `repo_compliance.py` and `prepare.py` — now in `_parquet_helpers.py`.
- Example: quality check names were hardcoded in 4 places — now in `quality.QUALITY_CHECK_NAMES`.

### 5. Pre-commit hooks run automatically
- `ruff` (lint + fix + format), `mypy`, and `pyright` run on every commit.
- Never commit with `--no-verify` unless you have a documented reason.
- Before pushing, run `uv run mypy src/ scripts/` and `uv run pyright` — the CI will reject type errors.

### 6. Tests must match specs
- Every SDD spec scenario maps to a repository test (`test:`) or to declared verify-phase evidence
  (`verify:`). A spec that carries a `## Test Mapping` table SHALL list every `#### Scenario:` in
  exactly one row, and each row's Verification cell SHALL begin with exactly one evidence prefix:
  `test:` (a repository test path, optionally `path::test_name`) or `verify:` (a declared evidence
  class). The contract of record is the `test-mapping-contract` capability.
- The gate (`scripts/check_test_mapping.py`, run in CI's `lint` job) verifies that a `test:` reference
  **exists and is collected by pytest**. That is an existence/collection check, not proof that the
  referenced test exercises the scenario. A `verify:` row is the **declared, non-verifiable**
  **escape hatch**: it names an evidence class, it does not prove its scenario, and no mechanism
  re-checks it. Owner: the repository maintainer. Review trigger: any change to a `verify:` row or to
  a spec's evidence class, and each release review. The checker reports the accepted `verify:` count
  on every run so the hatch's size is visible.
- Specs without a `## Test Mapping` table are recorded in `openspec/test-mapping-registry.md` as a
  **permanent declared backlog** — not pending work — and stay outside the gate. The checker enforces
  the registry↔tree bijection, so no spec can silently fall outside the gate.
- When implementing, run `uv run pytest tests/ -q` after every change batch. Never reduce coverage: the
  authoritative tally is what `uv run pytest tests/ -q` reports on your branch — re-derive it, never
  trust a figure written here.

### 7. CLI help text accuracy
- When adding a new flag or changing behavior, update the argparse `help=` and `description=` strings.
- The README must reflect the current CLI interface — update it in the same commit.

### 8. Naming conventions
- Private helpers: `_lowercase_with_underscores`
- Public API: `lowercase_with_underscores`
- Constants: `UPPERCASE_WITH_UNDERSCORES`
- Type annotations: always use `from __future__ import annotations`
- Use `TYPE_CHECKING` for imports that are only needed for type hints.

### 9. Dependency discipline
- Check if a dependency is already transitive before adding it (pyarrow comes via huggingface-hub).
- New dependencies go in `pyproject.toml` `dependencies`, not `dev-dependencies`, unless they're test-only.
- Prefer format-native readers over heavy dependencies (openpyxl over pandas for Excel).
- Dependency bumps (spec `ci` CI-13/CI-14): minor/patch are grouped and automatic; majors stay
  ungrouped and require explicit adaptation review. `ruff` is a coordinated multi-home pin, and
  `fastmcp` majors plus the `mypy`/`pyright` analyzer pins are ignored in
  `.github/dependabot.yml`; see CONTRIBUTING → Dependency updates
  for the manual bump procedure. Version declarations live in more than one home — move every home
  together, and let the guards in `tests/test_ci_workflows.py` catch the drift.

### 10. Architecture: one module per concern
- One module per concern: a command owns its domain module, and shared helpers live in `src/sofer/_*.py`.
- The module set is whatever `ls src/sofer/` reports — the directory is the source of truth, not a list
  in this file. `__init__.py` is the package docstring + public API.
- The full inventory, CLI subcommand list, and Windows path/containment notes live in
  CONTRIBUTING → Architecture.

### 11. PR template and delivery record
- All pull requests must use `.github/PULL_REQUEST_TEMPLATE.md`. Fill every section — no
  placeholders or `<!-- comments -->` — and put **actual command output** in Verification.
- Link the issue and any evidence artifacts that exist; the PR describes what, why, and how.
- OpenSpec artifacts are required only when the change uses OpenSpec: name the specs touched and
  the archive path for a change folder delivered by the PR. Ordinary ODD work needs no SDD
  artifacts section and is not made less thorough by that omission.

### 12. Release process
Releases are **tag-driven and automated** by `.github/workflows/release.yml`: pushing a `v*` tag
runs lint, the full test matrix, and wheel validation, then creates a GitHub Release with generated
notes. There is no PyPI publishing.

- `CITATION.cff` MUST declare the tagged version before tagging; the `citation-check` guard fails the
  workflow otherwise.
- The tag is the single source of truth for the version (hatch-vcs). Never add a static version
  field or a second bump location.
- Versioning is semver; pre-1.0 minor bumps may carry breaking changes — document them in the
  release notes. The shipped version always equals the tag: `--version` resolves from installed
  metadata, never from a static constant.
- **Never move or delete a pushed tag** unless the release job never ran (quality gates failed before
  publishing); then repair the preparation through a PR to `main`, delete the tag locally and
  remotely, and re-tag. A published release's tag is never retagged.
- Branch flow: `main` is the single long-lived branch and the default. All work lands through a
  short-lived branch and a reviewed pull request targeting `main`; merging to `main` publishes
  nothing. The release boundary is a version tag on an approved `main` commit, so `main` may carry
  unreleased work. (The `dev` retirement in issue #362 was a one-time bootstrap exception; it grants
  no standing permission to bypass review and no license to reintroduce an integration branch.)
- Python 3.13 is required for the mypy and complete-suite coverage gates; the `tomli` rationale and
  the exact invocations are in CONTRIBUTING → Releases.

The complete cutting-a-release runbook, the immutable-tag exception, and the full Python 3.13
rationale: CONTRIBUTING → Releases.

### 13. README / README_ES sync
- **Every** change to `README.md` MUST also update `README_ES.md` in the **same commit** — not only
  section additions or changes classified as user-facing. `README_ES.md` mirrors the headings and
  section order of `README.md`.
- Technical content (commands, flags, TOML/YAML excerpts, CLI output, filenames,
  URLs) stays in English in both files; only prose is translated.

### 14. CLI-core coverage: 100% mandate, zero pragmas
- `src/sofer/cli.py`, `src/sofer/scanner.py`, `src/sofer/prepare.py`, and
  `src/sofer/publish.py` MUST each measure **100.00% line coverage** under
  `uv run coverage report -m` (the `[tool.coverage.run]` configuration:
  `branch = true`, `source = ["src/sofer"]`), over the complete suite
  (`coverage run -m pytest`). The per-file scoped gates
  (`coverage report --include=src/sofer/<file>.py --fail-under=100 -m`, listed in
  `scripts/check_core_coverage.sh` and run by the CI coverage job) are the
  enforcement; a drop below 100.00% in any of the four files fails CI.
- `# pragma: no cover` is **FORBIDDEN** in those four modules — no exception,
  including "genuinely untestable" lines. Every line must actually execute in
  tests; a line that cannot be reached from a test is a defect in the test
  strategy or a design-doc escalation, never a pragma.
- The TOTAL gate stays config-owned (`[tool.coverage.report] fail_under = 90`,
  spec `ci` CI-01) and is never weakened, bypassed, or re-declared by the
  per-file mandate. The per-file 100% gates are additive and scoped per file;
  they hardcode 100 only because 100 is a fixed policy constant, not a tunable
  floor.
- This rule justifies NO `src/sofer/` edit: the dead `if __name__ == "__main__":
  main()` guard in `cli.py` is kept and exercised in-process
  (`runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless
  subcommand) as part of the 100.00% row — `python -m sofer.cli` remains a
  working entry point (`tests/conftest.py::run_cli` drives it as the PB-02
  subprocess boundary).
- This rule's 100% mandate covers exactly those four modules. Other modules are
  governed by their own per-file floors (spec `coverage` COV-01) or have no
  floor.
- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).

### 15. OpenSpec archive placement (when OpenSpec is used)
- A completed OpenSpec change SHALL be archived **inside the pull request that delivers it**: the
  same PR that merges the change also moves `openspec/changes/<change>/` to
  `openspec/changes/archive/<change>/` and adds its `archive-report.md`. The archive is part of the
  change, not follow-up housekeeping.
- Never open a second PR whose only purpose is to archive a change that already merged. By then the
  change is delivered, the archive is orphaned from its own diff, and the reviewer can no longer read
  the change and its record together — which is exactly what happened to the changes delivered by
  #276 and #279 and only archived later in #281.
- The PR body's OpenSpec artifacts description (rule 11) SHALL name the archive path for the change
  it delivers. **"Not archived yet — archive after merge" is not a valid state for a merged change.**
- An archive report's claims SHALL be true of the artifact they describe. A report saying "all tasks
  complete" while the archived `tasks.md` still carries a `pending` row is a **defect in the durable
  record**, not a cosmetic slip — the archived report is the only thing a future reader has (see the
  #281 correction in #282).
- Ordinary ODD work creates no change folder, so it has no archive report and no archive step.
  Historical OpenSpec archives are never rewritten.
