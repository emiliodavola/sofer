# Delta for data-quality

> **Change** `2026-10-16-chore-complete-bounded-scan-evidence` (issue **#317**, items 1 and 2) · branch
> `fix/316-321-bug-chore-followups` from `dev@eaf56f5` · store **hybrid**.
>
> **Two evidence corrections and one added case.** No `sofer` behaviour changes: #290's bounded-memory
> and full-scan-policy clauses are untouched, and what changes is the evidence block that records them,
> plus one paragraph in it that the measurement now falsifies.
>
> **Rule-6 resolution.** Unchanged from `2026-10-16-chore-bounded-scan-evidence`: `data-quality` has **no**
> `## Test Mapping` table and is a **permanent declared-backlog** entry in
> `openspec/test-mapping-registry.md`, so this delta adds no table and no registry edit. Everything below
> stays inside the existing `**Evidence (declared, outside this spec's gate):**` block.

## MODIFIED Requirements

### Requirement: End-to-end memory evidence for the bounded scan (issue #306) — the sampler correction

The evidence block SHALL NOT claim that no peak RSS can be published, and SHALL NOT attribute the
Windows sampler's failure to a silent constant independently confirmed by `tasklist`. The sampler
measures the process **subtree**, and the published figure is the tree's peak resident set.

**Removed** (the paragraph this change falsifies):

> **No peak RSS is published.** The sampler self-calibrates against a child holding a known 200 MiB
> before printing anything, and on the Windows host this was run on it reported 5.2 MiB for that child —
> a silent constant, confirmed independently with `tasklist`. Publishing that number would have
> reproduced the defect #306 exists to name, so the script prints `n/a` instead. On Linux the `/proc`
> path is calibrated the same way and yields a real figure.

**Replacing text:**

> **Peak RSS is published, and the reading it took to publish it was wrong first.** The sampler
> self-calibrates against a child holding a known 200 MiB and refuses to print a figure it cannot
> confirm. That guard has always failed on Windows — not because the platform code was wrong (checked: the
> handle is small, so no `restype` truncation; `sizeof(PROCESS_MEMORY_COUNTERS)` is 72, a correct layout;
> the counters were never stale) but because `sys.executable` in a uv-managed venv is a launcher that
> spawns the real interpreter as its **child**, so the sampler was reading an idle 5.2 MiB trampoline
> while the memory sat one hop below it. `tasklist` reporting the same 5,320 KB was therefore **not**
> independent confirmation: it was asked about the same process. The sampler now sums the process subtree
> at both reader sites, and the calibration passes on Windows for the first time.

#### Scenario: The peak RSS figure is published only after the calibration accepts the subtree reading — issue #317

- GIVEN a host where `sys.executable` spawns a real interpreter as a child process
- WHEN the sampler measures a run
- THEN it SHALL sum the resident set of the spawned process and its descendants
- AND it SHALL publish a figure only when the self-calibration accepts the subtree reading
- AND the calibration target SHALL NOT be weakened, bypassed, or special-cased per platform

#### Scenario: An unmeasured figure is not published — issue #306

- GIVEN a host whose self-calibration cannot confirm the sampler
- WHEN the script reports its measurements
- THEN it SHALL print `n/a` for the RSS column and say why
- AND it SHALL NOT print a number it could not confirm

#### Scenario: The cap's effect is measured where the cap is reached — issue #317 item 1

- GIVEN a corpus whose distinct row hashes exceed the configured `quality_max_dup_tracking`
- WHEN the script's cases are run
- THEN one case SHALL hold the **default** `quality_full_scan` policy with a cap below that count, so the
  cap is reached under the configuration a user actually runs
- AND the record SHALL state whether the peak moves when the cap binds, and what sets the peak

#### Scenario: The scale boundary is recorded, not implied — issue #317 item 3

- GIVEN #306 suggested a 20 000 000-row corpus as "N large enough to be honest"
- WHEN this change records its measurements
- THEN it SHALL state that the run was performed at 5 000 000 rows, the scale the maintainer chose on the
  development host (`2026-10-16-chore-bounded-scan-evidence` decision D4, which retained the script as the
  recipe for the larger run)
- AND it SHALL NOT present the 5 M result as evidence about 20 M

**Evidence:** `verify: end-to-end memory measurement — `scripts/measure_quality_scan_rss.py --rows 5000000`, recorded in `openspec/specs/data-quality/spec.md` §1`
