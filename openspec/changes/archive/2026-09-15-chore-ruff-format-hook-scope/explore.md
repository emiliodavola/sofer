# Exploration: chore-ruff-format-hook-scope

**Change**: `2026-09-15-chore-ruff-format-hook-scope` · **Issue**: #216 — *chore: the ruff-format
pre-commit hook rewrites README.md and README_ES.md (its types_or includes markdown)* · **Branch**:
`chore/216-ruff-format-hook-scope` (from `dev`, clean tree) · **Phase**: explore (notes only — no
implementation) · **Store**: hybrid (this file + Engram `sdd/2026-09-15-chore-ruff-format-hook-scope/explore`)
**Confirmed product decision (user, option (a))**: narrow the `ruff-format` hook with an explicit
`types_or` in `.pre-commit-config.yaml` so the hook no longer sees Markdown; document the decision; stay
consistent with `[tool.ruff] extend-exclude = ["openspec"]`.

This phase had **no shell access**. Everything below is either read from the working tree, or transcribed
from parent-supplied and repository-recorded measurements (labelled *measured* / *recorded* / *inferred*).
Nothing is asserted from upstream documentation — those reads are listed in §8 as research-lane work.

---

## 1. The defect, mechanically

`.pre-commit-config.yaml` declares `ruff-format` with **no** override of the upstream manifest's file-type
selector:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.7
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format          # .pre-commit-config.yaml:7 — no types_or override
```

The cached upstream manifest for that rev is readable on this machine and is exactly as the issue body
quotes (`C:/Users/elaze/.cache/pre-commit/repon1p3j7_t/.pre-commit-hooks.yaml`, read this phase):

```yaml
- id: ruff-format
  name: ruff format
  entry: ruff format --force-exclude
  language: python
  types_or: [python, pyi, jupyter, markdown]   # <-- markdown is in the hook's file set
```

So the hook's input set is `*.py` + `*.pyi` + `*.ipynb` + `*.md`. When the hook runs, ruff rewrites the
fenced Python in the two READMEs (`README.md:161`, `README.md:560`, `README_ES.md:169`, `README_ES.md:595`
— 2 blocks each, verified by grep this phase). The blocks are MCP pseudo-code with **aligned inline
comments** (e.g. `sofer_scan_dry_run(config="test.toml")   # preview — no writes`), which is exactly the
construct the formatter normalises.

