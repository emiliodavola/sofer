# Proposal — `2026-10-15-fix-profile-render-default-paths`

> **Change** `2026-10-15-fix-profile-render-default-paths` · issue **#294** · branch
> `fix/294-profile-render-default-paths` from `dev@b7dea51` · store **hybrid**
> (`odd/tasks/profile-render-default-paths.md` + this folder).
>
> **Status:** implementation complete; archived inside the delivering branch (AGENTS.md rule 15).

---

## 1. Intent

The MCP `output_dir` descriptions of the two batch tools advertise the bare `profiles` / `renders` as
the default directory. The pipeline writes `<dataset>/cache/profiles/` and `<dataset>/cache/renders/`:
`profile.py` / `render.py` resolve `write_root = base_dir / config.OUTPUT_DIR` and then append
`config.PROFILE_DIR` / `config.RENDER_DIR`. A reader who follows the documented default lands on a path
that is never written — and because `cache/` is the gitignored artifact cache, the documented
deliverables are also invisible in the tree.

The drift is narrow: the README's CLI sections already say `cache/profiles/` and `cache/renders/`. Only
the MCP surface was stale (the two parameter descriptions, the two README MCP-table rows and their
Spanish mirrors), plus the two tool docstrings' side-effect lines, which named the same bare
directories.

## 2. Scope

### In scope

- `mcp_server.py`: `_batch_output_dir_description(kind, configured_dir)` — the description text is
  **derived** from `sofer_config.OUTPUT_DIR` + the configured sub-directory and states the override
  semantics (`<output_dir>/<sub-directory>`).
- The two tool docstrings' side-effect lines name the configured key and the artifact-cache write root
  without a hardcoded path.
- `README.md` + `README_ES.md` MCP-table rows (`cache/profiles/`, `cache/renders/`), same commit
  (rule 13).
- `tests/test_mcp_schema.py`: a parametrized guard over both tools, plus a `_schema_description` helper
  that walks the per-interpreter schema wrappers.
- APX/MSP-R03 spec delta and this change folder.

### Out of scope (non-goals)

- **Issue item 2** (move the deliverables out of `cache/`): `cache/` stays the default (D4). Moving it
  is a contract change touching `config.OUTPUT_DIR`, `manifest.py`'s managed-directory list,
  `clean_cache` and the publish path; the escape hatch (`--output DIR`) already exists and is
  documented.
- **Issue item 3** (return the written paths in the envelope): deferred to its own change — it changes
  the tool `output_schema`. Consequence: `#294` is only partially delivered, so whether the PR closes
  it or references it is the maintainer's call (D5).
- No path, default or behaviour change of any kind; the diff is text, docstrings and one derived
  string plus its guard.

## 3. Settled decisions

| # | Decision |
| --- | --- |
| D1 | Derive the description from `config` constants, never a literal path — a literal is the same drift class that produced this issue (rule 1 applied to a documentation string). |
| D2 | State both the resolved default and the override semantics: an override replaces the write root, so files land in `<output_dir>/<sub-directory>`. |
| D3 | Docstrings name the configured key and the artifact-cache write root, without a literal path, keeping the tool-description sentence budget. |
| D4 | `cache/` stays the home; the issue's item 2 decision is "document it faithfully". |
| D5 | Item 3 is out of scope and the issue stays partially open; the closing reference is decided at PR time. |
| D6 | The guard compares against the same import-time `config` constants the description was built from (`Annotated[Field(...)]` is evaluated at function definition). |

## 4. Affected specs

`mcp-server`: MSP-R03 (Modified — the parameter clause requires the resolved default and the override
semantics in the batch `output_dir` descriptions) plus one scenario. No requirement added or removed;
the spec is a declared-backlog one, so no `## Test Mapping` row and no registry edit.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | An agent or user relied on the old (wrong) text. | Low | The old text pointed at a path that never exists; the new text names both the real default and where an override puts the files. |
| R2 | The description is built at import time, so a per-dataset `config` override does not change it. | Low | Documented in the helper's docstring; the shipped text is the default, and a dataset-level override is named by the `<output_dir>` clause. |
| R3 | README rows are still literals, so they could drift again. | Low | They already carry five consistent `cache/...` mentions; the code surface (what agents read) is derived and guarded. Flagged as the residual. |

## 6. Rollback

Revert-only: restoring the two literal descriptions, the two docstring lines and the four README cells
restores the previous text exactly. No state, no migration.

## 7. Success criteria

SC-1 Both descriptions name the resolved default composed from the configured cache root and
     sub-directory.
SC-2 Both descriptions state the `<output_dir>/<sub-directory>` override semantics.
SC-3 The guard fails if a description reverts to the bare directory name.
SC-4 README and README_ES agree with the code and each other (rule 13).
SC-5 Full suite, ruff/format/mypy/pyright and the mapping checker green; no behaviour change.
