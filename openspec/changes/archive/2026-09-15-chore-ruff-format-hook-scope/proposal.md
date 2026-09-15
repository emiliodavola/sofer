# Proposal: chore-ruff-format-hook-scope

**Change**: `2026-09-15-chore-ruff-format-hook-scope` · **Issue**: #216 — *chore: the ruff-format
pre-commit hook rewrites README.md and README_ES.md (its types_or includes markdown)* · **Branch**:
`chore/216-ruff-format-hook-scope` (from `dev`, clean tree)
**Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram mirrors it at
`sdd/2026-09-15-chore-ruff-format-hook-scope/proposal`
**Confirmed handoff**: `preproposal.md` revision 2 (orchestrator-owned; `proposal_ready=true`);
exploration `explore.md` revision 1 (Engram id 1275, SHA-256
`48178a7cb4fe5374aff1e07640f2be2d74975968a4042c887ff2397569a57a71`); research `research.md` (schema
`gentle-ai.sdd-research/v1`, outcome `blocked`, Engram id 1276)
**Size**: ≈25 changed lines of config + YAML comment + test (excluding phase artifacts and the spec
delta) · **Spec delta**: ≈45 lines, one new requirement · **Delivery**: `auto-chain`, review budget
1500 changed lines → **single PR, no chaining required. Ask-on-risk is not triggered** (see *Changed-lines
estimate*)
**Research lane**: **blocked** (harness defect, reported as `Gentleman-Programming/gentle-ai#4633`);
the user adopted a **local-empirical evidence strategy** on 2026-09-15, which this proposal carries as
binding (see *Evidence strategy*)

---

## Intent

`ruff-format` is the repository's only formatter enforcement, and today it rewrites the two READMEs.
The cached upstream manifest for the pinned rev declares:

```yaml
- id: ruff-format
  entry: ruff format --force-exclude
  types_or: [python, pyi, jupyter, markdown]   # markdown is the defect
```

`.pre-commit-config.yaml:7` declares the hook with **no** `types_or` override, so the manifest's file
set is the repository's file set. `uv run pre-commit run ruff-format --all-files` therefore reformats
the fenced Python blocks in `README.md` and `README_ES.md` — recorded in #195's apply phase as
`2 files reformatted, 9 files left unchanged`, after which #195 reverted both files and filed #216.

The upstream list is **not a stable contract**: the cached manifests show `[python, pyi, jupyter]` at
ruff 0.8.0 / 0.15.21 / 0.16.0 and `[…, markdown]` at 0.16.6 / 0.16.7. `markdown` arrived with a manifest
edit this repository never declared, and nothing in the repository detects such an arrival. A
repo-side `types_or` turns the hook's scope into a **repository declaration** that a future rev bump
cannot silently widen.

This change makes that declaration, records why durably, and adds the static guard that keeps it.

**It changes one thing and stops.** The hook stops seeing Markdown; nothing else about formatting
behaviour, the ruff version, or CI moves.

## Confirmed product decisions carried into this proposal (D1–D3)

These are the orchestrator-confirmed handoff (`preproposal.md` revision 2). They are **not** re-opened
here and are **not** re-interviewed in the question round below.

| ID | Decision (user-confirmed) | Consequence this proposal builds on |
| --- | --- | --- |
| D1 | Option **(a)** for #216 — narrow the `ruff-format` hook with an explicit `types_or` in `.pre-commit-config.yaml` so it no longer sees Markdown; document the decision; stay consistent with `[tool.ruff] extend-exclude = ["openspec"]` | One YAML key is the whole mechanical fix; a YAML comment on the edited line is part of the change in every case |
| D2 | Durable home = spec **`process-boundary`**, new requirement (**PB-14** — see the ID correction below); guard test in `tests/test_ci_workflows.py`; the proposal decides between creating a `## Test Mapping` table and mapping the scenario as verify-phase static evidence | The normative carrier is a spec requirement; the enforcing carrier is a pytest guard; the YAML comment is the local carrier |
| D3 | Guard test shape = **key present AND `"markdown" not in types_or`** — asserts the defect class directly and does not go stale on a legitimate future scope widening (adding `toml`/`yaml` must not fail the guard) | The guard is deliberately *not* an equality mirror of the declared list |

## In-repo correction the proposal must record: the next free ID is **PB-14**, not PB-13

The handoff's D2 says "new requirement `PB-13`". That ID is **already taken**:

