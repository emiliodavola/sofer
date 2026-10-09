# Proposal — `2026-10-09-feat-mcp-explicit-root`

> **Change** `2026-10-09-feat-mcp-explicit-root` · issue **#273**
> (*MCP: the documented explicit containment root does not exist*) · branch
> `feat/273-mcp-explicit-root` from `dev@b05d977` · store **hybrid** (this file + Engram mirror).
>
> **Status:** proposal complete, implemented and verified in the same branch.

---

## 1. Intent

`README.md` tells users *"The server inherits its working directory — pass an explicit root when
the agent should only reach a specific tree"*. No explicit root exists. Measured in the tree:

- `src/sofer/mcp_server.py::main()` calls `build_server()` with no argv parsing, no `--root`, and
  no `SOFER_MCP_ROOT` (the name appears nowhere in the package).
- `build_server(root=None)` resolves the containment root to `Path.cwd().resolve()` when no root is
  passed, so the root is **always** the host process cwd.

Every host that launches stdio MCP servers with its own cwd therefore cannot point the server at a
dataset tree, and every path-bearing tool is refused with `PathOutsideRootError`. This change makes
the documented behavior real: an explicit root at launch, with a documented precedence and a
fail-closed refusal for an invalid one.

## 2. Scope

### In scope

- `src/sofer/mcp_server.py`: `main(argv=None)` parses `--root PATH` and `SOFER_MCP_ROOT`, resolves
  by the documented precedence, validates the resolved root at startup, and passes it to
  `build_server(root=...)`. Two module-level constants name the flag and the env var (AGENTS.md
  rule 1).
- `openspec/specs/mcp-server/spec.md`: MSP-R01 amended — one clause in the requirement body plus one
  new scenario.
- `tests/test_mcp_process.py`: a new `TestExplicitRoot` class driving `main()` in-process.
- `README.md` + `README_ES.md` (same edit, rule 13): the false sentence corrected, the flag/env var
  and precedence documented, and the Windows `MCP cwd param` rows extended.
- SDD record under `openspec/changes/2026-10-09-feat-mcp-explicit-root/`.

### Out of scope (non-goals, strictly respected)

- **No containment change.** `_contained_path`, `_get_root`, `PathOutsideRootError`, and every
  tool's path resolution are untouched. The new root flows through the existing `build_server`
  argument; the containment checks are exactly as before.
- **No `build_server` signature change.** `build_server(root=..., approval_phrase=...)` is spec'd
  (MSP-R01, MSP-R05) and the suite drives it directly; only `main` learns the flag.
- **No per-file coverage pragma.** `mcp_server.py` is not one of the four rule-14 modules, so there
  is no floor — and no `# pragma: no cover` is added anywhere.
- **No Test Mapping row.** `mcp-server` is a permanent declared backlog spec; the registry is not
  edited.
- **No commit, stage, push, or branch creation.** The parent owns delivery.
- No `pyproject.toml`, `uv.lock`, `openspec/project.md`, `openspec/config.yaml`, or `odd/` change.

