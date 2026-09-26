# Tasks: chore-ruff-format-hook-scope

Closes #216 — the `ruff-format` pre-commit hook rewrites `README.md` / `README_ES.md`, because
`ruff-pre-commit` widened its cached manifest's `types_or` to include `markdown` between 0.15.21 and
0.16.6 while `.pre-commit-config.yaml:7` declares no `types_or` of its own, so the upstream default *is*
the repository's scope (`2 files reformatted, 9 files left unchanged`, measured in #195). Fix: declare the
scope repo-side (`types_or: [python, pyi, jupyter]`), record why on the edited entry, and pin it with one
static guard test. Branch `chore/216-ruff-format-hook-scope` (from `dev`, clean tree).
Store: **hybrid** — this file + Engram mirror under topic key
`sdd/2026-09-15-chore-ruff-format-hook-scope/tasks`.

**Single work unit — do not split.** The YAML key, its rationale comment, the guard test, the module
docstring count, and the spec delta are one atomic unit: the guard is non-vacuous only against the
declared key, the comment exists only on that entry, and the delta is what the guard maps to (rule 6).
No `apply` task may be created for the delta — `specs/process-boundary/spec.md` is **already written and
final** by the spec phase (PB-14, 2 scenarios, `## Test Mapping` rows); apply consumes it as read-only
context and MUST NOT edit it (`sdd-sync` is what promotes it into `openspec/specs/process-boundary/spec.md`).

