# Design: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

## Technical Approach

Three coupled documentation edits, applied identically to both mirrors:

1. **MCP surface** — replace the summary-row count and the MCP-paragraph count with
   `14 tools, 4 resources, 3 prompts`, add `sofer://status` to the resource list, and add a
   short paragraph describing it as a static resource with no path variables.
2. **Flags table** — extend the `--force`, `--dry-run`, and `--output DIR` rows to list
   every accepting subcommand, verified against the argparse builder; adjust the `--output`
   description for `codebook`.
3. **Placeholders** — replace `C:/Users/elaze/...`, `C:\Users\elaze\...`,
   `user="emiliodavola"`, and `--user emiliodavola` with `C:/Users/.../...`,
   `C:\Users\...\...`, `user="<hf-user>"`, and `--user <hf-user>`.

No source change, so no runtime behavior is altered.

## Architecture Decisions

### Decision: Correct the READMEs to the code, never the code to the READMEs

**Choice**: The README states what `mcp_server.py` and `cli.py` actually register.
**Alternatives considered**: Trim the MCP surface or the flag registrations to match the docs.
**Rationale**: The code is the shipped contract and is covered by tests; the README is a
description. AGENTS.md rule 7 makes the README a truth obligation, not a spec.

### Decision: Count resources as 4 registrations (3 templates + 1 static)

**Choice**: Report `4 resources` and name `sofer://status`.
**Alternatives considered**: Report `3 templates + 1 static` only.
**Rationale**: Both are true; the summary row needs a single count, and `4` matches the
four `server.resource(` registrations and the runtime `resources/list` + `resources/templates/list`
split. The body additionally names the static resource so the reader sees why the count is 4.

### Decision: Keep the canonical-spec de-identification out of this PR

**Choice**: README-only.
**Alternatives considered**: Include the `openspec/specs/*` example literals here.
**Rationale**: The maintainer's decided split files canonical-spec edits under the specs PR
(branch `docs/specs-veracity-sweep`); AGENTS.md rule 13 scopes this PR to the READMEs.

## Data Flow

    cli.py argparse registrations ──┐
    mcp_server.py registrations ────┼──> README.md  ==  README_ES.md (same counts/tokens)
    _resource_status() keys ────────┘

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Modify | Summary row; MCP paragraph + status note; 3 flag rows; placeholder literals |
| `README_ES.md` | Modify | Mirrored edits |

## Interfaces / Contracts

Documented MCP contract (after this change): 14 tools, 4 resources
(`sofer://dataset/{config}`, `sofer://codebook/{data_file}`,
`sofer://metadata/{data_file}`, `sofer://status`), 3 prompts.

Documented flags contract (after this change):
`--force` → init, prepare, publish, profile, render, scan;
`--dry-run` → init, publish, scan (+ mcp add/remove);
`--output` → codebook, prepare, publish, profile, render.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Static | README tokens still present | `tests/test_mcp_server.py::TestBuildClarityReadme` |
| Static | README/docs layout diagram | `tests/test_scanner.py -k docs_show_diagram` |
| Full | No collateral regression | `uv run pytest tests/ -q` |
| Independent | Counts/flags/placeholders match the tree | Read-only verifier (see verify-report) |

## Threat Matrix

N/A — no routing, shell/subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary changes. Markdown prose only.

## Migration / Rollout

None. Documentation is immediately in effect.

## Open Questions

None.