- `openspec/specs/process-boundary/spec.md` ends at **PB-13** — *Side-effect-free HF token resolution
  and cross-test env hermeticity*, added by change `2026-09-14-fix-hf-token-env-isolation` (issue #176).
- Confirmed independently by the #195 delta text in the archive, which lists
  "`process-boundary` PB-01..PB-09, PB-11..PB-13 | Unchanged".

The **content** of D2 is "a new requirement in `process-boundary`, at the next free ID"; the number in
the handoff is a stale reading of the file. This proposal therefore writes **PB-14** and says so
explicitly rather than renumbering or colliding. This is an in-repo fact, not a product decision, so it
is corrected here instead of being raised in the question round. **If the parent prefers a different
ID for any reason, nothing else in this proposal changes** — one identifier is the whole delta.

## Evidence strategy (user-confirmed override of the blocked web lane)

The research phase returned `outcome: blocked` with **zero validated web claims and nothing fabricated**
(the child session bound none of its four declared web tools; the denial-record write was refused by
the research-scope transport — the record was persisted by the parent on the same canonical path, and
the defect was reported as `Gentleman-Programming/gentle-ai#4633`). The user then chose **local
empirical evidence** over blocking the change. The proposal carries that choice as binding.

| ID | Claim | Load-bearing? | Evidence path this proposal commits to | Evidence class |
| --- | --- | --- | --- | --- |
| R1 | A config-level `types_or` on a remote-repo hook entry **REPLACES** the upstream manifest's `types_or`; it does not merge with it | **Yes** — if it merged, the override would be a no-op and the change would be cosmetic | **The issue's own acceptance check, in the verify phase, against the real ruff 0.16.7 hook materialised on this machine**: `uv run pre-commit run ruff-format --files README.md` MUST report the file as *not a hook input* (`(no files to check)Skipped`, exit 0), and `uv run pre-commit run ruff-format --all-files` MUST show **no markdown batch** (no `2 files reformatted`; the expectation is the 68 Python files unchanged) | Verify-phase **runtime** evidence, pasted with exit codes |
| R2 | `python`, `pyi`, `jupyter` are the exact type tags `identify` (the library pre-commit uses for tag resolution) recognises, so the declared list is not silently inert | Yes — an unrecognised tag would make the declaration vacuous | Verify phase, against the **locally installed `identify` package**: each declared tag MUST resolve as a known tag | Verify-phase **local runtime** evidence |
| R3 | When upstream `ruff-pre-commit` added `markdown` to the hook | No — informs the *why*, not the *what* | **Local pre-commit cache bracket**: absent at 0.15.21, present at 0.16.6 (five cached manifests read in explore §1) | Local-cache evidence, recorded as such (**no external citation exists, and none is claimed**) |
| R4 | The 11-markdown-file batch arithmetic (`2 reformatted + 9 unchanged`) | No — supporting | Re-earned from live `--all-files` output in the verify phase, not inherited from #195's record | Verify-phase runtime evidence |

**The honest shape of this evidence.** R1 is proven by the pinned tool's directly-observed behaviour,
not by upstream documentation. That is **stronger** than a docs citation for the question that matters
("does the override take effect on this pinned hook?") and **weaker** for a different question ("is
replacement the documented contract, and will it hold at some future rev?"). The second question is
answered by the guard test, not by documentation: the guard asserts the *repository's* declaration, so
the repository stops depending on the upstream semantic in order for its scope to be *stated*. What it
cannot do is make the hook behave; that is R1's job, and R1 is therefore an **acceptance gate**, not a
footnote.

## Verified state (evidence, not opinion)

All rows are read from the working tree or transcribed from repository-recorded measurements; explore
§1–§3 carries the file:line provenance.

| Fact | Evidence | Source |
| --- | --- | --- |
| `.pre-commit-config.yaml` has 15 lines, two repos, and **zero comments**; `ruff-format` sits at `:7` with no `types_or` | read this phase | `.pre-commit-config.yaml:1-15` |
| The cached upstream manifest at `v0.16.7` declares `types_or: [python, pyi, jupyter, markdown]` | read in explore (cached hook env `~/.cache/pre-commit/repon1p3j7_t`) | explore §1 |
| The hook's input set is therefore `*.py + *.pyi + *.ipynb + *.md`; the READMEs carry 2 fenced Python blocks each (`README.md:161,560`, `README_ES.md:169,595`) | recorded (#195) + grep (explore) | explore §1 |
| The defect fired once, in #195: `2 files reformatted, 9 files left unchanged` + `68 files left unchanged`; both READMEs reverted | recorded in #195's apply-progress | explore §1 |
| `[tool.ruff] extend-exclude = ["openspec"]` (`pyproject.toml:66`) carries a 4-line rationale comment — **the repository's precedent for a scope decision documented on the line that makes it** | read this phase | `pyproject.toml:56-73` |
| Exactly **one** test reads `.pre-commit-config.yaml`, and it asserts only the repo `rev` list — a hook-level `types_or` is invisible to it | read this phase | `tests/test_ci_workflows.py:463-472` |
| `tests/test_ci_workflows.py` is the established home for static repository-shape contracts, and its module docstring counts "the 18 `ci` Test Mapping rows … plus four tests owned by other capabilities or supporting this one" | read this phase | `tests/test_ci_workflows.py:1-15` |
| **No** CI or release workflow invokes pre-commit and none runs `ruff format --check` → the change has zero CI behaviour impact | recorded + grep | explore §2 |
| The four rule-14 modules and all of `src/sofer/**` are untouched: no source path reads ruff, pre-commit, or a hook scope | grep | explore §3, §7 |
| `process-boundary` has **no** `## Test Mapping` table; only `ci` (`:364`) and `coverage` (`:283`) have one | read this phase | `openspec/specs/process-boundary/spec.md` |
| PB-13 is taken; the file's highest requirement is PB-13 | read this phase | `openspec/specs/process-boundary/spec.md` |
| Repo delta convention: deltas live at `openspec/changes/<change>/specs/<capability>/spec.md`, and canonical specs absorb them at `sdd-sync` | read this phase | archived #177 / #195 deltas |
| `CONTRIBUTING.md:77` is hook-scope-adjacent prose, shares its sentence with #187's defect (`ruff.toml`), and states **no** file scope | read this phase | `CONTRIBUTING.md:77` |

### Unverified at proposal time (carried, not assumed)

1. **R1's replacement semantics** — verify-phase evidence (above); it is an acceptance gate.
2. **Whether the two extra declared tags (`pyi`, `jupyter`) are inert today** — explore says no `.pyi`
   and no `.ipynb` exist in the tree, so they are retained for upstream parity and future notebooks;
   R2 confirms they are at least *valid* tags, so the declaration is honest either way.
3. **Exact pre-change `--all-files` output on this clone** — #195's numbers are recorded, not re-measured;
   verify re-earns them (R4) instead of inheriting them.

## Scope

### In scope (four files, one keystroke wide)

1. `.pre-commit-config.yaml` — add `types_or: [python, pyi, jupyter]` to the `ruff-format` hook entry,
   plus a comment block on that entry recording **why** (upstream widened to `markdown` at 0.16.6; the
   READMEs were rewritten in #195; the explicit list is the repository's declaration and mirrors
   `extend-exclude`), and pointing at the durable home (PB-14).
2. `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md` — the
   **delta**: one `## ADDED Requirements` block for **PB-14**, and (per the decision below) the
   `## Test Mapping` table it introduces.
3. `tests/test_ci_workflows.py` — **one** new guard test asserting the hook entry declares `types_or`
   and that `"markdown" not in types_or`, reusing the module's existing `_load_yaml` and
   `_RUFF_PRE_COMMIT_REPO`; plus the module-docstring sentence that counts tests owned by other
   capabilities (`four` → `five`, and the enumeration gains this guard).
4. SDD phase artifacts for this change.

The canonical `openspec/specs/process-boundary/spec.md` is **not** edited by this change's apply phase —
it absorbs the delta at `sdd-sync`, exactly as #177 and #195 did.

### Out of scope — explicitly not absorbed

| Item | Owner | Why it stays out |
| --- | --- | --- |
| Making `ruff format` format Markdown (adopting a Markdown formatter, reflowing the fenced blocks, changing `quote-style` for docs) | — | Non-goal by construction: the change exists to stop the formatter's reach, not to extend it. Nothing about `[tool.ruff.format]` moves |
| Reformatting `README.md` / `README_ES.md` once and committing the churn (issue's option b) | — | Rejected with option (a); it would also force both READMEs to move together under rule 13 on every future doc edit, and would hand the churn to #180/#183/#190 |
| Any edit to `[tool.ruff]` (`extend-exclude`, `required-version`, `line-length`) | — | The alternative mechanism (a′: add the READMEs to `extend-exclude`) was recorded in explore §6 and **not** chosen: it would additionally shield the READMEs from *direct* ruff runs and from any future gate, which is a different decision than "what the hook sees" |
| Bumping the `ruff-pre-commit` `rev` or the dev pin / refreshing `uv.lock` | #195 owns the pin chain; the version wave owns bumps | The change is deliberately version-neutral: it is *because* the upstream list is version-unstable that the scope is declared repo-side. A rev bump here would confound the evidence and the diff |
| Arming any `ruff format --check` gate (CI, pre-push, or otherwise) | **#194** | PB-10's *No CI gate was armed* scenario asserts **zero** `format --check` invocations under `.github/workflows/**`; this change leaves that scenario passing and must state the relationship in the PR body (issue requirement) |
| `CONTRIBUTING.md:77` prose (and, in particular, its nonexistent `ruff.toml` path) | **#187** | Same sentence, different defect; #195's precedent is "resolve by ordering, never by merging concerns". Whether contributor prose *should* change is question Q4 below, and is **not** an assumption this proposal acts on |
| `AGENTS.md` rule 5 and `openspec/project.md:70,82` (hook order, stale versions) | #184 / #187 / #214 documentation wave | Adjacent drift with named owners; no test asserts rule 5's text, and adding a second guard for one key is not this change's job |
| Any `src/sofer/**` edit | — | Nothing in `src/` reads ruff or pre-commit; the four rule-14 modules MUST NOT appear in the diff |
| The `ci` `## Purpose` enumeration (`ci/spec.md:5-11`, already stale for CI-07/CI-08) | left stale by #195 | Its own defect; fixing it here would edit canonical prose for another requirement's class |

## Approach

Three carriers, each with a distinct job. None of them is redundant:

| Carrier | Job | Enforced by |
| --- | --- | --- |
| `types_or: [python, pyi, jupyter]` on the hook entry | **Decides** what the hook sees | pre-commit / the pinned hook (R1 — verify-phase acceptance) |
| YAML comment on the edited entry | **Explains on the line a future editor touches** — why Markdown is out, that upstream widened unilaterally, and where the decision lives | Nothing mechanical; it is a human-durable note (accepted: comments can be deleted, see risks) |
| PB-14 in `process-boundary` + guard test in `tests/test_ci_workflows.py` | **Makes the scope a standing contract**: the requirement states the invariant, the guard fails the suite if the declaration is removed or Markdown returns | `uv run pytest tests/ -q` |

The YAML comment mirrors the existing precedent in `pyproject.toml:63-66`, where the sibling scope
decision (`extend-exclude = ["openspec"]`) is documented on the line that makes it. Option (a) and the
existing documentation become symmetrical: **two scope decisions, two comments, one vocabulary.**

### Guard test

```text
tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown
  config = _load_yaml(".pre-commit-config.yaml")
  entry  = the ruff-pre-commit repo entry's hook with id == "ruff-format"
  1. the entry SHALL declare `types_or`                       # the contract (a rev bump cannot remove it silently)
  2. `"markdown" not in entry["types_or"]`                    # the defect class, asserted directly
```

Four properties of this shape, all deliberate:

- **It is a defect-class assertion, not a mirror.** Adding a legitimate new type (`toml`, `yaml`) MUST
  keep the guard green; only `markdown` fails it. An equality assertion would force every future
  scope widening to edit a test literal, which is exactly the staleness the user rejected in D3.
- **It is not vacuous.** Assertion 1 catches a silent deletion of the key (the shape a future edit or
  a re-vendored config would take); assertion 2 catches the regression. Both are needed: present-but-
  with-markdown passes 1 and fails 2, and absent-key fails 1.
- **It reuses existing helpers.** `_load_yaml` and `_RUFF_PRE_COMMIT_REPO` already exist (AGENTS.md
  rule 4); the guard adds no import, no helper, and no new module. It also reuses the same
  repo-entry lookup the CI-08 rev guard uses, so the two guards read the same object.
- **It is the TDD red.** Applied against the **unmodified** hook entry the guard fails (no `types_or`
  key); it goes green with the config line. Neither gate is decorative.

**What the guard cannot prove, stated plainly:** the guard asserts a *declaration*. It cannot observe
that pre-commit honours it (R1) — that would mean spawning the hook from the suite, a dependency class
the repository keeps out of pytest (#195 §7, AGENTS.md rule 9). The declaration proof and the
behavioural proof are two different pieces of evidence; the change must supply both, which is why R1's
`--files README.md` run is an acceptance gate and not an optional extra.

### Spec delta plan

**File**: `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/specs/process-boundary/spec.md`
(delta, not full spec — the repo's convention; the canonical file is untouched until `sdd-sync`).

**Block**: `## ADDED Requirements` → `### Requirement: <title> (PB-14)`, additive only: PB-01..PB-13 keep
their clauses and scenarios byte-for-byte, so archive-time replacement of a canonical block would be a
lossy no-op (the #177/#195 framing).

**Requirement content (normative intent, to be finalised in the design phase):**

> The `ruff-format` pre-commit hook's file-type scope SHALL be a repository declaration, not an
> inherited upstream default: the `astral-sh/ruff-pre-commit` entry in `.pre-commit-config.yaml` SHALL
> declare an explicit `types_or` that names the file types the repository intends the formatter to see
> (`python`, `pyi`, `jupyter`), and Markdown SHALL NOT be among them. The decision is deliberate and
> rationale-bearing: upstream widened the manifest's `types_or` to include `markdown` between
> `ruff-pre-commit` 0.15.21 and 0.16.6 without this repository changing anything, and the pinned hook
> then rewrote the fenced Python inside `README.md` and `README_ES.md` (recorded in change
> `2026-09-15-chore-ruff-single-authority`'s apply phase; issue #216). The declared scope SHALL
> therefore NOT be read as a mirror of the upstream default — a rev bump SHALL NOT widen it silently —
> and it SHALL stay consistent in vocabulary with the sibling scope decision
> `[tool.ruff] extend-exclude = ["openspec"]`.
>
> This requirement constrains **the hook only**. `types_or` is a pre-commit filter, not a ruff setting:
> a direct `ruff format <path>` (and any future gate armed by issue #194) still sees Markdown, and this
> requirement SHALL NOT be read as narrowing the formatter itself, as adopting a Markdown formatter, or
> as arming any gate. Issue #194 SHALL retain ownership of whether a `format --check` gate is armed and
> over which paths; this requirement SHALL arm no CI step and SHALL add no workflow file.
>
> The declaration SHALL be statically guarded in `tests/test_ci_workflows.py` (the established home for
> static repository-shape contracts): the hook entry SHALL declare `types_or`, and `markdown` SHALL NOT
> appear in it. The guard SHALL assert the defect class rather than mirroring the declared list, so a
> legitimate future widening to another type SHALL keep it green.

**Scenarios (intent, mapped 1:1 below):**

- **S1 — the hook declares its own scope** (pytest): the entry declares `types_or` and Markdown is absent.
- **S2 — the hook no longer receives Markdown, and the READMEs are untouched** (verify-phase runtime):
  `--files README.md` reports the file as not a hook input, and `--all-files` shows no Markdown batch.

### The `## Test Mapping` decision (D2's open question) — **create the table**

**Decision: create a `## Test Mapping` section in `process-boundary`, carrying the PB-14 rows.** The
delta introduces it; `sdd-sync` appends it to the canonical file.

*Why, on evidence:*

1. **The repository's canonical index for scenario-to-verification is that table**, and its prose states
   the rule explicitly: *"Every scenario SHALL map to a green test or to verify-phase static evidence
   (AGENTS.md rule 6; rules.specs). Static workflow/config assertions live in
   `tests/test_ci_workflows.py`"* (`ci/spec.md:366-368`). PB-14 S1 **is** a green pytest test — the
   classification that table exists to record.
2. **The user's stated intent is durable non-re-litigation.** A future reader who opens
   `process-boundary` to learn what owns the hook's file scope should see, in the capability file
   itself, that a guard enforces it. Without the table, the enforcement link lives only inside the
   change's archived delta.
3. **It is cheap and additive**: one new section, one or two rows, no existing requirement text
   touched. `process-boundary`'s table-less state is the *absence* of a convention, not a
   counter-convention — #177 had no pytest-mapped scenario at all, so it had nothing to index.

*Cost, stated honestly:* the new table will initially contain only PB-14 rows, while PB-01..PB-13 have
none. **Backfilling those rows is a named non-goal of this change** (their evidence classes are already
stated in their own scenario text — PB-10's blockquote, PB-09's fixtures, PB-11/PB-12/PB-13's scenario
prose) and belongs to whoever owns that backfill, not to a hook-scope chore.

*Named fallback (T2), so the design phase can move it without renegotiating anything else:* if the
design or review phase judges a one-row table in a canonical file to be worse than the coupling, map
S1 to the guard test inside the delta's own `## Rule-6 resolution` prose — the **#177 precedent**, which
explicitly resolved rule 6 in-delta and left `process-boundary` table-less. **Nothing else changes**:
the requirement text, the guard test, the YAML comment, and S2's evidence class are identical under
either option. This is a declaration-granularity choice, not a product tradeoff — which is why it is
decided here with a fallback rather than raised as a product question.

### Rule 6 (scenario ↔ test) resolution

| Scenario | Verification | Class |
| --- | --- | --- |
| PB-14 S1 — the hook declares its own scope and excludes Markdown | `tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown` | **Green test** (1:1, non-vacuous, red before the config change) |
| PB-14 S2 — the hook no longer receives Markdown; READMEs unchanged | Verify-phase runtime evidence — `uv run pre-commit run ruff-format --files README.md` and `--all-files`, with `git diff --stat -- README.md README_ES.md` empty | **Verify-phase runtime evidence** — the same class the repo already uses for `ci` CI-01 S2, CI-07's runtime rows, CI-08 S4, and every PB-10 scenario (asserting it from pytest would mean spawning `pre-commit` and its cached hook environment from the suite) |

No scenario is left unmapped and **no vacuous test is invented**. Two scenarios, two mappings, one of
each class — a split the repo already uses and that D2 and D3 already assume.

### Module-docstring accuracy (a real, small impact of the guard)

`tests/test_ci_workflows.py`'s docstring currently reads: *"the scenario-verifying tests are the 18
`ci` Test Mapping rows whose verification names a test in this module, plus four tests owned by other
capabilities or supporting this one — the two `coverage` COV-06 guards, the CodeQL private-window
guard, and `test_ci_workflow_files_present`"*. The new guard is **not** a `ci` row (it maps to
`process-boundary` PB-14), so the count becomes `five` and the enumeration gains it. Leaving the
docstring stale would be a second, self-inflicted inaccuracy in the very file the change edits.

## Acceptance-criteria traceability (issue #216, as supplied by the parent)

| AC | Criterion (transcription) | How this change satisfies it | Evidence class |
| --- | --- | --- | --- |
| 1 | The hook no longer touches `README.md` / `README_ES.md` | The `types_or` override removes Markdown from the hook's input set; proved behaviourally | **Verify-phase runtime** — `uv run pre-commit run ruff-format --files README.md` → `(no files to check)Skipped`, exit 0; and `git diff --stat -- README.md README_ES.md` empty after `--all-files`. **R1's acceptance gate** |
| 2 | `uv run pre-commit run ruff-format --all-files` shows no Markdown batch | The 11-file Markdown batch disappears; only the 68 tracked Python files remain in scope | **Verify-phase runtime** — no `2 files reformatted`, no `files were modified by this hook` (R4 re-earns the pre-change numbers) |
| 3 | The decision is recorded **with its reasoning** | Three carriers: PB-14 states the invariant and the upstream history; the YAML comment states it where a future editor edits; the guard test enforces it. The PR body additionally states the #194 relationship (explore §3, issue requirement) and points at the durable home | **Test** (the invariant) + **static/diff evidence** (the comment, the requirement text, the PR body) |

Two headline caveats the verify phase MUST respect, both measured in #195 — they are how a false "the
fix does not work" reading happens:

1. The hook's `entry` is `ruff format --force-exclude`, a **fixing** surface: it exits 0 *after*
   rewriting. Exit code alone never proves the file was untouched. The discriminating observation is
   the hook's **file-list output**.
2. pre-commit detects "files were modified" via `git diff`, which cannot see an **untracked** file.
   `README.md` is tracked, so a regression *would* surface as `Failed` + `files were modified` — the
   AC check is sound on this file; a throwaway untracked probe would not be.

## Changed-lines estimate and review workload

| File | Change | Changed lines (add+del) |
| --- | --- | --- |
| `.pre-commit-config.yaml` | 1 key added + 1 comment block (~3–4 lines) on one hook entry | ≈6–8 |
| `tests/test_ci_workflows.py` | 1 guard test (~12–18 lines incl. docstring) + module-docstring sentence | ≈16–22 |
| `openspec/changes/…/specs/process-boundary/spec.md` | PB-14 requirement + 2 scenarios + `## Test Mapping` rows | ≈45 |
| **Functional + spec subtotal** | | **≈70 (60–80)** |
| SDD phase artifacts (proposal → archive-report under the change root) | prospective documentation text | not counted as product size (repo precedent: #177, #195 both list artifacts separately) |

**Delivery decision: single PR.** ≈70 lines against a 1500-line budget is two orders of magnitude
inside it; nothing here is a candidate for chaining, and `ask-on-risk` is not triggered. Even if the
parent counts phase artifacts in the diff (≈500–700 lines for the whole SDD cycle), the change stays
inside the budget — and if that ever ceased to be true, the natural slice would be *config + guard test
+ delta* (one reviewable work unit; the guard, the scenario it satisfies, and the requirement text must
never be split across slices, per rule 6).

## Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| **R1 is wrong** — a config-level `types_or` merges with (rather than replaces) the manifest's, so the override is a no-op | Low (pre-commit's override list is documented; the pinned hook's behaviour is observable) but **not yet observed on this machine** | The change would look correct in review, pass its guard test, and fail its purpose silently — the worst failure mode available here | AC1's `--files README.md` run **is** the acceptance gate: if the file is still handed to ruff the fix has not landed, and the run says so loudly. R1 is verified *before* the change is called complete, never assumed |
| **The guard test proves only the declaration** — a future pre-commit version changes the replacement semantic and the hook starts receiving Markdown again while the guard stays green | Low | The defect class returns without a red suite | Named explicitly in the requirement and in this proposal: the guard is the *declaration* proof, R1/AC1 is the *behaviour* proof. The repository keeps a repo-side declaration either way, which is what stops the *silent* widening (the actual #216 mechanism) |
| **The YAML comment is deleted** by a reformat, a merge, or a future hand-edit of the file, removing the on-the-line explanation | Medium — comments carry no mechanical enforcement | The *why* is lost at the edit site; a future contributor may re-litigate | Accepted: PB-14 + the guard test carry the decision normatively; the comment is the cheap local half, matching the `extend-exclude` precedent, not a load-bearing one |
| **A future contributor wants the READMEs formatted** and finds the guard in the way | Medium over time | Friction: a deliberate scope widening now requires a spec edit, not just a YAML edit | This is the **intended** coupling, not a defect: the guard fails on `markdown` specifically because that is the defect class. A deliberate change updates PB-14 and the guard in the same change — which is exactly the "do not re-litigate silently" property the decision was made for. Q1/Q2 below check that this framing matches the user's intent |
| **Markdown code blocks stop being formatter-checked at all** | Certain by design | Fenced Python in the READMEs (and, when someone stages them, in `docs/`/templates) drifts from `ruff format`'s shape | Deliberate trade-off: the blocks are illustrative call chains (`sofer_init(...)`, `sofer_scan_dry_run(...)`) whose alignment is human-authored for readability, and #195/#216 record that the formatter's rewrite of them is *noise*, not a fix. **No enforced coverage is lost**: PB-10's and CI-08's evidence commands are already path-scoped to `src/ tests/ scripts/`, none of which includes Markdown |
| **`pyi` / `jupyter` are declared but inert** (no `.pyi`, no `.ipynb` in the tree) | Certain today | A reader may mistake the list for a statement about files that exist | Retained deliberately for upstream parity and future notebooks; R2 confirms they are valid tags (not silently inert identifiers), and the requirement text says the list names *intended* types. No `.ipynb` adoption is implied |
| **The ID collision recurs** (PB-13 vs PB-14) across the delta, the guard docstring, and the PR body | Medium if the handoff's number is copied forward | A wrong requirement ID in the requirement, the mapping table, and the test docstring | Corrected here with the evidence (`spec.md` ends at PB-13; the #195 delta confirms PB-11..PB-13 exist). The design and apply phases carry **PB-14**; one grep of the canonical file confirms it |
| **The new `## Test Mapping` table with one row reads as an incomplete index** | Low–Medium | Review friction; a reviewer may ask for PB-10..PB-13 rows | Stated in the delta as a named non-goal with its reason; T2 (in-delta rule-6 resolution, no table) is the named fallback if review prefers it |
| **The change quietly widens** (someone also touches `pyproject.toml`, the rev, CI, or the READMEs) | Low, but this is a chore with a tempting neighbourhood | Scope creep on a 4-file change; would confound R1's evidence (a rev bump changes the manifest) and violate rule 13 if a README moved | Every out-of-scope item above has a named owner; the success criteria include explicit "zero paths" assertions for `pyproject.toml`, `.github/workflows/**`, `src/sofer/**`, and both READMEs |
| **Verify misreads the fixing hook** (exit 0 after a rewrite read as "no rewrite") | Medium — #195 measured exactly this trap | A false green on AC1/AC2 | The two caveats are transcribed above and are part of the acceptance evidence: the discriminating observation is the hook's file-list output plus `git diff --stat`, never the exit code alone |

## Rollback

**Trivial, complete, and immediate.** Revert the single commit: the `types_or` key and its comment
disappear, the guard test and the delta disappear with it, and the canonical `process-boundary` spec is
untouched until `sdd-sync` (so a pre-sync revert leaves the canonical specs byte-for-byte as they are).

- **No runtime behaviour in the package**, no data or format migration, no dependency change, no
  published artefact, no CI step, no version move.
- **No hook-environment invalidation.** Changing `types_or` does not change the repo `rev`, the
  `language`, or any `additional_dependencies`, so pre-commit's cached hook environment stays valid:
  the config change takes effect on the next `pre-commit run` with no reinstall, and the revert does
  too. Developers need no `pre-commit clean`, and nothing is left behind on a clone.
- After a revert, the repository returns to "markdown in scope" — the pre-#216 state, with the #216
  issue still open and the exploration/research records still valid.

## Success criteria

1. `.pre-commit-config.yaml`'s `ruff-format` hook entry declares
   `types_or: [python, pyi, jupyter]`, and the entry carries a comment stating why Markdown is out and
   naming PB-14.
2. **R1 / AC1**: `uv run pre-commit run ruff-format --files README.md` reports the file as **not a hook
   input** (`(no files to check)Skipped`) and exits 0; output pasted in the verify report.
3. **AC2**: `uv run pre-commit run ruff-format --all-files` shows **no Markdown batch** — no
   `2 files reformatted`, no `files were modified by this hook` — and `git diff --stat -- README.md
   README_ES.md` is empty.
4. **R2**: each declared tag (`python`, `pyi`, `jupyter`) resolves as a valid tag in the locally
   installed `identify` package.
5. `tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown` fails against the **unmodified**
   hook entry (no `types_or`) and passes after the config change — red then green, both pasted.
6. `uv run pytest tests/ -q` is green with exactly **+1** collected test and 0 failures, 0 newly
   skipped; the `tests/test_ci_workflows.py` module docstring's cross-capability count is updated
   (`four` → `five`).
7. `uv run ruff check src/ tests/ scripts/` and `uv run mypy src/ scripts/` are clean (the enforced
   commands).
8. `git diff --stat` contains **exactly**: `.pre-commit-config.yaml`, `tests/test_ci_workflows.py`, and
   the change's spec-delta / artifact paths. **Zero** `pyproject.toml`, zero `.github/workflows/**`,
   zero `src/sofer/**`, zero `README.md` / `README_ES.md`, zero `uv.lock` paths.
9. `git grep -n "format --check" -- .github/workflows/` returns zero matches before and after (PB-10's
   no-gate scenario keeps passing; #194 keeps its ownership), and no `pre-commit` invocation appears
   under `.github/`.
10. `CONTRIBUTING.md` and `AGENTS.md` are unchanged (any contributor-facing prose change is Q4's
    question and, if wanted later, another change's edit).

## Open items passed forward (not decisions)

1. **R1's behavioural proof** — discharged only by AC1/AC2's pasted output; it gates completion.
2. **R2/R4 evidence** — local `identify` validation and re-earned `--all-files` arithmetic, in verify.
3. **PB-14's exact requirement wording** (title, clause boundaries, scenario phrasing) — finalised in
   the design phase against the intent and the two scenarios above.
4. **Test-Mapping table vs in-delta rule-6 resolution** — decided here (table), with T2 named as the
   fallback; the design phase may move it without further product input.
5. **The PR body's #194 relationship statement** (issue requirement) — drafted at apply time from the
   paragraph in *Scope → Out of scope* and from explore §3's independence argument.

## Proposal question round

These questions are meant to improve the product understanding behind a change that looks purely
mechanical. They are about **policy, product surface, and tradeoffs** — not about test commands, PR
shape, or line budgets. Answer them, correct the framing, ask for a second round, or **skip**: this
proposal is written to remain valid if every question is skipped, and the *Assumptions* block below
records exactly what "skip" means.

**Q1 — Are the fenced Python blocks in `README.md` / `README_ES.md` *source* or *illustrative prose*?**
The whole change rests on the answer. If docs snippets are source that must satisfy the formatter, the
correct direction is the opposite one (issue option b: format them once, accept the churn), and this
proposal's intent should be inverted. If they are illustrative, human-aligned pseudo-code whose
formatter rewrite is noise, option (a) is right and no formatter checking is lost.
*Assumptions guarded:* that the READMEs' code blocks are deliberately hand-shaped for readability; that
"Markdown leaves the formatter's scope" is a *decision*, not an accidental regression; and therefore
that PB-14's normative intent (repository-declared scope) is the right invariant to state. **Depends on
this answer:** the Intent, D1's framing, the "Markdown stops being formatter-checked" risk row, and PB-14's
requirement text.

**Q2 — When a future maintainer hand-bumps `ruff-pre-commit` and upstream widens the manifest again
(say `toml`, `yaml`, or a second Markdown-ish tag), should this repository follow upstream by default or
decide deliberately each time?**
The change asserts "deliberately, each time" and encodes it by making the declaration repo-side with a
`markdown`-specific guard. The alternative reading — "follow upstream, override only the one type that
annoys us" — would argue for a narrower comment and a differently worded requirement.
*Assumptions guarded:* that the repository's declared scope is an authority rather than a patch over
upstream; that the guard's ceiling (`no markdown`) is the right one rather than "must equal upstream";
and that a deliberate widening should require a spec edit. **Depends on this answer:** the *Guard test*
section, the risk row about a future contributor wanting the READMEs formatted, and PB-14's
"SHALL NOT be read as a mirror of the upstream default" clause.

**Q3 — Rule 13 requires `README.md` and `README_ES.md` to move together. Does a future deliberate
formatting of the fenced blocks in one README oblige the same edit in the other (and therefore a
translation-side cost), and does that make "keep Markdown out of the hook" the cheaper long-term
posture?**
The change assumes the mirroring rule is a real product constraint, which is *why* churn in the
READMEs is expensive rather than cosmetic. If the pair were allowed to diverge on code-block
formatting, the cost calculus behind option (a) weakens and a future gate over Markdown becomes more
attractive.
*Assumptions guarded:* that the README pair is a translated product surface with a synchronised
lifecycle; that the cost of formatter churn lands on documentation/translation work rather than on
source; and that "docs are out of formatter scope" is a stable posture rather than a temporary one.
**Depends on this answer:** the "Markdown stops being formatter-checked" tradeoff paragraph, the
"future contributor wants to format the READMEs" risk, and Q1's cost framing.

**Q4 — Does "recorded with its reasoning" (AC3) mean *normative spec + machine guard + on-the-line
comment* (this proposal's reading), or must a contributor reading `CONTRIBUTING.md` also be told that
Markdown is outside the hook's scope and that a direct `ruff format <path>` still sees it?**
`CONTRIBUTING.md:77` is the natural prose home and is currently untouched here, partly because #187
owns the same sentence. If contributor-facing prose is part of the requirement, this change's scope
grows by a sentence (and an ordering decision against #187), and the answer changes what "durable"
means for the reader who never opens `openspec/`.
*Assumptions guarded:* that a spec requirement plus a pytest guard plus a YAML comment satisfies
"documented durably" for contributors; that the #187 collision is a reason to stay out of that sentence;
and that a contributor needs no prose warning about direct `ruff format` (the #194 relationship lives in
the PR body and in PB-14). **Depends on this answer:** the *Scope → Out of scope* row for
`CONTRIBUTING.md:77`, success criterion 10, and the "word 'formatter scope' may be read as global" risk.

**Q5 — When #194 eventually arms a `ruff format --check` gate, should it be *required* to stay
path-scoped (`src/ tests/ scripts/`, so Markdown never enters CI), or is a repository-wide `.`-scoped
gate acceptable once Markdown is out of the hook?**
This change deliberately decides nothing about path scope (both PB-10's and CI-08's evidence commands
are already path-scoped, and #194 owns the gate). If the product intent is that a future gate *must*
stay path-scoped, that is a constraint worth stating somewhere normatively — possibly in PB-14, possibly
in #194's own change.
*Assumptions guarded:* that the hook-scope decision and the future-gate decision are independent; that
no path-scope clause needs to ride along here; and that a `.`-scoped gate would be rejected today
because it would immediately flag the two READMEs' code blocks. **Depends on this answer:** the
`types_or`-is-not-a-ruff-setting paragraph in PB-14, the #194 row in *Out of scope*, and success
criterion 9.

### Assumptions this proposal stands on if every question is skipped

1. The READMEs' fenced Python is illustrative prose, deliberately human-shaped, and formatter
   reformatting it is noise rather than a fix (Q1, Q3).
2. A repository-declared hook scope is an authority, not a patch: a rev bump MUST NOT widen it silently
   (Q2).
3. `CONTRIBUTING.md` / `AGENTS.md` prose is **not** required to carry this decision; the spec
   requirement, the guard test, and the YAML comment are sufficient, and #187 keeps ownership of the
   sentence this change stays out of (Q4).
4. Hook scope and any future CI gate are independent decisions, and no path-scope clause is added here
   (Q5).
5. The repository's rule-6 index for a pytest-mapped scenario is a capability `## Test Mapping` table,
   so `process-boundary` gets one (decided in this proposal, movable to the #177 in-delta form).
6. The next free `process-boundary` requirement ID is **PB-14** (in-repo fact, corrected above).

## Provenance read in this phase

`openspec/changes/2026-09-15-chore-ruff-format-hook-scope/{explore.md,research.md,preproposal.md}` ·
Engram observations 1275 / 1276 / 1277 · `.pre-commit-config.yaml` · `pyproject.toml:40-79` ·
`tests/test_ci_workflows.py:1-15, 29-106, 463-497` · `openspec/specs/process-boundary/spec.md`
(PB-01..PB-13, PB-10 in full) · `openspec/specs/ci/spec.md:360-390` (Test Mapping shape) ·
`CONTRIBUTING.md:73-79` · `openspec/changes/archive/2026-09-15-chore-ruff-single-authority/{proposal.md,
specs/ci/spec.md,specs/process-boundary/spec.md}` · `openspec/changes/archive/2026-09-14-chore-ruff-format-drift/specs/process-boundary/spec.md`
· `openspec/changes/` inventory (delta convention).
    
## Question round outcome
    
The orchestrator relayed the full round (Q1–Q5) to the user in the user's language on 2026-09-15.
The user chose **skip all questions**. The six assumptions recorded above are thereby confirmed as the
standing product intent of this change, and the proposal text (including PB-14's intended wording, the
guard-test scope, and the Out-of-scope rows) is final for the design phase. No second question round was
requested.
