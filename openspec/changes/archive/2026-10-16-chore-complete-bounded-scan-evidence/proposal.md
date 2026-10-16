# Proposal — `2026-10-16-chore-complete-bounded-scan-evidence`

> **Change** `2026-10-16-chore-complete-bounded-scan-evidence` · issue **#317** (items 1 and 2) · branch
> `fix/316-321-bug-chore-followups` from `dev@eaf56f5` · store **hybrid**
> (`odd/tasks/bug-chore-followups.md` + this folder).
>
> **Status:** proposal accepted from the maintainer's instruction; implementation in progress.
> Archived inside the delivering PR (AGENTS.md rule 15).

---

## 1. Intent

`chore-bounded-scan-evidence` (PR #315) delivered the end-to-end measurement #306 asked for and recorded,
in its own archive report and in the spec, three things it could not claim. Issue #317 files those three.
This change closes the two that are work; the third is a boundary and is recorded rather than performed.

## 2. Gap 1 — the peak does not move, so the cap's effect is undemonstrated

The recorded run measured two configurations:

| Case | `quality_full_scan` / `quality_max_dup_tracking` | peak `tracemalloc` | wall time |
| --- | --- | --- | --- |
| defaults | `auto` / 1 000 000 | 160.1 MiB | 159.7 s |
| bounded knobs | `never` / 10 000 | 160.1 MiB | 8.3 s |

The two peaks are identical because the cap never binds on that corpus. The generator writes one
distinct row per bucket of `DUPLICATE_EVERY` (17) rows, so 5 000 000 rows carry ≈294 000 distinct row
hashes — well under the shipped 1 000 000 cap. The measurement therefore shows a bounded peak, not that
the cap bounds anything.

**Fix:** a third case holds the *default* full-scan policy and a cap below the distinct-row-hash count
(`BOUND_DUP_CAP` = 100 000), so the cap is actually reached and the two default-policy peaks become
comparable. The first and third cases are deliberately left byte-identical to the recorded run, so their
numbers stay comparable with the table already in the spec.

## 3. Gap 2 — no RSS figure can be published, and the recorded diagnosis is wrong

The sampler self-calibrates against a child holding a known 200 MiB and refuses to publish below half of
it. On Windows it reported 5.2 MiB for that child, the calibration failed, and the table printed `n/a`.

Issue #317 offered two honest outcomes: fix the reading, or remove the Windows branch. The probe below
shows it is the first, and that neither the `ctypes` reading nor the branch is at fault.

`.venv\Scripts\python.exe` in a uv-managed venv on Windows is a **trampoline launcher**: it spawns the real
interpreter as a child. `_peak_rss_of` sampled `child.pid`, so it sampled the trampoline.

```text
$ uv run python -c "... _sampler_is_trustworthy() ..."
platform: Windows 11 3.13.12
trustworthy: False
reported: 5447680 = 5.2 MiB      # what _rss_bytes reads
expected: 209715200 = 200.0 MiB  # what the calibration child holds

$ Get-CimInstance Win32_Process -Filter 'ParentProcessId=<sampled pid>'
children: ['26188']
WorkingSet(trampoline)  =   5.2 MiB
WorkingSet(interpreter) = 136.6 MiB     # the same probe, 120 MiB child
$ same probe spawning sys._base_executable directly
WorkingSet = 310.5 MiB   (no children)
```

Three competing diagnoses were disproved before the pid one was accepted, which is why the fix belongs in
the pid selection and not in the platform code:

| Hypothesis | Verdict |
| --- | --- |
| `OpenProcess` `restype` truncates a 64-bit handle | **No.** The handle is `0x1b0`; pinning `argtypes`/`restype` yields the identical value. |
| The `PROCESS_MEMORY_COUNTERS` struct layout is wrong | **No.** `sizeof` is 72 and every field moves as the child's own counters do. |
| The counters go stale after the first read | **No.** They were constant because the trampoline is genuinely idle — the reading was true of the process being read. |

`tasklist` agreeing with `ctypes` at 5,320 KB is therefore **not** independent confirmation, which is what
`openspec/specs/data-quality/spec.md` §1 currently assumes. It is two readings of the same trampoline.

## 4. Why this is a spec change, not an ad-hoc fix

`openspec/specs/data-quality/spec.md` §1 does not merely omit the Windows number, it **declares** the
omission as evidence:

> **No peak RSS is published.** The sampler self-calibrates against a child holding a known 200 MiB
> before printing anything, and on the Windows host this was run on it reported 5.2 MiB for that child —
> a silent constant, confirmed independently with `tasklist`. Publishing that number would have
> reproduced the defect #306 exists to name, so the script prints `n/a` instead. On Linux the `/proc`
> path is calibrated the same way and yields a real figure.

Publishing a real Windows figure falsifies that paragraph, so this change carries a `data-quality` spec
delta, exactly as `2026-10-16-chore-bounded-scan-evidence` did for the paragraph it added.

## 5. Scope

- `scripts/measure_quality_scan_rss.py`: sample the **process subtree** at both reader sites
  (`_peak_rss_of`, the calibration, and `_subprocess_run`, the published figure); add the third case and
  name the shipped cap as a constant instead of an in-body literal.
- `openspec/specs/data-quality/spec.md` §1: correct the claim, record the Windows figure, and add the
  cap-reached row.

## 6. Non-goals

- **Not** switching the measurement child to `sys._base_executable`: it bypasses the venv's
  site-packages and would break the child's `sofer` import — the wrong fix for a correct reading.
- **Not** removing the Windows branch: the probe shows the platform path works.
- **Not** lowering `CALIBRATION_MIN_RATIO` or adding a Windows-only bypass. The calibration stays the
  only arbiter of whether a figure may be published.
- **Item 3 (the 20 M row run) is not performed.** #306 suggested 20 M rows; the maintainer chose 5 M on
  the development host and the recipe was retained. No host with the space and patience is available in
  this session, so 5 M is what is claimed and 20 M is recorded as not run.
- No `src/sofer/` change: the script is a development recipe, is not imported or packaged, and no CI job
  or test reads it.
