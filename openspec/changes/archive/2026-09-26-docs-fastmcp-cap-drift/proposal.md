# Proposal: Align the fastmcp cap to `>=4,<5` (#257)

## Intent

PR #253 bumped `fastmcp` from 3.4.7 to 4.0.5 and adapted the code; `uv.lock` and the wheel
assertions moved to `>=4,<5`. Three canonical declaration homes were not swept: the
`packaging` and `mcp-server` specs still require `fastmcp>=3.4,<4` (normative SHALL), and
`CONTRIBUTING.md` + `.github/dependabot.yml` still describe the `<4` cap. The canonical spec
therefore contradicts the shipped code, and no guard catches it (both specs are in the
permanent unmapped backlog). This change amends the requirements and the two prose homes, and
adds one supporting guard.

## Scope

### In Scope

- `openspec/specs/packaging/spec.md`: PKG-06 → `fastmcp>=4,<5` (requirement + 2 scenarios).
- `openspec/specs/mcp-server/spec.md`: MSP-R02 and MSP-R12 → `fastmcp>=4,<5` (requirements + 3 scenarios).
- `CONTRIBUTING.md`: `<4` cap → `<5`.
- `.github/dependabot.yml`: `<4` cap comment → `<5`.
- `tests/test_packaging.py`: a supporting guard deriving the cap from `pyproject.toml`.

### Out of Scope

- Any `src/sofer/**` change — PR #253's adaptation is correct.
- `uv.lock` / `pyproject.toml` — already `>=4,<5`.
- Any other `<4` mention that is **historical narrative** (e.g. `openspec/specs/ci/spec.md`
  CI-14 records that Dependabot rewrote the then-declared `<4` cap to `<5`; that is accurate
  history, not a requirement).
- The PKG-05 install contract (#259) and the SDD-context reconciliation (#258).

## Capabilities

### Modified Capabilities

- `packaging`: PKG-06 fastmcp cap → `>=4,<5`.
- `mcp-server`: MSP-R02 and MSP-R12 fastmcp cap → `>=4,<5`.

No scenario is added or removed; only the cap literal changes.

## Approach

1. Replace the cap literal in the two specs and update the requirement provenance notes.
2. Align `CONTRIBUTING.md` and the `.github/dependabot.yml` comment.
3. Add the supporting guard to `tests/test_packaging.py`.
4. Verify with the focused guard, the mcp-server wheel test, the full suite, the gates, and
   the checker; archive the change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/packaging/spec.md` | Modified | PKG-06 cap |
| `openspec/specs/mcp-server/spec.md` | Modified | MSP-R02 + MSP-R12 cap |
| `CONTRIBUTING.md` | Modified | fastmcp cap prose |
| `.github/dependabot.yml` | Modified | fastmcp cap comment |
| `tests/test_packaging.py` | Modified | One supporting guard |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missing a `<4` requirement home | Low | Targeted grep for `fastmcp>=3.4,<4` and the `` `<4` `` phrase across specs/CONTRIBUTING/dependabot |
| Guard duplicates the cap instead of deriving it | Low | The cap is derived from `pyproject.toml`; the guard holds no version literal |
| Historical `<4` mentions are mistaken for requirements | Low | Only the normative specs and the two prose homes are edited; CI-14's narrative is left intact |

## Rollback Plan

Revert the five-file diff + archived change folder. No dependency, code, workflow, or release
state is touched.

## Dependencies

None.

## Success Criteria

- [ ] Both specs require `fastmcp>=4,<5`; CONTRIBUTING and dependabot say `<5`.
- [ ] The supporting guard passes and fails if the cap drifts.
- [ ] Full suite green; ruff/mypy/pyright clean; checker exit 0.
