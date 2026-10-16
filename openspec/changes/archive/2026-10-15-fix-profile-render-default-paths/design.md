# Design — `2026-10-15-fix-profile-render-default-paths`

> **Change** `2026-10-15-fix-profile-render-default-paths` (issue **#294**) · branch
> `fix/294-profile-render-default-paths` from `dev@b7dea51` · store **hybrid**.

---

## 1. The defect, precisely

Two surfaces described the same default and both were wrong in the same way:

```python
# mcp_server.py, sofer_profile_all
Field(description="Override directory for batch profiles (default: profiles). Must stay under server root.")
# mcp_server.py, sofer_render_all
Field(description="Override directory for batch renders (default: renders). Must stay under server root.")
```

while `profile.py:264-270` and `render.py:204-211` both do:

```python
write_root = base_dir / config.OUTPUT_DIR          # cache/
profiles_dir = write_root / config.PROFILE_DIR     # cache/profiles/
```

So the advertised default is a directory the pipeline never writes, and — because `cache/` is the
gitignored artifact cache — a reader who follows it also finds nothing in the tree. The override
semantics were equally unstated: `output_dir` replaces the **write root**, not the leaf directory, so an
override puts the artifacts in `<output_dir>/profiles`, which the old text did not say.

The two tool docstrings carried the same bare-name text in their side-effect lines
(`batch writes profiles/<rel_stem>.metadata.yaml under the write root`,
`batch writes renders/<rel_stem>.README.md`).

## 2. Measured evidence

RED, after the guard was added:

```
$ uv run pytest tests/test_mcp_schema.py -q -k BatchOutputDirDescription
E  AssertionError: Override directory for batch renders (default: renders). Must stay under server root.
E  assert 'cache/renders' in 'Override directory for batch renders (default: renders). Must stay under server root.'
2 failed, 22 deselected
```

GREEN: the two MCP test modules together — **280 passed, 3 skipped**.

## 3. The edits

### 3.1 `src/sofer/mcp_server.py`

| Site | Change |
| --- | --- |
| `_batch_output_dir_description(kind, configured_dir)` (new) | Composes `Override directory for batch <kind> (default: <config.OUTPUT_DIR>/<configured_dir>); the files land in <output_dir>/<configured_dir>. Must stay under server root.` Documented contract: it is evaluated at function-definition time, so the shipped text reflects the import-time `config` constants, and the guard compares against those same constants. |
| `sofer_profile_all` / `sofer_render_all` | The `output_dir` `Field` description is now that call, with `sofer_config.PROFILE_DIR` / `sofer_config.RENDER_DIR`. |
| both docstrings | The side-effect line names the configured key and the artifact-cache write root instead of the bare path: `batch writes one metadata.yaml per [[file]] under the configured profile_dir, inside the artifact-cache write root`. |

The helper lives with the other description-composition helpers (right after `_workflow_description`),
so both uses are one call away from the text contract they share.

### 3.2 `README.md` + `README_ES.md`

The two MCP-table rows (`4b`, `5b`) now say `cache/profiles/` and `cache/renders/`, matching the CLI
sections that already said so. Both files change in the same commit (AGENTS.md rule 13); the paths stay
in English in both, only the prose around them is Spanish.

### 3.3 `tests/test_mcp_schema.py`

`_schema_description(schema)` walks `description` / `anyOf` / `allOf` / `oneOf` and returns the first
description found, mirroring the existing `_schema_has_description` walk (Python 3.10 nests an optional
parameter's description inside `anyOf`; 3.11+ keeps it at the top level). The new
`TestBatchOutputDirDescription` is parametrized over both tools and asserts the resolved default
(`cache/profiles` / `cache/renders`), the override form (`<output_dir>/profiles` / `<output_dir>/renders`)
and the containment note.

### 3.4 `openspec/specs/mcp-server/spec.md` (MSP-R03)

The parameter clause requires the batch `output_dir` descriptions to name the resolved default path (the
configured cache root joined with the configured sub-directory) and the override semantics, and forbids
presenting the bare directory name as the whole default. One scenario is added.

## 4. Rejected alternatives

1. **Writing the literal `cache/profiles` into the description** (the issue's first suggestion). It fixes
   today's text and reproduces the drift mechanism: the value would no longer follow
   `config.OUTPUT_DIR` / `config.PROFILE_DIR`. Deriving it costs one small function.
2. **Moving the deliverables out of `cache/`** (the issue's item 2). Deliberately not taken: see
   `proposal.md` D4 — it is a contract change across `config`, `manifest`, `clean_cache` and the publish
   path, and the documented `--output DIR` route already covers the "keep them where I can read them"
   need.
3. **Returning the written paths in the envelope** (item 3). Real value, but it changes
   `output_schema`; its own change.

## 5. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real red-then-green (§2): the guard was
written first and failed on the shipped text.

## 6. Risks

See `proposal.md` §5. The residual worth naming: the README's path mentions remain literals, so they can
drift again; the code surface agents read is derived and guarded.

## 7. Rollback

Revert-only (§6 of the proposal).

## 8. Success criteria

SC-1..SC-5 of `proposal.md` §7.
