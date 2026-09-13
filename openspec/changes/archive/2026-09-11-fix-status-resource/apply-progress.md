# Apply Progress — `2026-09-11-fix-status-resource` (issue #146)

Branch `fix/146-status-resource` (base `dev`; #144+#145 merged). Scope: ISSUE #146 ONLY —
register ONE static `sofer://status` posture resource so `resources/list` is never empty.

## Status consumed

- Native SDD status: `applyState: ready`, 18/18 implementation tasks, 3 parent-owned
  lifecycle actions deferred (commit / PR / post-apply review). `nextRecommended: sdd-apply`.
- `actionContext`: mode `repo-local`, allowedEditRoots `[C:\Users\elaze\Desktop\sofer]`, no warnings.
- Review Workload Forecast: `Decision needed before apply: No`, `Chained PRs recommended: No`,
  `400-line budget risk: Low`, chain strategy `pending` → no delivery decision required.
- `strict_tdd: false` (standard mode; no TDD evidence table required).

## Completed tasks (11 of 13 under design; 18/18 implementation rows total)

All 18 implementation-owned rows in `tasks.md` are now `- [x]`. Checkboxes were updated in the
persisted `openspec/changes/2026-09-11-fix-status-resource/tasks.md` immediately after each phase:

- **Phase 0 (5)**: git state recorded; full baseline **1495→1489 before edits** is 1489 passed /
  6 skipped (literal); ruff+mypy baseline green; anchors verified (`sofer://status` and
  `_resource_status` absent pre-edit, envelope keys at 1886-1896); `len(workflow.WORKFLOW_METADATA)` == 14.
- **Phase 1 (2)**: `_resource_status()` handler added before `_register_resources`; static
  `server.resource("sofer://status", description=...)` registered after the 3 templates;
  docstring updated to "3 resource templates + 1 static status resource (MSP-R07)".
- **Phase 2 (6)**: `TestStatusResource` class (6 tests) added after `TestResources`.
- **Phase 3 (5)**: full suite, scoped runs, lint+format+mypy+diff-check, no-touch gate,
  scenario→test map (below).

## Files changed

| File | Change | Scope guard |
|---|---|---|
| `src/sofer/mcp_server.py` | `_resource_status()` (6-field pure-global-read dict) + registration in `_register_resources` (after the 3 templates) + docstring first line + static-resource rationale paragraph | `sofer_auth_status`/envelope/hints/imports/globals/`build_server`/3 templates byte-identical; +45/−2 |
| `tests/test_mcp_server.py` | `import json`, `from sofer import workflow`, `class TestStatusResource` (6 tests) | Purely additive (+182); `TestResources` (9) and `TestToolRoster` (3) untouched |
| `openspec/changes/2026-09-11-fix-status-resource/tasks.md` | checkboxes → `[x]` for 18/18 implementation rows | Parent rows (3) preserved byte-for-byte, unchecked |
| `openspec/changes/2026-09-11-fix-status-resource/apply-progress.md` | this file | — |

## Test commands run (literal output)

- Baseline full suite (pre-edit): `uv run pytest tests/ -q` → **1489 passed, 6 skipped, 13 warnings in 54.62s**
- Final full suite (post-format): `uv run pytest tests/ -q` → **1495 passed, 6 skipped, 13 warnings in 44.30s**
  (= baseline 1489 + 6 new `TestStatusResource`; matches the expected delta exactly)
- Scoped: `uv run pytest tests/test_mcp_server.py -k TestStatusResource -q` → **6 passed**
- Scoped: `uv run pytest tests/test_mcp_server.py -k TestResources -q` → **9 passed** (unchanged pre/post — no-touch)
- Scoped: `uv run pytest tests/test_mcp_server.py -k TestToolRoster -q` → **3 passed** (roster stays 14)
- Combined scoped (post-format): `-k "TestStatusResource or TestResources or TestToolRoster"` → **18 passed**

## Lint / type / diff evidence

- `uv run ruff check src/sofer/mcp_server.py tests/test_mcp_server.py` → exit 0 (baseline)
- `uv run ruff check src/ tests/` → "All checks passed!" (pre- and post-format)
- `uv run ruff format src/sofer/mcp_server.py tests/test_mcp_server.py` → "1 file reformatted, 1 file left unchanged";
  re-check after format: `ruff format --check` → "2 files already formatted" (idempotent, zero diffs from format)
- `uv run mypy src/` → "Success: no issues found in 32 source files"
- `git diff --check` → clean
- `uv run python -c "import sofer.mcp_server"` → `import OK` (after handler + after registration)

## Scenario → test map (all 5 spec-delta scenarios)

| §Spec scenario | Test(s) | Status |
|---|---|---|
| Dataset resource returns raw TOML (verbatim-kept) | `TestResources::test_dataset_resource_raw_toml` | unmodified pin |
| Codebook resource generates on demand (verbatim-kept) | `TestResources::test_codebook_resource_generates_on_demand` | unmodified pin |
| Metadata resource when present (verbatim-kept) | `TestResources::test_metadata_resource_when_present`, `test_metadata_missing_clear_error` | unmodified pins |
| Static status resource listed with posture content (new) | `TestStatusResource::test_status_resource_listed` (resources/list non-empty incl. `sofer://status`; templates/list excludes it and still lists the 3 URI templates; `contents[0].text` non-empty) + `test_status_resource_content_explicit` (exactly the 6 keys; `approval_configured is True`; `phrase_source=="explicit"`; `root==str(tmp_path.resolve())`; `version==get_version()`; `started_at` regex ISO-8601 UTC µs; `tool_count==len(workflow.WORKFLOW_METADATA)`) | new |
| Status posture consistent across surfaces and free of secret material (new) | `test_status_resource_consistent_with_auth_status` (payload ≡ `sofer_auth_status` envelope: `approval_configured`/`phrase_source`/`started_at`==`server_started_at`/`version`==`server_version`; explicit-wins + env-only builds) + `test_status_resource_no_phrase_leak` (json.dumps serialized: `phrase123`/`envphrase456` and both sha256 hexdigests absent; exact 6-key set) + `test_status_resource_unconfigured_invariant` (a) no-arg+env deleted, (b) env `""`, (c) env `"   "`, (d) blank explicit with env set → `"none"` ⟺ `False` on every row; `phrase_source` domain) | new |
| Zero-side-effect clause (same scenario) | `test_status_resource_hermetic_deterministic` (two reads byte-identical; rglob before==after — nothing written; `started_at` stable) | new |

