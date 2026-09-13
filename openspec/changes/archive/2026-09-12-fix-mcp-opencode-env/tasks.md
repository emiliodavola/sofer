# Tasks: OpenCode Env-Drop Warning for `sofer mcp add` (GitHub #147)

> **Change:** `2026-09-12-fix-mcp-opencode-env` · **Branch:** `fix/147-opencode-env-warning` (base `dev`).
> Warning + documentation only. The opencode entry shape stays
> `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}`; no secret value is ever
> written. `pi` (#142) and any opencode format redesign are OUT of scope.
>
> Scope: `src/sofer/mcp_registration.py`, `src/sofer/cli.py`, `README.md`,
> `README_ES.md`, `tests/test_mcp_registration.py`, `tests/test_cli.py`.
> `strict_tdd: false` (openspec/config.yaml) — tests follow specs, red-green-refactor
> is not enforced per task, but the locked rollout order (helper → CLI → tests →
> docs) from the design phase is preserved.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~165–195 (additions ~165–192, deletions ~3) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

Rationale: two production files receive ~36 additive lines plus a small byte-identical
refactor; docs add one sentence per README; the bulk is new focused tests (~125–155
lines). Well under both the 400 canonical threshold and this session's 800 budget, so
no delivery pause is required. `Chain strategy` stays `pending` because no chaining was
selected.

## Test / Evidence Mapping

| Spec scenario | Test | File · class |
| --- | --- | --- |
| MCP-REG-03 · Warning when opencode chosen with env set | `test_opencode_warning_env_present` | `tests/test_mcp_registration.py` · `TestEnvForwarding` |
| MCP-REG-03 · Warning previewed in dry-run | `test_opencode_warning_dry_run` | `tests/test_mcp_registration.py` · `TestEnvForwarding` |
| MCP-REG-03 · Warning fires once for the opencode member of all | `test_opencode_warning_all_once` | `tests/test_mcp_registration.py` · `TestEnvForwarding` |
| MCP-REG-03 · No warning without env or for forwarding agents | `test_no_warning_without_env` + `test_no_warning_codex_gemini_env` (one scenario → two functions) | `tests/test_mcp_registration.py` · `TestEnvForwarding` |
| MCP-REG-03 · Values never leak into output or written file | `test_warning_values_never_leak` | `tests/test_mcp_registration.py` · `TestEnvForwarding` |
| CLI-R09 · add help documents env forwarding | `test_mcp_add_help_env_forwarding` | `tests/test_cli.py` · `TestMcpCliHelp` |

Evidence gates (all must be green):
`uv run pytest tests/ -q` (baseline 1501 collected / 1495 passed / 6 skipped + new tests),
`uv run ruff check src/ tests/`, `uv run mypy src/`.

---

## Phase 0 — Baseline & Preflight

- [x] 0.1 Confirm branch `fix/147-opencode-env-warning` is based on `dev` and the tree is clean; record the pre-change baseline with `uv run pytest tests/ -q` (expect 1501 collected / 1495 passed / 6 skipped), `uv run ruff check src/ tests/`, `uv run mypy src/`. Save the output for the PR verification section (AGENTS.md §11). <!-- sdd-owner: implementation -->

## Phase 1 — `mcp_registration.py`: single source for dropped env names

- [x] 1.1 Add private `_present_env_keys(env: Mapping[str, str]) -> list[str]` near `collect_env` (`src/sofer/mcp_registration.py` ~L441) implementing the single allow-list filter `[k for k in _ENV_KEYS if env.get(k)]` (NAMES only, never values; truthiness matches `collect_env` present-and-non-empty semantics). `Mapping` is NOT imported yet in this module — add `from collections.abc import Mapping` to the imports so mypy resolves the annotation under `from __future__ import annotations`. Include a full docstring (params, returns, "values never returned"). <!-- sdd-owner: implementation -->
- [x] 1.2 Add public `dropped_env_keys(agent: AgentName, env: Mapping[str, str]) -> list[str]` in the same module: `opencode` → `_present_env_keys(env)`; `codex`/`gemini` → `[]` (never `None`); reads keys only, never values. Include a full docstring documenting the `[]`-not-`None` contract. <!-- sdd-owner: implementation -->
- [x] 1.3 Refactor `build_entry` (`src/sofer/mcp_registration.py` L138-166) so the codex leg uses `env_vars = _present_env_keys(env)` and the gemini leg uses `{k: f"${k}" for k in _present_env_keys(env)}`; leave the opencode return byte-identical. Update the `build_entry` docstring: opencode entry stays env-less and the selection-time warning is the CLI's responsibility (AGENTS.md §2). <!-- sdd-owner: implementation -->
- [x] 1.4 Regression-proof the refactor: run the existing `TestEnvForwarding` tests (`uv run pytest tests/test_mcp_registration.py -q -k TestEnvForwarding`) and confirm codex `env_vars` / gemini `env` output is byte-identical and opencode output unchanged. <!-- sdd-owner: implementation -->

## Phase 2 — `cli.py`: per-agent warning, docstring, help text

- [x] 2.1 In `_cmd_mcp_add` (`src/sofer/cli.py` L605-719), immediately after `_agent = cast(_AgentName, agent)` and **before** `probe_native` and the `if dry_run:` branch, compute `dropped = mcp_registration.dropped_env_keys(_agent, env)` and, when truthy, print exactly one `!`-prefixed stderr line — the design's exact text (stable substrings `"receives no env"`, `"See README"`, names joined in `_ENV_KEYS` order; ASCII-only, single quotes, no U+2192/em-dash per issue #161):

    ```python
    print(
        f"  !  opencode registration receives no env: {', '.join(dropped)} "
        "not forwarded. See README for the launcher environment or an explicit "
        "'environment' literal in opencode.json.",
        file=sys.stderr,
    )
    ```

    Do NOT touch `overall`/exit code or stdout. <!-- sdd-owner: implementation -->
- [x] 2.2 Update the `_cmd_mcp_add` docstring (`src/sofer/cli.py` L606-632) to document the warning step in the per-agent orchestration flow and note it is informational (AGENTS.md §2). <!-- sdd-owner: implementation -->
- [x] 2.3 Append one ASCII-only sentence to the `mcp add` argparse `description=` (`src/sofer/cli.py` L1474-1481) — the design's exact text (yields stable substrings `"codex and gemini receive env forwarding (names only)"` and `"opencode entries carry no environment"`; CLI-R09 aligned):

    ```text
    Env: codex and gemini receive env forwarding (names only, values never
    written); opencode entries carry no environment, and a warning is printed
    on stderr when HF_TOKEN or SOFER_MCP_APPROVAL_PHRASE are set with
    --agent opencode (or all).
    ```

    ASCII-only (no U+2192/em-dash — issue #161; AGENTS.md §7). Do not rename or remove any flag. <!-- sdd-owner: implementation -->

## Phase 3 — Tests

- [x] 3.1 Add `test_opencode_warning_env_present` to `TestEnvForwarding` (`tests/test_mcp_registration.py`, after L481): `HF_TOKEN` + `SOFER_MCP_APPROVAL_PHRASE` set, `probe_native`→False, `validate_cwd`→True; assert `capsys` stderr contains `"receives no env"`, `"See README"`, `"HF_TOKEN"`, `"SOFER_MCP_APPROVAL_PHRASE"`; `rc == 0`; written `opencode.json` `mcp.sofer` == `{type:"local",command:["sofer-mcp"],cwd}` with no `env` key. <!-- sdd-owner: implementation -->
- [x] 3.2 Add `test_opencode_warning_dry_run`: `--dry-run` with `HF_TOKEN` set → warning on stderr; assert no config file and no `.bak` created. <!-- sdd-owner: implementation -->
- [x] 3.3 Add `test_opencode_warning_all_once`: `--agent all` with env set → exactly one warning line on stderr; codex/gemini files persist names only; `all` still expands to exactly `opencode`, `codex`, `gemini`. <!-- sdd-owner: implementation -->
- [x] 3.4 Add the no-warning scenario as two functions: `test_no_warning_without_env` (env vars deleted → no `"receives no env"` on stderr) and `test_no_warning_codex_gemini_env` (codex/gemini with env set → no warning; `env_vars` allow-list / gemini `$KEY` refs persisted, values absent). <!-- sdd-owner: implementation -->
- [x] 3.5 Add `test_warning_values_never_leak`: `HF_TOKEN=hf123`, `SOFER_MCP_APPROVAL_PHRASE=phrase123`; assert neither value appears in captured stdout+stderr nor in any written file, in both real and `--dry-run` modes. <!-- sdd-owner: implementation -->
- [x] 3.6 Add `test_mcp_add_help_env_forwarding` to `TestMcpCliHelp` (`tests/test_cli.py`, after `test_mcp_add_no_cwd_on_remove`): follow the class's existing harness — `pytest.raises(SystemExit)` around `cli._build_parser().parse_args(["mcp", "add", "--help"])`, then assert `capsys.readouterr().out` contains the stable substrings `"codex and gemini receive env forwarding (names only)"` and `"opencode entries carry no environment"`; leave existing `test_mcp_add_help_flags` unchanged. <!-- sdd-owner: implementation -->

## Phase 4 — README mirror (same commit, AGENTS.md §13)

- [x] 4.1 Append the additive warning sentence (design's exact wording) to the **Env** bullet in `README.md` (after the "Opencode receives no env." sentence at L620-621):

    > When `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode` (or `all`) is chosen, `sofer mcp add` prints a warning on stderr naming the dropped variables and leaves the exit code unchanged.

    Do NOT rewrite the existing "Opencode receives no env." bullet or the manual-alternative paragraph at L682-685 (AGENTS.md §4). <!-- sdd-owner: implementation -->
- [x] 4.2 Append the mirrored Spanish-prose sentence to the **Env** bullet in `README_ES.md` (after the "Opencode no recibe env." sentence at L652-654):

    > Cuando `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` están definidas y se elige `--agent opencode` (o `all`), `sofer mcp add` muestra una advertencia en stderr con los nombres de las variables descartadas y deja el código de salida sin cambios.

    Technical content (env var names, flags, `stderr`, exit-code wording) stays English in both files (AGENTS.md §13); verify the L717-720 manual-alternative paragraph is untouched. <!-- sdd-owner: implementation -->
- [x] 4.3 Verify cross-file sync: README.md and README_ES.md structure/headings still mirror and no paragraph was duplicated (AGENTS.md §4, §13). <!-- sdd-owner: implementation -->

## Phase 5 — Evidence Gates

- [x] 5.1 Run `uv run pytest tests/ -q`; confirm green with 1501 collected + 6 new tests and no prior test modified/removed. Capture actual output for the PR template. <!-- sdd-owner: implementation -->
- [x] 5.2 Run `uv run ruff check src/ tests/` and `uv run mypy src/`; both clean. Capture actual output. <!-- sdd-owner: implementation -->
- [x] 5.3 Scope-drift check: confirm no `pi` symbol, no adapter-table change, no `all`→4 expansion, no opencode `environment` object, no secret value written anywhere. <!-- sdd-owner: implementation -->

## Phase 6 — Parent lifecycle gates

- [x] 6.1 Run the bounded post-apply review (spec ⇄ test mapping, names-only invariant, cp1252 safety, exit-code unchanged). <!-- sdd-owner: parent -->
- [x] 6.2 Archive/merge gate: verify all Phase 5 evidence is green and open the PR against `dev` using `.github/PULL_REQUEST_TEMPLATE.md` with real command output. <!-- sdd-owner: parent -->
