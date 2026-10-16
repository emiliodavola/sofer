# Feature: opencode-timeout — issue #320

- **Issue:** [#320](https://github.com/emiliodavola/sofer/issues/320) — `feat(mcp): opencode receives no timeout key because its schema disagrees with itself across releases`
- **Branch:** `feat/320-opencode-timeout` from `dev@6a7a31e` · **Flow:** ODD only (no `openspec/changes/` folder; the spec of record is amended in place)
- **Spec of record:** `openspec/specs/mcp-registration/spec.md` (MCP-REG-05). This file is the working plan behind it.

## Goal

Four of the five registered agents receive the host deadlines that keep a cold start and a long call from
looking like a broken registration; **opencode receives none**, so an opencode user is exactly where every
user was before #287/#296. The cause is a disagreement inside opencode's own sources about the shape of
`timeout`. This change writes the key in the shape the schema accepts, from the budget that actually bites,
and nails the emitted shape with a test.

## Specs

S1 (issue #320 §Problem, verbatim): "Four of the five agents get theirs; **opencode gets none**, so an opencode user is exactly where every user was before the fix — the entry carries no deadline and the failure mode is a host error indistinguishable from a broken registration."

S2 (issue #320 §Proposed solution 1, verbatim): "**Detect the shape, do not guess it:** read the existing `mcp` block before writing. If the file already declares a `timeout` object for any server, the nested shape is in use; if it declares none, prefer the scalar the pinned zod schema accepts. Emit accordingly, and name the choice on stderr."

S3 (issue #320 §Proposed solution 2, verbatim): "**Pin a version and write that shape**, with a check that names the opencode version it was written for, so an upgrade that changes the schema is visible rather than silent."

S4 (issue #320 §Proposed solution 3, verbatim): "**Add an opencode adapter capability for the *startup* deadline only** (`timeout.startup`), which is the deadline that actually bites there, and leave execution alone."

S5 (issue #320 §Proposed solution, closing, verbatim): "Whichever is chosen, the test that pins it should assert the emitted shape, not just that a key exists."

S6 (issue #320 §Problem, verbatim): "Its **30 s startup** default is, against the measured 16–32 s cold start of `sofer-mcp`."

S7 (maintainer decision, questionnaire, verbatim): "Escalar en ms con el presupuesto de connect".

S8 (MCP-REG-05, the clause this change must keep true, verbatim): "An agent whose entry schema accepts no timeout key SHALL keep an entry without one, and `add` SHALL name that on stderr rather than reporting a clean success — the same informational contract as the OpenCode env-drop warning (MCP-REG-03)."

S9 (maintainer process instruction, verbatim): "quiero que utilices exclusivamente el flujo ODD, no SDD, y crees una rama por issue para versionar ahí el código que crees o modifiques".

## Evidence gathered before the first edit (the "research gate" the ROADMAP marked)

Verified against opencode's own sources, not against the issue's summary:

| Source | `timeout` for a local MCP server |
| --- | --- |
| `packages/opencode/src/config/mcp.ts` (zod `ConfigMCP.Local`) | `z.number().int().positive().optional()` — a **scalar** |
| opencode "MCP servers" docs (stable, `/docs/mcp-servers/`) | `timeout` — "**Number** … Timeout in ms for fetching tools from the MCP server. Defaults to 5000 (5 seconds)" |
| `packages/core/src/config/mcp.ts` (next-major tree) | a `Timeout` class: `{ startup?: PositiveInt, request?: PositiveInt }` |
| opencode "MCP servers" docs (`/v2/docs/mcp-servers/`) | `{ startup, catalog, execution }`, positive integer milliseconds |
| `packages/opencode/src/mcp/index.ts` | `DEFAULT_TIMEOUT = 30_000` |

Two further facts the issue does not state, and both change the answer:

1. The stable docs' default (**5000 ms**) and the code's `DEFAULT_TIMEOUT` (**30 000 ms**) disagree with each other, so the "which default bites" figure is not safely quotable — which *strengthens* S1: any default below the measured cold start is a risk, and writing the key removes the question. #322's machine measured ~1.8 s, but #322 also records that a warm-cache measurement cannot revise the 16–32 s figure, so the deadline to write is the configured one, not a measured one.
2. The next-major tree also moves server names from `mcp.<name>` to **`mcp.servers.<name>`**. So the layout half of the disagreement is a bigger defect than the timeout key: for a v2 user the entry's *position* is wrong regardless of this key.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | **Write the scalar** (`timeout = <connect budget × 1000>`), declared as the adapter's `connect_timeout_key` with unit `milliseconds`. | S7 + the evidence table. The scalar is what the schema that matches the **layout this adapter writes** (`mcp.<name>`, on the stable tree) accepts; the nested shape exists only in the next-major tree, whose layout this adapter does not write at all. Emitting the shape that belongs to the tree whose layout we write is internally consistent; mixing them is not. |
| D2 | **No shape detection** (D1 of S2 is not implemented). | S2's detector fires only for a file that mixes a v1 layout with a v2-shaped `timeout` object — a file valid in neither release — and it is silent in the case that actually bites (a fresh or untouched `opencode.json`, which is the file `mcp add` creates). It would add a document read, a branch and a second emitted shape to serve a case that does not exist, and a wrong shape in this file fails validation of the whole `mcp` block. |
| D3 | **No version pin and no `opencode --version` spawn** (S3 rejected). | The adapter declares `delegates: False` precisely so `sofer mcp add` never needs the binary on PATH; a version probe would reintroduce that dependency for a key whose shape is already decided by the layout. The upgrade risk S3 wants visible is answered instead by the emitted shape being pinned in a test and documented in the spec and both READMEs. |
| D4 | **The scalar carries the CONNECT budget, not the per-request one.** | The stable docs define it as the budget for *fetching tools* — establishing the server and listing its tools, i.e. the cold start S6/S1 are about. opencode's own execution default is 12 h, so the per-request deadline is not what breaks there. Mapping it to `request_seconds` would emit 900 000 for no reason. This is what `connect_timeout_key` already means, so the generic writer emits it with **no new capability**. |
| D5 | The **note's guard** must change with the adapter, or the fix prints the note it just made false. | `dropped_timeout_note` returns early only when `timeout_key is not None`; with `timeout_key: None` + `connect_timeout_key: "timeout"` it would still print "carries no timeout key" next to a written key. The guard becomes "declares neither key", which is what S8 actually says. |
| D6 | The **v2 layout** (`mcp.servers.<name>`) is **out of scope** and reported instead. | It is a different defect, in a different part of the file, on a tree that is not the one this adapter targets; folding it in would change what `mcp add` writes for everyone while #320's own subject is one key. |
| D7 | S8's clause stays in the spec unchanged. | Its force is for *any* host whose schema accepts no key; opencode stops being its example, not its justification. Repealed clauses are how a contract quietly loses scope. |

## Tasks

| ID | Task | Specs | Route | Commit |
| --- | --- | --- | --- | --- |
| T1 | `ADAPTERS["opencode"]` gains the scalar/ms key as its connect key; `dropped_timeout_note`'s guard becomes "declares neither key"; the two docstrings that claim opencode has no key are corrected; tests assert the **emitted shape** (scalar int, connect budget, unit), `--no-timeout`'s pre-change shape, rewrite-on-change, and the note not firing | S1, S5, S6, S7, S8, D1, D4, D5 | inline | `fix(mcp): opencode receives its timeout key in the shape its schema accepts (#320)` |
| T2 | Docs and spec in place: both READMEs (the per-agent table row and the manual-key paragraph, the env capability bullet if it names timeouts), the `mcp add` help text, and MCP-REG-05 | S1, S3, S5, D3, D6, D7 | inline | `docs(mcp): opencode's timeout key, and what it does not fix (#320)` |
| T3 | ODD record: this file's Log, `odd/ROADMAP.md` row, Engram mirror | S9 | inline | `chore(odd): record the #320 delivery` |
| T4 | Gates (`pytest tests/ -q`, `ruff`, `mypy`, `pyright`) and one independent `gentle-ai-verify` round | S5, D1 | inline + verifier | — |

## Log

L1 (maintainer request, verbatim): "comenzá la implementación de #323 y #320, revisá si es correcto lo que proponen antes de implementarlo, quiero que utilices exclusivamente el flujo ODD, no SDD, y crees una rama por issue para versionar ahí el código que crees o modifiques"

L2 (maintainer answer to the review questionnaire, verbatim): "2. #320: ¿qué forma de `timeout` escribe el adaptador de opencode? — Escalar en ms con el presupuesto de connect"

L3 (review finding, recorded before the first edit): the issue's diagnosis is correct and its table matches the sources, but **none of its three proposed solutions is the right one** — S2's detector is useless in the case that bites and guesses in the case that does not exist, S3 needs a binary the adapter deliberately avoids, and S4 needs a sub-key name the two trees disagree on (`request` vs `catalog`/`execution`). The correction none of the three names: the scalar is the *connect/catalog* budget, so it belongs in `connect_timeout_key` and the generic writer emits it with no new capability. Recorded in `odd/ROADMAP.md` when the research gate closed, before this branch existed.

L4 (what the change does NOT fix, recorded so it is not read as fixed): a v2 opencode resolves servers from `mcp.servers.<name>` while this adapter writes `mcp.<name>`. Intentional (D6); it needs its own issue.
