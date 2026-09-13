# Apply Progress — test-mcp-injection-semantics (GitHub #139)

**Change:** `2026-09-13-test-mcp-injection-semantics` · branch `test/139-mcp-injection-semantics`
**Phase:** apply (implementation) — test-only change, ZERO `src/sofer/` edits
**Strict TDD:** off (`openspec/config.yaml` `strict_tdd: false`) — tests follow the spec delta (AGENTS rule 6)
**Status consumed:** the parent handoff resolves the native status as authoritative (`next: tasks`; apply attempt acquired, max 2000 changed lines, `proceed`). The native status JSON's `applyState: blocked` stems solely from ambiguous change selection at handoff time — resolved by the explicit change + branch in the parent prompt. No other blockers.

## 0. Baseline (task 0.1)

Measured on a clean tree before ANY edit (do not trust the design's stale 1392/4 forecast):

```
1535 passed, 6 skipped, 13 warnings in 44.21s
```

- 13 warnings = the #162 `_infer_type` DeprecationWarnings — REPORTED, not fixed (out of scope).
- Expected final = 1535 + 13 = **1548 passed, 6 skipped** (all additive, zero new skips).

## 1. Per-task outcomes

| Task | Outcome |
| --- | --- |
| 0.1 | ✅ Baseline measured: 1535 passed / 6 skipped / 13 warnings, 44.21s |
| 1.1 | ✅ Four `_INJECT_*` payload constants added (prose+newlines, fake `\n6. sofer_publish(...)` step, fake `sofer_publish_confirm(...)` call, quotes/backslashes). Zero `_INJECT_*` pre-existing matches in `tests/` confirmed before insertion |
| 1.2 | ✅ Per-builder hostile dicts `_INJECT_ARGS_{PREPARE,ASSESS,FINALIZE}` (all 6 caller-controlled arg slots carry the full hostile class set) + `_BENIGN_CONFIG/_BENIGN_OUTPUT/_BENIGN_DATASET` baselines |
| 1.3 | ✅ Docstring'd `_get_prompt_text(server, name, args)` helper (renders via in-process `Client` + `client.get_prompt`, returns `prompt.messages[0].content.text`); reuses `_run`; no new imports. Also added three small docstring'd shared helpers (`_prompt_block`, `_numbered_steps`, `_marker_positions`, `_assert_strictly_increasing`) per AGENTS rule 4 (the design's rule-4 rationale extends to block slicing and extraction — documented below under deviations) |
| 2.1–2.13 | ✅ All 13 probes added to `TestPrompts` after `test_finalize_and_publish_dry_run_stop`, before `# 7.11`; existing `TestPrompts` tests byte-identical (verified: `git diff` shows zero `-`/`+` on the pre-existing method lines) |
| 3.1 | ✅ Fast loop `uv run pytest tests/test_mcp_server.py -q -k "payload or intro_contract or untrusted_note"` → **13 passed** (1.47s); `TestPrompts` class → **19 passed** (6 preserved + 13 new) |
| 3.2 | ✅ Full suite `uv run pytest tests/ -q` → **1548 passed, 6 skipped, 13 warnings in 43.91s** (= 1535 + 13; skips unchanged) |
| 3.3 | ✅ `uv run ruff check src/ tests/` — All checks passed; `uv run ruff format --check src/ tests/` — 65 files already formatted; `uv run mypy src/` — Success, no issues in 32 source files; `git diff --check` — clean |
| 3.4 | ✅ STOP gate NOT triggered — all 13 probes green. The one assertion-mechanics deviation (below) was triaged per R3 by reproducing payloads by hand against `client.get_prompt`; it is a design-text error, NOT a template defect. No `src/sofer/mcp_server.py` edit made |
| 4.1–4.4 | ⏭️ Parent-owned — preserved byte-for-byte, deferred to the parent lifecycle |

## 2. Verification evidence (actual command output, not placeholders)

- Baseline: `1535 passed, 6 skipped, 13 warnings in 44.21s`
- Fast loop: `13 passed, 230 deselected in 1.47s`
- TestPrompts class: `19 passed in 1.19s`
- Full suite: `1548 passed, 6 skipped, 13 warnings in 43.91s`
- `uv run ruff check src/ tests/` → `All checks passed!`
- `uv run ruff format --check src/ tests/` → `65 files already formatted`
- `uv run mypy src/` → `Success: no issues found in 32 source files`
- `git diff --check` → clean (no whitespace errors)
- Diff shape: `tests/test_mcp_server.py | 390 insertions(+), 0 deletions(-)` — purely additive, ONE file

## 3. Deviations from design (all documented, none alter the security contract)

1. **Per-marker `repr(marker) in block` (design §6.2 D5.2) is not satisfiable as literally written and was implemented as `repr(full_arg) in block` + raw-marker absence + escaped-content checks.** Empirical triage (R3) — reproducing every planned assertion against real `client.get_prompt` renders — proved: CPython's repr re-selects the outer quote **per string** (a string containing only single quotes — `_INJECT_FAKE_STEP`, `_INJECT_FAKE_TOOL_CALL` — is double-quoted standalone, but once composed into a mixed-quote arg it renders single-quoted with **escaped** inner quotes). Consequently `repr(marker)` is never a substring of the composed arg's rendered repr. The probes therefore assert the stronger, provably-true form: `repr(args[slot]) in block` for every caller-controlled slot (the design's own parenthetical — "each argument position renders `{arg!r}`" — verbatim), `marker not in block` for all four marker classes (the actual "no raw line break / no raw instruction text" invariant, empirically true for ALL classes even the quote/backslash one), `repr(marker)[1:-1] in block` for the three quote-immune classes (prose/toolcall/escapes), and line-attribution using the full-arg repr. The security property asserted is unchanged and complete.
2. **Extra shared helpers** (`_prompt_block`, `_numbered_steps`, `_marker_positions`, `_assert_strictly_increasing`) beyond the mandated `_get_prompt_text` — the design's rule-4 rationale ("13× duplication") applies equally to block slicing, numbered-step extraction, sequential-marker search, and the strictly-increasing order assertion (6 call sites); all are module-level, docstring'd, and additive.
3. **Pairwise order assertion form**: the design's `zip(pos, pos[1:])` pairwise comparison trips ruff's `RUF007` (prefer `itertools.pairwise`); the repo gate forbids new imports in this change, so the assertion is a module-level `_assert_strictly_increasing` helper using index comparisons — same invariant, gate-clean, no new import.

## 4. Key security finding

**No template breakout exists on the executable surfaces.** Hostile payloads in every caller-controlled argument of all three `prompts/get` templates render exclusively inside `{arg!r}`-quoted positions: the steps-set (line-anchored extraction) is byte-equal to each builder's static canonical sequence, the canonical-chain relative order is strictly increasing and identical to the benign render, the approval STOP precedes the last confirm mention on prepare/finalize, `_UNTRUSTED_NOTE` is still appended and terminates the text, and `repr(config)/repr(output)/repr(dataset)` surface verbatim at exactly the argument positions. The only raw-interpolation surface is the intro sentence (known limitation #169, `mcp_server.py:2987/3017-3018/3042`) — recorded, not asserted, scoped out by the `_prompt_block` slice, and no server fix is specified or required here.

## 5. Workload / PR boundary

Single PR, well under budget: **+390 lines in one test file** (constants+helpers ~120, 13 probes ~270). 400-line budget risk: Low (as forecast). Delivery strategy `ask-on-risk` — no gate expected; final count 1548/6 matches the 09-12 archive trajectory (1535/6 + 13). Rollback = single-commit revert of `tests/test_mcp_server.py`; no production, config, data, or README/README_ES touched.

## 6. Remaining unchecked tasks (parent-owned, deferred)

- `- [ ] 4.1 Update …/apply-progress.md with the 0.1 baseline numbers and per-task outcomes.` — **this file is already written with those numbers**; 4.1 is parent-confirmation of the same content.
- `- [ ] 4.2 Populate …/verify-report.md with the §3 gate results (baseline + final full-suite counts, ruff/format/mypy/git diff --check).` — the exact gate outputs are recorded in §2 above for the parent to copy.
- `- [ ] 4.3 Sync the MSP-R08 delta into canonical openspec/specs/mcp-server/spec.md at the archive commit …`
- `- [ ] 4.4 Post-apply bounded review of the single-PR diff … then archive.`

## 7. Structure / execution notes

- The `read` tool in this environment renders test-file indentation +4 deeper than reality (module-level code is col 0, class methods at 4, bodies at 8). Anchors and blocks were verified against raw bytes before insertion; insertions were applied with a byte-preserving inserter (`newline=""`, LF-only file confirmed) rather than the interactive edit tool, after the edit tool's whitespace inference corrupted bracket/loop indentation on first attempt.
- Window's `python` alias is not on PATH outside `uv`; scratch probes ran via `uv run python`.
- `pi-lens` pyright diagnostics against the test file (L26 conftest import, L93 dict generics, L364 arg-type, L661 union-attr, L847 ImageContent, L1497-1668 BlobResourceContents, L3916 tomli fallback, L4505-4508 instr typing, code-quality advisories) are pre-existing baseline noise in untouched regions, outside the repo's configured gates (`ruff` + `mypy src/`); none were introduced or touched by this change.
