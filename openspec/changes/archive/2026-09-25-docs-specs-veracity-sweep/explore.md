# Exploration: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

## Current State

Four approved read-only gap-analysis findings leave canonical specs and SDD/contributor docs
describing a tree that no longer exists.

- **#188 — canonical specs require the deleted `uploader.py` and the removed `upload`
  subcommand.** `openspec/specs/parquet-conversion/spec.md` §4 is titled
  "Conversion Logic — `uploader.py`" and states a function SHALL be added to
  `src/sofer/uploader.py`; §11's checklist names `uploader.py`. `repo-compliance/spec.md`
  §6.3 puts an 80% floor on "the upload orchestration code in `uploader.py`" and
  re-declares a 90% floor that the `coverage` capability now owns. `src/sofer/uploader.py`
  does not exist: conversion lives in `_converters.py`/`prepare.py`, delivery in
  `publish.py`.
- **#236 — residual stale references and a false version claim.** `AGENTS.md` rule 4's
  example names `uploader.py`; `docs/configuration.md` uses `data/` where the documented
  layout is `raw/ → cache/ → build/`; `openspec/project.md` claims "`__init__.py` exports
  version constant" while `__init__.py` exports nothing and `_version.py` resolves the
  version from installed metadata.
- **#187 — stale module inventories and a nonexistent `ruff.toml`.** `AGENTS.md` rule 10
  and the `CONTRIBUTING.md` tree omit the newer modules (`execution_context.py`,
  `manifest.py`, `workflow.py`, `_toml.py`, …); `CONTRIBUTING.md` points at `ruff.toml`,
  which does not exist (ruff config is `[tool.ruff]` in `pyproject.toml`).
- **#184 — `openspec/project.md` false baseline.** It says coverage tooling is not
  installed, carries `1342 passed, 2 skipped`, `29 files`, and `334+ spec scenarios across
  16 specs`, and its module inventory omits several modules.

## Affected Areas

- `openspec/specs/parquet-conversion/spec.md`, `openspec/specs/repo-compliance/spec.md`,
  `openspec/specs/mcp-server/spec.md`, `openspec/specs/process-boundary/spec.md`.
- `AGENTS.md`, `CONTRIBUTING.md`, `docs/configuration.md`, `openspec/project.md`.

## Approaches

1. **Correct to the current tree, marking superseded sections explicitly** (recommended) —
   point `uploader.py` requirements at the modules that own the behaviour now, and mark the
   historical design as superseded; defer coverage numbers to the `coverage` capability;
   update inventories (or defer to `ls src/sofer/`); drop absolute counts.
2. **Delete the historical sections outright** — rejected: the specs are an audit trail and
   §13 already supersedes §4 explicitly; deletion loses provenance.
3. **Rewrite the specs to the full current architecture** — rejected as beyond the issue's
   ask and error-prone; #188 accepts a superseded marking.

## Recommendation

Approach 1. Route every live `uploader.py` requirement to `_converters.py` +
`prepare.py`/`publish.py` and mark the superseded design; make the coverage sections defer
to the `coverage` capability; update both inventories and add a directory-is-source-of-truth
line; fix the `raw/` layout and the version claim; replace stale counts with non-stale
statements; de-identify the two spec examples (`#180` second scope).

## Risks

- `scripts/check_test_mapping.py` bijection: the four edited specs are registered
  (unmapped), so prose edits must not add/remove a `## Test Mapping` table.
- `tests/test_ci_workflows.py` asserts AGENTS.md rule 14 (untouched), the CONTRIBUTING.md
  "### Code style" section names the pinned ruff version (kept), and CI-06's coverage
  documentation (untouched).
- `openspec/changes/archive/**` must stay byte-for-byte frozen.

## Ready for Proposal

Yes.
