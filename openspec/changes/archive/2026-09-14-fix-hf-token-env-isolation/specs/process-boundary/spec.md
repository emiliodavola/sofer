# Delta for process-boundary

> **Change** `2026-09-14-fix-hf-token-env-isolation` (issue #176) · branch `fix/176-hf-token-test-isolation` — verified: `.git/HEAD` → `ref: refs/heads/fix/176-hf-token-test-isolation` · store **hybrid** (this file + Engram mirror under topic key `sdd/2026-09-14-fix-hf-token-env-isolation/spec`).
>
> **Capability choice — `process-boundary`, justified.** PB-06 "Deterministic and offline" (`openspec/specs/process-boundary/spec.md:184-199`) already owns suite determinism and credential-independence; the defect is a global write to the *process environment* that leaks across tests, which is exactly a process-boundary property. No canonical spec owns token resolution: `mcp-server` pins only `HF_TOKEN` presence for `sofer_publish_confirm` (`mcp-server/spec.md:135-160`, untouched) and `mcp-registration` pins env-NAME forwarding (`mcp-registration/spec.md:16-19`, untouched).
>
> **Additive, not destructive.** PB-01..PB-12 keep their text byte-for-byte — PB-06's clause and its "No credentials required" scenario are *enforced*, not restated — so the clause enters as new requirement **PB-13**, the next free ID in this capability (PB-12 is the current maximum). `## MODIFIED Requirements` is deliberately absent: no canonical block changes, so an archive-time replacement would be a lossy no-op. PB-09 covers *server-state* leakage (`_SERVER_ROOT`/`_APPROVAL_PHRASE`), explicitly not the environment; PB-06 says nothing about cross-test env hermeticity, which is the honest new property.
>
> **Domain hygiene:** the canonical `openspec/specs/process-boundary/spec.md` was read before writing (delta, not full spec); no other non-archived change carries `specs/process-boundary/`; this change has no legacy flat `openspec/changes/<change>/spec.md`.

## ADDED Requirements

### Requirement: Side-effect-free HF token resolution and cross-test env hermeticity (PB-13)

> Added by change `2026-09-14-fix-hf-token-env-isolation` (issue #176).

`_get_hf_token()` and its `.env` helper SHALL resolve a token **without writing to `os.environ`**: `.env` SHALL be read with `dotenv_values` and consulted as a value fallback, so no call path of shipped `src/sofer/mcp_server.py` SHALL assign into the process environment (today `load_dotenv(override=False)` at `:762-763` does, unrecorded). Precedence SHALL be decided by **key presence in `os.environ`, never by value truthiness** — a name present in the environment wins over the `.env` entry for that name even when its value is whitespace-only and `_clean_token` maps it to `None`, mirroring `load_dotenv(override=False)`, which skips a merely-present key; the `.env` value SHALL be consulted only when the name is absent from the environment. The resolution order SHALL stay `HF_TOKEN` → `HF_HUB_TOKEN` → `HUGGING_FACE_HUB_TOKEN` → `huggingface_hub.get_token()` (file/OIDC/Colab), and the `.env` view SHALL remain visible to the implicit-token gate `HF_HUB_DISABLE_IMPLICIT_TOKEN` (read at `src/sofer/mcp_server.py:806` via `_is_truthy_env`), which SHALL keep skipping the file/Colab fallback exactly as today. Consequently the suite SHALL be environment-hermetic: a test SHALL NOT leave the process environment mutated for later tests, and token resolution SHALL NOT mutate it at all.

#### Scenario: Resolution leaves the process environment unchanged (the gate)

- GIVEN a temp cwd holding a `.env` with `HF_TOKEN=from-dotenv` and a second key, and `HF_TOKEN`/`HF_HUB_TOKEN`/`HUGGING_FACE_HUB_TOKEN` absent from the environment, with an `os.environ` snapshot taken before the call
- WHEN `_get_hf_token()` is called
- THEN it SHALL return `"from-dotenv"`
- AND `os.environ` SHALL equal that snapshot — no injected key, not even from the second `.env` line

#### Scenario: Environment presence beats `.env` even when the value is blank

- GIVEN `.env` holding `HF_TOKEN=from-dotenv`, a *present but whitespace-only* `HF_TOKEN` in the environment, and `HF_HUB_TOKEN=alias-token`
- WHEN `_get_hf_token()` is called
- THEN it SHALL return `"alias-token"` — the `.env` value SHALL NOT be substituted for the blank present key (key-presence semantics, not value-truthiness)

#### Scenario: `.env` supplies a value only when the environment omits the name

- GIVEN `HF_TOKEN` absent from the environment and `.env` holding `HF_TOKEN=from-dotenv`
- WHEN `_get_hf_token()` is called
- THEN it SHALL return `"from-dotenv"` (`tests/test_mcp_server.py:3181` keeps holding), and the file fallback SHALL keep its position when neither the environment nor `.env` supplies a token

#### Scenario: `.env`-only disable flag still gates the implicit file fallback

- GIVEN `HF_HUB_DISABLE_IMPLICIT_TOKEN=true` present **only** in `.env`, no token in the environment or `.env`, and a valid token file configured
- WHEN `_get_hf_token()` is called
- THEN it SHALL return `None` rather than the file token — the `.env` view remains visible to the flag, so this change alters no production resolution outcome

#### Scenario: No test leaks a token to a later test (issue #176)

- GIVEN the suite running in one process with a cwd `.env` present and no ambient `HF_TOKEN`
- WHEN the resolving test at `tests/test_mcp_server.py:3168` runs before `tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array` (`:171`)
- THEN the victim SHALL observe no `HF_TOKEN` (`collect_env()` at `mcp_registration.py:450-461` reports none), create no `.bak`, and pass — the amplifier at `tests/test_mcp_registration.py:560-577` SHALL have nothing to restore

---

## Rule-6 resolution: one row per scenario

| # | Scenario | Evidence | Strength |
|---|---|---|---|
| S1 | Env unchanged after a `.env`-present call | **new test** in `tests/test_mcp_server.py::TestHfTokenFallback` (snapshot `os.environ`, call, assert equality + `.env` return) | Strong. Must be **RED before the fix** (today `load_dotenv` injects `HF_TOKEN`) and **not tautological**: it asserts both the resolved value *and* full env equality, so an implementation that merely stopped returning `.env` values fails it. |
| S2 | Blank env value beats `.env` | **new test** (`.env` + `HF_TOKEN="   "` + alias) | Strong, but the strict presence-vs-truthiness distinction has **no existing evidence**: `tests/test_mcp_server.py:3100` (`:3112`, `:3117`) exercises blank env values *without* writing a `.env`, so it cannot distinguish the two semantics on its own. The new test is what pins it — and it must assert `"alias-token"`, not merely "not `from-dotenv`". |
| S3 | `.env` used only when the name is absent; file fallback position | existing `tests/test_mcp_server.py:3168` (`:3181` asserts `"from-dotenv"`), `:3069` (env wins over `.env`), `:3083`/`:3131` (file fallback) | Strong for the happy paths. **Weaker, flagged:** when a repository-root `.env` exists, `:3083`/`:3117`/`:3131`/`:3148` fail for an unrelated reason (#207) — see below; this change neither fixes nor worsens them. |
| S4 | `.env`-only disable flag gates the file fallback | **new test** (flag only in `.env`); existing `tests/test_mcp_server.py:3119` covers the flag via `monkeypatch.setenv` only | **Weakest link, flagged honestly.** No existing test puts the flag in `.env`; behaviour preservation rests on the new test. If `design` decides the flag reads `os.environ` only, this scenario must be **corrected before `apply`**, not silently dropped — it is a production-visible change. |
| S5 | Leaker poisons no later test | **command evidence** — `uv run pytest tests/ -q` green with (a) no ambient `HF_TOKEN` and (b) an explicit in-process ordering check; plus S1's guard as the pytest-assertable proxy. Victim standalone: `uv run pytest "tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array" -q` | **Command-shaped, stated plainly.** A test that asserts the victim's outcome *after* the leaker in one process would have to re-order or fuse two modules' tests, which this change forbids; S1 is the pytest-assertable statement of the same property. No ordering plugin, no rename, no skip. |

**Coverage gates — corrected premise.** `src/sofer/mcp_server.py` is in **neither** the COV-06 four (`cli`/`scanner`/`prepare`/`publish`, `coverage` spec, AGENTS.md rule 14) **nor** the COV-01 floor set (`profile`/`mcp_registration`/`verification`). It therefore has **no per-file coverage floor**: only the config-owned TOTAL gate applies (`fail_under = 90`, `openspec/config.yaml`; `ci` CI-01 / `coverage` COV-02). This delta promises **no 100% row** and no new gate for that file — neither widening nor weakening COV-01/COV-06. AGENTS.md rule 6 is satisfied by the mapping above; rule 3 (no hardcoded values) is untouched (no new literal enters shipped code).

## Stated consequences, cross-references, and non-goals

- **(a) `HF_HUB_DISABLE_IMPLICIT_TOKEN` keeps seeing `.env`** — pinned by S4 above, because today's `load_dotenv` injection made that true; dropping it would silently re-enable the implicit file fallback in a shipped path.
- **(b) `mcp add` no longer reports a `.env`-only token.** `mcp_registration.collect_env()` (`:450-461`) reads `os.environ` only, so a token living *solely* in `.env` stops appearing as a forwarded env NAME. This is the **correct contract, not a regression**: the server that `mcp add` configures is spawned by the agent host and inherits the *real* host environment plus the host's own `.env` handling — it never saw our in-process read. No `mcp-registration` requirement changes and no `TestEnvForwarding` case moves.
- **Correction to `proposal.md` (informational; the file is not edited).** Its success-criteria bullet 3 reads as though the victim passes under an exported `HF_TOKEN=hf_pre_set_in_shell`. `collect_env()` would still surface that ambient value, so the true pinned property is *"the leaker no longer poisons the process"* (S1/S5) — not *"the victim tolerates an ambient token"*. `proposal.md` is deliberately left untouched; this line is the correction of record.
- **#207 is out of scope.** The five `TestHfTokenFallback` cases that fail when a repository-root `.env` exists (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`) have a different cause — the suite depending on the developer's cwd `.env` — and stay failing: this change removes the global mutation but still consults the cwd `.env`. Issue **#207** owns them.
- **Untouched:** `mcp_registration.py` and the victim's assertion; no test renamed, reordered, skipped or xfailed; no `pytest-randomly` or other ordering plugin; `.env.template`; canonical `openspec/specs/**` and `openspec/changes/archive/**`; `openspec/changes/2026-09-14-chore-python-version-313/`; `tasks.md` and `proposal.md`; no commit, push or PR.
