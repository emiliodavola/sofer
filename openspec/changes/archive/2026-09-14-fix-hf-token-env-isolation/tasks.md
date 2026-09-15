# Tasks: fix-hf-token-env-isolation

**Change** `2026-09-14-fix-hf-token-env-isolation` · **Issue** #176 · **Branch** `fix/176-hf-token-test-isolation` (verified: `.git/HEAD` → `ref: refs/heads/fix/176-hf-token-test-isolation`) · **Store** hybrid (this file + Engram `sdd/2026-09-14-fix-hf-token-env-isolation/tasks`) · **Delivery** `ask-on-risk`, 400-line budget.
**Inputs**: `proposal.md` (fix settled by the maintainer; success criterion 3 corrected by the parent), the PB-13 delta `specs/process-boundary/spec.md` (S1–S5 + rule-6 mapping), `design.md` (D1–D7), `openspec/config.yaml` (`strict_tdd: false`; `uv run pytest tests/ -q`; TOTAL floor 90).
**Chosen root fix**: `_get_hf_token()` stops writing `os.environ` — `src/sofer/mcp_server.py:747-765` drops `load_dotenv(override=False)` (`:762-763`) for a `dotenv_values` read consulted as a **value fallback**, with precedence decided by **key presence** (D1); the `HF_HUB_DISABLE_IMPLICIT_TOKEN` gate at `:806` is re-plumbed onto the merged view (D2a), so no production resolution outcome changes.
**Accepted cost (D2b — documented consequence, not a regression)**: `HF_TOKEN_PATH`, `HF_HOME`, `HF_OIDC_RESOURCE`, `HF_OIDC_ID_TOKEN` and arbitrary `.env` keys stop being visible to code reading `os.environ`, so `mcp_registration.collect_env()` (`:450-461`) stops reporting a `.env`-only token — correct, since a spawned server inherits the real host environment.

## Review Workload Forecast

| Field | Value |
| ----- | ----- |
| Estimated changed lines | ~90 (≈25 `mcp_server.py` + ≈40 `tests/test_mcp_server.py` + 4 READMEs) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

### Suggested Work Units

| Unit | Goal | Boundaries (start → finish · verify · rollback) |
| ---- | ---- | ---------------------------------------------- |
| WU-1 RED | Guard test exists and is red | `TestHfTokenFallback` (`tests/test_mcp_server.py:3056`) → `-k leaves_environ_unchanged` is **1 failed** · red output recorded before any `src/` edit · revert the test file |
| WU-2 GREEN + TRIANGULATE | S1–S5 green, no env write | `_read_dotenv_values`/`_merged_env` + `:806` re-wire (`src/sofer/mcp_server.py:747-807`) → new S2/S4 cases · `TestHfTokenFallback` green, greps clean · revert `mcp_server.py` + new tests |
| WU-3 docs | D6 wording in both READMEs | `README.md:658` → `README_ES.md:692` mirrored · diff is exactly the D6 lines · revert both lines |

## Apply tasks (apply phase only — these 11 checkboxes are the entire checklist)

### RED — guard test first, before any `src/` edit (D4)

- [x] 1.1 Add `test_dotenv_call_leaves_environ_unchanged` to `TestHfTokenFallback` (`tests/test_mcp_server.py:3056`) using D4's code verbatim (below) — it snapshots `dict(os.environ)` **after** setup and **before** the call and asserts both the resolved value and full snapshot equality. Evidence: `uv run pytest tests/test_mcp_server.py -k leaves_environ_unchanged --collect-only -q` collects exactly 1 test. Do not edit `src/` before 1.2. <!-- sdd-owner: implementation -->

