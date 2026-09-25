# Proposal: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

## Intent

The two READMEs are the project's most-read interface description, and three approved
issues show they contradict the shipped tree: the MCP summary row under-reports the
surface by 3 tools and 1 resource and hides `sofer://status`; three flag rows omit
subcommands that accept the flag; and copy-pasteable examples embed the maintainer's
local username and handle. AGENTS.md rules 7 and 13 require the README to reflect the
current CLI interface and the two files to stay mirrored.

## Scope

### In Scope

- `README.md` + `README_ES.md`: state **14 tools / 4 resources / 3 prompts** in both the
  summary row and the MCP paragraph, and document the static `sofer://status` resource.
- `README.md` + `README_ES.md`: complete the `--force`, `--dry-run`, and `--output DIR`
  flags-table rows against the argparse definitions in `src/sofer/cli.py`.
- `README.md` + `README_ES.md`: replace `elaze`/`emiliodavola` example literals with
  generic placeholders consistent with the file's own precedent.

### Out of Scope

- The canonical-spec `user="emiliodavola"` literals in `openspec/specs/mcp-server/spec.md`
  and `openspec/specs/process-boundary/spec.md` (#180 second scope) — routed to the specs PR.
- The optional `tests/test_docs_placeholders.py` guard (conditional in the issue; not added).
- `openspec/changes/archive/**` (frozen audit record).
- Any source, CLI, spec, or workflow change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a published-documentation correction; no spec-governed behavior changes. The
MCP surface, the CLI flags, and the placeholder contract are already governed by
`mcp-server`, `cli`, and `process-boundary`; the README is brought back into agreement with
them.

## Approach

Edit the mirrored README sections in place: update the two MCP count sites and append the
`sofer://status` description; extend the three flags-table rows (and the `--output`
description for `codebook`); substitute the local-path/handle literals with the generic
forms. No spec delta and no code change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `README.md` | Modified | MCP counts + `sofer://status`; flags rows; placeholder examples |
| `README_ES.md` | Modified | Mirrored edits (rule 13) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| README-reading tests break | Low | Preserve every pinned token; run focused tests + full suite |
| Rule-13 mirror drifts | Low | Edit both files in the same sections/order |
| `sofer://status` description diverges from `_resource_status` | Low | Fields copied from the handler; independently verified |

## Rollback Plan

Revert the single README commit (`git revert 710a3e5` or restore both files from the merge
base). No source, spec, or workflow state is touched.

## Dependencies

None.

## Success Criteria

- [ ] Both READMEs state 14 tools / 4 resources / 3 prompts and list `sofer://status`.
- [ ] The three flags rows list every accepting subcommand, verified against `cli.py`.
- [ ] `git grep -i elaze -- README.md README_ES.md` returns nothing; no `user="emiliodavola"` example remains.
- [ ] README.md and README_ES.md stay mirrored.
- [ ] `uv run pytest tests/ -q` green and the lint/type gates clean.
