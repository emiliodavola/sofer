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
| T1 | RED: `private = false` without an authorization reason is refused, naming the missing key | S2 | **done** | RED against the pre-slice code: `AssertionError: []` (the refusal produced no error) and `AttributeError: 'DatasetConfig' object has no attribute 'public_reason'`. GREEN: `TestVisibilityAuthorization` (8 passed) |
| T2 | RED: `confidential = false` without an authorization reason is refused; the init template writes `confidential = true` | S2, S5 | **done** | RED: `assert 'confidential = true' in …` on the old template, `AttributeError: … 'confidentiality_reason'`, `AssertionError: []` for the explicit-`false` case. GREEN: `TestVisibilityAuthorization` + `TestInitTemplatePosture` (2 passed) |
| T3 | RED: the publish plan and `sofer_auth_status` print configured + observed visibility + confidential | S3 | **done** | RED: `KeyError: 'private'` (the fields did not exist) and, once they did, the tool's declared `output_schema` **filtered them** until they were declared there too. GREEN: `TestPostureLines` (4) + `TestAuthStatusRemoteVisibility` (6) |
| T4 | RED: publish fails closed when configured and observed visibility diverge on an existing repo | S3 | **done** | GREEN: `TestTargetPostureGate` (3) — divergence refuses with rc 1 and `upload_folder` is asserted never called; agreement proceeds rc 0; a public config against a private repository is refused too |
| T5 | RED: `sofer_repo_settings` reads the posture without authorization, and refuses a write without the approval phrase + exact target state | S4 | **done** | GREEN: `TestRepoSettingsTool` — the read needs no phrase; a write without it returns `REPO_SETTINGS_APPROVAL_REQUIRED` and writes nothing; a dry run predicts without writing; no token is `REPO_SETTINGS_TOKEN_REQUIRED` |
| T6 | RED: `sofer_repo_settings` writes via `update_repo_settings`, and fails closed with a named reason when the installed SDK has no such method | S4 | **done** | GREEN: the write records `private`/`repo_type` and reports `changed` plus `diverges_from_config`; a legacy `HfApi` yields `REPO_SETTINGS_UNSUPPORTED` naming the method; a write failure yields `REPO_SETTINGS_WRITE_FAILED` with the cause |
| T7 | RED: a public target requires its own acknowledgement; `acknowledge_risk` alone no longer reads as public consent | S5 | pending | — |
| T8 | GREEN: authorization keys (`[dataset].public_reason`, `[meta].confidentiality_reason`), fail-closed validation, template default (D2 revised: no dataclass flip) | S2, S5 | **done** | commit `1385f12`. `declared_dataset_keys` is the presence signal that tells an explicit `false` from a TOML that never mentions visibility; `confidentiality_reason` joined `META_KEYS` so `sofer_meta_set` can write it; the validator warns when no posture is stated. Fixture fallout cleared (46 failures → 0): the shared `conftest` helper and two test-local TOMLs now state the reason |
| T9 | GREEN: observed visibility in the plan, `auth_status`, and the divergence gate | S3 | **done** | `_repo_visibility` (fail-closed probe: only not-found answers), `_posture_lines` (the plan block; the dry run says "not read", D8), the gate after the plan print and before staging, `sofer_auth_status(check_remote=...)` carrying `private`/`public_reason`/`confidentiality_reason`/`remote_visibility`. Eight fake-api sites now stub `repo_info` through the shared conftest `repo_info_private` |
| T10 | GREEN: `sofer_repo_settings` tool + roster/workflow/schema guards + `_PHASED_INSTRUCTIONS` | S4 | **done** | Registered as the 18th tool with its declared `output_schema`; workflow metadata + the `delivery` branch; `_PHASED_INSTRUCTIONS` posture paragraph; guards updated (roster counts → 18 in three test files with the "seventeen" names renamed, `_WRITING_TOOLS`, `_EXPECTED`, `CANONICAL_TOOLS`, the parity `AreaParity` entry) and both READMEs |
| T11 | GREEN: posture recorded in the publish report and the manifest | S6 | pending | — |
| T12 | Specs `publish` + `mcp-server` + `metadata`; README + README_ES (rules 7/13); new tool documented in both READMEs | S1-S6 | pending | — |
| T13 | Gates: pytest, ruff, mypy, pyright, coverage (rule 14: `publish.py` + `cli.py` at 100.00%), commit slices, push, PR assigned to `@emiliodavola` | — | pending | — |
| T14 | The writer cannot produce an unauthorized opt-out: `sofer_meta_set` refuses `confidential = false` without a reason in the same written state | S2 | **done** | RED then GREEN: `TestPostureAuthorizationOnWrite` (5). The guard lives in `apply_meta_edit`, before the atomic replace, so the CLI and the MCP tool share it; one CLI test that opted out now states its reason |

