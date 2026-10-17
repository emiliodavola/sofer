# Tasks: chore-bounded-scan-evidence

**Change** `2026-10-16-chore-bounded-scan-evidence` (GitHub **#306**) · branch
`chore/306-bounded-quality-scan-evidence` from `dev@6786ba1` · store **hybrid**.

**Inputs read this phase, directly:** `odd/tasks/bounded-quality-scan-evidence.md` (specification of
record), `design.md` and `proposal.md` of this change, and the archived
`2026-10-14-fix-bounded-quality-scan` (`design.md` §1, `archive-report.md`) whose structural evidence
this change replaces with a measurement.

**One-line outcome:** `sofer validate` was run end to end on a 5 000 000-row corpus and its peak
memory and wall time recorded, with both bounding configurations measured and the two numbers the
run cannot claim stated instead of implied.

---

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Branch off `dev`; feature doc | — | done | `chore/306-bounded-quality-scan-evidence`; `odd/tasks/bounded-quality-scan-evidence.md` |
| T2 | Corpus generator (memory-bounded chunks, two schemas, duplicates every 17 rows) | SC-1 | done | `scripts/measure_quality_scan_rss.py::_write_csv` |
| T3 | In-process measurement under `tracemalloc`, mirroring the CLI's validate sequence | SC-1 | done | `_in_process_run`; `scripts/measure_quality_scan_rss.py --rows 5000000` |
| T4 | Subprocess measurement with an RSS sampler + **self-calibration** | SC-2 | done | `_sampler_is_trustworthy`; the run prints `UNRELIABLE` and `n/a` on this host |
| T5 | Measure both configurations (defaults and the bounding knobs) | SC-3 | done | 159.7 s / 160.1 MiB and 8.3 s / 160.1 MiB |
| T6 | Publish the numbers, the corpus shape and the two caveats in the spec | SC-4 | done | `openspec/specs/data-quality/spec.md`, "Evidence (declared, outside this spec's gate)" |
| T7 | Gates: full suite, per-file coverage, ruff/format/mypy/pyright, test-mapping checker | SC-5 | done | see the close-out |
| T8 | Work-unit commits on the branch (no push, no PR) | — | done | see the archive report |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | 2173 passed, 9 skipped |
| `cli.py` / `scanner.py` / `prepare.py` / `publish.py` 100.00% (rule 14) | 100% each |
| TOTAL floor | 94% |
| ruff / format / mypy / pyright (includes `scripts/`) | clean |
| Test-mapping contract | `OK` |
| `src/sofer/` diff | empty — this change measures, it does not alter behaviour |

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change adds no production behaviour to test:
its deliverable is a measurement and a documentary evidence row. What was verified functionally, by
running it:

- a 20 000-row smoke run (both cases exit 0), and the 5 000 000-row run recorded in `design.md` §2;
- the sampler's **negative** result, which is the load-bearing check here: it reported 5.2 MiB for a
  child holding a known 200 MiB, so the script refuses to publish an RSS figure. Confirmed
  independently with `tasklist` and by the child reading its own counters (`design.md` §3.2).
