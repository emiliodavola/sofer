# Design: fix-dataset-identity-context

## Technical Approach

Introduce one shared identity contract in `src/sofer/execution_context.py` and make both adapters delegate to it. `sofer_init` (MCP, mcp_server.py:1647) and `_cmd_init` (CLI, cli.py:825) become **validate → resolve → write**: `validate_identity` rejects unsafe/placeholder/blank identity pre-write (INIT-05 / CLI-R07), `resolve_dataset_root` enforces the fail-closed strict-descendant cwd policy (INIT-02), and the canonical identity is reported as absolute `config_path`/`dataset_root` in the CLI print and the MCP envelope + `output_schema` (INIT-03, MSP-R03 — PB-03: same change or the boundary drops the keys). Config discovery becomes bounded at the MCP server root via `DatasetConfig.from_toml(path, discovery_root=_get_root())` (MSP-R10), retiring `_bound_discovery` (mcp_server.py:457-471). Relative output overrides re-anchor to `config_path.parent` (config-bearing tools) / the input's parent (single-file tools) in both adapters. Nine flips plus a ~43-site mechanical sweep re-base the test suite to the new contract (enumerated below); a real-process parent-root/child-cwd stdio fixture proves the ground-truth reproduction (PB-04/PB-09 second fixture).

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|---|---|---|---|
| D1 | Module | New `src/sofer/execution_context.py` | Fix in-place per adapter; extend `model.py` only | One testable contract (AGENTS.md rule 4); proposal approach 1. `model.py`-only misses the cwd/root half — the actual bug (exploration § root-cause). |
| D2 | `DatasetIdentity` | `@dataclass(frozen=True)`; `config_path` is a **derived property** (`dataset_root / f"{name}.toml"`); `from_parts(name, user, dataset_root)` classmethod resolves `dataset_root` and computes identity | Stored `config_path` field set in `__post_init__` | Property makes the invariant `config_path == dataset_root/name.toml` unbreakable by construction. Frozen = value object (matches conftest `McpStdioServer` frozen pattern). `from_parts` assumes validated input (adapters call `validate_identity` first); it only normalizes (`.resolve()`), never re-validates. |
| D3 | `validate_identity(name, user) -> list[str]` | Errors, not exceptions (proposal signature); **first check message must read `"name must be non-empty"`** | Raise `ValueError` | Keeps `test_empty_name_returns_ok_false` (test_mcp_server.py:2265-2271, `any("non-empty" in e …)`) and `TestRecoveryInit` L198 green without flips. Matrix per INIT-05: both mandatory non-empty (None/""/" " → error); single component — no `/`, `\`, `ntpath.splitdrive` drive/UNC, exact `.`/`..` ban (nested traversal `a/../b` is already banned by the separator rule), no `"`/`'`, no control chars `[\x00-\x1f\x7f]` (covers `\n`/`\t`), no leading/trailing whitespace (`s != s.strip()`); user regex `^[\w\-]+$`; placeholder ban `user.strip().lower() in model._PLACEHOLDERS` (covers `YOUR_USER`→`your_user`, `your-org`, … — model.py:33-35). Placeholder ban applies to **user only** (spec INIT-05 wording; `name` has no placeholder rule). |
| D4 | `IdentityResolutionError` placement | Define in `execution_context.py` | In `model.py` | `from_toml(discovery_root=…)` is an inert walk-up bound — it never raises. `model.py` doesn't need the exception; placing it there would couple model→execution_context. CLI never raises it (no bound). Import direction `execution_context → model (_PLACEHOLDERS) → config` is acyclic. |
| D5 | `resolve_dataset_root` | `resolve_dataset_root(cwd: str\|Path\|None, *, live_cwd: Path, server_root: Path\|None = None) -> Path`. Three modes: (a) `server_root=None` → `live_cwd.resolve()` (CLI no-bound; `cwd` must be None); (b) `cwd is not None` → inline containment (expanduser → absolutize against root → resolve → `is_relative_to`) raising `IdentityResolutionError` on escape; (c) `cwd is None` + root → strict descendant only (`live != root.resolve() AND live.is_relative_to(root.resolve())`) else `IdentityResolutionError` naming the required `cwd` argument with actionable guidance (pass `cwd="<dataset dir>"`). **The MCP str-branch does NOT route through it**: `sofer_init` keeps `_contained_path(cwd, root=…, must_exist=False)` (mcp_server.py:1717) so escapes raise `PathOutsideRootError` per INIT-02 — mode (b) is exercised **only by the unit matrix** (S7). The containment tests at L2422-2429 (`test_cwd_outside_rejected`) and L2641-2646 (`test_cwd_outside_via_mcp_schema_rejected`) keep their `ToolError` expectations **only because the mechanical sweep (D11) adds `user` to them** — without user they now fail at validation before reaching the cwd branch; the sweep region therefore extends through L2646 | Route str-branch through `resolve_dataset_root` | Spec INIT-02 pins **two** error contracts: str-escape → `PathOutsideRootError` (typed throw, boundary ToolError); None-fail-closed → "actionable `IdentityResolutionError` naming the required cwd". `PathOutsideRootError` is an `MCPToolError` living in mcp_server — execution_context can't raise it without an import cycle. Two documented paths, one error family each. |
| D6 | Identity error surfacing (MCP) | `sofer_init` catches `IdentityResolutionError` → **envelope refusal** `_refusal(errors)` (error_code `CONFIG_ERROR`, `next: {}`); `PathOutsideRootError` still propagates as ToolError | Typed throw for both | 10.3 envelope rule (mcp-server spec L364-380): expected failures MUST return the `{ok:false, error_code, message, next, config_errors}` envelope and MUST NOT throw `McpError`; only containment MAY throw. The cwd=None ambiguity is an input omission — same family as the existing name-empty envelope (mcp_server.py:1690-1699) and satisfies the process-boundary "input-required error naming the cwd argument". `next` stays in the dict but is not client-visible (schema drops it — recovery contract keys off hint VALUES, unchanged). |
| D7 | CLI `--user` required | **argparse `required=True`** (exit 2 naming `--user`, no write — CLI-R07 scenario) **AND** `validate_identity` defense-in-depth at the handler (exit 1) | Manual check only in `_cmd_init` | The spec scenario demands "argparse SHALL exit 2 naming the missing --user" — that is argparse behavior. The handler-level gate covers direct `_cmd_init(Namespace(...))` calls in tests (which bypass argparse) and future entry points. Order in `_cmd_init`: validate → resolve → exists-guard → scaffold raw/ → write. |
| D8 | `from_toml(discovery_root)` | `from_toml(cls, path, discovery_root: Path\|None = None)` → `config.reload(base_dir, stop_at=discovery_root)` (model.py:378). **Per-call** `discovery_root=_get_root()` at the 4 MCP sites (L520, L1245, L1367, L1433) + delete `_bound_discovery` definition (L457-471) and its 4 call sites (L524, L1252, L1367-region, L1440) | Single wrapper helper `_bounded_from_toml` | Per-call is a one-argument edit at 4 try/except-wrapped sites; a wrapper adds indirection for a 1-line change and each site's error handling stays local. `_find_project_root` with start outside `stop_at` returns None → defaults (config.py:113), so an out-of-bound base_dir is already safe. |
| D9 | Output anchoring | **Reuse `_contained_path` with the anchor as `root`** — no new helper. Config-bearing tools (6 sites: L775, L851, L1006, L1114, L1265, L1387): `root=cfg._base_dir` (the TOML dir, model.py:508 — already contained under server root, so containment is transitive). Single-file tools (3 sites: L1070, L1177, L1319): `root=data_path.parent` / `root=package_path.parent` (MSP-R10 "anchor on their input's directory"). CLI single-file: resolve relative `--output` against the input's parent inline — `_cmd_codebook` L219 (`Path(args.csv).parent`), `_cmd_profile` L292 (`Path(args.dataset).parent`), `_cmd_render` L361 (package dir-or-file: `pkg if pkg.is_dir() else pkg.parent`). CLI batch is already `cfg._base_dir`-anchored (profile.py:231-240, render.py:200-209, codebook.py:529) — no change. `_validate_output_targets(cfg, root=_get_root())` unchanged: it validates the TOML's declared targets against the server root; adapter overrides now anchor under a contained dir. | New helper in execution_context | `_contained_path` (L282-339) already implements the full algorithm (expanduser, absolutize, resolve, `is_relative_to`, ext allow-list, existence). Duplicating it violates rule 4. |
| D10 | Identity reporting | `report_identity(identity) -> dict` → `{"config_path": str(identity.config_path), "dataset_root": str(identity.dataset_root)}` (absolute strings). Added to the **3 success envelopes** of `sofer_init` (dry-run+move L1795, dry-run-only L1809, real L1828) AND to `output_schema` (L2098-2108: two `{"type":"string"}` properties; `required` stays `["ok","exit_code","output"]`) in the **same change** | Envelope-only | PB-03: FastMCP projects results through the declared `output_schema` — undeclared keys are dropped at the boundary. Envelope+schema must land together or clients never see the identity. Refusals carry no identity fields (pre-write). |
| D11 | Mechanical test sweep | Every in-process `sofer_init` call gains `"user": "testuser"` **and** an explicit `cwd` — `cwd=None` now fails closed when the pytest process cwd (repo root) is not strictly inside `tmp_path`. **~43 sites** need edits: 37 in test_mcp_server.py (region L2154-**2646**, inclusive of the schema test L2641-2646) + 7 in test_mcp_process.py (L113/170/174/181/195/203/262) − 1 already correct (L2576 has user+cwd). Only L2576 is untouched; ~35+ need `user`+`cwd`, the rest are flip sites (below) that change expectations anyway. Explicit `cwd=str(tmp_path)`/`str(child)` is deterministic and matches the existing `test_cwd_contained_succeeds` style | Rely on monkeypatch.chdir everywhere | The fail-closed default silently breaks every call site whose pytest cwd (repo root) is not strictly inside the test root. This is the hidden churn behind the named flips and the driver of the HIGH budget forecast (see Verification Plan). |

