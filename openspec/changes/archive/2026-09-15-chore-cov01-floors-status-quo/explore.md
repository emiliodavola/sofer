# Exploration: chore-cov01-floors-status-quo

**Change**: `2026-09-15-chore-cov01-floors-status-quo` · **Issue**: #215 — *COV-01's three ≥90% per-file floors are
declared binding but nothing that can fail in CI enforces them* · **Branch**: `chore/215-cov01-floors-status-quo`
(from `dev@319bb7e`) · **Phase**: explore (read-only notes — no implementation) · **Store**: hybrid (this file +
Engram `sdd/2026-09-15-chore-cov01-floors-status-quo/explore`)
**Confirmed product decision (user, option (b)) — NOT re-opened here**: keep the status quo (the three floors stay
verify-phase-only) and **record the choice as deliberate**. This change is spec/decision-recording only: no CI
change, no test change, no new gate, no coverage-number promise.

**Method note (read-only phase, no shell)**: this executor's tool surface is `read` / `grep` / `find` / CodeGraph /
memory — there is **no shell**, so `gh issue view 215` could not be run and no command output is produced here. The
issue's facts are taken from the parent-supplied delegation context and **each one was independently re-verified
against the working tree** (file:line rows in §2–§3). `.git/HEAD` reads
`ref: refs/heads/chore/215-cov01-floors-status-quo` — branch confirmed. Nothing below is asserted from upstream
documentation, and no command result is fabricated.

---

## 1. Scope

**In scope (this change, as framed by the parent):** record the deliberate non-enforcement of COV-01's three ≥90
per-file floors, with the reasoning and the enforcement boundary named, in a durable spec home; plus the SDD phase
artifacts.

**Out of scope (explicit non-goals — §7 carries the full list):** arming any gate, changing any test, editing any
workflow or `scripts/`, rewording AGENTS.md rule 14, promising a coverage number, and any option (a)/(c)/(d)
mechanics (arming a CI floor, deleting the floors, rewording them to "aspirational").

---

## 2. The defect, mechanically (verified)

The policy and the enforcement are two different statements, and only the first one exists:

| Layer | Text | Enforced by |
| --- | --- | --- |
| COV-01 (`openspec/specs/coverage/spec.md:54-90`) | the three second-tier modules "SHALL each measure ≥90% coverage"; "SHALL be individually binding"; TOTAL "SHALL NOT substitute" | **verify-phase runtime evidence only** — the requirement's own words (`:62`) |
| COV-06 (`spec.md:214-281`) | four CLI-core modules at 100.00%, enforced by scoped `--fail-under=100` invocations | `scripts/check_core_coverage.sh` run by `ci.yml:85` — a real gate |
| The one executable COV-01 check (`tests/test_coverage_contract.py:41-88`) | asserts the three rows + TOTAL ≥90 from a local `.coverage` file | **skips** whenever `.coverage` is absent (`:37-40`) |
| The arming prohibition (COV-06 S1 `spec.md:246-250`; COV-03 S3 `spec.md:159-164`; `ci` CI-01 S2 `ci/spec.md:46`, carve-out `:31`) | no `--fail-under` value other than 100 may appear in the workflow or the gate script | `tests/test_ci_workflows.py:237-264` + `:278-306` |

So: the floors are *declared* binding, *measured* by hand, *not* armed, and the obvious arming mechanism is
*forbidden by an existing, test-pinned policy* — which is exactly the status quo the user chose to keep and now to
record rather than to change.

**The one nuance that must not be overclaimed:** the non-100 ban is scoped to (a) the text of
`scripts/check_core_coverage.sh` and (b) the raw text of `ci.yml` / `release.yml`. A *future* change could add a
*new* script carrying `--fail-under=90` and reference it from a workflow without any current test going red (only
the two workflow files and the one gate script are read; `tests/test_ci_workflows.py:242-244` asserts the loop
roster of *that* script). The recorded decision — not a mechanism — is what makes such a move a deliberate spec
change rather than an accident. The requirement text written in the proposal SHALL NOT claim the ban is airtight.

