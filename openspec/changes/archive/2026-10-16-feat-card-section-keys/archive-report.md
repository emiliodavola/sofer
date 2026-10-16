# Archive report — `2026-10-16-feat-card-section-keys`

> **Change** `2026-10-16-feat-card-section-keys` · issue **#291** · branch
> `feat/291-card-section-keys` from `dev@6786ba1` · milestone
> **v0.6.0 — agent surface & card completeness**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

Five `[meta]` keys now fill the card sections that had no key at all, so a config with every ROTW field
filled produces a card with no sentinel — and an MCP consumer can satisfy every section it reads.

| Requirement | Where |
| --- | --- |
| RC-Universal-Card — "Card sections with a dedicated key" (6 scenarios, inline `test:` evidence) | `openspec/specs/repo-compliance/spec.md` §2.1.2 |
| The keys in the TOML representation | `openspec/specs/repo-compliance/spec.md` §2.1.1 |
| Five `DatasetConfig` fields + `from_toml` reads | `src/sofer/model.py` |
| One `_MORE_INFO` constant; the seven sentinel sites read their key | `src/sofer/repo_compliance.py` |
| `repository` → `source` fallback | `src/sofer/repo_compliance.py` |
| 10 tests | `tests/test_repo_compliance.py` |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T7). No `pending` row remains.

## 3. Measured evidence

| Gate | Command | Result |
| --- | --- | --- |
| Full suite | `uv run coverage run -m pytest tests/ -q` | **2165 passed, 9 skipped** (83 s) |
| `cli.py` / `scanner.py` / `prepare.py` / `publish.py` 100.00% (rule 14) | `uv run coverage report --include=… --fail-under=100 -m` | **100%** each |
| TOTAL floor | `uv run coverage report` | **94%** |
| Lint / format | `uv run ruff check src/ tests/ scripts/`, `ruff format` | `All checks passed!` |
| Types | `uv run mypy src/ scripts/`, `uv run pyright` | 0 errors (1 pre-existing `tomli` warning) |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK` |
| Pre-commit hooks on the commits | `ruff`, `ruff-format`, `mypy`, `pyright` | all `Passed` |

2165 = the baseline 2154 plus the 10 new tests, plus one previously-existing test now counted
differently — recorded as measured rather than reconciled by hand.

## 4. Decision recorded

**D1 — add the `[meta]` keys, not omit the sections.** The issue prefers omission and lists it first.
It is the more expensive option here: `repo-compliance` §2.1.2 *requires* the placeholder and the
*Minimal config* scenario requires it again, so omission carries a spec delta and rewrites the tests
that assert the sentinel — for a card that is shorter but no more informative. Adding the keys fixes
the reported defect (a **fully-filled** config shipping placeholders) while leaving the rule that an
unfilled config says so. The issue's own option 3 is delivered alongside it for `repository`.

## 5. Deviations and findings, stated

1. **No README change, and rule 13 is therefore not triggered.** The README's `[meta]` block enumerates
   only `description`, `license` and `tags`; the full key list lives in the spec. Adding a second copy
   to the README would be new duplicate surface, so the keys are documented where the others are.
2. **Three test fixtures were wrong before the assertions were.** Each correction is recorded in
   `design.md` §3.3 because each was a wrong premise of mine, not a code defect: the "fully filled"
   fixture omitted `language`, `collection_method` and `citation` (all of which already had keys), and
   `build_dataset_card()` takes `study_design_content` as a **parameter** rather than reading
   `cfg.study_design`. The resulting `test_curation_rationale_needs_study_design` makes the acceptance
   claim precise: with the five new keys set and no `study_design`, exactly one sentinel remains.
3. **No existing test changed expectation.** `370 passed` on the four affected files *before* the new
   tests existed: the five fields default to `""`, so every pre-existing sentinel assertion still holds.
   That is the evidence that this change is additive for every config that does not declare the keys.

## 6. Follow-ups this change creates

- **`Curation Rationale` still needs a file.** It has no free-text key by design (the issue names
  `study_design` as its path). A `curation_rationale` key would be one more field and one more site if
  a reviewer decides the file indirection is not worth it.
- **`#288`'s placeholder gate** (Fase 4 of this milestone) must cover the five new keys, so the
  "still a placeholder" check and the key set stay in step.
