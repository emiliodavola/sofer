# Exploration: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

## Current State

Three approved read-only gap-analysis findings make the published READMEs (the project's
single most-read surface) contradict the tree.

**#183 — MCP surface counts stale and `sofer://status` undocumented.** `README.md:332` /
`README_ES.md:344` summarise the server as `(11 tools, 3 resources, 3 prompts)`, but
`src/sofer/mcp_server.py` registers **14** `server.tool(` callables (`_register_tools`
docstring) and **4** resources — the three rest-pattern templates
(`sofer://dataset/{config_path*}`, `sofer://codebook/{data_file*}`,
`sofer://metadata/{data_file*}`) plus the static `sofer://status` added by MSP-R07. The
same README body already says "14 tool callables" but lists only 3 resources and never
mentions `sofer://status`, so the file contradicts itself.

**#190 — flags-at-a-glance under-reports availability.** The summary table rows for
`--force` (`prepare`, `publish`, `scan`), `--dry-run` (`publish`, `scan`) and
`--output DIR` (`prepare`, `publish`, `profile`, `render`) each omit subcommands that
accept the flag in `src/sofer/cli.py`: `--force` is also on `init`/`profile`/`render`,
`--dry-run` is also on `init`, and `codebook` accepts `-o`/`--output`.

**#180 — maintainer-local identity in copy-pasteable examples.** `git grep -i elaze --
README.md README_ES.md` returns 4 mirrored pairs (`C:\Users\elaze\...` and the
`C:/Users/elaze/...` MCP `cwd`), plus `user="emiliodavola"` / `--user emiliodavola` in
the greenfield chain. A reader cannot run the examples, and the local layout leaks.

## Affected Areas

- `README.md` — summary table row; flags table rows; Windows notes table; greenfield CLI/MCP chain.
- `README_ES.md` — mirrored sections only.

## Approaches

1. **Correct the three surfaces in place, READMEs only** (recommended) — minimal, faithful,
   and keeps rule 13's mirror contract. No spec or source change.
2. **Regenerate the READMEs from a single generator** — rejected: out of scope, and the
   README is hand-maintained with deliberate MCP-extra notes.
3. **Move the `--user emiliodavola` example to a spec-only fix** — rejected by the maintainer's
   decided PR split; #180's README half stays in this PR and its canonical-spec half is
   routed to the specs PR.

## Recommendation

Approach 1. State 14 tools / 4 resources / 3 prompts and document `sofer://status`; list
every accepting subcommand in the three flag rows; replace `elaze`/`emiliodavola` example
literals with the file's own generic placeholders (`C:\Users\...\...`,
`C:/Users/.../...`, `<hf-user>`).

## Risks

- `tests/test_mcp_server.py::TestBuildClarityReadme` and
  `tests/test_scanner.py::TestSourceLayoutCopyOnly::test_docs_show_diagram` read the
  READMEs; they pin tokens (`Phase 0`, `sofer_*`, `force`, `raw/`, `cache`) that the edits
  preserve. No test pins the MCP counts, the flags table, or `elaze`.
- Rule 13 mirror: both files must change together in the same sections.
- `openspec/changes/archive/**` carries `C:\Users\elaze\...` as captured evidence and is
  frozen — the sweep excludes it.

## Ready for Proposal

Yes.
