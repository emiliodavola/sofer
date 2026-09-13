# Apply Progress: fix-prompt-intro-repr

**Change**: `2026-09-13-fix-prompt-intro-repr` (GitHub #169)
**Branch**: `fix/169-prompt-intro-repr`
**Phase**: apply (implementation) — strict TDD off (`config.yaml strict_tdd: false`); tests-before-fix used with expected transient-RED, final state all-green.
**Status**: complete — all implementation-owned task rows `- [x]`; parent-owned rows (5.1–5.4) untouched, deferred to parent lifecycle.

---

## 1. Baseline (task 1.1)

Ran `uv run pytest tests/ -q` on the pristine branch before any edit — verbatim tail line:

```
1548 passed, 6 skipped, 13 warnings in 50.44s
```

That matches the handoff expectation (~1548/6). Measure confirmed the stale `config.yaml` count (1031 collected) was indeed stale. Baseline green before any edit.

## 2. Tasks completed and persisted checkbox updates

| Task | Outcome | Tasks.md persisted |
| --- | --- | --- |
| 1.1 | Baseline `1548 passed, 6 skipped` recorded | `- [x]` |
| 2.1 | `_prompt_intro(text)` added as module-level helper immediately after `_prompt_block` (`tests/test_mcp_server.py`); body `return text[: text.index("Canonical chain:")]`; docstring documents partition contract + unique anchor; single `"Canonical chain:"` literal shared with `_prompt_block` via `text.index` (verified: no second literal) | `- [x]` |
| 2.2 | `_prompt_block` docstring refreshed: raw-intro known-limitation sentence and exclusion framing removed; replaced with behavior description (canonical-chain header marks repr-protected executable surface; intros covered by `_prompt_intro` + intro-contract probes, #169 resolved). No line refs remain | `- [x]` |
| 2.3 | `test_prepare_dataset_intro_contract_scope` extended: docstring refreshed to RESOLVED contract (no line refs); all pre-existing block assertions kept byte-identical (`"\nCanonical chain:" in hostile`, 4 `_INJECT_*` markers absent from block, `repr(...)` for config+output in block, block line-count equality); ADDED intro assertions via `_prompt_intro`: `repr(config) in intro`, 4 markers absent from intro, `len(intro.splitlines()) == len(benign_intro.splitlines())`. No `output`-in-intro assertion (D1) | `- [x]` |
| 2.4 | `test_assess_dataset_intro_contract_scope` (new flat sibling): reprs of BOTH `config` and `dataset` present in intro (both fragments), 4 markers absent, intro line-count equality; docstring present | `- [x]` |
| 2.5 | `test_finalize_payload_intro_contract_scope` (new flat sibling): `repr(config)` in intro, 4 markers absent, intro line-count equality; explicitly NO `output`-in-intro assertion (D1); docstring present | `- [x]` |
| 2.6 | `test_prompts_no_raw_marker_across_templates` (new cross-template): loops all 3 `(name, hostile_args, benign_args)` triples; full-text scan — 4 markers absent verbatim + `len(text.splitlines()) == len(benign_text.splitlines())` per template; docstring present | `- [x]` |
| 3.1 | 3 intro tokens swapped in `src/sofer/mcp_server.py`: `2987` `{config}`→`{config!r}`; `3017` `{dataset}`→`{dataset!r}` AND `3018` `{config}`→`{config!r}` (2-fragment f-string, both change); `3042` `{config}`→`{config!r}`. Zero other source edits — `git diff --stat src/sofer/` = exactly **4 changed lines** (4 insertions + 4 deletions), one file | `- [x]` |
| 3.2 | No ruff reflow required: longest new line (assess `3017` with `{dataset!r}`) under line-length 100; `uv run ruff format --check src/ tests/` → all formatted (no churn from the fix itself) | `- [x]` |
| 4.1 | Full suite after fix: `1551 passed, 6 skipped, 13 warnings in 43.08s` — baseline + 3 net-new tests, 6 skipped preserved, zero failures | `- [x]` |
| 4.2 | `uv run ruff check src/ tests/` → `All checks passed!` | `- [x]` |
| 4.3 | `uv run ruff format --check src/ tests/` → `65 files already formatted` | `- [x]` |
| 4.4 | `uv run mypy src/` → `Success: no issues found in 32 source files` | `- [x]` |
| 4.5 | `git diff --check` → clean; diff surface = `src/sofer/mcp_server.py` (4 lines) + `tests/test_mcp_server.py` only; no README/README_ES/CLI change; no change under `openspec/changes/2026-09-13-test-mcp-injection-semantics/` | `- [x]` |
| 4.6 | Spec-δ/test 1:1 mapping verified (acceptance mapping table below) | `- [x]` |

### Acceptance mapping (AGENTS rule 6) — all scenarios have tests

| Scenario (MSP-R08 delta) | Test | Status |
| --- | --- | --- |
| Prompt list shows 3 templates | `test_prompt_list_shows_three` | preserved, unchanged |
| Confirm-before-publish idiom enforced | `test_publish_prompt_mandates_approval_stop` | preserved, unchanged |
| Hostile payload cannot alter prepare/assess/finalize workflow (6 scenarios) | existing `test_{prepare_dataset,assess_dataset,finalize_payload}_{no_steps_added,arg_containment,canonical_order}` + `_approval_stop_intact` pair | preserved, unchanged (all green in full suite) |
| Intro raw interpolation is resolved + prepare_dataset intro repr-contains | **extended** `test_prepare_dataset_intro_contract_scope` | extended |
| assess_dataset intro repr-contains | **new** `test_assess_dataset_intro_contract_scope` | new |
| finalize_and_publish intro repr-contains | **new** `test_finalize_payload_intro_contract_scope` | new |
| No raw caller-argument interpolation remains | **new** `test_prompts_no_raw_marker_across_templates` | new |

## 3. Files changed

| File | Change | Delta |
| --- | --- | --- |
| `src/sofer/mcp_server.py` | 3 intro interpolation tokens → `!r` (`2987`, `3017`, `3018`, `3042`); no other line | 4 lines (4 +/−) |
| `tests/test_mcp_server.py` | new `_prompt_intro` helper; refreshed `_prompt_block` + prepare probe docstrings (13 stale lines removed); extended prepare probe (additive); +3 new probes | +116 / −13 (forecast ~+81/−12 — deviation noted below) |
| `openspec/changes/2026-09-13-fix-prompt-intro-repr/specs/mcp-server/spec.md` | already written at spec phase (not edited at apply) | — |
| `openspec/changes/2026-09-13-fix-prompt-intro-repr/tasks.md` | implementation checkboxes marked `- [x]` | — |

## 4. Evidence gates (actual outputs)

- **Full suite (final)**: `1551 passed, 6 skipped, 13 warnings in 43.08s` (tail line verbatim)
- **Targeted intro probes**: `uv run pytest tests/test_mcp_server.py -k "intro_contract_scope or no_raw_marker_across or test_prompt_arguments_substituted" -q` → `5 passed, 241 deselected` (4 intro probes + the D6 backward-compat bare-substring probe all green)
- **Transient-RED evidence** (probes against pre-fix source, design §8 order): `4 failed` — the 3 new probes + extended prepare intro assertions fail on the raw intro before the token swap, go green after. Block assertions stayed green throughout.
- **ruff check**: `All checks passed!`
- **ruff format --check**: `65 files already formatted`
- **mypy src/**: `Success: no issues found in 32 source files`
- **git diff --check**: clean
- **git diff --stat**:

  ```
   src/sofer/mcp_server.py  |   8 +--
   tests/test_mcp_server.py | 127 ++++++++++++++++++++++++++++++++++++++++++-----
   2 files changed, 119 insertions(+), 16 deletions(-)
  ```

- **git diff --stat src/sofer/**: `1 file changed, 4 insertions(+), 4 deletions(-)` — exactly the 4 token lines.

## 5. Deviations from design

1. **Test-file delta slightly larger than forecast** (~+116/−13 vs ~+81/−12). Cause: (a) the cross-template probe's triple-loop tuples and marker loops are wrapped across lines (ruff line-length=100 compliance — E501 is enforced by this repo's ruff config, so the flat one-line tuples in the design sketch would have failed `ruff check`); (b) two of the docstrings are a line longer than sketched for clarity. Functionally identical to the design; no production-code deviation.
2. **`uv run pytest` mutated `pyproject.toml` + `uv.lock` during the baseline run** (added `coverage>=7.16.0` to `[dev-dependencies]` — environmental sync artifact, not part of this change). Both files were reverted to HEAD (`git checkout -- pyproject.toml uv.lock`) and are absent from the final diff. Note for verify: a subsequent `uv run ...` may re-trigger the same environment sync; it is not a change artifact.
3. **Pre-existing LSP diagnostics (pi-lens gate)**: the edit-time `pi-lens` check reports pyright-strict diagnostics across `tests/test_mcp_server.py` (e.g. `L26 conftest import`, `L93 dict` typing, `BlobResourceContents.text` accessors — 329 findings on the pristine HEAD file) and `src/sofer/mcp_server.py` (`L687 tomli fallback` — a documented latent issue per AGENTS rule 12; `_SERVER_*` constant redefinitions in `build_server`). All are pre-existing on HEAD verbatim and outside this change's diff (verified: `git diff` touches no flagged line). The repo's authoritative gates — `ruff check src/ tests/`, `ruff format --check`, `mypy src/` — are all clean; `mypy` runs on `src/` only and test helpers are intentionally untyped (design §3.2). Fixing them would violate proposal R5 / design D7 scope (any larger diff is a rejected scope violation), so they are documented here as pre-existing background noise, not introduced by this change.

## 6. Remaining tasks (implementation)

None. All implementation-owned rows are `- [x]` (10 rows: 1.1, 2.1–2.6, 3.1–3.2, 4.1–4.6). Parent-owned rows 5.1–5.4 (spec delta verify, verify-report, canonical sync, bounded review + archive) remain `- [ ]` and are deferred to parent lifecycle — not touched by apply.

## 7. Workload / PR boundary

- Estimated changed lines: 4 source + ~129 test ≈ 133 total executable — inside the 400-line budget (Low risk); single PR, no chaining (forecast: Chained PRs: No; Decision needed: No).
- Rollback = single commit revert; production diff is 4 token lines; the #139 suite stays green in both states (it never asserted the intro) — verified by construction (D6) and empirically (all #139 block probes green both before and after the fix).

## 8. Structured status consumed

- Native SDD status at apply entry: `applyState: blocked` with `nextRecommended: "Change selection is ambiguous: ..."` (6 sibling change dirs) — BUT the parent prompt supplied the explicit `change` + `proceed` handoff (token held by parent; max 800 lines, scope ~93 executable), which this executor treats as the authoritative selection override. No `applyState`/dependency blockers were honored as real blockers per the handoff contract.
- `actionContext`: `mode: repo-local`, `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` — all edits inside workspace root; no warnings.
- Delivery: `ask-on-risk` domain with `Decision needed: No` — no size-exception or chained-PR decision required; single PR.
