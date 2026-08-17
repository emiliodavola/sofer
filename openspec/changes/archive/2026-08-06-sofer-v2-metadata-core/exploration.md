# Exploration: sofer v2 repivot — metadata core (Fase A)

> Saved to Engram topic_key `sdd/sofer-v2-metadata-core/explore`. This file is the filesystem mirror (hybrid mode).

## Current State

sofer today = "publish any dataset to Hugging Face Hub". Flat `src/sofer/` package, argparse CLI with `func` dispatch, one module per concern. Commands: init, scan, validate, prepare, publish, codebook. Config: `[tool.sofer]` in pyproject.toml (`config.py` `_DEFAULTS` dict → module constants) + per-dataset TOML (`model.py` `DatasetConfig.from_toml`). 562 tests passing, Python 3.10+.

## Affected Areas

- `src/sofer/model.py` — add `InferenceStatus`, `SemanticTypeResult`, `PiiFinding` dataclasses (additive).
- `src/sofer/config.py` — add semantic priors + thresholds to `_DEFAULTS`.
- `src/sofer/cli.py` — register `profile` + `render` subcommands (additive).
- `pyproject.toml` — `[tool.sofer]` semantic defaults.
- NEW modules: `semantic.py`, `pii.py`, `metadata.py`, `profile.py`, `render.py`.
- UNTOUCHED: `codebook.py`, `quality.py`, `checks.py`, `repo_compliance.py`, `prepare.py`, `publish.py`, `scanner.py`, `splits.py`, `_mirror.py`, `_csv_reader.py`, `_sentinels.py`, `_parquet_helpers.py`, `_formats.py`, `verification.py`.

## Current capabilities map

**PROFILING** — partial. `codebook.infer_column_type` (codebook.py:36-62) does coarse string-coercion typing only (numeric / categorical/text / mixed / unknown). No semantic types, no confidence, no confirmed/inferred/unknown. `repo_compliance.build_schema_report` + `ColumnSchema` (repo_compliance.py:123-604) do 10k-row sample schema with Parquet/CSV paths.

**QUALITY** — strong P0. `quality.QualityValidator` (quality.py:57-525) single-pass streaming; 9 checks (duplicates, empty_rows/columns, null_profiling, format_consistency, corrupt_records, value_range, cross_file_types, encoding_validation). `QualityResult.partial` already carries the sample-vs-full distinction. Missing: validity/consistency/outlier checks, observed-vs-expected separation.

**DOCUMENTATION** — `build_dataset_card` (repo_compliance.py:629-967) imperatively builds YAML frontmatter + markdown body from `DatasetConfig` + `ColumnSchema`. YAML is NOT the source of truth; no standalone metadata document; no render-from-YAML; no human-input checklist.

**PUBLISHING** — done, desacoupled (`publish.py`: hf vs local target; auto-prepare). Out of Fase A.

## Approaches

1. **Additive metadata-core (RECOMMENDED)** — introduce `metadata.yaml` as source of truth, add `profile` + `render` commands, new detector modules. Existing card generation untouched; two render paths coexist until a later phase unifies.
   - Pros: zero risk to 562 tests; honors "not a rewrite"; clean vertical slice proves the model.
   - Cons: temporary dual render path (drift risk); requires strict naming to avoid vocabulary collision (storage_type vs semantic_type).
   - Effort: Medium.

2. **Deep rewire** — make `build_dataset_card` consume metadata.yaml immediately, replace imperative generation now.
   - Pros: single render path sooner.
   - Cons: touches 60-caller `build_dataset_card` / 30-caller `build_schema_report` — high regression risk, violates additive constraint.
   - Effort: High. Rejected.

## Recommendation

Approach 1. Fase A MVP: metadata.yaml schema + InferenceStatus state machine + ONE semantic detector (EmailDetector) + ONE PII detector (EmailPiiDetector) + `profile` + `render` + config-driven priors. See the Engram artifact for the full YAML skeleton, detector architecture, confidence formula (match_rate × prior), command surface, file sizes, risks, and fixture test strategy.

## Risks

- 562-test preservation (mitigate: additive-only, consume never modify).
- Vocabulary collision (storage_type vs semantic_type).
- Confidence determinism (fixed sample, sorted_keys YAML).
- PII over/under-flagging (heuristic, always "possible", never categorical).
- Two-render-path drift during migration.
- 400-line review budget → chained PRs likely.

## Ready for Proposal

Yes. Proceed to sdd-propose for change `sofer-v2-metadata-core` with the Fase A MVP scope; proposal must resolve the 400-line/chained-PR delivery question and the two-render-path migration risk.
