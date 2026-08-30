# SDD Archive Report: feat-profile-render-all-files

**Date**: 2026-08-30
**Change**: feat-profile-render-all-files
**Issue**: GitHub #91
**PRs**: #94 (merged 5e56c13) + #95 tests (merged 059636f)
**Branch**: feat/91-profile-render-all-files (base dev @ a7f09ca)
**Status**: Complete
**Verdict**: PASS — 31/31 scenarios compliant, 7/7 requirements
**Mode**: hybrid (Engram + OpenSpec)
**Archived to**: `openspec/changes/archive/2026-08-30-feat-profile-render-all-files/`

## Summary

`profile`/`render` now have `codebook`-parity batch via `TOML --all-files` (`generate_all_profiles`/`generate_all_renders`) with `rel_stem` collision map (`relative_to` + `PurePath.suffixes` → `.metadata.yaml`/`.README.md`), flat `profiles/`/`renders/` under `write_root` (Option B anchoring to `cfg._base_dir`, never `cache/`), configurable via `[tool.sofer] profile_dir`/`render_dir`, and `FileExistsError("use --force to overwrite")` guard for single-file. CLI `profile`/`render` + MCP `sofer_profile`/`sofer_render` parity and README sync included. 20/20 tasks complete, 1149 tests passing (1113 at verify, +36 thereafter), ruff + mypy clean, 49 remediation covering tests landed.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| profile | Updated (2 ADDED) | PRF-05 Batch profile via --all-files (8 scenarios) + PRF-06 Single-file force guard (2 scenarios) appended to `openspec/specs/profile/spec.md` (PRF-01..04 preserved, total 6 requirements) |
| render | Updated (2 ADDED) | RND-04 Batch render via --all-files (6 scenarios) + RND-05 Single-file force guard (2 scenarios) appended to `openspec/specs/render/spec.md` (RND-01..03 preserved) |
| cli | Updated (2 MODIFIED) | CLI-R03 profile/render subcommands expanded: `--output`/`--force`/`--all-files`/`--config`, TOML `[[file]]` contract + guard (6 scenarios) + CLI-R04 help text accurate (2 scenarios) replaced in `openspec/specs/cli/spec.md` (CLI-R01/R02/R05-R08 preserved) |
| tool-config | Updated (1 ADDED) | TC-11 profile_dir and render_dir config (5 scenarios) appended to `openspec/specs/tool-config/spec.md` (TC-01..10 preserved) |

Destructive check: no requirements removed or renamed; ADDED appends and MODIFIED replacements are additive. Preservation of unrelated requirements verified.

## Archive Contents

| Artifact | Path | Status |
|----------|------|--------|
| proposal.md | `archive/2026-08-30-feat-profile-render-all-files/proposal.md` | Present |
| explore.md | `archive/2026-08-30-feat-profile-render-all-files/explore.md` | Present — direct codegraph + file reads, batch gap + --force guard |
| specs/profile/spec.md | `archive/2026-08-30-feat-profile-render-all-files/specs/profile/spec.md` | Present — delta PRF-05/PRF-06 |
| specs/render/spec.md | `archive/2026-08-30-feat-profile-render-all-files/specs/render/spec.md` | Present — delta RND-04/RND-05 |
| specs/cli/spec.md | `archive/2026-08-30-feat-profile-render-all-files/specs/cli/spec.md` | Present — delta CLI-R03/R04 modified |
| specs/tool-config/spec.md | `archive/2026-08-30-feat-profile-render-all-files/specs/tool-config/spec.md` | Present — delta TC-11 |
| design.md | `archive/2026-08-30-feat-profile-render-all-files/design.md` | Present |
| tasks.md | `archive/2026-08-30-feat-profile-render-all-files/tasks.md` | 20/20 tasks complete — no unchecked boxes |
| verify-report.md | `archive/2026-08-30-feat-profile-render-all-files/verify-report.md` | PASS 31/31, blockers 0, critical 0 |
| archive-report.md | `archive/2026-08-30-feat-profile-render-all-files/archive-report.md` | This file |

Active changes directory no longer contains `feat-profile-render-all-files` — moved to archive with ISO date prefix 2026-08-30.

## Source of Truth Updated

Canonical specs now reflect new behavior:

