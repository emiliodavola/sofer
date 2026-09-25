# Design: `211-test-mapping-gate`

## Technical Approach

Build the **smallest honest mechanism** for rule 6 (option (b), settled by the maintainer): a
machine-readable prefix contract on the three existing `## Test Mapping` tables, a stdlib-only checker
under `scripts/` that enforces it, a committed registry that makes the uncovered set explicit and
checked, and one CI step in the existing `lint` job. No spec is swept, no test id is invented, no
existing evidence string is rewritten — rows are **re-tagged** with a single prefix.

The design maps to the three new capabilities:

- `test-mapping-contract` — the row grammar and the scope boundary (which specs the contract reaches).
- `mapping-checker` — enumeration, scenario↔row bijection, pytest collection of `test:` targets, the
  registry bijection, and the exit-code gate.
- `rule6-reword` — the honest rewrite of `AGENTS.md` rule 6 + `openspec/config.yaml` `rules.specs`, and
  the #214 absorption (delete the stale tally, do not update it).

## Scope Reconciliation — decision required before apply

The phase-2 instruction adds a **full scenario↔row bijection** ("every `#### Scenario:` in exactly one
row"). The approved proposal's checker contract is **row-level only** ("every data row's Verification
cell begins with exactly one prefix") and its out-of-scope list forbids spec content changes beyond the
Verification cells. These disagree, and the disagreement is measurable on this branch:

- `openspec/specs/process-boundary/spec.md` has **48 `#### Scenario:` headings** but its `## Test
  Mapping` table carries **2 rows** (PB-14 only). Its own prose says *"PB-01..PB-13 rows are not
  backfilled by this change: their evidence classes are stated in their own scenario text, and the
  backfill is a separate concern."* A full bijection would require adding ~46 rows and rewriting that
  paragraph — a spec prose change the proposal excludes.
- `openspec/specs/coverage/spec.md` carries a **COV-04 row** that names **no `#### Scenario:`**
  (it is the retired marker), which fails a "row names an existing scenario" rule.
- `openspec/specs/ci/spec.md` is 38 headings / 38 rows and appears 1:1, but only exact-text matching
  confirms it.

Two coherent resolutions:

| Resolution | Checker rule | Consequence |
|------------|--------------|-------------|
| **A — proposal-faithful (row-level)** | Every data row begins with exactly one prefix; every row's named scenario **exists** and is named by **at most one** row; rows need not cover every scenario | No table completion; `process-boundary` keeps its PB-14-only table and its deferral note; ~102-row re-tag only |
| **B — literal phase-2 (full bijection)** | Every `#### Scenario:` appears in **exactly one** row; every row names an existing scenario | Requires completing the `process-boundary` and `coverage` tables (add ~46 rows, drop/retarget the retired COV-04 row) and amending `process-boundary`'s deferral paragraph — a **scope expansion** beyond the proposal |

**This design is written to resolution B**, because that is the literal phase-2 instruction. Tasks 1.4
and 1.5 are the reconciliation work and SHALL be confirmed as in-scope by the maintainer before apply;
if resolution A is chosen, MC-02 relaxes to "unique row per named scenario" and tasks 1.4–1.5 are
dropped. This is the single open scope question for this change.

## Architecture Decisions

### Decision: Checker lives in `scripts/check_test_mapping.py`

**Choice**: a single stdlib-only Python script at `scripts/check_test_mapping.py`, runnable as
`python scripts/check_test_mapping.py` from the repository root, with an argparse surface exposing
`--repo-root` (default: resolved from the script location), `--specs-root` (default
`openspec/specs`), `--registry` (default `openspec/test-mapping-registry.md`), and
`--collect-only-cmd` (default derived from the running interpreter).
**Alternatives considered**: a shell script (rejected — Markdown table + TOML-ish parsing is a quoting
trap); a `tests/`-only static guard with no script (rejected — the CI gate must run without executing
the suite); a `src/sofer/` module (rejected — this is repository tooling, not shipped product).
**Rationale**: `scripts/` is already inside the enforced ruff + mypy scope, so the checker is held to
the same quality bar as `src/` (D6). `scripts/check_core_coverage.sh` is the precedent for a committed
gate script, and `scripts/update_citation.py` is the precedent for real Python under `scripts/`.
Module-level constants hold the default path roots and the prefix/CLI grammar (no in-body magic
strings); anything tool-wide and user-tunable is exposed as a CLI flag or, if it ever justifies it,
belongs in `[tool.sofer]` (AGENTS rule 1).

### Decision: `test:` collection uses `pytest --collect-only`, never test execution

**Choice**: resolve `test:` targets by running
`python -m pytest --collect-only -q -p no:cacheprovider <referenced files>` once per run — batched over
the **distinct referenced files** — and comparing the referenced node ids against the collected set.
Path-only references pass when the file yields ≥1 collected item; `path::name` references pass on exact
node-id membership.
**Alternatives considered**: AST/`def ` name scanning (rejected — misses parametrisation, decorators,
class methods, and import-gated collection, and re-implements pytest badly); executing the tests
(rejected — the gate must not run 1700+ tests, and "does it exercise the scenario" is not provable by
execution of the test alone); requiring every row to carry a full node id (rejected — the three
existing tables legitimately reference whole files such as `tests/test_ci_workflows.py`).
**Rationale**: collection is deterministic, offline, cheap, and exactly the honest limit R6-01 states —
**existence and collection, not exercise**. It also satisfies MC-03's wording ("collected by pytest")
without running a body. This resolves open question O3: the `::name` selector is **optional**, and the
matching rule is exact collected-node membership (not substring).

### Decision: Registry is a reason-only bijection, counts are re-derived

**Choice**: `openspec/test-mapping-registry.md` holds a two-column table `| Spec | Reason |`, one row
per unmapped spec, with the reason naming why it is unmapped and that it is a declared backlog entry.
No scenario counts are stored in the registry.
**Alternatives considered**: storing the measured scenario count per spec (rejected — it is precisely
the hand-maintained-figure class #214 files and the proposal's §3 drift re-proves: #211 measured 640/2,
this branch measures 659/3); a JSON/YAML registry (rejected — a Markdown table is human-reviewable in
the same renderer as the specs and needs no extra parser).
**Rationale**: the checker re-derives the count from `#### Scenario:` headings at check time and prints
it, so the number is always current and the registry cannot go stale. This resolves O2 (tree-derived,
not stored) and keeps D4's bijection as a pure set relation.

### Decision: One CI step in the existing `lint` job

**Choice**: add exactly one step to the `lint` job of `.github/workflows/ci.yml` (the job that already
runs `ruff`, mypy, and pyright), invoking the checker; its exit code fails the job.
**Alternatives considered**: a new dedicated job (rejected — D5: adds a matrix axis and wall-clock for
a sub-second static check); folding the check into `scripts/check_core_coverage.sh` (rejected — that
script's scope is the coverage gate and it runs in the `coverage` job; mixing concerns violates
AGENTS rule 10); a pre-commit hook only (rejected — a local-only gate is not a gate, and it would not
run in CI).
**Rationale**: mirrors the `scripts/check_core_coverage.sh` / CI-01 gate-exit-code precedent, adds no
matrix cost, and lands where the repository's other static gates already live.

### Decision: Empty rows are structural errors; scenario matching is exact text

**Choice**: parse Markdown tables with a small stdlib line parser that splits on `|`, recognises the
header/separator, and treats a line whose three cells are all whitespace as an **empty row** (fails).
Scenario↔row matching is exact `Scenario`-cell text against `#### Scenario:` heading text within the
same spec.
**Alternatives considered**: fuzzy/prefix matching (rejected — non-deterministic and would mask typos);
ignoring empty rows (rejected — `test-mapping-contract` TMC-04 declares them non-compliant).
**Rationale**: exact text is deterministic and catches drift; a typo becomes a visible row-vs-heading
mismatch rather than a silent pass. The heading convention is exactly `#### Scenario:` (four hashes),
which is what the proposal's measurement used; because only the three mapped specs are checked and they
all use that level, O4's concern about `data-quality` is moot for the gate (it is registry-only either
way).

