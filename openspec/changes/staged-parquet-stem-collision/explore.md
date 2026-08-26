# Exploration: staged-parquet-stem-collision (Issue #60)

> Research artifact — no source files were modified.

## Current State

### Important discovery: the write side is ALREADY hardened

Issue #60 describes two failure modes keyed on the bare filename stem. On the
current branch tip (`fix/staged-parquet-stem-collision`, clean tree, HEAD =
`349bceb`), the **conversion-write collision is already fixed**:

- `src/sofer/prepare.py:683-685` — each eligible CSV entry converts into a
  **per-entry temp subdir** (`tmpdir / str(idx)`), so `data/a/data.csv` and
  `data/b/data.csv` never compete for the same temp file even though
  `_convert_to_parquet` still names its output `{csv_path.stem}.parquet`
  (`prepare.py:293`) inside that unique subdir.
- `src/sofer/prepare.py:707-710` — each converted parquet is then staged into
  the mirror layout at its **remote-relative path**:
  `copy_to_mirror(parquet_path, output_dir,
  str(PurePosixPath(original_remote).with_suffix(".parquet")))`. Parents are
  created on demand (`_mirror.copy_to_mirror`, `_mirror.py:107-108`).

So the *producer* half of the handshake is correct and mirror-consistent.

### The bug that remains: the flat lookup (consumer half)

`src/sofer/repo_compliance.py` — `_build_schema_report_impl`:

```python
# :459
entry_stem = Path(entry.remote).stem
# :466-471
if staging_dir is not None and not entry.upload_as_csv:
    candidate = staging_dir / f"{entry_stem}.parquet"
    if candidate.exists():
        use_parquet = True
        parquet_path = candidate
        origin_name = f"{entry_stem}.parquet"
```

In the prepare flow, `staging_dir` is the mirror root `output_dir`
(`prepare.py:714-719`). Two concrete defects result:

1. **Nested remotes silently lose Parquet reading.** For
   `remote = "data/PROV/train.csv"`, the candidate is `output_dir/train.parquet`,
   which does not exist (the real file is at `output_dir/data/PROV/train.parquet`).
   The function falls back to CSV sample inference → the schema report loses
   exact Parquet dtypes / hf_dtypes / nullability, and row counts take the slow
   fully-read-CSV path instead of Parquet metadata. No error is raised — pure
   silent quality degradation.
2. **Cross-entry contamination for mixed layouts.** If a dataset declares BOTH
   `remote = "survey.csv"` (root) and `remote = "data/survey.csv"`, the nested
   entry's flat candidate `output_dir/survey.parquet` EXISTS — it is the root
   entry's converted file. Schema columns, dtypes, and the row count attributed
   to `data/survey.csv` describe the wrong file.

This matches issue #60's failure mode 2 ("both entries resolve to that single
candidate"); failure mode 1 (overwrite during conversion) is already resolved.

## Full inventory of staging-dir producers/consumers

| Site | Role | Layout used |
|---|---|---|
| `prepare._convert_to_parquet` (`prepare.py:293`) | writes parquet | bare stem, but into per-entry tmp subdir → safe |
| `prepare.prepare` steps 2/5 (`prepare.py:664-710`) | conversion + staging | per-entry tmpdir → remote-relative via `copy_to_mirror` |
| `prepare.prepare` step 6 (`prepare.py:714-719`) | passes `staging_dir=output_dir` to schema report | mirror layout |
| `repo_compliance._build_schema_report_impl` (`:459-471`) | **lookup — BUGGY** | flat `{stem}.parquet` |
| `prepare._check_local_overwrite` (`prepare.py:576`) | overwrite check | remote-relative (`PurePosixPath(...).with_suffix(".parquet")`) ✓ |
| `verification.verify_load_dataset` (`verification.py:47-87`) | loads whole tree via `datasets.load_dataset(str(staging_dir))` | layout-agnostic, unaffected |
| `publish.py` (`:233`, `:404` rglob, `:479`, `:524`) | reads planned parquets out of the mirror | remote-relative / rglob ✓ |
| `uploader.py` | no direct `staging_dir` usage; consumes the finished mirror layout | unaffected |

Conclusion: fixing the lookup in `repo_compliance.py` does not disturb any
other consumer — everything else is already remote-relative.

## Reusability of `_mirror.py` helpers

`_mirror.py` provides the canonical remote-path vocabulary:

- `planned_remotes()` (`_mirror.py:53-87`) derives
  `str(PurePosixPath(entry.remote).with_suffix(".parquet"))` for convertible
  CSVs (`:82`) — exactly the staging key we need for lookups.
- `copy_to_mirror()` (`_mirror.py:90-109`) is the writer counterpart.

The expression `str(PurePosixPath(entry.remote).with_suffix(".parquet"))` is
currently **duplicated in 5 places** (`_mirror.py:82`, `prepare.py:576`,
`prepare.py:709`, `publish.py:233`, `publish.py:479`). Per AGENTS.md rule 4
(no duplicated logic), the fix should extract a shared helper, e.g.
`_mirror.parquet_remote_for(remote: str) -> str`, and use it at every site —
including the new lookup.

## Edge cases analyzed

1. **Nested remotes (`a/b/c.csv`)** — target key `a/b/c.parquet`;
   `copy_to_mirror` already creates parents. Lookup must join all POSIX parts
   under `staging_dir` (`staging_dir.joinpath(*PurePosixPath(key).parts)`),
   not a single flat name.
