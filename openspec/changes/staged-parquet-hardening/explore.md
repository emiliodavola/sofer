# Exploration: staged-parquet-hardening

Combines two follow-up issues from #60 (carried as documented residuals in
`archive/2026-08-26-staged-parquet-stem-collision/archive-report.md` § "Residuals
Carried"):

- **#63 (bug)** — case-only-differing remotes collide on case-insensitive filesystems.
- **#64 (enhancement)** — warn on unreadable/corrupt staged Parquet, not just missing.

All line numbers below are from the post-#62 branch `fix/staged-parquet-hardening`.

## Current State

### `src/sofer/repo_compliance.py` — `_build_schema_report_impl` (lines 406–645)

Relevant structure, exact post-#62 line numbers:

| Line(s) | What |
|---------|------|
| 19 | `from ._mirror import parquet_remote_for, planned_remotes` |
| 438 | `_warn_duplicate_remotes(cfg)` — first statement of the impl |
| 447 | `_warned_missing: set[str] = set()` — the RC-R14 warn-once set |
| 449 | `for entry in cfg.files:` |
| 450 | `remote = entry.remote.lower()` — eligibility gate lowercases |
| 451 | `if entry.recursive or not remote.endswith(".csv"): continue` |
| 456 | `if not entry.include_in_schema: continue` |
| 469 | `if staging_dir is not None and not entry.upload_as_csv:` |
| 470 | `parquet_key = parquet_remote_for(entry.remote)` — **case-preserving key** |
| 471 | `candidate = staging_dir / PurePosixPath(parquet_key)` |
| 472 | `if candidate.exists():` → `use_parquet = True` |
| 476–483 | `elif parquet_key not in _warned_missing:` → RC-R14 `[!]` print |
| 488 | `parquet_result = _read_parquet_sample(parquet_path)` |
| 489–491 | `if parquet_result is None: use_parquet = False` — **silent CSV fallback** |
| 499, 562 | `row_counts.setdefault(entry.remote, ...)` — verbatim remote keying |

### `_read_parquet_sample` (lines 346–380)

`except Exception: return None` (lines 379–380). It does **not** distinguish
"absent" from "unreadable" — it only tries `pq.ParquetFile(parquet_path)`
(line 357) and swallows every failure, discarding the exception. It is called
at exactly one site (line 488).

### `_warn_duplicate_remotes` (lines 383–403)

Keys on the **exact** `entry.remote` string (`seen[entry.remote]`, line 397).
It warns only when two `[[file]]` entries declare the *verbatim-identical*
remote. It does **not** case-fold, so it does NOT cover case-only-differing
remotes. Its concern is row-count keying (verbatim-remote `setdefault`), not the
staged-Parquet key.

### `src/sofer/_mirror.py` — `parquet_remote_for` (lines 53–72)

