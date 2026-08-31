# Exploration: feat-mcp-auto-install — promote fastmcp from optional extra to required dependency

**Change:** `feat-mcp-auto-install` (Issue #100)  
**Date:** 2026-08-30  
**Mode:** hybrid (Engram + OpenSpec)  
**Status:** exploration only — no proposal created

---

## Current State

### 1. pyproject.toml dependency layout — file:line evidence

| Section | Lines | Content | Verdict |
|---|---|---|---|
| `[project].dependencies` | `pyproject.toml:21-29` | `huggingface-hub>=0.26.0`, `openpyxl>=3.1`, `pyarrow>=14.0`, `python-dotenv>=1.0.0`, `tomli>=2.0; python_version < '3.11'`, `tomli-w>=1.0`, `pyyaml>=6.0` — **no `fastmcp`** | Lean base |
| `[project.optional-dependencies].mcp` | `pyproject.toml:36-37` | `mcp = ["fastmcp>=3.4,<4"]` — single pin, source of truth for MCP | Optional |
| `[project.scripts]` | `pyproject.toml:39-41` | `sofer = "sofer.cli:main"` + `sofer-mcp = "sofer.mcp_server:main"` | Two entry points, one broken without extra |
| `[dependency-groups].dev` | `pyproject.toml:43-50` | `fastmcp>=3.4,<4` alongside `pytest`, `ruff`, `mypy`, `pre-commit` | Production pin duplicated for tests |
| `uv.lock` | `uv.lock:1943-1984` | `sofer` editable has `dependencies` without fastmcp; `[package.optional-dependencies] mcp = [{name="fastmcp"}]` at `uv.lock:1955-1957`; `[package.dev-dependencies] dev = [{name="fastmcp"}]` at `uv.lock:1960-1962`; resolved `fastmcp==3.4.7` (`uv.lock:527`) + `fastmcp-slim==3.4.7` (`uv.lock:539`); markers `extra == 'mcp'` (`uv.lock:1971`) | Lock mirrors pyproject split |
| `[tool.sofer]` | `pyproject.toml:88-148` | `output_dir`, `raw_dir`, `parquet_*`, `report_*`, `codebooks_dir`, `profile_dir`, `render_dir`, `agent_resource_max_bytes`, `card_collapse_threshold`, etc. | **No MCP flag** — correct; no new config needed |

**Installed wheel (current):**
```bash
uv run python -c "import importlib.metadata; print([r for r in importlib.metadata.distribution('sofer').requires if 'fastmcp' in str(r).lower()])"
# ["fastmcp<4,>=3.4; extra == 'mcp'"]   — still extra-gated
# METADATA: Provides-Extra: mcp / Requires-Dist: fastmcp<4,>=3.4; extra == 'mcp' (101:103)
```

**Repro confirmed (#100):** `uv tool install git+https://github.com/emiliodavola/sofer.git@v0.3.6 --force` → 22 packages, 2 executables, zero `fastmcp` → `sofer-mcp` → `ModuleNotFoundError: No module named 'fastmcp'` → `ImportError`.

### 2. Runtime guard in src/sofer/mcp_server.py:55-57

```python
# src/sofer/mcp_server.py:54-59
try:
    from fastmcp import FastMCP as _FastMCP
except ImportError as _exc:  # pragma: no cover - exercised via sys.modules monkeypatch
    raise ImportError(
        "sofer's MCP server requires the 'mcp' extra — install it with: pip install 'sofer[mcp]'"
    ) from _exc
```

**When it triggers:** Top-level import time — `import sofer.mcp_server` fails immediately when `fastmcp` absent. The `sofer-mcp` console script (`mcp_server:main` at `mcp_server.py:1488-1496`) never reaches `build_server()`.

**How it should evolve after promotion:**
- **Keep as degraded-install guard** (recommended). After promotion the path becomes unreachable under a correct install, but remains valuable for partial/corrupt wheels, `pip install --no-deps`, or offline `--no-build-isolation` edge cases.
- **Update message** to mention both ecosystems with correct PEP 508 direct-reference syntax:
  ```
  "sofer's MCP server requires 'fastmcp' — install with: pip install 'sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z' or uv tool install 'sofer[mcp] @ git+...' --force / uvx --from git+... --with 'sofer[mcp]' sofer-mcp --help"
  ```
  Existing hint (`pip install 'sofer[mcp]'`) is incomplete for `uv tool` users and omits the `git+https` direct-reference form.
- **Do NOT remove** — silent `ModuleNotFoundError` without guidance is worse UX; the guard is ~3 lines and has `pragma: no cover` test coverage.
- Alternative (remove guard) rejected: trades a clear degraded-install diagnostic for a raw `ModuleNotFoundError`.

### 3. Install docs — README.md / README_ES.md (AGENTS.md §13 sync required)

| File | Lines | Current wording | Issue |
|---|---|---|---|
| `README.md` Install | `README.md:38-52` | `uv tool install git+https://github.com/emiliodavola/sofer.git@vX.Y.Z` / `pip install git+...` — no extra, no PEP 508 `name @ URL` | Delivers broken `sofer-mcp` |
| `README_ES.md` Install | `README_ES.md:40-54` | Same commands, Spanish prose, English commands | Same bug |
| `README.md` AI and MCP server → Install the `mcp` extra | `README.md:438-445` | `pip install 'git+https://github.com/emiliodavola/sofer.git@vX.Y.Z[mcp]'` | **Syntactically broken:** PEP 508 direct references require `name[extra] @ URL`, not `URL[extra]`. Neither `pip` nor `uv` honors suffix form. |
| `README_ES.md` AI and MCP server → Install the `mcp` extra | `README_ES.md:473-481` | Same broken suffix form | Same bug |
| Both READMEs — AI section intro | `README.md:433-436` / `README_ES.md:465-471` | "The base install stays lean — `fastmcp` is an optional extra" | Must flip to "included by default — `sofer[mcp]` is now an alias" post-promotion |
| Both READMEs — uv tool / uvx examples | nowhere | Missing | Must add `uv tool install "sofer[mcp] @ git+...@vX.Y.Z" --force` + `uvx --from "git+...@vX.Y.Z" --with "sofer[mcp]" sofer-mcp --help` |

**AGENTS.md §13:** `README.md` ↔ `README_ES.md` headings/section order and code blocks must stay mirrored — any fix lands in **same commit** with English commands, Spanish prose. Verified: both files currently share `## Install`, `## AI and MCP server` headings in same order; code blocks diverge only by prose.

**Related docs:** `docs/configuration.md:1-60` — no `mcp`/`fastmcp` mentions (`grep` empty); no extra listing to update. No change needed there.

### 4. Affected specs — openspec/specs/

| Spec | File:line | Codifies optional-extra contract? | Action needed |
|---|---|---|---|
| `mcp-server/spec.md` | `mcp-server/spec.md:31-48` MSP-R02 | **Yes — explicitly:** "The base install SHALL stay lean — `fastmcp`/`pydantic` SHALL NOT be core dependencies." + scenarios "Import without the extra fails clearly" / "Extra installs cleanly" | **MODIFIED requirement** — delta must replace with "SHALL be included by default" and deprecate/alias the extra. Scenarios become "lean == MCP-included" + "sofer[mcp] alias still works". |
| `mcp-server/spec.md` | `mcp-server/spec.md:321-334` MSP-R12 | `pyproject.toml SHALL add [project.optional-dependencies] mcp = ["fastmcp>=3.4,<4"]` + wheel MUST have `Provides-Extra: mcp` | **MODIFIED** — SHALL declare in `dependencies`; MAY keep alias `mcp = ["fastmcp>=3.4,<4"]` for one minor. Scenarios: `Requires-Dist: fastmcp>=3.4,<4` (unconditional) + `Provides-Extra` optional. |
| `packaging/spec.md` | `packaging/spec.md:67-78` PKG-03 | `sofer = sofer.cli:main` only; no mention of `sofer-mcp` | Consider extending scenario to assert `sofer-mcp` present too (already in `release.yml:87`). Not blocking. |
| `tool-config/spec.md` | `tool-config/spec.md:1-300` | No MCP keys | **No delta** — `agent_resource_max_bytes` already covers MCP. No new `[tool.sofer]` key. |

No other spec owns the contract.

### 5. Tests for MCP

| Suite | File | Lines / coverage | Imports fastmcp? | Promotion impact |
|---|---|---|---|---|
| `test_mcp_server.py` | `tests/test_mcp_server.py:1-1283+` | ~1300 LOC, 13 test classes, 30+ scenarios (MSP-R01..R12, CF-1/2): `TestImportWithoutExtra`, `TestToolRoster` (10 callables), `TestStdioSmoke`, `TestNetworkOffline`, `TestPublishAuthorizationLadder`, `TestContainment` (8 vectors), `TestOutputTargetContainment`, etc. | **Yes** — `from fastmcp import Client` (`test_mcp_server.py:20`), `from mcp import ...` stdio. Relies on `fastmcp` in `dev` group. | **Test update required:** `TestImportWithoutExtra::test_import_raises_without_fastmcp` (`test_mcp_server.py:139-146`) asserts `ImportError` with `"sofer[mcp]"` — after promotion this test must be **inverted or removed**: `import sofer.mcp_server` should *succeed* without the extra. Alternatively keep as degraded-install guard test via `sys.modules` monkeypatch. `TestWheelPackaging::test_wheel_declares_script_and_extra` (`test_mcp_server.py:964-1005`) asserts `Provides-Extra: mcp` + `Requires-Dist: fastmcp>=3.4,<4` *unconditionally in METADATA* — currently checks `Provides-Extra` present; after promotion must assert `Requires-Dist: fastmcp>=3.4,<4` without `extra == 'mcp'` marker, with `Provides-Extra` optional. |
| `test_mcp_registration.py` | `tests/test_mcp_registration.py:1-564` | MCP-REG-01/02 + CLI-R09: `resolve_config_path`, `build_entry`, `merge`, idempotency, backup `.bak`, atomic write, dry-run, unreadable, `validate_cwd`, env forwarding, delegation (`probe_native`, `delegate_add`), `remove`. | **No** — imports only `sofer.cli`, `sofer.mcp_registration`, stdlib. No `fastmcp` dep. | **No change** — unaffected by dependency move. |
| New smoke needed? | — | Cover "fastmcp present after clean install" | — | Lightweight: `python -c "import fastmcp; print(fastmcp.__version__)"` or reuse `test_wheel_declares_script_and_extra` with updated assertion. No new test file required. |

**Existing green state:** `uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` passes today because `dependency-groups.dev` pulls `fastmcp`. Promotion does not break this path — it makes the *non-dev* path match it.

### 6. Packaging implications

**Wheel METADATA — before vs after:**

| Before (v0.3.6) | After (promotion, alias kept) |
|---|---|
| `Requires-Dist: huggingface-hub>=0.26.0` ... `Provides-Extra: mcp` / `Requires-Dist: fastmcp>=3.4,<4; extra == 'mcp'` | `Requires-Dist: fastmcp>=3.4,<4` (unconditional) + `Provides-Extra: mcp` / `Requires-Dist: fastmcp>=3.4,<4; extra == 'mcp'` (redundant alias) |
| `sofer-mcp` installed but crashes | `sofer-mcp --help` succeeds immediately |

If alias removed instead: `Provides-Extra: mcp` line disappears — `pip install "sofer[mcp]"` would warn/error. Keep alias for one minor (see §8).

**release.yml build checks (`release.yml:71-88`):**
- `Verify wheel METADATA version matches the tag` — unaffected (still `hatch-vcs`).
- `Verify wheel METADATA completeness (PKG-02)` — checks `Classifier`, `Project-URL` — unaffected.
- `Verify console-script entry point` — checks `sofer = sofer.cli:main` — should be extended to also assert `sofer-mcp = sofer.mcp_server:main` (already in wheel, but CI only checks one). Non-blocking but recommended.
- No `Requires-Dist: fastmcp` assertion yet — could add, but `test_wheel_declares_script_and_extra` already covers it.

**uv lock regeneration:**
```bash
# after moving fastmcp to dependencies in pyproject.toml:
uv lock   # regenerates uv.lock:1943-1984 — fastmcp moves from optional-dependencies to dependencies
uv sync
uv build
```
No `tool.sofer` or `docs/configuration.md` change beyond dependency move.

**Size impact:**
- `fastmcp==3.4.7` wheel: 8 KB (launcher) → `fastmcp-slim==3.4.7` wheel: 769 KB → transitive `mcp==1.24.x` + `anyio>=4.5` + `httpx>=0.27` + `h11` + `starlette` + `sse-starlette` + `pydantic>=2.11` (already indirect) + `uvicorn`, `python-multipart`, etc.
- **Measured delta:** `uv tool install ...@v0.3.6` = 22 packages; with `sofer[mcp]` = 30+ packages. **~8-12 MB** installed footprint (pip-measured). Domains already pay `pyarrow` (40 MB) + `huggingface-hub` — marginal.
- No native extensions beyond `pyarrow` already required; pure Python additions do not affect `build-system` (`hatchling`, `hatch-vcs` unchanged).

### 7. Alternatives — comparison

| # | Approach | Pros | Cons | Effort | Why rejected / trade-off |
|---|---|---|---|---|---|
| **A** | **Promote `fastmcp` to required (keep `mcp` alias)** — recommended | `sofer-mcp` works out-of-the-box; zero first-run crash; `pip install "sofer[mcp]"` still works; aligns with reporter preference `prefiero que instale automáticamente`; footprint modest vs `pyarrow`; docs converge cleanly | +8 pkgs / ~10 MB for dataset-only users who never use MCP | **Low** — 1 line in `pyproject.toml` + lock + docs + guard wording | **Winner** — fixes broken-by-default executable, respects UX vote, backward compat via alias |
| **B** | Keep optional but fix docs only (correct PEP 508 + add `uv tool`/`uvx` examples) | Preserves lean base for dataset-only installs; no wheel change | Preserves first-run crash; every new MCP user must discover `[mcp]` + correct `name[extra] @ URL` placement; reporter explicitly rejected ("prefiero que instale automáticamente") | Low | Rejected per reporter UX + leaves broken executable |
| **C** | Wrapper auto-install on first `sofer-mcp` run (`pip install fastmcp` at runtime) | Base stays lean; auto-heals | Mutates user env at runtime; breaks offline/air-gapped; violates "no network in tools" (MSP-R01: only `sofer_publish_confirm` has network); needs write perms | Medium | Rejected — violates security model + offline story |
| **D** | Two wheels: `sofer` (lean) vs `sofer-mcp` distribution | Clean separation; lean stays lean | Over-engineering; doubles release, docs, `uv tool` confusion; `fastmcp` footprint too small to justify split | High | Rejected — cost vs ~10 MB delta not justified; AI story wants MCP co-located |
| **E** | Promote but **remove** alias (`mcp` extra deleted) | Cleanest METADATA; no redundant line | **Breaking:** `pip install "sofer[mcp]"` fails for users pinned to old extra; churn for existing docs/scripts | Low | Deferred — keep alias one minor, deprecate in next major. Or keep indefinitely; alias is ~1 line and harmless. |
| **F** | Bundle/vendor fastmcp | No extra install step | Violates `AGENTS.md §9` dependency discipline; supply-chain hygiene risk; update lag | High | Rejected |

### 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Breaking lean install** — dataset-only users now pay ~10 MB / 8 extra packages even if they never run `sofer-mcp` | High (every install) | Low — marginal vs `pyarrow` (40 MB). No perf regression. | Communicate in release notes; `fastmcp` is pure Python, no build cost. If feedback negative, consider alias removal reasoning in next major. |
| **Alias breakage for `pip install "sofer[mcp]"`** — if alias removed, old one-liners fail | Low (if alias kept) / High (if removed) | Medium — CI/scripts with pinned extra break | **Keep `mcp = ["fastmcp>=3.4,<4"]` as alias** for one minor. Document alias as no-op ("already included"). |
| **`uv tool upgrade` path** — users on `uv tool install git+...@v0.3.6 --force` (no fastmcp) running `uv tool upgrade sofer` without `--with` may not pick up new required dep until re-install | Medium | Low — resolves on next `uv tool install "sofer @ git+...@v0.3.X" --force` | Note upgrade command in README + release notes. |
| **Version pin drift** — `dependencies: fastmcp>=3.4,<4` vs `optional-dependencies.mcp` alias vs `dependency-groups.dev` — three pins can diverge | Medium | Medium — lock/test mismatch | Pin identically in all three: `fastmcp>=3.4,<4`. Single source; update together. `uv lock` enforces. |
| **Guard wording drift** — stale `pip install 'sofer[mcp]'` hint after promotion misleads for direct-reference installs | High if not updated | Low — degraded-install only | Update guard message to include correct PEP 508 forms for both `pip` and `uv`. |
| **`release.yml` wheel check gap** — CI only asserts `sofer = sofer.cli:main`, not `sofer-mcp` | Low | Low — `sofer-mcp` already in wheel but unchecked | Extend `Verify console-script entry point` to assert both scripts; optional smoke `sofer-mcp --help`. |
| **README_ES sync lag** — fixing only EN README, forgetting ES (AGENTS.md §13 same-commit requirement) | Medium | Medium — CI/docs drift | Land both reads in same commit; prose ES, commands EN; verify headings order matches. |

---

## Affected Areas

- `pyproject.toml:21-29` — add `fastmcp>=3.4,<4` to `[project].dependencies` (primary change)
- `pyproject.toml:36-37` — keep `mcp = ["fastmcp>=3.4,<4"]` as alias for one minor (or remove with breaking-note; decision: keep)
- `pyproject.toml:43-50` — no functional change; keep `fastmcp` in `[dependency-groups].dev` but align pin
- `uv.lock:1943-1984` — regenerated (fastmcp moves to unconditional)
- `src/sofer/mcp_server.py:54-59` — update `ImportError` message to mention `pip` + `uv tool` + correct `sofer[mcp] @ git+...` syntax; keep guard
- `README.md:38-52` — replace Install code block with PEP 508 `sofer @ git+...` + `sofer[mcp] @ git+...` + `uvx --with` examples; `README.md:438-445` replace broken `git+...[mcp]` with `sofer[mcp] @ git+...` + `uv tool` counterpart; flip intro from "base stays lean — optional extra" to "included by default — alias"
- `README_ES.md:40-54` + `README_ES.md:473-481` — mirror above, Spanish prose, English commands, same commit per AGENTS.md §13
- `openspec/specs/mcp-server/spec.md:31-48` MSP-R02 + `:321-334` MSP-R12 — delta: `MODIFIED Requirement` for both (lean → included, optional → required + alias)
- `openspec/specs/packaging/spec.md:67-78` PKG-03 — optional extension to assert `sofer-mcp` entry point (non-blocking)
- `tests/test_mcp_server.py:139-146` + `964-1005` — invert/update `TestImportWithoutExtra` + `TestWheelPackaging` assertions
- `tests/test_mcp_registration.py` — not affected
- `docs/configuration.md` — no change (no extra listing)
- `.github/workflows/release.yml:84-88` — optional extension to assert `sofer-mcp` in `entry_points.txt`

## Approaches (summary)

1. **Promotion with alias retention (A)** — move pin to `dependencies`, keep `optional-dependencies.mcp` as one-minor alias, update guard/docs/specs, regenerate lock.
   - Pros: out-of-the-box `sofer-mcp`, backward compat, reporter-approved, ~10 MB cost
   - Cons: marginal size for lean users
   - Effort: Low

2. **Docs-only fix (B)** — correct `README.md:444` PEP 508, add `uv tool`/`uvx --with` examples, leave extra optional.
   - Pros: preserves lean, no wheel change
   - Cons: preserves crash, manual extra step, reporter rejected
   - Effort: Low

3. **Runtime auto-install wrapper (C)** — first `sofer-mcp` run bootstraps `fastmcp`.
   - Pros: auto-heals without wheel bloat
   - Cons: network at runtime, offline break, env mutation, violates MSP-R01
   - Effort: Medium

4. **Two-wheel split (D)** — separate `sofer-mcp` distribution.
   - Pros: perfect separation
   - Cons: double release, docs complexity, over-engineering for ~10 MB
   - Effort: High

## Recommendation

**Approach A — promote `fastmcp>=3.4,<4` from `[project.optional-dependencies].mcp` to `[project].dependencies`, retaining `mcp = ["fastmcp>=3.4,<4"]` as a one-minor alias.**

Why promotion wins:
- Fixes the **broken-by-default executable** — the highest UX cost in #100 (every `uv tool install` today ships a crashing `sofer-mcp`).
- Honors the reporter's explicit preference for automatic install (`prefiero que instale automáticamente`).
- Footprint is modest: ~8 packages / ~10 MB vs `pyarrow` already required; `fastmcp` adds no native extensions.
- Keeps blast radius small: one dependency line + docs + spec delta + guard wording + lock — no architecture change.
- Preserves backward compat via alias, so `pip install "sofer[mcp]"` and `pip install "sofer[mcp] @ git+..."` remain valid; deprecation can follow in next major if desired.

Docs must land atomically with the dependency move (same commit) per AGENTS.md §13: correct both READMEs, fix the broken `git+...[mcp]` suffix to `sofer[mcp] @ git+...`, add `uv tool` and `uvx --with` examples, and flip the intro from lean to included.

## Risks (condensed)

- Lean-install cost (+10 MB) — mitigated by modest delta vs `pyarrow` and release-notes communication.
- Alias drift/removal breakage — mitigated by keeping alias one minor and pinning identically in three places.
- Guard wording stale — update to mention PEP 508 forms for both `pip` and `uv`.
- `uv tool upgrade` not picking up new dep until re-install — document upgrade command.
- README_ES sync — enforce same-commit dual update.
- `release.yml` entry-point check gap — optionally extend to assert `sofer-mcp`.

## Ready for Proposal

**Yes** — exploration is complete and cites file:line. Next phases:

- `sdd-propose` — one-paragraph intent, scope, rollback, affected specs (`mcp-server` MSP-R02/R12, optionally `packaging` PKG-03).
- `sdd-spec` — delta specs for `mcp-server` (two `MODIFIED Requirements`) under `openspec/changes/feat-mcp-auto-install/specs/mcp-server/spec.md`.
- `sdd-design` — packaging decision + docs plan + test updates + lock strategy.
- `sdd-tasks` — 6-8 tasks: `pyproject.toml` + `uv.lock`, guard wording, README pair, spec delta, test assertion update, CI check optional, verification (`uv tool install` smoke, `test_wheel_declares_script_and_extra`).

No hidden coupling found beyond the 9 files listed in Affected Areas. No new `[tool.sofer]` key needed. No cross-spec blast radius.

---

*Evidence sources: `pyproject.toml:21-50`, `uv.lock:527-553/1943-1984`, `src/sofer/mcp_server.py:54-59/1488-1496`, `README.md:38-52/438-445`, `README_ES.md:40-54/473-481`, `openspec/specs/mcp-server/spec.md:31-48/321-334`, `openspec/specs/packaging/spec.md:67-78`, `tests/test_mcp_server.py:139-146/964-1005`, `tests/test_mcp_registration.py:1-564`, `.github/workflows/release.yml:71-88`, `docs/configuration.md:1-60`, `importlib.metadata` probes, `fastmcp`/`fastmcp-slim`/`mcp` transitive dep introspection, GH issue #100.*
