# Proposal — `2026-10-19-fix-manifest-authority`

> **Change** `2026-10-19-fix-manifest-authority` · issue **#349** ·
> branch `fix/349-manifest-authority` from `dev@47bf12c` · store **hybrid**
> (this folder + the ODD doc `odd/tasks/manifest-authority.md` + Engram mirror).
>
> **Status:** implementation in progress; to be archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

Two manifests exist and only one of them is ever the object of record.

`prepare` writes `build/manifest.json` once, at prepare time (`prepare.py:698-701`,
before this change), and nothing ever refreshes it. `publish` never reads that file:
it rebuilds its own manifest in memory (`publish.py:854-858`) and enforces against
that. `PackageManifest.from_dir` existed with no caller and no test.

So PUB-12 — "*`prepare` writes the manifest into the output dir; publish dry-run and
confirm SHALL read the SAME manifest to plan and to enforce contents (no
divergence)*" — never held, and the durable document is the one a human or an agent
reads to answer "what was published?". On the canonical chain
(`prepare → codebook_all → profile_all → render_all`, `mcp_server.py:16`) `prepare`
runs *before* the codebooks exist, so the file on disk declared `codebooks/` as
`optional` while the delivery that followed held the pages.

#346 fixed *what the manifest contains* (the explicit publishable/intermediate
classification) and deliberately left this half out; it also amended the same
requirement with a sentence that sanctions rebuilding the manifest, so PUB-12 now
contradicts itself.

## 2. Scope

**In:** the durable manifest as the single object of record — refreshed at the end of
every phase that adds package artifacts, read by `publish`, with a staleness
backstop that refuses the upload instead of delivering against a record some
out-of-band write has outrun; the PUB-12 reconciliation; the exact recovery text.

**Out (recorded, not implemented here):** the `! MISSING` rows of the dry-run plan
are unreachable (they are nested under `if modified:` while the dry-run path passes
`existing_files=[]`), and `codebooks_required` is dead in production (no caller
passes `True`). Both are separate issues.

## 3. Chosen branch

The maintainer chose **B** (verbatim, 2026-10-19): "opcion B".

- **A** — `publish` reads the file and fails closed when it is stale — blocks the
  canonical chain *by construction*, because `prepare` runs before `codebook_all`, so
  the file is always older than the pages. It collapses into B plus a failure mode.
- **B (chosen)** — the pipeline refreshes the durable manifest at the end of every
  phase that adds package artifacts, so the file is always current and `from_dir`
  becomes the reader.
- **C** — amend PUB-12 to declare the file a prepare-time checkpoint and label it as
  such — the smallest diff, but it leaves the auditable document unable to answer
  "what will be published".

## 4. Impact

1. `manifest.write_manifest()` is the single writer; `manifest.refresh_manifest()` is
   the later phases' entry point, and it never creates a record (`only_if_present`).
2. `prepare` creates the file through the same writer it always used; `codebook_all`,
   `profile_all` and `render_all` refresh it at the end of a successful run.
3. `publish` reads `from_dir(source)`; a package with no durable record is recomputed
   with an explicit notice, and a record older than what it declares refuses the `hf`
   upload before the network prologue and before staging.

Risk: item 3 — the manifest JSON and *which object the delivery rests on* are
contracts a human and an agent already consume.

## 5. Acceptance

Measured in `odd/tasks/manifest-authority.md` (specs S1-S8) and evidenced in
`archive-report.md` when this change closes.
