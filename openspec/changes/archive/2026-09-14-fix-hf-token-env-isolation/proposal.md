# Proposal: fix-hf-token-env-isolation

**Change**: `2026-09-14-fix-hf-token-env-isolation` · **Issue**: #176 · **Branch**: `fix/176-hf-token-test-isolation` (verified: `.git/HEAD` → `ref: refs/heads/fix/176-hf-token-test-isolation`, cut from `dev` @ ff319ac)
**Status**: proposal complete — the maintainer already chose the fix; recorded here as a premise, not re-opened · **Store**: hybrid (this file + Engram `sdd/2026-09-14-fix-hf-token-env-isolation/proposal`) · **Delivery**: `ask-on-risk`, 400-line budget
**Size**: ~25 src + ~40 test + ~4 doc lines + one spec scenario (≈90 changed lines) · **Exploration**: none persisted under `sdd/…/explore`; the parent supplied the mechanism inline and every line reference was re-verified this phase.

## Intent

`_get_hf_token()` resolves a `.env` token by **writing it into `os.environ`** (`load_dotenv(..., override=False)`) instead of merely reading it — so the shipped MCP server is an unrecorded global writer and the test suite is non-hermetic. `TestHfTokenFallback::test_dotenv_loads_when_env_absent` (`tests/test_mcp_server.py:3168`) deletes an already-absent `HF_TOKEN` (`:3169`); on pytest 9.1.1 that records **no undo entry** (`_pytest/monkeypatch.py:300-304`, `delitem` has no `else`), so its call at `:3181` leaves `HF_TOKEN=from-dotenv` live for every later test. Fix the root cause: read `.env` with `dotenv_values` and consult it as a fallback value, never mutating `os.environ`. This is a bug fix enforcing existing **PB-06**, not a new capability.

## Verified mechanism (re-checked on this branch)

| Fact | Evidence |
|---|---|
| Unrecorded mutation, on every resolution | `mcp_server.py:747-765` → `:762-763` `load_dotenv(dotenv_path=Path.cwd()/".env", override=False)` then `load_dotenv(override=False)`; `dotenv/main.py:105-108` writes `os.environ[k] = v` directly. Called at `:801`, the first statement of `_get_hf_token` (def `:790`) — there is **no** module-level "already loaded" flag. |
| Victim | `tests/test_mcp_registration.py:171` `TestMerge::test_codex_normalize_string_vs_array`: the leaked value adds `env_vars=["HF_TOKEN"]`, `merge` reports `changed=True`, a `.bak` appears (`cli.py:691` → `mcp_registration.py:450` → `:139` → `:464` → `:186` → `:211` → `:313`). |
| Ordering is *not* required, and neither is the plugin | `HF_TOKEN=hf_pre_set_in_shell uv run pytest "tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array" -q` fails standalone — the victim is brittle to the ambient environment, not only to ordering. `pytest-randomly` is not installed (only `anyio`), and default collection puts the victim before the leaker, so the issue's `-p no:randomly` is a no-op. |
| The two other candidate causes are ruled out | `grep -rn "autouse" tests/` → **0 hits**; `_load_dotenv_if_available` has no "already loaded" flag — it calls `load_dotenv` twice, unconditionally. |
| Re-arming amplifier | `tests/test_mcp_registration.py:560-577` `TestEnvForwarding::test_no_warning_without_env` deletes the now-*present* leaked key (that undo **is** recorded), so its `undo()` **restores** the poison value, leaving it live for every subsequent test. |

## Chosen fix — record it, do not re-open

