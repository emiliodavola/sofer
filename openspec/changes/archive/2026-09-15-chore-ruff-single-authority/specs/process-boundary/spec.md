# Delta for process-boundary

> **Change** `2026-09-15-chore-ruff-single-authority` (GitHub #195) · branch
> `chore/195-ruff-single-authority` · store **hybrid** (this file + Engram mirror under topic key
> `sdd/2026-09-15-chore-ruff-single-authority/spec`).
>
> **One sentence changes; everything else stays byte-for-byte.** `openspec/specs/process-boundary/spec.md:258`
> (PB-10's second body paragraph) ends with a sentence this change falsifies:
> *"The ruff version pin mismatch (pre-commit `v0.16.7` versus the environment's `0.16.0`) SHALL stay
> unaddressed here and SHALL be owned by issue #195."* This change **is** #195, so that sentence is
> replaced in place by the restatement below. PB-10's `:254` framing blockquote, its first body
> paragraph (`:256`), its "no new CI step" clause and its #194-ownership clause, its "Evidence for this
> requirement is command output …" tail, and all five of its scenarios (`:260-293`) are copied into this
> `## MODIFIED` block **verbatim**. Nothing else in PB-10 — and no other `process-boundary` requirement —
> changes.
>
> **The restatement carries no version literal** (no `0.16.7`, no `0.16.0`): the invariant lives in the
> requirement body, the value lives in the three declarations, and the guard required by `ci` CI-08 forces
> them equal. A spec literal would be a third place to forget a bump. Result: the count of clauses naming
> a version anywhere under `openspec/specs/**` goes **1 → 0**.
>
> **Boundaries this restatement is written to preserve.** (a) PB-10's "no new CI step" clause and its
> #194-ownership sentence stay verbatim. (b) The `:281-286` scenario *No CI gate was armed, and recurrence
> stays owned by #194* keeps asserting **zero** `format --check` invocations under
> `.github/workflows/**`; this change arms none — it adds no workflow file and no workflow step.
> (c) PB-10's blockquote claim ("Every scenario below is evidenced by command output rather than by a
> pytest assertion") stays true because this delta adds **no** PB-10 scenario; the three pytest-asserted
> guard scenarios of this change live in the `ci` delta under CI-08.
>
> **Domain hygiene (checked this phase).** `openspec/specs/process-boundary/spec.md` exists and was read
> before writing this delta (delta, not full spec); no other non-archived change carries
> `specs/process-boundary/` — the only active change directory in `openspec/changes/` is this one; this
> change has no legacy flat `openspec/changes/<change>/spec.md` to reconcile. The canonical file is **not**
> edited by this phase; it absorbs this delta at `sdd-sync`. The `ci` delta for this change (CI-08) is a
> separate file and is the only cross-capability reference this clause adds.
>
> **Proposal `Capabilities` section:** the proposal has none. Its `## Scope` items 6 and 7 name this
> `process-boundary` delta and the `ci` delta explicitly, so the two domains are proposal-supported rather
> than inferred here (reported as an assumption in the phase return).

## MODIFIED Requirements

### Requirement: Formatter integrity on a clean checkout (PB-10)

> Added by change `2026-09-14-chore-ruff-format-drift` (GitHub #177). Every scenario below is evidenced by command output rather than by a pytest assertion — the same framing this repository already uses for measured gate exit codes in the `coverage` capability (AGENTS.md rule 6).

The repository's Python sources and tests SHALL satisfy the project formatter: `uv run ruff format --check src/ tests/` SHALL exit 0 on a clean checkout, reporting zero files to reformat. Reaching that state SHALL be a formatting-only edit — exactly these six test files SHALL change (`tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`, `tests/test_mcp_registration.py`, `tests/test_profile.py`, `tests/test_publish.py`, `tests/test_splits.py`), no other path SHALL appear in the diff, and the edit SHALL NOT alter logic, assertions, imports or test behaviour. Because the formatter does not rewrite string contents, the two static contract guards keep their asserted strings.

The requirement SHALL be satisfiable with no new CI step: enforcement remains the local pre-commit `ruff-format` hook, which sees staged files only. It therefore SHALL NOT be read as closing the drift class — a formatter drift on files nobody stages can still return, and issue #194 owns both the decision to arm such a gate and that open gap. The ruff version SHALL have a single declared authority — the environment's dev dependency pin, `[tool.ruff] required-version`, and the pre-commit `rev` SHALL name the same version, asserted statically by the guard required by `ci` CI-08. Alignment SHALL remain a declaration-and-local-hook matter: it SHALL arm no CI step, and issue #194 SHALL retain ownership of the un-staged-file gap. Evidence for this requirement is command output, and the sibling gates SHALL remain green and unweakened (PB-05, PB-07, `ci` CI-01, `coverage` COV-06).

(Previously: the paragraph deferred the pin mismatch — `v0.16.7` hook versus `0.16.0` environment — to issue #195; change `2026-09-15-chore-ruff-single-authority` owns it, and no version literal remains in this spec.)

#### Scenario: Clean-checkout format check exits 0

- GIVEN a clean checkout with this change applied, no `--python` flag and no local formatting
- WHEN `uv run ruff format --check src/ tests/` runs
- THEN it SHALL exit 0 and report zero files to reformat
- AND `uv run ruff format --diff src/ tests/` SHALL emit no diff, so nothing is left to reformat

#### Scenario: Exactly the six test files changed

- GIVEN this change's diff
- WHEN `git diff --stat` is inspected
- THEN exactly the six named test files SHALL appear and no other path SHALL appear
- AND there SHALL be zero `src/sofer/`, zero `.github/workflows/`, and zero `pyproject.toml` paths

#### Scenario: Formatting-only — behaviour and asserted content preserved

- GIVEN the suite tally recorded immediately before the reformat
- WHEN `uv run pytest tests/ -q` runs after it
- THEN the passed/skipped/collected counts SHALL be identical and there SHALL be 0 failures
- AND `tests/test_ci_workflows.py` and `tests/test_coverage_contract.py` SHALL pass with their asserted strings unchanged — no logic, assertion, import, or test-behaviour edit SHALL be present

#### Scenario: No CI gate was armed, and recurrence stays owned by #194

- GIVEN `.github/workflows/**` before and after the change
- WHEN scanned for a `format --check` invocation
- THEN zero matches SHALL exist in both states and no workflow file SHALL appear in the diff
- AND enforcement SHALL remain the local pre-commit `ruff-format` hook on staged files, with recurrence owned by issue #194 rather than by any clause of PB-10

#### Scenario: Sibling gates stay green and unmoved

- GIVEN the change applied
- WHEN `uv run ruff check src/ tests/`, `uv run mypy src/`, `git diff --check`, and `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` run
- THEN each SHALL exit 0, the coverage script SHALL reach all four of its scoped gates with every row at 100.00% and an empty `Missing` column (`coverage` COV-06), and the TOTAL floor SHALL remain the config-owned `fail_under = 90` (`ci` CI-01)

---

## Scope boundaries this delta does not cross

| Surface | Treatment | Why |
| --- | --- | --- |
| PB-10's five scenarios (`openspec/specs/process-boundary/spec.md:260-293`) | Unchanged, evidence class unchanged | The correction is to one requirement sentence; PB-10's scenarios stay command-evidence shaped, so nothing is re-mapped or re-declared |
| PB-10 `:286` (#194 ownership) and its `:281-286` zero-invocation scenario | Unchanged, verbatim | This change arms no CI gate. `git grep -n "format --check" -- .github/workflows/` is verify-phase static evidence on top of the scenario's own scan; it must still return zero matches |
| `process-boundary` PB-01..PB-09, PB-11..PB-13 | Unchanged | No boundary contract, fixture, offline rule, or test-count anchor is affected by a declarative version-alignment change |
| `ci` CI-08 (new, this change) | Held in the sibling delta `specs/ci/spec.md` | The required guard is a static repository-shape contract, which `ci` already owns (CI-07 precedent, its `## Test Mapping` indexing `tests/test_ci_workflows.py`); PB-10 only *references* it |
| `ci` CI-01, `coverage` COV-01/COV-06, `packaging` PKG-06 | Cross-referenced, not modified | PB-10's sibling-gate clause names them; the version alignment moves no floor, no per-file mandate and no lock-refresh rule (PKG-06 already owns the `uv.lock` regeneration obligation this change discharges) |
| #187 (`CONTRIBUTING.md:77` names a nonexistent `ruff.toml`), #212 (documented gate commands narrower than CI), `openspec/project.md:82` and the `AGENTS.md` version statements | Out of scope, not absorbed | Named owners; this change adds only the version to `CONTRIBUTING.md:77`'s sentence, and edits neither SDD metadata file |