## Data Flow

    CLI:  args ─► _cmd_init ─► validate_identity(name,user) ─errors→ stderr, rc 1
                                   │ ok
                                   ▼
                        resolve_dataset_root(None, live_cwd=cwd)  (no bound)
                                   ▼
                        dataset_root/cwd-resolved ─► <root>/<name>.toml + raw/
                                   ▼
                        print absolute config_path   (canonical, CLI-R07)

    MCP:  sofer_init(name,user,cwd) ─► validate_identity ─errors→ _refusal(CONFIG_ERROR)
                                   │ ok
                                   ▼
                  cwd=None → resolve_dataset_root(strict-descendant) ─→ IdentityResolutionError → envelope
                  cwd=str  → _contained_path(cwd, root) ─→ PathOutsideRootError → ToolError
                                   ▼
                        effective_root ─► <eff>/<name>.toml + raw/
                                   ▼
                  envelope += report_identity() ; output_schema += config_path/dataset_root (same change, PB-03)

    Config:  _load_dataset ─► from_toml(path, discovery_root=_get_root()) ─► config.reload(base_dir, stop_at=root)
             (4 sites; _bound_discovery deleted)
    Output:  MCP config-bearing: _contained_path(override, root=cfg._base_dir)
             MCP single-file:    _contained_path(override, root=input.parent)
             CLI single-file:    relative --output → input.parent / override

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/execution_context.py` | Create | Module docstring + `DatasetIdentity` (frozen, `config_path` property, `from_parts`), `validate_identity`, `resolve_dataset_root`, `report_identity`, `IdentityResolutionError`, `_USER_RE` (AGENTS.md rules 1/2/8; imports only stdlib + `model._PLACEHOLDERS`) |
| `src/sofer/model.py` | Modify | `from_toml(cls, path, discovery_root=None)`; L378 → `config.reload(base_dir, stop_at=discovery_root)`; docstring notes the bound |
| `src/sofer/mcp_server.py` | Modify | `sofer_init` L1647-1833: validate→resolve→write; `user_val = user.strip()` (L1727 placeholder fallback deleted); Field descriptions for `user`/`cwd` (L1662/L1668, remove "YOUR_USER placeholder"/"falls back to the server root") + docstring L1674/1687; envelope + `config_path`/`dataset_root` in 3 success branches; output_schema L2098-2108 + 2 string props; `_bound_discovery` def + 4 call sites deleted; 4 `from_toml` sites gain `discovery_root=_get_root()`; 9 output-anchor `root=` swaps |
| `src/sofer/cli.py` | Modify | `_cmd_init`: import execution_context, validate first (exit 1, stderr per error), `dataset_root = resolve_dataset_root(None, live_cwd=Path.cwd().resolve())`, `output = dataset_root / f"{name}.toml"`, `raw_dir_path = dataset_root / config.RAW_DIR`, `user_val = args.user`, absolute `print(f"  OK  Created {output}")` (L841-858 and the 4 move-existing branches use the same resolved paths); argparse `--user` → `required=True` + help text (L1301-1309); single-file `--output` anchoring (L219, L292, L361) |
| `README.md`, `README_ES.md` | Modify | `init <name>` row (L318/330) and `--user` row (L348/360): remove "default: `YOUR_USER` placeholder", state required `--user`, pre-write rejection, absolute `config_path` print — mirrored in both files same commit (rule 13) |
| `tests/conftest.py` | Modify | Second module-scoped fixture `mcp_stdio_parent_root` (PB-09): `tmp_path_factory.mktemp("mcp-stdio-parent")` + `(parent / "child").mkdir()` → `McpStdioServer(cwd=parent)`; reuses the existing dataclass (no new class) |
| `tests/test_execution_context.py` | Create | `validate_identity`/`resolve_dataset_root`/`report_identity`/`DatasetIdentity` unit matrix (below) |
| `tests/test_mcp_server.py` | Modify | Flips (below) + mechanical user/cwd sweep + new unsafe-name cases (`a/../b`, quotes, newline, control char) in `TestInitTraversal` + new envelope-identity assertion + `test_force_true_overwrites` L2300-2302 expected template user |
| `tests/test_mcp_schema.py` | Modify | New assertion: `sofer_init` output_schema declares `config_path`/`dataset_root` (string props, not in `required`) |
| `tests/test_mcp_process.py` | Modify | `TestRecoveryInit` L162-206 (user + expected template), `TestNestedCwd` L113 (user+cwd), greenfield L262 (cwd), new `TestParentRootIdentity` real-process class |
| `tests/test_cli.py` | Modify | Flips L117/L187 (below) + user additions in `TestInitCommand` + new pre-write rejection tests (placeholder, unsafe, missing-user rc 1/rc 2) |

## Interfaces / Contracts

```python
# src/sofer/execution_context.py (new)
@dataclass(frozen=True)
class DatasetIdentity:
    name: str
    user: str
    dataset_root: Path          # absolute, resolved
    @property
    def config_path(self) -> Path: ...        # dataset_root / f"{name}.toml"
    @classmethod
    def from_parts(cls, name: str, user: str, dataset_root: Path) -> "DatasetIdentity": ...

