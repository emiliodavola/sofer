# Proposal — `2026-10-16-feat-mcp-doctor`

> **Change** `2026-10-16-feat-mcp-doctor` · issue **#322** · branch
> `feat/322-mcp-doctor` from `dev@24520b6` · store **hybrid**.
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

PR #311 writes each host's connect/startup deadline into the registration entry from a value chosen
against a *measurement* — the 16–32 s the `mcp-registration` spec quotes — rather than a measurement of
**this** machine. On a slower host, a cold container, or after a dependency lands in the import path,
the written value can be too small, and the failure is indistinguishable from a broken registration.
That is the symptom #287 exists to remove, and the diagnostic half of #287 was deliberately left out of
#311 (its archive report §5).

`sofer mcp doctor` is that half: spawn the real server, time the stdio `initialize` round trip, and print
the measurement beside the per-agent key and the value `sofer mcp add` would write there.

## 2. Scope

- `src/sofer/mcp_doctor.py` (new): entry-point resolution, the measurement, the per-agent rows, the
  report and its two renderings.
- `src/sofer/cli.py`: the `doctor` subparser, its help, and `_cmd_mcp_doctor`.
- `tests/test_mcp_doctor.py` (new): 35 tests.
- `openspec/specs/cli/spec.md`: CLI-R09 extended, CLI-R15 added.
- `openspec/specs/mcp-registration/spec.md`: MCP-REG-05 gains the diagnostic paragraph and a scenario.
- `README.md` + `README_ES.md`: the subcommand row and its two flags (rules 7 and 13).

Not in scope: changing any written default, touching a config file, or re-measuring the 16–32 s figure
the specs quote — see `design.md` §6.

## 3. Approach

- **Measure the round trip, not import time.** The host deadline covers connect *and* handshake, so
  import timing measures the wrong thing (issue #322 §"Proposed solution" 1).
- **Informational exit code.** Exceeding the budget does not fail; only "nothing could be measured"
  does. Same contract as `dropped_timeout_note` and the OpenCode env-drop warning.
- **Single-sourced values.** Every key and value a row reports comes from `timeout_entry_keys`, so the
  doctor cannot disagree with what `mcp add` writes.
- **No MCP SDK import.** The module must load without the optional `mcp` extra, because one of its most
  useful answers is "the server could not start".

## 4. Success criteria

- SC-1: a real `initialize` round trip is measured and reported in milliseconds.
- SC-2: `--json` emits the CLI-R10 stable-key object, never a `repr`.
- SC-3: each agent's row equals what `sofer mcp add` would write, with the adapter's own unit.
- SC-4: an agent with no timeout key carries the MCP-REG-05 note and no invented value.
- SC-5: exceeding the budget never changes the exit code; an unmeasurable launch exits 1.
- SC-6: the full gate set is green, including `cli.py` at 100.00% (rule 14).
