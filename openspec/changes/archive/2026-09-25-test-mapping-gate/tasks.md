# Tasks: `211-test-mapping-gate`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~750–1100 (re-tag ~102 rows + ~46 completed rows, checker ~250, checker tests ~350, registry ~25, docs ~20, CI ~5) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (registry + contract baseline) → PR 2 (checker + checker tests) → PR 3 (rule 6 reword + CI gate + verify) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Registry + the three tables comply with the contract (re-tag, and complete the tables under resolution B) | PR 1 | `python scripts/check_test_mapping.py` (once the checker lands) | `git --no-pager diff --stat openspec/specs openspec/test-mapping-registry.md` | Revert `openspec/test-mapping-registry.md` + the three table diffs; no code depends on them until PR 2 |
| 2 | Checker + its behavior tests | PR 2 | `uv run pytest tests/test_test_mapping_checker.py -q` | `python scripts/check_test_mapping.py` against the real tree | Revert `scripts/check_test_mapping.py` + `tests/test_test_mapping_checker.py`; PR 1 state still valid |
| 3 | Rule 6 / config rewrite + CI gate + static guards | PR 3 | `uv run pytest tests/test_ci_workflows.py -q` | `python scripts/check_test_mapping.py` inside the `lint` job shape | Revert `AGENTS.md`, `openspec/config.yaml`, `.github/workflows/ci.yml`, and the static guards |

> **Scope decision required before apply (resolution A vs B).** Tasks 1.5 and 1.6 implement the full
> scenario↔row bijection (resolution B, the literal phase-2 instruction). Under the proposal-faithful
> row-level contract (resolution A) they are dropped and `mapping-checker` MC-02 relaxes to "a scenario
> is named by at most one row". See `design.md` → Scope Reconciliation.

## Phase 1: Registry and contract baseline

- [ ] 1.1 Create `openspec/test-mapping-registry.md` with the `| Spec | Reason |` table and exactly the 17 unmapped specs (`cli`, `codebook`, `data-quality`, `mcp-registration`, `mcp-server`, `metadata`, `packaging`, `parquet-conversion`, `pii-detection`, `prepare`, `profile`, `publish`, `render`, `repo-compliance`, `scan`, `semantic-type-inference`, `tool-config`), each with a non-empty reason naming it a declared backlog entry (`mapping-checker` MC-05)
- [ ] 1.2 Re-tag every Verification cell of the `ci` table in `openspec/specs/ci/spec.md` (38 rows) with exactly one `test:` / `verify:` prefix, preserving each evidence string verbatim (`test-mapping-contract` TMC-01)
- [ ] 1.3 Re-tag every Verification cell of the `coverage` table in `openspec/specs/coverage/spec.md` with exactly one `test:` / `verify:` prefix, preserving each evidence string verbatim
- [ ] 1.4 Re-tag every Verification cell of the `process-boundary` table in `openspec/specs/process-boundary/spec.md` with exactly one `test:` / `verify:` prefix, preserving each evidence string verbatim
- [ ] 1.5 *(resolution B)* Complete the `process-boundary` table so every `#### Scenario:` heading (48 total) appears in exactly one row — add the ~46 PB-01..PB-13 rows with `verify:` references to each scenario's already-stated evidence class — and amend the "PB-01..PB-13 rows are not backfilled" paragraph to state the backfill now lands here (`mapping-checker` MC-02)
- [ ] 1.6 *(resolution B)* Reconcile the `coverage` table: retarget or remove the retired `COV-04` row so every row names an existing `#### Scenario:` heading, and every heading is named exactly once (`mapping-checker` MC-02)

## Phase 2: Checker implementation (`scripts/check_test_mapping.py`)

- [ ] 2.1 Create `scripts/check_test_mapping.py` with a module-level docstring, an argparse surface (`--repo-root`, `--specs-root`, `--registry`, `--collect-only-cmd`), and module-level constants for the default path roots and the prefix/`::` grammar — no inline magic values (AGENTS rules 1, 2)
- [ ] 2.2 Implement spec-tree enumeration and mapped/unmapped classification over `openspec/specs/*/spec.md`, deriving both sets from the tree (`mapping-checker` MC-01)
- [ ] 2.3 Implement the Markdown table parser: header/separator recognition, data-row extraction, and empty-row detection (`test-mapping-contract` TMC-04, `mapping-checker` MC-04)
- [ ] 2.4 Implement the prefix check and the `test:` / `verify:` reference grammar, including rejection of absolute/Windows paths, empty references, and multi-`::` references (`test-mapping-contract` TMC-01..TMC-03)
- [ ] 2.5 Implement the per-spec scenario↔row bijection: every `#### Scenario:` in exactly one row, every row naming an existing scenario (`mapping-checker` MC-02)
- [ ] 2.6 Implement `test:` resolution: file existence plus pytest **collect-only** node membership, batched over distinct referenced files, `shell=False`, `-p no:cacheprovider`, `cwd=repo_root`, and a `Path.resolve()`/`is_relative_to` containment check on every referenced path (`mapping-checker` MC-03; design Threat Matrix)
- [ ] 2.7 Implement the registry bijection: parse `openspec/test-mapping-registry.md`, require every unmapped spec listed once with a non-empty reason and every mapped spec absent, and re-derive scenario counts at check time (never stored) (`mapping-checker` MC-05)
- [ ] 2.8 Implement the exit contract: exit 0 on a clean tree, non-zero otherwise, reporting the **full** offender list (spec + row/scenario + reason) in one run and modifying no file (`mapping-checker` MC-06)

