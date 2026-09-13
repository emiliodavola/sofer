# Archive Report — 2026-09-11-fix-status-resource

**Change**: `2026-09-11-fix-status-resource`
**Issue**: GitHub **#146 ONLY** (enhancement) — static `sofer://status` posture resource so `resources/list` is never empty (all 3 pre-existing resources were URI templates, listed only under `resources/templates/list`)
**Date**: 2026-09-11
**Artifact store**: `openspec` (repo-local; `config.yaml` header says "hybrid (openspec + engram)" but the native status resolved `artifactStore: openspec` and the openspec store is authoritative — no Engram observation IDs for this change; **none performed or claimed**)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and not yet opened as a PR** — see *Delivery*)
**Verify verdict**: **PASS** — `gentle-ai.verify-result/v1`, `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 0/0` (MODIFIED delta), `scenarios: 5/5`, `test_exit_code: 0`, `build_exit_code: 0`; issue #146 acceptance criteria **3/3**
**Branch**: `fix/146-status-resource` (base `dev`, HEAD `d73c59a` = merge PR #159 from #145) — **0 commits beyond `dev`**; the change is a working-tree diff of 2 files (`src/sofer/mcp_server.py`, `tests/test_mcp_server.py`) plus the already-synced canonical spec merge
**Archived path**: `openspec/changes/archive/2026-09-11-fix-status-resource/`

## Summary

Registers ONE static resource `sofer://status` (no path variables) returning a JSON posture object with exactly six fields —
`approval_configured` (bool), `phrase_source` (`"env"|"explicit"|"none"`), `root` (resolved containment root), `version`
(installed package version, `get_version()`), `started_at` (ISO-8601 UTC µs captured at `build_server`), `tool_count`
(`len(workflow.WORKFLOW_METADATA)` == 14 today, derived never hardcoded) — all read from the #145 posture globals verbatim
(one fact source, two surfaces shared with the `sofer_auth_status` envelope). FastMCP lists a `{}`-free/no-arg-parameter
URI as a **static** resource under `resources/list` (vs. templates under `resources/templates/list`), fixing the issue's
empty-list surprise; the 3 URI templates keep their containment/size-guard semantics unchanged.

Implementation shape (D1–D6 in design.md): handler `_resource_status() -> dict[str, Any]` before `_register_resources`;
registration `server.resource("sofer://status", description=...)(_resource_status)` after the 3 templates; `_register_resources`
docstring updated to "3 resource templates + 1 static status resource (MSP-R07)". Deliberately NOT wrapped in
`_tool_execution()`/`_capture_output()` (pure global reads, nothing prints, no network) and NOT extended with
`_contained_path`/`_check_resource_size` (no path argument, no file read — MSP-R07 containment/size clauses govern
path-bearing resources only). Zero new imports, zero new state, zero config/`pyproject.toml` change, `build_server` untouched.

Diff: **2 files, 227 insertions / 2 deletions (~225 net lines)** measured at verify (`src/sofer/mcp_server.py` +45/−2,
`tests/test_mcp_server.py` +182/−0, pure insertion hunks) — inside the ~250–300 forecast and well under the 400-line
budget; single PR, no chaining, no `size:exception`. Tests: **6 new** in `TestStatusResource` (100 % additive). Full
suite **1495 passed / 6 skipped** vs. baseline **1489 / 6** (+6 exactly).

**No commits were made by this phase** (executor contract: parent versions; change root was untracked — `git mv` not
applicable). Delivery is pending: commit → PR into `dev` → bounded review → human approval/merge.

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (parent mandate: re-applying would regress the
transformed canonical block with `*Tests:*` scaffolding, `(issue #146)` provenance, and `(kept verbatim …)` annotations —
see `sync-note.md` inside this change, archived with it). Archive reads a *completed* sync, it does not perform one.

| Field | Value |
|---|---|
| Domains synced | **`mcp-server`** (1 of 1) |
| ADDED requirements | **none** |
| MODIFIED requirements | **`Resources (MSP-R07)`** — additive amendment in place (ONE static `sofer://status` + never-leak and boundary clauses; the three URI templates and their containment/size-guard semantics unchanged); canonical **line 181**, provenance at **line 183**. Net diff on merge: `35 insertions(+), 1 deletion(-)` (the single deletion is the old two-part provenance line collapsed to one); no requirement added/moved/removed |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical file | `openspec/specs/mcp-server/spec.md` (currently modified in the worktree — that modification *is* the absorbed sync merge, not archive's) |
| Provenance line (re-verified this pass) | `> Added by change \`sofer-mcp-server\` (archived 2026-08-28). Modified by \`2026-09-11-fix-status-resource\` (archived 2026-09-11).` — **archive date 2026-09-11 matches the provenance date, so no amendment was needed** (sync-note.md's conditional does not fire) |
| Counts (canonical, re-verified this pass) | requirement headers **24 → 24** (MODIFIED, not added); scenario headers **90 → 92** (+2 GWT scenarios; MSP-R07 3 → 5 scenarios, canonical scenarios kept verbatim); MSP-R07 occurrences **exactly 1**; `*Tests:*` occurrences **0**; `issue #146` occurrences **0** (canonical carries no issue refs); tabs **0**; trailing-whitespace lines **0**; LF-only; file 802 → **836 lines**, 48495 → **52775 bytes** |
| 10.8 integrity (re-verified this pass) | **byte-intact** — SHA-256 of the 10.8 block (requirement header → EOF, canonical line 454) = `a5c25bcf314fb08ee7f206a10403b49fdb80102bf23cce3b867ec383a4167328`, identical pre/post sync (#145 isolation honored; NOT re-added, NOT touched) |
| APX-01 integrity (re-verified this pass) | **byte-intact** — SHA-256 of the APX-01 block (requirement header → EOF, canonical line 518) = `5291acbb84f98a3c5b319d7f0a2a84513257b9d5099524d5c2a29046c4829aff`, identical to the hash recorded by the #145 sync-note after its merge (#144 isolation honored; NOT re-added, NOT touched) |
| Archive-time sync fallback | **NOT executed and not needed** — the sync was already complete (`sync-note.md` in this change root records it) and the parent prompt explicitly forbade re-application |
| Destructive merge | **Not applicable at archive** — archive performed no merge. The sync-phase merge itself was a MODIFIED-only replacement (35 insertions / 1 deletion, zero canonical requirements dropped, no `## REMOVED` section); `rules.archive`'s *"Warn before merging destructive deltas"* is honored: nothing destructive was merged and nothing was warned for |

**Precedent / where the sync record lives.** This repo has **no `sync-report.md` anywhere** (repo convention; 0 exist),
and it records spec-sync outcomes in the `## Spec Sync` section of `archive-report.md` (precedent:
`2026-09-11-fix-auth-status-hints/archive-report.md`, `2026-09-11-fix-auth-status-posture/archive-report.md`). The sync
phase wrote `sync-note.md` inside the change root as the handoff; `sync-note.md` is archived with the change.

**Delta recorded as-is.** `specs/mcp-server/spec.md` (MODIFIED-only op — MSP-R07 with **5 scenarios**:
3 canonical scenarios kept verbatim + 2 new GWT scenarios) is archived **byte-identical** (**7928 bytes**, 89 lines, no
trailing newline) for the audit record: `## MODIFIED Requirements` → `### Requirement: Resources (MSP-R07)` with
`#### Scenario:` blocks `Dataset resource returns raw TOML` / `Codebook resource generates on demand` /
`Metadata resource when present` (kept verbatim) + `Static status resource listed with posture content` /
`Status posture consistent across surfaces and free of secret material` (new).

**Idempotency (recorded in `sync-note.md`).** The native helper's `applyDeltaSpec` replaces a MODIFIED block by name
(`requireCanonicalBlock` + `replacements`), so a re-application **cannot duplicate** MSP-R07 (canonical re-split after
the merge: 24 blocks, all unique) — but it *would* overwrite the transformed canonical with the raw delta block
(regression: reintroduces `*Tests:*`, the `(issue #146)` provenance form, and `(kept verbatim …)` annotations). The
guard is this note + sync-note.md; archive deliberately did not run `applyDeltaSpec`.

**Active same-domain change warning.** None. `openspec/changes/` contains only `archive/` after the move; `find
openspec/changes -maxdepth 2 -path '*/specs/mcp-server/spec.md' -not -path '*/archive/*'` → **0 results**. This change
was the **only** active change touching domain `mcp-server`; `relationships.sameDomainActiveChanges: []` and
`collisions: []`.

## Verification

| Gate | Result |
|---|---|
| Verify verdict | `pass` — `blockers: 0`, `critical_findings: 0`, `requirements: 0/0`, `scenarios: 5/5` (machine-readable envelope at the head of `verify-report.md`, `evidence_revision: sha256:584da2d6…`) |
| Acceptance criteria (#146) | **3 / 3 PASS** — (1) `resources/list` returns the static resource: independent probe `client.list_resources()` → `{'sofer://status'}` (non-empty), `list_resource_templates()` → exactly the 3 URI templates, `sofer://status` absent (static: no `{}` in URI, no-arg handler); (2) content fields correct and build-time: payload keys == exactly `{approval_configured, phrase_source, root, version, started_at, tool_count}`, `approval_configured is True` (bool), `phrase_source == "explicit"`, `root == str(tmp.resolve())`, `version == get_version()` (`0.1.dev386+g1ad1d177f`, non-empty), `started_at == ms._SERVER_STARTED_AT` (ISO-8601 UTC µs, regex fullmatch), `tool_count == 14 == len(workflow.WORKFLOW_METADATA)` (derived, not hardcoded); (3) unit tests cover registration and content — `TestStatusResource` 6 tests, **6 passed** on `-k TestStatusResource` |
| Verification style | **Independent and adversarial**: verifier re-derived every acceptance signal through fresh client round-trips and re-ran all gates; nothing taken from apply-progress on faith; no-leak probe (explicit `phrase123` + env `envphrase456`) — payload free of both values and both sha256 hexdigests (4/4 assertions True); cross-surface probe with a real `_make_dataset` — resource payload ≡ `sofer_auth_status` envelope (`approval_configured`, `phrase_source`, `started_at` byte-identical to `server_started_at`, `version` identical to `server_version`) |
| Pytest (focused) | `uv run pytest tests/test_mcp_server.py -k TestStatusResource -q` → **6 passed**; `-k TestResources -q` → **9 passed** (unchanged — no-touch); `-k TestToolRoster -q` → **3 passed** (roster stays 14); combined `-k "TestStatusResource or TestResources or TestToolRoster"` → **18 passed** |
| Pytest (full) | `uv run pytest tests/ -q` → **1495 passed, 6 skipped**, 13 warnings in 44.30s (+6 vs baseline 1489/6; 0 skipped delta; no test removed/relaxed) |
| Lint / type / whitespace | `uv run ruff check src/ tests/` → "All checks passed!" · `uv run ruff format --check src/sofer/mcp_server.py tests/test_mcp_server.py` → "2 files already formatted" · `uv run mypy src/` → "Success: no issues found in 32 source files" · `git diff --check` → clean |
| Spec scenario coverage | 5 delta scenarios mapped to tests (AGENTS.md §6): 3 verbatim-kept scenarios pinned to unmodified `TestResources` tests; listed/content → `test_status_resource_listed` + `test_status_resource_content_explicit`; consistent/no-leak/invariant → `test_status_resource_consistent_with_auth_status` + `test_status_resource_no_phrase_leak` + `test_status_resource_unconfigured_invariant`; zero-side-effect clause → `test_status_resource_hermetic_deterministic`. No spec row without a test |
| No-leak / domain audit | payload = 6 fields of pure build-time metadata (bool, enum string, root path, two `_SERVER_*` strings, registry length); `phrase_source` describes the configuration path only, never material; guard test mirrors the pre-existing `:387` probe (sha256 probes incl.) and deliberately does NOT probe the bare prefix "phrase" (substring of `phrase_source`) — correct, not a gap |
| Assertion quality | equality/identity against sources of truth (`get_version()`, `workflow.WORKFLOW_METADATA`, resolved root, `_SERVER_STARTED_AT`), exact key-set equality, fullmatch regex, both-direction invariant, byte-identical reads + rglob no-write check; no tautologies, ghost loops, type-only or smoke-only assertions |
| Strict TDD | **Inactive by configuration** (`openspec/config.yaml` → `strict_tdd: false`); no TDD Cycle Evidence required; assertion-quality audit still performed (advisory) |

## Delivery

| Field | Value |
|---|---|
| Branch | `fix/146-status-resource`, base `dev` (HEAD `d73c59a` = merge PR #159 from #145) — never `main`/`dev` directly |
| Commits | **none** — HEAD is `d73c59a`; `git status --porcelain` at archive = 3 modified tracked files + untracked archived change root. The change is a **working-tree diff** |
| PR | **NOT yet opened** — parent-owned (`tasks.md` Phase 4 rows). Target: `dev`, via `.github/PULL_REQUEST_TEMPLATE.md` with REAL verification output (full pytest literal totals, scoped runs, ruff/mypy, `git diff --check`), the SDD artifacts section (proposal/spec/design/tasks paths + the scenario→test map), and this change's Review Workload Forecast; explicit note: no tag, no release, no version/CITATION bump |
| Merge target | `dev` only; `main` receives changes solely via release-time merges from `dev` |
| Release / tag step | **none** for this change (no version bump — hatch-vcs derives from tags) |
| Review workload | **227 insertions / 2 deletions (~225 net lines) over 2 files** measured at verify — inside the ~250–300 forecast and well under the 400-line budget → **single PR**, no chaining, no `size:exception` |
| PR boundary | issue #146 only: diff touches just `src/sofer/mcp_server.py` (handler + registration + docstring, +45/−2) and `tests/test_mcp_server.py` (pure additions, +182/−0); no README/README_ES, pyproject, workflow.py, cli.py, canonical spec re-edit, tags/releases/version bumps |

**Tasks Phase 4 rows (`sdd-owner: parent`) remain open in the persisted artifact** — parent lifecycle rows
(commit → push + PR → post-apply bounded review). They are **not** implementation tasks and their completion is
outside the archive's authority. Consequently the verified working-tree blobs are the blobs the parent will commit; no
revision was altered by this phase.

## Task Completion Gate

Re-read the persisted tasks artifact immediately before the archive move (now at
`openspec/changes/archive/2026-09-11-fix-status-resource/tasks.md`):

- **`- [ ]` implementation task markers remaining: ZERO.** All **18** implementation-owned rows (Phases 0–3) are `- [x]` (`grep -c "^- \[x\]"` = 18).
- The **3** remaining `- [ ]` rows are **all parent-owned** (`<!-- sdd-owner: parent -->`), reproduced verbatim:

```text
- [ ] Commit the two-file change as ONE work unit (implementation + tests + docstrings-in-code) with a conventional message; pre-commit hooks (ruff --fix, ruff-format, mypy src/) must pass on commit — never `--no-verify`. <!-- sdd-owner: parent -->
- [ ] Push `fix/146-status-resource` to origin and open a PR targeting `dev` ONLY using `.github/PULL_REQUEST_TEMPLATE.md` (fill every section; Verification section contains actual command output: full pytest literal totals, scoped runs, ruff/mypy, `git diff --check`; SDD artifacts section references this change). NEVER push to `main` or `dev` directly; NO tag, NO release, NO version/CITATION bump. <!-- sdd-owner: parent -->
- [ ] Post-apply bounded review of the open PR: scenario→test map complete, no-touch declarations hold, literal test totals quoted, diff stays within ~300 lines, `resources/templates/list` still lists the 3 templates and `resources/list` is non-empty with `sofer://status`. <!-- sdd-owner: parent -->
```

- **No stale-checkbox reconciliation was performed and none was needed.** The three rows are genuinely pending
  parent/human action (no commit exists, PR unopened, bounded review hasn't run), so mechanically flipping any box
  would have misrecorded state. The parent prompt did **not** instruct archive-time checkbox repair. Archive made
  **zero** edits to `tasks.md`.
- Final `tasks.md` count: **18 `[x]` / 3 `[ ]`** (all parent-owned) of 21.

## Deviations

**No material deviations at archive.** Deviations that arose during apply/verify were adjudicated there and are
recorded in `apply-progress.md`/`verify-report.md` (archived with the change); none affect archive correctness:

1. **`TestResources` count is 9, not 8/7** — task/design artifact counts were stale; the no-touch gate holds by
   construction (`git diff -U0` shows zero `-` content lines; pure insertion hunk `@@ -1644,0 +1647,180 @@`). Scoped
   `-k TestResources` = 9 passed before and after.
2. **No 7th `test_status_resource_static_not_template`** — tasks.md (authoritative) choreographs exactly 6 tests; the
   static-not-template clause is asserted behaviorally inside `test_status_resource_listed` (`sofer://status` ∉ template
   URIs; exact 3-template set equality). Consistent with the 6-new-test full-suite delta.
3. **`r.uri` is `AnyUrl` not `str`** (fastmcp v3) — one-line test-side `str(r.uri)` cast; no handler change.
4. Sync transforms applied on merge (provenance single-line form, `*Tests:*` stripped, `(kept verbatim …)` annotations
   dropped, blank-line normalization) — per-sync-note; the delta file is archived raw/byte-identical (7928 bytes).
5. Sync-note's provenance-date conditional did **not** fire (archive date == provenance date, both 2026-09-11).

## Scope Isolation (issue #144 / #145 / no-touch)

| Gate | Command / evidence | Result |
|---|---|---|
| TestResources pins intact | `git diff -U0 tests/test_mcp_server.py` — zero deletion lines (pure insertion hunk `@@ -1642,6 +1644,186 @@`); 9 pre-existing tests unchanged; scoped run → 9 passed | **PASS** |
| TestToolRoster intact | unchanged (3 passed, `test_exactly_fourteen_callables`, roster == 14 == `len(WORKFLOW_METADATA)`) | **PASS** |
| Envelope/hints (#144/#145) untouched | diff touches only handler + registration + docstring (+45/−2 in `mcp_server.py`); `sofer_auth_status`/`_envelope`/hints machinery (lines ~1782/1857/1888-1894) untouched; `test_mcp_schema.py` untouched | **PASS** |
| Canonical 10.8 / APX-01 untouched | delta spec has **no `## ADDED`/`## REMOVED` sections** (grep exit 1); 10.8-tail and APX-01-tail SHA-256 re-verified byte-intact this pass (hashes above) | **PASS** |
| No-leak | payload = bool + enum + `_SERVER_*` strings + root + int; guard test + adversarial probe: `phrase123`/`envphrase456` and both sha256 hexdigests absent from serialized payload | **PASS** |
| Roster / registry | 14 callables == 14 `WORKFLOW_METADATA` keys; `tool_count` derived, never a hardcoded literal | **PASS** |
| Out-of-scope files | `git status --porcelain` at archive = `openspec/specs/mcp-server/spec.md` (absorbed sync merge), `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, untracked archived change root — **no** README/README_ES, `pyproject.toml`, `workflow.py`, `cli.py`, `scratch/`, `.gitignore`, `TRACE.md` | **PASS** |
| Same-domain active changes | `find openspec/changes -maxdepth 2 -path '*/specs/mcp-server/spec.md' -not -path '*/archive/*'` → **0 results** | **PASS** |

## Status and actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` | archive ran file-backed; the canonical merge had already been performed by the sync phase (`sync-note.md`) |
| `planningHome` | repo-local `openspec/` | change root existed pre-move; all required artifacts read from disk directly |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies; `allowedEditRoots [C:\Users\elaze\Desktop\sofer]` encloses every path this phase read/wrote/moved |
| Change selection | unambiguous (`2026-09-11-fix-status-resource`), supplied by the parent prompt + confirmed on disk | no blocker |
| `taskProgress` | 18/18 implementation complete; unchecked = only the 3 parent-owned rows | **Final Task Completion Gate passes** |
| `dependencies` | verify `pass` (blockers 0, critical 0); sync already complete (`sync-note.md` + canonical re-verification this pass); the engine's `blocked` labels on sync/archive were attributable solely to the **missing `syncReport` artifact**, which this repo never writes (convention: `sync-note.md` + archive `## Spec Sync` section) | no real blocker — parent prompt explicitly mandates archive and forbids re-sync |
| `relationships.sameDomainActiveChanges` / `collisions` | `[]` / `[]` | no same-domain collision; this was the only active change |
| `rules.archive` (`openspec/config.yaml`) | *"Warn before merging destructive deltas."* | honored — archive performed no merge; the absorbed sync-phase merge was MODIFIED-only and non-destructive (35 insertions / 1 deletion, no `REMOVED`) |
| Engram observation IDs | n/a — `openspec` store | no `sdd/{change}/archive-report` memory write is required in this mode; **none performed or claimed** |

## Archive Mechanics

- **`git mv` not applicable**: the change root contained **0 tracked files**
  (`git ls-files openspec/changes/2026-09-11-fix-status-resource | wc -l` → **0**; `git status` reported the whole
  directory as `??` untracked, consistent with the parent not having committed yet). Precedent: #145's archive (same
  base `dev`, same untracked working-tree shape).
- **Move performed as a plain filesystem rename** (`mv openspec/changes/2026-09-11-fix-status-resource
  openspec/changes/archive/2026-09-11-fix-status-resource`) into the pre-existing `openspec/changes/archive/`
  (48 → 49 entries). No recorded git history existed for these files; the parent's upcoming commit adds them at their
  final archived path either way — so the audit trail and the parent's `git add` outcome are identical to a `git mv`.
- Files archived (**7**, none deleted or rewritten): `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`,
  `verify-report.md`, `sync-note.md`, `specs/mcp-server/spec.md` (7928 bytes, byte-identical delta).
- `archive-report.md` is **additive** and lives inside the archived change (repo convention — written at the archived
  path after the move). `openspec/changes/` now contains **exactly `archive/`**.
- Audit trail intact: active artifacts were **moved, never deleted or modified**. Nothing under `openspec/specs/`
  (already synced — NOT re-applied), `TRACE.md`, `scratch/`, `.gitignore`, `src/`, `tests/`, or
  `README.md`/`README_ES.md` was touched by this phase. Worktree change set after the move is byte-identical to
  before: the same 3 tracked modifications (`openspec/specs/mcp-server/spec.md`, `src/sofer/mcp_server.py`,
  `tests/test_mcp_server.py`) plus the archived change dir.
- **No commit was made, nothing was staged** (`git diff --cached` empty) — the parent versions the move and this
  report.

## Rollback

- **Rollback of the change itself:** `git checkout -- src/sofer/mcp_server.py tests/test_mcp_server.py` (or
  `git revert` once committed) restores pre-#146 behaviour (`resources/list` empty, as before); the canonical MSP-R07
  static-resource amendment would then need a manual restore of the pre-#146 `Resources (MSP-R07)` block in
  `openspec/specs/mcp-server/spec.md` (the 35-insertion/1-deletion MODIFIED block at canonical lines ~181–252, ending
  before `### Requirement: Prompts (MSP-R08)`; 10.8 and APX-01 stay untouched either way).
- **Rollback of the archive move:** move the folder back to `openspec/changes/2026-09-11-fix-status-resource/` and
  drop this report — lossless, since the original files were never modified and (being untracked) no history is
  invalidated.
- **Next steps (parent-owned):** commit the 2 code/test files **+ the archived change dir (with this report)** +
  the synced canonical `openspec/specs/mcp-server/spec.md` on `fix/146-status-resource` (Phase 4 row 1); open the
  **PR into `dev`** with the `.github/PULL_REQUEST_TEMPLATE.md` sections filled with real output (row 2); run the
  bounded review (row 3); then hand merge authorization to the user (`gh pr merge` is human-authorized; a GitHub
  owner cannot self-approve). Target: `dev`. No tag, no release, no version bump.
- **Out of scope, not created here:** the sync-note's provenance-date conditional did not fire (provenance already
  reads `archived 2026-09-11` == today) — nothing to amend.