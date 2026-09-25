# Proposal — `211-test-mapping-gate`

> **Change** `211-test-mapping-gate` · issue **#211** (*chore: spec↔test traceability (rule 6) has no
> enumerating gate — 640 scenarios, only 2 of 20 specs carry a Test Mapping table*) · branch
> `feat/211-test-mapping-gate` at `67289b8` · store **hybrid** (this file + Engram
> `sdd/211-test-mapping-gate/proposal`).
>
> **Phase:** proposal. Inputs read directly: issue #211, #214 and #212 bodies; `AGENTS.md`;
> `openspec/config.yaml`; the three existing `## Test Mapping` sections; and a direct shell
> measurement of `openspec/specs/**` on this branch. Every number in §3 is re-derived here, never
> copied from the issue.
>
> **Status:** proposal complete, ready for spec/design. Option **(b)** was closed by the maintainer
> before this phase and is *not* re-opened: rule 6 is rewritten to state exactly what is enforced; the
> three existing Test Mapping tables adopt a machine-readable `test:` / `verify:` contract; a checker
> in `scripts/` plus one CI gate enforce that contract; and the specs that carry no table are captured
> in an explicit registry under `openspec/` rather than swept. This document settles the WHY, the
> measured inventory, the scope boundary, and the HOW choices the parent left open.

---

## 1. Intent

`AGENTS.md:42` states the repository's central traceability invariant — *"Every SDD spec scenario must
have a corresponding test"* — and `openspec/config.yaml` repeats it normatively (rules.specs: *"Every
spec scenario MUST have a corresponding test (AGENTS.md rule 6)"*). **Nothing enumerates that
mapping, and no gate can fail when it is violated.** The invariant is currently satisfied by authoring
prose: a spec can add scenarios with no test and rule 6 keeps passing.

The measured reality on this branch (§3): **20 specs, 659 scenarios, only 3 specs carry a Test Mapping
table.** The other **17 specs have no mapping surface at all**, so their scenarios are outside any
enumerable artifact. Where tables *do* exist, rows route to prose ("Verify-phase static evidence — …")
that lives in an archived verify report, is re-read by nothing, and cannot fail later.

The root cause is not the individual stale rows (PB-11, COV-01, the ≥14 prose rows) — it is the
**missing mechanism**. This change builds the mechanism at the smallest honest size:

1. **A contract in the tables that exist.** Every data row of a Test Mapping table SHALL begin its
   Verification cell with exactly one machine-readable prefix — `test:` (routed to a repository test)
   or `verify:` (routed to verify-phase evidence) — so the mapping stops being free-form prose.
2. **A checker + CI gate.** A checker in `scripts/` parses the contract, and a CI step runs it, so a
   malformed row or a `test:` pointing at a non-existent test fails the build.
3. **An honest, auditable scope boundary.** The 17 specs without a table are recorded in a registry
   under `openspec/`. The checker asserts the registry and the spec tree agree, so **no spec can
   silently fall outside the gate** — adding a table without removing the registry entry (or vice
   versa) fails.
4. **A truthful rule 6.** `AGENTS.md:42` and `openspec/config.yaml` are rewritten to say what is
   actually enforced, including the escape hatch (`verify:` rows) explicitly, instead of stating an
   absolute that the repo does not honor.

The change is a **mechanism, not a sweep**: it does not author 659 test ids, and it does not invent
mapping tables for 17 specs. It makes the current gap **measured, bounded, and visible**, and makes
future mapped rows **machine-checkable**.

## 2. Scope

### In scope

- **Contract `test:` / `verify:` in the three tables that carry Test Mapping** —
  `openspec/specs/ci/spec.md`, `openspec/specs/coverage/spec.md`,
  `openspec/specs/process-boundary/spec.md`. Every existing data row's Verification cell is
  normalised to begin with exactly one prefix. `test:` names a repository test (path, optionally
  `::test_name`); `verify:` names the verify-phase evidence class (the existing prose is kept, just
  prefixed). This is a **re-tag of existing rows**, not a re-authorship of their content.
