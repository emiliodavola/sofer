# Delta for mcp-server

> **Change** `2026-10-09-feat-mcp-explicit-root` (GitHub **#273**) · branch
> `feat/273-mcp-explicit-root` from `dev@b05d977` · store **hybrid** (this file + Engram mirror).
>
> **One modification, no new requirement.** MSP-R01 (transport and entry point) gains the
> containment-root launch contract: the `--root PATH` flag, the `SOFER_MCP_ROOT` environment
> variable, the documented precedence, the unchanged containment semantics, and the fail-closed
> startup refusal. The requirement's existing clauses and scenarios are unchanged; only the one
> scenario added below is listed in this delta.
>
> **Rule-6 resolution.** `mcp-server` carries no `## Test Mapping` section and is recorded in
> `openspec/test-mapping-registry.md` as a permanent declared backlog, so this change adds no
> mapping row and does not edit the registry.

## MODIFIED Requirements

### Requirement: Transport and entry point (MSP-R01)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by
> `2026-10-09-feat-mcp-explicit-root` (issue #273) — the entry point resolves an
> explicit containment root.

`[project.scripts]` SHALL declare `sofer-mcp = "sofer.mcp_server:main"`; running
`sofer-mcp` SHALL start an MCP stdio server speaking JSON-RPC 2.0 over
stdin/stdout, supporting `initialize`, `tools/list`, `tools/call`,
`resources/list`+`read`, `prompts/list`+`get`. There SHALL be no
remote/streamable-http transport in v1. The server SHALL never call an LLM; its
only network access SHALL be the HF upload path inside the confirm tool.

`sofer-mcp` SHALL accept an explicit containment root: the `--root PATH` flag and
the `SOFER_MCP_ROOT` environment variable SHALL both set it, with precedence
explicit `--root PATH` > `SOFER_MCP_ROOT` > the resolved process cwd (the
documented default). A blank or whitespace-only `SOFER_MCP_ROOT` SHALL be treated
as unset. When the resolved root does not exist or is not a directory, startup
SHALL be refused with a message on stderr naming the resolved path and a non-zero
exit — the fail-closed signal for a stdio server. Containment semantics SHALL be
unchanged: every path-bearing argument and resource URI outside the resolved root
SHALL still be refused with `PathOutsideRootError`.

#### Scenario: Explicit root with fail-closed startup refusal

- GIVEN the sofer MCP entry point
- WHEN `--root PATH` is passed, `SOFER_MCP_ROOT` is set, or neither is present
- THEN the containment root SHALL be the first present of `--root PATH`, `SOFER_MCP_ROOT`, and the resolved process cwd (the argument wins; a blank env value counts as unset)
- AND paths outside the resolved root SHALL still be refused with `PathOutsideRootError`
- AND a resolved root that is missing or not a directory SHALL refuse startup with a message naming the resolved path and a non-zero exit
