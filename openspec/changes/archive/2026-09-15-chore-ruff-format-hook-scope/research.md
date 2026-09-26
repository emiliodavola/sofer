# Research record: 2026-09-15-chore-ruff-format-hook-scope

schema: gentle-ai.sdd-research/v1
revision: 1
outcome: blocked
selected_class: open-web (web_search, source_check, fetch_content, get_search_content)
documentation_class: not selected

## Questions

| ID | Question | Result |
| --- | --- | --- |
| R1 | Does a config-level `types_or` on a remote-repo pre-commit hook entry REPLACE (not merge with) the upstream manifest's `types_or`? (LOAD-BEARING) | blocked — no web tool callable in the research child; local empirical validation path adopted (see preproposal) |
| R2 | Are `python`, `pyi`, `jupyter`, `markdown` the exact identify type tags pre-commit recognises? | blocked — local validation against the installed `identify` package adopted for the verify phase |
| R3 | When/why did astral-sh/ruff-pre-commit add `markdown` to the `ruff-format` hook's `types_or`? | blocked — remains bracketed by locally cached upstream manifests (absent at 0.15.21, present at 0.16.6) |
| R4 | Re-earn the 11-markdown-file batch arithmetic from live hook output | deferred-local to the verify phase (not a web question) |

## Admission

- Selected open-web class could not run: the child session bound none of the four web tools despite the
  `sdd-research` agent frontmatter declaring them; the injected capability block reported
  `documentation: blocked; tools=[]` and `open-web: blocked; tools=[]`.
- This is a harness defect (declared tools unbound + denial-record write refused), NOT an admission policy
  denial. Diagnostic re-run on 2026-09-15 confirmed the tool surface: `read, grep, find, edit, write,
  mem_search, mem_get_observation, mem_save, subagent_parent_message` only.
- Defect reported (user-consented): Gentleman-Programming/gentle-ai#4633 (created 2026-09-15, created
  identity confirmed via issue list).

## Sources

(none — no web tool was callable in the child; search snippets and prior knowledge were NOT used as evidence)

## Validated claims

(none — zero claims; nothing fabricated)

## Persistence note

The research child's mandated denial-record writes were refused by the transport
(`Research scope refused: Tool arguments outside retained research artifact scope`), so this record was
persisted by the parent orchestrator on the same canonical path, same schema, and same bounds. The Engram
counterpart is topic `sdd/2026-09-15-chore-ruff-format-hook-scope/research`.
