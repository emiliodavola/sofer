```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:899a06c7a5a99bd333afde3c99917d55709251666f3ac8ab5f5a6340248c2fc3
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1 (MSP-R08 MODIFIED delta; 2 preserved + 5 new scenarios)
scenarios: 7/7 (2 preserved + 5 new, all traced to green tests)
test_command: PYTHONIOENCODING=utf-8 uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:899a06c7a5a99bd333afde3c99917d55709251666f3ac8ab5f5a6340248c2fc3
test_summary: "1548 passed, 6 skipped, 13 warnings in 43.93s"
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:5b3e3905d4d9e175f9dd86715f6d5a9643abecae88f3e6e7b2349e013c8e9006
```

## Verification Report

**Change**: test-mcp-injection-semantics (closes #139 — test-only; follow-up of #121)
**Version**: spec delta (MODIFIED MSP-R08 — Prompts)
**Mode**: Standard — strict TDD **off** (`openspec/config.yaml strict_tdd: false`); tests follow the MSP-R08 delta scenarios (AGENTS rule 6); GREEN-by-construction probing (repr-protected executable surface) with a STOP gate for any genuine breakout
**Branch**: `test/139-mcp-injection-semantics` @ HEAD b93aa2d (1 modified file + untracked change dir; openspec artifact dir untracked)
**Read-only**: src/ and tests/ untouched by this phase; no fixes made; no commits

### Completeness

| Metric | Value |
| -------- | ------- |
| Tasks total (implementation-owned) | 15 (0.1–3.4) |
| Tasks complete | 15 — all `[x]` with recorded evidence |
| Tasks incomplete (implementation) | 0 |
| Parent-owned lifecycle tasks (4.1–4.4, `sdd-owner: parent`) | 4 unchecked — not implementation scope; 4.2 fulfilled by this report (repo convention); 4.3/4.4 pending at sync/archive |
| Requirements covered | 1/1 (MSP-R08 MODIFIED: 2 preserved + 5 new scenarios) |
| Scenarios covered | 7/7 (Prompt list 3, Confirm-before-publish, prepare-hostile, assess-hostile, finalize-hostile, canonical-order, intro-limitation) |
| Files touched vs allowed set | 1/1 allowed (`tests/test_mcp_server.py`) |
| `src/sofer/` (incl. `mcp_server.py`) | untouched (verified via `git diff --name-only`) |
| Live `openspec/specs/mcp-server/spec.md` | untouched (sync deferred to archive per convention) |
| README / README_ES / CLI | untouched (§13 not triggered) |

### Scenario → test → result evidence table

All 13 new probes live in `TestPrompts` (`tests/test_mcp_server.py`, appended after `test_finalize_and_publish_dry_run_stop`, before the `# 7.11` header; payload constants + shared helpers module-level above `# 7.10` at L1830-1945). Fast loop: `13 passed, 230 deselected in 0.91s`; whole class: `19 passed in 1.64s` (6 preserved + 13 new).

| Spec scenario (MSP-R08 delta) | Probe(s) | Result | Non-vacuous (asserts the actual contract) |
| --- | --- | --- | --- |
| Prompt list shows 3 templates (preserved) | `test_prompt_list_shows_three` (unchanged) | ✅ | Existing — byte-identical (diff is 0 deletions) |
| Confirm-before-publish idiom (preserved) | `test_publish_prompt_mandates_approval_stop` + `test_finalize_and_publish_dry_run_stop` (unchanged) | ✅ | Existing — byte-identical |
| Hostile payload cannot alter **prepare_dataset** workflow | `test_prepare_dataset_payload_no_steps_added` (2.1) + `test_prepare_dataset_payload_arg_containment` (2.2); STOP/note folded into 2.4 | ✅ | Line-anchored numbered-step extraction == static 6-step canonical sequence (hostile AND benign); line-start `sofer_*` set ⊆ canonical tools; no line starts with `sofer_publish_confirm`; raw `_INJECT_FAKE_STEP`/`_INJECT_FAKE_TOOL_CALL` absent from block |
| Hostile payload cannot alter **assess_dataset** workflow | `test_assess_dataset_payload_no_steps_added` (2.5) + `test_assess_dataset_payload_arg_containment` (2.6) | ✅ | Exact 3-step chain `(1,sofer_validate),(2,sofer_profile),(3,sofer_render)` contiguous; zero line-start `sofer_*` calls; raw markers absent |
| Hostile payload cannot alter **finalize_and_publish** workflow | `test_finalize_payload_no_steps_added` (2.8) + `test_finalize_payload_arg_containment` (2.9); STOP/note folded into 2.11 | ✅ | 6 sofer steps + `(7,STOP)` exact; step-8 confirm is mid-line prose only (never a line start); line-start set ⊆ canonical tools; raw markers absent |
| Canonical chain order is payload-invariant | `test_prepare_dataset_payload_canonical_order` (2.3) + `test_assess_dataset_payload_canonical_order` (2.7) + `test_finalize_payload_canonical_order` (2.10) | ✅ | Sequential `find` per builder marker list, each search after the previous hit; `_assert_strictly_increasing` on BOTH hostile and benign renders (order shown invariant, not just present) |
| Intro raw interpolation is a recorded known limitation, not asserted | `test_prepare_dataset_intro_contract_scope` (2.13) | ✅ | `"\nCanonical chain:" in hostile` (block still starts on its own line under hostile args); block containment intact despite raw intro; asserts nothing about intro prose; docstring records `mcp_server.py:2987/3017-3018/3042` + #169 tracking + no server fix (no coupling to a future #169 fix) |
| AND clause of the three hostile scenarios: `_UNTRUSTED_NOTE` still appended | `test_prompts_untrusted_note_under_hostile_args` (2.12) | ✅ | All 3 templates: `ms._UNTRUSTED_NOTE in text` AND `text.endswith(ms._UNTRUSTED_NOTE)` under hostile args |

Arg-position containment asserted across all three arg-containment probes (2.2 / 2.6 / 2.9): for every caller-controlled slot, `repr(args[slot]) in hostile_block`, raw marker absent for all four marker classes, marker-bearing lines attributed to the matching arg syntax (`config=`, `output_dir=`, `dataset=`/`package=`), `"\\\\" in repr(_INJECT_ESCAPES)` (escape pinning), and `len(hostile_block.splitlines()) == len(benign_block.splitlines())` (payload newlines add zero executable lines). Approval-STOP probes (2.4 / 2.11) assert `block.index("STOP") < block.rindex("sofer_publish_confirm")` — the `rindex` requirement (canonical-chain line mentions `sofer_publish_confirm` before any STOP) is correctly implemented — plus human-approval wording and note survival.

### Structured status & actionContext findings

Native status (`gentle-ai.sdd-status` v1): `changeName: null`; parent prompt pinned the active change (`2026-09-13-test-mcp-injection-semantics`, matching branch `test/139-mcp-injection-semantics`) and the handoff states apply settled `complete` with a held verify token. `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` — the only changed file lies inside the workspace root; no warnings to act on. Verify produced no edits to source or test code (read-only enforced; the only write is this report).

### Evidence (exact commands and outputs)

**Focused probe loop** — `PYTHONIOENCODING=utf-8 uv run pytest tests/test_mcp_server.py -q -k "payload or intro_contract or untrusted_note"`:

```
13 passed, 230 deselected in 0.91s   (exit 0)
```

**TestPrompts class (preserved + new)** — `PYTHONIOENCODING=utf-8 uv run pytest tests/test_mcp_server.py::TestPrompts -q`:

```
19 passed in 1.64s   (exit 0)
```

**Full suite** — `PYTHONIOENCODING=utf-8 uv run pytest tests/ -q` (exit **0**):

```
1548 passed, 6 skipped, 13 warnings in 43.93s
```

Delta over the measured pre-change baseline (1535 passed / 6 skipped, apply-progress §0) is exactly +13 — the forecast `baseline + 13 = 1548` held precisely; additive only, no new skips, zero coverage reduction. The 13 warnings are the pre-existing #162 `_infer_type` DeprecationWarnings (`_infer_type is deprecated, use infer_column_type`) — **reported, NOT fixed** (out of scope, per proposal R5).

**Quality gates**:

```
uv run ruff check src/ tests/            → All checks passed!              (exit 0)
uv run ruff format --check src/ tests/   → 65 files already formatted      (exit 0)
uv run mypy src/                         → Success: no issues found in 32 source files (exit 0)
git diff --check                         → silent (clean)                  (exit 0)
```

Output hashes (byte-exact captures of the verify-run above): full-suite pytest → `sha256:899a06c7a5a99bd333afde3c99917d55709251666f3ac8ab5f5a6340248c2fc3`; mypy → `sha256:5b3e3905d4d9e175f9dd86715f6d5a9643abecae88f3e6e7b2349e013c8e9006` (byte-identical to the archived fix-xlsx mypy hash — stable output, cross-validates the gate); ruff → `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`.

`git diff --name-only` → `tests/test_mcp_server.py` only; `git diff --numstat` → `390 0` (purely additive, zero deletions = existing `TestPrompts` tests byte-identical). LF file, no CRLF (diff-check clean).

### Implementation scope checks (AGENTS.md rules)

- **Rule 1 (no hardcoded values)**: all payload literals live in module-level `_INJECT_*` / `_INJECT_ARGS_*` / `_BENIGN_*` constants (L1834-1860); probe bodies contain zero inline payload literals (verified by reading the full probe suite — every marker/arg reference goes through the constants).
- **Rule 2 (docstrings)**: `_get_prompt_text`, `_prompt_block`, `_numbered_steps`, `_marker_positions`, `_assert_strictly_increasing`, and each of the 13 probes carries a docstring (module docstring + param/return on the helpers).
- **Rule 4 (no duplicated logic)**: the `_get_prompt_text` helper replaces the 13× inline `_go()`/`_run()` boilerplate; the four extra helpers (`_prompt_block`, `_numbered_steps`, `_marker_positions`, `_assert_strictly_increasing`) dedup block slicing / regex extraction / sequential find / order assertion across 13 probes (documented apply-progress deviation 2, in-scope with the design's rule-4 rationale).
- **No new imports**: diff grep over added lines shows zero `import`/`from` additions (`re`, `Client`, `_run`, `ms` alias all pre-existing).
- **Rule 6 (tests match specs)**: every MSP-R08 delta scenario maps to ≥1 test per the authoritative table (section above).
- **Out of scope respected**: zero `src/sofer/` edits (including `mcp_server.py` — read-only reference); no new templates/behavior; #169 raw-intro sites recorded, not fixed; #162 warnings reported, not fixed; README/README_ES/CLI untouched; live spec untouched (sync at archive).

### Strict TDD compliance / assertion quality

Strict TDD is **off** (`strict_tdd: false` in `openspec/config.yaml` + apply/testing sections; no parent override; no project-local strict-TDD override file). No `TDD Cycle Evidence` table required — this is a green-by-construction probing change (behavior already correct; probes pin the #121 acceptance criterion). Assertion-quality audit (performed anyway): no tautologies — every probe asserts observable rendered-prompt behavior against an independently listed static canonical sequence and/or the benign render; no ghost loops — each loop over marker classes / arg slots asserts inside the loop; no type-only or smoke-only assertions — each probe has ≥3 distinct behavioral assertions; the one introspection-looking line (`"\\\\" in repr(_INJECT_ESCAPES)`) is a deliberate self-calibration pin (design D5.2) that guards the escape-immune-class probes against a payload-constant weakening, not an implementation assertion. The R3 repr deviation (below) was triaged empirically at apply time via hand-repros against `client.get_prompt` and does not weaken any asserted invariant.

### Deviations from design — assessed, none weaken the contract

1. **Per-marker `repr(marker) in block` → `repr(args[slot]) in block`** (apply-progress §3.1). Reason verified: CPython's `repr` re-selects the outer quote per string — a standalone single-quote-only payload renders double-quoted, while the composed mixed-quote arg renders single-quoted with escaped inner quotes — so a standalone `repr(marker)` is never a substring of the composed rendering. The implemented form is strictly sufficient: `repr(args[slot]) in block` (the design's own parenthetical, "each argument position renders `{arg!r}`", verbatim), `marker not in block` for **all four** marker classes (the actual no-raw-linebreak / no-raw-instruction invariant — empirically true for every class, even the quotes/backslash one), `repr(marker)[1:-1] in block` for the three quote-immune classes, and per-line arg-syntax attribution. No asserted security property was dropped or relaxed.
2. **Extra shared helpers** — additive dedup (assessment above); all docstring'd.
3. **`_assert_strictly_increasing` instead of pairwise `zip`** — avoids ruff RUF007 without a new `itertools` import, same strict-increase invariant.

### Review workload / PR boundary

`Review Workload Forecast` (tasks.md): ~250–330 estimated changed lines; Chained PRs recommended: **No**; Chain strategy: pending (not needed — single PR); 400-line budget risk: **Low**; `size:exception`: not used. Confirmed: measured diff **390 insertions / 0 deletions** in ONE file (constants+helpers ~120 lines, 13 probes ~270 lines) — inside the 400-line canonical budget and matching the 09-12 archive trajectory (1535/6 + 13 = 1548/6); single PR boundary respected; only the assigned slice implemented — no scope creep beyond tasks 0.1–3.4; follow-ups (#169 raw-intro sites, #162 warnings) correctly tracked out of scope. Minor note: the actual +390 lines slightly exceeds the forecast's upper bound (+330) yet remains within budget — budget risk stays Low, no chaining or exception warranted.

### Task checkbox reconciliation

All 15 implementation tasks (0.1, 1.1–1.3, 2.1–2.13, 3.1–3.4) are `[x]` with recorded evidence in apply-progress. The only unchecked `- [ ]` rows are the 4 parent-owned lifecycle tasks (exact lines from `openspec/changes/2026-09-13-test-mcp-injection-semantics/tasks.md`):

```
- [ ] 4.1 Update `openspec/changes/2026-09-13-test-mcp-injection-semantics/apply-progress.md` with the 0.1 baseline numbers and per-task outcomes. <!-- sdd-owner: parent -->
- [ ] 4.2 Populate `…/verify-report.md` with the §3 gate results (baseline + final full-suite counts, ruff/format/mypy/`git diff --check`). <!-- sdd-owner: parent -->
- [ ] 4.3 Sync the MSP-R08 delta into canonical `openspec/specs/mcp-server/spec.md` at the archive commit (full-block MODIFIED requirement replacement per the change-local spec, on merge to `dev`, AGENTS.md rule 12 branch flow); README/README_ES intentionally untouched (§13 not triggered). <!-- sdd-owner: parent -->
- [ ] 4.4 Post-apply bounded review of the single-PR diff (constants + helper + 13 probes; existing `TestPrompts` byte-identical), then archive. Rollback = single-commit revert of `tests/test_mcp_server.py` + deletion of the change-local spec delta — no production, config, data, or on-disk artifact touched. <!-- sdd-owner: parent -->
```

These are lifecycle steps owned by the parent, not implementation completeness: 4.1 is fulfilled by the already-written apply-progress; 4.2 is fulfilled by this verify-report (the repo convention — tasks.md's "verify.md" wording is generic); 4.3 (canonical spec sync) and 4.4 (bounded review + archive) remain pending. **Archive is not yet performed** and must wait for 4.3/4.4; no implementation task remains unchecked, so no CRITICAL completeness issue attaches to the code.

### Known / documented

- **#169 raw-intro interpolation** (`mcp_server.py:2987, 3017-3018, 3042`): the three intro sentences interpolate caller args raw; a hostile `config`/`dataset` legitimately adds *prose* lines before `Canonical chain:`. Recorded as a known limitation in the delta, design, and probe docstring; deliberately NOT asserted (a prose-purity probe would be knowingly red) and NOT fixed here (test-only scope). The probes prove no cascade into the executable block.
- **#162 `_infer_type` DeprecationWarnings**: 13 in the full-suite run — reported, not fixed.
- **STOP gate (R1/R3)**: not triggered — all 13 probes green; the one assertion-mechanics deviation (R3 deviation 1) was triaged by hand-repro against `client.get_prompt` and classified as a design-text error, not a template defect. No `src/sofer/mcp_server.py` edit was made.
- Diff boundary: `390 insertions(+), 0 deletions(-)`; LF; purely additive, one file — rollback is a single-revert boundary.

### Blockers

None. Verdict **PASS**: every MSP-R08 delta scenario (5 new + 2 preserved) maps to a passing, non-vacuous probe or unchanged existing test; all gates green (1548 passed / 6 skipped / 13 warnings; ruff check + format clean; mypy clean; `git diff --check` clean); the repr-protection contract is verified as implemented at every executable surface with the raw-intro gap recorded as #169 and not asserted; zero `src/sofer/` changes; scope boundaries, review workload (single PR, 390 lines, no exception), and all 15 implementation tasks verified. Archive remains pending the parent-owned 4.3 (live-spec sync) and 4.4 (bounded review + archive).
