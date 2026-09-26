# Archive Report — `2026-09-26-chore-234-verify-escape-hatch`

> Issue #234, branch `chore/234-verify-escape-hatch`, base `dev@90de0f7`. Docs + checker + registry +
> spec + tests. This report records the archive-time sync.

## Decision of record

**Option (b):** a `verify:` row is a **declared, non-verifiable** escape hatch. Owner: the repository
maintainer. Review trigger: any change to a `verify:` row or to a spec's evidence class, and each
release review. The 17 unmapped specs are a **permanent declared backlog**, not pending work. The
`SCENARIO_RE` four-hash assumption is documented and pinned by tests. Option (a) (machine-check the
`verify:` evidence) is explicitly rejected.

## Sync performed

| Target | Action | Result |
| --- | --- | --- |
| `openspec/specs/process-boundary/spec.md` | **ADDED** requirement **PB-15** with four scenarios, and its four rows appended to the spec's `## Test Mapping` table | The canonical capability now carries the escape-hatch policy; the scenario↔row bijection holds (checked) |
| `AGENTS.md` rule 6 | Escape-hatch sentence rewritten: declared, non-verifiable, owner + review trigger; registry stated as permanent declared backlog | The normative home is honest |
| `openspec/config.yaml` `rules.specs` | Matching bullet added; registry bullet retitled | The two normative homes agree (static guard) |
| `scripts/check_test_mapping.py` | Docstring + owner/trigger constants + `_count_verify_rows` report line + `SCENARIO_RE` comment | The checker states the policy and reports the hatch size on every run |
| `openspec/test-mapping-registry.md` | Permanent declared-backlog decision with owner + trigger; entry reasons retitled | The policy is recorded where the issue requires |

## Destructive-delta guard

No requirement was **REMOVED** or **MODIFIED**; the delta is a pure **ADDED** requirement. PB-01..PB-14
keep their exact canonical text. No `verify:` row was resolved, re-prefixed, or removed; the gate
still exits non-zero on the same violations.

## Post-sync checks

- `uv run python scripts/check_test_mapping.py` → `OK: test-mapping contract holds` (exit 0), with the
  declared `verify:` report line present.
- The four COV-06 modules stay at 100.00%; TOTAL stays above the config floor (no coverage path
  changed).
