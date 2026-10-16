# Tasks — `2026-10-16-chore-complete-bounded-scan-evidence`

> **Change** `2026-10-16-chore-complete-bounded-scan-evidence` · issue **#317** (items 1 and 2) · branch
> `fix/316-321-bug-chore-followups` from `dev@eaf56f5`.

| ID | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| SC-1 | Prove which process holds the memory, and disprove the three competing diagnoses | — | done | proposal §3: trampoline 5.2 MiB vs its child 136.6 MiB; `sys._base_executable` reads 310.5 MiB with no children; `restype`, struct layout and staleness each disproved |
| SC-2 | Verify a stdlib child-enumeration mechanism on the failing platform | D3 | done | Toolhelp32 snapshot matched `Get-CimInstance Win32_Process` exactly; `sizeof(PROCESSENTRY32)` = 304 |
| SC-3 | `_child_pids(pid)` — per-platform child enumeration, no new dependency | D3 | done | `scripts/measure_quality_scan_rss.py`; Windows path exercised by every run below |
| SC-4 | `_rss_bytes_of_tree(pid)` — bounded breadth-first sum, `None` when the root is unreadable | D1, D3 | done | 120 MiB child: root 5.2 MiB, tree 136.6 MiB |
| SC-5 | Both reader sites sample the subtree: `_peak_rss_of` and `_subprocess_run` | D2 | done | calibration `(False, 5.2 MiB)` → `(True, 216.6 MiB)`; smoke run printed 5.2 MiB before D2's second fix and 87.0 / 87.5 / 87.2 MiB after |
| SC-6 | Third case: default full-scan policy with a cap the corpus actually reaches | D5 | done | `BOUND_DUP_CAP` = 100 000 vs ≈294 000 distinct row hashes at 5 M rows; `DEFAULT_DUP_CAP` replaces the in-body `1_000_000` literal |
| SC-7 | The full 5 M row run, with a real Windows RSS figure and the cap-reached row | §4 | done | job-4, 15 m 47 s, exit 0 on every case: tracemalloc peak 160.1 MiB in all three; peak RSS 230.7 / 230.7 / 230.4 MiB |
| SC-8 | `data-quality` spec delta: the paragraph the fix falsifies, the Windows figure, the new table row | §4 | pending | |
| SC-9 | Archive report with the real numbers | — | pending | |
| SC-10 | Record item 3 as **not performed**, in the spec and in the report | §6 | pending | |
| SC-11 | Confirm the 100 000 cap actually binds at 5 M rows | D5 | pending | job-5: the `duplicates` finding must be marked partial/capped in that case, or the third case proves nothing |
| SC-12 | Identify the component that sets the 160.1 MiB peak | D5 | pending | The peak is 160.1 MiB in all three cases while the corpus is 160.0 MiB — the same near-equality the recorded run showed. Until the dominant component is named, "the cap does not move the peak" is an observation without a cause |
| SC-13 | Re-run the 5 M measurement on a host comparable to the recorded one, or state that wall times are host-specific | — | pending | job-4's wall times are ~2.5× the recorded ones (404.9 s vs 159.7 s for the same case) on the same 5 M corpus; the ~19× ratio reproduces (404.9 / 20.4 = 19.8), the absolute seconds do not |

## Explicit non-deliveries

- **Item 3, the 20 M row run: not performed.** #306 suggested 20 M rows; the maintainer chose 5 M on the
  development host and retained the script as the recipe. No host with the space and patience is available
  in this session. It is recorded as not run, never as done.
- **No `src/sofer/` change.** The script is a development recipe: not imported, not packaged, read by no
  test and no CI job. Its gates are `ruff`, `mypy` and `pyright` over `scripts/`, and the argparse help
  text, which this change does not alter.