Read `.env` without side effects — `dotenv_values(dotenv_path=Path.cwd()/".env")` then the default search — and consult those values **as a fallback inside** token resolution. Justification: it is the only option that removes the unrecorded global writer from *shipped* code, so it closes the class rather than an instance, and it neutralises the amplifier above for free, because nothing is leaked for it to restore. Rejected for *this* change: **(a)** a targeted save/restore in the leaking test — closes one instance; and a naive `monkeypatch.setenv("HF_TOKEN", "")` does **not** work (it makes `load_dotenv(override=False)` skip the key and breaks that test's own assertion), so a correct local fix needs an explicit snapshot in `try/finally`; **(b)** an autouse env snapshot/restore fixture in `tests/conftest.py` — test-only and class-closing, but it can mask future leaks and carries a finalizer-ordering trap. `dotenv_values` ships in the declared floor `python-dotenv>=1.0.0` (`pyproject.toml:26`); no shell tool exists in this phase, so `design`/`apply` confirm it by import.

## Contract the design must preserve — its central risk

`load_dotenv(override=False)` semantics must be replicated exactly, because existing tests depend on them; getting this wrong would silently change which token production uses, which is worse than the test defect:

- **Key-presence, not value-truthiness**: if a name is *present* in `os.environ`, the `.env` value for that name is never consulted — even when the env value is whitespace-only and `_clean_token` maps it to `None` (`tests/test_mcp_server.py:3117`). A value-truthiness fallback would silently merge the two namespaces.
- A **present, non-empty** env var wins over `.env`; `.env` supplies a value only when the environment does not; the HF token **file** fallback (`huggingface_hub.get_token()`) keeps its current position. `tests/test_mcp_server.py:3181` asserts `_get_hf_token() == "from-dotenv"` and must still hold.
- Every later `os.environ` read in resolution sees the same view as before — notably the `HF_HUB_DISABLE_IMPLICIT_TOKEN` truthy check (`:805`, via `_is_truthy_env` at `:768`), which today also observes `.env`.
- Consequence for `design` to state, not to fix here: `mcp_registration.collect_env()` (`:450`) reads `os.environ` only, so a token living *only* in `.env` stops being reported as a forwarding var by `sofer mcp add` — the correct contract, since a spawned server inherits the real environment, not our in-process read.

## Scope

1. `src/sofer/mcp_server.py` — `_load_dotenv_if_available`/`_get_hf_token` stop mutating `os.environ`; docstrings and the documented mechanism stay truthful (rule 2).
2. Alignment of the documented contract: `README.md:658` and `README_ES.md:692` — both describe `.env` support as `load_dotenv(override=False)`; both updated in the same change and mirrored (rule 13), since the mechanism changes even though user-visible behaviour should not.
3. Tests — existing assertions keep passing, **plus** a new guard asserting that calling `_get_hf_token()` with a `.env` present leaves `os.environ` unchanged. That guard is what converts "remember not to mutate globals" from discipline into a gate.
4. Gates — `mcp_server.py` is **not** a COV-06 module (cli/scanner/prepare/publish) nor a COV-01 floor module (profile/mcp_registration/verification): it has **no per-file floor** and is governed only by the config-owned TOTAL gate (`fail_under = 90`, COV-02/CI-01). Do not promise a 100% row. `uv run mypy src/` and `ruff` stay clean.

## Non-goals

- **Do not touch the five `TestHfTokenFallback` cases broken by a repository-root `.env`** (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`). That is a **different defect with a different cause** — the suite depending on the developer's cwd `.env` — now tracked as **#207**. This change removes the global mutation but still consults the cwd `.env`, so those failures remain and must not be silently folded in here.
- No change to `mcp_registration.py` or the victim's assertion; no rename, reorder or skip of any test; no `pytest-randomly` or any ordering plugin; no change to `.env.template`.
- Do not modify `openspec/specs/**` (canonical sync happens at archive time), `openspec/changes/archive/**`, or `openspec/changes/2026-09-14-chore-python-version-313/`. No commit, push or PR.

## Spec framing

The governing requirement already exists: **PB-06 "Deterministic and offline"** (`openspec/specs/process-boundary/spec.md:184-198`), scenario *"No credentials required"* (`:194-198`) — GIVEN `HF_TOKEN` absent / WHEN the suite runs / THEN it SHALL pass without credential-dependent skips or failures. So this is a bug fix enforcing an existing requirement. A small **ADDED** clause is still expected, because the provider requires a `specs` artifact before `apply`; the honest new property is **cross-test env hermeticity** — a test SHALL NOT leave the process environment mutated — which PB-06 does not currently state explicitly. No broader capability is invented.

## Affected areas

| Area | Impact | Description |
|---|---|---|
| `src/sofer/mcp_server.py` | ~25 lines | `dotenv_values` read; no `os.environ` write; docstrings |
| `tests/test_mcp_server.py` | ~40 lines | `TestHfTokenFallback` green + new no-mutation guard |
| `README.md`, `README_ES.md` | ~2 lines each | `.env` mechanism text (rule 13) |
| this change's `specs/process-boundary/spec.md` | one scenario | Delta only; canonical sync at archive time |
| `tests/test_mcp_registration.py`, `mcp_registration.py`, `.env.template` | None | Untouched |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Precedence subtly changed (key-presence vs value-truthiness) → production resolves a different token | Med | Stated above as the binding rule; existing `TestHfTokenFallback` cases plus a new precedence test pin it; `design` treats it as the central decision |
| The `.env`-only token is no longer reported by `mcp add` env forwarding | Low | Correct contract (a spawned server inherits the real env); recorded for `design`; `TestEnvForwarding` cases unchanged |
| The new guard is a tautology (asserts nothing about `.env`, or is written after the fix) | Low | It must assert `os.environ` equality across a `.env`-present call and be red before the source change |
| `dotenv_values` assumed, unverified this phase | Low | Ships in the declared floor `python-dotenv>=1.0.0`; `apply` confirms by import and runs the suite |

## Rollback

Plain revert of one branch's commits — no migration, no persisted state, no config surface. Afterwards the unrecorded global write returns and the suite is env-dependent exactly as today; the README text reverts with it.

## Success criteria

- [ ] With a `.env` present, `_get_hf_token()` returns the `.env` value and `os.environ` is **unchanged** — the new guard, red before the fix.
- [ ] `tests/test_mcp_server.py:3181` still asserts `_get_hf_token() == "from-dotenv"`; every `TestHfTokenFallback` case passes, including whitespace-only-env precedence.
- [ ] With **no ambient token set**, the victim at `tests/test_mcp_registration.py:171` passes **standalone** and in both orders — the leaker no longer poisons the process, and `-p no:randomly` is never required. **Correction (parent, after the spec phase):** this bullet previously read *"With `HF_TOKEN=hf_pre_set_in_shell`, the victim … passes standalone"*, which is **false** and contradicted this file's own mechanism table above (row *"Ordering is not required"*). An exported `HF_TOKEN` still makes the victim fail, because `collect_env()` reports any exported value and the merge then rewrites the entry — hardening the victim against an ambient environment was option (d), which was **not** chosen in favour of the root fix. That remaining brittleness is the same class as issue **#207** (the suite depending on the developer's ambient credentials) and is recorded there rather than silently absorbed here.
- [ ] `uv run pytest tests/ -q` green; `uv run mypy src/` and `uv run ruff check src/ tests/` clean; `README.md`/`README_ES.md` synced (rule 13); no 100% row promised for `mcp_server.py`; the five #207 failures remain untouched.

## Review workload & question round

≈90 changed lines across 4 files — a single PR, no chaining, no `size:exception`. The question round is already closed: the maintainer chose the code-level fix and it is recorded above as a premise, not re-offered as an option. The one product-shaped consequence worth a user's eye is the `.env`-only token no longer appearing in `sofer mcp add` env forwarding; if that behaviour must be preserved, it is a separate follow-up, not a second round here.
