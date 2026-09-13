# Proposal: 2026-09-12-fix-mcp-opencode-env

**Change:** `2026-09-12-fix-mcp-opencode-env` · **Branch:** `fix/147-opencode-env-warning` (base `dev`, PR-only)
**Scope: GitHub ISSUE #147 ONLY** — Fase 4 of `tmp/roadmap.md`. Issue #142 (`pi` agent, Fase 6) touches the same files (`mcp_registration.py`, `cli.py`, README) and is **explicitly NOT here**; this change must not overlap it beyond the files listed below.

## Intent

**Issue #147 (bug, verified by prior subagents — evidence in `tmp/TRACE.md`): `sofer mcp add --agent opencode` silently drops the publish environment.** When `HF_TOKEN` and/or `SOFER_MCP_APPROVAL_PHRASE` are set in the shell and the user chooses `--agent opencode`, the generated `opencode.json` registration carries **no environment at all**, so the MCP server process loses HF auth and the fail-closed approval-phrase gate (`PUBLISH_APPROVAL_NOT_CONFIGURED` in `tmp/TRACE.md` §2.2). The drop is **silent**: the command exits 0 and prints only the registration confirmation.

The roadmap (`tmp/roadmap.md`, Fase 4) defines the intended fix scope:

1. **Explicit warning** when `HF_TOKEN` / `SOFER_MCP_APPROVAL_PHRASE` are present **and** `--agent opencode` is chosen — opencode simply cannot receive env through the registration we generate; the warning MUST also appear in `--dry-run` output.
2. **README** documents the manual alternative (`environment` in `opencode.json`, with the plaintext-on-disk caveat) and the per-agent "opencode recibe no env" fact — prose in `README.md`, mirrored in `README_ES.md`, technical content stays English (AGENTS.md §13; the client-config table and entry shapes stay English in both files).
3. **Hard constraint: never persist secret VALUES** in generated plaintext configs — parity with the codex/gemini behavior (names, never values). Persisting `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` values into `opencode.json` is forbidden; so is any other format change that would start writing secrets.

This change is **warning + documentation**, not a registration-format change: the opencode entry shape stays `{type:"local", command:["sofer-mcp"], cwd}`. Issue #142 (`pi`, Fase 6) may later redesign the adapter table; this fix intentionally does not preempt it.

## Sources

### Issue

- **GitHub #147** (bug, open) — `sofer mcp add --agent opencode` silently drops `HF_TOKEN` / `SOFER_MCP_APPROVAL_PHRASE`; server loses HF auth + approval gate (evidence: `tmp/TRACE.md` — publish preflight `approval_configured:false` across 5 attempts; the opencode launch entry carried no env).

### Verified current state (re-verified this session against code, not taken on trust)

