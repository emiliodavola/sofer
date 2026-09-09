# Proposal: fix-dataset-identity-context (issue #116)

## Intent

CLI and MCP resolve dataset identity (name/user → `<name>.toml`, dataset root, config-discovery anchor, output anchors) through five interacting mechanisms, none of which validates before writing. Bug: with the MCP server root at a parent dir, `sofer_init(name="test", user="emiliodavola")` with omitted `cwd` wrote `Desktop/test.toml` instead of `Desktop/test/test.toml` because `Path.is_relative_to` includes equality — the auto-detect silently selected the parent root. Why now: issue #116 (tracker #115, first slice) needs one small, testable contract so a lower-capability implementer does not reverse-engineer five mechanisms; the live `mcp-server` INIT-02 "cwd None back-compat" scenario already contradicts the shipped code (drift from ad-hoc commit 82abfbc), so this change also removes a latent spec-vs-code conflict.

## Scope

### In Scope
- New shared module `src/sofer/execution_context.py` (identity contract, below).
- CLI `_cmd_init` + MCP `sofer_init` adopt validate → resolve → write; pre-write rejection of missing/blank/placeholder/unsafe/injection-shaped name and user.
- Canonical reporting: CLI prints absolute `config_path`; MCP envelope AND `output_schema` gain `config_path`/`dataset_root` (FastMCP boundary drops undeclared keys — same change or clients never see them).
- MCP `cwd=None` fail-closed strict-descendant policy with actionable `IdentityResolutionError`.
- `DatasetConfig.from_toml(path, discovery_root=None)` passes `stop_at=discovery_root` into `config.reload`; retire `_bound_discovery` (mcp_server.py:457-471).
- Relative output overrides anchor to `config_path.parent` in both adapters; CLI single-file `--output` anchors to the input's parent.
- Tests: real-process parent-root/child-cwd stdio launch (ground-truth-mandated); `validate_identity`/`resolve_dataset_root` matrix; `sofer_init` schema assertions; 4 intentional test flips.

### Out of Scope
- Removing `default_config_name` guessing for non-canonical CLI use (TC-07 bootstrap keeps it).
- Changing `model._PLACEHOLDERS` or the `repo_id` regex; only reusing them pre-write.
- HF publish/auth ladder, redaction, multi-dataset repo management.
- Any operation touching `SOFER_TRACE.md` (PB-08).

## Capabilities

### New Capabilities
- None — the shared module is new code, but the spec-level contract lands inside existing capabilities.

### Modified Capabilities
- `mcp-server`: INIT-02 (fail-closed `cwd=None` + strict-descendant), INIT-03 (identity reporting), MSP-R03 (`sofer_init` output_schema gains `config_path`/`dataset_root`), MSP-R10 (`from_toml` `discovery_root`), ADDED identity-validation requirement (both adapters).
- `cli`: CLI-R07 — init rejects placeholder/unsafe identity pre-write; `--user` required; canonical absolute `config_path` printed.
- `tool-config`: TC-05 — note that `from_toml` accepts `discovery_root` for bounded library loads.
- `process-boundary`: new scenario — real-process parent-root/child-cwd stdio launch via a PB-09-compliant second module-scoped fixture.

## Approach

Approach 1 — `src/sofer/execution_context.py`:

