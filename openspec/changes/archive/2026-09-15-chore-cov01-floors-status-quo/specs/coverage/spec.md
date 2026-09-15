# Delta for coverage

> **Change** `2026-09-15-chore-cov01-floors-status-quo` (issue #215) · branch
> `chore/215-cov01-floors-status-quo` · store **hybrid** (Engram mirror topic key
> `sdd/2026-09-15-chore-cov01-floors-status-quo/spec`).
>
> **Capability `coverage`, justified.** The recorded invariant is the enforcement posture of the three
> COV-01 floors, and this capability already owns that object: COV-01 declares the floors, COV-03/COV-06
> own the gate machinery, and COV-04 already demonstrates the recorded-not-enforced shape in this same
> file. The alternative home, `ci` CI-01, was considered and rejected: CI-01 owns the config-declared
> TOTAL floor and this change arms no CI step, so a `ci` requirement about un-gated per-file floors would
> be misfiled. `ci` is cross-referenced only, never modified.
>
> **Additive, not destructive.** COV-01..COV-06 keep their clauses, scenarios and earned verify evidence
> byte-for-byte, so archive-time replacement of a canonical block would be a lossy no-op; the clause
> enters as **new** requirement **COV-07** — the next free ID in this capability, whose canonical file
> ends at COV-06.
>
> **Sync mechanics (first of their kind in this repository).** This is the first requirement whose Test
> Mapping row is **appended to an existing table** rather than creating the section. Sync therefore
> (a) inserts the COV-07 block — requirement, scenario, and its own trailing `---` separator — between the
> `---` that closes COV-06 (`openspec/specs/coverage/spec.md:281`) and the `## Test Mapping` heading
> (`:283`), so no doubled separator is produced, and (b) appends the single row at the **end of the
> existing table**, immediately after the COV-06 TOTAL row (`:324`, the file's last content line). Sync
> edits nothing else: the `## Test Mapping` intro prose and every existing row stay byte-identical, and
> the `## Purpose` enumeration is deliberately left stale (the CI-07/CI-08 precedent — it already omits
> COV-04).

## ADDED Requirements

### Requirement: Second-tier per-file floors are deliberately verify-phase-only (COV-07)

The three COV-01 floors — `src/sofer/profile.py`, `src/sofer/mcp_registration.py`,
and `src/sofer/verification.py` — SHALL remain **verify-phase-evidenced only**: no
CI step, workflow, committed gate script, or `pyproject.toml` key SHALL enforce
them, and this requirement arms none. The posture is deliberate, not an oversight,
for three in-repo reasons: (a) coverage.py cannot express a per-file floor in
config — `[tool.coverage.report] fail_under` is a single scalar owned by the TOTAL
gate (CI-01 / COV-02); (b) the only executable in-repo ≥90 check,
`tests/test_coverage_contract.py`, skips when no local `.coverage` data file is
present, which is exactly the state the CI coverage job collects in, and COV-01-S3
declares that skip intended; and (c) the CLI-core 100% mandate (COV-06) already
consumes the repository's per-file gate machinery, and its S1 floor-literal ban is
the boundary this repository chose.

The enforcement boundary SHALL be that COV-06-S1 ban, scoped to the surfaces it
actually covers: `scripts/check_core_coverage.sh`, whose module roster is exactly
`cli scanner prepare publish`, and the raw text of `.github/workflows/ci.yml` and
`.github/workflows/release.yml`, pinned by
`tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and
`::test_coverage_gate_is_config_driven_without_cli_floor`. That boundary SHALL NOT
be read as a fence around the whole repository: a new gate script or workflow step
carrying a floor other than 100 would turn no existing test red, so what makes such
a move illegitimate is this requirement, not the ban alone.

Arming any gate for the three floors — a non-100 scoped invocation, a new gate
script, a per-file config key, or a workflow step — SHALL be its own SDD change,
and that change SHALL amend this requirement together with COV-06 and COV-03 and
the two ban-pinning guards named above, in the same change. This requirement SHALL
NOT restate, lower, raise, re-measure, or promise a coverage value, and SHALL NOT
be read as authorizing any of those floors to drift below the value COV-01
declares: the floors' values and their verify-phase evidence class stay exactly as
COV-01 declares them, and the TOTAL gate stays config-owned at 90 (COV-02 / `ci`
CI-01).

This requirement is additive: COV-01..COV-06 SHALL keep their clauses, scenarios,
and earned verify evidence unchanged, and this requirement SHALL NOT be read as
substituting for COV-01 (the floors still bind as declared) nor as weakening
COV-06, which owns the four-module mandate.

#### Scenario: No gate is armed for the three second-tier floors

- GIVEN the enforcement surfaces as committed by this change — `scripts/check_core_coverage.sh`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `pyproject.toml`'s `[tool.coverage.report]`
- WHEN they are inspected at verify time
- THEN the gate script's module roster SHALL still be exactly the four CLI-core modules, no `--fail-under` value other than 100 SHALL appear in the script or in either workflow (the COV-06-S1 boundary), and the only coverage threshold in `pyproject.toml` SHALL still be the scalar TOTAL `fail_under = 90` (CI-01 / COV-02)
- AND `profile.py`, `mcp_registration.py`, and `verification.py` SHALL appear in no gated invocation and no CI step SHALL enforce a per-file floor for any of them — they stay COV-01 verify-phase evidence
- AND this SHALL remain **verify-phase static evidence** recorded in the verify report: this requirement adds no test, and the two ban-pinning guards SHALL stay green **unmodified** — they keep the existing surfaces closed and do not make the ban airtight (the scoping paragraph above is the record)

---

## Test Mapping

Sync appends the single row below to the **end of the existing table** in
`openspec/specs/coverage/spec.md`, immediately after the COV-06 TOTAL row. The
section's existing intro prose and every existing row are untouched by this
change; this row is a verify-phase **static-evidence** row by construction,
because this change adds no test.

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| COV-07 | No gate is armed for the three second-tier floors | Verify-phase **static evidence** — read of `scripts/check_core_coverage.sh` (roster = the four CLI-core modules; every `--fail-under` literal is 100), `.github/workflows/ci.yml` and `.github/workflows/release.yml` (no `--fail-under`/`fail-under`/`fail_under`), and `pyproject.toml`'s `[tool.coverage.report]` (scalar `fail_under = 90` only), pasted into the verify report; the two guards `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` and `::test_coverage_gate_is_config_driven_without_cli_floor` stay green **unmodified** — this requirement adds no test |

---

## Cross-referenced and deliberately untouched

- `coverage` COV-01..COV-06 — no clause, scenario, floor value, evidence class, or requirement ID is
  edited, renumbered, retired, or re-scoped by this delta. COV-07 is additive: it does not substitute for
  COV-01 and does not weaken COV-06.
- `coverage` COV-02 / `ci` CI-01 — the config-owned TOTAL gate stays exactly where it is
  (`[tool.coverage.report]` `fail_under = 90`, next to `show_missing = true`). COV-07 declares no
  threshold and adds no config key.
- `coverage` COV-06-S1 — the non-100 `--fail-under` ban over `scripts/check_core_coverage.sh` and the raw
  text of both workflows is the boundary this requirement records, scoping caveat included. Neither the
  ban nor the two guards pinning it is edited here.
- `process-boundary` PB-05 — the complete-suite invariant every coverage figure is taken over. The COV-07
  scenario reads committed surfaces only and runs no measurement.
- Issue **#185** — owns the release/CI asymmetry (`release.yml`'s coverage job runs the TOTAL report step
  and no core gate script). COV-07 asserts nothing about it and closes nothing.

**Non-goals recorded by this delta:** no gate is armed for the three floors (no non-100 scoped invocation,
no new script, no config key, no workflow step); no `src/sofer/**`, `tests/**`, `scripts/**`,
`.github/workflows/**`, `pyproject.toml`, or `uv.lock` line; no change to `tests/test_coverage_contract.py`
or its skip semantics; no new coverage figure, re-measurement, or margin promise; no rewording of
`AGENTS.md` rule 14 (the pointer is a separate additive bullet in this change); no edit of the
`## Purpose` enumeration (left stale deliberately, CI-07/CI-08 precedent); no `CONTRIBUTING.md` update; no
canonical `openspec/specs/**` edit before `sdd-sync`; no commit, push, or PR.
