# Proposal: sofer v2 — metadata core (Fase A)

## Intent

Repivot sofer from HF-uploader to a Dataset Documentation & Quality CLI, additive only, keeping the name and 562 tests. Never present inference as fact — it always carries confirmed/inferred/unknown + confidence.

## Scope

### In Scope
- metadata.yaml schema + serialization
- InferenceStatus machine (model.py)
- EmailDetector (semantic.py)
- EmailPiiDetector (pii.py) — always "possible_pii"
- `profile` command (read-only)
- `render` command (README.md)
- config-driven priors/thresholds
- fixtures + tests

### Out of Scope
Other 13 detectors; full PII set; HTML renderer; quality observed-vs-expected split; check/document commands; prepare/publish rewiring; card-code removal; empirical prior calibration.

## Capabilities

### New Capabilities
- semantic-type-inference — detectors, InferenceStatus, confidence=match_rate×prior
- pii-detection — heuristic detectors → possible_pii
- metadata — metadata.yaml schema + serialize/load
- profile — CLI command
- render — CLI command

### Modified Capabilities
- cli — register profile + render; update help text

## Approach

metadata.yaml is source of truth; README rendered FROM it (new path only). build_dataset_card untouched → two render paths coexist until unification. Detectors plugin-style (base + registry, mirrors _formats.py), stdlib-only, additive. Confidence=match_rate×config prior; confirmed≥confirm_threshold, inferred between min/confirm, unknown below min.

## Affected Areas

New: semantic.py, pii.py, metadata.py, profile.py, render.py.
Modified: model.py, config.py, cli.py, pyproject.toml.
Untouched: every other module (consume-only).

## Delivery Plan

Chain off feat/sofer-v2-metadata-core. Forecast > 400 lines → chained PRs; each WU autonomous, testable, revertable.

| WU | Targets | Contents |
|----|---------|----------|
| WU-1 | base | model.py + config.py + pyproject.toml |
| WU-2 | WU-1 | _patterns.py + semantic.py + tests |
| WU-3 | WU-2 | pii.py + tests |
| WU-4 | WU-3 | metadata.py + tests |
| WU-5 | WU-4 | profile.py + _cmd_profile + fixtures + integration tests |
| WU-6 | WU-5 | render.py + _cmd_render + cli.py + README/help |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 562-test regression | Med | additive only; consume, never modify |
| Two-render-path drift | Med | render reads YAML only; unify later |
| storage_type vs semantic_type collision | Med | strict schema naming |
| Confidence non-determinism | Low | fixed sample; sorted_keys YAML |
| PII over/under-flagging | Med | heuristic, always "possible", config thresholds |

## Rollback Plan

Additions are new modules + additive dataclasses/constants + two subparsers. Revert = drop the PR chain (no data migration, 562 tests untouched); revert one WU independently.

## Dependencies

None new (stdlib only; PyYAML present).

## Success Criteria

- [ ] `sofer profile dataset.csv` writes metadata.yaml (read-only, no network)
- [ ] `sofer render metadata.yaml` → README.md, status-annotated
- [ ] confirmed/inferred/unknown distinguished with confidence
- [ ] confidence=match_rate×prior; priors/thresholds config-driven
- [ ] 562 tests pass + new tests; other commands unchanged
