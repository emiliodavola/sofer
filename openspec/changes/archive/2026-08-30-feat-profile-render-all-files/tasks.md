# Tasks: feat-profile-render-all-files

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 750–900 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 config → PR2 profile batch+guard → PR3 render batch+guard → PR4 cli/mcp → PR5 tests/docs |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Config `profile_dir`/`render_dir` | PR1 | Base `feat/profile-render-all-files` |
| 2 | Profile batch + guard | PR2 | Base PR1; needs Unit 1 |
| 3 | Render batch + guard | PR3 | Base PR2; mirrors profile |
| 4 | CLI + MCP wiring | PR4 | Base PR3; dispatch + containment |
| 5 | Tests + docs | PR5 | Base PR4; closes PRF-05/06 RND-04/05 |

## Phase 1: Foundation — Config

- [x] 1.1 Add `profile_dir="profiles"` + `render_dir="renders"` to `_DEFAULTS` in `src/sofer/config.py`; update module docstring
- [x] 1.2 Expose `PROFILE_DIR`/`RENDER_DIR` and rebind in `reload()` from `[tool.sofer]`; reject empty string
- [x] 1.3 Document keys in `pyproject.toml` `[tool.sofer]` example

## Phase 2: Core — Batch + Guard

- [x] 2.1 `src/sofer/profile.py` `generate_all_profiles(cfg, output_dir?)` — replicate `codebook.generate_all` collision map + `rel_stem` (`relative_to`+`PurePath.suffixes`) → `<write_root>/profiles/<rel_stem>.metadata.yaml`
- [x] 2.2 `src/sofer/profile.py:profile()` add `force=False` guard — `exists()` without `force` → `FileExistsError("use --force to overwrite <dest>")`
- [x] 2.3 `src/sofer/render.py` `generate_all_renders(cfg, output_dir?)` — mirror 2.1 → `renders/<rel_stem>.README.md`; skip missing `metadata.yaml`
- [x] 2.4 `src/sofer/render.py:render()` add `force` guard identical to 2.2

## Phase 3: Integration — CLI & MCP

- [x] 3.1 `src/sofer/cli.py:880-930` add `--all-files`/`--force`/`--config`/`--output` to `profile`/`render` parsers; update `help=`/`description=` for `[[file]]` contract + hint
- [x] 3.2 `src/sofer/cli.py` `_cmd_profile`/`_cmd_render` batch branches — `DatasetConfig.from_toml`, fail if no `[[file]]`, Option B anchoring to `cfg._base_dir`
- [x] 3.3 `src/sofer/mcp_server.py` `sofer_profile`/`sofer_render` add `all_files`/`force`/`config` params and batch dispatch
- [x] 3.4 `src/sofer/mcp_server.py` extend `_validate_output_targets`+`_reload_tool_config` to contain `profile_dir`/`render_dir` (`../../evil` rejected)

## Phase 4: Testing

- [x] 4.1 `tests/test_config.py` — defaults `profiles`/`renders`, override `docs/profiles`/`docs/renders`, `reload` rebinding, no hardcodes in `profile.py`/`render.py`
- [x] 4.2 `tests/test_profile.py` PRF-05 — N-files, nested `Labels/etiquetas_a`, collision `ValueError` after partial write, Option B abs/rel, `cache/` untouched, `[[file]]` fail
- [x] 4.3 `tests/test_profile.py` PRF-06 — exists without `--force` → `FileExistsError`+hint; with `--force` overwrites
- [x] 4.4 `tests/test_render.py` RND-04/05 — mirror 4.2+4.3 for `renders/*.README.md`; skip missing `metadata.yaml`
- [x] 4.5 `tests/test_cli.py` CLI-R03/R04 — flags present, batch dispatch, `[[file]]` non-zero, help lists `--all-files`/`--force`/`--config`
- [x] 4.6 `tests/test_mcp_server.py` — containment `../../evil`, batch success+collision, bounded anchoring

## Phase 5: Docs & Polish

- [x] 5.1 `README.md`+`README_ES.md` — update help excerpts, `--all-files` TOML examples, `--force` note; headings stay synced
- [x] 5.2 `uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest tests/ -q`; verify no bypass of `config.csv_*`
- [x] 5.3 Confirm spec deltas `openspec/specs/{profile,render,cli,tool-config}/spec.md` cover PRF-05/06 RND-04/05 TC-11
