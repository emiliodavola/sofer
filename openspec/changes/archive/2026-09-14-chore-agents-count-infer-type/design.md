# Design: chore-agents-count-infer-type (issue #162)

**Status**: complete (ready for tasks) · **Change**: `2026-09-14-chore-agents-count-infer-type`
**Branch**: `chore/162-agents-count-infer-type` (`.git/HEAD` → `ref: refs/heads/chore/162-agents-count-infer-type`)
**Phase**: design — apply blueprint. Spec delta PB-11/PB-12 already written (ADDED). Strict-TDD off. 3 files / ~30 lines → single PR.

## D1 — `AGENTS.md` rule 6 (line 44): exact replacement text

Pre-change: `- 1149 tests currently pass (1151 collected, 2 skipped) — never reduce coverage.`

Post-change (replaces that line verbatim; no other line of rule 6 is touched):

```markdown
- Never reduce coverage. The authoritative tally is what `uv run pytest tests/ -q` reports on your branch —
  re-derive it, never trust a figure here. Observed on this branch: <P> passed, <S> skipped (<C> collected).
```

- (a) Floor intent intact — the lead sentence keeps the prohibition unchanged.
- (b) No silently-staling literal — the figure is labelled an *observation*, never the floor's support, and the
  line itself says to re-derive it; nothing in rule 6 depends on it staying true.