- **A checker in `scripts/`** (design default: `scripts/check_test_mapping.py` — Python, matching the
  `scripts/` scope already linted and type-checked per AGENTS rule 12 and the `update_citation.py`
  precedent) that:
  - enumerates `openspec/specs/*/spec.md`;
  - for each spec with a `## Test Mapping` section, requires every data row's Verification cell to
    begin with exactly one `test:` / `verify:` prefix;
  - for a `test:` row, requires the referenced test file to exist, and the referenced `::test_name`
    to be present when given;
  - for a `verify:` row, requires a non-empty rationale;
  - cross-checks the **registry** against the tree: every spec without a `## Test Mapping` section
    MUST be listed; every spec with one MUST NOT be listed.
- **One CI gate** running the checker in the existing lint job (no new job, no new matrix axis),
  reusing the `scripts/check_core_coverage.sh` shape (`ci` CI-01 gate-exit-code precedent).
- **A registry of the specs without a table** (design default:
  `openspec/test-mapping-registry.md`) listing the ~17 specs, each with its measured scenario count,
  as the explicit, auditable backlog — the honest limit of what the gate covers.
- **Rewrite of rule 6** in `AGENTS.md:42` (and the cross-referenced `openspec/config.yaml`
  rules.specs bullet) to state the enforced contract, the `verify:` escape hatch, the `test:`/`verify:`
  prefixes, and the registry scope, matching the checker exactly.
- **Absorption of #214**: rule 6's stale hardcoded test tally is removed as part of the same rewrite
  (replaced by the reproducing command alone), and the other stale tallies #214 names are resolved or
  explicitly cross-referenced in the same pass (`openspec/project.md:40,81,87` → #184;
  `openspec/config.yaml:9` → the `1029 tests` literal).
- Verify-phase evidence and the full suite green (`uv run pytest tests/ -q`).

### Out of scope (non-goals, strictly respected)

- **No sweep.** No mapping table is authored for the registry specs; no test id is invented for the
  659 scenarios. That is the "separate concern" #211's own scope note defers.
- **No test-id backfill from prose.** The ≥14 `verify:` rows keep their existing evidence content;
  only the prefix is added. Reclassifying a `verify:` row as `test:` is a per-row decision for the
  owning change, not this one.
- **#212 is out** (documented gate-command scope drift in `AGENTS.md:39`,
  `CONTRIBUTING.md:28-29`, `.github/PULL_REQUEST_TEMPLATE.md`). It is a separate issue with its own
  owner; nothing in that command-scope surface is touched here.
- **No coverage change of any kind**: no floor movement, no `--fail-under` edit, no new `# pragma: no
  cover` (forbidden in the four AGENTS rule-14 modules), no test-count weakening.
- **No spec content change** beyond the Verification cells of the three tables and the rule/config
  rewrite. Requirements and scenarios are not reworded.
- No commit, push, or PR from any SDD phase.

## 3. Measured inventory (this branch, re-derived)

Direct measurement on `feat/211-test-mapping-gate` at `67289b8`:

```text
$ ls openspec/specs/*/spec.md | wc -l
20
$ grep -l '^## Test Mapping' openspec/specs/*/spec.md | wc -l
3
$ rg -c '^#### Scenario:' openspec/specs/*/spec.md | awk -F: '{s+=$2} END{print s}'
659
```

Per spec (`#### Scenario:` count, one number per spec; no deeper analysis):

| Spec | Test Mapping | Scenarios |
| --- | :---: | ---: |
| ci | yes | 38 |
| cli | — | 48 |
| codebook | — | 38 |
| coverage | yes | 16 |
| data-quality | — | 1 |
| mcp-registration | — | 21 |
| mcp-server | — | 113 |
| metadata | — | 7 |
| packaging | — | 13 |
| parquet-conversion | — | 20 |
| pii-detection | — | 6 |
| prepare | — | 44 |
| process-boundary | yes | 48 |
| profile | — | 23 |
| publish | — | 47 |
| render | — | 21 |
| repo-compliance | — | 66 |
| scan | — | 34 |
| semantic-type-inference | — | 11 |
| tool-config | — | 44 |
| **Total** | **3 yes / 17 no** | **659** |

