# Feature: bug-chore-followups — issues #316, #317, #318, #319, #321

**Branch:** `fix/316-321-bug-chore-followups` from `dev@eaf56f5`. **Issues:** `emiliodavola/sofer#316`,
`#317`, `#318`, `#319`, `#321`. **Delivery PR:** (pending — user decision) → `dev`.
**Milestone:** v0.7.0 — follow-up defects from the v0.6.0 batch. **Store:** hybrid
(`odd/tasks/bug-chore-followups.md` + `openspec/changes/<date>-<type>-<name>/` per issue that carries a
spec delta, archived inside the delivering PR per AGENTS.md rule 15).
**Risk:** item 3 for #316 and #321 (both change a warning/registration surface that other code and tests
consume — requested changes, so not high); item 6 for #317.2 (no test covers the sampler today); none for
#318 and #319.

## Goal

The v0.6.0 milestone ([`odd/ROADMAP.md`](../ROADMAP.md)) delivered #287, #288, #291, #296, #303 and #306
and filed nine follow-ups the day it closed. Five of them are `type:bug` / `type:chore`: one live
user-visible defect (#316) and four chores whose remaining work is a decision, a one-line report change,
a docs pointer and a measurement recipe.

This batch closes the five, resolves the #320/#321 overlap, and records which open issues are *not*
worth keeping.

## Verified state — every claim checked against the code, not the issue text

`dev@eaf56f5`, working tree clean, no open PRs, no open `openspec/changes/`.

| Issue | Claim | Verdict | Evidence |
| --- | --- | --- | --- |
| #316 | 3 warnings for 2 files | **reproduces** | `validate_split_mapping(["data/a.parquet","data/b.parquet"])` → 3 entries; summary at `splits.py:376-390`, per-file loop at `:392-411` fires for every file whose split carries no keyword anywhere |
| #317.1 | the two configs' peaks are identical | **reproduces** | `quality_max_dup_tracking` default `1_000_000` (`config.py:80`, `pyproject.toml:225`) never binds on ~294 000 distinct row hashes |
| #317.2 | "the Windows branch is effectively dead, two numbers neither usable" | **wrong diagnosis** | see `## Root cause` below — the branch is correct, the *pid* is wrong |
| #317.3 | the 20 M row scale was not run | **reproduces** | `--rows` default `5_000_000` (`scripts/measure_quality_scan_rss.py:420`) |
| #318 | README lists 3 of ~25 `[meta]` keys | **reproduces** | `README.md:190-193`; `language`, `pretty_name`, `task_categories`, `size_categories`, `citation`, `collection_method`, `direct_use`, `contact` → 0 mentions; `DatasetConfig` carries 26 card/meta fields (`model.py:305-312`, `:327-345`) |
| #319 | the `verify:` count cannot include the backlogged specs | **reproduces** | `_count_verify_rows` skips `record.table is None` (`check_test_mapping.py:591-611`); report prints 65; registry holds 17 rows |
| #319 | "`data-quality` carries no `verify:` rows" | **stale** | `openspec/specs/data-quality/spec.md:47` carries one, added by PR #315 |
| #321 | codex/gemini delegation declines by default | **reproduces** | `native_timeout: False` on every adapter; `native_delegation_decline_reasons` appends `"timeout"` when `timeouts is not None` (`mcp_registration.py:864`); `tests/test_cli.py:3215` pins it |
| #322, #323, #324 (features, out of scope) | premises | **all still true** | no `doctor` subcommand (`cli.py` `add_parser` list); no `sofer_meta_set`/`sofer_meta_check`; no `curation_rationale` key |

### Root cause of #317.2 — found, and it is not ctypes

`_peak_rss_of` samples `child.pid`. In this uv-managed venv `.venv\Scripts\python.exe` is a **trampoline
launcher**: it spawns the real interpreter as a *child*, so `child.pid` is the trampoline. Measured on
Windows 11 / CPython 3.13.12:

```text
$ Get-CimInstance Win32_Process -Filter 'ParentProcessId=<sampled pid>'   # one child
WorkingSet(trampoline) =   5.2 MiB      # what _rss_bytes reads
WorkingSet(interpreter) = 311.4 MiB     # what it should read
--- same probe spawning sys._base_executable directly ---
WorkingSet = 310.5 MiB                  # no child
```

The ctypes path is *correct*: the handle is small (`0x1b0`, so no `restype` truncation), the struct
`sizeof` is 72 (a correct `PROCESS_MEMORY_COUNTERS`), and `tasklist` agrees with it — all three measure
the same idle trampoline. The constant 5.2 MiB is a real reading of a real process, which is why the
self-calibration correctly refuses to publish it. **The fix is to sample the process subtree; it must NOT
switch to `sys._base_executable`, which would bypass the venv's site-packages and break the measurement
child's `sofer` import.**

## Specs

S1 (user, verbatim, the original request): "revisá los issues de tipo bug y chore y armate un plan de
implmentación, no confies en los bodies de los issues, chequealos"

S2 (user, verbatim, the authorization): "bien arrancá con #316, luego los chores, también resolvé esto que
mencionás del solapamiento y cerrá los issues que no tengan sentido si hay alguno"

S3 (issue #316 §"Proposed solution", verbatim): "Suppress the per-file message when that file's split has
**no** keyword in any of its files — the summary already covers it — and keep it for the mixed case it
exists for (some files in the split carry a keyword, this one does not). One predicate on the split's file
set, no new message."

S4 (issue #317 §"Proposed solution" 1, verbatim): "**A corpus that exercises the cap:** more distinct rows
(or a deliberately lowered cap in the *default* case) so the two peaks differ, and record whether the
default case then climbs."

S5 (issue #317 §"Proposed solution" 2, verbatim): "**A real Windows RSS path, or drop it honestly:**
either fix the `ctypes` reading (a debug print of every struct field on a child of known size is the first
step) or remove the Windows branch and state that RSS is Linux-only, so the script stops advertising a
capability it does not have."

S6 (issue #317 §"Proposed solution" 3, verbatim): "**The larger run**, when a host with the space and
patience is available; it changes no code."

S7 (issue #318 §"Proposed solution" 1, verbatim): "**Point, do not duplicate:** one line next to the
`[meta]` example naming the spec section as the full list, with the sentence "every `[meta]` key the card
reads is listed in `openspec/specs/repo-compliance/spec.md` §2.1.1". No second copy, no drift,
discoverable."

S8 (issue #319 §"Proposed solution", verbatim): "Either: 1. **Count them too:** a second counter over the
backlogged specs' inline `**Evidence:**` lines (e.g. `backlog-verify: N declared rows, not gated`), so the
printed size covers the whole tree and the difference between the two numbers is explicit. 2. **Say it in
the report:** one clause on the existing line stating that the count covers mapped specs only, so a reader
does not take 65 for the tree's total. Cheapest, and honest."

S9 (`openspec/specs/process-boundary/spec.md` PB-15, verbatim): "The checker `scripts/check_test_mapping.py`
SHALL state the same policy in its module docstring and SHALL report, on every run, the number of
`verify:` rows it accepted as declared evidence, labelled non-verifiable and naming the owner and review
trigger."

S10 (issue #321 §"Proposed solution" 1, verbatim): "**Delegate, then patch the timeouts.** Let the native
CLI write the entry, then add the timeout keys to the `sofer` entry in the same file (the merge/atomic-write
helpers already exist). One command, two writers in sequence, delegation preserved."

S11 (issue #321 §"Proposed solution" 3, verbatim): "**Keep the decline** and make `--no-timeout` louder: it
is currently documented in one help line and one README row, and it now carries more weight than it did."

S12 (issue #321, the blocker discovered while verifying this batch, not in the issue): the code's own
comment at `mcp_registration.py:127` states that codex's native commands "always act on the global
`$CODEX_HOME` config", while the codex adapter declares `user_env_dir: None` and resolves
`Path.home()/".codex"/"config.toml"`. S10 is therefore unsafe until the two resolutions agree.

## Decisions not in the issues

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | #316 ships as an **ad-hoc fix**, no `openspec/changes/` folder. | Its requirement `S4` and the scenario at `spec.md:1616` constrain only the **summary** warning, which the fix leaves byte-identical. The per-file message is not a spec'd clause, so suppressing it changes no contract of record. Verified by `grep -rn "detectable split keyword" openspec/specs/` → 0 hits. |
| D2 | #319 takes **option 2 of S8** — one clause stating what the count covers — and **not** option 1's second counter. | S9 pins that the checker reports "the number of `verify:` rows it **accepted**". Measured: the 17 backlogged specs carry **1** `verify:` line in the whole tree (`openspec/specs/data-quality/spec.md:47`) and have no row syntax at all, so a second counter would be ceremony over a population of one and would print a number that means something different from "accepted". Stating the exclusion removes the false impression that 65 is the tree's total, with no new syntax and no new semantics. **This corrects this document's first reading of the decision, which chose both halves** — the measurement is what settled it. |
| D3 | #317.2 is fixed by sampling the **subtree**, not by dropping the Windows branch. | S5 offers "fix it or drop it honestly"; the probe above proves it is fixable, so the honest branch is the one that publishes a real Windows number. Because `openspec/specs/data-quality/spec.md` §1 records the Windows `n/a` and the "silent constant" diagnosis as **declared evidence**, this fix is a spec change and carries its own `openspec/changes/` folder. |
| D4 | #321 is **not** delivered in this batch. | S10 reverses a spec'd requirement (MCP-REG-05 "Native delegation declines when it cannot reproduce the timeouts") and decision D4 of `2026-10-16-fix-mcp-registration-timeouts/design.md`, taken by the maintainer two days earlier — and S12 adds a prerequisite the issue did not know about. That is a product decision, not an implementation step. Filed back as a decision. |

## Non-goals

- #320, #322, #323, #324 — `type:feature`, outside the bug/chore scope of S1/S2.
- Push, PR creation and merge — user decisions.
- The 20 M row run of S6: no host with the space and patience is available in this session. Recorded as
  not performed, never as done.

## #320 / #321 — the overlap, resolved (T8)

The two issues are **not duplicates**, and neither closes the other. Both are about a `timeout` key in the
registration entry, which is the whole of their overlap:

- **#321 (codex, gemini).** The host's config schema accepts the key and sofer's file edit already writes
  it; what cannot express it is the host's own `mcp add` CLI. Delegation declines so the entry keeps the
  deadlines it exists for.
- **#320 (opencode).** There is no usable key to write: opencode's pinned zod schema declares `timeout`
  as a scalar while its current docs declare an object, and writing the wrong one can fail validation of
  the entire `mcp` block. opencode also never delegates (`delegates: False`).

So the issue-1 remedy of #321 ("delegate natively, then patch the timeout keys into the same file") helps
codex and gemini and does **nothing** for opencode, because opencode has no delegation step to preserve.
What they share is a *mechanism*, not a defect: both need to write timeout keys into an entry somebody
else just wrote. Resolution: keep both open, and if #321's option 1 is chosen, build it as a small
shape-aware helper that #320 can extend to the nested opencode shape, so the second host does not grow a
second mechanism.

### The prerequisite #321 did not know about

`mcp_registration.py:127` states that codex's native commands "always act on the global `$CODEX_HOME`
config", but the codex adapter declares `user_env_dir: None` and resolves `Path.home()/".codex"/config.toml`.
With `$CODEX_HOME` set, the issue's option 1 would delegate to the native CLI (which writes
`$CODEX_HOME/config.toml`) and then patch `~/.codex/config.toml` — **the #274 defect class, still live for
codex**. Option 1 is therefore gated on giving the codex adapter `user_env_dir = "CODEX_HOME"`, which is a
second, independent bug that this batch discovered and did not fix.

## Issue hygiene (T9)

Every one of the nine open issues was re-verified against `dev@eaf56f5`. **None is a duplicate, none is
inert, and none has a premise that has stopped being true**, so none was closed:

| Issue | Verdict | Why it stays open |
| --- | --- | --- |
| #316 | live defect | fixed by T1 |
| #317 | live | items 1 and 2 are defects; item 3 is a boundary, not a defect |
| #318 | live | 8 of the 26 card keys have 0 mentions in the README |
| #319 | live | the reported hatch size excludes a whole class of specs |
| #320 | live | no timeout shape is written for opencode |
| #321 | live | a decision is required; and D5's prerequisite is a second bug |
| #322 | live | no `doctor` subcommand exists |
| #323 | live | neither `sofer_meta_set` nor `sofer_meta_check` exists |
| #324 | live | no `curation_rationale` key exists |

Two bodies carry an inaccuracy that a correction comment should record (not posted — publishing is the
maintainer's action): #317.2's "the Windows branch is effectively dead" is a wrong diagnosis, and #319's
"`data-quality` has none" was overtaken by PR #315.

## Tasks

| ID | Issue | Route | Spec | State |
| --- | --- | --- | --- | --- |
| T1 | #316 | inline, test-first | S3 | delivered |
| T2 | #319 | inline | S8, S9 | delivered |
| T3 | #318 | inline | S7 | pending |
| T4 | #317 | inline, test-first | S5 | pending || T5 | #317 | inline, recipe + re-run | S4 | pending |
| T6 | #317 | record only | S6 | pending |
| T7 | #321 | decision | S10, S11, S12 | pending |
| T8 | #320/#321 | analysis | S2 | delivered (see the section above) |
| T9 | — | issue hygiene | S2 | delivered — nothing merits closing (see the section above) |

## Log

L1 (user, verbatim): "revisá los issues de tipo bug y chore y armate un plan de implmentación, no confies
en los bodies de los issues, chequealos"

L2 (user, verbatim): "bien arrancá con #316, luego los chores, también resolvé esto que mencionás del
solapamiento y cerrá los issues que no tengan sentido si hay alguno"

L3 (evidence): the audited open bug/chore set is exactly five issues; the recently closed bugs `#289`,
`#292`, `#293`, `#297`, `#304`, `#305` and `#274` were each re-checked against `dev` and are **genuinely
fixed** (schema-grouped configs, `_check_duplicates` per-file attribution, the wider `datasets` import
guard, the stale-`.coverage` guard, and `resolve_config_path`'s `--user-config` / `user_env_dir` branches
all present).

L4 (evidence, raised while implementing T4): `openspec/specs/data-quality/spec.md` §1 does not merely omit
the Windows figure — it **declares** the omission as evidence ("**No peak RSS is published.** ... on the
Windows host this was run on it reported 5.2 MiB for that child — a silent constant, confirmed
independently with `tasklist` ... so the script prints `n/a` instead"). Two things follow. First, T4 is a
spec change, not an ad-hoc fix: publishing a real Windows number falsifies that sentence. Second, the
sentence's *diagnosis* is wrong in the same way the issue body was — `tasklist` agreeing with ctypes is
not independent confirmation, it is two readings of the same 5.2 MiB trampoline; the interpreter holding
the memory is its child. The spec delta must correct the claim, not just the outcome.