| Area | Location | Verified |
| ------ | ---------- | ---------- |
| `build_entry` env forwarding per agent | `src/sofer/mcp_registration.py:138-166` | opencode → `{type:"local", command:["sofer-mcp"], cwd}` — **no env field** (L158-159). codex → `env_vars` allow-list of env **NAMES** present in `env` (L161-162). gemini → `env` dict NAME → `$NAME` refs (L164-165). Values are never written for any agent. |
| `_ENV_KEYS` | `src/sofer/mcp_registration.py:38` | `["HF_TOKEN", "SOFER_MCP_APPROVAL_PHRASE"]` — the single source to reuse (no hardcoded names in `cli.py`). |
| `collect_env` | `src/sofer/mcp_registration.py:441-451` | Returns present, non-empty keys only. |
| `_cmd_mcp_add` (no warning today) | `src/sofer/cli.py:605-719` | `env = mcp_registration.collect_env()` at L657; env used only by `build_entry` for codex/gemini. **No branch ever warns when `agent == "opencode" and env`.** Dry-run guard at L699-701 prints only `DRY RUN  Would register <agent> at <path>` and skips — warning must be emitted before this branch to reach dry-run. |
| `--agent all` expansion | `src/sofer/cli.py:630-631` | Expands to `["opencode", "codex", "gemini"]` — opencode is always a member, so the warning must fire per-agent inside the loop (covers both `--agent opencode` and `--agent all`). |
| opencode never delegates | `src/sofer/mcp_registration.py:444-447` (`probe_native`), `:459-463` (`delegate_add`) | Both hard-return `False` for opencode → file-edit path always runs → warning placement before the probe is safe and correct. |
| Existing messages style | `src/sofer/cli.py:702-703` | Non-fatal notices use `!` prefix on **stderr**; fatal use `X`. Warning should follow the same convention and must NOT change the exit code. |
| README Env bullet (already documents "no env") | `README.md:620-621`, `README_ES.md:652-654` | "Opencode receives no env." / "Opencode no recibe env." — roadmap item 2's dashboard fact is **already present** from the archived docs change; treat as verify-only, do not re-write (AGENTS.md §4). |
| README manual alternative (already documents `environment` literal) | `README.md:684-685`, `README_ES.md:717-719` | "…use the launcher environment or an explicit `environment` literal (plaintext on disk)" — already documented; **no new paragraph needed**; the residual README delta is the new CLI-warning behavior note. |
| `mcp add` argparse help | `src/sofer/cli.py:1494-1516` | `--agent/--scope/--cwd/--dry-run`; description covers idempotency/backup/atomic write but not env behavior. AGENTS.md §7: help= must reflect behavior changes in the same change. |
| Tests (env forwarding) | `tests/test_mcp_registration.py:432-481` (`TestEnvForwarding`) | Covers gemini `$KEY` refs and codex `env_vars` names-only; **no opencode-warning test exists**. Dry-run coverage at `test_add_dry_run_no_mutation` (L313-327), `test_add_all_dry_run_no_files` (L342-358); delegation at `TestDelegation` (L484+). |
| Affected specs | `openspec/specs/mcp-registration/spec.md` (MCP-REG-01), `openspec/specs/cli/spec.md` (CLI-R09, L321+), `openspec/specs/mcp-server/spec.md` (L530-531, L562) | mcp-registration MCP-REG-01 needs new scenarios; CLI-R09 help scenarios may need a delta if the description changes. mcp-server spec is **already consistent** — its per-agent guidance SHALL NOT claim env forwarding for opencode (L530, L562) — no change needed there, only a consistency check. |
| Baseline | `tmp/roadmap.md` | dev clean, CI green, 1501 collected / 1495 passed / 6 skipped; ruff + mypy clean. |

## Scope

### In Scope

- `src/sofer/mcp_registration.py`:
  - `build_entry` / agent-id logic — keep opencode entry shape byte-identical (`{type, command, cwd}`). Add a small single-source helper that reports which known env names would be dropped for a given agent (opencode → present keys from `_ENV_KEYS`; codex/gemini → none), so `cli.py` does not re-hardcode env knowledge. Exact symbol shape is a design-phase decision; it must reuse `_ENV_KEYS` and never receive secret values.
  - Docstrings: update `build_entry`'s env-forwarding contract to state the opencode warning contract (selection-time warning, entry still env-less).
- `src/sofer/cli.py` (`mcp add` flow, incl. `--dry-run`):
  - Emit the warning per-agent when `agent == "opencode" and env` (i.e. also for the opencode member of `--agent all`), **before** the delegation probe and the dry-run branch so it appears in both real and `--dry-run` output; stderr, `!` style; lists **names only** (the present keys from `_ENV_KEYS`), never values; exit code unchanged (informational).
  - `mcp_add` argparse `description=` / `--agent` help: mention env behavior (names-only for codex/gemini; opencode entry carries no env and prints a warning when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set) — AGENTS.md §7.
  - `_cmd_mcp_add` docstring: document the warning step in the orchestration flow (AGENTS.md §2).
- `README.md` + `README_ES.md` (same commit, AGENTS.md §13):
  - Verify the existing "opencode receives no env" bullet and the manual-alternative paragraph remain accurate; add one sentence to the `mcp add` section noting the CLI warning when env vars are set and `--agent opencode` is chosen. Prose translated to Spanish in `README_ES.md`; entry tables/technical content stay English in both.
- Tests:
  - `tests/test_mcp_registration.py`: new opencode-warning tests (env present → warning text on stderr; dry-run → warning present + no file/`.bak`; no env → no warning; codex/gemini with env → no warning; `--agent all` with env → exactly one warning for the opencode member; exit codes unchanged; secret **values** absent from captured output and from written file; opencode entry still `{type,command,cwd}`).
  - `tests/test_cli.py` (CLI-R09 help tests, L1161+): extend/additively assert the updated help text if the description changes.
- Spec delta (authored during the spec phase): **ADD** scenarios to MCP-REG-01 (opencode env warning, dry-run warning, names-only, no exit-code change) and, if the help description changes, an additive CLI-R09 scenario. mcp-server spec: **no delta** (already consistent — verified L530-531/L562).

