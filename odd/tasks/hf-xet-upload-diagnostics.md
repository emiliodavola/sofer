# Feature: hf-xet-upload-diagnostics — issue #289

**Branch:** `fix/289-hf-xet-upload-diagnostics` from `dev@4ca823e`. **Issue:** `emiliodavola/sofer#289`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-fix-hf-xet-upload-diagnostics/`
(archived inside this PR, AGENTS.md rule 15). **Risk:** high — delivery path, remote side effects.

## Goal

`sofer publish --target hf` reports `✗ I/O error: No such file or directory (os error 2)` for every
file, uploads nothing, and never names the backend that failed. With `hf-xet` active the same command
failed 0/9 three times and succeeded 9/9 with `HF_HUB_DISABLE_XET=1` (issue rows 1–6). The repository
is created before the upload, so the failure leaves a half-created, empty repo and an error the caller
reads as a flaky network. Make the failure name its cause, make the resulting state unambiguous, and
document the workaround. Evidence map: `src/sofer/publish.py:176-209` (`_hf_upload_folder`), `:108-136`
(`_ensure_repo`), `:818-864` (`publish()`), `:821` (`staging_root` → the reported `↑ repo/ →` label).

## Specs

S1 (issue §"Proposed solution" 1, verbatim): "**Name the backend in the error.** When the upload
raises, print the underlying exception type and whether xet is active (`HF_HUB_DISABLE_XET` /
`HF_XET_*`), so the user is not left guessing from \"I/O error\"."
S2 (issue §1, verbatim): "**Retry or fall back.** A failed xet upload of a folder that
`upload_folder` handles fine deserves at least one retry, and arguably an automatic fallback to the
non-xet path (or an explicit `--no-xet` flag mirroring `HF_HUB_DISABLE_XET`)."
S3 (issue §3, verbatim): "**Document the workaround** in the publish/troubleshooting section: if a
publish reports `0 uploaded, N failed` with an `I/O error`, re-run with `HF_HUB_DISABLE_XET=1` before
assuming the package or the token is wrong."
S4 (issue §4, verbatim): "**Do not leave a half-created repo behind silently.** The failure creates
the repo and uploads nothing; reporting that state explicitly (\"repository created, 0 files
uploaded\") makes the outcome unambiguous."
S5 (issue §Impact, verbatim): "the first (and in one sequence, every) HF publish of a perfectly valid
package uploads **nothing** and reports an opaque error that never names xet; the caller has to
diagnose it and discover `HF_HUB_DISABLE_XET=1` on their own."

## Decisions not in the issue

| # | Decision | Evidence |
| --- | --- | --- |
| D1 | **No runtime `--no-xet` flag and no automatic in-process non-xet fallback.** `HF_HUB_DISABLE_XET` is read as an import-time constant and `upload_folder` exposes no backend kwarg, so a mid-process flip cannot be made reliable; the flag alternative would need a subprocess/re-exec, a process-model change out of scope for a diagnostic fix. | `huggingface_hub/constants.py:343` (constant read at import); `upload_folder` signature has no xet/backend parameter. |
| D2 | **Implement one bounded retry** around the upload and stop there: no automatic xet fallback and no `--no-xet` flag. | Maintainer decision (L4), taken after the constraint below was explained: the retry covers the intermittent case (issue row 3, 6/9), while the systematic case (0/9, rows 1/4/5) is fixed by naming the cause and documenting the workaround. `HF_HUB_DISABLE_XET` is an import-time constant (`huggingface_hub/constants.py:343`), `upload_folder` has no backend kwarg (signature verified in the worktree venv), and `is_xet_available()` (`huggingface_hub/utils/_runtime.py:157-162`) reads that constant on every call — so only an unsupported third-party monkeypatch or a process re-exec could flip it mid-run. |
| D3 | The xet/backend probe reads `HF_HUB_DISABLE_XET` and the `HF_XET_*` names from **config**, never hardcoded in the function. | AGENTS.md rule 1; `[tool.sofer]` is the tool-defaults home. |

## Tasks

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | RED: tests for the named cause, the repo-created/0-uploaded report, and the documented workaround | S1 S4 | pending | — |
| T2 | `_hf_upload_folder` reports `type(exc).__name__: exc` plus the active backend (xet on/off, env names read from config) | S1 D1 D3 | pending | — |
| T3 | `publish()` reports the created-but-empty repository state explicitly when 0 files uploaded | S4 | pending | — |
| T4 | D2 decision applied (retry or not) with its own test | S2 | pending | — |
| T5 | README + README_ES troubleshooting: `HF_HUB_DISABLE_XET=1` before blaming the package or the token | S3 S5 | pending | — |
| T6 | `publish` spec delta (PUB-01/PUB-05/PUB-11) declaring the failure reporting | S1 S4 | pending | — |
| T7 | Gates: `publish.py` 100.00% with no pragma (AGENTS.md rule 14), full suite, ruff/format/mypy/pyright, coverage TOTAL ≥ 90 | — | pending | — |
| T8 | Commit + push + PR (base `dev`, assignee `emiliodavola`), `Closes #289` | — | pending | — |

## Log

L1 (2026-10-13, user, verbatim): "revisá los issues tipo bug e implementalos, 1 rama y PR (asignado a
mi) por issue"
L2: exploration (gentle-ai-explore) mapped the defect sites and found D1's technical blocker — a
runtime `--no-xet` cannot be reliable.
L3 (resolved): D2's retry scope was asked to the maintainer as one question, with the technical
constraint on a runtime `--no-xet` explained in plain language.
L4 (2026-10-13, maintainer answer, verbatim): "Diagnóstico + un retry" — D2 settled: exactly one
bounded retry, no fallback, no flag.
