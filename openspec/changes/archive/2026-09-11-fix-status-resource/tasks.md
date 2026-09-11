# Tasks — `2026-09-11-fix-status-resource` (issue #146)

Issue **#146 ONLY**: register ONE static `sofer://status` posture resource so `resources/list` is never empty (today all 3 registered resources are URI templates, listed only under `resources/templates/list`). MODIFIED `MSP-R07` only — no ADDED/REMOVED requirements; requirement `10.8` (#145) and `APX-01` (#144) are canonical and must NOT be re-added or touched here.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~250–300 (implementation ~40 in `src/sofer/mcp_server.py`; tests ~210–260 in `tests/test_mcp_server.py`) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

## Phase 0 — Baseline evidence (read-only; NO edits, NO commits)

- [x] Record the git state: `git rev-parse --abbrev-ref HEAD` == `fix/146-status-resource`; `git log -1 --oneline` HEAD sha (`d73c59a Merge pull request #159 from emiliodavola/fix/145-auth-status-posture`); `git status --porcelain` shows no uncommitted changes to `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, or the canonical `openspec/specs/mcp-server/spec.md` (only the untracked change root dir). <!-- sdd-owner: implementation -->
- [x] Re-measure the FULL baseline suite: run `uv run pytest tests/ -q` and record the **literal** totals shown (expected environment baseline per mandate: 1489 passed / 6 skipped — report what the run actually prints, never an estimate). <!-- sdd-owner: implementation -->
- [x] Linter/mypy baseline green: `uv run ruff check src/sofer/mcp_server.py tests/test_mcp_server.py` and `uv run mypy src/` both exit 0 before any edit. <!-- sdd-owner: implementation -->
- [x] Snapshot the anchors read-only (verify, do not modify): `_register_resources` verified (3 template registrations + `{name*}` rest-pattern docstring); handler `_resource_status` absent (grep exit 1); `sofer://status` absent (grep exit 1); posture globals confirmed; envelope keys confirmed at 1886-1896. <!-- sdd-owner: implementation -->
- [x] Roster/workflow count check: `TestToolRoster::test_exactly_fourteen_callables` expects 14 tools; `len(workflow.WORKFLOW_METADATA)` == **14** (verified via uv run python); `TestResources` currently holds **9** tests (tasks said 8 — stale count; gate is no-touch, 9 before == 9 after) and no `TestStatusResource` class exists (collect count 0). <!-- sdd-owner: implementation -->

## Phase 1 — Implementation (`src/sofer/mcp_server.py` ONLY)

- [x] Add handler `_resource_status() -> dict[str, Any]` directly before `_register_resources` (after `_resource_metadata`, ~line 2695). Body is pure global reads ONLY — `{"approval_configured": _APPROVAL_PHRASE is not None, "phrase_source": _PHRASE_SOURCE, "root": str(_get_root()), "version": _SERVER_VERSION, "started_at": _SERVER_STARTED_AT, "tool_count": len(workflow.WORKFLOW_METADATA)}` — exactly six keys. Docstring: JSON posture object, zero side effects, zero network, no `_tool_execution()`/`_capture_output()` wrapper, never contains the phrase or any phrase-derived value (same NEVER-LEAK contract as the `sofer_auth_status` posture fields). NO new imports. Verify: `uv run python -c "import sofer.mcp_server"` imports clean; `git diff src/sofer/mcp_server.py` shows only the added function so far. <!-- sdd-owner: implementation -->
- [x] Register the static resource: inside `_register_resources`, AFTER the three `server.resource(...)` template calls (after line 2713), add `server.resource("sofer://status", description=<concise static-resource description>)` applied to (not wrapping) `_resource_status` — URI has NO `{name}`/`{name*}` path variables, so FastMCP lists it under `resources/list`, not `resources/templates/list`. Update the `_register_resources` docstring first line to read "3 resource templates + 1 static status resource (MSP-R07)" and describe the static resource's placement rationale. Verify: string `sofer://status` present exactly once as a URI; no `{`/`}` in it; registration sits after the 3 templates inside the function; `uv run python -c "import sofer.mcp_server"` still imports clean. <!-- sdd-owner: implementation -->

## Phase 2 — Tests (`tests/test_mcp_server.py` ONLY, class `TestStatusResource` placed after `TestResources`)