## Phase 3: Checker tests (`tests/test_test_mapping_checker.py`)

- [ ] 3.1 Create `tests/test_test_mapping_checker.py` with a subprocess harness invoking `sys.executable scripts/check_test_mapping.py --repo-root <tmp>` against temp fixture trees, asserting exit code + reported offender (no `sys.path` mutation, no imports of the script)
- [ ] 3.2 Test that a compliant fixture tree (one mapped spec, registry in bijection) exits 0 (`mapping-checker` MC-06 S1)
- [ ] 3.3 Test that a row with no prefix, a row with two prefixes, and a differently-cased prefix each fail (`test-mapping-contract` TMC-01)
- [ ] 3.4 Test that a malformed `test:` reference (absolute path, empty, multi-`::`) fails (`test-mapping-contract` TMC-02)
- [ ] 3.5 Test that an empty `verify:` reference fails and is not reported as satisfied evidence (`test-mapping-contract` TMC-03, `mapping-checker` MC-04)
- [ ] 3.6 Test that an all-blank row and a row missing the Verification cell fail (`test-mapping-contract` TMC-04)
- [ ] 3.7 Test the scenario↔row failures: an unmapped scenario, a doubly-mapped scenario, and a row naming a non-existent scenario each fail (`mapping-checker` MC-02)
- [ ] 3.8 Test the `test:` resolution failures: missing file, uncollected `::name`, and a path-only file with zero collected items (`mapping-checker` MC-03)
- [ ] 3.9 Test the registry bijection failures: an unregistered unmapped spec, a stale entry for a mapped spec, and an empty reason (`mapping-checker` MC-05)
- [ ] 3.10 Test the subprocess/path hardening: a `test:; touch /tmp/pwned`-style reference is rejected by grammar before collection, and a `../`-escaping reference fails containment (design Threat Matrix RED tests)
- [ ] 3.11 Test that all failures are reported in a single run (two independent violations both appear) (`mapping-checker` MC-06 S3)
- [ ] 3.12 Integration: one subprocess run against the repository root asserts exit 0 on the committed tree, and a real `::name` node resolves through collect-only (`mapping-checker` MC-06 S1, MC-03 S4)

## Phase 4: Rule 6 reword

- [ ] 4.1 Rewrite `AGENTS.md` rule 6 to state the `test:`/`verify:` prefixes, the existence/collection limit (not exercise), the `verify:` escape hatch, and the registry boundary, pointing at the `test-mapping-contract` capability (`rule6-reword` R6-01..R6-03)
- [ ] 4.2 Delete the stale `1766 passed, 6 skipped (1772 collected)` triple from `AGENTS.md` rule 6 without writing a replacement figure, keeping `uv run pytest tests/ -q` as the sole anchor (`rule6-reword` R6-05; absorbs #214)
- [ ] 4.3 Align `openspec/config.yaml` `rules.specs` with the rewritten rule 6 so both normative homes state the same contract terms (`rule6-reword` R6-04)
- [ ] 4.4 Remove the stale `1029 tests (2 skipped, 1031 collected, 334 spec scenarios)` tally from `openspec/config.yaml` `context`, deferring to the `testing.test_command` already declared (`rule6-reword` R6-06)
- [ ] 4.5 Add the static guard to `tests/test_ci_workflows.py` asserting `AGENTS.md` rule 6 and `openspec/config.yaml` `rules.specs` agree on the contract terms, and that no stale tally literal remains (`rule6-reword` R6-04, R6-05)

## Phase 5: CI gate

- [ ] 5.1 Add exactly one step to the `lint` job of `.github/workflows/ci.yml` that invokes `scripts/check_test_mapping.py`; no new job and no new matrix axis (`mapping-checker` MC-07)
- [ ] 5.2 Add the static guard to `tests/test_ci_workflows.py` asserting the `lint` job contains exactly one checker step and no new job/axis was added (`mapping-checker` MC-07 S1)

## Phase 6: Verification

- [ ] 6.1 Run `python scripts/check_test_mapping.py` on the change branch and record the exit code and output as verify-phase runtime evidence (`mapping-checker` MC-06, MC-07 S3)
- [ ] 6.2 Run `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/ scripts/`, `uv run mypy src/ scripts/`, and `uv run pyright` — all clean (AGENTS rules 5, 12; `ci` CI-09/CI-11)
- [ ] 6.3 Run `uv run pytest tests/ -q` green and re-derive the tally on the branch (never quote a figure from the proposal — #214's lesson applied to itself; `process-boundary` PB-11)
- [ ] 6.4 Confirm the diff contains zero `src/sofer/` paths, zero `pyproject.toml` paths, and no coverage-gate change (`coverage` COV-03; `ci` CI-01), and that `openspec/project.md` (read-only) is untouched (`rule6-reword` R6-07)
- [ ] 6.5 Write the verify report under `openspec/changes/211-test-mapping-gate/verify-report.md` with the gate exit codes and the suite tally