class IdentityResolutionError(Exception): ... # "…pass cwd=<dataset dir>…" message

def validate_identity(name: str | None, user: str | None) -> list[str]: ...
def resolve_dataset_root(
    cwd: str | Path | None, *, live_cwd: Path, server_root: Path | None = None
) -> Path: ...
def report_identity(identity: DatasetIdentity) -> dict[str, str]: ...
```

```python
# model.py
@classmethod
def from_toml(cls, path: str | Path, discovery_root: Path | None = None) -> DatasetConfig: ...
#   config.reload(base_dir, stop_at=discovery_root)   # was reload(base_dir)
```
Error surfaces kept distinct: `IdentityResolutionError` → MCP envelope (`CONFIG_ERROR`) / CLI exit 1; `PathOutsideRootError` (str-cwd escape) → ToolError at boundary — unchanged from today.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `validate_identity` matrix | `tests/test_execution_context.py`: valid pair → `[]`; missing/blank name/user (None, `""`, `"   "`) → non-empty errors; placeholder `YOUR_USER`/`Your_User`/`your-username`; separators `a/b`, `a\\b`; drive `C:/evil` (`ntpath.splitdrive`); exact `.`/`..`; quotes; newline/control; leading/trailing space; user regex rejects `user.name`/`user name`; user regex accepts `user-org`/`user_org` |
| Unit | `resolve_dataset_root` matrix | no-bound (CLI) → live resolved; strict-descendant inside → live; `live == root` → `IdentityResolutionError` naming `cwd`; live outside → same; explicit-cwd contained → path; explicit-cwd escape → `IdentityResolutionError` (mode (b) is unit-matrix-only per S7); `report_identity`/`from_parts` invariants |
| Unit | TC-05 `from_toml(discovery_root=…)` bound (Finding 6) | `tests/test_model.py` with the conftest `pytree` fixture: `pyproject.toml` with `[tool.sofer]` ABOVE `discovery_root` and one INSIDE it → `DatasetConfig.from_toml(path, discovery_root=…)` applies only at-or-below values (tool-config/spec.md:17-21); omitted bound stays unbounded (TC-05 first scenario) |
| Boundary (in-process) | flips + identity envelope | `test_cwd_none_back_compat` → `test_cwd_none_fails_closed` (ok:False, `cwd` named, no parent TOML); `test_auto_cwd_outside_fallback` → `test_auto_cwd_outside_fails_closed`; `test_auto_cwd_inside_root` survives (strict-descendant, +user); **`test_default_user_placeholder` (L2199-2204) repurposed as an MCP-boundary refusal** (Finding 1): `sofer_init(name="my-ds")` with no user → envelope ok:False, error_code CONFIG_ERROR, error mentions user, **no `my-ds.toml` and no `raw/`** (INIT-05 scenario, mcp-server/spec.md:23-27); new envelope assert: absolute `config_path`/`dataset_root` on success |
| Boundary (in-process) | unsafe-name rejection path | The 4 traversal tests (L2245-2263) flip from `ToolError` to **envelope refusals** (Finding 3b): validate-first bans separators/drives before `_contained_path`, so `../evil`/`/abs/evil`/`C:/evil` → ok:False, CONFIG_ERROR, no file; add the newly-covered INIT-05 cases (`a/../b`, quotes, newline, control char) as envelope refusals with no-write asserts |
| Boundary (schema) | output_schema projection | test_mcp_schema.py: `sofer_init` schema declares `config_path`/`dataset_root` (PB-03); envelope carries them in the same change |
| Boundary (in-process) | MSP-R10 output re-anchoring success (Finding 5) | New test (test_mcp_server.py): `build_server(root=tmp_path)`, dataset at `proj/dataset.toml`, `sofer_prepare(config="proj/dataset.toml", output_dir="build")` → package written under `<root>/proj/build`, NOT `<root>/build` (mcp-server/spec.md:171-175) |
| E2E (real process) | PB-04 parent-root reproduction | `TestParentRootIdentity` (test_mcp_process.py) with `mcp_stdio_parent_root` fixture: (a) cwd omitted → input-required refusal naming `cwd`, no `parent/test.toml`, no parent `raw/`; (b) `cwd="child"` → `child/test.toml` + `child/raw/` exist, `parent/test.toml` absent, envelope reports absolute `config_path`/`dataset_root` |
| Boundary (CLI) | `--user` required + rejection + canonical print | `run_cli(["init", "myds"], cwd=…)` → rc 2, stderr names `--user`, no TOML (PB-02 subprocess); `run_cli(["init", "myds", "--user", "YOUR_USER"])` → rc 1, no file; `run_cli(["init", "a/../b", "--user", "u"])` → rc 1; **success-path print test (Finding 2)**: `run_cli(["init", "myds", "--user", "alice"], cwd=tmp_path)` → rc 0 AND stdout contains the absolute resolved `config_path` `str(tmp_path.resolve() / "myds.toml")` (cli/spec.md:95-99 — no existing test greps `Created`) |

**Intentional flips** (assertion inversions, not regressions; verify-report re-baselines) — the named 5 **plus** 6 additional sites the gate review surfaced:

*Named flips (proposal's 4 + recovery pair):*
1. `tests/test_cli.py:117` `test_init_content_is_valid_toml` — was `repo_id == "YOUR_USER/test-ds"` (no user) → now `user="alice"` + `repo_id == "alice/test-ds"` (template-validity intent preserved).
2. `tests/test_cli.py:187` `test_init_default_user_placeholder` — placeholder default deleted → replaced by missing-`--user` rejection tests (handler rc 1 + subprocess rc 2), no TOML written.
3. `tests/test_mcp_server.py:2399-2409` `test_cwd_none_back_compat` — was parent-root write → now fail-closed refusal (no parent TOML).
4. `tests/test_mcp_server.py:2521-2534` `test_auto_cwd_outside_fallback` — was silent parent fallback → now fail-closed refusal (no parent TOML).
5. `tests/test_mcp_process.py` `TestRecoveryInit` L162-206 — both replay tests: calls gain `user`/`cwd`; expected template flips from `_INIT_TEMPLATE.format(name=…, user="YOUR_USER")` to `user="testuser"` (L183, L205).

*Gate-review additions:*
6. `tests/test_mcp_server.py:2199-2204` `test_default_user_placeholder` — **repurposed** as the MCP-boundary placeholder-refusal test (Finding 1): no user → envelope ok:False + CONFIG_ERROR naming user, NO `my-ds.toml`, NO `raw/` (INIT-05, mcp-server/spec.md:23-27).
7. `tests/test_cli.py:22-27` `TestParser.test_init_command` — `parse_args(["init", "my-dataset"])` now raises `SystemExit(2)` under `--user required=True` (Finding 3a): pass `--user alice` to keep the parse assertion, or assert the SystemExit; add a sibling parser test for the required flag.
8. `tests/test_mcp_server.py:2245-2263` the 4 traversal tests (`../evil`, `/abs/evil`, `C:/evil`, client-raises) — validate-first turns them from `ToolError` into **envelope refusals** (Finding 3b); keep the no-write intent, assert ok:False + CONFIG_ERROR + no file.
9. `tests/test_mcp_server.py:2157`, `2170-2172`, `2300-2302` — template-content assertions embedding `user="YOUR_USER"` (Finding 3c: `test_creates_toml_and_raw`, `test_client_call_creates_toml`, `test_force_true_overwrites`): calls gain `user`+`cwd`, expected `_INIT_TEMPLATE.format(..., user="testuser")` (the named "6th site" was L2300-2302; L2157/L2170-2172 are the hidden 3rd/4th template flips).

*Mechanical sweep (assertions untouched, ~43 sites, D11):* every remaining `sofer_init` call in test_mcp_server.py L2154-2646 and test_mcp_process.py L113/170/174/181/195/203/262 gains `"user": "testuser"` + explicit `cwd` — including L2422-2429 and L2641-2646, which keep their `ToolError` expectations only because the sweep adds user before the cwd branch (D5 reconciliation). The `next: {}` on cwd=None refusals is deliberate (S8): the recovery contract keys off hint VALUES, and no mechanical hint value fits a caller-specific `cwd` — the message names the required argument instead.

Counts: baseline 1270 passed + 2 skipped; flips replace/repurpose tests (+~12 new tests: unit matrix, schema, output-anchoring, real-process pair, CLI print) — verify phase re-baselines.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable-file classification or doc-path execution introduced | — | — |
| Git repository selection | N/A — no git invocation; identity is path-based only | — | — |
| Commit state | N/A — no commit/index interaction | — | — |
| Push state | N/A — HF publish/auth unchanged (out of scope) | — | — |
| PR commands | N/A — no PR automation | — | — |

Process integration: the only new subprocess surface is the **test-side** real-process stdio spawn via the established `McpStdioServer`/`StdioServerParameters` mechanism (no shell, fixed `python -c` args) — follows the existing PB-09 lean-spawn pattern, no new adversarial surface in production code.

## Migration / Rollout

No data migration. Rollback (proposal § rollback): revert the merge commit on `dev` — restores `_bound_discovery`, the old INIT-02 back-compat behavior, the old envelope/schema, and the 4 flipped tests; spec deltas are destructive MODIFIED (plain replace at archive). Behavior-change note: deployments where server root == dataset root now fail closed on `cwd=None` (decision #1) — documented, caller passes `cwd=root` explicitly.

## Verification Plan

1. `uv run pytest tests/ -q` → re-baselined count (flips + additions), all green.
2. `uv run mypy src/` → clean (execution_context typed; tests excluded by mypy config).
3. `uv run ruff check src/ tests/` + `uv run ruff format --check src/ tests/` → clean.
4. `git diff --check` → clean.
5. README/README_ES in the same commit (rules 7, 13); no `SOFER_TRACE.md` touch (PB-08).
Changed-line forecast: production ~150-200 + tests ~250-300 (the ~43-site sweep is the driver, Finding 4) + README → **~500-650 total — 400-line budget risk: HIGH**. Tasks phase MUST recommend chained/stacked PRs (e.g. slice 1: execution_context + model + unit tests; slice 2: MCP adapter + boundary tests; slice 3: CLI + README + CLI tests; slice 4: real-process stdio fixture + process tests) or an explicit `size:exception` decision per sdd-phase-common §E.

## Open Questions

None — decisions 1-2 (strict-descendant edge, CLI `--user` required) were pre-approved in the proposal; this design reconciles them with the spec verbatim.