```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:f6b15d1013c2915935411f5e4b765d95ab0de9c925ca864fb7c5f43e1fecf03b
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 7/7
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:f6b15d1013c2915935411f5e4b765d95ab0de9c925ca864fb7c5f43e1fecf03b
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:5b3e3905d4d9e175f9dd86715f6d5a9643abecae88f3e6e7b2349e013c8e9006
```

## Verification Report

**Change**: fix-residual-parity
**Version**: spec delta (mcp-server NEW MSP-R16/MSP-R17; codebook NEW CB-R10)
**Mode**: Standard (strict_tdd: true — RED tests before implementation in the
implementation session; the parity guard flip is the designed RED→GREEN step)
**Branch**: fix/153-155-residual-parity

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 12 |
| Tasks complete | 12 |
| Tasks incomplete | 0 |
| Requirements covered | 3/3 (MSP-R16, MSP-R17, CB-R10) |
| Scenarios covered | 7/7 |

### Evidence

**Production implementation (committed 01ff605, re-verified)** —

`uv run pytest tests/test_mcp_server.py -k "PublishCleanup or CodebookAllMaxSample" -q`:

```
7 passed, 223 deselected in 1.17s
```

`uv run pytest tests/test_codebook.py -k generate_all_max_sample -q`:
`1 passed, 81 deselected in 0.08s`
`uv run pytest tests/test_cli.py -k codebook_all_files_max_sample -q`:
`1 passed, 100 deselected in 0.87s`

**Guard flip (RED→GREEN)** — `uv run pytest tests/test_parity.py -q`:

```
RED:   2 failed, 9 passed   (A6: sofer_codebook_all.max_sample now exists (#155);
                             publish clean/clean_cache now exist (#153))
GREEN: 11 passed in 0.82s
```

The publish area no longer carries `clean`/`clean_cache` in
`exempt_flags`/`known_gaps`; both are mapped in `flag_map` (`#153`) and
`max_sample` is declared for the codebook area (`#155`).

**Full suite** — `uv run pytest tests/ -q` (exit **0**):

```
1524 passed, 6 skipped, 13 warnings in 42.89s
```

Exactly the 1515 scan-parity baseline + 9 new residual tests (7 MCP + 1 codebook
unit + 1 CLI parity), zero failures. The 13 warnings remain the pre-existing
`_infer_type` deprecations (#162).

**Flags of the scheme** —

- `uv run ruff check src/ tests/`: clean — `All checks passed!`
- `uv run ruff format --check src/ tests/`: clean — 65 files already formatted
- `uv run mypy src/`: clean — `Success: no issues found in 32 source files`
  (exit 0)
- `git diff --check`: clean

### Known / documented

- Purely-formatting normalization of the production commit's own debt: the two
  `TestCodebookPlaceholderValidation` failures (pre-existing under 01ff605 —
  hand-built `Namespace`s at `tests/test_cli.py:439/460/486` lacked the new
  `max_sample` attribute read by `cli.py:207`) were fixed by completing the
  fixtures with `max_sample=None`; the pre-existing E501 at
  `tests/test_mcp_server.py:4765` and the unformatted files
  (`src/sofer/codebook.py` formatting-only, `tests/test_cli.py`,
  `tests/test_mcp_server.py`) were normalized with `uv run ruff format
  src/ tests/` (2 files reformatted, 63 unchanged). No logic changed in
  `src/sofer/`.
- All requirements/scenarios of this change (3/3, 7/7) and the guard flip
  (11 passed) are green; the canonical specs receive MSP-R16/R17 and CB-R10 at
  apply time.