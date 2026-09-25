# Design: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

## Technical Approach

Eight documentation/spec files edited in place, no source change:

1. **Retire `uploader.py` requirements** — `parquet-conversion/spec.md` §4 heading names
   `_converters.py` and a `Superseded` banner points to §13 and the prepare/publish split;
   §4.2 is marked superseded; §10.3 defers to `coverage`; §11's checklist row names the
   current owners. `repo-compliance/spec.md` §6.3 defers to `coverage`; its checklist rows
   name `publish.py`/`prepare.py`; the `cli.py` row drops the `uploader.upload()` claim.
   `codebook/spec.md` CB-R04 names the `publish` staging layout.
2. **Inventories** — `AGENTS.md` rule 10 and the `CONTRIBUTING.md` tree add the missing
   modules and explicitly defer to `ls src/sofer/`; CONTRIBUTING names `[tool.ruff]` in
   `pyproject.toml`.
3. **`project.md` baseline** — coverage recorded as installed; absolute counts replaced by
   the CI suite gate; module inventory defers to the directory; version-constant claim
   replaced by the runtime `_version.py` contract; `data/` → `raw/` and gate scopes widened
   to match CI.
4. **De-identify** — the two canonical-spec `user="emiliodavola"` examples use `<hf-user>`.

No delta spec: the specs are corrected in place, and the affected specs are registered as
unmapped (no `## Test Mapping` table), so the checker's bijection is unaffected.

## Architecture Decisions

### Decision: Mark the old `uploader.py` design superseded instead of rewriting it

**Choice**: Add a `Superseded` banner and retarget the live requirements; keep the historical
text.
**Alternatives considered**: Delete §4/§5; fully rewrite the spec to the current architecture.
**Rationale**: `parquet-conversion` §13 already declares it supersedes §4; the historical text
is an audit record, and #188 accepts an explicit superseded marking. A full rewrite risks
introducing new inaccuracies in a spec nobody executes.

### Decision: Defer per-module coverage floors to the `coverage` capability

**Choice**: Both specs say the floor is owned by `openspec/specs/coverage/spec.md` and do not
re-declare a number.
**Alternatives considered**: Keep 90%/80%.
**Rationale**: The `coverage` capability (COV-01/COV-06/COV-07) is the single source of the
per-module floor policy; duplicated numbers drift (exactly the #188 finding).

### Decision: Defer inventories to the directory, and also list the modules

**Choice**: Add the missing modules to the thematic lists AND state the directory is the
source of truth.
**Rationale**: Satisfies #187's either/or, and the explicit deferral prevents the list from
going stale again.

## Data Flow

    src/sofer/ tree ──> AGENTS rule 10 / CONTRIBUTING tree (or `ls src/sofer/`)
    conversion code (_converters.py, prepare.py) ──> parquet-conversion spec owners
    delivery code (publish.py) ──> repo-compliance spec owners + codebook CB-R04
    pyproject [tool.coverage] ──> project.md + the `coverage` capability

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `openspec/specs/parquet-conversion/spec.md` | Modify | §4/§5 superseded; §10.3 defers; §11 checklist corrected |
| `openspec/specs/repo-compliance/spec.md` | Modify | §6.3 defers; checklist rows corrected; cli.py row fixed |
| `openspec/specs/codebook/spec.md` | Modify | CB-R04 names the `publish` staging layout |
| `openspec/specs/mcp-server/spec.md` | Modify | Example → `<hf-user>` |
| `openspec/specs/process-boundary/spec.md` | Modify | Two examples → `<hf-user>` |
| `AGENTS.md` | Modify | Rule 4 example; rule 10 inventory + source-of-truth line |
| `CONTRIBUTING.md` | Modify | Tree + ruff config location |
| `docs/configuration.md` | Modify | Conversion example `raw/` → `build/` |
| `openspec/project.md` | Modify | Coverage, counts, inventory, version claim, layout, gate scopes |

## Interfaces / Contracts

Documented spec contract (after this change): conversion owner =
`_converters.py` + `prepare.py`; delivery owner = `publish.py`; per-module coverage floor
owner = the `coverage` capability. Module inventory owner = `ls src/sofer/`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Contract | test-mapping bijection intact | `uv run python scripts/check_test_mapping.py` |
| Static | CI-08/CI-09 CONTRIBUTING + AGENTS assertions | `uv run pytest tests/test_ci_workflows.py -q` |
| Static | Greps: no live `uploader.py` requirement, no `emiliodavola` fixture, no `ruff.toml`, no stale counts | `git grep` |
| Full | No collateral regression | `uv run pytest tests/ -q` |
| Independent | Owners/inventories/greps match the tree | Read-only verifier (see verify-report) |

## Threat Matrix

N/A — documentation/spec prose only; no runtime boundary, routing, subprocess, VCS/PR
automation, or executable-file classification changes.

## Migration / Rollout

None. The `coverage` capability remains the source of truth; no code or workflow changes.

## Open Questions

None.