- `openspec/specs/profile/spec.md` — PRF-05/PRF-06 added (batch + guard)
- `openspec/specs/render/spec.md` — RND-04/RND-05 added
- `openspec/specs/cli/spec.md` — CLI-R03/R04 modified to include `--all-files`/`--force`/`--config` + TOML contract
- `openspec/specs/tool-config/spec.md` — TC-11 added

No other specs were modified.

## Verification Summary

- **Build**: `uv run ruff check src/ tests/` → All checks passed; `uv run mypy src/` → Success in 28 source files
- **Tests**: 1113 passed / 2 skipped at verify (15.96s); 1149 passed after PR #95 merge per orchestrator context (49 remediation tests: test_config 8 + test_profile 12 + test_render 11 + test_cli 12 + test_mcp_server 6)
- **Spec compliance**: 31/31 scenarios compliant — all correctness and coherence evidence traceable to passing tests (strict runtime-evidence rule)
- **Coherence**: batch algorithm verbatim `codebook.generate_all:387-565`, flat layout under `write_root`, `FileExistsError` hint, MCP containment extended, README/ES headings synced
- **Issues**: CRITICAL 0 after remediation (6 UNTESTED remediated); WARNING 0; SUGGESTION 3 (keep DRY rationale, CI grep hardening, coverage threshold)

## Engram Observation Trace

Hybrid mode — all artifacts persisted to Engram with `capture_prompt: false`. IDs for traceability:

| Artifact | Topic Key | Obs ID | Sync ID |
|----------|-----------|--------|---------|
| explore | `sdd/feat-profile-render-all-files/explore` | 722 | obs-4e1be90451628229 |
| proposal | `sdd/feat-profile-render-all-files/proposal` | 723 | obs-75666f63524014ed |
| spec (concatenated) | `sdd/feat-profile-render-all-files/spec` | 724 | obs-4e2dac7833ea9229 |
| design | `sdd/feat-profile-render-all-files/design` | 725 | obs-ac2f043523c63c62 |
| tasks | `sdd/feat-profile-render-all-files/tasks` | 726 | obs-4889e345191550db |
| apply-progress | `sdd/feat-profile-render-all-files/apply-progress` | 727 | obs-c5fe4d7683f75964 |
| verify-report | `sdd/feat-profile-render-all-files/verify-report` | 728 | obs-3d17a7d576b6b861 |
| archive-report | `sdd/feat-profile-render-all-files/archive-report` | (this save) | (generated on save) |

## Key Implementation Details

- `src/sofer/config.py` — `_DEFAULTS` + `PROFILE_DIR`/`RENDER_DIR`, `reload()` rebinding, empty-string rejection, `pyproject.toml` example
- `src/sofer/profile.py` — `generate_all_profiles(cfg, output_dir?)` (base_dir/data_dir/rel_stem via `relative_to(data_dir)` else `base_dir`, `PurePath.suffixes` → `.metadata.yaml`, collision `output→[sources]`, partial write then `ValueError`), `profile(..., force=False)` guard `exists() → FileExistsError("use --force to overwrite <dest>")`
- `src/sofer/render.py` — `generate_all_renders` mirror with `RENDER_DIR`, skips missing `metadata.yaml`, identical guard for `README.md`
- `src/sofer/cli.py` — `profile`/`render` parsers accept `--all-files`/`--force`/`--config`/`--output` (L880-930 contract), `_cmd_profile`/`_cmd_render` batch branches via `DatasetConfig.from_toml`, `[[file]]` fail-fast, Option B anchoring to `cfg._base_dir`
- `src/sofer/mcp_server.py` — `sofer_profile`/`sofer_render` with `all_files`/`force`/`config`, `_validate_output_targets` + `_reload_tool_config` containment for `profile_dir`/`render_dir` (`../../evil` rejected, bounded at `_get_root()`)
- Tests: 49 covering tests bound to specs; no hardcoded `"profiles"`/`"renders"` except via `config`
- Docs: `README.md` + `README_ES.md` help excerpts + TOML `[[file]]` examples + `--force` note; `docs/configuration.md` + `pyproject.toml` synced

## Risks / Follow-ups

- None blocking. Suggestions S1-S3 from verify-report remain advisory (DRY comment, CI grep, coverage gate). Per-dataset `[meta] profile_dir` override deferred per design.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.
