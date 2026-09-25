# Proposal: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

## Intent

Canonical specs and SDD/contributor docs still describe the pre-split tree: they place
SHALL-requirements on the deleted `src/sofer/uploader.py`, point contributors at a
nonexistent `ruff.toml`, list module inventories that omit the newer modules, and hand SDD
phases a baseline that says coverage tooling is not installed and a suite ~400 tests
smaller than reality. A verify phase reading these documents checks requirements against
paths that do not exist; an agent using the module map does not discover `workflow.py`.
This change makes the specs and docs match `dev`, or marks the historical design as
superseded, per AGENTS.md rules 1/4/6/7.

## Scope

### In Scope

- `openspec/specs/parquet-conversion/spec.md` + `openspec/specs/repo-compliance/spec.md`:
  retire the `uploader.py` requirements (name the current owners `_converters.py`,
  `prepare.py`, `publish.py`, or mark superseded) and make the per-module coverage floors
  defer to the `coverage` capability instead of re-declaring a number.
- `AGENTS.md` (rule 4 example, rule 10 inventory), `CONTRIBUTING.md` (tree + ruff config
  location), `docs/configuration.md` (`raw/` layout), `openspec/project.md` (coverage
  tooling, absolute counts, module inventory, version-constant claim).
- `#180` second scope: de-identify `user="emiliodavola"` in
  `openspec/specs/mcp-server/spec.md` and `openspec/specs/process-boundary/spec.md`.

### Out of Scope

- `openspec/specs/cli/spec.md:20` (`GIVEN sofer upload dataset.toml`) — CLI-R01 asserts
  `upload` is rejected; explicit non-goal.
- `openspec/changes/archive/**` — frozen audit record (carries `C:\Users\elaze\...` as
  captured evidence).
- The optional `tests/test_docs_placeholders.py` guard (conditional in #180; not added).
- Live source docstrings naming `uploader.py` as provenance (`_parquet_helpers.py`,
  `publish.py`) — intentional historical references.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The change corrects canonical spec prose and contributor documentation; it does not
alter spec-governed behavior. Where a requirement was placed on a deleted module, it now
names the module that owns the behavior or is explicitly marked superseded (no behavioral
delta). `#180`'s spec edits are illustrative literals not asserted by any test.

## Approach

Edit each document in place: rewrite the `uploader.py` references to the current owners and
add a `Superseded` banner on the historical §4/§5 of `parquet-conversion` (already
superseded by §13); replace the re-declared coverage floors with a deferral to
`openspec/specs/coverage/spec.md`; update the two module inventories and add a
directory-is-source-of-truth line; fix `raw/`, the version claim, and the coverage
statement; drop absolute counts in favour of the CI suite gate; and genericise the two spec
examples. No source change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/parquet-conversion/spec.md` | Modified | §4/§5 superseded; §10.3 defers; §11 checklist corrected |
| `openspec/specs/repo-compliance/spec.md` | Modified | §6.3 defers to `coverage`; checklist corrected |
| `openspec/specs/mcp-server/spec.md` | Modified | Example de-identified (`<hf-user>`) |
| `openspec/specs/process-boundary/spec.md` | Modified | Two examples de-identified |
| `AGENTS.md` | Modified | Rule 4 example; rule 10 inventory + source-of-truth line |
| `CONTRIBUTING.md` | Modified | Tree adds `_toml.py`/`execution_context.py`/`manifest.py`/`workflow.py`; ruff config location |
| `docs/configuration.md` | Modified | Conversion example uses `raw/` → `build/` |
| `openspec/project.md` | Modified | Coverage installed; counts dropped; inventory fixed; version claim fixed |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| test-mapping checker bijection breaks | Low | Edited specs stay registered/unmapped; no `## Test Mapping` table added/removed |
| CI-08/CI-09 CONTRIBUTING assertions break | Low | Code-style section keeps the pinned ruff version; type-checking section untouched |
| Module tree omits a module | Low | Cross-check against `git ls-files src/sofer/*.py`; also defer to `ls src/sofer/` |

## Rollback Plan

Revert the three spec/docs commits (`bd91eee`, `8e51139`, `4e67352`). No source, CI, or
workflow state is touched.

## Dependencies

None.

## Success Criteria

- [ ] No live canonical spec places a requirement on `uploader.py`; remaining mentions are explicitly historical.
- [ ] The two coverage sections defer to the `coverage` capability.
- [ ] AGENTS.md rule 10 and the CONTRIBUTING tree cover `src/sofer/` or defer to the directory.
- [ ] `CONTRIBUTING.md` names `[tool.ruff]` in `pyproject.toml`; no `ruff.toml` reference.
- [ ] `openspec/project.md` records coverage as installed and drops stale counts.
- [ ] No `user="emiliodavola"` remains in canonical specs.
- [ ] `scripts/check_test_mapping.py` OK; `uv run pytest tests/ -q` green.
