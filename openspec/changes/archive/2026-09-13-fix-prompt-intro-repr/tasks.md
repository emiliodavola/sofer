# Tasks: fix-prompt-intro-repr

Closes #169: the three MCP prompt-template **intro sentences** in
`src/sofer/mcp_server.py` interpolate caller-controlled `config`/`dataset`
arguments **raw** (`2987` prepare, `3017-3018` assess, `3042` finalize) while
every executable surface (canonical-chain line, numbered steps, copy-paste
block, per-arg positions) is `repr`-protected — the single place hostile text
can render as real instruction-shaped prose instead of escaped data
(LLM01-class prose-contamination surface). Fix = exactly three f-string token
swaps to `{config!r}` / `{dataset!r}` (4 physical lines; the assess intro is a
2-fragment f-string where BOTH fragments carry substitutions, the finalize
intro's second fragment is plain — only the f-string fragment changes) +
extend the #139 injection suite to assert intro-region containment
(`repr(payload)` present, raw `_INJECT_*` markers absent, physical line-count
equality vs benign render) + refresh the two #139 docstrings that recorded the
now-resolved known limitation (behavioral wording, no line refs). `output` is
never intro-interpolated — its containment stays asserted over the block only
(no vacuous assertion). Spec delta (`MODIFIED MSP-R08`, #139 limitation marked
RESOLVED, 11 scenarios 1:1 test-mapped) already written at the spec phase —
this file is the apply-phase plan. Strict TDD off (`config.yaml
strict_tdd: false`); tests follow the spec delta scenario mapping. Branch:
`fix/169-prompt-intro-repr`.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~93 total executable (−/+) — `src/sofer/mcp_server.py` 4 lines (3 intro token swaps), `tests/test_mcp_server.py` ~+81 / −12 (new `_prompt_intro` helper + 2 docstring refreshes + extended prepare probe + 3 new probes). Spec delta (~190 lines) was already written and reviewed at the spec phase; `tasks.md`/`verify.md` are SDD artifacts, not review load |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not needed — single PR; chaining deferred until selected) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

> Forecast math note (explicit, per parent instruction): raw total with docs
> (~93 executable + ~190 spec delta + ~60 tasks/verify) exceeds the canonical
> 400, but the line-by-line review load is the executable surface (~93,
> additions+deletions, inside the budget) — the spec delta was already reviewed
> at proposal, and tasks.md/verify.md are change artifacts. Same accounting as
> the archived fix-xlsx-staged-parquet-warning forecast (Low / single PR).
> Nothing changed this math → Low / single PR / Decision: No stand.

### Suggested Work Units

| Unit | Goal | Likely PR | Boundaries (start → finish · verify · rollback) |
| ------ | ------ | ----------- | ------------------------------------------------ |
| 1 | Baseline: `uv run pytest tests/ -q` — record actual collected/passed/skipped (measure; config.yaml counts are stale — expect ~1548/6, do not trust) | PR 1 | 1.1 · recorded baseline, 0 failures · no change to revert |
| 2 | Tests: `_prompt_intro` helper + `_prompt_block` docstring refresh + probe family (extend `test_prepare_dataset_intro_contract_scope`; add `test_assess_dataset_intro_contract_scope`, `test_finalize_payload_intro_contract_scope`, `test_prompts_no_raw_marker_across_templates`) in `tests/test_mcp_server.py` | PR 1 | 2.1 → 2.5 · probes 2.2-2.5 red against pre-fix source (RAWR intro) then green after unit 3 · `git revert` of the commit with unit 3 |
| 3 | Source fix: 3 intro token swaps in `src/sofer/mcp_server.py` (`2987`, `3017`, `3018`, `3042`) — the ONLY production diff | PR 1 | 3.1 → 3.2 · `git diff --stat src/sofer/` = 4 lines · single-commit `git revert` |
| 4 | Gates: full suite + ruff + ruff format + mypy + `git diff --check` + spec-δ/test 1:1 completeness | PR 1 | 4.1 → 4.6 · all green; baseline + 3 net-new tests · revert with units 2+3 |
| 5 | OpenSpec lifecycle: apply-progress, verify.md, canonical spec sync, archive, bounded review | PR 1 | 5.1 → 5.4 (parent-owned) · canonical `openspec/specs/mcp-server/spec.md` carries the resolved MSP-R08 · docs-only revert |

Out of scope boundaries to respect during units 2-3: do NOT touch
`_with_untrusted_note`, `_UNTRUSTED_NOTE`, tool descriptions, `instructions`,
README/README_ES/CLI (§13 not triggered — no user-facing contract change;
grep-verified no doc pins the intro sentences), and none of #142/#161/#162/

