# Verify Report: 2026-09-25-chore-single-source-agent-registry

## Scope of verification

Issue #235 acceptance criteria: single source consumed by `AgentName`, `ADAPTERS`, both
argparse `choices`, both `all` expansions and `resolve_config_path`; `ADAPTERS["key"]`
used or removed; `delegate_add` dead variants removed; drift tests; suite + lone
checkers green. Pure refactor — no spec delta, so the test-mapping registry is unchanged.

## Evidence (branch `chore/235-single-source-agent-set`, local, Python 3.13)

### Full suite

```
$ uv run pytest tests/ -q
1859 passed, 1 skipped
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
(The single pyright warning is the pre-existing `tomli` source-resolution warning at
`src/sofer/_toml.py:27`; unrelated to this change.)

### Test-mapping contract

```
$ uv run python scripts/check_test_mapping.py
...
OK: test-mapping contract holds
```

### Coverage (`uv run coverage run -m pytest` first)

```
$ uv run coverage report -m --include=src/sofer/mcp_registration.py
Name                            Stmts   Miss Branch BrPart  Cover
src/sofer/mcp_registration.py     195      0     64      0   100%

$ uv run coverage report --include=src/sofer/cli.py --fail-under=100 -m
src/sofer/cli.py                  567      0    162      0   100%

$ uv run coverage report -m            # TOTAL
TOTAL                            5893    342   2250    152    93%
```

### Core coverage gate (rule 14)

```
$ bash scripts/check_core_coverage.sh
src/sofer/cli.py       567  0  162  0  100%
src/sofer/scanner.py   159  0   76  0  100%
src/sofer/prepare.py   325  0  180  0  100%
src/sofer/publish.py   326  0  138  0  100%
```

## Acceptance-criteria check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Single source consumed by `AGENT_NAMES`/choices/`all`/`resolve_config_path` | PASS | `TestSingleSourceRegistry::test_cli_agent_choices_derive_from_registry`, `test_all_expansion_and_choices_track_a_new_registry_entry`, `test_resolve_config_path_matches_registry_for_every_agent` |
| `ADAPTERS["key"]` used; no per-agent key hardcoded | PASS | `merge`/`remove_entry` use `_adapter(agent)["key"]`; existing merge/remove tests pass |
| `delegate_add` dead variants removed | PASS | single declared shape; `TestDelegationNext` passes |
| Drift tests fail if a site drifts | PASS | sentinel registry entry appears in CLI choices and is written by `--agent all` |
| Suite/lint/type green | PASS | outputs above |

## Conclusion

All #235 acceptance criteria verified. No spec requirements change; the `mcp-registration`
and `cli` capabilities stay registered as unmapped, and the test-mapping contract holds.
