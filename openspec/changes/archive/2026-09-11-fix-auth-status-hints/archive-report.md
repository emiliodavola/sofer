# Archive Report — 2026-09-11-fix-auth-status-hints

**Change**: `2026-09-11-fix-auth-status-hints`
**Issue**: GitHub **#144 ONLY** — PR **#1 of 2** (sibling: `fix/145-auth-status-posture`, issue #145, stacked after this one)
**Date**: 2026-09-11
**Artifact store**: `openspec` (repo-local; no Engram observation IDs for this change — the openspec store is authoritative)
**Status**: **archived** (archive mechanics complete; delivery **not yet committed and not yet opened as a PR** — see *Delivery*)
**Verify verdict**: **PASS** — `gentle-ai.verify-result/v1`, `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 4/4`, `test_exit_code: 0`, `build_exit_code: 0`; issue #144 acceptance criteria **3/3**
**Branch**: `fix/144-auth-status-hints` (base `dev`, `dev` is an ancestor) @ `7d5cc31` — **0 commits beyond `dev`**; the change is a working-tree diff (390 insertions / 8 deletions, `sha256:befb36e8…`)
**Archived path**: `openspec/changes/archive/2026-09-11-fix-auth-status-hints/`

## Summary

Fixes the **#144 dead-end hint**: with `approval_configured:false`, `sofer_auth_status` returned only
`hints = {"action": "configure_approval_phrase"}` — no actionable path. The root cause is **process-start
semantics**, not hint wording (the phrase is read exactly once in `build_server` and the running server never
re-reads the environment), so the fix is **guidance, not runtime re-read**.

One source of truth (`D3` fact constants: `_APPROVAL_PHRASE_ENV_VAR`, `_APPROVAL_PHRASE_ACTION`,
`_PHRASE_READ_ONCE_FACT`, `_PHRASE_LAUNCH_ENV_FACT`, `_PHRASE_RESTART_FACT`, `_PHRASE_VERIFY_FACT`,
`_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` + per-agent setup strings) drives **both** surfaces: the pure helper
`_approval_phrase_guidance_hints()` merged into the unconfigured preflight `hints` (keeps the stable
`action` key, adds 9 flat `approval_phrase_*` scalar keys incl. `approval_phrase_restart_required: true`),
and the composed `_APPROVAL_PHRASE_NOT_CONFIGURED_MESSAGE` replacing the inline literal in the
`sofer_publish_confirm` refusal (keeps the verbatim `"publish is disabled:"` prefix and the exact refusal
`hints == {"action": "configure_approval_phrase"}`). Envelope shape, `output_schema`, tool roster (14) and
the `next` registry continuation are untouched.

Diff: **3 files, 390 insertions / 8 deletions** (`src/sofer/mcp_server.py` +127/−8,
`tests/test_mcp_schema.py` +31, `tests/test_mcp_server.py` +232 — both test files **100 % additive**) plus
the change artifacts. Tests: **10 new** (`TestHintContentActionable` ×7, `TestApprovalNotConfiguredMessage` ×3)
and **3 additive extends**; no pre-existing assertion was modified or relaxed. Full suite
**1478 passed / 6 skipped** vs. the re-measured baseline **1468 / 6** (+10 exactly).

**No commits were made by this phase** (executor contract: parent versions). Delivery is pending:
commit → PR #1 into `dev` → human approval/merge.

## Spec Sync

**DONE — already absorbed by the sync phase; NOT re-applied at archive** (parent mandate: re-applying
throws). Archive reads a *completed* sync, it does not perform one.

| Field | Value |
|---|---|
| Domains synced | **`mcp-server`** (1 of 1) |
| ADDED requirements | **`Approval-phrase configuration diagnostics (APX-01)`** — with all **4** scenarios |
| MODIFIED requirements | **none** |
| REMOVED requirements | **none** |
| RENAMED requirements | **none** |
| Canonical file | `openspec/specs/mcp-server/spec.md` (currently modified in the worktree: **56 insertions(+) / 0 deletions**) |
| Insertion point | immediately after requirement `Auth status preflight read-only (10.8)` — `### Requirement: Approval-phrase configuration diagnostics (APX-01)` at canonical **line 434**, provenance blockquote at **line 436** |
| Provenance line | `> Added by change \`2026-09-11-fix-auth-status-hints\` (archived 2026-09-11).` — **archive date matches today (2026-09-11), so no date amendment was needed** |
| Counts (canonical, re-verified this pass) | requirement headers **23 → 24**; APX-01 occurrences **exactly 1** |
| Archive-time sync fallback | **NOT executed and not needed** — the sync was already complete and the parent prompt explicitly forbade re-application |
| Destructive merge | **Not applicable** — ADD-only, zero `REMOVED`, no large `MODIFIED`; no destructive-merge approval was required or given |