# 167. The merged #139 artifacts

(`openspec/changes/2026-09-13-test-mcp-injection-semantics/…`) are historical —
NOT edited. Any production diff larger than the 4 token lines is a scope
violation (proposal R5) and is rejected at apply/verify.

## Phase 1: Baseline

- [x] 1.1 Run the full suite on the current branch: `uv run pytest tests/ -q`; record the actual collected/passed/skipped counts (expect ~1548 passed / 6 skipped per handoff — **measure, do not trust** the stale `config.yaml` count of 1031 collected or other historical numbers). Baseline must be green before any edit. <!-- sdd-owner: implementation -->
  - **Evidence:** actual `uv run pytest tests/ -q` tail line with collected/passed/skipped counts recorded verbatim.

## Phase 2: Test helper + docstring refresh (`tests/test_mcp_server.py`)

- [x] 2.1 Add module-level `_prompt_intro(text)` immediately after `_prompt_block` (helper cluster ~L1890-1898): body exactly `return text[: text.index("Canonical chain:")]` — the complement of `_prompt_block` (which slices FROM the anchor), so `_prompt_intro(text) + _prompt_block(text)` partitions any full render exactly at the canonical-chain header. Docstring (AGENTS rule 2) documents: the partition contract, that the anchor's first occurrence is the unique chain header in all three templates, and that the helper is what the intro-contract probes assert on — no new literals, reuse the established `"Canonical chain:"` string (AGENTS rule 1). Untyped like its test-helper siblings (mypy runs on `src/` only). <!-- sdd-owner: implementation -->
  - **Evidence:** helper added; single `text.index("Canonical chain:")` literal shared with `_prompt_block` (no second literal).
