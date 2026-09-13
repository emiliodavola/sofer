```yaml
schema: gentle-ai.verify-result/v1
verdict: pass
blockers: 0
critical_findings: 0
warning_findings: 1
requirements: 2/2
scenarios: 6/6
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_summary: 1535 passed, 6 skipped, 13 warnings in 43.60s
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
```

## Verification Report

**Change**: fix-mcp-opencode-env (closes #147)
**Version**: spec delta — ADDED MCP-REG-03 (5 scenarios) + MODIFIED CLI-R09 (1 new scenario)
**Mode**: Standard — strict TDD **off** (`openspec/config.yaml strict_tdd: false`); tests follow the MCP-REG-03 / CLI-R09 scenarios; BDD-style behavioral assertions
**Branch**: `fix/147-opencode-env-warning` @ HEAD 86aded7 (base `dev`; 6 modified files, untracked change dir)
**Read-only**: src/ and tests/ untouched by this phase; no fixes made

### Completeness

| Metric | Value |
| -------- | ------- |
| Tasks total (implementation-owned, 0.1–5.3) | 16 |
| Tasks complete | 16 |
| Tasks incomplete (implementation) | 0 |
| Parent-owned lifecycle tasks (6.1–6.2, `sdd-owner: parent`) | 2 unchecked — lifecycle gates, not implementation scope; routed to parent |
| Requirements covered | 2/2 (ADDED MCP-REG-03, MODIFIED CLI-R09) |
| Scenarios covered | 6/6 (5 MCP-REG-03 + 1 CLI-R09, each traced to a green test) |
| New tests | 7 (6 runtime in `TestEnvForwarding` + 1 help in `TestMcpCliHelp`), purely additive |
| Files touched vs allowed set | 6/6 allowed (`src/sofer/mcp_registration.py`, `src/sofer/cli.py`, `tests/test_mcp_registration.py`, `tests/test_cli.py`, `README.md`, `README_ES.md`) |
| Out-of-scope files | `mcp_server.py`, `_mirror.py`, `prepare.py`, `openspec/specs/*` canonical specs, `pyproject.toml` — all untouched (verified `git diff --name-only`) |

### Scenario → test → code mapping (scenario ⇄ test ⇄ code)

| MCP-REG-03 scenario | Test (`tests/test_mcp_registration.py::TestEnvForwarding`) | Result | Exercises the scenario (non-vacuous) |
| --- | --- | --- | --- |
| S1 — Warning when opencode chosen with env set | `test_opencode_warning_env_present` | **passed** | Yes — asserts stderr warning with stable substrings `receives no env`, `See README`, both names; `rc == 0`; written `opencode.json` == `{type,command,cwd}` with no `env` key |
| S2 — Warning previewed in dry-run | `test_opencode_warning_dry_run` | **passed** | Yes — warning on stderr under `dry_run=True`; no `opencode.json` and no `.bak` created |
| S3 — Warning fires once for opencode member of all | `test_opencode_warning_all_once` | **passed** | Yes — `err.count("receives no env") == 1`; all three files created (opencode/codex/gemini); codex `env_vars` names-only + `hf123` absent from codex file; gemini `$KEY` refs asserted |
| S4 — No warning without env / for forwarding agents | `test_no_warning_without_env` + `test_no_warning_codex_gemini_env` | **both passed** | Yes — env deleted → silent; codex/gemini with env → silent + names-only persisted, `hf123` absent from gemini file; `env_vars`/`env` shapes asserted |
| S5 — Values never leak into output or written file | `test_warning_values_never_leak` | **passed** | Yes — `hf123`/`phrase123` absent from captured stdout+stderr and from the written file, in both real and dry-run modes |

| CLI-R09 scenario | Test (`tests/test_cli.py::TestMcpCliHelp`) | Result | Exercises the scenario (non-vacuous) |
|---|---|---|---|
| add help documents env forwarding | `test_mcp_add_help_env_forwarding` | **passed** | Yes — class harness (`pytest.raises(SystemExit)` around `parse_args(["mcp","add","--help"])`); whitespace-normalized text asserts pinned substrings `codex and gemini receive env forwarding (names only` and `opencode entries carry no environment`; existing `test_mcp_add_help_flags` unchanged |

Code-level invariants (all verified against the working tree):

- `_present_env_keys(env) = [k for k in _ENV_KEYS if env.get(k)]` (L478) — single source, NAMES only, reuses `_ENV_KEYS` (L39); `build_entry`'s codex leg (`env_vars: _present_env_keys(env)`) and gemini leg (`{k: f"${k}" for k in _present_env_keys(env)}`) are semantically byte-identical to the pre-refactor inline literals; the opencode leg `{"type": "local", "command": ["sofer-mcp"], "cwd": cwd_str}` is untouched by the diff — entry shape invariant holds.
- `dropped_env_keys(agent, env)` (L480) — `opencode` → `_present_env_keys(env)`; **all other agents → `[]`, never `None`**; reads keys only.
- Warning fires at the top of the per-agent loop in `_cmd_mcp_add` (cli.py L668-677), immediately after `_agent = cast(...)`, **before** `probe_native` and the `if dry_run:` branch — so it appears in real runs, dry-run previews, and for the opencode member of `--agent all` (agents list at cli.py:643 = exactly `["opencode", "codex", "gemini"]`; same at :756).
- Warning text byte-matches the design: `!  opencode registration receives no env: {names} not forwarded. See README …`. Exit code (`overall`) and stdout untouched — warning is stderr-only and informational.
- Help text appended to `mcp add` description (cli.py L1495-1499) — matches the design-pinned sentence; **ASCII-only** (no U+2192, no em-dash, single quotes) — cp1252-safe per #161. All non-ASCII additions in the diff are confined to **docstrings** (pre-existing `→`/`—` house style), never user-visible output.
- `all` → exactly `["opencode", "codex", "gemini"]` (3 agents, no `pi` #142 leakage, no adapter-table change, no opencode `environment` object); `mcp_server.py` and `delegate_add` untouched (adjacent delegation env gap correctly out of scope).

### Structured status & actionContext findings

Native status (`gentle-ai.sdd-status` v1) reported `changeName: null` with ambiguous selection across four sibling changes; the parent prompt pinned the active change (`2026-09-12-fix-mcp-opencode-env`, matching branch `fix/147-opencode-env-warning`), reported `apply: ready` (attempt settled `complete`, user-authorized budget 2000), and drove verify. Apply evidence confirmed end-to-end: 16/16 implementation rows `[x]`; suite 1535 passed / 6 skipped; ruff + mypy clean. `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` — all changed files lie inside the workspace root; no warnings to act on. Verify produced no edits to source/test code (read-only enforced).

### Evidence (exact commands and outputs)

**Focused new tests** — `uv run pytest tests/ -q -k "test_opencode_warning or test_no_warning or test_warning_values_never_leak or test_mcp_add_help_env_forwarding" -v`:

```
collected 1541 items / 1533 deselected / 8 selected
tests\test_cli.py .                                                 [ 12%]
tests\test_mcp_registration.py ......                               [ 87%]
tests\test_parquet_conversion.py .                                  [100%]
8 passed, 1533 deselected in 0.86s   (exit 0)
```

(7 are the new #147 tests; the 8th is an unrelated pre-existing `test_no_warning*` in `test_parquet_conversion.py` matched by the `-k` filter.)

**Class-level regression** — `uv run pytest tests/test_mcp_registration.py -q -k TestEnvForwarding`:

```
8 passed, 30 deselected in 0.38s   (exit 0)
```

**Help class** — `uv run pytest tests/test_cli.py -q -k TestMcpCliHelp`:

```
6 passed, 96 deselected in 0.29s   (exit 0)
```

**Full suite** — `uv run pytest tests/ -q` (exit **0**):

```
1535 passed, 6 skipped, 13 warnings in 43.60s
```

1541 collected (1535 + 6 skipped) — matches the parent's expectation (baseline 1501/1495/6 → +7 new from this change; the previously claimed intermediate baselines 1534/1528 are consistent with +7 = 1541/1535). Delta is purely additive: `git diff --stat tests/` shows 162+0 for `test_mcp_registration.py` and 17+0 for `test_cli.py`. The 13 warnings are the known pre-existing `_infer_type` DeprecationWarnings (issue #162) — **reported, not fixed** (out of scope).

**Quality gates**:

```
uv run ruff check src/ tests/            → All checks passed!              (exit 0)
uv run mypy src/                         → Success: no issues found in 32 source files (exit 0)
git diff --check                         → silent (clean)                  (exit 0)
```

**Diff size**: `git diff --stat` → `6 files changed, 289 insertions(+), 38 deletions(-)` (~327 changed lines).

### Implementation scope checks (AGENTS.md rules)

- **Rule 4 (no duplicated logic)**: single `_ENV_KEYS` source (L39) reused by `_present_env_keys`, `collect_env` (L457), and both `build_entry` legs; `cli.py` hardcodes no env knowledge (warning names come from `dropped_env_keys` → `_ENV_KEYS` order).
- **Rule 1 (no hardcoded values)**: warning text/help sentence are the only new literals (design-pinned); env names always sourced from `_ENV_KEYS`.
- **Rule 2 (docstrings)**: `_present_env_keys`, `dropped_env_keys` (params/returns, "values never returned", `[]`-not-`None` contract), `build_entry` (opencode env-less contract, warning is CLI's responsibility), `_cmd_mcp_add` (step-3 warning in orchestration flow) all updated.
- **Rule 6 (tests match specs)**: every MCP-REG-03/CLI-R09 scenario → a green test (tables above).
- **Rule 7 (help accuracy)**: `mcp add` description= documents env behavior; `TestMcpCliHelp` synced additively.
- **Rule 13 (README mirror)**: one additive sentence per file at the same relative position in the **Env** bullet (README.md L621-624 / README_ES.md L654-657); heading counts and order match 1:1 across the two files; technical terms stay English (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`, `--agent opencode`, `stderr`); existing "Opencode receives no env." / "Opencode no recibe env." bullets and the manual-`environment`-literal paragraphs untouched (verified: diff shows no changes to those blocks).
- **Out of scope respected**: `mcp_server.py`, canonical `openspec/specs/*`, `pyproject.toml` untouched; no `pi` symbol, no adapter-table change, no `all`→4 expansion, no opencode `environment` object, no secret value written (value-leak tests + `env_vars`/`env` value-absence assertions green). mcp-server spec pre-verified consistent (asserts opencode forwards NO env, L530/L562).

### Strict TDD compliance

Strict TDD is **off** (`strict_tdd: false` in `openspec/config.yaml` + `apply`/`testing` sections; no parent override; no project-local strict-TDD support file). No TDD Cycle Evidence table required. Assertion-quality audit (performed anyway): no tautologies, ghost loops, or type-only assertions — every new test asserts observable behavior (stderr substrings, exit codes, file existence/absence, parsed entry dicts, absence of configured secret values). The `for agent in ("codex", "gemini")` loops iterate real members and assert per-agent file contents.

### Review workload / PR boundary

`Review Workload Forecast` from tasks.md: single PR, `Chain strategy: pending` (no chaining selected), 400-line budget risk Low, estimated ~165–195 changed lines. **Measured actual: 327 changed lines (289+/38−)** — still under the 400 canonical threshold and the session budget 2000, so no delivery pause is required and single-PR is respected. Two accounting notes, flagged for the parent (WARNING, not blocker):

1. **Under-reported diff size**: apply-progress claims "~194 additions, 3 deletions"; the actual diff is 289 insertions / 38 deletions.
2. **Unrelated formatting churn**: the README/README_ES diffs contain 24 table-header reformats (`|---|---|` → `| --- | --- |`, 12 per file) and an EOF-newline addition each, which are cosmetic markdown normalization with **no relation to #147** and are not documented in apply-progress's "Interactions & deviations" section. They are consistent across both files (no mirror drift) and `git diff --check` is clean; recommend the parent either keep them with a PR-description note or drop them to keep the PR strictly #147-scoped.

Only the assigned slice was implemented; no functional scope creep beyond tasks 1.x–4.x. The adjacent codex/gemini delegation env gap and the `import tomli as _tomli` LSP note (apply-progress §Baseline LSP note) are correctly documented as pre-existing / out-of-scope (both authoritative gates pass regardless).

### Task checkbox reconciliation

Implementation rows 0.1–5.3 (16/16) are `[x]` with evidence. The only unchecked rows are the 2 **parent-owned lifecycle gates** (`sdd-owner: parent`):

- `- [ ] 6.1 Run the bounded post-apply review (spec ⇄ test mapping, names-only invariant, cp1252 safety, exit-code unchanged).`
- `- [ ] 6.2 Archive/merge gate: verify all Phase 5 evidence is green and open the PR against`dev` using `.github/PULL_REQUEST_TEMPLATE.md`with real command output.`

These do not count against implementation completeness (consistent with the archived fix-xlsx-staged-parquet-warning precedent). The concerns 6.1 enumerates are addressed by this verify report's scenario tables, value-leak tests, cp1252 grep, and exit-code assertions — the bounded review content is effectively delivered here. **Archive is not yet performed** and must wait for the parent's 6.1/6.2 lifecycle steps.

### Known / documented

- **README table-formatting churn** (24 lines) + EOF newlines — cosmetic, unrelated to #147, under-documented in apply-progress; WARNING carried into the verdict; no functional or mirror impact.
- apply-progress's help-test deviation (whitespace normalization + `(names only` prefix substring) is sound and reproduced: argparse reflows the pinned description at the terminal width, so the test normalizes whitespace and asserts the prefix ending at `(names only`— the pinned user-facing sentence itself is byte-exact in cli.py.
- `_infer_type` DeprecationWarnings: 13, pre-existing (issue #162), reported not fixed.
- opencode entry shape invariant holds: build_entry opencode leg byte-identical to pre-change; asserted by `test_opencode_warning_env_present` and pinned by the S1 scenario.
- Test fixtures isolate env via monkeypatch set/del of `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE`, independent of the runner's shell.

### Blockers

None. Verdict **PASS** (verified): all 6 spec scenarios map to green, non-vacuous tests (7 new + pre-existing regression classes 8/6 passed); full suite 1535 passed / 6 skipped with exit 0; ruff + mypy + `git diff --check` clean; names-never-values invariant, entry-shape invariant, exit-code invariance, dry-run no-write, `all`=3-agents, cp1252 safety, and README mirror all verified. One WARNING (README formatting churn + under-reported diff accounting) for the parent's PR-description/decision; no unchecked implementation tasks remain; archive waits on parent lifecycle 6.1/6.2.
