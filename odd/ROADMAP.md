# Roadmap

## v0.6.0 — agent surface & card completeness

**Milestone:** [v0.6.0 — agent surface & card completeness](https://github.com/emiliodavola/sofer/milestone/1)
**Issues:** #287, #288, #291, #296, #303, #306
**Verified against:** `dev@6786ba1`, working tree clean, no open PRs and no open `openspec/changes/`.

This file is the plan of record for the milestone. Each phase is its own SDD change on its own
branch, archived inside its own delivery PR (AGENTS.md rule 15). The per-phase feature documents
live under `odd/tasks/` and carry the task list, the decisions and the commit evidence.

### Verification of the reported defects

Every claim in the six issues was checked against the code, not against the issue text.

| Issue | Reproduces | Current-code evidence |
| --- | --- | --- |
| #287 | yes | `grep -rn connect_timeout src/ README.md docs/` → 0 hits. `ADAPTERS` (`mcp_registration.py:88-215`) carries `native_env`/`native_scope` only. The README per-agent table (lines 711-722) documents `command, cwd, env` and no timeout. `mcp_server.py` imports `.cli` at module load, so `scanner`/`prepare`/`publish`/pandas/pyarrow are all imported before `initialize` can be answered. No `doctor` subcommand exists. |
| #288 | yes | The `init` template is entirely placeholders (`cli.py:994-998`). No placeholder detection in `checks.py`/`quality.py` (`grep TODO` → 0 hits). No `sofer_meta_set`/`sofer_meta_check` in `mcp_server.py`. `sofer_validate`'s `Requires:` (`mcp_server.py:1172`) never mentions `[meta]`, and the canonical chain has no metadata step. |
| #291 | yes | All seven sentinel sites exist today: `_ns` at `repo_compliance.py:1522`, `- **Repository:** _ns` at 1691, Direct Use at 1699, Out-of-Scope Use at 1703, Curation Rationale at 1826, Bias/Risks/Limitations at 1853, Dataset Card Contact at 1892. The issue's line numbers are from v0.5.0 and have drifted; the substance holds. |
| #296 | yes | No `timeout` in `ADAPTERS`; no `Context`/progress usage anywhere in `mcp_server.py`; `specs/mcp-registration` and `specs/mcp-server` say nothing about timeouts. Pi's own `docs/mcp.md:68` documents a per-server `timeout` (default 60, reset by progress notifications), so the registered entry can carry it. |
| #303 | yes | `splits.py:303` → `validate_split_mapping(remotes)`, no config names. `publish.py:487` → `_print_split_mapping_validation(remotes)`, which never sees the card. The warning text (`splits.py:340-350`) is generic. `openspec/changes/archive/2026-10-13-fix-mixed-schema-configs/design.md` §3.3 and R2 record the removal and name this a follow-up. |
| #306 | yes | The memory clauses in `openspec/specs/data-quality/spec.md:34-38` cite structural tests only (`test_memory_is_o_columns_not_o_rows`, accumulator-size comparisons). The only RSS figure in the repository is the pre-fix 16.1 GB in the archived design/proposal/task document. No measurement of the fixed code exists. |

### One correction to the issues as written

#291 proposes *omitting* an unconfigured section as its first option. That is **not a code-only
fix**: `openspec/specs/repo-compliance/spec.md:82` requires the placeholder (`"[Not specified]"`),
and the *Minimal config* scenario at `:199` requires it again. Choosing omission means the change
also carries a spec delta and rewrites the tests that today assert the sentinel.

### Coupling map

```
287 ─┬─ same file, same defect class ─┐
296 ─┘   (host-side timeouts)          ├─→ one change, two specs
                                       │
303 ─── independent, cheap ────────────┘
291 ──→ 288   (the [meta] key set defines what the gate validates)
306 ─── independent, no src change, parallelizable
```

Nothing else overlaps. `mcp_registration.py` is the bottleneck for 287+296; `repo_compliance.py`
serves 291 and 303, which share `build_dataset_card()` but no concern.

### Phases

### Fase 1 — `fix/mcp-registration-timeouts` (#287 + #296) — size M

One branch, one SDD change (`openspec/changes/<date>-fix-mcp-registration-timeouts/`), spec
`mcp-registration`, two work-unit commits so either issue can be cherry-picked alone.

- New `ADAPTERS` capabilities beside `native_env`/`native_scope` — `native_timeout` and
  `native_connect_timeout` — so the registry stays the single source of truth.
- `--timeout` / `--connect-timeout` flags with `[tool.sofer]` defaults (AGENTS.md rule 1).
- README + README_ES: a per-agent row in the table, a cold-start paragraph (#287 §1) and the list
  of tools expected to run for minutes (#296 §2).
- #296 §3 (progress notifications) is a **separate change**: it touches every `sofer_*` tool and
  the `mcp-server` spec. Tracked as Fase 1b, not folded in.
- Cost to budget: `cli.py` is one of the four modules under the 100.00% line-coverage mandate
  (rule 14), so the new flags need real coverage, not pragmas.
- Risk: additive optional field on a contract others consume, which the Task Size rule excludes
  from high risk. Reported as item 3-adjacent in the closing line.

### Fase 2 — `fix/303-card-config-group-warning` (#303) — size S

`build_dataset_card()` already computes `plan = schema_config_plan(...)` at
`repo_compliance.py:1570` and discards it by returning `str`. Return the plan (or a small
`CardPlan`) so `prepare`/`publish` can print the warning with the emitted config names, instead of
the generic two-shape message. Spec `repo-compliance` → RC-Universal-Card S4.

### Fase 1b — `feat/mcp-progress-notifications` (#296 §3) — size M

Emit progress notifications from the long-running tools so a host deadline is reset instead of
raised by configuration, which also covers hosts whose timeout is not user-configurable. Spec
`mcp-server`.

### Fase 3 — `feat/291-card-section-keys` (#291) — size L, blocked by D1

Either add the `[meta]` keys the generator cannot currently fill (`repository`, `direct_use`,
`out_of_scope_use`, `bias_risks_limitations`, `contact`, plus `study_design` promoted to the
obvious path) and fall back `- **Repository:**` to `source`/`source_url`; or omit unconfigured
sections, which carries a `repo-compliance` spec delta at `:82` and `:199` plus rewritten tests.

### Fase 4 — `feat/288-agent-metadata-flow` (#288) — size M/L, after Fase 3

After the key set is settled, so the gate and the tool cover the new keys once. Adds the metadata
step to the canonical chain the agent reads, a template-placeholder detector (force decided by
D3), and optionally `sofer_meta_set` / `sofer_meta_check`. Specs `mcp-server` and the home of the
new check.

### Fase 5 — `chore/306-bounded-quality-scan-evidence` (#306) — size M, parallelizable

No `src/` change, so no coverage risk. A synthetic corpus in a temp dir, `sofer validate` with
default quality settings, peak RSS and wall time recorded, then the same run with
`full_scan = "never"` and a lowered `max_dup_tracking`. Output: a `verify:` row in
`specs/data-quality` plus corrections to any sentence the measurement falsifies.

### Order of execution

By user impact, not by issue number: Fase 1 (a lost MCP envelope is the only failure that makes an
agent reason on a lie) → Fase 2 (cheap, closes a declared R2) → Fase 1b → Fase 5 (cheap, no code
risk, parallelizable) → Fase 3 → Fase 4.

### Decisions required from the maintainer

| # | Decision | Recommendation |
| --- | --- | --- |
| D1 | #291: omit unconfigured sections (spec change) or add the `[meta]` keys? | Add the keys plus the `repository` → `source` fallback: it fixes a fully-filled config without touching the spec or the *Minimal config* tests. Omission is the more expensive option B. |
| D2 | #296: write the timeout and document it now, or also emit progress notifications? | Timeout + docs in Fase 1; notifications as its own change (Fase 1b). |
| D3 | #288: should the placeholder gate `warn` or `fail`? | `warn`. A `fail` breaks every existing config that still carries a placeholder, which is a contract change, not a fix. |
| D4 | #306: is 20 M rows honest enough, and on which machine does the run happen? | 20 M rows plus one repetition with the knobs lowered, on the 65 GB host named in #290. |

All six phases above are delivered and archived. The nine issues filed on 2026-10-16, the day this
milestone closed, are the next batch.

## v0.7.0 — follow-up defects from the v0.6.0 batch

**Issues:** #316, #317, #318, #319, #320, #321, #322, #323, #324
**Verified against:** `dev@eaf56f5`, working tree clean, no open PRs and no open `openspec/changes/`.
**Feature document:** [`odd/tasks/bug-chore-followups.md`](tasks/bug-chore-followups.md) — task list,
decisions and commit evidence.

Every claim in the nine issues was checked against the code. One body carried a wrong diagnosis
(#317.2: the Windows RSS branch is correct, the sampled **pid** is a uv trampoline), one carried a stale
measurement (#319: `data-quality` gained a `verify:` row in PR #315, so the probe that returned 0 now
returns 1), and one uncovered a prerequisite its own proposal did not know about (#321: codex's native CLI
acts on `$CODEX_HOME` while the adapter resolves `~/.codex`, so "delegate then patch" would patch a
different file than the native writer — the #274 defect class, still live for codex). The four remaining
`type:feature` issues (#320, #322, #323, #324) were checked too and every premise still holds.

### Batch A — bug/chore — **delivered**

| ID | Issue | Delivered in | Evidence |
| --- | --- | --- | --- |
| T1 | #316 split-mapping warning prints one message per file | #327 (`4c68cef`) | RED was 66 warnings for 65 files, GREEN is 1. The per-file message's *mixed* case turns out to be structurally unreachable — `detect_splits` attributes a file by its keyword — so the guard is pinned with a synthetic split instead of being deleted |
| T2 | #319 the `verify:` hatch size excludes the backlogged specs | #327 (`e1bc04f`) | option 2: the line states its own scope. Option 1 (a second counter) was measured and rejected — the whole backlog holds exactly one such line and no row syntax |
| T3 | #318 README lists 3 of 26 `[meta]` keys | #327 (`14d9131`) | a pointer to §2.1.1 in both READMEs rather than a drifting second copy |
| T4 | #317.2 the RSS sampler reads a trampoline | #327 (`2e77c51`) | calibration `(False, 5.2 MiB)` → `(True, 216.6 MiB)`. **Two** reader sites, not one: fixing only the calibration left the published figure at 5.2 MiB, and only a smoke run caught it |
| T5 | #317.1 the corpus never reaches the dup cap | #327 (`2e77c51`) | a third case holds the default policy with a cap the corpus reaches; the peak does not move across a 100× range of cap |
| T6 | #317.3 the 20 M row run | — | recorded as **not performed** in the spec and the archive report; no host with the space and patience |
| T7 | #321 native codex/gemini delegation declines by default | #328 (`967964d`) | the decision was to keep the decline and name the trade-off; option 1 was rejected on measurement, and the rejection is recorded in the change folder |
| — | #325 codex resolves `~/.codex` while its CLI acts on `$CODEX_HOME` | #328 (`2eda0af`) | found while working T7, and its prerequisite. One adapter field; the issue's own proposed fix would have moved the default |

Both PRs are merged — #327 as `2451763`, #328 as `397e7e2` — and both branches are deleted.

**One debt this batch created and then closed:** #328 merged without the archive move AGENTS.md rule 15
requires, leaving both change folders at `openspec/changes/` and their `tasks.md` files carrying `pending`
rows for work already done. `chore/sdd-close-v0.7.0-record` closes it; each archive report now carries a
"Late archive" section recording the miss, its cause and the remedy, because that record is the only thing
a future reader has.

### Finding raised by this batch (not in any issue)

The end-to-end measurement T5 produced answers #317 item 1 in a way that also **falsifies a sentence the
merged `data-quality` spec currently carries**. The peak does not move across a 100× range of
`quality_max_dup_tracking`, and the cap really is reached — but the peak is ≈1× the corpus size
(44.0 / 63.4 / 160.1 MiB for 31.2 / 63.4 / 160.0 MiB of CSV), so `sofer validate`'s memory is **not**
independent of the dataset size. #290's fix removed the 16.1 GB climb; it did not bound memory to a
constant. Instrumenting the two phases separately places the whole size-proportional spike in
`QualityValidator.run()` (44.0 MiB on a 31.2 MiB corpus) and none of it in `DatasetValidator.run_all()`
(0.0 MiB), and a post-pass snapshot retains almost nothing — so the spike is transient. This is reported,
its spec sentence is corrected in this batch, and the fix is proposed as its own issue — a `src/sofer/`
change with data-path consequences does not ride along on a chore.

### Order of execution

T1 (a live defect a user reads three times) → T2 and T3 (one-line-of-substance chores) → T4 (unblocks
real Windows evidence) → T5 → T6 → T7 (blocked on a maintainer decision).

### Decision required from the maintainer

| # | Decision | Recommendation |
| --- | --- | --- |
| D5 | #321: delegate natively and then patch the timeout keys into the same file (the issue's option 1), or keep the decline and make `--no-timeout` louder (option 3)? | **Decided: option 3, made honest** — keep the decline, and name the trade-off at the point a user meets it. Option 1 was rejected *after measuring*, not as a preference: `atomic_write` rewrites the whole document for TOML and JSON while only YAML splices, and `merge()` replaces the `sofer` entry wholesale, so "delegate then patch" produces the same document as the direct file edit — a `subprocess` and an extra `.bak` for nothing, with the claimed comment preservation undelivered. The prerequisite this row predicted was real and shipped anyway, as #325. |