**Why the guard cannot fail in CI (COV-01 S3 is by design):** `test_coverage_contract.py:37-40` guards on
`(_REPO_ROOT / ".coverage").exists()` at import time. In the CI coverage job the order is
`uv sync` → `coverage run -m pytest` (`ci.yml:73`) → `coverage report -m` (`:78`) → `bash
scripts/check_core_coverage.sh` (`:85`), so at test-import time on a clean checkout the data file is absent and the
guard skips — precisely what COV-01-S3 (`spec.md:86-90`) declares as intended. *(Parent-supplied fact, consistent
with the requirement text; not re-measured here — no shell in this phase.)*

---

## 3. Verified facts (file:line evidence, read this phase)

### 3.1 `openspec/specs/coverage/spec.md` — exact current text and IDs

| Anchor | Line(s) | Verbatim content (as read this phase) |
| --- | --- | --- |
| `## Requirements` | `:52` | — |
| **COV-01 header** | `:54` | `### Requirement: Per-file coverage floor for the three second-tier modules (COV-01)` |
| COV-01 body | `:56-72` | "`src/sofer/profile.py`, `src/sofer/mcp_registration.py`, and `src/sofer/verification.py` SHALL each measure ≥90% coverage under `coverage report -m` on the regenerated baseline, using the same `[tool.coverage.run]` configuration the CI coverage job uses (`branch = true`, `source = ["src/sofer"]`) over the complete suite (PB-05). Each of the three rows SHALL be individually binding; TOTAL ≥90 (COV-02) SHALL NOT substitute for any single row. **The floor SHALL be verified as verify-phase runtime evidence on the CI interpreter (ubuntu / Python 3.13), which is the arbiter because statement counts and branch arcs vary across Python versions; the measured rows SHALL be recorded with an observed margin above the floor. The change MAY additionally guard the floors with a skip-if-absent `tests/test_coverage_contract.py` regression guard that asserts the three rows and TOTAL from a local `.coverage` data file when one is present, and SHALL skip on a clean checkout (the data file is gitignored local state — a clean checkout SHALL never fail on its absence).** The top-tier CLI-core modules (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) are NOT governed by this ≥90 floor: they carry an absolute 100% mandate under COV-06, enforced by the scoped CI gates." |
| **COV-01 S1** | `:74-78` | `#### Scenario: Three second-tier rows meet the floor on the regenerated baseline` — GIVEN the `[tool.coverage.run]` configuration exactly as CI uses it and a fresh `coverage run -m pytest` (complete suite, PB-05) on `test/raise-coverage-90` / WHEN `coverage report -m` runs / THEN the three rows SHALL each be at or above 90 (the `cli.py`/`publish.py` rows are governed by COV-06 at 100.00, not this floor) |
| **COV-01 S2** | `:80-84` | `#### Scenario: The CI interpreter is the arbiter` — GIVEN the CI reproduction environment (ubuntu, Python 3.13) / WHEN `coverage run -m pytest` then `coverage report -m` run there / THEN each of the three rows SHALL be ≥90 with an observed margin above the floor recorded in the verify report and the CI coverage job log; "the four core rows are binary gates under COV-06 with no margin by design" |
| **COV-01 S3** | `:86-90` | `#### Scenario: Optional contract guard skips on a clean checkout` — GIVEN `tests/test_coverage_contract.py` present and a checkout with no local `.coverage` data file / WHEN the suite runs / THEN the contract test SHALL skip, and the suite SHALL pass without it — "the three floors remain verify-phase evidence (COV-01), never a hard test dependency on absent local state" |
| COV-02 / COV-03 / COV-04 / COV-05 headers | `:94` / `:125` / `:167` / `:186` | (COV-04 is the *retired* marker: `### Requirement: Cheapest-wins adjacent set (COV-04) — RETIRED in this change`, "has no scenarios and SHALL NOT be enforced") |
| **COV-03** (text) | `:125-145`, scenarios `:147-164` | body: strictly test-only diff; "**no path under `src/sofer/` SHALL be modified**"; the `cli.py` `__main__` guard KEeP; "`# pragma: no cover` SHALL be absent from the entire filesystem image of the four core modules"; "Coverage-gate machinery in the diff SHALL be limited to the COV-06 per-file scoped invocations … no Codecov, no `pytest-cov`, no XML output, no new config keys." **S3** (`:159-164`): "the only gate invocations SHALL be the COV-06 per-file scoped `coverage report --include=src/sofer/<file>.py --fail-under=100 -m` steps/script" |
| **COV-06 header** | `:214` | `### Requirement: CLI-core 100% mandate with scoped gates (COV-06)` |
| COV-06 body | `:216-244` | four core modules at 100.00%; "`# pragma: no cover` SHALL NOT appear anywhere in those four files"; "AGENTS.md SHALL carry rule 14"; the in-process runpy guard mandate; the scoped-invocation mandate ("for each of the four core module paths, a `coverage report --include=src/sofer/<file>.py --fail-under=100 -m` invocation SHALL run within the job — expressed either as four inline steps or as one committed `scripts/` gate script…"); "the scoped invocations SHALL NOT pass any floor other than 100, and no config key SHALL be added" |
| **COV-06 S1** | `:246-250` | `#### Scenario: Scoped gates are declared for all four core files` — …THEN each of the four paths SHALL appear in a `coverage report --include=src/sofer/<file>.py --fail-under=100 -m` invocation within the job — inline or via the gate script — **"and no `--fail-under` value other than 100 SHALL appear in the workflow or script (the config-key spelling `fail_under` SHALL still be absent, CI-01)"** |
| COV-06 S2 / S3 / S4 / S5 | `:252-256` / `:258-262` / `:264-273` / `:275-280` | pragma-token absence; AGENTS.md rule 14 text; the `cli.py` `__main__` guard executed via runpy under the tracer; "TOTAL stays config-owned at 90" |
| **Last existing requirement ID** | `:214` is the **highest** requirement in the file | Requirements in order: **COV-01, COV-02, COV-03, COV-04 (retired), COV-05, COV-06**. ⇒ **the next free ID is COV-07** |
| **`## Test Mapping` present?** | **`:283`** | YES — the CI-08 convention is already satisfied. Intro at `:285-295` ("Every scenario SHALL map to a green test or to verify-phase static/runtime evidence (AGENTS.md rule 6; rules.specs; PB-05/MSP-R12/CI-01-S2 precedent). Actual measured percentages are NOT pytest-assertable…"), then the coverage-raising-file paragraph `:296-303`, then the three-column table (`Req` / `Scenario` / `Verification`). **No sync risk of the #216 (T1/T2) kind** — the table exists; a new requirement only needs an insertion point (before `:283`) and optionally a row |

