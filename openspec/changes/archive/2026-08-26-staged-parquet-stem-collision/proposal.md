# Proposal: Fix staged-parquet staging lookup (remote-relative keys)

## Intent

Fix GitHub #60's *remaining* defect. The conversion-write side is already
hardened (`prepare.py` stages each Parquet into a per-entry tmpdir and copies it
to the mirror at its remote-relative path). What remains broken is the consumer:
`repo_compliance._build_schema_report_impl` (:459-471) looks up staged Parquets
as a **flat `{stem}.parquet`** under `staging_dir`. Consequences:

1. **Nested remotes silently lose Parquet reading** — `data/PROV/train.csv`
   looks for `train.parquet` at the mirror root, misses the real
   `data/PROV/train.parquet`, and falls back to CSV inference (dtype/nullability
   loss; slow CSV row counting).
2. **Cross-entry contamination** — root `survey.csv` + nested `data/survey.csv`
   both resolve to the root's staged file; one entry reports the other's schema
   and rows.

Issue #60's framing ("second conversion overwrites the first") is stale on this
branch; the defect is the flat lookup plus contamination.

## Scope

### In Scope

- Extract shared helper `_mirror.parquet_remote_for(remote: str) -> str`
  (`str(PurePosixPath(remote).with_suffix(".parquet"))`) and adopt it at all
  seven adoption sites — the 6 duplication sites (`_mirror.py:82`,
  `prepare.py:364`, `prepare.py:576`, `prepare.py:709`, `publish.py:233`,
  `publish.py:479`) plus the fixed flat lookup in `repo_compliance.py`
  (inventory corrected per design § Technical Approach).
- Lookup resolves all POSIX parts under `staging_dir`
  (`staging_dir.joinpath(*key.parts)`).
- `origin` label becomes the remote-relative posix path
  (`a/b/data.parquet`), keeping same-stem entries distinguishable in warnings;
  update affected test assertions.
- Missing expected staged Parquet → WARNING + CSV fallback (no hard error),
  following the deterministic-warning convention from #59
  (`_warn_duplicate_remotes` pattern).
- Backslash normalization: TOML remotes containing `\` are normalized to `/`
  consistently on writer AND reader sides, with tests.
- MODIFIED delta spec for `repo-compliance` (§ 3.3.3 step 2a / § 3.3.3 step 3).
- New tests: (a) nested remote reads its own Parquet; (b) root+nested same-stem
  pair → no contamination; (c) prepare→schema-report parity for nested remotes;
  (d) missing-Parquet warning + CSV fallback; (e) backslash remotes round-trip.

### Out of Scope

- Migration of any persisted artifacts (none exist — staging temp dirs are
  ephemeral; `output_dir` is user-regenerated).
- Behavior changes to `verification.py` / `uploader.py` (layout-agnostic,
  unaffected per exploration).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-compliance`: Parquet-path resolution changes from flat
  `{stem}.parquet` to remote-derived relative key; `origin` prefix becomes the
  remote-relative posix parquet path; a deterministic warning is emitted on
  fallback. Current spec (`openspec/specs/repo-compliance/spec.md:361-374`)
  mandates the buggy contract — delta is mandatory.

## Approach

Adopt exploration Approach 1: both handshake ends key on the centralized
`parquet_remote_for(remote)` value. Write side needs no behavioral change
(already compliant); flip the lookup, centralize the duplicated expression, add
warning + backslash handling, ship the delta spec and tests together so verify
passes against the updated contract.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | Modified | Add `parquet_remote_for()` helper |
| `src/sofer/repo_compliance.py` | Modified | Remote-relative lookup + origin label + fallback warning |
| `src/sofer/prepare.py` | Modified | Use helper (:576, :709); normalize backslashes |
| `src/sofer/publish.py` | Modified | Use helper (:233, :479) |
| `openspec/specs/repo-compliance/spec.md` | Modified | Via delta spec in this change |
| `tests/test_repo_compliance.py`, `tests/test_prepare.py`, `tests/test_mirror.py` | Modified/New | Scenarios (a)-(e) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Verify fails without delta spec | High | Delta ships in same change |
| `origin` label ripples into warning/card assertions | Medium | Audit tests during tasks phase |
| Backslash normalization diverges writer/reader | Low | Shared helper + round-trip test |

## Rollback Plan

Revert the change branch commits; no persisted state exists to migrate, and the
write side is untouched behaviorally. Gitflow: work stays on
`fix/staged-parquet-stem-collision`, PR targets `dev`.

## Success Criteria

- [x] Nested-remote entries read their own staged Parquet (exact dtypes, Parquet-metadata row counts)
- [x] Root+nested same-stem entries show zero cross-contamination
- [x] Single definition of the remote→parquet-key expression (7 adoption sites: 6 duplication sites + 1 flat lookup; see design's inventory correction)
- [x] Deterministic warning emitted when staged Parquet is missing; CSV fallback preserved
- [x] Backslash remotes behave identically on writer and reader sides
- [x] Full suite green: `uv run pytest tests/ -q`; `uv run mypy src/` clean
