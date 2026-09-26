# Design — `2026-09-26-chore-234-verify-escape-hatch`

## Technical Approach

Declare the escape hatch honestly in the three places that already speak about the mapping contract
(AGENTS.md rule 6, `openspec/config.yaml` `rules.specs`, the checker), record the permanent-backlog
policy in the registry, and expose the `verify:` count on every checker run. No `verify:` reference is
resolved. `SCENARIO_RE`'s level is documented and pinned by tests.

## Architecture Decisions

### ADR-1 — Option (b): `verify:` is declared and non-verifiable

**Choice:** keep `verify:` as the escape hatch and say so plainly, with an owner and a review
trigger. The checker keeps validating only non-emptiness.
**Alternatives:** option (a), machine-checking `verify:` against a declared class. Rejected: it would
reshape 46 heterogeneous rows, invent a resolvable namespace, contradict the accepted #211 D2, and
imply "the artifact exists" proves the scenario.
**Rationale:** the gate's honest limit is "force the evidence class to be declared". Accountable
declaration is the correct granularity; fake verification is worse than none.

### ADR-2 — Owner and review trigger are fixed strings

**Choice:** owner = `the repository maintainer`; review trigger = `any change to a verify: row or to
a spec's evidence class, and each release review`. These live as module constants in the checker and
are stated in rule 6, `rules.specs`, and the registry.
**Alternatives:** a named individual (rejected: does not survive turnover); "when convenient"
(rejected: not a trigger).
**Rationale:** a stable role and a concrete recurrence make the escape hatch reviewable; the static
guard pins both so they cannot be dropped silently.

### ADR-3 — The checker reports the accepted `verify:` count

**Choice:** `_report` prints one `INFO:` line naming the number of `verify:` rows it accepted, labelled
as declared, non-verifiable evidence, with the owner and review trigger. `_count_verify_rows` counts
rows whose Verification cell begins with `verify:` in mapped tables.
**Alternatives:** per-row output for all 46 (rejected: noise); no count (rejected: the issue's whole
point is that the hatch is invisible).
**Rationale:** a visible count turns the hatch's growth into an explicit review signal without
asserting anything about the evidence.

### ADR-4 — The 17 unmapped specs are a permanent declared backlog

**Choice:** the registry states the set is a **permanent declared backlog**, not pending work, with
the same owner/trigger. The checker's existing bijection already prevents silent growth.
**Alternatives:** a per-change ratchet ("at most one table adopted per change"). Rejected: it needs a
baseline the tree does not carry, and #211 already fixes the no-sweep boundary; the explicit policy is
mechanically enforceable only as the existing bijection, which is kept.
**Rationale:** the honest statement of the boundary the issue asks to record.

### ADR-5 — `SCENARIO_RE` is documented and pinned

**Choice:** document that `SCENARIO_RE` matches exactly `#### Scenario:` (four hashes) with optional
leading whitespace, add a comment beside the regex, and add tests: a `#####`/`###` heading is not
enumerated, an indented `####` heading is.
**Alternatives:** relax the regex to any heading level (rejected: the counted scenario inventory and
the #211 measurement are defined at four hashes; changing it is a separate decision).
**Rationale:** the assumption is now explicit and a level change fails a test instead of silently
miscounting.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `AGENTS.md` | Modify | Rule 6: state the non-verifiable escape hatch, its owner, and its review trigger |
| `openspec/config.yaml` | Modify | `rules.specs`: align the escape-hatch bullet with rule 6 |
| `scripts/check_test_mapping.py` | Modify | Docstring states the policy; owner/trigger constants; `_count_verify_rows` + report line; `SCENARIO_RE` documented |
| `openspec/test-mapping-registry.md` | Modify | Permanent declared-backlog decision with owner and review trigger |
| `openspec/specs/process-boundary/spec.md` | Modify | Add requirement PB-15 + its Test Mapping rows |
| `tests/test_test_mapping_checker.py` | Modify | Pin `SCENARIO_RE` level; assert the declared `verify:` report line |
| `tests/test_ci_workflows.py` | Modify | Static guard: rule 6 + `rules.specs` + registry state the owner/trigger |
| `openspec/changes/2026-09-26-chore-234-verify-escape-hatch/**` | Create | This change's SDD artifacts |

## Interfaces / Contracts

The checker's new report line is an **observable contract** for the test and for a human running the
gate:

```text
INFO: verify: <N> declared evidence row(s) — declared, non-verifiable escape hatch;
      owner: the repository maintainer;
      review: any change to a verify: row or to a spec's evidence class, and each release review
```

`SCENARIO_RE` contract (documented + pinned):

```text
scenario heading := optional indent + "####" + whitespace + "Scenario:" + name
                     (exactly four hashes; "###"/"#####" are not scenario headings)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `SCENARIO_RE` level; the declared `verify:` report line | `tests/test_test_mapping_checker.py` via the subprocess harness on fixture trees |
| Static | Rule 6 / `rules.specs` / registry agreement on non-verifiable + owner + trigger | `tests/test_ci_workflows.py` text/YAML inspections |
| Gate | Checker exits 0 and prints the count | verify-phase runtime evidence in the verify report |
| Suite | No regression | `uv run pytest tests/ -q` |

## Threat Matrix

No new subprocess, network, path, or privilege boundary is introduced: the change adds text, one
report line computed from already-parsed tables, and tests. The existing subprocess boundary
(pytest collection) is unchanged. N/A.

## Migration / Rollout

No migration and no feature flag. The text, checker, registry, spec, and tests land together, so the
tree is green from the first commit.

## Open Questions

None. The three issue decisions (option (b); permanent backlog; `SCENARIO_RE` documented + pinned) are
settled above.
