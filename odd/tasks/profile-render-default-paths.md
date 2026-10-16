# Feature: profile-render-default-paths — issue #294

**Branch:** `fix/294-profile-render-default-paths` from `dev@b7dea51`. **Issue:** `emiliodavola/sofer#294`
**Delivery PR:** (pending — user decision) → `dev`. **SDD change:**
`openspec/changes/2026-10-15-fix-profile-render-default-paths/` (archived inside this branch, rule 15).
**Risk:** low — documentation and docstring text plus one derived string; no path, default or contract
changes.

## Goal

The MCP parameter descriptions for the two batch tools state the default output directory as the bare
`profiles` / `renders`. The pipeline actually writes `<dataset>/cache/profiles/` and
`<dataset>/cache/renders/`, because `profile.py` / `render.py` resolve
`write_root = base_dir / config.OUTPUT_DIR` and then append `config.PROFILE_DIR` / `config.RENDER_DIR`.
A reader follows the documented default to a directory that is never written — and `cache/` is the
gitignored artifact cache, so the documented deliverables are also invisible to a reader who looks for
them in the tree.

## Specs

S1 (user, verbatim): "sincronizá `dev`, podá ramas locales y comenzá la implementación de ambos issues"

S2 (issue #294 §Problem, verbatim):

```text
sofer_profile_all: output_dir — "Override directory for batch profiles (default: profiles). Must stay under server root."
sofer_render_all:  output_dir — "Override directory for batch renders (default: renders). Must stay under server root."
```

S3 (issue #294 §Proposed solution item 1, verbatim): "1. Say where it writes: "(default:
`cache/profiles`)" / "(default: `cache/renders`)", or state the write root explicitly in the
side-effect line."

S4 (issue #294 §Why it matters, verbatim): "Beyond the wrong path: `cache/` is the gitignored artifact
cache, so the documented deliverables of these two steps are invisible to the user and excluded by a
default `.gitignore`. An agent that has to read a generated per-file README must first discover the
undocumented location."

S5 (issue #294 §Proposed solution items 2 and 3, verbatim): "2. Decide whether the artifact cache is the
right home for reviewable documentation. If the per-file renders are meant to be read and kept, a
non-gitignored default (e.g. `<dataset>/renders/`) is the better contract. 3. Return the written paths
in the envelope's structured content, so a consumer never has to guess the directory."

S6 (this triage, measured): the README's CLI sections **already** document `cache/profiles/` and
`cache/renders/` (`README.md:255`, `:266`, `:326`, `:327`, `:350`). The stale text is exactly four
places: the two parameter descriptions (`mcp_server.py:1834`, `:1991`), the two MCP-table rows
(`README.md:641`, `:643`) and their Spanish mirrors (`README_ES.md:679`, `:681`).

S7 (AGENTS.md rule 13, verbatim): "`README_ES.md` mirrors the user-facing headings and section order of
`README.md`. Any change to a translated README section MUST update the matching `README_ES.md` section
in the same commit"

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | The description text is **derived** from `sofer_config.OUTPUT_DIR` + the configured sub-directory, never typed as a literal path. | AGENTS.md rule 1 (no hardcoded values) applied to a documentation string: a literal `cache/profiles` in the description is the same drift class that produced this issue. |
| D2 | The description names the resolved default **and** the override semantics: `output_dir` replaces the write root, so files land in `<output_dir>/<subdir>`. | S3's second half; the current text never says what the override is relative to, which is what made the side-effect line ambiguous for an agent. |
| D3 | The tool docstrings' side-effect lines name the write root **without** a literal path ("under the configured `profile_dir` inside the artifact-cache write root"). | A literal path in a docstring is the same drift; the exact resolved default now lives in the derived parameter description. It also keeps the ≤3-sentence tool-description budget (spec clause 10.10). |
| D4 | `cache/` **stays** the default home (issue item 2's decision). | S4 is a real cost, but moving the default is a contract change touching `config.OUTPUT_DIR` semantics, `manifest.py`'s managed-directory list, `clean_cache` and the publish path. The user-facing escape hatch already exists and is documented: `--output DIR` moves the whole write root and leaves `cache/` untouched. |
| D5 | Issue item 3 (return the written paths in the envelope) is **out of scope** for this change. | It changes the tool `output_schema` and is a behaviour addition, not a doc fix — its own change. Consequence: `#294` is only partially delivered, so the closing reference is the maintainer's choice (`Closes` vs `Refs`), recorded at PR time. |
| D6 | The guard compares the description against the **same import-time** `config` constants the description was built from, and documents why. | `Annotated[..., Field(description=...)]` is evaluated when the function is defined, so the shipped text reflects the import-time defaults; a monkeypatched `config` cannot and should not change it. |

## Tasks

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | RED: both batch tools' `output_dir` description names the resolved default (`<output_dir>/profiles`, `cache/renders`) | S2 S3 D1 D2 | inline | pending | — |
| T2 | Derive the descriptions from `config`; fix the two docstring side-effect lines | S3 S4 D1 D2 D3 | inline | pending | — |
| T3 | README + README_ES MCP-table rows in the same commit | S6 S7 | inline | pending | — |
| T4 | `mcp-server` spec delta: parameter descriptions name the resolved default | S3 | inline | pending | — |
| T5 | Gates: focused tests, full suite, ruff/format/mypy/pyright, mapping checker | — | inline | pending | — |
| T6 | Archive the change in the branch and commit | — | inline | pending | — |

## Log

L1 (2026-10-16, user, verbatim): "sincronizá `dev`, podá ramas locales y comenzá la implementación de
ambos issues"

L2 (2026-10-16, this session, read-only triage): the drift is narrower than the issue suggests — the
README's CLI sections already say `cache/profiles/`; only the MCP surface is stale (S6). Item 2 is a
contract decision, item 3 a payload change; both are recorded as decisions rather than silently
dropped.

L3 (2026-10-16, parent decision): D4 keeps `cache/` and documents it faithfully (the roadmap
recommendation, accepted by proceeding); D5 defers item 3 to its own change and flags the issue-closing
consequence.
