# Pre-proposal state: 2026-09-15-chore-ruff-format-hook-scope

schema: gentle-ai.sdd-preproposal/v1
revision: 2
date: 2026-09-15

## Exploration reference

- OpenSpec: `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/explore.md` (revision 1)
- Engram: observation id 1275, project `sofer`, topic_key `sdd/2026-09-15-chore-ruff-format-hook-scope/explore`, revision_count 1
- SHA-256 of explore.md file bytes: `48178a7cb4fe5374aff1e07640f2be2d74975968a4042c887ff2397569a57a71`

## Research request and admission

- Selected class: open-web (`web_search`, `source_check`, `fetch_content`, `get_search_content`); documentation class not selected.
- Questions R1–R3: **blocked** (harness defect — declared web tools not bound in the child session; denial-record write refused). Zero validated web claims; nothing fabricated.
- Defect report (user-consented): Gentleman-Programming/gentle-ai#4633.
- R4: deferred-local to the verify phase.
- Full record: `openspec/changes/2026-09-15-chore-ruff-format-hook-scope/research.md` (schema `gentle-ai.sdd-research/v1`, outcome `blocked`).

## User evidence-strategy override (2026-09-15, explicit, supersedes the blocked web class)

The user chose **LOCAL EMPIRICAL EVIDENCE** over blocking the change:

- R1 (load-bearing `types_or` replace-vs-merge): empirically validated in the **verify phase** using the
  issue's own acceptance check against the real ruff 0.16.7 hook materialised on this machine:
  `uv run pre-commit run ruff-format --files README.md` must report the file as not a hook input
  (Skipped / no files to check), and `uv run pre-commit run ruff-format --all-files` must show no
  markdown batch (no "2 files reformatted"). Directly-observed behaviour of the pinned hook is stronger
  evidence of the override's effect than a docs citation would be.
- R2 (exact type tags): validated against the locally installed `identify` package in the verify phase
  (the same library pre-commit uses for tag resolution).
- R3 (upstream markdown history): remains bracketed by locally cached upstream manifests (absent at
  0.15.21, present at 0.16.6); recorded as local-cache evidence, no external citation.

Rationale: the user's standing rule is "never decide without evidence". The strategy above gives the
load-bearing semantic directly-observed evidence on the pinned toolchain, satisfying that rule without the
unavailable web lane.

## Product decisions

- **confirmed (user, 2026-09-15)**:
  - Option (a) for issue #216: narrow the `ruff-format` hook with an explicit `types_or` in
    `.pre-commit-config.yaml` so it no longer sees Markdown; document the decision durably; stay consistent
    with `[tool.ruff] extend-exclude = ["openspec"]`.
- **confirmed (user, 2026-09-15, revision 2)**:
  - Durable home: **spec `process-boundary`** — new requirement `PB-13` (the capability that already owns
    formatter integrity; PB-10 names this exact hook as the enforcement surface; #177 precedent chose
    process-boundary for no-CI-step changes). `process-boundary` has no Test Mapping table yet → the
    proposal creates one (or maps the scenario as verify-phase static evidence). The guard test lands in
    `tests/test_ci_workflows.py` (its established home). A YAML comment next to the hook entry is included
    in every case (cheap, on the edited line, `extend-exclude` comment precedent).
  - Guard test shape: **key present + no markdown** — assert the hook entry declares `types_or` AND
    `"markdown" not in types_or`. Asserts the defect class directly; does not go stale on legitimate
    future scope widening.

## Evidence references

- `explore.md` (above) — all in-repo surfaces verified there with file:line evidence.
- Issue #216 body (repository `emiliodavola/sofer`) — options table and acceptance criteria.
- Locally cached upstream `ruff-pre-commit` manifests at revs 0.8.0 / 0.15.21 / 0.16.0 / 0.16.6 / 0.16.7
  (local pre-commit cache; brackets R3).

## proposal_ready

**true** (revision 2) — basis: user-confirmed option (a); user-confirmed local-empirical evidence strategy
with explicit validation paths for R1–R2 and a local bracket for R3 (web lane blocked by reported harness
defect gentle-ai#4633); zero unvalidated web claims; both pending product decisions (durable home,
guard shape) confirmed by the user in revision 2. `sdd-proposal` may launch.
