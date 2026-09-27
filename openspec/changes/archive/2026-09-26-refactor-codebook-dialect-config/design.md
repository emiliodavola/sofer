# Design: codebook dialect defaults moved out of the signatures (GitHub #260)

## Technical Approach

Remove the literal CSV dialect defaults from `codebook.py`'s four entry points and
make the dialect a required argument; update the two `profile.py` call sites and
the affected tests; amend CB-R11/CB-R12 and compose the delta into the canonical
`codebook` spec. `generate_all` and the dataset-`[meta]` tier are untouched.

## Architecture Decisions

### Decision: required keyword-only arguments, not a `None` sentinel

**Choice**: `delimiter` and `encoding` are required keyword-only parameters on
`_read_csv`, `_read_tsv`, `_read_file`, and `generate`:
`def generate(csv_path, output_path=None, *, delimiter, encoding, max_sample=None)`.

**Alternatives considered**: keep `delimiter: str | None = None` and resolve
`config.CSV_DELIMITER` inside (the `max_sample`/`generate_all` pattern).

**Rationale**: Issue #260 explicitly asks to "make them required ... fail-closed
for any call site that relied on the default". A `None` sentinel narrows the trap
but still lets a caller silently inherit the configured default — the literal
default is replaced by an indirect one. Required arguments make omission a
`TypeError` at the call, which is the fail-closed contract rule 3 describes.
Keyword-only keeps `generate`'s existing positional API (`csv_path`,
`output_path`) intact and forces the dialect to be named at every call site.

### Decision: `generate_all` keeps its `None` sentinel

**Choice**: leave `generate_all(delimiter: str | None = None, encoding: str | None = None)`
unchanged.

**Rationale**: its tier is the dataset `[meta]` — `None` resolves to
`cfg.csv_delimiter`/`cfg.csv_encoding` (`codebook.py:522-523`), which is a
config source, not a literal. The issue lists only the four literal-default
sites, and CB-R12's "`generate_all`'s `None` sentinel" clause is retained.

### Decision: `profile.py` passes configured values for non-CSV formats

**Choice**: the two `_read_file` calls in `profile.py` (the `else` branch of
`profile()` and of `_read_dataset_for_profile`) pass
`config.CSV_DELIMITER`/`config.CSV_ENCODING`.

**Rationale**: those branches read parquet/xlsx/jsonl, where the dialect is
ignored, but `_read_file` now requires the arguments. Passing the configured
values (rather than inventing a literal) is exactly the rule-3 posture and keeps
the call sites honest. `profile.py`'s ≥90% floor row is unchanged in scope.

## Data Flow

    [tool.sofer] / dataset [meta]
              │  (config.reload, per invocation)
              ▼
    cli._cmd_codebook ──passes──┐
    mcp_server.sofer_codebook ──┼──► codebook.generate(required delimiter, encoding)
    tests (library) ────────────┘        │
                                         ▼
                              _read_file(required) ──► _read_csv/_read_tsv(required)

    profile.py (parquet/xlsx/jsonl) ── _read_file(config.CSV_*)  [dialect ignored]

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/codebook.py` | Modify | Four signatures: dialect required keyword-only; docstrings state rule 3 |
| `src/sofer/profile.py` | Modify | Two `_read_file` calls pass configured dialect |
| `src/sofer/cli.py` | Modify | Docstring/comment truth only |
| `tests/test_codebook.py` | Modify | Dialect at every call; `TestDialectParametersAreRequired` |
| `tests/test_config.py` | Modify | `generate_codebook` call passes configured dialect |
| `openspec/specs/codebook/spec.md` | Modify | CB-R11/CB-R12 amended via `sdd-archive-compose` |
| `openspec/changes/2026-09-26-refactor-codebook-dialect-config/` | Create | SDD artifacts |

## Interfaces / Contracts

```python
def generate(csv_path, output_path=None, *, delimiter: str, encoding: str, max_sample=None) -> str
def _read_file(path, *, delimiter: str, encoding: str) -> ...
def _read_csv(path, *, encoding: str, delimiter: str) -> ...
def _read_tsv(path, *, encoding: str) -> ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | Omitted dialect raises `TypeError` | `TestDialectParametersAreRequired` (4 entry points) |
| Unit | Supplied dialect drives parsing | `test_supplied_dialect_drives_parsing` |
| Unit | No literal default in signatures | `test_no_literal_dialect_default_in_signatures` (inspect) |
| Unit | Configured dialect reaches `generate` | existing CB-R11 CLI tests + `tests/test_config.py` |
| Runtime | CLI/MCP unchanged | full suite; `uv run pytest tests/ -q` |

## Threat Matrix

N/A — no routing, application shell/subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary changes. The change tightens a
function contract; it reads the same bytes under the same configured dialect.

## Migration / Rollout

No migration. Library callers of `codebook.generate` must now pass `delimiter`
and `encoding`; a caller that omits them raises `TypeError` (documented).

## Open Questions

None.
