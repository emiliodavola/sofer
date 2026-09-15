# Delta for codebook

**Capability choice (justified):** `codebook` only — CB-R11 is a codebook-generation contract: which
delimiter/encoding the emitted codebook reflects, and what a caller sees when the input cannot be
decoded. `tool-config` **TC-04** (`openspec/specs/tool-config/spec.md:65`) already fixes the *tier*
(discovery anchors on the cwd, one reload per invocation) and **TC-13** deliberately validates
`csv_encoding` only as "a non-empty string", so a typo'd codec name is reachable and is not a
config-validation defect. `mcp-server` **MSP-R10** (`:373-405`) owns the parity contract but its
scenario at `:401-405` is written for the MCP tool and is already satisfied pre-change — it gains no
text. `cli` **CLI-R10** governs status-JSON stability, NOT general parity (proposal
"Resolved decisions" 5), so it is not cited as basis. CB-R11 is the next free id (CB-R10 is the
current tail at `openspec/specs/codebook/spec.md:294`).

ADDED, not MODIFIED: no existing requirement's text changes — CB-R01/CB-R02 and CB-R08 stay verbatim
and this clause is purely additive, so no lossy archive-time replacement is incurred (CB-R10
precedent, parity gap #155). `codebook` owns the contract; the CLI single-file branch is one caller.

## ADDED Requirements

### Requirement: Single-file codebook reads through the resolved tool-wide config (CB-R11)

The `sofer codebook FILE` path SHALL pass the resolved tool-wide `config.CSV_DELIMITER` and
`config.CSV_ENCODING` into `codebook.generate`, resolved at call time after the invocation's single
tool-config reload (TC-04) — the same source MSP-R10 requires of the MCP codebook tools — and SHALL
NOT let the literal defaults in `codebook.generate` (`";"`, `"utf-8-sig"`) take effect.

When the input cannot be read — the configured encoding and the repository's fallback chain are
exhausted (`ValueError`), or the configured encoding names a codec that does not exist (`LookupError`,
reachable per TC-13) — the command SHALL print `Error: <message>` on stderr and SHALL exit non-zero.
It SHALL NOT emit an uncaught traceback, and it SHALL NOT retry `latin-1`/`cp1252`: the fallback
policy remains the repository's existing `utf-8-sig → utf-8` (`src/sofer/_csv_reader.py:27-31`), with
a configured non-UTF-8 encoding honoured first. `codebook.generate`'s parameter defaults and the
dataset-`[meta]` resolution of `generate_all` (`codebook.py:505-506`) SHALL remain unchanged, as the
fallback for direct library callers and for the `--all-files` tier respectively.

#### Scenario: Configured delimiter and encoding are what the codebook reflects

- GIVEN `[tool.sofer] csv_delimiter = ","` (and, separately, a non-default `csv_encoding`) and a file matching that configuration
- WHEN `sofer codebook FILE` runs with no `--config`
- THEN the codebook SHALL show the columns induced by the configured delimiter (two columns for a two-field header)
- AND the file SHALL be read under the configured encoding, not the literal `";"` / `"utf-8-sig"` defaults

#### Scenario: CLI and MCP agree on the same input

- GIVEN the same tool-wide config and the same file
- WHEN the CLI single-file command and the MCP single-file tool both run
- THEN both SHALL produce the same column structure for that file
- AND no MCP source or MCP test SHALL be modified by this change

#### Scenario: Undecodable input yields a diagnostic, never a traceback

- GIVEN a file that cannot be decoded under the configured encoding nor under `utf-8-sig → utf-8`
- WHEN `sofer codebook FILE` runs
- THEN it SHALL print `Error: <message>` on stderr
- AND it SHALL exit non-zero, with no uncaught traceback

#### Scenario: Unknown codec name yields the same diagnostic

- GIVEN `[tool.sofer] csv_encoding` naming a codec that does not exist (valid as a non-empty string under TC-13)
- WHEN `sofer codebook FILE` runs
- THEN the same `Error: <message>` diagnostic SHALL be printed on stderr with a non-zero exit
- AND no traceback SHALL escape the command

#### Scenario: The fallback policy is the existing one, not a new one

- GIVEN the configured encoding is honoured first and then exhausted
- WHEN the readers fall back
- THEN only `utf-8-sig → utf-8` SHALL be tried
- AND `latin-1`/`cp1252` SHALL NOT be added as retries

## Non-goals (binding)

- **No MCP change**: `src/sofer/mcp_server.py` is already correct (`:1481-1487`, `:2890-2893`) and pinned by `tests/test_mcp_server.py:3564-3574`; no MCP source or test edit.
- **Zero paths under `src/sofer/_converters.py` and `src/sofer/prepare.py`** — that defect is issue #181, a separate change with its own SDD cycle.
- No change to `codebook.generate`'s parameter defaults (library-caller fallback) and none to `generate_all`'s dataset-`[meta]` tier (`codebook.py:505-506`).
- No new CLI flag; no `README.md` / `README_ES.md`, `pyproject.toml` or workflow change; no codec-name validation at config-merge time (would re-open TC-13).
- Untouched: `tasks.md`, `proposal.md`, `openspec/specs/**` (canonical sync is archive-time), `openspec/changes/archive/**`, and every other in-flight change.
- No commit, push or PR — the parent owns delivery.

## Test Mapping

`codebook` carries no Test Mapping section; this delta adds one for CB-R11 only. Unlike the previous
two changes in this repository, **no command-evidence carve-out is needed**: every scenario below is
asserted by a real pytest test. All new CLI cases MUST drive the `tests/conftest.py::run_cli`
subprocess boundary (PB-02) because `src/sofer/cli.py` is under the **100.00% per-file line-coverage
mandate with `# pragma: no cover` forbidden** (AGENTS.md rule 14) — the new `ValueError`/`LookupError`
arms must actually execute there; an in-process `_cmd_codebook` call MAY be added but MUST NOT replace
the boundary test. Every scenario uses a non-default delimiter or encoding, or a deliberately broken
one: a `";"`-default case would prove nothing about this change. New tests land in `tests/test_cli.py`.

| Req | Scenario | Verification | Strength |
| --- | --- | --- | --- |
| CB-R11 | Configured delimiter and encoding are reflected | **pytest-asserted**: `tests/test_cli.py` CLI twin of `tests/test_mcp_server.py:3564` (`csv_delimiter = ","` + `,`-delimited file → 2 columns) and a non-default-`csv_encoding` success case, both through `run_cli` | Strong |
| CB-R11 | CLI and MCP agree on the same input | **pytest-asserted**: the CLI case above asserts the column structure the MCP case `test_codebook_honors_tool_sofer_delimiter` already asserts; MCP code/tests are byte-identical (`git diff --stat`) | Strong |
| CB-R11 | Undecodable input yields a diagnostic | **pytest-asserted**: undecodable bytes → `run_cli` rc ≠ 0, stderr starts with `Error: `, `"Traceback"` absent from stderr | Strong |
| CB-R11 | Unknown codec name yields the same diagnostic | **pytest-asserted**: `csv_encoding = "not-a-codec"` → same rc/stderr assertions; this is the arm that keeps `cli.py` at 100.00% | Strong |
| CB-R11 | Fallback policy is the existing one | **pytest-asserted**: existing `tests/test_quality.py:750-757` (`latin-1 → ValueError("Cannot decode")`) stays green, and the undecodable CLI case above confirms no `latin-1`/`cp1252` rescue; `_csv_reader.py` is untouched | Strong |
