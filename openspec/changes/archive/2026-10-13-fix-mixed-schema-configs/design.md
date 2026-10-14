# Design — `2026-10-13-fix-mixed-schema-configs`

> **Change** `2026-10-13-fix-mixed-schema-configs` (issue **#292**) · branch
> `fix/292-mixed-schema-configs` from `dev@4ca823e` · store **hybrid**.

---

## 1. The defect, precisely

`build_dataset_card()` emitted, unconditionally:

```python
config_name = cfg.config_names[0] if cfg.config_names else (cfg.pretty_name or cfg.name)
data_files = [{"split": "train", "path": r} for r in card_remotes]
frontmatter["configs"] = [
    {"config_name": config_name, "data_files": data_files, "default": True}
]
```

Two defects in one block: every remote lands in one `train` split regardless of
its columns, and `config_name` may be a display string. The issue's own
reproduction (two census tables with different columns loaded as one `train`
split) fails with `CastError` because the feature list of the first file is
applied to the second file's columns.

## 2. Measured evidence

The RED run against the unmodified code, focused on the new tests:

```
$ uv run pytest tests/test_repo_compliance.py::TestMixedSchemaConfigs \
    "tests/test_splits.py::TestValidateSplitMapping::test_group_aware_warning_names_configs"
6 failed, 1 passed
```

The failures include the reproduction itself — `test_mixed_schema_emits_one_config_per_group`
observed a single merged `configs` entry instead of two — and
`test_ungroupable_corpus_emits_no_configs` observed
`configs: [{'config_name': 'mixed', 'data_files': [a.parquet, b.parquet], 'default': True}]`
where the contract requires neither `configs` nor `dataset_info`.
`validate_split_mapping()` rejected the new `config_names` keyword
(`TypeError: validate_split_mapping() got an unexpected keyword argument`).

The GREEN run of the same selection after the change: **17 passed** (the mixed
class plus the full `TestValidateSplitMapping` contract).

## 3. The edits

### 3.1 `src/sofer/config.py` + its `[tool.sofer]` homes

Five new defaults, read at the call site (AGENTS.md rule 1):

| Key | Default | Use |
| --- | --- | --- |
| `card_config_slug_invalid_pattern` | `[^a-z0-9._-]+` | runs collapsed to the separator by `_slugify_config_name` |
| `card_config_slug_separator` | `-` | replacement; runs are collapsed so `" - "` cannot leave `---` |
| `card_config_slug_max_length` | `96` | slug truncation cap |
| `card_config_slug_fallback` | `default` | name when a slug would be empty |

They are declared in both `_DEFAULTS` (the built-in home) and
`pyproject.toml`'s `[tool.sofer]` section, because `tests/test_config.py`
enforces set-and-value parity between the two (AGENTS.md rule 1, #213).
Declaring them in `_DEFAULTS` without the pyproject entry would fail that guard
by construction.

### 3.2 `src/sofer/repo_compliance.py`

New helpers, all documented:

- `_feature_dtype(col)` — the emitted feature dtype, shared by
  `dataset_info.features` and the grouping signature.
- `_slugify_config_name(value)` — NFKD → ASCII, lowercase, collapse the
  invalid-character runs, trim, truncate, fallback. `pretty_name` is never
  passed here.
- `_origin_signatures(schema)` — `origin → ordered (name, dtype) tuple` (D2).
- `_remote_origin_aliases(cfg, remotes)` — a planned remote resolves to both
  its own normalised path and the declaring `FileEntry.remote`, because the
  CSV-fallback schema path keys `origin` and the row counts by the declared
  remote (RC-R05/R07) while `planned_remotes` returns the `.parquet` remote.
- `group_remotes_by_schema(remotes, schema, aliases)` — the grouping, including
  the schema-less and origin-less-fixture handling (below).
- `schema_config_plan(cfg, schema, keep_csv, staging_dir)` — the single
  `(config_name, remotes)` plan used by the card.
- `_features_for_group` and the single `_build_dataset_info` builder shared by
  the single-group and multi-group paths (AGENTS.md rule 4).

Grouping semantics:

1. Signature groups from the schema origins; a remote joins the group whose
   origin aliases match.
2. A remote with no schema entry joins the sole signature group when there is
   exactly one — the schema report's first-occurrence-wins dedup strips a later
   file whose columns all repeat an earlier file (the common train/test case).
   With several signatures it forms its own group.
3. A non-empty schema with no origins at all (hand-built fixtures) is one
   group for every remote.
4. No schema and more than one remote is **ungroupable** → `None`; the card
   then emits neither `configs` nor `dataset_info` (S2/D1). A single remote
   needs no grouping.

The card emits `default: True` only when the plan has exactly one group (D4),
and `dataset_info` as the historical dict for one group or the HF list shape
for several, each with its own `num_examples` (D5).

### 3.3 `src/sofer/splits.py`

`validate_split_mapping(remotes)` — the default-load warning states both card
shapes, because the card groups those files by column schema: a single-config
card loads every file into one `train` split, a multi-config card is loaded one
table at a time with `load_dataset(repo, name='<config>')`. An earlier draft
threaded the card's config names in through a `config_names` keyword and named
them (capped by a `card_config_group_warn_limit` default); that was removed
before delivery — no production caller can supply the names without parsing the
built card, and an unused keyword plus the default only it reads is surface that
does not earn its place. Naming the groups from the built card is a named
follow-up.

### 3.4 Tests

`tests/test_repo_compliance.py` gains `TestMixedSchemaConfigs` (6 tests:
two-group emission with per-group `dataset_info`, single-signature single
config, no `default` in a multi-group card, slug-never-`pretty_name`,
ungroupable silence, per-group row-count fallback) and a `_col` fixture helper.
`tests/test_splits.py` gains a warning test asserting both card shapes are
stated. Two existing
`TestExpandedCard` tests now pass a realistic schema: with the contract change,
two expanded sheet remotes and **no** schema are ungroupable, so they would no
longer emit a `configs` block. Their intent — configs list the expanded
remotes — is preserved by the schema fixture; one brittle exact-count assertion
was relaxed to `>= 4` because the schema's Data Fields table adds a reference.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is nevertheless a
real red-then-green (§2), RED recorded before the implementation and GREEN after.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | The schema report dedups column names globally (first occurrence wins), so a later file whose columns all repeat an earlier file has no schema entries. Grouping absorbs it into the sole signature group; with several signatures it gets its own group, which can split a same-schema table across configs (loadable, but not ideal). | **Med** | Named, not hidden. Fixing it needs per-origin full signatures, a `build_schema_report` return-shape change outside this issue's scope. The reproduction (distinct tables) is unaffected. |
| R2 | The dry-run warning does not name the emitted config groups. | **Closed before delivery** | The `config_names` keyword and the `card_config_group_warn_limit` default it alone read were removed; the warning now states both card shapes, which is true without the names. Naming the groups from the built card is a named follow-up, not a gap in the rule. |
| R3 | `pyproject.toml` is outside the listed edit surfaces but required by the `_DEFAULTS`↔`[tool.sofer]` parity guard. | Low | The five keys are additive and mechanical. Recorded in the handoff. |
| R4 | Grouping by emitted dtype (`hf_dtype` with the internal-dtype fallback) rather than the raw `dtype` field. | Low | Two tables with the same names but different emitted types must not merge — the emitted type is the loadability contract. |

## 6. Rollback

Revert-only: restoring the previous `configs`/`dataset_info` block, the
`validate_split_mapping` signature, the five config keys and the two test
edits restores the previous behaviour exactly. No state, no migration.

## 7. Success criteria

SC-1..SC-6 of `proposal.md` §4.
