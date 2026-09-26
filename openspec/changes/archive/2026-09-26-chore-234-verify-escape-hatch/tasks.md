# Tasks — `2026-09-26-chore-234-verify-escape-hatch`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~220–300 (docs + checker + registry + spec + tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single PR |
| Chain strategy | n/a |

## Phase 1: Decision implementation (docs + checker + registry)

- [ ] 1.1 Rewrite `AGENTS.md` rule 6's escape-hatch sentence to state plainly that a `verify:` row is a
      declared, **non-verifiable** escape hatch, and name the owner and the review trigger.
- [ ] 1.2 Add the matching bullet to `openspec/config.yaml` `rules.specs`, so the two normative homes
      agree.
- [ ] 1.3 `scripts/check_test_mapping.py`: state the policy in the module docstring; add
      `VERIFY_ESCAPE_HATCH_OWNER` / `VERIFY_ESCAPE_HATCH_REVIEW_TRIGGER` constants; implement
      `_count_verify_rows` and print the declared/non-verifiable report line from `_report`; document
      the `SCENARIO_RE` four-hash assumption beside the regex. No `verify:` resolution.
- [ ] 1.4 `openspec/test-mapping-registry.md`: record the **permanent declared backlog** decision for
      the 17 unmapped specs with the owner and review trigger; retitle the entry reasons.

## Phase 2: Spec + tests

- [ ] 2.1 Add requirement **PB-15** to `openspec/specs/process-boundary/spec.md` with its four
      scenarios and the corresponding Test Mapping rows (the bijection requires one row per scenario).
- [ ] 2.2 `tests/test_test_mapping_checker.py`: add
      `test_scenario_regex_matches_only_four_hash_headings` (a `###`/`#####` heading is not
      enumerated; an indented `####` heading is) and
      `test_verify_rows_reported_as_declared_escape_hatch` (the run output names the count, declares it
      non-verifiable, and states the owner and trigger).
- [ ] 2.3 `tests/test_ci_workflows.py`: add
      `test_verify_escape_hatch_has_owner_and_review_trigger` asserting rule 6, `rules.specs`, and the
      registry all state the non-verifiable escape hatch with the owner and review trigger.

## Phase 3: Verification

- [ ] 3.1 Run the new checker tests and the static guard focused, then `uv run pytest tests/ -q` green;
      re-derive the tally on the branch.
- [ ] 3.2 Run `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/ scripts/`,
      `uv run mypy src/ scripts/`, `uv run pyright`, and `uv run python scripts/check_test_mapping.py`
      (exit 0 with the declared `verify:` line).
- [ ] 3.3 Confirm the diff contains zero `src/sofer/` paths and no coverage-gate change; write
      `verify-report.md` with the actual output.

## Phase 4: Archive

- [ ] 4.1 Append PB-15 to `openspec/specs/process-boundary/spec.md` (the archive-time sync) and its
      rows to the spec's Test Mapping table.
- [ ] 4.2 Move the change directory to `openspec/changes/archive/2026-09-26-chore-234-verify-escape-hatch/`
      and write `archive-report.md`.
- [ ] 4.3 Re-run `uv run python scripts/check_test_mapping.py` after the archive (bijection + bijection
      count must hold).
