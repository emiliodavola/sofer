# Feature: mcp-user-config-resolution — issue #274

**Branch:** `feat/274-mcp-user-config` from `dev@69f5051`
**Issue:** `emiliodavola/sofer#274` — *`sofer mcp add --agent opencode` resolves the user config from `$HOME`, so the entry can land in a file the agent never reads*
**SDD change:** `openspec/changes/2026-10-09-fix-mcp-user-config-resolution/`

## Goal

`sofer mcp add --scope user` resolves the agent's config under `Path.home()`, which follows `$HOME`. Agents such as opencode resolve their global config from the **system account home** and ignore both `$HOME` and `XDG_CONFIG_HOME`. When those disagree — a container, a supervised process, a service account — sofer writes the entry into a file the agent never reads **and reports success**. That silent no-op is the defect: the worst shape of failure for an idempotent installer.

## The decisions — taken on our side, NOT inherited from the issue text

The issue is **evidence of a problem**, not a decision record. Its "Proposed solution" is a menu written by hand by the reporter, and its clause *"The containment rule for `--cwd` stays as is"* was **not** accepted as settled. Every decision below is ours, with the evidence that produced it.

| # | Decision | Why |
| --- | --- | --- |
| **D1** | `--user-config PATH` on `mcp add` and `mcp remove`. Precedence: `--user-config` > the adapter's `user_env_dir` (Pi's `PI_CODING_AGENT_DIR`) > `Path.home()`. | The explicit declaration wins. Precedent already exists in the registry (`user_env_dir`), so this generalizes a mechanism rather than inventing one. Always works, no guessing. |
| **D2** | `--user-config` with `--agent all` is **rejected**. | Each agent has a different config file, so a single path is ambiguous for `all`. The issue does not mention this; it is a real hole in its proposal. |
| **D3** | `--cwd` is refused **only** when the resolved path is not an existing directory; an existing directory **outside** home and the process cwd is **accepted with a warning naming both paths**. | The old rule was a **false gate**, measured: (a) it was **undeclared** — no spec clause anywhere enforced or described it; (b) it was **scope-blind** — `validate_cwd`'s two branches were the *same expression*, so its `scope` parameter lied to every reader; (c) it had **no real coverage** — the only "rejection" test monkeypatches the function to `False`, and 11+ other tests bypass it; (d) it protected **no privilege boundary** — the caller of `sofer mcp add` is the human, who can edit the agent's config directly, and since #273 the server root is explicitly settable (`--root`/`SOFER_MCP_ROOT`); (e) it **rejected legitimate configurations** — any tree outside `$HOME` and the process cwd, which is exactly the reported environment (`/workspace/test` with home `/opt/data`). |
| **D4** | The dead `scope` parameter is **removed** from `validate_cwd`. | With identical branches it is noise in the signature. If it cannot mean anything, it must not appear to. |
| **D5** | The containment rule is **declared** in MCP-REG-01, which has no containment clause today. | A rule that refuses configurations must be written down. This repo's discipline is that declarations are true and recorded; this one was enforced and unrecorded. |
| **D6** | Warning when `Path.home()` differs from the **account home** (`pwd.getpwuid(os.getuid()).pw_dir` on POSIX). | Removes the silent success, which is the worst part of the defect. On Windows there is no `pwd`; skip gracefully. |
| **D7** | READMEs updated in the same commit (rule 13): the flags table and the per-agent locations table. | The tables currently document the `$HOME`-derived paths as if they were the agent's real paths. |

**Considered and deferred, with reasons:** *ask the agent* (`opencode debug paths`, `CODEX_HOME`) — only works for agents that expose their paths, and does not fix the general case or the `--cwd` question; *`XDG_CONFIG_HOME`* — correct per the XDG spec but **insufficient**, because the issue measures opencode ignoring it.

## Tasks — slice 1 (the `--cwd` false gate): DONE

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: tests for the new `--cwd` rule, the warning and the CLI refusal | done | `8 failed`, including the run proving the old gate accepted a **nonexistent** cwd |
| T2 | GREEN: `validate_cwd(cwd)` existence rule, `scope` removed, `outside_root_warning` added | done | `8 passed` |
| T3 | `cli.py` caller: refuse on non-directory, warn on outside-root | done | `297 passed` on the focused files |
| T4 | Rewrite `TestCwdContainmentNext` (its first assertion *is* the changed behavior), keeping the resolve-failure coverage | done | found only when the full suite ran — a second class I had not seen |
| T5 | MCP-REG-01: clause + amendment note + `Cwd existence, not containment` scenario | done | `check_test_mapping.py` exit 0 |
| T6 | Rule-14 gate: `cli.py` at 100.00%, no pragma | done | `check_core_coverage.sh` exit 0; `cli.py 613 0 178 0 100%` |
| T7 | Full gates | done | `2011 passed, 6 skipped`; ruff/format/mypy/pyright clean; TOTAL 94% |
| T8 | Commits + push + PR | pending | — |

## Tasks — slice 2 (the `$HOME` resolution defect, the issue's own core): PENDING

| # | Task | State |
| --- | --- | --- |
| S1 | `--user-config PATH` on `mcp add`/`mcp remove`; precedence over `user_env_dir` and `Path.home()` | pending |
| S2 | Reject `--user-config` with `--agent all` (each agent has a different file) | pending |
| S3 | Account-home mismatch warning (`pwd.getpwuid(os.getuid()).pw_dir` on POSIX) | pending |
| S4 | MCP-REG-01 resolution clause; CLI-R09 flag enumeration and help scenario | pending |
| S5 | `README.md` + `README_ES.md` (rule 13): flags table + per-agent locations table | pending |

**Why two slices:** the two defects are independent, and each PR should carry one reason to exist.
Slice 1 is the decision taken on our side (the false gate); slice 2 is the issue's core fix. Splitting
also keeps `cli.py` — a rule-14 module — changing in two reviewable steps instead of one.

## Notes that condition the work

- **`cli.py` is an AGENTS.md rule-14 module: 100% line coverage, no `# pragma: no cover`.** Every new line needs a test that executes it, so the flag is designed with that in mind from the start, not retrofitted.
- The server-root containment (`_contained_path`, `_get_root`, `PathOutsideRootError`) is **untouched** — this change is about `mcp add`'s inputs, not the server's runtime containment.
- `mcp-registration` and `cli` are **permanent declared-backlog specs**: no Test Mapping rows, and `openspec/test-mapping-registry.md` is not touched.
- The one existing "rejection" test (`test_cmd_add_rejects_outside_root`) proves the caller's error handling, not the rule. This change adds the test that exercises the **real** rule — and that test fails against the current code, which is the honest RED for D3.
