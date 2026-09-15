# Proposal: fix-cli-codebook-config

**Change**: `2026-09-14-fix-cli-codebook-config` · **Issue**: #182 · **Branch**: `fix/182-cli-codebook-config` (verified via `.git/HEAD`)
**Status**: proposal complete — no open question round; the three open questions were resolved by the parent (Resolutions 1–5 below)
**Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram mirrors it at `sdd/2026-09-14-fix-cli-codebook-config/proposal`
**Size**: ~10 production lines + ~45 test lines + one additive spec requirement · **Delivery**: `ask-on-risk` · budget 400 changed lines
**Exploration**: none persisted under `sdd/…/explore`; the parent supplied the findings inline and they were re-verified line-by-line.

## Intent

`sofer codebook FILE` reads a CSV with the *literal* defaults inside `codebook.generate` (`;`, `utf-8-sig`) instead of the
resolved `[tool.sofer]` values that MCP already passes. The same file therefore yields a different codebook per surface:
with `csv_delimiter = ","` the CLI collapses the header into **one column** where MCP returns **two**; with
`csv_encoding = "cp1252"` the CLI raises `UnicodeDecodeError`, and a bogus codec name raises `LookupError` — neither is
handled by the single-file branch, so both escape `_cmd_codebook` into `main()` as an **uncaught traceback**. A crash is
worse than a wrong column count. Fix: pass the resolved tool-wide config exactly as `sofer_codebook` does, and turn an
undecodable/undecodable-codec file into a clean diagnostic with a non-zero exit. Closes #182.

## Verified state

