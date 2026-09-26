# Proposal: chore-ruff-single-authority

**Change**: `2026-09-15-chore-ruff-single-authority` · **Issue**: #195 — *chore: two authoritative ruff
versions in play (pre-commit v0.16.7 vs ambient 0.16.0)* · **Branch**:
`chore/195-ruff-single-authority` (from `dev@5a2ae38`)
**Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram mirrors it at
`sdd/2026-09-15-chore-ruff-single-authority/proposal`
**Confirmed handoff**: `preproposal.md` (orchestrator-owned; four product decisions D1–D4, no open
product questions) · **Exploration**: `explore.md`, SHA-256
`92a8861e7b9a833cc31a35d6d5e92419c019ae6706b6d3d47a4c067d6e4cb351`
**Size**: ≈105 changed lines of code/config/test + ≈50 lines of spec delta (excluding SDD phase
artifacts) · **Delivery**: `auto-chain`, review budget 400 changed lines · **Research lane**:
de-selected by the maintainer, so no external citations exist (D4)

## Intent

Two tools format and lint this repository, and they disagree about which ruff they are:
`.pre-commit-config.yaml:3` pins `ruff-pre-commit` `rev: v0.16.7`, while the dev group declares
`ruff>=0.9.0` (`pyproject.toml:47`) and `uv.lock:2033` resolves `0.16.0`. The hook is a *different
implementation* of the formatter than the binary PB-10's gate invokes, with no mechanism that makes
the disagreement visible — and `openspec/specs/process-boundary/spec.md:258` currently states that
this mismatch *"SHALL stay unaddressed here and SHALL be owned by issue #195"*. This **is** #195.

The change makes one version authoritative across all three declarations, makes a wrong version fail
loudly instead of disagreeing quietly, adds the static guard that keeps the declarations equal, and
corrects PB-10's now-false deferral sentence. It adds no CI step: enforcement of the *staged-file*
formatter stays the local hook, and #194 keeps owning the un-staged-file gap (PB-10 `:286`).

## Confirmed decisions carried into this proposal (D1–D4)

| ID | Decision (maintainer-confirmed) | Consequence this proposal builds on |
| --- | --- | --- |
| D1 | Authoritative version is **0.16.7** (the pre-commit rev) | Dev pin becomes `ruff==0.16.7`; `uv.lock` refreshed in the same change (AC5) |
| D2 | Enforcement is **`[tool.ruff] required-version` + a static guard test** | A third declaration site, plus a test forcing all three equal; a contributor on another ruff now gets an error — accepted |
| D3 | AC3 is evidenced by **exercising the real hook** | `pre-commit install` in this clone + a misformatted throwaway file, both verdicts recorded |
| D4 | **Research lane de-selected** (two `sdd-research` launches timed out, 0 turns) | No external citations: upstream semantics are labelled *measured* or *unverified*, never asserted from documentation |

## Verified state (evidence, not opinion)

