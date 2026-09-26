# Archive Report — `2026-09-26-test-205-csv-tier-gaps`

> Issue #205, branch `test/205-csv-tier-test-gaps`, base `dev@90de0f7`. Tests-only change (plus one
> comment). This report records the archive-time sync.

## Sync performed

| Target | Action | Result |
| --- | --- | --- |
| `openspec/specs/parquet-conversion/spec.md` | **ADDED** requirement **PC-U07** ("Discriminating, version-stable evidence for the declared-dialect tier") appended at the end of the spec | The canonical `parquet-conversion` capability now carries the evidence duty; PC-U01's behaviour text is untouched |
| `src/sofer/_converters.py` | Comment corrected (no behaviour change) | The `from_pylist` comment now matches the measured pyarrow 25.0.0 behaviour |
| `tests/test_parquet_conversion.py` | F1 rewritten, F4 rewritten | Discriminating plumbing assertion; test-time-derived byte-identity reference |
| `tests/test_converters.py` | F2/F3/F5 tests added | JSONL fallback, `\|` declared-wins, programmatic boundary |

## Destructive-delta guard

No requirement was **REMOVED** or **MODIFIED**; the delta is a pure **ADDED** requirement. PC-U01,
PC-U02..PC-U06, and the universal-pipeline requirement keep their exact canonical text.

## Registry / gate

`parquet-conversion` carries no `## Test Mapping` section, so it remains a registered unmapped spec
in `openspec/test-mapping-registry.md`; the checker's registry↔tree bijection is unchanged. After the
sync the checker reports `parquet-conversion` with the extra scenarios while still classifying it
**unmapped** (no table).

## Post-sync checks

- `uv run python scripts/check_test_mapping.py` → `OK: test-mapping contract holds` (exit 0).
- The four COV-06 modules stay at 100.00%; TOTAL stays above the config floor (no coverage path
  changed).
