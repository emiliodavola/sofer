# Delta for publish

> **Change** `2026-10-19-fix-codebook-promise` · issue **#354** · applies to the
> canonical spec at `openspec/specs/publish/spec.md` (PUB-12).

---

## MODIFIED Requirements

### Requirement: Package artifact manifest with explicit publishable/intermediate boundary (PUB-12) — Modified 2026-10-19, fix-codebook-promise

Missing **required** artifacts SHALL block confirm with a stable `error_code` and a concrete recovery (re-run prepare); optional artifacts absent SHALL be marked `optional` and SHALL NOT emit the "missing artifact" warning (no silent omission, no false warning). **The per-file codebook set SHALL be required exactly when the package carries its root `codebook.md` index**: `codebook_all` and `prepare --all-files` always write that index and create `codebooks/` only when they write a page, so an index with no page under `codebooks/` — including an existing but empty directory — SHALL be recorded `missing` and SHALL block confirm, while a package with neither SHALL record `codebooks/` `optional` and SHALL NOT warn. No caller-supplied flag SHALL record the promise, and a later-phase refresh SHALL NOT downgrade a promised absence back to `optional`.

A record written before this rule existed SHALL keep its recorded `optional` until the build chain refreshes it; the reader SHALL NOT special-case it, because the durable record is the object of record (issue #349).

#### Scenario: A promised codebook set that is absent blocks confirm (#354) — Added 2026-10-19

- GIVEN a package that carries the root `codebook.md` index and no page under `codebooks/`
- WHEN the durable manifest is built or refreshed, and confirm runs
- THEN the `codebook_page` entry SHALL read `missing`
- AND the confirm SHALL refuse before staging with the existing recovery naming the build chain
- AND a later `profile_all`/`render_all` refresh SHALL NOT turn that entry back into `optional`

#### Scenario: A package that never promised codebooks keeps them optional (#354) — Added 2026-10-19

- GIVEN a package with neither `codebook.md` nor any page under `codebooks/`
- WHEN the manifest is built and confirm runs
- THEN the `codebook_page` entry SHALL read `optional`
- AND no codebook-missing warning SHALL be emitted

#### Scenario: An empty codebooks directory is an absence, not a silent no-op (#354) — Added 2026-10-19

- GIVEN a package whose `codebooks/` directory exists but holds no page
- WHEN the manifest is built
- THEN the entry SHALL be `missing` when the root index is present and `optional` when it is not — never absent from the record
