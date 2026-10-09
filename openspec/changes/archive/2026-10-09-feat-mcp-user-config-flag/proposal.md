# Proposal — `2026-10-09-feat-mcp-user-config-flag`

> **Change** `2026-10-09-feat-mcp-user-config-flag` · issue **#274** · branch
> `feat/274-mcp-user-config-flag` from `dev@22877b0` · store **hybrid** (this file + Engram mirror).
>
> **Status:** proposal complete, implemented, verified and **archived inside this PR** (AGENTS.md
> rule 15).

---

## 1. Intent

`sofer mcp add --scope user` resolved the agent's config under `Path.home()`, which follows `$HOME`.
Agents such as opencode resolve their global config from the **system account home** and ignore both
`$HOME` and `XDG_CONFIG_HOME`. When the two disagree — a container, a supervised process, a service
account — sofer wrote the entry into a file the agent never reads **and reported success**. That
silent no-op is the defect: the worst shape of failure for an idempotent installer.

This is the issue's own defect. Slice 1 (change `2026-10-09-fix-mcp-user-config-resolution`,
delivered by #283) fixed a **different** defect found while exploring this one — the false `--cwd`
gate — and explicitly carried this work forward.

## 2. Scope

### In scope

- `--user-config PATH` on `mcp add` **and** `mcp remove`, with the documented three-step precedence.
- `--user-config` rejected with `--agent all`.
- A warning when `Path.home()` differs from the account home.
- The resolution contract and the flag declared in MCP-REG-01 and CLI-R09.
- Both READMEs: the flags table, the `--agent`/`--scope` row, and the per-agent locations table.

### Out of scope (non-goals)

- **The server-root containment** (`_contained_path`, `_get_root`, `PathOutsideRootError`,
  `build_server`) and every tool's path resolution — untouched.
- No version bump; no `pyproject.toml`, `uv.lock`, `openspec/project.md` or `openspec/config.yaml`
  change.
- No invented per-agent environment-variable names: agents do not read them, and the explicit flag is
  the contract.
- No Test Mapping rows (`mcp-registration` and `cli` are permanent declared-backlog specs) and no
  registry edit.

## 3. Settled decisions

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | `--user-config PATH` wins over the adapter's `user_env_dir` (Pi's `PI_CODING_AGENT_DIR`), which wins over `Path.home()`. | The explicit declaration wins. The `user_env_dir` mechanism already existed for Pi, so this generalizes a mechanism rather than inventing one. Always works, no guessing. |
| **D2** | `--user-config` with `--agent all` is **rejected**, exit 1, before any write. | Each agent has a different config file, so one path is ambiguous. The issue's proposal does not mention this — it is a real hole in it. |
| **D3** | The **mismatch warning** names both homes and fires for `--scope user` on both `add` and `remove`. | This is what removes the silent success, which is the worst part of the report. It does not change the exit code: a divergence is information, not an error. |
| **D4** | A blank or whitespace-only `--user-config` counts as **unset**, and project scope **ignores** it. | Matches the existing blank-approval-phrase treatment, and the declared file is a user-scope concept. |
| **D5** | The account home is read from `pwd` behind a **`sys.platform == "win32"`** guard, returning `None` off POSIX. | Windows has no passwd database. The `sys.platform` form is what lets mypy prune the POSIX-only `pwd`/`os.getuid` attributes, so the module type-checks on Windows *and* Linux; `os.name` does not narrow the same way. |
| **D6** | The two POSIX-only tests are `skipif`-guarded on `sys.platform == "win32"`. | The Windows matrix must not error on `import pwd`. The coverage they provide is measured on the Linux coverage job, where they run. |

## 4. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | The new tests are red before the change and green after (10 failed → 14 passed, 2 POSIX-only skipped) |
| SC-2 | `cli.py` stays at **100.00%** and `scripts/check_core_coverage.sh` exits 0 — it is a rule-14 module, and no `# pragma: no cover` is added |
| SC-3 | The full suite is green with the expected delta, and no other test changes status |
| SC-4 | MCP-REG-01 and CLI-R09 carry the contract; `check_test_mapping.py` exits 0 and the registry is untouched |
| SC-5 | `_contained_path`, `_get_root`, `PathOutsideRootError` and `build_server` are absent from the diff |
| SC-6 | The change folder and its `archive-report.md` live under `openspec/changes/archive/` in this same PR (rule 15) |

## 5. Non-goals (restated for the spec delta)

No change to the server-root containment; no version bump; no new requirement; no Test Mapping row; no
registry edit; no commit/push/PR from SDD phases; no `# pragma: no cover` anywhere.
