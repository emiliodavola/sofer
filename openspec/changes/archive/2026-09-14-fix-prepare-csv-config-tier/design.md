# Design — fix-prepare-csv-config-tier (issue #181)

Branch `fix/181-prepare-csv-config-tier` (`.git/HEAD` → `ref: refs/heads/fix/181-prepare-csv-config-tier`).
Delivery: `exception-ok`, **1500 changed lines explicitly authorized by the maintainer** so the 249-line
dead-code removal rides with the fix (recorded, not inferred). Scope ceiling: `_converters.py`, `prepare.py`,
`model.py`, three test modules. Zero `cli.py` / `codebook.py` / `repo_compliance.py` / `config.py` /
canonical-spec / README / `pyproject.toml` / workflow paths.

## Accurate defect statement (corrects the proposal's "fails / silently stages")

`pc.ReadOptions(encoding=...)` exists (pyarrow 25.0.0; `ReadOptions().encoding == 'utf8'`) and changes decoding,
but `_convert_csv_to_parquet` (`_converters.py:326-345`) never passes it: the file is decoded as UTF-8
regardless of `cfg.csv_encoding`. With the default, a `\xf1` byte does **not** raise — it comes back as a
**binary-typed value** (`b'\xf1'`), silently; other byte sequences do raise, and then the dispatcher returns
`{}` and `prepare.py:761` stages the original CSV. So the durable statement is *"the configured encoding is
never consulted, so decoding is UTF-8 either way — yielding a binary column or a read failure depending on the
bytes"*, not "it fails". Same correction applies to the delimiter half: a `|`-separated file with `|` ∉
`SNIFF_DELIMITERS` sniffs `best == 0` → tool-wide `";"` → **one column**, and the parity check re-reads with
the same wrong delimiter and agrees vacuously. The specs' normative clauses are already correct under this
reading; only the proposal's narration was overstated.

## D1 — presence signal: **declared-keys set (b)**, not `str | None` (a)

Add to `DatasetConfig`: `declared_meta_keys: frozenset[str] = field(default_factory=frozenset)`, populated in
`from_toml` as `frozenset(meta.keys())`; `csv_delimiter`/`csv_encoding` keep `";"` / `"utf-8-sig"`
(`model.py:321-322`, `:530-531` untouched in shape). Presence := `"csv_delimiter" in cfg.declared_meta_keys`.

