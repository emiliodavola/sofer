# Exploration: row-count-remote-keying (GitHub #57)

## Current State

### Collision mechanics confirmed in code

`_build_schema_report_impl()` (`src/sofer/repo_compliance.py:383`) collects exact
row counts in a single pass, keyed by **origin basename**:

- Parquet path (`repo_compliance.py:453`): `row_counts[origin_name] = pf.metadata.num_rows`,
  where `origin_name = f"{Path(entry.remote).stem}.parquet"` (derived from the **remote** stem).
- CSV path (`repo_compliance.py:514`): `row_counts[local.name] = len(rows)` (the **local**
  filename).

Two declared files sharing a basename (`data/a/data.csv` + `data/b/data.csv`)
both produce key `"data.csv"` — the second write silently overwrites the first,
and `num_examples = sum(row_counts.values())` undercounts (e.g. 30+40 → 40).

Note the keying is **already mixed**: parquet keys come from the remote stem,
CSV keys from the local filename. Same-basename collisions can also occur
*across* paths (local `x.csv` vs remote-stem-derived `x.parquet`).

### Call-site map (who produces/consumes row-count keys)

| Site | Role | Breaks if key changes? |
|---|---|---|
| `repo_compliance.py:453,514` | Producer (only writer) | n/a — this is the fix point |
| `prepare.py:714` | Only production caller of `build_schema_report_with_rows`; passes `row_counts` into `build_dataset_card(...)` | **No** |
| `repo_compliance.py:792-793` (`build_dataset_card`) | `sum(row_counts.values())` — **values only; keys never joined, displayed, or looked up** | **No** |
| `ColumnSchema.origin` (`repo_compliance.py:141`, rendered at `:922` Data Fields "File" column; used in `_dup_map`/`seen_names` duplicate-column warnings) | Display/provenance only. **No code joins `origin` against `row_counts` keys** | No — origin can stay basename-based for human-readable display |
| `tests/test_repo_compliance.py:1944,1964,1985,2020` | Assert exact dict contents (`{"d.csv": 5}`, `{"a.csv": 30, "b.csv": 40}`, `{"p.parquet": 5}`, `{"w.csv": 3}`) | **Yes — must update** |

Conclusion: the dict key is write-only metadata as far as production logic is
concerned; only `sum(values)` is consumed. Re-keying is a producer-side +
test-side change with zero card-rendering impact.

### Non-schema file categories (contribute NO row counts today)

From the loop guards in `_build_schema_report_impl`:

1. `entry.recursive == True` — recursive directory trees (skipped entirely).
2. Remote not ending `.csv` — including **declared native `.parquet` remotes**;
   these datasets always hit the `CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)`
   fallback even though parquet metadata would make their count free.
3. `entry.include_in_schema == False` — deliberately excluded columns/files.

Not skipped: `upload_as_csv` entries — they go through the CSV read path and
already get exact counts; the flag only disables parquet staging usage.

Costs of counting them: parquet metadata is free (`pq.ParquetFile.metadata.num_rows`);
CSV requires a full streaming read (`stream_csv(max_sample=None)`) — extra I/O
per excluded file; recursive trees require a directory walk plus per-file reads
(expensive, out of proportion).

Existing num_examples coverage: `TestNumExamplesFromRowCounts` (RC-R07,
`tests/test_repo_compliance.py:1920-2001`) — CSV exact, multi-file sum,
parquet-not-capped-by-sample, fallback. `tests/test_prepare.py` has no direct
num_examples assertions. Post-publish verification counts rows independently via
the loaded HF dataset (`verification.py:98-103`) — a separate mechanism, not a
pre-upload source.

### Interaction with #58 (config reload lifecycle)

Compliant already: every knob involved (`config.SCHEMA_SAMPLE_SIZE`,
`config.SCHEMA_DUP_THRESHOLD`, `config.CARD_FALLBACK_ROWS_PER_FILE`) is read
via `config.X` attribute access at call time inside the impl — nothing
row-count-related is frozen at import. No lifecycle work needed; just don't
introduce module-level constants in the fix.

## Affected Areas

- `src/sofer/repo_compliance.py` — `_build_schema_report_impl` (producer: key by `entry.remote`),
  docstrings of `_build_schema_report_impl`/`build_schema_report_with_rows`/`build_dataset_card`.
