# Verify report: 2026-09-25-csv-dialect-override

**Branch:** `feat/204-csv-dialect-override` · **Diff:** 14 files, +984 / −45

## Practical verification (from a fresh working tree)

### Tests

```
uv run pytest tests/test_cli.py tests/test_mcp_server.py tests/test_mcp_schema.py \
    tests/test_profile.py tests/test_codebook.py -q
=> 608 passed, 1 skipped

uv run coverage run -m pytest tests/ -q
=> 1913 passed, 2 skipped, 1 warning
```

### Quality gates

```
uv run ruff check src/ tests/ scripts/      => clean ([])
uv run ruff format --check src/ tests/ scripts/ => all formatted
uv run --python 3.13 mypy src/ scripts/     => No issues found
uv run pyright                              => 0 errors, 1 warning
                                               (pre-existing tomli reportMissingModuleSource)
uv run python scripts/check_test_mapping.py => OK: test-mapping contract holds
```

### Coverage

```
scripts/check_core_coverage.sh:
  src/sofer/cli.py      600 stmts / 176 branch / 0 miss / 0 partial / 100%
  src/sofer/scanner.py  ... 100%
  src/sofer/prepare.py  ... 100%
  src/sofer/publish.py  ... 100%

uv run coverage report -m:
  src/sofer/profile.py          96%
  src/sofer/mcp_registration.py 100%
  src/sofer/verification.py     100%
  TOTAL                         93%
```

No `# pragma: no cover` token exists in `cli.py` (verified by the static contract
test and full-text scan).

## Independent adversarial verification

A read-only `general` subagent falsified against 12 claims (CLI flags and
precedence, omitted-path equivalence, echo semantics, MCP params/schema/envelope,
scan exclusion, profile threading and `.tsv` carve-out, cli.py coverage, spec
sync, README mirror, no default removal).

**Result: 12/12 PASS, FALSIFIED: none.** Two non-falsifying nits were fixed after
the report:

- MSP-R18 now says the `dialect` echo applies to the **successful** envelope
  (error/refusal envelopes legitimately omit it — the read may never have run).
- The two MCP tests named `*_has_no_dialect_key` were renamed to `*_dialect_is_none`
  to match what they assert (`dialect` is declared in the schema, so FastMCP
  materializes it as `null`).

The verifier's third observation (omitted MCP responses gain `dialect: null`) is
the sanctioned design in MSP-R18; the genuinely byte-identical surface is the CLI
omitted path and the dialect resolution itself.

## Spec ↔ test evidence

The four capabilities are declared backlog in `openspec/test-mapping-registry.md`
(no `## Test Mapping` table), so the new scenarios do not enter the
test-mapping gate; the checker still passes and no registry entry changed.
Behavioural coverage lives in the new test classes listed in `apply-progress.md`.