```python
def test_dotenv_call_leaves_environ_unchanged(self, tmp_path, monkeypatch, restore_tool_config):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HF_HUB_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    monkeypatch.delenv("HF_HUB_DISABLE_IMPLICIT_TOKEN", raising=False)
    (tmp_path / ".env").write_text(
        "HF_TOKEN=from-dotenv\nHF_HUB_DISABLE_IMPLICIT_TOKEN=true\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    import huggingface_hub.constants as hf_constants

    monkeypatch.setattr(hf_constants, "HF_TOKEN_PATH", str(tmp_path / "no-token"))
    from sofer.mcp_server import _get_hf_token

    before = dict(os.environ)  # snapshot AFTER setup, BEFORE the call
    assert _get_hf_token() == "from-dotenv"
    assert dict(os.environ) == before
```

- [x] 1.2 Prove S1 is genuinely RED against the current code, still before any `src/` edit: `uv run pytest tests/test_mcp_server.py -k leaves_environ_unchanged -q` → **1 failed** (today `:762-763` injects both `.env` lines; not tautological, since the second `.env` key must also stay out). Evidence: the failing output captured pre-`src/`, so red→green provenance is recorded rather than claimed. <!-- sdd-owner: implementation -->

### GREEN — side-effect-free resolution (D1, D2, D3)

