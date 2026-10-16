# Design — `2026-10-16-chore-bounded-scan-evidence`

> **Change** `2026-10-16-chore-bounded-scan-evidence` (issue **#306**) · branch
> `chore/306-bounded-quality-scan-evidence` from `dev@6786ba1` · store **hybrid**.

---

## 1. The gap, precisely

`openspec/specs/data-quality/spec.md` asserted, for #290:

> per-row memory SHALL be independent of the dataset size

Its evidence was `test: ...test_memory_is_o_columns_not_o_rows` and
`test: ...test_tracking_dict_never_exceeds_the_cap` — structural assertions about the shape of two
accumulators. The `tracemalloc` figure the issue cites (~143 B per tracked row at a 1 M cap ≈ 137 MB)
is arithmetic on top of that, not a run. Nothing reported the cost of the *combination* while
streaming 5 M rows through the single pass.

## 2. What was measured

| Case | `quality_full_scan` / `quality_max_dup_tracking` | peak `tracemalloc` | wall time | exit |
| --- | --- | --- | --- | --- |
| defaults (a `fail` check forces the full scan) | `auto` / 1 000 000 | 160.1 MiB | 159.7 s | 0 |
| bounded knobs | `never` / 10 000 | 160.1 MiB | 8.3 s | 0 |

Corpus: 5 000 000 rows x 6 columns (160.0 MiB) plus a 50 000-row second schema, duplicate value every
17 rows. Host: Windows 11, CPython 3.13.

Both runs completed. The issue's acceptance — `validate` finishes on a multi-million-row corpus with
memory that does not climb — is shown: the reported 16.1 GB RSS climb of #290 does not reproduce, and
the peak this corpus reaches is 160 MiB.

## 3. Two findings that change what the evidence can claim

### 3.1 The policy knob moves wall time by ~19x and peak allocation by nothing

159.7 s → 8.3 s is a real, reproducible 19x, and it is the number that answers "can this run at all".
The memory numbers are **identical to 0.1 MiB**, and that is not a rounding artifact of the method: on
this corpus the peak is dominated by a component other than the capped hash table — ~294 000 distinct
row hashes against a 1 000 000 cap, so the default case never reaches the cap at all. A corpus with more
distinct rows, or a deliberately lowered cap in the *default* case, would be needed to show the cap
moving the peak. That is recorded in the spec next to the numbers rather than left for a reader to
notice, because a table showing two identical peaks next to a "this is bounded" claim reads as
confirmation when it is not one.

### 3.2 The RSS sampler cannot be trusted, and refuses to be

The first implementation sampled the child's resident set through `ctypes` + `GetProcessMemoryInfo`
and printed a peak RSS for both cases. It was wrong: **5.2 MiB for a child that had touched a 300 MiB
allocation**, and 5.2 MiB again for a bare interpreter and for a pyarrow import — a silent constant.
`tasklist` agreed (5 308 KB), and the child reading its own counters returned **0**. Two different
self-consistent-looking numbers, neither usable.

Publishing 5.2 MiB — a plausible-looking figure, with two runs agreeing — would have reproduced exactly
the defect #306 exists to name: evidence shaped like a measurement that is not one. The sampler now
self-calibrates first: it runs a child holding a known 200 MiB and refuses to print any RSS figure
unless the sampler reports at least half of it. On the Windows host it refuses, and the script prints
`n/a` with the reason. On Linux the `/proc` path is calibrated by the same guard, so the same command
yields a real figure there.

This is why the delivered evidence is `tracemalloc` peak (stdlib, always available, explicitly allowed
by the issue) rather than RSS.

## 4. Edits

- `scripts/measure_quality_scan_rss.py` (new). Corpus generation in memory-bounded chunks; an
  in-process pass under `tracemalloc` that mirrors the CLI's own validate sequence
  (`DatasetConfig.from_toml` → `DatasetValidator.run_all` → `QualityValidator.run`) with
  `config.reload(start=corpus)` so the case's `[tool.sofer]` values apply; a subprocess pass through
  `python -m sofer.cli validate`; the sampler and its calibration.
- `openspec/specs/data-quality/spec.md`: a declared-evidence block under the two #290 clauses, carrying
  the table above.

## 5. Where this evidence sits relative to the gate — stated because the issue gets it wrong

The issue says "the spec already carries declared `verify:` evidence rows, so no new mechanism is
needed". **It does not.** Verified: `grep -c "verify:" openspec/specs/data-quality/spec.md` → 0, and
`verify:` rows exist only in `ci`, `coverage` and `process-boundary`. Worse, `_count_verify_rows` in
`scripts/check_test_mapping.py` counts only data rows inside a **`## Test Mapping` table of a mapped
spec**, and `data-quality` is a permanent declared-backlog entry in
`openspec/test-mapping-registry.md` (no Test Mapping table, and the registry says explicitly that no
sweep will add one). So a `verify:` line here is **not** gate-counted, and the evidence is documentary:
declared, non-verifiable, owner the repository maintainer. It is written as `verify: end-to-end memory
measurement, scripts/measure_quality_scan_rss.py --rows 5000000` inside an `**Evidence (declared,
outside this spec's gate):**` block so a future reader cannot mistake it for a gate-checked reference.

## 6. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A reader takes the 160.1 MiB figure as proof the cap bounds memory. | **Med** | The spec text says the opposite in the same block: the peak does not move, and why. |
| R2 | The synthetic corpus is not representative of the reported 3.2 GB corpus. | **Med** | Stated with the numbers: shape, size and duplicate density are printed by the script and recorded in the spec. |
| R3 | The measurement is not reproducible on another host. | Low | The script is committed and every input is a flag with a default; only the RSS figure is platform-dependent, and it sa
