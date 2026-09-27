# Exploration: openspec SDD-context drift (#258)

**Change**: `docs-openspec-context-drift`
**Issue**: GitHub #258 — `openspec/project.md` and `openspec/config.yaml` carry stale stack + gate facts.
**Mode**: ODD (documentation reconciliation; the drift is unguarded prose, no capability requirement is amended).

## Problem

`openspec/project.md` and `openspec/config.yaml` are the SDD context that every future
change reads. Both had drifted from the enforced configuration and the shipped tree:

| Location | Stale fact | Source of truth |
| --- | --- | --- |
| `project.md` stack table | `mypy (strict=false, check_untyped_defs=true)` | `pyproject.toml` `[tool.mypy] strict = true` |
| `project.md` stack table + Pre-commit row | omits `pyright` | `.pre-commit-config.yaml` local `pyright` hook; CI-09 |
| `project.md` project tree | `9 subcommands: … mcp` | `src/sofer/cli.py` registers 10 (`report-failure` missing); `README.md` says 10 |
| `project.md` Pre-commit hook order | `ruff fix -> ruff format -> mypy` | pre-commit runs `mypy` then `pyright` |
| `project.md` Testing | `ruff 0.16.0` / `mypy 2.3.0`; type command omits pyright | `pyproject.toml` pins `ruff==0.16.8`, `mypy==2.3.1`, `pyright==1.1.414` |
| `config.yaml` context | same stale versions | same pins |
| `config.yaml` quality | linter scope misses `scripts/`; mypy scope misses `scripts/`; pyright absent; formatter without `--check` | `.github/workflows/ci.yml` lint job (CI-09, CI-11, CI-12) |
| `config.yaml` verify build_command | narrower than CI | `ci.yml` lint gate sequence |

No test references `openspec/project.md`; the only related guards check CONTRIBUTING for the
ruff pin (`tests/test_ci_workflows.py:748`) and the coverage fields of `config.yaml`
(`:694`). The drift was therefore invisible to the suite.

## Decision: ODD vs SDD

The issue left the mode open ("decide SDD vs ODD at proposal time based on whether a spec
requirement is amended"). No `openspec/specs/<capability>` requirement is amended: the
reconciliation edits SDD bootstrap artifacts (`project.md`, `config.yaml`), and the only
behavior-bearing part is the static guard. The guard is a **supporting guard** in the same
class as `test_ci_workflow_files_present` — it enforces agreement among existing
declarations opencode reads, and introduces no new capability requirement. This is ODD,
matching the `docs-*-veracity-sweep` precedent.

## Scope boundary

- In: `openspec/project.md`, `openspec/config.yaml`, and the new guards in
  `tests/test_ci_workflows.py`.
- Out: any `openspec/specs/**` change, any `src/sofer/**` change, the `fastmcp` cap drift
  (#257) and the PKG-05 install contract (#259).