### Decision: `verify:` is never resolved

**Choice**: the checker validates only that a `verify:` reference is non-empty; it does not resolve,
execute, or inspect the referenced evidence.
**Alternatives considered**: parsing the referenced evidence string for a known command (rejected —
reintroduces prose heuristics and false confidence).
**Rationale**: `verify:` is the declared escape hatch. The gate's job is to force the evidence class to
be **declared**, not to pretend a `verify:` row is proof (D2). This is the honest limit R6-01 must
state.

## Data Flow

    openspec/specs/*/spec.md ─┐
                              ├─► classify ──► mapped set ──► per-spec table parse
    openspec/test-mapping-registry.md ─┘              │              │
                                                     │              ├─ prefix (TMC-01)
                                                     │              ├─ ref grammar (TMC-02/03)
                                                     │              ├─ scenario↔row bijection (MC-02)
                                                     │              ├─ empty rows (MC-04)
                                                     │              └─ test: refs ──► pytest --collect-only
                                                     │                                   (no execution)
                                                     └─► bijection: mapped ∪ registry = all specs
                                                                      │ disjoint?
                                                                      ▼
                                              exit 0 (clean) / non-zero (offender list) ──► lint job

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `scripts/check_test_mapping.py` | Create | Stdlib-only checker: enumeration, table parse, prefix/reference grammar, scenario↔row bijection, pytest collect-only resolution, registry bijection, exit contract. Module + function docstrings per AGENTS rules. |
| `openspec/test-mapping-registry.md` | Create | Reason-only registry of the 17 unmapped specs; the checker's bijection partner. |
| `openspec/specs/ci/spec.md` | Modify | Re-tag every Verification cell with `test:` / `verify:` (evidence strings preserved). |
| `openspec/specs/coverage/spec.md` | Modify | Re-tag every Verification cell with `test:` / `verify:`. |
| `openspec/specs/process-boundary/spec.md` | Modify | Re-tag every Verification cell with `test:` / `verify:`. |
| `AGENTS.md` | Modify | Rewrite rule 6: prefixes, existence/collection limit, `verify:` escape hatch, registry; delete the stale tally (#214). |
| `openspec/config.yaml` | Modify | `rules.specs` aligned with rule 6; remove the stale `1029 tests` tally from `context`. |
| `.github/workflows/ci.yml` | Modify | One checker step in the `lint` job. |
| `tests/test_test_mapping_checker.py` | Create | Checker behavior tests driven through its CLI on temp fixture trees + one real-tree integration run. |
| `tests/test_ci_workflows.py` | Modify | Static guard: `AGENTS.md` rule 6 and `config.yaml` `rules.specs` agree on the contract terms; CI lint job runs the checker; no stale tally remains. |
| `openspec/changes/211-test-mapping-gate/**` | Modify | This change's own SDD artifacts (proposal/specs/design/tasks/verify). |

## Interfaces / Contracts

### Registry format

```markdown
# Test Mapping Registry

Specs without a `## Test Mapping` section ... (checker-enforced bijection; scenario counts are
re-derived at check time, never stored).

| Spec | Reason |
| --- | --- |
| cli | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| ... | ... |
```

The registry is parsed by the same table parser as the spec tables; the `Spec` cell is the spec's
directory name under `openspec/specs/`.

### Checker CLI

```text
python scripts/check_test_mapping.py [--repo-root PATH] [--specs-root PATH]
                                     [--registry PATH] [--collect-only-cmd CMD]
```

Exit 0 on a clean tree; non-zero with a full offender list otherwise. `--repo-root` defaults to the
repository root resolved from the script path; the remaining defaults are `openspec/specs`,
`openspec/test-mapping-registry.md`, and the running interpreter's `-m pytest --collect-only`.

### Row grammar (enforced against `test-mapping-contract`)

```text
Verification cell := "test:" test-ref | "verify:" verify-ref
test-ref          := <repo-relative POSIX path> [ "::" <test-name> ]     (non-empty)
verify-ref        := <non-empty artifact reference>                       (never resolved)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Checker rules: prefix, ref grammar, empty rows, scenario↔row bijection, registry bijection, exit codes | `tests/test_test_mapping_checker.py` invokes the script as a **subprocess** (`sys.executable scripts/check_test_mapping.py --repo-root <tmp>`) against temp fixture trees, asserting exit code + named offender. No import hackery, no `sys.path` mutation. |
| Integration | Real tree is clean; registry bijection holds; `test:` targets collect | One subprocess run against the repository root asserting exit 0; and the `::name` collect-only path exercised against a real test node. |
| Static | Rule 6 / `rules.specs` agreement; stale tally absent; lint job step present | `tests/test_ci_workflows.py` text/YAML inspections (the established home for repository-shape contracts). |
| Gate | Checker green in CI | Verify-phase runtime evidence: the `lint` job step's exit code pasted into the verify report (CI-01 precedent). |

Checker tests assert **observable outcomes only** (exit code, reported offender) per COV-05; no test
asserts a coverage percentage, and no test executes a test body to make the checker pass.

## Threat Matrix

The only new process-integration boundary is the checker spawning pytest for collection. Applicable
rows:

| Boundary | Risk | Mitigation | RED test |
|----------|------|-----------|----------|
| Subprocess invocation | Command injection / shell metacharacters in a referenced path | `subprocess.run([...], shell=False)` with a fixed argv list; references are grammar-validated as repository-relative POSIX paths before use; no reference text is ever passed to a shell | `tests/test_test_mapping_checker.py` — a malicious reference such as `test:; touch /tmp/pwned` is rejected by TMC-02 before collection |
| Path escape | A `test:`/registry path resolving outside the repository root | Validate every referenced path with `Path.resolve()` + `is_relative_to(repo_root)` (the `mcp_server.py` `_contained_path` precedent) before existence/collection | `tests/test_test_mapping_checker.py` — a `../`-escaping reference fails as non-compliant |
| Collection side effects | Writing `.pytest_cache` or running bodies | `-p no:cacheprovider` and `--collect-only`; `cwd=repo_root`; no network | asserted by the collect-only invocation shape and the integration run leaving the tree unchanged |

Other matrix rows (routing, VCS/PR automation, executable-file classification) are **N/A** — this
change adds none. Per the phase's read restriction, the shared `references/threat-matrix.md` was not
loaded; the applicable subset above is derived from the boundaries this change actually introduces.

## Migration / Rollout

No data migration and no feature flag. The three tables are re-tagged in the same change that lands the
checker, so the tree is green from the first commit. Rollout order (see `tasks.md`): registry → re-tag
tables → checker → checker tests → rule 6 / config rewrite → CI gate → verify. The registry is the
initial state that makes the checker's first run pass; the re-tag is what brings the three tables into
compliance.

## Open Questions

- [x] **O1 — checker filename/CLI**: resolved — `scripts/check_test_mapping.py` with the argparse
  surface above.
- [x] **O2 — registry format / stored counts**: resolved — reason-only Markdown table under
  `openspec/`; counts re-derived at check time, never stored.
- [x] **O3 — node-id required vs optional / match rule**: resolved — `::name` optional; exact
  collected-node membership via pytest collect-only.
- [x] **O4 — `data-quality` heading level**: resolved as moot for the gate — scenario enumeration is
  exactly `#### Scenario:`, and only mapped specs are checked; `data-quality` is registry-only.
- [x] **O5 — rule 6 inline count vs pointer**: resolved — no inline count; rule 6 names the registry
  and the reproducing command only (the stale-literal trap D7 removes).
- [ ] **Scope resolution A vs B** — confirm the full scenario↔row bijection (resolution B, encoded in
  `mapping-checker` MC-02 and tasks 1.4–1.5) or the proposal-faithful row-level contract (resolution A,
  which relaxes MC-02 and drops tasks 1.4–1.5). This is the only blocking scope question.
- [ ] **Chain strategy for apply** — the estimate is above the 400-line review budget (re-tag of ~102
  rows + checker + tests + registry + docs + CI). `tasks.md` recommends chained PRs and records
  `Chain strategy: pending`; the maintainer chooses `stacked-to-main` / `feature-branch-chain` /
  `size-exception` before apply.
