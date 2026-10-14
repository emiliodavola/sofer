# Design — `2026-10-13-fix-hf-xet-upload-diagnostics`

> **Change** `2026-10-13-fix-hf-xet-upload-diagnostics` (issue **#289**) · branch
> `fix/289-hf-xet-upload-diagnostics` from `dev@4ca823e` · store **hybrid**.

---

## 1. The defect, precisely

`_hf_upload_folder` uploaded the staged tree and, on failure, printed a bare
`print(f"  ✗  {exc}")` and returned `False`. For a failing xet upload of a folder the
non-xet path handles fine, that is an `I/O error` with no type, no message and no hint
that the transfer backend is the variable. `publish()` then printed
`Result: 0 uploaded, N failed` and returned rc 1 while leaving the repository it had just
created empty — an outcome the caller could not distinguish from a partial or flaky push.

Evidence map: `src/sofer/publish.py:176-209` (`_hf_upload_folder`), `:108-136`
(`_ensure_repo`), `:818-864` (`publish()`), `:821` (`staging_root` → the reported
`↑ repo/ →` label).

## 2. Measured evidence (parent shell runs, quoted)

RED against the unmodified code, on two of the new tests:

```
>       assert "RuntimeError: boom from the hub" in out, out
E       assert 'RuntimeError: boom from the hub' in '  \u2191  pkg/  \u2192  \\n  \u2717  boom from the hub\\n'
...
>       assert False is True
E       assert False is True
```

The old output is `✗  boom from the hub` — no exception type, no backend — and the flaky
case (first attempt raises, second would succeed) is never retried, so `result is False`.
That run is the argument for the change.

Corroborating measurements (worktree venv, `huggingface_hub` 2.2.0):

| Check | Result |
| --- | --- |
| `HfApi.upload_folder` parameters | `repo_id, folder_path, path_in_repo, commit_message, commit_description, token, repo_type, revision, create_pr, parent_commit, allow_patterns, ignore_patterns, delete_patterns, run_as_future` — **no backend/xet kwarg** (D1) |
| `huggingface_hub.constants.HF_HUB_DISABLE_XET` | a plain `bool` read once at import — a mid-process flip is not reliable (D1) |
| `huggingface_hub.utils._runtime.is_xet_available()` | reads that constant on every call but is not exported from `huggingface_hub.utils`; the stable signal is the constant itself |
| `create_repo(..., exist_ok=True)` | returns normally for both "created" and "already exists"; only the legacy already-exists **exception** path distinguishes them |

## 3. The edits

### 3.1 `src/sofer/config.py` — four config-owned defaults

Added to `_DEFAULTS` (and mirrored as module constants) exactly the values this change
needs: `hf_upload_retry_count = 1`, `hf_backend_disable_env = "HF_HUB_DISABLE_XET"`,
`hf_backend_prefix_env = "HF_XET_"`, `hf_upload_error_max_chars = 500`. The retry count is
validated as a non-negative integer (0 disables the retry) and the cap as a positive
integer; both raise a `ValueError` naming the key, matching the existing type-validation
block. **No value is hardcoded in `publish.py`.**

### 3.2 `src/sofer/publish.py` — helper `_hf_backend_note()`

Reads the env-var **names** from `config.HF_BACKEND_DISABLE_ENV` /
`config.HF_BACKEND_PREFIX_ENV` and the authoritative disable flag from
`getattr(huggingface_hub.constants, disable_env, False)` — the import-time constant D1
records, so an in-process env flip is never reported as effective. Present `HF_XET_*`
tuning variables are listed. The return is one line, e.g.
`xet backend: enabled (HF_HUB_DISABLE_XET unset or falsy)` or
`xet backend: disabled by HF_HUB_DISABLE_XET`.

### 3.3 `src/sofer/publish.py` — helper `_print_upload_failure(exc)` (S1)

Prints `✗  <type(exc).__name__>: <str(exc)>`, truncating the message at
`config.HF_UPLOAD_ERROR_MAX_CHARS` (ellipsis suffix), then the backend note. Shared by
every attempt so the retry's first failure and the final failure read identically.

### 3.4 `src/sofer/publish.py` — `_hf_upload_folder` bounded retry (S2/D2)

The single call becomes a loop over `config.HF_UPLOAD_RETRY_COUNT + 1` attempts. A
successful attempt prints `✓` and returns `True` immediately; a failing attempt prints the
named cause and, while attempts remain, an `↻ retrying upload (retry i/N) …` line. After
the bounded retries it returns `False`. **No fallback and no flag** (D1/D2). The old
try/except that swallowed the exception is replaced by this loop; the return contract
(`bool`, never raises) is unchanged.

### 3.5 `src/sofer/publish.py` — created-but-empty report (S4)

`publish()` already holds `existing_files` from the fail-closed prologue. When the upload
leaves `ok == 0` **and** the repository held no files (`not existing_files`), it prints:

```
  ⚠  Repository created, 0 files uploaded: <repo_id> exists but is empty.
     Re-run `sofer publish` once the upload failure is resolved.
```

If the repository already held files, the generic `Result: 0 uploaded, N failed` stands
alone — the "empty" claim is only made when it is true. PUB-05 and PUB-11 semantics are
untouched: nothing is deleted on failure and no upload is attempted after a failed
inspection.

### 3.6 Specs

PUB-01 gains one clause (named cause, config-owned backend probe, bounded retry, no
fallback, created-but-empty report) and three scenarios (`upload failure names the cause
and backend`, `upload retried once`, `created-but-empty repository reported`).
`publish` is a permanent declared-backlog spec: no Test Mapping row, and
`openspec/test-mapping-registry.md` is untouched.

### 3.7 Docs

README.md gains a `### Troubleshooting HF uploads` subsection under Command reference (and
the ToC entry); README_ES.md gains the matching `### Solución de problemas de subida a HF`
section. Prose is translated; the env-var names, commands and TOML keys stay English
(rule 13).

### 3.8 Tests

`tests/test_publish.py` gains `TestHfUploadDiagnostics` (named cause, backend
enabled/disabled/tuning, config-owned names, truncation, retry-success, retry-exhausted,
config-owned retry count), `TestHfUploadConfigDefaults` (the two validation arms) and
`TestPublishEmptyRepositoryReport` (empty repository reported; a repository with files is
not).

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`; the parent task nevertheless required a
red-first carrier for this change, and a real red-then-green was observed:

| Gate | RED (measured) | GREEN (measured) |
| --- | --- | --- |
| `pytest tests/test_publish.py::TestHfUploadDiagnostics tests/test_publish.py::TestPublishEmptyRepositoryReport` | **10 failed, 1 passed** (the passing one asserts absence of the new line) | **11 passed** |
| `pytest tests/test_publish.py` | — | **116 passed** |
| `pytest tests/test_publish.py tests/test_mcp_server.py tests/test_mcp_process.py` | — | **389 passed, 3 skipped** |

No REFACTOR target: the change adds diagnostics and a bounded loop around an existing call.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | A retry can duplicate a partially-completed upload | Low | `upload_folder` is a single commit-oriented call; the Hub treats a re-upload idempotently, and the retry is bounded to one. Accepted by D2. |
| R2 | `create_repo(exist_ok=True)` cannot distinguish "created now" from "already existed" | Low | The report is gated on the repository being **empty** (`not existing_files`), so "created … exists but is empty" is true in both cases; a repository that already held files never gets the line. |
| R3 | Reading `huggingface_hub.constants` by attribute name couples the probe to a third-party module | Low | The attribute is the documented import-time constant D1 names; `getattr(..., default=False)` degrades to "enabled" if it ever disappears, which is the safe diagnostic direction. |
| R4 | The repo's own `pyproject.toml` `[tool.sofer]` comment block does not list the four new keys | Low | `pyproject.toml` is outside this task's allowed edit surfaces; the keys are config-owned in `_DEFAULTS` and overridable from any `[tool.sofer]`. Recorded in the archive report. |

## 6. Rollback

Additive and revert-only: removing the two helpers, restoring the single
`try/except` body of `_hf_upload_folder`, dropping the four `_DEFAULTS` entries and their
constants, and reverting the README sections restores the previous behaviour exactly. No
state, no migration, no runtime side effect.

## 7. Success criteria

SC-1..SC-6 of `proposal.md` §4. Runtime evidence for SC-2 (the rule-14 gate) is recorded in
the verify report.
