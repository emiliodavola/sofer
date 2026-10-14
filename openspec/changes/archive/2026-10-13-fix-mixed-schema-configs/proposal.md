# Proposal — `2026-10-13-fix-mixed-schema-configs`

> **Change** `2026-10-13-fix-mixed-schema-configs` · issue **#292** · branch
> `fix/292-mixed-schema-configs` from `dev@4ca823e` · store **hybrid**
> (this file + Engram mirror).
>
> **Status:** implementation complete; archived inside the delivering branch
> (AGENTS.md rule 15).

---

## 1. Intent

`repo_compliance.build_dataset_card()` emitted **one** `configs` entry with **one**
`train` split for every planned remote, and derived `config_name` from
`pretty_name` — a human display string. For a corpus that mixes schemas (8 census
tables + 57 two-column dictionaries, 65 files, 66.2M rows) the published default
config is unloadable: `datasets` reports `CastError` / `DatasetGenerationError`
because the second file's columns do not match the first file's feature list, and
`dataset_info` reports a merged row total for a split that cannot be generated.
The observed `config_name`
`Censo Nacional de Población, Hogares y Viviendas 2010 (Argentina) - Microdatos`
— spaces, a comma, parentheses and accents — is not a usable
`load_dataset(config_name=...)` identifier.

The fix groups the planned remotes by column signature and emits one config per
group, each with its own `dataset_info`; slugs every `config_name`; drops the
`default` flag when more than one config is emitted; and emits neither
`configs` nor `dataset_info` when the corpus is ungroupable.

## 2. Scope

### In scope

- `build_dataset_card` config/dataset_info generation: grouping by
  `ColumnSchema.origin` signature, slugged `config_name`, single-config
  `default`, per-group `dataset_info`.
- The ungroupable guard (no schema for the remotes, more than one remote).
- `splits.validate_split_mapping` becomes group-aware: the default-load warning
  can name the configs the card will emit.
- New `[tool.sofer]`-backed defaults in `config.py`.
- The `repo-compliance` spec delta, the tests, and both README-relevant notes.

### Out of scope (non-goals)

- **`src/sofer/publish.py`** — frozen for this batch (owned by another branch);
  its dry-run caller keeps calling `validate_split_mapping(remotes)` and so gets
  the generic message. The group-aware message is one caller change away.
- **`src/sofer/prepare.py`** — untouched; the card generation path already
  passes the staging mirror and the schema.
- No `column`-level codebook, quality, or `.xlsx`/`.parquet` conversion change.
- No version bump; no new dependency.

## 3. Settled decisions

The spec of record (`odd/tasks/mixed-schema-configs.md`) already settles D1–D5,
quoted here for the durable record:

| # | Decision |
| --- | --- |
| **D1** | S1 and S2 are read together: group remotes by column signature and emit one config per group; S2's "emit nothing" is the guard for the **ungroupable** case, never a rule that suppresses valid per-group configs. |
| **D2** | Group identity = the ordered `(name, dtype)` signature of the `ColumnSchema` entries whose `origin` is that remote; sheet origins group per sheet. |
| **D3** | `config_name` is a slug (`[a-z0-9._-]`) from `[dataset] name` for a single group and from the remote's file stem for multiple groups, validated; `pretty_name` never reaches it. |
| **D4** | `default: True` only when the card emits exactly one config; a multi-group card carries no `default`. |
| **D5** | `dataset_info` follows the same grouping (one per config, its own `num_examples`); a group with no exact row count falls back to the conservative per-file product for that group only. |

## 4. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | The new tests are red before the change and green after |
| SC-2 | Two tables with different columns in one `train` split produce two configs, each with a matching `dataset_info`; the single-signature corpus keeps exactly one; a multi-group card has no `default` |
| SC-3 | `config_name` is a validated slug, never `pretty_name` |
| SC-4 | The ungroupable corpus emits neither `configs` nor `dataset_info` |
| SC-5 | The full suite is green, `coverage report` TOTAL ≥ 90, ruff/format/mypy/pyright clean, `check_test_mapping.py` exits 0 |
| SC-6 | No `# pragma: no cover` is added anywhere |

## 5. Non-goals recorded for the spec delta

No `publish.py` (or `prepare.py`) change; no version bump; no new requirement
beyond RC-R23; no Test Mapping row (`repo-compliance` stays a permanent declared
backlog); no registry edit.