| Fact | Evidence | Source |
| --- | --- | --- |
| Ambient ruff is `0.16.0`; hook rev is `v0.16.7`; dev group floats `ruff>=0.9.0` | `pyproject.toml:47`, `.pre-commit-config.yaml:3`, `uv.lock:2033` + specifier `uv.lock:2120` | handoff + re-read this phase |
| 0.16.7 and 0.16.0 give **identical** verdicts on this tree | `uvx ruff@0.16.7 format --check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/ scripts/` → both `68 files already formatted`, exit 0 | handoff (orchestrator measurement) — retires explore's "0.16.7 is unmeasured" |
| `required-version` fails **hard**, on both subcommands | probe with `required-version = "==99.0.0"`: `ruff check .` and `ruff format --check .` both fail — `Cause: Required version '==99.0.0' does not match the running version '0.16.0'`; a bogus key control was rejected | handoff (orchestrator measurement). Semantics recorded as **measured**, not as documented upstream |
| The hook has **never run here** | `.git/hooks/pre-commit` ENOENT; no `0.16.7` under the pre-commit cache (newest cached rev: `0.16.6`) | explore §2.3; handoff D3 |
| The hook's ruff comes from the `rev` alone | cached clone pins `"ruff==X.Y.Z"` in its own `pyproject.toml` and builds a per-rev venv; `.pre-commit-config.yaml` passes no `additional_dependencies` | explore §3.1 |
| **Zero** tests reference ruff; nothing in `tests/` reads `.pre-commit-config.yaml` | `grep -rn "ruff\|pre-commit-config\|required-version" tests/` → no matches | re-verified this phase |
| No runtime code reads a ruff version | only ruff reference in `src/`: `src/sofer/mcp_server.py:1` — `# ruff: noqa: E501`, a directive, not a version | re-verified this phase |
| CI resolves ruff from the lock, never from the hook | `ci.yml:19` and `release.yml:29` run `uv run ruff check src/ tests/ scripts/` after `uv sync`; CI never invokes pre-commit | re-verified this phase |
| Exactly one canonical clause names versions | `process-boundary/spec.md:258` (PB-10 body); **0** spec scenarios name one | handoff + re-read |
| `ci` has the pin-equality precedent and the only mapping table for this test file | `ci/spec.md:215-251` (CI-07), `ci/spec.md:285-296` (Test Mapping, "Static workflow/config assertions live in `tests/test_ci_workflows.py`") | re-verified this phase |

### Unverified at proposal time (carried, not assumed)

1. **Does upstream tag `v0.16.7` exist?** No local materialisation, no network in this phase.
   Consequence if it does not: every hooked commit fails for everyone. D3's evidence path is the
   materialisation probe and is the mitigation.
2. **Exact `uv.lock` delta shape** for a 0.16.7 refresh (explore §4's lock arithmetic is reasoned,
   not measured).
3. **`required-version` on 0.16.7 specifically** — the mechanism was measured with the ambient
   0.16.0 binary; the key is not version-specific in any evidence I hold, but that is **unverified**.

## Scope

### In scope

1. `pyproject.toml:47` — dev pin `"ruff>=0.9.0"` → `"ruff==0.16.7"` (exact, not a floor).
2. `pyproject.toml` `[tool.ruff]` (`:56-58`) — add `required-version = "==0.16.7"`.
3. `uv.lock` — refreshed in the same change (AC5); `ruff` block (`:2032-2054`) and dev specifier
   (`:2120`).
4. `tests/test_ci_workflows.py` — three static guard tests (below), reusing the module's existing
   `_read_text` / `_load_toml` / `_load_yaml` helpers.
5. `CONTRIBUTING.md:77` — the sentence gains the version (AC1). **The sentence keeps its stale
   `ruff.toml` path**: that defect is #187.
6. `process-boundary` delta — PB-10's deferral sentence corrected (mandatory; exact text below).
7. `ci` delta — new requirement **CI-08** carrying the declaration-equality contract plus its
   scenario-to-test mapping.
8. SDD artifacts for this change.

### Out of scope — explicitly not absorbed