2. **Backslashes in TOML remotes** — `PurePosixPath` treats `\` as a literal
   character, so `remote = "data\\a\\train.csv"` yields a one-component
   "directory-less" key, while `dest_root / remote` on a Windows `Path`
   interprets `\` as a separator when copying — writer and reader can diverge.
   Out of strict scope, but the proposal should either (a) normalize `\` → `/`
   when parsing remotes, or (b) add validation rejecting `\` in `remote`.
   Flagging as a follow-up hardening item.
3. **Entries without explicit remote** — impossible: `remote` is a required
   TOML key (`model.py:367`, `FileEntry.remote` has no default) and
   `scanner` always generates POSIX relative remotes
   (`tests/test_scanner.py:317`). No derivation-from-local path exists.
4. **Same remote declared twice** — `_warn_duplicate_remotes` already warns
   (`repo_compliance.py:400-403`) and row counts are first-wins via
   `setdefault` (fix #59). With remote-relative keys both duplicate entries
   resolve to the same candidate — behavior stays consistent, no new hazard.
5. **Non-CSV formats** — the schema impl only considers `.csv` remotes
   (`repo_compliance.py:450`); native `.parquet`, `upload_as_csv=True`
   entries, and recursive trees skip the Parquet branch entirely. Unaffected.
6. **Cleanup of old flat-layout files** — the temp staging dir is ephemeral
   (`shutil.rmtree(tmpdir)` in `finally`, `prepare.py:805-806`) and
   `output_dir` is user-managed/regenerated with `--force`. There is no
   persisted flat-layout state to migrate; only hand-written test fixtures
   place flat parquets.

## Existing tests covering the handshake

- `tests/test_repo_compliance.py::TestBuildSchemaReportParquet*` (~:548-655) —
  all use **root-level remotes** (`"survey.csv"`, `"ints.parquet"`, …) with
  flat fixtures; they keep passing after the fix because stem == remote at
  the root. This confirms backward compatibility of the new key.
- `TestBuildSchemaReportParquetFallback` (:658+) — no-staging / missing-parquet /
  `upload_as_csv` fallbacks remain valid semantics.
- Row-count tests :1971 (`test_same_stem_subdirectory_remotes_keep_distinct_counts`)
  exercise same-stem remotes via CSV fallback (no staged parquets) — unaffected.
- **Gaps needing new tests:** (a) nested remote + parquet placed at the
  remote-relative staging path → Parquet branch taken (dtypes from Parquet);
  (b) root + nested same-stem pair → each entry reads ITS OWN parquet
  (contamination regression test); (c) end-to-end `prepare` →
  `build_schema_report_with_rows` parity for a nested remote (schema report
  sees Parquet-derived types, row count equals Parquet metadata rows).
- `tests/test_prepare.py:116-117` already builds nested-remote configs
  (`data/PROV/train.csv`, `data/DPTO/train.csv`) — good scaffolding for (c).

## Spec impact (mandatory delta)

`openspec/specs/repo-compliance/spec.md:361-374` **explicitly specifies the
buggy contract**: "Look for `staging_dir / <stem>.parquet` (same stem as the
CSV file)" and origin prefixes like `"survey.parquet::age"`. The change MUST
include a repo-compliance delta spec updating:
- the Parquet-path resolution rule (remote-derived relative path);
- the origin/disambiguation label (recommend the POSIX remote-relative
  parquet path, e.g. `"data/survey.parquet"`, so same-stem files stay
  distinguishable in duplicate-column warnings — cosmetic but honest).

## Approaches

1. **Remote-relative staging key + shared helper (recommended)**
   Extract `_mirror.parquet_remote_for(remote)` (or equivalent), replace the
   flat lookup at `repo_compliance.py:459/467/471` with the remote-derived
   key joined under `staging_dir`, and reuse the helper at the 5 duplication
   sites. Update repo-compliance delta spec + tests.
   - Pros: aligns lookup with producer/mirror/publish vocabulary; kills the
     contamination and the silent-fallback defects at once; removes existing
     duplication; small diff.
   - Cons: changes `ColumnSchema.origin` strings for nested files (spec +
     possibly a few assertions).
   - Effort: Low/Medium.

2. **Keep flat key, make the writer flatten with mangled unique names**
   e.g. stage as `data__a__data.parquet`.
   - Pros: lookup stays flat/simple.
   - Cons: breaks mirror-layout consistency; publish/planned_remotes/
     overwrite-check all expect remote-relative paths; pollutes the HF repo
     layout; fights the architecture.
   - Effort: Medium (and architecturally wrong).

## Recommendation

Approach 1. Both handshake ends key on
`str(PurePosixPath(entry.remote).with_suffix(".parquet"))`, centralized in
`_mirror.py`. The write side already complies; only the lookup flips.

## Risks

- The current published spec mandates flat-stem lookup — verify phase will
  fail unless the delta spec ships in the same change.
- `origin` label change may ripple into duplicate-column warning assertions
  and card-rendering tests (audit before implementing).
- Backslash remotes remain an unresolved writer/reader divergence — propose
  normalization/validation as an explicit follow-up (or fold in if cheap).
- Issue #60's framing ("second overwrites the first") is stale on this
  branch; the proposal should restate the defect as flat-lookup miss +
  cross-entry contamination so tasks target reality.

## Ready for Proposal

Yes — proceed to `propose` with Approach 1, including the repo-compliance
delta spec and the three new test scenarios listed above.
