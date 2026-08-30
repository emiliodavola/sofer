# Proposal: feat-profile-render-all-files

## Intent

`profile`/`render` lack `codebook`'s `TOML --all-files` batch and silently overwrite `metadata.yaml`/`README.md` when two datasets share a directory. Align batch + add `--force` guard.

## Scope

### In Scope
- `--all-files` TOML batch + `--force` guard for `profile`/`render`
- Batch outputs: `<output>/profiles/<rel_stem>.metadata.yaml`, `<output>/renders/<rel_stem>.README.md`
- Config: `profile_dir="profiles"`, `render_dir="renders"` in `_DEFAULTS` + `[tool.sofer]`
- `rel_stem` collision map (replicate `codebook.generate_all`)
- Single-file `FileExistsError` without `--force` (breaking — documented)
- MCP `sofer_profile`/`sofer_render` parity + README sync

### Out of Scope
- Per-dataset `[meta]` dir override
- `<output>/<stem>/` per-dataset folders (config can emulate)
- Root index `profiles.md`/`renders.md`
- New inference types

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `profile`: `PRF-05` batch (TOML `[[file]]`→`rel_stem`) + `PRF-06` guard (`--force`)
- `render`: `RND-04` batch + `RND-05` guard
- `cli`: `CLI-R03`/`R04` list `--all-files`/`--force` + TOML contract

## Approach

**A — `--all-files` + `profiles/`/`renders/` + `--force`** replicates `codebook.generate_all:387-565`.

`[[file]]` via `DatasetConfig.from_toml` (reject `YOUR_USER`); `rel_stem` via `base_dir/OUTPUT_DIR`, `relative_to`, `PurePath.suffixes`; `output=(dir/rel_stem).with_suffix`; map `output→[sources]`, write non-colliding then `ValueError`. Single-file: `exists()→FileExistsError("use --force")`. Config `_DEFAULTS`+`[tool.sofer]`; CLI `880-930` flags (with `--all-files` positional must be TOML with `[[file]]`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py` | Modified | `--all-files`/`--force` + `_cmd_profile`/`_cmd_render` batch |
| `src/sofer/profile.py` | Modified | `generate_all_profiles` + guard; `config.PROFILE_DIR` |
| `src/sofer/render.py` | Modified | `generate_all_renders` + guard; `config.RENDER_DIR` |
| `src/sofer/config.py` | Modified | `profile_dir`/`render_dir` in `_DEFAULTS`+`reload` |
| `src/sofer/mcp_server.py` | Modified | `sofer_profile`/`render` + `_validate_output_targets` |
| `pyproject.toml` | Modified | Docs for `profile_dir`/`render_dir` |
| `openspec/specs/profile` | Modified | `PRF-05`/`PRF-06` |
| `openspec/specs/render` | Modified | `RND-04`/`RND-05` |
| `openspec/specs/cli` | Modified | `CLI-R03`/`R04` |
| `README*` | Modified | Help + examples |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `--force` breaking change | High | 0.x notes + `use --force` hint; budget 3000 ample |
| `rel_stem` drift → hidden collision | Med | Copy `relative_to`+`suffixes` verbatim; subpath tests |
| MCP dir escapes root | Med | Add to `_validate_output_targets` |
| `--all-files` without `[[file]]` | Low | Fail fast + help |

## Rollback Plan

Revert `cli/profile/render/config/mcp_server/pyproject` + spec deltas + README. Outputs regeneratable; callers add `--force`. Don't move `v*` tag if published.

## Dependencies

- `DatasetConfig.from_toml` + `[[file]]` validation; `config.OUTPUT_DIR` anchoring; explore #91

## Success Criteria

- [ ] Help lists `--all-files`/`--force` for both commands
- [ ] `profile dataset.toml --all-files` → one `<output>/profiles/<rel_stem>.metadata.yaml` per `[[file]]`
- [ ] `render dataset.toml --all-files` → one `<output>/renders/<rel_stem>.README.md` per entry
- [ ] Single-file without `--force` errors on exists; with `--force` overwrites
- [ ] `profile_dir`/`render_dir` from `[tool.sofer]`; no hardcodes
- [ ] MCP + README synced; specs merged
