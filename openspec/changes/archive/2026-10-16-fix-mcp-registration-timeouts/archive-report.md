# Archive report — `2026-10-16-fix-mcp-registration-timeouts`

> **Change** `2026-10-16-fix-mcp-registration-timeouts` · issues **#287** + **#296** · branch
> `fix/287-296-mcp-registration-timeouts` from `dev@6786ba1` · milestone
> **v0.6.0 — agent surface & card completeness**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

The registered `sofer` entry now carries the host deadlines it needs, and long tools reset them while
they run. The two failure modes the issues report — a cold start over a host's connect deadline and a
multi-minute tool call over its per-request deadline — no longer present as a broken registration.

| Requirement | Where |
| --- | --- |
| MCP-REG-05 — host timeouts in the registered entry | `openspec/specs/mcp-registration/spec.md` (new requirement, 6 scenarios, each with inline `test:` evidence) |
| `[tool.sofer] mcp_request_timeout_seconds` / `mcp_connect_timeout_seconds` / `mcp_progress_heartbeat_seconds` | `src/sofer/config.py`, `pyproject.toml` — both homes, parity guard green |
| Four adapter capabilities (`timeout_key`, `connect_timeout_key`, `timeout_unit`, `native_timeout`) | `src/sofer/mcp_registration.py` |
| `Timeouts`, `timeout_entry_keys()`, `_timeout_keys_equal()`, `dropped_timeout_note()`, the `timeout` decline reason | `src/sofer/mcp_registration.py` |
| `--timeout` / `--connect-timeout` / `--no-timeout`, `_positive_seconds()` | `src/sofer/cli.py` |
| `_ProgressHeartbeatMiddleware`, `_LONG_TOOL_NAMES`, `_LONG_TOOL_NOTE` | `src/sofer/mcp_server.py` |
| Cold start, per-agent timeout table, long-call expectation | `README.md` + `README_ES.md` (rule 13) |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T13). No `pending` row remains; the two work-unit commits on
the branch are the evidence for T13.

## 3. Measured evidence

| Gate | Command | Result |
| --- | --- | --- |
| Full suite | `uv run coverage run -m pytest tests/ -q` | **2185 passed, 9 skipped** (89 s) |
| `cli.py` 100.00% mandate (rule 14) | `uv run coverage report --include=src/sofer/cli.py --fail-under=100 -m` | **100%** (656 stmts, 200 branches, 0 miss) |
| `scanner.py` / `prepare.py` / `publish.py` | same, per file | **100%** each |
| TOTAL floor (`fail_under = 90`) | `uv run coverage report` | **94%** |
| Lint | `uv run ruff check src/ tests/ scripts/` | `All checks passed!` |
| Format | `uv run ruff format --check src/ tests/` | `75 files already formatted` |
| Types | `uv run mypy src/ scripts/` | `Success: no issues found in 37 source files` |
| Types (second) | `uv run pyright` | `0 errors` (1 pre-existing `tomli` warning) |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK: test-mapping contract holds` |
| Pre-commit hooks on both commits | `ruff`, `ruff-format`, `mypy`, `pyright` | all `Passed` |

RED→GREEN is recorded in `design.md` §4, including the plain statement that the new test section was
written after the production edits, with the eight changed-expectation tests as the RED signal
(`8 failed, 416 passed, 3 skipped`).

## 4. Work-unit commits

| Commit | Subject |
| --- | --- |
| `cb237d9` | `feat(mcp): write the host deadlines into the registration entry (#287, #296)` |
| `6b833a7` | `feat(mcp): re-announce progress from long tools so a host deadline resets (#296)` |

No push and no pull request: the maintainer opens them (deliberate, recorded in the change's Log L2).

## 5. Deviations from the plan, stated

1. **Progress notifications were split in the plan and delivered in one change.** The maintainer's D2
   chose the combined scope, so Fase 1b was folded in rather than delivered separately. The SDD change
   and the spec cover both.
2. **`sofer mcp doctor` (#287 §3, spec S6) was not delivered.** The issue lists it as an *optional*
   diagnostic aid, and the measurement it would print is now also the value the entry carries. It is
   left as a follow-up, and `tasks.md` does not claim it — S6 is recorded in the feature document's
   spec list without a task, so no archived row claims work that does not exist.
3. **A callable `Context` parameter was not needed.** The heartbeat middleware reaches the request
   context through `fastmcp.server.dependencies.get_context()`, so no tool signature changed and the
   existing direct-call tests kept working.
4. **opencode gets no timeout key.** Its published schema disagrees with itself across releases (a
   positive integer in `config/mcp.ts`'s zod schema, a `{startup,catalog,execution}` object in
   milliseconds in its current docs), so writing either shape risks failing validation of the whole
   `mcp` block. It is named on stderr and documented instead (decision D5 in `design.md`).

## 6. Follow-ups this change creates

- **`sofer mcp doctor`** (#287 §3): measure the cold start and print the per-agent key and value.
  Optional in the issue, and now partially redundant with the entry the command writes.
- **opencode's timeout**, if its schema stabilises: one adapter field plus one README row.
- **#296 §4**, returning written artifact paths in a form that survives a dropped response: out of
  scope here, and the manifest already helps.