| Item | Owner | Why it stays out |
| --- | --- | --- |
| Arming a `ruff format --check` CI step | **#194** | PB-10 `:286` assigns recurrence there; its "No CI gate was armed" scenario (`:281-286`) asserts zero `format --check` invocations under `.github/workflows/**` and MUST keep passing |
| `CONTRIBUTING.md:77`'s `ruff.toml` that does not exist (`ENOENT`) | **#187** | Same sentence, different defect. Interaction noted: both changes touch line 77 → resolve by ordering, never by merging concerns |
| `CONTRIBUTING.md:28-29` documenting `mypy src/` / `ruff check src/ tests/` when CI runs `src/ tests/ scripts/` | **#212** | Same class, separate issue. AC4's workspace wording is corrected by *running the enforced commands*, not by editing those lines |
| `openspec/project.md:82` ("ruff 0.16.0") and `AGENTS.md` version statements | **#184 / #187 / #214** documentation wave | Referenced only. `openspec/config.yaml:12` is gitignored (`.gitignore:57`), so it is local-only state, not change-bearing |
| Historical SDD prose naming the mismatch (`openspec/changes/archive/**`, incl. the #177/#178 records) | history | Never edited — it is a record, not state |
| Any `src/sofer/**` edit | — | The four rule-14 modules are untouched: 0.16.7 reformats nothing on this tree (handoff measurement), so no formatting commit is expected. **If one appears anyway, it is a scope change to surface, not absorb** |

## Approach

One version, three declarations, one test that forces them equal, one clause stating the invariant.

| # | Surface | Change | Enforces |
| --- | --- | --- | --- |
| 1 | `pyproject.toml` dev group | `ruff==0.16.7` (exact) | The binary `uv run ruff …`, the CI lint job (`ci.yml:19`, `release.yml:29`) and every local `uv sync` resolve |
| 2 | `pyproject.toml` `[tool.ruff]` | `required-version = "==0.16.7"` | A drifted environment **fails loudly** (`ruff check` and `ruff format` both abort at config load — measured) |
| 3 | `.pre-commit-config.yaml:3` | **unchanged** (`v0.16.7` already) | The hook's isolated per-rev venv; the project environment is never consulted (explore §3.1) |
| 4 | `tests/test_ci_workflows.py` | three guard tests | The three declarations cannot drift apart again without a red suite |

**The guard extracts, it does not hardcode.** Each test derives `X.Y.Z` from the `pyproject.toml` dev
pin and then asserts the other declarations agree — so a future bump edits declarations only, never a
test literal. That is also why this change introduces **no hardcoded value in the sense of the
repository rule**: the pin is a build/toolchain declaration of the same class as `.python-version`
(CI-07), not a runtime default; no `src/sofer/` code path reads it (verified above), and the only
literal is the single authoritative version value, mirrored deliberately and guarded mechanically.

### Guard tests (1:1 with the CI-08 scenarios)

| Test | Assertion |
| --- | --- |
| `test_ruff_pin_hook_rev_and_required_version_agree` | dev-group specifier matches `==X.Y.Z` exactly (a floor fails), `[tool.ruff]["required-version"] == "==" + X.Y.Z`, and the `astral-sh/ruff-pre-commit` entry's `rev == "v" + X.Y.Z` |
| `test_workflows_do_not_declare_a_ruff_version` | zero ruff version literals in `.github/workflows/*.yml` (the version travels in the lock, one declaration site, not two) |
| `test_contributing_names_the_declared_ruff_version` | the extracted `X.Y.Z` appears in `CONTRIBUTING.md`'s Code style section — no literal in the test, so the doc cannot go stale silently |

**Deliberately not asserted in pytest** (dependency class the repo keeps out of the suite):

- That `required-version` *fails* a mismatched binary (subprocess + binary): verify-phase runtime
  evidence, mirroring `ci` CI-01 S2's "gate is config-driven" exit-code row and CI-07's runtime rows.
- That `uv.lock` resolves the same version: the exact dev pin makes the resolver follow it, so a
  lockfile parser would add a new coupling (no test parses `uv.lock` today) without adding
  protection; `uv lock` / `uv lock --check` exit codes and `git diff uv.lock` are verify-phase
  evidence instead.
- That the hook is installed: `.git/hooks/pre-commit` is per-clone and untracked, so no repository
  test can observe it.

### Mandatory spec delta 1 — PB-10 corrected (`process-boundary`)

`openspec/specs/process-boundary/spec.md:258` currently ends its second paragraph with a sentence
that this change falsifies. The delta is `## MODIFIED Requirements` for
**`### Requirement: Formatter integrity on a clean checkout (PB-10)`**, and it touches **one
sentence only** — PB-10's other clauses, its five scenarios, its `:254` framing blockquote, and
every other requirement in the file stay byte-for-byte.

**Removed (verbatim):** *"The ruff version pin mismatch (pre-commit `v0.16.7` versus the environment's
`0.16.0`) SHALL stay unaddressed here and SHALL be owned by issue #195."*

**Restated (normative, no version literal — a spec that names `0.16.7` is a second place to forget):**

