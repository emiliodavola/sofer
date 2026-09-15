# Proposal: chore-cov01-floors-status-quo

**Change**: `2026-09-15-chore-cov01-floors-status-quo` · **Issue**: #215 — *COV-01's three ≥90% per-file floors
are declared binding but nothing that can fail in CI enforces them* · **Branch**:
`chore/215-cov01-floors-status-quo` (from `dev@319bb7e`; `.git/HEAD` reads
`ref: refs/heads/chore/215-cov01-floors-status-quo`)
**Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram mirrors it at
`sdd/2026-09-15-chore-cov01-floors-status-quo/proposal` (type `decision`)
**Confirmed handoff**: the two product decisions below were confirmed by the user this session and relayed by
the orchestrator; exploration `explore.md` (Engram id 1286)
**Phase inputs read**: `explore.md` (change root; only artifact in the change root — **no `preproposal.md` and
no `research.md` exist for this change**, so the confirmed decisions enter from the orchestrator's handoff, not
from a pre-proposal file), `openspec/specs/coverage/spec.md` (full), `openspec/specs/process-boundary/spec.md`
(PB-10, PB-14, Test Mapping), the archived #216 `proposal.md` / `design.md` / delta, `scripts/check_core_coverage.sh`,
`tests/test_coverage_contract.py`, `tests/test_ci_workflows.py:220-345`, `pyproject.toml:94-103`, `AGENTS.md:95-135`
**Size**: ≈1–2 lines of `AGENTS.md` + a spec delta ≈40–45 lines; **zero** code, test, workflow, script, or
`pyproject.toml` lines · **Delivery**: `auto-chain`, review budget 1500 changed lines → **single PR, no chaining
required; `ask-on-risk` is not triggered** (see *Changed-lines estimate*)
**Research lane**: not selected for this change (decision-recording only; no external claim is made — every
fact below is a read of the working tree)

---

## Intent

COV-01 (`openspec/specs/coverage/spec.md:54-90`) declares three per-file floors as **individually binding**:

| Module | Declared floor | Enforcement that can fail in CI today |
| --- | --- | --- |
| `src/sofer/profile.py` | ≥90% | **none** |
| `src/sofer/mcp_registration.py` | ≥90% | **none** |
| `src/sofer/verification.py` | ≥90% | **none** |

Nothing that can fail in CI enforces them. The gate script loops exactly the four CLI-core modules
(`scripts/check_core_coverage.sh:10` — `for f in cli scanner prepare publish; do`, each `--fail-under=100`);
the only executable ≥90 assertion in the repository loads a **local** `.coverage` file and **skips** when one is
absent (`tests/test_coverage_contract.py:37-40`), which is precisely the state of the CI coverage job at
test-import time (`ci.yml`: `uv sync` → `coverage run -m pytest` → `coverage report -m` → `bash
scripts/check_core_coverage.sh`). COV-01-S3 (`spec.md:86-90`) declares that skip to be intended.

So the repository carries a policy statement with no gate behind it, and — sharper — the obvious arming
mechanism is itself policy-closed: COV-06-S1 (`spec.md:246-250`) forbids any `--fail-under` value other than
100 in the workflow or the gate script, and `tests/test_ci_workflows.py:237-264` / `:278-306` pin that ban
against the **existing** surfaces.

The user's response to #215 was **option (b): keep the status quo and record it as deliberate**. This change is
therefore the record — it is *not* an enforcement change, *not* a coverage-number change, and *not* a mechanism
design. Its whole product content is a durable, falsifiable statement of the current posture plus a pointer for
the next person who asks "why is nothing checking these three files?".

**It changes two documents and stops.** One new spec requirement (COV-07), one Test Mapping row, one added line
in `AGENTS.md` near rule 14.

## Confirmed product decisions carried into this proposal (D1–D2, **user-confirmed**)

These are the orchestrator-relayed, user-confirmed decisions for issue #215. They are **not** re-opened here and
are **not** re-interviewed in the question round below.

| ID | Decision (user-confirmed) | Consequence this proposal builds on |
| --- | --- | --- |
| **D1** | **Option (b) for #215** — keep the status quo: the three second-tier floors stay verify-phase-evidenced only. Record the choice as *deliberate*. No gate arming, no test change, no workflow edit, no new coverage number, no option (a)/(c)/(d) mechanics | The diff is spec/doc only; the deliverable is the *record*, and the record's honesty (what is and is not enforced) is the load-bearing content |
| **D2** | Durable home = **new additive requirement COV-07** in `openspec/specs/coverage/spec.md` — **not** an amendment to COV-01 — **plus exactly one added line/note in `AGENTS.md` near rule 14** pointing at COV-07. Rule 14's own text SHALL NOT be reworded | COV-01..COV-06 keep their clauses, scenarios and already-earned verify evidence byte-for-byte; the agent-facing surface gains a one-line pointer; the canonical coverage spec is touched only at `sdd-sync` |

### In-repo fact this proposal corrects/fixes before designing anything: the next free ID is **COV-07**

