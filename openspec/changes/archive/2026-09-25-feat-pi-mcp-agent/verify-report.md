# Verify Report: 2026-09-25-feat-pi-mcp-agent

## Scope of verification

Issue #142 acceptance criteria and the MCP-REG-01/02/03 + CLI-R09 deltas: Pi is
a fourth MCP agent whose entry is a string `command` with `${KEY}` env
references and no `type`/`enabled`, written to Pi-owned files; add/remove are
idempotent/safe; `--agent all` covers four agents; Pi never delegates; docs and
CLI help updated; specs synced; suite/checkers green. Verified on branch
`feat/142-pi-mcp-agent` (base `dev@b546db3`), local, Python 3.13.

## Evidence (real command output)

### Full suite

```
$ uv run coverage run -m pytest -q
1875 passed, 2 skipped, 1 warning in 319.86s (0:05:19)
```

(The two skips are skip-if-absent environment guards, unchanged by this change.)

### MCP area

```
$ uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q
265 passed
```

### Linters / type checkers

```
$ uv run ruff check src/ tests/ scripts/
All checks passed!

$ uv run ruff format --check src/ tests/
70 files already formatted

$ uv run mypy src/ scripts/
Success: no issues found in 35 source files

$ uv run pyright
0 errors, 1 warning, 0 informations
```

(The single pyright warning is the pre-existing `tomli` source-resolution
warning at `src/sofer/_toml.py:27`; unrelated to this change.)

### Test-mapping contract

```
$ uv run python scripts/check_test_mapping.py
...
INFO: mcp-registration: 26 scenario(s), unmapped
INFO: cli: 48 scenario(s), unmapped
...
OK: test-mapping contract holds
```

`mcp-registration` and `cli` remain registered as unmapped (no `## Test Mapping`
table), so the registry↔tree bijection is unchanged.

### Coverage (`coverage run -m pytest` above)

```
$ uv run coverage report -m --include=src/sofer/mcp_registration.py
src/sofer/mcp_registration.py     204      0     68      0   100%

$ uv run coverage report --include=src/sofer/cli.py --fail-under=100 -m
src/sofer/cli.py     567      0    162      0   100%

$ uv run coverage report -m            # TOTAL
TOTAL                             5902    342   2254    152    93%
```

### Core coverage gate (rule 14)

```
$ bash scripts/check_core_coverage.sh
src/sofer/cli.py      567    0   162   0  100%
src/sofer/scanner.py  159    0    76   0  100%
src/sofer/prepare.py  325    0   180   0  100%
src/sofer/publish.py  326    0   138   0  100%
```

## Acceptance-criteria check

| #142 criterion | Status | Evidence |
|----------------|--------|----------|
| add pi user writes `$PI_CODING_AGENT_DIR/mcp.json` (else `~/.pi/agent/mcp.json`) with string command + `${KEY}` env, no secrets | PASS | `TestPiAdapter::test_pi_user_path_honours_env_dir_override`, `test_pi_user_path_defaults_under_home`, `test_pi_empty_env_dir_falls_back_to_home`, `TestPiCli::test_pi_add_user_writes_env_dir_override` |
| add pi project writes `<cwd>/.pi/mcp.json` | PASS | `TestPiAdapter::test_pi_project_path_is_dot_pi`, `TestPiCli::test_pi_add_project_writes_dot_pi_and_env` |
| Re-run byte-identical (no `.bak`, no write); `.bak`/atomic/dry-run/unreadable parity | PASS | `TestPiCli::test_pi_add_is_idempotent_no_backup_no_write`, `test_pi_dry_run_writes_nothing`, `test_pi_add_unreadable_exits_1_no_backup` |
| remove pi removes only `sofer`, preserves others; idempotent absent | PASS | `TestPiCli::test_pi_remove_preserves_other_servers`, `test_pi_remove_idempotent_when_absent` |
| `--agent all` covers pi (four) for add and remove | PASS | `TestPiAdapter::test_agent_names_includes_pi_last`, `TestSingleSourceRegistry::test_cli_agent_choices_derive_from_registry`, four-agent assertions in `test_add_all_dry_run_no_files` / `test_remove_all` / `test_opencode_warning_all_once` |
| Pi never array `command`/`type`/`enabled`; never delegates | PASS | `TestPiAdapter::test_pi_entry_shape_string_command_no_type_or_enabled`, `test_pi_env_braced_refs_and_omits_absent_keys`, `test_pi_never_delegates` |
| README + README_ES + argparse help; spec scenarios; tests; `mypy` clean | PASS | docs diff; `TestPiCli`/`TestPiAdapter`; CLI-R09 delta + `test_cli.py` assertion; `mypy` output above |
| `${KEY}` braces (not bare `$KEY`) persisted | PASS | `test_pi_env_braced_refs_and_omits_absent_keys` asserts `${HF_TOKEN}` present and `$HF_TOKEN` absent |

### Spec scenario → test map (informational; spec stays unmapped)

| Scenario | Test |
|----------|------|
| Add all (4) | `test_add_all_dry_run_no_files`, `test_opencode_warning_all_once` |
| Add Pi user | `TestPiCli::test_pi_add_user_writes_env_dir_override` |
| Add Pi project | `TestPiCli::test_pi_add_project_writes_dot_pi_and_env` |
| Pi entry shape | `TestPiAdapter::test_pi_entry_shape_string_command_no_type_or_enabled` |
| Pi env braced references only | `TestPiAdapter::test_pi_env_braced_refs_and_omits_absent_keys` |
| Remove all (4) | `test_remove_all` |
| Remove Pi preserves others | `TestPiCli::test_pi_remove_preserves_other_servers` |
| Warning fires once for opencode member of all (4) | `test_opencode_warning_all_once` |
| No warning for forwarding agents (incl. pi) | `test_no_warning_codex_gemini_env` — loops codex/gemini/pi, asserts no warning and pi `${KEY}` refs |
| CLI-R09 add/remove help includes pi | `test_cli.py::...::test_mcp_add_help_env_forwarding`, `test_mcp_add_help_flags`, `test_mcp_remove_help_flags` |

## Independent verification

Delegated to a read-only `general` subagent (adversarial, 11 claims). Verdict:
**PASS — all 11 claims verified, none falsified.** It independently reproduced
the focused tests (265 passed), `ruff check`, `mypy`, `pyright`, `ruff format
--check` and `check_test_mapping.py`, diffs of the canonical specs vs the deltas
(byte-identical requirement bodies), README/README_ES sync, and the no-`pragma`
scan.

Two non-blocking discrepancies were raised and resolved here:

1. **Pi "no warning" test gap (fixed in this change).** The scenario names
   `--agent pi`, but `test_no_warning_codex_gemini_env` looped only
   codex/gemini. The test now includes `pi` and asserts its no-warning path and
   `${KEY}` env shape.
2. **Pre-existing `mcp remove --scope project` anchors on `Path.cwd()`** because
   `remove` has no `--cwd`; this applies identically to all agents and is
   unchanged by #142. Recorded as a follow-up, not fixed here.

## Conclusion

All #142 acceptance criteria and the MCP-REG-01/02/03 + CLI-R09 deltas verified.
Pi support is a single-source registry addition with two new capability values;
opencode/codex/gemini behavior is unchanged. `mcp_server.py`'s approval-hint
roster remains a deliberately out-of-scope follow-up.
