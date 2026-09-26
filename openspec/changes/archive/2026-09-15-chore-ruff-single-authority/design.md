# Design: chore-ruff-single-authority

**Change**: `2026-09-15-chore-ruff-single-authority` · **Issue**: #195 — *chore: two authoritative ruff
versions in play (pre-commit v0.16.7 vs ambient 0.16.0)* · **Branch** `chore/195-ruff-single-authority`
**Artifact mode**: hybrid — this file + Engram `sdd/2026-09-15-chore-ruff-single-authority/design`
**Inputs read this phase**: `proposal.md`, `preproposal.md`, `explore.md`,
`specs/ci/spec.md`, `specs/process-boundary/spec.md`, plus the canonical
`openspec/specs/{ci,packaging,process-boundary}/spec.md`, `tests/test_ci_workflows.py`,
`pyproject.toml`, `.pre-commit-config.yaml`, `uv.lock`, `CONTRIBUTING.md`,
`.github/workflows/*.yml`, `openspec/config.yaml`, `.gitignore`.
**Evidence policy** (D4): every claim carries `file:line`, a read command, or is labelled
**unverified**. No upstream ruff documentation is cited, because the research lane was de-selected.

**One-line outcome**: one ruff version (`0.16.7`) declared in three places that a static guard forces
equal, enforced at config load by `[tool.ruff] required-version`, with PB-10's now-false deferral
sentence replaced and **no** CI format gate armed.

---

## 1. Context and ratified decisions

### 1.1 The defect in one paragraph

Two formatter implementations are in play and nothing makes their disagreement visible.
`.pre-commit-config.yaml:3` pins `astral-sh/ruff-pre-commit` at `rev: v0.16.7`, whose hook is a
`language: python` hook with `additional_dependencies: []` — pre-commit builds a per-rev venv from the
hook repo's own `pyproject.toml` (`dependencies = ["ruff==X.Y.Z"]`), so the project environment is never
consulted (`explore.md` §3.1). Meanwhile the dev group floats `ruff>=0.9.0` (`pyproject.toml:47`) and
`uv.lock:2034` resolves `0.16.0`, which is what `uv run ruff …` and both CI lint jobs use
(`ci.yml:19`, `release.yml:29`, each after `uv sync`). PB-10 currently states the mismatch is deferred
to #195 (`openspec/specs/process-boundary/spec.md:258`). This **is** #195.

### 1.2 Ratified decisions — D1–D4 (carried, not re-opened)

| ID | Decision | Design consequence |
| --- | --- | --- |
| D1 | Authoritative version is `0.16.7` | Dev pin `ruff==0.16.7`; `uv.lock` refreshed in the same change; both versions measured `68 files already formatted` on this tree, so no reformat is expected |
| D2 | Enforcement is `[tool.ruff] required-version` **plus** a static guard test | A third declaration site plus a three-way equality guard; a wrong binary fails at config load (measured: `ruff check` and `ruff format` both abort) |
| D3 | AC3 is evidenced by exercising the real hook | Hook materialisation probe (§5.2) is a required apply step, not optional evidence |
| D4 | Research lane de-selected | No upstream guarantee is asserted anywhere in this design; `required-version` semantics are recorded as **measured on this tree**, never as documented behaviour |

### 1.3 Design rulings on the seven open questions

| # | Question | Ruling |
| --- | --- | --- |
| 1 | `ci` CI-08 vs `process-boundary` PB-14 | **Ratify `ci`** (§1.4) |
| 2 | Owner of the `uv.lock` refresh obligation | **CI-08 owns it**; PKG-06 is cited as the same class with its `fastmcp` scope stated (§1.5) |
| 3 | PB-10 restatement wording | **Ratify as written**, with two collateral scoping rules added (§1.6) |
| 4 | Guard-test design | §3 |
| 5 | `tests/test_ci_workflows.py` docstring | **Extend to `CI-01..CI-08` and re-derive the count**; add the reconciling clause naming the four non-`ci` tests (§4) |
| 6 | `uv.lock` refresh command | No flag is asserted. A probe sequence with accept/reject rules is specified (§5.1) |
| 7 | `CONTRIBUTING.md:77` | Insert the version into the **first** sentence only; #187's second sentence stays byte-identical; same-line collision sequenced deliberately (§2.6) |

### 1.4 Ruling 1 — ratify `ci` for CI-08 (cost of moving stated)

**Adopted: `ci`.** Re-verified this phase:

| Evidence | Reading |
| --- | --- |
| `openspec/specs/ci/spec.md:285` | The `## Test Mapping` table. `grep "^## Test Mapping" openspec/specs/` returns exactly `ci/spec.md:285` and `coverage/spec.md:283` — two capabilities only |
| `ci/spec.md:285-287` | The table's own intro: *"Static workflow/config assertions live in `tests/test_ci_workflows.py` (pyyaml + tomllib)"* — the exact file the three guards land in |
| `ci/spec.md:215-283` (CI-07) | The direct precedent: a **cross-file declaration-equality** contract (`.python-version` equals both gate-job pins) hosted in `ci`, added by a change that armed no CI step either (all five CI-07 rows are verify-phase — `ci/spec.md:313-317`) |
| `ci.yml:19`, `release.yml:29` | The authority decides what CI lints with: the version reaches CI through `uv.lock`, which follows the dev specifier. The claim is CI-facing |
| `ci/spec.md:5-11` | Adding CI-07 left the `## Purpose` paragraph alone; a new requirement needs no Purpose edit here |
| `openspec/specs/process-boundary/spec.md:252-380` | `process-boundary` has **no** `## Test Mapping` table and no PB-14: requirement headings stop at PB-13 (`:339`) |

**Cost of moving to PB-14, stated so the move stays viable:** (a) the delta would have to *create* a
`## Test Mapping` section inside PB-14 — a new structural element in a canonical file that has never had
one, ≈6–8 added lines; (b) `tests/test_ci_workflows.py` would gain a second owning capability, losing the
single-owner property that makes the file's docstring coherent; (c) the `ci` Test Mapping table would
stay at 22 rows while PB-14's new table carried 3. **No test, no scenario, and no evidence class changes
under either home.** If the maintainer prefers one capability per change, the move costs exactly (a)–(c)
and nothing else. The #177 counter-precedent (*"a `ci` requirement naming a workflow step would be
false"*) does not transfer: CI-08 names no workflow step, adds no workflow file, and asserts the
**inverse** (zero ruff version literals under `.github/workflows/**`).

### 1.5 Ruling 2 — the `uv.lock` obligation lives in CI-08, not in PKG-06