**Precedent / where the sync record lives.** This repo has **no `sync-report.md` anywhere** (`find openspec
-name sync-report.md` → **0**), and it records spec-sync outcomes in the `## Spec Sync` section of
`archive-report.md` (precedent: `2026-09-09-feat-mcp-init-tool/archive-report.md`, the "already absorbed"
wording). The sync phase therefore wrote `sync-note.md` inside the change root as the handoff, explicitly
instructing **this** archive report to fold its content in — which is what this section does. `sync-note.md`
is archived with the change.

**Cited from `sync-note.md`** (the sync executor's own recorded evidence):

```text
node (native helper parse + re-apply):
  canonical blocks: 24 | unique names: 24 | duplicates: 0
  APX-01 blocks in canonical: 1 | APX-01 scenarios: 4 | provenance present: true
  RE-APPLY throws: Cannot add existing canonical requirement "Approval-phrase configuration diagnostics (APX-01)"
  delta ops -> added: 1, modified: 0, removed: 0
  fidelity: canonical APX-01 block byte-equal to delta block modulo the 3 declared transforms (56 lines)
git diff --stat canonical -> openspec/specs/mcp-server/spec.md | 59 insertions(+), 0 deletions
counts: requirement headers 23 -> 24; scenario headers 81 -> 85; APX-01 occurrences == 1; tabs == 0; LF-only
delta file untouched: specs/mcp-server/spec.md byte-identical
posture symbols: 0 in canonical post-merge (issue #145 isolation honored)
```

*(Note: `sync-note.md` recorded `59 insertions` when the canonical file also carried unrelated
whitespace; the archive-time re-measure is the authoritative **56 / 0.**)*

**Declared transforms applied on merge (3 — nothing else changed):**

1. delta's `*Introduced by change … (issue #144).*` italic line → canonical provenance blockquote;
2. delta's `*Tests:*` / backtick / `(extended)` test-pointer runs (13 lines) **dropped** — canonical format
   carries no test pointers (0 occurrences repo-wide); traceability lives in the delta + `verify-report.md`;
3. **zero edits to existing canonical content** — requirement 10.8 was left for #145.

**Idempotency verified.** Re-applying the delta to the canonical spec **throws**
`Cannot add existing canonical requirement "Approval-phrase configuration diagnostics (APX-01)"` — so the
sync can never be silently duplicated, and archive deliberately did **not** run `applyDeltaSpec`. The delta
file is left **byte-identical** for the archival record (its only in-scope edit — the test-pointer fix
`TestPublishApprovalLadder` → `TestPublishAuthorizationLadder` — is present at
`specs/mcp-server/spec.md:61` of the delta).

**⚠ Active same-domain change warning.** `openspec/changes/2026-09-11-fix-auth-status-diagnostics/specs/mcp-server/spec.md`
exists and is **active** (untracked) — it is the combined planning dir for #144+#145 carrying a combined
delta (APX-01 **+** the 10.8 posture rewrite). It is the **only** other active change touching domain
`mcp-server`. Composition rationale (recorded in the delta and `sync-note.md`): APX-01 is deliberately
**posture-free** and **ADD-only**, so the future #145 delta (which MAY reference APX-01's guidance) composes
cleanly onto the already-merged APX-01, and 10.8 remains untouched for it to rewrite at its own archive.
**Per the parent mandate this reference directory was neither moved nor touched by this archive** — it stays
outside `2026-09-11-fix-auth-status-hints` (verified: still at `openspec/changes/2026-09-11-fix-auth-status-diagnostics/`,
still untracked, 4 files, unchanged).

`openspec/config.yaml` `rules.archive`: *"Warn before merging destructive deltas."* — **honored**: no
destructive delta existed; no `REMOVED` requirement and no large `MODIFIED` block was merged here.

## Verification Evidence

| Gate | Result |
|---|---|
| Verify verdict | `pass` — `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 4/4` (machine-readable envelope at the head of `verify-report.md`) |
| Acceptance criteria (#144) | **3 / 3 PASS** — (1) actionable unconfigured `hints` (probe through the real in-memory `Client`: `action` + **9** `approval_phrase_*` keys, `approval_phrase_restart_required is True`, all values flat scalars, bare `approval_phrase` absent); (2) `PUBLISH_APPROVAL_NOT_CONFIGURED` message names the var + read-once + launcher env + restart, prefix kept, refusal `hints` exactly `{"action": "configure_approval_phrase"}`; (3) unit tests cover hint/message content — **exactly 10** collected |
| Spec coverage (APX-01) | **4 / 4 scenarios** mapped to tests (AGENTS.md §6): actionable → T1–T4 + extended schema test; refusal message → T8/T9 + extended ladder test; one fact source → T10 + T5; no leak / no config path → T6/T7 + extended no-leak test. No spec row without a test |
| Pytest (full) | `uv run pytest tests/ -q` → **1478 passed, 6 skipped**, 13 warnings, exit 0 (`stdout sha256:c9d78c56…`) — baseline **1468 / 6** (Phase 0 re-measure) + **10** new tests, reconciling exactly |
| Pytest (focused, incl. all pins) | `uv run pytest tests/test_mcp_server.py tests/test_mcp_schema.py -q` → **213 passed, 3 skipped**; `-k TestToolRoster` → 3 passed (**roster still 14 callables**) |
| New-test collection | `--collect-only -k "TestHintContentActionable or TestApprovalNotConfiguredMessage"` → **10/197** (exactly the 10 new tests, matching design T1–T10 one-for-one) |
| Mutation evidence (non-vacuity, executed outside the repo via throwaway `PYTHONPATH` pytest plugins — no repo file created/left behind) | **(a) revert to pre-#144 behaviour** (`_approval_phrase_guidance_hints` → `{"action": …}`, message → old literal): `test_mcp_server.py test_mcp_schema.py` → **8 failed, 205 passed, 3 skipped** — every new/extended test fired. **(b) fact drift** (`_PHRASE_RESTART_FACT` mutated after import, message left stale) → **4 failed, 209 passed, 3 skipped**, the drift guard failing with `assert 'no restart is needed, just re-call the tool' in 'publish is disabled: …'`. The new tests detect the exact regressions they were written to prevent; the drift guard is real, not decorative |
| Independent read-once probe (not a test) | Through the real `Client` boundary: built with `SOFER_MCP_APPROVAL_PHRASE` absent, **then** exported it and called `sofer_auth_status` → `_APPROVAL_PHRASE` stayed `None` and `approval_configured` stayed `false`. Corroborates the guidance's central claim (read-once ⇒ full restart required) and confirms exactly **one** env-read site (`mcp_server.py:2761`, inside `build_server`) |
| Per-agent claim-to-code check | Every per-agent claim re-derived from `mcp_registration.build_entry` and reproduced live: opencode → `{type, command, cwd}`, **no env field** (guidance states no environment is forwarded); codex → `env_vars` NAMES only; gemini → `env` NAME → `$NAME`; `mcp_registration.py:158-165` matches byte-for-byte |
| Lint / type / whitespace | `uv run ruff check src/ tests/` → "All checks passed!" · `uv run ruff format --check src/ tests/` → "64 files already formatted" · `uv run mypy src/` → "Success: no issues found in 32 source files" · `git diff --check` → clean (combined `stdout sha256:43488451…`, exit 0) |
| Pins intact (regression contract) | **Test files have 0 deletions**, so every pre-existing line is byte-identical: `_is_flat_hint_dict` definition, the refusal exact-dict `hints` assert, `"publish is disabled" in envelope["output"]`, configured `approval_phrase == "<from human>"`, the unconfigured `action` + bare-key-absent pins — all appear in the diff as **unchanged context lines**, with new asserts only *appended after* them |
| Strict TDD | **Inactive by configuration** (`openspec/config.yaml` → `strict_tdd: false`, `testing.strict_tdd: false`, `apply.tdd: false`); no `TDD Cycle Evidence` table is required and its absence is not a finding. Assertion-quality audit was still performed (advisory) — no tautology-only tests, no ghost loops, no smoke-only tests |

## Delivery

| Field | Value |
|---|---|
| Branch | `fix/144-auth-status-hints`, base `dev` (`git merge-base --is-ancestor dev HEAD` → OK) — never `main`/`dev` directly |
| Commits | **none** — `git rev-list --count dev..HEAD` → **0**; HEAD is `7d5cc31` (merge PR #157). The change is a **working-tree diff** of 3 files (`sha256:befb36e8…`) |
| PR | **#1 NOT yet opened** — parent-owned (`tasks.md` row 4.2). Target: `dev`, via `.github/PULL_REQUEST_TEMPLATE.md` with `Closes #144`, the "#144 only" scope note, real command output, and the SDD artifacts section |
| Merge target | `dev` only; `main` receives changes solely via release-time merges from `dev` |
| Release / tag step | **none** for this change (no version bump — hatch-vcs derives from tags) |
| Review workload | **390 insertions / 8 deletions** — 97.5 % of the 400-line canonical budget → **single PR**, no chaining, no `size:exception` (neither used nor needed) |
| PR boundary | design D6 slice = issue #144 only; the sibling `fix/145-auth-status-posture` work is entirely absent from this diff |

**Tasks 4.1–4.3 (`sdd-owner: parent`) remain open in the persisted artifact** — parent lifecycle rows
(commit → PR #1 → post-apply bounded review + user merge authorization). They are **not** implementation
tasks and their completion is outside the archive's authority. Consequently the verified working-tree blobs
are the blobs the parent will commit; no revision was altered by this phase.

## Task Completion Gate

Re-read the persisted tasks artifact immediately before the archive move (now at
`openspec/changes/archive/2026-09-11-fix-auth-status-hints/tasks.md`):

- **`- [ ]` implementation task markers remaining: ZERO.** **24** implementation-owned rows (Phases 0–3) are `[x]`.
- The **3** remaining `- [ ]` rows are **all parent-owned** (`<!-- sdd-owner: parent -->`), reproduced verbatim:

```text
- [ ] Commit the work in reviewable work units (e.g., Phase 1 implementation unit, Phase 2 test unit) on `fix/144-auth-status-hints`; pre-commit hooks run ruff + mypy automatically; never `--no-verify`; never push to `main`/`dev` directly, no tag, no release, no version bump. <!-- sdd-owner: parent -->
- [ ] Create PR #1 into `dev` using `.github/PULL_REQUEST_TEMPLATE.md` with every section filled: `Closes #144` (issue linked), scope note "issue #144 only — posture fields (#145) land in the stacked PR from `fix/145-auth-status-posture`", Verification with REAL command output (pytest totals, ruff, mypy), Files-changed table, and the SDD artifacts section listing this change's proposal/spec/design/tasks. <!-- sdd-owner: parent -->
- [ ] Post-apply bounded review (parent-owned lifecycle gate): re-read `specs/mcp-server/spec.md` APX-01 against the applied diff — every MUST/SHALL row honored, pins (`test_mcp_server.py:213/783-784/786`, `test_mcp_schema.py:327/348/349`) untouched, anti-posture grep clean, no scope drift beyond issue #144; then hand the merge authorization to the user (`gh pr merge` — a GitHub owner cannot self-approve). <!-- sdd-owner: parent -->
```

- **No stale-checkbox reconciliation was performed and none was needed.** The three rows are genuinely
  pending human/parent action (no commit exists, PR #1 is unopened, the bounded review has not run), so
  mechanically flipping any box would have misrecorded state. The parent prompt did **not** instruct
  archive-time checkbox repair. Archive made **zero** edits to `tasks.md`.
- Final `tasks.md` count: **24 `[x]` / 3 `[ ]`** (all parent-owned) of 27.

## Deviations and Adjudications

1. **Size forecast miss: ~215 (range 200–240) forecast → 390 insertions / 8 deletions actual (~1.8×).**
   Disclosed honestly in `apply-progress.md` and by verify as a **non-blocking WARNING**. The overage is
   mandated verbosity: the D3 constant block + composed message, per-agent setup prose, three docstring
   updates, and the 10 spec-required tests. It stays **inside the 400-line budget**, so the
   `Chained PRs recommended: No` / single-PR decision stands and `size:exception` was neither used nor needed.
2. **Ordering: implementation before tests** (`design.md` §6 prescribed RED-first; `tasks.md` + `strict_tdd: false`
   ordered implementation first). Non-vacuity was re-proved by **mutation** (see *Verification Evidence*),
   which is stronger evidence than a claimed RED run.
3. **T13 asserts on `message + output`, not `message` alone** — the fastmcp boundary drops some envelope
   fields on success envelopes; `_error_envelope` sets `output = message` on refusals, so the chosen carrier
   is the reliable one (independently confirmed by verify).
4. **`_PHRASE_VERIFY_FACT` rides only in the `hints` surface** — the refusal message intentionally carries
   exactly the 4 process-start facts. Consistent with spec scenario 3, which enumerates those 4.
5. **Duplicated env-var literal across modules** — `mcp_server._APPROVAL_PHRASE_ENV_VAR` and
   `mcp_registration._ENV_KEYS[1]` both spell `"SOFER_MCP_APPROVAL_PHRASE"`. Accepted by design (D3): the
   CLI-side module must never import the optional-`mcp`-extra server module, and the reverse import would be
   needless coupling. Guarded by a 1-line drift assert in the extended `test_auth_status_no_leak`. Noted so
   it is not re-litigated at review.
6. **Pin line numbers shifted** (+11 additive lines preceding them, +2 imports at file top): the accept-prompt
   quoted the schema pins as `:361/362`; in the working tree they are `:362-363`, and `:327/:348/:349` became
   `:329/:362/:363`. **Content is byte-identical** — test files have **0 deletions** — only offsets moved.
7. **Canonical spec insertion count differs from `sync-note.md`** (`59` recorded vs. **56** re-measured).
   The sync note's number included unrelated whitespace; the archive-time re-measure is authoritative.
   Line 434 / provenance 436 / APX-01 = 1 were re-verified directly this pass.
8. **`git mv` was not applicable** (see *Archive Mechanics*) — the change root had **0 tracked files**.
   Documented as a mechanics deviation, not an audit-trail deviation: no history existed to preserve.
9. **No partial-archive exception was invoked.** Proposal ✅, spec delta ✅, design ✅, tasks ✅,
   apply-progress ✅, verify-report ✅ — all required artifacts are present and complete. No destructive
   canonical merge occurred, so no destructive-merge approval was needed either.

## Scope Isolation (issue #145)

| Gate | Command | Result |
|---|---|---|
| Posture symbols absent from the whole diff | `git diff \| grep -nE "phrase_source\|server_process_id\|server_started_at\|server_version"` | **0 matches** (exit 1) |
| Posture symbols absent from the source file | `grep -nE "…" src/sofer/mcp_server.py` | **0 matches** (exit 1) |
| No new imports (`datetime`/`_version` are #145) | `git diff src/sofer/mcp_server.py` import scan | **0 matches**; sorted import-name list identical between `HEAD` and the tree |
| No envelope/schema drift | `output_schema`, `_ERROR_ENVELOPE_SCHEMA_FIELDS` | untouched in the diff |
| ASCII-only production text | non-ASCII scan of added `mcp_server.py` lines | **0 matches** |
| Out-of-scope files | `git status --porcelain` | **no** README/README_ES, `pyproject.toml`, `workflow.py`, `scratch/`, `.gitignore`, `TRACE.md` |
| Reference planning dir (combined #144+#145) | `openspec/changes/2026-09-11-fix-auth-status-diagnostics/` | **untouched, not moved** (parent mandate) — still active, still untracked, 4 files |

## Status and actionContext Findings

| Field | Value | Archive finding |
|---|---|---|
| `artifactStore` | `openspec` | archive ran file-backed per the openspec rules; the canonical merge had already been performed by the sync phase |
| `planningHome` | repo-local `openspec/` | change root existed and all required artifacts were read from disk directly |
| `actionContext.mode` | `repo-local` | no `workspace-planning` gate applies |
| `allowedEditRoots` | `[C:\Users\elaze\Desktop\sofer]` | the archive target `openspec/changes/archive/2026-09-11-fix-auth-status-hints/` and this report are **inside** the root — no out-of-root write |
| Change selection | **ambiguous** in the injected status JSON (`nextRecommended: "Change selection is ambiguous: 2026-09-11-fix-auth-status-diagnostics, 2026-09-11-fix-auth-status-hints."`, `blockedReasons` identical, `applyState`/`archive: blocked`) | **superseded by the parent prompt**, which explicitly selected `2026-09-11-fix-auth-status-hints` and supplied the change root + mandate. Per the non-authoritative-store carve-out this JSON was not treated as a real blocker: readiness was resolved by reading the Engram/openspec artifacts directly, and the concrete change root was confirmed on disk |
| `taskProgress` | 24/27 complete; unchecked = the 3 parent-owned rows | **zero unchecked implementation rows** → the Final Task Completion Gate passes |
| `dependencies` | `archive: blocked` (ambiguous selection) | adjudicated: the only real blocker class — ambiguous selection — was resolved by the parent's explicit selection; verify is `pass` with 0 blockers and the canonical sync is complete |
| `relationships.sameDomainActiveChanges` | not surfaced by the engine | the archive's own scan found the one active same-domain change `2026-09-11-fix-auth-status-diagnostics` → warned above |
| `collisions` | empty | nothing to raise |
| `rules.archive` (`openspec/config.yaml`) | *"Warn before merging destructive deltas."* | honored — no destructive delta existed |
| Engram observation IDs | n/a — `openspec` store | no `sdd/{change}/archive-report` memory write is required in this mode; **none performed or claimed** |

## Archive Mechanics

- **`git mv` was attempted and is not applicable here**: `git mv openspec/changes/2026-09-11-fix-auth-status-hints
  openspec/changes/archive/2026-09-11-fix-auth-status-hints` → `fatal: source directory is empty` — the change
  root contained **0 tracked files** (`git ls-files openspec/changes/2026-09-11-fix-auth-status-hints | wc -l` → **0**;
  `git status` reported the whole directory as `??` untracked, consistent with the parent not having committed yet).
- **Move performed as a plain filesystem rename** into the pre-existing `openspec/changes/archive/`
  (46 → 47 entries). There was no recorded git history for these files to preserve, and the parent's upcoming
  commit will add them at their final archived path either way — so the audit trail and the parent's
  `git add` outcome are identical to a `git mv`.
- Files archived (**8**, none deleted or rewritten): `proposal.md`, `design.md`, `tasks.md`,
  `apply-progress.md`, `verify-report.md`, `sync-note.md`, `reference-144-145-planning.md`,
  `specs/mcp-server/spec.md`.
- `archive-report.md` is **additive** and lives inside the archived change (repo convention — written at the
  archived path after the move). `openspec/changes/` now contains exactly `archive/` and the untouched
  reference dir `2026-09-11-fix-auth-status-diagnostics/`.
- Audit trail intact: active artifacts were **moved, never deleted or modified**. Nothing under
  `openspec/specs/` (already synced), `TRACE.md`, `scratch/`, `.gitignore`, `src/`, `tests/`,
  `README.md`/`README_ES.md`, or the reference planning dir was touched by this phase. Worktree change set
  after the move is byte-identical to before it: the same 4 tracked modifications
  (`openspec/specs/mcp-server/spec.md`, `src/sofer/mcp_server.py`, `tests/test_mcp_schema.py`,
  `tests/test_mcp_server.py`) plus the two untracked dirs.
- **No commit was made, nothing was staged** (`git diff --cached` empty) — the parent versions the move and
  this report.

## Rollback Notes and Next Steps

- **Rollback of the change itself:** `git checkout -- src/sofer/mcp_server.py tests/test_mcp_server.py
  tests/test_mcp_schema.py` (or `git revert` once committed) restores the pre-#144 behaviour; the canonical
  APX-01 requirement would then need a manual removal from `openspec/specs/mcp-server/spec.md` (only the
  APX-01 block + its provenance line, canonical lines 434–489 — the 56 merged lines, ending immediately
  before `### Requirement: Bootstrap Phase 0 conditional canonical` at :490) — nothing else in the canonical
  spec was touched.
- **Rollback of the archive move:** move the folder back to `openspec/changes/2026-09-11-fix-auth-status-hints/`
  and drop this report — lossless, since the original files were never modified and (being untracked) no
  history is invalidated.
- **Next steps (parent-owned):** commit the 3 code/test files **+ `openspec/specs/mcp-server/spec.md`** +
  the archived change dir on `fix/144-auth-status-hints` (rows 4.1), open **PR #1 into `dev`** with the
  `.github/PULL_REQUEST_TEMPLATE.md` sections filled with real output (row 4.2), run the post-apply bounded
  review (row 4.3), then hand merge authorization to the user (`gh pr merge` — a GitHub owner cannot
  self-approve). No tag, no release. The sibling `fix/145-auth-status-posture` change follows, stacked after
  this PR merges.
- **Recorded follow-ups (out of scope, not created here):** (a) the duplicated
  `SOFER_MCP_APPROVAL_PHRASE` literal across `mcp_server`/`mcp_registration` stays accepted-by-design (D3);
  (b) size forecasts for this style of change should budget for mandated docstrings/comments and
  spec-pinned tests; (c) the combined planning dir `2026-09-11-fix-auth-status-diagnostics/` is expected to
  be replaced by the #145 change and then deleted by its owner — not by this phase.
