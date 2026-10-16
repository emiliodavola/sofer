# Archive report — `2026-10-16-fix-card-config-group-warning`

> **Change** `2026-10-16-fix-card-config-group-warning` · issue **#303** · branch
> `fix/303-card-config-group-warning` from `dev@6786ba1` · milestone
> **v0.6.0 — agent surface & card completeness**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

The `sofer publish --dry-run` default-load warning now names the config groups the built card emitted,
so `load_dataset(repo, name='<config>')` is actionable without opening the frontmatter — and reachable
for an MCP caller, who receives the warning in the tool result but never the card.

| Requirement | Where |
| --- | --- |
| RC-Universal-Card "Actionable warning" (S4), amended + the new "Card config names" clause | `openspec/specs/repo-compliance/spec.md` (5 scenarios, each with inline `test:` evidence) |
| `card_config_names(build_dir)` | `src/sofer/repo_compliance.py` |
| `validate_split_mapping(remotes, config_names, warn_limit)` + `_config_name_hint()` | `src/sofer/splits.py` |
| `_print_split_mapping_validation(remotes, config_names)` + both call sites | `src/sofer/publish.py` |
| `[tool.sofer] card_config_group_warn_limit` | `src/sofer/config.py`, `pyproject.toml` — both homes |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T8). No `pending` row remains.

## 3. Measured evidence

| Gate | Command | Result |
| --- | --- | --- |
| Full suite | `uv run coverage run -m pytest tests/ -q` | **2173 passed, 9 skipped** (84 s) |
| `publish.py` 100.00% mandate (rule 14) | `uv run coverage report --include=src/sofer/publish.py --fail-under=100 -m` | **100%** (352 stmts, 150 branches, 0 miss) |
| `cli.py` / `scanner.py` / `prepare.py` | same, per file | **100%** each |
| TOTAL floor | `uv run coverage report` | **94%** |
| Lint / format | `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/` | `All checks passed!` / `75 files already formatted` |
| Types | `uv run mypy src/ scripts/`, `uv run pyright` | 0 errors (1 pre-existing `tomli` warning) |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK` |
| Pre-commit hooks on the commit | `ruff`, `ruff-format`, `mypy`, `pyright` | all `Passed` |

The full-suite count is 2173 rather than Fase 1's 2185 because this branch is cut from `dev`, not from
`fix/287-296-mcp-registration-timeouts` — each phase is its own PR against `dev` (AGENTS.md rule 12).

## 4. Deviations from the issue, stated

1. **Delivered the issue's option 2, not its preferred option 1.** The issue prefers "emit the
   group-aware warning from the card builder", but `sofer prepare` and `sofer publish --dry-run` are
   separate processes: a plan held in `prepare`'s memory cannot reach the caller that prints the
   warning. Option 1 as written would have required `publish` to re-derive the schema and grouping —
   the duplicate derivation option 1 exists to avoid. Reading the built card returns the names that
   actually shipped. Full reasoning in the change's `proposal.md` §3.
2. **The surface PR #301 removed is restored, with a caller.** The `config_names` keyword and the
   `card_config_group_warn_limit` default were dropped before delivery because no production caller
   could supply the names. Two `publish` call sites now can, which is the condition that review found
   missing; the change says so rather than silently reversing a recorded decision.
3. **Two new assertions were narrowed after the first run**, and the reason is recorded as a fact about
   the existing code: `validate_split_mapping` returns **three** warnings for two keyword-less files,
   not one (`design.md` §3.4, feature-document Log L4).

## 5. What this change did not do

- It does not name the configs in `prepare`. The warning belongs to the publish surface where the user
  acts on it; a second printing site would double the message.
- It does not recompute the schema or the grouping in `publish`.

## 6. Follow-ups this change creates

- **R1** (in `design.md`): a hand-edited card would name configs that no longer match the corpus.
  `README.md` is auto-generated and overwritten on every prepare, so this needs no action; recorded so
  a future reader does not rediscover it.
