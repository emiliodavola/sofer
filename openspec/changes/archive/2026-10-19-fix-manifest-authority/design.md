# Design — `2026-10-19-fix-manifest-authority` (issue #349)

## D1 — The durable file is the object of record

PUB-12 says publish dry-run and confirm "SHALL read the SAME manifest". Read as *the
same derivation* that requirement was satisfiable (publish recomputes
deterministically from the tree, so two runs agree); read as *the same artifact* it was
never satisfied, and the artifact is what a human or an agent actually opens. The
maintainer resolved the ambiguity for the artifact: **B** — the file on disk is the
object of record, and it is kept current instead of being treated as a snapshot.

Rejected: **A** (read the file, fail closed on staleness alone) blocks the canonical
chain by construction, because `prepare` runs before `codebook_all`; it is B plus a
guaranteed failure mode. **C** (declare the file a prepare-time checkpoint) is the
smallest diff but leaves the auditable document unable to answer the only question a
reader brings to it.

## D2 — One writer, and a refresh that never creates

`manifest.write_manifest(cfg, output_dir, *, keep_csv, codebooks_required,
only_if_present)` is the single writer; `prepare` calls it and creates the file.
`manifest.refresh_manifest(cfg, written_to)` is the phases' entry point: it resolves
the target (`written_to` when the phase wrote into a package directory, otherwise the
resolved package directory, because a cache-mode write changes what a recount of the
package says) and always passes `only_if_present=True`.

That flag is the whole safety story for later phases: a phase can never invent a
package record for a tree `prepare` never prepared, so `profile --all-files` on an
untouched dataset does not create a `build/manifest.json` that would then declare every
parquet `missing`. One shared function, four call sites, no copy of the classification
logic.

## D3 — Staleness is a backstop with an exact definition

The rule: **the durable manifest is stale when it is older than the newest file it
declares as `staged`**. Implementation notes that matter:

- **Both roots.** An entry path is package-relative for a package artifact and
  dataset-root-relative (or absolute) for an intermediate layer, so `source / path` is
  tried first and the dataset root second. Reading only one root would miss exactly the
  `cache/profiles/...` entries #346 fixed.
- **What is skipped.** Directory entries (a tree is enumerated at copy time, never one
  delivered file) and entries that resolve to nothing — absence is
  `required_missing()`'s business, and conflating the two would report a missing
  artifact as staleness.
- **Nothing declared → nothing to outrun.** A record whose declared files are all gone
  is not stale; it is a package whose missing artifacts the enforcement block already
  names.

Because every writer refreshes at the end of its run, the rule fires only for an
out-of-band write or a phase that forgot to refresh. That is what makes it a backstop:
the mechanism is D2, and the rule exists so a forgotten refresh cannot pass as a
current record.

## D4 — Fail closed, but only where it protects delivery

Placement is load-bearing: the check runs after the auto-prepare block (`_needs_prepare`
already rewrites the record when the package is stale against its inputs) and before the
quality gate, the `HfApi` construction, the remote prologue and staging. So a refusal
can never touch the network or mutate anything.

A dry-run and the local target print the same block as a warning and continue. A preview
that refuses to show the plan is useless, and a local copy delivers files, not the
record. Only the `hf` confirm refuses, which is the delivery PUB-12 is about.

## D5 — The invariant is executable

`PackageManifest.from_dir(output_dir) == build_package_manifest(cfg, output_dir)` after
each phase. One equality, four phases, and any future phase that adds artifacts without
refreshing fails it. The profile/render tests doctor the record with a ghost entry
first, so a phase that silently did *not* refresh cannot pass by coincidence.

## D6 — Reconciling PUB-12 with itself

#346 amended the last scenario to say a consumer needing the true class "SHALL
re-derive by rebuilding the manifest (`publish` does)". That sentence stays true only
where recomputation is still allowed, so this change scopes it: `publish` rebuilds
**only** for a package that carries no durable manifest, and never while the durable
file exists. The reconciliation lands in the canonical spec through the delta in this
folder.
