# Exploration — `2026-09-15-chore-ruff-single-authority`

Change: `2026-09-15-chore-ruff-single-authority` (GitHub issue **#195**)
Phase: **explore** (evidence only — no implementation, no source/workflow/lockfile/spec edits)
Date: 2026-09-15

---

## 1. Context

| Field | Value |
| --- | --- |
| Repository | `C:/Users/elaze/Desktop/sofer` (Windows; Git Bash available) |
| Branch | `chore/195-ruff-single-authority`, created from `dev@5a2ae38` (`.git/logs/HEAD:826`) |
| Change root | `openspec/changes/2026-09-15-chore-ruff-single-authority/` (created by this phase) |
| Issue | #195 — *chore: two authoritative ruff versions in play (pre-commit v0.16.7 vs ambient 0.16.0)* |
| Artifact store | hybrid (this file + Engram topic key `sdd/2026-09-15-chore-ruff-single-authority/exploration`) |
| Session preflight | execution `auto`, delivery `auto-chain`, review budget 1500 changed lines |

**Skills loaded before work** (paths injected by the parent, resolution = `paths-injected`):
`C:\Users\elaze\.pi\agent\skills\python-code-style\SKILL.md`,
`C:\Users\elaze\.agents\skills\uv\SKILL.md`,
`C:\Users\elaze\.pi\agent\npm\node_modules\gentle-pi\skills\gentle-ai\SKILL.md`.
All three were readable. Note: `python-code-style` prescribes a standalone root `ruff.toml` for
*its own* stack; this repository deliberately keeps ruff config in `pyproject.toml`
(`pyproject.toml:56-69`), so that skill's "drop `ruff.toml`" step does **not** apply here.

### Evidence limitations of this phase (read first)

This executor had **no shell/execution tool**. Every fact was established by reading files and
binary strings on disk. Consequences, stated explicitly so the later phases do not inherit a
false certainty:

- Commands the task asked me to run — `uv run ruff --version`, `uv run ruff --help`,
  `uv run ruff config --help`, `uv run ruff config` — **could not be executed**. They are
  replaced by (a) the installed distribution metadata and (b) the settings-documentation strings
  embedded in the installed `ruff.exe`. See §3.4; the substitution is evidence, not recollection,
  but it is *not* the same as the live command, and the verify phase must still paste the real
  command output.
- `uv lock` was **not** run (out of scope by instruction, and no shell). The lock-delta reasoning
  in §4 is reasoned from `uv.lock`, not measured.
- Whether ruff **0.16.7** formats this tree identically to **0.16.0** **could not be measured** —
  no 0.16.7 artifact exists on this machine (§2.3).
- Whether the upstream tag `v0.16.7` exists in `astral-sh/ruff-pre-commit` **could not be
  verified** (no network).
- Dates derived from `.git/logs/HEAD` epoch seconds are arithmetic estimates and are labelled as
  such.

---

## 2. Current state

### 2.1 Version-surface table

Whole-repository sweep for `ruff` (case-insensitive) plus a targeted sweep for `0.16.*`.
"Pins" = names an exact version; "floats" = admits a range; "resolves" = records the outcome;
"silent" = names ruff but no version.

| # | file:line | What it says | Classification |
| --- | --- | --- | --- |
| 1 | `.pre-commit-config.yaml:3` | `rev: v0.16.7` for `repo: https://github.com/astral-sh/ruff-pre-commit` | **pins** (hook env's ruff) |
| 2 | `pyproject.toml:47` | `"ruff>=0.9.0"` in `[dependency-groups] dev` | **floats** (floor only) |
| 3 | `uv.lock:2032-2033` | `[[package]] name = "ruff"` / `version = "0.16.0"` | **resolves** 0.16.0 |
| 4 | `uv.lock:2120` | `{ name = "ruff", specifier = ">=0.9.0" }` under `[package.metadata.requires-dev] dev` | **floats** (mirror of #2) |
| 5 | `.github/workflows/ci.yml:19` | `run: uv run ruff check src/ tests/ scripts/` | **silent** (inherits #3) |
| 6 | `.github/workflows/release.yml:29` | `run: uv run ruff check src/ tests/ scripts/` | **silent** (inherits #3) |
| 7 | `CONTRIBUTING.md:77` | "This project uses **ruff** … Configuration is in `ruff.toml` at the repo root." | **silent on version** (+ stale path, #187) |
| 8 | `CONTRIBUTING.md:29` | `uv run ruff check src/ tests/` | **silent** |
| 9 | `.github/PULL_REQUEST_TEMPLATE.md:20,43,44` | `uv run ruff check …`, `uv run ruff format --check src/ tests/` | **silent** |
| 10 | `openspec/config.yaml:12` | "ruff 0.16.0 (lint+format)" | **asserts 0.16.0** — **gitignored**, untracked (`.gitignore:57`) |
| 11 | `openspec/project.md:82` | "lint `uv run ruff check src/ tests/` (ruff 0.16.0)" | **asserts 0.16.0** — tracked |
| 12 | `openspec/project.md:12,13,16,17,70,83` | linter/formatter/pre-commit all "ruff" | **silent on version** |
| 13 | `openspec/specs/process-boundary/spec.md:258` | "The ruff version pin mismatch (pre-commit `v0.16.7` versus the environment's `0.16.0`) SHALL stay unaddressed here and SHALL be owned by issue #195." | **names both versions** — the only spec clause that does |
| 14 | `AGENTS.md:37` | "`ruff` (lint + fix + format) and `mypy` run on every commit" | **silent on version** |
| 15 | `README.md` / `README_ES.md` | zero `ruff` matches; each only *links* to `CONTRIBUTING.md` (`README.md:749,751`, `README_ES.md:788,790`) | **silent** |
| 16 | `docs/configuration.md:22` | ruff named only as a precedence precedent for `pyproject.toml` discovery | **silent on version** |
| 17 | `tests/**` | **zero `ruff` matches** (whole-directory grep) | **silent — no test asserts a version** |
| 18 | `.venv/Lib/site-packages/ruff-0.16.0.dist-info/METADATA:2-3` | `Name: ruff` / `Version: 0.16.0` | **resolved artifact** (untracked) |
| 19 | `openspec/changes/archive/2026-09-14-chore-ruff-format-drift/**`, `…chore-python-version-313/archive-report.md:72` | records the mismatch as a deferred follow-up | **historical prose — must not be edited** |

Derived facts:

- Exactly **two** declarations are authoritative in practice (`.pre-commit-config.yaml:3` and
  `pyproject.toml:47`), and they disagree. Everything else either inherits one of them or is
  prose.
- **Zero repository tests** reference ruff, so **zero existing tests break** on any pin choice,
  and there is currently **no static guard** for this class of drift.
- The `ruff.toml` named in `CONTRIBUTING.md:77` **does not exist**: reading
  `<repo>/ruff.toml` returns `ENOENT`; the ruff config lives at `pyproject.toml:56` (`[tool.ruff]`).
  That stale reference is #187 — see §7.

### 2.2 Which ruff actually runs, per surface

| Surface | Ruff binary | Version | Evidence |
| --- | --- | --- | --- |
| `git commit` (hook) | hook-local venv created by `pre-commit` from the pinned `rev` | **v0.16.7 per the config** — but see §2.3 | §3.1 |
| `uv run ruff …` (local) | `<repo>/.venv/Scripts/ruff.exe` | **0.16.0** | `.venv/Lib/site-packages/ruff-0.16.0.dist-info/METADATA:2-3`; `…/RECORD:1` lists a single 32 MB `../../Scripts/ruff.exe` |
| CI `lint` job (`ci.yml:9-21`) | `uv sync` then `uv run ruff`, i.e. the lockfile's wheel | **0.16.0** | `ci.yml:16-19` + `uv.lock:2033` |
| CI `coverage`/`test` jobs | ruff is never invoked (only pytest / coverage) | n/a | `ci.yml:24-91` |
| Release `lint` job (`release.yml:12-29`) | same as CI lint | **0.16.0** | `release.yml:25-29` + `uv.lock:2033` |

CI never invokes `pre-commit`, so **CI never runs the hook's ruff**. The two worlds never meet
inside CI.

### 2.3 The "both surfaces are green" claim is **not evidenced on this machine**

This is the most important correction to the orchestrator's briefing. Three independent probes
contradict the assumption that the v0.16.7 hook "already validated staged files":

1. **No v0.16.7 hook environment exists locally.** A whole-cache grep for `0.16.7` under
   `C:/Users/elaze/.cache/pre-commit` returns **"No matches found"**. Yet the same cache holds
   four `ruff-pre-commit` clones, each with the ruff version pinned in its own
   `pyproject.toml`:

| Clone dir | `pyproject.toml:5` | `ruff_pre_commit.egg-info/requires.txt:1` |
| --- | --- | --- |
| `repoym_k5mue` | `"ruff==0.8.0"` | `ruff==0.8.0` |
| `repo3ptoyxgr` | `"ruff==0.15.21"` | `ruff==0.15.21` |
| `repoqghug3i1` | `"ruff==0.16.0"` | `ruff==0.16.0` |
| `repo27dpqiot` | `"ruff==0.16.6"` | `ruff==0.16.6` |

   The newest cached rev is **0.16.6**, never 0.16.7.
2. **The git hook is not installed in this working copy.** `<repo>/.git/hooks/pre-commit` →
   `ENOENT` (and `.git/hooks/pre-commit.legacy` → `ENOENT`). `pre-commit install` has therefore
   never been run in this clone, so no local commit in it ran the hook at any rev.
3. **The repository's own record says the comparison was never made.** The change that created
   PB-10 recorded, at the time:

- `openspec/changes/archive/2026-09-14-chore-ruff-format-drift/proposal.md:68` —
  "Hook ruff (0.16.7) and ambient ruff (0.16.0) disagree … | Low, **unverified** | … no shell
  execution was available in this phase to test it";
- `…/design.md:23` — "the hook's output **was never measured** against 0.16.0";
- `…/apply-progress.md:58` — the pre-commit hook was **not** used as the reformat producer
  (design D1 fixed `uv run ruff format` = 0.16.0 as the producer).

   The `v0.16.7` bump is also recent: `.git/logs/HEAD:720` records the local commit
   `dbaa1f0` "fix(pre-commit): update ruff-pre-commit to version v0.16.7" at epoch
   `1789303823` (≈ 2026-09-13, arithmetic estimate), followed by ≥9 further commits. A rev
   bumped by `pre-commit autoupdate` would have left a `repo*` clone in the cache; there is
   none, so the bump is consistent with a **hand edit of the `rev` string**, and its tag has
   never been resolved by this machine's `pre-commit`.

**Consequence for the proposal:** the issue's implicit evidence (and the briefing's
"the hook already validated staged files with 0.16.7 while CI validated the whole tree with
0.16.0") must **not** be used as proof that 0.16.7 and 0.16.0 agree on this tree. It is
currently an untested assumption. See §4 (probe) and §6 (what can/cannot be pinned).

---

## 3. The divergence mechanism

### 3.1 `ruff-pre-commit` bundles its own ruff; the project environment is not consulted

Verified from the cached clone `C:/Users/elaze/.cache/pre-commit/repo27dpqiot` (rev 0.16.6 —
same shape for every rev):

- `repo27dpqiot/.pre-commit-hooks.yaml` declares three hooks — `ruff-check`, `ruff-format`, and
  the **legacy alias `ruff`** (which is what this repo's `.pre-commit-config.yaml:5` uses):
  ```yaml
  - id: ruff
    entry: ruff check --force-exclude
    language: python
    types_or: [python, pyi, jupyter]
    args: []
    require_serial: true
    additional_dependencies: []
    minimum_pre_commit_version: "2.9.2"
  ```
- `language: python` + `additional_dependencies: []` + no `language: system` means pre-commit
  creates an **isolated virtualenv per hook repo+rev** and installs the hook repo's own
  dependencies there. The project's `.venv` is never on that path.
- `repo27dpqiot/pyproject.toml:1-5`:
  ```toml
  [project]
  name = "ruff-pre-commit"
  version = "0.0.0"
  dependencies = ["ruff==0.16.6"]
  ```
  The **ruff version is a dependency of the hook repo, pinned exactly, at the checked-out rev.**
- The repository's own `.pre-commit-config.yaml` passes **no** `additional_dependencies` (the
  whole file is 18 lines; the only `args` are `[--fix]` on the `ruff` hook).

⇒ The hook's ruff is a function of the `rev` alone. Nothing in `pyproject.toml` or `uv.lock`
influences it, in either direction. This is exactly the mechanism of the divergence.

### 3.2 The tag and the bundled version are written together — `v0.16.7` ⟹ `ruff==0.16.7`

`repo27dpqiot/mirror.py` (the upstream tool that cuts every mirrored release) makes the mapping
mechanical rather than conventional:

- `mirror.py:60-63` asserts the current pin is **exact**, refusing anything but `==`:
  `assert len(specifiers) == 1 and specifiers[0].operator == "==", f"ruff's specifier should be exact matching…"`.
- `mirror.py:97-102` rewrites `pyproject.toml` with
  `re.sub(r'"ruff==.*"', f'"ruff=={version}"', content)` and `README.md`'s `rev: v{version}` with
  the **same** `version` value.
- `mirror.py:33-42` then, in one block per version: `git commit -m f"Mirror: {version}"` followed
  by `git tag f"v{version}"` — the tag is created **after** the pin rewrite in the same
  iteration, from the same variable. (If a version produced no change, the loop prints
  "No change v…" and creates neither commit nor tag.)

⇒ A tag `vX.Y.Z` existing implies the pyproject at that tag pins `ruff==X.Y.Z`. The tag-to-binary
correspondence is therefore reliable **for the version number**; the residual risk is whether the
tag exists at all (§8, verification gaps).

### 3.3 What each surface loads, precisely

Both surfaces read the *same* config file (`pyproject.toml:56` `[tool.ruff]`, discovered from the
repo root — `docs/configuration.md:22` confirms ruff's own upward search finds the first
`pyproject.toml`). They differ only in **which binary reads it**. That is the whole defect: a
single config, two implementations of formatting semantics.

### 3.4 `required-version` **does** exist — first-class, per the installed binary

Verified against the installed artifact, not from memory. The `ruff` 0.16.0 wheel is a single
self-contained binary, and it embeds its generated settings documentation as plain strings.
Grepping `.venv/Scripts/ruff.exe` yields (byte-offset line 75962):

```text
Accepts a [PEP 440](https://peps.python.org/pep-0440/) specifier, like `==0.3.1` or `>=0.3.1`.required-version = ">=0.0.193"Whether to enable preview mode. …
```

Findings:

- **Key name:** `required-version`, a **top-level `[tool.ruff]` setting** (not under
  `[tool.ruff.lint]` or `[tool.ruff.format]`). In a `ruff.toml` it would be `required-version`;
  under `pyproject.toml` it is `[tool.ruff] required-version`.
- **Semantics, as the installed binary documents them:** the value is a **PEP 440 version
  specifier** (`==0.3.1`, `>=0.3.1`, …). Ruff validates the *running* binary against it when it
  loads configuration; a mismatch is a hard error, not a warning and not a silent upgrade.
- The documentation example value printed in the binary is `">=0.0.193"`, i.e. the option
  predates the version in play by many releases — it is not new in 0.16.x.
- **Not verified:** whether `ruff config --help` / `ruff config` print this key (no shell), and
  whether 0.16.7 accepts the identical key and specifier grammar (no 0.16.7 artifact locally).

**Why this matters more than a doc edit:** `required-version` is the only mechanism found that
turns the *hook* into a failing surface. With `[tool.ruff] required-version = "==X"`, whichever
binary is wrong (hook env or venv) **errors out** when it loads `pyproject.toml`, so a
version drift becomes a loud, immediate failure on whichever side moved — instead of the current
silent disagreement. It does **not** make CI install the version; it makes a wrong version fail.

---

## 4. Options, evidence, and cost

Both candidate answers are legitimate; the trade-off is real and is presented rather than
resolved silently.

### Option A — make **0.16.7** authoritative (move the environment up)

| | |
| --- | --- |
| Changes | `pyproject.toml:47` `>=0.9.0` → `==0.16.7`; `.pre-commit-config.yaml:3` unchanged; `CONTRIBUTING.md` names 0.16.7; `uv lock` re-resolves |
| Lock cost | **Network-bound re-resolution.** `uv.lock:2033` `ruff 0.16.0` + its 16 wheel URLs/hashes + sdist (`uv.lock:2032-2054`) are replaced by the 0.16.7 artifact set (≈ 20 lock lines); `uv.lock:2120`'s specifier also changes |
| Risk | **The 0.16.7 formatter has never been run on this tree** (§2.3). `uv run ruff format --check src/ tests/ scripts/` → "68 files already formatted" was measured with 0.16.0 only. If 0.16.7 reformats anything, the change ships a formatting-fix commit touching files inside the four AGENTS.md rule 14 modules (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) whose per-file 100% coverage gates must stay green, and the "68 files" figure becomes a 0.16.0-only fact |
| Evidence for | Newer; the hook already claims it, so nothing in the hook config moves; avoids going backwards; `uvx ruff@0.16.7` makes a cheap direct probe available |
| Evidence against | Zero local verification; larger lock delta; the pin would be raised on the strength of a version string in a config file rather than on a measurement |

### Option B — make **0.16.0** authoritative (move the hook down)

| | |
| --- | --- |
| Changes | `pyproject.toml:47` `>=0.9.0` → `==0.16.0`; `.pre-commit-config.yaml:3` `v0.16.7` → `v0.16.0`; `CONTRIBUTING.md` names 0.16.0; `uv lock` refresh |
| Lock cost | **Expected one-line change.** The resolved artifact set is already 0.16.0 (`uv.lock:2032-2054`), so only the recorded specifier at `uv.lock:2120` (`>=0.9.0` → `==0.16.0`) should change. *Not measured — `uv lock` was out of scope; the verify phase must paste the real `git diff uv.lock`* |
| Risk | Moves the hook **backwards**; a later `pre-commit autoupdate` would move it forward again and silently reintroduce the divergence unless `required-version` (§3.4) or a static guard (§6) prevents it. The maintainer may not want to be a release behind |
| Evidence for | **It is the only version whose formatting output on this tree is measured** (`uv run ruff format --check src/ tests/ scripts/` → 68 files already formatted on `dev@5a2ae38`, ruff 0.16.0); the lock already resolves it, so no formatter surprise and no network; the `v0.16.0` hook pin has already been materialized successfully on this machine (`repoqghug3i1` clone, `ruff==0.16.0`), so the rev is known to be installable |

### Recommended: Option B, plus `required-version` and a static guard

Recommendation (not a decision — §8 Q1 is the maintainer's):

1. **Pin 0.16.0 on both surfaces** (Option B). Rationale, in evidence order:
   (a) it is the only candidate with a measurement on this tree;
   (b) the lock already resolves it, so the change is cheap, offline and reversible;
   (c) choosing 0.16.7 would ship an **unverified formatter** as the authority — the exact failure
   mode #195 exists to remove;
   (d) a "single authority" change that also re-pins the environment is a dependency change
   (AGENTS.md rule 9) and should be the *minimum* dependency change.
2. **Add `[tool.ruff] required-version = "==0.16.0"`** (`pyproject.toml`, beside
   `target-version`/`line-length`) so the authority is self-enforcing on *both* surfaces rather
   than trusting two declarations to stay equal (§3.4).
3. **Add the static guard test** (§6) so declaration drift is caught in the suite, not by a human.
4. If the maintainer prefers 0.16.7, the change **must** additionally carry the direct probe
   `uvx ruff@0.16.7 format --check --diff src/ tests/ scripts/` as apply-phase evidence, compare
   it to `uv run ruff format --check --diff src/ tests/ scripts/`, and accept the possible
   reformat of files inside the four 100% modules plus a network-bound `uv lock`.

### The cheap probe that would settle the formatting-compatibility question

Both candidates can be answered in one command pair (apply phase, needs network once):

```bash
uv run ruff format --check src/ tests/ scripts/                 # 0.16.0 (known: 68 already formatted)
uvx ruff@0.16.7 format --check --diff src/ tests/ scripts/      # 0.16.7 — the unmeasured side
```

If the second command also reports zero files, choosing either version is formatter-neutral on
this tree and the decision can be made on cost/currency alone. A pre-commit-side confirmation is
available too — `pre-commit install && pre-commit run ruff-format --all-files` — which is the only
way to materialize the v0.16.7 hook env (§2.3) and the only way to satisfy acceptance criterion 3
literally.

---

## 5. Blast radius

### 5.1 Files and clauses that name or resolve a ruff version

| Surface | Count | Items |
| --- | --- | --- |
| Declared pins/floor | 2 | `.pre-commit-config.yaml:3`, `pyproject.toml:47` |
| Lockfile | 2 | `uv.lock:2033` (resolution), `uv.lock:2120` (specifier mirror) |
| CI/release invocations (version-silent, inherit the lock) | 2 | `.github/workflows/ci.yml:19`, `.github/workflows/release.yml:29` |
| Docs that must gain a version | 1 (+1) | `CONTRIBUTING.md:77`; optionally `CONTRIBUTING.md:29` (see #212, §7) |
| Other docs naming ruff without a version | 6 | `AGENTS.md:37`, `openspec/project.md:12,13,16,17,70,83`, `.github/PULL_REQUEST_TEMPLATE.md:20,43,44`, `docs/configuration.md:22` |
| SDD metadata asserting a version | 2 | `openspec/project.md:82` (**tracked**), `openspec/config.yaml:12` (**gitignored**, `.gitignore:57`) |
| Spec clause naming both versions | **1** | `openspec/specs/process-boundary/spec.md:258` — PB-10 requirement body |
| Spec **scenarios** naming a version | **0** | PB-10's 5 scenarios (`spec.md:260-292`) name no version |
| Tests referencing ruff | **0** | whole-`tests/` grep: no matches → **no test breaks** |
| Editor config | 0 | no `.vscode/settings.json`, no `ruff.toml`, no `.ruff.toml` |
| Historical prose (read-only) | 15+ | `openspec/changes/archive/2026-09-14-chore-ruff-format-drift/{proposal.md:23,68,75; design.md:18,23,26,76,86; tasks.md:16,56,98; verify-report.md:186; archive-report.md:16,58; apply-progress.md:58}`, `…chore-python-version-313/archive-report.md:72` |

### 5.2 If the pin moves to a different ruff (i.e. Option A)

- **CI lint jobs (2)**: unchanged in text, but their verdict changes — both would run 0.16.7 via
  `uv sync`. No workflow edit is needed, and none should be added.
- **Pre-commit hook**: unchanged (already `v0.16.7`); its env becomes consistent with the lock.
- **`uv.lock`**: the ruff package block is replaced → the largest single diff in the change.
- **Editor integrations**: none in-repo to update; the risk is external (a contributor's globally
  installed ruff, or `uvx ruff` at another version, would now disagree with *both* surfaces —
  another argument for `required-version`).
- **Tests**: none reference ruff → **0 tests break, 0 spec scenarios change**; only the PB-10
  requirement *body* (1 sentence) is affected, plus whatever new guard the change adds.
- **The four AGENTS.md rule 14 modules**: at risk only through a possible reformat (Option A);
  their 100.00% per-file gates and the "no `# pragma: no cover`" ban are unaffected by the pin
  itself, but a formatting commit touching them widens the diff into `src/sofer/`.
- **PB-10's "No CI gate was armed" scenario** (`spec.md:284-286`) asserts **zero**
  `format --check` invocations exist under `.github/workflows/` — so this change must **not** arm
  one, in either option. That constraint survives the pin change.

### 5.3 Rule 13 (README / README_ES mirroring) — **not triggered**

`README.md` and `README_ES.md` contain **zero** `ruff` matches and no development-setup section;
both only hyperlink `CONTRIBUTING.md` (`README.md:749,751`, `README_ES.md:788,790`).
`README_ES.md:774` states explicitly that the technical reference docs (`docs/configuration.md`,
`CONTRIBUTING.md`) are in English. So editing `CONTRIBUTING.md` requires **no** README change.
The verify phase should still paste the two greps as proof.

### 5.4 Rule 7 (README reflects the CLI) — **not triggered** (no CLI surface changes).

### 5.5 Rule 14 — binds indirectly

The 100.00% per-file mandate and the pragma ban apply to `cli.py`, `scanner.py`, `prepare.py`,
`publish.py`. A new guard test lands in `tests/`, which has no per-file floor, so the guard itself
is unconstrained. A reformat under Option A is the only route by which this change could touch
those four files.

---

## 6. What can and cannot be pinned by a test

The repository already has the exact idiom for a "two declarations must agree" contract:
`tests/test_ci_workflows.py` reads repository files with `pyyaml` + `tomllib` and a plain-text
reader (`_read_text`/`_load_toml`/`_workflow`), and `openspec/specs/ci/spec.md` CI-07
("Dev interpreter pin matches the gate interpreter", `spec.md:215-251`) is a precedent where a
*pin-equality* requirement exists, whose scenario 1 is statically checkable. There is also an
explicit precedent for scenarios that are **not** pytest-assertable: the `ci` spec's Test Mapping
(`spec.md:298-316`) carries rows like "README mirrors README_ES | Verify-phase static evidence —
… **not pytest-assertable**", and PB-10 itself is introduced as "evidenced by command output
rather than by a pytest assertion" (`spec.md:254`), as is CI-07 (`spec.md:217`).

### What a test **can** assert (statically, offline, no binary)

1. `.pre-commit-config.yaml` — parse with `yaml.safe_load`, find the
   `astral-sh/ruff-pre-commit` repo entry, and assert its `rev` is `v<X.Y.Z>` where `<X.Y.Z>` is
   the version string extracted from `pyproject.toml`'s dev-group ruff pin. (Mirrors
   `_load_yaml` / `_load_toml` already in the file.)
2. `pyproject.toml` — assert the `[dependency-groups] dev` ruff specifier is **exact** (`==X.Y.Z`,
   not a `>=` floor) and that it equals the `rev`. This mechanically closes the "floating floor"
   half of #195 and prevents `uv lock` upgrades from silently moving the formatter.
3. `pyproject.toml` — if `required-version` is adopted, assert
   `[tool.ruff] required-version` equals the same `X.Y.Z` (making the self-enforcing mechanism
   itself tamper-evident).
4. `uv.lock` — optionally (tomllib) assert the `[[package]] name = "ruff"` version equals
   `X.Y.Z`. Cheap and offline, but couples the suite to the lockfile format; the repo currently
   has **no** test that parses `uv.lock`, so this would be a new coupling — a design decision, not
   an obligation.
5. `.github/workflows/*.yml` — reusing the scanning style of
   `test_coverage_gate_is_config_driven_without_cli_floor`, assert no workflow hardcodes a ruff
   version literal (keeps the authority in exactly one place).

### What a test **cannot** assert

- **Criterion 3's substance** — that `uv run ruff format --check src/ tests/` and the hook produce
  the same verdict on the same file. That is a runtime property of two *separately installed
  binaries*; asserting it in pytest would require installing/executing a second ruff (network +
  a hook env) inside the suite, which is a dependency class this repo's idiom avoids and which
  AGENTS.md rule 9 (dependency discipline) discourages. The honest precedents are PB-10 and CI-07:
  scenarios evidenced by pasted command output.
- **That the pre-commit hook is active at all**: `.git/hooks/pre-commit` is per-clone and
  untracked (it does not exist here), so no repo-level test can observe hook activation.
- **What `uv lock` will write** — resolver + network; verify-phase evidence only.

### Recommendation for criterion 3's shape

Split it, in this repository's idiom:

- **(a) pytest-assertable static equality** of `.pre-commit-config.yaml`'s rev == `pyproject.toml`
  dev pin == `required-version` (if adopted) — a small guard in `tests/test_ci_workflows.py`.
- **(b) verify-phase command evidence** for the behavioural half: paste
  `uv run ruff format --check src/ tests/` and its 0.16.7 counterpart
  (`uvx ruff@0.16.7 format --check --diff …`, or `pre-commit run ruff-format --all-files` after
  `pre-commit install`) — recorded in the verify report and, if the maintainer wants it spec'd,
  as one clause in the relevant spec's Test Mapping ("Verify-phase runtime evidence — CI-01/CI-07
  gate-exit-code precedent").

Note where such a clause would live: `openspec/specs/process-boundary/spec.md` has **no** Test
Mapping table (grep for `Mapping` in that file: no matches), whereas
`openspec/specs/ci/spec.md:298-316` does. That asymmetry is a real placement decision (§8 Q3).

---

## 7. Risks, non-goals, and out-of-scope cross-references

### In scope for this change

- One declared authority for the ruff version across the **two** real declarations
  (`.pre-commit-config.yaml:3`, `pyproject.toml:47`).
- Naming that version in `CONTRIBUTING.md` (today it names none).
- `uv.lock` refreshed in the same change when the pin moves (AC5; spec precedent PKG-06 at
  `openspec/specs/packaging/spec.md:134` — "`uv.lock` SHALL be regenerated" when a dependency
  declaration changes).
- Optionally: `[tool.ruff] required-version` (§3.4) and the static guard test (§6).
- Mandatory spec touch: `openspec/specs/process-boundary/spec.md:258` currently **forbids** this
  change's subject ("SHALL stay unaddressed here and SHALL be owned by issue #195"). Since this
  *is* #195, that sentence must be superseded minimally — replace the "stays unaddressed" clause
  with the resolution and a pointer, **without** weakening PB-10's other clauses: the six-file /
  formatting-only framing, "no new CI step", and "enforcement remains the local pre-commit
  `ruff-format` hook".

### Explicitly out of scope — must NOT be absorbed

- **#187** — `CONTRIBUTING.md:77` points at a `ruff.toml` at the repo root that does not exist
  (probe: `ENOENT`); the config is `pyproject.toml:56` `[tool.ruff]`. #187 also owns the stale
  module inventories. If both land together, they stay **separate concerns in the PR
  description**. *Interaction hazard to flag:* this change will edit that same sentence
  (`CONTRIBUTING.md:77`) to name the version, so the two changes will conflict textually — resolve
  by ordering, not by merging the concerns.
- **#212** — documented gate commands narrower than CI's. Concrete instance confirmed here:
  `CONTRIBUTING.md:29` documents `uv run ruff check src/ tests/` while `ci.yml:19` runs
  `src/ tests/ scripts/`. Do **not** "fix while here": widening the documented command is #212's
  concern (and note `scripts/` currently contains no ruff-visible Python anyway — `scripts/`
  grep for `ruff`: no matches — but that is irrelevant; the concern boundary stands).
- **#194** — arming a `ruff format --check` CI gate. PB-10 assigns recurrence to #194 and its
  "No CI gate was armed" scenario (`spec.md:284-286`) asserts **zero** `format --check`
  invocations under `.github/workflows/` in both states. This change must add none.
- **Raising the pin as a side effect** of any other change — AGENTS.md rule 9, and the
  #177 design's own instruction (`.git/…` archive `…chore-ruff-format-drift/design.md:26`):
  "Aligning the pins is a dependency change that must not ride along in a whitespace-only commit".
- **Editing historical SDD prose** under `openspec/changes/archive/**` — including the #177 and
  #178 records that name the mismatch. They are history, not state.
- **Touching the four AGENTS.md rule 14 modules** except via a formatter-only consequence that the
  change explicitly accepts and measures (Option A).

### Principal risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Choosing 0.16.7 ships an unmeasured formatter as the authority; `format --check` goes red | **Medium-high** — never measured (§2.3) | Reformat commit inside the 100%-gated modules; PB-10 gate red | Run the §4 probe **before** proposing; make the reformat, if any, an explicit task with its own evidence |
| Reintroduced drift: a later `pre-commit autoupdate` moves the hook off the pin again | High without a mechanism | The exact defect returns | `required-version` (§3.4) + static guard test (§6) |
| The `v0.16.7` tag was never resolved locally; if it does not exist upstream, the hook breaks on the next commit | **Unknown** — unverifiable offline | `git commit` fails for everyone with hooks installed | Verify with one `pre-commit autoupdate`-free probe: `pre-commit run --all-files` (or `git ls-remote --tags`); part of the §8 verification gaps |
| The pre-commit hook is **not installed** in the maintainer's working copy (it is not here) | Observed here | AC3's "the hook produces the same verdict" cannot be demonstrated in this clone without `pre-commit install` | The change (or the verify report) must state the exact command used to materialize the v0.16.7 env |
| `uv lock` diff larger than expected (Option B's one-line expectation unmeasured) | Low | Review noise; AC5 wording | Verify phase pastes the real `git diff uv.lock` |
| Editing the gitignored `openspec/config.yaml:12` looks like a change but is invisible to CI | Certain | A reviewer may treat it as tracking the version | Treat `openspec/project.md:82` (tracked) as the change-bearing metadata; mention `config.yaml` as local-only |

---

## 8. Verification gaps the later phases must close (probes, not decisions)

These are cheap, network-allowed in apply/verify, and each changes a conclusion above:

1. `uv run ruff --version`, `uv run ruff --help`, `uv run ruff config --help`, `uv run ruff config`
   — confirm the live 0.16.0 surface and that `required-version` is listed (§3.4 substituted binary
   strings for these; the real output should replace it).
2. `uvx ruff@0.16.7 format --check --diff src/ tests/ scripts/` vs
   `uv run ruff format --check --diff src/ tests/ scripts/` — settles formatting compatibility on
   this tree (§4).
3. Does upstream tag `v0.16.7` exist? (`git ls-remote --tags https://github.com/astral-sh/ruff-pre-commit v0.16.7`,
   or `pre-commit install && pre-commit run ruff-format --all-files`, which materializes the hook
   env — absent from `C:/Users/elaze/.cache/pre-commit` today, §2.3).
4. `uv lock` (Option A or B) → paste `git diff --stat uv.lock` and `uv lock --check` exit code
   (§4's lock-delta claims are reasoned, not measured).

---

## 9. Open questions for the orchestrator (genuine scope decisions)

**Q1 — Which version becomes authoritative: the measured 0.16.0, or the newer 0.16.7 the hook
already claims?** This is the one decision the evidence cannot make alone. The evidence favours
0.16.0 (only version measured on this tree; one-line lock delta; no formatter risk; hook moves
down). The "stay current" instinct favours 0.16.7 (nothing in the hook config moves; but it ships
an unmeasured formatter and needs a network-bound lock refresh). **If 0.16.7 is chosen, does the
change accept a possible formatting commit that reaches into the four rule-14 modules, and does it
carry the 0.16.7 probe as apply-phase evidence?** (This is a scope/cost decision, not a probe.)

**Q2 — Does the change adopt `[tool.ruff] required-version` as the enforcement mechanism, or only
align the declarations?** `required-version` is the only mechanism that makes the *hook itself*
fail loudly on drift, but it is a new repo-wide setting: any contributor, editor integration, or
`uvx ruff` at a different version starts erroring, and it must be kept in sync by the guard test
or it becomes a third place to forget. Align-and-guard-only is the smaller change; adopt-and-guard
is the durable one.

**Q3 — Where does the static guard (and its spec clause) live: the `ci` capability, which already
has a Test Mapping table and the CI-07 pin-equality precedent, or a new `process-boundary` (PB-10)
clause, which has no Test Mapping table?** The choice determines which spec receives the delta and
whether a Test Mapping row is added. It also decides whether `tests/test_ci_workflows.py` grows a
new concern or a new test file appears.

**Q4 — Does the change also update the tracked SDD metadata that asserts a version
(`openspec/project.md:82` "ruff 0.16.0") when the authority changes, or is SDD metadata out of
scope for a chore PR?** Only one of the two statements (`project.md:82`) is tracked;
`openspec/config.yaml:12` is gitignored (`.gitignore:57`) and invisible to CI. Leaving a tracked
file asserting the *old* version would recreate a small, quieter version of the same defect.

**Q5 — Does criterion 3 stay a manual one-off, or does the proposal add a spec scenario for it?**
Answering this determines whether §6's split (static equality test + verify-phase command
evidence) becomes spec'd behaviour or merely a PR-description claim.

---

*End of exploration. No source file, workflow, lockfile, or spec was modified by this phase; the
only writes were this artifact and the Engram save.*
