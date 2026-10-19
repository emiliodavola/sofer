# Proposal — `2026-10-19-fix-codebook-promise`

> **Change** `2026-10-19-fix-codebook-promise` · issue **#354** ·
> branch `fix/354-codebook-promise` from `dev@150ead1` · store **hybrid**
> (this folder + the ODD doc `odd/tasks/codebook-promise.md` + Engram mirror).
>
> **Status:** implementation complete; archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

PUB-12 says a promised per-file codebook set that is absent SHALL block confirm.
The mechanism that was supposed to carry that promise — `codebooks_required` —
cannot fire: no caller passes it, and the writers that build and refresh the
durable record never receive it, so an absent set is recorded `optional` and the
delivery ships silently.

The issue documents three breaks. Verifying it found a fourth: the canonical
chain runs `profile_all` and `render_all` **after** `codebook_all`, and both
refresh the record with the default `False`, so even a caller that passed `True`
would be downgraded back to `optional`. A fifth hole sits in the probe itself: an
existing but empty `codebooks/` directory emits no `codebook_page` entry at all.

## 2. Scope

**In:** one home for the promise; the durable record expresses it; the existing
required-missing block enforces it; the dead parameter is deleted from
`build_package_manifest`, `write_manifest`, `refresh_manifest`, `publish` and
`_delivery_divergence`; PUB-12 states the rule; both directions and the
empty-directory case are pinned by tests.

**Out:** the `! MISSING` rows of the dry-run plan (still unreachable, tracked by
#349's archive report) and PUB-12's pre-existing `error_code` drift — neither is
this defect.

## 3. Chosen branch

- **A (chosen) — derive the promise from the tree.** `codebook.md` present ⇔ the
  flow promised the pages.
- **B — a sticky boolean in `manifest.json`.** It cannot be recomputed from the
  tree, so #349's divergence recount would need a second source for the same
  fact — the opposite of "one home".
- **C — the reader owns the promise** (`publish(..., codebooks_required=True)`).
  Not viable: `publish` refuses to rebuild the record while one exists, so the
  flag never reaches the object it enforces against — this is the issue's own
  second branch and it is structurally dead.

## 4. Impact

1. `build_package_manifest` derives `promised = (output_dir / "codebook.md").is_file()`;
   an empty `codebooks/` is an absence, not a no-op.
2. Every writer and refresher inherits the promise for free: `prepare`,
   `codebook_all`, `profile_all` and `render_all` pass no flag and cannot
   downgrade it.
3. `publish` keeps reading the durable record and enforcing
   `required_missing()`; the parameter disappears from `publish` and
   `_delivery_divergence`, and the divergence recount uses the same derivation so
   the two sides always agree.
4. A record written before this change stays `optional` until the chain refreshes
   it — documented migration, not patched.

Risk: item 3 — the deleted keyword parameters are importable API, and the
codebook-presence rule is a delivery gate consumers observe.

## 5. Acceptance

Specs S1-S8 in `odd/tasks/codebook-promise.md`; evidence in `archive-report.md`.
