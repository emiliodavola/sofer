# Apply Progress — 2026-09-15-chore-type-gate-policy

Change: `2026-09-15-chore-type-gate-policy` (issue #201)
Branch: `chore/201-type-gate-policy` (from `dev@8184ffb`)
Date: 2026-09-15

Scope executed: the two recorded policy decisions (Q1 `tests/` excluded, Q2 pyright adopted as a real gate), the maintainer's `[tool.mypy] strict = true` + `python_version = "3.11"` edits, the exact pinning of both analyzers, the 17-site type cleanup, the durable records (CI-09 delta + the CI-07 amendment), and the six documentation surfaces.

## 1. Work units landed

| Unit | What | Evidence |
|---|---|---|
| Phase 1 — guards first | G1–G7 added to `tests/test_ci_workflows.py` (7 tests) + module docstring enumeration reconciled (CI-01..CI-09, 23 rows, 6 non-row tests) | red set captured BEFORE the config existed: G1/G3/G4/G7 red, G2/G5/G6 green (`4 failed, 26 passed`) |
| Phase 2 — configuration | `[tool.pyright]` (mode `standard`, `pythonVersion` 3.13, `include` src/+scripts/, `exclude` tests/, `stubPath`, venv declared, `reportMissingImports` posture), `typings/tomli-stubs/__init__.pyi` + sdist exclusion, CI `lint` step `run: uv run pyright`, local pre-commit `pyright` hook | `uv run pyright` → 6 errors (after Phase 3: **0 errors, 4 warnings**) |
| Phase 3 — source fixes | 17 sites across 9 files (see §2) | mypy `Success: no issues found in 33 source files`; pyright `0 errors` |
| Phase 5 — documentation | `CONTRIBUTING.md` §Type checking rewritten (both checkers, `tests/` excluded by policy, both pinned exactly), `AGENTS.md` rules 5 + 12, mirrored README/README_ES bullet, PR-template checklist item | G4 green |
| Phase 6 — spec delta (authoring only) | `openspec/changes/2026-09-15-chore-type-gate-policy/specs/ci/spec.md`: `## ADDED` CI-09 (5 scenarios + 5 Test Mapping rows) + `## MODIFIED` CI-07 (`python_version` clause only, COR-5 backticked marker) | `grep -c "^#### Scenario:"` → 5; `grep -c "\| CI-09 \|"` → 5; `grep -c '"3\.10"'` → 0 |

## 2. The 17-site type cleanup (all green)

| # | site | gate | resolution |
|---|---|---|---|
| 1 | `_mirror.py:77` | mypy | `entry: FileEntry` (design DC-4: `str` would have created a new error) |
| 2-3 | `_clean.py:58`, `:183` | mypy | `cfg: DatasetConfig` + `TYPE_CHECKING` import |
| 4 | `mcp_server.py:691` | mypy | `_read_toml_text` now version-gates the import (`if sys.version_info >= (3, 11)`) so a static checker evaluates exactly one arm |
| 5 | `publish.py:70` | **mypy + pyright** | `from huggingface_hub.errors import RepositoryNotFoundError` (public path; verified on hf 1.25.1) |
| 6 | `_converters.py:614` | **mypy + pyright** | `vals: list[object] = list(row) ...` (one annotation satisfies both checkers — the design's `Sequence` proposal proved unnecessary empirically) |
| 7 | `_converters.py:650` | pyright | the `if "raw_rows" in locals(): del raw_rows` block replaced by an explicit `raw_rows = []` rebind (frees the same list; removes the diagnostic static checkers cannot model) |
| 8-11 | `cli.py:465`, `config.py:151`, `mcp_registration.py:128`, `model.py:411` | pyright | one committed stub `typings/tomli-stubs/__init__.pyi` via `stubPath` — no dependency added, `cli.py` (rule 14) untouched |
| 12-13 | `prepare.py:445`, `publish.py:686` | pyright | per-line `# pyright: ignore[reportAttributeAccessIssue]` on the duck-typed `sys.stdout.reconfigure` (narrowing to `isinstance` would break the `_FakeStdout` tests) |
| 14-17 | `verification.py:97` (kills :101/:103/:116) | pyright | `actual_splits = [str(name) for name in ds.keys()]` — one coercion resolves the `str \| NamedSplit` family |

Maintainer-authored edits folded into this change (recorded, not re-litigated): `[tool.mypy]` `strict = true` + `python_version = "3.11"`; the completed `[[tool.mypy.overrides]]` block; runtime deps `datasets>=5.0.1` (`verification.py`'s optional guard is preserved, not deleted) and `numpy<2.3`; dev deps `types-openpyxl`, `types-pyyaml` (which retired the `metadata.py:239` diagnostic) and `pyright`; `mypy==2.3.0` exact pin (COR-6).

## 3. Evidence (raw)

```text
$ uv run mypy src/ scripts/
Success: no issues found in 33 source files

$ uv run pyright
0 errors, 4 warnings, 0 informations
# the 4 warnings are reportMissingModuleSource on the four tomli fallback sites: the stub
# supplies the types, and on the 3.13 gate interpreter that import genuinely has no source.
# The gate fails on errors only (D2); the summary is recorded so a future jump is visible.

$ uv run pytest tests/test_ci_workflows.py -q
1 failed, 29 passed in 0.39s
# the single failure is G7 (test_ci07_names_the_declared_mypy_language_level): RED BY DESIGN
# until sdd-sync lands the CI-07 amendment in the canonical spec.

$ uv run pytest tests/ -q
1 failed, 1791 passed, 6 skipped, 1 warning in 65.49s
# (the same G7; +6 tests vs the dev baseline of 1785 passed — the guard block)

$ uv run ruff check .
All checks passed!
$ uv run ruff format --check src/ tests/ scripts/
68 files already formatted

$ bash scripts/check_core_coverage.sh
src\sofer\cli.py | src\sofer\scanner.py | src\sofer\prepare.py | src\sofer\publish.py → 100% each
exit=0
```

## 4. Deviations and adjudications

| # | Item | Disposition |
|---|---|---|
| COR-1 | design DC-2 claimed `ignore_missing_imports = false`; the tree has `true` | `mypy_path = "typings"` dropped; the stub is a pyright-only artifact; `[tool.mypy]` gained zero lines |
| COR-2 | `metadata.py:239` retired by `types-pyyaml` | resolution removed from the table |
| COR-3 | `_converters.py:620` re-classified dual-gate | satisfied by the single binding annotation at `:614` (§2 row 6) |
| COR-4 | CI-07 `python_version` clause stale after the maintainer's `"3.11"` decision | amended **inside this change** as a recorded, authorized exception to the earlier CI-01..CI-08 non-goal; wording frozen; G7 enforces agreement |
| COR-5 | G7(b) vs the `(Previously: …)` marker | G7 kept as implemented (strong file-wide absence check); the marker writes the retired value backticked (`` `3.10` ``); `grep -c '"3\.10"'` on the delta → 0 |
| COR-6 | mypy pin (maintainer: "version the mypy changes too") | `mypy==2.3.0` (exact, matches `uv.lock`) + G5 generalized and renamed to `test_analyzer_dev_pins_are_exact_and_match_the_lock` |
| COR-7 | CI-07 Occurrence 1 join (frozen clause ends with `.`, canonical text continues with `,`) | sync resolves it as a new sentence — `The CI test matrix SHALL keep exercising …`; an otherwise broken `change., the` join is not shipped |
| D-A | AGENTS rule 12 wording: design claimed the stub serves BOTH checkers; false for mypy | the applied sentence states the stub serves pyright while mypy resolves the same sites through the global `ignore_missing_imports = true` — shipping the frozen sentence would have documented a false contract |
| D-B | `uv run ruff format --check .` is red on two README code blocks | pre-existing at base (`git show HEAD:README.md` byte-identical there), outside the repo's gate form (`src/ tests/ scripts/` green), and exactly the class PB-14 documents (the hook's `types_or` is a pre-commit filter, not a ruff setting) — left untouched |
| D-C | `uv.lock` diff is ≈+1500/−19 vs `dev` | the maintainer's in-tree dependency regeneration (datasets/pandas/numpy stack, `types-*`, `pyright`); the pin flip itself moves exactly one recorded specifier line. Disclosed in the PR body because the diff exceeds the 400-line threshold on its own |

## 5. Verify-phase carry-forward

1. **G7 is red by design** and must go green after `sdd-sync` writes the CI-07 amendment + the CI-09 block into `openspec/specs/ci/spec.md` — the post-sync re-run is the evidence.
2. The rule-14 rows were re-run **after** the `prepare.py` / `publish.py` edits: 4/4 at 100.00%.
3. `pyright` must be invoked as `uv run pyright` (bare/`uvx` inflate the diagnostics — evidence §7.1 of `evidence-type-gate-baseline.md`).
4. Rollback: one commit; `git revert` restores every touched file, and the canonical spec is untouched until `sdd-sync`.
5. No `# pragma: no cover` was added anywhere; no coverage floor, test count or matrix entry was weakened.

## 6. Post-verify dispositions (verified PASS WITH WARNINGS, 2/2 requirements, 5/5 scenarios)

| Finding | Disposition |
|---|---|
| **W2** — the delta/AGENTS/stub still said "five `tomli` fallback sites" while `mcp_server.py` is now version-gated (a false contract about to be promoted canonically) | **FIXED.** The delta's CI-09 stub clause, `AGENTS.md` rule 12's appended sentence and the stub docstring now say **four** `try:` / `except ImportError:` sites (`cli.py`, `config.py`, `mcp_registration.py`, `model.py`) and name `mcp_server.py`'s version-gated fallback as needing no stub. The delta's `python_version` clause drops the numeral entirely ("the interpreter-selection fallbacks"). Rule 12's pre-existing sentence is CI-07-asserted content and is deliberately untouched — its module list is still the same five. |
| **W1** — the applied resolutions at `_converters.py` (sites 6/7) and `mcp_server.py` (site 5) diverge from the frozen design §5.2 while its tasks are marked `[x]` | **ADJUDICATED.** The divergence is measurement-driven: design DC-10's premise ("annotating `vals: list[object]` fails both checkers") is **empirically falsified** on this tree — `uv run mypy src/ scripts/` and `uv run pyright` both exit 0 with the maintainer's single annotation at `_converters.py:614`, and `Sequence` appears nowhere. Row 7 (`_converters.py:650`) is likewise resolved by the explicit `raw_rows = []` rebind rather than the design's sketch; row 5 (`mcp_server.py`) is resolved by the maintainer's `sys.version_info` gate, which prunes the stale arm statically instead of relying on the stub. Both gates green; recorded as COR-8 (design addendum) rather than silently diverging. |
| **W3** — task 3.9's SC-4c sensitivity probe (run the wrong variant first) has no pasted evidence | **SUPERSEDED BY MEASUREMENT.** The probe's purpose was to prove the rejected variant fails; it does not fail. Re-running it would require deliberately breaking a green tree to prove a falsified claim. The falsification itself is the evidence, recorded in W1 above and in COR-8. |
| **W4** — task 3.2's evidence line `grep -c "locals()"` returned 1, not 0 | **FIXED.** The comment now says "not a `del` behind a runtime membership test"; `grep -c "locals()" src/sofer/_converters.py` → **0**. |
| **W5** — 1956 changed lines raw (415 excluding `uv.lock`) exceed the 400-line canonical threshold and the 1500-line session budget; no `size:exception` accepted and no `ask-on-risk` pause taken | **ESCALATED TO THE MAINTAINER** (an exception is never inferred). The overage decomposes as: the maintainer's `uv.lock` regeneration (≈+1500, dominated by the `datasets`/`pandas`/`numpy` stack they explicitly chose to keep in this PR), the 7-guard block (+279, mandated by the design), the 17-site cleanup (~+50), and the docs/delta. Disposition recorded in the PR body. |

Post-fix re-run (this phase): `uv run pyright` → `0 errors, 4 warnings`; `uv run mypy src/ scripts/` → `Success: no issues found in 33 source files`; `uv run pytest tests/test_ci_workflows.py -q` → `1 failed, 29 passed` (the single failure is G7, red by design until `sdd-sync`).

### W5 — resolved: `size:exception` explicitly accepted

The maintainer explicitly accepted a **single PR carrying `size:exception`** for this change (2026-09-15). The exception is never inferred; it is recorded here as the human decision the design's non-goal required, and the PR body discloses the decomposition (the maintainer's `uv.lock` regeneration ≈+1500, the 7-guard block +279, the 17-site cleanup, the docs/delta).
