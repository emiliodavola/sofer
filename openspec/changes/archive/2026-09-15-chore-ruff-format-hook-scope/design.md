# Design: chore-ruff-format-hook-scope

**Change** `2026-09-15-chore-ruff-format-hook-scope` (issue #216) · **Source of truth**: `proposal.md` revision 2 (FINAL; question round skipped → its six assumptions are confirmed intent; issue #216; D1–D3; R1 acceptance gate; #195 trap) · **Store**: hybrid (this file + Engram `sdd/2026-09-15-chore-ruff-format-hook-scope/design`)
**Design outcome**: every open item from the proposal is closed. 3 carriers (YAML declaration + YAML comment + PB-14/guard). No new dependency, no `src/sofer/**`, no CI, no `pyproject.toml`, no rev bump, no README edit.
**Confirmed inputs**: PB-14 is the next free ID (`openspec/specs/process-boundary/spec.md` ends at PB-13; no `## Test Mapping` section exists there today).

---

## 1. PB-14 — exact wording (delta text; final, no placeholders)

### Requirement: Repository-declared ruff-format hook file scope (PB-14)

> Added by change `2026-09-15-chore-ruff-format-hook-scope` (issue #216).

The `ruff-format` pre-commit hook's file-type scope SHALL be a **repository declaration**, not an inherited upstream default: the `astral-sh/ruff-pre-commit` hook entry in `.pre-commit-config.yaml` SHALL declare an explicit `types_or` naming the types this repository intends the formatter to see — `python`, `pyi`, and `jupyter` — and `markdown` SHALL NOT be among them. The decision is deliberate and rationale-bearing: upstream widened the manifest's `types_or` to include `markdown` between `ruff-pre-commit` 0.15.21 and 0.16.6 without this repository changing anything, and the pinned hook then rewrote the fenced Python inside `README.md` and `README_ES.md` (issue #216). The declared scope SHALL therefore NOT be read as a mirror of the upstream default, a `rev` bump SHALL NOT widen it silently, and the declared tag vocabulary SHALL stay consistent with the sibling scope decision `[tool.ruff] extend-exclude = ["openspec"]` in `pyproject.toml`.

This requirement SHALL constrain **the hook only**. `types_or` is a pre-commit filter, not a ruff setting: a direct `ruff format <path>` still sees Markdown, and this requirement SHALL NOT be read as narrowing the formatter itself, as adopting a Markdown formatter, or as arming any gate. Issue **#194** SHALL retain ownership of the decision to arm a `ruff format --check` gate and of that gate's path scope; this requirement SHALL arm no CI step. This change SHALL NOT move the `ruff-pre-commit` `rev`, SHALL NOT edit `pyproject.toml` or any `src/sofer/**` path, and SHALL leave `README.md` / `README_ES.md` byte-identical.

The declaration SHALL be statically guarded in `tests/test_ci_workflows.py` (the established home for static repository-shape contracts): the hook entry SHALL declare `types_or`, SHALL declare it as a list, and `markdown` SHALL NOT appear in it. The guard SHALL assert the **defect class**, not mirror the declared list, so a legitimate future widening to another type keeps it green. The guard SHALL assert declaration shape only: that pre-commit honours the override is verify-phase runtime evidence and SHALL NOT be asserted from pytest (the suite spawns no `pre-commit`).

#### Scenario: The hook declares its own scope and excludes Markdown

- GIVEN `.pre-commit-config.yaml` as committed by this change
- WHEN `tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown` parses it with the module's existing `_load_yaml` helper and selects the `astral-sh/ruff-pre-commit` repo's hook whose `id` is `ruff-format`
- THEN the entry SHALL be found exactly once and SHALL declare a list-valued `types_or`
- AND `"markdown"` SHALL NOT be a member of that list
- AND the guard SHALL be red against an entry with no `types_or` key and green once the config line lands (red then green, both recorded in the verify report)
- AND no other tag SHALL be asserted, so adding a legitimate type leaves the guard green

#### Scenario: The hook no longer receives Markdown and leaves the READMEs untouched

- GIVEN the pinned `ruff-pre-commit` hook materialised in the local pre-commit cache and the repository's declared `types_or` in place
- WHEN `uv run pre-commit run ruff-format --files README.md` runs
- THEN the hook SHALL report the file as not a hook input (`(no files to check)Skipped`) and SHALL exit 0
- AND `uv run pre-commit run ruff-format --all-files` SHALL show no Markdown batch — no `files were modified by this hook` — listing only `python` / `pyi` / `jupyter` inputs
- AND `git diff --stat -- README.md README_ES.md` SHALL be empty afterwards
- AND the hook's **file-list output**, not its exit code, SHALL be the discriminating evidence: the entry is the fixing command `ruff format --force-exclude`, which exits 0 after rewriting (the #195 trap)
- AND this evidence is **verify-phase runtime evidence** — the commands above pasted with their exit codes into the verify report (PB-10 / CI-08 S4 precedent)

---

## 2. Test Mapping decision — **T1: the delta carries the rows; sync creates the section**

**Decision: T1.** Evidence: `ci/spec.md:366-368` states the repository rule — *"Every scenario SHALL map to a green test or to verify-phase static evidence"* — and PB-14 S1 **is** a green pytest test, so it needs an index row; `process-boundary`'s table-less state is the *absence* of the convention (#177 had no pytest-mapped scenario and resolved rule 6 in-delta), not a counter-convention. **T2 (in-delta rule-6 prose, #177 form) is rejected** for exactly that reason: it would hide the only pytest-enforced link for a hook-scope invariant inside an archived change. Cost accepted and recorded in the delta: PB-01..PB-13 rows are a **named non-goal** (their evidence classes already live in their own scenario text).

Placement: the delta carries `## Test Mapping` **after** its `## ADDED Requirements` block, mirroring `ci/spec.md`'s position (last section of the file). Sync appends it to `openspec/specs/process-boundary/spec.md` **after PB-13's final scenario** (`tests/test_mcp_registration.py:560-577` line), separated by the same `---` + blank-line convention `ci/spec.md` uses before its table.

Exact rows (shape copied from `ci/spec.md:370-372`: `| Req | Scenario | Verification |`):

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| PB-14 | The hook declares its own scope and excludes Markdown | `tests/test_ci_workflows.py` — `test_ruff_format_hook_excludes_markdown`: YAML inspection of the `ruff-format` hook entry in `.pre-commit-config.yaml` |
| PB-14 | The hook no longer receives Markdown and leaves the READMEs untouched | Verify-phase runtime evidence — `uv run pre-commit run ruff-format --files README.md` and `--all-files`, plus an empty `git diff --stat -- README.md README_ES.md` |

Intro prose for that section (sync-pasted verbatim): *"Every scenario SHALL map to a green test or to verify-phase runtime evidence (AGENTS.md rule 6; rules.specs). Static config assertions live in `tests/test_ci_workflows.py`. PB-01..PB-13 rows are not backfilled by this change: their evidence classes are stated in their own scenario text, and the backfill is a separate concern."*

---

## 3. Guard test — exact shape (appended after `test_contributing_names_the_declared_ruff_version`, line 488)

Function name: `test_ruff_format_hook_excludes_markdown`. Reuses the existing `_load_yaml` and `_RUFF_PRE_COMMIT_REPO` only — **no new import, helper, module, or dependency** (AGENTS.md rule 4), reading the same repo entry the CI-08 rev guard reads.

```python
def test_ruff_format_hook_excludes_markdown() -> None:
    """PB-14 S1: the ruff-format hook declares its own scope and excludes Markdown."""
    config = _load_yaml(".pre-commit-config.yaml")
    hooks = [
        hook
        for repo in config["repos"]
        if repo.get("repo") == _RUFF_PRE_COMMIT_REPO
        for hook in repo.get("hooks", [])
        if hook.get("id") == "ruff-format"
    ]
    assert len(hooks) == 1, f"expected exactly one ruff-format hook entry, found {len(hooks)}"
    types_or = hooks[0].get("types_or")
    assert types_or is not None, (
        "the ruff-format hook entry must declare `types_or`: its scope is a repository "
        "declaration, not the upstream manifest default (PB-14)"
    )
    assert isinstance(types_or, list), f"`types_or` must be a list, got {types_or!r}"
    assert "markdown" not in types_or, (
        "`markdown` must not be in the ruff-format hook's `types_or`: upstream widened the "
        "manifest at 0.16.6 and the hook rewrote README.md / README_ES.md (issue #216)"
    )
```

Assertions, in order: (1) exactly one `ruff-format` entry, (2) `types_or` present, (3) `types_or` is a list, (4) `"markdown" not in types_or`. (3) is the hardening that keeps (4) non-vacuous — against a scalar `types_or: markdown`, `not in` would be a *substring* test and would false-green; it is part of clause "declares `types_or`", not a deviation from D3.

**RED on the unfixed config**: the entry has no `types_or` key, so `hooks[0].get("types_or")` is `None` and assertion 2 raises `AssertionError: the ruff-format hook entry must declare types_or: its scope is a repository declaration, not the upstream manifest default (PB-14)` → `1 failed`. **GREEN** after the YAML edit → `1 passed`.

Docstring edit (same file, module docstring lines 8-12): `plus four tests` → `plus five tests`, and the enumeration gains `and the PB-14 hook-scope guard`.

---

## 4. YAML edit — exact final text of the `ruff-format` entry

`types_or` sits **under `- id: ruff-format`**, in the same position style as `args:` under `- id: ruff`; the rationale comment sits **immediately above the `types_or:` line it justifies**, following the `pyproject.toml:63-66` precedent (comment on the line that carries the decision) and using that block's `#`-sentence style. Net added lines: **6**.

```yaml
      - id: ruff-format
        # ruff-format's file scope is a repository declaration, not the upstream default:
        # ruff-pre-commit widened its manifest to include `markdown` at 0.16.6, which let
        # this hook rewrite the fenced Python in README.md / README_ES.md (issue #216).
        # Declaring it here keeps a rev bump from widening it silently; see PB-14 in
        # `process-boundary` and the guard in tests/test_ci_workflows.py.
        types_or: [python, pyi, jupyter]
```

The block above is the exact applied text: entry indentation 6 spaces for `- id:`, 8 for the comment lines and the `types_or` key, flow-sequence list, no trailing comment on the decision line.

---

## 5. Delta + sync

- **Delta path**: `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md` (the repo convention; the canonical spec is untouched by apply).
- **Section shape** (mirrors `openspec/changes/archive/2026-09-14-chore-ruff-format-drift/specs/process-boundary/spec.md`): `# Delta for process-boundary` → a `>` blockquote header (change / issue / branch / store topic key; **capability choice**: `process-boundary`, justified because the invariant is a verification property of the tree, the same category PB-07/PB-10 own; **additive, not destructive**: PB-01..PB-13 keep clauses and scenarios byte-for-byte; **domain hygiene**: delta not full spec, no other active change carries `specs/process-boundary/`) → `## ADDED Requirements` with the PB-14 block from §1 → `## Test Mapping` with the rows from §2 → `## Cross-referenced and deliberately untouched` (`ci` CI-08's rev guard reads the same repo entry but asserts only the `rev`; PB-10 owns format-check integrity; #194 owns any gate; #187 owns `CONTRIBUTING.md:77`) → a **Non-goals** paragraph.
- **Sync step (sdd-sync)**: (a) insert the PB-14 block at `openspec/specs/process-boundary/spec.md` after PB-13's last scenario line, and (b) create the `## Test Mapping` section at the end of that file, preceded by `---`, with the §2 intro prose and the two rows. Sync edits nothing else: PB-01..PB-13 text is replaced by itself (lossless no-op), and `openspec/specs/ci/spec.md` is not touched. Pre-sync, a revert of the change commit restores the canonical specs byte-for-byte.

---

## 6. Verify plan — exact commands and expected output shapes

| # | Command | Expected |
| --- | --- | --- |
| V1 | `uv run pytest tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown -q` (before the YAML edit) | `1 failed`, message "must declare `types_or`" — the RED |
| V2 | same, after the YAML edit | `1 passed` — the GREEN, same test ID |
| V3 | `uv run pre-commit run ruff-format --files README.md` (**AC1 / R1 acceptance gate**) | `ruff-format....(no files to check)Skipped`, `- exit code: 0` — README.md is not a hook input |
| V4 | `uv run pre-commit run ruff-format --all-files` (**AC2**) | `ruff-format...Passed`, file list contains only `.py` / `.pyi` / `.ipynb` paths (the 68 tracked Python files); **no** `.md` path, **no** `files were modified by this hook`, exit 0 |
| V5 | `git diff --stat -- README.md README_ES.md` right after V4 | no output, exit 0 — both READMEs untouched (`--all-files` was the mutator in #195) |
| V6 | `uv run python -c "import identify as i; print([t in i.tags_from_filename(f) for t, f in (('python','x.py'),('pyi','x.pyi'),('jupyter','x.ipynb'))])"` (**R2**) | `[True, True, True]` — each declared tag resolves as a real type tag. `identify` 2.6.19 is already in `uv.lock:836` as a `pre-commit` dependency, so `uv run` reaches it with **no manifest edit** |
| V7 | `uv run pytest tests/ -q` | green, **exactly +1 collected**, 0 failures, 0 new skips; module-docstring count now reads `five` |
| V8 | `uv run ruff check src/ tests/ scripts/` · `uv run mypy src/ scripts/` | clean (enforced commands) |
| V9 | `git diff --stat` | exactly `.pre-commit-config.yaml`, `tests/test_ci_workflows.py`, the delta, this `design.md` and the other phase artifacts; **zero** `pyproject.toml`, `.github/workflows/**`, `src/sofer/**`, `README.md`, `README_ES.md`, `uv.lock` |
| V10 | `git grep -n "format --check" -- .github/workflows/` and `git grep -n "pre-commit" -- .github/` | zero matches each, before and after (PB-10's no-gate scenario, #194 ownership) |

**The #195 trap, stated for the record:** the hook's `entry` is `ruff format --force-exclude` — a **fixing** surface that exits 0 *after* rewriting files. Exit 0 alone proves nothing; V3's "not a hook input" line, V4's file list, and V5's empty diff are the evidence. Second half of the trap: pre-commit detects modification via `git diff`, which cannot see an untracked file — `README.md` is tracked, so V5 is sound on it, and no untracked probe is used as evidence.
**Optional, non-load-bearing (R4)**: a pre-change `--all-files` baseline (showing the 2-markdown reformat) may be captured *before* the YAML edit, but it mutates the READMEs — restore with `git checkout -- README.md README_ES.md` and confirm V5 empty. Skipping it changes no acceptance gate.

---

## 7. Estimate, rollback, out of scope

**Estimate: ~71 changed lines (60–80), one work unit, one commit, no chaining** — `.pre-commit-config.yaml` 6 (1 key + 5 comment lines), `tests/test_ci_workflows.py` ~20 (guard test + docstring `four`→`five`), delta ~45 (requirement, 2 scenarios, header blockquote, Test Mapping section). Phase artifacts are not counted as product size (#177/#195 precedent).

Decisions that push the estimate, explicitly: (a) the 5-line YAML rationale comment vs the proposal's "~3–4 lines" → +1–2; (b) the `isinstance(types_or, list)` assertion → +1; (c) the T1 Test Mapping section plus the delta's `#177`-style blockquote header → ~+10 over a bare requirement block. All three stay inside `auto-chain`'s 1500-line budget, so **single PR, no `ask-on-risk`**.

**Rollback**: revert the single commit — the key, comment, guard test, docstring count, and delta all disappear; the canonical `process-boundary` spec is untouched until sync, so a pre-sync revert returns the specs byte-for-byte. No runtime, data, dependency, artifact, CI, or version change. `types_or` does not alter the repo `rev`, `language`, or `additional_dependencies`, so pre-commit's cached hook environment stays valid: no `pre-commit clean` needed, and nothing is left behind on a clone.

**Out of scope here**: the stale parts of `tests/test_ci_workflows.py`'s module docstring that predate CI-07/CI-08 (e.g. row-count claims) are **not** touched — only the cross-capability `four`→`five` count and its enumeration change, because this change's guard is the cause. Also out: `CONTRIBUTING.md:77` (#187), `AGENTS.md` rule 5 / `openspec/project.md` (#184/#214), any `ruff format --check` gate (#194), the rev bump (#195), and PB-01..PB-13 Test Mapping backfill.

**Next phase**: `sdd-tasks`.
