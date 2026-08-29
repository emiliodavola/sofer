```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:1764c7bd863ef5c8daff80d50f4158367118e149605531a1eca198f1c2a96b9d
verdict: fail
blockers: 0
critical_findings: 1
requirements: 0/1
scenarios: 0/3
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:400f0724d4c867e595240fe77beaf66e93be3596d7b6c3d86731f456a6a036cb
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:394f9a8f812886c3c864e84a3513c8f2fdee340c3c59e60bb63bbb001be2ef6e
```

## Verification Report

**Change**: readme-overhaul-es — PR1 slice (tasks 1.1–1.4, bug fixes)
**Version**: spec delta v1 (tool-config TC-09)
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `strict_tdd: false`)
**Branch**: `docs/readme-overhaul-es` (off `dev`), commit `5923838`
**Scope note**: PR2/PR3/PR4 are intentionally NOT implemented (feature-branch chain, PR1 of 4). Their absence is expected and does not fail PR1 verification; it fails change-level archive readiness (envelope verdict `fail`, `requirements: 0/1`, `scenarios: 0/3` — "valid and persistable but not archive-ready" per the report contract). The PR1 slice itself passes all checks below.

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total (PR1 slice) | 4 |
| Tasks complete | 4 |
| Tasks incomplete (PR1 slice) | 0 |
| Change-wide tasks | 24 total, 20 incomplete (PR2–PR4 — expected by design) |

### Build & Tests Execution

**Build**: ✅ Passed (exit 0)
```text
uv run ruff check src/ tests/ && uv run mypy src/
All checks passed!
Success: no issues found in 26 source files
```

**Tests**: ✅ 886 passed / 0 failed / ⚠️ 2 skipped (13 warnings, 13.91s)
```text
uv run pytest tests/ -q
886 passed, 2 skipped, 13 warnings in 13.91s
```

**Coverage**: ➖ Not available (no coverage tooling configured — `openspec/config.yaml` `coverage.available: false`)

The 886-passed / 2-skipped result exactly matches the PR1 baseline recorded in `apply-progress.md` (task 1.4) and exceeds the 795 baseline cited in `tasks.md` (suite has grown since that note was written — no regression; code untouched by PR1).

### Spec Compliance Matrix

All three TC-09 scenarios target the PR2 `docs/configuration.md` extraction. PR1 neither implements nor regresses them.

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| TC-09 README documents discovery rules | Docs cover precedence and maintainer shift | (none — `docs/configuration.md` does not exist until PR2) | ⏳ PENDING BY DESIGN (PR2) |
| TC-09 README documents discovery rules | README points to the authoritative reference | (none — deep `[tool.sofer]` reference still lives in README L199-277 until PR2) | ⏳ PENDING BY DESIGN (PR2) |
| TC-09 README documents discovery rules | SOFER_VERBOSE pointer survives extraction | (none — pointer at README L245 intact; full explanation still in README until PR2) | ⏳ PENDING BY DESIGN (PR2) |

**Compliance summary**: 0/3 scenarios compliant in this slice — all PR2-pending by design; no scenario REGRESSED. Per design §Testing Strategy, docs scenarios are verified by manual/scripted checks (AGENTS.md rule 6 maps to verification, not pytest), so the absence of a pytest covering test is not a defect.

### Correctness (Static Evidence — PR1 tasks)

| Task | Status | Notes |
|------|--------|-------|
| 1.1 Spanish key principle → English | ✅ Implemented | README L36: `- **Automate observations; don't invent semantic knowledge.**` — English, kept in the surrounding `- **Principle.** explanation` list style. No other Spanish remnant in the Key principles list. |
| 1.2 Dedupe ×2 | ✅ Implemented | Exactly ONE canonical "Behavior change for editable installs" blockquote (L224-228) and ONE "Every value has a sensible default — the whole section is optional." line (L201-202). `rg` for `Release note|editable install|sensible default` confirms no duplicate remains. |
| 1.3 Rot-proof install note | ✅ Implemented | README L12-14: "Install it from the git tag of the release you want." — `rg -i "pypi"` returns 0 matches; no negative/rot-prone claim. Git-tag path intact (`uv tool install git+…@vX.Y.Z`, `pip install git+…@vX.Y.Z`) and truthful with the tag-driven release flow (AGENTS.md rule 12): L23-24 "`sofer --version` always matches the release tag". |
| 1.4 Tests green | ✅ Verified at runtime | `uv run pytest tests/ -q` → 886 passed, 2 skipped (exit 0). |

### No-Content-Loss Audit (diff `5923838` → README.md)

| Hunk | Removed | Added | Verdict |
|------|---------|-------|---------|
| Install (L9) | 3 lines — stale "not published on PyPI yet" claim | 3 lines — rot-proof git-tag wording | ✅ In scope (task 1.3) |
| Why / Key principles (L33) | 1 line — Spanish principle | 1 line — English principle | ✅ In scope (task 1.1) |
| Tool-wide config (L276) | 7 lines — duplicate "Release note" blockquote (4) + blank + duplicate "sensible default" line + blank | — | ✅ In scope (task 1.2) |

