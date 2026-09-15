# Proposal: fix-prepare-csv-config-tier (issue #181)

Branch `fix/181-prepare-csv-config-tier` off `dev` @ 568cc67 (verified in `.git/HEAD`).

## Intent

The conversion path ignores the dataset's declared CSV dialect. `src/sofer/prepare.py:757` calls the dispatcher with no config — `convert_file_to_parquet(local, entry_tmp)` — and `_converters.py:541-545` accepts `cfg` only to discard it (`:565  _ = cfg  # reserved`). `_convert_csv_to_parquet` (`:328-345`) sniffs tool-wide at `:334`, never reading `cfg.csv_delimiter`/`cfg.csv_encoding`. Two failures follow, both silent:

1. A delimiter outside `config.SNIFF_DELIMITERS` (`[";", ",", "\t"]`, `config.py:53`) — e.g. declared `"|"` — sniffs `best == 0` → tool-wide `";"`; `pc.read_csv` yields **one column** named after the whole header line. The parity check re-reads the raw CSV with the same wrong delimiter, agrees, and writes the wrong Parquet with no warning.
2. `cfg.csv_encoding` is never consulted (`pc.read_csv` reads raw bytes), so a non-UTF-8 file fails conversion and `prepare` silently falls back to staging the original CSV.

Both stayed invisible because `prepare.py:81-329` holds a **dead duplicate** of the converter: `_convert_to_parquet` (`:271-329`) has **0 production callers** (src-wide grep returns only its own definition). Dead code that looks live makes the real path read as config-aware (AGENTS.md rule 4).

## Scope

### In Scope
1. Thread config into the live path (`prepare.py:757` → `convert_file_to_parquet` → `_convert_csv_to_parquet`): the declared `[meta] csv_delimiter`/`csv_encoding` governs; existing sniff/tool-wide behaviour is the fallback when nothing is declared.
2. Actually honour `csv_encoding` on that path.
3. Remove the dead cluster and dispose of its call sites: 27 in `tests/test_parquet_conversion.py`, 16 in `tests/test_prepare.py` (`:1192-1259`, `:1666-1690`). Retarget to the `_converters` seam or delete as already covered by `tests/test_converters.py`; the design decides per case.
4. Delta-amend the canonical contradiction (canonical sync at archive time). `openspec/specs/parquet-conversion/spec.md:517` (PC-U01) says the `.csv` reader sniffs `config.SNIFF_DELIMITERS` with `config.CSV_ENCODING` — tool-wide; `openspec/specs/tool-config/spec.md:78-80` (TC-04 note) says *"The `prepare` command uses the DATASET-level `[meta] csv_delimiter`, not this tool-wide key."* Same caller, contradictory text; the design picks which file carries the precedence clause.
5. The missing catcher test: a dataset declaring `csv_delimiter = "|"` must produce the correct column count, and the parity check must be structurally unable to agree with a wrong delimiter. **Today no such test exists** — the only end-to-end delimiter test (`tests/test_parquet_conversion.py:713-736`) asserts merely that `data.parquet` exists and `data.csv` does not, which a one-column Parquet satisfies.

### Out of Scope (explicit non-goals)
- `cli.py`, `codebook.py`, CLI/MCP codebook paths → issue **#182**, sibling change `2026-09-14-fix-cli-codebook-config` (PR #203). The diff must contain **zero** `cli.py`/`codebook.py` paths.
- `repo_compliance.py` hardcoded defaults → issue **#202**, separate change. Zero MCP changes.
- `README.md`/`README_ES.md` (CLI surface unchanged), `pyproject.toml`, workflows.
- `openspec/specs/**` (canonical sync at archive time), `openspec/changes/archive/**`, `openspec/changes/2026-09-14-chore-python-version-313/**`.
- No commit, push or PR.

## Capabilities

### Modified Capabilities
- `parquet-conversion` (PC-U01): dataset-declared delimiter/encoding takes precedence; sniff/tool-wide is the fallback.
- `tool-config` (TC-04): precedence clause reconciled with PC-U01.

(New capabilities: none. Provider v2.9.0/2.9.1 makes `spec` + `design` hard dependencies of `apply`, so this change **requires** a delta and is followed by spec, design and tasks.)

## Approach

