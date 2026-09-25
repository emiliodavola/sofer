# Verify Report — `211-test-mapping-gate` (apply, resolution B)

> Phase: apply + verification. Scope resolution: **B — full scenario↔row bijection**, confirmed by the
> maintainer. Branch `feat/211-test-mapping-gate`. No commit, push, or PR was made.

## 1. Scope reconciliation executed (resolution B)

| Item | Action | Result |
| --- | --- | --- |
| `openspec/specs/process-boundary/spec.md` | Backfilled the 46 PB-01..PB-13 rows (`verify:` references to each scenario's own stated evidence class); re-tagged the 2 PB-14 rows; rewrote the "backfill is a separate concern" paragraph | 48 scenarios / 48 rows, bijective |
| `openspec/specs/coverage/spec.md` | Removed the retired `COV-04` row (it named no scenario); re-tagged the remaining 17 rows | 17 scenarios / 17 rows, bijective |
| `openspec/specs/ci/spec.md` | Re-tagged all 38 rows with exactly one `test:` / `verify:` prefix, preserving every evidence string | 38 scenarios / 38 rows, bijective |

The coverage guard scenario `#### Scenario: The cli.py __main__ guard is executed under the coverage
tracer` is indented in the spec body; the checker's scenario regex accepts optional leading whitespace,
so it is enumerated and mapped exactly once. This is the one reconciliation nuance resolution B exposed.

## 2. Contract, checker, registry, docs, CI

| Artifact | State |
| --- | --- |
| `scripts/check_test_mapping.py` | Created — stdlib-only checker: enumeration (MC-01), table parse (TMC-04/MC-04), prefix + `test:`/`verify:` grammar (TMC-01..TMC-03), scenario↔row bijection (MC-02), pytest **collect-only** resolution (MC-03), registry bijection (MC-05), exit contract (MC-06) |
| `openspec/test-mapping-registry.md` | Created — 17 unmapped specs, one non-empty reason each; counts re-derived, never stored |
| `AGENTS.md` rule 6 | Rewritten: prefixes, existence/collection limit (not exercise), `verify:` escape hatch, registry boundary; the stale `1766/6/1772` tally deleted (#214 absorbed), reproducing command retained |
| `openspec/config.yaml` | `rules.specs` aligned with rule 6; stale `1029 tests (2 skipped, 1031 collected, 334 spec scenarios)` removed from `context` (#214); `testing.test_command` retained |
| `.github/workflows/ci.yml` | One step added to the existing `lint` job: `uv run python scripts/check_test_mapping.py`; no new job, no new matrix axis |
| `tests/test_ci_workflows.py` | Three static guards: rule 6 ↔ `rules.specs` contract-term agreement, config-context tally absence, and the lint-job checker step |
| `tests/test_test_mapping_checker.py` | 25 behavior tests through the checker CLI on fixture trees + one real-tree integration run |

`openspec/project.md` was not touched (its tallies stay owned by #184); #212 is untouched.

## 3. Gate evidence (actual command output)

### Checker — exit 0 on the committed tree

```text
$ uv run python scripts/check_test_mapping.py
INFO: ci: 38 scenario(s), mapped
INFO: cli: 48 scenario(s), unmapped
INFO: codebook: 38 scenario(s), unmapped
INFO: coverage: 17 scenario(s), mapped
INFO: data-quality: 1 scenario(s), unmapped
INFO: mcp-registration: 21 scenario(s), unmapped
INFO: mcp-server: 113 scenario(s), unmapped
INFO: metadata: 7 scenario(s), unmapped
INFO: packaging: 13 scenario(s), unmapped
INFO: parquet-conversion: 20 scenario(s), unmapped
INFO: pii-detection: 6 scenario(s), unmapped
INFO: prepare: 44 scenario(s), unmapped
INFO: process-boundary: 48 scenario(s), mapped
INFO: profile: 23 scenario(s), unmapped
INFO: publish: 47 scenario(s), unmapped
INFO: render: 21 scenario(s), unmapped
INFO: repo-compliance: 66 scenario(s), unmapped
INFO: scan: 34 scenario(s), unmapped
INFO: semantic-type-inference: 11 scenario(s), unmapped
INFO: tool-config: 44 scenario(s), unmapped
OK: test-mapping contract holds
CHECKER_EXIT=0
```

### Full suite — green (tally re-derived on this branch, never quoted)

```text
$ uv run pytest tests/ -q
1846 passed, 2 skipped, 1 warning in 329.60s (0:05:29)
```

The single warning is the pre-existing `runpy` `RuntimeWarning` from
`tests/test_cli.py::test_cli_main_guard_executed_via_runpy`; it is not a `DeprecationWarning` from
`sofer.codebook` (PB-12).

### Lint / format / types

```text
$ uv run ruff check src/ tests/ scripts/      -> All checks passed!
$ uv run ruff format --check src/ tests/ scripts/ -> 72 files already formatted
$ uv run mypy src/ scripts/                   -> Success: no issues found in 35 source files
$ uv run pyright                              -> 0 errors, 1 warning, 0 informations
```

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` could not be resolved from source) is
pre-existing and outside this diff; `_toml.py` is not modified by this change. pyright's exit contract
is errors-only (CI-09), and it exits 0.

## 4. Diff scope

```text
$ git status --short
 M .github/workflows/ci.yml
 M AGENTS.md
 M openspec/config.yaml
 M openspec/specs/ci/spec.md
 M openspec/specs/coverage/spec.md
 M openspec/specs/process-boundary/spec.md
 M tests/test_ci_workflows.py
?? openspec/changes/211-test-mapping-gate/
?? openspec/test-mapping-registry.md
?? scripts/check_test_mapping.py
?? tests/test_test_mapping_checker.py
```

Zero `src/sofer/` paths, zero `pyproject.toml` paths, zero `openspec/project.md` paths. No coverage
floor or gate changed (COV-03 / CI-01).
