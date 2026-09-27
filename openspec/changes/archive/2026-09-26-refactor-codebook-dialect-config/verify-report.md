# Verify Report: codebook dialect defaults moved out of the signatures (GitHub #260)

**Change**: `2026-09-26-refactor-codebook-dialect-config`
**Branch**: `refactor/260-codebook-dialect-config` (base `dev`)
**Mode**: Standard (Strict TDD disabled)

## Scope Verified

| Scenario | Verification | Result |
|----------|--------------|--------|
| CB-R11 — Configured delimiter and encoding are what the codebook reflects | existing CLI tests + `_read_csv` comma/semicolon tests | PASS |
| CB-R11 — CLI and MCP agree on the same input | `tests/test_cli.py`, `tests/test_mcp_server.py` (unchanged) | PASS |
| CB-R11 — Undecodable input yields a diagnostic, never a traceback | existing CB-R11 tests (unchanged) | PASS |
| CB-R11 — Unknown codec name yields the same diagnostic | existing CB-R11 tests (unchanged) | PASS |
| CB-R11 — The fallback policy is the existing one, not a new one | `stream_csv` fallback tests (unchanged) | PASS |
| CB-R11 — Omitting the dialect fails closed | `TestDialectParametersAreRequired` (4 `TypeError` guards + `inspect` guard) | PASS |
| CB-R12 — Explicit delimiter/encoding win over config | existing CB-R12 tests (unchanged) | PASS |
| CB-R12 — Omitted override is unchanged / echoed / `.tsv` tab | existing CB-R12 tests (unchanged) | PASS |

## Runtime Evidence

| Command | Exit | Observed |
|---------|------|----------|
| `uv run pytest tests/test_codebook.py tests/test_config.py tests/test_profile.py -q` | 0 | `218 passed` |
| `uv run pytest tests/ -q` | 0 | `2000 passed, 1 skipped` |
| `bash scripts/check_core_coverage.sh` | 0 | four 100.00% rows (cli, scanner, prepare, publish) |
| `uv run python scripts/check_test_mapping.py` | 0 | `OK: test-mapping contract holds` |
| `uv run ruff check src/ tests/ scripts/` | 0 | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | 0 | `73 files already formatted` |
| `uv run mypy src/ scripts/` | 0 | `Success: no issues found` |
| `uv run pyright` | 0 | `0 errors, 1 warning` (`src/sofer/_toml.py:27`, pre-existing) |
| `uv run coverage report -m --include="src/sofer/profile.py"` | 0 | `96%` — above the ≥90% floor row |

The local gitignored `.coverage` was stale after the source edit; `uv run coverage run -m pytest`
re-measured the tree and `profile.py` at 96%. The plain suite re-run against the fresh database is
green (`2000 passed, 1 skipped`).

## Independent Verification

A separate read-only verifier (fresh context, no edits) confirmed against the working tree:
`inspect.signature` shows the four entry points with no dialect default; every `src/sofer/`
call site passes a resolved value; `cli.py`/`mcp_server.py` still inject the configured dialect;
`tests/test_codebook.py` passes (`88 passed`); the canonical `codebook` spec's CB-R11/CB-R12 are
amended and every prior scenario persists; the only remaining `";"`/`"utf-8-sig"` literals in
`src/sofer/` are the legitimate `config.py`/`model.py` default declarations. Verdict: PASS on all
claims.

## Limitations

- Verify-phase runtime evidence is local; CI re-measures on a clean checkout.
- Direct library callers of `codebook.generate` now fail loudly (`TypeError`) when they omit the
  dialect — the intended fail-closed behaviour (issue #260).

## Result

All targeted scenarios verified; full suite and gates green. Ready for archive.