- [x] 2.2 Refresh the `_prompt_block` docstring (~L1891-1897): REMOVE the raw-intro known-limitation sentence ("The intro sentence interpolates caller arguments raw — a known limitation tracked by issue #169 — and is deliberately excluded from strict checks") and the exclusion framing; describe behavior instead: the canonical-chain header marks the repr-protected executable surface (numbered steps, canonical-chain line, copy-paste block) the structural probes assert on, and the intro sentences are covered by `_prompt_intro` and the intro-contract probes (issue #169 resolved). NO absolute line refs (proposal R3 — the fix invalidates them). <!-- sdd-owner: implementation -->
  - **Evidence:** no "known limitation", "excluded from strict checks", or `2987`/`3017-3018`/`3042` wording remains in the docstring.

## Phase 3: Intro-contract probe family (`tests/test_mcp_server.py`, `TestPrompts`)

> Transient-RED note: probes 2.3-2.5 land BEFORE the source swap (design §8
> order), so their intro-region assertions fail against the pre-fix raw intro
> and go green only after unit 3 — expected under `strict_tdd: false`. The
> pre-existing BLOCK assertions inside the extended prepare probe must stay
> green throughout (they never touch the intro region).

- [x] 2.3 Extend `test_prepare_dataset_intro_contract_scope` (~L2295-2319): (a) refresh the docstring to the RESOLVED contract — role flips from "#169 scope guard" to "positive intro-containment check"; describe the intro by behavior, no line refs; (b) keep every existing block assertion byte-identical (`"\nCanonical chain:" in hostile`; 4 `_INJECT_*` markers absent from `_prompt_block`; `repr(...)` presence for `config`+`output` in the block; block line-count equality); (c) ADD intro assertions: `intro = _prompt_intro(hostile)`, `benign_intro = _prompt_intro(benign)` (benign = `{"config": _BENIGN_CONFIG, "output": _BENIGN_OUTPUT}`); assert `repr(_INJECT_ARGS_PREPARE["config"]) in intro`; each of `(_INJECT_PROSE, _INJECT_FAKE_STEP, _INJECT_FAKE_TOOL_CALL, _INJECT_ESCAPES)` `not in intro`; `len(intro.splitlines()) == len(benign_intro.splitlines())`. No `output` assertion in the intro (design D1 — `output` is never intro-interpolated). <!-- sdd-owner: implementation -->
  - **Evidence:** probe red before the fix (raw intro: `repr` absent, raw markers + extra physical lines present), green after; docstring contains no line refs.
- [x] 2.4 Add `test_assess_dataset_intro_contract_scope` (new flat sibling right after the prepare probe): render hostile (`_INJECT_ARGS_ASSESS`) + benign (`{"config": _BENIGN_CONFIG, "dataset": _BENIGN_DATASET}`); over `_prompt_intro`: assert `repr(_INJECT_ARGS_ASSESS["config"]) in intro` AND `repr(_INJECT_ARGS_ASSESS["dataset"]) in intro` (both intro args — the assess intro interpolates both fragments); all 4 `_INJECT_*` markers absent in intro; `len(intro.splitlines()) == len(benign_intro.splitlines())`. Docstring required (AGENTS rule 2); reuse module constants only. <!-- sdd-owner: implementation -->
  - **Evidence:** new test green after fix; covers spec scenario "assess_dataset intro repr-contains hostile dataset and config payloads".
- [x] 2.5 Add `test_finalize_payload_intro_contract_scope` (new flat sibling): render hostile (`_INJECT_ARGS_FINALIZE`) + benign (`{"config": _BENIGN_CONFIG, "output": _BENIGN_OUTPUT}`); over `_prompt_intro`: assert `repr(_INJECT_ARGS_FINALIZE["config"]) in intro`; all 4 `_INJECT_*` markers absent in intro; `len(intro.splitlines()) == len(benign_intro.splitlines())`. Explicitly NO `output`-in-intro assertion (design D1 — the finalize intro interpolates only `config`; `output` containment stays asserted over the block by the untouched `test_finalize_payload_arg_containment`). Docstring required. <!-- sdd-owner: implementation -->
  - **Evidence:** new test green after fix; covers spec scenario "finalize_and_publish intro repr-contains a hostile config payload".
- [x] 2.6 Add cross-template `test_prompts_no_raw_marker_across_templates` (new, zero-raw-scan): loop the three `(name, hostile_args, benign_args)` triples (`prepare_dataset`/`_INJECT_ARGS_PREPARE`, `assess_dataset`/`_INJECT_ARGS_ASSESS`, `finalize_and_publish`/`_INJECT_ARGS_FINALIZE` with the matching `_BENIGN_*` dicts); per template render hostile + benign and scan the **full** text: all 4 `_INJECT_*` markers absent verbatim, AND `len(text.splitlines()) == len(benign_text.splitlines())` — no raw payload newline starts a physical line anywhere in intro + block combined (the mechanical form of "no raw, non-`repr` interpolation remains"). Docstring required. <!-- sdd-owner: implementation -->
  - **Evidence:** new test green after fix; covers spec scenario "No raw caller-argument interpolation remains in any rendered prompt".

## Phase 4: Source fix — 3 intro tokens (`src/sofer/mcp_server.py`)

- [x] 3.1 Swap the three intro interpolation tokens exactly per design §3.1 (the ONLY production diff; verify each site by read before editing):
  1. `_prompt_prepare_dataset` intro (~2987): `{config}` → `{config!r}`
  2. `_prompt_assess_dataset` intro fragment 1 (~3017): `{dataset}` → `{dataset!r}`
  3. `_prompt_assess_dataset` intro fragment 2 (~3018): `{config}` → `{config!r}` (2-fragment f-string — BOTH fragments carry substitutions, both tokens change)
  4. `_prompt_finalize_and_publish` intro (~3042): `{config}` → `{config!r}` (f-string fragment + plain `"on Hugging Face Hub.\n"` fragment — only the f-string fragment changes)
  Zero other edits under `src/sofer/`: every other builder line stays byte-identical; `_with_untrusted_note`, `_UNTRUSTED_NOTE`, `output_repr` computation and its uses (numbered steps + copy-paste only) untouched. <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff --stat src/sofer/` = exactly 4 changed lines in `mcp_server.py`; no other file under `src/sofer/` in the diff.
- [x] 3.2 Confirm no ruff reflow required: longest new line (assess ~3017 with `{dataset!r}` ≈ 83 chars) stays under the repo's `line-length = 100` (`pyproject.toml:57`) → line numbers remain stable, no format churn from the fix itself. Commit guidance: land phases 2-4 as one commit (or tests-commit + fix-commit pair) so no pushed commit leaves the suite red; pre-commit hooks (ruff fix+format+mypy) run automatically — never `--no-verify` (AGENTS rule 5). <!-- sdd-owner: implementation -->
  - **Evidence:** `uv run ruff format --check src/sofer/mcp_server.py` reports the file formatted (no reflow of the 4 lines).

## Phase 5: Evidence gates

- [x] 4.1 Full suite: `uv run pytest tests/ -q` — passed count = baseline + 3 net-new tests (extended prepare probe is a modification, not new), 6 skipped preserved, zero failures. Record actual output, not placeholders. <!-- sdd-owner: implementation -->
  - **Evidence:** actual tail line (e.g. `1551 passed, 6 skipped`), plus targeted `-k` run of the 5 intro probes showing green.
- [x] 4.2 `uv run ruff check src/ tests/` clean. <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output.
- [x] 4.3 `uv run ruff format --check src/ tests/` clean (65 files already formatted; the 4 token swaps introduce no format delta). <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output.
- [x] 4.4 `uv run mypy src/` success (CI runs mypy under Python 3.13; do NOT add mypy to the version matrix per AGENTS rule 12). <!-- sdd-owner: implementation -->
  - **Evidence:** actual command output (`Success: no issues found in N source files`).
- [x] 4.5 `git diff --check` clean; confirm the diff surface: 4 source lines + ~+81/−12 test lines in `tests/test_mcp_server.py` only; no README/README_ES/CLI change; no change under `openspec/changes/2026-09-13-test-mcp-injection-semantics/`. <!-- sdd-owner: implementation -->
  - **Evidence:** `git diff --check` silent; `git diff --stat` matches the forecast.
- [x] 4.6 Spec-δ/test completeness check (AGENTS rule 6 / openspec specs rule): every scenario in the already-written MSP-R08 delta maps 1:1 — the six preserved #139 scenarios run unchanged and green; "Intro raw interpolation is resolved" + "prepare_dataset intro repr-contains" → extended 2.3; "assess_dataset intro repr-contains" → new 2.4; "finalize intro repr-contains" → new 2.5; "No raw caller-argument interpolation remains" → new 2.6. No scenario added without a test (and vice versa). <!-- sdd-owner: implementation -->
  - **Evidence:** acceptance mapping table below, cross-checked against the delta's informational comment.

Acceptance mapping (AGENTS rule 6) — MSP-R08 delta scenario → test:

| Scenario (delta) | Test | Status |
| --- | --- | --- |
| Prompt list shows 3 templates | existing `test_prompt_list_shows_three` | preserved, unchanged |
| Confirm-before-publish idiom enforced | existing `test_publish_prompt_mandates_approval_stop` | preserved, unchanged |
| Hostile payload cannot alter prepare/assess/finalize workflow (6 scenarios) | existing `test_{prepare_dataset,assess_dataset,finalize_payload}_{no_steps_added,arg_containment,canonical_order}` + `_approval_stop_intact` pair | preserved, unchanged |
| Intro raw interpolation is resolved + prepare_dataset intro repr-contains | **extended** `test_prepare_dataset_intro_contract_scope` (docstring refreshed; additive intro assertions) | extended |
| assess_dataset intro repr-contains | **new** `test_assess_dataset_intro_contract_scope` | new |
| finalize_and_publish intro repr-contains | **new** `test_finalize_payload_intro_contract_scope` | new |
| No raw caller-argument interpolation remains | **new** `test_prompts_no_raw_marker_across_templates` | new |

## Phase 6: OpenSpec lifecycle + bounded review (parent-owned, after implementation)

- [x] 5.1 Verify the change-local spec delta is in place and complete (`openspec/changes/2026-09-13-fix-prompt-intro-repr/specs/mcp-server/spec.md`: full-block MODIFIED MSP-R08; the #139 "known limitation" clause/scenario rewritten into the RESOLVED repr-intro contract with the `> (Previously: …)` lineage note; every pre-existing #139 scenario preserved byte-identical; 11 scenarios with the 1:1 test mapping comment); update apply-progress. <!-- sdd-owner: parent -->
- [x] 5.2 Populate `openspec/changes/2026-09-13-fix-prompt-intro-repr/verify-report.md` with the §5 gate results (actual command output, not placeholders). <!-- sdd-owner: parent -->
- [x] 5.3 Sync the delta into canonical `openspec/specs/mcp-server/spec.md` at archive merge (AGENTS rule 12 branch flow — lands on `dev`); README/README_ES intentionally untouched (§13 not triggered). Watch sibling active change `2026-09-12-fix-residual-parity` (mcp-server delta NEW MSP-R16/R17 — no overlap with MSP-R08, but respect archive merge ordering). <!-- sdd-owner: parent -->
- [x] 5.4 Post-apply bounded review of the PR diff (4 source tokens + test updates + docstring refreshes), then archive the change. Rollback = single-commit revert — production diff is 4 token lines; the #139 suite stays green in BOTH states because it never asserted the intro; spec delta supersedes only at its own archive merge. No migration, no config, no on-disk artifact, no destructive/publishing surface touched. <!-- sdd-owner: parent -->

## Follow-ups (out of scope, tracked)

- None blocking. Explicit non-goals preserved per proposal Scope: #142 (pi), #161
  (cp1252 help text), #162 (test hygiene / `_infer_type` deprecation warnings),
  #167 (`delegate_add` env) — no work in this change.
- Anchor-drift note (design §7.2): a future template edit that introduces a
  second `"Canonical chain:"` occurrence would shift `_prompt_intro` and
  `_prompt_block` identically (shared anchor literal) — no asymmetric drift;
  no action needed now.
