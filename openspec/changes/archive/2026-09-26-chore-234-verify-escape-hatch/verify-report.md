# Verify Report — `2026-09-26-chore-234-verify-escape-hatch`

> Phase: apply + verification. Branch `chore/234-verify-escape-hatch`, base `dev@90de0f7`. No commit,
> push, or PR was made during verification. All commands run with the repo's `uv` environment.

## 1. Decision implemented

**Option (b)** from issue #234: `verify:` is a declared, **non-verifiable** escape hatch. Owner: the
repository maintainer. Review trigger: any change to a `verify:` row or to a spec's evidence class,
and each release review. The 17 unmapped specs are a **permanent declared backlog** (not pending
work). `SCENARIO_RE`'s four-hash assumption is documented and pinned by tests. Option (a) —
machine-checking the `verify:` evidence — is explicitly rejected.

## 2. What changed

| File | Action | Description |
| --- | --- | --- |
| `AGENTS.md` | Modified | Rule 6 states the non-verifiable escape hatch + owner + review trigger; registry stated as permanent declared backlog |
| `openspec/config.yaml` | Modified | `rules.specs` aligned with rule 6 (matching bullet + registry bullet) |
| `scripts/check_test_mapping.py` | Modified | Docstring states the policy; owner/trigger constants; `_count_verify_rows` + report line; `SCENARIO_RE` four-hash comment |
| `openspec/test-mapping-registry.md` | Modified | Permanent declared-backlog decision + owner + review trigger; entry reasons retitled |
| `openspec/specs/process-boundary/spec.md` | Modified | Added PB-15 with four scenarios and four Test Mapping rows |
| `tests/test_test_mapping_checker.py` | Modified | `SCENARIO_RE` pin tests + declared-escape-hatch report-line test |
| `tests/test_ci_workflows.py` | Modified | Static guard: rule 6 / `rules.specs` / checker / registry state the policy |

No `src/sofer/` change; no `verify:` reference is resolved or executed.

## 3. Checker runtime evidence (issue #234 AC-1)

```text
$ uv run python scripts/check_test_mapping.py
INFO: ci: 40 scenario(s), mapped
...
INFO: process-boundary: 52 scenario(s), mapped
...
INFO: verify: 65 declared evidence row(s) — declared, non-verifiable escape hatch; owner: the repository maintainer; review: any change to a verify: row or to a spec's evidence class, and each release review
OK: test-mapping contract holds
CHECKER_EXIT=0
```

The escape hatch's size is now visible on every run (65 accepted `verify:` rows on this branch), and
no reference is resolved.

## 4. Focused tests

```text
$ uv run pytest tests/test_test_mapping_checker.py tests/test_ci_workflows.py -q
67 passed

$ uv run pytest \
    tests/test_test_mapping_checker.py::test_scenario_regex_matches_only_four_hash_headings \
    tests/test_test_mapping_checker.py::test_verify_rows_reported_as_declared_escape_hatch \
    tests/test_ci_workflows.py::test_verify_escape_hatch_has_owner_and_review_trigger -v
3 passed
```

The `SCENARIO_RE` pin proves a `###`/`#####`/`###### Scenario:` heading is **not** enumerated (a row
naming it fails as a non-existent scenario) while an indented four-hash heading **is** — both clauses
in the single referenced node `test_scenario_regex_matches_only_four_hash_headings`, so the PB-15
scenario is fully covered by its mapping row. The `process-boundary` bijection (52 scenarios / 52
rows) is enforced by the checker exit 0 above.

## 5. Full suite (tally re-derived on this branch, never quoted)

```text
$ uv run coverage run -m pytest tests/ -q
1917 passed, 1 skipped, 1 warning in 331.36s (0:05:31)
```

The single warning is the pre-existing `runpy` `RuntimeWarning` from
`tests/test_cli.py::test_cli_main_guard_executed_via_runpy`; not a `sofer.codebook`
`DeprecationWarning` (PB-12).

## 6. Coverage gates

```text
$ bash scripts/check_core_coverage.sh
... four 100% rows ...
CORE_EXIT=0

$ uv run coverage report -m | tail -1
TOTAL  5968  342  2282  152  93%
```

The four COV-06 modules stay at 100.00% with no `# pragma: no cover`; TOTAL (93%) is above the
config-owned `fail_under = 90`.

## 7. Lint / format / types

```text
$ uv run ruff check src/ tests/ scripts/          -> All checks passed!
$ uv run ruff format --check src/ tests/ scripts/ -> 72 files already formatted
$ uv run mypy src/ scripts/                       -> mypy: No issues found
$ uv run pyright                                  -> 0 errors, 1 warning, 0 informations
```

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` unresolved from source) is pre-existing
and outside this diff; pyright's exit contract is errors-only and it exits 0.

## 8. Archive sync

`openspec/specs/process-boundary/spec.md` already carries PB-15 and its four rows (the archive-time
sync landed in this branch); the change directory is archived under
`openspec/changes/archive/2026-09-26-chore-234-verify-escape-hatch/`. The checker re-run above is the
post-sync evidence.
