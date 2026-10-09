# Tasks: feat-mcp-user-config-flag

**Change** `2026-10-09-feat-mcp-user-config-flag` (GitHub **#274**) · branch
`feat/274-mcp-user-config-flag` from `dev@22877b0` · store **hybrid** — this file plus the Engram
mirror.

**Inputs read this phase, directly:** `proposal.md` and `design.md` of this change.

**One-line outcome:** `sofer mcp add`/`remove` accept an explicit user-scope config file that wins over
the adapter's env override and the home default, refuse it with `--agent all`, and name a divergence
between `$HOME` and the account home instead of reporting a silent success.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change adds a capability. The carrier is a
real red-then-green: the new tests failed **10 of 13** before the implementation (the three that passed
were the regression guards for the existing resolution) and pass afterwards. No REFACTOR target: the
resolution gains one higher-precedence step.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: the resolution, `all` rejection, warning and declared-path tests | done | `10 failed, 3 passed in 2.57s` |
| T2 | GREEN: `resolve_config_path(..., user_config=None)` with the three-step precedence | done | `14 passed, 2 skipped` |
| T3 | GREEN: `_account_home()` + `home_mismatch_warning()` | done | warning tests green |
| T4 | GREEN: the flag on both subparsers, the `all` rejection, the warning, the help text (rule 7) | done | focused files `314 passed, 3 skipped` |
| T5 | Strengthen `test_cmd_remove_uses_the_declared_user_config`, which passed vacuously under `dry_run=True` | done | now asserts the declared file was mutated |
| T6 | MCP-REG-01 resolution clause + `User-scope config resolution` scenario | done | spec diff; `check_test_mapping.py` exit 0 |
| T7 | CLI-R09: the flag in the enumeration, the help scenario, and the `all`-rejection paragraph | done | spec diff |
| T8 | `README.md` + `README_ES.md` (rule 13): flags table, `--agent`/`--scope` row, per-agent locations | done | 3 edits each, mirrored |
| T9 | Rule-14 gate: `cli.py` at 100.00%, no pragma | done | `check_core_coverage.sh` exit 0; `cli.py 631 0 190 0 100%` |
| T10 | mypy clean on **both** platforms | done | `sys.platform == "win32"` guard; `Success: no issues found in 36 source files` |
| T11 | Full gates | done | `2028 passed, 8 skipped`; ruff/format/mypy/pyright clean; TOTAL 94% |
| T12 | Archive the change **inside this PR** (rule 15) | done | this folder + `archive-report.md`, both under `openspec/changes/archive/` |

---

## Constraints honoured

- **No `# pragma: no cover` anywhere.** `cli.py` reaches 100% through real tests, including the
  Windows branch of `_account_home` and both new guards on both subcommands.
- **Server-root containment untouched:** `_contained_path`, `_get_root`, `PathOutsideRootError` and
  `build_server` are absent from the diff.
- No version bump, no `pyproject.toml`/`uv.lock`/`openspec/project.md`/`openspec/config.yaml` change, no
  new requirement, no Test Mapping row, no registry edit.
- No invented per-agent environment-variable names.

---

## Platform note, recorded rather than hidden

`mcp_registration.py` measures 98% locally and 100% on the Linux coverage job: lines 267-272 are the
POSIX-only `pwd` path, unreachable on this Windows host because the two tests covering them are
`skipif`-guarded (unguarded they would error on `import pwd` and break the Windows matrix). `cli.py` is
100% on both platforms and the four rule-14 gates pass locally.
