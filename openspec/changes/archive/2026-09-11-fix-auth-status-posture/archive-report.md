# Archive Report — 2026-09-11-fix-auth-status-posture

**Change**: `2026-09-11-fix-auth-status-posture`
**Issue**: GitHub **#145 ONLY** — PR **#2 of 2** (sibling: #144 `fix/144-auth-status-hints`, merged at `cf27584`)
**Date**: 2026-09-11
**Artifact store**: `openspec` (repo-local; no Engram observation IDs for this change — the openspec store is authoritative)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and not yet opened as a PR** — see *Delivery*)
**Verify verdict**: **PASS** — `gentle-ai.verify-result/v1`, `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 0/0` (MODIFIED delta), `scenarios: 5/5`, `test_exit_code: 0`, `build_exit_code: 0`; issue #145 acceptance criteria **3/3**
**Branch**: `fix/145-auth-status-posture` (base `dev`, sibling #144 merged at `cf27584`) — **0 commits beyond `dev`**; the change is a working-tree diff of 3 files (`src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `tests/test_mcp_schema.py`)
**Archived path**: `openspec/changes/archive/2026-09-11-fix-auth-status-posture/`

## Summary

Adds **restart-proof posture fields to `sofer_auth_status`** (issue #145, the second half of the auth_status split):
`phrase_source`, `server_process_id`, `server_started_at`, and `server_version` are captured once in `build_server`
(process-start semantics — never re-derived, never read from `os.environ` at envelope time) and exposed on the
envelope + `output_schema`.

Key mechanics: a new `_PhraseSource` literal + pure `_resolve_approval_phrase(explicit)` helper performs the
**single** env read via the `_APPROVAL_PHRASE_ENV_VAR` fact constant (precedence explicit > env > none, blank ⇒ fail
closed, blank explicit never falls back to env); `_next_started_at()` produces an ISO-8601 UTC µs timestamp with a
1 µs monotonic bump for Windows/CPython 3.10 clock granularity, anchoring build-difference semantics on
`server_started_at` (not pid, which is explicitly process-scoped and never asserted to differ — the mandated
anti-pitfall direction); `server_version` equals `get_version()`, non-empty, never raises. The `approval_configured`
invariant (`phrase_source == "none"` ⟺ `approval_configured is False`) is preserved, and posture fields carry zero
phrase material (no-leak audit).

Diff: **3 files, 406 changed lines (374 insertions / 32 deletions)** measured at verify — inside the ~380–430
forecast and under the ~450 ask-on-risk gate; no scope creep, no chaining, `size:exception` not used. Tests:
**14 new** (11 in `TestAuthStatusPosture` + 3 additive schema/envelope extends, all 100 % additive). Full suite
**1489 passed / 6 skipped** vs. baseline **1478 / 6** (+11 exactly).

**No commits were made by this phase** (executor contract: parent versions). Delivery is pending:
commit → PR #2 into `dev` → bounded review → human approval/merge.

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (parent mandate: re-applying would regress
the transformed canonical block with `*Tests:*` scaffolding, `(issue #145)` provenance, and `(kept verbatim …)`
annotations — see `sync-note.md`). Archive reads a *completed* sync, it does not perform one.

| Field | Value |
|---|---|
| Domains synced | **`mcp-server`** (1 of 1) |
| ADDED requirements | **none** |
| MODIFIED requirements | **`Auth status preflight read-only (10.8)`** — wholesale replacement in place (envelope contract + posture semantics); canonical **line 420** (provenance at **line 422**) |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical file | `openspec/specs/mcp-server/spec.md` (currently modified in the worktree: **52 insertions(+) / 2 deletions**) |
| Provenance line (re-verified this pass) | `> Added by change \`mcp-dx-audit-surface\` (archived 2026-08-31). Modified by \`2026-09-11-fix-auth-status-posture\` (archived 2026-09-11).` — **archive date 2026-09-11 matches the provenance date, so no amendment was needed** (sync-note.md's conditional does not fire) |
| Counts (canonical, re-verified this pass) | requirement headers **24 → 24** (MODIFIED, not added); scenario headers **85 → 90** (+5 posture GWT scenarios, canonical scenario kept); 10.8 occurrences **exactly 1**; `*Tests:*` occurrences **0**; tabs **0**; LF-only; file 752 → 802 lines |
| APX-01 integrity (re-verified this pass) | **byte-intact** — SHA-256 of the APX-01 block (header → EOF) = `5291acbb84f98a3c5b319d7f0a2a84513257b9d5099524d5c2a29046c4829aff`, identical pre/post sync (#144 isolation honored; NOT re-added, NOT touched) |
| Archive-time sync fallback | **NOT executed and not needed** — the sync was already complete (`sync-note.md` in this change root records it) and the parent prompt explicitly forbade re-application |
| Destructive merge | **Not applicable at archive** — archive performed no merge. The sync-phase merge itself was a MODIFIED-only replacement (52 insertions / 2 deletions, zero canonical requirements dropped); `rules.archive`'s *"Warn before merging destructive deltas"* is honored: no `REMOVED`, no large destructive block, no approval required or given |

**Precedent / where the sync record lives.** This repo has **no `sync-report.md` anywhere** (repo convention; 0 exist),
and it records spec-sync outcomes in the `## Spec Sync` section of `archive-report.md` (precedent:
`2026-09-09-feat-mcp-init-tool/archive-report.md`, `2026-09-11-fix-auth-status-hints/archive-report.md`). The sync
phase wrote `sync-note.md` inside the change root as the handoff; `sync-note.md` is archived with the change.

**Delta recorded as-is.** `specs/mcp-server/spec.md` (MODIFIED-only op — 10.8 with **6 scenarios**: canonical
"Preflight without publish" kept verbatim + 5 new posture scenarios) is archived **byte-identical** (8778 bytes) for
the audit record: `## MODIFIED Requirements` → `### Requirement: Auth status preflight read-only (10.8)` with
`#### Scenario:` blocks `Preflight without publish` / `Posture fields present in envelope and schema` /
`phrase_source follows configuration precedence` / `server_started_at is the restart-proof signal across server builds` /
`server_process_id is process-scoped` / `No phrase material in the posture fields`.

**Idempotency (recorded in `sync-note.md`).** The native helper's `applyDeltaSpec` replaces a MODIFIED block by name
(`requireCanonicalBlock` + `replacements`), so a re-application **cannot duplicate** 10.8 — but it *would* overwrite
the transformed canonical with the raw delta block (regression). The guard is this note + sync-note.md; archive
deliberately did not run `applyDeltaSpec`.

**Active same-domain change warning.** None. `openspec/changes/` contains only `archive/` after the move; the combined
planning dir `2026-09-11-fix-auth-status-diagnostics/` that #144 warned about has been removed from the tree by the
prior turn (re-verified: `find openspec/changes -maxdepth 1 -name '*diagnostics*'` → 0 results). This change was the
**only** active change touching domain `mcp-server`; `relationships.sameDomainActiveChanges: []` and `collisions: []`.

## Verification Evidence

| Gate | Result |
|---|---|
| Verify verdict | `pass` — `blockers: 0`, `critical_findings: 0`, `requirements: 0/0`, `scenarios: 5/5` (machine-readable envelope at the head of `verify-report.md`) |
| Acceptance criteria (#145) | **3 / 3 PASS** — (1) 4 fields in envelope AND documented in docstring (envelope `src/sofer/mcp_server.py:1890-1893`, reads globals only, never `os.environ`); (2) build-difference anchored on `server_started_at` (µs + monotonic bump), NOT pid (independent probe P3 strictly increasing, P4 pid process-scoped never asserted to differ); (3) unit tests cover fields + `phrase_source` values — exactly 11 new + 3 schema |
| Verification style | **Independent and adversarial**: direct code/diff inspection + standalone re-derivation probe `verify_145_probe.py` written from the spec (P1–P7: envelope+schema via fastmcp `Client`, no-leak, version, pid, roster) — **ALL INDEPENDENT PROBES PASSED** |
| Pytest (focused) | `uv run pytest tests/test_mcp_server.py::TestAuthStatusPosture tests/test_mcp_schema.py::TestOutputSchema::test_output_schema_typed tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak tests/test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured -q` → **14 passed in 1.41s** |
| #144 pin set (22 node IDs) | **22 passed in 1.50s** — no hunk in `TestHintContentActionable`, `TestNextHintContract`, `TestPublishAuthorizationLadder`, `TestApprovalNotConfiguredMessage`, `TestAuthStatusValidity`, `TestToolRoster::test_exactly_fourteen_callables`, or the schema guidance block |
| Pytest (full) | `uv run pytest tests/ -q` → **1489 passed, 6 skipped**, 13 warnings in 55.10s (+11 vs baseline 1478/6; 0 skipped delta; no test removed/relaxed) |
| Lint / type / whitespace | `uv run ruff check src/ tests/` → "All checks passed!" · `uv run ruff format --check` (3 changed files) → formatted · `uv run mypy src/` → "Success: no issues found in 32 source files" · `git diff --check` → clean |
| Spec scenario coverage | 5 new + 1 canonical scenarios mapped to tests (AGENTS.md §6): preflight pin kept verbatim; posture/schema → `test_posture_fields_present_and_typed` + `test_server_version_equals_get_version` + `test_posture_fields_confined_to_auth_status` + extended `test_output_schema_typed` (roster 14, `required == ["ok","exit_code","output"]`, no `enum`); precedence 5 paths + invariant; started_at restart-proof; pid process-scoped; no-leak extended. No spec row without a test |
| No-leak / domain audit | single env read via `_APPROVAL_PHRASE_ENV_VAR` (`:326-346`); old inline literal gone (`grep 'os.environ.get("SOFER'` → no match); envelope reads globals only; `phrase_source == "none"` ⟺ `approval_configured is False` (probe + 7 tests); `server_version == get_version()`, non-empty, never raises |
| Assertion quality | substantive — regex-fullmatch ISO µs, equality chains vs `get_version()`, roster-wide schema scan, 5 real config paths + module-default direct call, two real back-to-back builds for strict monotonicity, serialized-envelope scans for phrase material; no tautologies, no ghost loops, no smoke-only tests |
| Strict TDD | **Inactive by configuration** (`openspec/config.yaml` → `strict_tdd: false`); no TDD Cycle Evidence required; assertion-quality audit still performed (advisory) |

## Delivery

| Field | Value |
|---|---|
| Branch | `fix/145-auth-status-posture`, base `dev` (sibling #144 merged at `cf27584`) — never `main`/`dev` directly |
| Commits | **none** — HEAD is `cf27584` (merge PR #158); `git status --porcelain` = 3 modified files + untracked change root. The change is a **working-tree diff** |
| PR | **#2 NOT yet opened** — parent-owned (`tasks.md` row 4.2). Target: `dev`, via `.github/PULL_REQUEST_TEMPLATE.md` with REAL verification output (full pytest tail, ruff, mypy, `git diff --check`), the SDD artifacts section (proposal/spec/design/tasks paths + the 3.4 scenario→test map), and this change's Review Workload Forecast; explicit note: no tag, no release, no version bump |
| Merge target | `dev` only; `main` receives changes solely via release-time merges from `dev` |
| Release / tag step | **none** for this change (no version bump — hatch-vcs derives from tags) |
| Review workload | **406 changed lines (374 insertions / 32 deletions) over 3 files** measured at verify — inside the ~380–430 forecast and under the ~450 ask-on-risk gate → **single PR**, no chaining, `size:exception` not used. (Working-tree `git diff --stat` at archive reads 426 insertions / 34 deletions *including* the already-synced canonical `openspec/specs/mcp-server/spec.md` 54-line merge — that spec change is the sync phase's absorbed output, not archive's) |
| PR boundary | design D6 slice = issue #145 only; #144's hint/message payload entirely absent from this diff (hunk inventory additive-only) |

**Tasks 4.1–4.3 (`sdd-owner: parent`) remain open in the persisted artifact** — parent lifecycle rows
(commit → PR #2 → bounded review + user merge authorization). They are **not** implementation tasks and their
completion is outside the archive's authority. Consequently the verified working-tree blobs are the blobs the parent
will commit; no revision was altered by this phase.

## Task Completion Gate

Re-read the persisted tasks artifact immediately before the archive move (now at
`openspec/changes/archive/2026-09-11-fix-auth-status-posture/tasks.md`):

- **`- [ ]` implementation task markers remaining: ZERO.** All **38** implementation-owned rows (Phases 0–3) are `[x]` (`grep -c` = 38).
- The **3** remaining `- [ ]` rows are **all parent-owned** (`<!-- sdd-owner: parent -->`), reproduced verbatim:

```text
- [ ] 4.1 Parent: split the work into reviewable commits on `fix/145-auth-status-posture` (e.g. `feat(mcp): capture posture state in build_server` → `feat(mcp): expose posture fields on sofer_auth_status` → `test(mcp): cover auth status posture fields`) keeping tests with code; pre-commit ruff+mypy must pass; no commit to `main`/`dev`. <!-- sdd-owner: parent -->
- [ ] 4.2 Parent: open PR #2 (`fix/145-auth-status-posture` → `dev`) using `.github/PULL_REQUEST_TEMPLATE.md` with REAL verification output (full pytest tail, ruff, mypy, `git diff --check`), the SDD artifacts section (proposal/spec/design/tasks paths + the 3.4 scenario→test map), and this change's Review Workload Forecast; explicit note: no tag, no release, no version bump. <!-- sdd-owner: parent -->
- [ ] 4.3 Parent: start or reuse the bounded review for the PR diff and only then hand the merge decision to the human (`gh pr merge` is human-authorized); confirm the merge target is `dev`. <!-- sdd-owner: parent -->
```

- **No stale-checkbox reconciliation was performed and none was needed.** The three rows are genuinely pending
  parent/human action (no commit exists, PR #2 is unopened, the bounded review has not run), so mechanically
  flipping any box would have misrecorded state. The parent prompt did **not** instruct archive-time checkbox
  repair. Archive made **zero** edits to `tasks.md`.
- Final `tasks.md` count: **38 `[x]` / 3 `[ ]`** (all parent-owned) of 41.

## Deviations and Adjudications

1. **`global (...)` parenthesized syntax (design D5) is invalid Python** — implemented as **two** single-line
   `global` statements (`src/sofer/mcp_server.py:2860-2861`). Logic identical; `mypy` clean.
2. **D7 tool docstring compressed** — the full-length posture paragraph would push the pre-"When to use" fragment
   count past the ≤10 cap in `TestDescriptions::test_descriptions_concise_no_msp_untrusted` (an existing DX pin).
   Compressed to a dot-free-identifier 2-fragment paragraph preserving every required fact (types/domains,
   precedence, capture-once at build, restart-proof, process-scoped, never-leak, APX-01 pointer). Pin verified
   passing; live docstring inspected — all 4 fields documented.
3. **Pre-existing ruff format drift on README/README_ES.md** — full-tree `uv run ruff format --check` flags exactly
   those 2 files; both are **byte-identical to HEAD** `cf27584` and on the Scope Guards no-touch list — not
   introduced here, not touched. Scoped check on the 3 changed files: formatted.
4. **Anchor-line shifts** in tasks.md/apply-progress.md line references — resolved against the live file at apply
   time; verified by hunk positions.

## Scope Isolation (issue #144 / no-touch)

| Gate | Command / evidence | Result |
|---|---|---|
| #144 pins intact | `git diff -U0` hunk inventory — **additive only**; no hunks in `TestHintContentActionable` (:260-402, 10 pins), `TestNextHintContract` (:217), `TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed` (:1103), `test_blank_phrase_treated_as_unconfigured` (:1151), `TestApprovalNotConfiguredMessage` (:1187), `TestAuthStatusValidity` (:467), `TestToolRoster::test_exactly_fourteen_callables` (:423) | **PASS** — 22-pin run green |
| #144 fact constants untouched | no hunk touches `_approval_phrase_guidance_hints`, `_APPROVAL_PHRASE_*` constants (:185-245), `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE`, `sofer_publish_confirm`, or the roster | **PASS** |
| Canonical APX-01 untouched | delta spec has **no `## ADDED`/`## REMOVED`** (grep exit 1); APX-01 block SHA-256 re-verified byte-intact this pass | **PASS** |
| No-leak | envelope reads globals only, never `os.environ`; probe P6: `"phrase123"`/`"envphrase"` absent from posture + envelope; `phrase_source ∈ {"env","explicit","none"}` | **PASS** |
| Out-of-scope files | `git status --porcelain` at archive = `openspec/specs/mcp-server/spec.md` (synced merge), 3 code/test files, archived change root — **no** README/README_ES, `pyproject.toml`, `workflow.py`, `mcp_registration.py`, `scratch/`, `.gitignore`, `TRACE.md` | **PASS** |
| Combined planning dir | `openspec/changes/2026-09-11-fix-auth-status-diagnostics/` → **confirmed absent** (removed to /tmp by the prior turn; `find` → 0 results) — no leftover reference dir in the tree | **PASS** |

## Status and actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` | archive ran file-backed per the openspec rules; the canonical merge had already been performed by the sync phase |
| `planningHome` | repo-local `openspec/` | change root existed; all required artifacts read from disk directly |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies; `allowedEditRoots [C:\Users\elaze\Desktop\sofer]` encloses every path this phase read/wrote/moved |
| Change selection | unambiguous (`2026-09-11-fix-auth-status-posture`), supplied by the parent prompt + confirmed on disk | no blocker |
| `taskProgress` | 38/38 implementation complete; unchecked = only the 3 parent-owned rows | **Final Task Completion Gate passes** |
| `dependencies` | verify `pass` (blockers 0, critical 0); sync already complete (`sync-note.md`); the engine's `blocked` labels on sync/archive were attributable solely to the **missing `syncReport` artifact**, which this repo never writes (convention: `sync-note.md` + archive `## Spec Sync` section) | no real blocker — parent prompt explicitly mandates archive and forbids re-sync |
| `relationships.sameDomainActiveChanges` / `collisions` | `[]` / `[]` | no same-domain collision; this was the only active change |
| `rules.archive` (`openspec/config.yaml`) | *"Warn before merging destructive deltas."* | honored — archive performed no merge; the absorbed sync-phase merge was MODIFIED-only and non-destructive |
| Engram observation IDs | n/a — `openspec` store | no `sdd/{change}/archive-report` memory write is required in this mode; **none performed or claimed** |

## Archive Mechanics

- **`git mv` not applicable**: the change root contained **0 tracked files**
  (`git ls-files openspec/changes/2026-09-11-fix-auth-status-posture | wc -l` → **0**; `git status` reported the
  whole directory as `??` untracked, consistent with the parent not having committed yet). Precedent: #144's archive
  (same ancestor `cf27584`).
- **Move performed as a plain filesystem rename** into the pre-existing `openspec/changes/archive/` (47 → 48
  entries). No recorded git history existed for these files; the parent's upcoming commit adds them at their final
  archived path either way — so the audit trail and the parent's `git add` outcome are identical to a `git mv`.
- Files archived (**7**, none deleted or rewritten): `proposal.md`, `design.md`, `tasks.md`, `apply-progress.md`,
  `verify-report.md`, `sync-note.md`, `specs/mcp-server/spec.md` (8778 bytes, byte-identical delta).
- `archive-report.md` is **additive** and lives inside the archived change (repo convention — written at the archived
  path after the move). `openspec/changes/` now contains **exactly `archive/`**.
- Audit trail intact: active artifacts were **moved, never deleted or modified**. Nothing under `openspec/specs/`
  (already synced — NOT re-applied), `TRACE.md`, `scratch/`, `.gitignore`, `src/`, `tests/`, or
  `README.md`/`README_ES.md` was touched by this phase. Worktree change set after the move is byte-identical to
  before: the same 4 tracked modifications (`openspec/specs/mcp-server/spec.md`, `src/sofer/mcp_server.py`,
  `tests/test_mcp_schema.py`, `tests/test_mcp_server.py`) plus the archived change dir.
- **No commit was made, nothing was staged** (`git diff --cached` empty) — the parent versions the move and this
  report.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** `git checkout -- src/sofer/mcp_server.py tests/test_mcp_server.py
  tests/test_mcp_schema.py` (or `git revert` once committed) restores pre-#145 behaviour; the canonical 10.8 posture
  merge would then need a manual restore of the pre-#145 envelope contract in `openspec/specs/mcp-server/spec.md`
  (the 52-insertion/2-deletion MODIFIED block at canonical lines ~420–470, ending before
  `### Requirement: Approval-phrase configuration diagnostics (APX-01)`; APX-01 itself stays untouched).
- **Rollback of the archive move:** move the folder back to `openspec/changes/2026-09-11-fix-auth-status-posture/`
  and drop this report — lossless, since the original files were never modified and (being untracked) no history is
  invalidated.
- **Next steps (parent-owned):** commit the 3 code/test files **+ the archived change dir (with this report)** on
  `fix/145-auth-status-posture` (row 4.1) — note the canonical `openspec/specs/mcp-server/spec.md` merge is part of
  the *sync* output, not this working diff, and the parent decides whether to fold it into this commit or the sibling
  PR's; open **PR #2 into `dev`** with the `.github/PULL_REQUEST_TEMPLATE.md` sections filled with real output
  (row 4.2); run the bounded review (row 4.3); then hand merge authorization to the user (`gh pr merge` is
  human-authorized; a GitHub owner cannot self-approve). Target: `dev`. No tag, no release, no version bump.
- **Out of scope, not created here:** the parent may re-sync the canonical provenance date if the actual commit/PR
  lands on a later date than 2026-09-11 (sync-note.md conditional) — nothing to do at archive, the provenance date
  matches today.