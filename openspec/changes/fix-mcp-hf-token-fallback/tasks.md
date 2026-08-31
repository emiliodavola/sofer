# Tasks: fix/mcp-hf-token-fallback

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180–280 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (fix/mcp-hf-token-fallback → dev) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Token fallback + publish wiring + tests + docs | PR 1 | Single PR to `dev`; all verification included |

## Phase 1: Foundation — Token Helpers

- [x] 1.1 Add `_load_dotenv_if_available()` in `src/sofer/mcp_server.py` — try `load_dotenv(override=False)` before env check, swallow `ImportError`
- [x] 1.2 Add `_is_truthy_env(name: str) -> bool` in `src/sofer/mcp_server.py` — check `{"1","true","yes","on"}` lowercased
- [x] 1.3 Add `_clean_token(t: str | None) -> str | None` in `src/sofer/mcp_server.py` — `replace("\r","").replace("\n","").strip() or None`

## Phase 2: Core Implementation — Fallback Chain & Publish Wiring

- [x] 2.1 Implement `_get_hf_token() -> str | None` in `src/sofer/mcp_server.py` — dotenv then cascade `HF_TOKEN`->`HF_HUB_TOKEN`->`HUGGING_FACE_HUB_TOKEN` via `_clean_token`, then `huggingface_hub.get_token()` (file/OIDC/Colab); gate file/Colab on `HF_HUB_DISABLE_IMPLICIT_TOKEN`, propagate `OIDCError`
- [x] 2.2 Refactor `_require_hf_token() -> str` in `src/sofer/mcp_server.py` to delegate to `_get_hf_token()` and raise `HFTokenError` with static message when `None`
- [x] 2.3 Add `token: str | None = None` param to `publish()` in `src/sofer/publish.py` — use `HfApi(token=token)` when given, else module `_api`
- [x] 2.4 Update `sofer_publish_confirm` in `src/sofer/mcp_server.py` to resolve token once via `_get_hf_token()` after quality gate, construct `HfApi(token=token)`, pass to `run_publish(token=token)`

## Phase 3: Tests — Cascade & Integration (TDD off)

- [x] 3.1 Add `TestHfTokenFallback` in `tests/test_mcp_server.py` — `HF_TOKEN_PATH` tmp file via `monkeypatch`, verify `HF_TOKEN` prevails over alias/cache, `HUGGING_FACE_HUB_TOKEN` alone succeeds
- [x] 3.2 Add tests in `tests/test_mcp_server.py` for empty/whitespace as absent, `HF_HUB_DISABLE_IMPLICIT_TOKEN=true` skips file, OIDC `HF_OIDC_RESOURCE` propagates error
- [x] 3.3 Add tests in `tests/test_mcp_server.py` for dotenv not overriding env (`override=False`), never-log token in `output`/error, `HfApi(token=...)` called with resolved token (mock)
- [x] 3.4 Add integration tests in `tests/test_mcp_server.py` — file-only upload succeeds, no-token raises `HFTokenError` before `_api.create_repo`, quality gate failure returns `ok False` not `HFTokenError`

## Phase 4: Docs & Polish

- [x] 4.1 Update `README.md` and `README_ES.md` — add `hf auth login` as valid alternative, clarify `HF_HUB_TOKEN` compat alias vs `HUGGING_FACE_HUB_TOKEN`
- [x] 4.2 Update docstrings in `src/sofer/mcp_server.py` and `src/sofer/publish.py` for new helpers and token contract (never interpolate token)
- [x] 4.3 Run `uv run ruff check src/ tests/ && uv run ruff format && uv run mypy src/ && uv run pytest tests/ -q` — fix issues