**The gatekeeper's finding is confirmed.** `openspec/specs/packaging/spec.md:132-134` (PKG-06) reads:
*"`pyproject.toml` SHALL declare `fastmcp>=3.4,<4` in `dependencies`; MAY retain `mcp` alias with
identical pin. `uv.lock` SHALL be regenerated."* The regeneration clause sits in a sentence whose subject
is the `fastmcp` declaration, so it is scoped to **that** declaration. PKG-06's two scenarios
(`:136-146` — `dependencies include fastmcp`, `Alias identical pin`) assert the `fastmcp` pin and the
optional alias; **neither asserts the lock**, so PKG-06 is
not even an evidenced owner of lock hygiene for its own clause, let alone for a ruff pin move. The
`packaging` spec has no `## Test Mapping` table at all (`grep "^## Test Mapping" openspec/specs/` →
`ci` + `coverage` only).

**Ruling: CI-08 owns its own lock-refresh obligation.** The requirement body already states *"A change
that moves the pin SHALL refresh `uv.lock` in the same change"*, so the obligation has a normative home;
what is wrong is the trailing claim that PKG-06 owns it. The apply phase therefore makes this **exact
two-part wording fix** in `openspec/changes/2026-09-15-chore-ruff-single-authority/specs/ci/spec.md`
(this design does not write it; apply does):

1. In the CI-08 body, replace
   `A change that moves the pin SHALL refresh \`uv.lock\` in the same change; \`packaging\` PKG-06 owns that
   rule and this requirement SHALL NOT re-declare it.`
   with
   `A change that moves the pin SHALL refresh \`uv.lock\` in the same change, confined to the ruff package`
   `block and the dev specifier. \`packaging\` PKG-06 states the same regeneration class for its own`
   `\`fastmcp\` declaration and SHALL NOT be read as owning this one: its \`uv.lock\` clause is scoped to that`
   `declaration, so the obligation for a ruff pin move is stated here, in CI-08.`
2. In the delta's *Cross-referenced and deliberately untouched* table, replace the PKG-06 row's reason
   (`CI-08 states the same obligation without re-declaring it, so the lock rule keeps exactly one owner`)
   with `CI-08 owns its own lock-refresh obligation for a ruff pin move; PKG-06's clause is scoped to the`
   `\`fastmcp\` declaration and is cited as the same class of rule, not as this one's owner.`

**Which requirement a future reader finds it in**: **`ci` CI-08**, then `ci`'s Test Mapping consumption
of `git diff uv.lock` (AC5 evidence). PKG-06 stays a one-line packaging clause about `fastmcp`.

**No new scenario for the lock duty — and why.** PKG-06 is the in-repo precedent for a lock-refresh
clause carried in a requirement **body** with no scenario of its own. Adding a fifth CI-08 scenario would
add a fifth Test Mapping row whose evidence is byte-identical to AC5's verify-phase commands, growing the
canonical `ci` table for no new information. Rule 6 constrains *scenarios*, and no scenario changes here.
**Rejected alternative** (recorded): a `CI-08 S5 — pin move refreshes uv.lock` scenario; rejected for the
row-inflation reason above, reversible at tasks time if the maintainer wants every body duty scenario-visible.

**Also corrected**: the proposal's AC5 row cites *"`packaging` PKG-06's regeneration rule"* as the owner.
That citation is now superseded — the apply phase records the correction in `tasks.md`/apply progress and
the verify report cites CI-08 as the obligation's home with PKG-06 as precedent.

### 1.6 Ruling 3 — PB-10 restatement: ratified, plus two scoping rules

**Ratified as written** (`specs/process-boundary/spec.md:41-51`): one sentence removed, one normative
sentence replacing it in place, **no version literal**, the five scenarios and the remaining clauses
verbatim, and the non-normative `(Previously: …)` note. Reasons to leave it untouched:

- The restatement names the three declarations and the guard (`ci` CI-08) without naming a value —
  a spec literal would be a third place to forget a bump, which is the class of defect #195 exists to
  remove.
- The `(Previously: …)` note is a **canonical-spec convention**, not an invention here:
  `process-boundary/spec.md:12,63,95,115,232` all carry such notes, as do `mcp-server`, `codebook`,
  `publish`, `prepare`, `tool-config`, `repo-compliance`, `scan` and `data-quality`.
- **Criterion 7 refinement (recorded, because it is load-bearing):** the claim *"no spec file names a
  ruff version literal"* is only true of **normative** text. The `(Previously: …)` line intentionally
  names `v0.16.7` and `0.16.0` as history, exactly like every other `(Previously: …)` note in
  `openspec/specs/**`. The invariant is therefore: **normative clauses naming a ruff version: 1 → 0**,
  with the historical note exempt by convention. Verify must check the normative paragraphs, not
  `grep "0.16"` over the whole file (§6, criterion 7).

Two collateral rules the restatement needs, both discovered this phase:

1. **Verification-scoping rule.** PB-10's *"Exactly the six test files changed"* and *"Formatting-only"*
   scenarios (`openspec/specs/process-boundary/spec.md:267-279`) describe the **historical #177 edit**
   ("Reaching that state SHALL be a formatting-only edit — exactly these six test files SHALL change"),
   evidenced by that change's archive. **This change's diff touches `pyproject.toml`, `uv.lock`,
   `CONTRIBUTING.md` and `tests/test_ci_workflows.py`, and therefore must not be measured against those
   two scenarios.** PB-10's *live* clauses for this change are: the formatter-integrity invariant
   (`format --check` exits 0), the no-new-CI-step clause, the #194 ownership clause, the single-authority
   sentence, and the sibling-gates clause. A verify phase that re-runs S2/S3 against this diff would
   produce a false failure; naming the rule here prevents that.
2. **Sync-ordering rule.** PB-10's new sentence forward-references `ci` CI-08. `sdd-sync` must land both
   deltas **in the same sync operation**: a reader between the two writes would see PB-10 pointing at a
   requirement that does not exist yet. Verify confirms that whenever PB-10's restatement is in the
   canonical `process-boundary`, `grep -c "CI-08" openspec/specs/ci/spec.md` is non-zero.

**Known, accepted pre-existing imprecision**: `ci/spec.md:5-11` (`## Purpose`) enumerates `CI-01..CI-06`
and is already stale for CI-07. This change does **not** fix it: doing so would edit canonical `ci` prose
for CI-07's own omission, which is not this change's, and CI-07's precedent is that a new requirement
needs no Purpose upkeep. Recorded in the PR body so a reviewer does not read it as an oversight.

---

