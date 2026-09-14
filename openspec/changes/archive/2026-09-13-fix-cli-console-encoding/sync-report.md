# Sync Report — fix-cli-console-encoding (GitHub #161)

```yaml
schema: gentle-ai.sync-result/v1
change: 2026-09-13-fix-cli-console-encoding
status: synced
artifact_store: openspec
branch: fix/161-cli-console-encoding
```

## 1. Status

**SYNCED** — both frozen deltas were promoted into the canonical specs. The change folder was **not**
moved to `openspec/changes/archive/` (that is `sdd-archive`) and **nothing was committed**.

| Item | Outcome |
| --- | --- |
| Delta kind | 1 × **MODIFIED** requirement (`PB-02`) + 1 × **ADDED** requirement (`CLI-R11`) |
| Domains synced | `process-boundary`, `cli` |
| Canonical files updated | `openspec/specs/process-boundary/spec.md`, `openspec/specs/cli/spec.md` |
| Destructive sync? | **No** — no `## REMOVED Requirements`, no `## RENAMED Requirements`, no large MODIFIED block; PB-02's block was replaced only after proving every pre-existing scenario survives byte-identical |
| Approval gate | Not required (see §6) |
| Same-domain collisions | **None** (see §5) |

## 2. What was moved where

| Delta source | Normative content | Canonical destination |
| --- | --- | --- |
| `.../specs/process-boundary/spec.md` → `## MODIFIED Requirements` → `### Requirement: CLI user-visible output via executable subprocess (PB-02)` | Requirement prose + 4 scenarios, **full-block replacement** | `openspec/specs/process-boundary/spec.md`, PB-02 kept at its existing position (between PB-01 and PB-03) |
| `.../specs/cli/spec.md` → `## ADDED Requirements` → `### Requirement: Console output survives an unencodable character (CLI-R11)` | Requirement prose + 3 scenarios + its own `> Added by change …` provenance line | `openspec/specs/cli/spec.md`, appended immediately after CLI-R10 (the previous last requirement) |

### PB-02 — canonical edit detail

- The old one-paragraph prose was **replaced** by the delta's paragraph (12-invocation cp1252 boundary
  spanning every subcommand's help **and** the CLI's runtime console paths), plus the delta's
  `(Previously: …)` note.
- Scenario *cp1252 help on the ubuntu matrix* was **expanded in place**: its `- WHEN` / `- THEN` bullets
  now name the 12 invocations and add the `- AND no invocation SHALL surface a UnicodeEncodeError` bullet.
- Scenario **cp1252 runtime console output** was **added** (validate `rc == 1` + `scan --dry-run` `rc == 0`
  under `PYTHONIOENCODING=cp1252`).
- Scenarios *Help via subprocess* and *Dispatch exit codes* were carried across **byte-identical**.
- **One line was added that is not in the delta block**: the provenance note
  `> Modified by \`2026-09-13-fix-cli-console-encoding\` (GitHub #161).`, placed directly under the heading
  in the exact shape the same file already uses for PB-04 and PB-09
  (`> Modified by \`fix-dataset-identity-context\` (archived 2026-09-04).`). Per the repo convention the
  `(archived …)` suffix is omitted because the change is not archived yet; the `(GitHub #161)` form is the
  one this change's own deltas use. This is metadata, not normative text — the only canonical line that
  differs from the delta block.
- **No other requirement in the file was touched**, and no unrelated prose was rewritten.

### CLI-R11 — canonical edit detail

