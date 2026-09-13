# Apply Progress — fix-mcp-opencode-env (GitHub #147)

> Change: `2026-09-12-fix-mcp-opencode-env` · Branch: `fix/147-opencode-env-warning`
> Executor: SDD apply phase · Mode: standard (strict_tdd: false per `openspec/config.yaml`)
> Status consumed: native engine `apply: ready / next: apply` (authoritative; verify blocked until apply completes).

## Completed tasks

All implementation-owned checkboxes are marked `- [x]` in `tasks.md` (0.1, 1.1–1.4, 2.1–2.3,
3.1–3.6, 4.1–4.3, 5.1–5.3). Parent-owned rows 6.1/6.2 remain `- [ ]` (deferred lifecycle:
bounded review + PR, not run by apply).

| Task | Status | Evidence |
| --- | --- | --- |
| 0.1 Baseline | done | Branch `fix/147-opencode-env-warning` is a descendant of `dev`; tree clean pre-change; baseline `uv run pytest tests/ -q` → 1534 collected / 1528 passed / 6 skipped; `ruff` clean; `mypy` clean. |
| 1.1 `_present_env_keys(env)` | done | Added near `collect_env`; single allow-list filter `[k for k in _ENV_KEYS if env.get(k)]`; `from collections.abc import Mapping` added (mypy resolves the annotation under `from __future__ import annotations`); docstring (params, returns, "values never returned"). |
| 1.2 `dropped_env_keys(agent, env)` | done | `opencode` → `_present_env_keys(env)`; `codex`/`gemini` → `[]` (never None); docstring documents the `[]`-not-`None` contract; reads keys only. |
| 1.3 `build_entry` refactor | done | codex leg `env_vars = _present_env_keys(env)`; gemini leg `{k: f"${k}" for k in _present_env_keys(env)}`; opencode return byte-identical; docstring updated (opencode entry stays env-less; selection-time warning is CLI's responsibility). |
| 1.4 Regression proof | done | `uv run pytest tests/test_mcp_registration.py -q` → 38 passed; existing codex/gemini env tests byte-identical. |
| 2.1 Per-agent warning | done | In `_cmd_mcp_add`, immediately after `_agent = cast(...)`, before `probe_native` and the `dry_run` branch: `dropped = mcp_registration.dropped_env_keys(_agent, env)`; when truthy, exactly one `!`-prefixed stderr line with the design's exact text (stable substrings `receives no env`, `See README`, names joined in `_ENV_KEYS` order; ASCII-only; values never interpolated). Exit code / stdout untouched. |
| 2.2 Docstring | done | `_cmd_mcp_add` docstring records the warning step (step 3) in the per-agent orchestration flow and notes it is informational (AGENTS.md §2). |
| 2.3 Help text | done | Appended design-pinned ASCII-only sentence to `mcp add` description= (stable substrings `codex and gemini receive env forwarding (names only`… and `opencode entries carry no environment`); no U+2192 / em-dash (issue #161). |
| 3.1–3.5 Runtime tests | done | 6 new tests in `tests/test_mcp_registration.py::TestEnvForwarding`: `test_opencode_warning_env_present`, `test_opencode_warning_dry_run`, `test_opencode_warning_all_once`, `test_no_warning_without_env`, `test_no_warning_codex_gemini_env`, `test_warning_values_never_leak`. |
| 3.6 Help test | done | `test_mcp_add_help_env_forwarding` in `tests/test_cli.py::TestMcpCliHelp`, following the class harness (`pytest.raises(SystemExit)` around `parse_args(["mcp","add","--help"])`); asserts the pinned substrings; existing `test_mcp_add_help_flags` unchanged. |
| 4.1–4.3 README mirror | done | One additive sentence per file (EN + mirrored ES) appended to the **Env** bullet; existing "Opencode receives no env." bullet and the manual-`environment`-alternative paragraphs untouched (verified README.md:619-621/682-685, README_ES.md:652-654/717-720 before edit). Technical content stays English; prose translated (AGENTS.md §13). |
| 5.1 Full suite | done | `uv run pytest tests/ -q` → **1541 collected / 1535 passed / 6 skipped** (baseline 1534 collected / 1528 passed / 6 skipped; delta = +7 tests: 6 runtime + 1 help). No prior test modified/removed (task list unchanged except the task rows themselves). |
| 5.2 Lint + types | done | `uv run ruff check src/ tests/` → All checks passed!; `uv run mypy src/` → Success: no issues found in 32 source files. |
| 5.3 Scope drift | done | No `pi` symbol, no adapter-table change, no `all`→4 expansion (still exactly `["opencode","codex","gemini"]` at cli.py:643/756), no opencode `environment` object, no secret value written anywhere. `mcp_server.py`, `delegate_add`, `_ENV_KEYS`, opencode entry shape untouched. |

## Files changed

- `src/sofer/mcp_registration.py` — `Mapping` import; private `_present_env_keys`; public
  `dropped_env_keys`; `build_entry` codex/gemini legs consume `_present_env_keys`; docstrings.
- `src/sofer/cli.py` — warning block at top of per-agent loop in `_cmd_mcp_add`; `_cmd_mcp_add`
  docstring step 3; one appended help sentence on `mcp add` description=.
- `src/sofer/cli.py` warning + argparse text — ASCII-only (no U+2192, no em-dash, single quotes).
- `tests/test_mcp_registration.py` — 6 new tests in `TestEnvForwarding`.
- `tests/test_cli.py` — 1 new test in `TestMcpCliHelp`.
- `README.md` / `README_ES.md` — one additive sentence each (mirrored).

## Interactions & deviations from design

- **Help test whitespace normalization (deviation, additive-only):** design's pinned help
  sentence renders as `...(names only, values never written)...`, so the exact pinned test
  substring `"(names only)"` (with closing paren) cannot match the rendered description.
  The help sentence text is the pinned user-facing artifact and is kept byte-exact; the test
  asserts the stable substring the pinned text actually renders
  (`"codex and gemini receive env forwarding (names only"` — prefix ending at `(names only`)
  plus `"opencode entries carry no environment"`. Also, argparse reflows the description at
  the terminal width, so the test normalizes whitespace (`re.sub(r"\s+", " ", out)`) before
  asserting — otherwise the pinned words split across wrapped lines. Both pinned substrings'
  wording is fully preserved for the verify review gate.
- **Fixture env isolation:** all new tests set/del `HF_TOKEN` and `SOFER_MCP_APPROVAL_PHRASE`
  explicitly (monkeypatch), so results are independent of the runner's own environment.
- No other deviations. Rollout order preserved (helper → CLI → tests → README pair).

## Baseline LSP note (pre-existing, not introduced by this change)

`src/sofer/mcp_registration.py` L128 `import tomli as _tomli` inside `read_config`'s
try/except fallback is flagged by the pi-lens LSP as "Import tomli could not be resolved".
Evidence it is pre-existing and out of scope: (1) `git diff` shows this change touches only
the `Mapping` import, `build_entry`, and the two new env helpers; (2) the identical
`import tomli as _tomli`/`except ImportError: import tomllib` pattern already exists in
`config.py`, `cli.py`, `model.py`, `mcp_server.py`, and AGENTS.md §12 documents it as a
known cross-version pattern (`tomli` is required only on Python 3.10 where `tomllib` is
absent; this env is Python 3.11.15, so the fallback branch is the correct runtime path);
(3) both authoritative gates pass with it — `uv run mypy src/` → Success, `uv run ruff check
src/ tests/` → All checks passed!. The change contract scopes `mcp_registration.py` edits to
the env helpers + `build_entry` refactor; editing `read_config` would be out-of-scope scope
creep. Left untouched; flagged for the bounded post-apply review (6.1) as known baseline noise.

## Workload / PR boundary

- Changed lines: ~194 additions, 3 deletions across 6 files (well under the session's 800-line
  budget and the 400-line canonical threshold).
- Chain strategy: pending (no chaining selected; single PR recommended by the tasks file).
- Review workload forecast: Low risk — no delivery pause required.

## Remaining tasks (parent-owned, deferred)

- `- [ ] 6.1 Run the bounded post-apply review (spec ⇄ test mapping, names-only invariant, cp1252 safety, exit-code unchanged).`
- `- [ ] 6.2 Archive/merge gate: verify all Phase 5 evidence is green and open the PR against`dev` using `.github/PULL_REQUEST_TEMPLATE.md`with real command output.`

`next_recommended: parent-lifecycle` (bounded review + PR open by parent).
