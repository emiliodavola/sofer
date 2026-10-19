# Feature: manifest-authority — issue #349

**Branch:** `fix/349-manifest-authority` from `dev@47bf12c`
**Issue:** `emiliodavola/sofer#349` — *bug(publish): build/manifest.json is a prepare-time snapshot nothing refreshes, while publish re-derives its own — PUB-12 "read the SAME manifest" never holds*
**Delivery PR:** pending — push and PR creation are the maintainer's decision
**SDD change:** `openspec/changes/2026-10-19-fix-manifest-authority/`, archived inside the delivery PR (AGENTS.md rule 15)
**Decision (B):** the durable manifest is refreshed at the end of every phase that adds a package artifact, and `publish` reads it
**Risk:** item 3 — the manifest JSON and *which object the delivery rests on* are contracts a human and an agent already consume

## Goal

`build/manifest.json` is the auditable description of the package (`model.py:307`,
`_clean.py:75`), but it is a prepare-time snapshot: `prepare` is its only writer
(`prepare.py:698-701`), and `publish` ignores the file and rebuilds its own manifest
in memory (`publish.py:854-858`). On the canonical chain (`mcp_server.py:16`)
`prepare` runs before `codebook_all`, so the file on disk declares `codebooks/`
`optional` while the delivery contains the pages; `PackageManifest.from_dir`
(`manifest.py:143`) has no caller and no test. PUB-12 — "publish dry-run and confirm
SHALL read the SAME manifest to plan and to enforce contents (no divergence)" — never
holds, and after #346 the same requirement both demands reading that manifest and
sanctions rebuilding it.

## Specs

S1 — #349 `## Expected behaviour` (verbatim): "One of: `publish` reads
`build/manifest.json` and treats it as the object of record, with an explicit
staleness rule (mtime relative to the newest generated artifact) that fails closed
with a stable `error_code` and the correct recovery — this is what PUB-12 literally
says; or the pipeline refreshes the durable manifest at the end of every phase that
adds a package artifact, so the file on disk is always the current one and `from_dir`
becomes the reader; or PUB-12's text is amended to say the manifest is recomputed and
the file is a prepare-time checkpoint — in which case the file SHALL be labelled as
such, so no reader mistakes it for the delivery set."

S2 — maintainer decision, 2026-10-19 (verbatim): "opcion B" — the second branch of
S1. Instruction (verbatim): "versioná los cambios en rama aparte".

S3 — `openspec/specs/publish/spec.md` PUB-12 (verbatim): "`prepare` writes the
manifest into the output dir; publish dry-run and confirm SHALL read the SAME
manifest to plan and to enforce contents (no divergence)."

S4 — `openspec/specs/prepare/spec.md` PRP-11 (verbatim): "The manifest is the single
source of truth consumed by publish dry-run and confirm."

S5 — derived from S2/B (invariant): after any phase that adds a package artifact to
`output_dir`, `PackageManifest.from_dir(output_dir)` SHALL equal
`build_package_manifest(cfg, output_dir)`.

S6 — derived from S2/B (who refreshes): every phase that adds package artifacts SHALL
refresh the durable manifest of the package dir it wrote to. `prepare` SHALL create
it; a later phase SHALL refresh it **only where one already exists**, so no phase
invents a package record for a tree `prepare` never prepared.

S7 — derived from S2/B (who reads): `publish` SHALL read the durable manifest
(`from_dir`) when present, SHALL fail closed with a stable `error_code` and a
truthful recovery when it is older than the newest artifact it declares, and SHALL
recompute with an explicit notice when it is absent (a package prepared before this
change).