`git show 5923838 --numstat -- README.md` → **4 insertions / 11 deletions** — exactly the expected shape. Everything removed was duplicated or stale; the deep `[tool.sofer]` reference, precedence walk, bootstrap-key caveat, `SOFER_VERBOSE` pointer, and `## Command reference` are all intact. README is 494 lines (501 − 11 + 4), matching apply-progress.

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| PR1 = bug fixes only (design §Delivery Slicing) | ✅ Yes | Single-file README diff (4+/11-) plus SDD artifacts (tasks.md, apply-progress.md) in the same commit. |
| No-content-loss + dedupe ("Moves out" section) | ✅ Yes | Canonical copies retained in place for PR2 extraction; removed blocks were exact duplicates in meaning. |
| Canonical editable-install copy = "Behavior change for editable installs" blockquote | ✅ Yes | Retained at L224-228; matches apply-progress claim (L224-228 / L201-202). |
| git-tag install wording (AGENTS.md rule 12, "no rot-prone negative") | ✅ Yes | Wording truthful and future-proof: directs reader to check current tags/releases. |
| Keep Key principles verbatim (design: "Key principles kept verbatim" + L36 fix) | ✅ Yes | Only the single Spanish line changed; the rest of the list untouched. |

### Issues Found

**CRITICAL**:
- Change incomplete by design: 20/24 tasks pending (PR2–PR4) and TC-09 spec compliance 0/3 — expected for the PR1 slice, but it blocks archive readiness. Unblocked by `apply` (PR2). (Envelope `critical_findings: 1` / `verdict: fail` is the routing signal for "not archive-ready", NOT a PR1 defect.)

**WARNING**: None

**SUGGESTION**:
- `tasks.md` task 1.4 verify text says "795 tests still pass" — the suite is now 886 passed (growth already documented in apply-progress). Cosmetic; refresh the number when tasks.md is next edited (e.g. during PR2 planning).
- `apply-progress.md` "Issues found" references a "README is 388 lines" forecast claim that does not appear in the current `tasks.md` forecast table — internally inconsistent narrative; harmless, can be dropped or corrected in the next apply-progress update.

### Verdict

**FAIL (archive-readiness gate) — PR1 slice PASSES**: tasks 1.1–1.4 fully implemented and verified with runtime evidence (886 passed / 2 skipped; ruff + mypy clean; diff exactly 4+/11- with zero content loss; no spec scenario regressed). The envelope verdict is `fail` because the change-level evidence is intentionally incomplete (TC-09 0/3, 20/24 tasks — PR2–PR4), which is the canonical "valid and persistable but not archive-ready" state per the report contract. Next step: `apply` for PR2.

---

## PR2 Verification Report (slice 2 of 4 — restructure + extraction, tasks 2.1–2.7)

```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9b45aed68c72f7b5ef23806e0c25582bb12ad0f2b8b1ae0dac98b81cfaf4fd13
verdict: fail
blockers: 0
critical_findings: 1
requirements: 1/1
scenarios: 3/3
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:d019185c206b27fb3a0cc8bcf05dcb5a99af4daf759b844482a0a99214e4c9d2
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:394f9a8f812886c3c864e84a3513c8f2fdee340c3c59e60bb63bbb001be2ef6e
```

**Change**: readme-overhaul-es — PR2 slice (tasks 2.1–2.7, restructure + extraction)
**Version**: spec delta v1 (tool-config TC-09)
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `strict_tdd: false`)
**Branch**: `docs/readme-overhaul-es` (off `dev`), commits `1f81040` (2a restructure) + `d434b05` (2b extraction)
**Scope note**: PR3/PR4 are intentionally NOT implemented (feature-branch chain, PR2 of 4). Their absence is expected and does not fail PR2 verification; it keeps the change-level envelope verdict `fail` (not archive-ready). The PR2 slice itself passes all checks below — TC-09 is now 3/3 compliant.

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total (PR2 slice) | 7 |
| Tasks complete | 7 |
| Tasks incomplete (PR2 slice) | 0 |
| Change-wide tasks | 24 total, 13 incomplete (PR3 3.1–3.7, PR4 4.1–4.6 — expected by design) |

### Build & Tests Execution

**Build**: ✅ Passed (exit 0)
```text
uv run ruff check src/ tests/ && uv run mypy src/
All checks passed!
Success: no issues found in 26 source files
```
Build output byte-identical to the PR1 baseline (same `build_output_hash` `394f9a8f…`) — no code touched.

**Tests**: ✅ 886 passed / 0 failed / ⚠️ 2 skipped (13 warnings, 14.65s)
```text
uv run pytest tests/ -q
886 passed, 2 skipped, 13 warnings in 14.65s
```
Exactly matches the baseline recorded in `apply-progress.md` — no regression.

**Coverage**: ➖ Not available (no coverage tooling configured — `openspec/config.yaml` `coverage.available: false`)

### Spec Compliance Matrix

Per design §Testing Strategy, docs scenarios are verified by manual/scripted checks (AGENTS.md rule 6 maps to verification, not pytest) — static evidence below is the covering check.

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| TC-09 README documents discovery rules | Docs cover precedence and maintainer shift | Scripted: `docs/configuration.md` contains the 3-step precedence walk (dataset dir → cwd → defaults, L8–24), the cwd-only bootstrap-key caveat (`## Bootstrap keys (cwd-only)`, L32–43), and the editable-install behavior note (blockquote L26–30) | ✅ COMPLIANT |
| TC-09 README documents discovery rules | README points to the authoritative reference | Scripted: README `## Configuration` (L404–417) carries a summary + link to `docs/configuration.md#discovery-and-precedence`; deep-ref markers (`### Tool-wide configuration`, `#### …`) absent from README (0 occurrences) | ✅ COMPLIANT |
| TC-09 README documents discovery rules | SOFER_VERBOSE pointer survives extraction | Scripted: README L415–417 keeps the one-line `Set SOFER_VERBOSE=1 …` pointer linking to `docs/configuration.md#seeing-which-file-was-used` | ✅ COMPLIANT |

