# Design — `2026-10-16-chore-complete-bounded-scan-evidence`

> **Change** `2026-10-16-chore-complete-bounded-scan-evidence` · issue **#317** (items 1 and 2) · branch
> `fix/316-321-bug-chore-followups` from `dev@eaf56f5`.
>
> **Status:** implementation complete; archived inside the delivering branch (AGENTS.md rule 15).

---

## 1. Context

`_peak_rss_of(code, seconds)` spawns the measurement child with `subprocess.Popen([sys.executable,
"-c", code])` and samples its resident set every `RSS_SAMPLE_SECONDS`. On a uv-managed Windows venv
`sys.executable` is a trampoline launcher, so `child.pid` is the trampoline and the interpreter holding
the memory is its child. The reading was correct for the process it read, which is why every
"the counters are broken" hypothesis failed (proposal §3) and why `tasklist` agreed: it was asked about
the same trampoline.

`_sampler_is_trustworthy()` compares the peak against a child holding `CALIBRATION_MIB` (200 MiB) and
refuses to publish below `CALIBRATION_MIN_RATIO` (0.5) of it, so it had always failed on Windows.

## 2. Decisions

### D1 — Sample the process subtree, not one pid

The peak resident set of a *measurement* is the footprint of everything the measurement spawned. When the
launcher is a trampoline that is two processes, and the code has no business knowing which. Summing the
subtree is correct whether or not a trampoline exists, so the fix does not encode one platform's launcher
shape into a platform-independent script.

### D2 — Fix every reader site, not just the failing one

The first implementation change fixed `_peak_rss_of` — the calibration, which is what the issue's symptom
pointed at — and left `_subprocess_run`, the path that actually **publishes** the figure, sampling
`proc.pid` directly. The 20 000-row smoke run caught it: the calibration printed `trustworthy (216.6 MiB)`
while the table still printed `peak RSS 5.2 MiB` for all three cases. Both sites now read the subtree.

This is recorded as a decision because the lesson is not "be careful": the two loops are separate code
paths with the same defect, and a fix that only satisfies the reproduction of the reported symptom is
exactly how the published number stays wrong while the guard reports success.

### D3 — Enumerate children without adding a dependency

The script's docstring commits it to stdlib only, and `pyproject.toml` must not grow a dependency for a
development recipe. Child enumeration is therefore per platform, with the smallest interface that answers
the question:

| Host | Mechanism | Verified |
| --- | --- | --- |
| Windows | `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)` + `Process32First`/`Process32Next` through `ctypes`, filtering `th32ParentProcessID` | **Yes**, this session: the snapshot's children for a spawned pid matched `Get-CimInstance Win32_Process -Filter 'ParentProcessId=<pid>'` exactly (both `[33644]`), `sizeof(PROCESSENTRY32)` = 304 |
| Linux, WSL | `/proc/<pid>/task/<pid>/children`, a space-separated pid list | No — no Linux host in this session |
| Anything else | No descendants (`[]`) | n/a — identical to the pre-change behaviour |

The Linux path cannot be verified here, and that is why D4 matters: neither path can corrupt a published
figure without the calibration noticing. If the Linux reader were wrong, the measured process would simply
be the root process — which is what the script measured there before this change — and Linux has no
trampoline to miss.

### D4 — The self-calibration stays the only arbiter

No code path publishes an RSS figure the calibration has not accepted. The fix adds no Windows-only
"trust me", does not lower `CALIBRATION_MIN_RATIO`, and does not special-case the trampoline. If the
subtree reading still fails the calibration on some host, that host still prints `n/a`, which is the
behaviour issue #317 called honest.

### D5 — A third case, not a mutated first one

Gap 1 needs a case where the cap binds. Two ways exist: more distinct rows (≈20 M rows, outside this
session) or a deliberately lowered cap under the default policy. The third case takes the second.

It is a **new** case rather than a change to the existing `defaults` case for two reasons: the recorded
table stays comparable with the numbers already in the spec, and a case named "defaults" that no longer
holds the default cap would be a lie about what it measures. `BOUND_DUP_CAP` (100 000) is below the
≈294 000 distinct row hashes the generator produces at 5 M rows, and `DEFAULT_DUP_CAP` names the shipped
1 000 000 value that was previously an in-body literal (AGENTS.md rule 1).

## 3. Alternatives rejected

| Alternative | Why not |
| --- | --- |
| Spawn the child with `sys._base_executable` | Bypasses the venv's site-packages, so the measurement child could not `import sofer` — the wrong fix for a correct reading. |
| Rewrite the `ctypes` struct / pin `OpenProcess` `restype` | Both probed and both already right (proposal §3). Changing them would have hidden the real defect behind a plausible one. |
| Delete the Windows branch and declare RSS Linux-only | Permitted by issue #317 item 2 *only* as the alternative to fixing it; the probe shows it is fixable, so deleting it would discard a working path. |
| Sum only the direct children (depth 1) | Correct for a trampoline and for nothing else. `RSS_TREE_MAX_DEPTH` (4) buys headroom for one loop. |
| Raise the cap on the existing bounded case only | It would not answer the question. The open question is whether the cap bounds the peak **under the default policy**, which is the configuration a user actually runs. |

## 4. Spec delta

`openspec/specs/data-quality/spec.md` §1 carries the paragraph this change falsifies: it declares the
absence of a Windows figure as evidence and attributes the 5.2 MiB to "a silent constant, confirmed
independently with `tasklist`". The delta corrects both halves — the figure becomes available, and the
`tasklist` cross-check is recorded as **not** independent, because it read the same process — and extends
the evidence table with the new case.

## 5. Verification

- `_sampler_is_trustworthy()` on Windows 11 / CPython 3.13.12: `(False, 5.2 MiB, 200.0 MiB)` before,
  `(True, 216.6 MiB, 200.0 MiB)` after.
- A 20 000-row smoke run: before D2's second fix the table printed `peak RSS 5.2 MiB` for all three
  cases; after it, 87.0 / 87.5 / 87.2 MiB, which is the footprint of an interpreter that imported sofer.
- The full 5 M row run, recorded in the spec's evidence table.
