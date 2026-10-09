# Design — `2026-10-09-feat-mcp-user-config-flag`

> **Change** `2026-10-09-feat-mcp-user-config-flag` (issue **#274**) · branch
> `feat/274-mcp-user-config-flag` from `dev@22877b0` · store **hybrid**.

---

## 1. The defect, precisely

`resolve_config_path`'s user branch ended with:

```python
env_dir = spec["user_env_dir"]
override = os.environ.get(env_dir) if env_dir else None
if override:
    return Path(override).joinpath(spec["user_parts"][-1])
return Path.home().joinpath(*spec["user_parts"])
```

`Path.home()` follows `$HOME`. opencode resolves its global config from the **account** home and
ignores `$HOME`, so the entry could be written into a file the agent never reads — with sofer printing
`OK`. Nothing in the package could override the path.

## 2. The edits

### 2.1 `src/sofer/mcp_registration.py`

`resolve_config_path(agent, scope, cwd=None, user_config=None)` — the fourth parameter is new and
optional, so every existing caller keeps working. User scope resolves in the documented order: a
non-blank `user_config` (returned as the stated **file** path, expanded and resolved), then the
adapter's `user_env_dir`, then `Path.home()`. Project scope ignores `user_config`.

`_account_home()` — new. Returns the passwd home on POSIX, `None` on Windows or for a uid without an
entry. The platform guard is `sys.platform == "win32"`, not `os.name != "posix"`: **mypy narrows
`sys.platform`** and therefore prunes the POSIX-only `pwd` and `os.getuid` attributes, so the module
type-checks on both platforms. With `os.name` it did not, and `mypy src/ scripts/` failed with two
`attr-defined` errors on Windows — a real failure for this repository's Windows contributor, not a
theoretical one.

`home_mismatch_warning()` — new. Returns a stderr-ready message naming both homes, or `None` when they
agree or no account home is available. The marker is `"  !  "`, matching the repo's existing
informational-warning marker.

### 2.2 `src/sofer/cli.py`

- `--user-config` added to **both** subparsers, with help text stating the precedence and the `all`
  rejection (AGENTS.md rule 7: the help moves with the behaviour).
- Both handlers reject `--user-config` with `--agent all` before any write, and print the mismatch
  warning for `--scope user`.
- Both resolve calls pass `user_config` through.
- The `mcp add` description states the new resolution.

`cli.py` is an AGENTS.md rule-14 module. The new lines are covered by the refusal test, the warning
tests on both subcommands, and the declared-path tests, and the file measures **100.00%** with no
pragma added.

### 2.3 Specs

MCP-REG-01 gains the resolution clause and a `User-scope config resolution` scenario; CLI-R09 gains the
flag in its enumeration, in the help scenario, and in a new paragraph stating the `all` rejection.
Both are permanent declared-backlog specs: no Test Mapping rows, registry untouched.

### 2.4 Tests

Thirteen tests in a new `TestUserConfigResolution` class: the precedence (flag over env over home),
each step's regression guard, blank-as-unset, project-scope indifference, the `all` rejection on both
subcommands, the declared path actually used on both subcommands, the warning naming both homes, and
the warning's two `None` cases (homes agree; no account home).

## 3. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change adds a capability rather than altering
one. The carrier is a real red-then-green:

| Gate | RED (measured) | GREEN (measured) |
| --- | --- | --- |
| `pytest tests/test_mcp_registration.py::TestUserConfigResolution` | **10 failed, 3 passed** | **14 passed, 2 skipped** |
| `pytest tests/test_mcp_registration.py tests/test_cli.py` | — | `314 passed, 3 skipped` |
| `pytest tests/ -q` | — | `2028 passed, 8 skipped` (base `2012/6`; +16 = 16 new tests, +2 POSIX-only skips) |

**Two tests were strengthened after the fact, and one of them was vacuous.** The first draft of
`test_cmd_remove_uses_the_declared_user_config` used `dry_run=True` with a nonexistent file, where
removal writes nothing and exits 0 regardless — it passed against the old code and proved nothing. It
now runs with `dry_run=False` and asserts the declared file was **mutated**, which is the only way to
show the declared path was consulted. The same class of weakness was caught by an independent verifier
in slice 1 (`"SHALL NOT write"` asserted under `dry_run=True`), which is why it was looked for here.

## 4. Platform-specific coverage — stated rather than hidden

`mcp_registration.py` measures **98%** locally and **100%** on the Linux coverage job. Lines 267-272
are the POSIX-only path (`import pwd`, `getpwuid`), unreachable on this Windows host because the two
tests covering them are `skipif`-guarded — they would otherwise error on `import pwd` and break the
Windows test matrix. `cli.py` is 100% on both platforms, and `check_core_coverage.sh` (the four
rule-14 gates) exits 0 locally.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A user passes `--user-config` expecting a **directory** | Low | The help text and both READMEs say **file**. The flag is returned as the resolved path itself, so a directory would produce a confusing failure rather than a silent one. |
| R2 | The mismatch warning is noise for users whose homes agree | Low | It returns `None` when they agree; there is a test for that case. |
| R3 | Raising the exit code for a home divergence would be over-reach | Low | Deliberately not done: a divergence is information, not an error (D3). |

## 6. Rollback

Revert-only. `--user-config` is additive (a new optional parameter with a default), the `all` rejection
and the warning are new guards, and no existing resolution path changed except by gaining a
higher-precedence step. No state, no migration, no runtime impact outside `mcp add`/`mcp remove`.

## 7. Success criteria

SC-1..SC-6 of `proposal.md` §4. The runtime evidence for SC-2 is recorded in the verify report.
