# Tasks: feat-mcp-explicit-root

**Change** `2026-10-09-feat-mcp-explicit-root` (GitHub **#273**) · branch
`feat/273-mcp-explicit-root` from `dev@b05d977` · store **hybrid** — this file plus the Engram
mirror under topic key `sdd/2026-10-09-feat-mcp-explicit-root/tasks`.

**Inputs read this phase, directly:** `design.md` (this change) and `proposal.md` (this change).
No other document is consulted.

**One-line outcome:** `sofer-mcp` accepts `--root PATH` and `SOFER_MCP_ROOT` (argument wins over the
env var, which wins over the resolved process cwd), refuses an invalid root at startup with a
non-zero exit and a message naming the resolved path, and leaves containment semantics unchanged.

---

## TDD posture — stated honestly: the carrier is the new in-process entry-point tests

`openspec/config.yaml` sets `strict_tdd: false`, but this change adds a real runtime capability, so
the focused tests are a genuine red-then-green carrier:

- **RED (measured):** `pytest tests/test_mcp_process.py -q -k TestExplicitRoot` → `7 failed` with
  `TypeError: main() takes 0 positional arguments but 1 was given` (refusal tests) and
  `AttributeError` on `mcp_server._MCP_ROOT_ENV_VAR` (the rest).
- **GREEN (measured):** the same command → `7 passed`.

**REFACTOR has no target** — the change adds one resolution helper and one validation branch, with
no existing code to restructure.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | Write the `TestExplicitRoot` class (flag, env, precedence, cwd default, blank env, missing root, file root), **without** the `mcp_server.py` change | done | RED: `7 failed` (`TypeError` / `AttributeError`) |
| T2 | Add `_MCP_ROOT_ENV_VAR` / `_MCP_ROOT_FLAG` / reason constants and `_resolve_root(argv)` with the documented precedence | done | diff |
| T3 | Make `main(argv=None)` validate the resolved root and refuse before `build_server`, then build with `root=root` | done | GREEN: `7 passed` |
| T4 | Amend MSP-R01 in `openspec/specs/mcp-server/spec.md` (clause + scenario + note); no Test Mapping row | done | diff |
| T5 | Create the SDD delta under `openspec/changes/2026-10-09-feat-mcp-explicit-root/specs/mcp-server/spec.md` | done | diff |
| T6 | Correct the false sentence in `README.md` and `README_ES.md` (same edit, rule 13) | done | diff |
| T7 | Extend the Windows `MCP cwd param` rows and the security-model parenthetical in both READMEs | done | diff |
| T8 | Full gates: focused pytest, ruff check, ruff format --check, mypy, pyright | done | verify report |
| T9 | Work-unit commit(s) on the feature branch | done | `45a83d6` (feature, seven tests, both READMEs), `2df3aa7` (SDD record + harness tracking); PR #279 merged as `7c30aaa` |

---

## Constraints honoured

- **Containment unchanged.** `_contained_path`, `_get_root`, `PathOutsideRootError`, and every
  tool's path resolution are byte-identical; the new root arrives through the existing
  `build_server(root=...)` argument.
- **`build_server` signature unchanged** (MSP-R01/MSP-R05): `<root>`, `approval_phrase`.
- **No `# pragma: no cover`** added; `mcp_server.py` is not a rule-14 module and has no floor.
- **No Test Mapping row** and no edit to `openspec/test-mapping-registry.md` — `mcp-server` is a
  permanent declared backlog spec.
- **No `pyproject.toml`, `uv.lock`, `openspec/project.md`, `openspec/config.yaml`, or `odd/` change.**
- **No commit, stage, push, or branch creation** from the SDD phases; the parent owns delivery.