Rejected (a) `str | None = None`: it makes `None` the default for **all 244 `DatasetConfig(` constructions**,
so every undeclared dataset would trip `model._validate_config_types:646-649` (`isinstance(cfg.csv_delimiter,
str)` → `None` → a diagnostic), failing the many `validate` tests that assert empty diagnostics; and the six
live readers (`checks.py:174-175`, `quality.py:232-233`, `codebook.py:505-506`, `mcp_server.py:1543-1544`,
`repo_compliance.py:522-523`, `prepare.py:805-806`) would each need a new `or`-fallback, i.e. files this
change may not touch. (b) keeps every default and every sibling reader bit-identical, makes presence observable
*independently of the value* (exactly PC-U01's demand: declared `;` ≠ declared nothing), and is cheapest to
test — one `from_toml` assertion plus two resolutions. Cost, documented: presence is a **TOML** fact; a
programmatic `DatasetConfig(csv_delimiter="|")` without the key set takes the fallback path (today's
behaviour), which is the safe direction.

## D2 — warning shape (declared wins, non-blocking)

Channel: **stdout** via `print`, matching every other warning in the module (`_converters.py:330, :340, :589`;
`prepare.py:761`) — never stderr, never a return-code change. Fires only when a delimiter is **declared**,
the file decodes with the tool-wide encoding, and the sniffed delimiter differs:

```text
  [!] {local.name}: declared csv_delimiter '|' differs from sniffed ';' — using declared '|'
```

The sniff used for comparison is the *baseline* one (tool-wide `config.CSV_ENCODING`) so the message means
"what sniff would have chosen today". If that baseline read cannot decode the file the warning is suppressed
(no spurious warning on the declared-encoding scenario). Conversion still returns the Parquet path; `prepare`
still returns `0` (`prepare.py:936`).

## D3 — wiring: one resolution site in `_converters.py`

`prepare.py:757` becomes `convert_file_to_parquet(local, entry_tmp, cfg)`; `_converters.py:565` loses
`_ = cfg  # reserved`; the dispatcher forwards `cfg` into `_convert_csv_to_parquet(local, staging_dir, cfg)`.
New single helper (module-private, one place to read):

```python
_resolve_csv_dialect(local, cfg) -> tuple[str, str]     # (delimiter, encoding)
  delimiter = cfg.csv_delimiter if "csv_delimiter" in cfg.declared_meta_keys
              else _sniff_csv_delimiter(local, config.CSV_ENCODING)
  encoding  = cfg.csv_encoding if "csv_encoding" in cfg.declared_meta_keys
              else config.CSV_ENCODING
```

Then `_sniff_csv_delimiter(csv_path, encoding=config.CSV_ENCODING)` (one added optional parameter — its eight
existing call/behaviour arms are preserved) and, beneath it, `_try_sniff_csv_delimiter(csv_path, encoding) ->
str | None` returning `None` **only** when the file cannot be decoded, used by the D2 comparison.

Read + parity must move together: `pc.read_csv(local, read_options=pc.ReadOptions(encoding=encoding),
parse_options=pc.ParseOptions(delimiter=delimiter))`, and `_read_csv_raw_values(csv_path, delimiter,
encoding)` / `_check_conversion_parity(csv_path, delimiter, table, encoding)` must take the **same** resolved
encoding — otherwise the Python-side parity read (`config.CSV_ENCODING`) cannot decode the declared-encoding
file, parity returns `False`, and the fix silently reverts to staging the original CSV.

**Byte-identity rule:** when neither key is declared, pass **no** `read_options` and the current
`config.CSV_ENCODING` to the Python readers — i.e. the pre-change code path verbatim. `ReadOptions(encoding=…)`
is passed *only* for a declared `csv_encoding`, which is what keeps the "no declared dialect ⇒ byte-identical"
scenario true by construction rather than by luck.

**Structural parity guarantee (mis-split catcher):** parity must stop being able to agree with a wrong
delimiter. Add a collapse guard inside `_check_conversion_parity`: if `table.num_columns == 1` **and** the raw
first line contains the resolved delimiter outside quotes, parity SHALL fail. When the declared delimiter is
absent from the file (the D2 disagreement scenario) the delimiter count is `0`, the guard does not fire, and
the spec's "still use the declared one, do not fail" scenario holds. Together: the delimiter used by the
Parquet read and by the parity read is now a single resolved value (no heuristic in the loop), plus an
explicit anti-collapse assertion — no vacuous agreement remains.

## D4 — the 43 call sites

| Site | Disposition |
|---|---|
| `test_parquet_conversion.py:115-230` (`_convert_to_parquet` units, ~8) | **Retarget** to `_converters.convert_file_to_parquet(local, staging, cfg)` in `tests/test_converters.py`; delete only exact duplicates of arms already covered there (empty CSV, all-null cast, parity failure). |
| `test_parquet_conversion.py:432-501` (`_sniff_csv_delimiter` ×8) | **Retarget by import swap** to `sofer._converters._sniff_csv_delimiter` — same behaviour, same tie-break arms, new home. |
| `test_parquet_conversion.py:505-…` (`delimiter=` precedence trio) | **Retarget** to the cfg seam: these become the live declared-wins coverage for PC-U01 (`;` / `,` / nothing declared). |
| `test_prepare.py:1192-1259` (`_read_csv_raw_values`, `_check_conversion_parity` ×~8) | **Retarget** to `sofer._converters` (signatures extended only by the new `encoding` argument). |
| `test_prepare.py:1666-1690` (2) | Retarget where the arm is unique, else delete. |

`tests/test_converters.py` is the natural home and today has **no** `csv_delimiter`/`csv_encoding` test
(verified), so retargeting adds coverage there instead of overlapping it. Floor discipline: read
`_converters.py`'s per-file floor (COV-01 / `scripts/check_core_coverage.sh`) before deleting anything and
forbid a net-negative on that file — retarget wherever the arm is unique, delete only verified duplicates;
`prepare.py`'s 100.00%/zero-pragma row (rule 14) is re-derived after the deletion. The delta's structural
assertion (cluster absent, unreferenced) is joined by stronger evidence: a spy asserting that a `prepare()`
run routes CSV conversion through `sofer._converters.convert_file_to_parquet` with the resolved dialect — this
is the "single home is exercised" scenario with teeth, where the import/absence check alone is weak.

## D5 — precedence placement (confirmed)

Coherent as split. `parquet-conversion` owns the reader table that names the `.csv` caller, so the normative
resolution order and the warning duty belong to **PC-U01**; `tool-config` **TC-04** is about the *lifecycle*
(one reload per invocation) and only carries an illustrative note, so it must not hold normative precedence —
it points at PC-U01. At archive sync both deltas are genuine **replacements** (`Previously:` lines preserve
the superseded text): PC-U01's `.csv` table row + resolution-order paragraph (`openspec/specs/
parquet-conversion/spec.md:517`) and TC-04's note paragraph (`openspec/specs/tool-config/spec.md:78-80`) are
replaced/appended, never merely appended-to; after sync no canonical text still asserts the flat tool-wide
claim for `prepare`. No canonical file is edited in this change.

## D6 — blast radius, rollback, verification

Files: `_converters.py` (resolution, encoding into read+parity, collapse guard, consume `cfg`), `prepare.py`
(pass `cfg` at `:757`; delete `:81-329`), `model.py` (`declared_meta_keys` + `from_toml`), `tests/test_
converters.py`, `tests/test_parquet_conversion.py`, `tests/test_prepare.py`. Nothing else.

Reviewer must check: (1) `git diff --name-only` contains no forbidden path; (2) `grep -rn
"_convert_to_parquet\|_sniff_csv_delimiter\|_read_csv_raw_values\|_check_conversion_parity" src/` yields only
`_converters.py`; (3) the warning text names **both** values and does not alter the exit code; (4)
undeclared-dialect Parquet is byte-identical (`hashlib` comparison, pre-change fixture); (5) `_converters.py`
coverage ≥ baseline, `prepare.py` still 100.00% with zero pragmas; (6) `uv run pytest tests/ -q` green with the
re-derived tally (do not trust a copied number, rule 6).

Evidence set (the last one is *newly created*; today's only end-to-end delimiter test,
`tests/test_parquet_conversion.py:713-736`, asserts merely that `data.parquet` exists and `data.csv` does not —
satisfied by a one-column Parquet, so the mis-split passes it): (E1) `|`-delimited end-to-end → true column
count, header not collapsed (catcher, does not exist today); (E2) declared wins; (E3) disagreement warning
naming both values; (E4) declared encoding honoured, original CSV not staged; (E5) undeclared ⇒ byte-identical.

**Work-unit ordering** (keeps the fix readable apart from the deletion; each unit independently revertible):
**WU1** `model.py` presence signal + `from_toml` test (no behaviour change). **WU2** `_converters.py` resolution
+ encoding + warning + collapse guard, with its own new tests in `tests/test_converters.py` (the *fix*; the
dead-copy tests still import cleanly, so WU2 stands alone and green). **WU3** delete `prepare.py:81-329` + pass
`cfg` at `:757` + dispose all 43 call sites + the spy/absence tests (pure subtraction in the reviewer's view).
Rollback: `git revert` per unit — reverting WU3 restores dead code only (no behaviour change); reverting WU2
alone returns conversion to tool-wide sniffing; no migration, no data cleanup.

## D7 — explicitly unresolved

**One open item, not guessed.** `config.CSV_ENCODING`'s value is `utf-8-sig`; whether
`pc.ReadOptions(encoding="utf-8-sig")` is accepted by pyarrow 25.0.0 was **not** verified (only `cp1252` and
the default `utf8` were). Two candidate readings: **(R1)** pass the declared name verbatim — a dataset
declaring `csv_encoding = "utf-8-sig"` (the very default value, likely present in real TOMLs) then either works
or fails per-file into "stage the original"; **(R2)** normalize aliases (`utf-8-sig` → `utf8`) via a small
constant map, accepting the BOM-handling question that follows. Design recommendation: **R1**, with a mandated
one-line probe at tasks/apply time (`ReadOptions(encoding="utf-8-sig")` in a scratch run) plus a regression
test for a dataset that declares `utf-8-sig` literally; fall back to **R2** only if the probe raises. This item
does not touch the fallback path, which passes no `read_options` at all. Secondary, out of scope by fiat: the
5 sibling readers could later consume `declared_meta_keys` (#182 / #202) — deliberately not done here.
