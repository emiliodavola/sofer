# Archive Report — 2026-09-15-chore-type-gate-policy

**Change**: `2026-09-15-chore-type-gate-policy`
**Issue**: GitHub **#201** — *chore: exclude `tests/` from both type gates and adopt pyright as a real gate*. The archive does **not** close the issue: delivery (the single commit + PR) is parent-owned and still pending.
**Branch**: `chore/201-type-gate-policy` (from `dev@8184ffb`)
**Date**: authored 2026-09-15; **archived 2026-09-15**
**Artifact store**: **hybrid** — this file inside the archived change root, plus the Engram record under topic key `sdd/2026-09-15-chore-type-gate-policy/archive-report`, **observation id `1301`**
**Status**: **archived by the `sdd-archive` phase** — pass, no blockers
**Verify verdict**: **PASS WITH WARNINGS** — `verdict: pass_with_warnings`, `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 5/5`, `evidence_revision sha256:d10a4b24b93c544a45a4c4eb61dfad4237d2b997bae335299c5c2006536554b0`
**Sync report**: **SYNCED** — canonical `openspec/specs/ci/spec.md` carries CI-09 + the CI-07 amendment; G7 flipped green
**Archived path**: `openspec/changes/archive/2026-09-15-chore-type-gate-policy/`

## Summary

The change declares the type-gate posture (`tests/` excluded from **both** gates, pyright adopted as a real gate), pins both analyzers exactly, commits one `tomli` stub, clears the 17 measured type diagnostics under mypy `strict = true`, adds seven static guards (G1–G7) to `tests/test_ci_workflows.py`, and records the CI-09 requirement plus the single authorized CI-07 clause amendment, which `sdd-sync` promoted into the canonical `ci` capability. Archive moved the change root to the dated archive folder. This phase edited **no** product path and **no** canonical spec — the only file it wrote is this report.

## Preconditions (all satisfied — actual output)

| Gate | Command / source | Actual output |
| --- | --- | --- |
| Verify report resolves and passes | `verify-report.md` envelope at head | `verdict: pass_with_warnings`, `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 5/5`; no unresolved `FAIL` / `BLOCKED` / `CRITICAL`; the single warning class (W1–W5) is dispositions-tracked, not a verification blocker |
| File-backed sync completed | `sync-report.md` (status **SYNCED**) | present; CI-09 block + 5 mapping rows + 4 CI-07 spans promoted into `openspec/specs/ci/spec.md`; change deliberately stayed active |
| Canonical carries CI-09 | `grep -c "^\| CI-09 \|" openspec/specs/ci/spec.md` | **`5`** (requirement at `:374`, rows `:526–530`) |
| Retired literal absent canonically | `grep -c '"3\.10"' openspec/specs/ci/spec.md` | **`0`** (all remaining `3.10` tokens are backticked prose naming the `requires-python` floor / `.python-version` rationale) |
| Canonical structure grows as recorded | `grep -c '^### Requirement:'` → **`9`**; `grep -c '^#### Scenario:'` → **`31`**; `wc -l` → **`530`** | matches `sync-report.md`'s self-check exactly (was 8 / 26 / 400) |
| Fresh native `gentle-ai sdd-status` v2 (consumed read-only, not recomputed) | `gentle-ai sdd-status --cwd "C:\Users\elaze\Desktop\sofer"` at archive launch | `next: archive`; `apply: blocked`; `verify: all_done`; **`archive: ready`**; `tasks: 50/50 complete`; `artifacts.verifyReport: done`; `remediationState.required: false`; `nextRecommended` = archive instruction block |
| `actionContext` | native status JSON | `mode: repo-local` (not `workspace-planning`, so no `allowedEditRoots` deficit applies); `workspaceRoot: C:\Users\elaze\Desktop\sofer`; `allowedEditRoots: ["C:\Users\elaze\Desktop\sofer"]`; the move target and this report resolve inside that root |
| **Final Task Completion Gate** (re-read immediately before the move) | `grep -c "^\s*- \[ \]" …/tasks.md` → **`0`**; `grep -c "^\s*- \[x\]"` → **`50`** | **zero unchecked implementation task lines**; `tasks.md` sha256 `37128ee24d5cc63bea2b6804069311e88a2738090dbe51573cce9e827969b0d9` (unchanged by the move) |
| Closing evidence for the by-design pre-sync red (G7) re-confirmed at archive time | `uv run pytest tests/test_ci_workflows.py -q` | **`30 passed in 0.23s`** (exit 0) — no `--deselect`, no mark, no test weakened; G7 is green because the canonical CI-07 clause now names the value `pyproject.toml` declares |
| Legacy flat spec | change-root inventory | none — the change carries the domain delta `specs/ci/spec.md`, never a flat `spec.md` |
| Archive-name collision | `ls -d openspec/changes/archive/2026-09-15-chore-type-gate-policy` (pre-move) | `No such file or directory` — **no collision** |
| Active-change collisions | `ls -1 openspec/changes/` (pre-move) | `2026-09-15-chore-type-gate-policy` and `archive` only |
| Same-domain active changes | `find … -path "*/specs/ci/spec.md" -not -path "*/archive/*"`; native `relationships.sameDomainActiveChanges` | exactly the one change being archived; **`[]`** in native status — no sync/archive ordering decision needed |
| `rules.archive` (`openspec/config.yaml`) | config read | *"Warn before merging destructive deltas"* — **not triggered by archive**: the CI-09 promotion is purely additive and the CI-07 spans were the already-approved, parent-authorized exception recorded in `sync-report.md` and `apply-progress.md` COR-4/COR-8 |
| Path-reference safety of the move | `grep -n "openspec/changes"` over canonical `openspec/specs/ci/spec.md`, `AGENTS.md`, delta | no match — the move creates **no stale path reference** |

