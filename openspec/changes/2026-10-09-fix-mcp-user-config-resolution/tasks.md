# Tasks: fix-mcp-user-config-resolution (slice 1)

**Change** `2026-10-09-fix-mcp-user-config-resolution` (GitHub **#274**) · branch
`fix/274-cwd-containment-gate` from `dev@69f5051` · store **hybrid** — this file plus the Engram
mirror.

**Inputs read this phase, directly:** `design.md` and `proposal.md` of this change.

**One-line outcome:** the `--cwd` rule becomes *existence, not containment* — a nonexistent path is
refused with its resolved path named, an existing directory outside the home is accepted and named,
the dead `scope` parameter is gone, and the rule is declared in MCP-REG-01 for the first time.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change replaces a validation rule rather
than adding production behavior. The carrier is a real red-then-green on the tests that describe the
new rule:

- **RED (measured):** `pytest tests/test_mcp_registration.py::TestCwdContainment` → **8 failed**,
  including the CLI case that proves the old gate *accepted a nonexistent cwd*
  (`DRY RUN  Would register opencode at ...\nope\opencode.json`, exit 0).
- **GREEN (measured):** the same selection → **8 passed**; focused files → `297 passed, 1 skipped`;
  full suite → `2011 passed, 6 skipped` (base `2005/6`; +6 = 8 new minus 2 replaced).

**REFACTOR has no target** — the change replaces one rule with a simpler one.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: tests for the new `--cwd` rule, the warning, and the CLI refusal | done | `8 failed in 1.01s`, with the `assert 0 == 1` case quoted in `design.md` §2 |
| T2 | GREEN: `validate_cwd(cwd)` existence rule; `scope` parameter removed; `outside_root_warning` added | done | `8 passed`; `ruff check` clean |
| T3 | `cli.py` caller: refuse on non-directory, warn on outside-root; docstring updated | done | `297 passed` on the focused files |
| T4 | Rewrite `TestCwdContainmentNext`, whose first assertion *is* the changed behavior, keeping its resolve-failure coverage | done | found only when the full suite ran — the second class was not in the file I thought I had edited |
| T5 | MCP-REG-01: the clause, the amendment note and the `Cwd existence, not containment` scenario | done | spec diff; `check_test_mapping.py` exit 0 |
| T6 | Rule-14 gate: `cli.py` at 100.00% with no pragma | done | `check_core_coverage.sh` exit 0; `cli.py 613 0 178 0 100%` |
| T7 | Full gates | done | `2011 passed, 6 skipped`; ruff/format/mypy/pyright clean; coverage TOTAL 94% |
| T8 | Commits + push + PR | pending | PR URL |

---

## Constraints honoured

- **No `# pragma: no cover` anywhere.** An earlier draft guarded `root.resolve()` with one; it was
  removed by simplifying the loop, because an untestable branch is a design smell, not a reason to
  silence coverage.
- **`cli.py` stays at 100.00%** — both new branches (the refusal and the warning) are executed by the
  new tests.
- **Server-root containment untouched:** `_contained_path`, `_get_root`, `PathOutsideRootError` and
  `build_server` are absent from the diff.
- No `pyproject.toml`, `uv.lock`, `openspec/project.md`, `openspec/config.yaml` or registry change; no
  new requirement; no Test Mapping row; no README change in this slice.

---

## Carried to slice 2

The `$HOME` resolution defect itself — `--user-config PATH` on `mcp add`/`mcp remove` with precedence
over the adapter's `user_env_dir` and `Path.home()`; `--user-config` rejected with `--agent all`; the
account-home mismatch warning; MCP-REG-01's resolution clause; CLI-R09's flag enumeration; and both
READMEs' flags and per-agent-location tables. Contract already decided in
`odd/tasks/mcp-user-config-resolution.md`.
