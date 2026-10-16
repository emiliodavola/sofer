# Proposal — `2026-10-16-feat-card-section-keys`

> **Change** `2026-10-16-feat-card-section-keys` · issue **#291** · branch
> `feat/291-card-section-keys` from `dev@6786ba1` · store **hybrid**.
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

`build_dataset_card()` hardcoded five sections to a sentinel. There was no TOML key and no tool
argument that could fill them, so a config with every ROTW field filled still produced a card reading
`[More Information Needed]` / `[Not specified]` — and an MCP consumer was told `ok: true` on every call
with no way to satisfy them. The only escape was to stop generating the card and lose the per-column
schema tables that make it valuable.

## 2. Scope

- `src/sofer/model.py`: five new `[meta]` fields and their `from_toml` reads.
- `src/sofer/repo_compliance.py`: the seven sentinel sites use them, plus one `_MORE_INFO` constant.
- `openspec/specs/repo-compliance/spec.md`: §2.1.1's TOML block and §2.1.2's resolution rules.

Not in scope: the README enumerates only three `[meta]` keys, so the full key list stays in the spec
and rule 13 is not triggered.

## 3. Approach — the maintainer's decision D1

The issue offered three options (omit the section; add the keys; compose from what exists). **D1 chose
"add the keys"**, and this change delivers it with the issue's own option 3 for `repository`:

- five free-text keys fill the four narrative sections and the contact line;
- `- **Repository:**` falls back to `source`, which is already the best available value;
- `### Curation Rationale` keeps its existing `study_design` path — a file whose content the caller
  resolves — which is the issue's "promoted from the documented-but-obscure path".

That combination fixes a fully-filled config **without** the spec delta that option 1 (omit the section)
would have required at §2.1.2 and in the *Minimal config* scenario.

## 4. Success criteria

- SC-1: a config with every ROTW field set emits no sentinel anywhere.
- SC-2: an unset or whitespace-only value keeps the placeholder, so nothing changes for existing configs.
- SC-3: `repository` falls back to `source` and a declared value wins over it.
- SC-4: all five keys round-trip from a TOML.
- SC-5: the full gate set is green.