**No archive-time sync fallback was run** (`sync-report.md` already existed and is SYNCED), **no mechanical checkbox repair was performed**, and **no stale-checkbox reconciliation was needed or claimed** — the Final Task Completion Gate found zero `- [ ]` lines on a re-read taken immediately before the move.

## Artifacts read

- `proposal.md` (41,034 B), `explore.md` (43,888 B), `design.md` (103,507 B, revision 2 + §COR-5/§COR-7), `tasks.md` (57,578 B)
- `specs/ci/spec.md` (22,633 B; `## ADDED` CI-09 with 5 scenarios + 5 Test Mapping rows, `## MODIFIED` CI-07) — sha256 `2b78e4bf91f2ba663df899b1aab4e9300a59d96e6bb2fb7afa8bdcfa242c34ad`
- `evidence-type-gate-baseline.md` (15,785 B; §8 authoritative post-maintainer-edit re-measurement)
- `apply-progress.md` (11,739 B, including §6's post-verify dispositions W1–W5 and the explicitly accepted `size:exception`)
- `verify-report.md` (31,661 B), `sync-report.md` (22,518 B)
- `openspec/config.yaml` (`strict_tdd: false`, `rules.archive`, `rules.verify.build_command`)
- Canonical `openspec/specs/ci/spec.md` (read-only confirmation of CI-09 + the CI-07 amendment; sha256 `c906bfe756cc5845a9846ba37367e6521afa5d0e26419530c9614314ee916989`)
- `openspec/changes/archive/2026-09-15-chore-cov01-floors-status-quo/` (the #215 archived precedent for folder naming and report layout, alongside #216 `2026-09-15-chore-ruff-format-hook-scope` and `2026-09-15-chore-ruff-single-authority`)

## Structured status and `actionContext` findings

Native `gentle-ai.sdd-status` v2 was consumed read-only before phase work and was **current** for the archive decision (`next: archive`, `archive: ready`, `tasks: 50/50`) — the stale-snapshot problem `sdd-sync` recorded did not recur.

- `dependencies.apply: "blocked"` and the single live `blockedReasons` entry (`native SDD runtime execution is blocked(maintainer_decision) … this work unit's attempt or changed-line budget needs a maintainer decision …`) concern the **apply work-unit attempt/changed-line accounting** — the same accounting verify's **W5** and `sync-report.md`'s §Remaining-risks-2 name. They are **not** archive blockers: the selected action is `archive` with `archive: ready`, and the human decision W5 demanded was recorded — the maintainer explicitly accepted a single PR carrying `size:exception` (see *Destructive-merge and exception accounting*). This archive phase did not clear, reset, or reinterpret that runtime accounting; it is surfaced to the parent verbatim.
- The move target and this report path resolve inside the authoritative root; no write left `allowedEditRoots`.
- The native status reports `artifactStore: openspec` while the session preflight declares **hybrid**: both halves ran — the filesystem move + this file (openspec half) and the Engram record (hybrid half).
- **Post-move informational note (not a blocker):** re-running `gentle-ai sdd-status` after the move reports `## SDD Status: unresolved`, `next: sdd-new`, `apply/verify/archive: blocked`, `tasks: 0/0`. This is the expected **terminal** state of a successfully archived change — the artifact root now lives under `archive/`, which the status engine does not scan as an active change. The authoritative archive-readiness snapshot is the pre-move one above.

## Domains synced

Exactly one domain: **`ci`** → `openspec/specs/ci/spec.md`, performed by **`sdd-sync`** (**not** by this phase). This phase edited **no** canonical spec and no product file.

| Kind | Requirement names |
| --- | --- |
| ADDED | `Type-gate posture — \`tests/\` excluded from both type gates and pyright adopted as a real gate (CI-09)` — with scenarios `` `tests/` stays out of both type gates ``, `` `[tool.pyright]` declares the decided posture and the gate runs ``, `Exactly one pyright config home exists`, `The pin is exact, reaches CI through the lock, and matches the running binary`, `Adopting the gate leaves every existing gate declaration intact` |
| MODIFIED | `Dev interpreter pin matches the gate interpreter (CI-07)` — four spans only: the `[tool.mypy] python_version` clause (`"3.10"` → `"3.11"`, COR-7 join resolved), the backticked `(Previously: …)` marker, the `> Modified by …` blockquote line, and the `User-facing support is unchanged` scenario bullet |
| REMOVED | *(none)* — the only deletions are CI-07's two stale clause lines, replaced in place |
| RENAMED | *(none)* |

**Destructive-merge guard.** The single MODIFIED requirement touched four spans; the removed/replaced material is the stale `"3.10"` clause (2 deleted lines) inside a 132-insertion / 2-deletion canonical diff. Affected requirement named above, line count disclosed, and the parent prompt records **explicit approval** for this destructive-but-authorized edit (design §6.6 / DC-11, `apply-progress.md` COR-4, `sync-report.md`'s gate table). No scenario was dropped from the MODIFIED requirement: the delta restated the full clause and the scenario bullet, and `sync-report.md` verified the untouched remainder byte-level (`.python-version` = `3.13` equality clauses, flag-free mypy paragraph, COV-06-script paragraph, AGENTS-rule-12 latent-issue paragraph, the four other scenario bullets, and CI-07's existing Test Mapping row all intact).

The **W2 reconciliation was carried into the promoted text and not lost by the move**: `sync-report.md` confirms the canonical CI-09 clause group Q2 says **four** `try:` / `except ImportError:` fallback sites (`cli.py`, `config.py`, `mcp_registration.py`, `model.py`) with `mcp_server.py`'s version-gated fallback needing no stub — the false "five fallback sites" wording is **not** canonical. No canonical clause this archive leaves behind is false on the committed tree.

## Active same-domain change warnings

**None.** Native `relationships.sameDomainActiveChanges: []`; `find` over non-archived change roots found exactly one `specs/ci/spec.md` — the change being archived; and after the move `ls -1 openspec/changes/` returns **`archive` only**. No other active change can race the `ci` capability.

## Archive move

```text
BEFORE: openspec/changes/2026-09-15-chore-type-gate-policy/
AFTER:  openspec/changes/archive/2026-09-15-chore-type-gate-policy/
```

- **Method: plain `mv`** (not `git mv`, not committed). The parent prompt described the folder as *mixed* tracked/untracked; the measured state is **entirely untracked** — `git ls-files openspec/changes/2026-09-15-chore-type-gate-policy/` returned **nothing** (pre-move `git status --porcelain` showed `?? openspec/changes/2026-09-15-chore-type-gate-policy/`). A plain move is therefore correct: no tracked path changed, no rename detection is required, and nothing was staged.
- **Folder name equals the change name**, which already embeds its date (`2026-09-15-chore-type-gate-policy`) — matching the archived precedents `2026-09-15-chore-cov01-floors-status-quo` (#215), `2026-09-15-chore-ruff-format-hook-scope` (#216) and `2026-09-15-chore-ruff-single-authority`. **No double date prefix.**
- No archived change was deleted or modified; the whole move is one directory rename. Filesystem confirmation: the old path now reports `No such file or directory`; the new path exists.
- **Report-authoring order (intentional, parent-instructed):** the parent prompt directed this report to be written at the **archived** path, so it was authored *after* the move and describes the move as completed. The archived inventory below therefore lists it as the last arrival rather than as a file carried by the rename.
- Post-move `git status --porcelain` (scoped to the relevant paths):

```text
 M openspec/specs/ci/spec.md
?? openspec/changes/archive/2026-09-15-chore-type-gate-policy/
?? typings/
```

The `??` archive tree is the whole arrived change (all nine artifacts, all untracked before and after); `M openspec/specs/ci/spec.md` is `sdd-sync`'s promotion, untouched by this phase. Nothing is committed by this phase.

## Final inventory of the archived folder

Every file under `openspec/changes/archive/2026-09-15-chore-type-gate-policy/` (9 pre-existing artifacts + this report = 10 files):

| # | File | Bytes | Note |
| --- | --- | --- | --- |
| 1 | `explore.md` | 43,888 | phase artifact |
| 2 | `proposal.md` | 41,034 | phase artifact |
| 3 | `design.md` | 103,507 | revision 2 blueprint + §COR-5/§COR-7/§COR-8 addenda |
| 4 | `evidence-type-gate-baseline.md` | 15,785 | §8 authoritative baseline re-measurement |
| 5 | `tasks.md` | 57,578 | 50/50 checked, 0 unchecked; sha256 `37128ee2…` (unchanged by the move) |
| 6 | `specs/ci/spec.md` | 22,633 | the **domain delta** (CI-09 ADDED + CI-07 MODIFIED), sha256 `2b78e4bf…` — moved with the folder; note it is *not* the canonical file |
| 7 | `apply-progress.md` | 11,739 | includes §6 W1–W5 dispositions and the accepted `size:exception` |
| 8 | `verify-report.md` | 31,661 | `pass_with_warnings`, 0 blockers |
| 9 | `sync-report.md` | 22,518 | SYNCED; G7 before/after evidence |
| 10 | `archive-report.md` | *(this file)* | written into the archived folder after the move |

## Canonical spec is untouched by the move

```text
sha256 (pre-move)  : c906bfe756cc5845a9846ba37367e6521afa5d0e26419530c9614314ee916989  openspec/specs/ci/spec.md
sha256 (post-move) : c906bfe756cc5845a9846ba37367e6521afa5d0e26419530c9614314ee916989  openspec/specs/ci/spec.md
grep -c "| CI-09 |" (post-move): 5        # requirement :374 + rows :526–530
grep -c '"3.10"'    (post-move): 0        # the retired literal stays gone
git diff --stat -- openspec/specs/ci/spec.md: 1 file changed, 132 insertions(+), 2 deletions(-)
git diff --name-only -- openspec/          : openspec/specs/ci/spec.md   # the ONLY changed path under openspec/
```

The pre-move and post-move canonical hashes are **identical** and the only canonical diff in the tree is `sdd-sync`'s already-recorded promotion. The archive move touched no canonical byte: the delta under `specs/ci/spec.md` inside the change root is a *change-scoped* artifact and its relocation does not affect the capability spec at `openspec/specs/ci/spec.md`.

## Destructive-merge and exception accounting

- **Destructive canonical merge approval: recorded and precedented.** The CI-07 amendment replaced two stale clause lines in place; the parent prompt authorized it, `apply-progress.md` records it as COR-4 ("amend **inside this change** as a recorded, authorized exception"), `design.md` §6.6/DC-11 carries the rationale, and `sync-report.md`'s gate table records the approval. Archive neither added nor assumed any further destructive authorization.
- **`size:exception`: explicitly accepted by the maintainer (2026-09-15).** The raw delivered diff is **1907 insertions / 49 deletions = 1956 changed lines across 18 tracked files** (the 17 apply-touched paths + `openspec/specs/ci/spec.md`), of which **415** excluding the maintainer's `uv.lock` regeneration — both above the 400-line canonical threshold, and `1956` above the 1500-line session review budget. `apply-progress.md` §6's W5 entry records the maintainer's explicit acceptance of a single PR carrying `size:exception`, with the decomposition disclosed for the PR body. Archive treats that gate as satisfied by the recorded human decision, never inferred.
- **Zero unchecked implementation tasks**, so no stale-checkbox reconciliation, no mechanical checkbox repair and no archive-time sync fallback occurred.

## Commit plan (parent-owned)

Nothing was committed; the move is unstaged. The parent lands **ONE commit** on `chore/201-type-gate-policy`:

1. the **guard block** — `tests/test_ci_workflows.py` (+279/−8; G1–G7 and the module-docstring enumeration reconciled);
2. the **configuration, stub, CI and hook changes** — `pyproject.toml` (`[tool.pyright]`, the exact `mypy==2.3.0` / `pyright==1.1.414` dev pins, the maintainer's `strict = true` + `python_version = "3.11"` and dependency edits), `typings/tomli-stubs/__init__.pyi` + the sdist exclusion, `.github/workflows/ci.yml` (`run: uv run pyright`), `.pre-commit-config.yaml` (the pyright hook), `uv.lock`;
3. the **17-site source cleanup** across `src/sofer/` (`_clean.py`, `_converters.py`, `_mirror.py`, `mcp_server.py`, `prepare.py`, `publish.py`, `verification.py`);
4. the **docs** — `CONTRIBUTING.md` §Type checking, `AGENTS.md` rules 5 + 12, the mirrored `README.md` / `README_ES.md` bullet, `.github/PULL_REQUEST_TEMPLATE.md` checklist item;
5. the **canonical promotion** — `openspec/specs/ci/spec.md` (`132 insertions(+), 2 deletions(-)`), already on disk from `sdd-sync`;
6. **this archive trail** — the rename of `openspec/changes/2026-09-15-chore-type-gate-policy/` → `openspec/changes/archive/2026-09-15-chore-type-gate-policy/` with all ten artifacts above (all untracked, so `git add -A` simply adds them at the new path).

The commit carries the maintainer's **accepted `size:exception`**, and the PR body must disclose the overage decomposition plus the three `tasks.md` §Parent-owned-steps disclosures (`strict = true` coupling, the DC-8 stub-layout step taken, and R12's reading of CI-07's diff-scope clause). **The canonical promotion must not be separated from the archive move**: G7 asserts the canonical clause against `pyproject.toml`, so a commit carrying the config without the canonical clause would leave the branch red.

## Engram traceability

- Topic key: `sdd/2026-09-15-chore-type-gate-policy/archive-report`
- Observation id: **`1301`**, type `archive`, project `sofer`, scope `project`, `capture_prompt: false`
- Upstream observation ids recorded by their owning phases (per their reports): design **#1297**, proposal **#1296**, explore **#1295**, plus the `verify-report` and `sync-report` mirrors under `sdd/2026-09-15-chore-type-gate-policy/…`
- The Engram body is this report verbatim minus this one-line self-reference, which can only be added after the save returns the id. This file is the canonical record; the topic key is the stable cross-reference if the id ever changes on upsert.

## Risks

1. **Not committed.** The archive move, the canonical `openspec/specs/ci/spec.md` promotion, the source/doc changes and the whole archived change tree are uncommitted working-tree state; a hard reset would lose the canonical promotion and the audit trail. The single commit above is mandatory.
2. **The recorded app-side `blockedReasons` entry is unresolved at the runtime layer.** The apply work-unit attempt/changed-line accounting still reports `maintainer_decision`, even though the human decision it demanded (`size:exception`) is recorded in `apply-progress.md` §6. Clearing the runtime accounting is a maintainer `sdd-attempt reset`, not an archive action; if the parent expects the status engine to go quiet, it must do that explicitly.
3. **W1/W3 remain adjudicated but not re-authored.** The shipped `_converters.py` / `mcp_server.py` resolutions diverge from `design.md` §5.2's frozen sketch; `apply-progress.md` §6 records them as COR-8 (measurement-driven falsification of DC-10's premise) and W3's SC-4c probe as superseded by measurement. Both gates are green (`uv run mypy src/ scripts/` exit 0, `uv run pyright` exit 0). Archive did **not** rewrite `design.md`; a reader of the frozen blueprint will still see the divergence.
4. **Version-dependent resolution at `mcp_server.py`.** The `sys.version_info >= (3, 11)` gate hides the untyped `tomli` arm from a 3.11/3.13 analysis only; a future mypy run pinned to 3.10 could re-open `no-any-return` there, whereas the design's binding annotation would not.
5. **Delivery budget.** 1956 changed lines against the 400-line canonical threshold and the 1500-line session budget. The accepted `size:exception` is recorded, but the PR remains large enough that reviewer attention on the six substance files is the real cost.
6. **Issue #201 stays open.** Delivery (commit + PR) is parent-owned; the archive does not close it.

## Next recommended

**Delivery (parent-owned): the single commit + PR.** Land the one commit described above on `chore/201-type-gate-policy` and open the PR closing #201, disclosing the accepted `size:exception` and the three mandated PR-body items. No further SDD phase is required. This `hybrid` archive is complete: the change root is moved to `openspec/changes/archive/2026-09-15-chore-type-gate-policy/`, the canonical `ci` spec already carries CI-09 plus the CI-07 amendment, G7 is green (`30 passed`), and the Engram record is saved as observation `1301`.
