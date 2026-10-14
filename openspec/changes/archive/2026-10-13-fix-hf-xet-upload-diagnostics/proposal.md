# Proposal — `2026-10-13-fix-hf-xet-upload-diagnostics`

> **Change** `2026-10-13-fix-hf-xet-upload-diagnostics` · issue **#289** · branch
> `fix/289-hf-xet-upload-diagnostics` from `dev@4ca823e` · store **hybrid** (this file + Engram mirror).

---

## 1. Intent

Issue #289 reports that `sofer publish --target hf` fails with
`✗ I/O error: No such file or directory (os error 2)` for **every** file, uploads **nothing**,
and never names the transfer backend that failed. With `hf-xet` active the same command failed
0/9 three times and succeeded 9/9 with `HF_HUB_DISABLE_XET=1`. The repository is created **before**
the upload, so the failure leaves a half-created, empty repository behind and the caller reads the
opaque message as a flaky network.

This change makes the failure name its cause, makes the resulting state unambiguous, bounds the
recovery attempt, and documents the workaround. It does **not** change what is uploaded or how the
upload is scheduled.

## 2. Scope

### In scope

- `_hf_upload_folder` reports `<type(exc).__name__>: <str(exc)>` (config-capped) plus whether the
  xet backend is active, with the env-var **names** read from `[tool.sofer]`, and retries the upload
  exactly once.
- `publish()` names the created-but-empty repository state when the repository was empty and 0 files
  were uploaded.
- Four new `[tool.sofer]` defaults: `hf_upload_retry_count`, `hf_backend_disable_env`,
  `hf_backend_prefix_env`, `hf_upload_error_max_chars` (config-owned, read at the call site).
- README + README_ES publish/troubleshooting workaround (`HF_HUB_DISABLE_XET=1`).
- PUB-01 gains the failure-reporting clause and three scenarios.

### Out of scope (non-goals)

- **No runtime `--no-xet` flag and no automatic in-process non-xet fallback** (decision D1).
- No change to the remote fail-closed prologue (PUB-05): `_ensure_repo` / `_inspect_repo` semantics
  are untouched.
- No change to `--clean` gating (PUB-11): a failed upload still never deletes anything.
- No new requirement; no `## Test Mapping` row (`publish` is a permanent declared-backlog spec, so
  `openspec/test-mapping-registry.md` is untouched); no version bump; no PyPI change.

## 3. Settled decisions

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | **No runtime `--no-xet` flag and no automatic in-process non-xet fallback.** | `HF_HUB_DISABLE_XET` is read as an import-time constant (`huggingface_hub/constants.py`) and `upload_folder` exposes no backend kwarg, so a mid-process flip cannot be made reliable; a flag would need a subprocess/re-exec — a process-model change out of scope for a diagnostic fix. |
| **D2** | **Exactly one bounded retry** around the upload; no fallback, no flag. | Maintainer decision (ODD L4: "Diagnóstico + un retry"). The retry covers the intermittent case (issue rows 3, 6/9); the systematic case (0/9) is fixed by naming the cause and documenting the workaround. |
| **D3** | The backend probe reads `HF_HUB_DISABLE_XET` and the `HF_XET_*` names from **config**, never hardcoded in the function. | AGENTS.md rule 1; `[tool.sofer]` is the tool-defaults home. The active/disabled flag itself comes from `huggingface_hub.constants` — the same import-time constant D1 records. |

## 4. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | The new behaviour tests are red before the change and green after |
| SC-2 | `publish.py` stays at **100.00%** line and branch coverage with zero `# pragma: no cover` (`scripts/check_core_coverage.sh` exits 0) |
| SC-3 | The full suite is green; TOTAL coverage stays ≥ 90 |
| SC-4 | The retry count, both env-var names and the message cap are config-owned and overridable from `[tool.sofer]` (pinned by tests) |
| SC-5 | PUB-01 carries the clause and the three scenarios; `check_test_mapping.py` exits 0 and the registry is untouched |
| SC-6 | README.md and README_ES.md both carry the workaround, with English technical content |

## 5. Non-goals (restated for the spec delta)

No change to the fail-closed remote prologue (PUB-05) or the cleanup gate (PUB-11); no `--no-xet`
flag; no automatic fallback; no new requirement; no Test Mapping row; no registry edit; no version
bump; no commit/push/PR from SDD phases.