Two facts the numbers make explicit and this proposal treats as fixed inputs:

- **The issue's numbers have already drifted.** #211 measured `640` scenarios and `2` of `20` specs
  with a table on `dev@5a2ae38`; this branch measures `659` and `3`. `process-boundary` gained its
  table in between. A hand-maintained count is exactly the stale-literal class #214 files — which is
  why the registry (§3, approach) and the checker must be **tree-derived**, and rule 6 must lose its
  hardcoded tally.
- **`data-quality` has 1 `#### Scenario:` heading** while its spec body is long. That is the measured
  count under the exact heading `#### Scenario:` and nothing more is asserted about it here; if its
  scenarios use a different heading level, that is a per-spec concern the checker's design must decide
  (recorded as an open HOW in §4, not silently fixed).

## 4. Approach (settled decisions)

Option (b) is fixed. The HOW choices below are the proposal's, carried into spec/design.

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | The contract is a **prefix on the existing Verification cell** (`test:` / `verify:`), not a new column and not a new file | The three tables already have a `Verification` column with heterogeneous prose; a prefix is the least invasive edit that makes the routing machine-readable, and it preserves every existing evidence string verbatim. A new column would churn the archived table shape; a separate mapping file would duplicate the table and drift from it. |
| **D2** | `test:` names a **repository test path** (optionally `::test_name`); `verify:` names the **evidence class** | `test:` becomes checkable without running the suite (path existence + name presence), which is deterministic and cheap; deep assertion-quality remains the review lens (COV-05 precedent), not this gate's job. `verify:` is deliberately **not** machine-verifiable — it is the honest escape hatch, and the gate's job is only to force it to be declared, not to pretend it is proof. |
| **D3** | The gate is **scoped to specs that carry a `## Test Mapping` section**; the registry covers the rest | Arming a gate over 17 unmapped specs would either fail immediately (they have no rows) or require authoring them — the sweep #211 forbids. Scoping to declared tables makes the gate exact for what exists, while the registry makes the **uncovered set explicit and checked** so it cannot silently grow. |
| **D4** | The registry is a checked **bijection**, not a passive list | A passive list drifts. The checker asserts `{specs with a table}` ∪ `{registry entries}` = `{all specs}` and the two sets are disjoint, so a new spec with no table must be registered (failing until it is) and a spec that gains a table must be de-registered. This is what turns "17 specs have no table" from a fact in an issue into an enforced boundary. |
| **D5** | **One CI step in the existing lint job**, not a new job/axis | Matches `scripts/check_core_coverage.sh` (COV-06) and the CI-01 gate-exit-code precedent; adds no matrix cost, and the lint job already runs the repo's other static gates. |
| **D6** | The checker is **Python in `scripts/`** | `scripts/` is already in the enforced ruff + mypy scope (`ci.yml`), so the checker is held to the same quality bar as the code; Python parses Markdown tables and the registry without a shell quoting trap, and `scripts/update_citation.py` is the precedent for real Python under `scripts/`. |
| **D7** | Rule 6 is rewritten to state the **enforced contract + the escape hatch + the registry**, and its hardcoded tally is deleted (#214) | Rule 6 as written is an absolute the repo does not honor; the rewrite must match D1-D4 exactly. Removing the stale triple in the same edit closes #214's primary AC (the reproducing command alone stays) because PB-11 scenario 1 is satisfied by *no stale literal*, and it removes a hand-edited number that has gone stale twice. |
| **D8** | #214's other stale tallies are **cross-referenced, not silently rewritten**, in the same pass (`openspec/project.md:40,81,87` → #184; `openspec/config.yaml:9`) | #211's mechanism and #214's literals are the same class (hand-maintained figures no run re-derives), so absorbing #214 is in scope; but #184 owns `project.md` and is explicitly still open, so the proposal cross-references it rather than expanding this change into an unrelated doc sweep. `config.yaml:9`'s `1029 tests` is corrected alongside the rule-6 text because that file is edited here anyway. |
| **D9** | **`AGENTS.md:42` (the invariant line) and `openspec/config.yaml` rules.specs are the two normative homes** rewritten in lockstep; the process-boundary PB requirement gains the durable record | The two lines say the same thing and must not disagree (#211 AC: "`AGENTS.md` rule 6 and `openspec/config.yaml` rules agree"). Process-boundary is where PB-11 already lives and is one of the three mapped specs, so the change's own traceability record lands there. |
| **D10** | **#212 stays out** | Different surface (documented gate-command scope), different fix (four tracked doc sites aligned with CI), already separately scoped with its own AC. Absorbing it would blur two unrelated mechanisms. |

Open HOW questions deliberately deferred to spec/design (named, not resolved here):

- **O1** — exact checker filename and CLI (`scripts/check_test_mapping.py` is the default).
- **O2** — registry format (`openspec/test-mapping-registry.md` default) and whether scenario counts
  are stored or re-derived at check time (tree-derived is preferred, per D4/§3 drift).
- **O3** — whether a `test:` node id is required or optional per row, and the exact name-matching rule
  (substring vs `def ` scan) that keeps the check deterministic without running pytest.
- **O4** — `data-quality`'s single `#### Scenario:` heading vs its longer body (is there a heading-level
  convention the checker must honour?).
- **O5** — whether the rewritten rule 6 keeps a non-normative pointer to the registry or inlines the
  count (inlining is the stale-literal trap D7 exists to remove).

## 5. Acceptance-criteria mapping

| AC (source) | Criterion | Satisfied by |
| --- | --- | --- |
| #211 | An explicit decision is recorded: option (b) — rule 6 reworded to what is enforced, escape hatch in `AGENTS.md` | D7, §1 items 1-4, rule-6 + config rewrite |
| #211 | The chosen resolution is pinned by a test or CI step; rule 6 and `config.yaml` rules agree | D5 (CI gate), D9 (lockstep rewrite), `tests/` guard asserting `AGENTS.md`/`config.yaml` text matches the contract |
| #211 | The specs without a mapping table are given one **or covered by the decision** | D3/D4 — the registry covers all 17 explicitly; the checker enforces the bijection |
| #211 | `pytest` green; `ruff`/`mypy` clean | §6 verification |
| #214 | Rule 6's hardcoded triple replaced by the reproducing command alone | D7 (delete the `1766 / 6 / 1772` literal; keep `uv run pytest tests/ -q`) |
| #214 | If a figure stays, PB-11 gains a test/verify step to re-derive it | D7 removes the figure, so no figure stays; PB-11 scenario 1 is satisfied by the absence of the stale literal |
| #214 | Other stale tallies resolved or cross-referenced (`project.md:40,81,87` → #184; `config.yaml:9`) | D8 |
| #212 | *(excluded)* | D10 |

## 6. Verification strategy

- **Unit/static:** `tests/` gains assertions that the checker recognises/mis-recognises rows (a
  `test:` row whose target is absent fails; a `verify:` row without rationale fails; an unregistered
  spec without a table fails), plus a guard that `AGENTS.md` rule 6 and `openspec/config.yaml` rules
  agree with the contract text — the CI-06/COV-06 static-test precedent.
- **Runtime gate evidence:** the CI lint-job step running the checker exits 0 on the change branch,
  pasted into the verify report (CI-01 gate-exit-code precedent).
- **Full suite:** `uv run pytest tests/ -q` green, count re-derived on the branch (never quoted from
  this document — #214's lesson applied to itself).
- **Lint/types:** `uv run ruff check src/ tests/ scripts/` and `uv run mypy src/ scripts/` clean;
  `uv run pyright` clean.
