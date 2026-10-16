# Proposal — `2026-10-16-feat-agent-metadata-flow`

> **Change** `2026-10-16-feat-agent-metadata-flow` · issue **#288** · branch
> `feat/288-agent-metadata-flow` from `dev@6786ba1` · store **hybrid**.
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

`sofer init` writes a TOML whose `[meta]` block is **all placeholders**, and nothing in the agent-facing
surface said they had to be replaced:

- the canonical chain the server advertises (`instructions`, and each tool's `Requires:` / `Next:`)
  goes *init → scan → validate → prepare → codebook_all → profile_all → render_all → publish* — there
  is **no metadata step**;
- `sofer_validate` accepted them silently (`{"ok":true,"passed":true,"errors":[],"warnings":[]}`);
- `sofer_prepare` then baked them into the artifacts, so the Dataset Card opens with the placeholder
  itself and the LICENSE is built from the placeholder license.

An agent that follows the advertised flow correctly, to the letter, produces a package whose card and
license are placeholders — and the only way to notice is to read the output files. An MCP consumer has
no other source of truth than tool descriptions, `Requires:`/`Next:` hints and envelopes, so the
required step has to be in the surface it reads.

## 2. Scope

- `src/sofer/checks.py`: `meta_placeholder_warnings()`, wired into `DatasetValidator.run_all()`.
- `src/sofer/config.py` + `pyproject.toml`: `meta_placeholder_prefixes`.
- `src/sofer/workflow.py` + `src/sofer/mcp_server.py`: the metadata step in the advertised chain, the
  `Requires:` lines, and the `sofer_init` continuation.
- `README.md` + `README_ES.md`: who fills `[meta]`.
- `openspec/specs/mcp-server/spec.md`: MSP-META-01.

### Out of scope

- **A `sofer_meta_set` / `sofer_meta_check` tool.** The issue offers it as one of several options ("or
  at least `sofer_meta_check`"). A new tool changes the advertised tool inventory, which is its own
  decision with its own schema/parity surface; the warning already puts the step in front of the agent.
  Recorded as a follow-up.
- **Failing the run.** Maintainer decision D3: a `fail` would break every existing config that still
  carries a placeholder.

## 3. Success criteria

- SC-1: the advertised chain names the metadata step before Phase 1.
- SC-2: `sofer_validate` warns per offending `[meta]` field and keeps `passed == True`.
- SC-3: only a *prefix* marks a placeholder, matched case-insensitively.
- SC-4: the prefixes come from `[tool.sofer]`.
- SC-5: the full gate set is green.
