# Proposal — `2026-10-18-fix-scan-registered-count`

> **Change** `2026-10-18-fix-scan-registered-count` · issue **#345** · branch
> `fix/345-scan-registered-count` from `dev@c68e090` · store **hybrid**
> (this folder + Engram mirror).
>
> **Status:** implementation in progress; to be archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

`registered` is part of the machine-readable envelope contract, and on every
greenfield scan it is wrong by exactly the number of placeholders `sofer_init`
wrote. The measurement is `len(merged) - len(before)`, and `before` is taken
*before* `merge_entries` strips those placeholders, so the strip is subtracted
from the result instead of from the baseline.

The envelope and the TOML written by the same call disagree: the file holds 65
entries, the envelope says 63. An agent that trusts the number concludes two
files were dropped and goes looking for them — which is what happened twice, on
two different corpora (#345 body and its first comment).

## 2. Scope

**In:** `scanner.merge_entries_counted` returning the count it already computes;
both MCP scan tools reporting that count; the CLI `scan` line
(`Registered N new [[file]] entry(s).`) and its dry-run preview reporting the
same value; the tests that pin the contract; the `scan` spec delta.

**Out:** the envelope's field set and names (no new fields, no renames); the
placeholder-strip rule itself (`TODO:` / `raw/example*` stay stripped as today);
`moved`/`copied` accounting; anything in #347 (per-call containment root), which
touches the same module but a different concern.

The CLI inclusion is a maintainer decision (2026-10-18, "sí incluir cli.py"): the
defect is one root cause with three call sites, and fixing two of them would
leave the same bug behind under a different label.

## 3. Approach

`merge_entries` already computes `added` locally (`scanner.py:471`) and throws it
away, returning only the mutated TOML dict. Twenty-odd call sites and tests
depend on that dict return, so the dict shape is not up for change.

1. `merge_entries_counted(discovered, raw_toml, base_dir, data_dir) ->
   tuple[dict, int]` becomes the implementation; it keeps the docstring, the
   dedup rule and the strip, and returns the entry count it appended.
2. `merge_entries(...)` becomes a thin wrapper returning the dict alone, so every
   existing caller and test keeps working unmodified.
3. The three counting sites — `sofer_scan_dry_run`, `sofer_scan_apply`,
   `cli._cmd_scan` — drop the before/after arithmetic and use the returned count.

The semantics the fix pins: **`registered` is the number of entries this call
appended.** A greenfield scan of N files reports N; an idempotent re-scan reports
0. The dry run and the apply agree because both read the same count.

## 4. Affected specs

- `scan` — SCN-08 gains the counting rule and one scenario (greenfield count ==
  discovered count; idempotent re-scan == 0). `scan` is a permanent
  declared-backlog spec (`openspec/test-mapping-registry.md:41`), so no
  `## Test Mapping` row is owed and the registry is not edited.

## 5. Delivery

One branch, one delivery PR against `dev`, archived inside that PR. Work-unit
commits:

1. `fix(scan): count registered entries from the merge, not the pre-strip baseline (#345)`
   — T1, T2, T3.
2. `test(scan): pin the registered count on a fresh init tree (#345)` — T4, T5.