- `src/sofer/prepare.py` — consumer untouched (values-only); verify no key assumptions.
- `src/sofer/model.py` — no change expected (`FileEntry.remote` already exists).
- `tests/test_repo_compliance.py` — update 4 exact-dict assertions to remote-path keys;
  add regression fixture: `a/data.csv` (N rows) + `b/data.csv` (M rows) → distinct keys,
  `num_examples == N+M`.
- `openspec/specs/repo-compliance/spec.md` § 4.8 (RC-R07) — delta: keying semantics
  basename → remote path; retire the D7 collision caveat.
- Archive reference: `openspec/changes/archive/2026-08-17-publish-readme-bugs/design.md` D7
  documents the limitation being lifted.

## Approaches

1. **A — Key row counts by remote path** *(recommended)*
   - Change the two producer lines to `row_counts[entry.remote] = ...`
     (verbatim POSIX remote, matching how `planned_remotes`/`configs.data_files` render remotes);
     update docstrings + tests. Optionally emit a warning when two entries share a remote
     (hand-edited TOML can still collide; scanner dedups but doesn't validate).
   - Pros: minimal diff; unique by construction; zero production-consumer breakage;
     fixes the mixed local/remote-stem keying inconsistency too.
   - Cons: changes observable dict contents of a public-ish function (mitigated: internal tool,
     documented in delta spec, tests updated in same change).
   - Effort: Low.

2. **B — Tuple keys `(local_name, remote)`**
   - Preserves both identities per entry.
   - Pros: keeps provenance in the key.
   - Cons: ugly, harder to assert/debug, no consumer needs the tuple; provenance already lives
     in `ColumnSchema.origin`. No upside over A.
   - Effort: Low, but strictly worse ergonomics.

3. **C — Return structured records instead of dict**
   - E.g. `list[FileRowCount]` with `remote`, `origin`, `rows` fields.
   - Pros: richest provenance; cleanest long-term API.
   - Cons: changes the return type of `build_schema_report_with_rows`; consumer rewrite;
     overkill when the sole consumer sums values; A achieves correctness now.
   - Effort: Medium.

**Non-schema-files recommendation**: keep the D7 fallback policy in this change
(document the decision, satisfying acceptance criterion 3). Rationale: counting
`include_in_schema=false` or non-CSV entries adds full-file I/O during schema
reporting for data excluded from features; recursive trees need directory walks;
the fallback is deterministic, configured, and already tested. A worthwhile
follow-up (not this change): exact counts for concrete non-recursive entries
(parquet metadata is free; CSV one extra stream). Related known gap to document:
when *some* files produce counts and others can't, the card sums the partial
counts silently (undercount) rather than falling back — leave behavior, note it
in the design doc.

**Related latent bug surfaced (flag for proposal scope decision)**: the staged-parquet
lookup is flat-by-remote-stem (`staging_dir / f"{entry_stem}.parquet"`,
`repo_compliance.py:435`) while prepare.py stages converted parquets into the
mirror at full remote-relative paths (subdirectories included,
`prepare.py:708-710`). Subdirectory remotes therefore miss the staged parquet and
silently fall back to CSV reading, and two same-stem remotes map to the *same*
flat candidate path. Fixing the lookup to `staging_dir / remote.with_suffix(".parquet")`
naturally belongs alongside the remote-path keying fix; the proposal should decide
in-scope vs follow-up explicitly.

## Recommendation

Approach A (remote-path keys), keeping `ColumnSchema.origin` basename-based for
display, keeping the fallback policy for non-schema files (documented), and
treating the staged-parquet lookup path fix as either in-scope or an explicit
follow-up. Regression test per acceptance criteria: `a/data.csv` + `b/data.csv`
fixture asserting distinct keys and correct summed `num_examples`.

## Risks

- Public-ish API surface: dict key semantics of `build_schema_report_with_rows`
  change; mitigated by single production consumer being values-only and tests
  updated in the same commit.
- Hand-edited TOMLs with genuinely duplicated remotes will still overwrite
  (unvalidated precondition); optional low-cost mitigation: warn on duplicate remote.
- Partial-counts silent undercount for mixed schema/non-schema datasets remains
  by design (documented, not fixed here).
- Staged-parquet flat-stem lookup bug may confuse verification if left unfixed
  alongside this change.

## Ready for Proposal

Yes — proceed to `sdd-propose`. Tell the user: the fix is a low-risk two-line
keying change plus tests/spec updates; the open scope question for proposal is
whether the staged-parquet lookup fix rides along or is split into a follow-up.
