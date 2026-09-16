# Proposal — `2026-09-15-chore-type-gate-policy`

> **Change** `2026-09-15-chore-type-gate-policy` · issue **#201** (*policy: decide whether `tests/`
> joins the mypy gate, and whether pyright is a gate at all*) · branch `chore/201-type-gate-policy`
> from `dev@8184ffb` · store **hybrid** (this file + Engram `sdd/2026-09-15-chore-type-gate-policy/proposal`).
>
> **Phase:** proposal. Inputs read directly: `openspec/changes/2026-09-15-chore-type-gate-policy/explore.md`
> (cited as **EX §n**) and `openspec/changes/2026-09-15-chore-type-gate-policy/evidence-type-gate-baseline.md`
> (cited as **BL §n**). No other file was consulted; every fact below is a citation of those two, and
> every measurement is the parent's shell-run evidence quoted from them, never re-derived here.
>
> **Status:** proposal complete, ready for design. Two decisions were **closed by the maintainer before
> this phase** and are *not* re-opened here: Q1 → **(a)** `tests/` stays excluded from the mypy gate and
> the decision is recorded durably; Q2 → **(c)** pyright is adopted as a **real** gate. This document
> settles the ten HOW choices the parent left open, maps issue #201's acceptance criteria, and names the
> one question that legitimately needs the maintainer.

---

## 1. Intent

Make the repository's type-checking posture **explicit, enforceable, and honest**. Today the posture is
three-way inconsistent:

