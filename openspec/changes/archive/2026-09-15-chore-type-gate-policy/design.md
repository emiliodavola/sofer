# Design — `2026-09-15-chore-type-gate-policy`

> **Change** `2026-09-15-chore-type-gate-policy` · issue **#201** · branch `chore/201-type-gate-policy`
> · store **hybrid** (this file + Engram `sdd/2026-09-15-chore-type-gate-policy/design`).
>
> **Phase:** design. Inputs read directly: `proposal.md` (cited as **P §n**), `evidence-type-gate-baseline.md`
> (cited as **BL §n**, **§7 supersedes §2**), `explore.md` (cited as **EX §n**) — plus, for splice precision
> only, the live tree files this change edits (§2 records every anchor and every observed divergence).
>
> **Status:** design complete — this document is the apply blueprint. Every value below is frozen: apply
> copies it. Where the tree disagrees with BL/EX, §2 records the divergence and the design freezes the tree
> reading; where the proposal left a choice open, this document decides it and says why.
>
> **Revision 2 (post-§8 re-measurement) — authoritative.** The tree changed after revision 1. Input for this
> revision: **BL §8** (mypy still 6 errors with a *changed composition*; pyright still 13; suite
> `1785 passed, 6 skipped`; the maintainer's three decisions in §8.5; the required amendments in §8.6).
> Four amendments, applied throughout and logged as **COR-1…COR-4** in §2:
>
> - **A1** — `mypy_path = "typings"` is **dropped**: DC-2's premise was wrong (`ignore_missing_imports =
>   true`, and mypy's 6-error set contains no `tomli` diagnostic). The stub is a **pyright-only** artifact.
> - **A2** — the `metadata.py:239` resolution is **retired** (`types-pyyaml` resolved it); the resolution
>   table is renumbered to **17 sites** (§5) with BL tracing.
> - **A3** — `_converters.py:611/620` is **dual-gate**; its frozen fix is a `Sequence[object]` container
>   type, and the revision-1 `vals` annotation is explicitly **not** the fix (§5.1 site 6, DC-10).
> - **A4** — CI-07's `[tool.mypy] python_version` clause is **amended inside this change** — an authorized,
>   recorded exception to the earlier CI-01..CI-08 non-goal (§6.6, DC-11), guarded by new guard **G7**.
>
> Everything else from revision 1 stands: D1–D13, the `[tool.pyright]` block, the stub, G1–G6, CI-09, the
> verify plan skeleton and the rollback story. The maintainer's dependency/config edits (BL §8.5 #2–#3) are
> inputs: `datasets>=5.0.1`, `numpy<2.3`, the `[[tool.mypy.overrides]]` block and the regenerated `uv.lock`
> stay in this PR and are touched by no step of apply.
>
> **Nothing here re-opens D1–D13, Q1 (a) or Q2 (c).** The maintainer's two closed answers (hook-inclusive
> YES, README bullet YES) are inputs.

---

## 1. What this design freezes

| # | Frozen artifact | Section |
| --- | --- | --- |
| 1 | The `[tool.pyright]` block, key by key, with the venv decision (§7.1) | §3 |
| 2 | The `tomli` stub: path, exact content, isolation proof, layout fallbacks | §4 |
| 3 | The resolution table at diff precision — **17 apply sites** after COR-2's retirement and COR-3's dual-gate re-classification (BL §7.3 renumbered per BL §8.1/§8.3) | §5 |
| 4 | The CI-09 delta text + insertion/append anchors, **and the CI-07 clause amendment (DC-11)** | §6, §6.6 |
| 5 | The documentation edits, verbatim | §7 |
| 6 | Guards G1–G6, assertions, staleness argument, red-then-green plan | §8 |
| 7 | Verify plan SC-1…SC-8 + red-first probe + `tests/`-untouched proof + rule-14 row re-run | §9 |
| 8 | Rollback story, workload forecast, PR boundary | §10 |
| 9 | Dispositions of EX §9 O1…O12, the design's own additions (DC-1…DC-9), risks | §11, §12 |

Design-level decisions this document adds (numbered **DC-n** so they never collide with P §4's D1–D13):

| ID | Decision | Reason |
| --- | --- | --- |
| **DC-1** | `venvPath = "."` + `venv = ".venv"` are **declared** in `[tool.pyright]` | §7.1 of the evidence shows the first pinned run reported 29 phantom missing-import errors because pyright honoured an inherited `VIRTUAL_ENV` from `uvx`. Declaring the venv makes that failure mode structurally impossible instead of depending on how the process was launched |
| **DC-2 — RETRACTED (A1, COR-1)** | The `tomli` stub is consumed by **pyright only** (`stubPath = "typings"`); **`mypy_path = "typings"` is dropped** | Revision 1's premise was wrong: the tree declares `ignore_missing_imports = true` (BL §8) and BL §8.1's measured 6-error set contains **no** `tomli` diagnostic, so mypy needs no declaration at all. The stub still exists for the pyright gate. The retraction is **logged** (COR-1, §2), never silently deleted |
| **DC-3** | `[tool.hatch.build.targets.sdist] exclude = ["/typings"]` | The stub is a type-checker artifact, never a distribution artifact. The wheel never sees it (hatchling's src-layout selection builds `src/sofer`), and this one line keeps it out of the sdist as well, so §4's isolation claim holds for **both** artifacts by construction |
| **DC-4** | `_mirror.py:77`'s parameter is annotated `entry: FileEntry`, **not** `entry: str` | BL §6 row 1 says "call sites pass remote strings"; the tree contradicts it (see §2, OBS-2). `entry` is iterated from `cfg.files` (`_mirror.py:113`) and the body reads `entry.recursive` / `entry.remote`, so `str` would produce a **new** `attr-defined` error. The BL row is corrected, not followed |
| **DC-5** | The red-first guard set is **{G1, G3, G4}** plus **G7** (red until `sdd-sync` applies the CI-07 amendment); **G2, G5, G6** are tripwires green in both states | G2 asserts the absence of a file that does not exist today, G5 asserts a pin whose pre-step already landed, G6 asserts the status quo. Fabricating a red state for them would mean temporarily deleting committed config — dishonest evidence. P SC-7 ("all six red before") is corrected here; G7's redness is **real** and is the sync obligation made testable (A4) |
| **DC-6** | The PR-template item is asserted **inside G4**, not in a seventh test | G4 is already the "every documented surface states the posture" guard (AC1 + AC3); folding the CI-06-S4-shaped checklist assertion there keeps the guard count at six, as P §9 permits ("folded into G6's file read if the design prefers one fewer test") |
| **DC-7** | The red-first probe file is `src/sofer/_type_gate_probe.py`, deleted in the same step | P SC-3 says "inside `src/`". `src/` is coverage-measured but only over **executed** files (`[tool.coverage.run] source = ["src/sofer"]`), and the probe is deleted before the suite re-run, so the rule-14 rows cannot be touched by it |
| **DC-8** | The stub layout is `typings/tomli-stubs/__init__.pyi` (PEP 561 stub-package form) with a **two-step ordered fallback** | Matches D5 and BL §6.4. Fallback 1: mirror layout `typings/tomli/__init__.pyi`; fallback 2 (R3): five per-line `# pyright: ignore[reportMissingImports]` at the five import sites. Both fallbacks are comment/file-shape-only and cannot touch coverage |
| **DC-9** | `reportMissingImports = "error"` is declared **explicitly** in `[tool.pyright]` | D2 says "any rule we want to bind SHALL be declared at `error` severity". Declaring it makes the binding visible and guard-able (G1); the value equals the `standard`-mode default, so it changes no diagnostic |
| **DC-10** (A3) | The list-invariance site is fixed by **one** edit — `raw_rows: list[Sequence[object]]` at `_converters.py:611` — and `:614` stays **unannotated** | BL §8.1's mypy note names the only fix that satisfies both checkers: mypy says *"Perhaps you need `Sequence` instead of `list`"*. `list[bool \| float \| … \| None]` is a `Sequence[object]` by covariance but **not** a `list[object]` by invariance, so revision 1's `vals: list[object]` **relocates** the diagnostic (`[assignment]` / `reportAssignmentType` at `:614`) instead of clearing it — proven by SC-4c-i |
| **DC-11** (A4) | CI-07's clause "`[tool.mypy] python_version` SHALL remain `"3.10"`" and its restatement in CI-07's "User-facing support is unchanged" scenario **are amended inside this change** — the single authorized exception to the CI-01..CI-08 non-goal | The maintainer decided `python_version = "3.11"` stays (BL §8.5 #1), so the clause is stale; leaving it would ship a false requirement — the very failure mode this change removes. Frozen wording in §6.6, enforced by G7. `.python-version` = `3.13`, `requires-python`, the test matrix, the floor and every other CI-07 byte are untouched |

---

## 2. Anchor reconciliation — every divergence between the tree and the evidence

The design was written against the **tree**, not against the baseline's line references. Divergences found
while splicing are recorded here rather than silently harmonised.

| ID | Observation | Impact | Disposition (frozen) |
| --- | --- | --- | --- |
| **OBS-1 — RESOLVED by A1 (was COR-1's trigger)** | Revision 1 read the tree as `ignore_missing_imports = false` with `python_version = "3.11"` and inferred five mypy `tomli` diagnostics. The maintainer's later edit completed the block as `ignore_missing_imports = true` (BL §8), and BL §8.1's measured 6-error set contains **no** `tomli` diagnostic | Revision 1's **DC-2** (`mypy_path = "typings"`) is retracted; `[tool.mypy]` gains **zero** lines from this change | See **COR-1**. The stub remains a **pyright-only** artifact; §3 and §4 are amended accordingly |
| **OBS-2** | `_mirror.py:77`'s parameter is a `FileEntry`, not a string; BL §6 row 1 proposes `entry: str` | BL §6's row would not compile cleanly (`entry.recursive` on a `str`) | **DC-4**: annotate `entry: FileEntry` via the module's existing `if TYPE_CHECKING:` block (`_mirror.py:24-25` already imports `DatasetConfig` there) |
| **OBS-3** | `verification.py`'s three `reportArgumentType` errors come from **one** binding at `:97` (`actual_splits = list(ds.keys())`), consumed at `:101`, `:103`, `:116`. BL §7.3 lists the resolution sites as `:101`, `:103`, `:116` | The fix is a one-line coercion at `:97`; the three sites need no edit | §5 sites 15-17 fixes the binding site only |
| **OBS-4** | `datasets>=5.0.1` is in `[project] dependencies` (a **direct runtime** dependency now — BL §8.5 #3), `numpy<2.3` was added, and `pyright` 1.1.414 is installed in `.venv` with `nodeenv` and `typing-extensions` as declared dependencies (`uv.lock:2634-2639`) | Explains BL §7.2/§8.2 (pyright resolves `datasets`, so `verification.py` reports **structural** call-site errors, never a missing import) and answers **O4**: the PyPI wrapper provisions Node through its own hard `nodeenv` dependency — there is no Node *extra* to opt into. Because the errors are structural, `verification.py`'s optional-dependency `try: import datasets / except ImportError:` guard is now practically unreachable in a synced environment — and must be **preserved byte-identical** (it stays mockable: `tests/test_splits.py` patches `sys.modules`) | No design change to the resolution (§5.2 sites 15-17 stay a `str` coercion on the success path). Recorded so nobody re-opens "make datasets optional" here, and so R4 is stated accurately |
| **OBS-7** | The maintainer also added `[[tool.mypy.overrides]]` for `pyarrow`/`pyarrow.*`/`datasets`/`datasets.*` with `ignore_missing_imports = true` (BL §8.5 #2), and mypy resolves to 2.3.0 | The overrides block is a **no-op today** because the global `ignore_missing_imports = true` already covers those modules | **Input, untouched.** No site in §5 depends on it; G6's assertions are about the two mypy *invocations*, not the config block, so the block's presence changes no guard. This change neither adds nor removes an override |
| **OBS-5** | Canonical `openspec/specs/ci/spec.md`: CI-08's last scenario, then its closing `---`, then `## Test Mapping` (headings by content; the file's line numbers drift between reads and are not used as anchors) | P §8's `:380-393` are informative, not binding | §6 anchors the CI-09 insertion **by content**: the `---` that follows CI-08's last scenario and precedes `## Test Mapping`; rows appended after the table's last row (the CI-08 `required-version rejects a mismatched binary` row) |
| **OBS-6 — RESOLVED by A4** | CI-07's canonical text asserts `[tool.mypy] python_version` SHALL remain `"3.10"`, while the tree declares `"3.11"` — and the maintainer decided the `"3.11"` value **stays** (BL §8.5 #1) | Revision 1 declared this out of scope because P §2 forbade editing CI-01..CI-08 | **The prohibition is lifted for exactly one clause, by maintainer decision** (DC-11): §6.6 freezes the replacement wording, the `(Previously: …)` marker and the scope of the edit; **G7** makes the clause/config agreement testable. The `.python-version` pin and every other CI-07 clause stay byte-identical — see also **R12** for the one residual tension (CI-07's diff-scope clause) |

### 2.1 Corrections applied by revision 2 (recorded, never silently deleted)

| ID | Revision-1 claim | What the tree/evidence actually says | Correction |
| --- | --- | --- | --- |
| **COR-1** | "The tree declares `ignore_missing_imports = false`, so mypy needs the stub too → add `mypy_path = "typings"`" (DC-2) | `[tool.mypy] ignore_missing_imports = true` (BL §8), and BL §8.1's 6-error set contains **zero** `tomli` diagnostics | **`mypy_path` is dropped.** `[tool.mypy]` gains zero lines; the stub is pyright-only (§3, §4.1). The premise, not the reasoning, was wrong — had the premise held, DC-2 would still have been the right call |
| **COR-2** | "mypy half = 6 sites including `metadata.py:239`" | `types-pyyaml` (dev dep) resolves `yaml.safe_dump`, so `no-any-return` at `metadata.py:239` is **gone** (BL §8.1 REMOVED) | Site retired (no edit); the table is renumbered to 17 apply sites (§5) |
| **COR-3** | "`_converters.py:620` is pyright-only; annotate the binding at `:614`" (BL §7.3 #7, D8) | With `python_version = "3.11"` + `types-openpyxl`, mypy reports the **same** site (`arg-type`, list invariance); and the `vals` annotation does not clear pyright's diagnostic either — it relocates both to `:614` (BL §8.1/§8.6) | Site is **dual-gate**; frozen fix is `raw_rows: list[Sequence[object]]` at `:611` with `:614` unannotated (DC-10, §5.1 site 6) |
| **COR-4** | "CI-07 is cross-referenced, never edited" (P §2's non-goal) | The maintainer decided `python_version = "3.11"` stays (BL §8.5 #1), so CI-07's clause is false on the tree | **Authorized exception** for that one clause (+ its own restatement): §6.6 freezes the wording, DC-11 records the reason, G7 enforces the agreement, and §14's non-goal is restated with the carve-out |

---

## 3. The `[tool.pyright]` block (frozen)

Inserted in `pyproject.toml` **immediately after the `[tool.mypy]` block** (`pyproject.toml:79-85`) and before
the `# ── pytest ──` separator, so both type-checker declarations sit in one file (D4).

```toml
# ── pyright: second type checker (real gate) ─────────────────────────────
# Not advisory: `uv run pyright` is a gate in the CI `lint` job and in the
# pre-commit hooks. `standard` is the strongest mode reachable without a cleanup
# campaign — `basic` would silently drop the one real defect it found
# (`_converters.py:650`), and `strict` is a 578-error campaign, not a policy
# change. `pythonVersion` mirrors the gate interpreter (`.python-version`, 3.13)
# because pyright analyses the runtime environment it runs in: there the
# `tomllib` arm is the live one and the `tomli` fallback arm is the stale one the
# stub below targets. The scope is the enforced mypy scope; `tests/` is excluded
# from BOTH type gates by policy (openspec/specs/ci/spec.md CI-09). `venvPath`/
# `venv` are declared so import resolution can never depend on an inherited
# VIRTUAL_ENV. Invoke it as `uv run pyright` — never bare, never `uvx`.
[tool.pyright]
typeCheckingMode = "standard"
pythonVersion = "3.13"
venvPath = "."
venv = ".venv"
include = ["src", "scripts"]
exclude = ["tests", ".venv", "**/node_modules", "**/__pycache__"]
stubPath = "typings"
reportMissingImports = "error"
```

Key by key:

| Key | Value | Why exactly this value | Rejected alternative |
| --- | --- | --- | --- |
| `typeCheckingMode` | `"standard"` | D1: costs exactly one error more than `basic`, and that one error (`_converters.py:650`) is the only real defect either mode finds. BL §7 re-measured it with the pin: 13 errors / 0 warnings | `basic` — would drop the only genuine finding; `strict` — 578 errors (EX §5.1), an explicit non-goal |
| `pythonVersion` | `"3.13"` | D11 + BL §7: the gate interpreter, where `tomllib` is the live stdlib arm; mirroring mypy's *minimum* would flip the five `tomli` errors into five `tomllib` errors and demand a stdlib stub | `"3.10"`/`"3.11"` (mypy's keys) — models an interpreter the gate never runs on |
| `include` | `["src", "scripts"]` | D3: identical to the **enforced** mypy scope (`ci.yml:21`, `.pre-commit-config.yaml:22`); `scripts/` measured 0 errors in every mode (BL §2, §7) | `["src"]` — leaves `scripts/` unchecked while mypy checks it, a silent asymmetry |
| `exclude` | `["tests", ".venv", "**/node_modules", "**/__pycache__"]` | `tests` is Q1's policy exclusion and the G1/G4-asserted key; the rest is hygiene matching `[tool.mypy] exclude`'s `.venv/` spirit | `exclude = ["tests"]` only — leaves venv/node_modules/`__pycache__` eligible if `include` is ever widened |
| `stubPath` | `"typings"` | D5 + DC-8: one committed stub serves the five `tomli` sites; `typings` is pyright's own default location, declared explicitly so the layout is a repository decision, not a tool default | Five per-line ignores — documented fallback (DC-8), not the plan; adding `tomli` to dev — **forbidden** (BL §4.1: it breaks the `cli.py` COV-06 row) |
| `reportMissingImports` | `"error"` | D2 + DC-9: the binding is declared, not inherited; equals the `standard`-mode default so it adds no diagnostic | Omitted — then the "never globally disabled" clause would be true but invisible |
| `venvPath` | `"."` | **DC-1**: `.venv` sits at the repo root next to `pyproject.toml`, which is also the config file's directory, so the declaration is stable under `uv run` and under CI | Omitted — leaves resolution to an inherited `VIRTUAL_ENV` (the §7.1 29-error artifact) |

**The venv question (§7.1) — decided: declare it.** BL §7.1 records that `uvx pyright@1.1.414 src/` reported
29 errors because pyright honoured an ephemeral `VIRTUAL_ENV` containing only pyright. Declaring
`venvPath`/`venv` makes the resolution a config fact: the gate resolves third-party imports against
`<repo>/.venv` regardless of what the invoking process had exported. The residual obligation is documented,
not assumed: the gate is invoked as `uv run pyright` (which is what creates/uses `.venv`), and that
requirement is stated in `CONTRIBUTING.md` §Type checking (§7.1) and in CI-09 S2.

`[tool.mypy]` gains **zero lines** from this change (A1/COR-1). The maintainer's committed block is an
**input**, not a design target: `python_version = "3.11"`, `strict = true`, `check_untyped_defs = true`,
`ignore_missing_imports = true`, `warn_unused_ignores = true`, `exclude = ["tests/", ".venv/"]`, plus the
`[[tool.mypy.overrides]]` block for `pyarrow`/`pyarrow.*`/`datasets`/`datasets.*` (BL §8.5 #2 — a no-op while
the global `ignore_missing_imports = true` holds; kept as the maintainer asked). Apply touches none of it.
Two consequences are frozen here so no later step "fixes" them:

1. The five `tomli` sites need **no** declaration for mypy (the global key covers them) — the only consumer
   of the stub is the pyright gate (`stubPath`, §4). No `mypy_path`.
2. The block makes `_converters.py:611/620` a **mypy** site as well as a pyright one (§5.1 site 6, DC-10),
   which is the one resolution this revision's COR-3 changes.

and `[tool.hatch.build.targets.sdist]` gains its isolation exclusion (DC-3):

```toml
[tool.hatch.build.targets.sdist]
# `typings/` is a type-checker artifact: it must never ship in a distribution.
# The wheel already excludes it (hatchling's src-layout selection builds
# src/sofer); this keeps the sdist to the same rule.
exclude = ["/typings"]
```

`[tool.pyright]` is a **table inside `pyproject.toml`**, and D4's single-authority property is guarded by G2
(§8): pyright silently prefers a `pyrightconfig.json` over `[tool.pyright]`, so a stray JSON file would
re-open the drift class CI-08 closed.

---

## 4. The `tomli` stub (frozen)

### 4.1 Path and content

`typings/tomli-stubs/__init__.pyi` (new file, PEP 561 stub-package layout — DC-8):

```python
"""Stub for the marker-only ``tomli`` backport (``tomli>=2.0; python_version < '3.11'``).

``tomli`` is absent from the 3.13 gate interpreter *by design* (AGENTS.md rule 12):
installing it there would make the ``except ImportError`` arm of the five
try/except fallbacks dead and break the ``cli.py`` COV-06 row. The five modules
that select the TOML parser (`cli.py`, `config.py`, `mcp_registration.py`,
`mcp_server.py`, `model.py`) still name it in the stale arm, so the **pyright**
gate needs a declaration (mypy resolves the same arm through the global
`ignore_missing_imports = true` — COR-1). Only ``load`` is modelled — the one
entry point those modules use.
"""

from typing import Any, BinaryIO

def load(fp: BinaryIO, /) -> dict[str, Any]: ...
```

The five call sites are all `_tomli.load(fh)` with `fh` a binary file handle
(`cli.py:471`, `config.py:157`, `mcp_registration.py:133`, `mcp_server.py:691`, `model.py:434`), so `load` is
the whole surface; `loads` is deliberately **not** stubbed (nothing calls it — a narrower stub is a smaller
drift surface).

### 4.2 Why it cannot be imported at runtime

1. The file extension is `.pyi`. CPython's import system never loads `.pyi`; no import statement in `src/`
   can resolve to it (`import tomli` resolves to an installed distribution or raises `ImportError` — the
   behaviour the fallbacks depend on).
2. Nothing puts `<repo>/typings` on `sys.path` at runtime. It is not a package, is not installed, and no
   module adds it (`pyright`'s `stubPath` and mypy's `mypy_path` are **analyzer** settings, read by the
   analyzers only — neither is read by the interpreter).
3. Verified by probe (SC-3c): `uv run python -c "import importlib.util; print(importlib.util.find_spec('tomli'))"`
   prints `None` — before and after the change.
4. The gate itself is neutral: removing the stub directory makes `uv run pyright` report the five
   `reportMissingImports` errors again, which is the only effect the stub has.

### 4.3 Why it cannot affect coverage or AGENTS rule 14

1. `[tool.coverage.run] source = ["src/sofer"]` measures **only** that tree; `typings/**` is outside it by
   construction, so it contributes no measurable line.
2. `scripts/check_core_coverage.sh` gates four named modules (`cli`, `scanner`, `prepare`, `publish`) by
   `--include=src/sofer/<file>.py`; a stub file under `typings/` cannot enter any of those rows.
3. The stub adds **no** `# pragma: no cover` and no test, so rule 14's "every line must execute" mandate is
   untouched: the four rows are re-run in verify (SC-5) precisely because two of those modules are edited
   (comment-only edits, §5).
4. The five `tomli` import sites in those modules are **unchanged by this change** — the stub removes the
   *diagnostic*, not a line of code. `cli.py` (a rule-14 module) receives **zero** edits, which is the whole
   point of choosing the stub over per-line ignores (P §4 D5).

### 4.4 Why it cannot leak into the wheel or the sdist

1. **Wheel:** `pyproject.toml` declares no `[tool.hatch.build.targets.wheel]` section and no `packages`
   override; hatchling infers the src-layout package for a project named `sofer`, i.e. `src/sofer`. A
   top-level `typings/` directory is therefore not a build input. Probe: SC-3c lists the wheel's entries and
   asserts no `typings/` or `.pyi` path.
2. **sdist:** explicitly excluded by DC-3 (`exclude = ["/typings"]`). Probe: SC-3c lists the sdist's entries
   and asserts the same absence.
3. **Runtime:** even if a future build config shipped the file, `.pyi` is never imported (§4.2).

### 4.5 Fallback chain (if the pinned pyright rejects the layout)

| Step | Shape | Cost | Trigger |
| --- | --- | --- | --- |
| 0 (frozen) | `stubPath = "typings"` + `typings/tomli-stubs/__init__.pyi` | none beyond the file | default |
| 1 | mirror layout: `typings/tomli/__init__.pyi` | `git mv` only; `stubPath` unchanged (there is **no** `mypy_path` — COR-1) | `uv run pyright` still reports the five `reportMissingImports` |
| 2 (R3) | five per-line `# pyright: ignore[reportMissingImports]` at `cli.py:465`, `config.py:151`, `mcp_registration.py:128`, `mcp_server.py:687`, `model.py:411`; drop `stubPath` and the stub directory | comment-only, coverage-neutral, **not** a coverage pragma; `cli.py` stays rule-14-safe because comments execute nothing | step 1 also fails |

Step 2 requires a CI-09 text amendment (S2 names `stubPath`) and is therefore an escalation, not a silent
substitution. Apply reports which step was taken.

---

## 5. The 18-site resolution table (BL §7.3) at diff precision

Thirteen pyright diagnostics under `standard` + `pythonVersion 3.13` (BL §7, re-confirmed unchanged in
§8.2) and six mypy `strict = true` diagnostics whose **composition changed** (BL §8.1). Two sites are shared,
so the change has **17 distinct apply sites** (BL §8.3: 13 + 6 − 2):

- `publish.py:70` — mypy `attr-defined` **+** pyright `reportPrivateImportUsage`.
- `_converters.py:611/620` — mypy `arg-type` **+** pyright `reportArgumentType` (both list invariance; COR-3).

**Retired, no edit:** `metadata.py:239` (`no-any-return`) — `types-pyyaml` resolved it (BL §8.1 REMOVED;
COR-2). Rule-14 modules touched: `prepare.py` (site 13) and `publish.py` (sites 4, 14) — every edit on those is
comment-only or an import path.

### 5.1 mypy half (sites 1–5; site 6 is the second shared site and is detailed in §5.2)

**(1) `_mirror.py:77` — `no-untyped-def` (DC-4 correction) — BL §7.3 #1**

```python
# before
    def _is_convertible_entry(entry) -> bool:
# after  (module already has `if TYPE_CHECKING: from .model import DatasetConfig` at :24-25)
    def _is_convertible_entry(entry: FileEntry) -> bool:
```
`if TYPE_CHECKING:` gains `FileEntry` alongside `DatasetConfig`. The call site is `_mirror.py:113`
(`for entry in cfg.files: if not _is_convertible_entry(entry)`) and the body reads `entry.recursive` and
`entry.remote`, so `FileEntry` is the only annotation that is true. `model.py:83` defines it.

**(2)–(3) `_clean.py:58`, `_clean.py:183` — `no-untyped-def` — BL §7.3 #2–#3**

```python
# header (before → after)
from pathlib import Path

from . import config
# after
from pathlib import Path
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    # Declared for the checker only: a runtime import of `.model` here would
    # re-introduce the module-load cycle the unannotated `cfg` deliberately avoided.
    from .model import DatasetConfig
```
```python
# before
    def allowed_output_remotes(
        cfg,  # DatasetConfig — avoid hard import cycle at module load
        keep_csv: bool,
        output_dir: Path,
    ) -> set[str]:
# after
    def allowed_output_remotes(
        cfg: DatasetConfig,
        keep_csv: bool,
        output_dir: Path,
    ) -> set[str]:
```
```python
# before
    def clean_build(cfg, override: str | None) -> None:
# after
    def clean_build(cfg: DatasetConfig, override: str | None) -> None:
```
`from __future__ import annotations` is already at `_clean.py:26`, so the annotations are strings at runtime
and the `TYPE_CHECKING`-guarded import is never executed. The comment that justified the missing annotation
moves onto the `TYPE_CHECKING` block, where it is now true.

**RETIRED — was revision 1's site 4; it is NOT a site in this change. `metadata.py:239` is not edited.**
Revision 1 (and BL §7.3 #4) resolved the
`no-any-return` at `metadata.py:239` with a `dumped: str = yaml.safe_dump(...)` binding annotation. The
dev-dependency `types-pyyaml` resolves `yaml.safe_dump`'s return type, so the diagnostic is **gone** on the
current tree (BL §8.1 REMOVED) — the annotation is not applied and no line of `metadata.py` changes. Recorded as
**COR-2**; the idiom it would have used is the same one kept at site 5.

**(4) `publish.py:70` — dual gate: mypy `attr-defined` + pyright `reportPrivateImportUsage` — BL §7.3 #6**

```python
# before
from huggingface_hub.utils import RepositoryNotFoundError
# after
from huggingface_hub.errors import RepositoryNotFoundError
```
One edit clears both gates. Public path verified against the installed hf 1.25.1
(`.venv/Lib/site-packages/huggingface_hub/errors.py:301: class RepositoryNotFoundError(HfHubHTTPError)`); the
declared floor probe (`uv run --with "huggingface-hub==0.26.0" python -c "from huggingface_hub.errors import
RepositoryNotFoundError"`, SC-4b) closes P §6's re-verification against `huggingface-hub>=0.26.0`. Fallback
if the floor lacks the module: keep the old import line and add
`# type: ignore[attr-defined]` + `# pyright: ignore[reportPrivateImportUsage]` (comment-only; `publish.py` is
rule-14, and a comment executes nothing and is not a coverage pragma). `publish.py:69`
(`from huggingface_hub import HfApi`) is untouched.

**(5) `mcp_server.py:691` — `no-any-return` — BL §7.3 #5**

```python
# before
        with open(path, "rb") as fh:
            return _tomli.load(fh)
# after
        with open(path, "rb") as fh:
            payload: dict[str, Any] = _tomli.load(fh)
        return payload
```
Same "annotate the binding" idiom the repo adopted for #198/#200 (the idiom revision 1 would also have used at the now-retired `metadata.py:239`); `Any` and `dict` are already imported in the module.

### 5.2 pyright half (sites 6–17)

**(6) `_converters.py:611/620` — dual gate: mypy `arg-type` + pyright `reportArgumentType` (list invariance) — BL §7.3 #7, amended by BL §8.1 (COR-3, DC-10)**

The tree currently carries a *partial* attempt at this site — `vals: list[object] = list(row) if row is not None
else []` at `:614` — and it **does not work**: it moves the diagnostic from the append to the preliminary
assignment for **both** checkers, because `list[X]` is invariant in `X`. The frozen fix is the **container
type** — one edit — and `:614` goes back to being unannotated:

```python
# tree today (both edits replaced by this revision)
#   :611   raw_rows: list[list[object]] = []
#   :614   vals: list[object] = list(row) if row is not None else []   <-- revert this annotation

# frozen after
#   imports:  from collections.abc import Sequence        # UP035: never typing.Sequence
#   :614                           vals = list(row) if row is not None else []
#   :611   # Sequence[object], not list[object]: a tuple of openpyxl cell scalars is a
#          # Sequence[object] by covariance but NOT a list[object] by invariance — the single
#          # diagnostic both checkers report at the append below.
#          raw_rows: list[Sequence[object]] = []
```

The candidate table is the proof that one edit clears both gates and the revision-1 annotation clears neither:

| Candidate at this site | mypy `strict = true` (2.3.0) | pyright 1.1.414 `standard` |
| --- | --- | --- |
| `raw_rows: list[list[object]]`, `vals` unannotated (pre-change) | `[arg-type]` at `:620` — `list[bool \| float \| … \| None]` is not `list[object]` | `reportArgumentType` at `:620` — same invariance |
| `vals: list[object]` at `:614` (revision 1, **in the tree now**) | `[assignment]` at `:614` — **still red** | `reportAssignmentType` at `:614` — **still red** |
| **`raw_rows: list[Sequence[object]]` + `:614` unannotated (frozen)** | **clean** — `list[bool \| float \| …]` <: `Sequence[object]` | **clean** — same covariant relation |

mypy's own note at this site (*"Perhaps you need `Sequence` instead of `list`?"*) is the same conclusion
reached from the type relation. `Sequence` is the right abstraction rather than a workaround: after each
`append` the buffer is only **read** — indexing and `len(r)` at `:627-629` — because every mutation (`extend`,
the truncating slice) happens *before* the append. **Behaviour-neutrality:** the annotation and the import are
static-only; no executable statement is added, removed or reordered; the element reads still yield `object`
for `col_data: dict[str, list[object]]`; the `collections.abc` import is the only module-level addition and it is
a pure stdlib import of an abstract class, evaluated nowhere at runtime by these local annotations (PEP 526 does
not evaluate local annotations, and the module already carries `from __future__ import annotations`). `Sequence`
must come from `collections.abc` — ruff's `UP035` rejects `typing.Sequence` — and the import belongs at module
level with the other stdlib imports.

**(7) `_converters.py:650` — `reportPossiblyUnboundVariable` (D6 restructure) — BL §7.3 #8**

Before (`:609-650`, abridged to the affected region):

```python
            for sheet_name in sheet_names:
                ...dedup bookkeeping...
                ws = wb[sheet_name]
                rows_iter = ws.iter_rows(values_only=True)

                try:
                    header_row = next(rows_iter)
                except StopIteration:
                    header_row = None

                if header_row is None or all(v is None for v in header_row):
                    ...empty-sheet branch (declares nothing named raw_rows)...
                else:
                    header = [...]
                    # Collect rows
                    raw_rows: list[list[object]] = []
                    for row in rows_iter:
                        vals = list(row) if row is not None else []
                        ...
                        raw_rows.append(vals)
                    ...col_data build from raw_rows...
                ...write parquet...
                # Clean locals for next iteration
                if "raw_rows" in locals():
                    del raw_rows
```

After:

```python
            for sheet_name in sheet_names:
                ...dedup bookkeeping...
                ws = wb[sheet_name]
                rows_iter = ws.iter_rows(values_only=True)

                # Per-sheet row buffer. Re-initialising here (instead of the
                # `locals()`-guarded `del` that used to close the loop body)
                # releases the previous sheet's list at exactly the same point and
                # leaves `raw_rows` bound on every path, which is what pyright's
                # `reportPossiblyUnboundVariable` could not prove about the `del`.
                raw_rows: list[list[object]] = []

                try:
                    header_row = next(rows_iter)
                except StopIteration:
                    header_row = None

                if header_row is None or all(v is None for v in header_row):
                    ...unchanged...
                else:
                    header = [...]
                    # Collect rows
                    for row in rows_iter:
                        vals: list[object] = list(row) if row is not None else []
                        ...
                        raw_rows.append(vals)
                    ...col_data build from raw_rows (unchanged)...
                ...write parquet (unchanged)...
                # (the three lines `# Clean locals` / `if "raw_rows" in locals():` /
                #  `del raw_rows` are DELETED)
```

Behaviour-neutrality argument (why the restructure is not a suppression):

1. **Same lifetime.** The previous iteration's list becomes unreachable at the first statement of the next
   iteration — the same point (or earlier) at which `del raw_rows` released it. The memory-hygiene intent
   (do not hold N sheet buffers) is preserved exactly.
2. **Same values.** `raw_rows` was already re-initialised to `[]` inside the `else:` branch before its only
   append loop; moving the initialisation to the top of the iteration cannot change any value the parse
   reads, because the empty-sheet branch never reads `raw_rows` and the `else:` branch always overwrote it
   first.
3. **Same control flow.** No branch, condition, exception path or `finally` is added or removed; the only
   removed construct is a membership test on `locals()` and a `del` whose guard is what pyright could not
   model (BL §3).
4. **Coverage.** Three lines leave the module (the `if`, the `del`, the comment) and one line is added; the
   100.00% rows are unaffected (`_converters.py` has no per-file floor), and the pyright diagnostic that
   justified `standard` over `basic` (D1) disappears by fixing the code rather than by muting it.
5. **Verified by the existing converter tests** — the xlsx multi-sheet / empty-sheet / N-sheet dedup cases
   (`tests/test_converters*`) run green in SC-5.

**(8)–(12) `reportMissingImports` ×5 — the `tomli` stub** (§4): `cli.py:465`, `config.py:151`,
`mcp_registration.py:128`, `mcp_server.py:687`, `model.py:411` — BL §7.3 #9–#13. **Zero `src/` edits** on the
stub route (D5), and **no mypy change at all** (COR-1: mypy's global `ignore_missing_imports = true` already
covers all five).

**(13)–(14) `prepare.py:445`, `publish.py:686` — `reportAttributeAccessIssue` (`TextIO.reconfigure`) — BL §7.3 #14–#15**

```python
# before (prepare.py:444-445) — publish.py:685-686 is the identical shape
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
# after
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
```
Per-line ignore, not a narrowing (D7): typeshed places `reconfigure` on `TextIOWrapper`, not `TextIO`, and
narrowing to the `cli.py:1609-1611` house pattern would fail `tests/test_prepare.py:1626-1657` and
`tests/test_publish.py:2018-2052` (both inject a duck-typed `_FakeStdout` and assert the reconfiguration) and
leave these rule-14 lines unexecuted — a rule-14 violation by construction (BL §4.2). The ignore is a pyright
comment, invisible to mypy, so it cannot trip `warn_unused_ignores`.

**(15)–(17) `verification.py:97` — `reportArgumentType` ×3 (`str | NamedSplit`), consumed at `:101`, `:103`, `:116` — BL §7.3 #16–#18**

```python
# before (:97)
        actual_splits = list(ds.keys())
# after
        actual_splits = [str(name) for name in ds.keys()]
```
One coercion at the binding site fixes all three downstream uses (`split_row_counts[name]` at `:101`/`:103`,
`split_names=actual_splits` at `:116`). Behaviour-neutrality, with the library evidence:

- `datasets` declares `class DatasetDict(dict[Union[str, NamedSplit], "Dataset"])`
  (`.venv/Lib/site-packages/datasets/dataset_dict.py:63`), which is why `keys()` is typed
  `list[str | NamedSplit]`. Real `load_dataset()` builds those keys from plain split-name strings, so for the
  actual runtime the comprehension is the identity.
- If a key *were* a `NamedSplit`, `str()` returns `self._name` (`datasets/splits.py:375-376`, a `str`), and
  `NamedSplit.__hash__`/`__eq__` already delegate to the name (`splits.py:381-397`), so set comparison,
  dict-key lookup and `ds[name]` resolution are unchanged either way
  (`dataset_dict.py:90-92` accepts `str` or `NamedSplit`).
- `VerificationReport.split_names: list[str]` and `split_row_counts: dict[str, int]`
  (`verification.py:40,41`) become **true** instead of merely-tolerated.
- The only observable difference is the rendering inside one warning on the path where a split really is
  mismatched: `got [NamedSplit('train')]` becomes `got ['train']`. No test asserts that rendering — the
  assertion is the substring `"Split names differ from expected"` (`tests/test_splits.py:544`).
- The mocked tests inject plain-`str` dicts (`tests/test_splits.py:396-399, 431, 515, 535`), so the coercion
  is the identity on every existing test path.
- BL §8.2: `datasets` is now a **direct runtime dependency**, so these three diagnostics are **structural** —
  they will not revert to a missing import. The optional-dependency `try: import datasets / except ImportError:`
  guard (`verification.py:66`) is therefore practically unreachable in a synced environment and SHALL be
  **preserved byte-identical** (never deleted as "dead"): the coercion sits inside the success path only, and
  the guard stays mockable via `patch.dict(sys.modules, {"datasets": …})`, which is how the existing tests
  exercise this function (`tests/test_splits.py:406, 436, 456, 519, 540`).

### 5.3 Files touched, in one place

| File | Sites | Edit class | Rule-14 module |
| --- | --- | --- | --- |
| `_mirror.py` | 1 | annotation + TYPE_CHECKING import | no |
| `_clean.py` | 2, 3 | annotations + TYPE_CHECKING block | no |
| `publish.py` | 4, 14 | import path + comment | **yes** |
| `mcp_server.py` | 5 | binding annotation | no |
| `_converters.py` | 6, 7 | `Sequence[object]` container + `collections.abc` import; loop restructure | no |
| `prepare.py` | 13 | comment | **yes** |
| `verification.py` | 15-17 | one coercion | no |
| `cli.py`, `config.py`, `mcp_registration.py`, `model.py` | 8-12 | **0 lines** (stub route) | `cli.py` stays pristine |
| `metadata.py` | — | **RETIRED** by `types-pyyaml` (COR-2) — zero lines | no |

---

## 6. The CI-09 delta (frozen text and anchors)

### 6.1 File and framing

New file `openspec/changes/2026-09-15-chore-type-gate-policy/specs/ci/spec.md`, modelled on the archived
CI-08 delta (`openspec/changes/archive/2026-09-15-chore-ruff-single-authority/specs/ci/spec.md`) and the
COV-07 delta (`…/2026-09-15-chore-cov01-floors-status-quo/specs/coverage/spec.md`). Its framing blockquotes:

> **Additive for CI-09, plus one authorized modification for CI-07.** CI-01..CI-06 and CI-08 keep their
> clauses, scenarios and Test Mapping rows byte-for-byte; the contract enters as **new** requirement **CI-09**,
> the next free ID in this capability, with **five** scenarios and **five** appended Test Mapping rows. CI-07
> receives **one** clause amendment (+ its own restatement in one scenario bullet) — the authorized exception
> of §6.6/DC-11, driven by the maintainer's decision that `[tool.mypy] python_version = "3.11"` stays.
>
> **Capability `ci`, justified.** `ci` owns gate config/declaration truth (CI-01 flags-in-config, CI-06
> documentation truth, CI-07 declaration equality, CI-08 pin authority) and is the capability whose Test
> Mapping indexes `tests/test_ci_workflows.py` — the file the six guards land in. The alternative home
> `process-boundary` PB-15 was rejected: this change arms a CI step, so a requirement about the gate's
> declaration belongs with the gate (EX §3.1).
>
> **One requirement, two clause groups.** Q1 (`tests/` excluded from both gates) and Q2 (pyright is a real
> gate) are two halves of one policy question; they are separately **scenario'd** rather than split into
> CI-09 + CI-10, which halves the archive-insert cost (P §4 D9, O10 closed).
>
> **Rule-6 resolution.** S1–S4 map to static guards G1/G3/G4/G5 in `tests/test_ci_workflows.py`; S5's
> declarations-invariance half maps to guard G6 and its mypy-exit-zero half maps to **verify-phase runtime
> evidence** (CI-01/CI-08 precedent — a pytest cannot spawn the gate without adding a dependency class
> AGENTS rule 9 keeps out).
>
> **One CI step is armed, deliberately.** Unlike CI-08 (which asserted the *inverse*), CI-09 declares the
> `lint`-job step that runs the pyright gate, and G3 keeps that step and the ban on workflow version
> literals in one guard.
>
> **Domain hygiene (checked at design time).** `openspec/specs/ci/spec.md` ends at CI-08; no other
> non-archived change carries `specs/ci/`; this change has no legacy flat `openspec/changes/<change>/spec.md`.
> The canonical file is **not** edited before `sdd-sync`.
>
> **Cross-references, not edits.** `process-boundary` PB-07 ("New test helpers SHALL be type-annotated even
> though mypy excludes `tests/`") is cited by S1 and left byte-identical; PB-14 (hook scope) and CI-08 (pin
> authority) are cited, never modified; and CI-07's `.python-version` pin and every clause other than the
> `python_version` declaration are cited and untouched **except** the single amendment frozen in §6.6.

### 6.2 Requirement title and text

```markdown
### Requirement: Type-gate posture — `tests/` excluded from both type gates and pyright adopted as a real gate (CI-09)

> Added by change `2026-09-15-chore-type-gate-policy` (GitHub #201). Scenarios 1–4 are asserted
> by static guard tests in `tests/test_ci_workflows.py`; scenario 5's mypy-exit-zero half is
> verify-phase runtime evidence — the framing this capability's Test Mapping already uses for gate
> exit codes.
```

**Clause group Q1 — the `tests/` exclusion (the durable record of decision (a)).**

The repository SHALL keep `tests/` out of **every** enforced type gate. `[tool.mypy] exclude` SHALL contain
`tests/`; every mypy invocation in `.github/workflows/ci.yml` and `.pre-commit-config.yaml` SHALL name
`src`/`scripts` and SHALL NOT name `tests`; and `[tool.pyright] exclude` SHALL contain `tests`, so the
exclusion is declared once in configuration and the pyright gate SHALL be invoked **bare** (no path
arguments) for that declaration to be the single authority. The posture SHALL be documented in
`CONTRIBUTING.md`'s type-checking section, and this requirement SHALL NOT be read as relaxing
`process-boundary` PB-07: new test helpers SHALL still be type-annotated by convention even though neither
gate analyses them.

**Clause group Q2 — the pyright gate (the durable record of decision (c)).**

pyright SHALL be a **real** gate, not an advisory analyzer. `pyproject.toml` SHALL declare exactly one
`[tool.pyright]` table — the single configuration authority; no `pyrightconfig.json` SHALL exist anywhere in
the tree, because pyright silently prefers it over the table. That table SHALL declare
`typeCheckingMode = "standard"`, `include` covering `src` and `scripts` (the enforced mypy scope),
`exclude` containing `tests`, `pythonVersion` equal to the gate interpreter that `.python-version` pins,
`stubPath` naming the committed `tomli` stub directory, and SHALL NOT globally disable
`reportMissingImports`. One step in the `lint` job of `.github/workflows/ci.yml` SHALL run the gate, and one
local pre-commit hook SHALL run it locally, mirroring the `mypy` hook's shape (`pass_filenames: false`).

pyright SHALL be pinned by an exact `pyright==X.Y.Z` entry in `[dependency-groups] dev`, and the version
SHALL reach CI through `uv.lock`: **no file under `.github/workflows/` SHALL declare a pyright version
literal**. pyright has no `required-version` analogue, so the enforcement SHALL be a runtime equality proof
— `uv run pyright --version` SHALL equal the dev pin — recorded as verify-phase evidence.

The gate's exit contract SHALL be **errors only**: no invocation SHALL pass `--warnings`, and any rule the
repository wants to bind SHALL be declared at `error` severity in `[tool.pyright]` rather than left at
warning severity and hoped for. The measured `"N errors, M warnings"` summary SHALL be recorded as
verify-phase evidence so a warning-count jump is visible without failing the build.

The five `tomli` fallback sites SHALL be resolved by the committed stub under `stubPath` — never by adding
`tomli` to any dependency group, which would make the `except ImportError` arm dead on the pinned interpreter
and break the `cli.py` COV-06 row (AGENTS.md rule 12). The gate SHALL be invoked as `uv run pyright`, so
third-party imports resolve against the project environment.

**Clause group S — no weakening.** Adopting the new posture SHALL NOT weaken what already holds: under the
committed `[tool.mypy] strict = true`, `uv run mypy src/ scripts/` SHALL exit 0; the `[tool.coverage.report]`
TOTAL floor, the four COV-06 per-file gates, the CI test matrix and the `release.yml` `needs` graph SHALL be
unchanged; and no resolution of a type diagnostic SHALL add a `# pragma: no cover` anywhere.

### 6.3 The five scenarios (file style: `- GIVEN / - WHEN / - THEN / - AND`)

```markdown
#### Scenario: `tests/` stays out of both type gates

- GIVEN `pyproject.toml`'s `[tool.mypy]` and `[tool.pyright]` blocks, every mypy invocation in
  `.github/workflows/ci.yml` and `.pre-commit-config.yaml`, and `CONTRIBUTING.md`'s type-checking section
- WHEN `tests/test_ci_workflows.py::test_mypy_and_pyright_exclude_tests` inspects them
- THEN `[tool.mypy] exclude` SHALL contain `tests/` and `[tool.pyright] exclude` SHALL contain `tests`
- AND every mypy invocation SHALL name `src`/`scripts` and SHALL NOT name `tests`
- AND the type-checking section SHALL name both gate commands and state that `tests/` is excluded from
  both gates, so Q1's answer is documented where a contributor reads it
- AND the PR template's Checklist SHALL carry the pyright item (the CI-06 S4 shape), and
  `process-boundary` PB-07 SHALL be cross-referenced, not edited — its "test helpers are still
  annotated by convention" clause stays in force

#### Scenario: `[tool.pyright]` declares the decided posture and the gate runs

- GIVEN `pyproject.toml`, `.github/workflows/ci.yml`, and `.pre-commit-config.yaml`
- WHEN `tests/test_ci_workflows.py::test_pyright_config_declares_the_decided_posture` and
  `::test_ci_lint_job_runs_the_pyright_gate` inspect them
- THEN `[tool.pyright]` SHALL declare `typeCheckingMode = "standard"`, an `include` covering both
  `src` and `scripts`, an `exclude` containing `tests`, a `pythonVersion` equal to the value
  `.python-version` pins, and a `stubPath` naming the committed `tomli` stub directory
- AND `reportMissingImports` SHALL NOT be globally disabled
- AND the `lint` job SHALL contain exactly the bare gate invocation `uv run pyright`, and no file
  under `.github/workflows/` SHALL declare a pyright version literal
- AND the committed invocation SHALL exit 0 on the committed tree, with the measured
  `"N errors, 0 warnings"` summary recorded as verify-phase runtime evidence

#### Scenario: Exactly one pyright config home exists

- GIVEN the repository tree, excluding the virtual environment and other machine-local directories
- WHEN `tests/test_ci_workflows.py::test_pyright_has_exactly_one_config_home` searches it
- THEN zero `pyrightconfig.json` files SHALL exist, so `[tool.pyright]` stays the single
  configuration authority — the analogue of CI-08's single-declaration rule, which a stray JSON
  file would silently defeat because pyright prefers it over the table

#### Scenario: The pin is exact, reaches CI through the lock, and matches the running binary

- GIVEN `pyproject.toml`'s `[dependency-groups] dev` list and `uv.lock`
- WHEN `tests/test_ci_workflows.py::test_analyzer_dev_pins_are_exact_and_match_the_lock` derives
  `X.Y.Z` from the dev pin and compares the lock's resolved entry against it, and when
  `uv run pyright --version` runs
- THEN exactly one pyright dev entry SHALL exist and its specifier SHALL be the exact
  `==X.Y.Z`, so a `>=` floor SHALL fail the guard
- AND `uv.lock`'s resolved pyright package SHALL carry that same version
- AND the guard SHALL hold no version literal of its own, so a bump edits declarations only
- AND `uv run pyright --version` SHALL equal that version — the enforcement pyright itself lacks
  (it has no `required-version` analogue) — recorded as verify-phase runtime evidence

#### Scenario: Adopting the gate leaves every existing gate declaration intact

- GIVEN `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  `.pre-commit-config.yaml`, and `pyproject.toml`
- WHEN `tests/test_ci_workflows.py::test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`
  inspects them, and when `uv run mypy src/ scripts/` runs under the committed `strict = true`
- THEN the mypy invocations SHALL still be exactly `uv run mypy src/ scripts/` on both surfaces
  (the `lint` job step and the local `mypy` hook entry)
- AND no workflow SHALL declare a coverage floor literal or a `--fail-under` flag in its raw text,
  and exactly one `ruff-format` hook entry SHALL remain (PB-14)
- AND `uv run mypy src/ scripts/` SHALL exit 0 with zero errors, and the CI test matrix,
  `release.yml`'s `needs` graph, the TOTAL floor and the four COV-06 rows SHALL be unchanged —
  recorded as verify-phase runtime evidence (CI-01 gate-exit-code precedent)
```

### 6.4 Test Mapping rows (appended at the end of the canonical table)

```markdown
| CI-09 | `tests/` stays out of both type gates | `tests/test_ci_workflows.py` — `test_mypy_and_pyright_exclude_tests`: tomllib parse of both type-checker blocks + text inspection of every mypy invocation and of `CONTRIBUTING.md`'s type-checking section and the PR template |
| CI-09 | `[tool.pyright]` declares the decided posture and the gate runs | `tests/test_ci_workflows.py` — `test_pyright_config_declares_the_decided_posture` and `test_ci_lint_job_runs_the_pyright_gate`: tomllib + YAML inspection; local gate run `uv run pyright` exit code with the measured summary line (verify-phase runtime evidence) |
| CI-09 | Exactly one pyright config home exists | `tests/test_ci_workflows.py` — `test_pyright_has_exactly_one_config_home`: tree walk for `pyrightconfig.json` |
| CI-09 | The pin is exact, reaches CI through the lock, and matches the running binary | `tests/test_ci_workflows.py` — `test_analyzer_dev_pins_are_exact_and_match_the_lock`: dev-pin derivation + `uv.lock` resolution equality; `uv run pyright --version` equality (verify-phase runtime evidence) |
| CI-09 | Adopting the gate leaves every existing gate declaration intact | `tests/test_ci_workflows.py` — `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`: YAML/tomllib inspection; `uv run mypy src/ scripts/` exit code (CI-01 gate-exit-code precedent) |
```

### 6.5 Insertion and append anchors (sync mechanics)

| Anchor | Exact mechanics |
| --- | --- |
| **Requirement block** | Insert **between** the `---` that closes CI-08 (the separator immediately following CI-08's last scenario, whose final bullet is the verify-phase-evidence `- AND this evidence is **verify-phase runtime evidence** …` line) **and** the `## Test Mapping` heading. The block carries its **own trailing `---`** so no doubled separator appears (the CI-07/CI-08/COV-07 convention) |
| **Test Mapping rows** | Append the five rows **at the end of the existing table**, immediately after the CI-08 `required-version rejects a mismatched binary` row, which is the table's last content row today |
| **Untouched** | The `## Test Mapping` intro prose, every existing row, the `## Purpose` enumeration (deliberately left stale, listing only CI-01..CI-06 — the CI-07/CI-08 precedent), and every CI-01..CI-08 byte **except** the two CI-07 occurrences frozen in §6.6 |
| **Also in the delta file** | `## MODIFIED Requirements` carrying CI-07's amended clause (§6.6), `## Cross-referenced and deliberately untouched` (CI-01..CI-06, CI-08, PB-07, PB-14, PKG-06's `uv.lock` regeneration class, #187/#212/#194/#215 untouched) and `**Non-goals recorded by this delta:**` (the restated P §18 list, minus the CI-07 carve-out) |

### 6.6 The CI-07 clause amendment (MODIFIED — the authorized exception, DC-11)

This is the one place where this change edits an existing `ci` requirement. The exception is **authorized by
the maintainer's decision** (BL §8.5 #1: `[tool.mypy] python_version = "3.11"` stays), **recorded as COR-4 in
§2**, **frozen here word for word**, and **enforced by guard G7**. Rationale: leaving the clause as written
would ship a requirement that is false on the committed tree — the exact "documented contract is false"
failure mode this whole change exists to remove (P §1).

**Delta framing (goes in the same delta file, after the ADDED section):**

````markdown
## MODIFIED Requirements

### Requirement: Dev interpreter pin matches the gate interpreter (CI-07)

> Added by change `2026-09-14-chore-python-version-313` (GitHub #178). Every scenario below is evidenced by
> verify-phase static or runtime gate evidence rather than by a pytest assertion — the framing this
> capability's own Test Mapping already uses for gate exit codes.
>
> Modified by `2026-09-15-chore-type-gate-policy` (GitHub #201) — the `[tool.mypy] python_version` declaration
> moved to `"3.11"` by maintainer decision; the `.python-version` pin, its equality with both gate-job pins, and
> every other clause are unchanged.
````

(The second blockquote line is **appended** to CI-07's existing `> Added by …` blockquote line, exactly as
`openspec/specs/repo-compliance/spec.md:681-682` stacks "Added by … Modified by …". CI-07's heading, its `> Added
by …` line and every scenario heading keep their bytes.)

**Occurrence 1 — the clause inside CI-07's third paragraph.** Frozen replacement, inside a paragraph whose
remaining bytes are copied verbatim:

- **REMOVED** (the stale clause):
  `` `[tool.mypy] python_version` SHALL remain `"3.10"` (it declares the minimum language/typing level, tied to `requires-python`, not the developer interpreter) ``
- **INSERTED** (frozen wording, one sentence, same position in the paragraph):

```text
`[tool.mypy] python_version` SHALL be `"3.11"` — the language level mypy analyses against, declared
independently of both `requires-python` (`>=3.10`, the support floor) and `.python-version` (`3.13`, the gate
interpreter). At `3.11` the `import tomllib as _tomli` arm of the five interpreter-selection fallback sites is
a resolvable stdlib module for mypy, while the marker-only `tomli` arm is covered by the global
`ignore_missing_imports = true`. It SHALL NOT be read as a support declaration: `requires-python` SHALL remain
`>=3.10`. A change that moves this value SHALL amend this clause in the same change.
```

- **APPENDED** immediately after that paragraph, using the repository's `(Previously: …)` marker convention
  (`openspec/specs/cli/spec.md:209`, `parquet-conversion/spec.md:529`, `tool-config/spec.md:324`):

```text
(Previously: this clause required `[tool.mypy] python_version` to remain `"3.10"` and described it as the
minimum language level tied to `requires-python`; the maintainer declared `"3.11"` as the analysis level and
change `2026-09-15-chore-type-gate-policy` (GitHub #201) amends the clause to match the committed
configuration.)
```

**Occurrence 2 — the same clause restated in CI-07's "User-facing support is unchanged" scenario.** The
scenario's first THEN bullet repeats the clause, so amending only the paragraph would leave CI-07
self-contradictory. Frozen replacement (the bullet is wrapped over two lines in the canonical file):

- **REMOVED**: `` - THEN `requires-python` SHALL still be `>=3.10` and `[tool.mypy] python_version` / SHALL still be `"3.10"` ``
- **INSERTED**:

```text
- THEN `requires-python` SHALL still be `>=3.10` and `[tool.mypy] python_version`
  SHALL be `"3.11"` — the declared analysis level, amended by change
  `2026-09-15-chore-type-gate-policy` (GitHub #201) to match the committed configuration
```

**Deliberately untouched inside CI-07 (byte-identical; G7 reads none of them):** the `.python-version` =
`3.13` clause and its equality with both gate-job pins; the "flag-free mypy gates are green on the pinned
interpreter" paragraph (including its `[no-redef]` requirements); the COV-06-script paragraph; the AGENTS
rule 12 latent-issue paragraph; the four other scenario bullets (dev pin = both job pins; flag-free mypy
gates; COV-06 script; latent-issue note); and the fifth scenario's remaining bullets (`requires-python`,
matrix, floor, diff scope).

**Evidence class unchanged.** CI-07's Test Mapping row (`| CI-07 | User-facing support is unchanged |
Verify-phase static evidence — diff and config inspection … |`) stays byte-identical and is re-satisfied by
**SC-6c**: the row's evidence class — a static read of the config against the requirement — is exactly what
SC-6c performs, so **no new CI-07 row is added**.

**Scope note for the delta's `## Cross-referenced and deliberately untouched` section (freezes R12's disposition).**
Frozen wording:

```text
- `ci` CI-07's "zero `pyproject.toml` paths / zero `.github/workflows/` paths" clause — **not amended** by this
  change. It was written and verified as the evidence for the change that moved `.python-version` to `3.13`
  (where nothing else moved), and it is not read here as a standing ban on ever touching `pyproject.toml` or
  `.github/workflows/` — CI-09 itself requires a `ci.yml` lint step and a `[tool.pyright]` block. The clause's
  bytes stay identical; this reading is recorded so the tension is visible rather than latent.
```

**Sync anchors (in addition to §6.5):**

| Anchor | Exact mechanics |
| --- | --- |
| CI-07 blockquote | In `openspec/specs/ci/spec.md`, **append** the `> Modified by \`2026-09-15-chore-type-gate-policy\` (GitHub #201) — …` line to the existing CI-07 `> Added by …` blockquote line (same blockquote, one new line) |
| Occurrence 1 | Replace exactly the `[tool.mypy] python_version` sentence inside CI-07's third paragraph (the paragraph beginning "This requirement SHALL NOT change user-facing Python support:"); every other byte of the paragraph stays |
| `(Previously: …)` marker | Insert as a new paragraph immediately **after** CI-07's third paragraph |
| Occurrence 2 | Replace the first THEN bullet of the "User-facing support is unchanged" scenario (the only bullet that restates the clause) |

---

## 7. Documentation edits (verbatim, same change per D9/D13)

### 7.1 `CONTRIBUTING.md`

Replace the three lines at `CONTRIBUTING.md:79-81` (`### Type checking` + its two lines) with this
section — heading, two prose paragraphs, and one fenced command block (shown here un-nested because this
design file is itself markdown):

````text
### Type checking

Two type checkers gate the source — **mypy** (`[tool.mypy]`, `strict = true`) and **pyright**
(`[tool.pyright]`, `typeCheckingMode = "standard"`). Both are wired into the local pre-commit hooks and
into the CI `lint` job, and `pyproject.toml` is the single source of the mode, scope and version each one
runs with:

```bash
uv run mypy src/ scripts/   # the enforced mypy invocation (CI + the `mypy` hook)
uv run pyright              # the enforced pyright invocation (CI + the `pyright` hook)
```

The scope is `src/` and `scripts/`; **`tests/` is excluded from both type gates** by policy (recorded in
`openspec/specs/ci/spec.md` CI-09) — test helpers are still annotated by convention
(`process-boundary` PB-07), but the test tree is never type-checked. pyright is pinned exactly in
`[dependency-groups] dev` and must be run through `uv run`: it resolves third-party imports against the
project environment, so running it any other way (bare, `npx`, `uvx`) can report phantom missing imports.
````

The "Development commands" list (`CONTRIBUTING.md:24-30`) gains **exactly one** line, placed after
`uv run mypy src/`:

```bash
uv run pyright                   # second type gate (config-driven; src/ + scripts/)
```

Nothing else in that list changes. In particular the existing `uv run mypy src/` line is left as-is: the
narrower-than-CI command list is **#212's** surface (EX §9.1 #2, CI-08's cross-reference table), not this
change's — only the type-checking section and the roster grow here. The `ruff.toml`-at-root sentence
(`CONTRIBUTING.md:75`) is untouched (#187).

Truthfulness note: after §5 site 6 and the committed `strict = true`, the section's claims are literally
true — `[tool.mypy] strict = true` is the tree's value (the drift BL §0 records is resolved by the code,
exactly as P §6's conflict note requires; the doc is **not** rewritten to match a `false`).

### 7.2 `AGENTS.md`

**Rule 5** (`AGENTS.md:36-38`) — the pre-commit roster and the push instruction, minimally:

```markdown
### 5. Pre-commit hooks run automatically
- `ruff` (lint + fix + format), `mypy`, and `pyright` run on every commit.
- Never commit with `--no-verify` unless you have a documented reason.
- Before pushing, run `uv run mypy src/` and `uv run pyright` — the CI will reject type errors.
```

(Line 1 gains `pyright`; line 3 gains `and uv run pyright`. The `uv run mypy src/` path is left as written —
#212 owns the narrower-than-CI command text, and this rule is not that surface.)

**Rule 12's latent-issue bullet** (`AGENTS.md:91`) — append one sentence that **adds** without weakening any
CI-07-asserted content (the note must keep naming all five modules, quoting both fallback forms, keeping
"do not add mypy to the version matrix" and the `--python 3.13` escape hatch — it does):

```markdown
    … (unchanged text) … A pyright gate (`uv run pyright`, `[tool.pyright]`) now covers the same `src/` and
    `scripts/` scope; the five `tomli` fallback sites named here are resolved for **both** checkers by the
    committed `typings/tomli-stubs/` stub, never by adding `tomli` to the dev group — which is exactly the
    move this note forbids.
```

### 7.3 `README.md` + `README_ES.md` (one mirrored bullet, D13)

Insert as the **first** bullet of the section (before the coverage bullet), so the roster names both checkers
and the ordering matches the CI job order:

```markdown
- **Type checking**: `src/` and `scripts/` pass two type gates — **mypy** (strict mode,
  `[tool.mypy]`) and **pyright** (`standard` mode, `[tool.pyright]`) — both declared in
  `pyproject.toml` and run in CI and in the local pre-commit hooks. `tests/` is excluded
  from both gates by policy (`openspec/specs/ci/spec.md` CI-09).
```

`README_ES.md` gets the mirrored bullet in the same position under `## Controles de calidad y escaneo de
seguridad`, prose translated, technical content (commands, keys, paths, `CI-09`) in English, matching the
file's existing bullet style (English bold label, Spanish prose):

```markdown
- **Type checking**: `src/` y `scripts/` pasan por dos compuertas de tipos — **mypy** (modo strict,
  `[tool.mypy]`) y **pyright** (modo `standard`, `[tool.pyright]`) —, ambas declaradas en
  `pyproject.toml` y ejecutadas en CI y en los hooks locales de pre-commit. `tests/` queda
  excluido de ambas por política (`openspec/specs/ci/spec.md` CI-09).
```

Both files' section headings, order and existing bullets are unchanged (AGENTS rule 13 satisfied in the same
commit); the tables of contents are unaffected because the section already exists in both.

### 7.4 `.github/PULL_REQUEST_TEMPLATE.md`

| Location | Edit |
| --- | --- |
| Verification code block | add, after the mypy block: `$ uv run pyright` / `0 errors, 0 warnings` |
| Checklist | add after the `uv run mypy src/` item: `- [ ] `uv run pyright` — clean (pyright gate, `[tool.pyright]`)` |

The existing `uv run mypy src/` lines in both blocks are untouched (#212).

---

## 8. Guards G1–G6 (`tests/test_ci_workflows.py`)

One new helper, mirroring `_declared_ruff_version()` (`tests/test_ci_workflows.py:92-118`) exactly in
shape and refusal-to-accept-a-floor behaviour:

```python
def _declared_pyright_version() -> str:
    """Extract the ``X.Y.Z`` version from the ``pyproject.toml`` dev-group pyright pin.

    The single source of the pyright version for G3 and G5: both derive it and hold no
    version literal, so a bump edits declarations only.
    """
    dev = _load_toml("pyproject.toml")["dependency-groups"]["dev"]
    pins = []
    for entry in dev:
        match = _DEV_ENTRY_RE.match(entry) if isinstance(entry, str) else None
        if match is not None and match.group("name") == "pyright":
            pins.append(match.group("spec").strip())
    assert len(pins) == 1, f"expected exactly one pyright dev pin, found {pins}"
    exact = _EXACT_PIN_RE.match(pins[0])
    assert exact is not None, (
        f"the pyright dev pin must be an exact ==X.Y.Z specifier, got {pins[0]!r} — a floor "
        "lets `uv lock` drift the analyzer away from the version the gate runs"
    )
    return exact.group("version")
```

Plus one module constant for G2's walk: `_SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "htmlcov", ".pytest_cache", "__pycache__"})`.

| Guard | Assertion (exact) | Why it cannot go stale on a legitimate change | Red → green |
| --- | --- | --- | --- |
| **G1** `test_pyright_config_declares_the_decided_posture` | `[tool.pyright]` exists in `pyproject.toml`; `typeCheckingMode == "standard"`; `include` ⊇ {`src`, `scripts`}; `exclude` ⊇ {`tests`}; `pythonVersion == _read_text(".python-version").strip()`; `stubPath == "typings"`; `reportMissingImports not in ("none", False)` | It asserts the **decision class** (mode, scope, exclusions, interpreter, stub home, one binding rule) and **nothing else** — adding a rule key, an `executionEnvironments` entry, or a deeper exclude path stays green. The interpreter assertion is **derived** from `.python-version`, so a legitimate gate-interpreter bump keeps it green as long as the two move together (CI-07's invariant) | **RED now** (no `[tool.pyright]`) → green after §3 + §4 |
| **G2** `test_pyright_has_exactly_one_config_home` | walk the repo root with `os.walk`, pruning `_SKIP_DIRS`, and assert no file named `pyrightconfig.json` is found; assert the walk saw files (fails loudly, not vacuously) | It guards a property, not a value: it is red only when someone adds a second config home, which is a defect by D4 regardless of any legitimate change. Pruning `.venv`/`node_modules` keeps it fast and free of third-party false positives | green now → green after (**tripwire**, DC-5) |
| **G3** `test_ci_lint_job_runs_the_pyright_gate` | `ci.yml`'s `lint` job contains a step whose `run == "uv run pyright"`; **and** no workflow file contains the derived `_declared_pyright_version()` value **and** no workflow matches `pyright\s*(?:==\|@\|>=\|<=\|~=\|!=\|>\|<\|=)\s*\d` (mirrors `test_workflows_do_not_declare_a_ruff_version`) | The invocation is CI-09 S2's frozen text; the version half is derived and CI-08-S2-shaped. A legitimate change adds steps or edits other jobs — the guard matches one exact `run` string and scans for version specifiers only | **RED now** (no pyright step) → green after the `ci.yml` step |
| **G4** `test_mypy_and_pyright_exclude_tests` | (a) `[tool.mypy] exclude` ⊇ {`tests`}; (b) every mypy invocation in `ci.yml`'s `lint` job and in `.pre-commit-config.yaml`'s `local` hooks names `src`/`scripts` and not `tests`, and the hook entry equals `uv run mypy src/ scripts/`; (c) `[tool.pyright] exclude` ⊇ {`tests`}; (d) `CONTRIBUTING.md`'s `### Type checking` section contains `uv run mypy`, `uv run pyright` and `tests/`; (e) the PR-template Checklist contains `pyright` (DC-6) | Every clause **is** the decision (Q1's exclusion + AC3's documentation half), not incidental prose: a legitimate rewrite of the section still names both commands and the excluded tree, because that is what CI-09 S1 requires it to state. Clause (b) matches on the invocation text — the only legitimate change is a spec change to the gate command itself | **RED now** ((c), (d), (e) absent) → green after §3 + §7.1 + §7.4 |
| **G5** `test_analyzer_dev_pins_are_exact_and_match_the_lock` | `_declared_pyright_version()` (exactly one exact pin) and `_load_toml("uv.lock")["package"]` contains exactly one `name == "pyright"` entry whose `version` equals it | Both sides are derived and the lock is TOML, so the guard reads the resolution, not a literal. A legitimate bump edits the pin and regenerates the lock in one commit — green. It goes red only when the two disagree, which is the defect CI-08's shape exists to catch | green now (pin + lock already landed) → green after (**tripwire**, DC-5) |
| **G6** `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates` | `ci.yml`'s `lint` job still contains `run == "uv run mypy src/ scripts/"`; the `local` `mypy` hook's `entry` is still `uv run mypy src/ scripts/`; no workflow's raw text contains `fail_under` or `--fail-under`; exactly one `ruff-format` hook entry exists | It is the AC5 non-regression guard: it asserts the status quo the new gate must not disturb, so a legitimate change to the **new** pyright surface cannot make it red, and a change that rewrites an existing gate would (which is what CI-09 S5 forbids). Deliberately narrow: the ruff-version and floor-literal details stay owned by their existing narrower guards. The maintainer's `[[tool.mypy.overrides]]` block does not touch it — G6 asserts the two mypy *invocations*, never the config block | green now → green after (**non-regression**, DC-5) |
| **G7** (A4, DC-11) `test_ci07_names_the_declared_mypy_language_level` | read `[tool.mypy] python_version` from `pyproject.toml` (**derived — the guard holds no literal**) and assert that (a) `openspec/specs/ci/spec.md` names that value inside CI-07's requirement block, and (b) the retired `"3.10"` value appears **nowhere** in CI-07's text | It is the amendment's enforcement: the committed config and the canonical clause cannot diverge, and a future `python_version` move keeps it green **only** by amending CI-07 in the same change — which is what the amended clause itself requires. It is red until `sdd-sync` lands the amendment, so its redness *is* the sync obligation's evidence rather than a promise | **RED until `sdd-sync`** → green after the CI-07 amendment lands (DC-5) |

Guard count: **7 new tests (G1–G7), 1 new helper (`_declared_pyright_version`), 1 new constant
(`_SKIP_DIRS`)**; no existing test is modified (SC-7). **G7 is the only new guard, and no existing guard's
assertions change**, because nothing in revision 1 asserted what revision 2 changed: G1 asserted `stubPath` and
**never** `mypy_path` (COR-1); no guard asserted `metadata.py` (COR-2 — retired, no edit) or `_converters.py`
(COR-3 — a runtime diagnostic, proven by SC-4c, not by a static guard); and no guard read
`[tool.mypy] python_version` before G7 (COR-4/R10).

---

## 9. Verify plan SC-1…SC-8

Every command is run from the repository root. Outputs are pasted verbatim into the verify report
(`openspec/changes/2026-09-15-chore-type-gate-policy/verify-report.md`); this design states the expected
value so a mismatch is a finding, not a judgement call.

| SC | Command(s) | Expected output | Proves |
| --- | --- | --- | --- |
| **SC-1** | `uv run pyright; echo "exit=$?"` | `exit=0` and the summary line `0 errors, 0 warnings` pasted verbatim; no invocation anywhere passes `--warnings` (`grep -rn -- "--warnings" .github/ .pre-commit-config.yaml` → no match) | P SC-1: the gate is green and warnings do not fail it |
| **SC-2** | `uv run pyright --version`; `uv lock --check`; `grep -rn "1\.1\.414" .github/workflows/ \|\| echo "no workflow version literal"`; `find . -name pyrightconfig.json -not -path "./.venv/*" -print \| wc -l` | `pyright 1.1.414` equals the derived dev pin; `uv lock --check` exits 0; `no workflow version literal`; `0` | P SC-2: single pin, single config home, no workflow literal, lock current |
| **SC-3** | **(a) red-first probe:** `printf 'probe: int = "not an int"\n' > src/sofer/_type_gate_probe.py`, `uv run pyright; echo "exit=$?"`, `rm src/sofer/_type_gate_probe.py`, `uv run pyright; echo "exit=$?"` | first run `exit=1` with a `reportAssignmentType`/`reportInvalidTypeForm`-class error naming `src/sofer/_type_gate_probe.py`; second run `exit=0` with no probe in the output; `git status --porcelain` empty afterwards | the gate is **real** (P SC-3 first half) |
| **SC-3** | **(b) `tests/` is out:** `printf 'probe: int = "not an int"\n' > tests/type_gate_probe.py`, `uv run pyright; echo "exit=$?"`, `rm tests/type_gate_probe.py` | `exit=0` and `tests/` (the probe path) absent from the output. Informational only, **not** a pass/fail criterion: also record `uv run pyright tests/ > /tmp/pyright_tests.txt; echo "exit=$?"` to document the pinned version's behaviour when a file is named explicitly on the command line — the guarantee that matters is the bare invocation plus G4's `exclude` assertion | `tests/` is out of the gate (P SC-3 second half) |
| **SC-3** | **(c) stub and artifact isolation:** `uv run python -c "import importlib.util; print(importlib.util.find_spec('tomli'))"`; `uv build`; `uv run python -c "import glob, zipfile; w = sorted(glob.glob('dist/*.whl'))[0]; print(sorted(n for n in zipfile.ZipFile(w).namelist() if 'typings' in n or n.endswith('.pyi')))"`; `uv run python -c "import glob, tarfile; t = tarfile.open(sorted(glob.glob('dist/*.tar.gz'))[0]); print(sorted(n for n in t.getnames() if 'typings' in n))"`; `rm -rf dist` | `None`; `[]`; `[]` (the wheel probe prints an empty list, the sdist probe prints an empty list) | §4.2/§4.4: the stub is not importable at runtime and ships in neither artifact (DC-3) |
| **SC-4** | `uv run mypy src/ scripts/; echo "exit=$?"`; paste of the two mypy invocation lines (`grep -n "mypy" .github/workflows/ci.yml .pre-commit-config.yaml`) | `exit=0` with `Success: no issues found in 33 source files`; both lines unchanged and neither names `tests` | P SC-4: the six mypy diagnostics (§5.1 sites 1–5 **plus the dual site 6**) are cleared under `strict = true`, `tests/` still excluded. BL §8.1's six-error baseline is the pre-state: composition differs (`metadata.py:239` gone, `_converters.py:620` added) but the count does not |
| **SC-4b** | `uv run --with "huggingface-hub==0.26.0" python -c "from huggingface_hub.errors import RepositoryNotFoundError; print('ok')"` (needs network; ephemeral env, `uv.lock` untouched) | `ok` | §5.1 site 4's re-verification against the declared floor. If it fails, apply takes the documented fallback (per-line ignores) and records it |
| **SC-4c** (A3) | **dual-gate proof for `_converters.py:611/620`** — (i) sensitivity probe: temporarily restore the revision-1/current state (`raw_rows: list[list[object]]` at `:611` **and** `vals: list[object] = …` at `:614`), run `uv run mypy src/ scripts/; echo "exit=$?"` and `uv run pyright; echo "exit=$?"`; (ii) apply the frozen form (`raw_rows: list[Sequence[object]]` at `:611`, `:614` unannotated) and re-run both | (i) **both** checkers exit non-zero and name `_converters.py` — mypy `[assignment]`/`[arg-type]`, pyright `reportAssignmentType`/`reportArgumentType` — proving the annotation only **relocates** the diagnostic; (ii) both exit 0 with **no** `_converters.py` diagnostic anywhere in either output; afterwards `git status --porcelain` shows only the intended change | BL §8.1/§8.6 + DC-10: the frozen edit is the **one** edit that satisfies both checkers, and the rejected variant satisfies neither. Paste both runs, including the mypy note that recommends `Sequence` |
| **SC-5** | `uv run pytest tests/ -q`; `uv run coverage run -m pytest`; `bash scripts/check_core_coverage.sh`; `uv run coverage report -m`; `uv run ruff check src/ tests/ scripts/`; `uv run ruff format --check src/ tests/ scripts/` | the suite's passed/skipped tally is **not reduced** vs BL §8.4's `1785 passed, 6 skipped, 1 warning` and vs the pre-change run apply records in step 0 (re-derive it on the branch, never trust a stored number); `check_core_coverage.sh` exits 0 with **four** 100.00% rows and an empty `Missing` column for `cli.py`, `scanner.py`, `prepare.py`, `publish.py`; `coverage report -m` ≥ 90; ruff clean in both modes | AGENTS rule 14 four-row re-run + P SC-5 (`tests/` untouched by the change) |
| **SC-6** | `git diff --stat openspec/specs/` (after `sdd-sync`); `git diff openspec/specs/ci/spec.md`; `grep -n "CI-09" openspec/specs/ci/spec.md`; `git diff --stat openspec/specs/process-boundary/spec.md` | only `ci/spec.md` changes: the **additions** (CI-09 block + its 5 rows) **plus exactly the two CI-07 occurrences** of §6.6 with their `(Previously: …)` marker and `> Modified by …` line — nothing else; CI-01..CI-06, CI-08 and the `## Purpose` enumeration byte-identical; PB-07/PB-14 untouched | P SC-6: the durable record exists, and the amendment's blast radius is the one clause the maintainer's decision made stale |
| **SC-6b** | read `CONTRIBUTING.md` §Type checking + command list; `diff <(sed -n '/^## Quality gates/,/^## Related/p' README.md) <(sed -n '/^## Controles de calidad/,/^## Referencias/p' README_ES.md)` (eyeball the bullet count/order) | the section names both commands, states the `tests/` exclusion, contains no false posture claim; both READMEs carry the mirrored bullet in the same position | D9/D13 documentation truth (CI-06-S3/PB-05 static-evidence dialect) |
| **SC-6c** (A4) | **CI-07 amendment evidence** — `git diff openspec/specs/ci/spec.md`; `grep -n 'python_version' openspec/specs/ci/spec.md`; `grep -c '"3\.10"' openspec/specs/ci/spec.md`; `grep -n 'Modified by .2026-09-15-chore-type-gate-policy' openspec/specs/ci/spec.md`; `grep -n '`[tool.mypy] python_version`' pyproject.toml openspec/specs/ci/spec.md` | the diff shows **exactly two CI-07 modifications** (the clause + the scenario bullet) plus the new `(Previously: …)` paragraph and the `> Modified by …` line, and nothing else in CI-07; `python_version` in CI-07 reads `"3.11"` and equals `pyproject.toml`'s value; `grep -c '"3\.10"'` prints **0** (every surviving `3.10` mention is backticked prose — the retired `.python-version` rationale and the test matrix — and that is correct); CI-07's `.python-version`/`3.13` clauses and all four other scenario bullets are byte-identical | DC-11 + BL §8.5 #1: the stale clause is amended in this change, its scope is proven by the diff, and CI-07's existing Test Mapping row (`User-facing support is unchanged — verify-phase static evidence`) is re-satisfied by this read, so **no new CI-07 row** is added |
| **SC-7** | `uv run pytest tests/test_ci_workflows.py -q` and paste the count; the red-then-green log captured in step 1 and the post-sync run captured in step 6 of §13 | the module's tally increases by **exactly 7** with no pre-existing test modified; the recorded pre-config red state shows G1, G3, G4 failing and G2, G5, G6 passing; and G7 is red **before** `sdd-sync` and green **after** it (DC-5) | P SC-7 corrected: guards exist, hold no version literal, and the red-first set is the honest one — three guards red before the config/step/docs land, one red until sync, three tripwires |
| **SC-8** | `git diff --stat` review; `grep -rn "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py \|\| echo "none"`; `git diff --stat .github/workflows/release.yml pyproject.toml` (floor lines only) | no `# pragma: no cover` added (the four rule-14 modules report `none`); no `fail_under` edit, no CI matrix change, no `release.yml` change, no `openspec/project.md`/`openspec/config.yaml` edit | P SC-8: the change adds no coverage leniency and touches no unrelated surface |

---

## 10. Rollback and workload forecast

### 10.1 Rollback — one commit shape, four documented partial reverts

**Apply lands the work as a single commit** (or a single linear stack squashed before the PR) whose revert
restores the pre-change tree exactly. The change is additive, so rollback is a revert, not a migration:

1. **Whole-change revert** (`git revert <commit>`): config, stub, sources, gates, guards, docs and the
   spec delta all go back together. The **one coupling that does not revert cleanly** is the maintainer's
   `strict = true`: reverting this change means either reverting that edit too or accepting a red mypy gate.
   The design states the coupling; apply records it in the PR body (P §12 item 5).
2. **Hook-only revert** (if R11 fires — Node unavailable on a contributor machine): delete the
   `.pre-commit-config.yaml` `pyright` entry, keep CI-09 S2's CI step, and record a CI-only posture with the
   divergence from AGENTS rule 5 stated explicitly. AGENTS rule 5's roster reverts to mypy-only in the same
   revert.
3. **Gate revert:** delete the `ci.yml` step + the `[tool.pyright]` block; the guards and the CI-09 delta are
   reverted with them in the same commit, so no requirement asserts a gate that does not exist.
4. **Pin revert:** drop the `pyright==1.1.414` dev entry and regenerate `uv.lock`. No runtime impact —
   nothing in `src/` imports pyright.
5. **Source revert:** every `src/` edit is type-only or comment-only, except the `_converters.py` loop
   restructure (site 7) and the `Sequence[object]` container fix (site 6), both behaviour-preserving by
   construction (§5.1 site 6, §5.2 site 7), each reverting independently — covered by the existing converter
   tests either way.
6. **Docs/docs-adjacent revert:** CONTRIBUTING/AGENTS/README×2/PR-template are independent of the gates
   **except** for G4, which asserts them; reverting a doc alone turns G4 red by design (that is the record
   working).

### 10.2 Workload forecast and PR boundary

| File | Change | Est. lines |
| --- | --- | --- |
| `pyproject.toml` | `[tool.pyright]` block + rationale comment; `[tool.hatch.build.targets.sdist]` exclusion — **`mypy_path` dropped** (COR-1) | +17 / −1 |
| `typings/tomli-stubs/__init__.pyi` | new stub (§4.1), pyright-only consumer | +14 |
| `.github/workflows/ci.yml` | one `lint`-job step | +2 |
| `.pre-commit-config.yaml` | second `repo: local` hook entry | +7 |
| `src/sofer/` (8 files, §5.3) | 1 container-type fix + `collections.abc` import + 1 loop restructure + 3 annotations/coercions + 2 comments + 1 import path | 15 changed (≈ +9 / −6) |
| `tests/test_ci_workflows.py` | `_declared_pyright_version` + `_SKIP_DIRS` + G1–G7 | +125 … +185 |
| `CONTRIBUTING.md` | §Type checking replaced; +1 command-list line | +18 / −2 |
| `AGENTS.md` | rule 5 roster/push line; rule 12 cross-reference sentence | +3 / −2 |
| `README.md` + `README_ES.md` | one mirrored bullet each | +12 |
| `.github/PULL_REQUEST_TEMPLATE.md` | verification block line + checklist item | +3 |
| `openspec/specs/ci/spec.md` (via `sdd-sync`) | CI-09 block + 5 rows; **CI-07's two amended occurrences + `(Previously: …)` marker + `> Modified by …` line** | +60 … +90 |
| `pyproject.toml` + `uv.lock` — **maintainer-authored, already in the tree** (BL §8.5 #2–#3) | `[[tool.mypy.overrides]]`, `numpy<2.3`, `datasets>=5.0.1`, `types-openpyxl`, `types-pyyaml`, `pyright==1.1.414`; lock regenerated | ≈ +12…+20 config, +40…+120 mechanical lock — **not produced by apply** |
| SDD artifacts (proposal, explore, evidence, design, tasks, spec delta, verify report) | not source | +300 … +500 |

**Apply-authored code + config + tests ≈ 205–275 changed lines** (8 source files touched, no `publish`/`site`
surface), plus the maintainer-authored `pyproject.toml` + `uv.lock` edits already in the tree (≈ +12…+20
config, +40…+120 mechanical lock) and the CI-09/CI-07 spec additions — roughly **17–29 % of the 1500-line
review budget**. **Delivery decision stands: single PR, no chaining, no `size:exception`, no `ask-on-risk`
pause.** The dominant review loads are the guard block (now seven guards) and the `[tool.pyright]` lines; both
are bounded, and the forecast does not move if DC-8's fallback step 1 is taken (a file rename) or if the
SC-4b floor probe forces site 4's per-line-ignore fallback (+2 comment lines).

---

## 11. Dispositions of EX §9's open items

| ID | Disposition |
| --- | --- |
| **O1** | **Retired** — BL §2/§3 name the `standard`-only error (`_converters.py:650`, `reportPossiblyUnboundVariable`); §5.2 site 7 fixes it |
| **O2** | **Closed by BL §7** — with the pinned version and the committed config the gate reports `13 errors / 0 warnings`; the no-config `1088 warning` row is not the gate's composition, because the gate always runs under the committed config (D3/D4). D2 stands: errors-only exit, rule bindings declared at `error` |
| **O3** | **Settled `src/ scripts/`** — `scripts/` measures 0 errors in every mode (BL §2, §7) |
| **O4** | **Answered from the lock** — pyright 1.1.414's declared dependencies are `nodeenv` and `typing-extensions` (`uv.lock:2637-2639`): Node provisioning is a hard dependency, not an extra. Residual risk = first-run download if Node is absent locally → R11 |
| **O5** | **Adjudicated as non-blocking**: D10 does not depend on the answer — the enforcement is the runtime `uv run pyright --version` equality (SC-2), which holds whether or not a config key exists. If the pinned version does expose a version-pinning key, apply adds it to the same block (additive) and G5 extends one assertion; no decision changes |
| **O6** | **Closed by BL §7** — baselines re-measured with the pin: `src/` 13 errors / 0 warnings, `scripts/` 0, `tests/` 119 (excluded), `uv run pyright --version` → `pyright 1.1.414` |
| **O7** | **Settled `pythonVersion = "3.13"`** (D11, §3) |
| **O8** | **Settled hook-inclusive** (D12, §7.2) with the R11 rollback (§10.1 item 2) |
| **O9** | **Settled: the bullet names both checkers** (D13, §7.3) |
| **O10** | **Settled: one requirement CI-09** with two clause groups and five scenarios (§6) |
| **O11** | **Settled: `typings/tomli-stubs/__init__.pyi` + `stubPath = "typings"`**, with the ordered fallback chain (DC-8, §4.5) |
| **O12** | **Settled: PB-07 is cross-referenced from CI-09 S1, never edited** (§6.1/§6.3) |

---

## 12. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| **R1** | Baseline identity (npm 1.39.9 vs the pinned distribution) | — | **Retired** by BL §7: the pin is live and the baselines are re-measured with it |
| **R2** | The `standard`-only error being systemic | — | **Retired**: it is one local defect (BL §2/§3), fixed in §5.2 site 7 |
| **R3** | The pinned pyright rejecting the stub-package layout | Low | DC-8's ordered fallback: mirror layout → five per-line ignores (the last step is a CI-09 text amendment, so it is an escalation, not a silent swap) |
| **R4** | Node requirement for the local hook | Low | **Mitigated by evidence**: the PyPI wrapper declares `nodeenv` (`uv.lock:2637-2639`) and provisions Node itself; CI runners ship Node. Rollback: §10.1 item 2 |
| **R5** | Stale `# pyright: ignore[...]` comments after a typeshed/openpyxl upgrade (`warn_unused_ignores` cannot see them) | Low | The verify report records the `"N errors, M warnings"` summary each run, so drift is visible. `reportUnnecessaryTypeIgnoreComment` at `warning` severity is **deliberately not** declared in the frozen block — it would add an unbound key; a future change may add it as a visible non-failing rule |
| **R6** | A broad `uv.lock` diff inflating review load | — | **Retired**: the lock is already regenerated in the tree; SC-2 only re-checks `uv lock --check` |
| **R7** | `CONTRIBUTING.md` edits straying into #187's `ruff.toml` claim or #212's command list | Low | Scope-explicit in §7.1: only the type-checking section is replaced (+1 added command line); `ruff.toml` sentence, the `mypy src/` path text and the version tables stay for their owners |
| **R8** | The hook slowing every commit | Low | Bare `uv run pyright` over a 33-file scope; accepted as the cost of a real gate (D12) |
| **R9** | Revision 1's five implied `tomli` diagnostics (OBS-1) | — | **RETIRED (COR-1)**: the premise was false (`ignore_missing_imports = true`, BL §8), so `mypy_path` is dropped and `[tool.mypy]` gains nothing. Residual variant, still live: if apply's step-0 pre-flight shows a mypy diagnostic **outside** the six sites of §5.1, apply resolves it with the §5 idioms and reports the addition — never a pragma, never a config relaxation |
| **R10** | CI-07's canonical text asserted `[tool.mypy] python_version = "3.10"` while the tree declares `"3.11"` (OBS-6) | Med → **resolved** | **RESOLVED by DC-11/A4**: the clause and its own restatement are amended in this change (frozen wording §6.6), the reason (maintainer decision, BL §8.5 #1) and the exact scope are recorded, and **G7** enforces config/clause agreement so the drift cannot silently return. Residual process risk: the exception must not read as a general licence to edit CI-01..CI-08 — §14 restates the non-goal **with** the carve-out |
| **R11** | A contributor without Node (and offline) cannot commit | Low | §10.1 item 2 (hook-only revert, CI-only posture recorded with the AGENTS rule 5 divergence); `CONTRIBUTING.md` §Type checking states the `uv run` requirement |
| **R12** | CI-07's clause "the diff SHALL contain zero `pyproject.toml` paths and zero `.github/workflows/` paths" reads as if it were a **standing** constraint — and this change's diff necessarily touches both (the `[tool.pyright]` block, the `ci.yml` step), which a literal reading would flag | Med (interpretation, not code) | **Recorded, not silently reinterpreted**: §6.6 leaves that clause **byte-identical** as instructed and adds a scope note to the delta's `## Cross-referenced and deliberately untouched` section — the clause is evidence recorded for #178's own change (where the pin moved and nothing else did), not a standing ban on ever touching `pyproject.toml`/workflows, since CI-09 itself requires a `ci.yml` step. The tension is surfaced to the maintainer in this phase's return so the reading can be settled explicitly in a follow-up if wanted. Do **not** dress this up as an amendment: only the `python_version` clause is authorized |

---

## 13. Apply sequence (ordered, with the red-then-green evidence captured)

| Step | Action | Evidence captured |
| --- | --- | --- |
| **0. Pre-flight** | `uv run mypy src/ scripts/`, `uv run pyright --version`, `uv run pytest tests/ -q` on the untouched tree; paste all three | the **real** diagnostic set — expected: 6 mypy errors with BL §8.1's composition (`metadata.py:239` absent, `_converters.py:620` present) and 13 pyright errors — the pin, and the pre-change suite tally. Step 0 is a **verification** of BL §8.1/§8.2 now, not a gate on any design choice (COR-1 removed the DC-2 contingency) |
| **1. Guards first** | add `_declared_pyright_version`, `_SKIP_DIRS`, G1–G7 to `tests/test_ci_workflows.py`; run `uv run pytest tests/test_ci_workflows.py -q -k "pyright or tests or gate_invocations or ci07"` | the **red state**: G1, G3, G4 failing, G7 failing (the canonical CI-07 is not amended until step 6); G2, G5, G6 passing (DC-5) |
| **2. Config** | `[tool.pyright]` + stub (§4.1) + sdist exclusion — **no `mypy_path`**; then `uv run pyright` | the 13 frozen pyright diagnostics reproduced under the committed config (proves mode/scope/interpreter/`stubPath` are the measured ones, and that `venvPath`/`venv` keep the import resolution explicit) |
| **3. Sources** | §5.1 sites 1–5 and §5.2 sites 6–17 (site 6 = the `Sequence[object]` container fix at `:611`, with `:614` unannotated) | `uv run mypy src/ scripts/` → 0 errors; `uv run pyright` → `0 errors, 0 warnings`; SC-4c's dual-gate probe pasted |
| **4. Gates** | `ci.yml` step + `.pre-commit-config.yaml` hook | G3 green |
| **5. Docs** | `CONTRIBUTING.md`, `AGENTS.md`, `README.md`, `README_ES.md`, PR template (§7) | G4 green; SC-6b |
| **6. Spec** | write the delta file (§6): the CI-09 block (§6.2–§6.4) **and the `## MODIFIED Requirements` section for CI-07 (§6.6)**; at `sdd-sync`, insert the CI-09 block + 5 rows at §6.5's anchors **and apply the two CI-07 occurrences** at §6.6's anchors | SC-6 and SC-6c; re-run `uv run pytest tests/test_ci_workflows.py -q` → **G7 green** (it was red through steps 1–5) |
| **7. Full verify** | SC-1 … SC-8 (§9) | the verify report |

---

## 14. Non-goals (restated for apply)

No `tests/` in either type gate. No coverage change of any kind — no floor movement, no
`# pragma: no cover` anywhere (forbidden in the four AGENTS rule-14 modules), no test-count weakening, no
`scripts/check_core_coverage.sh` or `fail_under` edit. **No `tomli` (or `datasets`, or any other) dependency
added beyond the pyright pin already in the tree** — and the maintainer's `datasets>=5.0.1` / `numpy<2.3` /
`types-*` / `[[tool.mypy.overrides]]` edits are **inputs, not deliverables**: apply neither adds nor removes
them. No mypy `strict` reversion or further tightening; **no `python_version` or `ignore_missing_imports`
change** (revision 1's `mypy_path` proposal is withdrawn, COR-1). No `pyright strict` campaign; no
`basedpyright` or analyzer substitution; no `pyrightconfig.json`; no version literal in any workflow. No CI
test-matrix or `release.yml` change. **No edit to CI-01..CI-06, CI-08, PB-07, PB-14, the `## Purpose`
enumerations, `openspec/project.md`, or `openspec/config.yaml` — and to CI-07 only the single clause (plus its
repeated bullet) frozen in §6.6, which is the one authorized exception (DC-11/COR-4), nothing else in that
requirement.** No absorption of #187, #212, #194, #215, or the CI-07 diff-scope tension (R12). No commit,
push, or PR from any SDD phase.

---

## Amendments after the guards-first work unit (COR-5, COR-6) — 2026-09-15

Recorded by the orchestrator after the Phase 1 (guards-first) work unit reported two things needing a decision.

### COR-5 — G7(b) vs the `(Previously: …)` marker: resolved as OPTION A

The conflict: G7(b) (frozen) asserts the retired double-quoted value `"3.10"` appears nowhere in CI-07's block, while §6.6's frozen `(Previously: …)` paragraph would itself contain `"3.10"`; SC-6c expects `grep -c '"3\.10"' openspec/specs/ci/spec.md` → 0.

**Resolution (A): keep G7(b) exactly as implemented and write the historical marker with a BACKTICKED value (`` `3.10` ``), not a double-quoted one.** Rationale: the strong, file-wide absence invariant is what makes the divergence class this change fixes mechanically detectable; weakening it to "exactly one occurrence" would reintroduce ambiguity about where that occurrence is. The repository's other `(Previously: …)` markers already write retired values as inline code, so this is convention-consistent. §6.6's frozen marker text is amended accordingly; SC-6c stays as frozen (`grep` → 0) and G7 must go green after `sdd-sync` lands the amendment. No change to G7(a).

### COR-6 — the mypy pin joins the single-authority discipline (maintainer instruction)

The maintainer instructed that the mypy-related changes be versioned the same way the other analyzers are. Current state: `[dependency-groups] dev` carries `mypy>=1.15.0` (floating) while `ruff==0.16.7` and `pyright==1.1.414` are exact, and `uv.lock` resolves mypy to **2.3.0**.

**Amended decision (extends D10 and G5):**
- `pyproject.toml` `[dependency-groups] dev`: `mypy>=1.15.0` → **`mypy==2.3.0`** (the resolved version), with `uv lock` refreshed in the same work unit.
- **G5 is generalized**: it SHALL assert that EVERY type/lint analyzer dev pin is exact (`==`) and equals its single resolved `uv.lock` version — mypy and pyright alike (ruff keeps its existing trio guard, `test_ruff_pin_hook_rev_and_required_version_agree`). The guard derives both versions from declarations; no literals.
- The CI-09 delta text and the CONTRIBUTING §Type checking wording SHALL name the pinned analyzers consistently (mypy 2.3.0 / pyright 1.1.414 derive from the declarations in prose, never from hardcoded numbers in code).
- Rationale: identical to #195's ruff decision — a floating range lets the analyzer version move under CI without any diff, which is exactly the drift class CI-08 closed for ruff; a pin makes the gate's behaviour reproducible and reviewable.

Note to COR-6: generalizing the guard also RENAMED it — `test_pyright_dev_pin_is_exact_and_matches_the_lock` → `test_analyzer_dev_pins_are_exact_and_match_the_lock` (it now covers mypy and pyright). This document's §6.3/§6.4 and `tasks.md` were updated to the new name; `explore.md` and `proposal.md` keep the historical name they recorded, since they are superseded records.


### COR-7 — the CI-07 Occurrence 1 join, settled before sync

The frozen replacement clause ends with a period ("…amend this clause in the same change.") while the canonical paragraph continues with ", the CI test matrix SHALL keep exercising `3.10`–`3.14`…", which would render as "same change., the CI test matrix". Sync SHALL therefore resolve the join as: the amended clause keeps its terminating period and the continuation opens a new sentence — "The CI test matrix SHALL keep exercising `3.10`–`3.14`, the TOTAL coverage floor SHALL remain the config-owned `fail_under = 90` (CI-01), and the diff SHALL contain zero `pyproject.toml` paths and zero `.github/workflows/` paths." No other byte of the paragraph changes. (The worker correctly refused to author a reconstructed paragraph in the delta; sync owns the join.)

### COR-8 — the applied resolutions diverge from §5.2, and that is the correct outcome

Verify's W1 noted that the shipped resolutions at `_converters.py` (sites 6/7) and `mcp_server.py` (site 5) do not match §5.2's frozen sketch while the task list is marked complete. Adjudication: **§5.2 is superseded by measurement.**

- Site 6: DC-10 claimed the `vals: list[object]` binding annotation "merely relocates the diagnostic". Falsified on this tree — with that one annotation, `uv run mypy src/ scripts/` and `uv run pyright` both exit 0 and `Sequence` appears nowhere in `_converters.py`. The simpler edit ships.
- Site 7: resolved by the explicit `raw_rows = []` rebind rather than §5.2's sketch; pyright's `reportPossiblyUnboundVariable` is gone and the memory-hygiene intent is preserved.
- Site 5: resolved by the maintainer's `sys.version_info >= (3, 11)` gate, which prunes the stale arm statically instead of relying on the stub — and which is what the corrected "four `try:` / `except ImportError:` sites" wording across the delta, `AGENTS.md` and the stub docstring now describes.

No pragmatic consequence: every gate is green, G7 closed at sync, and the corrected wording was promoted (not the stale one). §5.2 stays in this document as the record of what was planned; `apply-progress.md` §6 is the record of what shipped.
