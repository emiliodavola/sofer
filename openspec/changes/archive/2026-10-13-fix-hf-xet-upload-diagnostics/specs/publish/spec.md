# Delta for publish

> **Change** `2026-10-13-fix-hf-xet-upload-diagnostics` (issue **#289**) · branch
> `fix/289-hf-xet-upload-diagnostics` from `dev@4ca823e` · store **hybrid**.
>
> **One modification, no new requirement.** PUB-01 gains the upload-failure reporting it
> never had: a named cause, a config-owned backend probe, one bounded retry, and the
> created-but-empty repository report.
>
> **Rule-6 resolution.** `publish` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the new scenarios map to their tests in
> `tests/test_publish.py` without a Test Mapping row, and the registry is not edited.

## MODIFIED Requirements

### Requirement: hf target uploads via upload_folder (PUB-01) — Universal (Modified 2026-10-13, fix-hf-xet-upload-diagnostics)

> Added by change `fix-multisheet-parquet-publish` (archived 2026-08-29).
>
> Modified by `2026-10-13-fix-hf-xet-upload-diagnostics` (issue #289) — an upload
> failure now names its cause and the active transfer backend, retries once, and reports
> a created-but-empty repository.

**Modification scope.** Exactly two spans move, and nothing else in the requirement does:

| Span | Operation |
| --- | --- |
| the requirement body | one paragraph appended after the existing body: named upload failure, config-owned backend probe, bounded retry, no fallback, created-but-empty report |
| the scenarios | three scenarios appended after `upload failure` |

**Added clause (verbatim, as it reads in the canonical spec after this change):**

When `upload_folder` fails, the system SHALL report the underlying exception as
`<type(exc).__name__>: <str(exc)>`, truncating the message at `[tool.sofer]`
`hf_upload_error_max_chars`, and SHALL name whether the xet transfer backend is active.
The backend probe SHALL read the `HF_HUB_DISABLE_XET` and `HF_XET_*` environment-variable
names from `[tool.sofer]` (`hf_backend_disable_env` / `hf_backend_prefix_env`), never
hardcoded, and SHALL take the effective disable flag from the `huggingface_hub` import-time
constant — an in-process environment flip is NOT reliable. The system SHALL retry the
upload at most `[tool.sofer] hf_upload_retry_count` times (default 1) and SHALL NOT attempt
an automatic non-xet fallback: `upload_folder` exposes no backend kwarg and the disable
flag is an import-time constant, so the documented recovery is a re-run with
`HF_HUB_DISABLE_XET=1`. When the repository held no files and no file was uploaded, the
system SHALL report the created-but-empty repository state explicitly ("Repository created,
0 files uploaded").

**Added scenarios (verbatim):**

#### Scenario: Upload failure names the cause and the backend

- GIVEN a prepared package and an `upload_folder` call that raises `I/O error: No such file or directory (os error 2)`
- WHEN `publish --target hf` runs
- THEN the report SHALL name the exception type and message (`<type>: <message>`) and whether the xet backend is active
- AND it SHALL NOT print a bare, unnamed `I/O error`

#### Scenario: Upload retried once

- GIVEN an `upload_folder` call that raises on its first attempt and succeeds on its second
- WHEN `publish --target hf` runs
- THEN the upload SHALL be attempted exactly twice and SHALL be reported as a success
- AND GIVEN an `upload_folder` call that raises on every attempt
- THEN it SHALL be attempted at most `hf_upload_retry_count + 1` times, the failure SHALL name the cause, and rc 1 SHALL be returned

#### Scenario: Created-but-empty repository reported

- GIVEN a repository that held no files and an `upload_folder` call that uploads nothing
- WHEN `publish --target hf` runs
- THEN the report SHALL state `Repository created, 0 files uploaded`
- AND GIVEN a repository that already held files, that statement SHALL NOT be printed

## Non-goals recorded by this change

No runtime `--no-xet` flag and no automatic in-process non-xet fallback (D1); no change to
the fail-closed remote prologue (PUB-05) or the cleanup gate (PUB-11); no new requirement;
no Test Mapping row; no registry edit; no version bump; no `pyproject.toml` edit; no
commit/push/PR from SDD phases.