- `DatasetIdentity` dataclass: `name`, `user`, `dataset_root: Path` (absolute, resolved), `config_path: Path` = `dataset_root / f"{name}.toml"`.
- `validate_identity(name, user) -> list[str]` — both mandatory non-empty; single component (no `/`, `\`, no `ntpath.splitdrive` drive/UNC, no `..`/`.` components, no quotes, no newlines/control chars, no leading/trailing whitespace); `user` MUST match `^[\w\-]+$` and MUST NOT be a placeholder (`YOUR_USER` plus `model._PLACEHOLDERS` normalized); rejects BEFORE any write.
- `resolve_dataset_root(cwd, *, live_cwd: Path, server_root: Path) -> Path` — `cwd` given → contained under `server_root` (`_contained_path`-equivalent, must-exist not required); `cwd` None → `live_cwd` only when `live_cwd != server_root.resolve() and live_cwd.is_relative_to(server_root.resolve())` (STRICT DESCENDANT); otherwise raise `IdentityResolutionError` naming the required `cwd` argument. CLI passes no server bound (dataset_root = resolved process cwd).
- `report_identity(identity) -> dict` — canonical absolute `config_path`/`dataset_root` strings.
- Adapter deltas: `_cmd_init` (validate → resolve → write → print absolute config_path); `sofer_init` (validate → resolve with server_root → write → envelope + schema); `model.from_toml(path, discovery_root=None)` → `config.reload(path.parent, stop_at=discovery_root)`; MCP config-bearing tools resolve relative output overrides against contained `config_path.parent`; CLI single-file `--output` anchors to input's parent.

## Acceptance Criteria (mapped to issue #116)

| Issue criterion | Mechanism |
|---|---|
| init rejects missing/blank/placeholder/unsafe/injection-shaped values pre-write | `validate_identity` called before any write in both adapters |
| Valid init returns/prints one canonical `config_path` + `dataset_root` | `report_identity`; CLI print + MCP envelope/schema fields |
| Parent-root/child-CWD tests prove the intended directory | real-process stdio test: cwd omitted → input-required, no parent TOML; `cwd=child` → `child/test.toml` + `raw/` |
| Out-of-bound/ambiguous CWD fail closed, truthful recovery | strict-descendant `resolve_dataset_root` + `IdentityResolutionError` naming `cwd` |
| MCP config loading always supplies `discovery_root=server_root` | `from_toml(..., discovery_root=_get_root())`; `_bound_discovery` retired |
| CLI and MCP use same config-relative output resolution | both anchor overrides to `config_path.parent` |
| Tests invoke public CLI/MCP boundaries | `run_cli` subprocess + `Client(server)`/stdio; no helper-only proofs |
| `uv run pytest tests/ -q`, `uv run mypy src/`, Ruff, `git diff --check` pass | PB-07 gates |
| No operation touches `SOFER_TRACE.md` | PB-08 |

## Assumptions & Decisions

1. **Strict-descendant edge**: a deployment where server root == dataset root now fails closed on `cwd=None` — caller MUST pass `cwd=root` explicitly. Documented decision, not left open.
2. **CLI `--user`**: flag kept but required-or-rejected; recommended resolution: require explicit `--user` and reject placeholder `YOUR_USER` pre-write.
3. **`default_config_name` guessing**: kept for non-canonical CLI use (TC-07); criterion only bans guessing in the canonical workflow.
4. **4 existing tests flip intentionally** (test_cli.py:117/187 placeholder generation; test_mcp_server.py:2399-2409, 2521-2534 parent-root fallback) — intentional removals, not regressions.
5. **New**: `sofer_init` schema fields MUST land in the same change as the envelope fields (PB-03 projection mechanism).
6. **New**: `from_toml(discovery_root=...)` is optional — CLI passes none, behavior unchanged there.

## Non-Goals

- No removal of `default_config_name` argparse defaults.
- No `_PLACEHOLDERS`/regex changes; no new HF auth behavior.
- No changes to publish, scan, or validation domain logic beyond identity.
- No `SOFER_TRACE.md` reads/writes/staging.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Root==dataset-root deployments fail closed on `cwd=None` (behavior change) | Med | Document `cwd=root`; decision #1; explicit error message |
| `config_path`/`dataset_root` silently dropped at boundary | Med | Schema updated in same change (decision #5); schema assertions in `test_mcp_schema.py` |
| Spec drift: INIT-02 delta must supersede back-compat cleanly | Med | Delta carries full replacement requirement; archive merge reviewed |
| 4 stale tests flip — misread as regressions | High | Mark as intentional removals in verify-report; PB-07 count re-baselined |
| Real-process stdio test cost | Med | PB-09-compliant second module-scoped fixture, one spawn per module |
| Over-removing CLI default-name guessing | Low | Decision #3 keeps non-canonical CLI path intact |
| `SOFER_TRACE.md` accidentally touched | Low | PB-08; no fixture reads it |

## Proposed Spec Deltas

- `mcp-server`: MODIFIED INIT-02 (cwd=None fail-closed + strict-descendant scenarios), MODIFIED INIT-03 (identity reporting fields), ADDED identity-validation requirement (init rejects unsafe/placeholder identity pre-write), MODIFIED MSP-R03 (`sofer_init` schema gains `config_path`/`dataset_root`), MODIFIED MSP-R10 (`from_toml(discovery_root=server_root)` bounds discovery).
- `cli`: MODIFIED CLI-R07 (explicit `--user`, pre-write rejection, canonical absolute path print).
- `tool-config`: MODIFIED TC-05 (note `discovery_root` param for bounded library loads).
- `process-boundary`: ADDED scenario — parent-root/child-cwd real-process stdio launch (PB-09 second module-scoped fixture).

## Proposal Question Round

Auto mode — the four exploration decisions were pre-approved by the orchestrator and are recorded above as Assumptions & Decisions. No open questions; the user may review decisions 1-2 (strict-descendant edge, CLI `--user` required) before apply.

## Rollback Plan

Single PR on `dev`. Revert via `git revert` of the merge commit; re-enable `_bound_discovery`, restore INIT-02 back-compat scenarios and the old envelope/schema, restore the 4 flipped tests. Spec deltas are destructive (MODIFIED supersedes) — archive-time merge is a plain replace, so rollback is code-level, not spec-merge surgery. No tag/release dependency.

## Dependencies

- None external. Internal seams: fastmcp `output_schema` projection (PB-03), `model._PLACEHOLDERS`, `config.reload(start, stop_at)`, `_contained_path` reuse.

## Success Criteria

- [ ] All 8 issue acceptance criteria proven by boundary-level tests (see mapping table).
- [ ] Real-process stdio test passes: parent-root launch, cwd omitted → input-required refusal with no parent TOML; `cwd=child` → child-anchored TOML + `raw/` + reported identity.
- [ ] `uv run pytest tests/ -q`, `uv run mypy src/`, `uv run ruff check src/ tests/`, `git diff --check` all pass; suite count re-baselined for the 4 intentional removals.
- [ ] `SOFER_TRACE.md` unchanged and untracked.
- [ ] Live specs (mcp-server INIT-02/03, MSP-R03/R10; cli CLI-R07; tool-config TC-05; process-boundary) reflect the new contract with no drift.