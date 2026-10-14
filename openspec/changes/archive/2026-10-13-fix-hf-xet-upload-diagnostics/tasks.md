# Tasks: fix-hf-xet-upload-diagnostics

**Change** `2026-10-13-fix-hf-xet-upload-diagnostics` (GitHub **#289**) · branch
`fix/289-hf-xet-upload-diagnostics` from `dev@4ca823e` · store **hybrid** — this file
plus the Engram mirror.

**Inputs read this phase, directly:** `design.md` and `proposal.md` of this change.

**One-line outcome:** a failed `upload_folder` names its exception type and message plus
the active Hub backend (env names from `[tool.sofer]`), retries exactly once, and reports
a created-but-empty repository; the READMEs document the `HF_HUB_DISABLE_XET=1`
workaround.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`; the parent task required a red-first
carrier, and a real red-then-green was observed:

- **RED (measured):** `pytest tests/test_publish.py::TestHfUploadDiagnostics
  tests/test_publish.py::TestPublishEmptyRepositoryReport` → **10 failed, 1 passed**, the
  named-cause case quoting `✗  boom from the hub` (no type, no backend) and the flaky case
  `assert False is True` (no retry).
- **GREEN (measured):** the same selection → **11 passed**; focused files →
  `389 passed, 3 skipped`.

**REFACTOR has no target** — the change adds diagnostics and a bounded loop around an
existing call.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: tests for the named cause, the repo-created/0-uploaded report, and the backend probe | done | `10 failed, 1 passed`; the `✗ boom from the hub` / `assert False is True` cases quoted in `design.md` §2 |
| T2 | `_hf_upload_folder` reports `<type>: <message>` plus the active backend (env names read from config) | done | `TestHfUploadDiagnostics::test_failure_names_*`, `test_backend_probe_reads_names_from_config` |
| T3 | `publish()` reports the created-but-empty repository state on a 0-upload failure | done | `TestPublishEmptyRepositoryReport` (2 tests) |
| T4 | D2 applied: exactly one bounded retry with its own tests | done | `test_retries_once_then_succeeds`, `test_fails_after_exactly_one_retry`, `test_retry_count_is_config_owned` |
| T5 | README + README_ES troubleshooting: `HF_HUB_DISABLE_XET=1` before blaming the package or the token | done | `README.md` / `README_ES.md` `### Troubleshooting HF uploads` / `### Solución de problemas de subida a HF` |
| T6 | `publish` spec delta (PUB-01) declaring the failure reporting | done | `specs/publish/spec.md` delta; registry untouched |
| T7 | Gates: `publish.py` 100.00% with no pragma (rule 14), full suite, ruff/format/mypy/pyright, coverage TOTAL ≥ 90 | done | verify report; `check_core_coverage.sh` exits 0; `publish.py 351 0 150 0 100%` |
| T8 | Commit (`fix(publish): ...`, `Closes #289`) | handed off | all git mutations are owned by the parent; this worktree carries the changes uncommitted |
| T9 | Config-owned defaults for the retry count, the two env-var names and the message cap, with their validation arms covered | done | `TestHfUploadConfigDefaults`; `_DEFAULTS` + module constants in `config.py` |

---

## Constraints honoured

- **Nothing outside the allowed edit surfaces** (`publish.py`, `config.py`, the three
  listed test files, both READMEs, `openspec/**`, the ODD task file). `pyproject.toml`
  is deliberately untouched (risk R4).
- **`publish.py` stays at 100.00%** line and branch coverage; no `# pragma: no cover`
  anywhere (rule 14).
- **Every new default is config-owned** (`hf_upload_retry_count`,
  `hf_backend_disable_env`, `hf_backend_prefix_env`, `hf_upload_error_max_chars`) and read
  at the call site — no literal in `publish.py` (rules 1/D3).
- **No automatic non-xet fallback and no `--no-xet` flag** (D1/D2); the documented
  workaround is an environment re-run, not a process-model change.
- No new requirement; no Test Mapping row; no registry edit; no version bump.

---

## Not carried by this change

The systematic (0/9) case is mitigated by naming the cause and the README workaround, not
fixed in-process: `HF_HUB_DISABLE_XET` is an import-time constant and `upload_folder`
exposes no backend kwarg (D1). A supported per-call backend selector remains a follow-up
only if huggingface_hub adds one.