S8 — derived from S2/B (record): the PUB-12 internal contradiction (paragraph 1
demands reading the same manifest; the #346 scenario sanctions rebuilding it) SHALL
be reconciled in the canonical spec, and the CLI help, the recovery text and
`README.md`/`README_ES.md` SHALL describe the object actually enforced (AGENTS.md
rules 7 and 13).

## Tasks

| # | Task | Spec | Commit |
| --- | --- | --- | --- |
| T1 | RED first: after `codebook_all` on a prepared tree, the durable manifest must equal the rebuild. Then `write_manifest()` in `manifest.py`, and `prepare` writes through it | S4, S5 | `d05acd4` |
| T2 | Refresh at the post-prepare phase boundaries: `codebook_all` (CLI + MCP), `profile_all`, `render_all` | S5, S6 | `d05acd4` |
| T3 | `publish` reads `from_dir`; staleness fails closed with a stable code and the truthful recovery; legacy tree recomputes with a notice | S3, S7 | `3ed11cf` |
| T4 | Tests: per-phase invariant, legacy tree without the file, stale manifest blocks, plus one regression test per existing command the change touches | S5-S7 | `3ed11cf` |
| T5 | Specs: reconcile PUB-12, update PRP-11, add the scenarios and the change folder archived inside the PR | S8 | `57dd0a7` |
| T6 | Docs: recovery text and CLI help name the real recovery; `README.md` + `README_ES.md` in the same commit | S8 | `57dd0a7` |
| T7 | Gates: suite, the four 100.00% core modules with zero pragmas, ruff, mypy 3.13, pyright, `check_test_mapping.py`, and the differential check of every command sharing the changed code against the base commit | — | closeout commit |

## Out of scope (found while verifying #349 — recorded, not implemented here)

- **The `! MISSING` rows are unreachable.** `publish.py:446-459` nests them under
  `if modified:`; the dry-run path is the only one that passes a manifest and it
  passes `existing_files=[]` (`publish.py:867-876`), so `modified` is always empty,
  while the confirm path passes no manifest at all (`publish.py:975-983`). The plan
  the human approves therefore never discloses the required-missing artifacts. Its
  only "evidence" is a unit test that injects existing files
  (`test_publish.py:2015`). Separate issue.
- **`codebooks_required` is dead in production.** `publish.py:768` defaults it to
  `False` and no caller passes `True` (`cli.py:194-204`, `mcp_server.py:1606`,
  `:1845`), so a missing `codebook_page` can never block. Separate issue.
- **PUB-12's "stable `error_code`" clause is already drift.** `sofer_publish_confirm`
  returns `{"ok": rc == 0, "exit_code": rc, "output": ...}` with no `error_code`
  field (`mcp_server.py:1860-1868`), so the pre-existing required-missing block has
  never carried one either. This change does not invent the field and does not claim
  it: the stale refusal's stable token is the printed marker inside `output`.
  Reconciling the clause itself is a separate issue.

## Log

**L1** — maintainer request (verbatim): "revisá el issue #349 y analizá si corresponde
o si es correcta su descripción y armate un roadmap de implementación usando ODD
exclusivamente"

**L2** — maintainer decision (verbatim): "opcion B", plus "versioná los cambios en
rama aparte". B is the second branch of S1: refresh the durable manifest at the end
of every phase that adds a package artifact, so the file is always current and
`from_dir` becomes the reader.

**L3** — verification of #349 against `dev@47bf12c` (5 corrections to the issue, all
recorded before implementing): (1) the "109 vs 209" figure does not exist anywhere in
the repository and the counting half it describes was fixed by #346 (its own record:
135 declared / 133 delivered); (2) the cited `path:line` values drifted
(`from_dir` is `manifest.py:143`, the rebuild is `publish.py:854-858`); (3) the
"publish blocks with the wrong recovery" example is unreachable, because nothing
passes `codebooks_required=True`; (4) PUB-12's staleness clause keys on the real
config path, so S1's first branch *adds* a rule rather than implementing one; (5) #346
strengthened the case by amending the same requirement to say a consumer needing the
true class "SHALL re-derive by rebuilding the manifest (`publish` does)" — the
requirement now contradicts itself.

**L4** — why B and not A or C: A (publish reads the file, fail-closed) blocks the
canonical chain by construction, because `prepare` runs before `codebook_all`, so the
file is always older than the pages — it collapses into B plus a failure mode. C
(amend PUB-12, label the file a checkpoint) is the smallest diff but leaves the
auditable document unable to answer "what will be published". B makes the document
true and turns S5 into an executable invariant: one test fails when a future phase
forgets to refresh.

**L5** — T1+T2 landed as `d05acd4`: `write_manifest()` and `refresh_manifest()` in
`manifest.py`, `prepare` writing through the writer, and the refresh call at the end of
`codebook_all`, `profile_all` and `render_all`. RED was observed before the helper
existed: `assert durable == build_package_manifest(cfg, out)` failed on the
`codebook_page` entry that stayed `optional` while the pages were on disk. GREEN is 15
passed, with ruff/mypy/pyright green in the pre-commit hooks.