The capability `## Purpose` (`:3-50`) enumerates COV-01/02/03/05/06 — it is **already stale for COV-04** (retired,
unmentioned). Adding COV-07 without touching `## Purpose` follows the CI-07/CI-08 precedent (#195/#216 both left a
stale `## Purpose` enumeration alone); touching `## Purpose` would be an extra canonical-prose edit this change does
not need.

### 3.2 `scripts/check_core_coverage.sh` — (a) the module loop

Read in full (12 lines). Verbatim, the loop and nothing else:

```bash
set -euo pipefail
for f in cli scanner prepare publish; do
  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
done
```

- **`:10`** — `for f in cli scanner prepare publish; do` ⇒ **exactly the four core modules; `profile`,
  `mcp_registration`, `verification` are absent.** The issue's fact (a) is **CONFIRMED**.
- Header comment `:2-6` states the design: "`--fail-under=100` is a fixed policy constant, never a tunable floor —
  the config-owned TOTAL gate (ci CI-01: 90) is untouched".
- Referenced from `.github/workflows/ci.yml:85` (`run: bash scripts/check_core_coverage.sh`, step at `:84`, the
  COV-06 banner at `:80-83`). `release.yml` has the TOTAL report step only (`:80`) and no core gate script —
  consistent with COV-06 declaring the `ci.yml` coverage job as the enforcement site.

### 3.3 `tests/test_coverage_contract.py` — (b) the skipif, and the only executable floor check

Read in full (104 lines):

- `:19` `_CORE_MODULES = ("cli.py", "scanner.py", "prepare.py", "publish.py")`;
  `:21` `_FLOOR_MODULES = ("profile.py", "mcp_registration.py", "verification.py")`.
