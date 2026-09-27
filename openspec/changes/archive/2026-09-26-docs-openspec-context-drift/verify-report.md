# Verify Report: Reconcile the openspec SDD context (#258)

**Change**: `docs-openspec-context-drift`
**Mode**: ODD (documentation context; no runtime boundary)
**Branch**: `docs/258-openspec-context-drift` (base `dev` @ `5f6c2de`)

## Verification evidence

| Check | Command | Result |
| --- | --- | --- |
| Focused guards | `uv run pytest tests/test_ci_workflows.py -q` | `49 passed` |
| Full suite | `uv run pytest tests/ -q` | `1992 passed, 1 skipped` |
| Lint | `uv run ruff check src/ tests/ scripts/` | passed |
| Format | `uv run ruff format --check src/ tests/` | 73 files already formatted |
| Types (mypy) | `uv run mypy src/ scripts/` | no issues |
| Types (pyright) | `uv run pyright` | 0 errors, 1 pre-existing `_toml.py` warning |
| Test-mapping contract | `uv run python scripts/check_test_mapping.py` | `OK: test-mapping contract holds` |

## Negative controls (guards genuinely fail on drift)

| Probe | Guard | Result |
| --- | --- | --- |
| project.md count `10 → 9` | subcommand inventory | FAILS (count mismatch), restored |
| project.md `mypy 2.3.1 → 2.3.0` | tool versions | FAILS, restored |
| project.md `uv run pyright` removed | pyright gate | FAILS, restored |
| config.yaml formatter `--check` removed | quality commands | FAILS, restored |

The working tree was restored byte-for-byte after each probe (`git diff` clean).

## Independent verification (subagent)

A read-only adversarial subagent verified the change against `pyproject.toml`,
`src/sofer/cli.py`, `.pre-commit-config.yaml`, `uv.lock`, and `ci.yml`.
**Verdict: PASS** on all eight claims (mypy posture, pyright gate named, subcommand
inventory = 10, tool versions, config quality commands, guard effectiveness, scope,
no spec touched). It executed the four guard functions directly and ran in-memory
negative controls confirming the guards fail on drift.

### Findings and resolution

- **M1 (docstring overstated derivation)** — reworded the quality-command guard
  docstring to say each command is *checked against* `_CI_LINT_GATE_RUNS`. Fixed.
- **M2 (premature completion marks)** — `tasks.md`/`apply-progress.md` marked the
  verify-report and archive steps complete before the artifacts existed. Resolved by
  producing this report and archiving the change in the same commit.
- **M3 (stale footer)** — updated `openspec/project.md`'s "Last updated" footer to the
  #258 reconciliation. Fixed.
- **M4 (latent substring looseness)** — hardened the tool-version guard to a boundary
  regex (`(?!\d)(?!\.\d)`), so `mypy 2.3.1` cannot pass on a `mypy 2.3.10` mention. Fixed.
  The pyright-gate guard's existence check is intentionally simple; no negated mention
  exists and the risk is latent only.

Unresolved findings: none.
