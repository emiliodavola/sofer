---
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:584da2d6f6bd3f0e65f5231e61509748b8bc6b608525077c8f82a222e5ccbf31
verdict: pass
blockers: 0
critical_findings: 0
requirements: 0/0
scenarios: 5/5
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:20fc14ba80b1ae8c034551243521518034cef71791c2b4dc0e763105b44a7b45
build_command: uv run ruff check src/ tests/ && uv run mypy src/ && git diff --check
build_exit_code: 0
build_output_hash: sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7
---

# Verify Report — `2026-09-11-fix-status-resource` (issue #146)

> NOTE: Independent, adversarial verification of the working-tree diff on branch
> `fix/146-status-resource` (HEAD `d73c59a`, base `dev`; change NOT committed — the
> commit/PR lifecycle rows are parent-owned and remain defer-red by design). The
> verifier re-derived every acceptance signal through fresh client round-trips and
> re-ran all gates; nothing was taken from apply-progress.md on faith. All 18
> implementation task rows are `- [x]`; the only unchecked rows (3) carry
> `<!-- sdd-owner: parent -->` (commit / push+PR / post-apply review) and are **not**
> implementation tasks — verification is complete, archive-ready pending sync.

## Verdict per issue #146 acceptance criterion

| #146 criterion | Verdict | Evidence (fresh, this verify) |
|---|---|---|
| 1. `resources/list` returns the static resource | PASS | Independent probe: `client.list_resources()` → `{'sofer://status'}` (non-empty); `client.list_resource_templates()` → exactly the 3 URI templates, `sofer://status` absent (static, no `{}` in URI, no-arg handler). Handler registered after the 3 templates in `_register_resources` (`server.resource("sofer://status", description=...)(_resource_status)`), `src/sofer/mcp_server.py`. |
| 2. Content fields correct, build-time state | PASS | Probe: payload keys == exactly `{approval_configured, phrase_source, root, version, started_at, tool_count}`; `approval_configured` is `True` (bool); `phrase_source == "explicit"`; `root == str(tmp.resolve())`; `version == get_version()` (`0.1.dev386+g1ad1d177f`, non-empty); `started_at == ms._SERVER_STARTED_AT` (ISO-8601 UTC µs, regex `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00`); `tool_count == 14 == len(workflow.WORKFLOW_METADATA)` (derived, not hardcoded). Cross-surface: equality with `sofer_auth_status` envelope of the same build (see cross-surface section). |
| 3. Unit tests cover registration and content | PASS | `TestStatusResource` (6 tests) all pass: `6 passed` on `-k TestStatusResource`. Coverage: listed/content/consistency/no-leak/unconfigured-invariant/hermetic-deterministic. |

## Scenario → test map (spec delta, 5 scenarios, all present + green)

| §Spec scenario | Test(s) | Status |
|---|---|---|
| Dataset resource returns raw TOML (verbatim-kept) | `TestResources::test_dataset_resource_raw_toml` | pin, unmodified, PASS (9 in class) |
| Codebook resource generates on demand (verbatim-kept) | `TestResources::test_codebook_resource_generates_on_demand` | pin, unmodified, PASS |
| Metadata resource when present (verbatim-kept) | `TestResources::test_metadata_resource_when_present`, `test_metadata_missing_clear_error` | pins, unmodified, PASS |
| Static status resource listed with posture content (new) | `TestStatusResource::test_status_resource_listed`, `test_status_resource_content_explicit` | new, PASS |
| Status posture consistent across surfaces, free of secret material (new) | `TestStatusResource::test_status_resource_consistent_with_auth_status`, `test_status_resource_no_phrase_leak`, `test_status_resource_unconfigured_invariant` (+ `test_status_resource_hermetic_deterministic` for the zero-side-effect clause) | new, PASS |

