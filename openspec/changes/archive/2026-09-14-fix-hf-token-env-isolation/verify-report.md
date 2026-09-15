```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9cae1a183b70074201df1a3b3a769df7fc3b6405c305d175d0be809518ab9b0e
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 5/5
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:7328daa391457fe94445dd2ac064a8f4dfef00874e4f53db9dc5269c2da4b98a
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:5b3e3905d4d9e175f9dd86715f6d5a9643abecae88f3e6e7b2349e013c8e9006
```

# Verify Report: fix-hf-token-env-isolation (issue #176)

**Change** `2026-09-14-fix-hf-token-env-isolation` · branch `fix/176-hf-token-test-isolation` @ `ff319ac` (+ uncommitted working tree) · store **openspec** + Engram mirror.
**Verdict: PASS** — 1 requirement (PB-13), 5/5 scenarios traced, 11/11 tasks complete, 0 unchecked, all gates green, no blockers, no critical findings.

**What the hashes were computed from.** `evidence_revision` = `sha256` of `git diff` (the full tracked candidate diff, 218 lines / 113 insertions + 28 deletions across the 4 files), recomputed after the red-provenance restore and identical to the pre-run value. `test_output_hash` = `sha256` of the captured stdout+stderr of `uv run pytest tests/ -q`. `build_output_hash` = `sha256` of the captured output of `uv run mypy src/`.

## Requirement / scenario coverage — PB-13, 1 ADDED requirement, 5 scenarios

Confirmed myself from the delta: `## ADDED Requirements` contains exactly one requirement, *"Side-effect-free HF token resolution and cross-test env hermeticity (PB-13)"*, with exactly five `#### Scenario:` blocks (S1–S5). No `## MODIFIED Requirements` block.

| # | Scenario | Evidence | Result |
|---|---|---|---|
| S1 | Resolution leaves the process environment unchanged | new guard `TestHfTokenFallback::test_dotenv_call_leaves_environ_unchanged` PASSED; **proven RED** against pre-change source (§ below); independent out-of-repo probe: token `from-dotenv`, `env_unchanged=True`, `added_keys=[]` **including the decoy key** | PASS |
| S2 | Environment presence beats `.env` even when the value is blank | new `test_dotenv_not_substituted_for_blank_present_env` PASSED (asserts the alias itself); independent probe: blank present `HF_TOKEN` + `HF_HUB_TOKEN=alias-token` → `alias-token`; whitespace-only present → `None` (truthiness would have returned `from-dotenv`) | PASS |
| S3 | `.env` supplies a value only when the environment omits the name | `:3181` `assert _get_hf_token() == "from-dotenv"` still holds verbatim at the unchanged line; independent probe → `from-dotenv`; file-fallback position pinned by `:3083`/`:3131` PASSED | PASS |
| S4 | `.env`-only disable flag still gates the implicit file fallback | new `test_dotenv_only_disable_flag_gates_file_fallback` PASSED; independent probe with a real token file: `.env` flag → `None`, control without the flag → `file-token` | PASS |
| S5 | No test leaks a token to a later test | both orders of `test_dotenv_loads_when_env_absent` + `TestMerge::test_codex_normalize_string_vs_array` → `2 passed` each; victim standalone passes; no ambient token in shell; `find . -name '*.bak'` empty; full suite green | PASS |

## Task completion

`tasks.md` scanned for `^\s*- \[ \]` — **0 unchecked lines**. All 11 apply checkboxes are `[x]`, matching `taskProgress 11/11` / `applyState: all_done`. Exact confirmation: no unchecked `- [ ]` implementation task line remains. The verify-gate, parent-lifecycle, and out-of-scope sections carry no checkboxes by design.

## Strict TDD

**Not active** — `openspec/config.yaml: strict_tdd: false` (and `testing.strict_tdd: false`). The `TDD Cycle Evidence` table is therefore not required and its absence is not a finding. The red→green pair required by design D4 / `tasks.md` was nevertheless verified independently (below).

### D4 / S1 red→green provenance — proven, not read