**Phase routing.** `strict_tdd: false` (`openspec/config.yaml`), but this change has a real test-first
carrier: the design's guard test is red against the unfixed entry and green after the YAML line (design
§3), so the tasks below are ordered strictly RED → GREEN, then the design §6 verify commands. No
TRIANGULATE / REFACTOR task exists — the change has no logic to triangulate. Enforced commands:
`uv run pytest tests/ -q`, `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/ scripts/`.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~71 (60–80) — `.pre-commit-config.yaml` 6 (1 key + 5 comment lines), `tests/test_ci_workflows.py` ~20 (guard test + docstring `four`→`five`), delta ~45. SDD phase artifacts (`proposal.md` / `design.md` / this file) are not counted as product size (#177 / #195 precedent) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR — one atomic unit (~71 lines vs the 400-line canonical threshold and the 1500-line review budget) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**Budget note.** `auto-chain` is the session's delivery strategy, but chaining is not *selected* here:
~71 lines is two orders of magnitude inside the budget, `ask-on-risk` does not fire, and the natural slice
(config + guard test + delta) is exactly the unit that rule 6 forbids splitting. The PR, the bounded review,
and the OpenSpec lifecycle (sync + archive) are **parent-owned** and are deliberately not tasks in this file.

## Phase 1: RED (guard test must fail before the config line lands)

- [x] 1.1 In `tests/test_ci_workflows.py`, append `test_ruff_format_hook_excludes_markdown` **immediately after** `test_contributing_names_the_declared_ruff_version` (that function ends at line 488) using the verbatim body from design §3 — reusing the module's existing `_load_yaml` and `_RUFF_PRE_COMMIT_REPO` only (no new import, helper, module, or dependency, AGENTS.md rule 4) — and update the module docstring (lines ~8–12): `plus four tests` → `plus five tests`, with the enumeration gaining `and the PB-14 hook-scope guard`. Assertion order is part of the contract: (1) exactly one `ruff-format` entry, (2) `types_or` present, (3) `isinstance(types_or, list)` (keeps assertion 4 non-vacuous against a scalar `types_or: markdown` substring match), (4) `"markdown" not in types_or`. <!-- sdd-owner: implementation -->
  - **Verify (V1):** `uv run pytest tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown -q` → `1 failed`, message "the ruff-format hook entry must declare \`types_or\`" (the unfixed entry has no `types_or` key).
  - **Evidence:** that exact failure output, pasted in the verify report (red half of PB-14 S1).

## Phase 2: GREEN (the one declaration)

- [x] 2.1 Add `types_or: [python, pyi, jupyter]` plus its 5-line rationale comment to the `ruff-format` hook entry in `.pre-commit-config.yaml`, text and indentation exactly as design §4: `- id: ruff-format` at 6 spaces, the comment lines and the `types_or` key at 8 spaces, flow-sequence list, no trailing comment on the decision line, comment placed immediately above the line it justifies (`pyproject.toml:63-66` precedent). Nothing else in the file changes — no `rev` move, no new repo, no touch of the `ruff` / `mypy` entries. <!-- sdd-owner: implementation -->
  - **Verify (V2):** the same test ID → `1 passed`.
  - **Verify (V7):** `uv run pytest tests/ -q` → green, **exactly +1 collected**, 0 failures, 0 new skips; the module docstring count now reads `five`.
  - **Evidence:** both command outputs and exit codes, pasted (green half of PB-14 S1).
  - **Delta is already done:** confirm `specs/process-boundary/spec.md` exists under the change dir and is final (PB-14 + 2 scenarios + `## Test Mapping`, with the PB-01..PB-13 backfill stated as a named non-goal). Do **not** edit it in apply; `sdd-sync` appends it to the canonical spec after PB-13.

## Phase 3: Full verify (design §6 V3–V10 — V1 / V2 / V7 are discharged by 1.1 and 2.1)

**The #195 trap, stated for the record — applies to 3.1 and 3.2.** The hook's `entry` is
`ruff format --force-exclude`, a **fixing** surface that exits 0 *after* rewriting files. Exit 0 alone
proves nothing; the discriminating evidence is the hook's **file-list output** plus the empty
`git diff --stat`. Second half: pre-commit detects modification via `git diff`, which cannot see an
untracked file — `README.md` is tracked, so the check is sound on it and no untracked probe is used.

- [x] 3.1 **AC1 (R1 acceptance gate) / V3** — run `uv run pre-commit run ruff-format --files README.md`: the hook MUST report `ruff-format....(no files to check)Skipped` and exit 0, proving the config-level `types_or` **replaces** (does not merge with) the manifest's. If `README.md` is still handed to ruff, the override is a no-op — stop, the fix has not landed. <!-- sdd-owner: implementation -->
  - **Evidence:** the hook's name / Skipped line and the exit code, pasted verbatim.
- [x] 3.2 **AC2 / V4 + V5** — run `uv run pre-commit run ruff-format --all-files`: expect a file list containing only `.py` / `.pyi` / `.ipynb` paths (the 68 tracked Python files), with **no** `.md` path, **no** `2 files reformatted`, and **no** `files were modified by this hook`, exit 0; immediately after, `git diff --stat -- README.md README_ES.md` MUST be empty (exit 0) — `--all-files` was the mutator in #195. <!-- sdd-owner: implementation -->
  - **Evidence:** the full `--all-files` output (file list + exit code) beside the empty `git diff --stat -- README.md README_ES.md`.
- [x] 3.3 **R2 / V6** — run `uv run python -c "import identify as i; print([t in i.tags_from_filename(f) for t, f in (('python','x.py'),('pyi','x.pyi'),('jupyter','x.ipynb'))])"` → `[True, True, True]`, proving each declared tag resolves as a real identify type tag and the declaration is not silently inert. `identify` 2.6.19 is already a `pre-commit` dependency (`uv.lock:836`), so no manifest edit is needed or allowed. <!-- sdd-owner: implementation -->
  - **Evidence:** the printed list and exit code.
- [x] 3.4 **V8** — `uv run ruff check src/ tests/ scripts/` and `uv run mypy src/ scripts/` → both clean (the repository's enforced commands; AGENTS.md rule 5). <!-- sdd-owner: implementation -->
  - **Evidence:** both commands' output and exit codes.
- [x] 3.5 **V9 (diff-path assertion)** — `git diff --stat` contains **exactly** `.pre-commit-config.yaml`, `tests/test_ci_workflows.py`, the change's spec delta, and the SDD phase artifacts under `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/**`; **zero** paths under `pyproject.toml`, `.github/workflows/**`, `src/sofer/**`, `README.md`, `README_ES.md`, `uv.lock`. Any other path is a scope violation — stop and revert, do not absorb. <!-- sdd-owner: implementation -->
  - **Evidence:** the `git diff --stat` output with each prohibited path asserted as absent (0 matches).
- [x] 3.6 **V10 (no gate armed)** — `git grep -n "format --check" -- .github/workflows/` and `git grep -n "pre-commit" -- .github/` → **zero** matches each, before and after, so PB-10's *No CI gate was armed* scenario keeps passing and #194 keeps ownership of (and the path scope of) any future `ruff format --check` gate. <!-- sdd-owner: implementation -->
  - **Evidence:** both grep results (0 matches) and the absence of `.github/` in the diff.

## Rollback

Revert the single commit: the `types_or` key and its comment, the guard test, the docstring `four`→`five`
change, and the delta all disappear. The canonical `openspec/specs/process-boundary/spec.md` is untouched
until `sdd-sync`, so a pre-sync revert restores the specs byte-for-byte. No runtime, data, dependency,
artifact, CI, or version change; `types_or` alters neither the `rev`, nor the `language`, nor any
`additional_dependencies`, so the cached hook environment stays valid and no `pre-commit clean` is needed.

## Out of scope (explicit non-goals — do not do these in this change)

Do not touch the stale module-docstring rows in `tests/test_ci_workflows.py` that predate CI-07/CI-08
(row-count claims) — only the cross-capability `four`→`five` count and its enumeration, because this
change's guard is the cause. Also out: `CONTRIBUTING.md:77` (#187), `AGENTS.md` rule 5 /
`openspec/project.md` (#184 / #214), any edit to `pyproject.toml` (`[tool.ruff]`, `extend-exclude`,
`required-version`, `line-length`), the `ruff-pre-commit` `rev` bump (#195), any `ruff format --check`
gate or CI/workflow change (#194), any `src/sofer/**` path, any `README.md` / `README_ES.md` edit
(rule 13 byte-identical), `uv.lock`, the canonical `openspec/specs/**` (sync-phase only), and the
PB-01..PB-13 `## Test Mapping` backfill. Do not commit, push, or open a PR — delivery and the OpenSpec
lifecycle are parent-owned.
