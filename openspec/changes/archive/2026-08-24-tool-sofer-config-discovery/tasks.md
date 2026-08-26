# Tasks: Fix `[tool.sofer]` config discovery anchoring (#56)

## Grep Audit Results (mechanical, executed this phase)

Frozen `from .config import ...` bindings in `src/sofer/` (10 modules):

| File:Line | Frozen names |
|---|---|
| `src/sofer/cli.py:19` | `CODEBOOK_MAX_SAMPLE`, `DEFAULT_CONFIG_NAME`, `OUTPUT_DIR` |
| `src/sofer/checks.py:17` | `REPORT_LINE_WIDTH`, `REPORT_SUB_LINE_WIDTH` |
| `src/sofer/codebook.py:23` | multiline block incl. `CODEBOOK_MAX_SAMPLE`, `OUTPUT_DIR` |
| `src/sofer/_csv_reader.py:15` | `CODEBOOK_MAX_SAMPLE`, `CSV_DELIMITER`, `CSV_ENCODING` |
| `src/sofer/profile.py:24` | `CSV_DELIMITER`, `CSV_ENCODING`, `PROFILE_MAX_SAMPLE` |
| `src/sofer/publish.py:62` | multiline block incl. `DEFAULT_CONFIG_NAME` |
| `src/sofer/quality.py:21` | multiline block |
| `src/sofer/prepare.py:65` | multiline block |
| `src/sofer/repo_compliance.py:22` | multiline block |
| `src/sofer/scanner.py:20` | `OUTPUT_ENCODING` |

Correct precedent already in place: `pii.py:30`, `semantic.py:23` use `from . import config`.

