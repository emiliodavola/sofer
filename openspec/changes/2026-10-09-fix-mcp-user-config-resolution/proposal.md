# Proposal — `2026-10-09-fix-mcp-user-config-resolution`

> **Change** `2026-10-09-fix-mcp-user-config-resolution` · issue **#274** · branch
> `fix/274-cwd-containment-gate` from `dev@69f5051` · store **hybrid** (this file + Engram mirror).
>
> **Status:** slice 1 of 2 implemented; slice 2 carried as an explicit follow-up (see §5).

---

## 1. Intent

Issue #274 reports that `sofer mcp add --scope user` resolves the agent's config under
`Path.home()`, which follows `$HOME`, while agents such as opencode resolve their global config from
the **system account home** — so the entry lands in a file the agent never reads and sofer reports
success.

Exploring that report surfaced a second, independent defect **inside the same code path**, and this
slice fixes that one:

**`validate_cwd` was a false gate.** It refused any `--cwd` outside `Path.home()` or the process
cwd. Measured, all five of these are true:

1. **Undeclared.** No spec clause described or enforced it — MCP-REG-01 had no containment clause at
   all. A rule that refuses configurations was enforced and unwritten.
2. **Scope-blind.** Its `user` and `project` branches were the *same expression*, so its `scope`
   parameter lied to every reader.
3. **Effectively untested.** The only "rejection" test monkeypatched the function to `False`, and
   11+ other tests bypass it. Nothing verified the rule itself.
4. **Protecting no privilege boundary.** The caller of `sofer mcp add` is the human, who can edit the
   agent's config directly; and since #273 the server root is explicitly settable
   (`--root`/`SOFER_MCP_ROOT`), so the config's `cwd` is no longer the only lever on containment.
5. **Rejecting legitimate trees while accepting a real mistake.** It refused any tree outside `$HOME`
   and the process cwd — exactly the reported container layout (`/workspace/test` with home
   `/opt/data`) — and it *accepted a nonexistent path* under either root. The RED run demonstrates
   it: `DRY RUN  Would register opencode at ...\nope\opencode.json`, exit 0.

The fix replaces the false gate with the check that catches the mistake that matters — the `--cwd`
must be an existing directory — and turns the unusual-but-legitimate case into a **named** one
instead of a silent refusal or a silent acceptance.

## 2. Scope

### In scope

- `validate_cwd` rule change: existence, not containment. The dead `scope` parameter is removed.
- A new `outside_root_warning`: informational, names the resolved cwd and the roots it is outside of.
- `cli.py`'s `_cmd_mcp_add` caller: refuse on a non-directory, warn on an outside-root directory.
- MCP-REG-01 gains the clause and a scenario — the rule stops being undeclared.
- The tests that exercise the **real** rule, replacing a test that bypassed it.

### Out of scope (non-goals)

- **The `$HOME` resolution defect itself** — the `--user-config` flag, the `--agent all` rejection,
  the account-home mismatch warning, and the README tables. That is slice 2 (§5).
- **The server-root containment**: `_contained_path`, `_get_root`, `PathOutsideRootError`,
  `build_server` and every tool's path resolution are untouched.
- No `pyproject.toml`, `uv.lock`, `openspec/project.md` or `openspec/config.yaml` change; no new
  requirement; no Test Mapping row (`mcp-registration` is a permanent declared-backlog spec).

## 3. Settled decisions

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | `--cwd` is refused **only** when the resolved path is not an existing directory. | That is the mistake worth failing on; the old rule failed on a policy opinion and missed this. |
| **D2** | An existing directory outside home and the process cwd is **accepted with a warning** naming both sides. | The explicit declaration wins; the odd case stays visible. Coherent with the rest of #274, whose theme is "the explicit declaration wins and anything suspicious is named". |
| **D3** | The dead `scope` parameter is **removed**. | Two identical branches make the parameter noise. If it cannot mean anything it must not appear to. |
| **D4** | The rule is **declared** in MCP-REG-01, with the removal rationale recorded beside it. | This repo's discipline is that declarations are true and recorded. The next reader of that function deserves to know why it stopped refusing. |

## 4. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | The new tests are red before the change and green after, including the test that exercises the real rule |
| SC-2 | `cli.py` stays at **100.00%** line coverage and `scripts/check_core_coverage.sh` exits 0 — `cli.py` is an AGENTS.md rule-14 module, and no `# pragma: no cover` is added |
| SC-3 | The full suite is green with the expected delta, and no other test changes status |
| SC-4 | MCP-REG-01 carries the clause and the scenario; `check_test_mapping.py` still exits 0 and the registry is untouched |
| SC-5 | `_contained_path`, `_get_root`, `PathOutsideRootError` and `build_server` are absent from the diff |

## 5. Slice 2 — the follow-up this change does not deliver

The `$HOME` resolution defect itself remains open, and its contract is already decided (recorded in
`odd/tasks/mcp-user-config-resolution.md`): `--user-config PATH` on `mcp add`/`mcp remove` with
precedence over the adapter's `user_env_dir` and `Path.home()`; `--user-config` rejected with
`--agent all`; an account-home mismatch warning; MCP-REG-01's resolution clause; CLI-R09's flag
enumeration; and both READMEs' flags and per-agent-location tables.

It is carried as a second, single-purpose change rather than folded here, because the two defects
are independent and each PR should carry one reason to exist.

## 6. Non-goals (restated for the spec delta)

No change to the server-root containment; no `--user-config` flag in this slice; no version bump; no
new requirement; no Test Mapping row; no registry edit; no README change (nothing user-facing in this
slice changes the documented flag set); no commit/push/PR from SDD phases.
