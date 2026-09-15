# Design: fix-hf-token-env-isolation

**Change** `2026-09-14-fix-hf-token-env-isolation` (issue #176) · branch `fix/176-hf-token-test-isolation` — verified this phase: `.git/HEAD` → `ref: refs/heads/fix/176-hf-token-test-isolation` · store **hybrid** (this file + Engram `sdd/2026-09-14-fix-hf-token-env-isolation/design`) · delivery `ask-on-risk`, 400-line budget (change ≈90 lines).
**Read this phase**: `proposal.md`; delta `specs/process-boundary/spec.md` (PB-13, S1–S5); `src/sofer/mcp_server.py:747-812`; `src/sofer/mcp_registration.py:450-461`; `tests/test_mcp_server.py:3056-3181`; `README.md:658`, `README_ES.md:692`; installed `python-dotenv` 1.2.2 and `huggingface_hub`.
**Fix is settled** (maintainer's choice, not re-opened): `_get_hf_token()` stops writing `os.environ`; `.env` is read with `dotenv_values` and consulted as a value fallback. `_load_dotenv_if_available` (`:747-765`) writes today at `:762-763` (`dotenv/main.py:105-108`); the disable check is at **`:806`** — the request cited `:805`; verified `:806`, cited as such below.
**Also settled**: an **exported** `HF_TOKEN` still makes the victim fail — that is issue #207's class, not this change's. Nothing here is designed to tolerate ambient credentials.

## D1 — Merged view: the environment wins by key PRESENCE, never by value truthiness

```python
def _read_dotenv_values() -> dict[str, str]:
    """Return the `.env` view WITHOUT touching `os.environ` (`{}` when dotenv is absent/disabled).

    Parity with the `load_dotenv(override=False)` used until now: the cwd `.env` wins, the default
    search fills the rest, a key with no value contributes nothing (dotenv/main.py:107), and a
    truthy `PYTHON_DOTENV_DISABLED` disables the read (dotenv/main.py:405-410).
    """
    try:
        from pathlib import Path

        from dotenv import dotenv_values
    except ImportError:
        return {}
    if _is_truthy_env("PYTHON_DOTENV_DISABLED", {}):
        return {}
    values: dict[str, str] = {}
    for path in (Path.cwd() / ".env", None):
        parsed = dotenv_values(dotenv_path=path) if path else dotenv_values()
        for key, value in parsed.items():
            if value is not None and key not in values:
                values[key] = value
    return values


def _merged_env(name: str, dotenv: Mapping[str, str]) -> str:
    """Environment value for *name* by PRESENCE, else its `.env` value, else ``""``."""
    if name in os.environ:  # presence — NOT `os.environ.get(name) or dotenv.get(name)`
        return os.environ[name]
    return dotenv.get(name, "")
```

Each token name is resolved as `_clean_token(_merged_env(name, dotenv))`.

- Why `in os.environ`: `load_dotenv(override=False)` skips a key merely *present* (`dotenv/main.py:105`). `tests/test_mcp_server.py:3117` pins the consequence — with `HF_TOKEN` present-but-blank and an alias set, resolution is `None`; a `.env` value must never be substituted for the blank present key (S2).
- **Failure mode of the alternatives**: `os.environ.get(name) or dotenv.get(name)` (value truthiness) silently falls through to `.env` whenever the exported value is blank, so production would publish with a token the operator explicitly blanked. `dotenv`-first precedence breaks `tests/test_mcp_server.py:3166` and `:3117` and ignores the shell. Both are one-token-away mistakes; hence one expression, one grep item (D7).
- `_is_truthy_env(name, dotenv)` gains the merged view as a **required** argument (its only caller is `:806`), so no call site can silently read `os.environ` alone; `PYTHON_DOTENV_DISABLED` is passed `{}` (`load_dotenv`'s own gate is environment-only).
- Equivalence spot-checks: `.env` `HF_TOKEN=` → `""` → `_clean_token` → `None` → chain continues (as today); a bare `HF_TOKEN` line contributes nothing (as today, `dotenv/main.py:107`); interpolation defaults match (`dotenv/main.py:383` vs `:432`).

## D2 — Every other reader of the merged view (decided explicitly)

| Reader | Today | After the fix |
|---|---|---|
| `HF_HUB_DISABLE_IMPLICIT_TOKEN`, sofer's gate at `:806` | visible from `.env` (the load injected it) | **preserved** — the gate consults the merged view; a `.env`-only flag still returns `None` (PB-13 S4) |
| `HF_OIDC_RESOURCE` / `HF_OIDC_ID_TOKEN` — `huggingface_hub` reads `os.environ` at call time (`utils/_auth.py:181`) | visible from `.env` | **no longer visible**; a `.env`-only OIDC resource stops enabling the OIDC path |
| `HF_TOKEN_PATH` / `HF_HOME` — snapshotted by `huggingface_hub.constants` at import (`constants.py:246-253`), and `get_token` is imported lazily at `mcp_server.py:807`, i.e. *after* today's injection | visible from `.env` in the cold-import case — which is the real server process | **no longer visible** |
| Any other `.env` key (HF or not) | injected into the process | **no longer visible** |

**Decision.** (a) The disable gate is re-plumbed onto the merged view — mandatory per the delta: dropping it would silently re-enable the implicit file fallback in a shipped path. (b) The remaining rows are an **accepted, documented narrowing**. Keeping them would require writing `os.environ` again (re-introducing the defect) or coupling to `huggingface_hub` internals; neither is acceptable, and nothing depends on them: the only `.env` fixtures in the suite are `tests/test_mcp_server.py:3156` and `:3173` (both `HF_TOKEN=` only), and the file-fallback cases (`test_file_fallback_when_env_absent` `:3085`, `test_hf_hub_disable_skips_file` `:3119`) set `hf_constants.HF_TOKEN_PATH` directly, never via `.env`. README's `.env` clause promises `.env` support for token *resolution* only, so it stays truthful; a user-facing note about the narrowing is a follow-up, not scope here.
`SOFER_MCP_APPROVAL_PHRASE` is unaffected either way: `_resolve_approval_phrase` reads the environment once at `build_server` (`:3125`), before any token resolution, so `.env` never fed it.

## D3 — Resolution order (reviewer checklist, one line per step)

1. Build the `.env` view once per call (cwd `.env` → default search → `{}` when `python-dotenv` is absent or `PYTHON_DOTENV_DISABLED` is truthy). Never writes.
2. `HF_TOKEN` → merged view → `_clean_token`; return when non-`None`.
3. `HF_HUB_TOKEN` → same.
4. `HUGGING_FACE_HUB_TOKEN` → same.
5. `_is_truthy_env("HF_HUB_DISABLE_IMPLICIT_TOKEN", dotenv)` → return `None`. **Same position as today (`:806`)**: after the three names, before the file fallback.
6. `huggingface_hub.get_token()` (OIDC → env → token file → Colab; `utils/_auth.py:79-84`) → `_clean_token`; `ImportError` → `None`; OIDC errors still propagate.
The blank/whitespace rule is applied by `_clean_token` at every step and never aborts the chain; presence decides env-vs-`.env` only (D1).

## D4 — The S1 guard test: location, name, shape, red-before-green, non-tautology

`tests/test_mcp_server.py`, class `TestHfTokenFallback` (`:3056`), new case **`test_dotenv_call_leaves_environ_unchanged`** (literal name for reviewer grep):

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

- **RED before the fix**: today `:762-763` writes *both* `.env` lines into the process environment, so the second assertion fails. `apply` records that failing run **before** touching `src/`, then the green run after — that pair is the red-then-green evidence.
- **Not tautological**: (i) it asserts the resolved *value* too, so deleting `.env` support fails the first assertion; (ii) the snapshot is taken after setup and before the call — taking it after the call (or asserting only `"HF_TOKEN" not in os.environ` against a key deleted in the same test) would compare the environment to itself; (iii) the second `.env` key has no bearing on the returned token yet must still not appear, so an ambient `HF_TOKEN` (the #207 class) cannot make it vacuous: `load_dotenv(override=False)` would skip that one name but still inject the flag.
- The write→restore loophole is closed by review, not a second static test: the delta says "SHALL NOT write", and D7 item 1 greps for it.

## D5 — Two contract consequences, stated plainly

**(a) The flag keeps `.env` visibility** (D2a), pinned by a new test (S4): `.env` holds `HF_HUB_DISABLE_IMPLICIT_TOKEN=true`, no token in the environment or `.env`, a valid token file configured → `_get_hf_token() is None`. Existing coverage of the gate (`tests/test_mcp_server.py:3119`) sets it via `monkeypatch.setenv` only; no existing test puts the flag in `.env`, so the new case is the only evidence for this row.
**(b) `sofer mcp add` stops reporting a `.env`-only token.** `mcp_registration.collect_env()` (`:450-461`) reads `os.environ` only. This is the **correct contract, not an accidental regression**: the server `mcp add` configures is spawned by the agent host and inherits the host's *real* environment (plus the host's own `.env` handling), so our in-process read of the cwd `.env` was never the right source for an env NAME list. No `mcp-registration` requirement changes and no `TestEnvForwarding` case moves.

## D6 — Documentation sync: literal replacement wording (rule 13, both files, one change)

`README.md:658` — replace the line (re-wrapping the adjacent sentence is allowed; this wording is the content of record):

- old: `.env` support (`load_dotenv(override=False)`); `HF_HUB_DISABLE_IMPLICIT_TOKEN`
- new: `.env` support read without mutating the process environment / (`dotenv_values`; a name present in the environment wins even when blank); / `HF_HUB_DISABLE_IMPLICIT_TOKEN` (as three wrapped lines)

`README_ES.md:692` — mirrored; technical tokens stay English, prose Spanish:

- old: soporte `.env` (`load_dotenv(override=False)`); `HF_HUB_DISABLE_IMPLICIT_TOKEN`
- new: soporte `.env` leído sin mutar el entorno del proceso / (`dotenv_values`; un nombre presente en el entorno gana aunque esté en blanco); / `HF_HUB_DISABLE_IMPLICIT_TOKEN`

No other README line changes: the surrounding sentence names `HF_TOKEN_PATH` / `HF_OIDC_RESOURCE` as mechanisms of `huggingface_hub.get_token()` for *exported* variables, which is unchanged and still true. No heading or section changes, so rule 13's mirror check is unaffected.

## D7 — Blast radius, rollback, verification, gates

**Files.** `src/sofer/mcp_server.py` (~25 lines: `_load_dotenv_if_available` → `_read_dotenv_values` + `_merged_env`; `_is_truthy_env` gains the mapping argument; `_get_hf_token` body and docstrings). The old helper name has no other caller and no test imports it — `grep -rn "_load_dotenv_if_available" src tests` → `mcp_server.py:747`, `:801` only. `tests/test_mcp_server.py` (~40 lines: S1 guard, S2 blank-presence-vs-`.env`, S4 `.env`-only flag; optionally a `PYTHON_DOTENV_DISABLED` case). `README.md:658`, `README_ES.md:692`. **Untouched**: `mcp_registration.py`, `tests/test_mcp_registration.py`, `.env.template`, `openspec/specs/**`, `proposal.md`, `tasks.md`, `pyproject.toml`.

**Reviewer must check.** `grep -n "os.environ\[" src/sofer/mcp_server.py` → no hits; `grep -n "load_dotenv(" src/sofer/mcp_server.py` → no hits (only `dotenv_values`); the merge uses `in os.environ`, not `or`; `_is_truthy_env` is called with the mapping at `:806`; docstrings say `dotenv_values` / no mutation (rule 2); the import stays inside the pre-existing `try/ImportError`, so an absent or older `python-dotenv` degrades exactly as today; both READMEs carry identical technical tokens; no behaviour change beyond D2a/D2b.

**Rollback.** Single-commit revert of this branch's change — no migration, no persisted state, no config surface. Reverting restores the unrecorded `os.environ` write and the README text together.

**Evidence set** (one command per item; `apply` records the actual output):
1. Red-then-green for S1: `uv run pytest tests/test_mcp_server.py -k leaves_environ_unchanged -q` → **1 failed** on the pre-fix tree (recorded before editing `src/`), **1 passed** after.
2. `uv run pytest tests/test_mcp_server.py::TestHfTokenFallback -q` → green, including `:3117` (blank env does not fall through to `.env`) and `:3181` (`== "from-dotenv"`).
3. Both orders of the two-test-id reproduction, no ambient token: `uv run pytest tests/test_mcp_server.py::TestHfTokenFallback::test_dotenv_loads_when_env_absent "tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array" -q`, then reversed → both green, no `.bak`.
4. `uv run pytest tests/ -q` → green, with the tally **re-derived** (AGENTS.md's 1766/6 is stale by construction — three new tests; never quote it as the result).
5. `uv run mypy src/` clean; `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/` clean.
6. `README.md`/`README_ES.md` diff is exactly the D6 lines, in both files.
7. No temp or orphan file left inside the repo (precedent: a stray `.pi-spec-linecount.tmp`); scratch outside the repo only.

**Gates — confirmed.** `src/sofer/mcp_server.py` has **no per-file coverage floor**: it is in neither COV-06 (`cli`/`scanner`/`prepare`/`publish`, AGENTS.md rule 14) nor COV-01 (`profile`/`mcp_registration`/`verification`), so only the config-owned TOTAL gate applies (`fail_under = 90`, `pyproject.toml:98`; `ci` CI-01 / `coverage` COV-02). No 100% row is promised and no pragma is needed. `dotenv_values` exists at the declared floor `python-dotenv>=1.0.0` (`pyproject.toml:26`; resolved 1.2.2 `uv.lock:1620-1622`; installed `dotenv/main.py:432`), and the call sits inside the existing `ImportError` guard — so even an install without it degrades to "no `.env` support" exactly as before, making the floor safety-moot.

## Out of scope (must not be folded in)

The five `TestHfTokenFallback` cases broken by a repository-root `.env` (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`) stay failing: different cause (the suite depending on the developer's cwd `.env`), tracked as **#207** — this change removes the global write but still consults the cwd `.env`. An exported `HF_TOKEN` still fails the victim (`collect_env()` reports it) — also #207's class. No `pytest-randomly` or ordering plugin, no test renamed/reordered/skipped, no commit, push or PR in this phase.

## Risks

| Risk | Mitigation |
|---|---|
| The merge is written by value truthiness (`or`) → production uses a token the operator blanked | D1 fixes one expression; S2's new test asserts the alias token, not merely "not `from-dotenv`"; D7 grep item |
| Users relying on `.env`-carried `HF_TOKEN_PATH` / `HF_OIDC_RESOURCE` / arbitrary keys see a narrowed `.env` | Accepted and documented here and in the delta as a stated consequence; no test, README contract or spec row depends on it; a user-facing note is a follow-up |
| S1 goes green for the wrong reason (ambient `HF_TOKEN`) | The second `.env` key makes the red signal unavoidable; snapshot after setup, before the call |
| The tally is copied from AGENTS.md instead of re-derived | D7 item 4 mandates re-derivation |
