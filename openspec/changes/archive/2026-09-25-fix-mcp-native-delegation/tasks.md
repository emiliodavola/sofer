# Tasks: 2026-09-25-fix-mcp-native-delegation

## Phase 1 — Registry + fidelity gate (`mcp_registration.py`)

- [x] 1.1 Add `native_env: bool` and `native_scope: bool` to `Adapter`; document
      them (value semantics, scope selector) in the TypedDict and module
      docstrings.
- [x] 1.2 Declare both fields on every entry: opencode/codex/pi `False/False`,
      gemini `False/True`.
- [x] 1.3 Add `native_delegation_decline_reasons(agent, env_keys, scope) ->
      list[str]` — the single fidelity predicate.
- [x] 1.4 `delegate_add(agent, cwd, env_keys, scope="user")`: gate on the
      predicate (return `False` without spawning), forward `--scope <scope>`
      when `native_scope`.
- [x] 1.5 `delegate_remove(agent, scope="user")`: same gate with `env_keys=[]`,
      forward `--scope` when `native_scope`.
- [x] 1.6 Update docstrings to state the criterion and the argv shapes.

## Phase 2 — CLI surface (`cli.py`)

- [x] 2.1 Pass `scope` into `delegate_add` / `delegate_remove`.
- [x] 2.2 Compute decline reasons and emit the informational stderr warning
      (agent + reason(s), names only, no values) before the file-edit fallback;
      keep the generic failure message for raises/non-zero exits.
- [x] 2.3 Update `mcp add` / `mcp remove` `help=`/`description=` with the native
      fidelity sentence.

## Phase 3 — Docs

- [x] 3.1 `README.md`: delegation bullet — native used only when faithful;
      `--scope` forwarded to gemini, codex user-only; env/scope decline warning;
      file edit persists env NAMES.
- [x] 3.2 `README_ES.md`: mirror the same section (prose Spanish, technical
      content English).

## Phase 4 — Specs

- [x] 4.1 Delta `specs/mcp-registration/spec.md`: MODIFIED MCP-REG-01/02
      (fidelity-qualified "prefer native"), ADDED MCP-REG-04 (native delegation
      fidelity) with env-decline, scope-forward, scope-decline, and
      warning+fallback scenarios.
- [x] 4.2 Delta `specs/cli/spec.md`: MODIFIED CLI-R09 (help documents the
      fidelity gate) + scenario.
- [x] 4.3 Sync both canonical specs with the deltas.

## Phase 5 — Tests

- [x] 5.1 `test_mcp_registration.py`: `TestNativeDelegationFidelity` — capability
      fields, predicate truth table, gemini `--scope` argv, codex project-scope
      decline, env-present decline for both, remove scope gate.
- [x] 5.2 Update the adapter-completeness key set and the sentinel registry entry
      for the two new fields.
- [x] 5.3 Update `test_present_delegates` (env now declines) and add the
      env-decline pin; no old env-dropping delegated call remains.
- [x] 5.4 `test_cli.py`: `TestMcpNativeDelegationFidelityCli` — decline warning on
      stderr (env and scope; names only), fallback still writes the file, gemini
      scope reaches the delegated call, generic failure message; `cli.py` stays
      at 100%.

## Phase 6 — Verification

- [x] 6.1 `uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q` —
      278 passed.
- [x] 6.2 `uv run coverage run -m pytest tests/ -q` — 1888 passed, 2 skipped.
- [x] 6.3 `uv run ruff check src/ tests/ scripts/` + `ruff format --check` —
      clean.
- [x] 6.4 `uv run mypy src/ scripts/` — no issues; `uv run pyright` — 0 errors
      (1 pre-existing tomli warning).
- [x] 6.5 `scripts/check_test_mapping.py` — OK; `scripts/check_core_coverage.sh`
      — 4×100%; `coverage report` — `cli.py` 100%, `mcp_registration.py` 100%,
      TOTAL 93%.
- [x] 6.6 Independent read-only verification by a `general` subagent — all 8
      claims PASS, nothing falsified.

## Phase 7 — Archive + PR

- [x] 7.1 Write `apply-progress.md`, `verify-report.md`, `sync-report.md`,
      `archive-report.md`; move the change to `openspec/changes/archive/`.
- [ ] 7.2 Commit, push the branch, open the PR against `dev` (assigned
      `emiliodavola`, body per `.github/PULL_REQUEST_TEMPLATE.md`).