Case-**preserving**, confirmed by both the docstring (line 62: "Case is
preserved — callers gate eligibility via `.lower()` themselves") and the unit
test `test_case_preserving` (`test_mirror.py:96–98`,
`"Data/PROV/Train.CSV" → "Data/PROV/Train.parquet"`). No case-folding exists
anywhere in the derivation. `planned_remotes` (lines 75–109) lowercases only for
the `.csv` eligibility check, then calls `parquet_remote_for` case-preserving.

### Writer/reader agreement on case

- Writer: `prepare.py:709–710` — `parquet_remote = parquet_remote_for(original_remote)` then
  `copy_to_mirror(parquet_path, output_dir, parquet_remote)`. Case-preserving.
- Reader: `repo_compliance.py:470–471` — same helper, case-preserving.
- Publisher: `publish.py:479–483` — same helper, case-preserving.

Both sides derive the SAME case-preserving key, so they agree. But on a
case-insensitive filesystem the two *distinct* keys `A.parquet` and `a.parquet`
resolve to the SAME physical file: the collision is a **real data-integrity
hazard** that happens first at prepare staging (writer), then silently at the
schema-report consumer.

## Affected Areas

- `src/sofer/repo_compliance.py` — the only file that needs to change for #63 and #64
  (detection + new warning, both inside `_build_schema_report_impl`; `_read_parquet_sample`
  needs to surface the exception class).
- `src/sofer/_mirror.py` — **no change required**. `parquet_remote_for` stays case-preserving
  by contract; the case-fold is detection-only and lives at the call site.
- `tests/test_repo_compliance.py` — new scenarios (see Test Inventory).
- `tests/test_mirror.py` — unchanged; `test_case_preserving` remains load-bearing and must
  keep passing.
- `openspec/specs/repo-compliance/spec.md` — RC-R14 (§4.15) will gain a new scenario (or a new
  requirement RC-R16) for #64; a new requirement for #63.

## Approaches

### Issue #63 — case-collision detection

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **A. Case-fold only the detection set** — add `_seen_parquet_keys: dict[str, str]` mapping `parquet_key.casefold()` → first verbatim key; warn when a later entry case-folds to an existing key but its verbatim key differs | Zero impact on actual staging path/upload; additive; preserves HF repo case; matches fix direction ("not necessarily the actual path") | Must guard against double-warning exact duplicates (already handled by `_warn_duplicate_remotes`) | Low |
| B. Case-fold the actual path (change `parquet_remote_for`) | Would make writer and reader agree on a single canonical key | Changes HF repo paths; breaks `test_case_preserving`; alters prepare/publish output; rejected by issue text | Med |
| C. Detect at prepare staging (writer) instead | Catches collision at the source | Out of #63's stated scope (the warn-once set in the schema report); writer is on the prepare hot path | Med |

**Recommendation: A.** The detection point is immediately after line 470
(`parquet_key = parquet_remote_for(entry.remote)`), keyed on `parquet_key.casefold()`.
The warning names both remotes. The guard — only warn when `parquet_key` differs
from the stored verbatim key (i.e. case-folded-equal but verbatim-unequal) —
prevents double-warning with `_warn_duplicate_remotes` for exact duplicates.

### Issue #64 — unreadable/corrupt warning

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **A. Add a warn-once at the read-failure branch (lines 489–491)** — new `_warned_unreadable: set[str]`; when `parquet_result is None`, print `[!]` naming `parquet_key` + exception class, then fall back to CSV | Directly matches RC-R14 / `_warn_duplicate_remotes` conventions; keeps CSV fallback (no hard error) | Requires `_read_parquet_sample` to expose the exception (today it discards it) | Low |
| B. Hard-error on unreadable Parquet | "Fails loud" | Contradicts #64's explicit "KEEP CSV fallback (no hard error)" | n/a |

**Recommendation: A.** `_read_parquet_sample` must be adjusted to surface the
failure class — either return the caught exception (change its `None` contract to
a richer `(None, exc)` or raise) or re-raise to the caller which wraps it. Since it
is called at exactly one site (line 488), the contract can change safely. The
warning should name both the key and the exception class, e.g.:

```
  [!] Staged Parquet '<parquet_key>' exists but could not be read (<ExceptionClass>); falling back to CSV inference.
```

Absent-vs-unreadable is already distinguished by the caller: RC-R14 fires at line
476 on `candidate.exists() == False` BEFORE the read; the unreadable branch
(line 489) is reached only when the file existed but `pq.ParquetFile`/read threw.

## Recommendation

1. **#63**: add a case-folded detection set (`parquet_key.casefold()`) in
   `_build_schema_report_impl` right after line 470, emitting one `[!]` when two
   distinct verbatim keys case-fold to the same value. Keep the actual path
   (`parquet_remote_for`) case-preserving. Do NOT touch `_mirror.py`.
2. **#64**: surface the exception class from `_read_parquet_sample`, and add a
   warn-once (`_warned_unreadable: set[str]`) at the line 489–491 branch with the
   same deterministic, non-raising convention, then fall back to CSV.
3. Both warnings key on `parquet_key` (missing uses `_warned_missing`; unreadable
   uses `_warned_unreadable`; collision uses the case-folded set) — three
   disjoint concerns, no cross-talk.

## Edge Cases

- **Both warnings for the same entry** — impossible for a single entry (absent XOR
  present, enforced by `candidate.exists()` branching at 472/476 vs 488/489).
- **Order determinism** — all three warning loops iterate `cfg.files` in declaration
  order; first declaration wins the warn-once slot (matches existing tests 2297, 1992).
- **`include_in_schema=false`** (line 456) — `continue` before parquet resolution →
  warning-free. ✓
- **`recursive`** (line 451) — `continue` before. ✓
- **`upload_as_csv`** (line 469) — skips the parquet branch entirely → warning-free. ✓
- **Empty/`None` remotes** — `remote` is a required `str` (model.py:68); the
  `.endswith(".csv")` gate (line 451) excludes empty remotes before
  `parquet_remote_for` is ever called. `_warn_duplicate_remotes` iterates ALL files
  (line 396) including empty remotes, but that is pre-existing and out of scope.
- **#63 double-warning guard** — exact-duplicate remotes (`A.csv` twice) are already
  warned by `_warn_duplicate_remotes`; the new case-fold detector MUST skip when the
  verbatim keys are identical to avoid a redundant second warning. The guard condition
  is: `key.casefold() in seen and seen[key.casefold()] != key`.

## Test Inventory

Existing coverage:

- **RC-R14 missing warning** — `TestStagedParquetRemoteRelativeLookup` in
  `tests/test_repo_compliance.py`: `test_missing_parquet_warns_once_and_falls_back_to_csv`
  (1957), `test_missing_parquet_warns_once_per_unique_key` (1992),
  `test_present_parquets_stay_silent` (2014).
- **Duplicate-remote warning** — `test_duplicate_remote_warns_once_and_keeps_first`
  (2267), `test_duplicate_remote_warnings_in_declaration_order` (2297),
  `test_unique_remotes_stay_silent` (2321).
- **`parquet_remote_for` case-preserving** — `TestParquetRemoteFor.test_case_preserving`
  (`tests/test_mirror.py:96`).

New scenarios needed:

- **#63**: (S-a) two remotes differing only by case (`data/A/train.csv` +
  `data/a/train.csv`) → exactly one `[!]` naming both, no raise; (S-b) remotes
  differing by more than case stay silent; (S-c) exact-duplicate remotes do NOT
  produce a second collision warning (guard).
