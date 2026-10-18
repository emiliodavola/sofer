# Feature: manifest-publishable-intermediate — issue #346

**Branch:** `fix/346-manifest-publishable-intermediate` from `dev@d07557e`
**Issue:** `emiliodavola/sofer#346` — *bug(publish): the artifact manifest declares profile/render artifacts that _copy_package never stages — the approved dry-run diff overstates the upload*
**Delivery PR:** pending — push and PR creation are the maintainer's decision
**SDD change:** `openspec/changes/archive/2026-10-18-fix-manifest-publishable-intermediate/` (archived inside this branch, AGENTS.md rule 15)
**Split-out issue:** #349 — the *other* half of #346 (publish re-derives the manifest instead of reading it) is not in this change
**Phase:** 3 of the 2026-10-18 batch (last: the only one with a format change). Rebased onto `dev@e23a6e8` after PR #351 merged, and the gate evidence re-taken there.

## Goal

`build/manifest.json` declares 135 artifacts on a corpus that delivers 133, because
`profile` and `render` entries sit in the same list as `parquet`, `card` and
`license`. They are intermediate layers that `_copy_package` never stages, and
nothing in the document says so — the classification PUB-12 demands exists only in
a module docstring. On top of that, the probe looks for the layers at
`<dataset root>/profiles`, while the pipeline writes them under the artifact cache
(`cache/profiles`, `profile.py:264-270`), so the entry is always an `optional`
directory placeholder that describes a location that does not exist.

## Specs

S1 — #346 `## Expected behaviour` (verbatim): "One of: `_copy_package` stages the
declared `profile`/`render` artifacts (they are regenerable from `cache/`), so the
manifest and the delivery agree; or the manifest stops declaring them as package
artifacts, if they are local-only by design — the delivery set should be the
delivery set; or the dry-run diff marks them as local-only, so the operator is not
told they will be uploaded."

S2 — `openspec/specs/publish/spec.md` PUB-12 (verbatim), which already decides the
direction of S1: artifacts "classified as **publishable** (parquet incl. multi-sheet
expansion, csv when keep_csv, README, LICENSE, codebook.md, codebooks/\*\*) or
**intermediate** (profiles, renders, per-sheet intermediates, schema/card inputs)",
and the scenario "GIVEN a single-CSV dataset and a fresh prepare … AND
profiles/renders present in the tree SHALL be `intermediate` (never publishable)".

S3 — maintainer decision, 2026-10-18 (verbatim): "3. explicito" — the
classification is an explicit `classification` field in the manifest JSON, not an
allowlist the consumer has to keep in its head.

S4 — #346 `## Summary` (verbatim): "`build/manifest.json` declares **135** package
artifacts. `_copy_package` can stage **133** of them."

S5 — #346 `## Impact` (verbatim): "the direction of the error is what makes it
worth fixing: it **overstates** the delivery."

## Tasks

| # | Task | Spec | Commit |
| --- | --- | --- | --- |
| T1 | `ArtifactClass` enum (`publishable`/`intermediate`) carried by every entry, in the JSON and in `from_dict` with a backward-compatible default | S2, S3 | `b8c5e9d` |
| T2 | `PackageManifest.publishable()` / `.intermediate()` / `.delivered()` selectors; only `delivered()` is the delivery set | S1, S4 | `b8c5e9d` |
| T3 | Probe the layers where they are actually written (artifact cache), keeping the dataset-root location working | S1 | `b8c5e9d`, `7bde2b9` |
| T4 | Tests: every entry classified, delivered == staged, the cache probe, the root fallback, and an old manifest without the field | S1-S5 | `b8c5e9d`, `7bde2b9` |
| T5 | PUB-12 spec clause (field + probe + delivered identity) in the delta and the canonical spec, plus the archive report | S1-S3 | `c87a43c`, `bc67a3c` |
| T6 | Gates: pytest 2495/9 on `dev@e23a6e8`, the four core modules at 100.00%, ruff, mypy, pyright, mapping checker | — | `b8c5e9d`, re-taken after `bc67a3c` |
| T7 | A recursive tree is a directory entry with a trailing slash, never a delivered file (found by the independent verifier) | S1, S4 | `e565331`, `bc67a3c` |

## Log

**L1** — maintainer request (verbatim): "revisá los issues de tipo bug y armate un
roadmap de implementación"

**L2** — maintainer decisions (verbatim): "1. sí incluir cli.py / 2. ambos / 3.
explicito / abrí los issues también"

