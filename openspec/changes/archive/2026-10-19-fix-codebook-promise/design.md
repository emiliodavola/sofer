# Design — `2026-10-19-fix-codebook-promise` (issue #354)

## D1 — The promise is a tree fact, not a parameter

`codebook.generate_all` always writes the root index (`codebook.py:792`), but it
creates `codebooks/` only when it writes a page (`out_path.parent.mkdir(...)` per
page). The pair therefore encodes both facts at once:

| `codebook.md` | `codebooks/` pages | meaning | manifest status |
| --- | --- | --- | --- |
| absent | none | never promised | `optional` (PUB-08) |
| present | none (or an empty dir) | promised, produced nothing | `missing` → blocks |
| present | at least one | promised and delivered | each page `staged` |

Deriving it in `build_package_manifest` gives every writer the same answer and
makes the promise survive a refresh it knows nothing about (D3).

Rejected: a sticky boolean in `manifest.json`. The #349 divergence rule compares
the record against a **recount of the same tree**; a field only the record knows
would make the two sides structurally unable to agree.

## D2 — An empty `codebooks/` is an absence

The previous probe was `if codebooks_dir.is_dir(): for page in rglob("*.md")`.
A directory that exists with zero pages entered the branch, iterated nothing, and
emitted no entry — neither `missing` nor `optional`, so no reader could see it.
The probe now collects the pages first and treats "no pages" as the absence it
is, including when the directory exists.

## D3 — Stickiness is a consequence, not a feature

`profile_all` and `render_all` run after `codebook_all` on the canonical chain
and refresh the record. A parameter-based promise would be downgraded by them.
Because the promise is recomputed from the tree on every build, no refresh can
downgrade it, and no call site needs to know it exists.

## D4 — Enforcement is unchanged

`publish` already blocks on `manifest.required_missing()` over the durable file
(`publish.py:1069-1080`). The change only makes the record capable of carrying a
`missing` codebook entry, then deletes the dead parameter from `publish` and
`_delivery_divergence`. The block, its recovery text and the dry-run/local
warning behavior are untouched.

## D5 — Migration is the documented behavior, not a patch

A record written before this change says `optional`. `publish` reads the record
as-is (PUB-12), so it does not block until the build chain refreshes it. That is
consistent with every other record-derived rule from #349 and is stated in the
spec delta instead of being special-cased in the reader.

## D6 — Divergence stays a path-set comparison

`_delivery_divergence` recounts with the same derivation, so a record that says
`optional` for a package that carries an index is not a path divergence: a
`missing` entry never enters the promised set. The block a human sees is the
required-missing one, which names the artifact and the recovery.