**Recorded, not re-opened** (maintainer's decision): *the dataset's declared `[meta] csv_delimiter`/`csv_encoding` governs conversion; where the dataset declares nothing, current sniff/tool-wide behaviour remains the fallback.* This aligns an outlier rather than inventing policy: five readers already resolve from the dataset tier — `checks.py:174-175`, `quality.py:232-233`, `codebook.generate_all` (`codebook.py:505-506`), MCP `sofer_codebook_all` (`mcp_server.py:1543-1544`), schema-report CSV fallback (`repo_compliance.py:522-523`) — and `prepare.py:805-806` already forwards `cfg.csv_delimiter`/`cfg.csv_encoding` to the schema report.

Design must resolve one nuance: `model.py:530-531` does `meta.get("csv_delimiter", ";")` / `meta.get("csv_encoding", "utf-8-sig")`, so "declared nothing" is **indistinguishable** from "declared `;`". Declared-wins therefore needs presence observable — an optional field (`str | None`, `None` = not declared) or a recorded set of declared keys. The design picks the shape; the spec states the precedence.

## Corrections to the brief (re-verified on this branch)

- Dead cluster is `prepare.py:81-329` = **249 lines**, not `84-268`/185. That range covers only the five helpers; `_convert_to_parquet` (`:271-329`, 59 lines) is a sixth dead block, and `_cast_null_columns_to_string` is a *third* copy — live at `_converters.py:107`.
- Test call sites are 43 (27 + 16), not ~22.
- Tie-break divergence confirmed: dead `prepare.py:107-111` prefers `;` > `\t` > `,`; live `_converters.py:175-189` follows `SNIFF_DELIMITERS` → `;` > `,` > `\t`.

## Affected Areas

- `src/sofer/_converters.py` — Modified: consume `cfg`, honour encoding, parity independent of the sniffed delimiter.
- `src/sofer/prepare.py` — Modified: pass `cfg` at `:757`; delete `:81-329`.
- `src/sofer/model.py` — Modified: make "declared" observable.
- `tests/test_parquet_conversion.py`, `tests/test_prepare.py` — Modified: 43 call sites; add the mis-split catcher.
- `openspec/specs/parquet-conversion/spec.md`, `openspec/specs/tool-config/spec.md` — delta.

## Risks

- **Review budget (High)**: ~249 deletions + 43 test sites + new test + impl plausibly exceeds the 400-line budget. Mitigation: `ask-on-risk` pause at tasks time; chain by slice; never invent `size:exception`.
- **Behavior change (Med)**: a dataset that declares a delimiter its files do not use now converts differently. Mitigation: declared-wins is the decision, fallback only when undeclared, regression test.
- **Presence signal (Med)**: `str | None` vs declared-keys set alters a public dataclass default; a `None`/empty default keeps undeclared datasets on today's path. Mitigation: narrow `from_toml` test.
- **Coverage loss (Med)**: deleting tests may drop `_converters` arms. Mitigation: retarget where `tests/test_converters.py` lacks the arm; re-derive the tally.

## Rollback Plan / Dependencies

Revert the branch's commits — no migration or data cleanup; conversion returns to tool-wide sniffing. No blocker: sibling `2026-09-14-fix-cli-codebook-config` (#182) is independent, with no shared file.

## Success Criteria

- [ ] A dataset declaring `csv_delimiter = "|"` yields the correct column count end-to-end (new test).
- [ ] A declared `csv_encoding` converts instead of silently staging the CSV.
- [ ] An undeclared dialect behaves byte-identically to today.
- [ ] `prepare.py:81-329` is gone; no `from sofer.prepare import _convert_to_parquet` (or its siblings) remains in `src/` or `tests/`.
- [ ] `git diff --name-only` contains no `cli.py`, `codebook.py`, `repo_compliance.py` or `openspec/specs/**` path.
- [ ] `uv run pytest tests/ -q` green; `prepare.py` still measures 100.00% with zero pragmas (rule 14).

## Proposal question round

The config tier is settled, so these are PRD-level gaps only — answer, skip, or ask for a second round:

1. **Business rule**: when `[meta]` declares a delimiter the file does not actually use, should conversion fail loudly rather than keep declared-wins and emit a mis-split? (Today: silent either way.)
2. **Impact / migration**: are there published datasets whose `[meta]` declares a delimiter this path has been ignoring? Their next `prepare` output changes — warn, or stay silent?
3. **Scope boundary**: may the 249-line dead-code deletion ride with the fix, or split so the reviewer sees the fix isolated from the deletion (interacts with the 400-line budget)?
