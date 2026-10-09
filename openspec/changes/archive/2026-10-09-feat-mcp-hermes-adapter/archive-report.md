# Archive Report: `hermes` adapter for `sofer mcp add`

**Change**: `2026-10-09-feat-mcp-hermes-adapter`
**Archived to**: `openspec/changes/archive/2026-10-09-feat-mcp-hermes-adapter/`
**Branch**: `feat/272-mcp-hermes-adapter` (base `origin/dev` @ `90ee69f`)

> Archived **inside the pull request that delivers it**, per AGENTS.md rule 15. The report therefore
> cites the branch and the base, not a merge commit — the merge does not exist yet, which is the
> consequence of archiving in the same PR rather than in a follow-up.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-registration` | Updated | Purpose line gains `hermes` and the YAML-vs-JSON/TOML write distinction. MCP-REG-01 amended: the `add` flag enumeration, the env-enforcement sentence (Hermes `${KEY}`), the agent table (one `hermes` row), the env-policy paragraph, two appended paragraphs (the YAML write contract with line endings, and the single-scope resolution), one amendment blockquote, `Add all` moved from 4 to 5 configs, and four scenarios added (`Add hermes`, `Hermes env references only`, `Hermes single-scope project substitution`, `Hermes merge preserves the document`). MCP-REG-02's `remove` enumeration gains `hermes`. No Test Mapping row and no registry edit: declared-backlog spec. |
| `cli` | Updated | CLI-R09 amended: both `--agent` enumerations gain `hermes`, the env-forwarding paragraph gains Hermes (and the `$KEY` / `${KEY}` split), a sentence pair for the YAML preservation and the single-scope note, the `add help` / `remove help` scenarios gain `hermes`, the env-forwarding scenario names Hermes, and one scenario is added (`add help documents the YAML preservation and the single-scope note`). No Test Mapping row and no registry edit: declared-backlog spec. |

Both canonical specs were amended **in place** from their deltas' `## MODIFIED Requirements` blocks,
which describe the spans that moved rather than re-copying the whole requirements. The deltas also
gained the line-ending precision after the independent verifier falsified the first wording.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, T1–T11 `done`; T12 records the push and the PR and is `pending` at archive
  time by design — the PR cannot be cited before the commit that archives the change exists, and the
  follow-up record commit inside the same PR closes it
- `specs/mcp-registration/spec.md` (delta) — present
- `specs/cli/spec.md` (delta) — present

No `explore.md`, `apply-progress.md`, `verify-report.md` or `sync-report.md` siblings were produced;
the work was orchestrated by the parent session and its evidence lives in the tasks table and in this
report.

## Evidence

| Item | Evidence |
| --- | --- |
| RED/GREEN, YAML work unit | RED `6 failed, 125 passed, 2 skipped, 1 error` (the error is the missing `_yaml` module at collection) → GREEN `153 passed, 2 skipped` |
| RED/GREEN, adapter work unit | RED `28 failed, 316 passed, 3 skipped` → GREEN `344 passed, 3 skipped` |
| Full suite at the tip | `uv run pytest tests/ -q` → **2088 passed, 8 skipped** (the run before the line-ending fix measured 2082; the fix added 6 tests) |
| Rule 14 | `cli.py 637 0 194 0 100%`, `scanner.py` / `prepare.py` / `publish.py` 100%; `scripts/check_core_coverage.sh` exit 0; pragma count 0 in all four |
| TOTAL floor | `uv run coverage report -m` → TOTAL 94% (floor 90) |
| Lint, format, types | `ruff check src/ tests/ scripts/` clean; `ruff format --check src/ tests/` clean; `mypy src/ scripts/` clean (37 files); `pyright` 0 errors (1 pre-existing `_tomli` warning) |
| Test-mapping gate | `uv run python scripts/check_test_mapping.py` → `OK: test-mapping contract holds` |
| End-to-end | Real CLI against a temp `HERMES_HOME` with a commented config: add → read back the entry, the absolute `cwd`, the `${KEY}` env form and the untouched sibling/comment lines; re-run → byte-identical, no new `.bak`; remove → back to the pre-add bytes; `--scope project` → the note on stderr and no `<cwd>/.hermes/`; `--agent all --scope project` → five configs |
| Adversarial | CRLF, LF, no trailing newline, quoted key, flow-style `mcp_servers`, block-sequence `mcp_servers` followed by another top-level key, blank line + comment after the entry — unrelated lines byte-identical in every case after the fix |

## Independent verification, and what it changed

An independent verifier ran the gate set, drove the CLI end-to-end and probed the splice writer. It
**falsified one clause** of the first implementation: on Windows the YAML branch read the pre-write
text with universal newlines and wrote in text mode, so an LF-only `config.yaml` came back entirely
CRLF and "unrelated lines stay byte-identical" was false. The fix (`efb439b`) reads and writes with
`newline=""`, renders the spliced entry with the document's own ending, and adds six tests; the
verifier re-ran the probes and closed the finding, and its second pass reported one nit — the
`mcp-registration` Purpose line still naming four agents — which is fixed in this archive commit.

## Declared boundaries

- **No native `hermes` delegation.** `hermes mcp add` documents no `cwd` and no env surface, and the
  issue's own reproduction had to run `hermes config set mcp_servers.sofer.cwd` afterwards; a native
  path that omitted `cwd` would reproduce the defect this change removes (D2).
- **Single-scope resolution, confirmed with the maintainer.** Hermes reads one config and has no
  project-scope file, so `--scope project` resolves to it and the substitution is named on stderr
  rather than refused or written into a file Hermes never reads (D4).
- **JSON's whole-document rewrite is untouched**, including its Windows line-ending translation: that
  is pre-existing, declared behavior, out of this change's scope, and only the YAML branch carries the
  byte-preservation contract (D5).
- No version bump, no dependency change (`pyyaml` was already a runtime dependency), no Test Mapping
  rows, and no `openspec/test-mapping-registry.md` edit.
