# Design: Align documented gate-command scope and sync CITATION.cff on `dev` (#212, #191)

## Technical Approach

Three documentation edits and one data sync, each minimal and script-driven where a script exists:

1. Fix the two command scopes in `AGENTS.md`, `CONTRIBUTING.md`, and the PR template so every
   documented gate names the same paths CI enforces.
2. Reorder `AGENTS.md` rule 12's "Cutting a release" steps so the `CITATION.cff` bump happens on
   `dev` before the merge, and record that in the branch-flow bullet.
3. Sync `CITATION.cff` to the latest release with `scripts/update_citation.py`.

No spec-level behavior changes, so no delta spec is produced.

## Architecture Decisions

### Decision: Align docs up to CI scope (not CI down to docs)

**Choice**: Documented commands become `uv run ruff check src/ tests/ scripts/` and
`uv run mypy src/ scripts/`; pyright stays bare (config-driven over `src` + `scripts`).
**Alternatives considered**: Narrow CI to the documented scope (#212's second option).
**Rationale**: `scripts/` contains live code (`check_core_coverage.sh`, `update_citation.py`);
dropping it from the gates would un-lint/type-check shipped code. CI is the authoritative gate;
the docs must describe it truthfully.

### Decision: Record option (a) by reordering rule 12, not by editing workflows

**Choice**: Move the CFF sync step before the merge in AGENTS.md and add one branch-flow sentence.
**Alternatives considered**: Option (b) (declare `main` authoritative) and option (c)/(d)
(automate or dual-guard).
**Rationale**: The maintainer recorded option (a). It is the only option that restores rule 12's
branch-flow rule and keeps the tag-time guard meaningful, with zero workflow/spec/test changes.

### Decision: Sync the CFF through the existing script only

**Choice**: `python scripts/update_citation.py --version 0.3.12 --date 2026-09-13`.
**Alternatives considered**: Hand-editing `CITATION.cff`.
**Rationale**: Issue AC: the script remains the only writer of the field. It edits only the two
target lines and preserves every other byte.

## Data Flow

    contributor reads docs ──→ runs command matching CI scope ──→ local result == CI result

    release: dev CFF bump ──(merge --no-ff)──→ main ──→ tag ──→ citation-check(tagged commit)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `AGENTS.md` | Modify | Rule 5 mypy scope; rule 12 step order; branch-flow sentence |
| `CONTRIBUTING.md` | Modify | Development commands: mypy + ruff check scopes |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modify | Verification block + Checklist: mypy + ruff check scopes |
| `CITATION.cff` | Modify | `version: 0.3.12`, `date-released: 2026-09-13` |

## Interfaces / Contracts

Documented command contract (after this change):

```
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/
uv run mypy src/ scripts/
uv run pyright
```

`scripts/update_citation.py` CLI contract is unchanged: rewrite path edits only `version:` and
`date-released:`; `--check` exits 0 only on an exact version + valid ISO date.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Static | Docs name the enforced scope | Read the three files; assert the wider scopes and no stale `uv run mypy src/` / `uv run ruff check src/ tests/` gate lines |
| Static | Rule 12 sets the bump on `dev` before the merge | Read AGENTS.md rule 12 |
| Static | CFF declares the synced version | `uv run python scripts/update_citation.py --check --version 0.3.12` |
| Regression | CI-09/CI-06 doc assertions still hold | `uv run pytest tests/test_ci_workflows.py -q` |
| Full | No collateral breakage | `uv run pytest tests/ -q` |

## Threat Matrix

N/A — no routing, shell/subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary changes. The change edits Markdown prose and runs an existing,
already-tested stdlib script to update two data fields.

## Migration / Rollout

No migration required. After this change, the next release follows the reordered rule 12.

## Open Questions

None.