- [x] 2.1 In `src/sofer/mcp_server.py:747-765` replace `_load_dotenv_if_available` with `_read_dotenv_values` + `_merged_env` from D1, keeping the import inside the pre-existing `try/ImportError` and the `PYTHON_DOTENV_DISABLED` short-circuit; the presence expression is literal — `if name in os.environ: return os.environ[name]` then `return dotenv.get(name, "")` — never `os.environ.get(name) or dotenv.get(name)`. Docstrings state `dotenv_values` / no mutation (rule 2). Evidence: `grep -rn "_load_dotenv_if_available" src tests` → no hits. <!-- sdd-owner: implementation -->
- [x] 2.2 Make `_is_truthy_env(name, dotenv)` take the mapping as a **required** argument and pass the merged view at the `:806` gate, so a `.env`-only `HF_HUB_DISABLE_IMPLICIT_TOKEN` still returns `None` (D2a/D5a) and no call site can silently read `os.environ` alone. <!-- sdd-owner: implementation -->
- [x] 2.3 Rewrite `_get_hf_token`'s body and docstring to D3's step order: the `.env` view built once per call; `HF_TOKEN` → `HF_HUB_TOKEN` → `HUGGING_FACE_HUB_TOKEN`, each via `_merged_env` + `_clean_token`; then the flag gate; then `huggingface_hub.get_token()` (file/OIDC/Colab), whose position and `ImportError` → `None` behaviour stay unchanged. <!-- sdd-owner: implementation -->
- [x] 2.4 Prove the fix — S1 green plus source greps (D7): `uv run pytest tests/test_mcp_server.py -k leaves_environ_unchanged -q` → **1 passed** (paired in the report with 1.1's red run); `grep -n "os.environ\[" src/sofer/mcp_server.py` → no hits; `grep -n "load_dotenv(" src/sofer/mcp_server.py` → no hits (only `dotenv_values`). Evidence: the green run and both greps pasted into the apply report. <!-- sdd-owner: implementation -->

### TRIANGULATE — the scenario tests (PB-13 S2, S4, and the S3/S5 pins)

- [x] 3.1 Add the S2 test: `.env` with `HF_TOKEN=from-dotenv`, a **present but whitespace-only** `HF_TOKEN` in the environment and `HF_HUB_TOKEN=alias-token` → `_get_hf_token() == "alias-token"` (assert the alias itself, never merely "not `from-dotenv`") — key presence, not value truthiness. <!-- sdd-owner: implementation -->
- [x] 3.2 Add the S4 test: `HF_HUB_DISABLE_IMPLICIT_TOKEN=true` present **only** in `.env`, no token in the environment or `.env`, a valid token file configured → `_get_hf_token() is None` (existing `:3119` covers the flag only via `monkeypatch.setenv`). <!-- sdd-owner: implementation -->
- [x] 3.3 Confirm the S3/S5 pins: `tests/test_mcp_server.py:3117` (blank present env does not fall through) and `:3181` (`== "from-dotenv"`) still hold, `TestHfTokenFallback` is fully green, and both orders of `TestHfTokenFallback::test_dotenv_loads_when_env_absent` + `tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array` pass with no ambient token and no `.bak` created — victim standalone too. Optionally add the `PYTHON_DOTENV_DISABLED` truthy case (`.env` view → `{}`, D1) or record the decision not to. Evidence: both order outputs, the standalone run, and the optional-case note. <!-- sdd-owner: implementation -->

### DOCS + EVIDENCE — D6 wording and the apply-owned verification run

- [x] 4.1 `README.md:658` and `README_ES.md:692` — apply D6's literal replacement (`.env` read without mutating the process environment; `dotenv_values`; a name present in the environment wins even when blank), Spanish prose in the ES file with technical tokens kept English; change no other line and no heading (rule 13). Evidence: both diffs show only these lines, mirrored. <!-- sdd-owner: implementation -->
- [x] 5.1 Re-derive the suite tally (never quote AGENTS.md's `1766 / 6`): `uv run pytest tests/ -q` green, plus `uv run coverage run -m pytest` with TOTAL ≥ 90 — **no per-file floor is claimed for `mcp_server.py`** (in neither COV-06 cli/scanner/prepare/publish nor COV-01 profile/mcp_registration/verification); `uv run mypy src/`, `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/` all clean. Evidence: pasted tallies, the coverage TOTAL row, the three clean commands, and no temp file left inside the repo. <!-- sdd-owner: implementation -->

## Verify gates — owner: verify phase (no checkboxes by design; verify owns these)

- Trace PB-13 S1–S5 to the evidence rows and re-check the rule-6 mapping table in `specs/process-boundary/spec.md`.
- Re-run `uv run pytest tests/ -q` against a re-derived baseline, `uv run mypy src/`, `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/`, and the coverage TOTAL row; confirm no per-file coverage floor was promised for `src/sofer/mcp_server.py`, no pragma was added, and the five untouched #207 lines (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`) sit with `mcp_registration.py`, `.env.template`, `pyproject.toml` and every workflow unmodified.

## Parent-owned lifecycle (no checkboxes by design; parent owns these)

- Bounded review of the apply diff: S1's red provenance, D1's presence expression, D4's non-tautology, and the D2b narrowing being documented rather than silently absorbed.
- Archive: sync PB-13 into `openspec/specs/process-boundary/spec.md` at archive time.
- PR: open the PR from `fix/176-hf-token-test-isolation` into `dev` via `.github/PULL_REQUEST_TEMPLATE.md`, with the real evidence in the Verification section.

## Out of scope (do not fold in)

The five `TestHfTokenFallback` cases broken by a repository-root `.env` (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`) stay failing — a different cause (the suite depending on the developer's cwd `.env`), tracked as **#207**; this change removes the global write but still consults the cwd `.env`. We also do **not** make the victim tolerate an exported `HF_TOKEN`: `collect_env()` would still surface it, which is #207's class, and the parent corrected the proposal criterion that wrongly implied this change does so. Also excluded: any change to `mcp_registration.py`, `.env.template`, `pyproject.toml` or any workflow; renaming, reordering, skipping or xfailing any test; adding `pytest-randomly` or any ordering plugin; promising a per-file coverage floor for `mcp_server.py`; editing `proposal.md`, `design.md`, the PB-13 delta, `openspec/specs/**` or `openspec/changes/archive/**`; creating any temporary file inside the repository; and any commit, push or PR in this phase.

## Closing note

Strict TDD is disabled repo-wide, but D4 and the parent make the guard test's red→green pair the provenance of record, so 1.1–1.2 precede every `src/` edit and are not reorderable. The only checkboxes in this file are the 11 apply tasks above — every verify gate and lifecycle step carries none — so finishing apply leaves **zero unchecked items**, which is what unblocks the verify phase.