1. `sha256` of the post-change `src/sofer/mcp_server.py` recorded (`2f5cdbd3…`), file copied to a scratch path outside the repo.
2. Pre-change file materialised from `git show HEAD:src/sofer/mcp_server.py` into `src/sofer/mcp_server.py` (HEAD = pre-change; the fix is uncommitted), `sha256` `9472bb0b…`.
3. `uv run pytest tests/test_mcp_server.py -k leaves_environ_unchanged -q` → **exit 1, 1 failed**, with `Left contains 2 more items: {'HF_HUB_DISABLE_IMPLICIT_TOKEN': 'true', 'HF_TOKEN': 'from-dotenv'}`.
4. Post-change file restored from the scratch copy; `sha256` `2f5cdbd3136326552632849f5348cd1682f2df0188a474846ed51af24872ad8e` — **byte-identical** to step 1; `git diff --stat` back to 113/28 on 4 files; re-hashed candidate diff identical to the pre-run value.
5. Against the restored tree the guard passes (`1 passed`).

**Non-tautological**, proven in two independent ways: (a) the guard snapshots `dict(os.environ)` *after* setup and *before* the call, and asserts both the resolved value and full env equality — an implementation that merely stopped returning `.env` values fails the first assertion; (b) the second `.env` key (`HF_HUB_DISABLE_IMPLICIT_TOKEN`, token-irrelevant) must **also** stay out of the environment, and it was injected pre-change, so an ambient `HF_TOKEN` cannot make the assertion vacuous. The out-of-repo probe reproduces the same property with an independent decoy key (`DECOY_KEY`) and shows `added_keys=[]`.

### Assertion quality audit of changed/created tests

The 4 new tests assert concrete observable outcomes: resolved token strings (`== "alias-token"`, `== "from-dotenv"`), full `dict(os.environ) == before`, `is None`, and `== {"HF_TOKEN": "from-dotenv"}` / `== {}`. No tautologies, no ghost loops, no type-only assertions, no smoke-only tests, no CSS/implementation-detail assertions. The S2 test asserts the alias token itself, not merely "not `from-dotenv`", as the delta required. `tests/test_mcp_server.py` diff is **66 insertions / 0 deletions** — no test renamed, reordered, skipped or xfailed.

## The three rigour checks

### 1. S1 guard provenance
See §Strict TDD above — RED (exit 1, both keys injected) against the pre-change file, GREEN after, tree restored byte-identically. Not tautological (two independent non-vacuity proofs above).

### 2. D1 presence semantics
Independently exercised out-of-repo with an exported blank value:
- `HF_TOKEN=""` (present, blank) + `HF_HUB_TOKEN=alias-token` + `.env HF_TOKEN=from-dotenv` → `alias-token` — the `.env` value is **not** substituted.
- `HF_TOKEN="   "` (present, whitespace-only), no alias → `None` — truthiness-based code would have returned `from-dotenv`.

Implemented expression is literally presence-based: `_merged_env` is `if name in os.environ: return os.environ[name]` / `return dotenv.get(name, "")` (`src/sofer/mcp_server.py:771-776`). There is **no** `or`-chain: `grep -n 'os.environ.get(name)'` matches only the explanatory comment on line 773. The single `os.environ[...]` hit in the file is the read at `:774`.

### 3. D2's two halves
**(a) The gate keeps `.env` visibility.** Independent probe: `.env` holding only `HF_HUB_DISABLE_IMPLICIT_TOKEN=true`, no token in env or `.env`, a valid token file configured → `_get_hf_token() is None`; the control with the flag removed returns `file-token`, proving the file fallback is live and `None` is caused by the flag. Had the helper been narrowed to `os.environ` only, production would have silently re-enabled the implicit file fallback — it is not narrowed. Pinned by the new S4 test and by `_is_truthy_env(name, dotenv)` taking the merged mapping as a **required** argument (only call site passes the merged view).

**(b) The accepted narrowing is documented, not presented as a regression.** Independent probe confirms `.env`-only keys (`HF_TOKEN_PATH`, `HF_HOME`, arbitrary keys) are **absent** from `os.environ` after a call (`HF_TOKEN_PATH_in_os_environ=False`, `HF_HOME_in_os_environ=False`), while `sofer`'s own merged view still reads them (`merged_keys=['HF_HOME','HF_TOKEN','HF_TOKEN_PATH']`). `design.md` D2 rows 2–4 and `apply-progress.md` §8 record this as an **accepted, documented narrowing**; the delta §"Stated consequences" (b) states it is the **correct contract, not a regression** (a spawned server inherits the host's real environment, not our in-process read of the cwd `.env`). **No test, README contract or spec row depends on it**: the only `.env` fixtures in the suite carry `HF_TOKEN=` alone, the file-fallback cases set `hf_constants.HF_TOKEN_PATH` directly (never via `.env`), no `mcp-registration` requirement changes, and no `TestEnvForwarding` case moves — all confirmed by the green suite. A user-facing note is a follow-up, correctly out of scope.