**L3** — evidence and corrections to the report: the printed dry-run diff does **not**
come from the manifest (`_repo_diff_summary` derives from `expanded_planned_remotes`;
the only manifest input is `required_missing()`, `publish.py:453-457`), so the
overstatement lives in `build/manifest.json` — the document the operator or agent
reads — not in the diff. The reported entries were `optional` directory
placeholders, not `staged` file lists, because of the wrong probe root.

**L4** — scope boundary: `publish.py` needs no change, because `required_missing()`
is the only manifest reader in the delivery path and intermediate entries are never
`missing`. The other half of #346 — `publish` re-deriving its own manifest instead
of reading the one `prepare` wrote — is issue #349, deliberately not folded in here.

**L5** — measured before/after with a scratch probe against the pre-fix module:
declared 7 entries, `classification` absent, `profile='profiles/'`/`optional` and
`render='renders/'`/`optional` while both layers sat in `cache/`. After: the same
entries classified, both layers staged at `cache/<dir>/<file>`, and
`delivered() == the 4 files _copy_package stages`.

**L6** — a defect of my own, caught by that probe before the commit: the first
version made `publishable()` the delivery set, which over-declared exactly like
#346 (`publishable 5` against `staged 4`) because an absent optional `codebook.md`
is publishable in principle. Added `delivered()` (publishable AND staged) and pinned
it against the real copy-path output in `test_delivered_set_is_the_staged_set`.

**L7** — test-first did not hold for this unit: the implementation came before the
tests, and the first RED (`ImportError: cannot import name 'ArtifactClass'` at
collection) was too weak to be the carrier, so the probe in L5 is. Recorded as a
deviation in the archived `tasks.md` and in the archive report.

**L8** — rebase and final evidence: PR #351 merged into `dev` as `e23a6e8`; `b8c5e9d`
was rebased onto it (clean) and the battery re-taken there. One commit attempt was
aborted by a pre-commit/hook stash conflict (the ruff-format hook rewrote a line also
present in pre-commit's stash); recovery was to stage the formatted version, never
`--no-verify`.

**L9** — independent verification round (the native `assess` was unavailable:
`package-local-binary-missing`, `changedPaths: 0`, so it said nothing about the
candidate). Verdict: backward compat PASS (with the legacy `profile`/`render` default
caveat, now stated in PUB-12), consumers PASS in code but with **doc drift** in
`openspec/specs/prepare/spec.md` (PRP-11 still listed four keys), probe-cannot-crash
PASS with the `except ValueError` branch **uncovered in the commit**, blocking rule
PASS, and `delivered() == staged` **FAIL**: on recursive remotes the manifest holds
one entry per tree, so `delivered()` listed `assets` and an empty `empty` while the
copy path staged `assets/a.txt` and `assets/nested/b.txt`. My claim came from a
non-recursive fixture and was over-general.

**L10** — what the FAIL changed: `e565331` records a recursive remote's path with a
trailing slash (the marker `codebooks/`/`profiles/`/`renders/` already used), adds
`ManifestEntry.is_directory`, excludes directory entries from `delivered()`, and pins
the case with a populated tree plus an empty tree; `bc67a3c` narrows the claim to
"publishable AND staged AND a file path" in the canonical spec, the delta and the
design, and fixes the PRP-11 drift. Re-measured: `delivered()` = `['LICENSE',
'README.md']`, entries `assets/` and `empty/`, staged files unchanged. The verifier
also flagged that it saw the tree change mid-run (I was editing while it read);
verification now targets a frozen commit.

**L11** — a mistake of mine while checking coverage: `coverage run --branch -m pytest
tests/test_manifest.py` (a subset) overwrote `.coverage`, so the coverage-contract
guard failed a clean suite with `profile.py measured 52.7%`. `.coverage` is gitignored,
so nothing reached the repo; repaired by re-running the full suite under coverage.
Subset measurements here must use `coverage run --data-file=<scratch>`.

**L12** — final evidence after the fix, on `dev@e23a6e8`: manifest tests 14 passed,
suite `2495 passed, 9 skipped` (2476 + 7 from #345 + 5 from #348 + 7 from this
change), the four core modules at 100.00% with exit 0 each, TOTAL 94% (7686 stmts),
ruff/mypy/pyright clean, `check_test_mapping.py` OK. Commits: `b8c5e9d`, `c87a43c`,
`5c3925e`, `7bde2b9`, `e565331`, `bc67a3c`, plus the closeout commit for this report.
