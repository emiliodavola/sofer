# Feature: visibility-enforcement — issue #338

**Branch:** `feat/338-visibility-enforcement` from `dev@ec511e7`
**Issue:** `emiliodavola/sofer#338` — *feat(publish): private and confidential must be enforced defaults; only explicit user authorization may change them*
**Delivery PR:** pending — assigned to `@emiliodavola`
**SDD change:** `openspec/changes/2026-10-17-feat-visibility-enforcement/`
**Phase:** 3 of the 2026-10-17 batch (last: the largest, the only one that changes a default and adds a tool)

## Goal

Visibility is a one-way, unverified config value. `private` is read from `[dataset]` and passed only to
`create_repo(..., exist_ok=True)`, which is a no-op on an existing repository; nothing compares the
configured value with the repository's actual state; the publish plan never prints it;
`sofer_auth_status` never reports it; `META_KEYS` cannot even express it. A corpus was uploaded with
`[dataset] private = false` because the request was read as "upload it". The maintainer's requirement is
that repositories are private and confidential by mandate, and that only an explicit user authorization
changes that.

## Specs

S1 (#338, verbatim): "**repositories are private and confidential by mandate; only an explicit user
authorization may change that state.**"

S2 (#338, verbatim): "**Enforce the defaults, fail closed.** Treat `private = false` and
`confidential = false` in `[dataset]`/`[meta]` as explicit opt-outs that require their own authorization
value (e.g. `allow_public = true`, or a required `public_reason`), so the intent lives in the config and
in the report instead of being a plain boolean anyone can flip."

S3 (#338, verbatim): "**Compare and show the remote state.** `sofer_auth_status` and the publish dry-run
plan should print the configured visibility, the *current* remote visibility, and the confidential flag.
`sofer_publish_confirm` should fail closed when they differ on an existing repo (exactly the case
`create_repo` cannot fix), naming the required human action."

S4 (#338, verbatim): "**Add an MCP tool for the posture**, e.g. `sofer_repo_settings(config, dry_run)`,
to read the remote visibility/permissions and to set it only when the call carries an explicit,
verifiable authorization (approval phrase + the exact target state). Reading it should never require
authorization."

S5 (#338, verbatim): "**Default `confidential = true`** in the init template with the same opt-down
requirement, and make the `acknowledge_risk` wording accurate: acknowledge the upload, and separately
acknowledge a *public* target when that is the case."

S6 (#338, verbatim): "**Record the posture** (configured, observed, acknowledged) in the publish
report/manifest so it is auditable after the fact."

## Measured baseline (2026-10-17, `dev@ec511e7`)

| Fact | Evidence |
| --- | --- |
| `private = false` is accepted and never compared | `model.py:561` `private=ds.get("private", True)`; only a bool type-check (`model.py:714-716`); 0 hits for `private` in `checks.py`/`verification.py` |
| `META_KEYS` cannot express visibility | `meta_edit.py:88-110` has `confidential: "flag"` and no `private` |
| The value reaches only `create_repo` | `publish.py:123` (docstring), `:135` (`private=cfg.private, exist_ok=True`) |
| The plan never shows visibility | `_repo_diff_summary` (`publish.py:355-365`) |
| `auth_status` never shows it | envelope at `mcp_server.py:2414-2426` |
| The settings route **does** exist | `HfApi.update_repo_settings` → `PUT {endpoint}/api/{repo_type}s/{repo_id}/settings` (`hf_api.py:4849`); present in `huggingface-hub==0.26.0` (the declared floor, verified in a throwaway env) and in installed 2.2.0 |

## Tasks

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | RED: `private = false` without an authorization reason is refused, naming the missing key | S2 | pending | — |
| T2 | RED: `confidential = false` without an authorization reason is refused; the init template writes `confidential = true` | S2, S5 | pending | — |
| T3 | RED: the publish plan and `sofer_auth_status` print configured + observed visibility + confidential | S3 | pending | — |
| T4 | RED: publish fails closed when configured and observed visibility diverge on an existing repo | S3 | pending | — |
| T5 | RED: `sofer_repo_settings` reads the posture without authorization, and refuses a write without the approval phrase + exact target state | S4 | pending | — |
| T6 | RED: `sofer_repo_settings` writes via `update_repo_settings`, and fails closed with a named reason when the installed SDK has no such method | S4 | pending | — |
| T7 | RED: a public target requires its own acknowledgement; `acknowledge_risk` alone no longer reads as public consent | S5 | pending | — |
| T8 | GREEN: authorization keys (`[dataset].public_reason`, `[meta].confidentiality_reason`), fail-closed validation, model default flip | S2, S5 | pending | — |
| T9 | GREEN: observed visibility in the plan, `auth_status`, and the divergence gate | S3 | pending | — |
| T10 | GREEN: `sofer_repo_settings` tool + roster/workflow/schema guards + `_PHASED_INSTRUCTIONS` | S4 | pending | — |
| T11 | GREEN: posture recorded in the publish report and the manifest | S6 | pending | — |
| T12 | Specs `publish` + `mcp-server` + `metadata`; README + README_ES (rules 7/13); new tool documented in both READMEs | S1-S6 | pending | — |
| T13 | Gates: pytest, ruff, mypy, pyright, coverage (rule 14: `publish.py` + `cli.py` at 100.00%), commit slices, push, PR assigned to `@emiliodavola` | — | pending | — |

## Decisions

- **D1 — the authorization value is a required reason string, not a boolean.** When `private = false`,
  `[dataset].public_reason` must be non-empty; when `confidential = false`,
  `[meta].confidentiality_reason` must be non-empty. A boolean flag can be flipped by the same accident
  the issue reports; a reason is a statement that gets echoed into the plan, `auth_status` and the
  manifest, so the intent is auditable after the fact (S6). The issue offers both forms
  ("`allow_public = true`, or a required `public_reason`"); the reason form carries S2's "so the intent
  lives in the config and in the report" without a second key per bit.
- **D2 — the model default flips to `confidential = True`.** The init template does (S5), and letting
  the dataclass default disagree with the template would leave every hand-written TOML on the old
  permissive default. This is a breaking change for existing configs — they must either declare
  `confidential = true` (no-op) or add `confidentiality_reason` — and it is documented as such in the
  PR body and both READMEs (rule 12, pre-1.0 minor).
- **D3 — the settings write uses the SDK, with feature detection.** `HfApi.update_repo_settings` exists
  in the declared floor; the code calls it only when present and otherwise fails closed naming the
  required `huggingface-hub` upgrade, so the "route is absent" case degrades into a named action instead
  of an exception. The correction recorded on the issue stands: the route exists, the earlier 404 came
  from a URL without the `/settings` suffix.
- **D4 — reads are free, writes are not.** `sofer_repo_settings(dry_run=true)` (the default) needs no
  approval phrase; the write path requires the phrase plus the exact target state, matching the
  publish gate, and is never reachable from a read.
- **D5 — divergence is a refusal, not a warning.** On an existing repo the publish refuses when the
  observed visibility differs from the configured one, naming the required human action. Here
  `create_repo` cannot fix it, which is the whole reason the state diverges invisibly today.
- **D6 — `acknowledge_risk` keeps its name and loses its lie.** It acknowledges the upload (irreversible
  overwrite of the target); a public target additionally requires `acknowledge_public`, and the
  confidential flag keeps `acknowledge_confidential`. Renaming the existing parameter would break every
  documented chain for no gain.

## Log

- **L1** (user, verbatim): "revisá los issues pendientes e armate un roadmap de implementación, no
  confies en lo que dicen, chequeá a partir de ellos y asegurate que digan lo correcto, sino modificalos

  necesito una rama por issue y luego un push y PR (asignado a mi) por implementación"
- **L2** (user, verbatim): "usá ODD obligatoriamente"
- **L3** — verification (2026-10-17): every claim checked against `dev@ec511e7`; #133 and #148 are
  already closed, so this is the remaining fail-closed gap. Two corrections applied to the issue:
  (a) the Hub settings route **does** exist (`update_repo_settings` → `PUT .../settings`, present at the
  declared floor) — the observed 404 came from `/api/datasets/<repo_id>` without `/settings`;
  (b) `private` defaults `true`, so the posture is not "both bits default open" — only `confidential`
  defaults permissive. Evidence appended to the issue body.