## Gates

| Gate | Command | Exit | Result |
|---|---|---|---|
| Full suite | `uv run pytest tests/ -q` | 0 | **1781 passed, 6 skipped, 0 failed** |
| Targeted | `uv run pytest tests/test_mcp_server.py -q` | 0 | 247 passed, 3 skipped |
| `TestHfTokenFallback` | `uv run pytest tests/test_mcp_server.py -k TestHfTokenFallback -v` | 0 | **14 passed** (incl. the 4 new); `:3117` `assert _get_hf_token() is None` and `:3181` `assert _get_hf_token() == "from-dotenv"` intact at unchanged lines |
| Repro order 1 | `uv run pytest "tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array" "tests/test_mcp_server.py::TestHfTokenFallback::test_dotenv_loads_when_env_absent" -q` | 0 | 2 passed |
| Repro order 2 | `uv run pytest "tests/test_mcp_server.py::TestHfTokenFallback::test_dotenv_loads_when_env_absent" "tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array" -q` | 0 | 2 passed |
| Coverage data | `uv run coverage run -m pytest -q` | 0 | 1781 passed, 6 skipped |
| Coverage report | `uv run coverage report -m` | 0 | **TOTAL 93%** (≥ 90 floor); `mcp_server.py` 90% (informational — no per-file floor); COV-01: `mcp_registration.py` 99%, `profile.py` 96%, `verification.py` 100% |
| Core coverage | `bash scripts/check_core_coverage.sh` | 0 | `cli.py`, `scanner.py`, `prepare.py`, `publish.py` each **100%**, empty `Missing` column |
| Types | `uv run mypy src/` | 0 | Success: no issues found in 32 source files |
| Lint | `uv run ruff check src/ tests/` | 0 | All checks passed! |
| Format | `uv run ruff format --check src/ tests/` | 0 | 67 files already formatted |
| Diff shape | `git diff --stat` | 0 | 4 files, 113 insertions / 28 deletions (141 tracked lines) |

