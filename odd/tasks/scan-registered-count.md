# Feature: scan-registered-count — issue #345

**Branch:** `fix/345-scan-registered-count` from `dev@c68e090`
**Issue:** `emiliodavola/sofer#345` — *bug(mcp): sofer_scan_apply/scan_dry_run under-report "registered" by the number of stripped init placeholders*
**Delivery PR:** pending — push and PR creation are the maintainer's decision
**SDD change:** `openspec/changes/archive/2026-10-18-fix-scan-registered-count/` (archived inside this branch, AGENTS.md rule 15)
**Phase:** 1 of the 2026-10-18 batch (first: smallest surface, and it shares the scan blocks in `mcp_server.py` with the pending #347)

## Goal

`registered` in the scan envelope is measured as `len(merged) - len(before)`, where `before` is
captured *before* `merge_entries` strips the two `raw/example*` placeholders that `sofer_init`
writes. On every greenfield MCP scan the field is therefore low by exactly 2. The CLI has the same
defect on `Registered N new [[file]] entry(s).`, so the count is wrong on all three surfaces and
right nowhere.

## Specs

S1 — #345 `## Expected behaviour` (verbatim): "`registered == N` when no file was previously
registered. With `N = 65`: `registered: 65`."

S2 — #345 `## Fix` (verbatim): "Measure `before` after the strip, or have `merge_entries` report the
number of entries it appended. The second is the honest one: `added` already exists inside
`merge_entries` as a local and is simply not returned."

S3 — #345 `## Impact` (verbatim): "the count is part of the machine-readable contract, so an agent
that trusts it concludes two files were silently dropped".

S4 — #345 comment, 2026-10-18 (verbatim): "A test that scans `N` loose files into a fresh
`sofer_init` tree and asserts `registered == N` would pin it."

S5 — maintainer decision, 2026-10-18 (verbatim): "sí incluir cli.py" — the CLI printout carries the
same defect and ships in this change rather than as a separate issue.

S6 — #345 `## Summary` (verbatim): "The `registered` field of the structured envelope disagrees with
the TOML the very same call writes."

## Tasks

| # | Task | Spec | Commit |
| --- | --- | --- | --- |
| T1 | `scanner.merge_entries_counted` returns `(toml, added)`; `merge_entries` stays a thin wrapper | S2 | `b6f2d56` |
| T2 | Both MCP scan tools report the counted value; `registered` described in both `output_schema` blocks | S1, S3 | `b6f2d56` |
| T3 | CLI `scan` reports the counted value in `Registered N` and the dry-run preview | S5 | `b6f2d56` |
| T4 | Tests: MCP apply + dry-run on a fresh `sofer_init` tree, idempotent re-scan, CLI line, scanner unit | S1, S4 | `b6f2d56` |
| T5 | `scan` + `mcp-server` spec clauses, both deltas and the archive report | S1-S3 | `0decb63` |
| T6 | Gates: pytest 2483/9, `scanner.py` + `cli.py` at 100.00%, ruff, mypy, pyright, mapping checker | — | `b6f2d56` |

## Log

**L1** — maintainer request (verbatim): "revisá los issues de tipo bug y armate un roadmap de
implementación"

**L2** — maintainer decisions (verbatim): "1. sí incluir cli.py / 2. ambos / 3. explicito / abrí los
issues también"

**L3** — discovery: the CLI carries the same defect at `cli.py:645-649` (`before_count` captured
before the strip). #345 is labelled `bug(mcp)` and does not mention it; the maintainer decided (L2,
item 1) to fix both in this change.

**L4** — evidence: `mcp_server.py:2838-2840` (`sofer_scan_dry_run`, def at `2750`) and
`mcp_server.py:2979-2981` (`sofer_scan_apply`, def at `2890`); strip at `scanner.py:434-444`;
`added` computed at `scanner.py:471` and discarded.

**L5** — RED observed before the fix, on all three surfaces: MCP `assert 3 == 5` over 5 files;
CLI `Would register 1` for 3 files; `ImportError: cannot import name 'merge_entries_counted'`.
The first CLI dry-run test was rewritten after its RED because `scan --dry-run` returns right after
the MOVE preview when loose candidates exist (`cli.py:572-579`, by design), so the registration
preview is only reachable with sources already under `raw/`; RED was re-observed on that path.

**L6** — GREEN and gates: suite `2483 passed, 9 skipped` (baseline 2476/9), `scanner.py` 100%,
`cli.py` 100%, TOTAL 94%, ruff/mypy/pyright clean, `check_test_mapping.py` OK. The gate battery was
run inline: two `gentle-ai-worker` launches were refused with `Writer session Git authority changed
before admission` and no native `Agent` fallback is available in this environment.

**L7** — commits `b6f2d56` (fix + tests), `0decb63` (specs + change folder), and the archive commit
(odd rows + `openspec/changes/archive/2026-10-18-fix-scan-registered-count/`). The branch is not
pushed and no PR exists; that is the maintainer's decision.
