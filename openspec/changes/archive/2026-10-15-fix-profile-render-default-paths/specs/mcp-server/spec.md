# Delta for mcp-server

> **Change** `2026-10-15-fix-profile-render-default-paths` (issue **#294**) · branch
> `fix/294-profile-render-default-paths` from `dev@b7dea51` · store **hybrid**
> (`odd/tasks/profile-render-default-paths.md` + this folder).
>
> **One modification, no new requirement.** MSP-R03's parameter clause gains the requirement that the
> batch `output_dir` descriptions name the resolved default path and the override semantics; one
> scenario pins it.
>
> **Rule-6 resolution.** `mcp-server` is a permanent declared-backlog spec, so the new scenario stays
> unmapped, the registry is not edited, and `scripts/check_test_mapping.py` still exits 0 — it reports
> 128 scenarios for the domain after this change.

## MODIFIED Requirements

### Requirement: Tool roster and schema contract (MSP-R03) — Modified 2026-10-15, fix-profile-render-default-paths

Everything else in the requirement is unchanged. The parameter clause now reads (verbatim, as it reads
in the canonical spec after this change):

Every param SHALL be `Annotated[Field(description)]` non-empty (10.1), and the batch `output_dir`
descriptions SHALL name the resolved default path — the artifact-cache write root
(`config.OUTPUT_DIR`) joined with the configured sub-directory (`config.PROFILE_DIR` for
`sofer_profile_all`, `config.RENDER_DIR` for `sofer_render_all`) — and SHALL state that an override
replaces that write root, so the artifacts land in `<output_dir>/<sub-directory>`.  The bare directory
name SHALL NOT be presented as the whole default.

One scenario is added (verbatim):

#### Scenario: batch output_dir descriptions name the resolved default

- GIVEN `tools/list` for `sofer_profile_all` and `sofer_render_all`
- WHEN the `output_dir` descriptions are inspected
- THEN each SHALL name `<output_dir>/<sub-directory>` and the resolved default composed from the
  configured cache root and the configured sub-directory
- AND neither SHALL present the bare `profiles` / `renders` as the whole default
