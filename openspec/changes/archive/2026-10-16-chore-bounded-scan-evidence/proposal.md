# Proposal — `2026-10-16-chore-bounded-scan-evidence`

> **Change** `2026-10-16-chore-bounded-scan-evidence` · issue **#306** · branch
> `chore/306-bounded-quality-scan-evidence` from `dev@6786ba1` · store **hybrid**.
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

#290's fix bounded every per-row accumulator in the quality scan, and the delivered evidence was
**structural**: identical accumulator sizes after 100 and after 3 000 rows, and a `tracemalloc`-measured
~143 B per tracked duplicate row. No run reported what the fixed code costs on a large corpus, so the
issue's acceptance — "validate/prepare can now run on multi-GB datasets" — was asserted rather than
shown. #306 asks for the missing number and offers `tracemalloc` peak as an acceptable measurement
alongside sampled RSS.

## 2. Scope

### In scope

- `scripts/measure_quality_scan_rss.py`: generate a synthetic corpus, run `sofer validate` both in
  process under `tracemalloc` and as a sampled subprocess, and print peak memory and wall time for the
  default configuration and for the bounding knobs.
- `openspec/specs/data-quality/spec.md`: the declared evidence row for both #290 clauses.

### Out of scope

- Any `src/sofer/` change. This change measures; it does not alter behaviour.
- A CI job. The issue is explicit that a multi-GB run does not belong in the matrix.

## 3. Approach

One script, two passes per case, and a **sampler self-calibration** before any RSS number is printed.
The self-calibration is the load-bearing decision of this change; `design.md` §3 records why.

## 4. Success criteria

- SC-1: the script runs a real corpus end to end and reports peak memory and wall time.
- SC-2: it refuses to print a peak-RSS number it cannot justify, and says so.
- SC-3: the two configurations show what the knobs do — including if that is "nothing", for one of them.
- SC-4: the spec carries the measured numbers and the corpus shape.
- SC-5: the full gate set stays green and no `src/sofer/` file changes.
