```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:1fd15c2f7d174de78342f02d132f92615f91ae0c4299605114fc4b1f5ec101f1
verdict: pass
blockers: 0
critical_findings: 0
requirements: 0/0
scenarios: 0/0
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:1fd15c2f7d174de78342f02d132f92615f91ae0c4299605114fc4b1f5ec101f1
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:5b3e3905d4d9e175f9dd86715f6d5a9643abecae88f3e6e7b2349e013c8e9006
```

## Verification Report

**Change**: test-cli-mcp-parity-guard
**Version**: test-only (no spec delta)
**Mode**: Standard (strict_tdd: true — the guard IS the deliverable and its
RED step is the fixing changes' explicit flip of `known_gaps`)
**Branch**: test/mcp-cli-parity-guard

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 10 |
| Tasks complete | 10 |
| Tasks incomplete | 0 |

### Evidence

**Targeted** — `uv run pytest tests/test_parity.py -q`:

```
11 passed in 0.91s
```

**Full suite** — `uv run pytest tests/ -q` (exit 0):

```
1506 passed, 6 skipped, 13 warnings in 41.72s
```

1495 baseline + 11 new guard tests; the 13 warnings are the pre-existing
`_infer_type` deprecations in `tests/test_codebook.py` (tracked as #162).

**Mutation probe (detection evidence, reverted)** — a temporary `--noop`
flag added to the scan parser produced the expected A2 failure, then the
working tree was restored:

```
E  AssertionError: scan: CLI flags without MCP mapping/exemption: ['noop']
FAILED tests/test_parity.py::TestAreaParity::test_area_surface_contract[scan]
```

`git status` after revert: only `tests/test_parity.py` +
`openspec/changes/2026-09-12-test-cli-mcp-parity-guard/*` are new
(untracked/modified); no `src/` mutation remains.

**Gates** — ruff (`src/` + `tests/`) clean; mypy (`src/`) clean — 32 source
files; `git diff --check` clean.

### Known deferred behavior (documented, out of scope)

- #152 Phase-1 move-to-raw semantics: behavior, not surface — covered by the
  fixing change's behavior tests (Fase 1).
- `known_gaps` #153/#154/#155: asserting param **absence** today; the fixing
  changes flip each entry to `flag_map` (RED) then implement (GREEN).