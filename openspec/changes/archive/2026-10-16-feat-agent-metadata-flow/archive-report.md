# Archive report — `2026-10-16-feat-agent-metadata-flow`

> **Change** `2026-10-16-feat-agent-metadata-flow` · issue **#288** · branch
> `feat/288-agent-metadata-flow` from `dev@6786ba1` · milestone
> **v0.6.0 — agent surface & card completeness**.
>
> Archived inside the delivering branch, before the pull request (AGENTS.md rule 15).

---

## 1. What was delivered

The metadata step is in the surface the agent reads, and the pipeline warns while `[meta]` still carries
template placeholders — without failing the run.

| Deliverable | Where |
| --- | --- |
| MSP-META-01 (4 scenarios, inline `test:` evidence) | `openspec/specs/mcp-server/spec.md` |
| `meta_placeholder_warnings()` + `_looks_like_placeholder()` | `src/sofer/checks.py` |
| Wired into `DatasetValidator.run_all()` — one call site covering the CLI validate, the MCP tool and the pre-prepare run | `src/sofer/checks.py` |
| `[tool.sofer] meta_placeholder_prefixes` | `src/sofer/config.py`, `pyproject.toml` (both homes) |
| The metadata step in the advertised chain, `Requires:` on validate/prepare/init | `src/sofer/mcp_server.py` |
| The registry requirement for `sofer_validate` | `src/sofer/workflow.py` |
| Who fills `[meta]` | `README.md` + `README_ES.md` (rule 13) |
| 15 tests | `tests/test_checks.py` (9), `tests/test_mcp_server.py` (6) |

## 2. Task state

Every task in `tasks.md` is `done` (T1–T10). No `pending` row remains.

## 3. Measured evidence

| Gate | Result |
| --- | --- |
| Full suite | **2170 passed, 9 skipped** (83 s) |
| `cli.py` / `scanner.py` / `prepare.py` / `publish.py` 100.00% (rule 14) | **100%** each |
| TOTAL floor | **94%** |
| ruff / ruff format / mypy / pyright | clean (0 errors; 1 pre-existing `tomli` warning) |
| Test-mapping contract | `OK` |

## 4. Deviations, and the three findings worth keeping

1. **`sofer_meta_set` / `sofer_meta_check` were not delivered.** The issue offers them as one option
   ("or at least `sofer_meta_check`"), and a new tool changes the advertised tool inventory — its own
   decision on its own schema and parity surface. The warning already puts the step in front of the
   agent, which is the issue's stated goal for the gate. Recorded as a follow-up.
2. **`example` as a prefix has a false-positive surface.** It flags an organisation genuinely named
   "Example …". That is the issue's own prefix list and the intended behaviour, but it is named in a
   dedicated test and in `design.md` §4 rather than left for a user to discover — and the list is
   configuration, so a maintainer who decides otherwise changes one `[tool.sofer]` value.
3. **The change's first draft had an ordering defect.** `_PHASED_INSTRUCTIONS` listed the metadata step
   after `Phase 1 Build`, which teaches the wrong order. The surface test asserts the position **by
   index**, not by presence, and caught it. Recorded because a presence-only assertion would have
   passed.

## 5. TDD posture, and the five failures that were mine

`openspec/config.yaml` sets `strict_tdd: false`. The production edits landed before the new tests, so the
new tests did not themselves observe RED. The measured sequence:

- `140 passed` on the five affected existing files **before** the new tests existed — no existing
  expectation changed, because the gate only adds warnings.
- First run of the new tests: **`5 failed, 17 passed`**. All five were wrong premises of mine, not code
  defects: an empty `tags` list is not a placeholder (3 warnings, not 4); `source = "Example Organisation"`
  used as a "real" value trips the `example` prefix, correctly; `config` was not imported by the test
  module; and the `passed is True` assertion was measuring a missing-file error rather than the warning.
- Final: `23 passed` on `tests/test_checks.py`, `6 passed` on the surface class, `2170 passed, 9 skipped`
  on the full suite.

## 6. Follow-ups this change creates

- **`sofer_meta_check`**, if the maintainer wants the metadata step to be a *tool* rather than a warning:
  one read-only tool over `meta_placeholder_warnings`, plus the schema and parity updates a new tool
  requires.
- **`sofer meta set` (CLI)**, the same surface from the command line.
- **`example` in the prefix list**, if the false positive ever bites a real config.
