# Proposal — `2026-09-26-test-205-csv-tier-gaps`

> **Change** `2026-09-26-test-205-csv-tier-gaps` · issue **#205** (*tests: five test-quality
> findings from the prepare csv-tier verification*) · branch `test/205-csv-tier-test-gaps` · base
> `dev` at `90de0f7` · store **hybrid** (this file + Engram).
>
> **Phase:** proposal. Inputs read directly: issue #205 body, the archived parent change
> `2026-09-14-fix-prepare-csv-config-tier` (proposal/design/apply-progress/archive-report),
> `tests/test_parquet_conversion.py`, `tests/test_converters.py`, `src/sofer/_converters.py`,
> `src/sofer/model.py`, `src/sofer/config.py`, `pyproject.toml`.
>
> **Status:** proposal complete. Tests-only. Any finding that would require a product-code change
> is reduced to a documented decision (ADR) and pinned by a test instead of expanding scope.

---

## 1. Intent

The verify phase of `2026-09-14-fix-prepare-csv-config-tier` (issue #181) recorded five
test-quality gaps. A test that cannot fail is worse than no test: it reads as proof. This change
turns the four test-only gaps into tests that **can** fail, and records the fifth (a documented API
boundary) as an explicit, pinned decision.

The parent change is already merged; the behaviour it fixed (dataset-declared `[meta]
csv_delimiter`/`csv_encoding` WINS over the sniff, PC-U01) is correct. The gap is in the **evidence**
for that behaviour, not in the behaviour itself. This change therefore touches tests (and one
comment) and nothing in the conversion logic.

## 2. Scope

### In scope

- **F1 — vacuous plumbing test** (`tests/test_parquet_conversion.py`,
  `TestDelimiterPlumbing::test_custom_delimiter_used_via_upload`). Rewrite it to drive the
  declared-TOML seam (`_declared_cfg`) and assert the **true column count/names**, not the mere
  presence of `data.parquet`. Proven RED against the mis-split before the fix.
- **F2 — untested JSONL fallback** (`src/sofer/_converters.py`,
  `_convert_jsonl_to_parquet` fallback; `tests/test_converters.py`). Add a test that forces the
  fallback and asserts its **real** behaviour (schema inferred from the first record; keys appearing
  only in later records are dropped; the parity check is advisory), and correct the inaccurate
  `from_pylist handles sparse keys (union)` comment.
- **F3 — non-discriminating declared-wins cases** (`tests/test_converters.py`,
  `TestCsvDialectResolution`). Add a declared-wins case over `|`, which is **outside**
  `config.SNIFF_DELIMITERS` (`[";", ",", "\t"]`), so honouring the declaration is the only way to
  pass.
- **F4 — brittle frozen digest** (`tests/test_parquet_conversion.py`,
  `TestUndeclaredDialectByteIdentical`). Replace the frozen `_PRECHANGE_UNDECLARED_SHA256` literal
  with a reference digest computed **at test time** from the pre-change read shape; a permitted
  pyarrow upgrade cannot break the assertion for the wrong reason.
- **F5 — programmatic-`DatasetConfig` boundary** (decision + test + ADR). Decide explicitly whether
  a programmatic `DatasetConfig(csv_delimiter="|")` without `declared_meta_keys` overriding is an
  acceptable library boundary. Decision: **accepted** (the presence signal is the contract; only
  `from_toml` populates it) and **pinned by a test**, documented in `design.md` (ADR-4) and already
  described in `model.py`'s `declared_meta_keys` docstring. No product change.
- A new `parquet-conversion` requirement **PC-U07** stating the discriminating, version-stable test
  evidence contract for the declared-dialect tier.
- Verify-phase evidence and the full suite green.

### Out of scope (non-goals, strictly respected)

- **No conversion-behaviour change.** `_converters.py` changes only its JSONL comment.
- **No `from_pylist` union fix.** The real pyarrow behaviour is asserted as-is; changing it is a
  product decision not carried by #205.
- **No presence-signal redesign.** `declared_meta_keys` keeps its shape; the boundary is accepted.
- **No coverage-floor or gate change**, no `# pragma: no cover`, no test-count weakening.
- **No CLI/MCP/README change.**
- No commit, push, or PR from any SDD phase.

## 3. Findings inventory (this branch, re-derived)

| # | Location | Current state | Fix |
| --- | --- | --- | --- |
| F1 | `test_parquet_conversion.py::TestDelimiterPlumbing::test_custom_delimiter_used_via_upload` | Programmatic `DatasetConfig(csv_delimiter="\|")` with empty `declared_meta_keys`; asserts only `data.parquet` exists and `data.csv` does not — a one-column mis-split satisfies both | Drive `_declared_cfg`, assert `num_columns == 2` / column names |
| F2 | `_converters.py:665-709` (`_convert_jsonl_to_parquet` fallback) | Fallback sub-path has no test; comment claims `from_pylist` unions sparse keys, which is false on pyarrow 25.0.0 | Force fallback; assert real behaviour; correct comment |
| F3 | `test_converters.py::TestCsvDialectResolution::test_declared_semicolon_wins` / `test_declared_comma_wins` | Sniff independently selects the same delimiter, so they pass whether or not the declaration is honoured | Add a `\|` case outside `SNIFF_DELIMITERS` |
| F4 | `test_parquet_conversion.py::_PRECHANGE_UNDECLARED_SHA256` | Literal digest of pyarrow-version-dependent output bytes | Derive the reference digest at test time |
| F5 | `model.py:336` / `_converters.py:264` | Programmatic value without `declared_meta_keys` falls back to sniff — documented but unpinned | Pin with a test; ADR records the accepted boundary |

## 4. Approach (settled decisions)

| # | Decision | Rationale |
| --- | --- | --- |
| **D1** | F1 drives `_declared_cfg` (the `from_toml` seam) and asserts the column count | The presence signal is `declared_meta_keys`, which only `from_toml` populates; the declared-TOML seam is the discriminating path. Column count, not file presence, is what a mis-split breaks |
| **D2** | F2 forces the fallback by making `pyarrow.json.read_json` raise, then asserts the real schema-from-first-record behaviour and corrects the comment | The fallback is otherwise unreachable in a deterministic test; asserting real behaviour is honest and adds no product change |
| **D3** | F3 adds a dedicated `\|` case rather than reworking the `;`/`,` cases | Keeps existing coverage while adding the one case that cannot pass by coincidence |
| **D4** | F4 recreates the pre-change read shape in-test and compares bytes produced by the same installed pyarrow | Removes the cross-version brittleness while preserving the byte-identity claim (both sides move together on an upgrade) |
| **D5** | F5 is an accepted boundary: programmatic value without the presence signal does not override | The signal is deliberate (issue #181 design D1); changing it would reverse a merged contract. Pinned by a test + ADR, no product change |
| **D6** | A new `PC-U07` requirement carries the evidence contract | The behaviour spec (PC-U01) is unchanged; the evidence duty needs an explicit home so it cannot silently regress |

## 5. Acceptance-criteria mapping

| AC (issue #205) | Criterion | Satisfied by |
| --- | --- | --- |
| F1 | `test_custom_delimiter_used_via_upload` asserts column count through the declared-TOML seam and fails against a mis-split (RED proven) | D1, task 1.2, verify report RED/GREEN evidence |
| F2 | JSONL fallback has a test asserting its real behaviour **and** the inaccurate comment is corrected | D2, tasks 1.3/1.4 |
| F3 | At least one declared-wins test uses a delimiter outside `SNIFF_DELIMITERS` | D3, task 1.1 |
| F4 | Byte-identity evidence no longer depends on frozen cross-version bytes | D4, task 1.5 |
| F5 | Programmatic boundary decided; if changed, presence signal redesigned. Decision: accepted, documented and pinned | D5, task 1.6 |
| — | `pytest` green; coverage TOTAL ≥ floor and the four COV-06 modules at 100.00% with no pragma | task 2.1/2.2 |

## 6. Verification strategy

- **RED before GREEN** for F1: run the rewritten assertion against the old (mis-split-producing)
  programmatic config and record the observed one-column failure; then run it green on the fixed
  test.
- **Unit:** the four new/rewritten tests plus the full suite `uv run pytest tests/ -q`.
- **Static/coverage:** `uv run coverage run -m pytest` + `uv run coverage report -m`; confirm the
  four COV-06 modules stay 100.00% and TOTAL ≥ the config floor.
- **Lint/types/gate:** `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/
  tests/ scripts/`, `uv run mypy src/ scripts/`, `uv run pyright`, and
  `uv run python scripts/check_test_mapping.py`.