| Fact | Evidence (re-verified this phase) |
|---|---|
| Single-file branch passes no delimiter/encoding | `cli.py:235` `generate_codebook(args.csv, output_path=…, max_sample=…)` |
| Literal defaults are what take effect | `codebook.py:382-388` `generate(csv_path, output_path=None, delimiter=";", encoding="utf-8-sig", max_sample=None)` |
| Decode failure escapes unhandled | `codebook.py:65-69` `_read_csv(path, encoding="utf-8-sig", delimiter=";")`; `:75` `open(...)` has **no** enclosing `except` |
| MCP already complies (both paths) | `mcp_server.py:1484-1485` (`sofer_codebook`) and `:2892-2893` (resource) pass `delimiter=sofer_config.CSV_DELIMITER, encoding=sofer_config.CSV_ENCODING` |
| The `--all-files` branch needs nothing | `codebook.py:505-506` resolves dataset `[meta]` tier (`:485-489`), not `[tool.sofer]`; leave it alone |
| Pattern to mirror already exists in the same function | `cli.py:224` resolves `max_sample` through config at call time; `main():1607` calls `config.reload(None)` |
| Parity pinned on MCP side only | `tests/test_mcp_server.py:3564` `test_codebook_honors_tool_sofer_delimiter`; **no** CLI twin drives a configured delimiter/encoding |
| Tier and basis are spec-decided | `tool-config` **TC-04** (`spec.md:65`); `mcp-server` **MSP-R10** (`:373`); **CB-R10** (`codebook/spec.md:294`, precedent #155) |
| Branch | `.git/HEAD` → `ref: refs/heads/fix/182-cli-codebook-config` |
| Issue body / correction comment | **Not read this phase** — no shell tool exists in this phase, so `gh issue view 182` could not run. The parent supplied the issue content inline, and the correction comment on #182 matches the verified evidence above |

## Resolved decisions

1. **Undecodable input — follow the repo's existing contract, invent nothing.** `_csv_reader.py:27` `ENCODING_FALLBACKS = ["utf-8-sig", "utf-8"]`, policy at `:28-31`: non-UTF-8 files are rejected because the quality gate enforces
   UTF-8 before upload, so `latin-1`/`cp1252` are deliberately **not** retried. `stream_csv` (`:69-75`) resolves
   `delimiter`/`encoding`/`max_sample` through `config` **at call time**, honours the configured encoding first, and on
   exhaustion raises `ValueError("Cannot decode '<name>' — all encodings exhausted.")` (`:88`). `quality.py:533-556`
   probes under the same policy. So: pass the configured encoding, honour it first, add **no** latin-1/cp1252 retries.
2. **The diagnostic shape already exists in this file — reuse it, do not invent a convention.** `cli.py:210-213`, the
   `--all-files` sibling branch, already does exactly `except ValueError as exc: print(f"Error: {exc}", file=sys.stderr); return 1`.
   The single-file branch adopts that **same** shape: `ValueError`-shaped failure surfaced as `Error: <message>` on
   stderr with exit 1, never an uncaught traceback.
3. **Invalid codec name gets the same clean diagnostic — catching `LookupError` at the CLI branch (chosen).** `LookupError`
   (e.g. `csv_encoding = "not-a-codec"`) is **not** in the tuple `stream_csv` catches
   (`UnicodeDecodeError, UnicodeError, csv.Error`, `_csv_reader.py:84`), so it escapes as a traceback too; `tool-config`
   **TC-13** (`spec.md:315`) validates `csv_encoding` only as "a non-empty string", so a typo'd codec is reachable.
   Choice: widen the single-file branch to `except (ValueError, LookupError)` — no change to the shared reader and no
   scope creep into config validation (validating codec names at merge time would re-open TC-13 and is out of scope).
   `cli.py` is under the **100.00% per-file line-coverage mandate with `# pragma: no cover` forbidden** (AGENTS.md
   rule 14), so the added branch is **genuinely exercised** by a `csv_encoding = "not-a-codec"` case, not exempted.
4. **Parity direction: MCP stays untouched.** `mcp_server.py:1481-1487` / `:2890-2893` and `tests/test_mcp_server.py:3564-3574`
   already pin the correct behaviour. The CLI is the outlier, so this change adds **no MCP code and no MCP test** —
   an explicit non-goal so a reviewer does not go looking for it.
5. **CLI-R10 correction accepted.** `cli/spec.md:359` **CLI-R10** governs status-JSON stability (*"keeping parity between
   CLI and MCP **status**"*), not a general parity contract. The basis for this change is **MSP-R10 + TC-04 + CB-R10**.

## Scope

1. `src/sofer/cli.py`, single-file branch: pass `delimiter=config.CSV_DELIMITER, encoding=config.CSV_ENCODING` into
   `generate_codebook`, resolved at call time like `max_sample`.
2. Same path: `except (ValueError, LookupError)` → one `Error: …` line on stderr, return `1` (Resolution 2 shape).
3. Tests in `tests/test_cli.py`: (a) CLI twin of `test_mcp_server.py:3564` — `csv_delimiter = ","` + `,`-delimited file
   yields 2 columns; (b) non-default `csv_encoding` that succeeds; (c) undecodable bytes → exit 1, diagnostic, no
   `Traceback`; (d) bogus codec → same clean diagnostic (exercises the `LookupError` arm for rule 14).
4. Spec delta: **ADDED** requirement `CB-R11` in the `codebook` capability (tool-wide delimiter/encoding for the
   single-file path on both surfaces, plus the decode/codec diagnostic) — additive rather than `MODIFIED`, following
   CB-R10, so archive-time replacement stays lossless. `codebook` owns the contract; the CLI is one caller.

## Non-goals

- **No touch of `src/sofer/_converters.py` or `src/sofer/prepare.py`** — that defect (delimiter outside `SNIFF_DELIMITERS`
  → one-column Parquet, `cfg.csv_encoding` never consulted, ~185 dead helper lines) is **#181**, a separate change. V5 asserts zero changed paths there.
- **No MCP edits and no MCP test edits** (Resolution 4).
- `codebook.generate`'s parameter defaults stay — they remain the fallback for direct library callers; no dataset-level
  tier for this caller; no change to the already-correct `--all-files` branch; no codec-name validation at config-merge time.
- No CLI surface change (no new flag) → no `README.md` / `README_ES.md` edit; no `pyproject.toml`, no workflow, no
  `openspec/specs/**` (canonical sync is archive-time), no `openspec/changes/archive/**`, no other in-flight change.
- No commit, push or PR — the parent owns delivery.

## Affected areas

| Area | Impact | Description |
|---|---|---|
| `src/sofer/cli.py` | ~10 lines | Two kwargs + one `except (ValueError, LookupError)` branch in `_cmd_codebook` |
| `tests/test_cli.py` | ~45 lines | CLI parity twin, non-default-encoding success, undecodable bytes, bogus codec |
| `openspec/changes/2026-09-14-fix-cli-codebook-config/**` | New | Proposal + spec/design/tasks |
| `src/sofer/codebook.py`, `mcp_server.py`, `_converters.py`, `prepare.py` | None | Read-only reference |

## Verification

V1 `pytest -q tests/test_cli.py -k codebook_` → delimiter twin 2 columns; encoding success, undecodable and bogus-codec cases green.
V2 `pytest tests/ -q` → baseline 1766 passed / 6 skipped **plus** the added tests, 0 failures (AGENTS.md rule 6).
V3 `bash scripts/check_core_coverage.sh` (pinned 3.13) → exit 0, `cli.py` at **100.00%** (both new arms executed).
V4 `mypy src/` clean; `ruff check src/ tests/` clean.
V5 `git diff --stat` → only `cli.py`, `tests/test_cli.py`, `openspec/changes/…/**`; **zero** paths under `_converters.py` / `prepare.py`, zero MCP paths.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| 100% `cli.py` gate fails because a new branch is unreachable from a test | Low | Undecodable-bytes and bogus-codec tests drive both arms through the real subprocess boundary (`run_cli`), not a mock |
| Switching `;`→configured delimiter shifts existing CLI codebook output in a `;` repo | Low | Defaults unchanged when `[tool.sofer]` is silent; V2 catches any shift |
| Issue #182 content was not machine-read this phase | Low | Parent supplied it inline and its correction comment matches the verified evidence; Resolutions 1–5 remove the ambiguity it could have introduced |
