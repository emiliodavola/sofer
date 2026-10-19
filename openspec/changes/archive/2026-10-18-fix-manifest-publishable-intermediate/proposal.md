# Proposal — `2026-10-18-fix-manifest-publishable-intermediate`

> **Change** `2026-10-18-fix-manifest-publishable-intermediate` · issue **#346** ·
> branch `fix/346-manifest-publishable-intermediate` from `dev@d07557e` · store
> **hybrid** (this folder + Engram mirror).
>
> **Status:** implementation in progress; to be archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

`build/manifest.json` is the auditable description of the package, and it declares
`profile`/`render` entries in the same list as `parquet`, `card` and `license`.
Those layers are never uploaded, and nothing in the document says so: PUB-12
demands an explicit publishable/intermediate boundary, but only `.status` was ever
serialized, so the boundary lived in a module docstring. A corpus therefore
declared 135 artifacts and delivered 133 (#346), and any reader counting the list
concluded two artifacts were missing from the upload.

The probe made it worse: the layers were looked for at `<dataset root>/profiles`
while `profile_all`/`render_all` write them under the artifact cache
(`profile.py:264-270`), so the entry was always an `optional` directory placeholder
describing a location nobody writes to.

## 2. Scope

**In:** an explicit `classification` field on every manifest entry
(`publishable`/`intermediate`), the derived `delivered()` selector (publishable ∧
present), the layer probe pointed at the artifact cache with the dataset root kept
as the explicit-location fallback, the tests that pin all of it, and the PUB-12
clause.

**Out:** the other half of #346 — `publish` re-deriving its own manifest instead of
reading the one `prepare` wrote — which is issue **#349** and a different decision.
Also out: staging the layers (`_copy_package` correctly never uploads them, and
they are regenerable), and any change to `.status` vocabulary.

## 3. Approach

1. `ArtifactClass` = `publishable` | `intermediate`, carried by every
   `ManifestEntry` and serialized as `classification`. Two independent axes:
   `classification` says *does it belong to the delivery*, `status` says *is it
   here and does its absence block*.
2. `from_dict` defaults a missing field to `publishable`, so a manifest written by
   0.6.1 still loads (the field is additive; the roundtrip stays byte-stable).
3. `PackageManifest.delivered()` = publishable ∧ staged, which is exactly what
   `_copy_package` stages. `publishable()` stays the pure classification query,
   because an absent optional artifact (`codebook.md` before an `--all-files`
   prepare) is publishable in principle and still not delivered — the probe caught
   my first version conflating the two.
4. The layer probe looks under `<root>/<output_dir>/<dir>` first, then
   `<root>/<dir>`, and records the path relative to the root (with a fallback when
   the cache path is outside it), so the entry reports the tree the pipeline built.

## 4. Affected specs

- `publish` — PUB-12 gains the `classification` field, the probe rule and the
  `delivered()` identity, with three scenarios. `publish` is a permanent
  declared-backlog spec (`openspec/test-mapping-registry.md:38`), so no
  `## Test Mapping` row is owed and the registry is not edited.

## 5. Delivery

One branch, one delivery PR against `dev`, archived inside that PR. Work-unit
commits:

1. `fix(manifest): classify every artifact publishable or intermediate (#346)` —
   T1, T2, T3.
2. `test(manifest): pin the delivered set against the staged set (#346)` — T4.
3. `docs(specs): declare the PUB-12 classification boundary (#346)` — T5.
4. `chore(odd): record the #346 work units and archive the change` — T5, T6.