- **#64**: (S-d) present-but-corrupt staged Parquet → exactly one `[!]` naming the key
  and the failure class, then CSV fallback (no raise); (S-e) two entries sharing one
  corrupt key → one warning (warn-once); (S-f) present-and-readable stays silent
  (distinguish from corrupt).

## Risks

- **No `_mirror.py` change** — keeps `test_case_preserving` green and preserves HF repo
  casing, but means the case-collision is only *warned*, not *resolved*: the two CSVs
  still collapse into one physical Parquet on case-insensitive filesystems at prepare
  staging (writer). If full resolution is desired later, it belongs in `prepare.py:709`
  (staging) / `publish.py:479`, not this change.
- **`_read_parquet_sample` contract change** — it is called at exactly one site today,
  but any future caller must honor the richer failure contract.
- **`_warned_missing` blast radius** — it is a local variable inside
  `_build_schema_report_impl` only (lines 447/476/479); nothing outside consumes it, so
  changing/adding detection sets has no cross-module impact. `row_counts` keying
  (lines 499/562) is verbatim-remote and untouched by case-folding.

## Ready for Proposal

Yes — both issues have a single, low-effort, additive fix localized to
`src/sofer/repo_compliance.py`, with precise line-level fix points identified and
test scenarios enumerated. The orchestrator should proceed to `sdd-propose`, noting
that #64 likely updates RC-R14 (§4.15) with a new "unreadable" scenario and #63
adds a new requirement (suggest RC-R16).