`openspec/specs/coverage/spec.md` requirement order: **COV-01** (`:54`), **COV-02** (`:94`), **COV-03** (`:125`),
**COV-04** (retired, `:167`), **COV-05** (`:186`), **COV-06** (`:214`) — `:214` is the highest requirement in the
file, so **COV-07 is free**. Independently corroborated by the delta conventions in the archive and by explore §3.1.
No renumbering and no collision (the #216/PB-13→PB-14 lesson).

### Scope refinement against explore §7 non-goal 4 — recorded, because it is a real divergence

`explore.md` §7 recorded "**No rule-14 rewording** — `AGENTS.md` untouched (candidate (iii) is closed)" and §5(iii)
argued against an AGENTS.md home. **D2 overrides the "untouched" part**: `AGENTS.md` gains **one additive line**.
The non-goal that survives is the one that mattered — **rule 14's existing sentences SHALL NOT be reworded**; the
note is an *addition* pointing at COV-07, not a correction of rule 14, and it carries no mechanical enforcement
obligation (see *Approach → carrier 3* and risk R3). Everything else in explore §7 stands unchanged.

## Verified state (evidence, not opinion)

Every row was read from the working tree in the explore phase (file:line provenance in `explore.md` §2–§3) or
re-read in this phase. No command output is claimed.

| Fact | Evidence | Source |
| --- | --- | --- |
| The gate script gates exactly four modules at 100; the three floors are absent | `for f in cli scanner prepare publish; do` + `--include="src/sofer/${f}.py" --fail-under=100 -m` | `scripts/check_core_coverage.sh:10-11` |
| The script is referenced by the CI coverage job | `run: bash scripts/check_core_coverage.sh` (COV-06 banner above it) | `.github/workflows/ci.yml:80-85` |
| The only executable ≥90 check is switched off in CI **by design** | `@pytest.mark.skipif(not (_REPO_ROOT / ".coverage").exists(), reason="no local .coverage data file (clean checkout — CI measurement is the arbiter)")`; the assertion body is `:41-88` | `tests/test_coverage_contract.py:37-40` |
| COV-01-S3 declares that skip intended | "the contract test SHALL skip, and the suite SHALL pass without it" | `openspec/specs/coverage/spec.md:86-90` |
| COV-06-S1 pins the non-100 ban | "no `--fail-under` value other than 100 SHALL appear in the workflow or script" | `openspec/specs/coverage/spec.md:246-250` |
| Two tests pin that ban against the **existing** surfaces | `test_coverage_job_gates_core_modules_at_100` asserts the loop roster string and that every `--fail-under=<n>` in script + `ci.yml` + `release.yml` equals 100; `test_coverage_gate_is_config_driven_without_cli_floor` bans `--fail-under` / `fail-under` / `fail_under` in both workflow files | `tests/test_ci_workflows.py:237-264`, `:278-306` |
| **The ban is scoped, not airtight** — a brand-new script carrying `--fail-under=90` would turn **no** current test red | Only the one gate script and the two workflow files are read; `:242-244` asserts the roster of *that* script | `tests/test_ci_workflows.py:237-264` |
| No per-file floor is expressible in config | `[tool.coverage.report]` holds `show_missing = true` and the **scalar** `fail_under = 90` | `pyproject.toml:100-102` |
| `## Test Mapping` already exists in the coverage capability, and is the file's last section | section header, intro prose, three-column table; nothing follows the table | `openspec/specs/coverage/spec.md:283` + end of file |
| The capability's mapping convention admits verify-phase **static** evidence | "Every scenario SHALL map to a green test or to verify-phase static/runtime evidence (AGENTS.md rule 6; …)" | `openspec/specs/coverage/spec.md:285-295` |
| The capability already holds a recorded, non-enforced requirement | COV-04 is "RETIRED in this change", "has no scenarios and SHALL NOT be enforced", and its mapping row reads "Recorded in proposal Decision Point 2 / Scope Out … not enforced" | `openspec/specs/coverage/spec.md:167-183` + mapping table |
| The freshest precedent for recording a decision is a **new** requirement with a rationale + an explicit boundary + a named adjacent owner | PB-14 (`process-boundary`), added by #216, beside an untouched PB-10; its delta also carries the `## Test Mapping` rows | `openspec/specs/process-boundary/spec.md:378-426` |
| The repo already accepts **absence-recording** as normative spec content | PB-10 S4: "No CI gate was armed…" — "zero matches SHALL exist in both states and no workflow file SHALL appear in the diff" | `openspec/specs/process-boundary/spec.md:283-288` |
| `AGENTS.md` rule 14 names the **four core modules only**; the three floors appear as a bare spec pointer with **no** enforcement posture | last bullet: "Other modules are governed by their own per-file floors (spec `coverage` COV-01) or have no floor"; rule 14 is the **last** rule in the file (no `### 15.`) | `AGENTS.md:101-126` |
| Rule 14's text is test-pinned, and the pin is **presence-based** | `re.search(r"### 14\..*?(?=\n### 15\.\|\Z)", …)` (the `|` is escaped here so the markdown cell parses) then asserts the four module names, `"100.00%"`, and a pragma-token regex match | `tests/test_ci_workflows.py:266-277` |
| No test reads the coverage spec file | zero matches for `COV-0\d` / `specs/coverage` under `tests/` | `grep tests/` |
| No test enumerates AGENTS.md rules; only rule 14's region and rule 6's anchor are read | `grep AGENTS\.md tests/` → `test_ci_workflows.py:269` only (plus docstring references) | `grep tests/` |
| Repo delta convention: deltas live at `openspec/changes/<change>/specs/<capability>/spec.md`; the canonical spec absorbs them at `sdd-sync`; deltas are additive and carry a blockquote header | read in full | `openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md` |
| Branch is the expected one | `ref: refs/heads/chore/215-cov01-floors-status-quo` | `.git/HEAD` |

### Unverified at proposal time (carried, not assumed)

1. **Issue #215's acceptance-criteria list** could not be re-read (`gh` is not available in this runtime).
   The parent supplied the option-(b) deliverable — *"no code change; add an explicit decision line to the spec /
   AGENTS.md"* — and that is what the AC-traceability section below traces against, stated as such. If the issue
   carries additional ACs, the section must be extended before verify.
2. **Current measured margins** for the three rows (reported on `dev` as `profile.py` 96%, `mcp_registration.py`
   99%, `verification.py` 100%) are transcribed, not re-measured. COV-07 deliberately asserts **no number**, so
   nothing in this change depends on them (non-goal 5).
3. **Exact rendered line count of the AGENTS.md bullet** — one bullet, ~2 wrapped lines; the design phase fixes
   the wording.

## Scope

### In scope (two documents, plus phase artifacts)

1. `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` — the **delta**: an
   `## ADDED Requirements` block for **COV-07** (rationale + enforcement boundary + the "arming is its own SDD
   change" clause), **one** scenario mapped to verify-phase static evidence, and the **one** Test Mapping row.
   The delta inserts COV-07 **before** the canonical file's `## Test Mapping` section on sync.
2. `AGENTS.md` — **exactly one added line/bullet** near rule 14 pointing at COV-07. Rule 14's existing sentences
   are byte-identical before and after.
3. SDD phase artifacts for this change (`proposal.md` here, then `design.md`, `tasks.md`, verify/archive reports).

The canonical `openspec/specs/coverage/spec.md` is **not** edited by this change's apply phase — it absorbs the
delta at `sdd-sync`, exactly as #177/#195/#216 did.

### Out of scope — explicitly not absorbed

| Item | Owner | Why it stays out |
| --- | --- | --- |
| Arming any gate for the three floors (a non-100 scoped invocation, a new gate script, a per-file config key, a workflow step) | a **future, separate SDD change** | D1 = option (b). COV-07 names the arming path as *its own spec change* and nothing else |
| Deleting the floors, or rewording them to "aspirational"/"soft" (issue option (c)/(d)) | — | D1 fixes option (b); rewording a binding floor is a different product decision than recording its enforcement posture |
| Any change to `tests/**` | — | Non-goal 2. In particular the two ban-pinning guards and the `.coverage`-guarded contract test move zero bytes; COV-07's single scenario maps to verify-phase static evidence precisely so that no test is invented |
| Any change to `.github/workflows/**`, `scripts/**`, `pyproject.toml` | — | Non-goal 1/3. Success criterion 5 is a zero-path assertion |
| Widening the **scope** of the non-100 ban (adding a fence for new scripts/workflows) | not requested by #215 | Only the *boundary as it stands* is recorded; the honest scoping caveat is stated in text, not closed by a new mechanism |
| Rewording rule 14, or naming the three modules as a new mandate there | — | D2: the note is a **pointer**, one added line. Rule 14's mandate covers the four core modules and keeps saying so |
| The `coverage` `## Purpose` enumeration (already stale for COV-04) | its own defect, left alone by #195/#216 | CI-07/CI-08 precedent: a purpose enumeration stays untouched; touching it would edit canonical prose for another requirement's class |
| `CONTRIBUTING.md` contributor-facing prose about coverage tiers | not requested | The durable home is the spec + the AGENTS.md pointer |
| The release/CI **asymmetry** between `ci.yml` (which runs the core gate script) and `release.yml` (TOTAL report only) | **#185** | Explicitly another issue's territory; COV-07 asserts nothing about it |
| New coverage figures, re-measurement, or margin promises | — | Non-goal 5: COV-01 owns the floors and the verify-phase rows; COV-07 asserts no number |
| Any `src/sofer/**` path, any dependency, any version move | — | Nothing in `src/` reads coverage policy; the change is documentation-only |

## Approach

Three carriers, each with a distinct job. None is redundant, and together they are the whole change.

| Carrier | Job | Enforced by |
| --- | --- | --- |
| **COV-07** in the coverage capability (delta → canonical at sync) | States the invariant and the boundary **normatively**: the three floors are deliberately verify-phase-only; the COV-06-S1 ban over the *existing* surfaces is the enforcement boundary; arming a gate is its own SDD change that must amend this requirement, COV-06/COV-03, and the two ban-pinning guards | Nothing mechanical — it is a record (the class COV-04 already demonstrates in this capability). Its one scenario is verified by static evidence at verify time |
| **One Test Mapping row** in the coverage table | Keeps the repository's rule-6 index complete: a new scenario with no row would be an unmapped scenario | Review + the table's own convention (`spec.md:285-295`) |
| **One added `AGENTS.md` line** near rule 14 | Makes the posture visible on the surface an agent reads every session — today an agent reading rule 14 sees a `COV-01` pointer and would reasonably assume a gate exists | Nothing mechanical; framing/prose (accepted, see R3) |

### Carrier 1 — COV-07 requirement text (normative intent; design fixes the wording)

**Title shape** (repo convention: short parenthesised title + ID): *"Second-tier per-file floors are
deliberately verify-phase-only (COV-07)"*. Candidate alternates for design: *"No gate is armed for the COV-01
floors (COV-07)"*.

**Clauses the requirement SHALL carry** (intent, not final prose — design owns the exact rendering):

1. **The posture.** The three COV-01 floors (`profile.py` ≥90, `mcp_registration.py` ≥90, `verification.py` ≥90)
   SHALL remain **verify-phase-evidenced only**: no CI step, workflow, committed script, or `pyproject.toml` key
   SHALL enforce them, and this change arms none.
2. **The rationale, with its three in-repo reasons.** (a) coverage.py cannot express a per-file floor in config
   (`[tool.coverage.report] fail_under` is one scalar, `pyproject.toml:100-102`); (b) the only executable in-repo
   ≥90 check is the `.coverage`-guarded `tests/test_coverage_contract.py`, which by **COV-01-S3 design** skips on
   the clean-checkout state the CI coverage job is in; (c) the CLI-core 100% mandate (COV-06) already consumes the
   per-file gate machinery, and its S1 ban is the boundary the repository chose.
3. **The boundary, named and honestly scoped.** The enforcement boundary is the **COV-06-S1 non-100 `--fail-under`
   ban scoped to the surfaces it actually covers** — `scripts/check_core_coverage.sh` (roster exactly
   `cli scanner prepare publish`) and the raw text of `.github/workflows/ci.yml` / `release.yml` — pinned by
   `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and
   `::test_coverage_gate_is_config_driven_without_cli_floor`. The requirement SHALL state explicitly that this
   boundary is **not a fence around the whole repository**: a *new* script or workflow step could carry
   `--fail-under=90` without turning any existing test red, so what makes such a move illegitimate is **this
   requirement**, not the ban alone. (Explore §2's "do not overclaim" nuance, promoted into canonical text —
   see decision D4 below.)
4. **The arming path.** Arming any gate for the three floors — a non-100 scoped invocation, a new gate script, a
   per-file config key, or a workflow step — SHALL be its own SDD change, and that change SHALL amend this
   requirement **together with** COV-06 and COV-03 and the two ban-pinning guards in the same change. (This is
   the PB-14 shape: a named adjacent owner, except here the owner is "the next arming change".)
5. **No number, no drift licence.** This requirement SHALL NOT restate, lower, raise, re-measure or promise a
   coverage value, and SHALL NOT be read as authorizing a floor to drift below 90: the floors' values and their
   verify-phase evidence class stay exactly as **COV-01** declares them, and the TOTAL gate stays config-owned at
   90 (COV-02 / `ci` CI-01).
6. **Continuity clause.** This requirement is additive: COV-01..COV-06 keep their clauses, scenarios and evidence
   unchanged, and this requirement SHALL NOT be read as substituting for COV-01 (the floors still bind as
   declared) nor as weakening COV-06 (which owns the four-module mandate).

### Carrier 1b — COV-07's scenario count and content (**decided here: exactly one scenario**)

**Decision: one scenario**, mapped to **verify-phase static evidence**, consistent with the delegation's "one
Test Mapping row" and with rule 6 (every scenario needs a mapping; a second scenario would need a second row whose
evidence class cannot be a green test under non-goal 2).

**Why not zero (the COV-04 form)?** COV-04's zero-scenario shape works because it is a *retirement marker* — its
content is "superseded, has no scenarios, SHALL NOT be enforced", and its mapping row points at the decision
record. COV-07 is not a retirement: it states a live posture, a boundary, and a forward obligation, and it is the
requirement a future reader will cite when asking "is a gate intended here?". Giving it one scenario makes the
status quo **checkable at verify time** (a static inventory of the four surfaces) rather than only assertable in
review.

**Why not two?** A second scenario about "the boundary is scoped, not airtight" would assert a property of
*another* requirement's text (COV-06-S1's coverage), which is review prose, not evidence — it belongs in clause 3.
A second scenario about "a future arming must be its own SDD change" has no observable evidence class at all
under this change's non-goals. Both live in the requirement body, exactly as PB-10 keeps its `#194`-ownership
clause in the body and gives scenarios only to the observable properties.

**Scenario intent** — *"No gate is armed for the three second-tier floors"*:

> - GIVEN the enforcement surfaces as committed by this change — `scripts/check_core_coverage.sh`,
>   `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `pyproject.toml`'s
>   `[tool.coverage.report]`
> - WHEN they are inspected at verify time
> - THEN the gate script's module roster SHALL still be exactly the four CLI-core modules and every
>   `--fail-under` literal in `scripts/` and both workflows SHALL still be `100` (the COV-06-S1 boundary), and
>   the only coverage threshold in `pyproject.toml` SHALL still be the scalar TOTAL `fail_under = 90`
> - AND `profile.py`, `mcp_registration.py` and `verification.py` SHALL appear in no gated invocation and no CI
>   step SHALL enforce a ≥90 per-file floor — they stay COV-01 verify-phase evidence
> - AND this evidence is **verify-phase static evidence** recorded in the verify report; this change SHALL add no
>   test, and the two existing ban-pinning guards SHALL stay green **unmodified** (they keep the existing
>   surfaces closed; they do not make the ban airtight — clause 3 is the record)

**Why this scenario is not a vacuous restatement of COV-06-S1** (the objection explore §5(ii) raised): COV-06-S1
asserts what *must* appear (the four core paths with `--fail-under=100`) and that no *other* floor value appears.
COV-07's scenario asserts the complementary inventory that COV-06 never states — that the three named floor
modules appear in **no** gated invocation, that no CI step enforces a ≥90 per-file floor, and that the skip of
`tests/test_coverage_contract.py` on a clean checkout is the *designed* state rather than an oversight. It is a
"recorded, not enforced" inventory, and the mapping row says exactly that.

### Carrier 2 — the Test Mapping row (one row, appended to an existing table)

The delta carries `## Test Mapping` with the intro prose already used by the capability (`spec.md:285-295`) and
**one** row:

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| COV-07 | No gate is armed for the three second-tier floors | Verify-phase **static evidence** — read of `scripts/check_core_coverage.sh` (roster = four CLI-core modules), `.github/workflows/{ci,release}.yml` (no non-100 `--fail-under`, no `fail_under`) and `pyproject.toml` (scalar `fail_under = 90` only), recorded in the verify report; the two existing pinned guards `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and `::test_coverage_gate_is_config_driven_without_cli_floor` stay green **unmodified** — no new test is added by this change |

**First-of-its-kind mechanics, so design must state them explicitly:** every in-repo delta so far either created a
`## Test Mapping` section (#216) or worked in a capability that already had one (the `ci`/`coverage` deltas).
COV-07 is the first requirement whose mapping row is **appended to an existing table**. Sync therefore does two
things in the canonical file: (a) insert the COV-07 block **before** `## Test Mapping` (`spec.md:283`), and (b)
append the single row **at the end of the existing table** (after the last COV-06 row). Both steps are specified
in the delta and in the design phase.

### Carrier 3 — the `AGENTS.md` line (exactly one added line; rule 14 not reworded)

**Decided placement**: one **additive bullet at the end of rule 14's bullet list** (after `AGENTS.md:125-126`'s
"…own per-file floors (spec `coverage` COV-01) or have no floor."). Rationale: rule 14 is the **last** rule in the
file (no `### 15.` exists), so there is no "outside rule 14" region after it; a bullet is the minimal possible
diff, keeps the list structure, and is exactly the "near rule 14" surface D2 asked for.

**Draft text (design finalizes; one bullet, ~2 wrapped lines):**

```markdown
-   Adjacent policy pointer (not part of this rule's mandate): the three second-tier
    per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are
    deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a
    gate for them is a spec change (see spec `coverage` COV-07).
```

Four properties, all deliberate:

- **Additive only.** No existing sentence in rule 14 is edited, reordered, or deleted, so the "no rule-14
  rewording" non-goal survives (explore §7 non-goal 4, narrowed by D2 to "no rewording").
- **It does not create a second mandate.** The bullet says *pointer*, and the parenthetical keeps it out of
  rule 14's mandate, which continues to cover exactly the four core modules.
- **It stays green against the pin.** `tests/test_ci_workflows.py:266-277` captures rule 14 with
  `### 14\..*?(?=\n### 15\.|\Z)` and asserts **presence** of the four module names, `100.00%`, and a pragma
  token; adding a bullet cannot remove any of them. Because rule 14 is the file's last rule, the added bullet
  **is** inside the regex-captured region — verified harmless (presence-based assertions) and recorded here so
  the design phase does not have to rediscover it. **No test change is required** and none is made (non-goal 2).
- **Discoverability is the point.** A reader of `AGENTS.md` today sees a `COV-01` pointer and would reasonably
  infer a gate exists; the one line removes that false inference at the surface agents actually read.

### Spec delta and sync plan

- **Delta path**: `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` (repo
  convention; the canonical file is untouched by apply).
- **Section shape** (mirrors the #216 delta): `# Delta for coverage` → a `>` blockquote header (change / issue /
  branch / store topic key; **capability choice**: `coverage`, justified because the invariant is a property of
  the coverage policy the capability already owns — COV-01 declares the floors, COV-03/COV-06 own the gate
  machinery, and COV-04 already demonstrates the recorded-not-enforced shape in this very file; **additive, not
  destructive**: COV-01..COV-06 keep clauses and scenarios byte-for-byte, so archive-time replacement of a
  canonical block would be a lossy no-op; **domain hygiene**: delta not full spec, and no other active change
  carries `specs/coverage/`) → `## ADDED Requirements` with the COV-07 block (requirement + **one** scenario) →
  `## Test Mapping` with the single appended row → `## Cross-referenced and deliberately untouched` →
  a **Non-goals** paragraph.
- **Sync step (`sdd-sync`)**: (a) insert the COV-07 block **between** COV-06's last scenario (`spec.md:275-280`)
  and the `---` preceding `## Test Mapping` (`spec.md:281-283`) — **order is load-bearing: a requirement placed
  after the mapping table would break the file's section order**; and (b) append the single row at the end of the
  existing table. Sync edits nothing else: COV-01..COV-06 text is replaced by itself (lossless no-op), the
  `## Purpose` enumeration is deliberately left stale (COV-04 precedent), and `## Test Mapping`'s existing prose
  and rows are untouched.
- **Pre-sync revertability**: because the change is purely additive and pre-sync, reverting the change commit
  restores the canonical `coverage` spec **byte-for-byte** — the property explore §6 named as candidate (ii)'s
  advantage over amending COV-01.
- **Named fallback (so design/review can move without renegotiating anything else):** if review judges a new ID
  for a non-action to be spec inflation, add **one scenario to COV-01** in the PB-10 "No CI gate was armed…"
  style instead of creating COV-07. The facts, the boundary clause, the honest scoping caveat, the evidence
  class, and the AGENTS.md pointer are **identical** under either option; only the carrier and the ID change.
  (Explore §6's fallback, retained.)

## Acceptance-criteria traceability (issue #215, as supplied by the parent)

The issue's AC list itself could not be re-read in this runtime (no `gh`; stated as unverified item 1). The
option-(b) deliverable relayed by the parent is *"no code change; add an explicit decision line to the spec /
AGENTS.md"*, transcribed as AC1–AC3 below.

| AC | Criterion (transcription) | How this change satisfies it | Evidence class |
| --- | --- | --- | --- |
| AC1 | **No code change** | The diff contains zero `src/sofer/**`, zero `tests/**`, zero `scripts/**`, zero `.github/workflows/**`, zero `pyproject.toml` lines. The only executable-content-bearing surfaces of the repository are untouched: the gate script still loops four modules at 100, both workflows are byte-identical, `fail_under = 90` is the only threshold | **Static/diff evidence** — `git diff --stat` + success criterion 5's zero-path assertions + success criterion 6's `git grep` for non-100 floor literals under `scripts/` and `.github/workflows/` (zero matches before **and** after) |
| AC2 | **Add an explicit decision line to the spec** | **COV-07** in the `coverage` capability: the deliberate verify-phase-only posture, the rationale (three in-repo reasons), the enforcement boundary **named and honestly scoped**, the "arming is its own SDD change amending COV-06/COV-03 + the two ban guards" clause, and the no-number/no-drift clause. Purely additive ⇒ COV-01's already-earned verify evidence and its three mapping rows stay untouched | **Normative spec text** (canonical after sync) + **verify-phase static evidence** for its single scenario (mapping row above) |
| AC3 | **…to the spec / AGENTS.md** | Exactly **one** added `AGENTS.md` bullet near rule 14 pointing at COV-07 and stating that the floors are deliberately un-gated, with rule 14's existing mandate text byte-identical | **Static/diff evidence** — the added bullet (one line) + `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` green **unmodified** |

**What this change explicitly does not claim:** that the floors are now enforced (they are not — that is the
recorded decision), that the non-100 ban is airtight (it is scoped, and clause 3 says so), that any coverage value
changed, or that a gate will ever be armed. The record's value is precisely that these four statements are now
written down where the next question will find them.

## Changed-lines estimate and review workload

| File | Change | Changed lines (add+del) |
| --- | --- | --- |
| `openspec/changes/…/specs/coverage/spec.md` (delta) | header blockquote (~10) + COV-07 requirement (~20–25) + one scenario (~10) + `## Test Mapping` row (~1) + cross-referenced/non-goals (~10) | ≈45 (40–55) |
| `AGENTS.md` | one added bullet near rule 14 | ≈2 |
| **Functional + spec subtotal** | | **≈47 (42–57)** |
| SDD phase artifacts (proposal → verify/report under the change root) | prospective documentation text | not counted as product size (repo precedent: #177, #195, #216 all list artifacts separately) |

**Delivery decision: single PR.** ≈47 lines against a 1500-line review budget is far inside it; nothing here is a
candidate for chaining, and `ask-on-risk` is not triggered. Even if the parent counts phase artifacts in the diff
(≈400–600 lines for the whole SDD cycle), the change stays inside the budget. If that ever ceased to be true, the
natural slice is *spec delta first, `AGENTS.md` pointer second* — but the pointer and the requirement text must
never land in different slices, since the pointer is meaningless without COV-07 to point at.

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| **COV-07 is a record, not an obligation** — a new ID for a non-action reads as spec inflation and is not falsifiable | Medium | Review friction; a reviewer may reasonably ask "what does this requirement make anyone do?" | The one scenario gives the requirement a checkable verify-time inventory (not just review prose); clause 6 makes the additivity and non-substitution explicit; the named fallback (a PB-10-style absence scenario on COV-01) is recorded and changes nothing else |
| **The record is misread as an airtight prohibition** — a reader concludes "arming a non-100 floor is impossible" | Medium — the natural misreading of a ban-pinned policy | A future contributor either feels blocked or (worse) believes a *new* script would be caught by CI and is surprised when it is not | Clause 3 states the scoping honestly in canonical text (this is decision D4), and the proposal repeats it. **The words "is impossible to arm" appear nowhere** in this change's artifacts |
| **The recorded decision is later read as licence to let a floor drift** below 90, since nothing enforces it | Low–Medium | A floor erodes without a red gate — the exact defect #215 is about, but now with a written excuse | Clause 5: COV-07 SHALL NOT restate/lower/raise the floors and SHALL NOT be read as authorizing drift; COV-01's floors and their verify-phase evidence class stay as declared; the `.coverage`-guarded contract test remains the local check |
| **The `AGENTS.md` bullet lands under a heading about a different tier** (rule 14 is "CLI-core coverage: 100% mandate, zero pragmas"; the floors are second-tier) and confuses a reader | Medium — explore §5(iii) raised exactly this | A reader attributes the floors to rule 14's mandate | The bullet's leading clause marks it an **adjacent policy pointer, not part of this rule's mandate**, and it points at the spec for the substance. The tradeoff is accepted deliberately (D2 chose agent-facing visibility); the spec remains the normative home |
| **Rule 14's text-asserted guard goes red** because the added bullet is inside the regex-captured region (`### 14\.[^\Z]` — rule 14 is the file's last rule) | Low — **verified presence-based this phase** (`:266-277` asserts four module names, `100.00%`, a pragma token) | A red suite on a docs-only change | Verified at proposal time and restated for design: no test change is needed (non-goal 2). Verify confirms the guard green **unmodified**; if the design phase ever changed the note into a *reword* of an existing rule-14 sentence, that would be caught here |
| **Sync inserts COV-07 in the wrong place** (after the `## Test Mapping` table), breaking the canonical file's section order | Low — but the failure is silent and structural | A requirement stranded below the index; future readers and tooling see a malformed capability file | The insertion point is specified twice (here and in the delta header): **between COV-06's last scenario and the `---` preceding `## Test Mapping` at `:281-283`**. First-of-its-kind mechanics (appending a row to an existing table) are also named explicitly |
| **Scope creep into #185's territory** (release/CI asymmetry) or into "improve the ban" (fencing new scripts) | Low–Medium — the neighbourhood is tempting because the boundary is visibly scoped | The change stops being a record and becomes a policy change — a different product decision | Both are explicit *Out of scope* rows with owners; success criteria assert zero workflow/script/pyproject movement |
| **Someone expects the recorded margins (96% / 99% / 100%) to appear in COV-07** and treats their absence as an incomplete record | Medium | Review churn; pressure to add numbers | Non-goal 5, stated in the *Out of scope* table and in clause 5: COV-01 owns floors and margins; COV-07 asserts no figure, and none is promised or re-measured. The reported margins are carried in the **proposal** as context only, marked as transcribed |
| **The `## Purpose` staleness grows** (it already omits COV-04; COV-07 will be omitted too) | Certain, by decision | A reader of the purpose paragraph sees an incomplete enumeration | Deliberate: the CI-07/CI-08 precedent leaves purpose enumerations untouched, and editing canonical prose for a third requirement's class is not this chore's job. Recorded as a named non-goal, owned by whoever fixes the COV-04 gap |
| **The change quietly widens** (someone also edits the contract test, the gate script, or the workflows "while here") | Low, but the temptation is real for a coverage chore | Destroys the "no code change" AC and confounds every piece of evidence | Success criteria assert **zero** paths in `src/`, `tests/`, `scripts/`, `.github/workflows/`, `pyproject.toml`; the tally must be unchanged (no test added) |

## Rollback

**Trivial, complete, and immediate.** Revert the single commit: the delta disappears, the `AGENTS.md` bullet
disappears, and the canonical `openspec/specs/coverage/spec.md` is untouched until `sdd-sync` — so a pre-sync
revert leaves **all** canonical specs byte-for-byte as they are, which is the strongest form of reversibility
available (explore §6).

- No runtime behaviour in the package, no test, no workflow, no gate script, no `pyproject.toml` key, no
  dependency, no lockfile, no published artefact, no version move.
- No CI effect either way: nothing in the diff is read by any workflow, and the only guard that reads either
  edited document (rule 14's pin) is green before and after.
- After a revert the repository is back to "three floors declared, nothing enforcing them, nothing saying so",
  with issue #215 still open and this change's explore/proposal records still valid.

## Success criteria

1. The delta at `openspec/changes/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md` contains
   exactly **one** new requirement (**COV-07**), **one** scenario, and **one** Test Mapping row, under
   `## ADDED Requirements` with the blockquote header.
2. COV-07's text states the posture, the rationale, the **scoped** boundary (with the "not a fence around the
   whole repository" caveat), the arming path (own SDD change amending COV-06/COV-03 + the two ban guards), and
   the no-number/no-drift clause; **it contains no coverage figure**.
3. The change is **additive**: the canonical `openspec/specs/coverage/spec.md` is not edited by apply, and no
   COV-01..COV-06 clause or scenario is reworded anywhere in the diff.
4. `AGENTS.md` gains exactly **one** added line (one bullet near rule 14) pointing at COV-07; rule 14's existing
   sentences are byte-identical (`git diff -U0 -- AGENTS.md` shows one added line and zero deleted lines).
5. `git diff --stat` contains **exactly**: `AGENTS.md`, the change's delta, and the change's phase artifacts.
   **Zero** `src/sofer/**`, zero `tests/**`, zero `scripts/**`, zero `.github/workflows/**`, zero
   `pyproject.toml`, zero `uv.lock`.
6. `git grep -n -- "--fail-under=" -- scripts/ .github/workflows/` returns only `100` literals, before and after;
   `git grep -n "fail_under" -- .github/workflows/` returns zero matches, before and after.
7. `uv run pytest tests/ -q` is green with the tally **unchanged** (no test added, none skipped newly). The
   authoritative figure is re-derived on this branch at verify time — the proposal carries the reported
   `1766 passed, 6 skipped (1772 collected)` only as context, never as a promise (AGENTS.md rule 6).
8. `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` passes **unmodified** after the
   `AGENTS.md` bullet lands; `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and
   `::test_coverage_gate_is_config_driven_without_cli_floor` pass unmodified.
9. The verify report carries the **static evidence** for COV-07's single scenario: the gate script's roster, both
   workflows' floor literals, and `pyproject.toml`'s scalar threshold, each pasted as read at verify time.
10. `sdd-sync` inserts COV-07 **before** `## Test Mapping` and appends the row at the end of the existing table,
    editing nothing else in the canonical capability file.

## Open items passed forward (not decisions)

1. **Issue #215's full AC list** — not re-readable here; the parent's transcription (AC1–AC3 above) is what this
   proposal traces. If the issue carries more ACs, extend the traceability table before verify.
2. **Exact COV-07 wording, title, and clause boundaries** — design phase, against the intent in *Carrier 1*.
3. **Exact `AGENTS.md` bullet wording** and whether it names the three modules (recommended: yes — it is the
   discoverability payload) — design phase; the placement decision (final bullet of rule 14's list) is made here.
4. **The delta's cross-referenced/non-goals prose** — design phase, mirroring the #216 delta's shape.
5. **Observed-margin figures for the three rows** — deliberately *not* part of COV-07; if the verify phase
   captures them, they belong in the verify report / COV-01's existing evidence chain, never in the new
   requirement text.

## Decisions this proposal makes that explore left open

| Explore open item | Decision now | Where |
| --- | --- | --- |
| §8 Q2 — home choice (i) vs (ii) | **(ii) new additive COV-07**, with (i) as the named fallback; **not** an amendment of COV-01 | D2 (confirmed) + *Carrier 1* |
| §8 Q3 — zero scenarios (COV-04 style) or one (static evidence) | **Exactly one**, mapped to verify-phase static evidence; the boundary and arming-path content stays in the requirement body | *Carrier 1b* |
| §8 Q4 — how much of the "ban is scoped, not airtight" nuance goes into canonical text | **One explicit clause in COV-07** (clause 3), plus mechanics in the design doc; the "is impossible to arm" framing is banned | *Carrier 1* clause 3, risk R2 |
| §8 Q5 — requirement title | **"Second-tier per-file floors are deliberately verify-phase-only (COV-07)"**, one alternate named; design fixes the final clause-level prose | *Carrier 1* |
| §8 Q6 — sync mechanics | Insertion **before** `## Test Mapping`; one row appended to the existing table (first-of-its-kind mechanics named) | *Spec delta and sync plan* |
| §5(iii) — AGENTS.md home "excluded by non-goals" | **Overridden by D2, narrowly**: one additive bullet, rule 14 not reworded, no test change needed (guard verified presence-based) | *Scope refinement* + *Carrier 3* |
| §7 non-goal 6 / #185 | Confirmed out of scope: no option (a)/(c)/(d) mechanics and no release/CI asymmetry decision | *Out of scope* table |
| `## Purpose` staleness (COV-04 already unmentioned) | **Left stale deliberately** (CI-07/CI-08 precedent); named non-goal | Risk row + *Out of scope* |

## Proposal question round

These questions are meant to improve the product understanding behind a change that is *only* a record — not to
re-open D1/D2 (already user-confirmed: option (b), COV-07 + one `AGENTS.md` line) and not to discuss test commands
or PR shape. Answer, correct the framing, ask for a second round, or **skip**: the proposal is written to remain
valid if every question is skipped, and the *Assumptions* block records exactly what "skip" means.

**Q1 — Is the record's audience an agent reading `AGENTS.md`, a maintainer reading the spec, or both?**
This decides how much the one bullet has to carry. If the audience is "an agent that will never open
`openspec/specs/`", the bullet needs enough substance (the three module names, the word "not CI-gated", the pointer)
to prevent a false inference on its own. If the spec is the audience and `AGENTS.md` only needs a breadcrumb, the
bullet can be shorter and less informative.
*Assumptions guarded:* that agent-facing discoverability is a product requirement of this record rather than a
convenience; that one line is sufficient for it; and that putting the floors' names inside a rule-14 bullet does not
misattribute them to the 100% mandate. **Depends on this answer:** the bullet's wording and length, the "adjacent
policy pointer" framing, and risk R4's mitigation. **Q1 guarded assumption: both audiences, with the bullet
carrying the pointer plus the posture, and the spec carrying the substance.**

**Q2 — When someone later wants these three floors gated, is "open a new SDD change that amends COV-06/COV-03 and
the two ban guards" the right friction, or would you rather the record name a *trigger* (e.g. "revisit when a
floor's measured margin shrinks below X") or an owner/issue?**
This change's answer is "the arming decision is its own change, nothing else is asked". The alternative is a
conditional review trigger, which is a different kind of policy (a maintenance obligation rather than a fence).
*Assumptions guarded:* that the status quo is acceptable indefinitely unless someone deliberately re-opens it;
that no monitoring/trigger obligation is being created; and that the repository prefers a deliberate spec change
over a scheduled review. **Depends on this answer:** COV-07's arming clause, and whether a new owner/trigger row
belongs in the requirement text (it does not today). **Q2 guarded assumption: the friction is correct and no
trigger or owner is named.**

**Q3 — Should the record state the honest limitation out loud in canonical text — that the non-100 ban covers
today's gate script and the two workflows only, so a *new* script could carry a 90 floor without any current test
going red?**
The proposal says yes (one clause), because saying "nothing can enforce these" while a future reader assumes CI
would catch an attempt is exactly the kind of half-truth that gets a repo into #215-style trouble. The alternative
is to keep the caveat in the design doc only and let the canonical requirement state just the boundary.
*Assumptions guarded:* that canonical spec text is the right home for a policy's honest scope; that a reviewer
would not read the caveat as an invitation; and that precision here is worth the extra clause. **Depends on this
answer:** COV-07 clause 3 and risk R2's mitigation. **Q3 guarded assumption: yes, one clause in the requirement
text.**

**Q4 — Is "record, don't enforce" the right long-term posture for these three files specifically, or should the
record itself be time-boxed (e.g. "revisit at the next coverage-policy change")?**
#215's option (b) is deliberately open-ended. A reader six months from now cannot tell whether the status quo is
still intended or merely still unreviewed. A one-clause expiry/revisit note ("this posture SHALL be re-affirmed or
replaced at the next coverage-policy change") is the cheap alternative.
*Assumptions guarded:* that "deliberate" without an explicit review horizon still communicates intent; that no
expiry obligation is needed; and that COV-01's own verify-phase evidence keeps the floors visible often enough that
the posture gets re-read. **Depends on this answer:** whether COV-07 gains a revisit clause (today it does not).
**Q4 guarded assumption: no expiry/revisit clause is added — the status quo is intended until a deliberate
change revisits it.**

### Assumptions this proposal stands on if every question is skipped

1. The record's audience is **both** `AGENTS.md` readers and spec readers: the bullet carries the posture plus the
   pointer; the spec carries the substance (Q1).
2. The arming decision stays a future deliberate SDD change, with **no** monitoring trigger, owner, or expiry
   clause added by this change (Q2, Q4).
3. The **honest scoping caveat belongs in canonical COV-07 text** as one clause, and the phrase "is impossible to
   arm" is used nowhere (Q3).
4. COV-07 is **additive and non-substituting**: COV-01's floors, their values, and their verify-phase evidence
   class are untouched, and COV-06's mandate is neither weakened nor extended.
5. The deliverable is a **documentation-only record** — no code, no test, no workflow, no gate, no coverage number
   (issue #215 option (b), as relayed).
6. The next free `coverage` requirement ID is **COV-07** (in-repo fact, verified this phase).
7. `AGENTS.md` rule 14 is the file's **last** rule, so the added bullet falls inside the guard's regex capture —
   verified harmless because the guard asserts presence, and **no test change is made**.

## Provenance read in this phase

`openspec/changes/2026-09-15-chore-cov01-floors-status-quo/explore.md` (full; the change root contains no other
artifact) · Engram observation 1286 (`sdd/2026-09-15-chore-cov01-floors-status-quo/explore`) ·
`openspec/specs/coverage/spec.md` (full, `## Purpose` through the end of the Test Mapping table) ·
`openspec/specs/process-boundary/spec.md:250-450` (PB-10, PB-11, PB-12, PB-13, PB-14, `## Test Mapping`) ·
`openspec/changes/archive/2026-09-15-chore-ruff-format-hook-scope/{proposal.md,design.md,
specs/process-boundary/spec.md}` · `scripts/check_core_coverage.sh` · `tests/test_coverage_contract.py` ·
`tests/test_ci_workflows.py:220-345` · `pyproject.toml:94-103` · `AGENTS.md:95-135` · `.git/HEAD` ·
`grep tests/` for `AGENTS\.md`, `COV-0\d`, `specs/coverage` (no test reads the coverage spec; only the rule-14 pin
reads `AGENTS.md`).
