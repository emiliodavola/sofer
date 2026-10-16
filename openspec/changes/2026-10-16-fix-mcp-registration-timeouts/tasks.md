# Tasks: fix-mcp-registration-timeouts

**Change** `2026-10-16-fix-mcp-registration-timeouts` (GitHub **#287** + **#296**) · branch
`fix/287-296-mcp-registration-timeouts` from `dev@6786ba1` · store **hybrid** — this file plus the
Engram mirror.

**Inputs read this phase, directly:** `odd/tasks/mcp-registration-timeouts.md` (specification of
record), `design.md` and `proposal.md` of this change.

**One-line outcome:** the registered `sofer` entry carries the host deadline it needs and long tools
reset it while they run, so neither a cold start nor a long call has to look like a broken
registration.

---

## Task list

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Feature doc + branch off `dev` | — | done | `odd/tasks/mcp-registration-timeouts.md`; branch `fix/287-296-mcp-registration-timeouts` |
| T2 | `config.py` + `pyproject.toml`: three `[tool.sofer]` defaults, validated positive | D1 | done | `test_config.py` parity guard green |
| T3 | `ADAPTERS`: `timeout_key`, `connect_timeout_key`, `timeout_unit`, `native_timeout` for all five agents | S1 D4 D5 | done | `TestSingleSourceRegistry::test_every_agent_name_has_a_complete_adapter` |
| T4 | `Timeouts` + `timeout_entry_keys()` + `build_entry()` writing the keys | S1 S2 | done | `TestRegistrationTimeouts::test_entry_carries_each_host_timeout_key_and_unit` |
| T5 | `_timeout_keys_equal()` wired into `_entries_equal()` | S7 | done | `test_changed_timeout_is_not_swallowed_by_the_idempotency_guard`, `test_same_timeout_is_idempotent`, `test_codex_same_timeouts_different_command_form_is_idempotent` |
| T6 | `timeout` decline reason in `native_delegation_decline_reasons()` + `delegate_add()` passthrough | S8 D4 | done | `test_native_delegation_declines_with_the_timeout_reason`, `test_decline_reason_order_is_env_scope_timeout`, `test_no_timeouts_leaves_delegation_available` |
| T7 | `dropped_timeout_note()` + CLI stderr note | D5 | done | `test_dropped_timeout_note_only_for_a_host_without_the_key`, `TestMcpRegistrationTimeoutsCli::test_opencode_names_the_missing_timeout_key_on_stderr` |
| T8 | CLI: `--timeout` / `--connect-timeout` / `--no-timeout`, `_positive_seconds()`, help text | S1 D2 | done | `TestMcpRegistrationTimeoutsCli` (11 tests, including the four rejected values and the help assertions) |
| T9 | `mcp-registration` spec delta + canonical spec | S1 S2 S7 S8 | done | `specs/mcp-registration/spec.md` of this change; `openspec/specs/mcp-registration/spec.md` |
| T10 | Progress heartbeat around the long tools + `Runs for minutes:` in their descriptions | S4 S5 | done | `tests/test_mcp_server.py::TestProgressHeartbeat` |
| T11 | README + README_ES: cold start, per-agent timeout table, long-call expectation | S3 S4 | done | both files, rule 13 |
| T12 | Gates: full suite, `cli.py` per-file 100.00%, ruff/format/mypy/pyright, test-mapping checker | — | done | see the close-out below |
| T13 | Work-unit commits on the branch (no push, no PR) | — | done | see the close-out below |

## Close-out

Filled in as the tasks were verified; the measured numbers are recorded in the closing report rather
than restated here.

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The RED signal for this change is the eight existing
tests that failed when the new behaviour landed (`8 failed, 416 passed, 3 skipped`), recorded in
full in `design.md` §4 together with the plain statement that the new test section was written after
the production edits rather than before them.