Appended verbatim after CLI-R10's final scenario, carrying the delta's **own** provenance blockquote
`> Added by change \`2026-09-13-fix-cli-console-encoding\` (GitHub #161).` (inside the requirement block,
matching CLI-R05/CLI-R06/CLI-R09's in-block provenance style). No separator rule was inserted: the file's
three most recently appended requirements (CLI-R08, CLI-R09, CLI-R10) carry no `---` before them, so the
append mirrors that. RFC 2119 phrasing and heading level are identical to the delta.

## 3. Requirement inventory (before → after)

| Capability | Requirements before | Requirements after | Scenarios before | Scenarios after |
| --- | --- | --- | --- | --- |
| `process-boundary` | 9 (`PB-01`..`PB-09`) | **9** (unchanged — PB-02 replaced, not added) | 30 | **31** (`PB-02`: 3 → 4) |
| `cli` | 10 (`CLI-R01`..`CLI-R10`) | **11** (`CLI-R11` added) | 45 | **48** (`CLI-R11`: +3) |

Measured with `grep -c "^### Requirement"` / `grep -c "^#### Scenario"`, before and after (§7).

- **ADDED requirement names:** `Console output survives an unencodable character (CLI-R11)`.
- **MODIFIED requirement names:** `CLI user-visible output via executable subprocess (PB-02)`.
- **REMOVED requirement names:** none.
- **RENAMED requirement names:** none (and `## RENAMED Requirements` does not appear in either delta, so the
  unsupported-RENAMED block does not apply).

## 4. Scenario → test mapping (frozen scenarios + V-01 closure)

Source of truth: `verify-report.md` §3 (scenario tables, verdict `passed`) plus the **test-only follow-up**
recorded in `apply-progress.md` § `V-01 closure`. The verify report is frozen and predates the follow-up;
the mapping below is the **final** state.

| Requirement | Scenario | Test (`tests/test_cli.py`) | Outcome |
| --- | --- | --- | --- |
| PB-02 | Help via subprocess | `TestSubprocessBoundary::test_help_exits_zero_and_lists_every_subcommand` | PASSED |
| PB-02 | cp1252 help on the ubuntu matrix (12 invocations) | `TestSubprocessBoundary::test_help_strict_cp1252[argv0..argv11]` | 12 × PASSED |
| PB-02 | cp1252 runtime console output | `TestSubprocessBoundary::test_runtime_output_strict_cp1252` (validate half) + `::test_scan_dry_run_strict_cp1252` (dry-run half) | PASSED |
| PB-02 | Dispatch exit codes | `TestSubprocessBoundary::test_unknown_command_exits_2` | PASSED |
| CLI-R11 | Runtime output with an unencodable character keeps the command's result | `TestSubprocessBoundary::test_runtime_output_strict_cp1252` (shared with the PB-02 runtime scenario) | PASSED |
| CLI-R11 | ASCII literal with an unencodable interpolated value does not abort | `TestSubprocessBoundary::test_interpolated_unencodable_value_strict_cp1252` (**stderr** / argv vector) **+** `TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252` (**stdout** / TOML-declared-path vector, added by the `V-01` closure, +37 lines) | PASSED (both halves) |
| CLI-R11 | Console warning path carrying a glyph degrades instead of aborting | `TestSubprocessBoundary::test_codebook_warning_strict_cp1252` | PASSED |
| CLI-R11 | normative clause, rule-14 arms (not a frozen scenario) | `TestConsoleEncodingGuard::test_console_streams_reconfigured_in_place` / `::test_console_guard_skips_stream_without_reconfigure` / `::test_console_guard_survives_unreconfigurable_text_wrapper` | 3 × PASSED |

**All 7 frozen scenarios have a named, passing test (AGENTS.md rule 6).** Final measured suite after the
follow-up: **1766 passed / 6 skipped**, `tests/test_cli.py` collecting **166** tests (the frozen verify
report recorded 1765 / 165 before the follow-up). PB-09's shared `run_cli` subprocess helper is reused,
not re-implemented — the synced PB-02 text now states that reuse explicitly.

## 5. Active same-domain collisions

**None.** Native status reports `relationships.sameDomainActiveChanges: []`, `collisions: []`; the only
non-archive change directory under `openspec/changes/` is this change. No other active change touches
`openspec/specs/process-boundary/spec.md` or `openspec/specs/cli/spec.md`, so no archive/sync ordering
decision was needed.

## 6. Destructive-sync approvals / blockers

- No `## REMOVED Requirements` and no `## RENAMED Requirements` in either delta.
- PB-02 is a **full-block MODIFIED** replacement, but it is not destructive: the two pre-existing scenarios
  were proven byte-identical to their canonical predecessors and the requirement keeps its ID, heading and
  position. No `size:exception`, no approval gate, no blocker.
- `rules.sync` is **not declared** in `openspec/config.yaml` (it defines `proposal`, `specs`, `design`,
  `tasks`, `apply`, `verify`, `archive`), so no additional sync rules applied.

## 7. Validation commands and checks performed

```text
# requirement / scenario inventory, before -> after
$ grep -c "^### Requirement" openspec/specs/process-boundary/spec.md   # 9  -> 9
$ grep -c "^### Requirement" openspec/specs/cli/spec.md               # 10 -> 11   (expected +1)
$ grep -c "^#### Scenario"   openspec/specs/process-boundary/spec.md   # 30 -> 31
$ grep -c "^#### Scenario"   openspec/specs/cli/spec.md                # 45 -> 48

# focused diff — only the PB-02 block replacement and the CLI-R11 append
$ git diff --unified=0 -- openspec/specs/process-boundary/spec.md openspec/specs/cli/spec.md | grep "^@@"
@@ -374,0 +375,32 @@   (cli: pure append after CLI-R10)
@@ -59 +59,5 @@       (process-boundary: PB-02 prose -> provenance + prose + (Previously: …))
@@ -70,2 +74,11 @@   (process-boundary: PB-02 cp1252-help bullets expanded + runtime scenario added)
$ git diff --stat -- <the two canonical files>
 openspec/specs/cli/spec.md              | 32 +++++++++
 openspec/specs/process-boundary/spec.md | 19 +++--   (16 insertions, 3 deletions)
# No hunk touches any other requirement. Only 3 deletions exist in total: the old PB-02 prose line and
# the two old cp1252-help bullets that the delta itself replaces.

# byte-parity of the synced blocks against the deltas (normalized: trailing whitespace + blank edges)
  PB-02  : canonical == delta block, except the single deliberate `> Modified by …` provenance line — PASS
  CLI-R11: canonical == delta block, byte-for-byte (3538 == 3538 bytes) — PASS

# no delta wrapper / informational table leaked into canonical
$ grep -n "# Delta for\|## MODIFIED Requirements\|## ADDED Requirements\|Informational only" openspec/specs/{process-boundary,cli}/spec.md
# (no match)

# the explicit non-goal: CLI-R02's existing U+2192 untouched
  openspec/specs/cli/spec.md still contains `raw/→cache/→build/` and was NOT ASCII-ified — PASS

# encoding / line endings
$ git ls-files --eol openspec/specs/{cli,process-boundary}/spec.md
i/lf  w/lf  attr/text=auto eol=lf   (both)
  0 × CRLF byte pairs, no BOM — matches every other openspec/specs/*/spec.md

# pragma / scope
$ grep -c "pragma: no cover" openspec/specs/cli/spec.md openspec/specs/process-boundary/spec.md
0 for both; no `# pragma: no cover` introduced anywhere
$ git status --porcelain
 M README.md / README_ES.md / openspec/specs/cli/spec.md / openspec/specs/process-boundary/spec.md /
   src/sofer/cli.py / src/sofer/config.py / tests/test_cli.py
?? openspec/changes/2026-09-13-fix-cli-console-encoding/
# This phase's own writes are exactly: the two canonical spec files + this report. No src/, tests/,
# README*, AGENTS.md, tasks.md, verify-report.md, apply-progress.md or delta file was modified.
```

No git write command was run (no commit, no stage, no archive move).

## 8. Not synced (with reason)

| Item | Reason |
| --- | --- |
| Delta wrapper headers (`# Delta for process-boundary` / `# Delta for cli`, `## MODIFIED Requirements`, `## ADDED Requirements`) | Change-local scaffolding, not requirement content |
| The deltas' change-header blockquotes (`> **Change:** …`) | Change-level provenance; the canonical files carry requirement-level provenance instead |
| The deltas' trailing `<!-- Informational only … -->` scenario→test mapping tables | Explicitly marked "Not part of the archived requirement blocks"; canonical specs carry no such tables (matches the `2026-09-12-fix-mcp-opencode-env` sync) |
| ASCII-ification of spec prose (e.g. `U+2192` in CLI-R02) | Explicit non-goal of this change; spec files are UTF-8 documents, not console output. The U+2192 in `openspec/specs/cli/spec.md` was deliberately left intact |
| `V-01` finding, deviations `D1`–`D6`, issues `I-01`–`I-03` | Verify-phase findings owned by the parent / their own issues (stale test counts, `ruff format` drift, MCP `HF_TOKEN` isolation leak, etc.) — not spec content |
| Any `src/**`, `tests/**`, `README*`, `AGENTS.md`, frozen change artifact | Outside this phase's allowed edit surfaces |

## 9. Structured status and `actionContext` findings

- Native status: `artifactStore: openspec`, `isNonAuthoritative: false`, `planningHome.root` = the repo
  root, `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` — both
  canonical paths are inside the workspace and the allowed edit root. **No stop condition fired.**
- `dependencies.sync: blocked` at parent resolution is the pipeline's ordering rule ("sync only after
  verification is clean"). The verify report is present with verdict **`passed`** and its single
  non-blocking finding (`V-01`) was closed by the test-only follow-up — the sync input requirement is
  satisfied, so the state is treated as **ready**, per the non-authoritative/ordering carve-out.
  `nextRecommended: sdd-verify` in the same JSON is the pre-verify snapshot and is stale.
- `relationships.sameDomainActiveChanges: []`, `collisions: []`, `taskProgress: 36/36`,
  `taskArtifactErrors: []` — no collision or blocking signal.
- Two `sdd-owner: parent` lifecycle rows remain open: **8.1** (bounded review of the finalized diff) and
  **8.2** (accept vs. rollback + trigger archive). They are parent-owned and are the only remaining
  gate before archive; they are not implementation tasks and are not sync blockers.

## 10. Next recommended phase

**`sdd-archive`** — once the parent closes 8.1 (review) and 8.2 (accept). Archive readiness from this
phase's perspective: clean verify (`passed`), 36/36 implementation tasks checked, `sync-report.md` present,
and both canonical specs updated. The archive phase moves
`openspec/changes/2026-09-13-fix-cli-console-encoding/` to `openspec/changes/archive/2026-09-13-2026-09-13-fix-cli-console-encoding/`
and may normalize the PB-02 provenance line to the `(archived 2026-09-13)` suffix form then.

## 11. Risks

| Item | Severity | Note |
| --- | --- | --- |
| Pre-existing markdown-lint blocker at `openspec/specs/cli/spec.md:119` (`#### Scenario: TOML without [[file]] errors` parsed as a wikilink to `file`) | Low | The line is **byte-identical to HEAD** and lies outside every diff hunk of this sync — not introduced here, and fixing it would mean rewriting unrelated CLI-R03 prose (explicitly out of scope) and would break this phase's required diff shape (only the PB-02 replacement + the CLI-R11 append). The identical pattern exists in two untouched canonical specs (`profile/spec.md:171`, `render/spec.md:149`) and `[[file]]` appears bare in 11 canonical spec files, so this is a systemic corpus-wide linter false positive, not a sync defect. No test or script parses canonical spec titles (no `openspec/specs` reference under `tests/`, `scripts/`, `src/`). Needs its own housekeeping touch if the linter gate is enforced on canonical specs |
| PB-02 provenance line uses `(GitHub #161)` rather than `(archived 2026-09-13)` | Low | Accurate for an unarchived change and consistent with in-flight precedents (`mcp-server/spec.md` uses `(closes #154)` / `(closes #155)`); normalize at archive time if the repo prefers the archived form |
| `V-01`'s stdout clause is covered only by the post-verify follow-up test (`test_interpolated_stdout_value_strict_cp1252`) | Low | Recorded here so archive/review sees the final state; the frozen `verify-report.md` still carries the pre-follow-up wording by design |
| PB-02's "run on the ubuntu CI matrix" clause | Low (delivery, not sync) | Verify report §9.2 records that only the local cp1252 equivalent was executed; CI will exercise it on the ubuntu matrix |
| Uncommitted trees on `fix/161-cli-console-encoding` | Medium (for archive, not sync) | Parent-owned; this phase did not commit |

## 12. Change-directory status

The change directory remains **active** at
`openspec/changes/2026-09-13-fix-cli-console-encoding/` with its frozen artifacts
(`proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, both deltas) untouched;
only `sync-report.md` was added by this phase. The change is now **ready for `sdd-archive`**.