## 2. Architecture and the exact file-by-file edit plan

### 2.1 How the authority propagates

```text
pyproject.toml [dependency-groups] dev  "ruff==0.16.7"      <- THE source (extracted by the guards)
        |                                        \
        | uv lock                                 \  guarded equality (CI-08 S1)
        v                                          v
  uv.lock  ruff 0.16.7                    pyproject.toml [tool.ruff]
        |                                 required-version = "==0.16.7"
        | uv sync / uv run                         |
        v                                          | config load
  .venv ruff.exe 0.16.7  --> ruff check / ruff format        wrong binary -> HARD ERROR
        ^                                                  (measured, both subcommands)
        |
  .pre-commit-config.yaml  rev: v0.16.7  --> hook venv, its own ruff==0.16.7
                                              guarded equality (CI-08 S1)
```

One value, three declarations, no fourth place to forget it: the guard tests (and the correction in
`CONTRIBUTING.md`) **extract** `X.Y.Z` rather than restating it, so a bump edits declarations only
(§3). No `src/sofer/**` code path reads a ruff version — the only ruff reference in `src/` is
`src/sofer/mcp_server.py:1` `# ruff: noqa: E501`, a directive (verified this phase).

### 2.2 Edit plan

| # | Path | Exact edit | Est. lines |
| --- | --- | --- | --- |
| 1 | `pyproject.toml:47` | `    "ruff>=0.9.0",` → `    "ruff==0.16.7",` | 2 |
| 2 | `pyproject.toml:56-62` (`[tool.ruff]`) | insert, after `line-length = 100` (`:58`) and before the `extend-exclude` comment block (`:59`): a 3-line comment plus `    required-version = "==0.16.7"` | 4 |
| 3 | `uv.lock` | **regenerated by `uv lock` only — never hand-edited.** Expected diff: the `ruff` package block (`uv.lock:2032-2055`: version `:2034`, `sdist` `:2036`, the 17 wheel entries) and the dev specifier `uv.lock:2120`. Probe + accept/reject rules: §5.1 | ≈40 (unverified) |
| 4 | `.pre-commit-config.yaml` | **no edit.** Already `rev: v0.16.7` (`:3`). The guard test fails if it moves alone, so "unchanged" is an asserted property, not an assumption | 0 |
| 5 | `tests/test_ci_workflows.py` | one shared extraction helper + 2 module constants + 3 tests + the docstring reconciliation (§3, §4) | ≈78 |
| 6 | `CONTRIBUTING.md:77` | one clause in the **first** sentence (§2.6) | 2 |
| 7 | `.../specs/ci/spec.md` (change root) | the two wording fixes of §1.5; nothing else | ≈6 |
| 8 | `.../specs/process-boundary/spec.md` (change root) | **unchanged** — ratified as written (§1.6 has the collateral rules, not a text change) | 0 |
| 9 | `openspec/specs/**` | **not edited by this change.** Canonical sync is `sdd-sync`'s job | 0 |

**No other path may appear in the diff.** In particular: no `.github/workflows/**` (zero ruff version
literals today — `grep "format" .github/workflows/` → 0 matches, verified this phase), no
`src/sofer/**`, no `openspec/project.md`, no `openspec/config.yaml`.

### 2.3 `pyproject.toml` — the two edits, verbatim

Pin (`:47`), exact specifier, no floor — a floor is what let `uv lock` resolve `0.16.0` in the first
place:

```toml
    "ruff==0.16.7",
```

`[tool.ruff]` (`:56-62`), inserted after `line-length = 100`:

```toml
    # Single authoritative ruff version: equal to the dev-group pin above and to the
    # `ruff-pre-commit` rev; the three declarations are forced to agree by CI-08's guards in
    # tests/test_ci_workflows.py. A drifting binary fails ruff here, at config load.
    required-version = "==0.16.7"
```

**Rule 1 (no hardcoded values) compliance, stated rather than assumed.** This literal is a
**build/toolchain declaration**, not a runtime default: it is the same class as `.python-version`, which
CI-07 already treats as a declaration, or `[tool.mypy] python_version = "3.10"` (`pyproject.toml:74`),
both already literals in this file. `[tool.sofer]` holds *tool-wide runtime defaults* consumed by
`src/sofer/config.py`; a formatter's own required version is not a runtime default, and no `src/sofer/`
code path reads it (verified above). The comment deliberately does **not** repeat the version, so there
is exactly one occurrence in the file per declaration site.

### 2.4 `uv.lock` — regenerated, never hand-written

Hand-editing a lock file would produce an internally inconsistent lock; `uv lock` is the only producer.
The confinement expectation, and what counts as unrelated churn to **surface rather than absorb**, are
in §5.1. `uv.lock` is derived state, which is also why **no pytest guard parses it** (§3.5).

### 2.5 `.pre-commit-config.yaml` — zero diff, asserted

The hook already declares the authoritative version, so criterion 2's `.pre-commit-config.yaml` half is
satisfied by *not* editing it. The guard asserts the `astral-sh/ruff-pre-commit` entry's `rev` equals
`v` + the dev pin, so any future one-sided move of the rev goes red. `grep -n
"astral-sh/ruff-pre-commit" .pre-commit-config.yaml` → the entry is at `:2-3`; the file is 18 lines and
passes no `additional_dependencies`, which is why the hook's ruff is decided by the `rev` alone.

### 2.6 `CONTRIBUTING.md:77` — one clause, one sentence, #187 untouched

Current line 77 (single line, three sentences):

> `This project uses **ruff** for linting and formatting. Configuration is in `ruff.toml` at the repo
> root. Run `ruff check` and `ruff format` before committing — the pre-commit hook does this
> automatically.`

**Exact edit — first sentence only:**

> `This project uses **ruff** 0.16.7 for linting and formatting. Configuration is in `ruff.toml` at the
> repo root. Run `ruff check` and `ruff format` before committing — the pre-commit hook does this
> automatically.`

| Concern | Rule |
| --- | --- |
| **#187 not absorbed** | The second sentence's `ruff.toml` path (which does not exist — a repo-root `ruff.toml` is ENOENT; config lives at `pyproject.toml:56`) stays **byte-identical**. The guard asserts the *presence of the version* and asserts nothing about the path |
| **#212 not absorbed** | `CONTRIBUTING.md:29`'s `uv run ruff check src/ tests/` (narrower than `ci.yml:19`'s `src/ tests/ scripts/`) is not touched. AC4's evidence runs the *enforced* command instead of editing that line |
| **Section scoping** | The version must land inside `### Code style` (`:75`) and before the next heading `### Type checking` (`:80`), because CI-08 S3 greps that section. The version may **not** be placed in the Development-commands block (`:22-31`) — that block is #212's surface |
| **Same-line collision with #187** | Both changes edit line 77. If #187 lands first, apply **re-reads line 77 before applying** and re-anchors the edit; no stale hunk, no merge of concerns. Apply sequences itself so the sentence-changing edit happens after any #187 rebase |
| **Mechanical proof of the boundary** | `git diff --word-diff CONTRIBUTING.md` must show exactly one changed line and exactly one inserted token (`0.16.7`) plus its space; the `ruff.toml` sentence must not appear in the diff at all |

