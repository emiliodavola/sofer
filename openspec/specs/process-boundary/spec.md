# process-boundary Specification

## Purpose

Contracts for the test-only regression suite that pins sofer's MCP server and CLI through the same boundaries real agents use: in-process FastMCP `Client(server)`, real stdio transport, and executable CLI subprocesses. The suite SHALL make `tools/list`, schema serialization, process CWD, Windows console encoding, and CLI output regressions visible. No production behavior is specified here — the contracts these tests pin are already stated by the `mcp-server` (MSP-R01/R02) and `cli` (CLI-R01/R02) specs.

## Requirements

### Requirement: Registered MCP tools via public boundary (PB-01)

The suite SHALL exercise registered MCP tools through `fastmcp.Client(server)` (in-process) or the real stdio transport, and SHALL NOT rely on imported tool functions alone. Direct-call tests for `sofer_publish_confirm`, `sofer_init`, `sofer_validate`, `sofer_publish`, and `sofer_scan_apply` in `tests/test_mcp_server.py` — plus `test_offline_happy_path` and `test_auth_status_no_leak` in `tests/test_mcp_schema.py` — SHALL be routed through `Client(server)` via the shared `call_tool`/`_call` helper. The suite SHALL verify `tools/list`, JSON-Schema generation, envelopes, and a `tools/call` round-trip. Invalid Literal inputs (e.g. non-`local` `sofer_publish` targets) SHALL surface as `ToolError` at the client boundary through in-schema rejection, NOT as envelope `error_code` branches. New tests SHALL NOT add boundary-hiding direct calls for registered tools.
(Previously: conversion list named only `sofer_publish_confirm`/`sofer_init`/`sofer_validate`; invalid inputs were asserted via envelope `error_code` branches.)

#### Scenario: tools/list and call via in-process client

- GIVEN `build_server()` and an in-process `Client(server)`
- WHEN `tools/list` and one `tools/call` execute
- THEN 14 callables SHALL be listed and the call SHALL return the documented envelope

#### Scenario: Seven publish/scan_apply conversions through the client

- GIVEN the seven conversion sites in `tests/test_mcp_server.py` (`test_publish_dry_run_default_no_network`, `test_publish_hf_target_schema_rejected`, `test_garbage_target_dry_run_false_refused_no_api`, `test_aws_target_dry_run_false_refused`, `test_local_target_dry_run_false_copies_package`, and `test_xlsx_registered_validate_passes_and_idempotent` covering the two `sofer_scan_apply` sites)
- WHEN each runs via `_call(server, "sofer_publish"|"sofer_scan_apply", {...})` through `Client(server)`
- THEN valid-input conversions (dry-run plan `test_publish_dry_run_default_no_network`, local copy `test_local_target_dry_run_false_copies_package`, scan registration `test_xlsx_registered_validate_passes_and_idempotent`) SHALL return the documented envelope shape

#### Scenario: Stdio transport with clean framing

- GIVEN the server spawned as a subprocess
- WHEN `initialize → tools/list → tools/call` run
- THEN every response SHALL be valid JSON-RPC with no stray stdout bytes

#### Scenario: No remaining direct-call proofs

- GIVEN the converted test suite
- WHEN direct-call sites are enumerated across `tests/test_mcp_server.py` and `tests/test_mcp_schema.py`
- THEN zero registered tool SHALL be imported and called directly — every registered-tool call SHALL go through `Client(server)` or stdio

#### Scenario: Invalid Literal target rejected before the tool body

