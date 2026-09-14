# Design: fix-cli-codebook-config (issue #182)

**Status**: complete (ready for tasks) · **Change**: `2026-09-14-fix-cli-codebook-config`
**Branch**: `fix/182-cli-codebook-config` — `.git/HEAD` → `ref: refs/heads/fix/182-cli-codebook-config` (verified this phase)
**Phase**: design (blueprint for apply) · Strict-TDD off (`config.yaml`); tests follow the CBT-R11 delta
**Delivery**: `ask-on-risk`, 400-line review budget · Store: hybrid (this file + Engram `sdd/2026-09-14-fix-cli-codebook-config/design`)
**Basis**: CB-R11 delta (`…/specs/codebook/spec.md`), MSP-R10, tool-config TC-04/TC-13, AGENTS rules 4/6/14.

## D1 — Where the config is read, and why there

`_cmd_codebook` resolves at **call time** from the config module constants, exactly as the MCP single-file path does
(`mcp_server.py:1484-1485`) and as the same function already resolves `max_sample` (`cli.py:224` →
`config.CODEBOOK_MAX_SAMPLE`):

```python
delimiter = config.CSV_DELIMITER      # cli.py single-file branch, beside the max_sample resolution
encoding = config.CSV_ENCODING
generate_codebook(args.csv, output_path=output_path, delimiter=delimiter, encoding=encoding, max_sample=max_sample)
```

**Ordering guarantee**: `main()` calls `_configure_console_streams()` then `config.reload(None)` (`cli.py:1606-1607`)
*before* `_build_parser()`/`parse_args()`/dispatch (`cli.py:1608-1610`), and dispatch happens only after `main()` returns
from the parser — so a module-constant read inside `_cmd_codebook` observes this invocation's single resolution
(TC-04). No second reload, no dataset tier, no `check_config_reload`-style plumbing; the module constant is the
intended seam. `--all-files` is untouched: `generate_all` keeps its dataset-`[meta]` tier (`codebook.py:505-506`).

## D2 — Exception surface: `(ValueError, LookupError)`, nothing wider

- Decode failures arrive as `UnicodeDecodeError ⊂ UnicodeError ⊂ ValueError` — the reason the `--all-files` sibling's
  `except ValueError` (`cli.py:210-213`) already catches them; the single-file branch simply had no such clause.
- An unknown codec raises `LookupError` (`unknown encoding: …`), which nothing catches today, and is reachable because
  TC-13 validates `csv_encoding` only as a non-empty string.
- Final clause: `except (ValueError, LookupError) as exc:` — the narrowest tuple that covers both reachable classes.
  **No `except Exception`**: `FileNotFoundError`/`IsADirectoryError` are `OSError`, deliberately not in scope (existing
  behaviour, unchanged by this change), and widening would silently swallow the `generate_all` collision `ValueError`
  contract class. No change to `_csv_reader.py`'s own catch tuple.

## D3 — Message shape: reuse the repository's existing phrasing

The `ValueError` text is *already* the repo's own and is reused verbatim, not re-invented: `stream_csv` raises
`ValueError("Cannot decode '<name>' — all encodings exhausted.")` (`_csv_reader.py:88`). Output goes through the
established envelope `Error: {exc}` on stderr with exit 1 (same shape as `cli.py:210-213`), so the two printed lines are:

