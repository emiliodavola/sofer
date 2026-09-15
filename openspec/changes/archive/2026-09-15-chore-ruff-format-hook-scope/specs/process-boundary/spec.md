# Delta for process-boundary

> **Change** `2026-09-15-chore-ruff-format-hook-scope` (GitHub #216) · branch
> `chore/216-ruff-format-hook-scope` · store **hybrid** (this file + Engram mirror under topic key
> `sdd/2026-09-15-chore-ruff-format-hook-scope/spec`).
>
> **Capability choice — `process-boundary`, justified.** This change has no behaviour change and no
> capability change: it narrows one pre-commit hook's file-type scope. What it establishes is a durable
> verification property of the tree, and `process-boundary` already owns exactly that category — PB-07
> enumerates the gates a change must satisfy, PB-10 states formatter integrity on a clean checkout, and
> PB-14 is the sibling scope declaration for the formatter's hook. The alternative home, `ci` CI-08, was
> considered and **rejected**: CI-08 owns the declarative ruff version authority and asserts only the
> `rev` of that same repo entry, and this change arms **no CI step**, so a `ci` requirement about hook
> file scope would be misfiled. `ci` is cross-referenced only, never modified.
>
> **Additive, not destructive.** No existing `process-boundary` requirement text changes (PB-01..PB-13
> keep clauses and scenarios byte-for-byte), so archive-time replacement of a canonical block would be a
> lossy no-op; the clause enters as **new** requirement **PB-14** (next free ID in this capability —
> `openspec/specs/process-boundary/spec.md` ends at PB-13).
>
> **Domain hygiene (checked this phase).** `openspec/specs/process-boundary/spec.md` exists and was read
> before writing this delta (delta, not full spec); no other non-archived change carries
> `specs/process-boundary/` — the only active change directory under `openspec/changes/` is this one; this
> change has no legacy flat `openspec/changes/<change>/spec.md` to reconcile. The canonical file is **not**
> edited by this phase; it absorbs this delta at `sdd-sync` (the PB-14 block after PB-13's final scenario,
> and the new `## Test Mapping` section at the end of the file).
>
> **Proposal `Capabilities` section:** the proposal has none. Its `## Scope` item 2 names this
> `process-boundary` delta explicitly, so the domain is proposal-supported rather than inferred here
> (reported as an assumption in the phase return).

## ADDED Requirements

### Requirement: Repository-declared ruff-format hook file scope (PB-14)

> Added by change `2026-09-15-chore-ruff-format-hook-scope` (issue #216).

The `ruff-format` pre-commit hook's file-type scope SHALL be a **repository declaration**, not an
inherited upstream default: the `astral-sh/ruff-pre-commit` hook entry in `.pre-commit-config.yaml` SHALL
declare an explicit `types_or` naming the types this repository intends the formatter to see — `python`,
`pyi`, and `jupyter` — and `markdown` SHALL NOT be among them. The decision is deliberate and
rationale-bearing: upstream widened the manifest's `types_or` to include `markdown` between
`ruff-pre-commit` 0.15.21 and 0.16.6 without this repository changing anything, and the pinned hook then
rewrote the fenced Python inside `README.md` and `README_ES.md` (issue #216). The declared scope SHALL
therefore NOT be read as a mirror of the upstream default, a `rev` bump SHALL NOT widen it silently, and
the declared tag vocabulary SHALL stay consistent with the sibling scope decision
`[tool.ruff] extend-exclude = ["openspec"]` in `pyproject.toml`.

This requirement SHALL constrain **the hook only**. `types_or` is a pre-commit filter, not a ruff setting:
a direct `ruff format <path>` still sees Markdown, and this requirement SHALL NOT be read as narrowing the
formatter itself, as adopting a Markdown formatter, or as arming any gate. Issue **#194** SHALL retain
ownership of the decision to arm a `ruff format --check` gate and of that gate's path scope; this
requirement SHALL arm no CI step. This change SHALL NOT move the `ruff-pre-commit` `rev`, SHALL NOT edit
`pyproject.toml` or any `src/sofer/**` path, and SHALL leave `README.md` / `README_ES.md` byte-identical.

The declaration SHALL be statically guarded in `tests/test_ci_workflows.py` (the established home for
static repository-shape contracts): the hook entry SHALL declare `types_or`, SHALL declare it as a list,
and `markdown` SHALL NOT appear in it. The guard SHALL assert the **defect class**, not mirror the
declared list, so a legitimate future widening to another type keeps it green. The guard SHALL assert
declaration shape only: that pre-commit honours the override is verify-phase runtime evidence and SHALL
NOT be asserted from pytest (the suite spawns no `pre-commit`).

#### Scenario: The hook declares its own scope and excludes Markdown

- GIVEN `.pre-commit-config.yaml` as committed by this change
- WHEN `tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown` parses it with the module's existing `_load_yaml` helper and selects the `astral-sh/ruff-pre-commit` repo's hook whose `id` is `ruff-format`
- THEN the entry SHALL be found exactly once and SHALL declare a list-valued `types_or`
- AND `"markdown"` SHALL NOT be a member of that list
- AND the guard SHALL be red against an entry with no `types_or` key and green once the config line lands (red then green, both recorded in the verify report)
- AND no other tag SHALL be asserted, so adding a legitimate type leaves the guard green

#### Scenario: The hook no longer receives Markdown and leaves the READMEs untouched

- GIVEN the pinned `ruff-pre-commit` hook materialised in the local pre-commit cache and the repository's declared `types_or` in place
- WHEN `uv run pre-commit run ruff-format --files README.md` runs
- THEN the hook SHALL report the file as not a hook input (`(no files to check)Skipped`) and SHALL exit 0
- AND `uv run pre-commit run ruff-format --all-files` SHALL show no Markdown batch — no `files were modified by this hook` — listing only `python` / `pyi` / `jupyter` inputs
- AND `git diff --stat -- README.md README_ES.md` SHALL be empty afterwards
- AND the hook's **file-list output**, not its exit code, SHALL be the discriminating evidence: the entry is the fixing command `ruff format --force-exclude`, which exits 0 after rewriting (the #195 trap)
- AND this evidence is **verify-phase runtime evidence** — the commands above pasted with their exit codes into the verify report (PB-10 / CI-08 S4 precedent)

---

## Test Mapping

Every scenario SHALL map to a green test or to verify-phase runtime evidence (AGENTS.md rule 6;
rules.specs). Static config assertions live in `tests/test_ci_workflows.py`. PB-01..PB-13 rows are not
backfilled by this change: their evidence classes are stated in their own scenario text, and the backfill
is a separate concern.

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| PB-14 | The hook declares its own scope and excludes Markdown | `tests/test_ci_workflows.py` — `test_ruff_format_hook_excludes_markdown`: YAML inspection of the `ruff-format` hook entry in `.pre-commit-config.yaml` |
| PB-14 | The hook no longer receives Markdown and leaves the READMEs untouched | Verify-phase runtime evidence — `uv run pre-commit run ruff-format --files README.md` and `--all-files`, plus an empty `git diff --stat -- README.md README_ES.md` |

---

## Cross-referenced and deliberately untouched

- `ci` CI-08 (declarative ruff version authority) — its rev guard reads the **same** `astral-sh/ruff-pre-commit`
  repo entry, but asserts only the `rev`; a hook-level `types_or` is invisible to it. Untouched: no `ci`
  requirement is added, modified, or removed, and `openspec/specs/ci/spec.md` is not edited by this change.
- `process-boundary` PB-10 (formatter integrity on a clean checkout, branch #177 / change
  `2026-09-14-chore-ruff-format-drift`) — owns format-check integrity and its #194-ownership clause,
  including the scenario asserting **zero** `format --check` invocations under `.github/workflows/**`.
  PB-14 constrains the hook only and arms no gate, so that scenario keeps passing unmodified.
- Issue **#194** — owns both the decision to arm a `ruff format --check` gate and that gate's path scope.
  PB-14 states the independence explicitly and adds no claim about any future gate.
- Issue **#187** — owns `CONTRIBUTING.md:77` prose (the same sentence whose `ruff.toml` path is its own
  defect). Contributor-facing prose is not edited here.
- `process-boundary` PB-01..PB-13 — untouched: no boundary contract, fixture, offline rule, test-count
  anchor, or requirement-ID numbering is affected by a hook scope declaration.

**Non-goals recorded by this delta:** no backfill of `## Test Mapping` rows for PB-01..PB-13; no
`CONTRIBUTING.md` or `AGENTS.md` prose change; no `pyproject.toml` edit; no `ruff-pre-commit` `rev` move;
no `src/sofer/**` path; no `README.md` / `README_ES.md` edit; no CI or workflow change (no
`ruff format --check` gate, no pre-commit invocation under `.github/**`); no touch of `tasks.md`,
`proposal.md`, or canonical specs under `openspec/specs/**` (sync-phase only); no commit, push, or PR.
