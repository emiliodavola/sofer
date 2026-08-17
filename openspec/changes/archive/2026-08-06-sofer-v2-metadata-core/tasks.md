# Tasks: sofer v2 — metadata core (Fase A)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1150 source + ~600 test (~1750 total) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (WU1) → PR 2 (WU2) → PR 3 (WU3) → PR 4 (WU4) → PR 5 (WU5) → PR 6 (WU6) |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Base branch | Notes |
|------|------|-------------|-------|
| WU1 | config + InferenceStatus + EMAIL_PATTERN | feat/sofer-v2-metadata-core | config/model tests; 562 stay green |
| WU2 | semantic.py + test_semantic.py | WU1 branch | new tests |
| WU3 | pii.py + test_pii.py | WU2 branch | new tests |
| WU4 | metadata.py + test_metadata.py | WU3 branch | new tests |
| WU5 | profile.py + _cmd_profile + test_profile.py + CLI | WU4 branch | new tests |
| WU6 | render.py + _cmd_render + test_render.py + README | WU5 branch | new tests |

## Phase 1: Foundation — WU1 (PR 1 → feat/sofer-v2-metadata-core)

- [x] RED `tests/test_model.py`: `InferenceStatus` has exactly `confirmed`/`inferred`/`unknown` (MTA-04).
- [x] RED `tests/test_config.py`: defaults for `SEMANTIC_PRIORS`, `CONFIRM_THRESHOLD`, `MIN_THRESHOLD`, `DETECT_THRESHOLD`, `CONFIDENCE_ROUND_DIGITS`, `PROFILE_MAX_SAMPLE`; TOML override; `semantic_priors` rejects non-dict.
- [x] GREEN `src/sofer/model.py`: add `class InferenceStatus(str, Enum)` (additive; mirrors `QUALITY_CHECK_NAMES`).
- [x] GREEN `src/sofer/config.py`: `_DEFAULTS` += new keys + constants; dict-type validation for `semantic_priors`.
- [x] GREEN `src/sofer/_patterns.py`: module docstring + `EMAIL_PATTERN` (shared regex).
- [x] GREEN `pyproject.toml`: mirror new `[tool.sofer]` keys (email prior `0.98`, thresholds `0.8`/`0.5`/`0.5`, `confidence_round_digits=4`, `profile_max_sample=100000`).
- [x] Verify `uv run pytest tests/ -q` — 562 existing + new stay green.

## Phase 2: Semantic inference — WU2 (PR 2 → WU1 branch)

- [x] RED `tests/test_semantic.py`: detector contract (STI-01), Detection shape (STI-02), confidence `round(0.8×0.9, 4)==0.72` via `pytest.approx` (STI-03), status boundaries (STI-04), email match/no-match (STI-05), `detect_threshold`→`None` boundary, missing values excluded from denominator.
- [x] GREEN `src/sofer/semantic.py`: `Detection` dataclass, `SemanticDetector` ABC, `EmailDetector`, `infer_semantic_types`, `infer_status`.
- [x] Prior read from `SEMANTIC_PRIORS[name]` at detect-time; missing prior → `ValueError`; `confidence = round(match_rate × prior, CONFIDENCE_ROUND_DIGITS)`.
- [x] Verify `uv run pytest tests/ -q`.

## Phase 3: PII detection — WU3 (PR 3 → WU2 branch)

- [x] RED `tests/test_pii.py`: finding shape (PII-02), note always `possible_pii` never affirmative (PII-03), email flag/no-flag (PII-04), `infer_pii_types` aggregation.
- [x] GREEN `src/sofer/pii.py`: `PiiDetection` dataclass, `PiiDetector` ABC, `EmailPiiDetector`, `infer_pii_types` (symmetric aggregator).
- [x] Reuse `EMAIL_PATTERN` from `_patterns`; PII confidence = same `match_rate × SEMANTIC_PRIORS["email"]`.
- [x] Verify `uv run pytest tests/ -q`.

## Phase 4: metadata.yaml — WU4 (PR 4 → WU3 branch)

- [x] RED `tests/test_metadata.py`: skeleton sections (MTA-01), `metadata_version == METADATA_VERSION` (MTA-02), byte-identical serialize + round-trip (MTA-03), per-column contract (`storage_type`/`semantic_type`/`pii`), read-only (MTA-05).
- [x] GREEN `src/sofer/metadata.py`: `METADATA_VERSION = "1"`, schema dataclasses, `serialize` (`yaml.safe_dump(sort_keys=True)`), `load`, `missing_fields` derivation, generated provenance.
- [x] Verify `uv run pytest tests/ -q`.

## Phase 5: profile command — WU5 (PR 5 → WU4 branch)

- [x] RED `tests/test_profile.py`: CSV→metadata.yaml beside dataset (PRF-02), email semantic type + status, `note="possible_pii"`, missing `description`/`license`/`source` in `documentation.missing_fields` (PRF-04), unsupported format → non-zero exit no YAML (PRF-04), source bytes unchanged (PRF-03).
- [x] GREEN `src/sofer/profile.py`: detect format via `_formats`; CSV via `_csv_reader.stream_csv` (`max_sample=PROFILE_MAX_SAMPLE`, config delimiter/encoding); non-CSV via `codebook._read_file`; `codebook.infer_column_type` coarse; semantic + PII; assemble + write `metadata.yaml`; report missing fields (read-only).
- [x] GREEN `src/sofer/cli.py`: `profile` subparser, `_cmd_profile` handler (docstring documents orchestration), `set_defaults(func=_cmd_profile)`.
- [x] Verify `uv run pytest tests/ -q`.

## Phase 6: render command — WU6 (PR 6 → WU5 branch)

- [x] RED `tests/test_render.py`: confirmed plain / `email (inferred, 78%)` / `unknown` (RND-03); README reflects metadata (RND-02).
- [x] GREEN `src/sofer/render.py`: load metadata.yaml → README.md; `round(confidence × 100)` percentage.
- [x] GREEN `src/sofer/cli.py`: `render` subparser + `_cmd_render`; file-vs-directory disambiguation (RND-01).
- [x] RED `tests/test_cli.py`: `profile` + `render` in `--help`, dispatch, help accuracy (CLI-R03/R04).
- [x] GREEN `README.md`: document `profile`/`render` (rule 7).
- [x] Verify `uv run pytest tests/ -q`.

## Verification Checklist (per WU, plus final)

- [x] `uv run pytest tests/ -q` — 562 existing + all new tests green (never reduce).
- [x] `uv run ruff check src/ tests/` — clean.
- [x] `uv run ruff format` — no diff.
- [x] `uv run mypy src/` — clean.
- [x] `build_dataset_card` / `build_schema_report` signatures untouched.

## Delivery Strategy

- **Chain**: `feat/sofer-v2-metadata-core` (tracker). WU1 targets tracker; WU2→WU6 each target the immediate previous WU branch. Only the tracker merges to main.
- **Commits**: work-unit commits; one PR per WU (~290 lines avg, under 400-line budget); review budget 2000 lines across the chain.
- **Rollback**: revert any WU/PR independently; no data migration.