> The ruff version SHALL have a single declared authority — the environment's dev dependency pin,
> `[tool.ruff] required-version`, and the pre-commit `rev` SHALL name the same version, asserted
> statically by the guard required by `ci` CI-08. Alignment SHALL remain a declaration-and-local-hook
> matter: it SHALL arm no CI step, and issue #194 SHALL retain ownership of the un-staged-file gap.

The delta carries the standard note: *(Previously: the paragraph deferred the pin mismatch —
`v0.16.7` hook versus `0.16.0` environment — to issue #195; change
`2026-09-15-chore-ruff-single-authority` owns it, and no version literal remains in this spec.)*

Two boundaries this restatement is written to preserve: PB-10's "no new CI step" clause and the #194
ownership sentence (**both kept verbatim**), and the `:281-286` scenario asserting zero
`format --check` invocations under `.github/workflows/**` (**this change arms none**).

### Mandatory-adjacent spec decision — does the guard warrant a `ci` clause?

The handoff asks for an evidence-based recommendation between a `ci` clause and leaving the guard a
plain test. **Recommendation: a `ci` clause — new requirement CI-08 — with the three scenarios above
mapped 1:1 to the three guard tests (AGENTS.md rule 6), and a Test Mapping row each.**

| Evidence | Why it points at `ci` |
| --- | --- |
| `ci/spec.md:215-251` (CI-07) | The direct precedent: a **cross-file declaration-equality** contract (`.python-version` equals both gate-job pins) hosted in `ci`. A three-declaration ruff version authority is the same shape |
| `ci/spec.md:285-296` | `ci` is the only capability that indexes static assertions against `tests/test_ci_workflows.py` — the exact file the guard lands in. `grep "## Test Mapping"` over `openspec/specs/` finds only `coverage/spec.md:283` and `ci/spec.md:285`; `process-boundary` has none |
| `ci.yml:19`, `release.yml:29`, `uv.lock:2033` | The authority decides **what CI lints with**: the lint job resolves ruff from the lock, which follows the pinned specifier. The claim is CI-facing, not tree-internal |
| `ci/spec.md:5-11` | Adding CI-07 left the `ci` Purpose paragraph unchanged (it still lists CI-01..CI-06 only), so this delta likewise needs no Purpose edit — the precedent keeps the delta minimal |

**Reconciling the counter-precedent honestly.** #177 placed the formatter contract in
`process-boundary` and rejected `ci` because "this change deliberately adds no CI step, so a `ci`
requirement naming a workflow step would be false"
(`openspec/changes/archive/2026-09-14-chore-ruff-format-drift/specs/process-boundary/spec.md`). CI-08
names **no workflow step** and adds no workflow file; it asserts the *inverse* (zero workflow version
literals) and is verified by the file `ci` already owns. The rejection does not transfer — but the
residual argument (the ruff authority is arguably the same *formatter-integrity* class as PB-10, and
`process-boundary` could host it as PB-14 instead) is real, so the design phase inherits it as a named
alternative with this recommendation recorded, not as a silent choice.

**What CI-08 does not do:** it arms no CI step, re-declares no coverage floor, and adds no scenario
for PB-10's already-spec'd no-`format --check` clause (that scenario stays verify-phase static
evidence as PB-10 wrote it) — so no scenario exists without a 1:1 test, and no existing scenario's
evidence class changes.

## Acceptance-criteria traceability (issue #195, verbatim — supplied by the parent from `gh issue view 195`)

