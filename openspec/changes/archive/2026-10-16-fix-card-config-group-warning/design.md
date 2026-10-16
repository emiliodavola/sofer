# Design — `2026-10-16-fix-card-config-group-warning`

> **Change** `2026-10-16-fix-card-config-group-warning` (issue **#303**) · branch
> `fix/303-card-config-group-warning` from `dev@6786ba1` · store **hybrid**.

---

## 1. The gap, precisely

`_print_split_mapping_validation(remotes)` called `validate_split_mapping(remotes)` and printed
`load_dataset(repo, name='<config>')` — a template the reader could not resolve. The names were
computed two layers away, inside `build_dataset_card`, and discarded with the rest of the plan:

```python
plan = schema_config_plan(cfg, schema, keep_csv, staging_dir) if cfg.files else None
...
for config_name, group_remotes in plan:   # names known here, and only here
```

`publish.py` does not build the card, and `prepare()` — which does — returns only an exit code.

## 2. Where the names come from

`card_config_names(build_dir)` reads `<build_dir>/README.md`, takes the block between the first two
`---` fences, `yaml.safe_load`s it, and returns `[entry["config_name"] for entry in frontmatter["configs"]]`.

Three details decided the implementation:

- **`maxsplit=2`.** A `---` inside the YAML (a multi-line citation, say) must not be mistaken for the
  closing fence.
- **A leading non-blank prefix disqualifies the file.** `text.split("---", 2)` on a card without
  frontmatter produces a first element that is not blank, and the reader returns `[]` rather than
  parsing prose as YAML.
- **Any entry that is not a mapping with a non-empty string `config_name` returns `[]` for the whole
  card.** A partial list would name some configs and silently hide others — worse than the
  placeholder, which at least does not look complete.

## 3. The edits

### 3.1 `src/sofer/config.py` + its `[tool.sofer]` home

| Key | Default | Use |
| --- | --- | --- |
| `card_config_group_warn_limit` | `5` | How many config names the warning lists before eliding. Must be positive: `0` would name none, which is the defect the cap lives inside of. |

### 3.2 `src/sofer/splits.py`

```python
def validate_split_mapping(
    remotes: list[str],
    config_names: list[str] | None = None,
    warn_limit: int | None = None,
) -> list[str]:
```

`_config_name_hint(config_names, warn_limit)` returns the bare `name='a', name='b'` list (or
`name='a', ... and N more`, or `name='<config>'`) and the caller supplies the surrounding prose, so the
elision rule is testable on its own. `warn_limit=None` reads `config.CARD_CONFIG_GROUP_WARN_LIMIT` at
call time (AGENTS.md rule 1 — never a literal in the call path).

### 3.3 `src/sofer/publish.py`

`_print_split_mapping_validation(remotes, config_names=None)` forwards the names. Both call sites pass
`card_config_names(source)`; the dry-run site guards with `if source.is_dir()`, because before a
package exists `source` is not yet a directory and there is no card to read.

### 3.4 Tests

- `tests/test_repo_compliance.py::TestCardConfigNames` (10 tests). The first builds a real multi-schema
  card with `build_dataset_card` and asserts the reader returns exactly the names the card emitted —
  writer and reader agreeing through the public interface, not through a hand-written fixture.
- `tests/test_splits.py::TestConfigNameHintInWarning` (7 tests): names, placeholder fallback, elision,
  the config-read default, and that the named warning only fires on the default-load path.
- `tests/test_publish.py::TestSplitMappingValidationNamesConfigsNext` (2 tests): the pass-through.

Two of the new assertions had to be narrowed during implementation and the reason is recorded because
it is a fact about the existing code, not a convenience: `validate_split_mapping` returns **three**
warnings for two keyword-less files, not one (the per-split keyword-consistency check adds its own), so
the tests select the `Default-load warning` entry instead of indexing `warnings[0]`.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests, so
the new tests did not themselves observe RED. What was
