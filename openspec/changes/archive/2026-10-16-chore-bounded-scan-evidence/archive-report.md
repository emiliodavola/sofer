# Archive report — `2026-10-16-chore-bounded-scan-evidence`

> **Change** `2026-10-16-chore-bounded-scan-evidence` · issue **#306** · branch
> `chore/306-bounded-quality-scan-evidence` from `dev@6786ba1` · milestone
> **v0.6.0 — agent surface & card completeness**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

A real end-to-end run of `sofer validate` on a 5 000 000-row corpus, with peak memory and wall time
recorded for both bounding configurations, and the reproducible script committed.

| Deliverable | Where |
| --- | --- |
| Measurement script (corpus generator, in-process `tracemalloc` pass, subprocess pass, self-calibrating RSS sampler) | `scripts/measure_quality_scan_rss.py` |
| The numbers, the corpus shape, and the two caveats | `openspec/specs/data-quality/spec.md`, "Evidence (declared, outside this spec's gate)" |
| Spec delta | `openspec/changes/archive/2026-10-16-chore-bounded-scan-evidence/specs/data-quality/spec.md` |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T8). No `pending` row remains.

## 3. Measured evidence

| Case | `quality_full_scan` / `quality_max_dup_tracking` | peak `tracemalloc` | wall time | exit |
| --- | --- | --- | --- | --- |
| defaults (a `fail` check forces the full scan) | `auto` / 1 000 000 | 160.1 MiB | 159.7 s | 0 |
| bounded knobs | `never` / 10 000 | 160.1 MiB | 8.3 s | 0 |

Corpus: 5 000 000 rows x 6 columns (160.0 MiB) + 50 000 rows x 3 columns (second schema), duplicate
value every 17 rows. Host: Windows 11, CPython 3.13, `--rows 5000000`.

| Gate | Result |
| --- | --- |
| Full suite | 2173 passed, 9 skipped |
| `cli.py` / `scanner.py` / `prepare.py` / `publish.py` 100.00% (rule 14) | 100% each |
| TOTAL floor | 94% |
| ruff / format / mypy / pyright (including `scripts/`) | clean |
| Test-mapping contract | `OK` |
| `src/sofer/` diff | empty |

## 4. Two negative results, stated because the evidence is weaker without them

1. **No peak RSS is published.** The sampler self-calibrates against a child holding a known 200 MiB,
   and on this host it reported 5.2 MiB — for that child, and identically for a bare interpreter and for
   a pyarrow import. `tasklist` agreed (5 308 KB) and the child reading its own counters returned 0. No
   RSS number was printed. Publishing 5.2 MiB, with two runs agreeing, would have produced evidence
   shaped like a measurement that is not one — the exact defect this issue exists to name.
2. **The memory figure does not move between the two configurations.** 160.1 MiB for both, because
   ~294 000 distinct row hashes never reach the 1 000 000 cap on this corpus. So this measurement does
   **not** demonstrate that the cap bounds the peak; it demonstrates that the run completes with a
   bounded peak instead of #290's 16.1 GB climb, and that the policy knob moves wall time by 19x. Both
   statements are in the spec next to the numbers.

## 5. Correction to the issue as written

The issue says "the spec already carries declared `verify:` evidence rows, so no new mechanism is
needed". Verified false for this spec: `grep -c "verify:" openspec/specs/data-quality/spec.md` → **0**.
`verify:` rows exist only in `ci`, `coverage` and `process-boundary`, and
`_count_verify_rows` in `scripts/check_test_mapping.py` counts only rows inside a `## Test Mapping`
table of a **mapped** spec — a table `data-quality` does not have and that
`openspec/test-mapping-registry.md` says no sweep will add. The evidence row is therefore documentary,
labelled `**Evidence (declared, outside this spec's gate):**`, and the archive states that plainly.

## 6. Scale deviation

The issue suggested 20 M rows "large enough to be honest". The maintainer chose 5 M rows on this host
with the script retained as the recipe (decision D4). 5 M rows is recorded as the measured scale; the
0.5 GB-plus run remains one command away and is not claimed as done.

## 7. Follow-ups this change creates

- **A corpus with more distinct rows** (or a lowered cap in the default case) is needed to show the cap
  moving the peak. Named in `design.md` §3.1.
- **An RSS figure on Linux**, where the `/proc` path is calibrated by the same guard. Named in
  `design.md` §3.2.