- decode exhaustion → `Error: Cannot decode 'ventas.csv' — all encodings exhausted.`
- unknown codec → `Error: unknown encoding: not-a-codec.` (Python's own `LookupError` text under the same envelope)

One class of failure reads the same on every surface; no new message literal is introduced.

## D4 — Evaluated: keep `codebook`'s reader, or delegate to `stream_csv`? → **Option B**

| Criterion | Option A (minimal) | Option B (delegate) |
| --- | --- | --- |
| Shape | CLI passes config; `codebook._read_csv` keeps its own `open(...)` | CLI passes config; `_read_file`'s CSV arm delegates to `_csv_reader.stream_csv(delimiter=…, encoding=…, max_sample=None)` |
| Diff | ~10 production lines | ~25 production lines (adapter transposes `(header, row)` → column-wise) + tests |
| Fallback policy | **Fails CB-R11 scenarios 3 & 5**: a bare `open()` attempts the configured encoding once, then dies — `utf-8-sig → utf-8` is never walked ("nor under `utf-8-sig → utf-8`"). Restoring it locally means a second hand-rolled chain → AGENTS rule 4 violation | **Satisfied by reuse**: `_build_fallback_chain` (`:91-97`) puts the configured encoding first, then `utf-8-sig → utf-8`, and raises the established `ValueError` |
| Rule 4 (no duplicated logic) | Keeps the duplicate reader | Removes it for the codebook path |
| `cli.py` 100.00% gate | Identical cost — the same two arms (`ValueError`, `LookupError`) are exercised by the same two tests in both options | Identical cost |
| Risk | Lower | Touches the shared `_read_file` CSV arm, also used by `--all-files` |

**Recommendation: Option B.** Option A is only "smaller" by leaving the fallback contract unimplemented; B makes CB-R11
scenario 5 true *by reuse*, satisfies rule 4, and still fits the budget (~70 changed lines total, 400-line budget).
Two mandatory guardrails for the adapter: pass `max_sample=None` **explicitly** (otherwise `stream_csv` silently applies
`config.CODEBOOK_MAX_SAMPLE`, double-capping against `generate`'s own `_build_markdown(max_sample)`), and keep
`_read_tsv` as-is. `generate`/`generate_all` signatures and defaults are unchanged (binding non-goal).
**If the tasks phase cannot land B inside the budget, the only sanctioned fallback is A *plus* a spec correction to
scenarios 3/5 — never a locally re-rolled encoding chain.**

## D5 — Test set (four new tests, `tests/test_cli.py`, all via `run_cli`)

All four drive the subprocess boundary `tests/conftest.py::run_cli` (PB-02) — the only way `cli.py`'s new arms actually
execute under the 100.00% per-file mandate, since `# pragma: no cover` is forbidden (rule 14). Every case uses a
non-default delimiter, a non-default encoding, or a broken/absent codec; a `;`-default case proves nothing here.

| # | Test | Scenario | Non-default axis |
|---|---|---|---|
| 1 | `test_codebook_honors_tool_sofer_delimiter` (CLI twin of `test_mcp_server.py:3564`) | 1 + 2 | `csv_delimiter = ","` + `,` file → 2 columns (asserts the MCP-asserted structure) |
| 2 | `test_codebook_honors_tool_sofer_encoding` | 1 | `csv_encoding = "cp1252"`, `cp1252`-only bytes → success, same columns |
| 3 | `test_codebook_undecodable_file_is_diagnostic` | 3 + 5 | bytes undecodable under configured + both fallbacks → rc ≠ 0, stderr starts `Error: `, `"Traceback"` absent |
| 4 | `test_codebook_unknown_codec_is_diagnostic` | 4 | `csv_encoding = "not-a-codec"` → same assertions; this is the `LookupError` arm keeping `cli.py` at 100.00% |

## D6 — Blast radius and rollback

Changed: `src/sofer/cli.py` (kwargs + one `except`), `src/sofer/codebook.py` (`_read_csv` → adapter; **only** under
D4-B), `tests/test_cli.py`, this change's `openspec/changes/**`. Reviewer must check: (a) `git diff --stat` shows
**zero** paths under `src/sofer/_converters.py` and `src/sofer/prepare.py` (that is #181, a separate change) and **zero**
`mcp_server.py` / `tests/test_mcp_server.py` paths; (b) `codebook.generate` defaults and `generate_all`'s
`:505-506` tier byte-identical; (c) `stream_csv` receives an explicit `max_sample=None`; (d) `_csv_reader.py` untouched;
(e) `bash scripts/check_core_coverage.sh` exit 0 with `cli.py` at 100.00%. Rollback is a single-commit revert — no
migration, no persisted artifact, no config/pyproject/workflow surface touched.

## Output contract

- **status**: complete
- **executive_summary**: `_cmd_codebook`'s single-file branch froze the literal `";"`/`"utf-8-sig"` defaults inside
  `codebook.generate`, so a configured repo got one collapsed column (delimiter) or an uncaught `UnicodeDecodeError` /
  `LookupError` traceback (encoding). D1 resolves `config.CSV_DELIMITER`/`config.CSV_ENCODING` at call time beside the
  existing `max_sample` resolution, safe because `main()` reloads at `cli.py:1607` before dispatch at `:1610`.
  D2 fixes `except (ValueError, LookupError)` — justified because `UnicodeDecodeError ⊂ UnicodeError ⊂ ValueError`
  (which is why the `--all-files` sibling already catches it) and because `LookupError` is reachable under TC-13.
  D3 reuses the repo's own message and envelope: `Error: Cannot decode '<name>' — all encodings exhausted.` on stderr,
  exit 1. D4 evaluates both options and **recommends B** (delegate `codebook`'s CSV arm to `stream_csv`): A cannot walk
  the `utf-8-sig → utf-8` fallback the delta's scenarios 3/5 require without duplicating the chain (rule 4), whereas B
  gets that policy for free at the same `cli.py` coverage cost (~70 changed lines, inside the 400-line budget). D5 names
  four subprocess-boundary tests, one per scenario, each using a non-default delimiter/encoding or a broken codec. D6
  pins the diff to three production/test files with zero #181 and zero MCP paths; rollback is one revert.
- **artifacts**: `openspec/changes/2026-09-14-fix-cli-codebook-config/design.md` (this file) · Engram topic key
  `sdd/2026-09-14-fix-cli-codebook-config/design`, type `architecture`
- **next_recommended** (tasks): (1) `cli.py` kwargs + `except (ValueError, LookupError)`; (2) `codebook._read_csv`
  adapter over `stream_csv` with explicit `max_sample=None`; (3) the four `tests/test_cli.py` cases; (4) gates —
  `pytest -q tests/test_cli.py -k codebook_`, full `pytest tests/ -q` (1766+ passed / 6 skipped baseline, rule 6),
  `check_core_coverage.sh` (cli.py 100.00%), `mypy src/`, `ruff check src/ tests/`, `git diff --stat` scope check.
- **risks**: D4-B touches the shared `_read_file` CSV arm used by `--all-files` (mitigated: explicit params preserved,
  per-file `except Exception` warning path at `codebook.py:621-622` still catches the new `ValueError`); a mis-passed
  `max_sample` would double-cap row sampling (mitigated by the explicit `None`); existing `;`-default repos must see
  byte-identical output when `[tool.sofer]` is silent (mitigated by full-suite run).
- **skill_resolution**: none (no executor/phase skill path injected; no SDD-design skill in the available list —
  no fallback loading was required for this read-and-write phase).
