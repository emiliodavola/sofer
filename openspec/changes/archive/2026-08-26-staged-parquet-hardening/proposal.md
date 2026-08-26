# Proposal: Harden the staged-Parquet handshake

## Intent

Close two residuals from #60's staged-Parquet work. On case-insensitive
filesystems, two `[[file]]` remotes differing only by case derive distinct
`parquet_remote_for` keys that collapse onto one physical path, silently
corrupting data (#63). Separately, a present-but-unreadable staged Parquet
silently falls back to CSV with no signal (#64). #63 is resolved by refusal,
#64 by observability.

## Scope

### In Scope

- **#63** — reject two entries whose `entry.remote` case-folds equal while
  their verbatim remotes differ, with a deterministic error naming both
  colliding remotes. Fires early in config validation, before any staging write.
- **#64** — when a staged Parquet exists but fails to read, emit a deterministic
  `[!]` warning naming the parquet key and the failure class (corrupt/parse,
  io/permission, other), then fall back to CSV. Warn-once per key,
  declaration-order.

### Out of Scope

- Hash/suffix disambiguation of colliding keys.
- Changing `parquet_remote_for` case preservation (writer/reader/publisher keys
  stay as-is).
- Any behavior change for `include_in_schema=false`, `recursive`, or
  `upload_as_csv` entries.
- Hard-erroring on unreadable Parquet (#64 stays warn + CSV fallback).
- Resolving the writer-side overwrite in `prepare.py` staging (still reachable
  if `validate()` is bypassed).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-compliance` — ADDED **RC-R16** (#63 case-fold collision refusal) and
  **RC-R17** (#64 unreadable-parquet warning), continuing RC-R01–RC-R15
  numbering.

## Approach

- **#63**: add `_validate_case_fold_collisions(cfg) -> list[str]` in
  `src/sofer/_mirror.py` beside `_validate_remote_paths`; call it from
  `DatasetConfig.validate()` (model.py) so it runs in `_load_and_validate`
  before any staging. Detection case-folds `entry.remote` only — the actual
  `parquet_remote_for` path stays case-preserving. A guard skips
  verbatim-identical pairs so RC-R11's exact-duplicate warning is untouched.
- **#64**: change `_read_parquet_sample` to re-raise (stop
  `except Exception: return None`). At its single call site
  (`_build_schema_report_impl`) add `_warned_unreadable: set[str]`, catch,
  classify via `_classify_parquet_read_failure(exc) -> str`, print the `[!]`,
  then `use_parquet = False`.

**Delta spec implications**: RC-R16/R17 are additive. RC-R13 and RC-R14 need no
touch-up (case preservation and missing-warning semantics are unchanged). RC-R11
needs a clarifying note: verbatim duplicates warn (non-aborting), while
case-differing case-fold collisions are refused by RC-R16 (earlier, in
`validate()`).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | New | `_validate_case_fold_collisions` helper |
| `src/sofer/model.py` | Modified | `validate()` calls the collision helper |
| `src/sofer/repo_compliance.py` | Modified | `_read_parquet_sample` re-raises; `_warned_unreadable` + classifier + `[!]` |
| `tests/test_repo_compliance.py` | Modified | #64 scenarios S-d–S-f |
| `tests/test_splits.py` / `test_mirror.py` | Modified | #63 scenarios S-a–S-c |
| `openspec/specs/repo-compliance/spec.md` | Modified | RC-R16, RC-R17 deltas (at archive) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `_read_parquet_sample` contract change breaks future callers | Low | Single call site today; docstring documents new raise contract |
| RC-R11 vs RC-R16 boundary confusion | Med | Guard skips exact dups; spec phase states warn-vs-refuse boundary |
| Direct API callers bypass `validate()` | Low | `_warn_duplicate_remotes` still catches verbatim dups |

## Rollback Plan

Revert the commit on `fix/staged-parquet-hardening`. Both changes are additive
and isolated (one validation helper + one warning branch); no schema or on-disk
format changes.

## Dependencies

- Post-#62 `dev` base (branch `fix/staged-parquet-hardening`).

## Success Criteria

- [ ] Two case-differing remotes produce exactly one deterministic error naming
      both, and `prepare` exits 1 before staging.
- [ ] Present-but-corrupt Parquet emits one `[!]` naming key + failure class,
      then CSV fallback (no raise); readable Parquet stays silent.
- [ ] Exact-duplicate remotes still warn via RC-R11, not refuse.
- [ ] `test_case_preserving` still passes; `uv run pytest tests/ -q` green;
      `uv run mypy src/` clean.
