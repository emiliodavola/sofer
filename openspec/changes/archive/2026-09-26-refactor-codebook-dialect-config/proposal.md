# Proposal: codebook dialect defaults moved out of the signatures (GitHub #260)

**Change:** `2026-09-26-refactor-codebook-dialect-config` · **Issue:** #260
`refactor(codebook)` · **Branch:** `refactor/260-codebook-dialect-config`
(base `dev`, PR-only)

## Intent

`src/sofer/codebook.py` still hardcodes the CSV delimiter/encoding as default
parameter values (`";"`, `"utf-8-sig"`), violating AGENTS.md rule 3. Every
production caller already resolves the configured value and passes it, so the
literals are a latent trap: a caller that omits them silently assumes the wrong
dialect. Remove the literal defaults, make the dialect a **required** argument,
and have every call site pass the configured value — behaviour-preserving for
CLI/MCP (which already pass config), fail-closed for any caller that relied on
the default.

## Scope

### In Scope

- `src/sofer/codebook.py`: `_read_csv`, `_read_tsv`, `_read_file`, and
  `generate` take `delimiter`/`encoding` as required keyword arguments. No
  literal default remains.
- `src/sofer/profile.py`: the two non-streamed `_read_file` calls pass
  `config.CSV_DELIMITER`/`config.CSV_ENCODING` (the values are ignored for
  parquet/xlsx/jsonl, but the call site must supply the required arguments).
- `src/sofer/cli.py`: docstring/comment truth only (already passes config).
- `tests/test_codebook.py`, `tests/test_config.py`: pass the dialect explicitly
  and add a guard pinning the required-argument / no-literal-default contract.
- Specs: `codebook` CB-R11 and CB-R12 amended.

### Out of Scope

- `generate_all`: its `None` sentinel already resolves from the dataset `[meta]`
  (`cfg.csv_delimiter`/`cfg.csv_encoding`); it is left unchanged.
- `mcp_server.py`: MSP-R10 already injects the post-reload config; no code change.
- `repo_compliance.py` / `prepare.py` dialect tiers and the `_csv_reader`
  fallback chain.
- The `profile`/`cli`/`mcp-server` specs: no clause there pins the codebook
  parameter defaults.

## Capabilities

### Modified Capabilities

- `codebook`: CB-R11 ("Single-file codebook reads through the resolved
  tool-wide config") and CB-R12 ("Explicit CSV dialect override wins over
  config") are amended to require the dialect parameters and forbid literal
  defaults.

## Approach

Replace the four signatures' literal defaults with required keyword-only
arguments, update the two `profile.py` call sites, update the affected tests, and
amend CB-R11/CB-R12. `generate_all` keeps its `None` sentinel and the
`--all-files` tier is untouched. Archive-compose the delta into the canonical
`codebook` spec.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/codebook.py` | Modified | Four entry points lose the literal dialect defaults |
| `src/sofer/profile.py` | Modified | Two non-streamed `_read_file` calls pass configured values |
| `src/sofer/cli.py` | Modified | Docstring/comment truth (no behaviour change) |
| `tests/test_codebook.py` | Modified | Explicit dialect at every call; required-arg guard |
| `tests/test_config.py` | Modified | `generate_codebook` call passes configured dialect |
| `openspec/specs/codebook/spec.md` | Modified | CB-R11/CB-R12 amended |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| A production call site is missed and breaks at runtime | Low | `grep` of every `_read_*`/`generate` call site; full suite + mypy/pyright |
| Direct library caller breaks | Medium | Intended fail-closed behaviour (issue #260); documented in the docstring |
| `profile.py` ≥90% floor row regresses | Low | Both non-streamed branches are covered by `tests/test_profile.py`; fresh coverage re-measured |
| Spec↔code drift | Low | CB-R11/CB-R12 amended in the same change; `codebook` has no Test Mapping table (declared backlog) so no row churn |

## Rollback Plan

Revert the change: restore `codebook.py`, `profile.py`, `cli.py`,
`tests/test_codebook.py`, `tests/test_config.py`, and `openspec/specs/codebook/spec.md`
from the merge base. No persisted state is involved.

## Dependencies

None new.

## Success Criteria

- [ ] No literal `";"` / `"utf-8-sig"` default remains on `_read_csv`,
      `_read_tsv`, `_read_file`, or `generate`.
- [ ] CLI/MCP single-file codebook output is unchanged (they already pass config).
- [ ] Omitting the dialect fails with `TypeError`, pinned by a test.
- [ ] `uv run pytest tests/ -q` green; ruff/mypy/pyright clean; core 100% gate green.
