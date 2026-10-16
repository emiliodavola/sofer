# Feature: bounded-quality-scan-evidence — issue #306

**Branch:** `chore/306-bounded-quality-scan-evidence` from `dev@6786ba1`. **Issue:** `emiliodavola/sofer#306`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-chore-bounded-scan-evidence/`
(archived inside this PR, AGENTS.md rule 15). **Milestone:** v0.6.0.
**Risk:** low — no `src/sofer/` change. The risk this change carries is *evidential*: a wrong number
here would be worse than no number, which is why the sampler self-calibrates.

## Goal

#290 bounded every per-row accumulator in the quality scan. The delivered evidence was structural
(accumulator sizes after 100 and 3 000 rows; ~143 B per tracked duplicate row by `tracemalloc`), so the
issue's acceptance — "validate/prepare can now run on multi-GB datasets" — was asserted, not shown.
#306 asks for the end-to-end number.

## Specs

S1 (issue #306 §"Proposed solution" 3, verbatim): "Record peak RSS (sampling RSS at an interval, or
`tracemalloc` peak) and wall time, then repeat with `[quality] full_scan = "never"` and
`quality_max_dup_tracking` lowered, to show the knobs move the number."

S2 (issue #306 §"Proposed solution" 4, verbatim): "Publish the two numbers plus the corpus shape as a
`verify:` row in the `data-quality` spec (the spec already carries declared `verify:` evidence rows, so
no new mechanism is needed), and correct any sentence in the spec or README that the measurement
falsifies."

S3 (issue #306 §"Proposed solution" 1, verbatim): "Generate a synthetic corpus in a temp dir: one CSV
with N rows (N large enough to be honest, e.g. 20 M) and enough columns to exercise the per-row
accumulators, plus a second CSV with a different schema and a duplicated-column-label table to exercise
the card path."

**Outcome per spec:** S1 delivered. S3 delivered at 5 M rows, the scale the maintainer chose (D4) with
the recipe retained for the larger run. S2 delivered **with one correction**: `data-quality` carries no
`verify:` rows and is a permanent declared-backlog spec with no `## Test Mapping` table, so a `verify:`
line there is documentary rather than gate-counted — verified in `design.md` §5 and recorded that way in
the spec.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The RSS sampler self-calibrates against a known 200 MiB child and prints `n/a` when it fails. | The first implementation printed 5.2 MiB for every child, including one holding 300 MiB — a silent constant, confirmed with `tasklist` and by the child's own counters. Publishing it would have reproduced the defect the issue names. |
| D2 | `tracemalloc` peak is the reported memory figure, not RSS. | The issue allows either; only `tracemalloc` is reliable here. On Linux the `/proc` path is calibrated by the same guard and yields RSS. |
| D3 | The spec records that the peak does **not** move between the two configurations, with the reason. | The two peaks are identical because ~294 000 distinct hashes never reach the 1 000 000 cap; a table of two equal peaks next to a "bounded" claim reads as confirmation when it is not one. |
| D4 | The evidence lives in an `**Evidence (declared, outside this spec's gate):**` block. | `data-quality` has no Test Mapping table and the registry says none will be added, so the row is declared and non-verifiable — labelled so no reader mistakes it for gate-checked. |

## Log

L1 (user request, verbatim): "revisá los issues pendientes, chequeá que sea correcto lo que reportan y
armá un roadmap de implementación"

L2 (user request, verbatim): "dale persistilo y convertilo en un milestone en github

arrancá la implementación, llevala hasta el final para cada issue pero no hagas push y PR, eso lo
hacemos mañana"

L3 (maintainer decision D4): "5 M filas acá para el número + receta" — run at 5 M rows on this host,
keeping the script as the recipe for the larger run.

L4 (measured, contradicting the issue's premise): the issue says "the spec already carries declared
`verify:` evidence rows, so no new mechanism is needed". `grep -c "verify:"` on
`openspec/specs/data-quality/spec.md` returns **0**; `verify:` rows exist only in `ci`, `coverage` and
`process-boundary`; and `_count_verify_rows` counts only rows inside a `## Test Mapping` table of a
mapped spec, which `data-quality` is not. Recorded in `design.md` §5 and reflected in how the evidence
is labelled.

L5 (measured, a limit of the evidence): the memory figure does not move between the two configurations
(160.1 MiB both) while wall time moves 19x (159.7 s → 8.3 s). This measurement therefore does not show
the cap bounding the peak on this corpus; it shows the run completing with a bounded peak instead of the
16.1 GB climb of #290. Stated in the spec next to the numbers, not smoothed over.
