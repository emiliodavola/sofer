# Pre-proposal handoff — `2026-09-15-chore-ruff-single-authority`

> Orchestrator-owned artifact. Records the maintainer-confirmed product decisions and the evidence
> base the proposal must build on. The proposal phase receives this as its confirmed handoff and
> MUST NOT interview the maintainer or infer consent.

## Change identity

| Field | Value |
| --- | --- |
| Change | `2026-09-15-chore-ruff-single-authority` |
| GitHub issue | #195 — *chore: two authoritative ruff versions in play (pre-commit v0.16.7 vs ambient 0.16.0)* |
| Branch | `chore/195-ruff-single-authority` (from `dev@5a2ae38`) |
| Artifact store | hybrid (`openspec` + Engram) |
| Session preflight | execution `auto`, delivery `auto-chain`, review budget 400 lines |
| Explore artifact | `openspec/changes/2026-09-15-chore-ruff-single-authority/explore.md` — SHA-256 `92a8861e7b9a833cc31a35d6d5e92419c019ae6706b6d3d47a4c067d6e4cb351` |

## Research lane: UNSELECTED (maintainer decision)

The maintainer initially selected the `documentation` research lane. Two launches of `sdd-research`
timed out with **0 turns and 0 tool calls** and wrote nothing, while every other phase agent in the
same session completed normally. The maintainer then explicitly de-selected the lane so the
pre-proposal gate could open.

Consequence for the proposal: **no external citations are available.** Every fact below is either a
command the orchestrator ran on this working tree or a file observation. Claims that would normally
be backed by upstream documentation — the precise semantics of `required-version`, ruff's formatter
stability policy, and the `ruff-pre-commit` tag↔version contract — are recorded as measured
behaviour, not as documented guarantees. The proposal must not assert what was not measured.

## Confirmed product decisions

These four were put to the maintainer with evidence and cost, and answered explicitly.

### D1 — Authoritative version: **0.16.7** (the pre-commit rev)

The hook already declares `rev: v0.16.7` and that bump is a recent commit by the maintainer
(`.git/logs/HEAD:720`, epoch ≈ 2026-09-13). Measured evidence that moving the environment *up* is
safe on this tree:

```text
$ uvx ruff@0.16.7 format --check src/ tests/ scripts/
68 files already formatted                    # exit 0
$ uv run ruff format --check src/ tests/ scripts/     # ruff 0.16.0
68 files already formatted                    # exit 0
```

Both versions produce an identical verdict, so pinning 0.16.7 does not reformat anything and does
not reach into the four AGENTS.md rule-14 modules. This retires the explore artifact's reason for
preferring 0.16.0 ("0.16.7 is unmeasured on this tree") — the orchestrator measured it.

Consequence to design for: the dev-group pin becomes `ruff==0.16.7` and `uv.lock` must be refreshed
in the same change (issue acceptance criterion 5).

### D2 — Enforcement mechanism: `required-version` + a static guard test

`[tool.ruff] required-version` is a real top-level setting and fails **hard**, measured directly:

```text
$ # tmp/probe-ruff/pyproject.toml: [tool.ruff] required-version = "==99.0.0"
$ ruff check .
ruff failed
  Cause: Required version `==99.0.0` does not match the running version `0.16.0`
$ ruff format --check .
ruff failed
  Cause: Required version `==99.0.0` does not match the running version `0.16.0`
$ ruff config                 # lists `required-version` among resolvable settings
```

A control probe with an invented key (`totally-bogus-setting = 1`) was rejected with a TOML parse
error, confirming the key name is valid rather than silently ignored. The maintainer also accepted
the ergonomic cost: a contributor running a different ruff will now see an error. That is the point.

The static guard test asserts the three declarations agree: the `pyproject.toml` dev pin, the
`[tool.ruff] required-version` value, and the `[tool.ruff]`-relevant `rev:` in
`.pre-commit-config.yaml`.

### D3 — Acceptance criterion 3 is evidenced by exercising the real hook

The issue's criterion 3 requires `uv run ruff format --check` and the `ruff-format` hook to produce
the same verdict on the same file. The maintainer chose the **direct** evidence path: install the
hook in this clone (`pre-commit install` — a local, unversioned `.git/hooks` change) and exercise it
on a deliberately misformatted throwaway file, recording both verdicts.

Relevant measured fact: `.git/hooks/pre-commit` does **not** exist in this clone and the pre-commit
cache holds no `0.16.7` environment, so the hook has never run here. The issue's premise that "the
hook already validated staged files with 0.16.7" is **not** evidenced; the change must not inherit
that assumption.

### D4 — Research lane de-selected (see above)

## Evidence base — measured by the orchestrator with shell

| Fact | Command / source |
| --- | --- |
| Ambient ruff is 0.16.0 | `uv run ruff --version` |
| Hook rev is v0.16.7 | `.pre-commit-config.yaml:3` |
| Dev group floats | `pyproject.toml` dev group declares `ruff>=0.9.0` |
| Lock resolves 0.16.0 | `uv.lock` |
| 0.16.7 and 0.16.0 agree on this tree | both `format --check` runs → `68 files already formatted` |
| `required-version` fails hard | probes above, both `check` and `format` |
| The hook has never run here | `.git/hooks/pre-commit` ENOENT; no `0.16.7` under `~/.cache/pre-commit` |
| Hook mechanism | the cached hook clone pins `ruff==X.Y.Z` in its own `pyproject.toml` and builds a per-rev venv, so the project environment is never consulted |
| Zero tests reference ruff | `grep -rn "ruff" tests/` → no matches |
| Exactly one canonical clause names versions | `openspec/specs/process-boundary/spec.md:258` (PB-10 body); **0 scenarios** |
| Blast radius | 2 declarations, 2 lock lines, 1 doc (`CONTRIBUTING.md:77`), 2 SDD metadata statements |

## Mandatory consequence the proposal must carry

`openspec/specs/process-boundary/spec.md:258` (PB-10) states, verbatim, that the mismatch
*"SHALL stay unaddressed here and SHALL be owned by issue #195"*. Once the versions are aligned,
that requirement body is factually wrong and **this change owns correcting it**. The proposal must
land a `process-boundary` delta that restates PB-10 without the mismatch clause — and must keep the
change's scope separate from PB-10's other content.

## Hard scope boundaries

1. **No CI format gate.** PB-10 `:286` states enforcement stays the local `ruff-format` hook and
   that recurrence *"is owned by issue #194 rather than by any clause of PB-10"*. This change arms
   no `format --check` step in any workflow. Any spec scenario asserting zero such invocations must
   keep passing.
2. **#187 is separate.** `CONTRIBUTING.md:77` points at a `ruff.toml` that does not exist. It sits in
   the same sentence that must gain the version, but the nonexistent-file defect belongs to #187 and
   must not be silently absorbed.
3. **#212 is separate.** `CONTRIBUTING.md:28-29` documents `mypy src/` and `ruff check src/ tests/`
   while CI runs `src/ tests/ scripts/`. Same class, different issue.
4. **No unrelated version claims.** `openspec/project.md:82` and `AGENTS.md` also state tool
   versions. They are owned by the documentation wave (#184/#187/#214). The proposal may reference
   them but must not expand this change to cover them.

## Open questions for the proposal

None at the product level — all four decisions are answered. The proposal should resolve design-level
questions itself, in particular: where the static guard test lives (the `tests/test_ci_workflows.py`
idiom already pins workflow shape) and which canonical surface carries the new requirement once
PB-10's mismatch clause is removed.
