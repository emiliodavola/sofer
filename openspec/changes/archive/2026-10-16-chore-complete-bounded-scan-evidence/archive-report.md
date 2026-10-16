# Archive report — `2026-10-16-chore-complete-bounded-scan-evidence`

> **Change** `2026-10-16-chore-complete-bounded-scan-evidence` · issue **#317** (items 1 and 2) · branch
> `fix/316-321-bug-chore-followups` from `dev@eaf56f5`.
>
> **Status:** implementation complete; archived inside the delivering PR (AGENTS.md rule 15).
> Item 3 is recorded as **not performed**, never as done.

---

## 1. What landed

| File | Change |
| --- | --- |
| `scripts/measure_quality_scan_rss.py` | `_child_pids` (per-platform child enumeration) and `_rss_bytes_of_tree` (bounded subtree sum); both reader sites — `_peak_rss_of` and `_subprocess_run` — sample the subtree; a third case (`BOUND_DUP_CAP` = 100 000, default policy); `DEFAULT_DUP_CAP` replaces an in-body `1_000_000` literal |
| `openspec/specs/data-quality/spec.md` §1 | the sampler paragraph corrected, the evidence table extended, the "bounded, non-growing memory" sentence replaced by what the measurement actually shows, and the 20 M boundary stated |
| `openspec/changes/archive/2026-10-16-chore-complete-bounded-scan-evidence/` | proposal, design, tasks, this report, and the `data-quality` delta (archived inside the delivering PR, AGENTS.md rule 15) |

No `src/sofer/` change. The script is a development recipe: not imported, not packaged, read by no test and
no CI job.

## 2. The sampler defect and its fix

`.venv\Scripts\python.exe` in a uv-managed venv on Windows is a trampoline launcher that spawns the real
interpreter as a child, so the sampler read an idle launcher while the memory sat one hop below it.

| Probe | Before | After |
| --- | --- | --- |
| `_sampler_is_trustworthy()` on Windows 11 / CPython 3.13.12 | `(False, 5.2 MiB, 200.0 MiB)` | `(True, 216.6 MiB, 200.0 MiB)` |
| 120 MiB child: root reading | 5.2 MiB | 5.2 MiB (unchanged, and correct for that process) |
| 120 MiB child: subtree reading | — | 136.6 MiB |
| 20 000-row smoke run, `peak RSS` column | 5.2 MiB in all three cases | 87.0 / 87.5 / 87.2 MiB |

Three competing diagnoses were disproved before the pid one was accepted, and they are recorded because
disproving them is what kept the fix out of the platform code: the `OpenProcess` handle is `0x1b0` (so no
`restype` truncation), `sizeof(PROCESS_MEMORY_COUNTERS)` is 72 (a correct layout), and the counters were
never stale — they were a true reading of an idle process. `tasklist` agreeing at 5,320 KB was therefore
**not** independent confirmation.

**Two sites, not one.** The first fix changed `_peak_rss_of` — the calibration, which is what the
reproduction exercises — and left `_subprocess_run`, the path that publishes the figure, sampling a pid.
The calibration printed `trustworthy (216.6 MiB)` while the table still printed `5.2 MiB`. Only the smoke
run caught it. A test that satisfies the reported reproduction is not a test that satisfies the defect.

## 3. The cap, reached, and not the binding constraint

The recorded #306 run could not distinguish "the cap does not matter" from "the cap was never reached":
5 000 000 rows carry ≈294 000 distinct row hashes (one distinct row per bucket of 17), under the shipped
1 000 000 cap, and the `never` case samples the pass so its table never filled either.

The 5 M run (exit 0 on every case):

| Case | `quality_full_scan` / `quality_max_dup_tracking` | peak `tracemalloc` | wall time | peak RSS |
| --- | --- | --- | --- | --- |
| defaults | `auto` / 1 000 000 | 160.1 MiB | 404.9 s | 230.7 MiB |
| default policy, cap reached | `auto` / 100 000 | 160.1 MiB | 409.0 s | 230.7 MiB |
| bounded knobs | `never` / 10 000 | 160.1 MiB | 20.4 s | 230.4 MiB |

The cap is really reached in the middle case — the `duplicates` finding reads
`partial — tracking capped at 100000 distinct rows`, while at 1 000 000 it does not — and the peak does not
move across a **100× range of cap**. The policy knob moves wall time ~19× (404.9 / 20.4 = 19.8). Absolute
seconds are host-specific: this host is ~2.5× slower than the one behind the recorded table (404.9 s vs
159.7 s for the same case and corpus), so the ratio transfers and the seconds do not.