## Deviations from design

1. **`TestResources` count is 9, not 8** (tasks.md) / 7 (design.md §6): the artifact counts were stale —
   the pre-edit file holds 9 tests. The no-touch gate holds by construction: the tests diff is purely
   additive (`git diff -U0` shows zero `-` content lines; `@@ -1644,0 +1647,180 @@ class TestResources:` is
   a pure insertion hunk after the class). Scoped `-k TestResources` = 9 passed before and after.
2. **No `test_status_resource_static_not_template`** (design §6 mentioned it as a 7th "~6 per spec"
   test). tasks.md — the authoritative apply artifact — choreographs exactly 6 tests with
   `test_status_resource_hermetic_deterministic` as the 6th; the static-not-template clause is asserted
   behaviorally inside `test_status_resource_listed` (`sofer://status` ∉ template URIs; the 3 templates
   still listed). Followed tasks.md: 6 tests, matching the "6 new tests" full-suite delta.
3. **`r.uri` is `AnyUrl`, not `str`**: fastmcp v3 client returns `Resource.uri` as `AnyUrl`
   (a `str` subclass); the list assertion converts with `str(r.uri)`. One-line test-side adaptation,
   no handler change.
4. Handler docstring wording: the task mandate says the docstring must state the never-leak contract and
   zero side effects — mirrored from the design D1 docstring (which referenced MSP-R13 for tool_count;
   kept, as task text names `workflow.WORKFLOW_METADATA` and design D3 names MSP-R13).

## Remaining tasks (parent-owned, preserved byte-for-byte in tasks.md Phase 4)

- `- [ ] Commit the two-file change as ONE work unit ... <!-- sdd-owner: parent -->`
- `- [ ] Push fix/146-status-resource to origin and open a PR targeting dev ONLY ... <!-- sdd-owner: parent -->`
- `- [ ] Post-apply bounded review of the open PR ... <!-- sdd-owner: parent -->`

## Workload / PR boundary

- Diff: `src/sofer/mcp_server.py +45/−2`, `tests/test_mcp_server.py +182/−0` → **227 insertions, 2 deletions**
  (~225 net lines vs the ~250-300 forecast; well under the 400-line budget). Single PR (chain strategy
  `pending`; `Chained PRs recommended: No`). No `size:exception` requested.
- No commits made, no push (parent-owned). Working tree: only the 2 intended files modified +
  the untracked change root.

## Risks

- **None new.** R1 (phrase leak) mitigated by construction + guard test incl. sha256 probes; R3 (surface
  drift) pinned by the cross-surface test; R5 (fastmcp v3 static/JSON semantics) resolved — the only
  surprise was `AnyUrl` on `list_resources`, adapted in the test.
- Residual (accepted in design §9 R2): `root` full-path exposure in the payload is by design (INIT-03-consistent).