---

## 3. Guard-test design (ruling 4)

### 3.1 Placement and the shared extractor

All three guards live in **`tests/test_ci_workflows.py`**, appended after
`test_pr_template_has_coverage_checklist_item` (`:421`), with the helper and the two module constants
placed next to the existing helpers (after `_load_toml`, before `_workflow`). Rationale: AGENTS.md rule 4
(no duplicated logic) — `_read_text` / `_load_toml` / `_load_yaml` are reused, not re-implemented; and one
module owns repository-shape contracts. Appending tests keeps every existing line anchor intact.

**No fourth test.** The module docstring's 1:1 claim is preserved: three scenarios → three tests. A test
for the lockfile, for the hook's activation, or "the tests do not hardcode a version" would be an
unmapped, near-vacuous fourth test (§3.5).

### 3.2 Constants and the extraction helper

```python
_RUFF_PRE_COMMIT_REPO = "https://github.com/astral-sh/ruff-pre-commit"
_DEV_ENTRY_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<spec>[<>=!~].*)$")
_EXACT_PIN_RE = re.compile(r"^==(?P<version>\d+\.\d+\.\d+)$")


def _declared_ruff_version() -> str:
    """Extract the ``X.Y.Z`` version from the ``pyproject.toml`` dev-group ruff pin.

    The dev pin is CI-08's single source of the ruff version: the guards derive the
    value from it and carry no version literal of their own, so bumping ruff edits
    declarations only.

    Returns:
        The version without its specifier, e.g. ``"0.16.7"``.
    """
    dev = _load_toml("pyproject.toml")["dependency-groups"]["dev"]
    pins = []
    for entry in dev:
        match = _DEV_ENTRY_RE.match(entry) if isinstance(entry, str) else None
        if match is not None and match.group("name") == "ruff":
            pins.append(match.group("spec").strip())
    assert len(pins) == 1, f"expected exactly one ruff dev pin, found {pins}"
    exact = _EXACT_PIN_RE.match(pins[0])
    assert exact is not None, (
        f"the ruff dev pin must be an exact ==X.Y.Z specifier, got {pins[0]!r} — a floor "
        "lets `uv lock` drift the formatter (this is how 0.16.0 got in)"
    )
    return exact.group("version")
```

Two properties worth stating: `_DEV_ENTRY_RE` parses a PEP 508 **name** rather than string-matching the
`"ruff"` prefix, so a future `ruff-lsp>=0.1` entry is excluded instead of tripping the "exactly one"
assertion; and the exactness assertion is what makes the guard fail on today's `ruff>=0.9.0` — the RED
state the apply phase must observe **before** editing `pyproject.toml` (§3.6).

### 3.3 The three tests — assertion shape

```python
def test_ruff_pin_hook_rev_and_required_version_agree() -> None:
    """CI-08 S1: the dev pin, required-version, and the hook rev name one version."""
    version = _declared_ruff_version()
    required = _load_toml("pyproject.toml")["tool"]["ruff"]["required-version"]
    assert required == f"=={version}", f"required-version must be '=={version}', got {required!r}"
    config = _load_yaml(".pre-commit-config.yaml")
    revs = [
        repo.get("rev") for repo in config["repos"] if repo.get("repo") == _RUFF_PRE_COMMIT_REPO
    ]
    assert revs == [f"v{version}"], f"ruff-pre-commit rev must be 'v{version}', got {revs!r}"


def test_workflows_do_not_declare_a_ruff_version() -> None:
    """CI-08 S2: the version reaches CI through uv.lock, never through a workflow."""
    version = _declared_ruff_version()
    names = _workflow_names()
    assert names, "no workflow files found — the scan would pass vacuously"
    for name in names:
        raw = _read_text(f"{_WORKFLOW_DIR}/{name}")
        assert version not in raw, f"{name} declares the ruff version {version}"
        assert re.search(r"ruff\s*(?:==|@|>=|<=|~=|!=|>|<|=)\s*\d", raw) is None, (
            f"{name} declares a ruff version specifier"
        )


def test_contributing_names_the_declared_ruff_version() -> None:
    """CI-08 S3: the Code style section names the version the pin declares."""
    version = _declared_ruff_version()
    text = _read_text("CONTRIBUTING.md")
    assert "### Code style" in text, "CONTRIBUTING.md has no '### Code style' section"
    section = text.split("### Code style", 1)[1].split("### ", 1)[0]
    assert re.search(rf"(?<![\d.]){re.escape(version)}(?![\d.])", section), (
        f"the Code style section must name ruff {version}"
    )
```

Design notes on the two non-obvious choices:

