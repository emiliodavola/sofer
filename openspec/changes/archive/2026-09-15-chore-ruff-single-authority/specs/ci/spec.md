# Delta for ci

> **Change** `2026-09-15-chore-ruff-single-authority` (GitHub #195) · branch
> `chore/195-ruff-single-authority` · store **hybrid** (this file + Engram mirror
> under topic key `sdd/2026-09-15-chore-ruff-single-authority/spec`).
>
> **Additive, not destructive.** No existing `ci` requirement text changes: CI-01..CI-07
> keep their canonical clauses and scenarios byte-for-byte, so archive-time replacement of
> a canonical requirement block would be a lossy no-op. The contract enters as **new**
> requirement **CI-08** (the next free ID in this capability), followed by the four
> `## Test Mapping` rows it adds to the canonical table.
>
> **Capability choice — `ci`, and the named alternative, both recorded.** The proposal
> recommends `ci` and names `process-boundary` PB-14 as the fallback; this delta adopts
> `ci`. The reasoning is kept visible below (§ *Capability placement*) so the design phase
> can ratify it or move it to PB-14 with the same three guard tests and the same three
> pytest-mapped scenarios either way.
>
> **Rule-6 resolution.** CI-08's scenarios 1–3 map 1:1 to three static guard tests in
> `tests/test_ci_workflows.py`; scenario 4 (a mismatched binary fails loudly) maps to
> verify-phase runtime command evidence, because asserting it from pytest would mean
> spawning a second ruff binary from the suite — a dependency class AGENTS.md rule 9 keeps
> out. No scenario is left unmapped and no vacuous test is invented.
>
> **No CI gate is armed.** CI-08 adds no workflow file and no `format --check` step; its
> workflow assertion is the inverse (zero ruff version literals under
> `.github/workflows/**`). `process-boundary` PB-10's *No CI gate was armed, and recurrence
> stays owned by #194* scenario keeps passing, and #194 still owns the un-staged-file gap.
>
> **Domain hygiene (checked this phase).** `openspec/specs/ci/spec.md` exists and was read
> before writing this delta (delta, not full spec); no other non-archived change carries
> `specs/ci/` — the only active change directory in `openspec/changes/` is this one; this
> change has no legacy flat `openspec/changes/<change>/spec.md`. The canonical file is
> **not** edited by this phase; it absorbs this delta at `sdd-sync`. The `process-boundary`
> delta for this change (PB-10) is a separate file.
>
> **Proposal `Capabilities` section:** the proposal has none. Its `## Scope` items 6 and 7
> name this `ci` delta and the `process-boundary` delta explicitly, so the two domains are
> proposal-supported rather than inferred here (reported as an assumption in the phase
> return).

## ADDED Requirements

### Requirement: Single authoritative ruff version (CI-08)

> Added by change `2026-09-15-chore-ruff-single-authority` (GitHub #195). Scenarios 1–3 are
> asserted by three static guard tests in `tests/test_ci_workflows.py`; scenario 4 is
> verify-phase runtime evidence — the framing this capability's own Test Mapping already
> uses for gate exit codes.

The repository SHALL declare exactly one authoritative ruff version, and the three
declarations that decide which ruff runs SHALL name that same version: the `pyproject.toml`
dev-group pin (an exact `==X.Y.Z` specifier, never a floor), `[tool.ruff] required-version`
in `pyproject.toml`, and the `astral-sh/ruff-pre-commit` entry's `rev` in
`.pre-commit-config.yaml` (`vX.Y.Z`). The dev pin SHALL be the single source of the value —
`required-version` and the hook `rev` SHALL be derived from it — so a future bump edits
declarations only and SHALL NOT have to edit a test literal.

`[tool.ruff] required-version` SHALL be the enforcing declaration: a binary whose version
does not satisfy it SHALL fail when configuration is loaded, so a drifted environment
errors instead of silently formatting or linting under a version the repository did not
declare. The declarations SHALL be statically guarded in `tests/test_ci_workflows.py`,
extending that module's existing `_read_text` / `_load_toml` / `_load_yaml` helpers: the dev
pin's exact specifier, the `required-version` value, and the hook `rev` SHALL be asserted
equal; no file under `.github/workflows/` SHALL declare a ruff version literal (the version
reaches CI through `uv.lock`, not through a workflow); and the extracted `X.Y.Z` SHALL
appear in `CONTRIBUTING.md`'s Code style section. Each guard SHALL derive the version from
the dev pin and SHALL NOT hardcode a version literal.

This requirement SHALL arm no CI step and SHALL add no workflow file: it SHALL NOT
introduce a `ruff format --check` invocation under `.github/workflows/**`, enforcement of
the staged-file formatter SHALL remain the local pre-commit `ruff-format` hook, and issue
#194 SHALL retain the un-staged-file gap (`process-boundary` PB-10). A change that moves
the pin SHALL refresh `uv.lock` in the same change, confined to the ruff package
block and the dev specifier. `packaging` PKG-06 states the same regeneration class for its own
`fastmcp` declaration and SHALL NOT be read as owning this one: its `uv.lock` clause is scoped to that
declaration, so the obligation for a ruff pin move is stated here, in CI-08.

#### Scenario: Dev pin, required-version, and hook rev agree

- GIVEN the three ruff version declarations — the `[dependency-groups] dev` pin in
  `pyproject.toml`, `[tool.ruff] required-version`, and the `astral-sh/ruff-pre-commit`
  entry in `.pre-commit-config.yaml`
- WHEN `tests/test_ci_workflows.py::test_ruff_pin_hook_rev_and_required_version_agree`
  extracts `X.Y.Z` from the dev pin and compares the other two declarations against it
- THEN the dev specifier SHALL be exact (`==X.Y.Z`, so a `>=` floor SHALL fail the guard)
- AND `[tool.ruff] required-version` SHALL equal `"==" + X.Y.Z`
- AND the hook entry's `rev` SHALL equal `"v" + X.Y.Z`

#### Scenario: No workflow declares a ruff version

- GIVEN every file under `.github/workflows/`
- WHEN `tests/test_ci_workflows.py::test_workflows_do_not_declare_a_ruff_version` scans
  them for a ruff version literal
- THEN zero matches SHALL exist, so the authority stays in the three declarations and CI
  receives the version through `uv.lock`

#### Scenario: CONTRIBUTING names the declared version

- GIVEN `CONTRIBUTING.md`'s Code style section
- WHEN `tests/test_ci_workflows.py::test_contributing_names_the_declared_ruff_version`
  looks for the `X.Y.Z` extracted from the dev pin
- THEN that value SHALL appear
- AND the guard SHALL hold no version literal of its own, so a bump cannot leave the
  documentation silently stale

#### Scenario: required-version rejects a mismatched binary

- GIVEN the repository's declared `[tool.ruff] required-version` and a mismatch probe that
  declares a different required version
- WHEN `uv run ruff check src/ tests/ scripts/` and
  `uv run ruff format --check src/ tests/ scripts/` run under the probe, and both run again
  under the declared value
- THEN each probe run SHALL exit non-zero and SHALL report both the required and the
  running version
- AND each declared-value run SHALL exit 0, so the mismatch fails loudly instead of
  disagreeing quietly
- AND this evidence is **verify-phase runtime evidence** — the commands above, pasted with
  their exit codes into the verify report (CI-01 gate-exit-code precedent)

---

## Test Mapping

The four rows below follow this file's canonical `## Test Mapping` format and are appended
to that table at `sdd-sync` (the CI-07 rows at `openspec/specs/ci/spec.md:313-317` are the
precedent for both the row shape and the append-at-sync mechanics; the canonical table is
not edited by this phase). The two verify-phase row conventions already in use —
"Verify-phase static evidence — `<command>`" and "Verify-phase runtime evidence —
`<command>`" — are reused verbatim.

| Req | Scenario | Verification |
| --- | --- | --- |
| CI-08 | Dev pin, required-version, and hook rev agree | `tests/test_ci_workflows.py` — `test_ruff_pin_hook_rev_and_required_version_agree`: tomllib + YAML declaration equality, with `X.Y.Z` extracted from the dev pin |
| CI-08 | No workflow declares a ruff version | `tests/test_ci_workflows.py` — `test_workflows_do_not_declare_a_ruff_version`: YAML/full-text scan of `.github/workflows/*.yml` |
| CI-08 | CONTRIBUTING names the declared version | `tests/test_ci_workflows.py` — `test_contributing_names_the_declared_ruff_version`: text inspection of `CONTRIBUTING.md` |
| CI-08 | required-version rejects a mismatched binary | Verify-phase runtime evidence — `uv run ruff check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/ scripts/` exit codes under a mismatched `required-version` probe and under the declared value (CI-01 gate-exit-code precedent) |

---

## Capability placement — adopted `ci`, alternative `process-boundary` PB-14

**Adopted: `ci`.** The evidence the proposal marshalled, re-checked against the canonical
files this phase:

1. `ci/spec.md:215-283` (CI-07) is the direct precedent — a **cross-file
   declaration-equality** contract (`.python-version` equals both gate-job pins) hosted in
   `ci`. A three-declaration ruff version authority is the same shape.
2. `ci/spec.md:285` is one of only two `## Test Mapping` tables in `openspec/specs/**`
   (`coverage/spec.md:283` is the other), and it is the one that indexes
   `tests/test_ci_workflows.py` — the exact file the three guards land in.
   `process-boundary/spec.md` has no Test Mapping table at all (`grep "## Test Mapping"`
   over `openspec/specs/` returns only `coverage` and `ci`).
3. The authority decides what CI lints with: `ci.yml:19` and `release.yml:29` run
   `uv run ruff check src/ tests/ scripts/` after `uv sync`, so the version CI uses follows
   the dev pin through `uv.lock`. The claim is CI-facing, not tree-internal.
4. `ci/spec.md:5-11` shows that adding CI-07 left the `## Purpose` paragraph unchanged (it
   still enumerates CI-01..CI-06 only), so this delta likewise needs no Purpose edit. The
   Purpose paragraph's enumeration is therefore stale for **both** CI-07 and CI-08 — a
   pre-existing condition this change does not introduce and deliberately does not touch.

**Alternative: `process-boundary` PB-14, to be ratified or moved by the design phase.** The
counter-argument is real and stays on the record: the ruff authority is arguably the same
*formatter-integrity* class as PB-10, so it could live beside PB-10 as PB-14. The
counter-precedent behind that reading (#177 rejecting `ci` because "this change
deliberately adds no CI step, so a `ci` requirement naming a workflow step would be false")
does **not** transfer: CI-08 names no workflow step, adds no workflow file, and asserts the
*inverse* (zero workflow version literals). What CI-08 loses relative to PB-14 is the
Test Mapping table, which `process-boundary` would need to grow for its three pytest-mapped
scenarios. **If moved, nothing else changes**: the three guard tests, the four scenarios,
and the `required-version` evidence class are identical under either home.

---

## Cross-referenced and deliberately untouched

| Canonical text | Treatment | Why |
| --- | --- | --- |
| `ci` CI-01 (config-owned `fail_under = 90`; flag ban) | Not modified | CI-08 adds no threshold, no `--fail-under` flag, and no coverage invocation; CI-01's gate-exit-code row is only a framing precedent |
| `ci` CI-02, CI-03, CI-04, CI-05 | Not modified | No workflow content changes at all: the diff contains zero `.github/workflows/` paths |
| `ci` CI-06 (documentation truth, four asserted surfaces) | Not modified | `openspec/config.yaml`, README/README_ES and the PR template are untouched; `CONTRIBUTING.md` is touched by this change, but its Code style sentence gaining the version is a **new** CI-08 assertion, not a change to CI-06's asserted surface list |
| `ci` CI-07 (dev interpreter pin) | Not modified | A sibling declaration-equality contract; its scenarios and rows stay byte-for-byte. The parallel is why CI-08 exists, not an edit to it |
| `ci` `## Purpose` (`ci/spec.md:5-11`) | Not modified | Precedent (CI-07) left it unchanged; its CI-01..CI-06 enumeration is already stale and belongs to the documentation wave, not here |
| `process-boundary` PB-10 | Modified by this change's sibling delta `specs/process-boundary/spec.md` (one sentence) | PB-10 states the invariant and points here for the guard; the two deltas are complementary and neither duplicates the other's clauses |
| `packaging` PKG-06 (`uv.lock` SHALL be regenerated) | Cross-referenced, not modified | CI-08 owns its own lock-refresh obligation for a ruff pin move; PKG-06's clause is scoped to the `fastmcp` declaration and is cited as the same class of rule, not as this one's owner |
| #187 (`CONTRIBUTING.md:77` names a nonexistent `ruff.toml`), #212 (documented commands narrower than CI), #194 (no `format --check` gate) | Out of scope, not absorbed | Each has its own owner; CI-08's third guard asserts the *presence of the version* in `CONTRIBUTING.md` and asserts nothing about that file's `ruff.toml` path |
| `openspec/project.md:82` and the `AGENTS.md` version statements | Out of scope, not absorbed | Owned by the documentation wave (#184/#187/#214); `openspec/config.yaml:12` is gitignored local state, not change-bearing |
