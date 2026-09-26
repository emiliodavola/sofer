# Tasks: chore-type-gate-policy

**Change** `2026-09-15-chore-type-gate-policy` (GitHub **#201**) · branch `chore/201-type-gate-policy`
· store **hybrid** — this file plus the Engram mirror under topic key
`sdd/2026-09-15-chore-type-gate-policy/tasks`.

**Inputs read this phase, directly**: `design.md` — **revision 2**, the apply blueprint (the 17-site
resolution table §5, the frozen `[tool.pyright]` block §3, the `tomli` stub §4, guards G1–G7 §8, the CI-09
delta **and** the CI-07 amendment §6/§6.6, the SC-1…SC-8 verify plan §9, the corrections log COR-1…COR-4 §2,
the workload forecast §10.2, and §13's eight ordered steps) and `evidence-type-gate-baseline.md` — **§7 and
§8 authoritative** (§8 is the post-maintainer-edit re-measurement; §7.3 is superseded where §8 differs).
There is **no separate `sdd/{change}/spec` artifact**: this change has no legacy flat
`openspec/changes/<change>/spec.md`, and the `ci` delta is authored in Phase 6 below
(design §6.1 "Domain hygiene"). Engram context consulted: design #1297, proposal #1296, explore #1295.

**One-line outcome**: `tests/` stays out of **both** type gates and pyright becomes a **real** gate — one
`[tool.pyright]` table, one committed `tomli` stub, one exact dev pin reaching CI through `uv.lock`, one CI
`lint` step, one pre-commit hook, seven new static guards, a durable `ci` CI-09 requirement **plus** the one
authorized CI-07 clause amendment, and the 17 measured diagnostics cleared under mypy `strict = true`.

**Already in the tree — inputs, not tasks** (evidence §8.5 #2–#3; design §3 "the maintainer's committed block
is an input"): `pyproject.toml` carries `[tool.mypy] python_version = "3.11"`, `strict = true`,
`ignore_missing_imports = true`, the completed `[[tool.mypy.overrides]]` block, runtime `datasets>=5.0.1` +
`numpy<2.3`, dev `types-openpyxl`, `types-pyyaml`, `pyright==1.1.414`; `uv.lock` is regenerated and `uv sync`
has run. **No step below edits any of them** (design §14: "neither adds nor removes them").

---

## TDD posture — stated honestly: there is no classic RED for a config-policy change

`openspec/config.yaml` sets `strict_tdd: false`. More importantly, **this change has no production behaviour
to drive red-first**: it declares a posture (config), resolves 17 static diagnostics, arms a gate, and writes
documents. A manufactured "failing test first" would have to be a test of behaviour that does not exist —
theatre, not TDD.

The **only** honest red-then-green carrier is the **guard block G1–G7** (design §8/DC-5), and it is a real
one: at Phase 1 the guards run against a tree that has no `[tool.pyright]`, no stub, no CI step, no hook and
unamended `CONTRIBUTING.md`, so they fail for the exact reasons the change exists. The recorded red set is
**{G1, G3, G4} failing, {G2, G5, G6} passing as tripwires, G7 failing** (G7 stays red until the canonical
spec is synced in Phase 6). No other failing test is created, and **REFACTOR has no target**: the only
restructure (`_converters.py` site 7) is behaviour-preserving by construction and is proven by the existing
converter tests, not by a new refactor pass (task 3.7).

#### RED → GREEN → TRIANGULATE mapping

| Step | RED | GREEN | TRIANGULATE |
| --- | --- | --- | --- |
| Phase 1 | G1/G3/G4/G7 fail on the committed tree | — | — |
| Phases 2–6 | — | G1 (P2), G3 (P4), G4 (P5), G7 (P6) | Phase 3's mutation probes: the SC-4c sensitivity probe (wrong variant **first**), the src/ red-first gate probe, and the SC-3b `tests/`-is-out probe |
| — | — | — | REFACTOR: **not applicable** — task 3.7 records why |

---

## Phase routing and sequencing rules

| Rule | Value |
| --- | --- |
| `strict_tdd` | `false` — see the section above; the guard block is the whole red carrier |
| **Hard ordering 1 — guards first** | **Phase 1 must complete before Phase 2.** The honest red set must be captured against a tree with **no** `[tool.pyright]`, **no** stub, **no** CI step and unamended docs. Landing the config first would leave the guards green from birth and destroy the only evidence the change has |
| **Hard ordering 2 — the SC-4c wrong variant runs FIRST** | Task 3.6(i) **must** run before task 3.6(ii). The probe's whole purpose is to show the *rejected* form failing; running it after the fix would prove nothing (design DC-10, §9 SC-4c) |
| **Hard ordering 3 — config before sources** | Phase 2 precedes Phase 3, so the frozen 13 pyright diagnostics are reproduced **under the committed config** before any of them is resolved (design §13 step 2's stated evidence) |
| **Hard ordering 4 — sync is coupled to CI-07** | **G7 stays red through Phases 1–5** and can only go green when the CI-09 block **and** the CI-07 amendment land in the same `sdd-sync` operation (task 6.2). Never split them |
| **Hard ordering 5 — docs before spec** | Phase 5 (docs) precedes Phase 6, because G4's clause (d)/(e) reads `CONTRIBUTING.md` and the PR template, and G7's evidence must be taken on the final doc state |
| Ownership | Every checkbox below carries `<!-- sdd-owner: implementation -->` per the repo convention. No RDD authority/receipt/delivery-gate task is generated here |
| Other binding conventions | Rule 1 (no hardcoded values — the `[tool.pyright]`/pin literals are toolchain declarations, design §7.1/§10.2), rule 4 (reuse the module's existing helpers; add no new test file), rule 6 (every CI-09 scenario maps to a named guard — see the map below), rule 12 (COV-06 rows re-run because `prepare.py`/`publish.py` are edited), rule 14 (zero `# pragma: no cover`, four 100.00% rows) |

**Guard ↔ CI-09 scenario ↔ rule-6 map** (design §6.3/§6.4, §8):

| CI-09 scenario | Guard(s) in `tests/test_ci_workflows.py` | Red at Phase 1? |
| --- | --- | --- |
| S1 `tests/` stays out of both type gates | **G4** `test_mypy_and_pyright_exclude_tests` (a–e, incl. the PR-template clause folded in by DC-6) | **yes** |
| S2 `[tool.pyright]` declares the decided posture and the gate runs | **G1** `test_pyright_config_declares_the_decided_posture` + **G3** `test_ci_lint_job_runs_the_pyright_gate`; S2's "exit 0 + summary line" half = verify evidence SC-1 | **yes** |
| S3 exactly one pyright config home | **G2** `test_pyright_has_exactly_one_config_home` | no (tripwire) |
| S4 pin exact, reaches CI through the lock, matches the binary | **G5** `test_analyzer_dev_pins_are_exact_and_match_the_lock`; equality half = SC-2 | no (tripwire) |
| S5 adopting the gate leaves existing declarations intact | **G6** `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`; mypy-exit-zero half = SC-4 | no (non-regression) |
| CI-07 clause agreement (DC-11) | **G7** `test_ci07_names_the_declared_mypy_language_level` | **yes — red until Phase 6** |

---

## Review Workload Forecast

| Field | Value |
| --- | --- |
| Estimated changed lines | **≈205–275 apply-authored** (code + config + tests + docs), per design §10.2: `pyproject.toml` +17/−1 · `typings/tomli-stubs/__init__.pyi` +14 · `ci.yml` +2 · `.pre-commit-config.yaml` +7 · 8 `src/sofer/` files ≈15 (+9/−6) · `tests/test_ci_workflows.py` +125…+185 · `CONTRIBUTING.md` +18/−2 · `AGENTS.md` +3/−2 · `README.md`+`README_ES.md` +12 · PR template +3 · `openspec/specs/ci/spec.md` (sync) +60…+90. Excluded from the estimate because **not produced by apply**: the maintainer's `pyproject.toml`/`uv.lock` edits already in the tree (≈+52…+140, mostly mechanical lock) and the SDD artifacts (+300…+500 prose, not review load — repo precedent) |
| 400-line budget risk | **Low** (≈205–275 against 400; ≈17–29 % of the 1500-line session review budget) |
| Chained PRs recommended | **No** |
| Suggested split | **Single PR** against `dev`. The dominant review loads are the seven-guard block and the `[tool.pyright]` lines; both are bounded. The forecast does not move if DC-8 fallback 1 is taken (a `git mv`) or if the SC-4b floor probe forces site 4's per-line-ignore fallback (+2 comment lines) |
| Delivery strategy | **auto-chain** (session preference) — the risk is Low, so **no chain is selected** and `ask-on-risk` does not fire |
| Chain strategy | **pending** (chaining deferred until selected; not needed here) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**PR boundary (frozen).** One PR, one branch, **no chaining, no `size:exception`, no `ask-on-risk` pause**.
The guard tests are **never** split from the CI-09 scenario rows they satisfy (rule 6) and the CI-09 block is
**never** split from the CI-07 amendment (G7 couples them). Pre-sync, the change is one commit; if apply
lands a linear stack, it is squashed before the PR. Rollback handle: `git revert <commit>` — see Phase 8.

### Suggested Work Units

| Unit | Goal | Boundaries (start → finish · verify · rollback) |
| --- | --- | --- |
| 1 | Pre-flight baseline (tasks 0.1–0.4) | start: untouched tree on the branch · finish: three pasted measurements · verify: 6 mypy errors with §8.1 composition, 13 pyright errors pending config, `pyright 1.1.414`, re-derived suite tally · rollback: none (read-only) |
| 2 | Guards RED-first (tasks 1.1–1.5) | start: no guard exists · finish: G1–G7 present and the honest red set recorded · verify: `pytest tests/test_ci_workflows.py` shows G1/G3/G4/G7 failing, G2/G5/G6 passing · rollback: revert the guard block |
| 3 | Config + stub (tasks 2.1–2.4) | start: no `[tool.pyright]` · finish: `[tool.pyright]` + stub + sdist exclusion; G1 green; 13 pyright diagnostics reproduced · verify: `uv run pyright` = 13 errors; `uv run mypy` still 6 · rollback: revert `pyproject.toml` + delete `typings/` together |
| 4 | Sources — the 17 sites (tasks 3.1–3.8) | start: 6 mypy + 13 pyright errors · finish: both gates at 0 · verify: `mypy` exit 0, `pyright` `0 errors, 0 warnings`, SC-4c probe pasted, suite `check_core_coverage.sh` still four 100.00% rows · rollback: every edit is type-only/comment-only except sites 6–7, each independently revertible |
| 5 | Gates armed (tasks 4.1–4.3) | start: no pyright step/hook · finish: CI `lint` step + pre-commit hook; G3 green · verify: step `run == "uv run pyright"`, no workflow version literal · rollback: delete step + hook entry |
| 6 | Docs (tasks 5.1–5.5) | start: docs claim mypy-only · finish: both checkers documented on all four surfaces; G4 green · verify: `--word-diff` shows only the named spans; README/README_ES bullet parity · rollback: revert the five doc files (G4 goes red by design — that is the record working) |
| 7 | Spec delta + `sdd-sync` (tasks 6.1–6.3) | start: no `specs/ci/spec.md` in the change · finish: CI-09 + 5 rows + the two CI-07 occurrences landed in the canonical spec; G7 green · verify: SC-6/SC-6c greps · rollback: whole-change revert; pre-sync revert restores canonical specs byte-for-byte |
| 8 | Full verify + evidence (tasks 7.1–7.8, 8.1–8.2) | start: all gates green · finish: the verify-report input block · verify: SC-1…SC-8 with pasted output · rollback: none needed; residue is a failure |

---

## Phase 0 — Pre-flight: measure the untouched tree (design §13 step 0)

Step 0 is a **verification** of evidence §8.1/§8.2 on apply's own tree, not a gate on any design choice
(COR-1 removed the DC-2 contingency). Read-only; no edit in this phase.

- [x] 0.1 Confirm the branch is `chore/201-type-gate-policy` (not `dev`), and record
  `git status --porcelain` verbatim. The expected footprint is this change's SDD artifacts
  (`openspec/changes/2026-09-15-chore-type-gate-policy/**`) plus the maintainer's already-committed
  `pyproject.toml`/`uv.lock` state — anything else is a scope surprise to surface, not absorb. Do **not**
  commit, push, tag or open a PR at any point in this change.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the branch line plus the verbatim `git status --porcelain`.

- [x] 0.2 Re-measure the mypy half: `uv run mypy src/ scripts/; echo "exit=$?"`. Expected **exactly 6
  errors in 5 files (checked 33 source files)**, with evidence §8.1's composition — `_converters.py:620`
  `[arg-type]`, `_mirror.py:77` `[no-untyped-def]`, `_clean.py:58` `[no-untyped-def]`, `_clean.py:183`
  `[no-untyped-def]`, `publish.py:70` `[attr-defined]`, `mcp_server.py:691` `[no-any-return]`. Two negative
  assertions are part of the evidence: **no `metadata.py:239`** (`types-pyyaml` retired it, COR-2) and **no
  `tomli` diagnostic at all** (COR-1 — this is why `mypy_path` is dropped).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the verbatim error block + exit code, with the two absences stated explicitly.

- [x] 0.3 Confirm the pin and the second gate's pre-state: `uv run pyright --version` → `pyright 1.1.414`
  (the pin is live), and `uv run pytest tests/ -q` → **re-derive** the tally on this branch and paste the
  tail line. Evidence §8.4 records `1785 passed, 6 skipped, 1 warning`; treat it as context to compare
  against, never as a figure to copy (AGENTS rule 6).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the version line plus the actual passed/skipped tail line.

- [x] 0.4 Record the **R9 stop rule** before touching anything: if 0.2 shows a mypy diagnostic **outside**
  the six sites of evidence §8.1, apply resolves it with the §5 idioms (annotate the binding / annotate the
  parameter / public import path) and **reports the addition** — never a `# pragma: no cover`, never a
  config relaxation, never a new `# type: ignore` beyond site 4's documented fallback. If a *seventh* error
  appears in a rule-14 module, **stop and report** instead of improvising (design R9, §5.3).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the recorded rule in the apply progress, and either "six sites confirmed" or the escalation.

---

## Phase 1 — Guards first: the RED state (design §13 step 1)

**Hard ordering 1.** This phase must complete before Phase 2. These seven tests are the change's entire
red-first evidence.

- [x] 1.1 Append the guard block to the **end of `tests/test_ci_workflows.py`** (after the file's last
  existing test — re-read the tail immediately before appending; no line number from the design is an
  anchor). Contents, exactly as frozen in design §8:
  - the helper `_declared_pyright_version() -> str`, mirroring `_declared_ruff_version()` (`:92-118`) in
    shape and in its refusal to accept a floor: read `_load_toml("pyproject.toml")["dependency-groups"]["dev"]`,
    match each string entry with the existing `_DEV_ENTRY_RE`, require **exactly one** `pyright` entry, require
    `_EXACT_PIN_RE`, and return the version group. **The helper holds no version literal.**
  - the module constant `_SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "htmlcov", ".pytest_cache", "__pycache__"})`,
    placed with the other module constants.
  - the seven tests **verbatim by assertion set** (design §8's table):
    **G1** `test_pyright_config_declares_the_decided_posture` · **G2**
    `test_pyright_has_exactly_one_config_home` · **G3** `test_ci_lint_job_runs_the_pyright_gate` ·
    **G4** `test_mypy_and_pyright_exclude_tests` · **G5**
    `test_analyzer_dev_pins_are_exact_and_match_the_lock` · **G6**
    `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates` · **G7**
    `test_ci07_names_the_declared_mypy_language_level`.
  Reuse the module's existing helpers (`_read_text`, `_load_toml`, `_load_yaml`, `_workflow`, `_find_step`,
  `_DEV_ENTRY_RE`, `_EXACT_PIN_RE`) — **no new file, no duplicated parsing** (rule 4). G2's walk must assert
  it saw files, so it cannot pass vacuously. G7 must read `[tool.mypy] python_version` from
  `pyproject.toml` (**derived — no literal**) and assert `openspec/specs/ci/spec.md` names that value inside
  CI-07's block and contains the retired `"3.10"` value nowhere in CI-07's text. Docstrings on the helper
  and each test name the CI-09 scenario (and, for G7, the CI-07 clause) they assert.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the appended block's text plus `git diff --numstat tests/test_ci_workflows.py`.

- [x] 1.2 Run `uv run ruff format tests/test_ci_workflows.py`, then `uv run ruff check --fix tests/test_ci_workflows.py`,
  then `uv run ruff check tests/test_ci_workflows.py` → clean. One fix pass per warning, then surface — do not
  enter a third cycle.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the three commands' output and exit codes.

- [x] 1.3 **Capture the honest RED set** (this is the RED of the whole change): run
  `uv run pytest tests/test_ci_workflows.py -q` and record the exact pass/fail split. Expected:
  **G1, G3, G4 failing** (no `[tool.pyright]`; no CI step; `[tool.pyright] exclude` + the `CONTRIBUTING.md`
  section + the PR-template item all absent) and **G7 failing** (canonical CI-07 still says `"3.10"`);
  **G2, G5, G6 passing** as tripwires (no `pyrightconfig.json` exists; the pin and lock already landed; the
  existing mypy/ruff declarations are the status quo). Record each failing guard's assertion message
  verbatim; if the failures come from a missing file or a `KeyError` instead of the intended assertion, fix
  the guard — a guard that fails for the wrong reason is not evidence.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the pytest summary plus the four failing guards' assertion messages, and the statement
    that G2/G5/G6 passed.

- [x] 1.4 Static-red proof for G3's version half: `uv run pytest tests/test_ci_workflows.py -q -k "pyright"` and
  record it; the guard must be red on the *step* assertion today, not on the version-specifier scan (nothing
  in `.github/workflows/` declares a pyright version today either). Note explicitly that **G5 is green now**
  and would go red if `uv lock` ever drifted the resolved pyright version away from the dev pin — that is the
  tripwire's purpose, not a defect (design DC-5, §8).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the filtered run's output plus the tripwire statement.

- [x] 1.5 Confirm **no pre-existing test was modified**: `git diff --numstat tests/test_ci_workflows.py` shows
  the append's added lines only (no removals in existing tests), and paste the count of `def test_` functions
  before and after. This is SC-7's "tally increases by exactly 7" precondition.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the numstat line plus the two `def test_` counts (before → after, +7).

---

## Phase 2 — Config and stub: GREEN for G1 (design §13 step 2)

**Hard ordering 3.** Reproduce the frozen 13 pyright diagnostics **under the committed config** before
resolving any of them.

- [x] 2.1 Edit `pyproject.toml` — **insert** the frozen `[tool.pyright]` block, key for key (design §3),
  **after** the complete `[tool.mypy]` table *and* its following `[[tool.mypy.overrides]]` block, and
  **before** the `# ── pytest ──` separator (design's `:79-85` is a snapshot — re-read the region and anchor
  by those two content markers, then record the real insertion line). Include the block's rationale comment
  verbatim, and the eight keys exactly:
  `typeCheckingMode = "standard"`, `pythonVersion = "3.13"`, `venvPath = "."`, `venv = ".venv"`,
  `include = ["src", "scripts"]`, `exclude = ["tests", ".venv", "**/node_modules", "**/__pycache__"]`,
  `stubPath = "typings"`, `reportMissingImports = "error"`. **Do not add `mypy_path`** — COR-1 retracted it;
  `[tool.mypy]` gains **zero** lines from this change.
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff pyproject.toml` naming only the `[tool.pyright]` hunk, plus
    `grep -n "mypy_path" pyproject.toml` → **no match**.

- [x] 2.2 Edit `pyproject.toml` again — add the sdist isolation exclusion (DC-3), in a
  `[tool.hatch.build.targets.sdist]` table with its two-line comment and `exclude = ["/typings"]`. If the
  table already exists, add the key to it; never duplicate the table.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `grep -n -A3 "tool.hatch.build.targets.sdist" pyproject.toml`.

- [x] 2.3 Create `typings/tomli-stubs/__init__.pyi` (new file, PEP 561 stub-package layout — DC-8) with the
  docstring and `load` signature frozen in design §4.1 (`from typing import Any, BinaryIO` +
  `def load(fp: BinaryIO, /) -> dict[str, Any]: ...`). Only `load` is stubbed; `loads` is deliberately
  absent (a narrower stub is a smaller drift surface). The file must contain **no** `# pragma: no cover` and
  no executable statement.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the file's full text plus `ls -l typings/tomli-stubs/`.

- [x] 2.4 Reproduce the frozen baseline under the committed config: `uv run pyright; echo "exit=$?"` must
  report **13 errors, 0 warnings** with exactly evidence §7.2/§8.2's set — `_converters.py:620`,
  `_converters.py:650`, the five `tomli` sites (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`,
  `model.py`), `prepare.py:445`, `publish.py:686`, `publish.py:70`, `verification.py:101/103/116` — and **no
  phantom missing-import errors for `pyarrow`/`pydantic`/`fastmcp`/`huggingface_hub`** (that is the
  `venvPath`/`venv` declaration doing its job, DC-1). Then re-run `uv run pytest tests/test_ci_workflows.py -q`
  and confirm **G1 is green**, G3/G4/G7 still red, G2/G5/G6 still green.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the 13-error output, the absence of the five phantom import classes, and the updated
    guard split.

- [x] 2.5 **R3 fallback discipline (stop-and-report, do not silently substitute).** If the pinned pyright
  rejects the `typings/tomli-stubs/` layout in 2.4 (the five `reportMissingImports` diagnostics survive),
  take **fallback 1** — `git mv typings/tomli-stubs typings/tomli`, keeping `stubPath = "typings"` — and
  re-run 2.4. If fallback 1 also fails, **fallback 2 is an escalation, not a substitution**: it needs five
  per-line `# pyright: ignore[reportMissingImports]` comments plus a CI-09 S2 text amendment (S2 names
  `stubPath`), so **stop and report to the parent** with the observed output. Never delete `stubPath`,
  never add `tomli` to any dependency group (that breaks the `cli.py` COV-06 row — evidence §4.1), and never
  leave the tree in a half-migrated stub layout.
  <!-- sdd-owner: implementation -->
  - **Evidence:** either "frozen layout worked at step 0" or the fallback taken with its re-run output, plus
    the escalation record if step 2 was reached.

---

## Phase 3 — Sources: the 17 apply sites (design §13 step 3, §5)

**Per-file edit list — the complete, scoped roster.** Nothing outside this table may change in `src/`.
**Rule-14 modules among them: `prepare.py` (site 13) and `publish.py` (sites 4, 14)** — every edit on those
is comment-only or an import path, which is why the four COV-06 rows must be re-run in task 7.5. `cli.py`
(a rule-14 module) receives **zero** edits — that is the point of the stub route; `scanner.py` likewise.

| File | Site(s) | Anchored edit | Rule-14 |
| --- | --- | --- | --- |
| `src/sofer/_converters.py` | 6, 7 | `from collections.abc import Sequence` with the module's stdlib imports; `raw_rows: list[Sequence[object]] = []` at `:611` with `:614` left **unannotated**; the per-sheet loop restructure at `:609-650` | no |
| `src/sofer/_mirror.py` | 1 | `_is_convertible_entry(entry: FileEntry)` at `:77`; `FileEntry` added to the existing `if TYPE_CHECKING:` import block at `:24-25` | no |
| `src/sofer/_clean.py` | 2, 3 | new `from typing import TYPE_CHECKING` + `if TYPE_CHECKING: from .model import DatasetConfig` block; annotate `cfg: DatasetConfig` on both `allowed_output_remotes` (`:58`) and `clean_build` (`:183`, the existing `override` annotation is left as-is) | no |
| `src/sofer/publish.py` | 4, 14 | `from huggingface_hub.errors import RepositoryNotFoundError` replacing the `huggingface_hub.utils` import at `:70`; `# pyright: ignore[reportAttributeAccessIssue]` on the `sys.stdout.reconfigure` line at `:686` | **yes** |
| `src/sofer/mcp_server.py` | 5 | type the `_tomli.load(fh)` binding (`payload: dict[str, Any] = …` then `return payload`) at `:691` | no |
| `src/sofer/prepare.py` | 13 | `# pyright: ignore[reportAttributeAccessIssue]` on the `sys.stdout.reconfigure` line at `:445` | **yes** |
| `src/sofer/verification.py` | 15–17 | `actual_splits = [str(name) for name in ds.keys()]` at `:97` — one coercion at the binding site; `:101`, `:103`, `:116` are **not** edited | no |
| `src/sofer/cli.py`, `config.py`, `mcp_registration.py`, `model.py` | 8–12 | **0 lines** — resolved by the Phase 2 stub | `cli.py` stays pristine |
| `src/sofer/metadata.py` | — | **0 lines** — retired by `types-pyyaml` (COR-2) | no |

- [x] 3.1 Edit `src/sofer/_converters.py` site 6 — the **one** dual-gate fix. Add `from collections.abc import Sequence`
  (never `typing.Sequence` — ruff UP035) with the module's stdlib imports; at `:611` write
  `raw_rows: list[Sequence[object]] = []` with the two-line rationale comment frozen in design §5.2 site 6;
  and **remove** any pre-existing `vals: list[object] = …` annotation at `:614` so it reads
  `vals = list(row) if row is not None else []`. The comment must state that a tuple of openpyxl cell scalars
  is a `Sequence[object]` by covariance but **not** a `list[object]` by invariance — the single diagnostic
  both checkers report at the append below.
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff src/sofer/_converters.py` plus `grep -n "Sequence" src/sofer/_converters.py`.

- [x] 3.2 Edit `src/sofer/_converters.py` site 7 — the loop restructure. Move the per-sheet row-buffer
  initialisation to the top of the `for sheet_name in sheet_names:` iteration, carrying the frozen 5-line
  comment, and **delete** the three lines `# Clean locals for next iteration` /
  `if "raw_rows" in locals():` / `del raw_rows`. Do not touch the empty-sheet branch, the `else:` branch
  body, the `col_data` build or the parquet write. This removes pyright's `reportPossiblyUnboundVariable`
  by fixing the code, not by suppressing it (design §5.2 site 7's five-point behaviour-neutrality argument).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `grep -c "locals()" src/sofer/_converters.py` → **0**.

- [x] 3.3 Edit `src/sofer/_mirror.py` site 1 — annotate `entry: FileEntry` at `:77` and add `FileEntry` to
  the module's existing `if TYPE_CHECKING:` block at `:24-25` (already importing `DatasetConfig`). **Not
  `str`**: evidence §6's row 1 is corrected by DC-4 — `entry` is iterated from `cfg.files` at `:113` and the
  body reads `entry.recursive` / `entry.remote`, so `str` would create a *new* `attr-defined` error.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `grep -n "FileEntry" src/sofer/_mirror.py`.

- [x] 3.4 Edit `src/sofer/_clean.py` sites 2–3 — add `from typing import TYPE_CHECKING` and the
  `if TYPE_CHECKING:` block importing `DatasetConfig` from `.model`, with the frozen comment explaining that
  a runtime import would re-introduce the module-load cycle the unannotated `cfg` avoided; then annotate
  `cfg: DatasetConfig` at `:58` and `:183`. `from __future__ import annotations` is already present, so the
  annotations stay strings at runtime and the guarded import is never executed.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `grep -n "DatasetConfig" src/sofer/_clean.py`.

- [x] 3.5 Edit `src/sofer/publish.py` site 4 (the shared fix) and site 14:
  (a) replace `from huggingface_hub.utils import RepositoryNotFoundError` at `:70` with
  `from huggingface_hub.errors import RepositoryNotFoundError` — one edit clears mypy `attr-defined` **and**
  pyright `reportPrivateImportUsage`; `publish.py:69`'s `from huggingface_hub import HfApi` is untouched.
  (b) add `# pyright: ignore[reportAttributeAccessIssue]` to the `sys.stdout.reconfigure(encoding="utf-8")`
  line at `:686` (publish.py is **rule-14**: the ignore is a pyright comment, invisible to mypy, so it cannot
  trip `warn_unused_ignores` and executes nothing). Then run **SC-4b**: `uv run --with "huggingface-hub==0.26.0" python -c "from huggingface_hub.errors import RepositoryNotFoundError; print('ok')"`
  → `ok` (needs network; ephemeral env, `uv.lock` untouched). **If it fails**, take the documented fallback:
  keep the old import line and add `# type: ignore[attr-defined]` + `# pyright: ignore[reportPrivateImportUsage]`
  (comment-only), and **record the divergence** — this is an escalation, not a silent substitution.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the two diff hunks, plus the SC-4b command output (`ok`) or the recorded fallback.

- [x] 3.6 Edit `src/sofer/mcp_server.py` site 5 — annotate the `_tomli.load(fh)` binding as
  `payload: dict[str, Any]` and `return payload` at `:691` (`Any`/`dict` are already imported). The five
  `tomli` **import** sites are **not** touched by this change; the Phase 2 stub removed the diagnostic.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `git diff --numstat src/sofer/mcp_server.py`.

- [x] 3.7 Edit `src/sofer/verification.py` sites 15–17 — replace `actual_splits = list(ds.keys())` at `:97`
  with `actual_splits = [str(name) for name in ds.keys()]`. One coercion fixes all three downstream uses
  (`:101`, `:103`, `:116`); do **not** edit those three sites. Preserve `verification.py`'s
  `try: import datasets / except ImportError:` guard **byte-identical** — never delete it as "dead"
  (evidence §8.2: it stays mockable via `patch.dict(sys.modules, …)`, which is how the existing tests drive
  this function).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `git diff --numstat src/sofer/verification.py` → `1  1`.

- [x] 3.8 Edit `src/sofer/prepare.py` site 13 — add `# pyright: ignore[reportAttributeAccessIssue]` to the
  `sys.stdout.reconfigure(encoding="utf-8")` line at `:445`. **Per-line ignore, not a narrowing** (D7):
  narrowing to `isinstance(_, io.TextIOWrapper)` (the `cli.py` house pattern) would fail
  `tests/test_prepare.py:1626-1657` and `tests/test_publish.py:2018-2052`, both of which inject a duck-typed
  `_FakeStdout`, and would strand these rule-14 lines unexecuted. `prepare.py` is **rule-14**; the ignore is
  a comment and executes nothing.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `git diff --numstat src/sofer/prepare.py` → `1  1`.

- [x] 3.9 Run **SC-4c**, the dual-gate sensitivity probe with the **wrong variant FIRST**, pasting both
  checkers' output. This task is deliberately ordered (i) → (ii) and must not be reordered or re-run
  after (ii) alone.
  - **(i) the rejected variant first.** Temporarily set `:611` to `raw_rows: list[list[object]] = []` **and**
    put the revision-1 annotation back at `:614` (`vals: list[object] = list(row) if row is not None else []`).
    Run `uv run mypy src/ scripts/; echo "exit=$?"` and `uv run pyright; echo "exit=$?"`. Expected: **both
    non-zero and both naming `_converters.py`** — mypy `[assignment]` / pyright
    `reportAssignmentType` **at `:614`**, i.e. the diagnostic was *relocated*, not cleared. This is the
    proof that the candidate the design rejected satisfies neither checker (DC-10, evidence §8.1/§8.6).
  - **(ii) the frozen form.** Restore the frozen state — `raw_rows: list[Sequence[object]] = []` at `:611`,
    `:614` unannotated — and re-run both commands. Expected: both `exit=0`, with **no `_converters.py`
    diagnostic anywhere** in either output.
  - Paste **both** checkers' output for **both** runs, including mypy's note recommending `Sequence`, and
    finish with `git status --porcelain` showing only the intended change.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the four command outputs (two checkers × two variants) with exit codes, plus the closed
    `git status --porcelain`.

- [x] 3.10 GREEN the whole source set: `uv run mypy src/ scripts/; echo "exit=$?"` → `exit=0`,
  `Success: no issues found in 33 source files`; `uv run pyright; echo "exit=$?"` → `exit=0` with
  `0 errors, 0 warnings`. Then re-run `uv run pytest tests/test_ci_workflows.py -q` and confirm
  **G2, G3, G5, G6 green** (G3 needs Phase 4 — if the CI step is not armed yet, G3 is still red, which is
  expected; record the split honestly rather than claiming a full green).
  <!-- sdd-owner: implementation -->
  - **Evidence:** both gate outputs with exit codes, plus the guard split at this step.

- [x] 3.11 REFACTOR — recorded as **not applicable, with the reason**. This change adds no production
  behaviour to restructure: sites 1–5 and 13–17 are static annotations/import paths/comments, and the two
  real code changes (site 6's container type, site 7's loop) are behaviour-preserving by construction and
  are covered by the existing converter tests run in task 7.5. If a genuine duplication is discovered while
  applying the sites, extract it inside the task that found it — do not open a refactor phase.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the one-line statement in the apply progress, plus any extraction actually performed.

---

## Phase 4 — Arms the gate: GREEN for G3 (design §13 step 4)

- [x] 4.1 Edit `.github/workflows/ci.yml` — add **one** step to the `lint` job whose `run` string is exactly
  `uv run pyright` (bare: no path arguments — the config's `include` is the single scope authority, CI-09 S1).
  Place it after the existing `uv run mypy src/ scripts/` step mirroring the job's order. Do **not** add any
  pyright version literal, any `--warnings` flag, or any path argument.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk, plus `grep -rn "pyright" .github/workflows/` naming the step and **no**
    version specifier, plus `grep -rn -- "--warnings" .github/` → no match.

- [x] 4.2 Edit `.pre-commit-config.yaml` — add the second `repo: local` hook, mirroring the `mypy` hook's
  shape: `id: pyright`, `name: pyright`, `entry: uv run pyright`, `language: system`,
  `pass_filenames: false`, `types_or`/`files` as the existing mypy hook uses them (re-read that hook and
  mirror it; do not invent keys). `uv.lock` is **not** regenerated — the pin already landed
  (evidence §8.5) and the hook consumes `uv run`.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `uv run pytest tests/test_ci_workflows.py -q` showing **G3 green**.

- [x] 4.3 Confirm no pre-existing gate declaration moved: `git diff .github/workflows/ .pre-commit-config.yaml`
  shows **only** the one new ci.yml step and the one new hook entry. The existing
  `run: uv run mypy src/ scripts/` step and the existing `mypy` hook entry must be byte-identical — G6
  asserts exactly that (CI-09 S5).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunks plus the G6 pass in the same run as 4.2.

---

## Phase 5 — Documentation: GREEN for G4 (design §13 step 5, §7)

- [x] 5.1 `CONTRIBUTING.md` — replace the `### Type checking` section (design's `:79-81` is a snapshot;
  re-read and anchor on the heading and its two lines) with the frozen section from design §7.1: heading, two
  prose paragraphs and the one fenced command block naming `uv run mypy src/ scripts/` and `uv run pyright`,
  stating that `tests/` is excluded from **both** gates by policy (`ci` CI-09) and that pyright must be run
  through `uv run`. The claim must be **true of the committed tree** — after Phase 3 and the committed
  `strict = true` it is; do not rewrite the doc to match a `false`.
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff CONTRIBUTING.md` limited to that section, plus
    `grep -n "uv run pyright\|tests/" CONTRIBUTING.md`.

- [x] 5.2 `CONTRIBUTING.md` — add **exactly one** line to the Development-commands list, after the existing
  `uv run mypy src/` entry: `uv run pyright                   # second type gate (config-driven; src/ + scripts/)`.
  Nothing else in the list changes: the existing `uv run mypy src/` text and the `ruff.toml` sentence
  (`:75`) stay byte-identical (#212's and #187's surfaces — design R7).
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff CONTRIBUTING.md` → exactly this one added line in that list, plus
    `grep -n "ruff.toml" CONTRIBUTING.md` unchanged.

- [x] 5.3 `AGENTS.md` — rule 5 (design's `:36-38`) minimally: line 1 gains `pyright` to the hook roster;
  line 3 becomes "Before pushing, run `uv run mypy src/` and `uv run pyright` — …". Leave the
  `uv run mypy src/` path text as written (#212 owns the narrower-than-CI command text).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the rule 5 diff hunk, `git diff --numstat AGENTS.md` → `3  2` for this change's two rules.

- [x] 5.4 `AGENTS.md` — rule 12's latent-issue bullet: **append** the one frozen sentence from design §7.2
  naming the `uv run pyright` gate and the committed `typings/tomli-stubs/` stub. It must **add without
  weakening**: the bullet keeps naming all five modules, quoting both fallback forms, keeping "do not add
  mypy to the version matrix" and the `--python 3.13` escape hatch — CI-07's own clause requires that and
  G7's read must not be invalidated by this edit.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the diff hunk plus `grep -n "tomli-stubs" AGENTS.md`.

- [x] 5.5 `README.md` + `README_ES.md` (D13, rule 13 — **one commit, both files**) — insert the mirrored
  bullet as the **first** bullet of the quality-gates section (before the coverage bullet), so the roster
  names both checkers and the order matches the CI job order. `README.md` gets the English bullet from
  design §7.3; `README_ES.md` gets the Spanish-prose/English-technical mirror in the same position under
  `## Controles de calidad y escaneo de seguridad`. Section headings, order and existing bullets unchanged;
  no TOC edit is needed (the section already exists in both). Then edit `.github/PULL_REQUEST_TEMPLATE.md`:
  add `$ uv run pyright` / `0 errors, 0 warnings` after the mypy block in the Verification code block, and
  `- [ ] \`uv run pyright\` — clean (pyright gate, \`[tool.pyright]\`)` after the `uv run mypy src/` checklist
  item — leaving the existing `uv run mypy src/` lines untouched (#212). The PR-template item is what G4's
  clause (e) reads (DC-6 — no seventh test).
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff README.md README_ES.md .github/PULL_REQUEST_TEMPLATE.md` plus a successful
    `uv run pytest tests/test_ci_workflows.py -q` with **G4 green**.

---

## Phase 6 — Spec delta **and** the CI-07 amendment, landed by one `sdd-sync` (design §13 step 6)

- [x] 6.1 Author the delta file
  `openspec/changes/2026-09-15-chore-type-gate-policy/specs/ci/spec.md`, modelled on the archived CI-08 delta
  and the COV-07 delta, containing **in this order**:
  - the framing blockquotes frozen in design §6.1 (additive CI-09 **plus** one authorized CI-07
    modification; the `ci`-capability justification; one-requirement/two-clause-groups; the rule-6
    resolution; the one-armed-CI-step note; domain hygiene; cross-references-not-edits);
  - `## ADDED Requirements` with the CI-09 requirement title and text (§6.2), the **five** scenarios
    (§6.3, `- GIVEN / - WHEN / - THEN / - AND`) and the requirement block's **own trailing `---`** so no
    doubled separator appears;
  - `## Test Mapping` with the **five** rows verbatim (§6.4), naming the seven guards and the verify-phase
    evidence classes;
  - `## MODIFIED Requirements` carrying the CI-07 amendment (§6.6) — heading, the **appended**
    `> Modified by \`2026-09-15-chore-type-gate-policy\` (GitHub #201) — …` blockquote line stacked under the
    existing `> Added by …` line, **Occurrence 1** (the stale `python_version` clause replaced with the
    frozen `"3.11"` wording, every other byte of the paragraph copied), the `(Previously: …)` marker
    paragraph immediately after it, and **Occurrence 2** (the first THEN bullet of CI-07's "User-facing
    support is unchanged" scenario replaced with the frozen two-and-a-half-line wording);
  - `## Cross-referenced and deliberately untouched` including the **frozen R12 scope note** for CI-07's
    "zero `pyproject.toml` paths / zero `.github/workflows/` paths" clause, and `**Non-goals recorded by
    this delta:**`.
  Rule 6 check: exactly **one** new requirement, **five** scenarios, **five** rows, **nine** guard names
  across them (G7 is the CI-07 enforcement and takes no CI-09 row).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the file's full text plus `grep -c "^#### Scenario:"` → 5 and `grep -c "| CI-09 |"` → 5.

- [x] 6.2 **Land the CI-09 block, its five rows, and the two CI-07 occurrences in ONE `sdd-sync`
  operation** — one work unit because G7 stays red until the canonical spec is synced (hard ordering 4), and
  because a reader between two writes would see either a CI-09 requirement with no rows or a CI-07 clause
  contradicting its own scenario. Anchors, by **content** (evidence §7.3's line numbers are snapshots and
  drift between reads — OBS-5):
  - insert the CI-09 requirement block **between** the `---` that closes CI-08's last scenario and the
    `## Test Mapping` heading, carrying its own trailing `---`;
  - append the five rows at the **end** of the existing table, immediately after the CI-08
    `required-version rejects a mismatched binary` row;
  - apply CI-07 Occurrence 1 (the clause inside the paragraph beginning "This requirement SHALL NOT change
    user-facing Python support:"), the `(Previously: …)` paragraph after it, the `> Modified by …` blockquote
    line on CI-07's provenance line, and CI-07 Occurrence 2 (the first THEN bullet of the "User-facing
    support is unchanged" scenario) — and **nothing else in CI-07**: the `.python-version` = `3.13` clause
    and its equality with both job pins, the flag-free-mypy paragraph, the COV-06-script paragraph, the
    AGENTS-rule-12 latent-issue paragraph, the four other scenario bullets and the fifth scenario's
    remaining bullets stay byte-identical (design §6.6's "deliberately untouched" list; the `## Purpose`
    enumeration stays stale per the CI-07/CI-08 precedent).
  <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff openspec/specs/ci/spec.md` showing exactly the CI-09 additions plus the four
    CI-07 spans (clause, `(Previously: …)`, `> Modified by …`, scenario bullet), and
    `uv run pytest tests/test_ci_workflows.py -q` showing **G7 green** (it was red through Phases 1–5).

- [x] 6.3 Post-sync integrity checks: `grep -n "CI-09" openspec/specs/ci/spec.md` → the requirement and its
  five rows; `grep -c '"3\.10"' openspec/specs/ci/spec.md` → **0** (every surviving `3.10` mention is
  backticked prose — the retired `.python-version` rationale and the test matrix — which is correct);
  `git diff --name-only openspec/specs/` → **only** `ci/spec.md` (CI-01..CI-06, CI-08, PB-07 and PB-14
  untouched; `process-boundary/spec.md` has an empty diff).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the three command outputs.

---

## Phase 7 — Full verify: SC-1…SC-8 with exact commands and expected output (design §13 step 7, §9)

Every command runs from the repository root. Paste **actual output**, never a restatement (AGENTS rule 11).
Each expected value is frozen, so a mismatch is a finding, not a judgement call.

- [x] 7.1 **SC-1 — the gate is green and errors-only.** `uv run pyright; echo "exit=$?"` → `exit=0` and the
  summary line `0 errors, 0 warnings` pasted verbatim; `grep -rn -- "--warnings" .github/ .pre-commit-config.yaml`
  → **no match**. Proves P SC-1.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the run output and exit code, plus the empty grep.

- [x] 7.2 **SC-2 — one pin, one config home, no workflow literal, lock current.**
  `uv run pyright --version` → `pyright 1.1.414`, **equal to** the version derived from the dev pin;
  `uv lock --check` → exit 0; `grep -rn "1\.1\.414" .github/workflows/ || echo "no workflow version literal"`
  → `no workflow version literal`;
  `find . -name pyrightconfig.json -not -path "./.venv/*" -print | wc -l` → `0`.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the four command outputs.

- [x] 7.3 **SC-3(a) — the red-first probe: the gate is REAL.** `printf 'probe: int = "not an int"\n' > src/sofer/_type_gate_probe.py`;
  `uv run pyright; echo "exit=$?"` → **`exit=1`** with a `reportAssignmentType`/`reportInvalidTypeForm`-class
  error naming `src/sofer/_type_gate_probe.py`; `rm src/sofer/_type_gate_probe.py`;
  `uv run pyright; echo "exit=$?"` → `exit=0` with no probe in the output; `git status --porcelain` empty
  afterwards (the probe is `src/sofer/_type_gate_probe.py` per DC-7 and is deleted in the same task —
  `src/` is coverage-measured only over executed files and the probe is gone before any suite run).
  <!-- sdd-owner: implementation -->
  - **Evidence:** both runs with exit codes, plus the closed `git status --porcelain`.

- [x] 7.4 **SC-3(b) — `tests/` is out of the gate.** `printf 'probe: int = "not an int"\n' > tests/type_gate_probe.py`;
  `uv run pyright; echo "exit=$?"` → `exit=0` and the `tests/` probe path **absent from the output**;
  `rm tests/type_gate_probe.py`. Informational only, **not** a pass/fail criterion: also record
  `uv run pyright tests/ > /tmp/pyright_tests.txt; echo "exit=$?"` to document the pinned version's
  behaviour when a file is named explicitly on the command line — the guarantee that matters is the **bare**
  invocation plus G4's `exclude` assertion.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the bare run's output/exit code, the informational explicit-path run, and the removal.

- [x] 7.5 **SC-3(c) — stub and artifact isolation.**
  `uv run python -c "import importlib.util; print(importlib.util.find_spec('tomli'))"` → `None`;
  `uv build`; then the wheel probe
  `uv run python -c "import glob, zipfile; w = sorted(glob.glob('dist/*.whl'))[0]; print(sorted(n for n in zipfile.ZipFile(w).namelist() if 'typings' in n or n.endswith('.pyi')))"`
  → `[]`; the sdist probe
  `uv run python -c "import glob, tarfile; t = tarfile.open(sorted(glob.glob('dist/*.tar.gz'))[0]); print(sorted(n for n in t.getnames() if 'typings' in n))"`
  → `[]`; then `rm -rf dist` (the artifacts are probes, never deliverables).
  <!-- sdd-owner: implementation -->
  - **Evidence:** all four outputs, plus the post-cleanup `git status --porcelain`.

- [x] 7.6 **SC-4 — mypy strict is green on the enforced scope, `tests/` still excluded.**
  `uv run mypy src/ scripts/; echo "exit=$?"` → `exit=0` with
  `Success: no issues found in 33 source files`; paste
  `grep -n "mypy" .github/workflows/ci.yml .pre-commit-config.yaml` → both invocations unchanged and
  **neither names `tests`**. Baseline for the comparison is task 0.2 (six errors, changed composition).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the mypy output/exit code plus the two grep lines.

- [x] 7.7 **SC-5 — coverage, lint and the rule-14 four rows.** `uv run pytest tests/ -q` (tally **not
  reduced** vs task 0.3's baseline and vs evidence §8.4's `1785 passed, 6 skipped, 1 warning` — re-derive
  on the branch, never copy); `uv run coverage run -m pytest`;
  `bash scripts/check_core_coverage.sh` → exit 0 with **four** 100.00% rows (`cli.py`, `scanner.py`,
  `prepare.py`, `publish.py`) and an empty `Missing` column; `uv run coverage report -m` → TOTAL ≥ 90;
  `uv run ruff check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/ scripts/` → clean in
  both modes. If the interpreter is older than 3.13, pass `--python 3.13` explicitly (AGENTS rule 12). This
  is the rule-14 re-run that Phase 3's two rule-14 edits (`prepare.py`, `publish.py`) require.
  <!-- sdd-owner: implementation -->
  - **Evidence:** all six commands' output with exit codes, and the four 100.00% rows.

- [x] 7.8 **SC-6 — the durable record exists and the amendment's blast radius is exactly the stale clause.**
  `git diff --stat openspec/specs/` → only `ci/spec.md`; `git diff openspec/specs/ci/spec.md` → the CI-09
  additions **plus** the four CI-07 spans and nothing else; `grep -n "CI-09" openspec/specs/ci/spec.md`;
  `git diff --stat openspec/specs/process-boundary/spec.md` → **empty**. Then **SC-6b** (docs truth):
  read `CONTRIBUTING.md`'s type-checking section + command list, and
  `diff <(sed -n '/^## Quality gates/,/^## Related/p' README.md) <(sed -n '/^## Controles de calidad/,/^## Referencias/p' README_ES.md)`
  → eyeball bullet count/order: both READMEs carry the mirrored bullet in the same first position. Then
  **SC-6c** (the CI-07 amendment evidence): `grep -n 'python_version' openspec/specs/ci/spec.md`;
  `grep -c '"3\.10"' openspec/specs/ci/spec.md` → **0**;
  `grep -n 'Modified by .2026-09-15-chore-type-gate-policy' openspec/specs/ci/spec.md`;
  `grep -n '`[tool.mypy] python_version`' pyproject.toml openspec/specs/ci/spec.md` → the spec's value equals
  `pyproject.toml`'s `"3.11"`. No new CI-07 Test Mapping row is added — CI-07's existing
  "verify-phase static evidence" row is **re-satisfied** by this read.
  <!-- sdd-owner: implementation -->
  - **Evidence:** all SC-6/SC-6b/SC-6c command outputs.

- [x] 7.9 **SC-7 — the guards exist, hold no version literal, and the red-first set was the honest one.**
  `uv run pytest tests/test_ci_workflows.py -q` → the module's tally increases by **exactly 7** with no
  pre-existing test modified (compare against task 1.5's before/after counts); paste the Phase 1 red-then-green
  log (G1, G3, G4 red; G2, G5, G6 green) beside the post-Phase-6 run (G7 green); and assert
  `grep -cE "1\.1\.414" tests/test_ci_workflows.py` → **0** (the guards derive, never literalise).
  <!-- sdd-owner: implementation -->
  - **Evidence:** the module tally, the two guard-split logs, and the zero-literal grep.

- [x] 7.10 **SC-8 — no leniency added, no unrelated surface touched.** `git diff --stat` review;
  `grep -rn "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py || echo "none"`
  → `none`; `git diff --stat .github/workflows/release.yml pyproject.toml` → no `fail_under` edit, no CI
  matrix change, no `release.yml` change (the only `pyproject.toml` hunks are §3's `[tool.pyright]` block and
  §2.2's sdist exclusion), and **no** `openspec/project.md` / `openspec/config.yaml` diff.
  <!-- sdd-owner: implementation -->
  - **Evidence:** all three command outputs.

- [x] 7.11 Assemble the verify-report input block (`openspec/changes/2026-09-15-chore-type-gate-policy/verify-report.md`
  is the verify phase's artifact; this task only gathers the pasted evidence): (a) task 0.2's pre-state
  mypy block; (b) Phase 1's red-then-green guard log; (c) task 3.9's SC-4c four outputs; (d) 7.1's summary
  line and 7.2's pin/lock/literal/JSON results; (e) 7.3/7.4/7.5's probe outputs; (f) 7.7's four 100.00%
  rows and the suite tally beside the baseline; (g) 7.8's SC-6/6b/6c outputs; (h) 7.9's guard tally; (i)
  7.10's scope and pragma checks; (j) the SC-4b floor probe verdict or the recorded fallback; (k) a
  statement of which Phase 2 stub layout was used (DC-8 step 0, 1 or 2). One section per item, each with
  its command.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the assembled block in the apply progress.

---

## Phase 8 — Rollback handle and stop-and-report conditions

- [x] 8.1 Record the rollback handle in the apply progress: **one commit** (or one squashed linear stack)
  whose `git revert <sha>` restores the pre-change tree. The six documented partial reverts (design §10.1)
  are carried as the operational detail: whole-change revert; hook-only revert (R11 — Node unavailable, CI-only
  posture recorded with the AGENTS rule 5 divergence); gate revert (ci step + `[tool.pyright]` together, so
  no requirement asserts a gate that does not exist); pin revert; per-source revert (sites 1–5, 13–17 are
  type/comment-only; sites 6–7 are behaviour-preserving and covered by the existing converter tests); docs
  revert (independent of the gates **except** through G4, whose going red is the record working). State the
  one coupling honestly: **reverting this change also reverts the maintainer's `strict = true`**, or it
  leaves the mypy gate red — apply records that in the PR body rather than hiding it.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the recorded handle plus the coupling sentence.

- [x] 8.2 Record the **stop-and-report conditions** verbatim; none may be resolved by improvisation:
  (1) task 0.2 shows a mypy diagnostic outside the six measured sites — resolve with the §5 idioms and
  **report the addition** (R9), or stop if it lands in a rule-14 module;
  (2) task 2.5's fallback 1 also fails → fallback 2 is an escalation (CI-09 S2 text amendment), never a
  silent substitution;
  (3) task 3.5's SC-4b floor probe fails → take the documented per-line-ignore fallback for `publish.py:70`
  and record it;
  (4) task 3.9(i) does **not** show **both** checkers non-zero on the rejected variant → stop: DC-10's
  premise is broken and the resolution must be re-designed, not patched;
  (5) any of G2/G5/G6 turns red at any point → a tripwire was breached; stop;
  (6) the diff reaches any path in the Forbidden list below, or `git diff --name-only openspec/specs/` names
  anything other than `ci/spec.md` → stop;
  (7) the suite tally is reduced or any of the four COV-06 rows drops below 100.00% → stop (a rule-14
  violation is never repaired with a `# pragma: no cover`);
  (8) the CI-07 diff moves beyond the four frozen spans (clause, `(Previously: …)`, `> Modified by …`,
  scenario bullet) → stop — R12's diff-scope clause is **not** authorized for amendment.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the recorded condition list, with any fired condition reported by name.

- [x] 8.3 Final self-check before returning: `[tool.pyright]` present and `mypy_path` absent; both gates
  exit 0; G1–G7 green with the Phase 1 red log recorded; the delta file exists and the canonical spec carries
  CI-09 + the two CI-07 occurrences; no `# pragma: no cover` added; the four COV-06 rows still 100.00%; the
  diff names only the intended paths; no commit, push, PR, tag or release was performed.
  <!-- sdd-owner: implementation -->
  - **Evidence:** the checklist result with the supporting commands already pasted above.

---

## Forbidden (zero-path guard for the whole apply phase — design §14)

Absent from the diff by construction: `tests/**` edits to existing tests (the guard append is the only test
change) · `openspec/specs/**` anything other than `ci/spec.md` via sync · `openspec/specs/ci/spec.md`
CI-01..CI-06, CI-08, the `## Purpose` enumeration, and every CI-07 byte outside the four frozen spans ·
`openspec/specs/process-boundary/spec.md` (PB-07/PB-14 are cross-referenced, never edited) ·
`openspec/project.md` · `openspec/config.yaml` · `.github/workflows/release.yml` · the CI test matrix ·
`[tool.mypy]` (zero lines gained — no `mypy_path`, no `python_version` change, no
`ignore_missing_imports` change, no override added or removed) · `uv.lock` (already regenerated by the
maintainer; `uv lock --check` only) · the maintainer's `datasets>=5.0.1` / `numpy<2.3` / `types-*` /
`[[tool.mypy.overrides]]` edits · `src/sofer/cli.py`, `scanner.py`, `config.py`, `mcp_registration.py`,
`model.py`, `metadata.py` (zero lines) · any `tomli` (or other) dependency addition · any
`pyrightconfig.json` · any workflow version literal · any `--warnings` flag · any `# pragma: no cover`
anywhere · any coverage floor movement, `--fail-under` edit, or `scripts/check_core_coverage.sh` change · any
`# type: ignore` beyond site 4's documented fallback · any absorption of #187, #212, #194, #215 or the R12
CI-07 diff-scope tension. No `pyright strict` campaign, no `basedpyright`, no analyzer substitution. **No
commit, push, tag, PR or release from any SDD phase.**

---

## Parent-owned steps (not tasks — no delivery-gate checkbox generated here)

- **Delivery**: one PR against `dev`, per AGENTS rule 12's branch flow. The forecast is Low against the
  400-line threshold and ≈17–29 % of the 1500-line session budget, so **no chain is selected**,
  `ask-on-risk` is not exercised, and **no `size:exception` is requested**. If the diff ever exceeds the
  budget or leaves the intended paths, stop and ask rather than chain.
- **Bounded review** with `.github/PULL_REQUEST_TEMPLATE.md`, every section filled with real output. The PR
  body must carry three disclosures: the `strict = true` coupling from task 8.1; which DC-8 stub layout
  step was taken (task 2.5); and **R12** — CI-07's "zero `pyproject.toml` / zero `.github/workflows/` paths"
  clause stays byte-identical and is read as #178's change-scoped evidence, not a standing ban, since CI-09
  itself requires a `ci.yml` step and a `[tool.pyright]` block. Settling that reading is a maintainer
  follow-up, deliberately **not** dressed up as a second amendment.
- **Rollback**: one commit, `git revert` — see Phase 8.