## 4. The finding this change forced, and did not fix

The peak is ≈1× the corpus size, so it is **not** independent of the dataset size:

| Corpus | CSV size | peak `tracemalloc` | peak / CSV |
| --- | --- | --- | --- |
| 1 000 000 rows | 31.2 MiB | 44.0 MiB | 1.41 |
| 2 000 000 rows | 63.4 MiB | 63.4 MiB | 1.00 |
| 5 000 000 rows | 160.0 MiB | 160.1 MiB | 1.00 |

Attribution: on a 1 M-row / 31.2 MiB corpus, `DatasetValidator.run_all()` peaks at **0.0 MiB** and
`QualityValidator.run()` at **44.0 MiB**, and a `tracemalloc` snapshot taken after the pass retains almost
nothing — the spike is **transient**, not accumulating state.

This falsifies the sentence `openspec/specs/data-quality/spec.md` §1 carried ("`sofer validate` completes on
a multi-million-row corpus with bounded, non-growing memory"), which this change corrects. #290's fix is
real — it removed the pre-fix 16.1 GB climb — but it did not make memory size-independent, so a corpus of N
bytes should be assumed to need on the order of N bytes of RAM until the allocator is identified. That
identification is a `src/sofer/` change with data-path consequences: **proposed as its own issue, not fixed
here.**

## 5. What this change does NOT claim

- **The 20 M row scale was not run.** #306 suggested it; the maintainer chose 5 M on the development host
  and retained the script as the recipe (`2026-10-16-chore-bounded-scan-evidence` D4). Nothing here is
  evidence about 20 M.
- **The Linux child-enumeration path is unverified.** `/proc/<pid>/task/<pid>/children` is the documented
  interface and is the smallest reader that answers the question, but no Linux host was available. The
  Windows path was verified against `Get-CimInstance Win32_Process` (identical children, `sizeof` = 304).
  An unverified path cannot corrupt a published figure: if it returned nothing, the measured process would
  be the root — which is what the script measured on Linux before this change — and Linux has no
  trampoline to miss.
- **The peak's allocator is unidentified.** §4 says where and how big, not what.
- **`CALIBRATION_MIN_RATIO` was not lowered and no platform bypass was added.** The calibration remains the
  only arbiter of whether a figure may be published: a host it cannot confirm still prints `n/a`.

## 6. Task ledger

| ID | State | Evidence |
| --- | --- | --- |
| SC-1 | done | proposal §3; the three disproved diagnoses |
| SC-2 | done | Toolhelp32 vs `Get-CimInstance Win32_Process` |
| SC-3, SC-4, SC-5 | done | §2 table; smoke run caught the second reader site |
| SC-6 | done | `BOUND_DUP_CAP` = 100 000 under ≈294 000 distinct hashes |
| SC-7 | done | §3 table (job-4, 15 m 47 s, exit 0) |
| SC-8 | done | `openspec/specs/data-quality/spec.md` §1 + the delta in this folder |
| SC-9 | done | this report |
| SC-10 | done | §5, first bullet; stated in the merged spec too |
| SC-11 | done | `partial — tracking capped at 100000 distinct rows` at 100 000, absent at 1 000 000 |
| SC-12 | done with a finding | §4; attribution to the quality pass, fix deferred to its own issue |
| SC-13 | done | host-specific wall times stated in the spec and in §3 |

## 7. Verification gates

| Gate | Command | Result |
| --- | --- | --- |
| Lint and format | `uv run ruff check scripts/measure_quality_scan_rss.py` | pass |
| Types | `uv run mypy src/ scripts/` | `Success: no issues found in 38 source files` |
| Types | `uv run pyright` | `0 errors, 1 warning` — the pre-existing `_tomli.py` `reportMissingModuleSource` |
| Full suite | `uv run pytest tests/ -q` | `2233 passed, 9 skipped` |
| Spec revision | `uv run pytest tests/test_test_mapping_checker.py tests/test_ci_workflows.py -q` | `79 passed` after the final prose edit to the merged spec, and `scripts/check_test_mapping.py` still reports `OK: test-mapping contract holds`, with `data-quality: 1 scenario(s), unmapped` unchanged |
| End-to-end | `uv run python scripts/measure_quality_scan_rss.py --rows 5000000` | §3; exit 0 in every case |
| End-to-end (smoke) | `uv run python scripts/measure_quality_scan_rss.py --rows 20000` | §2; this is the run that caught the second reader site |

The suite was run once on the change (job-9, `2233 passed / 9 skipped`) and the spec-reading tests were re-run after the last prose edit, because that edit landed after the suite had started. Nothing else in the tree changed between the two.