| AC | Verbatim criterion | How this change satisfies it | Evidence class |
| --- | --- | --- | --- |
| 1 | "One ruff version is declared authoritative and named in `CONTRIBUTING.md` (which today does not mention a version at all)." | Authority: the three declarations name `0.16.7` with `required-version` as the enforcing one. Name: `CONTRIBUTING.md:77` gains the version | **Test** — `test_ruff_pin_hook_rev_and_required_version_agree` + `test_contributing_names_the_declared_ruff_version` |
| 2 | "`.pre-commit-config.yaml`'s `rev` and `pyproject.toml`'s dev dependency agree on that version." | Equal by construction and guarded; the `.pre-commit-config.yaml` side needs **no edit** (already `v0.16.7`) | **Test** — the same guard test's core assertion (both other declarations equal the dev pin) |
| 3 | "`uv run ruff format --check src/ tests/` and the `ruff-format` hook produce the same verdict on the same file." | D3's direct path: `pre-commit install` in this clone, then a deliberately misformatted throwaway file run through both surfaces, both verdicts pasted | **Verify-phase runtime evidence**, not pytest: two separately installed binaries + a per-clone, untracked hook. **Scope note:** the parity pair is recorded at AC3's `src/ tests/`; the `scripts/` scope appears in the CI/env commands (`ci.yml:19`) and is not in conflict — the table says which scope each row covers so verify does not re-litigate it |
| 4 | "`uv run pytest tests/ -q` stays green; `ruff check` and `mypy src/` stay clean." | Run the **enforced** commands, not the narrower documented ones: `uv run ruff check src/ tests/ scripts/` (`ci.yml:19`, `release.yml:29`), `uv run mypy src/ scripts/` (`ci.yml:21`, `release.yml:32`, `.pre-commit-config.yaml:13`), plus the suite. Note the tally delta: +3 guard tests collected and passing, zero skipped, zero failures — nothing reduced | **Verify-phase runtime evidence**; AC4's narrower wording is the documented-vs-CI drift owned by **#212** and is **not edited here** |
| 5 | "If the pin moves, `uv.lock` is refreshed in the same change." | The pin does move (0.16.0 → 0.16.7), so the refresh is mandatory in the same change — `packaging` PKG-06's regeneration rule (`packaging/spec.md:132-134`) | **Verify-phase runtime evidence** — `git diff uv.lock` confined to the ruff block + dev specifier, `uv lock --check` exit 0 |

Two ACs (1 and 2) become durable test assertions; three (3, 4, 5) are command evidence in the verify
report — the split the handoff mandates for criterion 3 and the repo already uses for
gate exit codes.

## Changed-lines estimate and review workload

**Functional change (code / config / docs / tests):**

| File | Change | Changed lines (add+del) |
| --- | --- | --- |
| `pyproject.toml` | 1 pin replaced + 1 setting added (+1 comment) | ≈4 |
| `uv.lock` | ruff block: version, sdist, 16 wheel URLs/hashes; dev specifier | ≈40 (36–46) |
| `.pre-commit-config.yaml` | **nothing** | 0 |
| `CONTRIBUTING.md:77` | sentence gains the version | 2 |
| `tests/test_ci_workflows.py` | 3 tests (~55–70 added) + module-docstring count `15 → 18` mapped rows | ≈60 (50–75) |
| **Functional subtotal** | | **≈105 (90–130)** |

**Spec deltas in the change root** (canonical specs receive them at archive, per this repo's
OpenSpec flow): `process-boundary` MODIFIED PB-10 ≈10 lines · `ci` ADDED CI-08 with four scenarios
and four Test Mapping rows ≈40 lines → **≈50**.

**SDD phase artifacts** (proposal → archive-report under
`openspec/changes/2026-09-15-chore-ruff-single-authority/`): ≈600 lines of prospective documentation
text. This proposal does not count them as product size, following this repo's own precedent (#177
recorded "Size: 6 test files, ~41 changed lines" and listed its artifacts separately).

**Review-workload note.** The functional + spec change (≈155 lines) fits a single PR inside the
400-line budget. If the parent counts the raw diff *including* artifacts (≈750 lines), the change
exceeds 400 and the first chained PR SHALL be the functional core — `pyproject.toml` + `uv.lock` +
the three guard tests + `CONTRIBUTING.md` (≈105 lines, and the slice where AC1/AC2/AC5 are verifiable
in isolation) — with the spec deltas as slice 2 and the phase artifacts as slice 3. The guard tests
stay in the slice that carries the scenario text they satisfy (rule 6), never split across slices.

## Risks

