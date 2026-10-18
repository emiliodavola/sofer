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
| T1 | RED first: after `codebook_all` on a prepared tree, the durable manifest must equal the rebuild. Then `write_manifest()` in `manifest.py`, and `prepare` writes through it | S4, S5 | |
| T2 | Refresh at the post-prepare phase boundaries: `codebook_all` (CLI + MCP), `profile_all`, `render_all` | S5, S6 | |
| T3 | `publish` reads `from_dir`; staleness fails closed with a stable code and the truthful recovery; legacy tree recomputes with a notice | S3, S7 | |
| T4 | Tests: per-phase invariant, legacy tree without the file, stale manifest blocks, plus one regression test per existing command the change touches | S5-S7 | |
| T5 | Specs: reconcile PUB-12, update PRP-11, add the scenarios and the change folder archived inside the PR | S8 | |
| T6 | Docs: recovery text and CLI help name the real recovery; `README.md` + `README_ES.md` in the same commit | S8 | |
| T7 | Gates: suite, the four 100.00% core modules with zero pragmas, ruff, mypy 3.13, pyright, `check_test_mapping.py`, and the differential check of every command sharing the changed code against the base commit | — | |

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