**L6** — the writer delegation for T3 was refused three times by the harness
(`Writer session Git authority changed before admission`), repeated after verifying
clean Git state (single worktree, HEAD `d05acd4`, no index or hook locks) and after
changing the task label to force a fresh writer session. Delegation is unavailable for
this session, so T3 was implemented inline by the parent; a refused delegation is
reported, never retried into ceremony.

**L7** — T3 held test-first: the six `TestDurableManifest` tests were written before the
implementation and observed RED as real assertion failures, never as a collection
error. The strongest is the discriminator
`test_an_entry_only_the_file_declares_blocks_the_confirm`: a ghost `missing` entry
exists only in the durable document, so a recount cannot see it, and before the change
the run proceeded all the way to the upload (the offline `upload_folder` spy raised
`AssertionError: network call attempted`) instead of blocking with the manifest
message.

**L8** — one existing test needed a fixture adjustment, not a code change:
`TestAutoPrepare::test_up_to_date_skips_prepare` moves `data.parquet` to a future mtime
to prove the auto-prepare signal, which after this change is *also* a genuinely stale
record. The record's mtime moves with the artifact, so the fixture keeps describing the
up-to-date package it was written about while still testing that signal. The staleness
check's placement is what makes the refusal safe: it runs after the auto-prepare block
and before the quality gate, the `HfApi` construction, the remote prologue and staging.

**L9** — a test-authoring defect of mine, caught by the first GREEN attempt: the entry
helper's fifth positional parameter is `status`, and one case passed `"intermediate"`
there, so the manifest failed to decode (`ValueError: 'intermediate' is not a valid
ArtifactStatus`) before any assertion ran. Fixed by naming the parameter
(`classification="intermediate"`).

**L10** — S7 inherited "a stable `error_code`" from #349's own expected behaviour, and
the transport does not have one: `sofer_publish_confirm` returns `ok`, `exit_code` and
`output` only (`mcp_server.py:1860-1868`), exactly as the pre-existing required-missing
block has always done. Rather than adopt a word that promises a field nothing emits,
the implementation and both spec texts say **marker**: `STALE_MANIFEST` printed in the
block, carried to an agent inside the envelope's `output`. The drift in PUB-12's own
`error_code` clause is recorded as out of scope, not silently rewritten.

**L11** — final evidence on the frozen tree, from the repo root:

- `uv run coverage run -m pytest tests/ -q` → `2504 passed, 9 skipped, 6 warnings in
  118.45s` (base `dev@47bf12c`: 2495/9 → +9: six cases in `tests/test_publish.py`,
  three in `tests/test_manifest.py`).
- the four rule-14 gates, each at `--fail-under=100` → **exit 0**: `cli` 741 stmts,
  `scanner` 196, `prepare` 342, `publish` 413; `coverage report -m` TOTAL **94%**
  (7731 stmts) against the config-owned floor of 90.
- `uv run python scripts/check_test_mapping.py` → `OK: test-mapping contract holds`,
  exit 0, with `publish` at 65 scenarios (was 60) and `prepare` at 46 (was 45), both
  remaining in the permanent declared backlog because neither carries a
  `## Test Mapping` table.
- `uv run ruff check src/ tests/ scripts/` → All checks passed;
  `ruff format --check src/ tests/` → 79 files already formatted.
- **Differential check** against base `47bf12c`, both sides run in the SAME fixture
  directory wiped and recreated between passes: **6/6 IDENTICAL** in stdout+stderr and
  exit code — `prepare`, `codebook --all-files --config`, `profile --all-files`,
  `render --all-files`, `publish --dry-run`, `publish --target local --output ./out`.
  No difference nobody asked for.

**L12** — two harness defects of mine, caught because the first differential result was
not trusted: (1) the first pass ran each side in its own directory, so five commands
"DIFFERED" only by the side's absolute path — a false positive, never a regression;
(2) `codebook dataset.toml --all-files` exited 1 on BOTH sides
(`--all-files cannot be used with a positional file argument`), so that row proved
nothing about the codebook refresh path. Fixed by running both sides in one reset
directory and invocating the batch form as `codebook --all-files --config dataset.toml`.
The `sed`-based path normalization I tried first did not substitute on file input in
this environment; it was abandoned in favour of removing the path difference at the
source, rather than debugged into the evidence.