- GIVEN `sofer_publish` called via `Client(server)` with `target` outside the `"local"` Literal (`"hf"`, `"garbage"`, `"aws"`)
- WHEN the call executes
- THEN the request SHALL be rejected in-schema at input validation and SHALL surface as `ToolError` at the boundary — not an envelope `error_code` branch — and the tool body SHALL NOT run (`test_garbage_target_dry_run_false_refused_no_api`'s `calls == []` is preserved; the guard moved from the in-tool TARGET_INVALID gate to in-schema rejection)
- AND the deleted `test_garbage_target_dry_run_ok_no_network` direct-call-only test (`garbage` + `dry_run` → `ok:True`) SHALL NOT be re-added — its boundary-visible replacement is this in-schema rejection, which holds regardless of `dry_run`

#### Scenario: Stream-restore conversion exercises the tool body

- GIVEN `TestStreamRestore.test_stdout_stderr_restored_after_raise` routed through `Client(server)`
- WHEN `sofer_publish` raises INSIDE the tool body (missing TOML → `MCPToolError`), not via `target="hf"` which input validation rejects before the body
- THEN `pytest.raises(ToolError)` SHALL pass AND stdout/stderr SHALL be restored, exercising `_capture_output`'s stream swap

#### Scenario: auth_status routes via the boundary and exposes next

- GIVEN `test_auth_status_no_leak` (`tests/test_mcp_schema.py`) converted to `Client(server)`
- WHEN `sofer_auth_status` runs via the boundary
- THEN the call SHALL return the documented envelope INCLUDING `next` — the only tool whose `output_schema` declares it — making this the sole boundary-level `next` assertion

### Requirement: CLI user-visible output via executable subprocess (PB-02)

> Modified by `2026-09-13-fix-cli-console-encoding` (archived 2026-09-13).

Tests in `tests/test_cli.py` SHALL invoke `[sys.executable, "-m", "sofer.cli", ...]` (or the installed script) whenever the requirement concerns user-visible output; parser-level tests SHALL remain for dispatch semantics. Tests SHALL reuse the shared `tests/conftest.py::run_cli` subprocess helper (PB-09) and SHALL NOT re-implement it. The cp1252 boundary SHALL cover BOTH the help output of EVERY subcommand the CLI exposes — the nine top-level subcommands (`init`, `scan`, `validate`, `prepare`, `publish`, `codebook`, `profile`, `render`, `mcp`) plus the nested `mcp add` and `mcp remove` — AND the CLI's runtime console paths, which SHALL be exercised by at least one real command run, not only `--help`. These invocations SHALL run on the ubuntu CI matrix via `PYTHONIOENCODING=cp1252` with `encoding="cp1252", errors="strict"`, SHALL exit with their documented exit code, SHALL produce strict-decodable stdout (and strict-decodable stderr where the exercised path emits there), and SHALL NOT surface a `UnicodeEncodeError`. A cp1252 boundary assertion SHALL be shaped as exit code + cp1252-encodability + a stable ASCII substring of the surrounding message, and SHALL NOT assert a glyph, so the boundary test does not pre-commit how the CLI makes its text encodable. Windows-only behavior SHALL skip without privileges rather than fail.

(Previously: the cp1252 clause was a single `--help` invocation, which renders no subparser `description=` and therefore passed while `prepare --help` / `scan --help` crashed; runtime console paths were not covered at all.)

#### Scenario: Help via subprocess

- GIVEN the CLI subprocess helper
- WHEN `python -m sofer.cli --help` runs
- THEN exit code SHALL be 0 and stdout SHALL list every subcommand

#### Scenario: cp1252 help on the ubuntu matrix

- GIVEN `PYTHONIOENCODING=cp1252` in the subprocess env
- WHEN `--help` runs for every subcommand the CLI exposes — `--help` alone, plus `<cmd> --help` for `init`, `scan`, `validate`, `prepare`, `publish`, `codebook`, `profile`, `render`, `mcp`, plus `mcp add --help` and `mcp remove --help`
- THEN every invocation SHALL exit with code 0 and stdout SHALL strict-decode as cp1252
- AND no invocation SHALL surface a `UnicodeEncodeError`

#### Scenario: cp1252 runtime console output

- GIVEN `PYTHONIOENCODING=cp1252` in the subprocess env and a real command whose ordinary console output carries a character outside the cp1252 repertoire (a `validate` run that reports configuration errors, and a `scan --dry-run` run that previews a copy)
- WHEN each command runs through the executable subprocess boundary
- THEN each SHALL exit with its documented exit code (`1` for the configuration-error report, `0` for the dry run) and stdout SHALL strict-decode as cp1252
- AND the surrounding ASCII substring SHALL still be present (`Configuration errors`, `DRY RUN`)
- AND no `UnicodeEncodeError` traceback SHALL appear on stderr

#### Scenario: Dispatch exit codes

- GIVEN `python -m sofer.cli <unknown-command>`
- WHEN it runs
- THEN argparse SHALL exit 2

### Requirement: Recovery replay executes returned calls (PB-03)

Recovery tests SHALL key off the deterministic hint VALUES that the production gates pin for each refusal, plus the boundary-visible `output` message, and SHALL execute the hinted arguments as a second call. `next` itself is NOT client-visible for `sofer_publish_confirm`/`sofer_init` because the declared `output_schema`s project envelopes and do not list `next` (re-audited: `sofer_auth_status` is the only tool whose schema declares `next`, proving the projection is the cause); surfacing `next` would require a production schema change, outside this suite's scope — the hint-VALUE substitution IS the deliberate recovery contract. Replayed calls SHALL be asserted to reach a DIFFERENT gate than the refusal, or `ok:True` — not merely that the hint is present.
(Previously: framed as "executes the documented hint arguments" with the boundary projection as a parenthetical correction.)

#### Scenario: publish_confirm replay

- GIVEN `sofer_publish_confirm` refused at the risk gate (`ok:False`; the boundary-visible `output` message states `acknowledge_risk=True` is required)
- WHEN the documented hint VALUE `{"acknowledge_risk": True}` is replayed as a second call with the token still present
- THEN the call SHALL be refused at the approval gate — the NEXT check after the risk gate — proving the risk gate accepted the acknowledgment

#### Scenario: init refusal replay

- GIVEN `sofer_init` returning a boundary-visible refusal (`config_errors`/`output` state the required correction: file-exists → replay `{"force": True}`; name-empty → replay a non-empty name)
- WHEN the documented hint VALUES are replayed
- THEN the intended branch SHALL be reached (a different gate or `ok:True`)

### Requirement: Config-state scenario coverage (PB-04)

> Modified by `fix-dataset-identity-context` (archived 2026-09-04).

The suite SHALL cover empty config, existing config, greenfield, triage, nested output, malformed config, and delivery handoff, using real config files and public outputs (e.g., `tests/fixtures/mcp-happy-path/`), not dataclass or private-helper construction alone. The nested-output proof SHALL launch the REAL MCP process over stdio with a parent server root and an intended child cwd — `build_server(root=child)` or imported-function tests are insufficient for the parent/child identity contract.

(Previously: the nested-output scenario was proven only via `monkeypatch.chdir` + `build_server`.)

#### Scenario: Empty config

- GIVEN a TOML with no `[[file]]`
- WHEN `sofer_validate` runs via the client
- THEN it SHALL return the documented empty-config result

#### Scenario: Existing config

- GIVEN a TOML with registered files
- WHEN the pipeline runs
- THEN validate SHALL pass without re-registration

#### Scenario: Greenfield bootstrap

- GIVEN an empty directory under the server root
- WHEN `sofer_init` then `sofer_scan_apply` run
- THEN files SHALL be registered and `sofer_validate` SHALL pass

#### Scenario: Triage

- GIVEN unregistered files
- WHEN `sofer_scan_dry_run` runs
- THEN the preview SHALL list candidates without copying files or writing the TOML

#### Scenario: Nested output CWD

- GIVEN a parent server root and a dataset in a nested directory
- WHEN dataset tools run with the nested CWD
- THEN writes SHALL land under the nested dataset, not the parent root

#### Scenario: Real-process parent-root launch, cwd omitted fails closed

- GIVEN the second module-scoped stdio fixture (PB-09-compliant) spawning the real `sofer-mcp` process with server root = parent dir and an existing child dataset dir, and a live CWD at the parent root
- WHEN `sofer_init(name="test", user="<hf-user>")` runs over stdio with `cwd` omitted
- THEN the call SHALL be refused with an input-required error naming the `cwd` argument
- AND NO `parent/test.toml` SHALL be written and no `raw/` SHALL be created at the parent

#### Scenario: Real-process parent-root launch, cwd=child anchors identity

- GIVEN the same parent-root stdio fixture and the intended child dataset dir `child/`
- WHEN `sofer_init(name="test", user="<hf-user>", cwd="child")` runs over stdio
- THEN `child/test.toml` and `child/raw/` SHALL exist, `parent/test.toml` SHALL NOT
- AND the envelope SHALL report absolute `config_path` `child/test.toml` and `dataset_root` `child`

#### Scenario: Real-process greenfield chain reaches publish dry-run

- GIVEN a module-scoped stdio fixture spawning the real `sofer-mcp` process with server root = parent dir and an intended child dataset dir holding a loose source file
- WHEN `sofer_init(cwd="child")` then `sofer_scan_apply` then `sofer_validate` then `sofer_prepare` then `sofer_codebook_all` then `sofer_publish(dry_run=True)` run over one stdio session with NO manual file moves
- THEN every step SHALL return `ok:true` and the chain SHALL reach the dry-run plan (issue #115 criterion #1) with the config/root anchored under `child/`
- AND the chain SHALL stay fully offline (`sofer_publish(dry_run=True)` returns before any network branch)

### Requirement: Complete-run gate (PB-05)

CI SHALL keep the complete suite (`uv run pytest -v`) as the test gate; no focused-only command SHALL replace it.

#### Scenario: CI runs the complete suite

- GIVEN `.github/workflows/ci.yml`
- WHEN the test job is inspected
- THEN it SHALL invoke the full suite, not a focused subset

#### Scenario: No focused-only gate

- GIVEN the CI test invocation
- WHEN compared with the developer command `uv run pytest tests/ -q`
- THEN both SHALL cover the complete suite

### Requirement: Deterministic and offline (PB-06)

The suite SHALL be deterministic, run offline, and SHALL NOT require HF credentials; network-bound tools SHALL monkeypatch `publish._api`.

#### Scenario: Offline happy path

- GIVEN `publish._api` monkeypatched
- WHEN validate → prepare → codebook → profile → render → publish run
- THEN every step SHALL pass with no real network access

#### Scenario: No credentials required

- GIVEN `HF_TOKEN` absent from the environment
- WHEN the suite runs
- THEN it SHALL pass without credential-dependent skips or failures

### Requirement: Quality gates (PB-07)

After the change, `uv run pytest tests/ -q`, `uv run ruff check src/ tests/`, `uv run mypy src/`, and `git diff --check` SHALL all pass. New test helpers SHALL be type-annotated even though mypy excludes `tests/`.

#### Scenario: Full suite passes

- GIVEN the complete repository
- WHEN `uv run pytest tests/ -q` runs
- THEN all tests SHALL pass and the pre-existing count SHALL not regress

#### Scenario: Lint, types, whitespace

- GIVEN the change applied
- WHEN ruff, mypy, and `git diff --check` run
- THEN all three SHALL pass

### Requirement: SOFER_TRACE.md untouched (PB-08)

No operation of the suite, fixtures, or CI SHALL read, modify, or stage `SOFER_TRACE.md`.

#### Scenario: Untracked trace file untouched

- GIVEN `SOFER_TRACE.md` untracked at the repo root
- WHEN the suite and gates run
- THEN the file SHALL remain unchanged and unstaged

### Requirement: Shared fixtures and per-test server isolation (PB-09)

> Modified by `fix-dataset-identity-context` (archived 2026-09-04).

Boundary fixtures/helpers SHALL live in `tests/conftest.py` — a stdio server fixture, a CLI subprocess helper with cp1252 env, and a Root-unwrap `_mcp_payload` helper — and SHALL be reused across modules, not duplicated. Each test SHALL build its own server via `build_server()` because `_SERVER_ROOT`/`_APPROVAL_PHRASE` are per-process globals. Stdio spawns SHALL use one shared fixture per module to bound wall-clock; a SECOND module-scoped stdio fixture SHALL be permitted for the parent-root/child-cwd layout, keeping one spawn per module per fixture. Async SHALL use `asyncio.run`; no new dependencies and no pytest-asyncio SHALL be added.

(Previously: exactly one module-scoped stdio fixture was specified.)

#### Scenario: One server per test

- GIVEN two tests in one process
- WHEN each calls `build_server()`
- THEN no server-root or approval-phrase state SHALL leak between them

#### Scenario: Shared conftest helpers

- GIVEN `tests/conftest.py` helpers
- WHEN used by `tests/test_mcp_process.py` and sibling modules
- THEN no module SHALL re-implement the same boundary helper

#### Scenario: Lean process spawns

- GIVEN the process-boundary module
- WHEN stdio tests run
- THEN a single module-scoped server fixture SHALL be spawned, not one per test

### Requirement: Formatter integrity on a clean checkout (PB-10)

> Added by change `2026-09-14-chore-ruff-format-drift` (GitHub #177). Every scenario below is evidenced by command output rather than by a pytest assertion — the same framing this repository already uses for measured gate exit codes in the `coverage` capability (AGENTS.md rule 6).

The repository's Python sources and tests SHALL satisfy the project formatter: `uv run ruff format --check src/ tests/` SHALL exit 0 on a clean checkout, reporting zero files to reformat. Reaching that state SHALL be a formatting-only edit — exactly these six test files SHALL change (`tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`, `tests/test_mcp_registration.py`, `tests/test_profile.py`, `tests/test_publish.py`, `tests/test_splits.py`), no other path SHALL appear in the diff, and the edit SHALL NOT alter logic, assertions, imports or test behaviour. Because the formatter does not rewrite string contents, the two static contract guards keep their asserted strings.

The requirement SHALL be satisfiable with no new CI step: enforcement remains the local pre-commit `ruff-format` hook, which sees staged files only. It therefore SHALL NOT be read as closing the drift class — a formatter drift on files nobody stages can still return, and issue #194 owns both the decision to arm such a gate and that open gap. The ruff version SHALL have a single declared authority — the environment's dev dependency pin, `[tool.ruff] required-version`, and the pre-commit `rev` SHALL name the same version, asserted statically by the guard required by `ci` CI-08. Alignment SHALL remain a declaration-and-local-hook matter: it SHALL arm no CI step, and issue #194 SHALL retain ownership of the un-staged-file gap. Evidence for this requirement is command output, and the sibling gates SHALL remain green and unweakened (PB-05, PB-07, `ci` CI-01, `coverage` COV-06).

(Previously: the paragraph deferred the pin mismatch — `v0.16.7` hook versus `0.16.0` environment — to issue #195; change `2026-09-15-chore-ruff-single-authority` owns it, and no version literal remains in this spec.)

#### Scenario: Clean-checkout format check exits 0

- GIVEN a clean checkout with this change applied, no `--python` flag and no local formatting
- WHEN `uv run ruff format --check src/ tests/` runs
- THEN it SHALL exit 0 and report zero files to reformat
- AND `uv run ruff format --diff src/ tests/` SHALL emit no diff, so nothing is left to reformat

#### Scenario: Exactly the six test files changed

- GIVEN this change's diff
- WHEN `git diff --stat` is inspected
- THEN exactly the six named test files SHALL appear and no other path SHALL appear
- AND there SHALL be zero `src/sofer/`, zero `.github/workflows/`, and zero `pyproject.toml` paths

#### Scenario: Formatting-only — behaviour and asserted content preserved

- GIVEN the suite tally recorded immediately before the reformat
- WHEN `uv run pytest tests/ -q` runs after it
- THEN the passed/skipped/collected counts SHALL be identical and there SHALL be 0 failures
- AND `tests/test_ci_workflows.py` and `tests/test_coverage_contract.py` SHALL pass with their asserted strings unchanged — no logic, assertion, import, or test-behaviour edit SHALL be present

#### Scenario: No CI gate was armed, and recurrence stays owned by #194

- GIVEN `.github/workflows/**` before and after the change
- WHEN scanned for a `format --check` invocation
- THEN zero matches SHALL exist in both states and no workflow file SHALL appear in the diff
- AND enforcement SHALL remain the local pre-commit `ruff-format` hook on staged files, with recurrence owned by issue #194 rather than by any clause of PB-10

#### Scenario: Sibling gates stay green and unmoved

- GIVEN the change applied
- WHEN `uv run ruff check src/ tests/`, `uv run mypy src/`, `git diff --check`, and `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` run
- THEN each SHALL exit 0, the coverage script SHALL reach all four of its scoped gates with every row at 100.00% and an empty `Missing` column (`coverage` COV-06), and the TOTAL floor SHALL remain the config-owned `fail_under = 90` (`ci` CI-01)

### Requirement: Verifiable test-count anchor (PB-11)

> Added by change `2026-09-14-chore-agents-count-infer-type` (GitHub #162).

`AGENTS.md` rule 6 SHALL anchor its "never reduce coverage" floor to the source of the tally — the command that reports it — and SHALL NOT present a bare hardcoded pass/collected/skipped literal as the floor's only support. Any recorded figure SHALL match the tally that command reports on the change's branch.

#### Scenario: Anchor carries its own command

- GIVEN `AGENTS.md` rule 6 after the change
- WHEN the rule text is inspected
- THEN it SHALL name the count command (`uv run pytest tests/ -q`)
- AND any recorded pass/collected/skipped figure SHALL match that command's actual tally

#### Scenario: The stale literal is gone

- GIVEN `AGENTS.md:44` pre-change (`1149 tests currently pass (1151 collected, 2 skipped)`)
- WHEN post-change rule 6 is inspected
- THEN the 1149/1151/2 triple SHALL be absent
- AND no hardcoded tally SHALL remain without the reproducing command beside it

### Requirement: Zero deprecation warnings from the migrated codebook surface (PB-12)

> Added by change `2026-09-14-chore-agents-count-infer-type` (GitHub #162).

A normal suite run SHALL emit zero `DeprecationWarning`s from the codebook type-inference surface: `_infer_type` in `src/sofer/codebook.py` SHALL be deleted (the only in-repo caller migrates to the live public API), and no module, test or doc outside `openspec/changes/archive/**` SHALL reference it. The migration SHALL NOT drop, weaken, skip or reword away a behavioural assertion: `tests/test_codebook.py` SHALL assert the SAME `(values, expected)` cases against `infer_column_type`, and `test_returns_same_as_private` — whose only subject was the alias — SHALL be replaced by those same cases asserted against the live API.

#### Scenario: Suite run is deprecation-free

- GIVEN the change applied on `chore/162-agents-count-infer-type`
- WHEN `uv run pytest tests/ -q` runs
- THEN it SHALL be green
- AND the warnings summary SHALL contain zero `DeprecationWarning` lines from `sofer.codebook`

#### Scenario: Behavioural parity preserved on the live API

- GIVEN `tests/test_codebook.py` post-migration
- WHEN `uv run pytest tests/test_codebook.py -q` runs
- THEN every pre-change `(values, expected)` case SHALL still assert the same expected output, now against `infer_column_type`, with no case deleted, relaxed or parametrised away

#### Scenario: No residual alias reference

- GIVEN the post-change tree
- WHEN `_infer_type` is searched over `src/`, `tests/`, `AGENTS.md` and the READMEs
- THEN zero matches SHALL be found outside `openspec/changes/archive/**` historical prose

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

### Requirement: Repository-declared ruff-format hook file scope (PB-14)

> Added by change `2026-09-15-chore-ruff-format-hook-scope` (issue #216).

The `ruff-format` pre-commit hook's file-type scope SHALL be a **repository declaration**, not an
inherited upstream default: the `astral-sh/ruff-pre-commit` hook entry in `.pre-commit-config.yaml` SHALL
declare an explicit `types_or` naming the types this repository intends the formatter to see — `python`,
`pyi`, and `jupyter` — and `markdown` SHALL NOT be among them. The decision is deliberate and
rationale-bearing: upstream widened the manifest's `types_or` to include `markdown` between
`ruff-pre-commit` 0.15.21 and 0.16.6 without this repository changing anything, and the pinned hook then
rewrote the fenced Python inside `README.md` and `README_ES.md` (issue #216). The declared scope SHALL
therefore NOT be read as a mirror of the upstream default, a `rev` bump SHALL NOT widen it silently, and
the declared tag vocabulary SHALL stay consistent with the sibling scope decision
`[tool.ruff] extend-exclude = ["openspec"]` in `pyproject.toml`.

This requirement SHALL constrain **the hook only**. `types_or` is a pre-commit filter, not a ruff setting:
a direct `ruff format <path>` still sees Markdown, and this requirement SHALL NOT be read as narrowing the
formatter itself, as adopting a Markdown formatter, or as arming any gate. Issue **#194** SHALL retain
ownership of the decision to arm a `ruff format --check` gate and of that gate's path scope; this
requirement SHALL arm no CI step. This change SHALL NOT move the `ruff-pre-commit` `rev`, SHALL NOT edit
`pyproject.toml` or any `src/sofer/**` path, and SHALL leave `README.md` / `README_ES.md` byte-identical.

The declaration SHALL be statically guarded in `tests/test_ci_workflows.py` (the established home for
static repository-shape contracts): the hook entry SHALL declare `types_or`, SHALL declare it as a list,
and `markdown` SHALL NOT appear in it. The guard SHALL assert the **defect class**, not mirror the
declared list, so a legitimate future widening to another type keeps it green. The guard SHALL assert
declaration shape only: that pre-commit honours the override is verify-phase runtime evidence and SHALL
NOT be asserted from pytest (the suite spawns no `pre-commit`).

#### Scenario: The hook declares its own scope and excludes Markdown

- GIVEN `.pre-commit-config.yaml` as committed by this change
- WHEN `tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown` parses it with the module's existing `_load_yaml` helper and selects the `astral-sh/ruff-pre-commit` repo's hook whose `id` is `ruff-format`
- THEN the entry SHALL be found exactly once and SHALL declare a list-valued `types_or`
- AND `"markdown"` SHALL NOT be a member of that list
- AND the guard SHALL be red against an entry with no `types_or` key and green once the config line lands (red then green, both recorded in the verify report)
- AND no other tag SHALL be asserted, so adding a legitimate type leaves the guard green

#### Scenario: The hook no longer receives Markdown and leaves the READMEs untouched

- GIVEN the pinned `ruff-pre-commit` hook materialised in the local pre-commit cache and the repository's declared `types_or` in place
- WHEN `uv run pre-commit run ruff-format --files README.md` runs
- THEN the hook SHALL report the file as not a hook input (`(no files to check)Skipped`) and SHALL exit 0
- AND `uv run pre-commit run ruff-format --all-files` SHALL show no Markdown batch — no `files were modified by this hook` — listing only `python` / `pyi` / `jupyter` inputs
- AND `git diff --stat -- README.md README_ES.md` SHALL be empty afterwards
- AND the hook's **file-list output**, not its exit code, SHALL be the discriminating evidence: the entry is the fixing command `ruff format --force-exclude`, which exits 0 after rewriting (the #195 trap)
- AND this evidence is **verify-phase runtime evidence** — the commands above pasted with their exit codes into the verify report (PB-10 / CI-08 S4 precedent)

---

## Test Mapping

Every `#### Scenario:` in this spec appears in exactly one row below — the full scenario↔row bijection
(`mapping-checker` MC-02; AGENTS.md rule 6; rules.specs). Static config assertions live in
`tests/test_ci_workflows.py`; the remaining rows route to declared verify-phase evidence (`verify:`),
whose evidence classes are stated in each scenario's own text. The PB-01..PB-13 backfill lands here:
their rows are `verify:` references to those scenario-stated evidence classes — not invented tests, and
not a machine-verified claim that a test exercises the scenario.

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| PB-01 | tools/list and call via in-process client | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` in-process `Client(server)`: `tools/list` lists the 14 callables and one `tools/call` returns the documented envelope |
| PB-01 | Seven publish/scan_apply conversions through the client | verify:Verify-phase runtime evidence — the seven conversion sites in `tests/test_mcp_server.py` run via `_call(...)` through `Client(server)`; valid-input sites return the documented envelope shape |
| PB-01 | Stdio transport with clean framing | verify:Verify-phase runtime evidence — `tests/test_mcp_process.py` stdio subprocess `initialize → tools/list → tools/call`; every response is valid JSON-RPC with no stray stdout bytes |
| PB-01 | No remaining direct-call proofs | verify:Verify-phase static evidence — enumeration of direct-call sites across `tests/test_mcp_server.py` and `tests/test_mcp_schema.py`: zero registered tool imported and called directly |
| PB-01 | Invalid Literal target rejected before the tool body | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py::test_garbage_target_dry_run_false_refused_no_api` and the `ToolError` rejection for non-`local` `sofer_publish` targets at the `Client(server)` boundary |
| PB-01 | Stream-restore conversion exercises the tool body | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py::TestStreamRestore::test_stdout_stderr_restored_after_raise` via `Client(server)` |
| PB-01 | auth_status routes via the boundary and exposes next | verify:Verify-phase runtime evidence — `tests/test_mcp_schema.py::test_auth_status_no_leak` via `Client(server)`; asserts the envelope includes `next` |
| PB-02 | Help via subprocess | verify:Verify-phase runtime evidence — `tests/test_cli.py` via `tests/conftest.py::run_cli`: `python -m sofer.cli --help` exits 0 and lists every subcommand |
| PB-02 | cp1252 help on the ubuntu matrix | verify:Verify-phase runtime evidence — `tests/test_cli.py` cp1252 subprocess runs for `--help`, every `<cmd> --help`, `mcp add --help`, and `mcp remove --help`; exit 0 and strict-decodable stdout |
| PB-02 | cp1252 runtime console output | verify:Verify-phase runtime evidence — `tests/test_cli.py` cp1252 `validate` (rc 1, `Configuration errors`) and `scan --dry-run` (rc 0, `DRY RUN`) subprocess runs |
| PB-02 | Dispatch exit codes | verify:Verify-phase runtime evidence — `tests/test_cli.py` subprocess run of an unknown command; argparse exits 2 |
| PB-03 | publish_confirm replay | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `sofer_publish_confirm` risk-gate refusal, then the `{"acknowledge_risk": True}` replay reaches the approval gate |
| PB-03 | init refusal replay | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `sofer_init` file-exists/name-empty refusals replayed with the hinted values reach the intended branch |
| PB-04 | Empty config | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `sofer_validate` via `Client(server)` on a TOML with no `[[file]]` |
| PB-04 | Existing config | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` pipeline on a TOML with registered files; validate passes without re-registration |
| PB-04 | Greenfield bootstrap | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `sofer_init` then `sofer_scan_apply` on an empty directory; files register and `sofer_validate` passes |
| PB-04 | Triage | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `sofer_scan_dry_run` on unregistered files; the preview lists candidates without copying files or writing the TOML |
| PB-04 | Nested output CWD | verify:Verify-phase runtime evidence — `tests/test_mcp_process.py` dataset tools with the nested CWD; writes land under the nested dataset, not the parent root |
| PB-04 | Real-process parent-root launch, cwd omitted fails closed | verify:Verify-phase runtime evidence — `tests/test_mcp_process.py` second module-scoped stdio fixture; `sofer_init` with `cwd` omitted is refused and no `parent/test.toml` or `raw/` is written |
| PB-04 | Real-process parent-root launch, cwd=child anchors identity | verify:Verify-phase runtime evidence — `tests/test_mcp_process.py` stdio `sofer_init(cwd="child")`; `child/test.toml` and `child/raw/` exist and `parent/test.toml` does not |
| PB-04 | Real-process greenfield chain reaches publish dry-run | verify:Verify-phase runtime evidence — `tests/test_mcp_process.py` module-scoped stdio fixture running init → scan_apply → validate → prepare → codebook_all → publish(dry_run=True) fully offline |
| PB-05 | CI runs the complete suite | verify:Verify-phase static evidence — `.github/workflows/ci.yml` `test` job runs `uv run pytest -v`, the full suite rather than a focused subset |
| PB-05 | No focused-only gate | verify:Verify-phase static evidence — the CI `uv run pytest -v` and the developer `uv run pytest tests/ -q` both cover the complete suite |
| PB-06 | Offline happy path | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` with `publish._api` monkeypatched: validate → prepare → codebook → profile → render → publish all pass with no real network access |
| PB-06 | No credentials required | verify:Verify-phase runtime evidence — suite run with `HF_TOKEN` absent from the environment; passes with no credential-dependent skips or failures |
| PB-07 | Full suite passes | verify:Verify-phase runtime evidence — `uv run pytest tests/ -q` green with the pre-existing count not regressed |
| PB-07 | Lint, types, whitespace | verify:Verify-phase runtime evidence — `uv run ruff check src/ tests/`, `uv run mypy src/`, and `git diff --check` all exit 0 |
| PB-08 | Untracked trace file untouched | verify:Verify-phase runtime evidence — `SOFER_TRACE.md` untracked at the repo root; the suite and gates leave it unchanged and unstaged |
| PB-09 | One server per test | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py`/`tests/conftest.py` two tests calling `build_server()`; no server-root or approval-phrase state leaks between them |
| PB-09 | Shared conftest helpers | verify:Verify-phase static evidence — `tests/conftest.py` helpers reused by `tests/test_mcp_process.py` and sibling modules; no module re-implements a boundary helper |
| PB-09 | Lean process spawns | verify:Verify-phase runtime evidence — `tests/test_mcp_process.py` module-scoped stdio fixture spawns a single server per module, not one per test |
| PB-10 | Clean-checkout format check exits 0 | verify:Verify-phase runtime evidence — `uv run ruff format --check src/ tests/` exits 0 with zero files to reformat and `--diff` emits no diff |
| PB-10 | Exactly the six test files changed | verify:Verify-phase static evidence — `git diff --stat` of the PB-10 change shows exactly the six named test files and zero `src/sofer/`, `.github/workflows/`, `pyproject.toml` paths |
| PB-10 | Formatting-only — behaviour and asserted content preserved | verify:Verify-phase runtime evidence — `uv run pytest tests/ -q` after the reformat reports identical pass/skip/collect counts with 0 failures |
| PB-10 | No CI gate was armed, and recurrence stays owned by #194 | verify:Verify-phase static evidence — `.github/workflows/**` scanned for a `format --check` invocation in both the pre- and post-change states: zero matches |
| PB-10 | Sibling gates stay green and unmoved | verify:Verify-phase runtime evidence — `uv run ruff check src/ tests/`, `uv run mypy src/`, `git diff --check`, and `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` all exit 0 |
| PB-11 | Anchor carries its own command | verify:Verify-phase static evidence — `AGENTS.md` rule 6 text names `uv run pytest tests/ -q` as the count command; any recorded figure matches that command's tally |
| PB-11 | The stale literal is gone | verify:Verify-phase static evidence — `AGENTS.md` rule 6 post-change carries no stale pass/collected/skipped triple, and no hardcoded tally remains without the reproducing command beside it |
| PB-12 | Suite run is deprecation-free | verify:Verify-phase runtime evidence — `uv run pytest tests/ -q` green; the warnings summary contains zero `DeprecationWarning` lines from `sofer.codebook` |
| PB-12 | Behavioural parity preserved on the live API | verify:Verify-phase runtime evidence — `uv run pytest tests/test_codebook.py -q` green with every pre-change `(values, expected)` case asserted against `infer_column_type` |
| PB-12 | No residual alias reference | verify:Verify-phase static evidence — search of `src/`, `tests/`, `AGENTS.md`, and the READMEs for `_infer_type`: zero matches outside `openspec/changes/archive/**` |
| PB-13 | Resolution leaves the process environment unchanged (the gate) | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `_get_hf_token()` with a temp-cwd `.env`; returns `"from-dotenv"` and `os.environ` equals the pre-call snapshot |
| PB-13 | Environment presence beats `.env` even when the value is blank | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `_get_hf_token()` with a present whitespace-only `HF_TOKEN` and `HF_HUB_TOKEN=alias-token`; returns `"alias-token"` |
| PB-13 | `.env` supplies a value only when the environment omits the name | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `_get_hf_token()` with `HF_TOKEN` absent from the environment and `.env` holding it; returns `"from-dotenv"` |
| PB-13 | `.env`-only disable flag still gates the implicit file fallback | verify:Verify-phase runtime evidence — `tests/test_mcp_server.py` `_get_hf_token()` with `HF_HUB_DISABLE_IMPLICIT_TOKEN=true` only in `.env`; returns `None` rather than the file token |
| PB-13 | No test leaks a token to a later test (issue #176) | verify:Verify-phase runtime evidence — same-process ordering of `tests/test_mcp_server.py:3168` before `tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array`; the victim observes no `HF_TOKEN` and passes |
| PB-14 | The hook declares its own scope and excludes Markdown | test:tests/test_ci_workflows.py::test_ruff_format_hook_excludes_markdown — YAML inspection of the `ruff-format` hook entry in `.pre-commit-config.yaml` |
| PB-14 | The hook no longer receives Markdown and leaves the READMEs untouched | verify:Verify-phase runtime evidence — `uv run pre-commit run ruff-format --files README.md` and `--all-files`, plus an empty `git diff --stat -- README.md README_ES.md` |
