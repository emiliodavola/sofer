# Tasks — `2026-10-16-fix-codex-home-resolution`

> **Change** `2026-10-16-fix-codex-home-resolution` · issue **#325** · branch
> `fix/325-codex-home-and-321-delegation` (from `fix/316-321-bug-chore-followups`).

| ID | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| CH-1 | Reproduce the resolution on the failing path | — | done | With `CODEX_HOME=/tmp/other-codex`, `resolve_config_path("codex", "user")` returned `C:\Users\elaze\.codex\config.toml` |
| CH-2 | RED tests: the override wins, the default survives, project scope ignores it | D1, D2 | done | `test_codex_env_dir_wins_over_home` failed on `home/.codex/config.toml`; the other two passed, which is what makes them guards rather than restatements |
| CH-3 | Declare `user_env_dir = "CODEX_HOME"` on the codex adapter, leaving `user_parts` alone | D1 | done | `src/sofer/mcp_registration.py`, with the comment tying it to `native_scope: False` (D4) |
| CH-4 | GREEN on the resolution surface | D3 | done | `uv run pytest tests/test_mcp_registration.py -k "resolve_config or UserConfigResolution"` → 22 passed, 2 skipped |
| CH-5 | Both READMEs name the override, as they already do for Pi and Hermes | — | done | `README.md:720` and `README_ES.md:756` (the per-agent table); `README.md:360` and `README_ES.md:372` (`--user-config`) now name both env-override agents |
| CH-6 | Full suite and the type gates | — | done | 2236 passed / 9 skipped on this revision; ruff, mypy and pyright clean via the pre-commit hooks |
| CH-7 | Archive report | — | done | this folder's `archive-report.md` — archived late, see its §8 |

## Explicit non-deliveries

- No spec delta (proposal §4): the resolution rule and the per-agent table are unchanged, and nine
  archived changes set the precedent for a change that alters adapter data only.
- Codex's project-scope resolution is untouched and now pinned by a test instead of implied.
- Codex's own behaviour is not re-derived from its sources; if `mcp_registration.py:127` is wrong, that
  assertion is the bug and this change is a no-op.