**Recorded whole-tree measurement (#195 apply phase, `apply-progress.md:485-500`)** — the tripwire that
produced this issue:

```console
$ uv run pre-commit run ruff-format --all-files
ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook
2 files reformatted, 9 files left unchanged
68 files left unchanged
```

`git diff --stat` showed `README.md | 10 +++----` and `README_ES.md` only; both were reverted with
`git checkout -- README.md README_ES.md`.

**The batch arithmetic closes, and it is worth recording because it *is* the fix's acceptance evidence**
(inferred this phase from the tracked-file inventory + the recorded output):

- 68 python files = the tracked `src/sofer/` (32) + `tests/` (35) + `scripts/` (1) — matches
  `uv run ruff format --check src/ tests/ scripts/` → "68 files already formatted" (#195 G4).
- 11 markdown files reach ruff's hands = every tracked `*.md` outside `openspec/`: `AGENTS.md`,
  `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `README.md`, `README_ES.md`, `SECURITY.md`,
  `docs/configuration.md`, `.github/PULL_REQUEST_TEMPLATE.md`, and the three `.github/ISSUE_TEMPLATE/*.md`.
  `2 reformatted + 9 unchanged = 11` — exactly the recorded line.
- `openspec/**/*.md` is passed to the hook too, but ruff's `--force-exclude` honours
  `[tool.ruff] extend-exclude = ["openspec"]` (`pyproject.toml:63-66`), so those files are not counted and
  not rewritten. This is the **existing precedent for the decision**: the repository already keeps
  documentation out of formatter scope, one configuration surface at a time.

**Cause is upstream-manifest content, not this repository's rev choice — and the upstream list is not
stable.** Reading the cached `ruff-pre-commit` manifests on this machine (each cache dir's
`pyproject.toml` pins the ruff it installs):

| Cached rev | ruff | `ruff-format` `types_or` |
| --- | --- | --- |
| `repoym_k5mue` | 0.8.0 | `[python, pyi, jupyter]` |
| `repo3ptoyxgr` | 0.15.21 | `[python, pyi, jupyter]` |
| `repoqghug3i1` | 0.16.0 | `[python, pyi, jupyter]` |
| `repo27dpqiot` | 0.16.6 | `[python, pyi, jupyter, markdown]` |
| `repon1p3j7_t` | 0.16.7 | `[python, pyi, jupyter, markdown]` |

So `markdown` entered the upstream hook between 0.15.21 and 0.16.6, and the `ruff` (lint) hook — the legacy
alias this config uses — declares `[python, pyi, jupyter]` under **every** rev, which is why only the
formatter was ever the problem. Consequences for the write-up:

1. The **verdict on the README bytes** is version-independent (#195 recorded 0.16.0 and 0.16.7 agreeing on
   that), but the **hook's file set is not** — the exposure arrived with a manifest edit this repository
   never declared.
2. This is the strongest argument for option (a) over "document it": an explicit repo-side `types_or`
   makes the hook's scope a **repository declaration** that a future rev bump (or another upstream manifest
   edit) cannot silently widen. Dependabot does **not** watch the `pre-commit` ecosystem
   (`.github/dependabot.yml` has only `uv` and `github-actions`), so the rev moves by hand — and CI-08's
   guards already force a hand-bump to keep three declarations in sync
   (`tests/test_ci_workflows.py:463-473`).

---

## 2. Verified state of the touched surfaces

| Surface | Current content | Evidence |
| --- | --- | --- |
| `.pre-commit-config.yaml` | 15 lines, two repos: `astral-sh/ruff-pre-commit` @ `v0.16.7` (hooks `ruff` with `args: [--fix]`, `ruff-format`) and a `local` `mypy` hook (`types: [python]`, `pass_filenames: false`). **Zero comments** in the file | read this phase; ids/revs at `:2,:3,:5,:7,:9,:11` |
| `pyproject.toml [tool.ruff]` | `required-version = "==0.16.7"` (`:62`), `extend-exclude = ["openspec"]` (`:66`) with a 4-line comment stating the rationale ("Design docs and specs under openspec/ embed Python snippets inside markdown; … keep them out of scope") | read this phase |
| `[tool.ruff.format]` | `quote-style = "double"`, `indent-style = "space"` (`:71-73`) — **no** `exclude` / no per-file overrides | read this phase |
| `AGENTS.md` rule 5 ("Pre-commit hooks run automatically") | `:36-39`, three bullets: "`ruff` (lint + fix + format) and `mypy` run on every commit", "Never commit with `--no-verify`", "`uv run mypy src/`". **No statement of the hook's file scope** | read this phase |
| `AGENTS.md` rules 1 / 7 / 13 | rule 1 (no hardcoded values) → a `types_or` list is a tool-scope declaration, the same class as `.python-version` / `required-version` (CI-07/CI-08 precedent), not a runtime default; rule 7 (CLI help + README) → **not triggered**, no CLI surface moves; rule 13 (README/README_ES mirroring) → **not triggered**, and critically the change **must not touch** either README | read this phase |
| `CONTRIBUTING.md` | `:16` `pre-commit install`; `:29` `uv run ruff check src/ tests/`; `:77` — "This project uses **ruff** 0.16.7 for linting and formatting. Configuration is in `ruff.toml` at the repo root. Run `ruff check` and `ruff format` before committing — the pre-commit hook does this automatically." **No statement of hook scope**; the `ruff.toml` path it names does not exist (`find` → no `ruff.toml`; config lives in `pyproject.toml`) | read this phase |
| `.github/workflows/ci.yml` | lint job runs only `uv run ruff check src/ tests/ scripts/` (`:19`) and `uv run mypy src/ scripts/` (`:21`). **No `ruff format --check`, no `pre-commit` invocation anywhere under `.github/`** (grep this phase: only hit is the PR template) | read this phase |
| `.github/PULL_REQUEST_TEMPLATE.md` | `:44` checklist item `uv run ruff format --check src/ tests/` — a **direct** ruff run, unaffected by hook scope; also narrower than the CI scope (`scripts/` missing → #212's class) | read this phase |
| `openspec/specs/ci/spec.md` | CI-08 (`:290-360`) owns the ruff **version** authority and states "enforcement of the staged-file formatter SHALL remain the local pre-commit `ruff-format` hook" (`:312-314`). **It says nothing about which file types that hook sees.** Test Mapping table at `:285+`; `## Purpose` (`:5-11`) still enumerates CI-01..CI-06 (stale for CI-07/CI-08 too — a pre-existing condition) | read this phase |
| `openspec/specs/process-boundary/spec.md` | PB-10 "Formatter integrity on a clean checkout" (`:252-289`) — the formatter contract; its *No CI gate was armed* scenario (`:281-288`) states "enforcement SHALL remain the local pre-commit `ruff-format` hook on staged files, with recurrence owned by issue #194". **No file-type clause.** `process-boundary` has no `## Test Mapping` table (only `ci:285` and `coverage:283` have one) | read this phase |
| `openspec/project.md` | `:70` "Pre-commit hook order: ruff fix -> ruff format -> mypy"; `:82` stale CI/ruff/mypy versions (`ruff 0.16.0`) — owned by other issues, not this one | read this phase |
| `openspec/changes/` | contains **only** `archive/` — this change root does not exist yet; no other active change carries a conflicting delta | find this phase |
| `.gitignore` | `.pi/`, `.agents/` are ignored, and no Python outside `src/ tests/ scripts/` is tracked (`find "**/*.py"` → 68 files, all three trees) | read this phase |

---

## 3. Blast radius of the proposed edit

The edit is one key on one hook entry: `types_or: [python, pyi, jupyter]` under `.pre-commit-config.yaml:7`.

**Nothing that exists today asserts the opposite.**

| Referencing surface | Effect | Evidence |
| --- | --- | --- |
| `tests/test_ci_workflows.py` (the only test that reads the file) | `test_ruff_pin_hook_rev_and_required_version_agree` (`:463-473`) loads the YAML, filters `config["repos"]` by `repo == _RUFF_PRE_COMMIT_REPO`, and asserts the **`rev` list** equals `[f"v{version}"]`. It never enumerates hook keys and never asserts a hook shape. A hook-level `types_or` is invisible to it | read this phase |
| Other tests | grep for `pre-commit-config` / `pre_commit_config` / `ruff-format` across `tests/` → **one** hit (the above). No test enumerates hook ids or asserts the config's exact shape | grep this phase |
| CI / release workflows | no `pre-commit` invocation and no `ruff format` step anywhere under `.github/` → **zero CI behaviour change**; CI keeps linting via `uv run ruff check src/ tests/ scripts/` after `uv sync` | grep + read this phase |
| Docs | `CONTRIBUTING.md:77`, `AGENTS.md:36-39`, `openspec/project.md:70` are the only hook-scope-adjacent prose; none of them asserts the file set, so none becomes *false* — but none records the new scope either (see §4) | read this phase |
| Specs | CI-08 and PB-10 both name the hook as the enforcement surface but are silent on file types — **no clause is falsified**; the decision is unowned today | read this phase |
| Files still formatted afterwards | exactly the 68 tracked Python files under `src/ tests/ scripts/` (no `.pyi`, no `.ipynb` anywhere in the tree → `pyi`/`jupyter` are inert today and retained for upstream parity and future notebooks) | find this phase |
| Files that leave the hook's scope | the 11 tracked markdown files outside `openspec/`; **2** of them (the READMEs) were being rewritten. `openspec/**/*.md` was never actually formatted (ruff `--force-exclude` + `extend-exclude`), so nothing enforced is lost | §1 arithmetic, inferred from recorded output |
| Enforced gate coverage | PB-10's gate is `uv run ruff format --check src/ tests/` (and CI-08's evidence uses `src/ tests/ scripts/`) — neither includes Markdown, so **no enforced scope shrinks** | `process-boundary/spec.md:256`, `ci/spec.md:353` |

**What stays true after the change and must be stated in the PR body (issue AC):** `types_or` is a
**pre-commit** filter, not a ruff setting. A *direct* `uv run ruff format README.md` — or a future
`ruff format --check .` armed by **#194** — still sees and rewrites Markdown. This change decides **what the
hook considers formattable**; #194 decides **whether a `--check` gate is armed in CI and over which paths**.
The two are independent, and the independence is the reason #194's decision does not have to wait on this
one (it only inherits the fact that a naive `.`-scoped gate would flag the READMEs — which is *also* why
PB-10's and CI-08's evidence commands are path-scoped rather than `.`-scoped).

---

## 4. Where should the DECISION be recorded durably? (candidates + evidence — **not decided here**)

The user's intent is explicit: "document the decision; the next contributor must not re-litigate it." Six
candidate homes exist. Evidence for and against each, without a recommendation:

**C1 — new requirement in `openspec/specs/ci/spec.md` (CI-09).**
*For*: `ci` is the only capability with a `## Test Mapping` table indexing `tests/test_ci_workflows.py`
(`ci:285`), the exact file a static guard would live in; CI-08 was placed there on exactly that argument
(`openspec/changes/archive/2026-09-15-chore-ruff-single-authority/specs/ci/spec.md`, §*Capability
placement*), and CI-08 already owns a clause about this very hook. *Against*: `ci`'s `## Purpose` is
continuous-integration presence; pre-commit is never invoked in CI, so this claim has **no CI-facing
consequence** — CI-08 at least decided what CI lints with (the version via `uv.lock`). Adding CI-09 deepens
the already-stale `## Purpose` enumeration (`:5-11`, stale for CI-07 and CI-08) that #195 deliberately left
alone.

**C2 — new requirement in `openspec/specs/process-boundary/spec.md` (PB-13/PB-14).**
*For*: PB-10 is literally the formatter-integrity contract, names the local `ruff-format` hook as the
enforcement surface, and its scenario text already reasons about *which files the hook sees* ("staged files
only", `:281-288`); #177 deliberately chose `process-boundary` for formatter integrity and rejected `ci`
for a change that "adds no CI step" — a framing that transfers to this change more cleanly than to CI-08.
*Against*: `process-boundary` has **no `## Test Mapping` table**, so a pytest-mapped scenario would either
need the table created or the scenario mapped as verify-phase static evidence (§5).

**C3 — `CONTRIBUTING.md` Code style section (`:77`).**
*For*: it is the contributor-facing statement of exactly this ("Run `ruff check` and `ruff format` before
committing — the pre-commit hook does this automatically"); CI-08 established the precedent that this
section is **test-asserted** (`test_contributing_names_the_declared_ruff_version`, `:520-531`), so a
sentence here can be guarded. *Against*: prose alone does not stop a future hand edit to the YAML, and the
same sentence already carries a false statement (`ruff.toml`, owned by **#187**) — editing this line means
an ordering decision against #187 (which #195 already recorded as "resolve by ordering, never by merging
concerns").

**C4 — inline comment in `.pre-commit-config.yaml` at the hook entry.**
*For*: the rationale sits on the exact line a future editor touches; it is the same convention the
repository already uses in `pyproject.toml:63-66` for the sibling scope decision
(`extend-exclude = ["openspec"]`), so option (a) and the existing documentation become symmetrical.
*Against*: the file currently has **zero** comments (no precedent in it); comments are not asserted by any
test, so they can be deleted by a reformat/merge without a red suite.

**C5 — `AGENTS.md` rule 5.**
*For*: rule 5 is the agent-facing statement of hook behaviour; a sub-bullet ("`ruff-format` is scoped to
`python`/`pyi`/`jupyter`; Markdown is out of the formatter's scope — see `.pre-commit-config.yaml`") is
cheap and is read by every agent session. *Against*: no test asserts rule 5's content, and the rule-14
precedent (`test_agents_md_declares_core_100_mandate`) shows AGENTS.md text *can* be guarded, which would
add a second guard for one key.

**C6 — static guard test only, no spec clause.**
*For*: the claim is defensible as repository shape rather than product behaviour; `tests/test_ci_workflows.py`
is the established home for "static repository-shape contracts", and rule 6 binds only if a spec scenario
exists — no spec clause, no rule-6 obligation. *Against*: "the decision must not be re-litigated" argues for
a normative home; tests document only if someone reads them, and the *why* (upstream manifest breadth, the
consequence for #194) has no natural slot in a test name.

**Cross-cutting constraint for whichever home is chosen** — if a spec scenario is added, rule 6 requires a
corresponding test (AGENTS.md rule 6), and the node that consumes the decision is `#194` (the format-gate
issue), so the PR body must **state the #194 relationship verbatim** (issue AC) **and** point at the
durable home.

---

## 5. Verification design

**A static guard is feasible and cheap; a runtime proof of the hook's file set is not a pytest matter.**

What a guard in `tests/test_ci_workflows.py` can assert with existing helpers (`_load_yaml`, `_read_text`
— no new import, no new file, rule 4):

1. The `astral-sh/ruff-pre-commit` repo entry contains a hook with `id == "ruff-format"`.
2. That hook declares `types_or` explicitly (the key is present — the *contract*, and the part a future rev
   bump cannot silently remove).
3. The declared value does not contain `markdown` (the *defect*, directly), and/or equals
   `["python", "pyi", "jupyter"]` (the *positive scope*).

The fork between #3's two forms is a design decision, not an exploration one: an equality assertion is
precise and mirrors CI-08's style but is a "declaration mirror" edited alongside the config, whereas a
`"markdown" not in types_or` assertion is weaker but cannot go stale. Note CI-08's guards deliberately
**extract** their expected value from an existing declaration rather than hardcoding it; here there is no
upstream declaration to extract from — the config **is** the source — which is the honest asymmetry to
record.

What the suite deliberately should **not** do (matching the repo's established dependency discipline,
AGENTS.md rule 9, and #195's §7 reasoning): spawn `pre-commit` from pytest. `pre-commit` needs a per-clone
`.git/hooks` install and a cached hook environment; #195 recorded that library as a verify-phase concern,
and CI-08 S4 is verify-phase runtime evidence for the same reason.

**Runtime evidence available to the verify phase on this machine** (the hook env is already materialised
at `~/.cache/pre-commit/repon1p3j7_t`, ruff 0.16.7 — recorded by #195, so no network is needed):

```console
# the issue's own AC — the file must no longer be a hook input at all
$ uv run pre-commit run ruff-format --files README.md
# expected after the change: "(no files to check)Skipped", exit 0

# the whole-tree proof — the markdown batch must disappear
$ uv run pre-commit run ruff-format --all-files
# expected after the change: "68 files left unchanged" with NO "files were modified by this hook"
#                           (pre-change: "2 files reformatted, 9 files left unchanged" + "68 …")

# nothing was rewritten
$ git diff --stat -- README.md README_ES.md    # expected: empty
```

**Two wrapper caveats #195 measured and this change's verify must respect** (they are how a false
"the fix does not work" reading happens):

1. The hook's `entry` is `ruff format --force-exclude` — a **fixing** surface. `ruff format` exits 0 after
   writing changes; only `--check` exits 1. So "exit 0" alone never proves the file was untouched.
2. pre-commit detects "files were modified" through `git diff`, which cannot see an **untracked** file.
   `README.md` here is tracked, so on a regression the run *would* report `Failed` + "files were modified"
   and exit 1 — that makes the AC check sound on this file, but a throwaway probe file would not be.

The observation that **does** discriminate cleanly is the hook's own file-list output: pre-change the hook
runs on 11 markdown files and reports them; post-change it must report the markdown batch as absent
(`(no files to check)Skipped` for `--files README.md`; no "2 files reformatted" line for `--all-files`).

---

## 6. Alternatives with a different blast radius (recorded for the design phase; option (a) is the user's choice)

| Alt | Mechanism | Blast radius difference | Evidence |
| --- | --- | --- | --- |
| **(b) reformat both READMEs once** (issue's option b) | Run the formatter deliberately, commit the result | Ends today's diff noise but leaves the hook rewriting them on every future README edit; contradicts rule 13's mirroring discipline in spirit (both files must move together every time); #180/#183/#190 would inherit the churn | issue body; `CONTRIBUTING.md:77`; rule 13 |
| **(c) leave and document** (issue's option c) | Comment only | No mechanical protection; the next contributor re-litigates; upstream can widen again | issue body |
| **(a′) add the READMEs (or `*.md`) to `[tool.ruff] extend-exclude`** | `pyproject.toml:66` `["openspec"]` → `["openspec", "README.md", "README_ES.md"]` | **Broader**: `extend-exclude` applies to *direct* ruff invocations too (with `--force-exclude`) and to `ruff check`, so it would additionally shield the READMEs from a future #194 gate. **Different consistency story**: it extends the *existing* documented mechanism (`pyproject.toml:63-66`) rather than introducing a second one; but it makes the exclusion invisible to `pre-commit run --all-files` readers, and it would also exclude the READMEs from `ruff format` if a future contributor *wants* them formatted | `pyproject.toml:63-66`; the sibling-comment precedent; #194 ownership of any `--check` gate |
| **(a″) `exclude:` / `files:` regex on the hook entry** | `exclude: '\.md$'` on `ruff-format` | Same effect as `types_or` but expressed as a path pattern rather than file types; `types_or` is the field the upstream manifest uses, so the override reads as the direct counterpart — and `types_or` survives a file rename/extension regardless of path | upstream manifest; nothing in this repo uses `exclude:` today |

None of these is decided here. The evidence relevant to the *user's confirmed choice* is only that option
(a) is the narrowest edit that removes markdown from the hook while keeping every other file type upstream
intends (`pyi`, `jupyter`), and that its residual gap — direct `ruff format` on Markdown — is stated rather
than silently inherited.

---

## 7. Scope discipline: what this change must NOT absorb

Named owners, each with its own issue, so the PR body can carry them as explicit non-goals:

| Item | Owner | Why it stays out |
| --- | --- | --- |
| `CONTRIBUTING.md:77`'s nonexistent `ruff.toml` path | **#187** | Same sentence, different defect; #195 already set the precedent "resolve by ordering, never by merging concerns". If the decision is recorded in this sentence (candidate C3), the `ruff.toml` fix must still not ride along |
| `CONTRIBUTING.md:28-29` / PR-template `:44` naming a narrower scope than CI (`src/ tests/` vs `src/ tests/ scripts/`) | **#212** | Documented-vs-CI drift, its own class; the template item is a *direct* ruff run and is not changed by hook scope |
| Arming any `ruff format --check` gate in CI | **#194** | PB-10's *No CI gate was armed* scenario (`:281-288`) asserts **zero** `format --check` invocations under `.github/workflows/**`; this change must leave that scenario passing, and the PR body must state the relationship |
| `openspec/project.md:70,82` (hook order; stale `ruff 0.16.0` / `mypy 2.3.0`) and other version prose | #184 / #187 / #214 documentation wave | Historical/documentation drift, not hook scope; `openspec/config.yaml` is gitignored local state (`.gitignore:57`) |
| `openspec/specs/ci/spec.md` `## Purpose` (`:5-11`, stale for CI-07/CI-08) | left stale by #195 | Its own defect; fixing it here would edit canonical prose for another requirement's class |
| Any edit to `README.md` / `README_ES.md` | — | The change exists to stop touching them; a README diff here would be self-defeating and would trigger rule 13 |
| Any `src/sofer/**` edit | — | Nothing in `src/` reads ruff or pre-commit (verified by #195 and re-read here: the only `src/` ruff reference is the `# ruff: noqa: E501` directive in `mcp_server.py`) |

---

## 8. Research-lane items (external verification still owed — not asserted here)

1. **Does a config-level `types_or` on a remote-repo hook entry *replace* (not merge with) the manifest's
   `types_or`?** This is the load-bearing upstream semantic of option (a). The empirical answer is
   observable locally (§5, `--files README.md` → skipped), but the documented contract should be cited so
   the guard test's *meaning* is anchored: pre-commit docs, "Overriding hooks" — including whether
   `types_or` is on the overridable list for non-`local` repos (the documented caveat class around `entry` /
   `language` is the thing to check).
2. **The exact accepted type tags for this hook** — confirm `python`, `pyi`, `jupyter` are the identifiers
   `identify`/pre-commit recognises (and that there is no separate `markdown`-adjacent tag such as
   `markdown` vs `md`), so the declared list cannot be silently inert.
3. **When the upstream manifest added `markdown`, and whether upstream documents/intends Markdown
   formatting** (changelog or the PR that edited `.pre-commit-hooks.yaml`). This decides whether the
   override is a *divergence* to justify or a *restoration* of the pre-0.16.6 behaviour — currently the
   local cache brackets it to `(0.15.21, 0.16.6]` with no citation.
4. **Whether `--all-files` file counting by pre-commit matches the §1 arithmetic** (11 markdown files
   outside `openspec/`): the arithmetic is an inference from #195's recorded output, and verify will
   re-earn it from live output rather than inherit it.

---

## 9. Risks to carry into design/plan

| Risk | Where the risk lands | Mitigation already available |
| --- | --- | --- |
| A guard test that hardcodes the expected `types_or` list becomes a mirror that a future, deliberate scope change must edit in two places | `tests/test_ci_workflows.py` | Either accept the mirror (CI-08 style is *extract*, not *hardcode* — so state the asymmetry) or assert the narrower `"markdown" not in types_or` contract |
| The word "formatter scope" may be read as global, so a future contributor believes direct `ruff format` is also narrowed | docs / PR body | State the pre-commit-only nature explicitly in the chosen durable home (§3), and point at #194 |
| Markdown code blocks stop being formatter-checked at all (deliberate trade-off) | README/docs python snippets | They are illustrative pseudo-code (`sofer_init(...)` call chains), not executable sources; PB-10/CI-08 evidence is already path-scoped to `src/ tests/ scripts/`, so no enforced coverage is lost |
| Adding a `ci` requirement would deepen the stale `## Purpose` enumeration | `openspec/specs/ci/spec.md:5-11` | If C1 is chosen, note the pre-existing staleness in the PR body and leave `## Purpose` untouched (the CI-07/CI-08 precedent) |
| Editing `CONTRIBUTING.md:77` collides with **#187** (same sentence) | `CONTRIBUTING.md` | Order the two changes, or record the decision in a home that does not touch that sentence (C1/C2/C4) |
| Verify could misread a `--force-exclude`/fixing-hook exit 0 as proof of no rewrite | verify phase | The discriminating observation is the hook's file-list output, not the exit code (§5 caveats) |

## 10. Open questions for the design phase (not decisions taken here)

1. **Which home carries the decision** — C1 (`ci` CI-09) vs C2 (`process-boundary` PB-13) vs prose-only
   (C3/C4/C5) vs test-only (C6)? The exploration lists evidence for all six and picks none.
2. **Guard shape** — explicit `types_or` key present, `"markdown" not in …`, or full equality?
3. **Whether the change earns a spec delta at all**, given the repository's own rule-6 coupling (a spec
   scenario obliges a test) and #194's ownership of the adjacent gate decision.
4. **Whether the near-miss mechanism gets a sentence in the same change** (upstream manifests are not a
   stable contract; the override is what makes the scope repo-owned) — that framing is the durable answer
   to "why not just document it".

---

## Read in this phase (provenance)

`AGENTS.md` (rules 1, 5, 6, 7, 13, 14) · `.pre-commit-config.yaml` · `pyproject.toml` ·
`.github/workflows/ci.yml` · `.github/PULL_REQUEST_TEMPLATE.md` · `.github/dependabot.yml` ·
`.gitignore` · `tests/test_ci_workflows.py` · `CONTRIBUTING.md` · `README.md:155-180,555-575` ·
`openspec/specs/ci/spec.md` · `openspec/specs/process-boundary/spec.md:245-325` ·
`openspec/project.md` · `openspec/config.yaml` ·
`openspec/changes/archive/2026-09-15-chore-ruff-single-authority/{proposal.md,apply-progress.md,archive-report.md,verify-report.md,specs/ci/spec.md}` ·
cached `ruff-pre-commit` manifests at revs 0.8.0 / 0.15.21 / 0.16.0 / 0.16.6 / 0.16.7 under
`~/.cache/pre-commit/`.
