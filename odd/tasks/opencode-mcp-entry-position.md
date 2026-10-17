# Feature: opencode-mcp-entry-position — issue #334

- **Issue:** [#334](https://github.com/emiliodavola/sofer/issues/334) — `fix(mcp): sofer mcp add writes the opencode entry in the position v2 no longer reads`
- **Branch:** `fix/334-opencode-mcp-entry-position` from `dev@1559604` · **Flow:** ODD only (no `openspec/changes/` folder; the spec of record is amended in place)
- **Spec of record:** `openspec/specs/mcp-registration/spec.md` (MCP-REG-03). This file is the working plan behind it.

## Goal

Issue #334 reports that `sofer mcp add --agent opencode` writes `mcp.sofer` while a v2 opencode reads
`mcp.servers.sofer`, and it is explicit that this is **a finding, not a verified defect**: its own first
task is to decide the severity ("**This is a finding, not a verified defect, and the first task is to
verify it, not to fix it**"), and its two outcomes need different fixes. This document records that
verification and the delivery the answer requires.

## Specs

S1 (issue §Problem, verbatim): "`sofer mcp add` writes the opencode entry into the `mcp` table under the server name" — `"mcp": { "sofer": { "type": "local", "command": ["sofer-mcp"], "cwd": "..." } }`.

S2 (issue §Problem, verbatim): "opencode's next-major tree and its v2 docs place server names under a `servers` sub-object instead" — `"mcp": { "servers": { "sofer": { "type": "local", "command": ["sofer-mcp"] } } }`.

S3 (issue §Problem, verbatim): "**This is a finding, not a verified defect, and the first task is to verify it, not to fix it.** The severity depends on one thing I could not check from this repository: whether opencode's V1→V2 config migration moves an existing `mcp.<name>` entry to `mcp.servers.<name>` on read. If it does, the current output keeps working and this issue becomes a documentation problem; if it does not, every opencode user on v2 has an entry their host never reads".

S4 (issue §Proposed solution 3, verbatim): "**If it is migrated:** no code change; amend `mcp-registration` and both READMEs to state that the entry is written in the v1 position and that opencode migrates it, so a reader is not left wondering — and so the next person does not \"fix\" the position into a shape a stable opencode rejects."

S5 (issue §Proposed solution 1, verbatim): "Run `opencode` v2 against a sofer-written file, **or** read the migration source in `packages/core`. Record the answer here before proposing a change, because the two outcomes need different fixes."

S6 (issue §Proposed solution 2, the option this verdict rejects, verbatim): "**If it is ignored:** teach the opencode adapter the position (a per-adapter key path rather than a single `key`), keep writing the v1 position for a v1 file, and make the choice visible on stderr the way every other registration decision in this module is."

S7 (issue §Related, verbatim): "- #287 — the cold start whose failure mode a mis-positioned entry would reproduce".

S8 (maintainer request, verbatim): "utilizando ODD, revisá el issue pendiente, chequeá que sea así e implementalo para solucionarlo".

S9 (maintainer instruction, verbatim): "creá una rama aparte para versionarlo".

S10 (issue §Related, verbatim): "`openspec/specs/mcp-registration/spec.md` — MCP-REG-03, whose \"the generated opencode entry MUST remain `{type, command, cwd}` …\" clause is the text that would change with option 2 or 3".

## Verification — the answer to S3/S5, before any edit

**Verdict: the migration happens. A v2 opencode reads the flat V1 position. This is option 3 (S4): no
code change; the durable text in the spec and both READMEs is what is wrong.**

Two independent sources, both read on 2026-10-17, and the first is the executed code path rather than a
description of it.

1. **The normalization source — the code that runs when a config file is loaded.**
   `packages/core/src/config/normalize.ts` (repo `anomalyco/opencode`, branch `dev`, the v2 tree),
   `normalizeMcp(input, encoded, diagnostics)`, called from the top-level `normalize()` at
   `normalize.ts:193`; the file is imported by `packages/core/src/config.ts:17`
   (`import { ConfigNormalize } from "./config/normalize.js"`). Its loop over `input.mcp`:

   ```ts
   Object.entries(input.mcp).forEach(([name, value]) => {
     const path = ["mcp", name]
     if (isEnabledOnlyMcp(value)) { /* omitted, diagnostic */ return }
     if (name === "servers" && !isDirectLegacyMcp(value)) { /* native mcp.servers */ return }
     if (name === "timeout" && !isDirectLegacyMcp(value)) { /* native mcp.timeout */ return }
     const server = decodeValue(ConfigMCPV1.Info, value, path, diagnostics)
     if (server !== undefined)
       setOwn(legacyServers, name, canonical(ConfigMCP.Server, ConfigMigrateV1.migrateMcp(server)))
   })
   ...
   const servers = mergeMaps(legacyServers, nativeServers, ["mcp", "servers"], diagnostics)
   encoded.mcp = { ...(timeout), ...(servers) }
   ```

   Every `mcp.<name>` that is not the `servers` / `timeout` container is decoded **as the V1 server
   schema** and put in `legacyServers`; `mergeMaps` folds `legacyServers` into the one `servers` mapping
   that is emitted. `migrateMcp` also carries the scalar `timeout` across
   (`migrateMcpTimeout(timeout) → {startup, catalog, execution}`), which keeps #320's connect meaning of
   that scalar. sofer's entry is exactly `{type:"local", command:["sofer-mcp"], cwd, timeout}` — a shape
   `ConfigMCPV1.Info` decodes, with a server name (`sofer`) that collides with neither reserved container
   name. It therefore lands under `mcp.servers.sofer` **in the in-memory config**, and the source file is
   not rewritten, so the entry stays valid for v1 on the same machine.
2. **The vendor's own migration page.** `https://opencode.ai/v2/docs/migrate-v1/`: "Existing supported
   server config fields … should continue to work without changes", "V2 reads these same locations. It
   normalizes supported V1 and native V2 fields **in memory without rewriting the source file**.
   Existing supported V1 configuration is intended to keep working, so you do not need to convert it to
   try or adopt V2", and "OpenCode recognizes mixed V1 and V2 members within `mcp`, `compaction`, and
   `experimental`".
3. **Corroborating:** opencode's own tracker carries
   [an issue about this migration](https://github.com/anomalyco/opencode/issues/54184) ("V1 to V2 MCP
   migration drops `timeout.startup`"), i.e. the migration is a live, maintained code path applied to
   entries in exactly sofer's V1 shape — the situation S3 could not rule out, confirmed from the other
   side.

S5 offers running a v2 binary as an alternative to reading the source; the source read was taken, and it
is the stronger one for this question: it is the exact predicate that decides whether the entry is read,
at the revision the v2 docs describe, and it is re-readable by anyone with one `curl`. Downloaded
evidence kept under `tmp/` (untracked) for this session: `tmp/oc-normalize.ts`, `tmp/oc-migrate.ts`,
`tmp/oc-core-config.ts`.

**What follows from the verdict.** The position stays as it is (S4, and the S6 option is refused, not
deferred): writing `mcp.servers.sofer` instead would put the entry where the **stable** opencode's schema
(`ConfigMCP.Local`, server name directly under `mcp`) does not look, and the stable release is what
`opencode-ai@latest` (1.19.3 at the time of writing) installs. The `delegates: False` adapter cannot
choose per version, so the only position correct for both is the V1 one. The durable text asserting
otherwise — README.md, README_ES.md, and the spec's silence on the position — is the defect.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | **The position is a contract, and it is pinned by a test, not only by prose.** | S4 asks for documentation, but the *reason* it asks (S4: "so the next person does not \"fix\" the position") is a behavior claim: the entry must stay at `mcp.<name>`. One test asserting `mcp.sofer` exists and **no `mcp.servers` is created** is what makes that claim fail loudly; prose alone is what failed the first time (README already mentioned the v2 layout and still read as a live defect). |
| D2 | **No behavior change anywhere in `src/`.** | The verdict is S4's second branch. Nothing in the write path, the adapter registry, or the CLI changes; the only `src/` edit is one sentence of the `ADAPTERS["opencode"]` comment, which is the text a future contributor reads before "fixing" this. |
| D3 | **The spec clause lands in MCP-REG-03**, which is already the requirement that owns the opencode entry shape (S10), rather than a new requirement. | The entry shape and the warning live in one clause today; splitting the position out would make two clauses disagreeable about one entry. |
| D4 | **`odd/ROADMAP.md` and `odd/tasks/opencode-timeout.md` are not rewritten.** | D6/L4 there recorded the layout as out of scope for #320, which is still true of #320's change; this file is where the follow-up's verdict lives, and the ROADMAP gets a new row, not an edit of the old one. Logs are appended, never corrected in place. |

## Tasks

| ID | Task | Specs | Route | Commit |
| --- | --- | --- | --- | --- |
| T1 | Verdict recorded in this document, with both sources and the exact code path; the issue's S3 question answered as *migrated* | S3, S5, D2 | inline | `26830b5` |
| T2 | The position pinned by a test (`TestMerge`: `mcp.sofer` present, no `mcp.servers` created) and the adapter comment corrected | S1, S2, S4, D1, D2 | inline | `00b9fd9` |
| T3 | MCP-REG-03 carries the position contract and its scenario; both READMEs lose the "larger defect in the layout, tracked separately" paragraph and state what v2 actually does | S4, S10, D3 | inline | `e51bdae` |
| T4 | `odd/ROADMAP.md` row; Engram mirror | S8 | inline | `chore(odd): record the #334 delivery` |
| T5 | Gates: `uv run pytest tests/ -q`, `ruff check`/`format`, `uv run --python 3.13 mypy src/ scripts/`, `uv run pyright`, `scripts/check_test_mapping.py` | S8 | inline | — |

## Log

L1 (maintainer request, verbatim): "utilizando ODD, revisá el issue pendiente, chequeá que sea así e implementalo para solucionarlo"

L2 (maintainer instruction, verbatim): "creá una rama aparte para versionarlo"

L3 (repo state at start): `dev@1559604`, clean tree; `gh issue list --state open` returned exactly one
issue, #334, labelled `type:bug` and assigned to the maintainer. Branch
`fix/334-opencode-mcp-entry-position` created from `dev` before the first write (S9).

L4 (the research gate, closed before the first edit): verdict **migrated** — see §Verification. The
decisive artifact is `packages/core/src/config/normalize.ts::normalizeMcp` on `anomalyco/opencode@dev`,
which folds every non-container `mcp.<name>` decoded as the V1 schema into the emitted `mcp.servers`.
The issue's own S3 alternative (`or read the migration source in packages/core`) was the route taken;
its binary route was not, and the record states why. Consequence: S6's "teach the adapter the position"
is refused, because it would break `opencode-ai@latest` (1.19.3), whose schema reads `mcp.<name>`.

L5 (what the previous delivery had recorded, now corrected): `odd/tasks/opencode-timeout.md` L4 and both
READMEs said the v2 layout was "a larger defect in the layout, tracked separately". The layout part is
true (`mcp.servers` is where v2 puts servers natively) and the *defect* part is not: nothing is
mis-registered, because v2 migrates the flat form it finds. A reader of that sentence would go "fix" a
working position — exactly the outcome S4 names.

L6 (T1, `26830b5`): the verdict and the plan, committed before the first edit to anything else. The
research is the whole cost of this delivery (D-cost, ROADMAP): three files from `anomalyco/opencode@dev`
and one vendor doc page, from which one function decided the answer.

L7 (T2, `00b9fd9`): the pin. **No behaviour changed, so a RED in the TDD sense does not exist here** —
and that is recorded rather than glossed: the change is documentation, and the only executable content is
the pin itself. What was checked instead is the thing a pin can be wrong about, its discriminating power:
written first with the inverted expectation (`assert "servers" in data["mcp"]`, i.e. the shape the refused
option would produce) it **failed on a real write** —
`AssertionError: assert 'servers' in {'sofer': {'type': 'local', 'command': ['sofer-mcp'], 'cwd': …, 'timeout': 120000}}`
— and passes with the contract as written. A test that could not tell the two positions apart would have
been worth nothing.

L8 (T3, `e51bdae`): the spec clause, its scenario, its `**Evidence:**` row naming the test from L7, and
the README pair (rule 13). MCP-REG-03 keeps its title — other documents reference it by number and name
— with the modification marker and note added, following MCP-REG-05's convention.

L9 (T4/T5, state at close): gates on the branch — `uv run pytest tests/ -q` **2380 passed, 9 skipped**;
`ruff check .` clean; `ruff format --check src/ tests/` **79 files already formatted**; `uv run --python 3.13
mypy src/ scripts/` **Success: no issues found in 40 source files**; `uv run pyright` **0 errors, 1 warning**,
and that warning (`src/sofer/_toml.py:27` could not resolve `tomli` from source) was reproduced on the
stashed `dev` state, so it predates this branch; `scripts/check_test_mapping.py` **OK**. One reported,
unfixed, out-of-scope item: `ruff format --check .` flags `README.md` and `README_ES.md` for the fenced
Python in their walkthrough block — pre-existing on `dev` (verified by running the same check on both
files as `dev` has them), in lines this change does not touch, and outside every gate by declaration:
`.pre-commit-config.yaml` restricts `ruff-format` to `types_or: [python, pyi, jupyter]` (issue #216) and
CI runs it on `src/ tests/` only.

L10 (open, not a task): the verdict is **not** on the issue. #334's first task says "Record the answer
here before proposing a change", and "here" is the issue thread; posting it is a publish action and needs
the maintainer's word, so the durable answer lives in this file and MCP-REG-03 until then.