Default-param captures (beyond plain imports):
- `codebook.py:258` and `codebook.py:331` — `max_sample: int = CODEBOOK_MAX_SAMPLE`
- `_csv_reader.py:29` — `max_sample: int | None = CODEBOOK_MAX_SAMPLE` (**audit finding not in design's AD-3 table — must also get None-sentinel treatment**)

Argparse defaults capturing pre-reload values:
- `cli.py:606–607` — `--max-sample` `default=CODEBOOK_MAX_SAMPLE` (help string also embeds it)
- `cli.py:616` — `--config` `default=DEFAULT_CONFIG_NAME`
- `cli.py:707` — `scan` positional config `default=DEFAULT_CONFIG_NAME`

Test-side frozen captures and seams:
- `tests/test_config.py:75,:113` — zero-arg monkeypatch `lambda: tmp_path` on `_find_project_root` (seam breaks with new signature)
- `tests/test_config.py:16` — `from sofer.config import (...)` at module top
- `tests/test_repo_compliance.py:8,:1989,:2301` — `from sofer.config import ...` constants captured at import/call time (**audit finding: stale-value risk once reload mutates constants mid-process**)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~550–650 across ~13 files |
| 400-line budget risk | Low (vs 2000-line session budget; exceeds 400-line default, accepted by auto-forecast) |
| Chained PRs recommended | No |
| Suggested split | Single PR, 3 ordered work-unit commits |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

### Work Units (commit sequencing per design)

| Unit | Goal | Commit | Verification gate |
|------|------|--------|-------------------|
| WU-1 | config.py core + test seam migration | 1 | pytest subset green |
| WU-2 | Consumer de-freeze (all 10 modules + sentinels + argparse) | 2 | full suite green |
| WU-3 | Reload hooks + visibility + docs + regression | 3 | suite + ruff + mypy green |

## Phase 1: Foundation — config.py core + seam migration (WU-1)

- [x] 1.1 Rewrite `_find_project_root(start: str | Path | None = None) -> Path | None` in `src/sofer/config.py`: walk `[start_dir, *start_dir.parents]`, first hit wins, `None` when exhausted; delete the `Path(__file__)` anchor. Verify: `uv run ruff check src/sofer/config.py`.
- [x] 1.2 Add `reload(start=None) -> None` recomputing merged values and rebinding all module constants under a `threading.Lock`; set `SOURCE_PATH: Path | None`; emit one stderr line when `SOFER_VERBOSE` env is truthy (AD-2/AD-5). Verify: `uv run python -c "import sofer.config"` (no fs access at import).
- [x] 1.3 Make import-time binding source only from `_DEFAULTS` (no filesystem access during module import — hardens TC-03).
- [x] 1.4 Migrate `tests/test_config.py` seam: both `monkeypatch.setattr("sofer.config._find_project_root", lambda: tmp_path)` (:75,:113) → `lambda start=None: tmp_path`; convert `tests/test_config.py:16` from-import to `from sofer import config` + attribute reads.
- [x] 1.5 Create `tests/conftest.py` with a `pytree` fixture helper building tmp `pyproject.toml` layouts (with/without `[tool.sofer]`, nested trees).
- [x] 1.6 Verify WU-1: `uv run pytest tests/test_config.py -q && uv run ruff check src/sofer/config.py tests/test_config.py tests/conftest.py`.

## Phase 2: Consumer de-freeze (WU-2)

- [x] 2.1 Convert mechanical frozen imports to `from . import config` + `config.X` call-time access in: `checks.py`, `profile.py`, `scanner.py`, `_csv_reader.py` (per audit table lines). Verify: `uv run ruff check src/sofer/checks.py src/sofer/profile.py src/sofer/scanner.py src/sofer/_csv_reader.py`.
- [x] 2.2 Same conversion for multiline-import modules: `quality.py`, `prepare.py`, `publish.py`, `repo_compliance.py`. Verify: `uv run pytest tests/test_quality.py tests/test_repo_compliance.py -q` (or matching test files).
- [x] 2.3 Same conversion for `cli.py` (:19) and `codebook.py` (:23), replacing every function-body use of frozen names (`OUTPUT_DIR` at cli.py:281/285/313/316, codebook.py:394).
- [x] 2.4 De-freeze `codebook.py:258,:331`: `max_sample: int | None = None`, body resolves `config.CODEBOOK_MAX_SAMPLE if max_sample is None`.
- [x] 2.5 De-freeze `_csv_reader.py:29` (audit finding): same None-sentinel pattern for its two reader signatures (:29 and the `max_sample: int | None` consumer at :83).
- [x] 2.6 De-freeze argparse: `cli.py:606` → `default=None` with `_cmd_codebook` resolving through `config.CODEBOOK_MAX_SAMPLE`; fix help string (:607) to describe behavior instead of embedding a value; leave `--config` defaults (:616,:707) reading `config.DEFAULT_CONFIG_NAME` inside `_build_parser()` (post-Phase-0, correct per AD-3).
- [x] 2.7 Migrate `tests/test_repo_compliance.py:8,:1989,:2301` from-imports to `config.X` attribute reads (stale-capture risk).
- [x] 2.8 Re-audit: `rg "from \.config import" src/ tests/` must return zero matches; `rg "= CODEBOOK_MAX_SAMPLE|= DEFAULT_CONFIG_NAME|= OUTPUT_" src/` must return zero matches. Verify WU-2: `uv run pytest tests/ -q` (422 baseline green) + `uv run mypy src/` under Python 3.13.

## Phase 3: Hooks & wiring (start of WU-3)

- [x] 3.1 In `src/sofer/model.py` `from_toml`: call `config.reload(base_dir)` immediately after `base_dir = path.parent`, before validation (only dataset-anchored call site — TC-04/TC-05).
- [x] 3.2 In `src/sofer/cli.py` `main()`: call `config.reload(None)` before `_build_parser()` (Phase-0 bootstrap anchor — TC-07).
- [x] 3.3 Confirm structural single-fire: reload call sites are exactly `{model.from_toml, cli.main}`; enforce via re-audit `rg "config\.reload\(" src/`.

## Phase 4: Tests — one task per spec requirement

- [x] 4.1 **TC-01** (`tests/test_config.py`): pyproject two levels above dataset dir honored; start-dir itself included in walk; `reload(tmp_tree)` selects temp pyproject without touching real user dirs.
- [x] 4.2 **TC-02**: conflicting `schema_sample_size` in dataset tree (500) vs cwd tree (1000) → 500 wins; empty trees → all values equal `_DEFAULTS`.
- [x] 4.3 **TC-03**: section-less `[project]`-only pyproject stops walk → defaults; editable-install simulation: sofer package dir outside user tree never consulted.
- [x] 4.4 **TC-04** (integration): monkeypatched reload counter around `main([...])` asserts exactly one Phase-1 reload; `sofer codebook FILE` with no `--config` anchors cwd; csv delimiter override effective same-invocation.
- [x] 4.5 **TC-05** (integration): direct `DatasetConfig.from_toml` on tmp tree sets `config.SCHEMA_SAMPLE_SIZE` from sibling pyproject.
- [x] 4.6 **TC-06**: post-reload visibility through `generate(max_sample=None)` and csv reader sentinel; two sequential operations see reloaded value (no stale import-time copy).
- [x] 4.7 **TC-07**: cwd-tree pyproject sets `default_config_name = "my.toml"`; after `reload(None)` parser default reflects it.
- [x] 4.8 **TC-08** (capsys): `SOFER_VERBOSE=1` → stderr absolute path line (or "built-in defaults"); unset → stdout byte-identical, no source line.
- [x] 4.9 Verify Phase 4: `uv run pytest tests/test_config.py -q && uv run pytest tests/ -q`.

## Phase 5: Docs & final regression (rest of WU-3)

- [x] 5.1 **TC-09**: README §[tool.sofer] documents anchoring rules, three-step precedence (dataset dir → cwd → `_DEFAULTS`), bootstrap-key cwd-only caveat (`default_config_name`, `output_dir` until Phase 1 rebinds), editable-install behavior shift, and `SOFER_VERBOSE` usage (AGENTS.md rule 7).
- [x] 5.2 Add release-notes note (GitHub Release notes via PR description or changelog entry) about editable-install runtime behavior shift — maintainers' own repo TOML no longer applies at runtime.
- [x] 5.3 Final regression: `uv run pytest tests/ -q` (≥422 + new tests green), `uv run ruff check .`, `uv run mypy src/` (Python 3.13); confirm CLI help text accuracy for changed flags.
