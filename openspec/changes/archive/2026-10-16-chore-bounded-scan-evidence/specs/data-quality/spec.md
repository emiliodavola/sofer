# Delta for data-quality

> **Change** `2026-10-16-chore-bounded-scan-evidence` (issue **#306**) · branch
> `chore/306-bounded-quality-scan-evidence` from `dev@6786ba1` · store **hybrid**.
>
> **One added evidence block.** No clause changes: #290's bounded-memory and full-scan-policy clauses
> are unchanged. What changes is their evidence — a real end-to-end run replaces the structural
> argument.
>
> **Rule-6 resolution.** `data-quality` has **no** `## Test Mapping` table and is a **permanent
> declared-backlog** entry in `openspec/test-mapping-registry.md`, so this change adds no table and no
> registry edit. The new row is written as a `verify:` reference inside an
> `**Evidence (declared, outside this spec's gate):**` block, next to the `test:` rows it complements,
> so a reader cannot mistake it for a gate-checked reference. It is declared and non-verifiable; owner,
> the repository maintainer.

## ADDED Requirements

### Requirement: End-to-end memory evidence for the bounded scan (issue #306)

The `Bounded per-row memory (issue #290)` and `Explicit full-scan policy (issue #290)` clauses SHALL
carry declared end-to-end evidence from a real run of `sofer validate` on a multi-million-row corpus, in
addition to the structural unit tests, because those clauses' acceptance — that validate/prepare can
run on multi-GB datasets — cannot be shown by the shape of an accumulator.

The evidence SHALL name the corpus shape, both bounding configurations, the peak memory and the wall
time, and SHALL state what the measurement does **not** show.

#### Scenario: The measurement and its limits are recorded — issue #306

- GIVEN `scripts/measure_quality_scan_rss.py --rows 5000000`
- WHEN its output is recorded as spec evidence
- THEN the record SHALL name the corpus shape, both `quality_full_scan` / `quality_max_dup_tracking`
  configurations, the peak memory and the wall time for each
- AND it SHALL state that the peak does not move between the configurations on this corpus, and why

**Evidence:** `verify: end-to-end memory measurement — `scripts/measure_quality_scan_rss.py --rows 5000000`, recorded in `openspec/specs/data-quality/spec.md` §1`

#### Scenario: An unmeasured figure is not published — issue #306

- GIVEN a host where the resident-set sampler cannot see a child's real footprint
- WHEN the measurement runs
- THEN no peak-RSS figure SHALL be printed
- AND the output SHALL name the failed self-calibration instead

**Evidence:** `verify: sampler self-calibration — `scripts/measure_quality_scan_rss.py`, `_sampler_is_trustworthy()`, observed reporting `UNRELIABLE` and `n/a` on Windows 11 / CPython 3.13`
