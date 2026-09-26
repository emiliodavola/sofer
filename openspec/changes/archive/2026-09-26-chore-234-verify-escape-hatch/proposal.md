# Proposal — `2026-09-26-chore-234-verify-escape-hatch`

> **Change** `2026-09-26-chore-234-verify-escape-hatch` · issue **#234** (*chore(sdd): the `verify:`
> escape hatch in the Test Mapping gate is unverifiable (46 rows) and 17/20 specs stay outside it*) ·
> branch `chore/234-verify-escape-hatch` · base `dev` at `90de0f7` · store **hybrid** (this file +
> Engram).
>
> **Phase:** proposal. Inputs read directly: issue #234 body, `scripts/check_test_mapping.py`,
> `openspec/test-mapping-registry.md`, `AGENTS.md` rule 6, `openspec/config.yaml`, the three mapped
> specs, and the archived `2026-09-25-test-mapping-gate` change.
>
> **Status:** proposal complete. The issue's explicit **decision** is settled below (option **b**),
> plus the **permanent declared backlog** choice for the unmapped specs and the `SCENARIO_RE` pin.

---

## 1. Intent

The `## Test Mapping` gate added by #211 closes the *enumeration* gap, but its `verify:` escape hatch
is **content-free**: `scripts/check_test_mapping.py` validates only that a `verify:` cell is non-empty
and carries exactly one prefix. Nothing asserts the referenced evidence exists, is reachable, or is
re-checked. **46** `verify:` rows across the three mapped specs therefore pass by construction, and
~600 scenarios assert traceability that no mechanism verifies. The registry lists **17** unmapped
specs with no stated policy for that set beyond "declared backlog".

This change makes the escape hatch **honest and bounded**: it declares plainly what `verify:` is, who
owns it, and when it is reviewed, and it makes the size of the escape hatch visible on every checker
run. It does not pretend the `verify:` rows are proof, and it does not sweep the unmapped specs.

## 2. The decision (issue #234 AC-1)

The issue offers two options. **Decision: option (b)** — `verify:` is a **declared, non-verifiable**
escape hatch with an **owner** and a **review trigger**.

| Option | Assessment |
| --- | --- |
| **(a)** machine-check `verify:` against a declared, resolvable class | Rejected. It would require reshaping 46 rows and inventing a resolvable namespace for heterogeneous evidence (gate exit codes, static inspections, report sections), and it would contradict the accepted design D2 of #211 ("`verify:` is deliberately not machine-verifiable"). Option (a) also risks **false confidence**: "the artifact exists" is not "the scenario is exercised". |
| **(b)** declare `verify:` non-verifiable with owner + review trigger | **Chosen.** It matches the merged #211 design, is the honest limit, and is implementable without inventing verification. The gate's job stays "force the evidence class to be declared", now with an accountable owner and a review cadence. |

For the 17 unmapped specs (AC-2) the issue offers a ratchet **or** an explicit permanent
declared-backlog decision. **Decision: permanent declared backlog**, recorded in
`openspec/test-mapping-registry.md` with the same owner and review trigger. A per-change ratchet
("at most one spec adopts a table per change") is not mechanically enforceable from the tree without a
baseline, and the #211 no-sweep boundary already fixes the set; the explicit policy is the stronger
honest option available.

AC-3 (`SCENARIO_RE` heading-depth assumption) is satisfied by documenting the grammar **and** pinning
it with a test.

## 3. Scope

### In scope

- **AGENTS.md rule 6** — state that a `verify:` row is a declared, non-verifiable escape hatch, name
  its **owner** and its **review trigger**.
- **`openspec/config.yaml` `rules.specs`** — align the normative bullet with rule 6 (the two homes
  must agree).
- **`scripts/check_test_mapping.py`** — state the same in the module docstring; add a run-time
  report line naming the accepted `verify:` row count as **declared, non-verifiable** evidence with
  the owner and review trigger; document the `SCENARIO_RE` four-hash assumption. No resolution or
  execution of `verify:` references is added (that would be option (a)).