## 3. Settled decisions

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | Precedence is explicit `--root PATH` > `SOFER_MCP_ROOT` > resolved process cwd. | Mirrors the existing approval-phrase resolution (explicit argument > env var > none) so the server has one precedence idiom; the cwd default stays the documented behavior. |
| **D2** | `main` takes `argv: Sequence[str] | None = None` (`None` → `sys.argv[1:]`). | Lets a test drive the real entry point in-process without a subprocess; this is the precedent the repository already uses for `sofer.cli.main` (rule 14's `runpy` guard test) and the existing process-boundary suite's in-process `build_server` calls. |
| **D3** | An invalid root refuses with a stderr message naming the **resolved** path and `SystemExit(1)`, before `build_server` runs. | A stdio server's non-zero exit is the fail-closed signal; naming the resolved path makes a bad launcher argument diagnosable. Refusing before building guarantees no tool can ever serve from an unrelated cwd. |
| **D4** | A blank/whitespace-only `SOFER_MCP_ROOT` counts as unset. | Matches the existing fail-closed treatment of a blank `SOFER_MCP_APPROVAL_PHRASE` (`_resolve_approval_phrase`); an empty variable is a launch mistake, not a root. |
| **D5** | The contract lands as a **MODIFIED** MSP-R01 block, not a new requirement. | MSP-R01 owns the transport and entry point; the launch root is part of how that entry point starts. Precedent: MSP-R03 was amended the same way. |

## 4. Issue #273 acceptance mapping

| AC | Acceptance criterion | Satisfied by |
| --- | --- | --- |
| **AC1** | `sofer-mcp --root PATH` and `SOFER_MCP_ROOT` both set the root | `_resolve_root` + the `TestExplicitRoot` flag/env tests |
| **AC2** | Precedence: explicit argument > env var > resolved cwd | `_resolve_root` ordering + `test_root_flag_beats_env_var` / `test_default_root_is_resolved_process_cwd` |
| **AC3** | Containment semantics unchanged, fail-closed | `build_server(root=root)` reuses `_contained_path` untouched; `test_root_flag_sets_containment_root` resolves a tool inside the chosen root |
| **AC4** | Invalid/missing root refuses at startup, naming the resolved path | `main` validation + `test_missing_root_refuses_at_startup` / `test_file_root_refuses_at_startup` |
| **AC5** | The false README sentence is fixed and the flag + precedence documented | `README.md` + `README_ES.md` edits (rule 13) |

## 5. Affected areas

| Area | File | Change class |
| --- | --- | --- |
| Entry point | `src/sofer/mcp_server.py` | additive (`_resolve_root` + `main` argv/validation, 2 constants) |
| Tests | `tests/test_mcp_process.py` | additive (1 class, 7 tests) |
| Spec | `openspec/specs/mcp-server/spec.md` | modification (MSP-R01 clause + scenario + note) |
| Docs | `README.md`, `README_ES.md` | modification (false sentence, Windows row, security-model parenthetical) |
| SDD | `openspec/changes/2026-10-09-feat-mcp-explicit-root/**` | new |

**Code + tests + docs: well inside the review budget.** Single PR, no chaining.

## 6. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A host that relied on the cwd default sees a behavior change | Very low | The default is unchanged (cwd, resolved); only an explicit root or env var changes it, and both are opt-in |
| R2 | An invalid root exits before the MCP handshake, which a host might report as a cryptic crash | Low | By design (D3): the stderr message names the resolved path and the reason, so the host's captured stderr is diagnostic |
| R3 | Adding `argparse` changes `sofer-mcp --help` behavior | Positive | `argparse` gives `--help` a clean exit 0, which MSP-R02 already requires |
| R4 | `main`'s new argv parameter could break the console-script entry point | Very low | The entry point calls `main()` with no arguments; `argv=None` reads `sys.argv[1:]`, the intended behavior |

## 7. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | The new `TestExplicitRoot` tests are red before the `mcp_server.py` edit and green after |
| SC-2 | `uv run pytest tests/test_mcp_process.py -q` green with no reduction in the passed tally |
| SC-3 | `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/`, `uv run mypy src/ scripts/`, and `uv run pyright` all green |
| SC-4 | `_contained_path`, `_get_root`, `PathOutsideRootError`, and `build_server`'s signature are byte-identical |
| SC-5 | `README.md` and `README_ES.md` document the flag, the env var, and the precedence with identical section structure |
| SC-6 | No `# pragma: no cover` added; `test-mapping-registry.md` untouched |

## 8. PR boundary

**Boundary: one PR, no chaining.** The change is a single, small entry-point capability whose code,
spec clause, tests, and docs are mutually dependent.

## 9. Non-goals (restated for the spec delta)

No containment behavior change; no edit to `_contained_path`, `_get_root`, `PathOutsideRootError`,
or any tool's path resolution; no `build_server` signature change; no `# pragma: no cover`; no Test
Mapping row or registry edit; no `pyproject.toml`, `uv.lock`, `openspec/project.md`,
`openspec/config.yaml`, or `odd/` change; no commit/stage/push/branch from SDD phases.