### Out of Scope

- **`pi` agent (#142, Fase 6)** — no adapter, no `--agent pi`, no `all` → 4 agents. Same files, later phase; must stay untouched here.
- **Opencode registration-format redesign** — the entry stays `{type, command, cwd}`; no `environment` object is generated (it would require persisting secret values → violates constraint #3; or duplicating host-shell expansion semantics that are opencode's own concern).
- **Persisting secret values anywhere** — never write `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` values into any generated config (constraint #3, parity with codex/gemini).
- **`mcp_server.py` / MCP tool changes** — the server already reports env state correctly (`approval_configured`, `phrase_source`); nothing to fix server-side. The archived #144/#145 work already made the unconfigured state actionable.
- **Codex/gemini native-delegation env gap** (observed: `delegate_add(agent, cwd, env_keys)` ignores `env_keys` — signature parity — so a native `codex mcp add`/`gemini mcp add` registers `sofer-mcp` without forwarding env names). This is **adjacent but distinct** from #147 and out of the roadmap's Fase-4 scope; do not change delegation behavior in this PR. Track as a follow-up issue candidate (see Risks).
- Native delegation behavior, `README` re-documentation of already-covered content (AGENTS.md §4 — no duplicated paragraphs), config keys, `pyproject.toml`, workflow modules.

## Approach

1. **Single source for "which env keys are dropped"** — in `mcp_registration.py`, a small pure helper (design phase picks exact name/signature, e.g. `dropped_env_keys(agent, env) -> list[str]`) returning the present keys from `_ENV_KEYS` for opencode and `[]` for codex/gemini; `build_entry` keeps returning the minimal opencode entry. This keeps env knowledge in the module that owns it (AGENTS.md §4) and gives the unit test a direct, value-free surface.
2. **CLI warning** — in `_cmd_mcp_add`, after `env = mcp_registration.collect_env()` (L657), inside the per-agent loop: `if agent == "opencode" and dropped := helper(opencode, env): print warning to stderr`. Placement before `probe_native` and before the `if dry_run:` branch (L699) guarantees the warning appears in real runs, in `--dry-run`, and for `--agent all`. Message names the dropped variables (NAMES only), states the entry carries no env, and points at the README section for the launcher-env / `environment`-literal alternative. Exit code untouched.
3. **Docs** — one additive sentence in the `mcp add` README section (English in `README.md`, Spanish prose in `README_ES.md`) describing the warning; verify the already-existing bullets stay accurate; no duplication.
4. **Help text** — extend `mcp add` description with the env-forwarding summary (names-only codex/gemini; opencode no-env + warning) and sync the CLI-R09 help tests additively.
5. **Tests** — cover: warning presence/absence matrix (opencode±env, codex/gemini+env, all+env, dry-run), exit codes, values-never-in-output/file, entry-shape invariant, help text. Every new spec scenario maps to a test (AGENTS.md §6: `uv run pytest tests/ -q` is the suite; config `strict_tdd: false`).
6. **Spec delta** — ADD-only for MCP-REG-01 (and optional CLI-R09 additive); mcp-server spec verified consistent, no modification.

## Alternatives

| Alternative | Rejected because |
| ------------- | ------------------ |
| Silently keep current behavior (document only, no CLI warning) | The bug is the **silence**: issue #147's pain is that users discover the dropped env only at publish time (fail-closed, `tmp/TRACE.md`). A selection-time warning is the cheapest faithful fix and the roadmap's explicit item 1. |
| Write an `environment` object into the opencode entry (attempt to forward env) | Requires persisting **secret VALUES** into plaintext `opencode.json` (opencode has no `$KEY`-reference semantics like gemini's runtime expansion) → violates constraint #3 and the codex/gemini names-only parity. Also a format redesign → out of scope. |
| Error out / exit 1 when `--agent opencode` + env present | Registration is still valid (command + cwd work; publish works via CLI with the launcher env). Hard-failing breaks `--agent all` for users with env set, and the roadmap asks for a warning, not a gate. |
| Warn only in non-dry-run | Dry-run is the preview surface — the roadmap explicitly requires the warning in `--dry-run` output; skipping it there would let users preview a silent drop. |
| Keep the warning inline in `cli.py` (hardcoded env names in cli) | Duplicates `_ENV_KEYS` knowledge in a second module (AGENTS.md §4) and the names would drift; a helper in `mcp_registration.py` reuses the single source (AGENTS.md §1 — no hardcoded values). |

## Proposal question round (assumptions taken; no user interview per confirmed handoff)

The handoff states the fix scope is confirmed, so no blocking questions. Assumptions recorded for user review at the review gate:

1. **`--agent all` must warn too** — `all` includes the opencode member (L630-631), so the warning fires once for it when env is present. If the user prefers suppressing the warning under `all`, that is a one-line deviation — flag at review.
2. **Warning is informational, never a gate** — exit code stays 0; stdout/stderr unaffected. Assumed from roadmap item 1 ("warning", not "error").
3. **README residual delta is minimal** — the manual alternative and the "recibe no env" dashboard fact are **already documented** (verified L620-621/L684-685 EN, L652-654/L717-719 ES); this change only adds the *warning-behavior* sentence and verifies mirrors. No re-documentation.
4. **Codex/gemini delegation env gap is out of scope** — `delegate_add` ignores `env_keys` (signature parity); a follow-up issue/phase should assess whether native registration must forward env names. Not changed here to keep the PR focused on #147.

## Risks

| Risk | Likelihood | Mitigation |
| ------ | ------------ | ------------ |
| Secret value leak into the warning message or capture | Low | Warning prints NAMES only (from `_ENV_KEYS`), never values; unit test asserts the configured values are absent from captured stderr and the written file. |
| Exit-code change breaks scripts / `--agent all` | Low | Warning is informational; code path returns `overall` unchanged; tests assert rc stays 0/1 as before. |
| Dry-run path misses the warning (bug in placement) | Low | Warning emitted before the dry-run branch (L699) and covered by a dedicated dry-run test (no file/`.bak`, warning present). |
| README/README_ES drift or duplication with existing paragraphs | Low | One additive sentence per file, same commit (AGENTS.md §13); existing bullets verified as accurate rather than rewritten (AGENTS.md §4). |
| Scope drift into #142 (`pi`) or a format redesign during apply | Med | Proposal names both OUT with the same-file rationale; review gate checks no `pi`/adapter/`environment` symbols appear; spec delta is ADD-only. |
| Adjacent delegation gap misattributed to this change (or silently "fixed" during apply) | Med | Documented OUT in Scope + item 4 of the question round; delegation methods untouched; filed as follow-up candidate for the parent. |
| Help-text change breaks CLI-R09 tests | Low | Updates are additive; sync `tests/test_cli.py` help assertions in the same commit. |

## Rollback

- The change is additive (warning print, help-text sentence, one README sentence per file, new spec scenarios, new tests). Reverting the PR cleanly restores prior behavior; no migration, no data, no config-format compatibility impact.
- `build_entry`'s opencode return value is unchanged, so removing the helper (should it be added to `mcp_registration.py`) leaves entry generation byte-identical — no `.bak`/format coexistence issue.
- README and README_ES must be reverted together (AGENTS.md §13); warnings/help text revert with `cli.py`.

## Success Criteria

**Issue #147 acceptance contract (roadmap items 1-3):**

- [ ] `sofer mcp add --agent opencode` (and `--agent all`'s opencode member) with `HF_TOKEN` and/or `SOFER_MCP_APPROVAL_PHRASE` set prints an explicit warning listing those **names**, states the entry carries no env, and points at the README alternative — exit code and stdout registration output unchanged.
- [ ] The warning appears in `--dry-run` output; `--dry-run` still performs no write and creates no `.bak`.
- [ ] No warning when no env vars are set, and no warning for `--agent codex`/`gemini` with env set (both still forward names-only as today).
- [ ] Generated `opencode.json` entry remains exactly `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}`; **no** env names or values ever written for opencode; codex `env_vars` and gemini `env` still persist names only (values never on disk).
- [ ] `README.md` + `README_ES.md` updated in the same commit: warning-behavior sentence in the `mcp add` section; existing manual-alternative and no-env bullets verified accurate; technical content English, prose mirrored.
- [ ] `mcp add` help text reflects the env behavior (AGENTS.md §7); CLI-R09 tests updated additively.
- [ ] New MCP-REG-01 scenarios (+ additive CLI-R09 scenario if help changed) each backed by a test; full suite `uv run pytest tests/ -q` green (baseline 1501/1495/6), `uv run ruff check src/ tests/` and `uv run mypy src/` clean.
- [ ] No overlap with #142: no `pi` symbol, no adapter change, no `all`→4 expansion anywhere in this PR.