- `:24-34` `test_core_modules_contain_no_pragma_tokens` (COV-03/06 static scan).
- **`:37-40`** — the decorator:
  ```python
  @pytest.mark.skipif(
      not (_REPO_ROOT / ".coverage").exists(),
      reason="no local .coverage data file (clean checkout — CI measurement is the arbiter)",
  )
  ```
  The issue's fact (b) is **CONFIRMED** (issue said "`tests/test_coverage_contract.py:37-40` skipif on `.coverage`" — exact match).
- `:41-88` `test_three_floor_modules_and_total_meet_90_when_data_file_present` — the only executable ≥90 assertion:
  loads `.coverage` read-only, computes executed-statement % per module and for TOTAL, `assert value >= 90.0`, and
  `pytest.skip` when the DB is empty/partial. **This is the entire in-repo enforcement surface for COV-01**, and it
  is off in CI by its own decorator.
- `:91-104` `test_gate_machinery_bounded` — asserts `fail_under = 90` present in `pyproject.toml` and no
  xml/codecov/coveralls tokens in the two workflows.

### 3.4 `tests/test_ci_workflows.py` — (c) which tests pin the non-100 ban, and what exactly they assert

**Line numbers in the issue's brief are stale — see §3.6.** The two ban-pinning tests at current HEAD:

1. **`test_coverage_job_gates_core_modules_at_100` — `:237-264`** (COV-06 mapping row). Asserts, in order:
   - `:256` `assert "for f in cli scanner prepare publish" in script` — **the loop roster is literally pinned**
     (widening the script to the three floor modules with a non-100 floor fails this line);
   - `:257` `assert '--include="src/sofer/${f}.py" --fail-under=100 -m' in script`;
   - `:258-259` each of `cli`/`scanner`/`prepare`/`publish` appears in the script;
   - `:260` `assert "bash scripts/check_core_coverage.sh" in _read_text(".../ci.yml")`;
   - `:261-264` for **`script` + `ci.yml` + `release.yml`** raw text: `assert "fail_under" not in raw` and every
     `re.findall(r"--fail-under=[0-9]+", raw)` match `== "--fail-under=100"`.
   ⇒ **a `--fail-under=90` added to `scripts/check_core_coverage.sh` turns this test red.** This is the pinned
   boundary that makes the status quo a *policy* rather than an oversight.
2. **`test_coverage_gate_is_config_driven_without_cli_floor` — `:278-306`** (CI-01 S2 mapping row). Asserts for
   `ci.yml` **and** `release.yml`: `"--fail-under" not in raw`, `"fail_under" not in raw`, `"fail-under" not in
   raw`; then for every coverage job: a step `uv run coverage report -m` exists (`:295-299`), and a step equal to
   exactly that flag-free invocation exists **and** does not contain `--fail-under` **and does not contain** `bash
   scripts/check_core_coverage.sh` (`:300-306`). The docstring (`:279-290`) states the scope explicitly: "The
   documented exception is the COV-06 per-file 100% machinery … never as flags or config keys in the workflows."

