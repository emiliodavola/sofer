# Exploration: publish-readme-bugs

Verified against current code on branch `fix/publish-readme-bugs`. All four prior
diagnoses CONFIRMED; line numbers updated. No fixes applied.

## Bug 1 — Codebooks not uploaded with publish auto-prepare

**Root cause**
- `src/sofer/prepare.py:605-612` — `prepare(..., all_files: bool = False, ...)`.
- `src/sofer/prepare.py:785-796` — codebooks generated ONLY under `if all_files:`
  (`generate_all_codebooks(cfg, output_dir=...)`); otherwise prints the stderr
  advisory `"Re-run with --all-files ..."`.
- `src/sofer/publish.py:596-598` — auto-prepare calls `prepare(cfg, source,
  force=True)` with NO `all_files` → always `False`.
- `src/sofer/cli.py:528-576` — the `publish` subparser exposes `--target`,
  `--output`, `--force`, `--keep-csv`, `--dry-run`; NO `--all-files`.

**Current vs expected**
- Current: a plain `sofer publish config.toml` produces a package with Parquet +
  README + LICENSE but zero codebooks; nothing warns the user at publish time.
- Expected: publish delivers a complete package (data + card + license +
  codebooks), matching what `prepare --all-files && publish` would produce.

**Confirmed supporting facts**
- `_copy_package` (`src/sofer/publish.py:449-515`, codebook staging at 510-515)
  stages `codebooks/**/*.md` + root `codebook.md` correctly WHEN they exist.
- `_collect_codebook_remotes` (`src/sofer/publish.py:426-446`) reports them in
  the diff WHEN they exist — so absence is silent: the diff simply omits them.
