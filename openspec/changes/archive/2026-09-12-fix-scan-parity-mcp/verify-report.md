```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:7abf64e1a3581867e85a5cd953b75bbb66bc20b331af55b024fb810f6aa3217d
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 8/8
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:7abf64e1a3581867e85a5cd953b75bbb66bc20b331af55b024fb810f6aa3217d
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:5b3e3905d4d9e175f9dd86715f6d5a9643abecae88f3e6e7b2349e013c8e9006
```

## Verification Report

**Change**: fix-scan-parity-mcp
**Version**: spec delta (mcp-server, MODIFIED MSP-R06 + NEW MSP-R14/MSP-R15)
**Mode**: Standard (strict_tdd: true — RED tests before implementation; the
parity guard flip is the designed RED→GREEN step)
**Branch**: fix/152-154-scan-parity

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 12 |
| Tasks complete | 12 |
| Tasks incomplete | 0 |
| Requirements covered | 3/3 (MSP-R06, MSP-R14, MSP-R15) |
| Scenarios covered | 8/8 |

### Evidence

**Targeted (RED→GREEN)** — `uv run pytest tests/test_mcp_server.py -k "MoveLoose or ExtensionsFilter"`:

```
RED:     8 failed, 1 passed (schema rejection: unexpected_keyword_argument)
GREEN:   9 passed
```

**Guard flip** — `uv run pytest tests/test_parity.py tests/test_mcp_server.py -q`:

```
231 passed, 3 skipped in 13.25s
```

The scan area no longer carries `ext` in `known_gaps`; `extension` is mapped
(`ext → extensions`, #154 closed-by-change) and `move_loose` is a documented
MCP-only exemption (#152).

**Full suite** — `uv run pytest tests/ -q` (exit 0):

```
1515 passed, 6 skipped, 13 warnings in 44.03s
```

1506 baseline (incl. parity guard) + 9 new scan-parity tests; the 13 warnings
remain the pre-existing `_infer_type` deprecations (#162).

**Flags of the scheme** — ruff (`src/` + `tests/`) clean; ruff format clean
(65 files); mypy (`src/`) clean — 32 files; `git diff --check` clean.

### Known / documented

- Registered-but-loose legacy files (`local = "data.csv"` direct) are moved
  like any loose file — CLI parity (the Phase-1 move does not distinguish
  registered state from physical location). Out of scope; documented in the
  proposal and spec (MSP-R15 scenarios).