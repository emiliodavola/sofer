# Test Mapping Registry

Every spec under `openspec/specs/` that does **not** carry a `## Test Mapping` section SHALL be
listed here exactly once, with a non-empty reason. This registry is the checker's bijection partner
(`scripts/check_test_mapping.py`, capability `mapping-checker` MC-05): `mapped ∪ registered` equals
the full spec set and `mapped ∩ registered` is empty, so a new spec cannot silently fall outside the
gate and a spec that gains a table must be de-registered. Scenario counts are **re-derived at check
time** and are deliberately not stored here — a hand-maintained count is exactly the stale-literal
class issue #214 files.

Each entry below is a **declared backlog** item, not mapped work: the gate does not cover it until a
`## Test Mapping` table lands in its spec.

| Spec | Reason |
| --- | --- |
| cli | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| codebook | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| data-quality | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| mcp-registration | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| mcp-server | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| metadata | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| packaging | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| parquet-conversion | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| pii-detection | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| prepare | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| profile | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| publish | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| render | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| repo-compliance | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| scan | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| semantic-type-inference | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
| tool-config | No `## Test Mapping` section — declared backlog; gate does not cover it until a table lands |
