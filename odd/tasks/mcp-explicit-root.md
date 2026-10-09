# Feature: mcp-explicit-root — issue #273

**Branch:** `feat/273-mcp-explicit-root` from `dev@b05d977`
**Issue:** `emiliodavola/sofer#273` — *`sofer-mcp` accepts no explicit root (`--root` / `SOFER_MCP_ROOT`) while the README tells users to pass one*
**SDD change:** `openspec/changes/2026-10-09-feat-mcp-explicit-root/`

## Goal

The README told users to pass an explicit root, and no such lever existed. The containment root was
always the host process cwd, so every host that launches stdio servers with its own cwd could not
point the server at a dataset tree, and every path-bearing tool was refused. Add the flag and the env
var, keep the fail-closed containment semantics, and make the documentation true.

## The contract, taken from the issue (no product decision was pending)

1. `sofer-mcp --root PATH` and `SOFER_MCP_ROOT`; the explicit argument wins over the environment,
   which wins over today's default (the process cwd, resolved).
2. Containment semantics unchanged: a path outside the resolved root is still refused with
   `PathOutsideRootError`, fail-closed, no fallback.
3. An invalid or missing root refuses **at startup**, naming the resolved path, instead of silently
   rooting at an unrelated cwd.
4. The README sentence and the Windows-notes cwd entry document the flag and the precedence, and
   keep "root defaults to the process cwd" as the stated default.

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: tests for `--root`, `SOFER_MCP_ROOT`, precedence, cwd default and startup refusal | done | 7 failed before the implementation (`TypeError: main() takes 0 positional arguments but 1 was given`) |
| T2 | GREEN: argv + env resolution in `main()`, fail-closed on an invalid root | done | 7 passed; `tests/test_mcp_process.py` 14 → 21 tests |
| T3 | MSP-R01: contract clause + scenario + attribution note | done | spec diff |
| T4 | `README.md` + `README_ES.md` (rule 13) + Windows-notes cwd row + security-model bullet | done | 13 lines each, symmetric |
| T5 | Independent verification of the full gate set | in progress | delegated (background) |
| T6 | Commits + push + PR against `dev` | pending | — |

## Design notes

- `main(argv: Sequence[str] | None = None)` resolves the root via `_resolve_root`, validates
  `root.is_dir()` **before** building the server, and refuses with `SystemExit(1)` plus a stderr
  message naming the **resolved** path.
- `build_server(root=..., approval_phrase=...)` keeps its signature and body — it is spec'd
  (MSP-R01/MSP-R05) and driven directly by the existing suite.
- Root names are module constants (`_MCP_ROOT_ENV_VAR`, `_MCP_ROOT_FLAG`), per AGENTS.md rule 1. A
  blank/whitespace-only env value is treated as unset, matching the blank approval-phrase treatment.
- `mcp-server` is in the permanent declared backlog, so the new scenario needs no Test Mapping row,
  and `openspec/test-mapping-registry.md` was not touched.
- `src/sofer/mcp_server.py` is **not** a rule-14 module, so no per-file 100% floor applies — and no
  `# pragma: no cover` was added.

## Behavior change, declared and accepted

`main()` now parses argv with `argparse`, so two things change versus the old no-parse entry point:

- `sofer-mcp --help` exits 0 instead of starting the stdio server (an improvement; the writer flagged
  it).
- An **unknown argument now fails** instead of being silently ignored.

The second one is accepted deliberately, and it is not merely tolerable: a silently ignored flag is
**exactly the failure mode this issue exists to remove**. `--rot /data` (a typo) under tolerant
parsing would start the server rooted at the cwd — the same silent mis-rooting that #273 fixes. Failing
loudly on a typo is the fail-closed behavior this change is about.

Repo-side check that nothing depends on the old tolerance: every registration in the repo writes the
bare command (`tests/test_mcp_registration.py` asserts `entry["command"] == "sofer-mcp"` /
`["sofer-mcp"]`), and the stdio boundary fixtures spawn the entry point with no extra arguments.

## Contradiction found in the parent's brief

The brief asserted that `tests/test_mcp_process.py` already ran `main()` in-process. **It does not** —
that file drives `main` through a subprocess and otherwise uses in-process `build_server`. The real
in-process `main()` precedent is in `tests/test_cli.py` (runpy) and `tests/test_config.py`
(`sofer.cli.main(argv)`). The implementer followed the true precedent instead of the brief's claim.
Lesson: the parent must verify a claimed precedent before writing it into a brief.

## Related

#272 (the `hermes` adapter) — this flag reduces its urgency: with an explicit root, any host can fix
its own containment without a new adapter.