| Risk | Likelihood | Impact | Evidence / mitigation |
| --- | --- | --- | --- |
| **`required-version` raises the bar for every contributor** — any editor integration, global install or `uvx ruff` at another version now fails at config load | Certain by design (D2, maintainer-accepted) | A contributor's `ruff check` errors until they `uv sync` | Measured failure text names both versions (`Required version '==…' does not match the running version '…'`), and `CONTRIBUTING.md:77` now names the expected version (AC1). Accepted cost, deliberate: a loud failure replaces a silent disagreement |
| **The `v0.16.7` tag has never resolved on this machine**, so the hook may be un-installable | Unknown (no network this phase) | Every hooked commit fails for everyone with hooks installed | AC3's evidence path **is** the materialisation probe (`pre-commit install` + run); it must run before the change is called complete, and it retires this risk in one step. If the tag is absent, that is a finding to escalate — not a silent workaround |
| **Dev-environment / CI-matrix interaction** — 3.10–3.14 × {ubuntu, windows} test legs, one lint job on 3.13 (`ci.yml:15,27,28`), one coverage job on 3.13 (`ci.yml:61`) | Low | A leg/version-dependent formatter verdict could surface only in CI | Ruff is invoked by exactly one shape — `uv run ruff …` after `uv sync` (`ci.yml:19`, `release.yml:29`) — so **every leg installs the same wheel from the refreshed lock**; the version was already single-valued on the CI side (0.16.0 via the lock). What becomes single-valued is the *agreement* between CI/env and the hook, which no leg previously observed. The test matrix never invokes ruff |
| **`uv.lock` refresh is network-bound and could move unrelated packages** — a resolver refresh can shift more than the ruff block | Low–Med | Unrelated lock churn inflates the diff, obscures the change, and could move another dependency silently | Inspect `git diff --stat uv.lock`; the expectation is the ruff block + the dev specifier only. A package-scoped refresh (uv's `--upgrade-package ruff`) is the intended way to confine it — **the exact flag is unverified in this phase** and SHALL be confirmed by the apply phase, which pastes the resulting diff. Unrelated churn is a scope finding to surface, never to absorb |
| **A formatter change appears anyway** (0.16.7 reformats a file) | Low — both versions returned `68 files already formatted` | Would reach into `src/sofer/`, i.e. the four rule-14 modules | The measurement is the mitigation; if a reformat still appears, it is a separate, explicitly-accepted task with its own evidence — never a quiet ride-along |
| **PB-10 is over-edited** — a "restatement" that rewrites its clauses or scenarios | Medium (the doc is one long paragraph) | Weakens a shipped requirement; breaks its five scenarios' framing and the sibling-gate clause | Delta is one sentence; the restatement is quoted above; the `:281-286` no-gate scenario and the #194 ownership sentence stay verbatim; verify re-reads the paragraph against the pre-change text |
| **The edit to `CONTRIBUTING.md:77` collides with #187** (same sentence) | Medium | Rebase conflict, or concerns silently merged | Interaction named in both directions: this change adds the version only; the nonexistent `ruff.toml` path stays #187's. The guard asserts the version's presence, nothing about the path |
| **The `ci` clause duplicates or arms a CI gate by accident** | Low | Violates PB-10 `:286` and steps on #194 | CI-08 adds no workflow file and no `format --check`; its workflow assertion is the inverse (zero version literals); the PB-10 no-gate scenario stays untouched and passing |
| **The new guard tests drift the documented test tally** (`AGENTS.md` rule 6, the module docstring's "15 mapped rows") | Certain | Stale counts in two places (a class this repo already tracks) | Update the module docstring in the same change; the tally is re-derived at apply and verify with `uv run pytest tests/ -q`, never copied from `AGENTS.md` |

## Rollback

Trivial and complete: revert the single commit. The change adds no runtime behaviour, no data or
format migration, no dependency other than a version bump of an already-present dev tool, and nothing
published. The only artefact outside git is the local `.git/hooks/pre-commit` written by AC3's
evidence path — untracked, per-clone, removable with `pre-commit uninstall` (it does not exist today,
so removing it restores the prior state exactly). Spec deltas revert with the same commit; canonical
specs merge at archive, so a pre-archive revert leaves the canonical specs untouched.

## Success criteria

1. `pyproject.toml` declares `ruff==0.16.7` **exactly** (no floor), `[tool.ruff] required-version`
   is `==0.16.7`, and `.pre-commit-config.yaml:3` stays `v0.16.7` — with the guard test red if any of
   the three moves alone.
2. A deliberately mismatched `required-version` value fails **both** `ruff check` and `ruff format`,
   and the real value passes both (pastable command block in the verify report).
3. AC3 parity: `uv run ruff format --check src/ tests/` and the `ruff-format` hook give the same
   verdict on the same deliberately misformatted file, with both outputs pasted and the exact
   hook-materialisation command named.
4. `uv run ruff format --check src/ tests/ scripts/` still reports zero reformats; **zero**
   `format --check` invocations exist under `.github/workflows/**` before and after; no workflow file
   appears in the diff.
5. `uv run pytest tests/ -q` green (baseline +3 guard tests, 0 failures, 0 newly skipped);
   `uv run ruff check src/ tests/ scripts/` and `uv run mypy src/ scripts/` clean — the enforced
   commands, with AC4's narrower wording recorded as #212.
6. `uv.lock` refreshed in the same change; `git diff --stat uv.lock` confined to the ruff block and
   the dev specifier; `uv lock --check` exit 0.
7. PB-10's deferral sentence is gone, its other clauses and all five scenarios are unchanged, and no
   spec file names a ruff version literal (the count of version-naming clauses goes 1 → 0).
8. No rule-14 module (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) appears in the diff; no
   `src/sofer/**` path appears at all.

## Rule 6 (scenario ↔ test) resolution

Four new scenarios, four mappings, no vacuous test invented: **S1/S2/S3** of CI-08 map 1:1 to the
three guard tests in `tests/test_ci_workflows.py`; **S4** (a mismatched binary fails loudly) maps to
verify-phase runtime command evidence, the same framing this repository uses for measured gate exit
codes (`ci` CI-01 S2, CI-07's runtime rows, PB-10's own `:254` blockquote) — asserting it from pytest
would mean spawning a second ruff binary from the suite, a dependency class AGENTS.md rule 9 keeps
out. PB-10's restored clauses and its five scenarios keep their existing evidence classes; nothing is
re-mapped, weakened, or re-declared.

## Proposal question round

All four product decisions are answered by the handoff, so this round does **not** re-open them. These
are the design-level assumptions I proceeded on; correct any of them and I revise — a second round is
available on request, and the maintainer may redirect the framing rather than answer item by item.

1. **PB-10's restatement** removes the version literal from the spec entirely (the invariant lives in
   the requirement body; the value lives in two declarations + the guard). The alternative — naming
   `0.16.7` in the corrected sentence — was rejected because a spec literal is a third place to
   forget, but it is a legitimate reading of "keep the edit minimal".
2. **CI-08 lives in `ci`** (recommendation, justified above) rather than as a new `process-boundary`
   PB-14 beside PB-10; if the maintainer prefers one capability per change, PB-14 is the named
   fallback and the three guard tests are unchanged either way.
3. **The guard tests extend `tests/test_ci_workflows.py`** (reusing its `_read_text` / `_load_toml` /
   `_load_yaml` helpers) rather than forming a new module — AGENTS.md rule 4 (no duplicated logic) and
   one home for static repository-shape contracts.
4. **AC1's `CONTRIBUTING.md` half is test-asserted dynamically** (the extracted version must appear),
   not left to verify-phase prose nor asserted as a literal — so a future bump cannot leave the doc
   silently stale.
5. **Lock-refresh confinement** (plain `uv lock` versus a package-scoped refresh) is delegated to the
   apply phase as a probe, with unrelated lock churn treated as a scope finding rather than absorbed.

## Open items passed forward (not decisions)

- **Hook materialisation + upstream tag existence** (unverified #1) — discharged by AC3's evidence.
- **`uv.lock` delta shape** (unverified #2) and **`required-version` under 0.16.7** (unverified #3) —
  settled by apply/verify command output.
- **Slice boundaries** if the review budget counts SDD artifacts — the parent decides chaining with
  the estimate above; the guard-test/scenario pairing must not be split.
