# Test Mapping Registry

Every spec under `openspec/specs/` that does **not** carry a `## Test Mapping` section SHALL be
listed here exactly once, with a non-empty reason. This registry is the checker's bijection partner
(`scripts/check_test_mapping.py`, capability `mapping-checker` MC-05): `mapped ∪ registered` equals
the full spec set and `mapped ∩ registered` is empty, so a new spec cannot silently fall outside the
gate and a spec that gains a table must be de-registered. Scenario counts are **re-derived at check
time** and are deliberately not stored here — a hand-maintained count is exactly the stale-literal
class issue #214 files.

## Decision — permanent declared backlog (issue #234)

The entries below are a **permanent declared backlog**, not pending work. No sweep will author a
`## Test Mapping` table for them; they stay outside the gate until a spec voluntarily adopts one, at
which point it MUST be de-registered here (the checker enforces that). This is the "no sweep"
boundary of #211, stated explicitly.

- **Owner:** the repository maintainer.
- **Review trigger:** any change to this registry or a spec's `## Test Mapping` status; reviewed at
  each release review.

Each entry below is a **declared backlog** item, not mapped work: the gate does not cover it until a
`## Test Mapping` table lands in its spec.

| Spec | Reason |
| --- | --- |
| cli | No `## Test Mapping` section — permanent declared backlog |
| codebook | No `## Test Mapping` section — permanent declared backlog |
| data-quality | No `## Test Mapping` section — permanent declared backlog |
| mcp-registration | No `## Test Mapping` section — permanent declared backlog |
| mcp-server | No `## Test Mapping` section — permanent declared backlog |
| metadata | No `## Test Mapping` section — permanent declared backlog |
| packaging | No `## Test Mapping` section — permanent declared backlog |
| parquet-conversion | No `## Test Mapping` section — permanent declared backlog |
| pii-detection | No `## Test Mapping` section — permanent declared backlog |
| prepare | No `## Test Mapping` section — permanent declared backlog |
| profile | No `## Test Mapping` section — permanent declared backlog |
| publish | No `## Test Mapping` section — permanent declared backlog |
| render | No `## Test Mapping` section — permanent declared backlog |
| repo-compliance | No `## Test Mapping` section — permanent declared backlog |
| scan | No `## Test Mapping` section — permanent declared backlog |
| semantic-type-inference | No `## Test Mapping` section — permanent declared backlog |
| tool-config | No `## Test Mapping` section — permanent declared backlog |