- **S2 asserts two things**: the extracted literal is absent from every workflow (cheap and exact) *and*
  no ruff version-specifier syntax exists (so a *different* version — or a `uses: …/ruff-pre-commit@vX`
  form — cannot slip in by not matching today's value). The non-empty names assertion removes the
  vacuous-pass hole the module's existing `test_ci_workflow_files_present` covers for its own tests.
- **S3 is boundary-aware** (`(?<![\d.])…(?![\d.])`): a bare `version in section` would accept `0.16.7`
  as a substring of `0.16.70`. No literal appears in the test — the pattern is built from the extracted
  value.

### 3.4 Behaviour on a missing or malformed declaration

| Condition | Behaviour (deliberately loud, never a skip) |
| --- | --- |
| `pyproject.toml` / `.pre-commit-config.yaml` / `CONTRIBUTING.md` absent | `FileNotFoundError` from `_read_text` |
| `[dependency-groups]` or `dev` absent | `KeyError` from the subscript (module style is direct subscripting) |
| zero, two, or more `ruff` dev pins | `assert len(pins) == 1` with the parsed list in the message |
| pin is a floor/unpinned (`>=0.9.0`, `~=`, bare `ruff`) | `assert exact is not None` with a drift-explaining message |
| `[tool.ruff]` or `required-version` absent | `KeyError` from the subscript |
| `repos` absent, no ruff-pre-commit entry, or a malformed rev | `assert revs == [...]` prints the actual list (`[]`, `['v0.16.6']`, …) |
| `.github/workflows/` empty | `assert names` fails instead of passing vacuously |
| malformed YAML | the YAML parser raises |
| `CONTRIBUTING.md` has no `### Code style` section | explicit `assert` with that message |

The only `pytest.skip` in the module stays where it is (`_openspec_config`, for the gitignored
`openspec/config.yaml`); **no new skip is introduced**, so the suite's skipped count cannot move.

### 3.5 Deliberately *not* asserted in pytest — with reasons

| Not asserted | Why |
| --- | --- |
| That `required-version` *fails* a mismatched binary | Requires spawning a second binary from the suite (dependency class AGENTS.md rule 9 keeps out). CI-08 S4 = verify-phase runtime evidence, the CI-01 gate-exit-code precedent |
| That `uv.lock` resolves the same version | `uv.lock` is **derived** state: a `==` dev specifier admits exactly one version and uv re-resolves the lock whenever the declarations disagree, so the lock cannot silently drift into use. A lockfile parser would add a new coupling (no test parses `uv.lock` today) for no added protection. AC5 owns it as verify-phase evidence |
| That the pre-commit hook is installed/active | `.git/hooks/pre-commit` is per-clone and untracked (it does not exist in this clone today); no repository test can observe it |
| That the tests carry no version literal | A test-for-the-test. The property is enforced by construction (extraction) and reviewed in the diff; S3's scenario states it as a requirement |

### 3.6 Non-vacuity evidence (apply-phase, mandatory)

The three-way guard is only useful if each leg can fail. Apply records:

1. **RED first, before any declaration edit**: `uv run pytest tests/test_ci_workflows.py -q` with the
   three tests present and `pyproject.toml:47` still `ruff>=0.9.0` → `_declared_ruff_version()` fails on
   the exactness assertion. This is the guard's teeth on today's defect.
2. **Mutation probe — one leg per declaration** (each mutated, observed RED, then reverted with
   `git checkout --` on that one file):
   - `.pre-commit-config.yaml` `rev: v0.16.7` → `v0.16.6` ⇒ test 1 fails on the rev assertion.
   - `pyproject.toml` `required-version` → `"==0.16.6"` ⇒ test 1 fails on the required assertion.
   - `CONTRIBUTING.md`: version removed from the Code style sentence ⇒ test 3 fails.
3. **Cleanup assertion**: `git status --porcelain` shows only the intended change paths plus SDD
   artifacts — no probe residue. A leftover mutation is a verification failure, not a footnote.

Full command list in §5.4; these three probes are what turn "the guard passes" into "the guard is not
vacuous".

---

## 4. Module-docstring reconciliation decision (ruling 5)

**Current text** (`tests/test_ci_workflows.py:1-11`) says *"requirements CI-01..CI-06"* and *"the 15
mapped rows of the spec Test Mapping table, plus one supporting guard (`test_ci_workflow_files_present`)"*.

**Measured now**: 19 `def test_` functions (`grep -c "^def test_" tests/test_ci_workflows.py` → 19); the
canonical `ci` Test Mapping table holds **22** data rows (`ci/spec.md:296-317`), of which **15** name a
test in this module (`grep "^| CI-0" openspec/specs/ci/spec.md | grep -c "test_ci_workflows.py"` → 15).
The arithmetic closes: 15 mapped + 2 `coverage` COV-06 guards + 1 CodeQL private-window guard + 1
supporting guard = 19. The docstring is stale on the enumeration (CI-07 missing) and names only one of
the four non-`ci` tests.

**Ruling: fix both halves, and add the reconciling clause.** After this change:

- the enumeration becomes **`CI-01..CI-08`** — fixing the pre-existing CI-07 omission, because leaving it
  would make the newly-added CI-08 mention manifestly wrong next to a missing CI-07;
- the row figure becomes **18** (15 + the 3 new pytest-mapped CI-08 rows) and is stated as *"`ci` rows
  whose verification names a test in this module"*, which is what the number actually counts;
- one added sentence names the four remaining tests (the two `coverage` COV-06 guards, the CodeQL
  private-window guard, and `test_ci_workflow_files_present`), so 18 + 4 = 22 = the test-function count.
  Without it, the next reader re-derives a mismatch — the same defect class this change exists to remove;
- the runtime-evidence sentence gains CI-08 S4 alongside CI-01 S2.

**Why not only the count?** A bare `15 → 18` leaves `CI-01..CI-06` contradicting a CI-08-mapped module and
keeps an arithmetic that does not close. Both edits are in the same 11-line docstring, change no
behaviour, and are covered by the module's own review. The blast radius is one docstring; no scenario
asserts these figures (CI-08's scenarios assert declarations, not docstring counts).

**Forward-reference caveat (important for verify).** Apply edits the docstring *before* `sdd-sync` appends
the four delta rows to the canonical table. So immediately after apply, the canonical file alone holds 22
rows and the delta holds 4; the "18 mapped rows" figure is true of **canonical + delta union**, which is
the union the reader will see after sync. Verify must therefore **re-derive, never copy**:

```bash
grep -c "^def test_" tests/test_ci_workflows.py                      # -> 22
grep "^| CI-0" openspec/specs/ci/spec.md \
  openspec/changes/2026-09-15-chore-ruff-single-authority/specs/ci/spec.md \
  | grep -c "test_ci_workflows.py"                                   # -> 18
```

If either number differs, the docstring (or the delta's row set) is wrong — and the fix is the figure,
not the evidence.

---

## 5. Apply-phase probe plan

Ordering matters: §5.1 (lock) must precede §5.2/§5.3, because the S4 and AC3 probes must run against
**0.16.7 in the venv** — the declared value the change creates. §3.6's RED probe must precede the
declaration edits.

### 5.1 `uv.lock` confinement probe (ruling 6) — no flag asserted

**No flag is asserted here** (this phase had no shell; the confinement claim is `explore.md` §4's reading
of `uv.lock`, not a measurement). Apply runs the sequence and records raw output:

```bash
# 0. Baseline — before touching pyproject.toml
git status --porcelain uv.lock                  # -> empty (lock is clean)
uv lock --help | grep -n "upgrade-package\|check\|locked"   # which flags this uv actually has

# 1. Edit pyproject.toml (pin + required-version), then refresh
uv lock
git diff --numstat uv.lock
git diff uv.lock

# 1b. ONLY if step 1 shows churn outside the ruff block / dev specifier:
git checkout -- uv.lock
uv lock --upgrade-package ruff                  # package-scoped refresh (flag NOT verified this phase)
git diff uv.lock

# 2. Consistency check (record the actual flag this uv supports)
uv lock --check ; echo "exit=$?"                # or `uv lock --locked` if --check is unsupported

# 3. Reinstall the pinned binary so later probes run on 0.16.7
uv sync
uv run ruff --version                           # -> ruff 0.16.7
```

**Acceptable diff (accept):**

- lines inside the `ruff` package block (`uv.lock:2032-2055` pre-change): `version = "0.16.0"` →
  `0.16.7`, the `sdist` line, and the wheel list (`:2038-2054`, 17 entries pre-change);
- the single dev-specifier line `uv.lock:2120`: `{ name = "ruff", specifier = ">=0.9.0" }` →
  `{ name = "ruff", specifier = "==0.16.7" }` (this line lives in the `[[package]] name = "sofer"`
  block, so that block is expected to change on **that one line only**);
- `uv lock --check` (or `--locked`) exits 0 after the refresh;
- every `-`/`+` line's context names `ruff`, or is the sofer metadata block's ruff specifier. Verify this
  by reading the hunks, not by trusting the file-level diffstat.

**Unrelated churn (surface, never absorb):**

- any other `[[package]]` entry touched (version/source/sdist/wheels), any package added or removed;
- the lock header (`uv.lock:1-11`: `version`, `revision`, `requires-python`, `resolution-markers`);
- whitespace/ordering churn, or a change to any non-ruff `requires-dev` / `requires-dist` entry.

**On rejection the change stops being a two-file dependency change.** `git checkout -- uv.lock`, record
the observed churn verbatim in apply progress, and escalate to the parent as a scope finding. **Forbidden
workarounds**: hand-editing `uv.lock`; staging a partial lock hunk; absorbing the churn because "it is
only a lock file". If the machine is offline, `uv lock` cannot run: report AC5 as **blocked**, do not
claim the change complete.

### 5.2 Hook materialisation + AC3 parity probe (D3)

AC3 needs two separately installed binaries to agree on **the same file content**. Sequence:

```bash
# 1. Pre-state
git status --porcelain            # clean apart from SDD artifacts
pre-commit install                # writes the untracked .git/hooks/pre-commit
ls .git/hooks/pre-commit

# 2. Write the probe file ONCE; it is the immutable content both surfaces judge
#    (root-level, untracked, deliberately misformatted but valid Python):
#      def probe( x,y ):
#          return    x+y

# 3. Surface A — the environment's binary, check-only (does not mutate)
uv run ruff format --check _ruff_parity_probe.py ; echo "exit=$?"

# 4. Surface B — the hook's binary (0.16.7 from the per-rev venv). It REWRITES the file on failure.
pre-commit run ruff-format --files _ruff_parity_probe.py ; echo "exit=$?"

# 5. Prove the hook's binary is 0.16.7 by its own mechanism, not by its output text
grep -n "ruff==" ~/.cache/pre-commit/*/pyproject.toml

# 6. Cleanup + no-residue check
rm _ruff_parity_probe.py
git status --porcelain
```

| Step | Expected (record the actual) |
| --- | --- |
| 3 | exit 1, `1 file would be reformatted` — the environment's 0.16.7 |
| 4 | exit 1, `1 file would be reformatted` — the hook's 0.16.7 ⇒ **same verdict on the same bytes** = AC3 |
| 5 | a cache clone whose `pyproject.toml` pins `ruff==0.16.7` (explore found the newest cached rev was 0.16.6, so a **new** clone is itself evidence the tag materialised) |
| 6 | no tracked file changed; the probe file is gone |

Notes: (a) run surface A **before** surface B, because the hook rewrites the file; (b) additionally paste
`pre-commit run ruff-format --all-files` as the whole-tree leg — it must report no reformat, which is the
same-tree confirmation that the two versions agree on this tree (both `--check` runs already reported
`68 files already formatted` per D1); (c) **if any tracked file changes** during the `--all-files` run,
0.16.7 differs from 0.16.0 on this tree, the D1 measurement is falsified for that path, and the run stops:
`git checkout --` over the affected paths, surface as a finding, do not absorb; (d) the hook being installed is a
per-clone untracked side effect — leave it installed (the intended contributor state) and record that
rollback is `pre-commit uninstall`; (e) if the `v0.16.7` tag cannot be fetched, that is the AC3/upstream
finding to escalate — never a silent `language: system` workaround.

### 5.3 CI-08 S4 probe — `required-version` rejects a mismatched binary

Three legs, all on the refreshed environment (`uv run ruff --version` → 0.16.7):

```bash
# Leg A — the declared value passes
uv run ruff check src/ tests/ scripts/ ; echo "exit=$?"
uv run ruff format --check src/ tests/ scripts/ ; echo "exit=$?"     # -> 68 files already formatted

# Leg B — a mismatch probe (temp dir OUTSIDE the repo; the tracked pyproject.toml is never edited)
#   %TEMP%/ruff-probe/ruff.toml :  required-version = "==99.0.0"
uv run ruff check --config "$TEMP/ruff-probe/ruff.toml" src/ tests/ scripts/ ; echo "exit=$?"
uv run ruff format --check --config "$TEMP/ruff-probe/ruff.toml" src/ tests/ scripts/ ; echo "exit=$?"
```

| Leg | Expected | Non-vacuity |
| --- | --- | --- |
| A | exit 0 on both subcommands | the declared value is satisfiable |
| B | **non-zero** on both (record the actual code; do **not** assert 2), message naming both the required and the running version | the message text proves the failure is `required-version`, not a parse error — the same control the orchestrator used when it rejected an invented key |

`--config` replaces config discovery entirely, which is why the tracked `pyproject.toml` need not be
touched; the probe file is a `ruff.toml`-shaped file holding only `required-version`, so the repo's own
`[tool.ruff]` settings are intentionally out of scope for leg B (it fails at config load, before linting).
**Unverified**: whether this uv's `--config` accepts an out-of-tree path and whether 0.16.7 accepts the
identical key — the probe records what happens; if `--config` is rejected, apply falls back to the
orchestrator's measured shape (a temp dir with `pyproject.toml` holding `[tool.ruff] required-version`)
and records the substitution.

### 5.4 Full apply-phase command block (order)

```bash
# Phase 1 — baseline + RED
git status --porcelain
uv run pytest tests/ -q                       # baseline tally (re-derive, never copy AGENTS.md)
# write the 3 guard tests -> RED on today's `ruff>=0.9.0`
uv run pytest tests/test_ci_workflows.py -q

# Phase 2 — declarations, then lock (probe §5.1)
# edit pyproject.toml:47 and [tool.ruff]; refresh + confine the lock; uv sync

# Phase 3 — guard teeth (mutation probe §3.6), each reverted immediately
# Phase 4 — runtime evidence: §5.2 (hook/AC3, S4 legs A+B), §5.3, criterion 4 greps
# Phase 5 — docs + docstring: CONTRIBUTING.md:77 (§2.6), module docstring (§4),
#           delta wording fix (§1.5)

# Phase 6 — final gates
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/     # -> 68 files already formatted
uv run mypy src/ scripts/
uv run pytest tests/ -q                             # baseline + 3 passed, 0 failed, 0 newly skipped
git status --porcelain                              # intended paths + SDD artifacts only
```

---

## 6. Verification strategy

Evidence classes per the repo's own convention (`ci/spec.md:285-287`): static workflow/config assertions
are pytest; gate exit codes are pasted verify-phase runtime evidence. **No new pytest file** and no
harness is introduced.

| Success criterion | Evidence |
| --- | --- |
| 1 — one authoritative version, guard red if any declaration moves alone | `uv run pytest tests/test_ci_workflows.py -q` → 22 passed; §3.6's three-leg mutation probe output |
| 2 — `required-version` fails a mismatched binary, passes the real one | §5.3 legs A + B, exit codes and both messages pasted |
| 3 — AC3: `uv run ruff format --check` and the `ruff-format` hook agree | §5.2 steps 3 + 4 output verbatim, plus the cache-clone `ruff==0.16.7` line |
| 4 — zero reformats, **no** CI format gate | `uv run ruff format --check src/ tests/ scripts/` → `68 files already formatted`; `grep -rn "format" .github/workflows/` → 0 matches (before and after); `git diff --stat` contains no `.github/workflows/` path |
| 5 — suite + enforced commands green | `uv run pytest tests/ -q` (baseline re-derived first: +3 passed, 0 failed, 0 newly skipped); `uv run ruff check src/ tests/ scripts/`; `uv run mypy src/ scripts/` (the CI/pre-commit scope; AC4's narrower `mypy src/` wording stays #212). `.python-version` = `3.13`, so no `--python` flag is needed (AGENTS.md rule 12) |
| 6 — `uv.lock` refreshed in the same change, confined | §5.1's `git diff` / `git diff --numstat` and the `uv lock --check` (or `--locked`) exit code |
| 7 — PB-10 corrected, no normative version literal left | `diff` the delta's MODIFIED PB-10 block against the canonical block → exactly one replaced sentence plus the `(Previously: …)` insertion, five scenarios byte-identical. Normative-text check: awk the delta's PB-10 block up to the `(Previously:` line into a temp file, then count version literals in it — expected **0** (`grep -cE "0\.16\.[0-9]"`). The historical `(Previously: …)` note is the only occurrence anywhere and is exempt by convention (§1.6) |
| 8 — no `src/sofer/**` in the diff | `git diff --name-only` → exactly the intended paths (`pyproject.toml`, `uv.lock`, `CONTRIBUTING.md`, `tests/test_ci_workflows.py`, the two change-root deltas) + SDD artifacts |
| PB-10 live clauses still hold | `grep -rn "format --check" .github/workflows/` → 0 (the `:281-286` scenario); delta PB-10 carries the "no new CI step" clause and the #194-ownership sentence verbatim |
| CI-08 S1–S3 mapped 1:1 | the three test names present, one per scenario, in `tests/test_ci_workflows.py`; §4's two re-derivation greps |

**Verify must not do these** (they would produce false failures): re-run PB-10's *"exactly the six test
files"* / *"formatting-only"* scenarios against this change's diff (§1.6, rule 1); grep `0.16` over a
whole spec file and call the `(Previously: …)` note a violation (§1.6, criterion 7); edit canonical specs
(that is `sdd-sync`).

---

## 7. Review-workload forecast input for the tasks phase

| Item | Estimate (changed lines, add+del) |
| --- | --- |
| `pyproject.toml` | 4–5 |
| `uv.lock` | ≈40 (36–46, **unverified** until §5.1 runs) |
| `tests/test_ci_workflows.py` (helper + constants + 3 tests + docstring) | ≈78 (65–85) |
| `CONTRIBUTING.md:77` | 2 |
| `.pre-commit-config.yaml` | 0 |
| **Functional subtotal** | **≈124 (≈110–140)** |
| Spec-delta content in the change root (`ci` CI-08 + 4 rows + §1.5 wording fix ≈50; `process-boundary` PB-10 ≈10) | ≈60 |
| **Load under the repo's own rule** (`archive/2026-09-14-chore-ruff-format-drift/tasks.md:23`: *"`proposal.md` / `spec.md` / `design.md` / this file are SDD artifacts, not review load"*) | **≈184** |

**Does it exceed 400? No.** ≈184 changed lines of functional + spec-delta load is well inside the
400-line canonical threshold, so this is **a single PR, no chained slices, no `size:exception`**. The SDD
artifacts under the change root (proposal/spec/design/tasks/apply-progress/verify-report, ≈700 lines of
prose) do not count as review load by the repo's own precedent. If the parent ever counts them, the only
sensible split remains one that keeps the guard tests with the CI-08 scenarios they satisfy (AGENTS.md
rule 6) — never split apart.

**Observed preflight discrepancy (recorded, not re-opened).** The session preflight block in this phase's
context states a 1500-line review budget while also noting 400 as canonical; the parent's ruling for this
change is 400 with SDD artifacts excluded. The estimate passes under **both** readings, so the tasks phase
should record `400-line budget risk: Low` and proceed as a single PR without asking. Flagging it here
because the earlier phase's arithmetic was challenged, and the tasks file is where that number is
consumed.

**Suggested work units for `tasks.md`** (one PR, reviewable in order):

| Unit | Contents | Rollback |
| --- | --- | --- |
| 1 | Guard tests (RED first) — §3, §3.6 | revert the test file |
| 2 | Declarations + lock — §2.3, §2.4, §5.1 | revert `pyproject.toml` + `uv.lock` together, never one alone |
| 3 | Runtime evidence — §5.2, §5.3, criterion 4 greps | no source rollback; the hook is removable with `pre-commit uninstall` |
| 4 | Docs + SDD text — §2.6, §4, §1.5 | revert `CONTRIBUTING.md`, the test docstring, the `ci` delta |
| 5 | Final gates + verify-report inputs — §5.4 phase 6 | whole-change `git revert` |

---

## 8. Risks, with evidence

| Risk | Evidence / likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| **Upstream tag `v0.16.7` does not exist**, so every hooked commit fails | **Unverified** — no network and no local materialisation this phase; the pre-commit cache's newest ruff-pre-commit clone pins `ruff==0.16.6` and a whole-cache grep for `0.16.7` finds nothing (`explore.md` §2.3) | Blocks AC3 and breaks `git commit` for anyone with hooks installed | §5.2 step 4 materialises the tag **before** the change is called complete, and step 5 proves the hook's bundled pin. A failure is escalated, never worked around |
| **The hook has never run in this clone**, so AC3 has no inherited evidence | `.git/hooks/pre-commit` ENOENT; the issue's premise that the hook "already validated staged files" is unevidenced (`explore.md` §2.3) | AC3 could be claimed without evidence | `pre-commit install` is a named, required apply step; both verdicts are pasted |
| **`uv.lock` refresh drags in unrelated churn** | Low–Med; the exact flag is **unverified** this phase (no shell) | Inflates the diff, moves other dependencies silently | §5.1's probe and accept/reject rules; unrelated churn is surfaced and escalated, never absorbed |
| **`uv lock` needs the network** | Certain | AC5 cannot be evidenced offline | Record AC5 as blocked and do not claim completion; do not hand-edit the lock |
| **A reformat appears anyway** (0.16.7 differs from 0.16.0 on this tree) | Low — both versions returned `68 files already formatted` on this tree (D1, measured by the orchestrator) | Would reach `src/sofer/`, including the four rule-14 modules | §5.2(c): any tracked change during the `--all-files` run stops the probe, is reverted, and is surfaced as a scope change — never absorbed |
| **`required-version` raises the bar for every contributor** | Certain by design (D2, maintainer-accepted) | Any editor integration, global install or `uvx ruff` at another version fails at config load | The measured message names both versions; `CONTRIBUTING.md:77` now names the expected version; loud failure replaces silent disagreement. Recorded as an accepted cost |
| **PB-10 over-edited** — a "restatement" that rewrites clauses or scenarios | Medium: the requirement is one long paragraph and this change also relies on its scenarios' framing | Weakens a shipped requirement | Ruling 3 ratifies the delta text unchanged; verify diffs the blocks and expects exactly one changed sentence; §1.6 forbids re-running S2/S3 against this diff |
| **PB-10's forward reference to CI-08 dangles between two sync writes** | Low: both deltas are in this change | A reader sees a requirement pointing at nothing | §1.6 sync-ordering rule + the verify check that `CI-08` exists in canonical `ci` whenever the restatement is present |
| **The `CONTRIBUTING.md:77` edit collides with #187** | Medium — same sentence, different defect | Rebase conflict or silently merged concerns | §2.6: first sentence only; re-read line 77 before applying; `git diff --word-diff` must show one token; the `ruff.toml` sentence must not appear in the diff |
| **`PKG-06` cited as the lock owner (the gatekeeper's finding)** | Confirmed: `packaging/spec.md:132-134` scopes its regeneration clause to the `fastmcp` declaration; its two scenarios assert no lock | A future reader finds no obligation for a ruff pin move | Ruling 2: CI-08 owns it; the two-part wording fix is specified verbatim (§1.5) and AC5's verification cites CI-08 |
| **The guard tests are vacuous** (pass under a floor, a wrong rev, or a different version in a workflow) | The three-legged equality is the guard's entire value | A silent re-drift, i.e. the original defect returns | §3.6: RED before the edit plus a per-leg mutation probe with reversion proof |
| **The docstring figures drift again** (15 → 18 → ?) | Certain if the edit only swaps numbers: the current text already mis-counts (19 tests vs "15 mapped + one guard") | Reviewers re-derive and distrust the module | §4: enumeration + count + the reconciling clause, and two re-derivation commands named for verify (never a copied figure) |
| **`ci` `## Purpose` (`:5-11`) stays enumerating CI-01..CI-06** | Verified this phase; CI-07 already stale | A reader of the `ci` purpose line does not see CI-08 | Accepted and named (§1.6): the omission is pre-existing, fixing it would edit canonical prose for CI-07's defect, and the change records it in the PR body |
| **`AGENTS.md` rule 6's tally literal / `openspec/project.md:82` "ruff 0.16.0"** | Both are other owners' (#184/#187/#214); `openspec/config.yaml:7` also claims `ruff 0.16.0` and is gitignored (`.gitignore` `/openspec/config.yaml`) | Stale version prose survives the change | Explicitly out of scope; verify re-derives the tally from `uv run pytest tests/ -q` and does **not** copy `AGENTS.md` |

---

## 9. Explicit non-goals

1. **No CI format gate.** PB-10 keeps enforcement on the local `ruff-format` hook and assigns recurrence
   to #194; this change arms no `format --check` step, adds no workflow file, and adds no workflow step.
   The `:281-286` scenario (zero `format --check` invocations under `.github/workflows/**`) keeps passing
   — verified today: `grep "format" .github/workflows/` → 0 matches.
2. **No edit to canonical specs** (`openspec/specs/**`). Canonical sync is `sdd-sync`'s job; the deltas
   stay in the change root.
3. **No #187 work** — `CONTRIBUTING.md:77`'s nonexistent `ruff.toml` path stays exactly as it is.
4. **No #212 work** — `CONTRIBUTING.md:22-31`'s narrower documented commands are not edited; AC4 runs the
   enforced commands instead.
5. **No #194 work, no `size:exception`, no tag movement, no release action, no publish.**
6. **No other version claim** — `openspec/project.md:82`, `AGENTS.md`, and `openspec/config.yaml:7`
   version statements belong to the documentation wave (#184/#187/#214). `openspec/config.yaml` is
   gitignored local state and is **not** absorbed here, including under change #210's decision that the
   file becomes committed — that is a different change.
7. **No `src/sofer/**` edit.** Both ruff versions returned `68 files already formatted`, so no reformat is
   expected; if one appears it is a scope change to surface, with the four rule-14 modules
   (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) and their 100.00% per-file gates explicitly at risk.
8. **No new pytest file, no test for the lockfile, no test for hook activation, no test that asserts the
   guards carry no literal** (§3.5), and **no extra scenario** for the lock duty (§1.5).
9. **No historical-prose edits** — `openspec/changes/archive/**` (including the #177/#178 records that
   name the mismatch) is a record, not state.
10. **No advisory-directory change**: `openspec/project.md:82`'s tracked version statement and
    `AGENTS.md` rule 6's tally literal remain untouched; verify re-derives figures instead of editing them.