**Baseline failure: CLEARED, not reproduced.** Apply re-derived the true pre-change baseline as `1 failed, 1776 passed, 6 skipped` (AGENTS.md's `1766 / 6` is stale — three new tests exist) and identified the single failure as `tests/test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present` asserting `TOTAL measured 89.9% locally (< 90)`. I confirmed the mechanism from the test source: it `skipif`s when `.coverage` is absent and otherwise reads the **gitignored** root `.coverage` data file, asserting TOTAL ≥ 90 at line 88 — a read-only pin on a coverage artifact, orthogonal to token resolution and absent from the diff (the diff touches none of its inputs). Apply's task-5.1-mandated `coverage run` refreshed that stale artifact, so my `uv run pytest tests/ -q` is fully green with **0 failed**; the failure is cleared and cannot be attributed to this diff.

**Source greps (D7 checklist).** No `os.environ[...] =` write anywhere in the diff's module or in `src/`: the write-pattern grep exits 1 (no match). No `os.environ.setdefault` / `.update` / `.pop` / `os.putenv`. `load_dotenv(` survives only as prose inside D1's own docstring (`:750`, `:785`) — **no call remains**. `grep -rn '_load_dotenv_if_available' src tests` exits 1 — the old helper is gone. `grep -c load_dotenv README.md README_ES.md` → `0` / `0`; both READMEs carry the new `dotenv_values` wording mirrored (README.md:659 / README_ES.md:693; ES prose Spanish, technical tokens English), and the diff shows no other README line or heading changed (rule 13 satisfied).

## Scope / review workload / PR boundary

- Files changed: exactly `src/sofer/mcp_server.py`, `tests/test_mcp_server.py`, `README.md`, `README_ES.md` (+ the untracked change dir). No temp or orphan file inside the repo; no `.env` created at the root (constraint honoured).
- Untouched, verified with `git diff --quiet`: `src/sofer/mcp_registration.py`, `.env.template`, `pyproject.toml`, both workflows. The `tasks.md`/`proposal.md`/`design.md`/delta/canonical specs/archive/sibling change were not edited in this phase.
- The five #207 victim lines (`tests/test_mcp_server.py:3083`, `:3098`, `:3117`, `:3131`, `:3148`) are intact at their line numbers (the 4 new tests were appended after `:3181`, so nothing shifted) and remain untouched.
- `Review Workload Forecast` respected: forecast `~90` lines / single PR / no chaining / budget risk Low; actual **141 tracked lines < 400**. No `size:exception` was used or needed, and no scope creep beyond the assigned tasks — the diff is confined to the three work units (RED guard, GREEN fix, docs).
- No pragma added to any COV-06 module; the one `# pragma: no cover` in `mcp_server.py:75` is pre-existing and outside every diff hunk.

## Documented, accepted anomaly (NOT a finding against this change)

`apply-progress.md` discloses it twice — an escalation warning at **line 7** and the full §12 *"Runtime ledger escalation"* (line 228+) — that a **probe payload** was passed to `sdd-attempt settle`, which the engine accepted and committed, leaving a fabricated runtime-ledger row for attempt ordinal 1: `evidence_revision: sha256:000…0`, `diagnosis: "probe"`, `cleanup_evidence: "probe"`, `process_evidence: "probe"`, `changed_lines: 384` (against a real 141 tracked lines). I confirmed this independently: `gentle-ai sdd-attempt status` prints exactly that fabricated row for ordinal 1, and two later honest settles short-circuited on the terminal objective without amending it.

**Impact: none on this change or on any evidence row.** A grep for the null `sha256:000…0` value across the whole change directory matches **only** `apply-progress.md:235`, where it is *quoted as the ledger's content* inside §12 — no requirement, scenario, task, gate, design decision or evidence row anywhere in any artifact carries it. The fabricated values appear nowhere else. The verification attempt for this phase was acquired on the same attempt token and **settled honestly**: `sdd-attempt status` now records ordinal 2 (`hf-token-isolation-verification`) as `outcome: passed`, `changed_lines: 116`, `evidence_revision: sha256:9cae1a18…`, with the objective `complete`. The fabricated row is therefore isolated to ordinal 1 and did not contaminate the verification record. The maintainer has explicitly chosen to leave the disclosure documented rather than authorise the destructive `reset` (which the provider documents as discarding the scope instead of amending it); that decision is respected and no reset was attempted. Note as part of the same anomaly: the reset recipe quoted in §12 cites a `--expected-revision` (`sha256:17f7bdec…`) and an apply token (`sha256:972edf…`) that no longer match the current `status` revision (`sha256:8f12dce6…`), so if a reset is ever wanted, `sdd-attempt status` must be re-run first. (Post-settlement, the objective is terminal, so only `reset` — an explicit maintainer scope decision — could amend ordinal 1; no separate work unit remains.) Reported here as a **documented, accepted anomaly** with its impact stated — never as a finding against the change and never a reason to withhold the verdict.

## Pre-existing static findings (out of scope, not fixed)

A repo-wide static scanner reports diagnostics inside `src/sofer/mcp_server.py`: `import tomli as _tomli` (L687), `with open(path, "rb")` (L690), and the `_SERVER_ROOT` / `_APPROVAL_PHRASE` / `_PHRASE_SOURCE` / `_SERVER_PROCESS_ID` / `_SERVER_STARTED_AT` / `_SERVER_VERSION` redefinitions. They appeared during the temporary pre-change substitution and after restore, are **byte-identical on unmodified `HEAD`**, and no diff hunk intersects them (hunks touch only lines 66, 747-782, 804-821). They are the documented latent issues of AGENTS.md rule 12 (`tomli` backport) and the intentional PB-09 single-writer pattern. The authoritative gates — `uv run mypy src/` and `uv run ruff check src/ tests/` — are both clean. Left untouched by instruction.

## Blockers

**None.** Archive readiness: `openspec/changes/2026-09-14-fix-hf-token-env-isolation/verify-report.md` now resolves, 0 unchecked tasks, PASS verdict — archive may proceed with the canonical PB-13 sync. The §12 ledger anomaly is documented and accepted, not an archive blocker. Issue **#207** remains separately open and correctly out of scope.