1. **The documented contract is false.** `CONTRIBUTING.md:79-81` says "We use **mypy** in strict mode"
   while `pyproject.toml:79` declares `strict = false` (EX §2.1, EX §9.1 #1).
2. **A real analyzer runs with no authority at all.** pyright is configured **nowhere** in the repo — no
   `pyrightconfig.json`, no `[tool.pyright]`, no hook, no CI step (EX §2.2, BL §2). It nevertheless drives
   every editor and agent squiggle on this project (Engram #1236), so contributors and agents are held to
   a standard that no gate enforces and that no document records.
3. **The exclusion of `tests/` is silent.** `[tool.mypy] exclude = ["tests/", ".venv/"]` is an implicit
   policy with no rationale on record; `process-boundary` PB-07 only implies it in passing (EX §2.4).

The change closes all three: it gives each posture decision a **durable, testable home**, promotes pyright
from "ambient editor behaviour" to an **enforced second opinion beside mypy**, and resolves — as a
by-product — the already-committed maintainer edit that makes `strict = true` true in the tree.

Why now: issue #201 is the last open policy question of the type-checking recurrence set (#192, #194,
#195 are already resolved; #195/CI-08 shipped the single-authority pin discipline this change reuses). It
is also the cheapest time to do it — the measured pyright surface on `src/ scripts/` is **11 errors under
`standard`** (BL §2), i.e. a bounded, one-time cleanup, not a campaign.

## 2. Scope

### In scope

- Durable record of both closed decisions: new **additive** `ci` requirement **CI-09** + its Test Mapping
  rows (EX §3.1, §7).
- A committed `[tool.pyright]` config as the single config authority, with the decided mode, scope,
  exclusions, interpreter level and stub path.
- An exact `pyright==X.Y.Z` dev pin + `uv.lock` regeneration; one CI lint-job step; one local pre-commit
  hook entry.
- Resolution of the **11 `standard`-mode pyright diagnostics** on `src/` (BL §2) and of the **6 mypy
  `strict = true` errors** introduced by the maintainer's uncommitted edit (BL §1).
- New static guards in `tests/test_ci_workflows.py`; verify-phase runtime evidence.
- Documentation surfaces updated in the same change: `CONTRIBUTING.md` §Type checking (fixes the drift),
  `AGENTS.md`, `README.md` + `README_ES.md`, PR template.

### Out of scope (non-goals, strictly respected)

- **`tests/` joins neither gate.** No mypy `tests/` inclusion, no pyright `tests/` analysis (Q1 closed).
- **No coverage change of any kind:** no floor movement, no `# pragma: no cover` (forbidden in the four
  AGENTS rule-14 modules), no test-count weakening, no `scripts/check_core_coverage.sh` or `fail_under`
  edit. **No resolution may add `tomli` to the dev environment** (BL §4.1 — it would make `cli.py:467`
  unreachable on the 3.13 interpreter and permanently break the `cli.py` COV-06 100.00% row).
- **No `pyright strict` campaign** (578 errors, EX §5.1) and no new analyzer (`basedpyright` changes the
  rule catalogue and invalidates the measured baselines, EX §6.1).
- **No `openspec/project.md` rewrite** (stale throughout, EX §9.1 #3) and **no `openspec/config.yaml`
  contract** (gitignored local state, EX §3.1/EX §9.1 #5).
- **No absorption of #187** (the `CONTRIBUTING.md:75` `ruff.toml`-at-root claim and the `mypy 2.3.0` /
  `ruff 0.16.0` truth tables have owners) or of #212. Nothing else in `CONTRIBUTING.md` is rewritten: the
  edit is confined to the type-checking lines.
- **No CI test-matrix change and no `release.yml` change**; CI-01..CI-08, PB-07 and PB-14 are
  **cross-referenced, never edited** (EX §8).
- No commit, push, or PR from any SDD phase.

## 3. Inputs taken as given (not re-opened)

| Given | Source | Effect on this proposal |
| --- | --- | --- |
| Q1 → (a): `tests/` stays out of the mypy gate, decision recorded durably | EX header | §8 clause group A + guard G4 |
| Q2 → (c): pyright is adopted as a **real** gate, not advisory | EX header | §8 clause group B + guards G1-G3, G5 |
| The maintainer's uncommitted `pyproject.toml` edit (`strict = false` → `true`) **is part of this change** | parent handoff; BL §0 | §6: the change must resolve the 6 resulting mypy errors, and `CONTRIBUTING.md:81` becomes true rather than being edited to match a `false` |
| pyright is measured at 11 errors / 0 warnings on `src/` under `standard`; `scripts/` is clean in every mode | BL §2 | §4 decisions 1 and 3 |
| `publish.py:70` is one edit clearing **both** mypy `attr-defined` and pyright `reportPrivateImportUsage` | BL §1 (verified public path on hf 1.25.1) | §6 and §7 item 9 |

## 4. Settled decisions

Each row states the decision and a one-line rationale. "EX/BL" points at the evidence; the reasoning is
the proposal's own.

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | `typeCheckingMode = "standard"` | `standard` costs exactly **one** error more than `basic` — `_converters.py:650` (BL §2) — and that extra error is the only **real defect** either mode finds (BL §3), so `standard` buys the rule set that catches future regressions at the price of one genuine fix. |
| **D2** | Warnings SHALL NOT fail the gate; the gate command is **bare `uv run pyright`** (no `--warnings`) | pyright exits non-zero only on errors (EX §5.2), and the measured `src/` warning count is 0 under every configured mode (BL §2), so `--warnings` would bind an unenumerated failure mode; instead any rule we want to bind SHALL be declared at `error` severity in `[tool.pyright]`, and the measured `"N errors, M warnings"` summary is recorded as verify evidence so a future warning jump is visible without failing the build. |
| **D3** | Gate scope is **`src/ scripts/`**, declared in config via `include`, never on the command line | Matches the **enforced** mypy scope (`ci.yml:21`, `.pre-commit-config.yaml:22`, both `uv run mypy src/ scripts/`, EX §2.1) so "what type-checks in this repo" is one scope; `scripts/` measured 0 errors in every mode (BL §2), so the symmetry is free; declaring it in config keeps the `tests` exclusion enforceable exactly once (EX §5.3 shape A). |
| **D4** | Single config authority: `[tool.pyright]` in `pyproject.toml` immediately after `[tool.mypy]`, plus a guard asserting **no `pyrightconfig.json` anywhere in the tree** | pyright silently prefers `pyrightconfig.json` over `[tool.pyright]` (BL §4.3), so a stray file would silently re-open the drift class CI-08 closed; one file also puts both type-checker declarations side by side. |
| **D5** | The five `tomli` sites resolve via **one committed stub + `stubPath`**, not five per-line ignores | DRY, zero `src/` edits, and it keeps **`cli.py`** — an AGENTS rule-14 module — untouched (EX §4 rows 2-6); adding `tomli` to the dev group is already rejected (BL §4.1). The five-ignore route stays documented as the fallback if the pinned pyright rejects the stub layout (O11). |
| **D6** | `_converters.py:650` is **restructured**, not suppressed | It is the only real defect `standard` finds (BL §3): the `if "raw_rows" in locals(): del raw_rows` guard is replaced by an explicit per-iteration re-initialization (`raw_rows = []` at the top of the sheet loop), which removes the `locals()` test, removes the possibly-unbound read, and preserves the memory-hygiene intent — whereas an ignore would silence the one finding that justifies choosing `standard` over `basic` (D1). `_converters.py` is not a rule-14 module, so no pragma question arises. |
| **D7** | `prepare.py:445` and `publish.py:686` (`TextIO.reconfigure`) resolve as per-line `# pyright: ignore[reportAttributeAccessIssue]`, keeping the deliberate duck-typed runtime guard | Narrowing to the `cli.py:1609-1611` `isinstance(_, io.TextIOWrapper)` house pattern would fail `tests/test_prepare.py:1626-1657` and `tests/test_publish.py:2018-2052` (both inject a duck-typed `_FakeStdout`) **and** strand those rule-14 lines (BL §4.2); the ignore is comment-only, invisible to mypy, and therefore cannot trip `warn_unused_ignores` the way a `# type: ignore` could. |
| **D8** | `_converters.py:620` resolves by **annotating the binding** at `:614` (`vals: list[object] = …`) | Values are openpyxl cell scalars that the code already means as `object`; mypy misses the invariance only because it does not model openpyxl, while pyright resolves the real types (EX §4 row 1) — so the annotation is the strictly better typing, is one line, and is behaviour-neutral. |
| **D9** | Durable homes: **one** additive `ci` requirement **CI-09** carrying both decisions as separately-scenario'd clause groups, its **Test Mapping rows** appended to `openspec/specs/ci/spec.md:380-393`, **`CONTRIBUTING.md` §Type checking** rewritten (states the real posture, names both commands, adds pyright to the command list), and **`AGENTS.md` gets a line** (rule 5's pre-commit roster gains pyright; rule 12's latent-issue note gains a cross-reference that the five `tomli` sites are resolved by a stub, never by a dependency — rule 12's CI-07-asserted text is **not** weakened) | `ci` is the capability that already owns gate config/declaration truth (CI-01/06/07/08) and the one that indexes `tests/test_ci_workflows.py` in its Test Mapping, so the record lands where it is assertable (EX §3.1); **one** requirement rather than CI-09+CI-10 because it is a single policy question with two halves, and the archive insert is cheaper (EX §3.1, O10 closed); AGENTS needs its line because rule 5's "`ruff` … and `mypy` run on every commit" becomes **factually false** the moment a pyright hook lands (EX §3.1). |
| **D10** | Pin mechanism: an **exact `pyright==X.Y.Z` entry in `[dependency-groups] dev`** + regenerated `uv.lock`, with pin enforcement carried by **verify-phase runtime evidence** (`uv run pyright --version` must equal the derived pin) instead of a config key | The version then reaches CI through `uv.lock` — the ruff path, and the shape CI-08 S2 bans from workflows (EX §6.1/§6.2) — and pyright has **no `required-version` analogue** (BL §5), so the ruff trio (pin ↔ config ↔ hook rev) has no third leg here and the runtime equality proof takes its place. |
| **D11** | `pythonVersion = "3.13"` (the gate interpreter), **not** mypy's `3.10` minimum | pyright is a runtime-truth analyzer executing on the 3.13 gate interpreter, where `tomllib` is the live stdlib arm; mirroring `3.10` would flip the five measured `import tomli` errors into five `import tomllib` errors and demand a stdlib stub for a module that exists — the stub must target the genuinely-stale arm (BL §2, EX §5.3/O7). |
| **D12** | The local **pre-commit hook is added** (a second `repo: local` entry, `pass_filenames: false`, mirroring the mypy entry) | Q2 closed as "a **real** gate"; with CI-only the gate is not true where contributors actually work, and the mypy precedent puts both type checks on the same surface (EX §6.4). The Node-on-contributor-machines cost is a named risk with an explicit rollback (§11/R4). |
| **D13** | `README.md` + `README_ES.md` §"Quality gates and security scanning" gain **one mirrored bullet naming both mypy and pyright** | The section currently lists coverage + CodeQL and **never mentions mypy** (EX §9.1 #4), so adding pyright alone would be asymmetric; naming both closes O9 and satisfies AGENTS rule 13 (same commit, both files). |

Two supporting choices follow from the above and need no separate vote: the PR template gains **one**
Checklist item for the pyright gate (CI-06 S4 shape), and `PB-07` is **cross-referenced from CI-09's
text** rather than edited (EX §7.2, O12 closed) — its existing incidental clause *"New test helpers SHALL
be type-annotated even though mypy excludes `tests/`"* stays in force and is consistent with D9/Q1.

## 5. Issue #201 acceptance-criteria mapping

Issue #201 asks two policy questions and requires the answers to be decided, recorded, and made
enforceable. The five criteria below are the issue's acceptance set as carried by EX §1/§3/§7 and the
maintainer's closed decisions; each is mapped to the artifact that satisfies it.

| AC | Acceptance criterion | Satisfied by |
| --- | --- | --- |
| **AC1** | Decide whether `tests/` joins the enforced mypy gate — decision **closed: it does not**, and the exclusion stops being silent | **`openspec/changes/{change}/specs/ci/spec.md`** delta clause group A (CI-09 S1: `[tool.mypy] exclude` contains `tests/`; every mypy invocation in `ci.yml` and `.pre-commit-config.yaml` names `src`/`scripts` and never `tests`; `[tool.pyright] exclude` contains `tests`) + inline rationale comment beside `[tool.mypy]` + `CONTRIBUTING.md` §Type checking states the posture in prose |
| **AC2** | Decide whether pyright is a gate at all — decision **closed: adopted as a real gate** | **CI-09 clause group B** (S2: `[tool.pyright]` exists with the decided mode/scope/interpreter/stub path; one `ci.yml` lint-job step running bare `uv run pyright`; the local hook) + `[tool.pyright]` in `pyproject.toml` + `pyright==X.Y.Z` dev pin + guard **G3** |
| **AC3** | Record both decisions durably (not in prose alone) | **CI-09** itself — the next free additive requirement of `openspec/specs/ci/spec.md` (EX §2.4/§2.5 precedent COV-07) — plus its **Test Mapping rows**, plus the four doc surfaces of D9/D13 |
| **AC4** | Make the decisions enforceable, so the drift cannot silently return | Guards **G1-G6** in `tests/test_ci_workflows.py` (each assertion in §9) + the pyright analogue of CI-08's single authority (**G2**: no `pyrightconfig.json`; **G5**: one exact dev pin matching `uv.lock`; **G3**: no pyright version literal in any workflow) + verify-phase runtime evidence (green run, version equality, red-first failure, `tests/` untouched) |
| **AC5** | Adopting the new posture must not weaken what already holds | §2 non-goals, guarded by **G6** (existing gate invocations intact) and proven by success criteria SC-5/SC-6: `uv run mypy src/ scripts/` exits 0 **under the committed `strict = true`**, `uv run pytest tests/ -q` stays green, and `scripts/check_core_coverage.sh` still reports four 100.00% rows |

## 6. The mypy surface this change must also clear (maintainer's committed edit)

BL §0/§1: `strict = true` is already in the working tree and makes the enforced mypy gate **RED** with 6
errors in 5 files. Because the edit is part of this change, no success criterion of §13 can be met until
these are resolved. All six are type-only or comment-only; none changes runtime behaviour.

| # | Site | mypy code | Resolution (decided) |
| --- | --- | --- | --- |
| 1-3 | `_mirror.py:77` (`_is_convertible_entry(entry)`); `_clean.py:58` (`allowed_output_remotes(cfg, …)`); `_clean.py:183` (`clean_build(cfg, override)`) | `no-untyped-def` | Annotate the parameters: `entry: str` at `_mirror.py:77` (call sites pass remote strings — apply re-verifies the call sites); `cfg` annotated in `_clean.py` via a `TYPE_CHECKING`-guarded `SoferConfig` import, preserving the deliberate no-import-cycle-at-module-load intent the baseline records |
| 4 | `metadata.py:239` | `no-any-return` | Annotate the binding: `dumped: str = yaml.safe_dump(...)`, then `return dumped` |
| 5 | `publish.py:70` | `attr-defined` | Import from the **public** module: `from huggingface_hub.errors import RepositoryNotFoundError` — verified present on the installed hf 1.25.1 (BL §1) and to be re-verified against the declared floor `huggingface-hub>=0.26.0` in apply. **This single edit also clears pyright's `reportPrivateImportUsage`** |
| 6 | `mcp_server.py:691` | `no-any-return` | Annotate the binding: `payload: dict[str, Any] = _tomli.load(fh)`, then `return payload` — the same "annotate the binding" idiom the repo adopted for #198/#200 (Engram #1261 §5), now applied consistently at #4, #6 and D8 |

**Not touched by this change:** the `strict = true` value itself (the maintainer's edit is the input, not a
proposal decision), `python_version = "3.10"` (the minimum-language-level declaration, CI-07's clause),
`check_untyped_defs`, `ignore_missing_imports`, `warn_unused_ignores`, or the `exclude` list.

> **Conflict note (recorded, not hidden):** EX §8 lists "No mypy `strict = true` flip" as a non-goal, and
> EX §9.1 #1 treats the CONTRIBUTING drift as a documentation fix. Both statements were written **before
> the maintainer's edit landed in the tree**. The edit supersedes the first (there is no flip left to
> avoid); the second is **resolved by the code**, not by rewriting the doc to match `false`: after §6,
> `CONTRIBUTING.md:81` ("mypy in strict mode") is **true**. The design must not restate EX §8's superseded
> bullet.

## 7. The pyright surface this change must clear (`standard` mode, `src/`)

11 errors, 0 warnings (BL §2). Full resolution table with the rejected alternatives:

| # | Site | rule | Resolution (decided) | Rejected alternative |
| --- | --- | --- | --- | --- |
| 1 | `_converters.py:620` | `reportArgumentType` | `vals: list[object]` annotation at `:614` (D8) | per-line ignore — keeps the code under-typed for no gain |
| 2 | `_converters.py:650` | `reportPossiblyUnboundVariable` | restructure the `locals()`/`del` block (D6) | targeted ignore — silences the only real defect found |
| 3-7 | `cli.py:465`, `config.py:151`, `mcp_registration.py:128`, `mcp_server.py:687`, `model.py:411` | `reportMissingImports` (`tomli`) | one committed `tomli` stub + `[tool.pyright] stubPath` (D5) | (a) `tomli` in the dev group → **breaks CI** (BL §4.1); (b) five per-line ignores — the documented fallback, not the plan |
| 8-9 | `prepare.py:445`, `publish.py:686` | `reportAttributeAccessIssue` (`TextIO.reconfigure`) | per-line `# pyright: ignore[reportAttributeAccessIssue]` (D7) | `isinstance(_, io.TextIOWrapper)` narrowing → fails two duck-typed tests and strands rule-14 lines (BL §4.2) |
| 10 | `publish.py:70` | `reportPrivateImportUsage` | public import path (same edit as §6 #5) | per-line ignore — loses the free two-gate fix |
| 11 | `verification.py:66` | `reportMissingImports` (`datasets`) | one per-line ignore | stub (models `load_dataset`/`keys`/`__getitem__`/`len` for one call site — drift surface); dev dep (heavy; violates "no dependency beyond the gate") |

`reportMissingImports` **SHALL NOT** be globally disabled (the ignore is per-site, at the one optional
dependency).

## 8. Durable homes (what the spec delta will carry)

**`ci` spec — new requirement CI-09** ("Type-gate posture: `tests/` excluded from both gates; pyright
adopted as a real gate"), inserted between the `---` that closes CI-08 and the `## Test Mapping` heading,
carrying its own trailing separator; rows appended at the end of the existing table; the stale `## Purpose`
enumeration **deliberately left stale** (CI-07/CI-08 precedent, EX §2.4). Five scenarios:

- **S1 (Q1 record).** `tests/` is out of **every** enforced type gate: `[tool.mypy] exclude` contains
  `tests/`; every mypy invocation in `ci.yml` and `.pre-commit-config.yaml` targets `src`/`scripts` and
  never `tests`; `[tool.pyright] exclude` contains `tests`; the pyright gate is config-driven and invoked
  bare so the exclusion is declared once. Cross-references `PB-07` (not edited).
- **S2 (Q2 record).** pyright is a real gate: `[tool.pyright]` in `pyproject.toml` declares
  `typeCheckingMode = "standard"`, `include = ["src", "scripts"]`, `exclude` ⊇ `tests`, `pythonVersion =
  "3.13"`, `stubPath`; one `ci.yml` `lint` step runs `uv run pyright`; a local pre-commit hook runs the
  same; the committed tree exits 0.
- **S3 (warnings).** Warnings SHALL NOT fail the gate (D2): the gate's exit contract is errors only, no
  `--warnings` flag appears in any invocation, and any bound rule SHALL be declared at `error` severity.
  The measured `"N errors, M warnings"` summary is recorded as verify-phase evidence.
- **S4 (single authority + pin).** Exactly one config home (no `pyrightconfig.json` anywhere); the version
  reaches CI through `uv.lock` from an exact `pyright==X.Y.Z` dev pin; **no workflow declares a pyright
  version**; `uv run pyright --version` equals the pin (the enforcement pyright itself lacks).
- **S5 (no weakening).** Under the maintainer's `strict = true`, `uv run mypy src/ scripts/` exits 0; the
  coverage floors, CI matrix, `release.yml` graph and test counts are unchanged.

**Documentation surfaces (same change, per D9/D13):** `CONTRIBUTING.md` §Type checking + command list;
`AGENTS.md` rule 5 (pyright joins the pre-commit roster) and a rule-12 cross-reference; `README.md` +
`README_ES.md` gate bullet; `.github/PULL_REQUEST_TEMPLATE.md` Checklist item. Inline rationale comments
sit next to `[tool.mypy]` (why `tests/` stays out) and inside the new `[tool.pyright]` block (why this
mode/scope/interpreter), in the style of `pyproject.toml:63-66` — supplementary, never the record.

## 9. Guard plan — `tests/test_ci_workflows.py`

Six static guards, all **deriving** versions from the dev pin and holding no literal (CI-08 S1/S3 rule),
reusing `_read_text`, `_load_toml`, `_load_yaml`, `_find_step`, `_workflow`, `_DEV_ENTRY_RE`,
`_EXACT_PIN_RE` (EX §7.1). Each row is the guard and its exact assertion.

| Guard | Assertion |
| --- | --- |
| **G1** `test_pyright_config_declares_the_decided_posture` | `[tool.pyright]` exists in `pyproject.toml`; `typeCheckingMode == "standard"`; `include` covers both `src` and `scripts`; `exclude` contains `tests`; `reportMissingImports` is **not** globally disabled (`not in ("none", False)`) — asserts the **decision class**, not a mirror of the whole config, so adding a rule key later stays green |
| **G2** `test_pyright_has_exactly_one_config_home` | no `pyrightconfig.json` at the repo root **or anywhere in the tree** — the pyright analogue of "single authoritative version" |
| **G3** `test_ci_lint_job_runs_the_pyright_gate` | `ci.yml`'s `lint` job has a step whose `run` equals the decided bare invocation; **and** no workflow file contains a pyright version specifier (CI-08 S2 analogue) |
| **G4** `test_mypy_and_pyright_exclude_tests` | `[tool.mypy] exclude` contains `tests/`; **every** mypy invocation in `ci.yml` and `.pre-commit-config.yaml` names `src`/`scripts` and never `tests`; `[tool.pyright] exclude` keeps `tests` out; `CONTRIBUTING.md` documents the posture — the testable core of AC1 |
| **G5** `test_pyright_dev_pin_is_exact_and_matches_the_lock` | exactly one `pyright==X.Y.Z` entry in `[dependency-groups] dev` (derived via `_DEV_ENTRY_RE`/`_EXACT_PIN_RE`, tolerating an optional Node-provisioning extra) and the same resolved version present in `uv.lock` |
| **G6** `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates` | the mypy invocations in `ci.yml`/`.pre-commit-config.yaml` remain `uv run mypy src/ scripts/`; no `fail_under`/floor literal and no ruff version literal appear in any workflow; exactly one `ruff-format` hook entry — i.e. **importing the new gate left the existing gate declarations intact** (the AC5 guard) |

Plus the CI-06 S4-shaped **text** assertion for the PR-template Checklist item (folded into G6's file read
if the design prefers one fewer test).

**Verify-phase (runtime) evidence — belongs in the verify report, not in pytest** (CI-01 S2 / CI-08 S4
dialect):

1. `uv run pyright` → **exit 0**, with the pasted `N errors, 0 warnings` summary.
2. `uv run pyright --version` → equals the derived dev pin.
3. **Red-first proof the gate is real:** inject a transient type error in a scratch file **inside the gate
   scope** → the gate exits non-zero and reports it; remove it → exit 0.
4. **Proof `tests/` is out:** a deliberately broken file under `tests/` does **not** fail the gate, and no
   `tests/` file appears in the output.
5. `uv run mypy src/ scripts/` → exit 0 (post-§6, under `strict = true`); `uv run pytest tests/ -q` → green
   and unchanged; `bash scripts/check_core_coverage.sh` → four 100.00% rows.

## 10. Affected areas

| Area | Files | Change class |
| --- | --- | --- |
| Config | `pyproject.toml` (`[tool.pyright]` + rationale comment; `pyright==X.Y.Z` dev entry) | additive |
| Pin lock | `uv.lock` (dev-group closure + wrapper transitives) | mechanical |
| Gates | `.github/workflows/ci.yml` (+1 lint step), `.pre-commit-config.yaml` (+1 local hook) | additive |
| Stub (D5) | `typings/tomli-stubs/__init__.pyi` (new) | new file |
| Source — mypy strict | `_mirror.py`, `_clean.py`, `metadata.py`, `publish.py`, `mcp_server.py` | type-only |
| Source — pyright | `_converters.py` (2), `publish.py` (reconfigure ignore), `prepare.py` (ignore), `verification.py` (ignore) | type/comment-only |
| Guards | `tests/test_ci_workflows.py` (+6 guards, small helpers) | additive |
| Docs/spec | `openspec/changes/{change}/specs/ci/spec.md` (delta), `CONTRIBUTING.md`, `AGENTS.md`, `README.md`, `README_ES.md`, `.github/PULL_REQUEST_TEMPLATE.md` | additive + one drift fix |

## 11. Risks

| # | Risk | Severity | Mitigation / disposition |
| --- | --- | --- | --- |
| R1 | **Baseline identity:** the 11-error / 0-warning counts come from the local **npm** pyright 1.39.9, not from the pinned PyPI distribution (BL §2, EX §6.2) | Med | Re-measure with the pinned version **before** freezing the mode and the resolution table (O6); if counts move, re-derive the §7 table rather than assume. If `standard` grows to a systemic set, fall back to `basic` and record the mode choice as a decision with its rationale (EX §5.1) — never a silent weakening |
| R2 | The `standard`-only 11th error could have been systemic (5 × `reportRedeclaration` on the tomli/tomllib double imports) instead of one local fix | Low | **Retired:** BL §2 enumerates it — `_converters.py:650` `reportPossiblyUnboundVariable`, a single local defect, resolved by D6 |
| R3 | The stub route (D5) may not be accepted in the PEP 561 layout chosen for the pinned pyright | Low | Deterministic fallback already specified: five per-line `# pyright: ignore[reportMissingImports]` comments (comment-only, coverage-neutral, no pragma; `cli.py` stays R14-safe). Design confirms the layout (O11) |
| R4 | **Node requirement:** the PyPI wrapper needs Node at runtime, so the local hook turns a missing Node into a hard commit failure for contributors | Med | Prefer the wrapper's Node-provisioning extra when `uv lock` can express it (O4); document the requirement in `CONTRIBUTING.md` §Type checking; named rollback: drop the hook entry and record a CI-only posture (reverting D12) with the divergence from AGENTS rule 5 stated explicitly |
| R5 | Stale `# pyright: ignore` comments after a typeshed/openpyxl upgrade (`warn_unused_ignores` cannot see them) | Low | D2's recorded summary line makes drift visible; the design MAY additionally declare `reportUnnecessaryTypeIgnoreComment` at `warning` severity (visible, non-failing) — optional, not required by CI-09 |
| R6 | `uv.lock` regeneration produces a broad mechanical diff that inflates review load | Low | Bounded by precedent (CI-08); the diff is confined to the dev-group closure region plus the wrapper's transitives; see §12 |
| R7 | `CONTRIBUTING.md` rewrite strays into the #187-owned `ruff.toml`-at-root claim | Low | Scope-explicit: only the type-checking lines are touched; the `ruff.toml` sentence and the version truth tables stay for their owners |
| R8 | Adding a pyright hook slows every commit | Low | The hook runs bare `uv run pyright` over a 33-file scope; acceptable for a real gate (D12), and R4's rollback covers the worst case |

## 12. Rollback

The change is **additive**, so rollback is a revert, not a migration. Ordered by blast radius:

1. **Hook-only rollback** (R4 fires): delete the `.pre-commit-config.yaml` pyright entry, keep CI-09 S4,
   and record the CI-only posture with its rationale — `AGENTS.md` rule 5 wording reverts to mypy-only.
2. **Gate rollback:** revert the `ci.yml` step + the `[tool.pyright]` block; the decision record (CI-09 and
   the guards) is removed with it in the same revert, so no requirement is left asserting a gate that does
   not exist (guards are red-then-green by construction).
3. **Pin rollback:** drop the `pyright==X.Y.Z` dev entry and regenerate `uv.lock` — no runtime impact,
   since nothing in `src/` imports pyright.
4. **Source rollback:** every `src/` edit is type-only or comment-only (§6/§7); reverting them restores the
   pre-change bytes with **identical runtime behaviour**, so no behavioural rollback path is needed. The
   one exception is the `_converters.py:650` restructure (D6) — behaviour-preserving by design
   (re-initialization instead of `del`), covered by the existing converter tests, and revertible on its own.
5. **Not rollback-able independently:** the maintainer's `strict = true` edit. Reverting the change means
   either reverting that edit or accepting a red mypy gate; the design must state this coupling.

## 13. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | `uv run pyright` → **exit 0** on the committed tree, with the `N errors, 0 warnings` summary recorded; no `--warnings` flag anywhere |
| SC-2 | `uv run pyright --version` equals the `X.Y.Z` derived from the single exact dev pin, and the same version appears resolved in `uv.lock`; no workflow contains a pyright version literal; no `pyrightconfig.json` exists anywhere in the tree |
| SC-3 | Red-first proof: a transient type error inside `src/` fails the gate; a transient error under `tests/` does not, and no `tests/` file appears in the output |
| SC-4 | `uv run mypy src/ scripts/` → exit 0 under the committed `strict = true` (the 6 errors of §6 cleared), with `tests/` still excluded and never named in an invocation |
| SC-5 | `uv run pytest tests/ -q` green with **no reduction** in the collected/passed tally; `bash scripts/check_core_coverage.sh` reports the four rule-14 modules at **100.00%**; `uv run ruff check src/ tests/ scripts/` green |
| SC-6 | CI-09 is present in the canonical `ci` spec after `sdd-sync`, with its Test Mapping rows; CI-01..CI-08, PB-07 and PB-14 bytes unchanged; `CONTRIBUTING.md` names both gate commands and no longer contains a false posture claim; `README.md`/`README_ES.md` agree |
| SC-7 | Six static guards G1-G6 exist, are red before the change and green after, and hold no version literal (each derives it from the dev pin) |
| SC-8 | No `# pragma: no cover` added anywhere; no coverage floor, CI matrix, `release.yml`, `openspec/project.md`, or `openspec/config.yaml` edit in the diff |

## 14. PR boundary and workload forecast

**Boundary: one PR, no chaining, no `size:exception`, no `ask-on-risk` pause.** The change is a single
policy adoption whose record (spec delta), enforcement (guards, CI step, hook) and cleanup (11 pyright +
6 mypy diagnostics) are mutually dependent: guards for CI-09 cannot go green without the config, the
config cannot go green without the resolutions, and the standing SDD instruction requires the whole cycle
(including verify and archive) inside the PR. There is nothing coherent to defer — a "config-only" or
"guards-only" slice would leave the repo with either a red gate or a requirement asserting a gate that
does not exist.

| File | Change | Est. lines |
| --- | --- | --- |
| `pyproject.toml` | `[tool.pyright]` + rationale comments; `pyright==X.Y.Z` dev entry | +16 / −1 |
| `uv.lock` | dev-group closure + wrapper transitives | +40 … +120 (mechanical) |
| `.github/workflows/ci.yml` | one pyright step in `lint` | +4 … +6 |
| `.pre-commit-config.yaml` | second `repo: local` hook entry | +6 … +10 |
| `typings/tomli-stubs/__init__.pyi` | new stub (D5) | +10 … +20 |
| `src/sofer/` — mypy strict (§6) | 4 files: annotations, binding annotations, public import | 8 … 12 |
| `src/sofer/` — pyright (§7) | `_converters.py` ×2, `prepare.py` ×1, `publish.py` ×1, `verification.py` ×1 | 5 … 7 |
| `tests/test_ci_workflows.py` | G1-G6 + small helpers | +100 … +180 |
| `CONTRIBUTING.md` | §Type checking + command list; drift fixed | +6 … +10 / −2 |
| `AGENTS.md` | rule 5 roster + rule-12 cross-reference | +2 … +6 |
| `README.md` + `README_ES.md` | one mirrored gate bullet | +4 … +8 |
| `.github/PULL_REQUEST_TEMPLATE.md` | one Checklist item (+ verification line) | +2 … +3 |
| SDD artifacts (proposal, design, tasks, spec delta, verify report) | not source | +250 … +420 |

**Code + config + tests: ≈ 200–360 changed lines (≈ 240–480 including `uv.lock`)** — roughly **16-32 % of
the 1500-line review budget**, so the delivery decision stands: **single PR**. Dominant review loads are
the mechanical `uv.lock` region and the guard block; both are bounded, and neither grows if R1/R3 move the
forecast by tens of lines rather than hundreds.

## 15. Design-phase decisions (dispositions of EX §9's open items)

| ID | Disposition |
| --- | --- |
| O1 | **Retired** — answered by BL §2 (`_converters.py:650`); resolution decided in D6 |
| O2 | Carried to design: reproduce the three measured runs **under the committed `[tool.pyright]` config** and enumerate the no-config rule composition. D2 is already decided; this measurement becomes the recorded evidence that supports it |
| O3 | **Settled in favour of `src/ scripts/`** — BL §2 measures `scripts/` at 0 errors in every mode (D3) |
| O4 | Carried to design: does the pinned wrapper offer a Node-provisioning extra expressible in `uv lock`? Affects R4's mitigation, not the decision |
| O5 | Carried to design/apply: confirm the pinned version has no `required-version` analogue. D10 already assumes the answer; a surprise only adds a config key, it does not change the runtime proof |
| O6 | Carried to design: re-measure the baselines with the pinned distribution/version (R1). This gates the frozen §7 table and the final `standard`-vs-`basic` confirmation |
| O7 | **Settled: `pythonVersion = "3.13"`** (D11) |
| O8 | **Settled: hook included** (D12), with its rollback |
| O9 | **Settled: README/README_ES name both mypy and pyright** (D13) |
| O10 | **Settled: one requirement CI-09** with separately-scenario'd clause groups (D9) |
| O11 | Carried to design/apply: the accepted `stubPath` layout for the `tomli` stub; fallback = five per-line ignores (R3) |
| O12 | **Settled: PB-07 is cross-referenced from CI-09, never edited** (D9) |
| — | Design must also freeze: the exact pinned `X.Y.Z` value (latest stable at apply time, or deliberately the version the maintainer's harness already runs so editor and gate agree — R1 decides which is measurable), and the `_converters.py:650` restructure's exact shape |

## 16. Open questions genuinely needing the maintainer

1. **Local gate ergonomics (D12 / R4).** The decided design puts pyright in the pre-commit hook, which
   makes a **missing Node** a hard commit failure on a contributor's machine. Confirm hook-inclusive
   (default, mirrors the mypy precedent and makes "real gate" true locally) or CI-only (keeps local
   commits dependency-free and diverges from AGENTS rule 5's sentence). This is the maintainer's call
   because it trades contributor ergonomics against gate strength — not a technical unknown.
2. **Public posture on the README (D13).** The gate section is user-facing: confirm that advertising type
   checking publicly (both mypy and pyright) is wanted, rather than keeping the README roster to coverage
   and CodeQL. Content, not mechanics — and the only piece of the change a *reader* of the README sees.

No other item in §15 requires the maintainer: the remaining ones are measurements (O2, O4, O5, O6, O11)
that the design resolves with the pinned tool in hand, exactly as EX §9 assigns them.

## 17. Proposal question round

This proposal was shaped from the maintainer's closed decisions, not from a fresh interview. The questions
below are offered as a single review round — they exist to surface product intent and edge cases that
could still change the *shape* of the change (not its harness mechanics). Answer, correct, skip, or ask for
a second round.

1. **Business problem.** The stated pain is CI/editor divergence: pyright drives every squiggle while mypy
   is the only enforced gate, so contributors and agents are held to a standard nobody can see. Is that the
   whole pain, or is the deeper cost a specific class of defect that reached `dev` while both checkers were
   silent on it? The answer decides whether `standard` (D1) is sufficient or whether a rule must be
   promoted explicitly.
2. **Who is affected, and when.** The gate is felt at three moments — a contributor committing, CI on a PR,
   and an agent editing `src/`. Is the *first* moment (the hook, D12) actually wanted, or is the intent that
   the gate catches things at PR time and the local surface stays light?
3. **Edge cases the proposal could be over- or under-building.** `tests/` stays out of both gates (Q1), but
   the repo also carries optional-dependency and platform-guarded code paths that neither checker can model
   — today those are ignores. Is the intent that such paths stay permanently ignored (accepting comment
   drift, R5), or that each becomes a tracked item the first time an ignore is added?
4. **Scope boundary.** The change deliberately leaves the `README` gate roster aside from one bullet, and
   does not touch `openspec/project.md`. Confirm that keeping the broader documentation truth (version
   tables, `ruff.toml` path claim → #187) out of this PR is right, rather than draining it here while the
   type-gate documentation is being rewritten anyway.

**Assumptions carried unless corrected:** (a) pyright's purpose is a *second opinion beside mypy*, so
`standard` — not `basic` (weakest) and not `strict` (578 errors) — is the intended strength; (b) the
maintainer's `strict = true` edit is permanent intent, so the six diagnostics are meant to be fixed, not
the edit reverted; (c) `tests/` remains untyped by policy but test helpers still get annotations (PB-07's
incidental clause stays in force); (d) a daily-development gate may demand Node, i.e. contributor
ergonomics are subordinate to gate strength.

## 18. Non-goals (restated for the spec delta)

Recorded as the delta's explicit "Non-goals recorded by this change" block, per the COV-07 precedent
(EX §2.5): no `tests/` in either gate; no coverage floor / pragma / test-count change; no `tomli` (or
`datasets`, or any other) dependency added beyond the gate itself; no mypy `strict` reversion or further
tightening; no `pyright strict` campaign; no `basedpyright` or other analyzer substitution; no
`pyrightconfig.json`; no version literal in any workflow; no CI test-matrix or `release.yml` change; no edit
to CI-01..CI-08, PB-07, PB-14, or the `## Purpose` enumerations; no `openspec/project.md` or
`openspec/config.yaml` edit; no absorption of #187 or #212; no commit/push/PR from SDD phases.

## 19. Handoff to design

Design must: (1) freeze the pinned `pyright==X.Y.Z` and re-measure both baselines with it (O6/R1) before
freezing §7; (2) confirm O2, O4, O5, O11 — none of which can change D1-D13, only their evidence; (3)
translate §8's five scenarios into the CI-09 delta text with the archive append convention; (4) translate
§9's guards into red-then-green tests with derived versions and no literals; (5) freeze the exact
`_converters.py:650` restructure and the six §6 resolutions; (6) plan the verify report around SC-1..SC-8,
including the red-first probe and the `tests/`-untouched proof; (7) keep the superseded EX §8 bullet (mypy
`strict`) out of the delta, citing §6's conflict note instead.