- **`openspec/test-mapping-registry.md`** — record the **permanent declared backlog** decision for the
  17 unmapped specs, with owner and review trigger, and retitle the entries from "until a table
  lands" to a permanent-backlog statement.
- **`openspec/specs/process-boundary/spec.md`** — add requirement **PB-15** with the scenario set and
  its Test Mapping rows.
- **Tests** — `tests/test_test_mapping_checker.py` pins the four-hash scenario grammar and the
  declared/non-verifiable `verify:` report line; `tests/test_ci_workflows.py` guards that rule 6,
  `rules.specs`, and the registry state the escape-hatch owner and review trigger.
- Verify-phase evidence and the full suite green.

### Out of scope (non-goals, strictly respected)

- **No verification of `verify:` rows** (option (a) is rejected). No `verify:` reference is resolved,
  executed, or inspected beyond non-emptiness.
- **No table authored for any unmapped spec** (the #211 no-sweep boundary).
- **No gate weakening**: the checker still exits non-zero on the same violations; no row is removed,
  re-prefixed, or reclassified; no coverage floor moves.
- **No production (`src/sofer/`) change.**
- No commit, push, or PR from any SDD phase.

## 4. Approach (settled decisions)

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | Option (b): declare `verify:` non-verifiable with owner + review trigger | Honest, cheap, matches #211 D2; avoids false confidence of option (a) |
| **D2** | The owner is **the repository maintainer**; the review trigger is **any change to a `verify:` row or to a spec's evidence class, and each release review** | A stable, non-personal owner and a concrete recurrence trigger; both must survive turnover |
| **D3** | The checker **reports** the accepted `verify:` count each run | Makes the escape hatch's size visible; a growing hatch is a review signal, not a silent one |
| **D4** | The 17 unmapped specs are a **permanent declared backlog** with the same owner/trigger | The #211 no-sweep boundary is explicit; a ratchet is not mechanically derivable from the tree |
| **D5** | `SCENARIO_RE`'s four-hash assumption is documented **and** pinned by tests | Documentation alone drifts; the test makes a level change fail loudly |
| **D6** | Rule 6, `rules.specs`, and the registry are edited in lockstep | #211's AC requires the normative homes to agree; a static guard enforces it |

## 5. Acceptance-criteria mapping

| AC (issue #234) | Criterion | Satisfied by |
| --- | --- | --- |
| AC-1 | An explicit decision is recorded: (b) rule 6 states `verify:` is a declared, non-verifiable escape hatch with owner and review trigger, and the checker's docstring/error text says so | §2, D1/D2/D3, tasks 1.1–1.3, 2.1–2.2 |
| AC-2 | The 17 unmapped specs get a ratchet **or** an explicit permanent declared-backlog decision, recorded in the registry | D4, task 1.4 |
| AC-3 | The checker's `SCENARIO_RE` heading-depth assumption is documented or pinned by a test | D5, tasks 1.3, 2.2 |
| AC-4 | `pytest` green; `ruff`/`mypy` clean | tasks 3.1–3.3 |

## 6. Verification strategy

- **Behavioural:** the new checker tests run the checker as a subprocess on fixture trees (the
  established harness) and assert observable outcomes: the four-hash grammar (a five-hash heading is
  not enumerated; an indented four-hash heading is) and the declared/non-verifiable `verify:` report
  line with the owner and review trigger.
- **Static:** `tests/test_ci_workflows.py` asserts AGENTS.md rule 6, `openspec/config.yaml`
  `rules.specs`, and the registry all state the non-verifiable escape hatch with the owner and the
  review trigger.
- **Gate/report:** `uv run python scripts/check_test_mapping.py` exits 0 and prints the declared
  `verify:` count; the full suite, ruff, mypy, and pyright are green.