**Compliance summary**: 3/3 scenarios compliant — TC-09 fully satisfied by PR2.

### Correctness (Static Evidence — PR2 tasks)

| Task | Status | Notes |
|------|--------|-------|
| 2.1 TOC | ✅ Implemented | 15 flat bullets, fence-aware slug check: **0 unresolved anchors**. PR3 subsection bullets (Flags at a glance / Parquet conversion limitations / Verify the built package) correctly NOT in the TOC — their sections are PR3 content; task 2.1's "every anchor resolves" gate satisfied. |
| 2.2 Reorder + Quick start | ✅ Implemented | H2 order matches design spine exactly: Install → Quick start → Why → Typical workflow → TOML reference → Directory layout → Profiling and rendering → Command reference → Data format support → Validation and quality checks → Codebook generation → AI and MCP server → Configuration → Architecture summary → Related (Split detection is PR3, absent by design). Quick start = 5-command happy path (init→scan→prepare→publish) + Typical-workflow pointer. |
| 2.3 Heading renames | ✅ Implemented | 4 renames (design D2 + tree): `Profiling and rendering`, `Semantic types and PII detection`, `Validation and quality checks`, `AI and MCP server`. **0 double-hyphen slugs** among 28 real headings (fence-aware GitHub slug rule). |
| 2.4 docs/configuration.md | ✅ Implemented | Deep-ref body (69 non-heading lines from old README `### Tool-wide configuration`) — **0 missing**; 4 pinned `##` headings present with clean anchors (`#discovery-and-precedence`, `#bootstrap-keys-cwd-only`, `#seeing-which-file-was-used`, `#metadata-inference-tuning`); single canonical copies of the PR1-deduped items (sensible-default ×1, editable-install ×1, 0 in README). |
| 2.5 Configuration summary | ✅ Implemented | README deep reference removed (0 leftover markers); `## Configuration` summary = precedence one-liner + authoritative link + one-line `SOFER_VERBOSE` pointer with destination anchor. TC-09 scenarios 1–3 all satisfied. |
| 2.6 CONTRIBUTING extensions | ✅ Implemented | `Development setup` (merged env steps, Getting-started step 3 points to it), `Development commands` (3 commands), `Architecture` (25-line module tree verbatim + 2-line orientation). Existing content preserved: 29 old non-heading lines, only 1 intentionally reworded (`3. Set up the environment:` → pointer, documented deviation #4). |
| 2.7 Architecture summary | ✅ Implemented | `## Architecture summary` (3 lines) + links to `CONTRIBUTING.md#architecture` and `CONTRIBUTING.md`; no leftover `## Architecture` / `## Development setup` / `## Development` in README. |

### No-Content-Loss Audit (diff `1f81040` + `d434b05` vs `5923838`)

Line-set diff of README@5923838 (494 lines) against current README + docs/configuration.md + CONTRIBUTING.md:

| Metric | Result |
|--------|--------|
| Old README non-heading lines | 318 — **0 missing** across the three current files |
| Old README heading slugs (32) | 7 not found verbatim — ALL are D2/design renames to clean anchors (see below) |
| Deep-ref body → docs/configuration.md | 69/69 lines present (0 missing) |
| CONTRIBUTING old lines | 29 — 1 gone, intentional step-3 pointer reword (deviation #4) |

Renamed-slug reconciliation (every missing slug has a replacement anchor):
`ai--mcp-server` → `ai-and-mcp-server`; `profiling--rendering-metadata-workflow` → `profiling-and-rendering`; `semantic-types--pii-detection` → `semantic-types-and-pii-detection`; `validation--quality-checks-automatic` → `validation-and-quality-checks`; `where-sofer-looks-for-it-discovery--precedence` → `discovery-and-precedence`; `bootstrap-keys-cwd-only-until-a-dataset-config-loads` → `bootstrap-keys-cwd-only`; `development` → `development-commands` (CONTRIBUTING).

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D2 heading renames (drop `&`/`/`/parens) | ✅ Yes | 4 renames, matching design's own target tree (incl. `AI and MCP server`); 0 `--` slugs |
| Design spine (README target structure) | ✅ Yes | H2 order matches; Split detection deferred to PR3 per tasks.md 3.5 |
| docs/configuration.md pinned structure | ✅ Yes | H1 + 4 pinned `##` headings + intro + canonical copies — matches design tree |
| CONTRIBUTING.md extended structure | ✅ Yes | Development setup / Development commands / Architecture added; existing sections kept |
| README Configuration + Architecture summary | ✅ Yes | Summary forms match design (precedence one-liner, links, verbosity pointer) |
| TOC format (flat bullets) | ✅ Yes | `- [Install](#install)` style, top-level only in PR2 (subsection bullets land in PR3) |
| Deviations recorded in apply-progress | ✅ Yes | 4 documented, none block: TOC subsection bullets → PR3; badges placeholder (D7); CONTRIBUTING PR sync bullet → PR4; Getting-started step 3 pointer |

### Issues Found

**CRITICAL**:
- None for the PR2 slice. (Change-level: 13/24 tasks pending PR3/PR4 and the change is not archive-ready — expected for slice 2 of 4; envelope `critical_findings: 1` / `verdict: fail` is the routing signal, NOT a PR2 defect.)

**WARNING**: None

**SUGGESTION**:
- Missing trailing newline at EOF in all three touched markdown files (`README.md`, `docs/configuration.md`, `CONTRIBUTING.md`) — POSIX text-file convention; pre-commit hooks (ruff/mypy, `types: [python]`) do not cover `.md`, so nothing breaks. Cosmetic.
- `tasks.md` still cites stale line counts (388/501) and a 795-test baseline; authoritative numbers are 462-line README / 886 passed. Refresh when tasks.md is next edited (PR3 planning).
- PR3 carry-forward is now mandatory, not optional: the 3 TOC subsection bullets (`Flags at a glance`, `Parquet conversion limitations`, `Verify the built package`) must be added in the same commit as their sections, or the design's final-state TOC is never reached.

### Verdict

**FAIL (archive-readiness gate) — PR2 slice PASSES**: tasks 2.1–2.7 fully implemented and verified with runtime evidence (886 passed / 2 skipped; ruff + mypy clean, byte-identical to baseline; 318/318 old README lines preserved, 69/69 deep-ref lines in docs/configuration.md; 15/15 TOC anchors resolve; 0 `--` slugs; TC-09 3/3 compliant). The envelope verdict stays `fail` because the change is not archive-ready until PR3/PR4 land (canonical "valid and persistable but not archive-ready" state). Next step: `apply` for PR3.
---

```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9ab617e39a89df782ee23464c79d9a8cdf5c766922bab00bf37b9f96916e456c
verdict: fail
blockers: 0
critical_findings: 1
requirements: 1/1
scenarios: 1/1
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:1f9d20f6b370bb152775d8c3abacb99994d20243f260b6c3549d3854e38cc5e5
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:394f9a8f812886c3c864e84a3513c8f2fdee340c3c59e60bb63bbb001be2ef6e
```

## PR3 Verification Report (slice 3 of 4 — feature documentation, tasks 3.1–3.7)

**Change**: readme-overhaul-es — PR3 slice (tasks 3.1–3.7, feature documentation)
**Version**: spec delta v1 (tool-config TC-09) + parquet-conversion spec §7.2 interaction
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `strict_tdd: false`)
**Branch**: `docs/readme-overhaul-es` (off `dev`), commits `1c28dc9` + `e3d1ddf` + `adb3f67`
**Scope note**: PR4 is intentionally NOT implemented (feature-branch chain, PR3 of 4). Its absence is expected and does not fail PR3 verification; it keeps the change-level envelope verdict `fail` (not archive-ready). The PR3 slice itself passes all checks below — every task 3.1–3.7 is implemented and verified with source + runtime evidence.

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total (PR3 slice) | 7 |
| Tasks complete | 7 |
| Tasks incomplete (PR3 slice) | 0 |
| Change-wide tasks | 24 total, 6 incomplete (PR4 4.1–4.6 — expected by design) |

### Build & Tests Execution

**Build**: ✅ Passed (exit 0)
```text
uv run ruff check src/ tests/ && uv run mypy src/
All checks passed!
Success: no issues found in 26 source files
```
Build output byte-identical to the PR1/PR2 baseline (same `build_output_hash` `394f9a8f…`) — no code touched by the PR3 slice.

**Tests**: ✅ 886 passed / 0 failed / ⚠️ 2 skipped (13 warnings, 14.30s)
```text
uv run pytest tests/ -q
886 passed, 2 skipped, 13 warnings in 14.30s
```
Exactly matches the baseline recorded in `apply-progress.md` (task 1.4 / PR3 evidence) — no regression.

**Coverage**: ➖ Not available (no coverage tooling configured — `openspec/config.yaml` `coverage.available: false`)

### Spec Compliance Matrix

Per design §Testing Strategy, docs scenarios are verified by manual/scripted checks (AGENTS.md rule 6 maps to verification, not pytest); the underlying code behavior IS pytest-covered (`tests/test_splits.py`, `tests/test_cli.py`, `tests/test_parquet_conversion.py`), which anchors the documented facts.

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| parquet-conversion §7.2 — limitations SHALL be documented in the project README | Comma-as-decimal gap documented | Scripted: README `### Parquet conversion limitations` table row `Comma as decimal separator (3,14)` with workaround `Use a non-comma csv_delimiter in the TOML` (README L283) | ✅ COMPLIANT |
| parquet-conversion §7.2 — limitations SHALL be documented in the project README | Mixed-type >50 % gap documented | Scripted: README row `Mixed-type column, >50 % numeric-looking with some text` with workaround `Clean the column or accept the string type` (README L284) | ✅ COMPLIANT |
| parquet-conversion §7.2 — limitations SHALL be documented in the project README | >2 GB string gap documented | Scripted: README row `Extremely long string fields (>2 GB)` with workaround `Split the file or trim the field` (README L285) | ✅ COMPLIANT |
| TC-09 (PR2, regression check) | README still points to the authoritative reference | Scripted: `## Configuration` summary + `docs/configuration.md#discovery-and-precedence` link intact; no deep `[tool.sofer]` reference re-introduced by PR3 | ✅ COMPLIANT (no regression) |

**Compliance summary**: 3/3 §7.2 gap scenarios compliant; TC-09 remains 3/3 from PR2 with no PR3 regression. Deviation #5 (fallback wording modernized to the prepare/publish flow) judged **acceptable** — see Coherence.

### Correctness (Static Evidence — PR3 tasks)

| Task | Status | Notes |
|------|--------|-------|
| 3.1 `sofer-mcp` row | ✅ Implemented | README L250: `\| sofer-mcp \| Launch the MCP server over stdio (10 tools, 3 resources, 3 prompts). Requires the mcp extra — see AI and MCP server. \|` — **verbatim** vs design carry-forward #1. Separate console-script entry point confirmed in `pyproject.toml` `[project.scripts]` L41: `sofer-mcp = "sofer.mcp_server:main"`; no `<args>` placeholder. `sofer upload`-removal note (L252-253) kept. Row facts cross-checked: `_register_tools` registers exactly 10 tools (mcp_server.py L1116-1127); `mcp = ["fastmcp>=3.4,<4"]` extra exists (pyproject L37). |
| 3.2 Flags at a glance | ✅ Implemented | All 5 rows verified against `cli.py` `_build_parser` (L446-740): `--keep-csv` → publish parser only, help "(hf target only)" (L570-574) — matches "no effect with `--target local`"; `--no-checks` → prepare parser, help "Skip the structural and quality validation report" (L509-516), wired `run_checks=not args.no_checks` (cli.py L117); `--force` → prepare (L517-521, "Overwrite existing generated artifacts"), publish (L565-569, "Skip overwrite protection… unconditionally" — also skips the per-file confirmation prompt, publish.py `_check_overwrite_protection` L302-303), scan (L726-730, "Overwrite existing files in cache/"); `--dry-run` → publish (L575-579, "without preparing or uploading"), scan (L721-725, "without modifying the disk or TOML"); `--output DIR` → prepare (L500-503), publish (L557-564), profile (L650-653), render (L676-679) — all four accept `--output`, default locations match the glossary. Design carry-forward command list followed verbatim. |
| 3.3 Data format table | ✅ Implemented | Rows = `SUPPORTED_FORMATS` keys exactly (`.csv/.tsv/.parquet/.xlsx/.jsonl`, `_formats.py` L10-16); `scan`/`codebook`/`profile` supports confirmed via cli.py helps (`--ext` choices = `SUPPORTED_FORMATS.keys()` L734; codebook/profile "CSV, TSV, Parquet, Excel, or JSON Lines"). `prepare`/`publish` columns + footnote verified against prepare.py conversion loop (L660-711): CSV → Parquet unless `upload_as_csv` (L675-677, `_convert_to_parquet` L270-327); every other format staged as-is (step 7, L768-775); `publish` delivers the prepared package unchanged (publish.py upload-folder flow). Footnote claim `upload_as_csv = true` verified (model.py L71, L370). |
| 3.4 Parquet conversion limitations | ✅ Implemented | Section under `## Data format support` (design D6) at README L277-285. The three §7.2 gaps documented in a pattern/workaround table — comma-as-decimal, mixed-type >50 %, >2 GB strings — each with the spec's workaround, verbatim-in-spirit (spec §7.2 L305-313). Fallback wording modernized to the current prepare flow: "prepare prints a warning and stages the original CSV instead" — verified against prepare.py `_convert_to_parquet` failure path (L323-326: warning printed, returns `None`) + step 7 staging of non-converted files (L768-775). Deviation #5 acceptable (see Coherence). |
| 3.5 Split detection | ✅ Implemented | README L287-300 vs `splits.py`: keywords `train/training`, `validation/valid/val/dev`, `test/testing/eval/evaluation` = `_SPLIT_KEYWORDS` (L23-27) exactly; delimiting rule `test-file.csv` ✅ / `testfile.csv` ❌ with `-`, `_`, `.`, whitespace = `re.split(r"[_\-\s.]+", …)` (L89); cascade directory → filename → shard (≥2 distinct splits) → single-train fallback = `detect_splits` (L205-251) + `_detect_shard_splits` ≥2 gate (L182-183); exclusions README.md/LICENSE/.gitattributes/.gitignore = `_EXCLUDED_FILES` (L195-202); unclassified reporting (SplitReport.unclassified); HF-viewer `train` requirement = `validate_layout` warning (L274-281). Underlying behavior pytest-covered (`tests/test_splits.py`: TestDetectSplitsDirectory.test_directory_wins_over_filename, TestDetectSplitsShard.test_shard_pattern_needs_two_splits, keyword tests). |
| 3.6 Verify the built package | ✅ Implemented | Subsection under `Validation and quality checks` (design D4) at README L330-345 vs `verification.py` + `cli.py` + `prepare.py`: end-to-end `datasets.load_dataset()` on the output dir (verification.py L87, module docstring "the canonical test that a user calling load_dataset('user/repo') will succeed"); SKIPPED when optional `datasets` absent with `pip install datasets` hint (L65-75 + `_print_verification_report` L126-130); PASSED/FAILED with split comparison (L105-121, `passed = len(errors) == 0 and len(warnings) == 0`); non-blocking — prepare.py step 10 (L800-803) never changes the return code (PRP-08); cli.py `--verify` help "print PASSED/FAILED (non-blocking)" (L522-529). |
| 3.7 Badges (optional bonus) | ✅ Implemented (adopted) | 3 badges at the D7 pinned position (under tagline, above TOC, README L10-12): CI `…/actions/workflows/ci.yml/badge.svg` — `.github/workflows/ci.yml` exists (verified), workflow `name: CI`, repo slug `emiliodavola/sofer` matches `pyproject.toml` `[project.urls] Homepage`; License `img.shields.io/github/license/emiliodavola/sofer` — LICENSE file exists (MIT text verified) + `license = "MIT"` (pyproject L7); Python `python-3.10%2B-3776AB` static badge — `requires-python = ">=3.10"` (pyproject L6). No invented/dead URLs; static (non-PyPI) badge chosen because sofer is unpublished (consistent with PR1's rot-proof install note). Live-HF-link + rendered-codebook bonuses correctly deferred. |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D4 `--verify` home = subsection of Validation and quality checks | ✅ Yes | `### Verify the built package (prepare --verify)` under `## Validation and quality checks` (README L330) |
| D6 Parquet limitations = subsection under Data format support | ✅ Yes | `### Parquet conversion limitations` at README L277, immediately after the format table |
| D7 Badges position (under tagline, above TOC), mirrored in ES in PR4 | ✅ Yes | README L10-12, exactly between the tagline/description and `## Table of Contents`; PR4 carry-forward to README_ES.md recorded in apply-progress |
| Carry-forward #1 `sofer-mcp` row verbatim | ✅ Yes | README L250 byte-identical to design text; upload-removal note kept |
| Carry-forward #2 flags glossary per-command semantics | ✅ Yes | All 5 rows match `cli.py` argparse; command list = design's (prepare/publish/profile/render) |
| TOC subsection bullets land with their sections (PR2 deviation #1 RESOLVED) | ✅ Yes | All 3 mandatory bullets (`#flags-at-a-glance`, `#parquet-conversion-limitations`, `#verify-the-built-package-prepare---verify`) present in TOC and as headings; 19/19 anchors resolve (fence-aware slug check) |
| Badges placeholder → real badges (PR2 deviation #2 RESOLVED) | ✅ Yes | 3 real badge URLs, each backed by an existing artifact (workflow file, LICENSE, requires-python) |
| Deviation #5 — §7.2 fallback wording modernized | ✅ Acceptable | The parquet-conversion spec's "upload as CSV" language predates the `upload` removal (prepare+publish split; README itself documents the removal). The current behavior — warning + stage the original CSV into the package as-is — IS the spec's "CSV-fallback path" in the current architecture (prepare.py L323-326 → L768-775). The three §7.2 gaps are documented verbatim-in-spirit; the README wording describes actual behavior. No spec violation; judged acceptable. |
| Deviation #6 — `--output` row omits `codebook` | ✅ Acceptable (noted) | `codebook --output` exists (cli.py L602-606) but is an output FILE path (default stdout), semantically different from the DIR semantics of the glossary's four commands; the design's carry-forward list is followed verbatim. Reviewer may extend the row. |

### Issues Found

**CRITICAL**:
- None for the PR3 slice. (Change-level: 6/24 tasks pending PR4 4.1–4.6 and the change is not archive-ready — expected for slice 3 of 4; envelope `critical_findings: 1` / `verdict: fail` is the routing signal, NOT a PR3 defect.)

**WARNING**: None

**SUGGESTION**:
- PR2's trailing-newline suggestion still applies to `README.md` (last byte `0x41` `'A'`, no EOF newline) — POSIX text-file convention, cosmetic, nothing enforces it for `.md`.
- `tasks.md` still cites stale README line counts (388/501) and a 795-test baseline; authoritative numbers are 493-line README / 886 passed. Refresh when tasks.md is next edited (PR4 planning).
- `prepare.py` L324 prints "conversion failed — uploading as CSV" — uploader-era phrasing that survives inside the code message while the README correctly says "stages the original CSV". Out of scope for this docs change; flag for a future code-message cleanup (cosmetic, user-visible only on conversion failure).
- PR4 MUST mirror the badge block (README L10-12) verbatim into `README_ES.md` — recorded as a hard carry-forward in apply-progress task 3.7.

### Verdict

**FAIL (archive-readiness gate) — PR3 slice PASSES**: tasks 3.1–3.7 fully implemented and verified with source + runtime evidence (886 passed / 2 skipped; ruff + mypy clean, byte-identical to baseline; 19/19 TOC anchors resolve including the triple-hyphen `#verify-the-built-package-prepare---verify`; all 3 mandatory subsection bullets in TOC and as headings; `sofer-mcp` row verbatim + entry point confirmed; all 5 flag rows match `cli.py`; split/verify/parquet sections trace to `splits.py`/`verification.py`/`prepare.py`; §7.2 3/3 gaps documented; badges real and backed by existing artifacts). The envelope verdict stays `fail` because the change is not archive-ready until PR4 lands (canonical "valid and persistable but not archive-ready" state). Next step: `apply` for PR4.

---

```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4942ea4346a0c1f41491f53c72ec20fd3da21ee47df99c51c97ccb8317cd9a99
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 3/3
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:4942ea4346a0c1f41491f53c72ec20fd3da21ee47df99c51c97ccb8317cd9a99
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:394f9a8f812886c3c864e84a3513c8f2fdee340c3c59e60bb63bbb001be2ef6e
```

## PR4 FINAL Verification Report (slice 4 of 4 — README_ES.md + sync policy; FULL change 24/24)

**Change**: readme-overhaul-es — FINAL full-change verification (tasks 1.1–4.6, all 24/24)
**Version**: spec delta v1 (tool-config TC-09) + parquet-conversion §7.2 interaction
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `strict_tdd: false`)
**Branch**: `docs/readme-overhaul-es` (off `dev`), commits `d39cc1e` (README_ES + switcher), `65ad281` (sync policy), `8453a37` (openspec artifacts); chain base `5923838` (PR1) → `1f81040`/`d434b05` (PR2) → `1c28dc9`/`e3d1ddf`/`adb3f67` (PR3)
**Scope note**: This is the FINAL gate. All 4 PR slices are implemented; the change is COMPLETE (24/24 tasks). Envelope verdict **pass** — zero CRITICAL findings — archive unblocked.

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total (change-wide) | 24 |
| Tasks complete | 24 |
| Tasks incomplete | 0 |
| PR1 (1.1–1.4) / PR2 (2.1–2.7) / PR3 (3.1–3.7) / PR4 (4.1–4.6) | 4 / 7 / 7 / 6 — all [x] |

### Build & Tests Execution

**Build**: ✅ Passed (exit 0)
```text
uv run ruff check src/ tests/ && uv run mypy src/
All checks passed!
Success: no issues found in 26 source files
```
Build output **byte-identical** to the PR1/PR2/PR3 baseline (same `build_output_hash` `394f9a8f…`) — the whole change is docs-only, zero code touched.

**Tests**: ✅ 886 passed / 0 failed / ⚠️ 2 skipped (13 warnings, 13.87s)
```text
uv run pytest tests/ -q
886 passed, 2 skipped, 13 warnings in 13.87s
```
Exactly the required count (886 passed, 2 skipped), unchanged across all four slices — no regression.

**Coverage**: ➖ Not available (no coverage tooling configured — `openspec/config.yaml` `coverage.available: false`)

### Spec Compliance Matrix (final, change-wide)

| Requirement | Scenario | Test (scripted/static per design §Testing Strategy) | Result |
|-------------|----------|------|--------|
| TC-09 README documents discovery rules | Docs cover precedence and maintainer shift | `docs/configuration.md`: 3-step precedence walk (dataset dir → cwd → defaults, L8–20), cwd-only bootstrap-key caveat (`## Bootstrap keys (cwd-only)`, L32–43), editable-install behavior note (blockquote L26–30, single canonical copy) | ✅ COMPLIANT |
| TC-09 README documents discovery rules | README points to the authoritative reference | README `## Configuration` (L467–480): summary + precedence one-liner (verified normalized) + link to `docs/configuration.md#discovery-and-precedence`; deep-ref markers absent — `### Tool-wide configuration` / `#### Bootstrap keys` / `Metadata inference tuning` / `default_config_name` = **0 occurrences** in README | ✅ COMPLIANT |
| TC-09 README documents discovery rules | SOFER_VERBOSE pointer survives extraction | README L478–480: one-line `Set SOFER_VERBOSE=1 …` pointer linking to `docs/configuration.md#seeing-which-file-was-used`; README_ES mirrors it (L519–521) with the same English anchor | ✅ COMPLIANT |
| parquet-conversion §7.2 (PR3 carry) | 3 gaps documented, no regression | `### Parquet conversion limitations` table (README L283–287) — comma-as-decimal, mixed-type >50 %, >2 GB — all three with workarounds; section also mirrored in README_ES (L291–302) | ✅ COMPLIANT (no regression) |

**Compliance summary**: 3/3 TC-09 + §7.2 carried — all compliant. No scenario regressed at any slice.

### Correctness (Static Evidence — all 24 tasks)

**PR1 — bug fixes (4/4)**

| Task | Status | Evidence |
|------|--------|----------|
| 1.1 English key principle | ✅ | README L84: `- **Automate observations; don't invent semantic knowledge.**`; `Automatizar observaciones` = 0 occurrences |
| 1.2 Dedupe ×2 | ✅ | "the whole section is optional" = 1 occurrence (README L470, summary); "Behavior change for editable installs" = 0 in README, **1 canonical** in docs/configuration.md L26 |
| 1.3 Rot-proof install | ✅ | README L40–42: "Install it from the git tag of the release you want" (normalized check); `(?i)pypi` = 0 matches |
| 1.4 Tests green | ✅ | 886 passed / 2 skipped (all 4 runs) |

**PR2 — restructure + extraction (7/7)**

| Task | Status | Evidence |
|------|--------|----------|
| 2.1 TOC | ✅ | 19 flat bullets (incl. the 3 PR3 subsections); **0 unresolved anchors** (GitHub-slug rule, both files) |
| 2.2 Reorder + Quick start | ✅ | H2 order = design spine **17/17 exact match** (verified programmatically); Quick start = 5-command happy path init→scan→prepare→publish |
| 2.3 Heading renames | ✅ | `Profiling and rendering`, `Semantic types and PII detection`, `Validation and quality checks`, `AI and MCP server`; **0 double-hyphen slugs** among 32 headings |
| 2.4 docs/configuration.md | ✅ | H1 + 4 pinned `##` headings + intro; 79 lines; single canonical copies (sensible-default ×1, editable-install ×1) |
| 2.5 Configuration summary | ✅ | Deep ref removed (0 markers); summary + authoritative link + verbosity pointer (TC-09 3/3, see matrix) |
| 2.6 CONTRIBUTING extensions | ✅ | Development setup (L12–20), Development commands (L22–30), Architecture (L32–64, 25-line module tree + orientation); existing sections preserved |
| 2.7 Architecture summary | ✅ | README L482–490: 3-line summary + links to `CONTRIBUTING.md#architecture` and `CONTRIBUTING.md` |

**PR3 — feature documentation (7/7)**

| Task | Status | Evidence |
|------|--------|----------|
| 3.1 sofer-mcp row | ✅ | README L252 + README_ES L264, **byte-identical** (Compare-Object); verbatim vs design carry-forward #1 (modulo the `sofer-mcp` backticks the design's table omitted); upload-removal note kept |
| 3.2 Flags at a glance | ✅ | 5-row glossary (README L259–265); all 5 rows verified against `cli.py` in the PR3 report; table **7/7 lines byte-identical** in ES (headers + 5 rows) |
| 3.3 Format columns | ✅ | `prepare`/`publish` columns + footnote (README L269–277); mirrored in ES (L281–289) with footnote prose translated, technical tokens English |
| 3.4 Parquet limitations | ✅ | README L279–287 + ES L291–302 (translated headers, English technical content) |
| 3.5 Split detection | ✅ | README L289–302 + ES L304–333 (Spanish prose, English keywords/commands) |
| 3.6 Verify the built package | ✅ | README L332–347 + ES L363–379; SKIPPED/PASSED/FAILED tokens English in both |
| 3.7 Badges | ✅ | 3 real badges (CI/License/Python) at D7 position; **byte-identical block** in both files (verified) |

**PR4 — README_ES + sync policy (6/6)**

| Task | Status | Evidence |
|------|--------|----------|
| 4.1 README_ES mirror (D1) | ✅ | Heading tree **32/32 identical** (fence-aware Compare-Object, same order/level); all **13 code-fence blocks byte-identical** (0 differing, comments included); prose neutral professional Spanish — 14 tú forms, **0 voseo** (the single `nombra` hit is the standard tú imperative, false positive); "technical docs are in English" note (ES L516–517) |
| 4.2 Switcher | ✅ | `**[English](README.md) \| [Español](README_ES.md)**` — **exactly 1 occurrence per file**, byte-identical, immediately after the H1 (verified by substring position) |
| 4.3 Carried rows | ✅ | sofer-mcp row + Flags-at-a-glance table byte-identical in ES (verified above) |
| 4.4 AGENTS.md rule 13 | ✅ | **Verbatim** vs design.md L99–106 (normalized Contains, both raw and CRLF-stripped) |
| 4.5 PR template item | ✅ | `.github/PULL_REQUEST_TEMPLATE.md` L48: `- [ ] README_ES.md updated if a translated README section changed` — directly after the README item (L47), before "Related issues linked" |
| 4.6 Final mirror + packaging | ✅ | Heading diff EMPTY (32/32); `pyproject.toml` `readme = "README.md"` unchanged, no README_ES reference; tests 886/2 |

### No-Content-Loss / No-Drift Audit (change-wide)

| Check | Result |
|--------|--------|
| PR1 fixes survived PR2–PR4 | ✅ English principle (L84), single sensible-default copy, rot-proof install — all verified above |
| PR2 extraction intact | ✅ 0 deep-ref markers in README; docs/configuration.md carries the full reference (TC-09 S1) |
| PR3 sections intact | ✅ All 5 sections present in README + mirrored in ES; 19/19 TOC anchors resolve in both files |
| PR4 didn't touch prior content | ✅ `d39cc1e` README diff = +2 lines only (switcher); 65ad281 = +7/+1/+1 policy lines |
| Total footprint vs dev | ✅ +864/−198 across 6 files (README_ES 536 new lines dominates); no code files in the diff |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 English headings / Spanish prose | ✅ Yes | 32/32 identical English heading tree; neutral tú prose; all technical tokens English |
| D2 clean heading anchors | ✅ Yes | 4 renames; 0 `--` slugs; 19/19 TOC anchors resolve |
| D5 sync policy (rule 13 + PR-template item) | ✅ Yes | Both verbatim; PR2 deviation #3 (CONTRIBUTING bullet) RESOLVED in PR4 — bullet present at CONTRIBUTING L91 |
| D7 badges mirrored in ES | ✅ Yes | Badge block byte-identical in both files |
| Switcher placement (after H1, before tagline) | ✅ Yes | Verified by substring position in both files |
| README_ES not referenced by pyproject | ✅ Yes | `readme = "README.md"` unchanged; packaging untouched |
| Chain boundaries (PR1→PR4) | ✅ Yes | 4 commits on `docs/readme-overhaul-es`; each slice's diff scoped to its work unit |

### Issues Found

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
- (Carried from PR2/PR3) Missing trailing newline at EOF in `README.md`, `README_ES.md`, `docs/configuration.md`, `CONTRIBUTING.md` (last byte is `)` or `` ` `` or `.`, not `\n`) — POSIX text-file convention; cosmetic, nothing enforces it for `.md`. `AGENTS.md` and `PULL_REQUEST_TEMPLATE.md` are fine.
- (Carried) `tasks.md` cites stale line counts (388/501) and a 795-test baseline; authoritative numbers are 495-line README / 536-line README_ES / 886 passed. Cosmetic; refresh if tasks.md is edited before archive.
- (Carried from PR3) `prepare.py` L324 prints "conversion failed — uploading as CSV" — uploader-era phrasing inside a code message while the README correctly documents "stages the original CSV". Out of scope for this docs change; flag for a future code-message cleanup.

### Verdict

**PASS — change COMPLETE and archive-ready.** All 24/24 tasks implemented and verified with runtime + scripted evidence: 886 passed / 2 skipped (unchanged across all 4 slices); ruff + mypy clean with build output byte-identical to baseline (zero code touched); TC-09 3/3 and §7.2 compliant; D1 mirror contract fully satisfied (32/32 headings, 19/19 TOC, 13/13 fence blocks, badge block, switcher ×1 per file — all byte-identical); sync policy (AGENTS.md rule 13, PR-template item, CONTRIBUTING bullet) verbatim per design; PR1 fixes, PR2 extraction, and PR3 sections all survived with zero drift. Zero CRITICAL findings — envelope verdict `pass` — **archive is unblocked**. Next step: `sdd-archive`.