- (c) The reproducing command is named in the rule text → PB-11 scenario 1.
- `<P>/<S>/<C>` are **measurements, not choices**: apply pastes them from its recorded post-change
  `uv run pytest tests/ -q` run (PB-11 scenario 2: any recorded figure matches that command's tally). No wording
  is left for apply to invent.

## D2 — `tests/test_codebook.py` migration shape

1. Delete the single import line `_infer_type,` (L11) — the block is alphabetical, nothing else reorders.
2. Banner L23 `── _infer_type ──` → `── infer_column_type ──`.
3. `TestInferType` (L25-53) → **`TestInferColumnTypeSamples`**, docstring
   `"""Sample-value cases for the public infer_column_type (issue #162 migration)."""` — a class named after the
   private alias is a lie once the alias is gone. All **9 call sites** (L28/31/34/38/41/46/49/52/53) keep identical
   inputs and identical expected outputs, now calling `infer_column_type`.
4. `TestInferColumnType` docstring (L57) → `"""Public infer_column_type — API surface and representative expected
   outputs."""` (current text names the deleted symbol).
5. `test_returns_same_as_private` (L64-73) is **deleted**, replaced by
   **`test_representative_cases_expected_outputs`**: the same four `(values, expected)` cases, asserted once each
   against the live API (4 assertions). The 4 discarded `== _infer_type(values)` assertions were exact duplicates
   of the 4 kept `== expected` assertions over identical inputs (the alias merely delegates) → **no distinct
   assertion lost**; stated explicitly rather than glossed.

**Pre-migration baseline (parity target for verify)** — 9 sample cases (verbatim inputs → outputs):
`["1","2","3","4"]`→numeric, `["1,5","2,0","3,7"]`→numeric, `["red","blue","green","red"]`→categorical/text,
`["1","2","three","4"]`→`"mixed" in`, `["","NA","MISSING"]`→categorical/text, `["10","","20","NA","30"]`→`"mixed" in`,
`["NA","NA",""]`→categorical/text, `["42"]`→numeric, `["hello"]`→categorical/text. Plus the 4 parity cases
`["1","2","3"]`→numeric, `["red","blue"]`→categorical/text, `["1","two","3"]`→mixed (mostly numeric),
`["NA","","MISSING"]`→categorical/text. **Post-migration: 13 cases / 13 primary assertions — none added, none dropped.**

## D3 — delete `_infer_type` (`src/sofer/codebook.py:60-71`, −12)

Safe by evidence: repo-wide search finds only the definition and `tests/test_codebook.py`; every other hit is prose
under `openspec/changes/archive/**`. Canonical `openspec/specs/repo-compliance/spec.md:1494` only records a past
rename, it does not require the alias. **`codebook.py` has no per-file floor** — COV-01 = `profile.py` /
`mcp_registration.py` / `verification.py`, COV-06 = `cli.py`/`scanner.py`/`prepare.py`/`publish.py`
(`scripts/check_core_coverage.sh` loops exactly those four) — so deleting fully-covered lines cannot drop a scoped
gate; TOTAL is re-measured against the config-owned `fail_under = 90` (`pyproject.toml:98`).

**Compatibility note (verbatim, PR description + release notes):** "Removes the private, deprecated alias
`sofer.codebook._infer_type`. It was uncalled anywhere in the repository (tests included); use the public
`sofer.codebook.infer_column_type` instead. No public API changes."
**Option (A) stays the documented fallback** if a reviewer objects: keep the alias behind a `pytest.warns` test in
place of the parity test — same acceptance criterion (zero `DeprecationWarning`s), but A leaves dead code and a
warning surface, so B is chosen.

## D4 — requirement numbering / merge-ordering hazard

`openspec/specs/process-boundary/spec.md` on this branch ends at **PB-09** (highest match, L226). **PB-10 belongs to
the unmerged sibling `2026-09-14-chore-ruff-format-drift` (PR #196).** This delta uses PB-11/PB-12, which read
correctly only if PB-10 lands first. Constraint: **PR #196 must merge before this change's PR**, and the archive step
must insert PB-11/PB-12 *after* PB-10 without renumbering anything. If the ordering cannot be honoured the breakage is
a **gap PB-09 → PB-11**; requirement IDs are labels, so the gap is cosmetic and **must not be "fixed" by renumbering a
merged requirement** — report it instead.

## D5 — rejected alternatives

| Alternative | Why rejected |
| --- | --- |
| Keep the alias + `pytest.warns` test | Leaves a warning surface and dead code; pinning the deprecation is not the fix. Documented as the fallback (D3) |
| `filterwarnings = error::DeprecationWarning` in `pyproject.toml` | Turns a suite-wide pytest policy change into this chore (`[tool.pytest.ini_options]`, L83) and surfaces unrelated third-party warnings; the delta declares it out of scope |
| Test asserting `AGENTS.md`'s count equals a computed count | A fourth file outside the declared scope (precedent `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate`). The honest fix is to stop hardcoding (D1) — recorded as an **explicit follow-up**, not silenced |

## D6 — blast radius, rollback, verification

| File | Change | Est. |
| --- | --- | --- |
| `AGENTS.md` | rule 6 line 44 replaced (§D1) | ~−1/+2 |
| `tests/test_codebook.py` | import −1, banner, class rename + docstring, 9 call sites, parity test replaced | ~−15/+14 |
| `src/sofer/codebook.py` | `_infer_type` deleted | −12 |

**Rollback**: single-commit revert of the three-file diff. No data, migration, feature flag, config or CI change; the
suite is green in both states.

**Verification**: `uv run pytest tests/ -q` green with **zero** `DeprecationWarning` lines · `uv run pytest
tests/test_codebook.py -q` green · same with `-W error::DeprecationWarning` · `uv run mypy src/` clean · `uv run ruff
check src/ tests/` and `uv run ruff format --check src/ tests/` clean · `bash scripts/check_core_coverage.sh` exit 0
(four modules 100%) · `uv run coverage report -m` TOTAL ≥ 90 · `_infer_type` repo-wide search → zero hits outside
`openspec/changes/archive/**` · **behavioural-parity diff**: post-change `(values, expected)` list equals the §D2
baseline case-for-case (13 cases).

PB-11 (2 scenarios) and PB-12 (3 scenarios) map 1:1 to those commands per the delta's `## Test Mapping`; only the
parity row is pytest-asserted, and this design does not upgrade the others' declared strength.

---

## Output contract

- **status**: complete
- **executive_summary**: D1-D4 above. Anchor is the command, not the number; the migration preserves all 13 cases via
  `infer_column_type`; the private uncalled alias goes (it backs no coverage floor); PR #196 (PB-10) is a merge
  prerequisite and no requirement is renumbered.
- **artifacts**: `openspec/changes/2026-09-14-chore-agents-count-infer-type/design.md` + Engram mirror
  `sdd/2026-09-14-chore-agents-count-infer-type/design`.
- **next_recommended**: tasks — §D1 wording, §D2 five steps, §D3 deletion, §D6 commands + parity diff, then `tasks.md`.
- **risks**: see D5/D6 and the chat return.
- **skill_resolution**: `none` — no skill paths injected, no design-phase executor skill in the available set, no
  fallback lookup performed.