**L13** — closeout: the change folder moved to
`openspec/changes/archive/2026-10-19-fix-manifest-authority/` inside this branch
(AGENTS.md rule 15) together with its `archive-report.md`, which carries the verbatim
gate evidence, the six deviations and the three findings recorded as out of scope.
Commits on `fix/349-manifest-authority` from `dev@47bf12c`: `d05acd4` (the refresh
unit), `3ed11cf` (`publish` plans and enforces against the durable record), `57dd0a7`
(the specs, the CLI help and both READMEs) and the closeout commit carrying the move
and this entry. Push and the pull request are the maintainer's decision.

**L14** — independent verification (required by the ASSESS plan: `risk: high`,
`nativeRisk: unassessable` because the package-local `gentle-ai` binary is missing,
`agentEscalation` item 3 applied, `plan.independentVerifier: true`). Verdict:
**PASS on S1-S8**, with falsifications that carried weight:

- the invariant is **not vacuous**: with the `refresh_manifest` call replaced by
  `pass` in a COPY of `0ece5ea`, `test_profile_and_render_all_refresh_the_durable_manifest`
  fails exactly as designed (`generate_all_profiles must rewrite the durable record`);
- **no false-refusal surface reproduced**: every in-repo writer after `prepare` —
  `prepare` itself, `codebook_all`, `profile_all` and `render_all` in both package-dir
  and cache mode, `_clean.prune_orphans` (deletes only), `publish._copy_package` (writes
  to `dest` only) and the auto-prepare path — leaves the record newer than what it wrote;
- the legacy path works: `No durable package manifest in ... - recomputed from the tree`
  with exit 0 for both `--dry-run` and the local target;
- the quoted literals match the spec byte for byte (the spec's escaped backticks render
  to the printed recovery; the marker and the `X`/`[!]` forms are the ones implemented).

It reported as unverifiable: the maintainer decision text (a record, not
authenticatable from the repository), the L11 full-suite and gate numbers (it re-ran only
`tests/test_manifest.py` + `tests/test_publish.py`: 153 passed), the MCP envelope path,
and a genuine broken symlink (the host refuses `os.symlink`). It also noted, correctly,
that profiles/renders written into the **package** dir via
`profile --all-files --output build` are not declared at all — the probe reads
`cache/<dir>` and `<root>/<dir>` — and that they are `intermediate` and never delivered,
so they cannot trigger staleness. That is #346 probe territory, recorded as an
observation rather than folded in.

**L15** — two defects the verifier found in MY code, both introduced by making `from_dir`
live, both fixed rather than documented away:

1. a corrupt `build/manifest.json` crashed `publish` with an unhandled
   `json.decoder.JSONDecodeError` — exit 1 through the failure reporter, no marker and no
   recovery;