- `planned_remotes` (`src/sofer/_mirror.py:53-87`) excludes codebooks BY DESIGN
  (docstring: "Compliance files … and codebooks are NOT included — callers stage
  those separately"). No change needed there.

**Affected tests**
- `tests/test_publish.py:695` `test_no_codebooks_means_nothing_codebook_staged`
  — **pins the buggy behavior** (asserts no codebook staged after bare prepare);
  must be updated/reversed by the fix.
- `tests/test_publish.py:677` `test_codebooks_staged_in_staging` — happy path
  when the user manually ran `prepare --all-files`; stays valid.
- `tests/test_prepare.py:255` `test_no_codebooks_without_all_files` — pins
  prepare-side advisory; stays valid while the `prepare` flag remains optional.

**Fix recommendation** — make publish's auto-prepare pass `all_files=True`
(publish = deliver the full package). Optionally thread an opt-out later.
Effort: Low. Risk: Low-Medium — reverses one pinned test; codebook generation
adds read time (up to CODEBOOK_MAX_SAMPLE rows per file) to auto-prepare runs.

## Bug 2 — README "Data Fields" mixes columns across files without attribution

**Root cause**
- `build_schema_report` (`src/sofer/repo_compliance.py:391-604`) merges columns
  from ALL `.csv` entries into ONE flat `list[ColumnSchema]`. Duplicate names
  across files are DROPPED (first-occurrence-wins) at `seen_names` checks:
  Parquet path lines 468-474, CSV path lines 527-533; only a console warning
  results (lines 580-602, threshold `SCHEMA_DUP_THRESHOLD`).
- `ColumnSchema` (`src/sofer/repo_compliance.py:124-149`) has NO origin/file
  field — attribution information is destroyed at collection time.
- The card renders the flat list side-by-side with no per-file grouping:
  `build_dataset_card` "### Data Fields" at `src/sofer/repo_compliance.py:848-865`.
- YAML `num_examples` bug: `src/sofer/repo_compliance.py:728-736` —
  `total_unique = sum(s.unique for s in schema)` becomes
  `splits[0]["num_examples"]`. Summing unique-value counts ACROSS COLUMNS AND
  FILES is not a row count (e.g., 13 unique values over 5 columns of a 5-row
  dataset → "num_examples: 13").

**Current vs expected**
- Current: one undifferentiated table; duplicate column names vanish silently;
  absurd `num_examples`.
- Expected: per-file attribution (grouped sections or a "File" column); every
  included column visible; `num_examples` = real sampled/actual row count per
  split (Parquet: `pf.metadata.num_rows`; CSV: counted rows), not `sum(unique)`.

**Fix recommendation** — add `origin: str | None = None` to `ColumnSchema`
(default `None`; all construction sites use keyword args — verified at
repo_compliance.py:502-512, 565-575 and tests — so backward compatible).
Populate from `origin_name` / `local.name`. In `build_dataset_card`, group rows
by origin (or add a File column) and stop skipping `::` pseudo-columns once
attribution is structural. Compute `num_examples` from actual row counts
collected during `build_schema_report` (it already opens each file) or from
Parquet metadata in `prepare`. Effort: Medium. Risk: Medium — touches the
card's YAML contract (`dataset_info.splits`); spec `openspec/specs/
repo-compliance/spec.md` § 3.1/§ 3.3 will need delta updates.

**Affected tests**
- `tests/test_repo_compliance.py:913` `test_dataset_info_has_splits_when_files_present`
  — only asserts `num_examples` key EXISTS (survives; value semantics change).
- Duplicate-handling warnings tests exist around § 3.3.7 scenarios
  (`tests/test_repo_compliance.py`, `SCHEMA_DUP_THRESHOLD` block) — behavior of
  *warnings* unchanged; report content changes need new tests.

## Bug 3 — README "Data Structure" shows local disk paths

**Root cause** — `src/sofer/repo_compliance.py:837-842`:

```python
file_list = "\n".join(f"  - `{e.local}` -> `{e.remote}`" for e in cfg.files)
```

- Embeds the publisher's private disk layout (`C:\Users\...\cache\data_a.csv`)
  into a PUBLIC artifact.
- Lists PRE-conversion remotes: a declared `data.csv` entry is rendered verbatim
  even though the repo actually delivers `data.parquet` (prepare converts;
  `_copy_package`/`planned_remotes` honor `upload_as_csv`, `keep_csv`,
  `recursive` — the card ignores all of them).

**Current vs expected**
- Current: `- {local disk path} -> {declared remote}` regardless of conversion.
- Expected: repo-relative DELIVERED paths only — exactly the mapping
  `planned_remotes(cfg, keep_csv)` computes (`_mirror.py:53-87`): recursive →
  directory remote; eligible CSV → `.parquet` remote (+ original CSV only when
  `keep_csv`); else declared remote. Drop `e.local` entirely.

**Affected tests** — none pin the format. `tests/test_repo_compliance.py:290`
(inside `test_happy_path_full_meta`, def at :253) only asserts the
`"## Dataset Structure"` header exists. Low test churn; low risk.

**Fix recommendation** — reuse the `planned_remotes` derivation (import from
`_mirror` or extract shared helper — AGENTS.md rule 4 forbids duplicating the
mapping logic). Render `- \`{remote}\`` per delivered path; optionally note
recursive directories. Effort: Low. Risk: Low.

## Bug 4 — "10,000-row sample" magic number + unique-counting stat bug

**Magic number**
- `_SCHEMA_SAMPLE_SIZE = 10_000` — hardcoded module constant,
  `src/sofer/repo_compliance.py:35` (with justifying comment). Used at:
  - `:371` `_read_parquet_sample` row-group limit
  - `:463` Parquet-path sample slice
  - `:522` CSV-path sample slice
- Footnote is a hardcoded STRING at `src/sofer/repo_compliance.py:861-864`:
  `"*Statistics (unique, missing%) based on a 10,000-row sample. ..."`
- Divergence: codebook samples `CODEBOOK_MAX_SAMPLE = 100_000` from
  `[tool.sofer] codebook_max_sample` (`pyproject.toml:79`, loaded at
  `src/sofer/config.py:146`) — same column shows different unique/missing
  between README and codebook.
- AGENTS.md rule 1 violation. `[tool.sofer]` currently has NO schema-sample key
  (verified pyproject.toml:60-110).

**Fix recommendation** — add `schema_sample_size` under `[tool.sofer]` (Dataset
Card section), expose `SCHEMA_SAMPLE_SIZE` in `config.py`, replace the constant
and its three uses; generate the footnote text FROM the configured value
(f-string), never a literal. Update the two footnote tests.

**Unique-counting bug** — contradicts the `ColumnSchema.unique` docstring
(`repo_compliance.py:134-135`: "excluding missing-value sentinels"):
- `src/sofer/repo_compliance.py:500` — Parquet path: `n_unique =
  len(set(col_values))` (None was coerced to "" at :380-381, so nulls count too).
- `src/sofer/repo_compliance.py:563` — CSV path: same expression.
- Both paths ALREADY compute the correct filtered list (`non_missing`, lines
  494-499 and 557-562) for `example` — the fix is `len(set(non_missing))`.
- SHARED bug in sibling modules (same sentinel-in-set mistake):
  - `src/sofer/codebook.py:291` — `n_unique = len(set(col_values))` (missing %
    at :293 correctly filters — inconsistent within the same function).
  - `src/sofer/profile.py:213` — `unique=len(set(values))` in `_build_column`
    (`_is_missing` used only for missing/example at :192-194).
- `quality.py` is CLEAN — uses `_is_missing` (:49) properly; no raw-set unique.

**Representativeness caveat (verified)** — `_read_parquet_sample`
(`repo_compliance.py:354-388`) reads ONLY row group 0 (`pf.read_row_groups([0])`,
line 369). For multi-row-group files the sample covers only the leading chunk
(bias for ordered/sorted data). With default `parquet_row_group_size = 100_000`
and a 10k sample cap, small datasets are unaffected; large ones sample the head.
Document in the footnote; consider spreading reads across row groups later
(out of scope here).

**Affected tests**
- `tests/test_repo_compliance.py:1733` `test_footnote_present_when_schema_has_columns`
  and `:1748` `test_no_footnote_when_schema_empty` — assert the literal
  "10,000-row sample" string; MUST be updated when configurable.
- No tests currently pin the wrong unique counts (they'd need sentinels in
  fixtures) — new tests required for the corrected behavior.

## Cross-cutting notes

1. **Tests to touch**: `test_publish.py:695` (Bug 1, reverse),
   `test_repo_compliance.py:1733/1748` (Bug 4, literal string),
   `test_repo_compliance.py:913` (Bug 2, survives). New tests: per-file
   attribution, delivered-path rendering, configured sample size, sentinel-free
   unique counts.
2. **AGENTS.md compliance**: Bug 3+4 fixes must share the conversion mapping
   (extract/reuse `planned_remotes` — rule 4) and route the sample size through
   `config.py`/`[tool.sofer]` (rule 1). New fields/params need docstrings
   (rule 2). All construction sites of `ColumnSchema` use keyword args, so
   appending `origin` is safe.
3. **Spec impact**: `openspec/specs/repo-compliance/spec.md` §§ 3.1-3.3 describe
   the current flat-schema card and sampling; the change needs delta specs.
4. **Ordering**: Bugs 2 and 4 both modify `build_schema_report` /
   `build_dataset_card`; implement together to avoid double test churn. Bug 1
   and Bug 3 are independent.
5. **Extra finding**: `cli.py:604-608` hardcodes `--max-sample` default
   `100_000` for `codebook` instead of using `CODEBOOK_MAX_SAMPLE` — same rule-1
   class of issue, worth folding into the fix batch.

## Ready for Proposal

Yes — all four diagnoses verified with exact current locations; recommend the
proposal scope cover all four bugs plus the `cli.py:606` literal, with Bug 2 as
the largest work item.