## Decisions

- **D1 — the authorization value is a required reason string, not a boolean.** When `private = false`,
  `[dataset].public_reason` must be non-empty; when `confidential = false`,
  `[meta].confidentiality_reason` must be non-empty. A boolean flag can be flipped by the same accident
  the issue reports; a reason is a statement that gets echoed into the plan, `auth_status` and the
  manifest, so the intent is auditable after the fact (S6). The issue offers both forms
  ("`allow_public = true`, or a required `public_reason`"); the reason form carries S2's "so the intent
  lives in the config and in the report" without a second key per bit.
- **D2 — the default changes in the template, not in the model, and an explicit opt-out carries the
  reason.** The issue asks for `confidential = true` **in the init template** (S5) and for *explicit*
  opt-outs to require an authorization value (S2). Flipping the dataclass default instead would silently
  re-mark every existing TOML and force `acknowledge_confidential` on every publish — a global posture
  change nobody asked for, whose blast radius is every documented chain. So: the template writes `true`;
  an explicit `[meta] confidential = false` requires a `confidentiality_reason`; a TOML that never
  mentions the key keeps its own default and the validator surfaces that absence as a warning naming
  both ways to say it. `[dataset] private` is already fail-closed by default, and an explicit `false`
  requires `public_reason`.
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
- **D8 — the dry run stays network-free; the observed state lands where the network already is.**
  `publish --dry-run` is documented and tested as token-free and offline, so it prints the configured
  posture and says the remote was not read. The observed visibility appears in the **confirm** plan
  (which inspects the repository anyway) and in `sofer_auth_status(check_remote=true)`, the opt-in
  preflight a human runs before approving. Making the dry run reach the Hub would have traded a
  documented property for a line of output.

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
- **L4** — first slice delivered (commit `1385f12`, rebased onto the reworded `dev@903237e`): the
  authorization surface. Two things it settled against this plan: **(a) D2 revised** — the
  confidentiality default changes in the template, not in the dataclass, because flipping the dataclass
  would re-mark every existing TOML and force `acknowledge_confidential` on every publish, which
  "explicit opt-outs" does not ask for; the roadmap carries the same correction (`8d33082`). **(b)** the
  fallout was entirely test-side: 46 failures, all from TOMLs declaring `confidential = false` with no
  reason, so the shared `conftest` helper and two test-local TOMLs now state why. Gates at the commit:
  2439 passed / 9 skipped, TOTAL coverage 94%, the four rule-14 files at 100.00%, ruff/mypy/pyright clean.
- **L5** — second slice: the writer guard. `sofer_meta_set` could write `confidential = false` on its
  own and leave a config `validate()` must reject, so `apply_meta_edit` now refuses (before the atomic
  replace) unless the same written state carries a non-empty `confidentiality_reason`. It is a
  consequence of this change rather than a line in the issue, hence its own task row (T14): the tool
  must not be able to produce the state the validator refuses. RED captured first (`2 failed, 3
  passed`), then the guard; one CLI test that opted out had to state its reason.
- **L6** — third slice: the target-posture surface, and two findings worth keeping. **(a)** The tool's
  declared `output_schema` **filters** envelope fields it does not declare: the four new keys were
  silently dropped until they were added there, which is the same "registry + schema + docs move
  together" class the #323 finding recorded. **(b)** The first version of the no-token test reached the
  **real Hub** through a token stored on this machine and failed with a false "absent"; it now patches
  `_get_hf_token` and asserts the probe is never called, so the branch is pinned without the network.
  Added **D8**: the dry run stays network-free, so the observed state lives in the confirm plan and in
  `sofer_auth_status(check_remote=true)`.
- **L7** — fourth slice: the tool and its registration. Adding a tool bit back exactly where the #323
  finding predicted: the roster count was pinned in **five** places (three test files, two of them named
  `...seventeen...`), plus the read-only/writing partition, `CANONICAL_TOOLS`, the workflow metadata, the
  `delivery` branch, the CLI/MCP parity map and the declared `output_schema`. Reading is free and needs no
  phrase; a write needs the phrase **and** the exact state, and a legacy SDK fails closed naming
  `update_repo_settings` instead of raising an obscure `AttributeError`.
