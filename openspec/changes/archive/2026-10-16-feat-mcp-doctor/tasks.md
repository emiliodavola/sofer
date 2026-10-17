# Tasks: feat-mcp-doctor

**Change** `2026-10-16-feat-mcp-doctor` (GitHub **#322**) · branch `feat/322-mcp-doctor` from
`dev@24520b6` · store **hybrid**.

**Inputs read this phase, directly:** `odd/tasks/mcp-doctor.md` (specification of record),
`proposal.md` and `design.md` of this change, and issue #322.

**One-line outcome:** `sofer mcp doctor` reports this machine's real cold start beside the key and
value `sofer mcp add` writes, and never fails because a machine is slow.

---

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Branch `feat/322-mcp-doctor` off `dev@24520b6` | — | git | done | `git rev-parse --short HEAD` = `24520b6` |
| T2 | Feature doc written before the first source edit | — | inline | done | `odd/tasks/mcp-doctor.md` |
| T3 | Probe the real stdio handshake (framing + baseline) | S1 | inline | done | line-delimited JSON-RPC confirmed; 1874 / 1718 ms |
| T4 | RED: 35 tests, transport injected, one real spawn | S1–S6 | inline, test-first | done | `35 failed` against the `NotImplementedError` skeleton |
| T5 | `src/sofer/mcp_doctor.py` | S1 S3 S4 S6 | inline | done | `tests/test_mcp_doctor.py` 35 passed |
| T6 | `cli.py`: the `doctor` parser, help and `_cmd_mcp_doctor` | S2 S7 | inline | done | `TestCliSurface`; `test_mcp_help_lists_doctor` |
| T7 | `cli` spec: CLI-R09 extended, CLI-R15 added | S1–S8 | inline | done | `openspec/specs/cli/spec.md` + this change's delta |
| T8 | `mcp-registration` spec: MCP-REG-05 diagnostic | S8 | inline | done | `openspec/specs/mcp-registration/spec.md` + this change's delta |
| T9 | README + README_ES: subcommand row and flags | S2 | inline | done | both READMEs, same position |
| T10 | Gates: full suite, `cli.py` at 100.00%, ruff/format/mypy/pyright, test-mapping | — | inline | done | see the archive report |
| T11 | Archive inside the delivery branch (rule 15) | — | inline | done | this folder |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | see the archive report |
| `cli.py` 100.00% (rule 14) | see the archive report |
| TOTAL floor (≥ 90%) | see the archive report |
| ruff / format / mypy / pyright | clean |
| Test-mapping contract | `OK` |
| README / README_ES | both updated in the same change (rules 7, 13) |

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, and this change **did** honour red-green anyway: the
tests were written first, a skeleton with the full public surface and `NotImplementedError` bodies was
placed so the failure was a per-behaviour assertion rather than a collection `ImportError`, and
`35 failed` was observed before the implementation. The first draft of the tests was then corrected —
its per-agent row model assumed one key per agent, while `sofer mcp add` writes two deadlines for
codex and hermes and a single millisecond-valued key for gemini. The correction is recorded in
`design.md` §3.2 because it was a wrong premise, not a code defect.