- [x] Add `test_status_resource_listed` (scenario: Static status resource listed with posture content): build server with `approval_phrase="phrase123"` via existing `_make_dataset(tmp_path)` + `build_server(root=tmp_path, approval_phrase="phrase123")` pattern; assert `resources/list` is non-empty and includes `sofer://status`; assert `resources/templates/list` does NOT include it and still lists the 3 URI templates; read via `Client(server).read_resource("sofer://status")` (`_run(...)` helper) and assert `contents[0].text`. <!-- sdd-owner: implementation -->
- [x] Add `test_status_resource_content_explicit` (same scenario): `json.loads(contents[0].text)` yields exactly the six keys `approval_configured|phrase_source|root|version|started_at|tool_count`; `approval_configured is True`, `phrase_source == "explicit"`, `root` equals the resolved build root (consistency with `sofer_init`'s absolute path semantics), `version == get_version()` non-empty, `started_at` matches regex `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00`, `tool_count == len(workflow.WORKFLOW_METADATA)` (import sofer.workflow; never a hardcoded count). <!-- sdd-owner: implementation -->
- [x] Add `test_status_resource_consistent_with_auth_status` (scenario: Status posture consistent across surfaces): one build with `approval_phrase="phrase123"` AND `SOFER_MCP_APPROVAL_PHRASE` set (explicit wins), plus an env-only build (`build_server(root=tmp_path)` with env set → `"env"`); compare payload vs `_envelope(server, tmp_path)` from `sofer_auth_status`: `approval_configured`/`phrase_source` equal, `started_at == envelope["server_started_at"]`, `version == envelope["server_version"]` — one fact source, two surfaces. <!-- sdd-owner: implementation -->
- [x] Add `test_status_resource_no_phrase_leak` (same scenario, NEVER-LEAK): use `_clean_hf(monkeypatch)`; build with `approval_phrase="phrase123"` and env value `"envphrase456"` configured; serialize the payload (`json.dumps`); assert neither `"phrase123"` nor `"envphrase456"` nor either value's `hashlib.sha256(...).hexdigest()` appears in the serialized text (mirror the existing probe at tests/test_mcp_server.py:387; do NOT probe bare prefix "phrase" — it is a substring of `phrase_source`). <!-- sdd-owner: implementation -->
- [x] Add `test_status_resource_unconfigured_invariant` (same scenario): hermetic `_clean_hf(monkeypatch)`; across unconfigured paths — (a) no arg + env deleted, (b) env `""`, (c) env `"   "`, (d) blank explicit `approval_phrase=""` with env set — assert `phrase_source == "none"` ⟺ `approval_configured is False` and `phrase_source` ∈ `{"env","explicit","none"}` for every case. <!-- sdd-owner: implementation -->
- [x] Add `test_status_resource_hermetic_deterministic` (zero-side-effect clause of the same scenario): two successive reads return byte-identical `contents[0].text`; no file is created under the root by the read (assert like `test_codebook_resource_generates_on_demand`'s no-write check); reading does not mutate posture state (`started_at` stable across reads within one build). <!-- sdd-owner: implementation -->

## Phase 3 — Evidence (verification of the whole change)

- [x] Full suite: `uv run pytest tests/ -q` — record the **literal** new totals (expect the Phase 0 baseline + 6 new `TestStatusResource` tests; report what the run prints). <!-- sdd-owner: implementation -->
- [x] Scoped runs: `uv run pytest tests/test_mcp_server.py -k TestStatusResource -q` → 6 passed; `uv run pytest tests/test_mcp_server.py -k TestResources -q` → exactly the preexisting tests, unchanged (no-touch gate on `TestResources`); `uv run pytest tests/test_mcp_server.py -k TestToolRoster -q` → roster stays 14 (`test_exactly_fourteen_callables`). <!-- sdd-owner: implementation -->
- [x] Lint + format: `uv run ruff check src/ tests/` green; `uv run ruff format src/sofer/mcp_server.py tests/test_mcp_server.py` then re-check (`ruff check` still green, zero diffs from format); `uv run mypy src/` green; `git diff --check` clean. <!-- sdd-owner: implementation -->
- [x] No-touch gate: `git status --porcelain` shows ONLY `src/sofer/mcp_server.py` and `tests/test_mcp_server.py` modified — nothing else (no `TRACE.md`, `scratch/`, `.gitignore`, `README.md`/`README_ES.md`, `pyproject.toml`, `src/sofer/workflow.py`, `src/sofer/cli.py`, canonical `openspec/specs/mcp-server/spec.md`, no `10.8`/`APX-01` additions); confirm `sofer_auth_status` and its `_envelope`/hints behavior are untouched by the diff. <!-- sdd-owner: implementation -->
- [x] Scenario→test map verification: all 5 spec-delta scenarios covered — 3 verbatim-kept scenarios pinned to the unmodified existing `TestResources` tests, 2 new GWT scenarios pinned to `TestStatusResource` (listed/content → `..._listed` + `..._content_explicit`; consistent/no-leak/invariant → `..._consistent_with_auth_status` + `..._no_phrase_leak` + `..._unconfigured_invariant`, plus `..._hermetic_deterministic` for the zero-side-effect clause). Record the mapping in the commit message or PR body. <!-- sdd-owner: implementation -->

## Phase 4 — Parent-owned: commit + PR (lifecycle gate)

- [ ] Commit the two-file change as ONE work unit (implementation + tests + docstrings-in-code) with a conventional message; pre-commit hooks (ruff --fix, ruff-format, mypy src/) must pass on commit — never `--no-verify`. <!-- sdd-owner: parent -->
- [ ] Push `fix/146-status-resource` to origin and open a PR targeting `dev` ONLY using `.github/PULL_REQUEST_TEMPLATE.md` (fill every section; Verification section contains actual command output: full pytest literal totals, scoped runs, ruff/mypy, `git diff --check`; SDD artifacts section references this change). NEVER push to `main` or `dev` directly; NO tag, NO release, NO version/CITATION bump. <!-- sdd-owner: parent -->
- [ ] Post-apply bounded review of the open PR: scenario→test map complete, no-touch declarations hold, literal test totals quoted, diff stays within ~300 lines, `resources/templates/list` still lists the 3 templates and `resources/list` is non-empty with `sofer://status`. <!-- sdd-owner: parent -->