Spec delta: only `## MODIFIED Requirements` (MSP-R07) — no ADDED/REMOVED; requirement 10.8 (#145)
and APX-01 (#144) untouched; canonical `openspec/specs/mcp-server/spec.md` has no working-tree edit.

## No-leak (adversarial)

Independent probe (explicit `phrase123` + env `envphrase456`): `json.dumps(payload)` contains
neither `phrase123` nor `envphrase456` nor either `hashlib.sha256(...).hexdigest()` — all four
assertions True. The payload is 6 fields of pure build-time metadata (bool, enum string, root
path, two `_SERVER_*` strings, registry length); `phrase_source` describes the configuration
path only, never material. The new guard test mirrors the existing probe at
tests/test_mcp_server.py:387 (sha256 probes incl.) and deliberately does NOT probe the bare
prefix "phrase" (substring of `phrase_source`) — correct, not a gap.

## Cross-surface (one fact source, two surfaces)

Independent probe with a real dataset (`_make_dataset`): resource payload vs `sofer_auth_status`
envelope of the same build — `approval_configured True==True`, `phrase_source "explicit"=="explicit"`,
`started_at` byte-identical to `server_started_at` (same timestamp), `version` identical to
`server_version`. The handler reads the exact same globals through the exact same expressions
(`_APPROVAL_PHRASE is not None`, `_PHRASE_SOURCE`, `_SERVER_STARTED_AT`, `_SERVER_VERSION`;
mcp_server.py:291/349/351/352; envelope identity at :1857, fields at :1888-1894). Envelope/hints
machinery (#144/#145) is untouched by the diff (only +45/−2 in mcp_server.py: handler +
registration + docstring lines).

## Deviations / findings

- **Apply-progress deviation claims confirmed accurate**: TestResources holds 9 (not 8/7) pre-existing
  tests — no-touch holds by construction: `git diff -U0 tests/test_mcp_server.py` shows **zero**
  deletion lines (pure insertion hunk, `@@ -1642,6 +1644,186 @@`); TestToolRoster unchanged (3 passed,
  `test_exactly_fourteen_callables`, roster == 14 == `len(WORKFLOW_METADATA)`).
- No 7th `test_status_resource_static_not_template` test: the static-not-template clause is asserted
  behaviorally inside `test_status_resource_listed` (`sofer://status` ∉ template URIs; exact 3-template
  set equality). Consistent with tasks.md (authoritative: 6 tests) — no completeness gap.
- Test-side `str(r.uri)` cast for fastmcp v3 `AnyUrl` — documented in apply-progress, verified in the
  probe (no handler change needed).
- **Assertion quality**: all new tests assert by equality/identity against sources of truth
  (`get_version()`, `workflow.WORKFLOW_METADATA`, resolved root, `_SERVER_STARTED_AT`), exact key-set
  equality, fullmatch regex, both-direction invariant, byte-identical reads + rglob no-write check.
  No tautologies, ghost loops, type-only or smoke-only assertions.
- **Review workload**: actual diff **227 insertions / 2 deletions (~229 net lines)** vs ~250-300
  forecast — under the 400-line budget; single PR (chained PRs not recommended); no `size:exception`.
  Scope is issue #146 ONLY: diff touches just `src/sofer/mcp_server.py` (handler + registration +
  docstring) and `tests/test_mcp_server.py` (pure additions). No scope creep; no README/README_ES,
  pyproject, workflow.py, cli.py, canonical spec, no tags/releases/version bumps.

## Status & actionContext findings

- Native status consumed: change `2026-09-11-fix-status-resource`, state `ready` for verify;
  18/18 implementation tasks complete; `actionContext`: mode `repo-local`,
  `allowedEditRoots [C:\Users\elaze\Desktop\sofer]`, no warnings; `nextRecommended: sdd-verify`.
- Strict TDD: NOT active (`strict_tdd: false` in apply-progress; no TDD table required — standard mode).

## Test / validation commands (literal)

- `uv run pytest tests/ -q` → **1495 passed, 6 skipped, 13 warnings in 53.15s** (exit 0)
  (= baseline 1489 + 6 new TestStatusResource; matches expected delta exactly)
- `uv run pytest tests/test_mcp_server.py -k TestStatusResource -q` → **6 passed**
- `uv run pytest tests/test_mcp_server.py -k TestResources -q` → **9 passed** (unchanged — no-touch)
- `uv run pytest tests/test_mcp_server.py -k TestToolRoster -q` → **3 passed** (roster stays 14)
- `uv run ruff check src/ tests/` → **All checks passed!**
- `uv run ruff format --check src/sofer/mcp_server.py tests/test_mcp_server.py` → **2 files already formatted**
- `uv run mypy src/` → **Success: no issues found in 32 source files**
- `git diff --check` → clean
- `uv run python -c "import sofer.mcp_server"` → import OK; `len(workflow.WORKFLOW_METADATA)` == 14
- Debug probe for the cross-surface run originally hit a minimal-TOML `output: Failed to read TOML: 'repo_id'`
  envelope (envelope returns None posture fields on a config error); re-run with a real
  `_make_dataset(tmp_path)` dataset — all 4 shared fields equal. Not an implementation defect.

## Blockers

None. 0 blockers, 0 critical findings.

## Skills resolution

- Skill loaded: `C:\Users\elaze\.pi\agent\npm\node_modules\gentle-pi\skills\gentle-ai\SKILL.md`
  (parent-injected path). `skill_resolution: paths-injected`. No fallback needed.

## Key Learnings

- fastmcp v3 `read_resource` returns a lazy sequence — `contents[0].text` on the result directly
  (a `CallToolResult.data` is a `types.Root` dataclass for envelope tools; the resource read path
  is a plain list of `ResourceContents`).
- `sofer_auth_status` returns an error envelope (posture fields `None`) when the config TOML fails
  to parse — cross-surface probes must build a real dataset (`_make_dataset`) or they compare
  against `None` and produce false alarms.
- The no-leak probe must never scan for the bare prefix "phrase" — it is a substring of
  `phrase_source`; the sha256-twin probe is the robust form and mirrors the :387 pin.
- Static-vs-template classification is URI/arity-driven (`{` in URI OR handler params → template);
  a no-arg handler on `sofer://status` lands under `resources/list` — the issue's fix is exactly
  this structural fact, and the round-trip must assert BOTH list callbacks.