# Proposal — `2026-10-16-fix-card-config-group-warning`

> **Change** `2026-10-16-fix-card-config-group-warning` · issue **#303** · branch
> `fix/303-card-config-group-warning` from `dev@6786ba1` · store **hybrid**.
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

Since #292 the generated card emits one config per column-signature group, and the dry-run
default-load warning was rewritten to say so instead of claiming one merged `train` split. It now
reads:

```
[!] Default-load warning: 65 data files have no split keywords. The generated card groups them by
    column schema: a single-config card loads every file into one 'train' split when load_dataset()
    is called without a config name ..., while a multi-config card is loaded one table at a time with
    load_dataset(repo, name='<config>'). ...
```

Which is true, but does not tell the user **which names to pass**. The names are known exactly when
the card is built, and the caller that prints the warning never sees them: `publish.py` calls
`validate_split_mapping(remotes)` and has neither the schema nor the card, while `prepare()` builds
the card and returns only an exit code. For an agent driving the MCP surface it is worse — the tool
result carries the warning, not the card.

## 2. Scope

### In scope

- `src/sofer/repo_compliance.py`: `card_config_names(build_dir)`, reading the emitted
  `configs[].config_name` values back from the card's YAML frontmatter.
- `src/sofer/splits.py`: `validate_split_mapping(remotes, config_names=None, warn_limit=None)` and
  `_config_name_hint()`.
- `src/sofer/publish.py`: `_print_split_mapping_validation(remotes, config_names=None)` and both call
  sites passing `card_config_names(source)`.
- `src/sofer/config.py`, `pyproject.toml`: `card_config_group_warn_limit` in both homes.
- `openspec/specs/repo-compliance/spec.md`: RC-Universal-Card "Actionable warning" (S4).

### Out of scope

- **Re-deriving the plan in `publish`.** The names are read from the artifact that shipped, so the
  warning cannot disagree with the card. Recomputing the schema in `publish` would duplicate the
  derivation and put a second answer on the table.
- **Naming the configs in `prepare`.** `prepare` builds the card and knows the plan, but the warning
  belongs to the publish surface where the user acts on it; adding a second printing site would
  double the message.

## 3. Approach

The issue offers two options and prefers the first ("emit the group-aware warning from the card
builder"). The delivered design is its second, and the reason is worth stating: `sofer prepare` and
`sofer publish --dry-run` are **separate processes**, so a plan held in `prepare`'s memory cannot
reach the caller that prints the warning. Option 1 as written would therefore require `publish` to
re-derive the schema and grouping, which is exactly the duplicate derivation the first option exists
to avoid. Reading the built card costs one small frontmatter reader (`sofer/_yaml.py` already owns
YAML parsing) and returns the names that actually shipped.

Which is why the removed draft surface of PR #301 now earns its place: a `config_names` keyword with
no production caller was surface that did not pay for itself. With a production caller — both
`publish` call sites — it does, and `card_config_group_warn_limit` earns its place for the same
reason, capping a list that a 65-table corpus would otherwise print in full.

## 4. Success criteria

- SC-1: the dry-run warning names the emitted configs when the card is on disk.
- SC-2: no built card, or a card without `configs`, keeps today's placeholder form.
- SC-3: the named list is capped by a `[tool.sofer]` value, with `... and N more`.
- SC-4: a card whose names cannot be read yields no names — never a guess.
- SC-5: the full gate set is green, with `publish.py` still at 100.00% line coverage.