Adjacent context (not ban-pinning, listed so the proposal does not mis-attribute): `:225`
`test_ci_workflow_files_present`, `:231` `test_pyproject_declares_coverage_fail_under_90`, `:266`
`test_agents_md_declares_core_100_mandate` (**the test that pins AGENTS.md rule 14's text** — it requires the four
module names, `"100.00%"`, and a pragma-ban regex), `:310` `test_coverage_report_honors_show_missing`, `:343`
`test_release_is_gated_on_the_coverage_job`, and `:499` `test_ruff_format_hook_excludes_markdown` (the PB-14 guard
added by #216 — evidence that this file is the repo's established home for static repo-shape contracts).

### 3.5 `pyproject.toml` — (d) `[tool.coverage.*]` keys

| Line | Content |
| --- | --- |
| `:94-95` | `# ── coverage.py ──…` banner comment |
| `:96` | `[tool.coverage.run]` |
| `:97` | `branch = true` |
| `:98` | `source = ["src/sofer"]` |
| `:100` | `[tool.coverage.report]` |
| `:101` | `show_missing = true` |
| `:102` | `fail_under = 90` |

There is **no `[tool.coverage]` key capable of expressing a per-file floor**: `fail_under` is a single scalar read by
coverage.py, which is why COV-06 needed shell invocations at all (`spec.md:236-240` says this in the spec's own
words). So the three floors have exactly two conceivable homes — config (impossible) and a CLI flag in a script (banned
for non-100 values) — and both are recorded here as closed/`.coverage`-guarded.

### 3.6 `AGENTS.md` rule 14 — (e) which modules does it name?

Rule 14 spans **`:101-126`** (`### 14. CLI-core coverage: 100% mandate, zero pragmas` at `:101`; next rule `### 15.`
absent — it is the last rule).

- `:102-110`: **names the four core modules** `cli.py`, `scanner.py`, `prepare.py`, `publish.py`, the `100.00%`
  mandate, and points at `scripts/check_core_coverage.sh` + the CI coverage job as the enforcement.
- `:111-115`: the absolute `# pragma: no cover` ban in those four modules.
- `:116-120`: the TOTAL gate stays config-owned at 90; the per-file gates are additive, "they hardcode 100 only
  because 100 is a fixed policy constant, not a tunable floor".
- `:121-124`: the runpy `__main__`-guard clause.
- **`:125-126`**: "This rule's 100% mandate covers exactly those four modules. Other modules are governed by their
  own per-file floors (spec `coverage` COV-01) or have no floor."

⇒ **Rule 14 names the four core modules only.** The three second-tier modules are **never named** in AGENTS.md; they
are referenced *by spec pointer* (`COV-01`), with **no statement of their enforcement posture**. So the AGENTS.md
home would be a *new* addition, not a correction — and it is excluded by the change's non-goals ("no rule-14
rewording"), and its text is test-asserted (`tests/test_ci_workflows.py:266-277`), so editing it carries a guard
obligation for zero enforcement gain.

### 3.7 `#216` precedent — how a decision was recorded one change earlier (both shapes exist)

| Artifact | What it did | Transferable lesson |
| --- | --- | --- |
| `openspec/specs/process-boundary/spec.md:378-426` (**PB-14**) | **NEW requirement** (`### Requirement: Repository-declared ruff-format hook file scope (PB-14)`), added *by delta*, with a rationale paragraph ("The decision is deliberate and rationale-bearing: upstream widened … without this repository changing anything"), a scope-boundary paragraph ("This requirement SHALL constrain the hook only"; another issue "SHALL retain ownership"; "SHALL arm no CI step"), and an in-requirement clause naming its static guard | The repo's most recent decision-recording pattern is **a new requirement with a rationale + an explicit boundary + a named owner for the adjacent decision** — not an amendment of the neighbouring requirement (PB-10 the formatter contract was left intact) |
| `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/{explore.md,proposal.md,design.md}` | explore compared six candidate homes **without** recommending; proposal picked it with D1–D3 + a named fallback (T2); design fixed the exact wording and the `## Test Mapping` decision (T1: create the table) | The house style is: explore enumerates and frames; **proposal decides**; design fixes wording. This document therefore recommends but does not fix the final text |
| `openspec/specs/process-boundary/spec.md:283-288` | **PB-10's scenario** `#### Scenario: No CI gate was armed, and recurrence stays owned by #194` — an *existing* requirement carrying an absence-recording scenario ("THEN zero matches SHALL exist in both states and no workflow file SHALL appear in the diff") | The repo already accepts **negative/absence clauses** ("no gate was armed", "SHALL arm no CI step") as normative spec content — the shape this change needs |
| `openspec/specs/coverage/spec.md:167-183` | **COV-04 retired marker** — a requirement whose entire content is a recorded decision ("Why: superseded by the amendment … recorded in the proposal Decision Point 2 and Out-of-Scope list") and which "has no scenarios and SHALL NOT be enforced" | The `coverage` capability **already contains a decision-recording requirement with no scenarios** — the closest in-capability precedent for "record, do not enforce" |

---

## 4. Fact drift found this phase (proposal must not copy the brief's line numbers)

| Brief says | Actual at HEAD `319bb7e` | Consequence |
| --- | --- | --- |
| `tests/test_ci_workflows.py` ~**lines 219-266** pin the non-100 `--fail-under` ban | The two ban tests are **`:237-264`** and **`:278-306`**; the `:219-266` window today holds `test_ci_workflow_files_present` (`:225`), `test_pyproject_declares_coverage_fail_under_90` (`:231`) and only the *first* ban test | Line references in the issue/brief are stale (the file has grown: #216 appended the PB-14 guard at `:499` and reworded the module docstring `:1-15`). **The facts themselves all hold**; only the coordinates move. Proposal/design SHALL cite `:237-264` and `:278-306` |
| "nothing that can fail in CI enforces them" | TRUE, with one sharpening: `scripts/check_core_coverage.sh` *would* fail CI if a non-100 floor were added to it — because `tests/test_ci_workflows.py:256-264` pins the roster and the 100-only literal. The floors are unenforced **and** the arming path is policy-closed for the existing script/workflow surfaces (§2 nuance: a brand-new script is not fenced) | Record the *boundary*, not "impossible to arm" |
| Issue ACs (count/wording) | **Not available this phase** — `gh issue view 215` could not be run (no shell); the parent-supplied context is the only transcription | Open question Q1 (§8): the proposal must obtain the issue AC list (or confirm ACs are purely the "record the decision" narrative) before it can trace against them |

---

## 5. Durable-home candidates (comparison; recommendation in §6)

Three candidates were requested. Evidence for and against each, plus what breaks and what stays stable.

### (i) Amend COV-01 in place (add a clause/scenario to `spec.md:54-90`)

**Shape**: delta `## MODIFIED Requirements` replacing the COV-01 block; the added text would say something like
"the floors are deliberately verify-phase-only; the COV-06-S1 / CI-01-S2 non-100 `--fail-under` ban is the
enforcement boundary; the optional guard's clean-checkout skip is by design; no CI gate is intended".

- *For*: zero new IDs; the decision lands on the requirement it is about; COV-01 already contains half the sentence
  ("SHALL be verified as verify-phase runtime evidence", `:62`; S3 already declares the skip), so the amendment is
  small and reads as a completion, not a new claim; the `## Test Mapping` table already has COV-01 rows to extend.
- *Against*: COV-01's three scenarios are **backed by verify-phase evidence that was already earned and recorded**
  by `2026-09-13-raise-per-file-coverage`; a MODIFIED delta forces the whole block to be re-emitted at sync
  (byte-for-byte risk on a block three table rows point at) and invites re-verification of an *unchanged* policy;
  it merges two falsifiable claims with different verification classes (the ≥90 measurement vs the enforcement
  posture) into one requirement; the #216 precedent explicitly chose a **new** requirement beside the neighbouring
  contract rather than editing it.
- *Breaks*: nothing at test level (no test reads `openspec/specs/coverage/spec.md` — verified: zero matches for
  `specs/coverage|coverage/spec.md|openspec/specs` under `tests/`). Authoring/review risk only, plus a rule-6
  obligation for any new scenario (mapped as verify-phase static evidence, same as the existing COV-02/COV-03 rows).
- *Stays stable*: COV-01 S1/S2/S3 evidence chain, the ban tests, COV-06, AGENTS.md.

### (ii) NEW requirement in the coverage spec — next free ID **COV-07** (recommended)

**Shape**: additive delta `## ADDED Requirements` → `### Requirement: <Decision-record title> (COV-07)`, inserted
before `## Test Mapping` (`:283`); rationale paragraph naming the deliberate choice; scope-boundary paragraph naming
the enforcement boundary (COV-06 S1 + CI-01 S2 + `scripts/check_core_coverage.sh:10` + the `.coverage`-guarded
contract test) and the owners of adjacent decisions; optional one scenario mapped to **verify-phase static
evidence** (the coverage Test Mapping intro `:285-295` already permits that class for COV rows), or **no scenario at
all** in the COV-04 retired-marker style.

- *For*: purely additive — COV-01..COV-06 stay byte-for-byte, so the archived delta chain, the three Test Mapping
  rows pointing at COV-01, and the already-earned verify evidence are untouched; matches #216's PB-14 pattern
  (new requirement with rationale + explicit boundary + named adjacent owner); matches in-capability precedent for a
  recorded, non-enforcing requirement (COV-04, `:167-183`); the requirement is the honest falsifiable unit ("the
  floors SHALL remain verify-phase-only; no CI invocation SHALL enforce them; a change that arms one SHALL amend
  this requirement"); the capability **already has** a `## Test Mapping` section, so the #216 T1/T2 table-creation
  question does not arise (no sync risk); zero test/workflow movement by construction.
- *Against*: consumes an ID for a claim that adds no new obligation; a scenario-less requirement is only
  review-checked (mitigated: COV-04 precedent, and the decision is *by nature* a record, not a behavior); if a
  scenario is added, rule 6 wants a mapping row that cannot be a green test here (non-goal: no test changes) — so
  the row must be verify-phase static evidence (permitted by the coverage table's own convention, and by the
  CI-01-S2 / PB-10 precedent) — the proposal must word it so it is not a vacuous "grep finds nothing" restatement of
  COV-06 S1.
- *Breaks*: nothing. *Stays stable*: everything in §3.1–§3.6.
- *Sync note*: insertion point is **before `:283`** (the file's last section must remain the mapping table), which
  is exactly how PB-14 was appended in `process-boundary` — the reverse ordering (requirement after the table) would
  break the file's section order.

### (iii) AGENTS.md note under/near rule 14

**EXCLUDED by the change's non-goals** ("no rule-14 rewording"). Recorded for completeness:

- Current state: rule 14 `:125-126` already *points* at the floors ("Other modules are governed by their own
  per-file floors (spec `coverage` COV-01) or have no floor") but never names the three modules and never states
  their enforcement posture.
- *For*: agent-facing, read every session; one sentence would be cheap.
- *Against / what breaks*: (1) non-goal; (2) rule 14's text **is test-asserted** — `tests/test_ci_workflows.py:266-277`
  (`test_agents_md_declares_core_100_mandate`) extracts rule 14 via regex `### 14\..*?(?=\n### 15\.|\Z)` and
  requires the four module names, `100.00%`, and a pragma token; a new sentence would need to keep all three green
  (feasible, but it adds a doc surface whose only consumer is a *duplicate* of the spec text); (3) it duplicates the
  spec rather than citing it; (4) rule 14 declares the 100% mandate, not the floors — a floors note there sits under
  a heading about a different tier (the very confusion the spec home avoids).

---

## 6. Recommendation (for the proposal to decide — not fixed here)

**Recommend (ii): a new, additive requirement **COV-07** in `openspec/specs/coverage/spec.md`, with the decision
recorded in its own words and the enforcement boundary named, inserted before `## Test Mapping` at `:283`.**

Why, in one paragraph: the change's entire product content is a *record* — nothing is armed, nothing moves — so it
should land where records live (a spec requirement) and it should be **additive**, because COV-01's clauses are
already backed by earned verify evidence and by three Test Mapping rows, and rewriting them would re-open a settled,
unchanged policy for zero behavioral gain. This is also the repository's freshest precedent for recording exactly this
class of decision (#216 → PB-14: new requirement, rationale paragraph, "SHALL arm no CI step", adjacent owner named)
and the `coverage` capability already demonstrates the "recorded, not enforced" requirement shape (COV-04, retired).
The one thing COV-07 buys that COV-01's amendment does not is **a named, falsifiable posture**: "these three floors
are deliberately verify-phase-only; no invocation in `scripts/` or `.github/workflows/` SHALL enforce them; arming one
SHALL require amending this requirement" — with the boundary facts from §2/§3 (COV-06 S1 + CI-01 S2 + the
`.coverage`-guarded skip) cited, and the §2 nuance (the ban is scoped, not airtight) stated honestly.

**Named fallback (so design can move it without renegotiating): (i)** — if review judges a new ID for a non-action to
be spec inflation, add one scenario to COV-01 in the PB-10 style
(`process-boundary/spec.md:283-288`, "No CI gate was armed…"). Nothing else changes: same facts, same boundary
sentence, same verify-phase evidence class, same zero test/workflow movement.

**Either way, three constraints hold**: (1) no new test (non-goal), so any scenario maps to **verify-phase static
evidence** and the delta says so explicitly; (2) the delta is a spec-delta file under
`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` (repo convention; the canonical
spec is only touched at `sdd-sync`); (3) revertability — pre-sync revert restores the canonical spec byte-for-byte,
which is only fully true under candidate (ii).

---

## 7. Non-goals (binding on proposal/design/apply)

1. **No gate arming** — no `--fail-under=90` (or any non-100 value) anywhere in `scripts/` or
   `.github/workflows/**`, no new script, no new step, no `pyproject.toml` threshold.
2. **No test changes** — `tests/test_coverage_contract.py`, `tests/test_ci_workflows.py` and the rest of `tests/`
   move zero bytes.
3. **No workflow edits** — `ci.yml`, `release.yml`, `codeql.yml` untouched.
4. **No rule-14 rewording** — `AGENTS.md` untouched (candidate (iii) is closed).
5. **No coverage-number promises** — no new ≥90/observed-margin figure is asserted, re-measured, or promised; the
   floor values stay as COV-01 declares them. No `coverage run` evidence is claimed unless verify actually runs it.
6. **No option (a)/(c)/(d) mechanics** — no enforcement mechanism is designed, no floor is deleted or reworded to
   "aspirational", no "lightly armed" middle option is invented. Option (b) is settled.
7. **Not this change**: the `coverage` `## Purpose` staleness (pre-existing, COV-04 already unmentioned), the
   `.coverage`-guard's CI-skip *design* (owned by COV-01-S3), the TOTAL gate (CI-01/COV-02), the four-module 100%
   mandate (COV-06), the gate-script roster (COV-06 S1), and any widening of the non-100 ban's *scope* (a new
   fence is not requested — only the boundary is recorded).

---

## 8. Open questions for the proposal

1. **Issue #215's acceptance criteria** — not re-readable in this phase (no shell). Does the issue demand anything
   beyond "record the decision as deliberate"? If it names ACs (e.g. a required sentence, a required home), the
   proposal must trace against them; otherwise the parent should confirm the AC list is the narrative in the
   delegation. **(Blocker for the AC-traceability section only.)**
2. **Home choice (i) vs (ii)** — §6 recommends (ii) COV-07 with (i) as the named fallback. Confirm, or pick the
   fallback; no other text changes either way.
3. **Scenarios: zero (COV-04 style) or one (verify-phase static evidence)?** A zero-scenario requirement records the
   decision and triggers no rule-6 mapping, but is only review-checked; a one-scenario requirement forces a mapping
   row whose evidence class must be verify-phase static evidence — and must not restate COV-06 S1 vacuously.
4. **Does COV-07 cite the fact that the non-100 ban is *scoped* (a new script is not fenced), or only that the
   existing surfaces are closed?** §2 argues for the honest version; the proposal should decide how much of the
   nuance belongs in canonical spec text vs the change's design doc.
5. **Requirement title and vocabulary** — the repo's convention is a parenthesised short title (`… (COV-07)`);
   candidate framings: "Per-file floors are deliberately verify-phase-only", "COV-01 floors: no armed gate
   (decision record)". Design fixes the wording; explore does not.
6. **Sync mechanics** — insertion before `## Test Mapping` (`:283`) is required by the file's section order (PB-14 /
   `process-boundary` precedent). Confirm the delta carries the exact block so sync is a pure insert.

---

## 9. Read in this phase (provenance, read-only)

`openspec/specs/coverage/spec.md` (in full) · `openspec/specs/process-boundary/spec.md:252-450` (PB-10, PB-14, the
`## Test Mapping` section) · `openspec/specs/ci/spec.md` (CI-01 header/body/scenarios + Test Mapping anchors) ·
`scripts/check_core_coverage.sh` (in full) · `tests/test_coverage_contract.py` (in full) ·
`tests/test_ci_workflows.py:1-30, 190-345, 446-520` · `pyproject.toml:94-103` · `AGENTS.md:99-132` ·
`.github/workflows/ci.yml:60-90` · `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/{explore.md,
proposal.md,design.md}` (the #216 decision-record precedent) · `openspec/changes/` inventory (only `archive/`
exists — this change root was created by this phase) · `.git/HEAD` (branch confirmation).
