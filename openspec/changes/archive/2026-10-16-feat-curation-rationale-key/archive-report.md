# Archive report — `2026-10-16-feat-curation-rationale-key`

> **Change** `2026-10-16-feat-curation-rationale-key` · issue **#324** · branch
> `feat/324-curation-rationale-key` from `dev@5249be6` · store **hybrid**.

> milestone **v0.7.0 — follow-up defects from the v0.6.0 batch**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

`### Curation Rationale` is no longer the one card section that requires a file. A user with three
paragraphs of rationale types them into `[meta] curation_rationale`; a user who wants a document points
`[meta] study_design` at it, exactly as before.

| Requirement | Where |
| --- | --- |
| RC-Universal-Card — "Card sections with a dedicated key", Curation Rationale clause (6 scenarios, inline `test:` evidence) | `openspec/specs/repo-compliance/spec.md` §2.1.2 |
| The key in the TOML representation | `openspec/specs/repo-compliance/spec.md` §2.1.1 |
| The `DatasetConfig` field + its `from_toml` read | `src/sofer/model.py` |
| The three-arm resolution chain | `src/sofer/repo_compliance.py` |
| 7 new tests + 2 extended fixtures | `tests/test_repo_compliance.py` |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T7). No `pending` row remains.

## 3. Measured evidence

| Gate | Command | Result |
| --- | --- | --- |
| Full suite | `uv run pytest tests/ -q` | **2247 passed, 9 skipped** (86.44 s) |
| Collection delta | `uv run pytest tests/ -q --collect-only` before/after the change | **2249 → 2256** collected; +7 = the 7 new tests |
| Failing-on-RED | `uv run pytest tests/test_repo_compliance.py -q -k "CurationRationale or CardSectionKeys"` before the source edit | **7 failed, 11 passed** — `AttributeError`/`TypeError` on the missing field |
| Focused GREEN | same selection after the source edit | **21 passed** |
| Lint / format | `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/` | `All checks passed!` / `75 files already formatted` |
| Types | `uv run --python 3.13 mypy src/ scripts/`, `uv run pyright` | 0 errors / 0 errors (1 pre-existing `tomli` warning in `_toml.py`) |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK` |
| rule-14 per-file 100.00% gates | `scripts/check_core_coverage.sh` | **not run.** No edit touches `cli.py`, `scanner.py`, `prepare.py` or `publish.py`, and no test in this change executes a line of them. Stated as not-run rather than reported as passed |

The collection baseline was measured by stashing `src/` and `tests/`, collecting, and restoring — so
the +7 is a counted delta, not a reconciled-by-hand number.

## 4. Decision recorded

**D1 — option 1 of the issue: a free-text key in front of the existing file path, not in place of it.**
Option 2 (make `study_design` accept inline text too) is rejected for the reason the issue gives — it
makes one key mean two things — and option 3 ("keep it and say so") is delivered as a by-product, since
§2.1.1 and §2.1.2 now say it where a TOML author looks.

## 5. Deviations and findings, stated

1. **The feature document was written after the first source edit.** `odd/README.md` asks for it before,
   and this change did not honour that. Recorded as D6 in `odd/tasks/curation-rationale-key.md` and in
   `design.md` §4 rather than quietly re-ordered. The red-green half of the contract did hold.
2. **The first draft of the spec left a contradiction.** §2.1.2's #291 paragraph ended with "it has no
   free-text key of its own"; a naive extension kept that sentence beside the new clause. It was
   removed and the section was delegated to a new clause. This is the reason the change carries a
   `MODIFIED Requirements` delta instead of an `ADDED` one.
3. **A pre-existing red gate nobody in this change touched.** `uv run ruff format --check .` (bare, not
   the scoped CI gate) fails on `README.md:166` and `README_ES.md:174` — comment alignment drift inside
   the MCP example block. CI is green because its gate is `uv run ruff format --check src/ tests/`.
   Reported, deliberately not fixed: unrelated scope.
4. **A reconnaissance subagent stalled.** The `gentle-ai-explore` task that was to map the four open
   issues' change surface hung for 30 minutes inside `codegraph` and was killed by its timeout; the
   mapping was completed inline. Cost, not correctness — but it is why the recon batch was larger than
   planned.

## 6. Follow-ups this change creates

- **The `init` template still writes no card-section keys.** Neither #291's five nor this one. A
  `sofer init` user gets a `[meta]` block with `description`/`license`/`source`/`tags` placeholders
  and must learn the rest from the spec. Not in this issue's scope; noted because the same
  discoverability gap is what #318 addressed for the README.
- **#323's `sofer_meta_set` must cover this key too.** A tool that writes `[meta]` keys and does not
  know about `curation_rationale` would leave a gap in exactly the flow it exists to serve.
- **#291's placeholder gate (#288's detector) must know the key.** It currently checks the four scalar
  placeholders; `curation_rationale` is a fifth scalar a reviewer may want gated.
