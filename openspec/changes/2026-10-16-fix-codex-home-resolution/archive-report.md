# Archive report — `2026-10-16-fix-codex-home-resolution`

> **Change** `2026-10-16-fix-codex-home-resolution` · issue **#325** · branch
> `fix/325-codex-home-and-321-delegation` (from `fix/316-321-bug-chore-followups`) · store **hybrid**.
>
> **Status:** implementation complete; archived inside the delivering PR (AGENTS.md rule 15).

---

## 1. What landed

| File | Change |
| --- | --- |
| `src/sofer/mcp_registration.py` | `ADAPTERS["codex"]["user_env_dir"] = "CODEX_HOME"`. `user_parts` is deliberately unchanged (D1), and the field carries a comment tying it to `native_scope: False`, which is `False` *because* those native commands act on the same global config. |
| `tests/test_mcp_registration.py` | three tests in `TestUserConfigResolution`: the override wins, the no-variable default survives, project scope ignores it. |
| `README.md`, `README_ES.md` | the per-agent table's codex user-scope row reads `$CODEX_HOME/config.toml` (default `~/.codex/config.toml`), the shape the Pi and Hermes rows already use; the `--user-config` row now names both env-override agents instead of only Pi. |
| `openspec/changes/2026-10-16-fix-codex-home-resolution/` | proposal, design, tasks, this report. **No `specs/` delta** — see §4. |

## 2. The defect, measured

`src/sofer/mcp_registration.py:127` documents that codex's native commands "always act on the global
`$CODEX_HOME` config". The adapter declared `user_env_dir: None`, so `resolve_config_path` never consulted
the variable:

| Probe | Before | After |
| --- | --- | --- |
| `CODEX_HOME` set, `resolve_config_path("codex", "user")` | `~/.codex/config.toml` | `$CODEX_HOME/config.toml` |
| `CODEX_HOME` absent (the documented default) | `~/.codex/config.toml` | `~/.codex/config.toml` (unchanged) |
| `resolve_config_path("codex", "project", proj)` with the variable set | `proj/.codex/config.toml` | `proj/.codex/config.toml` (unchanged) |

Before the fix, a user with `CODEX_HOME` pointing anywhere else got a successful command and a registration
codex never read — the #274 defect class, for the one host #274 did not cover.

## 3. What the issue's own proposal got wrong, and why a test exists because of it

The issue proposed changing **two** fields, including `user_parts: ("config.toml",)`. That would have
moved the *default* to `~/config.toml`: `resolve_config_path` joins only `user_parts[-1]` onto the
override, then falls back to the **full** `user_parts` when the variable is unset — which the adapter
contract states at `:110-111`.

So the correct change is one field, and `test_codex_default_survives_the_override_being_declared` exists
specifically as the guard for it: this change's most likely future edit is "clean up the redundant leading
path component", which would silently move every user's config. The wrong proposal is corrected on the
issue (`#325` comment), because it was published first and a reader could have implemented it.

## 4. Why there is no spec delta

The spec already requires this resolution order — `--user-config PATH`, then the adapter's `user_env_dir`
file, then `Path.home()` joined with `user_parts` (`openspec/specs/mcp-registration/spec.md:69-73`) — and
its per-agent table names only the file name (`:16`). The defect was that codex's adapter *data*
contradicted the contract its own field documents, so no clause changes; nine archived changes carry no
`specs/` delta, which is the precedent for a change that alters adapter data rather than a rule.

## 5. What this does not claim

- **Codex's own behaviour is not re-derived.** Whether codex honours `$CODEX_HOME` is not verified from
  codex's sources here; the repository asserts it at `:127`, and this change makes sofer agree with its own
  documented belief. If that assertion is wrong, this change is a no-op **and the assertion is the bug**.
- **Project scope is untouched**, and now pinned by a test rather than left implied.
- **#321 is not fixed here.** It is the next commit on this branch, and it *does* carry a spec delta,
  because it reverses a clause by name. It is also the reason this commit comes first: with the two
  resolvers disagreeing, "delegate then patch" would have written the entry in one file and the timeouts in
  another.

## 6. Task ledger

| ID | State | Evidence |
| --- | --- | --- |
| CH-1 | done | §2, before column |
| CH-2 | done | `test_codex_env_dir_wins_over_home` failed on `home/.codex/config.toml`; the other two passed, which is what makes them guards rather than restatements |
| CH-3 | done | §1, first row |
| CH-4 | done | 22 passed, 2 skipped on the resolution surface |
| CH-5 | done | `README.md:720`, `README_ES.md:756`, `README.md:360`, `README_ES.md:372` |
| CH-6 | done | §7 |
| CH-7 | done | this report |

## 7. Verification gates

| Gate | Result |
| --- | --- |
| `uv run pytest tests/ -q` | **2236 passed, 9 skipped** — the previous revision's 2233 plus the three tests this branch adds |
| The three new tests | RED before the fix (`test_codex_env_dir_wins_over_home` returned `home/.codex/config.toml`), GREEN after (22 passed, 2 skipped on the resolution surface) |
| `uv run ruff check` / `ruff format` | clean (pre-commit hooks on the commit) |
| `uv run mypy src/ scripts/` | clean (pre-commit hook) |
| `uv run pyright` | 0 errors (the 1 warning is the pre-existing `_tomli.py` one) |
