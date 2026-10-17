# Feature: scan-move-to-raw-mandatory — issue #339

**Branch:** `fix/339-scan-move-raw-mandatory` from `dev@ec511e7`
**Issue:** `emiliodavola/sofer#339` — *bug(scan): moving sources into raw/ is opt-in, so the default MCP flow leaves them in the disposable cache/*
**Delivery PR:** pending — assigned to `@emiliodavola`
**SDD change:** `openspec/changes/2026-10-17-fix-scan-move-raw-mandatory/`
**Phase:** 1 of the v0.8.0 batch (first, because it is the only one of the three with a data-loss path)

## Goal

`sofer_scan_apply` is the documented agent path (`sofer_init` → `sofer_scan_apply`), and today its
move-to-`raw/` half is gated behind `move_loose`, default `false`. The default run therefore reproduces
exactly the state #152 was filed about: `raw/` empty, sources left loose next to the TOML, and the
`[[file]]` entries pointing at `cache/` — the tool-wide, sibling-shared, deletion-prone staging
directory that `clean_cache` removes. On top of that, registering a nested loose file flattens it one
segment (`Labels/x.csv` → `cache/x.csv`) while the same file after the move registers as
`cache/Labels/x.csv`, so a re-scan adds a second entry for one source and the stale entry is never
removed. One source file ends up registered under two remotes.

The CLI already does the right thing and the MCP adapter does not, which is the CLI/MCP parity
mismatch #152 accepted as its own criterion.

## Specs

S1 — the maintainer's requirement (#339, verbatim): **"`sofer_scan_apply` is a mandatory step and
moving the data into `raw/` is obligatory"** — "it must run as part of the workflow rather than
depending on an operator remembering a flag."

S2 (#339, verbatim): "The canonical chain populates `raw/` without an extra flag, or fails closed and
names the required action - it must never silently leave the sources outside `raw/`."

S3 (#339, verbatim): "A re-scan is idempotent whatever the layout: the same file maps to the same
destination whether it is discovered loose or under `raw/`."

S4 (#339, verbatim): "`validate`/`prepare` refuse a config whose `local` points into `cache/` while
`raw/` holds no corresponding source, so `clean_cache` cannot destroy the only copy of a registered
file."

S5 (#152, verbatim): "After `sofer_scan_apply` on a directory with loose supported files, the files end
up under `raw/`, not silently left at TOML level." — plus "CLI/MCP parity of move semantics; dry-run
performs no mutation; collisions abort before any move."

S6 (#339 proposed fix 5, verbatim): "Document the step in the workflow contract (`workflow.py` and the
MCP `next` hints) so an agent following the chain cannot skip it."

## Measured baseline (2026-10-17, `dev@ec511e7`)

`tmp/verify-339/repro.py` drives the real helpers (`discover_files` → `merge_entries` → `move_to_raw` →
`discover_files` → `merge_entries`) over `A.csv` + `Labels/B.csv`:

```
run 1  registered entries    = ['cache/A.csv', 'cache/B.csv']      raw/ populated = False
run 2  moved                 = ['raw/A.csv', 'raw/Labels/B.csv']
run 2  registered entries    = ['cache/A.csv', 'cache/B.csv', 'cache/Labels/B.csv']
TOTAL entries for 2 files    = 3     remotes = ['A.csv', 'B.csv', 'Labels/B.csv']
```

## Tasks

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | RED: MCP default run moves loose files into `raw/` | S1, S2, S5 | **done** | RED against pre-fix `src/` (stashed): `tests/test_mcp_server.py::TestScanMoveToRawPhase` → `assert 0 == 1 where 0 = envelope.get('moved')`, the nested file absent from `raw/`, and the dry-run advertising `move_loose` |
| T2 | RED: `scan → move → scan` registers nothing new (nested tree) | S3 | **done** | RED against pre-fix `src/`: `ImportError: cannot import name 'registration_path' from 'sofer.scanner'` (collection) — the helper and the key rule did not exist |
| T3 | RED: `validate`/`prepare` refuse a `cache/`-only registration whose source is absent from `raw/` | S4 | pending | — |
| T4 | GREEN: make Phase 1 unconditional in `sofer_scan_apply`; keep the collision abort and the `dry_run` preview; the stale `move_loose` parameter is removed (see D1) | S1, S2 | **done** | `sofer_scan_apply`/`sofer_scan_dry_run` run the move unconditionally; both call `check_raw_collisions` before any move; `grep -rn move_loose src/` → 0 hits; `tests/test_mcp_server.py::TestScanMoveToRawPhase` 6 passed; `tests/test_parity.py` exemption removed |
| T5 | GREEN: register every discovered file relative to `raw/` instead of dropping a fixed segment, so layout cannot change the destination | S3 | **done** | new `scanner.registration_path` (#339) used by `check_flatten_collisions`, `merge_entries` and `copy_files`; loose and `raw/`-rooted discovery key identically; `TestRegistrationPath` 4 passed |
| T6 | GREEN: new enforcement check for S4, fail-closed, naming the exact repair | S4 | pending | — |
| T7 | GREEN: report duplicates/stale `cache/` entries on scan without rewriting unrelated config; name the repair in the envelope | S3 | pending | — |
| T8 | `workflow.py` + MCP `next` hints + tool descriptions name the mandatory move | S6 | **done** | both tool docstrings/descriptions state the move is mandatory and never an opt-in; `_PHASED_INSTRUCTIONS` names it in the Phase 0 chain |
| T9 | `scan` spec: SCN-01/SCN-02 key rule and SCN-07 move contract amended in place, plus 3 new scenarios; README + README_ES (rule 13) and rule 7 help text | S1-S6 | **partial** | spec amends landed (SCN-01, SCN-02, SCN-07 + `MCP scan moves without an opt-in flag`, `Nested tree keys identically loose and under raw`, `MCP dry-run previews the mandatory move`); README pair and argparse help updated. `scan` is in the permanent declared-backlog registry, so no `## Test Mapping` row is owed. The SDD change folder and the S4 clause land with T6/T7 |
| T10 | Gates: pytest, ruff, mypy, pyright, coverage (rule 14: `scanner.py` + `cli.py` at 100.00%), commit slices, push, PR assigned to `@emiliodavola` | — | **partial** | `uv run pytest tests/ -q` → **2387 passed, 9 skipped** (baseline `2380 passed, 9 skipped`); `uv run ruff check src/ tests/ scripts/` clean; `uv run ruff format --check src/ tests/` clean. mypy/pyright/coverage and the push/PR remain |

## Decisions

- **D1 — `move_loose` is removed, not defaulted to `true`.** A parameter that must always be `true` is a
  lie in the tool schema, and leaving it accepts `move_loose=false` as a silent way back to the reported
  state. The MCP tool is pre-1.0 surface and the removal is a documented breaking change (rule 12);
  agents that passed `move_loose=True` keep working, agents that relied on the default stop skipping the
  move, which is the point.
- **D2 — the move stays previewable, never promptable.** The MCP channel has no terminal, so
  `sofer_scan_dry_run` keeps previewing the move and `sofer_scan_apply` executes it. `[y/N]` remains
  CLI-only (§the CLI already prompts or takes `--force`).
- **D3 — the registration key is `raw/`-relative, not "drop the first segment".** The spec's intent
  (SCN-02 "Flattened paths") is `raw/Labels/x.csv` → `remote = "Labels/x.csv"`; dropping a fixed segment
  only expresses that while discovery happens to be `raw/`-rooted. Making the move mandatory restores
  that invariant, and computing the key relative to `raw/` keeps it true for any nesting depth.
- **D4 — the S4 check refuses; it does not rewrite the TOML.** Silently rewriting a generated config
  hides a state the operator must see, and the repository has no format-preserving array-of-tables
  writer outside `meta_edit.py`. The check fails closed and names the repair (`re-scan after the
  mandatory move`, or delete the stale entry).
- **D5 — legacy duplicate entries.** After T5 a re-scan no longer creates duplicates, but entries a
  pre-fix scan already wrote stay. T7 reports them (count + first N paths + the repair) instead of
  mutating them.

## Log

- **L1** (user, verbatim): "revisá los issues pendientes e armate un roadmap de implementación, no
  confies en lo que dicen, chequeá a partir de ellos y asegurate que digan lo correcto, sino modificalos

  necesito una rama por issue y luego un push y PR (asignado a mi) por implementación"
- **L2** (user, verbatim): "usá ODD obligatoriamente"
- **L3** — verification (2026-10-17): every claim in #339 checked against `dev@ec511e7`; the
  double-registration reproduced with the real helpers. One correction applied to the issue: "both
  entry points are opt-in" is false — the CLI `sofer scan` runs Phase 1 unconditionally
  (`cli.py:550-593`) and only the MCP adapter gates it. One finding added: the stale entry is also never
  removed, so one source is registered under two remotes. Evidence appended to the issue body.
- **L4** — slice 1 delivered on `fix/339-scan-move-raw-mandatory` (T1, T2, T4, T5, T8, and the T9
  documentation half): the move is unconditional in both MCP scan tools and `move_loose` is gone from
  the schema; `scanner.registration_path` keys every file relative to the root that owns it, so a loose
  `Labels/x.csv` and its post-move `raw/Labels/x.csv` register identically and a re-scan adds nothing.
  RED was observed against the pre-fix `src/` (stashed) before the GREEN run. Suite 2380 → 2387 passed.
  Deviation from the plan: none in scope; the SDD change folder was deferred to the T6/T7 slice so the
  delta it describes is complete when it is written.
