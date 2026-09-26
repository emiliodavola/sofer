# Archive Report — 2026-09-14-fix-hf-token-env-isolation

**Change**: `2026-09-14-fix-hf-token-env-isolation`
**Issue**: GitHub #176 (environment leakage between tests / HF token resolution)
**Date**: 2026-09-14/15 (archived 2026-09-14)
**Artifact store**: `openspec` (this file) mirrored to Engram `sdd/2026-09-14-fix-hf-token-env-isolation/archive-report` (observation id `1259`)
**Status**: **archived — PASS** (canonical sync performed at archive time; additive)
**Verify verdict**: **PASS** — `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 5/5`, `test_exit_code: 0`, `build_exit_code: 0`; validated by `gentle-ai sdd-verify-validate` → exit 0; `evidence_revision: sha256:9cae1a183b70074201df1a3b3a769df7fc3b6405c305d175d0be809518ab9b0e` — confirmed equal to the sha256 of the current `git diff`, with `test_output_hash` and `build_output_hash` each verified against the run's captured files
**Branch**: `fix/176-hf-token-test-isolation`
**Commits**: `3266171` `fix(mcp): resolve the HF token without mutating the process environment` (4 files) · `53e1e68` `docs(sdd): add the hf-token-env-isolation change artifacts` (HEAD)
**Archived path**: `openspec/changes/archive/2026-09-14-fix-hf-token-env-isolation/`

## Summary

**Root cause.** `_get_hf_token()`'s `.env` helper called `load_dotenv(override=False)`, which assigns every `.env` key into the **real `os.environ`** and records no undo. pytest's `monkeypatch.delenv(name, raising=False)` on a key that was *absent at setup* records nothing, so the injected `HF_TOKEN` survived the test and leaked into later tests in the same process — the #176 amplifier.

**Fix.** Resolution now reads the `.env` with `dotenv_values` and **never writes `os.environ`**; precedence is decided by **key presence in `os.environ`, not value truthiness**. The guard `test_dotenv_call_leaves_environ_unchanged` was proven **RED before** the fix (`Left contains 2 more items: {'HF_HUB_DISABLE_IMPLICIT_TOKEN': 'true', 'HF_TOKEN': 'from-dotenv'}`) and green after, and is non-tautological thanks to the decoy `.env` key.

## Artifacts read

`proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `specs/process-boundary/spec.md`, `openspec/config.yaml`; canonical target `openspec/specs/process-boundary/spec.md`. No `sync-report.md` exists for this change.

## Archive preconditions / final task gate

- The verify report is present and clearly passing (no `FAIL`, `BLOCKED`, `CRITICAL` or verification blocker).
- The persisted `tasks.md` was re-read immediately before the sync and the move: **11 `- [x]`, zero `- [ ]`** → no stale-checkbox reconciliation was needed and none was performed; no checkbox was re-added to the archived `tasks.md`.
- `sync-report.md` is absent → the archive-time sync fallback ran under the parent prompt's **explicit approval**.
- Destructive merge guard: **ADDED only** — no `MODIFIED`, `REMOVED` or `RENAMED`; nothing was replaced or deleted.

## Canonical sync

| Domain spec | Delta | Operation | `git diff --numstat` |
| --- | --- | --- | --- |
| `openspec/specs/process-boundary/spec.md` | PB-13 | ADDED → appended after PB-12 (the last requirement) | 38 insertions / 1 deletion |

- **PB-13** *"Side-effect-free HF token resolution and cross-test env hermeticity"* was appended directly after PB-12 with the provenance line ``> Added by change `2026-09-14-fix-hf-token-env-isolation` (issue #176).``, matching this file's addition-marker style.
- **The single "deletion" is the EOF-newline artifact, not a content deletion.** The pre-existing last line (*"THEN zero matches SHALL be found outside `openspec/changes/archive/**` historical prose"*) carried no trailing newline; appending necessarily terminates it, so git records that byte-identical line as removed and re-added. Verified byte-for-byte: the new file equals the `HEAD` content (with its one EOF newline added) plus the PB-13 block. Every pre-existing requirement keeps its text verbatim — PB-01…PB-12 are untouched, and nothing was replaced.
- Requirements in the canonical spec after sync: **13** (PB-01…PB-13); exactly one `(PB-13)` heading. PB-13 carries its five scenarios (S1–S5).
- Working-tree hygiene: the file was written with LF bytes matching `.gitattributes` (`* text=auto eol=lf`); no CRLF drift.
- Active same-domain change warnings: **none** — `sameDomainActiveChanges: []`; this change was the only non-archived folder, and after the move `openspec/changes/` holds no active change.

## Structured status / `actionContext`

- Native status: `artifactStore: openspec`, `applyState: all_done`, `taskProgress 11/11`, `dependencies.verify: all_done`, `archive: ready`, `nextRecommended: archive`, `blockedReasons: []`.
- `actionContext.mode: repo-local`; `workspaceRoot` = `allowedEditRoots` = `C:\Users\elaze\Desktop\sofer` — every write (canonical spec, archive move) stayed inside the authoritative workspace.

## Measured final state

- `uv run pytest tests/ -q` → **1781 passed, 6 skipped** (`test_exit_code: 0`).
- Coverage **TOTAL 93%** against the config-owned floor `fail_under = 90` (`pyproject.toml:98`; `branch = true` at `:93`).
- `bash scripts/check_core_coverage.sh` → **exit 0** with `cli.py`, `scanner.py`, `prepare.py`, `publish.py` each at **100%** and an empty `Missing` column (AGENTS.md rule 14).
- `uv run mypy src/`, `uv run ruff check`, `uv run ruff format --check` clean (`build_exit_code: 0`).
- Diff of the fix commit: **4 files, 113 insertions / 28 deletions** (`src/sofer/mcp_server.py` 41/26, `tests/test_mcp_server.py` 66/0, `README.md` 3/1, `README_ES.md` 3/1).

## Guaranteed contract and accepted narrowing

**Guaranteed (pinned):**

- An **exported-but-blank** value still wins over `.env`: `tests/test_mcp_server.py:3117` asserts `_get_hf_token() is None` with a blank present `HF_TOKEN` plus an alias and a `.env` entry — presence, not truthiness.
- The `HF_HUB_DISABLE_IMPLICIT_TOKEN` gate keeps `.env` visibility via the **merged view**, so a `.env`-only flag still skips the implicit file/Colab fallback (PB-13 S4); production resolution outcomes are unchanged.

**Accepted narrowing (explicit consequence, not a regression).** `.env`-only keys stop being visible to code that reads `os.environ` — `HF_TOKEN_PATH`, `HF_HOME`, `HF_OIDC_RESOURCE`, `HF_OIDC_ID_TOKEN`, and arbitrary keys. Concretely, `mcp_registration.collect_env()` no longer reports a token that lives **only** in `.env`. This is the **correct contract**: the server that `mcp add` configures is spawned by the agent host and inherits the host's *real* environment, never our in-process cwd `.env` read. No test, README contract, or spec row depends on the narrowing; a user-facing note is a follow-up.

## Reportable anomaly: runtime-ledger row (documented, maintainer-accepted)

A **probe payload** was submitted to `sdd-attempt settle`; the engine accepted and committed it, leaving a **fabricated row for attempt ordinal 1** (`evidence_revision: sha256:000…0`, `diagnosis: "probe"`, `cleanup_evidence`/`process_evidence: "probe"`, `changed_lines: 384` against the real 141 tracked lines). Two later honest settles short-circuited on the terminal objective and could not amend it. The maintainer explicitly chose to leave it **documented** rather than authorise the destructive `reset`, which the provider documents as *discarding the scope* instead of amending it.

**Impact: no evidence row in any artifact is affected.** The null `sha256:000…0` value appears nowhere in this archive or in any requirement, scenario, task, gate, design decision, or evidence row — only quoted as ledger content in `apply-progress.md` §12. The verification attempt settled honestly (ordinal 2, outcome `passed`, `changed_lines: 116`, `evidence_revision: sha256:9cae1a18…`, objective `complete`).

## Verify-phase cancellation and integrity confirmation

The verify phase was **cancelled accidentally** mid-flight. Rather than re-running it, the parent verified the resulting report's integrity: the envelope is bound to the current diff, `gentle-ai sdd-verify-validate` accepts it (exit 0), `test_output_hash`/`build_output_hash` each match the run's captured files, and the 26 captured files include the red-provenance and the D1 presence probe. The native engine then reported `verify: all_done` with `nextRecommended: archive`. Integrity confirmed → no re-run was performed.

## Out of scope

- Issue **#207**: the five `TestHfTokenFallback` cases that fail when a repository-root `.env` exists (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`) and the ambient-`HF_TOKEN` brittleness are a **different defect with a different cause** (the suite depending on the developer's cwd `.env`). Correctly left open and untouched.
- **Pre-existing static findings, not regressions.** `import tomli as _tomli` (L687), `with open(path, "rb")` (L690), and the `_SERVER_ROOT`/`_APPROVAL_PHRASE`/`_PHRASE_SOURCE`/`_SERVER_PROCESS_ID`/`_SERVER_STARTED_AT`/`_SERVER_VERSION` redefinitions in `src/sofer/mcp_server.py` are byte-identical on unmodified `HEAD`; no diff hunk intersects them, and the authoritative `uv run mypy src/` and `uv run ruff check` gates are clean.

## Delivery / workload

Diff **141 tracked lines < 400** review budget; single PR, no chaining, no `size:exception`. The change directory moved wholesale into the archive with every artifact preserved. The parent owns the commit; no commit, push, PR, or tag was created here.

## Blockers

None.