2. `_newest_declared_artifact` propagated `PermissionError` when a declared entry could
   not be statted, contradicting its own docstring ("an entry that resolves to nothing is
   skipped").

The durable read now catches `OSError`, `ValueError`, `KeyError` and `TypeError`, prints
an `UNREADABLE_MANIFEST` block in the same five-line shape as `STALE_MANIFEST`, refuses
the `hf` confirm before any network call, and lets a dry-run or a local delivery recount
for the preview after saying what happened. The scan catches `OSError` per candidate and
skips the entry exactly like a missing one: deciding what an unreadable entry means is not
the scan's call. Three tests pin both, written after the finding and green on the fixed
tree. PUB-12 gains the clause because "read the SAME manifest" has to say what happens
when the same manifest cannot be read.

**L16** — the full suite then caught what the verifier's enumeration could not: with the
mtime rule, `TestCodebookUpload::test_root_index_uploaded_as_codebook_md` failed. That
test **overwrites** a file the record already declares (`codebook.md`) to prove the
package's own file is what ships. The record and the tree declared exactly the same
paths — only the bytes changed, which the record cannot express — so the mtime proxy
refused a delivery nobody asked to refuse, and the recovery it printed (`prepare
--force --all-files`) would have *regenerated* that file and destroyed the edit. The
proxy was wrong, not the test.

The rule is now material: **the record must declare, path for path, the deliverable set
a recount of the same tree produces** (`publishable` ∧ `staged` ∧ file path). A record
that omits a delivered file, or promises one the delivery no longer has, refuses the
`hf` confirm with the same `STALE_MANIFEST` marker, now naming the `undeclared` and the
`withdrawn` paths — bounded by `config.REPORT_MAX_ITEMS` — before any network call;
a dry-run and the local target warn and keep planning. `intermediate` entries are never
compared: a local-only layer is regenerable churn, not a delivery fact. An in-place
edit of a declared file is therefore not a divergence.

Two consequences worth recording. `_newest_declared_artifact` is gone with its whole
`stat` scan, so the verifier's second finding (a raising `Path.is_file`) is structurally
impossible now rather than patched, and the rule no longer needs root resolution,
directory-entry or unreadable-entry special cases. And one more existing fixture moved
to the supported flow: `test_codebook_uploaded_to_codebook_subpath` hand-adds
`codebooks/PROV.md` after `prepare`, which **is** a real divergence (the page ships and
the record omits it) — it now re-runs the chain, which rewrites the record including
that page, exactly as the printed recovery tells a user to do.

**L17** — the arc's final evidence, on the tree that carries the fix: suite
`2506 passed, 9 skipped` under coverage (base `dev@47bf12c` 2495/9 → +11), the four
rule-14 gates exit 0 each with TOTAL **94%** (7740 stmts), `check_test_mapping.py` OK with
`publish` at 66 scenarios (+6) and `prepare` at 46 (+1), ruff check and format clean, and
the differential **re-run after the rule change**: 6/6 IDENTICAL in stdout, stderr and
exit code against `47bf12c` for `prepare`, `codebook --all-files --config`,
`profile --all-files`, `render --all-files`, `publish --dry-run` and
`publish --target local`. The arc lands as the `publish` fix and the record/spec commit.
Re-verification of the changed rule follows the independent verifier that passed the
rejected version; its verdict closes this document.

**L18** — the second verification round (same read-only verifier, frozen
`0ece5ea..da39960`) returned PASS on behaviour and three things to fix, all now closed:

- **A false claim in this record, caught by the verifier.** L15 and the `da39960` commit
  message said PUB-12 had gained the `UNREADABLE_MANIFEST` clause; it had not — the block
  existed only in `publish.py`, its tests, L15 and the archive report. The clause, its
  scenario and the matching clause in the archived delta, design D3b, the publish CLI
  help and both READMEs are added in the follow-up commit. That is the defect class rule
  15 names, one level down: a durable record asserting a state its artifact does not have.
- **A real hole in the rule, with behaviour behind it.** A record still promising a
  recursive tree the delivery no longer holds went undetected: the tree entry is a
  directory, `delivered()` excludes those by design (#346), and `required_missing()`
  cannot see it either because the status stays `staged`. The verifier showed the upload
  succeeding without the tree. `_delivery_divergence` now compares the *presence* of every
  publishable entry, files and trees alike (`_promised_paths`), and the case is pinned by
  `test_a_withdrawn_recursive_tree_refuses_the_upload`.
- **An under-declaration the rule cannot enforce**, now stated instead of implied: a
  `keep_csv` upload adds the original CSVs at publish time from the configuration, so the
  record — which describes the package tree — has never declared them and the comparison
  must not refuse on that account. The canonical spec, the delta and D3b say so.

The verifier could not reach a genuine pre-#346 manifest, so the legacy-default path (a
staged `profile`/`render` entry in a record without `classification`, which reads back as
`publishable` and would be reported `withdrawn`) stays a flagged risk, unproven in either
direction.

**L19** — the closing round confirmed the two behaviour claims (`1a`–`1d`, `3a`–`3b`:
removing a recursive tree refuses with `withdrawn: assets/` and no upload; the tree present
publishes; a `codebooks/` placeholder that gains pages after the chain publishes; an
in-place edit publishes; both `keep_csv` forms publish) and confirmed all three scope
claims — and then refuted part of my record **in the same class as L18**. `56c581b`'s
message, L18 and the archive report said the `UNREADABLE_MANIFEST` clause reached design
D3b and the CLI help: the design had zero mentions, the CLI had the prose but not the
marker, and the archived delta carried the clause without the scenario the canonical spec
had gained. All four are fixed in the follow-up commit. Twice in one change the claim came
from what I meant to have written rather than from what the artifact contained; the durable
lesson is that a record asserting an artifact state has to be **diffed against the
artifact**, per file, before it is written — the same discipline this change applies to the
manifest itself.
