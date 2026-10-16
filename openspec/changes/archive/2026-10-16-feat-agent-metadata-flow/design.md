# Design — `2026-10-16-feat-agent-metadata-flow`

> **Change** `2026-10-16-feat-agent-metadata-flow` (issue **#288**) · branch
> `feat/288-agent-metadata-flow` from `dev@6786ba1` · store **hybrid**.

---

## 1. The defect, precisely

Measured on the reported run: `sofer_validate` returned
`{"ok":true,"passed":true,"errors":[],"warnings":[],"quality_failures":[],"quality_warnings":[]}` for a
config whose `[meta]` block was `description = "TODO: short description"`, `license = "TODO: MIT / …"`,
`source = "TODO: organisation name"`, `tags = ["TODO: tag1", "TODO: tag2"]`. Nothing in the chain
mentioned metadata, so the placeholders travelled to the Dataset Card and the LICENSE with every
envelope reporting success.

## 2. The two halves, and why both

**The chain.** `_PHASED_INSTRUCTIONS` listed Phase 0, Phase 1 and Phase 2 with no metadata step between
them. It was edited to name one, positioned *before* `Phase 1 Build` — which the test asserts by index,
not by presence, because a step listed after the phase it precedes teaches the wrong order (the first
draft did exactly that and the test caught it). `sofer_validate`'s `Requires` gains
`[meta] description/license/source/tags filled (no placeholders)` in both carriers: the tool docstring
(what `tools/list` ships) and `workflow.WORKFLOW_METADATA` (the registry MSP-R13 calls the single source
for the chain).

**The gate.** `meta_placeholder_warnings(cfg)` returns one message per offending field, and
`DatasetValidator.run_all()` extends `report.warnings` with them. That single call site covers the CLI
`sofer validate`, the MCP `sofer_validate` tool, and the pre-prepare run that `prepare` performs — the
three surfaces the issue names — with no second implementation.

## 3. Decisions and their evidence

| # | Decision | Evidence / rationale |
| --- | --- | --- |
| D1 | **Warn, never fail** (maintainer D3). | A `fail` would break every existing config that still carries a placeholder — a contract change rather than a fix. `ValidationReport.passed` is asserted `True` with the warning present. |
| D2 | The prefixes are `[tool.sofer] meta_placeholder_prefixes`, default `["TODO", "YOUR_", "example"]`. | AGENTS.md rule 1; the list matches the issue's own wording. Validated as a non-empty list of non-empty strings, so a bad value cannot make the gate match everything or nothing. |
| D3 | Only a **prefix** matches, case-insensitively. | "An example-driven survey" is prose; "example.org" is a stand-in. Tested both ways. |
| D4 | An empty value warns for the three scalars but an empty `tags` list does not. | There is no value to replace in an empty list; warning about it would be noise on every config that legitimately declares no tags. |
| D5 | No `sofer_meta_set` / `sofer_meta_check` tool. | The issue offers it as one option, not a requirement, and adding a tool changes the advertised inventory — its own decision on its own schema/parity surface. Recorded as a follow-up. |

## 4. The one honest caveat about `example`

`example` as a prefix flags an organisation genuinely named "Example …". That is the issue's own prefix
list and it is the intended behaviour — the template's stand-in values are what the gate exists to
catch — but it is a false-positive surface, so it is named in a named test
(`test_an_example_prefixed_source_is_flagged`) and here, rather than discovered by a user. A config that
means it literally can add a prefix-free wording, or the maintainer can drop `example` from the
`[tool.sofer]` list, which is exactly why the list is configuration.

## 5. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests, so the
new tests did not themselves observe RED. What was measured:

- `140 passed` on the five affected existing files **before** the new tests existed — no existing
  expectation changed, because the gate only adds warnings and the surface edits are prose.
- The first run of the new tests: `5 failed, 17 passed`. All five were **my** errors, not the code's, and
  each is recorded because each was a wrong premise: an empty `tags` list is not a placeholder (3
  warnings, not 4); a fixture using `source = "Example Organisation"` as if it were a real value trips
  the `example` prefix, which is correct; `config` was not imported by the test module; and a
  `passed is True` assertion was measuring a missing-file error rather than the warning, so the fixture
  now creates the file.
- The surface test's first run found a real ordering defect in the change itself: the metadata step was
  listed after `Phase 1 Build`, so the assertion is by index.
- Final: `23 passed` on `tests/test_checks.py`, `6 passed` on the surface class, `2170 passed, 9 skipped`
  on the full suite.

## 6. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | The `example` prefix flags a legitimate value. | Low | Named in §4 and in a dedicated test; the list is `[tool.sofer]`-configurable. |
| R2 | The warning is noise on a config that intentionally keeps a placeholder. | Low | It is one line per field in the validate report, and it never changes the exit code. |
| R3 | The chain edit breaks the advertised phase order. | Low | Asserted by index, and a test asserts all three phases still appear. |
| R4 | `run_all()` gaining a check changes an existing report's warning count. | Low | Only adds warnings; the full suite records no changed expectation. |

## 7. Rollback

Revert-only: drop the function and its `run_all` call, the config key, and the three prose edits.
No state, no migration.
