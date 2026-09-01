# Tasks: Registered MCP and CLI process-boundary regression suite

## Review Workload Forecast

Estimated changed lines: ~1,100–1,400 (design forecast).
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

Slices 1 (270–500) and 2 (450–550) each brush/exceed the 400-line guard, so both split into two PRs; `mcp-config-states/` fixtures move to PR 3 for slice-2 independence.

Forecast note (PR 3 planning): PR 2 landed at 436 changed lines (260 insertions + 168 deletions) vs the ~250–350 forecast — a 1.25–1.7× miss; plan later slices against the upper bound of each range or higher.

### Suggested Work Units (feature-branch-chain on `test/mcp-cli-regression-suite`)

| Unit | Goal | PR | Base |
|------|------|----|------|
| 1 | Conftest fixtures + `_unwrap` delegation | PR 1 | tracker (~180–220) |
| 2 | Direct-call→Client conversions | PR 2 | PR 1 (~250–350) |
| 3 | `mcp-config-states/` + stdio/CWD/recovery | PR 3 | PR 2 (~280–360) |
| 4 | Config states + handoff | PR 4 | PR 3 (~230–280) |
| 5 | test_cli subprocess + CI comment | PR 5 | PR 4 (~130–170) |

Retarget/rebase child PRs showing parent-slice changes.

## Phase 1: Shared boundary fixtures (PR 1)

- [x] 1.1 Add `mcp_payload(result)` Root-unwrap to `tests/conftest.py` (ported from `_unwrap`), typed (PB-09/07).
- [x] 1.2 Add `run_cli(argv, *, cwd, env=None, encoding="utf-8")` — spawns `[sys.executable, "-m", "sofer.cli", ...]` (PB-02).
- [x] 1.3 Add module-scoped `mcp_stdio_server`: one `main()` stdio spawn per module (PB-09).
- [x] 1.4 `test_mcp_server._unwrap` delegates to `mcp_payload` (D2).
- [x] 1.5 Gate: full pytest, ruff, mypy, `git diff --check`; `SOFER_TRACE.md` untouched (PB-07/08).

## Phase 2: Route registered tools through Client(server) (PR 2)

- [x] 2.1 Convert ~22 `sofer_publish_confirm` direct calls in `tests/test_mcp_server.py` to `_call(server, ...)` + unwrap (PB-01).
- [x] 2.2 Convert ~16 `sofer_init` direct calls to `_call(server, ...)` (PB-01).
- [x] 2.3 Convert remaining direct `sofer_validate` calls; drop unused imports (PB-01).
- [x] 2.4 `test_mcp_schema.py`: convert direct validate/publish_confirm calls; route `test_offline_happy_path` via `Client(server)`, keep `_api` mock + `HF_TOKEN` (PB-01/06).
- [x] 2.5 Gate: no new boundary-hiding direct calls (PB-01); count not regressed (PB-07).

## Phase 3: Process module — stdio, CWD, recovery (PR 3)

- [x] 3.1 Create `tests/fixtures/mcp-config-states/{empty,malformed}.toml`, out of `mcp-happy-path/` (PB-04).
- [x] 3.2 Stdio framing: `initialize → tools/list (14) → tools/call`; clean JSON-RPC, no stray stdout (PB-01).
- [x] 3.3 Nested CWD: `build_server(parent)` + `chdir(nested)`; init lands under nested — assert paths (PB-04).
- [x] 3.4 Recovery: publish_confirm refusal → replay `next` → past risk gate (PB-03).
- [x] 3.5 Recovery: init refusals (file-exists/name-empty) → replay → intended branch (PB-03).
- [x] 3.6 Gate: focused `test_mcp_process.py`, then full suite + ruff + mypy + `git diff --check` (PB-07); win32 skips reuse `_make_link` (D6).

## Phase 4: Process module — config states + handoff (PR 4)

- [ ] 4.1 Empty config: validate via client → documented empty-config result (PB-04).
- [ ] 4.2 Existing config: happy-path TOML validates without re-registration (PB-04).
- [ ] 4.3 Greenfield + triage: init → scan_apply → validate passes; scan_dry_run lists, copies nothing, TOML unchanged (PB-04).
- [ ] 4.4 Malformed: validate via client → refusal with `config_errors` (PB-04).
- [ ] 4.5 Handoff: validate→prepare→codebook→profile→render→publish(dry)→publish_confirm; `_api` mocked + `HF_TOKEN`; reaches upload (PB-04/06).
- [ ] 4.6 Gate: suite passes without `HF_TOKEN` (PB-06); full gates (PB-07/08).

## Phase 5: CLI subprocess + CI + final gates (PR 5)

- [ ] 5.1 Add `TestSubprocessBoundary` to `tests/test_cli.py`: `--help` subprocess → rc 0, lists all subcommands (PB-02).
- [ ] 5.2 cp1252: `PYTHONIOENCODING=cp1252` + `errors="strict"` → rc 0, strict-decodable; no non-cp1252 glyphs; win32-only skips (PB-02).
- [ ] 5.3 Dispatch: unknown command subprocess → argparse rc 2 (PB-02).
- [ ] 5.4 `ci.yml`: comment-only annotation on `uv run pytest -v` as complete gate (PB-05, D7).
- [ ] 5.5 Final gate: full pytest (count stable) + ruff + mypy + `git diff --check`; `SOFER_TRACE.md` untracked/unstaged (PB-07/08); one spawn per module (PB-09).