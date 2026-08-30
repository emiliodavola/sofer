# Apply Progress: feat-publish-clean-and-prune-orphans (GitHub #92)

## Status
- Phase: apply
- Branch: feat/92-publish-clean-and-prune-orphans
- Mode: Standard (strict_tdd false)
- Review budget: 3000 lines (single PR, Low risk)
- Commits:
  - 2fd1764 feat(publish): add --clean and prune orphans (PUB-11/PRP-09)
  - 921a620 docs: document --clean/--clean-cache/--all and orphan pruning
  - 05025a0 chore(sdd): add feat-publish-clean-and-prune-orphans specs and design

## Completed Tasks
- [x] 1.1 src/sofer/_clean.py allowed_output_remotes (expanded_planned_remotes + _AUTO_GENERATED + codebooks/** + keep_csv, dual __/_ guard)
- [x] 1.2 prune_orphans (rglob, delete not in allowlist, try/except per file, log absolute paths)
- [x] 1.3 clean_build/clean_cache (existence check + shutil.rmtree + try/except; clean_cache anchored to cfg._base_dir / config.OUTPUT_DIR)
- [x] 2.1 cli.py --clean (build-only) + --clean-cache/--all alias, help warns sibling-shared, plumbed to publish()
- [x] 2.2 publish.py clean/clean_cache params, gated clean && !dry_run && quality_passed && fail==0, resolve_output_dir + cfg._base_dir/config.OUTPUT_DIR
- [x] 2.3 hf cache cleanup (clean_cache with warn)
- [x] 2.4 local cleanup (dest-only when clean, no delete otherwise)
- [x] 2.5 prepare.py force prune after codebooks (allowed_output_remotes + prune_orphans, force=False skips)
- [x] 3.1 tests/test_clean.py (single-_ sheets, stale delete, compliance/keep_csv retention, idempotency)
- [x] 3.2 tests/test_publish.py PUB-11 scenarios (dry_run no-delete, quality-fail no-delete, upload-fail no-delete, build vs cache isolation, --output anchoring, local dest-only)
- [x] 3.3 tests/test_prepare.py PRP-09 (force prunes, non-force retains, compliance survive, idempotent)
- [x] 3.4 tests/test_cli.py --help contains --clean/--clean-cache/--all, parser plumbs flags
- [x] 3.5 pytest 1062 passed (2 skipped), ruff check passed, mypy src/ passed
- [x] 4.1 README.md documented --clean/--clean-cache/--all, build-only default, sibling cache warning, --output anchoring
- [x] 4.2 README_ES.md mirrored per AGENTS.md rule 13 (flags stay English)
- [x] 4.3 CLI help strings verified
- [x] 4.4 openspec/specs/publish/spec.md (PUB-11) and prepare/spec.md (PRP-09) verified

## Verification
```
uv run pytest tests/ -q  -> 1062 passed, 2 skipped
uv run ruff check src/ tests/  -> All checks passed!
uv run mypy src/  -> Success: no issues found in 28 source files
```

## Files Changed
| File | Action | What Was Done |
|------|--------|---------------|
| src/sofer/_clean.py | Created | allowed_output_remotes, prune_orphans, clean_build, clean_cache |
| src/sofer/cli.py | Modified | --clean + --clean-cache/--all, plumbed to run_publish, help warns siblings |
| src/sofer/publish.py | Modified | clean/clean_cache params, gated hf/local cleanup, resolve_output_dir anchoring |
| src/sofer/prepare.py | Modified | force prune after codebooks (allowed_output_remotes + prune_orphans) |
| tests/test_clean.py | Created | PUB-11/PRP-09 unit tests for _clean |
| tests/test_publish.py | Modified | PUB-11 gated cleanup scenarios |
| tests/test_prepare.py | Modified | PRP-09 prune scenarios |
| tests/test_cli.py | Modified | parser/--help tests for new flags |
| README.md | Modified | --clean docs, sibling warning, --output anchoring |
| README_ES.md | Modified | Mirrored docs (prose translated, flags English) |

## Deviations
None — implementation matches design.md.

## Next
Ready for sdd-verify. PR to be created targeting dev.

## Artifacts
- Engram topic: sdd/feat-publish-clean-and-prune-orphans/apply-progress
- Filesystem: openspec/changes/feat-publish-clean-and-prune-orphans/apply-progress.md
- Tasks: openspec/changes/feat-publish-clean-and-prune-orphans/tasks.md (all [x])
