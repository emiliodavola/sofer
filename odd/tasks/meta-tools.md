# Feature: meta-tools — issue #323

- **Issue:** [#323](https://github.com/emiliodavola/sofer/issues/323) — `feat(mcp): the metadata step has no tool surface (sofer_meta_set / sofer_meta_check)`
- **Branch:** `feat/323-meta-tools` from `dev@6a7a31e` · **Flow:** ODD only (no `openspec/changes/` folder; the specs of record are edited in place)
- **Specs of record:** `openspec/specs/mcp-server/spec.md` (MSP-R03 roster, MSP-META-01) and `openspec/specs/cli/spec.md` (new CLI-R16). This file is the working plan behind them.

## Goal

`sofer_validate` warns while `[meta]` still carries the `sofer init` placeholders, and
`_PHASED_INSTRUCTIONS` tells the agent to fill them — but there is no tool that can write them
(`mcp_server.py:188-197`). Over MCP the agent can read the warning and cannot act on it, so the
advertised step is a dead end and the only path is a human with an editor. This change closes both
halves: a read-only `sofer_meta_check` that reports the state on demand, and a `sofer_meta_set` that
writes the `[meta]` keys it is given into the dataset TOML, plus the CLI counterparts so the two
surfaces stay in step.

## Specs

S1 (issue #323 §Problem, verbatim): "Over MCP there is no tool for writing a file, so the agent must either ask the human for every value or abandon the phased flow. The warning is actionable for a human with an editor and much less so for the agent the issue is written about."

S2 (issue #323 §Proposed solution 1, verbatim): "**`sofer_meta_check` first** — read-only, reuses `meta_placeholder_warnings()` verbatim, no writes, `readOnlyHint: True`. It makes the warning queryable instead of only push-based, and it is the cheapest step that closes the \"agent cannot see the state\" half. It does not yet close the write half."

S3 (issue #323 §Proposed solution 2, verbatim): "**`sofer_meta_set` second** — writes only the `[meta]` keys it is given, into the dataset TOML under the server root, preserving every other key and the file's formatting where the format allows. This needs a containment check (`_contained_path`), an atomic write, and a decision on whether it may be called while a build exists."

S4 (issue #323 §Proposed solution 3, verbatim): "**The CLI counterpart** (`sofer meta set`) if the tool lands, so the two surfaces stay in step."

S5 (issue #323 §Proposed solution, closing paragraph, verbatim): "Whichever lands, the parity tests that pin the tool inventory and the per-area surface contract must be updated in the same change, and the metadata step in `_PHASED_INSTRUCTIONS` should name the tool rather than \"fill `[meta]`\"."

S6 (issue #323 §Problem, last paragraph, verbatim): "a new tool changes the advertised tool inventory (`Register the 15 tool callables`), with its own schema, annotations, output schema and parity surface. That is a decision worth taking deliberately, not as a side effect of a warning."

S7 (maintainer decision, questionnaire, verbatim): "Completo: check + set + CLI".

S8 (maintainer decision, questionnaire, verbatim): "Todas las de [meta] que lee el card".

S9 (maintainer process instruction, verbatim): "quiero que utilices exclusivamente el flujo ODD, no SDD, y crees una rama por issue para versionar ahí el código que crees o modifiques".

S10 (issue #323 §Proposed solution 2, second requirement, verbatim): "This needs a containment check (`_contained_path`), an atomic write, and a decision on whether it may be called while a build exists."

S11 (issue #323 §Related, verbatim): "**#314** — added five more fillable card-section keys, which a `sofer_meta_set` would also need to cover."

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | ODD only: `odd/tasks/` + `odd/ROADMAP.md` + one branch and one commit per work unit. No `openspec/changes/` folder. The specs of record are edited **in place** (MSP-R03, MSP-META-01, CLI-R16) because leaving them saying "15 callables" would make the durable record false. | S9. Same shape as #324/#322 minus the change folder. |
| D2 | The settable key set is **every `[meta]` key `DatasetConfig.from_toml` reads** — the 40 `meta.get(...)` calls at `model.py:564-604` — not just the four the placeholder warning names. | S8, S11. One registry, derived from the read list, with a behavioural drift guard (S8's "lee el card" is exactly that read list). |
| D3 | A **new surgical writer** (`src/sofer/meta_edit.py`): a line-based editor limited to the `[meta]` table, with `tomllib` as the authority for three questions — which line is the real `[meta]` header, which line is a real top-level assignment, and where the value ends. Rejected: a `tomli-w` whole-document rewrite (destroys the ~60 comment lines of the `sofer init` template, `cli.py:1049-1108`), and a `tomlkit` dependency (AGENTS.md rule 9; the format-native reader already in use is `tomllib`). | S3's "preserving every other key and the file's formatting where the format allows". The three questions are the ones a naive regex gets wrong (a `[meta]`-looking line inside a multi-line string, or a `description = ` line inside a multi-line value). |
| D4 | `apply_meta_edit` **never returns text it has not parsed**: the edited document is re-parsed with `tomllib` and every requested key is read back before the atomic replace. A failure is a refusal (`MetaEditError`), never a partial file. | The strongest available guarantee that a TOML edit cannot corrupt the file, and it is what makes the line scanner safe to use. |
| D5 | Values are always written **single-line** (basic strings with `\n` escapes, inline arrays, `true`/`false`), so the file stays line-addressable and the diff stays reviewable. A pre-existing *multi-line* value is replaced over its whole range, located by the same prefix-parse — never by a first-line replacement. | D4's guarantee holds either way; this keeps the small diff the issue asks for ("preserving ... formatting"). |
| D6 | `sofer_meta_check` and `sofer meta check` are **informational**: exit code 0 and `ok: true` with the warnings listed, never a failure. | The pre-existing decision this change builds on: `checks.py:53-56` (D3 of #288) — "a failure would break every existing config that still carries a placeholder". A query command must not be stricter than the validator it queries. |
| D7 | `sofer_meta_set` **may** run while a build exists, and names it: `build_stale: true` plus an informational line, never a refusal. | S10's open question. The same contract as MCP-REG-03/05's informational notes: the human is told, the exit code is not changed. A refusal would block the legitimate re-write-after-tweak flow. |
| D8 | The registry carries the chain: `sofer_scan_apply`.next → `sofer_meta_set`, `sofer_meta_set`.next → `sofer_validate`, `sofer_meta_check`.next → `sofer_meta_set`. | S5's "the metadata step ... should name the tool". A continuation is executable state, not prose, and `workflow.WORKFLOW_METADATA` is the single source that `tools/list`, the doctor-style envelopes and `tests/test_workflow.py` all read. |
| D9 | The CLI surface is one uniform flag — `--set KEY=VALUE` (repeatable) — plus `--dry-run` and `--json`. No per-key flags. | S7 wants all 40 keys on the CLI; 40 flags is 40 help lines and 40 parity rows. `--set KEY=VALUE` with a kind-aware parse (`text` → verbatim, `list` → comma-separated, `flag` → `true`/`false`) is one rule to document and to test. |
| D10 | `meta_edit.py` is a new module and the placeholder check is **reused**, not re-written: `checks.meta_placeholder_warnings` stays the single implementation, so the tool and the validator cannot disagree. | AGENTS.md rules 4 and 10; S2's "reuses `meta_placeholder_warnings()` verbatim". |
| D11 | The tool roster goes 15 → 17 and the parity declarations grow two areas (`meta check`, `meta set`). | S5's named cost, and `openspec/specs/mcp-server/spec.md:97` pins the count. |

## Tasks

| ID | Task | Specs | Route | Commit |
| --- | --- | --- | --- | --- |
| T1 | `src/sofer/meta_edit.py`: key registry (40 keys, kinds), `apply_meta_edit` (surgical, parse-verified), `set_meta` (atomic write), `build_predates_write`; unit tests in `tests/test_meta_edit.py` including the RED-first corruption refusals | S3, S8, S10, D3, D4, D5, D7 | inline | `ac4ca04 feat(meta): write [meta] keys without rewriting the dataset TOML (#323)` |
| T1b | Byte-preservation fix: the two defects the independent verifier falsified (line endings normalized document-wide, trailing blank lines collapsed) plus the quoted-key/header spelling it probed; 8 regression tests asserting `read_bytes` | S3, D4, D5 | inline | `a95ae6e fix(meta): keep the document's bytes when writing [meta] (#323)` |
| T1c | Second-round residuals: compare the parsed value instead of the line's bytes (the idempotency sentence the change ships was false), keep a missing EOF terminator, accept the quoted/whitespace header forms and name the inline/dotted refusal; 6 regression tests | S3, D4, D5 | inline | `c9760a9 fix(meta): compare the value, not the line, and stop refusing valid documents (#323)` |
| T2 | CLI `sofer meta check` / `sofer meta set` (`--set`, `--dry-run`, `--json`), help text, exit codes; tests in `tests/test_cli.py` under the rule-14 100.00% gate | S4, S7, D6, D9 | inline | `feat(cli): add sofer meta check and sofer meta set (#323)` |
| T3 | MCP `sofer_meta_check` / `sofer_meta_set`: tools, annotations, output schemas, registry entries + chain, `_PHASED_INSTRUCTIONS`, docstrings; parity/roster/workflow tests | S2, S5, S11, D6, D8, D11 | inline | `feat(mcp): expose sofer_meta_check and sofer_meta_set (#323)` |
| T4 | Docs and specs in place: both READMEs (tool table, command table, `[meta]` guidance), MSP-R03 17 callables, MSP-META-01 names the tool, new CLI-R16 | S5, D1, D11 | inline | `docs(meta): document the metadata tools and amend MSP-R03 / MSP-META-01 / CLI-R16 (#323)` |
| T5 | Gates: `uv run pytest tests/ -q`, `ruff check`, `mypy`, `pyright`, `scripts/check_core_coverage.sh`, test-mapping checker | S3, D4 | inline + `verify-meta-tools` independent verifier | — |

## Log

L1 (maintainer request, verbatim): "comenzá la implementación de #323 y #320, revisá si es correcto lo que proponen antes de implementarlo, quiero que utilices exclusivamente el flujo ODD, no SDD, y crees una rama por issue para versionar ahí el código que crees o modifiques"

L2 (maintainer answers to the review questionnaire, verbatim): "1. #323: ¿qué superficie implemento del issue (check read-only / set que escribe el TOML / CLI)? — Completo: check + set + CLI  2. #320: ¿qué forma de `timeout` escribe el adaptador de opencode? — Escalar en ms con el presupuesto de connect  3. #323: ¿qué claves debe aceptar la escritura de `[meta]`? — Todas las de [meta] que lee el card"

L3 (review finding on #323, recorded before the first edit): the issue's diagnosis verifies against the code — `checks.meta_placeholder_warnings` exists (`checks.py:42`) and `sofer_validate` calls it (`checks.py:266`); the instructions call the step manual (`mcp_server.py:188-197`); the registry requires `[meta] placeholders replaced` (`workflow.py:322-328`); no tool writes `[meta]`. What the issue does not name is the integration cost of a 16th/17th tool: one `WORKFLOW_METADATA` entry each (`workflow.py:300`, spec MSP-R13), the `SHALL expose 15 callables` pin and `tests/test_mcp_schema.py::TestToolCount::test_fifteen_tools`, `tests/test_parity.py::AREAS` coverage, `tests/test_workflow.py::CANONICAL_TOOLS`, both README tool tables, and `cli.py`'s 100.00% coverage mandate. Its proposed *order* (check first) is defensible but not the value order: the read half already arrives push-based in `sofer_validate`'s envelope; the write half is the dead end. Both land (S7).

L4 (review finding, TOML writer, recorded before the first edit): there is no format-preserving TOML writer in this repository — `_toml.py` only reads, `scanner.write_toml` (`scanner.py:505`) reserializes the whole document with `tomli_w` and would strip the `sofer init` template's comments (`cli.py:1049-1108`), and the surgical splice exists only for YAML (`_yaml.py`). Resolved as D3/D4 instead of adding `tomlkit`: the new editor addresses only the `[meta]` table and refuses anything it cannot parse back.

L5 (independent verification, first round): `gentle-ai-verify` returned **covered** for S1, S2, S4, S5, S6, S7, S8, S9, S10, S11 and **covered with two counterexamples** for S3. It confirmed by execution: the 17-tool roster and the `readOnlyHint` partition, `sofer_meta_check`'s warnings identical to `sofer_validate`'s, the chain `sofer_scan_apply -> sofer_meta_set -> sofer_validate` with the bootstrap continuation executable and `input_required: ["values"]`, every refusal path writing nothing (byte-identical file), `--json` as a single parseable stdout line, idempotency, dry-run, and `openspec/changes/` free of this change. It also recorded that the branch advanced mid-verification (`d1dc180`, `odd/ROADMAP.md` only) and that the code under test was unaffected.

The two counterexamples, both reproduced through the CLI on this host:

1. A real write rewrote **every line's bytes**: an LF document came back all-CRLF (and on POSIX a CRLF document would come back all-LF), because `_read_text`/`_atomic_replace` used the universal-newline default. The repo's own tests missed it because they compared bytes only on the no-op and `--dry-run` paths.
2. Trailing blank lines collapsed (`_join` did `rstrip("\n") + "\n"`).

Plus a **non-finding it correctly classified as safe**: a quoted key (`"description" = "old"`, valid TOML) was not matched by the locator, so the insert path duplicated it and the parse gate refused — nothing written, but with "Cannot overwrite a value" as the message for a document that parses fine.

L6 (fix, D4/D5 held): lines are now kept with their terminators and rebuilt with `"".join`, I/O opens with `newline=""` (via `open`, not `Path.read_text`/`write_text`, whose `newline` argument only exists from Python 3.13 while this package supports 3.10), a replacement carries the terminator the assignment already had, and an insertion uses the document's own first terminator after terminating an unterminated last line. The quoted spellings are now recognized for both the key and the table header, and a recognized quoted key is rewritten unquoted. The two findings are the reason the "byte for byte" clause is now tested with `read_bytes` on a real write — the gap was in the tests as much as in the code.

L7 (fix evidence): the verifier's own CLI reproductions replayed byte-for-byte on this host — LF, CRLF, trailing blanks, unterminated last line, quoted key, quoted header: six of six `bytes_match_expected=True`. 8 new regression tests; full suite 2370 passed / 9 skipped (+8 over the 2362 before the fix). Re-verification of the corrected revision was launched next, scoped to the writer's byte preservation.

L8 (independent verification, second round): **both findings CLOSED.** The verifier re-ran its own reproductions through the real subprocess entry point and extended the matrix it had not used: LF, CRLF, mixed endings in one file, no `[meta]` at all, an unterminated last line, trailing blank lines, trailing whitespace-only lines, non-ASCII, `["meta"]`, empty/comment-only blocks, multi-line `"""` and array replacements, and every refusal path — all exact, with `read_bytes` assertions. Remaining suite at that revision: 570 passed / 4 skipped on its selection. It returned three **residuals** and classified them non-blocking:

- (a) an equal value in another spelling (`description = """New"""`, `"description" = "New"`, `description="New"`) triggered a normalizing write: `changed: true` with `written: []`, message `"wrote: "`, and a first run that rewrote the author's line. This **contradicted a sentence this change ships** in the CLI help, CLI-R16 and MSP-META-01 — "re-running with the values the file already holds writes nothing" — so it was a contract defect, not a formatting preference.
- (b) a multi-line value that ended the file without a newline gained one.
- (c) `[ meta ]`, `[ \"meta\" ]`, `[\tmeta\t]` and a top-level `meta = { ... }` / `meta.description = ...` were refused as duplicates on documents that are themselves valid.

L9 (residual fix, `c9760a9`): the decision now compares the **parsed value**, not the line's bytes — the editor writes a value and is not a formatter, so a key already holding the requested value is untouched and `changed` implies a non-empty `written` again. A replacement keeps the missing terminator when the replaced range's last line had none. The header pattern accepts the quoted and whitespace forms; a top-level inline/dotted `meta` now refuses with a named reason instead of `tomllib`'s "cannot declare twice", with the same total guarantee. One test of mine was wrong before the code was: **after `[dataset]`, `meta = { ... }` is a key OF `[dataset]`**, so appending a `[meta]` table there is correct and no refusal applies — now pinned by its own test, because the distinction is exactly what a reader would get wrong.

**Evidence**: the verifier's residual reproductions replayed through the real CLI at byte level — four groups, all exact (`FAILURES: 0`), including `bytes_identical=True` for every refusal. 6 new tests (53 in `tests/test_meta_edit.py`); full suite 2376 passed / 9 skipped. One narrow third round was launched to re-verify the residual fix, because this is the high-risk component and round 2 showed its test gap was systematic rather than incidental.

L10 (independent verification, third round — final): **all three residuals CLOSED, no counterexample, no regression in what round 2 confirmed.** The verifier attacked each claim through the real subprocess and the MCP surface with `read_bytes` assertions, and added a 2250-call invariant fuzz that found **0 violations** of four contract invariants: `changed` equals "the bytes on disk changed", `changed` equals "`written` is non-empty", `written ∩ unchanged = ∅` with their union covering the requested keys, idempotency, and "a refusal never wrote". Claim (a) held for six spellings including exotically-spelled equal lists; (b) held for `"""`, `'''` and array forms at EOF; (c) held for five header spellings and for all three top-level inline/dotted refusals, with `bytes_identical=True`. Envelope consistency (`changed`/`written`/`unchanged`/`message`/`--json` single line) held on both surfaces. Boundary notes it recorded as non-counterexamples: a multi-line value at EOF **plus** a second key inserted in the same call gains a trailing newline because the inserted line needs one to be legal — the value-replacement claim as written still holds; `meta = 5` is refused earlier by the config loader; and MCP refusal envelopes omit `changed`/`written`/`unchanged`, which is pre-existing and not a contradiction between success envelopes. Selection it ran: 576 passed / 4 skipped.

L11 (state at close): branch `feat/323-meta-tools` from `dev@6a7a31e`, head `073275a` before this record, nine commits — seven work units (`ac4ca04`, `a0c0bdd`, `3adf2a9`, `44d77c7`, `a95ae6e`, `c9760a9`, plus T4's docs) and the ODD records. `uv run pytest tests/ -q` 2376 passed / 9 skipped; rule-14 per-file gates 100.00% (`cli.py` 742 stmts / 224 branch / 0 missed) with TOTAL 94% against the config-owned 90 floor; ruff, ruff format, mypy (40 files), pyright (0 errors) and `scripts/check_test_mapping.py` clean. Not pushed and no PR opened: delivery beyond the branch is the maintainer's decision (S9 asked for a branch per issue, not for a PR). Known limitation kept honest: the writer addresses the `[meta]` **table** form; an inline-table or dotted-keys `meta` is refused with a named reason and nothing written.
